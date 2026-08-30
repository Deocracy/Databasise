"""Storage lifecycle ABC, reproduced by copy (not import) from v1's ``StorageNameSpace``
(upstream_ref: v1/lightrag/base.py, lines 160-219; D-14/CONTRACT §7 lineage attribution).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class StorageNameSpace(ABC):
    """Every store adapter in this phase shares this lifecycle, so the runner has one
    commit/abort contract regardless of backend: ``initialize``/``finalize`` for setup/teardown,
    ``index_done_callback`` for commit, ``drop_pending_index_ops`` for abort, ``drop`` for a full
    reset. v1's ``global_config`` field is intentionally dropped from this reproduction
    (``namespace``/``workspace`` only) — nothing in this tracer needs it yet; a later plan can add
    it back without breaking this ABC's shape.
    """

    namespace: str
    workspace: str

    async def initialize(self) -> None:
        """Initialize the storage."""
        return

    async def finalize(self) -> None:
        """Finalize the storage."""
        return

    @abstractmethod
    async def index_done_callback(self) -> None:
        """Commit the storage operations after indexing."""

    async def drop_pending_index_ops(self) -> None:
        """Discard any not-yet-flushed buffered writes (the abort path)."""
        return

    @abstractmethod
    async def drop(self) -> dict[str, str]:
        """Drop all data from storage and clean up resources."""
