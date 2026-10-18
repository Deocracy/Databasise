"""10-07-PLAN.md (STOR-04, Phase 10 D-14): ``Databasise.health()`` is read-only. It probes every
namespace of every shipped wiring from one static list, creates nothing, and reports each store as
``ok``, ``absent``, ``corrupted`` or ``busy``. The drift test pins that list to the shipped wirings
and part modules (research Pitfall 19).
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import numpy as np

import databasise.seam.engine as engine_module
from databasise.seam.engine import Databasise
from databasise.stores.graph import CozoGraphStore, _ClientRegistry
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore
from databasise.tests.seam.test_corpus_status import _make_fake_run_corpus_op
from databasise.tests.stores.test_graph_lock import hold_graph_in_subprocess

_WS = "health-probe"
_KEYS = {
    "kv:text_chunks",
    "graph:chunk_entity_relation",
    "vector:chunks",
    "vector:entities",
    "vector:relationships",
    "kv:hipporag-text-chunks",
    "graph:hipporag-graph",
    "vector:hipporag-chunks",
    "vector:hipporag-entities",
    "vector:hipporag-facts",
}
_STATES = {"ok", "absent", "corrupted", "busy"}
_PACKAGE = Path(engine_module.__file__).resolve().parents[1]


def _engine(store_root, monkeypatch) -> Databasise:
    monkeypatch.setattr(engine_module, "run_corpus_op", _make_fake_run_corpus_op())
    return Databasise(store_root=store_root, workspace=_WS)


def _tree(root: Path) -> list[Path]:
    return sorted(root.rglob("*"))


async def _write_vector(store_root: Path, namespace: str = "chunks") -> Path:
    store = FaissVectorStore(namespace=namespace, workspace=_WS, store_root=store_root)
    await store.upsert(ids=["c1"], embeddings=np.array([[1.0, 0.0, 0.0]]), metadatas=[{"content": "x"}])
    await store.index_done_callback()
    await store.finalize()
    return store_root / _WS / namespace


def _relations(db_path: Path) -> list:
    key, shared = _ClientRegistry.acquire(db_path)
    try:
        return shared.client.run("::relations", {}, True)["rows"]
    finally:
        _ClientRegistry.release(key)


async def test_health_on_a_fresh_root_creates_nothing_and_reports_every_store_absent(store_root, monkeypatch):
    engine = _engine(store_root, monkeypatch)
    before = _tree(store_root)

    report = await engine.health()

    assert _tree(store_root) == before
    assert set(report.stores) == _KEYS
    assert set(report.stores.values()) == {"absent"}
    assert report.status == "degraded"


async def test_a_garbage_faiss_index_reports_corrupted(store_root, monkeypatch):
    ns_dir = await _write_vector(store_root)
    (ns_dir / "vector.faiss").write_bytes(b"not a faiss index")

    report = await _engine(store_root, monkeypatch).health()

    assert report.stores["vector:chunks"] == "corrupted"
    assert report.status == "degraded"


async def test_a_lone_faiss_file_reports_corrupted(store_root, monkeypatch):
    ns_dir = await _write_vector(store_root)
    (ns_dir / "vector.meta.json").unlink()

    report = await _engine(store_root, monkeypatch).health()

    assert report.stores["vector:chunks"] == "corrupted"


async def test_populated_stores_report_ok_and_the_probe_leaves_no_sidecar_or_relation(store_root, monkeypatch):
    await _write_vector(store_root)
    kv = SqliteKVStore(namespace="text_chunks", workspace=_WS, store_root=store_root)
    await kv.upsert({"c1": {"content": "x"}})
    await kv.index_done_callback()
    await kv.finalize()
    graph = CozoGraphStore("chunk_entity_relation", _WS, store_root)
    await graph.upsert_node("n1", {"entity_type": "x"})
    await graph.index_done_callback()
    await graph.finalize()
    db_path = store_root / _WS / "chunk_entity_relation" / "graph.cozo"
    relations_before = _relations(db_path)
    engine = _engine(store_root, monkeypatch)
    # RocksDB rotates its own files inside graph.cozo/data/ on open (research A3); nothing else may change.
    outside_data = lambda: [p for p in _tree(store_root) if db_path / "data" not in p.parents]  # noqa: E731
    before = outside_data()

    report = await engine.health()

    assert report.stores["kv:text_chunks"] == "ok"
    assert report.stores["graph:chunk_entity_relation"] == "ok"
    assert report.stores["vector:chunks"] == "ok"
    assert outside_data() == before
    assert not (store_root / _WS / "text_chunks" / "kv.sqlite3-wal").exists()
    assert not (store_root / _WS / "text_chunks" / "kv.sqlite3-shm").exists()
    assert _relations(db_path) == relations_before


async def test_a_graph_held_by_another_process_reports_busy(store_root, monkeypatch):
    engine = _engine(store_root, monkeypatch)
    with hold_graph_in_subprocess(store_root / _WS / "chunk_entity_relation" / "graph.cozo"):
        report = await engine.health()

    assert report.stores["graph:chunk_entity_relation"] == "busy"
    assert report.status == "degraded"


async def test_a_graph_held_in_this_process_reports_ok(store_root, monkeypatch):
    held = CozoGraphStore("chunk_entity_relation", _WS, store_root)
    try:
        report = await _engine(store_root, monkeypatch).health()
    finally:
        await held.finalize()

    assert report.stores["graph:chunk_entity_relation"] == "ok"


_VECTOR_PART_MODULES = (
    "databasise.parts_core.lightrag.chunk_vector",
    "databasise.parts_core.lightrag.entity_lookup",
    "databasise.parts_core.lightrag.relation_lookup",
    "databasise.parts_core.hipporag.chunk_embed",
    "databasise.parts_core.hipporag.entity_fact_embed",
    "databasise.parts_core.hipporag.fact_score",
)


def test_the_kv_and_graph_probes_match_the_shipped_wirings_store_namespaces():
    shipped = set()
    for family in ("lightrag", "hipporag"):
        namespaces = json.loads((_PACKAGE / "wirings" / family / "base.json").read_text())["store_namespaces"]
        shipped |= {(kind, namespaces[kind]) for kind in ("kv", "graph")}

    assert {(k, ns) for k, ns in engine_module._HEALTH_PROBES if k in ("kv", "graph")} == shipped


def test_the_vector_probes_match_the_part_modules_namespace_constants():
    shipped = {
        value
        for name in _VECTOR_PART_MODULES
        for attr, value in vars(importlib.import_module(name)).items()
        if attr.endswith("_NAMESPACE") and isinstance(value, str)
    }

    assert {ns for k, ns in engine_module._HEALTH_PROBES if k == "vector"} == shipped


def test_rest_health_serves_the_state_map(store_root, monkeypatch):
    from fastapi.testclient import TestClient

    from databasise.seam.rest import create_app

    monkeypatch.setattr(engine_module, "run_corpus_op", _make_fake_run_corpus_op())
    body = TestClient(create_app(store_root=store_root, workspace=_WS)).get("/health").json()

    assert set(body["stores"]) == _KEYS
    assert set(body["stores"].values()) <= _STATES
