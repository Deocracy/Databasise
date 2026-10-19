"""RUN-10: an upload-poll-delete round trip shows the document counts drop after a delete, over REST
and in-process.

The stub ingest and delete Part bodies and the faked ``run_corpus_op("status", ...)`` share one
in-memory corpus. A delete therefore lowers the counts only if it really removes the document, and a
second delete of the same id reports ``not_found`` because the document is gone, not because a
different stub was swapped in.
"""

from __future__ import annotations

import dataclasses
from collections import Counter
from typing import Any

import pytest

pytest.importorskip("fastapi")

import databasise.seam.engine as engine_module
from databasise.parts.registry import PartRegistry, default_registry
from databasise.parts_core.declared_only import LIGHTRAG_FULL_DELETE_PART, LIGHTRAG_FULL_INGEST_PART
from databasise.runner.trace import TokenAccounting
from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.rest import create_app
from databasise.tests.fixtures.v1_corpus_driver_stub import _run_health, _run_status
from fastapi.testclient import TestClient


def _shared_corpus(monkeypatch) -> tuple[dict[str, dict[str, Any]], PartRegistry]:
    """Returns the shared corpus (document id -> {track_id, status}) and a full default registry
    whose LightRAG ingest/delete parts write to it. Also patches the engine's ``run_corpus_op``
    so status reads report from it."""
    corpus: dict[str, dict[str, Any]] = {}

    async def _ingest_body(ctx) -> dict[str, Any]:
        config = ctx.config or {}
        documents = config.get("documents") or []
        for document in documents:
            corpus[document["id"]] = {"track_id": config.get("track_id"), "status": "processed"}
        return {
            "track_id": config.get("track_id"),
            "enqueued": len(documents),
            "usage": None,
            "tokens": TokenAccounting(counted_by="unbudgetable"),
        }

    async def _delete_body(ctx) -> dict[str, Any]:
        doc_id = (ctx.config or {}).get("doc_id")
        found = corpus.pop(doc_id, None) is not None
        if found:
            for store in ("graph", "vector", "kv"):
                ctx.record_store_touch(store)
        status = "success" if found else "not_found"
        return {
            "status": status,
            "doc_id": doc_id,
            "message": f"stub delete status={status}",
            "status_code": 200 if found else 404,
            "file_path": None,
            "usage": None,
            "tokens": TokenAccounting(counted_by="unbudgetable"),
        }

    def _fake_run_corpus_op(op: str, payload: dict[str, Any], **_kwargs: Any) -> dict[str, Any]:
        if op == "status":
            documents = [
                {"document_id": doc_id, "_track_id": row["track_id"], "status": row["status"],
                 "updated_at": "t", "error_message": None}
                for doc_id, row in corpus.items()
            ]
            counts = dict(Counter(row["status"] for row in corpus.values()))
            return _run_status({**payload, "_stub_documents": documents, "_stub_counts": counts})
        if op == "health":
            return _run_health(payload)
        raise AssertionError(f"unexpected corpus op {op!r}")

    monkeypatch.setattr(engine_module, "run_corpus_op", _fake_run_corpus_op)

    swapped = {
        part.name_at_version: part
        for part in (
            dataclasses.replace(LIGHTRAG_FULL_INGEST_PART, body=_ingest_body),
            dataclasses.replace(LIGHTRAG_FULL_DELETE_PART, body=_delete_body),
        )
    }
    base = default_registry()
    registry = PartRegistry(seed_tracer_parts=False)
    for name in base.keys():
        part = base.get(name)
        registry.register(swapped.get(part.name_at_version, part))
    return corpus, registry


def test_rest_upload_poll_delete_drops_the_counts_by_one(store_root, monkeypatch):
    corpus, registry = _shared_corpus(monkeypatch)
    client = TestClient(create_app(store_root=store_root, workspace="run10-rest", registry=registry))

    upload = client.post(
        "/documents/upload",
        files={"file": ("doc.txt", b"hello world", "text/plain")},
        data={"document_id": "run10-doc"},
    )
    assert upload.status_code == 200, upload.text
    job = client.get(f"/jobs/{upload.json()['job_id']}")
    assert job.status_code == 200, job.text
    assert [d["status"] for d in job.json()["documents"]] == ["processed"]

    before = client.get("/corpus/counts")
    assert before.status_code == 200, before.text
    assert before.json()["by_status"] == {"processed": 1}
    assert before.json()["total"] == 1

    deleted = client.delete("/documents/run10-doc")
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["status"] == "success"
    assert "run10-doc" not in corpus

    after = client.get("/corpus/counts")
    assert after.status_code == 200, after.text
    assert after.json()["by_status"].get("processed", 0) == before.json()["by_status"]["processed"] - 1 == 0
    assert after.json()["total"] == before.json()["total"] - 1 == 0

    again = client.delete("/documents/run10-doc")
    assert again.status_code == 200, again.text
    assert again.json()["status"] == "not_found"
    assert client.get("/corpus/counts").json()["total"] == 0


async def test_in_process_upload_poll_delete_drops_the_counts_by_one(store_root, monkeypatch):
    corpus, registry = _shared_corpus(monkeypatch)
    engine = Databasise(store_root=store_root, workspace="run10-in-process", registry=registry)

    job = await engine.ingest(IngestDocument(text="hello world", document_id="run10-doc-2"))
    status = await engine.get_job_status(job.job_id)
    assert [d.status for d in status.documents] == ["processed"]

    before = await engine.document_counts()
    assert before.by_status == {"processed": 1}
    assert before.total == 1

    outcome = await engine.delete_document("run10-doc-2")
    assert outcome.status == "success"
    assert "run10-doc-2" not in corpus

    after = await engine.document_counts()
    assert after.by_status.get("processed", 0) == before.by_status["processed"] - 1 == 0
    assert after.total == before.total - 1 == 0

    assert (await engine.delete_document("run10-doc-2")).status == "not_found"
    assert (await engine.document_counts()).total == 0
