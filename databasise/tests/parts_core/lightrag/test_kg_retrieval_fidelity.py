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


# --------------------------------------------------------------------------------------------- #
# entity-hydrate-expand: v1's (rank, weight) order and one degree lookup per node
# --------------------------------------------------------------------------------------------- #


class _CountingGraph:
    """A graph stub counting node_degree calls per node. Edge endpoints are canonically ordered,
    as the real store returns them; weights are strings, as Cozo returns them."""

    _DEGREES = {"A": 3, "B": 2, "C": 2, "D": 4}
    # B-WR-04: "9.0" vs "10.0" orders one way as strings and the other as floats.
    _EDGES = [("A", "B", "9.0"), ("A", "C", "10.0"), ("A", "D", "1.0")]

    def __init__(self) -> None:
        self.degree_calls: dict[str, int] = {}

    async def get_node(self, name: str) -> dict[str, Any] | None:
        return {"entity_type": "thing"} if name in self._DEGREES else None

    async def node_degree(self, name: str) -> int:
        self.degree_calls[name] = self.degree_calls.get(name, 0) + 1
        return self._DEGREES[name]

    async def get_node_edges(self, name: str) -> list[dict[str, Any]]:
        return [
            {"src": src, "tgt": tgt, "attrs": {"weight": weight}}
            for src, tgt, weight in self._EDGES
            if name in (src, tgt)
        ]


async def test_one_hop_relations_sort_by_rank_then_weight_descending_with_one_degree_per_node():
    from databasise.parts_core.lightrag.entity_hydrate_expand import (
        LIGHTRAG_ENTITY_HYDRATE_EXPAND_PART,
    )

    graph = _CountingGraph()
    seeds = [{"id": "e-a", "entity_name": "A"}, {"id": "e-b", "entity_name": "B"}]
    result = await LIGHTRAG_ENTITY_HYDRATE_EXPAND_PART.body(
        _ctx("entity-hydrate-expand", inputs={"entity-lookup": {"items": seeds}}, stores={"graph": graph})
    )

    # v1 operate.py:5259-5261: A-D (rank 7), A-C (rank 5, weight 10.0), A-B (rank 5, weight 9.0).
    # A string compare would put A-B ("9.0") before A-C ("10.0").
    assert [tuple(r["src_tgt"]) for r in result["relations"]] == [("A", "D"), ("A", "C"), ("A", "B")]
    assert graph.degree_calls == {"A": 1, "B": 1, "C": 1, "D": 1}


# --------------------------------------------------------------------------------------------- #
# chunk-sel-kg: separate entity and relation selection, VECTOR via embedder-query
# --------------------------------------------------------------------------------------------- #

_ENTITIES = [
    {"entity_name": "E1", "source_id": "c1<SEP>c2"},
    {"entity_name": "E2", "source_id": "c3"},
]
_RELATIONS = [
    {"src_tgt": ["A", "B"], "source_id": "c2<SEP>c4"},
    {"src_tgt": ["C", "D"], "source_id": "c5"},
]
# Query [1, 0, 0]: entity side scores c2 > c1 > c3, relation side c4 > c5.
_CHUNK_VECTORS = {
    "c1": [0.8, 0.6, 0.0],
    "c2": [1.0, 0.0, 0.0],
    "c3": [0.0, 1.0, 0.0],
    "c4": [0.6, 0.8, 0.0],
    "c5": [0.0, 0.0, 1.0],
}


async def _chunk_stores(store_root: Any) -> tuple[Any, Any]:
    from databasise.stores.kv import SqliteKVStore
    from databasise.stores.vector import FaissVectorStore

    kv = SqliteKVStore(namespace="text_chunks", workspace="ws", store_root=store_root)
    await kv.upsert({cid: {"content": f"text {cid}"} for cid in _CHUNK_VECTORS})
    vector = FaissVectorStore(namespace="chunks", workspace="ws", store_root=store_root)
    await vector.upsert(ids=list(_CHUNK_VECTORS), embeddings=list(_CHUNK_VECTORS.values()))
    await vector.index_done_callback()

    class _Handle:
        def select(self, namespace: str) -> Any:
            assert namespace == "chunks"
            return vector

    return kv, _Handle()


def _chunk_sel_inputs(embedder_out: dict[str, Any] | None) -> dict[str, Any]:
    inputs: dict[str, Any] = {
        "budget-entities": {"items": _ENTITIES},
        "budget-relations": {"items": _RELATIONS},
    }
    if embedder_out is not None:
        inputs["embedder-query"] = embedder_out
    return inputs


async def test_chunk_sel_kg_vector_selects_entity_and_relation_chunks_separately(store_root):
    from databasise.parts_core.lightrag.chunk_sel_kg import LIGHTRAG_CHUNK_SELECTOR_KG_PART

    kv, vectors = await _chunk_stores(store_root)
    result = await LIGHTRAG_CHUNK_SELECTOR_KG_PART.body(
        _ctx(
            "chunk-sel-kg",
            config={"pick_method": "VECTOR", "fallback_pick_method": "WEIGHT", "related_chunk_number": 2},
            inputs=_chunk_sel_inputs({"vector": [1.0, 0.0, 0.0]}),
            stores={"kv": kv, "vector": vectors},
        )
    )

    # Entity side: int(2 * 2 / 2) = 2 of {c1, c2, c3} -> c2, c1. Relation side: c2 is already an
    # entity chunk, so 2 of {c4, c5} -> c4, c5. Round-robin entity, relation, entity, relation.
    assert [item["chunk_id"] for item in result["items"]] == ["c2", "c4", "c1", "c5"]
    assert result["pick_method_used"] == "VECTOR"


async def test_chunk_sel_kg_without_a_query_vector_falls_back_to_weight(store_root):
    from databasise.parts_core.lightrag.chunk_sel_kg import LIGHTRAG_CHUNK_SELECTOR_KG_PART

    kv, vectors = await _chunk_stores(store_root)
    result = await LIGHTRAG_CHUNK_SELECTOR_KG_PART.body(
        _ctx(
            "chunk-sel-kg",
            config={"pick_method": "VECTOR", "fallback_pick_method": "WEIGHT", "related_chunk_number": 2},
            inputs=_chunk_sel_inputs(None),
            stores={"kv": kv, "vector": vectors},
        )
    )

    # Weighted polling per side: entity side c1, c2, c3; relation side (c2 excluded) c4, c5.
    assert [item["chunk_id"] for item in result["items"]] == ["c1", "c4", "c2", "c5", "c3"]
    assert result["pick_method_used"] == "WEIGHT"


# --------------------------------------------------------------------------------------------- #
# join-chunks and the base wiring
# --------------------------------------------------------------------------------------------- #


async def test_join_chunks_puts_vector_chunks_first_and_dedups_by_chunk_id():
    from databasise.parts_core.lightrag.join_roundrobin import LIGHTRAG_JOIN_ROUNDROBIN_PART
    from databasise.wirings.resolve import load_base

    config = dict(load_base()["nodes"]["join-chunks"]["config"])
    result = await LIGHTRAG_JOIN_ROUNDROBIN_PART.body(
        _ctx(
            "join-chunks",
            config=config,
            inputs={
                "chunk-sel-kg": {"items": [{"chunk_id": "c1"}, {"chunk_id": "c4"}]},
                "chunk-vector": {"items": [{"id": "c1"}, {"id": "c9"}]},
            },
        )
    )
    keys = [item.get("chunk_id") or item.get("id") for item in result["items"]]
    assert keys == ["c1", "c9", "c4"]


def test_base_wiring_feeds_chunk_sel_kg_the_query_vector_and_rerank_the_query():
    from databasise.parts.registry import default_registry
    from databasise.seam.engine import _inject_query
    from databasise.validator.parse import parse_wiring
    from databasise.wirings.resolve import load_base, resolve_arm

    base = load_base()
    assert "embedder-query" in base["nodes"]["chunk-sel-kg"]["deps"]
    assert "rerank" in base["consumes_query"]

    resolved = _inject_query(resolve_arm("hybrid"), "the query")
    assert resolved["nodes"]["rerank"]["config"]["query"] == "the query"
    for arm in ("naive", "bypass", "hybrid", "local", "global"):
        report = parse_wiring(resolve_arm(arm), default_registry()).report
        assert report.ok, (arm, [v.code for v in report.violations])
