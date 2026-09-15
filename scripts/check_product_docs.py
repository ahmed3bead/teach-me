#!/usr/bin/env python3
"""Validate cross-edition product metadata and generated documentation."""

from __future__ import annotations

import hashlib
import json
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
    skill_frontmatter = yaml.safe_load((ROOT / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1])
    if len(skill_frontmatter.get("description", "")) > 200:
        failures.append("SKILL.md description exceeds Claude's 200-character limit")
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
    for stale_claim in ("eligible managed workspace", "eligible managed-workspace"):
        if stale_claim in readme or stale_claim in (ROOT / "chatgpt-edition" / "README.md").read_text(encoding="utf-8"):
            failures.append(f"ChatGPT documentation retains a stale account restriction: {stale_claim}")

    claude_readme = (ROOT / "claude-edition" / "README.md").read_text(encoding="utf-8")
    for required in (
        "Customize → Skills",
        "Code execution and file creation",
        "--target-host claude-code",
        "-TargetHost claude-code",
        "~/.claude/skills/teach-me",
        "python3 scripts/package_claude_skill.py",
        "teach-me-claude-1.0.0-beta.1-development.zip",
    ):
        if required not in claude_readme:
            failures.append(f"Claude setup guide is missing {required!r}")
    if not (ROOT / "claude-edition" / "ACCEPTANCE_TESTS.md").is_file():
        failures.append("Claude acceptance tests are missing")

    plugin_manifest_path = ROOT / ".claude-plugin" / "plugin.json"
    marketplace_path = ROOT / ".claude-plugin" / "marketplace.json"
    try:
        plugin_manifest = json.loads(plugin_manifest_path.read_text(encoding="utf-8"))
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        failures.append(f"Claude Code plugin metadata is missing or invalid JSON: {exc}")
    else:
        skill_name = skill_frontmatter.get("name")
        if plugin_manifest.get("name") != skill_name:
            failures.append("Claude Code plugin name does not match SKILL.md")
        if plugin_manifest.get("skills") != "./skills/":
            failures.append("Claude Code plugin must expose its conventional skills directory")
        if "displayName" in plugin_manifest:
            failures.append("Claude Code plugin manifest must avoid displayName for legacy client compatibility")
        if "version" in plugin_manifest:
            failures.append("Claude Code plugin manifest must use commit-based version fallback")
        if marketplace.get("name") != "teach-me":
            failures.append("Claude Code marketplace name must remain teach-me")
        plugins = marketplace.get("plugins")
        if not isinstance(plugins, list) or len(plugins) != 1:
            failures.append("Claude Code marketplace must list exactly one plugin")
        else:
            entry = plugins[0]
            if entry.get("name") != skill_name or entry.get("source") != "./":
                failures.append("Claude Code marketplace does not expose the root Teach Me plugin")
            if "displayName" in entry:
                failures.append("Claude Code marketplace entry must avoid displayName for legacy client compatibility")
            if "version" in entry:
                failures.append("Claude Code marketplace entry must use commit-based version fallback")
        expected_repository = "https://github.com/ahmed3bead/teach-me"
        if plugin_manifest.get("repository") != expected_repository:
            failures.append("Claude Code plugin repository metadata is incorrect")

        claude_skill = ROOT / "skills" / "teach-me" / "SKILL.md"
        if not claude_skill.is_file():
            failures.append("Claude Code compatibility skill adapter is missing")
        else:
            adapter = claude_skill.read_text(encoding="utf-8")
            for required in ("name: teach-me", "${CLAUDE_PLUGIN_ROOT}/SKILL.md"):
                if required not in adapter:
                    failures.append(f"Claude Code compatibility skill adapter is missing {required!r}")

    for required in (
        "/plugin marketplace add ahmed3bead/teach-me",
        "/plugin install teach-me@teach-me",
        "/teach-me:teach-me",
    ):
        if required not in claude_readme or required not in readme:
            failures.append(f"Claude Code marketplace setup is missing {required!r}")

    for relative in ("installers/install.sh", "installers/install.ps1"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        if f'PINNED_VERSION="{version}"' not in text and f'$PinnedVersion = "{version}"' not in text:
            failures.append(f"{relative} does not pin the repository version")
        if "e924647f3bcd11c8e090fe51a12ef4d2fbbfcd30001be76c9631e1733abde728" not in text:
            failures.append(f"{relative} does not pin the published archive checksum")
        if "claude-code" not in text:
            failures.append(f"{relative} does not expose the Claude Code target")
        if ".claude" not in text or "skills" not in text:
            failures.append(f"{relative} does not select Claude Code's personal skills directory")

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
