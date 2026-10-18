"""STOR-09 (D-12): the vector adapter refuses invalid input and unselected reads by name —
``top_k <= 0`` raises ``InvalidTopKError``, the unselected-namespace refusal lists only directories
holding ``vector.faiss``, and every read on an unselected multi-namespace handle raises
``VectorNamespaceNotSelectedError`` instead of ``AttributeError``.
"""

from __future__ import annotations

import pytest

from databasise.stores.vector import (
    FaissVectorStore,
    InvalidTopKError,
    MultiNamespaceVectorStore,
    VectorNamespaceNotSelectedError,
)


@pytest.mark.parametrize("top_k", [0, -1])
async def test_query_refuses_non_positive_top_k_on_an_empty_store(store_root, top_k):
    store = FaissVectorStore(namespace="chunks", workspace="ws", store_root=store_root)
    with pytest.raises(InvalidTopKError) as info:
        await store.query([1.0, 0.0, 0.0], top_k=top_k)
    assert isinstance(info.value, ValueError)
    assert info.value.top_k == top_k


@pytest.mark.parametrize("top_k", [0, -1])
async def test_query_and_self_knn_refuse_non_positive_top_k_on_a_populated_store(store_root, top_k):
    store = FaissVectorStore(namespace="chunks", workspace="ws", store_root=store_root)
    await store.upsert(["a", "b"], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    await store.index_done_callback()
    with pytest.raises(InvalidTopKError):
        await store.query([1.0, 0.0, 0.0], top_k=top_k)
    with pytest.raises(InvalidTopKError):
        await store.self_knn(top_k=top_k)


async def _workspace_with_non_vector_dirs(store_root):
    chunks = FaissVectorStore(namespace="chunks", workspace="ws", store_root=store_root)
    await chunks.upsert(["a"], [[1.0, 0.0, 0.0]])
    await chunks.index_done_callback()
    (store_root / "ws" / "text_chunks").mkdir()
    (store_root / "ws" / "chunk_entity_relation").mkdir()
    return MultiNamespaceVectorStore(workspace="ws", store_root=store_root)


async def test_unselected_refusal_lists_only_vector_namespaces(store_root):
    handle = await _workspace_with_non_vector_dirs(store_root)
    with pytest.raises(VectorNamespaceNotSelectedError) as info:
        await handle.query([1.0, 0.0, 0.0], top_k=1)
    assert info.value.available == ["chunks"]


async def test_every_read_on_an_unselected_handle_refuses_by_name(store_root):
    handle = await _workspace_with_non_vector_dirs(store_root)
    with pytest.raises(VectorNamespaceNotSelectedError):
        await handle.score_all([1.0, 0.0, 0.0])
    with pytest.raises(VectorNamespaceNotSelectedError):
        await handle.self_knn(top_k=1)
    with pytest.raises(VectorNamespaceNotSelectedError):
        handle.get_by_id("a")
    # raises at call time, not at the first next() (research Pitfall 12)
    with pytest.raises(VectorNamespaceNotSelectedError) as info:
        handle.iter_vectors()
    assert info.value.available == ["chunks"]
