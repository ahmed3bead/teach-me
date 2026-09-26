#!/usr/bin/env python3
"""Validate the explicit, default-deny Teach Me remote asset boundary."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "mcp" / "teach-me-assets.json"
SAFE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:/")
TOP_LEVEL_KEYS = {
    "schema_version",
    "manifest_version",
    "teach_me_version",
    "selection_model",
    "ordering",
    "module_categories",
    "asset_classifications",
    "canonical_roots",
    "allowed_suffixes",
    "prohibited",
    "limits",
    "assets",
}
ASSET_KEYS = {"order", "id", "path", "classification", "required", "module_categories"}
POLICY_MAX_ASSET_COUNT = 128
POLICY_MAX_INDIVIDUAL_BYTES = 1024 * 1024
POLICY_MAX_TOTAL_BYTES = 5 * 1024 * 1024
POLICY_CANONICAL_ROOTS = {
    "SKILL.md": "file",
    "references": "directory",
    "domain-packs": "directory",
    "templates": "directory",
    "schemas": "directory",
}
POLICY_PROHIBITED_PREFIXES = {
    ".git",
    ".agents",
    ".claude-plugin",
    ".github",
    ".venv",
    "agents",
    "chatgpt-edition",
    "claude-edition",
    "dist",
    "docs",
    "evals",
    "fixtures",
    "installers",
    "mcp",
    "node_modules",
    "plugins",
    "reports",
    "scripts",
    "skills",
    "venv",
}
POLICY_PROHIBITED_SEGMENTS = {".git", ".venv", "__pycache__", "node_modules", "reports"}


def _mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{label} must be an object")
        return {}
    return value


def _list(value: Any, label: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{label} must be an array")
        return []
    return value


def _positive_integer(value: Any, label: str, errors: list[str]) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        errors.append(f"{label} must be a positive integer")
        return 0
    return value


def _duplicates(values: list[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        key = value.casefold()
        if key in seen:
            duplicates.add(value)
        seen.add(key)
    return duplicates


def _teach_me_version(root: Path, errors: list[str]) -> str | None:
    skill = root / "SKILL.md"
    try:
        text = skill.read_text(encoding="utf-8")
    except OSError as exc:
        errors.append(f"cannot read canonical SKILL.md: {exc}")
        return None
    match = re.search(r'^  version:\s*["\']?([^"\'\s]+)', text, flags=re.MULTILINE)
    if not match:
        errors.append("canonical SKILL.md is missing metadata.version")
        return None
    return match.group(1)


def _safe_relative_path(value: Any, label: str, errors: list[str]) -> PurePosixPath | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label} must be a non-empty string")
        return None
    if "\\" in value:
        errors.append(f"{label} must use repository-relative POSIX separators")
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or WINDOWS_ABSOLUTE.match(value) or value.startswith("//"):
        errors.append(f"{label} must not be absolute")
        return None
    if any(part in {"", ".", ".."} for part in path.parts):
        errors.append(f"{label} must be normalized and must not traverse directories")
        return None
    if path.as_posix() != value:
        errors.append(f"{label} must be normalized")
        return None
    return path


def _under_canonical_root(path: str, roots: list[tuple[str, str]]) -> bool:
    folded = path.casefold()
    for root, kind in roots:
        candidate = root.casefold()
        if kind == "file" and folded == candidate:
            return True
        if kind == "directory" and folded.startswith(candidate + "/"):
            return True
    return False


def _prohibited(path: PurePosixPath, rules: dict[str, Any]) -> str | None:
    value = path.as_posix().casefold()
    prefixes = [str(item).casefold().rstrip("/") for item in rules.get("path_prefixes", [])]
    if any(value == prefix or value.startswith(prefix + "/") for prefix in prefixes):
        return "prohibited path prefix"
    segments = {str(item).casefold() for item in rules.get("path_segments", [])}
    if any(part.casefold() in segments for part in path.parts):
        return "prohibited path segment"
    basenames = {str(item).casefold() for item in rules.get("basenames", [])}
    if path.name.casefold() in basenames or path.name.casefold().startswith(".env."):
        return "prohibited basename"
    suffixes = [str(item).casefold() for item in rules.get("suffixes", [])]
    if any(path.name.casefold().endswith(suffix) for suffix in suffixes):
        return "prohibited suffix"
    return None


def validate_manifest(manifest_path: Path = MANIFEST, root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    root = root.resolve()
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read manifest: {exc}"]
    manifest = _mapping(value, "manifest", errors)
    unknown = set(manifest).difference(TOP_LEVEL_KEYS)
    missing = TOP_LEVEL_KEYS.difference(manifest)
    if unknown:
        errors.append(f"manifest has unknown fields: {sorted(unknown)}")
    if missing:
        errors.append(f"manifest is missing fields: {sorted(missing)}")
    if manifest.get("schema_version") != "1.0.0":
        errors.append("schema_version must be 1.0.0")
    if manifest.get("manifest_version") != "1.0.0":
        errors.append("manifest_version must be 1.0.0")
    if manifest.get("selection_model") != "explicit-allowlist":
        errors.append("selection_model must be explicit-allowlist")
    canonical_version = _teach_me_version(root, errors)
    if canonical_version and manifest.get("teach_me_version") != canonical_version:
        errors.append("teach_me_version must match canonical SKILL.md metadata.version")

    ordering = _mapping(manifest.get("ordering"), "ordering", errors)
    if ordering != {"key": "order", "direction": "ascending", "require_contiguous": True}:
        errors.append("ordering must require contiguous ascending order values")

    categories = _list(manifest.get("module_categories"), "module_categories", errors)
    category_ids: list[str] = []
    active_categories: set[str] = set()
    for index, raw in enumerate(categories):
        category = _mapping(raw, f"module_categories[{index}]", errors)
        if set(category) != {"id", "status"}:
            errors.append(f"module_categories[{index}] must contain only id and status")
        identifier = category.get("id")
        status = category.get("status")
        if not isinstance(identifier, str) or not SAFE_ID.fullmatch(identifier):
            errors.append(f"module_categories[{index}].id is invalid")
        else:
            category_ids.append(identifier)
        if status not in {"active", "reserved"}:
            errors.append(f"module_categories[{index}].status must be active or reserved")
        elif status == "active" and isinstance(identifier, str):
            active_categories.add(identifier)
    if duplicates := _duplicates(category_ids):
        errors.append(f"duplicate module category identifiers: {sorted(duplicates)}")
    if not active_categories:
        errors.append("at least one module category must be active")

    classifications_raw = _list(manifest.get("asset_classifications"), "asset_classifications", errors)
    classifications = [item for item in classifications_raw if isinstance(item, str)]
    if len(classifications) != len(classifications_raw) or any(not SAFE_ID.fullmatch(item) for item in classifications):
        errors.append("asset_classifications must contain only kebab-case identifiers")
    if duplicates := _duplicates(classifications):
        errors.append(f"duplicate asset classifications: {sorted(duplicates)}")

    roots_raw = _list(manifest.get("canonical_roots"), "canonical_roots", errors)
    roots: list[tuple[str, str]] = []
    for index, raw in enumerate(roots_raw):
        item = _mapping(raw, f"canonical_roots[{index}]", errors)
        if set(item) != {"path", "kind"}:
            errors.append(f"canonical_roots[{index}] must contain only path and kind")
        path = _safe_relative_path(item.get("path"), f"canonical_roots[{index}].path", errors)
        kind = item.get("kind")
        if kind not in {"file", "directory"}:
            errors.append(f"canonical_roots[{index}].kind must be file or directory")
        if path is not None and kind in {"file", "directory"}:
            roots.append((path.as_posix(), kind))
    if duplicates := _duplicates([item[0] for item in roots]):
        errors.append(f"duplicate canonical roots: {sorted(duplicates)}")
    for path, kind in roots:
        if POLICY_CANONICAL_ROOTS.get(path) != kind:
            errors.append(f"canonical root {path!r} with kind {kind!r} is not permitted by validator policy")
            continue
        candidate = root.joinpath(*PurePosixPath(path).parts)
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            errors.append(f"canonical root {path!r} does not exist")
            continue
        if not resolved.is_relative_to(root):
            errors.append(f"canonical root {path!r} resolves outside the repository")
        if candidate.is_symlink():
            errors.append(f"canonical root {path!r} must not be a symbolic link")
        if kind == "file" and not resolved.is_file():
            errors.append(f"canonical root {path!r} must be a file")
        if kind == "directory" and not resolved.is_dir():
            errors.append(f"canonical root {path!r} must be a directory")

    suffixes_raw = _list(manifest.get("allowed_suffixes"), "allowed_suffixes", errors)
    allowed_suffixes = [item.casefold() for item in suffixes_raw if isinstance(item, str)]
    if len(allowed_suffixes) != len(suffixes_raw) or any(not item.startswith(".") for item in allowed_suffixes):
        errors.append("allowed_suffixes must contain only dot-prefixed strings")
    if duplicates := _duplicates(allowed_suffixes):
        errors.append(f"duplicate allowed suffixes: {sorted(duplicates)}")

    prohibited = _mapping(manifest.get("prohibited"), "prohibited", errors)
    required_prohibited_keys = {"path_prefixes", "path_segments", "basenames", "suffixes"}
    if set(prohibited) != required_prohibited_keys:
        errors.append("prohibited must define exactly path_prefixes, path_segments, basenames, and suffixes")
    for key in required_prohibited_keys:
        items = _list(prohibited.get(key), f"prohibited.{key}", errors)
        if any(not isinstance(item, str) or not item for item in items):
            errors.append(f"prohibited.{key} must contain only non-empty strings")
    declared_prefixes = {str(item).casefold().rstrip("/") for item in prohibited.get("path_prefixes", [])}
    missing_prefixes = POLICY_PROHIBITED_PREFIXES.difference(declared_prefixes)
    if missing_prefixes:
        errors.append(f"prohibited.path_prefixes is missing policy-required entries: {sorted(missing_prefixes)}")
    declared_segments = {str(item).casefold() for item in prohibited.get("path_segments", [])}
    missing_segments = POLICY_PROHIBITED_SEGMENTS.difference(declared_segments)
    if missing_segments:
        errors.append(f"prohibited.path_segments is missing policy-required entries: {sorted(missing_segments)}")

    limits = _mapping(manifest.get("limits"), "limits", errors)
    if set(limits) != {"max_asset_count", "max_individual_asset_bytes", "max_total_asset_bytes"}:
        errors.append("limits must define exactly count, individual-byte, and total-byte ceilings")
    max_count = _positive_integer(limits.get("max_asset_count"), "limits.max_asset_count", errors)
    max_individual = _positive_integer(
        limits.get("max_individual_asset_bytes"), "limits.max_individual_asset_bytes", errors
    )
    max_total = _positive_integer(limits.get("max_total_asset_bytes"), "limits.max_total_asset_bytes", errors)
    if max_count > POLICY_MAX_ASSET_COUNT:
        errors.append(f"max_asset_count exceeds policy ceiling {POLICY_MAX_ASSET_COUNT}")
    if max_individual > POLICY_MAX_INDIVIDUAL_BYTES:
        errors.append(f"max_individual_asset_bytes exceeds policy ceiling {POLICY_MAX_INDIVIDUAL_BYTES}")
    if max_total > POLICY_MAX_TOTAL_BYTES:
        errors.append(f"max_total_asset_bytes exceeds policy ceiling {POLICY_MAX_TOTAL_BYTES}")
    if max_total and max_individual and max_individual > max_total:
        errors.append("individual asset ceiling must not exceed total asset ceiling")

    assets = _list(manifest.get("assets"), "assets", errors)
    if not assets:
        errors.append("assets must not be empty")
    if max_count and len(assets) > max_count:
        errors.append(f"asset count {len(assets)} exceeds manifest ceiling {max_count}")
    identifiers: list[str] = []
    paths: list[str] = []
    orders: list[int] = []
    total_size = 0
    for index, raw in enumerate(assets):
        asset = _mapping(raw, f"assets[{index}]", errors)
        if set(asset) != ASSET_KEYS:
            errors.append(f"assets[{index}] must contain exactly {sorted(ASSET_KEYS)}")
        order = asset.get("order")
        if isinstance(order, bool) or not isinstance(order, int):
            errors.append(f"assets[{index}].order must be an integer")
        else:
            orders.append(order)
        identifier = asset.get("id")
        if not isinstance(identifier, str) or not SAFE_ID.fullmatch(identifier):
            errors.append(f"assets[{index}].id is invalid")
        else:
            identifiers.append(identifier)
        classification = asset.get("classification")
        if classification not in classifications:
            errors.append(f"assets[{index}].classification is not declared")
        if asset.get("required") is not True:
            errors.append(f"assets[{index}].required must be true for the current runtime boundary")
        modules = _list(asset.get("module_categories"), f"assets[{index}].module_categories", errors)
        if not modules:
            errors.append(f"assets[{index}].module_categories must not be empty")
        for module in modules:
            if module not in category_ids:
                errors.append(f"assets[{index}] references unknown module category {module!r}")
            elif module not in active_categories:
                errors.append(f"assets[{index}] references reserved module category {module!r}")

        path = _safe_relative_path(asset.get("path"), f"assets[{index}].path", errors)
        if path is None:
            continue
        relative = path.as_posix()
        paths.append(relative)
        if not _under_canonical_root(relative, roots):
            errors.append(f"asset {relative!r} is outside declared canonical roots")
        if reason := _prohibited(path, prohibited):
            errors.append(f"asset {relative!r} has {reason}")
        if path.suffix.casefold() not in allowed_suffixes:
            errors.append(f"asset {relative!r} has a disallowed suffix")
        candidate = root.joinpath(*path.parts)
        current = root
        for part in path.parts:
            current = current / part
            if current.is_symlink():
                errors.append(f"asset {relative!r} uses a symbolic-link path component")
                break
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            errors.append(f"asset {relative!r} does not exist")
            continue
        if not resolved.is_relative_to(root):
            errors.append(f"asset {relative!r} resolves outside the repository")
            continue
        if not resolved.is_file():
            errors.append(f"asset {relative!r} is not a regular file")
            continue
        size = resolved.stat().st_size
        total_size += size
        if max_individual and size > max_individual:
            errors.append(f"asset {relative!r} size {size} exceeds manifest ceiling {max_individual}")

    if duplicates := _duplicates(identifiers):
        errors.append(f"duplicate asset identifiers: {sorted(duplicates)}")
    if duplicates := _duplicates(paths):
        errors.append(f"duplicate asset paths: {sorted(duplicates)}")
    expected_order = list(range(1, len(assets) + 1))
    if orders != expected_order:
        errors.append(f"asset order must be contiguous and manifest-sorted: expected {expected_order}, got {orders}")
    if max_total and total_size > max_total:
        errors.append(f"total asset size {total_size} exceeds manifest ceiling {max_total}")
    return errors


def main() -> int:
    errors = validate_manifest()
    if errors:
        for error in errors:
            print(f"MCP asset error: {error}", file=sys.stderr)
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    total = sum((ROOT / asset["path"]).stat().st_size for asset in manifest["assets"])
    print(f"Teach Me MCP asset validation passed ({len(manifest['assets'])} assets, {total} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
