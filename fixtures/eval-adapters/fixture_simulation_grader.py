#!/usr/bin/env python3
"""Deterministic grader adapter used only for simulation-runner tests."""

import json
import sys


payload = json.load(sys.stdin)
if str(payload.get("simulation_id", "")).endswith("grader-failure"):
    print("synthetic grader protocol failure", file=sys.stderr)
    raise SystemExit(2)
passed = payload["transfer_answer"] == "fixture-learned"
json.dump({
    "baseline_score": 0.0,
    "transfer_score": 1.0 if passed else 0.0,
    "model": "fixture-simulation-grader",
    "results": [{"passed": passed, "reason": "fixture protocol check"} for _ in payload["expected"]],
}, sys.stdout)
