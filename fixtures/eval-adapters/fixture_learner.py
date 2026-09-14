#!/usr/bin/env python3
"""Deterministic learner adapter used only for simulation-runner tests."""

import json
import sys


payload = json.load(sys.stdin)
if payload["type"] == "baseline":
    result = {"answer": "I do not know this fictional system.", "model": "fixture-learner"}
elif payload["type"] == "transfer":
    result = {"answer": "fixture-fail" if "FORCE_FAIL" in payload["task"] else "fixture-learned", "model": "fixture-learner"}
else:
    done = not str(payload.get("simulation_id", "")).endswith("max-turn")
    message = "I understand the complete unit."
    if str(payload.get("simulation_id", "")).endswith("artifact-blocking"):
        message = "Draft: I understand.\n{"
    result = {"message": message, "done": done, "model": "fixture-learner"}
json.dump(result, sys.stdout)
