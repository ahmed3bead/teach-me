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
from evaluation_cost import (
    cost_accounting_snapshot,
    derive_cost_plan,
    invocation_reservation,
    load_cost_policy,
    reconcile_usage,
    uses_long_artifact_budget,
)

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
NAVIGATION_CLAUSE = re.compile(
    r"^(?:"
    r"what\s+(?:would\s+you\s+like\s+to|are\s+you\s+hoping\s+to)\s+(?:learn|study|use|build|create|do)(?:\s+next|\s+it\s+for)?|"
    r"(?:what|which)\s+(?:operating system|device|platform|language|book|source|course)\s+do\s+you\s+use|"
    r"what\s+(?:concept|idea|topic|subject)\s+(?:are\s+you\s+trying\s+to|do\s+you\s+want\s+to)\s+(?:understand|learn|study|work\s+on)|"
    r"what\s+(?:concept|idea|topic|subject)\s+do\s+you\s+want(?:\s+to\s+(?:understand|learn|study|work\s+on))?|"
    r"(?:what|which)\s+part\s+(?:feels|is)\s+(?:unclear|confusing)|"
    r"(?:what|which)\s+(?:is|are)\s+your\s+(?:job|work|goal|country|nationality|citizenship|residence|jurisdiction)|"
    r"how\s+much\s+time\s+can\s+you\s+(?:spend|set aside|study)(?:.*)?|"
    r"(?:ما|أي)\s+(?:نوع\s+)?(?:عملك|وظيفتك|هدفك|المهام(?:\s+التي)?(?:\s+تريد.*)?|بلد\s+الدراسة|جنسيتك|محل\s+إقامتك|بلد\s+إقامتك|المفهوم|الفكرة|الجزء)|"
    r"ما\s+(?:الدولة|البلد)\s+التي\s+تريد\s+(?:الدراسة|التقديم)\s+فيها|"
    r"كم\s+(?:وقت(?:ًا|ا)?|ساعة|دقيقة).*(?:تستطيع|يمكنك).*(?:التعلم|التعلّم|للتعلم|للتعلّم|الدراسة|للدراسة|تخصيص).*|"
    r"هل\s+(?:ستقد[ّ]?م|تستخدم|تستعمل).*(?:بلد\s+إقامتك|جهاز|منصة|نظام)|"
    r"هل\s+البرنامج\s+(?:قصير|طويل|قصير\s+أم\s+طويل)"
    r")$",
    flags=re.IGNORECASE,
)
NAVIGATION_SPLIT = re.compile(
    r"[،,]\s*(?=(?:and\s+)?(?:what|which|who|when|where|why|how|can)\b|و?(?:ما|أي|هل|كم)\b)",
    flags=re.IGNORECASE,
)


def is_navigation_question(text: str) -> bool:
    """Accept only questions whose every comma-delimited clause requests context."""
    cleaned = text.strip().lstrip("-*#> ").rstrip("؟?").strip()
    cleaned = re.sub(r"^(?:[0-9٠-٩]+|[A-Za-z])[.)]\s*", "", cleaned)
    clauses = NAVIGATION_SPLIT.split(cleaned)
    normalized = [re.sub(r"^(?:and\s+|و(?=(?:ما|أي|هل|كم)\b))", "", clause.strip(), flags=re.I) for clause in clauses]
    return bool(normalized) and all(NAVIGATION_CLAUSE.fullmatch(clause) for clause in normalized)


ASSESSMENT_OFFER = re.compile(
    r"(?:اختبار|تحق[ّ]?ق|مراجعة|أسئلة|تمارين|check|quiz|test|questions?|exercises?)",
    flags=re.IGNORECASE,
)
ASSESSMENT_INVITATION = re.compile(
    r"^(?:هل\s+(?:تريد|ترغب|تحب).*(?:اختبار|تحق[ّ]?ق|مراجعة|أسئلة|تمارين)|"
    r"(?:do\s+you\s+want|would\s+you\s+like).*(?:check|quiz|test|questions?|exercises?)).*[؟?]$",
    flags=re.IGNORECASE,
)
GENERIC_START_INVITATION = re.compile(
    r"^(?:هل\s+(?:تريد|ترغب|تحب)\s+أن\s+نبدأ|(?:would\s+you\s+like\s+to|shall\s+we)\s+start)\s*[؟?]$",
    flags=re.IGNORECASE,
)
CONSENT_SELECTION = re.compile(
    r"(?:أجب|رد|اختر).*(?:نعم|أجل).*(?:لا|كلا).*(?:اختبار|تحق[ّ]?ق|مراجعة|أسئلة)|"
    r"(?:reply|answer|choose).*(?:yes|no).*(?:check|quiz|test|questions?)",
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

FAILURE_TAXONOMY = {
    "educational": "case-local",
    "deterministic-guard": "case-local",
    "model-protocol": "case-local",
    "artifact-protocol": "case-local",
    "artifact-validation": "case-local",
    "grader-protocol": "case-local",
    "contradictory-grader-verdict": "case-local",
    "infrastructure": "case-local-when-accounted",
    "candidate-sha-drift": "global",
    "credential-boundary": "global",
    "model-identity-mismatch": "global",
    "usage-accounting": "global",
    "cost-ceiling": "global",
    "report-persistence": "global",
    "invalid-global-configuration": "global",
    "operator-interrupt": "global",
}
ABORT_PATH_INVENTORY = (
    {"path": "invalid-adapter-command-or-global-configuration", "classification": "invalid-global-configuration", "disposition": "global-preflight"},
    {"path": "fresh-report-collision-or-invalid-resume", "classification": "invalid-global-configuration", "disposition": "global-preflight"},
    {"path": "credential-boundary-or-exposure-risk", "classification": "credential-boundary", "disposition": "global"},
    {"path": "candidate-sha-drift", "classification": "candidate-sha-drift", "disposition": "global"},
    {"path": "response-command-error", "classification": "infrastructure", "disposition": "accounted-case-local-or-global"},
    {"path": "response-timeout", "classification": "infrastructure", "disposition": "accounted-case-local-or-global"},
    {"path": "response-incomplete", "classification": "model-protocol", "disposition": "case-local"},
    {"path": "response-malformed-payload", "classification": "model-protocol", "disposition": "accounted-case-local-or-global"},
    {"path": "response-schema-failure", "classification": "model-protocol", "disposition": "accounted-case-local-or-global"},
    {"path": "model-identity-mismatch", "classification": "model-identity-mismatch", "disposition": "global"},
    {"path": "artifact-extraction-failure", "classification": "artifact-protocol", "disposition": "case-local"},
    {"path": "artifact-validation-failure", "classification": "artifact-validation", "disposition": "case-local"},
    {"path": "deterministic-guard-failure", "classification": "deterministic-guard", "disposition": "case-local"},
    {"path": "grader-command-error", "classification": "infrastructure", "disposition": "accounted-case-local-or-global"},
    {"path": "grader-timeout", "classification": "infrastructure", "disposition": "accounted-case-local-or-global"},
    {"path": "grader-malformed-payload", "classification": "grader-protocol", "disposition": "accounted-case-local-or-global"},
    {"path": "grader-schema-failure", "classification": "grader-protocol", "disposition": "accounted-case-local-or-global"},
    {"path": "invalid-grader-evidence", "classification": "grader-protocol", "disposition": "case-local"},
    {"path": "contradictory-grader-verdict", "classification": "contradictory-grader-verdict", "disposition": "case-local"},
    {"path": "report-serialization-or-persistence", "classification": "report-persistence", "disposition": "global"},
    {"path": "usage-accounting-failure", "classification": "usage-accounting", "disposition": "global"},
    {"path": "authorized-cost-ceiling", "classification": "cost-ceiling", "disposition": "global-preflight"},
    {"path": "operator-interrupt", "classification": "operator-interrupt", "disposition": "global"},
)


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
        if api_key_env != OPENAI_API_KEY_ENV: raise GlobalIntegrityError("only OPENAI_API_KEY may be passed to an adapter")
        if not source.get(api_key_env): raise GlobalIntegrityError("requested adapter API key environment variable is missing")
        environment[api_key_env] = source[api_key_env]
    return environment


class AdapterInvocationError(RuntimeError):
    """A retryable transport or malformed-protocol adapter failure."""

    def __init__(self, kind: str, message: str, record: dict[str, Any]):
        super().__init__(message)
        self.kind = kind
        self.record = record


class NonRetryableEvaluationError(RuntimeError):
    """A completed invocation with a case-local content or artifact failure."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


class GlobalIntegrityError(RuntimeError):
    """A run-wide safety or release-integrity failure that must abort."""


def validate_cost_authorization(
    authorized_cost_usd: float | None,
    conservative_max_cost_usd: float | None,
    calculated_max_cost_usd: float | None,
    required: bool,
) -> None:
    supplied = (
        authorized_cost_usd is not None,
        conservative_max_cost_usd is not None,
        calculated_max_cost_usd is not None,
    )
    if (required and not all(supplied)) or len(set(supplied)) != 1:
        raise GlobalIntegrityError("authorization, declared ceiling, and calculated ceiling are all required")
    if not any(supplied):
        return
    values = (authorized_cost_usd, conservative_max_cost_usd, calculated_max_cost_usd)
    if not all(isinstance(value, (int, float)) and value > 0 and value < float("inf") for value in values):
        raise GlobalIntegrityError("cost authorization values must be finite and positive")
    if conservative_max_cost_usd != calculated_max_cost_usd:
        raise GlobalIntegrityError("declared conservative maximum does not match the calculated pricing ceiling")
    if conservative_max_cost_usd > authorized_cost_usd:
        raise GlobalIntegrityError("conservative maximum cost exceeds authorized cost ceiling")


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
            except (NonRetryableEvaluationError, GlobalIntegrityError): raise
            except RuntimeError:
                record["status"] = "malformed-protocol"
                if on_record: on_record(record)
                raise
            return output, records, validated
        except NonRetryableEvaluationError as exc:
            records[-1]["status"] = "content-error"
            records[-1]["content_error"] = str(exc)
            records[-1]["content_error_kind"] = exc.kind
            if on_record: on_record(records[-1])
            return output, records, exc
        except GlobalIntegrityError:
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

NEGATIVE_CRITERION = re.compile(
    r"(?:\b(?:no|not|never|without|stop|stops|remain(?:s)? internal|not announced|does not)\b|"
    r"لا |دون |من دون|يتوقف|تبقى داخلية|لا تُعلن|لا تعلن)",
    flags=re.IGNORECASE,
)
NEGATIVE_SATISFACTION_REASON = re.compile(
    r"(?:\b(?:does not|do not|not|without|no |never |stops?|remains? internal|avoids?)\b|"
    r"لا يتضمن|لا يحتوي|من دون|دون |يوقف|يتوقف|تبقى داخلية)",
    flags=re.IGNORECASE,
)


def pass_reason_contradicts(criterion: str, reason: str) -> bool:
    """Downgrade absent required behavior, not the desired absence of prohibited behavior."""
    if not UNSUPPORTED_PASS_REASON.search(reason):
        return False
    if NEGATIVE_CRITERION.search(criterion) and NEGATIVE_SATISFACTION_REASON.search(reason):
        return False
    return True


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
        if passed and pass_reason_contradicts(criterion, reason):
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


USAGE_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_tokens",
    "output_tokens",
    "reasoning_tokens",
    "total_tokens",
)


def failed_protocol_criteria(expected: list[str], reason: str) -> list[dict[str, Any]]:
    """Fail every criterion when no grader verdict can be trusted."""
    return [
        {
            "criterion": criterion,
            "passed": False,
            "verdict": "fail",
            "evidence": {"source": "absent", "quote": f"ABSENT: {reason}"[:800]},
            "reason": reason,
        }
        for criterion in expected
    ]


def compact_case_invocations(journal: list[dict[str, Any]], case_key: str) -> None:
    """Hash raw adapter results while retaining invalid grader output for audit."""
    for record in [item for item in journal if item.get("case_key") == case_key]:
        raw_result = record.pop("result", None)
        if raw_result is None:
            continue
        record["result_sha256"] = hashlib.sha256(
            json.dumps(raw_result, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        usage = raw_result.get("usage") if isinstance(raw_result, dict) else None
        if isinstance(usage, dict):
            record["usage"] = {
                field: value
                for field in USAGE_FIELDS
                if isinstance((value := usage.get(field)), int) and value >= 0
            }
        if record.get("status") == "malformed-protocol":
            record["protocol_result"] = raw_result


def valid_usage_record(output: dict[str, Any]) -> bool:
    usage = output.get("usage")
    try:
        reconcile_usage(usage)
    except ValueError:
        return False
    return True


def validate_usage_evidence(output: dict[str, Any], role: str, required: bool) -> None:
    if required and not valid_usage_record(output):
        raise GlobalIntegrityError(f"{role} usage cannot be accounted for safely")


def invocation_failure_is_safely_accounted(error: AdapterInvocationError, credential_env: str | None) -> bool:
    """A command failure is local only when it is provably zero-cost or carries valid usage."""
    if credential_env is None:
        return True
    result = error.record.get("result")
    return isinstance(result, dict) and valid_usage_record(result)


def result_has_failure_category(result: dict[str, Any], category: str) -> bool:
    categories = result.get("failure_categories")
    if isinstance(categories, list):
        return category in categories
    return result.get("failure_category") == category


def aggregate_usage(invocations: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate auditable usage from every invocation, including failed attempts."""
    totals = {field: 0 for field in USAGE_FIELDS}
    records = 0
    for invocation in invocations:
        usage = invocation.get("usage")
        if not isinstance(usage, dict):
            continue
        records += 1
        for field in USAGE_FIELDS:
            value = usage.get(field, 0)
            if isinstance(value, int) and value >= 0:
                totals[field] += value
    return {"records": records, **totals}


def refresh_cost_accounting(report: dict[str, Any]) -> None:
    """Keep partial and final reports spend-complete without exposing credentials."""
    cost_plan = report.get("cost_plan")
    if not isinstance(cost_plan, dict):
        return
    active = report.get("active_case")
    reservation = active.get("cost_reservation") if isinstance(active, dict) else None
    try:
        report["cost_accounting"] = cost_accounting_snapshot(
            report.get("invocations", []),
            cost_plan,
            reservation if isinstance(reservation, dict) else None,
        )
    except ValueError as exc:
        raise GlobalIntegrityError(f"unsafe spending accounting: {exc}") from exc


def reserve_invocation_cost(
    report: dict[str, Any],
    role: str,
    max_output_tokens: int,
) -> dict[str, Any] | None:
    cost_plan = report.get("cost_plan")
    if not isinstance(cost_plan, dict):
        return None
    reservation = invocation_reservation(cost_plan, role, max_output_tokens)
    report["active_case"]["cost_reservation"] = reservation
    refresh_cost_accounting(report)
    return reservation


def checkpoint_invocation_cost(
    report: dict[str, Any],
    record: dict[str, Any],
    reservation: dict[str, Any] | None,
) -> None:
    if reservation is not None:
        record.setdefault("cost_reservation", reservation)
    active = report.get("active_case")
    if isinstance(active, dict):
        active.pop("cost_reservation", None)
    refresh_cost_accounting(report)


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
    navigation_questionnaire = bool(question_lines) and all(is_navigation_question(line) for line in question_lines)
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
            if ASSESSMENT_INVITATION.search(candidate):
                continue
            if GENERIC_START_INVITATION.search(candidate) and ASSESSMENT_OFFER.search(line):
                continue
            if is_navigation_question(candidate):
                continue
            if ASSESSMENT_QUESTION.search(candidate):
                return AssessmentMatch(candidate)
            task_candidate = re.sub(r"^(?:current action|your action|الخطوة الحالية|إجراءك الحالي|الإجراء الآن)\s*[:：-]?\s*", "", candidate, flags=re.I)
            task_candidate = re.sub(r"^(?:if you want|إذا أردت|إن أردت|إن أحببت)[،,]?\s*", "", task_candidate, flags=re.I)
            imperative = ASSESSMENT_IMPERATIVE.match(task_candidate)
            if imperative:
                if CONSENT_SELECTION.search(candidate): continue
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

    def require_deterministic_pass(item: dict[str, Any], check: dict[str, Any]) -> None:
        """A hard guard may fail closed but must never erase a grader failure or downgrade."""
        if check["passed"]:
            return
        item["passed"] = False
        item["verdict"] = "fail"
        item["evidence"] = {
            "source": "absent",
            "quote": f"ABSENT: {item['criterion']}"[:800],
        }
        item["reason"] = f"{check['reason']} (authoritative)"

    for item in criteria:
        criterion = item["criterion"].lower()
        if (
            "response is written in" in criterion
            or "response uses the requested locale" in criterion
            or "response remains in english" in criterion
        ):
            require_deterministic_pass(item, language)
            continue
        elif "is preserved in its original script and defined in arabic on first use" in criterion:
            require_deterministic_pass(item, terminology)
            continue
        elif (
            "communication interface from maintaining synchronized data copies" in criterion
            or "api is distinguished from maintaining synchronized database copies" in criterion
        ):
            require_deterministic_pass(item, api_replication_contrast)
            continue
        elif "no assessment question is asked before learner opt-in" in criterion:
            assessment_criterion_present = True
            require_deterministic_pass(item, assessment)
            continue
        elif "one central concept is taught before notation" in criterion:
            require_deterministic_pass(item, child_concept_order)
            continue
        elif "acknowledges that the child is starting from zero" in criterion:
            require_deterministic_pass(item, child_onboarding)
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
    try:
        serialized = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    except (TypeError, ValueError) as exc:
        raise GlobalIntegrityError("report serialization failed") from exc
    if os.environ.get(OPENAI_API_KEY_ENV) and os.environ[OPENAI_API_KEY_ENV] in serialized:
        raise GlobalIntegrityError("credential exposure risk in report")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(serialized)
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
        raise GlobalIntegrityError(f"{role} expected model must be an exact provider/model identifier")
    requested_model = expected_model.split("/", 1)[1]
    if output.get("model") != expected_model or output.get("settings", {}).get("model") != requested_model:
        raise GlobalIntegrityError(f"{role} release evidence does not match expected model {expected_model}")


def validate_response_output(output: dict[str, Any]) -> str:
    validate_model_evidence(output, "response")
    evaluation_error = output.get("evaluation_error")
    if isinstance(evaluation_error, dict):
        if evaluation_error.get("kind") != "model-incomplete":
            kind = str(evaluation_error.get("kind") or "model-response-invalid")
            raise NonRetryableEvaluationError(kind, f"adapter completed with {kind}")
        if output.get("response") not in {None, ""} or output.get("artifact_evidence") not in (None, []):
            raise RuntimeError("incomplete model output must not expose partial response or artifact content")
        return ""
    response = output.get("response")
    if not isinstance(response, str) or not response.strip():
        raise RuntimeError("response adapter returned no non-empty response")
    return response


def verify_release_commit(candidate: str, root: Path = ROOT) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", candidate or ""): raise GlobalIntegrityError("release candidate must be a full lowercase SHA-1")
    commands = {
        "head": ["git", "rev-parse", "HEAD"], "origin_main": ["git", "rev-parse", "origin/main"],
        "merge_base": ["git", "merge-base", "HEAD", "origin/main"], "tracked_status": ["git", "status", "--porcelain", "--untracked-files=no"],
    }
    observed = {}
    for name, command in commands.items():
        done = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
        observed[name] = {"command": command, "returncode": done.returncode, "stdout": done.stdout.strip(), "stderr": done.stderr.strip()}
        if done.returncode: raise GlobalIntegrityError(f"release git verification failed: {name}")
    if any(observed[name]["stdout"] != candidate for name in ("head", "origin_main", "merge_base")): raise GlobalIntegrityError("candidate, HEAD, origin/main, and merge base must match")
    if observed["tracked_status"]["stdout"]: raise GlobalIntegrityError("release evidence requires a clean tracked worktree")
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
    parser.add_argument("--pricing-file", type=Path, default=None)
    parser.add_argument("--authorized-cost-usd", type=float, default=None)
    parser.add_argument("--conservative-max-cost-usd", type=float, default=None)
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
    if args.release_evidence and args.pricing_file is None:
        parser.error("--release-evidence requires --pricing-file")
    cost_policy: dict[str, Any] | None = None
    cost_plan: dict[str, Any] | None = None
    if args.pricing_file is not None:
        try:
            cost_policy = load_cost_policy(args.pricing_file, ROOT)
            cost_plan = derive_cost_plan(
                cost_policy,
                suites,
                args.response_command,
                args.grader_command,
                args.protocol_retries,
                args.expected_response_model,
                args.expected_grader_model,
            )
        except ValueError as exc:
            raise GlobalIntegrityError(f"pricing preflight failed: {exc}") from exc
    validate_cost_authorization(
        args.authorized_cost_usd,
        args.conservative_max_cost_usd,
        cost_plan["conservative_cost"]["total_usd"] if cost_plan else None,
        args.release_evidence,
    )
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
        if args.output.exists() and not args.resume:
            parser.error("fresh release evidence refuses to overwrite an existing report")

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
        "authorized_cost_usd": args.authorized_cost_usd,
        "conservative_max_cost_usd": args.conservative_max_cost_usd,
        "pricing_policy_sha256": cost_plan["policy_sha256"] if cost_plan else None,
    }
    configuration_sha256 = hashlib.sha256(json.dumps(run_configuration, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    report: dict[str, Any] = {
        "schema_version": "2.2.0", "status": "running", "release_evidence": args.release_evidence,
        "candidate_commit": git_verification["verified_sha"] if git_verification else None,
        "verified_commit": git_verification, "run_id": f"behavioral-{generated_at.strftime('%Y%m%dT%H%M%S.%fZ')}",
        "generated_at": generated_at.isoformat(), "resume": {"requested": args.resume, "completed_case_keys": []},
        "run_configuration": run_configuration, "run_configuration_sha256": configuration_sha256,
        "cost_plan": cost_plan,
        "commands": {"response": safe_adapter_command(args.response_command), "grader": safe_adapter_command(args.grader_command),
                     "response_credential_env": args.response_api_key_env, "grader_credential_env": args.grader_api_key_env,
                     "protocol_retries": args.protocol_retries, "timeout_seconds": args.timeout,
                     "authorized_cost_usd": args.authorized_cost_usd,
                     "conservative_max_cost_usd": args.conservative_max_cost_usd,
                     "calculated_max_cost_usd": cost_plan["conservative_cost"]["total_usd"] if cost_plan else None,
                     "pricing_policy_sha256": cost_plan["policy_sha256"] if cost_plan else None},
        "failure_taxonomy": FAILURE_TAXONOMY,
        "abort_path_inventory": list(ABORT_PATH_INVENTORY),
        "instruction_sources": {}, "prompt_packets": {}, "invocations": invocation_journal, "results": results,
    }
    refresh_cost_accounting(report)
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
            model_protocol_failed = False
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
                    generated, records = pending_generation, pending_records
                    validate_usage_evidence(generated, "response", args.response_api_key_env is not None)
                    validate_release_model(generated, "response", args.release_evidence, args.expected_response_model)
                    try:
                        response = validate_response_output(generated)
                    except NonRetryableEvaluationError as exc:
                        response = exc
                    pending_generation = None
                else:
                    if args.release_evidence:
                        verify_release_commit(args.candidate_commit)
                    report["active_case"] = {"case_key": case_key, "stage": "response-invoking", "turn": turn_index, "attempts": [],
                        "transcript": history, "attempt_log": attempt_log, "last_generation": generated,
                        "response_attempts": response_attempts, "selected_attempts": selected_attempts,
                        "turn_guard_results": turn_guard_results, "artifacts": all_artifacts}
                    response_limit = 0
                    if cost_plan:
                        response_limit = cost_plan["request_ceiling"][
                            "long_artifact_response_max_output_tokens"
                            if uses_long_artifact_budget(case)
                            else "response_max_output_tokens"
                        ]
                    response_reservation = reserve_invocation_cost(
                        report, "response", response_limit
                    ) if response_limit else None
                    write_report(args.output, report)
                    def checkpoint_response(record: dict[str, Any]) -> None:
                        if record not in invocation_journal: invocation_journal.append(record)
                        checkpoint_invocation_cost(report, record, response_reservation)
                        report["active_case"]["attempts"] = [item for item in invocation_journal if item.get("role") == "response" and item.get("case_key") == case_key and item.get("turn_index") == turn_index]
                        write_report(args.output, report)
                    try:
                        generated, records, response = invoke_protocol(
                            args.response_command, generation_payload, args.timeout, "response", args.protocol_retries,
                            lambda output: (
                                validate_usage_evidence(output, "response", args.response_api_key_env is not None),
                                validate_release_model(output, "response", args.release_evidence, args.expected_response_model),
                                validate_response_output(output),
                            )[2],
                            checkpoint_response, args.response_api_key_env,
                        )
                    except AdapterInvocationError as exc:
                        if not invocation_failure_is_safely_accounted(exc, args.response_api_key_env):
                            raise GlobalIntegrityError(
                                "response invocation failed without auditable usage; spending cannot be accounted for safely"
                            ) from exc
                        records = [
                            item for item in invocation_journal
                            if item.get("role") == "response"
                            and item.get("case_key") == case_key
                            and item.get("turn_index") == turn_index
                        ]
                        generated = exc.record.get("result")
                        generated = dict(generated) if isinstance(generated, dict) else {}
                        timeout_failure = exc.record.get("retry_cause") == "timeout"
                        kind = "response-timeout" if timeout_failure else (
                            "response-protocol" if exc.kind == "malformed-protocol" else "response-command-error"
                        )
                        generated["evaluation_error"] = {"kind": kind, "message": str(exc)}
                        response = NonRetryableEvaluationError(kind, str(exc))
                report["active_case"].update({"stage": "response", "attempts": records})
                write_report(args.output, report)
                response_attempts += len(records)
                evaluation_error = generated.get("evaluation_error")
                validation_failure = response if isinstance(response, NonRetryableEvaluationError) else None
                if isinstance(evaluation_error, dict) or validation_failure is not None:
                    if not isinstance(evaluation_error, dict):
                        evaluation_error = {
                            "kind": validation_failure.kind,
                            "message": str(validation_failure),
                        }
                    failure_kind = str(evaluation_error.get("kind") or "model-response-invalid")
                    if failure_kind == "model-incomplete":
                        failure_reason = (
                            "model response was incomplete; "
                            f"status={evaluation_error.get('status', 'unknown')}, "
                            f"reason={evaluation_error.get('reason', 'unknown')}"
                        )
                    else:
                        failure_reason = str(
                            evaluation_error.get("message")
                            or f"model response failed local validation ({failure_kind})"
                        )
                    if failure_kind == "artifact-validation":
                        failure_category = "artifact-validation"
                        failure_detail_key = "artifact_validation_failure"
                        invocation_status = "artifact-validation-error"
                    elif failure_kind in {"artifact-extraction", "artifact-schema", "artifact-protocol"}:
                        failure_category = "artifact-protocol"
                        failure_detail_key = "artifact_protocol_failure"
                        invocation_status = "artifact-protocol-error"
                    elif failure_kind in {"response-timeout", "response-command-error"}:
                        failure_category = "infrastructure"
                        failure_detail_key = "infrastructure_failure"
                        invocation_status = "transport-error"
                    else:
                        failure_category = "model-protocol"
                        failure_detail_key = "model_protocol_failure"
                        invocation_status = "model-protocol-error"
                    for index, record in enumerate(records, response_attempts - len(records) + 1):
                        record["status"] = invocation_status
                        attempt_log.append(
                            {
                                "sequence": index,
                                "turn_index": turn_index,
                                "attempt_index": 1,
                                "protocol_retry_cause": record.get("retry_cause"),
                                "retry_feedback": record.get("retry_feedback"),
                                "status": record["status"],
                                "model": generated.get("model"),
                                "raw_result": generated,
                                "accepted": False,
                                "deterministic_guards": None,
                                "rejection_reasons": [
                                    {"check": failure_category, "reason": failure_reason}
                                ],
                            }
                        )
                    selected_attempts.append(response_attempts)
                    failure_history = history + [dict(turn, turn=turn_index)]
                    rejected_response = generated.get("response")
                    if isinstance(rejected_response, str) and rejected_response:
                        failure_history.append(
                            {"role": "assistant", "turn": turn_index, "content": rejected_response}
                        )
                    criteria = [
                        {
                            "criterion": criterion,
                            "passed": False,
                            "verdict": "fail",
                            "evidence": {
                                "source": "absent",
                                "quote": f"ABSENT: {failure_reason}"[:800],
                            },
                            "reason": failure_reason,
                        }
                        for criterion in case_expected
                    ]
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
                            "passed": False,
                            "failure_category": failure_category,
                            "failure_categories": [failure_category],
                            failure_detail_key: evaluation_error,
                            "criteria": criteria,
                            "deterministic_guards": turn_guard_results,
                            "raw_transcript": failure_history,
                            "response_attempts": response_attempts,
                            "attempt_log": attempt_log,
                            "selected_attempts": selected_attempts,
                            "selected_attempt": selected_attempts[-1],
                            "deterministic_preflight_passed": False,
                            "response_evidence": {
                                **{key: generated.get(key) for key in ("model", "settings", "adapter_version", "invocation_id", "timing")},
                                **{key: generated[key] for key in ("usage", "api", "effective_prompt_sha256") if key in generated},
                                "evaluation_error": evaluation_error,
                                "invalid_artifact_evidence": generated.get("invalid_artifact_evidence", []),
                                "raw_result_ref": f"attempt_log:{selected_attempts[-1]}",
                            },
                            "grader_evidence": {
                                "skipped": True,
                                "reason": failure_reason,
                            },
                            "artifacts": all_artifacts,
                            "invalid_artifacts": generated.get("invalid_artifact_evidence", []),
                        }
                    )
                    compact_case_invocations(invocation_journal, case_key)
                    completed_keys.add(case_key)
                    report["resume"]["completed_case_keys"] = sorted(completed_keys)
                    report.pop("active_case", None)
                    write_report(args.output, report)
                    model_protocol_failed = True
                    break
                guards: dict[str, Any] = {}
                for guard_name, guard_function in (
                    ("language", lambda: deterministic_language_check(response, case["locale"])),
                    ("assessment", lambda: deterministic_assessment_check(response, current_turns)),
                    ("completeness", lambda: deterministic_completeness_check(response, prompt)),
                    ("terminology", lambda: deterministic_terminology_check(response, prompt)),
                    ("text_quality", lambda: deterministic_text_quality_check(response)),
                ):
                    try:
                        guard_result = guard_function()
                        if (
                            not isinstance(guard_result, dict)
                            or not isinstance(guard_result.get("passed"), bool)
                            or not isinstance(guard_result.get("reason"), str)
                        ):
                            raise ValueError("guard result must contain Boolean passed and text reason")
                        guards[guard_name] = guard_result
                    except Exception as exc:
                        guards[guard_name] = {
                            "passed": False,
                            "reason": f"deterministic guard execution failure: {type(exc).__name__}: {exc}",
                        }
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

            if model_protocol_failed:
                continue

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
            if args.release_evidence:
                verify_release_commit(args.candidate_commit)
            report["active_case"].update({"stage": "grader-invoking", "grader_attempts": []})
            grader_limit = cost_plan["request_ceiling"]["grader_max_output_tokens"] if cost_plan else 0
            grader_reservation = reserve_invocation_cost(
                report, "grader", grader_limit
            ) if grader_limit else None
            write_report(args.output, report)
            def checkpoint_grader(record: dict[str, Any]) -> None:
                if record not in invocation_journal: invocation_journal.append(record)
                checkpoint_invocation_cost(report, record, grader_reservation)
                report["active_case"]["grader_attempts"] = [item for item in invocation_journal if item.get("role") == "grader" and item.get("case_key") == case_key]
                write_report(args.output, report)
            def checkpoint_criterion(result: dict[str, Any], index: int) -> None:
                report["active_case"].setdefault("validated_grader_results", []).append(result)
                report["active_case"]["stage"] = f"grader-result:{index}"
                write_report(args.output, report)
            try:
                graded, grader_records, normalized_grade = invoke_protocol(
                    args.grader_command,
                    grade_payload,
                    args.timeout,
                    "grader",
                    args.protocol_retries,
                    lambda output: (
                        validate_usage_evidence(output, "grader", args.grader_api_key_env is not None),
                        validate_model_evidence(output, "grader"),
                        validate_release_model(output, "grader", args.release_evidence, args.expected_grader_model),
                        validate_grade(output, case_expected, history, artifacts, checkpoint_criterion),
                    )[3],
                    checkpoint_grader,
                    args.grader_api_key_env,
                )
            except AdapterInvocationError as exc:
                if not invocation_failure_is_safely_accounted(exc, args.grader_api_key_env):
                    raise GlobalIntegrityError(
                        "grader invocation failed without auditable usage; spending cannot be accounted for safely"
                    ) from exc
                grader_records = [
                    item for item in invocation_journal
                    if item.get("role") == "grader" and item.get("case_key") == case_key
                ]
                timeout_failure = exc.record.get("retry_cause") == "timeout"
                failure_category = "grader-protocol" if exc.kind == "malformed-protocol" else "infrastructure"
                failure_detail_key = (
                    "grader_protocol_failure" if failure_category == "grader-protocol"
                    else "infrastructure_failure"
                )
                failure_reason = (
                    f"grader protocol failure: {exc}" if failure_category == "grader-protocol"
                    else f"grader invocation failure: {exc}"
                )
                failure_detail = {
                    "kind": "grader-timeout" if timeout_failure else exc.kind,
                    "message": str(exc),
                    "attempts": len(grader_records),
                }
                invalid_output = exc.record.get("result")
                invalid_output = invalid_output if isinstance(invalid_output, dict) else {}
                report["active_case"].update({
                    "stage": f"{failure_category}-failure",
                    "grader_attempts": grader_records,
                    failure_detail_key: failure_detail,
                })
                write_report(args.output, report)
                selected_records = [attempt_log[sequence - 1] for sequence in selected_attempts]
                deterministic_preflight_passed = all(item["accepted"] for item in selected_records)
                grader_failure_categories = [
                    *(["deterministic-guard"] if not deterministic_preflight_passed else []),
                    failure_category,
                ]
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
                        "passed": False,
                        "failure_category": failure_category,
                        "failure_categories": grader_failure_categories,
                        failure_detail_key: failure_detail,
                        "criteria": failed_protocol_criteria(case_expected, failure_reason),
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
                            "skipped": False,
                            "failure": failure_detail,
                            **{key: invalid_output.get(key) for key in ("model", "settings", "adapter_version", "raw_result", "invocation_id", "timing")},
                            **{key: invalid_output[key] for key in ("usage", "api", "effective_prompt_sha256", "results", "evaluation_error") if key in invalid_output},
                        },
                        "artifacts": artifacts,
                    }
                )
                compact_case_invocations(invocation_journal, case_key)
                completed_keys.add(case_key)
                report["resume"]["completed_case_keys"] = sorted(completed_keys)
                report.pop("active_case", None)
                write_report(args.output, report)
                continue
            report["active_case"].update({"stage": "grader", "grader_attempts": grader_records})
            write_report(args.output, report)
            grader_criteria_passed = all(item["passed"] for item in normalized_grade)
            has_contradictory_pass = any(
                item.get("grader_protocol_adjustment") for item in normalized_grade
            )
            criteria = enforce_deterministic_checks(
                normalized_grade,
                response,
                case["locale"],
                turns,
                turns[-1]["content"],
            )
            selected_records = [attempt_log[sequence - 1] for sequence in selected_attempts]
            deterministic_preflight_passed = all(item["accepted"] for item in selected_records)
            final_passed = deterministic_preflight_passed and all(item["passed"] for item in criteria)
            final_failure_categories: list[str] = []
            if not deterministic_preflight_passed:
                final_failure_categories.append("deterministic-guard")
            if not grader_criteria_passed:
                final_failure_categories.append(
                    "contradictory-grader-verdict" if has_contradictory_pass else "educational"
                )
            final_failure_category = final_failure_categories[0] if final_failure_categories else None
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
                    "passed": final_passed,
                    "failure_category": final_failure_category,
                    "failure_categories": final_failure_categories,
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
            compact_case_invocations(invocation_journal, case_key)
            completed_keys.add(case_key)
            report["resume"]["completed_case_keys"] = sorted(completed_keys)
            report.pop("active_case", None)
            write_report(args.output, report)

    passed = sum(item["passed"] for item in results)
    pass_rate = passed / len(results)
    critical_failures = [f"{item['suite']}/{item['case_id']}" for item in results if item["critical"] and not item["passed"]]
    refresh_cost_accounting(report)
    report.update({
        "status": "complete", "completed_at": datetime.now(timezone.utc).isoformat(), "duration_seconds": time.monotonic() - run_started,
        "summary": {
            "cases": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "unfinished": case_count - len(results),
            "pass_rate": pass_rate,
            "threshold": args.pass_threshold,
            "critical_failures": critical_failures,
            "response_invocations": sum(item.get("role") == "response" for item in invocation_journal),
            "grader_invocations": sum(item.get("role") == "grader" for item in invocation_journal),
            "grader_skipped": sum(bool(result.get("grader_evidence", {}).get("skipped")) for result in results),
            "grader_protocol_adjustments": sum(
                bool(criterion.get("grader_protocol_adjustment"))
                for result in results
                for criterion in result["criteria"]
            ),
            "model_protocol_failures": sum(
                result_has_failure_category(result, "model-protocol") for result in results
            ),
            "grader_protocol_failures": sum(
                result_has_failure_category(result, "grader-protocol") for result in results
            ),
            "artifact_protocol_failures": sum(
                result_has_failure_category(result, "artifact-protocol") for result in results
            ),
            "artifact_validation_failures": sum(
                result_has_failure_category(result, "artifact-validation") for result in results
            ),
            "deterministic_guard_failures": sum(
                result_has_failure_category(result, "deterministic-guard") for result in results
            ),
            "educational_failures": sum(
                result_has_failure_category(result, "educational") for result in results
            ),
            "contradictory_grader_verdict_failures": sum(
                result_has_failure_category(result, "contradictory-grader-verdict")
                for result in results
            ),
            "case_infrastructure_failures": sum(
                result_has_failure_category(result, "infrastructure") for result in results
            ),
            "grader_protocol_attempt_failures": sum(
                item.get("role") == "grader" and item.get("status") == "malformed-protocol"
                for item in invocation_journal
            ),
            "infrastructure_failures": sum(
                item.get("status") == "transport-error" for item in invocation_journal
            ),
            "usage_unavailable_invocations": sum(
                not isinstance(item.get("usage"), dict) for item in invocation_journal
            ),
            "usage": aggregate_usage(invocation_journal),
            "cost_accounting": report.get("cost_accounting"),
        },
    })
    write_report(args.output, report)
    _ACTIVE_REPORT = None
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if pass_rate >= args.pass_threshold and not critical_failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, OSError, RuntimeError, TypeError, ValueError, subprocess.TimeoutExpired, yaml.YAMLError) as exc:
        if _ACTIVE_REPORT is not None:
            path, diagnostic = _ACTIVE_REPORT
            diagnostic["status"] = "failed"
            diagnostic["failure"] = {"type": type(exc).__name__, "message": str(exc)}
            diagnostic["completed_at"] = datetime.now(timezone.utc).isoformat()
            try:
                refresh_cost_accounting(diagnostic)
                write_report(path, diagnostic)
            except (OSError, RuntimeError, TypeError, ValueError): pass
        print(f"Behavioral eval failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
