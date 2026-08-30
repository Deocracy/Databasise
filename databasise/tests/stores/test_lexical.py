"""Tests for databasise/stores/lexical.py: SqliteLexicalStore's FTS5 search and lifecycle.
One test per <behavior> claim in 01-05-PLAN.md's Task 2 (tests 8-12).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from databasise.stores.lexical import Fts5UnavailableError, SqliteLexicalStore


async def test_8_query_term_present_in_two_of_three_docs_returns_exactly_those_two_ranked(
    tmp_path: Path,
):
    store = SqliteLexicalStore(namespace="ns", workspace="ws", store_root=tmp_path)
    await store.upsert(
        {
            "doc1": {"content": "the quick brown fox"},
            "doc2": {"content": "a slow brown turtle"},
            "doc3": {"content": "nothing relevant here"},
        }
    )
    await store.index_done_callback()

    hits = await store.query("brown")

    ids = {hit["id"] for hit in hits}
    assert ids == {"doc1", "doc2"}
    assert "doc3" not in ids
    await store.finalize()


async def test_9_fts5_syntax_characters_in_query_term_are_treated_literally(tmp_path: Path):
    store = SqliteLexicalStore(namespace="ns", workspace="ws", store_root=tmp_path)
    await store.upsert({"doc1": {"content": "value AND OR NOT NEAR term"}})
    await store.index_done_callback()

    # A term containing FTS5 boolean/operator syntax must not raise and must not be parsed
    # as query structure — it is searched as a literal phrase.
    hits = await store.query('"quoted AND term"')

    assert hits == []
    await store.finalize()


async def test_10_empty_query_string_returns_empty_list_not_every_document(tmp_path: Path):
    store = SqliteLexicalStore(namespace="ns", workspace="ws", store_root=tmp_path)
    await store.upsert({"doc1": {"content": "some content"}})
    await store.index_done_callback()

    hits = await store.query("")

    assert hits == []
    await store.finalize()


async def test_11_lifecycle_buffered_until_flush_discarded_on_abort(tmp_path: Path):
    store = SqliteLexicalStore(namespace="ns", workspace="ws", store_root=tmp_path)
    await store.upsert({"doc1": {"content": "searchable text"}})

    # Not yet flushed — the FTS5 index has nothing committed.
    assert await store.query("searchable") == []

    await store.drop_pending_index_ops()
    await store.index_done_callback()  # flushing an empty buffer commits nothing

    assert await store.query("searchable") == []
    await store.finalize()


async def test_12_drop_removes_content_and_leaves_a_reusable_empty_store(tmp_path: Path):
    store = SqliteLexicalStore(namespace="ns", workspace="ws", store_root=tmp_path)
    await store.upsert({"doc1": {"content": "searchable text"}})
    await store.index_done_callback()
    assert await store.query("searchable") != []

    result = await store.drop()
    assert result["status"] == "success"
    assert await store.query("searchable") == []

    await store.upsert({"doc2": {"content": "fresh content"}})
    await store.index_done_callback()
    assert await store.query("fresh") != []
    await store.finalize()


class _NoFts5Connection:
    """Delegates to a real sqlite3.Connection, raising on any FTS5-referencing statement —
    simulates FTS5 being unavailable without touching the immutable ``sqlite3.Connection`` type
    (its ``execute`` slot cannot be monkeypatched directly on CPython).
    """

    def __init__(self, real_conn: sqlite3.Connection) -> None:
        self._real = real_conn

    def execute(self, sql, *args, **kwargs):
        if "fts5" in sql.lower():
            raise sqlite3.OperationalError("no such module: fts5")
        return self._real.execute(sql, *args, **kwargs)

    def commit(self):
        return self._real.commit()

    def close(self):
        return self._real.close()


def test_no_silent_fallback_when_fts5_is_unavailable(tmp_path: Path, monkeypatch):
    """Behaviourally verified (not by grepping for a fallback): with FTS5 monkeypatched to
    appear unavailable, constructing the lexical store raises an error naming FTS5, and no
    query executes.
    """
    real_connect = sqlite3.connect

    def fake_connect(*args, **kwargs):
        return _NoFts5Connection(real_connect(*args, **kwargs))

    monkeypatch.setattr(sqlite3, "connect", fake_connect)

    with pytest.raises(Fts5UnavailableError, match="FTS5"):
        SqliteLexicalStore(namespace="ns", workspace="ws", store_root=tmp_path)
