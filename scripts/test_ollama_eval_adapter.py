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
        )
        self.assertEqual(result["response"], "أهلاً")
        self.assertEqual(result["model"], "ollama/qwen3:8b")
        sent = json.loads(mocked.call_args.args[0].data.decode("utf-8"))
        self.assertFalse(sent["stream"])
        self.assertEqual(sent["format"]["required"], ["response"])

    def test_role_mapping_rejects_wrong_adapter(self):
        self.assertEqual(adapter.role_for_payload("simulation-grade"), "grader")
        with self.assertRaises(ValueError):
            adapter.role_for_payload("unknown")


if __name__ == "__main__":
    unittest.main()
