"""16-05 (CONN-08): the operator trace list, GET /traces.

New API is reached over HTTP, so before the change each row fails by a plain ``AssertionError`` (the
route is a 404), never by an import error (16-RESEARCH Pitfall 1). Queries run on stub clients over
the synthetic naive store, so nothing reaches a provider.
"""

from __future__ import annotations

import inspect

import pytest

pytest.importorskip("fastapi")

from databasise.seam.rest import create_app
from databasise.tests.seam.test_rest_transport import _QUERY_BODY, _stub_clients
from fastapi.testclient import TestClient

_ITEM_KEYS = {"trace_reference", "created_at", "partial", "degraded", "stop_reason"}


def _operator_app(synthetic_naive_store):
    assert "operator" in inspect.signature(create_app).parameters, "create_app has no operator flag (CONN-01)"
    return create_app(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=_stub_clients(synthetic_naive_store),
        operator=True,
    )


def test_traces_list_newest_first_with_paging(synthetic_naive_store):
    client = TestClient(_operator_app(synthetic_naive_store))
    envelopes = []
    for _ in range(3):
        response = client.post("/query", json=_QUERY_BODY)
        assert response.status_code == 200, (response.status_code, response.text)
        envelopes.append(response.json())
    tokens = [e["trace_token"] for e in envelopes]

    response = client.get("/traces", params={"limit": 50})
    assert response.status_code == 200, (response.status_code, response.text)
    body = response.json()
    assert body.get("total") == 3, body
    items = body.get("items") or []
    assert [i.get("trace_reference") for i in items] == tokens[::-1], items
    stamps = [i.get("created_at") for i in items]
    assert stamps == sorted(stamps, reverse=True), stamps
    by_token = {e["trace_token"]: e for e in envelopes}
    for item in items:
        assert set(item) == _ITEM_KEYS, sorted(set(item) ^ _ITEM_KEYS)
        assert item["partial"] == by_token[item["trace_reference"]]["partial"], item
        resolved = client.post("/trace/resolve", json={"trace_reference": item["trace_reference"]})
        assert resolved.status_code == 200, (resolved.status_code, resolved.text)

    first = client.get("/traces", params={"limit": 2}).json()
    assert len(first.get("items") or []) == 2, first
    assert first.get("next_offset") == 2, first
    last = client.get("/traces", params={"limit": 2, "offset": 2}).json()
    assert len(last.get("items") or []) == 1, last
    assert last.get("next_offset") is None, last

    bad = client.get("/traces", params={"limit": 0})
    assert bad.status_code == 422, (bad.status_code, bad.text)
    assert "PageBoundsError" in bad.text, bad.text
