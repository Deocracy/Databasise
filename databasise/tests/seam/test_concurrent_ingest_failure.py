"""Phase 10 review WR-04: a failing ingest that drops its pending ops must not delete the staged
``.tmp`` files of a successful ingest that is between its prepare and its commit on the same
namespace. The vector store unlinks only what its own instance staged, and the engine drops under the
same flush lock that serializes prepare-to-commit."""

from __future__ import annotations

import asyncio

from databasise.seam import Databasise
from databasise.seam.corpus import IngestDocument, IngestJob
from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.seam.selectors import Selector
from databasise.stores.graph import CozoGraphStore
from databasise.stores.vector import FaissVectorStore
from seam.test_hipporag_write_path import (
    _DOCUMENT_TEXT,
    _HIPPORAG_CAPABILITY,
    _StubEmbeddingClient,
    _StubIngestQueryLLMClient,
    _WORKSPACE,
)


class _PoisonedDocumentLLM(_StubIngestQueryLLMClient):
    """Fails any call whose prompt carries the poison marker, half a second in."""

    async def chat(self, messages, **kwargs):
        if "POISON" in messages[0]["content"]:
            await asyncio.sleep(0.5)
            raise RuntimeError("poisoned document")
        return await super().chat(messages, **kwargs)


async def test_a_failing_ingest_does_not_destroy_a_concurrent_ingests_staged_vectors(store_root, monkeypatch):
    real_prepare = CozoGraphStore.prepare

    async def _slow_graph_prepare(self):
        # Holds the good ingest between its vector prepare and its commit while the bad one fails.
        await asyncio.sleep(1.2)
        await real_prepare(self)

    monkeypatch.setattr(CozoGraphStore, "prepare", _slow_graph_prepare)
    engine = Databasise(
        store_root=store_root,
        workspace=_WORKSPACE,
        clients={"embedding": _StubEmbeddingClient(), "llm": _PoisonedDocumentLLM()},
    )
    selector = Selector(capability=_HIPPORAG_CAPABILITY)

    good, bad = await asyncio.gather(
        engine.ingest(IngestDocument(document_id="good-doc", text=_DOCUMENT_TEXT), selector=selector),
        engine.ingest(IngestDocument(document_id="bad-doc", text="POISON " + _DOCUMENT_TEXT), selector=selector),
        return_exceptions=True,
    )
    monkeypatch.undo()

    assert isinstance(bad, ForeignEngineRefusalError)
    assert isinstance(good, IngestJob), good
    chunks = FaissVectorStore("hipporag-chunks", _WORKSPACE, store_root)
    try:
        assert list(chunks.iter_vectors())
    finally:
        await chunks.finalize()
    assert not list((store_root / _WORKSPACE).rglob("*.tmp"))


async def test_abort_prepared_leaves_a_pair_staged_by_another_instance(store_root):
    staging = FaissVectorStore("ns", "ws", store_root)
    await staging.upsert(["a"], [[1.0, 0.0]], [{"v": 1}])
    await staging.prepare()
    bystander = FaissVectorStore("ns", "ws", store_root)

    await bystander.drop_pending_index_ops()
    await staging.commit_prepared()  # the staged pair must still exist

    assert FaissVectorStore("ns", "ws", store_root).get_by_id("a") == {"id": "a", "v": 1}


async def test_abort_prepared_removes_the_pair_this_instance_staged(store_root):
    store = FaissVectorStore("ns", "ws", store_root)
    await store.upsert(["a"], [[1.0, 0.0]], [{"v": 1}])
    await store.prepare()
    assert list((store_root / "ws" / "ns").glob("*.tmp"))

    await store.abort_prepared()

    assert not list((store_root / "ws" / "ns").glob("*.tmp"))
