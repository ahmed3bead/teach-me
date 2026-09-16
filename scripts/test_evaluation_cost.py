#!/usr/bin/env python3
"""Regression tests for paid behavioral-evaluation cost accounting."""

from __future__ import annotations

import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_behavioral_evals as runner
from evaluation_cost import (
    cost_accounting_snapshot,
    derive_cost_plan,
    invocation_reservation,
    load_cost_policy,
    price_usage,
    reconcile_usage,
)


POLICY = ROOT / "evals" / "pricing" / "openai-gpt-5.6-sol-standard.json"
RESPONSE_COMMAND = (
    "python3 scripts/openai_api_eval_adapter.py --role response --model gpt-5.6-sol "
    "--api-key-env OPENAI_API_KEY --max-output-tokens 2048 "
    "--long-artifact-max-output-tokens 4096 --reasoning-effort none "
    "--temperature 0 --timeout 600"
)
GRADER_COMMAND = (
    "python3 scripts/openai_api_eval_adapter.py --role grader --model gpt-5.6-sol "
    "--api-key-env OPENAI_API_KEY --max-output-tokens 2048 "
    "--reasoning-effort none --temperature 0 --timeout 600"
)


def current_plan() -> dict:
    paths = sorted((ROOT / "evals").glob("*.yaml")) + sorted(
        (ROOT / "domain-packs").glob("*/evals.yaml")
    )
    suites = runner.load_suites(paths, None)
    policy = load_cost_policy(POLICY, ROOT)
    return derive_cost_plan(
        policy,
        suites,
        RESPONSE_COMMAND,
        GRADER_COMMAND,
        0,
        "openai/gpt-5.6-sol",
        "openai/gpt-5.6-sol",
    )


def test_independent_token_prices_without_double_counting() -> None:
    usage = {
        "input_tokens": 100,
        "cached_input_tokens": 20,
        "cache_write_tokens": 30,
        "output_tokens": 10,
        "reasoning_tokens": 4,
        "total_tokens": 110,
    }
    reconciled = reconcile_usage(usage)
    assert reconciled["uncached_input_tokens"] == 50
    priced = price_usage(
        usage,
        {"uncached_input": 4, "cached_input": 0.4, "cache_write": 5, "output": 20},
    )
    assert priced["components"] == {
        "uncached_input_usd": 0.0002,
        "cached_input_usd": 0.000008,
        "cache_write_usd": 0.00015,
        "output_usd": 0.0002,
    }
    assert priced["total_usd"] == 0.000558
    bad = dict(usage, cached_input_tokens=80, cache_write_tokens=30)
    try:
        reconcile_usage(bad)
    except ValueError as exc:
        assert "exceed aggregate input" in str(exc)
    else:
        raise AssertionError("overlapping input categories were double-counted")


def test_exact_current_release_ceiling_and_authorization() -> None:
    plan = current_plan()
    assert plan["request_ceiling"] == {
        "response_requests": 95,
        "grader_requests": 90,
        "long_artifact_response_requests": 19,
        "response_max_output_tokens": 2048,
        "long_artifact_response_max_output_tokens": 4096,
        "grader_max_output_tokens": 2048,
        "protocol_retries": 0,
        "aggregate_output_tokens": 417792,
    }
    assert plan["token_ceiling"]["aggregate_input_tokens"] == 1910427
    assert plan["token_ceiling"]["maximum_planned_input_tokens_per_request"] == 200000
    assert plan["high_context_pricing"]["threshold_input_tokens"] == 272000
    assert plan["conservative_cost"] == {
        "worst_case_input_category": "cache_write",
        "input_usd": 9.552135,
        "output_usd": 8.35584,
        "total_usd": 17.907975,
    }
    try:
        runner.validate_cost_authorization(16.0, 17.907975, 17.907975, True)
    except runner.GlobalIntegrityError as exc:
        assert "exceeds authorized" in str(exc)
    else:
        raise AssertionError("a $16 authorization incorrectly passed preflight")
    runner.validate_cost_authorization(17.907975, 17.907975, 17.907975, True)
    for declared in (15.997548, 17.91):
        try:
            runner.validate_cost_authorization(20.0, declared, 17.907975, True)
        except runner.GlobalIntegrityError as exc:
            assert "does not match" in str(exc)
        else:
            raise AssertionError("an inconsistent declared ceiling passed preflight")


def test_interrupted_and_partial_report_cost_integrity() -> None:
    plan = current_plan()
    known_usage = {
        "input_tokens": 100168,
        "cached_input_tokens": 0,
        "cache_write_tokens": 92491,
        "output_tokens": 6072,
        "reasoning_tokens": 0,
        "total_tokens": 106240,
    }
    reservation = invocation_reservation(plan, "response", 2048)
    assert reservation["high_context_pricing_applied"] is True
    assert reservation["maximum_cost_usd"] == 9.28144
    invocations = [
        {
            "role": "response",
            "credential_env": "OPENAI_API_KEY",
            "status": "completed",
            "usage": known_usage,
        },
        {
            "role": "response",
            "credential_env": "OPENAI_API_KEY",
            "status": "transport-error",
            "cost_reservation": reservation,
        },
    ]
    snapshot = cost_accounting_snapshot(invocations, plan)
    assert snapshot["known_usage_records"] == 1
    assert snapshot["known_usage"]["uncached_input_tokens"] == 7677
    assert snapshot["known_cost_usd"] == 0.614603
    assert len(snapshot["unresolved_invocations"]) == 1
    assert snapshot["unresolved_maximum_cost_usd"] == reservation["maximum_cost_usd"]
    assert snapshot["known_cost_usd"] < snapshot["current_upper_bound_cost_usd"]
    assert snapshot["current_upper_bound_cost_usd"] <= 17.907975

    active = cost_accounting_snapshot(invocations[:1], plan, reservation)
    assert active["unresolved_invocations"][0]["status"] == "interrupted-in-flight"
    assert active["current_upper_bound_cost_usd"] == snapshot["current_upper_bound_cost_usd"]
    try:
        cost_accounting_snapshot(
            [{"credential_env": "OPENAI_API_KEY", "status": "malformed-protocol"}],
            plan,
        )
    except ValueError as exc:
        assert "lacks a maximum-cost reservation" in str(exc)
    else:
        raise AssertionError("unbounded credentialed usage passed partial-report accounting")
    assert "OPENAI_API_KEY" not in json.dumps(snapshot)


def test_pricing_policy_fails_closed_when_stale_or_incomplete() -> None:
    raw = json.loads(POLICY.read_text(encoding="utf-8"))
    for mutation in (
        lambda item: item["prices_usd_per_million_tokens"].pop("cache_write"),
        lambda item: item["cost_sensitive_source_sha256"].update({"SKILL.md": "0" * 64}),
        lambda item: item.update(pricing_source="https://example.com/pricing"),
    ):
        candidate = copy.deepcopy(raw)
        mutation(candidate)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pricing.json"
            path.write_text(json.dumps(candidate), encoding="utf-8")
            try:
                load_cost_policy(path, ROOT)
            except ValueError:
                pass
            else:
                raise AssertionError("invalid or stale pricing information passed preflight")


def main() -> int:
    test_independent_token_prices_without_double_counting()
    test_exact_current_release_ceiling_and_authorization()
    test_interrupted_and_partial_report_cost_integrity()
    test_pricing_policy_fails_closed_when_stale_or_incomplete()
    print("Teach Me evaluation cost-accounting tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
