"""Read-only store probes for ``Databasise.health()`` (Phase 10 D-14, STOR-04). Each probe takes one
namespace directory and returns ``"ok"``, ``"absent"``, ``"corrupted"`` or ``"busy"``. A probe
creates nothing and never raises.

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
from databasise.stores.vector import load_committed

ProbeState = Literal["ok", "absent", "corrupted", "busy"]


def probe_kv(dir_path: Path) -> ProbeState:
    db_path = Path(dir_path) / "kv.sqlite3"
    if not db_path.is_file():
        return "absent"
    wal_open = db_path.with_name("kv.sqlite3-wal").exists()
    uri = db_path.as_uri() + ("?mode=ro" if wal_open else "?mode=ro&immutable=1")
    conn = None
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=0.1)
        conn.execute("SELECT 1 FROM kv LIMIT 1").fetchall()
        return "ok"
    except sqlite3.OperationalError as exc:
        return "busy" if "locked" in str(exc).lower() else "corrupted"
    except Exception:
        return "corrupted"
    finally:
        if conn is not None:
            conn.close()


def probe_graph(dir_path: Path) -> ProbeState:
    db_path = Path(dir_path) / "graph.cozo"
    if not db_path.exists():
        return "absent"
    try:
        key, shared = _ClientRegistry.acquire(db_path)
    except GraphStoreBusyError:
        return "busy"
    except Exception:
        return "corrupted"
    try:
        shared.client.run("::relations", {}, True)
        return "ok"
    except Exception:
        return "corrupted"
    finally:
        _ClientRegistry.release(key)


def probe_vector(dir_path: Path) -> ProbeState:
    try:
        return "absent" if load_committed(Path(dir_path)) is None else "ok"
    except Exception:  # VectorStoreCorruptedError, or anything the read itself raises
        return "corrupted"
