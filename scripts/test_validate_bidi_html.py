#!/usr/bin/env python3
"""Positive and negative tests for Arabic/English direction isolation."""

import tempfile
from pathlib import Path

from validate_bidi_html import validate


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    valid = validate(ROOT / "fixtures" / "bidi" / "valid.html")
    if valid:
        raise AssertionError(f"valid bidi fixture failed: {valid!r}")
    printable_path = ROOT / "fixtures" / "bidi" / "printable.html"
    printable = validate(printable_path, require_print=True)
    if printable:
        raise AssertionError(f"printable bidi fixture failed: {printable!r}")
    template = validate(
        ROOT / "templates" / "bidi-learning-pack.html", check_links=False, require_print=True
    )
    if template:
        raise AssertionError(f"bidi template failed: {template!r}")
    with tempfile.TemporaryDirectory() as directory:
        no_print_path = Path(directory) / "no-print.html"
        no_print_path.write_text(
            (ROOT / "fixtures" / "bidi" / "valid.html").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        print_errors = validate(no_print_path, require_print=True)
        if not any("@page" in error for error in print_errors) or not any(
            "break-inside" in error for error in print_errors
        ):
            raise AssertionError(f"missing PDF print controls were accepted: {print_errors!r}")
    valid_text = (ROOT / "fixtures" / "bidi" / "valid.html").read_text(encoding="utf-8")
    if 'bdi[dir="ltr"] { white-space: nowrap; }' not in valid_text:
        raise AssertionError("multiword LTR terms can wrap across PDF lines")
    for term in ("API", "Replication", "Contract Test", "Prompt", "Database"):
        if f'<bdi dir="ltr">{term}</bdi>' not in valid_text:
            raise AssertionError(f"technical term lacks explicit LTR isolation: {term}")
    compact = valid_text.replace("direction: rtl", "direction:rtl").replace(
        "direction: ltr", "direction:ltr"
    ).replace("white-space: nowrap", "white-space:nowrap")
    with tempfile.TemporaryDirectory() as directory:
        compact_path = Path(directory) / "compact.html"
        compact_path.write_text(compact, encoding="utf-8")
        if errors := validate(compact_path):
            raise AssertionError(f"semantically valid compact CSS failed: {errors!r}")
        compact_path.write_text(
            compact.replace("<main>", "").replace("</main>", ""), encoding="utf-8"
        )
        errors = validate(compact_path)
        if errors != ["missing main landmark"]:
            raise AssertionError(f"missing main was not isolated exactly: {errors!r}")
    invalid = validate(ROOT / "fixtures" / "bidi" / "invalid-unisolated.html")
    if not any("unisolated" in error for error in invalid):
        raise AssertionError(f"unisolated LTR content was accepted: {invalid!r}")
    print("Teach Me bidi HTML tests passed (isolated and broken fixtures)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
