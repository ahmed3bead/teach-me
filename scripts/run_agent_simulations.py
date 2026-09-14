#!/usr/bin/env python3
"""Run closed-book teacher/learner simulations through command adapters.

Live dialogue adapters must return ``utterance``, ``assessment_intent``, and
``done``. Missing structured fields are protocol failures. Conservative text
classification exists only for reading stored legacy transcript content.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from assessment_intent import ASSESSMENT_INTENTS, validate_assessment_intent
from locale_policy import canonical_locale
from run_behavioral_evals import (
    deterministic_assessment_check,
    deterministic_completeness_check,
    deterministic_language_check,
    deterministic_text_quality_check,
)

try:
    import yaml
except ImportError as exc:
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc


ROOT = Path(__file__).resolve().parents[1]
UNSUPPORTED_MASTERY_CLAIM = re.compile(
    r"(?:لقد\s+أتقنت|أنت\s+الآن\s+تتقن|أصبحت\s+تتقن|تم\s+تسجيل\s+(?:الإتقان|إتقان)|"
    r"you(?:'ve|\s+have)?\s+mastered|you\s+now\s+master|you\s+fully\s+understand|"
    r"marked\s+you\s+as\s+(?:mastered|proficient))",
    flags=re.IGNORECASE,
)
ROLE_OUTPUT_ARTIFACT = re.compile(
    r"\b(?:repair|correction|draft|evaluator|system|assistant)\s*:|"
    r"(?:^|\n)\s*[{}]\s*(?:$|\n)|<!--|</?[a-z][^>]*>",
    flags=re.IGNORECASE,
)


def invoke(command: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    completed = subprocess.run(
        shlex.split(command),
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(f"adapter failed ({completed.returncode}): {completed.stderr.strip()}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("adapter stdout was not one JSON object") from exc
    if not isinstance(result, dict):
        raise RuntimeError("adapter output must be a JSON object")
    return result


def load(selected: str | None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for path in sorted((ROOT / "evals" / "simulations").glob("*.yaml")):
        suite = yaml.safe_load(path.read_text(encoding="utf-8"))
        for simulation in suite["simulations"]:
            simulation["locale"] = canonical_locale(simulation["locale"])
            key = f"{suite['suite']}/{simulation['id']}"
            if not selected or selected == key:
                result.append({"key": key, **simulation})
    return result


def required_text(result: dict[str, Any], field: str, key: str) -> str:
    value = result.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{key}: adapter returned no {field}")
    return value


def required_learner_event(result: dict[str, Any], key: str) -> dict[str, str]:
    """Validate one structured dialogue event without inferring permission from prose."""
    utterance = result.get("utterance")
    if not isinstance(utterance, str) or not utterance.strip():
        raise RuntimeError(f"{key}: learner event requires a non-empty utterance")
    try:
        intent = validate_assessment_intent(utterance, result.get("assessment_intent"))
    except ValueError as exc:
        raise RuntimeError(f"{key}: invalid learner event: {exc}") from exc
    return {"utterance": utterance, "assessment_intent": intent}


def required_done(result: dict[str, Any], key: str) -> bool:
    """Require the live adapter's explicit Boolean completion event."""
    if "done" not in result or not isinstance(result["done"], bool):
        raise RuntimeError(f"{key}: learner event requires boolean done")
    return result["done"]


def expected_behavior_intent(behavior: Any) -> str | None:
    """Return an optional fixture expectation while retaining legacy string profiles."""
    if not isinstance(behavior, dict):
        return None
    expected = behavior.get("expected_assessment_intent")
    if expected not in ASSESSMENT_INTENTS:
        raise RuntimeError("structured learner behavior has invalid expected_assessment_intent")
    return expected


def grade_results(grade: dict[str, Any], expected: list[dict[str, str]], key: str) -> list[dict[str, Any]]:
    raw = grade.get("results")
    if not isinstance(raw, list) or len(raw) != len(expected):
        raise RuntimeError(f"{key}: grader must return one result per expected criterion")
    result = []
    for specification, item in zip(expected, raw):
        if not isinstance(item, dict) or not isinstance(item.get("passed"), bool):
            raise RuntimeError(f"{key}: each grader result needs boolean passed")
        reason = item.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise RuntimeError(f"{key}: each grader result needs a non-empty evidence reason")
        result.append(
            {
                "evidence_scope": specification["evidence_scope"],
                "criterion": specification["criterion"],
                "passed": item["passed"],
                "reason": reason,
                "attempts": item.get("attempts", 1),
                "retry_reason": item.get("retry_reason"),
            }
        )
    return result


def summarize_rows(rows: list[dict[str, Any]], simulations: int, threshold: float) -> dict[str, Any]:
    passed = sum(row.get("passed") is True for row in rows)
    failed = sum(row.get("passed") is False for row in rows)
    evaluated = passed + failed
    return {
        "simulations": simulations,
        "completed": sum(row.get("evaluation_status") == "completed" for row in rows),
        "passed": passed,
        "failed": failed,
        "pass_rate": passed / evaluated if evaluated else 0.0,
        "threshold": threshold,
        "critical_failures": [
            row["simulation_id"] for row in rows if row.get("critical") and row.get("passed") is False
        ],
    }


def score(grade: dict[str, Any], field: str, key: str) -> float:
    value = grade.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise RuntimeError(f"{key}: grader {field} must be a number from 0 to 1")
    return float(value)


def adapter_attempt_record(result: dict[str, Any], phase: str, turn: int | None = None) -> dict[str, Any]:
    record = {
        "phase": phase,
        "attempts": result.get("adapter_attempts", 1),
        "retry_reason": result.get("adapter_retry_reason"),
    }
    if turn is not None:
        record["turn"] = turn
    return record


def deterministic_simulation_guards(
    locale: str,
    history: list[dict[str, str]],
    learner_outputs: list[str],
    teacher_turn_checks: list[dict[str, Any]],
    learner_payloads_closed_book: bool,
) -> list[dict[str, Any]]:
    """Return hard, auditable checks that an AI simulation grader cannot override."""
    teacher_text = "\n".join(item["content"] for item in history if item["role"] == "teacher")
    learner_text = "\n".join(learner_outputs)
    teacher_language = deterministic_language_check(teacher_text, locale)
    learner_language = deterministic_language_check(learner_text, locale)
    text_quality = deterministic_text_quality_check(teacher_text + "\n" + learner_text)
    teacher_language_failures = [
        item["turn_index"] for item in teacher_turn_checks if not item["language"]["passed"]
    ]
    assessment_failures = [
        item["turn_index"] for item in teacher_turn_checks if not item["assessment"]["passed"]
    ]
    completeness_failures = [
        item["turn_index"] for item in teacher_turn_checks if not item["completeness"]["passed"]
    ]
    mastery_matches = sorted(set(UNSUPPORTED_MASTERY_CLAIM.findall(teacher_text)))
    role_artifacts = sorted(set(match.group(0).strip() for match in ROLE_OUTPUT_ARTIFACT.finditer(learner_text)))
    return [
        {
            "guard": "closed-book learner payload boundary",
            "passed": learner_payloads_closed_book,
            "reason": (
                "baseline, dialogue, and transfer learner payloads exclude the hidden teaching_material field"
                if learner_payloads_closed_book
                else "a learner payload exposed the hidden teaching_material field"
            ),
        },
        {
            "guard": "teacher output language",
            "passed": bool(teacher_language["passed"] and not teacher_language_failures),
            "reason": f"{teacher_language['reason']}; failing teacher turns {teacher_language_failures}",
        },
        {"guard": "learner output language", **learner_language},
        {"guard": "generated text quality", **text_quality},
        {
            "guard": "learner output contains only learner utterances",
            "passed": not role_artifacts,
            "reason": f"role or template artifacts {role_artifacts}",
        },
        {
            "guard": "assessment requires prior learner opt-in",
            "passed": not assessment_failures,
            "reason": f"deterministic opt-in failures on teacher turns {assessment_failures}",
        },
        {
            "guard": "teacher responses are complete",
            "passed": not completeness_failures,
            "reason": f"deterministic completeness failures on teacher turns {completeness_failures}",
        },
        {
            "guard": "no unsupported mastery claim",
            "passed": not mastery_matches,
            "reason": f"unsupported mastery markers {mastery_matches}",
        },
    ]


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def invocation_attempt_count(exc: BaseException) -> int:
    match = re.search(r"\battempts=(\d+)\b", str(exc))
    return int(match.group(1)) if match else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--teacher-command")
    parser.add_argument("--learner-command")
    parser.add_argument("--grader-command")
    parser.add_argument("--simulation")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("reports/agent-simulations.json"))
    parser.add_argument("--pass-threshold", type=float, default=0.90)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    if not 0 <= args.pass_threshold <= 1:
        parser.error("--pass-threshold must be between 0 and 1")
    simulations = load(args.simulation)
    if not simulations:
        parser.error("no matching simulations")
    if args.validate_only:
        print(f"Dynamic simulation runner loaded {len(simulations)} simulations")
        return 0
    if not all((args.teacher_command, args.learner_command, args.grader_command)):
        parser.error("execution requires teacher, learner, and grader commands")

    started_at = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "generated_at": started_at,
        "run_status": "running",
        "summary": {
            "simulations": len(simulations),
            "completed": 0,
            "passed": 0,
            "failed": 0,
            "pass_rate": 0.0,
            "threshold": args.pass_threshold,
            "critical_failures": [],
        },
        "results": rows,
    }
    write_report(args.output, report)

    for simulation in simulations:
        key = simulation["key"]
        failure_stage = "initialization"
        model_role: str | None = None
        baseline = ""
        transfer = ""
        learner_outputs: list[str] = []
        history: list[dict[str, Any]] = []
        teacher_models: list[str | None] = []
        learner_models: list[str | None] = []
        teacher_turn_checks: list[dict[str, Any]] = []
        teacher_adapter_calls: list[dict[str, Any]] = []
        learner_adapter_calls: list[dict[str, Any]] = []
        remaining_lifecycle_events: list[Any] = []
        learner_payloads_closed_book = True
        deterministic_guards: list[dict[str, Any]] = []
        row: dict[str, Any] = {
            "simulation_id": key,
            "critical": simulation["critical"],
            "evaluation_status": "running",
            "passed": None,
            "minimum_gain": simulation["minimum_gain"],
            "minimum_transfer": simulation["minimum_transfer"],
            "turns": 0,
            "criteria": [],
            "deterministic_guards": [],
            "teacher_turn_checks": [],
            "baseline_answer": None,
            "transcript": [],
            "transfer_answer": None,
            "teacher_models": [],
            "learner_models": [],
            "teacher_adapter_calls": [],
            "learner_adapter_calls": [],
            "remaining_lifecycle_events": [],
        }
        rows.append(row)
        write_report(args.output, report)
        public = {
            "simulation_id": key,
            "locale": simulation["locale"],
            "learner_persona": simulation["learner_persona"],
            "learner_behaviors": simulation["learner_behaviors"],
        }
        try:
            failure_stage = "baseline"
            model_role = "learner"
            baseline_payload = {
                "type": "baseline", **public, "task": simulation["baseline_task"],
                "instruction": "Answer from your current knowledge only. The fictional teaching material is intentionally unavailable.",
            }
            learner_payloads_closed_book = "teaching_material" not in baseline_payload
            baseline_result = invoke(args.learner_command, baseline_payload, args.timeout)
            baseline = required_text(baseline_result, "answer", key)
            learner_outputs = [baseline]
            learner_event = {
                "utterance": simulation["initial_request"],
                "assessment_intent": "none",
            }
            learner_models = [baseline_result.get("model")]
            learner_adapter_calls = [adapter_attempt_record(baseline_result, "baseline")]

            for turn_index in range(1, simulation["max_turns"] + 1):
                failure_stage = f"teacher_turn_{turn_index}"
                model_role = "teacher"
                teaching = invoke(args.teacher_command, {
                    "type": "teach", "simulation_id": key, "locale": simulation["locale"],
                    "teaching_material": simulation["teaching_material"], "history": history,
                    "learner_message": learner_event["utterance"],
                    "learner_event": learner_event,
                    "turn_index": turn_index,
                    "max_turns": simulation["max_turns"], "skill_root": str(ROOT),
                }, args.timeout)
                teacher_response = required_text(teaching, "response", key)
                teacher_models.append(teaching.get("model"))
                teacher_adapter_calls.append(adapter_attempt_record(teaching, "teach", turn_index))
                teacher_turn_checks.append(
                    {
                        "turn_index": turn_index,
                        "language": deterministic_language_check(teacher_response, simulation["locale"]),
                        "text_quality": deterministic_text_quality_check(teacher_response),
                        "completeness": deterministic_completeness_check(
                            teacher_response,
                            simulation["initial_request"],
                            learner_event=learner_event,
                        ),
                        "assessment": deterministic_assessment_check(
                            teacher_response,
                            learner_event=learner_event,
                        ),
                    }
                )
                history.extend([
                    {
                        "role": "learner",
                        "content": learner_event["utterance"],
                        "assessment_intent": learner_event["assessment_intent"],
                    },
                    {"role": "teacher", "content": teacher_response},
                ])
                failure_stage = f"learner_turn_{turn_index}"
                model_role = "learner"
                dialogue_payload = {
                    "type": "dialogue", **public, "history": history, "turn_index": turn_index,
                    "max_turns": simulation["max_turns"],
                    "current_behavior": (
                        simulation["learner_behaviors"][turn_index - 1]
                        if turn_index <= len(simulation["learner_behaviors"])
                        else None
                    ),
                    "completed_behaviors": simulation["learner_behaviors"][: max(turn_index - 1, 0)],
                    "instruction": "Respond as the persona. Do not invent rules not stated in the transcript.",
                }
                learner_payloads_closed_book = learner_payloads_closed_book and "teaching_material" not in dialogue_payload
                learner = invoke(args.learner_command, dialogue_payload, args.timeout)
                learner_models.append(learner.get("model"))
                learner_adapter_calls.append(adapter_attempt_record(learner, "dialogue", turn_index))
                done = required_done(learner, key)
                next_learner_event = required_learner_event(learner, key)
                expected_intent = expected_behavior_intent(dialogue_payload["current_behavior"])
                if expected_intent is not None and next_learner_event["assessment_intent"] != expected_intent:
                    raise RuntimeError(
                        f"{key}: learner assessment_intent {next_learner_event['assessment_intent']!r} "
                        f"did not exercise expected intent {expected_intent!r}"
                    )
                learner_outputs.append(next_learner_event["utterance"])
                if done or turn_index == simulation["max_turns"]:
                    history.append({
                        "role": "learner",
                        "content": next_learner_event["utterance"],
                        "assessment_intent": next_learner_event["assessment_intent"],
                    })
                if done and turn_index < len(simulation["learner_behaviors"]):
                    remaining_lifecycle_events = simulation["learner_behaviors"][turn_index:]
                    row["remaining_lifecycle_events"] = remaining_lifecycle_events
                    failure_stage = "lifecycle"
                    raise RuntimeError(
                        f"{key}: learner ended before all required behaviors were exercised"
                    )
                if done:
                    break
                learner_event = next_learner_event

            completed_behavior_count = min(turn_index, len(simulation["learner_behaviors"]))
            if completed_behavior_count < len(simulation["learner_behaviors"]):
                remaining_lifecycle_events = simulation["learner_behaviors"][completed_behavior_count:]
                row["remaining_lifecycle_events"] = remaining_lifecycle_events
                failure_stage = "lifecycle"
                model_role = "learner"
                raise RuntimeError(
                    f"{key}: maximum turns reached with unexercised learner behaviors"
                )

            failure_stage = "transfer"
            model_role = "learner"
            transfer_payload = {
                "type": "transfer", **public, "history": history, "task": simulation["transfer_task"],
                "instruction": "Solve independently from what the teacher taught. Do not receive hidden teaching material.",
            }
            learner_payloads_closed_book = learner_payloads_closed_book and "teaching_material" not in transfer_payload
            transfer_result = invoke(args.learner_command, transfer_payload, args.timeout)
            transfer = required_text(transfer_result, "answer", key)
            learner_outputs.append(transfer)
            learner_models.append(transfer_result.get("model"))
            learner_adapter_calls.append(adapter_attempt_record(transfer_result, "transfer"))
            deterministic_guards = deterministic_simulation_guards(
                simulation["locale"], history, learner_outputs, teacher_turn_checks,
                learner_payloads_closed_book,
            )
            row.update({
                "evaluation_status": "awaiting_grading",
                "turns": len(teacher_models),
                "deterministic_guards": deterministic_guards,
                "teacher_turn_checks": teacher_turn_checks,
                "baseline_answer": baseline,
                "transcript": history,
                "transfer_answer": transfer,
                "teacher_models": teacher_models,
                "learner_models": learner_models,
                "teacher_adapter_calls": teacher_adapter_calls,
                "learner_adapter_calls": learner_adapter_calls,
            })
            write_report(args.output, report)

            failure_stage = "grading"
            model_role = "grader"
            graded = invoke(args.grader_command, {
                "type": "simulation-grade", "simulation_id": key, "locale": simulation["locale"],
                "teaching_material": simulation["teaching_material"], "baseline_task": simulation["baseline_task"],
                "baseline_answer": baseline, "transcript": history, "transfer_task": simulation["transfer_task"],
                "transfer_answer": transfer, "expected": simulation["expected"],
                "grading_rule": "Score observable evidence only. Penalize leakage, invented knowledge, prompting pressure, and unsupported mastery claims.",
            }, args.timeout)
            failure_stage = "post_grading_validation"
            baseline_score = score(graded, "baseline_score", key)
            transfer_score = score(graded, "transfer_score", key)
            criteria = grade_results(graded, simulation["expected"], key)
            gain = transfer_score - baseline_score
            passed = (
                transfer_score >= simulation["minimum_transfer"]
                and gain >= simulation["minimum_gain"]
                and all(item["passed"] for item in criteria)
                and all(item["passed"] for item in deterministic_guards)
            )
            row.update({
                "evaluation_status": "completed",
                "passed": passed,
                "baseline_score": baseline_score,
                "transfer_score": transfer_score,
                "gain": gain,
                "criteria": criteria,
                "grader_model": graded.get("model"),
                "grader_score_attempts": graded.get("score_attempts", 1),
                "grader_score_retry_reason": graded.get("score_retry_reason"),
                "baseline_score_reason": graded.get("baseline_score_reason"),
                "transfer_score_reason": graded.get("transfer_score_reason"),
            })
        except (OSError, RuntimeError, subprocess.TimeoutExpired, ValueError) as exc:
            row.update({
                "evaluation_status": "failed",
                "passed": False,
                "turns": len(teacher_models),
                "deterministic_guards": deterministic_guards,
                "teacher_turn_checks": teacher_turn_checks,
                "baseline_answer": baseline or None,
                "transcript": history,
                "transfer_answer": transfer or None,
                "teacher_models": teacher_models,
                "learner_models": learner_models,
                "teacher_adapter_calls": teacher_adapter_calls,
                "learner_adapter_calls": learner_adapter_calls,
                "remaining_lifecycle_events": remaining_lifecycle_events,
                "failure_stage": failure_stage,
            })
            report.update({
                "run_status": "failed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "failure_stage": failure_stage,
                "error": {"type": type(exc).__name__, "message": str(exc)[:500]},
                "model_role": model_role,
                "invocation_attempt_count": invocation_attempt_count(exc),
            })
            report["summary"] = summarize_rows(rows, len(simulations), args.pass_threshold)
            write_report(args.output, report)
            print(f"Agent simulation failed: {exc}", file=sys.stderr)
            return 2

    summary = summarize_rows(rows, len(simulations), args.pass_threshold)
    report.update({
        "run_status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
    })
    write_report(args.output, report)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["pass_rate"] >= args.pass_threshold and not summary["critical_failures"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired, yaml.YAMLError) as exc:
        print(f"Agent simulation failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
