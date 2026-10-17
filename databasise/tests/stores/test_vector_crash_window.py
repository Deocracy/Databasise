"""10-06-PLAN.md Task 2 (STOR-08, Q6): a Faiss namespace directory holding only one of its two files
is refused as ``VectorStoreCorruptedError`` instead of opening empty (which the next flush would
overwrite). Through the seam, ``resolve_evidence`` turns it into the ``StoreCorrupted`` fault (502),
never the 404 "record no longer present" refusal.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from databasise.seam.engine import Databasise
from databasise.seam.evidence import EvidenceRef
from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.stores import vector as vector_module
from databasise.stores.vector import FaissVectorStore, VectorStoreCorruptedError, load_committed

_WS = "ws"
_REF = EvidenceRef(ref="a", namespace="chunks", kind="text_chunk")


@pytest.fixture(autouse=True)
def _clear_snapshot_cache():
    vector_module._SNAPSHOT_CACHE.clear()
    yield
    vector_module._SNAPSHOT_CACHE.clear()


async def _flushed(store_root: Path) -> Path:
    store = FaissVectorStore("chunks", _WS, store_root)
    await store.upsert(["a"], [[1.0, 0.0]], [{"content": "alpha"}])
    await store.index_done_callback()
    return store_root / _WS / "chunks"


@pytest.fixture(params=["vector.meta.json", "vector.faiss"])
async def damaged(request, store_root) -> tuple[Path, str]:
    ns_dir = await _flushed(store_root)
    load_committed(ns_dir)  # a cached snapshot must not hide the damage
    (ns_dir / request.param).unlink()
    return ns_dir, request.param


async def test_opening_a_half_written_directory_raises_and_writes_nothing(damaged, store_root):
    ns_dir, missing = damaged
    survivor = next(ns_dir.iterdir())
    before = survivor.read_bytes()

    with pytest.raises(VectorStoreCorruptedError) as exc_info:
        FaissVectorStore("chunks", _WS, store_root)

    assert exc_info.value.expected is None
    assert exc_info.value.actual == f"<missing {missing}>"
    assert sorted(p.name for p in ns_dir.iterdir()) == [survivor.name]
    assert survivor.read_bytes() == before


async def test_load_committed_raises_on_a_half_written_directory(damaged):
    ns_dir, _missing = damaged
    with pytest.raises(VectorStoreCorruptedError):
        load_committed(ns_dir)


def test_load_committed_on_an_empty_directory_returns_none(store_root):
    (store_root / "empty").mkdir()
    assert load_committed(store_root / "empty") is None


async def test_resolve_on_a_damaged_namespace_is_the_store_corrupted_fault(damaged, store_root):
    engine = Databasise(store_root=store_root, workspace=_WS)

    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await engine.resolve_evidence(_REF)

    assert exc_info.value.failure_class == "StoreCorrupted"
    assert isinstance(exc_info.value.cause, VectorStoreCorruptedError)


async def test_rest_resolve_on_a_damaged_namespace_is_a_502_without_the_store_path(damaged, store_root):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from databasise.seam.rest import create_app

    client = TestClient(create_app(store_root=store_root, workspace=_WS))
    response = client.post("/evidence/resolve", json=_REF.model_dump())

    assert response.status_code == 502
    body = response.json()
    assert body["refusal_type"] == "ForeignEngineRefusalError"
    assert body["failure_class"] == "StoreCorrupted"
    assert str(store_root) not in response.text
    assert "vector.faiss" not in response.text and "vector.meta.json" not in response.text
