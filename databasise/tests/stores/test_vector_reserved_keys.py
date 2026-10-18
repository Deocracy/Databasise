"""STOR-16 (D-11): metadata keys ``id`` and ``score`` are refused at ``FaissVectorStore.upsert``, so
no metadata can shadow a result's real id or score, and the v1 importer strips them from v1 data.
"""

from __future__ import annotations

import json

import faiss
import numpy as np
import pytest

from databasise.parity.import_index import _import_vector_kind
from databasise.stores.vector import FaissVectorStore, ReservedMetadataKeyError


@pytest.mark.parametrize(
    ("metadata", "keys"),
    [
        ({"id": "SHADOW", "score": 99}, ["id", "score"]),
        ({"id": "x"}, ["id"]),
        ({"score": 1}, ["score"]),
    ],
)
async def test_reserved_metadata_keys_are_refused_before_buffering(store_root, metadata, keys):
    store = FaissVectorStore(namespace="chunks", workspace="ws", store_root=store_root)
    with pytest.raises(ReservedMetadataKeyError) as info:
        await store.upsert(["a"], [[1.0, 0.0, 0.0]], [metadata])
    assert isinstance(info.value, ValueError)
    assert info.value.keys == keys
    assert store._pending == {}
    await store.index_done_callback()
    assert store.get_by_id("a") is None


async def test_results_carry_the_real_id_and_score(store_root):
    store = FaissVectorStore(namespace="chunks", workspace="ws", store_root=store_root)
    await store.upsert(
        ["a", "b"], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], [{"content": "ok"}, {"content": "b"}]
    )
    await store.index_done_callback()

    assert store.get_by_id("a") == {"id": "a", "content": "ok"}
    top = (await store.query([1.0, 0.0, 0.0], top_k=1))[0]
    assert top["id"] == "a"
    assert isinstance(top["score"], float)
    assert top["score"] == pytest.approx(1.0)
    assert {r["id"] for r in await store.score_all([1.0, 0.0, 0.0])} == {"a", "b"}
    knn = await store.self_knn(top_k=1)
    assert knn["a"][0]["id"] == "b"
    assert knn["b"][0]["id"] == "a"


async def test_v1_import_strips_reserved_keys(tmp_path, store_root):
    v1_dir = tmp_path / "v1"
    v1_dir.mkdir()
    index = faiss.IndexFlatIP(3)
    index.add(np.array([[1.0, 0.0, 0.0]], dtype="float32"))
    faiss.write_index(index, str(v1_dir / "faiss_index_chunks.index"))
    (v1_dir / "faiss_index_chunks.index.meta.json").write_text(
        json.dumps({"0": {"__id__": "c1", "id": "SHADOW", "score": 99, "content": "x"}}),
        encoding="utf-8",
    )

    await _import_vector_kind("chunks", v1_dir, store_root, "ws")

    store = FaissVectorStore(namespace="chunks", workspace="ws", store_root=store_root)
    assert store.get_by_id("c1") == {"id": "c1", "content": "x"}
