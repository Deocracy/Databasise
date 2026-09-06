"""``lightrag/entity-hydrate-expand`` (base wiring position 4 of 18) — hydrates ``entity-lookup``'s
seed items from the graph store and expands each hydrated entity to its one-hop neighbour edges.
Ported by search from ``v1/lightrag/operate.py``'s ``_get_node_data`` (seed hydration: node lookup
plus degree, combined with the vector-search rank) and ``_find_most_related_edges_from_entities``
(neighbour expansion: batch edge lookup, deduplicated by canonical endpoint pair, ranked by
``edge_degree`` = the sum of both endpoints' own node degree — v1's own ``edge_degree`` shape,
``v1/lightrag/kg/cozo_impl.py:336``, computed here as two ``node_degree`` calls rather than adding
a batch method, per 03-RESEARCH.md Open Question 1's loop-not-batch answer).

Reads only ``ctx.stores["graph"]`` (``get_node``/``node_degree``/``get_node_edges`` — the read
method 03-05-PLAN.md Task 1 added). Never reaches ``ctx.stores["vector"]`` or ``ctx.stores["kv"]``:
this node's declared effects are ``reads_graph`` only, and the scheduler's deny-by-default view
raises ``UndeclaredEffectError`` on any attempt to reach either.

A seed whose node is absent from the graph is reported in ``missing_seeds`` rather than silently
dropped (v1's own ``_get_node_data`` merely logs a warning and filters it out — this decomposition
makes that gap observable instead of silent, since a shorter result set here would otherwise read
as a genuine retrieval difference in plan 03-07's parity comparison). A seed that is itself
malformed (missing the required ``entity_name`` key) follows the same rule: it is reported in
``missing_seeds`` with a diagnostic naming the missing field, rather than raising and halting the
whole node's batch. Every hydrated or expanded item carries ``derived_from`` naming the seed ref (or
entity name) it was computed from — a hydration that re-projects a seed into a wider shape is
authoring, not pass-through (CONTRACT §4).

Emits two lists, both consumed by plan 03-06's join nodes: ``entities`` (the hydrated seeds) and
``relations`` (the expanded one-hop edges) — ``entity-hydrate-expand``'s own edge-expansion
sub-step emits relations too, which is why the base wiring's ``join-relations`` node depends on
this node as well as ``relation-hydrate-expand`` (see ``databasise/wirings/lightrag/arm-local.json-
patch.json``'s own guard note on this crossover).
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/entity-hydrate-expand@0.1.0"


async def _entity_hydrate_expand_body(ctx: NodeContext) -> dict[str, Any]:
    seeds = list(ctx.inputs["entity-lookup"]["items"])
    graph = ctx.stores["graph"]

    hydrated: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for seed in seeds:
        raw_entity_name = seed.get("entity_name")
        if raw_entity_name is None:
            missing.append(
                {
                    "entity_name": None,
                    "missing": True,
                    "malformed_seed": True,
                    "diagnostic": "seed missing required field 'entity_name'",
                    "derived_from": [seed.get("id")],
                }
            )
            continue
        entity_name = str(raw_entity_name)
        node = await graph.get_node(entity_name)
        if node is None:
            missing.append(
                {"entity_name": entity_name, "missing": True, "derived_from": [seed.get("id")]}
            )
            continue
        degree = await graph.node_degree(entity_name)
        hydrated.append(
            {**node, "entity_name": entity_name, "rank": degree, "derived_from": [seed.get("id")]}
        )

    seen_edges: set[tuple[str, str]] = set()
    relations: list[dict[str, Any]] = []
    for entity in hydrated:
        entity_name = entity["entity_name"]
        for edge in await graph.get_node_edges(entity_name):
            key = (edge["src"], edge["tgt"])  # already canonically ordered by the store
            if key in seen_edges:
                continue
            seen_edges.add(key)
            attrs = dict(edge["attrs"])
            attrs.setdefault("weight", 1.0)
            edge_degree = await graph.node_degree(key[0]) + await graph.node_degree(key[1])
            relations.append(
                {
                    "src_tgt": list(key),
                    "rank": edge_degree,
                    **attrs,
                    "derived_from": [entity_name],
                }
            )

    return {"entities": hydrated, "relations": relations, "missing_seeds": missing}


LIGHTRAG_ENTITY_HYDRATE_EXPAND_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="retriever",
    structural_depth="stage",
    effects=["reads_graph"],
    upstream_ref="v1/lightrag/operate.py",
    body=_entity_hydrate_expand_body,
)
