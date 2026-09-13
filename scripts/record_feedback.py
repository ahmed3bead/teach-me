#!/usr/bin/env python3
"""Validate and append one consented, minimized feedback event to local NDJSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import ValidationError
except ImportError as exc:
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc


ROOT = Path(__file__).resolve().parents[1]


def load_event(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def existing_event_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    identifiers: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            identifiers.add(json.loads(line)["event_id"])
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ValueError(f"invalid feedback ledger line {line_number}") from exc
    return identifiers


def record(event: dict[str, Any], output: Path) -> None:
    schema = json.loads((ROOT / "schemas" / "feedback.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(event)
    if event["contains_personal_data"]:
        raise ValueError("feedback marked as containing personal data must not be recorded")
    if event["event_id"] in existing_event_ids(output):
        raise ValueError(f"duplicate feedback event_id: {event['event_id']}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8", newline="\n") as ledger:
        ledger.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("event", type=Path, help="one feedback JSON event")
    parser.add_argument("output", type=Path, help="local NDJSON ledger to append")
    args = parser.parse_args()
    try:
        record(load_event(args.event), args.output)
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        print(f"Feedback rejected: {exc}", file=sys.stderr)
        return 1
    print(f"Recorded minimized feedback event in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
