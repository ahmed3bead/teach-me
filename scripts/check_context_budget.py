#!/usr/bin/env python3
"""Prevent the always-loaded skill and routed references from growing without bound."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LIMITS = {"SKILL.md": 2200}
REFERENCE_LIMIT = 1100
LINK = re.compile(r"\[[^\]]+\]\((references/[^)]+\.md)\)")


def words(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").split())


def main() -> int:
    failures: list[str] = []
    for relative, limit in LIMITS.items():
        count = words(ROOT / relative)
        if count > limit:
            failures.append(f"{relative}: {count} words exceeds {limit}")
    skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    for relative in sorted(set(LINK.findall(skill))):
        count = words(ROOT / relative)
        if count > REFERENCE_LIMIT:
            failures.append(f"{relative}: {count} words exceeds {REFERENCE_LIMIT}")
    if failures:
        print("Context budget failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print(f"Teach Me context budget passed ({words(ROOT / 'SKILL.md')} always-loaded words)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
