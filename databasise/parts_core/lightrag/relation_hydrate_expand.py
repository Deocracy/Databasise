"""``lightrag/relation-hydrate-expand`` (base wiring position 6 of 18) — hydrates
``relation-lookup``'s seed items from the graph store and expands each hydrated relation to its
two endpoint entities. Ported by search from ``v1/lightrag/operate.py``'s ``_get_edge_data`` (seed
hydration: edge lookup by endpoint pair, vector-search order preserved rather than re-ranked — v1's
own comment: "Keep edge data without rank, maintain vector search order") and
``_find_most_related_entities_from_relationships`` (endpoint expansion: batch node lookup, no
degree needed — v1's own comment: "Only get nodes data, no need for node degrees").

Reads only ``ctx.stores["graph"]`` (``get_edge``/``get_node``). Never reaches
``ctx.stores["vector"]`` or ``ctx.stores["kv"]``: this node's declared effects are ``reads_graph``
only, and the scheduler's deny-by-default view raises ``UndeclaredEffectError`` on any attempt to
reach either.

A seed whose edge is absent from the graph is reported in ``missing_seeds`` rather than silently
dropped — the same observability rule ``entity-hydrate-expand`` follows, for the symmetric reason.
Every hydrated or expanded item carries ``derived_from`` naming the seed ref (or endpoint-pair key)
it was computed from (CONTRACT §4's authored-evidence rule).

Emits two lists, both consumed by plan 03-06's join nodes: ``relations`` (the hydrated seeds) and
``entities`` (the expanded endpoint entities) — this node's own endpoint-expansion sub-step emits
entities too, which is why the base wiring's ``join-entities`` node depends on this node as well as
``entity-hydrate-expand`` (see ``databasise/wirings/lightrag/arm-global.json-patch.json``'s own
guard note on this crossover).
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/relation-hydrate-expand@0.1.0"


async def _relation_hydrate_expand_body(ctx: NodeContext) -> dict[str, Any]:
    seeds = list(ctx.inputs["relation-lookup"]["items"])
    graph = ctx.stores["graph"]

    hydrated: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for seed in seeds:
        src_id = str(seed["src_id"])
        tgt_id = str(seed["tgt_id"])
        edge = await graph.get_edge(src_id, tgt_id)
        if edge is None:
            missing.append(
                {
                    "src_id": src_id,
                    "tgt_id": tgt_id,
                    "missing": True,
                    "derived_from": [seed["id"]],
                }
            )
            continue
        attrs = dict(edge)
        attrs.setdefault("weight", 1.0)
        hydrated.append({"src_id": src_id, "tgt_id": tgt_id, **attrs, "derived_from": [seed["id"]]})

    seen_entities: set[str] = set()
    entities: list[dict[str, Any]] = []
    for relation in hydrated:
        endpoint_key = f"{relation['src_id']}|{relation['tgt_id']}"
        for entity_name in (relation["src_id"], relation["tgt_id"]):
            if entity_name in seen_entities:
                continue
            seen_entities.add(entity_name)
            node = await graph.get_node(entity_name)
            if node is None:
                missing.append(
                    {"entity_name": entity_name, "missing": True, "derived_from": [endpoint_key]}
                )
                continue
            entities.append({**node, "entity_name": entity_name, "derived_from": [endpoint_key]})

    return {"relations": hydrated, "entities": entities, "missing_seeds": missing}


LIGHTRAG_RELATION_HYDRATE_EXPAND_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="retriever",
    structural_depth="stage",
    effects=["reads_graph"],
    upstream_ref="v1/lightrag/operate.py",
    body=_relation_hydrate_expand_body,
)
