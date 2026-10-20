"""14-08-PLAN.md Task 2 (LEDG-01, D-01, D-03): no operator verb answers 500 or raises
``AssertionError`` for a trace from a partial run.

``promote`` refuses a partial trace by name. ``rollback`` and ``retire`` accept it (M-06 option (b)):
the arm comes from the record's own ``arm_id`` when it names a wiring, and a partial record whose arm
cannot be identified refuses by name, never as ``UnknownTraceReferenceError``. The file imports only
names that exist at the phase base and copies its own stubs, so it collects and fails by assertion
there.
"""

from __future__ import annotations

import json

import pytest

from databasise.ledger.ledger import Ledger
from databasise.seam.engine import Databasise
from databasise.seam.query import QueryObject
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


def _node_ids(arm_name: str) -> list[str]:
    resolved = next(resolved for name, resolved in all_wirings() if name == arm_name)
    return sorted(resolved.get("nodes", {}).keys())


def _seed(store_root, arm_name: str) -> str:
    """A complete, old-format record (no status, no partial, ``arm_id`` ``seam``) for ``arm_name``."""
    return TraceStore(store_root).persist(
        {
            "run_id": f"fake-run-{arm_name}",
            "wiring_id": f"lightrag-{arm_name}",
            "wiring_instance_hash": f"sha256:{'0' * 63}{len(_node_ids(arm_name)) % 10}",
            "arm_id": "seam",
            "nodes": [{"node_id": node_id} for node_id in _node_ids(arm_name)],
        }
    )


def _persist(store_root, **fields) -> str:
    record = {"run_id": "fake-run", "wiring_id": "x", "wiring_instance_hash": f"sha256:{'a' * 64}"}
    record.update(fields)
    return TraceStore(store_root).persist(record)


def _rows(store_root) -> int:
    return Ledger(store_root)._conn.execute("SELECT COUNT(*) FROM ledger").fetchone()[0]


def _no_ledger(store_root) -> bool:
    return not any((store_root / name).exists() for name in ("ledger.db", "ledger.db-wal", "ledger.db-shm"))


async def _real_partial_naive(synthetic_naive_store):
    """A naive query with ``clients=None``: the embedder-query node fails, the run is partial."""
    root, workspace = synthetic_naive_store["store_root"], synthetic_naive_store["workspace"]
    engine = Databasise(store_root=root, workspace=workspace, clients=None)
    envelope = await engine.query(QueryObject(text="q"))
    assert envelope.partial is True and envelope.trace_token
    return engine, root, envelope.trace_token


async def _two_generations(engine, root, alias):
    first = await engine.promote(alias, [_seed(root, "naive")], "human_edit")
    second = await engine.promote(alias, [_seed(root, "hybrid")], "human_edit")
    return first.version, second.version


async def test_promote_refuses_a_real_partial_trace(synthetic_naive_store):
    engine, root, token = await _real_partial_naive(synthetic_naive_store)

    caught = await _capture(engine.promote("alias-p", [token], "human_edit"))

    assert type(caught).__name__ == "PartialRunEvidenceError", f"{type(caught).__name__}: {caught}"
    assert _no_ledger(root), "a refused promote created ledger.db"


async def test_rollback_and_retire_accept_a_real_partial_trace(synthetic_naive_store):
    engine, root, token = await _real_partial_naive(synthetic_naive_store)
    first, second = await _two_generations(engine, root, "alias-r")
    partial_hash = TraceStore(root).resolve(token)["wiring_instance_hash"]

    rolled = await _capture(engine.rollback("alias-r", first, [token], "human_edit"))
    assert getattr(rolled, "record_kind", None) == "rollback", f"{type(rolled).__name__}: {rolled}"
    assert Ledger(root).by_alias("alias-r").arm_instance_hashes == [partial_hash]

    retired = await _capture(engine.retire("alias-r", second, [token], "human_edit"))
    assert getattr(retired, "record_kind", None) == "tombstone", f"{type(retired).__name__}: {retired}"


async def test_a_hipporag_partial_record_is_accepted_by_rollback_and_retire(tmp_path):
    engine = Databasise(store_root=tmp_path, workspace="partial-evidence")
    first, second = await _two_generations(engine, tmp_path, "alias-h")
    token = _persist(
        tmp_path,
        arm_id="hipporag",
        partial=True,
        nodes=[
            {"node_id": "chunk-embed", "status": "completed"},
            {"node_id": "fact-score", "status": "failed"},
        ],
    )

    rolled = await _capture(engine.rollback("alias-h", first, [token], "human_edit"))
    assert getattr(rolled, "record_kind", None) == "rollback", f"{type(rolled).__name__}: {rolled}"
    retired = await _capture(engine.retire("alias-h", second, [token], "human_edit"))
    assert getattr(retired, "record_kind", None) == "tombstone", f"{type(retired).__name__}: {retired}"


async def test_an_unidentifiable_partial_record_is_refused_by_name(tmp_path):
    engine = Databasise(store_root=tmp_path, workspace="partial-evidence")
    first, second = await _two_generations(engine, tmp_path, "alias-u")
    rows = _rows(tmp_path)
    partial = _persist(tmp_path, arm_id="seam", partial=True, nodes=[{"node_id": "embedder-query", "status": "failed"}])
    complete = _persist(tmp_path, arm_id="seam", nodes=[{"node_id": "no-such-node"}])

    for verb, call in (
        ("rollback", engine.rollback("alias-u", first, [partial], "human_edit")),
        ("retire", engine.retire("alias-u", second, [partial], "human_edit")),
    ):
        caught = await _capture(call)
        assert type(caught).__name__ == "PartialRunEvidenceError", f"{verb}: {type(caught).__name__}: {caught}"
        assert caught.trace_ids == [partial]
    assert _rows(tmp_path) == rows

    for verb, call in (
        ("rollback", engine.rollback("alias-u", first, [complete], "human_edit")),
        ("retire", engine.retire("alias-u", second, [complete], "human_edit")),
    ):
        caught = await _capture(call)
        assert type(caught).__name__ == "UnknownTraceReferenceError", f"{verb}: {type(caught).__name__}: {caught}"
    assert _rows(tmp_path) == rows


async def test_no_verb_returns_500_for_partial_evidence(synthetic_naive_store):
    engine, root, token = await _real_partial_naive(synthetic_naive_store)
    first, second = await _two_generations(engine, root, "alias-s")
    unidentifiable = _persist(root, arm_id="seam", partial=True, nodes=[{"node_id": "embedder-query", "status": "failed"}])
    client = TestClient(
        create_app(store_root=root, workspace=synthetic_naive_store["workspace"], clients=None),
        raise_server_exceptions=False,
    )
    rows = _rows(root)

    response = client.post("/promote", json={"alias": "alias-s", "trace_ids": [token], "change_origin": "human_edit"})
    assert response.status_code == 422, response.text
    assert response.json()["refusal_type"] == "PartialRunEvidenceError", response.text
    assert response.json()["trace_ids"] == [token]

    for route, version in (("/rollback", first), ("/retire", second)):
        response = client.post(
            route,
            json={"alias": "alias-s", "version": version, "trace_ids": [unidentifiable], "change_origin": "human_edit"},
        )
        assert response.status_code == 422, f"{route}: {response.status_code} {response.text}"
        assert response.json()["refusal_type"] == "PartialRunEvidenceError", f"{route}: {response.text}"
    assert _rows(root) == rows


async def test_the_mcp_promote_tool_reports_partial_evidence(synthetic_naive_store):
    try:
        from databasise.mcp import create_server
        from databasise.mcp.server import RefusalToolError
    except ImportError:
        pytest.skip("the `mcp` extra is not installed")
    engine, root, token = await _real_partial_naive(synthetic_naive_store)
    server = create_server(store_root=root, workspace=synthetic_naive_store["workspace"], clients=None)

    caught = await _capture(
        server.call_tool(
            "promote", {"args": {"alias": "alias-m", "trace_ids": [token], "change_origin": "human_edit"}}
        )
    )

    assert isinstance(caught, RefusalToolError), f"{type(caught).__name__}: {caught}"
    assert json.loads(str(caught))["refusal_type"] == "PartialRunEvidenceError"
