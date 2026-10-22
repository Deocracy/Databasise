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

Scope: this module stores the table and the projections. The operator path lives in
``databasise/seam/engine.py``: ``promote``, ``rollback`` and ``retire`` each append one row through
``loop.run_in_executor``, and ``change_origin`` and ``record_kind`` are columns of that row. The
runner never appends: running an arm MUST NOT append to the ledger (CONTRACT §6); only an operator
verb does.

**``alias`` column (04-03-PLAN.md checkpoint, answer ``dedicated-alias-column``).** A small,
additive ``alias TEXT`` column, distinct from ``mutation_id``: the ledger is append-only, enforced
by the ``BEFORE UPDATE``/``BEFORE DELETE`` triggers below, so a field carrying two meanings (a
mutation's own identity, and a separate public handle a consumer might name) could never be
disentangled once real rows exist under whatever shape this module reads. The seam's alias
selector (``databasise.seam.selectors._resolve_alias``) reads it via :meth:`Ledger.by_alias`,
itself a derived projection exactly like :meth:`active_pointer` — never an independently-writable
"current alias" column. ``promote``, ``rollback`` and ``retire`` write the rows, each naming both
``alias`` (the promoted alias string) and ``mutation_id`` (the identifier of the wiring/arm) on
the same record. A missing ``ledger.db`` and an alias with no row both refuse, cleanly and
identically, per D-12/FA-06.

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
TABLE IF NOT EXISTS`` column list; the one later schema change, the unique index below, is applied
by :meth:`Ledger._create_schema` on an existing file as well (when old duplicate rows block it,
the old index stays and the condition is logged).

**07-05-PLAN.md (G-07-1): ``(alias, minted_version)`` is now UNIQUE.** A minted semver is a
published name under D-06/CONTRACT §0.4 and is never reused; previously this rule was enforced
only by a read (``by_alias``/``generation_state``) inside the promoting verb, which G-07-1 proved
insufficient under concurrency — two racing writers could both read "no conflict" before either
committed. ``ux_ledger_generation`` (see :meth:`Ledger._create_schema`) now enforces it at the
database itself, independent of any Python read path. Tombstone rows are exempt by SQLite's own
NULL-distinctness rule (verified: two rows with ``minted_version IS NULL`` on the same ``alias``
are accepted under a plain unique index), not by a partial-index predicate — retirement stays
unaffected.

**07-05-PLAN.md (G-07-1): :meth:`Ledger.transaction`.** ``append()`` alone was never the gap —
07-REVIEW.md's WR-01 and 07-UAT.md's reproduction both showed that ``seam/engine.py``'s three
operator verbs read a guard (the tombstone check, the active-generation check, the prior-version
read the semver mint depends on) and then, on a *separate* autocommit statement, ``append()``. A
concurrent writer could commit between the read and the append, so the guard's own answer could go
stale before the append it was gating ever ran. ``transaction()`` widens the span so the guard read
and the append commit together, as one ``BEGIN IMMEDIATE`` transaction: no writer can commit
between them, so a rollback can no longer land after a tombstone naming the same generation
(D-05/D-07), and a losing caller either serializes onto freshly-committed state or refuses through
the already-shipped ``TombstonedGenerationError`` — never a bare ``sqlite3`` exception. This adds
no second write; it encloses the one ``INSERT`` each verb already made with its own decisive read
(07-01-PLAN.md's "one ``INSERT`` in one transaction is the atomic alias repoint" still holds — the
repoint was always atomic, the *decision* to repoint is what G-07-1 closes).

**WR-03, deliberate exception:** every method on ``Ledger`` is plain synchronous ``def`` — this
module has no ``async def`` surface to dispatch off the event loop in the first place, unlike
``stores/kv.py``/``stores/lexical.py`` (own deliberate-exception notes) or ``stores/graph.py``
(the one that does dispatch). That is deliberate, not an oversight: the runner never calls
``append()``, and the three operator verbs in ``seam/engine.py`` call it from inside an
``async def`` body by offloading the whole ledger span (open, guard reads, ``append()``, close) to
one executor thread with ``loop.run_in_executor``, so the event loop never blocks. The offload
lives at those call sites rather than in this module, which stays synchronous.
"""

from __future__ import annotations

import contextlib
import json
import logging
import sqlite3
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Self


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


@dataclass(frozen=True, kw_only=True)
class LedgerEntry(LedgerRecord):
    """The read projection of a ledger row: a :class:`LedgerRecord` plus the table's own ``id``
    (the generation ordinal) and ``created_at``. Never a write type; ``LedgerRecord``'s CONTRACT §7
    field list is unchanged.
    """

    id: int
    created_at: str


_log = logging.getLogger(__name__)

_JSON_FIELDS = ("arm_instance_hashes", "opaque_ttl_renewals", "parity_records", "promotion_trace_ids")

# Bounded retry for the WAL-pragma first-touch race; see Ledger._set_wal.
_WAL_ATTEMPTS = 5
_WAL_RETRY_SECONDS = 0.02


class Ledger:
    """SQLite-backed append-only ledger, at its own database file at the store root beside the
    artifact registry.
    """

    _ro_wal: Path | None = None  # set by open_existing(read_only=True) only

    def __init__(self, store_root: str | Path) -> None:
        db_path = Path(store_root) / "ledger.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        try:
            self._conn.row_factory = sqlite3.Row
            self._set_wal()
            self._create_schema()
        except BaseException:
            self._conn.close()
            raise

    @classmethod
    def open_existing(cls, store_root: str | Path, *, read_only: bool = False) -> Ledger | None:
        """Open ``ledger.db`` without creating it: ``None`` when the file is absent.

        ``read_only=False`` (rollback and retire, which append anyway): a normal :class:`Ledger`,
        so the schema step and its index migration still run on an old file (D-08).

        ``read_only=True`` (``_resolve_alias``, CONTRACT §6: a read must not write): a
        ``PRAGMA query_only`` connection with no journal-mode change, no schema step, no migration
        and no commit. :meth:`close` decides the close checkpoint at close time. When
        ``ledger.db-wal`` holds any bytes then, the close does not checkpoint it into ``ledger.db``
        when this Python's ``sqlite3`` has ``SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE`` (without it, closing
        the last connection still checkpoints). When the WAL is empty or absent, the close
        checkpoint is kept, so the last reader to close removes the ``-wal`` and ``-shm`` files the
        reads created, overlapping reads included. After a writer's frames reach the WAL, the
        files stay until a writer's close removes them. SQLite's hot-journal recovery, after a
        writer crashed in rollback-journal mode, can still write the file; it does not change the
        logical content.
        A file with no ``ledger`` table (a zero-byte file included) also gives ``None``,
        so the caller refuses it exactly as it refuses an absent file. Only the read methods are
        valid on this handle. The file check and the open can race a first writer; the answer is
        correct as of the read.
        """
        db_path = Path(store_root) / "ledger.db"
        if not db_path.is_file():
            return None
        if not read_only:
            return cls(store_root)
        self = cls.__new__(cls)
        # A plain path plus PRAGMA query_only, not a `mode=ro` URI: the LEDG-06 lifecycle check
        # recognises ledger connections by their file path, and query_only refuses every write
        # statement on this connection just the same. query_only does not stop the WAL checkpoint
        # SQLite runs when the last connection closes, so close() disables it whenever the WAL may
        # hold a writer's frames (14-REVIEW-ITER2 WR-02); a Python whose sqlite3 lacks the constant
        # keeps the close checkpoint.
        self._ro_wal = db_path.with_name("ledger.db-wal")
        self._conn = sqlite3.connect(db_path)
        try:
            self._conn.execute("PRAGMA query_only = ON")
            self._conn.row_factory = sqlite3.Row
            has_table = self._conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'ledger'"
            ).fetchone()
        except BaseException:
            self.close()
            raise
        if has_table is None:
            self.close()
            return None
        return self

    def close(self) -> None:
        """Close the underlying connection.

        On a ``read_only`` handle the close checkpoint is decided here, not at the open
        (16-REVIEW-ITER2 WR-01), so overlapping reads still leave no ``-wal`` or ``-shm``.
        """
        # SQLite checkpoints on close only when this is the last connection on the file. A WAL of
        # zero bytes holds no frame, so that checkpoint copies nothing and only deletes the -wal
        # and -shm a read made. A WAL with any bytes may hold a writer's frames: no checkpoint.
        if self._ro_wal is not None and hasattr(sqlite3, "SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE"):
            try:
                holds_frames = self._ro_wal.stat().st_size > 0
            except FileNotFoundError:
                holds_frames = False
            if holds_frames:
                self._conn.setconfig(sqlite3.SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE, True)
        self._conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()  # returns None: never swallows the exception

    def _set_wal(self) -> None:
        """Switch the database to WAL, tolerating the first-touch race.

        Flipping journal mode needs a moment with no other connection on the file, and SQLite does
        NOT run the busy handler for it — so ``PRAGMA journal_mode=WAL`` raises ``SQLITE_BUSY``
        outright when several connections open a *fresh* ``ledger.db`` at once, rather than waiting
        the way an ordinary statement would. Measured at 5/360 constructions (1.4%) with six
        concurrent constructors on a new file, which is what made
        ``test_six_concurrent_promotes_mint_six_distinct_versions_with_zero_exceptions`` fail ~1 run
        in 30: a raw ``sqlite3.OperationalError`` escaping :meth:`__init__`, outside any
        :meth:`transaction` span and so unreachable by G-07-1's fix.

        WAL is a property of the file and persists once set, so whichever racer wins settles it for
        everyone and the rest observe ``wal`` on a later attempt.

        ponytail: degrades to the default rollback journal instead of raising if every attempt is
        contended. WAL widens reader/writer concurrency but is not load-bearing for correctness —
        :meth:`transaction`'s ``BEGIN IMMEDIATE`` serializes writers in either mode. Raising here
        would trade a 1.4% flake for a rarer one; refusing to start over a performance pragma is
        the worse failure.
        """
        for _ in range(_WAL_ATTEMPTS):
            try:
                mode = self._conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            except sqlite3.OperationalError:
                mode = None
            if str(mode).lower() == "wal":
                return
            time.sleep(_WAL_RETRY_SECONDS)

    @contextlib.contextmanager
    def transaction(self) -> Iterator[None]:
        """G-07-1: widen a caller's guard-read-then-append into one ``BEGIN IMMEDIATE``
        transaction, so no other writer can commit between the guard's read and the append it
        gates. Entered around a promotion verb's own guard read (not just its final ``INSERT``) —
        see the module docstring's "07-05-PLAN.md (G-07-1)" note for why the read has to be inside
        the span, not only the write.

        On success (the ``yield`` body raises nothing), commits. On any exception, rolls back and
        re-raises — this rollback path is load-bearing: every refusal a wrapped verb raises exits
        through here, and the rollback ends the write transaction so later writers are not
        blocked. Opening a ``Ledger`` over a current schema takes no write lock. First-time schema
        creation and the unique-index migration on a pre-07-05 file do, so those opens can wait up
        to the connection's busy timeout behind a writer. ``open_existing(read_only=True)`` never
        takes the write lock.

        ponytail: two ceilings, not enforced in code. (a) One ``append()`` per ``transaction()`` —
        ``append()``'s own ``commit()`` ends the span early; a caller needing two appends in one
        transaction would have to move that commit out. (b) Does not nest — a second
        ``BEGIN IMMEDIATE`` inside an open one raises ``sqlite3.OperationalError: cannot start a
        transaction within a transaction``.
        """
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self._conn.rollback()
            raise
        else:
            self._conn.commit()

    @contextlib.contextmanager
    def snapshot(self) -> Iterator[None]:
        """One deferred read transaction around several reads, so they see one WAL snapshot
        (16-REVIEW-B WR-02). It does not block writers: a promote or rollback can commit during
        the reads, and the reads do not see it, so they stay consistent with each other. Allowed
        on the ``read_only`` handle; always rolled back, so it writes nothing."""
        self._conn.execute("BEGIN")
        try:
            yield
        finally:
            self._conn.rollback()

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
        # G-07-1/07-05-PLAN.md: DROP the old plain index by name, then CREATE the UNIQUE index
        # under a NEW name. Per the plan's own verified fact (mechanism_decision fact 2):
        # `CREATE UNIQUE INDEX IF NOT EXISTS ix_ledger_generation ...` over an EXISTING plain
        # index of that same name is a silent no-op in SQLite 3.53.1 — sqlite_master.sql would
        # still read `CREATE INDEX`, and duplicates would still be accepted, on any database that
        # already ran the old schema. Dropping first and naming the replacement differently is the
        # whole fix; reusing the old name would ship a "fix" that does nothing on an existing
        # ledger.db. Dropping/creating an index is not a row mutation, so the append-only
        # BEFORE UPDATE/BEFORE DELETE triggers below are untouched.
        #
        # 14-REVIEW A-WR-01: CREATE the unique index first and DROP the old one only once it
        # exists. Each DDL statement autocommits, so the old drop-then-create order committed the
        # drop even when the create failed. A pre-07-05 file can hold duplicate
        # (alias, minted_version) rows (the G-07-1 race); there the create fails, the old plain
        # index stays, and the condition is logged instead of raised, so an operator verb never
        # sees a raw IntegrityError as a 500. Writers on such a file stay serialized by
        # transaction()'s BEGIN IMMEDIATE, and every projection that reads a generation's row
        # (by_alias, generation_state, lineage) takes the latest one with ORDER BY id DESC.
        try:
            self._conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_ledger_generation "
                "ON ledger(alias, minted_version)"
            )
        except sqlite3.IntegrityError:
            _log.warning(
                "ledger.db holds duplicate (alias, minted_version) rows from before 07-05; "
                "kept the old ix_ledger_generation index, ux_ledger_generation not created"
            )
        else:
            self._conn.execute("DROP INDEX IF EXISTS ix_ledger_generation")
        # ponytail: a raw sqlite3.IntegrityError from this index on INSERT is deliberately NOT
        # wrapped into a SeamRefusalError. Once Ledger.transaction() (above) encloses every write
        # path, this constraint is a backstop no caller can reach through the seam — it signals a
        # broken machine invariant, not a caller error, exactly like _promote_sync's own
        # unreachable-by-construction UnrecognisedPromotionVerbError backstop. Wrapping it would
        # add new §18 surface for a path no consumer can reach.
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

    def _row_to_record(self, row: sqlite3.Row, cls: type[LedgerRecord] = LedgerRecord) -> Any:
        kwargs: dict[str, Any] = {}
        for field_name in cls.__dataclass_fields__:
            value = row[field_name]
            if field_name in _JSON_FIELDS:
                value = json.loads(value)
            kwargs[field_name] = value
        return cls(**kwargs)

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
        row names this alias. The seam's alias selector (``databasise.seam.selectors.
        _resolve_alias``) and the promote, rollback and retire verbs in ``seam/engine.py`` call it;
        the selector refuses identically whether the table holds no rows at all or holds rows
        naming a different alias (D-12/FA-06).

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
        ``None`` when this alias has no such generation. The rollback and retire verbs in
        ``seam/engine.py`` call it for their tombstone and unknown-version refusals; it lives
        beside :meth:`by_alias`/:meth:`active_pointer`, so the projection set stays in one module.
        """
        cur = self._conn.execute(
            "SELECT * FROM ledger WHERE alias = ? AND (minted_version = ? OR targets_version = ?) "
            "ORDER BY id DESC LIMIT 1",
            (alias, version, version),
        )
        row = cur.fetchone()
        return self._row_to_record(row) if row is not None else None

    def lineage(self, alias: str, version: str) -> list[str]:
        """The versions reached from ``version`` by following ``targets_version`` through the row
        that minted each version (the latest such row, as :meth:`by_alias` reads it, so a pre-07-05
        file with duplicate ``(alias, minted_version)`` rows follows the active row), in walk order
        starting with ``version``. Stops at a missing or non-rollback row, and on a version already
        visited, so a cycle terminates. Guards go by version through the rollback lineage, never by
        wiring identity (RIG §PR.2: a re-promotion is a new generation); the retire and rollback
        guards and Phase 16's CONN-07 ``active`` read it. Not :meth:`generation_state`: for a
        rollback's target that returns the active row itself, so a walk over it loops.
        """
        visited = [version]
        while True:
            row = self._conn.execute(
                "SELECT record_kind, targets_version FROM ledger "
                "WHERE alias = ? AND minted_version = ? ORDER BY id DESC LIMIT 1",
                (alias, visited[-1]),
            ).fetchone()
            if row is None or row["record_kind"] != "rollback" or row["targets_version"] in visited:
                return visited
            visited.append(row["targets_version"])

    def history(self, mutation_id: str) -> list[LedgerRecord]:
        """Every record for ``mutation_id``, oldest first. Test-only: no product code calls it;
        the product reads an alias's history through :meth:`history_for_alias`.
        """
        cur = self._conn.execute(
            "SELECT * FROM ledger WHERE mutation_id = ? ORDER BY id ASC",
            (mutation_id,),
        )
        return [self._row_to_record(r) for r in cur.fetchall()]

    def aliases(self) -> list[LedgerEntry]:
        """The active row of every alias, ordered by alias: :meth:`by_alias`'s active-row rule (the
        latest non-tombstone row) applied to each alias in one SELECT. The operator console's alias
        listing reads it."""
        cur = self._conn.execute(
            "SELECT * FROM ledger WHERE id IN (SELECT MAX(id) FROM ledger "
            "WHERE alias IS NOT NULL AND record_kind != 'tombstone' GROUP BY alias) ORDER BY alias"
        )
        return [self._row_to_record(r, cls=LedgerEntry) for r in cur.fetchall()]

    def history_for_alias(self, alias: str) -> list[LedgerEntry]:
        """Every row for ``alias``, oldest first, rollbacks and tombstones included. Each entry
        carries the row's ``id`` (the generation ordinal) and ``created_at``. Phase 16's
        CONN-06/CONN-07 routes read it.
        """
        cur = self._conn.execute(
            "SELECT * FROM ledger WHERE alias = ? ORDER BY id ASC",
            (alias,),
        )
        return [self._row_to_record(r, cls=LedgerEntry) for r in cur.fetchall()]
