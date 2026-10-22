---
phase: 16-gui-connectors
lane: B
reviewed: 2026-10-22T20:40:37Z
depth: deep
diff_base: d608162
files_reviewed: 5
files_reviewed_list:
  - databasise/seam/engine.py
  - databasise/seam/trace_store.py
  - databasise/ledger/ledger.py
  - databasise/seam/refusals.py
  - databasise/seam/promotion.py
findings:
  critical: 0
  warning: 5
  info: 7
  total: 12
status: issues_found
---

# Phase 16: Code Review Report (Lane B)

**Reviewed:** 2026-10-22T20:40:37Z
**Depth:** deep
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Scope: the Phase 16 operator read methods in `databasise/seam/engine.py` (`info`, `_write_in_flight`, `wirings`, `ledger_aliases`, `ledger_history`, `list_traces`, `preview_promotion`, `chunk_page`, `_graph_dir`, `graph_nodes`, `graph_node`, `log_tail`), the `_promotion_prologue` / `_plan_promotion` extraction, `_scrub_reasons`, `TraceStore.list_page`, `Ledger.aliases`, and `UnknownGraphNodeError`. `databasise/seam/promotion.py` has no change in `d608162..HEAD`, so it was reviewed only as a call target. Call chains were followed into `stores/probes.py` (`graph_node_page`, `graph_node_edges`, `_is_store_error`), `stores/graph.py` (`held_graph_paths`, edge canonicalisation), `stores/vector.py` (`FaissVectorStore.__init__`, `list_ids`, `load_committed`), `seam/operator_rest.py`, `seam/rest.py` (`_status_for`, `PromoteRequest`), `seam/corpus.py` (`Page`, `_URL_RE`) and `foreign/v1_corpus_adapter.py` (`redact_secrets`).

These checks found no defect:
- **Promote extraction.** `promote()` still calls `_plan_promotion` inside `with Ledger(...) as ledger, ledger.transaction():` (engine.py:2903-2906), so the prior-row read, the version mint and the append still share one `BEGIN IMMEDIATE` span. The prologue is the old code moved unchanged, so the refusal order is the same as before.
- **Preview agrees with promote.**
  - It runs the same prologue and computes `next_version` with the same `_plan_promotion`.
  - When stage 1 refuses before alias validation, the best-effort arm lookup swallows the later input refusals, so preview gives `GateNotCalibratedError` exactly as promote does.
  - No ledger file is created when none exists.
- **Paging.** `Page` refuses `limit < 1`, `limit > MAX_PAGE_SIZE` and `offset < 0`. Every `next_offset` is `offset + limit` when that is below `total`, else `None`. This is correct at both boundaries.
- **Degree counts.** Edges are stored under a canonical key (`_canonical_edge_key`). The degree queries count each `{src, tgt}` pair once, so a self-loop counts once.
- **Statuses.**
  - `UnknownGraphNodeError` answers 422 through `_status_for`'s default.
  - A busy graph is re-raised as `StoreBusyError(store_kind="graph")`, which answers 409.
  - A corrupted graph or vector store becomes a `StoreCorrupted` fault (502).
- **No store construction on reads.** `chunk_page` never builds `_build_stores` or `CozoGraphStore`.
- **`info()` leaks nothing.** It returns only version, workspace, client key presence and two booleans.

The defects found are robustness gaps on the read paths:
- The read-only ledger handle leaves `-wal`/`-shm` files behind (verified by probe).
- The multi-statement reads take no snapshot.
- Corrupted JSON rows escape as 500s.
- `log_tail` has an unmapped OS error path and no per-line size bound.

## Warnings

### WR-01: Read-only ledger reads create `ledger.db-wal` and `ledger.db-shm` (D-09 "creates no file" does not hold)

**File:** `databasise/ledger/ledger.py:191` (via `databasise/seam/engine.py:2175`, `:2205`, `:2307`)
**Issue:** `Ledger.open_existing(read_only=True)` opens the WAL-mode `ledger.db` with a plain `sqlite3.connect(db_path)` and `PRAGMA query_only`. On a WAL database whose last writer closed cleanly, so that no `-wal` or `-shm` file exists, that open creates both files. Because the handle sets `SQLITE_DBCONFIG_NO_CKPT_ON_CLOSE`, the close does not checkpoint, so SQLite does not delete them. A scratch probe confirmed it. After `Ledger(d)` closes, the directory holds `['ledger.db']`. After `open_existing(d, read_only=True)` plus `aliases()` plus close, it holds `['ledger.db', 'ledger.db-shm', 'ledger.db-wal']`.

Three new operator read routes inherit this: `GET /ledger/aliases`, `POST /ledger/history` and `POST /promote/preview`. Each therefore writes files under `store_root`. This contradicts the phase rule that a read path creates nothing, and the `ledger_aliases` docstring ("creates nothing"). On a store root that is read-only to the server process, every one of these reads fails with `sqlite3.OperationalError`, which becomes a 502 `StoreFault` even though the ledger is healthy. `stores/probes.py:8-10` already records the same SQLite behaviour for `kv.sqlite3` and avoids it.
**Fix:** Mirror `list_kv_prefix` (`stores/probes.py:234-244`). Open with `immutable=1` when no `-wal` file exists, and with plain `mode=ro` only when both `-wal` and `-shm` already exist. If the LEDG-06 lifecycle check needs the plain path, extend it to recognise the URI form.
```python
db_path = (Path(store_root) / "ledger.db").resolve()
wal, shm = db_path.with_name("ledger.db-wal"), db_path.with_name("ledger.db-shm")
live = wal.exists() and shm.exists()
uri = db_path.as_uri() + ("?mode=ro" if live else "?mode=ro&immutable=1")
self._conn = sqlite3.connect(uri, uri=True)
```
Add a test asserting that `sorted(os.listdir(store_root))` is unchanged across `ledger_aliases()`, `ledger_history()` and `preview_promotion()`.

### WR-02: Multi-statement operator reads take no snapshot, so `active` flags and totals can contradict the rows returned

**File:** `databasise/seam/engine.py:2209-2212`, `databasise/seam/trace_store.py:107-111`
**Issue:** `ledger_history` reads `history_for_alias`, then `by_alias`, then `lineage` as three autocommit statements on one read-only handle. If a `promote` or `rollback` commits between the first and second read, `head` is a row that is not in `rows`:
- After a new promotion, the head's lineage is just its own new version, so no returned row is flagged `active`.
- After a new rollback, the lineage covers the rollback's target. The old target row is then flagged `active` and the previously active row is not, while the page omits the rollback row that explains the change.

`TraceStore.list_page` runs the page `SELECT` and `COUNT(*)` as separate statements, so `total` (and therefore `next_offset`) can count rows the page did not see. `graph_node_edges` (`stores/probes.py:194-201`) likewise computes `degree` and the edge page in two queries, and `graph_node` derives `next_offset` from that `degree`.
**Fix:** Run each multi-statement read inside one read transaction. `BEGIN` (deferred) is allowed under `PRAGMA query_only` and pins a WAL snapshot:
```python
with handle:
    handle._conn.execute("BEGIN")
    try:
        rows = handle.history_for_alias(alias)
        head = handle.by_alias(alias)
        active = set(handle.lineage(alias, head.minted_version)) if head is not None else set()
    finally:
        handle._conn.rollback()
```
Do the same around the two statements in `list_page`. The cleaner option is a `Ledger.snapshot()` context manager, so callers do not reach into `_conn`.

### WR-03: A corrupted JSON row in `trace.db` or `ledger.db` escapes as a 500, not the 502 store fault

**File:** `databasise/seam/engine.py:2243-2260`, `:2186-2193`, `:2219-2236`; `databasise/seam/trace_store.py:112`; `databasise/ledger/ledger.py:375`
**Issue:** `list_traces` catches only `sqlite3.Error`. `TraceStore.list_page` calls `json.loads(r["run_record"])` for every row, so one row holding invalid JSON raises `json.JSONDecodeError` (a `ValueError`) out of the route as an unhandled 500. That breaks every page containing the row, including the default first page once the row is recent. A row that decodes to a non-dict, such as a JSON list, fails at `rec.get("partial")` with `AttributeError`, also a 500. `ledger_aliases` and `ledger_history` have the same gap: `_row_to_record` runs `json.loads` on `arm_instance_hashes`, `promotion_trace_ids` and the other JSON columns, and only `sqlite3.Error` is mapped. The phase rule is that a corrupted store is a named 502 fault and nothing escapes as a 500.
**Fix:** Widen the mapping at each of the three call sites:
```python
except (sqlite3.Error, ValueError, TypeError, AttributeError) as exc:
    raise _foreign_fault("list_traces", exc, failure_class="StoreCorrupted") from exc
```
`SeamRefusalError` is itself a `ValueError`, so either catch it first and re-raise it, or decode in `list_page` and raise a store-local error type there. Also guard `isinstance(rec, dict)` before calling `.get`.

### WR-04: `log_tail` can raise an unmapped `OSError` (500): check-then-open race, and permission errors

**File:** `databasise/seam/engine.py:2422-2431`
**Issue:** `Path(path).is_file()` is checked on the event loop and the file is opened later on a worker thread. If logrotate, or an operator, moves or deletes the file between the two steps, `open()` raises `FileNotFoundError`. A log file that is not readable raises `PermissionError`. Neither is caught, so `GET /log` answers a bare 500, although the route declares only 502/503/409 in OpenAPI (`operator_rest.py:135`).
**Fix:** Do the existence check and the read inside the thread, and map the errors:
```python
def _tail() -> list[str]:
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            tail = deque(handle, maxlen=limit)
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise _foreign_fault("log_tail", exc, failure_class="StoreFault") from exc
    ...
```

### WR-05: The log tail is bounded in lines but not in bytes

**File:** `databasise/seam/engine.py:2428-2429`
**Issue:** `deque(handle, maxlen=limit)` caps the number of lines (1..1000) but not their length. A log line with no newline, for example a logged request body, a long unwrapped `repr`, or a wrong `--log-file` pointing at a binary file, is held whole in memory and returned whole in the JSON body. Each of the 1000 lines can be arbitrarily large, so the response is unbounded in size. The phase requires a bounded tail.
**Fix:** Truncate each line before redaction, for example `line[:4096]` with a marker. The cap must be applied before `redact_secrets`, so that a truncated secret is still a prefix the patterns match, or after a pass that cannot split a token: truncate, redact, then append `"…[truncated]"`. Optionally read only the last N bytes with `seek` instead of the whole file. That also retires the `shortcut:` comment at line 2426.

## Info

### IN-01: `_write_in_flight` takes `_WRITE_GATES_GUARD` and inserts gate entries on a read

**File:** `databasise/seam/engine.py:2132-2135` (via `_gate_for`, `:850-852`)
**Issue:** The flag never acquires a write gate, so D-17 holds. It does take the module mutex `_WRITE_GATES_GUARD`, and `setdefault` inserts a new `threading.Lock` for the HippoRAG key of every workspace that `GET /info` is asked about, including one that never wrote. The mutex is held only briefly, so there is no deadlock risk, but "takes no lock" is not literally true.
**Fix:** Use `_WRITE_GATES.get(str(path.resolve()))` with no guard. A gate that does not exist is not held. The CPython GIL makes the dict read atomic.

### IN-02: `graph_busy` reports the console's own reads, and `/health`'s, as "in use"

**File:** `databasise/seam/engine.py:2129`; `databasise/stores/probes.py:148`, `:190`
**Issue:** `graph_node_page`, `graph_node_edges` and `probe_graph` each `_ClientRegistry.acquire` the graph, which adds a key to `_entries`. A `GET /info` that runs concurrently with a graph browse or a health probe therefore returns `graph_busy: true` with no write in flight.
**Fix:** Document this in the console copy ("in use, including reads"), or count only holders that are `CozoGraphStore` instances.

### IN-03: An `OSError` on the graph directory gets a different `failure_class` than elsewhere

**File:** `databasise/seam/engine.py:2382-2385`, `:2408-2411` vs `:665-666`
**Issue:** `graph_nodes` and `graph_node` route every `_is_store_error` exception, `OSError`/`PermissionError` included, to `failure_class="StoreCorrupted"`. `_build_stores` maps `OSError` to `StoreFault`. The same unreadable directory therefore answers differently on `/query` and on `/graph/nodes`.
**Fix:** Before the `_is_store_error` branch, add `if isinstance(exc, OSError): raise _foreign_fault(..., failure_class="StoreFault")`.

### IN-04: `next_offset` arithmetic is copied five times instead of using `_next_offset`

**File:** `databasise/seam/engine.py:2213`, `:2247`, `:2354`, `:2386`, `:2412` vs `:515`
**Issue:** The existing SEAM-08 helper `_next_offset` uses `offset + len(rows)`. The new copies use `offset + limit`. Both are correct today, but there are now two rules for one concept, and the copies can drift apart.
**Fix:** Use one helper, e.g. `_page_next(page, total)`, for the five copies.

### IN-05: Preview and promote disagree on a corrupted `ledger.db`

**File:** `databasise/seam/engine.py:2319-2321` vs `:2903`
**Issue:** On a `ledger.db` that is not a database, preview maps `sqlite3.Error` to a 502 `StoreFault`. `promote` builds `Ledger(self.store_root)`, whose `_set_wal` catches only `OperationalError`, so `sqlite3.DatabaseError: file is not a database` escapes `promote` as a 500. The same input therefore gets different statuses on `/promote/preview` and `/promote`. The gap in promote predates this phase. Phase 16 makes it visible.
**Fix:** Wrap `promote()`'s `run_in_executor` call in the same `except sqlite3.Error` mapping to `_foreign_fault("promote", ..., failure_class="StoreFault")`.

### IN-06: Log-tail redaction misses common key shapes

**File:** `databasise/seam/engine.py:2429` (patterns at `databasise/foreign/v1_corpus_adapter.py:60-66`)
**Issue:** The patterns cover `sk-…`, `Bearer …`, `api_key=`/`api-key:` and `?key=`. They do not match `API key: <value>`, which has a space and is a common provider error format, or Google `AIza…` and Voyage `pa-…` keys outside a `key=` query. D-19 relies on "the log never holds env values". The redaction on read is the only defence if that assumption fails.
**Fix:** Add `(?i)(api\s+key\s*[=:]\s*)\S+` and `\bAIza[0-9A-Za-z_-]{20,}`, and add a test that feeds known provider error strings through `log_tail`.

### IN-07: `preview_promotion` best-effort lookup can raise a raw `sqlite3.Error` from inside the outcome-refusal handler

**File:** `databasise/seam/engine.py:2299-2304`
**Issue:** The best-effort `_resolve_operator_preconditions` call catches only `SeamRefusalError`. A `trace.db` fault there escapes as a bare `sqlite3.Error` (500) and hides the outcome `reason` already computed. The prologue's own trace resolution has the same unmapped path in both promote and preview, so the two still agree, but neither returns a named fault.
**Fix:** In the best-effort block, also catch `sqlite3.Error` and degrade to `arm_name = None`. Separately, map `trace.db` errors in `_resolve_operator_preconditions` to `_foreign_fault(..., "StoreFault")`.

---

_Reviewed: 2026-10-22T20:40:37Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: deep_
