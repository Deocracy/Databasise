"""Tests for ``databasise.stores.vector.MultiNamespaceVectorStore`` (03-12-PLAN.md Task 1) — the
handle that lets each vector-reading §L.1 position select its own namespace, and refuses by name
when a caller forgets to select one instead of silently serving a default index.

Covers: the no-namespace-selected refusal (naming the available namespaces), select()'s
same-object caching, and the lifecycle fan-out (initialize/finalize touch only selected
namespaces, never construct an unselected one).
"""

from __future__ import annotations

from databasise.stores.vector import (
    FaissVectorStore,
    MultiNamespaceVectorStore,
    VectorNamespaceNotSelectedError,
)


async def test_query_without_selecting_raises_naming_available_namespaces(store_root):
    # Pre-populate two namespace directories on disk directly, bypassing select() — the handle's
    # refusal message must name what actually exists under the workspace, not just what it has
    # selected so far (which is nothing, in this test).
    chunks = FaissVectorStore(namespace="chunks", workspace="ws", store_root=store_root)
    await chunks.upsert(ids=["c1"], embeddings=[[1.0, 0.0]])
    await chunks.index_done_callback()
    entities = FaissVectorStore(namespace="entities", workspace="ws", store_root=store_root)
    await entities.upsert(ids=["e1"], embeddings=[[0.0, 1.0]])
    await entities.index_done_callback()
    await chunks.finalize()
    await entities.finalize()

    handle = MultiNamespaceVectorStore(workspace="ws", store_root=store_root)

    try:
        await handle.query([1.0, 0.0], top_k=5)
        raised = False
    except VectorNamespaceNotSelectedError as exc:
        raised = True
        assert "chunks" in exc.available
        assert "entities" in exc.available
        assert "chunks" in str(exc)
        assert "entities" in str(exc)
    assert raised


async def test_upsert_and_delete_by_ids_without_selecting_also_raise(store_root):
    handle = MultiNamespaceVectorStore(workspace="ws", store_root=store_root)

    try:
        await handle.upsert(ids=["x"], embeddings=[[1.0, 0.0]])
        raised_upsert = False
    except VectorNamespaceNotSelectedError:
        raised_upsert = True
    assert raised_upsert

    try:
        await handle.delete_by_ids(["x"])
        raised_delete = False
    except VectorNamespaceNotSelectedError:
        raised_delete = True
    assert raised_delete


def test_selecting_the_same_namespace_twice_returns_the_identical_object(store_root):
    handle = MultiNamespaceVectorStore(workspace="ws", store_root=store_root)

    first = handle.select("entities")
    second = handle.select("entities")

    assert first is second


def test_selecting_two_different_namespaces_returns_different_objects(store_root):
    handle = MultiNamespaceVectorStore(workspace="ws", store_root=store_root)

    entities = handle.select("entities")
    relationships = handle.select("relationships")

    assert entities is not relationships
    assert entities.namespace == "entities"
    assert relationships.namespace == "relationships"


async def test_finalize_finalizes_only_selected_namespaces_and_constructs_no_others(store_root):
    handle = MultiNamespaceVectorStore(workspace="ws", store_root=store_root)
    selected = handle.select("entities")
    await selected.upsert(ids=["e1"], embeddings=[[1.0, 0.0]])
    await selected.index_done_callback()

    # Nothing under "relationships" was ever selected — its namespace directory must not exist.
    assert not (store_root / "ws" / "relationships").exists()

    await handle.finalize()

    # finalize() must not have constructed "relationships" as a side effect of fanning out.
    assert not (store_root / "ws" / "relationships").exists()
    assert "relationships" not in handle._children


async def test_query_through_a_selected_namespace_works_normally(store_root):
    handle = MultiNamespaceVectorStore(workspace="ws", store_root=store_root)
    entities = handle.select("entities")
    await entities.upsert(ids=["ent-a"], embeddings=[[1.0, 0.0]], metadatas=[{"entity_name": "A"}])
    await entities.index_done_callback()

    results = await handle.select("entities").query([1.0, 0.0], top_k=5)

    assert [r["id"] for r in results] == ["ent-a"]
    assert results[0]["entity_name"] == "A"
