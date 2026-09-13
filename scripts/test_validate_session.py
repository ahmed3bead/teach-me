#!/usr/bin/env python3
"""Dependency-free behavioral tests for cross-artifact integrity checks."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from validate_session import validate


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "session"


def load(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def artifacts() -> dict[str, dict[str, Any]]:
    return {
        "session": load("learning-session.json"),
        "coverage": load("source-coverage.json"),
        "knowledge_base": load("knowledge-base.json"),
        "curriculum_map": load("curriculum-map.json"),
        "curriculum": load("study-curriculum.json"),
        "claims": load("claim-ledger.json"),
        "lesson": load("lesson-plan.json"),
        "progress": load("progress.json"),
    }


def require_error(case: dict[str, dict[str, Any]], fragment: str) -> None:
    errors = validate(**case)
    if not any(fragment in error for error in errors):
        raise AssertionError(f"expected error containing {fragment!r}; got {errors!r}")


def main() -> int:
    valid = artifacts()
    if errors := validate(**valid):
        raise AssertionError(f"valid fixture failed: {errors!r}")

    wrong_session = copy.deepcopy(valid)
    wrong_session["progress"]["session_id"] = "OTHER"
    require_error(wrong_session, "progress session_id")

    wrong_source = copy.deepcopy(valid)
    wrong_source["coverage"]["sources"][0]["source_id"] = "OTHER"
    require_error(wrong_source, "missing from coverage")

    broken_map = copy.deepcopy(valid)
    broken_map["curriculum_map"]["units"][0]["objective_ids"] = ["OTHER"]
    require_error(broken_map, "curriculum-map unit references unknown objective_id")

    objective_cycle = copy.deepcopy(valid)
    objective_cycle["session"]["objectives"][0]["prerequisite_objective_ids"] = ["OBJ1"]
    require_error(objective_cycle, "cannot depend on itself")
    require_error(objective_cycle, "objective prerequisite cycle")

    mismatched_checkpoint = copy.deepcopy(valid)
    mismatched_checkpoint["session"]["checkpoint"]["latest_state"] = "retained"
    require_error(mismatched_checkpoint, "latest_state")

    orphan_assessment = copy.deepcopy(valid)
    orphan_assessment["progress"]["records"][0]["assessment_id"] = "UNKNOWN"
    require_error(orphan_assessment, "unknown assessment_id")

    wrong_active_pair = copy.deepcopy(valid)
    wrong_active_pair["curriculum"]["modules"].append(
        {
            "module_id": "MOD2",
            "title": "وحدة ثانية",
            "outcome": "ناتج ثان",
            "prerequisite_module_ids": [],
            "lessons": [
                {
                    "lesson_id": "LES2",
                    "title": "درس ثان",
                    "objective_ids": ["OBJ1"],
                    "demonstrable_outcome": "ناتج",
                    "activity": "نشاط",
                    "assessment": "تقييم",
                    "source_refs": [],
                }
            ],
        }
    )
    wrong_active_pair["session"]["checkpoint"]["active_lesson_id"] = "LES2"
    wrong_active_pair["curriculum"]["active_lesson_id"] = "LES2"
    require_error(wrong_active_pair, "does not belong")

    print("Teach Me session validator tests passed (8 scenarios)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
