"""Phase 10 review CR-01 (D-13 on the query path): a store error inside a query node is a named
``ForeignEngineRefusalError``, never a 200 envelope carrying a path, a checksum or a node id; any other
node exception still degrades, with the closed ``node_failed`` code as ``stop_reason`` (the exception class
name stays in the debug trace only)."""

from __future__ import annotations

import sqlite3

import pytest

from databasise.seam import QueryObject
from databasise.seam.corpus import IngestDocument
from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.seam.selectors import Selector
from databasise.stores.vector import FaissVectorStore
from seam.test_hipporag_write_path import _DOCUMENT_TEXT, _HIPPORAG_CAPABILITY, _WORKSPACE, _make_engine

_QUERY = QueryObject(text="What did Ed Wood direct?")


def _selector() -> Selector:
    return Selector(capability=_HIPPORAG_CAPABILITY)


async def _ingested_engine(store_root):
    engine = _make_engine(store_root)
    await engine.ingest(IngestDocument(document_id="q-fault-doc", text=_DOCUMENT_TEXT), selector=_selector())
    return engine


async def test_a_corrupted_vector_index_under_a_query_node_is_a_store_corrupted_fault(store_root):
    engine = await _ingested_engine(store_root)
    index = store_root / _WORKSPACE / "hipporag-chunks" / "vector.faiss"
    index.write_bytes(index.read_bytes() + b"damage")

    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await engine.query(_QUERY, _selector())

    assert exc_info.value.failure_class == "StoreCorrupted"
    assert str(store_root) not in str(exc_info.value)


async def test_another_store_error_under_a_query_node_is_a_store_fault(store_root, monkeypatch):
    engine = await _ingested_engine(store_root)

    async def _raise(self, *args, **kwargs):
        raise sqlite3.OperationalError(f"disk I/O error at {store_root}")

    monkeypatch.setattr(FaissVectorStore, "score_all", _raise)

    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await engine.query(_QUERY, _selector())

    assert exc_info.value.failure_class == "StoreFault"


async def test_a_non_store_node_failure_degrades_with_the_closed_node_failed_code(store_root, monkeypatch):
    engine = await _ingested_engine(store_root)
    secret = f"{store_root}/secret-checksum-5ab2"

    async def _raise(self, *args, **kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(FaissVectorStore, "score_all", _raise)

    envelope = await engine.query(_QUERY, _selector())

    assert envelope.partial is True
    for text in (envelope.stop_reason, envelope.degradation_reason):
        assert text == "node_failed"  # D-05: a closed code, no exception class and no detail
        assert "RuntimeError" not in text
        assert str(store_root) not in text and "secret-checksum" not in text
    trace = await engine.resolve_trace(envelope.trace_token, debug=False)
    assert str(store_root) not in repr(trace)
    debug_trace = await engine.resolve_trace(envelope.trace_token, debug=True)
    failed = [n for n in debug_trace["nodes"] if n.get("status") == "failed"]
    assert failed and "RuntimeError" in failed[0]["cross_process_failure_cause"]
