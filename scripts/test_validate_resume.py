#!/usr/bin/env python3
"""Behavioral tests for portable resume-code parsing and migration."""

from __future__ import annotations

from validate_resume import validate


def expect(code: str, status: str) -> dict[str, object]:
    output = validate(code)
    if output["status"] != status:
        raise AssertionError(f"{code!r}: expected {status!r}, got {output!r}")
    if output["mastery_evidence"] is not False:
        raise AssertionError(f"{code!r}: locator became mastery evidence")
    return output


def main() -> int:
    current = expect("TEACH-ME:v2:S001:prompts:ar-EG:M01:L02", "valid")
    if current["fields"].get("session_id") != "S001":
        raise AssertionError("v2 session_id was not preserved")
    if current["fields"].get("language") != "ar-MSA":
        raise AssertionError("legacy ar-EG locale was not canonicalized")

    legacy = expect("TEACH-ME:v1:prompts:ar-EG:M01:L02:retained", "legacy-valid")
    if legacy.get("legacy_claimed_state") != "retained" or "state" in legacy["fields"]:
        raise AssertionError("legacy mastery claim was not isolated")
    if legacy["fields"].get("language") != "ar-MSA":
        raise AssertionError("legacy v1 ar-EG locale was not canonicalized")

    expect("TEACH-ME:v2:S001:prompts:ar-EG:M01", "partial")
    expect("TEACH-ME:v1:prompts:ar-EG:M01", "partial")
    expect("TEACH-ME:v3:S001:prompts:ar-EG:M01:L02", "unsupported-version")
    expect("TEACH-ME:v2:S001:prompts:xx:M01:L02", "malformed")
    expect("TEACH-ME:v2:S 001:prompts:ar-EG:M01:L02", "malformed")
    expect("OTHER:v2:S001:prompts:ar-EG:M01:L02", "malformed")

    print("Teach Me resume validator tests passed (8 scenarios)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
