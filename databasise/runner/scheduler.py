"""Structured-concurrency runner.

Claude's Discretion (01-02-PLAN.md ``<decisions_recorded_here>``): ``graphlib.TopologicalSorter``
for readiness bookkeeping plus one ``asyncio.TaskGroup`` per ready batch. No orchestrator, no
external scheduler, no metadata DB.

D-09 (one-way door, confirmed 01-01-PLAN.md Task 4, recorded in 01-01-SUMMARY.md): **option-a**
selected — intra-node concurrency is bounded by a per-node ``asyncio.Semaphore``, sized from that
node's own declared ``config.max_concurrency`` (default 1 when absent), created fresh per node
per run and NEVER shared across nodes. D-11 rejects a process-wide concurrency cap explicitly:
one arm's fan-out must never throttle an unrelated arm beside it, contaminating Phase 6's
side-by-side comparison — so this module defines no module-level singleton, manager object, or
global limits dict. The v1 shape this rejects lives at ``v1/lightrag/kg/shared_storage.py:66``
(``_manager``), ``:111`` (``_global_concurrency_limits``), and ``:175`` (``class UnifiedLock``);
none of it is imported or re-derived here (D-11/D-14).
"""

from __future__ import annotations

import asyncio
import graphlib
import time
from typing import Any

from databasise.identity.canon import config_hash
from databasise.identity.env import environment_hash
from databasise.identity.instance import instance_hash
from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext
from databasise.runner.trace import NodeTrace, TokenAccounting
from databasise.validator.depth import derive_execution_mode, effective_depth
from databasise.validator.parse import ParsedWiring

# Transient store-write members plus writes_artifact/mutates_store: per D-13's rule, a node
# carrying one of these has mutated a store on the completed portion of the run, so it can never
# count as a safe resume boundary regardless of any determinism stamp.
_STORE_MUTATING_EFFECTS = frozenset(
    {
        "writes_artifact",
        "mutates_store",
        "writes_kv",
        "writes_vector",
        "writes_graph",
        "writes_lexical",
    }
)


class UnsupportedExecutionModeError(RuntimeError):
    """A node's derived execution_mode is not yet hosted. Phase 1's runner implements
    in-process only, per D-08; subprocess/confined-unit/long-lived-service are named refusals
    until Phase 5's real opaque-node admission forces the hosting to be built.
    """


def _resolve_identities(parsed: ParsedWiring) -> dict[str, dict[str, str]]:
    """Bottom-up ``(name@version, config_hash, resolved_dependency_ids)`` per node.

    ``resolved_dependency_ids`` is the sorted list of each direct dependency's OWN
    ``instance_hash`` — never the raw dependency node id, since a wiring node id is a position,
    never an identity.
    """
    env = environment_hash()  # one resolved-closure digest per run, shared across every node
    order = list(graphlib.TopologicalSorter(dict(parsed.deps)).static_order())
    identities: dict[str, dict[str, str]] = {}
    for node_id in order:
        node = parsed.nodes[node_id]
        part = parsed.parts[node_id]
        resolved_dep_ids = sorted(
            identities[dep]["instance_hash"] for dep in parsed.deps.get(node_id, ())
        )
        c_hash = config_hash(node.config or {}, env=env)
        i_hash = instance_hash(part.name_at_version, c_hash, resolved_dep_ids)
        identities[node_id] = {"config_hash": c_hash, "instance_hash": i_hash}
    return identities


async def _run_node(
    node_id: str, parsed: ParsedWiring, stores: dict[str, Any], results: dict[str, Any]
) -> tuple[Any, int]:
    node = parsed.nodes[node_id]
    part = parsed.parts[node_id]

    execution_mode = derive_execution_mode(node.effects, node.kind)
    if execution_mode != "in-process":
        raise UnsupportedExecutionModeError(
            f"node {node_id!r} derived execution_mode={execution_mode!r}; only in-process is "
            "implemented in Phase 1 (D-08)"
        )

    max_concurrency = 1
    if node.config:
        max_concurrency = int(node.config.get("max_concurrency", 1))
    semaphore = asyncio.Semaphore(max_concurrency)  # per node per run, never shared (D-09/D-11)

    inputs = {dep: results[dep] for dep in parsed.deps.get(node_id, ())}
    ctx = NodeContext(node_id=node_id, config=node.config, inputs=inputs, stores=stores)

    start = time.monotonic()
    async with semaphore:
        output = await part.body(ctx) if part.body is not None else inputs
    wall_clock_ms = int((time.monotonic() - start) * 1000)
    return output, wall_clock_ms


async def run_wiring(
    parsed: ParsedWiring,
    registry: PartRegistry,
    stores: dict[str, Any],
    *,
    determinism_setting: str,
    concurrency_setting: str,
) -> dict[str, Any]:
    """Drive readiness with ``graphlib.TopologicalSorter``; on ``graphlib.CycleError`` return the
    cycle as data under a ``cycle`` key rather than propagating the exception, because cyclic
    wirings are legal content. Each ready batch is sorted by node id before dispatch, so two runs
    of the same wiring produce the same dispatch order, then the batch runs inside one
    ``asyncio.TaskGroup``.

    ``registry`` is accepted for signature parity with the rest of this phase's call sites — this
    tracer resolves every part it needs via ``parsed.parts`` (already looked up by
    ``validator.parse.parse_wiring``) and does not re-query the registry during execution.
    ``determinism_setting``/``concurrency_setting`` are threaded through for the caller (the
    public composer in ``databasise/__init__.py``) to stamp on the run-level record; this tracer
    does not yet vary its own behaviour on either setting.
    """
    del registry, determinism_setting, concurrency_setting

    try:
        depths = effective_depth(parsed)
    except graphlib.CycleError as exc:
        return {"cycle": list(exc.args[1])}

    identities = _resolve_identities(parsed)

    ts = graphlib.TopologicalSorter(dict(parsed.deps))
    ts.prepare()

    results: dict[str, Any] = {}
    node_traces: list[NodeTrace] = []

    while ts.is_active():
        ready = sorted(ts.get_ready())
        async with asyncio.TaskGroup() as tg:
            tasks = {
                node_id: tg.create_task(_run_node(node_id, parsed, stores, results))
                for node_id in ready
            }
        for node_id, task in tasks.items():
            output, wall_clock_ms = task.result()
            results[node_id] = output
            node = parsed.nodes[node_id]
            part = parsed.parts[node_id]
            resumable = not (set(node.effects) & _STORE_MUTATING_EFFECTS)
            node_traces.append(
                NodeTrace(
                    node_id=node_id,
                    instance_hash=identities[node_id]["instance_hash"],
                    depth=part.structural_depth,
                    effective_depth=depths[node_id],
                    wall_clock_ms=wall_clock_ms,
                    cache_hit=False,  # real value: Phase 1 has no cache to hit yet
                    guards_fired=[],  # real value: no data guards declared/fired in this tracer
                    budget_state="within_budget",  # real value: no budget halt occurred
                    realised_budget_share=1.0,  # real value: no budget cap exists yet (runner/budget.py, later plan) — every node ran to completion
                    cross_process_failure_cause=None,  # real value: in-process only, no cross-process boundary crossed
                    resumable=resumable,
                    tokens=TokenAccounting(),  # real zeros: no LLM/embedding/rerank call in this tracer
                )
            )
            ts.done(node_id)

    return {"results": results, "nodes": node_traces}
