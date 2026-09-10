"""06-05-PLAN.md: Task 1 (``fact-edges``/``passage-edges``), Task 2 (``synonymy-edges``) and
Task 3 (``graph-augment-persist``) — the four remaining index-side node positions of HippoRAG 2,
covering each task's own ``<behavior>`` block plus an end-to-end index-side run and a round-trip
persist -> ``export_to_igraph`` proof. Mirrors ``test_index_side_extraction.py``'s per-body test
shape: a plain, unscoped ``NodeContext`` and small stub client/store doubles, no network, no
imported parity index.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.parts.schema import NodeContext
from databasise.parts_core.hipporag.chunk_embed import HIPPORAG_CHUNKER_EMBEDDER_PART
from databasise.parts_core.hipporag.entity_fact_embed import (
    CHUNK_VERTEX_PREFIX,
    ENTITY_VERTEX_PREFIX,
    HIPPORAG_ENTITY_FACT_EMBEDDER_PART,
)
from databasise.parts_core.hipporag.fact_edges import HIPPORAG_FACT_EDGE_BUILDER_PART
from databasise.parts_core.hipporag.graph_augment_persist import HIPPORAG_GRAPH_MATERIALIZER_PART
from databasise.parts_core.hipporag.openie import _fact_id as openie_fact_id
from databasise.parts_core.hipporag.openie import HIPPORAG_OPENIE_EXTRACTOR_PART
from databasise.parts_core.hipporag.passage_edges import HIPPORAG_PASSAGE_EDGE_BUILDER_PART
from databasise.parts_core.hipporag.synonymy_edges import HIPPORAG_SYNONYMY_EDGE_BUILDER_PART
from databasise.runner.trace import TokenAccounting
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore, MultiNamespaceVectorStore


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


def _finding(subject: str, predicate: str, obj: str, chunk_id: str) -> dict[str, Any]:
    return {
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "chunk_id": chunk_id,
        "fact_id": openie_fact_id(subject, predicate, obj),
    }


def _entity_ref(name: str) -> str:
    return f"{ENTITY_VERTEX_PREFIX}{name.strip().lower()}"


def _chunk_ref(chunk_id: str) -> str:
    return f"{CHUNK_VERTEX_PREFIX}{chunk_id}"


# --------------------------------------------------------------------------------------------- #
# Task 1: fact-edges, passage-edges
# --------------------------------------------------------------------------------------------- #


async def test_fact_edges_emits_one_symmetric_edge_with_cooccurrence_count_weight():
    findings = [
        _finding("cat", "sat_on", "mat", "c1"),
        _finding("cat", "sat_on", "mat", "c2"),
        _finding("mat", "under", "cat", "c3"),  # reversed subject/object, same pair
    ]
    ctx = _ctx("fact-edges", inputs={"openie": {"findings": findings}})

    result = await HIPPORAG_FACT_EDGE_BUILDER_PART.body(ctx)

    assert len(result["edges"]) == 1
    edge = result["edges"][0]
    assert edge["weight"] == 3.0
    assert {edge["src"], edge["tgt"]} == {_entity_ref("cat"), _entity_ref("mat")}


async def test_fact_edges_are_canonically_ordered_regardless_of_source_order():
    result_ab = await HIPPORAG_FACT_EDGE_BUILDER_PART.body(
        _ctx("fact-edges", inputs={"openie": {"findings": [_finding("cat", "sat_on", "mat", "c1")]}})
    )
    result_ba = await HIPPORAG_FACT_EDGE_BUILDER_PART.body(
        _ctx("fact-edges", inputs={"openie": {"findings": [_finding("mat", "under", "cat", "c1")]}})
    )

    assert (result_ab["edges"][0]["src"], result_ab["edges"][0]["tgt"]) == (
        result_ba["edges"][0]["src"],
        result_ba["edges"][0]["tgt"],
    )


async def test_passage_edges_emits_one_edge_per_chunk_entity_pair_at_unit_weight():
    findings = [_finding("cat", "sat_on", "mat", "c1")]
    ctx = _ctx("passage-edges", inputs={"openie": {"findings": findings}})

    result = await HIPPORAG_PASSAGE_EDGE_BUILDER_PART.body(ctx)

    pairs = {(e["src"], e["tgt"]) for e in result["edges"]}
    assert pairs == {
        (_chunk_ref("c1"), _entity_ref("cat")),
        (_chunk_ref("c1"), _entity_ref("mat")),
    }
    assert all(e["weight"] == 1.0 for e in result["edges"])


async def test_fact_and_passage_edges_reach_no_store_and_no_client():
    findings = [_finding("cat", "sat_on", "mat", "c1")]

    fact_result = await HIPPORAG_FACT_EDGE_BUILDER_PART.body(
        _ctx("fact-edges", inputs={"openie": {"findings": findings}}, stores={}, clients={})
    )
    passage_result = await HIPPORAG_PASSAGE_EDGE_BUILDER_PART.body(
        _ctx("passage-edges", inputs={"openie": {"findings": findings}}, stores={}, clients={})
    )

    assert fact_result["edges"]
    assert passage_result["edges"]


async def test_fact_and_passage_edges_emit_empty_list_given_no_findings():
    fact_result = await HIPPORAG_FACT_EDGE_BUILDER_PART.body(
        _ctx("fact-edges", inputs={"openie": {"findings": []}})
    )
    passage_result = await HIPPORAG_PASSAGE_EDGE_BUILDER_PART.body(
        _ctx("passage-edges", inputs={"openie": {"findings": []}})
    )

    assert fact_result["edges"] == []
    assert passage_result["edges"] == []


# --------------------------------------------------------------------------------------------- #
# Task 2: synonymy-edges
# --------------------------------------------------------------------------------------------- #


async def test_synonymy_edges_emits_deduped_canonical_edges_above_threshold(store_root):
    entity_store = FaissVectorStore(
        namespace="hipporag-entities", workspace="synonymy-ws", store_root=store_root
    )
    # cat/kitten are near-identical (cosine ~1.0); rug is unrelated (cosine 0).
    await entity_store.upsert(
        ids=[_entity_ref("cat"), _entity_ref("kitten"), _entity_ref("rug")],
        embeddings=np.array(
            [[1.0, 0.01, 0.0], [1.0, 0.0, 0.01], [0.0, 1.0, 0.0]], dtype="float32"
        ),
        metadatas=[{}, {}, {}],
    )
    await entity_store.index_done_callback()

    vector_store = MultiNamespaceVectorStore(workspace="synonymy-ws", store_root=store_root)
    ctx = _ctx(
        "synonymy-edges",
        config={"synonymy_top_k": 2, "synonymy_threshold": 0.9},
        inputs={
            "entity-fact-embed": {
                "entities": [{"ref": _entity_ref("cat"), "surface_form": "cat"}]
            }
        },
        stores={"vector": vector_store},
    )

    result = await HIPPORAG_SYNONYMY_EDGE_BUILDER_PART.body(ctx)

    pairs = [(e["src"], e["tgt"]) for e in result["edges"]]
    assert (_entity_ref("cat"), _entity_ref("kitten")) in pairs
    assert len(pairs) == len(set(pairs))  # deduped
    assert all(pair[0] < pair[1] for pair in pairs)  # canonically ordered
    assert not any(_entity_ref("rug") in pair for pair in pairs)


async def test_synonymy_edges_zero_upstream_chunk_count_makes_no_store_read():
    ctx = _ctx(
        "synonymy-edges",
        config={"synonymy_top_k": 5, "synonymy_threshold": 0.8},
        inputs={"entity-fact-embed": {"entities": [], "facts": []}},
        stores={},
    )

    result = await HIPPORAG_SYNONYMY_EDGE_BUILDER_PART.body(ctx)

    assert result["edges"] == []


# --------------------------------------------------------------------------------------------- #
# Task 3: graph-augment-persist
# --------------------------------------------------------------------------------------------- #


def _edge(src: str, tgt: str, weight: float, edge_type: str) -> dict[str, Any]:
    return {"src": src, "tgt": tgt, "weight": weight, "edge_type": edge_type}


async def test_graph_augment_persist_writes_every_vertex_and_edge_as_quarantined(store_root):
    graph_store = CozoGraphStore(
        namespace="hipporag-graph", workspace="persist-ws", store_root=store_root
    )
    ctx = _ctx(
        "graph-augment-persist",
        inputs={
            "fact-edges": {
                "edges": [_edge(_entity_ref("cat"), _entity_ref("mat"), 2.0, "fact-cooccurrence")]
            },
            "passage-edges": {
                "edges": [_edge(_chunk_ref("c1"), _entity_ref("cat"), 1.0, "passage-entity")]
            },
            "synonymy-edges": {"edges": []},
        },
        stores={"graph": graph_store},
    )

    result = await HIPPORAG_GRAPH_MATERIALIZER_PART.body(ctx)

    assert result["artifact_scope"] == "quarantined"
    graph = await graph_store.export_to_igraph()
    assert set(graph.vs["name"]) == {_entity_ref("cat"), _entity_ref("mat"), _chunk_ref("c1")}
    assert sorted(graph.es["weight"]) == [1.0, 2.0]


async def test_graph_augment_persist_collapses_two_edge_types_into_summed_weight(store_root):
    graph_store = CozoGraphStore(
        namespace="hipporag-graph", workspace="collapse-ws", store_root=store_root
    )
    pair_a, pair_b = _entity_ref("cat"), _entity_ref("mat")
    ctx = _ctx(
        "graph-augment-persist",
        inputs={
            "fact-edges": {"edges": [_edge(pair_a, pair_b, 2.0, "fact-cooccurrence")]},
            "passage-edges": {"edges": []},
            "synonymy-edges": {"edges": [_edge(pair_b, pair_a, 0.95, "synonymy")]},
        },
        stores={"graph": graph_store},
    )

    await HIPPORAG_GRAPH_MATERIALIZER_PART.body(ctx)

    edge = await graph_store.get_edge(pair_a, pair_b)
    assert edge["weight"] == 2.0 + 0.95
    assert set(edge["edge_types"]) == {"fact-cooccurrence", "synonymy"}


async def test_graph_augment_persist_round_trips_through_export_to_igraph_with_negative_control(
    store_root,
):
    graph_store = CozoGraphStore(
        namespace="hipporag-graph", workspace="roundtrip-ws", store_root=store_root
    )
    ctx = _ctx(
        "graph-augment-persist",
        inputs={
            "fact-edges": {
                "edges": [_edge(_entity_ref("cat"), _entity_ref("mat"), 3.0, "fact-cooccurrence")]
            },
            "passage-edges": {"edges": []},
            "synonymy-edges": {"edges": []},
        },
        stores={"graph": graph_store},
    )
    await HIPPORAG_GRAPH_MATERIALIZER_PART.body(ctx)

    graph = await graph_store.export_to_igraph()
    assert set(graph.vs["name"]) == {_entity_ref("cat"), _entity_ref("mat")}
    assert graph.es["weight"] == [3.0]

    # Negative control: a mutated weight changes the exported value.
    await graph_store.upsert_edge(_entity_ref("cat"), _entity_ref("mat"), {"weight": 999.0})
    await graph_store.index_done_callback()
    mutated_graph = await graph_store.export_to_igraph()
    assert mutated_graph.es["weight"] == [999.0]


async def test_graph_augment_persist_with_three_empty_streams_persists_nothing(store_root):
    graph_store = CozoGraphStore(
        namespace="hipporag-graph", workspace="empty-ws", store_root=store_root
    )
    ctx = _ctx(
        "graph-augment-persist",
        inputs={
            "fact-edges": {"edges": []},
            "passage-edges": {"edges": []},
            "synonymy-edges": {"edges": []},
        },
        stores={"graph": graph_store},
    )

    result = await HIPPORAG_GRAPH_MATERIALIZER_PART.body(ctx)

    graph = await graph_store.export_to_igraph()
    assert graph.vcount() == 0
    assert graph.ecount() == 0
    assert result["artifact"]["node_count"] == 0


class _StubEmbeddingClient:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def embed(self, texts: list[str], **kwargs: Any) -> EmbeddingResult:
        self.calls.append(list(texts))
        return EmbeddingResult(
            vectors=[[1.0, 0.0, 0.0] for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubOpenieLLMClient:
    """Same alternating-NER/triples-by-call-index shape ``test_index_side_extraction.py``'s own
    stub establishes — call ``2*i`` is chunk ``i``'s NER call, call ``2*i + 1`` is chunk ``i``'s
    triple-extraction call.
    """

    def __init__(self, ner_responses: list[list[str]], triple_responses: list[Any]) -> None:
        self._ner_responses = ner_responses
        self._triple_responses = triple_responses
        self.calls: list[str] = []

    async def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> ChatResult:
        content = messages[0]["content"]
        self.calls.append(content)
        call_index = len(self.calls) - 1
        chunk_index, is_triple_call = divmod(call_index, 2)
        if is_triple_call:
            text = json.dumps({"triples": self._triple_responses[chunk_index]})
        else:
            text = json.dumps({"entities": self._ner_responses[chunk_index]})
        return ChatResult(
            text=text,
            tokens=TokenAccounting(
                prompt_tokens=5, completion_tokens=3, call_count=1, counted_by="stub-llm"
            ),
            resolved_model_identity="stub-llm-model",
        )


async def test_end_to_end_index_run_produces_a_graph_with_passage_and_entity_vertices(
    store_root, seeded_hipporag_source_documents
):
    workspace = "e2e-index-ws"
    embedding_client = _StubEmbeddingClient()
    vector_store = MultiNamespaceVectorStore(workspace=workspace, store_root=store_root)
    kv_store = SqliteKVStore(
        namespace="hipporag-text-chunks", workspace=workspace, store_root=store_root
    )
    graph_store = CozoGraphStore(
        namespace="hipporag-graph", workspace=workspace, store_root=store_root
    )

    chunk_ctx = _ctx(
        "chunk-embed",
        config={"documents": seeded_hipporag_source_documents},
        stores={"vector": vector_store, "kv": kv_store},
        clients={"embedding": embedding_client},
    )
    chunk_result = await HIPPORAG_CHUNKER_EMBEDDER_PART.body(chunk_ctx)
    await vector_store.index_done_callback()
    await kv_store.index_done_callback()

    llm_client = _StubOpenieLLMClient(
        ner_responses=[["cat", "mat"], ["cat", "rug"], ["dog", "rug"]],
        triple_responses=[
            [["cat", "sat_on", "mat"]],
            [["cat", "likes", "rug"]],
            [["dog", "sat_on", "rug"]],
        ],
    )
    openie_ctx = _ctx("openie", inputs={"chunk-embed": chunk_result}, clients={"llm": llm_client})
    openie_result = await HIPPORAG_OPENIE_EXTRACTOR_PART.body(openie_ctx)

    entity_ctx = _ctx(
        "entity-fact-embed",
        inputs={"openie": openie_result},
        stores={"vector": vector_store},
        clients={"embedding": embedding_client},
    )
    entity_result = await HIPPORAG_ENTITY_FACT_EMBEDDER_PART.body(entity_ctx)
    await vector_store.index_done_callback()

    fact_edges_result = await HIPPORAG_FACT_EDGE_BUILDER_PART.body(
        _ctx("fact-edges", inputs={"openie": openie_result})
    )
    passage_edges_result = await HIPPORAG_PASSAGE_EDGE_BUILDER_PART.body(
        _ctx("passage-edges", inputs={"openie": openie_result})
    )
    synonymy_ctx = _ctx(
        "synonymy-edges",
        config={"synonymy_top_k": 3, "synonymy_threshold": 0.99},
        inputs={"entity-fact-embed": entity_result},
        stores={"vector": vector_store},
    )
    synonymy_edges_result = await HIPPORAG_SYNONYMY_EDGE_BUILDER_PART.body(synonymy_ctx)

    persist_ctx = _ctx(
        "graph-augment-persist",
        inputs={
            "fact-edges": fact_edges_result,
            "passage-edges": passage_edges_result,
            "synonymy-edges": synonymy_edges_result,
        },
        stores={"graph": graph_store},
    )
    await HIPPORAG_GRAPH_MATERIALIZER_PART.body(persist_ctx)

    graph = await graph_store.export_to_igraph()
    vertex_names = set(graph.vs["name"])
    assert any(name.startswith(CHUNK_VERTEX_PREFIX) for name in vertex_names)
    assert any(name.startswith(ENTITY_VERTEX_PREFIX) for name in vertex_names)
