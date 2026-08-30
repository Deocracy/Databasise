"""Tests for databasise/stores/kv.py: SqliteKVStore's buffer/commit/abort discipline.
One test per <behavior> claim in 01-05-PLAN.md's Task 2 (tests 1-7).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from databasise.stores.kv import SqliteKVStore


async def test_1_upsert_then_get_by_id_before_flush_returns_buffered_value(tmp_path: Path):
    store = SqliteKVStore(namespace="ns", workspace="ws", store_root=tmp_path)
    await store.upsert({"a": {"v": 1}})

    value = await store.get_by_id("a")

    assert value == {"v": 1}
    await store.finalize()


async def test_2_upsert_then_abort_then_get_by_id_returns_none(tmp_path: Path):
    store = SqliteKVStore(namespace="ns", workspace="ws", store_root=tmp_path)
    await store.upsert({"a": {"v": 1}})
    await store.drop_pending_index_ops()

    value = await store.get_by_id("a")

    assert value is None
    await store.finalize()


async def test_3_upsert_commit_reopen_is_durable(tmp_path: Path):
    store = SqliteKVStore(namespace="ns", workspace="ws", store_root=tmp_path)
    await store.upsert({"a": {"v": 1}})
    await store.index_done_callback()
    await store.finalize()

    reopened = SqliteKVStore(namespace="ns", workspace="ws", store_root=tmp_path)
    value = await reopened.get_by_id("a")

    assert value == {"v": 1}
    await reopened.finalize()


async def test_4_filter_keys_returns_absent_keys_counting_buffered_as_present(tmp_path: Path):
    store = SqliteKVStore(namespace="ns", workspace="ws", store_root=tmp_path)
    await store.upsert({"buffered": {"v": 1}})

    absent = await store.filter_keys({"buffered", "missing"})

    assert absent == {"missing"}
    await store.finalize()


async def test_5_get_by_ids_empty_and_is_empty_semantics(tmp_path: Path):
    store = SqliteKVStore(namespace="ns", workspace="ws", store_root=tmp_path)

    assert await store.get_by_ids([]) == []
    assert await store.is_empty() is True

    await store.upsert({"a": {"v": 1}})

    assert await store.is_empty() is False
    await store.finalize()


class _FailNthInsertConnection:
    """Delegates to a real sqlite3.Connection, raising on the Nth ``INSERT INTO kv`` call —
    simulates a mid-flush write failure without touching the immutable ``sqlite3.Connection``
    type (its ``execute`` slot cannot be monkeypatched directly on CPython).
    """

    def __init__(self, real_conn: sqlite3.Connection, fail_on_call_n: int) -> None:
        self._real = real_conn
        self._fail_on = fail_on_call_n
        self._call_count = 0

    def execute(self, sql, *args, **kwargs):
        if sql.startswith("INSERT INTO kv"):
            self._call_count += 1
            if self._call_count == self._fail_on:
                raise sqlite3.OperationalError("simulated flush failure")
        return self._real.execute(sql, *args, **kwargs)

    def commit(self):
        return self._real.commit()

    def rollback(self):
        return self._real.rollback()

    def close(self):
        return self._real.close()


async def test_6_write_that_fails_mid_flush_raises_and_buffer_stays_intact(tmp_path: Path):
    store = SqliteKVStore(namespace="ns", workspace="ws", store_root=tmp_path)
    await store.upsert({"a": {"v": 1}, "b": {"v": 2}})

    store._conn = _FailNthInsertConnection(store._conn, fail_on_call_n=2)

    with pytest.raises(sqlite3.OperationalError):
        await store.index_done_callback()

    assert store._pending_upserts == {"a": {"v": 1}, "b": {"v": 2}}
    await store.finalize()


async def test_7_two_stores_on_different_namespace_dirs_do_not_see_each_others_keys(
    tmp_path: Path,
):
    store_a = SqliteKVStore(namespace="ns-a", workspace="ws", store_root=tmp_path)
    store_b = SqliteKVStore(namespace="ns-b", workspace="ws", store_root=tmp_path)

    await store_a.upsert({"key": {"v": "in-a"}})
    await store_a.index_done_callback()

    value_in_b = await store_b.get_by_id("key")

    assert value_in_b is None
    await store_a.finalize()
    await store_b.finalize()
