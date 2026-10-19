"""11-06 Task 1 (LRAG-04, D-07): a LightRAG write to a v1 working dir that another write holds is
refused with ``StoreBusyError(store_kind="corpus")`` (409), never run beside it.

v1 is faked at ``run_corpus_op`` (the real full-ingest, full-delete and v1-index-sync bodies run).
The fake sleeps inside its thread and writes a minimal v1 index (doc status plus text chunks), so
the sync really reads, mirrors and writes its prune manifest. The gate covers the whole write: the
v1 call, the sync's manifest read, the staging and the commit.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import json
import logging
import threading
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import databasise.seam.engine as engine_module
from databasise.foreign.v1_corpus_adapter import CorpusOpSubprocessError
from databasise.parts_core.lightrag import full_delete, full_ingest, v1_index_sync
from databasise.parts_core.lightrag.v1_index_sync import V1_INDEX_SYNC_MANIFEST_KEY
from databasise.seam.corpus import DeletionOutcome, IngestDocument, IngestJob
from databasise.seam.engine import Databasise
from databasise.seam.refusals import ForeignEngineRefusalError, StoreBusyError
from databasise.seam.rest import create_app
from databasise.seam.selectors import Selector
from databasise.stores.kv import SqliteKVStore
from seam.test_hipporag_write_path import (
    _DOCUMENT_TEXT,
    _HIPPORAG_CAPABILITY,
    _StubEmbeddingClient,
    _StubIngestQueryLLMClient,
)


class _FakeV1:
    """A v1 stand-in: sleeps ``delay`` in the worker thread, then records the document as
    processed with one text chunk in the working dir, as v1 commits it."""

    def __init__(self, delay: float = 1.0, fail: bool = False):
        self.delay = delay
        self.fail = fail
        self.intervals: list[tuple[float, float]] = []
        self.events: list[str] = []
        self._lock = threading.Lock()

    def ingest(self, _op, payload, *, working_dir=None, **_kwargs):
        start = time.monotonic()
        self.events.append("driver-start")
        time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("v1 exploded")
        working_dir = Path(working_dir)
        with self._lock:
            working_dir.mkdir(parents=True, exist_ok=True)
            status_path = working_dir / "kv_store_doc_status.json"
            chunks_path = working_dir / "kv_store_text_chunks.json"
            status = json.loads(status_path.read_text()) if status_path.exists() else {}
            chunks = json.loads(chunks_path.read_text()) if chunks_path.exists() else {}
            for doc in payload["documents"]:
                chunk_id = f"{doc['id']}-chunk-000"
                status[doc["id"]] = {"status": "processed", "chunks_list": [chunk_id], "track_id": payload["track_id"]}
                chunks[chunk_id] = {"content": doc["text"], "full_doc_id": doc["id"]}
            status_path.write_text(json.dumps(status))
            chunks_path.write_text(json.dumps(chunks))
        self.events.append("driver-end")
        self.intervals.append((start, time.monotonic()))
        return {"track_id": payload["track_id"], "enqueued": 1, "usage": None}

    def delete(self, _op, payload, **_kwargs):
        start = time.monotonic()
        self.events.append("driver-start")
        time.sleep(self.delay)
        self.events.append("driver-end")
        self.intervals.append((start, time.monotonic()))
        return {"status": "success", "doc_id": payload.get("doc_id"), "message": ""}


@pytest.fixture
def fake_v1(monkeypatch) -> _FakeV1:
    fake = _FakeV1()
    monkeypatch.setattr(full_ingest, "run_corpus_op", fake.ingest)
    monkeypatch.setattr(full_delete, "run_corpus_op", fake.delete)
    return fake


def _doc(document_id: str) -> IngestDocument:
    return IngestDocument(document_id=document_id, text=f"{document_id} text")


def _one_job_one_busy(results: list) -> StoreBusyError:
    jobs = [r for r in results if isinstance(r, (IngestJob, DeletionOutcome))]
    busy = [r for r in results if isinstance(r, StoreBusyError)]
    assert len(jobs) == 1 and len(busy) == 1, results
    assert busy[0].store_kind == "corpus"
    return busy[0]


async def test_a_second_ingest_on_a_busy_working_dir_is_refused(store_root, fake_v1):
    engine = Databasise(store_root=store_root, workspace="ws")

    results = await asyncio.gather(engine.ingest(_doc("a")), engine.ingest(_doc("b")), return_exceptions=True)

    _one_job_one_busy(results)
    assert len(fake_v1.intervals) == 1


async def test_a_delete_beside_an_ingest_is_refused(store_root, fake_v1):
    engine = Databasise(store_root=store_root, workspace="ws")

    results = await asyncio.gather(engine.ingest(_doc("a")), engine.delete_document("a"), return_exceptions=True)

    _one_job_one_busy(results)
    assert len(fake_v1.intervals) == 1


async def _until(predicate, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, "the first write never reached the awaited phase"
        await asyncio.sleep(0.01)


@pytest.mark.parametrize("phase", ["driver-start", "sync-start", "commit-start"])
async def test_a_write_arriving_in_any_phase_of_another_never_interleaves_the_manifest(
    store_root, fake_v1, monkeypatch, phase
):
    """Orchestrator requirement (11-01 security review): the gate covers the v1 call, the sync's
    manifest read and the commit, so two writes can never read one manifest and both write it."""
    events = fake_v1.events
    real_read = v1_index_sync.read_v1_snapshot
    real_commit = engine_module._commit_all

    def _slow_read(working_dir, **kwargs):
        events.append("sync-start")
        time.sleep(0.5)
        snapshot = real_read(working_dir, **kwargs)
        events.append("sync-end")
        return snapshot

    async def _slow_commit(stores, operation, store_root):
        events.append("commit-start")
        await asyncio.sleep(0.5)
        await real_commit(stores, operation, store_root)
        events.append("commit-end")

    monkeypatch.setattr(v1_index_sync, "read_v1_snapshot", _slow_read)
    monkeypatch.setattr(engine_module, "_commit_all", _slow_commit)
    engine = Databasise(store_root=store_root, workspace="ws")

    first = asyncio.create_task(engine.ingest(_doc("a")))
    await _until(lambda: phase in events)
    with pytest.raises(StoreBusyError) as refused:
        await engine.ingest(_doc("b"))
    assert refused.value.store_kind == "corpus"
    assert isinstance(await first, IngestJob)
    assert events == ["driver-start", "driver-end", "sync-start", "sync-end", "commit-start", "commit-end"]

    # The refused write left nothing behind, and the next write mirrors and prunes from a manifest
    # that names exactly what the v2 store holds.
    assert isinstance(await engine.ingest(_doc("b")), IngestJob)
    kv = SqliteKVStore(namespace="text_chunks", workspace="ws", store_root=store_root)
    try:
        manifest = await kv.get_by_id(V1_INDEX_SYNC_MANIFEST_KEY)
        assert manifest["text_chunks"] == ["a-chunk-000", "b-chunk-000"]
        assert [r["full_doc_id"] for r in await kv.get_by_ids(manifest["text_chunks"])] == ["a", "b"]
    finally:
        await kv.finalize()


def test_the_second_rest_post_is_a_409_naming_no_path(store_root, fake_v1):
    client = TestClient(create_app(store_root=store_root, workspace="ws"))
    responses: dict[str, object] = {}

    def _post(name: str) -> None:
        responses[name] = client.post("/documents", json={"document": {"document_id": name, "text": "t"}})

    first = threading.Thread(target=_post, args=("a",))
    first.start()
    deadline = time.monotonic() + 10
    while "driver-start" not in fake_v1.events:
        assert time.monotonic() < deadline
        time.sleep(0.01)
    _post("b")
    first.join()

    assert responses["a"].status_code == 200
    busy = responses["b"]
    assert busy.status_code == 409
    body = busy.json()
    assert (body["refusal_type"], body["store_kind"]) == ("StoreBusyError", "corpus")
    assert str(store_root) not in busy.text and "lightrag-v1" not in busy.text


async def test_two_workspaces_of_one_store_root_write_side_by_side(store_root, fake_v1):
    one = Databasise(store_root=store_root, workspace="w1")
    two = Databasise(store_root=store_root, workspace="w2")

    results = await asyncio.gather(one.ingest(_doc("a")), two.ingest(_doc("a")), return_exceptions=True)

    assert all(isinstance(r, IngestJob) for r in results), results
    (s1, e1), (s2, e2) = fake_v1.intervals
    assert max(s1, s2) < min(e1, e2)  # they really overlapped


async def test_a_hipporag_ingest_beside_a_lightrag_ingest_is_not_gated(store_root, fake_v1):
    engine = Databasise(
        store_root=store_root,
        workspace="ws",
        clients={"embedding": _StubEmbeddingClient(), "llm": _StubIngestQueryLLMClient()},
    )
    hipporag = Selector(capability=_HIPPORAG_CAPABILITY)

    results = await asyncio.gather(
        engine.ingest(_doc("a")),
        engine.ingest(IngestDocument(document_id="h", text=_DOCUMENT_TEXT), selector=hipporag),
        return_exceptions=True,
    )

    assert all(isinstance(r, IngestJob) for r in results), results


@pytest.mark.parametrize(
    ("operation", "phase", "end"),
    [("ingest", "driver-start", "driver-end"), ("ingest", "sync-start", "sync-end"), ("delete", "driver-start", "driver-end")],
)
async def test_a_cancelled_write_holds_the_gate_until_the_v1_thread_returns(
    store_root, fake_v1, monkeypatch, operation, phase, end
):
    """11 REVIEW A-CR-01: a thread cannot be cancelled, so a cancelled write must keep the gate
    until v1 (or the sync's read of v1's files) has returned, and a second write meanwhile is 409."""
    events = fake_v1.events
    real_read = v1_index_sync.read_v1_snapshot

    def _slow_read(working_dir, **kwargs):
        events.append("sync-start")
        time.sleep(1.0)
        events.append("sync-end")
        return real_read(working_dir, **kwargs)

    monkeypatch.setattr(v1_index_sync, "read_v1_snapshot", _slow_read)
    engine = Databasise(store_root=store_root, workspace="ws")
    first = asyncio.create_task(engine.ingest(_doc("a")) if operation == "ingest" else engine.delete_document("a"))
    await _until(lambda: phase in events)

    first.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first  # A2-WR-01: the cancel gives up the wait at once
    assert end not in events, "the fake v1 thread returned before the check; raise its delay"
    assert engine._write_gate_held()
    with pytest.raises(StoreBusyError) as refused:
        await engine.ingest(_doc("b"))
    assert refused.value.store_kind == "corpus"

    await _until(lambda: end in events)
    await _until(lambda: not engine._write_gate_held())
    assert len(fake_v1.intervals) == 1  # the refused write never reached v1


async def test_a_sync_over_its_ceiling_raises_the_timeout_fault_and_holds_the_gate_until_the_read_returns(
    store_root, fake_v1, monkeypatch
):
    """11 REVIEW A2-WR-01: the sync's 300 s ceiling (condition 4) is enforced again. The timeout
    gives up the wait; the gate stays held until the worker thread returns, so a write meanwhile
    is a 409."""
    events = fake_v1.events
    fake_v1.delay = 0.0
    real_read = v1_index_sync.read_v1_snapshot

    def _slow_read(working_dir, **kwargs):
        events.append("sync-start")
        time.sleep(2.0)
        events.append("sync-end")
        return real_read(working_dir, **kwargs)

    monkeypatch.setattr(v1_index_sync, "read_v1_snapshot", _slow_read)
    monkeypatch.setattr(v1_index_sync, "V1_INDEX_SYNC_WALL_CLOCK_CEILING_SECONDS", 0.3)
    engine = Databasise(store_root=store_root, workspace="ws")

    started = time.monotonic()
    with pytest.raises(ForeignEngineRefusalError) as fault:
        await engine.ingest(_doc("a"))
    assert time.monotonic() - started < 1.5  # within the ceiling, well before the 2 s read returns
    assert fault.value.failure_class == "CorpusOpTimeoutError"

    assert "sync-end" not in events
    assert engine._write_gate_held()
    with pytest.raises(StoreBusyError) as refused:
        await engine.ingest(_doc("b"))
    assert refused.value.store_kind == "corpus"

    await _until(lambda: "sync-end" in events)
    await _until(lambda: not engine._write_gate_held())
    assert len(fake_v1.intervals) == 1  # the refused write never reached v1


async def test_a_reingest_after_a_sync_timeout_mirrors_the_document_v1_committed(store_root, fake_v1, monkeypatch):
    """11 REVIEW A3-WR-01: v1 committed but the sync timed out, so v2 lacks the document. The
    re-ingest of that id does not call v1 again (A-CR-02), yet it runs the sync, so the document
    becomes resolvable in v2. It still answers ``enqueued: 0`` with the original track id."""
    fake_v1.delay = 0.0
    real_read = v1_index_sync.read_v1_snapshot
    reads: list[int] = []

    def _first_read_slow(working_dir, **kwargs):
        reads.append(1)
        if len(reads) == 1:
            time.sleep(1.0)
        return real_read(working_dir, **kwargs)

    def _status(_op, payload, *, working_dir, **_kwargs):
        rows = json.loads((Path(working_dir) / "kv_store_doc_status.json").read_text())
        held = [{"document_id": d, "status": r["status"]} for d, r in rows.items() if d == payload["document_id"]]
        return {"counts": {}, "documents": held, "total": len(held)}

    monkeypatch.setattr(v1_index_sync, "read_v1_snapshot", _first_read_slow)
    monkeypatch.setattr(v1_index_sync, "V1_INDEX_SYNC_WALL_CLOCK_CEILING_SECONDS", 0.3)
    monkeypatch.setattr(engine_module, "run_corpus_op", _status)
    engine = Databasise(store_root=store_root, workspace="ws")

    with pytest.raises(ForeignEngineRefusalError) as fault:
        await engine.ingest(_doc("a"))
    assert fault.value.failure_class == "CorpusOpTimeoutError"
    await _until(lambda: not engine._write_gate_held())
    status = json.loads((store_root / "ws" / "lightrag-v1" / "kv_store_doc_status.json").read_text())
    original_track = status["a"]["track_id"]

    job = await engine.ingest(_doc("a"))

    assert (job.job_id, job.enqueued) == (original_track, 0)
    assert len(fake_v1.intervals) == 1  # v1 was not called again
    assert not engine._write_gate_held()
    kv = SqliteKVStore(namespace="text_chunks", workspace="ws", store_root=store_root)
    try:
        assert (await kv.get_by_id("a-chunk-000"))["full_doc_id"] == "a"
        assert (await kv.get_by_id(V1_INDEX_SYNC_MANIFEST_KEY))["text_chunks"] == ["a-chunk-000"]
    finally:
        await kv.finalize()


async def test_a_cancelled_write_logs_the_discarded_v1_failure_once_redacted(store_root, monkeypatch, caplog):
    """11 REVIEW A2-WR-02: the outcome of a v1 worker whose wait was given up reaches no caller, so
    it is logged once, server-side, with the failure class and the redacted stderr tail."""
    started = threading.Event()

    def _failing_v1(_op, _payload, **_kwargs):
        started.set()
        time.sleep(0.5)
        raise CorpusOpSubprocessError(1, "Traceback ...\nAuthenticationError: bad key sk-live1234secret")

    monkeypatch.setattr(full_ingest, "run_corpus_op", _failing_v1)
    engine = Databasise(store_root=store_root, workspace="ws")
    first = asyncio.create_task(engine.ingest(_doc("a")))
    await _until(started.is_set)

    with caplog.at_level(logging.WARNING):
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        await _until(lambda: not engine._write_gate_held())

    discarded = [r.getMessage() for r in caplog.records if "discarded the worker's failure" in r.getMessage()]
    assert len(discarded) == 1, discarded
    assert "failure_class=CorpusOpSubprocessError" in discarded[0]
    assert "AuthenticationError" in discarded[0] and "sk-[REDACTED]" in discarded[0]
    assert "sk-live1234secret" not in caplog.text


class _ResetFailsOnce:
    """An ``ABANDONED_WORKERS`` stand-in whose first ``reset`` raises: the gate's earlier cleanup
    failing before the release."""

    def __init__(self):
        self.parked: list | None = None
        self.failed = False

    def set(self, parked):
        self.parked = parked
        return object()

    def reset(self, _token):
        if not self.failed:
            self.failed = True
            raise RuntimeError("cleanup failed")


async def test_a_failing_gate_cleanup_still_releases_the_gate(store_root, fake_v1, monkeypatch):
    """11 REVIEW A3-WR-02: an exception in the gate's earlier cleanup cannot skip the release."""
    fake_v1.delay = 0.0
    monkeypatch.setattr(engine_module, "ABANDONED_WORKERS", _ResetFailsOnce())
    engine = Databasise(store_root=store_root, workspace="ws")

    with pytest.raises(RuntimeError, match="cleanup failed"):
        await engine.ingest(_doc("a"))

    assert not engine._write_gate_held()
    assert isinstance(await engine.ingest(_doc("b")), IngestJob)


def test_a_failing_gate_cleanup_still_defers_the_release_to_a_parked_worker(tmp_path, monkeypatch):
    """A3-WR-02, deferred path: with a parked worker the gate is released once it returns."""
    var = _ResetFailsOnce()
    monkeypatch.setattr(engine_module, "ABANDONED_WORKERS", var)
    worker: concurrent.futures.Future = concurrent.futures.Future()

    with pytest.raises(RuntimeError, match="cleanup failed"), engine_module._write_gate(tmp_path):
        var.parked.append(worker)

    gate = engine_module._gate_for(tmp_path)
    assert gate.locked()
    worker.set_result(None)
    deadline = time.monotonic() + 5
    while gate.locked():
        assert time.monotonic() < deadline, "the gate was never released"
        time.sleep(0.01)
    with engine_module._write_gate(tmp_path):
        pass


async def test_a_failed_write_releases_the_gate(store_root, fake_v1):
    engine = Databasise(store_root=store_root, workspace="ws")
    fake_v1.fail = True
    with pytest.raises(ForeignEngineRefusalError):
        await engine.ingest(_doc("a"))
    assert not engine._write_gate_held()

    fake_v1.fail = False
    assert isinstance(await engine.ingest(_doc("a")), IngestJob)
    assert not engine._write_gate_held()
