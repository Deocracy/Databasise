"""Effective depth (the taint rule) and execution_mode derivation — CONTRACT.md §3.

Depth is computed by the validator, never declared. Effective depth is the minimum over a node's
own structural depth and the effective depth of every transitive dep — the taint rule — ordered
``opaque < evidence < stage`` (CONTRACT §3: "Effective depth is the minimum over a node's
transitive deps"). Depth is computed over a Tarjan SCC condensation (``validator/cycles.py``),
not a direct topological sort of ``deps`` itself, so a cyclic wiring — legal content per
CONTRACT §1 — still resolves a defined depth for every node rather than raising: every member of
a cycle collapses into one condensed node and therefore receives that condensed node's depth,
which is exactly what the taint rule's own definition implies for mutually reachable nodes
(01-RESEARCH.md "Pattern 2: SCC-condensation depth computation", D-01/D-03).
"""

from __future__ import annotations

import graphlib
from typing import TYPE_CHECKING

from databasise.validator.cycles import condensation, strongly_connected_components

if TYPE_CHECKING:
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


def effective_depth(parsed: ParsedWiring) -> dict[str, str]:
    """Minimum over transitive deps, per node, computed over the SCC condensation of
    ``parsed.deps`` so cyclic input resolves a defined depth for every node instead of raising.

    Every member of one SCC receives that SCC's depth: mutually reachable nodes resolve to the
    same effective depth under the taint rule's own definition (min over transitive deps, and
    each cycle member is transitively a dep of every other member).
    """
    deps_as_sets = {node_id: set(dep_tuple) for node_id, dep_tuple in parsed.deps.items()}
    sccs = strongly_connected_components(deps_as_sets)
    cond = condensation(deps_as_sets, sccs)
    order = list(graphlib.TopologicalSorter(cond).static_order())  # always acyclic by construction

    scc_of: dict[str, int] = {}
    for i, component in enumerate(sccs):
        for node_id in component:
            scc_of[node_id] = i

    scc_depth: dict[int, int] = {}
    for scc_id in order:
        own_ranks = [
            _DEPTH_RANK[parsed.parts[node_id].structural_depth] for node_id in sccs[scc_id]
        ]
        dep_ranks = [scc_depth[dep_scc_id] for dep_scc_id in cond[scc_id]]
        scc_depth[scc_id] = min(own_ranks + dep_ranks)

    return {node_id: _RANK_DEPTH[scc_depth[scc_of[node_id]]] for node_id in parsed.nodes}


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
