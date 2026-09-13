#!/usr/bin/env python3
"""Test profile expiry, renewal, deletion request, and confirmed deletion."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "profile_lifecycle.py"
FIXTURE = ROOT / "fixtures" / "session" / "learner-profile.json"


def call(arguments: list[str], expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, str(SCRIPT), *arguments], text=True, capture_output=True, check=False)
    if result.returncode != expected:
        raise AssertionError(f"expected {expected}, got {result.returncode}: {result.stdout} {result.stderr}")
    return result


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teach-me-profile-") as directory:
        profile = Path(directory) / "profile.json"
        shutil.copyfile(FIXTURE, profile)

        active = json.loads(call(["status", str(profile), "--at", "2026-09-20T00:00:00Z"]).stdout)
        if not active["active"]:
            raise AssertionError("active profile was rejected")
        expired = json.loads(call(["status", str(profile), "--at", "2026-11-01T00:00:00Z"], expected=1).stdout)
        if expired["reason"] != "expired":
            raise AssertionError("expired profile was not blocked")

        call(
            [
                "renew",
                str(profile),
                "--confirm-profile-id",
                "PROF1",
                "--purpose",
                "Continue the requested learning journey",
                "--retention-until",
                "2027-01-01T00:00:00Z",
                "--at",
                "2026-11-01T00:00:00Z",
            ]
        )
        renewed = json.loads(call(["status", str(profile), "--at", "2026-11-02T00:00:00Z"]).stdout)
        if not renewed["active"]:
            raise AssertionError("renewed profile was not activated")

        wrong = call(["delete", str(profile), "--confirm-profile-id", "OTHER"], expected=1)
        if "does not match" not in wrong.stderr or not profile.exists():
            raise AssertionError("wrong confirmation deleted the profile")
        call(["request-deletion", str(profile), "--confirm-profile-id", "PROF1"])
        requested = json.loads(call(["status", str(profile), "--at", "2026-11-02T00:00:00Z"], expected=1).stdout)
        if requested["reason"] != "deletion-requested":
            raise AssertionError("deletion request did not block profile use")
        rejected = call(
            [
                "renew",
                str(profile),
                "--confirm-profile-id",
                "PROF1",
                "--purpose",
                "Try to reverse deletion",
                "--retention-until",
                "2027-02-01T00:00:00Z",
            ],
            expected=1,
        )
        if "cannot be renewed" not in rejected.stderr:
            raise AssertionError("deletion-requested profile was renewed")
        call(["delete", str(profile), "--confirm-profile-id", "PROF1"])
        if profile.exists():
            raise AssertionError("confirmed profile deletion failed")

    print("Teach Me profile lifecycle tests passed (expiry, renewal, request, deletion)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
