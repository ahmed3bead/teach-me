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
    for required in ("name: teach-me", "Learner Mode", "Educator Mode", "Source-Grounded", "references/educator-mode.md", "references/source-grounded-mode.md", "references/integration-core.md", "references/research-sweep.md", "references/curriculum-delivery.md"):
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
    coverage = (ROOT / "templates" / "source-coverage.md").read_text(encoding="utf-8")
    for word in ("Actually inspected", "Understanding gate", "Safe teaching scope"):
        if word not in coverage:
            fail(f"source-coverage.md: missing {word}")
    session = (ROOT / "templates" / "learning-session.md").read_text(encoding="utf-8")
    for word in ("Session ID", "Active objective", "Mastery evidence", "Resume checkpoint"):
        if word not in session:
            fail(f"learning-session.md: missing {word}")
    knowledge = (ROOT / "templates" / "knowledge-base.md").read_text(encoding="utf-8")
    for word in ("Source matrix", "Actually inspected", "Topic map", "Teaching readiness"):
        if word not in knowledge:
            fail(f"knowledge-base.md: missing {word}")
    curriculum = (ROOT / "templates" / "study-curriculum.md").read_text(encoding="utf-8")
    for word in ("Curriculum ID", "Learning path", "Demonstrable outcome", "Source references", "Progress and resume checkpoint"):
        if word not in curriculum:
            fail(f"study-curriculum.md: missing {word}")


def check_integration() -> None:
    session = json.loads((ROOT / "schemas" / "learning-session.schema.json").read_text(encoding="utf-8"))
    claim = json.loads((ROOT / "schemas" / "claim-ledger.schema.json").read_text(encoding="utf-8"))
    for field in ("session_id", "audience", "input_mode", "objectives", "checkpoint"):
        if field not in session["required"]:
            fail(f"learning-session.schema.json: {field} must be required")
    objective = session["properties"]["objectives"]["items"]
    for field in ("objective_id", "mastery_evidence", "state", "next_action"):
        if field not in objective["required"]:
            fail(f"learning-session.schema.json: objective {field} must be required")
    if "session_id" not in claim["required"] or "claims" not in claim["required"]:
        fail("claim-ledger.schema.json: missing connected required fields")
    integration_eval = (ROOT / "evals" / "integration-cases.yaml").read_text(encoding="utf-8")
    for invariant in ("reading or lesson completion is not recorded as mastery", "educator and source-grounded handling are combined", "dependent objectives and lessons are identified"):
        if invariant not in integration_eval:
            fail(f"integration-cases.yaml: missing invariant {invariant!r}")
    validator = ROOT / "scripts" / "validate_session.py"
    if not validator.exists():
        fail("missing session referential-integrity validator")


def check_research_sweep() -> None:
    schema = json.loads((ROOT / "schemas" / "knowledge-base.schema.json").read_text(encoding="utf-8"))
    for field in ("session_id", "subject", "researched_at", "sources", "topic_map", "teaching_readiness"):
        if field not in schema["required"]:
            fail(f"knowledge-base.schema.json: {field} must be required")
    source = schema["properties"]["sources"]["items"]
    for field in ("source_id", "source_family", "access", "inspected", "role", "limitations"):
        if field not in source["required"]:
            fail(f"knowledge-base.schema.json: source {field} must be required")
    cases = (ROOT / "evals" / "research-sweep-cases.yaml").read_text(encoding="utf-8")
    for invariant in ("access controls are not bypassed", "popularity is not treated as an accuracy signal", "prior knowledge is not presented as a completed sweep"):
        if invariant not in cases:
            fail(f"research-sweep-cases.yaml: missing invariant {invariant!r}")


def check_curriculum_delivery() -> None:
    schema = json.loads((ROOT / "schemas" / "study-curriculum.schema.json").read_text(encoding="utf-8"))
    for field in ("curriculum_id", "session_id", "subject", "language", "target_capability", "scope", "modules", "completion_criteria"):
        if field not in schema["required"]:
            fail(f"study-curriculum.schema.json: {field} must be required")
    module = schema["properties"]["modules"]["items"]
    for field in ("module_id", "title", "outcome", "lessons"):
        if field not in module["required"]:
            fail(f"study-curriculum.schema.json: module {field} must be required")
    lesson = module["properties"]["lessons"]["items"]
    for field in ("lesson_id", "objective_ids", "demonstrable_outcome", "activity", "assessment", "source_refs"):
        if field not in lesson["required"]:
            fail(f"study-curriculum.schema.json: lesson {field} must be required")
    cases = (ROOT / "evals" / "curriculum-delivery-cases.yaml").read_text(encoding="utf-8")
    for invariant in ("an editable Markdown curriculum is the default artifact", "the rendered pages are inspected before delivery", "structured Markdown is provided in chat as a disclosed fallback"):
        if invariant not in cases:
            fail(f"curriculum-delivery-cases.yaml: missing invariant {invariant!r}")


def main() -> int:
    check_json()
    check_skill()
    check_evals()
    check_templates()
    check_integration()
    check_research_sweep()
    check_curriculum_delivery()
    print("Teach Me validation passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, json.JSONDecodeError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
