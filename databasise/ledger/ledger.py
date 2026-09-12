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

**``alias`` column (04-03-PLAN.md checkpoint, answer ``dedicated-alias-column``).** A small,
additive ``alias TEXT`` column, distinct from ``mutation_id``: the ledger is append-only, enforced
by the ``BEFORE UPDATE``/``BEFORE DELETE`` triggers below, so a field carrying two meanings (a
mutation's own identity, and a separate public handle a consumer might name) could never be
disentangled once Phase 7 writes the first real row under whatever shape this module reads. The
seam's alias selector (``databasise.seam.selectors._resolve_alias``) reads it via
:meth:`Ledger.by_alias`, itself a derived projection exactly like :meth:`active_pointer` — never
an independently-writable "current alias" column. The registry is empty until Phase 7's promote
path appends the first row naming both ``alias`` (the promoted alias string) and ``mutation_id``
(the identifier of the promoted wiring/arm) on the same record; every alias lookup against an
empty or non-matching registry refuses, cleanly and identically, per D-12/FA-06.

**07-01-PLAN.md: four additive columns, each with exactly one meaning.** ``change_origin`` (NOT
NULL — ``"human_edit"`` or ``"machine_mutation"``, CONTRACT §7) and ``record_kind`` (NOT NULL —
``"promotion"``, ``"rollback"`` or ``"tombstone"``) are the promote path's own write-side
requirements; ``minted_version`` (nullable) and ``targets_version`` (nullable) are four, not
CONTRACT §7's/RESEARCH.md's suggested three, because this module's own ``alias``-column precedent
above states the reason directly: a field carrying two meanings can never be disentangled once
real rows exist. ``minted_version`` means "the semver **this record mints**" and is ``NULL``
exactly when ``record_kind == "tombstone"``. ``targets_version`` means "the semver **this record
acts on**" and is non-``NULL`` exactly for ``record_kind`` in ``("rollback", "tombstone")``.
Collapsing them into one column would make a tombstone's own version indistinguishable from a
version it minted. No SQL default on either NOT NULL column — an absent value fails at the
database, never falls back to a plausible string. All four columns land in the single ``CREATE
TABLE IF NOT EXISTS`` column list, following the identical no-migration precedent the ``alias``
column set: the table holds zero rows in every environment this milestone runs in.

**WR-03, deliberate exception:** every method on ``Ledger`` is plain synchronous ``def`` — this
module has no ``async def`` surface to dispatch off the event loop in the first place, unlike
``stores/kv.py``/``stores/lexical.py`` (own deliberate-exception notes) or ``stores/graph.py``
(the one that does dispatch). That is deliberate, not an oversight: per the scope fence above,
nothing in the live Phase 1 runner path calls ``append()`` at all, so there is no event-loop-
blocking concern to fix yet. If a later phase's promotion path calls ``append()`` from inside an
``async def`` body, offload it (``loop.run_in_executor``) at that call site then — mirroring
``check_same_thread=False`` and cross-thread-safety concerns already noted in
``stores/kv.py``'s own docstring — rather than making this module async pre-emptively for a
caller that does not exist yet.
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
    change_origin: str
    record_kind: str
    alias: str | None = None
    minted_version: str | None = None
    targets_version: str | None = None


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
                change_origin TEXT NOT NULL,
                record_kind TEXT NOT NULL,
                alias TEXT,
                minted_version TEXT,
                targets_version TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_ledger_mutation_id ON ledger(mutation_id)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_ledger_alias ON ledger(alias)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_ledger_generation ON ledger(alias, minted_version)"
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
            "promotion_provenance, promotion_trace_ids, change_origin, record_kind, alias, "
            "minted_version, targets_version, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
                record.change_origin,
                record.record_kind,
                record.alias,
                record.minted_version,
                record.targets_version,
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

    def by_alias(self, alias: str) -> LedgerRecord | None:
        """The active pointer for ``alias`` — a projection over the ledger, computed by
        ``ORDER BY id DESC LIMIT 1`` keyed on the additive ``alias`` column, exactly like
        :meth:`active_pointer`'s own projection keyed on ``mutation_id``. Returns ``None`` when no
        row names this alias — the seam's alias selector (``databasise.seam.selectors.
        _resolve_alias``) is this method's only caller, and refuses identically whether the
        registry holds no rows at all or holds rows naming a different alias (D-12/FA-06's
        empty-registry-refuses-cleanly requirement).

        07-01-PLAN.md: excludes ``record_kind = 'tombstone'`` rows — the active pointer derives
        from promotion and rollback generations only. A retirement record names a generation that
        has stopped being eligible; deriving the alias from it would resolve the alias to the very
        wiring that was just retired.
        """
        cur = self._conn.execute(
            "SELECT * FROM ledger WHERE alias = ? AND record_kind != 'tombstone' "
            "ORDER BY id DESC LIMIT 1",
            (alias,),
        )
        row = cur.fetchone()
        return self._row_to_record(row) if row is not None else None

    def generation_state(self, alias: str, version: str) -> LedgerRecord | None:
        """07-01-PLAN.md: the latest record naming the ``(alias, version)`` generation, whether it
        is the record that minted that version (``minted_version == version``) or a later record
        acting on it (``targets_version == version``) — a rollback or a tombstone. Returns
        ``None`` when this alias has no such generation. 07-02's tombstone and
        unknown-version refusals are this method's only callers; it lands here, beside
        :meth:`by_alias`/:meth:`active_pointer`, so the projection set stays in one module.
        """
        cur = self._conn.execute(
            "SELECT * FROM ledger WHERE alias = ? AND (minted_version = ? OR targets_version = ?) "
            "ORDER BY id DESC LIMIT 1",
            (alias, version, version),
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
