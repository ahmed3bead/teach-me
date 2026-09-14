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
from assessment_intent import legacy_assessment_intent, validate_assessment_intent
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
    lifecycle = [
        ("I need a different explanation.", "none"),
        ("لا أريد الأسئلة الآن.", "decline"),
        ("أختار الفحص القصير.", "accept"),
        ("This is my answer.", "none"),
    ]
    assert [validate_assessment_intent(*event) for event in lifecycle] == [
        "none", "decline", "accept", "none"
    ]
    for utterance in (
        "أختار الفحص.", "نعم، أوافق على الفحص.",
        "  أختارُ   الفحصَ!  ", "I choose the quiz.",
        "Yes, I accept the check.", "READY FOR THE TEST!",
    ):
        assert legacy_assessment_intent(utterance) == "accept", utterance
    for utterance in (
        "لا أختار الفحص.", "لا، أوافق.", "لا أريد الأسئلة الآن.",
        "لن أوافق على الفحص.", "لم أوافق على الاختبار.",
        "غير مستعد للأسئلة.", "لَسْتُ مُسْتَعِدًّا للاختبار.", "مش مستعد للتمارين.",
        "لا أظن أنني مستعد للاختبار.",
        "Not ready for the quiz.", "I do not want the test.", "I DON'T WANT QUESTIONS.",
        "I will not accept the check.", "Won't accept the quiz.",
        "I did not agree to the test.", "I never agreed to questions.",
        "No quiz.", "Do not test me now.", "Please do not give me a quiz.",
        "I won't be ready for the check.",
        "No, I accept the quiz.", "PLEASE DO NOT START THE QUIZ!",
    ):
        assert legacy_assessment_intent(utterance) == "decline", utterance
        try:
            validate_assessment_intent(utterance, "accept")
        except ValueError:
            pass
        else:
            raise AssertionError(f"negated consent was accepted: {utterance}")
    for utterance in (
        "readiness for the quiz", "noteworthy example", "classification test",
        "المستعدون للتعلم", "الاختبارية", "أوافقون على الفكرة",
        "Please do.", "Let's do it.", "Maybe I am ready someday.",
    ):
        assert legacy_assessment_intent(utterance) == "none", utterance
    for invalid in (None, True, "", "unknown", "ACCEPT"):
        try:
            validate_assessment_intent("A neutral learner utterance.", invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid assessment intent was accepted: {invalid!r}")
    for result in (
        {"message": "An old live-adapter message.", "done": False},
        {"utterance": "A learner message."},
        {"utterance": "I do not agree to the quiz.", "assessment_intent": "accept"},
        {"utterance": 7, "assessment_intent": "none"},
    ):
        try:
            runner.required_learner_event(result, "fixture")
        except RuntimeError:
            pass
        else:
            raise AssertionError(f"malformed learner event was accepted: {result!r}")
    for malformed_done in ({}, {"done": None}, {"done": "false"}, {"done": 0}, {"done": 1}):
        try:
            runner.required_done(malformed_done, "fixture")
        except RuntimeError:
            pass
        else:
            raise AssertionError(f"malformed done was accepted: {malformed_done!r}")
    assert runner.required_done({"done": False}, "fixture") is False
    assert runner.required_done({"done": True}, "fixture") is True

    registered = yaml.safe_load(
        (ROOT / "evals" / "simulations" / "zero-knowledge-fictional.yaml").read_text(encoding="utf-8")
    )
    luma = next(item for item in registered["simulations"] if item["id"] == "luma-routing-ar-msa")
    assert [item["expected_assessment_intent"] for item in luma["learner_behaviors"]] == [
        "none", "decline", "accept", "none"
    ]
    behavior_text = " ".join(item["instruction"] for item in luma["learner_behaviors"])
    for required in ("unsure which rule", "continue the explanation", "shown in another form"):
        assert required in behavior_text
    for forbidden in (
        "route N", "route H", "route Y", "route Q", "expected routes", "answer key",
        "materially different representation", "without pressure", "grader criterion",
        "assessment contract", "expected behavior",
    ):
        assert forbidden not in behavior_text

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
        {"id": "missing-intent", **base, "transfer_task": "Apply the learned rule."},
        {"id": "missing-done", **base, "transfer_task": "Apply the learned rule."},
        {"id": "contradictory-intent", **base, "transfer_task": "Apply the learned rule."},
        {
            "id": "early-done", **base,
            "learner_behaviors": ["First required behavior.", "Second required behavior."],
            "transfer_task": "Apply the learned rule.",
        },
        {
            "id": "one-remaining-max-turn", **base, "max_turns": 1,
            "learner_behaviors": ["First required behavior.", "Second required behavior."],
            "transfer_task": "Apply the learned rule.",
        },
        {
            "id": "two-remaining-max-turn", **base, "max_turns": 1,
            "learner_behaviors": [
                "First required behavior.", "Second required behavior.", "Third required behavior."
            ],
            "transfer_task": "Apply the learned rule.",
        },
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
                "assessment_intent": "none",
            }
            assert all(
                "assessment_intent" in item
                for item in report["results"][0]["transcript"]
                if item["role"] == "learner"
            )
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
            for simulation_id in ("missing-intent", "missing-done", "contradictory-intent"):
                invalid = run(f"fixture-runner/{simulation_id}", output)
                assert invalid.returncode == 2, invalid.stderr
                report = json.loads(output.read_text(encoding="utf-8"))
                assert report["run_status"] == "failed"
                assert report["failure_stage"] == "learner_turn_1"
                assert report["results"][0]["passed"] is False
                assert report["error"]["type"] == "RuntimeError"
            early_done = run("fixture-runner/early-done", output)
            assert early_done.returncode == 2, early_done.stderr
            report = json.loads(output.read_text(encoding="utf-8"))
            assert report["failure_stage"] == "lifecycle"
            assert len(report["results"][0]["remaining_lifecycle_events"]) == 1
            assert report["results"][0]["transcript"][-1]["role"] == "learner"
            for simulation_id, remaining_count in (
                ("one-remaining-max-turn", 1), ("two-remaining-max-turn", 2)
            ):
                incomplete = run(f"fixture-runner/{simulation_id}", output)
                assert incomplete.returncode == 2, incomplete.stderr
                report = json.loads(output.read_text(encoding="utf-8"))
                assert report["run_status"] == "failed"
                assert report["failure_stage"] == "lifecycle"
                assert report["results"][0]["transfer_answer"] is None
                assert len(report["results"][0]["remaining_lifecycle_events"]) == remaining_count
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
