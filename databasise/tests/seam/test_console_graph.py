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

from databasise.seam import refusals, rest
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
    from databasise.stores.graph import _ClientRegistry
    for key in client.app.state.engine._graph_holds:
        _ClientRegistry.release(key)
    client.app.state.engine._graph_holds.clear()
    held = pycozo.Client("rocksdb", str(path.resolve()), dataframe=False)
    try:
        busy = client.post("/graph/nodes", json={})
    finally:
        held.close()
    assert busy.status_code == 409, (busy.status_code, busy.text)
    assert busy.json().get("refusal_type") == "StoreBusyError", busy.text
    assert busy.json().get("store_kind") == "graph", busy.text


def test_graph_nodes_corrupted_graph_is_a_named_fault_and_openapi_declares_409(tmp_path):
    root = tmp_path / "store"
    graph_dir = root / "ws" / _NAMESPACE / "graph.cozo"
    graph_dir.mkdir(parents=True)
    app = _operator_app(root)
    client = TestClient(app)

    corrupted = client.post("/graph/nodes", json={})
    assert corrupted.status_code == 502, (corrupted.status_code, corrupted.text)
    assert corrupted.json().get("refusal_type") == "ForeignEngineRefusalError", corrupted.text
    assert corrupted.json().get("failure_class") == "StoreCorrupted", corrupted.text
    assert list(graph_dir.iterdir()) == [], "the read created files in a non-database directory"

    declared = app.openapi()["paths"].get("/graph/nodes", {}).get("post", {}).get("responses", {})
    assert {"409", "502", "503"} <= set(declared), sorted(declared)


# ---- 16-09 (CONN-12): POST /graph/node, one node's edges as references plus the allowlist ----

_SECRET = "secret corpus text"
_EDGE_KEYS = {"src", "tgt", "edge_types", "weight"}


async def _build_graph_with_attrs(store_root, namespace, edges):
    """A graph with the given ``(src, tgt, attrs)`` edges (16-08's ``_build_graph`` takes no attrs)."""
    store = CozoGraphStore(namespace, "ws", store_root)
    for src, tgt, attrs in edges:
        await store.upsert_edge(src, tgt, attrs)
    await store.index_done_callback()
    await store.finalize()


async def test_graph_node_lists_a_known_nodes_edges_with_paging(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    client = TestClient(_operator_app(root))
    await _build_graph_with_attrs(
        root,
        _NAMESPACE,
        [
            ("a1", "a2", {"weight": 2.0, "description": _SECRET}),
            ("a1", "a3", {"weight": 1.0}),
            ("a1", "b1", {"weight": 1.0}),
            ("a2", "b1", {"weight": 1.0}),
        ],
    )

    first = client.post("/graph/node", json={"selector": None, "node_id": "a1", "limit": 2, "offset": 0})
    assert first.status_code == 200, (first.status_code, first.text)
    body = first.json()
    assert body.get("id") == "a1" and body.get("degree") == 3, body
    edges = body.get("edges") or []
    assert [(e.get("src"), e.get("tgt")) for e in edges] == [("a1", "a2"), ("a1", "a3")], body
    assert all(set(e) == _EDGE_KEYS for e in edges), body
    assert all(e["edge_types"] is None for e in edges), body
    assert edges[0]["weight"] == 2.0, body
    assert body.get("next_offset") == 2, body
    assert _SECRET not in first.text, "edge description text crossed the seam"

    last = client.post("/graph/node", json={"node_id": "a1", "limit": 2, "offset": 2})
    assert last.status_code == 200, (last.status_code, last.text)
    assert [(e.get("src"), e.get("tgt")) for e in last.json().get("edges") or []] == [("a1", "b1")], last.text
    assert last.json().get("next_offset") is None, last.text


async def test_graph_node_edges_and_unknown_node_422(tmp_path):
    # CONN-12 row node: the new refusal exists, the allowlist holds for both families, 422 not 404.
    assert getattr(refusals, "UnknownGraphNodeError", None) is not None, "refusals has no UnknownGraphNodeError (CONN-12)"
    unknown_cls = refusals.UnknownGraphNodeError

    root = tmp_path / "store"
    root.mkdir()
    client = TestClient(_operator_app(root))
    await _build_graph_with_attrs(
        root, _NAMESPACE, [("a1", "a2", {"weight": 2.0, "description": _SECRET}), ("a1", "a3", {"weight": 1.0})]
    )
    await _build_graph_with_attrs(
        root,
        "hipporag-graph",
        [("e1", "e2", {"edge_types": ["synonymy"], "weight": 1.5, "cooccurrence_by_chunk": {"c1": 1}})],
    )

    lightrag = client.post("/graph/node", json={"node_id": "a1"})
    assert lightrag.status_code == 200, (lightrag.status_code, lightrag.text)
    assert [e.get("weight") for e in lightrag.json().get("edges") or []] == [2.0, 1.0], lightrag.text
    assert _SECRET not in lightrag.text

    hippo = client.post("/graph/node", json={"selector": {"capability": ["reads_graph"]}, "node_id": "e1"})
    assert hippo.status_code == 200, (hippo.status_code, hippo.text)
    (edge,) = hippo.json().get("edges") or [{}]
    assert set(edge) == _EDGE_KEYS, hippo.text
    assert edge.get("edge_types") == ["synonymy"] and edge.get("weight") == 1.5, hippo.text
    assert "cooccurrence_by_chunk" not in hippo.text

    unknown = client.post("/graph/node", json={"node_id": "nope"})
    assert unknown.status_code == 422, (unknown.status_code, unknown.text)
    assert unknown.json().get("refusal_type") == "UnknownGraphNodeError", unknown.text
    assert unknown.json().get("node_id") == "nope", unknown.text

    fresh = tmp_path / "fresh"
    fresh.mkdir()
    absent = TestClient(_operator_app(fresh)).post("/graph/node", json={"node_id": "nope"})
    assert absent.status_code == 422, (absent.status_code, absent.text)
    assert absent.json().get("refusal_type") == "UnknownGraphNodeError", absent.text

    assert rest._status_for(unknown_cls(node_id="x")) == 422
