#!/usr/bin/env python3
"""Canonical language and terminology policy shared by Teach Me tooling."""

from __future__ import annotations

import re


CANONICAL_LOCALES = {"ar-MSA", "en"}
LEGACY_LOCALE_ALIASES = {"ar-EG": "ar-MSA"}
ARABIC_TEXT = re.compile(r"[\u0600-\u06ff]")


def unicode_phrase_boundary(pattern: str) -> str:
    """Wrap a phrase pattern so it cannot match inside a Unicode word.

    Arabic diacritics are combining marks rather than word characters, so a phrase
    may end with marks ("حلّ") but may not continue into more letters ("حلّلت").
    """
    marks = r"\u064B-\u065F\u0670"
    return rf"(?<![\w{marks}])(?:{pattern})[{marks}]*(?![\w{marks}])"


ENGLISH_REQUEST = re.compile(
    unicode_phrase_boundary(
        r"(?:بال(?:لغة\s+)?(?:إنجليزي|الإنجليزي|انجليزي|الانجليزي|إنجليزية|الإنجليزية|انجليزية|الانجليزية)|"
        r"(?:answer|respond|continue|teach|explain)\s+(?:me\s+)?in\s+english)"
    ),
    flags=re.IGNORECASE,
)


def canonical_locale(value: str) -> str:
    """Return a supported locale, mapping the retired ar-EG value to ar-MSA."""
    normalized = value.strip().lower().replace("_", "-")
    if normalized in {"ar-msa", "ar-eg"}:
        return "ar-MSA"
    if normalized == "en":
        return "en"
    raise ValueError(f"unsupported locale: {value}")


def infer_locale(text: str, explicit: str | None = None) -> str:
    """Honor an explicit English request, then a locale field; otherwise infer Arabic or English."""
    if ENGLISH_REQUEST.search(text):
        return "en"
    if isinstance(explicit, str) and explicit.strip():
        return canonical_locale(explicit)
    return "ar-MSA" if ARABIC_TEXT.search(text) else "en"
