"""Embedded Cozo graph store, ported by deliberate copy — never import — from v1's
``CozoGraphStorage`` (upstream_ref: v1/lightrag/kg/cozo_impl.py). D-14 keeps this package's import
boundary intact: nothing here imports from v1's ``lightrag`` package, and nothing here reproduces
v1's process-wide ``shared_storage`` locking singleton (D-11's rejected anti-analog). In one
process, every instance on one resolved ``graph.cozo`` path shares one reference-counted pycozo
``Client`` (``_ClientRegistry``, Phase 10 D-01); each instance keeps its own pending buffers, flushes
on one path are serialized, and the last release closes the client. An open that cannot share (the
path held by another OS process) raises ``GraphStoreBusyError``. In-process only, matching
EMBED-01's no-external-server claim.

Cozo 0.7.6 (pinned exactly in ``pyproject.toml``) is architecture-frozen: it ships five known
correctness bugs with no upstream fix expected. The query-shape constraints below are permanent
mitigations, not temporary workarounds — see
``databasise/tests/stores/test_graph_frozen_bugs.py`` for the non-skippable regression suite that
binds them to this adapter, not merely to the original v1 class:
    #244    aggregation returning zero rows silently -> never use count() aggregation
    #296/#269  UUID sort/coercion                    -> store every key as String, never UUID
    #253    JSON key-order loss                       -> consume Json columns as dict, never rely
                                                          on key order
    #275    wrong DataValue types on round-trip        -> assert types explicitly on every read
    (no #)  starts_with on a key column becomes a key-range scan with an exclusive lower bound, so
            the key equal to the prefix is dropped     -> bind it first: ``x = id, starts_with(x, $p)``
            (stores/probes.py ``graph_node_page``; regression in tests/stores/test_graph_read_review_c.py)

Deferred-write contract, reproduced from the v1 docstring verbatim as a design constraint (not
merely as prose): Cozo commits each ``:put``/``:rm`` immediately in its own transaction, but this
adapter buffers writes in-memory and flushes them at ``index_done_callback``. Four in-process
buffers:
    _pending_node_puts  : dict[id, attrs]
    _pending_edge_puts  : dict[(src, tgt), attrs]   # canonical order
    _pending_node_rms   : set[id]
    _pending_edge_rms   : set[(src, tgt)]           # canonical order
Reads consult these buffers FIRST (read-your-writes before flush). All four are cleared on
``index_done_callback`` (commit) or ``drop_pending_index_ops`` (abort).

Edges stay consistent with nodes (Phase 10 D-10, matching v1's cascade and networkx): ``delete_node``
drops the node's buffered edges at once, marks its disk edges removed, and the flush cascades
``:rm edges`` before ``:rm nodes`` in the same transaction; ``upsert_edge`` creates a missing
endpoint with ``{}`` attributes. No path leaves a dangling edge.

``pycozo``'s ``Client.run()`` is synchronous; every call is dispatched via
``asyncio.get_running_loop().run_in_executor(None, ...)`` so it never blocks the runner's event
loop — plan 01-08's structured-concurrency plan depends on this.

Every node id, edge endpoint, and query value is a bound parameter, never interpolated into
CozoScript — entity names arriving from an LLM extraction path routinely contain Datalog
metacharacters (``{``, ``}``, ``?``, ``*``), and interpolation would let those alter query
structure.

One Cozo database file lives inside this store's own namespace directory
(``<store_root>/<workspace>/<namespace>/graph.cozo``), matching D-07's one-directory-per-namespace
layout — the same layout ``stores/kv.py`` already established in plan 01-02.

Forward-compatibility (Phase 6, deferred fact layer): the two stored relations below carry only
``id``/``src``/``tgt``/``attrs`` columns today, shaped so an additive ``Validity``-typed key column
can be introduced later without a schema migration of existing rows. Phase 1 does not build the
recovered fact layer — see ``.planning/RECOVERED-FACT-LAYER.md`` — but D-05/D-07 must not
foreclose it.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import threading
from collections.abc import Collection
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from databasise.stores.base import StorageNameSpace

try:
    from pycozo.client import Client as CozoClient
except ImportError as _cozo_import_err:
    raise ImportError(
        "cozo-embedded is required for CozoGraphStore. "
        "Install with: pip install 'pycozo[embedded]'"
    ) from _cozo_import_err


def _cozo_rows(result: Any) -> list[list]:
    """Normalise a ``pycozo`` ``run()`` result to ``list[list]`` across both shapes 0.7.6
    returns: a plain dict ``{"headers": [...], "rows": [...]}`` when pandas is not importable, or
    a pandas DataFrame when it is. Ported by copy from ``v1/lightrag/kg/cozo_impl.py``.
    """
    if hasattr(result, "to_dict"):
        return result.values.tolist()
    return result.get("rows", [])


def _canonical_edge_key(src: str, tgt: str) -> tuple[str, str]:
    """(src, tgt) lexicographically ordered so A-B and B-A resolve to the same key. Ported by
    copy from ``v1/lightrag/kg/cozo_impl.py``.
    """
    if src > tgt:
        return tgt, src
    return src, tgt


def _attrs_to_dict(raw: Any) -> dict[str, Any]:
    """Coerce a Cozo ``Json`` column value to a plain dict, whether pycozo returned it already
    parsed or as a JSON string — consumed as a dict, never by relying on key order (frozen-bug
    #253's mitigation).
    """
    if isinstance(raw, dict):
        return dict(raw)
    return json.loads(raw)


class GraphStoreBusyError(RuntimeError):
    """Raised at open time (Phase 10 D-01) when RocksDB refuses the ``graph.cozo`` lock: the path is
    held by another OS process, or by an open that cannot share the registry's client. The message is
    fixed and never carries the path (RocksDB's own lock text embeds it); the engine translates this
    into the seam's ``StoreBusyError``.
    """

    def __init__(self) -> None:
        super().__init__(
            "graph store is held by another process or by an open that cannot share it; "
            "retry once it is released"
        )


def _is_lock_error(exc: BaseException) -> bool:
    """RocksDB's two verified lock-refusal texts (10-RESEARCH R7 same process, R8 other process)."""
    text = str(exc.args[0]) if exc.args else str(exc)
    return "kIOError" in text and ("lock hold by current process" in text or "While lock file" in text)


@dataclass
class _SharedClient:
    client: Any
    refcount: int = 1
    flush_lock: threading.Lock = field(default_factory=threading.Lock)


class _ClientRegistry:
    """One pycozo ``Client`` per resolved ``graph.cozo`` path, reference-counted (D-01). The dict and
    every refcount change only under ``_lock``, so threads (a REST worker, the test loop) can acquire
    the same path concurrently without a double open."""

    _entries: dict[str, _SharedClient] = {}
    _lock = threading.Lock()

    @classmethod
    def acquire(cls, db_path: str | Path) -> tuple[str, _SharedClient]:
        key = str(Path(db_path).resolve())
        with cls._lock:
            entry = cls._entries.get(key)
            if entry is not None:
                entry.refcount += 1
                return key, entry
            try:
                client = CozoClient("rocksdb", key, dataframe=False)
            except Exception as exc:
                if _is_lock_error(exc):
                    raise GraphStoreBusyError() from exc
                raise
            entry = cls._entries[key] = _SharedClient(client=client)
            return key, entry

    @classmethod
    def release(cls, key: str) -> None:
        with cls._lock:
            entry = cls._entries.get(key)
            if entry is None:
                return
            entry.refcount -= 1
            if entry.refcount > 0:
                return
            del cls._entries[key]
            # Phase 10 review WR-01: closed under the lock, so a concurrent acquire of this path waits
            # for RocksDB to drop its LOCK file instead of opening a second client and reading the
            # still-held lock as "busy".
            entry.client.close()


def held_graph_paths(prefix: str, own: Collection[str] = ()) -> list[str]:
    """Sorted resolved paths of the graph clients this process holds under ``prefix`` (16-10, D-17).
    A snapshot of in-process holders only: it opens no client, takes no lock, and cannot see another
    process. ``list()`` copies the entries in one step, so a concurrent acquire or release is harmless.
    ``own`` is the caller's own long-lived references, one per key: a key in it is listed only while
    something else holds it too (16-REVIEW-C WR-01, the operator engine's held graph client)."""
    return sorted(
        key
        for key, entry in list(_ClientRegistry._entries.items())
        if key.startswith(prefix) and entry.refcount > (key in own)
    )


class CozoGraphStore(StorageNameSpace):
    """Embedded Cozo (RocksDB) graph store, one database file per namespace directory."""

    upstream_ref = "v1/lightrag/kg/cozo_impl.py"

    def __init__(self, namespace: str, workspace: str, store_root: str | Path) -> None:
        super().__init__(namespace=namespace, workspace=workspace)
        self._dir = Path(store_root) / workspace / namespace
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._dir / "graph.cozo"
        self._registry_key, self._shared = _ClientRegistry.acquire(self._db_path)
        self._client = self._shared.client
        self._released = False
        self._prepared_mt: Any = None
        try:
            self._ensure_relations()
        except BaseException:
            self._release()
            raise

        self._pending_node_puts: dict[str, dict[str, Any]] = {}
        self._pending_edge_puts: dict[tuple[str, str], dict[str, Any]] = {}
        self._pending_node_rms: set[str] = set()
        self._pending_edge_rms: set[tuple[str, str]] = set()

    def _ensure_relations(self) -> None:
        """Create the two stored relations if absent (idempotent across reopens). Keys are typed
        ``String``, never ``UUID`` — frozen-bug #296/#269's mitigation.
        """
        for script in (
            ":create nodes {id: String => attrs: Json}",
            ":create edges {src: String, tgt: String => attrs: Json}",
        ):
            try:
                self._client.run(script, {})
            except Exception as exc:
                # Idempotent :create on reopen. Cozo's actual re-create message is "Stored
                # relation <name> conflicts with an existing one" (observed via pycozo's
                # QueryException, not "already exists") — narrowed to that exact phrase rather
                # than a bare "relation" substring, which previously also swallowed unrelated
                # errors (a malformed schema, a corrupted RocksDB file, a permissions error)
                # that happen to mention "relation" at all (WR-01).
                message = str(exc).lower()
                if "already exists" not in message and "conflicts with an existing" not in message:
                    raise

    async def _run(self, script: str, params: dict[str, Any] | None = None) -> list[list]:
        """Dispatch a synchronous ``pycozo`` call off the event loop and normalise its result."""
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: self._client.run(script, params or {}))
        return _cozo_rows(result)

    # ------------------------------------------------------------------ #
    # Reads — buffer consulted first (read-your-writes before flush)      #
    # ------------------------------------------------------------------ #

    def _edge_hidden(self, key: tuple[str, str]) -> bool:
        """A disk edge is hidden once removed, or once either endpoint is pending removal (D-10)."""
        return (
            key in self._pending_edge_rms
            or key[0] in self._pending_node_rms
            or key[1] in self._pending_node_rms
        )

    async def has_node(self, node_id: str) -> bool:
        if node_id in self._pending_node_rms:
            return False
        if node_id in self._pending_node_puts:
            return True
        rows = await self._run("?[id] := *nodes{id}, id = $id", {"id": node_id})
        return len(rows) > 0

    async def get_node(self, node_id: str) -> dict[str, Any] | None:
        if node_id in self._pending_node_rms:
            return None
        if node_id in self._pending_node_puts:
            return dict(self._pending_node_puts[node_id])
        rows = await self._run("?[attrs] := *nodes{id, attrs}, id = $id", {"id": node_id})
        if not rows:
            return None
        return _attrs_to_dict(rows[0][0])

    async def has_edge(self, source_node_id: str, target_node_id: str) -> bool:
        key = _canonical_edge_key(source_node_id, target_node_id)
        if self._edge_hidden(key):
            return False
        if key in self._pending_edge_puts:
            return True
        rows = await self._run(
            "?[src, tgt] := *edges{src, tgt}, src = $src, tgt = $tgt",
            {"src": key[0], "tgt": key[1]},
        )
        return len(rows) > 0

    async def get_edge(self, source_node_id: str, target_node_id: str) -> dict[str, Any] | None:
        key = _canonical_edge_key(source_node_id, target_node_id)
        if self._edge_hidden(key):
            return None
        if key in self._pending_edge_puts:
            return dict(self._pending_edge_puts[key])
        rows = await self._run(
            "?[attrs] := *edges{src, tgt, attrs}, src = $src, tgt = $tgt",
            {"src": key[0], "tgt": key[1]},
        )
        if not rows:
            return None
        return _attrs_to_dict(rows[0][0])

    async def node_degree(self, node_id: str) -> int:
        """Count undirected incident edges from disk + buffer. Avoids ``count()`` aggregation
        (frozen-bug #244's mitigation) by fetching rows and taking ``len()`` in Python.
        """
        db_rows = await self._run(
            "?[src, tgt] := *edges{src, tgt}, src = $id or tgt = $id", {"id": node_id}
        )
        db_keys = {_canonical_edge_key(r[0], r[1]) for r in db_rows}
        effective = {k for k in db_keys if not self._edge_hidden(k)} | {
            k for k in self._pending_edge_puts if node_id in k
        }
        return len(effective)

    async def get_node_edges(self, node_id: str) -> list[dict[str, Any]]:
        """Every edge incident on ``node_id``, either direction, as ``{"src", "tgt", "attrs"}``
        dicts — ``src``/``tgt`` already in canonical order (every write path canonicalises via
        ``_canonical_edge_key`` before storing, so no re-canonicalisation is needed here). Extends
        ``node_degree``'s own non-aggregating query shape (frozen-bug #244's mitigation) to also
        project ``attrs``, rather than introducing a second aggregation-shaped query for the same
        underlying scan. Buffer consulted the same way ``node_degree`` computes its effective set:
        a pending put for a key touching ``node_id`` overrides (or adds) that edge's attrs; a
        pending removal drops it. An unknown or edge-free node returns ``[]``, never raises.
        """
        db_rows = await self._run(
            "?[src, tgt, attrs] := *edges{src, tgt, attrs}, src = $id or tgt = $id", {"id": node_id}
        )
        effective: dict[tuple[str, str], dict[str, Any]] = {
            (r[0], r[1]): _attrs_to_dict(r[2])
            for r in db_rows
            if not self._edge_hidden((r[0], r[1]))
        }
        for key, attrs in self._pending_edge_puts.items():
            if node_id in key:
                effective[key] = dict(attrs)
        return [{"src": src, "tgt": tgt, "attrs": attrs} for (src, tgt), attrs in effective.items()]

    async def export_to_igraph(self, *, weight_attr: str = "weight") -> "igraph.Graph":  # noqa: F821 — quoted forward ref, resolved by the function-scoped import below
        """§14.2's Graph bulk-export sub-capability (06-01-PLAN.md): the whole graph as one
        undirected ``igraph.Graph``, built from exactly two Cozo queries — one for the node
        relation, one for the edge relation — never a pointwise per-node/per-edge loop. Mirrors
        05-06's lazy-optional-import discipline: ``igraph`` is imported function-scoped so a
        machine that never dispatches a bulk-export-consuming node (every wiring but HippoRAG's)
        never pays the import cost.

        Consults the pending write buffers first, exactly as ``get_node``/``get_node_edges`` do
        (read-your-writes before flush), so a graph written earlier in this same run and not yet
        flushed is exported. Builds the vertex-name-to-dense-index map once, sets ``vs["name"]``
        to the stored node ids and ``es["weight"]`` to each edge's own ``weight_attr`` value
        (default ``1.0`` when an edge's stored ``attrs`` carries no ``weight_attr`` key — the
        edge is kept, never dropped, per PARTS.md ``## §H``'s "single ``weight`` edge attribute
        collapsing all three edge types" clause). Cites CONTRACT.md §14.2's bulk-export row.
        """
        import igraph

        node_rows = await self._run("?[id] := *nodes{id}", {})
        db_ids = {r[0] for r in node_rows}
        effective_ids = (db_ids - self._pending_node_rms) | set(self._pending_node_puts.keys())

        edge_rows = await self._run("?[src, tgt, attrs] := *edges{src, tgt, attrs}", {})
        effective_edges: dict[tuple[str, str], dict[str, Any]] = {
            (r[0], r[1]): _attrs_to_dict(r[2])
            for r in edge_rows
            if not self._edge_hidden((r[0], r[1]))
        }
        for key, attrs in self._pending_edge_puts.items():
            effective_edges[key] = dict(attrs)

        vertex_names = sorted(effective_ids)
        index_by_id = {node_id: i for i, node_id in enumerate(vertex_names)}

        edge_pairs: list[tuple[int, int]] = []
        weights: list[float] = []
        for (src, tgt), attrs in effective_edges.items():
            if src not in index_by_id or tgt not in index_by_id:
                # An edge endpoint absent from the node relation (a data inconsistency this
                # store's own write paths should never produce) — skipped rather than raising,
                # since a bulk export has no per-edge caller to refuse to.
                continue
            edge_pairs.append((index_by_id[src], index_by_id[tgt]))
            weights.append(float(attrs.get(weight_attr, 1.0)))

        graph = igraph.Graph(n=len(vertex_names), edges=edge_pairs, directed=False)
        graph.vs["name"] = vertex_names
        graph.es["weight"] = weights
        return graph

    async def get_all_labels(self) -> list[str]:
        """All node ids, disk + buffer, sorted. Avoids ``count()`` aggregation (frozen-bug #244)."""
        rows = await self._run("?[id] := *nodes{id}", {})
        db_ids = {r[0] for r in rows}
        effective = (db_ids - self._pending_node_rms) | set(self._pending_node_puts.keys())
        return sorted(effective)

    # ------------------------------------------------------------------ #
    # Writes — buffered, flushed at index_done_callback                    #
    # ------------------------------------------------------------------ #

    async def upsert_node(self, node_id: str, node_data: dict[str, Any]) -> None:
        self._pending_node_rms.discard(node_id)
        self._pending_node_puts[node_id] = dict(node_data)

    async def upsert_edge(
        self, source_node_id: str, target_node_id: str, edge_data: dict[str, Any]
    ) -> None:
        for endpoint in (source_node_id, target_node_id):
            if not await self.has_node(endpoint):  # a pending put answers without a query
                await self.upsert_node(endpoint, {})
        key = _canonical_edge_key(source_node_id, target_node_id)
        self._pending_edge_rms.discard(key)
        self._pending_edge_puts[key] = dict(edge_data)

    async def delete_node(self, node_id: str) -> None:
        self._pending_node_puts.pop(node_id, None)
        self._pending_node_rms.add(node_id)
        for key in [k for k in self._pending_edge_puts if node_id in k]:
            del self._pending_edge_puts[key]
        # Mark the disk edges removed too, so re-creating the node does not bring them back.
        db_rows = await self._run(
            "?[src, tgt] := *edges{src, tgt}, src = $id or tgt = $id", {"id": node_id}
        )
        self._pending_edge_rms.update((r[0], r[1]) for r in db_rows)

    async def delete_edge(self, source_node_id: str, target_node_id: str) -> None:
        key = _canonical_edge_key(source_node_id, target_node_id)
        self._pending_edge_puts.pop(key, None)
        self._pending_edge_rms.add(key)

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    def _has_pending(self) -> bool:
        return bool(
            self._pending_node_puts
            or self._pending_edge_puts
            or self._pending_node_rms
            or self._pending_edge_rms
        )

    def _snapshot(self) -> tuple[Any, ...]:
        """Copies of the four buffers, taken on the loop thread before an executor call."""
        return (
            dict(self._pending_node_puts),
            dict(self._pending_edge_puts),
            set(self._pending_node_rms),
            set(self._pending_edge_rms),
        )

    def _stage(self, snapshot: tuple[Any, ...]) -> Any:
        """Open a write ``multi_transact`` and run every buffered statement in it, uncommitted
        (research R3: invisible to plain ``run()`` until commit). Aborts and re-raises on error."""
        node_puts, edge_puts, node_rms, edge_rms = snapshot
        mt = self._client.multi_transact(write=True)
        try:
            if node_puts:
                rows = [[nid, attrs] for nid, attrs in node_puts.items()]
                mt.run("?[id, attrs] <- $rows :put nodes {id => attrs}", {"rows": rows})
            if edge_puts:
                rows = [[src, tgt, attrs] for (src, tgt), attrs in edge_puts.items()]
                mt.run(
                    "?[src, tgt, attrs] <- $rows :put edges {src, tgt => attrs}",
                    {"rows": rows},
                )
            for node_id in node_rms:
                mt.run(  # D-10 cascade (research R9): incident edges go in the same transaction
                    "?[src, tgt] := *edges{src, tgt}, src = $id or tgt = $id :rm edges {src, tgt}",
                    {"id": node_id},
                )
                mt.run("?[id] <- [[$id]] :rm nodes {id}", {"id": node_id})
            for src, tgt in edge_rms:
                mt.run("?[src, tgt] <- [[$s, $t]] :rm edges {src, tgt}", {"s": src, "t": tgt})
        except Exception:
            with contextlib.suppress(Exception):
                mt.abort()
            raise
        return mt

    @staticmethod
    def _commit_or_abort(mt: Any) -> None:
        """Commit a staged transaction exactly once; a failed commit is aborted (research R10)."""
        try:
            mt.commit()
        except Exception:
            with contextlib.suppress(Exception):
                mt.abort()
            raise

    def _clear_pending(self) -> None:
        self._pending_node_puts.clear()
        self._pending_edge_puts.clear()
        self._pending_node_rms.clear()
        self._pending_edge_rms.clear()

    async def prepare(self) -> None:
        """D-07: stage the buffers in an open ``multi_transact``. It holds per-key locks (R6) until
        ``commit_prepared`` or ``abort_prepared``, so the engine serializes this window."""
        if not self._has_pending():
            return
        loop = asyncio.get_running_loop()
        self._prepared_mt = await loop.run_in_executor(None, self._stage, self._snapshot())

    async def commit_prepared(self) -> None:
        mt, self._prepared_mt = self._prepared_mt, None
        if mt is not None:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._commit_or_abort, mt)  # R4: any thread may commit
        self._clear_pending()

    async def abort_prepared(self) -> None:
        mt, self._prepared_mt = self._prepared_mt, None
        if mt is not None:
            loop = asyncio.get_running_loop()
            with contextlib.suppress(Exception):
                await loop.run_in_executor(None, mt.abort)
        self._clear_pending()

    async def index_done_callback(self) -> None:
        """Flush all four buffers to Cozo in one atomic ``multi_transact``, off-loop, under the
        path's flush lock (direct users; the engine uses prepare/commit under its own lock)."""
        if not self._has_pending():
            return
        snapshot = self._snapshot()

        def _do_flush() -> None:
            with self._shared.flush_lock:
                self._commit_or_abort(self._stage(snapshot))

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _do_flush)
        self._clear_pending()

    async def drop_pending_index_ops(self) -> None:
        await self.abort_prepared()

    async def drop(self) -> dict[str, str]:
        try:
            loop = asyncio.get_running_loop()

            def _drop_all() -> None:
                self._client.run("?[src, tgt] := *edges{src, tgt} :rm edges {src, tgt}", {})
                self._client.run("?[id] := *nodes{id} :rm nodes {id}", {})

            await loop.run_in_executor(None, _drop_all)
            await self.drop_pending_index_ops()
            return {"status": "success", "message": "data dropped"}
        except Exception as exc:  # noqa: BLE001 — drop()'s own documented contract (v1 StorageNameSpace)
            return {"status": "error", "message": str(exc)}

    def _release(self) -> None:
        if self._released:
            return
        self._released = True
        _ClientRegistry.release(self._registry_key)

    async def finalize(self) -> None:
        """Release this instance's client reference once; idempotent (an engine ``finally`` may run
        after a partial construction). The last release closes the shared client. A still-open
        prepared transaction is aborted first: the client must not close under one (research R10)."""
        if self._released:
            return
        self._released = True  # set on the loop thread, so two concurrent finalizes release once
        loop = asyncio.get_running_loop()
        try:
            mt, self._prepared_mt = self._prepared_mt, None
            if mt is not None:
                with contextlib.suppress(Exception):
                    await loop.run_in_executor(None, mt.abort)
        finally:
            await loop.run_in_executor(None, _ClientRegistry.release, self._registry_key)
