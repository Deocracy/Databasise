"""10-05-PLAN.md (STOR-06, D-07): each store stages a run's writes at ``prepare()`` without
committing them, makes them visible at ``commit_prepared()``, and leaves nothing at
``abort_prepared()``. ``index_done_callback`` stays prepare plus commit in one call.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore, MultiNamespaceVectorStore


def _committed_kv_ids(db_path) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {row[0] for row in conn.execute("SELECT id FROM kv")}
    finally:
        conn.close()


# --------------------------------------------------------------------------------------------- #
# kv: an uncommitted sqlite transaction.
# --------------------------------------------------------------------------------------------- #


async def test_kv_prepare_stages_rows_a_second_connection_cannot_see_until_commit(store_root):
    store = SqliteKVStore("ns", "ws", store_root)
    try:
        await store.upsert({"a": {"v": 1}})
        await store.prepare()

        assert "a" not in _committed_kv_ids(store._db_path)

        await store.commit_prepared()

        assert "a" in _committed_kv_ids(store._db_path)
        assert store._pending_upserts == {}
    finally:
        await store.finalize()


async def test_kv_abort_prepared_rolls_back_and_the_row_never_appears(store_root):
    store = SqliteKVStore("ns", "ws", store_root)
    await store.upsert({"b": {"v": 2}})
    await store.prepare()
    await store.abort_prepared()
    assert store._pending_upserts == {}
    await store.finalize()

    reopened = SqliteKVStore("ns", "ws", store_root)
    try:
        assert await reopened.get_by_id("b") is None
    finally:
        await reopened.finalize()


async def test_kv_index_done_callback_still_commits_in_one_call(store_root):
    store = SqliteKVStore("ns", "ws", store_root)
    try:
        await store.upsert({"c": {"v": 3}})
        await store.delete(["gone"])
        await store.index_done_callback()

        assert _committed_kv_ids(store._db_path) == {"c"}
        assert store._pending_upserts == {}
        assert store._pending_deletes == set()
    finally:
        await store.finalize()


# --------------------------------------------------------------------------------------------- #
# vector: the .tmp file pair; prepare rebases on the on-disk committed state.
# --------------------------------------------------------------------------------------------- #


def _tmp_pair(store: FaissVectorStore) -> list[Path]:
    return [p.with_suffix(p.suffix + ".tmp") for p in (store._index_path, store._meta_path)]


async def test_vector_prepare_writes_only_the_tmp_pair_on_a_fresh_namespace(store_root):
    store = FaissVectorStore("vec", "ws", store_root)
    await store.upsert(ids=["a"], embeddings=[[1.0, 0.0]])
    await store.prepare()

    assert not store._index_path.exists()
    assert not store._meta_path.exists()
    assert all(p.exists() for p in _tmp_pair(store))

    await store.commit_prepared()

    assert not list(store._dir.glob("*.tmp"))
    assert store._pending == {}
    assert FaissVectorStore("vec", "ws", store_root).get_by_id("a") == {"id": "a"}


async def test_vector_prepare_keeps_the_committed_bytes_until_commit(store_root):
    store = FaissVectorStore("vec", "ws", store_root)
    await store.upsert(ids=["a"], embeddings=[[1.0, 0.0]])
    await store.index_done_callback()
    index_before = store._index_path.read_bytes()
    meta_before = store._meta_path.read_bytes()

    await store.upsert(ids=["b"], embeddings=[[0.0, 1.0]])
    await store.prepare()

    assert store._index_path.read_bytes() == index_before
    assert store._meta_path.read_bytes() == meta_before
    assert FaissVectorStore("vec", "ws", store_root).get_by_id("b") is None

    await store.commit_prepared()

    assert FaissVectorStore("vec", "ws", store_root).get_by_id("b") == {"id": "b"}


async def test_vector_abort_prepared_removes_the_tmp_pair_and_commits_nothing(store_root):
    store = FaissVectorStore("vec", "ws", store_root)
    await store.upsert(ids=["a"], embeddings=[[1.0, 0.0]])
    await store.prepare()
    await store.abort_prepared()

    assert not list(store._dir.glob("*.tmp"))
    assert store._pending == {}
    assert store.get_by_id("a") is None
    assert FaissVectorStore("vec", "ws", store_root).get_by_id("a") is None


async def test_two_vector_instances_opened_before_either_flushes_keep_both_ids(store_root):
    store_a = FaissVectorStore("vec", "ws", store_root)
    store_b = FaissVectorStore("vec", "ws", store_root)

    await store_a.upsert(ids=["a"], embeddings=[[1.0, 0.0]])
    await store_a.index_done_callback()
    await store_b.upsert(ids=["b"], embeddings=[[0.0, 1.0]])
    await store_b.index_done_callback()

    reopened = FaissVectorStore("vec", "ws", store_root)
    assert reopened.get_by_id("a") == {"id": "a"}
    assert reopened.get_by_id("b") == {"id": "b"}
    assert reopened._entries["a"]["int_id"] != reopened._entries["b"]["int_id"]


async def test_multi_namespace_vector_lifecycle_fans_out_to_every_selected_child(store_root):
    multi = MultiNamespaceVectorStore("ws", store_root)
    await multi.select("one").upsert(ids=["a"], embeddings=[[1.0, 0.0]])
    await multi.select("two").upsert(ids=["b"], embeddings=[[0.0, 1.0]])

    await multi.prepare()
    assert all(p.exists() for name in ("one", "two") for p in _tmp_pair(multi.select(name)))
    await multi.commit_prepared()

    assert FaissVectorStore("one", "ws", store_root).get_by_id("a") == {"id": "a"}
    assert FaissVectorStore("two", "ws", store_root).get_by_id("b") == {"id": "b"}

    await multi.select("one").upsert(ids=["c"], embeddings=[[1.0, 1.0]])
    await multi.select("two").upsert(ids=["d"], embeddings=[[1.0, 1.0]])
    await multi.prepare()
    await multi.abort_prepared()

    for name, doc_id in (("one", "c"), ("two", "d")):
        assert not list(multi.select(name)._dir.glob("*.tmp"))
        assert FaissVectorStore(name, "ws", store_root).get_by_id(doc_id) is None


# --------------------------------------------------------------------------------------------- #
# graph: a staged multi_transact.
# --------------------------------------------------------------------------------------------- #


async def test_graph_prepare_stages_a_node_another_instance_cannot_see_until_commit(store_root):
    s1 = CozoGraphStore("graph", "ws", store_root)
    s2 = CozoGraphStore("graph", "ws", store_root)
    try:
        await s1.upsert_node("n", {})
        await s1.prepare()

        assert await s2.has_node("n") is False

        await s1.commit_prepared()

        assert await s2.has_node("n") is True
        assert s1._pending_node_puts == {}
    finally:
        await s1.finalize()
        await s2.finalize()


async def test_graph_abort_prepared_leaves_nothing(store_root):
    store = CozoGraphStore("graph", "ws", store_root)
    try:
        await store.upsert_node("n", {})
        await store.prepare()
        await store.abort_prepared()

        assert store._pending_node_puts == {}
        assert await store.has_node("n") is False
    finally:
        await store.finalize()


async def test_graph_finalize_while_prepared_aborts_first_and_raises_nothing(store_root):
    store = CozoGraphStore("graph", "ws", store_root)
    await store.upsert_node("n", {})
    await store.prepare()
    await store.finalize()

    reopened = CozoGraphStore("graph", "ws", store_root)
    try:
        assert await reopened.has_node("n") is False
    finally:
        await reopened.finalize()
