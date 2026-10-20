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
from databasise.stores.kv import SqliteKVStore
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
