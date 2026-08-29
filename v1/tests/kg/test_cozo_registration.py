"""test_cozo_registration.py — Plan 01.1-03 registration assertions.

Verifies that:
  (a) get_storage_class("CozoGraphStorage") resolves to the correct class.
  (b) The library-level LightRAG dataclass default graph_storage == "CozoGraphStorage".
  (c) The API-config default DefaultRAGStorageConfig.GRAPH_STORAGE == "CozoGraphStorage".
  (d) The vector default resolves to FaissVectorDBStorage (exact IndexFlatIP cosine, D-P1.1-03).
  (e) STORAGE_ENV_REQUIREMENTS["CozoGraphStorage"] == [] (embedded, no external service, T-01.1-07).
  (f) NetworkXStorage is still registered in the factory (parity baseline, D-P1.1-01).

No real database or LLM is constructed — these are pure registry/import assertions.
"""

from __future__ import annotations

import dataclasses

import pytest


# ---------------------------------------------------------------------------
# (a) Factory resolution — CozoGraphStorage
# ---------------------------------------------------------------------------

def test_get_storage_class_resolves_cozo():
    from lightrag.kg.factory import get_storage_class

    cls = get_storage_class("CozoGraphStorage")
    assert cls.__name__ == "CozoGraphStorage", (
        f"Expected CozoGraphStorage, got {cls.__name__}"
    )


def test_cozo_storage_class_is_subclass_of_base():
    from lightrag.base import BaseGraphStorage
    from lightrag.kg.factory import get_storage_class

    cls = get_storage_class("CozoGraphStorage")
    assert issubclass(cls, BaseGraphStorage), (
        "CozoGraphStorage must subclass BaseGraphStorage"
    )


# ---------------------------------------------------------------------------
# (b) Library-level dataclass default — graph_storage
# ---------------------------------------------------------------------------

def test_lightrag_dataclass_graph_storage_default():
    """LightRAG dataclass default for graph_storage must be CozoGraphStorage."""
    from lightrag.lightrag import LightRAG

    fields = {f.name: f for f in dataclasses.fields(LightRAG)}
    graph_field = fields.get("graph_storage")
    assert graph_field is not None, "LightRAG has no graph_storage field"
    default_val = graph_field.default
    assert default_val == "CozoGraphStorage", (
        f"LightRAG.graph_storage default is '{default_val}', expected 'CozoGraphStorage'"
    )


# ---------------------------------------------------------------------------
# (c) API-config default — DefaultRAGStorageConfig.GRAPH_STORAGE
# ---------------------------------------------------------------------------

def test_api_config_graph_storage_default():
    from lightrag.api.config import DefaultRAGStorageConfig

    assert DefaultRAGStorageConfig.GRAPH_STORAGE == "CozoGraphStorage", (
        f"DefaultRAGStorageConfig.GRAPH_STORAGE is "
        f"'{DefaultRAGStorageConfig.GRAPH_STORAGE}', expected 'CozoGraphStorage'"
    )


# ---------------------------------------------------------------------------
# (d) Vector default — FaissVectorDBStorage with IndexFlatIP (D-P1.1-03)
# ---------------------------------------------------------------------------

def test_lightrag_dataclass_vector_storage_default():
    """LightRAG dataclass default for vector_storage must be FaissVectorDBStorage."""
    from lightrag.lightrag import LightRAG

    fields = {f.name: f for f in dataclasses.fields(LightRAG)}
    vec_field = fields.get("vector_storage")
    assert vec_field is not None, "LightRAG has no vector_storage field"
    default_val = vec_field.default
    assert default_val == "FaissVectorDBStorage", (
        f"LightRAG.vector_storage default is '{default_val}', expected 'FaissVectorDBStorage'"
    )


def test_api_config_vector_storage_default():
    from lightrag.api.config import DefaultRAGStorageConfig

    assert DefaultRAGStorageConfig.VECTOR_STORAGE == "FaissVectorDBStorage", (
        f"DefaultRAGStorageConfig.VECTOR_STORAGE is "
        f"'{DefaultRAGStorageConfig.VECTOR_STORAGE}', expected 'FaissVectorDBStorage'"
    )


def test_get_storage_class_resolves_faiss():
    from lightrag.kg.factory import get_storage_class

    cls = get_storage_class("FaissVectorDBStorage")
    assert cls.__name__ == "FaissVectorDBStorage", (
        f"Expected FaissVectorDBStorage, got {cls.__name__}"
    )


def test_faiss_uses_indexflatip():
    """FaissVectorDBStorage must use IndexFlatIP (exact cosine), not an approximate index."""
    import inspect

    from lightrag.kg.faiss_impl import FaissVectorDBStorage

    source = inspect.getsource(FaissVectorDBStorage)
    assert "IndexFlatIP" in source, (
        "FaissVectorDBStorage source does not contain IndexFlatIP — "
        "D-P1.1-03 requires exact cosine (IndexFlatIP), not an approximate index"
    )
    # Confirm no approximate index types slipped in
    for approx in ("IndexIVF", "IndexHNSW", "IndexPQ"):
        assert approx not in source, (
            f"Approximate index type '{approx}' found in FaissVectorDBStorage — "
            "v1 must use exact cosine search only (D-P1.1-03)"
        )


# ---------------------------------------------------------------------------
# (e) STORAGE_ENV_REQUIREMENTS — CozoGraphStorage == [] (T-01.1-07)
# ---------------------------------------------------------------------------

def test_cozo_env_requirements_empty():
    """CozoGraphStorage must have no required env vars (embedded, no external service)."""
    from lightrag.kg import STORAGE_ENV_REQUIREMENTS

    reqs = STORAGE_ENV_REQUIREMENTS.get("CozoGraphStorage")
    assert reqs is not None, "CozoGraphStorage missing from STORAGE_ENV_REQUIREMENTS"
    assert reqs == [], (
        f"STORAGE_ENV_REQUIREMENTS['CozoGraphStorage'] = {reqs!r}, expected []"
    )


# ---------------------------------------------------------------------------
# (f) NetworkXStorage still registered (parity baseline, D-P1.1-01)
# ---------------------------------------------------------------------------

def test_networkx_still_registered_in_implementations():
    from lightrag.kg import STORAGE_IMPLEMENTATIONS

    impls = STORAGE_IMPLEMENTATIONS["GRAPH_STORAGE"]["implementations"]
    assert "NetworkXStorage" in impls, (
        "NetworkXStorage must remain in STORAGE_IMPLEMENTATIONS (parity baseline)"
    )


def test_networkx_still_resolvable_via_factory():
    from lightrag.kg.factory import get_storage_class

    cls = get_storage_class("NetworkXStorage")
    assert cls.__name__ == "NetworkXStorage", (
        f"Expected NetworkXStorage, got {cls.__name__}"
    )


# ---------------------------------------------------------------------------
# (g) Registry dict completeness cross-check
# ---------------------------------------------------------------------------

def test_cozo_in_all_three_registry_dicts():
    from lightrag.kg import STORAGE_ENV_REQUIREMENTS, STORAGE_IMPLEMENTATIONS, STORAGES

    assert "CozoGraphStorage" in STORAGE_IMPLEMENTATIONS["GRAPH_STORAGE"]["implementations"]
    assert "CozoGraphStorage" in STORAGE_ENV_REQUIREMENTS
    assert "CozoGraphStorage" in STORAGES
    assert STORAGES["CozoGraphStorage"] == ".kg.cozo_impl"
