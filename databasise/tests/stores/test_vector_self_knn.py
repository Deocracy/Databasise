"""06-05-PLAN.md Task 2: ``FaissVectorStore.self_knn`` — §14.2's batched self-KNN sub-capability.
A loop-based implementation composing ``query()``/``search`` once per stored vector would scale its
own Faiss ``search`` call count with the stored vector count; the real implementation issues
exactly one batched ``search`` call whatever the store's size. Mirrors
``databasise/tests/stores/test_graph_bulk_export.py``'s own call-counting convention, applied here
to a proxy around ``FaissVectorStore``'s own ``_index`` attribute (a Faiss C-extension object,
which cannot have a bound method reassigned directly).
"""

from __future__ import annotations

import numpy as np

from databasise.stores.vector import FaissVectorStore

_WORKSPACE = "self-knn-test"


async def _seeded_store(store_root, namespace: str, count: int, seed: int = 42) -> FaissVectorStore:
    store = FaissVectorStore(namespace=namespace, workspace=_WORKSPACE, store_root=store_root)
    ids = [f"v{i}" for i in range(count)]
    rng = np.random.default_rng(seed=seed)
    embeddings = rng.random((count, 8)).astype("float32")
    await store.upsert(ids=ids, embeddings=embeddings, metadatas=[{} for _ in ids])
    await store.index_done_callback()
    return store


class _SearchCountingIndexProxy:
    """Wraps ``store._index`` (a Faiss C-extension object whose methods cannot be monkeypatched
    directly) so ``search`` calls are counted while every other attribute (``ntotal``,
    ``reconstruct``, ...) delegates through to the real index unchanged."""

    def __init__(self, real_index: object) -> None:
        self._real_index = real_index
        self.count = 0

    def search(self, *args: object, **kwargs: object) -> object:
        self.count += 1
        return self._real_index.search(*args, **kwargs)  # type: ignore[attr-defined]

    def __getattr__(self, name: str) -> object:
        return getattr(self._real_index, name)


def _counting_search(store: FaissVectorStore) -> _SearchCountingIndexProxy:
    proxy = _SearchCountingIndexProxy(store._index)
    store._index = proxy  # type: ignore[assignment]
    return proxy


async def test_self_knn_returns_top_k_neighbours_per_vector_never_including_itself(store_root):
    store = await _seeded_store(store_root, "basic", count=40)

    results = await store.self_knn(top_k=3)

    assert len(results) == 40
    for doc_id, neighbours in results.items():
        assert len(neighbours) <= 3
        assert all(n["id"] != doc_id for n in neighbours)


async def test_self_knn_search_call_count_does_not_scale_with_stored_vector_count(store_root):
    small_store = await _seeded_store(store_root, "small", count=8)
    small_counter = _counting_search(small_store)
    await small_store.self_knn(top_k=3)

    large_store = await _seeded_store(store_root, "large", count=40)
    large_counter = _counting_search(large_store)
    await large_store.self_knn(top_k=3)

    assert small_counter.count == large_counter.count == 1


async def test_self_knn_on_empty_store_returns_empty_mapping(store_root):
    store = FaissVectorStore(namespace="empty", workspace=_WORKSPACE, store_root=store_root)

    results = await store.self_knn(top_k=3)

    assert results == {}


async def test_mutating_a_stored_vector_changes_its_neighbour_list_negative_control(store_root):
    """Negative control: a comparison of neighbour lists must have teeth — mutating one stored
    vector and re-computing self_knn must change that vector's own neighbour list."""
    store = await _seeded_store(store_root, "negctl", count=10)
    before = await store.self_knn(top_k=3)

    new_vector = np.zeros(8, dtype="float32")
    new_vector[0] = 1.0
    await store.upsert(ids=["v0"], embeddings=new_vector, metadatas=[{}])
    await store.index_done_callback()

    after = await store.self_knn(top_k=3)

    assert before["v0"] != after["v0"]
