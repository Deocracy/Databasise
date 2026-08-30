"""The append-only promotion ledger (CONTRACT §7/§6): an INSERT-only SQLite table, with the
"active pointer" always a derived query (``SELECT ... ORDER BY id DESC LIMIT 1``), never its own
writable column — "the ledger append **is** the promotion decision; the active pointer is a
projection derived from the ledger, not an independent record" (CONTRACT §6).

Columns are exactly CONTRACT §7's ledger-record field enumeration: mutation id, class, parent,
arm instance hashes, effect size, verdict, evidence pointer, proposer id, depth label,
tier-of-decision, decomposition ratio, opaque-node TTL renewals with their recorded reasons,
parity records for decompositions, ``promotion_provenance``, and ``promotion_trace_ids`` — plus
``id`` (the monotonic append order) and ``created_at``. List-valued fields (``arm_instance_hashes``,
``opaque_ttl_renewals``, ``parity_records``, ``promotion_trace_ids``) are stored as JSON text.

Append-only is enforced at the database level, not merely by omitting Python methods: SQLite
``BEFORE UPDATE``/``BEFORE DELETE`` triggers ``RAISE(ABORT, ...)`` for any mutation attempt
against the ``ledger`` table, through any connection, not only through this module's own code.

Scope fence (Phase 1 only stands the table and the projection up): this module does not implement
the operator path, ``change_origin``, the tombstone-lifting prohibition, or the atomic alias
repoint — those are MACH-07 and Phase 7's deliverables. Nothing in the runner calls ``append()``:
running an arm MUST NOT append to the ledger (CONTRACT §6) — only a promotion does, and Phase 1
does not exercise a real promotion.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LedgerRecord:
    """One ledger record: every CONTRACT §7-enumerated field this module implements."""

    mutation_id: str
    mutation_class: str
    parent: str | None
    arm_instance_hashes: list[str]
    effect_size: float | None
    verdict: str | None
    evidence_pointer: str | None
    proposer_id: str
    depth_label: str | None
    tier_of_decision: str | None
    decomposition_ratio: float | None
    opaque_ttl_renewals: list[dict[str, Any]]
    parity_records: list[dict[str, Any]]
    promotion_provenance: str
    promotion_trace_ids: list[str]


_JSON_FIELDS = ("arm_instance_hashes", "opaque_ttl_renewals", "parity_records", "promotion_trace_ids")


class Ledger:
    """SQLite-backed append-only ledger, at its own database file at the store root beside the
    artifact registry.
    """

    def __init__(self, store_root: str | Path) -> None:
        db_path = Path(store_root) / "ledger.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def _create_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ledger (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mutation_id TEXT NOT NULL,
                mutation_class TEXT NOT NULL,
                parent TEXT,
                arm_instance_hashes TEXT NOT NULL,
                effect_size REAL,
                verdict TEXT,
                evidence_pointer TEXT,
                proposer_id TEXT NOT NULL,
                depth_label TEXT,
                tier_of_decision TEXT,
                decomposition_ratio REAL,
                opaque_ttl_renewals TEXT NOT NULL,
                parity_records TEXT NOT NULL,
                promotion_provenance TEXT NOT NULL,
                promotion_trace_ids TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_ledger_mutation_id ON ledger(mutation_id)"
        )
        self._conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_ledger_no_update
            BEFORE UPDATE ON ledger
            BEGIN
                SELECT RAISE(ABORT, 'ledger is append-only: UPDATE is refused');
            END
            """
        )
        self._conn.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_ledger_no_delete
            BEFORE DELETE ON ledger
            BEGIN
                SELECT RAISE(ABORT, 'ledger is append-only: DELETE is refused');
            END
            """
        )
        self._conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> LedgerRecord:
        kwargs: dict[str, Any] = {}
        for field_name in LedgerRecord.__dataclass_fields__:
            value = row[field_name]
            if field_name in _JSON_FIELDS:
                value = json.loads(value)
            kwargs[field_name] = value
        return LedgerRecord(**kwargs)

    def append(self, record: LedgerRecord) -> int:
        """Insert ``record``, returning its monotonically increasing ``id``. Never updates or
        deletes an existing row — this is the ledger's only mutation.
        """
        created_at = datetime.now(UTC).isoformat()
        cur = self._conn.execute(
            "INSERT INTO ledger (mutation_id, mutation_class, parent, arm_instance_hashes, "
            "effect_size, verdict, evidence_pointer, proposer_id, depth_label, "
            "tier_of_decision, decomposition_ratio, opaque_ttl_renewals, parity_records, "
            "promotion_provenance, promotion_trace_ids, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                record.mutation_id,
                record.mutation_class,
                record.parent,
                json.dumps(record.arm_instance_hashes),
                record.effect_size,
                record.verdict,
                record.evidence_pointer,
                record.proposer_id,
                record.depth_label,
                record.tier_of_decision,
                record.decomposition_ratio,
                json.dumps(record.opaque_ttl_renewals),
                json.dumps(record.parity_records),
                record.promotion_provenance,
                json.dumps(record.promotion_trace_ids),
                created_at,
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def active_pointer(self, mutation_id: str) -> LedgerRecord | None:
        """The most recent record for ``mutation_id`` — a projection over the ledger, computed
        by ``ORDER BY id DESC LIMIT 1``, never read from an independently-written column.
        """
        cur = self._conn.execute(
            "SELECT * FROM ledger WHERE mutation_id = ? ORDER BY id DESC LIMIT 1",
            (mutation_id,),
        )
        row = cur.fetchone()
        return self._row_to_record(row) if row is not None else None

    def history(self, mutation_id: str) -> list[LedgerRecord]:
        """Every record for ``mutation_id``, oldest first."""
        cur = self._conn.execute(
            "SELECT * FROM ledger WHERE mutation_id = ? ORDER BY id ASC",
            (mutation_id,),
        )
        return [self._row_to_record(r) for r in cur.fetchall()]
