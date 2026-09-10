"""``hipporag/synonymy-edge-builder`` (HippoRAG 2 base wiring position ``synonymy-edges``,
PARTS.md ``## §H``) — entity-to-entity synonymy edges from a bulk self-referential KNN over the
entity namespace. Ported by search from ``hipporag/HippoRAG.py:332``, ``:959-1020`` (self-KNN at
``:986-992``). Declared capability ``§14.2`` Vector self-KNN, ``## §H``'s H1 register row's own
landing (``CONTRACT.md §14.2``'s Vector self-KNN row).

Composing this node's own similarity pass by calling ``FaissVectorStore.query()`` in a loop over
every stored entity is not an acceptable substitute: §14.2 requires the store expose a batched
self-KNN path or refuse the wiring outright, so a loop would be an emulation of a capability the
store had not earned (CONTRACT.md §14.2: "that the store exposes a batched self-KNN path rather
than forcing an O(N^2) pointwise emulation"). ``databasise/stores/vector.py``'s
``FaissVectorStore.self_knn`` is that earned capability.

**The guard.** The governing wiring's own ``config.guard`` names ``num_new_chunks > 0`` — checked
before any store handle is taken, so a no-new-chunks index build costs nothing at this position.
This node's sole dep is ``entity-fact-embed``, whose own output carries no direct chunk count;
the number of entities ``entity-fact-embed`` produced (``ctx.inputs["entity-fact-embed"]
["entities"]``) is the faithful, available proxy for "did this index run's upstream chain produce
anything new" — ``entity-fact-embed`` itself already short-circuits to zero entities when
``openie`` found zero findings, which in turn only happens when ``chunk-embed`` produced zero new
chunks. Recorded here as a 06-05-PLAN.md design decision, mirroring 06-02-PLAN.md's own precedent
for interpreting an underspecified upstream-data guard against the data the wiring actually
threads through this dep chain.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "hipporag/synonymy-edge-builder@0.1.0"
_ENTITIES_NAMESPACE = "hipporag-entities"
_EDGE_TYPE = "synonymy"
_DEFAULT_SYNONYMY_TOP_K = 5
_DEFAULT_SYNONYMY_THRESHOLD = 0.8


def _canonical_pair(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))  # type: ignore[return-value]


async def _synonymy_edges_body(ctx: NodeContext) -> dict[str, Any]:
    entity_fact_embed_output = ctx.inputs["entity-fact-embed"]
    entities = list(entity_fact_embed_output.get("entities", []))
    if not entities:
        return {"edges": []}

    config = ctx.config or {}
    top_k = int(config.get("synonymy_top_k", _DEFAULT_SYNONYMY_TOP_K))
    threshold = float(config.get("synonymy_threshold", _DEFAULT_SYNONYMY_THRESHOLD))

    entity_store = ctx.stores["vector"].select(_ENTITIES_NAMESPACE)
    neighbours_by_id = await entity_store.self_knn(top_k=top_k)

    weight_by_pair: dict[tuple[str, str], float] = {}
    for entity_ref, neighbours in neighbours_by_id.items():
        for neighbour in neighbours:
            if neighbour["score"] < threshold:
                continue
            pair = _canonical_pair(entity_ref, neighbour["id"])
            weight_by_pair.setdefault(pair, neighbour["score"])

    edges = [
        {"src": src, "tgt": tgt, "weight": weight, "edge_type": _EDGE_TYPE}
        for (src, tgt), weight in sorted(weight_by_pair.items())
    ]
    return {"edges": edges}


HIPPORAG_SYNONYMY_EDGE_BUILDER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="extractor",
    structural_depth="opaque",
    effects=["reads_vector"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_synonymy_edges_body,
)
