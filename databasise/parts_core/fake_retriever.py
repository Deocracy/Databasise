"""D-04's deterministic fake retriever: declares ``reads_vector``, returns an ordered slice of a
small fixture corpus keyed by the query string. No embedding model, no network — determinism is
the point, so a later plan can test the run record's determinism stamp without an LLM in the
loop.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_FIXTURE_CORPUS: dict[str, list[str]] = {
    "graph databases": ["doc-cozo-01", "doc-cozo-02", "doc-neo4j-01"],
    "vector search": ["doc-faiss-01", "doc-faiss-02", "doc-qdrant-01"],
}


async def _fake_retriever_body(ctx: NodeContext) -> dict[str, Any]:
    """Deterministic: the same query returns the same ordered result list on every call."""
    config = ctx.config or {}
    query = str(config.get("query", ""))
    results = list(_FIXTURE_CORPUS.get(query, []))
    return {"query": query, "results": results}


FAKE_RETRIEVER_PART = Part(
    name_at_version="parts-core/fake-retriever@1.0.0",
    kind="retriever",
    structural_depth="stage",
    effects=["reads_vector"],
    upstream_ref=None,
    body=_fake_retriever_body,
)
