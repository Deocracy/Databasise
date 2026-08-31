"""Real metering end to end through the public ``databasise.run_wiring`` seam (Gap 2 / MACH-05,
01-10-PLAN.md). Closes ``01-VERIFICATION.md``'s finding that ``runner/scheduler.py`` stamped
``budget_state``/``realised_budget_share``/``tokens`` as literal constants regardless of what a
node's body actually spent, with ``runner/budget.py``'s ``meter()`` and ``runner/guards.py``'s
``evaluate_guards()`` never wired into the live dispatch path at all.

Every test in this file runs the metered node through ``databasise.run_wiring`` — the public
composer — rather than ``runner.scheduler.run_wiring`` directly (contrast
``tests/runner/test_scheduler.py``, which deliberately bypasses ``parse_wiring``): this is the
seam a real consumer calls, and it is also what exercises ``databasise/__init__.py``'s newly
threaded ``partial``/``degraded``/``stop_reason``/``degradation_reason`` fields.

Task 1 (this file's first section) was written and observed FAILING against the pre-fix tree:
every token assertion failed on the scheduler's hardcoded all-zero ``TokenAccounting``, and every
halt assertion failed because no node ever reported ``budget_state="halted"`` (the scheduler
stamped ``"within_budget"``/``1.0`` unconditionally). Task 2 extends this file with the metering
edge battery (boundary, adjacency, empty, ordering, precision, guard refusal) named in this
plan's ``must_haves.truths``.
"""

from __future__ import annotations

from typing import Any

import pytest

import databasise
from databasise.parts.registry import PartRegistry
from databasise.parts.schema import Part
from databasise.parts_core.fake_llm_caller import FAKE_LLM_CALLER_PART
from databasise.runner.budget import meter, realised_share
from databasise.runner.guards import GuardDeclarationError
from databasise.runner.trace import TokenAccounting

_DETERMINISM_SETTING = "cache-bypassed"
_CONCURRENCY_SETTING = "sequential"
_NODE_ID = "n1"
_PROMPT = "count these words please"  # 4 words -> a small, known prompt_tokens contribution


def _caller_registry() -> PartRegistry:
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(FAKE_LLM_CALLER_PART)
    return registry


def _metered_wiring(
    token_allowance: int,
    *,
    prompt: str = _PROMPT,
    effects: list[str] | None = None,
    guards: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """One wiring: a single ``FAKE_LLM_CALLER_PART`` node carrying ``token_allowance``. ``effects``
    defaults to the Part's own real declaration (``["calls_llm"]``); pass ``effects=[]`` to
    construct the CR-01 under-declared-wiring case, which is still metered for its real spend
    because ``meter()`` is handed the registry's ``Part.effects``, never the wiring's.
    """
    config: dict[str, Any] = {"prompt": prompt, "token_allowance": token_allowance}
    if guards is not None:
        config["guards"] = guards
    return {
        "nodes": {
            _NODE_ID: {
                "component": FAKE_LLM_CALLER_PART.name_at_version,
                "kind": "llm-caller",
                "effects": effects if effects is not None else list(FAKE_LLM_CALLER_PART.effects),
                "config": config,
                "deps": [],
            }
        }
    }


async def _run(wiring: dict[str, Any], store_root, registry: PartRegistry | None = None) -> dict[str, Any]:
    return await databasise.run_wiring(
        wiring,
        store_root=store_root,
        registry=registry if registry is not None else _caller_registry(),
        determinism_setting=_DETERMINISM_SETTING,
        concurrency_setting=_CONCURRENCY_SETTING,
    )


def _trace(record: dict[str, Any], node_id: str = _NODE_ID) -> dict[str, Any]:
    return next(n for n in record["nodes"] if n["node_id"] == node_id)


# --------------------------------------------------------------------------------------------- #
# Task 1: one metered node, one honest run record, through the public seam                        #
# --------------------------------------------------------------------------------------------- #


async def test_metered_node_reports_the_bodys_own_token_accounting_never_the_all_zero_placeholder(
    store_root,
):
    record = await _run(_metered_wiring(1000), store_root)
    trace = _trace(record)

    assert trace["tokens"]["counted_by"] == "fixture-tokenizer@1"
    assert trace["tokens"]["prompt_tokens"] > 0
    assert trace["tokens"]["completion_tokens"] > 0
    assert trace["tokens"]["call_count"] == 1


async def test_metered_node_within_budget_reports_the_exact_fractional_realised_share(store_root):
    record = await _run(_metered_wiring(1000), store_root)
    trace = _trace(record)

    spend = trace["tokens"]["prompt_tokens"] + trace["tokens"]["completion_tokens"]
    assert 0.0 < trace["realised_budget_share"] < 1.0
    assert trace["realised_budget_share"] == spend / 1000
    assert trace["budget_state"] == "within_budget"


async def test_metered_node_over_allowance_halts_and_the_record_is_a_traced_budget_halt_partial_run(
    store_root,
):
    record = await _run(_metered_wiring(5), store_root)
    trace = _trace(record)

    assert trace["budget_state"] == "halted"
    assert record["partial"] is True
    assert record["degraded"] is True
    assert record["stop_reason"] == "budget_halt"
    assert record["degradation_reason"]


async def test_under_declared_wiring_effects_is_still_metered_for_its_real_spend_cr01(store_root):
    """CR-01's trusted-source rule applied to the metering path: a wiring node declaring
    ``effects: []`` (legal under ``parse_wiring``'s subset rule) while its resolved Part declares
    ``calls_llm`` is still metered for its real spend — ``meter()`` reads ``parsed.parts[node_id]
    .effects`` (the registry's own resolved declaration), never ``parsed.nodes[node_id].effects``
    (the wiring's self-declared, unverified field).
    """
    record = await _run(_metered_wiring(5, effects=[]), store_root)
    trace = _trace(record)

    assert trace["budget_state"] == "halted"


async def test_second_identical_run_against_the_same_store_root_stamps_cache_hit_true(store_root):
    wiring = _metered_wiring(1000)

    await _run(wiring, store_root)
    second_record = await _run(wiring, store_root)

    assert _trace(second_record)["cache_hit"] is True


async def test_every_task_1_case_passes_the_frozen_trace_schema(store_root, assert_valid_trace):
    for allowance in (1000, 5):
        record = await _run(_metered_wiring(allowance), store_root)
        assert_valid_trace(record)

    cache_record = await _run(_metered_wiring(1000), store_root)
    assert_valid_trace(cache_record)


# --------------------------------------------------------------------------------------------- #
# Task 2: the metering edge battery — boundary, adjacency, empty, ordering, precision            #
# --------------------------------------------------------------------------------------------- #


async def _spend_for(prompt: str, store_root) -> int:
    """The metered node's real spend for ``prompt``, read from a generous-allowance run's own
    trace rather than hardcoded, so a change to the canned completion does not silently
    invalidate a boundary/adjacency test.
    """
    record = await _run(_metered_wiring(10_000, prompt=prompt), store_root)
    tokens = _trace(record)["tokens"]
    return tokens["prompt_tokens"] + tokens["completion_tokens"]


async def test_boundary_one_under_exactly_equal_and_one_over_the_spend(store_root):
    """RIG §LC.1's stated threshold direction: one token under continues (halted — the
    allowance was not enough), exactly equal continues (within_budget — landing on the ceiling
    has not exceeded it), one token over continues (within_budget — plenty of headroom).
    """
    spend = await _spend_for(_PROMPT, store_root)

    under = await _run(_metered_wiring(spend - 1, prompt=_PROMPT), store_root)
    assert _trace(under)["budget_state"] == "halted"

    exact = await _run(_metered_wiring(spend, prompt=_PROMPT), store_root)
    assert _trace(exact)["budget_state"] == "within_budget"

    over = await _run(_metered_wiring(spend + 1, prompt=_PROMPT), store_root)
    assert _trace(over)["budget_state"] == "within_budget"


async def test_adjacency_share_is_1_0_in_both_the_exact_fit_and_the_over_spend_case_distinguished_only_by_state(
    store_root,
):
    spend = await _spend_for(_PROMPT, store_root)

    exact = await _run(_metered_wiring(spend, prompt=_PROMPT), store_root)
    exact_trace = _trace(exact)
    assert exact_trace["realised_budget_share"] == 1.0
    assert exact_trace["budget_state"] == "within_budget"

    over_spend = await _run(_metered_wiring(spend - 1, prompt=_PROMPT), store_root)
    over_spend_trace = _trace(over_spend)
    assert over_spend_trace["realised_budget_share"] == 1.0
    assert over_spend_trace["budget_state"] == "halted"


async def _run_passthrough(config: dict[str, Any] | None, store_root) -> dict[str, Any]:
    node: dict[str, Any] = {"component": "core/passthrough@1.0.0", "kind": "passthrough", "deps": []}
    if config is not None:
        node["config"] = config
    return await databasise.run_wiring(
        {"nodes": {_NODE_ID: node}},
        store_root=store_root,
        registry=PartRegistry(),  # seeds core/passthrough@1.0.0
        determinism_setting=_DETERMINISM_SETTING,
        concurrency_setting=_CONCURRENCY_SETTING,
    )


async def test_empty_absent_config_missing_token_allowance_and_zero_effect_all_stay_within_budget_at_zero_share(
    store_root,
):
    """A node with config absent (None); a node with config present but carrying no
    token_allowance key; and a zero-effect node (``core/passthrough@1.0.0``, which declares no
    calling effect) — all three are metered against an allowance of 0, accrue spend 0 regardless
    of the body's output, and stamp an honest all-zero tokens object. None of them raises.
    """
    for config in (None, {"note": "no token_allowance key here"}):
        record = await _run_passthrough(config, store_root)
        trace = _trace(record)
        assert trace["budget_state"] == "within_budget"
        assert trace["realised_budget_share"] == 0.0
        assert trace["tokens"] == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "cached_read_tokens": 0,
            "call_count": 0,
            "counted_by": "none",
        }


async def test_ordering_guards_fired_is_declaration_order_never_sorted_and_empty_list_never_none(
    store_root,
):
    guards = [
        {"name": "zeta", "evaluating_node": _NODE_ID, "value_when_not_fired": None, "granularity": "per-query"},
        {"name": "alpha", "evaluating_node": _NODE_ID, "value_when_not_fired": None, "granularity": "per-query"},
        {"name": "mid", "evaluating_node": _NODE_ID, "value_when_not_fired": None, "granularity": "per-query"},
    ]
    # value_when_not_fired=None guarantees every guard fires: the fake LLM caller's own body
    # always returns a dict, which is never equal to None.
    record = await _run(_metered_wiring(1000, guards=guards), store_root)
    trace = _trace(record)

    assert trace["guards_fired"] == ["zeta", "alpha", "mid"]
    assert trace["guards_fired"] != sorted(trace["guards_fired"])

    no_guards_record = await _run(_metered_wiring(1000), store_root)
    assert _trace(no_guards_record)["guards_fired"] == []


def test_precision_halt_decision_is_integer_only_and_zero_allowance_share_is_exactly_0_0():
    """A unit-level exercise of ``meter()``/``realised_share()`` directly: a spend and an
    allowance differing by exactly 1 (no float can straddle it), plus the zero-allowance report
    case — proving ``realised_budget_share`` never divides by zero.
    """
    tokens = TokenAccounting(prompt_tokens=3, completion_tokens=2)  # spend = 5, both ints

    within = meter("n1", ["calls_llm"], 5, tokens)
    halted = meter("n1", ["calls_llm"], 4, tokens)

    assert within.state == "within_budget"
    assert halted.state == "halted"
    assert realised_share(0, 0) == 0.0


async def test_guard_declaration_with_an_inadmissible_granularity_refuses_before_any_node_is_dispatched(
    store_root,
):
    ran = {"called": False}

    async def body(ctx):
        ran["called"] = True
        return {}

    part = Part(
        name_at_version="test/guarded@1.0.0",
        kind="stage",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=body,
    )
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(part)
    wiring = {
        "nodes": {
            _NODE_ID: {
                "component": "test/guarded@1.0.0",
                "kind": "stage",
                "config": {
                    "guards": [
                        {
                            "name": "bad-granularity",
                            "evaluating_node": _NODE_ID,
                            "value_when_not_fired": None,
                            "granularity": "per-run",  # not one of per-query/per-instance
                        }
                    ]
                },
                "deps": [],
            }
        }
    }

    with pytest.raises(GuardDeclarationError) as exc_info:
        await databasise.run_wiring(
            wiring,
            store_root=store_root,
            registry=registry,
            determinism_setting=_DETERMINISM_SETTING,
            concurrency_setting=_CONCURRENCY_SETTING,
        )

    assert "bad-granularity" in str(exc_info.value)
    assert ran["called"] is False
