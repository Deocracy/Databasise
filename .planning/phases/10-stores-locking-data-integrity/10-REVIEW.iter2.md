---
phase: 10-stores-locking-data-integrity
reviewed: 2026-10-17T00:00:00Z
depth: standard
iteration: 2
files_reviewed: 63
files_reviewed_list:
  - databasise/launcher/gc_namespaces.py
  - databasise/namespaces.py
  - databasise/parity/build_hipporag_index.py
  - databasise/parity/import_index.py
  - databasise/parity/run_arm.py
  - databasise/parity/run_comparison.py
  - databasise/parity/run_cross_modality.py
  - databasise/parity/storage_audit.py
  - databasise/parts_core/__init__.py
  - databasise/parts_core/codebase_memory_mcp.py
  - databasise/parts_core/hipporag/graph_augment_persist.py
  - databasise/parts_core/lightrag/full_delete.py
  - databasise/parts_core/lightrag/full_ingest.py
  - databasise/runner/scheduler.py
  - databasise/seam/corpus.py
  - databasise/seam/engine.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/stores/base.py
  - databasise/stores/graph.py
  - databasise/stores/kv.py
  - databasise/stores/probes.py
  - databasise/stores/vector.py
  - databasise/validator/errors.py
  - databasise/validator/parse.py
  - databasise/tools/check_import_boundary.py
  - databasise/tests/parity/test_storage_audit.py
  - databasise/tests/parity/test_store_leaks.py
  - databasise/tests/runner/test_capability_scoping_modes.py
  - databasise/tests/runner/test_scheduler.py
  - databasise/tests/runner/test_store_proxy_hardening.py
  - databasise/tests/seam/test_build_stores_cleanup.py
  - databasise/tests/seam/test_concurrent_ingest_failure.py
  - databasise/tests/seam/test_corpus_status.py
  - databasise/tests/seam/test_evidence_resolve_stores.py
  - databasise/tests/seam/test_health_probe.py
  - databasise/tests/seam/test_ingest_abort.py
  - databasise/tests/seam/test_query_store_fault.py
  - databasise/tests/seam/test_refusal_status_codes.py
  - databasise/tests/seam/test_rest_transport.py
  - databasise/tests/seam/test_store_open_faults.py
  - databasise/tests/seam/test_store_refusal_status.py
  - databasise/tests/stores/test_delete_commit_contract.py
  - databasise/tests/stores/test_delete_status_commit.py
  - databasise/tests/stores/test_graph_delete_cascade.py
  - databasise/tests/stores/test_graph_lock.py
  - databasise/tests/stores/test_graph_registry_close_race.py
  - databasise/tests/stores/test_graph_staging.py
  - databasise/tests/stores/test_kv_buffer_isolation.py
  - databasise/tests/stores/test_prepared_commit.py
  - databasise/tests/stores/test_probe_hardening.py
  - databasise/tests/stores/test_vector.py
  - databasise/tests/stores/test_vector_crash_window.py
  - databasise/tests/stores/test_vector_reserved_keys.py
  - databasise/tests/stores/test_vector_snapshot_robustness.py
  - databasise/tests/stores/test_vector_validation.py
  - databasise/tests/test_embed_startup.py
  - databasise/tests/test_namespaces_gc.py
  - databasise/tests/test_phase_success_criteria.py
  - databasise/tests/test_removed_stores_absent.py
  - databasise/tests/validator/test_taint_conformance.py
  - databasise/tests/wirings/__init__.py
  - databasise/tests/wirings/test_store_effects_wired.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 10: Code Review Report (iteration 2)

**Reviewed:** 2026-10-17
**Depth:** standard
**Files Reviewed:** 63
**Status:** issues_found

## Summary

Scope: the iteration-1 file list plus the 13 files the fix commits fa4dcfe..76c17a1 added or changed
(25 files in `git diff --name-only 57c1961 HEAD -- databasise/`). The review concentrated on the diff
and its call paths; files the fixes did not touch were not re-read line by line. The 227 tests in the
fix-related suites pass (`tests/stores`, the new seam, runner and parity tests). Every finding below
marked "probe" was reproduced with a script in the session scratchpad; no repo file was changed.

### Iteration-1 findings

| Id | Status | Note |
|----|--------|------|
| CR-01 | Resolved | A store error from a query node is now 502 `StoreFault` or `StoreCorrupted`. `stop_reason` carries the class name only. See IN-01 for classification limits. |
| WR-01 | Resolved | `close()` runs under the registry lock. Re-entrancy checked: `acquire` and `release` never nest. |
| WR-02 | Partly resolved | The named attributes (`_target`, `_mode`, `_conn`, `_children`) are closed and pickling is blocked. Other routes remain (WR-04 below). |
| WR-03 | Resolved | |
| WR-04 | Resolved | `_staged` flag plus `_drop_pending` under the flush lock. No deadlock (see answer 4). |
| WR-05 | Partly resolved | Retries, uncached-valid return and the wrapping of read errors work. The vanish path still returns `None` (WR-01 below). |
| WR-06 | Resolved | Deep copies on every result shape; probe confirmed no cross-reader leak. |
| WR-07 | Partly resolved | Empty directory, garbage `CURRENT` and zero-byte kv are fixed. Two inputs still create files and one raises (WR-02, WR-03 below). |
| WR-08 | Resolved | Corrupt MANIFEST probe: `StoreCorrupted`, no raw error. |
| WR-09 | Resolved | No remaining graph open without a finalize (see answer 5). |
| WR-10 | Resolved | The new tests passed here. I did not repeat the author's mutation runs. |

### Answers to the six focus questions

1. **Snapshot cache: refuted in part, confirmed in part.** The automated review is right that
   `load_committed` returns `None` after the retries run out (probe: `P1a` returns `None` when
   `_read_snapshot` raises `FileNotFoundError` on every attempt while both files stat as present). It is
   also right that `snapshot = error = None` at the top of every iteration discards an earlier
   corruption error (probe `P1b`: attempt 1 is a checksum failure with a changed stat, attempts 2 and 3
   vanish, result `None`). Your rule (absent only when one stat shows both files missing) is therefore
   violated. See WR-01. What is not a problem: a read that passed validation but saw a changing stat is
   returned uncached; a failed read on the last attempt raises; a half-present pair on every attempt
   raises. `return None` at line 251 is reachable only through the vanish path, so the fix is to
   raise there.
2. **CR-01 boundary.** Counted as store faults: `sqlite3.Error`, and any exception whose type is
   defined in a module starting with `databasise.stores` or `pycozo` (`_is_store_fault`). Degrading
   (200, partial, class name only): everything else, including `OSError`, faiss `RuntimeError` and
   `UndeclaredEffectError`. No shipped part wraps a store error: parts_core has no `raise ... from`, no
   `TaskGroup` or `gather`, and `dispatch` calls the body directly, so a store error reaches
   `node_exceptions` unwrapped. `_is_store_fault` inspects only the top-level type, so a wrapped or
   grouped store error would degrade. No exception message text reaches `stop_reason`,
   `degradation_reason` or the non-debug trace; the debug trace still carries
   `cross_process_failure_cause` with full text, as intended. See IN-01.
3. **WR-02 proxy.** Still reachable: `proxy.<allowed method>.__self__`, `type(proxy)._target.__get__(proxy)`,
   `proxy.__init__.__globals__`, the public `unwrap_store_handle`, `object.__setattr__(proxy, "_mode", "w")`,
   and `ctx.stores._scoped._raw_stores`. Blocked (probe): `_target`, `vars()`, `__dict__`, pickle,
   `copy.copy`, `__reduce_ex__`, `__getstate__`. See WR-04.
4. **WR-04 locking.** No deadlock. The three `_drop_pending` call sites (ingest line 1019, delete lines
   1167 and 1174) are outside `async with _flush_lock`; `_commit_all` aborts through `_abort_prepared`,
   which takes no lock. `asyncio.Lock` is not re-entrant, so a future `_drop_pending` call from inside
   `_commit_all` would hang. Since `_staged` is per instance, the lock is no longer needed for
   correctness; it is harmless.
5. **WR-09.** No `_build_stores` or `CozoGraphStore` open remains outside a try with a finalize. Checked
   `seam/engine.py` (3 sites), `parity/run_arm.py`, `build_hipporag_index.py`, `run_comparison.py`,
   `storage_audit.py`, `import_index.py`. The only unfinalized store is a kv store in
   `databasise/__init__.py:76` (IN-03).
6. **WR-07.** Yes, health can still create files, and one input makes it raise (WR-02, WR-03).

## Warnings

### WR-01: `load_committed` reports a namespace as absent when its files exist but vanish mid-read

**File:** `databasise/stores/vector.py:210-251`; pinned by `databasise/tests/stores/test_vector_snapshot_robustness.py:105-113`
**Issue:** If `_read_snapshot` raises `FileNotFoundError` on all three attempts after both stats
succeeded, the loop ends with `snapshot is None` and `error is None`, and line 251 returns `None`. The
caller then treats the namespace as empty:
- `FaissVectorStore._read_committed` sets an empty index; `prepare()` re-reads, gets `None` again,
  builds a fresh index from the pending buffer and `os.replace`s it over the existing pair. That is
  data loss for the namespace.
- A read path serves empty results; health reports `absent`.

The `error = None` reset on each iteration also drops a checksum failure seen on an earlier attempt
(probe `P1b`). The existing test asserts the `None` outcome, so it protects the bug.
Reaching this needs three consecutive vanish events with both files present at stat time, so it is rare
(a store being dropped or replaced while read). It still breaks the rule that absent means both stats
missing, and the consequence is a silent overwrite. Separately, `_stat_signature` catches only
`FileNotFoundError`: a `PermissionError` or `NotADirectoryError` from `stat` escapes
`load_committed` raw (probe: `chmod 000` on the namespace directory raises `PermissionError`), and
`resolve_evidence` and the query nodes do not map it.
**Fix:**
```python
for _attempt in range(_SNAPSHOT_ATTEMPTS):
    snapshot = None                       # keep `error` across attempts
    ...
    try:
        snapshot = _read_snapshot(index_path, meta_path, signature)
    except FileNotFoundError:
        error = VectorStoreCorruptedError(index_path, None, "<vanished while being read>")
        continue
    except VectorStoreCorruptedError as exc:
        error = exc
    ...
if snapshot is not None:
    return snapshot
raise error   # every path out of the loop without a return sets `error`
```
Change `test_a_file_that_keeps_vanishing_means_the_namespace_is_absent` to expect
`VectorStoreCorruptedError`. In `_stat_signature`, catch `OSError` other than `FileNotFoundError` and
raise `VectorStoreCorruptedError(path, None, "<unreadable: ...>")`.

### WR-02: Health raises a bare `ValueError` for every existing kv store when `store_root` is relative

**File:** `databasise/stores/probes.py:50`; reachable from `databasise/seam/engine.py:1268-1274`, `databasise/launcher/__init__.py:45`
**Issue:** `probe_kv` builds the sqlite URI with `db_path.as_uri()`, which raises
`ValueError: relative path can't be expressed as a file URI` for a relative path. `--store-root` is
`type=Path` with no `resolve()`, and `Databasise.__init__` keeps `Path(store_root)` as given. The
`ValueError` is not caught by `except (sqlite3.Error, OSError)`, and `health()` wraps nothing, so
`GET /health` fails with a 500 for `--store-root ./stores` once any `kv.sqlite3` exists. Probe:
`probe_kv(Path("w/t"))` raised `ValueError`. WR-07's stated rule was that programming errors surface;
this is a deployment input, and health is the call that must not raise for a store state. The code
dates from c64ac1a and iteration 1 did not flag it.
**Fix:** `db_path = (Path(dir_path) / "kv.sqlite3").resolve()` at the top of `probe_kv` (and the same
for `probe_graph`'s `db_path`, which already resolves for the key). Add a health test with a relative
`store_root`.

### WR-03: Health still creates files for two inputs, against STOR-04

**File:** `databasise/stores/probes.py:49-50` (kv), `databasise/stores/probes.py:84-102` (graph)
**Issue:**
- kv: `wal_open` is true whenever `kv.sqlite3-wal` exists, and the probe then opens `?mode=ro`. SQLite
  creates `-shm` even for a read-only connection. A database restored from a backup or left by a crash
  without its `-shm` therefore gains a file on every cold health call. Probe: a copy of
  `kv.sqlite3` plus `kv.sqlite3-wal` returned `ok` and created `kv.sqlite3-shm`.
- graph: for a valid RocksDB directory whose `graph.cozo/manifest` file is missing, the probe returned
  `ok` and created `graph.cozo/manifest`, plus the usual `data/` rotation. The module docstring says the
  open touches "nothing outside" `data/`; that is false for this input. With `data/LOCK` missing the
  probe creates it (also inside `data/`, so within the accepted IN-04 behaviour).

The populated-graph `data/` rotation (000010.sst, new MANIFEST, OPTIONS, `LOG.old.*`) is the accepted
IN-04 and is not re-reported.
**Fix:** kv: use `immutable=1` unless both `-wal` and `-shm` exist (`live = wal.exists() and
shm.exists()`). graph: also require `graph.cozo/manifest` in `_rocksdb_marker_present`, and correct the
docstring. Add before/after tree-comparison tests for a wal-without-shm copy and a missing manifest.

### WR-04: The proxy and scope layers still hand a part the raw store through ordinary Python attributes

**File:** `databasise/parts_core/__init__.py:104-152`, `databasise/runner/scheduler.py:259-283`
**Issue:** The WR-02 fix closes the slot names, but the guarantee "no part can reach the raw store or
upgrade a read proxy" still fails (probe, read proxy on a kv store):
- `proxy.get_by_id.__self__` returns the raw `SqliteKVStore` (`getattr(target, name)` hands back a bound
  method).
- `type(proxy)._target.__get__(proxy)` returns it (the slot descriptor is a class attribute; dunder
  `__class__` is allowed).
- `proxy.__init__.__globals__["unwrap_store_handle"](proxy)` returns it.
- `unwrap_store_handle` is public and exported in `__all__`; any part can import it.
- `object.__setattr__(proxy, "_mode", "w")` upgrades the proxy; after that `proxy.upsert` resolves.
- `ctx.stores._scoped._raw_stores["graph"]` bypasses the proxy entirely: `_ScopedStoresView` and
  `CapabilityScopedStores` keep the raw dict in ordinary attributes.

In-process Python cannot be sealed against code that tries; the realistic aim is to stop accidental
misuse, and the fix achieves that for the direct attribute names. But the review's own risk statement
(D-09's "engine-only on every handle") is stronger than that, and the tests now assert only the named
routes, so the claim in the commit message and the docstring over-states what is enforced.
**Fix:** Pick one of two. Either state the threat model in the `_StoreProxy` docstring (accidental
misuse only, not hostile part code) and remove `unwrap_store_handle` from `__all__`, or harden the cheap
routes: return `lambda *a, **kw: attr(*a, **kw)` instead of the bound method, keep `_raw_stores` and
`_scoped` out of instance attributes (closure or name-mangled with `__slots__`), and refuse every dunder
name except `__class__`, `__repr__` and `__eq__`. Add a test that `proxy.get_by_id.__self__` is not the
raw store.

## Info

### IN-01: `_is_store_fault` classifies by module and top-level type only

**File:** `databasise/seam/engine.py:278-282`, `databasise/seam/engine.py:445-452`, `databasise/seam/engine.py:1354-1359`
**Issue:** Three consequences, none shipping a wrong answer today:
- `InvalidTopKError`, `ReservedMetadataKeyError` and `VectorNamespaceNotSelectedError` are defined under
  `databasise.stores`, so a wiring with `top_k: 0` or a part that forgets `select()` now returns 502
  `StoreFault` on the query path instead of a degraded envelope. That is a wiring or part defect, not a
  store fault.
- A store error wrapped by a part (`raise X from store_error`) or raised from inside an
  `ExceptionGroup` is not recognised. No shipped part does either.
- `_build_stores` recognises pycozo's bare `Exception` by exact type, but not `pycozo.client.QueryException`
  (what `_ensure_relations` re-raises for any non-"already exists" failure), which would escape as a
  raw 500. I could not produce one: a corrupt MANIFEST raises the bare `Exception` (probe, now
  `StoreCorrupted`).
**Fix:** In `_build_stores` use `_is_store_fault(exc)` in place of `type(exc) is Exception` and add the
`QueryException` case. For the first item, exclude the three input-validation classes from
`_is_store_fault` (or give them a shared marker base) so they keep degrading.

### IN-02: `hasattr`, `getattr(..., default)` and `copy` raise `UndeclaredEffectError` instead of `AttributeError`

**File:** `databasise/parts_core/__init__.py:121-126`
**Issue:** For any single-underscore name the new `__getattribute__` raises `UndeclaredEffectError`, a
`PermissionError`. `hasattr(proxy, "_x")` and `getattr(proxy, "_x", None)` therefore raise instead of
returning `False` or the default, and any library that probes for `_is_coroutine`-style markers on a
handle will fail. No shipped part does this, so no test fails.
**Fix:** Make the error for `_`-prefixed names also an `AttributeError`
(`class _PrivateAttribute(UndeclaredEffectError, AttributeError)`), or raise `AttributeError` there.

### IN-03: The tracer composer opens a kv store with no finalize on error

**File:** `databasise/__init__.py:75-100`
**Issue:** `run_wiring` in the package root opens a `SqliteKVStore`, awaits `_scheduler.run_wiring`, and
finalizes only on the success and cycle paths. A `WiringRefusedError` or a cancelled run leaves the
sqlite connection open until garbage collection. Kv only, no graph client, so it is not the WR-09 class.
**Fix:** `try: ... finally: for store in stores.values(): await store.finalize()`.

### IN-04: An unreadable snapshot reports itself as a checksum mismatch in the log

**File:** `databasise/stores/vector.py:191`, `databasise/stores/vector.py:91-100`
**Issue:** `_read_snapshot` wraps read errors as `VectorStoreCorruptedError(index_path, None,
"<unreadable: JSONDecodeError>")`, whose message then says "sidecar recorded index_checksum None, but
the on-disk index file's actual checksum is '<unreadable: JSONDecodeError>'". The text goes only to the
server log (the refusal body names the failure class), but it misleads whoever reads it.
**Fix:** Give `VectorStoreCorruptedError` an optional `reason` argument and use it in the message when
the failure is not a checksum comparison.

---

_Reviewed: 2026-10-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 2_
