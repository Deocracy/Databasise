"""16-01 (CONN-04): GET /info on the operator surface reports the version, the workspace and which
model clients were configured at startup, as presence booleans only (D-05).

New API is reached through ``inspect.signature`` so that, before the change, the row fails by a plain
``AssertionError`` rather than a ``TypeError`` (16-RESEARCH Pitfall 1).
"""

from __future__ import annotations

import inspect
import json

import pytest

pytest.importorskip("fastapi")

import databasise
from databasise.clients.builder import build_clients
from databasise.seam.rest import create_app
from fastapi.testclient import TestClient

_FAKE_ENV = {
    "LLM_BINDING_HOST": "http://127.0.0.1:9",
    "LLM_MODEL": "fake-model-x",
    "LLM_BINDING_API_KEY": "sk-fake-key",
    "EMBEDDING_BINDING_HOST": "http://127.0.0.1:9",
    "EMBEDDING_MODEL": "fake-model-x",
    "EMBEDDING_BINDING_API_KEY": "sk-fake-key",
}
_RERANK_ENV = {
    "RERANK_BINDING": "cohere",
    "RERANK_BINDING_HOST": "http://127.0.0.1:9",
    "RERANK_MODEL": "fake-model-x",
    "RERANK_BINDING_API_KEY": "sk-fake-key",
}


class _Recorder:
    """A stand-in client that records every attribute access and truth test."""

    def __init__(self) -> None:
        object.__setattr__(self, "record", [])

    def __getattr__(self, name):
        self.record.append(name)
        raise AttributeError(name)

    def __bool__(self):
        self.record.append("__bool__")
        return True


def _operator_app(tmp_path, **kw):
    assert "operator" in inspect.signature(create_app).parameters, "create_app has no operator flag (CONN-01)"
    return create_app(store_root=tmp_path, workspace="ws", operator=True, **kw)


def _info(tmp_path, clients):
    response = TestClient(_operator_app(tmp_path, clients=clients)).get("/info")
    assert response.status_code == 200, response.text
    return response.json(), response.text


def test_info_reports_version_workspace_and_client_presence(tmp_path):
    body, _ = _info(tmp_path / "none", None)
    assert body.get("version") == databasise.__version__
    assert body.get("workspace") == "ws"
    assert body.get("clients") == {"llm": False, "embedding": False, "rerank": False}

    llm, embedding = _Recorder(), _Recorder()
    body, _ = _info(tmp_path / "stub", {"llm": llm, "embedding": embedding})
    assert body.get("clients") == {"llm": True, "embedding": True, "rerank": False}
    assert llm.record == [] and embedding.record == [], "info() touched a client object"

    body, text = _info(tmp_path / "no_rerank", build_clients(dict(_FAKE_ENV)))
    assert body.get("clients") == {"llm": True, "embedding": True, "rerank": False}
    body, text = _info(tmp_path / "rerank", build_clients({**_FAKE_ENV, **_RERANK_ENV}))
    assert body.get("clients") == {"llm": True, "embedding": True, "rerank": True}

    serialized = json.dumps(body) + text
    for leaked in (str(tmp_path), "http", "fake-model-x", "sk-fake-key", "api_key"):
        assert leaked not in serialized, f"/info leaked {leaked!r}"
