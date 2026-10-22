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
