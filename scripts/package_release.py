#!/usr/bin/env python3
"""Validate and build a reproducible Teach Me release archive plus SHA-256."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {".git", ".venv", "__pycache__", "dist", "reports"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def version() -> str:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    frontmatter = text.split("---", 2)[1]
    metadata = yaml.safe_load(frontmatter)
    value = metadata.get("metadata", {}).get("version")
    if not isinstance(value, str) or not value:
        raise RuntimeError("SKILL.md metadata.version is missing")
    return value


def validate() -> None:
    commands = [
        [sys.executable, "scripts/validate.py"],
        [sys.executable, "scripts/validate_schemas.py"],
        [sys.executable, "scripts/validate_evals.py"],
        [sys.executable, "scripts/validate_domain_packs.py"],
        [sys.executable, "scripts/test_validate_session.py"],
        [sys.executable, "scripts/test_validate_resume.py"],
        [sys.executable, "scripts/test_behavioral_eval_runner.py"],
        [sys.executable, "scripts/test_feedback_pipeline.py"],
        [sys.executable, "scripts/test_validate_bidi_html.py"],
    ]
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)


def included_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)
        if path.is_dir() or EXCLUDED_PARTS.intersection(relative.parts) or path.suffix in EXCLUDED_SUFFIXES:
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())


def build(output_directory: Path, release_version: str) -> tuple[Path, Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    archive = output_directory / f"teach-me-{release_version}.zip"
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()
    if not args.skip_validation:
        validate()
    archive, checksum = build(args.output_dir, version())
    print(archive)
    print(checksum)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError, yaml.YAMLError) as exc:
        print(f"Packaging failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
