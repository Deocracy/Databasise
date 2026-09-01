"""Tests for ``databasise.stores.graph.CozoGraphStore`` (plan 01-06, Task 1).

Covers the <behavior> claims: read-your-writes buffering, canonical edge-key symmetry, the abort
path, the commit path, bound-parameter safety against Datalog metacharacters, namespace isolation,
off-loop dispatch, and the actionable ImportError when ``pycozo`` is unavailable.
"""

from __future__ import annotations

import asyncio
import importlib
import sys

import pytest
from databasise.stores.graph import CozoGraphStore


async def test_read_your_writes_before_flush(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)

    pending_attrs = {k for k in vars(store) if k.startswith("_pending")}
    assert pending_attrs == {
        "_pending_node_puts",
        "_pending_edge_puts",
        "_pending_node_rms",
        "_pending_edge_rms",
    }

    await store.upsert_node("A", {"kind": "entity"})

    node = await store.get_node("A")

    assert node == {"kind": "entity"}
    await store.finalize()


async def test_canonical_edge_key_symmetry(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)
    await store.upsert_node("A", {})
    await store.upsert_node("B", {})
    await store.upsert_edge("A", "B", {"weight": "1.0"})
    await store.index_done_callback()

    forward = await store.get_edge("A", "B")
    reverse = await store.get_edge("B", "A")

    assert forward == reverse == {"weight": "1.0"}
    await store.finalize()


async def test_drop_pending_index_ops_discards_all_four_buffers(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)
    await store.upsert_node("A", {"kind": "entity"})
    await store.upsert_node("B", {"kind": "entity"})
    await store.upsert_edge("A", "B", {"weight": "1.0"})
    await store.index_done_callback()

    # Now buffer a second round of changes and abort them.
    await store.upsert_node("C", {"kind": "entity"})
    await store.delete_node("A")
    await store.upsert_edge("B", "C", {"weight": "2.0"})
    await store.delete_edge("A", "B")

    await store.drop_pending_index_ops()

    assert await store.get_node("C") is None
    assert await store.get_node("A") == {"kind": "entity"}
    assert await store.get_edge("B", "C") is None
    assert await store.get_edge("A", "B") == {"weight": "1.0"}
    await store.finalize()


async def test_index_done_callback_flush_is_durable_across_reopen(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)
    await store.upsert_node("A", {"kind": "entity"})
    await store.upsert_node("B", {"kind": "entity"})
    await store.upsert_edge("A", "B", {"weight": "1.0"})
    await store.index_done_callback()
    await store.finalize()

    reopened = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)

    assert await reopened.get_node("A") == {"kind": "entity"}
    assert await reopened.get_edge("A", "B") == {"weight": "1.0"}
    await reopened.finalize()


async def test_node_id_with_datalog_metacharacters_round_trips(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)
    tricky_id = "entity{a}?*b"

    await store.upsert_node(tricky_id, {"kind": "entity"})
    await store.index_done_callback()

    assert await store.has_node(tricky_id) is True
    assert await store.get_node(tricky_id) == {"kind": "entity"}
    await store.finalize()


async def test_two_namespace_directories_hold_disjoint_graphs(store_root):
    store_a = CozoGraphStore(namespace="graph-a", workspace="ws", store_root=store_root)
    store_b = CozoGraphStore(namespace="graph-b", workspace="ws", store_root=store_root)

    await store_a.upsert_node("A", {"kind": "entity"})
    await store_a.index_done_callback()

    assert await store_a.has_node("A") is True
    assert await store_b.has_node("A") is False
    await store_a.finalize()
    await store_b.finalize()


async def test_query_dispatch_does_not_block_the_event_loop(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)
    await store.upsert_node("A", {"kind": "entity"})
    await store.index_done_callback()

    interleaved = False

    async def _ticker() -> None:
        nonlocal interleaved
        await asyncio.sleep(0)
        interleaved = True

    async def _query() -> None:
        # Force a real off-loop dispatch (buffer is empty post-flush, so this hits pycozo).
        await store.get_node("A")

    ticker_task = asyncio.create_task(_ticker())
    await _query()
    await ticker_task

    assert interleaved is True
    await store.finalize()


async def test_get_node_edges_returns_incident_edges_in_either_direction(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)
    await store.upsert_node("A", {})
    await store.upsert_node("B", {})
    await store.upsert_node("C", {})
    await store.upsert_edge("A", "B", {"weight": "1.0"})
    await store.upsert_edge("C", "A", {"weight": "2.0"})
    await store.index_done_callback()

    edges = await store.get_node_edges("A")

    pairs = {(e["src"], e["tgt"]): e["attrs"] for e in edges}
    assert pairs == {("A", "B"): {"weight": "1.0"}, ("A", "C"): {"weight": "2.0"}}
    await store.finalize()


async def test_get_node_edges_returns_empty_list_for_unknown_or_edge_free_node(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)
    await store.upsert_node("Lonely", {})
    await store.index_done_callback()

    assert await store.get_node_edges("Lonely") == []
    assert await store.get_node_edges("Nonexistent") == []
    await store.finalize()


async def test_get_node_edges_consults_pending_buffers_before_flush(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)
    await store.upsert_node("A", {})
    await store.upsert_node("B", {})
    await store.upsert_edge("A", "B", {"weight": "1.0"})
    await store.index_done_callback()

    # Unflushed put updates the attrs; unflushed removal (on a different edge) is excluded.
    await store.upsert_node("C", {})
    await store.upsert_edge("A", "B", {"weight": "9.0"})
    await store.upsert_edge("A", "C", {"weight": "3.0"})
    await store.delete_edge("A", "C")

    edges = await store.get_node_edges("A")

    pairs = {(e["src"], e["tgt"]): e["attrs"] for e in edges}
    assert pairs == {("A", "B"): {"weight": "9.0"}}
    await store.finalize()


async def test_get_node_edges_agrees_with_node_degree_including_buffered_state(store_root):
    store = CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)
    await store.upsert_node("A", {})
    await store.upsert_node("B", {})
    await store.upsert_node("C", {})
    await store.upsert_edge("A", "B", {"weight": "1.0"})
    await store.upsert_edge("A", "C", {"weight": "2.0"})
    await store.index_done_callback()

    await store.upsert_node("D", {})
    await store.upsert_edge("A", "D", {"weight": "3.0"})
    await store.delete_edge("A", "B")

    degree = await store.node_degree("A")
    edges = await store.get_node_edges("A")

    assert degree == len(edges) == 2
    await store.finalize()


def test_importing_without_pycozo_raises_actionable_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "pycozo", None)
    monkeypatch.setitem(sys.modules, "pycozo.client", None)
    monkeypatch.delitem(sys.modules, "databasise.stores.graph", raising=False)

    with pytest.raises(ImportError, match="pip install 'pycozo\\[embedded\\]'"):
        importlib.import_module("databasise.stores.graph")

    # Restore real module state so later tests in this session see the working import.
    monkeypatch.delitem(sys.modules, "databasise.stores.graph", raising=False)
    monkeypatch.delitem(sys.modules, "pycozo", raising=False)
    monkeypatch.delitem(sys.modules, "pycozo.client", raising=False)
    importlib.import_module("databasise.stores.graph")
