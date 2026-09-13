#!/usr/bin/env python3
"""Verify deterministic packaging and the installed skill root."""

from __future__ import annotations

import hashlib
import tempfile
import zipfile
from pathlib import Path

from package_release import build, version


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

    print("Teach Me package tests passed (determinism, checksum, install root)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
