#!/usr/bin/env python3
"""Validate a portable Teach Me locator without treating it as mastery evidence."""

from __future__ import annotations

import json
import re
import sys


LANGUAGES = {"ar-MSA", "ar-EG", "en", "mixed"}
LEGACY_STATES = {
    "not-started",
    "introduced",
    "practised-with-help",
    "applied-independently",
    "transferred",
    "retained",
}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def result(
    status: str,
    fields: dict[str, str] | None = None,
    errors: list[str] | None = None,
    legacy_claimed_state: str | None = None,
) -> dict[str, object]:
    output: dict[str, object] = {
        "status": status,
        "fields": fields or {},
        "errors": errors or [],
        "mastery_evidence": False,
    }
    if legacy_claimed_state is not None:
        output["legacy_claimed_state"] = legacy_claimed_state
    return output


def parse_fields(parts: list[str], names: tuple[str, ...], version: str) -> tuple[dict[str, str], dict[str, object] | None]:
    values = parts[2:]
    parsed = {name: value for name, value in zip(names, values) if value}
    if len(parts) != len(names) + 2 or len(parsed) != len(names):
        return parsed, result(
            "partial",
            fields=parsed,
            errors=[f"expected {len(names)} non-empty locator fields after {version}"],
        )
    return parsed, None


def invalid_ids(parsed: dict[str, str], names: tuple[str, ...]) -> list[str]:
    return [f"invalid {name}" for name in names if not SAFE_ID.fullmatch(parsed[name])]


def validate(code: str) -> dict[str, object]:
    parts = code.strip().split(":")
    if len(parts) < 2 or parts[0] != "TEACH-ME":
        return result("malformed", errors=["expected TEACH-ME prefix"])

    version = parts[1]
    if version == "v2":
        names = ("session_id", "subject", "language", "module", "lesson")
        parsed, early = parse_fields(parts, names, version)
        if early:
            return early
        errors = invalid_ids(parsed, ("session_id", "subject", "module", "lesson"))
        if parsed["language"] not in LANGUAGES:
            errors.append("unsupported language")
        return result("malformed", errors=errors) if errors else result("valid", fields=parsed)

    if version == "v1":
        names = ("subject", "language", "module", "lesson", "state")
        parsed, early = parse_fields(parts, names, version)
        if early:
            return early
        errors = invalid_ids(parsed, ("subject", "module", "lesson"))
        if parsed["language"] not in LANGUAGES:
            errors.append("unsupported language")
        if parsed["state"] not in LEGACY_STATES:
            errors.append("unsupported legacy state")
        if errors:
            return result("malformed", errors=errors)
        state = parsed.pop("state")
        return result(
            "legacy-valid",
            fields=parsed,
            errors=["v1 state is an unverified historical claim and was not restored"],
            legacy_claimed_state=state,
        )

    return result("unsupported-version", errors=["supported versions are v2 and legacy v1"])


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps(result("malformed", errors=["provide exactly one resume code"])))
        return 1
    output = validate(sys.argv[1])
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0 if output["status"] in {"valid", "legacy-valid"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
