"""Per-body tests for the seven parts 03-04-PLAN.md Task 2 ports for the ``naive`` arm — a stub
client double and a temporary store, no network, runs everywhere. Every part is exercised through
its own registered ``Part.body`` (never a private module function reached into directly), the
same call shape ``databasise.parts.registry.dispatch`` uses.
"""

from __future__ import annotations

from typing import Any

import pytest
from databasise.clients import ClientNotWiredError
from databasise.clients.base import ChatResult, EmbeddingResult, RerankResult
from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag.assemble import LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART
from databasise.parts_core.lightrag.chunk_vector import LIGHTRAG_RETRIEVER_CHUNK_TOPK_PART
from databasise.parts_core.lightrag.embedder_index import LIGHTRAG_EMBEDDER_INDEX_PART
from databasise.parts_core.lightrag.embedder_query import LIGHTRAG_EMBEDDER_QUERY_PART
from databasise.parts_core.lightrag.generate import LIGHTRAG_GENERATOR_LLM_PART
from databasise.parts_core.lightrag.heading_backfill import (
    LIGHTRAG_CHUNK_HEADING_BACKFILLER_PART,
)
from databasise.parts_core.lightrag.rerank import LIGHTRAG_RERANKER_CROSS_ENCODER_PART
from databasise.runner.trace import TokenAccounting
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore


def _ctx(
    node_id: str,
    config: dict[str, Any] | None = None,
    inputs: dict[str, Any] | None = None,
    stores: dict[str, Any] | None = None,
    clients: dict[str, Any] | None = None,
) -> NodeContext:
    """A plain, unscoped ``NodeContext`` — every body here does plain dict-subscript access
    (``ctx.stores["kv"]``, ``ctx.clients["llm"]``), so a raw dict exercises the same call shape
    the scheduler's ``_ScopedStoresView``/``_ScopedClientsView`` present without needing the
    deny-by-default wrapper itself, which is covered by ``tests/runner/test_clients_threading.py``
    and ``tests/parts/test_reference_parts.py`` already.
    """
    return NodeContext(
        node_id=node_id,
        config=config,
        inputs=inputs or {},
        stores=stores or {},
        clients=clients or {},
    )


class _StubEmbeddingClient:
    """Returns ``vector`` for every input text, in order, plus a real, non-zero
    ``TokenAccounting`` — one call, ``len(texts)`` prompt tokens (one per requested text)."""

    def __init__(self, vector: list[float], resolved_model_identity: str = "stub-embed-model"):
        self.vector = vector
        self.resolved_model_identity = resolved_model_identity
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str], **kwargs: Any) -> EmbeddingResult:
        self.calls.append(list(texts))
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(
                prompt_tokens=len(texts), call_count=1, counted_by=self.resolved_model_identity
            ),
            resolved_model_identity=self.resolved_model_identity,
        )


class _StubLLMClient:
    def __init__(self, completion: str = "stub completion"):
        self.completion = completion
        self.calls: list[list[dict[str, str]]] = []

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ChatResult:
        self.calls.append(list(messages))
        return ChatResult(
            text=self.completion,
            tokens=TokenAccounting(prompt_tokens=3, completion_tokens=2, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


class _StubRerankClient:
    def __init__(self, ranked_indices: list[int]):
        self.ranked_indices = ranked_indices
        self.calls: list[tuple[str, list[str]]] = []

    async def rerank(self, query: str, documents: list[str], **kwargs: Any) -> RerankResult:
        self.calls.append((query, list(documents)))
        return RerankResult(
            ranked_indices=self.ranked_indices,
            tokens=TokenAccounting(prompt_tokens=1, call_count=1, counted_by="stub-rerank"),
            resolved_model_identity="stub-rerank-model",
        )


# --------------------------------------------------------------------------------------------- #
# embedder-query
# --------------------------------------------------------------------------------------------- #


async def test_embedder_query_returns_a_vector_and_a_populated_token_accounting_from_config():
    client = _StubEmbeddingClient(vector=[1.0, 0.0, 0.0])
    ctx = _ctx("embedder-query", config={"query": "what films did Ed Wood direct"}, clients={"embedding": client})

    result = await LIGHTRAG_EMBEDDER_QUERY_PART.body(ctx)

    assert result["vector"] == [1.0, 0.0, 0.0]
    assert result["tokens"].call_count == 1
    assert result["tokens"].prompt_tokens > 0
    assert client.calls == [["what films did Ed Wood direct"]]


async def test_embedder_query_prefers_the_keywords_node_output_when_present():
    client = _StubEmbeddingClient(vector=[0.0, 1.0, 0.0])
    ctx = _ctx(
        "embedder-query",
        config={"query": "config-path text, must not be used"},
        inputs={"keywords": {"query": "keywords-path text"}},
        clients={"embedding": client},
    )

    result = await LIGHTRAG_EMBEDDER_QUERY_PART.body(ctx)

    assert result["query"] == "keywords-path text"
    assert client.calls == [["keywords-path text"]]


# --------------------------------------------------------------------------------------------- #
# chunk-vector
# --------------------------------------------------------------------------------------------- #


async def test_chunk_vector_returns_items_ordered_by_descending_score(store_root):
    store = FaissVectorStore(namespace="chunks", workspace="ws", store_root=store_root)
    await store.upsert(
        ids=["low", "high", "mid"],
        # Directions, not magnitudes: FaissVectorStore L2-normalises on write, so two vectors
        # differing only in magnitude collapse to the same cosine similarity — these differ by
        # angle from the [1,0,0] query instead (1.0 / ~0.707 / 0.0 cosine similarity respectively).
        embeddings=[[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.7, 0.7, 0.0]],
        metadatas=[{"content": "low"}, {"content": "high"}, {"content": "mid"}],
    )
    await store.index_done_callback()

    ctx = _ctx(
        "chunk-vector",
        config={"top_k": 10},
        inputs={"embedder-query": {"vector": [1.0, 0.0, 0.0]}},
        stores={"vector": store},
    )

    result = await LIGHTRAG_RETRIEVER_CHUNK_TOPK_PART.body(ctx)

    scores = [item["score"] for item in result["items"]]
    assert scores == sorted(scores, reverse=True)
    assert [item["id"] for item in result["items"]] == ["high", "mid", "low"]


# --------------------------------------------------------------------------------------------- #
# heading-backfill
# --------------------------------------------------------------------------------------------- #


async def test_heading_backfill_attaches_kv_content_and_heading_breadcrumb(store_root):
    kv = SqliteKVStore(namespace="text_chunks", workspace="ws", store_root=store_root)
    await kv.upsert(
        {
            "chunk-1": {
                "content": "authoritative KV content",
                "file_path": "doc.txt",
                "heading": {"heading": "Section 2"},
                "parent_headings": ["Document", "Chapter 1"],
            }
        }
    )
    await kv.index_done_callback()

    ctx = _ctx(
        "heading-backfill",
        inputs={"chunk-vector": {"items": [{"id": "chunk-1", "score": 0.9, "content": "stale vector content"}]}},
        stores={"kv": kv},
    )

    result = await LIGHTRAG_CHUNK_HEADING_BACKFILLER_PART.body(ctx)

    item = result["items"][0]
    assert item["content"] == "authoritative KV content"
    assert item["content_headings"] == "Document > Chapter 1 > Section 2"
    assert item["file_path"] == "doc.txt"


async def test_heading_backfill_omits_content_headings_when_the_kv_record_has_no_heading_fields(store_root):
    kv = SqliteKVStore(namespace="text_chunks", workspace="ws", store_root=store_root)
    await kv.upsert({"chunk-1": {"content": "plain content"}})
    await kv.index_done_callback()

    ctx = _ctx(
        "heading-backfill",
        inputs={"chunk-vector": {"items": [{"id": "chunk-1", "score": 0.5}]}},
        stores={"kv": kv},
    )

    result = await LIGHTRAG_CHUNK_HEADING_BACKFILLER_PART.body(ctx)

    assert "content_headings" not in result["items"][0]
    assert result["items"][0]["content"] == "plain content"


async def test_heading_backfill_leaves_an_item_untouched_when_no_kv_record_exists(store_root):
    kv = SqliteKVStore(namespace="text_chunks", workspace="ws", store_root=store_root)
    ctx = _ctx(
        "heading-backfill",
        inputs={"chunk-vector": {"items": [{"id": "missing-chunk", "score": 0.1, "content": "from vector store"}]}},
        stores={"kv": kv},
    )

    result = await LIGHTRAG_CHUNK_HEADING_BACKFILLER_PART.body(ctx)

    assert result["items"][0] == {"id": "missing-chunk", "score": 0.1, "content": "from vector store"}


# --------------------------------------------------------------------------------------------- #
# rerank (D-09: declared pass-through by default)
# --------------------------------------------------------------------------------------------- #


async def test_rerank_returns_items_in_unchanged_order_and_score_by_default():
    items = [{"id": "a", "score": 0.9, "content": "x"}, {"id": "b", "score": 0.1, "content": "y"}]
    ctx = _ctx("rerank", inputs={"heading-backfill": {"items": items}})

    result = await LIGHTRAG_RERANKER_CROSS_ENCODER_PART.body(ctx)

    assert result["items"] == items


def test_rerank_part_declares_calls_rerank_even_as_a_pass_through():
    assert "calls_rerank" in LIGHTRAG_RERANKER_CROSS_ENCODER_PART.effects


async def test_rerank_with_live_rerank_requested_and_no_client_wired_is_refused_by_name():
    """A plain dict client mapping (this file's usual ``_ctx`` shape) would raise a raw
    ``KeyError`` on a missing key — not the named refusal the scheduler's real deny-by-default
    view produces. This test threads the real ``CapabilityScopedClients``/``_ScopedClientsView``
    pair (``runner/scheduler.py``'s exact wrapping) so the *named* refusal is what is asserted,
    not merely that something raises.
    """
    from databasise.clients import CapabilityScopedClients
    from databasise.runner.scheduler import _ScopedClientsView

    items = [{"id": "a", "score": 0.9, "content": "x"}]
    declared_effects = LIGHTRAG_RERANKER_CROSS_ENCODER_PART.effects
    scoped_clients = _ScopedClientsView(
        CapabilityScopedClients({}, declared_effects), declared_effects
    )
    ctx = _ctx(
        "rerank",
        config={"live_rerank": True, "query": "q"},
        inputs={"heading-backfill": {"items": items}},
        clients=scoped_clients,
    )

    with pytest.raises(ClientNotWiredError) as exc_info:
        await LIGHTRAG_RERANKER_CROSS_ENCODER_PART.body(ctx)
    assert "rerank" in str(exc_info.value)


async def test_rerank_with_live_rerank_requested_and_a_client_wired_reorders_items():
    items = [{"id": "a", "score": 0.2, "content": "x"}, {"id": "b", "score": 0.1, "content": "y"}]
    client = _StubRerankClient(ranked_indices=[1, 0])
    ctx = _ctx(
        "rerank",
        config={"live_rerank": True, "query": "q"},
        inputs={"heading-backfill": {"items": items}},
        clients={"rerank": client},
    )

    result = await LIGHTRAG_RERANKER_CROSS_ENCODER_PART.body(ctx)

    assert [item["id"] for item in result["items"]] == ["b", "a"]
    assert client.calls == [("q", ["x", "y"])]


# --------------------------------------------------------------------------------------------- #
# assemble
# --------------------------------------------------------------------------------------------- #


async def test_assemble_joins_ordered_item_content_into_one_context_string_with_no_effects():
    assert LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART.effects == []
    items = [{"content": "first chunk"}, {"content": "second chunk"}]
    ctx = _ctx("assemble", config={"order_policy": "naive-template"}, inputs={"rerank": {"items": items}})

    result = await LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART.body(ctx)

    assert "first chunk" in result["context"]
    assert "second chunk" in result["context"]
    assert result["context"].index("first chunk") < result["context"].index("second chunk")
    assert result["order_policy"] == "naive-template"


async def test_assemble_respects_a_configured_max_total_tokens_budget_by_dropping_whole_chunks():
    items = [{"content": "a" * 40}, {"content": "b" * 40}, {"content": "c" * 40}]
    # ~4 chars/token heuristic (assemble.py's own documented ratio): a tiny budget keeps only the
    # first chunk, never a partial chunk.
    ctx = _ctx("assemble", config={"max_total_tokens": 10}, inputs={"rerank": {"items": items}})

    result = await LIGHTRAG_ASSEMBLER_KG_CONTEXT_PART.body(ctx)

    assert result["chunk_count"] == 1
    assert "a" * 40 in result["context"]
    assert "b" * 40 not in result["context"]


# --------------------------------------------------------------------------------------------- #
# generate
# --------------------------------------------------------------------------------------------- #


async def test_generate_returns_a_completion_and_a_populated_token_accounting():
    client = _StubLLMClient(completion="the answer")
    ctx = _ctx(
        "generate",
        config={"query": "what is the answer"},
        inputs={"assemble": {"context": "some context"}},
        clients={"llm": client},
    )

    result = await LIGHTRAG_GENERATOR_LLM_PART.body(ctx)

    assert result["completion"] == "the answer"
    assert result["tokens"].call_count == 1
    assert result["tokens"].prompt_tokens + result["tokens"].completion_tokens > 0
    assert len(client.calls) == 1


async def test_generate_with_no_assemble_input_still_calls_the_llm_with_just_the_query():
    """The ``bypass`` arm's own shape: ``generate`` with ``deps: []``."""
    client = _StubLLMClient()
    ctx = _ctx("generate", config={"query": "direct question"}, inputs={}, clients={"llm": client})

    result = await LIGHTRAG_GENERATOR_LLM_PART.body(ctx)

    assert result["completion"]
    assert client.calls[0][0]["content"] == "direct question"


# --------------------------------------------------------------------------------------------- #
# embedder-index
# --------------------------------------------------------------------------------------------- #


async def test_embedder_index_part_declares_calls_embedding_and_writes_artifact_quarantined():
    assert set(LIGHTRAG_EMBEDDER_INDEX_PART.effects) == {"calls_embedding", "writes_artifact"}
    assert LIGHTRAG_EMBEDDER_INDEX_PART.artifact_scope == "quarantined"


async def test_embedder_index_with_no_sample_configured_makes_no_embedding_call():
    client = _StubEmbeddingClient(vector=[0.0, 0.0, 1.0])
    ctx = _ctx("embedder-index", config={}, clients={"embedding": client})

    result = await LIGHTRAG_EMBEDDER_INDEX_PART.body(ctx)

    assert result["artifact"] == {"vectors": {}}
    assert client.calls == []


async def test_embedder_index_with_a_sample_embeds_exactly_those_chunk_ids():
    client = _StubEmbeddingClient(vector=[0.0, 0.0, 1.0])
    sample = [{"chunk_id": "c1", "text": "text one"}, {"chunk_id": "c2", "text": "text two"}]
    ctx = _ctx("embedder-index", config={"sample": sample}, clients={"embedding": client})

    result = await LIGHTRAG_EMBEDDER_INDEX_PART.body(ctx)

    assert set(result["artifact"]["vectors"].keys()) == {"c1", "c2"}
    assert result["artifact"]["vectors"]["c1"] == [0.0, 0.0, 1.0]
    assert client.calls == [["text one", "text two"]]
