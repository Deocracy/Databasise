"""Shared fixtures for ``databasise/tests/seam/``.

``synthetic_naive_store`` builds the same minimal, synthetic imported-store shape
``databasise/tests/parity/test_naive_arm_end_to_end.py`` builds — directly through the v2 stores'
own public write paths (``FaissVectorStore.upsert``, ``SqliteKVStore.upsert``), never a file copy
or a real v1 build — so every test in this directory that needs a real seven-node ``naive`` run
can drive ``databasise.seam.Databasise`` against it with no network and no ``v1/`` artifacts.
"""

from __future__ import annotations

import numpy as np
import pytest

from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore

_CONTENT = "Ed Wood directed several low-budget films."


@pytest.fixture
async def synthetic_naive_store(store_root):
    workspace = "seam-test"
    query_vector = [1.0, 0.0, 0.0]

    vector_store = FaissVectorStore(namespace="chunks", workspace=workspace, store_root=store_root)
    await vector_store.upsert(
        ids=["chunk-1"],
        embeddings=np.array([query_vector]),
        metadatas=[{"content": _CONTENT}],
    )
    await vector_store.index_done_callback()

    kv_store = SqliteKVStore(namespace="text_chunks", workspace=workspace, store_root=store_root)
    await kv_store.upsert({"chunk-1": {"content": _CONTENT, "file_path": "ed_wood.txt"}})
    await kv_store.index_done_callback()

    return {"store_root": store_root, "workspace": workspace, "query_vector": query_vector}
