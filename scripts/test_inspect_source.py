#!/usr/bin/env python3
"""End-to-end coverage tests for PDF and evidence-bounded video intake."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from render_learning_pack import render


ROOT = Path(__file__).resolve().parents[1]


def invoke(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "inspect_source.py"), *arguments],
                          cwd=ROOT, text=True, capture_output=True, check=False)


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        pdf = directory / "lesson.pdf"
        render(ROOT / "fixtures" / "bidi" / "printable.html", pdf, ["Prompt"])
        ledger = directory / "pdf-coverage.json"
        text = directory / "extracted.txt"
        result = invoke(["--session-id", "S1", "--source-id", "PDF1", "--title", "Synthetic lesson",
                         "--media-type", "document", "--path", str(pdf), "--output", str(ledger),
                         "--text-output", str(text)])
        assert result.returncode == 0, result.stderr
        value = json.loads(ledger.read_text(encoding="utf-8"))
        assert value["overall_status"] == "ready-to-teach"
        assert value["sources"][0]["coverage"] == "complete"
        assert "Prompt" in text.read_text(encoding="utf-8")

        transcript = directory / "transcript.txt"
        transcript.write_text("Synthetic transcript evidence.", encoding="utf-8")
        result = invoke(["--session-id", "S1", "--source-id", "VID1", "--title", "Synthetic video",
                         "--media-type", "video", "--transcript", str(transcript), "--output", str(ledger)])
        assert result.returncode == 0, result.stderr
        value = json.loads(ledger.read_text(encoding="utf-8"))
        source = value["sources"][0]
        assert source["coverage"] == "progressive"
        assert "visuals" not in source["inspected_components"]
        assert any("No visual frames" in item for item in source["limitations"])

        result = invoke(["--session-id", "S1", "--source-id", "VID2", "--title", "Opaque video",
                         "--media-type", "video", "--path", str(pdf), "--output", str(ledger)])
        assert result.returncode == 1
    print("Teach Me source intake tests passed (PDF extraction, transcript boundary, video refusal)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
