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

import pytest
from databasise.clients.base import ChatResult
from databasise.parts.schema import NodeContext
from databasise.parts_core import CapabilityScopedStores, UndeclaredEffectError
from databasise.parts_core.lightrag.entity_hydrate_expand import (
    LIGHTRAG_ENTITY_HYDRATE_EXPAND_PART,
)
from databasise.parts_core.lightrag.entity_lookup import LIGHTRAG_ENTITY_LOOKUP_PART
from databasise.parts_core.lightrag.keywords import LIGHTRAG_KEYWORD_EXTRACTOR_PART
from databasise.parts_core.lightrag.relation_hydrate_expand import (
    LIGHTRAG_RELATION_HYDRATE_EXPAND_PART,
)
from databasise.parts_core.lightrag.relation_lookup import LIGHTRAG_RELATION_LOOKUP_PART
from databasise.runner.scheduler import _ScopedStoresView
from databasise.runner.trace import TokenAccounting
from databasise.stores.graph import CozoGraphStore
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


class _NamespaceRecordingVectorHandle:
    """A fake multi-namespace vector handle (``databasise.stores.vector.MultiNamespaceVectorStore``'s
    real call shape): records every namespace name ``select()`` was asked for, and returns the
    single real per-namespace store this test wired underneath, regardless of which name was
    requested — sufficient to assert *which* namespace a node asked for without needing more than
    one real namespace built per test.
    """

    def __init__(self, store: Any):
        self._store = store
        self.selected_namespaces: list[str] = []

    def select(self, namespace: str) -> Any:
        self.selected_namespaces.append(namespace)
        return self._store


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
    fake_vector = _NamespaceRecordingVectorHandle(store)

    ctx = _ctx(
        "entity-lookup",
        config={"top_k": 10},
        inputs={"embedder-query": {"vector": [1.0, 0.0, 0.0]}},
        stores={"vector": fake_vector},
    )

    result = await LIGHTRAG_ENTITY_LOOKUP_PART.body(ctx)

    assert fake_vector.selected_namespaces == ["entities"]
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
    fake_vector = _NamespaceRecordingVectorHandle(store)

    ctx = _ctx(
        "relation-lookup",
        config={"top_k": 10},
        inputs={"embedder-query": {"vector": [1.0, 0.0, 0.0]}},
        stores={"vector": fake_vector},
    )

    result = await LIGHTRAG_RELATION_LOOKUP_PART.body(ctx)

    assert fake_vector.selected_namespaces == ["relationships"]
    assert [(item["src_id"], item["tgt_id"]) for item in result["items"]] == [("C", "D"), ("A", "B")]
    scores = [item["score"] for item in result["items"]]
    assert scores == sorted(scores, reverse=True)


# --------------------------------------------------------------------------------------------- #
# entity-hydrate-expand / relation-hydrate-expand
# --------------------------------------------------------------------------------------------- #


async def test_entity_hydrate_expand_hydrates_seeds_and_expands_to_neighbour_relations(store_root):
    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace="ws", store_root=store_root)
    await graph.upsert_node("Alice", {"entity_type": "person", "description": "a person"})
    await graph.upsert_node("Bob", {"entity_type": "person", "description": "another person"})
    await graph.upsert_edge("Alice", "Bob", {"weight": "1.0", "description": "knows"})
    await graph.index_done_callback()

    ctx = _ctx(
        "entity-hydrate-expand",
        inputs={"entity-lookup": {"items": [{"id": "ent-alice", "score": 0.9, "entity_name": "Alice"}]}},
        stores={"graph": graph},
    )

    result = await LIGHTRAG_ENTITY_HYDRATE_EXPAND_PART.body(ctx)

    assert len(result["entities"]) == 1
    hydrated = result["entities"][0]
    assert hydrated["entity_name"] == "Alice"
    assert hydrated["description"] == "a person"
    assert hydrated["rank"] == 1
    assert hydrated["derived_from"] == ["ent-alice"]

    assert len(result["relations"]) == 1
    relation = result["relations"][0]
    assert set(relation["src_tgt"]) == {"Alice", "Bob"}
    assert relation["description"] == "knows"
    assert relation["derived_from"] == ["Alice"]
    assert result["missing_seeds"] == []
    await graph.finalize()


async def test_entity_hydrate_expand_reports_a_missing_seed_rather_than_dropping_it(store_root):
    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace="ws", store_root=store_root)
    ctx = _ctx(
        "entity-hydrate-expand",
        inputs={
            "entity-lookup": {
                "items": [{"id": "ent-ghost", "score": 0.5, "entity_name": "Ghost"}]
            }
        },
        stores={"graph": graph},
    )

    result = await LIGHTRAG_ENTITY_HYDRATE_EXPAND_PART.body(ctx)

    assert result["entities"] == []
    assert len(result["missing_seeds"]) == 1
    assert result["missing_seeds"][0]["entity_name"] == "Ghost"
    assert result["missing_seeds"][0]["missing"] is True
    await graph.finalize()


async def test_entity_hydrate_expand_reports_a_malformed_seed_missing_entity_name(store_root):
    """CR-01 regression: a seed lacking the required ``entity_name`` key must land in
    ``missing_seeds`` with a diagnostic naming the missing field, not raise ``KeyError`` and halt
    the whole node.
    """
    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace="ws", store_root=store_root)
    ctx = _ctx(
        "entity-hydrate-expand",
        inputs={"entity-lookup": {"items": [{"id": "ent-broken", "score": 0.3}]}},
        stores={"graph": graph},
    )

    result = await LIGHTRAG_ENTITY_HYDRATE_EXPAND_PART.body(ctx)

    assert result["entities"] == []
    assert len(result["missing_seeds"]) == 1
    entry = result["missing_seeds"][0]
    assert entry["missing"] is True
    assert entry["malformed_seed"] is True
    assert "entity_name" in entry["diagnostic"]
    assert entry["derived_from"] == ["ent-broken"]
    await graph.finalize()


async def test_entity_hydrate_expand_cannot_reach_the_vector_store(store_root):
    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace="ws", store_root=store_root)
    vector = FaissVectorStore(namespace="entities", workspace="ws", store_root=store_root)
    declared_effects = LIGHTRAG_ENTITY_HYDRATE_EXPAND_PART.effects
    scoped_stores = _ScopedStoresView(
        CapabilityScopedStores({"graph": graph, "vector": vector}, declared_effects), declared_effects
    )
    ctx = _ctx(
        "entity-hydrate-expand",
        inputs={"entity-lookup": {"items": []}},
        stores=scoped_stores,
    )

    with pytest.raises(UndeclaredEffectError):
        ctx.stores["vector"]

    await graph.finalize()
    await vector.finalize()


async def test_relation_hydrate_expand_hydrates_seeds_and_expands_to_endpoint_entities(store_root):
    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace="ws", store_root=store_root)
    await graph.upsert_node("Alice", {"entity_type": "person"})
    await graph.upsert_node("Bob", {"entity_type": "person"})
    await graph.upsert_edge("Alice", "Bob", {"weight": "1.0", "description": "knows"})
    await graph.index_done_callback()

    ctx = _ctx(
        "relation-hydrate-expand",
        inputs={
            "relation-lookup": {
                "items": [{"id": "rel-ab", "score": 0.8, "src_id": "Alice", "tgt_id": "Bob"}]
            }
        },
        stores={"graph": graph},
    )

    result = await LIGHTRAG_RELATION_HYDRATE_EXPAND_PART.body(ctx)

    assert len(result["relations"]) == 1
    relation = result["relations"][0]
    assert relation["src_id"] == "Alice"
    assert relation["tgt_id"] == "Bob"
    assert relation["description"] == "knows"
    assert relation["derived_from"] == ["rel-ab"]

    assert {e["entity_name"] for e in result["entities"]} == {"Alice", "Bob"}
    assert result["missing_seeds"] == []
    await graph.finalize()


async def test_relation_hydrate_expand_reports_a_missing_seed_rather_than_dropping_it(store_root):
    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace="ws", store_root=store_root)
    await graph.upsert_node("Alice", {"entity_type": "person"})
    await graph.index_done_callback()

    ctx = _ctx(
        "relation-hydrate-expand",
        inputs={
            "relation-lookup": {
                "items": [{"id": "rel-ghost", "score": 0.4, "src_id": "Alice", "tgt_id": "Nobody"}]
            }
        },
        stores={"graph": graph},
    )

    result = await LIGHTRAG_RELATION_HYDRATE_EXPAND_PART.body(ctx)

    assert result["relations"] == []
    assert len(result["missing_seeds"]) == 1
    assert result["missing_seeds"][0]["missing"] is True
    await graph.finalize()


async def test_relation_hydrate_expand_reports_a_malformed_seed_missing_src_or_tgt_id(store_root):
    """CR-01 regression: a seed lacking ``src_id``/``tgt_id`` must land in ``missing_seeds`` with a
    diagnostic naming the missing field, not raise ``KeyError`` and halt the whole node.
    """
    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace="ws", store_root=store_root)
    ctx = _ctx(
        "relation-hydrate-expand",
        inputs={
            "relation-lookup": {
                "items": [{"id": "rel-broken", "score": 0.2, "src_id": "Alice"}]
            }
        },
        stores={"graph": graph},
    )

    result = await LIGHTRAG_RELATION_HYDRATE_EXPAND_PART.body(ctx)

    assert result["relations"] == []
    assert len(result["missing_seeds"]) == 1
    entry = result["missing_seeds"][0]
    assert entry["missing"] is True
    assert entry["malformed_seed"] is True
    assert "tgt_id" in entry["diagnostic"]
    assert entry["derived_from"] == ["rel-broken"]
    await graph.finalize()


async def test_relation_hydrate_expand_cannot_reach_the_kv_store(store_root):
    from databasise.stores.kv import SqliteKVStore

    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace="ws", store_root=store_root)
    kv = SqliteKVStore(namespace="text_chunks", workspace="ws", store_root=store_root)
    declared_effects = LIGHTRAG_RELATION_HYDRATE_EXPAND_PART.effects
    scoped_stores = _ScopedStoresView(
        CapabilityScopedStores({"graph": graph, "kv": kv}, declared_effects), declared_effects
    )
    ctx = _ctx(
        "relation-hydrate-expand",
        inputs={"relation-lookup": {"items": []}},
        stores=scoped_stores,
    )

    with pytest.raises(UndeclaredEffectError):
        ctx.stores["kv"]

    await graph.finalize()
