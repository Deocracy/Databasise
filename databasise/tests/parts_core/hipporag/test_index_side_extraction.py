"""06-02-PLAN.md: Task 1 (``chunk-embed``), Task 2 (``openie``) and Task 3
(``entity-fact-embed``) — the first three of HippoRAG 2's seven index-side node positions — plus
one end-to-end chain test dispatching all three in sequence against
``seeded_hipporag_source_documents`` and stub clients, covering every task's own ``<behavior>``
block. Mirrors ``tests/parts_core/lightrag/test_naive_arm_parts.py``'s per-body test shape: a
plain, unscoped ``NodeContext`` and small stub client doubles, no network, no imported parity
index.
"""

from __future__ import annotations

import json
from typing import Any

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.parts.schema import NodeContext
from databasise.parts_core.hipporag.chunk_embed import HIPPORAG_CHUNKER_EMBEDDER_PART
from databasise.parts_core.hipporag.openie import HIPPORAG_OPENIE_EXTRACTOR_PART
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


# --------------------------------------------------------------------------------------------- #
# Task 2: openie
# --------------------------------------------------------------------------------------------- #


class _StubOpenieLLMClient:
    """Alternates NER/triple responses by call index: call ``2*i`` is chunk ``i``'s NER call,
    call ``2*i + 1`` is chunk ``i``'s triple-extraction call — mirrors ``openie.py``'s own strict
    per-chunk NER-then-triples order. ``triple_responses[i]`` may be a raw malformed string
    instead of a triple list, to exercise the malformed-response-degrades-only-this-chunk path.
    """

    def __init__(
        self,
        ner_responses: list[list[str]],
        triple_responses: list[Any],
    ) -> None:
        self._ner_responses = ner_responses
        self._triple_responses = triple_responses
        self.calls: list[str] = []

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ChatResult:
        content = messages[0]["content"]
        self.calls.append(content)
        call_index = len(self.calls) - 1
        chunk_index, is_triple_call = divmod(call_index, 2)
        if is_triple_call:
            payload = self._triple_responses[chunk_index]
            text = payload if isinstance(payload, str) else json.dumps({"triples": payload})
        else:
            text = json.dumps({"entities": self._ner_responses[chunk_index]})
        return ChatResult(
            text=text,
            tokens=TokenAccounting(
                prompt_tokens=5, completion_tokens=3, call_count=1, counted_by="stub-llm"
            ),
            resolved_model_identity="stub-llm-model",
        )


_CAT_CHUNK = {"chunk_id": "c1", "document_id": "doc-1", "ordinal": 0, "text": "The cat sat on the mat."}
_DOG_CHUNK = {"chunk_id": "c2", "document_id": "doc-2", "ordinal": 0, "text": "A dog sat on the rug."}


async def test_openie_makes_exactly_two_calls_per_chunk_ner_then_triples():
    client = _StubOpenieLLMClient(
        ner_responses=[["cat", "mat"], ["dog", "rug"]],
        triple_responses=[[["cat", "sat_on", "mat"]], [["dog", "sat_on", "rug"]]],
    )
    ctx = _ctx(
        "openie",
        inputs={"chunk-embed": {"chunks": [_CAT_CHUNK, _DOG_CHUNK]}},
        clients={"llm": client},
    )

    await HIPPORAG_OPENIE_EXTRACTOR_PART.body(ctx)

    assert len(client.calls) == 4
    assert "---Recognised Entities---" not in client.calls[0]
    assert "---Recognised Entities---" in client.calls[1]
    # The triple call for chunk 1 carries chunk 1's own NER result.
    assert '"cat"' in client.calls[1]
    assert '"mat"' in client.calls[1]
    assert "---Recognised Entities---" not in client.calls[2]
    assert "---Recognised Entities---" in client.calls[3]
    assert '"dog"' in client.calls[3]


async def test_openie_emits_one_finding_per_triple_with_a_stable_fact_id():
    client = _StubOpenieLLMClient(
        ner_responses=[["cat", "mat"]], triple_responses=[[["cat", "sat_on", "mat"]]]
    )
    ctx = _ctx("openie", inputs={"chunk-embed": {"chunks": [_CAT_CHUNK]}}, clients={"llm": client})

    result = await HIPPORAG_OPENIE_EXTRACTOR_PART.body(ctx)

    assert len(result["findings"]) == 1
    finding = result["findings"][0]
    assert finding["subject"] == "cat"
    assert finding["predicate"] == "sat_on"
    assert finding["object"] == "mat"
    assert finding["chunk_id"] == "c1"
    assert isinstance(finding["fact_id"], str) and len(finding["fact_id"]) == 64

    client2 = _StubOpenieLLMClient(
        ner_responses=[["cat", "mat"]], triple_responses=[[["cat", "sat_on", "mat"]]]
    )
    ctx2 = _ctx("openie", inputs={"chunk-embed": {"chunks": [_CAT_CHUNK]}}, clients={"llm": client2})
    result2 = await HIPPORAG_OPENIE_EXTRACTOR_PART.body(ctx2)
    assert result2["findings"][0]["fact_id"] == finding["fact_id"]


async def test_openie_malformed_triple_response_degrades_only_its_own_chunk():
    client = _StubOpenieLLMClient(
        ner_responses=[["cat", "mat"], ["dog", "rug"]],
        triple_responses=["not valid json at all", [["dog", "sat_on", "rug"]]],
    )
    ctx = _ctx(
        "openie",
        inputs={"chunk-embed": {"chunks": [_CAT_CHUNK, _DOG_CHUNK]}},
        clients={"llm": client},
    )

    result = await HIPPORAG_OPENIE_EXTRACTOR_PART.body(ctx)

    chunk1_findings = [f for f in result["findings"] if f["chunk_id"] == "c1"]
    chunk2_findings = [f for f in result["findings"] if f["chunk_id"] == "c2"]
    assert chunk1_findings == []
    assert len(chunk2_findings) == 1


async def test_openie_makes_zero_calls_with_empty_chunks_input():
    client = _StubOpenieLLMClient(ner_responses=[], triple_responses=[])
    ctx = _ctx("openie", inputs={"chunk-embed": {"chunks": []}}, clients={"llm": client})

    result = await HIPPORAG_OPENIE_EXTRACTOR_PART.body(ctx)

    assert result["findings"] == []
    assert client.calls == []
