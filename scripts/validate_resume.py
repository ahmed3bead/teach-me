#!/usr/bin/env python3
"""Validate a TEACH-ME portable resume code without treating it as mastery evidence."""

from __future__ import annotations

import json
import re
import sys


STATES = {
    "not-started",
    "introduced",
    "practised-with-help",
    "applied-independently",
    "transferred",
    "retained",
}
LANGUAGES = {"ar-MSA", "ar-EG", "en", "mixed"}
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def result(status: str, fields: dict[str, str] | None = None, errors: list[str] | None = None) -> dict[str, object]:
    return {
        "status": status,
        "fields": fields or {},
        "errors": errors or [],
        "mastery_evidence": False,
    }


def validate(code: str) -> dict[str, object]:
    parts = code.strip().split(":")
    if len(parts) < 2 or parts[0] != "TEACH-ME":
        return result("malformed", errors=["expected TEACH-ME prefix"])
    if parts[1] != "v1":
        return result("unsupported-version", errors=["only v1 is supported"])

    names = ("subject", "language", "module", "lesson", "state")
    values = parts[2:]
    parsed = {name: value for name, value in zip(names, values) if value}
    if len(parts) != 7 or len(parsed) != 5:
        return result("partial", fields=parsed, errors=["expected five non-empty locator fields after v1"])

    errors: list[str] = []
    for name in ("subject", "module", "lesson"):
        if not SAFE_ID.fullmatch(parsed[name]):
            errors.append(f"invalid {name}")
    if parsed["language"] not in LANGUAGES:
        errors.append("unsupported language")
    if parsed["state"] not in STATES:
        errors.append("unsupported state")
    return result("malformed", errors=errors) if errors else result("valid", fields=parsed)


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps(result("malformed", errors=["provide exactly one resume code"])))
        return 1
    output = validate(sys.argv[1])
    print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    return 0 if output["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
