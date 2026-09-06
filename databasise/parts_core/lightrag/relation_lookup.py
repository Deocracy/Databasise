"""``lightrag/relation-lookup`` (base wiring position 5 of 18) — top-k relation vector search.
Ported by search from ``v1/lightrag/operate.py``'s ``_get_edge_data``, which calls
``relationships_vdb.query(keywords, top_k=query_param.top_k, query_embedding=...)``; this port
receives the already-computed query vector from ``embedder-query``, selects this position's own
``relationships`` vector namespace off the multi-namespace handle
(``databasise/stores/vector.py``'s ``MultiNamespaceVectorStore``), and calls that namespace's
``query(vector, top_k)`` directly, never re-embedding — same shape as ``entity-lookup``.

Emitted items carry ``src_id``/``tgt_id`` (the graph edge's endpoint node ids) in their metadata,
the provenance refs ``relation-hydrate-expand`` dereferences via ``ctx.stores["graph"].get_edge`` —
v1's own vector metadata shape for a relation record (``v1/lightrag/lightrag.py``'s
``data_for_rels_vdb``).
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/relation-lookup@0.1.0"
# v1's own default (v1/lightrag/constants.py's DEFAULT_TOP_K), ported unchanged.
_DEFAULT_TOP_K = 40
# This position's own vector namespace (v1's own per-kind naming, matching
# databasise/parity/import_index.py's _VECTOR_KINDS) — a property of relation-lookup's own §L.1
# position, not of the wiring, so it lives here rather than as a config key.
_RELATIONSHIPS_NAMESPACE = "relationships"


async def _relation_lookup_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    top_k = int(config.get("top_k", _DEFAULT_TOP_K))
    vector = ctx.inputs["embedder-query"]["vector"]
    store = ctx.stores["vector"].select(_RELATIONSHIPS_NAMESPACE)
    raw_items = await store.query(vector, top_k=top_k)
    items = sorted(raw_items, key=lambda item: (-item["score"], item["id"]))
    return {"items": items}


LIGHTRAG_RELATION_LOOKUP_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="retriever",
    structural_depth="stage",
    effects=["reads_vector"],
    upstream_ref="v1/lightrag/operate.py",
    body=_relation_lookup_body,
)
