"""06-01-PLAN.md Task 3: drives ``_ppr_body`` directly (the same call shape
``databasise.parts.registry.dispatch`` uses) against a hand-seeded graph and a hand-built reset
vector — proving the NaN/negative-zeroing guard, the passage-partition-only readback, and pinning
the exact ``personalized_pagerank`` call shape against an independently-constructed igraph call
made in this test module, with a negative control (changing ``damping``) proving that comparison
has teeth.
"""

from __future__ import annotations

import math

import pytest

from databasise.parts.schema import NodeContext
from databasise.parts_core.hipporag.ppr import _ppr_body
from databasise.stores.graph import CozoGraphStore

_WORKSPACE = "ppr-test"


async def _seeded_graph(store_root, namespace: str) -> CozoGraphStore:
    store = CozoGraphStore(namespace=namespace, workspace=_WORKSPACE, store_root=store_root)
    await store.upsert_node("entity:cat", {})
    await store.upsert_node("entity:mat", {})
    await store.upsert_node("chunk:c1", {})
    await store.upsert_node("chunk:c2", {})
    await store.upsert_edge("entity:cat", "entity:mat", {"weight": 1.0})
    await store.upsert_edge("entity:mat", "chunk:c1", {"weight": 1.0})
    await store.upsert_edge("chunk:c1", "chunk:c2", {"weight": 0.5})
    await store.index_done_callback()
    return store


def _ctx(graph_store, join_output, *, damping: float | None = None) -> NodeContext:
    config: dict = {}
    if damping is not None:
        config["damping"] = damping
    return NodeContext(
        node_id="ppr",
        config=config,
        inputs={"reset-vector-join": join_output},
        stores={"graph": graph_store},
        clients={},
    )


async def test_nan_and_negative_reset_entries_are_zeroed_before_the_call(store_root):
    graph_store = await _seeded_graph(store_root, "nan-zero-test")
    join_output = {
        "vertex_names": ["entity:cat", "entity:mat", "chunk:c1", "chunk:c2"],
        "reset_vector": [float("nan"), -2.0, 3.0, 4.0],
    }
    ctx = _ctx(graph_store, join_output)

    result = await _ppr_body(ctx)

    graph = await graph_store.export_to_igraph()
    weight_by_name = dict(zip(join_output["vertex_names"], join_output["reset_vector"], strict=True))
    expected_reset = []
    for name in graph.vs["name"]:
        raw = weight_by_name[name]
        if isinstance(raw, float) and math.isnan(raw):
            raw = 0.0
        if raw < 0:
            raw = 0.0
        expected_reset.append(raw)
    assert expected_reset == [3.0, 4.0, 0.0, 0.0]  # chunk:c1, chunk:c2, entity:cat, entity:mat order

    expected_scores = graph.personalized_pagerank(
        vertices=range(graph.vcount()),
        damping=0.5,
        directed=False,
        weights="weight",
        reset=expected_reset,
        implementation="prpack",
    )
    expected_passage_scores = {
        name: score
        for name, score in zip(graph.vs["name"], expected_scores, strict=True)
        if name.startswith("chunk:")
    }

    returned = {item["id"]: item["score"] for item in result["items"]}
    assert returned.keys() == expected_passage_scores.keys()
    for name, score in expected_passage_scores.items():
        assert returned[name] == pytest.approx(score)


async def test_readback_contains_only_the_passage_partition_sorted_descending(store_root):
    graph_store = await _seeded_graph(store_root, "readback-test")
    join_output = {
        "vertex_names": ["entity:cat", "entity:mat", "chunk:c1", "chunk:c2"],
        "reset_vector": [1.0, 1.0, 1.0, 1.0],
    }
    ctx = _ctx(graph_store, join_output)

    result = await _ppr_body(ctx)

    ids = [item["id"] for item in result["items"]]
    assert set(ids) == {"chunk:c1", "chunk:c2"}
    assert all(i.startswith("chunk:") for i in ids)
    scores = [item["score"] for item in result["items"]]
    assert scores == sorted(scores, reverse=True)


async def test_changing_damping_produces_a_different_score_vector_negative_control(store_root):
    """Negative control: the pinned-argument assertion above has teeth only if changing one of the
    pinned arguments (damping) actually changes the result."""
    graph_store = await _seeded_graph(store_root, "damping-negctl-test")
    join_output = {
        "vertex_names": ["entity:cat", "entity:mat", "chunk:c1", "chunk:c2"],
        "reset_vector": [1.0, 0.5, 2.0, 0.1],
    }

    result_default = await _ppr_body(_ctx(graph_store, join_output))
    result_higher = await _ppr_body(_ctx(graph_store, join_output, damping=0.85))

    scores_default = [item["score"] for item in result_default["items"]]
    scores_higher = [item["score"] for item in result_higher["items"]]
    assert scores_default != scores_higher
