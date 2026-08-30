"""SQLite-backed KV store (D-06, D-07): one database file per namespace directory under the
caller-supplied store root. Reproduces v1's ``BaseKVStorage`` method signatures by copy
(upstream_ref: v1/lightrag/base.py, lines 382-437) — never imported.

Buffers writes in memory and flushes them on ``index_done_callback``, with reads consulting the
buffer first (read-your-writes before flush) — the same discipline v1's Cozo adapter already
uses (``v1/lightrag/kg/cozo_impl.py``'s deferred-write buffer pattern) and the Cozo port in a
later plan will need too. A failed write raises; it is never logged and continued — this
project's house style is refusals over silent fallbacks.

``PRAGMA journal_mode=WAL`` and ``PRAGMA synchronous=NORMAL`` are set at connect time: WAL keeps
concurrent readers (e.g. a verification read from a second connection) from blocking on the
flush transaction inside a single process tree, which is the only concurrency shape EMBED-01
admits (no external DB server, no cross-process writers).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from databasise.stores.base import StorageNameSpace


class SqliteKVStore(StorageNameSpace):
    def __init__(self, namespace: str, workspace: str, store_root: str | Path) -> None:
        super().__init__(namespace=namespace, workspace=workspace)
        self._dir = Path(store_root) / workspace / namespace
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._dir / "kv.sqlite3"
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS kv (id TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        self._conn.commit()
        self._pending_upserts: dict[str, dict[str, Any]] = {}
        self._pending_deletes: set[str] = set()

    async def get_by_id(self, id: str) -> dict[str, Any] | None:
        if id in self._pending_deletes:
            return None
        if id in self._pending_upserts:
            return self._pending_upserts[id]
        row = self._conn.execute("SELECT value FROM kv WHERE id = ?", (id,)).fetchone()
        return json.loads(row[0]) if row else None

    async def get_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for i in ids:
            value = await self.get_by_id(i)
            if value is not None:
                results.append(value)
        return results

    async def filter_keys(self, keys: set[str]) -> set[str]:
        existing = {k for k in keys if await self.get_by_id(k) is not None}
        return keys - existing

    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
        for key, value in data.items():
            self._pending_upserts[key] = value
            self._pending_deletes.discard(key)

    async def delete(self, ids: list[str]) -> None:
        for i in ids:
            self._pending_deletes.add(i)
            self._pending_upserts.pop(i, None)

    async def is_empty(self) -> bool:
        if self._pending_upserts:
            return False
        row = self._conn.execute("SELECT COUNT(*) FROM kv").fetchone()
        count = row[0] if row else 0
        return count == 0

    async def index_done_callback(self) -> None:
        try:
            for key, value in self._pending_upserts.items():
                self._conn.execute(
                    "INSERT INTO kv (id, value) VALUES (?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET value = excluded.value",
                    (key, json.dumps(value)),
                )
            for key in self._pending_deletes:
                self._conn.execute("DELETE FROM kv WHERE id = ?", (key,))
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        self._pending_upserts.clear()
        self._pending_deletes.clear()

    async def drop_pending_index_ops(self) -> None:
        self._pending_upserts.clear()
        self._pending_deletes.clear()

    async def drop(self) -> dict[str, str]:
        try:
            self._conn.execute("DELETE FROM kv")
            self._conn.commit()
            self._pending_upserts.clear()
            self._pending_deletes.clear()
            return {"status": "success", "message": "data dropped"}
        except Exception as exc:  # noqa: BLE001 — drop()'s own documented contract (v1 StorageNameSpace)
            return {"status": "error", "message": str(exc)}

    async def finalize(self) -> None:
        self._conn.close()
