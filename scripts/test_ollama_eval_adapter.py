#!/usr/bin/env python3
"""Unit tests for the local Ollama evaluation adapter."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import ollama_eval_adapter as adapter


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return json.dumps({"model": "qwen3:8b", "message": {"content": '{"response":"أهلاً"}'}}).encode()


class AdapterTests(unittest.TestCase):
    def test_remote_hosts_require_explicit_opt_in(self):
        adapter.require_local_host("http://localhost:11434", False)
        with self.assertRaises(ValueError):
            adapter.require_local_host("https://example.com", False)

    def test_loads_skill_and_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "SKILL.md").write_text("skill", encoding="utf-8")
            (root / "references").mkdir()
            (root / "references" / "mode.md").write_text("mode", encoding="utf-8")
            context = adapter.load_skill_context(root)
        self.assertIn("SKILL.md", context)
        self.assertIn("references/mode.md", context)

    @mock.patch("ollama_eval_adapter.request.urlopen", return_value=FakeResponse())
    def test_chat_returns_runner_shape_and_model(self, mocked):
        result = adapter.ollama_chat(
            "http://localhost:11434",
            "qwen3:8b",
            [{"role": "user", "content": "مرحبا"}],
            adapter.text_schema("response"),
            0.2,
            30,
            4096,
            512,
            7,
        )
        self.assertEqual(result["response"], "أهلاً")
        self.assertEqual(result["model"], "ollama/qwen3:8b")
        self.assertEqual(result["seed"], 7)
        sent = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertFalse(sent["stream"])
        self.assertFalse(sent["think"])
        self.assertEqual(sent["options"]["num_predict"], 512)
        self.assertEqual(sent["options"]["repeat_penalty"], 1.0)
        self.assertEqual(sent["options"]["seed"], 7)
        self.assertEqual(sent["format"]["required"], ["response"])

    def test_role_mapping_rejects_wrong_adapter(self):
        self.assertEqual(adapter.role_for_payload("simulation-grade"), "grader")
        with self.assertRaises(ValueError):
            adapter.role_for_payload("unknown")

    def test_combined_simulation_grade_has_no_model_protocol(self):
        with self.assertRaisesRegex(ValueError, "must be decomposed"):
            adapter.messages_and_schema(
                {"type": "simulation-grade", "locale": "en", "expected": []}, None
            )
        schema = adapter.grade_schema(1)
        self.assertEqual(schema["required"], ["results"])
        self.assertNotIn("baseline_score", schema["properties"])
        self.assertNotIn("transfer_score", schema["properties"])

    def test_corrective_retry_uses_next_reproducible_seed(self):
        self.assertEqual(adapter.seed_for_payload(7, {"attempt_index": 1}), 7)
        self.assertEqual(adapter.seed_for_payload(7, {"attempt_index": 2}), 1016)

    def test_invalid_simulation_scores_are_rejected_without_coercion(self):
        self.assertIn("not bool", adapter.simulation_score_error({"score": False, "reason": "evidence"}))
        self.assertIn("not str", adapter.simulation_score_error({"score": "1", "reason": "evidence"}))
        self.assertIsNone(adapter.simulation_score_error({"score": 1.0, "reason": "evidence"}))

    def test_grader_reason_cannot_merely_repeat_the_criterion(self):
        criterion = "the learner applies the new rule"
        self.assertIn(
            "repeats the criterion",
            adapter.grader_decision_error(
                {"results": [{"verdict": "pass", "reason": criterion}]}, criterion
            ),
        )
        passed = adapter.derive_simulation_criterion(
            {"results": [{"verdict": "pass", "reason": "The answer applies rule A to the unseen input."}]},
            criterion,
        )
        failed = adapter.derive_simulation_criterion(
            {"results": [{"verdict": "fail", "reason": "The answer never applies rule A."}]},
            criterion,
        )
        self.assertTrue(passed["passed"])
        self.assertFalse(failed["passed"])

    def test_invalid_simulation_verdicts_fail_closed(self):
        criterion = "the learner applies the new rule"
        invalid = [
            {"results": [{"reason": "Evidence is missing."}]},
            {"results": [{"verdict": "unknown", "reason": "Evidence is missing."}]},
            {"results": [{"verdict": True, "reason": "Evidence is missing."}]},
            {"results": [{"verdict": None, "reason": "Evidence is missing."}]},
        ]
        for result in invalid:
            self.assertIsNotNone(adapter.grader_decision_error(result, criterion))
            with self.assertRaises(ValueError):
                adapter.derive_simulation_criterion(result, criterion)

    def test_only_structured_output_failures_are_retryable(self):
        self.assertTrue(
            adapter.retryable_structured_output_error(
                RuntimeError("Ollama did not return valid structured JSON: 'draft'")
            )
        )
        self.assertFalse(adapter.retryable_structured_output_error(RuntimeError("cannot reach Ollama")))

    def test_generate_infers_arabic_and_forbids_english_switch(self):
        payload = {
            "type": "generate",
            "prompt": "أنا عاوز أفهم الكسور من الصفر",
            "history": [],
        }
        self.assertEqual(adapter.requested_locale(payload), "ar-MSA")
        messages, _schema, temperature = adapter.messages_and_schema(payload, "skill")
        system = messages[0]["content"]
        self.assertIn("اكتب الرد كله بفصحى مبسطة", system)
        self.assertIn("ممنوع تحويل الشرح إلى الإنجليزية", system)

    def test_legacy_ar_eg_locale_maps_to_simplified_msa(self):
        self.assertEqual(adapter.requested_locale({"locale": "ar-EG", "prompt": "عاوز أتعلم"}), "ar-MSA")
        self.assertEqual(adapter.locale_instruction("ar-EG"), adapter.locale_instruction("ar-MSA"))

    def test_english_question_uses_english(self):
        payload = {"type": "generate", "prompt": "Explain fractions simply.", "history": []}
        self.assertEqual(adapter.requested_locale(payload), "en")
        messages, _schema, temperature = adapter.messages_and_schema(payload, "skill")
        self.assertIn("Respond entirely in English", messages[0]["content"])

    def test_explicit_english_request_overrides_arabic_wording(self):
        payload = {"type": "generate", "locale": "ar-MSA", "prompt": "اشرح الكسور بالإنجليزية", "history": []}
        self.assertEqual(adapter.requested_locale(payload), "en")
        self.assertEqual(adapter.requested_locale({"prompt": "اشرح بالإنجليزية."}), "en")
        self.assertEqual(adapter.requested_locale({"prompt": "هذه كلمة بالإنجليزيةمبسطة داخل نص عربي"}), "ar-MSA")

    def test_unsupported_locale_is_rejected_instead_of_silently_widened(self):
        with self.assertRaises(ValueError):
            adapter.requested_locale({"locale": "ar-SA", "prompt": "اشرح الكسور"})

    def test_simplified_msa_locale_avoids_english_and_local_dialect(self):
        instruction = adapter.locale_instruction("ar-MSA")
        self.assertIn("فصحى مبسطة", instruction)
        self.assertIn("تناسب عمر المتعلم", instruction)
        self.assertIn("تجنب اللهجات المحلية", instruction)
        self.assertIn("ممنوع تحويل الشرح إلى الإنجليزية", instruction)

        payload = {
            "type": "generate",
            "locale": "ar-MSA",
            "prompt": "اشرح الكسور",
            "history": [],
        }
        contract = adapter.teacher_output_contract(payload)
        self.assertIn("إن أحببت، يمكننا تجربة سؤال قصير", contract)
        self.assertIn("من دون حركات أو علامات تشكيل اختيارية", contract)
        self.assertIn("إذا كنت تفهم فسأختبرك", contract)
        for term in ("API", "Replication", "Contract Test", "Prompt", "Database"):
            self.assertIn(term, contract)
        self.assertIn("API (واجهة تسمح لبرنامج بالتواصل مع برنامج آخر)", contract)
        self.assertIn('<bdi dir="ltr">', contract)
        self.assertIn('dir="ltr"', contract)

    def test_teacher_contract_repeats_language_rule_after_skill_context(self):
        payload = {
            "type": "generate",
            "locale": "ar-MSA",
            "prompt": "اشرح الكسور",
            "history": [],
        }
        messages, _schema, _temperature = adapter.messages_and_schema(payload, "skill-context")
        system = messages[0]["content"]
        self.assertLess(system.index("skill-context"), system.index("عقد إخراج إلزامي"))
        self.assertIn("فلا تسأله سؤال معرفة", system)
        self.assertIn("100 إلى 180 كلمة", system)

    def test_simulation_roles_enforce_msa_and_adaptive_representation_generically(self):
        teacher_payload = {
            "type": "teach",
            "locale": "ar-MSA",
            "turn_index": 2,
            "learner_message": "ما زلت لا أفهم الفرق.",
            "history": [
                {"role": "learner", "content": "اشرح الفكرة من البداية."},
                {"role": "teacher", "content": "هذا هو التعريف الأساسي للفكرة."},
            ],
            "teaching_material": "The higher constraint applies before the default rule.",
            "max_turns": 4,
        }
        teacher_contract = adapter.simulation_teacher_contract(teacher_payload)
        self.assertIn("materially different representation", teacher_contract)
        self.assertIn("repeated or lightly paraphrased explanation is not a repair", teacher_contract)
        self.assertIn("higher-priority constraint before the general rule", teacher_contract)
        self.assertIn("Do not mirror dialectal function words", teacher_contract)
        self.assertIn("never transliterate them into Arabic script", teacher_contract)
        self.assertIn("include no question or task", teacher_contract)

        learner_payload = {
            "type": "dialogue",
            "locale": "ar-MSA",
            "learner_persona": "A beginner who may write informally.",
            "learner_behaviors": ["Ask for a clearer comparison."],
            "history": [],
            "turn_index": 1,
            "max_turns": 3,
        }
        messages, _schema, _temperature = adapter.messages_and_schema(learner_payload, None)
        learner_contract = messages[0]["content"]
        self.assertIn("natural simplified Modern Standard Arabic", learner_contract)
        self.assertIn("Do not mirror dialectal function words", learner_contract)
        self.assertIn("technical terms in their original language", learner_contract)

        self.assertTrue(adapter.learner_opted_in({"locale": "ar-MSA", "learner_message": "نعم، أوافق."}))
        self.assertFalse(adapter.learner_opted_in({"locale": "ar-MSA", "learner_message": "هذا مستعدون له."}))
        self.assertTrue(adapter.learner_opted_in({"locale": "en", "learner_message": "Ready?"}))
        self.assertFalse(adapter.learner_opted_in({"locale": "en", "learner_message": "Readying notes."}))

    def test_child_contract_teaches_equal_parts_before_one_symbol(self):
        payload = {
            "type": "generate",
            "locale": "ar-MSA",
            "prompt": "اشرح لطفل في ابتدائي مفهوم الكسور من الصفر",
            "history": [],
        }
        contract = adapter.teacher_output_contract(payload)
        self.assertTrue(adapter.child_lesson_requested(payload))
        self.assertIn("سنبدأ من الصفر بخطوة بسيطة", contract)
        self.assertIn("الجمل الثلاث الأولى بلا أي رمز رياضي", contract)
        self.assertIn("للشريط جزآن متساويان", contract)
        self.assertIn("الجزآن معا يشكلان الشريط الكامل", contract)
        self.assertIn("لا تضف جملة تبدأ بكلمة «إذا»", contract)
        self.assertIn("رمزًا واحدًا فقط مثل 1/2", contract)
        self.assertIn("لا تضف 1/4 أو 3/4", contract)

    def test_technical_comparison_contract_requires_direct_first_use_definitions(self):
        payload = {
            "type": "generate",
            "locale": "ar-MSA",
            "prompt": "اشرح الفرق بين API وDatabase Replication",
            "history": [],
        }
        contract = adapter.teacher_output_contract(payload)
        self.assertIn("ابدأ المقارنة بتعريفين مباشرين بين قوسين", contract)
        self.assertIn("API ينظم التواصل ولا ينسخ قاعدة البيانات", contract)
        self.assertIn("Database Replication يزامن نسخ البيانات", contract)

    def test_retry_contract_names_invalid_prior_response(self):
        payload = {
            "type": "generate",
            "locale": "ar-MSA",
            "prompt": "اشرح الكسور",
            "history": [],
            "retry_feedback": "اللغة غير صحيحة",
        }
        contract = adapter.teacher_output_contract(payload)
        self.assertIn("تصحيح إلزامي في هذه المحاولة: اللغة غير صحيحة", contract)
        self.assertNotIn("English response", contract)

    def test_arabic_teacher_uses_compact_localized_skill_context(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "SKILL.md").write_text("English skill contract", encoding="utf-8")
            context = adapter.teacher_skill_context(root, {"locale": "ar-MSA"})
        self.assertIn("أنت معلّم صبور ودقيق", context)
        self.assertIn("ثبّت اسم الشيء نفسه", context)
        self.assertNotIn("English skill contract", context)

    def test_grader_requires_concrete_evidence_in_order(self):
        payload = {
            "type": "grade",
            "locale": "ar-MSA",
            "expected": ["first criterion", "second criterion"],
            "response": "response",
        }
        messages, _schema, _temperature = adapter.messages_and_schema(payload, None)
        system = messages[0]["content"]
        self.assertIn("دليلًا محددًا", system)
        self.assertIn("ممنوع نسخ نص المعيار", system)
        self.assertIn("قيّم كل معيار منفصلًا", system)
        self.assertIn("لا تطلب وجود سؤال قبل الموافقة", system)

        _messages, schema, _temperature = adapter.messages_and_schema(payload, None)
        self.assertEqual(schema["properties"]["results"]["items"]["properties"]["reason"]["maxLength"], 300)

        one = {**payload, "expected": ["one criterion"]}
        one_messages, _schema, _temperature = adapter.messages_and_schema(one, None)
        self.assertIn("يوجد معيار واحد فقط", one_messages[0]["content"])

    def test_simulation_teacher_stays_inside_authorized_fictional_material(self):
        payload = {
            "type": "teach",
            "locale": "en",
            "teaching_material": "Local rules run before global rules.",
            "history": [],
            "learner_message": "Teach me from zero.",
            "turn_index": 1,
        }
        messages, _schema, temperature = adapter.messages_and_schema(payload, "skill")
        self.assertIn("Use only facts explicitly stated", messages[0]["content"])
        self.assertIn("Add no rule, exception, or override", messages[0]["content"])
        self.assertIn("labels have no implied real-world meaning", messages[0]["content"])
        self.assertIn("one complete example", messages[0]["content"])
        self.assertGreater(messages[0]["content"].index("CLOSED-BOOK SIMULATION BOUNDARY"), messages[0]["content"].index("skill"))
        self.assertIn("brief optional-check invitation", messages[0]["content"])
        content = json.loads(messages[1]["content"])
        self.assertIn("operational decision path", " ".join(content["response_requirements"]))
        self.assertEqual(temperature, 0.0)

    def test_simulated_arabic_learner_uses_msa_and_advances_behaviors_once(self):
        payload = {
            "type": "dialogue",
            "locale": "ar-MSA",
            "learner_persona": "متعلم يبدأ من الصفر",
            "learner_behaviors": ["اطلب توضيحًا مرة واحدة"],
            "history": [],
        }
        messages, _schema, _temperature = adapter.messages_and_schema(payload, None)
        self.assertIn("simplified Modern Standard Arabic", messages[0]["content"])
        self.assertIn("at most once", messages[0]["content"])

    def test_simulation_grader_scores_baseline_and_transfer_separately(self):
        source = {
            "locale": "ar-MSA",
            "baseline_task": "baseline task",
            "baseline_answer": "I do not know.",
            "transfer_task": "transfer task",
            "transfer_answer": "A maps to B.",
            "teaching_material": "A maps to B.",
        }
        baseline = adapter.simulation_score_payload(source, "baseline")
        transfer = adapter.simulation_score_payload(source, "transfer")
        self.assertNotIn("transfer_answer", baseline)
        self.assertNotIn("baseline_answer", transfer)
        messages, schema, temperature = adapter.messages_and_schema(baseline, None)
        self.assertIn("admits missing knowledge", messages[0]["content"])
        self.assertIn("score", schema["required"])
        self.assertEqual(temperature, 0.0)

    def test_simulation_criterion_grading_does_not_request_scores(self):
        payload = {
            "type": "grade",
            "evaluation_mode": "simulation-criterion",
            "locale": "en",
            "expected": ["the teacher repairs confusion"],
            "baseline_answer": "I do not know.",
            "transcript": [{"role": "teacher", "content": "Here is a decision table."}],
            "transfer_answer": "The new case follows the first row.",
        }
        messages, schema, _temperature = adapter.messages_and_schema(payload, None)
        self.assertIn("only the evidence authorized by", messages[0]["content"])
        self.assertIn("Set verdict to 'pass'", messages[0]["content"])
        self.assertNotIn("PASS:", messages[0]["content"])
        self.assertNotIn("FAIL:", messages[0]["content"])
        item_properties = schema["properties"]["results"]["items"]["properties"]
        self.assertIn("verdict", item_properties)
        self.assertNotIn("passed", item_properties)
        self.assertNotIn("baseline_score", schema["properties"])

    def test_simulation_criterion_payload_exposes_only_declared_evidence_scope(self):
        source = {
            "locale": "en",
            "simulation_id": "suite/case",
            "baseline_task": "baseline task",
            "baseline_answer": "baseline answer",
            "teaching_material": "secret rules",
            "transcript": ["complete transcript"],
            "transfer_task": "transfer task",
            "transfer_answer": "transfer answer",
        }
        baseline = adapter.simulation_criterion_payload(
            source, {"evidence_scope": "baseline", "criterion": "starts at zero"}
        )
        self.assertEqual(baseline["baseline_answer"], "baseline answer")
        self.assertNotIn("transcript", baseline)
        self.assertNotIn("transfer_answer", baseline)
        transfer = adapter.simulation_criterion_payload(
            source, {"evidence_scope": "transfer", "criterion": "applies the rule"}
        )
        self.assertEqual(transfer["transfer_answer"], "transfer answer")
        self.assertNotIn("baseline_answer", transfer)
        self.assertNotIn("transcript", transfer)

    def test_transfer_prompt_requires_precedence_dimensions_in_taught_order(self):
        payload = {
            "type": "transfer",
            "locale": "en",
            "learner_persona": "A beginner",
            "learner_behaviors": [],
            "history": [],
            "task": "Apply the fictional rules.",
        }
        messages, _schema, _temperature = adapter.messages_and_schema(payload, None)
        self.assertIn("same learner after the lesson", messages[0]["content"])
        self.assertNotIn("Behaviors:", messages[0]["content"])
        transfer_request = json.loads(messages[1]["content"])
        self.assertIn("apply those dimensions in their stated order", transfer_request["instruction"])
        self.assertIn("one final answer with no draft", transfer_request["instruction"])

        retry_payload = {**payload, "adapter_retry_feedback": "invalid JSON"}
        retry_messages, _schema, _temperature = adapter.messages_and_schema(retry_payload, None)
        self.assertIn("OUTPUT-SHAPE CORRECTION", retry_messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
