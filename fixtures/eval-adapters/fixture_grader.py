#!/usr/bin/env python3
"""Deterministic grader adapter used only to test runner plumbing."""

import json
import sys


payload = json.load(sys.stdin)
prompt = [x for x in payload["ordered_transcript"] if x["role"] == "user"][-1]["content"]
response = payload["raw_final_response"]
turn = [x for x in payload["ordered_transcript"] if x["role"] == "assistant"][-1]["turn"]
passed = response != "fixture-fail"
results = []
for criterion in payload["criteria"]:
    criterion_passed = passed
    if "FALSE_LANGUAGE_FAIL" in prompt and "response is written in" in criterion:
        criterion_passed = False
    if "OPTIONAL_INVITATION" in prompt and "no assessment question is asked before learner opt-in" in criterion:
        criterion_passed = False
    if "CONCEPT_ORDER_OK" in prompt and "one central concept is taught before notation" in criterion:
        criterion_passed = False
    if "CONCEPT_ORDER_OK" in prompt and "acknowledges that the child is starting from zero" in criterion:
        criterion_passed = False
    if "TECHNICAL_COMPARISON_OK" in prompt:
        criterion_passed = False
    evidence = ({"source": "response", "turn": turn, "quote": response[:120]} if criterion_passed
                else {"source": "absent", "quote": f"ABSENT: {criterion}"})
    results.append(
        {
            "verdict": "pass" if criterion_passed else "fail",
            "evidence": evidence,
            "reason": (
                "The exact response excerpt supplies the required observable behavior."
                if criterion_passed
                else "The required behavior is absent from the raw response."
            ),
        }
    )
json.dump(
    {
        "model": "fixture/grader-v2", "settings": {"deterministic": True},
        "adapter_version": "fixture-2.0.0", "invocation_id": "fixture-grader-invocation",
        "timing": {"started_at": "2026-09-14T00:00:00Z", "completed_at": "2026-09-14T00:00:00Z", "duration_seconds": 0.0},
        "raw_result": {"results": results},
        "results": results,
    },
    sys.stdout,
)
