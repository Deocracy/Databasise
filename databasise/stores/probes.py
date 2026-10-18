"""Read-only store probes for ``Databasise.health()`` (Phase 10 D-14, STOR-04). Each probe takes one
namespace directory and returns ``"ok"``, ``"absent"``, ``"corrupted"`` or ``"busy"``. A probe
creates nothing and never raises for a store state (a programming error still surfaces). A
``graph.cozo`` that is not a RocksDB database (no ``data/CURRENT`` naming an existing manifest) is
``corrupted`` and is never opened.

Two measurements (10-07 planning) shape the probes:
- sqlite: on a WAL ``kv.sqlite3`` with no open writer, ``?mode=ro`` leaves ``kv.sqlite3-wal`` and
  ``kv.sqlite3-shm`` behind, and ``?mode=ro&immutable=1`` creates nothing. When a writer is open the
  ``-wal`` file already exists, and ``?mode=ro`` reads committed rows without blocking.
- Cozo: opening a missing ``graph.cozo`` creates it, so the probe checks existence first. Opening an
  existing one rotates RocksDB's own files inside ``graph.cozo/data/`` and nothing outside it.
  ``::relations`` run immutable adds no relation, and ``_ensure_relations`` is never called.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal

from databasise.stores.graph import GraphStoreBusyError, _ClientRegistry
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
    db_path = Path(dir_path) / "kv.sqlite3"
    if not db_path.is_file():
        return "absent"
    try:
        if db_path.stat().st_size == 0:
            return "absent"  # a valid empty database: SqliteKVStore creates its table on first open
    except OSError:
        return "corrupted"
    wal_open = db_path.with_name("kv.sqlite3-wal").exists()
    uri = db_path.as_uri() + ("?mode=ro" if wal_open else "?mode=ro&immutable=1")
    conn = None
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=0.1)
        conn.execute("SELECT 1 FROM kv LIMIT 1").fetchall()
        return "ok"
    except sqlite3.OperationalError as exc:
        return "busy" if "locked" in str(exc).lower() else "corrupted"
    except (sqlite3.Error, OSError):
        return "corrupted"
    finally:
        if conn is not None:
            conn.close()


def _rocksdb_marker_present(db_path: Path) -> bool:
    """True when ``db_path`` is a directory holding a RocksDB database: ``data/CURRENT`` names a
    ``MANIFEST-*`` file that exists. Opening anything else would create files inside it."""
    try:
        name = (db_path / "data" / "CURRENT").read_text(encoding="utf-8").strip()
        return name.startswith("MANIFEST-") and (db_path / "data" / name).is_file()
    except (OSError, ValueError):
        return False


def probe_graph(dir_path: Path) -> ProbeState:
    db_path = Path(dir_path) / "graph.cozo"
    if not db_path.exists():
        return "absent"
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


def probe_vector(dir_path: Path) -> ProbeState:
    try:
        return "absent" if load_committed(Path(dir_path)) is None else "ok"
    except (VectorStoreCorruptedError, OSError):  # an unreadable pair, or a PermissionError on it
        return "corrupted"
