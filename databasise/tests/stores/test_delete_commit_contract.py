"""STOR-07 (Phase 10 D-08, research Q4): a delete commits all of itself or none of it.

``Databasise.delete_document`` builds its stores from the resolved delete wiring's
``store_namespaces``, commits every store through prepare-all/commit-all when the delete succeeds,
and drops every store's pending ops when the delete node raises or reports ``status == "fail"``.
``FaissVectorStore.delete_by_ids`` buffers until the flush, so a drop reverts it like the other
stores. No HippoRAG delete wiring ships yet (research Pitfall 22), so the engine tests swap in a
fixture delete wiring that declares the ``fx-*`` namespaces.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import databasise.seam.engine as engine_module
import pytest
from databasise.parts.schema import NodeContext
from databasise.parts_core.declared_only import LIGHTRAG_FULL_DELETE_PART
from databasise.runner.trace import TokenAccounting
from databasise.seam.engine import Databasise
from databasise.seam.refusals import ForeignEngineRefusalError
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore
from databasise.tests.seam.test_delete_document import (
    _make_engine,
    _make_stub_full_delete_body,
    _registry_with,
)

_WS = "test-delete"
_DELETE_WIRING = Path(engine_module.__file__).resolve().parents[1] / "wirings" / "lightrag" / "corpus-delete.json"
_FX_NAMESPACES = {"kv": "fx-text", "graph": "fx-graph"}


async def _seed(store_root: Path) -> None:
    kv = SqliteKVStore(namespace="fx-text", workspace=_WS, store_root=store_root)
    await kv.upsert({"doc-1:0": {"content": "chunk zero"}})
    await kv.index_done_callback()
    await kv.finalize()
    vector = FaissVectorStore(namespace="fx-chunks", workspace=_WS, store_root=store_root)
    await vector.upsert(ids=["doc-1:0"], embeddings=[[1.0, 0.0]], metadatas=[{"text": "chunk zero"}])
    await vector.index_done_callback()
    await vector.finalize()
    graph = CozoGraphStore(namespace="fx-graph", workspace=_WS, store_root=store_root)
    await graph.upsert_node("doc-1", {"kind": "document"})
    await graph.index_done_callback()
    await graph.finalize()


async def _present(store_root: Path) -> tuple[bool, bool, bool]:
    """(kv, vector, graph) presence of the seeded records, read through freshly opened stores."""
    kv = SqliteKVStore(namespace="fx-text", workspace=_WS, store_root=store_root)
    vector = FaissVectorStore(namespace="fx-chunks", workspace=_WS, store_root=store_root)
    graph = CozoGraphStore(namespace="fx-graph", workspace=_WS, store_root=store_root)
    try:
        return (
            await kv.get_by_id("doc-1:0") is not None,
            vector.get_by_id("doc-1:0") is not None,
            await graph.has_node("doc-1"),
        )
    finally:
        for store in (kv, vector, graph):
            await store.finalize()


def _fixture_delete_body(outcome: str):
    async def _body(ctx: NodeContext) -> dict[str, Any]:
        await ctx.stores["kv"].delete(["doc-1:0"])
        await ctx.stores["vector"].select("fx-chunks").delete_by_ids(["doc-1:0"])
        await ctx.stores["graph"].delete_node("doc-1")
        if outcome == "raise":
            raise RuntimeError("delete failed")
        return {"status": outcome, "message": "", "tokens": TokenAccounting(counted_by="unbudgetable")}

    return _body


def _fixture_engine(store_root: Path, monkeypatch, outcome: str) -> Databasise:
    part = dataclasses.replace(
        LIGHTRAG_FULL_DELETE_PART,
        body=_fixture_delete_body(outcome),
        effects=[*LIGHTRAG_FULL_DELETE_PART.effects, "writes_kv", "writes_vector", "writes_graph"],
    )

    def _wiring(_query_wiring: dict[str, Any], operation: str) -> dict[str, Any]:
        assert operation == "delete"
        wiring = json.loads(_DELETE_WIRING.read_text(encoding="utf-8"))
        wiring["store_namespaces"] = dict(_FX_NAMESPACES)
        return wiring

    monkeypatch.setattr(engine_module, "_corpus_wiring", _wiring)
    return Databasise(store_root=store_root, workspace=_WS, registry=_registry_with(part))


async def test_a_successful_delete_removes_every_record_in_the_declared_namespaces(store_root, monkeypatch):
    await _seed(store_root)
    engine = _fixture_engine(store_root, monkeypatch, "success")

    outcome = await engine.delete_document("doc-1")

    assert outcome.status == "success"
    assert await _present(store_root) == (False, False, False)
    assert not (store_root / _WS / "text_chunks").exists()
    assert not (store_root / _WS / "chunk_entity_relation").exists()


async def test_a_delete_node_that_raises_after_staging_commits_nothing(store_root, monkeypatch):
    await _seed(store_root)
    engine = _fixture_engine(store_root, monkeypatch, "raise")

    with pytest.raises(ForeignEngineRefusalError):
        await engine.delete_document("doc-1")

    assert await _present(store_root) == (True, True, True)


async def test_a_delete_reporting_fail_drops_its_staged_deletes(store_root, monkeypatch):
    await _seed(store_root)
    engine = _fixture_engine(store_root, monkeypatch, "fail")

    outcome = await engine.delete_document("doc-1")

    assert outcome.status == "fail"
    assert await _present(store_root) == (True, True, True)


_WRITE_METHODS = {
    SqliteKVStore: ("upsert", "delete"),
    FaissVectorStore: ("upsert", "delete_by_ids"),
    CozoGraphStore: ("upsert_node", "upsert_edge", "delete_node", "delete_edge"),
}


async def test_the_default_lightrag_delete_stages_no_v2_store_write(store_root, monkeypatch):
    calls: list[str] = []
    prepared: list[str] = []
    for cls, methods in _WRITE_METHODS.items():
        for name in methods:
            original = getattr(cls, name)

            def _spy(self, *args, _original=original, _name=f"{cls.__name__}.{name}", **kwargs):
                calls.append(_name)
                return _original(self, *args, **kwargs)

            monkeypatch.setattr(cls, name, _spy)
        original_prepare = cls.prepare

        async def _prepare_spy(self, _original=original_prepare, _name=cls.__name__):
            prepared.append(_name)
            await _original(self)

        monkeypatch.setattr(cls, "prepare", _prepare_spy)

    engine = _make_engine(store_root, body=_make_stub_full_delete_body(timeout=5.0, stub_status="success"))
    outcome = await engine.delete_document("deadbeef")

    assert outcome.status == "success"
    assert calls == []
    # The commit ran over every store (the vector handle has no selected namespace to prepare).
    assert sorted(prepared) == ["CozoGraphStore", "SqliteKVStore"]
    kv = SqliteKVStore(namespace="text_chunks", workspace=_WS, store_root=store_root)
    graph = CozoGraphStore(namespace="chunk_entity_relation", workspace=_WS, store_root=store_root)
    try:
        assert await kv.is_empty() is True
        assert await graph.get_all_labels() == []
    finally:
        await kv.finalize()
        await graph.finalize()
    assert list((store_root / _WS).rglob("vector.faiss")) == []
