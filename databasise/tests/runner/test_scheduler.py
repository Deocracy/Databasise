"""Tests for the completed runner (Task 1, 01-08-PLAN.md): per-node semaphore concurrency
boundaries, deterministic ready-batch dispatch ordering, D-08's named placement refusals, D-04's
declaration-only dispatch refusal (via the live scheduler path, closing 01-04's inherited gap 1),
cycle-as-data, and structured-concurrency failure semantics.

Every test constructs a ``ParsedWiring`` directly (bypassing ``validator.parse.parse_wiring``,
which is out of this plan's lane and already has its own test suite) so each test can register a
purpose-built ``Part`` body without needing a real component registry entry.
"""

from __future__ import annotations

import asyncio

import pytest
from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.runner import scheduler
from databasise.runner.scheduler import InvalidMaxConcurrencyError, WiringRefusedError
from databasise.validator.errors import ValidationReport, Violation
from databasise.validator.parse import ParsedWiring


def _wiring(nodes: dict, parts: dict, deps: dict, report: ValidationReport | None = None) -> ParsedWiring:
    return ParsedWiring(
        nodes=nodes,
        parts=parts,
        deps=deps,
        node_order=tuple(sorted(nodes)),
        report=report if report is not None else ValidationReport(),
    )


async def _run(parsed: ParsedWiring, stores: dict | None = None) -> dict:
    return await scheduler.run_wiring(
        parsed,
        PartRegistry(),
        stores or {},
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
    )


def _fanout_part(name: str, width: int, counter: dict) -> Part:
    """A part whose body fans out ``width`` internal child coroutines, each gated by the
    scheduler-owned ``ctx._semaphore`` extension attribute (see scheduler.py's module
    docstring), tracking the peak number simultaneously inside the semaphore.
    """

    async def body(ctx: NodeContext):
        async def child() -> None:
            async with ctx._semaphore:
                counter["current"] += 1
                counter["peak"] = max(counter["peak"], counter["current"])
                await asyncio.sleep(0.02)
                counter["current"] -= 1

        await asyncio.gather(*(child() for _ in range(width)))
        return {"ran": True}

    return Part(
        name_at_version=name, kind="fanout", structural_depth="stage", effects=[], upstream_ref=None, body=body
    )


async def test_1_max_concurrency_1_never_exceeds_1_in_flight():
    counter = {"current": 0, "peak": 0}
    part = _fanout_part("test/fanout1@1.0.0", 4, counter)
    node = WiringNode(component="test/fanout1@1.0.0", kind="fanout", config={"max_concurrency": 1}, deps=[])
    parsed = _wiring({"n1": node}, {"n1": part}, {"n1": ()})

    await _run(parsed)

    assert counter["peak"] == 1


async def test_2_max_concurrency_2_reaches_peak_2_never_3():
    counter = {"current": 0, "peak": 0}
    part = _fanout_part("test/fanout2@1.0.0", 4, counter)
    node = WiringNode(component="test/fanout2@1.0.0", kind="fanout", config={"max_concurrency": 2}, deps=[])
    parsed = _wiring({"n1": node}, {"n1": part}, {"n1": ()})

    await _run(parsed)

    assert counter["peak"] == 2


async def test_3_max_concurrency_0_is_refused_at_validation_naming_the_node():
    ran = {"called": False}

    async def body(ctx: NodeContext):
        ran["called"] = True
        return {}

    part = Part(
        name_at_version="test/zero@1.0.0",
        kind="fanout",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=body,
    )
    node = WiringNode(component="test/zero@1.0.0", kind="fanout", config={"max_concurrency": 0}, deps=[])
    parsed = _wiring({"bad-node": node}, {"bad-node": part}, {"bad-node": ()})

    with pytest.raises(InvalidMaxConcurrencyError) as exc_info:
        await _run(parsed)

    assert "bad-node" in str(exc_info.value)
    assert ran["called"] is False  # the run never started


async def test_3b_max_concurrency_non_numeric_is_refused_as_invalid_max_concurrency_not_value_error():
    """WR-04 regression: a non-numeric ``max_concurrency`` (a string ``int()`` cannot coerce)
    must raise the module's own named ``InvalidMaxConcurrencyError``, not a bare ``ValueError``
    leaking out of ``int(...)`` — the module's own documented "refused at validation, naming the
    offending node id" contract must hold for this class of malformed input too.
    """
    ran = {"called": False}

    async def body(ctx: NodeContext):
        ran["called"] = True
        return {}

    part = Part(
        name_at_version="test/non-numeric@1.0.0",
        kind="fanout",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=body,
    )
    node = WiringNode(
        component="test/non-numeric@1.0.0",
        kind="fanout",
        config={"max_concurrency": "not-a-number"},
        deps=[],
    )
    parsed = _wiring({"bad-node": node}, {"bad-node": part}, {"bad-node": ()})

    with pytest.raises(InvalidMaxConcurrencyError) as exc_info:
        await _run(parsed)

    assert "bad-node" in str(exc_info.value)
    assert ran["called"] is False  # the run never started


async def test_4_isolation_one_arms_fanout_never_throttles_an_unrelated_arm():
    counter_a = {"current": 0, "peak": 0}
    counter_b = {"current": 0, "peak": 0}
    part_a = _fanout_part("test/iso-a@1.0.0", 4, counter_a)
    part_b = _fanout_part("test/iso-b@1.0.0", 8, counter_b)
    node_a = WiringNode(component="test/iso-a@1.0.0", kind="fanout", config={"max_concurrency": 1}, deps=[])
    node_b = WiringNode(component="test/iso-b@1.0.0", kind="fanout", config={"max_concurrency": 8}, deps=[])
    parsed = _wiring(
        {"a": node_a, "b": node_b},
        {"a": part_a, "b": part_b},
        {"a": (), "b": ()},
    )

    await _run(parsed)

    assert counter_a["peak"] == 1
    assert counter_b["peak"] == 8


async def test_5_ready_batch_dispatch_order_is_sorted_and_stable_across_ten_runs():
    async def body(ctx: NodeContext):
        return {"node_id": ctx.node_id}

    parts = {
        n: Part(name_at_version=f"test/{n}@1.0.0", kind="passthrough", structural_depth="stage", effects=[], upstream_ref=None, body=body)
        for n in ("gamma", "alpha", "beta")
    }
    nodes = {
        n: WiringNode(component=f"test/{n}@1.0.0", kind="passthrough", deps=[]) for n in parts
    }
    parsed = _wiring(nodes, parts, {n: () for n in parts})

    for _ in range(10):
        result = await _run(parsed)
        assert [n.node_id for n in result["nodes"]] == ["alpha", "beta", "gamma"]


async def test_6_fanout_adjacency_is_never_collapsed_by_identity():
    calls = {"count": 0}

    async def body(ctx: NodeContext):
        calls["count"] += 1
        return {}

    shared_config = {"note": "shared"}
    part = Part(
        name_at_version="test/adjacent@1.0.0",
        kind="passthrough",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=body,
    )
    node_1 = WiringNode(component="test/adjacent@1.0.0", kind="passthrough", config=shared_config, deps=[])
    node_2 = WiringNode(component="test/adjacent@1.0.0", kind="passthrough", config=shared_config, deps=[])
    parsed = _wiring(
        {"branch-1": node_1, "branch-2": node_2},
        {"branch-1": part, "branch-2": part},
        {"branch-1": (), "branch-2": ()},
    )

    result = await _run(parsed)

    assert calls["count"] == 2
    node_ids = {n.node_id for n in result["nodes"]}
    assert node_ids == {"branch-1", "branch-2"}
    instance_hashes = {n.instance_hash for n in result["nodes"]}
    assert len(instance_hashes) == 1  # same component@version + same config -> one identity


async def test_7_a_single_node_runs_and_an_empty_wiring_is_refused_before_the_runner_starts():
    async def body(ctx: NodeContext):
        return {}

    part = Part(
        name_at_version="test/single@1.0.0",
        kind="passthrough",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=body,
    )
    node = WiringNode(component="test/single@1.0.0", kind="passthrough", deps=[])
    parsed = _wiring({"only": node}, {"only": part}, {"only": ()})

    result = await _run(parsed)
    assert len(result["nodes"]) == 1

    empty_report = ValidationReport(
        violations=[Violation(code="empty-wiring", pointer="/nodes", message="a wiring's `nodes` object must not be empty")]
    )
    empty_parsed = _wiring({}, {}, {}, report=empty_report)

    with pytest.raises(WiringRefusedError):
        await _run(empty_parsed)


async def test_8_a_sibling_failure_cancels_the_batch_and_marks_the_run_not_clean():
    sibling_finished = {"value": False}

    async def failing_body(ctx: NodeContext):
        raise RuntimeError("deliberate failure")

    async def slow_sibling_body(ctx: NodeContext):
        await asyncio.sleep(0.2)
        sibling_finished["value"] = True  # should never be reached — cancelled by the failure
        return {}

    part_fail = Part(
        name_at_version="test/fail@1.0.0", kind="passthrough", structural_depth="stage", effects=[], upstream_ref=None, body=failing_body
    )
    part_slow = Part(
        name_at_version="test/slow@1.0.0", kind="passthrough", structural_depth="stage", effects=[], upstream_ref=None, body=slow_sibling_body
    )
    node_fail = WiringNode(component="test/fail@1.0.0", kind="passthrough", deps=[])
    node_slow = WiringNode(component="test/slow@1.0.0", kind="passthrough", deps=[])
    parsed = _wiring(
        {"fail": node_fail, "slow": node_slow},
        {"fail": part_fail, "slow": part_slow},
        {"fail": (), "slow": ()},
    )

    result = await _run(parsed)

    assert result["partial"] is True
    assert result["stop_reason"] is not None
    assert sibling_finished["value"] is False  # the sibling was cancelled, not merely outrun


async def test_9_a_placement_refusal_stamps_the_derived_placement_without_suppressing_it():
    async def body(ctx: NodeContext):
        return {}

    part = Part(
        name_at_version="test/networked@1.0.0",
        kind="stage",
        structural_depth="stage",
        effects=["net"],
        upstream_ref=None,
        body=body,
    )
    node = WiringNode(component="test/networked@1.0.0", kind="stage", effects=["net"], deps=[])
    parsed = _wiring({"net-node": node}, {"net-node": part}, {"net-node": ()})

    result = await _run(parsed)

    assert result["partial"] is True
    net_node_trace = next(n for n in result["nodes"] if n.node_id == "net-node")
    assert "long-lived-service" in net_node_trace.cross_process_failure_cause


async def test_11_placement_is_sourced_from_the_parts_effects_not_the_wirings_underdeclared_ones():
    """CR-01 regression. The wiring node deliberately under-declares ``effects=[]`` (looks pure
    and hostable), while its resolved ``Part`` declares ``net`` — a real capability that must
    derive ``long-lived-service`` (unhosted in Phase 1, D-08) regardless of what the wiring
    claims. A wiring document is untrusted, author-supplied input (see
    ``databasise/validator/cycles.py``'s own "a hostile or merely large wiring could declare..."
    framing); before the fix, ``derive_execution_mode`` read ``WiringNode.effects``/``.kind`` and
    would have derived ``in-process`` here instead, silently bypassing D-08's containment rule.
    This test bypasses ``parse_wiring`` (as every test in this module does — see module
    docstring) so it can construct the adversarial node/part pair directly; the equivalent
    document-validation-layer refusal (``CODE_EFFECTS_EXCEED_PART``) is covered separately in
    ``tests/validator/test_cycles_and_depth.py``.
    """

    async def body(ctx: NodeContext):
        return {}  # never reached — placement is refused before dispatch

    part = Part(
        name_at_version="test/underdeclared-net@1.0.0",
        kind="stage",
        structural_depth="stage",
        effects=["net"],  # the Part's real, registered capability
        upstream_ref=None,
        body=body,
    )
    node = WiringNode(component="test/underdeclared-net@1.0.0", kind="stage", effects=[], deps=[])
    parsed = _wiring({"n1": node}, {"n1": part}, {"n1": ()})

    result = await _run(parsed)

    assert result["partial"] is True
    trace = next(n for n in result["nodes"] if n.node_id == "n1")
    assert "long-lived-service" in trace.cross_process_failure_cause


async def test_12_capability_scoped_store_view_is_sourced_from_the_parts_effects_not_the_wirings():
    """CR-01 regression. The wiring node under-declares ``effects=[]`` while its resolved ``Part``
    declares ``writes_kv`` — the actual capability the body needs to reach ``ctx.stores["kv"]``.
    Before the fix, ``CapabilityScopedStores`` was built from ``WiringNode.effects`` (empty here),
    so this exact body would have raised ``UndeclaredEffectError`` and failed the node even though
    the Part is genuinely entitled to the store. The store view must be scoped by the Part's own
    declaration, not the wiring's under-declared one.
    """

    async def body(ctx: NodeContext):
        return {"kv": ctx.stores["kv"]}

    part = Part(
        name_at_version="test/underdeclared-kv@1.0.0",
        kind="stage",
        structural_depth="stage",
        effects=["writes_kv"],
        upstream_ref=None,
        body=body,
    )
    node = WiringNode(component="test/underdeclared-kv@1.0.0", kind="stage", effects=[], deps=[])
    parsed = _wiring({"n1": node}, {"n1": part}, {"n1": ()})

    result = await _run(parsed, stores={"kv": "the-real-kv-store"})

    assert result["partial"] is False
    assert result["results"]["n1"]["kv"] == "the-real-kv-store"

    # The same substitution reaches D-13's resume boundary: the node genuinely mutated a store
    # (the Part declares writes_kv and the scoped view granted it), so it can never be stamped a
    # safe resume point. Sourcing `resumable` from the wiring's empty effects[] would claim it is.
    trace = next(n for n in result["nodes"] if n.node_id == "n1")
    assert trace.resumable is False


async def test_10_a_cyclic_wiring_returns_the_cycle_as_data_rather_than_raising():
    async def body(ctx: NodeContext):
        return {}

    part_a = Part(name_at_version="test/cyc-a@1.0.0", kind="passthrough", structural_depth="stage", effects=[], upstream_ref=None, body=body)
    part_b = Part(name_at_version="test/cyc-b@1.0.0", kind="passthrough", structural_depth="stage", effects=[], upstream_ref=None, body=body)
    node_a = WiringNode(component="test/cyc-a@1.0.0", kind="passthrough", deps=["b"])
    node_b = WiringNode(component="test/cyc-b@1.0.0", kind="passthrough", deps=["a"])
    cyclic_report = ValidationReport(violations=[], cycles=[["a", "b"]])
    parsed = _wiring(
        {"a": node_a, "b": node_b},
        {"a": part_a, "b": part_b},
        {"a": ("b",), "b": ("a",)},
        report=cyclic_report,
    )

    result = await _run(parsed)

    assert result == {"cycle": [["a", "b"]]}
