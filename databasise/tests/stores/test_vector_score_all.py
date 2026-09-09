"""06-01-PLAN.md Task 3: ``FaissVectorStore.score_all`` is a genuinely different capability from
``query`` — never a top-k truncation, one scored entry per stored vector, and never composed by
calling ``query`` in a loop.
"""

from __future__ import annotations

import numpy as np

from databasise.stores.vector import FaissVectorStore

_WORKSPACE = "score-all-test"


async def _seeded_store(store_root, count: int) -> FaissVectorStore:
    store = FaissVectorStore(namespace="vecs", workspace=_WORKSPACE, store_root=store_root)
    ids = [f"v{i}" for i in range(count)]
    rng = np.random.default_rng(seed=42)
    embeddings = rng.random((count, 8)).astype("float32")
    await store.upsert(ids=ids, embeddings=embeddings, metadatas=[{} for _ in ids])
    await store.index_done_callback()
    return store


async def test_score_all_returns_one_entry_per_stored_vector_never_a_top_k_truncation(store_root):
    store = await _seeded_store(store_root, count=25)
    query_vector = np.ones(8, dtype="float32")

    results = await store.score_all(query_vector)

    assert len(results) == 25
    ids = {r["id"] for r in results}
    assert ids == {f"v{i}" for i in range(25)}


async def test_score_all_is_sorted_descending_with_id_tie_break(store_root):
    store = await _seeded_store(store_root, count=25)
    query_vector = np.ones(8, dtype="float32")

    results = await store.score_all(query_vector)

    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    # Tie-break check: group consecutive equal-score runs and confirm each run's ids ascend.
    i = 0
    while i < len(results):
        j = i
        while j < len(results) and results[j]["score"] == results[i]["score"]:
            j += 1
        tied_ids = [results[k]["id"] for k in range(i, j)]
        assert tied_ids == sorted(tied_ids)
        i = j


async def test_score_all_and_query_are_visibly_different_capabilities_against_the_same_store(
    store_root,
):
    store = await _seeded_store(store_root, count=25)
    query_vector = np.ones(8, dtype="float32")

    all_scored = await store.score_all(query_vector)
    top_5 = await store.query(query_vector, top_k=5)

    assert len(all_scored) == 25
    assert len(top_5) == 5
    # query()'s top-5 ids are a subset of score_all()'s own top-5 by score.
    top_5_from_all = {r["id"] for r in all_scored[:5]}
    assert {r["id"] for r in top_5} == top_5_from_all
