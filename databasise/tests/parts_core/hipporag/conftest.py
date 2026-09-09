"""Shared fixtures for HippoRAG 2 part tests and the cross-modality seam test.

``seeded_hipporag_store`` mirrors ``databasise/tests/seam/conftest.py``'s own
``synthetic_naive_store`` shape exactly: writes through the v2 stores' own public write paths only
(``FaissVectorStore.upsert``, ``SqliteKVStore.upsert``, ``CozoGraphStore.upsert_node``/
``upsert_edge``) — never a file copy and never a v1 artifact — so a test in this directory, or in
``tests/seam/`` (via an explicit cross-package import: ``tests/`` has no top-level ``__init__.py``,
so ``parts_core`` is importable as a top-level package once any test under ``tests/`` has been
collected), can drive a real HippoRAG run with no network and no real index.

Graph shape: three entity ("phrase") vertices, two chunk ("passage") vertices, weighted edges
between them — the minimal hand-checkable shape 06-01-PLAN.md's own Task 2 action text names.
"""

from __future__ import annotations

import numpy as np
import pytest

from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore

_WORKSPACE = "hipporag-test"
_GRAPH_NAMESPACE = "hipporag-graph"
_KV_NAMESPACE = "hipporag-text-chunks"
_FACTS_NAMESPACE = "hipporag-facts"
_CHUNKS_NAMESPACE = "hipporag-chunks"

# The query vector every stub embedding client in this directory returns — aligned with fact
# "f1" and chunk "chunk:c1", so the happy-path retrieval chain has an unambiguous top hit.
QUERY_VECTOR = [1.0, 0.0, 0.0]


@pytest.fixture
async def seeded_hipporag_store(store_root):
    graph_store = CozoGraphStore(
        namespace=_GRAPH_NAMESPACE, workspace=_WORKSPACE, store_root=store_root
    )
    await graph_store.upsert_node("entity:cat", {})
    await graph_store.upsert_node("entity:mat", {})
    await graph_store.upsert_node("entity:sat", {})
    await graph_store.upsert_node("chunk:c1", {})
    await graph_store.upsert_node("chunk:c2", {})
    await graph_store.upsert_edge("entity:cat", "entity:mat", {"weight": 2.0})
    await graph_store.upsert_edge("entity:mat", "chunk:c1", {"weight": 1.0})
    await graph_store.upsert_edge("entity:cat", "chunk:c1", {"weight": 1.0})
    await graph_store.upsert_edge("chunk:c1", "chunk:c2", {"weight": 0.5})
    await graph_store.upsert_edge("entity:sat", "chunk:c2", {"weight": 1.0})
    await graph_store.index_done_callback()
    await graph_store.finalize()

    facts_store = FaissVectorStore(
        namespace=_FACTS_NAMESPACE, workspace=_WORKSPACE, store_root=store_root
    )
    await facts_store.upsert(
        ids=["f1", "f2"],
        embeddings=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        metadatas=[
            {"entities": ["entity:cat", "entity:mat"]},
            {"entities": ["entity:sat"]},
        ],
    )
    await facts_store.index_done_callback()
    await facts_store.finalize()

    chunks_store = FaissVectorStore(
        namespace=_CHUNKS_NAMESPACE, workspace=_WORKSPACE, store_root=store_root
    )
    await chunks_store.upsert(
        ids=["chunk:c1", "chunk:c2"],
        embeddings=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        metadatas=[{}, {}],
    )
    await chunks_store.index_done_callback()
    await chunks_store.finalize()

    kv_store = SqliteKVStore(
        namespace=_KV_NAMESPACE, workspace=_WORKSPACE, store_root=store_root
    )
    await kv_store.upsert(
        {
            "fact:f1": {"chunk_ids": ["chunk:c1"]},
            "fact:f2": {"chunk_ids": ["chunk:c2"]},
            "chunk:c1": {"content": "Cats sit on mats."},
            "chunk:c2": {"content": "The cat sat on the mat again."},
        }
    )
    await kv_store.index_done_callback()
    await kv_store.finalize()

    return {
        "store_root": store_root,
        "workspace": _WORKSPACE,
        "query_vector": QUERY_VECTOR,
    }


@pytest.fixture
def seeded_hipporag_source_documents() -> list[dict[str, str]]:
    """Three short source documents (06-02-PLAN.md Task 1) whose entities overlap across
    documents — "cat", "mat" and "rug" each recur — so 06-05's shared-entity edge cases (an entity
    introduced by one document's findings, referenced again by another's) have real data to
    exercise instead of three disjoint one-entity graphs.
    """
    return [
        {"document_id": "doc-1", "text": "The cat sat on the mat."},
        {"document_id": "doc-2", "text": "The cat also likes the rug near the mat."},
        {"document_id": "doc-3", "text": "A dog sat on the rug."},
    ]
