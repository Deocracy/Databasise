"""STOR-05 (D-09): capability scoping is enforced per access mode.

A node declaring only ``reads_X`` gets a read-only allowlist proxy through the real scheduler
dispatch path; ``writes_X`` gets the writable handle (and wins over ``reads_X`` whatever the
declaration order); lifecycle methods are engine-only on every handle; and the store-less
effects are refused without touching ``raw_stores``.
"""

from __future__ import annotations

from pathlib import Path
from typing import get_args

import databasise
import pytest
from databasise.parity import run_arm, storage_audit
from databasise.parts.registry import PartRegistry
from databasise.parts.schema import Effect, NodeContext, Part, WiringNode
from databasise.parts_core import EFFECT_TO_STORE, CapabilityScopedStores, UndeclaredEffectError
from databasise.runner import scheduler
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import MultiNamespaceVectorStore
from databasise.validator.errors import ValidationReport
from databasise.validator.parse import ParsedWiring

_READS = {
    "kv": ["get_by_id", "get_by_ids", "filter_keys", "is_empty"],
    "vector": ["select", "query", "score_all", "self_knn", "iter_vectors", "get_by_id"],
    "graph": [
        "has_node",
        "get_node",
        "has_edge",
        "get_edge",
        "node_degree",
        "get_node_edges",
        "export_to_igraph",
        "get_all_labels",
    ],
}
_ENGINE_ONLY = [
    "index_done_callback",
    "drop_pending_index_ops",
    "finalize",
    "drop",
    "prepare",
    "commit_prepared",
    "abort_prepared",
]


def _single_node(effects: list[str], body) -> ParsedWiring:
    part = Part(
        name_at_version="test/scoped@1.0.0",
        kind="fanout",
        structural_depth="stage",
        effects=effects,
        upstream_ref=None,
        body=body,
    )
    node = WiringNode(component="test/scoped@1.0.0", kind="fanout", config=None, deps=[])
    return ParsedWiring(
        nodes={"n1": node},
        parts={"n1": part},
        deps={"n1": ()},
        node_order=("n1",),
        report=ValidationReport(),
    )


async def _run(parsed: ParsedWiring, stores: dict, recorder=None) -> dict:
    kwargs = {"recorder": recorder} if recorder is not None else {}
    return await scheduler.run_wiring(
        parsed,
        PartRegistry(),
        stores,
        determinism_setting="cache-bypassed",
        concurrency_setting="sequential",
        **kwargs,
    )


async def _upsert(ctx: NodeContext):
    await ctx.stores["kv"].upsert({"a": {"v": 1}})
    return {"ok": True}


async def test_case_1_reads_kv_node_cannot_upsert_and_nothing_is_written(store_root):
    kv = SqliteKVStore(namespace="ns", workspace="ws", store_root=store_root)
    try:
        result = await _run(_single_node(["reads_kv"], _upsert), {"kv": kv})
        exc = result["node_exceptions"]["n1"]
        assert isinstance(exc, UndeclaredEffectError)
        assert exc.effect == "writes_kv"
        assert kv._pending_upserts == {}
    finally:
        await kv.finalize()


async def test_reads_kv_node_can_read(store_root):
    kv = SqliteKVStore(namespace="ns", workspace="ws", store_root=store_root)
    seen = {}

    async def body(ctx: NodeContext):
        seen["value"] = await ctx.stores["kv"].get_by_id("a")
        return {"ok": True}

    try:
        result = await _run(_single_node(["reads_kv"], body), {"kv": kv})
        assert result["node_exceptions"] == {}
        assert seen == {"value": None}
    finally:
        await kv.finalize()


async def test_case_3_read_then_write_declaration_gets_the_writable_handle(store_root):
    kv = SqliteKVStore(namespace="ns", workspace="ws", store_root=store_root)
    try:
        result = await _run(_single_node(["reads_kv", "writes_kv"], _upsert), {"kv": kv})
        assert result["node_exceptions"] == {}
        assert "a" in kv._pending_upserts
    finally:
        await kv.finalize()


async def test_recorder_still_sees_each_store_access(store_root):
    kv = SqliteKVStore(namespace="ns", workspace="ws", store_root=store_root)
    touches: list[tuple] = []

    async def body(ctx: NodeContext):
        await ctx.stores["kv"].get_by_id("a")
        await ctx.stores["kv"].get_by_id("b")
        return {"ok": True}

    try:
        await _run(
            _single_node(["reads_kv"], body),
            {"kv": kv},
            recorder=lambda *t: touches.append(t),
        )
        assert touches.count(("n1", "store", "kv")) == 2
    finally:
        await kv.finalize()


@pytest.fixture
async def real_stores(store_root):
    stores = {
        "kv": SqliteKVStore(namespace="ns", workspace="ws", store_root=store_root),
        "vector": MultiNamespaceVectorStore(workspace="ws", store_root=store_root),
        "graph": CozoGraphStore(namespace="g", workspace="ws", store_root=store_root),
    }
    yield stores
    for store in stores.values():
        await store.finalize()


async def test_case_2_reads_vector_selected_child_cannot_delete(real_stores):
    async def body(ctx: NodeContext):
        await ctx.stores["vector"].select("chunks").delete_by_ids(["x"])
        return {"ok": True}

    result = await _run(_single_node(["reads_vector"], body), real_stores)
    exc = result["node_exceptions"]["n1"]
    assert isinstance(exc, UndeclaredEffectError)
    assert exc.effect == "writes_vector"

    child = CapabilityScopedStores(real_stores, ["reads_vector"]).require("reads_vector").select("chunks")
    assert callable(child.query)
    assert callable(child.score_all)


@pytest.mark.parametrize(
    "method", ["upsert_node", "upsert_edge", "delete_node", "delete_edge", "drop"]
)
def test_reads_graph_cannot_mutate(real_stores, method):
    graph = CapabilityScopedStores(real_stores, ["reads_graph"]).require("reads_graph")
    with pytest.raises(UndeclaredEffectError) as exc_info:
        getattr(graph, method)
    # drop is engine-only on every handle; the mutators name the missing write effect
    assert exc_info.value.effect == ("drop" if method == "drop" else "writes_graph")


@pytest.mark.parametrize("method", ["upsert", "delete", "upsert_node", "delete_by_ids"])
def test_read_proxies_refuse_writes_naming_the_write_effect(real_stores, method):
    for kind in ("kv", "vector", "graph"):
        handle = CapabilityScopedStores(real_stores, [f"reads_{kind}"]).require(f"reads_{kind}")
        with pytest.raises(UndeclaredEffectError) as exc_info:
            getattr(handle, method)
        assert exc_info.value.effect == f"writes_{kind}"


def test_every_allowlisted_name_resolves_on_a_read_proxy(real_stores):
    scoped = CapabilityScopedStores(real_stores, ["reads_kv", "reads_vector", "reads_graph"])
    targets = {
        "kv": scoped.require("reads_kv"),
        "vector": scoped.require("reads_vector").select("chunks"),
        "graph": scoped.require("reads_graph"),
    }
    for kind, names in _READS.items():
        for name in names:
            # select lives on the multi-namespace handle; the rest on the selected namespace
            target = scoped.require("reads_vector") if name == "select" else targets[kind]
            assert callable(getattr(target, name)), (kind, name)


@pytest.mark.parametrize("mode", ["reads", "writes"])
def test_lifecycle_methods_are_engine_only_on_every_handle(real_stores, mode):
    effects = [f"{mode}_{kind}" for kind in ("kv", "vector", "graph")]
    scoped = CapabilityScopedStores(real_stores, effects)
    handles = [scoped.require(e) for e in effects]
    handles.append(scoped.require(f"{mode}_vector").select("chunks"))
    for handle in handles:
        for name in _ENGINE_ONLY:
            with pytest.raises(UndeclaredEffectError, match="engine-only"):
                getattr(handle, name)


def test_writable_handles_pass_every_other_method_through(real_stores):
    scoped = CapabilityScopedStores(real_stores, ["writes_kv", "writes_vector", "writes_graph"])
    assert scoped.require("writes_kv").upsert == real_stores["kv"].upsert
    child = scoped.require("writes_vector").select("chunks")
    assert child.delete_by_ids == real_stores["vector"].select("chunks").delete_by_ids
    assert scoped.require("writes_graph").upsert_edge == real_stores["graph"].upsert_edge


class _RecordingMapping(dict):
    def __init__(self) -> None:
        super().__init__(kv=object(), vector=object(), graph=object())
        self.accessed: list[object] = []

    def __getitem__(self, key):
        self.accessed.append(key)
        return super().__getitem__(key)

    def get(self, key, default=None):
        self.accessed.append(key)
        return super().get(key, default)

    def __contains__(self, key):
        self.accessed.append(key)
        return super().__contains__(key)


@pytest.mark.parametrize(
    "effect",
    [
        "mutates_store",
        "self_storage",
        "writes_artifact",
        "reads_lexical",
        "writes_lexical",
        "reads_blob",
        "calls_llm",
        "calls_rerank",
        "calls_embedding",
        "net",
        "fs",
    ],
)
def test_case_4_store_less_effects_are_refused_without_reading_raw_stores(effect):
    raw = _RecordingMapping()
    with pytest.raises(UndeclaredEffectError, match="no store backs effect") as exc_info:
        CapabilityScopedStores(raw, [effect]).require(effect)
    assert exc_info.value.effect == effect
    assert raw.accessed == []


def test_effect_to_store_has_exactly_the_17_effect_members():
    assert set(EFFECT_TO_STORE) == set(get_args(Effect))
    assert len(EFFECT_TO_STORE) == 17


def test_storage_audit_uses_the_same_table():
    assert storage_audit._declared_handles(["calls_llm", "reads_kv", "writes_vector"]) == frozenset(
        {("client", "llm"), ("store", "kv"), ("store", "vector")}
    )
    assert storage_audit._declared_handles(["writes_artifact"]) == frozenset()
    assert storage_audit._declared_handles(["mutates_store", "net", "fs"]) == frozenset()


def test_parity_runs_reach_stores_only_through_the_scheduler_view():
    assert run_arm._scheduler is scheduler
    package = Path(databasise.__file__).parent
    hits = [
        str(p)
        for p in (package / "parity").rglob("*.py")
        if "CapabilityScopedStores(" in p.read_text(encoding="utf-8")
    ]
    assert hits == []


def test_no_effect_is_mapped_to_a_store_by_splitting_its_name():
    package = Path(databasise.__file__).parent
    hits = [
        str(p)
        for sub in ("parts_core", "runner", "parity", "seam")
        for p in (package / sub).rglob("*.py")
        if 'split("_", 1)' in p.read_text(encoding="utf-8")
    ]
    assert hits == []
