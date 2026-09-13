#!/usr/bin/env python3
"""Create, update, validate, and resume evidence-safe Teach Me sessions."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import ValidationError
except ImportError as exc:
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc

from validate_resume import validate as validate_resume
from validate_session import validate as validate_integrity


ROOT = Path(__file__).resolve().parents[1]
SESSION_FILE = "learning-session.json"
PROGRESS_FILE = "progress.json"
TRANSACTION_FILE = ".teach-me-transaction.json"
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
STATE_RANK = {
    "not-started": 0,
    "introduced": 1,
    "practised-with-help": 2,
    "applied-independently": 3,
    "transferred": 4,
    "retained": 5,
}
HELP_LEVEL = {"modelled": 6, "scaffolded": 4, "hint": 2, "none": 0}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def validate_schema(value: dict[str, Any], name: str) -> None:
    schema = read_json(ROOT / "schemas" / f"{name}.schema.json")
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)


def recover_transaction(directory: Path) -> None:
    transaction_path = directory / TRANSACTION_FILE
    if not transaction_path.exists():
        return
    transaction = read_json(transaction_path)
    session = transaction.get("session")
    progress = transaction.get("progress")
    if transaction.get("version") != 1 or not isinstance(session, dict) or not isinstance(progress, dict):
        raise ValueError("invalid pending session transaction; manual recovery required")
    validate_schema(session, "learning-session")
    validate_schema(progress, "progress")
    if session["session_id"] != progress["session_id"]:
        raise ValueError("pending transaction has mismatched session identifiers")
    atomic_json(directory / PROGRESS_FILE, progress)
    atomic_json(directory / SESSION_FILE, session)
    transaction_path.unlink()


def commit_pair(directory: Path, session: dict[str, Any], progress: dict[str, Any]) -> None:
    transaction_path = directory / TRANSACTION_FILE
    atomic_json(transaction_path, {"version": 1, "session": session, "progress": progress})
    atomic_json(directory / PROGRESS_FILE, progress)
    atomic_json(directory / SESSION_FILE, session)
    transaction_path.unlink()


@contextmanager
def session_lock(directory: Path) -> Iterator[None]:
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / ".teach-me.lock"
    with lock_path.open("a+b") as lock:
        if os.name == "nt":
            import msvcrt

            if lock.tell() == 0:
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("observed_at must include a timezone")
    return parsed.astimezone(timezone.utc)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def require_safe_id(value: str, label: str) -> None:
    if not SAFE_ID.fullmatch(value):
        raise ValueError(f"{label} must be a non-sensitive safe identifier")


def initialize(args: argparse.Namespace) -> None:
    for value, label in (
        (args.session_id, "session_id"),
        (args.subject_slug, "subject_slug"),
        (args.objective_id, "objective_id"),
        (args.module_id, "module_id"),
        (args.lesson_id, "lesson_id"),
    ):
        require_safe_id(value, label)
    if args.input_mode == "source-grounded" and not args.source_id:
        raise ValueError("source-grounded sessions require at least one --source-id")
    for source_id in args.source_id:
        require_safe_id(source_id, "source_id")

    session_path = args.directory / SESSION_FILE
    progress_path = args.directory / PROGRESS_FILE
    with session_lock(args.directory):
        recover_transaction(args.directory)
        if session_path.exists() or progress_path.exists():
            raise ValueError("session files already exist; refuse to overwrite")
        session = {
            "version": "1.0.0",
            "revision": 0,
            "session_id": args.session_id,
            "subject_slug": args.subject_slug,
            "audience": args.audience,
            "input_mode": args.input_mode,
            "language": args.language,
            "goal": args.goal,
            "constraints": args.constraint,
            "source_ids": args.source_id,
            "curriculum_id": None,
            "objectives": [
                {
                    "objective_id": args.objective_id,
                    "capability": args.capability,
                    "origin": "learner" if args.audience == "learner" else "educator",
                    "prerequisite_objective_ids": [],
                    "source_ids": args.source_id,
                    "source_refs": [],
                    "mastery_evidence": args.mastery_evidence,
                    "state": "not-started",
                    "lesson_ids": [args.lesson_id],
                    "assessment_ids": [],
                    "next_action": args.next_action,
                }
            ],
            "checkpoint": {
                "active_objective_id": args.objective_id,
                "active_module_id": args.module_id,
                "active_lesson_id": args.lesson_id,
                "latest_state": "not-started",
                "evidence": "No learner-performance evidence recorded yet.",
                "blocker_or_misconception": None,
                "strategy_context": None,
                "next_action": args.next_action,
                "review_due_at": None,
                "updated_at": iso_now(),
            },
        }
        progress = {"version": "1.0.0", "session_id": args.session_id, "records": []}
        validate_schema(session, "learning-session")
        validate_schema(progress, "progress")
        commit_pair(args.directory, session, progress)


def highest_non_retention(records: list[dict[str, Any]], objective_id: str) -> str:
    states = [
        item["state"]
        for item in records
        if item.get("objective_id") == objective_id and item.get("state") != "retained"
    ]
    return max(states, key=lambda state: STATE_RANK[state], default="introduced")


def derive_state(
    *,
    current: str,
    evidence_type: str,
    support_level: str,
    outcome: str,
    objective_id: str,
    observed_at: datetime,
    task_fingerprint: str,
    records: list[dict[str, Any]],
) -> str:
    if outcome != "successful":
        if evidence_type == "delayed-retrieval":
            return highest_non_retention(records, objective_id)
        return "introduced" if current == "not-started" else current
    if support_level == "modelled":
        candidate = "introduced"
    elif support_level in {"scaffolded", "hint"}:
        candidate = "practised-with-help"
    elif evidence_type == "transfer":
        candidate = "transferred"
    elif evidence_type == "delayed-retrieval":
        prior = [
            item
            for item in records
            if item.get("objective_id") == objective_id
            and item.get("outcome") == "successful"
            and item.get("support_level") == "none"
            and item.get("state") in {"applied-independently", "transferred", "retained"}
            and item.get("task_fingerprint") != task_fingerprint
            and parse_datetime(item["observed_at"]) <= observed_at - timedelta(hours=24)
        ]
        if not prior:
            raise ValueError("retained requires fresh successful retrieval at least 24 hours after independent evidence")
        candidate = "retained"
    else:
        candidate = "applied-independently"
    return max((current, candidate), key=lambda state: STATE_RANK[state])


def record_evidence(args: argparse.Namespace) -> str:
    observed = parse_datetime(args.observed_at or iso_now())
    with session_lock(args.directory):
        recover_transaction(args.directory)
        session_path = args.directory / SESSION_FILE
        progress_path = args.directory / PROGRESS_FILE
        session = read_json(session_path)
        progress = read_json(progress_path)
        validate_schema(session, "learning-session")
        validate_schema(progress, "progress")
        if session["revision"] != args.expected_revision:
            raise ValueError(
                f"revision conflict: expected {args.expected_revision}, current {session['revision']}"
            )
        if progress["session_id"] != session["session_id"]:
            raise ValueError("progress session_id does not match")
        if any(item["record_id"] == args.record_id for item in progress["records"]):
            raise ValueError(f"duplicate record_id: {args.record_id}")
        objective = next(
            (item for item in session["objectives"] if item["objective_id"] == args.objective_id),
            None,
        )
        if objective is None:
            raise ValueError(f"unknown objective_id: {args.objective_id}")
        state = derive_state(
            current=objective["state"],
            evidence_type=args.evidence_type,
            support_level=args.support_level,
            outcome=args.outcome,
            objective_id=args.objective_id,
            observed_at=observed,
            task_fingerprint=args.task_fingerprint,
            records=progress["records"],
        )
        record = {
            "record_id": args.record_id,
            "objective_id": args.objective_id,
            "objective": objective["capability"],
            "lesson_id": args.lesson_id,
            "assessment_id": args.assessment_id,
            "evidence_type": args.evidence_type,
            "support_level": args.support_level,
            "outcome": args.outcome,
            "task_fingerprint": args.task_fingerprint,
            "state": state,
            "evidence": args.evidence,
            "help_level": HELP_LEVEL[args.support_level],
            "observed_at": observed.isoformat().replace("+00:00", "Z"),
            "next_action": args.next_action,
        }
        progress["records"].append(record)
        objective["state"] = state
        objective["next_action"] = args.next_action
        checkpoint = session["checkpoint"]
        checkpoint.update(
            {
                "active_objective_id": args.objective_id,
                "active_lesson_id": args.lesson_id or checkpoint.get("active_lesson_id"),
                "latest_state": state,
                "evidence": args.evidence,
                "next_action": args.next_action,
                "updated_at": record["observed_at"],
            }
        )
        session["revision"] += 1
        validate_schema(progress, "progress")
        validate_schema(session, "learning-session")
        errors = validate_integrity(session, progress=progress)
        if errors:
            raise ValueError("; ".join(errors))
        commit_pair(args.directory, session, progress)
        return state


def resume(directory: Path) -> dict[str, Any]:
    with session_lock(directory):
        recover_transaction(directory)
        session = read_json(directory / SESSION_FILE)
        progress = read_json(directory / PROGRESS_FILE)
        validate_schema(session, "learning-session")
        validate_schema(progress, "progress")
        errors = validate_integrity(session, progress=progress)
        if errors:
            raise ValueError("; ".join(errors))
        checkpoint = session["checkpoint"]
        if not checkpoint.get("active_module_id") or not checkpoint.get("active_lesson_id"):
            raise ValueError("resume requires active_module_id and active_lesson_id in the checkpoint")
        code = ":".join(
            (
                "TEACH-ME",
                "v2",
                session["session_id"],
                session["subject_slug"],
                session["language"],
                checkpoint["active_module_id"],
                checkpoint["active_lesson_id"],
            )
        )
        parsed = validate_resume(code)
        if parsed["status"] != "valid":
            raise ValueError(f"generated invalid resume code: {parsed['errors']}")
        return {
            "resume_code": code,
            "revision": session["revision"],
            "goal": session["goal"],
            "checkpoint": checkpoint,
            "mastery_evidence": False,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init")
    init.add_argument("directory", type=Path)
    init.add_argument("--session-id", required=True)
    init.add_argument("--subject-slug", required=True)
    init.add_argument("--audience", choices=("learner", "educator"), required=True)
    init.add_argument("--input-mode", choices=("topic-led", "source-grounded"), required=True)
    init.add_argument("--language", choices=("ar-MSA", "ar-EG", "en", "mixed"), required=True)
    init.add_argument("--goal", required=True)
    init.add_argument("--constraint", action="append", default=[])
    init.add_argument("--source-id", action="append", default=[])
    init.add_argument("--objective-id", required=True)
    init.add_argument("--capability", required=True)
    init.add_argument("--mastery-evidence", action="append", required=True)
    init.add_argument("--module-id", required=True)
    init.add_argument("--lesson-id", required=True)
    init.add_argument("--next-action", required=True)

    record = commands.add_parser("record-evidence")
    record.add_argument("directory", type=Path)
    record.add_argument("--expected-revision", type=int, required=True)
    record.add_argument("--record-id", required=True)
    record.add_argument("--objective-id", required=True)
    record.add_argument("--lesson-id")
    record.add_argument("--assessment-id")
    record.add_argument(
        "--evidence-type",
        choices=("recognition", "explanation", "prediction", "application", "transfer", "delayed-retrieval"),
        required=True,
    )
    record.add_argument("--support-level", choices=("modelled", "scaffolded", "hint", "none"), required=True)
    record.add_argument("--outcome", choices=("successful", "partial", "unsuccessful"), required=True)
    record.add_argument("--task-fingerprint", required=True)
    record.add_argument("--evidence", required=True)
    record.add_argument("--observed-at")
    record.add_argument("--next-action", required=True)

    inspect = commands.add_parser("resume")
    inspect.add_argument("directory", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "init":
            initialize(args)
            print(f"Created Teach Me session in {args.directory}")
        elif args.command == "record-evidence":
            state = record_evidence(args)
            print(json.dumps({"state": state}, ensure_ascii=False))
        else:
            print(json.dumps(resume(args.directory), ensure_ascii=False, indent=2))
    except (OSError, ValueError, json.JSONDecodeError, ValidationError) as exc:
        print(f"Session operation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
