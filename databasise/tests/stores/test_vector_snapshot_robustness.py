"""Phase 10 review WR-05 and WR-06: the shared committed-snapshot cache.

WR-05: ``load_committed`` retries a changing stat up to three times, treats a file that vanishes
between stat and read as a changed stat, returns a checksum-valid snapshot uncached rather than
calling a busy store corrupt, and turns every unreadable-sidecar failure into
``VectorStoreCorruptedError`` (so the seam maps it to ``StoreCorrupted``, never a 500).

WR-06: a record handed to a reader is a deep copy, so mutating it cannot reach another reader.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from databasise.seam.engine import Databasise
from databasise.seam.evidence import EvidenceRef
from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.stores import vector as vector_module
from databasise.stores.vector import FaissVectorStore, VectorStoreCorruptedError

_WS = "ws"


@pytest.fixture(autouse=True)
def _clear_snapshot_cache():
    vector_module._SNAPSHOT_CACHE.clear()
    yield
    vector_module._SNAPSHOT_CACHE.clear()


async def _commit(store_root: Path, metadata: dict | None = None) -> Path:
    store = FaissVectorStore("chunks", _WS, store_root)
    await store.upsert(["a", "b"], [[1.0, 0.0], [0.0, 1.0]], [metadata or {"content": "alpha"}, {"content": "beta"}])
    await store.index_done_callback()
    vector_module._SNAPSHOT_CACHE.clear()
    return store_root / _WS / "chunks"


def _bump_mtime(path: Path, step: int) -> None:
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + step))


# --------------------------------------------------------------------------------------------- #
# WR-05
# --------------------------------------------------------------------------------------------- #


async def test_a_valid_snapshot_is_returned_uncached_when_the_stat_keeps_changing(store_root, monkeypatch):
    directory = await _commit(store_root)
    real, reads = vector_module._read_snapshot, []

    def _read_then_touch(index_path, meta_path, signature):
        reads.append(1)
        snapshot = real(index_path, meta_path, signature)
        _bump_mtime(index_path, 1_000_000 * len(reads))
        return snapshot

    monkeypatch.setattr(vector_module, "_read_snapshot", _read_then_touch)

    snapshot = vector_module.load_committed(directory)

    assert set(snapshot.entries) == {"a", "b"}
    assert len(reads) == 3
    assert not vector_module._SNAPSHOT_CACHE


async def test_a_failed_validation_on_the_last_attempt_is_corruption(store_root, monkeypatch):
    directory = await _commit(store_root)
    meta = directory / "vector.meta.json"
    meta.write_text(meta.read_text().replace('"index_checksum": "', '"index_checksum": "0'))
    real = vector_module._read_snapshot

    def _read_then_touch(index_path, meta_path, signature):
        try:
            return real(index_path, meta_path, signature)
        finally:
            _bump_mtime(index_path, 7_000_000)

    monkeypatch.setattr(vector_module, "_read_snapshot", _read_then_touch)

    with pytest.raises(VectorStoreCorruptedError):
        vector_module.load_committed(directory)


async def test_a_file_that_vanishes_between_stat_and_read_is_retried(store_root, monkeypatch):
    directory = await _commit(store_root)
    real, calls = vector_module._read_snapshot, []

    def _vanish_once(index_path, meta_path, signature):
        calls.append(1)
        if len(calls) == 1:
            raise FileNotFoundError(str(meta_path))
        return real(index_path, meta_path, signature)

    monkeypatch.setattr(vector_module, "_read_snapshot", _vanish_once)

    assert set(vector_module.load_committed(directory).entries) == {"a", "b"}
    assert len(calls) == 2


async def test_a_file_that_keeps_vanishing_is_refused_as_corruption_not_absent(store_root, monkeypatch):
    # Iteration-2 WR-01: absent means BOTH stats showed both files missing. Returning None here made
    # prepare() rebuild the index from the pending buffer and replace the existing pair.
    directory = await _commit(store_root)

    def _always_vanish(index_path, meta_path, signature):
        raise FileNotFoundError(str(meta_path))

    monkeypatch.setattr(vector_module, "_read_snapshot", _always_vanish)

    with pytest.raises(VectorStoreCorruptedError):
        vector_module.load_committed(directory)


async def test_a_corruption_seen_on_an_earlier_attempt_survives_later_vanishes(store_root, monkeypatch):
    directory = await _commit(store_root)
    meta = directory / "vector.meta.json"
    meta.write_text(meta.read_text().replace('"index_checksum": "', '"index_checksum": "0'))
    real, calls = vector_module._read_snapshot, []

    def _corrupt_then_vanish(index_path, meta_path, signature):
        calls.append(1)
        if len(calls) > 1:
            raise FileNotFoundError(str(meta_path))
        try:
            return real(index_path, meta_path, signature)
        finally:
            _bump_mtime(index_path, 3_000_000)

    monkeypatch.setattr(vector_module, "_read_snapshot", _corrupt_then_vanish)

    with pytest.raises(VectorStoreCorruptedError) as exc_info:
        vector_module.load_committed(directory)

    assert len(calls) == 3
    assert not exc_info.value.actual.startswith("<"), "the checksum failure was replaced by a vanish"


@pytest.mark.parametrize("error", [PermissionError, NotADirectoryError])
async def test_an_unstatable_file_is_a_corrupted_store_not_a_raw_oserror(store_root, monkeypatch, error):
    directory = await _commit(store_root)
    real_stat = Path.stat

    def _deny(self, *args, **kwargs):
        if self.name == "vector.faiss":
            raise error(13, "denied")
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", _deny)

    with pytest.raises(VectorStoreCorruptedError):
        vector_module.load_committed(directory)


@pytest.mark.parametrize("garbage", ["not json at all", "{}", "[1, 2]"])
async def test_an_unreadable_sidecar_is_a_corrupted_store_not_a_raw_error(store_root, garbage):
    directory = await _commit(store_root)
    (directory / "vector.meta.json").write_text(garbage)

    with pytest.raises(VectorStoreCorruptedError):
        vector_module.load_committed(directory)


async def test_a_garbage_sidecar_reaches_the_seam_as_store_corrupted(store_root):
    directory = await _commit(store_root)
    (directory / "vector.meta.json").write_text("not json at all")
    engine = Databasise(store_root=store_root, workspace=_WS)

    with pytest.raises(ForeignEngineRefusalError) as exc_info:
        await engine.resolve_evidence(EvidenceRef(ref="a", namespace="chunks", kind="text_chunk"))

    assert exc_info.value.failure_class == "StoreCorrupted"


# --------------------------------------------------------------------------------------------- #
# WR-06
# --------------------------------------------------------------------------------------------- #


async def test_mutating_a_returned_record_cannot_reach_another_reader(store_root):
    await _commit(store_root, {"content": "alpha", "tags": [1], "nested": {"k": [1]}})
    first, second = FaissVectorStore("chunks", _WS, store_root), FaissVectorStore("chunks", _WS, store_root)

    record = first.get_by_id("a")
    record["tags"].append(99)
    record["nested"]["k"].append(99)
    for results in (
        await first.query([1.0, 0.0], top_k=2),
        await first.score_all([1.0, 0.0]),
        (await first.self_knn(top_k=2))["b"],
    ):
        for item in results:
            if item["id"] == "a":
                item["tags"].append(98)
                item["nested"]["k"].append(98)

    untouched = second.get_by_id("a")
    assert untouched["tags"] == [1] and untouched["nested"] == {"k": [1]}
    assert (await second.query([1.0, 0.0], top_k=1))[0]["tags"] == [1]
