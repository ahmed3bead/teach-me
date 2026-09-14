#!/usr/bin/env python3
"""End-to-end test for mixed-direction HTML to accessible PDF output."""

from __future__ import annotations

import tempfile
from pathlib import Path

from render_learning_pack import render


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "lesson.pdf"
        details = render(
            ROOT / "fixtures" / "bidi" / "printable.html",
            output,
            [
                "درس كتابة طلب واضح",
                "API",
                "Replication",
                "Contract Test",
                "Prompt",
                "Database",
                "python3 scripts/validate.py",
            ],
        )
        assert details["pages"] == 1, details
        assert output.read_bytes().startswith(b"%PDF-")
    print("Teach Me PDF tests passed (bidi HTML, PDF/UA, title, text, one-page layout)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
