#!/usr/bin/env python3
"""End-to-end protocol and threshold tests for the behavioral eval runner."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_behavioral_evals.py"
RESPONSE = ROOT / "fixtures" / "eval-adapters" / "fixture_response.py"
GRADER = ROOT / "fixtures" / "eval-adapters" / "fixture_grader.py"


def run(suite: Path, report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            str(suite),
            "--response-command",
            f"{sys.executable} {RESPONSE}",
            "--grader-command",
            f"{sys.executable} {GRADER}",
            "--output",
            str(report),
            "--pass-threshold",
            "1.0",
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teach-me-eval-") as directory:
        temporary = Path(directory)
        passing_suite = temporary / "passing.yaml"
        passing_suite.write_text(
            "suite: runner-pass\nversion: 1.0.0\ncases:\n"
            "  - id: passes\n    critical: true\n    prompt: OK\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        passing_report = temporary / "passing.json"
        passed = run(passing_suite, passing_report)
        if passed.returncode != 0:
            raise AssertionError(f"passing adapter run failed: {passed.stderr}")
        data = json.loads(passing_report.read_text(encoding="utf-8"))
        if data["summary"]["pass_rate"] != 1.0 or data["summary"]["critical_failures"]:
            raise AssertionError("passing report summary is incorrect")

        failing_suite = temporary / "failing.yaml"
        failing_suite.write_text(
            "suite: runner-fail\nversion: 1.0.0\ncases:\n"
            "  - id: fails\n    critical: true\n    prompt: FORCE_FAIL\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        failing_report = temporary / "failing.json"
        failed = run(failing_suite, failing_report)
        if failed.returncode != 1:
            raise AssertionError("critical failure did not fail the run")
        data = json.loads(failing_report.read_text(encoding="utf-8"))
        if data["summary"]["critical_failures"] != ["runner-fail/fails"]:
            raise AssertionError("critical failure was not reported")

    print("Teach Me behavioral eval runner tests passed (pass and critical-fail paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
