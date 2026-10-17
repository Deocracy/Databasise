"""10-01-PLAN.md Task 2 (STOR-01, D-01, D-02): overlapping calls on one graph namespace share one
reference-counted pycozo ``Client``; a ``graph.cozo`` held by another OS process is refused by name
(``GraphStoreBusyError`` at the store, ``StoreBusyError`` / HTTP 409 at the seam), never a 500.

``hold_graph_in_subprocess`` is imported by 10-07's health tests.
"""

from __future__ import annotations

import asyncio
import contextlib
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

from databasise.seam.engine import Databasise
from databasise.seam.evidence import EvidenceRef
from databasise.seam.query import QueryObject
from databasise.stores import graph as graph_module
from databasise.stores.graph import CozoGraphStore
from databasise.tests.seam.conftest import synthetic_naive_store  # noqa: F401 — fixture

_HOLDER = """\
import sys
from pycozo.client import Client

client = Client("rocksdb", sys.argv[1], dataframe=False)
print("ready", flush=True)
sys.stdin.read()
client.close()
"""


@contextlib.contextmanager
def hold_graph_in_subprocess(db_path: Path):
    """Hold ``db_path`` (a ``graph.cozo`` path) open from a second OS process until the block exits."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    script = Path(tempfile.mkdtemp()) / "hold_graph.py"
    script.write_text(_HOLDER)
    proc = subprocess.Popen(
        [sys.executable, "-I", str(script), str(db_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        ready: list[str] = []
        reader = threading.Thread(target=lambda: ready.append(proc.stdout.readline()), daemon=True)
        reader.start()
        reader.join(30)
        if not ready or ready[0].strip() != "ready":
            raise RuntimeError("graph holder subprocess did not report ready within 30 s")
        yield proc
    finally:
        with contextlib.suppress(Exception):
            proc.stdin.close()
        try:
            proc.wait(10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def _entries() -> dict:
    return graph_module._ClientRegistry._entries


def _key(store_root: Path, workspace: str, namespace: str) -> str:
    return str((Path(store_root) / workspace / namespace / "graph.cozo").resolve())


@pytest.fixture
def no_v1_health(monkeypatch):
    from databasise.tests.seam.test_rest_corpus_endpoints import _patch_status_and_health

    _patch_status_and_health(monkeypatch)


_CHUNK_1 = EvidenceRef(ref="chunk-1", namespace="chunks", kind="text_chunk")


async def test_overlapping_engine_calls_complete_while_the_graph_is_held_in_process(
    synthetic_naive_store, no_v1_health  # noqa: F811
):
    root, ws = synthetic_naive_store["store_root"], synthetic_naive_store["workspace"]
    held = CozoGraphStore("chunk_entity_relation", ws, root)
    try:
        engine = Databasise(store_root=root, workspace=ws)
        envelope, record, report = await asyncio.gather(
            engine.query(QueryObject(text="x")),
            engine.resolve_evidence(_CHUNK_1),
            engine.health(),
        )
        assert envelope is not None
        assert record is not None
        assert report.stores["graph"] is True
    finally:
        await held.finalize()


async def test_rest_calls_return_200_while_the_graph_is_held_in_process(
    synthetic_naive_store, no_v1_health  # noqa: F811
):
    from fastapi.testclient import TestClient

    from databasise.seam.rest import create_app

    root, ws = synthetic_naive_store["store_root"], synthetic_naive_store["workspace"]
    held = CozoGraphStore("chunk_entity_relation", ws, root)
    try:
        client = TestClient(create_app(store_root=root, workspace=ws), raise_server_exceptions=False)
        assert client.post("/query", json={"query": {"text": "x"}}).status_code == 200
        resolved = client.post("/evidence/resolve", json=_CHUNK_1.model_dump())
        assert resolved.status_code == 200
        assert client.get("/health").status_code == 200
    finally:
        await held.finalize()


async def test_two_instances_share_one_client_but_keep_separate_buffers(store_root):
    a = CozoGraphStore("graph", "ws", store_root)
    b = CozoGraphStore("graph", "ws", store_root)
    key = _key(store_root, "ws", "graph")
    try:
        assert a._client is b._client
        assert _entries()[key].refcount == 2

        await a.upsert_node("n", {})
        assert await b.has_node("n") is False

        await b.upsert_node("m", {})
        await a.drop_pending_index_ops()
        assert b._pending_node_puts == {"m": {}}

        await a.finalize()
        assert await b.has_node("m") is True
        assert key in _entries()
    finally:
        await b.finalize()
    assert key not in _entries()


async def test_finalize_twice_releases_the_client_once(store_root):
    a = CozoGraphStore("graph", "ws", store_root)
    b = CozoGraphStore("graph", "ws", store_root)
    key = _key(store_root, "ws", "graph")
    await a.finalize()
    await a.finalize()
    assert _entries()[key].refcount == 1
    await b.finalize()
    assert key not in _entries()


def test_a_store_open_held_by_another_process_raises_graph_store_busy(store_root):
    db_path = Path(store_root) / "ws" / "graph" / "graph.cozo"
    with hold_graph_in_subprocess(db_path):
        with pytest.raises(graph_module.GraphStoreBusyError) as info:
            CozoGraphStore("graph", "ws", store_root)
    assert str(store_root) not in str(info.value)
    assert _key(store_root, "ws", "graph") not in _entries()


async def test_engine_and_rest_refuse_a_graph_held_by_another_process_with_store_busy(
    synthetic_naive_store, no_v1_health  # noqa: F811
):
    from fastapi.testclient import TestClient

    from databasise.seam.refusals import StoreBusyError
    from databasise.seam.rest import create_app

    root, ws = synthetic_naive_store["store_root"], synthetic_naive_store["workspace"]
    with hold_graph_in_subprocess(Path(root) / ws / "chunk_entity_relation" / "graph.cozo"):
        engine = Databasise(store_root=root, workspace=ws)
        with pytest.raises(StoreBusyError) as info:
            await engine.query(QueryObject(text="x"))
        assert info.value.store_kind == "graph"

        client = TestClient(create_app(store_root=root, workspace=ws), raise_server_exceptions=False)
        response = client.post("/query", json={"query": {"text": "x"}})
    assert response.status_code == 409
    body = response.json()
    assert body["refusal_type"] == "StoreBusyError"
    assert body["store_kind"] == "graph"
    assert str(root) not in response.text
    assert "chunk_entity_relation" not in response.text
