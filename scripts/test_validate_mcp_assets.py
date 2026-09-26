#!/usr/bin/env python3
"""Focused tests for the default-deny Teach Me remote asset boundary."""

from __future__ import annotations

import copy
import json
import tempfile
from pathlib import Path
from typing import Any

from validate_mcp_assets import (
    MANIFEST,
    POLICY_PROHIBITED_PREFIXES,
    POLICY_PROHIBITED_SEGMENTS,
    ROOT,
    validate_manifest,
)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def minimal_repository(directory: Path) -> tuple[Path, dict[str, Any]]:
    (directory / "references").mkdir(parents=True)
    (directory / "SKILL.md").write_text(
        '---\nname: teach-me\nmetadata:\n  version: "1.0.0-beta.2"\n---\n', encoding="utf-8"
    )
    (directory / "references" / "core.md").write_text("# Core\n", encoding="utf-8")
    manifest = {
        "schema_version": "1.0.0",
        "manifest_version": "1.0.0",
        "teach_me_version": "1.0.0-beta.2",
        "selection_model": "explicit-allowlist",
        "ordering": {"key": "order", "direction": "ascending", "require_contiguous": True},
        "module_categories": [
            {"id": "topic-led-conversational", "status": "active"},
            {"id": "future-mode", "status": "reserved"},
        ],
        "asset_classifications": ["entrypoint", "policy"],
        "canonical_roots": [
            {"path": "SKILL.md", "kind": "file"},
            {"path": "references", "kind": "directory"},
        ],
        "allowed_suffixes": [".md"],
        "prohibited": {
            "path_prefixes": sorted(POLICY_PROHIBITED_PREFIXES),
            "path_segments": sorted(POLICY_PROHIBITED_SEGMENTS),
            "basenames": [".env"],
            "suffixes": [".log", ".tmp"],
        },
        "limits": {
            "max_asset_count": 4,
            "max_individual_asset_bytes": 1024,
            "max_total_asset_bytes": 2048,
        },
        "assets": [
            {
                "order": 1,
                "id": "teach-me-skill",
                "path": "SKILL.md",
                "classification": "entrypoint",
                "required": True,
                "module_categories": ["topic-led-conversational"],
            },
            {
                "order": 2,
                "id": "core-policy",
                "path": "references/core.md",
                "classification": "policy",
                "required": True,
                "module_categories": ["topic-led-conversational"],
            },
        ],
    }
    path = directory / "mcp" / "teach-me-assets.json"
    write_json(path, manifest)
    return path, manifest


def require_error(path: Path, root: Path, fragment: str) -> None:
    errors = validate_manifest(path, root)
    if not any(fragment in error for error in errors):
        raise AssertionError(f"expected error containing {fragment!r}; got {errors!r}")


def mutated_case(directory: Path, value: dict[str, Any]) -> Path:
    path = directory / "mcp" / "case.json"
    write_json(path, value)
    return path


def main() -> int:
    if errors := validate_manifest(MANIFEST, ROOT):
        raise AssertionError(f"committed MCP asset manifest failed: {errors!r}")

    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        manifest_path, valid = minimal_repository(directory)
        if errors := validate_manifest(manifest_path, directory):
            raise AssertionError(f"valid minimal manifest failed: {errors!r}")

        absolute = copy.deepcopy(valid)
        absolute["assets"][1]["path"] = "C:/secrets.txt"
        require_error(mutated_case(directory, absolute), directory, "must not be absolute")

        traversal = copy.deepcopy(valid)
        traversal["assets"][1]["path"] = "references/../SKILL.md"
        require_error(mutated_case(directory, traversal), directory, "must not traverse")

        duplicate = copy.deepcopy(valid)
        duplicate["assets"][1]["id"] = duplicate["assets"][0]["id"]
        duplicate["assets"][1]["path"] = duplicate["assets"][0]["path"]
        require_error(mutated_case(directory, duplicate), directory, "duplicate asset identifiers")
        require_error(mutated_case(directory, duplicate), directory, "duplicate asset paths")

        missing = copy.deepcopy(valid)
        missing["assets"][1]["path"] = "references/missing.md"
        require_error(mutated_case(directory, missing), directory, "does not exist")

        prohibited = copy.deepcopy(valid)
        prohibited["canonical_roots"].append({"path": "scripts", "kind": "directory"})
        prohibited["assets"][1]["path"] = "scripts/secret.md"
        (directory / "scripts").mkdir()
        (directory / "scripts" / "secret.md").write_text("secret", encoding="utf-8")
        require_error(mutated_case(directory, prohibited), directory, "prohibited path prefix")

        reserved = copy.deepcopy(valid)
        reserved["assets"][1]["module_categories"] = ["future-mode"]
        require_error(mutated_case(directory, reserved), directory, "reserved module category")

        conflicting_category = copy.deepcopy(valid)
        conflicting_category["module_categories"][1]["id"] = "topic-led-conversational"
        require_error(mutated_case(directory, conflicting_category), directory, "duplicate module category")

        unordered = copy.deepcopy(valid)
        unordered["assets"][0]["order"] = 2
        unordered["assets"][1]["order"] = 1
        require_error(mutated_case(directory, unordered), directory, "asset order must be contiguous")

        count_limited = copy.deepcopy(valid)
        count_limited["limits"]["max_asset_count"] = 1
        require_error(mutated_case(directory, count_limited), directory, "asset count")

        size_limited = copy.deepcopy(valid)
        size_limited["limits"]["max_individual_asset_bytes"] = 4
        require_error(mutated_case(directory, size_limited), directory, "size")

        total_limited = copy.deepcopy(valid)
        total_limited["limits"]["max_total_asset_bytes"] = 8
        total_limited["limits"]["max_individual_asset_bytes"] = 8
        require_error(mutated_case(directory, total_limited), directory, "total asset size")

        (directory / "references" / "unlisted.md").write_text("not selected\n", encoding="utf-8")
        if errors := validate_manifest(manifest_path, directory):
            raise AssertionError(f"an unrelated unlisted file changed selection: {errors!r}")
        selected = {item["path"] for item in valid["assets"]}
        if "references/unlisted.md" in selected:
            raise AssertionError("unlisted repository file entered the explicit allowlist")

        outside = directory.parent / f"{directory.name}-outside.md"
        outside.write_text("outside\n", encoding="utf-8")
        link = directory / "references" / "linked.md"
        try:
            link.symlink_to(outside)
        except OSError:
            pass
        else:
            symlink = copy.deepcopy(valid)
            symlink["assets"][1]["path"] = "references/linked.md"
            require_error(mutated_case(directory, symlink), directory, "symbolic-link path component")
            link.unlink()
        outside.unlink()

    print("Teach Me MCP asset validator focused tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
