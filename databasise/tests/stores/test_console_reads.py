"""16-07: store-level spies for the operator console reads (CONN-10 here; CONN-11 and CONN-13 are
added by later plans). A console read must not rebuild what it only lists.
"""

from __future__ import annotations

import os

import numpy as np

from databasise.stores import graph as graph_module
from databasise.stores import probes
from databasise.stores.graph import CozoGraphStore
from databasise.stores.vector import FaissVectorStore, load_committed


async def test_list_ids_never_reconstructs(store_root, monkeypatch):
    list_ids = getattr(FaissVectorStore, "list_ids", None)
    assert callable(list_ids), "FaissVectorStore has no list_ids (CONN-10)"

    writer = FaissVectorStore(namespace="ns", workspace="ws", store_root=store_root)
    await writer.upsert(
        ids=["c", "a", "b"],
        embeddings=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
    )
    await writer.index_done_callback()

    # The narrowest object a reconstructing read would call: the loaded index's own class.
    index_class = type(load_committed(store_root / "ws" / "ns").index)

    def _forbidden(self, *args, **kwargs):
        raise AssertionError("list_ids reconstructed a vector")

    monkeypatch.setattr(index_class, "reconstruct", _forbidden)

    reader = FaissVectorStore(namespace="ns", workspace="ws", store_root=store_root)
    assert list_ids(reader, 0, 2) == (["a", "b"], 3)
    assert list_ids(reader, 2, 2) == (["c"], 3)

    missing = FaissVectorStore(namespace="never", workspace="ws", store_root=store_root)
    assert list_ids(missing, 0, 10) == ([], 0)
    assert not (store_root / "ws" / "never").exists()


async def test_one_degree_query_per_page(store_root, monkeypatch):
    page = getattr(probes, "graph_node_page", None)
    assert callable(page), "probes has no graph_node_page (CONN-11)"

    writer = CozoGraphStore("g", "ws", store_root)
    for node in ["a1", "a2", "a3", "b1", "lonely"]:
        await writer.upsert_node(node, {})
    for src, tgt in [("a1", "a2"), ("a1", "a3"), ("a1", "b1"), ("a2", "b1"), ("a3", "a3")]:
        await writer.upsert_edge(src, tgt, {})
    await writer.index_done_callback()
    await writer.finalize()

    scripts: list[str] = []
    real = probes._run_immutable

    def _recorder(client, script, params):
        scripts.append(script)
        return real(client, script, params)

    def _forbidden(*args, **kwargs):
        raise AssertionError("the graph node page used CozoGraphStore")

    monkeypatch.setattr(probes, "_run_immutable", _recorder)
    monkeypatch.setattr(CozoGraphStore, "__init__", _forbidden)
    monkeypatch.setattr(CozoGraphStore, "node_degree", _forbidden)

    rows, total = page(store_root / "ws" / "g", "", 50, 0)
    assert rows == [("a1", 3), ("a2", 2), ("a3", 2), ("b1", 2), ("lonely", 0)]
    assert total == 5
    assert len([s for s in scripts if "is_in" in s]) == 1, scripts


async def test_held_graph_paths_sees_an_open_store_under_a_symlinked_root(tmp_path):
    """16-10 (CONN-13, D-17): the registry keys are resolved paths, so a store opened through a
    symlinked root is found by a resolved-workspace prefix and by no other workspace's prefix."""
    held = getattr(graph_module, "held_graph_paths", None)
    assert callable(held), "stores.graph has no held_graph_paths (CONN-13)"

    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real)
    prefix = str((link / "ws").resolve()) + os.sep
    other = str((link / "other").resolve()) + os.sep

    store = CozoGraphStore("chunk_entity_relation", "ws", link)
    try:
        assert held(prefix), "an open store under a symlinked root was not seen"
        assert held(other) == []
    finally:
        await store.finalize()
    assert held(prefix) == []
    assert held(other) == []
