"""WIRE-11 (13-03-PLAN.md): every NodeTrace field reports what was measured, in a schema that
admits it. ``execution_mode`` is stamped on both the success and the refusal path, ``cache_hit``
is the part's own boolean or ``None``, ``spent``/``allowance`` carry the metered figures (an
overspend is visible there while ``realised_budget_share`` stays capped at 1.0), and ``tier`` /
``feed_tier`` are ``None`` rather than a placeholder (D-14).

Import discipline: only names that exist at the phase base are imported at module level; new names
are resolved with ``getattr`` and exceptions are captured, so each test fails by assertion on
pre-fix code.
"""

from __future__ import annotations

from typing import Any

import databasise
from databasise.parts.admission import (
    MANIFEST_SOURCE_CODE_INSPECTED,
    AdmissionRecord,
    ConditionVerdict,
)
from databasise.parts.registry import PartRegistry, default_registry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.parts_core.fake_llm_caller import FAKE_LLM_CALLER_PART
from databasise.parts_core.passthrough import PASSTHROUGH_PART
from databasise.runner import scheduler
from databasise.runner.trace import NodeTrace, TokenAccounting
from databasise.validator.errors import ValidationReport
from databasise.validator.parse import ParsedWiring

_VERDICTS = tuple(
    ConditionVerdict(condition=i, verdict="satisfied", evidence=f"evidence for condition {i}")
    for i in range(1, 12)
)


def _admitted_opaque_part() -> Part:
    async def body(ctx: NodeContext) -> dict[str, Any]:
        return {"ran": True}

    record = AdmissionRecord(
        part_name_at_version="test/opaque-part@1.0.0",
        entry_path="subprocess",
        storage="machine",
        wall_clock_ceiling_seconds=60.0,
        wall_clock_ceiling_basis="test fixture",
        feed_tier="document",
        ttl_days=1,
        network_namespace="denied-by-construction",
        environment_hash="sha256:" + "a" * 64,
        manifest_source=MANIFEST_SOURCE_CODE_INSPECTED,
        verdicts=_VERDICTS,
    )
    return Part(
        name_at_version="test/opaque-part@1.0.0",
        kind="opaque",
        structural_depth="opaque",
        effects=[],
        upstream_ref=None,
        body=body,
        artifact_scope="quarantined",
        admission=record,
    )


def _parsed(part: Part, config: dict[str, Any] | None = None) -> ParsedWiring:
    node = WiringNode(
        component=part.name_at_version, kind=part.kind, effects=list(part.effects), config=config, deps=[]
    )
    return ParsedWiring(
        nodes={"n1": node},
        parts={"n1": part},
        deps={"n1": ()},
        node_order=("n1",),
        report=ValidationReport(),
    )


async def _run(parsed: ParsedWiring, stores: dict | None = None) -> dict:
    return await scheduler.run_wiring(
        parsed,
        PartRegistry(),
        stores or {},
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )


def _passthrough_wiring() -> dict[str, Any]:
    return {
        "nodes": {
            "n1": {
                "component": PASSTHROUGH_PART.name_at_version,
                "kind": PASSTHROUGH_PART.kind,
                "effects": [],
                "config": {},
                "deps": [],
            }
        }
    }


async def test_a_passthrough_node_is_stamped_in_process_and_reports_no_cache_hit():
    result = await _run(_parsed(PASSTHROUGH_PART))

    trace = result["nodes"][0]
    assert getattr(trace, "execution_mode", None) == "in-process"
    assert trace.cache_hit is None


async def test_the_run_record_validates_against_the_derived_schema(store_root, assert_valid_trace):
    record = await databasise.run_wiring(
        _passthrough_wiring(),
        store_root=store_root,
        registry=default_registry(),
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )
    node = record["nodes"][0]
    assert node.get("execution_mode") == "in-process"

    try:
        assert_valid_trace(record)
        valid_error = None
    except Exception as exc:  # noqa: BLE001 - asserted on below
        valid_error = exc
    assert valid_error is None, f"a real record must validate: {valid_error}"

    node["execution_mode"] = "elsewhere"
    try:
        assert_valid_trace(record)
        rejected = False
    except AssertionError:
        rejected = True
    assert rejected, "assert_valid_trace must reject an execution_mode outside the declared enum"


def _spender(spent_prompt: int, spent_completion: int) -> Part:
    async def body(ctx: NodeContext) -> dict[str, Any]:
        tokens = TokenAccounting(
            prompt_tokens=spent_prompt, completion_tokens=spent_completion, call_count=1, counted_by="t"
        )
        return {"tokens": tokens}

    return Part(
        name_at_version="test/spender@1.0.0",
        kind="llm-caller",
        structural_depth="stage",
        effects=["calls_llm"],
        upstream_ref=None,
        body=body,
    )


async def test_an_admitted_opaque_node_is_stamped_subprocess():
    result = await _run(_parsed(_admitted_opaque_part()))

    trace = result["nodes"][0]
    assert getattr(trace, "execution_mode", None) == "subprocess"
    assert getattr(trace, "status", None) == "completed"


async def test_a_refused_placement_is_stamped_on_the_failed_trace():
    async def body(ctx: NodeContext) -> dict[str, Any]:
        return {}

    unit = Part(
        name_at_version="test/fs-unit@1.0.0",
        kind="unit",
        structural_depth="stage",
        effects=["fs"],
        upstream_ref=None,
        body=body,
    )
    result = await _run(_parsed(unit, {"token_allowance": 7}))

    trace = result["nodes"][0]
    assert result["partial"] is True
    assert getattr(trace, "execution_mode", None) == "confined-unit"
    assert getattr(trace, "status", None) == "failed"
    assert getattr(trace, "allowance", None) == 7
    assert getattr(trace, "spent", "unset") is None
    assert trace.cache_hit is None


async def test_a_failed_body_is_stamped_failed_with_its_derived_placement():
    async def body(ctx: NodeContext) -> dict[str, Any]:
        raise RuntimeError("body failed")

    failing = Part(
        name_at_version="test/failing@1.0.0",
        kind="stage",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=body,
    )
    result = await _run(_parsed(failing))

    trace = result["nodes"][0]
    assert getattr(trace, "execution_mode", None) == "in-process"
    assert getattr(trace, "status", None) == "failed"


async def test_an_overspending_node_reports_spent_and_allowance():
    result = await _run(_parsed(_spender(1000, 500), {"token_allowance": 1000}))

    trace = result["nodes"][0]
    spent = getattr(trace, "spent", None)
    allowance = getattr(trace, "allowance", None)
    assert spent == 1500
    assert allowance == 1000
    assert spent / allowance > 1.0
    assert trace.budget_state == "halted"
    assert trace.realised_budget_share == 1.0


async def test_spending_exactly_the_allowance_stays_within_budget():
    exact = (await _run(_parsed(_spender(600, 400), {"token_allowance": 1000})))["nodes"][0]
    assert getattr(exact, "spent", None) == 1000
    assert exact.budget_state == "within_budget"
    assert exact.realised_budget_share == 1.0

    over = (await _run(_parsed(_spender(600, 401), {"token_allowance": 1000})))["nodes"][0]
    assert getattr(over, "spent", None) == 1001
    assert over.budget_state == "halted"


async def test_a_zero_allowance_node_with_no_spend_is_within_budget():
    trace = (await _run(_parsed(PASSTHROUGH_PART)))["nodes"][0]

    assert getattr(trace, "spent", None) == 0
    assert getattr(trace, "allowance", None) == 0
    assert trace.budget_state == "within_budget"
    assert trace.realised_budget_share == 0.0


def test_node_trace_defaults_carry_no_placeholder_tier():
    trace = NodeTrace(
        node_id="n1",
        instance_hash="a" * 64,
        depth="stage",
        effective_depth="stage",
        wall_clock_ms=0,
        cache_hit=None,
        guards_fired=[],
        budget_state="within_budget",
        realised_budget_share=0.0,
        cross_process_failure_cause=None,
        resumable=True,
        tokens=TokenAccounting(),
    )

    assert trace.tier is None
    assert trace.feed_tier is None


async def test_fake_llm_caller_still_reports_its_cache_hit(store_root):
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(FAKE_LLM_CALLER_PART)
    wiring = {
        "nodes": {
            "n1": {
                "component": FAKE_LLM_CALLER_PART.name_at_version,
                "kind": "llm-caller",
                "effects": list(FAKE_LLM_CALLER_PART.effects),
                "config": {"prompt": "count these words please", "token_allowance": 1000},
                "deps": [],
            }
        }
    }

    hits = []
    for _ in range(2):
        record = await databasise.run_wiring(
            wiring,
            store_root=store_root,
            registry=registry,
            determinism_setting="cache-bypassed",
            concurrency_setting="sequential",
        )
        hits.append(record["nodes"][0]["cache_hit"])

    assert hits == [False, True]
