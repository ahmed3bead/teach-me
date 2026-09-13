#!/usr/bin/env python3
"""Inspect local text/PDF sources or supplied video evidence without overstating access."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import ValidationError
    from pypdf import PdfReader
except ImportError as exc:
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc


ROOT = Path(__file__).resolve().parents[1]


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.blocked_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "template"}:
            self.blocked_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "template"} and self.blocked_depth:
            self.blocked_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.blocked_depth and data.strip():
            self.parts.append(data.strip())


def sha256(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: str(item)):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def inspect_document(path: Path) -> tuple[str, list[str], list[str], int, list[str], list[str]]:
    suffix = path.suffix.lower()
    limitations: list[str] = []
    if suffix == ".pdf":
        reader = PdfReader(path)
        pages = [page.extract_text() or "" for page in reader.pages]
        inspected = [f"page-{index}" for index, text in enumerate(pages, 1) if text.strip()]
        if len(inspected) != len(pages):
            limitations.append("Some PDF pages had no extractable text; OCR or visual inspection is required.")
        return "\n\n".join(pages), ["text", "structure"], limitations, len(pages), inspected, [path]
    raw = path.read_text(encoding="utf-8")
    if suffix in {".html", ".htm"}:
        parser = TextExtractor()
        parser.feed(raw)
        raw = "\n".join(parser.parts)
        components = ["text", "structure", "links"]
    else:
        components = ["text", "structure"]
    return raw, components, limitations, 1, ["whole-file"], [path]


def inspect_video(transcript: Path | None, frames: list[Path]) -> tuple[str, list[str], list[str], int, list[str], list[Path]]:
    components: list[str] = []
    limitations: list[str] = []
    files: list[Path] = []
    text = ""
    if transcript:
        text = transcript.read_text(encoding="utf-8")
        files.append(transcript)
        components.append("transcript-auto")
        limitations.append("Transcript provenance is supplied by the caller; audio accuracy was not independently verified.")
    if frames:
        for frame in frames:
            if not frame.is_file() or frame.stat().st_size == 0:
                raise ValueError(f"invalid sampled frame: {frame}")
        files.extend(frames)
        components.extend(["visuals", "frames-sampled"])
        limitations.append("Sampled frames do not establish complete visual coverage.")
    else:
        limitations.append("No visual frames were inspected; do not make claims about on-screen content.")
    if not transcript and not frames:
        limitations.append("No transcript, audio, or visual evidence was supplied.")
    return text, components, limitations, len(frames), [frame.name for frame in frames], files


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--media-type", choices=("text", "document", "video"), required=True)
    parser.add_argument("--path", type=Path)
    parser.add_argument("--transcript", type=Path)
    parser.add_argument("--frame", type=Path, action="append", default=[])
    parser.add_argument("--location", default="")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--text-output", type=Path)
    args = parser.parse_args()
    try:
        if args.media_type in {"text", "document"}:
            if not args.path or not args.path.is_file():
                raise ValueError("text/document inspection requires an existing --path")
            text, components, limitations, total, units, files = inspect_document(args.path)
        else:
            if args.path:
                raise ValueError("video bytes are not silently decoded; supply --transcript and/or sampled --frame evidence")
            text, components, limitations, total, units, files = inspect_video(args.transcript, args.frame)
        if args.text_output and text:
            args.text_output.parent.mkdir(parents=True, exist_ok=True)
            args.text_output.write_text(text, encoding="utf-8")
        if args.media_type == "video":
            access = "partial" if components else "unavailable"
            coverage = "sampled" if "frames-sampled" in components else ("progressive" if components else "none")
            confidence = "medium" if components else "low"
            overall = "ready-for-progressive-study" if components else "needs-more-access"
        else:
            access = "full"
            complete = bool(units) and len(units) == total and bool(text.strip())
            coverage = "complete" if complete else "progressive"
            confidence = "high" if complete else "medium"
            overall = "ready-to-teach" if complete else "ready-for-progressive-study"
        source: dict[str, Any] = {
            "source_id": args.source_id, "title": args.title, "location": args.location or str(args.path or ""),
            "media_type": args.media_type, "access": access, "inspected_components": components,
            "coverage": coverage, "confidence": confidence, "limitations": limitations,
            "inspected_at": datetime.now(timezone.utc).isoformat(), "units_total": total,
            "inspected_units": units, "source_refs": units,
        }
        if files:
            source["content_sha256"] = sha256(files)
        ledger = {"version": "1.0.0", "session_id": args.session_id, "sources": [source], "overall_status": overall}
        schema = json.loads((ROOT / "schemas" / "source-coverage.schema.json").read_text(encoding="utf-8"))
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(ledger)
        atomic_json(args.output, ledger)
        print(json.dumps({"overall_status": overall, "coverage": coverage, "components": components}, ensure_ascii=False))
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        print(f"Source inspection failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
