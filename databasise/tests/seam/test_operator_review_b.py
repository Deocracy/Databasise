"""Phase 16 lane B review fixes for the operator read methods in ``databasise/seam/engine.py``."""

from __future__ import annotations

import asyncio
import os
import sqlite3
from pathlib import Path

import pytest
from databasise.ledger.ledger import Ledger, LedgerRecord
from databasise.seam.corpus import Page
from databasise.seam.engine import Databasise
from databasise.seam.rest import create_app
from databasise.seam.trace_store import TraceStore
from fastapi.testclient import TestClient


def _record(alias: str, version: str, mutation_id: str = "m1") -> LedgerRecord:
    return LedgerRecord(
        mutation_id=mutation_id,
        mutation_class="wiring",
        parent=None,
        arm_instance_hashes=["h"],
        effect_size=None,
        verdict=None,
        evidence_pointer=None,
        proposer_id="operator",
        depth_label=None,
        tier_of_decision=None,
        decomposition_ratio=None,
        opaque_ttl_renewals=[],
        parity_records=[],
        promotion_provenance="operator-asserted",
        promotion_trace_ids=["t"],
        change_origin="test",
        record_kind="promotion",
        alias=alias,
        minted_version=version,
    )


def _seed_ledger(root: Path) -> None:
    with Ledger(root) as ledger:
        ledger.append(_record("a", "1.0.0"))


def test_ledger_reads_leave_no_wal_or_shm_files(tmp_path: Path) -> None:
    # WR-01: the first read of a WAL ledger made -wal/-shm and the no-checkpoint close kept them
    _seed_ledger(tmp_path)
    engine = Databasise(store_root=tmp_path, workspace="ws")
    before = sorted(os.listdir(tmp_path))
    assert "ledger.db-wal" not in before
    assert [r["alias"] for r in asyncio.run(engine.ledger_aliases())] == ["a"]
    assert asyncio.run(engine.ledger_history("a", Page(limit=10, offset=0)))["total"] == 1
    assert sorted(os.listdir(tmp_path)) == before


def test_ledger_history_reads_one_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # WR-02: a promotion committed between the history read and the head read left no row active
    _seed_ledger(tmp_path)
    engine = Databasise(store_root=tmp_path, workspace="ws")
    original = Ledger.history_for_alias

    def _then_promote(self: Ledger, alias: str) -> list:
        rows = original(self, alias)
        with Ledger(tmp_path) as writer:
            writer.append(_record("a", "2.0.0", mutation_id="m2"))
        return rows

    monkeypatch.setattr(Ledger, "history_for_alias", _then_promote)
    page = asyncio.run(engine.ledger_history("a", Page(limit=10, offset=0)))
    assert [(r["minted_version"], r["active"]) for r in page["records"]] == [("1.0.0", True)]


class _WriteBetween:
    """A connection proxy that persists one trace after the page SELECT, before the COUNT."""

    def __init__(self, conn: sqlite3.Connection, root: Path) -> None:
        self._conn, self._root, self._done = conn, root, False

    def execute(self, sql: str, *args: object) -> sqlite3.Cursor:
        cur = self._conn.execute(sql, *args)
        if sql.startswith("SELECT token") and not self._done:
            self._done = True
            TraceStore(self._root).persist({"partial": False})
        return cur

    def rollback(self) -> None:
        self._conn.rollback()


def test_trace_page_and_total_read_one_snapshot(tmp_path: Path) -> None:
    # WR-02: the COUNT ran as its own statement, so total counted a row the page never saw
    engine = Databasise(store_root=tmp_path, workspace="ws")
    engine._trace_store.persist({"partial": False})
    engine._trace_store._conn = _WriteBetween(engine._trace_store._conn, tmp_path)
    page = asyncio.run(engine.list_traces(Page(limit=10, offset=0)))
    assert (len(page["items"]), page["total"]) == (1, 1)


def _operator_client(root: Path, log_path: Path | None = None) -> TestClient:
    return TestClient(create_app(store_root=root, workspace="ws", operator=True, log_path=log_path))


@pytest.mark.parametrize("bad", ["{not json", "[]"])
def test_a_corrupted_trace_row_is_a_502(tmp_path: Path, bad: str) -> None:
    # WR-03 (and lane A WR-01): json.loads or rec.get escaped GET /traces as a bare 500
    client = _operator_client(tmp_path)
    with sqlite3.connect(tmp_path / "trace.db") as conn:
        conn.execute("INSERT INTO traces VALUES ('t', ?, '2026-01-01')", (bad,))
    response = client.get("/traces")
    assert response.status_code == 502
    assert "StoreCorrupted" in response.text


def test_a_corrupted_ledger_row_is_a_502(tmp_path: Path) -> None:
    # WR-03: _row_to_record's json.loads escaped the ledger reads as a bare 500
    _seed_ledger(tmp_path)
    with sqlite3.connect(tmp_path / "ledger.db") as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(ledger)") if r[1] != "id"]
        picks = ["'{bad'" if c == "arm_instance_hashes" else "'2.0.0'" if c == "minted_version" else c for c in cols]
        conn.execute(f"INSERT INTO ledger ({', '.join(cols)}) SELECT {', '.join(picks)} FROM ledger")
    client = _operator_client(tmp_path)
    for response in (client.get("/ledger/aliases"), client.post("/ledger/history", json={"alias": "a"})):
        assert response.status_code == 502
        assert "StoreCorrupted" in response.text
