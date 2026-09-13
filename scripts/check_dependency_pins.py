#!/usr/bin/env python3
"""Require exact direct dependencies and immutable GitHub Action references."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTION = re.compile(r"^\s*-\s+uses:\s+([^\s@]+)@([^\s#]+)", re.MULTILINE)


def main() -> int:
    failures: list[str] = []
    for number, raw in enumerate((ROOT / "requirements-dev.txt").read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if line and not line.startswith("#") and not re.fullmatch(r"[A-Za-z0-9_.-]+==[^\s]+", line):
            failures.append(f"requirements-dev.txt:{number}: direct dependency is not exactly pinned")
    for workflow in (ROOT / ".github" / "workflows").glob("*.y*ml"):
        text = workflow.read_text(encoding="utf-8")
        for action, ref in ACTION.findall(text):
            if not re.fullmatch(r"[a-f0-9]{40}", ref):
                failures.append(f"{workflow.relative_to(ROOT)}: {action}@{ref} is not an immutable commit SHA")
    if failures:
        print("Dependency pin check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Teach Me dependency pin check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
