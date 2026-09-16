#!/usr/bin/env python3
"""Fail-closed pricing and usage accounting for paid behavioral evaluations."""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import copy
from decimal import Decimal
from pathlib import Path
from typing import Any


USAGE_FIELDS = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_tokens",
    "output_tokens",
    "reasoning_tokens",
    "total_tokens",
)
PRICE_FIELDS = (
    "uncached_input",
    "cached_input",
    "cache_write",
    "output",
)
LONG_ARTIFACT_TYPES = frozenset({"markdown", "html", "pdf", "curriculum", "learning-pack"})
LONG_ARTIFACT_SCOPES = frozenset({"substantial", "journey"})
OFFICIAL_PRICING_PREFIX = "https://developers.openai.com/"
REQUEST_METADATA_TOKEN_ALLOWANCE = 100


def _decimal(value: Any, label: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as exc:
        raise ValueError(f"{label} must be a decimal number") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError(f"{label} must be finite and positive")
    return result


def _usd(tokens: int, rate: Decimal) -> Decimal:
    return Decimal(tokens) * rate / Decimal(1_000_000)


def _number(value: Decimal) -> float:
    return float(value)


def cost_sensitive_paths(root: Path) -> list[Path]:
    """Return every committed input that can change rendered request size."""
    paths = [
        root / "SKILL.md",
        root / "fixtures" / "eval-registry.yaml",
        root / "scripts" / "behavioral_eval_contract.py",
        root / "scripts" / "codex_subscription_eval_adapter.py",
        root / "scripts" / "evaluation_cost.py",
        root / "scripts" / "openai_api_eval_adapter.py",
        root / "scripts" / "run_behavioral_evals.py",
        *sorted((root / "references").glob("*.md")),
        *sorted((root / "evals").glob("*.yaml")),
        *sorted((root / "domain-packs").glob("*/PACK.md")),
        *sorted((root / "domain-packs").glob("*/evals.yaml")),
    ]
    return sorted(set(paths))


def load_cost_policy(path: Path, root: Path) -> dict[str, Any]:
    """Load a source-bound pricing policy and reject stale or incomplete data."""
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"pricing policy cannot be read: {path}") from exc
    if not isinstance(policy, dict) or policy.get("schema_version") != "1.0.0":
        raise ValueError("pricing policy schema_version must be 1.0.0")
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", str(policy.get("model", ""))):
        raise ValueError("pricing policy requires an exact provider/model identifier")
    if policy.get("service_tier") != "default":
        raise ValueError("pricing policy must bind Standard service_tier=default")
    source = policy.get("pricing_source")
    if not isinstance(source, str) or not source.startswith(OFFICIAL_PRICING_PREFIX):
        raise ValueError("pricing policy requires an official OpenAI documentation source")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(policy.get("pricing_verified_at", ""))):
        raise ValueError("pricing policy requires an ISO pricing verification date")

    prices = policy.get("prices_usd_per_million_tokens")
    if not isinstance(prices, dict) or set(prices) != set(PRICE_FIELDS):
        raise ValueError(f"pricing policy must define exactly {list(PRICE_FIELDS)}")
    normalized_prices = {name: _decimal(prices[name], f"price {name}") for name in PRICE_FIELDS}
    high_context = policy.get("high_context_pricing")
    if not isinstance(high_context, dict) or set(high_context) != {
        "threshold_input_tokens", "input_multiplier", "output_multiplier"
    }:
        raise ValueError("pricing policy requires complete high-context pricing")
    if not isinstance(high_context["threshold_input_tokens"], int) or high_context["threshold_input_tokens"] <= 0:
        raise ValueError("high-context threshold must be a positive integer")
    normalized_high_context = {
        "threshold_input_tokens": high_context["threshold_input_tokens"],
        "input_multiplier": _decimal(high_context["input_multiplier"], "high-context input multiplier"),
        "output_multiplier": _decimal(high_context["output_multiplier"], "high-context output multiplier"),
    }

    ceiling = policy.get("token_ceiling")
    required_ceiling = {
        "aggregate_input_tokens",
        "aggregate_output_tokens",
        "maximum_planned_input_tokens_per_request",
        "provider_max_input_tokens_per_request",
        "response_requests",
        "grader_requests",
        "long_artifact_response_requests",
        "response_max_output_tokens",
        "long_artifact_response_max_output_tokens",
        "grader_max_output_tokens",
        "protocol_retries",
    }
    if not isinstance(ceiling, dict) or set(ceiling) != required_ceiling:
        raise ValueError("pricing policy token_ceiling fields are missing or inconsistent")
    if not all(isinstance(ceiling[name], int) and ceiling[name] >= 0 for name in required_ceiling):
        raise ValueError("pricing policy token ceilings must be non-negative integers")
    if ceiling["aggregate_input_tokens"] <= 0 or ceiling["aggregate_output_tokens"] <= 0:
        raise ValueError("aggregate token ceilings must be positive")
    if ceiling["provider_max_input_tokens_per_request"] <= 0:
        raise ValueError("provider per-request input limit must be positive")

    expected_paths = {item.relative_to(root).as_posix() for item in cost_sensitive_paths(root)}
    source_hashes = policy.get("cost_sensitive_source_sha256")
    if not isinstance(source_hashes, dict) or set(source_hashes) != expected_paths:
        raise ValueError("pricing policy cost-sensitive source inventory is stale")
    for relative, expected in source_hashes.items():
        if not re.fullmatch(r"[0-9a-f]{64}", str(expected)):
            raise ValueError(f"invalid source hash for {relative}")
        candidate = (root / relative).resolve()
        if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
            raise ValueError(f"unsafe or missing cost-sensitive source: {relative}")
        normalized = candidate.read_text(encoding="utf-8").replace("\r\n", "\n")
        actual = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        if actual != expected:
            raise ValueError(f"cost-sensitive source changed; recalculate pricing policy: {relative}")

    return {
        **policy,
        "prices_usd_per_million_tokens": normalized_prices,
        "high_context_pricing": normalized_high_context,
        "policy_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "policy_path": str(path.resolve()),
    }


def _option(parts: list[str], name: str) -> str:
    indexes = [index for index, value in enumerate(parts) if value == name]
    if len(indexes) != 1 or indexes[0] + 1 >= len(parts):
        raise ValueError(f"adapter command must contain exactly one {name}")
    return parts[indexes[0] + 1]


def _positive_int_option(parts: list[str], name: str) -> int:
    try:
        value = int(_option(parts, name))
    except ValueError as exc:
        raise ValueError(f"adapter option {name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"adapter option {name} must be positive")
    return value


def uses_long_artifact_budget(case: dict[str, Any]) -> bool:
    routing = case.get("routing", {})
    capabilities = case.get("capabilities", {})
    return (
        routing.get("artifact_type") in LONG_ARTIFACT_TYPES
        and routing.get("instructional_scope") in LONG_ARTIFACT_SCOPES
        and capabilities.get("file") == "executable_temp"
    )


def derive_cost_plan(
    policy: dict[str, Any],
    suites: list[dict[str, Any]],
    response_command: str,
    grader_command: str,
    protocol_retries: int,
    expected_response_model: str,
    expected_grader_model: str,
) -> dict[str, Any]:
    """Verify the committed run configuration and derive its maximum charge."""
    response_parts = shlex.split(response_command)
    grader_parts = shlex.split(grader_command)
    root = Path(policy["policy_path"]).parents[2]
    official_adapter = (root / "scripts" / "openai_api_eval_adapter.py").resolve()
    for role, parts in (("response", response_parts), ("grader", grader_parts)):
        script_arguments = [
            (root / part).resolve() if not Path(part).is_absolute() else Path(part).resolve()
            for part in parts
            if part.endswith(".py")
        ]
        if script_arguments != [official_adapter]:
            raise ValueError(f"{role} command must use only the official OpenAI API adapter")
        if _option(parts, "--api-key-env") != "OPENAI_API_KEY":
            raise ValueError(f"{role} command must pass only OPENAI_API_KEY by environment name")
    model = policy["model"]
    provider_model = model.split("/", 1)[1]
    if expected_response_model != model or expected_grader_model != model:
        raise ValueError("expected release models do not match the pricing policy")
    if _option(response_parts, "--role") != "response" or _option(grader_parts, "--role") != "grader":
        raise ValueError("pricing policy requires the official response and grader roles")
    if _option(response_parts, "--model") != provider_model or _option(grader_parts, "--model") != provider_model:
        raise ValueError("adapter command models do not match the pricing policy")
    for role, parts in (("response", response_parts), ("grader", grader_parts)):
        if _option(parts, "--reasoning-effort") != "none":
            raise ValueError(f"{role} command must use reasoning-effort none for the bounded request plan")
        try:
            temperature = Decimal(_option(parts, "--temperature"))
        except Exception as exc:
            raise ValueError(f"{role} command temperature must be numeric") from exc
        if not temperature.is_finite() or temperature != 0:
            raise ValueError(f"{role} command must use temperature 0 for the bounded request plan")

    response_max = _positive_int_option(response_parts, "--max-output-tokens")
    response_long_max = _positive_int_option(response_parts, "--long-artifact-max-output-tokens")
    grader_max = _positive_int_option(grader_parts, "--max-output-tokens")
    cases = [case for suite in suites for case in suite["cases"]]
    response_requests = sum(len(case.get("turns") or [case.get("prompt")]) for case in cases)
    long_requests = sum(
        len(case.get("turns") or [case.get("prompt")])
        for case in cases
        if uses_long_artifact_budget(case)
    )
    grader_requests = len(cases)
    attempts = protocol_retries + 1
    output_ceiling = attempts * (
        (response_requests - long_requests) * response_max
        + long_requests * response_long_max
        + grader_requests * grader_max
    )

    ceiling = policy["token_ceiling"]
    if ceiling["maximum_planned_input_tokens_per_request"] > policy["high_context_pricing"]["threshold_input_tokens"]:
        raise ValueError("planned request ceiling crosses the high-context threshold; base-rate ceiling is unsafe")
    observed = {
        "response_requests": response_requests,
        "grader_requests": grader_requests,
        "long_artifact_response_requests": long_requests,
        "response_max_output_tokens": response_max,
        "long_artifact_response_max_output_tokens": response_long_max,
        "grader_max_output_tokens": grader_max,
        "protocol_retries": protocol_retries,
        "aggregate_output_tokens": output_ceiling,
    }
    for name, value in observed.items():
        if ceiling[name] != value:
            raise ValueError(f"pricing policy {name}={ceiling[name]} does not match configured {value}")

    prices = policy["prices_usd_per_million_tokens"]
    input_category, input_rate = max(
        ((name, prices[name]) for name in ("uncached_input", "cached_input", "cache_write")),
        key=lambda item: item[1],
    )
    input_cost = _usd(ceiling["aggregate_input_tokens"], input_rate)
    output_cost = _usd(ceiling["aggregate_output_tokens"], prices["output"])
    total_cost = input_cost + output_cost
    return {
        "policy_path": policy["policy_path"],
        "policy_sha256": policy["policy_sha256"],
        "model": model,
        "service_tier": policy["service_tier"],
        "pricing_source": policy["pricing_source"],
        "pricing_verified_at": policy["pricing_verified_at"],
        "prices_usd_per_million_tokens": {name: _number(value) for name, value in prices.items()},
        "high_context_pricing": {
            name: value if isinstance(value, int) else _number(value)
            for name, value in policy["high_context_pricing"].items()
        },
        "request_ceiling": observed,
        "token_ceiling": {
            "aggregate_input_tokens": ceiling["aggregate_input_tokens"],
            "aggregate_output_tokens": ceiling["aggregate_output_tokens"],
            "maximum_planned_input_tokens_per_request": ceiling["maximum_planned_input_tokens_per_request"],
            "provider_max_input_tokens_per_request": ceiling["provider_max_input_tokens_per_request"],
        },
        "conservative_cost": {
            "worst_case_input_category": input_category,
            "input_usd": _number(input_cost),
            "output_usd": _number(output_cost),
            "total_usd": _number(total_cost),
        },
    }


def reconcile_usage(usage: Any) -> dict[str, int]:
    """Partition aggregate input exactly once into cached, write, and uncached tokens."""
    if not isinstance(usage, dict) or set(usage) != set(USAGE_FIELDS):
        raise ValueError("usage must contain the complete token accounting fields")
    if not all(isinstance(usage[name], int) and usage[name] >= 0 for name in USAGE_FIELDS):
        raise ValueError("usage token fields must be non-negative integers")
    if usage["total_tokens"] != usage["input_tokens"] + usage["output_tokens"]:
        raise ValueError("total tokens do not equal input plus output")
    categorized = usage["cached_input_tokens"] + usage["cache_write_tokens"]
    if categorized > usage["input_tokens"]:
        raise ValueError("cached reads plus cache writes exceed aggregate input")
    if usage["reasoning_tokens"] > usage["output_tokens"]:
        raise ValueError("reasoning tokens exceed aggregate output")
    return {
        **usage,
        "uncached_input_tokens": usage["input_tokens"] - categorized,
    }


def price_usage(usage: dict[str, int], prices: dict[str, Any]) -> dict[str, Any]:
    reconciled = reconcile_usage(usage)
    normalized = {name: _decimal(prices[name], f"price {name}") for name in PRICE_FIELDS}
    components = {
        "uncached_input_usd": _usd(reconciled["uncached_input_tokens"], normalized["uncached_input"]),
        "cached_input_usd": _usd(reconciled["cached_input_tokens"], normalized["cached_input"]),
        "cache_write_usd": _usd(reconciled["cache_write_tokens"], normalized["cache_write"]),
        "output_usd": _usd(reconciled["output_tokens"], normalized["output"]),
    }
    return {
        "usage": reconciled,
        "components": {name: _number(value) for name, value in components.items()},
        "total_usd": _number(sum(components.values(), Decimal(0))),
    }


def invocation_usage(record: dict[str, Any]) -> dict[str, int] | None:
    """Read usage from either a live result or its compacted journal form, never both."""
    usage = record.get("usage")
    if not isinstance(usage, dict):
        result = record.get("result")
        usage = result.get("usage") if isinstance(result, dict) else None
    return usage if isinstance(usage, dict) else None


def _provider_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Mirror the official adapter's strict-schema expansion for cost bounding."""
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


def request_input_token_bound(
    payload: dict[str, Any],
    role: str,
    cost_plan: dict[str, Any],
    max_output_tokens: int,
) -> dict[str, Any]:
    """Bound one actual request without falling back to the provider-wide limit."""
    if role not in {"response", "grader"} or payload.get("type") != ("generate" if role == "response" else "grade"):
        raise ValueError("request role and payload type do not match")
    if not isinstance(max_output_tokens, int) or max_output_tokens <= 0:
        raise ValueError("request output-token limit must be a positive integer")
    try:
        from codex_subscription_eval_adapter import output_schema, render_prompt

        provider_model = str(cost_plan["model"]).split("/", 1)[1]
        prompt = render_prompt(payload, role, provider_model)
        schema = _provider_schema(output_schema(payload))
        request_body = {
            "model": provider_model,
            "input": prompt,
            "store": False,
            "tools": [],
            "parallel_tool_calls": False,
            "service_tier": cost_plan["service_tier"],
            "truncation": "disabled",
            "max_output_tokens": max_output_tokens,
            "reasoning": {"effort": "none"},
            "temperature": 0,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": f"teach_me_{role}",
                    "strict": True,
                    "schema": schema,
                },
                "verbosity": "low",
            },
        }
        submitted_bytes = len(
            json.dumps(request_body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise ValueError(f"cannot calculate a safe request-specific input bound: {exc}") from exc
    maximum_input_tokens = submitted_bytes + REQUEST_METADATA_TOKEN_ALLOWANCE
    planned_limit = cost_plan["token_ceiling"]["maximum_planned_input_tokens_per_request"]
    provider_limit = cost_plan["token_ceiling"]["provider_max_input_tokens_per_request"]
    if maximum_input_tokens > planned_limit:
        raise ValueError(
            "request-specific input bound exceeds the committed planned per-request limit; "
            "recalculate the pricing policy"
        )
    if maximum_input_tokens > provider_limit:
        raise ValueError("request-specific input bound exceeds the provider input limit")
    return {
        "method": "utf8-request-byte-upper-bound",
        "submitted_request_bytes": submitted_bytes,
        "metadata_token_allowance": REQUEST_METADATA_TOKEN_ALLOWANCE,
        "maximum_input_tokens": maximum_input_tokens,
    }


def invocation_reservation(
    cost_plan: dict[str, Any],
    role: str,
    payload: dict[str, Any],
    max_output_tokens: int,
) -> dict[str, Any]:
    prices = cost_plan["prices_usd_per_million_tokens"]
    input_bound = request_input_token_bound(payload, role, cost_plan, max_output_tokens)
    input_tokens = input_bound["maximum_input_tokens"]
    input_category, input_rate = max(
        ((name, _decimal(prices[name], f"price {name}")) for name in ("uncached_input", "cached_input", "cache_write")),
        key=lambda item: item[1],
    )
    high_context = cost_plan["high_context_pricing"]
    input_multiplier = Decimal(1)
    output_multiplier = Decimal(1)
    if input_tokens > high_context["threshold_input_tokens"]:
        input_multiplier = _decimal(high_context["input_multiplier"], "high-context input multiplier")
        output_multiplier = _decimal(high_context["output_multiplier"], "high-context output multiplier")
    maximum = (
        _usd(input_tokens, input_rate * input_multiplier)
        + _usd(max_output_tokens, _decimal(prices["output"], "price output") * output_multiplier)
    )
    return {
        "role": role,
        "input_bound": input_bound,
        "maximum_input_tokens": input_tokens,
        "maximum_output_tokens": max_output_tokens,
        "worst_case_input_category": input_category,
        "cache_write_possible": True,
        "high_context_pricing_applied": input_multiplier > 1,
        "maximum_cost_usd": _number(maximum),
        "status": "in-flight",
    }


def cost_accounting_snapshot(
    invocations: list[dict[str, Any]],
    cost_plan: dict[str, Any],
    active_reservation: dict[str, Any] | None = None,
    hard_spend_cap_usd: float | None = None,
) -> dict[str, Any]:
    """Price known usage and bound every credentialed invocation without usage."""
    totals = {name: 0 for name in USAGE_FIELDS}
    records = 0
    unresolved: list[dict[str, Any]] = []
    for index, record in enumerate(invocations):
        usage = invocation_usage(record)
        if usage is not None:
            reconciled = reconcile_usage(usage)
            if record.get("credential_env"):
                reservation = record.get("cost_reservation")
                if not isinstance(reservation, dict):
                    raise ValueError("credentialed invocation with usage lacks its request-specific reservation")
                actual = Decimal(str(price_usage(usage, cost_plan["prices_usd_per_million_tokens"])["total_usd"]))
                maximum = _decimal(reservation.get("maximum_cost_usd"), "reservation maximum cost")
                if actual > maximum:
                    raise ValueError("provider-reported usage exceeds the request-specific reservation")
            records += 1
            for name in USAGE_FIELDS:
                totals[name] += reconciled[name]
            continue
        if record.get("credential_env"):
            reservation = record.get("cost_reservation")
            if not isinstance(reservation, dict):
                raise ValueError("credentialed invocation without usage lacks a maximum-cost reservation")
            unresolved.append({"journal_index": index, **reservation, "status": record.get("status", "unknown")})
    if active_reservation is not None:
        unresolved.append({"journal_index": None, **active_reservation, "status": "interrupted-in-flight"})

    priced = price_usage(totals, cost_plan["prices_usd_per_million_tokens"])
    input_ceiling = cost_plan["token_ceiling"]["aggregate_input_tokens"]
    output_ceiling = cost_plan["token_ceiling"]["aggregate_output_tokens"]
    if totals["input_tokens"] > input_ceiling or totals["output_tokens"] > output_ceiling:
        raise ValueError("observed token usage exceeds the conservative token ceiling")
    unresolved_max = sum(Decimal(str(item["maximum_cost_usd"])) for item in unresolved)
    known_cost = Decimal(str(priced["total_usd"]))
    run_ceiling = Decimal(str(cost_plan["conservative_cost"]["total_usd"]))
    upper_bound = known_cost + unresolved_max
    if upper_bound > run_ceiling:
        raise ValueError("recorded cost plus unresolved reservations exceed the theoretical full-run ceiling")
    hard_cap = _decimal(hard_spend_cap_usd, "hard spend cap") if hard_spend_cap_usd is not None else None
    if hard_cap is not None and upper_bound > hard_cap:
        raise ValueError("recorded cost plus unresolved reservations exceed the hard spend cap")
    remaining = hard_cap - upper_bound if hard_cap is not None else None
    return {
        "known_usage_records": records,
        "known_usage": priced["usage"],
        "known_cost_components_usd": priced["components"],
        "known_cost_usd": priced["total_usd"],
        "recorded_cost_usd": priced["total_usd"],
        "unresolved_invocations": unresolved,
        "unresolved_reservations": unresolved,
        "unresolved_maximum_cost_usd": _number(unresolved_max),
        "unresolved_reservations_usd": _number(unresolved_max),
        "current_upper_bound_cost_usd": _number(upper_bound),
        "conservative_run_ceiling_usd": _number(run_ceiling),
        "theoretical_full_run_ceiling_usd": _number(run_ceiling),
        "hard_spend_cap_usd": _number(hard_cap) if hard_cap is not None else None,
        "remaining_spendable_budget_usd": _number(remaining) if remaining is not None else None,
    }


def hard_spend_cap_decision(
    accounting: dict[str, Any],
    next_reservation: dict[str, Any],
    hard_spend_cap_usd: float,
) -> dict[str, Any]:
    """Apply the pre-dispatch hard-cap inequality using exact decimal arithmetic."""
    hard_cap = _decimal(hard_spend_cap_usd, "hard spend cap")
    recorded = Decimal(str(accounting["recorded_cost_usd"]))
    outstanding = Decimal(str(accounting["unresolved_reservations_usd"]))
    next_maximum = _decimal(next_reservation.get("maximum_cost_usd"), "next-request maximum cost")
    exposure_after_dispatch = recorded + outstanding + next_maximum
    return {
        "recorded_cost_usd": _number(recorded),
        "outstanding_reservations_usd": _number(outstanding),
        "next_request_maximum_usd": _number(next_maximum),
        "exposure_after_dispatch_usd": _number(exposure_after_dispatch),
        "hard_spend_cap_usd": _number(hard_cap),
        "dispatch_permitted": exposure_after_dispatch <= hard_cap,
    }
