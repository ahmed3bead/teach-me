#!/usr/bin/env python3
"""Validate behavioral cases and build immutable, capability-safe prompt packets."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "fixtures" / "eval-registry.yaml"
CANONICAL_LOCALES = frozenset({"ar-MSA", "en"})
CAPABILITIES = ("source", "web", "file", "rendering", "sandbox", "video", "external_catalog")
CAPABILITY_STATES = frozenset({"unavailable", "not_required", "supplied_result", "executable_temp"})
ROUTING_AXES = (
    "audience", "mode", "source_type", "artifact_type", "session_state",
    "accessibility", "safety_level", "instructional_scope", "assessment_state", "domain_pack",
)
SECRET_KEY = re.compile(r"(?:password|passwd|api[_-]?key|access[_-]?token|private[_-]?key|client[_-]?secret)", re.I)
SECRET_VALUE = re.compile(r"(?:AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")
DANGEROUS_COMMAND = re.compile(r"(?:\brm\s+-rf\b|\bdelete\s+--all\b|\bformat\s+[A-Za-z]:|\bdrop\s+(?:database|table)\b)", re.I)
BEHAVIORAL_DIRECTIVE = re.compile(
    r"(?:inferred additions? must|must remain labeled|the response (?:must|should)|the assistant (?:must|should)|"
    r"ask the (?:learner|educator)|produce (?:a|an|the) (?:lesson|rubric|curriculum)|"
    r"يجب على الرد|على المساعد|اسأل المتعلم|قدم خطة درس)", re.I,
)


def canonical_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def safe_relative_path(value: str) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and not any(part in {"", ".", ".."} for part in value.split("/")) and not value.startswith("~")


def _require_choice(value: Any, choices: set[str] | frozenset[str], field: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"{field} must be one of: {', '.join(sorted(choices))}")
    return value


def _walk_strings(value: Any, path: str = "result") -> list[tuple[str, str]]:
    if isinstance(value, str): return [(path, value)]
    if isinstance(value, list): return [item for index, child in enumerate(value) for item in _walk_strings(child, f"{path}[{index}]")]
    if isinstance(value, dict): return [item for key, child in value.items() for item in _walk_strings(child, f"{path}.{key}")]
    return []


def _walk_mapping_items(value: Any, path: str = "result") -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        return [(f"{path}.{key}", child) for key, child in value.items()] + [item for key, child in value.items() for item in _walk_mapping_items(child, f"{path}.{key}")]
    if isinstance(value, list): return [item for index, child in enumerate(value) for item in _walk_mapping_items(child, f"{path}[{index}]")]
    return []


def validate_registry_entry(entry: Any) -> None:
    required = {"id", "capability", "state", "authorized", "provenance", "captured_at", "content_sha256", "simulated", "result"}
    if not isinstance(entry, dict) or set(entry) != required:
        raise ValueError(f"registry fixture keys must be exactly: {', '.join(sorted(required))}")
    if not isinstance(entry.get("id"), str) or not re.fullmatch(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", entry["id"]):
        raise ValueError("fixture id must be stable lowercase ASCII")
    _require_choice(entry["capability"], set(CAPABILITIES) | {"context"}, "fixture.capability")
    _require_choice(entry["state"], {"supplied_result", "executable_temp"}, "fixture.state")
    if entry["capability"] == "context" and entry["state"] != "supplied_result": raise ValueError("context fixtures must be supplied_result")
    if entry["capability"] in {"source", "web", "video", "sandbox", "external_catalog"} and entry["state"] != "supplied_result":
        raise ValueError(f"{entry['capability']} fixtures must be supplied_result")
    if entry["capability"] in {"file", "rendering"} and entry["state"] != "executable_temp":
        raise ValueError(f"{entry['capability']} fixtures must be executable_temp")
    if entry["authorized"] is not True or entry["simulated"] is not True: raise ValueError("fixtures must be authorized simulated evaluation input")
    if not isinstance(entry["provenance"], str) or not entry["provenance"].strip(): raise ValueError("fixture provenance is required")
    if not isinstance(entry["captured_at"], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", entry["captured_at"]):
        raise ValueError("fixture captured_at must be an explicit UTC timestamp")
    if entry["content_sha256"] != canonical_hash(entry["result"]): raise ValueError(f"fixture {entry['id']} content hash mismatch")
    result = entry["result"]
    if not isinstance(result, dict) or not result: raise ValueError("fixture result must be a non-empty object")
    expected_result_type = {"file": "artifact_workspace", "rendering": "local_renderer"}.get(entry["capability"], f"simulated_{entry['capability']}")
    if result.get("tool_result_type") != expected_result_type: raise ValueError(f"fixture {entry['id']} result type mismatch")
    expected_result_keys = {
        "file": {"tool_result_type", "workspace", "artifact_protocol", "overwrite", "symlinks", "tool_network"},
        "rendering": {"tool_result_type", "engine", "input_capability", "source_media_type", "output_media_type", "tool_network"},
    }.get(entry["capability"], {"tool_result_type", "data"})
    if set(result) != expected_result_keys: raise ValueError(f"fixture {entry['id']} has unknown or missing result keys")
    if "data" in result and not isinstance(result["data"], dict): raise ValueError("supplied result data must be an object")
    for key, value in _walk_mapping_items(result):
        if SECRET_KEY.search(key.rsplit(".", 1)[-1]) and value not in (False, None, "none", "absent"):
            raise ValueError(f"fixture {entry['id']} contains a credential-like field")
    for field, text in _walk_strings(result):
        if SECRET_VALUE.search(text): raise ValueError(f"fixture {entry['id']} contains a real-credential pattern")
        if BEHAVIORAL_DIRECTIVE.search(text): raise ValueError(f"fixture {entry['id']} contains criterion-like behavioral instructions")
        if DANGEROUS_COMMAND.search(text) and not (entry["capability"] == "video" and result.get("data", {}).get("contains_unsafe_observation") is True):
            raise ValueError(f"fixture {entry['id']} contains an unsafe executable command in ordinary content")
        if field.endswith(("path", "root", "output")) and not safe_relative_path(text): raise ValueError(f"fixture {entry['id']} contains unsafe path {text!r}")
    policy = result if entry["capability"] in {"file", "rendering"} else result.get("data", {})
    if entry["capability"] in {"file", "rendering", "sandbox"} and policy.get("tool_network") != "disabled":
        raise ValueError(f"fixture {entry['id']} must disable agent tool network")
    if entry["capability"] == "file" and policy.get("workspace") != "disposable_temp": raise ValueError("file fixture must use disposable_temp")
    if entry["capability"] == "rendering" and policy.get("input_capability") != "file": raise ValueError("rendering fixture must consume file artifacts")


def load_fixture_registry(path: Path = REGISTRY_PATH) -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != "1.0.0" or not isinstance(data.get("fixtures"), list):
        raise ValueError("fixture registry must contain version 1.0.0 and a fixtures array")
    registry: dict[str, dict[str, Any]] = {}
    for entry in data["fixtures"]:
        validate_registry_entry(entry)
        if entry["id"] in registry: raise ValueError(f"duplicate fixture id: {entry['id']}")
        registry[entry["id"]] = entry
    return registry


def resolve_case_fixtures(case: dict[str, Any], registry: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    registry = registry or load_fixture_registry()
    refs = case.get("fixture_refs", {})
    if not isinstance(refs, dict) or not set(refs) <= set(CAPABILITIES) | {"context"}: raise ValueError("fixture_refs contains unknown capability keys")
    resolved: dict[str, Any] = {}
    for capability, state in case["capabilities"].items():
        fixture_id = refs.get(capability)
        required = state in {"supplied_result", "executable_temp"}
        if required != (fixture_id is not None): raise ValueError(f"capabilities.{capability}={state} fixture reference mismatch")
        if fixture_id is None: continue
        entry = registry.get(fixture_id)
        if not entry: raise ValueError(f"unknown fixture id: {fixture_id}")
        if entry["capability"] != capability or entry["state"] != state: raise ValueError(f"fixture {fixture_id} type/state mismatch")
        resolved[capability] = entry
    if "context" in refs:
        entry = registry.get(refs["context"])
        if not entry or entry["capability"] != "context": raise ValueError(f"invalid context fixture id: {refs['context']}")
        resolved["context"] = entry
    return resolved


def validate_case_contract(case: dict[str, Any], registry: dict[str, dict[str, Any]] | None = None) -> None:
    _require_choice(case.get("locale"), CANONICAL_LOCALES, "locale")
    manifest = case.get("capabilities")
    if not isinstance(manifest, dict) or set(manifest) != set(CAPABILITIES): raise ValueError(f"capabilities must declare exactly: {', '.join(CAPABILITIES)}")
    for name in CAPABILITIES: _require_choice(manifest[name], CAPABILITY_STATES, f"capabilities.{name}")
    if manifest["rendering"] == "executable_temp" and manifest["file"] != "executable_temp": raise ValueError("rendering executable_temp requires file executable_temp")
    case_text = case.get("prompt", "") + " " + " ".join(turn.get("content", "") for turn in case.get("turns", []))
    if re.search(r"(?:ignore|override|escalate|change).{0,30}(?:capabilit|fixture|tool access)|(?:تجاهل|غيّر|تجاوز).{0,30}(?:الصلاحيات|القدرات)", case_text, re.I):
        raise ValueError("case text attempts to alter evaluator capabilities")
    routing = case.get("routing")
    if not isinstance(routing, dict) or set(routing) != set(ROUTING_AXES): raise ValueError(f"routing must declare exactly: {', '.join(ROUTING_AXES)}")
    _require_choice(routing["audience"], {"learner", "educator"}, "routing.audience")
    _require_choice(routing["mode"], {"topic-led", "source-grounded"}, "routing.mode")
    _require_choice(routing["source_type"], {"none", "book", "document", "video", "playlist", "course", "curriculum", "website"}, "routing.source_type")
    _require_choice(routing["artifact_type"], {"chat", "markdown", "html", "pdf", "curriculum", "learning-pack"}, "routing.artifact_type")
    _require_choice(routing["session_state"], {"new", "resume", "multi-turn"}, "routing.session_state")
    _require_choice(routing["accessibility"], {"standard", "child", "screen-reader", "audio", "blocked"}, "routing.accessibility")
    _require_choice(routing["safety_level"], {"standard", "sensitive", "high-stakes"}, "routing.safety_level")
    _require_choice(routing["instructional_scope"], {"brief", "substantial", "journey"}, "routing.instructional_scope")
    _require_choice(routing["assessment_state"], {"none", "offered", "accepted", "declined", "intensive"}, "routing.assessment_state")
    _require_choice(routing["domain_pack"], {"none", "photography", "programming"}, "routing.domain_pack")
    resolve_case_fixtures(case, registry)


def reference_paths(case: dict[str, Any]) -> list[Path]:
    validate_case_contract(case)
    r, c = case["routing"], case["capabilities"]
    names = ["teaching-contract.md"]
    if r["audience"] == "educator": names.append("educator-mode.md")
    if r["mode"] == "source-grounded": names.extend(["source-grounded-mode.md", "evidence-policy.md"])
    if r["source_type"] in {"video", "playlist"} or c["video"] != "not_required": names.append("multimodal-video.md")
    if c["web"] != "not_required" or r["source_type"] in {"book", "course", "website"}: names.extend(["research-sweep.md", "evidence-policy.md"])
    if case["locale"] == "ar-MSA": names.append("arabic-teaching-style.md")
    if r["artifact_type"] in {"curriculum", "markdown", "html", "pdf", "learning-pack"}: names.extend(["curriculum-delivery.md", "learning-pack-structure.md"])
    if r["artifact_type"] in {"html", "pdf"}: names.append("bidirectional-output.md")
    if r["session_state"] in {"resume", "multi-turn"}: names.extend(["integration-core.md", "learner-model.md"])
    if any(c[name] != "not_required" for name in ("file", "rendering", "sandbox", "external_catalog")): names.append("integration-foundation.md")
    if r["instructional_scope"] == "journey" or r["artifact_type"] == "learning-pack": names.append("guided-learning-pack.md")
    if r["session_state"] != "new" or r["instructional_scope"] == "journey": names.append("retention-adaptation.md")
    if r["accessibility"] != "standard": names.append("accessibility-engagement.md")
    if r["accessibility"] == "child" or r["safety_level"] != "standard": names.append("safety-privacy.md")
    if r["audience"] == "learner" and r["session_state"] == "new": names.append("diagnostic-engine.md")
    if r["audience"] == "learner": names.append("teaching-engine.md")
    if r["audience"] == "learner" and (r["instructional_scope"] in {"substantial", "journey"} or r["session_state"] == "multi-turn"):
        names.append("conversational-teaching.md")
    if r["assessment_state"] != "none" or r["session_state"] == "multi-turn": names.append("assessment-feedback-engine.md")
    paths = [ROOT / "SKILL.md", *(ROOT / "references" / name for name in names)]
    if r["domain_pack"] != "none": paths.append(ROOT / "domain-packs" / r["domain_pack"] / "PACK.md")
    unique: list[Path] = []
    for path in paths:
        if path.resolve() not in {item.resolve() for item in unique}: unique.append(path)
    return unique


def instruction_manifest(case: dict[str, Any]) -> list[dict[str, Any]]:
    manifest = []
    for path in reference_paths(case):
        content = path.read_text(encoding="utf-8")
        manifest.append({"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(content.encode()).hexdigest(), "content": content})
    return manifest


def immutable_prompt_packet(suite: str, case: dict[str, Any]) -> dict[str, Any]:
    validate_case_contract(case)
    packet = {"packet_version": "1.1.0", "suite": suite, "case_id": case["id"], "locale": case["locale"], "routing": case["routing"], "capabilities": case["capabilities"], "controlled_inputs": resolve_case_fixtures(case), "instruction_sources": instruction_manifest(case)}
    packet["sha256"] = canonical_hash(packet)
    return packet
