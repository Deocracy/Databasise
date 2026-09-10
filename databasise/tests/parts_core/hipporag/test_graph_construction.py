"""06-05-PLAN.md: Task 1 (``fact-edges``/``passage-edges``), Task 2 (``synonymy-edges``) and
Task 3 (``graph-augment-persist``) — the four remaining index-side node positions of HippoRAG 2,
covering each task's own ``<behavior>`` block plus an end-to-end index-side run and a round-trip
persist -> ``export_to_igraph`` proof. Mirrors ``test_index_side_extraction.py``'s per-body test
shape: a plain, unscoped ``NodeContext`` and small stub client/store doubles, no network, no
imported parity index.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from databasise.parts.schema import NodeContext
from databasise.parts_core.hipporag.entity_fact_embed import (
    CHUNK_VERTEX_PREFIX,
    ENTITY_VERTEX_PREFIX,
)
from databasise.parts_core.hipporag.fact_edges import HIPPORAG_FACT_EDGE_BUILDER_PART
from databasise.parts_core.hipporag.openie import _fact_id as openie_fact_id
from databasise.parts_core.hipporag.passage_edges import HIPPORAG_PASSAGE_EDGE_BUILDER_PART
from databasise.parts_core.hipporag.synonymy_edges import HIPPORAG_SYNONYMY_EDGE_BUILDER_PART
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
