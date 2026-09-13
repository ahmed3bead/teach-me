#!/usr/bin/env python3
"""Deterministic grader adapter used only to test runner plumbing."""

import json
import sys


payload = json.load(sys.stdin)
passed = payload["response"] != "fixture-fail"
results = []
for criterion in payload["expected"]:
    criterion_passed = passed
    if "FALSE_LANGUAGE_FAIL" in payload["prompt"] and "response is written in" in criterion:
        criterion_passed = False
    if "OPTIONAL_INVITATION" in payload["prompt"] and "no assessment question is asked before learner opt-in" in criterion:
        criterion_passed = False
    if "CONCEPT_ORDER_OK" in payload["prompt"] and "one central concept is taught before notation" in criterion:
        criterion_passed = False
    if "CONCEPT_ORDER_OK" in payload["prompt"] and "acknowledges that the child is starting from zero" in criterion:
        criterion_passed = False
    if "TECHNICAL_COMPARISON_OK" in payload["prompt"]:
        criterion_passed = False
    results.append({"passed": criterion_passed, "reason": "fixture protocol check"})
json.dump(
    {
        "model": "fixture-grader",
        "results": results,
    },
    sys.stdout,
)
