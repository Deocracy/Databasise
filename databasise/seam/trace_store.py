"""``databasise.seam.trace_store`` — durable ``RunRecord`` persistence keyed by an opaque token
(API-10, D-06), 04-04's Task 1 deliverable. Nothing in the codebase persists a ``RunRecord`` before
this module: ``databasise/__init__.py:run_wiring`` and ``databasise/parity/run_arm.py`` both
construct one and return it in-memory only. This module gives the seam's trace reference (§18.2)
something durable to resolve against.

**Why the token is random, not derived (D-06's own prohibition against a decodable reference).**
``databasise.identity.canon.canonicalise`` is available and could derive a token from the run's own
fields, but a derived token is a decodable token: anything computed from ``run_id``/``wiring_id``/
a timestamp/a sequence number carries exactly the recoverable structure §18.2 requires kept *behind*
the reference, not encoded *in* it. ``secrets.token_urlsafe`` mints an unguessable value with no
relationship at all to the record it is later bound to in this store's own table — the only way to
learn what a token resolves to is to already hold a record this module minted it for.

**Schema, WAL mode, row round-tripping** — following ``databasise/ledger/ledger.py``'s established
pattern exactly: its own database file (``trace.db``) beside ``ledger.db`` at the store root, one
table, ``PRAGMA journal_mode=WAL``. Unlike the ledger, this table is not append-only-with-triggers —
a trace record is never amended or superseded, so there is nothing analogous to guard against.

**04-05, Task 1 (Rule 3 deviation): ``check_same_thread=False``.** Unlike ``databasise/stores/kv.py``'s
connection (whose own docstring defers this exact change as "real surgery with real correctness
risk" for the *runner's* structured concurrency), ``TraceStore`` is constructed exactly once, in
``Databasise.__init__``, and is then used for the *lifetime* of that engine instance. 04-05's REST
transport constructs the engine once (an application factory, ``databasise.seam.rest.create_app``)
but then serves every request on the ASGI server's own event-loop thread — which, under a test
driven by ``starlette.testclient.TestClient``, is a *different* OS thread than the one that
constructed the engine (`TestClient` runs the ASGI app on an ``anyio`` portal thread). This is
never concurrent, cross-thread *access* (exactly one thread executes at any instant, since a
single connection is only ever awaited sequentially through the async engine) — only a mismatch
between the *constructing* thread and the *using* thread, which ``check_same_thread=False`` is
the documented, correct escape hatch for. A real multi-worker/multi-threaded deployment sharing
one ``TraceStore`` connection across concurrent requests remains out of scope and unaddressed by
this change, exactly as it always was.
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from databasise.seam.refusals import SeamRefusalError

# secrets.token_urlsafe(32) -> 256 bits of entropy from os.urandom, well above the 128-bit floor
# API-10's acceptance criteria require.
_TOKEN_BYTES = 32


class UnknownTraceReferenceError(SeamRefusalError):
    """Raised when a trace reference names no record this store currently holds. Never returns
    ``None`` and never a partial record (API-10's own truth: an unknown reference resolves to a
    named refusal, never a partial or empty record) — an untrusted reference handed back to the
    seam gets a raise, not a value a caller could mistake for "the run had no trace"."""

    def __init__(self, trace_reference: str):
        self.trace_reference = trace_reference
        super().__init__(
            f"trace reference {trace_reference!r} does not resolve to any stored run record"
        )


class TraceStore:
    """SQLite-backed run-record store at its own database file, ``trace.db``, beside ``ledger.db``
    under the store root — mirrors ``databasise/ledger/ledger.py``'s schema-creation/WAL/
    row-round-trip pattern."""

    def __init__(self, store_root: str | Path) -> None:
        db_path = Path(store_root) / "trace.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: see this module's own docstring (04-05, Task 1) — safe here
        # because this connection is never accessed concurrently from more than one thread at a
        # time, only sequentially from a thread that may differ from the one that opened it.
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()

    def _create_schema(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS traces (
                token TEXT PRIMARY KEY,
                run_record TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._conn.commit()

    def persist(self, run_record: dict[str, Any]) -> str:
        """Mint a fresh, unguessable token and persist ``run_record`` (a ``RunRecord.to_dict()``
        shape) under it, returning the token. Two calls — even for byte-identical ``run_record``
        content — mint two distinct tokens; each run gets its own reference.
        """
        token = secrets.token_urlsafe(_TOKEN_BYTES)
        self._conn.execute(
            "INSERT INTO traces (token, run_record, created_at) VALUES (?, ?, ?)",
            (token, json.dumps(run_record), datetime.now(UTC).isoformat()),
        )
        self._conn.commit()
        return token

    def resolve(self, token: str) -> dict[str, Any]:
        """The record persisted under ``token``. Raises :class:`UnknownTraceReferenceError` —
        never returns ``None``, never a partial record — for a token this store does not hold.
        """
        cur = self._conn.execute("SELECT run_record FROM traces WHERE token = ?", (token,))
        row = cur.fetchone()
        if row is None:
            raise UnknownTraceReferenceError(token)
        return json.loads(row["run_record"])


__all__ = ["TraceStore", "UnknownTraceReferenceError"]
