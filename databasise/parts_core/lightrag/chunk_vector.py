"""``lightrag/retriever-chunk-topk`` (naive arm position 2 of 7) — top-k chunk vector search.
Ported by search from ``v1/lightrag/operate.py``'s ``_get_vector_context``, which calls
``chunks_vdb.query(query, top_k=search_top_k, query_embedding=...)``; this port receives the
already-computed query vector from ``embedder-query``, selects this position's own ``chunks``
vector namespace off the multi-namespace handle (``databasise/stores/vector.py``'s
``MultiNamespaceVectorStore``), and calls that namespace's ``query(vector, top_k)`` directly,
never re-embedding.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/retriever-chunk-topk@0.1.0"
_DEFAULT_TOP_K = 10
# This position's own vector namespace (v1's own per-kind naming, matching
# databasise/parity/import_index.py's _VECTOR_KINDS) — a property of chunk-vector's own §L.1
# position, not of the wiring, so it lives here rather than as a config key.
_CHUNKS_NAMESPACE = "chunks"


def cosine_threshold(config: dict[str, Any]) -> float:
    """B-CR-02: v1's Faiss store drops hits whose cosine is below ``cosine_better_than_threshold``
    (faiss_impl.py:421). The v2 store's scores are inner products of L2-normalised vectors, i.e.
    cosine, so the same cut applies. Like v1's store (faiss_impl.py:208-211), the part has no
    default of its own: the shipped value, v1 COSINE_THRESHOLD 0.2 (lightrag.py:735), is set in
    ``wirings/lightrag/base.json``. A config without the key cuts nothing."""
    return float(config.get("cosine_better_than_threshold", "-inf"))


async def _chunk_vector_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    top_k = int(config.get("top_k", _DEFAULT_TOP_K))
    threshold = cosine_threshold(config)
    vector = ctx.inputs["embedder-query"]["vector"]
    store = ctx.stores["vector"].select(_CHUNKS_NAMESPACE)
    # v1's own test, `dist < threshold` drops: a NaN score is kept and reaches the evidence fault.
    raw_items = [i for i in await store.query(vector, top_k=top_k) if not i["score"] < threshold]
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
