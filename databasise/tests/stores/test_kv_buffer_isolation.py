"""STOR-11: ``SqliteKVStore`` keeps its pending buffer separate from callers, and ``is_empty``
counts pending deletes.
"""

from __future__ import annotations

from pathlib import Path

from databasise.stores.kv import SqliteKVStore


def _open(tmp_path: Path) -> SqliteKVStore:
    return SqliteKVStore(namespace="ns", workspace="ws", store_root=tmp_path)


async def _reopened_value(tmp_path: Path, store: SqliteKVStore):
    await store.index_done_callback()
    await store.finalize()
    reopened = _open(tmp_path)
    value = await reopened.get_by_id("a")
    await reopened.finalize()
    return value


async def test_mutating_a_read_does_not_change_the_buffered_record(tmp_path: Path):
    store = _open(tmp_path)
    await store.upsert({"a": {"v": 1}})

    record = await store.get_by_id("a")
    record["v"] = 2

    assert (await store.get_by_id("a"))["v"] == 1
    assert (await _reopened_value(tmp_path, store))["v"] == 1


async def test_mutating_the_callers_dict_after_upsert_changes_nothing(tmp_path: Path):
    store = _open(tmp_path)
    data = {"v": 1}
    await store.upsert({"a": data})

    data["v"] = 3

    assert (await store.get_by_id("a"))["v"] == 1
    assert (await _reopened_value(tmp_path, store))["v"] == 1


async def test_nested_values_are_copied_too(tmp_path: Path):
    store = _open(tmp_path)
    await store.upsert({"a": {"xs": [1]}})

    (await store.get_by_id("a"))["xs"].append(2)
    (await store.get_by_ids(["a"]))[0]["xs"].append(3)

    assert (await store.get_by_id("a"))["xs"] == [1]
    await store.finalize()


async def test_is_empty_when_every_committed_row_is_pending_deletion(tmp_path: Path):
    store = _open(tmp_path)
    await store.upsert({"a": {"v": 1}})
    await store.index_done_callback()
    assert await store.is_empty() is False

    await store.delete(["a"])

    assert await store.is_empty() is True
    await store.finalize()


async def test_is_not_empty_while_a_committed_row_survives(tmp_path: Path):
    store = _open(tmp_path)
    await store.upsert({"a": {"v": 1}, "b": {"v": 2}})
    await store.index_done_callback()

    await store.delete(["a"])

    assert await store.is_empty() is False
    await store.finalize()


async def test_is_empty_on_an_empty_store_and_not_with_a_pending_upsert(tmp_path: Path):
    store = _open(tmp_path)
    assert await store.is_empty() is True

    await store.upsert({"a": {"v": 1}})

    assert await store.is_empty() is False
    await store.finalize()
