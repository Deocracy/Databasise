"""06-01-PLAN.md Task 3: RIG §RUN.1/§RUN.2's per-modality isolation and artifact-overlap rules,
proven against the same ``_build_stores`` the seam and the parity harness both use. Resolves
LightRAG's ``naive`` arm and HippoRAG's base wiring against one ``store_root``/``workspace`` pair
and asserts their resolved graph/KV directories are disjoint — then pins the regression (LightRAG's
own directories are unchanged from before this plan) and proves the cross-read refusal: seeding
one modality's graph namespace leaves the other's empty.
"""

from __future__ import annotations

from databasise.seam.engine import _build_stores
from databasise.wirings.resolve import load_wiring, resolve_arm

_WORKSPACE = "isolation-test"


def _resolved_dirs(store_root):
    lightrag_stores = _build_stores(store_root, _WORKSPACE, resolve_arm("naive"))
    hipporag_stores = _build_stores(store_root, _WORKSPACE, load_wiring("hipporag"))
    return lightrag_stores, hipporag_stores


def test_resolved_graph_and_kv_directories_are_disjoint_between_modalities(store_root):
    lightrag_stores, hipporag_stores = _resolved_dirs(store_root)

    assert lightrag_stores["graph"]._dir != hipporag_stores["graph"]._dir
    assert lightrag_stores["kv"]._dir != hipporag_stores["kv"]._dir


def test_lightrags_own_directories_are_unchanged_from_before_this_plan(store_root):
    """Regression pin: a future change that relocates LightRAG's on-disk state must fail here
    rather than silently orphaning the Phase 3 imported index."""
    lightrag_stores, hipporag_stores = _resolved_dirs(store_root)

    assert lightrag_stores["graph"]._dir.name == "chunk_entity_relation"
    assert lightrag_stores["kv"]._dir.name == "text_chunks"
    assert hipporag_stores["graph"]._dir.name == "hipporag-graph"
    assert hipporag_stores["kv"]._dir.name == "hipporag-text-chunks"


async def test_seeding_one_modalitys_graph_leaves_the_others_empty_cross_read_refusal(store_root):
    lightrag_stores, hipporag_stores = _resolved_dirs(store_root)

    await lightrag_stores["graph"].upsert_node("lightrag-only-node", {})
    await lightrag_stores["graph"].index_done_callback()

    assert await hipporag_stores["graph"].get_all_labels() == []
    assert await lightrag_stores["graph"].get_all_labels() == ["lightrag-only-node"]

    await hipporag_stores["graph"].upsert_node("hipporag-only-node", {})
    await hipporag_stores["graph"].index_done_callback()

    assert await hipporag_stores["graph"].get_all_labels() == ["hipporag-only-node"]
    # The reverse direction: HippoRAG's own write did not leak into LightRAG's namespace either.
    assert await lightrag_stores["graph"].get_all_labels() == ["lightrag-only-node"]

    for store in (*lightrag_stores.values(), *hipporag_stores.values()):
        await store.finalize()
