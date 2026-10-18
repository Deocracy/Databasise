"""11-06 Task 2 (D-02, M-12, LRAG-01): ``GET /jobs/{job_id}`` dispatches on the modality family
that minted the job. A committed HippoRAG ingest is answered from the machine's own record
(``<store_root>/jobs.db``) and never asks v1; a LightRAG job, and any id no record knows, still goes
to v1 exactly as before. Reads never create ``jobs.db`` (LRAG-13)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

import databasise.seam.engine as engine_module
from databasise.parts_core.lightrag import full_ingest
from databasise.seam.corpus import IngestDocument
from databasise.seam.refusals import ForeignEngineRefusalError, UnknownJobError
from databasise.seam.rest import create_app
from databasise.seam.selectors import Selector
from databasise.stores.graph import CozoGraphStore
from databasise.tests.fixtures.v1_corpus_driver_stub import _run_health, _run_status
from seam.test_hipporag_write_path import (
    _DOCUMENT_TEXT,
    _HIPPORAG_CAPABILITY,
    _StubEmbeddingClient,
    _StubIngestQueryLLMClient,
    _make_engine,
)


class _RecordingV1:
    """Serves ``status``/``health`` through the stub driver over ``documents`` and records calls."""

    def __init__(self, documents: list[dict] = ()):
        self.documents = list(documents)
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, op, payload, **_kwargs):
        self.calls.append((op, payload))
        job = {**payload, "_stub_documents": self.documents, "_stub_counts": {}}
        return _run_status(job) if op == "status" else _run_health(job)


@pytest.fixture
def v1(monkeypatch) -> _RecordingV1:
    fake = _RecordingV1()
    monkeypatch.setattr(engine_module, "run_corpus_op", fake)
    return fake


def _hipporag() -> Selector:
    return Selector(capability=_HIPPORAG_CAPABILITY)


def test_a_committed_hipporag_job_is_processed_without_asking_v1(store_root, v1):
    client = TestClient(
        create_app(
            store_root=store_root,
            workspace="ws",
            clients={"embedding": _StubEmbeddingClient(), "llm": _StubIngestQueryLLMClient()},
        )
    )
    posted = client.post(
        "/documents",
        json={"document": {"document_id": "h1", "text": _DOCUMENT_TEXT}, "selector": {"capability": _HIPPORAG_CAPABILITY}},
    )
    assert posted.status_code == 200, posted.text

    response = client.get(f"/jobs/{posted.json()['job_id']}")

    assert response.status_code == 200, response.text
    body = response.json()
    assert [(d["document_id"], d["status"]) for d in body["documents"]] == [("h1", "processed")]
    assert body["counts"] == {"processed": 1}
    assert body["next_offset"] is None
    assert v1.calls == []


async def test_a_lightrag_job_is_still_answered_by_v1(store_root, v1, monkeypatch):
    monkeypatch.setattr(
        full_ingest, "run_corpus_op", lambda _op, payload, **_k: {"track_id": payload["track_id"], "enqueued": 1}
    )
    engine = _make_engine(store_root, workspace="ws")
    job = await engine.ingest(IngestDocument(document_id="l1", text="t"))
    v1.documents = [
        {"document_id": "l1", "_track_id": job.job_id, "status": "processed", "updated_at": "2026-01-01T00:00:00Z"}
    ]

    status = await engine.get_job_status(job.job_id)

    assert [(d.document_id, d.status) for d in status.documents] == [("l1", "processed")]
    assert [(op, payload["track_id"]) for op, payload in v1.calls] == [("status", job.job_id)]


def test_an_id_no_record_and_no_v1_row_knows_is_a_404(store_root, v1):
    response = TestClient(create_app(store_root=store_root, workspace="ws")).get("/jobs/unknown")

    assert response.status_code == 404
    assert response.json()["refusal_type"] == "UnknownJobError"
    assert [op for op, _ in v1.calls] == ["status"]


async def test_reads_never_create_jobs_db_and_the_first_ingest_does(store_root, v1):
    engine = _make_engine(store_root, workspace="ws")
    jobs_db = store_root / "jobs.db"
    assert not jobs_db.exists()

    await engine.health()
    await engine.corpus_status()
    with pytest.raises(UnknownJobError):
        await engine.get_job_status("nothing")
    assert not jobs_db.exists()

    await engine.ingest(IngestDocument(document_id="h1", text=_DOCUMENT_TEXT), selector=_hipporag())
    assert jobs_db.exists()


async def test_a_refused_hipporag_ingest_records_nothing(store_root, v1, monkeypatch):
    fixed = uuid.UUID(int=7)
    monkeypatch.setattr(engine_module.uuid, "uuid4", lambda: fixed)

    async def _raise(self, *args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(CozoGraphStore, "upsert_edge", _raise)
    engine = _make_engine(store_root, workspace="ws")
    with pytest.raises(ForeignEngineRefusalError):
        await engine.ingest(IngestDocument(document_id="h1", text=_DOCUMENT_TEXT), selector=_hipporag())

    assert not (store_root / "jobs.db").exists()
    with pytest.raises(UnknownJobError):
        await engine.get_job_status(fixed.hex)
    assert [(op, payload["track_id"]) for op, payload in v1.calls] == [("status", fixed.hex)]
