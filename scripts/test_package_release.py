#!/usr/bin/env python3
"""Verify deterministic packaging and the installed skill root."""

from __future__ import annotations

import hashlib
import tempfile
import zipfile
from pathlib import Path

import yaml

from package_claude_skill import build as build_claude
from package_release import build, version
from verify_release_evidence import verify


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teach-me-package-") as directory:
        output = Path(directory)
        first, first_checksum = build(output / "one", version())
        second, _ = build(output / "two", version())
        if hashlib.sha256(first.read_bytes()).digest() != hashlib.sha256(second.read_bytes()).digest():
            raise AssertionError("release archive is not deterministic")
        expected = first_checksum.read_text(encoding="utf-8").split()[0]
        actual = hashlib.sha256(first.read_bytes()).hexdigest()
        if expected != actual:
            raise AssertionError("release checksum does not match archive")
        with zipfile.ZipFile(first) as bundle:
            names = set(bundle.namelist())
        if "teach-me/SKILL.md" not in names:
            raise AssertionError("archive does not install SKILL.md at the skill root")
        if "teach-me/teach-me/SKILL.md" in names:
            raise AssertionError("archive contains a nested duplicate skill")
        if any("__pycache__" in name or name.startswith("teach-me/dist/") for name in names):
            raise AssertionError("archive includes local build artifacts")
        with zipfile.ZipFile(first) as bundle:
            skill_text = bundle.read("teach-me/SKILL.md").decode("utf-8")
        frontmatter = yaml.safe_load(skill_text.split("---", 2)[1])
        if frontmatter.get("name") != "teach-me" or not frontmatter.get("description"):
            raise AssertionError("archive is missing Agent Skills name or description metadata")
        if len(frontmatter["description"]) > 200:
            raise AssertionError("archive skill description exceeds Claude's 200-character limit")

        claude_first, claude_checksum = build_claude(output / "claude-one")
        claude_second, _ = build_claude(output / "claude-two")
        if claude_first.name != f"teach-me-claude-{version()}-development.zip":
            raise AssertionError("Claude development package has an unexpected name")
        if hashlib.sha256(claude_first.read_bytes()).digest() != hashlib.sha256(claude_second.read_bytes()).digest():
            raise AssertionError("Claude development package is not deterministic")
        if claude_checksum.read_text(encoding="utf-8").split()[0] != hashlib.sha256(claude_first.read_bytes()).hexdigest():
            raise AssertionError("Claude development checksum does not match its archive")
        fixture = __import__("json").loads(
            (Path(__file__).resolve().parents[1] / "fixtures/session/release-evidence.json").read_text(encoding="utf-8")
        )
        try:
            verify(fixture)
        except ValueError as exc:
            if "fixture evidence" not in str(exc):
                raise
        else:
            raise AssertionError("fixture evidence authorized a stable release")

    print("Teach Me package tests passed (determinism, checksum, Agent Skills compatibility, install root)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
