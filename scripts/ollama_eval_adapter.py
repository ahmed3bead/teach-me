#!/usr/bin/env python3
"""Run Teach Me evaluation roles against a local Ollama model.

The adapter reads one runner payload from stdin and writes one JSON object to
stdout. It intentionally accepts only loopback Ollama endpoints unless the
caller explicitly opts into a remote host.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib import error, parse, request


LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
ARABIC_TEXT = re.compile(r"[\u0600-\u06ff]")


def normalize_host(value: str) -> str:
    value = value.rstrip("/")
    if "://" not in value:
        value = "http://" + value
    parsed = parse.urlparse(value)
    if not parsed.hostname:
        raise ValueError("invalid Ollama host")
    return value


def require_local_host(host: str, allow_remote: bool) -> None:
    hostname = parse.urlparse(host).hostname
    if not allow_remote and hostname not in LOCAL_HOSTS:
        raise ValueError(
            "refusing a non-local Ollama endpoint; pass --allow-remote only when cost and privacy are understood"
        )


def load_skill_context(skill_root: Path) -> str:
    skill_file = skill_root / "SKILL.md"
    if not skill_file.is_file():
        raise ValueError(f"SKILL.md not found under {skill_root}")
    files = [skill_file, *sorted((skill_root / "references").glob("*.md"))]
    chunks = []
    for path in files:
        relative = path.relative_to(skill_root)
        chunks.append(f"\n--- {relative} ---\n{path.read_text(encoding='utf-8')}")
    return "".join(chunks)


def requested_locale(payload: dict[str, Any]) -> str:
    """Return the explicit locale or infer a safe default from learner text."""
    locale = payload.get("locale")
    if isinstance(locale, str) and locale.strip():
        return locale.strip()

    text_parts = [payload.get("prompt"), payload.get("learner_message")]
    text_parts.extend(
        item.get("content")
        for item in payload.get("history", [])
        if isinstance(item, dict)
    )
    combined = " ".join(part for part in text_parts if isinstance(part, str))
    return "ar" if ARABIC_TEXT.search(combined) else "en"


def locale_instruction(locale: str) -> str:
    normalized = locale.lower().replace("_", "-")
    if normalized == "ar-eg":
        return (
            "Respond in natural Egyptian Arabic. Keep English technical terms only when useful, "
            "and explain each new term in Arabic on first use. Do not switch the explanation to English."
        )
    if normalized in {"ar-msa", "ar-sa"}:
        return (
            "Respond in clear Modern Standard Arabic. Keep English technical terms only when useful, "
            "and explain each new term in Arabic on first use. Do not switch the explanation to English."
        )
    if normalized.startswith("ar"):
        return (
            "Respond in Arabic and match the learner's dialect or register from their latest message. "
            "Keep English technical terms only when useful, explain them in Arabic, and do not switch the explanation to English."
        )
    if normalized.startswith("en"):
        return "Respond in English and match the learner's level and register."
    return f"Respond in the requested locale {locale} and match the learner's register."


def text_schema(field: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {field: {"type": "string", "minLength": 1}},
        "required": [field],
        "additionalProperties": False,
    }


def grade_schema(count: int, simulation: bool = False) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "results": {
            "type": "array",
            "minItems": count,
            "maxItems": count,
            "items": {
                "type": "object",
                "properties": {
                    "passed": {"type": "boolean"},
                    "reason": {"type": "string"},
                },
                "required": ["passed", "reason"],
                "additionalProperties": False,
            },
        }
    }
    required = ["results"]
    if simulation:
        properties.update(
            {
                "baseline_score": {"type": "number", "minimum": 0, "maximum": 1},
                "transfer_score": {"type": "number", "minimum": 0, "maximum": 1},
            }
        )
        required = ["baseline_score", "transfer_score", "results"]
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def role_for_payload(payload_type: str) -> str:
    if payload_type == "generate":
        return "response"
    if payload_type == "teach":
        return "teacher"
    if payload_type in {"baseline", "dialogue", "transfer"}:
        return "learner"
    if payload_type in {"grade", "simulation-grade"}:
        return "grader"
    raise ValueError(f"unsupported payload type: {payload_type}")


def messages_and_schema(payload: dict[str, Any], skill_context: str | None) -> tuple[list[dict[str, str]], dict[str, Any], float]:
    kind = payload["type"]
    if kind == "generate":
        language_rule = locale_instruction(requested_locale(payload))
        system = (
            "You are the Teach Me teaching agent. Follow the supplied skill contract exactly, "
            "act directly as the teacher, and do not mention evaluation machinery.\n"
            f"Required language rule: {language_rule}\n\n"
            + (skill_context or "")
        )
        messages = [{"role": "system", "content": system}]
        messages.extend(payload.get("history", []))
        messages.append({"role": "user", "content": str(payload["prompt"])})
        return messages, text_schema("response"), 0.2

    if kind == "teach":
        language_rule = locale_instruction(requested_locale(payload))
        system = (
            "You are the Teach Me teaching agent in a closed-book simulation. Follow the skill, "
            "teach naturally in the requested locale, and never discuss the test harness.\n"
            f"Required language rule: {language_rule}\n\n"
            + (skill_context or "")
        )
        history = payload.get("history", [])
        content = {
            "locale": payload.get("locale"),
            "authorized_teaching_material": payload.get("teaching_material"),
            "dialogue_so_far": history,
            "current_learner_message": payload.get("learner_message"),
            "turn": payload.get("turn_index"),
            "maximum_turns": payload.get("max_turns"),
        }
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(content, ensure_ascii=False)},
        ], text_schema("response"), 0.2

    if kind in {"baseline", "dialogue", "transfer"}:
        system = (
            "Act only as the described learner. Never use hidden or outside knowledge. "
            "Admit uncertainty naturally and follow the learner behaviors without quoting them.\n"
            f"Persona: {payload.get('learner_persona', '')}\n"
            f"Behaviors: {json.dumps(payload.get('learner_behaviors', []), ensure_ascii=False)}"
        )
        if kind == "baseline":
            user = f"Instruction: {payload.get('instruction', '')}\nTask: {payload.get('task', '')}"
            return [{"role": "system", "content": system}, {"role": "user", "content": user}], text_schema("answer"), 0.2
        if kind == "transfer":
            user = json.dumps(
                {
                    "instruction": payload.get("instruction"),
                    "teaching_transcript": payload.get("history", []),
                    "fresh_task": payload.get("task"),
                },
                ensure_ascii=False,
            )
            return [{"role": "system", "content": system}, {"role": "user", "content": user}], text_schema("answer"), 0.2
        schema = text_schema("message")
        schema["properties"]["done"] = {"type": "boolean"}
        schema["required"].append("done")
        user = json.dumps(
            {
                "instruction": payload.get("instruction"),
                "dialogue": payload.get("history", []),
                "turn": payload.get("turn_index"),
                "maximum_turns": payload.get("max_turns"),
                "task": "Write the learner's next natural message. Set done=true only at a natural endpoint.",
            },
            ensure_ascii=False,
        )
        return [{"role": "system", "content": system}, {"role": "user", "content": user}], schema, 0.2

    expected = payload.get("expected", [])
    simulation = kind == "simulation-grade"
    system = (
        "You are an independent strict evaluator. Judge only observable evidence in the supplied response or transcript. "
        "Do not infer missing behavior. Return results in exactly the same order as the criteria."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ], grade_schema(len(expected), simulation=simulation), 0.0


def ollama_chat(host: str, model: str, messages: list[dict[str, str]], schema: dict[str, Any], temperature: float, timeout: int, num_ctx: int) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": model,
            "messages": messages,
            "stream": False,
            "format": schema,
            "keep_alive": "10m",
            "options": {"temperature": temperature, "num_ctx": num_ctx},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(
        host + "/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError(f"cannot reach Ollama at {host}: {exc.reason}") from exc
    content = result.get("message", {}).get("content")
    if not isinstance(content, str):
        raise RuntimeError("Ollama returned no message content")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Ollama did not return valid structured JSON") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("Ollama structured output must be an object")
    parsed["model"] = "ollama/" + str(result.get("model") or model)
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=["response", "teacher", "learner", "grader"], required=True)
    parser.add_argument("--model", default=os.environ.get("OLLAMA_MODEL", "qwen3:8b"))
    parser.add_argument("--host", default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--num-ctx", type=int, default=32768)
    args = parser.parse_args()

    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, dict) or not isinstance(payload.get("type"), str):
            raise ValueError("stdin must be a runner payload object with a type")
        expected_role = role_for_payload(payload["type"])
        if args.role != expected_role:
            raise ValueError(f"payload type {payload['type']} requires --role {expected_role}")
        host = normalize_host(args.host)
        require_local_host(host, args.allow_remote)
        skill_context = None
        if args.role in {"response", "teacher"}:
            skill_context = load_skill_context(Path(payload["skill_root"]))
        messages, schema, temperature = messages_and_schema(payload, skill_context)
        result = ollama_chat(host, args.model, messages, schema, temperature, args.timeout, args.num_ctx)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (KeyError, OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"Ollama adapter failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
