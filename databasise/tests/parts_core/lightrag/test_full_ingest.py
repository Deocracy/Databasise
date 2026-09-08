"""05-01-PLAN.md Task 1: the end-to-end tracer test — one document ingested through the admitted
opaque ``lightrag/full-ingest`` node, dispatched by the real scheduler at the ``subprocess``
placement, against a stub driver (never a real v1 venv or a real LLM call) for the bulk of the
suite, plus one real-interpreter smoke test guarded by ``pytest.mark.skipif``.

Every test drives ``Databasise.ingest()`` against a registry holding a *test-local variant* of the
production ``lightrag/full-ingest@0.1.0`` Part — same name, effects, structural_depth,
artifact_scope and (a copy of) the admission record, but with its ``body`` pointed at
``databasise/tests/fixtures/v1_corpus_driver_stub.py`` via ``run_corpus_op``'s own
``driver_script=``/``interpreter=`` override points, so the suite proves the real wiring/scheduler/
admission/adapter path without paying for a real v1 process or LLM call.
"""

from __future__ import annotations

import asyncio
import dataclasses
import sys
from pathlib import Path
from typing import Any

import pytest
from databasise.foreign import CorpusOpTimeoutError, run_corpus_op
from databasise.parts.admission import MissingWallClockCeilingError
from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext
from databasise.parts_core.declared_only import LIGHTRAG_FULL_INGEST_PART
from databasise.runner.trace import TokenAccounting
from databasise.seam.corpus import IngestDocument, IngestJob
from databasise.seam.engine import Databasise
from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.validator.execution_mode import derive_execution_mode, host

_STUB_DRIVER = Path(__file__).resolve().parents[2] / "fixtures" / "v1_corpus_driver_stub.py"
_V1_VENV_PYTHON = Path(__file__).resolve().parents[4] / "v1" / ".venv" / "bin" / "python"
_V1_CORPUS_DRIVER_SCRIPT = (
    Path(__file__).resolve().parents[4] / "databasise" / "foreign" / "v1_corpus_driver_script.py"
)
_V1_ENV_PARITY = Path(__file__).resolve().parents[4] / "v1" / ".env.parity"


def _make_stub_full_ingest_body(*, timeout: float, sleep_seconds: float = 0.0):
    """A test-local ``full_ingest_body`` variant pointed at the stub driver — same shape as
    ``databasise.parts_core.lightrag.full_ingest.full_ingest_body``, but with fixed
    ``timeout=``/``driver_script=``/``interpreter=`` closure values rather than reading the
    production constant."""

    async def _body(ctx: NodeContext) -> dict[str, Any]:
        config = ctx.config or {}
        payload: dict[str, Any] = {
            "documents": config.get("documents") or [],
            "track_id": config.get("track_id"),
        }
        if sleep_seconds:
            payload["_stub_sleep_seconds"] = sleep_seconds

        result = await asyncio.to_thread(
            run_corpus_op,
            "ingest",
            payload,
            timeout=timeout,
            interpreter=Path(sys.executable),
            driver_script=_STUB_DRIVER,
        )

        usage = result.get("usage")
        if usage:
            tokens = TokenAccounting(
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
                counted_by=str(usage.get("model") or "v1-subprocess"),
            )
        else:
            tokens = TokenAccounting(counted_by="unbudgetable")

        return {
            "track_id": result.get("track_id"),
            "enqueued": result.get("enqueued", 0),
            "usage": usage,
            "tokens": tokens,
        }

    return _body


def _make_engine(store_root, *, body, ceiling: float = 5.0) -> Databasise:
    """A ``Databasise`` whose registry holds only the test-local ``lightrag/full-ingest@0.1.0``
    variant — sufficient for ``ingest()``, which never resolves a selector against the full
    registry (see ``databasise.seam.engine.Databasise.ingest``'s own docstring)."""
    admission = dataclasses.replace(LIGHTRAG_FULL_INGEST_PART.admission, wall_clock_ceiling_seconds=ceiling)
    test_part = dataclasses.replace(LIGHTRAG_FULL_INGEST_PART, body=body, admission=admission)
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(test_part)
    return Databasise(store_root=store_root, workspace="test-ingest", registry=registry)


async def test_ingest_returns_a_job_carrying_the_stub_echoed_track_id_and_enqueued_count(store_root):
    engine = _make_engine(store_root, body=_make_stub_full_ingest_body(timeout=5.0))

    job = await engine.ingest(IngestDocument(text="hello world"))

    assert isinstance(job, IngestJob)
    assert job.enqueued == 1
    assert job.job_id  # v1's own track_id, minted by the seam and echoed back by the stub


def test_derive_execution_mode_returns_subprocess_and_host_accepts_the_declared_ceiling():
    mode = derive_execution_mode(LIGHTRAG_FULL_INGEST_PART.effects, LIGHTRAG_FULL_INGEST_PART.kind)
    assert mode == "subprocess"
    host(mode, wall_clock_ceiling_seconds=LIGHTRAG_FULL_INGEST_PART.admission.wall_clock_ceiling_seconds)


def test_host_with_subprocess_placement_and_no_ceiling_raises_missing_wall_clock_ceiling_error():
    with pytest.raises(MissingWallClockCeilingError):
        host("subprocess")


async def test_a_stub_job_outlasting_a_tiny_ceiling_raises_foreign_engine_refusal_with_timeout_cause(
    store_root,
):
    tiny_ceiling = 0.1
    engine = _make_engine(
        store_root,
        body=_make_stub_full_ingest_body(timeout=tiny_ceiling, sleep_seconds=2.0),
        ceiling=tiny_ceiling,
    )

    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await engine.ingest(IngestDocument(text="slow document"))

    assert isinstance(exc_info.value.cause, CorpusOpTimeoutError)
    assert exc_info.value.cause.timeout == tiny_ceiling


async def test_two_separately_minted_ingests_return_distinct_job_ids(store_root):
    engine = _make_engine(store_root, body=_make_stub_full_ingest_body(timeout=5.0))

    job1 = await engine.ingest(IngestDocument(text="first document"))
    job2 = await engine.ingest(IngestDocument(text="second document"))

    assert job1.job_id != job2.job_id


async def test_an_ingest_with_no_reported_usage_reports_the_unbudgetable_sentinel_and_the_seam_refuses_to_count_it(
    store_root,
):
    """MODAL-02/precision (must_haves.truths): the ingest node's token spend is never
    substituted with an estimated, rounded, or zero number when the subprocess reports no usage —
    it carries the existing ``unbudgetable`` sentinel, and the seam's own existing
    ``assemble_token_breakdown`` mechanism (already proven elsewhere, e.g.
    ``tests/seam/test_token_accounting.py``) refuses to fold it into a breakdown, exercised here
    for the first time against a real (non-fixture) part's own trace.
    """
    from databasise.runner import scheduler as _scheduler
    from databasise.seam.tokens import UnbudgetableParticipantError, assemble_token_breakdown
    from databasise.validator.parse import parse_wiring

    body = _make_stub_full_ingest_body(timeout=5.0)
    admission = dataclasses.replace(LIGHTRAG_FULL_INGEST_PART.admission, wall_clock_ceiling_seconds=5.0)
    test_part = dataclasses.replace(LIGHTRAG_FULL_INGEST_PART, body=body, admission=admission)
    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(test_part)

    wiring = {
        "wiring_id": "test-ingest-unbudgetable",
        "nodes": {
            "full-ingest": {
                "component": test_part.name_at_version,
                "kind": "opaque",
                "effects": test_part.effects,
                "config": {"documents": [{"id": "doc-1", "text": "x"}], "track_id": "trace-1"},
                "deps": [],
            }
        },
        "provides": ["full-ingest"],
    }
    parsed = parse_wiring(wiring, registry)
    assert parsed.report.ok, [v.code for v in parsed.report.violations]

    scheduled = await _scheduler.run_wiring(
        parsed, registry, stores={}, determinism_setting="cache-bypassed", concurrency_setting="sequential"
    )

    ingest_trace = next(node for node in scheduled["nodes"] if node.node_id == "full-ingest")
    assert ingest_trace.tokens.counted_by == "unbudgetable"

    with pytest.raises(UnbudgetableParticipantError):
        assemble_token_breakdown(scheduled["nodes"])


@pytest.mark.skipif(not _V1_VENV_PYTHON.exists(), reason="v1/.venv/bin/python not built")
def test_the_real_driver_script_parses_and_speaks_the_protocol_for_an_empty_document_list(tmp_path):
    """Proves the real leaf script under v1's own interpreter builds v1's facade and speaks the
    stdin/stdout protocol, without paying for a full LLM extraction (an empty document list never
    reaches the LLM)."""
    result = run_corpus_op(
        "ingest",
        {"documents": [], "track_id": "real-interpreter-smoke-test"},
        timeout=120.0,
        interpreter=_V1_VENV_PYTHON,
        driver_script=_V1_CORPUS_DRIVER_SCRIPT,
        env_path=_V1_ENV_PARITY,
        working_dir=tmp_path / "corpus_working_dir",
    )
    assert "track_id" in result
