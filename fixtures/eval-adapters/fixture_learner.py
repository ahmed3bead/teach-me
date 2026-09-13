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
    result = {"message": "I understand the complete unit.", "done": True, "model": "fixture-learner"}
json.dump(result, sys.stdout)
