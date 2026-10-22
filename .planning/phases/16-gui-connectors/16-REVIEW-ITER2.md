---
phase: 16-gui-connectors
iteration: 2
reviewed: 2026-10-22T23:30:00Z
depth: deep
scope: "fix(16) commits b85c7ed 12f9dce 7ebbf66 32a247a 48e53ba fabe7d9 83b642c 07a4b7a fd55fc1 (after b72783b); C-WR-01 / lane C WR-01 excluded (held graph client, awaiting owner grant)"
files_reviewed: 8
files_reviewed_list:
  - databasise/ledger/ledger.py
  - databasise/seam/engine.py
  - databasise/seam/trace_store.py
  - databasise/seam/operator_rest.py
  - databasise/stores/probes.py
  - databasise/stores/graph.py
  - databasise/launcher/serve_rest.py
  - docs/gui/API-INVENTORY.md
findings:
  critical: 0
  warning: 1
  info: 4
  total: 5
status: issues_found
---

# Phase 16: Code Review Report, Iteration 2 (review-fix re-check)

**Reviewed:** 2026-10-22
**Depth:** deep
**Files Reviewed:** 8
**Status:** issues_found

## Summary

I re-checked the nine `fix(16):` commits after b72783b against 16-REVIEW-A/B/C.md and the Lane A/B/C tables in 16-REVIEW-FIX.md. C-WR-01 is left out as instructed. Lane C's WR-01 is the same held-graph-client finding, so it is left out too.

How I checked:
- I read the source diffs `b72783b..HEAD`. I did not open, grep or diff any test file.
- I ran the covering tests with plain pytest and no `-m live`. `test_operator_review_b.py`, `test_operator_review_a.py`, `test_graph_read_review_c.py`, `test_log_file_refusal.py`, `test_console_graph.py` and `test_console_log.py` gave 33 passed. `tests/ledger` gave 29 passed.
- I ran two scratch probes, `scratchpad/iter2/probe_ledger.py` and `scratchpad/iter2/probe_graph_log.py`, on tmp stores only.
- `ruff` reports nothing on the changed lines. Every ruff finding in these files predates the fixes.

Results:
- Eight of the nine findings in scope are fixed, and I found no regression in them.
- B-WR-01 is fixed only when reads do not overlap. Two read-only ledger handles that overlap still leave `ledger.db-wal` and `ledger.db-shm` behind. After that, every later read keeps them (probed). See WR-01.
- **Data loss (lane B WR-01's conditional close checkpoint):** I found no data-loss risk. A close checkpoint runs only when the connection holds SQLite's exclusive lock, which means no other connection is open. It copies committed frames only. In the probe, a writer committed and closed while a reader was open. The reader's close then checkpointed, and both alias rows (`a`, `b`) were intact afterwards.
- No fix contradicts D-01..D-19.
  - D-15 spells the node page as `:order id :limit :offset`. C-CR-01/B-WR-02 now slice in Python. The result is the same, and the O(N) cost is unchanged from the old total query.
  - D-09 ("creates no file") holds for sequential reads only. See WR-01.
- The not-fixed and needs-owner-grant reasons:
  - B-WR-01: rejecting `immutable=1` is sound. With `immutable=1`, SQLite skips locking and change detection, so a concurrent promote in the same process could give a torn read.
  - B-WR-02: the residual in `graph_node_edges` is disclosed.
  - A-WR-04's 503 residual is sound for the two graph routes only. See IN-03.

## Per-finding verdicts

| Finding | Verdict | Evidence |
|---|---|---|
| C-CR-01 | fixed | `databasise/stores/probes.py:159-166`. Probe on nodes `a, ab, b, Al, Alice, Alice Smith, ""`: prefix `a` gives `a, ab`; `Al` gives `Al, Alice, Alice Smith`; `Alice Smith` gives itself; `""` gives all 7. Paging (`A`, limit 2, offset 1) and offset 2^70 are correct. Frozen-bug list at `databasise/stores/graph.py:11, 21-23`. |
| C-WR-02 | fixed | `databasise/stores/probes.py:132-136, 157-158, 203-204`. Probe on a nodes-only store (crash between the two `:create`): gives `([], 0)` and `(False, 0, [])`, and `::relations` afterwards still lists `nodes` only, so nothing was created. Consistent with `probe_graph` `ok`. |
| C-WR-01 / lane C WR-01 | excluded | Held graph client, awaiting owner grant (instruction). |
| B-WR-01 | partially fixed | `databasise/ledger/ledger.py:193-201`. Sequential reads leave only `ledger.db` (probe). Overlapping reads leave both files for good: see **WR-01**. Narrowing of 14-REVIEW-ITER2 WR-02: see IN-02. |
| B-WR-02 | fixed | `ledger.py:286-295` (`snapshot`), `engine.py:2213`, `trace_store.py:109-117`, `probes.py:162-168`. Probe: a writer committed inside an open `snapshot()`, and the second `history_for_alias` still returned 1 row, so the snapshot holds. The residual in `graph_node_edges` (`probes.py:189-191`) is disclosed. Docstring overstatement: IN-01. Shared-connection coupling: IN-04. |
| B-WR-03 / A-WR-01 | fixed | `engine.py:2197-2198, 2242-2243, 2254-2255, 2331-2332`; `trace_store.py:118-120`. Not catching `TypeError` is sound: every JSON column is `NOT NULL` (`ledger.py:305, 313-316`), so `json.loads` (`ledger.py:393`) only ever sees text. Pre-existing and out of scope: the prologue's `_refuse_gate_verb` ledger read (`engine.py:2757-2762`) is unmapped for gate verbs (lane B IN-07 class). |
| B-WR-04 / A-WR-02 | fixed | `engine.py:2451-2464`. The `is_file()` check and the open are on one worker thread, and every `OSError` becomes `StoreFault`. `Path.is_file` re-raises EACCES on an unreadable parent, which is also mapped. |
| B-WR-05 | fixed | `engine.py:414-415, 2441-2459`. Probe: a line of exactly the cap is kept whole. Cap+1 is cut with the marker. A line of cap plus `\r` is kept whole (universal newlines). A last line of 3x the cap with no newline is cut. An `sk-` key cut right after `sk-` leaks no key characters. The patterns use `+` (`v1_corpus_adapter.py:60-66`), so a cut that keeps 1 or more key characters is masked. |
| A-WR-03 | fixed | `serve_rest.py:135-142`, before `open_engine` at 143-146. `refuse()` prints one `databasise:` line and returns 1 (`launcher/__init__.py:125-129`). |
| A-WR-04 | fixed, with a residual | `operator_rest.py:90-136`; `API-INVENTORY.md:768-781`. 409 is declared on the two graph routes only. The statuses in the table match the engine (`engine.py:2193-2198, 2238-2243, 2250-2255, 2327-2332, 2361-2364, 2388-2396, 2410-2422, 2461-2464`). The 503 residual's reasoning: IN-03. |

## Warnings

### WR-01: B-WR-01 holds only for reads that do not overlap. Two overlapping read-only handles leave `-wal`/`-shm`, and they stay for every later read

**File:** `databasise/ledger/ledger.py:197-201`

**Issue:** Each handle decides at open time whether its close may checkpoint, by checking `wal_existed = db_path.with_name("ledger.db-wal").exists()`. When two read-only handles overlap:
- Reader A opens first and its first read creates `-wal`.
- Reader B then sees `-wal` and sets `NO_CKPT_ON_CLOSE`.
- A closes first. It is not the last connection, so nothing is checkpointed.
- B closes last, with the checkpoint disabled. Both files remain.
- From then on, every read sees `-wal` and also disables the checkpoint. The files stay until a writer is the last connection to close.

Probe (`scratchpad/iter2/probe_ledger.py`, case 2):
```
overlap A,B (A closes first): ['ledger.db', 'ledger.db-shm', 'ledger.db-wal']
next sequential read after overlap: ['ledger.db', 'ledger.db-shm', 'ledger.db-wal']
after 3 more sequential reads: ['ledger.db', 'ledger.db-shm', 'ledger.db-wal']
```
The same thing happens if the check runs just before a writer's close deletes `-wal`.

**Failure scenario:** The console polls `GET /ledger/aliases` while the operator opens `POST /ledger/history`. Each runs `Ledger.open_existing(read_only=True)` in `asyncio.to_thread` (`engine.py:2178, 2210`), so the two handles overlap. A consumer alias `/query` can also overlap them: `_resolve_alias` uses the same handle (`selectors.py:299`), inline on the event loop. After one such overlap, D-09's "creates no file" and the `ledger_aliases` docstring ("creates nothing", `engine.py:2174`) are false for the rest of the server's life. The covering test reads sequentially, so it does not detect this.

**Fix:** Decide at close time, not at open time. Allow the close checkpoint only when the WAL holds no frames. This also undoes the IN-02 narrowing, because a WAL that holds a writer's frames is never checkpointed by a reader:
```python
def close(self) -> None:
    if self._read_only and hasattr(sqlite3, "SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE"):
        wal = self._db_path.with_name("ledger.db-wal")
        try:
            empty = wal.stat().st_size == 0  # a reader-created WAL has no frames
        except FileNotFoundError:
            empty = True
        self._conn.setconfig(sqlite3.SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE, not empty)
    self._conn.close()
```
Set `self._read_only` and `self._db_path` in `open_existing`, and drop the open-time `wal_existed` branch. Add a test that opens two read handles, closes them in either order, and asserts `sorted(os.listdir(root)) == ["ledger.db"]`.

## Info

### IN-01: The `Ledger.snapshot()` docstring says a promote or rollback "cannot commit between them". In WAL mode it can

**File:** `databasise/ledger/ledger.py:288-290`
**Issue:** A deferred read transaction in WAL mode does not block writers. It pins the reader's view only. In the probe (case 4), `Ledger(d).append(...)` committed while the snapshot was open. The reads stayed consistent, which is what WR-02 needed, but the docstring overstates what the snapshot does.
**Fix:** Change the sentence to "so they see one WAL snapshot: a promote or rollback that commits meanwhile is not seen by them".

### IN-02: B-WR-01 narrows 14-REVIEW-ITER2 WR-02 on the consumer alias read path

**File:** `databasise/ledger/ledger.py:193-201`; `databasise/seam/selectors.py:299`
**Issue:** The narrowing is disclosed. It needs no `-wal` at the open, and a writer that commits and closes while the read is open. In that case the read-only handle's close checkpoints the writer's frames into `ledger.db`, a physical write on the read path that CONTRACT §6 forbids ("a read must not write"). Probe case 3: the alias rows stayed intact and there was no data loss. The fix suggested in WR-01 removes this case, because a WAL that holds frames keeps `NO_CKPT_ON_CLOSE`.
**Fix:** Take WR-01's close-time rule. Otherwise keep the docstring as it is.

### IN-03: A-WR-04's needs-owner-grant reason for the 503 holds only for the two graph routes

**File:** `databasise/seam/operator_rest.py:90-136`; `.planning/phases/16-gui-connectors/16-CONTEXT.md:234`
**Issue:** By the fix report and the test name, the protected `test_console_graph.py` assertion pins `{"409", "502", "503"}` on `/graph/nodes`. The other six store-reading routes are pinned only by the CONTEXT OpenAPI line "(502, 503, 409)". The same commit already departed from that line when it dropped the 409 from those routes. So the line is treated as binding for 503 and not for 409. As a result, OpenAPI still declares, on eight routes, a 503 that no operator path can raise. I checked this: every `_ENGINE_UNAVAILABLE` class is raised only on v1, driver or digest paths (`engine.py:728, 814`).
**Fix:** Ask the owner for one amendment to 16-CONTEXT.md:234 that covers both statuses. It should say that store-reading operator routes declare 502, and the graph routes also declare 409. Apply it together with the protected-test change named in 16-REVIEW-FIX.md.

### IN-04: `TraceStore.list_page`'s explicit `BEGIN`/`rollback()` on the shared write connection is safe only while it runs on the same thread as `persist`

**File:** `databasise/seam/trace_store.py:109-117`; callers `engine.py:2251` and `engine.py:2563`
**Issue:** `list_traces` and `_execute`'s `persist` both run synchronously on the event-loop thread, so they cannot interleave today. Lane A IN-04 suggests moving `list_traces` into `asyncio.to_thread`. If that is done with this connection (`check_same_thread=False`), this order becomes possible:
- `list_page` runs `BEGIN`.
- `persist` runs its `INSERT` inside that transaction.
- `list_page` runs `rollback()`, which discards the `INSERT`.
- `persist` runs `commit()`, which commits nothing.

The consumer then holds a trace token that answers 404.
**Fix:** Add one line above the `BEGIN`: `# same-thread only: a rollback here would discard a concurrent persist() INSERT on this shared connection`. If the read ever moves to a worker thread, give it its own read-only connection.

---

_Reviewed: 2026-10-22_
_Reviewer: Claude (gsd-code-reviewer), iteration 2_
_Depth: deep_
