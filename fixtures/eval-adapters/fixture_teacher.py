#!/usr/bin/env python3
"""Deterministic teacher adapter used only for simulation-runner tests."""

import json
import sys


payload = json.load(sys.stdin)
response = "This complete fixture lesson explains the fictional rule clearly before offering any optional check."
if str(payload.get("simulation_id", "")).endswith("guard-blocking"):
    response = "Answer this question now: what does the fictional rule map to after this brief explanation?"
json.dump(
    {
        "response": response,
        "model": "fixture-teacher",
    },
    sys.stdout,
)
