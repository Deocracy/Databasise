"""WIRE-13 (13-07, D-15): the MACH-11 seam event reports a mutating node's outcome truthfully.

``failed`` is a mutating node whose execution raised (the scheduler stamps it ``status="failed"``,
``budget_state="halted"`` and a ``cross_process_failure_cause``); ``halted`` stays for a node that
completed and whose budget halted; otherwise ``completed``. A run with no mutating node emits no
event, and an ingest wiring holding a ``mutates_store`` part returns an ``IngestJob`` carrying one
(met since LRAG-03, pinned here). The ``component`` leg follows in 13-13.

Outcomes are read with ``getattr``/``try-except`` so a pre-fix run fails by ``AssertionError``.
"""

from __future__ import annotations

import copy
import dataclasses

from databasise.parts.registry import Part, PartRegistry
from databasise.parts_core.declared_only import LIGHTRAG_FULL_INGEST_PART
from databasise.runner.scheduler import TOUCH_KIND_OBSERVED
from databasise.runner.trace import NodeTrace, TokenAccounting
from databasise.seam import engine as engine_module
from databasise.seam.engine import Databasise, _mach11_events
from databasise.seam.selectors import Selector
from databasise.validator.parse import parse_wiring

_MUTATOR = "test/seam-events-mutator@1.0.0"
_EFFECTS = ["mutates_store", "writes_kv"]
_NODE = "mutator"


def _mutator_part(body=None) -> Part:
    async def _body(ctx):
        return {"node_id": ctx.node_id}

    return Part(
        name_at_version=_MUTATOR,
        kind="mutator",
        structural_depth="stage",
        effects=list(_EFFECTS),
        upstream_ref=None,
        body=body or _body,
    )


def _parsed_one_node(part: Part):
    registry = PartRegistry()
    registry.register(part)
    wiring = {
        "wiring_id": "seam-events-fixture",
        "nodes": {_NODE: {"component": part.name_at_version, "kind": part.kind, "effects": part.effects, "deps": []}},
        "provides": [],
    }
    return parse_wiring(wiring, registry)


def _trace(*, status: str, budget_state: str, cause: str | None) -> NodeTrace:
    return NodeTrace(
        node_id=_NODE,
        instance_hash="h",
        depth="stage",
        effective_depth="stage",
        wall_clock_ms=0,
        cache_hit=None,
        guards_fired=[],
        budget_state=budget_state,
        realised_budget_share=0.0,
        cross_process_failure_cause=cause,
        resumable=False,
        tokens=TokenAccounting(counted_by="none"),
        status=status,
    )


def _outcomes(node_trace: NodeTrace | None) -> list[str]:
    parsed = _parsed_one_node(_mutator_part())
    node_by_id = {_NODE: node_trace} if node_trace is not None else {}
    touches = [(_NODE, TOUCH_KIND_OBSERVED, "kv")]
    return [event.outcome for event in _mach11_events(parsed, touches, node_by_id)]


def test_an_emitted_event_names_the_capability():
    completed = _trace(status="completed", budget_state="within_budget", cause=None)
    parsed = _parsed_one_node(_mutator_part())

    events = _mach11_events(parsed, [(_NODE, TOUCH_KIND_OBSERVED, "kv")], {_NODE: completed})

    assert [event.component for event in events] == ["mutates_store"]
    assert "@" not in events[0].component and "/" not in events[0].component


def test_events_come_in_recorded_touch_order_one_per_mutating_node():
    registry = PartRegistry()
    registry.register(_mutator_part())
    wiring = {
        "wiring_id": "seam-events-order",
        "nodes": {
            name: {"component": _MUTATOR, "kind": "mutator", "effects": list(_EFFECTS), "deps": []}
            for name in ("b_node", "a_node")
        },
        "provides": [],
    }
    parsed = parse_wiring(wiring, registry)
    touches = [
        ("b_node", TOUCH_KIND_OBSERVED, "kv"),
        ("a_node", TOUCH_KIND_OBSERVED, "kv"),
        ("b_node", TOUCH_KIND_OBSERVED, "kv"),
    ]
    traces = {
        name: _trace(status="completed", budget_state="within_budget", cause=None) for name in ("b_node", "a_node")
    }
    traces["b_node"] = dataclasses.replace(traces["b_node"], node_id="b_node")
    traces["a_node"] = dataclasses.replace(traces["a_node"], node_id="a_node", budget_state="halted")

    outcomes = [event.outcome for event in _mach11_events(parsed, touches, traces)]

    assert outcomes == ["completed", "halted"]


def test_a_mutating_node_that_raised_reports_failed():
    failed = _trace(status="failed", budget_state="halted", cause="NodeExecutionError: X")

    assert _outcomes(failed) == ["failed"]


def test_a_budget_halted_mutating_node_reports_halted():
    halted = _trace(status="completed", budget_state="halted", cause=None)

    assert _outcomes(halted) == ["halted"]


def test_a_completed_mutating_node_reports_completed():
    completed = _trace(status="completed", budget_state="within_budget", cause=None)

    assert _outcomes(completed) == ["completed"]


def test_a_run_with_no_mutating_node_emits_no_event():
    registry = PartRegistry()
    wiring = {
        "wiring_id": "seam-events-plain",
        "nodes": {_NODE: {"component": "core/passthrough@1.0.0", "kind": "passthrough", "effects": [], "deps": []}},
        "provides": [],
    }
    parsed = parse_wiring(wiring, registry)
    touches = [(_NODE, TOUCH_KIND_OBSERVED, "kv")]
    node_by_id = {_NODE: _trace(status="completed", budget_state="within_budget", cause=None)}

    assert _mach11_events(parsed, touches, node_by_id) == []


async def test_an_ingest_with_a_mutating_part_returns_one_seam_event(store_root, monkeypatch):
    async def _body(ctx):
        ctx.record_store_touch("kv")
        return {"track_id": "t", "enqueued": 1, "tokens": TokenAccounting(counted_by="none")}

    part = dataclasses.replace(LIGHTRAG_FULL_INGEST_PART, name_at_version=_MUTATOR, body=_body, admission=dataclasses.replace(LIGHTRAG_FULL_INGEST_PART.admission, part_name_at_version=_MUTATOR))
    wiring = {
        "wiring_id": "seam-events-ingest",
        "nodes": {
            "ing": {"component": _MUTATOR, "kind": part.kind, "effects": list(part.effects), "deps": []},
        },
        "provides": ["ing"],
        "consumes_documents": ["ing"],
    }
    monkeypatch.setattr(engine_module, "_corpus_wiring", lambda _query_wiring, _op: copy.deepcopy(wiring))
    registry = engine_module.default_registry()
    registry.register(part)
    engine = Databasise(store_root=store_root, workspace="seam-events-ingest", registry=registry, clients={})

    from databasise.seam.corpus import IngestDocument

    job = None
    caught = None
    try:
        job = await engine.ingest(
            IngestDocument(document_id="se-doc", text="hello"), Selector(capability=["reads_graph", "reads_kv"])
        )
    except Exception as exc:  # noqa: BLE001 - asserted below
        caught = exc

    assert caught is None, repr(caught)
    assert len(getattr(job, "seam_events", None) or []) == 1
