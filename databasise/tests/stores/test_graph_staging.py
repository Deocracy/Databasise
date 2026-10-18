"""Phase 10 review WR-10: the graph store stages inside ``prepare`` and commits only in
``commit_prepared``. These tests fail against a no-op ``prepare``, and against a ``commit_prepared``
that flushes the buffers instead of committing a staged transaction (both were verified to pass the
earlier tests unchanged)."""

from __future__ import annotations

import pytest

from databasise.stores.graph import CozoGraphStore


@pytest.fixture
async def pair(store_root):
    writer = CozoGraphStore("graph", "ws", store_root)
    reader = CozoGraphStore("graph", "ws", store_root)  # a second reader on the same path
    yield writer, reader
    await writer.finalize()
    await reader.finalize()


async def test_prepare_holds_a_staged_transaction_that_commit_needs_no_buffer_for(pair):
    writer, reader = pair
    await writer.upsert_node("n", {"k": 1})
    await writer.upsert_edge("n", "m", {"w": 2})

    await writer.prepare()

    assert writer._prepared_mt is not None
    assert await reader.has_node("n") is False  # staged, not committed
    # Everything is already in the transaction: dropping the buffers must not lose the writes.
    writer._clear_pending()

    await writer.commit_prepared()

    assert writer._prepared_mt is None
    assert await reader.get_node("n") == {"k": 1}
    assert await reader.has_edge("n", "m") is True


async def test_abort_prepared_after_a_real_prepare_commits_nothing(pair, store_root):
    writer, reader = pair
    await writer.upsert_node("n", {})
    await writer.prepare()
    assert writer._prepared_mt is not None
    assert await reader.has_node("n") is False

    await writer.abort_prepared()

    assert writer._prepared_mt is None
    assert await reader.has_node("n") is False
    await writer.finalize()
    reopened = CozoGraphStore("graph", "ws", store_root)
    try:
        assert await reopened.get_all_labels() == []
    finally:
        await reopened.finalize()


async def test_a_statement_that_cannot_be_staged_fails_at_prepare_not_at_commit(pair):
    writer, reader = pair
    await writer.upsert_node("ok", {})
    await writer.upsert_node("bad", {"unserializable": object()})

    with pytest.raises(Exception):
        await writer.prepare()

    assert writer._prepared_mt is None
    assert await reader.has_node("ok") is False
