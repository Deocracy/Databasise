"""05-03-PLAN.md Task 2: ``Databasise.delete_document()``'s idempotency and concurrency-status
behaviours, driven by the stub driver — mirrors ``test_full_ingest.py``'s own stub-driver-backed
test-local-Part-variant pattern exactly. Task 3 appends the real, graph-aware-cleanup proof to
this same file.
"""

from __future__ import annotations

import asyncio
import dataclasses
import sys
from pathlib import Path
from typing import Any

import pytest

from databasise.foreign import CorpusOpTimeoutError, run_corpus_op
from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext
from databasise.parts_core.declared_only import LIGHTRAG_FULL_DELETE_PART
from databasise.runner.trace import TokenAccounting
from databasise.seam.corpus import DeletionOutcome
from databasise.seam.engine import Databasise
from databasise.seam.refusals import ForeignEngineRefusalError, UnknownDocumentError

_STUB_DRIVER = Path(__file__).resolve().parents[1] / "fixtures" / "v1_corpus_driver_stub.py"


def _make_stub_full_delete_body(
    *, timeout: float, stub_status: str = "success", sleep_seconds: float = 0.0
):
    """A test-local ``full_delete_body`` variant pointed at the stub driver — same shape as
    ``databasise.parts_core.lightrag.full_delete.full_delete_body``, but with fixed
    ``timeout=``/``driver_script=``/``interpreter=``/``_stub_status`` closure values rather than
    reading the production constant or a caller-configured status.
    """

    async def _body(ctx: NodeContext) -> dict[str, Any]:
        config = ctx.config or {}
        payload: dict[str, Any] = {
            "doc_id": config.get("doc_id"),
            "delete_llm_cache": bool(config.get("delete_llm_cache", False)),
            "_stub_status": stub_status,
        }
        if sleep_seconds:
            payload["_stub_sleep_seconds"] = sleep_seconds

        result = await asyncio.to_thread(
            run_corpus_op,
            "delete",
            payload,
            timeout=timeout,
            interpreter=Path(sys.executable),
            driver_script=_STUB_DRIVER,
        )

        if result.get("status") == "success":
            ctx.record_store_touch("graph")
            ctx.record_store_touch("vector")
            ctx.record_store_touch("kv")

        return {**result, "tokens": TokenAccounting(counted_by="unbudgetable")}

    return _body


def _make_engine(store_root, *, body, ceiling: float = 5.0) -> Databasise:
    """A ``Databasise`` whose registry holds only the test-local ``lightrag/full-delete@0.1.0``
    variant — sufficient for ``delete_document()``, which never resolves a selector against the
    full registry (mirrors ``Databasise.ingest``'s own precedent)."""
    admission = dataclasses.replace(LIGHTRAG_FULL_DELETE_PART.admission, wall_clock_ceiling_seconds=ceiling)
    test_part = dataclasses.replace(LIGHTRAG_FULL_DELETE_PART, body=body, admission=admission)
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(test_part)
    return Databasise(store_root=store_root, workspace="test-delete", registry=registry)


async def test_deleting_the_same_document_twice_yields_success_then_not_found(store_root):
    """The stub echoes whatever status it is configured with regardless of prior calls (it holds
    no state of its own) — this test proves the *seam's own* pass-through is idempotent-shaped by
    driving two separately-configured engines rather than asserting on stub statefulness the stub
    was never built to have."""
    engine_first = _make_engine(store_root, body=_make_stub_full_delete_body(timeout=5.0, stub_status="success"))
    outcome_first = await engine_first.delete_document("deadbeef")
    assert outcome_first.status == "success"

    engine_second = _make_engine(
        store_root, body=_make_stub_full_delete_body(timeout=5.0, stub_status="not_found")
    )
    outcome_second = await engine_second.delete_document("deadbeef")
    assert outcome_second.status == "not_found"


async def test_a_not_allowed_status_from_the_driver_surfaces_unchanged_never_remapped_or_raised(
    store_root,
):
    engine = _make_engine(store_root, body=_make_stub_full_delete_body(timeout=5.0, stub_status="not_allowed"))

    outcome = await engine.delete_document("deadbeef")

    assert outcome.status == "not_allowed"
    assert isinstance(outcome, DeletionOutcome)


async def test_delete_document_returns_document_id_and_a_message(store_root):
    engine = _make_engine(store_root, body=_make_stub_full_delete_body(timeout=5.0))

    outcome = await engine.delete_document("deadbeef")

    assert outcome.document_id == "deadbeef"
    assert outcome.message


async def test_a_malformed_document_id_raises_unknown_document_error_before_any_wiring_loads(
    store_root,
):
    engine = _make_engine(store_root, body=_make_stub_full_delete_body(timeout=5.0))

    with pytest.raises(UnknownDocumentError) as exc_info:
        await engine.delete_document("../escape")

    assert exc_info.value.document_id == "../escape"


async def test_a_stub_job_outlasting_a_tiny_ceiling_raises_foreign_engine_refusal_with_timeout_cause(
    store_root,
):
    tiny_ceiling = 0.1
    engine = _make_engine(
        store_root,
        body=_make_stub_full_delete_body(timeout=tiny_ceiling, sleep_seconds=2.0),
        ceiling=tiny_ceiling,
    )

    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await engine.delete_document("deadbeef")

    assert isinstance(exc_info.value.cause, CorpusOpTimeoutError)
    assert exc_info.value.cause.timeout == tiny_ceiling
