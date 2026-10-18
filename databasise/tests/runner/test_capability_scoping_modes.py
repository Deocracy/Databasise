"""STOR-05 (D-09): capability scoping is enforced per access mode.

A node declaring only ``reads_X`` gets a read-only allowlist proxy through the real scheduler
dispatch path; ``writes_X`` gets the writable handle (and wins over ``reads_X`` whatever the
declaration order); lifecycle methods are engine-only on every handle; and the store-less
effects are refused without touching ``raw_stores``.
"""

from __future__ import annotations

from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.parts_core import UndeclaredEffectError
from databasise.runner import scheduler
from databasise.stores.kv import SqliteKVStore
from databasise.validator.errors import ValidationReport
from databasise.validator.parse import ParsedWiring


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
