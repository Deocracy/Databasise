"""05-03-PLAN.md Task 2: ``Databasise.delete_document()``'s idempotency and concurrency-status
behaviours, driven by the stub driver — mirrors ``test_full_ingest.py``'s own stub-driver-backed
test-local-Part-variant pattern exactly. Task 3 appends the real, graph-aware-cleanup proof to
this same file.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import pytest

import databasise.foreign.v1_corpus_adapter as _v1_corpus_adapter
from databasise.foreign import CorpusOpTimeoutError, run_corpus_op
from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext
from databasise.parts_core.declared_only import LIGHTRAG_FULL_DELETE_PART
from databasise.runner.trace import TokenAccounting
from databasise.seam.corpus import DeletionOutcome
from databasise.seam.engine import Databasise
from databasise.seam.refusals import ForeignEngineRefusalError, UnknownDocumentError

_STUB_DRIVER = Path(__file__).resolve().parents[1] / "fixtures" / "v1_corpus_driver_stub.py"

_REPO_ROOT = Path(__file__).resolve().parents[3]
_V1_ROOT = _REPO_ROOT / "v1"
_V1_PARITY_WORKING_DIR = _V1_ROOT / ".parity_working_dir"
_V1_VENV_PYTHON = _V1_ROOT / ".venv" / "bin" / "python"
_V1_CORPUS_DRIVER_SCRIPT = _REPO_ROOT / "databasise" / "foreign" / "v1_corpus_driver_script.py"
_V1_ENV_PARITY = _V1_ROOT / ".env.parity"
_CORPUS_MANIFEST = (
    _REPO_ROOT / "databasise" / "tests" / "fixtures" / "corpus" / "MANIFEST.json"
)

_REAL_DELETE_ENV_VAR = "DATABASISE_RUN_REAL_DELETE"


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


# ---------------------------------------------------------------------------------------------
# 05-03-PLAN.md Task 3: API-02's graph-aware cleanup proved against a real v1 working directory
# — an entity shared with a surviving document survives with its source set reduced; an entity
# the deletion orphans is removed. Real leg, opt-in (cost gate + precondition gate), never a
# stub.
# ---------------------------------------------------------------------------------------------


def _target_document_id() -> str:
    """The first document id in the corpus manifest, sorted — deterministic, never a hand-picked
    guess. A one-time reconnaissance pass over this v1 build (recorded in 05-03-SUMMARY.md) found
    every document in this 20-document corpus except three already contributes both a shared and
    an orphan-only entity, so the first document alphabetically already proves the claim without
    a search loop.
    """
    manifest = json.loads(_CORPUS_MANIFEST.read_text(encoding="utf-8"))
    return sorted(manifest["documents"])[0]


def _real_entities(doc_id: str, working_dir: Path) -> dict[str, Any]:
    return run_corpus_op(
        "entities",
        {"doc_id": doc_id},
        timeout=120.0,
        interpreter=_V1_VENV_PYTHON,
        driver_script=_V1_CORPUS_DRIVER_SCRIPT,
        env_path=_V1_ENV_PARITY,
        working_dir=working_dir,
    )


def _partition_shared_vs_orphan_only(
    entities: dict[str, list[str]], chunk_ids: list[str]
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """An entity is "shared" when its source_id set names a chunk outside ``chunk_ids`` (this
    document's own chunks) — i.e. a chunk belonging to another document — and "orphan-only" when
    every chunk id in its set is one of ``chunk_ids``."""
    chunk_set = set(chunk_ids)
    shared: dict[str, list[str]] = {}
    orphan_only: dict[str, list[str]] = {}
    for name, sources in entities.items():
        if set(sources) - chunk_set:
            shared[name] = sources
        else:
            orphan_only[name] = sources
    return shared, orphan_only


@pytest.mark.skipif(
    not _V1_PARITY_WORKING_DIR.exists(),
    reason=(
        f"v1/.parity_working_dir not found at {_V1_PARITY_WORKING_DIR} — run "
        "v1/scripts/run_parity_ingest.py first (Phase 3's committed ingest build; 03-02-PLAN.md's "
        "D-01 pins every recorded parity number to this one build, and this test's own copy never "
        "mutates it)"
    ),
)
@pytest.mark.skipif(
    os.environ.get(_REAL_DELETE_ENV_VAR) != "1",
    reason=(
        f"real deletion against the v1 parity build is opt-in — set {_REAL_DELETE_ENV_VAR}=1 to "
        "run it. Cost: one real v1 subprocess deletion of a real document, which may reach the "
        "LLM for a partial entity/relation rebuild when no extraction cache is present."
    ),
)
async def test_deleting_a_real_document_reduces_shared_entities_and_removes_orphan_only_ones(
    tmp_path, store_root, monkeypatch
):
    working_dir_copy = tmp_path / "parity_working_dir_copy"
    shutil.copytree(_V1_PARITY_WORKING_DIR, working_dir_copy)
    doc_id = _target_document_id()

    before = _real_entities(doc_id, working_dir_copy)
    chunk_ids = before["chunk_ids"]
    if not chunk_ids:
        pytest.skip(f"document {doc_id!r} carries no doc-status chunk_ids in this v1 build")
    shared_before, orphan_before = _partition_shared_vs_orphan_only(before["entities"], chunk_ids)
    if not shared_before:
        pytest.skip(
            f"document {doc_id!r} contributes no shared entity in this v1 build — cannot prove "
            "the shared-entity half of this claim"
        )
    if not orphan_before:
        pytest.skip(
            f"document {doc_id!r} contributes no orphan-only entity in this v1 build — cannot "
            "prove the orphan-removal half of this claim"
        )

    # Redirects the real, unmodified production Part's subprocess launch at the copied directory
    # — run_corpus_op reads DEFAULT_V1_WORKING_DIR from this module's own globals at call time
    # (module-level `working_dir or DEFAULT_V1_WORKING_DIR`), so this monkeypatch is visible to
    # full_delete_body's call without any test-only override plumbing in production code. The
    # original v1/.parity_working_dir is never opened for writing — only working_dir_copy is.
    monkeypatch.setattr(_v1_corpus_adapter, "DEFAULT_V1_WORKING_DIR", working_dir_copy)

    registry = PartRegistry(seed_tracer_parts=False)
    registry.register(LIGHTRAG_FULL_DELETE_PART)
    engine = Databasise(store_root=store_root, workspace="test-delete-real", registry=registry)

    start = time.monotonic()
    outcome = await engine.delete_document(doc_id)
    duration_seconds = time.monotonic() - start

    assert outcome.status == "success", outcome.message

    # The deletion just removed doc_id's own doc-status record, so op == "entities" (keyed by
    # doc_id) can no longer find anything "for this document" — this re-check instead looks up
    # every entity name captured before deletion, by name, via op == "entity_info".
    checked_names = list(shared_before) + list(orphan_before)
    after = run_corpus_op(
        "entity_info",
        {"entity_names": checked_names},
        timeout=120.0,
        interpreter=_V1_VENV_PYTHON,
        driver_script=_V1_CORPUS_DRIVER_SCRIPT,
        env_path=_V1_ENV_PARITY,
        working_dir=working_dir_copy,
    )
    after_entities = {name: sources for name, sources in after["entities"].items() if sources is not None}

    example_shared_name = next(iter(shared_before))
    for name, before_sources in shared_before.items():
        assert name in after_entities, f"shared entity {name!r} was removed entirely — over-deletion"
        after_sources = set(after_entities[name])
        assert not (after_sources & set(chunk_ids)), (
            f"shared entity {name!r} still names one of the deleted document's chunk ids"
        )
        assert after_sources, (
            f"shared entity {name!r} lost every surviving source — should have been rebuilt from "
            "surviving sources, not emptied"
        )

    for name in orphan_before:
        assert name not in after_entities, f"orphan-only entity {name!r} survived the deletion"

    assert duration_seconds < LIGHTRAG_FULL_DELETE_PART.admission.wall_clock_ceiling_seconds, (
        f"real deletion took {duration_seconds:.1f}s, exceeding the declared "
        f"{LIGHTRAG_FULL_DELETE_PART.admission.wall_clock_ceiling_seconds}s ceiling — this is "
        "evidence for raising the ceiling deliberately in full_delete.py, never a reason to "
        "widen this assertion"
    )

    # 05-03-SUMMARY.md's own evidence section (Task 3 item D) is populated from this line's
    # output — printed with -s/-rs so a re-run always reproduces the same numbers without
    # re-reading this test's source.
    print(
        "\n05-03 real-delete evidence: "
        f"doc_id={doc_id!r} shared_count={len(shared_before)} orphan_only_count={len(orphan_before)} "
        f"example_shared_entity={example_shared_name!r} "
        f"before_sources={shared_before[example_shared_name]!r} "
        f"after_sources={sorted(after_entities[example_shared_name])!r} "
        f"duration_seconds={duration_seconds:.2f}"
    )
