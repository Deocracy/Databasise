"""14-08-PLAN.md Task 2 (D-05): rollback and retire onto an alias whose active row names a wiring
that does not resolve refuse by name (``UnsatisfiableSelectorError`` naming only the caller's alias)
and never raise ``AssertionError``. Promote no longer refuses there: 14-REVIEW A-WR-02 makes it
repair the alias (``tests/seam/test_review14_fixes.py``).
"""

from __future__ import annotations

import pytest

from databasise.ledger.ledger import Ledger, LedgerRecord
from databasise.seam.engine import Databasise
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings

pytest.importorskip("fastapi")
from databasise.seam.rest import create_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


async def _capture(awaitable):
    try:
        return await awaitable
    except Exception as caught:  # noqa: BLE001 - the assertion is on the captured type
        return caught


def _row(mutation_id: str, version: str) -> LedgerRecord:
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
        alias="x",
        minted_version=version,
    )


def _store(tmp_path):
    """Alias ``x``: 1.0.0 names ``naive``, the active 2.0.0 names a wiring nothing resolves."""
    ledger = Ledger(tmp_path)
    ledger.append(_row("naive", "1.0.0"))
    ledger.append(_row("nonexistent", "2.0.0"))
    ledger._conn.close()
    resolved = next(resolved for name, resolved in all_wirings() if name == "naive")
    node_ids = sorted(resolved.get("nodes", {}).keys())
    trace = TraceStore(tmp_path).persist(
        {
            "run_id": "fake-run-naive",
            "wiring_id": resolved.get("wiring_id"),
            "wiring_instance_hash": f"sha256:{'0' * 63}{len(node_ids) % 10}",
            "arm_id": "seam",
            "nodes": [{"node_id": node_id} for node_id in node_ids],
        }
    )
    return trace


def _rows(tmp_path) -> int:
    ledger = Ledger(tmp_path)
    try:
        return ledger._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    finally:
        ledger._conn.close()


async def test_the_verbs_refuse_an_unresolvable_alias_row_by_name(tmp_path):
    trace = _store(tmp_path)
    rows = _rows(tmp_path)
    engine = Databasise(store_root=tmp_path, workspace="alias-row")

    calls = {
        "rollback": engine.rollback("x", "1.0.0", [trace], "human_edit"),
        "retire": engine.retire("x", "1.0.0", [trace], "human_edit"),
    }
    for verb, call in calls.items():
        caught = await _capture(call)
        assert type(caught).__name__ == "UnsatisfiableSelectorError", f"{verb}: {type(caught).__name__}: {caught}"
        assert caught.requested == "x"
        assert "nonexistent" not in str(caught), f"{verb}: {caught}"
    assert _rows(tmp_path) == rows


def test_rest_answers_422_for_an_unresolvable_alias_row(tmp_path):
    trace = _store(tmp_path)
    rows = _rows(tmp_path)
    client = TestClient(create_app(store_root=tmp_path, workspace="alias-row"), raise_server_exceptions=False)

    bodies = {
        "/rollback": {"alias": "x", "version": "1.0.0", "trace_ids": [trace], "change_origin": "human_edit"},
        "/retire": {"alias": "x", "version": "1.0.0", "trace_ids": [trace], "change_origin": "human_edit"},
    }
    for route, body in bodies.items():
        response = client.post(route, json=body)
        assert response.status_code == 422, f"{route}: {response.status_code} {response.text}"
        assert response.json()["refusal_type"] == "UnsatisfiableSelectorError", f"{route}: {response.text}"
        assert "nonexistent" not in response.text, f"{route}: {response.text}"
    assert _rows(tmp_path) == rows
