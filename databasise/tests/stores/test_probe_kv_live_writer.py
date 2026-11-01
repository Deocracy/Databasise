"""Sweep (phase 10): ``probe_kv`` on a ``kv.sqlite3`` with a live writer must never report
``corrupted``. An ``immutable=1`` open takes no lock, so it can read a page the writer's WAL
checkpoint is rewriting and mistake the torn page for corruption, which made ``/health`` degraded
during an ingest. With both ``-wal`` and ``-shm`` present the probe opens plain ``mode=ro`` like
:func:`list_kv_prefix` does, which locks correctly and creates nothing."""

from __future__ import annotations

import threading
from pathlib import Path

from databasise.stores.kv import SqliteKVStore
from databasise.stores.probes import probe_kv


async def test_probe_kv_never_reports_corrupted_while_a_live_writer_checkpoints(tmp_path: Path):
    store = SqliteKVStore("t", "ws", tmp_path)
    store._conn.execute("PRAGMA wal_autocheckpoint=1")  # checkpoint on every commit, as a long ingest does
    directory = tmp_path / "ws" / "t"
    stop = threading.Event()
    seen: list[str] = []

    def probe_loop() -> None:
        while not stop.is_set():
            seen.append(probe_kv(directory))

    threads = [threading.Thread(target=probe_loop) for _ in range(4)]
    try:
        for t in threads:
            t.start()
        for i in range(300):
            await store.upsert({f"k{i}": {"v": "x" * 4096}})
            await store.index_done_callback()
    finally:
        stop.set()
        for t in threads:
            t.join()
        await store.finalize()

    assert seen and "corrupted" not in set(seen), sorted(set(seen))
    assert set(seen) <= {"ok", "busy"}
