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
    hard_spend_cap_decision,
    invocation_reservation,
    load_cost_policy,
    price_usage,
    reconcile_usage,
    request_input_token_bound,
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


def grade_payload(response: str = "A grounded response.") -> dict:
    return {
        "type": "grade",
        "ordered_transcript": [
            {"role": "user", "turn": 1, "content": "Explain."},
            {"role": "assistant", "turn": 1, "content": response},
        ],
        "assessment_events": [],
        "case_context": {},
        "controlled_inputs": {},
        "artifacts": [],
        "raw_final_response": response,
        "criteria": ["observable behavior"],
        "evidence_requirements": "Use exact evidence.",
    }


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
    assert plan["token_ceiling"]["aggregate_input_tokens"] == 2111257
    assert plan["token_ceiling"]["maximum_planned_input_tokens_per_request"] == 200000
    assert plan["high_context_pricing"]["threshold_input_tokens"] == 272000
    assert plan["conservative_cost"] == {
        "worst_case_input_category": "cache_write",
        "input_usd": 10.556285,
        "output_usd": 8.35584,
        "total_usd": 18.912125,
    }
    try:
        runner.validate_cost_authorization(16.0, 18.912125, 18.912125, True)
    except runner.GlobalIntegrityError as exc:
        assert "exceeds authorized" in str(exc)
    else:
        raise AssertionError("a $16 authorization incorrectly passed preflight")
    runner.validate_cost_authorization(18.912125, 18.912125, 18.912125, True)
    for declared in (15.997548, 17.907975):
        try:
            runner.validate_cost_authorization(20.0, declared, 18.912125, True)
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
    reservation = invocation_reservation(plan, "grader", grade_payload("x" * 60000), 2048)
    assert reservation["high_context_pricing_applied"] is False
    assert reservation["maximum_input_tokens"] < 200000
    assert reservation["maximum_input_tokens"] != 922000
    assert reservation["worst_case_input_category"] == "cache_write"
    assert reservation["maximum_cost_usd"] > 0.614603
    invocations = [
        {
            "role": "response",
            "credential_env": "OPENAI_API_KEY",
            "status": "completed",
            "usage": known_usage,
            "cost_reservation": reservation,
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
    assert snapshot["current_upper_bound_cost_usd"] <= 18.912125

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

    try:
        request_input_token_bound(grade_payload("x" * 110000), "grader", plan, 2048)
    except ValueError as exc:
        assert "committed planned per-request limit" in str(exc)
    else:
        raise AssertionError("an unbounded request fell back to the provider-global reservation")


def test_hard_spend_cap_dispatch_and_interruption_integrity() -> None:
    plan = current_plan()
    completed_reservation = {
        "role": "response",
        "maximum_cost_usd": 1.0,
        "status": "reconciled",
    }
    usage = {
        "input_tokens": 190000,
        "cached_input_tokens": 0,
        "cache_write_tokens": 190000,
        "output_tokens": 100,
        "reasoning_tokens": 0,
        "total_tokens": 190100,
    }
    invocations = [
        {
            "role": "response",
            "credential_env": "OPENAI_API_KEY",
            "status": "completed",
            "usage": usage,
            "cost_reservation": completed_reservation,
        }
        for _ in range(7)
    ]
    unresolved = {
        "role": "grader",
        "maximum_input_tokens": 20000,
        "maximum_output_tokens": 2048,
        "maximum_cost_usd": 0.25,
        "status": "unresolved-spent",
    }
    invocations.append(
        {
            "role": "grader",
            "credential_env": "OPENAI_API_KEY",
            "status": "transport-error",
            "cost_reservation": unresolved,
        }
    )
    snapshot = cost_accounting_snapshot(invocations, plan, hard_spend_cap_usd=7.0)
    assert snapshot["theoretical_full_run_ceiling_usd"] == 18.912125
    assert snapshot["hard_spend_cap_usd"] == 7.0
    assert snapshot["recorded_cost_usd"] == 6.664
    assert snapshot["unresolved_reservations_usd"] == 0.25
    assert snapshot["remaining_spendable_budget_usd"] == 0.086

    next_reservation = invocation_reservation(plan, "grader", grade_payload("x" * 15000), 2048)
    decision = hard_spend_cap_decision(snapshot, next_reservation, 7.0)
    assert decision["dispatch_permitted"] is False
    assert decision["exposure_after_dispatch_usd"] > 7.0

    interrupted = cost_accounting_snapshot(invocations[:-1], plan, unresolved, 7.0)
    assert interrupted["unresolved_reservations_usd"] == 0.25
    assert interrupted["remaining_spendable_budget_usd"] == 0.086
    try:
        cost_accounting_snapshot(invocations, plan, {**unresolved, "maximum_cost_usd": 0.1}, 7.0)
    except ValueError as exc:
        assert "exceed the hard spend cap" in str(exc)
    else:
        raise AssertionError("recorded cost plus unresolved reservations exceeded $7.00")

    report = {
        "status": "running",
        "release_evidence": True,
        "run_configuration": {"hard_spend_cap_usd": 7.0},
        "cost_plan": plan,
        "invocations": invocations,
        "active_case": {"case_key": "suite/case", "stage": "grader-invoking"},
    }
    try:
        runner.reserve_invocation_cost(report, "grader", grade_payload("x" * 15000), 2048)
    except runner.HardSpendCapReached as exc:
        runner.finalize_hard_spend_cap_stop(report, exc)
    else:
        raise AssertionError("runner dispatched a request that could exceed the $7.00 cap")
    assert report["status"] == "stopped-hard-spend-cap"
    assert report["release_evidence"] is False
    assert "cost_reservation" not in report["active_case"]
    assert report["cost_accounting"]["remaining_spendable_budget_usd"] == 0.086
    assert report["hard_spend_cap_stop"]["decision"]["dispatch_permitted"] is False
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "partial.json"
        runner.write_report(output, report)
        persisted = json.loads(output.read_text(encoding="utf-8"))
        assert persisted["status"] == "stopped-hard-spend-cap"
        assert persisted["cost_accounting"]["recorded_cost_usd"] == 6.664
        assert persisted["cost_accounting"]["unresolved_reservations_usd"] == 0.25
        assert persisted["cost_accounting"]["remaining_spendable_budget_usd"] == 0.086
        assert "unit-test-secret-canary" not in output.read_text(encoding="utf-8")


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
    test_hard_spend_cap_dispatch_and_interruption_integrity()
    test_pricing_policy_fails_closed_when_stale_or_incomplete()
    print("Teach Me evaluation cost-accounting tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
