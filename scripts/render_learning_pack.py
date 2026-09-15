#!/usr/bin/env python3
"""Validate an Arabic learning-pack HTML file and render a checked PDF/UA."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from pypdf import PdfReader
    from weasyprint import HTML
except ImportError as exc:
    print("Missing PDF dependencies: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc

from validate_bidi_html import validate as validate_bidi


def inspect_pdf(path: Path, expected: list[str]) -> dict[str, object]:
    reader = PdfReader(path)
    if reader.is_encrypted:
        raise ValueError("generated PDF is unexpectedly encrypted")
    if not reader.pages:
        raise ValueError("generated PDF has no pages")
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    compact_text = re.sub(r"(?<=[A-Za-z])\s+(?=[A-Za-z])", "", text)
    for value in expected:
        compact_value = re.sub(r"(?<=[A-Za-z])\s+(?=[A-Za-z])", "", value)
        if value not in text and compact_value not in compact_text:
            raise ValueError(f"generated PDF is missing expected text: {value!r}")
    title = (reader.metadata or {}).get("/Title")
    if not title:
        raise ValueError("generated PDF has no document title")
    return {"pages": len(reader.pages), "title": str(title), "bytes": path.stat().st_size}


def render(source: Path, output: Path, expected: list[str]) -> dict[str, object]:
    errors = validate_bidi(source, check_links=True, require_print=True)
    if errors:
        raise ValueError("invalid bilingual HTML: " + "; ".join(errors))
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    HTML(filename=str(source), base_url=str(source.parent)).write_pdf(
        temporary,
        pdf_variant="pdf/ua-1",
        custom_metadata=True,
    )
    temporary.replace(output)
    return inspect_pdf(output, expected)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--expect-text", action="append", default=[])
    args = parser.parse_args()
    try:
        details = render(args.html, args.pdf, args.expect_text)
    except (OSError, ValueError) as exc:
        print(f"PDF render failed: {exc}", file=sys.stderr)
        return 1
    print(f"Rendered {args.pdf} ({details['pages']} pages, {details['bytes']} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
