#!/usr/bin/env python3
"""Run closed-book teacher/learner simulations through command adapters."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc


ROOT = Path(__file__).resolve().parents[1]


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
            key = f"{suite['suite']}/{simulation['id']}"
            if not selected or selected == key:
                result.append({"key": key, **simulation})
    return result


def required_text(result: dict[str, Any], field: str, key: str) -> str:
    value = result.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RuntimeError(f"{key}: adapter returned no {field}")
    return value


def grade_results(grade: dict[str, Any], expected: list[str], key: str) -> list[dict[str, Any]]:
    raw = grade.get("results")
    if not isinstance(raw, list) or len(raw) != len(expected):
        raise RuntimeError(f"{key}: grader must return one result per expected criterion")
    result = []
    for criterion, item in zip(expected, raw):
        if not isinstance(item, dict) or not isinstance(item.get("passed"), bool):
            raise RuntimeError(f"{key}: each grader result needs boolean passed")
        result.append({"criterion": criterion, "passed": item["passed"], "reason": str(item.get("reason", ""))})
    return result


def score(grade: dict[str, Any], field: str, key: str) -> float:
    value = grade.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise RuntimeError(f"{key}: grader {field} must be a number from 0 to 1")
    return float(value)


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


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

    rows: list[dict[str, Any]] = []
    for simulation in simulations:
        key = simulation["key"]
        public = {
            "simulation_id": key,
            "locale": simulation["locale"],
            "learner_persona": simulation["learner_persona"],
            "learner_behaviors": simulation["learner_behaviors"],
        }
        baseline_result = invoke(args.learner_command, {
            "type": "baseline", **public, "task": simulation["baseline_task"],
            "instruction": "Answer from your current knowledge only. The fictional teaching material is intentionally unavailable.",
        }, args.timeout)
        baseline = required_text(baseline_result, "answer", key)
        history: list[dict[str, str]] = []
        learner_message = simulation["initial_request"]
        teacher_models: list[str | None] = []
        learner_models: list[str | None] = [baseline_result.get("model")]
        for turn_index in range(1, simulation["max_turns"] + 1):
            teaching = invoke(args.teacher_command, {
                "type": "teach", "simulation_id": key, "locale": simulation["locale"],
                "teaching_material": simulation["teaching_material"], "history": history,
                "learner_message": learner_message, "turn_index": turn_index,
                "max_turns": simulation["max_turns"], "skill_root": str(ROOT),
            }, args.timeout)
            teacher_response = required_text(teaching, "response", key)
            teacher_models.append(teaching.get("model"))
            history.extend([
                {"role": "learner", "content": learner_message},
                {"role": "teacher", "content": teacher_response},
            ])
            learner = invoke(args.learner_command, {
                "type": "dialogue", **public, "history": history, "turn_index": turn_index,
                "max_turns": simulation["max_turns"],
                "instruction": "Respond as the persona. Do not invent rules not stated in the transcript.",
            }, args.timeout)
            learner_models.append(learner.get("model"))
            done = learner.get("done", False)
            if not isinstance(done, bool):
                raise RuntimeError(f"{key}: learner done must be boolean")
            if done:
                break
            learner_message = required_text(learner, "message", key)

        transfer_result = invoke(args.learner_command, {
            "type": "transfer", **public, "history": history, "task": simulation["transfer_task"],
            "instruction": "Solve independently from what the teacher taught. Do not receive hidden teaching material.",
        }, args.timeout)
        transfer = required_text(transfer_result, "answer", key)
        learner_models.append(transfer_result.get("model"))
        graded = invoke(args.grader_command, {
            "type": "simulation-grade", "simulation_id": key, "locale": simulation["locale"],
            "teaching_material": simulation["teaching_material"], "baseline_task": simulation["baseline_task"],
            "baseline_answer": baseline, "transcript": history, "transfer_task": simulation["transfer_task"],
            "transfer_answer": transfer, "expected": simulation["expected"],
            "grading_rule": "Score observable evidence only. Penalize leakage, invented knowledge, prompting pressure, and unsupported mastery claims.",
        }, args.timeout)
        baseline_score = score(graded, "baseline_score", key)
        transfer_score = score(graded, "transfer_score", key)
        criteria = grade_results(graded, simulation["expected"], key)
        gain = transfer_score - baseline_score
        passed = (
            transfer_score >= simulation["minimum_transfer"]
            and gain >= simulation["minimum_gain"]
            and all(item["passed"] for item in criteria)
        )
        rows.append({
            "simulation_id": key, "critical": simulation["critical"], "passed": passed,
            "baseline_score": baseline_score, "transfer_score": transfer_score, "gain": gain,
            "minimum_gain": simulation["minimum_gain"], "minimum_transfer": simulation["minimum_transfer"],
            "turns": len(history) // 2, "criteria": criteria, "baseline_answer": baseline,
            "transcript": history, "transfer_answer": transfer, "teacher_models": teacher_models,
            "learner_models": learner_models, "grader_model": graded.get("model"),
        })

    passed_count = sum(row["passed"] for row in rows)
    rate = passed_count / len(rows)
    critical_failures = [row["simulation_id"] for row in rows if row["critical"] and not row["passed"]]
    summary = {"simulations": len(rows), "passed": passed_count, "failed": len(rows) - passed_count,
               "pass_rate": rate, "threshold": args.pass_threshold, "critical_failures": critical_failures}
    write_report(args.output, {"schema_version": "1.0.0", "generated_at": datetime.now(timezone.utc).isoformat(),
                               "summary": summary, "results": rows})
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if rate >= args.pass_threshold and not critical_failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired, yaml.YAMLError) as exc:
        print(f"Agent simulation failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
