#!/usr/bin/env python3
"""Run Teach Me eval cases through command-based model and grader adapters.

Each adapter receives one JSON object on stdin and must return one JSON object on
stdout. This keeps the runner independent of any model provider or agent host.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
import time
import unicodedata
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from locale_policy import canonical_locale, unicode_phrase_boundary
from assessment_intent import intent_from_turn
from behavioral_eval_contract import immutable_prompt_packet, validate_case_contract

try:
    import yaml
except ImportError as exc:
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc


ROOT = Path(__file__).resolve().parents[1]
_ACTIVE_REPORT: tuple[Path, dict[str, Any]] | None = None
ARABIC_LETTER = re.compile(r"[\u0621-\u063a\u0640-\u064a\u066e\u066f\u0671-\u06d3\u06fa-\u06fc]")
LATIN_LETTER = re.compile(r"[A-Za-z]")
COLLOQUIAL_ARABIC_MARKER = re.compile(
    unicode_phrase_boundary(r"(?:ده|دي|دول|كده|إحنا|احنا|عشان|عايز|عاوز|إزاي|ازاي|دلوقتي|مش|لسه)")
)
TECHNICAL_TERMS = {
    "Database Replication": ("داتابيز ريبليكيشن", "داتا بيز ريبليكيشن"),
    "API": ("إيه بي آي", "أي بي آي"),
    "Replication": ("ريبليكيشن", "ريبيليكيشن"),
    "Contract Test": ("كونتراكت تيست",),
    "Prompt": ("برومبت",),
    "Database": ("داتابيز", "داتا بيز"),
}
ASSESSMENT_IMPERATIVE = re.compile(
    unicode_phrase_boundary(
        r"(?:جاوب(?:ني)?|جاوبي|حل|احسب|اختار|حد[دّ]|اكتب\s+(?:إجابتك|الحل|نسخة)|ارسم|لو[نّ]|جر[بّ]|"
        r"answer|calculate|choose\s+(?:the\s+correct|which)|identify\s+(?:the|which)|write\s+(?:your\s+answer|a\s+solution)|"
        r"draw|colou?r|solve|predict)"
    ),
    flags=re.IGNORECASE,
)
ASSESSMENT_QUESTION = re.compile(
    r"^(?:هل|ماذا|ما|أي|من|متى|أين|كيف|لماذا|ليه|كم|كام|"
    r"what|which|who|when|where|why|how|can\s+you\s+explain|did\s+you\s+understand|do\s+you\s+understand|got\s+it)\b.*[؟?]$",
    flags=re.IGNORECASE,
)
NAVIGATION_CONTEXT = re.compile(
    r"(?:topic|subject|book|source|video|link|url|title|author|edition|operating system|device|goal|"
    r"available time|budget|file|chapter|lesson|curriculum|course|framework|skill|language|platform|outcome|result|"
    r"prior knowledge|experience|learners?|students?|age|grade|duration|version|access|completion date|hours|time|"
    r"tool|used|build|want to (?:create|learn|do)|"
    r"الموضوع|المادة|الكتاب|المصدر|الفيديو|الرابط|العنوان|المؤلف|الطبعة|نظام التشغيل|الجهاز|الهدف|"
    r"الوقت|وقت|الميزانية|الملف|الفصل|الدرس|المنهج|الكورس|المهارة|اللغة)",
    flags=re.IGNORECASE,
)
NON_ASSESSMENT_ACTION = re.compile(
    r"^(?:current action|your action|الخطوة الحالية|إجراءك الحالي|الإجراء الآن)?\s*[:：-]?\s*"
    r"(?:send|provide|paste|attach|tell me|reply with|read|observe|notice|continue|open|look at|"
    r"أرسل|ارسل|ألصق|الصق|أرفق|ارفق|أخبرني|اخبرني|اذكر|اقرأ|لاحظ|تابع|انتقل|افتح)",
    flags=re.IGNORECASE,
)
FRACTION_NOTATION = re.compile(r"\b\d+\s*/\s*\d+\b")
EQUAL_PARTS = re.compile(r"(?:أجزاء|أقسام|قسمان|قسمين|جزآن|جزءان|جزأين|جزءين|قطعتان|قطعتين)\s+متساوي")
CHILD_CONCRETE_EXAMPLE = re.compile(r"(?:شريط|ورق|دائرة|مربع|تفاحة|رغيف|قلم|مكعب|strip|paper|circle|square|apple|loaf|pencil|cube)", re.IGNORECASE)
SHAMING_LANGUAGE = re.compile(r"\b(?:غبي|فاشل|كسول|ساذج|عيب|يجب أن تعرف|سهل جدًا)\b")
REPEATED_ARABIC_DIACRITIC = re.compile(r"([\u064b-\u065f])\1+")
ARABIC_TOKEN = re.compile(r"[\u0600-\u06ff]+")
SENSITIVE_ARGUMENT = re.compile(r"(?:api[-_]?key|access[-_]?token|password|passwd|private[-_]?key|client[-_]?secret|authorization)", re.I)
ADAPTER_ENV_ALLOWLIST = frozenset({"PATH", "HOME", "CODEX_HOME", "LANG", "LC_ALL", "LC_CTYPE", "TMPDIR", "TEMP", "TMP"})
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"


def safe_adapter_command(command: str) -> list[str]:
    parts = shlex.split(command)
    if not parts: raise RuntimeError("adapter command is empty")
    index = 0
    while index < len(parts):
        if parts[index] == "--api-key-env":
            if index + 1 >= len(parts) or parts[index + 1] != OPENAI_API_KEY_ENV:
                raise RuntimeError("adapter API key option must name OPENAI_API_KEY")
            index += 2
            continue
        if SENSITIVE_ARGUMENT.search(parts[index]): raise RuntimeError("adapter command contains credential-bearing arguments")
        index += 1
    return parts


def stream_metadata(value: str | bytes | None) -> dict[str, Any]:
    if value is None: raw = b""
    elif isinstance(value, bytes): raw = value
    else: raw = value.encode("utf-8", errors="replace")
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def adapter_environment(source: dict[str, str], api_key_env: str | None = None) -> dict[str, str]:
    environment = {name: source[name] for name in ADAPTER_ENV_ALLOWLIST if source.get(name)}
    if api_key_env is not None:
        if api_key_env != OPENAI_API_KEY_ENV: raise RuntimeError("only OPENAI_API_KEY may be passed to an adapter")
        if not source.get(api_key_env): raise RuntimeError("requested adapter API key environment variable is missing")
        environment[api_key_env] = source[api_key_env]
    return environment


class AdapterInvocationError(RuntimeError):
    """A retryable transport or malformed-protocol adapter failure."""

    def __init__(self, kind: str, message: str, record: dict[str, Any]):
        super().__init__(message)
        self.kind = kind
        self.record = record


class NonRetryableEvaluationError(RuntimeError):
    """A completed invocation whose content or artifact validation failed."""


def payload_journal_fields(payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {"payload_sha256": hashlib.sha256(encoded).hexdigest(), "payload_type": payload.get("type"),
            "case_key": "/".join(str(payload.get(key, "")) for key in ("suite", "case_id")).strip("/"),
            "turn_index": payload.get("turn_index")}


def invoke_once(command: str, payload: dict[str, Any], timeout: int, role: str, api_key_env: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Invoke once and preserve an independently auditable command journal entry."""
    started_at = datetime.now(timezone.utc)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            shlex.split(command),
            input=json.dumps(payload, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            env=adapter_environment(dict(os.environ), api_key_env),
        )
    except subprocess.TimeoutExpired as exc:
        record = {
            "role": role,
            "started_at": started_at.isoformat(),
            "duration_seconds": time.monotonic() - started,
            "command": safe_adapter_command(command),
            "credential_env": api_key_env,
            **payload_journal_fields(payload),
            "stdout": stream_metadata(exc.stdout),
            "stderr": stream_metadata(exc.stderr),
            "status": "transport-error",
            "retry_cause": "timeout",
        }
        raise AdapterInvocationError("transport-error", "adapter timed out", record) from exc
    record = {
        "role": role,
        "started_at": started_at.isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": time.monotonic() - started,
        "command": safe_adapter_command(command),
        "credential_env": api_key_env,
        **payload_journal_fields(payload),
        "stdout": stream_metadata(completed.stdout),
        "stderr": stream_metadata(completed.stderr),
        "returncode": completed.returncode,
        "status": "completed",
        "retry_cause": payload.get("protocol_retry", {}).get("cause"),
        "retry_feedback": payload.get("protocol_retry", {}).get("feedback"),
    }
    if completed.returncode != 0:
        record["status"] = "transport-error"
        raise AdapterInvocationError(
            "transport-error", f"adapter failed with return code {completed.returncode}", record
        )
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        record["status"] = "malformed-protocol"
        raise AdapterInvocationError("malformed-protocol", "adapter stdout was not one JSON object", record) from exc
    if not isinstance(output, dict):
        record["status"] = "malformed-protocol"
        raise AdapterInvocationError("malformed-protocol", "adapter output must be an object", record)
    record["result"] = output
    return output, record


def invoke_protocol(
    command: str,
    payload: dict[str, Any],
    timeout: int,
    role: str,
    protocol_retries: int,
    validator: Any | None = None,
    on_record: Any | None = None,
    api_key_env: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], Any]:
    """Retry only transport/malformed protocol failures, never content or guard failures."""
    records: list[dict[str, Any]] = []
    cause: str | None = None
    for retry_index in range(protocol_retries + 1):
        attempt_payload = dict(payload)
        if cause is not None:
            attempt_payload["protocol_retry"] = {
                "cause": cause,
                "retry_index": retry_index,
                "feedback": "Return one well-formed object matching the documented adapter protocol.",
            }
        try:
            output, record = invoke_once(command, attempt_payload, timeout, role, api_key_env)
            records.append(record)
            if on_record: on_record(record)
            try: validated = validator(output) if validator else None
            except NonRetryableEvaluationError: raise
            except RuntimeError:
                record["status"] = "malformed-protocol"
                if on_record: on_record(record)
                raise
            return output, records, validated
        except NonRetryableEvaluationError as exc:
            records[-1]["status"] = "content-error"; records[-1]["content_error"] = str(exc)
            if on_record: on_record(records[-1])
            raise
        except AdapterInvocationError as exc:
            records.append(exc.record)
            if on_record: on_record(exc.record)
            cause = exc.kind
            if retry_index >= protocol_retries:
                raise
        except RuntimeError as exc:
            records[-1]["status"] = "malformed-protocol"
            records[-1]["protocol_error"] = str(exc)
            if on_record: on_record(records[-1])
            cause = "malformed-protocol"
            if retry_index >= protocol_retries:
                raise AdapterInvocationError("malformed-protocol", str(exc), records[-1]) from exc
    raise AssertionError("unreachable")


def load_suites(paths: list[Path], selected_case: str | None) -> list[dict[str, Any]]:
    suites: list[dict[str, Any]] = []
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        cases = data.get("cases", [])
        for case in cases:
            validate_case_contract(case)
        if selected_case:
            cases = [case for case in cases if f"{data.get('suite')}/{case.get('id')}" == selected_case]
        if cases:
            suites.append({"suite": data["suite"], "version": data["version"], "cases": cases})
    return suites


UNSUPPORTED_PASS_REASON = re.compile(
    r"(?:\b(?:absent|omitted|lacks?|missing|never demonstrates|fails? to show|not (?:shown|provided|performed|present|explicit(?:ly)?)|"
    r"not performed|promised later|implicit only|did not explicitly|only implied|promised (?:later|for later)|future work)\b|"
    r"لا يتضمن|يفتقد|غائب|لم ينفذ|لم يتم تنفيذ|سيقوم لاحق[ًاا]|لم (?:يذكر|يقدم|ينفذ|يعرض) صراحة|الدليل (?:غائب|غير موجود))",
    flags=re.IGNORECASE,
)


def validate_grade(grade: dict[str, Any], expected: list[str], transcript: list[dict[str, Any]], artifacts: list[dict[str, Any]] | None = None, on_result: Any | None = None) -> list[dict[str, Any]]:
    results = grade.get("results")
    if not isinstance(results, list) or len(results) != len(expected):
        raise RuntimeError("grader must return one result per expected criterion")
    normalized: list[dict[str, Any]] = []
    for criterion, item in zip(expected, results):
        if not isinstance(item, dict) or set(item) != {"verdict", "evidence", "reason"} or item.get("verdict") not in {"pass", "fail"}:
            raise RuntimeError("each grader result needs verdict pass or fail")
        evidence = item.get("evidence")
        reason = item.get("reason")
        if not isinstance(evidence, dict) or set(evidence) - {"source", "turn", "artifact_path", "quote"} or not isinstance(reason, str) or not reason.strip():
            raise RuntimeError("each grader result needs exact evidence and concise reasoning")
        passed = item["verdict"] == "pass"
        source, quote = evidence.get("source"), evidence.get("quote")
        expected_keys = {"response": {"source", "turn", "quote"}, "artifact": {"source", "artifact_path", "quote"}, "absent": {"source", "quote"}}
        if source not in expected_keys or set(evidence) != expected_keys[source] or not isinstance(quote, str) or not quote.strip() or len(quote) > 800:
            raise RuntimeError("grader evidence source and quote are required")
        if source == "response":
            turn = evidence.get("turn")
            messages = [m for m in transcript if m.get("role") == "assistant" and m.get("turn") == turn]
            if len(messages) != 1 or quote not in messages[0].get("content", ""):
                raise RuntimeError("evidence quote must occur in the identified assistant turn")
        elif source == "artifact":
            matches = [a for a in (artifacts or []) if a.get("path") == evidence.get("artifact_path")]
            if len(matches) != 1 or quote not in matches[0].get("content", ""):
                raise RuntimeError("evidence quote must occur in the identified artifact")
        elif passed or not quote.startswith("ABSENT:"):
            raise RuntimeError("only FAIL may use ABSENT: evidence")
        protocol_adjustment = None
        if passed and UNSUPPORTED_PASS_REASON.search(reason):
            protocol_adjustment = {
                "kind": "contradictory-pass-downgraded",
                "original_verdict": item["verdict"],
                "original_evidence": evidence,
            }
            passed = False
            evidence = {"source": "absent", "quote": f"ABSENT: {criterion}"[:800]}
        normalized_item = {
            "criterion": criterion,
            "passed": passed,
            "verdict": "pass" if passed else "fail",
            "evidence": evidence,
            "reason": reason,
        }
        if protocol_adjustment is not None:
            normalized_item["grader_protocol_adjustment"] = protocol_adjustment
        normalized.append(normalized_item)
        if on_result: on_result(normalized[-1], len(normalized))
    return normalized


def locale_criterion(locale: str) -> str:
    normalized = canonical_locale(locale)
    if normalized == "ar-MSA":
        return (
            "the response is written in clear simplified Modern Standard Arabic without colloquial dialect; foreign and "
            "technical terms remain in their original language and are explained in Arabic on first use when needed"
        )
    return "the response is written in English and matches the learner's level and register"


def expected_criteria(case: dict[str, Any]) -> list[str]:
    expected = list(case["expected"])
    locale = case.get("locale")
    if isinstance(locale, str) and locale.strip():
        expected.append(locale_criterion(locale.strip()))
    return expected


def deterministic_language_check(text: str, locale: str | None) -> dict[str, Any]:
    """Reject a response whose dominant script contradicts an Arabic/English locale."""
    if locale not in {"ar-MSA", "en"}:
        return {"passed": False, "reason": f"explicit canonical locale required, got {locale!r}"}
    try:
        normalized = canonical_locale(locale)
    except ValueError:
        return {"passed": False, "reason": f"unsupported locale {locale!r}"}
    arabic = len(ARABIC_LETTER.findall(text))
    latin = len(LATIN_LETTER.findall(text))
    other = sum(
        1
        for character in text
        if unicodedata.category(character).startswith("L")
        and not ARABIC_LETTER.fullmatch(character)
        and not LATIN_LETTER.fullmatch(character)
    )
    letters = arabic + latin + other

    if normalized == "ar-MSA":
        share = arabic / letters if letters else 0.0
        markers = sorted(set(COLLOQUIAL_ARABIC_MARKER.findall(text)))
        dialect_passed = not markers
        passed = arabic >= 20 and share >= 0.55 and other == 0 and dialect_passed
        target = "Arabic"
    else:
        share = latin / letters if letters else 0.0
        passed = latin >= 20 and share >= 0.70 and other == 0
        target = "Latin"

    dialect = f", colloquial Arabic markers {markers}" if normalized == "ar-MSA" else ""
    return {
        "passed": passed,
        "reason": (
            f"deterministic script check for {target}: {arabic} Arabic letters, "
            f"{latin} Latin letters, {other} other-script letters, target-script share {share:.1%}{dialect}"
        ),
    }


def deterministic_terminology_check(text: str, prompt: str) -> dict[str, Any]:
    """Preserve requested technical terms and verify Arabic first-use definitions."""
    required: list[str] = []
    missing: list[str] = []
    missing_definitions: list[str] = []
    transliterated: list[str] = []
    combined = prompt.casefold()
    established_context = bool(re.search(r"(?:خلصنا|اكتمل|completed|resume|continue|تابع|واصل)", combined))
    for term, variants in sorted(TECHNICAL_TERMS.items(), key=lambda item: len(item[0]), reverse=True):
        requested = term.casefold() in combined or any(variant in prompt for variant in variants)
        if not requested or any(term.casefold() in longer.casefold() for longer in required):
            continue
        required.append(term)
        positions = [match.start() for match in re.finditer(re.escape(term), text, flags=re.IGNORECASE)]
        if not positions:
            missing.append(term)
        elif ARABIC_LETTER.search(prompt) and not established_context:
            markers = {
                "API": r"(?:واجهة|تواصل|اتصال|طلب)",
                "Database Replication": r"(?:نسخ|تزامن|متزامن)",
                "Replication": r"(?:نسخ|تزامن|متزامن)",
                "Contract Test": r"(?:اختبار|اتفاق|تكامل)",
                "Prompt": r"(?:تعليمات|طلب|نص)",
                "Database": r"(?:بيانات|مخزن|منظم)",
            }[term]
            definition = False
            for position in positions:
                start = max(text.rfind(mark, 0, position) for mark in ".!?؟\n؛;") + 1
                ends = [text.find(mark, position) for mark in ".!?؟\n؛;" if text.find(mark, position) >= 0]
                end = min(ends) if ends else len(text)
                span = text[start:end]
                if re.search(r"(?:يعني|تعني|هو|هي|اختصار|يقصد\s+به|تسمح|تحافظ|آلية)", span) and re.search(markers, span): definition = True
                if re.search(r"\((?=[^)]*[\u0600-\u06ff])(?=[^)]*" + markers + r")[^)]{4,}\)", span): definition = True
                if definition: break
            if not definition:
                missing_definitions.append(term)
        transliterated.extend(variant for variant in variants if variant in text)
    passed = not missing and not missing_definitions and not transliterated
    return {
        "passed": passed,
        "reason": (
            f"deterministic terminology check: required {required}, missing {missing}, "
            f"missing first-use Arabic definitions {missing_definitions}, "
            f"Arabic transliterations {sorted(set(transliterated))}"
        ),
    }


def deterministic_api_replication_contrast_check(text: str, prompt: str) -> dict[str, Any]:
    """Verify the observable functional contrast requested by the API/replication case."""
    applicable = "api" in prompt.casefold() and "database replication" in prompt.casefold()
    if not applicable:
        return {"passed": True, "reason": "deterministic API/replication contrast check not applicable"}
    folded = text.casefold()
    communication = bool(
        re.search(r"(?:واجهة|تواصل|اتصال|طلب|interface|communicat|request)", folded)
    )
    synchronized_copies = bool(
        re.search(r"(?:نسخ|نسخة|تزامن|متزامن|replica|synchroni[sz]|cop(?:y|ies))", folded)
    )
    contrast = bool(re.search(r"(?:بينما|أما|في المقابل|ولكن|whereas|while|unlike|but)", folded))
    terms = "api" in folded and "database replication" in folded
    passed = terms and communication and synchronized_copies and contrast
    return {
        "passed": passed,
        "reason": (
            "deterministic API/replication contrast check: "
            f"original terms {terms}, communication role {communication}, "
            f"synchronized-copy role {synchronized_copies}, explicit contrast {contrast}"
        ),
    }


def learner_opted_into_assessment(turns: list[dict[str, Any]]) -> bool:
    """Support old behavioral fixtures; new simulations pass structured intent."""
    learner_turns = [turn for turn in turns if turn.get("role") in {"user", "learner"}]
    state = "none"
    for turn in learner_turns:
        try:
            intent = intent_from_turn(turn, allow_legacy=True)
        except ValueError:
            return False
        if intent == "accept": state = "accept"
        elif intent == "decline": state = "decline"
        if turn.get("assessment_boundary") in {"complete", "new-unit"}: state = "none"
    return state == "accept"


class AssessmentMatch:
    def __init__(self, text: str):
        self.text = text

    def group(self, _index: int = 0) -> str:
        return self.text


def assessment_prompt_match(text: str) -> AssessmentMatch | None:
    """Find an actual knowledge task without treating navigation or quoted examples as assessment."""
    visible = re.sub(r"```.*?```|`[^`]*`|«[^»]*»|“[^”]*”|\"[^\"]*\"", " ", text, flags=re.DOTALL)
    question_lines = [line for line in visible.splitlines() if "?" in line or "؟" in line]
    navigation_questionnaire = bool(question_lines) and all(NAVIGATION_CONTEXT.search(line) for line in question_lines)
    outside_fence = True
    for original in text.splitlines():
        line = original.strip().lstrip("-*#> ")
        if line.startswith("```"):
            outside_fence = not outside_fence
            continue
        if not outside_fence or not line:
            continue
        # Examples and code are evidence supplied by the teacher, not learner tasks.
        line = re.sub(r"`[^`]*`|«[^»]*»|“[^”]*”|\"[^\"]*\"", " ", line).strip()
        if not line:
            continue
        for candidate in re.split(r"(?<=[.!؛;؟?])\s+", line):
            candidate = candidate.strip()
            if not candidate: continue
            if re.search(r"(?:answer|أجب|جاوب)\s+(?:these|the following|هذه|الآتية)?\s*(?:\w+\s+)?questions|read .*answer|اقرأ .*أجب", candidate, re.I):
                if navigation_questionnaire: continue
                return AssessmentMatch(candidate)
            if ASSESSMENT_QUESTION.search(candidate):
                if NAVIGATION_CONTEXT.search(candidate): continue
                return AssessmentMatch(candidate)
            task_candidate = re.sub(r"^(?:current action|your action|الخطوة الحالية|إجراءك الحالي|الإجراء الآن)\s*[:：-]?\s*", "", candidate, flags=re.I)
            task_candidate = re.sub(r"^(?:if you want|إذا أردت|إن أردت|إن أحببت)[،,]?\s*", "", task_candidate, flags=re.I)
            imperative = ASSESSMENT_IMPERATIVE.match(task_candidate)
            if imperative:
                if NON_ASSESSMENT_ACTION.search(candidate) and not re.search(r"(?:answer|solve|explain why|أجب|حل|فسر|لماذا)", candidate, re.I): continue
                return AssessmentMatch(candidate)
    return None


def deterministic_assessment_check(
    text: str,
    turns: list[dict[str, Any]] | None = None,
    learner_event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Prevent the first test item or task from being bundled with its invitation."""
    current = learner_event
    structured = current is not None
    if current is None:
        current = next((turn for turn in reversed(turns or []) if turn.get("role") in {"user", "learner"}), None)
        structured = current is not None and "assessment_intent" in current
    if structured:
        try:
            opted_in = learner_opted_into_assessment(turns or ([current] if current else []))
        except ValueError:
            return {
                "passed": False,
                "reason": "structured assessment intent is missing, malformed, or contradictory",
            }
        source = "structured learner assessment_intent"
    else:
        opted_in = learner_opted_into_assessment(turns or [])
        source = "legacy learner text"
    if opted_in:
        return {"passed": True, "reason": f"learner explicitly opted into assessment via {source}"}
    match = assessment_prompt_match(text)
    if match:
        excerpt = " ".join(match.group(0).split())[:120]
        return {
            "passed": False,
            "reason": f"deterministic opt-in check found an assessment prompt before consent: {excerpt!r}",
        }
    return {
        "passed": True,
        "reason": "deterministic opt-in check found no assessment task or knowledge question before consent",
    }


def deterministic_completeness_check(
    text: str,
    prompt: str = "",
    learner_event: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply strict teaching length, with a bounded exception for accepted assessment tasks."""
    stripped = text.strip()
    word_count = len(stripped.split())
    child_lesson = any(
        marker in prompt.casefold() for marker in ("طفل", "ابتدائي", "primary school", "child")
    )
    substantive_minimum = 40 if child_lesson else 12
    intent = "missing"
    if learner_event is not None:
        try:
            intent = intent_from_turn(learner_event, allow_legacy=False)
        except ValueError:
            intent = "invalid"
    assessment_task = assessment_prompt_match(stripped) is not None
    short_assessment = intent == "accept" and assessment_task
    minimum_words = 8 if short_assessment else substantive_minimum
    minimum_characters = 30 if short_assessment else 1
    fences_closed = stripped.count("```") % 2 == 0
    stack: list[str] = []; pairs = {")": "(", "]": "[", "}": "{"}; in_double = False
    for character in stripped.replace("```", ""):
        if character == '"': in_double = not in_double
        elif not in_double and character in "([{": stack.append(character)
        elif not in_double and character in pairs:
            if not stack or stack.pop() != pairs[character]: stack.append("INVALID"); break
    pairs_closed = not stack and not in_double and stripped.count("«") == stripped.count("»") and stripped.count("“") == stripped.count("”")
    final_line = next((line.strip() for line in reversed(stripped.splitlines()) if line.strip()), "")
    structural_ending = stripped.endswith((".", "!", "?", "؟", "…", "`", "»", "”", '"', "'", ")", "]", "}"))
    structural_ending = structural_ending or bool(re.search(r"TEACH-ME:v2:[^\s`]+`?$", final_line))
    structural_ending = structural_ending or bool(re.match(r"^(?:[-*]|\d+[.)])\s+\S+", final_line))
    dangling = bool(re.search(r"(?:\b(?:and|or|because|to|the|a|an|with|for|of|in|but|then|that)|(?:من|إلى|في|ثم|لكن|لأن))\s*$", stripped, re.I))
    terminal = structural_ending and fences_closed and pairs_closed and not dangling
    passed = word_count >= minimum_words and len(stripped) >= minimum_characters and terminal
    return {
        "passed": passed,
        "reason": (
            f"deterministic completeness check ({'accepted assessment task' if short_assessment else 'substantive response'}): "
            f"{word_count} words, minimum {minimum_words}; {len(stripped)} characters, "
            f"minimum {minimum_characters}; structurally closed ending {terminal}; "
            f"fences closed {fences_closed}; paired delimiters closed {pairs_closed}; "
            f"structured assessment intent {intent}"
        ),
    }


def deterministic_child_concept_order_check(text: str, prompt: str) -> dict[str, Any]:
    """Verify that an introductory child fractions lesson establishes equal parts before notation."""
    lowered_prompt = prompt.casefold()
    applicable = (
        any(marker in lowered_prompt for marker in ("طفل", "ابتدائي", "primary school", "child"))
        and any(marker in lowered_prompt for marker in ("كسر", "كسور", "fraction"))
    )
    if not applicable:
        return {"passed": True, "reason": "deterministic child concept-order check not applicable"}
    equal_match = EQUAL_PARTS.search(text)
    notations = list(FRACTION_NOTATION.finditer(text))
    unique_notations = sorted({match.group(0).replace(" ", "") for match in notations})
    ordered = equal_match is not None and (not notations or equal_match.start() < notations[0].start())
    passed = ordered and len(unique_notations) <= 1
    return {
        "passed": passed,
        "reason": (
            "deterministic child concept-order check: "
            f"equal-parts explanation {'precedes' if ordered else 'does not precede'} notation; "
            f"introductory fraction symbols {unique_notations}"
        ),
    }


def deterministic_child_onboarding_check(text: str, prompt: str) -> dict[str, Any]:
    """Require an explicit from-zero start and a concrete, non-shaming child example."""
    lowered_prompt = prompt.casefold()
    applicable = any(
        marker in lowered_prompt for marker in ("طفل", "ابتدائي", "primary school", "child")
    )
    if not applicable:
        return {"passed": True, "reason": "deterministic child onboarding check not applicable"}
    topic = r"(?:الكسور?|الكسر|fraction(?:s)?)"
    starts_from_zero = bool(re.search(
        rf"(?:من الصفر|سنبدأ من (?:البداية|الصفر)|مبتدئ(?:ة)? تمامًا|start(?:ing)? from (?:zero|the beginning))|(?:لا (?:تعرف|يعرف)|لا توجد .*معرفة سابقة|لن أفترض .*معرفة سابقة|لم .* من قبل).{{0,45}}{topic}|(?:no prior knowledge|never studied|know nothing about|new to).{{0,45}}{topic}|{topic}.{{0,45}}(?:from zero|from the beginning|no prior knowledge)",
        text, flags=re.IGNORECASE))
    concrete = bool(CHILD_CONCRETE_EXAMPLE.search(text))
    shaming = sorted(set(SHAMING_LANGUAGE.findall(text)))
    passed = starts_from_zero and concrete and not shaming
    return {
        "passed": passed,
        "reason": (
            "deterministic child onboarding check: "
            f"from-zero acknowledgement {starts_from_zero}, concrete example {concrete}, "
            f"shaming markers {shaming}"
        ),
    }


def deterministic_text_quality_check(text: str) -> dict[str, Any]:
    """Reject malformed Unicode structure without maintaining a vocabulary blacklist."""
    repeated_matches = list(REPEATED_ARABIC_DIACRITIC.finditer(text))
    repeated_marks = sorted({match.group(0) for match in repeated_matches})
    affected_tokens = sorted(
        {
            token.group(0)
            for token in ARABIC_TOKEN.finditer(text)
            if any(token.start() <= mark.start() < token.end() for mark in repeated_matches)
        }
    )
    replacement_character = "\ufffd" in text
    control_codepoints = sorted(
        {
            f"U+{ord(character):04X}"
            for character in text
            if unicodedata.category(character) == "Cc" and character not in "\n\r\t"
        }
    )
    passed = not repeated_marks and not replacement_character and not control_codepoints
    return {
        "passed": passed,
        "reason": (
            "deterministic text-quality check: "
            f"repeated Arabic diacritics {repeated_marks}, affected tokens {affected_tokens}, "
            f"replacement character {replacement_character}, disallowed controls {control_codepoints}"
        ),
    }


def enforce_deterministic_checks(
    criteria: list[dict[str, Any]],
    response: str,
    locale: str | None,
    turns: list[dict[str, str]],
    prompt: str,
) -> list[dict[str, Any]]:
    """Make hard policy checks necessary for a pass even when the AI grader errs."""
    language = deterministic_language_check(response, locale)
    assessment = deterministic_assessment_check(response, turns)
    child_concept_order = deterministic_child_concept_order_check(response, prompt)
    child_onboarding = deterministic_child_onboarding_check(response, prompt)
    terminology = deterministic_terminology_check(response, prompt)
    api_replication_contrast = deterministic_api_replication_contrast_check(response, prompt)
    assessment_criterion_present = False
    for item in criteria:
        criterion = item["criterion"].lower()
        if (
            "response is written in" in criterion
            or "response uses the requested locale" in criterion
            or "response remains in english" in criterion
        ):
            item["passed"] = bool(language["passed"])
            item["reason"] = f"{language['reason']} (authoritative)"
            continue
        elif "is preserved in its original script and defined in arabic on first use" in criterion:
            item["passed"] = bool(terminology["passed"])
            item["reason"] = f"{terminology['reason']} (authoritative)"
            continue
        elif (
            "communication interface from maintaining synchronized data copies" in criterion
            or "api is distinguished from maintaining synchronized database copies" in criterion
        ):
            item["passed"] = bool(api_replication_contrast["passed"])
            item["reason"] = f"{api_replication_contrast['reason']} (authoritative)"
            continue
        elif "no assessment question is asked before learner opt-in" in criterion:
            assessment_criterion_present = True
            item["passed"] = bool(assessment["passed"])
            item["reason"] = f"{assessment['reason']} (authoritative)"
            continue
        elif "one central concept is taught before notation" in criterion:
            item["passed"] = bool(child_concept_order["passed"])
            item["reason"] = f"{child_concept_order['reason']} (authoritative)"
            continue
        elif "acknowledges that the child is starting from zero" in criterion:
            item["passed"] = bool(child_onboarding["passed"])
            item["reason"] = f"{child_onboarding['reason']} (authoritative)"
            continue
    completeness = deterministic_completeness_check(response, prompt)
    text_quality = deterministic_text_quality_check(response)
    language_index = next(
        (
            index
            for index, item in enumerate(criteria)
            if "response is written in" in item["criterion"].lower()
            or "response uses the requested locale" in item["criterion"].lower()
        ),
        len(criteria),
    )
    criteria.insert(
        language_index,
        {
            "criterion": "foreign and technical terms remain in their original language",
            "passed": terminology["passed"],
            "reason": terminology["reason"],
        },
    )
    criteria.insert(
        language_index,
        {
            "criterion": "the response is complete and not visibly truncated",
            "passed": completeness["passed"],
            "reason": completeness["reason"],
        },
    )
    criteria.insert(
        language_index,
        {
            "criterion": "the response contains no malformed Unicode sequences or repeated Arabic diacritics",
            "passed": text_quality["passed"],
            "reason": text_quality["reason"],
        },
    )
    if not assessment_criterion_present:
        criteria.insert(
            language_index,
            {
                "criterion": "no assessment question is asked before learner opt-in",
                "passed": assessment["passed"],
                "reason": assessment["reason"],
            },
        )
    return criteria


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        stream.flush(); os.fsync(stream.fileno())
    temporary.replace(path)


def validate_model_evidence(output: dict[str, Any], role: str) -> None:
    required = {"model", "settings", "adapter_version", "raw_result", "invocation_id", "timing"}
    if not required <= set(output): raise RuntimeError(f"{role} evidence missing: {sorted(required - set(output))}")
    if not isinstance(output["model"], str) or not output["model"].strip(): raise RuntimeError(f"{role} model identity missing")
    if not isinstance(output["settings"], dict) or not output["settings"]: raise RuntimeError(f"{role} model settings missing")
    if not isinstance(output["adapter_version"], str) or not output["adapter_version"]: raise RuntimeError(f"{role} adapter version missing")
    if not isinstance(output["invocation_id"], str) or not output["invocation_id"]: raise RuntimeError(f"{role} invocation identifier missing")
    if not isinstance(output["raw_result"], dict): raise RuntimeError(f"{role} raw result missing")
    timing = output["timing"]
    if not isinstance(timing, dict) or set(timing) != {"started_at", "completed_at", "duration_seconds"}: raise RuntimeError(f"{role} timing missing")
    if not all(isinstance(timing[key], str) and timing[key] for key in ("started_at", "completed_at")) or not isinstance(timing["duration_seconds"], (int, float)) or timing["duration_seconds"] < 0: raise RuntimeError(f"{role} timing malformed")


def validate_release_model(output: dict[str, Any], role: str, release_evidence: bool, expected_model: str) -> None:
    if not release_evidence: return
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", expected_model):
        raise RuntimeError(f"{role} expected model must be an exact provider/model identifier")
    requested_model = expected_model.split("/", 1)[1]
    if output.get("model") != expected_model or output.get("settings", {}).get("model") != requested_model:
        raise RuntimeError(f"{role} release evidence does not match expected model {expected_model}")


def validate_response_output(output: dict[str, Any]) -> str:
    if isinstance(output.get("evaluation_error"), dict):
        raise NonRetryableEvaluationError(f"adapter completed with {output['evaluation_error'].get('kind', 'evaluation-error')}")
    response = output.get("response")
    if not isinstance(response, str) or not response.strip():
        raise RuntimeError("response adapter returned no non-empty response")
    validate_model_evidence(output, "response")
    return response


def verify_release_commit(candidate: str, root: Path = ROOT) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", candidate or ""): raise RuntimeError("release candidate must be a full lowercase SHA-1")
    commands = {
        "head": ["git", "rev-parse", "HEAD"], "origin_main": ["git", "rev-parse", "origin/main"],
        "merge_base": ["git", "merge-base", "HEAD", "origin/main"], "tracked_status": ["git", "status", "--porcelain", "--untracked-files=no"],
    }
    observed = {}
    for name, command in commands.items():
        done = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
        observed[name] = {"command": command, "returncode": done.returncode, "stdout": done.stdout.strip(), "stderr": done.stderr.strip()}
        if done.returncode: raise RuntimeError(f"release git verification failed: {name}")
    if any(observed[name]["stdout"] != candidate for name in ("head", "origin_main", "merge_base")): raise RuntimeError("candidate, HEAD, origin/main, and merge base must match")
    if observed["tracked_status"]["stdout"]: raise RuntimeError("release evidence requires a clean tracked worktree")
    return {"verified_sha": candidate, "checks": observed}


def main() -> int:
    global _ACTIVE_REPORT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suites", nargs="*", type=Path)
    parser.add_argument("--response-command", help="command that generates a response from a JSON payload")
    parser.add_argument("--grader-command", help="command that grades a response from a JSON payload")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--case", help="run one suite/case-id")
    parser.add_argument("--output", type=Path, default=Path("reports/behavioral-evals.json"))
    parser.add_argument("--pass-threshold", type=float, default=0.90)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--protocol-retries", type=int, default=1)
    parser.add_argument("--candidate-commit", default=None)
    parser.add_argument("--release-evidence", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--expected-response-model", default="codex/gpt-5.6-sol")
    parser.add_argument("--expected-grader-model", default="codex/gpt-5.6-sol")
    parser.add_argument("--response-api-key-env", default=None)
    parser.add_argument("--grader-api-key-env", default=None)
    args = parser.parse_args()

    if not 0 <= args.pass_threshold <= 1:
        parser.error("--pass-threshold must be between 0 and 1")
    if not 0 <= args.protocol_retries <= 2:
        parser.error("--protocol-retries must be between 0 and 2")
    if args.response_api_key_env not in {None, OPENAI_API_KEY_ENV} or args.grader_api_key_env not in {None, OPENAI_API_KEY_ENV}:
        parser.error("adapter API key environment options accept only OPENAI_API_KEY")
    if any(value and not os.environ.get(value) for value in (args.response_api_key_env, args.grader_api_key_env)):
        parser.error("requested adapter API key environment variable is missing")
    paths = args.suites or (
        sorted((ROOT / "evals").glob("*.yaml"))
        + sorted((ROOT / "domain-packs").glob("*/evals.yaml"))
    )
    suites = load_suites(paths, args.case)
    case_count = sum(len(suite["cases"]) for suite in suites)
    if not case_count:
        parser.error("no matching eval cases")
    if args.validate_only:
        print(f"Behavioral eval runner loaded {len(suites)} suites and {case_count} cases")
        return 0
    if not args.response_command or not args.grader_command:
        parser.error("execution requires both --response-command and --grader-command")

    if args.release_evidence and not args.candidate_commit:
        parser.error("--release-evidence requires --candidate-commit")
    if args.release_evidence and (args.case or case_count < 90 or args.pass_threshold != 0.90):
        parser.error("release evidence requires the full case set and the committed 0.90 threshold")
    git_verification = verify_release_commit(args.candidate_commit) if args.release_evidence else None
    if args.candidate_commit and not args.release_evidence:
        parser.error("--candidate-commit is accepted only with --release-evidence")
    if args.release_evidence:
        reports_root = (ROOT / "reports").resolve(); destination = args.output.resolve()
        if not destination.is_relative_to(reports_root): parser.error("release evidence output must be under reports/")
        ignored = subprocess.run(["git", "check-ignore", "-q", str(destination)], cwd=ROOT, check=False)
        if ignored.returncode != 0: parser.error("release evidence output must be Git-ignored")

    generated_at = datetime.now(timezone.utc)
    run_started = time.monotonic()
    results: list[dict[str, Any]] = []
    invocation_journal: list[dict[str, Any]] = []
    resume_active: dict[str, Any] | None = None
    run_configuration = {
        "suite_hashes": {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths},
        "contract_hashes": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in [ROOT / "SKILL.md", ROOT / "fixtures" / "eval-registry.yaml", *sorted((ROOT / "references").glob("*.md")), *sorted((ROOT / "domain-packs").glob("*/PACK.md"))]},
        "selected_case": args.case, "response_command": safe_adapter_command(args.response_command),
        "grader_command": safe_adapter_command(args.grader_command), "protocol_retries": args.protocol_retries,
        "timeout_seconds": args.timeout, "pass_threshold": args.pass_threshold,
        "expected_response_model": args.expected_response_model, "expected_grader_model": args.expected_grader_model,
        "response_credential_env": args.response_api_key_env, "grader_credential_env": args.grader_api_key_env,
    }
    configuration_sha256 = hashlib.sha256(json.dumps(run_configuration, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    report: dict[str, Any] = {
        "schema_version": "2.0.0", "status": "running", "release_evidence": args.release_evidence,
        "candidate_commit": git_verification["verified_sha"] if git_verification else None,
        "verified_commit": git_verification, "run_id": f"behavioral-{generated_at.strftime('%Y%m%dT%H%M%S.%fZ')}",
        "generated_at": generated_at.isoformat(), "resume": {"requested": args.resume, "completed_case_keys": []},
        "run_configuration": run_configuration, "run_configuration_sha256": configuration_sha256,
        "commands": {"response": safe_adapter_command(args.response_command), "grader": safe_adapter_command(args.grader_command),
                     "response_credential_env": args.response_api_key_env, "grader_credential_env": args.grader_api_key_env,
                     "protocol_retries": args.protocol_retries, "timeout_seconds": args.timeout},
        "instruction_sources": {}, "prompt_packets": {}, "invocations": invocation_journal, "results": results,
    }
    completed_keys: set[str] = set()
    if args.resume and args.output.exists():
        previous = json.loads(args.output.read_text(encoding="utf-8"))
        if previous.get("status") not in {"running", "failed"} or previous.get("verified_commit") != git_verification or previous.get("run_configuration_sha256") != configuration_sha256:
            raise RuntimeError("resume report is stale or bound to different Git evidence")
        results.extend(previous.get("results", [])); invocation_journal.extend(previous.get("invocations", []))
        report["instruction_sources"].update(previous.get("instruction_sources", {})); report["prompt_packets"].update(previous.get("prompt_packets", {}))
        resume_active = previous.get("active_case")
        completed_keys = {f"{item['suite']}/{item['case_id']}" for item in results}
        report["resume"] = {"requested": True, "completed_case_keys": sorted(completed_keys), "previous_run_id": previous.get("run_id")}
        if resume_active: report["active_case"] = resume_active
    write_report(args.output, report)
    _ACTIVE_REPORT = (args.output, report)
    for suite in suites:
        for case in suite["cases"]:
            case_key = f"{suite['suite']}/{case['id']}"
            if case_key in completed_keys: continue
            case_expected = expected_criteria(case)
            turns = case.get("turns") or [{"role": "user", "content": case["prompt"]}]
            packet = immutable_prompt_packet(suite["suite"], case)
            for source in packet["instruction_sources"]:
                report["instruction_sources"].setdefault(source["sha256"], {"path": source["path"], "content": source["content"]})
            stored_packet = dict(packet)
            stored_packet["instruction_sources"] = [{"path": source["path"], "sha256": source["sha256"], "content_ref": source["sha256"]} for source in packet["instruction_sources"]]
            report["prompt_packets"][packet["sha256"]] = stored_packet
            active = resume_active if resume_active and resume_active.get("case_key") == case_key else {}
            history: list[dict[str, Any]] = list(active.get("transcript", []))
            generated: dict[str, Any] = active.get("last_generation", {})
            response_attempts = int(active.get("response_attempts", 0))
            attempt_log: list[dict[str, Any]] = list(active.get("attempt_log", []))
            selected_attempts: list[int] = list(active.get("selected_attempts", []))
            turn_guard_results: list[dict[str, Any]] = list(active.get("turn_guard_results", []))
            all_artifacts: list[dict[str, Any]] = list(active.get("artifacts", []))
            completed_turns = len([item for item in history if item.get("role") == "assistant"])
            pending_records = list(active.get("attempts", []))
            pending_generation = pending_records[-1].get("result") if pending_records and pending_records[-1].get("status") == "completed" and active.get("turn", 0) > completed_turns else None
            for turn_index, turn in enumerate(turns, 1):
                if turn_index <= completed_turns: continue
                prompt = turn["content"]
                current_turns = [item for item in history if item.get("role") == "user"] + [dict(turn, turn=turn_index)]
                generation_payload = {
                    "type": "generate",
                    "suite": suite["suite"],
                    "case_id": case["id"],
                    "locale": case["locale"],
                    "prompt": prompt,
                    "history": history,
                    "turn_index": turn_index,
                    "turn_count": len(turns),
                    "attempt_index": 1,
                    "prompt_packet": packet,
                }
                if pending_generation is not None and turn_index == active.get("turn"):
                    generated, records, response = pending_generation, pending_records, validate_response_output(pending_generation)
                    validate_release_model(pending_generation, "response", args.release_evidence, args.expected_response_model)
                    pending_generation = None
                else:
                    report["active_case"] = {"case_key": case_key, "stage": "response-invoking", "turn": turn_index, "attempts": [],
                        "transcript": history, "attempt_log": attempt_log, "last_generation": generated,
                        "response_attempts": response_attempts, "selected_attempts": selected_attempts,
                        "turn_guard_results": turn_guard_results, "artifacts": all_artifacts}
                    write_report(args.output, report)
                    def checkpoint_response(record: dict[str, Any]) -> None:
                        if record not in invocation_journal: invocation_journal.append(record)
                        report["active_case"]["attempts"] = [item for item in invocation_journal if item.get("role") == "response" and item.get("case_key") == case_key and item.get("turn_index") == turn_index]
                        write_report(args.output, report)
                    generated, records, response = invoke_protocol(
                        args.response_command, generation_payload, args.timeout, "response", args.protocol_retries,
                        lambda output: (validate_response_output(output), validate_release_model(output, "response", args.release_evidence, args.expected_response_model))[0],
                        checkpoint_response, args.response_api_key_env,
                    )
                report["active_case"].update({"stage": "response", "attempts": records})
                write_report(args.output, report)
                response_attempts += len(records)
                guards: dict[str, Any] = {}
                for guard_name, guard_function in (
                    ("language", lambda: deterministic_language_check(response, case["locale"])),
                    ("assessment", lambda: deterministic_assessment_check(response, current_turns)),
                    ("completeness", lambda: deterministic_completeness_check(response, prompt)),
                    ("terminology", lambda: deterministic_terminology_check(response, prompt)),
                    ("text_quality", lambda: deterministic_text_quality_check(response)),
                ):
                    guards[guard_name] = guard_function()
                    report["active_case"].update({"stage": f"guard:{guard_name}", "guards": guards})
                    write_report(args.output, report)
                turn_guard_results.append({"turn_index": turn_index, "guards": guards})
                report["active_case"].update({"stage": "guards", "guards": guards})
                write_report(args.output, report)
                failures = [(name, check) for name, check in guards.items() if not check["passed"]]
                all_artifacts.extend(dict(item, turn=turn_index) for item in generated.get("artifact_evidence", []))
                for index, record in enumerate(records, response_attempts - len(records) + 1):
                    attempt_log.append(
                        {
                            "sequence": index,
                            "turn_index": turn_index,
                            "attempt_index": 1,
                            "protocol_retry_cause": record.get("retry_cause"),
                            "retry_feedback": record.get("retry_feedback"),
                            "status": record["status"],
                            "model": record.get("result", {}).get("model"),
                            "raw_result": record.get("result"),
                            "accepted": index == response_attempts and not failures,
                            "deterministic_guards": guards if index == response_attempts else None,
                            "rejection_reasons": (
                                [{"check": name, "reason": check["reason"]} for name, check in failures]
                                if index == response_attempts else []
                            ),
                        }
                    )
                selected_attempts.append(response_attempts)
                history.extend([dict(turn, turn=turn_index), {"role": "assistant", "turn": turn_index, "content": response}])
                report["active_case"].update({"stage": "turn-complete", "transcript": history, "attempt_log": attempt_log,
                    "last_generation": generated, "response_attempts": response_attempts, "selected_attempts": selected_attempts,
                    "turn_guard_results": turn_guard_results})
                report["active_case"]["artifacts"] = all_artifacts
                write_report(args.output, report)

            response = history[-1]["content"]
            raw_evidence = response
            artifacts = all_artifacts
            controlled = packet.get("controlled_inputs", {})
            grade_payload = {
                "type": "grade",
                "suite": suite["suite"], "case_id": case["id"],
                "ordered_transcript": history,
                "assessment_events": [{"turn": item["turn"], "intent": item.get("assessment_intent", "none"), "boundary": item.get("assessment_boundary", "continue")} for item in history if item["role"] == "user"],
                "case_context": controlled.get("context", {}).get("result", {}),
                "controlled_inputs": controlled,
                "artifacts": artifacts,
                "raw_final_response": raw_evidence,
                "criteria": case_expected,
                "evidence_requirements": (
                    "Judge observable behavior only. One verdict per criterion. PASS evidence must be an exact raw-response "
                    "turn or generated-artifact excerpt. FAIL may identify an absent requirement."
                ),
            }
            report["active_case"].update({"stage": "grader-invoking", "grader_attempts": []})
            write_report(args.output, report)
            def checkpoint_grader(record: dict[str, Any]) -> None:
                if record not in invocation_journal: invocation_journal.append(record)
                report["active_case"]["grader_attempts"] = [item for item in invocation_journal if item.get("role") == "grader" and item.get("case_key") == case_key]
                write_report(args.output, report)
            def checkpoint_criterion(result: dict[str, Any], index: int) -> None:
                report["active_case"].setdefault("validated_grader_results", []).append(result)
                report["active_case"]["stage"] = f"grader-result:{index}"
                write_report(args.output, report)
            graded, grader_records, normalized_grade = invoke_protocol(
                args.grader_command,
                grade_payload,
                args.timeout,
                "grader",
                args.protocol_retries,
                lambda output: (validate_model_evidence(output, "grader"), validate_release_model(output, "grader", args.release_evidence, args.expected_grader_model), validate_grade(output, case_expected, history, artifacts, checkpoint_criterion))[2],
                checkpoint_grader,
                args.grader_api_key_env,
            )
            report["active_case"].update({"stage": "grader", "grader_attempts": grader_records})
            write_report(args.output, report)
            criteria = enforce_deterministic_checks(
                normalized_grade,
                response,
                case["locale"],
                turns,
                turns[-1]["content"],
            )
            selected_records = [attempt_log[sequence - 1] for sequence in selected_attempts]
            deterministic_preflight_passed = all(item["accepted"] for item in selected_records)
            results.append(
                {
                    "suite": suite["suite"],
                    "case_id": case["id"],
                    "locale": case["locale"],
                    "routing": case["routing"],
                    "capabilities": case["capabilities"],
                    "fixture_refs": case.get("fixture_refs", {}),
                    "prompt_packet_ref": packet["sha256"],
                    "critical": bool(case.get("critical", False)),
                    "passed": deterministic_preflight_passed and all(item["passed"] for item in criteria),
                    "criteria": criteria,
                    "deterministic_guards": turn_guard_results,
                    "raw_transcript": history,
                    "response_attempts": response_attempts,
                    "attempt_log": attempt_log,
                    "selected_attempts": selected_attempts,
                    "selected_attempt": selected_attempts[-1],
                    "deterministic_preflight_passed": deterministic_preflight_passed,
                    "response_evidence": {
                        **{key: generated.get(key) for key in ("model", "settings", "adapter_version", "invocation_id", "timing")},
                        **{key: generated[key] for key in ("usage", "api", "effective_prompt_sha256") if key in generated},
                        "raw_result_ref": f"attempt_log:{selected_attempts[-1]}",
                    },
                    "grader_evidence": {
                        **{key: graded.get(key) for key in ("model", "settings", "adapter_version", "raw_result", "invocation_id", "timing")},
                        **{key: graded[key] for key in ("usage", "api", "effective_prompt_sha256") if key in graded},
                    },
                    "artifacts": artifacts,
                }
            )
            for record in [item for item in invocation_journal if item.get("case_key") == case_key]:
                raw_result = record.pop("result", None)
                if raw_result is not None:
                    record["result_sha256"] = hashlib.sha256(json.dumps(raw_result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            completed_keys.add(case_key)
            report["resume"]["completed_case_keys"] = sorted(completed_keys)
            report.pop("active_case", None)
            write_report(args.output, report)

    passed = sum(item["passed"] for item in results)
    pass_rate = passed / len(results)
    critical_failures = [f"{item['suite']}/{item['case_id']}" for item in results if item["critical"] and not item["passed"]]
    report.update({
        "status": "complete", "completed_at": datetime.now(timezone.utc).isoformat(), "duration_seconds": time.monotonic() - run_started,
        "summary": {
            "cases": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": pass_rate,
            "threshold": args.pass_threshold,
            "critical_failures": critical_failures,
            "response_invocations": sum(item.get("role") == "response" for item in invocation_journal),
            "grader_invocations": sum(item.get("role") == "grader" for item in invocation_journal),
            "grader_protocol_adjustments": sum(
                bool(criterion.get("grader_protocol_adjustment"))
                for result in results
                for criterion in result["criteria"]
            ),
        },
    })
    write_report(args.output, report)
    _ACTIVE_REPORT = None
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if pass_rate >= args.pass_threshold and not critical_failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, OSError, RuntimeError, subprocess.TimeoutExpired, yaml.YAMLError) as exc:
        if _ACTIVE_REPORT is not None:
            path, diagnostic = _ACTIVE_REPORT
            diagnostic["status"] = "failed"
            diagnostic["failure"] = {"type": type(exc).__name__, "message": str(exc)}
            diagnostic["completed_at"] = datetime.now(timezone.utc).isoformat()
            try: write_report(path, diagnostic)
            except OSError: pass
        print(f"Behavioral eval failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
