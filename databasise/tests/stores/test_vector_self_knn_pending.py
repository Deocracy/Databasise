"""12-03-PLAN.md Task 2 (D-05, HIPP-07): ``FaissVectorStore.self_knn(ids=...)`` searches committed
and staged vectors for exactly the given ids. The default path (ids omitted) stays committed-only
and is pinned by ``test_vector_self_knn.py``; these tests cover only the ids path and the
default-path contrast.
"""

from __future__ import annotations

import numpy as np

from databasise.stores.vector import FaissVectorStore, InvalidTopKError

_WORKSPACE = "self-knn-pending-test"


def _vec(*components: float) -> np.ndarray:
    return np.array([components], dtype="float32")


async def _store(store_root, namespace: str, committed: dict[str, list[float]]):
    store = FaissVectorStore(namespace=namespace, workspace=_WORKSPACE, store_root=store_root)
    if committed:
        await store.upsert(
            ids=list(committed),
            embeddings=np.array(list(committed.values()), dtype="float32"),
            metadatas=[{} for _ in committed],
        )
        await store.index_done_callback()
    return store


async def test_a_staged_id_finds_a_committed_neighbour(store_root):
    store = await _store(store_root, "staged-finds-committed", {"y": [1.0, 0.0, 0.0]})
    await store.upsert(ids=["x"], embeddings=_vec(1.0, 0.01, 0.0), metadatas=[{}])

    result = await store.self_knn(top_k=1, ids=["x"])

    assert list(result) == ["x"]
    assert [n["id"] for n in result["x"]] == ["y"]


async def test_a_committed_id_finds_a_staged_neighbour(store_root):
    store = await _store(store_root, "committed-finds-staged", {"y": [1.0, 0.0, 0.0]})
    await store.upsert(ids=["x"], embeddings=_vec(1.0, 0.01, 0.0), metadatas=[{}])

    result = await store.self_knn(top_k=1, ids=["y"])

    assert [n["id"] for n in result["y"]] == ["x"]


async def test_an_id_staged_for_deletion_is_never_returned_or_queried(store_root):
    store = await _store(
        store_root, "deleted", {"y": [1.0, 0.0, 0.0], "z": [0.0, 1.0, 0.0], "w": [0.9, 0.1, 0.0]}
    )
    await store.upsert(ids=["x"], embeddings=_vec(1.0, 0.01, 0.0), metadatas=[{}])
    await store.delete_by_ids(["y"])

    result = await store.self_knn(top_k=2, ids=["x", "y"])

    assert list(result) == ["x"]
    assert "y" not in [n["id"] for n in result["x"]]
    assert [n["id"] for n in result["x"]] == ["w", "z"]


async def test_a_staged_upsert_of_a_committed_id_is_scored_with_its_staged_vector(store_root):
    store = await _store(
        store_root, "shadowed", {"a": [1.0, 0.0, 0.0], "b": [0.0, 1.0, 0.0], "c": [0.0, 0.0, 1.0]}
    )
    # a moves next to b; its committed vector must no longer be what anything is scored against
    await store.upsert(ids=["a"], embeddings=_vec(0.0, 1.0, 0.01), metadatas=[{}])

    from_b = await store.self_knn(top_k=1, ids=["b"])
    from_a = await store.self_knn(top_k=1, ids=["a"])

    assert [n["id"] for n in from_b["b"]] == ["a"]
    assert from_b["b"][0]["score"] > 0.99
    assert [n["id"] for n in from_a["a"]] == ["b"]


async def test_the_query_id_is_not_its_own_neighbour_and_ties_sort_by_id(store_root):
    store = await _store(store_root, "ties", {"b": [1.0, 0.0, 0.0], "a": [1.0, 0.0, 0.0]})
    await store.upsert(ids=["q"], embeddings=_vec(1.0, 0.0, 0.0), metadatas=[{}])

    result = await store.self_knn(top_k=5, ids=["q"])

    assert [n["id"] for n in result["q"]] == ["a", "b"]


async def test_ids_omitted_keeps_one_batched_search_and_ignores_staged_vectors(store_root):
    store = await _store(store_root, "default-path", {"y": [1.0, 0.0, 0.0], "z": [0.0, 1.0, 0.0]})
    await store.upsert(ids=["x"], embeddings=_vec(1.0, 0.01, 0.0), metadatas=[{}])

    result = await store.self_knn(top_k=2)

    assert set(result) == {"y", "z"}
    assert "x" not in [n["id"] for neighbours in result.values() for n in neighbours]


async def test_no_committed_index_with_staged_ids_still_returns_matches(store_root):
    store = await _store(store_root, "no-index", {})
    await store.upsert(
        ids=["p", "q"],
        embeddings=np.array([[1.0, 0.0, 0.0], [1.0, 0.01, 0.0]], dtype="float32"),
        metadatas=[{}, {}],
    )

    result = await store.self_knn(top_k=1, ids=["p"])

    assert [n["id"] for n in result["p"]] == ["q"]


async def test_unknown_ids_are_skipped(store_root):
    store = await _store(store_root, "unknown", {"y": [1.0, 0.0, 0.0]})

    assert await store.self_knn(top_k=1, ids=["nope"]) == {}


async def test_a_non_positive_top_k_is_refused_before_anything_else(store_root):
    store = await _store(store_root, "bad-k", {})
    errors: list[BaseException] = []
    for k in (0, -1):
        try:
            await store.self_knn(top_k=k, ids=["x"])
        except InvalidTopKError as exc:
            errors.append(exc)

    assert len(errors) == 2
