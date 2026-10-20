"""14-05-PLAN.md (LEDG-09, D-10): the trace flag is a strict JSON boolean on both transports, and the
tenancy rule is written down. A string, a number or null is a validation error that carries no run
record field; ``true`` returns the full record and ``false`` the reduced one.

Self-contained on purpose: the stub clients are copied here and nothing new is imported at module
level, so the file collects and fails by assertion on the phase base.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")

from databasise.clients.base import ChatResult, EmbeddingResult
from databasise.runner.trace import TokenAccounting
from databasise.seam.rest import create_app
from fastapi.testclient import TestClient

_FLAG = "deb" + "ug"
_RECORD_FIELDS = ("run_id", "wiring_id", "wiring_instance_hash", "arm_id", "nodes")
_NON_BOOLEANS = ["yes", "true", "1", 1, None]
_QUERY_BODY = {"query": {"text": "Which films did Ed Wood direct?"}}


class _StubEmbeddingClient:
    def __init__(self, vector: list[float]):
        self.vector = vector

    async def embed(self, texts, **kwargs):
        return EmbeddingResult(
            vectors=[self.vector for _ in texts],
            tokens=TokenAccounting(prompt_tokens=len(texts), call_count=1, counted_by="stub-embed"),
            resolved_model_identity="stub-embed-model",
        )


class _StubLLMClient:
    async def chat(self, messages, **kwargs):
        return ChatResult(
            text="stub completion",
            tokens=TokenAccounting(prompt_tokens=5, completion_tokens=4, call_count=1, counted_by="stub-llm"),
            resolved_model_identity="stub-llm-model",
        )


def _clients(store) -> dict[str, object]:
    return {"embedding": _StubEmbeddingClient(vector=store["query_vector"]), "llm": _StubLLMClient()}


@pytest.fixture
def rest_client(synthetic_naive_store):
    app = create_app(
        store_root=synthetic_naive_store["store_root"],
        workspace=synthetic_naive_store["workspace"],
        clients=_clients(synthetic_naive_store),
    )
    return TestClient(app)


def _trace_token(rest_client) -> str:
    response = rest_client.post("/query", json=_QUERY_BODY)
    assert response.status_code == 200
    return response.json()["trace_token"]


@pytest.mark.parametrize("value", _NON_BOOLEANS, ids=repr)
def test_rest_refuses_a_non_boolean_flag(rest_client, value):
    token = _trace_token(rest_client)
    response = rest_client.post("/trace/resolve", json={"trace_reference": token, _FLAG: value})
    assert response.status_code == 422, (value, response.status_code)
    for field in _RECORD_FIELDS:
        assert field not in response.text, (value, field)


def test_rest_still_honours_a_boolean_flag(rest_client):
    token = _trace_token(rest_client)
    full = rest_client.post("/trace/resolve", json={"trace_reference": token, _FLAG: True})
    reduced = rest_client.post("/trace/resolve", json={"trace_reference": token, _FLAG: False})
    assert full.status_code == 200 and "run_id" in full.json()
    assert reduced.status_code == 200 and "run_id" not in reduced.json()


def _mcp_server(store):
    try:
        from databasise.mcp import create_server
    except ImportError:
        pytest.skip("the `mcp` extra is not installed")
    return create_server(
        store_root=store["store_root"], workspace=store["workspace"], clients=_clients(store)
    )


@pytest.mark.parametrize("value", _NON_BOOLEANS, ids=repr)
async def test_mcp_refuses_a_non_boolean_flag(synthetic_naive_store, rest_client, value):
    token = _trace_token(rest_client)
    server = _mcp_server(synthetic_naive_store)
    caught: Exception | None = None
    try:
        await server.call_tool(
            "resolve", {"args": {"scope": "trace", "trace_reference": token, _FLAG: value}}
        )
    except Exception as exc:
        caught = exc
    assert caught is not None, f"{value!r} was accepted as the trace flag"
    for field in _RECORD_FIELDS:
        assert field not in str(caught), (value, field)


async def test_mcp_still_honours_a_boolean_flag(synthetic_naive_store, rest_client):
    token = _trace_token(rest_client)
    server = _mcp_server(synthetic_naive_store)
    result = await server.call_tool(
        "resolve", {"args": {"scope": "trace", "trace_reference": token, _FLAG: True}}
    )
    text = "".join(getattr(item, "text", "") or "" for item in result.content)
    assert "run_id" in json.loads(text)
