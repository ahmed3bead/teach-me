#!/usr/bin/env python3
"""Dependency-free structural checks for the Teach Me skill repository."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_ORIGINS = {"curriculum", "educator", "inferred", "external", "adaptation"}


def fail(message: str) -> None:
    raise AssertionError(message)


def check_json() -> None:
    for path in sorted((ROOT / "schemas").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            fail(f"{path}: unexpected or missing JSON Schema dialect")
        if data.get("type") != "object" or not data.get("required"):
            fail(f"{path}: expected an object schema with required fields")


def check_skill() -> None:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        fail("SKILL.md: missing YAML frontmatter")
    for required in ("name: teach-me", "Educator Mode", "references/educator-mode.md"):
        if required not in text:
            fail(f"SKILL.md: missing {required!r}")
    for match in re.findall(r"\]\(([^)]+)\)", text):
        if "://" not in match and not (ROOT / match).exists():
            fail(f"SKILL.md: broken local reference {match}")


def check_evals() -> None:
    # Avoid a runtime YAML dependency: these invariants cover the committed format.
    for path in sorted((ROOT / "evals").glob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        ids = re.findall(r"^  - id: (\S+)$", text, flags=re.MULTILINE)
        if not ids or len(ids) != len(set(ids)):
            fail(f"{path}: missing or duplicate case IDs")
        if "    expected:\n" not in text:
            fail(f"{path}: cases need observable expectations")


def check_templates() -> None:
    curriculum = (ROOT / "templates" / "curriculum-map.md").read_text(encoding="utf-8")
    lesson = (ROOT / "templates" / "lesson-plan.md").read_text(encoding="utf-8")
    for word in ("Origin", "Source references", "Approval"):
        if word not in curriculum:
            fail(f"curriculum-map.md: missing {word}")
    for word in ("Demonstrable outcomes", "Assessment", "Traceability"):
        if word not in lesson:
            fail(f"lesson-plan.md: missing {word}")
    if not ALLOWED_ORIGINS.issubset(set(lesson.replace("/", " ").split())):
        fail("lesson-plan.md: origin labels are incomplete")


def main() -> int:
    check_json()
    check_skill()
    check_evals()
    check_templates()
    print("Teach Me validation passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, json.JSONDecodeError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
