"""Phase 15 review-fix checks for the parity CLIs (15-REVIEW-ITER2-A.md, lane A iteration 2)."""

from __future__ import annotations

import asyncio
import json


def _v1_dir_with_one_chunk(tmp_path):
    v1_dir = tmp_path / "v1"
    v1_dir.mkdir()
    (v1_dir / "kv_store_text_chunks.json").write_text(json.dumps({"chunk-1": {"content": "text"}}), encoding="utf-8")
    return v1_dir


def _store_with_orphan_wal(tmp_path):
    from databasise.stores.kv import SqliteKVStore

    store_root = tmp_path / "store"
    store = SqliteKVStore(namespace="text_chunks", workspace="ws", store_root=store_root)
    asyncio.run(store.upsert({"chunk-1": {"content": "text"}}))
    asyncio.run(store.index_done_callback())
    asyncio.run(store.finalize())
    ns = store_root / "ws" / "text_chunks"
    (ns / "kv.sqlite3-shm").unlink(missing_ok=True)
    (ns / "kv.sqlite3-wal").write_bytes(b"\0" * 64)  # frames left behind by a copy that skipped -shm
    return store_root


def test_verify_import_refuses_a_wal_without_its_shm(tmp_path):
    """WR-01: an unreadable read-only KV is a precondition refusal, not an uncaught sqlite error."""
    from databasise.parity.import_index import verify_import

    store_root = _store_with_orphan_wal(tmp_path)
    result = asyncio.run(verify_import(_v1_dir_with_one_chunk(tmp_path), store_root, "ws"))
    assert result.status == "refused"
    assert [v.assertion for v in result.violations] == ["precondition"]
    assert "kv.sqlite3-shm is missing" in result.violations[0].detail
