"""Read-only store probes for ``Databasise.health()`` (Phase 10 D-14, STOR-04). Each probe takes one
namespace directory and returns ``"ok"``, ``"absent"``, ``"corrupted"`` or ``"busy"``. A probe
creates nothing and never raises for a store state (a programming error still surfaces). A
``graph.cozo`` that is not a Cozo RocksDB database (no ``manifest`` file, or no ``data/CURRENT``
naming an existing manifest) is ``corrupted`` and is never opened.

Two measurements (10-07 planning, 10-review iteration 2) shape the probes:
- sqlite: on a WAL ``kv.sqlite3``, ``?mode=ro`` leaves ``kv.sqlite3-wal`` and ``kv.sqlite3-shm``
  behind (and creates a missing ``-shm``), and ``?mode=ro&immutable=1`` creates nothing, so the kv
  probe is always immutable.
- Cozo: opening a missing ``graph.cozo`` creates it, so the probe checks existence first. Opening a
  complete one rotates RocksDB's own files inside ``graph.cozo/data/`` and nothing outside it; the
  one file Cozo keeps outside ``data/`` is ``manifest``, which the marker check requires.
  ``::relations`` run immutable adds no relation, and ``_ensure_relations`` is never called.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Literal

from databasise.stores.graph import GraphStoreBusyError, _attrs_to_dict, _ClientRegistry, _cozo_rows
from databasise.stores.vector import VectorStoreCorruptedError, load_committed

ProbeState = Literal["ok", "absent", "corrupted", "busy"]


def _is_store_error(exc: Exception) -> bool:
    """The failures a probe reports as ``corrupted``: sqlite, OS (``PermissionError`` included),
    value/runtime errors from the readers, and pycozo's native layer, which raises a bare
    ``Exception`` or its own ``QueryException``. Anything else (``AttributeError``, ``TypeError``,
    ...) is a programming error and surfaces."""
    return (
        isinstance(exc, (OSError, sqlite3.Error, ValueError, RuntimeError, KeyError))
        or type(exc) is Exception
        or type(exc).__module__.startswith("pycozo")
    )


def probe_kv(dir_path: Path) -> ProbeState:
    # resolve(): as_uri() raises ValueError for a relative path (iteration-2 WR-02)
    db_path = (Path(dir_path) / "kv.sqlite3").resolve()
    try:
        if not db_path.is_file():
            return "absent"
    except OSError:  # an unreadable namespace directory (mode 000): is_file() lets EACCES through
        return "corrupted"
    try:
        if db_path.stat().st_size == 0:
            return "absent"  # a valid empty database: SqliteKVStore creates its table on first open
    except OSError:
        return "corrupted"
    # Always immutable (iteration-2 WR-03): plain ``mode=ro`` on a WAL database creates ``-shm`` when
    # it is missing (a backup, or a crash leftover with a ``-wal`` but no ``-shm``). The probe only
    # checks that the file opens and the schema reads, so stale WAL content is acceptable.
    uri = db_path.as_uri() + "?mode=ro&immutable=1"
    conn = None
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=0.1)
        conn.execute("SELECT 1 FROM kv LIMIT 1").fetchall()
        return "ok"
    except sqlite3.OperationalError as exc:
        message = str(exc).lower()
        if "no such table" in message and db_path.with_name("kv.sqlite3-wal").exists():
            return "ok"  # a live writer's CREATE TABLE is still in the WAL, which immutable ignores
        return "busy" if "locked" in message else "corrupted"
    except (sqlite3.Error, OSError):
        return "corrupted"
    finally:
        if conn is not None:
            conn.close()


def _rocksdb_marker_present(db_path: Path) -> bool:
    """True when ``db_path`` is a directory holding a Cozo RocksDB database: Cozo's own ``manifest``
    file (the one marker it writes outside ``data/``) exists and ``data/CURRENT`` names a
    ``MANIFEST-*`` file that exists. Opening anything else would create files, ``manifest`` included
    (iteration-2 WR-03)."""
    try:
        if not (db_path / "manifest").is_file():
            return False
        name = (db_path / "data" / "CURRENT").read_text(encoding="utf-8").strip()
        return name.startswith("MANIFEST-") and (db_path / "data" / name).is_file()
    except (OSError, ValueError):
        return False


def probe_graph(dir_path: Path) -> ProbeState:
    db_path = Path(dir_path) / "graph.cozo"
    try:
        if not db_path.exists():
            return "absent"
    except OSError:  # an unreadable namespace directory (mode 000)
        return "corrupted"
    key = str(db_path.resolve())
    # Phase 10 review WR-07: never open a client on a directory that is not a RocksDB database (an
    # empty one, or one a first open died in): RocksDB would create its files there and the probe
    # would report ok. Checked under the registry lock so a first open in progress is not misread.
    with _ClientRegistry._lock:
        if key not in _ClientRegistry._entries and not _rocksdb_marker_present(db_path):
            return "corrupted"
    try:
        key, shared = _ClientRegistry.acquire(db_path)
    except GraphStoreBusyError:
        return "busy"
    except Exception as exc:
        if not _is_store_error(exc):
            raise
        return "corrupted"
    try:
        shared.client.run("::relations", {}, True)
        return "ok"
    except Exception as exc:
        if not _is_store_error(exc):
            raise
        return "corrupted"
    finally:
        _ClientRegistry.release(key)


class GraphStoreCorruptedError(RuntimeError):
    """``graph.cozo`` exists but is not a Cozo RocksDB database; the engine maps it to StoreCorrupted."""


def _run_immutable(client: Any, script: str, params: dict[str, Any]) -> list[list]:
    """The one query seam of the graph read path: an immutable run, rows normalised. Tests spy here."""
    return _cozo_rows(client.run(script, params, True))


def _has_graph_relations(client: Any) -> bool:
    """False for a RocksDB database whose ``nodes``/``edges`` relations were never created (a crash
    between the client open and ``_ensure_relations``). That graph reads as empty, matching
    :func:`probe_graph`'s ``ok``; nothing is created (Phase 16 review C WR-02)."""
    return {"nodes", "edges"} <= {r[0] for r in _run_immutable(client, "::relations", {})}


def acquire_graph(dir_path: Path) -> tuple[str, Any] | None:
    """One :class:`_ClientRegistry` reference to ``dir_path``'s graph, opened as :func:`probe_graph`
    opens it: ``None`` for a missing ``graph.cozo`` (nothing is created), :class:`GraphStoreCorruptedError`
    for a directory without the RocksDB marker (never opened), ``GraphStoreBusyError`` for a held graph.
    The caller releases the returned key."""
    db_path = Path(dir_path) / "graph.cozo"
    if not db_path.exists():
        return None
    key = str(db_path.resolve())
    with _ClientRegistry._lock:
        if key not in _ClientRegistry._entries and not _rocksdb_marker_present(db_path):
            raise GraphStoreCorruptedError("graph.cozo is not a Cozo RocksDB database")
    return _ClientRegistry.acquire(db_path)


def graph_node_page(
    dir_path: Path, prefix: str, limit: int, offset: int
) -> tuple[list[tuple[str, int]], int]:
    """Phase 16 D-15 (CONN-11): ``(id, degree)`` for one page of graph nodes whose id starts with
    ``prefix``, ordered by id, plus the number of such nodes. It follows :func:`probe_graph`: a missing
    ``graph.cozo`` is ``([], 0)`` and creates nothing, a directory without the RocksDB marker raises
    :class:`GraphStoreCorruptedError` before any open, and a held graph raises ``GraphStoreBusyError``.
    It never constructs ``CozoGraphStore``. Degrees come from one batched edge query per page, counted
    here with ``{src, tgt}`` so a self-loop counts once (Cozo ``count()`` is avoided, bug #244)."""
    held = acquire_graph(dir_path)
    if held is None:
        return [], 0
    key, shared = held
    try:
        if not _has_graph_relations(shared.client):
            return [], 0
        # x = id stops Cozo pushing starts_with into a key-range scan that drops the key equal to $p.
        # One statement gives the page and the total, so they agree (16-REVIEW-B WR-02).
        # shortcut: O(N) ids per page, no count() (Cozo #244); add a counter relation if graphs exceed ~10^6 nodes
        matching = [
            r[0]
            for r in _run_immutable(
                shared.client, "?[id] := *nodes{id}, x = id, starts_with(x, $p) :order id", {"p": prefix}
            )
        ]
        ids, total = matching[offset : offset + limit], len(matching)
        rows = _run_immutable(
            shared.client,
            "?[src, tgt] := *edges{src, tgt}, is_in(src, $ids)\n?[src, tgt] := *edges{src, tgt}, is_in(tgt, $ids)",
            {"ids": ids},
        )
    finally:
        _ClientRegistry.release(key)
    degree = dict.fromkeys(ids, 0)
    for src, tgt in rows:
        for node in {src, tgt}:
            if node in degree:
                degree[node] += 1
    return [(i, degree[i]) for i in ids], total


def graph_node_edges(
    dir_path: Path, node_id: str, limit: int, offset: int
) -> tuple[bool, int, list[dict[str, Any]]]:
    """Phase 16 D-15/D-16 (CONN-12): ``(found, degree, edges)`` for one graph node. Opens the graph as
    :func:`graph_node_page` does. ``(False, 0, [])`` is a missing ``graph.cozo`` or an id that is not a
    node. ``degree`` is the unpaged incident-edge count (a self-loop counts once). It and the edge page
    are two statements: pycozo 0.7.6 has no read snapshot (a ``multi_transact(False)`` sees a write
    committed after it began), so a write between them can shift ``degree`` by that write. Each edge is
    projected to ``{src, tgt, edge_types, weight}`` and nothing else, so extracted description text and
    per-chunk maps stay behind the seam (D-16)."""
    held = acquire_graph(dir_path)
    if held is None:
        return False, 0, []
    key, shared = held
    try:
        if not _has_graph_relations(shared.client):
            return False, 0, []
        if not _run_immutable(shared.client, "?[id] := *nodes{id}, id = $id", {"id": node_id}):
            return False, 0, []
        degree = len(
            _run_immutable(shared.client, "?[src, tgt] := *edges{src, tgt}, src = $id or tgt = $id", {"id": node_id})
        )
        rows = _run_immutable(
            shared.client,
            "?[src, tgt, attrs] := *edges{src, tgt, attrs}, src = $id or tgt = $id :order src, tgt :limit $l :offset $o",
            {"id": node_id, "l": limit, "o": offset},
        )
    finally:
        _ClientRegistry.release(key)
    edges = []
    for src, tgt, raw in rows:
        attrs = _attrs_to_dict(raw)
        edges.append({"src": src, "tgt": tgt, "edge_types": attrs.get("edge_types"), "weight": attrs.get("weight")})
    return True, degree, edges


def probe_vector(dir_path: Path) -> ProbeState:
    try:
        return "absent" if load_committed(Path(dir_path)) is None else "ok"
    except (VectorStoreCorruptedError, OSError):  # an unreadable pair, or a PermissionError on it
        return "corrupted"


def list_kv_prefix(
    dir_path: Path, prefix: str, *, limit: int, offset: int
) -> tuple[list[tuple[str, dict[str, Any]]], int]:
    """Phase 12 D-13 (HIPP-15): the ``(key, decoded value)`` rows of one namespace whose key starts
    with ``prefix``, in ascending key order, plus the total number of such keys. A missing, empty or
    table-less ``kv.sqlite3`` is ``([], 0)``. The read path creates nothing (LRAG-13), which is why
    this is not a ``SqliteKVStore`` (its constructor makes the directory and the table). The
    database opens ``immutable`` like :func:`probe_kv`, except when a live writer's ``-wal`` and
    ``-shm`` both exist: then plain ``mode=ro`` is safe (it creates neither) and sees a committed
    write that is still in the WAL. A sqlite error other than a missing table propagates, including a
    WAL with frames but no ``-shm`` (a crash leftover or copied store: refused rather than listed
    short). Residual race, accepted: a writer that closes between the existence check and the open
    can leave the ``mode=ro`` open to create ``-shm``."""
    db_path = (Path(dir_path) / "kv.sqlite3").resolve()
    if not db_path.is_file() or db_path.stat().st_size == 0:
        return [], 0
    wal, shm = db_path.with_name("kv.sqlite3-wal"), db_path.with_name("kv.sqlite3-shm")
    try:
        wal_has_frames = wal.stat().st_size > 0
    except FileNotFoundError:  # B-IN-07: the last writer closed and SQLite removed the WAL, which is healthy
        wal_has_frames = False
    if wal_has_frames and not shm.exists():
        # B-WR-02: an immutable open ignores the WAL, so it would omit committed documents; a plain
        # read-only open would create -shm. Neither is an honest listing.
        raise sqlite3.OperationalError("kv.sqlite3-wal holds frames but kv.sqlite3-shm is missing")
    live = wal.exists() and shm.exists()
    uri = db_path.as_uri() + ("?mode=ro" if live else "?mode=ro&immutable=1")
    conn = sqlite3.connect(uri, uri=True, timeout=0.1)
    # Every key >= prefix and < prefix with its last character incremented starts with prefix; an
    # empty prefix matches every key.
    if prefix:
        where, bounds = "WHERE id >= ? AND id < ?", (prefix, prefix[:-1] + chr(ord(prefix[-1]) + 1))
    else:
        where, bounds = "", ()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM kv {where}", bounds).fetchone()[0]
        rows = conn.execute(
            f"SELECT id, value FROM kv {where} ORDER BY id LIMIT ? OFFSET ?",
            (*bounds, limit, offset),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" in str(exc).lower():
            return [], 0  # a writer's CREATE TABLE has not reached a snapshot this connection can see
        raise
    finally:
        conn.close()
    return [(key, json.loads(value)) for key, value in rows], int(total)
