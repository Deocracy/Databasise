"""11-01-PLAN.md (D-01): the v1 index readers and the ``lightrag/v1-index-sync`` part.

A synthetic v1 working dir (doc_status + text_chunks JSON, three Faiss pairs, a Cozo db) holds one
processed, one failed, one ``dup-*`` and one still-processing document, so the PROCESSED-only rule
is checked row by row. No v1 venv and no model server needed.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import faiss
import numpy as np
import pytest
from pycozo.client import Client as CozoClient

import databasise.parts_core.lightrag.full_delete as full_delete_module
import databasise.parts_core.lightrag.full_ingest as full_ingest_module
import databasise.seam.engine as engine_module
from databasise.parity.import_index import mirror_snapshot, read_v1_snapshot
from databasise.parts_core.lightrag.v1_index_sync import v1_index_sync_body
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore, MultiNamespaceVectorStore

_DIM = 8


def _write_faiss(v1_dir: Path, kind: str, rows: dict[str, dict[str, Any]]) -> None:
    index = faiss.IndexFlatIP(_DIM)
    vectors = np.eye(_DIM, dtype="float32")[: len(rows)]
    index.add(vectors)
    faiss.write_index(index, str(v1_dir / f"faiss_index_{kind}.index"))
    meta = {str(i): {"__id__": vid, "__created_at__": 0, **extra} for i, (vid, extra) in enumerate(rows.items())}
    (v1_dir / f"faiss_index_{kind}.index.meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _write_cozo(v1_dir: Path, nodes: dict[str, str], edges: dict[tuple[str, str], str]) -> None:
    client = CozoClient("rocksdb", str(v1_dir / "cozo_graph_chunk_entity_relation.db"), dataframe=False)
    try:
        client.run(":create nodes {id: String => attrs: Json}", {})
        client.run(":create edges {src: String, tgt: String => attrs: Json}", {})
        client.run(
            "?[id, attrs] <- $rows :put nodes {id => attrs}",
            {"rows": [[nid, {"source_id": src, "entity_type": "x"}] for nid, src in nodes.items()]},
        )
        client.run(
            "?[src, tgt, attrs] <- $rows :put edges {src, tgt => attrs}",
            {"rows": [[s, t, {"source_id": src, "weight": 1.0}] for (s, t), src in edges.items()]},
        )
    finally:
        client.close()


@pytest.fixture
def mixed_v1_dir(tmp_path: Path) -> Path:
    v1_dir = tmp_path / "lightrag-v1"
    v1_dir.mkdir()
    doc_status = {
        "docP": {"status": "processed", "chunks_list": ["c1"], "file_path": "unknown_source"},
        "docF": {"status": "failed", "chunks_list": ["c2"], "file_path": "unknown_source"},
        "dup-x": {"status": "failed", "chunks_list": [], "metadata": {"is_duplicate": True}},
        "docR": {"status": "processing", "chunks_list": ["c3"], "file_path": "unknown_source"},
    }
    (v1_dir / "kv_store_doc_status.json").write_text(json.dumps(doc_status), encoding="utf-8")
    chunks = {cid: {"content": f"text {cid}", "full_doc_id": doc} for cid, doc in (("c1", "docP"), ("c2", "docF"), ("c3", "docR"))}
    (v1_dir / "kv_store_text_chunks.json").write_text(json.dumps(chunks), encoding="utf-8")
    _write_faiss(v1_dir, "chunks", {cid: {"full_doc_id": rec["full_doc_id"], "content": rec["content"]} for cid, rec in chunks.items()})
    _write_faiss(v1_dir, "entities", {"ent-a": {"source_id": "c1"}, "ent-c": {"source_id": "c2"}, "ent-r": {"source_id": "c3"}})
    _write_faiss(v1_dir, "relationships", {"rel-ab": {"source_id": "c1"}, "rel-bc": {"source_id": "c2<SEP>c3"}})
    _write_cozo(
        v1_dir,
        nodes={"A": "c1", "B": "c2<SEP>c1", "C": "c2", "R": "c3"},
        edges={("A", "B"): "c1", ("A", "C"): "c1", ("B", "C"): "c2"},
    )
    return v1_dir


def test_the_snapshot_keeps_only_rows_of_processed_documents(mixed_v1_dir):
    snapshot = read_v1_snapshot(mixed_v1_dir)

    assert set(snapshot.text_chunks) == {"c1"}
    assert snapshot.vectors["chunks"][0] == ["c1"]
    assert snapshot.vectors["entities"][0] == ["ent-a"]
    assert snapshot.vectors["relationships"][0] == ["rel-ab"]
    assert snapshot.vectors["chunks"][1].shape == (1, _DIM)
    assert set(snapshot.nodes) == {"A", "B"}
    # A-C names c1 but its endpoint C is dropped; B-C names only a failed chunk.
    assert set(snapshot.edges) == {("A", "B")}


def test_the_unfiltered_snapshot_keeps_every_row(mixed_v1_dir):
    snapshot = read_v1_snapshot(mixed_v1_dir, processed_only=False)

    assert set(snapshot.text_chunks) == {"c1", "c2", "c3"}
    assert set(snapshot.nodes) == {"A", "B", "C", "R"}


def test_an_absent_dir_or_doc_status_file_is_no_snapshot(tmp_path):
    assert read_v1_snapshot(tmp_path / "missing") is None
    (tmp_path / "empty").mkdir()
    assert read_v1_snapshot(tmp_path / "empty") is None


def test_an_unreadable_doc_status_file_raises(tmp_path):
    (tmp_path / "kv_store_doc_status.json").write_text("{not json", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        read_v1_snapshot(tmp_path)


async def test_the_mirror_prunes_only_ids_its_previous_manifest_lists(mixed_v1_dir, tmp_path):
    full = read_v1_snapshot(mixed_v1_dir, processed_only=False)
    kept = read_v1_snapshot(mixed_v1_dir)
    kv = SqliteKVStore(namespace="text_chunks", workspace="ws", store_root=tmp_path)
    vector = MultiNamespaceVectorStore(workspace="ws", store_root=tmp_path)
    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace="ws", store_root=tmp_path)
    try:
        await kv.upsert({"foreign": {"content": "a parity row"}})
        await mirror_snapshot(full, kv=kv, vector=vector, graph=graph)
        for store in (kv, vector, graph):
            await store.index_done_callback()

        await mirror_snapshot(kept, kv=kv, vector=vector, graph=graph, manifest=full.ids())
        for store in (kv, vector, graph):
            await store.index_done_callback()

        assert await kv.get_by_id("c1") is not None and await kv.get_by_id("c2") is None
        assert await kv.get_by_id("foreign") is not None
        assert vector.select("chunks").get_by_id("c3") is None
        assert sorted(await graph.get_all_labels()) == ["A", "B"]
        assert await graph.has_edge("A", "B") and not await graph.has_edge("A", "C")
    finally:
        for store in (kv, vector, graph):
            await store.finalize()


class _NoStores:
    def __getitem__(self, key: str) -> Any:
        raise AssertionError(f"the sync touched store {key!r} with no v1 dir")


async def test_the_sync_touches_no_store_when_the_v1_dir_is_absent(tmp_path):
    ctx = SimpleNamespace(config={"working_dir": str(tmp_path / "lightrag-v1")}, stores=_NoStores())

    result = await v1_index_sync_body(ctx)

    assert result["synced"] is False
    assert result["tokens"].counted_by == "none"
    assert not (tmp_path / "lightrag-v1").exists()


class _FakeV1Index:
    """A v1 stand-in that keeps doc status, text chunks and the chunk vectors of every live
    document in its working dir, as v1 commits them."""

    def __init__(self) -> None:
        self.docs: list[str] = []

    def _write(self, working_dir: Path) -> None:
        working_dir.mkdir(parents=True, exist_ok=True)
        status = {d: {"status": "processed", "chunks_list": [f"{d}-c"], "track_id": f"t-{d}"} for d in self.docs}
        chunks = {f"{d}-c": {"content": f"text {d}", "full_doc_id": d} for d in self.docs}
        (working_dir / "kv_store_doc_status.json").write_text(json.dumps(status), encoding="utf-8")
        (working_dir / "kv_store_text_chunks.json").write_text(json.dumps(chunks), encoding="utf-8")
        _write_faiss(working_dir, "chunks", {cid: {"full_doc_id": rec["full_doc_id"]} for cid, rec in chunks.items()})

    def ingest(self, _op: str, payload: dict[str, Any], *, working_dir: Any = None, **_: Any) -> dict[str, Any]:
        self.docs += [doc["id"] for doc in payload["documents"]]
        self._write(Path(working_dir))
        return {"track_id": payload["track_id"], "enqueued": 1, "usage": None}

    def delete(self, _op: str, payload: dict[str, Any], *, working_dir: Any = None, **_: Any) -> dict[str, Any]:
        self.docs.remove(payload["doc_id"])
        self._write(Path(working_dir))
        return {"status": "success", "doc_id": payload["doc_id"], "message": ""}


async def test_a_vector_commit_failure_on_a_delete_is_pruned_by_the_next_sync(tmp_path, monkeypatch):
    """11 REVIEW A-WR-01: kv commits before vector, so a vector commit failure during a delete used
    to leave a manifest without the deleted ids, and their vector rows stayed for good."""
    fake = _FakeV1Index()
    monkeypatch.setattr(full_ingest_module, "run_corpus_op", fake.ingest)
    monkeypatch.setattr(full_delete_module, "run_corpus_op", fake.delete)
    monkeypatch.setattr(engine_module, "run_corpus_op", lambda *_a, **_k: {"counts": {}, "documents": [], "total": 0})
    engine = Databasise(store_root=tmp_path, workspace="heal")
    for doc_id in ("a", "b"):
        await engine.ingest(IngestDocument(document_id=doc_id, text=f"text {doc_id}"))

    real_commit = MultiNamespaceVectorStore.commit_prepared
    failures = [OSError("disk full")]

    async def _commit_once_fails(self):
        if failures:
            raise failures.pop()
        await real_commit(self)

    monkeypatch.setattr(MultiNamespaceVectorStore, "commit_prepared", _commit_once_fails)
    with pytest.raises(ForeignEngineRefusalError) as refused:
        await engine.delete_document("a")
    assert refused.value.failure_class == "StoreFault"

    assert await _kv_ids(tmp_path) == {"b-c"}  # kv committed the delete
    assert await _vector_ids_of(tmp_path) == {"a-c", "b-c"}  # vector did not

    await engine.ingest(IngestDocument(document_id="c", text="text c"))

    assert await _kv_ids(tmp_path) == {"b-c", "c-c"}
    assert await _vector_ids_of(tmp_path) == {"b-c", "c-c"}


async def _kv_ids(store_root: Path) -> set[str]:
    kv = SqliteKVStore(namespace="text_chunks", workspace="heal", store_root=store_root)
    try:
        return {cid for cid in ("a-c", "b-c", "c-c") if await kv.get_by_id(cid) is not None}
    finally:
        await kv.finalize()


async def _vector_ids_of(store_root: Path) -> set[str]:
    store = FaissVectorStore(namespace="chunks", workspace="heal", store_root=store_root)
    try:
        return {cid for cid in ("a-c", "b-c", "c-c") if store.get_by_id(cid) is not None}
    finally:
        await store.finalize()


async def test_a_corrupt_v1_index_refuses_the_ingest_and_commits_nothing(tmp_path, monkeypatch):
    def _fake_driver(op: str, payload: dict[str, Any], *, timeout: float, working_dir: Any = None, **_: Any):
        assert working_dir is not None, "full-ingest launched v1 without a per-workspace working_dir"
        Path(working_dir).mkdir(parents=True, exist_ok=True)
        (Path(working_dir) / "kv_store_doc_status.json").write_text("{torn", encoding="utf-8")
        return {"track_id": payload["track_id"], "enqueued": 1, "usage": None}

    monkeypatch.setattr(full_ingest_module, "run_corpus_op", _fake_driver)
    engine = Databasise(store_root=tmp_path, workspace="sync-corrupt")

    with pytest.raises(ForeignEngineRefusalError):
        await engine.ingest(IngestDocument(document_id="d1", text="UNIQcorrupt text"))

    kv = SqliteKVStore(namespace="text_chunks", workspace="sync-corrupt", store_root=tmp_path)
    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace="sync-corrupt", store_root=tmp_path)
    try:
        assert await kv.is_empty() is True
        assert await graph.get_all_labels() == []
    finally:
        await kv.finalize()
        await graph.finalize()
    assert list((tmp_path / "sync-corrupt").rglob("vector.faiss")) == []
