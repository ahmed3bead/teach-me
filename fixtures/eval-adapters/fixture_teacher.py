#!/usr/bin/env python3
"""Deterministic teacher adapter used only for simulation-runner tests."""

import json
import sys


payload = json.load(sys.stdin)
json.dump({"response": "fixture complete lesson", "model": "fixture-teacher"}, sys.stdout)
