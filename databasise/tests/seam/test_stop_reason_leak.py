"""WIRE-03 (D-05): a consumer-visible ``stop_reason`` or ``degradation_reason`` is one of the closed
node-free codes. It carries no node id, no ``name@version`` and no exception class name; node detail
stays in the debug-only ``cross_process_failure_cause``. These are the construction legs (REST
envelope and non-debug trace); the gate legs follow in 13-08.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from databasise.parts.registry import default_registry
from databasise.seam.rest import create_app
from fastapi.testclient import TestClient

_FORBIDDEN = (
    "node '",
    "embedder-query",
    "fact-score",
    "chunk-vector",
    "NodeExecutionError",
    "ClientNotWiredError",
    *default_registry().keys(),
)
_HIPPORAG_SELECTOR = {"capability": ["reads_graph", "reads_kv"]}


def _assert_node_free(reasons: dict[str, str | None]) -> None:
    for field, text in reasons.items():
        assert text, f"{field} is empty on a run that could not complete"
        for fragment in _FORBIDDEN:
            assert fragment not in text, f"{field}={text!r} carries {fragment!r}"


def _query(client: TestClient, body: dict) -> dict:
    response = client.post("/query", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _reasons(envelope: dict) -> dict[str, str | None]:
    return {"stop_reason": envelope["stop_reason"], "degradation_reason": envelope["degradation_reason"]}


def test_a_naive_query_without_clients_returns_node_free_reasons(synthetic_naive_store):
    store = synthetic_naive_store
    client = TestClient(create_app(store_root=store["store_root"], workspace=store["workspace"], clients=None))

    envelope = _query(client, {"query": {"text": "x"}})

    assert envelope["partial"] is True
    _assert_node_free(_reasons(envelope))


def test_the_non_debug_trace_reasons_are_node_free(synthetic_naive_store):
    store = synthetic_naive_store
    client = TestClient(create_app(store_root=store["store_root"], workspace=store["workspace"], clients=None))
    envelope = _query(client, {"query": {"text": "x"}})

    response = client.post("/trace/resolve", json={"trace_reference": envelope["trace_token"], "debug": False})

    assert response.status_code == 200, response.text
    _assert_node_free(_reasons(response.json()))


def test_a_hipporag_query_on_a_fresh_root_returns_node_free_reasons(store_root):
    client = TestClient(create_app(store_root=store_root, workspace="leak-fresh", clients=None))

    envelope = _query(client, {"query": {"text": "x"}, "selector": _HIPPORAG_SELECTOR})

    _assert_node_free(_reasons(envelope))
