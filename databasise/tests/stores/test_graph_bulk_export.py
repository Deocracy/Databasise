"""06-01-PLAN.md Task 3: §14.2's no-pointwise-emulation rule made observable for
``CozoGraphStore.export_to_igraph`` — a loop-based implementation would scale its own Cozo query
count with node/edge count; this store's real implementation issues exactly two queries whatever
the graph's size. Mirrors ``databasise/tests/stores/test_graph_frozen_bugs.py``'s own store-test
shape and negative-control convention (a negative control proving a comparison has teeth).
"""

from __future__ import annotations

import itertools

from databasise.stores.graph import CozoGraphStore

_WORKSPACE = "bulk-export-test"


async def _seeded_store(store_root, namespace: str, node_count: int, edge_count: int) -> CozoGraphStore:
    store = CozoGraphStore(namespace=namespace, workspace=_WORKSPACE, store_root=store_root)
    node_ids = [f"n{i}" for i in range(node_count)]
    for node_id in node_ids:
        await store.upsert_node(node_id, {})
    pairs = list(itertools.combinations(node_ids, 2))[:edge_count]
    for index, (src, tgt) in enumerate(pairs):
        await store.upsert_edge(src, tgt, {"weight": float(index + 1)})
    await store.index_done_callback()
    return store


def _counting_run(store: CozoGraphStore) -> "list[int]":
    """Wraps ``store._run`` with a call counter — returns a one-element mutable list holding the
    running count, so the caller can read it after ``export_to_igraph`` returns."""
    counter = [0]
    original_run = store._run

    async def counting_run(script, params=None):
        counter[0] += 1
        return await original_run(script, params)

    store._run = counting_run
    return counter


async def test_export_issues_exactly_two_cozo_queries_regardless_of_graph_size(store_root):
    small_store = await _seeded_store(store_root, "small", node_count=3, edge_count=3)
    small_counter = _counting_run(small_store)
    small_graph = await small_store.export_to_igraph()
    assert small_counter[0] == 2
    assert small_graph.vcount() == 3
    assert small_graph.ecount() == 3

    large_store = await _seeded_store(store_root, "large", node_count=30, edge_count=60)
    large_counter = _counting_run(large_store)
    large_graph = await large_store.export_to_igraph()
    assert large_counter[0] == 2
    assert large_graph.vcount() == 30
    assert large_graph.ecount() == 60


async def test_every_stored_node_id_and_edge_weight_round_trips(store_root):
    store = await _seeded_store(store_root, "roundtrip", node_count=5, edge_count=6)
    graph = await store.export_to_igraph()

    assert set(graph.vs["name"]) == {f"n{i}" for i in range(5)}
    assert sorted(graph.es["weight"]) == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]


async def test_mutating_a_stored_weight_changes_the_exported_weight_negative_control(store_root):
    """Negative control: a comparison of exported weights must have teeth — mutating one stored
    edge's weight and re-exporting must change the corresponding exported value."""
    store = await _seeded_store(store_root, "negctl", node_count=3, edge_count=3)
    before = sorted((await store.export_to_igraph()).es["weight"])

    await store.upsert_edge("n0", "n1", {"weight": 999.0})
    await store.index_done_callback()
    after = sorted((await store.export_to_igraph()).es["weight"])

    assert before != after
    assert 999.0 in after
