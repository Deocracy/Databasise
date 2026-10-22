"""Phase 16 lane C review fixes for the operator graph reads in ``databasise/stores/probes.py``."""

from __future__ import annotations

import asyncio
from pathlib import Path

from databasise.stores.graph import CozoGraphStore
from databasise.stores.probes import graph_node_edges, graph_node_page, probe_graph
from pycozo.client import Client


def _seed(root: Path, ids: list[str]) -> Path:
    async def _go() -> None:
        store = CozoGraphStore("g", "ws", root)
        for node_id in ids:
            await store.upsert_node(node_id, {})
        await store.index_done_callback()
        await store.finalize()

    asyncio.run(_go())
    return root / "ws" / "g"


def test_prefix_equal_to_a_node_id_returns_that_node(tmp_path: Path) -> None:
    # CR-01: Cozo 0.7.6 pushes starts_with on the key into a range scan with an exclusive lower bound
    d = _seed(tmp_path, ["a", "ab", "b", "Al", "Alice", "Alice Smith"])
    assert graph_node_page(d, "a", 50, 0) == ([("a", 0), ("ab", 0)], 2)
    assert graph_node_page(d, "Al", 50, 0) == ([("Al", 0), ("Alice", 0), ("Alice Smith", 0)], 3)
    assert graph_node_page(d, "Alice Smith", 50, 0) == ([("Alice Smith", 0)], 1)
    assert graph_node_page(d, "", 50, 0)[1] == 6


def test_marker_without_relations_reads_as_an_empty_graph(tmp_path: Path) -> None:
    # WR-02: a crash between the client open and _ensure_relations leaves a valid empty database
    d = tmp_path / "ws" / "g"
    d.mkdir(parents=True)
    Client("rocksdb", str(d / "graph.cozo"), dataframe=False).close()
    assert probe_graph(d) == "ok"
    assert graph_node_page(d, "", 50, 0) == ([], 0)
    assert graph_node_edges(d, "a", 50, 0) == (False, 0, [])
    c = Client("rocksdb", str(d / "graph.cozo"), dataframe=False)
    try:
        assert c.run("::relations", {}, True)["rows"] == []  # the reads created no relation
    finally:
        c.close()
