"""14-02-PLAN.md Task 2 (D-06, D-08): deterministic closing, the read-only open, and the rollback
lineage walk. Non-row unit tests; new names are resolved with ``getattr``/``hasattr`` so each test
fails by ``AssertionError`` on code that predates them.
"""

from __future__ import annotations

import sqlite3

from databasise.ledger.ledger import Ledger, LedgerRecord

_ALIAS = "lin-alias"


def _record(**overrides) -> LedgerRecord:
    base = {
        "mutation_id": "naive",
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
        "alias": _ALIAS,
    }
    base.update(overrides)
    return LedgerRecord(**base)


def _promotion(version: str) -> LedgerRecord:
    return _record(record_kind="promotion", minted_version=version)


def _rollback(version: str, target: str) -> LedgerRecord:
    return _record(record_kind="rollback", minted_version=version, targets_version=target)


def test_a_ledger_closes_as_a_context_manager(store_root):
    assert hasattr(Ledger, "close"), "Ledger.close does not exist"
    assert hasattr(Ledger, "__enter__"), "Ledger.__enter__ does not exist"

    ledger = Ledger(store_root)
    with ledger as opened:
        assert opened is ledger
        assert ledger._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0] == 0

    caught = None
    try:
        ledger._conn.execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001 - the type is the assertion
        caught = exc
    assert type(caught).__name__ == "ProgrammingError", caught


def test_exit_does_not_swallow_an_exception(store_root):
    caught = None
    try:
        with Ledger(store_root):
            raise ValueError("boom")
    except ValueError as exc:
        caught = exc
    assert caught is not None and str(caught) == "boom"


def test_open_existing_on_a_fresh_root_returns_none_and_creates_nothing(store_root):
    open_existing = getattr(Ledger, "open_existing", None)
    assert open_existing is not None, "Ledger.open_existing does not exist"

    assert open_existing(store_root) is None
    for name in ("ledger.db", "ledger.db-wal", "ledger.db-shm"):
        assert not (store_root / name).exists(), name


def test_open_existing_opens_an_existing_file(store_root):
    open_existing = getattr(Ledger, "open_existing", None)
    assert open_existing is not None, "Ledger.open_existing does not exist"

    with Ledger(store_root) as writer:
        writer.append(_promotion("1.0.0"))
    opened = open_existing(store_root)
    assert opened is not None
    with opened:
        assert [r.minted_version for r in opened.history_for_alias(_ALIAS)] == ["1.0.0"]


def test_open_existing_runs_the_index_migration_on_an_old_file(store_root):
    open_existing = getattr(Ledger, "open_existing", None)
    assert open_existing is not None, "Ledger.open_existing does not exist"

    # Build the old-format file: seed through a real Ledger, then swap in the plain index.
    with Ledger(store_root) as seed:
        seed._conn.execute("DROP INDEX ux_ledger_generation")
        seed._conn.execute("CREATE INDEX ix_ledger_generation ON ledger(alias, minted_version)")
        seed._conn.commit()

    opened = open_existing(store_root)
    assert opened is not None
    with opened:
        names = {
            row["name"]
            for row in opened._conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            ).fetchall()
        }
    assert "ux_ledger_generation" in names
    assert "ix_ledger_generation" not in names


def test_lineage_follows_rollbacks_to_their_promotion(store_root):
    lineage = getattr(Ledger, "lineage", None)
    assert lineage is not None, "Ledger.lineage does not exist"

    ledger = Ledger(store_root)
    ledger.append(_promotion("1.0.0"))
    ledger.append(_promotion("2.0.0"))
    ledger.append(_rollback("3.0.0", "1.0.0"))
    ledger.append(_promotion("4.0.0"))
    ledger.append(_rollback("5.0.0", "3.0.0"))

    assert lineage(ledger, _ALIAS, "5.0.0") == ["5.0.0", "3.0.0", "1.0.0"]
    assert lineage(ledger, _ALIAS, "4.0.0") == ["4.0.0"]
    assert lineage(ledger, _ALIAS, "9.9.9") == ["9.9.9"]


def test_lineage_terminates_on_a_cycle(store_root):
    lineage = getattr(Ledger, "lineage", None)
    assert lineage is not None, "Ledger.lineage does not exist"

    ledger = Ledger(store_root)
    ledger.append(_rollback("2.0.0", "3.0.0"))
    ledger.append(_rollback("3.0.0", "2.0.0"))

    assert lineage(ledger, _ALIAS, "2.0.0") == ["2.0.0", "3.0.0"]


def test_the_transaction_docstring_makes_no_stall_claim():
    assert "stall" not in (Ledger.transaction.__doc__ or "").lower()


def test_a_failed_constructor_closes_its_connection(store_root, monkeypatch):
    connections: list[sqlite3.Connection] = []
    real_connect = sqlite3.connect

    def recording_connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs)
        connections.append(conn)
        return conn

    def failing_schema(self):
        raise RuntimeError("schema failed")

    monkeypatch.setattr(sqlite3, "connect", recording_connect)
    monkeypatch.setattr(Ledger, "_create_schema", failing_schema)

    constructor_error = None
    try:
        Ledger(store_root)
    except RuntimeError as exc:
        constructor_error = exc
    assert constructor_error is not None and str(constructor_error) == "schema failed"
    assert connections, "Ledger did not connect"

    use_error = None
    try:
        connections[-1].execute("SELECT 1")
    except Exception as exc:  # noqa: BLE001 - the type is the assertion
        use_error = exc
    assert type(use_error).__name__ == "ProgrammingError", "the failed constructor left its connection open"
