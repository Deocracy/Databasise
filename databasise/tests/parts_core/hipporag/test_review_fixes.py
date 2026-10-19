"""Phase 12 code-review fixes (12-REVIEW.md, lane A): A-WR-01..04 regression tests.

A new file because the tests around the same behaviour are ledger-protected.
"""

from __future__ import annotations

import pytest

from databasise.parts.schema import NodeContext
from databasise.parts_core.hipporag.assemble_result import HIPPORAG_RESULT_ASSEMBLER_PART
from databasise.parts_core.hipporag.openie import _parse_entities, _parse_triples
from databasise.stores.kv import SqliteKVStore
from databasise.wirings.resolve import load_wiring


async def _assemble(store_root, *, config, ppr_items, dpr_items, guard_fired=False):
    kv_store = SqliteKVStore(namespace="hipporag-text-chunks", workspace="review-fix-ws", store_root=store_root)
    await kv_store.upsert({item["id"]: {"content": f"text of {item['id']}"} for item in ppr_items + dpr_items})
    await kv_store.index_done_callback()
    return await HIPPORAG_RESULT_ASSEMBLER_PART.body(
        NodeContext(
            node_id="assemble-result",
            config=config,
            inputs={
                "fact-filter": {"guard_fired": guard_fired},
                "ppr": {"items": ppr_items},
                "dpr-fallback": {"items": dpr_items},
            },
            stores={"kv": kv_store},
            clients={},
        )
    )


async def test_assemble_result_tolerates_a_missing_config_block(store_root):
    """A-WR-01: config None means the defaults, not an AttributeError."""
    result = await _assemble(
        store_root, config=None, ppr_items=[], dpr_items=[{"id": "d0", "score": 0.5}], guard_fired=True
    )

    assert [item["id"] for item in result["items"]] == ["d0"]


@pytest.mark.parametrize("top_k", [0, -1])
async def test_assemble_result_refuses_a_top_k_below_one(store_root, top_k):
    """A-WR-01: -1 used to cut the last item silently and 0 returned no evidence."""
    with pytest.raises(ValueError, match="top_k"):
        await _assemble(
            store_root,
            config={"top_k": top_k},
            ppr_items=[],
            dpr_items=[{"id": "d0", "score": 0.5}],
            guard_fired=True,
        )


async def test_an_empty_ppr_branch_falls_back_to_the_dense_items(store_root):
    """A-WR-02: PPR reached nothing (all scores 0), so the dense items computed in the same run answer."""
    result = await _assemble(
        store_root,
        config={"top_k": 5},
        ppr_items=[{"id": "p0", "score": 0.0}],
        dpr_items=[{"id": "d0", "score": 0.7}, {"id": "d1", "score": 0.4}],
    )

    assert [item["id"] for item in result["items"]] == ["d0", "d1"]


async def test_a_non_empty_ppr_branch_does_not_use_the_dense_items(store_root):
    result = await _assemble(
        store_root,
        config={"top_k": 5},
        ppr_items=[{"id": "p0", "score": 0.3}],
        dpr_items=[{"id": "d0", "score": 0.7}],
    )

    assert [item["id"] for item in result["items"]] == ["p0"]


@pytest.mark.parametrize(
    "text",
    [
        '{"triples": [["Ed Wood", "directed"]]}',
        '{"triples": [[1, 2, 3]]}',
        '{"triples": [["Ed Wood", "", "films"]]}',
        '{"triples": [["Ed Wood", "directed", "films"], ["bad"]]}',
    ],
)
def test_a_triples_list_with_any_invalid_item_is_unparseable(text):
    """A-WR-03: item-level leniency would give a silently thinner graph, which D-08 rules out."""
    assert _parse_triples(text) is None


def test_an_empty_triples_list_and_a_valid_one_still_parse():
    assert _parse_triples('{"triples": []}') == []
    assert _parse_triples('{"triples": [[" Ed Wood ", "directed", "films"]]}') == [("Ed Wood", "directed", "films")]


def test_an_entities_list_with_a_non_string_item_is_unparseable():
    assert _parse_entities('{"entities": ["Ed Wood", 3]}') is None
    assert _parse_entities('{"entities": ["Ed Wood", " "]}') == ["Ed Wood"]


# HIPP-18 / A-WR-04: the config keys each node's part (or the scheduler's guard machinery, for
# fact-filter ``guards``) reads. A new unread key fails the test below; add a key here only with its reader.
_READ_KEYS: dict[str, set[str]] = {
    "openie": {"max_concurrency"},
    "synonymy-edges": {"synonymy_top_k", "synonymy_threshold"},
    "fact-filter": {"guards", "linking_top_k"},
    "reset-vector-join": {"arity", "passage_node_weight"},
    "ppr": {"damping"},
    "assemble-result": {"top_k"},
}


@pytest.mark.parametrize("variant", ["base", "corpus-ingest"])
def test_every_config_key_in_the_hipporag_wirings_is_read(variant):
    for node_id, node in load_wiring("hipporag", variant=variant)["nodes"].items():
        unread = set(node.get("config") or {}) - _READ_KEYS.get(node_id, set())
        assert not unread, (variant, node_id, sorted(unread))
