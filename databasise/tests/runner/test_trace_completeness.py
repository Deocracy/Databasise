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
from databasise.runner.trace import TokenAccounting
from databasise.seam import promotion
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


async def _captured_run(parsed: ParsedWiring) -> tuple[dict | None, BaseException | None]:
    try:
        return await _run(parsed), None
    except BaseException as exc:  # noqa: BLE001 - the tests assert on what escaped
        return None, exc


async def test_malformed_token_fields_fail_that_node_and_keep_the_siblings():
    async def bad(ctx: NodeContext):
        return {"tokens": TokenAccounting(prompt_tokens="x")}

    parsed = _wiring({"early": _ok, "zbad": bad}, {"early": (), "zbad": ()}, effects={"zbad": ["calls_llm"]})

    result, escaped = await _captured_run(parsed)

    assert escaped is None, type(escaped).__name__
    assert _statuses(result) == {"early": "completed", "zbad": "failed"}
    assert type(result["node_exceptions"]["zbad"]).__name__ == "TypeError"
    assert result["partial"] is True


async def test_an_output_whose_comparison_raises_fails_that_node():
    class Bomb:
        def __ne__(self, other):
            raise ValueError("comparison exploded")

    async def body(ctx: NodeContext):
        return Bomb()

    guard = {"name": "g", "evaluating_node": "guarded", "value_when_not_fired": 0, "granularity": "per-query"}
    parsed = _wiring({"guarded": body}, {"guarded": ()}, config={"guarded": {"guards": [guard]}})

    result, escaped = await _captured_run(parsed)

    assert escaped is None, type(escaped).__name__
    assert _statuses(result) == {"guarded": "failed"}
    assert type(result["node_exceptions"]["guarded"]).__name__ == "ValueError"


async def test_a_body_that_raises_cancelled_error_is_traced_cancelled():
    async def body(ctx: NodeContext):
        raise asyncio.CancelledError()

    parsed = _wiring({"only": body}, {"only": ()})

    result, escaped = await _captured_run(parsed)

    assert escaped is None, type(escaped).__name__
    assert _statuses(result) == {"only": "cancelled"}
    assert result["stop_reason"] == "cancelled"
    assert result["partial"] is True


async def test_a_real_cancellation_of_the_run_still_propagates():
    async def body(ctx: NodeContext):
        await asyncio.sleep(5)

    run = asyncio.ensure_future(_run(_wiring({"only": body}, {"only": ()})))
    await asyncio.sleep(0.05)
    run.cancel()

    try:
        await run
        propagated = False
    except asyncio.CancelledError:
        propagated = True
    assert propagated


async def test_failure_reasons_are_closed_codes():
    failed = await _run(_wiring({"only": _slow_fail(0.0)}, {"only": ()}))
    refused = await _run(_wiring({"net-node": _ok}, {"net-node": ()}, effects={"net-node": ["net"]}))

    assert (failed["stop_reason"], failed["degradation_reason"]) == ("node_failed", "node_failed")
    assert (refused["stop_reason"], refused["degradation_reason"]) == ("placement_refused", "placement_refused")


def test_a_partial_run_is_not_matched_by_its_dispatched_set():
    record = {
        "nodes": [
            {"node_id": "done", "status": "completed"},
            {"node_id": "later", "status": "not-scheduled"},
            {"node_id": "broke", "status": "failed"},
            {"node_id": "legacy"},  # persisted before Phase 13: no status field
        ]
    }

    assert promotion._dispatched_node_ids(record) == frozenset({"done", "legacy"})
