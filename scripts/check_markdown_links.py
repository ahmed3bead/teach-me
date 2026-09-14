#!/usr/bin/env python3
"""Check repository-relative Markdown links without network access."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
GENERATED_OUTPUT_LINKS = {("templates/start-here.md", "CURRICULUM.md")}


def main() -> int:
    failures: list[str] = []
    for document in sorted(ROOT.rglob("*.md")):
        if any(part in {".git", ".venv", "dist", "reports"} for part in document.relative_to(ROOT).parts):
            continue
        for raw in LINK.findall(document.read_text(encoding="utf-8")):
            destination = raw.strip().strip("<>").split(maxsplit=1)[0]
            if not destination or destination.startswith("#"):
                continue
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", destination):
                continue
            path_text = unquote(destination.split("#", 1)[0])
            if not path_text:
                continue
            document_name = document.relative_to(ROOT).as_posix()
            if (document_name, path_text) in GENERATED_OUTPUT_LINKS:
                continue
            candidate = (document.parent / path_text).resolve()
            if not candidate.is_relative_to(ROOT):
                failures.append(f"{document.relative_to(ROOT)}: link escapes repository: {raw}")
            elif not candidate.exists():
                failures.append(f"{document.relative_to(ROOT)}: missing target: {raw}")
    if failures:
        print("Markdown link validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Markdown relative-link validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
