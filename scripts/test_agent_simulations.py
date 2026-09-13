#!/usr/bin/env python3
"""Exercise passing and blocking paths in the dynamic simulation runner."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_agent_simulations.py"
PYTHON = sys.executable
TEACHER = f"{PYTHON} {ROOT / 'fixtures/eval-adapters/fixture_teacher.py'}"
LEARNER = f"{PYTHON} {ROOT / 'fixtures/eval-adapters/fixture_learner.py'}"
GRADER = f"{PYTHON} {ROOT / 'fixtures/eval-adapters/fixture_simulation_grader.py'}"


def run(selected: str, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([
        PYTHON, str(RUNNER), "--simulation", selected, "--teacher-command", TEACHER,
        "--learner-command", LEARNER, "--grader-command", GRADER, "--output", str(output),
    ], cwd=ROOT, text=True, capture_output=True, check=False)


def main() -> int:
    suite_path = ROOT / "evals" / "simulations" / "fixture-runner.yaml"
    base = {
        "locale": "en", "critical": True, "max_turns": 2,
        "learner_persona": "Zero knowledge synthetic learner.", "learner_behaviors": ["Admit uncertainty."],
        "initial_request": "Teach this fictional rule.", "teaching_material": "A maps to B.",
        "baseline_task": "What does A map to?", "expected": ["learns only after teaching"],
        "minimum_gain": 0.6, "minimum_transfer": 0.8,
    }
    data = {"suite": "fixture-runner", "version": "1.0.0", "simulations": [
        {"id": "passing", **base, "transfer_task": "Apply the learned rule."},
        {"id": "blocking", **base, "transfer_task": "FORCE_FAIL"},
    ]}
    try:
        suite_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "report.json"
            passing = run("fixture-runner/passing", output)
            assert passing.returncode == 0, passing.stderr
            report = json.loads(output.read_text(encoding="utf-8"))
            assert report["summary"]["passed"] == 1
            assert report["results"][0]["gain"] == 1.0
            blocking = run("fixture-runner/blocking", output)
            assert blocking.returncode == 1, blocking.stderr
            report = json.loads(output.read_text(encoding="utf-8"))
            assert report["summary"]["critical_failures"] == ["fixture-runner/blocking"]
    finally:
        suite_path.unlink(missing_ok=True)
    print("Teach Me agent simulation tests passed (gain, transfer, critical blocking)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
