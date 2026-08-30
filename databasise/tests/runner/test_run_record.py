"""Tests for the full RIG §TR.1 run record and declared data guards (Task 3, 01-08-PLAN.md):
schema validity, the honesty invariant, and guard declaration/firing.
"""

from __future__ import annotations

import pytest
from databasise.parts.schema import NodeContext
from databasise.parts_core.fake_llm_caller import FAKE_LLM_CALLER_PART
from databasise.runner.guards import (
    GuardDeclarationError,
    declare_guard,
    evaluate_guards,
)
from databasise.runner.trace import NodeTrace, RunRecord, TokenAccounting
from databasise.stores.kv import SqliteKVStore


def _clean_node(node_id: str = "n1", **overrides) -> NodeTrace:
    fields = {
        "node_id": node_id,
        "instance_hash": "a" * 64,
        "depth": "stage",
        "effective_depth": "stage",
        "wall_clock_ms": 5,
        "cache_hit": False,
        "guards_fired": [],
        "budget_state": "within_budget",
        "realised_budget_share": 1.0,
        "cross_process_failure_cause": None,
        "resumable": True,
        "tokens": TokenAccounting(),
    }
    fields.update(overrides)
    return NodeTrace(**fields)


def _clean_record(**overrides) -> RunRecord:
    fields = {
        "run_id": "run-1",
        "wiring_id": "wiring-1",
        "wiring_instance_hash": "sha256:abc",
        "arm_id": "base",
        "arm_execution_order": 0,
        "executor_version": "databasise@0.1.0",
        "concurrency_setting": "sequential",
        "determinism_setting": "cache-bypassed",
        "nodes": [_clean_node()],
    }
    fields.update(overrides)
    return RunRecord(**fields)


def test_1_a_completed_run_validates_with_zero_errors_and_real_run_level_values(assert_valid_trace):
    record = _clean_record()
    doc = record.to_dict()

    assert_valid_trace(doc)
    for field in ("run_id", "wiring_id", "wiring_instance_hash", "arm_id", "executor_version", "concurrency_setting", "determinism_setting"):
        assert doc[field], f"{field} must carry a real, non-placeholder value"
    assert doc["bundle_ref"].startswith("sentinel:")
    assert doc["corpus_snapshot_hash"].startswith("sentinel:")


def test_2_every_node_carries_all_required_fields_and_depth_may_differ_from_effective_depth(assert_valid_trace):
    tainted_node = _clean_node(node_id="tainted", depth="stage", effective_depth="opaque")
    record = _clean_record(nodes=[_clean_node(), tainted_node])
    doc = record.to_dict()

    assert_valid_trace(doc)
    required = {
        "node_id", "instance_hash", "depth", "effective_depth", "tier", "feed_tier",
        "wall_clock_ms", "cache_hit", "guards_fired", "budget_state", "realised_budget_share",
        "cross_process_failure_cause", "resumable", "tokens",
    }
    for node in doc["nodes"]:
        assert required <= set(node)
    tainted = next(n for n in doc["nodes"] if n["node_id"] == "tainted")
    assert tainted["depth"] != tainted["effective_depth"]


def test_3_arm_execution_order_increases_across_arms_and_is_stable_across_runs():
    arm_0 = _clean_record(arm_execution_order=0)
    arm_1 = _clean_record(arm_execution_order=1, arm_id="hybrid")
    assert arm_1.arm_execution_order > arm_0.arm_execution_order

    rerun_arm_0 = _clean_record(arm_execution_order=0)
    assert rerun_arm_0.arm_execution_order == arm_0.arm_execution_order


async def test_4_cache_hit_is_false_first_then_true_on_a_genuine_repeat_call(store_root):
    kv = SqliteKVStore(namespace="cache", workspace="test", store_root=store_root)
    ctx = NodeContext(node_id="n1", config={"prompt": "hello"}, inputs={}, stores={"kv": kv})

    first = await FAKE_LLM_CALLER_PART.body(ctx)
    second = await FAKE_LLM_CALLER_PART.body(ctx)
    first_trace = _clean_node(cache_hit=first["cache_hit"])
    second_trace = _clean_node(cache_hit=second["cache_hit"])

    assert first_trace.cache_hit is False
    assert second_trace.cache_hit is True
    await kv.finalize()


def test_5_realised_budget_share_is_present_on_every_node_and_within_0_1(assert_valid_trace):
    record = _clean_record(nodes=[_clean_node(realised_budget_share=0.0), _clean_node(node_id="n2", realised_budget_share=1.0)])
    doc = record.to_dict()
    assert_valid_trace(doc)
    for node in doc["nodes"]:
        assert 0.0 <= node["realised_budget_share"] <= 1.0


def test_6_guards_fired_lists_exactly_the_declared_guards_that_fired_and_is_never_absent():
    fired_guard = declare_guard("g1", evaluating_node="upstream-a", value_when_not_fired=None, granularity="per-query")
    unfired_guard = declare_guard("g2", evaluating_node="upstream-b", value_when_not_fired="expected", granularity="per-instance")

    fired = evaluate_guards(
        [fired_guard, unfired_guard], runtime_values={"upstream-a": "something-else", "upstream-b": "expected"}
    )
    assert fired == ["g1"]

    none_fired = evaluate_guards([unfired_guard], runtime_values={"upstream-b": "expected"})
    assert none_fired == []  # empty list, never None/absent

    node = _clean_node(guards_fired=fired)
    assert node.to_dict()["guards_fired"] == ["g1"]


def test_7_determinism_and_concurrency_setting_carry_the_values_the_run_was_invoked_with():
    record = _clean_record(determinism_setting="cache-bypassed", concurrency_setting="concurrent")
    doc = record.to_dict()
    assert doc["determinism_setting"] == "cache-bypassed"
    assert doc["concurrency_setting"] == "concurrent"


def test_8_a_degraded_run_names_its_path_a_clean_run_carries_none(assert_valid_trace):
    degraded = _clean_record(degraded=True, partial=True, stop_reason="fallback-path-taken", degradation_reason="client-capability-fallback")
    assert_valid_trace(degraded.to_dict())
    assert degraded.degraded is True
    assert degraded.degradation_reason == "client-capability-fallback"

    clean = _clean_record()
    assert_valid_trace(clean.to_dict())
    assert clean.degraded is False
    assert clean.degradation_reason is None


def test_9_a_budget_halted_run_is_partial_with_a_stop_reason_and_is_still_fully_traced(assert_valid_trace):
    halted_node = _clean_node(budget_state="halted")
    halted_run = _clean_record(
        nodes=[halted_node],
        partial=True,
        degraded=True,
        stop_reason="node 'n1' exceeded its budget allowance",
        degradation_reason="budget_halted",
    )
    assert_valid_trace(halted_run.to_dict())
    assert halted_run.partial is True
    assert halted_run.stop_reason is not None
    assert len(halted_run.nodes) == 1  # traced, not discarded

    clean = _clean_record()
    assert clean.partial is False
    assert clean.stop_reason is None


def test_10_cross_process_failure_cause_is_null_in_process_and_named_on_a_placement_refusal():
    in_process_node = _clean_node(cross_process_failure_cause=None)
    refused_node = _clean_node(
        node_id="refused", cross_process_failure_cause="execution_mode='subprocess' not hosted (D-08)"
    )
    assert in_process_node.cross_process_failure_cause is None
    assert "subprocess" in refused_node.cross_process_failure_cause


def test_11_the_two_guard_granularities_are_distinguishable_and_a_missing_one_is_refused():
    per_instance = declare_guard("g1", "n1", None, "per-instance")
    per_query = declare_guard("g2", "n1", None, "per-query")
    assert per_instance.granularity != per_query.granularity
    assert {per_instance.granularity, per_query.granularity} == {"per-instance", "per-query"}

    with pytest.raises(GuardDeclarationError) as exc_info:
        declare_guard("g3", "n1", None, granularity="")
    assert "per-query" in str(exc_info.value)
    assert "per-instance" in str(exc_info.value)


def test_12_constructing_a_confounded_run_record_raises():
    with pytest.raises(ValueError):
        _clean_record(stop_reason="something halted", partial=False)

    with pytest.raises(ValueError):
        _clean_record(degradation_reason="something fired", degraded=False)

    with pytest.raises(ValueError):
        _clean_record(nodes=[_clean_node(budget_state="halted")], partial=False)
