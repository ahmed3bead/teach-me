#!/usr/bin/env python3
"""Exercise passing and blocking paths in the dynamic simulation runner."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock

import yaml
import run_agent_simulations as runner


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
    criterion = [{"evidence_scope": "transfer", "criterion": "observable evidence is required"}]
    for invalid_reason in (None, "", "   ", 7):
        try:
            runner.grade_results(
                {"results": [{"passed": True, "reason": invalid_reason}]}, criterion, "fixture"
            )
        except RuntimeError:
            pass
        else:
            raise AssertionError("simulation runner accepted a missing evidence reason")

    summary = runner.summarize_rows(
        [
            {"simulation_id": "one", "critical": True, "evaluation_status": "completed", "passed": True},
            {"simulation_id": "two", "critical": False, "evaluation_status": "completed", "passed": False},
            {"simulation_id": "three", "critical": True, "evaluation_status": "failed", "passed": False},
        ],
        simulations=4,
        threshold=0.9,
    )
    assert summary == {
        "simulations": 4,
        "completed": 2,
        "passed": 1,
        "failed": 2,
        "pass_rate": 1 / 3,
        "threshold": 0.9,
        "critical_failures": ["three"],
    }

    suite_path = ROOT / "evals" / "simulations" / "fixture-runner.yaml"
    base = {
        "locale": "en", "critical": True, "max_turns": 2,
        "learner_persona": "Zero knowledge synthetic learner.", "learner_behaviors": ["Admit uncertainty."],
        "initial_request": "Teach this fictional rule.", "teaching_material": "A maps to B.",
        "baseline_task": "What does A map to?",
        "expected": [{"evidence_scope": "transfer", "criterion": "learns only after teaching"}],
        "minimum_gain": 0.6, "minimum_transfer": 0.8,
    }
    data = {"suite": "fixture-runner", "version": "1.0.0", "simulations": [
        {"id": "passing", **base, "transfer_task": "Apply the learned rule."},
        {"id": "blocking", **base, "transfer_task": "FORCE_FAIL"},
        {"id": "guard-blocking", **base, "transfer_task": "Apply the learned rule."},
        {"id": "artifact-blocking", **base, "transfer_task": "Apply the learned rule."},
        {"id": "grader-failure", **base, "transfer_task": "Apply the learned rule."},
        {"id": "max-turn", **base, "max_turns": 1, "transfer_task": "Apply the learned rule."},
    ]}
    try:
        suite_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "report.json"
            passing = run("fixture-runner/passing", output)
            assert passing.returncode == 0, passing.stderr
            report = json.loads(output.read_text(encoding="utf-8"))
            assert report["summary"]["passed"] == 1
            assert report["run_status"] == "completed"
            assert report["results"][0]["gain"] == 1.0
            assert all(item["passed"] for item in report["results"][0]["deterministic_guards"])
            assert report["results"][0]["learner_adapter_calls"][0]["attempts"] == 1
            assert report["results"][0]["teacher_adapter_calls"][0]["phase"] == "teach"
            assert report["results"][0]["transcript"][-1] == {
                "role": "learner",
                "content": "I understand the complete unit.",
            }
            blocking = run("fixture-runner/blocking", output)
            assert blocking.returncode == 1, blocking.stderr
            report = json.loads(output.read_text(encoding="utf-8"))
            assert report["summary"]["critical_failures"] == ["fixture-runner/blocking"]
            guarded = run("fixture-runner/guard-blocking", output)
            assert guarded.returncode == 1, guarded.stderr
            report = json.loads(output.read_text(encoding="utf-8"))
            assessment = next(
                item
                for item in report["results"][0]["deterministic_guards"]
                if item["guard"] == "assessment requires prior learner opt-in"
            )
            assert not assessment["passed"]
            artifact = run("fixture-runner/artifact-blocking", output)
            assert artifact.returncode == 1, artifact.stderr
            report = json.loads(output.read_text(encoding="utf-8"))
            utterance = next(
                item
                for item in report["results"][0]["deterministic_guards"]
                if item["guard"] == "learner output contains only learner utterances"
            )
            assert not utterance["passed"]
            output.write_text('{"run_status":"completed","marker":"stale"}\n', encoding="utf-8")
            grader_failure = run("fixture-runner/grader-failure", output)
            assert grader_failure.returncode == 2, grader_failure.stderr
            report = json.loads(output.read_text(encoding="utf-8"))
            assert report["run_status"] == "failed"
            assert report["failure_stage"] == "grading"
            assert report["model_role"] == "grader"
            assert report["invocation_attempt_count"] == 1
            assert report["results"][0]["transcript"][-1]["role"] == "learner"
            assert report["results"][0]["transfer_answer"] == "fixture-learned"
            assert report["results"][0]["deterministic_guards"]
            assert "marker" not in report
            assert not output.with_suffix(output.suffix + ".tmp").exists()
            max_turn = run("fixture-runner/max-turn", output)
            assert max_turn.returncode == 0, max_turn.stderr
            report = json.loads(output.read_text(encoding="utf-8"))
            assert report["results"][0]["transcript"][-1]["role"] == "learner"

            atomic = Path(temporary) / "atomic.json"
            runner.write_report(atomic, {"generation": "old"})
            with mock.patch.object(Path, "replace", side_effect=OSError("interrupted replacement")):
                try:
                    runner.write_report(atomic, {"generation": "new"})
                except OSError:
                    pass
                else:
                    raise AssertionError("atomic replacement failure should propagate")
            assert json.loads(atomic.read_text(encoding="utf-8")) == {"generation": "old"}
    finally:
        suite_path.unlink(missing_ok=True)
    print("Teach Me agent simulation tests passed (gain, transfer, critical blocking)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
