"""12-09-PLAN.md Task 2 (D-13, HIPP-15, LRAG-13): ``list_kv_prefix`` lists a namespace's keys by
prefix in ascending order, counts them with one range query, and creates nothing."""

from __future__ import annotations

import sqlite3

from databasise.stores.kv import SqliteKVStore
from databasise.stores.probes import list_kv_prefix


def _files(path):
    return sorted(p.name for p in path.iterdir()) if path.exists() else None


async def test_a_missing_directory_lists_nothing_and_creates_nothing(tmp_path):
    missing = tmp_path / "ws" / "hipporag-text-chunks"

    assert list_kv_prefix(missing, "doc:", limit=10, offset=0) == ([], 0)
    assert not (tmp_path / "ws").exists()


async def test_prefix_adjacent_keys_are_listed_once_in_order_and_other_keys_never(store_root):
    store = SqliteKVStore("ns", "ws", store_root)
    await store.upsert(
        {
            "doc:b": {"n": 3},
            "doc:a": {"n": 1},
            "doc:ab": {"n": 2},
            "fact:x": {"n": 9},
            "doc": {"n": 8},
            "doc;": {"n": 7},
        }
    )
    await store.index_done_callback()
    directory = store_root / "ws" / "ns"
    before = _files(directory)

    rows, total = list_kv_prefix(directory, "doc:", limit=10, offset=0)

    assert [(key, value["n"]) for key, value in rows] == [("doc:a", 1), ("doc:ab", 2), ("doc:b", 3)]
    assert total == 3
    page, total = list_kv_prefix(directory, "doc:", limit=1, offset=1)
    assert [key for key, _ in page] == ["doc:ab"] and total == 3
    assert list_kv_prefix(directory, "doc:", limit=5, offset=3) == ([], 3)
    assert _files(directory) == before  # a read adds no file, -wal and -shm included


def test_a_plain_database_without_a_wal_is_read_and_left_untouched(tmp_path):
    directory = tmp_path / "ns"
    directory.mkdir()
    conn = sqlite3.connect(directory / "kv.sqlite3")
    conn.execute("CREATE TABLE kv (id TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO kv VALUES ('doc:z', '{\"n\": 5}')")
    conn.commit()
    conn.close()
    before = _files(directory)

    assert list_kv_prefix(directory, "doc:", limit=10, offset=0) == ([("doc:z", {"n": 5})], 1)
    assert _files(directory) == before


def test_a_database_with_no_kv_table_lists_nothing(tmp_path):
    directory = tmp_path / "ns"
    directory.mkdir()
    sqlite3.connect(directory / "kv.sqlite3").execute("CREATE TABLE other (x INTEGER)").connection.close()

    assert list_kv_prefix(directory, "doc:", limit=10, offset=0) == ([], 0)
