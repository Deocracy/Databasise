"""SQLite FTS5-backed lexical (full-text) store (D-06): one database file per namespace
directory under the caller-supplied store root.

``lexical`` is a **new primitive** — v1 has no full-text store to port (D-06), so only the
lifecycle ABC shape and the buffer/commit/abort discipline travel forward (the same discipline
already reproduced in ``stores/kv.py`` from v1's Cozo adapter pattern); the FTS5 body here is
new. Writes buffer in memory; ``index_done_callback`` flushes them into the FTS5 index inside one
transaction and clears the buffer; ``drop_pending_index_ops`` discards the buffer without
touching the index. A failed flush raises and leaves the buffer intact — this project's house
style is refusals over silent fallbacks, never a logged-and-continued partial write.

Every query term is bound as a parameter and always wrapped in FTS5 double-quote phrase syntax
before binding, so a term containing FTS5 operator characters (``*``, ``^``, ``:``, ``AND``,
``OR``, ``NOT``, ``NEAR``, parentheses) is searched literally rather than altering query
structure — the same discipline the Cozo port (plan 01-06) carries for Datalog metacharacters,
applied here to the lexical backend.

FTS5 availability is verified at construction, not lazily at first query: a SQLite build without
FTS5 compiled in raises ``Fts5UnavailableError`` naming FTS5 explicitly, rather than silently
falling back to a ``LIKE`` scan — a silent fallback would make the lexical primitive quietly not
be one.

**WR-03, deliberate exception:** this adapter's SQLite calls run synchronously inline inside their
``async def`` bodies, the same deliberate (documented, not code-changed) exception
``stores/kv.py``'s own module docstring records and gives its full rationale for — WAL-mode writes
here are typically fast, and dispatching through ``run_in_executor`` would first require
reopening the connection with ``check_same_thread=False`` and re-verifying cross-thread safety
under this project's single-writer discipline, which is real surgery deliberately deferred rather
than applied speculatively.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from databasise.stores.base import StorageNameSpace


class Fts5UnavailableError(RuntimeError):
    """Raised when the running interpreter's SQLite build has no FTS5 module compiled in."""


def _quote_literal(term: str) -> str:
    """Wrap ``term`` in FTS5 double-quote phrase syntax so it is matched literally, never
    parsed as FTS5 query syntax (operators, column filters, NEAR, boolean keywords).
    """
    return '"' + term.replace('"', '""') + '"'


class SqliteLexicalStore(StorageNameSpace):
    def __init__(self, namespace: str, workspace: str, store_root: str | Path) -> None:
        super().__init__(namespace=namespace, workspace=workspace)
        self._dir = Path(store_root) / workspace / namespace
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._dir / "lexical.sqlite3"
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        try:
            self._conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS docs "
                "USING fts5(doc_id UNINDEXED, content)"
            )
        except sqlite3.OperationalError as exc:
            self._conn.close()
            raise Fts5UnavailableError(
                "SQLite FTS5 module is not compiled into the running interpreter's sqlite3 — "
                "the lexical store requires FTS5 and refuses to fall back to a LIKE scan "
                f"(original error: {exc})"
            ) from exc
        self._conn.commit()
        self._pending_upserts: dict[str, str] = {}
        self._pending_deletes: set[str] = set()

    async def upsert(self, data: dict[str, dict[str, Any]]) -> None:
        """Buffer documents for indexing. Each value must carry a ``"content"`` string field."""
        for doc_id, value in data.items():
            self._pending_upserts[doc_id] = value["content"]
            self._pending_deletes.discard(doc_id)

    async def delete(self, ids: list[str]) -> None:
        for doc_id in ids:
            self._pending_deletes.add(doc_id)
            self._pending_upserts.pop(doc_id, None)

    async def query(self, term: str) -> list[dict[str, Any]]:
        """Search the flushed FTS5 index for ``term``, bound and quoted as a literal phrase.

        An empty query string returns an empty result list rather than every document.
        """
        if not term:
            return []
        match_expr = _quote_literal(term)
        rows = self._conn.execute(
            "SELECT doc_id, bm25(docs) AS rank FROM docs WHERE docs MATCH ? ORDER BY rank",
            (match_expr,),
        ).fetchall()
        return [{"id": doc_id, "score": rank} for doc_id, rank in rows]

    async def index_done_callback(self) -> None:
        try:
            for doc_id in self._pending_deletes:
                self._conn.execute("DELETE FROM docs WHERE doc_id = ?", (doc_id,))
            for doc_id, content in self._pending_upserts.items():
                self._conn.execute("DELETE FROM docs WHERE doc_id = ?", (doc_id,))
                self._conn.execute(
                    "INSERT INTO docs (doc_id, content) VALUES (?, ?)", (doc_id, content)
                )
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
            self._conn.execute("DELETE FROM docs")
            self._conn.commit()
            self._pending_upserts.clear()
            self._pending_deletes.clear()
            return {"status": "success", "message": "data dropped"}
        except Exception as exc:  # noqa: BLE001 — drop()'s own documented contract (v1 StorageNameSpace)
            return {"status": "error", "message": str(exc)}

    async def finalize(self) -> None:
        self._conn.close()
