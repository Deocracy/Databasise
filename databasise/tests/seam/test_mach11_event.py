"""04-04-PLAN.md Task 2: MACH-11 — an out-of-``deps`` ``mutates_store`` mutation surfaces as a
seam-level event; an ordinary declared-and-in-graph mutation does not (D-09, FA-08).

No registered ``parts_core``/``LIGHTRAG_PARTS`` part declares ``mutates_store`` today
(04-RESEARCH.md Pitfall 6), so this test drives the correlation against two fixture parts
registered here, wired into a small fixture graph, run through the real
``databasise.runner.scheduler.run_wiring`` — never a hand-inspected shape. Neither fixture part is
added to ``databasise/parts_core/``.

**A genuine, separate gap this test works around and documents rather than hides.**
``databasise.validator.execution_mode.derive_execution_mode`` routes any ``Part`` declaring
``mutates_store`` to the ``confined-unit`` placement, and Phase 1's ``host()`` (D-08) hosts
``in-process`` only — every other placement is refused by name. This means a fixture part
declaring ``mutates_store`` can never complete real dispatch under the current runner: the run
still executes and returns (``partial=True``, the node traced ``budget_state="halted"`` per
CONTRACT §9's "MUST NOT be discarded" rule — never a hard failure), but the node's own body never
runs, so the scheduler's own recorder never observes a touch for it. To still prove the
correlation logic against a *real* touch tuple in the exact shape the scheduler's own
``_ScopedStoresView`` emits, this test calls that same production class directly for the two
mutator nodes — the identical code path a hosted node's body would exercise via ``ctx.stores["kv"]``
— rather than fabricating a `(node_id, kind, key)` tuple by hand. The run itself (via
``run_wiring``, with a real recorder) still supplies a genuine touch for the non-mutating
dependency node, proving the recorder plumbing itself.
"""

from __future__ import annotations

import asyncio
import dataclasses
import sys
from pathlib import Path

import pydantic
import pytest

from databasise.foreign import run_corpus_op
from databasise.parts.registry import Part, PartRegistry
from databasise.parts.schema import NodeContext
from databasise.parts_core import CapabilityScopedStores
from databasise.parts_core.declared_only import LIGHTRAG_FULL_DELETE_PART
from databasise.runner.scheduler import TOUCH_KIND_NODE_REPORTED, _ScopedStoresView, run_wiring
from databasise.runner.trace import TokenAccounting
from databasise.seam.engine import _accounted_store_keys, _mach11_events
from databasise.seam.envelope import SeamEvent
from databasise.stores.kv import SqliteKVStore
from databasise.validator.parse import parse_wiring

IN_DEPS_MUTATOR_NAME = "test/mach11-in-deps-mutator@1.0.0"
OUT_OF_DEPS_MUTATOR_NAME = "test/mach11-out-of-deps-mutator@1.0.0"
_MUTATOR_EFFECTS = ["mutates_store", "writes_kv"]


async def _mutator_body(ctx: NodeContext) -> dict[str, object]:
    """Never actually dispatched in this test (see module docstring's D-08 note) — present so
    the fixture ``Part`` is a genuine, executable component, not a declaration-only stub."""
    store = ctx.stores["kv"]
    await store.upsert({ctx.node_id: {"mutated": True}})
    return {"node_id": ctx.node_id}


def _make_registry() -> PartRegistry:
    """``PartRegistry()``'s default seeding already carries ``core/passthrough@1.0.0`` (no
    effects) and ``core/kv-writer@1.0.0`` (``writes_kv``) — the tracer's own reference parts,
    reused here as the two dependency shapes this test needs rather than authoring new ones."""
    registry = PartRegistry()
    registry.register(
        Part(
            name_at_version=IN_DEPS_MUTATOR_NAME,
            kind="mutator",
            structural_depth="stage",
            effects=list(_MUTATOR_EFFECTS),
            upstream_ref=None,
            body=_mutator_body,
        )
    )
    registry.register(
        Part(
            name_at_version=OUT_OF_DEPS_MUTATOR_NAME,
            kind="mutator",
            structural_depth="stage",
            effects=list(_MUTATOR_EFFECTS),
            upstream_ref=None,
            body=_mutator_body,
        )
    )
    return registry


_FIXTURE_WIRING = {
    "wiring_id": "mach11-fixture",
    "nodes": {
        "dep-writes-kv": {
            "component": "core/kv-writer@1.0.0",
            "kind": "kv-writer",
            "effects": ["writes_kv"],
            "deps": [],
        },
        "mut-in-deps": {
            "component": IN_DEPS_MUTATOR_NAME,
            "kind": "mutator",
            "effects": _MUTATOR_EFFECTS,
            "deps": ["dep-writes-kv"],
        },
        "dep-no-store-effects": {
            "component": "core/passthrough@1.0.0",
            "kind": "passthrough",
            "effects": [],
            "deps": [],
        },
        "mut-out-of-deps": {
            "component": OUT_OF_DEPS_MUTATOR_NAME,
            "kind": "mutator",
            "effects": _MUTATOR_EFFECTS,
            "deps": ["dep-no-store-effects"],
        },
    },
    "provides": [],
}


async def _run_fixture_and_synthesize_mutator_touches(store_root):
    """Real ``parse_wiring`` + real ``run_wiring`` (with a real recorder) over the full fixture
    graph, then — per this module's own D-08 note — the two mutator nodes' own store touch is
    produced by calling the scheduler's own ``_ScopedStoresView`` directly, since neither node can
    complete real dispatch under Phase 1's hosting.
    """
    registry = _make_registry()
    parsed = parse_wiring(_FIXTURE_WIRING, registry)
    assert parsed.report.ok, [v.code for v in parsed.report.violations]

    stores = {
        "kv": SqliteKVStore(namespace="mach11-fixture", workspace="mach11-test", store_root=store_root)
    }
    touches: list[tuple[str, str, str]] = []

    def recorder(node_id: str, kind: str, key: str) -> None:
        touches.append((node_id, kind, key))

    try:
        scheduled = await run_wiring(
            parsed,
            registry,
            stores,
            determinism_setting="cache-bypassed",
            concurrency_setting="sequential",
            recorder=recorder,
        )

        # D-08: neither mutator node can complete real dispatch (mutates_store -> confined-unit ->
        # unhosted), so its own touch is produced via the scheduler's own production touch-recording
        # class directly — the identical code path a hosted node's body would exercise.
        for node_id in ("mut-in-deps", "mut-out-of-deps"):
            view = _ScopedStoresView(
                CapabilityScopedStores(stores, _MUTATOR_EFFECTS), _MUTATOR_EFFECTS, node_id, recorder
            )
            view["kv"]
    finally:
        await stores["kv"].finalize()

    return parsed, scheduled, touches


async def test_both_mutator_nodes_are_traced_as_halted_never_silently_dropped(store_root):
    """CONTRACT §9's own "MUST NOT be discarded" rule — a placement refusal still produces a
    traced, partial result, per this module's own D-08 note."""
    _parsed, scheduled, _touches = await _run_fixture_and_synthesize_mutator_touches(store_root)

    assert scheduled["partial"] is True
    node_by_id = {node.node_id: node for node in scheduled["nodes"]}
    assert node_by_id["mut-in-deps"].budget_state == "halted"
    assert node_by_id["mut-out-of-deps"].budget_state == "halted"


async def test_the_recorder_observes_at_least_one_store_touch_for_the_mutating_fixture_run(store_root):
    _parsed, _scheduled, touches = await _run_fixture_and_synthesize_mutator_touches(store_root)

    assert any(kind == "store" for _node_id, kind, _key in touches)
    assert ("dep-writes-kv", "store", "kv") in touches


async def test_an_out_of_deps_mutation_yields_exactly_one_event_and_the_in_deps_mutation_yields_none(
    store_root,
):
    parsed, scheduled, touches = await _run_fixture_and_synthesize_mutator_touches(store_root)
    node_by_id = {node.node_id: node for node in scheduled["nodes"]}

    events = _mach11_events(parsed, touches, node_by_id)

    assert len(events) == 1
    assert isinstance(events[0], SeamEvent)


async def test_the_events_component_equals_the_out_of_deps_parts_registered_name_at_version(
    store_root,
):
    parsed, scheduled, touches = await _run_fixture_and_synthesize_mutator_touches(store_root)
    node_by_id = {node.node_id: node for node in scheduled["nodes"]}
    registry = _make_registry()

    [event] = _mach11_events(parsed, touches, node_by_id)

    assert event.component == registry.get(OUT_OF_DEPS_MUTATOR_NAME).name_at_version
    assert event.component == OUT_OF_DEPS_MUTATOR_NAME


async def test_the_out_of_deps_event_carries_a_present_zero_spend_with_a_non_empty_counted_by(
    store_root,
):
    parsed, scheduled, touches = await _run_fixture_and_synthesize_mutator_touches(store_root)
    node_by_id = {node.node_id: node for node in scheduled["nodes"]}

    [event] = _mach11_events(parsed, touches, node_by_id)

    assert event.spend is not None
    assert event.spend.prompt_tokens == 0
    assert event.spend.completion_tokens == 0
    assert event.spend.call_count == 0
    assert event.spend.counted_by  # present and non-empty ("none" — no LLM call in this fixture)


async def test_the_out_of_deps_events_outcome_is_a_member_of_the_declared_closed_vocabulary(
    store_root,
):
    parsed, scheduled, touches = await _run_fixture_and_synthesize_mutator_touches(store_root)
    node_by_id = {node.node_id: node for node in scheduled["nodes"]}

    [event] = _mach11_events(parsed, touches, node_by_id)

    assert event.outcome in ("completed", "halted", "failed")


def test_constructing_a_seam_event_with_an_outcome_outside_the_declared_set_raises_validation_error():
    with pytest.raises(pydantic.ValidationError):
        SeamEvent(component=OUT_OF_DEPS_MUTATOR_NAME, spend=None, outcome="not-a-real-outcome")


async def test_the_event_carries_no_node_position_wiring_id_or_instance_hash(store_root):
    parsed, scheduled, touches = await _run_fixture_and_synthesize_mutator_touches(store_root)
    node_by_id = {node.node_id: node for node in scheduled["nodes"]}

    [event] = _mach11_events(parsed, touches, node_by_id)

    dumped = event.model_dump()
    assert set(dumped.keys()) == {"component", "spend", "outcome"}
    assert "mut-out-of-deps" not in dumped["component"]
    for node in scheduled["nodes"]:
        assert node.instance_hash not in str(dumped)
        assert node.node_id != dumped["component"]


async def test_accounted_store_keys_reads_the_deps_own_resolved_part_effects(store_root):
    parsed, _scheduled, _touches = await _run_fixture_and_synthesize_mutator_touches(store_root)

    assert _accounted_store_keys(parsed, "mut-in-deps") == {"kv"}
    assert _accounted_store_keys(parsed, "mut-out-of-deps") == set()


async def test_the_fallback_spend_for_a_touched_but_untraced_node_uses_a_distinct_unknown_sentinel(
    store_root,
):
    """WR-02: a node_id present in `touches` but absent from `node_by_id` (this run's own trace
    never observed it, despite a recorded touch) must report a spend visibly distinct from a real,
    honestly-reported zero-count "none" entry — never a fabricated-looking "none" a reader could
    mistake for "this participant genuinely spent zero tokens" (D-08)."""
    parsed, _scheduled, touches = await _run_fixture_and_synthesize_mutator_touches(store_root)

    [event] = _mach11_events(parsed, touches, node_by_id={})

    assert event.spend is not None
    assert event.spend.counted_by == "unknown"
    assert event.spend.counted_by != "none"


# --------------------------------------------------------------------------------------------
# 05-03-PLAN.md Task 2: the real deleting part — the first non-fixture mutates_store part MACH-11
# ever correlates. Unlike the fixture mutators above, lightrag/full-delete@0.1.0's kind is
# "opaque" (subprocess placement, hosted given a positive ceiling), so it completes real dispatch
# under the current runner — no D-08 workaround is needed here.
# --------------------------------------------------------------------------------------------

_STUB_DRIVER = Path(__file__).resolve().parents[1] / "fixtures" / "v1_corpus_driver_stub.py"


def _make_stub_full_delete_body(*, timeout: float, stub_status: str = "success"):
    async def _body(ctx: NodeContext) -> dict[str, object]:
        config = ctx.config or {}
        payload: dict[str, object] = {
            "doc_id": config.get("doc_id"),
            "delete_llm_cache": bool(config.get("delete_llm_cache", False)),
            "_stub_status": stub_status,
        }
        result = await asyncio.to_thread(
            run_corpus_op,
            "delete",
            payload,
            timeout=timeout,
            interpreter=Path(sys.executable),
            driver_script=_STUB_DRIVER,
        )

        if result.get("status") == "success":
            ctx.record_store_touch("graph")
            ctx.record_store_touch("vector")
            ctx.record_store_touch("kv")

        return {**result, "tokens": TokenAccounting(counted_by="unbudgetable")}

    return _body


async def _run_real_delete_part_wiring(store_root, *, stub_status: str = "success"):
    """Real ``parse_wiring`` + real ``run_wiring`` (with a real recorder) over a one-node wiring
    naming a test-local variant of the production ``lightrag/full-delete@0.1.0`` Part — same name,
    effects, structural_depth, artifact_scope and (a copy of) the admission record, body pointed
    at the stub driver, exactly mirroring ``test_full_ingest.py``'s own test-local-variant pattern.
    """
    admission = dataclasses.replace(
        LIGHTRAG_FULL_DELETE_PART.admission, wall_clock_ceiling_seconds=5.0
    )
    body = _make_stub_full_delete_body(timeout=5.0, stub_status=stub_status)
    test_part = dataclasses.replace(LIGHTRAG_FULL_DELETE_PART, body=body, admission=admission)
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(test_part)

    wiring = {
        "wiring_id": "test-delete-mach11",
        "nodes": {
            "full-delete": {
                "component": test_part.name_at_version,
                "kind": "opaque",
                "effects": test_part.effects,
                "config": {"doc_id": "deadbeef"},
                "deps": [],
            }
        },
        "provides": ["full-delete"],
    }
    parsed = parse_wiring(wiring, registry)
    assert parsed.report.ok, [v.code for v in parsed.report.violations]

    touches: list[tuple[str, str, str]] = []

    def recorder(node_id: str, kind: str, key: str) -> None:
        touches.append((node_id, kind, key))

    scheduled = await run_wiring(
        parsed,
        registry,
        stores={},
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
        recorder=recorder,
    )

    return parsed, scheduled, touches


async def test_the_real_deleting_part_produces_exactly_one_seam_event(store_root):
    parsed, scheduled, touches = await _run_real_delete_part_wiring(store_root)
    node_by_id = {node.node_id: node for node in scheduled["nodes"]}

    events = _mach11_events(parsed, touches, node_by_id)

    assert len(events) == 1


async def test_the_real_deleting_events_component_equals_the_registered_name_at_version_not_a_node_id(
    store_root,
):
    parsed, scheduled, touches = await _run_real_delete_part_wiring(store_root)
    node_by_id = {node.node_id: node for node in scheduled["nodes"]}

    [event] = _mach11_events(parsed, touches, node_by_id)

    assert event.component == LIGHTRAG_FULL_DELETE_PART.name_at_version
    assert event.component != "full-delete"


async def test_the_real_deleting_events_spend_carries_a_real_value_not_the_unknown_sentinel(
    store_root,
):
    parsed, scheduled, touches = await _run_real_delete_part_wiring(store_root)
    node_by_id = {node.node_id: node for node in scheduled["nodes"]}

    [event] = _mach11_events(parsed, touches, node_by_id)

    assert event.spend is not None
    assert event.spend.counted_by == "unbudgetable"
    assert event.spend.counted_by != "unknown"


async def test_the_real_deleting_nodes_recorded_touches_carry_the_node_reported_kind(store_root):
    _parsed, _scheduled, touches = await _run_real_delete_part_wiring(store_root)

    node_touches = [(node_id, kind, key) for node_id, kind, key in touches if node_id == "full-delete"]
    assert node_touches, "no touch recorded for the full-delete node"
    for _node_id, kind, _key in node_touches:
        assert kind == TOUCH_KIND_NODE_REPORTED
