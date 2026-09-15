#!/usr/bin/env python3
"""Mocked tests for the official OpenAI Responses API adapter."""

from __future__ import annotations

import copy
import hashlib
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
    def __init__(
        self,
        raw: dict[str, object],
        *,
        status: str = "completed",
        incomplete_reason: str | None = None,
        output_text: str | None = None,
    ) -> None:
        self.raw = raw
        self.status = status
        self.incomplete_reason = incomplete_reason
        self.output_text = output_text
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> SimpleNamespace:
        self.calls.append(kwargs)
        return SimpleNamespace(
            status=self.status,
            incomplete_details=SimpleNamespace(reason=self.incomplete_reason),
            output_text=(
                self.output_text
                if self.output_text is not None
                else json.dumps(self.raw) if self.status == "completed" else "{truncated"
            ),
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


def fake_client(
    raw: dict[str, object],
    *,
    status: str = "completed",
    incomplete_reason: str | None = None,
    output_text: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        responses=FakeResponses(
            raw, status=status, incomplete_reason=incomplete_reason, output_text=output_text
        )
    )


def generation_payload(
    *,
    artifact_type: str = "chat",
    instructional_scope: str = "brief",
    file_capability: str = "not_required",
    rendering_capability: str = "not_required",
) -> dict[str, object]:
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
    case["routing"].update(
        artifact_type=artifact_type,
        instructional_scope=instructional_scope,
    )
    case["capabilities"]["file"] = file_capability
    case["capabilities"]["rendering"] = rendering_capability
    if file_capability == "executable_temp":
        case["fixture_refs"] = {"file": "file.disposable-workspace.v1"}
    if rendering_capability == "executable_temp":
        case["fixture_refs"]["rendering"] = "rendering.pdf-from-html.v1"
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


def test_long_artifact_budget_and_incomplete_evidence() -> None:
    raw = {"response": "A complete teaching explanation with one clear example.", "artifacts": []}
    long_client = fake_client(raw)
    long_result = adapter.execute(
        generation_payload(artifact_type="curriculum", instructional_scope="substantial", file_capability="executable_temp"),
        "response",
        "gpt-5.6-sol",
        2048,
        "none",
        0.0,
        adapter.API_KEY_ENV,
        long_client,
        4096,
    )
    assert long_client.responses.calls[0]["max_output_tokens"] == 4096
    assert long_result["settings"]["long_artifact_budget_applied"] is True
    assert long_result["settings"]["configured_max_output_tokens"] == 2048

    incomplete_client = fake_client(
        {}, status="incomplete", incomplete_reason="max_output_tokens"
    )
    incomplete = adapter.execute(
        generation_payload(artifact_type="curriculum", instructional_scope="substantial", file_capability="executable_temp"),
        "response",
        "gpt-5.6-sol",
        2048,
        "none",
        0.0,
        adapter.API_KEY_ENV,
        incomplete_client,
        4096,
    )
    assert incomplete["evaluation_error"] == {
        "kind": "model-incomplete",
        "status": "incomplete",
        "reason": "max_output_tokens",
    }
    assert incomplete["raw_result"] == {
        "status": "incomplete",
        "incomplete_details": {"reason": "max_output_tokens"},
    }
    assert incomplete["response"] == "" and incomplete["artifact_evidence"] == []
    assert incomplete["usage"]["output_tokens"] == 30


def test_completed_malformed_output_preserves_usage() -> None:
    client = fake_client({}, output_text="not one JSON object")
    result = adapter.execute(
        generation_payload(),
        "response", "gpt-5.6-sol", 2048, "none", 0.0,
        adapter.API_KEY_ENV, client, 4096,
    )
    assert result["evaluation_error"]["kind"] == "response-schema"
    assert result["response"] == "" and result["artifact_evidence"] == []
    assert result["raw_result"]["unparsed_output"] == "not one JSON object"
    assert result["usage"]["total_tokens"] == 150
    assert result["model"] == "openai/gpt-5.6-sol"

    grader = adapter.execute(
        {"type": "grade", "criteria": ["one"]},
        "grader", "gpt-5.6-sol", 2048, "none", 0.0,
        adapter.API_KEY_ENV, fake_client({"response": "wrong schema"}), 4096,
    )
    assert grader["evaluation_error"]["kind"] == "grader-schema"
    assert "results" not in grader and grader["usage"]["total_tokens"] == 150


def test_output_budget_routing() -> None:
    for artifact_type in ("markdown", "html", "pdf", "curriculum", "learning-pack"):
        payload = generation_payload(
            artifact_type=artifact_type,
            instructional_scope="substantial",
            file_capability="executable_temp",
        )
        assert adapter.uses_long_artifact_budget(payload), artifact_type
        assert adapter.effective_output_token_limit(payload, 2048, 4096) == 4096

    ordinary = (
        generation_payload(),
        generation_payload(
            artifact_type="html",
            instructional_scope="brief",
            file_capability="executable_temp",
        ),
        generation_payload(
            artifact_type="pdf",
            instructional_scope="substantial",
            file_capability="not_required",
        ),
    )
    for payload in ordinary:
        assert not adapter.uses_long_artifact_budget(payload)
        assert adapter.effective_output_token_limit(payload, 2048, 4096) == 2048

    grader_payload = generation_payload(
        artifact_type="curriculum",
        instructional_scope="journey",
        file_capability="executable_temp",
    )
    grader_payload["type"] = "grade"
    assert adapter.effective_output_token_limit(grader_payload, 2048, 4096) == 2048


def test_invalid_artifact_evidence() -> None:
    html = (
        '<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
        '<style>@page{size:A4;margin:18mm}html,body{direction:rtl}'
        'bdi,.ltr,code,pre{unicode-bidi:isolate}bdi[dir="ltr"]{white-space:nowrap}'
        '.ltr,code,pre{direction:ltr}pre,table{break-inside:avoid}</style>'
        '</head><body><p>محتوى عربي صالح الاتجاه لكنه بلا معلم رئيسي.</p></body></html>'
    )
    raw = {
        "response": "تم حفظ الاستجابة المرفوضة مع دليل تدقيق دون تسليم الملف.",
        "artifacts": [{"path": "pack.html", "media_type": "text/html", "content": html}],
    }
    client = fake_client(raw)
    result = adapter.execute(
        generation_payload(
            artifact_type="pdf",
            instructional_scope="substantial",
            file_capability="executable_temp",
            rendering_capability="executable_temp",
        ),
        "response",
        "gpt-5.6-sol",
        2048,
        "none",
        0.0,
        adapter.API_KEY_ENV,
        client,
        4096,
    )
    assert result["evaluation_error"]["kind"] == "artifact-validation"
    assert "missing main landmark" in result["evaluation_error"]["message"]
    assert "direction CSS" not in result["evaluation_error"]["message"]
    assert result["artifact_evidence"] == []
    assert result["raw_result"] == raw
    assert result["model"] == "openai/gpt-5.6-sol"
    assert result["usage"]["total_tokens"] == 150
    assert result["api"]["request_id"] == "req_test"
    assert set(result["timing"]) == {"started_at", "completed_at", "duration_seconds"}
    assert result["settings"]["max_output_tokens"] == 4096
    rejected = result["invalid_artifact_evidence"]
    assert len(rejected) == 1 and rejected[0]["accepted"] is False
    assert rejected[0]["path"] == "pack.html"
    assert rejected[0]["sha256"] == hashlib.sha256(html.encode()).hexdigest()
    assert rejected[0]["bytes"] == len(html.encode())


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
    test_long_artifact_budget_and_incomplete_evidence()
    test_completed_malformed_output_preserves_usage()
    test_output_budget_routing()
    test_invalid_artifact_evidence()
    test_grader_schema_and_normalization()
    test_secret_boundaries_and_release_identity()
    print("Teach Me OpenAI API adapter mocked tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
