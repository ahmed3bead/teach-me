#!/usr/bin/env python3
"""Validate behavioral eval structure, identity, and global uniqueness."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from behavioral_eval_contract import REGISTRY_PATH, load_fixture_registry, validate_case_contract

try:
    import yaml
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import SchemaError, ValidationError
except ImportError as exc:
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc


ROOT = Path(__file__).resolve().parents[1]
EVALS = ROOT / "evals"


def main() -> int:
    schema = json.loads((EVALS / "eval-suite.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    registry_schema = json.loads((ROOT / "schemas" / "eval-fixture-registry.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(registry_schema)
    registry_data = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    Draft202012Validator(registry_schema, format_checker=FormatChecker()).validate(registry_data)
    registry = load_fixture_registry()
    suites: set[str] = set()
    case_keys: set[str] = set()
    case_count = 0

    paths = sorted(EVALS.glob("*.yaml")) + sorted((ROOT / "domain-packs").glob("*/evals.yaml"))
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        validator.validate(data)
        suite = data["suite"]
        if suite in suites:
            raise AssertionError(f"duplicate suite name: {suite}")
        suites.add(suite)
        for case in data["cases"]:
            validate_case_contract(case, registry)
            key = f"{suite}/{case['id']}"
            if key in case_keys:
                raise AssertionError(f"duplicate case key: {key}")
            case_keys.add(key)
            case_count += 1

    if not suites:
        raise AssertionError("no eval suites found")
    print(f"Teach Me eval validation passed ({len(suites)} suites, {case_count} cases)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, ValueError, SchemaError, ValidationError, yaml.YAMLError) as exc:
        print(f"Eval validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
