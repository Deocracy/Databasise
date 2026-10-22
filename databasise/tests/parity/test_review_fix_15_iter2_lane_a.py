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


def test_import_index_refuses_a_locked_v1_graph_by_name(tmp_path, capsys):
    """WR-02: a v1 Cozo graph whose RocksDB lock is held elsewhere is one stderr line and exit 1."""
    from pycozo.client import Client

    from databasise.parity import import_index

    v1_dir = _v1_dir_with_one_chunk(tmp_path)
    holder = Client("rocksdb", str(v1_dir / "cozo_graph_chunk_entity_relation.db"), dataframe=False)
    try:
        (tmp_path / "store" / "ws").mkdir(parents=True)
        argv = ["--verify", "--store-root", str(tmp_path / "store"), "--workspace", "ws", "--v1-working-dir", str(v1_dir)]
        assert import_index.main(argv) == 1
    finally:
        holder.close()
    err = capsys.readouterr().err.strip()
    assert err.startswith("V1IndexLockedError: ") and "\n" not in err


def test_import_index_exits_3_on_an_inconclusive_verification(tmp_path, capsys):
    """WR-05: a comparison that ran and found a chunk-text difference is D-03's inconclusive, exit 3."""
    from databasise.parity import import_index

    (tmp_path / "store" / "ws").mkdir(parents=True)
    argv = ["--verify", "--store-root", str(tmp_path / "store"), "--workspace", "ws",
            "--v1-working-dir", str(_v1_dir_with_one_chunk(tmp_path))]
    assert import_index.main(argv) == 3
    out = capsys.readouterr()
    assert "[inconclusive] chunk-text: " in out.out and out.err == ""


def test_import_index_refused_verification_is_one_stderr_line(tmp_path, capsys):
    """WR-05: a "refused" (precondition) verification prints one D-03 stderr line and exits 1."""
    from databasise.parity import import_index

    (tmp_path / "store" / "ws").mkdir(parents=True)
    argv = ["--verify", "--store-root", str(tmp_path / "store"), "--workspace", "ws",
            "--v1-working-dir", str(tmp_path / "no-such-v1")]
    assert import_index.main(argv) == 1
    out = capsys.readouterr()
    assert out.err.count("\n") == 1 and out.err.startswith("ImportPreconditionError: no v1 index found at ")
    assert "[refused]" not in out.out
