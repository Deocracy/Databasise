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

**The guard.** The wiring declares no guard key for this node; the new-entity rule below is the
guard. A run that produced no new entity takes no store handle, so a no-new-chunks index build costs
nothing at this position (``entity-fact-embed`` already short-circuits to zero entities when
``openie`` found zero findings).

**New entities only (D-05, HIPP-07).** The new-entity rule is the guard, hard-coded: only entities
new in this ingest are matched, against every committed and staged entity via
``self_knn(ids=...)``. New refs are ``entity-fact-embed``'s ``new_entities`` when that key is
present, else the refs whose committed ``get_by_id`` is ``None``. No new entity means no store
query and no edges. A pair is therefore emitted once, on the ingest that introduces it, and never
re-emitted. Accepted recall difference: a new entity that appears only in an old entity's top-k
(not the reverse) is missed.

**Restoring a re-ingest's lost edges (A-CR-01).** ``document-remover`` deletes an orphaned entity's
vertex, which hides every synonymy edge on it, including ones another document's ingest created.
In ``corpus-ingest.json`` this node depends on the remover and re-emits each of its
``removed_synonymy_edges`` whose two endpoints still exist at the end of the run: an endpoint
survives if the remover did not remove it, or if this run re-added it."""

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
    if "new_entities" in entity_fact_embed_output:
        new_refs = list(entity_fact_embed_output["new_entities"])
    else:
        new_refs = [e["ref"] for e in entities if entity_store.get_by_id(e["ref"]) is None]
    if not new_refs:
        return {"edges": []}
    neighbours_by_id = await entity_store.self_knn(top_k=top_k, ids=new_refs)

    weight_by_pair: dict[tuple[str, str], float] = {}
    for entity_ref, neighbours in neighbours_by_id.items():
        for neighbour in neighbours:
            if neighbour["score"] < threshold:
                continue
            pair = _canonical_pair(entity_ref, neighbour["id"])
            weight_by_pair.setdefault(pair, neighbour["score"])

    # A-CR-01: restore the edges the remover hid. Recomputed pairs above keep their fresh score.
    removed = set(ctx.inputs.get("document-remover", {}).get("removed_entities", []))
    present = {e["ref"] for e in entities}
    for edge in ctx.inputs.get("document-remover", {}).get("removed_synonymy_edges", []):
        ends = (edge["src"], edge["tgt"])
        if all(end in present or end not in removed for end in ends):
            weight_by_pair.setdefault(_canonical_pair(*ends), float(edge["weight"]))

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
