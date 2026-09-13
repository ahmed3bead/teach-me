#!/usr/bin/env python3
"""Validate dynamic learner simulation suites and globally unique identities."""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import yaml
    from jsonschema import Draft202012Validator
    from jsonschema.exceptions import SchemaError, ValidationError
except ImportError as exc:
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    schema = json.loads((ROOT / "evals" / "simulation.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    keys: set[str] = set()
    count = 0
    paths = sorted((ROOT / "evals" / "simulations").glob("*.yaml"))
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        validator.validate(data)
        for simulation in data["simulations"]:
            key = f"{data['suite']}/{simulation['id']}"
            if key in keys:
                raise AssertionError(f"duplicate simulation key: {key}")
            keys.add(key)
            count += 1
    if not count:
        raise AssertionError("no dynamic simulations found")
    print(f"Teach Me simulation validation passed ({len(paths)} suites, {count} simulations)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, SchemaError, ValidationError, yaml.YAMLError) as exc:
        print(f"Simulation validation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
