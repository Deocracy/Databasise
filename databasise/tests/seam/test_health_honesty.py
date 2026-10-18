"""11-09-PLAN.md (LRAG-13, LRAG-14, LRAG-06; D-12, D-14, research Q5): GET /health writes nothing and
reports only facts it checked.

The real-driver cases run the v1 corpus driver under v1's own interpreter against the hermetic
loopback stub (skips only when ``v1/.venv/bin/python`` is absent), so no network and no real key.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from databasise.clients.builder import build_clients
from databasise.foreign import v1_corpus_adapter
from databasise.seam.rest import create_app
from databasise.tests.fixtures.v1_stub_server import (  # noqa: F401 - real_v1 is a fixture
    _OVERLAY_KEYS,
    real_v1,
    requires_v1,
    write_env_overlay,
)
from fastapi.testclient import TestClient

_WS = "h"
_ENGINE_KEYS = {"interpreter_present", "working_dir_present", "v1_reachable"}


@pytest.fixture
def clean_env(monkeypatch):
    # The adapter starts from os.environ, so the test process must not supply any v1 key itself.
    for key in _OVERLAY_KEYS:
        monkeypatch.delenv(key, raising=False)


@requires_v1
def test_health_on_a_fresh_root_through_the_real_driver_writes_nothing(real_v1, clean_env):  # noqa: F811
    store_root = real_v1.store_root
    app = create_app(store_root=store_root, workspace=_WS, clients=build_clients(real_v1.client_env))
    client = TestClient(app)
    before = sorted(store_root.rglob("*"))

    response = client.get("/health")

    assert response.status_code == 200, response.text
    assert sorted(store_root.rglob("*")) == before
    assert not (store_root / _WS / "lightrag-v1").exists()
    assert not (store_root / "jobs.db").exists()
    assert not (store_root / _WS / "text_chunks" / "kv.sqlite3").exists()
    assert not (store_root / _WS / "chunk_entity_relation" / "graph.cozo").exists()
    body = response.json()
    assert set(body["engine"]) == _ENGINE_KEYS
    assert body["engine"]["v1_reachable"] is True


@requires_v1
def test_health_names_the_missing_v1_key_and_no_value(real_v1, clean_env, monkeypatch, tmp_path):  # noqa: F811
    overlay = write_env_overlay(tmp_path / "blank-dim.env", real_v1.server.url, blank=("EMBEDDING_DIM",))
    monkeypatch.setattr(v1_corpus_adapter, "DEFAULT_V1_ENV_PARITY", overlay)
    app = create_app(store_root=real_v1.store_root, workspace=_WS, clients=build_clients(real_v1.client_env))

    response = TestClient(app).get("/health")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "degraded"
    assert body["engine"]["v1_reachable"] is False
    assert "EMBEDDING_DIM" in body["engine_reason"]
    for value in (real_v1.server.url, "stub-local-key", "stub-embed", "stub-llm", "JsonKVStorage"):
        assert value not in response.text
