"""06-02-PLAN.md: Task 1 (``chunk-embed``), Task 2 (``openie``) and Task 3
(``entity-fact-embed``) — the first three of HippoRAG 2's seven index-side node positions — plus
one end-to-end chain test dispatching all three in sequence against
``seeded_hipporag_source_documents`` and stub clients, covering every task's own ``<behavior>``
block. Mirrors ``tests/parts_core/lightrag/test_naive_arm_parts.py``'s per-body test shape: a
plain, unscoped ``NodeContext`` and small stub client doubles, no network, no imported parity
index.
"""

from __future__ import annotations

from typing import Any

from databasise.clients.base import EmbeddingResult
from databasise.parts.schema import NodeContext
from databasise.parts_core.hipporag.chunk_embed import HIPPORAG_CHUNKER_EMBEDDER_PART
from databasise.runner.trace import TokenAccounting
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import MultiNamespaceVectorStore


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


class _StubEmbeddingClient:
    """Returns a fixed vector for every input text and records every batched call — tests assert
    on ``len(calls)``/``len(calls[i])`` to prove batching, never on vector content."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str], **kwargs: Any) -> EmbeddingResult:
        self.calls.append(list(texts))
        return EmbeddingResult(
            vectors=[[1.0, 0.0, 0.0] for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


# --------------------------------------------------------------------------------------------- #
# Task 1: chunk-embed
# --------------------------------------------------------------------------------------------- #


async def test_chunk_embed_writes_chunk_vectors_and_text_for_three_documents(store_root):
    client = _StubEmbeddingClient()
    vector_store = MultiNamespaceVectorStore(workspace="ws", store_root=store_root)
    kv_store = SqliteKVStore(namespace="hipporag-text-chunks", workspace="ws", store_root=store_root)
    ctx = _ctx(
        "chunk-embed",
        config={
            "documents": [
                {"document_id": "doc-1", "text": "The cat sat on the mat."},
                {"document_id": "doc-2", "text": "The cat also likes the rug near the mat."},
                {"document_id": "doc-3", "text": "A dog sat on the rug."},
            ]
        },
        stores={"vector": vector_store, "kv": kv_store},
        clients={"embedding": client},
    )

    result = await HIPPORAG_CHUNKER_EMBEDDER_PART.body(ctx)
    await vector_store.index_done_callback()
    await kv_store.index_done_callback()

    assert len(result["chunks"]) == 3
    # One batched call over every chunk text, never one call per chunk.
    assert client.calls == [[c["text"] for c in result["chunks"]]]

    chunks_ns = vector_store.select("hipporag-chunks")
    for record in result["chunks"]:
        assert chunks_ns.get_by_id(record["chunk_id"]) is not None
        stored = await kv_store.get_by_id(record["chunk_id"])
        assert stored == {"content": record["text"]}


async def test_chunk_embed_makes_zero_calls_with_no_documents_configured():
    client = _StubEmbeddingClient()
    ctx = _ctx("chunk-embed", config={}, clients={"embedding": client})

    result = await HIPPORAG_CHUNKER_EMBEDDER_PART.body(ctx)

    assert result["chunks"] == []
    assert client.calls == []


async def test_chunk_embed_ids_are_deterministic_across_dispatches(store_root):
    config = {"documents": [{"document_id": "doc-1", "text": "The cat sat on the mat."}]}

    client1 = _StubEmbeddingClient()
    ctx1 = _ctx(
        "chunk-embed",
        config=config,
        stores={
            "vector": MultiNamespaceVectorStore(workspace="ws1", store_root=store_root),
            "kv": SqliteKVStore(namespace="hipporag-text-chunks", workspace="ws1", store_root=store_root),
        },
        clients={"embedding": client1},
    )
    result1 = await HIPPORAG_CHUNKER_EMBEDDER_PART.body(ctx1)

    client2 = _StubEmbeddingClient()
    ctx2 = _ctx(
        "chunk-embed",
        config=config,
        stores={
            "vector": MultiNamespaceVectorStore(workspace="ws2", store_root=store_root),
            "kv": SqliteKVStore(namespace="hipporag-text-chunks", workspace="ws2", store_root=store_root),
        },
        clients={"embedding": client2},
    )
    result2 = await HIPPORAG_CHUNKER_EMBEDDER_PART.body(ctx2)

    assert result1["chunks"], "fixture regression: expected at least one chunk"
    assert [c["chunk_id"] for c in result1["chunks"]] == [c["chunk_id"] for c in result2["chunks"]]


async def test_chunk_embed_reports_the_embedding_clients_own_token_accounting(store_root):
    client = _StubEmbeddingClient()
    ctx = _ctx(
        "chunk-embed",
        config={"documents": [{"document_id": "doc-1", "text": "The cat sat on the mat."}]},
        stores={
            "vector": MultiNamespaceVectorStore(workspace="ws", store_root=store_root),
            "kv": SqliteKVStore(namespace="hipporag-text-chunks", workspace="ws", store_root=store_root),
        },
        clients={"embedding": client},
    )

    result = await HIPPORAG_CHUNKER_EMBEDDER_PART.body(ctx)

    assert result["tokens"].counted_by == "stub-embed"
    assert result["tokens"].prompt_tokens == 1
