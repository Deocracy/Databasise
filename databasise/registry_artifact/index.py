"""The artifact registry (CONTRACT §7): a SQLite index over the content-addressed blob store
(``databasise/stores/blob.py``), carrying every §7-enumerated field and distinguishing all three
CONTRACT §3 scopes — ``shared``/``quarantined``/``self_storage`` — at the schema level, not just
in application code.

Table schema (Claude's Discretion, recorded here): a single ``artifacts`` table with an integer
primary key, plus ``content_hash``, ``namespace``, ``scope`` (CHECK over exactly the three
scopes), the three SA-2 sub-recipe stamps, ``corpus_id``, ``space_id`` (nullable),
``producer_instance_hash``, ``recipe_hash``, ``retention_tier`` (CHECK over exactly
``runnable``/``readable``/``tombstoned``), and ``created_at``. A UNIQUE index over
``(content_hash, namespace, scope)`` makes ``register()`` idempotent — a second registration of
hash-identical inputs resolves to the existing row rather than a coincidentally-equal duplicate
(RIG §RUN.2's "identical means shared" case) — and a non-unique index on ``recipe_hash`` makes
``overlaps()`` a lookup rather than a scan.

``register()`` is gated to D-02's second call site (the artifact-write path,
``registry_artifact/write_path.py``) via ``REGISTER_AUTHORIZATION``, a module-level sentinel: a
caller must import and pass it explicitly to reach ``register()`` at all. This is not real
Python privacy — any caller can import the sentinel — but it makes bypass a deliberate, grep-able
act rather than an accidental plain method call, which is the property D-02's "no path can
bypass by accident" actually needs. This plan's own ``tests/registry_artifact/test_index.py``
imports the sentinel to exercise ``register()`` directly, exactly as ``write_path.py`` does;
``tests/registry_artifact/test_write_path_blast_radius.py`` (Task 2) proves the refusal fires
for a caller that does not.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NamedTuple

from databasise.namespaces import artifacts_overlap

# A transient store write (writes_kv/writes_vector/writes_graph/writes_lexical) carries no
# artifact namespace, no sub-recipe stamp, no corpus and no producing-instance binding this
# registry's shape requires (CONTRACT §7) — it is never a registry entry at all.
_TRANSIENT_STORE_EFFECTS = frozenset(
    {"writes_kv", "writes_vector", "writes_graph", "writes_lexical"}
)

_SCOPES = ("shared", "quarantined", "self_storage")
_RETENTION_TIERS = ("runnable", "readable", "tombstoned")

# See module docstring: the write-path authorization gate (D-02's second call site).
REGISTER_AUTHORIZATION = object()


class TransientWriteNotRegistrableError(ValueError):
    """Raised by ``register()`` when handed a transient store effect (``writes_kv`` /
    ``writes_vector`` / ``writes_graph`` / ``writes_lexical``) rather than ``writes_artifact`` —
    CONTRACT §7 states such a write "MUST NOT be registered as an entry here at all."
    """

    def __init__(self, effect: str) -> None:
        self.effect = effect
        super().__init__(
            f"effect {effect!r} is a transient store write, not writes_artifact; CONTRACT §7 "
            "states a transient store write MUST NOT be registered as an artifact-registry "
            "entry at all — it carries no namespace, no sub-recipe stamp, no corpus and no "
            "producing-instance binding this registry's shape requires"
        )


class UnauthorizedRegisterCallError(RuntimeError):
    """Raised by ``register()`` when called without ``REGISTER_AUTHORIZATION`` — D-02's second
    blast-radius call site (``write_path.write_artifact()``) is the sanctioned route.
    """

    def __init__(self) -> None:
        super().__init__(
            "register() called without write-path authorization; use "
            "write_path.write_artifact() instead (D-02's second blast-radius call site), or "
            "import REGISTER_AUTHORIZATION explicitly if you are exercising this registry's "
            "own test suite"
        )


@dataclass(frozen=True)
class ArtifactRecord:
    """One artifact-registry row: every CONTRACT §7 field."""

    id: int
    content_hash: str
    namespace: str
    scope: str
    sa2_chunker: str
    sa2_extraction: str
    sa2_embedding: str
    corpus_id: str
    space_id: str | None
    producer_instance_hash: str
    recipe_hash: str
    retention_tier: str
    created_at: str


@dataclass(frozen=True)
class DiscoveryResult:
    """One §16.1 discovery result: scope, SA-2 stamps, space_id, producing instance, retention
    tier, and ``pin_required`` — per §16.1, a result omitting scope or the pin-required flag
    would not let an author answer whether their wiring may read the artifact.
    """

    content_hash: str
    namespace: str
    scope: str
    sa2_chunker: str
    sa2_extraction: str
    sa2_embedding: str
    corpus_id: str
    space_id: str | None
    producer_instance_hash: str
    recipe_hash: str
    retention_tier: str
    pin_required: bool


class Pin(NamedTuple):
    """§16.2's pin: an explicit, author-written reference naming the artifact (by content hash
    and namespace) and the instance that produced it — never implicit, never glob-matched.
    """

    content_hash: str
    namespace: str
    producer_instance_hash: str


_FILTERABLE_COLUMNS = frozenset(
    {
        "content_hash",
        "namespace",
        "corpus_id",
        "space_id",
        "sa2_chunker",
        "sa2_extraction",
        "sa2_embedding",
        "recipe_hash",
        "retention_tier",
    }
)


class ArtifactRegistry:
    """SQLite index over the content-addressed blob store, at its own database file at the store
    root (not inside a namespace directory — the registry indexes across namespaces).
    """

    def __init__(self, store_root: str | Path) -> None:
        db_path = Path(store_root) / "artifact_registry.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def _create_schema(self) -> None:
        scope_check = ", ".join(f"'{s}'" for s in _SCOPES)
        tier_check = ", ".join(f"'{t}'" for t in _RETENTION_TIERS)
        self._conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash TEXT NOT NULL,
                namespace TEXT NOT NULL,
                scope TEXT NOT NULL CHECK (scope IN ({scope_check})),
                sa2_chunker TEXT NOT NULL,
                sa2_extraction TEXT NOT NULL,
                sa2_embedding TEXT NOT NULL,
                corpus_id TEXT NOT NULL,
                space_id TEXT,
                producer_instance_hash TEXT NOT NULL,
                recipe_hash TEXT NOT NULL,
                retention_tier TEXT NOT NULL CHECK (retention_tier IN ({tier_check})),
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS ux_artifacts_hash_ns_scope "
            "ON artifacts(content_hash, namespace, scope)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS ix_artifacts_recipe_hash ON artifacts(recipe_hash)"
        )
        self._conn.commit()

    def _row_to_record(self, row: sqlite3.Row) -> ArtifactRecord:
        return ArtifactRecord(
            id=row["id"],
            content_hash=row["content_hash"],
            namespace=row["namespace"],
            scope=row["scope"],
            sa2_chunker=row["sa2_chunker"],
            sa2_extraction=row["sa2_extraction"],
            sa2_embedding=row["sa2_embedding"],
            corpus_id=row["corpus_id"],
            space_id=row["space_id"],
            producer_instance_hash=row["producer_instance_hash"],
            recipe_hash=row["recipe_hash"],
            retention_tier=row["retention_tier"],
            created_at=row["created_at"],
        )

    def _find(self, content_hash: str, namespace: str, scope: str) -> ArtifactRecord | None:
        cur = self._conn.execute(
            "SELECT * FROM artifacts WHERE content_hash = ? AND namespace = ? AND scope = ?",
            (content_hash, namespace, scope),
        )
        row = cur.fetchone()
        return self._row_to_record(row) if row is not None else None

    def register(
        self,
        *,
        _authorization: object | None = None,
        effect: str,
        content_hash: str,
        namespace: str,
        scope: str,
        sa2_chunker: str,
        sa2_extraction: str,
        sa2_embedding: str,
        corpus_id: str,
        space_id: str | None,
        producer_instance_hash: str,
        recipe_hash: str,
        retention_tier: str = "runnable",
    ) -> ArtifactRecord:
        """Insert a row, refusing (a) a caller without ``REGISTER_AUTHORIZATION`` and (b) a
        transient store write. Idempotent on the ``(content_hash, namespace, scope)`` UNIQUE key:
        a second registration of hash-identical inputs returns the existing row rather than
        raising or creating a coincidentally-equal duplicate (RIG §RUN.2).
        """
        if _authorization is not REGISTER_AUTHORIZATION:
            raise UnauthorizedRegisterCallError()
        if effect in _TRANSIENT_STORE_EFFECTS:
            raise TransientWriteNotRegistrableError(effect)

        existing = self._find(content_hash, namespace, scope)
        if existing is not None:
            return existing

        created_at = datetime.now(UTC).isoformat()
        cur = self._conn.execute(
            "INSERT INTO artifacts (content_hash, namespace, scope, sa2_chunker, sa2_extraction, "
            "sa2_embedding, corpus_id, space_id, producer_instance_hash, recipe_hash, "
            "retention_tier, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                content_hash,
                namespace,
                scope,
                sa2_chunker,
                sa2_extraction,
                sa2_embedding,
                corpus_id,
                space_id,
                producer_instance_hash,
                recipe_hash,
                retention_tier,
                created_at,
            ),
        )
        self._conn.commit()
        cur2 = self._conn.execute("SELECT * FROM artifacts WHERE id = ?", (cur.lastrowid,))
        return self._row_to_record(cur2.fetchone())

    def discover(
        self,
        *,
        caller_instance_hash: str,
        pins: Sequence[Pin] = (),
        **filters: Any,
    ) -> list[DiscoveryResult]:
        """§16.1's discovery operation. Applies the scope filter itself as part of executing the
        query — never a keyword the caller can disable: ``shared`` is visible to any caller, a
        ``quarantined`` row only under an explicit pin naming both the artifact and its producing
        instance, and a ``self_storage`` row only to its own producing instance.
        """
        unknown = set(filters) - _FILTERABLE_COLUMNS
        if unknown:
            raise ValueError(f"discover() got unknown filter keys: {sorted(unknown)}")

        where_clauses = []
        params: list[Any] = []
        for key, value in filters.items():
            if value is None:
                where_clauses.append(f"{key} IS NULL")
            else:
                where_clauses.append(f"{key} = ?")
                params.append(value)

        sql = "SELECT * FROM artifacts"
        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)
        cur = self._conn.execute(sql, params)
        rows = [self._row_to_record(r) for r in cur.fetchall()]

        pin_set = {(p.content_hash, p.namespace, p.producer_instance_hash) for p in pins}

        results: list[DiscoveryResult] = []
        for row in rows:
            if row.scope == "shared":
                visible, pin_required = True, False
            elif row.scope == "quarantined":
                visible = (row.content_hash, row.namespace, row.producer_instance_hash) in pin_set
                pin_required = True
            elif row.scope == "self_storage":
                visible = row.producer_instance_hash == caller_instance_hash
                pin_required = True
            else:  # pragma: no cover — unreachable given the schema's CHECK constraint
                visible, pin_required = False, True

            if not visible:
                continue
            results.append(
                DiscoveryResult(
                    content_hash=row.content_hash,
                    namespace=row.namespace,
                    scope=row.scope,
                    sa2_chunker=row.sa2_chunker,
                    sa2_extraction=row.sa2_extraction,
                    sa2_embedding=row.sa2_embedding,
                    corpus_id=row.corpus_id,
                    space_id=row.space_id,
                    producer_instance_hash=row.producer_instance_hash,
                    recipe_hash=row.recipe_hash,
                    retention_tier=row.retention_tier,
                    pin_required=pin_required,
                )
            )
        return results

    def overlaps(self, recipe_hash: str) -> list[ArtifactRecord]:
        """RIG §RUN.2's artifact-overlap decision: rows whose recipe hash overlaps
        ``recipe_hash`` under ``namespaces.artifacts_overlap`` — the index narrows candidates to
        an indexed lookup, and ``artifacts_overlap`` (not a re-derived ``==``) is what decides
        overlap, so this module never introduces a second, looser comparison.
        """
        cur = self._conn.execute("SELECT * FROM artifacts WHERE recipe_hash = ?", (recipe_hash,))
        rows = [self._row_to_record(r) for r in cur.fetchall()]
        return [r for r in rows if artifacts_overlap(r.recipe_hash, recipe_hash)]

    def delete(self, content_hash: str, namespace: str) -> None:
        """Remove the row at ``(content_hash, namespace)``. Deletion-capable by design — unlike
        the ledger (Task 3), which never shares a mutation path with this registry.
        """
        self._conn.execute(
            "DELETE FROM artifacts WHERE content_hash = ? AND namespace = ?",
            (content_hash, namespace),
        )
        self._conn.commit()
