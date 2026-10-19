"""12-11 (HIPP-11, D-20, D-22): ``assemble-result``'s one ``top_k`` cut. The key is read from config
(a value-change test), the PPR branch drops zero-score items before the cut and keeps the branch's
own order, and an all-zero PPR branch passes nothing on."""

from __future__ import annotations

from databasise.parts.schema import NodeContext
from databasise.parts_core.hipporag.assemble_result import HIPPORAG_RESULT_ASSEMBLER_PART
from databasise.stores.kv import SqliteKVStore


async def _assembled_ids(store_root, *, guard_fired: bool, items: list[dict], config: dict) -> list[str]:
    kv_store = SqliteKVStore(namespace="hipporag-text-chunks", workspace="assemble-ws", store_root=store_root)
    await kv_store.upsert({item["id"]: {"content": f"text of {item['id']}"} for item in items})
    await kv_store.index_done_callback()
    branch = "dpr-fallback" if guard_fired else "ppr"
    result = await HIPPORAG_RESULT_ASSEMBLER_PART.body(
        NodeContext(
            node_id="assemble-result",
            config=config,
            inputs={
                "fact-filter": {"guard_fired": guard_fired},
                "ppr": {"items": items if branch == "ppr" else []},
                "dpr-fallback": {"items": items if branch == "dpr-fallback" else []},
            },
            stores={"kv": kv_store},
            clients={},
        )
    )
    return [item["id"] for item in result["items"]]


def _scored(scores: list[float]) -> list[dict]:
    return [{"id": f"c{index}", "score": score} for index, score in enumerate(scores)]


async def test_top_k_value_change_changes_how_many_items_pass_on(store_root):
    items = _scored([0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1])

    five = await _assembled_ids(store_root, guard_fired=True, items=items, config={"top_k": 5})
    two = await _assembled_ids(store_root, guard_fired=True, items=items, config={"top_k": 2})

    assert {"five": five, "two": two} == {
        "five": ["c0", "c1", "c2", "c3", "c4"],
        "two": ["c0", "c1"],
    }


async def test_top_k_defaults_to_five_and_returns_all_when_fewer(store_root):
    many = await _assembled_ids(store_root, guard_fired=True, items=_scored([0.9] * 8), config={})
    few = await _assembled_ids(store_root, guard_fired=True, items=_scored([0.9, 0.8]), config={})

    assert {"many": len(many), "few": few} == {"many": 5, "few": ["c0", "c1"]}


async def test_the_ppr_branch_drops_zero_score_items_and_keeps_order(store_root):
    items = _scored([0.4, 0.0, 0.2])

    ids = await _assembled_ids(store_root, guard_fired=False, items=items, config={"top_k": 5})

    assert ids == ["c0", "c2"]


async def test_an_all_zero_ppr_branch_passes_no_item_on(store_root):
    ids = await _assembled_ids(store_root, guard_fired=False, items=_scored([0.0, 0.0]), config={"top_k": 5})

    assert ids == []


async def test_the_dpr_branch_keeps_zero_score_items_within_the_cut(store_root):
    """Dense passage retrieval is not filtered by score; only the cut applies to it."""
    ids = await _assembled_ids(store_root, guard_fired=True, items=_scored([0.4, 0.0]), config={"top_k": 5})

    assert ids == ["c0", "c1"]
