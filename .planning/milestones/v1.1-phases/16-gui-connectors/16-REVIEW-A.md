---
phase: 16-gui-connectors
lane: A
reviewed: 2026-10-22T00:00:00Z
depth: deep
diff_base: d608162
files_reviewed: 7
files_reviewed_list:
  - databasise/seam/operator_rest.py
  - databasise/seam/rest.py
  - databasise/launcher/serve_rest.py
  - databasise/launcher/__init__.py
  - databasise/evidence/COVERAGE.md
  - docs/gui/API-INVENTORY.md
  - docs/gui/CODEBASE-MAP.md
findings:
  critical: 0
  warning: 4
  info: 6
  total: 10
status: issues_found
---

# Phase 16: Code Review Report (Lane A: surface, launcher, docs)

**Reviewed:** 2026-10-22
**Depth:** deep (call chains followed into `seam/engine.py`, `seam/trace_store.py`, `stores/probes.py`, `stores/graph.py`, `stores/vector.py`, `ledger/ledger.py`, `seam/floors_store.py` and uvicorn 0.52.4's `Config`)
**Files Reviewed:** 7 (`databasise/launcher/__init__.py` has no diff since d608162; it was read for `is_loopback_host` and `check_engine_arguments`)
**Status:** issues_found

## Summary

Mounting is correct. `create_app` mounts the operator routes only when `operator=True` (rest.py:545-549), and it mounts GET /log only when `log_path is not None` as well. `main` refuses `--operator` with a non-loopback `--host` before `check_engine_arguments`, so `--allow-remote-unauthenticated` cannot bypass the refusal (serve_rest.py:122-126). Each operator route body is one `return await engine.<m>(...)`. The new routes reuse the TrustedHost and Origin guards and CORS without changes. GET /info returns no store_root, URL, model name or key: a probe on a tmp store returned `{version, workspace, clients, write_in_flight, graph_busy}` only. The `log_config` shape matches uvicorn 0.52.4's `LOGGING_CONFIG`: `uvicorn` and `uvicorn.access` get the file handler, and `uvicorn.error` propagates into `uvicorn`. The preview reuses `_promotion_prologue`/`_plan_promotion`, and promote keeps `_plan_promotion` inside `Ledger.transaction()` (engine.py:2903-2906). Paging (`end < total`) is correct on every route, and the degree count treats a self-loop as one edge (probes.py:169, 194-196).

The defects are on the error paths behind the routes. Two new operator routes return a bare 500 on store or file faults, which the phase rule forbids (reproduced). A bad `--log-file` crashes the launcher with a traceback instead of a launcher refusal (reproduced). The log tail limits the number of lines but not the length of each line. The documented and OpenAPI-declared statuses do not match what the routes return.

Tests run (plain pytest, no `-m live`): test_console_surface.py, test_console_log.py, test_console_info.py, test_rest_transport.py and tests/launcher/: 159 passed. Probe script: `/tmp/claude-1000/-home-chris-coding-Databasise-2-0-fully-agnostic-system/32d1701b-4256-409c-a5a7-e305cc822f40/scratchpad/p16/laneA_probe.py`.

## Warnings

### WR-01: GET /traces answers a bare 500 for a corrupted trace row

**File:** `databasise/seam/engine.py:2243-2258` (called from `databasise/seam/operator_rest.py:99-102`; parse at `databasise/seam/trace_store.py:112`)
**Issue:** `list_traces` maps only `sqlite3.Error` to the `StoreFault` fault. `TraceStore.list_page` calls `json.loads(r["run_record"])` on every row, so one truncated or hand-edited `run_record` raises `json.JSONDecodeError`. That error escapes as an unhandled 500 and breaks the console's trace picker for the whole store, not only for that row. A row whose JSON is valid but not an object (for example `[]`) fails the same way at `rec.get(...)` with `AttributeError`. Reproduced: inserting `run_record = '{not json'` into `trace.db` makes `GET /traces` return `500 Internal Server Error`. This breaks the phase rule that a corrupted store is a 502 named fault.
**Fix:**
```python
try:
    rows, total = self._trace_store.list_page(page.limit, page.offset)
except (sqlite3.Error, ValueError) as exc:  # JSONDecodeError is a ValueError
    raise _foreign_fault("list_traces", exc, failure_class="StoreCorrupted") from exc
```
Also check `isinstance(rec, dict)` before projecting, or raise the same fault for a non-object record.

### WR-02: GET /log answers a bare 500 when the log file cannot be opened

**File:** `databasise/seam/engine.py:2421-2431`
**Issue:** `log_tail` checks `Path(path).is_file()`, then calls `open(path)` in `_tail` with no `OSError` handling. A file that exists but cannot be read (mode 000, an ACL, a root-owned file after an earlier `sudo` launch) passes the `is_file()` check and raises `PermissionError`, so the response is an unhandled 500. A file removed or rotated between the check and the open raises `FileNotFoundError`, also a 500. Reproduced: `chmod 0` on the log file makes `GET /log` return `500 Internal Server Error`. The route is meant to diagnose 500s, so it should not produce one.
**Fix:**
```python
try:
    return {"lines": await asyncio.to_thread(_tail)}
except FileNotFoundError:
    return {"lines": []}
except OSError as exc:
    raise _foreign_fault("log_tail", exc, failure_class="StoreFault") from exc
```

### WR-03: A bad --log-file crashes the launcher with a traceback after it takes the store lock

**File:** `databasise/launcher/serve_rest.py:135-146` (with `log_config_for` at 90-111)
**Issue:** `--log-file` is never validated. `uvicorn.run` builds `Config`, which calls `configure_logging()` and then `logging.config.dictConfig` inside `Config.__init__` (uvicorn/config.py:297, 392). A path whose parent directory is missing, a directory path, `--log-file ''` (which becomes `Path('.')`) or an unwritable path raises `ValueError: Unable to configure handler 'file'`. Reproduced with `dictConfig(log_config_for(tmp/"missing-dir"/"server.log"))`. That error is not in `LAUNCH_REFUSALS` and is raised outside the `refuse()` path, so the operator gets a raw Python traceback instead of a `databasise: ...` line and exit code 1. The traceback comes after the store lock is acquired and the clients are built from the env file. The `finally` does release the lock, but every other launch failure in this module is a named one-line refusal (RUN-05).
**Fix:** validate before `open_engine`, next to the CORS check:
```python
if args.log_file is not None:
    try:
        with open(args.log_file, "a", encoding="utf-8"):
            pass
    except OSError as exc:
        parser.error(f"--log-file {args.log_file} cannot be opened for append: {exc.strerror}")
```

### WR-04: OpenAPI and API-INVENTORY document statuses the routes never return and omit the faults they do return

**File:** `databasise/seam/operator_rest.py:89-143`, `docs/gui/API-INVENTORY.md:768-775`
**Issue:** `_OPERATOR_STORE_RESPONSES` declares `409 StoreBusyError` on /ledger/aliases, /ledger/history, /traces, /promote/preview, /chunks and /log. Only `graph_nodes` and `graph_node` can raise `StoreBusyError` (engine.py:2379-2381, 2403-2405). The ledger reads map every sqlite error, including "database is locked", to `ForeignEngineRefusalError(failure_class="StoreFault")`, which is a 502 (engine.py:2192-2193, 2235-2236). `log_tail` raises no refusal. API-INVENTORY.md:768 then lists `StoreBusyError 409` as the named refusal for `GET /ledger/aliases`, which that route never returns, and it omits the 502 that the route does return. The table also leaves out the StoreFault 502 on /ledger/history, /traces and /promote/preview and the StoreCorrupted 502 on /graph/node. The Phase 17/18 console builds its error banners from this table and from OpenAPI, so it would handle a 409 that never arrives and miss the 502.
**Fix:** declare `_FAULT_RESPONSES` on the ledger, trace, preview and chunk routes, and `_OPERATOR_STORE_RESPONSES` on the two graph routes only. Declare nothing extra on /log. In API-INVENTORY.md change line 768 to "the `StoreFault` fault (502)". Add "the `StoreFault` fault" to the /ledger/history, /traces and /promote/preview rows, and "the `StoreCorrupted` fault" to the /graph/node row.

## Info

### IN-01: GET /log bounds the line count but not the line length

**File:** `databasise/seam/engine.py:2425-2429`
**Issue:** `deque(handle, maxlen=limit)` caps the number of lines at 1000, but each line keeps its full length, and the redaction regexes run over the whole line. `log_config_for` sets the root logger to INFO (serve_rest.py:110), so third-party INFO records now reach the file. Any single-line record that embeds a large payload (a repr of a run record or an LLM response, a long v1 stderr tail) is returned whole, so the response size has no fixed bound. This is Info rather than Warning because uvicorn caps request lines and `_foreign_fault` trims v1 stderr to 2000 characters, so no current producer of very long lines was found.
**Fix:** truncate each line after redaction, for example `line[:4096]`, and add a `shortcut:` comment that states the cap.

### IN-02: With --log-file, engine warnings and faults stop reaching stderr, and the file on disk is not redacted

**File:** `databasise/launcher/serve_rest.py:110`
**Issue:** `config["root"] = {"handlers": ["file"], ...}` gives root a handler, so `logging.lastResort` no longer prints the engine's WARNING records to the terminal. With `--log-file`, `_foreign_fault` tracebacks and "graph store busy" warnings appear only in the file. The `--log-file` help text does not say so. Redaction runs only when GET /log reads the file (engine.py:2429). Third-party lines are written unredacted, and the file gets default umask permissions (usually 0644).
**Fix:** add `"default"` to the root handlers so stderr still gets warnings, or state the behaviour in the `--log-file` help text. Consider `os.umask`/`chmod 0o600` on the log file.

### IN-03: The write_in_flight read takes a lock and inserts into a shared dict, which its docstring says it does not

**File:** `databasise/seam/engine.py:2120-2135` (via `_gate_for`, engine.py:850-852)
**Issue:** The docstring says "Neither read takes a lock", and the phase rule is that store-busy flags take no lock. `_gate_for` acquires the process-global `_WRITE_GATES_GUARD`, runs `Path.resolve()` (filesystem syscalls) while holding it, and `setdefault`s a new `threading.Lock` into `_WRITE_GATES` for every workspace that /info polls. The guard is held only briefly, so nothing blocks today. The documented property is still false.
**Fix:** read without inserting: `gate = _WRITE_GATES.get(str(path.resolve())); return gate is not None and gate.locked()`. A single dict `get` needs no guard under the GIL.

### IN-04: GET /traces runs its full-table sort on the event loop

**File:** `databasise/seam/engine.py:2243-2244`
**Issue:** The new ledger, chunk and graph reads all run in `asyncio.to_thread`. `list_traces` calls `list_page` inline, which runs `ORDER BY created_at DESC` with no index (the shortcut at trace_store.py:106) plus `COUNT(*)`. On a large `trace.db`, every GET /traces stalls every other request, including the /info busy flags the console polls during a write. The `TraceStore` connection is bound to its thread (`check_same_thread`), which explains the inline call, but the shortcut comment does not mention that the sort blocks the event loop.
**Fix:** extend the shortcut comment to say the sort blocks the event loop, or open a per-call read-only connection inside `to_thread`, as `Ledger.open_existing` does.

### IN-05: API-INVENTORY rows keep stale facts beside the new "Built as" notes

**File:** `docs/gui/API-INVENTORY.md:713, 741, 842`
**Issue:** Line 713 still says the no-enumeration rule is at `selectors.py:259-263`; 16-CONTEXT says the correct citation is `selectors.py:281-302`. It also says "`LedgerRecord` has no `id`/`created_at` ... read raw rows", but `Ledger.aliases()` now projects `LedgerEntry`. Line 741 still says "30 `SeamRefusalError` subclasses" and "`refusals.__all__` misses `NoRawUploadPathForModalityError`". The committed `docs/gui/refusals.json` has 51 entries, all in `__all__`. Line 842 repeats the old selectors citation. A row that now ends in "Built as ..." contradicts itself.
**Fix:** update the counts and citations in those rows, or strike the superseded clauses.

### IN-06: COVERAGE.md says wiring identities appear only on the operator surface

**File:** `databasise/evidence/COVERAGE.md:136-137`
**Issue:** "Wiring names, `wiring_id`, `arm`, `mutation_class` and aliases appear only on the `--operator` surface." The same bullet names the `debug=true` precedent on `/trace/resolve`, which returns `wiring_id`/`arm_id` on the default app without `--operator` (16-CONTEXT D-02). Aliases are also consumer input on every selector-bearing route. The statement is not accurate as written.
**Fix:** "...are listed or derived only on the `--operator` surface. `/trace/resolve` with `debug=true` on the default app remains the earlier exception."

---

_Reviewed: 2026-10-22_
_Reviewer: Claude (gsd-code-reviewer), lane A_
_Depth: deep_
