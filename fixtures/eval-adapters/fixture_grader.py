#!/usr/bin/env python3
"""Deterministic grader adapter used only to test runner plumbing."""

import json
import sys


payload = json.load(sys.stdin)
passed = payload["response"] == "fixture-pass"
json.dump(
    {
        "model": "fixture-grader",
        "results": [
            {"passed": passed, "reason": "fixture protocol check"}
            for _ in payload["expected"]
        ],
    },
    sys.stdout,
)
