"""05-04-PLAN.md Task 1: ``Databasise.health()``/``corpus_status()``/``document_counts()`` — the
API-06 bounding proof. One test per health/counts/pagination/no-content ``<behavior>`` bullet.
``test_ingest_job_status.py`` covers ``get_job_status()``'s own behaviours; this file covers the
rest. Driven the same way that file is — monkeypatching ``databasise.seam.engine.run_corpus_op``
with a fake that delegates to the real stub driver's own ``_run_status``/``_run_health`` functions
(``databasise.tests.fixtures.v1_corpus_driver_stub``), so there is exactly one slicing/filtering
implementation under test, never two independently-maintained copies.
"""

from __future__ import annotations

from typing import Any

import pydantic
import pytest

import databasise.seam.engine as engine_module
from databasise.seam import corpus as corpus_module
from databasise.seam.corpus import MAX_PAGE_SIZE, CorpusStatus, DocumentCounts, HealthReport, Page
from databasise.seam.engine import Databasise
from databasise.seam.refusals import PageSizeExceededError
from databasise.tests.fixtures.v1_corpus_driver_stub import _run_health, _run_status


def _make_fake_run_corpus_op(
    *,
    documents: list[dict[str, Any]] = (),
    counts: dict[str, int] | None = None,
    working_dir_present: bool = True,
    storages_initialized: bool = True,
):
    counts = counts if counts is not None else {}
    documents = list(documents)

    def _fake(op: str, payload: dict[str, Any], *, timeout: float | None = None, **kwargs: Any) -> dict[str, Any]:
        job = {
            **payload,
            "_stub_documents": documents,
            "_stub_counts": counts,
            "_stub_working_dir_present": working_dir_present,
            "_stub_storages_initialized": storages_initialized,
        }
        if op == "status":
            return _run_status(job)
        if op == "health":
            return _run_health(job)
        raise AssertionError(f"unexpected op {op!r}")

    return _fake


def _make_engine(store_root) -> Databasise:
    return Databasise(store_root=store_root, workspace="test-corpus-status")


def _big_document_list(count: int) -> list[dict[str, Any]]:
    return [
        {"document_id": f"doc-{i:04d}", "status": "processed", "updated_at": "t", "error_message": None}
        for i in range(count)
    ]


# ------------------------------------------------------------------------------------------- #
# corpus_status(): bounded, paginated document list, never a full corpus dump.
# ------------------------------------------------------------------------------------------- #


async def test_corpus_status_pages_across_the_whole_corpus_in_at_least_three_pages(store_root, monkeypatch):
    """The stub's own configurable document count, large enough to exercise pagination across at
    least three pages (05-04-PLAN.md Task F) — 250 documents at MAX_PAGE_SIZE (100) is three pages
    (100 + 100 + 50)."""
    monkeypatch.setattr(
        engine_module, "run_corpus_op", _make_fake_run_corpus_op(documents=_big_document_list(250))
    )
    engine = _make_engine(store_root)

    page1 = await engine.corpus_status(Page(limit=MAX_PAGE_SIZE, offset=0))
    assert isinstance(page1, CorpusStatus)
    assert len(page1.documents) == 100
    assert page1.total == 250
    assert page1.next_offset == 100

    page2 = await engine.corpus_status(Page(limit=MAX_PAGE_SIZE, offset=100))
    assert len(page2.documents) == 100
    assert page2.next_offset == 200

    page3 = await engine.corpus_status(Page(limit=MAX_PAGE_SIZE, offset=200))
    assert len(page3.documents) == 50
    assert page3.next_offset is None


async def test_corpus_status_defaults_to_the_first_page_when_no_page_is_given(store_root, monkeypatch):
    monkeypatch.setattr(
        engine_module, "run_corpus_op", _make_fake_run_corpus_op(documents=_big_document_list(3))
    )
    engine = _make_engine(store_root)

    status = await engine.corpus_status()

    assert len(status.documents) == 3
    assert status.next_offset is None


def test_page_limit_above_the_cap_is_refused_never_clamped():
    """A ``Page.limit`` above ``MAX_PAGE_SIZE`` raises inside the model validator — pydantic wraps
    it into a ``ValidationError`` (the same wrapping ``AmbiguousIngestPayloadError``'s own module
    docstring documents for ``IngestDocument``), so this asserts on the wrapped message's own
    load-bearing substring, mirroring ``test_full_ingest.py``'s identical pattern for that refusal.
    """
    Page(limit=MAX_PAGE_SIZE)  # never refused at the cap itself

    with pytest.raises(pydantic.ValidationError) as exc_info:
        Page(limit=MAX_PAGE_SIZE + 1)

    assert "PageSizeExceededError" in str(exc_info.value)


def test_page_size_exceeded_error_carries_requested_and_limit_as_real_integers():
    """The typed refusal itself, constructed directly (pydantic's wrapping loses the original
    exception object) — matches the plan's own acceptance criterion of real integers, asserted
    directly."""
    error = PageSizeExceededError(requested=MAX_PAGE_SIZE + 1, limit=MAX_PAGE_SIZE)
    assert error.requested == MAX_PAGE_SIZE + 1
    assert error.limit == MAX_PAGE_SIZE
    assert isinstance(error.requested, int)
    assert isinstance(error.limit, int)


def test_page_with_a_negative_offset_raises_value_error():
    with pytest.raises(pydantic.ValidationError) as exc_info:
        Page(offset=-1)
    assert "non-negative" in str(exc_info.value)


# ------------------------------------------------------------------------------------------- #
# document_counts(): a fixed-size record, never a per-document list.
# ------------------------------------------------------------------------------------------- #


async def test_document_counts_by_status_keys_match_and_total_is_their_sum(store_root, monkeypatch):
    counts = {"processed": 3, "failed": 1, "pending": 2}
    monkeypatch.setattr(engine_module, "run_corpus_op", _make_fake_run_corpus_op(counts=counts))
    engine = _make_engine(store_root)

    result = await engine.document_counts()

    assert isinstance(result, DocumentCounts)
    assert result.by_status == counts
    assert result.total == sum(counts.values())


# ------------------------------------------------------------------------------------------- #
# health(): a fixed-size liveness record; never raises for an unreachable participant.
# ------------------------------------------------------------------------------------------- #


async def test_health_returns_the_fixed_field_set(store_root, monkeypatch):
    monkeypatch.setattr(engine_module, "run_corpus_op", _make_fake_run_corpus_op())
    engine = _make_engine(store_root)

    report = await engine.health()

    assert isinstance(report, HealthReport)
    assert set(report.stores) == {"kv", "vector", "graph"}
    assert set(report.engine) == {"interpreter_present", "working_dir_present", "storages_initialized"}
    assert report.status in ("ok", "degraded")


async def test_health_reports_degraded_and_never_raises_when_the_foreign_engine_op_fails(
    store_root, monkeypatch
):
    def _raising_run_corpus_op(op: str, payload: dict[str, Any], *, timeout: float | None = None, **kwargs: Any):
        raise RuntimeError("simulated foreign engine failure")

    monkeypatch.setattr(engine_module, "run_corpus_op", _raising_run_corpus_op)
    engine = _make_engine(store_root)

    report = await engine.health()

    assert report.status == "degraded"
    assert report.engine["working_dir_present"] is False
    assert report.engine["storages_initialized"] is False


# ------------------------------------------------------------------------------------------- #
# No field on any corpus-status model ever carries document/chunk/embedding/graph content.
# ------------------------------------------------------------------------------------------- #


def test_no_corpus_status_model_declares_a_content_bearing_field():
    banned = {"text", "content", "raw", "body", "chunk", "chunks", "embedding", "vector", "payload", "node"}
    for name in ("JobStatus", "CorpusStatus", "DocumentCounts", "HealthReport", "DocumentStatusEntry"):
        model = getattr(corpus_module, name)
        overlap = banned & set(model.model_fields)
        assert not overlap, (name, overlap)
