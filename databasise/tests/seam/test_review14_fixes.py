"""Regression tests for the 14-REVIEW.md warning fixes (A-WR-01, A-WR-02)."""

from __future__ import annotations

import logging
import sqlite3

import pytest

from databasise.ledger.ledger import Ledger, LedgerRecord
from databasise.seam.refusals import UnsatisfiableSelectorError
from databasise.seam.selectors import _resolve_alias


def _row(mutation_id: str, version: str, alias: str = "prod") -> LedgerRecord:
    return LedgerRecord(
        mutation_id=mutation_id,
        mutation_class="retrieval-side",
        parent=None,
        arm_instance_hashes=[],
        effect_size=None,
        verdict=None,
        evidence_pointer=None,
        proposer_id="test-fixture",
        depth_label=None,
        tier_of_decision=None,
        decomposition_ratio=None,
        opaque_ttl_renewals=[],
        parity_records=[],
        promotion_provenance="operator_asserted",
        promotion_trace_ids=[],
        change_origin="human_edit",
        record_kind="promotion",
        alias=alias,
        minted_version=version,
    )


def _indexes(db) -> list[str]:
    conn = sqlite3.connect(db)
    try:
        return sorted(
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND name NOT LIKE 'sqlite_%'"
            )
        )
    finally:
        conn.close()


def _journal_mode(db) -> str:
    conn = sqlite3.connect(db)
    try:
        return conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()


def _legacy_file_with_duplicates(tmp_path):
    """A pre-07-05 ledger.db: the old plain index and two (prod, 1.0.0) rows (the G-07-1 race)."""
    with Ledger(tmp_path) as ledger:
        ledger._conn.execute("DROP INDEX ux_ledger_generation")
        ledger._conn.execute("CREATE INDEX ix_ledger_generation ON ledger(alias, minted_version)")
        ledger.append(_row("naive", "1.0.0"))
        ledger.append(_row("naive", "1.0.0"))
    return tmp_path / "ledger.db"


# --- A-WR-01: the alias read path is read-only; the writer migration never raises on duplicates


def test_an_alias_read_on_a_legacy_file_resolves_and_changes_nothing(tmp_path):
    db = _legacy_file_with_duplicates(tmp_path)
    before = (db.read_bytes(), _indexes(db))

    resolved = _resolve_alias("prod", store_root=tmp_path)

    assert resolved["wiring_id"]
    assert (db.read_bytes(), _indexes(db)) == before
    assert "ix_ledger_generation" in before[1]


def test_a_zero_byte_ledger_refuses_by_name_and_stays_empty(tmp_path):
    db = tmp_path / "ledger.db"
    db.touch()

    with pytest.raises(UnsatisfiableSelectorError) as caught:
        _resolve_alias("prod", store_root=tmp_path)

    assert caught.value.requested == "prod"
    assert db.stat().st_size == 0


def test_a_file_with_no_ledger_table_refuses_by_name_and_keeps_its_journal_mode(tmp_path):
    db = tmp_path / "ledger.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE other (x)")
    conn.commit()
    conn.close()
    before = (db.read_bytes(), _journal_mode(db))

    with pytest.raises(UnsatisfiableSelectorError):
        _resolve_alias("prod", store_root=tmp_path)

    assert (db.read_bytes(), _journal_mode(db)) == before
    assert before[1] == "delete"


def test_an_alias_read_never_converts_a_rollback_journal_file_to_wal(tmp_path):
    with Ledger(tmp_path) as ledger:
        ledger.append(_row("naive", "1.0.0"))
        ledger._conn.execute("PRAGMA journal_mode=DELETE")
    db = tmp_path / "ledger.db"
    assert _journal_mode(db) == "delete"

    _resolve_alias("prod", store_root=tmp_path)

    assert _journal_mode(db) == "delete"


def test_the_read_only_handle_refuses_a_write(tmp_path):
    with Ledger(tmp_path) as ledger:
        ledger.append(_row("naive", "1.0.0"))

    with Ledger.open_existing(tmp_path, read_only=True) as ledger:
        assert ledger.by_alias("prod").minted_version == "1.0.0"
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            ledger.append(_row("naive", "2.0.0"))


def test_the_writer_open_keeps_the_old_index_and_logs_when_duplicates_block_the_unique_one(
    tmp_path, caplog
):
    db = _legacy_file_with_duplicates(tmp_path)

    with caplog.at_level(logging.WARNING, logger="databasise.ledger.ledger"):
        opened = Ledger.open_existing(tmp_path)
    assert opened is not None
    opened.close()

    assert "ix_ledger_generation" in _indexes(db)
    assert "ux_ledger_generation" not in _indexes(db)
    assert "duplicate (alias, minted_version)" in caplog.text


def test_the_writer_open_still_migrates_a_legacy_file_without_duplicates(tmp_path):
    with Ledger(tmp_path) as ledger:
        ledger._conn.execute("DROP INDEX ux_ledger_generation")
        ledger._conn.execute("CREATE INDEX ix_ledger_generation ON ledger(alias, minted_version)")
        ledger.append(_row("naive", "1.0.0"))

    Ledger.open_existing(tmp_path).close()

    indexes = _indexes(tmp_path / "ledger.db")
    assert "ux_ledger_generation" in indexes
    assert "ix_ledger_generation" not in indexes
