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
and ``delete_by_ids`` buffers ids (D-08) in-process; neither is visible to a read until
``index_done_callback`` flushes them, and ``drop_pending_index_ops`` discards both. Buffered vectors are
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
refused at the next open instead of used. A directory holding only one of the two files (STOR-08: a
crash inside the very first commit, or a file removed by hand) is refused the same way, with the
missing file named, rather than opened empty and overwritten by the next flush.

Metadata sidecar: the Faiss index and a ``.meta.json`` sidecar both live inside this store's own
namespace directory (``<store_root>/<workspace>/<namespace>/``), matching D-07's
one-directory-per-namespace layout — the same layout ``stores/kv.py`` and ``stores/graph.py``
already use.

Committed-snapshot cache (D-05, STOR-03): every committed-state read goes through
:func:`load_committed`, a bounded process-level cache of read-only snapshots keyed on the resolved
directory plus ``(st_ino, st_mtime_ns, st_size)`` of both files. ``os.replace`` gives each commit a
new inode, so a flush invalidates the key with no hook. The cache holds snapshots, never store
objects: writers build their own ``FaissVectorStore`` and clone the index before changing it.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import threading
from collections import OrderedDict
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
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
    ``index_checksum`` its own metadata sidecar claims, or (STOR-08) when only one of the two files
    exists: ``expected`` is then ``None`` and ``actual`` names the missing file. This is the signature of the two-file
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


_RESERVED_METADATA_KEYS = frozenset({"id", "score"})


class ReservedMetadataKeyError(ValueError):
    """Raised by :meth:`FaissVectorStore.upsert` (STOR-16, D-11) when a metadata dict carries
    ``id`` or ``score``. Results are built as ``{"id": ..., "score": ..., **metadata}``, so such a
    key would overwrite the real id or score every reader sees; the store refuses it by name before
    the pending buffer changes. ``keys`` is the sorted list of reserved keys found.
    """

    def __init__(self, keys: list[str]):
        self.keys = sorted(keys)
        super().__init__(
            f"vector metadata may not use the reserved key(s) {self.keys!r}: results carry the "
            "real id and score under those names, so metadata cannot set them."
        )


class InvalidTopKError(ValueError):
    """Raised by :meth:`FaissVectorStore.query` and :meth:`FaissVectorStore.self_knn` (STOR-09)
    when ``top_k <= 0``, checked before any empty-index shortcut so the refusal does not depend on
    store contents. Faiss would otherwise fail with a bare ``AssertionError``. ``top_k`` is the
    value refused.
    """

    def __init__(self, top_k: int):
        self.top_k = top_k
        super().__init__(f"top_k must be a positive integer, got {top_k!r}")


def _sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


_Signature = tuple[tuple[int, int, int], tuple[int, int, int]]


@dataclass(frozen=True)
class _Committed:
    """A read-only committed snapshot of one namespace, shared by every reader (D-05). ``entries``
    is a ``MappingProxyType``; writers copy it and clone ``index`` before any change."""

    index: Any
    entries: Mapping[str, dict[str, Any]]
    next_int_id: int
    dim: int
    signature: _Signature


# shortcut: fixed LRU of 32 snapshots, make it configurable if a deployment serves more namespaces
_SNAPSHOT_CACHE_SIZE = 32
_SNAPSHOT_CACHE: OrderedDict[tuple[str, _Signature], _Committed] = OrderedDict()
_SNAPSHOT_LOCK = threading.Lock()


def _stat_signature(path: Path) -> tuple[int, int, int] | None:
    try:
        st = path.stat()
    except FileNotFoundError:
        return None
    return (st.st_ino, st.st_mtime_ns, st.st_size)


def _read_snapshot(index_path: Path, meta_path: Path, signature: _Signature) -> _Committed:
    with meta_path.open("r", encoding="utf-8") as f:
        meta = json.load(f)
    expected_checksum = meta.get("index_checksum")
    actual_checksum = _sha256_of(index_path)
    if expected_checksum != actual_checksum:
        raise VectorStoreCorruptedError(index_path, expected_checksum, actual_checksum)
    index = faiss.read_index(str(index_path))
    return _Committed(
        index=index,
        entries=MappingProxyType(meta["entries"]),
        next_int_id=meta["next_int_id"],
        dim=index.d,
        signature=signature,
    )


def load_committed(dir_path: Path) -> _Committed | None:
    """The committed snapshot of the namespace directory ``dir_path``, or ``None`` when neither file
    exists; exactly one file is ``VectorStoreCorruptedError`` (STOR-08). Never creates a directory. A hit costs two ``stat`` calls; a miss reads the sidecar,
    hashes and reads the index, then stats again: a signature that changed during the read (a reader
    inside another writer's two-rename window, research Pitfall 4) is retried once, then refused as
    ``VectorStoreCorruptedError``."""
    dir_path = Path(dir_path).resolve()
    index_path, meta_path = dir_path / "vector.faiss", dir_path / "vector.meta.json"
    error: VectorStoreCorruptedError | None = None
    for _attempt in range(2):
        index_sig, meta_sig = _stat_signature(index_path), _stat_signature(meta_path)
        if index_sig is None and meta_sig is None:
            return None
        if index_sig is None:
            error = VectorStoreCorruptedError(meta_path, None, "<missing vector.faiss>")
            continue
        if meta_sig is None:
            error = VectorStoreCorruptedError(index_path, None, "<missing vector.meta.json>")
            continue
        signature: _Signature = (index_sig, meta_sig)
        key = (str(dir_path), signature)
        with _SNAPSHOT_LOCK:
            hit = _SNAPSHOT_CACHE.get(key)
            if hit is not None:
                _SNAPSHOT_CACHE.move_to_end(key)
                return hit
        try:
            snapshot, error = _read_snapshot(index_path, meta_path, signature), None
        except VectorStoreCorruptedError as exc:
            snapshot, error = None, exc
        if (_stat_signature(index_path), _stat_signature(meta_path)) != signature:
            continue
        if snapshot is None:
            raise error  # type: ignore[misc]
        with _SNAPSHOT_LOCK:
            for stale in [k for k in _SNAPSHOT_CACHE if k[0] == key[0]]:
                del _SNAPSHOT_CACHE[stale]
            _SNAPSHOT_CACHE[key] = snapshot
            while len(_SNAPSHOT_CACHE) > _SNAPSHOT_CACHE_SIZE:
                _SNAPSHOT_CACHE.popitem(last=False)
        return snapshot
    raise error or VectorStoreCorruptedError(index_path, None, "<changed while being read>")


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
        self._pending_deletes: set[str] = set()
        self._prepared: tuple[Any, dict[str, dict[str, Any]], int] | None = None
        # Phase 10 review WR-04: the .tmp pair is one fixed path per namespace, shared by every
        # instance, so abort_prepared may unlink it only if THIS instance wrote it.
        self._staged = False
        self._dim: int | None = None
        self._index: Any = None
        self._entries: Mapping[str, dict[str, Any]] = {}
        self._next_int_id: int = 0
        self._loaded_signature: _Signature | None = None
        self._read_committed()

    def _committed_signature(self) -> tuple[tuple[int, int, int], ...] | None:
        """``(st_ino, st_mtime_ns, st_size)`` of the committed pair, or ``None`` when absent.
        ``os.replace`` changes the inode, so any other writer's commit changes it."""
        try:
            stats = (self._index_path.stat(), self._meta_path.stat())
        except FileNotFoundError:
            return None
        return tuple((st.st_ino, st.st_mtime_ns, st.st_size) for st in stats)

    def _read_committed(self) -> None:
        """Adopt the committed snapshot from :func:`load_committed` (shared, read-only, D-05),
        refusing a torn pair (WR-02)."""
        snapshot = load_committed(self._dir)
        if snapshot is None:
            self._index, self._entries, self._next_int_id = None, {}, 0
            self._loaded_signature = None
            return
        self._index, self._entries = snapshot.index, snapshot.entries
        self._next_int_id, self._dim = snapshot.next_int_id, snapshot.dim
        self._loaded_signature = snapshot.signature

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
        buffer if ``ids``/``embeddings``/``metadatas`` lengths disagree, or if a metadata dict uses a
        reserved key (``ReservedMetadataKeyError``, STOR-16) — a mis-paired vector is
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
        for meta in metadatas or ():
            reserved = _RESERVED_METADATA_KEYS.intersection(meta)
            if reserved:
                raise ReservedMetadataKeyError(list(reserved))
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
            self._pending_deletes.discard(doc_id)  # a later upsert cancels a buffered delete

    async def delete_by_ids(self, ids: list[str]) -> None:
        """Buffer a delete until the flush (D-08), so ``drop_pending_index_ops`` reverts it like the
        other stores' deletes. Drops any pending upsert of the same id; an id with no committed
        entry is a no-op at flush. Reads stay committed-only until then (research Pitfall 14)."""
        for doc_id in ids:
            self._pending.pop(doc_id, None)
            self._pending_deletes.add(doc_id)

    # ------------------------------------------------------------------ #
    # Reads — only committed (flushed) data is queryable                  #
    # ------------------------------------------------------------------ #

    async def query(self, vector: Any, top_k: int = 10) -> list[dict[str, Any]]:
        if top_k <= 0:
            raise InvalidTopKError(top_k)
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

    async def score_all(self, vector: Any) -> list[dict[str, Any]]:
        """§14.2's exhaustive dense inner-product sub-capability (06-01-PLAN.md): one scored entry
        per currently-committed vector, never a top-k truncation — the store-side counterpart
        HippoRAG's ``fact-scorer`` needs (it scores every fact against the query, not merely the
        nearest few). One batched Faiss search with ``k`` set to this index's own ``ntotal``,
        reusing the identical normalisation and result shape :meth:`query` already establishes —
        never composed by calling :meth:`query` in a loop with increasing ``top_k``. Sorted
        descending by score, ``id`` as the deterministic tie-break, matching
        ``parts_core/lightrag/chunk_vector.py``'s own sort key.
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        query_vec = np.asarray(vector, dtype="float32").reshape(1, -1)
        faiss.normalize_L2(query_vec)
        k = self._index.ntotal
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

    async def self_knn(self, *, top_k: int) -> dict[str, list[dict[str, Any]]]:
        """§14.2's batched self-KNN sub-capability (06-05-PLAN.md): one Faiss ``search`` call over
        the whole stored matrix at once, returning each stored id's own top-``k`` nearest
        neighbours excluding itself — never composed by calling :meth:`query` (or ``search``) once
        per stored entity, which would be exactly the ``O(N^2)`` pointwise emulation §14.2's
        Vector self-KNN row forbids (CONTRACT.md §14.2: "that the store exposes a batched self-KNN
        path rather than forcing an O(N^2) pointwise emulation").

        Requests ``top_k + 1`` neighbours per row (via :meth:`iter_vectors`'s own per-id
        ``reconstruct`` calls to rebuild the query matrix — never a second ``search`` call) so the
        self-match can be dropped, then issues exactly one batched ``search`` over that matrix.
        Each id's own neighbour list is sorted descending by score with ``id`` as the deterministic
        tie-break, matching :meth:`query`/:meth:`score_all`'s own sort key so all three
        retrieval-shaped methods agree on ordering. An empty store returns an empty mapping,
        following this class's own established empty-state behaviour rather than raising.
        ``top_k <= 0`` raises :class:`InvalidTopKError` (STOR-09).
        """
        if top_k <= 0:
            raise InvalidTopKError(top_k)
        if self._index is None or self._index.ntotal == 0:
            return {}

        doc_ids: list[str] = []
        rows: list[np.ndarray] = []
        for doc_id, vector in self.iter_vectors():
            doc_ids.append(doc_id)
            rows.append(vector)
        matrix = np.vstack(rows).astype("float32")

        k = min(top_k + 1, self._index.ntotal)
        scores, int_ids = self._index.search(matrix, k)

        int_to_doc = {v["int_id"]: did for did, v in self._entries.items()}
        results: dict[str, list[dict[str, Any]]] = {}
        for row_index, self_doc_id in enumerate(doc_ids):
            neighbours: list[dict[str, Any]] = []
            for score, int_id in zip(scores[row_index], int_ids[row_index], strict=True):
                if int_id == -1:
                    continue
                neighbour_id = int_to_doc.get(int(int_id))
                if neighbour_id is None or neighbour_id == self_doc_id:
                    continue
                entry = self._entries[neighbour_id]
                neighbours.append({"id": neighbour_id, "score": float(score), **entry["metadata"]})
            neighbours.sort(key=lambda r: (-r["score"], r["id"]))
            results[self_doc_id] = neighbours[:top_k]
        return results

    def iter_vectors(self) -> Iterator[tuple[str, np.ndarray]]:
        """Yield ``(doc_id, vector)`` for every committed (flushed) entry — WR-02: a public
        accessor for callers that need the raw stored vectors (e.g. the parity import verifier),
        so they read this store's public surface instead of reaching into ``_entries``/``_index``.
        """
        if self._index is None:
            return
        for doc_id, entry in self._entries.items():
            yield doc_id, self._index.reconstruct(entry["int_id"])

    def get_by_id(self, doc_id: str) -> dict[str, Any] | None:
        """The same per-item shape ``query()`` returns for ``doc_id`` (``{"id": doc_id,
        **metadata}``, score-free since no query vector is involved here) if this store currently
        holds a committed entry for it, else ``None``. A public accessor mirroring
        ``iter_vectors``'s own WR-02 reasoning: a caller that needs to resolve one specific
        committed entry back to its metadata — the seam's evidence-reference dereference (D-07) —
        reads this store's public surface instead of reaching into ``_entries``.
        """
        entry = self._entries.get(doc_id)
        if entry is None:
            return None
        return {"id": doc_id, **entry["metadata"]}

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    async def prepare(self) -> None:
        """D-07: stage the pending buffer as the ``.tmp`` file pair, leaving the committed pair
        untouched. If another writer committed since this instance loaded, rebase on the on-disk
        state first, so its vectors are kept and int ids never collide (research Pitfall 3). A
        failure leaves no ``.tmp`` and keeps ``_pending``/``_pending_deletes``. Buffered deletes are
        applied first, to ids present in the rebased entries only.

        Off-loop (WR-03): ``np.vstack``, ``faiss.add_with_ids`` and ``faiss.write_index`` are not
        obviously cheap at scale, and a slow flush on the loop would stall every sibling node in the
        runner's batch. ``self._index``/``self._entries``/``self._next_int_id`` are reassigned only on
        the event-loop thread, in ``commit_prepared``, so a concurrent ``query()`` never races a
        worker-thread mutation.
        """
        if not (self._pending or self._pending_deletes):
            return

        signature = self._committed_signature()
        if signature != self._loaded_signature:
            self._read_committed()
        deletes = [doc_id for doc_id in self._pending_deletes if doc_id in self._entries]
        if not (self._pending or deletes):
            return  # only deletes of uncommitted ids: nothing to write

        if self._index is None:
            dim = next(iter(self._pending.values())).vector.shape[0]
            base_index = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))
        else:
            base_index = self._index
        base_entries = dict(self._entries)
        base_next_int_id = self._next_int_id
        pending = dict(self._pending)

        def _do_flush() -> tuple[Any, dict[str, dict[str, Any]], int]:
            staging = faiss.clone_index(base_index)
            staging_entries = dict(base_entries)
            next_int_id = base_next_int_id
            if deletes:
                doomed = [staging_entries.pop(doc_id)["int_id"] for doc_id in deletes]
                staging.remove_ids(np.array(doomed, dtype="int64"))

            vectors: list[np.ndarray] = []
            int_ids: list[int] = []
            for doc_id, doc in pending.items():
                if doc_id in staging_entries:
                    staging.remove_ids(np.array([staging_entries[doc_id]["int_id"]], dtype="int64"))
                int_id = next_int_id
                next_int_id += 1
                vectors.append(doc.vector)
                int_ids.append(int_id)
                staging_entries[doc_id] = {"int_id": int_id, "metadata": doc.metadata}

            if vectors:
                matrix = np.vstack(vectors).astype("float32")
                staging.add_with_ids(matrix, np.array(int_ids, dtype="int64"))

            self._write_staged(staging, staging_entries, next_int_id)
            return staging, staging_entries, next_int_id

        loop = asyncio.get_running_loop()
        self._prepared = await loop.run_in_executor(None, _do_flush)

    async def commit_prepared(self) -> None:
        """Rename the staged pair into place, then adopt it on the event-loop thread."""
        if self._prepared is not None:
            self._commit_staged()
            self._staged = False
            self._index, self._entries, self._next_int_id = self._prepared
            self._dim = self._index.d
            self._loaded_signature = self._committed_signature()
            self._prepared = None
        self._pending.clear()
        self._pending_deletes.clear()

    async def abort_prepared(self) -> None:
        if self._staged:
            for tmp in self._tmp_paths():
                tmp.unlink(missing_ok=True)
            self._staged = False
        self._prepared = None
        self._pending.clear()
        self._pending_deletes.clear()

    async def index_done_callback(self) -> None:
        """Flush the pending buffer into the index and sidecar: ``prepare`` then
        ``commit_prepared`` in one call."""
        await self.prepare()
        await self.commit_prepared()

    def _tmp_paths(self) -> tuple[Path, Path]:
        return (
            self._index_path.with_suffix(self._index_path.suffix + ".tmp"),
            self._meta_path.with_suffix(self._meta_path.suffix + ".tmp"),
        )

    def _write_staged(
        self, index: Any, entries: dict[str, dict[str, Any]], next_int_id: int
    ) -> None:
        """Write the index and sidecar to the ``.tmp`` pair. An ordinary Python exception during
        either write removes both and raises, so the committed pair stays untouched. The sidecar
        carries a SHA-256 ``index_checksum`` of the index it accompanies, checked at the next open
        (WR-02)."""
        tmp_index, tmp_meta = self._tmp_paths()
        self._staged = True
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
            self._staged = False
            raise

    def _commit_staged(self) -> None:
        """Two renames, not one transaction (WR-02, module docstring): the sidecar checksum catches
        a crash between them at the next open."""
        tmp_index, tmp_meta = self._tmp_paths()
        os.replace(tmp_index, self._index_path)
        os.replace(tmp_meta, self._meta_path)

    async def drop_pending_index_ops(self) -> None:
        await self.abort_prepared()

    async def drop(self) -> dict[str, str]:
        try:
            self._index_path.unlink(missing_ok=True)
            self._meta_path.unlink(missing_ok=True)
            self._index = None
            self._entries = {}
            self._next_int_id = 0
            self._dim = None
            self._pending.clear()
            self._pending_deletes.clear()
            return {"status": "success", "message": "data dropped"}
        except Exception as exc:  # noqa: BLE001 — drop()'s own documented contract (v1 StorageNameSpace)
            return {"status": "error", "message": str(exc)}


class VectorNamespaceNotSelectedError(RuntimeError):
    """Raised by :class:`MultiNamespaceVectorStore`'s ``query``/``upsert``/``delete_by_ids`` when
    no namespace has been selected via :meth:`MultiNamespaceVectorStore.select` first — the whole
    point of that handle: a node that forgets to select its own namespace can no longer be silently
    served a default one. Names the workspace and lists the namespace directories under it that
    hold a ``vector.faiss`` (STOR-09) (this handle never enumerates a fixed namespace set up front, so the
    honest answer to "available" is what is actually there), following
    :class:`VectorStoreCorruptedError`'s and ``StoreNotWiredError``'s own house style — a named
    exception carrying the specifics, never a bare ``None`` and never a silent fallback.
    """

    def __init__(self, workspace: str, available: list[str]):
        self.workspace = workspace
        self.available = list(available)
        super().__init__(
            f"no vector namespace selected for workspace {workspace!r} — call "
            "select(namespace) before query()/upsert()/delete_by_ids(). Namespaces available "
            f"under this workspace: {self.available!r}"
        )


class MultiNamespaceVectorStore(StorageNameSpace):
    """A vector store handle over ``<store_root>/<workspace>/<namespace>/`` that binds no single
    namespace at construction time. Each vector-reading §L.1 position (``entity-lookup``,
    ``relation-lookup``, ``chunk-vector``, ``chunk-sel-kg``) selects its own namespace via
    ``select(name)`` before reading — the fix for ``run_arm._build_stores`` previously binding one
    ``FaissVectorStore`` instance (the ``chunks`` namespace) under the sole key ``"vector"``, which
    silently served every vector-reading node the same chunks index regardless of which namespace
    its own position is actually defined over.

    ``select(name)`` is lazy and cached: the first call for a given namespace constructs a real
    :class:`FaissVectorStore` and caches it; every later ``select(name)`` for the same name returns
    the identical object (the same open index, never re-opened). Lifecycle methods
    (``initialize``/``finalize``/``index_done_callback``/``drop_pending_index_ops``/``drop``) fan
    out only over namespaces this handle has actually selected so far — an unselected namespace is
    never constructed just to be torn down.

    ``query``/``upsert``/``delete_by_ids``/``score_all``/``self_knn``/``get_by_id``/``iter_vectors``
    called on this handle itself (rather than on a namespace returned by ``select``) refuse by name
    via :class:`VectorNamespaceNotSelectedError` (STOR-09): a caller that forgot to select can no
    longer be handed a default index. These are store-level refusals, outside the seam catalogue
    (D-12).
    """

    def __init__(self, workspace: str, store_root: str | Path) -> None:
        super().__init__(namespace="<multi>", workspace=workspace)
        self._store_root = store_root
        self._children: dict[str, FaissVectorStore] = {}

    def select(self, namespace: str) -> FaissVectorStore:
        child = self._children.get(namespace)
        if child is None:
            child = FaissVectorStore(
                namespace=namespace, workspace=self.workspace, store_root=self._store_root
            )
            self._children[namespace] = child
        return child

    def _available_namespaces(self) -> list[str]:
        base = Path(self._store_root) / self.workspace
        if base.exists():
            try:
                return sorted(p.name for p in base.iterdir() if (p / "vector.faiss").is_file())
            except OSError:
                pass
        return sorted(self._children.keys())

    async def query(self, vector: Any, top_k: int = 10) -> list[dict[str, Any]]:
        raise VectorNamespaceNotSelectedError(self.workspace, self._available_namespaces())

    async def upsert(
        self,
        ids: list[str],
        embeddings: Any,
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        raise VectorNamespaceNotSelectedError(self.workspace, self._available_namespaces())

    async def delete_by_ids(self, ids: list[str]) -> None:
        raise VectorNamespaceNotSelectedError(self.workspace, self._available_namespaces())

    async def score_all(self, vector: Any) -> list[dict[str, Any]]:
        raise VectorNamespaceNotSelectedError(self.workspace, self._available_namespaces())

    async def self_knn(self, *, top_k: int) -> dict[str, list[dict[str, Any]]]:
        raise VectorNamespaceNotSelectedError(self.workspace, self._available_namespaces())

    def get_by_id(self, doc_id: str) -> dict[str, Any] | None:
        raise VectorNamespaceNotSelectedError(self.workspace, self._available_namespaces())

    def iter_vectors(self) -> Iterator[tuple[str, np.ndarray]]:
        # a plain method, not a generator, so the refusal fires at call time (research Pitfall 12)
        raise VectorNamespaceNotSelectedError(self.workspace, self._available_namespaces())

    async def initialize(self) -> None:
        for child in self._children.values():
            await child.initialize()

    async def finalize(self) -> None:
        for child in self._children.values():
            await child.finalize()

    async def index_done_callback(self) -> None:
        for child in self._children.values():
            await child.index_done_callback()

    async def drop_pending_index_ops(self) -> None:
        for child in self._children.values():
            await child.drop_pending_index_ops()

    async def prepare(self) -> None:
        for child in self._children.values():
            await child.prepare()

    async def commit_prepared(self) -> None:
        for child in self._children.values():
            await child.commit_prepared()

    async def abort_prepared(self) -> None:
        for child in self._children.values():
            await child.abort_prepared()

    async def drop(self) -> dict[str, str]:
        errors: dict[str, str] = {}
        for name, child in self._children.items():
            result = await child.drop()
            if result.get("status") != "success":
                errors[name] = result.get("message", "unknown error")
        if errors:
            return {"status": "error", "message": str(errors)}
        return {"status": "success", "message": f"dropped {len(self._children)} namespace(s)"}
