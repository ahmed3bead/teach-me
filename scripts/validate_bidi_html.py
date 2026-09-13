#!/usr/bin/env python3
"""Check structural direction isolation and relative links in Arabic HTML packs."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


LTR_TEXT = re.compile(r"(?:[A-Za-z]{2,}|\d|https?://)")
PLACEHOLDER = re.compile(r"\{\{[^{}]+\}\}")
ISOLATING_TAGS = {"bdi", "code", "pre"}


class BidiParser(HTMLParser):
    def __init__(self, path: Path) -> None:
        super().__init__(convert_charrefs=True)
        self.path = path
        self.errors: list[str] = []
        self.stack: list[tuple[str, bool]] = []
        self.html_attrs: dict[str, str] = {}
        self.has_utf8 = False
        self.has_main = False
        self.styles: list[str] = []
        self.in_style = False
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key: value or "" for key, value in attrs}
        if tag == "html":
            self.html_attrs = values
        if tag == "meta" and values.get("charset", "").lower() == "utf-8":
            self.has_utf8 = True
        if tag == "main":
            self.has_main = True
        if tag == "style":
            self.in_style = True
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])
        parent_isolated = self.stack[-1][1] if self.stack else False
        classes = set(values.get("class", "").split())
        isolated = parent_isolated or tag in ISOLATING_TAGS or "ltr" in classes or values.get("dir") == "ltr"
        self.stack.append((tag, isolated))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "style":
            self.in_style = False
        if not self.stack:
            return
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                return

    def handle_data(self, data: str) -> None:
        if self.in_style:
            self.styles.append(data)
            return
        if self.stack and self.stack[-1][0] in {"script", "title"}:
            return
        isolated = self.stack[-1][1] if self.stack else False
        visible_data = PLACEHOLDER.sub("", data)
        if LTR_TEXT.search(visible_data) and not isolated:
            sample = " ".join(visible_data.split())[:80]
            self.errors.append(f"unisolated left-to-right text: {sample!r}")


def validate(path: Path, check_links: bool = True) -> list[str]:
    parser = BidiParser(path)
    parser.feed(path.read_text(encoding="utf-8"))
    errors = parser.errors
    if parser.html_attrs.get("dir") != "rtl" or not parser.html_attrs.get("lang", "").startswith("ar"):
        errors.append("html must declare Arabic language and dir=rtl")
    if not parser.has_utf8:
        errors.append("missing UTF-8 meta charset")
    if not parser.has_main:
        errors.append("missing main landmark")
    css = "\n".join(parser.styles)
    for rule in ("unicode-bidi", "isolate", "direction: ltr", "direction: rtl"):
        if rule not in css:
            errors.append(f"missing direction CSS rule containing {rule!r}")
    if check_links:
        for href in parser.links:
            parsed = urlparse(href)
            if parsed.scheme or href.startswith(("#", "mailto:", "tel:")):
                continue
            target = (path.parent / parsed.path).resolve()
            if not target.exists():
                errors.append(f"broken relative link: {href}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", nargs="+", type=Path)
    parser.add_argument("--skip-links", action="store_true", help="for validating a standalone template")
    args = parser.parse_args()
    failed = False
    for path in args.html:
        errors = validate(path, check_links=not args.skip_links)
        if errors:
            failed = True
            for error in errors:
                print(f"{path}: {error}", file=sys.stderr)
        else:
            print(f"Bidi HTML validation passed: {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
