#!/usr/bin/env python3
"""Meta-validate every schema and exercise it with positive and negative fixtures."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import SchemaError, ValidationError
except ImportError as exc:  # pragma: no cover - exercised by dependency-free CI failure
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc


ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "schemas"
FIXTURES = ROOT / "fixtures" / "session"


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expect_rejected(validator: Draft202012Validator, value: dict[str, Any], label: str) -> None:
    if validator.is_valid(value):
        raise AssertionError(f"{label}: invalid fixture was accepted")


def validate_pair(schema_path: Path) -> None:
    if schema_path.name == "eval-fixture-registry.schema.json":
        schema = load(schema_path); Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        fixture = yaml.safe_load((ROOT / "fixtures" / "eval-registry.yaml").read_text(encoding="utf-8"))
        validator.validate(fixture)
        bad = copy.deepcopy(fixture); bad["fixtures"][0]["unexpected"] = True
        expect_rejected(validator, bad, "fixture registry additional-property check")
        return
    fixture_path = FIXTURES / schema_path.name.replace(".schema", "")
    if not fixture_path.exists():
        raise AssertionError(f"{schema_path.name}: missing fixture {fixture_path.name}")

    schema = load(schema_path)
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    fixture = load(fixture_path)
    validator.validate(fixture)

    missing_required = copy.deepcopy(fixture)
    missing_required.pop(schema["required"][0])
    expect_rejected(validator, missing_required, f"{schema_path.name} required-field check")

    wrong_version = copy.deepcopy(fixture)
    wrong_version["version"] = "999.0.0"
    expect_rejected(validator, wrong_version, f"{schema_path.name} version check")

    extra_property = copy.deepcopy(fixture)
    extra_property["unexpected"] = True
    expect_rejected(validator, extra_property, f"{schema_path.name} additional-property check")


def main() -> int:
    paths = sorted(SCHEMAS.glob("*.schema.json"))
    if not paths:
        raise AssertionError("no schemas found")
    for path in paths:
        validate_pair(path)
    print(f"Teach Me schema validation passed ({len(paths)} schemas)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, SchemaError, ValidationError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"Schema validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
