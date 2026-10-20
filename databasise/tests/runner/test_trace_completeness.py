"""WIRE-10 (D-13, D-26): ``run_wiring`` returns exactly one ``NodeTrace`` per node of the parsed
wiring, each with a status (completed, failed, cancelled, not-scheduled); a failed node carries its
measured wall time; nothing a node body or a post-dispatch step does escapes the run.

Every test builds a ``ParsedWiring`` directly (the pattern ``test_scheduler.py`` documents) so each
can register a purpose-built part body. New names are read with ``getattr`` and exceptions are
captured, so the tests collect and fail by assertion on code that predates the fix.
"""

from __future__ import annotations

import asyncio

from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.runner import scheduler
from databasise.validator.errors import ValidationReport
from databasise.validator.parse import ParsedWiring


def _part(name: str, body, effects: list[str] | None = None) -> Part:
    return Part(
        name_at_version=f"test/{name}@1.0.0",
        kind="passthrough",
        structural_depth="stage",
        effects=effects or [],
        upstream_ref=None,
        body=body,
    )


async def _ok(ctx: NodeContext):
    return {"node": ctx.node_id}


def _slow_fail(delay_s: float):
    async def body(ctx: NodeContext):
        await asyncio.sleep(delay_s)
        raise RuntimeError("deliberate failure")

    return body


def _wiring(bodies: dict, deps: dict, effects: dict | None = None, config: dict | None = None) -> ParsedWiring:
    parts = {
        node_id: _part(node_id, body, (effects or {}).get(node_id)) for node_id, body in bodies.items()
    }
    nodes = {
        node_id: WiringNode(
            component=parts[node_id].name_at_version,
            kind="passthrough",
            config=(config or {}).get(node_id),
            deps=list(deps[node_id]),
        )
        for node_id in bodies
    }
    return ParsedWiring(
        nodes=nodes,
        parts=parts,
        deps={node_id: tuple(deps[node_id]) for node_id in bodies},
        node_order=tuple(sorted(nodes)),
        report=ValidationReport(),
    )


async def _run(parsed: ParsedWiring) -> dict:
    return await scheduler.run_wiring(
        parsed, PartRegistry(), {}, determinism_setting="cache-bypassed", concurrency_setting="sequential"
    )


def _statuses(result: dict) -> dict[str, str | None]:
    return {trace.node_id: getattr(trace, "status", None) for trace in result["nodes"]}


async def test_every_node_gets_one_trace_with_its_status():
    parsed = _wiring(
        {"a-fail": _slow_fail(0.06), "z-sibling": _ok, "mid": _ok, "last": _ok},
        {"a-fail": (), "z-sibling": (), "mid": ("a-fail", "z-sibling"), "last": ("mid",)},
    )

    result = await _run(parsed)

    assert sorted(_statuses(result)) == sorted(parsed.nodes)
    assert len(result["nodes"]) == len(parsed.nodes)
    assert _statuses(result) == {
        "a-fail": "failed",
        "z-sibling": "not-scheduled",
        "mid": "not-scheduled",
        "last": "not-scheduled",
    }
    assert result["partial"] is True


async def test_a_failed_node_reports_its_measured_wall_time():
    parsed = _wiring({"only": _slow_fail(0.06)}, {"only": ()})

    result = await _run(parsed)

    failed = next(trace for trace in result["nodes"] if trace.node_id == "only")
    assert failed.wall_clock_ms >= 50


async def test_a_failure_in_the_last_batch_keeps_earlier_nodes_completed():
    parsed = _wiring(
        {"first": _ok, "second": _ok, "tail-a": _slow_fail(0.0), "tail-b": _ok},
        {"first": (), "second": (), "tail-a": ("first", "second"), "tail-b": ("first", "second")},
    )

    result = await _run(parsed)

    assert _statuses(result) == {
        "first": "completed",
        "second": "completed",
        "tail-a": "failed",
        "tail-b": "not-scheduled",
    }


async def test_a_one_node_failing_wiring_gives_one_failed_trace():
    parsed = _wiring({"only": _slow_fail(0.0)}, {"only": ()})

    result = await _run(parsed)

    assert [(trace.node_id, getattr(trace, "status", None)) for trace in result["nodes"]] == [("only", "failed")]


async def test_traces_list_dispatched_nodes_then_not_scheduled_nodes_by_id():
    parsed = _wiring(
        {"a": _ok, "m": _slow_fail(0.0), "d-late": _ok, "b-late": _ok, "zz": _ok},
        {"a": (), "m": (), "d-late": ("a",), "b-late": ("m",), "zz": ("d-late",)},
    )

    result = await _run(parsed)

    assert [trace.node_id for trace in result["nodes"]] == ["a", "m", "b-late", "d-late", "zz"]
    assert [getattr(trace, "status", None) for trace in result["nodes"]] == [
        "completed",
        "failed",
        "not-scheduled",
        "not-scheduled",
        "not-scheduled",
    ]
