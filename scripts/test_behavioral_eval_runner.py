#!/usr/bin/env python3
"""End-to-end protocol and threshold tests for the behavioral eval runner."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import run_behavioral_evals as runner
from locale_policy import unicode_phrase_boundary


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "run_behavioral_evals.py"
RESPONSE = ROOT / "fixtures" / "eval-adapters" / "fixture_response.py"
GRADER = ROOT / "fixtures" / "eval-adapters" / "fixture_grader.py"


def run(suite: Path, report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            str(suite),
            "--response-command",
            f"{sys.executable} {RESPONSE}",
            "--grader-command",
            f"{sys.executable} {GRADER}",
            "--output",
            str(report),
            "--pass-threshold",
            "1.0",
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="teach-me-eval-") as directory:
        temporary = Path(directory)
        passing_suite = temporary / "passing.yaml"
        passing_suite.write_text(
            "suite: runner-pass\nversion: 1.0.0\ncases:\n"
            "  - id: passes\n    critical: true\n    locale: ar-EG\n    prompt: OK\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        passing_report = temporary / "passing.json"
        passed = run(passing_suite, passing_report)
        if passed.returncode != 0:
            raise AssertionError(f"passing adapter run failed: {passed.stderr}")
        data = json.loads(passing_report.read_text(encoding="utf-8"))
        if data["summary"]["pass_rate"] != 1.0 or data["summary"]["critical_failures"]:
            raise AssertionError("passing report summary is incorrect")
        criteria = data["results"][0]["criteria"]
        if data["results"][0]["locale"] != "ar-MSA":
            raise AssertionError("legacy ar-EG locale was not canonicalized to ar-MSA")
        if data["results"][0]["selected_attempts"] != [1] or not data["results"][0]["deterministic_preflight_passed"]:
            raise AssertionError("selected attempt preflight state was not recorded")
        if len(criteria) != 6 or "simplified Modern Standard Arabic" not in criteria[-1]["criterion"]:
            raise AssertionError("locale criterion was not added to the grader contract")
        if not criteria[-5]["passed"] or "opt-in check" not in criteria[-5]["reason"]:
            raise AssertionError("assessment opt-in was not enforced when the case omitted that criterion")
        if not criteria[-4]["passed"] or "text-quality check" not in criteria[-4]["reason"]:
            raise AssertionError("a pass did not require the deterministic text-quality check")
        if not criteria[-3]["passed"] or "completeness check" not in criteria[-3]["reason"]:
            raise AssertionError("a pass did not require the deterministic completeness check")
        if not criteria[-2]["passed"] or "terminology check" not in criteria[-2]["reason"]:
            raise AssertionError("a pass did not require the deterministic terminology check")
        if "deterministic script check" not in criteria[-1]["reason"]:
            raise AssertionError("locale success did not require the deterministic language check")

        failing_suite = temporary / "failing.yaml"
        failing_suite.write_text(
            "suite: runner-fail\nversion: 1.0.0\ncases:\n"
            "  - id: fails\n    critical: true\n    prompt: FORCE_FAIL\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        failing_report = temporary / "failing.json"
        failed = run(failing_suite, failing_report)
        if failed.returncode != 1:
            raise AssertionError("critical failure did not fail the run")
        data = json.loads(failing_report.read_text(encoding="utf-8"))
        if data["summary"]["critical_failures"] != ["runner-fail/fails"]:
            raise AssertionError("critical failure was not reported")

        retry_suite = temporary / "retry.yaml"
        retry_suite.write_text(
            "suite: language-retry\nversion: 1.0.0\ncases:\n"
            "  - id: retries-once\n    critical: true\n    locale: ar-MSA\n    prompt: ENGLISH_THEN_ARABIC\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        retry_report = temporary / "retry.json"
        retried = run(retry_suite, retry_report)
        if retried.returncode != 0:
            raise AssertionError(f"language retry did not recover: {retried.stderr}")
        retry_data = json.loads(retry_report.read_text(encoding="utf-8"))["results"][0]
        if retry_data["response_attempts"] != 2 or not retry_data["response"].startswith("هذا شرح"):
            raise AssertionError("wrong-language response was not replaced by exactly one Arabic retry")

        incomplete_retry_suite = temporary / "incomplete-retry.yaml"
        incomplete_retry_suite.write_text(
            "suite: completeness-retry\nversion: 1.0.0\ncases:\n"
            "  - id: retries-truncated-output\n    critical: true\n    locale: ar-MSA\n    prompt: INCOMPLETE_THEN_COMPLETE\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        incomplete_retry_report = temporary / "incomplete-retry.json"
        incomplete_retry = run(incomplete_retry_suite, incomplete_retry_report)
        incomplete_retry_data = json.loads(incomplete_retry_report.read_text(encoding="utf-8"))["results"][0]
        if incomplete_retry.returncode != 0 or incomplete_retry_data["response_attempts"] != 2:
            raise AssertionError("truncated response was not replaced by exactly one complete retry")

        incomplete_suite = temporary / "incomplete.yaml"
        incomplete_suite.write_text(
            "suite: deterministic-completeness\nversion: 1.0.0\ncases:\n"
            "  - id: rejects-false-ai-pass\n    critical: true\n    locale: ar-MSA\n    prompt: ALWAYS_INCOMPLETE\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        incomplete_report = temporary / "incomplete.json"
        incomplete = run(incomplete_suite, incomplete_report)
        incomplete_data = json.loads(incomplete_report.read_text(encoding="utf-8"))["results"][0]
        if incomplete.returncode != 1 or incomplete_data["response_attempts"] != 2:
            raise AssertionError("persistent truncated response did not fail after exactly one retry")
        if incomplete_data["criteria"][-3]["passed"]:
            raise AssertionError("AI grader false pass overrode the deterministic completeness failure")

        malformed_retry_suite = temporary / "malformed-retry.yaml"
        malformed_retry_suite.write_text(
            "suite: text-quality-retry\nversion: 1.0.0\ncases:\n"
            "  - id: repairs-malformed-arabic\n    critical: true\n    locale: ar-MSA\n"
            "    prompt: MALFORMED_THEN_CLEAN\n    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        malformed_retry_report = temporary / "malformed-retry.json"
        malformed_retry = run(malformed_retry_suite, malformed_retry_report)
        malformed_retry_data = json.loads(malformed_retry_report.read_text(encoding="utf-8"))["results"][0]
        if malformed_retry.returncode != 0 or malformed_retry_data["response_attempts"] != 2:
            raise AssertionError("malformed Arabic response was not replaced by exactly one clean retry")
        first_attempt, second_attempt = malformed_retry_data["attempt_log"]
        if first_attempt["accepted"] or first_attempt["rejection_reasons"][0]["check"] != "text_quality":
            raise AssertionError("malformed response rejection reason was not recorded")
        if "affected tokens ['قسّّيت']" not in first_attempt["rejection_reasons"][0]["reason"]:
            raise AssertionError("general Unicode check did not report the affected token")
        if not second_attempt["accepted"] or malformed_retry_data["selected_attempt"] != 2:
            raise AssertionError("selected corrective attempt was not recorded")
        if malformed_retry_data["selected_attempts"] != [2] or not malformed_retry_data["deterministic_preflight_passed"]:
            raise AssertionError("corrective attempt was not recorded as the selected passing turn")

        malformed_suite = temporary / "malformed.yaml"
        malformed_suite.write_text(
            "suite: deterministic-text-quality\nversion: 1.0.0\ncases:\n"
            "  - id: rejects-persistent-malformed-arabic\n    critical: true\n    locale: ar-MSA\n"
            "    prompt: ALWAYS_MALFORMED\n    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        malformed_report = temporary / "malformed.json"
        malformed = run(malformed_suite, malformed_report)
        malformed_data = json.loads(malformed_report.read_text(encoding="utf-8"))["results"][0]
        if malformed.returncode != 1 or malformed_data["response_attempts"] != 2:
            raise AssertionError("persistent malformed Arabic did not fail after exactly one retry")
        if malformed_data["criteria"][-4]["passed"]:
            raise AssertionError("malformed Arabic token survived the deterministic text-quality check")

        english_suite = temporary / "english.yaml"
        english_suite.write_text(
            "suite: deterministic-language\nversion: 1.0.0\ncases:\n"
            "  - id: rejects-false-ai-pass\n    critical: true\n    locale: ar-MSA\n    prompt: ALWAYS_ENGLISH\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        english_report = temporary / "english.json"
        english = run(english_suite, english_report)
        english_data = json.loads(english_report.read_text(encoding="utf-8"))["results"][0]
        if english.returncode != 1 or english_data["response_attempts"] != 2:
            raise AssertionError("persistent English response did not fail after exactly one retry")
        if english_data["criteria"][-1]["passed"]:
            raise AssertionError("AI grader false pass overrode the deterministic language failure")

        false_negative_suite = temporary / "false-negative.yaml"
        false_negative_suite.write_text(
            "suite: deterministic-language\nversion: 1.0.0\ncases:\n"
            "  - id: overrides-false-ai-fail\n    critical: true\n    locale: ar-MSA\n    prompt: FALSE_LANGUAGE_FAIL\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        false_negative_report = temporary / "false-negative.json"
        false_negative = run(false_negative_suite, false_negative_report)
        false_negative_data = json.loads(false_negative_report.read_text(encoding="utf-8"))["results"][0]
        if false_negative.returncode != 0 or not false_negative_data["criteria"][-1]["passed"]:
            raise AssertionError("AI grader false negative overrode the deterministic language success")

        dialect_suite = temporary / "msa-dialect.yaml"
        dialect_suite.write_text(
            "suite: simplified-msa\nversion: 1.0.0\ncases:\n"
            "  - id: rejects-egyptian-as-msa\n    critical: true\n    locale: ar-MSA\n    prompt: ALWAYS_EGYPTIAN\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        dialect_report = temporary / "msa-dialect.json"
        dialect = run(dialect_suite, dialect_report)
        dialect_data = json.loads(dialect_report.read_text(encoding="utf-8"))["results"][0]
        if dialect.returncode != 1 or dialect_data["criteria"][-1]["passed"]:
            raise AssertionError("colloquial Arabic was falsely accepted as simplified MSA")

        assessment_suite = temporary / "assessment.yaml"
        assessment_suite.write_text(
            "suite: assessment-opt-in\nversion: 1.0.0\ncases:\n"
            "  - id: rejects-premature-task\n    critical: true\n    locale: ar-MSA\n    prompt: PREMATURE_ASSESSMENT\n"
            "    expected:\n"
            "      - after explanation, no assessment question is asked before learner opt-in\n",
            encoding="utf-8",
        )
        assessment_report = temporary / "assessment.json"
        assessment = run(assessment_suite, assessment_report)
        assessment_data = json.loads(assessment_report.read_text(encoding="utf-8"))["results"][0]
        if assessment.returncode != 1 or assessment_data["criteria"][0]["passed"]:
            raise AssertionError("premature assessment survived the deterministic opt-in check")
        if assessment_data["response_attempts"] != 2:
            raise AssertionError("premature assessment did not receive exactly one corrective retry")

        multi_turn_suite = temporary / "multi-turn-assessment.yaml"
        multi_turn_suite.write_text(
            "suite: multi-turn-assessment\nversion: 1.0.0\ncases:\n"
            "  - id: preserves-earlier-rejection\n    critical: true\n    locale: ar-MSA\n"
            "    turns:\n"
            "      - role: user\n        content: PREMATURE_ASSESSMENT\n"
            "      - role: user\n        content: اختبرني الآن\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        multi_turn_report = temporary / "multi-turn-assessment.json"
        multi_turn = run(multi_turn_suite, multi_turn_report)
        multi_turn_data = json.loads(multi_turn_report.read_text(encoding="utf-8"))["results"][0]
        if multi_turn.returncode != 1 or multi_turn_data["deterministic_preflight_passed"]:
            raise AssertionError("later learner opt-in erased an earlier selected-turn rejection")
        if multi_turn_data["selected_attempts"] != [2, 3]:
            raise AssertionError("multi-turn selected attempts were not recorded per turn")

        understanding_suite = temporary / "understanding.yaml"
        understanding_suite.write_text(
            "suite: assessment-question\nversion: 1.0.0\ncases:\n"
            "  - id: rejects-understanding-question\n    critical: true\n    locale: ar-MSA\n    prompt: UNDERSTANDING_CHECK\n"
            "    expected:\n"
            "      - after explanation, no assessment question is asked before learner opt-in\n",
            encoding="utf-8",
        )
        understanding_report = temporary / "understanding.json"
        understanding = run(understanding_suite, understanding_report)
        if understanding.returncode != 1:
            raise AssertionError("direct understanding question survived the deterministic opt-in check")

        legacy_alias_suite = temporary / "legacy-alias.yaml"
        legacy_alias_suite.write_text(
            "suite: legacy-locale-alias\nversion: 1.0.0\ncases:\n"
            "  - id: maps-ar-eg-to-msa\n    critical: true\n    locale: ar-EG\n    prompt: ALWAYS_MSA\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        legacy_alias_report = temporary / "legacy-alias.json"
        legacy_alias = run(legacy_alias_suite, legacy_alias_report)
        legacy_alias_data = json.loads(legacy_alias_report.read_text(encoding="utf-8"))["results"][0]
        if legacy_alias.returncode != 0 or legacy_alias_data["locale"] != "ar-MSA":
            raise AssertionError("legacy ar-EG locale was not treated as ar-MSA")

        english_suite = temporary / "english-response.yaml"
        english_suite.write_text(
            "suite: english-language\nversion: 1.0.0\ncases:\n"
            "  - id: answers-english-in-english\n    critical: true\n    locale: en\n    prompt: Explain fractions simply.\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        english_response_report = temporary / "english-response.json"
        english_response = run(english_suite, english_response_report)
        english_response_data = json.loads(english_response_report.read_text(encoding="utf-8"))["results"][0]
        if english_response.returncode != 0 or "deterministic script check for Latin" not in english_response_data["criteria"][-1]["reason"]:
            raise AssertionError("English request did not produce a deterministically verified English response")

        terms_suite = temporary / "terms.yaml"
        terms_suite.write_text(
            "suite: original-technical-terms\nversion: 1.0.0\ncases:\n"
            "  - id: preserves-terms\n    critical: true\n    locale: ar-MSA\n"
            "    prompt: TECHNICAL_TERMS_OK API Replication Contract Test Prompt Database\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        terms_report = temporary / "terms.json"
        terms = run(terms_suite, terms_report)
        terms_data = json.loads(terms_report.read_text(encoding="utf-8"))["results"][0]
        if terms.returncode != 0 or not terms_data["criteria"][-2]["passed"]:
            raise AssertionError("original technical terms were not deterministically preserved")

        comparison_suite = temporary / "technical-comparison.yaml"
        comparison_suite.write_text(
            "suite: technical-comparison\nversion: 1.0.0\ncases:\n"
            "  - id: defines-compound-term\n    critical: true\n    locale: ar-MSA\n"
            "    prompt: TECHNICAL_COMPARISON_OK اشرح الفرق بين API وDatabase Replication\n"
            "    expected:\n"
            "      - API is preserved in its original script and defined in Arabic on first use\n"
            "      - Database Replication is preserved in its original script and defined in Arabic on first use\n"
            "      - the explanation distinguishes a communication interface from maintaining synchronized data copies\n",
            encoding="utf-8",
        )
        comparison_report = temporary / "technical-comparison.json"
        comparison = run(comparison_suite, comparison_report)
        comparison_data = json.loads(comparison_report.read_text(encoding="utf-8"))["results"][0]
        terminology = next(
            item for item in comparison_data["criteria"] if "technical terms remain" in item["criterion"]
        )
        if comparison.returncode != 0 or not terminology["passed"]:
            raise AssertionError("compound Database Replication term or its first-use definition failed")
        if not all(item["passed"] for item in comparison_data["criteria"][:3]):
            raise AssertionError("AI grader false rejection overrode deterministic technical contract checks")

        transliterated_suite = temporary / "transliterated.yaml"
        transliterated_suite.write_text(
            "suite: transliterated-technical-terms\nversion: 1.0.0\ncases:\n"
            "  - id: rejects-transliteration\n    critical: true\n    locale: ar-MSA\n"
            "    prompt: TECHNICAL_TERMS_TRANSLITERATED API Replication Contract Test Prompt Database\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        transliterated_report = temporary / "transliterated.json"
        transliterated = run(transliterated_suite, transliterated_report)
        transliterated_data = json.loads(transliterated_report.read_text(encoding="utf-8"))["results"][0]
        if transliterated.returncode != 1 or transliterated_data["criteria"][-2]["passed"]:
            raise AssertionError("Arabic transliteration of technical terms survived the deterministic guard")

        foreign_suite = temporary / "foreign.yaml"
        foreign_suite.write_text(
            "suite: foreign-script\nversion: 1.0.0\ncases:\n"
            "  - id: rejects-third-script\n    critical: true\n    locale: ar-MSA\n    prompt: FOREIGN_SCRIPT\n"
            "    expected:\n      - observable behavior\n",
            encoding="utf-8",
        )
        foreign_report = temporary / "foreign.json"
        foreign = run(foreign_suite, foreign_report)
        foreign_data = json.loads(foreign_report.read_text(encoding="utf-8"))["results"][0]
        if foreign.returncode != 1 or foreign_data["criteria"][-1]["passed"]:
            raise AssertionError("third-script letters survived the deterministic language check")

        invitation_suite = temporary / "invitation.yaml"
        invitation_suite.write_text(
            "suite: assessment-invitation\nversion: 1.0.0\ncases:\n"
            "  - id: allows-invitation\n    critical: true\n    locale: ar-MSA\n    prompt: OPTIONAL_INVITATION\n"
            "    expected:\n"
            "      - after explanation, no assessment question is asked before learner opt-in\n",
            encoding="utf-8",
        )
        invitation_report = temporary / "invitation.json"
        invitation = run(invitation_suite, invitation_report)
        if invitation.returncode != 0:
            raise AssertionError(f"optional invitation was incorrectly blocked: {invitation.stderr}")
        invitation_data = json.loads(invitation_report.read_text(encoding="utf-8"))["results"][0]
        if not invitation_data["criteria"][0]["passed"] or "authoritative" not in invitation_data["criteria"][0]["reason"]:
            raise AssertionError("AI grader false rejection overrode the deterministic opt-in success")

        concept_ok_suite = temporary / "concept-order-ok.yaml"
        concept_ok_suite.write_text(
            "suite: concept-order\nversion: 1.0.0\ncases:\n"
            "  - id: equal-parts-first\n    critical: true\n    locale: ar-MSA\n"
            "    prompt: CONCEPT_ORDER_OK اشرح الكسور لطفل في ابتدائي\n"
            "    expected:\n"
            "      - the explanation acknowledges that the child is starting from zero and uses one concrete, short, age-appropriate, non-shaming example\n"
            "      - one central concept is taught before notation and exceptions\n",
            encoding="utf-8",
        )
        concept_ok_report = temporary / "concept-order-ok.json"
        concept_ok = run(concept_ok_suite, concept_ok_report)
        if concept_ok.returncode != 0:
            raise AssertionError("AI grader false rejection overrode the deterministic concept-order success")

        concept_wrong_suite = temporary / "concept-order-wrong.yaml"
        concept_wrong_suite.write_text(
            "suite: concept-order\nversion: 1.0.0\ncases:\n"
            "  - id: notation-first\n    critical: true\n    locale: ar-MSA\n"
            "    prompt: CONCEPT_ORDER_WRONG اشرح الكسور لطفل في ابتدائي\n"
            "    expected:\n      - one central concept is taught before notation and exceptions\n",
            encoding="utf-8",
        )
        concept_wrong_report = temporary / "concept-order-wrong.json"
        concept_wrong = run(concept_wrong_suite, concept_wrong_report)
        if concept_wrong.returncode != 1:
            raise AssertionError("notation-first child lesson survived the deterministic concept-order check")

        english_feedback = runner.build_retry_feedback("en", ["language", "text_quality"])
        if not english_feedback.startswith("The previous response") or "الرد السابق" in english_feedback:
            raise AssertionError("English retry feedback was not localized")
        unseen_malformed = runner.deterministic_text_quality_check("هذا مثال يعلّّم الفكرة بعلامة مكررة.")
        if unseen_malformed["passed"] or "يعلّّم" not in unseen_malformed["reason"]:
            raise AssertionError("text-quality check was not general across unseen Arabic tokens")
        if not runner.deterministic_text_quality_check("هذا مثال يعلّم الفكرة بعلامات سليمة.")["passed"]:
            raise AssertionError("text-quality check rejected well-formed Arabic")

        arabic_phrase = re.compile(unicode_phrase_boundary("ليه"))
        for standalone in ("ليه", "ليه؟"):
            if not arabic_phrase.search(standalone):
                raise AssertionError(f"standalone Arabic token was missed: {standalone}")
        for embedded in ("إليه", "عليه", "إليهم"):
            if arabic_phrase.search(embedded):
                raise AssertionError(f"internal Arabic characters caused a phrase match: {embedded}")

        for standalone in ("ليه؟", "ليه تغيرت النتيجة؟"):
            if runner.deterministic_assessment_check(standalone, [])["passed"]:
                raise AssertionError(f"standalone Arabic assessment phrase was missed: {standalone}")
        for embedded in ("اتجه إليه؟", "هل الطريق عليه آمن؟", "وصلت إليهم؟"):
            if not runner.deterministic_assessment_check(embedded, [])["passed"]:
                raise AssertionError(f"internal Arabic characters caused a phrase false positive: {embedded}")
        if runner.deterministic_assessment_check("Why did the value change?", [])["passed"]:
            raise AssertionError("existing English assessment phrase was missed")
        if not runner.learner_opted_into_assessment([{"role": "user", "content": "Please test me."}]):
            raise AssertionError("existing English assessment opt-in phrase was missed")
        legacy_lifecycle = [
            {"role": "user", "content": "Please test me."},
            {"role": "user", "content": "Here is my first answer."},
        ]
        if not runner.learner_opted_into_assessment(legacy_lifecycle):
            raise AssertionError("legacy assessment acceptance was not retained across a neutral answer")
        legacy_lifecycle.append({"role": "user", "content": "Do not test me now."})
        if runner.learner_opted_into_assessment(legacy_lifecycle):
            raise AssertionError("a later legacy refusal did not revoke assessment acceptance")
        structured_accept = [{
            "role": "learner",
            "content": "نعم، أوافق على الفحص.",
            "assessment_intent": "accept",
        }]
        if not runner.deterministic_assessment_check(
            "اكتب إجابتك الآن.", structured_accept
        )["passed"]:
            raise AssertionError("structured Arabic assessment acceptance was ignored")
        structured_decline = [{
            "role": "learner",
            "content": "لا أريد الأسئلة الآن.",
            "assessment_intent": "decline",
        }]
        if runner.deterministic_assessment_check(
            "اكتب إجابتك الآن.", structured_decline
        )["passed"]:
            raise AssertionError("structured Arabic assessment refusal permitted a question")
        contradictory = [{
            "role": "learner",
            "content": "I do not agree to the quiz.",
            "assessment_intent": "accept",
        }]
        if runner.deterministic_assessment_check(
            "Answer this question.", contradictory
        )["passed"]:
            raise AssertionError("contradictory structured intent did not fail closed")

        accepted_event = {
            "role": "learner",
            "content": "I accept the short check.",
            "assessment_intent": "accept",
        }
        ten_word_question = "Which sorting method should this dataset use, and why exactly?"
        if len(ten_word_question.split()) != 10:
            raise AssertionError("the short-assessment regression fixture must contain exactly ten words")
        if not runner.deterministic_completeness_check(
            ten_word_question, learner_event=accepted_event
        )["passed"]:
            raise AssertionError("a complete ten-word post-consent assessment question was rejected")
        if not runner.deterministic_completeness_check(
            "أي طريقة تناسب هذه المسألة الجديدة، وما سبب اختيارك لها؟",
            learner_event={
                "role": "learner",
                "content": "أختار الفحص القصير.",
                "assessment_intent": "accept",
            },
        )["passed"]:
            raise AssertionError("a complete Arabic post-consent assessment question was rejected")
        if runner.deterministic_assessment_check(
            ten_word_question,
            learner_event={
                "role": "learner", "content": "I need more explanation.", "assessment_intent": "none"
            },
        )["passed"]:
            raise AssertionError("the same question was allowed before structured acceptance")
        if runner.deterministic_completeness_check(
            "This short explanation states a rule but omits useful supporting detail.",
            learner_event=accepted_event,
        )["passed"]:
            raise AssertionError("acceptance weakened completeness for a substantive explanation")
        for minimal in ("Ready?", "Answer?", "جاهز؟", "أجب."):
            if runner.deterministic_completeness_check(
                minimal, learner_event=accepted_event
            )["passed"]:
                raise AssertionError(f"a minimal post-consent response passed completeness: {minimal}")
        if runner.deterministic_completeness_check(
            ten_word_question.removesuffix("?"), learner_event=accepted_event
        )["passed"]:
            raise AssertionError("truncated post-consent assessment text passed completeness")
        normal_teaching = (
            "This complete explanation introduces the rule, demonstrates its use, and ends with a clear example."
        )
        if not runner.deterministic_completeness_check(normal_teaching)["passed"]:
            raise AssertionError("an existing normal-length teaching response failed completeness")
        for blocked_event in (
            {"role": "learner", "content": "I decline the check.", "assessment_intent": "decline"},
            {"role": "learner", "content": "I need more explanation."},
            {"role": "learner", "content": "I accept the check.", "assessment_intent": "unknown"},
        ):
            if runner.deterministic_completeness_check(
                ten_word_question, learner_event=blocked_event
            )["passed"]:
                raise AssertionError(f"invalid assessment authority enabled the short threshold: {blocked_event}")
            if runner.deterministic_assessment_check(
                ten_word_question, learner_event=blocked_event
            )["passed"]:
                raise AssertionError(f"invalid assessment authority permitted a question: {blocked_event}")

        dialect = runner.deterministic_language_check(
            "هذا شرح عام، لكن النتيجة مش واضحة حتى الآن ونحتاج إلى مثال آخر.", "ar-MSA"
        )
        if dialect["passed"] or "مش" not in dialect["reason"]:
            raise AssertionError("standalone dialect token was not rejected")
        standard = runner.deterministic_language_check(
            "هذا المشروع يشرح الفكرة بطريقة واضحة، ويعرض نتيجة صحيحة ومثالا مفيدا للمتعلم.", "ar-MSA"
        )
        if not standard["passed"] or "مش" in standard["reason"]:
            raise AssertionError("dialect characters embedded in a standard Arabic word were falsely rejected")

    print("Teach Me behavioral eval runner tests passed (pass and critical-fail paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
