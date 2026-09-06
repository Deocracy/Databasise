"""End-to-end tests for the graph-half retrieval path (``entity-lookup`` -> ``entity-hydrate-
expand``, ``relation-lookup`` -> ``relation-hydrate-expand``) against the real, plan-03-11-
re-ingested and plan-03-02-imported v1 parity corpus — never a synthetic double. Skips cleanly
(naming the reason) when the imported v2 store is absent on this machine, via the
``v2_parity_store_dir`` fixture (``databasise/tests/parity/conftest.py``).

Uses ``run_arm._build_stores`` for the exact stores dict a real arm run wires, and
``import_index._import_workspace()`` for the exact workspace derivation — never a hand-rolled
namespace string — so this proves the same wiring path a real ``hybrid``/``local``/``global`` run
takes, not a parallel one that happens to also work. The query vector is one of the real, already-
imported vectors itself (its own nearest neighbour is always itself), so no live embedding call is
needed to prove the read path end to end.
"""

from __future__ import annotations

from typing import Any

from databasise.parity import run_arm as _run_arm
from databasise.parity.import_index import DEFAULT_STORE_ROOT, _import_workspace
from databasise.parts.schema import NodeContext
from databasise.parts_core.lightrag.entity_hydrate_expand import (
    LIGHTRAG_ENTITY_HYDRATE_EXPAND_PART,
)
from databasise.parts_core.lightrag.entity_lookup import LIGHTRAG_ENTITY_LOOKUP_PART
from databasise.parts_core.lightrag.relation_hydrate_expand import (
    LIGHTRAG_RELATION_HYDRATE_EXPAND_PART,
)
from databasise.parts_core.lightrag.relation_lookup import LIGHTRAG_RELATION_LOOKUP_PART


def _ctx(
    node_id: str,
    config: dict[str, Any] | None = None,
    inputs: dict[str, Any] | None = None,
    stores: dict[str, Any] | None = None,
) -> NodeContext:
    return NodeContext(
        node_id=node_id, config=config, inputs=inputs or {}, stores=stores or {}, clients={}
    )


async def test_entity_lookup_and_hydrate_expand_against_the_real_imported_index(
    v2_parity_store_dir,
):
    workspace = _import_workspace()
    stores = _run_arm._build_stores(DEFAULT_STORE_ROOT, workspace)
    try:
        vector_handle = stores["vector"]
        entities_store = vector_handle.select("entities")
        _first_id, first_vector = next(iter(entities_store.iter_vectors()), (None, None))
        assert first_vector is not None, "entities vector namespace is empty in the imported store"

        lookup_ctx = _ctx(
            "entity-lookup",
            config={"top_k": 40},
            inputs={"embedder-query": {"vector": first_vector.tolist()}},
            stores={"vector": vector_handle},
        )
        lookup_result = await LIGHTRAG_ENTITY_LOOKUP_PART.body(lookup_ctx)

        assert lookup_result["items"], "entity-lookup returned no items against the real index"
        for item in lookup_result["items"]:
            assert item.get("entity_name"), (
                f"entity-lookup item {item.get('id')!r} carries no non-empty entity_name — "
                "this is the exact field whose absence produced the recorded "
                "NodeExecutionError: 'entity_name'"
            )

        hydrate_ctx = _ctx(
            "entity-hydrate-expand",
            inputs={"entity-lookup": lookup_result},
            stores={"graph": stores["graph"]},
        )
        hydrate_result = await LIGHTRAG_ENTITY_HYDRATE_EXPAND_PART.body(hydrate_ctx)

        assert hydrate_result["missing_seeds"] == [], (
            f"entity-hydrate-expand reported missing seeds against the real graph: "
            f"{hydrate_result['missing_seeds']}"
        )
        assert len(hydrate_result["entities"]) >= 1, (
            "entity-hydrate-expand hydrated zero real graph nodes"
        )
    finally:
        for store in stores.values():
            await store.finalize()


async def test_relation_lookup_and_hydrate_expand_against_the_real_imported_index(
    v2_parity_store_dir,
):
    workspace = _import_workspace()
    stores = _run_arm._build_stores(DEFAULT_STORE_ROOT, workspace)
    try:
        vector_handle = stores["vector"]
        relationships_store = vector_handle.select("relationships")
        _first_id, first_vector = next(iter(relationships_store.iter_vectors()), (None, None))
        assert first_vector is not None, (
            "relationships vector namespace is empty in the imported store"
        )

        lookup_ctx = _ctx(
            "relation-lookup",
            config={"top_k": 40},
            inputs={"embedder-query": {"vector": first_vector.tolist()}},
            stores={"vector": vector_handle},
        )
        lookup_result = await LIGHTRAG_RELATION_LOOKUP_PART.body(lookup_ctx)

        assert lookup_result["items"], "relation-lookup returned no items against the real index"
        for item in lookup_result["items"]:
            assert item.get("src_id"), (
                f"relation-lookup item {item.get('id')!r} carries no non-empty src_id — this is "
                "the exact field whose absence produced the recorded NodeExecutionError: 'src_id'"
            )
            assert item.get("tgt_id"), (
                f"relation-lookup item {item.get('id')!r} carries no non-empty tgt_id"
            )

        hydrate_ctx = _ctx(
            "relation-hydrate-expand",
            inputs={"relation-lookup": lookup_result},
            stores={"graph": stores["graph"]},
        )
        hydrate_result = await LIGHTRAG_RELATION_HYDRATE_EXPAND_PART.body(hydrate_ctx)

        assert hydrate_result["missing_seeds"] == [], (
            f"relation-hydrate-expand reported missing seeds against the real graph: "
            f"{hydrate_result['missing_seeds']}"
        )
        assert len(hydrate_result["relations"]) >= 1, (
            "relation-hydrate-expand hydrated zero real graph edges"
        )
    finally:
        for store in stores.values():
            await store.finalize()
