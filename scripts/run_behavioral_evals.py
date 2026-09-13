#!/usr/bin/env python3
"""Run Teach Me eval cases through command-based model and grader adapters.

Each adapter receives one JSON object on stdin and must return one JSON object on
stdout. This keeps the runner independent of any model provider or agent host.
"""

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
    if completed.returncode != 0:
        raise RuntimeError(f"adapter failed ({completed.returncode}): {completed.stderr.strip()}")
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("adapter stdout was not one JSON object") from exc
    if not isinstance(output, dict):
        raise RuntimeError("adapter output must be a JSON object")
    return output


def load_suites(paths: list[Path], selected_case: str | None) -> list[dict[str, Any]]:
    suites: list[dict[str, Any]] = []
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        cases = data.get("cases", [])
        if selected_case:
            cases = [case for case in cases if f"{data.get('suite')}/{case.get('id')}" == selected_case]
        if cases:
            suites.append({"suite": data["suite"], "version": data["version"], "cases": cases})
    return suites


def validate_grade(grade: dict[str, Any], expected: list[str]) -> list[dict[str, Any]]:
    results = grade.get("results")
    if not isinstance(results, list) or len(results) != len(expected):
        raise RuntimeError("grader must return one result per expected criterion")
    normalized: list[dict[str, Any]] = []
    for criterion, item in zip(expected, results):
        if not isinstance(item, dict) or not isinstance(item.get("passed"), bool):
            raise RuntimeError("each grader result needs boolean passed")
        normalized.append(
            {
                "criterion": criterion,
                "passed": item["passed"],
                "reason": str(item.get("reason", "")),
            }
        )
    return normalized


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suites", nargs="*", type=Path)
    parser.add_argument("--response-command", help="command that generates a response from a JSON payload")
    parser.add_argument("--grader-command", help="command that grades a response from a JSON payload")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--case", help="run one suite/case-id")
    parser.add_argument("--output", type=Path, default=Path("reports/behavioral-evals.json"))
    parser.add_argument("--pass-threshold", type=float, default=0.90)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    if not 0 <= args.pass_threshold <= 1:
        parser.error("--pass-threshold must be between 0 and 1")
    paths = args.suites or (
        sorted((ROOT / "evals").glob("*.yaml"))
        + sorted((ROOT / "domain-packs").glob("*/evals.yaml"))
    )
    suites = load_suites(paths, args.case)
    case_count = sum(len(suite["cases"]) for suite in suites)
    if not case_count:
        parser.error("no matching eval cases")
    if args.validate_only:
        print(f"Behavioral eval runner loaded {len(suites)} suites and {case_count} cases")
        return 0
    if not args.response_command or not args.grader_command:
        parser.error("execution requires both --response-command and --grader-command")

    results: list[dict[str, Any]] = []
    for suite in suites:
        for case in suite["cases"]:
            turns = case.get("turns") or [{"role": "user", "content": case["prompt"]}]
            history: list[dict[str, str]] = []
            generated: dict[str, Any] = {}
            for turn_index, turn in enumerate(turns, 1):
                prompt = turn["content"]
                generation_payload = {
                    "type": "generate",
                    "suite": suite["suite"],
                    "case_id": case["id"],
                    "locale": case.get("locale"),
                    "prompt": prompt,
                    "history": history,
                    "turn_index": turn_index,
                    "turn_count": len(turns),
                    "skill_root": str(ROOT),
                }
                generated = invoke(args.response_command, generation_payload, args.timeout)
                response = generated.get("response")
                if not isinstance(response, str) or not response.strip():
                    raise RuntimeError(f"{suite['suite']}/{case['id']}: response adapter returned no response")
                history.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": response}])

            base = {
                "suite": suite["suite"],
                "case_id": case["id"],
                "locale": case.get("locale"),
                "prompt": turns[-1]["content"],
                "turns": turns,
                "transcript": history,
                "skill_root": str(ROOT),
            }
            graded = invoke(
                args.grader_command,
                {
                    "type": "grade",
                    **base,
                    "response": response,
                    "expected": case["expected"],
                    "grading_rule": "Judge observable behavior only. Do not award credit for implied or missing behavior.",
                },
                args.timeout,
            )
            criteria = validate_grade(graded, case["expected"])
            results.append(
                {
                    "suite": suite["suite"],
                    "case_id": case["id"],
                    "critical": bool(case.get("critical", False)),
                    "passed": all(item["passed"] for item in criteria),
                    "criteria": criteria,
                    "response": response,
                    "response_model": generated.get("model"),
                    "grader_model": graded.get("model"),
                }
            )

    passed = sum(item["passed"] for item in results)
    pass_rate = passed / len(results)
    critical_failures = [f"{item['suite']}/{item['case_id']}" for item in results if item["critical"] and not item["passed"]]
    report = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "cases": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": pass_rate,
            "threshold": args.pass_threshold,
            "critical_failures": critical_failures,
        },
        "results": results,
    }
    write_report(args.output, report)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if pass_rate >= args.pass_threshold and not critical_failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired, yaml.YAMLError) as exc:
        print(f"Behavioral eval failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
