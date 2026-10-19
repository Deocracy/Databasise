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

Dispatched unconditionally by the wiring (``deps: ["fact-filter", "fact-score"]``) regardless of whether the
guard fires — nothing in this body reads a guard; ``assemble-result`` is what chooses between this
node's items and ``ppr``'s, per the guard's outcome.

The query vector arrives from ``fact-score`` over a direct dep (D-17), so this node never calls the
embedding client and declares ``reads_vector`` alone — narrower than ``## §H``'s
(``calls_embedding``, ``reads_vector``), a documented divergence (see
``databasise/evidence/HIPPORAG-PORT-RECORD.md``).
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "hipporag/dpr-fallback@0.1.0"
_CHUNKS_NAMESPACE = "hipporag-chunks"


async def dense_passage_retrieval(*, query_vector: Any, chunks_store: Any) -> list[dict[str, Any]]:
    """Reads §14.2's exhaustive ``score_all`` sub-capability over ``chunks_store`` (the already
    namespace-``select``-ed ``hipporag-chunks`` handle) with the query vector ``fact-score``
    embedded — a full dot product over the passage matrix, never a top-k store query. Returns the
    raw, unsorted per-chunk items (one entry per stored chunk), so a caller wanting sorted
    presentation (:func:`_dpr_fallback_body`) and a caller wanting only the unordered per-id scores
    (``reset_vector_join.py``'s passage-weight construction) share one implementation rather than
    diverging on what dense passage retrieval means.
    """
    return await chunks_store.score_all(query_vector)


async def _dpr_fallback_body(ctx: NodeContext) -> dict[str, Any]:
    query_vector = ctx.inputs["fact-score"]["query_vector"]
    chunks_store = ctx.stores["vector"].select(_CHUNKS_NAMESPACE)
    raw_items = await dense_passage_retrieval(query_vector=query_vector, chunks_store=chunks_store)

    items = [
        {**item, "kind": "text_chunk"}
        for item in sorted(raw_items, key=lambda item: (-item["score"], item["id"]))
    ]
    return {"items": items}


HIPPORAG_DPR_FALLBACK_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="retriever",
    structural_depth="opaque",
    effects=["reads_vector"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_dpr_fallback_body,
)
