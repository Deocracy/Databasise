"""``databasise.seam.floors_store`` — the calibrated A/A floors the promotion gate reads (TOOL-12, D-13).

One sqlite file, ``<store_root>/floors.db``, one table ``floors``, WAL, in ``jobs_store.py``'s pattern.
``eval.aa_run --spend`` writes one row per family; ``Databasise.promote`` reads them for a gate verb.
A row is keyed on the traces' own ``wiring_instance_hash`` plus the five ``NullIdentity`` fields, so a
floor calibrated for one arm, bundle, tier, metric or determinism/concurrency setting is never read as
another's (``CalibrationResult.floor_for`` makes the staleness call at the gate).

The file is created only by :meth:`FloorStore.record`; :meth:`any_floor` and :meth:`lookup` open
read-only and create nothing, so a refused gate verb leaves the store root untouched. Each call opens
and closes its own connection (one engine serves several threads under REST). This module imports
nothing from the ledger package and defines no promotion verb: it is a store, not a gate.

Recorded limits (D-13): no production part reports ``cache_hit``, so a real A/A run is refused by
``calibrate_aa_floor`` and no floor is persisted by one yet; and only an engine started on the eval
store root reads these floors, because they live under that root.
"""

from __future__ import annotations

import contextlib
import sqlite3
from dataclasses import astuple, dataclass, fields
from pathlib import Path


@dataclass(frozen=True)
class FloorRow:
    wiring_instance_hash: str
    bundle_at_v: str
    tier: str
    metric: str
    determinism_setting: str
    concurrency_setting: str
    floor: float
    n_questions: int
    n_resamples: int
    seed: int | None
    created_at: str


_FIELD_NAMES = tuple(f.name for f in fields(FloorRow))
_KEY_COLUMNS = _FIELD_NAMES[:6]


class FloorStore:
    def __init__(self, store_root: str | Path) -> None:
        self._path = Path(store_root) / "floors.db"

    def record(self, row: FloorRow) -> None:
        """Persist ``row``, replacing a row with the same key; creates ``floors.db`` on first call."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        columns = ", ".join(_FIELD_NAMES)
        with contextlib.closing(sqlite3.connect(self._path)) as conn, conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS floors ({columns}, PRIMARY KEY ({', '.join(_KEY_COLUMNS)}))"
            )
            conn.execute(
                f"INSERT OR REPLACE INTO floors ({columns}) VALUES ({', '.join('?' * len(_FIELD_NAMES))})",
                astuple(row),
            )

    def any_floor(self) -> bool:
        """True when ``floors.db`` exists and holds a row. Opens read-only and creates nothing."""
        if not self._path.is_file():
            return False
        with contextlib.closing(sqlite3.connect(f"{self._path.resolve().as_uri()}?mode=ro", uri=True)) as conn:
            try:
                return conn.execute("SELECT 1 FROM floors LIMIT 1").fetchone() is not None
            except sqlite3.OperationalError:  # file exists but no table yet
                return False

    def lookup(self, wiring_instance_hash: str) -> list[FloorRow]:
        """Every row recorded for ``wiring_instance_hash``; ``[]`` when none or the file is absent."""
        if not self._path.is_file():
            return []
        with contextlib.closing(sqlite3.connect(f"{self._path.resolve().as_uri()}?mode=ro", uri=True)) as conn:
            try:
                rows = conn.execute(
                    f"SELECT {', '.join(_FIELD_NAMES)} FROM floors WHERE wiring_instance_hash = ? "
                    "ORDER BY bundle_at_v, tier, metric",
                    (wiring_instance_hash,),
                ).fetchall()
            except sqlite3.OperationalError:
                return []
        return [FloorRow(*row) for row in rows]


__all__ = ["FloorRow", "FloorStore"]
