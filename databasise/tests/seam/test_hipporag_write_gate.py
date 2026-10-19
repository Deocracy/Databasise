"""12-06-PLAN.md Task 3 (D-14): HippoRAG ingests and deletes take a per-workspace gate keyed on
``<store_root>/<workspace>/hipporag-write``, acquired before any store is built. A second HippoRAG
writer waits and is refused with ``StoreBusyError(store_kind="corpus")`` only when its wait ceiling
runs out; LightRAG's refuse-at-once gate (LRAG-04) is a different key and is unchanged.
"""

from __future__ import annotations

import asyncio
import time

from databasise.clients.base import EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam import Databasise
from databasise.seam.corpus import IngestDocument, IngestJob
from databasise.seam.refusals import StoreBusyError
from databasise.seam.selectors import Selector
from seam.test_hipporag_write_path import (
    _DOCUMENT_TEXT,
    _HIPPORAG_CAPABILITY,
    _StubEmbeddingClient,
    _StubIngestQueryLLMClient,
)

_SELECTOR = Selector(capability=_HIPPORAG_CAPABILITY)
_WORKSPACE = "hipporag-write-gate-ws"


class _IntervalRecordingEmbedding(_StubEmbeddingClient):
    """Sleeps inside every embed call and records its (start, end), so two ingests whose store
    phases overlap in time show overlapping intervals."""

    def __init__(self) -> None:
        super().__init__()
        self.intervals: list[tuple[float, float]] = []

    async def embed(self, texts, **kwargs):
        start = time.monotonic()
        await asyncio.sleep(0.05)
        result = await super().embed(texts, **kwargs)
        self.intervals.append((start, time.monotonic()))
        return result


def _engine(store_root, embedding=None) -> Databasise:
    return Databasise(
        store_root=store_root,
        workspace=_WORKSPACE,
        clients={"embedding": embedding or _StubEmbeddingClient(), "llm": _StubIngestQueryLLMClient()},
    )


def _document(document_id: str) -> IngestDocument:
    return IngestDocument(document_id=document_id, text=_DOCUMENT_TEXT + f" ({document_id})")


async def test_two_hipporag_ingests_on_one_workspace_never_run_their_store_phases_at_once(store_root):
    embedding = _IntervalRecordingEmbedding()
    engine = _engine(store_root, embedding)

    first, second = await asyncio.gather(
        engine.ingest(_document("gate-a"), selector=_SELECTOR),
        engine.ingest(_document("gate-b"), selector=_SELECTOR),
    )

    assert isinstance(first, IngestJob) and isinstance(second, IngestJob)
    intervals = sorted(embedding.intervals)
    assert len(intervals) >= 4
    overlaps = [(a, b) for a, b in zip(intervals, intervals[1:]) if b[0] < a[1]]
    assert overlaps == []


async def test_a_waiter_past_the_ceiling_is_refused_with_a_409_and_builds_no_store(store_root, monkeypatch):
    import databasise.seam.engine as engine_module

    monkeypatch.setattr(engine_module, "_HIPPORAG_GATE_WAIT_SECONDS", 0.1, raising=False)
    engine = _engine(store_root)
    gate = engine_module._gate_for(store_root / _WORKSPACE / "hipporag-write")
    assert gate.acquire(blocking=False)
    caught: BaseException | None = None
    try:
        await engine.ingest(_document("gate-held"), selector=_SELECTOR)
    except BaseException as exc:  # noqa: BLE001 - asserted on below
        caught = exc
    finally:
        gate.release()

    assert isinstance(caught, StoreBusyError), repr(caught)
    assert caught.store_kind == "corpus"
    workspace_dir = store_root / _WORKSPACE
    built = [p.name for p in workspace_dir.iterdir()] if workspace_dir.exists() else []
    assert not [name for name in built if name.startswith("hipporag-")], built


async def test_a_hipporag_delete_gathered_with_an_ingest_of_another_document_waits_and_both_complete(
    store_root,
):
    engine = _engine(store_root, _IntervalRecordingEmbedding())
    await engine.ingest(_document("gate-old"), selector=_SELECTOR)

    deleted, ingested = await asyncio.gather(
        engine.delete_document("gate-old", selector=_SELECTOR),
        engine.ingest(_document("gate-new"), selector=_SELECTOR),
    )

    assert deleted.status == "success"
    assert isinstance(ingested, IngestJob)
    assert (await engine.delete_document("gate-old", selector=_SELECTOR)).status == "not_found"
    assert (await engine.delete_document("gate-new", selector=_SELECTOR)).status == "success"


async def test_a_held_lightrag_v1_gate_does_not_delay_a_hipporag_ingest(store_root):
    import databasise.seam.engine as engine_module

    engine = _engine(store_root)
    gate = engine_module._gate_for(engine._v1_working_dir())
    assert gate.acquire(blocking=False)
    try:
        job = await asyncio.wait_for(engine.ingest(_document("gate-v1"), selector=_SELECTOR), timeout=30)
    finally:
        gate.release()

    assert isinstance(job, IngestJob)
