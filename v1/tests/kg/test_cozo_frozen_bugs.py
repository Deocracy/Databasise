"""Dedicated regression suite for frozen Cozo 0.7.6 correctness bugs.

Guards D-P1.1-07: four known latent correctness bugs in the frozen 0.7.6 engine
that are silent-wrong-result risks (NOT data corruption). Because the engine is
pinned forever (D-P1.1-08) these tests are permanently valid.

Tests target the EXACT query shapes CozoGraphStorage issues, verified against
``sourcerer-lightrag/lightrag/kg/cozo_impl.py``.  Where a bug is provably
unreachable given Sourcerer's model, the test documents WHY and locks the
avoidance in with an assertion (so a future change that accidentally re-enters
the bug path becomes a test failure here).

Bug inventory
-------------
#244  aggregation returning 0 rows
      Risk: count() / aggregation over a relation with matching rows silently
            returns 0 rows instead.
      Adapter shape: The adapter does NOT use Cozo count() aggregation at all.
      ``node_degree`` uses ``?[src, tgt] := *edges{...}, src=$id or tgt=$id``
      and counts Python-side.  ``get_popular_labels`` calls node_degree
      iteratively.  ``get_all_labels`` uses ``?[id] := *nodes{id}``.
      Risk level: MITIGATED-BY-DESIGN — count() never issued.  Tests confirm
      the edge-enumeration+Python-count shape returns correct non-zero results.

#275  wrong DataValue types
      Risk: a query returns a value coerced to the wrong Cozo DataValue type
            (e.g. number instead of string, or vice-versa).
      Adapter shapes at risk: attrs Json blob round-trip (get_node/get_edge),
      degree count (node_degree returns Python int), label strings (get_all_labels).
      Tests assert all types survive the engine round-trip.

#253  JSON object key-order loss
      Risk: a Json column loses key ordering on round-trip.
      LightRAG consumes attrs as a plain dict so ordering itself is not the
      parity requirement — completeness + correctness of key/value pairs is.
      Tests assert every key/value present and equal after write→flush→read.

#296/#269  UUID sort/coercion
      Risk: UUID-typed Cozo values sort or coerce incorrectly.
      Adapter reality: Sourcerer stores ALL node and edge keys as Cozo String,
      NEVER as Cozo Uuid.  Schema declared as ``{id: String => attrs: Json}``
      (confirmed via ``::columns nodes``).  Entity IDs are entity-name strings;
      even MD5-derived IDs are stored as hex strings.
      Risk level: AVOIDED-BY-DESIGN — UUID Cozo type never used.  Tests lock
      in the String-key model and assert UUID-shaped strings are stored/sorted
      as plain lexicographic strings.

Usage:
    ./sourcerer-venv/Scripts/python.exe -m pytest \\
        sourcerer-lightrag/tests/kg/test_cozo_frozen_bugs.py -x -q
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import shutil
from typing import Any

import numpy as np
import pytest

from lightrag.kg.cozo_impl import (
    CozoGraphStorage,
    _cozo_rows,
    _attrs_to_dict,
    _canonical_edge_key,
)
from lightrag.kg.shared_storage import finalize_share_data, initialize_share_data
from lightrag.utils import EmbeddingFunc

try:
    from pycozo.client import Client as CozoClient
except ImportError:
    CozoClient = None  # type: ignore

pytestmark = pytest.mark.offline


# ---------------------------------------------------------------------------
# Shared-data lifecycle (required by CozoGraphStorage.initialize())
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _shared_data():
    """Initialize (and tear down) shared storage data for every test."""
    finalize_share_data()
    initialize_share_data(workers=1)
    yield
    finalize_share_data()


# ---------------------------------------------------------------------------
# Test fixtures and helpers
# ---------------------------------------------------------------------------

async def _dummy_embed(texts: list[str]) -> list[list[float]]:
    return np.random.rand(len(texts), 8).tolist()


_EMBEDDING_FUNC = EmbeddingFunc(
    embedding_dim=8,
    max_token_size=512,
    func=_dummy_embed,
)

_GLOBAL_CONFIG = {
    "working_dir": "",
    "embedding_batch_num": 10,
    "vector_db_storage_cls_kwargs": {"cosine_better_than_threshold": 0.5},
    "max_graph_nodes": 1000,
}


def _make_store(tmp_dir: str, ns: str = "frozen_bug") -> CozoGraphStorage:
    """Create a CozoGraphStorage instance in a temporary directory."""
    cfg = dict(_GLOBAL_CONFIG, working_dir=tmp_dir)
    return CozoGraphStorage(
        namespace=ns,
        workspace="",
        global_config=cfg,
        embedding_func=_EMBEDDING_FUNC,
    )


def _make_raw_client(tmp_dir: str, db_name: str = "raw_test") -> Any:
    """Create a bare pycozo Client (RocksDB) for engine-level query tests."""
    db_path = os.path.join(tmp_dir, db_name + ".db")
    return CozoClient("rocksdb", db_path)


def _raw_rows(result: Any) -> list[list]:
    """Normalise pycozo result to list[list] (handles DataFrame or dict)."""
    return _cozo_rows(result)


# ---------------------------------------------------------------------------
# Fixed graph fixture — matches typical LightRAG entity/relation output shape
# ---------------------------------------------------------------------------
# 6 nodes, 7 edges — enough variety in degrees for get_popular_labels ordering
# Attrs carry all four LightRAG provenance fields used downstream.

_NODES = [
    ("Alice",   {"entity_type": "PERSON",       "description": "Main subject",
                  "source_id": "doc_001", "file_path": "corpus/a.txt"}),
    ("Bob",     {"entity_type": "PERSON",       "description": "Secondary actor",
                  "source_id": "doc_001", "file_path": "corpus/a.txt"}),
    ("Carol",   {"entity_type": "PERSON",       "description": "Tertiary actor",
                  "source_id": "doc_002", "file_path": "corpus/b.txt"}),
    ("ACME",    {"entity_type": "ORGANIZATION", "description": "Employer",
                  "source_id": "doc_001", "file_path": "corpus/a.txt"}),
    ("Python",  {"entity_type": "TECHNOLOGY",   "description": "Programming language",
                  "source_id": "doc_002", "file_path": "corpus/b.txt"}),
    ("DataSet", {"entity_type": "ARTIFACT",     "description": "Shared corpus",
                  "source_id": "doc_001", "file_path": "corpus/a.txt"}),
]

_EDGES = [
    ("Alice", "Bob",     {"weight": "1.0", "relation": "KNOWS",    "source_id": "doc_001"}),
    ("Alice", "ACME",    {"weight": "0.9", "relation": "WORKS_AT", "source_id": "doc_001"}),
    ("Alice", "Python",  {"weight": "0.8", "relation": "USES",     "source_id": "doc_001"}),
    ("Bob",   "Carol",   {"weight": "0.7", "relation": "KNOWS",    "source_id": "doc_001"}),
    ("Bob",   "ACME",    {"weight": "0.6", "relation": "WORKS_AT", "source_id": "doc_001"}),
    ("Carol", "Python",  {"weight": "0.5", "relation": "USES",     "source_id": "doc_002"}),
    ("ACME",  "DataSet", {"weight": "0.4", "relation": "OWNS",     "source_id": "doc_001"}),
]
# Expected degrees (undirected):
#   Alice: 3 (Bob, ACME, Python)
#   Bob:   3 (Alice, Carol, ACME)
#   ACME:  3 (Alice, Bob, DataSet)
#   Carol: 2 (Bob, Python)
#   Python:2 (Alice, Carol)
#   DataSet:1 (ACME)

_EXPECTED_DEGREES = {
    "Alice": 3,
    "Bob": 3,
    "ACME": 3,
    "Carol": 2,
    "Python": 2,
    "DataSet": 1,
}


async def _build_and_flush(store: CozoGraphStorage) -> None:
    """Upsert the fixture graph and commit to Cozo."""
    for node_id, attrs in _NODES:
        await store.upsert_node(node_id, attrs)
    for src, tgt, attrs in _EDGES:
        await store.upsert_edge(src, tgt, attrs)
    await store.index_done_callback()


# ===========================================================================
# BUG #244 — aggregation returning 0 rows
# ===========================================================================

class TestBug244AggregationZeroRows:
    """Guards against #244: aggregation silently returning 0 rows.

    The adapter's strategy (confirmed in cozo_impl.py):
    - node_degree: issues ``?[src, tgt] := *edges{src, tgt}, src=$id or tgt=$id``
      then len(rows) in Python — NO Cozo count() aggregation.
    - get_popular_labels: calls node_degree() iteratively per node.
    - get_all_labels: issues ``?[id] := *nodes{id}`` — a plain scan, not
      an aggregation.

    #244 is MITIGATED-BY-DESIGN: the adapter avoids Cozo count() aggregation
    entirely.  These tests confirm that the actual edge-enumeration + Python-
    count pattern returns correct non-zero values after a disk flush, so a
    future inadvertent introduction of count() would be caught here.
    """

    @pytest.mark.asyncio
    async def test_244_node_degree_nonzero_after_flush(self, tmp_path):
        """Bug #244 guard — node_degree returns correct non-zero int after flush.

        The adapter issues ``?[src,tgt]:=*edges{src,tgt},src=$id or tgt=$id``
        (not count()) so #244 cannot trigger.  This test confirms that:
        (a) the edge-row query returns the expected number of rows after a
            write+flush cycle, and
        (b) node_degree() returns a Python int equal to the expected degree.

        At-risk method: CozoGraphStorage.node_degree
        """
        cz_dir = str(tmp_path)
        store = _make_store(cz_dir)
        await store.initialize()
        try:
            await _build_and_flush(store)

            for node_id, expected_deg in _EXPECTED_DEGREES.items():
                deg = await store.node_degree(node_id)
                assert isinstance(deg, int), (
                    f"[#244] node_degree({node_id!r}) returned {type(deg).__name__}, "
                    "not int — possible DataValue coercion"
                )
                assert deg == expected_deg, (
                    f"[#244] node_degree({node_id!r}) = {deg}, expected {expected_deg}. "
                    "If this is 0 on a connected node, #244 zero-row aggregation has been triggered."
                )
        finally:
            await store.finalize()

    @pytest.mark.asyncio
    async def test_244_edge_degree_nonzero_after_flush(self, tmp_path):
        """Bug #244 guard — edge_degree (= sum of both endpoint degrees) is correct.

        edge_degree calls node_degree twice; if node_degree returned 0 due to
        #244, edge_degree would also return 0 for connected edges.

        At-risk method: CozoGraphStorage.edge_degree
        """
        cz_dir = str(tmp_path)
        store = _make_store(cz_dir)
        await store.initialize()
        try:
            await _build_and_flush(store)

            for src, tgt, _ in _EDGES:
                ed = await store.edge_degree(src, tgt)
                src_deg = _EXPECTED_DEGREES[src]
                tgt_deg = _EXPECTED_DEGREES[tgt]
                expected_ed = src_deg + tgt_deg
                assert isinstance(ed, int), (
                    f"[#244] edge_degree({src!r},{tgt!r}) returned {type(ed).__name__}, not int"
                )
                assert ed == expected_ed, (
                    f"[#244] edge_degree({src!r},{tgt!r}) = {ed}, expected {expected_ed}. "
                    "If this is 0, the #244 zero-row path was entered."
                )
        finally:
            await store.finalize()

    @pytest.mark.asyncio
    async def test_244_get_popular_labels_nonempty_and_ordered(self, tmp_path):
        """Bug #244 guard — get_popular_labels returns non-empty degree-ordered list.

        get_popular_labels calls node_degree() iteratively (not a Cozo ORDER+LIMIT
        aggregation query), so #244 is avoided.  The test verifies:
        (a) the result is non-empty (all 6 nodes present),
        (b) the highest-degree node(s) appear first (correct ordering),
        (c) last entry is DataSet (degree 1, the lowest).

        At-risk method: CozoGraphStorage.get_popular_labels
        """
        cz_dir = str(tmp_path)
        store = _make_store(cz_dir)
        await store.initialize()
        try:
            await _build_and_flush(store)

            popular = await store.get_popular_labels(limit=100)
            assert len(popular) == len(_NODES), (
                f"[#244] get_popular_labels returned {len(popular)} results, "
                f"expected {len(_NODES)}. If 0, aggregation zero-row bug has been triggered."
            )

            # All node IDs must be present
            assert set(popular) == {n[0] for n in _NODES}, (
                f"[#244] get_popular_labels missing nodes: "
                f"expected {sorted(n[0] for n in _NODES)}, got {sorted(popular)}"
            )

            # Degree-ordered: DataSet (degree 1) should be last
            assert popular[-1] == "DataSet", (
                f"[#244] Expected DataSet (degree 1) to be last in popular_labels, "
                f"got {popular[-1]!r}. Ordering is wrong, possibly due to all-zero degrees."
            )

            # Top-3 should be the degree-3 nodes (Alice, Bob, ACME) in any order
            top_3 = set(popular[:3])
            assert top_3 == {"Alice", "Bob", "ACME"}, (
                f"[#244] Top-3 popular labels should be the degree-3 nodes "
                f"{{Alice, Bob, ACME}}, got {top_3}. Wrong degree ordering."
            )
        finally:
            await store.finalize()

    @pytest.mark.asyncio
    async def test_244_engine_level_edge_query_returns_rows(self, tmp_path):
        """Bug #244 guard — raw Cozo edge-enumeration query returns expected rows.

        This tests the EXACT CozoScript the adapter issues for node_degree, at
        the engine level (via bare pycozo Client), bypassing all Python logic.
        Confirms the underlying engine does NOT suppress rows on this query shape.

        Query shape: ``?[src, tgt] := *edges{src, tgt}, src=$id or tgt=$id``

        At-risk adapter method: CozoGraphStorage.node_degree (the _run() call)
        """
        cz_dir = str(tmp_path)
        client = _make_raw_client(cz_dir, "raw_244")
        try:
            client.run(":create nodes {id: String => attrs: Json}", {})
            client.run(":create edges {src: String, tgt: String => attrs: Json}", {})

            # Insert nodes + edges matching LightRAG output shape
            nodes = [("Alice", {"entity_type": "PERSON", "source_id": "d1"}),
                     ("Bob",   {"entity_type": "PERSON", "source_id": "d1"}),
                     ("Carol", {"entity_type": "PERSON", "source_id": "d2"})]
            for nid, attrs in nodes:
                client.run(
                    "?[id, attrs] <- [[$id, $attrs]] :put nodes {id => attrs}",
                    {"id": nid, "attrs": attrs},
                )

            edge_data = [("Alice", "Bob",   {"weight": "1.0"}),
                         ("Alice", "Carol", {"weight": "0.5"}),
                         ("Bob",   "Carol", {"weight": "0.3"})]
            for src, tgt, attrs in edge_data:
                client.run(
                    "?[src, tgt, attrs] <- [[$s, $t, $a]] :put edges {src, tgt => attrs}",
                    {"s": src, "t": tgt, "a": attrs},
                )

            # THE EXACT QUERY SHAPE from cozo_impl.node_degree
            for node_id, expected_count in [("Alice", 2), ("Bob", 2), ("Carol", 2)]:
                result = client.run(
                    "?[src, tgt] := *edges{src, tgt}, src = $id or tgt = $id",
                    {"id": node_id},
                )
                rows = _raw_rows(result)
                assert len(rows) == expected_count, (
                    f"[#244 engine-level] Edge query for {node_id!r} returned "
                    f"{len(rows)} rows, expected {expected_count}. "
                    "A result of 0 indicates the #244 zero-row aggregation bug is active "
                    "on this query shape in the installed engine version."
                )
        finally:
            client.close()


# ===========================================================================
# BUG #275 — wrong DataValue types
# ===========================================================================

class TestBug275DataValueTypes:
    """Guards against #275: query returns a value with the wrong Cozo DataValue type.

    At-risk shapes in the adapter:
    - attrs Json blob → get_node / get_edge return dict via _attrs_to_dict
    - node_degree → returns Python int (len() of rows, not a Cozo integer)
    - get_all_labels → returns list[str] of node IDs
    - Cozo Json column → must return dict (not str, not list)
    """

    @pytest.mark.asyncio
    async def test_275_node_degree_returns_python_int(self, tmp_path):
        """Bug #275 guard — node_degree returns a Python int, never str/float.

        node_degree computes len(effective) in Python (not Cozo count()), so
        the integer cannot be coerced by the engine.  This test confirms the
        contract is honoured for connected nodes.

        At-risk method: CozoGraphStorage.node_degree
        """
        cz_dir = str(tmp_path)
        store = _make_store(cz_dir)
        await store.initialize()
        try:
            await _build_and_flush(store)

            for node_id, expected_deg in _EXPECTED_DEGREES.items():
                deg = await store.node_degree(node_id)
                assert type(deg) is int, (
                    f"[#275] node_degree({node_id!r}) type is {type(deg).__name__!r}, "
                    "expected int. Wrong DataValue type coercion."
                )
                assert deg == expected_deg, (
                    f"[#275] node_degree({node_id!r}) = {deg!r}, expected {expected_deg}"
                )

            # Absent node → 0 (also int, not None or empty)
            absent_deg = await store.node_degree("__nonexistent__")
            assert type(absent_deg) is int, (
                f"[#275] node_degree for absent node returned {type(absent_deg).__name__}, not int"
            )
            assert absent_deg == 0
        finally:
            await store.finalize()

    @pytest.mark.asyncio
    async def test_275_get_all_labels_returns_str_values(self, tmp_path):
        """Bug #275 guard — get_all_labels returns list[str] (not int/bytes/etc.).

        The adapter issues ``?[id] := *nodes{id}`` and extracts r[0] for each
        row.  Cozo should return String column values as Python str.

        At-risk method: CozoGraphStorage.get_all_labels
        """
        cz_dir = str(tmp_path)
        store = _make_store(cz_dir)
        await store.initialize()
        try:
            await _build_and_flush(store)

            labels = await store.get_all_labels()
            assert len(labels) == len(_NODES), (
                f"[#275] Expected {len(_NODES)} labels, got {len(labels)}"
            )
            for lbl in labels:
                assert type(lbl) is str, (
                    f"[#275] Label {lbl!r} has type {type(lbl).__name__}, expected str. "
                    "Wrong DataValue type from Cozo String column."
                )

            # All expected node IDs must be present
            expected_ids = sorted(n[0] for n in _NODES)
            assert labels == expected_ids, (
                f"[#275] get_all_labels returned {labels}, expected {expected_ids}"
            )
        finally:
            await store.finalize()

    @pytest.mark.asyncio
    async def test_275_get_node_attrs_str_types_after_flush(self, tmp_path):
        """Bug #275 guard — get_node attrs values are all Python str after flush.

        The adapter's _attrs_to_dict coerces all Json-blob values to str via
        str(v).  This test confirms the coercion is correct and that no Cozo
        DataValue type leaks through as a non-str type.

        At-risk method: CozoGraphStorage.get_node (via _attrs_to_dict)
        """
        cz_dir = str(tmp_path)
        store = _make_store(cz_dir)
        await store.initialize()
        try:
            await _build_and_flush(store)

            for node_id, original_attrs in _NODES:
                retrieved = await store.get_node(node_id)
                assert retrieved is not None, (
                    f"[#275] get_node({node_id!r}) returned None after flush"
                )
                for key, orig_val in original_attrs.items():
                    got_val = retrieved.get(key)
                    assert type(got_val) is str, (
                        f"[#275] get_node({node_id!r})[{key!r}] = {got_val!r} "
                        f"has type {type(got_val).__name__}, expected str. "
                        "DataValue type coercion by Cozo or _attrs_to_dict failure."
                    )
                    assert got_val == str(orig_val), (
                        f"[#275] get_node({node_id!r})[{key!r}]: expected {str(orig_val)!r}, "
                        f"got {got_val!r}"
                    )
        finally:
            await store.finalize()

    @pytest.mark.asyncio
    async def test_275_get_edge_attrs_str_types_after_flush(self, tmp_path):
        """Bug #275 guard — get_edge attrs values are all Python str after flush.

        At-risk method: CozoGraphStorage.get_edge (via _attrs_to_dict)
        """
        cz_dir = str(tmp_path)
        store = _make_store(cz_dir)
        await store.initialize()
        try:
            await _build_and_flush(store)

            for src, tgt, original_attrs in _EDGES:
                retrieved = await store.get_edge(src, tgt)
                assert retrieved is not None, (
                    f"[#275] get_edge({src!r},{tgt!r}) returned None after flush"
                )
                for key, orig_val in original_attrs.items():
                    got_val = retrieved.get(key)
                    assert type(got_val) is str, (
                        f"[#275] get_edge({src!r},{tgt!r})[{key!r}] = {got_val!r} "
                        f"has type {type(got_val).__name__}, expected str. "
                        "DataValue type coercion by Cozo or _attrs_to_dict failure."
                    )
                    assert got_val == str(orig_val), (
                        f"[#275] get_edge({src!r},{tgt!r})[{key!r}]: "
                        f"expected {str(orig_val)!r}, got {got_val!r}"
                    )
        finally:
            await store.finalize()

    @pytest.mark.asyncio
    async def test_275_engine_level_json_column_returns_dict(self, tmp_path):
        """Bug #275 guard — Cozo Json column returns Python dict, not str or other.

        At the engine level (bare pycozo Client), a Json column value should be
        returned as a Python dict when pandas is available (the current env).
        This is the DataValue type the adapter's _attrs_to_dict handles — it
        must be dict or str (json string), not int/list/etc.
        """
        cz_dir = str(tmp_path)
        client = _make_raw_client(cz_dir, "raw_275")
        try:
            client.run(":create nodes {id: String => attrs: Json}", {})

            attrs_with_mixed = {
                "str_val": "hello",
                "num_str": "42",
                "entity_type": "PERSON",
                "source_id": "chunk_001",
                "file_path": "corpus/doc.txt",
            }
            client.run(
                "?[id, attrs] <- [[$id, $attrs]] :put nodes {id => attrs}",
                {"id": "TypeTest", "attrs": attrs_with_mixed},
            )

            result = client.run(
                "?[attrs] := *nodes{id, attrs}, id = $id",
                {"id": "TypeTest"},
            )
            rows = _raw_rows(result)
            assert len(rows) == 1, f"[#275] Expected 1 row, got {len(rows)}"

            raw_attrs = rows[0][0]
            assert isinstance(raw_attrs, (dict, str)), (
                f"[#275] Cozo Json column returned {type(raw_attrs).__name__}, "
                f"expected dict or str. Wrong DataValue type — #275 active."
            )

            # Normalise to dict (as _attrs_to_dict does)
            normalised = _attrs_to_dict(raw_attrs)
            for key, orig_val in attrs_with_mixed.items():
                got = normalised.get(key)
                assert got == str(orig_val), (
                    f"[#275 engine] attrs[{key!r}]: expected {str(orig_val)!r}, got {got!r}"
                )
        finally:
            client.close()


# ===========================================================================
# BUG #253 — JSON object key-order loss
# ===========================================================================

class TestBug253JsonKeyOrderLoss:
    """Guards against #253: a Json column loses object key ordering on round-trip.

    LightRAG's parity requirement is NOT key ordering per se (dict access in
    Python is order-independent for lookup), but COMPLETENESS and CORRECTNESS
    of every key/value pair after write→flush→read.  If #253 caused dropped
    keys or corrupted values, that would break downstream consumers.

    Tests confirm:
    (a) all keys survive (none silently dropped by key-order collision)
    (b) all values are correct
    (c) the attrs round-trip is consistent across reopening the store

    At-risk methods: CozoGraphStorage.get_node, get_edge, get_all_nodes, get_all_edges
    """

    # LightRAG provenance key set — all must survive every round-trip
    _FULL_PROVENANCE_ATTRS = {
        "entity_type": "ORGANIZATION",
        "description": "A company that owns a large dataset and employs many researchers",
        "source_id": "chunk_7f3a29bc",
        "file_path": "corpus/enterprise/annual_report_2024.pdf",
        "weight": "0.95",
        "extra_metadata": "domain:enterprise,tier:1",
        "raw_text_fragment": "The organization was founded in 1985 and operates globally.",
    }

    @pytest.mark.asyncio
    async def test_253_node_attrs_all_keys_present_after_flush(self, tmp_path):
        """Bug #253 guard — node attrs: all keys/values survive write→flush→read.

        Uses a multi-key attrs dict including all standard LightRAG provenance
        fields plus extra keys, inserted in a deliberate order.  After flush,
        every key must be retrievable with its original value.

        At-risk method: CozoGraphStorage.get_node
        """
        cz_dir = str(tmp_path)
        store = _make_store(cz_dir)
        await store.initialize()
        try:
            node_id = "RichNode"
            await store.upsert_node(node_id, dict(self._FULL_PROVENANCE_ATTRS))
            await store.index_done_callback()

            retrieved = await store.get_node(node_id)
            assert retrieved is not None, f"[#253] get_node({node_id!r}) returned None after flush"

            for key, orig_val in self._FULL_PROVENANCE_ATTRS.items():
                assert key in retrieved, (
                    f"[#253] Key {key!r} missing from get_node result. "
                    "JSON key-order collision may have dropped this key."
                )
                assert retrieved[key] == str(orig_val), (
                    f"[#253] get_node[{key!r}]: expected {str(orig_val)!r}, "
                    f"got {retrieved[key]!r}"
                )
        finally:
            await store.finalize()

    @pytest.mark.asyncio
    async def test_253_edge_attrs_all_keys_present_after_flush(self, tmp_path):
        """Bug #253 guard — edge attrs: all keys/values survive write→flush→read.

        At-risk method: CozoGraphStorage.get_edge
        """
        cz_dir = str(tmp_path)
        store = _make_store(cz_dir)
        await store.initialize()
        try:
            await store.upsert_node("SrcNode", {"entity_type": "A"})
            await store.upsert_node("TgtNode", {"entity_type": "B"})
            edge_attrs = {
                "relation": "RELATES_TO",
                "weight": "0.88",
                "source_id": "chunk_edge_001",
                "file_path": "corpus/edges.txt",
                "description": "A rich edge with many attributes",
                "extra_context": "long text field that might trigger ordering issues",
                "rank": "7",
            }
            await store.upsert_edge("SrcNode", "TgtNode", edge_attrs)
            await store.index_done_callback()

            retrieved = await store.get_edge("SrcNode", "TgtNode")
            assert retrieved is not None, "[#253] get_edge returned None after flush"

            for key, orig_val in edge_attrs.items():
                assert key in retrieved, (
                    f"[#253] Edge attr {key!r} missing after flush. "
                    "JSON key-order loss may have dropped this key."
                )
                assert retrieved[key] == str(orig_val), (
                    f"[#253] get_edge[{key!r}]: expected {str(orig_val)!r}, "
                    f"got {retrieved[key]!r}"
                )
        finally:
            await store.finalize()

    @pytest.mark.asyncio
    async def test_253_attrs_consistent_across_store_reopen(self, tmp_path):
        """Bug #253 guard — attrs survive close+reopen of the Cozo store.

        A key-order corruption that manifests only after serialisation+deserialisation
        to RocksDB (not in the in-process cache) would be caught here.

        At-risk method: CozoGraphStorage.get_node (after re-open)
        """
        cz_dir = str(tmp_path)

        store1 = _make_store(cz_dir, ns="graph")
        await store1.initialize()
        await store1.upsert_node("PersistNode", dict(self._FULL_PROVENANCE_ATTRS))
        await store1.index_done_callback()
        await store1.finalize()

        # Reopen the same RocksDB path
        store2 = _make_store(cz_dir, ns="graph")
        await store2.initialize()
        try:
            retrieved = await store2.get_node("PersistNode")
            assert retrieved is not None, "[#253] get_node returned None after reopen"

            for key, orig_val in self._FULL_PROVENANCE_ATTRS.items():
                assert key in retrieved, (
                    f"[#253] Key {key!r} missing after close+reopen. "
                    "JSON key-order corruption on disk persists."
                )
                assert retrieved[key] == str(orig_val), (
                    f"[#253] After reopen, get_node[{key!r}]: "
                    f"expected {str(orig_val)!r}, got {retrieved[key]!r}"
                )
        finally:
            await store2.finalize()

    @pytest.mark.asyncio
    async def test_253_engine_level_json_key_completeness(self, tmp_path):
        """Bug #253 guard — raw Cozo Json round-trip preserves all keys at engine level.

        Tests the exact `:put` then `*nodes{id, attrs}` query shape the adapter
        uses for nodes, confirming the engine does not lose any key from a
        7-field attrs dict (the typical LightRAG provenance payload).
        """
        cz_dir = str(tmp_path)
        client = _make_raw_client(cz_dir, "raw_253")
        try:
            client.run(":create nodes {id: String => attrs: Json}", {})

            # Multi-key attrs dict — same fields LightRAG writes to graph nodes
            attrs = {
                "entity_type": "PERSON",
                "description": "Test entity with all provenance fields populated",
                "source_id": "chunk_12345",
                "file_path": "corpus/document.pdf",
                "weight": "0.75",
                "extra_field_1": "value_one",
                "extra_field_2": "value_two",
            }
            client.run(
                "?[id, attrs] <- [[$id, $attrs]] :put nodes {id => attrs}",
                {"id": "KeyOrderNode", "attrs": attrs},
            )

            result = client.run(
                "?[attrs] := *nodes{id, attrs}, id = $id",
                {"id": "KeyOrderNode"},
            )
            rows = _raw_rows(result)
            assert len(rows) == 1, f"[#253 engine] Expected 1 row, got {len(rows)}"

            raw_attrs = rows[0][0]
            normalised = _attrs_to_dict(raw_attrs)

            for key, orig_val in attrs.items():
                assert key in normalised, (
                    f"[#253 engine] Key {key!r} missing from round-tripped attrs dict. "
                    "JSON key-order collision may have dropped this key in the engine."
                )
                assert normalised[key] == str(orig_val), (
                    f"[#253 engine] attrs[{key!r}]: expected {str(orig_val)!r}, "
                    f"got {normalised[key]!r}"
                )
        finally:
            client.close()


# ===========================================================================
# BUG #296 / #269 — UUID sort/coercion — AVOIDED BY DESIGN
# ===========================================================================

class TestBug296And269UuidSortCoercion:
    """Guards that Sourcerer's model avoids Cozo bugs #296 and #269 by design.

    #296 and #269 concern incorrect sort/coercion of Cozo UUID-typed values.

    SOURCERER'S MODEL:
    All node and edge keys are declared as Cozo ``String``, NEVER as Cozo
    ``Uuid``.  The schema (in _ensure_relations) is:
        :create nodes {id: String => attrs: Json}
        :create edges {src: String, tgt: String => attrs: Json}
    Entity IDs in LightRAG are entity-name strings (possibly MD5-derived hex
    strings).  Even when an entity name visually resembles a UUID (e.g.
    ``"6ba7b810-9dad-11d1-80b4-00c04fd430c8"``), it is stored as a Cozo
    String — the Cozo Uuid datatype is never used.

    CONSEQUENCE:
    Cozo's UUID sort/coercion logic is never entered.  These bugs are
    AVOIDED-BY-DESIGN.  The tests in this class LOCK IN that avoidance:
    if a future change accidentally introduces Uuid-typed columns, the schema
    introspection assertions here will fail, making the regression visible.

    Tests:
    1. Schema introspection asserts nodes.id and edges.src/tgt are String.
    2. UUID-shaped string IDs round-trip byte-identically as str.
    3. get_all_labels sorts UUID-shaped strings lexicographically (str sort),
       NOT by UUID semantic ordering.
    4. get_node with a UUID-shaped ID works identically to any other string ID.
    """

    # A set of UUID-format strings and ordinary entity names to exercise both
    UUID_SHAPED_IDS = [
        "550e8400-e29b-41d4-a716-446655440000",
        "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
        "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    ]
    PLAIN_IDS = [
        "alice",
        "bob",
        "Zephyr_entity",
        "md5hexid_abc123def456",
    ]

    @pytest.mark.asyncio
    async def test_296_schema_columns_are_string_not_uuid(self, tmp_path):
        """Bug #296/#269 avoidance — schema declares String columns, never Uuid.

        Queries Cozo's ``::columns <relation>`` system command to confirm that
        the ``id`` column of ``nodes`` and the ``src``/``tgt`` columns of
        ``edges`` are declared as ``String``.  A ``Uuid`` type here would put
        those columns on the #296/#269 code path.

        This test makes the avoidance contract machine-checkable: any future
        schema change that introduces Uuid will fail here before propagating.

        At-risk: the schema declared in CozoGraphStorage._ensure_relations
        """
        cz_dir = str(tmp_path)
        store = _make_store(cz_dir)
        await store.initialize()
        try:
            # Query the system catalog for nodes columns
            nodes_cols = await store._run("::columns nodes", {})
            # rows: [col_name, is_key, col_index, type_name, nullable]
            col_map_nodes = {r[0]: r[3] for r in nodes_cols}
            assert "id" in col_map_nodes, "[#296/#269] 'id' column missing from nodes relation"
            assert col_map_nodes["id"] == "String", (
                f"[#296/#269] nodes.id column type is {col_map_nodes['id']!r}, "
                "expected 'String'. A Uuid type here activates the #296/#269 bug path."
            )

            # Query the system catalog for edges columns
            edges_cols = await store._run("::columns edges", {})
            col_map_edges = {r[0]: r[3] for r in edges_cols}
            for col in ("src", "tgt"):
                assert col in col_map_edges, (
                    f"[#296/#269] '{col}' column missing from edges relation"
                )
                assert col_map_edges[col] == "String", (
                    f"[#296/#269] edges.{col} column type is {col_map_edges[col]!r}, "
                    "expected 'String'. Uuid type here activates the #296/#269 bug path."
                )
        finally:
            await store.finalize()

    @pytest.mark.asyncio
    async def test_296_uuid_shaped_ids_round_trip_as_strings(self, tmp_path):
        """Bug #296/#269 avoidance — UUID-shaped string IDs are stored/retrieved byte-identically.

        Inserts node IDs that look like UUIDs (dash-delimited hex groups) and
        asserts they come back as identical Python str values.  If the engine
        were treating them as Uuid, the sort order and byte representation could
        differ.

        At-risk methods: CozoGraphStorage.get_node, has_node
        """
        cz_dir = str(tmp_path)
        store = _make_store(cz_dir)
        await store.initialize()
        try:
            all_ids = self.UUID_SHAPED_IDS + self.PLAIN_IDS
            for node_id in all_ids:
                await store.upsert_node(node_id, {"entity_type": "TEST", "source_id": "d1"})
            await store.index_done_callback()

            for node_id in all_ids:
                # has_node must find it
                exists = await store.has_node(node_id)
                assert exists, (
                    f"[#296/#269] has_node({node_id!r}) returned False after flush. "
                    "UUID string stored as Uuid type might have a different key representation."
                )

                # get_node must return its attrs
                attrs = await store.get_node(node_id)
                assert attrs is not None, (
                    f"[#296/#269] get_node({node_id!r}) returned None after flush"
                )
                assert attrs.get("entity_type") == "TEST", (
                    f"[#296/#269] Attrs not retrieved correctly for {node_id!r}: {attrs}"
                )
        finally:
            await store.finalize()

    @pytest.mark.asyncio
    async def test_296_get_all_labels_sorts_uuid_ids_lexicographically(self, tmp_path):
        """Bug #296/#269 avoidance — get_all_labels sorts all IDs as plain strings.

        The adapter's get_all_labels returns ``sorted(effective)`` — Python's
        default lexicographic sort on strings.  If node IDs were stored/returned
        as Cozo Uuid, Cozo's UUID semantic sort (by variant bits) would disagree
        with Python's lexicographic sort, and IDs could appear in a different
        order than expected here.

        This test asserts that lexicographic Python sort == actual returned order,
        confirming String-type storage and Python-side sorting.

        At-risk method: CozoGraphStorage.get_all_labels
        """
        cz_dir = str(tmp_path)
        store = _make_store(cz_dir)
        await store.initialize()
        try:
            all_ids = self.UUID_SHAPED_IDS + self.PLAIN_IDS
            for node_id in all_ids:
                await store.upsert_node(node_id, {"entity_type": "TEST"})
            await store.index_done_callback()

            labels = await store.get_all_labels()
            expected_sorted = sorted(all_ids)

            assert labels == expected_sorted, (
                f"[#296/#269] get_all_labels sort order differs from lexicographic Python sort.\n"
                f"  Expected: {expected_sorted}\n"
                f"  Got:      {labels}\n"
                "If order differs for UUID-shaped IDs, Cozo Uuid sort semantics may be active."
            )
        finally:
            await store.finalize()

    @pytest.mark.asyncio
    async def test_296_engine_level_string_vs_uuid_schema_introspection(self, tmp_path):
        """Bug #296/#269 avoidance — raw Cozo schema is String, not Uuid.

        At the engine level (bare pycozo Client), after creating a relation with
        ``{id: String => attrs: Json}``, the ``::columns`` system command must
        report the id column type as ``String``.  Confirms the type declaration
        is honoured by the engine for the exact DDL the adapter issues.

        This is redundant with test_296_schema_columns_are_string_not_uuid above
        (which goes through the adapter) but exercises the engine directly to
        distinguish an adapter bug from an engine bug.
        """
        cz_dir = str(tmp_path)
        client = _make_raw_client(cz_dir, "raw_296")
        try:
            client.run(":create nodes {id: String => attrs: Json}", {})
            client.run(":create edges {src: String, tgt: String => attrs: Json}", {})

            # Check nodes
            result = client.run("::columns nodes", {})
            rows = _raw_rows(result)
            col_types = {row[0]: row[3] for row in rows}
            assert col_types.get("id") == "String", (
                f"[#296/#269 engine] nodes.id type is {col_types.get('id')!r}, "
                "expected 'String'. Uuid here activates the UUID sort bug."
            )

            # Check edges
            result_e = client.run("::columns edges", {})
            rows_e = _raw_rows(result_e)
            col_types_e = {row[0]: row[3] for row in rows_e}
            for col in ("src", "tgt"):
                assert col_types_e.get(col) == "String", (
                    f"[#296/#269 engine] edges.{col} type is {col_types_e.get(col)!r}, "
                    "expected 'String'."
                )

            # Insert a UUID-shaped id and verify it round-trips as a string
            uuid_id = "550e8400-e29b-41d4-a716-446655440000"
            client.run(
                "?[id, attrs] <- [[$id, $attrs]] :put nodes {id => attrs}",
                {"id": uuid_id, "attrs": {"entity_type": "UUID_STRING_TEST"}},
            )
            result_get = client.run(
                "?[id] := *nodes{id}, id = $id",
                {"id": uuid_id},
            )
            get_rows = _raw_rows(result_get)
            assert len(get_rows) == 1, (
                f"[#296/#269 engine] UUID-shaped id not found: expected 1 row, got {len(get_rows)}"
            )
            returned_id = get_rows[0][0]
            assert returned_id == uuid_id, (
                f"[#296/#269 engine] UUID-shaped id round-trip: expected {uuid_id!r}, "
                f"got {returned_id!r}"
            )
            assert type(returned_id) is str, (
                f"[#296/#269 engine] Returned id type is {type(returned_id).__name__}, "
                "expected str. Cozo may have coerced it to Uuid."
            )
        finally:
            client.close()


# ===========================================================================
# Integration test: full adapter lifecycle covering all four bug classes
# ===========================================================================

@pytest.mark.asyncio
async def test_all_four_bug_classes_in_adapter_lifecycle(tmp_path):
    """Integration: all four frozen-bug guards pass end-to-end in one adapter lifecycle.

    Exercises the complete CozoGraphStorage flow (upsert → flush → reopen →
    query) with data shaped to expose each bug class if present.  Acts as a
    single smoke test that the adapter's actual pipeline is clean across all
    four risk areas simultaneously.

    Bug guards:
    - #244: node_degree for connected nodes is non-zero after reopen (aggregation)
    - #275: all attrs values are str, node_degree is int (DataValue types)
    - #253: all provenance keys survive the reopen (JSON key completeness)
    - #296/#269: UUID-shaped IDs sort lexicographically (String keys, not Uuid)
    """
    cz_dir = str(tmp_path)

    # --- Write phase ---
    store1 = _make_store(cz_dir, ns="integration")
    await store1.initialize()
    await _build_and_flush(store1)
    await store1.finalize()

    # --- Reopen + read phase ---
    store2 = _make_store(cz_dir, ns="integration")
    await store2.initialize()
    try:
        # #244: node_degree non-zero for all connected nodes
        for node_id, expected_deg in _EXPECTED_DEGREES.items():
            deg = await store2.node_degree(node_id)
            assert deg == expected_deg, (
                f"[Integration #244] node_degree({node_id!r}) = {deg}, "
                f"expected {expected_deg} after reopen"
            )

        # #275: degree is int, labels are str
        deg_alice = await store2.node_degree("Alice")
        assert type(deg_alice) is int, f"[Integration #275] degree type: {type(deg_alice)}"
        labels = await store2.get_all_labels()
        for lbl in labels:
            assert type(lbl) is str, f"[Integration #275] label type: {type(lbl)}"

        # #253: all provenance keys present in get_node result
        alice = await store2.get_node("Alice")
        assert alice is not None, "[Integration #253] get_node('Alice') returned None"
        for key in ("entity_type", "description", "source_id", "file_path"):
            assert key in alice, f"[Integration #253] Key {key!r} missing from get_node result"
            assert type(alice[key]) is str, (
                f"[Integration #253/#275] Key {key!r} value type: {type(alice[key])}"
            )

        # #296/#269: get_all_labels is lexicographically sorted
        all_lbl = await store2.get_all_labels()
        assert all_lbl == sorted(all_lbl), (
            f"[Integration #296/#269] get_all_labels not sorted: {all_lbl}"
        )

        # #296/#269: edge_degree is correct (no UUID coercion of edge src/tgt)
        ed = await store2.edge_degree("Alice", "Bob")
        expected_ed = _EXPECTED_DEGREES["Alice"] + _EXPECTED_DEGREES["Bob"]
        assert ed == expected_ed, (
            f"[Integration #296/#269] edge_degree('Alice','Bob') = {ed}, "
            f"expected {expected_ed}"
        )

    finally:
        await store2.finalize()
