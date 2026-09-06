"""Verified, one-time import of v1's built index into the v2 namespace layout
(03-02-PLAN.md Task 3, D-01/D-02).

Two entry points, mirroring ``databasise/tools/check_import_boundary.py``'s own shape:

- ``import_v1_index`` — the importer. Reads v1's on-disk Faiss indexes, JSON KV state, and Cozo
  graph directly (never imports v1's Python — this module lives under ``databasise/`` and
  ``check_import_boundary.py`` forbids that import here), and writes the same data through the
  v2 stores' own public write paths (``FaissVectorStore.upsert``, ``SqliteKVStore.upsert``,
  ``CozoGraphStore.upsert_node``/``upsert_edge``).
- ``verify_import`` — the verifier. Runs D-02's three assertions and returns a
  ``VerificationResult`` with one of three states, never a bare boolean:
    - ``"verified"``   — all three assertions passed.
    - ``"inconclusive"`` — the comparison ran but at least one assertion failed; each failure is
      recorded as a ``Violation`` naming the specific assertion and offending id. Per PITFALLS 8
      and this project's refusals-over-silent-fallbacks house style, a failed precondition is
      never reported as a plain pass or fail.
    - ``"refused"``    — the comparison could not even be attempted (the v2 side was never
      imported).

**Import mechanism is read-and-reinsert, never file copy** (Claude's Discretion per
03-02-PLAN.md's "Flagged planner assumptions"): v1's two Faiss sidecar shapes (an ``_id_to_meta``
dict) and v2's (``next_int_id`` + ``entries`` + ``index_checksum``) are structurally different, so
copying the file pair would leave a v2 store that refuses to load. Vectors are read out of v1's
index with ``faiss.read_index`` + ``IndexFlatIP.reconstruct`` and re-inserted through
``FaissVectorStore.upsert(ids, embeddings, metadatas)`` — the v2 store's precomputed-embedding
write path. Nothing here calls any embedding client; vectors are never recomputed.

**Both stores L2-normalise on write** (module docstring of ``databasise/stores/vector.py``): v1
already stores L2-normalised vectors (its own docstring: "storing L2-normalised vectors in an
``IndexFlatIP``"), so v2's ``upsert`` re-normalising an already-normalised vector is idempotent up
to floating-point rounding — this is exactly why the per-vector tolerance comparison below is
meaningful rather than trivially true — a real re-embedding or a real normalisation bug would move
a vector's components well past the tolerance; idempotent re-normalisation of an already-unit
vector does not.

Cozo's schema is identical on both sides (``nodes {id: String => attrs: Json}``,
``edges {src: String, tgt: String => attrs: Json}`` — see ``v1/lightrag/kg/cozo_impl.py`` and
``databasise/stores/graph.py``), but this module still reads v1's rows through a plain, read-only
``pycozo`` client and reinserts them through ``CozoGraphStore.upsert_node``/``upsert_edge``, for
the same read-and-reinsert reason as the vectors: consistency of import mechanism across every
store kind, not an accident of the schemas happening to match.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import numpy as np

from databasise.namespaces import derive_namespace
from databasise.parity.corpus import load_snapshot
from databasise.stores.graph import CozoGraphStore
from databasise.stores.kv import SqliteKVStore
from databasise.stores.vector import FaissVectorStore

try:
    import faiss  # type: ignore[import-untyped]
except ImportError as _faiss_import_err:  # pragma: no cover — same guard as stores/vector.py
    raise ImportError(
        "faiss-cpu is required for the parity importer. Install with: pip install faiss-cpu"
    ) from _faiss_import_err

try:
    from pycozo.client import Client as CozoClient
except ImportError as _cozo_import_err:  # pragma: no cover — same guard as stores/graph.py
    raise ImportError(
        "cozo-embedded is required for the parity importer. "
        "Install with: pip install 'pycozo[embedded]'"
    ) from _cozo_import_err

# v1's own namespace-kind vocabulary (v1/lightrag/namespace.py's NameSpace class), reused
# verbatim as the v2-side per-store-kind ``namespace`` argument so a reader can trace which v1
# file a given v2 store directory came from.
_VECTOR_KINDS: tuple[str, ...] = ("chunks", "entities", "relationships")
_GRAPH_KIND = "chunk_entity_relation"
_TEXT_CHUNKS_KIND = "text_chunks"

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_V1_WORKING_DIR = _REPO_ROOT / "v1" / ".parity_working_dir"
DEFAULT_STORE_ROOT = _REPO_ROOT / "v1" / ".parity_v2_store"


class MissingV1IndexError(RuntimeError):
    """Raised when the v1 index directory itself does not exist — naming the expected path
    rather than silently importing an empty store set (03-02-PLAN.md Task 3 acceptance
    criterion).
    """

    def __init__(self, expected_path: Path):
        self.expected_path = expected_path
        super().__init__(
            f"v1 index directory not found at {expected_path} — run "
            "v1/scripts/run_parity_ingest.py first (03-02-PLAN.md Task 2)"
        )


@dataclass(frozen=True)
class Violation:
    """One failed D-02 assertion: which assertion, a human-readable detail, and the offending id
    (chunk id, vector kind, or node/edge identity) if the failure is id-scoped.
    """

    assertion: Literal["chunk-text", "vector-tolerance", "graph-topology"]
    detail: str
    offending_id: str | None = None


@dataclass(frozen=True)
class VerificationResult:
    status: Literal["verified", "inconclusive", "refused"]
    violations: tuple[Violation, ...] = field(default_factory=tuple)


def _import_workspace() -> str:
    """The recipe-identity ``workspace`` every per-kind store directory nests under (D-07's
    one-directory-per-namespace layout), derived from the real corpus hash so the namespace
    itself changes if the corpus snapshot ever changes (03-02-PLAN.md key_link: "a ported node
    reading ``ctx.stores['kv']`` sees the same chunk text v1 stored").
    """
    corpus_hash = load_snapshot().corpus_hash
    return derive_namespace(
        sa1_instance_hash="phase3-parity-v1-import",
        sa2_chunker="v1-fixed-token-F",
        sa2_extraction="v1-lightrag-1.5.4",
        sa2_embedding="qwen3-embedding-8b@openrouter",
        corpus_id=corpus_hash,
        space_id=None,
        scope="shared",
    )


def _cozo_rows(result: Any) -> list[list]:
    """Normalise a ``pycozo`` ``run()`` result to ``list[list]`` across both shapes 0.7.6
    returns — duplicated (not imported) from ``databasise/stores/graph.py``'s private helper of
    the same name, kept local so this module reads v1's raw Cozo rows without reaching into
    another module's private internals.
    """
    if hasattr(result, "to_dict"):
        return result.values.tolist()
    return result.get("rows", [])


def _attrs_to_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    return json.loads(raw)


def _canonical_edge_key(src: str, tgt: str) -> tuple[str, str]:
    return (src, tgt) if src <= tgt else (tgt, src)


# --------------------------------------------------------------------------------------------- #
# Importer
# --------------------------------------------------------------------------------------------- #


async def _import_vector_kind(
    kind: str, v1_working_dir: Path, store_root: Path, workspace: str
) -> None:
    index_path = v1_working_dir / f"faiss_index_{kind}.index"
    meta_path = Path(str(index_path) + ".meta.json")
    if not index_path.exists() or not meta_path.exists():
        # A legitimately empty extraction result (e.g. no relationships found) — not the
        # "v1 index directory missing entirely" case, which is checked by the caller before
        # any per-kind import is attempted.
        return

    index = faiss.read_index(str(index_path))
    meta: dict[str, dict[str, Any]] = json.loads(meta_path.read_text(encoding="utf-8"))
    if not meta:
        return

    ids: list[str] = []
    vectors: list[np.ndarray] = []
    metadatas: list[dict[str, Any]] = []
    for fid_str, record in meta.items():
        fid = int(fid_str)
        vectors.append(index.reconstruct(fid))
        ids.append(record["__id__"])
        metadatas.append(
            {k: v for k, v in record.items() if k not in ("__id__", "__vector__", "__created_at__")}
        )

    store = FaissVectorStore(namespace=kind, workspace=workspace, store_root=store_root)
    await store.upsert(ids=ids, embeddings=np.vstack(vectors), metadatas=metadatas)
    await store.index_done_callback()


async def _import_text_chunks(v1_working_dir: Path, store_root: Path, workspace: str) -> None:
    kv_path = v1_working_dir / f"kv_store_{_TEXT_CHUNKS_KIND}.json"
    if not kv_path.exists():
        return
    data: dict[str, dict[str, Any]] = json.loads(kv_path.read_text(encoding="utf-8"))
    if not data:
        return
    store = SqliteKVStore(namespace=_TEXT_CHUNKS_KIND, workspace=workspace, store_root=store_root)
    await store.upsert(data)
    await store.index_done_callback()


async def _import_graph(v1_working_dir: Path, store_root: Path, workspace: str) -> None:
    db_path = v1_working_dir / f"cozo_graph_{_GRAPH_KIND}.db"
    if not db_path.exists():
        return

    v1_client = CozoClient("rocksdb", str(db_path))
    try:
        node_rows = _cozo_rows(v1_client.run("?[id, attrs] := *nodes{id, attrs}", {}))
        edge_rows = _cozo_rows(v1_client.run("?[src, tgt, attrs] := *edges{src, tgt, attrs}", {}))
    finally:
        v1_client.close()

    if not node_rows and not edge_rows:
        return

    store = CozoGraphStore(namespace=_GRAPH_KIND, workspace=workspace, store_root=store_root)
    for node_id, attrs_raw in node_rows:
        await store.upsert_node(node_id, _attrs_to_dict(attrs_raw))
    for src, tgt, attrs_raw in edge_rows:
        await store.upsert_edge(src, tgt, _attrs_to_dict(attrs_raw))
    await store.index_done_callback()
    await store.finalize()


async def import_v1_index(
    v1_working_dir: Path = DEFAULT_V1_WORKING_DIR,
    store_root: Path = DEFAULT_STORE_ROOT,
    workspace: str | None = None,
) -> str:
    """Import v1's built index (Faiss x3, text_chunks KV, Cozo graph) into the v2 namespace
    layout under ``workspace`` (derived from the real corpus hash by default — see
    ``_import_workspace``; a test may pass an explicit value to avoid coupling a synthetic
    fixture to the real corpus snapshot). Returns the workspace string used (the caller passes it
    straight to ``verify_import``).

    Raises ``MissingV1IndexError`` naming the expected path if ``v1_working_dir`` itself does not
    exist — never silently imports an empty store set.
    """
    if not v1_working_dir.exists():
        raise MissingV1IndexError(v1_working_dir)

    if workspace is None:
        workspace = _import_workspace()
    for kind in _VECTOR_KINDS:
        await _import_vector_kind(kind, v1_working_dir, store_root, workspace)
    await _import_text_chunks(v1_working_dir, store_root, workspace)
    await _import_graph(v1_working_dir, store_root, workspace)
    return workspace


# --------------------------------------------------------------------------------------------- #
# Verifier
# --------------------------------------------------------------------------------------------- #


def _v1_text_chunks(v1_working_dir: Path) -> dict[str, dict[str, Any]]:
    kv_path = v1_working_dir / f"kv_store_{_TEXT_CHUNKS_KIND}.json"
    if not kv_path.exists():
        return {}
    return json.loads(kv_path.read_text(encoding="utf-8"))


# Both stores L2-normalise on write (module docstring above), but a *second* normalisation pass
# over an already-unit vector is only idempotent up to floating-point rounding — empirically,
# renormalising a float32 unit vector can shift its last ULP. Measured directly against the real
# Task 2 build (4096-dim qwen3-embedding-8b vectors, 407 vectors across all three kinds): observed
# per-component noise up to ~1e-5.
#
# This module originally compared a SHA-256 hash over each vector rounded to a fixed number of
# decimals (tried 6, 5, then 3, then 2 decimals). Every fixed-decimal round is a grid with
# boundaries: any grid fine enough to sit close to the ~1e-5 noise floor above will occasionally
# have a real vector's true value fall within noise-distance of a grid line, flipping the rounded
# value on one side and not the other — a property of where the real data happens to sit relative
# to the grid, not a bug in the rounding call, so coarsening the grid only makes the boundary case
# rarer, never removes it (03-11-PLAN.md's real re-ingest tripped exactly this case: one of 188
# entity vectors landed 1.49e-8 from a 3-decimal grid line). Coarsening the grid also throws away
# real discriminating power: rounding a 4096-dim, L2-normalised vector (typical per-component
# magnitude ~1/sqrt(4096) ≈ 0.0156) to 2 decimals collapses roughly a quarter of its components —
# every one with |x| < 0.005 — to exactly 0.0 before the hash ever sees them.
#
# Replaced with a direct tolerance check on the raw, unrounded float32 vectors (CR-02 fix cycle):
# no grid, so no boundary case regardless of how the dataset grows, and it uses each vector's full
# component resolution rather than discarding a quarter of it up front. 1e-4 is two orders of
# magnitude above the measured ~1e-5 noise ceiling — comfortable headroom that a genuine
# re-normalisation pass never trips — while a real re-embedding or a wrong id-to-vector pairing
# (which differ across many of a vector's 4096 components at once, several orders of magnitude
# above this tolerance) is still caught, and the comparison now names the specific offending
# vector id rather than only reporting a whole-set hash mismatch.
_VECTOR_TOLERANCE = 1e-4


def _v1_vector_pairs(v1_working_dir: Path, kind: str) -> list[tuple[str, np.ndarray]]:
    index_path = v1_working_dir / f"faiss_index_{kind}.index"
    meta_path = Path(str(index_path) + ".meta.json")
    if not index_path.exists() or not meta_path.exists():
        return []
    index = faiss.read_index(str(index_path))
    meta: dict[str, dict[str, Any]] = json.loads(meta_path.read_text(encoding="utf-8"))
    pairs = []
    for fid_str, record in meta.items():
        vec = index.reconstruct(int(fid_str)).astype("float32")
        pairs.append((record["__id__"], vec))
    return pairs


async def _v2_vector_pairs(store_root: Path, workspace: str, kind: str) -> list[tuple[str, np.ndarray]]:
    store_dir = Path(store_root) / workspace / kind
    if not (store_dir / "vector.faiss").exists():
        return []
    store = FaissVectorStore(namespace=kind, workspace=workspace, store_root=store_root)
    return [(doc_id, vec.astype("float32")) for doc_id, vec in store.iter_vectors()]


def _compare_vector_sets(
    v1_pairs: list[tuple[str, np.ndarray]],
    v2_pairs: list[tuple[str, np.ndarray]],
    kind: str,
) -> list[Violation]:
    """Compare two vector sets id-by-id: id sets must match, and every common id's v1/v2 vectors
    must agree within ``_VECTOR_TOLERANCE`` on every component (max-abs-diff over the raw float32
    vectors, no rounding — see the module-level rationale above). Unlike the rounded-hash
    comparison this replaces, a failure here names the specific offending vector id rather than
    only reporting that some vector in the set differs.
    """
    v1_by_id = dict(v1_pairs)
    v2_by_id = dict(v2_pairs)
    violations: list[Violation] = []

    missing = set(v1_by_id) - set(v2_by_id)
    extra = set(v2_by_id) - set(v1_by_id)
    if missing or extra:
        violations.append(
            Violation(
                assertion="vector-tolerance",
                detail=(
                    f"vector kind {kind!r}: {len(missing)} id(s) missing from v2, "
                    f"{len(extra)} id(s) extra in v2"
                ),
                offending_id=min(missing | extra),
            )
        )

    for doc_id in sorted(set(v1_by_id) & set(v2_by_id)):
        max_abs_diff = float(np.max(np.abs(v1_by_id[doc_id] - v2_by_id[doc_id])))
        if max_abs_diff >= _VECTOR_TOLERANCE:
            violations.append(
                Violation(
                    assertion="vector-tolerance",
                    detail=(
                        f"vector kind {kind!r}, id {doc_id!r}: max component diff "
                        f"{max_abs_diff:.6g} >= tolerance {_VECTOR_TOLERANCE:.0e}"
                    ),
                    offending_id=doc_id,
                )
            )
    return violations


def _v1_graph(v1_working_dir: Path) -> tuple[set[str], set[tuple[str, str]]] | None:
    db_path = v1_working_dir / f"cozo_graph_{_GRAPH_KIND}.db"
    if not db_path.exists():
        return None
    client = CozoClient("rocksdb", str(db_path))
    try:
        node_rows = _cozo_rows(client.run("?[id] := *nodes{id}", {}))
        edge_rows = _cozo_rows(client.run("?[src, tgt] := *edges{src, tgt}", {}))
    finally:
        client.close()
    node_ids = {r[0] for r in node_rows}
    edges = {_canonical_edge_key(r[0], r[1]) for r in edge_rows}
    return node_ids, edges


def _v2_graph(store_root: Path, workspace: str) -> tuple[set[str], set[tuple[str, str]]] | None:
    db_path = Path(store_root) / workspace / _GRAPH_KIND / "graph.cozo"
    if not db_path.exists():
        return None
    client = CozoClient("rocksdb", str(db_path))
    try:
        node_rows = _cozo_rows(client.run("?[id] := *nodes{id}", {}))
        edge_rows = _cozo_rows(client.run("?[src, tgt] := *edges{src, tgt}", {}))
    finally:
        client.close()
    node_ids = {r[0] for r in node_rows}
    edges = {_canonical_edge_key(r[0], r[1]) for r in edge_rows}
    return node_ids, edges


async def verify_import(
    v1_working_dir: Path = DEFAULT_V1_WORKING_DIR,
    store_root: Path = DEFAULT_STORE_ROOT,
    workspace: str | None = None,
) -> VerificationResult:
    """Run D-02's three assertions and return a ``VerificationResult``. Never returns a bare
    pass/fail — a precondition that cannot even be checked yields ``"refused"``; a checked
    precondition that fails yields ``"inconclusive"`` naming the offending id.
    """
    if workspace is None:
        workspace = _import_workspace()

    if not (Path(store_root) / workspace).exists():
        return VerificationResult(
            status="refused",
            violations=(
                Violation(
                    assertion="chunk-text",
                    detail=(
                        f"no imported v2 store found at {Path(store_root) / workspace} — "
                        "run import_v1_index() first"
                    ),
                ),
            ),
        )

    violations: list[Violation] = []

    # (a) chunk text byte-identical, v1 KV vs v2 KV, per chunk id.
    v1_chunks = _v1_text_chunks(v1_working_dir)
    v2_store = SqliteKVStore(namespace=_TEXT_CHUNKS_KIND, workspace=workspace, store_root=store_root)
    for chunk_id, v1_record in sorted(v1_chunks.items()):
        v2_record = await v2_store.get_by_id(chunk_id)
        if v2_record is None:
            violations.append(
                Violation(
                    assertion="chunk-text",
                    detail=f"chunk id {chunk_id!r} present in v1's KV but missing from v2's KV",
                    offending_id=chunk_id,
                )
            )
            continue
        if v2_record.get("content") != v1_record.get("content"):
            violations.append(
                Violation(
                    assertion="chunk-text",
                    detail=f"chunk id {chunk_id!r} content differs between v1's KV and v2's KV",
                    offending_id=chunk_id,
                )
            )

    # (b) vector sets equal within tolerance, per vector kind, naming the offending id.
    for kind in _VECTOR_KINDS:
        v1_pairs = _v1_vector_pairs(v1_working_dir, kind)
        v2_pairs = await _v2_vector_pairs(store_root, workspace, kind)
        violations.extend(_compare_vector_sets(v1_pairs, v2_pairs, kind))

    # (c) graph node count, edge count, node id set, edge endpoint-pair set all matching.
    v1_graph = _v1_graph(v1_working_dir)
    v2_graph = _v2_graph(store_root, workspace)
    if v1_graph is not None and v2_graph is not None:
        v1_nodes, v1_edges = v1_graph
        v2_nodes, v2_edges = v2_graph
        if v1_nodes != v2_nodes:
            missing = v1_nodes - v2_nodes
            extra = v2_nodes - v1_nodes
            violations.append(
                Violation(
                    assertion="graph-topology",
                    detail=(
                        f"node id set differs: {len(missing)} missing from v2, "
                        f"{len(extra)} extra in v2"
                    ),
                    offending_id=min(missing | extra) if (missing | extra) else None,
                )
            )
        if v1_edges != v2_edges:
            missing_e = v1_edges - v2_edges
            extra_e = v2_edges - v1_edges
            offending = min(missing_e | extra_e) if (missing_e | extra_e) else None
            violations.append(
                Violation(
                    assertion="graph-topology",
                    detail=(
                        f"edge endpoint-pair set differs: {len(missing_e)} missing from v2, "
                        f"{len(extra_e)} extra in v2"
                    ),
                    offending_id=f"{offending[0]}-{offending[1]}" if offending else None,
                )
            )

    if violations:
        return VerificationResult(status="inconclusive", violations=tuple(violations))
    return VerificationResult(status="verified")


# --------------------------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------------------------- #


def main(argv: list[str] | None = None) -> int:
    """Import (unless ``--verify`` is passed) then verify v1's index against the v2 namespace
    layout, printing one line per violation and returning 1 on anything but ``"verified"``.
    """
    import asyncio

    argv = sys.argv[1:] if argv is None else argv
    verify_only = "--verify" in argv

    async def _run() -> VerificationResult:
        workspace = _import_workspace()
        if not verify_only:
            await import_v1_index(DEFAULT_V1_WORKING_DIR, DEFAULT_STORE_ROOT)
        return await verify_import(DEFAULT_V1_WORKING_DIR, DEFAULT_STORE_ROOT, workspace)

    try:
        result = asyncio.run(_run())
    except MissingV1IndexError as exc:
        print(str(exc))
        return 1

    if result.status == "verified":
        return 0

    for v in result.violations:
        suffix = f" (id={v.offending_id})" if v.offending_id else ""
        print(f"[{result.status}] {v.assertion}: {v.detail}{suffix}")
    if not result.violations:
        print(f"[{result.status}] no comparison could be made")
    return 1


if __name__ == "__main__":
    sys.exit(main())
