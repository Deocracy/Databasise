"""10-05-PLAN.md (STOR-06, D-07): each store stages a run's writes at ``prepare()`` without
committing them, makes them visible at ``commit_prepared()``, and leaves nothing at
``abort_prepared()``. ``index_done_callback`` stays prepare plus commit in one call.
"""

from __future__ import annotations

import sqlite3

from databasise.stores.kv import SqliteKVStore


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
