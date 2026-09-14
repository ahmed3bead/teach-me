#!/usr/bin/env python3
"""Run Teach Me eval cases through command-based model and grader adapters.

Each adapter receives one JSON object on stdin and must return one JSON object on
stdout. This keeps the runner independent of any model provider or agent host.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from locale_policy import canonical_locale, unicode_phrase_boundary

try:
    import yaml
except ImportError as exc:
    print("Missing dependency: install requirements-dev.txt", file=sys.stderr)
    raise SystemExit(2) from exc


ROOT = Path(__file__).resolve().parents[1]
ARABIC_LETTER = re.compile(r"[\u0621-\u063a\u0641-\u064a\u066e\u066f\u0671-\u06d3\u06fa-\u06fc]")
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
ASSESSMENT_OPT_IN = re.compile(
    unicode_phrase_boundary(
        r"(?:اختبرني|اسألني|اديني\s+(?:سؤال|أسئلة|تمرين|تمارين)|"
        r"(?:عايز|عاوز|جاهز|موافق)\s+(?:لل)?(?:أسئلة|تمارين|اختبار)|"
        r"test\s+me|quiz\s+me|ask\s+me|give\s+me\s+(?:a\s+)?(?:question|exercise)|"
        r"ready\s+for\s+(?:the\s+)?(?:questions|quiz|test))"
    ),
    flags=re.IGNORECASE,
)
DIRECT_ASSESSMENT = re.compile(
    r"(?:^|[.!؟?\n:]\s*|,\s*)"
    r"(?:لو\s+(?:حابب|عايز|عاوز)[،,]?\s*|if\s+you\s+want\s+to\s+practice[،,]?\s*)?"
    + unicode_phrase_boundary(
        r"(?:جاوب(?:ني)?|جاوبي|حل|احسب|اختار|حد[دّ]|قول(?:ي|ّي)|اكتب|ارسم|لو[نّ]|جر[بّ]|"
        r"answer|calculate|choose|identify|tell\s+me|write|draw|colou?r|solve|try)"
    ),
    flags=re.IGNORECASE,
)
ASSESSMENT_QUESTION = re.compile(
    unicode_phrase_boundary(
        r"(?:إيه|ايه|كام|ليه|ما\s+(?:هو|هي)|تفتكر|قول(?:ي|ّي)|احسب|اختار|"
        r"هل\s+(?:فهمت|فهمتي)|فاهم(?:ة)?|what|which|how\s+many|why|can\s+you\s+explain|"
        r"did\s+you\s+understand|do\s+you\s+understand|got\s+it)"
    )
    + r"[^؟?]*[؟?]",
    flags=re.IGNORECASE,
)
FRACTION_NOTATION = re.compile(r"\b\d+\s*/\s*\d+\b")
EQUAL_PARTS = re.compile(r"(?:أجزاء|أقسام|قسمان|قسمين|جزآن|جزءان|جزأين|جزءين|قطعتان|قطعتين)\s+متساوي")
CHILD_CONCRETE_EXAMPLE = re.compile(r"(?:شريط|ورق|دائرة|مربع|تفاحة|رغيف|قلم|مكعب)")
SHAMING_LANGUAGE = re.compile(r"\b(?:غبي|فاشل|كسول|ساذج|عيب|يجب أن تعرف|سهل جدًا)\b")
REPEATED_ARABIC_DIACRITIC = re.compile(r"([\u064b-\u065f])\1+")
ARABIC_TOKEN = re.compile(r"[\u0600-\u06ff]+")


def invoke(command: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    completed = subprocess.run(
        shlex.split(command),
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"adapter failed ({completed.returncode}): {completed.stderr.strip()}")
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("adapter stdout was not one JSON object") from exc
    if not isinstance(output, dict):
        raise RuntimeError("adapter output must be a JSON object")
    return output


def load_suites(paths: list[Path], selected_case: str | None) -> list[dict[str, Any]]:
    suites: list[dict[str, Any]] = []
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        cases = data.get("cases", [])
        for case in cases:
            locale = case.get("locale")
            if isinstance(locale, str):
                case["locale"] = canonical_locale(locale)
        if selected_case:
            cases = [case for case in cases if f"{data.get('suite')}/{case.get('id')}" == selected_case]
        if cases:
            suites.append({"suite": data["suite"], "version": data["version"], "cases": cases})
    return suites


def validate_grade(grade: dict[str, Any], expected: list[str]) -> list[dict[str, Any]]:
    results = grade.get("results")
    if not isinstance(results, list) or len(results) != len(expected):
        raise RuntimeError("grader must return one result per expected criterion")
    normalized: list[dict[str, Any]] = []
    for criterion, item in zip(expected, results):
        if not isinstance(item, dict) or not isinstance(item.get("passed"), bool):
            raise RuntimeError("each grader result needs boolean passed")
        normalized.append(
            {
                "criterion": criterion,
                "passed": item["passed"],
                "reason": str(item.get("reason", "")),
            }
        )
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
    try:
        normalized = canonical_locale(locale or "en")
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
    for term, variants in sorted(TECHNICAL_TERMS.items(), key=lambda item: len(item[0]), reverse=True):
        requested = term.casefold() in combined or any(variant in prompt for variant in variants)
        if not requested or any(term.casefold() in longer.casefold() for longer in required):
            continue
        required.append(term)
        position = text.casefold().find(term.casefold())
        if position < 0:
            missing.append(term)
        elif ARABIC_LETTER.search(prompt):
            tail = text[position + len(term) : position + len(term) + 180]
            definition = re.match(
                r"^[\s`*_:،—–-]*(?:(?:يعني|هو|هي|فهو|فهي|وهو|وهي|أي|ويقصد\s+به)\b|"
                r"\((?=[^)]*[\u0600-\u06ff])[^)]{4,}\))",
                tail,
            )
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


def learner_opted_into_assessment(turns: list[dict[str, str]]) -> bool:
    learner_text = "\n".join(
        str(turn.get("content", "")) for turn in turns if turn.get("role") == "user"
    )
    return bool(ASSESSMENT_OPT_IN.search(learner_text))


def deterministic_assessment_check(text: str, turns: list[dict[str, str]]) -> dict[str, Any]:
    """Prevent the first test item or task from being bundled with its invitation."""
    if learner_opted_into_assessment(turns):
        return {"passed": True, "reason": "learner explicitly opted into assessment"}
    match = DIRECT_ASSESSMENT.search(text) or ASSESSMENT_QUESTION.search(text)
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


def deterministic_completeness_check(text: str, prompt: str = "") -> dict[str, Any]:
    """Reject visibly truncated or too-short model output even if the AI grader approves it."""
    stripped = text.strip()
    word_count = len(stripped.split())
    child_lesson = any(
        marker in prompt.casefold() for marker in ("طفل", "ابتدائي", "primary school", "child")
    )
    minimum_words = 40 if child_lesson else 12
    terminal = stripped.endswith((".", "!", "?", "؟", "…"))
    passed = word_count >= minimum_words and terminal
    return {
        "passed": passed,
        "reason": (
            f"deterministic completeness check: {word_count} words, minimum {minimum_words}, "
            f"terminal punctuation {'present' if terminal else 'missing'}"
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
    starts_from_zero = "من الصفر" in text
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


def build_retry_feedback(locale: str | None, failure_codes: list[str]) -> str:
    """Describe hard-check failures in the requested output language."""
    normalized = canonical_locale(locale or "en")
    messages = {
        "ar-MSA": {
            "language": "الرد السابق فشل فحص اللغة الحتمي؛ اكتب الرد من الصفر باللغة المطلوبة",
            "assessment": "الرد السابق بدأ سؤالًا أو مهمة تقييم قبل الموافقة؛ احذف التقييم واكتفِ بدعوة اختيارية بلا سؤال",
            "completeness": "الرد السابق كان قصيرًا جدًا أو انتهى في منتصف جملة؛ اكتب شرحًا مكتملًا واختمه بعلامة ترقيم",
            "terminology": "الرد السابق حذف مصطلحًا أجنبيًا أو كتبه بحروف عربية؛ احتفظ به بلغته الأصلية واشرح معناه بالعربية عند الحاجة",
            "text_quality": "الرد السابق احتوى تسلسل Unicode غير سليم أو علامة تشكيل مكررة؛ أعد صياغته بكلمات فصيحة مألوفة من دون حركات أو علامات تشكيل اختيارية",
        },
        "en": {
            "language": "The previous response failed the deterministic language check; rewrite it entirely in English",
            "assessment": "The previous response started an assessment before opt-in; remove the task and offer only an optional check",
            "completeness": "The previous response was too short or visibly truncated; provide a complete explanation with terminal punctuation",
            "terminology": "The previous response omitted or transliterated a foreign technical term; keep every term in its original script",
            "text_quality": "The previous response contained malformed Unicode or a repeated diacritic; rewrite it with well-formed text",
        },
    }
    separator = "، و" if normalized == "ar-MSA" else "; "
    closing = ". حافظ على هدف الشرح." if normalized == "ar-MSA" else ". Preserve the teaching goal."
    return separator.join(messages[normalized][code] for code in failure_codes) + closing


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
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suites", nargs="*", type=Path)
    parser.add_argument("--response-command", help="command that generates a response from a JSON payload")
    parser.add_argument("--grader-command", help="command that grades a response from a JSON payload")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--case", help="run one suite/case-id")
    parser.add_argument("--output", type=Path, default=Path("reports/behavioral-evals.json"))
    parser.add_argument("--pass-threshold", type=float, default=0.90)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    if not 0 <= args.pass_threshold <= 1:
        parser.error("--pass-threshold must be between 0 and 1")
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

    results: list[dict[str, Any]] = []
    for suite in suites:
        for case in suite["cases"]:
            case_expected = expected_criteria(case)
            turns = case.get("turns") or [{"role": "user", "content": case["prompt"]}]
            history: list[dict[str, str]] = []
            generated: dict[str, Any] = {}
            response_attempts = 0
            attempt_log: list[dict[str, Any]] = []
            selected_attempts: list[int] = []
            for turn_index, turn in enumerate(turns, 1):
                prompt = turn["content"]
                retry_feedback = None
                current_turns = [item for item in history if item.get("role") == "user"] + [turn]
                for attempt_index in range(1, 3):
                    generation_payload = {
                        "type": "generate",
                        "suite": suite["suite"],
                        "case_id": case["id"],
                        "locale": case.get("locale"),
                        "prompt": prompt,
                        "history": history,
                        "turn_index": turn_index,
                        "turn_count": len(turns),
                        "attempt_index": attempt_index,
                        "skill_root": str(ROOT),
                    }
                    if retry_feedback is not None:
                        generation_payload["retry_feedback"] = retry_feedback
                    generated = invoke(args.response_command, generation_payload, args.timeout)
                    response_attempts += 1
                    response = generated.get("response")
                    if not isinstance(response, str) or not response.strip():
                        raise RuntimeError(f"{suite['suite']}/{case['id']}: response adapter returned no response")
                    language = deterministic_language_check(response, case.get("locale"))
                    assessment = deterministic_assessment_check(response, current_turns)
                    completeness = deterministic_completeness_check(response, prompt)
                    terminology = deterministic_terminology_check(response, prompt)
                    text_quality = deterministic_text_quality_check(response)
                    failures: list[tuple[str, dict[str, Any]]] = []
                    if not language["passed"]:
                        failures.append(("language", language))
                    if not assessment["passed"]:
                        failures.append(("assessment", assessment))
                    if not completeness["passed"]:
                        failures.append(("completeness", completeness))
                    if not terminology["passed"]:
                        failures.append(("terminology", terminology))
                    if not text_quality["passed"]:
                        failures.append(("text_quality", text_quality))
                    attempt_log.append(
                        {
                            "sequence": response_attempts,
                            "turn_index": turn_index,
                            "attempt_index": attempt_index,
                            "model": generated.get("model"),
                            "seed": generated.get("seed"),
                            "accepted": not failures,
                            "rejection_reasons": [
                                {"check": code, "reason": check["reason"]} for code, check in failures
                            ],
                        }
                    )
                    if not failures or attempt_index == 2:
                        break
                    retry_feedback = build_retry_feedback(
                        case.get("locale"), [code for code, _check in failures]
                    )
                selected_attempts.append(attempt_log[-1]["sequence"])
                history.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": response}])

            base = {
                "suite": suite["suite"],
                "case_id": case["id"],
                "locale": case.get("locale"),
                "prompt": turns[-1]["content"],
                "turns": turns,
                "transcript": history,
                "skill_root": str(ROOT),
            }
            graded = invoke(
                args.grader_command,
                {
                    "type": "grade",
                    **base,
                    "response": response,
                    "expected": case_expected,
                    "grading_rule": "Judge observable behavior only. Do not award credit for implied or missing behavior.",
                },
                args.timeout,
            )
            criteria = enforce_deterministic_checks(
                validate_grade(graded, case_expected),
                response,
                case.get("locale"),
                turns,
                turns[-1]["content"],
            )
            selected_records = [attempt_log[sequence - 1] for sequence in selected_attempts]
            deterministic_preflight_passed = all(item["accepted"] for item in selected_records)
            results.append(
                {
                    "suite": suite["suite"],
                    "case_id": case["id"],
                    "locale": case.get("locale"),
                    "critical": bool(case.get("critical", False)),
                    "passed": deterministic_preflight_passed and all(item["passed"] for item in criteria),
                    "criteria": criteria,
                    "response": response,
                    "response_attempts": response_attempts,
                    "attempt_log": attempt_log,
                    "selected_attempts": selected_attempts,
                    "selected_attempt": selected_attempts[-1],
                    "deterministic_preflight_passed": deterministic_preflight_passed,
                    "response_model": generated.get("model"),
                    "grader_model": graded.get("model"),
                }
            )

    passed = sum(item["passed"] for item in results)
    pass_rate = passed / len(results)
    critical_failures = [f"{item['suite']}/{item['case_id']}" for item in results if item["critical"] and not item["passed"]]
    report = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "cases": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": pass_rate,
            "threshold": args.pass_threshold,
            "critical_failures": critical_failures,
        },
        "results": results,
    }
    write_report(args.output, report)
    print(json.dumps(report["summary"], ensure_ascii=False))
    return 0 if pass_rate >= args.pass_threshold and not critical_failures else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired, yaml.YAMLError) as exc:
        print(f"Behavioral eval failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
