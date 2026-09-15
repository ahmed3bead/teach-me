#!/usr/bin/env python3
"""Build a deterministic development ZIP for Claude and Claude Code testing."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", "dist", "reports"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def skill_metadata() -> tuple[str, str]:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    version_match = re.search(r'^  version:\s*["\']?([^"\'\s]+)', frontmatter, flags=re.MULTILINE)
    description_match = re.search(r"^description:\s*(.+)$", frontmatter, flags=re.MULTILINE)
    if "name: teach-me" not in frontmatter or not version_match or not description_match:
        raise ValueError("SKILL.md is missing Claude-compatible name, description, or version metadata")
    description = description_match.group(1).strip().strip('"\'')
    if len(description) > 200:
        raise ValueError("SKILL.md description exceeds Claude's 200-character limit")
    return version_match.group(1), description


def included_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if path.is_dir() or EXCLUDED_PARTS.intersection(relative.parts) or path.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def build(output_directory: Path) -> tuple[Path, Path]:
    version, _ = skill_metadata()
    output_directory.mkdir(parents=True, exist_ok=True)
    archive = output_directory / f"teach-me-claude-{version}-development.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for path in included_files():
            relative = path.relative_to(ROOT)
            info = zipfile.ZipInfo(f"teach-me/{relative.as_posix()}", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if relative.parts[0] == "scripts" and path.suffix == ".py" else 0o644) << 16
            bundle.writestr(info, path.read_bytes())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    checksum_path = archive.with_suffix(".zip.sha256")
    checksum_path.write_text(f"{checksum}  {archive.name}\n", encoding="utf-8")
    return archive, checksum_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    archive, checksum = build(args.output_dir)
    print(archive)
    print(checksum)
    print("Development package only; do not present it as a published release.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as exc:
        print(f"Claude skill packaging failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
