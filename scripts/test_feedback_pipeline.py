#!/usr/bin/env python3
"""Test consent, personal-data, duplicate, and aggregation feedback gates."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path

from aggregate_feedback import aggregate, load_events
from record_feedback import load_event, record
from jsonschema.exceptions import ValidationError


ROOT = Path(__file__).resolve().parents[1]


def must_reject(event: dict[str, object], ledger: Path, fragment: str) -> None:
    try:
        record(event, ledger)
    except (ValueError, ValidationError) as exc:
        if fragment not in str(exc):
            raise AssertionError(f"unexpected rejection: {exc}") from exc
    else:
        raise AssertionError(f"expected rejection containing {fragment!r}")


def main() -> int:
    base = load_event(ROOT / "fixtures" / "session" / "feedback.json")
    with tempfile.TemporaryDirectory(prefix="teach-me-feedback-") as directory:
        ledger = Path(directory) / "events.ndjson"
        for number in range(1, 4):
            event = copy.deepcopy(base)
            event["event_id"] = f"EVT{number}"
            record(event, ledger)

        duplicate = copy.deepcopy(base)
        duplicate["event_id"] = "EVT1"
        must_reject(duplicate, ledger, "duplicate")

        personal = copy.deepcopy(base)
        personal["event_id"] = "EVT4"
        personal["contains_personal_data"] = True
        must_reject(personal, ledger, "personal data")

        no_consent = copy.deepcopy(base)
        no_consent["event_id"] = "EVT5"
        no_consent["consent"] = False
        must_reject(no_consent, ledger, "True was expected")

        summary = aggregate(load_events(ledger), minimum_group_size=3)
        if summary["event_count"] != 3 or summary["published_group_count"] != 1:
            raise AssertionError("three-event feedback group was not aggregated")
        if "reproducible_summary" in json.dumps(summary):
            raise AssertionError("free text leaked into feedback aggregate")

    print("Teach Me feedback pipeline tests passed (consent, privacy, dedupe, aggregation)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
