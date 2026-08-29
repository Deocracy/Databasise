"""CozoGraphStorage — embedded graph store backed by CozoDB (RocksDB).

This module implements the full ``BaseGraphStorage`` contract (~18 async methods)
using an embedded Cozo database via ``pycozo``.

Schema
------
Two stored relations mirror NetworkX's node/edge attribute dicts:

    nodes { id: String => attrs: Json }
    edges { src: String, tgt: String => attrs: Json }

Edges are stored with a canonical key ordering (src < tgt) so the undirected
lookups in both directions (A→B and B→A) resolve to the same row.

Forward-compatibility shaping (Phase 6)
----------------------------------------
The schema is intentionally shaped so adding a ``Validity``-typed key column
later (for bi-temporal append-and-invalidate versioning, Phase 6) is an
ADDITIVE migration — no existing column is dropped or renamed. Provenance
fields ``source_id`` and ``file_path`` are preserved inside the ``attrs``
JSON blob because the upstream LightRAG pipeline populates them and downstream
consumers (citation tracking, deduplication) depend on them.

Deferred-write contract (D-P1.1-04)
-------------------------------------
Cozo commits each ``:put``/``:rm`` immediately in its own transaction, but
LightRAG buffers writes in-memory and flushes them at ``index_done_callback``.
This adapter resolves the mismatch by maintaining four in-process buffers:

    _pending_node_puts  : dict[id, attrs]      — nodes to upsert
    _pending_edge_puts  : dict[(src,tgt), attrs] — edges to upsert (canonical order)
    _pending_node_rms   : set[id]               — node ids to delete
    _pending_edge_rms   : set[(src,tgt)]        — edge pairs to delete (canonical order)

Reads consult these buffers FIRST (read-your-writes before flush). All four
buffers are cleared on ``index_done_callback`` (commit) or
``drop_pending_index_ops`` (abort).

Thread / event-loop safety (D-P1.1-04)
----------------------------------------
``pycozo``'s ``Client.run()`` is synchronous. Every call is dispatched via
``asyncio.get_running_loop().run_in_executor(None, ...)`` so it never blocks
the async event loop. This is the same pattern the threat register prescribes
for T-01.1-05.

Security (T-01.1-06)
----------------------
All node IDs, edge endpoints, and search queries are passed as bound
parameters to ``Client.run()`` — never string-interpolated into the
CozoScript body. Entity names containing Datalog metacharacters (``{``, ``}``,
``?``, ``*``) cannot alter the query structure.

Cozo known-bug regression tests (D-P1.1-07)
--------------------------------------------
The unit tests in ``tests/kg/test_cozo_graph_storage.py`` include targeted
regression shapes for the frozen-0.7.6 bugs:
  #244 aggregation 0-rows, #275 wrong DataValue types,
  #253 JSON key-order loss, #296/#269 UUID sort/coercion.

License note
------------
``cozo-embedded`` 0.7.6 is licensed under the Mozilla Public License 2.0
(MPL-2.0). Source: https://github.com/cozodb/cozo. Sourcerer ships it as a
dependency; MPL-2.0 is compatible with the project's MIT license.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections import deque
from dataclasses import dataclass, field
from typing import Any, final

from lightrag.base import BaseGraphStorage
from lightrag.types import KnowledgeGraph, KnowledgeGraphEdge, KnowledgeGraphNode
from lightrag.utils import logger, validate_workspace

from .shared_storage import get_namespace_lock, get_update_flag, set_all_update_flags

try:
    from pycozo.client import Client as CozoClient
except ImportError as _cozo_import_err:
    raise ImportError(
        "cozo-embedded is required for CozoGraphStorage. "
        "Install with: pip install 'pycozo[embedded]'"
    ) from _cozo_import_err


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cozo_rows(result: Any) -> list[list]:
    """Normalise a pycozo run() result to ``list[list]``.

    pycozo 0.7.6 returns a plain dict ``{"headers": [...], "rows": [...]}``
    when pandas is not importable, or a pandas DataFrame when it is. This
    function handles both shapes and always returns the bare rows list.

    Args:
        result: Return value from ``Client.run()``.

    Returns:
        List of row lists (may be empty).
    """
    if hasattr(result, "to_dict"):
        # pandas DataFrame path
        return result.values.tolist()
    # plain dict path: {"headers": [...], "rows": [...]}
    return result.get("rows", [])


def _canonical_edge_key(src: str, tgt: str) -> tuple[str, str]:
    """Return (src, tgt) with lexicographic ordering so A-B and B-A are the same key."""
    if src > tgt:
        return tgt, src
    return src, tgt


def _attrs_to_dict(raw: Any) -> dict[str, str]:
    """Coerce a Cozo Json column value to a plain ``dict[str, str]``.

    Cozo may return the Json column as a Python dict or as a JSON string,
    depending on the pycozo version and whether pandas is active.

    The values are coerced to strings to match NetworkXStorage's GraphML
    round-trip which serialises all attributes as strings.
    """
    if isinstance(raw, str):
        raw = json.loads(raw)
    if not isinstance(raw, dict):
        return {}
    return {k: str(v) for k, v in raw.items()}


# ---------------------------------------------------------------------------
# Storage class
# ---------------------------------------------------------------------------

@final
@dataclass
class CozoGraphStorage(BaseGraphStorage):
    """Embedded graph store backed by CozoDB (RocksDB) via pycozo.

    Storage model
    -------------
    A single CozoDB instance (``Client('rocksdb', db_path)``) holds two
    stored relations: ``nodes`` and ``edges``. All mutations are buffered
    in-process and flushed as a single Cozo transaction at
    ``index_done_callback``.

    Concurrency invariants
    ----------------------
    Single writer per workspace (inherited from NetworkXStorage's model).
    ``_storage_lock`` serialises commits; all ``client.run`` calls are
    dispatched through ``run_in_executor``.
    """

    # ------------------------------------------------------------------ #
    # Post-init / initialise / finalise                                   #
    # ------------------------------------------------------------------ #

    def __post_init__(self):
        # Reject path-traversal characters before using workspace in a path
        validate_workspace(self.workspace)

        working_dir = self.global_config["working_dir"]
        if self.workspace:
            workspace_dir = os.path.join(working_dir, self.workspace)
        else:
            workspace_dir = working_dir
            self.workspace = ""

        os.makedirs(workspace_dir, exist_ok=True)

        # RocksDB database directory (analogous to graph_<ns>.graphml in NetworkX)
        self._db_path = os.path.join(
            workspace_dir, f"cozo_graph_{self.namespace}.db"
        )

        # Shared-storage hooks (initialised in initialize())
        self._storage_lock = None
        self.storage_updated = None

        # In-process write buffers (see module docstring — deferred-write contract)
        self._pending_node_puts: dict[str, dict] = {}
        self._pending_edge_puts: dict[tuple[str, str], dict] = {}
        self._pending_node_rms: set[str] = set()
        self._pending_edge_rms: set[tuple[str, str]] = set()

        # Open the Cozo client eagerly (synchronous in __post_init__ is fine
        # because __post_init__ itself is not async)
        self._client: CozoClient = CozoClient("rocksdb", self._db_path)

        # Ensure the two stored relations exist (idempotent :create if not exists)
        self._ensure_relations()

        logger.info(
            f"[{self.workspace}] CozoGraphStorage opened: {self._db_path}"
        )

    def _ensure_relations(self) -> None:
        """Create stored relations if they do not yet exist.

        Uses Cozo's ``?`` suffix (``::if-not-exists``) pattern by catching the
        "relation already exists" error from a plain ``:create``.  This keeps
        the schema stable across restarts.
        """
        # nodes relation: id (key) → attrs (Json value)
        try:
            self._client.run(":create nodes {id: String => attrs: Json}", {})
            logger.debug(f"[{self.workspace}] Created 'nodes' relation")
        except Exception as e:
            if "already exists" in str(e).lower() or "relation" in str(e).lower():
                logger.debug(f"[{self.workspace}] 'nodes' relation already exists")
            else:
                raise

        # edges relation: src, tgt (composite key, canonical order) → attrs (Json value)
        try:
            self._client.run(
                ":create edges {src: String, tgt: String => attrs: Json}", {}
            )
            logger.debug(f"[{self.workspace}] Created 'edges' relation")
        except Exception as e:
            if "already exists" in str(e).lower() or "relation" in str(e).lower():
                logger.debug(f"[{self.workspace}] 'edges' relation already exists")
            else:
                raise

        # Full-text search index on node ids (for search_labels / ::fts)
        # NOTE: Cozo 0.7.6's ::fts create syntax requires a specific tokenizer
        # argument that differs across versions and is not clearly documented for
        # the frozen 0.7.6 wheel. The linear-scan fallback in search_labels produces
        # results identical to NetworkXStorage (same scoring algorithm), so FTS is
        # disabled here for parity correctness. A future phase may enable it once
        # the correct syntax for the installed version is confirmed.
        # Tracked in SUMMARY.md as a known deviation.
        self._fts_available = False

    async def initialize(self) -> None:
        """Wire up the cross-process update flag and namespace lock."""
        self.storage_updated = await get_update_flag(
            self.namespace, workspace=self.workspace
        )
        self._storage_lock = get_namespace_lock(
            self.namespace, workspace=self.workspace
        )

    async def finalize(self) -> None:
        """Close the Cozo client, releasing the RocksDB file handles."""
        if self._client is not None:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._client.close)
            self._client = None
            logger.info(f"[{self.workspace}] CozoGraphStorage closed: {self._db_path}")

    # ------------------------------------------------------------------ #
    # Internal run helper                                                 #
    # ------------------------------------------------------------------ #

    async def _run(self, script: str, params: dict | None = None) -> list[list]:
        """Run a CozoScript query off the event loop and return plain rows."""
        if params is None:
            params = {}
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, lambda: self._client.run(script, params)
        )
        return _cozo_rows(result)

    # ------------------------------------------------------------------ #
    # READ methods (consult in-process buffer for read-your-writes)       #
    # ------------------------------------------------------------------ #

    async def has_node(self, node_id: str) -> bool:
        # Check buffer first
        if node_id in self._pending_node_rms:
            return False
        if node_id in self._pending_node_puts:
            return True
        # Query Cozo
        rows = await self._run(
            "?[id] := *nodes{id}, id = $id",
            {"id": node_id},
        )
        return len(rows) > 0

    async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        key = _canonical_edge_key(source_node_id, target_node_id)
        if key in self._pending_edge_rms:
            return False
        if key in self._pending_edge_puts:
            return True
        rows = await self._run(
            "?[src, tgt] := *edges{src, tgt}, src = $src, tgt = $tgt",
            {"src": key[0], "tgt": key[1]},
        )
        return len(rows) > 0

    async def get_node(self, node_id: str) -> dict[str, str] | None:
        if node_id in self._pending_node_rms:
            return None
        if node_id in self._pending_node_puts:
            return {k: str(v) for k, v in self._pending_node_puts[node_id].items()}
        rows = await self._run(
            "?[attrs] := *nodes{id, attrs}, id = $id",
            {"id": node_id},
        )
        if not rows:
            return None
        return _attrs_to_dict(rows[0][0])

    async def node_degree(self, node_id: str) -> int:
        """Count undirected incident edges (from disk + buffer, deduplicated)."""
        # Gather keys from disk
        db_rows = await self._run(
            "?[src, tgt] := *edges{src, tgt}, src = $id or tgt = $id",
            {"id": node_id},
        )
        db_keys: set[tuple[str, str]] = set()
        for r in db_rows:
            db_keys.add(_canonical_edge_key(r[0], r[1]))

        # Apply buffer: add pending puts, remove pending rms
        effective = (db_keys - self._pending_edge_rms) | {
            k
            for k in self._pending_edge_puts
            if node_id in k
        }
        return len(effective)

    async def edge_degree(self, src_id: str, tgt_id: str) -> int:
        return await self.node_degree(src_id) + await self.node_degree(tgt_id)

    async def get_edge(
        self, source_node_id: str, target_node_id: str
    ) -> dict[str, str] | None:
        key = _canonical_edge_key(source_node_id, target_node_id)
        if key in self._pending_edge_rms:
            return None
        if key in self._pending_edge_puts:
            return {k: str(v) for k, v in self._pending_edge_puts[key].items()}
        rows = await self._run(
            "?[attrs] := *edges{src, tgt, attrs}, src = $src, tgt = $tgt",
            {"src": key[0], "tgt": key[1]},
        )
        if not rows:
            return None
        return _attrs_to_dict(rows[0][0])

    async def get_node_edges(
        self, source_node_id: str
    ) -> list[tuple[str, str]] | None:
        """Return (src, tgt) tuples for all edges incident on source_node_id.

        Returns None if the node does not exist (mirrors NetworkXStorage).
        Note: tuples are returned in the natural (source_node_id, neighbour)
        orientation rather than the canonical (min, max) order, matching
        NetworkX's ``graph.edges(node)`` output.
        """
        if not await self.has_node(source_node_id):
            return None

        # Disk edges
        db_rows = await self._run(
            "?[src, tgt] := *edges{src, tgt}, src = $id or tgt = $id",
            {"id": source_node_id},
        )

        # Build effective edge set (canonical keys)
        db_keys: dict[tuple[str, str], tuple[str, str]] = {}
        for r in db_rows:
            raw = (r[0], r[1])
            key = _canonical_edge_key(raw[0], raw[1])
            # Orientation: put source_node_id first
            if raw[0] == source_node_id:
                db_keys[key] = (raw[0], raw[1])
            else:
                db_keys[key] = (source_node_id, raw[0] if raw[1] == source_node_id else raw[1])

        # Apply buffer removals
        for rm_key in self._pending_edge_rms:
            db_keys.pop(rm_key, None)

        # Apply buffer additions
        for put_key in self._pending_edge_puts:
            if source_node_id in put_key:
                other = put_key[1] if put_key[0] == source_node_id else put_key[0]
                db_keys[put_key] = (source_node_id, other)

        return list(db_keys.values())

    async def get_all_labels(self) -> list[str]:
        """Return all node IDs sorted alphabetically (from disk + buffer)."""
        rows = await self._run("?[id] := *nodes{id}", {})
        db_ids = {r[0] for r in rows}
        # Apply buffer
        effective = (db_ids - self._pending_node_rms) | set(self._pending_node_puts.keys())
        return sorted(effective)

    async def get_all_nodes(self) -> list[dict]:
        """Return all nodes as dicts with an 'id' key (from disk + buffer)."""
        rows = await self._run("?[id, attrs] := *nodes{id, attrs}", {})

        # Build from disk
        result: dict[str, dict] = {}
        for r in rows:
            node_id = r[0]
            attrs = _attrs_to_dict(r[1])
            attrs["id"] = node_id
            result[node_id] = attrs

        # Apply removes
        for rm_id in self._pending_node_rms:
            result.pop(rm_id, None)

        # Apply pending puts (overlay)
        for put_id, put_attrs in self._pending_node_puts.items():
            node_dict = {k: str(v) for k, v in put_attrs.items()}
            node_dict["id"] = put_id
            result[put_id] = node_dict

        return list(result.values())

    async def get_all_edges(self) -> list[dict]:
        """Return all edges as dicts with 'source' and 'target' keys."""
        rows = await self._run("?[src, tgt, attrs] := *edges{src, tgt, attrs}", {})

        result: dict[tuple[str, str], dict] = {}
        for r in rows:
            src, tgt = r[0], r[1]
            key = (src, tgt)
            attrs = _attrs_to_dict(r[2])
            attrs["source"] = src
            attrs["target"] = tgt
            result[key] = attrs

        # Apply removes (canonical keys)
        for rm_key in self._pending_edge_rms:
            result.pop(rm_key, None)

        # Apply pending puts
        for put_key, put_attrs in self._pending_edge_puts.items():
            edge_dict = {k: str(v) for k, v in put_attrs.items()}
            edge_dict["source"] = put_key[0]
            edge_dict["target"] = put_key[1]
            result[put_key] = edge_dict

        return list(result.values())

    async def get_popular_labels(self, limit: int = 300) -> list[str]:
        """Return node IDs sorted by degree descending (from disk + buffer)."""
        # Get all node IDs (effective after buffer)
        all_labels = await self.get_all_labels()

        # Compute degree for each (using buffered degree computation)
        degrees: list[tuple[str, int]] = []
        for node_id in all_labels:
            deg = await self.node_degree(node_id)
            degrees.append((node_id, deg))

        degrees.sort(key=lambda x: x[1], reverse=True)
        popular = [node_id for node_id, _ in degrees[:limit]]

        logger.debug(
            f"[{self.workspace}] Retrieved {len(popular)} popular labels (limit: {limit})"
        )
        return popular

    async def search_labels(self, query: str, limit: int = 50) -> list[str]:
        """Search node IDs for query using FTS index (falls back to linear scan).

        Ordering matches NetworkXStorage: exact > prefix > contains, then
        alphabetical within each tier.
        """
        query_lower = query.lower().strip()
        if not query_lower:
            return []

        # Try FTS first (only for disk data; buffer is small so linear scan ok)
        candidate_ids: set[str] = set()

        if self._fts_available:
            try:
                fts_rows = await self._run(
                    "?[id, score] := ~nodes:node_id_fts{id | query: $q, bind_score: score}",
                    {"q": query},
                )
                for r in fts_rows:
                    candidate_ids.add(r[0])
            except Exception as e:
                logger.warning(
                    f"[{self.workspace}] FTS search failed, falling back to linear scan: {e}"
                )
                candidate_ids = set()

        # Also include buffer candidates
        for buf_id in self._pending_node_puts:
            if query_lower in buf_id.lower():
                candidate_ids.add(buf_id)

        # If FTS returned no candidates (or FTS unavailable), fall back to
        # full linear scan over disk+buffer IDs
        if not candidate_ids:
            all_labels = await self.get_all_labels()
            candidate_ids = {n for n in all_labels if query_lower in n.lower()}
        else:
            # Also add any disk nodes that contain query but weren't in FTS results
            # (FTS tokenisation may miss substring-only matches)
            all_labels = await self.get_all_labels()
            for lbl in all_labels:
                if query_lower in lbl.lower():
                    candidate_ids.add(lbl)

        # Remove pending-rm nodes
        candidate_ids -= self._pending_node_rms

        # Score the candidates (same algorithm as NetworkXStorage)
        matches: list[tuple[str, int]] = []
        for node_str in candidate_ids:
            node_lower = node_str.lower()
            if query_lower not in node_lower:
                continue
            if node_lower == query_lower:
                score = 1000
            elif node_lower.startswith(query_lower):
                score = 500
            else:
                score = 100 - len(node_str)
                if f" {query_lower}" in node_lower or f"_{query_lower}" in node_lower:
                    score += 50
            matches.append((node_str, score))

        matches.sort(key=lambda x: (-x[1], x[0]))
        results = [m[0] for m in matches[:limit]]

        logger.debug(
            f"[{self.workspace}] search_labels('{query}') → {len(results)} results"
        )
        return results

    # ------------------------------------------------------------------ #
    # WRITE methods (buffer only — flush at index_done_callback)          #
    # ------------------------------------------------------------------ #

    async def upsert_node(self, node_id: str, node_data: dict[str, str]) -> None:
        """Buffer a node upsert. Flushed at index_done_callback."""
        self._pending_node_rms.discard(node_id)
        self._pending_node_puts[node_id] = dict(node_data)

    async def upsert_edge(
        self,
        source_node_id: str,
        target_node_id: str,
        edge_data: dict[str, str],
    ) -> None:
        """Buffer an edge upsert. Flushed at index_done_callback."""
        key = _canonical_edge_key(source_node_id, target_node_id)
        self._pending_edge_rms.discard(key)
        self._pending_edge_puts[key] = dict(edge_data)

    async def delete_node(self, node_id: str) -> None:
        """Buffer a node deletion. Flushed at callback (with cascade edge deletion at flush time)."""
        self._pending_node_puts.pop(node_id, None)
        self._pending_node_rms.add(node_id)
        # Also remove any in-buffer edges incident on this node
        # (disk-side incident edges will be cascade-deleted at flush time via multi_transact)
        rm_edge_keys = [k for k in self._pending_edge_puts if node_id in k]
        for k in rm_edge_keys:
            del self._pending_edge_puts[k]
        logger.debug(f"[{self.workspace}] Buffered deletion of node: {node_id}")

    async def remove_nodes(self, nodes: list[str]) -> None:
        """Buffer deletion of multiple nodes."""
        for node_id in nodes:
            await self.delete_node(node_id)

    async def remove_edges(self, edges: list[tuple[str, str]]) -> None:
        """Buffer deletion of multiple edges."""
        for src, tgt in edges:
            key = _canonical_edge_key(src, tgt)
            self._pending_edge_puts.pop(key, None)
            self._pending_edge_rms.add(key)

    # ------------------------------------------------------------------ #
    # Commit / abort / drop                                               #
    # ------------------------------------------------------------------ #

    async def index_done_callback(self) -> None:
        """Flush all buffered ops to Cozo as a single transaction.

        Mirrors NetworkXStorage's two-block structure:
          Block 1: Early-return if another process committed while we buffered.
          Block 2: Actual flush + notify other processes.

        Raises on flush error (consistent with NetworkXStorage — do NOT swallow,
        so the document is not falsely marked PROCESSED, per T-01.1-03).
        """
        async with self._storage_lock:
            if self.storage_updated.value:
                logger.info(
                    f"[{self.workspace}] Graph was updated by another process; "
                    "discarding local buffer (will reload on next read)"
                )
                # Discard the buffer — the external update supersedes our changes
                self._clear_buffers()
                self.storage_updated.value = False
                return

        # Build one multi-statement CozoScript for ALL pending ops
        async with self._storage_lock:
            try:
                await self._flush_buffers()
                await set_all_update_flags(self.namespace, workspace=self.workspace)
                self.storage_updated.value = False
                self._clear_buffers()
            except Exception as e:
                logger.error(
                    f"[{self.workspace}] Error flushing graph buffer to Cozo: {e}"
                )
                raise

    async def _flush_buffers(self) -> None:
        """Execute all pending ops atomically via multi_transact + run_in_executor.

        Uses ``Client.multi_transact(write=True)`` to group all buffered
        ``:put`` and ``:rm`` operations in one atomic transaction (T-01.1-03).
        Node deletes cascade to incident disk edges inside the transaction.
        The entire transaction runs on the executor thread so the event loop
        is never blocked (T-01.1-05).
        """
        if not (
            self._pending_node_puts
            or self._pending_edge_puts
            or self._pending_node_rms
            or self._pending_edge_rms
        ):
            logger.debug(f"[{self.workspace}] Nothing to flush")
            return

        logger.info(
            f"[{self.workspace}] Flushing buffer: "
            f"{len(self._pending_node_puts)} node puts, "
            f"{len(self._pending_edge_puts)} edge puts, "
            f"{len(self._pending_node_rms)} node rms, "
            f"{len(self._pending_edge_rms)} edge rms"
        )

        # Snapshot the buffers for the executor thread (avoid mutation in flight)
        node_puts = dict(self._pending_node_puts)
        edge_puts = dict(self._pending_edge_puts)
        node_rms = set(self._pending_node_rms)
        edge_rms = set(self._pending_edge_rms)

        def _do_flush() -> None:
            mt = self._client.multi_transact(write=True)
            try:
                # 1. Node upserts (batch via row-vector syntax)
                if node_puts:
                    rows = [[nid, attrs] for nid, attrs in node_puts.items()]
                    mt.run(
                        "?[id, attrs] <- $rows :put nodes {id => attrs}",
                        {"rows": rows},
                    )

                # 2. Edge upserts (batch via row-vector syntax)
                if edge_puts:
                    rows = [[src, tgt, attrs] for (src, tgt), attrs in edge_puts.items()]
                    mt.run(
                        "?[src, tgt, attrs] <- $rows :put edges {src, tgt => attrs}",
                        {"rows": rows},
                    )

                # 3. Node deletes — cascade incident disk edges first
                for node_id in node_rms:
                    # Find incident edges in the DB (within the same transaction)
                    edge_result = mt.run(
                        "?[src, tgt] := *edges{src, tgt}, src = $id or tgt = $id",
                        {"id": node_id},
                    )
                    edge_rows = (
                        edge_result.get("rows", [])
                        if isinstance(edge_result, dict)
                        else edge_result.values.tolist()
                    )
                    for row in edge_rows:
                        mt.run(
                            "?[src, tgt] <- [[$s, $t]] :rm edges {src, tgt}",
                            {"s": row[0], "t": row[1]},
                        )
                    # Delete the node itself
                    mt.run(
                        "?[id] <- [[$id]] :rm nodes {id}",
                        {"id": node_id},
                    )

                # 4. Edge deletes (explicit, e.g. from remove_edges)
                for src, tgt in edge_rms:
                    mt.run(
                        "?[src, tgt] <- [[$s, $t]] :rm edges {src, tgt}",
                        {"s": src, "t": tgt},
                    )

                mt.commit()
            except Exception:
                try:
                    mt.abort()
                except Exception:
                    pass
                raise

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _do_flush)

    def _clear_buffers(self) -> None:
        """Discard all in-process write buffers."""
        self._pending_node_puts.clear()
        self._pending_edge_puts.clear()
        self._pending_node_rms.clear()
        self._pending_edge_rms.clear()

    async def drop_pending_index_ops(self) -> None:
        """Discard the in-process write buffer without touching the database.

        This is the ABORT path (T-01.1-04): called when a batch is failing and
        the buffered records belong to a document that will be re-processed on
        the next run. Clearing the buffer prevents stale/poisoned records from
        being re-flushed.
        """
        self._clear_buffers()
        logger.debug(
            f"[{self.workspace}] drop_pending_index_ops: write buffer discarded"
        )

    async def drop(self) -> dict[str, str]:
        """Clear all data from both relations and return success status.

        Persists immediately (no buffering), notifies other processes.
        """
        try:
            async with self._storage_lock:
                # Clear both relations by removing all rows
                loop = asyncio.get_running_loop()

                def _drop_all():
                    # Remove all rows from edges then nodes
                    self._client.run(
                        "?[src, tgt] := *edges{src, tgt} :rm edges {src, tgt}", {}
                    )
                    self._client.run(
                        "?[id] := *nodes{id} :rm nodes {id}", {}
                    )

                await loop.run_in_executor(None, _drop_all)
                self._clear_buffers()

                await set_all_update_flags(self.namespace, workspace=self.workspace)
                self.storage_updated.value = False

                logger.info(
                    f"[{self.workspace}] drop(): both relations cleared"
                )
            return {"status": "success", "message": "data dropped"}
        except Exception as e:
            logger.error(f"[{self.workspace}] Error dropping Cozo graph: {e}")
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------ #
    # Knowledge-graph BFS (native Datalog)                                #
    # ------------------------------------------------------------------ #

    async def get_knowledge_graph(
        self,
        node_label: str,
        max_depth: int = 3,
        max_nodes: int = None,
    ) -> KnowledgeGraph:
        """Retrieve a connected subgraph via degree-prioritized BFS.

        Mirrors NetworkXStorage's observable output (same node/edge sets,
        same is_truncated logic) but uses Python-side BFS over Cozo-fetched
        adjacency data (avoids complex recursive Datalog translation of the
        degree-sorted BFS algorithm).

        Args:
            node_label: Starting node label.  ``"*"`` = top-by-degree nodes.
            max_depth:  Maximum BFS depth (ignored for ``"*"`` branch).
            max_nodes:  Maximum nodes to return.  Defaults to
                        ``global_config["max_graph_nodes"]`` (1000).

        Returns:
            KnowledgeGraph with nodes, edges, and is_truncated flag.
        """
        if max_nodes is None:
            max_nodes = self.global_config.get("max_graph_nodes", 1000)
        else:
            max_nodes = min(max_nodes, self.global_config.get("max_graph_nodes", 1000))

        result = KnowledgeGraph()

        if node_label == "*":
            # Top-by-degree branch: fetch all nodes and their degrees
            all_labels = await self.get_all_labels()
            if not all_labels:
                return result

            degrees: list[tuple[str, int]] = []
            for nid in all_labels:
                deg = await self.node_degree(nid)
                degrees.append((nid, deg))
            degrees.sort(key=lambda x: x[1], reverse=True)

            if len(degrees) > max_nodes:
                result.is_truncated = True
                logger.info(
                    f"[{self.workspace}] Graph truncated: {len(degrees)} nodes → {max_nodes}"
                )

            selected_nodes = {nid for nid, _ in degrees[:max_nodes]}
            # Collect inter-selected edges
            all_edges = await self.get_all_edges()
            selected_edges = [
                e for e in all_edges
                if e["source"] in selected_nodes and e["target"] in selected_nodes
            ]

            seen_nodes: set[str] = set()
            for nid in [n for n, _ in degrees[:max_nodes]]:
                if nid in seen_nodes:
                    continue
                node_attrs = await self.get_node(nid) or {}
                result.nodes.append(
                    KnowledgeGraphNode(
                        id=nid,
                        labels=[nid],
                        properties=dict(node_attrs),
                    )
                )
                seen_nodes.add(nid)

            seen_edges: set[str] = set()
            for edge in selected_edges:
                src, tgt = edge["source"], edge["target"]
                if src > tgt:
                    src, tgt = tgt, src
                edge_id = f"{src}-{tgt}"
                if edge_id in seen_edges:
                    continue
                edge_props = {k: v for k, v in edge.items() if k not in ("source", "target")}
                result.edges.append(
                    KnowledgeGraphEdge(
                        id=edge_id,
                        type="DIRECTED",
                        source=src,
                        target=tgt,
                        properties=edge_props,
                    )
                )
                seen_edges.add(edge_id)

        else:
            # Labeled BFS branch
            if not await self.has_node(node_label):
                logger.warning(
                    f"[{self.workspace}] Node '{node_label}' not found in graph"
                )
                return KnowledgeGraph()

            # Build in-memory adjacency map for the BFS
            all_edges_list = await self.get_all_edges()
            adjacency: dict[str, list[str]] = {}
            for edge in all_edges_list:
                src, tgt = edge["source"], edge["target"]
                adjacency.setdefault(src, []).append(tgt)
                adjacency.setdefault(tgt, []).append(src)

            # Degree-prioritised BFS (mirrors NetworkXStorage algorithm exactly)
            bfs_nodes: list[str] = []
            visited: set[str] = set()

            start_deg = len(adjacency.get(node_label, []))
            queue: deque[tuple[str, int, int]] = deque(
                [(node_label, 0, start_deg)]
            )

            has_unexplored_neighbors = False

            while queue and len(bfs_nodes) < max_nodes:
                current_depth = queue[0][1]

                # Collect all nodes at this depth level
                current_level: list[tuple[str, int, int]] = []
                while queue and queue[0][1] == current_depth:
                    current_level.append(queue.popleft())

                # Sort by degree descending
                current_level.sort(key=lambda x: x[2], reverse=True)

                for current_node, depth, _deg in current_level:
                    if current_node not in visited:
                        visited.add(current_node)
                        bfs_nodes.append(current_node)

                        if depth < max_depth:
                            neighbors = adjacency.get(current_node, [])
                            unvisited = [n for n in neighbors if n not in visited]
                            for neighbor in unvisited:
                                nbr_deg = len(adjacency.get(neighbor, []))
                                queue.append((neighbor, depth + 1, nbr_deg))
                        else:
                            neighbors = adjacency.get(current_node, [])
                            unvisited = [n for n in neighbors if n not in visited]
                            if unvisited:
                                has_unexplored_neighbors = True

                    if len(bfs_nodes) >= max_nodes:
                        break

            if (queue and len(bfs_nodes) >= max_nodes) or has_unexplored_neighbors:
                if len(bfs_nodes) >= max_nodes:
                    result.is_truncated = True
                    logger.info(
                        f"[{self.workspace}] BFS truncated at max_nodes={max_nodes}"
                    )
                else:
                    logger.info(
                        f"[{self.workspace}] BFS reached max_depth={max_depth} "
                        f"with {len(bfs_nodes)} nodes"
                    )

            bfs_set = set(bfs_nodes)

            seen_nodes: set[str] = set()
            for nid in bfs_nodes:
                if nid in seen_nodes:
                    continue
                node_attrs = await self.get_node(nid) or {}
                result.nodes.append(
                    KnowledgeGraphNode(
                        id=nid,
                        labels=[nid],
                        properties=dict(node_attrs),
                    )
                )
                seen_nodes.add(nid)

            seen_edges: set[str] = set()
            for edge in all_edges_list:
                src, tgt = edge["source"], edge["target"]
                if src not in bfs_set or tgt not in bfs_set:
                    continue
                if src > tgt:
                    src, tgt = tgt, src
                edge_id = f"{src}-{tgt}"
                if edge_id in seen_edges:
                    continue
                edge_props = {k: v for k, v in edge.items() if k not in ("source", "target")}
                result.edges.append(
                    KnowledgeGraphEdge(
                        id=edge_id,
                        type="DIRECTED",
                        source=src,
                        target=tgt,
                        properties=edge_props,
                    )
                )
                seen_edges.add(edge_id)

        logger.info(
            f"[{self.workspace}] get_knowledge_graph('{node_label}'): "
            f"{len(result.nodes)} nodes, {len(result.edges)} edges"
        )
        return result
