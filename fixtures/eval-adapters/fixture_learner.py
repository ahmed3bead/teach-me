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
    utterance = "I understand the complete unit."
    assessment_intent = "none"
    if str(payload.get("simulation_id", "")).endswith("artifact-blocking"):
        utterance = "Draft: I understand.\n{"
    if str(payload.get("simulation_id", "")).endswith("missing-intent"):
        result = {"utterance": utterance, "done": done, "model": "fixture-learner"}
    elif str(payload.get("simulation_id", "")).endswith("missing-done"):
        result = {
            "utterance": utterance,
            "assessment_intent": assessment_intent,
            "model": "fixture-learner",
        }
    else:
        if str(payload.get("simulation_id", "")).endswith("contradictory-intent"):
            utterance = "I do not agree to the quiz."
            assessment_intent = "accept"
        result = {
            "utterance": utterance,
            "assessment_intent": assessment_intent,
            "done": done,
            "model": "fixture-learner",
        }
json.dump(result, sys.stdout)
