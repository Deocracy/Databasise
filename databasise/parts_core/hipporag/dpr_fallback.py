"""``hipporag/dpr-fallback`` (HippoRAG 2 base wiring position ``dpr-fallback``, PARTS.md ``## §H``)
— the thirteenth and final position, the query-side dense passage retrieval branch the
``zero_surviving_facts_dpr_fallback`` guard (``§19.8``, evaluated at ``fact-filter``) selects
between. Ported by search from ``hipporag/HippoRAG.py:1467-1499``'s ``dense_passage_retrieval``
helper.

**Not wired: ``retrieve_dpr``.** ``HippoRAG.py:665-733``'s ``retrieve_dpr`` is a separate top-level
ablation entry point that also calls ``dense_passage_retrieval``, but is reached through no path
``retrieve()`` itself takes — it is stated here explicitly as not wired (PARTS.md ``## §H``'s own
``Arms:`` field, point 3), rather than silently omitted, since an omission reads to a later reader
as an oversight.

**The shared helper.** :func:`dense_passage_retrieval` is the one dense-passage-retrieval
implementation both this node and ``reset-vector-join``'s passage-weight construction call — the
same helper upstream calls in both places (``HippoRAG.py:1467-1499``, ``:1591-1608``).
``reset_vector_join.py`` imports it from here rather than computing its own, so the two positions
cannot silently diverge on what dense passage retrieval means.

Dispatched unconditionally by the wiring (``deps: ["fact-filter"]``) regardless of whether the
guard fires — nothing in this body reads a guard; ``assemble-result`` is what chooses between this
node's items and ``ppr``'s, per the guard's outcome.

Effects are exactly ``## §H``'s own declared set for this row (``calls_embedding``,
``reads_vector``) — no additive discrepancy, unlike several of this port's other query/index-side
nodes (see ``databasise/evidence/HIPPORAG-PORT-RECORD.md``).
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "hipporag/dpr-fallback@0.1.0"
_CHUNKS_NAMESPACE = "hipporag-chunks"


async def dense_passage_retrieval(
    *, embedding_client: Any, chunks_store: Any, query: str
) -> tuple[list[dict[str, Any]], Any]:
    """Embeds ``query`` then reads §14.2's exhaustive ``score_all`` sub-capability over
    ``chunks_store`` (the already namespace-``select``-ed ``hipporag-chunks`` handle) — a full dot
    product over the passage matrix, never a top-k store query. Returns the raw, unsorted
    per-chunk items (one entry per stored chunk) plus the embed call's own ``EmbeddingResult``, so
    a caller wanting sorted presentation (:func:`_dpr_fallback_body`) and a caller wanting only
    the unordered per-id scores (``reset_vector_join.py``'s passage-weight construction) share one
    implementation rather than diverging on what dense passage retrieval means.
    """
    embed_result = await embedding_client.embed([query])
    vector = embed_result.vectors[0]
    raw_items = await chunks_store.score_all(vector)
    return raw_items, embed_result


async def _dpr_fallback_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    query = str(config.get("query", ""))

    embedding_client = ctx.clients["embedding"]
    chunks_store = ctx.stores["vector"].select(_CHUNKS_NAMESPACE)
    raw_items, embed_result = await dense_passage_retrieval(
        embedding_client=embedding_client, chunks_store=chunks_store, query=query
    )

    items = [
        {**item, "kind": "text_chunk"}
        for item in sorted(raw_items, key=lambda item: (-item["score"], item["id"]))
    ]
    return {"items": items, "tokens": embed_result.tokens}


HIPPORAG_DPR_FALLBACK_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="retriever",
    structural_depth="opaque",
    effects=["calls_embedding", "reads_vector"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_dpr_fallback_body,
)
