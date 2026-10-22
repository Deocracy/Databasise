"""16-08 (CONN-11): POST /graph/nodes, the operator graph browser's node page.

The route pages a fitted modality's graph nodes with degrees through a read path that follows
``probe_graph``: it never builds a ``CozoGraphStore``, and a graph held by another holder is a named 409
(D-15). New API is reached over HTTP, so before the change each row fails by a plain ``AssertionError``
(the route is a 404), never by an import error (16-RESEARCH Pitfall 1).
"""

from __future__ import annotations

import inspect

import pytest

pytest.importorskip("fastapi")

from databasise.seam.rest import create_app
from databasise.stores.graph import CozoGraphStore
from fastapi.testclient import TestClient

_NAMESPACE = "chunk_entity_relation"
_NODES = ["a1", "a2", "a3", "b1", "lonely"]
# a3-a3 is a self-loop: it counts once for a3, so a3 has degree 1 (a1) + 1 (self) = 2.
_EDGES = [("a1", "a2"), ("a1", "a3"), ("a1", "b1"), ("a2", "b1"), ("a3", "a3")]


def _operator_app(store_root):
    assert "operator" in inspect.signature(create_app).parameters, "create_app has no operator flag (CONN-01)"
    return create_app(store_root=store_root, workspace="ws", clients=None, operator=True)


async def _build_graph(store_root):
    store = CozoGraphStore(_NAMESPACE, "ws", store_root)
    for node in _NODES:
        await store.upsert_node(node, {"entity_type": "t"})
    for src, tgt in _EDGES:
        await store.upsert_edge(src, tgt, {"weight": 1.0})
    await store.index_done_callback()
    await store.finalize()  # releases the registry entry, so a raw client can hold the path


async def test_graph_nodes_page_degrees_prefix_and_busy_409(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    client = TestClient(_operator_app(root))

    # No graph yet: an empty page, and the read creates nothing.
    none = client.post("/graph/nodes", json={"selector": None, "prefix": "", "limit": 50, "offset": 0})
    assert none.status_code == 200, (none.status_code, none.text)
    assert none.json().get("total") == 0 and none.json().get("nodes") == [], none.text
    assert not (root / "ws" / _NAMESPACE).exists()

    await _build_graph(root)

    full = client.post("/graph/nodes", json={"selector": None, "prefix": "", "limit": 50, "offset": 0})
    assert full.status_code == 200, (full.status_code, full.text)
    page = full.json()
    nodes = page.get("nodes") or []
    assert [n.get("id") for n in nodes] == _NODES, page
    assert [n.get("degree") for n in nodes] == [3, 2, 2, 2, 0], page
    assert page.get("total") == 5 and page.get("next_offset") is None, page

    prefixed = client.post("/graph/nodes", json={"prefix": "a"})
    assert prefixed.status_code == 200, (prefixed.status_code, prefixed.text)
    assert [n.get("id") for n in prefixed.json().get("nodes") or []] == ["a1", "a2", "a3"], prefixed.text
    assert prefixed.json().get("total") == 3, prefixed.text

    first = client.post("/graph/nodes", json={"limit": 2, "offset": 0})
    assert first.json().get("next_offset") == 2, first.text
    last = client.post("/graph/nodes", json={"limit": 2, "offset": 4})
    assert last.status_code == 200 and last.json().get("next_offset") is None, last.text
    assert [n.get("id") for n in last.json().get("nodes") or []] == ["lonely"], last.text

    # Another holder on the same path: a named 409, never a 500.
    import pycozo

    path = root / "ws" / _NAMESPACE / "graph.cozo"
    held = pycozo.Client("rocksdb", str(path.resolve()), dataframe=False)
    try:
        busy = client.post("/graph/nodes", json={})
    finally:
        held.close()
    assert busy.status_code == 409, (busy.status_code, busy.text)
    assert busy.json().get("refusal_type") == "StoreBusyError", busy.text
    assert busy.json().get("store_kind") == "graph", busy.text
