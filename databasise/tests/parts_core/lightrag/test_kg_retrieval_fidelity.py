"""LRAG-18 parity tests (D-16, "match v1"): the KG arms' retrieval ordering and selection follow
``v1/lightrag/operate.py``'s ``kg_query``. Part bodies are driven with plain ``NodeContext``s over
recording clients and stores; no network, runs everywhere.

v1 references: keyword fallback operate.py:3850-3860; one batched embed of
``[query, ll_keywords_str, hl_keywords_str]`` operate.py:4350-4403.
"""

from __future__ import annotations

import json
from typing import Any

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag.embedder_query import LIGHTRAG_EMBEDDER_QUERY_PART
from databasise.parts_core.lightrag.entity_lookup import LIGHTRAG_ENTITY_LOOKUP_PART
from databasise.parts_core.lightrag.keywords import LIGHTRAG_KEYWORD_EXTRACTOR_PART
from databasise.parts_core.lightrag.relation_lookup import LIGHTRAG_RELATION_LOOKUP_PART
from databasise.runner.trace import TokenAccounting


def _ctx(
    node_id: str,
    config: dict[str, Any] | None = None,
    inputs: dict[str, Any] | None = None,
    stores: dict[str, Any] | None = None,
    clients: dict[str, Any] | None = None,
) -> NodeContext:
    return NodeContext(
        node_id=node_id,
        config=config,
        inputs=inputs or {},
        stores=stores or {},
        clients=clients or {},
    )


class _RecordingEmbeddingClient:
    """One distinct vector per distinct text, so a test can tell which string a vector came from."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.vector_by_text: dict[str, list[float]] = {}

    async def embed(self, texts: list[str], **kwargs: Any) -> EmbeddingResult:
        self.calls.append(list(texts))
        vectors = []
        for text in texts:
            vector = self.vector_by_text.setdefault(
                text, [float(len(self.vector_by_text) + 1), 0.0, 0.0]
            )
            vectors.append(vector)
        return EmbeddingResult(
            vectors=vectors,
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="rec-embed"),
            resolved_model_identity="rec-embed-model",
        )


class _EmptyKeywordLLM:
    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ChatResult:
        return ChatResult(
            text=json.dumps({"high_level_keywords": [], "low_level_keywords": []}),
            tokens=TokenAccounting(prompt_tokens=3, completion_tokens=2, call_count=1, counted_by="kw"),
            resolved_model_identity="kw-model",
        )


class _RecordingVectorHandle:
    """Records (namespace, vector) for every query; returns one item per query."""

    def __init__(self) -> None:
        self.queries: list[tuple[str, Any]] = []

    def select(self, namespace: str) -> Any:
        handle = self

        class _Namespace:
            async def query(self, vector: Any, top_k: int = 10) -> list[dict[str, Any]]:
                handle.queries.append((namespace, vector))
                return [{"id": f"{namespace}-1", "score": 1.0, "entity_name": "X", "src_id": "X", "tgt_id": "Y"}]

        return _Namespace()


_QUERY = "What did UNIQalpha Corp build in UNIQalpha City?"
_LL = ["UNIQalpha Corp", "UNIQalpha City"]
_HL = ["bridge engineering"]


async def _pinned_keywords(hl: list[str], ll: list[str], query: str = _QUERY) -> dict[str, Any]:
    ctx = _ctx(
        "keywords",
        config={
            "query": query,
            "pinned": True,
            "pinned_output": {"high_level_keywords": hl, "low_level_keywords": ll},
        },
    )
    return await LIGHTRAG_KEYWORD_EXTRACTOR_PART.body(ctx)


# --------------------------------------------------------------------------------------------- #
# keywords: v1's fallback and the joined keyword strings
# --------------------------------------------------------------------------------------------- #


async def test_keywords_short_query_with_no_keywords_falls_back_to_the_query_as_ll():
    ctx = _ctx("keywords", config={"query": "short q"}, clients={"llm": _EmptyKeywordLLM()})
    result = await LIGHTRAG_KEYWORD_EXTRACTOR_PART.body(ctx)
    assert result["low_level_keywords"] == ["short q"]
    assert result["high_level_keywords"] == []
    assert result["ll_keywords_str"] == "short q"
    assert result["hl_keywords_str"] == ""


async def test_keywords_long_query_with_no_keywords_keeps_both_lists_empty():
    query = "x" * 60
    ctx = _ctx("keywords", config={"query": query}, clients={"llm": _EmptyKeywordLLM()})
    result = await LIGHTRAG_KEYWORD_EXTRACTOR_PART.body(ctx)
    assert result["low_level_keywords"] == []
    assert result["high_level_keywords"] == []


async def test_keywords_emits_comma_joined_keyword_strings():
    result = await _pinned_keywords(_HL, _LL)
    assert result["ll_keywords_str"] == "UNIQalpha Corp, UNIQalpha City"
    assert result["hl_keywords_str"] == "bridge engineering"


# --------------------------------------------------------------------------------------------- #
# embedder-query + entity-lookup + relation-lookup: the hybrid arm's first four nodes
# --------------------------------------------------------------------------------------------- #


async def test_hybrid_lookups_search_with_v1s_keyword_string_embeddings():
    keywords_out = await _pinned_keywords(_HL, _LL)
    client = _RecordingEmbeddingClient()
    embed_out = await LIGHTRAG_EMBEDDER_QUERY_PART.body(
        _ctx(
            "embedder-query",
            config={"query": _QUERY},
            inputs={"keywords": keywords_out},
            clients={"embedding": client},
        )
    )

    # One batched call, exactly v1's three strings (operate.py:4350-4403).
    assert client.calls == [[_QUERY, "UNIQalpha Corp, UNIQalpha City", "bridge engineering"]]
    assert embed_out["vector"] == client.vector_by_text[_QUERY]
    assert embed_out["ll_vector"] == client.vector_by_text["UNIQalpha Corp, UNIQalpha City"]
    assert embed_out["hl_vector"] == client.vector_by_text["bridge engineering"]
    assert embed_out["tokens"].call_count == 1

    vectors = _RecordingVectorHandle()
    inputs = {"embedder-query": embed_out}
    await LIGHTRAG_ENTITY_LOOKUP_PART.body(_ctx("entity-lookup", inputs=inputs, stores={"vector": vectors}))
    await LIGHTRAG_RELATION_LOOKUP_PART.body(
        _ctx("relation-lookup", inputs=inputs, stores={"vector": vectors})
    )

    assert vectors.queries == [
        ("entities", embed_out["ll_vector"]),
        ("relationships", embed_out["hl_vector"]),
    ]


async def test_naive_embedder_query_without_keywords_embeds_the_query_alone():
    client = _RecordingEmbeddingClient()
    out = await LIGHTRAG_EMBEDDER_QUERY_PART.body(
        _ctx("embedder-query", config={"query": "plain query"}, clients={"embedding": client})
    )
    assert client.calls == [["plain query"]]
    assert out["vector"] == client.vector_by_text["plain query"]


async def test_empty_ll_list_gives_no_ll_vector_and_entity_lookup_skips_the_store():
    keywords_out = await _pinned_keywords(_HL, [])
    client = _RecordingEmbeddingClient()
    embed_out = await LIGHTRAG_EMBEDDER_QUERY_PART.body(
        _ctx("embedder-query", inputs={"keywords": keywords_out}, clients={"embedding": client})
    )
    assert client.calls == [[_QUERY, "bridge engineering"]]
    assert embed_out["ll_vector"] is None

    vectors = _RecordingVectorHandle()
    result = await LIGHTRAG_ENTITY_LOOKUP_PART.body(
        _ctx("entity-lookup", inputs={"embedder-query": embed_out}, stores={"vector": vectors})
    )
    assert result["items"] == []
    assert vectors.queries == []
