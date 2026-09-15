#!/usr/bin/env python3
"""Official OpenAI Responses API adapter for isolated behavioral evaluation roles."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import openai
from openai import OpenAI

from codex_subscription_eval_adapter import materialize_artifacts, output_schema, render_prompt

DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_MAX_OUTPUT_TOKENS = 2048
DEFAULT_LONG_ARTIFACT_MAX_OUTPUT_TOKENS = 4096
LONG_ARTIFACT_TYPES = frozenset({"curriculum", "learning-pack"})
ADAPTER_VERSION = "1.1.0"
API_KEY_ENV = "OPENAI_API_KEY"


def provider_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Convert protocol JSON Schema to the API's strict required-or-null form."""
    result = copy.deepcopy(schema)

    def visit(node: Any) -> None:
        if not isinstance(node, dict):
            return
        if node.get("type") == "object":
            properties = node.get("properties", {})
            required = set(node.get("required", []))
            for name, child in properties.items():
                visit(child)
                if name not in required:
                    properties[name] = {"anyOf": [child, {"type": "null"}]}
            node["required"] = list(properties)
            node["additionalProperties"] = False
        if node.get("type") == "array":
            visit(node.get("items"))
        for choice in node.get("anyOf", []):
            visit(choice)

    visit(result)
    return result


def normalize_protocol_result(raw: dict[str, Any], role: str) -> dict[str, Any]:
    """Remove provider-only nullable evidence fields before runner validation."""
    if not isinstance(raw, dict):
        raise ValueError("structured output must be one JSON object")
    result = copy.deepcopy(raw)
    if role != "grader":
        return result
    items = result.get("results")
    if not isinstance(items, list):
        raise ValueError("grader structured output requires results")
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("evidence"), dict):
            raise ValueError("grader structured output requires evidence objects")
        evidence = item["evidence"]
        source = evidence.get("source")
        normalized = {"source": source, "quote": evidence.get("quote")}
        if source == "response":
            normalized["turn"] = evidence.get("turn")
        elif source == "artifact":
            normalized["artifact_path"] = evidence.get("artifact_path")
        elif source != "absent":
            raise ValueError("grader evidence source is invalid")
        item["evidence"] = normalized
    return result


def usage_record(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        raise RuntimeError("OpenAI response did not include token usage")
    input_details = getattr(usage, "input_tokens_details", None)
    output_details = getattr(usage, "output_tokens_details", None)
    return {
        "input_tokens": int(getattr(usage, "input_tokens", 0) or 0),
        "cached_input_tokens": int(getattr(input_details, "cached_tokens", 0) or 0),
        "cache_write_tokens": int(getattr(input_details, "cache_write_tokens", 0) or 0),
        "output_tokens": int(getattr(usage, "output_tokens", 0) or 0),
        "reasoning_tokens": int(getattr(output_details, "reasoning_tokens", 0) or 0),
        "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
    }


def uses_long_artifact_budget(payload: dict[str, Any]) -> bool:
    """Reserve the larger bound only for file-backed curriculum artifacts."""
    if payload.get("type") != "generate":
        return False
    packet = payload.get("prompt_packet", {})
    routing = packet.get("routing", {}) if isinstance(packet, dict) else {}
    capabilities = packet.get("capabilities", {}) if isinstance(packet, dict) else {}
    return (
        routing.get("artifact_type") in LONG_ARTIFACT_TYPES
        and capabilities.get("file") == "executable_temp"
    )


def effective_output_token_limit(
    payload: dict[str, Any],
    max_output_tokens: int,
    long_artifact_max_output_tokens: int,
) -> int:
    if uses_long_artifact_budget(payload):
        return max(max_output_tokens, long_artifact_max_output_tokens)
    return max_output_tokens


def incomplete_reason(response: Any) -> str:
    details = getattr(response, "incomplete_details", None)
    if isinstance(details, dict):
        reason = details.get("reason")
    else:
        reason = getattr(details, "reason", None)
    return str(reason or "unknown")


def execute(
    payload: dict[str, Any],
    role: str,
    model: str,
    max_output_tokens: int,
    reasoning_effort: str,
    temperature: float,
    api_key_env: str,
    client: Any,
    long_artifact_max_output_tokens: int = DEFAULT_LONG_ARTIFACT_MAX_OUTPUT_TOKENS,
) -> dict[str, Any]:
    prompt = render_prompt(payload, role, model)
    schema = output_schema(payload)
    effective_max_output_tokens = effective_output_token_limit(
        payload, max_output_tokens, long_artifact_max_output_tokens
    )
    started_at = datetime.now(timezone.utc)
    started = time.monotonic()
    response = client.responses.create(
        model=model,
        input=prompt,
        store=False,
        tools=[],
        parallel_tool_calls=False,
        service_tier="default",
        truncation="disabled",
        max_output_tokens=effective_max_output_tokens,
        reasoning={"effort": reasoning_effort},
        temperature=temperature,
        text={
            "format": {
                "type": "json_schema",
                "name": f"teach_me_{role}",
                "strict": True,
                "schema": provider_schema(schema),
            },
            "verbosity": "low",
        },
    )
    completed_at = datetime.now(timezone.utc)
    returned_model = str(getattr(response, "model", ""))
    if not returned_model:
        raise RuntimeError("OpenAI response did not include a model identifier")
    status = str(getattr(response, "status", "missing"))
    common_evidence = {
        "model": f"openai/{returned_model}",
        "settings": {
            "model": model,
            "requested_model": model,
            "reasoning": {"effort": reasoning_effort},
            "temperature": temperature,
            "max_output_tokens": effective_max_output_tokens,
            "configured_max_output_tokens": max_output_tokens,
            "long_artifact_max_output_tokens": long_artifact_max_output_tokens,
            "long_artifact_budget_applied": uses_long_artifact_budget(payload),
            "store": False,
            "tools": [],
            "parallel_tool_calls": False,
            "service_tier": "default",
            "truncation": "disabled",
            "structured_output": {"type": "json_schema", "strict": True},
            "model_transport": "openai-responses-api-standard",
            "external_source_access": "controlled-fixtures-only",
            "sdk": f"openai/{openai.__version__}",
            "sdk_max_retries": 0,
            "api_key_env": api_key_env,
        },
        "adapter_version": ADAPTER_VERSION,
        "invocation_id": str(uuid.uuid4()),
        "timing": {
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": time.monotonic() - started,
        },
        "usage": usage_record(response),
        "effective_prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "api": {
            "response_id": getattr(response, "id", None),
            "request_id": getattr(response, "_request_id", None),
            "service_tier_returned": getattr(response, "service_tier", None),
            "created_at": getattr(response, "created_at", None),
        },
    }
    if status != "completed":
        reason = incomplete_reason(response)
        return {
            **common_evidence,
            "response": "",
            "artifacts": [],
            "artifact_evidence": [],
            "raw_result": {"status": status, "incomplete_details": {"reason": reason}},
            "evaluation_error": {
                "kind": "model-incomplete",
                "status": status,
                "reason": reason,
            },
        }
    raw = json.loads(response.output_text)
    normalized = normalize_protocol_result(raw, role)
    evaluation_error = None
    artifact_records: list[dict[str, Any]] = []
    if role == "response":
        with tempfile.TemporaryDirectory(prefix="teach-me-openai-eval-") as directory:
            try:
                artifact_records = materialize_artifacts(
                    normalized,
                    Path(directory),
                    payload.get("prompt_packet", {}).get("capabilities", {}),
                )
            except (OSError, ValueError) as exc:
                evaluation_error = {"kind": "artifact-validation", "message": str(exc)}

    result = dict(normalized)
    result.update(
        {
            **common_evidence,
            "raw_result": raw,
        }
    )
    if role == "response":
        result["artifact_evidence"] = artifact_records
    if evaluation_error is not None:
        result["evaluation_error"] = evaluation_error
    return result


def require_api_key(environment: dict[str, str], name: str) -> str:
    if name != API_KEY_ENV:
        raise ValueError("only OPENAI_API_KEY is supported")
    value = environment.get(name)
    if not value:
        raise ValueError("OPENAI_API_KEY is missing")
    return value


def redacted_message(error: BaseException, secret: str) -> str:
    message = str(error)
    return message.replace(secret, "[REDACTED]") if secret else message


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=["response", "grader"], required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-key-env", choices=[API_KEY_ENV], required=True)
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument(
        "--long-artifact-max-output-tokens",
        type=int,
        default=DEFAULT_LONG_ARTIFACT_MAX_OUTPUT_TOKENS,
    )
    parser.add_argument("--reasoning-effort", choices=["none"], default="none")
    parser.add_argument("--temperature", type=float, choices=[0.0], default=0.0)
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--check-access", action="store_true")
    args = parser.parse_args()
    if not 256 <= args.max_output_tokens <= 4096:
        parser.error("--max-output-tokens must be between 256 and 4096")
    if not args.max_output_tokens <= args.long_artifact_max_output_tokens <= 8192:
        parser.error("--long-artifact-max-output-tokens must be between --max-output-tokens and 8192")

    secret = ""
    try:
        secret = require_api_key(dict(os.environ), args.api_key_env)
        client = OpenAI(api_key=secret, timeout=args.timeout, max_retries=0)
        if args.check_access:
            model = client.models.retrieve(args.model)
            print(json.dumps({"accessible": True, "requested_model": args.model, "returned_model": model.id, "api_key_env": args.api_key_env}))
            return 0
        payload = json.load(sys.stdin)
        print(
            json.dumps(
                execute(
                    payload,
                    args.role,
                    args.model,
                    args.max_output_tokens,
                    args.reasoning_effort,
                    args.temperature,
                    args.api_key_env,
                    client,
                    args.long_artifact_max_output_tokens,
                ),
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:
        print(f"OpenAI API adapter failed: {redacted_message(exc, secret)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
