"""05-03-PLAN.md Task 2: ``Databasise.delete_document()``'s idempotency and concurrency-status
behaviours, driven by the stub driver — mirrors ``test_full_ingest.py``'s own stub-driver-backed
test-local-Part-variant pattern exactly.

11-01-PLAN.md Task 2 (D-05) replaced the env-gated real-delete proof (``DATABASISE_RUN_REAL_DELETE``,
``v1/.parity_working_dir`` and the driver's ``entities``/``entity_info`` ops) with a hermetic one:
the real v1 driver against the loopback stub model server, read back from the v2 graph after the
``lightrag/v1-index-sync`` mirror.
"""

from __future__ import annotations

import asyncio
import dataclasses
import sys
from pathlib import Path
from typing import Any

import pytest

from databasise.clients.builder import build_clients
from databasise.foreign import CorpusOpTimeoutError, MissingV1InterpreterError, run_corpus_op
from databasise.parts.registry import PartRegistry, default_registry
from databasise.parts.schema import NodeContext
from databasise.parts_core.declared_only import LIGHTRAG_FULL_DELETE_PART
from databasise.runner.trace import TokenAccounting
from databasise.seam.corpus import DeletionOutcome, IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.refusals import ForeignEngineRefusalError, InvalidDocumentIdError
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.tests.fixtures.v1_stub_server import real_v1, requires_v1  # noqa: F401 - fixture

_STUB_DRIVER = Path(__file__).resolve().parents[1] / "fixtures" / "v1_corpus_driver_stub.py"


def _make_stub_full_delete_body(
    *,
    timeout: float,
    stub_status: str = "success",
    sleep_seconds: float = 0.0,
    interpreter: Path | None = None,
):
    """A test-local ``full_delete_body`` variant pointed at the stub driver — same shape as
    ``databasise.parts_core.lightrag.full_delete.full_delete_body``, but with fixed
    ``timeout=``/``driver_script=``/``interpreter=``/``_stub_status`` closure values rather than
    reading the production constant or a caller-configured status. ``interpreter`` defaults to the
    current test process's own interpreter (unchanged behaviour for every existing call site) —
    passing a nonexistent path is this module's own reproduction of a real
    ``MissingV1InterpreterError`` (G-05-1 / WR-01).
    """
    resolved_interpreter = interpreter if interpreter is not None else Path(sys.executable)

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
            interpreter=resolved_interpreter,
            driver_script=_STUB_DRIVER,
        )

        if result.get("status") == "success":
            ctx.record_store_touch("graph")
            ctx.record_store_touch("vector")
            ctx.record_store_touch("kv")

        return {**result, "tokens": TokenAccounting(counted_by="unbudgetable")}

    return _body


def _registry_with(part: Any) -> PartRegistry:
    """A full ``default_registry()`` with ``part``'s own ``name_at_version`` swapped in
    (06-10-PLAN.md deviation). ``Databasise.delete_document()`` now resolves the default §18.4
    selector before dispatching (closing Gap 1(a) required removing the module constant it used
    to read directly) — ``resolve_selector``'s default branch walks every candidate wiring
    ``databasise.wirings.resolve.all_wirings()`` enumerates and requires each to parse against the
    registry; a registry holding only the part under test can no longer satisfy that."""
    base = default_registry()
    registry = PartRegistry(seed_tracer_parts=False)
    for name in base.keys():
        candidate = base.get(name)
        registry.register(part if candidate.name_at_version == part.name_at_version else candidate)
    return registry


def _make_engine(store_root, *, body, ceiling: float = 5.0) -> Databasise:
    """A ``Databasise`` whose registry holds the test-local ``lightrag/full-delete@0.1.0`` variant
    swapped into a full default registry (see :func:`_registry_with`)."""
    admission = dataclasses.replace(LIGHTRAG_FULL_DELETE_PART.admission, wall_clock_ceiling_seconds=ceiling)
    test_part = dataclasses.replace(LIGHTRAG_FULL_DELETE_PART, body=body, admission=admission)
    registry = _registry_with(test_part)
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


async def test_a_malformed_document_id_raises_invalid_document_id_error_before_any_wiring_loads(
    store_root,
):
    engine = _make_engine(store_root, body=_make_stub_full_delete_body(timeout=5.0))

    with pytest.raises(InvalidDocumentIdError) as exc_info:
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


async def test_an_unclassified_node_failure_through_delete_document_raises_rather_than_a_causeless_fail(
    store_root, tmp_path
):
    """WR-01 / G-05-1: same root cause as CR-02, one file over. Pointing the delete node's
    interpreter at a nonexistent path previously produced ``DeletionOutcome(status='fail',
    message='')`` with no cause (05-REVIEW.md's own recorded transcript) — it now raises
    ``ForeignEngineRefusalError`` carrying the real cause, through the same shared
    ``_node_result_or_refuse`` helper ``ingest()`` routes through.

    ``test_a_not_allowed_status_from_the_driver_surfaces_unchanged_never_remapped_or_raised`` and
    ``test_deleting_the_same_document_twice_yields_success_then_not_found`` are the tests that hold
    the line between "v1 answered not_found/not_allowed" (a normal outcome, never a refusal) and
    "the machine could not get an answer at all" (this refusal) — both still pass unmodified,
    proving this change does not blur that distinction.
    """
    missing_interpreter = tmp_path / "does-not-exist" / "python"
    engine = _make_engine(
        store_root,
        body=_make_stub_full_delete_body(timeout=5.0, interpreter=missing_interpreter),
    )

    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await engine.delete_document("deadbeef")

    assert exc_info.value.operation == "delete"
    assert isinstance(exc_info.value.cause, MissingV1InterpreterError)


# ---------------------------------------------------------------------------------------------
# API-02's graph-aware cleanup, proved hermetically (11-01-PLAN.md Task 2, D-05): an entity shared
# with a surviving document survives with its source set reduced to that document's chunks; an
# entity only the deleted document named is removed. Read from the v2 graph after the mirror.
# ---------------------------------------------------------------------------------------------

_SEP = "<SEP>"


@requires_v1
async def test_deleting_a_document_reduces_shared_entities_and_removes_orphan_only_ones(real_v1):  # noqa: F811
    store_root, ws = real_v1.store_root, "test-delete-real"
    engine = Databasise(store_root=store_root, workspace=ws, clients=build_clients(real_v1.client_env))
    await engine.ingest(IngestDocument(document_id="docA", text="UNIQshared and UNIQonlya meet here."))
    await engine.ingest(IngestDocument(document_id="docB", text="UNIQshared and UNIQonlyb meet there."))

    outcome = await engine.delete_document("docA")

    assert outcome.status == "success", outcome.message
    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace=ws, store_root=store_root)
    kv = SqliteKVStore(namespace="text_chunks", workspace=ws, store_root=store_root)
    try:
        assert await graph.get_node("UNIQonlya Corp") is None, "an orphan-only entity survived the deletion"
        shared = await graph.get_node("UNIQshared Corp")
        assert shared is not None, "a shared entity was removed entirely: over-deletion"
        sources = [s for s in str(shared.get("source_id") or "").split(_SEP) if s]
        assert sources, "the shared entity lost every surviving source"
        owners = {(await kv.get_by_id(chunk_id) or {}).get("full_doc_id") for chunk_id in sources}
        assert owners == {"docB"}, f"the shared entity still names chunks of {owners - {'docB'}}"
    finally:
        await graph.finalize()
        await kv.finalize()
