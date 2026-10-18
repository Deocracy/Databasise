"""LRAG-07 (11-08-PLAN.md Task 1, D-08): a timed-out ingest leaves its document visibly
``interrupted``, the next unrelated ingest does not reprocess it, and ``POST
/documents/{document_id}/retry`` brings it to ``processed`` and queryable.

The real-driver cases run the real v1 driver against the loopback stub model server
(``tests/fixtures/v1_stub_server``) and skip only when ``v1/.venv/bin/python`` is absent. The
gate-held cases fake ``run_corpus_op``: while a write holds the D-07 gate, v1's own mid-pipeline
status is reported unchanged.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

import databasise.seam.engine as engine_module
from databasise.clients.builder import build_clients
from databasise.parts_core.lightrag import full_ingest
from databasise.seam.engine import Databasise
from databasise.seam.refusals import StoreBusyError
from databasise.seam.rest import create_app
from databasise.tests.fixtures.v1_stub_server import real_v1, requires_v1  # noqa: F401 - fixture

_WS = "interrupted"


def _statuses(client: TestClient) -> dict[str, str]:
    response = client.get("/corpus")
    assert response.status_code == 200, response.text
    return {doc["document_id"]: doc["status"] for doc in response.json()["documents"]}


@requires_v1
def test_a_timed_out_ingest_is_interrupted_left_alone_and_recovered_by_retry(real_v1, monkeypatch):  # noqa: F811
    monkeypatch.setattr(full_ingest, "INGEST_WALL_CLOCK_CEILING_SECONDS", 10.0)
    real_v1.server.delay_for["UNIQslow"] = 30.0
    client = TestClient(
        create_app(store_root=real_v1.store_root, workspace=_WS, clients=build_clients(real_v1.client_env))
    )

    slow = client.post("/documents", json={"document": {"document_id": "slow1", "text": "UNIQslow Corp hauls freight."}})
    assert slow.status_code == 503, slow.text
    assert slow.json()["failure_class"] == "CorpusOpTimeoutError"
    assert any("UNIQslow" in call for call in real_v1.server.chat_calls), "the slow call never started"

    assert _statuses(client) == {"slow1": "interrupted"}
    counts = client.get("/corpus/counts").json()
    assert counts["by_status"]["interrupted"] == 1
    assert counts["total"] == sum(counts["by_status"].values())

    real_v1.server.delay_for.clear()
    slow_calls_before = sum("UNIQslow" in call for call in real_v1.server.chat_calls)
    fast = client.post("/documents", json={"document": {"document_id": "fast1", "text": "UNIQfast Corp bakes bread."}})
    assert fast.status_code == 200, fast.text
    rows = client.get(f"/jobs/{fast.json()['job_id']}").json()["documents"]
    assert [row["document_id"] for row in rows] == ["fast1"]
    assert sum("UNIQslow" in call for call in real_v1.server.chat_calls) == slow_calls_before, (
        "an unrelated ingest reprocessed the interrupted document"
    )
    assert _statuses(client)["slow1"] == "interrupted"

    doc_status = real_v1.store_root / _WS / "lightrag-v1" / "kv_store_doc_status.json"
    original_track_id = json.loads(doc_status.read_text(encoding="utf-8"))["slow1"]["track_id"]
    retried = client.post("/documents/slow1/retry")
    assert retried.status_code == 200, retried.text
    assert retried.json()["enqueued"] == 1
    assert retried.json()["job_id"] == original_track_id
    assert _statuses(client) == {"slow1": "processed", "fast1": "processed"}

    evidence = client.post("/query", json={"query": {"text": "UNIQslow freight"}}).json()["evidence"]
    contents = [client.post("/evidence/resolve", json=ref).json().get("content", "") for ref in evidence]
    assert any("UNIQslow" in content for content in contents), "the retried document is not queryable"

    not_interrupted = client.post("/documents/fast1/retry")
    assert not_interrupted.status_code == 422
    body = not_interrupted.json()
    assert (body["refusal_type"], body["document_id"], body["status"]) == (
        "DocumentNotInterruptedError",
        "fast1",
        "processed",
    )
    unknown = client.post("/documents/nosuch/retry")
    assert (unknown.status_code, unknown.json()["refusal_type"]) == (422, "UnknownDocumentError")


_ROWS = [
    {"document_id": "a", "status": "processing", "updated_at": "t", "error_message": None},
    {"document_id": "b", "status": "pending", "updated_at": "t", "error_message": None},
    {"document_id": "c", "status": "parsing", "updated_at": "t", "error_message": None},
    {"document_id": "d", "status": "analyzing", "updated_at": "t", "error_message": None},
    {"document_id": "e", "status": "processed", "updated_at": "t", "error_message": None},
]
_COUNTS = {"processing": 1, "pending": 1, "parsing": 1, "analyzing": 1, "processed": 1}


@pytest.fixture
def fake_status(monkeypatch) -> list[dict[str, Any]]:
    sent: list[dict[str, Any]] = []

    def fake(op, payload, **_kwargs):
        assert op == "status"
        sent.append(payload)
        rows = [row for row in _ROWS if payload.get("document_id") in (None, row["document_id"])]
        return {"counts": dict(_COUNTS), "documents": rows, "total": len(rows)}

    monkeypatch.setattr(engine_module, "run_corpus_op", fake)
    return sent


async def test_with_no_write_in_flight_mid_pipeline_rows_are_interrupted_and_pending_is_not(store_root, fake_status):
    engine = Databasise(store_root=store_root, workspace=_WS)

    status = await engine.corpus_status()
    counts = await engine.document_counts()

    assert {doc.document_id: doc.status for doc in status.documents} == {
        "a": "interrupted",
        "b": "pending",
        "c": "interrupted",
        "d": "interrupted",
        "e": "processed",
    }
    assert status.counts == {"interrupted": 3, "pending": 1, "processed": 1}
    assert counts.by_status == {"interrupted": 3, "pending": 1, "processed": 1}
    assert counts.total == 5


async def test_while_a_write_holds_the_gate_v1s_own_status_is_reported_and_retry_is_busy(store_root, fake_status):
    engine = Databasise(store_root=store_root, workspace=_WS)

    with engine_module._write_gate(engine._v1_working_dir()):
        status = await engine.corpus_status()
        counts = await engine.document_counts()
        with pytest.raises(StoreBusyError) as busy:
            await engine.retry_document("a")

    assert {doc.document_id: doc.status for doc in status.documents}["a"] == "processing"
    assert counts.by_status == _COUNTS
    assert busy.value.store_kind == "corpus"
