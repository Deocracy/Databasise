"""Tests for ``databasise.stores.vector.FaissVectorStore`` (plan 01-06, Task 3).

Covers the <behavior> claims: nearest-neighbour ordering, raise-before-mutation on a mismatched
embedding count, the index+sidecar two-phase commit, namespace isolation, an empty-index query,
deletion consistency, durability across reopen, and the no-fallback-vector-store guarantee.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import pytest
from databasise.stores.vector import FaissVectorStore, VectorStoreCorruptedError


def _vec(*values: float) -> list[float]:
    return list(values)


async def test_upsert_and_query_returns_nearest_neighbours_descending_with_stable_ties(
    store_root,
):
    store = FaissVectorStore(namespace="vec", workspace="ws", store_root=store_root)
    await store.upsert(
        ids=["a", "b", "c"],
        embeddings=[_vec(1.0, 0.0), _vec(0.0, 1.0), _vec(1.0, 0.0)],
        metadatas=[{"text": "a"}, {"text": "b"}, {"text": "c"}],
    )
    await store.index_done_callback()

    results = await store.query(_vec(1.0, 0.0), top_k=3)

    assert [r["id"] for r in results] == ["a", "c", "b"]
    assert results[0]["score"] >= results[1]["score"] >= results[2]["score"]
    # Stable tie-break: "a" and "c" score identically, ordered by id ascending.
    assert results[0]["id"] == "a"
    assert results[1]["id"] == "c"


async def test_upsert_raises_on_embedding_count_mismatch_and_buffer_stays_intact(store_root):
    store = FaissVectorStore(namespace="vec", workspace="ws", store_root=store_root)
    await store.upsert(ids=["a"], embeddings=[_vec(1.0, 0.0)])
    pending_before = dict(store._pending)

    with pytest.raises(ValueError, match="does not match"):
        await store.upsert(ids=["b", "c"], embeddings=[_vec(0.0, 1.0)])

    assert store._pending == pending_before
    assert len(store._pending) == 1


def test_no_fallback_vector_store_import_failure_names_faiss():
    """With ``faiss`` unavailable, importing the adapter raises an error naming Faiss and no
    other vector-store class is instantiated. Run in a subprocess — faiss's SWIG wrapper
    monkeypatches its own C-extension classes at import time, so forcing a second faiss import
    inside this test's own process would corrupt every faiss object already alive here.
    """
    script = textwrap.dedent(
        """
        import sys
        sys.modules["faiss"] = None
        import importlib
        try:
            importlib.import_module("databasise.stores.vector")
        except ImportError as exc:
            assert "faiss" in str(exc).lower()
            print("OK")
        else:
            print("NO_RAISE")
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert result.stdout.strip() == "OK"


async def test_index_and_sidecar_commit_together_or_neither(store_root, monkeypatch):
    store = FaissVectorStore(namespace="vec", workspace="ws", store_root=store_root)
    await store.upsert(ids=["a"], embeddings=[_vec(1.0, 0.0)])
    await store.index_done_callback()
    index_bytes_before = store._index_path.read_bytes()
    meta_bytes_before = store._meta_path.read_bytes()

    await store.upsert(ids=["b"], embeddings=[_vec(0.0, 1.0)])

    tmp_meta = store._meta_path.with_suffix(store._meta_path.suffix + ".tmp")
    real_open = Path.open

    def _open_patched(self: Path, *args: object, **kwargs: object):
        if self == tmp_meta and args and args[0] == "w":
            raise OSError("simulated sidecar write failure")
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", _open_patched)

    with pytest.raises(OSError, match="simulated sidecar write failure"):
        await store.index_done_callback()

    monkeypatch.undo()

    # Neither file was replaced: both still equal their pre-failure committed bytes.
    assert store._index_path.read_bytes() == index_bytes_before
    assert store._meta_path.read_bytes() == meta_bytes_before
    # No temp files left behind.
    assert not list(store._dir.glob("*.tmp"))
    # The pending buffer is untouched by the failed flush.
    assert "b" in store._pending


async def test_a_half_committed_pair_is_detected_and_refused_at_next_open(store_root):
    """WR-02 regression: the two ``os.replace`` calls in ``_persist`` are not one transaction, so
    a crash landing between them can leave a *new* index paired with a *stale* sidecar (or vice
    versa). Simulated here directly by writing an index file that does not match the checksum its
    own sidecar records — before the fix, reopening this pair would silently succeed with a
    corrupted store; after the fix, ``__init__`` refuses it by name.
    """
    store = FaissVectorStore(namespace="vec", workspace="ws", store_root=store_root)
    await store.upsert(ids=["a"], embeddings=[_vec(1.0, 0.0)])
    await store.index_done_callback()

    # Simulate the crash window: overwrite the committed index with different bytes (as a second
    # commit's index-write would, mid-flush) without updating the sidecar's checksum to match.
    store._index_path.write_bytes(store._index_path.read_bytes() + b"\x00")

    with pytest.raises(VectorStoreCorruptedError):
        FaissVectorStore(namespace="vec", workspace="ws", store_root=store_root)


async def test_two_namespaces_are_disjoint_and_both_files_present_after_commit(store_root):
    store_a = FaissVectorStore(namespace="vec-a", workspace="ws", store_root=store_root)
    store_b = FaissVectorStore(namespace="vec-b", workspace="ws", store_root=store_root)

    await store_a.upsert(ids=["a"], embeddings=[_vec(1.0, 0.0)])
    await store_a.index_done_callback()

    assert store_a._index_path.exists()
    assert store_a._meta_path.exists()
    assert store_a._index_path.parent == store_a._dir
    assert store_a._meta_path.parent == store_a._dir

    results_a = await store_a.query(_vec(1.0, 0.0))
    results_b = await store_b.query(_vec(1.0, 0.0))

    assert [r["id"] for r in results_a] == ["a"]
    assert results_b == []

    # All five lifecycle methods are present, per the shared StorageNameSpace ABC.
    for method in (
        "initialize",
        "finalize",
        "index_done_callback",
        "drop_pending_index_ops",
        "drop",
    ):
        assert callable(getattr(store_a, method))


async def test_query_on_empty_index_returns_empty_list_rather_than_raising(store_root):
    store = FaissVectorStore(namespace="vec", workspace="ws", store_root=store_root)

    results = await store.query(_vec(1.0, 0.0))

    assert results == []


async def test_delete_by_ids_removes_entries_and_stays_consistent(store_root):
    store = FaissVectorStore(namespace="vec", workspace="ws", store_root=store_root)
    await store.upsert(
        ids=["a", "b"],
        embeddings=[_vec(1.0, 0.0), _vec(0.0, 1.0)],
        metadatas=[{"text": "a"}, {"text": "b"}],
    )
    await store.index_done_callback()

    await store.delete_by_ids(["a"])

    results = await store.query(_vec(1.0, 0.0), top_k=5)
    assert [r["id"] for r in results] == ["b"]
    assert store._index_path.exists()
    assert store._meta_path.exists()
    assert "a" not in store._entries


async def test_reopening_store_from_directory_returns_same_results_after_commit(store_root):
    store = FaissVectorStore(namespace="vec", workspace="ws", store_root=store_root)
    await store.upsert(
        ids=["a", "b"],
        embeddings=[_vec(1.0, 0.0), _vec(0.0, 1.0)],
        metadatas=[{"text": "a"}, {"text": "b"}],
    )
    await store.index_done_callback()
    before = await store.query(_vec(1.0, 0.0), top_k=5)

    reopened = FaissVectorStore(namespace="vec", workspace="ws", store_root=store_root)
    after = await reopened.query(_vec(1.0, 0.0), top_k=5)

    assert before == after
    assert np.isclose(before[0]["score"], after[0]["score"])
