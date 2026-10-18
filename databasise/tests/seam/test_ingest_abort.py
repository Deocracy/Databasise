"""10-04-PLAN.md (STOR-06, D-06, D-09, D-13): an ingest whose run records any node failure, or
that stopped early, commits nothing. The engine drops every store's pending writes and raises
``ForeignEngineRefusalError``; a reopened store holds no record of the refused document.

Reuses ``test_hipporag_write_path.py``'s stub clients, workspace and HippoRAG selector.
"""

from __future__ import annotations

import asyncio
import sqlite3

import pytest

from databasise.runner import scheduler as _scheduler
from databasise.seam import QueryObject
from databasise.seam.corpus import IngestDocument
from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.seam.selectors import Selector
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore, MultiNamespaceVectorStore
from seam.test_hipporag_write_path import _DOCUMENT_TEXT, _HIPPORAG_CAPABILITY, _WORKSPACE, _make_engine

_VECTOR_NAMESPACES = ("hipporag-chunks", "hipporag-entities", "hipporag-facts")


def _selector() -> Selector:
    return Selector(capability=_HIPPORAG_CAPABILITY)


def _fail_upsert_edge(monkeypatch, exc: BaseException) -> None:
    async def _raise(self, *args, **kwargs):
        raise exc

    monkeypatch.setattr(CozoGraphStore, "upsert_edge", _raise)


async def _assert_nothing_committed(store_root) -> None:
    kv = SqliteKVStore("hipporag-text-chunks", _WORKSPACE, store_root)
    try:
        assert await kv.is_empty()
    finally:
        await kv.finalize()
    for namespace in _VECTOR_NAMESPACES:
        vector = FaissVectorStore(namespace, _WORKSPACE, store_root)
        try:
            assert list(vector.iter_vectors()) == [], namespace
        finally:
            await vector.finalize()
    graph = CozoGraphStore(namespace="hipporag-graph", workspace=_WORKSPACE, store_root=store_root)
    try:
        assert await graph.get_all_labels() == []
    finally:
        await graph.finalize()


async def _refused_ingest(store_root, monkeypatch, exc: BaseException) -> ForeignEngineRefusalError:
    _fail_upsert_edge(monkeypatch, exc)
    engine = _make_engine(store_root)
    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await engine.ingest(IngestDocument(document_id="abort-doc-1", text=_DOCUMENT_TEXT), selector=_selector())
    monkeypatch.undo()
    return exc_info.value


# --------------------------------------------------------------------------------------------- #
# Task 1: a failing later node commits nothing.
# --------------------------------------------------------------------------------------------- #


async def test_a_failing_graph_augment_persist_commits_no_kv_vector_or_graph_write(store_root, monkeypatch):
    await _refused_ingest(store_root, monkeypatch, RuntimeError("boom"))
    await _assert_nothing_committed(store_root)


async def test_a_query_after_a_refused_ingest_returns_no_evidence_from_it(store_root, monkeypatch):
    await _refused_ingest(store_root, monkeypatch, RuntimeError("boom"))

    envelope = await _make_engine(store_root).query(QueryObject(text="What did Ed Wood direct?"), _selector())

    assert envelope.evidence == []


async def test_a_successful_hipporag_ingest_still_commits(store_root):
    await _make_engine(store_root).ingest(
        IngestDocument(document_id="abort-doc-ok", text=_DOCUMENT_TEXT), selector=_selector()
    )

    kv = SqliteKVStore("hipporag-text-chunks", _WORKSPACE, store_root)
    try:
        assert not await kv.is_empty()
    finally:
        await kv.finalize()
    chunks = FaissVectorStore("hipporag-chunks", _WORKSPACE, store_root)
    try:
        assert list(chunks.iter_vectors())
    finally:
        await chunks.finalize()
    # Phase 10 review WR-10: the graph committed too, not only kv and the chunks vector.
    graph = CozoGraphStore(namespace="hipporag-graph", workspace=_WORKSPACE, store_root=store_root)
    try:
        assert await graph.get_all_labels()
    finally:
        await graph.finalize()


# --------------------------------------------------------------------------------------------- #
# Task 2: StoreFault and RunIncomplete (D-13, Q2), and any node's exception refuses (D-06).
# --------------------------------------------------------------------------------------------- #


async def test_a_store_error_inside_a_node_is_a_store_fault(store_root, monkeypatch):
    refusal = await _refused_ingest(store_root, monkeypatch, sqlite3.OperationalError("simulated store fault"))

    assert refusal.failure_class == "StoreFault"
    assert "v1" not in str(refusal)
    assert "foreign engine" not in str(refusal).lower()
    await _assert_nothing_committed(store_root)


async def test_a_non_store_exception_keeps_its_existing_class(store_root, monkeypatch):
    refusal = await _refused_ingest(store_root, monkeypatch, RuntimeError("boom"))

    assert refusal.failure_class == "UnclassifiedEngineFailure"


def _fake_run_wiring(scheduled_extra: dict, calls: list):
    async def _run_wiring(parsed, registry, stores, **kwargs):
        await stores["kv"].upsert({"leaked-chunk": {"content": "must not survive"}})
        calls.append("run_wiring")
        scheduled = {
            "results": {node_id: {"artifact": {}} for node_id in parsed.parts},
            "nodes": [],
            "partial": False,
            "stop_reason": None,
            "degraded": False,
            "degradation_reason": None,
            "node_exceptions": {},
        }
        scheduled.update(scheduled_extra)
        return scheduled

    return _run_wiring


async def test_an_exception_on_a_non_result_node_still_refuses_and_commits_nothing(store_root, monkeypatch):
    calls: list = []
    extra = {"node_exceptions": {"chunk-embed": RuntimeError("non-result node failed")}}
    monkeypatch.setattr(_scheduler, "run_wiring", _fake_run_wiring(extra, calls))

    with pytest.raises(ForeignEngineRefusalError):
        await _make_engine(store_root).ingest(
            IngestDocument(document_id="abort-doc-2", text=_DOCUMENT_TEXT), selector=_selector()
        )

    assert calls == ["run_wiring"]
    await _assert_nothing_committed(store_root)


async def test_an_early_stop_with_no_exception_is_run_incomplete_and_drops_every_store(store_root, monkeypatch):
    calls: list = []
    extra = {"partial": True, "stop_reason": "budget_halt", "degraded": True, "degradation_reason": "budget_halt"}
    monkeypatch.setattr(_scheduler, "run_wiring", _fake_run_wiring(extra, calls))
    lifecycle: list[tuple[str, str]] = []
    for store_cls in (SqliteKVStore, MultiNamespaceVectorStore, CozoGraphStore):
        for method in ("drop_pending_index_ops", "index_done_callback"):
            original = getattr(store_cls, method)

            async def _spy(self, _original=original, _method=method):
                lifecycle.append((type(self).__name__, _method))
                return await _original(self)

            monkeypatch.setattr(store_cls, method, _spy)

    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await _make_engine(store_root).ingest(
            IngestDocument(document_id="abort-doc-3", text=_DOCUMENT_TEXT), selector=_selector()
        )
    monkeypatch.undo()

    assert exc_info.value.failure_class == "RunIncomplete"
    assert sorted(lifecycle) == [
        ("CozoGraphStore", "drop_pending_index_ops"),
        ("MultiNamespaceVectorStore", "drop_pending_index_ops"),
        ("SqliteKVStore", "drop_pending_index_ops"),
    ]
    await _assert_nothing_committed(store_root)


# --------------------------------------------------------------------------------------------- #
# 10-05 (D-07): a successful run commits through prepare-all, then commit-all.
# --------------------------------------------------------------------------------------------- #

_STORE_CLASSES = (SqliteKVStore, MultiNamespaceVectorStore, CozoGraphStore)


async def test_every_store_prepares_before_any_store_commits(store_root, monkeypatch):
    calls: list[tuple[str, str]] = []
    for store_cls in _STORE_CLASSES:
        for method in ("prepare", "commit_prepared"):
            original = getattr(store_cls, method)

            async def _spy(self, _original=original, _method=method):
                calls.append((type(self).__name__, _method))
                return await _original(self)

            monkeypatch.setattr(store_cls, method, _spy)

    await _make_engine(store_root).ingest(
        IngestDocument(document_id="prepared-doc-1", text=_DOCUMENT_TEXT), selector=_selector()
    )
    monkeypatch.undo()

    assert [method for _, method in calls] == ["prepare"] * 3 + ["commit_prepared"] * 3
    assert {name for name, _ in calls[:3]} == {cls.__name__ for cls in _STORE_CLASSES}


async def test_a_graph_prepare_failure_aborts_every_store_and_is_a_store_fault(store_root, monkeypatch):
    async def _raise(self):
        raise sqlite3.OperationalError("prepare failed")

    monkeypatch.setattr(CozoGraphStore, "prepare", _raise)
    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await _make_engine(store_root).ingest(
            IngestDocument(document_id="prepared-doc-2", text=_DOCUMENT_TEXT), selector=_selector()
        )
    monkeypatch.undo()

    assert exc_info.value.failure_class == "StoreFault"
    await _assert_nothing_committed(store_root)
    assert not list((store_root / _WORKSPACE).rglob("*.tmp"))


_SECOND_DOCUMENT_TEXT = "Ed Wood also wrote many pulp novels."


async def _committed_chunks(store_root) -> tuple[set[str], set[str]]:
    vector = FaissVectorStore("hipporag-chunks", _WORKSPACE, store_root)
    vector_ids = {doc_id for doc_id, _ in vector.iter_vectors()}
    await vector.finalize()
    kv = SqliteKVStore("hipporag-text-chunks", _WORKSPACE, store_root)
    try:
        kv_ids = {row[0] for row in kv._conn.execute("SELECT id FROM kv")}
    finally:
        await kv.finalize()
    return vector_ids, kv_ids


async def test_two_concurrent_hipporag_ingests_on_one_root_both_commit_in_full(store_root, tmp_path):
    documents = [
        IngestDocument(document_id="concurrent-doc-1", text=_DOCUMENT_TEXT),
        IngestDocument(document_id="concurrent-doc-2", text=_SECOND_DOCUMENT_TEXT),
    ]
    sequential_root = tmp_path / "sequential"
    sequential_root.mkdir()
    for document in documents:
        await _make_engine(sequential_root).ingest(document, selector=_selector())
    expected_vectors, expected_kv = await _committed_chunks(sequential_root)
    assert len(expected_vectors) >= 2

    engine = _make_engine(store_root)
    await asyncio.gather(*(engine.ingest(document, selector=_selector()) for document in documents))

    assert await _committed_chunks(store_root) == (expected_vectors, expected_kv)


@pytest.mark.parametrize("failure_class", ["StoreFault", "RunIncomplete"])
def test_store_fault_and_run_incomplete_answer_502(failure_class):
    pytest.importorskip("fastapi")
    from databasise.seam.rest import _status_for

    refusal = ForeignEngineRefusalError(operation="ingest", cause=RuntimeError("x"), failure_class=failure_class)

    assert _status_for(refusal) == 502
