#!/usr/bin/env python3
"""Deterministic response adapter used only to test runner plumbing."""

import json
import sys


payload = json.load(sys.stdin)
response = "fixture-fail" if "FORCE_FAIL" in payload["prompt"] else "fixture-pass"
json.dump({"response": response, "model": "fixture-response"}, sys.stdout)
