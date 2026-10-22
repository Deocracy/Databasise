"""16-04 (CONN-06, CONN-07): the operator ledger reads, GET /ledger/aliases and POST /ledger/history.

Both are read-only (``open_existing(read_only=True)``), so a fresh store root stays empty and no
sqlite connection to ``ledger.db`` stays open afterwards. New API is reached over HTTP, so before the
change each row fails by a plain ``AssertionError`` (the route is a 404), never by an import error
(16-RESEARCH Pitfall 1).
"""

from __future__ import annotations

import inspect
import os

import pytest

pytest.importorskip("fastapi")

from databasise.seam.rest import create_app
from databasise.tests.seam.test_rest_transport import _seed_trace
from fastapi.testclient import TestClient

_ALIAS_KEYS = {"alias", "active_version", "record_kind", "generation_ordinal", "created_at"}
_ABSENT_KEYS = {"mutation_id", "parent", "arm_instance_hashes"}


def _operator_app(store_root):
    assert "operator" in inspect.signature(create_app).parameters, "create_app has no operator flag (CONN-01)"
    return create_app(store_root=store_root, workspace="ws", operator=True)


def _open_ledger_fds(store_root) -> int:
    """How many of this process's file descriptors resolve to ``<store_root>/ledger.db``."""
    target = str(store_root / "ledger.db")
    count = 0
    for name in os.listdir("/proc/self/fd"):
        try:
            count += os.readlink(f"/proc/self/fd/{name}") == target
        except OSError:
            continue
    return count


def _promote(client, alias: str, arm: str, store_root) -> dict:
    response = client.post(
        "/promote",
        json={"alias": alias, "trace_ids": [_seed_trace(store_root, arm)], "change_origin": "human_edit"},
    )
    assert response.status_code == 200, (response.status_code, response.text)
    return response.json()


def test_aliases_lists_each_alias_once_and_creates_no_file(tmp_path):
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    response = TestClient(_operator_app(fresh)).get("/ledger/aliases")
    assert response.status_code == 200, (response.status_code, response.text)
    assert response.json() == []
    assert not (fresh / "ledger.db").exists()

    root = tmp_path / "populated"
    root.mkdir()
    client = TestClient(_operator_app(root))
    _promote(client, "a", "naive", root)
    _promote(client, "b", "naive", root)
    second_a = _promote(client, "a", "local", root)

    fds_before = _open_ledger_fds(root)
    response = client.get("/ledger/aliases")
    assert response.status_code == 200, (response.status_code, response.text)
    rows = response.json()
    assert _open_ledger_fds(root) == fds_before

    assert [row.get("alias") for row in rows] == ["a", "b"], rows
    for row in rows:
        assert set(row) == _ALIAS_KEYS, sorted(set(row) ^ _ALIAS_KEYS)
        assert row.get("record_kind") == "promotion"
        assert row.get("created_at"), row
        assert isinstance(row.get("generation_ordinal"), int), row
    assert rows[0].get("active_version") == second_a["version"]


def _history(client, alias: str, **page) -> object:
    return client.post("/ledger/history", json={"alias": alias, **page})


def test_history_flags_active_and_tombstoned_and_bounds_the_page(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    client = TestClient(_operator_app(root))
    v1 = _promote(client, "h", "naive", root)["version"]
    v2 = _promote(client, "h", "local", root)["version"]
    rolled = client.post(
        "/rollback",
        json={
            "alias": "h",
            "version": v1,
            "trace_ids": [_seed_trace(root, "naive")],
            "change_origin": "human_edit",
        },
    )
    assert rolled.status_code == 200, (rolled.status_code, rolled.text)
    v3 = rolled.json()["version"]
    retired = client.post(
        "/retire",
        json={
            "alias": "h",
            "version": v2,
            "trace_ids": [_seed_trace(root, "local")],
            "change_origin": "human_edit",
        },
    )
    assert retired.status_code == 200, (retired.status_code, retired.text)

    response = _history(client, "h", limit=50, offset=0)
    assert response.status_code == 200, (response.status_code, response.text)
    body = response.json()
    records = body.get("records")
    assert isinstance(records, list) and body.get("total") == 4, body
    assert body.get("next_offset") is None
    ordinals = [r.get("generation_ordinal") for r in records]
    assert ordinals == sorted(ordinals), ordinals
    for record in records:
        assert not _ABSENT_KEYS & set(record), sorted(_ABSENT_KEYS & set(record))
        assert isinstance(record.get("promotion_trace_ids"), list), record

    promote_v1, promote_v2, rollback_v3, tombstone = records
    assert (promote_v1["minted_version"], promote_v1["active"], promote_v1["tombstoned"]) == (v1, True, False)
    assert (promote_v2["minted_version"], promote_v2["active"], promote_v2["tombstoned"]) == (v2, False, True)
    assert (rollback_v3["minted_version"], rollback_v3["active"], rollback_v3["tombstoned"]) == (v3, True, False)
    assert tombstone["record_kind"] == "tombstone"
    assert (tombstone["targets_version"], tombstone["active"], tombstone["tombstoned"]) == (v2, False, True)

    low, high = _history(client, "h", limit=0), _history(client, "h", limit=101)
    assert (low.status_code, low.json().get("refusal_type")) == (422, "PageBoundsError"), low.text
    assert (high.status_code, high.json().get("refusal_type")) == (422, "PageSizeExceededError"), high.text

    first = _history(client, "h", limit=2, offset=0).json()
    assert len(first.get("records", [])) == 2 and first.get("next_offset") == 2, first
    last = _history(client, "h", limit=2, offset=2).json()
    assert len(last.get("records", [])) == 2 and last.get("next_offset") is None, last

    fresh = tmp_path / "fresh"
    fresh.mkdir()
    empty = _history(TestClient(_operator_app(fresh)), "nope")
    assert empty.status_code == 200, (empty.status_code, empty.text)
    assert empty.json() == {"records": [], "total": 0, "next_offset": None}
    assert not (fresh / "ledger.db").exists()
