"""Content-addressed filesystem blob store (D-06): SHA-256-keyed, git-object-store-style
fan-out layout under the caller-supplied store root's namespace directory. New primitive — v1
has no blob store to port.

Fan-out layout (Claude's-Discretion choice per CONTEXT.md, recorded here as a layout decision
requiring migration to change, not a tuning knob): **two** levels of two hex characters each, so
a digest ``abcd1234...`` lands at ``<namespace_dir>/blobs/ab/cd/abcd1234...``, carrying the full
64-character digest as the filename. Git's own object store uses one level; two keeps the leaf
directory count bounded well below any filesystem's practical per-directory limit for a
multi-million-blob store, at the cost of one extra directory level.

``put()`` writes to a temporary file in the same directory and ``os.replace``s into position, so
a partially-written blob can never be observed at its final path. Identical content already
stored is a no-op — content addressing makes "overwrite" meaningless, since the bytes already at
that path are exactly the bytes that would be written.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from databasise.stores.base import StorageNameSpace


class BlobNotFoundError(KeyError):
    """Raised by ``get``/``read_range`` when the requested digest has no stored blob — a missing
    blob is never mistaken for empty content (an empty blob has its own real digest and rounds
    trips normally; only a genuinely absent digest raises this).
    """


class FilesystemBlobStore(StorageNameSpace):
    def __init__(self, namespace: str, workspace: str, store_root: str | Path) -> None:
        super().__init__(namespace=namespace, workspace=workspace)
        self._blobs_root = Path(store_root) / workspace / namespace / "blobs"
        self._blobs_root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, digest: str) -> Path:
        return self._blobs_root / digest[:2] / digest[2:4] / digest

    def put(self, content: bytes) -> str:
        """Hash ``content``, compute its fan-out path, and write only if not already present."""
        digest = hashlib.sha256(content).hexdigest()
        path = self._path_for(digest)
        if path.exists():
            return digest  # identical content already stored — a no-op, never an overwrite
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.parent / f".{digest}.{uuid.uuid4().hex}.tmp"
        tmp_path.write_bytes(content)
        os.replace(tmp_path, path)  # atomic — a partial write is never observable at `path`
        return digest

    def get(self, digest: str) -> bytes:
        path = self._path_for(digest)
        if not path.exists():
            raise BlobNotFoundError(digest)
        return path.read_bytes()

    def read_range(self, digest: str, offset: int, length: int) -> bytes:
        """Read ``length`` bytes starting at ``offset`` without loading the whole blob.

        Raises if the requested range extends past the blob's length, rather than silently
        returning short data — this is the operation CONTRACT §2's ``reads_blob`` amendment and
        the ``addressable-subrange`` sub-capability exist for.
        """
        path = self._path_for(digest)
        if not path.exists():
            raise BlobNotFoundError(digest)
        size = path.stat().st_size
        if offset < 0 or offset + length > size:
            raise ValueError(
                f"range [{offset}, {offset + length}) extends past blob {digest} (length {size})"
            )
        with path.open("rb") as f:
            f.seek(offset)
            return f.read(length)

    def delete(self, digest: str) -> None:
        """Remove the blob at ``digest``; a no-op (never an error) if it is already absent."""
        self._path_for(digest).unlink(missing_ok=True)
        # Pruning an emptied fan-out directory could race a concurrent put() repopulating that
        # same prefix — leave the (possibly now-empty) directory rather than risk deleting one a
        # concurrent writer just recreated.

    async def index_done_callback(self) -> None:
        """No-op: ``put()``'s temp-file-plus-``os.replace`` writes are already atomic and
        immediately durable, so there is nothing buffered left to flush at commit time.
        Implemented explicitly (rather than inherited) so a reader does not have to go looking
        for why it is missing.
        """
        return

    async def drop(self) -> dict[str, str]:
        try:
            for entry in self._blobs_root.rglob("*"):
                if entry.is_file():
                    entry.unlink()
            return {"status": "success", "message": "data dropped"}
        except Exception as exc:  # noqa: BLE001 — drop()'s own documented contract (v1 StorageNameSpace)
            return {"status": "error", "message": str(exc)}
