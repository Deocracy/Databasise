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

import databasise
from databasise.parts.registry import PartRegistry
from databasise.parts_core.fake_llm_caller import FAKE_LLM_CALLER_PART

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
