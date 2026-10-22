"""16-03 (CONN-05): GET /wirings on the operator surface lists one row per wiring, with the full node
count, the default arm and whether a capability selector reaches each arm (D-06).

New API is reached over HTTP, so before the change the row fails by a plain ``AssertionError`` (the
route is a 404), never by an import or type error (16-RESEARCH Pitfall 1).
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from databasise.seam.rest import create_app
from fastapi.testclient import TestClient

_FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "selector-resolution.json"
_ROW_KEYS = {
    "name",
    "wiring_id",
    "wiring_version",
    "title",
    "node_count",
    "effects",
    "provides",
    "harnesses",
    "default_eligible",
    "is_default",
    "reachable",
}
_NODE_COUNTS = {"naive": 7, "bypass": 1, "hybrid": 17, "local": 15, "global": 15, "hipporag": 14}
_LIGHTRAG_ARMS = ("naive", "bypass", "hybrid", "local", "global")


def _operator_app(tmp_path, **kw):
    assert "operator" in inspect.signature(create_app).parameters, "create_app has no operator flag (CONN-01)"
    return create_app(store_root=tmp_path, workspace="ws", operator=True, **kw)


def _wirings(app) -> list[dict]:
    response = TestClient(app).get("/wirings")
    assert response.status_code == 200, (response.status_code, response.text)
    rows = response.json()
    assert isinstance(rows, list), rows
    return rows


def test_wirings_lists_six_reachable_rows_matching_the_fixture(tmp_path):
    rows = _wirings(_operator_app(tmp_path))
    by_name = {row.get("name"): row for row in rows}
    assert len(rows) == 6 and set(by_name) == set(_NODE_COUNTS), [row.get("name") for row in rows]

    for name, row in by_name.items():
        assert set(row) == _ROW_KEYS, (name, sorted(set(row) ^ _ROW_KEYS))
        assert row.get("node_count") == _NODE_COUNTS[name], (name, row.get("node_count"))
        assert row.get("is_default") is (name == "naive"), name
        assert row.get("default_eligible") is (name != "hipporag"), name
        assert "codebase-memory" not in json.dumps(row), name

    assert len({row.get("wiring_id") for row in rows}) == 6
    assert len({by_name[name].get("title") for name in _LIGHTRAG_ARMS}) == 1

    fixture = json.loads(_FIXTURE.read_text(encoding="utf-8"))["reachable"]
    assert {name: row.get("reachable") for name, row in by_name.items()} == fixture
    assert all(row.get("reachable") is True for row in rows)


def test_reachable_is_computed_from_selector_resolution(tmp_path, monkeypatch):
    from databasise.seam import engine as engine_module

    real = engine_module.resolve_selector

    def naive_for_every_capability(selector, **kw):
        if selector is not None and selector.capability is not None:
            return real(None, **kw)
        return real(selector, **kw)

    monkeypatch.setattr(engine_module, "resolve_selector", naive_for_every_capability)
    reachable = {row.get("name"): row.get("reachable") for row in _wirings(_operator_app(tmp_path))}
    assert reachable == {name: name == "naive" for name in _NODE_COUNTS}, reachable


def test_an_injected_codebase_memory_mcp_part_adds_no_wirings_row(tmp_path):
    from databasise.parts.registry import default_registry
    from databasise.parts_core.declared_only import CODEBASE_MEMORY_MCP_PART

    registry = default_registry()
    registry.register(CODEBASE_MEMORY_MCP_PART)
    rows = _wirings(_operator_app(tmp_path, registry=registry))
    assert {row.get("name") for row in rows} == set(_NODE_COUNTS), [row.get("name") for row in rows]
    assert "codebase-memory" not in json.dumps(rows)
