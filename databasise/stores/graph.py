"""Embedded Cozo graph store, ported by deliberate copy — never import — from v1's
``CozoGraphStorage`` (upstream_ref: v1/lightrag/kg/cozo_impl.py). D-14 keeps this package's import
boundary intact: nothing here imports from v1's ``lightrag`` package, and nothing here reproduces
v1's process-wide ``shared_storage`` locking singleton (D-11's rejected anti-analog) — this store
is single-writer, single-process, in-process only, matching EMBED-01's no-external-server claim.

Cozo 0.7.6 (pinned exactly in ``pyproject.toml``) is architecture-frozen: it ships four known
correctness bugs with no upstream fix expected. The query-shape constraints below are permanent
mitigations, not temporary workarounds — see
``databasise/tests/stores/test_graph_frozen_bugs.py`` for the non-skippable regression suite that
binds them to this adapter, not merely to the original v1 class:
    #244    aggregation returning zero rows silently -> never use count() aggregation
    #296/#269  UUID sort/coercion                    -> store every key as String, never UUID
    #253    JSON key-order loss                       -> consume Json columns as dict, never rely
                                                          on key order
    #275    wrong DataValue types on round-trip        -> assert types explicitly on every read

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


class CozoGraphStore(StorageNameSpace):
    """Embedded Cozo (RocksDB) graph store, one database file per namespace directory."""

    upstream_ref = "v1/lightrag/kg/cozo_impl.py"

    def __init__(self, namespace: str, workspace: str, store_root: str | Path) -> None:
        super().__init__(namespace=namespace, workspace=workspace)
        self._dir = Path(store_root) / workspace / namespace
        self._dir.mkdir(parents=True, exist_ok=True)
        self._db_path = self._dir / "graph.cozo"
        self._client = CozoClient("rocksdb", str(self._db_path))
        self._ensure_relations()

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
        if key in self._pending_edge_rms:
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
        if key in self._pending_edge_rms:
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
        effective = (db_keys - self._pending_edge_rms) | {
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
            (r[0], r[1]): _attrs_to_dict(r[2]) for r in db_rows
        }
        for key in self._pending_edge_rms:
            effective.pop(key, None)
        for key, attrs in self._pending_edge_puts.items():
            if node_id in key:
                effective[key] = dict(attrs)
        return [{"src": src, "tgt": tgt, "attrs": attrs} for (src, tgt), attrs in effective.items()]

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
        key = _canonical_edge_key(source_node_id, target_node_id)
        self._pending_edge_rms.discard(key)
        self._pending_edge_puts[key] = dict(edge_data)

    async def delete_node(self, node_id: str) -> None:
        self._pending_node_puts.pop(node_id, None)
        self._pending_node_rms.add(node_id)

    async def delete_edge(self, source_node_id: str, target_node_id: str) -> None:
        key = _canonical_edge_key(source_node_id, target_node_id)
        self._pending_edge_puts.pop(key, None)
        self._pending_edge_rms.add(key)

    # ------------------------------------------------------------------ #
    # Lifecycle                                                            #
    # ------------------------------------------------------------------ #

    async def index_done_callback(self) -> None:
        """Flush all four buffers to Cozo in one atomic ``multi_transact``, off-loop."""
        if not (
            self._pending_node_puts
            or self._pending_edge_puts
            or self._pending_node_rms
            or self._pending_edge_rms
        ):
            return

        node_puts = dict(self._pending_node_puts)
        edge_puts = dict(self._pending_edge_puts)
        node_rms = set(self._pending_node_rms)
        edge_rms = set(self._pending_edge_rms)

        def _do_flush() -> None:
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
                    mt.run("?[id] <- [[$id]] :rm nodes {id}", {"id": node_id})
                for src, tgt in edge_rms:
                    mt.run("?[src, tgt] <- [[$s, $t]] :rm edges {src, tgt}", {"s": src, "t": tgt})
                mt.commit()
            except Exception:
                with contextlib.suppress(Exception):
                    mt.abort()
                raise

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _do_flush)

        self._pending_node_puts.clear()
        self._pending_edge_puts.clear()
        self._pending_node_rms.clear()
        self._pending_edge_rms.clear()

    async def drop_pending_index_ops(self) -> None:
        self._pending_node_puts.clear()
        self._pending_edge_puts.clear()
        self._pending_node_rms.clear()
        self._pending_edge_rms.clear()

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

    async def finalize(self) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._client.close)
