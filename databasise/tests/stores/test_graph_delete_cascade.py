"""STOR-10 (Phase 10 D-10): ``CozoGraphStore`` keeps edges consistent with nodes.

``delete_node`` cascades to incident edges, in the pending buffer and on disk, and ``upsert_edge``
auto-creates a missing endpoint with ``{}`` attributes, so no path leaves a dangling edge.
"""

from __future__ import annotations

from databasise.stores.graph import CozoGraphStore


def _open(store_root) -> CozoGraphStore:
    return CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)


async def _assert_x_gone(store: CozoGraphStore) -> None:
    assert await store.has_node("x") is False
    assert await store.node_degree("y") == 0
    assert await store.get_node_edges("x") == []
    assert await store.get_node_edges("y") == []
    assert await store.has_edge("x", "y") is False
    assert await store.get_edge("x", "y") is None
    graph = await store.export_to_igraph()
    assert graph.ecount() == 0
    assert graph.vs["name"] == ["y"]


async def _flushed_x_y(store_root) -> CozoGraphStore:
    store = _open(store_root)
    await store.upsert_node("x", {"kind": "entity"})
    await store.upsert_node("y", {"kind": "entity"})
    await store.upsert_edge("x", "y", {"weight": 1.0})
    await store.index_done_callback()
    return store


async def test_flushed_delete_removes_incident_edges_on_disk_and_after_reopen(store_root):
    store = await _flushed_x_y(store_root)

    await store.delete_node("x")
    await store.index_done_callback()

    await _assert_x_gone(store)
    await store.finalize()

    reopened = _open(store_root)
    await _assert_x_gone(reopened)
    await reopened.finalize()


async def test_buffered_delete_already_hides_incident_edges_before_flush(store_root):
    store = await _flushed_x_y(store_root)

    await store.delete_node("x")

    await _assert_x_gone(store)
    await store.finalize()


async def test_delete_drops_buffered_incident_edges_at_once(store_root):
    store = _open(store_root)
    await store.upsert_node("x", {})
    await store.upsert_node("y", {})
    await store.upsert_edge("x", "y", {})

    await store.delete_node("x")

    assert store._pending_edge_puts == {}
    await store.index_done_callback()
    await _assert_x_gone(store)
    await store.finalize()


async def test_delete_keeps_edges_that_do_not_touch_the_node(store_root):
    store = _open(store_root)
    for node in ("x", "y", "z"):
        await store.upsert_node(node, {})
    await store.upsert_edge("x", "y", {})
    await store.upsert_edge("y", "z", {})
    await store.index_done_callback()

    await store.delete_node("x")
    await store.index_done_callback()

    assert await store.node_degree("y") == 1
    assert await store.has_edge("y", "z") is True
    await store.finalize()


async def test_edge_to_a_missing_endpoint_creates_it_with_empty_attrs(store_root):
    store = _open(store_root)
    await store.upsert_node("y", {"kind": "entity"})
    await store.index_done_callback()

    await store.upsert_edge("y", "missing", {})
    await store.index_done_callback()

    assert await store.has_node("missing") is True
    assert await store.get_node("missing") == {}
    assert await store.get_node("y") == {"kind": "entity"}
    await store.finalize()


async def test_edge_on_an_empty_store_creates_both_endpoints(store_root):
    store = _open(store_root)

    await store.upsert_edge("p", "q", {})
    await store.index_done_callback()

    assert await store.has_node("p") is True
    assert await store.has_node("q") is True
    assert (await store.export_to_igraph()).ecount() == 1
    await store.finalize()


async def test_edge_after_delete_recreates_the_node_and_keeps_the_edge(store_root):
    store = await _flushed_x_y(store_root)

    await store.delete_node("x")
    await store.upsert_edge("x", "z", {})
    await store.index_done_callback()

    assert await store.has_node("x") is True
    assert await store.get_node("x") == {}
    assert await store.has_edge("x", "z") is True
    # The recreated x starts edge-free: the deleted node's old edge to y does not come back.
    assert await store.has_edge("x", "y") is False
    assert await store.node_degree("y") == 0
    await store.finalize()


async def test_pending_endpoints_need_no_disk_lookup(store_root, monkeypatch):
    store = _open(store_root)
    await store.upsert_node("a", {})
    await store.upsert_node("b", {})
    calls: list[str] = []
    real_run = store._run

    async def spy(script, params=None):
        calls.append(script)
        return await real_run(script, params)

    monkeypatch.setattr(store, "_run", spy)

    await store.upsert_edge("a", "b", {})

    assert calls == []
    await store.finalize()
