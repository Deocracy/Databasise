"""``databasise.seam.jobs_store`` — which modality family minted an ingest job (11-06, D-02, M-12).

One sqlite file, ``<store_root>/jobs.db``, one table ``job_families``, WAL, in ``trace_store.py``'s
pattern. ``Databasise.get_job_status`` looks a job id up here first: a HippoRAG job is answered
from its row, anything else (a LightRAG row, or no row) asks v1 as before.

The file is created only by :meth:`JobFamilyStore.record`, so health, status and job reads never
create it (LRAG-13). Each call opens and closes its own connection: one engine is driven from
several threads under the REST transport, and a per-call connection shares no transaction state.
"""

from __future__ import annotations

import contextlib
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import NamedTuple


class JobFamily(NamedTuple):
    family: str
    document_id: str | None
    created_at: str


class JobFamilyStore:
    def __init__(self, store_root: str | Path) -> None:
        self._path = Path(store_root) / "jobs.db"

    def record(self, job_id: str, family: str, document_id: str | None) -> None:
        """Record ``job_id``'s family, creating ``jobs.db`` on the first call."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.closing(sqlite3.connect(self._path)) as conn, conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS job_families (job_id TEXT PRIMARY KEY, family TEXT NOT NULL, "
                "document_id TEXT, created_at TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO job_families VALUES (?, ?, ?, ?)",
                (job_id, family, document_id, datetime.now(UTC).isoformat()),
            )

    def lookup(self, job_id: str) -> JobFamily | None:
        """``job_id``'s row, or ``None``. Opens read-only and creates nothing."""
        if not self._path.is_file():
            return None
        with contextlib.closing(sqlite3.connect(f"{self._path.resolve().as_uri()}?mode=ro", uri=True)) as conn:
            row = conn.execute(
                "SELECT family, document_id, created_at FROM job_families WHERE job_id = ?", (job_id,)
            ).fetchone()
        return JobFamily(*row) if row else None


__all__ = ["JobFamily", "JobFamilyStore"]
