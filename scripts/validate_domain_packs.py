#!/usr/bin/env python3
"""Validate domain-pack manifests, concept graphs, guides, and eval suites."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError, ValidationError
except ImportError as exc:
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc


ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "domain-packs"


def duplicate(values: list[str]) -> bool:
    return len(values) != len(set(values))


def has_cycle(graph: dict[str, list[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(item) for item in graph.get(node, []) if item in graph):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def main() -> int:
    pack_schema = json.loads((PACKS / "pack.schema.json").read_text(encoding="utf-8"))
    eval_schema = json.loads((ROOT / "evals" / "eval-suite.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(pack_schema)
    Draft202012Validator.check_schema(eval_schema)
    pack_validator = Draft202012Validator(pack_schema)
    eval_validator = Draft202012Validator(eval_schema)
    count = 0

    for path in sorted(PACKS.glob("*/pack.yaml")):
        folder = path.parent
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
        pack_validator.validate(data)
        if data["id"] != folder.name:
            raise AssertionError(f"{path}: id must match directory name")
        guide = folder / "PACK.md"
        evaluations = folder / "evals.yaml"
        if not guide.exists() or not evaluations.exists():
            raise AssertionError(f"{folder}: PACK.md and evals.yaml are required")
        guide_text = guide.read_text(encoding="utf-8")
        for heading in ("Use and boundaries", "Teaching pattern", "Practice and evidence", "Arabic and accessibility", "Safety"):
            if heading not in guide_text:
                raise AssertionError(f"{guide}: missing section {heading!r}")

        prerequisite_ids = [item["id"] for item in data["prerequisites"]]
        concept_ids = [item["id"] for item in data["concepts"]]
        if duplicate(prerequisite_ids) or duplicate(concept_ids):
            raise AssertionError(f"{path}: prerequisite and concept IDs must be unique")
        known = set(prerequisite_ids + concept_ids)
        graph = {item["id"]: item["prerequisite_ids"] for item in data["concepts"]}
        for concept, prerequisites in graph.items():
            missing = set(prerequisites).difference(known)
            if missing:
                raise AssertionError(f"{path}: {concept} has unknown prerequisites {sorted(missing)}")
        if has_cycle(graph):
            raise AssertionError(f"{path}: concept prerequisite cycle detected")

        eval_data = yaml.safe_load(evaluations.read_text(encoding="utf-8"))
        eval_validator.validate(eval_data)
        if eval_data["suite"] != f"domain-{data['id']}":
            raise AssertionError(f"{evaluations}: suite must be domain-{data['id']}")
        count += 1

    if not count:
        raise AssertionError("no domain packs found")
    print(f"Teach Me domain-pack validation passed ({count} packs)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, SchemaError, ValidationError, yaml.YAMLError) as exc:
        print(f"Domain-pack validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
