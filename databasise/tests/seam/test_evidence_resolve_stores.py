"""10-06-PLAN.md Task 1 (STOR-03, D-05): ``/evidence/resolve`` opens only the named vector namespace
and reads the committed Faiss snapshot through a process-level cache keyed on both files' stat
signatures, so N resolves read and hash the index once until it changes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from databasise.seam.engine import Databasise
from databasise.seam.evidence import EvidenceRef
from databasise.stores import vector as vector_module
from databasise.stores.graph import CozoGraphStore
from databasise.stores.vector import FaissVectorStore
from databasise.tests.stores.test_graph_lock import hold_graph_in_subprocess

_WS = "ws"
_C1 = EvidenceRef(ref="c1", namespace="chunks", kind="text_chunk")
_C2 = EvidenceRef(ref="c2", namespace="chunks", kind="text_chunk")


@pytest.fixture(autouse=True)
def _clear_snapshot_cache():
    cache = getattr(vector_module, "_SNAPSHOT_CACHE", None)
    if cache is not None:
        cache.clear()
    yield
    if cache is not None:
        cache.clear()


@pytest.fixture
async def chunks_only_root(store_root: Path) -> Path:
    store = FaissVectorStore("chunks", _WS, store_root)
    await store.upsert(["c1"], [[1.0, 0.0, 0.0]], [{"content": "alpha"}])
    await store.index_done_callback()
    return store_root


@pytest.fixture
def counters(monkeypatch):
    counts = {"read": 0, "hash": 0}
    real_read, real_hash = vector_module.faiss.read_index, vector_module._sha256_of

    def _read(*args, **kwargs):
        counts["read"] += 1
        return real_read(*args, **kwargs)

    def _hash(*args, **kwargs):
        counts["hash"] += 1
        return real_hash(*args, **kwargs)

    monkeypatch.setattr(vector_module.faiss, "read_index", _read)
    monkeypatch.setattr(vector_module, "_sha256_of", _hash)
    return counts


def _no_other_store(root: Path) -> None:
    names = {p.name for p in root.rglob("*")}
    assert not names & {"kv.sqlite3", "graph.cozo", "text_chunks", "chunk_entity_relation"}, names


async def test_resolve_returns_the_record_and_opens_nothing_but_the_vector_namespace(chunks_only_root):
    engine = Databasise(store_root=chunks_only_root, workspace=_WS)

    record = await engine.resolve_evidence(_C1)

    assert record == {"id": "c1", "content": "alpha"}
    _no_other_store(chunks_only_root)


def test_rest_resolve_returns_the_record_and_opens_nothing_else(chunks_only_root):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from databasise.seam.rest import create_app

    client = TestClient(create_app(store_root=chunks_only_root, workspace=_WS))
    response = client.post("/evidence/resolve", json=_C1.model_dump())

    assert response.status_code == 200
    assert response.json() == {"id": "c1", "content": "alpha"}
    _no_other_store(chunks_only_root)


async def test_resolve_succeeds_while_the_graph_is_held_in_process(chunks_only_root):
    held = CozoGraphStore("chunk_entity_relation", _WS, chunks_only_root)
    try:
        engine = Databasise(store_root=chunks_only_root, workspace=_WS)
        assert (await engine.resolve_evidence(_C1))["content"] == "alpha"
    finally:
        await held.finalize()


async def test_resolve_succeeds_while_another_process_holds_the_graph(chunks_only_root):
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from databasise.seam.rest import create_app

    with hold_graph_in_subprocess(chunks_only_root / _WS / "chunk_entity_relation" / "graph.cozo"):
        engine = Databasise(store_root=chunks_only_root, workspace=_WS)
        assert (await engine.resolve_evidence(_C1))["content"] == "alpha"
        client = TestClient(create_app(store_root=chunks_only_root, workspace=_WS))
        assert client.post("/evidence/resolve", json=_C1.model_dump()).status_code == 200


async def test_five_resolves_read_and_hash_the_index_once_until_it_changes(chunks_only_root, counters):
    engine = Databasise(store_root=chunks_only_root, workspace=_WS)

    for _ in range(5):
        assert (await engine.resolve_evidence(_C1))["content"] == "alpha"
    assert counters == {"read": 1, "hash": 1}

    writer = FaissVectorStore("chunks", _WS, chunks_only_root)
    await writer.upsert(["c2"], [[0.0, 1.0, 0.0]], [{"content": "beta"}])
    await writer.index_done_callback()

    assert await engine.resolve_evidence(_C2) == {"id": "c2", "content": "beta"}
    assert counters["read"] == 2
    assert (await engine.resolve_evidence(_C1))["content"] == "alpha"
    assert counters["read"] == 2


async def test_the_cached_snapshot_is_read_only_and_writers_keep_their_own_state(chunks_only_root):
    snapshot = vector_module.load_committed(chunks_only_root / _WS / "chunks")

    with pytest.raises(TypeError):
        snapshot.entries["x"] = {"int_id": 99, "metadata": {}}

    writer = FaissVectorStore("chunks", _WS, chunks_only_root)
    await writer.upsert(["c2"], [[0.0, 1.0, 0.0]], [{"content": "beta"}])
    await writer.index_done_callback()

    assert "c2" not in snapshot.entries
    assert snapshot.index.ntotal == 1
    fresh = vector_module.load_committed(chunks_only_root / _WS / "chunks")
    assert fresh is not snapshot and "c2" in fresh.entries


def test_load_committed_on_a_missing_directory_returns_none_and_creates_nothing(store_root):
    missing = store_root / _WS / "nope"

    assert vector_module.load_committed(missing) is None
    assert not missing.exists()
    assert not (store_root / _WS).exists()


async def test_the_cache_keeps_one_key_per_directory_and_stays_bounded(store_root):
    cache = vector_module._SNAPSHOT_CACHE
    for i in range(vector_module._SNAPSHOT_CACHE_SIZE + 3):
        store = FaissVectorStore(f"ns{i}", _WS, store_root)
        await store.upsert(["a"], [[1.0, 0.0]], [{"content": str(i)}])
        await store.index_done_callback()
        vector_module.load_committed(store_root / _WS / f"ns{i}")
    assert len(cache) == vector_module._SNAPSHOT_CACHE_SIZE

    cache.clear()
    store = FaissVectorStore("one", _WS, store_root)
    for i in range(3):
        await store.upsert([f"d{i}"], [[1.0, 0.0]], [{}])
        await store.index_done_callback()
        vector_module.load_committed(store_root / _WS / "one")
    assert len(cache) == 1
