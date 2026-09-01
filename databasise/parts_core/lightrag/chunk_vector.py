"""``lightrag/retriever-chunk-topk`` (naive arm position 2 of 7) — top-k chunk vector search.
Ported by search from ``v1/lightrag/operate.py``'s ``_get_vector_context``, which calls
``chunks_vdb.query(query, top_k=search_top_k, query_embedding=...)``; this port receives the
already-computed query vector from ``embedder-query`` and calls the v2 store's own
``query(vector, top_k)`` directly (``databasise/stores/vector.py``), never re-embedding.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/retriever-chunk-topk@0.1.0"
_DEFAULT_TOP_K = 10


async def _chunk_vector_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    top_k = int(config.get("top_k", _DEFAULT_TOP_K))
    vector = ctx.inputs["embedder-query"]["vector"]
    store = ctx.stores["vector"]
    raw_items = await store.query(vector, top_k=top_k)
    # The store's own contract already returns descending-score order (stores/vector.py's
    # `results.sort(key=lambda r: (-r["score"], r["id"]))`); re-sorted here too so this node's own
    # <behavior> contract ("scored chunk items ordered by descending score") holds independent of
    # which vector store implementation is wired for a given run.
    items = sorted(raw_items, key=lambda item: (-item["score"], item["id"]))
    return {"items": items}


LIGHTRAG_RETRIEVER_CHUNK_TOPK_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="retriever",
    structural_depth="stage",
    effects=["reads_vector"],
    upstream_ref="v1/lightrag/operate.py",
    body=_chunk_vector_body,
)
