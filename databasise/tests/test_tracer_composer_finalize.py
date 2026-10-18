"""Iteration-2 IN-03: the tracer composer (``databasise.run_wiring``) finalizes its kv store on every
exit, including a scheduler failure, so no sqlite connection waits for garbage collection."""

from __future__ import annotations

import pytest

import databasise
from databasise.stores.kv import SqliteKVStore


async def test_the_kv_store_is_finalized_when_the_scheduler_raises(store_root, monkeypatch):
    finalized = []
    real_finalize = SqliteKVStore.finalize

    async def _spy(self):
        finalized.append(self)
        await real_finalize(self)

    async def _boom(*_args, **_kwargs):
        raise RuntimeError("scheduler failure")

    monkeypatch.setattr(SqliteKVStore, "finalize", _spy)
    monkeypatch.setattr(databasise, "parse_wiring", lambda *_a, **_k: None)
    monkeypatch.setattr(databasise._scheduler, "run_wiring", _boom)

    with pytest.raises(RuntimeError, match="scheduler failure"):
        await databasise.run_wiring(
            {}, store_root=store_root, determinism_setting="a", concurrency_setting="b"
        )

    assert len(finalized) == 1
