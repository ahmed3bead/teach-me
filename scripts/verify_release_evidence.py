#!/usr/bin/env python3
"""Validate evidence and enforce the stable-release quality floor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import ValidationError
except ImportError as exc:
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc

from locale_policy import canonical_locale


ROOT = Path(__file__).resolve().parents[1]


def verify(value: dict[str, Any], candidate_commit: str | None = None) -> None:
    schema = json.loads((ROOT / "schemas" / "release-evidence.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(value)
    failures: list[str] = []
    if value["evidence_kind"] != "real-release":
        failures.append("fixture evidence cannot authorize a stable release")
    if candidate_commit and value["candidate_commit"] != candidate_commit:
        failures.append("candidate_commit does not match the release candidate")
    behavioral = value["behavioral"]
    if behavioral["cases"] < 88 or behavioral["pass_rate"] < 0.90 or behavioral["critical_failures"]:
        failures.append("behavioral evaluation does not meet 88 cases, 90%, and zero critical failures")
    simulations = value["simulations"]
    if simulations["count"] < 2 or simulations["pass_rate"] < 0.90 or simulations["minimum_observed_gain"] < 0.60 or simulations["critical_failures"]:
        failures.append("dynamic simulations do not meet count, pass-rate, gain, and critical-failure gates")
    locales = {canonical_locale(item["locale"]) for item in value["human_reviews"] if item["verdict"] == "pass"}
    if not {"ar-MSA", "en"}.issubset(locales):
        failures.append("passing human reviews are required in English and Arabic")
    if not all(value["journeys"].values()) or not all(value["artifact_review"].values()):
        failures.append("journey and artifact review gates must all pass")
    if failures:
        raise ValueError("; ".join(failures))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--candidate-commit")
    args = parser.parse_args()
    try:
        verify(json.loads(args.evidence.read_text(encoding="utf-8")), args.candidate_commit)
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        print(f"Release evidence failed: {exc}", file=sys.stderr)
        return 1
    print("Teach Me stable release evidence passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
