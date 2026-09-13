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


def duplicates(values: list[Any]) -> set[Any]:
    seen: set[Any] = set()
    repeated: set[Any] = set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return repeated


def cyclic_nodes(graph: dict[str, list[str]]) -> set[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycles: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            cycles.add(node)
            return
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph.get(node, []):
            if dependency in graph:
                visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
    return cycles


def validate(
    session: dict[str, Any],
    *,
    coverage: dict[str, Any] | None = None,
    knowledge_base: dict[str, Any] | None = None,
    curriculum_map: dict[str, Any] | None = None,
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
    if repeated := duplicates(objective_ids):
        errors.append(f"objective_id values must be unique: {sorted(repeated)}")

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

    objective_graph = {
        item.get("objective_id"): item.get("prerequisite_objective_ids", [])
        for item in objectives
        if item.get("objective_id")
    }
    if cycles := cyclic_nodes(objective_graph):
        errors.append(f"objective prerequisite cycle detected: {sorted(cycles)}")

    checkpoint = session.get("checkpoint", {})
    active_objective = next((item for item in objectives if item.get("objective_id") == active), None)
    if active_objective and checkpoint.get("latest_state") != active_objective.get("state"):
        errors.append("checkpoint latest_state does not match the active objective state")

    artifacts = [
        ("coverage", coverage),
        ("knowledge-base", knowledge_base),
        ("curriculum-map", curriculum_map),
        ("curriculum", curriculum),
        ("claims", claims),
        ("lesson", lesson),
        ("progress", progress),
    ]
    for name, artifact in artifacts:
        if artifact is not None and artifact.get("session_id") != session_id:
            errors.append(f"{name} session_id does not match the learning session")

    if curriculum_map is not None:
        if session.get("curriculum_id") != curriculum_map.get("curriculum_id"):
            errors.append("curriculum-map curriculum_id does not match the learning session")
        map_sources = [item.get("source_id") for item in curriculum_map.get("sources", [])]
        map_units = [item.get("unit_id") for item in curriculum_map.get("units", [])]
        if duplicates(map_sources):
            errors.append("curriculum-map source IDs must be unique")
        if duplicates(map_units):
            errors.append("curriculum-map unit IDs must be unique")
        for source_id in map_sources:
            if source_id not in known_sources:
                errors.append(f"curriculum-map references unknown source_id {source_id!r}")
        for unit in curriculum_map.get("units", []):
            for source_id in unit.get("source_ids", []):
                if source_id not in map_sources:
                    errors.append(f"curriculum-map unit references undeclared source_id {source_id!r}")
            for objective_id in unit.get("objective_ids", []):
                if objective_id not in known_objectives:
                    errors.append(f"curriculum-map unit references unknown objective_id {objective_id!r}")

    if curriculum is not None:
        if session.get("curriculum_id") != curriculum.get("curriculum_id"):
            errors.append("curriculum_id does not match the learning session")
        modules = curriculum.get("modules", [])
        module_ids = [item.get("module_id") for item in modules]
        curriculum_lessons = [item for module in modules for item in module.get("lessons", [])]
        lesson_ids = [item.get("lesson_id") for item in curriculum_lessons]
        if None in module_ids or duplicates(module_ids):
            errors.append("curriculum module_id values must be present and unique")
        if None in lesson_ids or duplicates(lesson_ids):
            errors.append("curriculum lesson_id values must be present and unique")
        known_modules = set(module_ids)
        known_lessons = set(lesson_ids)
        for source_id in curriculum.get("source_ids", []):
            if source_id not in known_sources:
                errors.append(f"curriculum references unknown source_id {source_id!r}")
        for module in modules:
            module_id = module.get("module_id")
            for dependency in module.get("prerequisite_module_ids", []):
                if dependency == module_id:
                    errors.append(f"module {module_id!r} cannot depend on itself")
                elif dependency not in known_modules:
                    errors.append(f"module {module_id!r} references unknown prerequisite {dependency!r}")
            for curriculum_lesson in module.get("lessons", []):
                for objective_id in curriculum_lesson.get("objective_ids", []):
                    if objective_id not in known_objectives:
                        errors.append(f"curriculum lesson references unknown objective_id: {objective_id!r}")
        module_graph = {
            item.get("module_id"): item.get("prerequisite_module_ids", [])
            for item in modules
            if item.get("module_id")
        }
        if cycles := cyclic_nodes(module_graph):
            errors.append(f"module prerequisite cycle detected: {sorted(cycles)}")
        active_module = checkpoint.get("active_module_id")
        active_lesson = checkpoint.get("active_lesson_id")
        if active_module is not None and active_module not in known_modules:
            errors.append(f"checkpoint references unknown module_id: {active_module!r}")
        if active_lesson is not None and active_lesson not in known_lessons:
            errors.append(f"checkpoint references unknown lesson_id: {active_lesson!r}")
        if active_module is not None and active_lesson is not None:
            module_lessons = {
                item.get("lesson_id")
                for module in modules
                if module.get("module_id") == active_module
                for item in module.get("lessons", [])
            }
            if active_lesson not in module_lessons:
                errors.append("checkpoint active_lesson_id does not belong to active_module_id")
        if curriculum.get("active_module_id") != active_module or curriculum.get("active_lesson_id") != active_lesson:
            errors.append("curriculum active checkpoint does not match the learning session")
    else:
        known_lessons = set()

    if coverage is not None:
        coverage_ids = [item.get("source_id") for item in coverage.get("sources", [])]
        if duplicates(coverage_ids):
            errors.append("coverage source IDs must be unique")
        missing = known_sources.difference(coverage_ids)
        if missing:
            errors.append(f"session source_ids missing from coverage: {sorted(missing)}")

    if knowledge_base is not None:
        research_ids = [item.get("source_id") for item in knowledge_base.get("sources", [])]
        if duplicates(research_ids):
            errors.append("knowledge-base source IDs must be unique")
        missing = known_sources.difference(research_ids)
        if missing:
            errors.append(f"session source_ids missing from knowledge-base: {sorted(missing)}")

    if claims is not None:
        claim_ids = [claim.get("claim_id") for claim in claims.get("claims", [])]
        if duplicates(claim_ids):
            errors.append("claim_id values must be unique")
        for claim in claims.get("claims", []):
            for objective_id in claim.get("dependent_objective_ids", []):
                if objective_id not in known_objectives:
                    errors.append(f"claim {claim.get('claim_id')!r} references unknown objective_id {objective_id!r}")
            for support in claim.get("support", []):
                source_id = support.get("source_id")
                if source_id and source_id not in known_sources:
                    errors.append(f"claim {claim.get('claim_id')!r} references unknown source_id {source_id!r}")

    if lesson is not None:
        lesson_id = lesson.get("lesson_id")
        if curriculum is not None and lesson_id not in known_lessons:
            errors.append(f"lesson-plan references unknown lesson_id {lesson_id!r}")
        referenced = set(lesson.get("objective_ids", []))
        referenced.update(lesson.get("assessment", {}).get("objective_ids", []))
        for objective_id in referenced:
            if objective_id not in known_objectives:
                errors.append(f"lesson references unknown objective_id {objective_id!r}")
        assessment_id = lesson.get("assessment", {}).get("assessment_id")
        for objective_id in lesson.get("assessment", {}).get("objective_ids", []):
            objective = next((item for item in objectives if item.get("objective_id") == objective_id), {})
            if assessment_id not in objective.get("assessment_ids", []):
                errors.append(f"assessment {assessment_id!r} is not registered for objective {objective_id!r}")

    if progress is not None:
        record_ids = [record.get("record_id") for record in progress.get("records", [])]
        if duplicates(record_ids):
            errors.append("progress record_id values must be unique")
        for record in progress.get("records", []):
            objective_id = record.get("objective_id")
            if objective_id not in known_objectives:
                errors.append(f"progress references unknown objective_id {objective_id!r}")
            lesson_id = record.get("lesson_id")
            if lesson_id and curriculum is not None and lesson_id not in known_lessons:
                errors.append(f"progress references unknown lesson_id {lesson_id!r}")
            assessment_id = record.get("assessment_id")
            objective = next((item for item in objectives if item.get("objective_id") == objective_id), {})
            if assessment_id and assessment_id not in objective.get("assessment_ids", []):
                errors.append(f"progress references unknown assessment_id {assessment_id!r}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    parser.add_argument("--coverage", type=Path)
    parser.add_argument("--knowledge-base", type=Path)
    parser.add_argument("--curriculum-map", type=Path)
    parser.add_argument("--curriculum", type=Path)
    parser.add_argument("--claims", type=Path)
    parser.add_argument("--lesson", type=Path)
    parser.add_argument("--progress", type=Path)
    args = parser.parse_args()

    errors = validate(
        load(args.session),
        coverage=load(args.coverage) if args.coverage else None,
        knowledge_base=load(args.knowledge_base) if args.knowledge_base else None,
        curriculum_map=load(args.curriculum_map) if args.curriculum_map else None,
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
