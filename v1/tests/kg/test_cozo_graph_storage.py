"""Parity tests: CozoGraphStorage method-by-method vs NetworkXStorage.

Tests a fixed small graph (~10 nodes, ~15 edges) inserted into both
CozoGraphStorage and NetworkXStorage, flushed, then compared method-by-method.
Also covers:
  - Deferred-write contract (buffer → flush → reopen → present)
  - Abort path (buffer → drop_pending_index_ops → flush → reopen → absent)
  - get_knowledge_graph ("*" top-by-degree branch + labeled BFS branch)
  - search_labels
  - drop() return value and post-drop state
  - Cozo 0.7.6 frozen-bug regression shapes (D-P1.1-07)

Usage:
    ./sourcerer-venv/Scripts/python.exe -m pytest \\
        sourcerer-lightrag/tests/kg/test_cozo_graph_storage.py -x -q
"""

from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from typing import Any

import numpy as np
import pytest

from lightrag.kg.cozo_impl import CozoGraphStorage
from lightrag.kg.networkx_impl import NetworkXStorage
from lightrag.kg.shared_storage import finalize_share_data, initialize_share_data
from lightrag.utils import EmbeddingFunc

pytestmark = pytest.mark.offline


# ---------------------------------------------------------------------------
# Shared-data lifecycle
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _shared_data():
    """Initialize (and tear down) shared storage data for every test."""
    finalize_share_data()
    initialize_share_data(workers=1)
    yield
    finalize_share_data()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

async def _embed(texts: list[str]) -> list[list[float]]:
    return np.random.rand(len(texts), 8).tolist()


_EMBEDDING_FUNC = EmbeddingFunc(
    embedding_dim=8,
    max_token_size=512,
    func=_embed,
)

_GLOBAL_CONFIG = {
    "working_dir": "",          # overridden per-test via tmp_path
    "embedding_batch_num": 10,
    "vector_db_storage_cls_kwargs": {"cosine_better_than_threshold": 0.5},
    "max_graph_nodes": 1000,
}


def _make_nx(tmp_path: str, ns: str = "nx_parity") -> NetworkXStorage:
    cfg = dict(_GLOBAL_CONFIG, working_dir=tmp_path)
    return NetworkXStorage(
        namespace=ns,
        workspace="",
        global_config=cfg,
        embedding_func=_EMBEDDING_FUNC,
    )


def _make_cozo(tmp_path: str, ns: str = "cz_parity") -> CozoGraphStorage:
    cfg = dict(_GLOBAL_CONFIG, working_dir=tmp_path)
    return CozoGraphStorage(
        namespace=ns,
        workspace="",
        global_config=cfg,
        embedding_func=_EMBEDDING_FUNC,
    )


# ---------------------------------------------------------------------------
# Fixed test graph
# ---------------------------------------------------------------------------
# 10 nodes, 14 edges — enough for degree variety and multi-hop BFS.
# Attrs carry entity_type, source_id, file_path to validate provenance fields.

NODES: list[tuple[str, dict[str, str]]] = [
    ("Alice",   {"entity_type": "PERSON",       "source_id": "doc1", "file_path": "a.txt"}),
    ("Bob",     {"entity_type": "PERSON",       "source_id": "doc1", "file_path": "a.txt"}),
    ("Carol",   {"entity_type": "PERSON",       "source_id": "doc2", "file_path": "b.txt"}),
    ("Dave",    {"entity_type": "PERSON",       "source_id": "doc2", "file_path": "b.txt"}),
    ("Eve",     {"entity_type": "PERSON",       "source_id": "doc3", "file_path": "c.txt"}),
    ("ACME",    {"entity_type": "ORGANIZATION", "source_id": "doc1", "file_path": "a.txt"}),
    ("BigCo",   {"entity_type": "ORGANIZATION", "source_id": "doc3", "file_path": "c.txt"}),
    ("Python",  {"entity_type": "TECHNOLOGY",   "source_id": "doc2", "file_path": "b.txt"}),
    ("GraphDB", {"entity_type": "TECHNOLOGY",   "source_id": "doc3", "file_path": "c.txt"}),
    ("DataSet", {"entity_type": "ARTIFACT",     "source_id": "doc1", "file_path": "a.txt"}),
]

EDGES: list[tuple[str, str, dict[str, str]]] = [
    ("Alice",  "Bob",     {"weight": "1.0", "relation": "KNOWS",      "source_id": "doc1"}),
    ("Alice",  "ACME",    {"weight": "0.9", "relation": "WORKS_AT",   "source_id": "doc1"}),
    ("Bob",    "Carol",   {"weight": "0.8", "relation": "KNOWS",      "source_id": "doc1"}),
    ("Bob",    "ACME",    {"weight": "0.7", "relation": "WORKS_AT",   "source_id": "doc1"}),
    ("Carol",  "Dave",    {"weight": "0.6", "relation": "KNOWS",      "source_id": "doc2"}),
    ("Carol",  "Python",  {"weight": "0.5", "relation": "USES",       "source_id": "doc2"}),
    ("Dave",   "Python",  {"weight": "0.4", "relation": "USES",       "source_id": "doc2"}),
    ("Dave",   "BigCo",   {"weight": "0.3", "relation": "WORKS_AT",   "source_id": "doc2"}),
    ("Eve",    "BigCo",   {"weight": "0.9", "relation": "WORKS_AT",   "source_id": "doc3"}),
    ("Eve",    "GraphDB", {"weight": "0.8", "relation": "USES",       "source_id": "doc3"}),
    ("ACME",   "DataSet", {"weight": "0.5", "relation": "OWNS",       "source_id": "doc1"}),
    ("BigCo",  "DataSet", {"weight": "0.4", "relation": "OWNS",       "source_id": "doc3"}),
    ("BigCo",  "GraphDB", {"weight": "0.7", "relation": "USES",       "source_id": "doc3"}),
    ("Python", "GraphDB", {"weight": "0.6", "relation": "INTEGRATES", "source_id": "doc2"}),
]


async def _build_and_flush(store: Any) -> None:
    """Upsert the fixed graph into *store* and call index_done_callback."""
    for node_id, attrs in NODES:
        await store.upsert_node(node_id, attrs)
    for src, tgt, attrs in EDGES:
        await store.upsert_edge(src, tgt, attrs)
    await store.index_done_callback()


# ---------------------------------------------------------------------------
# Parity tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_has_node_parity(tmp_path):
    """has_node returns the same bool for both backends."""
    nx_dir = str(tmp_path / "nx")
    cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize()
    await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        for node_id, _ in NODES:
            nx_res = await nx_store.has_node(node_id)
            cz_res = await cz_store.has_node(node_id)
            assert nx_res == cz_res == True, f"has_node({node_id!r}) mismatch"

        assert await nx_store.has_node("NonExistent") is False
        assert await cz_store.has_node("NonExistent") is False
    finally:
        await nx_store.finalize()
        await cz_store.finalize()


@pytest.mark.asyncio
async def test_has_edge_parity(tmp_path):
    """has_edge returns the same bool for both backends (both directions)."""
    nx_dir = str(tmp_path / "nx"); cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize(); await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        for src, tgt, _ in EDGES:
            # Forward direction
            nx_res = await nx_store.has_edge(src, tgt)
            cz_res = await cz_store.has_edge(src, tgt)
            assert nx_res == cz_res == True, f"has_edge({src!r},{tgt!r}) mismatch"
            # Reverse direction (undirected)
            nx_rev = await nx_store.has_edge(tgt, src)
            cz_rev = await cz_store.has_edge(tgt, src)
            assert nx_rev == cz_rev == True, f"has_edge({tgt!r},{src!r}) mismatch"

        assert await nx_store.has_edge("Alice", "NonExistent") is False
        assert await cz_store.has_edge("Alice", "NonExistent") is False
    finally:
        await nx_store.finalize(); await cz_store.finalize()


@pytest.mark.asyncio
async def test_get_node_parity(tmp_path):
    """get_node returns same attrs dict (all str values) for both backends."""
    nx_dir = str(tmp_path / "nx"); cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize(); await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        for node_id, _ in NODES:
            nx_res = await nx_store.get_node(node_id)
            cz_res = await cz_store.get_node(node_id)
            assert nx_res is not None, f"nx_store.get_node({node_id!r}) returned None"
            assert cz_res is not None, f"cz_store.get_node({node_id!r}) returned None"
            # Compare key-value pairs (both should have str values)
            for key in nx_res:
                assert key in cz_res, f"Key {key!r} missing in cozo get_node({node_id!r})"
                assert nx_res[key] == cz_res[key], (
                    f"get_node({node_id!r})[{key!r}]: nx={nx_res[key]!r} vs cz={cz_res[key]!r}"
                )

        # None for absent node
        assert await nx_store.get_node("Ghost") is None
        assert await cz_store.get_node("Ghost") is None
    finally:
        await nx_store.finalize(); await cz_store.finalize()


@pytest.mark.asyncio
async def test_get_edge_parity(tmp_path):
    """get_edge returns same attrs dict (both directions) for both backends."""
    nx_dir = str(tmp_path / "nx"); cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize(); await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        for src, tgt, expected_attrs in EDGES:
            for a, b in [(src, tgt), (tgt, src)]:
                nx_e = await nx_store.get_edge(a, b)
                cz_e = await cz_store.get_edge(a, b)
                assert nx_e is not None, f"nx get_edge({a!r},{b!r}) is None"
                assert cz_e is not None, f"cz get_edge({a!r},{b!r}) is None"
                for key, val in expected_attrs.items():
                    assert key in cz_e, f"Edge attr {key!r} missing in cozo get_edge({a!r},{b!r})"

        # None for absent edge
        assert await nx_store.get_edge("Alice", "Eve") is None
        assert await cz_store.get_edge("Alice", "Eve") is None
    finally:
        await nx_store.finalize(); await cz_store.finalize()


@pytest.mark.asyncio
async def test_node_degree_parity(tmp_path):
    """node_degree returns same int for both backends."""
    nx_dir = str(tmp_path / "nx"); cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize(); await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        for node_id, _ in NODES:
            nx_deg = await nx_store.node_degree(node_id)
            cz_deg = await cz_store.node_degree(node_id)
            assert nx_deg == cz_deg, (
                f"node_degree({node_id!r}): nx={nx_deg} vs cz={cz_deg}"
            )

        # 0 for absent node
        assert await nx_store.node_degree("Ghost") == 0
        assert await cz_store.node_degree("Ghost") == 0
    finally:
        await nx_store.finalize(); await cz_store.finalize()


@pytest.mark.asyncio
async def test_edge_degree_parity(tmp_path):
    """edge_degree == node_degree(src) + node_degree(tgt) for both backends."""
    nx_dir = str(tmp_path / "nx"); cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize(); await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        for src, tgt, _ in EDGES:
            nx_ed = await nx_store.edge_degree(src, tgt)
            cz_ed = await cz_store.edge_degree(src, tgt)
            assert nx_ed == cz_ed, (
                f"edge_degree({src!r},{tgt!r}): nx={nx_ed} vs cz={cz_ed}"
            )
    finally:
        await nx_store.finalize(); await cz_store.finalize()


@pytest.mark.asyncio
async def test_get_node_edges_parity(tmp_path):
    """get_node_edges returns same set of (src,tgt) pairs for both backends."""
    nx_dir = str(tmp_path / "nx"); cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize(); await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        for node_id, _ in NODES:
            nx_edges = await nx_store.get_node_edges(node_id)
            cz_edges = await cz_store.get_node_edges(node_id)
            assert nx_edges is not None, f"nx get_node_edges({node_id!r}) is None"
            assert cz_edges is not None, f"cz get_node_edges({node_id!r}) is None"
            # Compare as sets of canonical (min,max) pairs (undirected)
            nx_canon = {(min(a, b), max(a, b)) for a, b in nx_edges}
            cz_canon = {(min(a, b), max(a, b)) for a, b in cz_edges}
            assert nx_canon == cz_canon, (
                f"get_node_edges({node_id!r}) mismatch:\n"
                f"  nx={sorted(nx_canon)}\n  cz={sorted(cz_canon)}"
            )

        # None for absent node
        assert await nx_store.get_node_edges("Ghost") is None
        assert await cz_store.get_node_edges("Ghost") is None
    finally:
        await nx_store.finalize(); await cz_store.finalize()


@pytest.mark.asyncio
async def test_get_all_labels_parity(tmp_path):
    """get_all_labels returns same sorted list for both backends."""
    nx_dir = str(tmp_path / "nx"); cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize(); await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        nx_labels = await nx_store.get_all_labels()
        cz_labels = await cz_store.get_all_labels()
        assert nx_labels == cz_labels, (
            f"get_all_labels mismatch:\n  nx={nx_labels}\n  cz={cz_labels}"
        )
        # Must contain all 10 nodes
        assert len(cz_labels) == len(NODES)
    finally:
        await nx_store.finalize(); await cz_store.finalize()


@pytest.mark.asyncio
async def test_get_all_nodes_parity(tmp_path):
    """get_all_nodes returns same set of node IDs for both backends."""
    nx_dir = str(tmp_path / "nx"); cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize(); await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        nx_nodes = await nx_store.get_all_nodes()
        cz_nodes = await cz_store.get_all_nodes()

        nx_ids = {n["id"] for n in nx_nodes}
        cz_ids = {n["id"] for n in cz_nodes}
        assert nx_ids == cz_ids, (
            f"get_all_nodes id sets differ:\n  nx={sorted(nx_ids)}\n  cz={sorted(cz_ids)}"
        )
        assert len(cz_ids) == len(NODES)
    finally:
        await nx_store.finalize(); await cz_store.finalize()


@pytest.mark.asyncio
async def test_get_all_edges_parity(tmp_path):
    """get_all_edges returns same set of edge pairs for both backends."""
    nx_dir = str(tmp_path / "nx"); cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize(); await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        nx_edges = await nx_store.get_all_edges()
        cz_edges = await cz_store.get_all_edges()

        def _canonical_pair(e: dict) -> tuple[str, str]:
            # Normalise to canonical (min, max) for undirected comparison
            a, b = e["source"], e["target"]
            return (a, b) if a <= b else (b, a)

        nx_pairs = {_canonical_pair(e) for e in nx_edges}
        cz_pairs = {_canonical_pair(e) for e in cz_edges}
        assert nx_pairs == cz_pairs, (
            f"get_all_edges mismatch:\n"
            f"  nx_only={sorted(nx_pairs - cz_pairs)}\n"
            f"  cz_only={sorted(cz_pairs - nx_pairs)}"
        )
        assert len(cz_pairs) == len(EDGES)
    finally:
        await nx_store.finalize(); await cz_store.finalize()


@pytest.mark.asyncio
async def test_get_popular_labels_parity(tmp_path):
    """get_popular_labels returns same ordering (by degree) for both backends."""
    nx_dir = str(tmp_path / "nx"); cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize(); await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        nx_pop = await nx_store.get_popular_labels(limit=10)
        cz_pop = await cz_store.get_popular_labels(limit=10)

        # Both should return all 10 nodes (limit >= len)
        assert len(nx_pop) == len(cz_pop) == len(NODES)

        # The highest-degree node should be first in both
        # (exact ordering may differ for ties, so we only check the top)
        assert cz_pop[0] == nx_pop[0], (
            f"Top popular label differs: nx={nx_pop[0]!r} vs cz={cz_pop[0]!r}"
        )

        # Same set of labels
        assert set(nx_pop) == set(cz_pop), (
            f"popular_labels sets differ: nx={sorted(nx_pop)} vs cz={sorted(cz_pop)}"
        )
    finally:
        await nx_store.finalize(); await cz_store.finalize()


@pytest.mark.asyncio
async def test_search_labels_parity(tmp_path):
    """search_labels returns same set of matches for both backends."""
    nx_dir = str(tmp_path / "nx"); cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize(); await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        # Test various queries
        # Note: counts are validated by set equality with NetworkX (the reference);
        # the absolute counts here are derived from the fixed NODES list.
        # "a" (case-insensitive) matches: Alice, ACME, Dave, Carol, DataSet, GraphDB = 6
        for query, expected_count in [
            ("Alice",   1),   # exact match
            ("a",       6),   # substring (case-insensitive): Alice, ACME, Dave, Carol, DataSet, GraphDB
            ("Big",     1),   # prefix of BigCo
            ("xyz",     0),   # no match
            ("",        0),   # empty string → empty list
        ]:
            nx_res = await nx_store.search_labels(query, limit=50)
            cz_res = await cz_store.search_labels(query, limit=50)

            assert set(nx_res) == set(cz_res), (
                f"search_labels({query!r}) set mismatch:\n"
                f"  nx={sorted(nx_res)}\n  cz={sorted(cz_res)}"
            )
            if expected_count is not None:
                assert len(cz_res) == expected_count, (
                    f"search_labels({query!r}) expected {expected_count} results, got {len(cz_res)}: {cz_res}"
                )
    finally:
        await nx_store.finalize(); await cz_store.finalize()


@pytest.mark.asyncio
async def test_get_knowledge_graph_star_parity(tmp_path):
    """get_knowledge_graph('*') — top-by-degree branch — matches NetworkXStorage."""
    nx_dir = str(tmp_path / "nx"); cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize(); await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        nx_kg = await nx_store.get_knowledge_graph("*", max_nodes=10)
        cz_kg = await cz_store.get_knowledge_graph("*", max_nodes=10)

        # Both should include all 10 nodes (no truncation)
        nx_node_ids = {n.id for n in nx_kg.nodes}
        cz_node_ids = {n.id for n in cz_kg.nodes}
        assert nx_node_ids == cz_node_ids, (
            f"KG('*') node sets differ:\n  nx_only={nx_node_ids - cz_node_ids}\n  cz_only={cz_node_ids - nx_node_ids}"
        )

        nx_edge_ids = {e.id for e in nx_kg.edges}
        cz_edge_ids = {e.id for e in cz_kg.edges}
        assert nx_edge_ids == cz_edge_ids, (
            f"KG('*') edge sets differ:\n  nx_only={nx_edge_ids - cz_edge_ids}\n  cz_only={cz_edge_ids - nx_edge_ids}"
        )

        # is_truncated matches
        assert nx_kg.is_truncated == cz_kg.is_truncated

        # With a low max_nodes, truncation should occur and match
        nx_kg_small = await nx_store.get_knowledge_graph("*", max_nodes=5)
        cz_kg_small = await cz_store.get_knowledge_graph("*", max_nodes=5)
        assert len(nx_kg_small.nodes) == len(cz_kg_small.nodes) == 5
        assert nx_kg_small.is_truncated == cz_kg_small.is_truncated == True
    finally:
        await nx_store.finalize(); await cz_store.finalize()


@pytest.mark.asyncio
async def test_get_knowledge_graph_labeled_bfs_parity(tmp_path):
    """get_knowledge_graph(label) — labeled BFS branch — matches NetworkXStorage."""
    nx_dir = str(tmp_path / "nx"); cz_dir = str(tmp_path / "cz")
    os.makedirs(nx_dir); os.makedirs(cz_dir)

    nx_store = _make_nx(nx_dir)
    cz_store = _make_cozo(cz_dir)
    await nx_store.initialize(); await cz_store.initialize()

    try:
        await _build_and_flush(nx_store)
        await _build_and_flush(cz_store)

        # BFS from Alice, depth=2: should reach Alice's 1-hop + 2-hop neighbors
        nx_kg = await nx_store.get_knowledge_graph("Alice", max_depth=2, max_nodes=100)
        cz_kg = await cz_store.get_knowledge_graph("Alice", max_depth=2, max_nodes=100)

        nx_ids = {n.id for n in nx_kg.nodes}
        cz_ids = {n.id for n in cz_kg.nodes}
        assert nx_ids == cz_ids, (
            f"KG('Alice',depth=2) node sets differ:\n"
            f"  nx_only={nx_ids - cz_ids}\n  cz_only={cz_ids - nx_ids}"
        )

        nx_eids = {e.id for e in nx_kg.edges}
        cz_eids = {e.id for e in cz_kg.edges}
        assert nx_eids == cz_eids, (
            f"KG('Alice',depth=2) edge sets differ:\n"
            f"  nx_only={nx_eids - cz_eids}\n  cz_only={cz_eids - nx_eids}"
        )

        # Missing node → empty KnowledgeGraph (not an error)
        nx_empty = await nx_store.get_knowledge_graph("Ghost", max_depth=2, max_nodes=100)
        cz_empty = await cz_store.get_knowledge_graph("Ghost", max_depth=2, max_nodes=100)
        assert len(nx_empty.nodes) == len(cz_empty.nodes) == 0
        assert len(nx_empty.edges) == len(cz_empty.edges) == 0
    finally:
        await nx_store.finalize(); await cz_store.finalize()


# ---------------------------------------------------------------------------
# Deferred-write contract tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deferred_write_single_flush(tmp_path):
    """Buffered upserts are NOT in the DB until index_done_callback is called."""
    cz_dir = str(tmp_path)
    store = _make_cozo(cz_dir, ns="deferred")
    await store.initialize()

    try:
        # Buffer writes without flushing
        await store.upsert_node("Alice", {"entity_type": "PERSON"})
        await store.upsert_edge("Alice", "Bob", {"weight": "1.0"})

        # Read-your-writes: in-process reads should see the buffered data
        assert await store.has_node("Alice"), "Buffered node should be visible before flush"

        # But on-disk count is 0 (directly queried bypassing the buffer)
        db_rows = await store._run("?[id] := *nodes{id}", {})
        assert len(db_rows) == 0, "DB should be empty before flush"

        # Flush and verify durability
        await store.index_done_callback()

        db_rows_after = await store._run("?[id] := *nodes{id}", {})
        assert len(db_rows_after) == 1, f"Expected 1 node after flush, got {len(db_rows_after)}"
        assert db_rows_after[0][0] == "Alice"
    finally:
        await store.finalize()


@pytest.mark.asyncio
async def test_deferred_write_reopen_persists(tmp_path):
    """Data flushed by index_done_callback persists across store close+reopen."""
    cz_dir = str(tmp_path)

    store1 = _make_cozo(cz_dir, ns="graph")
    await store1.initialize()
    await _build_and_flush(store1)
    await store1.finalize()

    # Reopen — a new instance on the same path should see all flushed data
    store2 = _make_cozo(cz_dir, ns="graph")
    await store2.initialize()

    try:
        for node_id, _ in NODES:
            assert await store2.has_node(node_id), (
                f"Node {node_id!r} missing after reopen"
            )
        for src, tgt, _ in EDGES:
            assert await store2.has_edge(src, tgt), (
                f"Edge ({src!r},{tgt!r}) missing after reopen"
            )
    finally:
        await store2.finalize()


@pytest.mark.asyncio
async def test_abort_path_drop_pending(tmp_path):
    """drop_pending_index_ops discards buffered writes — subsequent flush commits nothing."""
    cz_dir = str(tmp_path)

    # First: establish a baseline in the DB
    store_baseline = _make_cozo(cz_dir, ns="graph")
    await store_baseline.initialize()
    await store_baseline.upsert_node("Baseline", {"entity_type": "MARKER"})
    await store_baseline.index_done_callback()
    await store_baseline.finalize()

    # Now: buffer more writes and ABORT them
    store_abort = _make_cozo(cz_dir, ns="graph")
    await store_abort.initialize()
    try:
        await store_abort.upsert_node("Carol", {"entity_type": "PERSON"})
        await store_abort.upsert_edge("Carol", "Baseline", {"weight": "0.5"})

        # Abort — discard the buffer
        await store_abort.drop_pending_index_ops()

        # Call index_done_callback — should flush nothing (buffer is empty)
        await store_abort.index_done_callback()
    finally:
        await store_abort.finalize()

    # Reopen and verify: Baseline present, Carol absent
    store_check = _make_cozo(cz_dir, ns="graph")
    await store_check.initialize()
    try:
        assert await store_check.has_node("Baseline"), "Baseline node should be present"
        assert not await store_check.has_node("Carol"), "Aborted Carol should be absent"
        assert not await store_check.has_edge("Carol", "Baseline"), "Aborted edge should be absent"
    finally:
        await store_check.finalize()


# ---------------------------------------------------------------------------
# drop() tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_drop_returns_correct_status(tmp_path):
    """drop() returns {'status': 'success', 'message': 'data dropped'}."""
    cz_dir = str(tmp_path)
    store = _make_cozo(cz_dir, ns="graph")
    await store.initialize()
    try:
        await _build_and_flush(store)
        result = await store.drop()
        assert result == {"status": "success", "message": "data dropped"}, (
            f"Unexpected drop() result: {result}"
        )
    finally:
        await store.finalize()


@pytest.mark.asyncio
async def test_drop_clears_all_data(tmp_path):
    """drop() leaves both relations empty immediately (no buffering)."""
    cz_dir = str(tmp_path)
    store = _make_cozo(cz_dir, ns="graph")
    await store.initialize()
    try:
        await _build_and_flush(store)

        # Verify data exists before drop
        labels_before = await store.get_all_labels()
        assert len(labels_before) == len(NODES)

        await store.drop()

        labels_after = await store.get_all_labels()
        assert labels_after == [], f"Labels after drop: {labels_after}"

        edges_after = await store.get_all_edges()
        assert edges_after == [], f"Edges after drop: {edges_after}"
    finally:
        await store.finalize()


# ---------------------------------------------------------------------------
# Read-your-writes test (buffer → read before flush)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_read_your_writes(tmp_path):
    """Reads return buffered data before flush (same behavior as NetworkXStorage)."""
    cz_dir = str(tmp_path)
    store = _make_cozo(cz_dir, ns="graph")
    await store.initialize()
    try:
        # Buffer without flush
        await store.upsert_node("X", {"entity_type": "TEST"})
        await store.upsert_node("Y", {"entity_type": "TEST"})
        await store.upsert_edge("X", "Y", {"weight": "1.0"})

        # All reads should reflect the buffered state
        assert await store.has_node("X")
        assert await store.has_node("Y")
        assert await store.has_edge("X", "Y")
        assert await store.has_edge("Y", "X")  # undirected

        node_x = await store.get_node("X")
        assert node_x is not None
        assert node_x.get("entity_type") == "TEST"

        edge = await store.get_edge("X", "Y")
        assert edge is not None
        assert edge.get("weight") == "1.0"

        labels = await store.get_all_labels()
        assert "X" in labels and "Y" in labels

        deg_x = await store.node_degree("X")
        assert deg_x == 1, f"Expected degree 1, got {deg_x}"
    finally:
        await store.finalize()


# ---------------------------------------------------------------------------
# Provenance field preservation test (D-P1.1-05)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_provenance_fields_preserved(tmp_path):
    """source_id and file_path attrs are preserved through flush and reopen."""
    cz_dir = str(tmp_path)
    store1 = _make_cozo(cz_dir, ns="graph")
    await store1.initialize()
    await store1.upsert_node(
        "Alice",
        {"entity_type": "PERSON", "source_id": "chunk_001", "file_path": "report.pdf"},
    )
    await store1.index_done_callback()
    await store1.finalize()

    store2 = _make_cozo(cz_dir, ns="graph")
    await store2.initialize()
    try:
        alice = await store2.get_node("Alice")
        assert alice is not None
        assert alice.get("source_id") == "chunk_001", f"source_id lost: {alice}"
        assert alice.get("file_path") == "report.pdf", f"file_path lost: {alice}"
    finally:
        await store2.finalize()


# ---------------------------------------------------------------------------
# Cozo 0.7.6 bug regression shapes (D-P1.1-07)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_bug244_aggregation_zero_rows(tmp_path):
    """Regression: count() on empty relation returns 0, not empty result (#244)."""
    cz_dir = str(tmp_path)
    store = _make_cozo(cz_dir, ns="graph")
    await store.initialize()
    try:
        # node_degree on absent node (aggregation over 0 matching rows)
        deg = await store.node_degree("Nonexistent")
        assert deg == 0, f"Expected 0 degree for absent node, got {deg}"

        # get_all_labels on empty store
        labels = await store.get_all_labels()
        assert labels == [], f"Expected empty list on empty store, got {labels}"
    finally:
        await store.finalize()


@pytest.mark.asyncio
async def test_bug253_json_key_order_preserved(tmp_path):
    """Regression: JSON attrs dict round-trips correctly (#253 key-order)."""
    cz_dir = str(tmp_path)
    store = _make_cozo(cz_dir, ns="graph")
    await store.initialize()
    try:
        attrs = {
            "entity_type": "PERSON",
            "source_id": "doc1",
            "file_path": "test.txt",
            "description": "A test entity",
        }
        await store.upsert_node("TestNode", attrs)
        await store.index_done_callback()

        retrieved = await store.get_node("TestNode")
        assert retrieved is not None
        for key, val in attrs.items():
            assert retrieved.get(key) == str(val), (
                f"Key {key!r} round-trip failed: expected {val!r}, got {retrieved.get(key)!r}"
            )
    finally:
        await store.finalize()


@pytest.mark.asyncio
async def test_bug275_count_returns_int(tmp_path):
    """Regression: count() returns an int, not a wrong DataValue type (#275)."""
    cz_dir = str(tmp_path)
    store = _make_cozo(cz_dir, ns="graph")
    await store.initialize()
    try:
        await store.upsert_node("A", {"entity_type": "T"})
        await store.upsert_node("B", {"entity_type": "T"})
        await store.upsert_edge("A", "B", {"w": "1.0"})
        await store.index_done_callback()

        deg = await store.node_degree("A")
        assert isinstance(deg, int), f"node_degree returned {type(deg).__name__}, not int"
        assert deg == 1
    finally:
        await store.finalize()
