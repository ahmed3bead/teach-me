#!/usr/bin/env python3
"""End-to-end tests for session creation, evidence derivation, locking, and resume."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANAGER = ROOT / "scripts" / "session_manager.py"


def call(arguments: list[str], expected: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [sys.executable, str(MANAGER), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != expected:
        raise AssertionError(
            f"expected exit {expected}, got {completed.returncode}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed


def evidence(directory: Path, revision: int, record_id: str, kind: str, support: str, outcome: str, task: str, observed: str, expected: int = 0) -> subprocess.CompletedProcess[str]:
    return call(
        [
            "record-evidence",
            str(directory),
            "--expected-revision",
            str(revision),
            "--record-id",
            record_id,
            "--objective-id",
            "OBJ1",
            "--lesson-id",
            "LES1",
            "--evidence-type",
            kind,
            "--support-level",
            support,
            "--outcome",
            outcome,
            "--task-fingerprint",
            task,
            "--evidence",
            "Observable fixture evidence",
            "--observed-at",
            observed,
            "--next-action",
            "Continue with the next bounded task",
        ],
        expected,
    )


def state(directory: Path) -> tuple[int, str, int]:
    session = json.loads((directory / "learning-session.json").read_text(encoding="utf-8"))
    progress = json.loads((directory / "progress.json").read_text(encoding="utf-8"))
    return session["revision"], session["objectives"][0]["state"], len(progress["records"])


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teach-me-session-") as temporary:
        directory = Path(temporary) / "learner"
        call(
            [
                "init",
                str(directory),
                "--session-id",
                "S001",
                "--subject-slug",
                "prompts",
                "--audience",
                "learner",
                "--input-mode",
                "topic-led",
                "--language",
                "ar-EG",
                "--goal",
                "Write a clear prompt",
                "--objective-id",
                "OBJ1",
                "--capability",
                "Write a prompt with task, context, constraints, and output",
                "--mastery-evidence",
                "A fresh independent prompt passes the rubric",
                "--module-id",
                "MOD1",
                "--lesson-id",
                "LES1",
                "--next-action",
                "Read the worked example",
            ]
        )
        if state(directory) != (0, "not-started", 0):
            raise AssertionError("initial state is incorrect")
        initialized = json.loads((directory / "learning-session.json").read_text(encoding="utf-8"))
        if initialized["language"] != "ar-MSA":
            raise AssertionError("legacy ar-EG input was not stored canonically as ar-MSA")

        resumed = json.loads(call(["resume", str(directory)]).stdout)
        if resumed["resume_code"] != "TEACH-ME:v2:S001:prompts:ar-MSA:MOD1:LES1":
            raise AssertionError("resume locator is incorrect")
        if resumed["mastery_evidence"] is not False:
            raise AssertionError("resume locator became mastery evidence")

        evidence(directory, 0, "REC1", "recognition", "modelled", "successful", "task-1", "2026-09-01T10:00:00Z")
        if state(directory) != (1, "introduced", 1):
            raise AssertionError("modelled evidence state is incorrect")

        duplicate = evidence(directory, 1, "REC1", "application", "none", "successful", "task-2", "2026-09-01T11:00:00Z", expected=1)
        if "duplicate record_id" not in duplicate.stderr or state(directory) != (1, "introduced", 1):
            raise AssertionError("duplicate record changed state")

        conflict = evidence(directory, 0, "REC2", "application", "none", "successful", "task-2", "2026-09-01T11:00:00Z", expected=1)
        if "revision conflict" not in conflict.stderr:
            raise AssertionError("stale revision was not rejected")

        evidence(directory, 1, "REC2", "application", "none", "successful", "task-2", "2026-09-01T11:00:00Z")
        if state(directory) != (2, "applied-independently", 2):
            raise AssertionError("independent application state is incorrect")

        early = evidence(directory, 2, "REC3", "delayed-retrieval", "none", "successful", "task-3", "2026-09-01T20:00:00Z", expected=1)
        if "at least 24 hours" not in early.stderr or state(directory) != (2, "applied-independently", 2):
            raise AssertionError("early retention changed state")

        repeated = evidence(directory, 2, "REC3", "delayed-retrieval", "none", "successful", "task-2", "2026-09-02T12:00:00Z", expected=1)
        if "at least 24 hours" not in repeated.stderr:
            raise AssertionError("repeated retention task was accepted")

        evidence(directory, 2, "REC3", "delayed-retrieval", "none", "successful", "task-3", "2026-09-02T12:00:00Z")
        if state(directory) != (3, "retained", 3):
            raise AssertionError("valid delayed retrieval was not retained")

        evidence(directory, 3, "REC4", "delayed-retrieval", "none", "unsuccessful", "task-4", "2026-09-05T12:00:00Z")
        if state(directory) != (4, "applied-independently", 4):
            raise AssertionError("failed later retrieval did not preserve only independent evidence")
        session = json.loads((directory / "learning-session.json").read_text(encoding="utf-8"))
        progress = json.loads((directory / "progress.json").read_text(encoding="utf-8"))
        session["revision"] = 5
        session["checkpoint"]["evidence"] = "Recovered transaction evidence"
        (directory / ".teach-me-transaction.json").write_text(
            json.dumps({"version": 1, "session": session, "progress": progress}), encoding="utf-8"
        )
        (directory / "learning-session.json").unlink()
        recovered = json.loads(call(["resume", str(directory)]).stdout)
        if recovered["revision"] != 5 or (directory / ".teach-me-transaction.json").exists():
            raise AssertionError("pending transaction was not recovered")
        if list(directory.glob("*.tmp")):
            raise AssertionError("temporary state files leaked")

    print("Teach Me session manager tests passed (init, resume, evidence, conflicts, retention, recovery)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
