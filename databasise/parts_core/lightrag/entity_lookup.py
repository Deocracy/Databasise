"""``lightrag/entity-lookup`` (base wiring position 3 of 18) — top-k entity vector search. Ported
by search from ``v1/lightrag/operate.py``'s ``_get_node_data``, which calls
``entities_vdb.query(query, top_k=query_param.top_k, query_embedding=...)``; this port receives
the already-computed query vector from ``embedder-query``, selects this position's own ``entities``
vector namespace off the multi-namespace handle (``databasise/stores/vector.py``'s
``MultiNamespaceVectorStore``), and calls that namespace's ``query(vector, top_k)`` directly, never
re-embedding — same shape as ``chunk-vector`` (``databasise/parts_core/lightrag/chunk_vector.py``),
which selects ``chunks`` instead.

Emitted items carry ``entity_name`` (the graph node id) in their metadata, the provenance ref
``entity-hydrate-expand`` dereferences via ``ctx.stores["graph"].get_node`` — v1's own vector
metadata shape for an entity record (``v1/lightrag/lightrag.py``'s ``data_for_entities_vdb``).
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/entity-lookup@0.1.0"
# v1's own default (v1/lightrag/constants.py's DEFAULT_TOP_K), ported unchanged — this node's own
# <action> instruction is to port v1's scoring and ordering rather than re-deriving them.
_DEFAULT_TOP_K = 40
# This position's own vector namespace (v1's own per-kind naming, matching
# databasise/parity/import_index.py's _VECTOR_KINDS) — a property of entity-lookup's own §L.1
# position, not of the wiring, so it lives here rather than as a config key.
_ENTITIES_NAMESPACE = "entities"


async def _entity_lookup_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    top_k = int(config.get("top_k", _DEFAULT_TOP_K))
    vector = ctx.inputs["embedder-query"]["vector"]
    store = ctx.stores["vector"].select(_ENTITIES_NAMESPACE)
    raw_items = await store.query(vector, top_k=top_k)
    # The store's own contract already returns descending-score order; re-sorted here too so this
    # node's own <behavior> contract holds independent of which vector store is wired for a run —
    # the same tie-break convention chunk-vector's own body already establishes.
    items = sorted(raw_items, key=lambda item: (-item["score"], item["id"]))
    return {"items": items}


LIGHTRAG_ENTITY_LOOKUP_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="retriever",
    structural_depth="stage",
    effects=["reads_vector"],
    upstream_ref="v1/lightrag/operate.py",
    body=_entity_lookup_body,
)
