"""Per-body tests for the pure-transform parts 03-06-PLAN.md ports — ``join-roundrobin`` (Task 1,
three positions), with ``truncator-token-budget``/``chunk-selector-kg`` (Task 2) added below in
this same plan's next commit. No network, runs everywhere. Every part is exercised through its own
registered ``Part.body`` (never a private module function reached into directly), the same call
shape ``databasise.parts.registry.dispatch`` uses — matching ``test_graph_half_parts.py``'s and
``test_naive_arm_parts.py``'s own ``_ctx`` convention.

Join configs are drawn from the committed wiring files (``databasise/wirings/resolve.py``'s
``load_base``/``resolve_arm``), not hand-written dicts, so a config drift in the wiring itself
breaks this suite rather than silently diverging from what actually ships.
"""

from __future__ import annotations

from typing import Any

import pytest
from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag.join_roundrobin import LIGHTRAG_JOIN_ROUNDROBIN_PART
from databasise.wirings.resolve import load_base, resolve_arm


def _ctx(
    node_id: str,
    config: dict[str, Any] | None = None,
    inputs: dict[str, Any] | None = None,
    stores: dict[str, Any] | None = None,
    clients: dict[str, Any] | None = None,
) -> NodeContext:
    """A plain, unscoped ``NodeContext`` — see ``test_graph_half_parts.py``'s own ``_ctx``
    docstring for why this exercises the same subscript-access call shape the scheduler's scoped
    views present, without needing the deny-by-default wrapper for every ordinary case.
    """
    return NodeContext(
        node_id=node_id,
        config=config,
        inputs=inputs or {},
        stores=stores or {},
        clients=clients or {},
    )


def _base_config(node_id: str) -> dict[str, Any]:
    return dict(load_base()["nodes"][node_id]["config"])


def _resolved_config(arm_name: str, node_id: str) -> dict[str, Any]:
    return dict(resolve_arm(arm_name)["nodes"][node_id]["config"])


# --------------------------------------------------------------------------------------------- #
# join-roundrobin — join-entities (mix/base config: two arms, entity-hydrate-expand first)
# --------------------------------------------------------------------------------------------- #


async def test_join_entities_interleaves_round_robin_with_entity_hydrate_expand_first():
    config = _base_config("join-entities")
    assert "entity-hydrate-expand" in config["arm_precedence"]  # the wiring's own committed text

    entity_a = {"entity_name": "Alice", "derived_from": ["seed-alice"]}
    entity_b = {"entity_name": "Bob", "derived_from": ["seed-bob"]}
    entity_c = {"entity_name": "Carol", "derived_from": ["seed-carol"]}
    ctx = _ctx(
        "join-entities",
        config=config,
        inputs={
            "entity-hydrate-expand": {"entities": [entity_a, entity_c]},
            "relation-hydrate-expand": {"entities": [entity_b]},
        },
    )

    result = await LIGHTRAG_JOIN_ROUNDROBIN_PART.body(ctx)

    assert [item["entity_name"] for item in result["items"]] == ["Alice", "Bob", "Carol"]
    assert [item["rank_position"] for item in result["items"]] == [0, 1, 2]


# --------------------------------------------------------------------------------------------- #
# join-roundrobin — join-relations (mix/base config: order-insensitive dedup by endpoint pair)
# --------------------------------------------------------------------------------------------- #


async def test_join_relations_order_insensitive_dedup_collapses_a_reversed_endpoint_pair():
    config = _base_config("join-relations")
    assert "dedup" in config["arm_precedence"]  # the wiring's own committed dedup description

    survivor = {"src_tgt": ["Alice", "Bob"], "description": "knows", "derived_from": ["Alice"]}
    duplicate = {"src_id": "Bob", "tgt_id": "Alice", "description": "knows", "derived_from": ["rel-ab"]}
    unique = {"src_tgt": ["Carol", "Dave"], "description": "met", "derived_from": ["Carol"]}
    ctx = _ctx(
        "join-relations",
        config=config,
        inputs={
            "entity-hydrate-expand": {"relations": [survivor]},
            "relation-hydrate-expand": {"relations": [duplicate, unique]},
        },
    )

    result = await LIGHTRAG_JOIN_ROUNDROBIN_PART.body(ctx)

    assert len(result["items"]) == 2  # the reversed-pair duplicate collapsed into the survivor
    kept = next(item for item in result["items"] if set(item["src_tgt"]) == {"Alice", "Bob"})
    assert set(kept["derived_from"]) == {"Alice", "rel-ab"}  # CONTRACT §4 D9: both origins union in


async def test_join_relations_reprojected_item_carries_derived_from():
    """A merge that collapses two contributing items into one is authoring, not pass-through
    (CONTRACT §4, repaired at D9) — the surviving item's ``derived_from`` must carry both
    contributors' own origins, never just whichever arrived first.
    """
    config = _base_config("join-relations")
    first = {"src_tgt": ["X", "Y"], "derived_from": ["origin-1"]}
    second = {"src_id": "Y", "tgt_id": "X", "derived_from": ["origin-2"]}
    ctx = _ctx(
        "join-relations",
        config=config,
        inputs={
            "entity-hydrate-expand": {"relations": [first]},
            "relation-hydrate-expand": {"relations": [second]},
        },
    )

    result = await LIGHTRAG_JOIN_ROUNDROBIN_PART.body(ctx)

    assert len(result["items"]) == 1
    assert set(result["items"][0]["derived_from"]) == {"origin-1", "origin-2"}


async def test_join_relations_unchanged_item_keeps_its_own_derived_from():
    config = _base_config("join-relations")
    only = {"src_tgt": ["A", "B"], "derived_from": ["seed-a"]}
    ctx = _ctx(
        "join-relations",
        config=config,
        inputs={
            "entity-hydrate-expand": {"relations": [only]},
            "relation-hydrate-expand": {"relations": []},
        },
    )

    result = await LIGHTRAG_JOIN_ROUNDROBIN_PART.body(ctx)

    assert result["items"][0]["derived_from"] == ["seed-a"]


# --------------------------------------------------------------------------------------------- #
# join-roundrobin — join-chunks (mix/base config: arity 2, chunk-sel-kg emitted first)
# --------------------------------------------------------------------------------------------- #


async def test_join_chunks_honours_arity_two_and_chunk_sel_kg_precedence():
    config = _base_config("join-chunks")
    assert config["arity"] == 2

    kg_item = {"id": "chunk-kg", "content": "kg"}
    vec_item = {"id": "chunk-vec", "content": "vec"}
    ctx = _ctx(
        "join-chunks",
        config=config,
        inputs={
            "chunk-sel-kg": {"items": [kg_item]},
            "chunk-vector": {"items": [vec_item]},
        },
    )

    result = await LIGHTRAG_JOIN_ROUNDROBIN_PART.body(ctx)

    assert [item["id"] for item in result["items"]] == ["chunk-kg", "chunk-vec"]


async def test_join_chunks_arity_mismatch_raises():
    config = _base_config("join-chunks")
    ctx = _ctx(
        "join-chunks",
        config=config,
        inputs={"chunk-sel-kg": {"items": []}},  # only one input against a declared arity of two
    )

    with pytest.raises(ValueError, match="arity"):
        await LIGHTRAG_JOIN_ROUNDROBIN_PART.body(ctx)


async def test_join_chunks_degenerate_one_ary_local_arm_config_does_not_raise():
    """The ``local``/``global``/``hybrid`` arm patches replace ``join-chunks``'s config with
    ``arity: 1`` for their own single-input join — the same body, a different declared arity,
    drawn from the arm's own resolved config rather than hand-written.
    """
    config = _resolved_config("local", "join-chunks")
    assert config["arity"] == 1

    ctx = _ctx(
        "join-chunks",
        config=config,
        inputs={"chunk-sel-kg": {"items": [{"id": "only-one"}]}},
    )

    result = await LIGHTRAG_JOIN_ROUNDROBIN_PART.body(ctx)

    assert [item["id"] for item in result["items"]] == ["only-one"]
