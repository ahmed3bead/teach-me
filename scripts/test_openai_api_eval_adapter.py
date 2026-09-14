#!/usr/bin/env python3
"""Mocked tests for the official OpenAI Responses API adapter."""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import openai_api_eval_adapter as adapter
import run_behavioral_evals as runner
from behavioral_eval_contract import immutable_prompt_packet

CAPABILITIES = {
    "source": "not_required",
    "web": "not_required",
    "file": "not_required",
    "rendering": "not_required",
    "sandbox": "not_required",
    "video": "not_required",
    "external_catalog": "not_required",
}
ROUTING = {
    "audience": "learner",
    "mode": "topic-led",
    "source_type": "none",
    "artifact_type": "chat",
    "session_state": "new",
    "accessibility": "standard",
    "safety_level": "standard",
    "instructional_scope": "brief",
    "assessment_state": "none",
    "domain_pack": "none",
}


class FakeResponses:
    def __init__(self, raw: dict[str, object]) -> None:
        self.raw = raw
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(
            status="completed",
            output_text=json.dumps(self.raw),
            model="gpt-5.6-sol",
            id="resp_test",
            _request_id="req_test",
            service_tier="default",
            created_at=1_789_000_000,
            usage=SimpleNamespace(
                input_tokens=120,
                input_tokens_details=SimpleNamespace(cached_tokens=20, cache_write_tokens=0),
                output_tokens=30,
                output_tokens_details=SimpleNamespace(reasoning_tokens=0),
                total_tokens=150,
            ),
        )


def fake_client(raw: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(responses=FakeResponses(raw))


def generation_payload() -> dict[str, object]:
    case = {
        "id": "mock",
        "locale": "en",
        "prompt": "Explain a small concept.",
        "expected": ["the explanation is useful"],
        "critical": False,
        "routing": copy.deepcopy(ROUTING),
        "capabilities": copy.deepcopy(CAPABILITIES),
        "fixture_refs": {},
    }
    return {
        "type": "generate",
        "suite": "mock-suite",
        "case_id": "mock",
        "locale": "en",
        "prompt": case["prompt"],
        "history": [],
        "turn_index": 1,
        "turn_count": 1,
        "prompt_packet": immutable_prompt_packet("mock-suite", case),
    }


def test_generation_request() -> None:
    raw = {"response": "A complete teaching explanation with one clear example.", "artifacts": []}
    client = fake_client(raw)
    result = adapter.execute(generation_payload(), "response", "gpt-5.6-sol", 2048, "none", 0.0, adapter.API_KEY_ENV, client)
    call = client.responses.calls[0]
    assert call["model"] == "gpt-5.6-sol"
    assert call["store"] is False and call["tools"] == [] and call["parallel_tool_calls"] is False
    assert call["service_tier"] == "default" and call["max_output_tokens"] == 2048
    assert call["reasoning"] == {"effort": "none"} and call["temperature"] == 0.0
    assert call["text"]["format"]["strict"] is True
    assert result["model"] == "openai/gpt-5.6-sol"
    assert result["settings"]["model_transport"] == "openai-responses-api-standard"
    assert result["settings"]["api_key_env"] == "OPENAI_API_KEY"
    assert result["usage"] == {
        "input_tokens": 120,
        "cached_input_tokens": 20,
        "cache_write_tokens": 0,
        "output_tokens": 30,
        "reasoning_tokens": 0,
        "total_tokens": 150,
    }
    assert result["api"]["request_id"] == "req_test" and result["raw_result"] == raw


def test_grader_schema_and_normalization() -> None:
    protocol = adapter.output_schema({"type": "grade", "criteria": ["one"]})
    strict = adapter.provider_schema(protocol)
    evidence = strict["properties"]["results"]["items"]["properties"]["evidence"]
    assert set(evidence["required"]) == {"source", "turn", "artifact_path", "quote"}
    raw = {
        "results": [
            {
                "verdict": "pass",
                "evidence": {"source": "response", "turn": 1, "artifact_path": None, "quote": "clear example"},
                "reason": "The exact quote supplies the required evidence.",
            }
        ]
    }
    client = fake_client(raw)
    payload = {
        "type": "grade",
        "suite": "mock-suite",
        "case_id": "mock",
        "ordered_transcript": [
            {"role": "user", "turn": 1, "content": "Teach."},
            {"role": "assistant", "turn": 1, "content": "A clear example."},
        ],
        "assessment_events": [],
        "case_context": {},
        "controlled_inputs": {},
        "artifacts": [],
        "raw_final_response": "A clear example.",
        "criteria": ["one"],
        "evidence_requirements": "Exact evidence.",
    }
    result = adapter.execute(payload, "grader", "gpt-5.6-sol", 2048, "none", 0.0, adapter.API_KEY_ENV, client)
    assert result["results"][0]["evidence"] == {"source": "response", "turn": 1, "quote": "clear example"}
    assert result["raw_result"] == raw


def test_secret_boundaries_and_release_identity() -> None:
    canary = "unit-test-secret-canary"
    environment = {"PATH": os.environ.get("PATH", ""), "OPENAI_API_KEY": canary, "UNRELATED_SECRET": canary}
    assert "OPENAI_API_KEY" not in runner.adapter_environment(environment)
    scoped = runner.adapter_environment(environment, "OPENAI_API_KEY")
    assert scoped["OPENAI_API_KEY"] == canary and "UNRELATED_SECRET" not in scoped
    assert runner.safe_adapter_command("python adapter.py --api-key-env OPENAI_API_KEY")[-1] == "OPENAI_API_KEY"
    for command in ("python adapter.py --api-key literal", "python adapter.py --api-key-env OTHER_SECRET"):
        try:
            runner.safe_adapter_command(command)
        except RuntimeError:
            pass
        else:
            raise AssertionError("credential-bearing command was accepted")
    assert canary not in adapter.redacted_message(RuntimeError(f"failure: {canary}"), canary)
    try:
        adapter.require_api_key({}, "OPENAI_API_KEY")
    except ValueError as exc:
        assert canary not in str(exc)
    else:
        raise AssertionError("missing API key was accepted")

    evidence = {"model": "openai/gpt-5.6-sol", "settings": {"model": "gpt-5.6-sol"}}
    runner.validate_release_model(evidence, "response", True, "openai/gpt-5.6-sol")
    try:
        runner.validate_release_model(evidence, "response", True, "codex/gpt-5.6-sol")
    except RuntimeError:
        pass
    else:
        raise AssertionError("provider mismatch was accepted")


def main() -> int:
    test_generation_request()
    test_grader_schema_and_normalization()
    test_secret_boundaries_and_release_identity()
    print("Teach Me OpenAI API adapter mocked tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
