"""11-07-PLAN.md Task 1 (LRAG-06, D-12, research Q3): a missing or unsupported v1 configuration key
reaches every corpus route as a named 503 that lists key names, never values.

Real driver under v1's interpreter (skips only when ``v1/.venv/bin/python`` is absent). The driver
refuses before it builds v1 or calls a model, so the sentinel values below never leave the process.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from databasise.foreign import CorpusOpSubprocessError, v1_corpus_adapter
from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.seam.rest import create_app
from databasise.tests.fixtures.v1_stub_server import requires_v1

_SENTINEL = "SENTINEL-VALUE"
_VALUE_KEYS = (
    "LLM_MODEL",
    "LLM_BINDING_API_KEY",
    "LLM_BINDING_HOST",
    "EMBEDDING_MODEL",
    "EMBEDDING_BINDING_HOST",
    "EMBEDDING_BINDING_API_KEY",
    "EMBEDDING_DIM",
)
_BACKENDS = {
    "LIGHTRAG_KV_STORAGE": "JsonKVStorage",
    "LIGHTRAG_GRAPH_STORAGE": "CozoGraphStorage",
    "LIGHTRAG_VECTOR_STORAGE": "FaissVectorDBStorage",
    "LIGHTRAG_DOC_STATUS_STORAGE": "JsonDocStatusStorage",
}
_STATUS_ROUTES = ("/corpus", "/corpus/counts", "/jobs/x")


def _overlay(path: Path, *, blank: tuple[str, ...] = (), backends: dict[str, str] | None = None) -> Path:
    lines = [f"{key}=" if key in blank else f"{key}={_SENTINEL}-{key.lower()}" for key in _VALUE_KEYS]
    lines += [f"{key}={value}" for key, value in {**_BACKENDS, **(backends or {})}.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def use_overlay(tmp_path, monkeypatch):
    # The adapter starts from os.environ, so the test process must not supply any key itself.
    for key in (*_VALUE_KEYS, *_BACKENDS):
        monkeypatch.delenv(key, raising=False)

    def _use(**kwargs) -> None:
        monkeypatch.setattr(v1_corpus_adapter, "DEFAULT_V1_ENV_PARITY", _overlay(tmp_path / "v1.env", **kwargs))

    return _use


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(store_root=tmp_path / "store", workspace="ws"), raise_server_exceptions=False)


def _assert_not_configured(response, *, missing: list[str], unsupported: list[str] = (), forbidden=()) -> None:
    assert response.status_code == 503, response.text
    assert len(response.content) < 1024
    body = response.json()
    assert body["refusal_type"] == "ForeignEngineRefusalError"
    assert body["failure_class"] == "V1NotConfigured"
    assert body["missing_keys"] == missing
    assert body["unsupported_keys"] == list(unsupported)
    for text in (_SENTINEL, "/home/", "Traceback", *forbidden):
        assert text not in response.text


@requires_v1
@pytest.mark.parametrize("route", _STATUS_ROUTES)
def test_a_status_route_names_the_missing_store_key(use_overlay, client, route):
    use_overlay(blank=("EMBEDDING_DIM", "LLM_MODEL"))
    _assert_not_configured(client.get(route), missing=["EMBEDDING_DIM"])


@requires_v1
def test_ingest_and_delete_also_name_the_missing_model_key(use_overlay, client):
    use_overlay(blank=("EMBEDDING_DIM", "LLM_MODEL"))
    expected = ["EMBEDDING_DIM", "LLM_MODEL"]
    _assert_not_configured(client.post("/documents", json={"document": {"text": "x"}}), missing=expected)
    _assert_not_configured(client.delete("/documents/x"), missing=expected)


@requires_v1
def test_an_unsupported_backend_is_named_without_its_value(use_overlay, client):
    use_overlay(backends={"LIGHTRAG_VECTOR_STORAGE": "OtherVectorStorage"})
    _assert_not_configured(
        client.get("/corpus"), missing=[], unsupported=["LIGHTRAG_VECTOR_STORAGE"], forbidden=("OtherVectorStorage",)
    )


@requires_v1
async def test_the_mcp_status_tool_carries_the_same_key_names(use_overlay, tmp_path):
    pytest.importorskip("mcp")
    from databasise.mcp import create_server
    from databasise.mcp._sdk import import_sdk

    tool_error = import_sdk("mcp.server.mcpserver.exceptions").ToolError
    use_overlay(blank=("EMBEDDING_DIM", "LLM_MODEL"))
    server = create_server(store_root=tmp_path / "store", workspace="ws")

    with pytest.raises(tool_error) as exc_info:
        await server.call_tool("status", {"args": {"scope": "corpus"}})

    text = str(exc_info.value)
    body = json.loads(text)
    assert body["failure_class"] == "V1NotConfigured"
    assert body["missing_keys"] == ["EMBEDDING_DIM"]
    assert _SENTINEL not in text and len(text) < 1024


def test_only_the_v1_not_configured_class_carries_key_lists():
    exc = ForeignEngineRefusalError(operation="ingest", cause=CorpusOpSubprocessError(1, "boom"))
    assert "missing_keys" not in vars(exc)
    assert "unsupported_keys" not in vars(exc)
