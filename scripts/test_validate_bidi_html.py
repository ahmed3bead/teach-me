#!/usr/bin/env python3
"""Positive and negative tests for Arabic/English direction isolation."""

from pathlib import Path

from validate_bidi_html import validate


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    valid = validate(ROOT / "fixtures" / "bidi" / "valid.html")
    if valid:
        raise AssertionError(f"valid bidi fixture failed: {valid!r}")
    template = validate(ROOT / "templates" / "bidi-learning-pack.html", check_links=False)
    if template:
        raise AssertionError(f"bidi template failed: {template!r}")
    invalid = validate(ROOT / "fixtures" / "bidi" / "invalid-unisolated.html")
    if not any("unisolated" in error for error in invalid):
        raise AssertionError(f"unisolated LTR content was accepted: {invalid!r}")
    print("Teach Me bidi HTML tests passed (isolated and broken fixtures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
