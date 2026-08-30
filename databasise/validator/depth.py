"""Effective depth (the taint rule) and execution_mode derivation — CONTRACT.md §3.

Depth is computed by the validator, never declared. Effective depth is the minimum over a node's
own structural depth and the effective depth of every transitive dep — the taint rule — ordered
``opaque < evidence < stage`` (CONTRACT §3: "Effective depth is the minimum over a node's
transitive deps"). For the tracer this module implements the acyclic case with
``graphlib.TopologicalSorter.static_order()``; plan 01-03 replaces the ordering source with a
Tarjan SCC condensation for the cycle-safe general case (spike 005's measured-sound taint rule,
D-01/D-03). The seam plan 01-03 fills is exactly where the order comes from
(``_topological_order`` below) — the min-reduce itself (the loop body in ``effective_depth``)
does not change.
"""

from __future__ import annotations

import graphlib

from databasise.validator.parse import ParsedWiring

_DEPTH_RANK: dict[str, int] = {"opaque": 0, "evidence": 1, "stage": 2}
_RANK_DEPTH: dict[int, str] = {rank: depth for depth, rank in _DEPTH_RANK.items()}

# Effects requiring containment stronger than in-process hosting, per CONTRACT §3: "only pure,
# non-iterative nodes MAY be hosted in-process." A node's own machine-owned store reads/writes
# (kv/vector/graph/lexical/blob, self_storage) stay in-process — they are internal to the trusted
# runtime, not an external side effect crossing a process boundary. Everything below crosses a
# real external boundary (LLM/rerank/embedding API, network, filesystem, or an in-place store
# overwrite outside the artifact-production shape) and is refused by name at the runner (D-08)
# until a later phase builds the real hosting for it.
_REQUIRES_CONTAINMENT: frozenset[str] = frozenset(
    {"calls_llm", "calls_rerank", "calls_embedding", "net", "fs", "mutates_store"}
)


def _topological_order(parsed: ParsedWiring) -> list[str]:
    return list(graphlib.TopologicalSorter(dict(parsed.deps)).static_order())


def effective_depth(parsed: ParsedWiring) -> dict[str, str]:
    """Minimum over transitive deps, per node. Raises ``graphlib.CycleError`` for cyclic input
    — the caller (runner/scheduler.py) is responsible for reporting the cycle as data rather than
    letting the exception propagate, per the wiring-spec's cycle-as-data rule.
    """
    order = _topological_order(parsed)
    result: dict[str, str] = {}
    for node_id in order:
        own_rank = _DEPTH_RANK[parsed.parts[node_id].structural_depth]
        dep_ranks = [_DEPTH_RANK[result[dep]] for dep in parsed.deps.get(node_id, ())]
        result[node_id] = _RANK_DEPTH[min([own_rank, *dep_ranks])]
    return result


def derive_execution_mode(effects: list[str], kind: str) -> str:
    """Derived from declared effects, never requested by the component (CONTRACT §3).

    ``fixpoint`` nodes are iterative by construction and MUST NOT be hosted in-process (CONTRACT
    §2: "Iterative components MUST be hosted as fixpoint nodes; the executor, not the component,
    owns every loop and its halt condition"). Every other node is in-process unless it declares
    an effect in ``_REQUIRES_CONTAINMENT``.
    """
    if kind == "fixpoint":
        return "subprocess"
    if any(effect in _REQUIRES_CONTAINMENT for effect in effects):
        return "subprocess"
    return "in-process"
