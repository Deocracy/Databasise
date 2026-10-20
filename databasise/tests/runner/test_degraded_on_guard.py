"""D-21 / HIPP-14: the scheduler reports a completed run whose declared guard fired as ``degraded``
(not ``partial``) with closed, node-free reason codes, and ``RunRecord`` accepts that shape.
"""

from __future__ import annotations

import pytest
from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.runner import scheduler
from databasise.runner.trace import (
    DEGRADATION_REASON_FALLBACK_PATH,
    STOP_REASON_DECLARED_FALLBACK,
    NodeTrace,
    RunRecord,
    TokenAccounting,
)
from databasise.validator.errors import ValidationReport
from databasise.validator.parse import ParsedWiring


async def _run_guarded(output: dict) -> dict:
    async def body(ctx: NodeContext):
        return output

    part = Part(
        name_at_version="test/evaluator@1.0.0",
        kind="stage",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=body,
    )
    guard = {
        "name": "g",
        "evaluating_node": "n1",
        "value_when_not_fired": True,
        "granularity": "per-query",
        "signal": "ok",
    }
    node = WiringNode(
        component="test/evaluator@1.0.0", kind="stage", config={"guards": [guard]}, deps=[]
    )
    parsed = ParsedWiring(
        nodes={"n1": node},
        parts={"n1": part},
        deps={"n1": ()},
        node_order=("n1",),
        report=ValidationReport(),
    )
    return await scheduler.run_wiring(
        parsed,
        PartRegistry(),
        {},
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )


async def test_a_fired_guard_on_a_completed_run_is_degraded_not_partial_with_closed_codes():
    result = await _run_guarded({"ok": False})

    assert (result["degraded"], result["partial"]) == (True, False)
    assert result["stop_reason"] == STOP_REASON_DECLARED_FALLBACK == "declared_fallback"
    assert result["degradation_reason"] == DEGRADATION_REASON_FALLBACK_PATH == "fallback_path_taken"


async def test_an_unfired_guard_leaves_the_run_clean():
    result = await _run_guarded({"ok": True})

    assert (result["degraded"], result["partial"]) == (False, False)
    assert (result["stop_reason"], result["degradation_reason"]) == (None, None)


def _record(**overrides) -> RunRecord:
    node = NodeTrace(
        node_id="n1",
        instance_hash="a" * 64,
        depth="stage",
        effective_depth="stage",
        wall_clock_ms=1,
        cache_hit=False,
        guards_fired=[],
        budget_state="within_budget",
        realised_budget_share=1.0,
        cross_process_failure_cause=None,
        resumable=True,
        tokens=TokenAccounting(),
    )
    fields = {
        "run_id": "r",
        "wiring_id": "w",
        "wiring_instance_hash": "sha256:abc",
        "arm_id": "base",
        "arm_execution_order": 0,
        "executor_version": "databasise@0.1.0",
        "concurrency_setting": "sequential",
        "determinism_setting": "cache-bypassed",
        "nodes": [node],
    }
    fields.update(overrides)
    return RunRecord(**fields)


def test_run_record_accepts_degraded_without_partial_and_partial_without_degraded():
    reasons = {"stop_reason": "s", "degradation_reason": "d"}

    assert _record(degraded=True, **reasons).partial is False
    assert _record(partial=True, **reasons).degraded is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"degraded": True, "stop_reason": "s"},
        {"degraded": True, "degradation_reason": "d"},
        {"stop_reason": "s"},
        {"degradation_reason": "d"},
    ],
)
def test_run_record_still_refuses_a_missing_or_stray_reason(overrides):
    with pytest.raises(ValueError):
        _record(**overrides)
