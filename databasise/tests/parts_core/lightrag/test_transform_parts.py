"""Per-body tests for the three pure-transform parts 03-06-PLAN.md ports — ``join-roundrobin``
(Task 1, three positions), ``truncator-token-budget`` and ``chunk-selector-kg`` (Task 2). No
network, runs everywhere. Every part is exercised through its own registered ``Part.body`` (never a
private module function reached into directly), the same call shape ``databasise.parts.registry.
dispatch`` uses — matching ``test_graph_half_parts.py``'s and ``test_naive_arm_parts.py``'s own
``_ctx`` convention.

Task 1's join configs are drawn from the committed wiring files (``databasise/wirings/resolve.py``'s
``load_base``/``resolve_arm``), not hand-written dicts, so a config drift in the wiring itself
breaks this suite rather than silently diverging from what actually ships.
"""

from __future__ import annotations

from typing import Any

import pytest
from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag.chunk_sel_kg import LIGHTRAG_CHUNK_SELECTOR_KG_PART
from databasise.parts_core.lightrag.join_roundrobin import LIGHTRAG_JOIN_ROUNDROBIN_PART
from databasise.parts_core.lightrag.truncator_token_budget import (
    LIGHTRAG_TRUNCATOR_TOKEN_BUDGET_PART,
)
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore
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


# --------------------------------------------------------------------------------------------- #
# truncator-token-budget
# --------------------------------------------------------------------------------------------- #


async def test_truncator_preserves_input_order_and_removes_from_the_tail():
    items = [{"entity_name": f"e{i}", "description": "x" * 40} for i in range(5)]
    # Each item costs the same estimated tokens; an allowance covering three items' worth keeps
    # exactly the first three, in their original order — never re-sorted.
    per_item_cost = len(__import__("json").dumps(items[0], sort_keys=True)) // 4
    allowance = per_item_cost * 3
    ctx = _ctx(
        "budget-entities",
        config={"max_token_allowance": allowance},
        inputs={"join-entities": {"items": items}},
    )

    result = await LIGHTRAG_TRUNCATOR_TOKEN_BUDGET_PART.body(ctx)

    assert [item["entity_name"] for item in result["items"]] == ["e0", "e1", "e2"]
    assert result["consumed"] > 0


async def test_truncator_allowance_below_first_items_cost_yields_empty_and_zero_consumed():
    items = [{"entity_name": "e0", "description": "y" * 100}]
    ctx = _ctx(
        "budget-relations",
        config={"max_token_allowance": 1},
        inputs={"join-relations": {"items": items}},
    )

    result = await LIGHTRAG_TRUNCATOR_TOKEN_BUDGET_PART.body(ctx)

    assert result["items"] == []
    assert result["consumed"] == 0


async def test_truncator_default_allowance_differs_by_position_id():
    """``budget-entities``/``budget-relations`` share one body; v1's own differing defaults
    (``DEFAULT_MAX_ENTITY_TOKENS``/``DEFAULT_MAX_RELATION_TOKENS``) are selected by node id alone.
    """
    entities_ctx = _ctx("budget-entities", inputs={"join-entities": {"items": []}})
    relations_ctx = _ctx("budget-relations", inputs={"join-relations": {"items": []}})

    entities_result = await LIGHTRAG_TRUNCATOR_TOKEN_BUDGET_PART.body(entities_ctx)
    relations_result = await LIGHTRAG_TRUNCATOR_TOKEN_BUDGET_PART.body(relations_ctx)

    assert entities_result["allowance"] == 6000
    assert relations_result["allowance"] == 8000


# --------------------------------------------------------------------------------------------- #
# chunk-selector-kg
# --------------------------------------------------------------------------------------------- #


def test_chunk_selector_kg_declares_reads_vector_even_with_a_weight_only_config():
    """§19.9's fallback-reachability rule: the Part's own registered ``effects`` carries
    ``reads_vector`` unconditionally — never gated on whatever ``config["pick_method"]`` a given
    wiring happens to set.
    """
    assert "reads_vector" in LIGHTRAG_CHUNK_SELECTOR_KG_PART.effects
    assert "reads_kv" in LIGHTRAG_CHUNK_SELECTOR_KG_PART.effects


async def test_chunk_selector_kg_reports_which_pick_method_ran_on_fall_through(store_root):
    kv = SqliteKVStore(namespace="text_chunks", workspace="ws", store_root=store_root)
    await kv.upsert({"chunk-1": {"content": "hello"}})
    entity = {"entity_name": "Alice", "source_id": "chunk-1"}
    config = dict(load_base()["nodes"]["chunk-sel-kg"]["config"])
    assert config["pick_method"] == "VECTOR"  # the published base config's own primary method
    # No config["query_vector"] supplied: the VECTOR path yields nothing (see module docstring —
    # this node's own base-wiring deps carry no query embedding), so it falls through to WEIGHT.

    ctx = _ctx(
        "chunk-sel-kg",
        config=config,
        inputs={"budget-entities": {"items": [entity]}, "budget-relations": {"items": []}},
        stores={"kv": kv},
    )

    result = await LIGHTRAG_CHUNK_SELECTOR_KG_PART.body(ctx)

    assert result["pick_method_used"] == "WEIGHT"
    assert [item["chunk_id"] for item in result["items"]] == ["chunk-1"]


async def test_chunk_selector_kg_vector_path_reaches_the_vector_store_when_a_query_vector_is_supplied(
    store_root,
):
    kv = SqliteKVStore(namespace="text_chunks", workspace="ws", store_root=store_root)
    await kv.upsert({"chunk-1": {"content": "hello"}, "chunk-2": {"content": "world"}})
    vector = FaissVectorStore(namespace="chunks", workspace="ws", store_root=store_root)
    await vector.upsert(ids=["chunk-1", "chunk-2"], embeddings=[[1.0, 0.0], [0.0, 1.0]])
    await vector.index_done_callback()

    entity = {"entity_name": "Alice", "source_id": "chunk-1<SEP>chunk-2"}
    ctx = _ctx(
        "chunk-sel-kg",
        config={
            "pick_method": "VECTOR",
            "fallback_pick_method": "WEIGHT",
            "query_vector": [1.0, 0.0],
            "related_chunk_number": 5,
        },
        inputs={"budget-entities": {"items": [entity]}, "budget-relations": {"items": []}},
        stores={"kv": kv, "vector": vector},
    )

    result = await LIGHTRAG_CHUNK_SELECTOR_KG_PART.body(ctx)

    assert result["pick_method_used"] == "VECTOR"
    assert result["items"][0]["chunk_id"] == "chunk-1"  # closest to the supplied query vector
