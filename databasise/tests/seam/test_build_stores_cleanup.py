"""10-01-PLAN.md Task 3 (STOR-02, D-04): a failed store open finalizes every store already opened
in that call, in the engine and in ``parity.run_arm``. No sqlite connection is left open."""

from __future__ import annotations

import pytest

from databasise.seam.corpus import IngestDocument
from databasise.seam.engine import Databasise
from databasise.seam.evidence import EvidenceRef
from databasise.seam.query import QueryObject
from databasise.stores import graph as graph_module
from databasise.stores import kv as kv_module


@pytest.fixture
def kv_counts(monkeypatch):
    """Graph open always fails; counts SqliteKVStore constructions and finalizations."""
    counts = {"built": 0, "finalized": 0}
    real_init = kv_module.SqliteKVStore.__init__
    real_finalize = kv_module.SqliteKVStore.finalize

    def counting_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        counts["built"] += 1

    async def counting_finalize(self):
        counts["finalized"] += 1
        await real_finalize(self)

    def failing_graph_init(self, *args, **kwargs):
        raise RuntimeError("graph open failed")

    monkeypatch.setattr(kv_module.SqliteKVStore, "__init__", counting_init)
    monkeypatch.setattr(kv_module.SqliteKVStore, "finalize", counting_finalize)
    monkeypatch.setattr(graph_module.CozoGraphStore, "__init__", failing_graph_init)
    return counts


async def test_query_finalizes_the_kv_store_when_the_graph_open_fails(store_root, kv_counts):
    engine = Databasise(store_root=store_root, workspace="ws")
    with pytest.raises(RuntimeError, match="graph open failed"):
        await engine.query(QueryObject(text="x"))
    assert kv_counts == {"built": 1, "finalized": 1}


async def test_ingest_finalizes_the_kv_store_and_stages_nothing(store_root, kv_counts):
    engine = Databasise(store_root=store_root, workspace="ws")
    with pytest.raises(RuntimeError, match="graph open failed"):
        await engine.ingest(IngestDocument(document_id="doc-a", text="hello"))
    assert kv_counts == {"built": 1, "finalized": 1}
    inbox = store_root / "corpus-inbox"
    assert not inbox.exists() or not any(inbox.iterdir())


async def test_delete_document_finalizes_the_kv_store(store_root, kv_counts):
    engine = Databasise(store_root=store_root, workspace="ws")
    with pytest.raises(RuntimeError, match="graph open failed"):
        await engine.delete_document("doc-a")
    assert kv_counts == {"built": 1, "finalized": 1}


async def test_resolve_evidence_opens_no_kv_store(synthetic_naive_store, kv_counts):
    engine = Databasise(
        store_root=synthetic_naive_store["store_root"], workspace=synthetic_naive_store["workspace"]
    )
    record = await engine.resolve_evidence(
        EvidenceRef(ref="chunk-1", namespace="chunks", kind="text_chunk")
    )
    assert record is not None
    assert kv_counts["built"] == 0


async def test_three_failing_queries_finalize_every_kv_store(store_root, kv_counts):
    engine = Databasise(store_root=store_root, workspace="ws")
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await engine.query(QueryObject(text="x"))
    assert kv_counts == {"built": 3, "finalized": 3}


async def test_run_arm_finalizes_the_kv_store_when_the_graph_open_fails(store_root, kv_counts):
    from databasise.parity.run_arm import run_arm

    with pytest.raises(RuntimeError, match="graph open failed"):
        await run_arm("naive", "x", store_root=store_root, workspace="ws", clients={})
    assert kv_counts == {"built": 1, "finalized": 1}
