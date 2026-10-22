"""16-06 (CONN-09): POST /promote/preview, the dry run of /promote.

New API is reached over HTTP, so before the change each row fails by a plain ``AssertionError`` (the
route is a 404), never by an import error (16-RESEARCH Pitfall 1). Every app runs on ``clients=None``
or stub clients, so nothing reaches a provider.
"""

from __future__ import annotations

import inspect

import pytest

pytest.importorskip("fastapi")

from databasise.seam.rest import create_app
from databasise.tests.seam.test_rest_transport import _seed_trace
from fastapi.testclient import TestClient

_QUERY = {"query": {"text": "Which films did Ed Wood direct?"}}


def _operator_app(store_root, workspace="preview"):
    assert "operator" in inspect.signature(create_app).parameters, "create_app has no operator flag (CONN-01)"
    return create_app(store_root=store_root, workspace=workspace, clients=None, operator=True)


def _ledger_files(store_root) -> list[str]:
    return sorted(p.name for p in store_root.iterdir() if p.name.startswith("ledger.db"))


def test_preview_matches_what_promote_mints_and_refuses(store_root, synthetic_naive_store):
    # (1) complete trace on a fresh root: promotable, 1.0.0, no ledger written, /promote mints 1.0.0.
    fresh = store_root / "fresh"
    fresh.mkdir()
    client = TestClient(_operator_app(fresh))
    trace = _seed_trace(fresh, "naive")
    body = {"alias": "p", "trace_ids": [trace], "change_origin": "human_edit"}

    preview = client.post("/promote/preview", json=body)
    assert preview.status_code == 200, (preview.status_code, preview.text)
    data = preview.json()
    assert data.get("promotable") is True, data
    assert data.get("next_version") == "1.0.0", data
    assert data.get("arm") == "naive", data
    assert data.get("mutation_class"), data
    # (3) a preview leaves a fresh root without a ledger.
    assert _ledger_files(fresh) == [], _ledger_files(fresh)

    promoted = client.post("/promote", json=body)
    assert promoted.status_code == 200, (promoted.status_code, promoted.text)
    assert promoted.json()["version"] == data["next_version"], (promoted.json(), data)

    # (2) a real partial trace: preview reports the named reason, /promote refuses with the same name.
    root = synthetic_naive_store["store_root"]
    partial_client = TestClient(_operator_app(root, synthetic_naive_store["workspace"]))
    query = partial_client.post("/query", json=_QUERY)
    assert query.status_code == 200, (query.status_code, query.text)
    assert query.json()["partial"] is True, query.json()
    partial_body = {"alias": "q", "trace_ids": [query.json()["trace_token"]], "change_origin": "human_edit"}

    preview = partial_client.post("/promote/preview", json=partial_body)
    assert preview.status_code == 200, (preview.status_code, preview.text)
    assert preview.json().get("promotable") is False, preview.json()
    assert preview.json().get("reason") == "PartialRunEvidenceError", preview.json()
    refused = partial_client.post("/promote", json=partial_body)
    assert refused.status_code == 422, (refused.status_code, refused.text)
    assert refused.json().get("refusal_type") == "PartialRunEvidenceError", refused.json()
    assert _ledger_files(root) == [], _ledger_files(root)

    # (4) an unknown trace id is the same 404 from preview as from /promote.
    unknown = {"alias": "p", "trace_ids": ["no-such-trace"], "change_origin": "human_edit"}
    preview = client.post("/promote/preview", json=unknown)
    assert preview.status_code == 404, (preview.status_code, preview.text)
    assert preview.json().get("refusal_type") == "UnknownTraceReferenceError", preview.json()
