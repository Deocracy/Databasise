"""``hipporag/fact-scorer`` (HippoRAG 2 base wiring position ``fact-score``, PARTS.md ``## §H``) —
the query-side dense fact scoring call. Ported by search from ``hipporag/HippoRAG.py:461,
1427-1465``, specifically the exhaustive dot product at ``:1459`` (``retrieve_facts`` calling
``self.embedding_model.get_query_doc_scores`` over every stored fact, never a top-k vector search).

Embeds ``ctx.config["query"]`` through ``ctx.clients`` — the same client-call shape
``parts_core/lightrag/embedder_query.py`` uses — then reads §14.2's exhaustive ``score_all``
sub-capability off this position's own ``hipporag-facts`` vector namespace
(``databasise/stores/vector.py``'s ``FaissVectorStore.score_all``), never ``query()``'s top-k path.

PARTS.md ``## §H`` declares this node's effects as ``reads_vector`` alone; ``calls_embedding`` is
added here as a stated additive discrepancy — see the module-level note below and this plan's own
SUMMARY.md, in the same shape 05-06 recorded ``mutates_store`` on the codebase-memory-mcp part.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "hipporag/fact-scorer@0.1.0"
_FACTS_NAMESPACE = "hipporag-facts"

# ADDITIVE EFFECTS DISCREPANCY (06-01-PLAN.md, recorded per SUMMARY.md): PARTS.md ## §H declares
# this node's effects as ["reads_vector"] alone. The governing wiring's own "fact-score" node has
# deps: [] (no upstream embedder position feeds it a precomputed query vector, unlike LightRAG's
# chunk-vector, which always receives one from embedder-query). This node must therefore embed the
# query itself, so "calls_embedding" is declared here in addition to "reads_vector" — never
# silently resolved by dropping the embed call or by silently widening deps instead.


async def _fact_score_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    query = str(config.get("query", ""))

    embedding_client = ctx.clients["embedding"]
    embed_result = await embedding_client.embed([query])
    vector = embed_result.vectors[0]

    store = ctx.stores["vector"].select(_FACTS_NAMESPACE)
    raw_items = await store.score_all(vector)

    items = [
        {**item, "kind": "graph_fact"}
        for item in sorted(raw_items, key=lambda item: (-item["score"], item["id"]))
    ]
    return {"items": items, "tokens": embed_result.tokens}


HIPPORAG_FACT_SCORER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="retriever",
    structural_depth="opaque",
    effects=["reads_vector", "calls_embedding"],
    upstream_ref="hipporag/src/hipporag/HippoRAG.py",
    body=_fact_score_body,
)
