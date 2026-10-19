"""B-CR-02 (D-16, LRAG-18): v1's Faiss store drops every hit whose cosine is below
``cosine_better_than_threshold`` (default 0.2, ``v1/lightrag/kg/faiss_impl.py:421``). The three v2
vector lookups (chunk-vector, entity-lookup, relation-lookup) apply the same cut, so an off-topic
question reaches v1's "nothing above threshold" path: ``fail_response`` with no generation call.
"""

from __future__ import annotations

import dataclasses
import json

import numpy as np
import pytest
from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag.chunk_vector import (
    LIGHTRAG_RETRIEVER_CHUNK_TOPK_PART,
)
from databasise.parts_core.lightrag.entity_lookup import LIGHTRAG_ENTITY_LOOKUP_PART
from databasise.parts_core.lightrag.prompts import PROMPTS
from databasise.parts_core.lightrag.relation_lookup import LIGHTRAG_RELATION_LOOKUP_PART
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore, MultiNamespaceVectorStore
from databasise.tests.seam._probes import CountingLLMClient, counting_clients
from databasise.wirings.resolve import load_base, resolve_arm

_WS = "cosine-threshold"
_NEAR = [1.0, 0.0, 0.0]
_ORTHOGONAL = [0.0, 1.0, 0.0]


async def _seed(store_root) -> None:
    rows = {
        "chunks": [("chunk-near", {"content": "near"}), ("chunk-far", {"content": "far"})],
        "entities": [("ent-near", {"entity_name": "Near"}), ("ent-far", {"entity_name": "Far"})],
        "relationships": [
            ("rel-near", {"src_id": "Near", "tgt_id": "Far"}),
            ("rel-far", {"src_id": "Far", "tgt_id": "Near"}),
        ],
    }
    for namespace, items in rows.items():
        store = FaissVectorStore(namespace=namespace, workspace=_WS, store_root=store_root)
        await store.upsert(
            ids=[row_id for row_id, _ in items],
            embeddings=np.array([_NEAR, _ORTHOGONAL]),
            metadatas=[metadata for _, metadata in items],
        )
        await store.index_done_callback()
        await store.finalize()
    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace=_WS, store_root=store_root)
    for name, chunk in (("Near", "chunk-near"), ("Far", "chunk-far")):
        await graph.upsert_node(name, {"entity_type": "thing", "description": name, "source_id": chunk})
    await graph.upsert_edge(
        "Far", "Near", {"weight": "1.0", "description": "linked", "source_id": "chunk-far"}
    )
    await graph.index_done_callback()
    await graph.finalize()
    kv = SqliteKVStore(namespace="text_chunks", workspace=_WS, store_root=store_root)
    await kv.upsert(
        {
            "chunk-near": {"content": "near", "file_path": "near.txt"},
            "chunk-far": {"content": "far", "file_path": "far.txt"},
        }
    )
    await kv.index_done_callback()
    await kv.finalize()


@pytest.mark.parametrize(
    ("part", "node_id", "vector_key"),
    [
        (LIGHTRAG_RETRIEVER_CHUNK_TOPK_PART, "chunk-vector", "vector"),
        (LIGHTRAG_ENTITY_LOOKUP_PART, "entity-lookup", "ll_vector"),
        (LIGHTRAG_RELATION_LOOKUP_PART, "relation-lookup", "hl_vector"),
    ],
)
async def test_the_orthogonal_hit_is_dropped_and_the_near_hit_kept(
    store_root, part, node_id, vector_key
):
    await _seed(store_root)
    config = load_base()["nodes"][node_id]["config"]
    assert config["cosine_better_than_threshold"] == 0.2  # v1 COSINE_THRESHOLD, set in base.json

    result = await part.body(
        NodeContext(
            node_id=node_id,
            config=config,
            inputs={"embedder-query": {vector_key: _NEAR}},
            stores={"vector": MultiNamespaceVectorStore(workspace=_WS, store_root=store_root)},
            clients={},
        )
    )

    assert [item["id"].split("-")[1] for item in result["items"]] == ["near"]


class _KeywordLLM(CountingLLMClient):
    """Answers every call with both keyword lists filled, so global and local search too."""

    async def chat(self, messages, **kwargs):
        result = await super().chat(messages, **kwargs)
        keywords = {"high_level_keywords": ["topic"], "low_level_keywords": ["thing"]}
        return dataclasses.replace(result, text=json.dumps(keywords))


@pytest.mark.parametrize("arm", ["naive", "hybrid", "local", "global"])
async def test_an_off_topic_query_gets_fail_response_with_no_generation_call(store_root, arm):
    await _seed(store_root)
    clients = counting_clients([0.0, 0.0, 1.0])  # orthogonal to every stored vector
    clients["llm"] = _KeywordLLM()
    engine = Databasise(store_root=store_root, workspace=_WS, clients=clients)

    envelope = await engine._execute_resolved(QueryObject(text="off topic?"), resolve_arm(arm))

    assert not envelope.degraded, envelope.degradation_reason
    assert envelope.answer == PROMPTS["fail_response"]
    assert envelope.evidence == []
    keyword_calls = 0 if arm == "naive" else 1
    assert clients["llm"].calls == keyword_calls  # only the keyword call; generate makes none
