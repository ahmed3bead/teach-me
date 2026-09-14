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
    valid_text = (ROOT / "fixtures" / "bidi" / "valid.html").read_text(encoding="utf-8")
    if 'bdi[dir="ltr"] { white-space: nowrap; }' not in valid_text:
        raise AssertionError("multiword LTR terms can wrap across PDF lines")
    for term in ("API", "Replication", "Contract Test", "Prompt", "Database"):
        if f'<bdi dir="ltr">{term}</bdi>' not in valid_text:
            raise AssertionError(f"technical term lacks explicit LTR isolation: {term}")
    invalid = validate(ROOT / "fixtures" / "bidi" / "invalid-unisolated.html")
    if not any("unisolated" in error for error in invalid):
        raise AssertionError(f"unisolated LTR content was accepted: {invalid!r}")
    print("Teach Me bidi HTML tests passed (isolated and broken fixtures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
