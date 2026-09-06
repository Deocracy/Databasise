"""Tests for ``databasise.parity.import_index`` (03-02-PLAN.md Task 3).

The <behavior> claims this module is built against:
  - Importing a v1 index produces a v2 store set whose chunk text is byte-identical to v1's for
    every chunk id.
  - Every vector's v1/v2 copies agree within tolerance, component-wise, after import (CR-02 fix
    cycle: a direct per-vector tolerance check, not a rounded-hash comparison — see
    `import_index.py`'s module-level rationale).
  - The v2 graph's node count, edge count, node id set, and edge endpoint-pair set all match v1's.
  - A deliberately corrupted chunk text on the v2 side makes the verifier report `inconclusive`
    with that chunk id named, and does not report a pass or a fail.
  - A missing v1 index directory raises naming the expected path rather than importing an empty
    store set.

Every case below runs against a **synthetic v1-shaped index** built directly with ``faiss`` and
``pycozo`` — the same packages ``databasise/pyproject.toml`` already depends on — so this whole
suite runs on every machine with no ``v1/`` venv and no network. A separate, skip-guarded test at
the bottom exercises the real Task 2 build when it is present.
"""

from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
import pytest
from databasise.parity.import_index import (
    MissingV1IndexError,
    import_v1_index,
    verify_import,
)
from databasise.stores.kv import SqliteKVStore
from pycozo.client import Client as CozoClient

_WORKSPACE = "synthetic-parity-import-test"


def _write_faiss_kind(v1_dir: Path, kind: str, id_to_vector_and_meta: dict[str, tuple]) -> None:
    """Write a v1-shaped ``faiss_index_<kind>.index`` + ``.meta.json`` pair. Empty dict writes
    nothing (matching v1's own behaviour of not creating a file for an empty vector store).
    """
    if not id_to_vector_and_meta:
        return
    dim = len(next(iter(id_to_vector_and_meta.values()))[0])
    index = faiss.IndexFlatIP(dim)
    meta: dict[str, dict] = {}
    vectors = []
    for fid, (vector, custom_id, extra_meta) in enumerate(id_to_vector_and_meta.values()):
        vectors.append(vector)
        record = {"__id__": custom_id, "__created_at__": 0}
        record.update(extra_meta)
        meta[str(fid)] = record
    arr = np.vstack(vectors).astype("float32")
    faiss.normalize_L2(arr)
    index.add(arr)
    faiss.write_index(index, str(v1_dir / f"faiss_index_{kind}.index"))
    (v1_dir / f"faiss_index_{kind}.index.meta.json").write_text(json.dumps(meta), encoding="utf-8")


def _write_cozo_graph(v1_dir: Path, nodes: dict[str, dict], edges: list[tuple[str, str, dict]]) -> None:
    db_path = v1_dir / "cozo_graph_chunk_entity_relation.db"
    client = CozoClient("rocksdb", str(db_path))
    try:
        client.run(":create nodes {id: String => attrs: Json}", {})
        client.run(":create edges {src: String, tgt: String => attrs: Json}", {})
        if nodes:
            rows = [[nid, attrs] for nid, attrs in nodes.items()]
            client.run("?[id, attrs] <- $rows :put nodes {id => attrs}", {"rows": rows})
        if edges:
            rows = [[src, tgt, attrs] for src, tgt, attrs in edges]
            client.run("?[src, tgt, attrs] <- $rows :put edges {src, tgt => attrs}", {"rows": rows})
    finally:
        client.close()


@pytest.fixture
def synthetic_v1_index(tmp_path: Path) -> Path:
    """A synthetic v1-shaped index directory: 2 chunks, a handful of entities/relationships, and
    a small graph — enough to exercise all three D-02 assertions without any real ingest.
    """
    v1_dir = tmp_path / "v1_index"
    v1_dir.mkdir()

    (v1_dir / "kv_store_text_chunks.json").write_text(
        json.dumps(
            {
                "chunk-aaa": {
                    "tokens": 5,
                    "content": "Ed Wood directed several films.",
                    "full_doc_id": "ed_wood",
                    "chunk_order_index": 0,
                },
                "chunk-bbb": {
                    "tokens": 6,
                    "content": "Scott Derrickson is an American director.",
                    "full_doc_id": "scott_derrickson",
                    "chunk_order_index": 0,
                },
            }
        ),
        encoding="utf-8",
    )

    _write_faiss_kind(
        v1_dir,
        "chunks",
        {
            "chunk-aaa": (np.array([1.0, 0.0, 0.0]), "chunk-aaa", {"content": "Ed Wood directed several films."}),
            "chunk-bbb": (np.array([0.0, 1.0, 0.0]), "chunk-bbb", {"content": "Scott Derrickson is an American director."}),
        },
    )
    _write_faiss_kind(
        v1_dir,
        "entities",
        {
            "ent-ed-wood": (np.array([0.5, 0.5, 0.0]), "ent-ed-wood", {"entity_name": "Ed Wood"}),
            "ent-scott": (np.array([0.2, 0.2, 0.9]), "ent-scott", {"entity_name": "Scott Derrickson"}),
        },
    )
    _write_faiss_kind(v1_dir, "relationships", {})  # empty extraction result — legitimate, no file

    _write_cozo_graph(
        v1_dir,
        nodes={"Ed Wood": {"entity_type": "person"}, "Scott Derrickson": {"entity_type": "person"}},
        edges=[("Ed Wood", "Scott Derrickson", {"description": "contemporaries"})],
    )

    return v1_dir


async def test_import_produces_byte_identical_chunk_text(synthetic_v1_index, store_root):
    await import_v1_index(synthetic_v1_index, store_root, workspace=_WORKSPACE)
    v2_store = SqliteKVStore(namespace="text_chunks", workspace=_WORKSPACE, store_root=store_root)

    v1_chunks = json.loads((synthetic_v1_index / "kv_store_text_chunks.json").read_text())
    for chunk_id, record in v1_chunks.items():
        v2_record = await v2_store.get_by_id(chunk_id)
        assert v2_record is not None, f"chunk {chunk_id!r} missing from v2 KV after import"
        assert v2_record["content"] == record["content"]


async def test_import_and_verify_reports_verified_for_a_clean_import(synthetic_v1_index, store_root):
    workspace = await import_v1_index(synthetic_v1_index, store_root, workspace=_WORKSPACE)
    result = await verify_import(synthetic_v1_index, store_root, workspace)

    assert result.status == "verified"
    assert result.violations == ()


async def test_graph_node_and_edge_sets_match_after_import(synthetic_v1_index, store_root):
    from databasise.parity.import_index import _v1_graph, _v2_graph

    workspace = await import_v1_index(synthetic_v1_index, store_root, workspace=_WORKSPACE)
    v1_nodes, v1_edges = _v1_graph(synthetic_v1_index)
    v2_nodes, v2_edges = _v2_graph(store_root, workspace)

    assert v1_nodes == v2_nodes == {"Ed Wood", "Scott Derrickson"}
    assert v1_edges == v2_edges
    assert len(v1_edges) == 1


async def test_corrupted_v2_chunk_yields_inconclusive_naming_the_chunk_id(synthetic_v1_index, store_root):
    workspace = await import_v1_index(synthetic_v1_index, store_root, workspace=_WORKSPACE)

    # Deliberately corrupt one chunk's content on the v2 side, post-import.
    v2_store = SqliteKVStore(namespace="text_chunks", workspace=workspace, store_root=store_root)
    await v2_store.upsert({"chunk-aaa": {"content": "TAMPERED", "tokens": 1}})
    await v2_store.index_done_callback()

    result = await verify_import(synthetic_v1_index, store_root, workspace)

    assert result.status == "inconclusive"
    assert result.status not in ("verified",)  # never a plain pass
    chunk_violations = [v for v in result.violations if v.assertion == "chunk-text"]
    assert any(v.offending_id == "chunk-aaa" for v in chunk_violations)


async def test_missing_v1_index_directory_raises_naming_the_expected_path(tmp_path, store_root):
    missing_dir = tmp_path / "does_not_exist"

    with pytest.raises(MissingV1IndexError) as exc_info:
        await import_v1_index(missing_dir, store_root, workspace=_WORKSPACE)

    assert str(missing_dir) in str(exc_info.value)


async def test_verify_without_prior_import_is_refused_not_pass_or_fail(synthetic_v1_index, tmp_path):
    empty_store_root = tmp_path / "never_imported_store"
    result = await verify_import(synthetic_v1_index, empty_store_root, workspace=_WORKSPACE)

    assert result.status == "refused"


# --------------------------------------------------------------------------------------------- #
# Real Task 2 build — skip-guarded, exercised only when v1/ has actually been run
# --------------------------------------------------------------------------------------------- #


async def test_real_v1_build_verifies_clean(v1_index_dir, store_root):
    workspace = await import_v1_index(v1_index_dir, store_root)
    result = await verify_import(v1_index_dir, store_root, workspace)

    assert result.status == "verified", (
        f"real Task 2 build failed D-02 verification: {result.violations}"
    )


async def test_real_v1_build_perturbed_vector_is_caught_and_named(v1_index_dir, store_root):
    """CR-02 fix cycle: replacing the rounded-hash comparison with a direct per-vector tolerance
    check must still catch a genuinely different vector on the real imported index — and, unlike
    the whole-set hash it replaces, must name the specific offending id rather than only the
    vector kind. The perturbation (+1.0 on one component) is four orders of magnitude above
    `_VECTOR_TOLERANCE` (1e-4), well past the ~1e-5 re-normalisation noise ceiling the tolerance is
    sized against.
    """
    from databasise.parity.import_index import _VECTOR_TOLERANCE
    from databasise.stores.vector import FaissVectorStore

    workspace = await import_v1_index(v1_index_dir, store_root)

    store = FaissVectorStore(namespace="entities", workspace=workspace, store_root=store_root)
    perturbed_id, original_vector = next(iter(store.iter_vectors()))
    perturbed_vector = original_vector.copy()
    perturbed_vector[0] += 1.0
    assert abs(float(perturbed_vector[0] - original_vector[0])) > 1000 * _VECTOR_TOLERANCE
    await store.upsert([perturbed_id], perturbed_vector, [{}])
    await store.index_done_callback()

    result = await verify_import(v1_index_dir, store_root, workspace)

    assert result.status == "inconclusive"
    tolerance_violations = [v for v in result.violations if v.assertion == "vector-tolerance"]
    assert any(v.offending_id == perturbed_id for v in tolerance_violations), (
        f"expected a vector-tolerance violation naming {perturbed_id!r}, got: "
        f"{result.violations}"
    )


async def test_real_imported_entities_and_relationships_are_non_empty_with_identifying_fields(
    v2_parity_store_dir,
):
    """03-11-PLAN.md Task 1(h): proves at the store boundary — through the store's own public
    read surface, against the real re-imported index, never a synthetic fixture — that the
    entity and relation vector namespaces the OPENAI_LLM_EXTRA_BODY defect emptied are now
    populated and carry the exact fields whose absence produced the recorded
    ``KeyError: 'entity_name'`` / ``KeyError: 'src_id'`` stop reasons.
    """
    from databasise.parity.import_index import _import_workspace
    from databasise.stores.vector import FaissVectorStore

    workspace = _import_workspace()  # same derivation import_index.py itself uses, not hardcoded

    for kind, required_fields in (
        ("entities", ("entity_name",)),
        ("relationships", ("src_id", "tgt_id")),
    ):
        store = FaissVectorStore(namespace=kind, workspace=workspace, store_root=v2_parity_store_dir)
        first_id, first_vector = next(iter(store.iter_vectors()), (None, None))
        assert first_id is not None, f"{kind} vector namespace is empty in the imported store"

        records = await store.query(first_vector, top_k=10_000)
        assert records, f"{kind} query against the store's own data returned no records"

        for record in records:
            for field_name in required_fields:
                value = record.get(field_name)
                assert value, (
                    f"{kind} record {record.get('id')!r} is missing a non-empty "
                    f"{field_name!r} — this is the exact field whose absence produced the "
                    f"recorded KeyError stop reason"
                )
