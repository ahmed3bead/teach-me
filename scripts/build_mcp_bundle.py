#!/usr/bin/env python3
"""Build the deterministic, content-addressed Teach Me MCP runtime bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from validate_mcp_assets import MANIFEST, ROOT, validate_manifest


BUNDLE = ROOT / "mcp" / "generated" / "teach-me-runtime.json"
BUNDLE_SCHEMA_VERSION = "1.0.0"
MANIFEST_PROVENANCE = "mcp/teach-me-assets.json"
GENERATOR_PROVENANCE = "scripts/build_mcp_bundle.py"


class BundleBuildError(ValueError):
    """Raised when validated canonical inputs cannot produce a safe bundle."""


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize digest input without insignificant whitespace or ASCII escaping."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def output_json_bytes(value: Any) -> bytes:
    """Serialize the committed artifact with stable formatting and one LF."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(",", ": "),
        )
        + "\n"
    ).encode("utf-8")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalized_utf8(path: Path) -> tuple[str, bytes]:
    """Decode strict UTF-8 and normalize every source newline to LF."""

    try:
        text = path.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise BundleBuildError(f"cannot read canonical UTF-8 asset {path.name!r}: {exc}") from exc
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text, text.encode("utf-8")


def selected_asset_path(root: Path, relative: str) -> Path:
    """Recheck a manifest-selected path immediately before reading it."""

    logical = PurePosixPath(relative)
    candidate = root.joinpath(*logical.parts)
    current = root
    for part in logical.parts:
        current = current / part
        if current.is_symlink():
            raise BundleBuildError(f"selected asset {relative!r} uses a symbolic-link path component")
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise BundleBuildError(f"selected asset {relative!r} cannot be resolved: {exc}") from exc
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise BundleBuildError(f"selected asset {relative!r} is not a safe repository file")
    return resolved


def render_bundle(manifest_path: Path = MANIFEST, root: Path = ROOT) -> tuple[bytes, dict[str, Any]]:
    """Return deterministic artifact bytes and the decoded artifact."""

    root = root.resolve()
    manifest_path = manifest_path.resolve()
    expected_manifest = (root / MANIFEST_PROVENANCE).resolve()
    if manifest_path != expected_manifest:
        raise BundleBuildError(f"manifest must be {MANIFEST_PROVENANCE}")
    errors = validate_manifest(manifest_path, root)
    if errors:
        raise BundleBuildError("invalid MCP asset manifest: " + "; ".join(errors))
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BundleBuildError(f"cannot read validated MCP asset manifest: {exc}") from exc

    assets: list[dict[str, Any]] = []
    total_content_bytes = 0
    for selected in manifest["assets"]:
        path = selected_asset_path(root, selected["path"])
        content, content_bytes = normalized_utf8(path)
        total_content_bytes += len(content_bytes)
        assets.append(
            {
                "classification": selected["classification"],
                "content": content,
                "content_bytes": len(content_bytes),
                "id": selected["id"],
                "module_categories": selected["module_categories"],
                "order": selected["order"],
                "path": selected["path"],
                "required": selected["required"],
                "sha256": sha256(content_bytes),
            }
        )

    payload: dict[str, Any] = {
        "asset_count": len(assets),
        "assets": assets,
        "build": {
            "content_encoding": "utf-8",
            "content_newlines": "lf",
            "generated_by": GENERATOR_PROVENANCE,
            "output_serialization": "json-sort-keys-indent-2-final-lf-v1",
            "payload_serialization": "json-sort-keys-compact-utf8-v1",
        },
        "bundle_schema_version": BUNDLE_SCHEMA_VERSION,
        "content_bytes": total_content_bytes,
        "source_manifest": {
            "manifest_version": manifest["manifest_version"],
            "path": MANIFEST_PROVENANCE,
            "schema_version": manifest["schema_version"],
            "selection_model": manifest["selection_model"],
            "sha256": sha256(canonical_json_bytes(manifest)),
        },
        "teach_me_version": manifest["teach_me_version"],
    }
    artifact = dict(payload)
    artifact["bundle_digest"] = "sha256:" + sha256(canonical_json_bytes(payload))
    return output_json_bytes(artifact), artifact


def atomic_write(path: Path, content: bytes) -> None:
    """Replace the output only after a complete temporary write succeeds."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the generated runtime bundle is missing or stale")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    manifest = (root / MANIFEST_PROVENANCE).resolve()
    output = (root / "mcp" / "generated" / "teach-me-runtime.json").resolve()
    expected, artifact = render_bundle(manifest, root)
    if args.check:
        try:
            current = output.read_bytes()
        except OSError:
            current = None
        if current != expected:
            print(f"Teach Me MCP runtime bundle is missing or stale: {output}", file=sys.stderr)
            return 1
    else:
        atomic_write(output, expected)
    print(
        f"Teach Me MCP runtime bundle is current "
        f"({artifact['asset_count']} assets, {len(expected)} bytes, {artifact['bundle_digest']})"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BundleBuildError as exc:
        print(f"MCP bundle build failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
