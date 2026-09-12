"""07-05-PLAN.md Task 2 (G-07-1): the schema-level backstop for D-06's never-reused published
name — ``UNIQUE(alias, minted_version)`` (``ux_ledger_generation``), refusing a duplicate at the
database itself, independent of any Python read path. The old-index case
(``test_reopening_a_database_carrying_the_old_plain_index_enforces_uniqueness``) is the test that
would have caught a silent no-op fix: ``CREATE UNIQUE INDEX IF NOT EXISTS`` over an existing plain
index of the same name does nothing in SQLite (mechanism_decision fact 2), which is exactly why the
real fix drops the old index by name and creates the unique one under a new name.
"""

from __future__ import annotations

import sqlite3

import pytest
from databasise.ledger.ledger import Ledger, LedgerRecord


def _record(**overrides) -> LedgerRecord:
    base = {
        "mutation_id": "mut-1",
        "mutation_class": "retrieval-side",
        "parent": None,
        "arm_instance_hashes": ["a" * 64],
        "effect_size": None,
        "verdict": None,
        "evidence_pointer": None,
        "proposer_id": "operator",
        "depth_label": None,
        "tier_of_decision": None,
        "decomposition_ratio": None,
        "opaque_ttl_renewals": [],
        "parity_records": [],
        "promotion_provenance": "operator_asserted",
        "promotion_trace_ids": [],
        "change_origin": "human_edit",
        "record_kind": "promotion",
        "alias": "gen-alias",
    }
    base.update(overrides)
    return LedgerRecord(**base)


def test_a_duplicate_non_null_alias_minted_version_pair_is_refused_by_the_database(store_root):
    ledger = Ledger(store_root)
    ledger.append(_record(mutation_id="naive", minted_version="1.0.0", record_kind="promotion"))

    with pytest.raises(sqlite3.IntegrityError):
        ledger.append(
            _record(mutation_id="bypass", minted_version="1.0.0", record_kind="promotion")
        )


def test_any_number_of_tombstone_rows_null_minted_version_still_insert(store_root):
    ledger = Ledger(store_root)

    for i in range(3):
        row_id = ledger.append(
            _record(
                mutation_id=f"naive-{i}",
                minted_version=None,
                targets_version="1.0.0",
                record_kind="tombstone",
            )
        )
        assert isinstance(row_id, int)

    rows = ledger._conn.execute(
        "SELECT COUNT(*) FROM ledger WHERE record_kind = 'tombstone'"
    ).fetchone()[0]
    assert rows == 3


def test_reopening_a_database_carrying_the_old_plain_index_enforces_uniqueness(store_root):
    """The test that would have caught a silent no-op fix: build the OLD schema shape (a plain,
    non-unique ``ix_ledger_generation`` index) with a raw connection first, then open a real
    ``Ledger`` over that same file and prove a duplicate append now raises.
    """
    db_path = store_root / "ledger.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(db_path)
    raw.execute(
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
    # The OLD, plain (non-unique) index this plan replaces.
    raw.execute("CREATE INDEX IF NOT EXISTS ix_ledger_generation ON ledger(alias, minted_version)")
    raw.commit()
    raw.close()

    # Opening a real Ledger over this file must upgrade the index, not silently no-op.
    ledger = Ledger(store_root)
    sql = ledger._conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'ux_ledger_generation'"
    ).fetchone()
    assert sql is not None and "UNIQUE" in sql["sql"]
    old_index_still_present = ledger._conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = 'ix_ledger_generation'"
    ).fetchone()
    assert old_index_still_present is None  # dropped, not left behind alongside the new one

    ledger.append(_record(mutation_id="naive", minted_version="1.0.0", record_kind="promotion"))
    with pytest.raises(sqlite3.IntegrityError):
        ledger.append(
            _record(mutation_id="bypass", minted_version="1.0.0", record_kind="promotion")
        )
