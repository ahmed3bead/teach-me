#!/usr/bin/env python3
"""Focused tests for the deterministic Teach Me MCP runtime bundle."""

from __future__ import annotations

import copy
import contextlib
import io
import json
import tempfile
from pathlib import Path
from typing import Any

from build_mcp_bundle import BundleBuildError, main as build_main, render_bundle
from test_validate_mcp_assets import minimal_repository, write_json


def load_artifact(content: bytes) -> dict[str, Any]:
    return json.loads(content.decode("utf-8"))


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teach-me-mcp-bundle-") as temporary:
        root = Path(temporary)
        manifest_path, manifest = minimal_repository(root)

        first_bytes, first = render_bundle(manifest_path, root)
        second_bytes, second = render_bundle(manifest_path, root)
        if first_bytes != second_bytes or first["bundle_digest"] != second["bundle_digest"]:
            raise AssertionError("unchanged inputs did not produce a byte-identical bundle")
        if not first_bytes.endswith(b"\n") or first_bytes.endswith(b"\n\n"):
            raise AssertionError("bundle must end in exactly one LF")

        output = root / "mcp" / "generated" / "teach-me-runtime.json"
        common = ["--root", str(root)]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            current_result = build_main(common)
            check_result = build_main(["--check", *common])
        if current_result != 0 or check_result != 0:
            raise AssertionError("--check did not accept a current bundle")
        output.write_bytes(first_bytes + b" ")
        stale = output.read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            stale_result = build_main(["--check", *common])
        if stale_result == 0 or output.read_bytes() != stale:
            raise AssertionError("--check did not reject stale output without modifying it")
        output.unlink()
        with contextlib.redirect_stderr(io.StringIO()):
            missing_result = build_main(["--check", *common])
        if missing_result == 0 or output.exists():
            raise AssertionError("--check did not reject missing output without creating it")

        policy_path = root / "references" / "core.md"
        original_asset_digest = first["assets"][1]["sha256"]
        policy_path.write_text("# Core\n\nمرحبا بالعالم\n", encoding="utf-8", newline="\n")
        changed_bytes, changed = render_bundle(manifest_path, root)
        if changed["assets"][1]["sha256"] == original_asset_digest:
            raise AssertionError("selected content did not change its per-asset digest")
        if changed["bundle_digest"] == first["bundle_digest"] or changed_bytes == first_bytes:
            raise AssertionError("selected content did not change the bundle digest and bytes")
        if changed["assets"][1]["content"] != "# Core\n\nمرحبا بالعالم\n":
            raise AssertionError("Arabic UTF-8 content did not survive generation")

        policy_path.write_text("# Core\n", encoding="utf-8", newline="\n")
        policy_path.write_bytes(b"# Core\r\n")
        normalized_bytes, _ = render_bundle(manifest_path, root)
        if normalized_bytes != first_bytes:
            raise AssertionError("CRLF source checkout changed normalized bundle bytes")
        policy_path.write_text("# Core\n", encoding="utf-8", newline="\n")
        (root / "references" / "unlisted.md").write_text("not selected\n", encoding="utf-8")
        unlisted_bytes, unlisted = render_bundle(manifest_path, root)
        if unlisted_bytes != first_bytes or any(asset["path"] == "references/unlisted.md" for asset in unlisted["assets"]):
            raise AssertionError("an unlisted repository file entered or changed the bundle")

        expected_order = [asset["id"] for asset in manifest["assets"]]
        if [asset["id"] for asset in first["assets"]] != expected_order:
            raise AssertionError("bundle assets do not follow validated manifest order")

        unsafe = copy.deepcopy(manifest)
        unsafe["assets"][1]["path"] = "references/../SKILL.md"
        write_json(manifest_path, unsafe)
        try:
            render_bundle(manifest_path, root)
        except BundleBuildError as exc:
            if "traverse" not in str(exc):
                raise
        else:
            raise AssertionError("generator bypassed manifest path validation")

        if str(root).encode("utf-8") in first_bytes:
            raise AssertionError("bundle contains its machine-specific repository path")
        prohibited_metadata = {"generated_at", "timestamp", "username", "hostname", "git_commit", "checkout"}
        if prohibited_metadata.intersection(first) or prohibited_metadata.intersection(first["build"]):
            raise AssertionError("bundle contains machine- or checkout-specific metadata")

        if first["teach_me_version"] != manifest["teach_me_version"]:
            raise AssertionError("Teach Me version was not propagated")
        if first["source_manifest"]["manifest_version"] != manifest["manifest_version"]:
            raise AssertionError("manifest version was not propagated")
        if first["asset_count"] != len(manifest["assets"]):
            raise AssertionError("asset count does not match the explicit allowlist")
        if load_artifact(first_bytes) != first:
            raise AssertionError("serialized bundle does not round-trip as its rendered artifact")

    print("Teach Me MCP bundle focused tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
