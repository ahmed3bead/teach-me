"""Validate structured assessment intent and support conservative legacy text."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from locale_policy import unicode_phrase_boundary


ASSESSMENT_INTENTS = frozenset({"none", "accept", "decline"})
_ARABIC_MARK = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")
_ARABIC_SEPARATOR = r"[\s،,؛;:.!?؟\-]*"

_DECLINE = re.compile(
    unicode_phrase_boundary(
        r"(?:"
        rf"(?:لا|لن|لم){_ARABIC_SEPARATOR}(?:أختار|اختار|أوافق|اوافق|أريد|اريد)|"
        rf"(?:لا|لن|لم){_ARABIC_SEPARATOR}(?:\w+{_ARABIC_SEPARATOR}){{0,4}}(?:أوافق|اوافق|أختار|اختار|أريد|اريد|جاهز(?:ة|ا)?|مستعد(?:ة|ا)?)|"
        rf"(?:غير|لست|مش){_ARABIC_SEPARATOR}(?:جاهز(?:ة|ا)?|مستعد(?:ة|ا)?)|"
        r"ليس\s+الآن|(?:لا|لن)\s+(?:تختبرني|تسألني)|أفضل\s+(?:متابعة|استكمال)\s+الشرح|"
        r"(?:i\s+)?(?:do|did|will)\s+not\s+(?:\w+\s+){0,2}(?:choose|agree|accept|want)|"
        r"(?:i\s+)?(?:don['’]t|didn['’]t|won['’]t)\s+(?:\w+\s+){0,2}(?:choose|agree|accept|want)|"
        r"(?:do\s+not|don['’]t|did\s+not|didn['’]t|will\s+not|won['’]t)\s+(?:\w+\s+){0,4}(?:check|quiz|test|questions?|exercises?|ready)|"
        r"(?:i(?:['’]m|\s+am)\s+)?not\s+(?:\w+\s+){0,2}(?:ready|comfortable)|"
        r"never\s+(?:agreed|accepted|consented)|"
        r"no[\s,;:.!?-]+(?:i\s+)?(?:agree|accept|choose|want)|"
        r"no\s+(?:check|quiz|test|questions?|exercises?)|"
        r"(?:do\s+not|don['’]t)\s+(?:test|quiz|ask)\s+me|i\s+decline|maybe\s+later"
        r")"
    ),
    flags=re.IGNORECASE,
)

_ACCEPT = re.compile(
    unicode_phrase_boundary(
        r"(?:"
        r"نعم\s*[،,]?\s*(?:أوافق|اوافق|أختار|اختار|أريد|اريد)|"
        r"أجل\s*[،,]?\s*(?:أوافق|اوافق|أختار|اختار|أريد|اريد)|"
        r"(?:أوافق|اوافق)\s+على\s+(?:الفحص|الاختبار|الأسئلة|التمارين)|"
        r"(?:أختار|اختار|أريد|اريد)\s+(?:الفحص|الاختبار|الأسئلة|التمارين)|"
        r"(?:أنا\s+)?(?:جاهز(?:ة|ا)?|مستعد(?:ة|ا)?)\s+(?:للفحص|للاختبار|للأسئلة|للتمارين)|"
        r"اختبرني|اسألني|"
        r"(?:yes|sure|okay|ok)\s*[,.]?\s*i\s+(?:agree|accept|choose)(?:\s+(?:the\s+)?(?:check|quiz|test|questions?|exercises?))?|"
        r"please\s+(?:do|start)\s+(?:the\s+)?(?:check|quiz|test|questions?|exercises?)|"
        r"let['’]s\s+do\s+(?:the\s+)?(?:check|quiz|test|questions?|exercises?)|"
        r"i\s+(?:choose|accept|agree\s+to|want)\s+(?:the\s+)?(?:check|quiz|test|questions?|exercises?)|"
        r"(?:i(?:'m|\s+am)\s+)?ready\s+for\s+(?:the\s+)?(?:check|quiz|test|questions?|exercises?)|"
        r"(?:test|quiz|ask)\s+me"
        r")"
    ),
    flags=re.IGNORECASE,
)


def legacy_assessment_intent(text: str) -> str:
    """Classify only explicit legacy consent or refusal, with negation winning."""
    normalized = _ARABIC_MARK.sub("", unicodedata.normalize("NFKC", text))
    if _DECLINE.search(normalized):
        return "decline"
    if _ACCEPT.search(normalized):
        return "accept"
    return "none"


def validate_assessment_intent(utterance: str, intent: Any) -> str:
    """Validate a structured intent and reject contradictions with explicit text."""
    if not isinstance(intent, str) or intent not in ASSESSMENT_INTENTS:
        raise ValueError("assessment_intent must be one of: none, accept, decline")
    legacy = legacy_assessment_intent(utterance)
    if legacy != "none" and legacy != intent:
        raise ValueError(
            f"assessment_intent {intent!r} contradicts explicit {legacy!r} learner language"
        )
    return intent


def intent_from_turn(turn: dict[str, Any], *, allow_legacy: bool) -> str:
    """Read a structured learner turn, or conservatively classify an old turn."""
    content = turn.get("utterance", turn.get("content", ""))
    if not isinstance(content, str):
        raise ValueError("learner utterance must be a string")
    if "assessment_intent" in turn:
        return validate_assessment_intent(content, turn["assessment_intent"])
    if allow_legacy:
        return legacy_assessment_intent(content)
    raise ValueError("learner turn is missing assessment_intent")
