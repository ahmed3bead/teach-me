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

    def test_corrective_retry_uses_next_reproducible_seed(self):
        self.assertEqual(adapter.seed_for_payload(7, {"attempt_index": 1}), 7)
        self.assertEqual(adapter.seed_for_payload(7, {"attempt_index": 2}), 1016)

    def test_generate_infers_arabic_and_forbids_english_switch(self):
        payload = {
            "type": "generate",
            "prompt": "أنا عاوز أفهم الكسور من الصفر",
            "history": [],
        }
        self.assertEqual(adapter.requested_locale(payload), "ar-MSA")
        messages, _schema, _temperature = adapter.messages_and_schema(payload, "skill")
        system = messages[0]["content"]
        self.assertIn("اكتب الرد كله بفصحى مبسطة", system)
        self.assertIn("ممنوع تحويل الشرح إلى الإنجليزية", system)

    def test_legacy_ar_eg_locale_maps_to_simplified_msa(self):
        self.assertEqual(adapter.requested_locale({"locale": "ar-EG", "prompt": "عاوز أتعلم"}), "ar-MSA")
        self.assertEqual(adapter.locale_instruction("ar-EG"), adapter.locale_instruction("ar-MSA"))

    def test_english_question_uses_english(self):
        payload = {"type": "generate", "prompt": "Explain fractions simply.", "history": []}
        self.assertEqual(adapter.requested_locale(payload), "en")
        messages, _schema, _temperature = adapter.messages_and_schema(payload, "skill")
        self.assertIn("Respond entirely in English", messages[0]["content"])

    def test_explicit_english_request_overrides_arabic_wording(self):
        payload = {"type": "generate", "locale": "ar-MSA", "prompt": "اشرح الكسور بالإنجليزية", "history": []}
        self.assertEqual(adapter.requested_locale(payload), "en")

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


if __name__ == "__main__":
    unittest.main()
