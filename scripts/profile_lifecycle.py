#!/usr/bin/env python3
"""Enforce consent, retention, renewal, and deletion for one learner profile."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import ValidationError
except ImportError as exc:
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc


ROOT = Path(__file__).resolve().parents[1]


def read_profile(path: Path) -> dict[str, Any]:
    profile = json.loads(path.read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "schemas" / "learner-profile.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(profile)
    return profile


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("time must include a timezone")
    return parsed.astimezone(timezone.utc)


def now(value: str | None) -> datetime:
    return parse_time(value) if value else datetime.now(timezone.utc)


def status(profile: dict[str, Any], at: datetime) -> dict[str, Any]:
    governance = profile["data_governance"]
    deletion = governance["deletion_status"]
    expired = at >= parse_time(governance["retention_until"])
    active = profile["consent"] is True and deletion == "active" and not expired
    reason = "active"
    if deletion != "active":
        reason = deletion
    elif expired:
        reason = "expired"
    elif profile["consent"] is not True:
        reason = "no-consent"
    return {
        "profile_id": profile["profile_id"],
        "active": active,
        "reason": reason,
        "retention_until": governance["retention_until"],
    }


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def require_id(profile: dict[str, Any], expected: str) -> None:
    if profile["profile_id"] != expected:
        raise ValueError("profile confirmation does not match profile_id")


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("status")
    check.add_argument("profile", type=Path)
    check.add_argument("--at")
    deletion = commands.add_parser("request-deletion")
    deletion.add_argument("profile", type=Path)
    deletion.add_argument("--confirm-profile-id", required=True)
    renew = commands.add_parser("renew")
    renew.add_argument("profile", type=Path)
    renew.add_argument("--confirm-profile-id", required=True)
    renew.add_argument("--purpose", required=True)
    renew.add_argument("--retention-until", required=True)
    renew.add_argument("--at")
    remove = commands.add_parser("delete")
    remove.add_argument("profile", type=Path)
    remove.add_argument("--confirm-profile-id", required=True)
    args = parser.parse_args()

    try:
        profile = read_profile(args.profile)
        if args.command == "status":
            result = status(profile, now(args.at))
            print(json.dumps(result, ensure_ascii=False))
            return 0 if result["active"] else 1
        require_id(profile, args.confirm_profile_id)
        if args.command == "request-deletion":
            profile["data_governance"]["deletion_status"] = "deletion-requested"
            atomic_json(args.profile, profile)
            print("Profile marked deletion-requested and must not be used")
            return 0
        if args.command == "renew":
            if profile["data_governance"]["deletion_status"] in {"deletion-requested", "deleted"}:
                raise ValueError("a deletion-requested profile cannot be renewed; create a new consented profile")
            renewed_at = now(args.at)
            retention = parse_time(args.retention_until)
            if retention <= renewed_at:
                raise ValueError("retention_until must be later than consent renewal")
            profile["consent"] = True
            profile["data_governance"].update(
                {
                    "purpose": args.purpose,
                    "consent_recorded_at": renewed_at.isoformat().replace("+00:00", "Z"),
                    "retention_until": retention.isoformat().replace("+00:00", "Z"),
                    "deletion_status": "active",
                }
            )
            atomic_json(args.profile, profile)
            print("Profile consent and retention renewed")
            return 0
        args.profile.unlink()
        print("Profile permanently deleted")
        return 0
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        print(f"Profile operation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
