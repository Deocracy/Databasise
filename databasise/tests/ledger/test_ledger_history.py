"""LEDG-07 (14-02-PLAN.md, D-09): an alias's full history reads back oldest first, each entry
carrying the table's own ``id`` (the generation ordinal) and ``created_at``.

Fail-first friendly: the new method is resolved with ``getattr`` so the file collects on the phase
base and fails by ``AssertionError`` there. Helpers are copied in, not imported from other tests.
"""

from __future__ import annotations

import sqlite3

from databasise.ledger.ledger import Ledger, LedgerRecord
from databasise.seam.engine import Databasise
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings

_ALIAS = "hist-a"
_OTHER = "hist-b"


def _seed_trace(store_root, arm_name: str) -> str:
    resolved = next(resolved for name, resolved in all_wirings() if name == arm_name)
    node_ids = sorted(resolved.get("nodes", {}).keys())
    fake_record = {
        "run_id": f"fake-run-{arm_name}",
        "wiring_id": resolved.get("wiring_id"),
        "wiring_instance_hash": f"sha256:{'0' * 64}",
        "arm_id": "seam",
        "nodes": [{"node_id": node_id} for node_id in node_ids],
    }
    return TraceStore(store_root).persist(fake_record)


def _table_rows(store_root, alias: str) -> list[sqlite3.Row]:
    conn = sqlite3.connect(store_root / "ledger.db")
    conn.row_factory = sqlite3.Row
    try:
        return conn.execute(
            "SELECT id, created_at, record_kind, minted_version, targets_version, mutation_id "
            "FROM ledger WHERE alias = ? ORDER BY id",
            (alias,),
        ).fetchall()
    finally:
        conn.close()


async def _build_history(store_root):
    engine = Databasise(store_root=store_root, workspace="history-test")
    t_naive = _seed_trace(store_root, "naive")
    t_hybrid = _seed_trace(store_root, "hybrid")
    first = await engine.promote(_ALIAS, [t_naive], "human_edit")
    second = await engine.promote(_ALIAS, [t_hybrid], "human_edit")
    rolled = await engine.rollback(_ALIAS, first.version, [_seed_trace(store_root, "naive")], "human_edit")
    retired = await engine.retire(_ALIAS, second.version, [_seed_trace(store_root, "hybrid")], "human_edit")
    await engine.promote(_OTHER, [_seed_trace(store_root, "naive")], "human_edit")
    return first, second, rolled, retired


async def test_history_for_alias_returns_the_alias_rows_oldest_first(store_root):
    first, second, rolled, _retired = await _build_history(store_root)

    history_for_alias = getattr(Ledger, "history_for_alias", None)
    assert history_for_alias is not None, "Ledger.history_for_alias does not exist"

    entries = history_for_alias(Ledger(store_root), _ALIAS)
    table = _table_rows(store_root, _ALIAS)

    assert [e.id for e in entries] == [r["id"] for r in table]
    assert [e.created_at for e in entries] == [r["created_at"] for r in table]
    assert [e.record_kind for e in entries] == ["promotion", "promotion", "rollback", "tombstone"]
    assert [e.minted_version for e in entries] == [first.version, second.version, rolled.version, None]
    assert [e.targets_version for e in entries] == [None, None, first.version, second.version]
    assert [e.mutation_id for e in entries] == [r["mutation_id"] for r in table]
    assert all(e.alias == _ALIAS for e in entries)


async def test_every_entry_is_a_ledger_record(store_root):
    await _build_history(store_root)

    history_for_alias = getattr(Ledger, "history_for_alias", None)
    assert history_for_alias is not None, "Ledger.history_for_alias does not exist"

    entries = history_for_alias(Ledger(store_root), _ALIAS)
    assert entries
    for entry in entries:
        assert isinstance(entry, LedgerRecord)
        assert isinstance(entry.id, int)
        assert isinstance(entry.created_at, str) and entry.created_at


def test_an_alias_with_no_rows_reads_empty(store_root):
    history_for_alias = getattr(Ledger, "history_for_alias", None)
    assert history_for_alias is not None, "Ledger.history_for_alias does not exist"

    assert history_for_alias(Ledger(store_root), "never-promoted") == []
