#!/usr/bin/env python3
"""Validate cross-edition product metadata and generated documentation."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

import yaml

from build_chatgpt_edition import render


ROOT = Path(__file__).resolve().parents[1]


def skill_version() -> str:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    return yaml.safe_load(text.split("---", 2)[1])["metadata"]["version"]


def main() -> int:
    failures: list[str] = []
    config = yaml.safe_load((ROOT / "chatgpt-edition" / "gpt-config.yaml").read_text(encoding="utf-8"))
    version = skill_version()
    if config.get("version") != version:
        failures.append("ChatGPT configuration version does not match SKILL.md")
    if config.get("status") != "private-draft-configuration":
        failures.append("ChatGPT Edition must remain a private draft configuration")
    if config.get("sharing") != "Private while in beta; do not publish from this repository setup.":
        failures.append("ChatGPT Edition sharing status is not private")
    expected_capabilities = {
        "web_search": True,
        "code_interpreter_and_data_analysis": True,
        "image_generation": False,
        "canvas": False,
        "actions": [],
    }
    if config.get("recommended_capabilities") != expected_capabilities:
        failures.append("ChatGPT recommended capabilities changed unexpectedly")
    if config.get("required_knowledge_files") != ["KNOWLEDGE.md"]:
        failures.append("ChatGPT owner setup must require exactly the generated knowledge bundle")

    for path, content in render().items():
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            failures.append(f"generated file is stale: {path.relative_to(ROOT)}")

    sources = (ROOT / "chatgpt-edition" / "knowledge-sources.txt").read_text(encoding="utf-8")
    if re.search(r"(^|/)(evals|fixtures|schemas|scripts)(/|$)", sources, flags=re.MULTILINE):
        failures.append("learner knowledge bundle includes internal eval, fixture, schema, or script content")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for heading in (
        "## Choose how you want to use Teach Me",
        "## Which edition should I choose?",
        "## First-session walkthrough",
        "## Limitations",
        "## Development and validation",
    ):
        if heading not in readme:
            failures.append(f"README is missing {heading}")
    if readme.find("## Development and validation") < readme.find("## Choose how you want to use Teach Me"):
        failures.append("advanced validation appears before edition choice")
    if "publicly available ChatGPT Edition" in readme:
        failures.append("README advertises an unpublished public ChatGPT Edition")

    for relative in ("installers/install.sh", "installers/install.ps1"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        if f'PINNED_VERSION="{version}"' not in text and f'$PinnedVersion = "{version}"' not in text:
            failures.append(f"{relative} does not pin the repository version")
        if "e924647f3bcd11c8e090fe51a12ef4d2fbbfcd30001be76c9631e1733abde728" not in text:
            failures.append(f"{relative} does not pin the published archive checksum")

    install_doc = (ROOT / "docs" / "codex-installation.md").read_text(encoding="utf-8")
    for relative in ("installers/install.sh", "installers/install.ps1"):
        # Raw GitHub serves the LF-normalized Git blob even when a Windows
        # checkout materializes CRLF worktree files.
        blob = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
        checksum = hashlib.sha256(blob).hexdigest()
        if checksum not in install_doc:
            failures.append(f"documented bootstrap checksum is stale for {relative}")

    if failures:
        print("Product documentation validation failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    print("Teach Me edition and product documentation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
