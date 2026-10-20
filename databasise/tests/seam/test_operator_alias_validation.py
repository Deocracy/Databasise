"""14-08-PLAN.md Task 2 (LEDG-05, D-07): promote, rollback and retire all refuse an empty alias and a
hash-shaped alias (64-hex, ``sha256:`` plus 64-hex) as ``InvalidPromotionAliasError``, on the engine,
REST and MCP, writing no row. The alias check is the first step of the shared prologue. The file
imports only names that exist at the phase base and copies its own helpers, so it collects and fails
by assertion there.
"""

from __future__ import annotations

import json

import pytest

from databasise.ledger.ledger import Ledger, LedgerRecord
from databasise.seam.engine import Databasise
from databasise.seam.trace_store import TraceStore
from databasise.wirings.resolve import all_wirings

pytest.importorskip("fastapi")
from databasise.seam.rest import create_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

_BAD_ALIASES = ["", "f" * 64, "sha256:" + "f" * 64]


async def _capture(awaitable):
    try:
        return await awaitable
    except Exception as caught:  # noqa: BLE001 - the assertion is on the captured type
        return caught


def _seed_naive_trace(store_root) -> str:
    resolved = next(resolved for name, resolved in all_wirings() if name == "naive")
    node_ids = sorted(resolved.get("nodes", {}).keys())
    return TraceStore(store_root).persist(
        {
            "run_id": "fake-run-naive",
            "wiring_id": resolved.get("wiring_id"),
            "wiring_instance_hash": f"sha256:{'0' * 63}{len(node_ids) % 10}",
            "arm_id": "seam",
            "nodes": [{"node_id": node_id} for node_id in node_ids],
        }
    )


def _seed_row(store_root, alias: str) -> None:
    ledger = Ledger(store_root)
    ledger.append(
        LedgerRecord(
            mutation_id="naive",
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
            minted_version="1.0.0",
        )
    )
    ledger._conn.close()  # Ledger.close() does not exist at the phase base


def _rows(store_root) -> int:
    ledger = Ledger(store_root)
    try:
        return ledger._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]
    finally:
        ledger._conn.close()


def _prepare(tmp_path, alias: str):
    """A store with one row for ``alias`` (minted 1.0.0) and a valid naive trace."""
    _seed_row(tmp_path, alias)
    return Databasise(store_root=tmp_path, workspace="alias-validation"), _seed_naive_trace(tmp_path)


@pytest.mark.parametrize("alias", _BAD_ALIASES)
async def test_all_three_verbs_refuse_bad_aliases(tmp_path, alias):
    engine, trace = _prepare(tmp_path, alias)
    rows = _rows(tmp_path)

    calls = {
        "promote": engine.promote(alias, [trace], "human_edit"),
        "rollback": engine.rollback(alias, "1.0.0", [trace], "human_edit"),
        "retire": engine.retire(alias, "1.0.0", [trace], "human_edit"),
    }
    for verb, call in calls.items():
        caught = await _capture(call)
        assert type(caught).__name__ == "InvalidPromotionAliasError", (
            f"{verb} with alias {alias!r} gave {type(caught).__name__}: {caught}"
        )
        assert _rows(tmp_path) == rows, f"{verb} with alias {alias!r} wrote a row"


@pytest.mark.parametrize("alias", _BAD_ALIASES)
def test_rest_refuses_bad_aliases_on_all_three_routes(tmp_path, alias):
    engine, trace = _prepare(tmp_path, alias)
    rows = _rows(tmp_path)
    client = TestClient(create_app(store_root=tmp_path, workspace="alias-validation"), raise_server_exceptions=False)

    bodies = {
        "/promote": {"alias": alias, "trace_ids": [trace], "change_origin": "human_edit"},
        "/rollback": {"alias": alias, "version": "1.0.0", "trace_ids": [trace], "change_origin": "human_edit"},
        "/retire": {"alias": alias, "version": "1.0.0", "trace_ids": [trace], "change_origin": "human_edit"},
    }
    for route, body in bodies.items():
        response = client.post(route, json=body)
        assert response.status_code == 422, f"{route} with alias {alias!r}: {response.status_code} {response.text}"
        assert response.json()["refusal_type"] == "InvalidPromotionAliasError", f"{route}: {response.text}"
    assert _rows(tmp_path) == rows


@pytest.mark.parametrize("alias", _BAD_ALIASES)
async def test_mcp_refuses_bad_aliases_on_all_three_tools(tmp_path, alias):
    try:
        from databasise.mcp import create_server
        from databasise.mcp.server import RefusalToolError
    except ImportError:
        pytest.skip("the `mcp` extra is not installed")
    engine, trace = _prepare(tmp_path, alias)
    rows = _rows(tmp_path)
    server = create_server(store_root=tmp_path, workspace="alias-validation")

    arguments = {
        "promote": {"alias": alias, "trace_ids": [trace], "change_origin": "human_edit"},
        "rollback": {"alias": alias, "version": "1.0.0", "trace_ids": [trace], "change_origin": "human_edit"},
        "retire": {"alias": alias, "version": "1.0.0", "trace_ids": [trace], "change_origin": "human_edit"},
    }
    for tool, args in arguments.items():
        caught = await _capture(server.call_tool(tool, {"args": args}))
        assert isinstance(caught, RefusalToolError), f"{tool} with alias {alias!r}: {type(caught).__name__}: {caught}"
        assert json.loads(str(caught))["refusal_type"] == "InvalidPromotionAliasError", f"{tool}: {caught}"
    assert _rows(tmp_path) == rows
