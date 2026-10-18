"""11-09-PLAN.md (LRAG-13, LRAG-14, LRAG-06; D-12, D-14, research Q5): GET /health writes nothing and
reports only facts it checked.

The real-driver cases run the v1 corpus driver under v1's own interpreter against the hermetic
loopback stub (skips only when ``v1/.venv/bin/python`` is absent), so no network and no real key.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("fastapi")

import databasise.seam.engine as engine_module
from databasise.clients.builder import build_clients
from databasise.foreign import v1_corpus_adapter
from databasise.seam.engine import Databasise
from databasise.seam.rest import create_app
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore
from databasise.tests.fixtures.v1_stub_server import (  # noqa: F401 - real_v1 is a fixture
    _OVERLAY_KEYS,
    real_v1,
    requires_v1,
    write_env_overlay,
)
from databasise.tests.seam.test_corpus_status import _make_fake_run_corpus_op
from fastapi.testclient import TestClient

_WS = "h"
_ENGINE_KEYS = {"interpreter_present", "working_dir_present", "v1_reachable"}
_BOTH_CLIENTS = {"llm": object(), "embedding": object()}


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


# --------------------------------------------------------------------------------------------- #
# Task 2 (LRAG-14): ok needs model clients; facts survive a driver failure; a probe failure degrades.
# --------------------------------------------------------------------------------------------- #


async def _populate_every_namespace(store_root: Path) -> None:
    """Every LightRAG and HippoRAG namespace in ``_HEALTH_PROBES`` on disk, plus the v1 working dir."""
    for kind, namespace in engine_module._HEALTH_PROBES:
        if kind == "kv":
            store = SqliteKVStore(namespace=namespace, workspace=_WS, store_root=store_root)
            await store.upsert({"c1": {"content": "x"}})
        elif kind == "graph":
            store = CozoGraphStore(namespace, _WS, store_root)
            await store.upsert_node("n1", {"entity_type": "x"})
        else:
            store = FaissVectorStore(namespace=namespace, workspace=_WS, store_root=store_root)
            await store.upsert(ids=["c1"], embeddings=np.array([[1.0, 0.0, 0.0]]), metadatas=[{"content": "x"}])
        await store.index_done_callback()
        await store.finalize()
    (store_root / _WS / "lightrag-v1").mkdir(parents=True)


@pytest.fixture
def interpreter_present(tmp_path, monkeypatch):
    fake = tmp_path / "python"
    fake.touch()
    monkeypatch.setattr(engine_module, "DEFAULT_V1_INTERPRETER", fake)


async def test_status_is_ok_only_with_both_model_clients(store_root, monkeypatch, interpreter_present):
    await _populate_every_namespace(store_root)
    monkeypatch.setattr(engine_module, "run_corpus_op", _make_fake_run_corpus_op())

    bare = await Databasise(store_root=store_root, workspace=_WS, clients=None).health()
    wired = await Databasise(store_root=store_root, workspace=_WS, clients=_BOTH_CLIENTS).health()

    assert set(bare.stores.values()) == {"ok"}
    assert bare.status == "degraded"
    assert bare.engine_reason == "model clients not configured"
    assert wired.status == "ok"
    assert wired.engine_reason is None


def test_rest_health_without_clients_is_degraded(store_root, monkeypatch, interpreter_present):
    import asyncio

    asyncio.run(_populate_every_namespace(store_root))
    monkeypatch.setattr(engine_module, "run_corpus_op", _make_fake_run_corpus_op())

    body = TestClient(create_app(store_root=store_root, workspace=_WS, clients=None)).get("/health").json()

    assert body["status"] == "degraded"
    assert body["engine_reason"] == "model clients not configured"


async def test_a_driver_failure_keeps_the_working_dir_fact(store_root, monkeypatch):
    (store_root / _WS / "lightrag-v1").mkdir(parents=True)

    def _raising(*_args, **_kwargs):
        raise RuntimeError("simulated foreign engine failure")

    monkeypatch.setattr(engine_module, "run_corpus_op", _raising)

    report = await Databasise(store_root=store_root, workspace=_WS, clients=_BOTH_CLIENTS).health()

    assert report.engine["working_dir_present"] is True
    assert report.engine["v1_reachable"] is False
    assert "v1 unreachable" in report.engine_reason
    assert report.status == "degraded"


def test_a_raising_probe_is_a_200_degraded_report_with_that_store_corrupted(store_root, monkeypatch):
    def _finalize_failed(_path):
        raise RuntimeError("finalize failed")

    monkeypatch.setitem(engine_module._PROBES, "kv", _finalize_failed)
    monkeypatch.setattr(engine_module, "run_corpus_op", _make_fake_run_corpus_op())
    client = TestClient(create_app(store_root=store_root, workspace=_WS), raise_server_exceptions=False)

    response = client.get("/health")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "degraded"
    assert body["stores"]["kv:text_chunks"] == "corrupted"
    assert {"kv:hipporag-text-chunks", "graph:hipporag-graph"} <= set(body["stores"])
