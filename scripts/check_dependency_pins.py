#!/usr/bin/env python3
"""Require exact direct dependencies and immutable GitHub Action references."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACTION = re.compile(r"^\s*-\s+uses:\s+([^\s@]+)@([^\s#]+)", re.MULTILINE)
EXACT_VERSION = re.compile(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?")
# The remote MCP Worker may ship only these runtime packages; the adapter itself stays dependency-free.
ALLOWED_RUNTIME_DEPENDENCIES = {"@modelcontextprotocol/sdk", "zod"}


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
    package = json.loads((ROOT / "mcp" / "package.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "mcp" / "package-lock.json").read_text(encoding="utf-8"))
    locked = lock.get("packages", {})
    for name in sorted(set(package.get("dependencies", {})) - ALLOWED_RUNTIME_DEPENDENCIES):
        failures.append(f"mcp/package.json: runtime dependency {name} is not on the reviewed Worker allowlist")
    for section in ("dependencies", "devDependencies"):
        for name, version in package.get(section, {}).items():
            if EXACT_VERSION.fullmatch(str(version)) is None:
                failures.append(f"mcp/package.json: {section} entry {name} is not exactly pinned")
            elif locked.get(f"node_modules/{name}", {}).get("version") != version:
                failures.append(f"mcp/package-lock.json: {name} does not resolve to pinned {version}")
            if locked.get("", {}).get(section, {}).get(name) != version:
                failures.append(f"mcp/package-lock.json: root {section} entry {name} is out of sync")
    if failures:
        print("Dependency pin check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Teach Me dependency pin check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
