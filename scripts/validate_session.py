#!/usr/bin/env python3
"""Validate referential integrity across Teach Me session artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate(
    session: dict[str, Any],
    *,
    coverage: dict[str, Any] | None = None,
    knowledge_base: dict[str, Any] | None = None,
    curriculum: dict[str, Any] | None = None,
    claims: dict[str, Any] | None = None,
    lesson: dict[str, Any] | None = None,
    progress: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    session_id = session.get("session_id")
    objectives = session.get("objectives", [])
    objective_ids = [item.get("objective_id") for item in objectives]
    known_objectives = set(objective_ids)
    known_sources = set(session.get("source_ids", []))

    if None in known_objectives or "" in known_objectives:
        errors.append("every objective needs a non-empty objective_id")
    if len(objective_ids) != len(known_objectives):
        errors.append("objective_id values must be unique")

    active = session.get("checkpoint", {}).get("active_objective_id")
    if active not in known_objectives:
        errors.append(f"checkpoint references unknown objective_id: {active!r}")

    for item in objectives:
        current = item.get("objective_id")
        for dependency in item.get("prerequisite_objective_ids", []):
            if dependency == current:
                errors.append(f"objective {current!r} cannot depend on itself")
            elif dependency not in known_objectives:
                errors.append(f"objective {current!r} references unknown prerequisite {dependency!r}")
        for source_id in item.get("source_ids", []):
            if source_id not in known_sources:
                errors.append(f"objective {current!r} references unknown source_id {source_id!r}")

    artifacts = [
        ("coverage", coverage),
        ("knowledge-base", knowledge_base),
        ("curriculum", curriculum),
        ("claims", claims),
        ("lesson", lesson),
        ("progress", progress),
    ]
    for name, artifact in artifacts:
        if artifact is not None and artifact.get("session_id") != session_id:
            errors.append(f"{name} session_id does not match the learning session")

    if curriculum is not None:
        if session.get("curriculum_id") != curriculum.get("curriculum_id"):
            errors.append("curriculum_id does not match the learning session")
        modules = curriculum.get("modules", [])
        module_ids = [item.get("module_id") for item in modules]
        lesson_ids = [lesson.get("lesson_id") for module in modules for lesson in module.get("lessons", [])]
        if None in module_ids or len(module_ids) != len(set(module_ids)):
            errors.append("curriculum module_id values must be present and unique")
        if None in lesson_ids or len(lesson_ids) != len(set(lesson_ids)):
            errors.append("curriculum lesson_id values must be present and unique")
        for module in modules:
            for lesson in module.get("lessons", []):
                for objective_id in lesson.get("objective_ids", []):
                    if objective_id not in known_objectives:
                        errors.append(f"curriculum lesson references unknown objective_id: {objective_id!r}")
        checkpoint = session.get("checkpoint", {})
        active_module = checkpoint.get("active_module_id")
        active_lesson = checkpoint.get("active_lesson_id")
        if active_module is not None and active_module not in set(module_ids):
            errors.append(f"checkpoint references unknown module_id: {active_module!r}")
        if active_lesson is not None and active_lesson not in set(lesson_ids):
            errors.append(f"checkpoint references unknown lesson_id: {active_lesson!r}")

    if coverage is not None:
        coverage_ids = [item.get("id") for item in coverage.get("sources", [])]
        if len(coverage_ids) != len(set(coverage_ids)):
            errors.append("coverage source IDs must be unique")
        missing = known_sources.difference(coverage_ids)
        if missing:
            errors.append(f"session source_ids missing from coverage: {sorted(missing)}")

    if knowledge_base is not None:
        research_ids = [item.get("source_id") for item in knowledge_base.get("sources", [])]
        if len(research_ids) != len(set(research_ids)):
            errors.append("knowledge-base source IDs must be unique")
        missing = known_sources.difference(research_ids)
        if missing:
            errors.append(f"session source_ids missing from knowledge-base: {sorted(missing)}")

    if claims is not None:
        for claim in claims.get("claims", []):
            for objective_id in claim.get("dependent_objective_ids", []):
                if objective_id not in known_objectives:
                    errors.append(f"claim {claim.get('claim_id')!r} references unknown objective_id {objective_id!r}")
            for support in claim.get("support", []):
                source_id = support.get("source_id")
                if source_id and source_id not in known_sources:
                    errors.append(f"claim {claim.get('claim_id')!r} references unknown source_id {source_id!r}")

    if lesson is not None:
        referenced = set(lesson.get("objective_ids", []))
        referenced.update(lesson.get("assessment", {}).get("objective_ids", []))
        for objective_id in referenced:
            if objective_id not in known_objectives:
                errors.append(f"lesson references unknown objective_id {objective_id!r}")

    if progress is not None:
        for record in progress.get("records", []):
            objective_id = record.get("objective_id")
            if objective_id and objective_id not in known_objectives:
                errors.append(f"progress references unknown objective_id {objective_id!r}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    parser.add_argument("--coverage", type=Path)
    parser.add_argument("--knowledge-base", type=Path)
    parser.add_argument("--curriculum", type=Path)
    parser.add_argument("--claims", type=Path)
    parser.add_argument("--lesson", type=Path)
    parser.add_argument("--progress", type=Path)
    args = parser.parse_args()

    errors = validate(
        load(args.session),
        coverage=load(args.coverage) if args.coverage else None,
        knowledge_base=load(args.knowledge_base) if args.knowledge_base else None,
        curriculum=load(args.curriculum) if args.curriculum else None,
        claims=load(args.claims) if args.claims else None,
        lesson=load(args.lesson) if args.lesson else None,
        progress=load(args.progress) if args.progress else None,
    )
    if errors:
        for error in errors:
            print(f"Integration error: {error}", file=sys.stderr)
        return 1
    print("Teach Me session integration passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
