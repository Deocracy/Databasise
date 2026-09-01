"""Per-body tests for the graph-half parts 03-05-PLAN.md ports — a stub client double and a
temporary store, no network, runs everywhere. Every part is exercised through its own registered
``Part.body`` (never a private module function reached into directly), the same call shape
``databasise.parts.registry.dispatch`` uses. Task 2 covers ``keywords``/``entity-lookup``/
``relation-lookup``; Task 3 extends this file with ``entity-hydrate-expand``/
``relation-hydrate-expand``.
"""

from __future__ import annotations

import json
from typing import Any

from databasise.clients.base import ChatResult
from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag.entity_lookup import LIGHTRAG_ENTITY_LOOKUP_PART
from databasise.parts_core.lightrag.keywords import LIGHTRAG_KEYWORD_EXTRACTOR_PART
from databasise.parts_core.lightrag.relation_lookup import LIGHTRAG_RELATION_LOOKUP_PART
from databasise.runner.trace import TokenAccounting
from databasise.stores.vector import FaissVectorStore


def _ctx(
    node_id: str,
    config: dict[str, Any] | None = None,
    inputs: dict[str, Any] | None = None,
    stores: dict[str, Any] | None = None,
    clients: dict[str, Any] | None = None,
) -> NodeContext:
    """A plain, unscoped ``NodeContext`` — see ``test_naive_arm_parts.py``'s own ``_ctx`` docstring
    for why this exercises the same subscript-access call shape the scheduler's scoped views
    present, without needing the deny-by-default wrapper for every ordinary case.
    """
    return NodeContext(
        node_id=node_id,
        config=config,
        inputs=inputs or {},
        stores=stores or {},
        clients=clients or {},
    )


class _StubKeywordLLMClient:
    """Returns a fixed JSON keyword payload, plus a real, non-zero ``TokenAccounting``."""

    def __init__(self, high_level: list[str], low_level: list[str]):
        self.high_level = high_level
        self.low_level = low_level
        self.calls: list[list[dict[str, str]]] = []

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ChatResult:
        self.calls.append(list(messages))
        payload = json.dumps(
            {"high_level_keywords": self.high_level, "low_level_keywords": self.low_level}
        )
        return ChatResult(
            text=payload,
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-kw-llm"),
            resolved_model_identity="stub-kw-model",
        )


# --------------------------------------------------------------------------------------------- #
# keywords
# --------------------------------------------------------------------------------------------- #


async def test_keywords_live_call_sends_v1s_prompt_and_returns_a_populated_token_accounting():
    client = _StubKeywordLLMClient(high_level=["retrieval"], low_level=["Ed Wood"])
    ctx = _ctx(
        "keywords", config={"query": "what films did Ed Wood direct"}, clients={"llm": client}
    )

    result = await LIGHTRAG_KEYWORD_EXTRACTOR_PART.body(ctx)

    assert result["high_level_keywords"] == ["retrieval"]
    assert result["low_level_keywords"] == ["Ed Wood"]
    assert result["tokens"].call_count == 1
    assert result["tokens"].prompt_tokens > 0
    assert len(client.calls) == 1
    sent_prompt = client.calls[0][0]["content"]
    assert "what films did Ed Wood direct" in sent_prompt
    assert "expert keyword extractor" in sent_prompt  # v1's own prompt role line


async def test_keywords_pinned_path_returns_the_recorded_output_and_makes_zero_llm_calls():
    class _ExplodingClient:
        async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ChatResult:
            raise AssertionError("pinned path must not call the LLM client")

    ctx = _ctx(
        "keywords",
        config={
            "query": "irrelevant on the pinned path",
            "pinned": True,
            "pinned_output": {"high_level_keywords": ["a"], "low_level_keywords": ["b", "c"]},
        },
        clients={"llm": _ExplodingClient()},
    )

    result = await LIGHTRAG_KEYWORD_EXTRACTOR_PART.body(ctx)

    assert result["high_level_keywords"] == ["a"]
    assert result["low_level_keywords"] == ["b", "c"]
    assert result["tokens"].call_count == 0
    assert result["tokens"].counted_by == "pinned-replay"


async def test_keywords_pinned_and_live_accounting_are_distinguishable():
    pinned_ctx = _ctx(
        "keywords",
        config={"pinned": True, "pinned_output": {"high_level_keywords": [], "low_level_keywords": []}},
    )
    live_client = _StubKeywordLLMClient(high_level=[], low_level=[])
    live_ctx = _ctx("keywords", config={"query": "q"}, clients={"llm": live_client})

    pinned_result = await LIGHTRAG_KEYWORD_EXTRACTOR_PART.body(pinned_ctx)
    live_result = await LIGHTRAG_KEYWORD_EXTRACTOR_PART.body(live_ctx)

    assert pinned_result["tokens"].call_count != live_result["tokens"].call_count
    assert pinned_result["tokens"].counted_by != live_result["tokens"].counted_by


# --------------------------------------------------------------------------------------------- #
# entity-lookup / relation-lookup
# --------------------------------------------------------------------------------------------- #


async def test_entity_lookup_returns_items_ordered_by_descending_score_with_entity_name(store_root):
    store = FaissVectorStore(namespace="entities", workspace="ws", store_root=store_root)
    await store.upsert(
        ids=["ent-low", "ent-high"],
        embeddings=[[0.0, 1.0, 0.0], [1.0, 0.0, 0.0]],
        metadatas=[{"entity_name": "Low"}, {"entity_name": "High"}],
    )
    await store.index_done_callback()

    ctx = _ctx(
        "entity-lookup",
        config={"top_k": 10},
        inputs={"embedder-query": {"vector": [1.0, 0.0, 0.0]}},
        stores={"vector": store},
    )

    result = await LIGHTRAG_ENTITY_LOOKUP_PART.body(ctx)

    assert [item["entity_name"] for item in result["items"]] == ["High", "Low"]
    scores = [item["score"] for item in result["items"]]
    assert scores == sorted(scores, reverse=True)


async def test_relation_lookup_returns_items_ordered_by_descending_score_with_endpoints(store_root):
    store = FaissVectorStore(namespace="relationships", workspace="ws", store_root=store_root)
    await store.upsert(
        ids=["rel-low", "rel-high"],
        embeddings=[[0.0, 1.0, 0.0], [1.0, 0.0, 0.0]],
        metadatas=[{"src_id": "A", "tgt_id": "B"}, {"src_id": "C", "tgt_id": "D"}],
    )
    await store.index_done_callback()

    ctx = _ctx(
        "relation-lookup",
        config={"top_k": 10},
        inputs={"embedder-query": {"vector": [1.0, 0.0, 0.0]}},
        stores={"vector": store},
    )

    result = await LIGHTRAG_RELATION_LOOKUP_PART.body(ctx)

    assert [(item["src_id"], item["tgt_id"]) for item in result["items"]] == [("C", "D"), ("A", "B")]
    scores = [item["score"] for item in result["items"]]
    assert scores == sorted(scores, reverse=True)
