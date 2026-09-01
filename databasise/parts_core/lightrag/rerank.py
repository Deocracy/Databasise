"""``lightrag/reranker-cross-encoder`` (naive arm position 4 of 7) — a declared pass-through
(D-09): the published base wiring configures no reranker, so this node's default behaviour is to
return its input items unchanged, in order and score, while still declaring ``calls_rerank`` per
§19.9's fallback-reachability rule — the same reason §L.2 has ``chunk-sel-kg`` declare
``reads_vector`` on a weight-only configuration.

A node's config MAY still request a live rerank (``config["live_rerank"] = True``); when it does,
this body reaches ``ctx.clients["rerank"]`` exactly like any other client-calling part. If no
rerank client is wired for that run, ``CapabilityScopedClients.require`` raises
:class:`~databasise.clients.ClientNotWiredError` — a refusal, not a silent no-op — per this
node's own <action> contract ("its body must not silently no-op when the config asks it to rerank
... is a refusal").
"""

from __future__ import annotations

from typing import Any

from databasise.parts.schema import NodeContext, Part

_NAME_AT_VERSION = "lightrag/reranker-cross-encoder@0.1.0"


async def _rerank_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    items = list(ctx.inputs["heading-backfill"]["items"])

    if not config.get("live_rerank"):
        return {"items": items}

    if not items:
        return {"items": items}

    client = ctx.clients["rerank"]  # raises ClientNotWiredError by name if unwired — never a no-op
    query = str(config.get("query", ""))
    documents = [str(item.get("content", "")) for item in items]
    result = await client.rerank(query, documents)
    ranked_items = [items[i] for i in result.ranked_indices]
    return {"items": ranked_items, "tokens": result.tokens}


LIGHTRAG_RERANKER_CROSS_ENCODER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="ranker-reranker",
    structural_depth="stage",
    effects=["calls_rerank"],
    upstream_ref="v1/lightrag/operate.py",
    body=_rerank_body,
)
