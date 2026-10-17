"""10-04-PLAN.md (STOR-06, D-06, D-09, D-13): an ingest whose run records any node failure, or
that stopped early, commits nothing. The engine drops every store's pending writes and raises
``ForeignEngineRefusalError``; a reopened store holds no record of the refused document.

Reuses ``test_hipporag_write_path.py``'s stub clients, workspace and HippoRAG selector.
"""

from __future__ import annotations

import pytest

from databasise.seam import QueryObject
from databasise.seam.corpus import IngestDocument
from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.seam.selectors import Selector
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore
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
