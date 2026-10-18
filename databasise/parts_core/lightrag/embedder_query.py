"""``lightrag/embedder-query`` (naive arm position 1 of 7) — the query-side embedding call §L.1
supersedes v1's store-internal embedding fallback with: v1's vector stores embed the query text
themselves inside ``query()`` when no ``query_embedding`` is passed (located by searching
``_get_vector_context`` in ``v1/lightrag/operate.py``, which calls ``chunks_vdb.query(query,
top_k=..., query_embedding=None)``); this port makes that call explicit as its own node, so
``chunk-vector`` (the next node) always receives a precomputed vector, never raw text.

Takes its query text from ``ctx.inputs["keywords"]`` when the ``keywords`` node is present in the
resolved arm (a later plan ports that node's real body), and from ``ctx.config["query"]`` when it
is not — in the ``naive`` arm the patch sets this node's own ``deps`` to ``[]``, so the config path
is the one this plan's tracer exercises.
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/embedder-query@0.1.0"


def _query_text(ctx: NodeContext) -> str:
    keywords_output = ctx.inputs.get("keywords")
    if keywords_output is not None:
        if isinstance(keywords_output, dict):
            return str(keywords_output.get("query") or keywords_output.get("text") or "")
        return str(keywords_output)
    config = ctx.config or {}
    return str(config.get("query", ""))


async def _embedder_query_body(ctx: NodeContext) -> dict[str, Any]:
    query = _query_text(ctx)
    client = ctx.clients["embedding"]
    keywords_output = ctx.inputs.get("keywords")
    if not isinstance(keywords_output, dict):
        result = await client.embed([query])
        return {
            "query": query,
            "vector": result.vectors[0],
            "tokens": result.tokens,
            "resolved_model_identity": result.resolved_model_identity,
        }

    # KG arms (D-16, LRAG-18): v1 embeds the query and the two ", "-joined keyword strings in one
    # batched call (operate.py:4350-4403); entity-lookup searches with ll_vector, relation-lookup
    # with hl_vector. An empty string is not embedded and its vector is None.
    texts = {
        "vector": query,
        "ll_vector": str(keywords_output.get("ll_keywords_str") or ""),
        "hl_vector": str(keywords_output.get("hl_keywords_str") or ""),
    }
    wanted = [(key, text) for key, text in texts.items() if text]
    out: dict[str, Any] = {"query": query, "vector": None, "ll_vector": None, "hl_vector": None}
    if not wanted:
        return out
    result = await client.embed([text for _, text in wanted])
    for (key, _), vector in zip(wanted, result.vectors, strict=True):
        out[key] = vector
    out["tokens"] = result.tokens
    out["resolved_model_identity"] = result.resolved_model_identity
    return out


LIGHTRAG_EMBEDDER_QUERY_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="embedder",
    structural_depth="stage",
    effects=["calls_embedding"],
    upstream_ref="v1/lightrag/operate.py",
    body=_embedder_query_body,
)
