#!/usr/bin/env python3
"""Create summary-only feedback groups; never export free-text event content."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


GROUP_FIELDS = (
    "skill_version",
    "audience",
    "input_mode",
    "locale",
    "subject_category",
    "failure_category",
    "outcome",
)


def load_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid feedback ledger line {line_number}") from exc
        if event.get("contains_personal_data") is not False or event.get("consent") is not True:
            raise ValueError(f"unsafe feedback event at line {line_number}")
        events.append(event)
    return events


def aggregate(events: list[dict[str, Any]], minimum_group_size: int) -> dict[str, Any]:
    groups = Counter(tuple(event.get(field) for field in GROUP_FIELDS) for event in events)
    visible = []
    visible_count = 0
    for values, count in sorted(groups.items(), key=lambda item: tuple(str(value) for value in item[0])):
        if count < minimum_group_size:
            continue
        visible.append({**dict(zip(GROUP_FIELDS, values)), "count": count})
        visible_count += count
    return {
        "schema_version": "1.0.0",
        "minimum_group_size": minimum_group_size,
        "event_count": len(events),
        "published_group_count": len(visible),
        "suppressed_event_count": len(events) - visible_count,
        "groups": visible,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--minimum-group-size", type=int, default=3)
    args = parser.parse_args()
    if args.minimum_group_size < 2:
        parser.error("--minimum-group-size must be at least 2")
    try:
        summary = aggregate(load_events(args.input), args.minimum_group_size)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(args.output)
    except (OSError, ValueError) as exc:
        print(f"Feedback aggregation failed: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote privacy-minimized feedback summary to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
