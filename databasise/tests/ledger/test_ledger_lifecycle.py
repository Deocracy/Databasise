"""14-09-PLAN.md Task 2 (LEDG-06, D-08): every operator verb and every alias read closes its
``ledger.db`` connection, a refused verb on a fresh store root creates none of ``ledger.db``,
``ledger.db-wal`` and ``ledger.db-shm``, and ``Ledger.transaction`` makes no "stall" claim.

The file imports only names that exist at the phase base and copies its own helpers, so it collects
and fails by assertion there.
"""

from __future__ import annotations

import sqlite3

from databasise.ledger.ledger import Ledger
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
from databasise.seam.selectors import Selector
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings

_ALIAS = "a"


async def _capture(awaitable):
    try:
        return await awaitable
    except Exception as caught:  # noqa: BLE001 - the assertion is on the captured type
        return caught


def _seed_trace(store_root, arm_name: str = "naive") -> str:
    resolved = next(resolved for name, resolved in all_wirings() if name == arm_name)
    node_ids = sorted(resolved.get("nodes", {}).keys())
    return TraceStore(store_root).persist(
        {
            "run_id": f"fake-run-{arm_name}",
            "wiring_id": resolved.get("wiring_id"),
            "wiring_instance_hash": f"sha256:{'0' * 63}{len(node_ids) % 10}",
            "arm_id": "seam",
            "nodes": [{"node_id": node_id} for node_id in node_ids],
        }
    )


class _RecordingConnection(sqlite3.Connection):
    closed = False

    def close(self) -> None:
        self.closed = True
        super().close()


def _install_counter(monkeypatch) -> list[_RecordingConnection]:
    """Wrap ``sqlite3.connect`` so every connection to a ``ledger.db`` path is recorded."""
    recorded: list[_RecordingConnection] = []
    real_connect = sqlite3.connect

    def counting_connect(database, *args, **kwargs):
        kwargs["factory"] = _RecordingConnection
        connection = real_connect(database, *args, **kwargs)
        if str(database).endswith("ledger.db"):
            recorded.append(connection)
        return connection

    monkeypatch.setattr(sqlite3, "connect", counting_connect)
    return recorded


async def test_no_ledger_connection_is_left_open(tmp_path, monkeypatch):
    engine = Databasise(store_root=tmp_path, workspace="lifecycle")
    first = await engine.promote(_ALIAS, [_seed_trace(tmp_path, "naive")], "human_edit")
    second = await engine.promote(_ALIAS, [_seed_trace(tmp_path, "hybrid")], "human_edit")
    # Without the file open_existing would return None, no connection would open, and the test
    # would prove nothing.
    assert (tmp_path / "ledger.db").is_file()

    recorded = _install_counter(monkeypatch)
    for _ in range(20):
        # The store is empty, so the query refuses; the alias read that opens the ledger ran first.
        await _capture(engine.query(QueryObject(text="q"), Selector(alias=_ALIAS)))
    await engine.promote(_ALIAS, [_seed_trace(tmp_path, "naive")], "human_edit")
    await engine.rollback(_ALIAS, first.version, [_seed_trace(tmp_path, "naive")], "human_edit")
    await engine.retire(_ALIAS, second.version, [_seed_trace(tmp_path, "naive")], "human_edit")

    assert len(recorded) >= 23, f"only {len(recorded)} ledger.db connections were recorded"
    unclosed = [connection for connection in recorded if not connection.closed]
    assert not unclosed, f"{len(unclosed)} of {len(recorded)} ledger.db connections were left open"


async def test_refused_verbs_on_a_fresh_root_create_no_ledger_file(tmp_path):
    engine = Databasise(store_root=tmp_path, workspace="lifecycle")
    trace = _seed_trace(tmp_path)
    assert not (tmp_path / "ledger.db").exists()

    outcomes = {
        "promote-next": await _capture(engine.promote(_ALIAS, [trace], "human_edit", verb="promote-next")),
        "promote-now": await _capture(engine.promote(_ALIAS, [trace], "human_edit", verb="promote-now")),
        "rollback": await _capture(engine.rollback(_ALIAS, "9.9.9", [trace], "human_edit")),
        "retire": await _capture(engine.retire(_ALIAS, "9.9.9", [trace], "human_edit")),
    }
    expected = {
        "promote-next": "GateNotCalibratedError",
        "promote-now": "GateNotCalibratedError",
        "rollback": "UnknownGenerationVersionError",
        "retire": "UnknownGenerationVersionError",
    }
    for verb, caught in outcomes.items():
        assert type(caught).__name__ == expected[verb], f"{verb} gave {type(caught).__name__}: {caught}"

    leftovers = [name for name in ("ledger.db", "ledger.db-wal", "ledger.db-shm") if (tmp_path / name).exists()]
    assert not leftovers, f"refused verbs left {leftovers} on a fresh root"


def test_the_transaction_docstring_makes_no_stall_claim():
    assert "stall" not in (Ledger.transaction.__doc__ or "")
