"""05-04-PLAN.md Task 1: ``Databasise.get_job_status()`` — API-01's polling half. One test per
job-status ``<behavior>`` bullet, driven by monkeypatching ``databasise.seam.engine.run_corpus_op``
with a fake that reuses the real stub driver's own ``_run_status`` logic
(``databasise.tests.fixtures.v1_corpus_driver_stub``) — no subprocess, no v1 venv, but the same
slicing/filtering contract the real leaf script implements. ``test_corpus_status.py`` covers
health/counts/pagination/no-content behaviours; this file covers job-status behaviours only.
"""

from __future__ import annotations

from typing import Any

import pytest

import databasise.seam.engine as engine_module
from databasise.seam.corpus import DocumentStatusEntry, JobStatus, Page
from databasise.seam.engine import Databasise
from databasise.seam.refusals import UnknownJobError
from databasise.tests.fixtures.v1_corpus_driver_stub import _run_health, _run_status


def _make_fake_run_corpus_op(*, documents: list[dict[str, Any]] = (), counts: dict[str, int] | None = None):
    """A fake matching ``run_corpus_op``'s own call signature (``op, payload, *, timeout=None,
    **kwargs``) that serves ``"status"``/``"health"`` entirely in-memory by delegating to the real
    stub driver's own functions — never a second, independently-maintained slicing implementation.
    """
    counts = counts if counts is not None else {}
    documents = list(documents)

    def _fake(op: str, payload: dict[str, Any], *, timeout: float | None = None, **kwargs: Any) -> dict[str, Any]:
        job = {**payload, "_stub_documents": documents, "_stub_counts": counts}
        if op == "status":
            return _run_status(job)
        if op == "health":
            return _run_health(job)
        raise AssertionError(f"unexpected op {op!r}")

    return _fake


def _make_engine(store_root) -> Databasise:
    return Databasise(store_root=store_root, workspace="test-job-status")


_KNOWN_JOB_DOCUMENTS = [
    {
        "document_id": "doc-1",
        "_track_id": "job-1",
        "status": "processed",
        "updated_at": "2026-01-01T00:00:00Z",
        "error_message": None,
    },
    {
        "document_id": "doc-2",
        "_track_id": "job-1",
        "status": "failed",
        "updated_at": "2026-01-01T00:01:00Z",
        "error_message": "extraction failed",
    },
]


async def test_get_job_status_for_a_known_job_returns_one_entry_per_document(store_root, monkeypatch):
    monkeypatch.setattr(
        engine_module,
        "run_corpus_op",
        _make_fake_run_corpus_op(documents=_KNOWN_JOB_DOCUMENTS, counts={"processed": 1, "failed": 1}),
    )
    engine = _make_engine(store_root)

    status = await engine.get_job_status("job-1")

    assert isinstance(status, JobStatus)
    assert status.job_id == "job-1"
    assert [doc.document_id for doc in status.documents] == ["doc-1", "doc-2"]
    assert all(isinstance(doc, DocumentStatusEntry) for doc in status.documents)


async def test_get_job_status_error_message_is_present_only_for_the_failed_document(store_root, monkeypatch):
    monkeypatch.setattr(
        engine_module, "run_corpus_op", _make_fake_run_corpus_op(documents=_KNOWN_JOB_DOCUMENTS)
    )
    engine = _make_engine(store_root)

    status = await engine.get_job_status("job-1")

    by_id = {doc.document_id: doc for doc in status.documents}
    assert by_id["doc-1"].error_message is None
    assert by_id["doc-2"].error_message == "extraction failed"


async def test_get_job_status_for_an_unknown_job_id_raises_unknown_job_error(store_root, monkeypatch):
    monkeypatch.setattr(engine_module, "run_corpus_op", _make_fake_run_corpus_op(documents=[]))
    engine = _make_engine(store_root)

    with pytest.raises(UnknownJobError) as exc_info:
        await engine.get_job_status("no-such-job")

    assert exc_info.value.job_id == "no-such-job"


async def test_get_job_status_next_offset_is_none_on_the_last_page(store_root, monkeypatch):
    documents = [
        {
            "document_id": f"doc-{i}",
            "_track_id": "job-2",
            "status": "processed",
            "updated_at": "t",
            "error_message": None,
        }
        for i in range(3)
    ]
    monkeypatch.setattr(engine_module, "run_corpus_op", _make_fake_run_corpus_op(documents=documents))
    engine = _make_engine(store_root)

    status = await engine.get_job_status("job-2", Page(limit=10, offset=0))

    assert len(status.documents) == 3
    assert status.next_offset is None


async def test_get_job_status_next_offset_advances_across_a_partial_page(store_root, monkeypatch):
    documents = [
        {
            "document_id": f"doc-{i}",
            "_track_id": "job-3",
            "status": "processed",
            "updated_at": "t",
            "error_message": None,
        }
        for i in range(5)
    ]
    monkeypatch.setattr(engine_module, "run_corpus_op", _make_fake_run_corpus_op(documents=documents))
    engine = _make_engine(store_root)

    status = await engine.get_job_status("job-3", Page(limit=2, offset=0))

    assert len(status.documents) == 2
    assert status.next_offset == 2
