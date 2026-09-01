"""``NodeContext.clients`` / the scheduler's ``_ScopedClientsView`` threading (D-06, 03-01-PLAN.md
Task 4). Mirrors ``tests/runner/test_scheduler.py``'s own pattern: each test constructs a
``ParsedWiring`` directly (bypassing ``validator.parse.parse_wiring``, out of this plan's lane).
"""

from __future__ import annotations

from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.runner import scheduler
from databasise.validator.errors import ValidationReport
from databasise.validator.parse import ParsedWiring


def _wiring(nodes: dict, parts: dict, deps: dict) -> ParsedWiring:
    return ParsedWiring(
        nodes=nodes,
        parts=parts,
        deps=deps,
        node_order=tuple(sorted(nodes)),
        report=ValidationReport(),
    )


async def _run(parsed: ParsedWiring, clients: dict | None = None) -> dict:
    return await scheduler.run_wiring(
        parsed,
        PartRegistry(),
        {},
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
        clients=clients,
    )


def _llm_reading_part(name: str = "test/llm-reader@1.0.0") -> Part:
    async def body(ctx: NodeContext):
        return {"got": ctx.clients["llm"]}

    return Part(
        name_at_version=name,
        kind="stage",
        structural_depth="stage",
        effects=["calls_llm"],
        upstream_ref=None,
        body=body,
    )


async def test_1_a_part_declaring_calls_llm_reading_ctx_clients_llm_receives_the_wired_handle():
    sentinel = object()
    part = _llm_reading_part()
    node = WiringNode(component="test/llm-reader@1.0.0", kind="stage", deps=[])
    parsed = _wiring({"n1": node}, {"n1": part}, {"n1": ()})

    result = await _run(parsed, clients={"llm": sentinel})

    assert result["partial"] is False
    assert result["results"]["n1"]["got"] is sentinel


async def test_2_a_part_declaring_only_reads_kv_reading_ctx_clients_llm_is_refused():
    """The part's own declared effects carry no ``calls_llm`` — reaching ``ctx.clients["llm"]``
    must raise ``UndeclaredEffectError`` at the part boundary, surfaced by the scheduler as a
    traced partial run (CONTRACT §9 — batch-internal failures are never a raised exception out of
    ``run_wiring``, see ``runner/scheduler.py``'s own module docstring).
    """

    async def body(ctx: NodeContext):
        return {"got": ctx.clients["llm"]}

    part = Part(
        name_at_version="test/kv-only@1.0.0",
        kind="stage",
        structural_depth="stage",
        effects=["reads_kv"],
        upstream_ref=None,
        body=body,
    )
    node = WiringNode(component="test/kv-only@1.0.0", kind="stage", deps=[])
    parsed = _wiring({"n1": node}, {"n1": part}, {"n1": ()})

    result = await _run(parsed, clients={"llm": object()})

    assert result["partial"] is True
    trace = next(n for n in result["nodes"] if n.node_id == "n1")
    assert "undeclared effect" in trace.cross_process_failure_cause
    assert "calls_llm" in trace.cross_process_failure_cause


async def test_3_a_declared_calls_llm_with_no_llm_client_wired_is_refused_by_name():
    part = _llm_reading_part("test/llm-reader-unwired@1.0.0")
    node = WiringNode(component="test/llm-reader-unwired@1.0.0", kind="stage", deps=[])
    parsed = _wiring({"n1": node}, {"n1": part}, {"n1": ()})

    result = await _run(parsed, clients={})  # no "llm" entry

    assert result["partial"] is True
    trace = next(n for n in result["nodes"] if n.node_id == "n1")
    assert "calls_llm" in trace.cross_process_failure_cause
    assert "llm" in trace.cross_process_failure_cause


async def test_4_a_run_with_no_clients_argument_at_all_behaves_exactly_as_before():
    """A part that never touches ``ctx.clients`` must run unaffected whether or not a ``clients``
    mapping is passed at all — the whole existing suite (every part predating D-06) stays green.
    """

    async def body(ctx: NodeContext):
        return {"x": ctx.inputs}

    part = Part(
        name_at_version="test/no-clients@1.0.0",
        kind="stage",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=body,
    )
    node = WiringNode(component="test/no-clients@1.0.0", kind="stage", deps=[])
    parsed = _wiring({"n1": node}, {"n1": part}, {"n1": ()})

    result = await scheduler.run_wiring(
        parsed,
        PartRegistry(),
        {},
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
        # `clients` omitted entirely.
    )

    assert result["partial"] is False
    assert result["results"]["n1"] == {"x": {}}
