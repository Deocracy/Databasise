"""Embedded Faiss vector store, ported by deliberate copy — never import — from v1's
``FaissVectorDBStorage`` (upstream_ref: v1/lightrag/kg/faiss_impl.py). D-14 keeps this package's
import boundary intact: nothing here imports from v1's ``lightrag`` package, and nothing here
reproduces v1's multi-process ``shared_storage`` synchronisation protocol (D-11's rejected
anti-analog) — this store is single-writer, single-process, in-process only.

Faiss is the sole vector primitive (D-05); there is no fallback pairing. ``nano-vectordb`` is not
part of this stack (01-RESEARCH.md's "Deprecated/outdated" section), so a failure to import
``faiss`` is an error naming Faiss, never a silent degrade onto something else.

Index type: an exact inner-product index (``IndexFlatIP``) over L2-normalised vectors, which is
cosine similarity — matching v1's incumbent behaviour. Faiss is the Phase 3 parity baseline, so the
index type is part of the baseline, not a free choice. Vectors are wrapped in ``IndexIDMap2`` so
each document keeps a stable caller-supplied string id across upserts and deletes, addressed
internally via a monotonically increasing int64 id persisted in the metadata sidecar.

Deferred-write discipline, mirroring the Cozo adapter's buffer contract (D-06's house style: one
commit/abort contract regardless of backend): ``upsert`` buffers ``_PendingVectorDoc`` entries
in-process; nothing is queryable until ``index_done_callback`` flushes them. Buffered vectors are
**precomputed and caller-supplied** — this adapter never calls an embedding model itself.

Raise-don't-silently-drop rule (CONTEXT.md's stated house style — refusals over silent fallbacks):
an embedding-count mismatch is validated and raised inside ``upsert`` itself, before the pending
buffer is touched. A flush failure (index-add error or sidecar-write error) raises before either
the index file or the metadata sidecar is renamed into place, so under an ordinary Python
exception the two files commit together or neither does.

That guard covers only the write-to-temp-file phase, though: the two ``os.replace`` calls that
actually swap the temp files into place are themselves two separate filesystem operations with no
shared transaction, so a hard crash (SIGKILL, power loss) landing between them can still leave a
*new* index paired with the *old* sidecar (WR-02). Since that window cannot be closed with two
independent files on a POSIX filesystem without a heavier scheme (a staging-directory swap, or a
symlink flip), the sidecar instead carries a SHA-256 ``index_checksum`` of the index file it was
written to accompany; ``__init__`` recomputes that checksum against whatever index file is
actually on disk and refuses (``VectorStoreCorruptedError``) rather than silently loading a
half-committed pair — the crash window still exists, but a pair it produces is now detected and
refused at the next open instead of used.

Metadata sidecar: the Faiss index and a ``.meta.json`` sidecar both live inside this store's own
namespace directory (``<store_root>/<workspace>/<namespace>/``), matching D-07's
one-directory-per-namespace layout — the same layout ``stores/kv.py`` and ``stores/graph.py``
already use.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from databasise.stores.base import StorageNameSpace

try:
    import faiss  # type: ignore[import-untyped]
except ImportError as _faiss_import_err:
    raise ImportError(
        "faiss-cpu is required for FaissVectorStore. Install with: pip install faiss-cpu"
    ) from _faiss_import_err


class VectorStoreCorruptedError(RuntimeError):
    """Raised at open time (WR-02) when the on-disk index file's SHA-256 does not match the
    ``index_checksum`` its own metadata sidecar claims. This is the signature of the two-file
    commit's known non-atomic window (two independent ``os.replace`` calls — see module
    docstring): a crash landing exactly between them can pair a new index with a stale sidecar
    (or vice versa). Rather than silently loading a mismatched pair, this store refuses by name so
    the corruption is visible and actionable instead of a source of quiet, wrong query results.
    """

    def __init__(self, index_path: Path, expected: str | None, actual: str):
        self.index_path = index_path
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"vector store at {index_path!s} is corrupted: sidecar recorded index_checksum "
            f"{expected!r}, but the on-disk index file's actual checksum is {actual!r}. This is "
            "the signature of a crash landing between the index and sidecar's two independent "
            "commit renames (WR-02) — the pair is refused rather than silently loaded."
        )


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass
class _PendingVectorDoc:
    """A buffered upsert awaiting flush into the Faiss index. ``vector`` is already an
    L2-normalised float32 1D ndarray by the time it is buffered, so flush can ``vstack`` and
    ``add_with_ids`` without re-normalising."""

    vector: np.ndarray
    metadata: dict[str, Any] = field(default_factory=dict)


class FaissVectorStore(StorageNameSpace):
    """Embedded Faiss (``IndexFlatIP`` over normalised vectors) store, one index directory per
    namespace, with a JSON metadata sidecar written atomically alongside it."""

    upstream_ref = "v1/lightrag/kg/faiss_impl.py"

    def __init__(self, namespace: str, workspace: str, store_root: str | Path) -> None:
        super().__init__(namespace=namespace, workspace=workspace)
        self._dir = Path(store_root) / workspace / namespace
        self._dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self._dir / "vector.faiss"
        self._meta_path = self._dir / "vector.meta.json"

        self._pending: dict[str, _PendingVectorDoc] = {}
        self._dim: int | None = None
        self._index: Any = None
        self._entries: dict[str, dict[str, Any]] = {}
        self._next_int_id: int = 0

        if self._index_path.exists() and self._meta_path.exists():
            with self._meta_path.open("r", encoding="utf-8") as f:
                meta = json.load(f)
            expected_checksum = meta.get("index_checksum")
            actual_checksum = _sha256_of(self._index_path)
            if expected_checksum != actual_checksum:
                raise VectorStoreCorruptedError(self._index_path, expected_checksum, actual_checksum)

            self._index = faiss.read_index(str(self._index_path))
            self._dim = self._index.d
            self._entries = meta["entries"]
            self._next_int_id = meta["next_int_id"]

    # ------------------------------------------------------------------ #
    # Writes — buffered, flushed at index_done_callback                    #
    # ------------------------------------------------------------------ #

    async def upsert(
        self,
        ids: list[str],
        embeddings: Any,
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Buffer precomputed embeddings for later flush. Raises before touching the pending
        buffer if ``ids``/``embeddings``/``metadatas`` lengths disagree — a mis-paired vector is
        made impossible rather than merely unlikely.
        """
        ids = list(ids)
        embeddings_arr = np.asarray(embeddings, dtype="float32")
        if embeddings_arr.ndim == 1:
            embeddings_arr = embeddings_arr.reshape(1, -1)
        if len(ids) != embeddings_arr.shape[0]:
            raise ValueError(
                f"embedding count ({embeddings_arr.shape[0]}) does not match "
                f"document count ({len(ids)})"
            )
        if metadatas is not None and len(metadatas) != len(ids):
            raise ValueError(
                f"metadata count ({len(metadatas)}) does not match document count ({len(ids)})"
            )
        if self._dim is not None and embeddings_arr.shape[1] != self._dim:
            raise ValueError(
                f"embedding dimension ({embeddings_arr.shape[1]}) does not match "
                f"this store's dimension ({self._dim})"
            )

        normalised = embeddings_arr.copy()
        faiss.normalize_L2(normalised)

        for i, doc_id in enumerate(ids):
            meta = dict(metadatas[i]) if metadatas is not None else {}
            self._pending[doc_id] = _PendingVectorDoc(vector=normalised[i], metadata=meta)

    async def delete_by_ids(self, ids: list[str]) -> None:
        """Remove entries immediately (not deferred): the index and sidecar are written together
        via the same two-phase persist helper ``upsert``'s flush uses, so they stay consistent."""
        self._pending = {k: v for k, v in self._pending.items() if k not in ids}
        to_remove = [i for i in ids if i in self._entries]
        if not to_remove or self._index is None:
            return

        staging = faiss.clone_index(self._index)
        int_ids = np.array([self._entries[i]["int_id"] for i in to_remove], dtype="int64")
        staging.remove_ids(int_ids)
        staging_entries = {k: v for k, v in self._entries.items() if k not in to_remove}

        self._persist(staging, staging_entries, self._next_int_id)

    # ------------------------------------------------------------------ #
    # Reads — only committed (flushed) data is queryable                  #
    # ------------------------------------------------------------------ #

    async def query(self, vector: Any, top_k: int = 10) -> list[dict[str, Any]]:
        if self._index is None or self._index.ntotal == 0:
            return []

        query_vec = np.asarray(vector, dtype="float32").reshape(1, -1)
        faiss.normalize_L2(query_vec)
        k = min(top_k, self._index.ntotal)
        scores, int_ids = self._index.search(query_vec, k)

        int_to_doc = {v["int_id"]: doc_id for doc_id, v in self._entries.items()}
        results: list[dict[str, Any]] = []
        for score, int_id in zip(scores[0], int_ids[0], strict=True):
            if int_id == -1:
                continue
            doc_id = int_to_doc.get(int(int_id))
            if doc_id is None:
                continue
            entry = self._entries[doc_id]
            results.append({"id": doc_id, "score": float(score), **entry["metadata"]})

        results.sort(key=lambda r: (-r["score"], r["id"]))
        return results

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    async def index_done_callback(self) -> None:
        if not self._pending:
            return

        if self._index is None:
            self._dim = next(iter(self._pending.values())).vector.shape[0]
            self._index = faiss.IndexIDMap2(faiss.IndexFlatIP(self._dim))

        staging = faiss.clone_index(self._index)
        staging_entries = dict(self._entries)
        next_int_id = self._next_int_id

        vectors: list[np.ndarray] = []
        int_ids: list[int] = []
        for doc_id, pending in self._pending.items():
            if doc_id in staging_entries:
                staging.remove_ids(np.array([staging_entries[doc_id]["int_id"]], dtype="int64"))
            int_id = next_int_id
            next_int_id += 1
            vectors.append(pending.vector)
            int_ids.append(int_id)
            staging_entries[doc_id] = {"int_id": int_id, "metadata": pending.metadata}

        if vectors:
            matrix = np.vstack(vectors).astype("float32")
            staging.add_with_ids(matrix, np.array(int_ids, dtype="int64"))

        self._persist(staging, staging_entries, next_int_id)
        self._pending.clear()

    def _persist(
        self, index: Any, entries: dict[str, dict[str, Any]], next_int_id: int
    ) -> None:
        """Write the index and sidecar to temp files, then rename both into place. An ordinary
        Python exception during either write leaves the previously-committed pair on disk
        untouched and raises rather than partially writing; the two ``os.replace`` calls below
        still are not a single transaction (WR-02 — see module docstring), so the sidecar carries
        a SHA-256 ``index_checksum`` of the index file it is written to accompany, checked back
        against the on-disk index at the next ``__init__``.
        """
        tmp_index = self._index_path.with_suffix(self._index_path.suffix + ".tmp")
        tmp_meta = self._meta_path.with_suffix(self._meta_path.suffix + ".tmp")
        try:
            faiss.write_index(index, str(tmp_index))
            index_checksum = _sha256_of(tmp_index)
            with tmp_meta.open("w", encoding="utf-8") as f:
                json.dump(
                    {"next_int_id": next_int_id, "entries": entries, "index_checksum": index_checksum},
                    f,
                )
        except Exception:
            tmp_index.unlink(missing_ok=True)
            tmp_meta.unlink(missing_ok=True)
            raise

        os.replace(tmp_index, self._index_path)
        os.replace(tmp_meta, self._meta_path)

        self._index = index
        self._entries = entries
        self._next_int_id = next_int_id

    async def drop_pending_index_ops(self) -> None:
        self._pending.clear()

    async def drop(self) -> dict[str, str]:
        try:
            self._index_path.unlink(missing_ok=True)
            self._meta_path.unlink(missing_ok=True)
            self._index = None
            self._entries = {}
            self._next_int_id = 0
            self._dim = None
            self._pending.clear()
            return {"status": "success", "message": "data dropped"}
        except Exception as exc:  # noqa: BLE001 — drop()'s own documented contract (v1 StorageNameSpace)
            return {"status": "error", "message": str(exc)}
