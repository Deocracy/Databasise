---
phase: 10-stores-locking-data-integrity
fixed_at: 2026-10-17T00:00:00Z
review_path: .planning/phases/10-stores-locking-data-integrity/10-REVIEW.md
iteration: 1
findings_in_scope: 11
fixed: 11
skipped: 0
status: all_fixed
---

# Phase 10: Code Review Fix Report

**Fixed at:** 2026-10-17
**Source review:** .planning/phases/10-stores-locking-data-integrity/10-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 11 (CR-01, WR-01 to WR-10)
- Fixed: 11
- Skipped: 0

Edits were made in the main checkout (`workflow.use_worktrees=false`), so there is no worktree or
recovery sentinel to clean up. Verification ran in the main checkout, so the numbers below are
reproducible from the tree. Each fix has a regression test; the tests were run against the unfixed
source (via `git checkout --` of the source file) and failed for the stated reason before the fix.
No protected test file was edited.

**Verification (main checkout, after the last commit):**
- `cd databasise && .venv/bin/pytest -q tests/stores tests/seam tests/mcp tests/parity tests/runner`: 1186 passed, 1 skipped, 3 deselected, exit 0.
- `.venv/bin/python tools/check_offline_suite.py`: 1844 passed, 1 skipped, 4 deselected (both runs), exit 0.

## Fixed Issues

### CR-01: A store fault inside a query node returned 200 with the store path in the envelope

**Files modified:** `databasise/seam/engine.py`, `databasise/runner/scheduler.py`, `databasise/tests/seam/test_query_store_fault.py` (new)
**Commit:** fa4dcfe
**Applied fix:** `_execute_resolved` now raises `ForeignEngineRefusalError` before any envelope is built when a node exception is a store error (`_is_store_fault`): `failure_class="StoreCorrupted"` for `VectorStoreCorruptedError`, `"StoreFault"` otherwise; the cause is logged once by `_foreign_fault`. Every other node exception keeps the degraded envelope, but the scheduler's `stop_reason` (and so `degradation_reason` and the non-debug trace fields) is now `node '<id>': NodeExecutionError: <ExceptionClassName>` with no message text. The full text stays in the debug-only node trace (`cross_process_failure_cause`). Tests: corrupted vector index gives `StoreCorrupted`, a sqlite error gives `StoreFault`, a `RuntimeError` carrying the store path degrades with the class name only and the path absent from the envelope and the non-debug trace.
**Deferred (per orchestrator ruling):** the node id still appears in `stop_reason` (`node 'dpr-fallback': ...`). Node-free consumer text is WIRE scope in Phase 13 and is not reworked here.
**Status:** fixed (logic fix; human verification of the classification boundary is advisable)

### WR-01: Registry release closed the client outside the lock

**Files modified:** `databasise/stores/graph.py`, `databasise/tests/stores/test_graph_registry_close_race.py` (new)
**Commit:** 69c12d5
**Applied fix:** `_ClientRegistry.release` now calls `entry.client.close()` while holding the registry lock, so a concurrent `acquire` waits for RocksDB to drop its LOCK instead of opening a second client. Test forces a 0.5 s close and acquires 0.1 s later; it raised `GraphStoreBusyError` before the fix and opens cleanly after.

### WR-02: Proxy exposed `_target`, `_mode` and private store attributes

**Files modified:** `databasise/parts_core/__init__.py`, `databasise/tests/runner/test_scheduler.py`, `databasise/tests/parity/test_storage_audit.py`, `databasise/tests/runner/test_store_proxy_hardening.py` (new)
**Commit:** 5ab853c
**Applied fix:** `_StoreProxy` now overrides `__getattribute__`, `__setattr__` and `__delattr__`. Any single-underscore name (its own `_target`/`_mode`/`_kind`/`_declared`, or the target's `_conn`, `_client`, `_children`, ...) raises `UndeclaredEffectError`; assignment and deletion raise; dunder names resolve normally so `isinstance`/`repr` still work. Internals use `object.__getattribute__`. Added module-level `unwrap_store_handle(proxy)` in `parts_core` (docstring: for tests and engine only) and switched test_scheduler.py and test_storage_audit.py to it.

### WR-03: `delete_document` committed staged writes on `not_allowed`

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/stores/test_delete_status_commit.py` (new)
**Commit:** 1fc183f
**Applied fix:** commit only when `status in ("success", "not_found")`; `not_allowed`, `fail` and any other status drop pending ops. Tests: `not_allowed` leaves kv, vector and graph records intact; `success` and `not_found` commit.
**Status:** fixed (logic fix; human verification advisable)

### WR-04: Vector abort unlinked a shared `.tmp` pair; engine dropped outside the flush lock

**Files modified:** `databasise/stores/vector.py`, `databasise/seam/engine.py`, `databasise/tests/seam/test_concurrent_ingest_failure.py` (new)
**Commit:** 2f92fec
**Applied fix:** `FaissVectorStore` keeps a per-instance `_staged` flag (set when it writes the pair, cleared on commit or on its own abort); `abort_prepared` unlinks the pair only if the flag is set. `_drop_pending(stores, store_root)` now runs under `_flush_lock(store_root)` at all three call sites. Tests: a store-level test (an unrelated instance's drop does not break another's commit; it raised `FileNotFoundError` before) and an engine-level test with a failing ingest concurrent with a successful one that leaves the successful one's vectors committed and no `.tmp` behind.
**Note:** `_drop_pending` gained a required second parameter. No caller outside engine.py exists in the readable test directories; the full suite passes.

### WR-05: Snapshot load reported false corruption and let raw read errors escape

**Files modified:** `databasise/stores/vector.py`, `databasise/tests/stores/test_vector_snapshot_robustness.py` (new)
**Commit:** 37e3b17 (shared with WR-06, same file and one test module)
**Applied fix:** `load_committed` retries until two consecutive stats match, capped at 3 attempts (`_SNAPSHOT_ATTEMPTS`). A `FileNotFoundError` between stat and read counts as a changed stat; if it persists the namespace is absent (`None`). If the last read passed checksum validation but the stat kept changing, the snapshot is returned uncached; `VectorStoreCorruptedError` is raised only if the last read itself failed validation or the pair stays half-present. `_read_snapshot` wraps `OSError`, `ValueError` (including `JSONDecodeError`), `KeyError`, `TypeError`, `AttributeError` and `RuntimeError` into `VectorStoreCorruptedError`, so a garbage sidecar reaches the seam as `StoreCorrupted` (502). Tests cover each branch, including a garbage sidecar through `resolve_evidence`.
**Status:** fixed (logic fix; human verification advisable)

### WR-06: Cached snapshot entries were mutable through a reader

**Files modified:** `databasise/stores/vector.py`, `databasise/tests/stores/test_vector_snapshot_robustness.py`
**Commit:** 37e3b17
**Applied fix:** `get_by_id`, `query`, `score_all` and `self_knn` return `copy.deepcopy(entry["metadata"])`. Measured 19 ms for 10,000 small entries, so the deep copy is kept. Test mutates nested lists and dicts in every result shape and checks a second reader.

### WR-07: Health created files and reported `ok` for an empty `graph.cozo`

**Files modified:** `databasise/stores/probes.py`, `databasise/tests/stores/test_probe_hardening.py` (new)
**Commit:** 2d075e9
**Applied fix:** `probe_graph` requires `graph.cozo/data/CURRENT` naming an existing `MANIFEST-*` file (checked under the registry lock so a first open in progress is not misread) before it acquires a client; otherwise it reports `corrupted` for an existing path and `absent` for a missing one, and never opens a client. The blind `except` is replaced by `_is_store_error` (OS errors including `PermissionError`, sqlite, value/runtime/key errors, pycozo's bare `Exception` and `pycozo.*` types); programming errors surface. `probe_vector` catches `(VectorStoreCorruptedError, OSError)`. A zero-byte `kv.sqlite3` is now `absent` (a valid empty database), the review's third bullet. Tests assert zero files created for the empty directory, `data/` without `CURRENT`, garbage `CURRENT`, garbage file, zero-byte kv, and through `Databasise.health()`.
**Accepted, unchanged:** IN-04 (RocksDB file rotation when probing a populated graph).

### WR-08: A corrupt kv or graph store failed at open with a raw 500

**Files modified:** `databasise/seam/engine.py`, `databasise/stores/kv.py`, `databasise/tests/seam/test_store_open_faults.py` (new)
**Commit:** f26faf1
**Applied fix:** `_build_stores` gained `operation=` and wraps all three constructors: `sqlite3.Error`, `VectorStoreCorruptedError` or a bare `Exception` (pycozo's native open, recognised by origin) becomes `ForeignEngineRefusalError(StoreCorrupted)`; an `OSError` becomes `StoreFault`; other exceptions propagate. `GraphStoreBusyError` handling is unchanged. The three call sites pass `"ingest"`, `"delete"` and `"query"`. `SqliteKVStore.__init__` closes its connection when the open fails. Tests cover corrupt kv and corrupt graph on query, ingest and delete, and assert nothing is left held.

### WR-09: Graph stores left open, raw Client on a registry path

**Files modified:** `databasise/parity/run_cross_modality.py`, `databasise/parity/import_index.py`, `databasise/parity/build_hipporag_index.py`, `databasise/parity/run_comparison.py`, `databasise/parity/storage_audit.py`, `databasise/tests/parity/test_store_leaks.py` (new), `databasise/tests/stores/test_probe_hardening.py` (registry assertion scoped to the test's own root)
**Commit:** 5470867
**Applied fix:** `_resolved_store_dirs` computes the directories from the declared namespaces without opening any store. `_import_graph`, `_import_text_chunks` and `verify_import`'s kv store finalize in `try/finally`. `_v2_graph` reads through `_ClientRegistry.acquire`/`release` instead of a raw `CozoClient`. `build_index`, `_run_decomposed_arm` and `run_audit` build stores inside the `try` with `into=`. Tests include `_resolved_store_dirs` followed by import and verify in one process (it failed with RocksDB "lock hold by current process" before), a failing graph import, kv finalize accounting, and a `_build_stores` that opens one store then fails for each of the three harnesses.

### WR-10: Graph staging tests passed without the behaviour

**Files modified:** `databasise/tests/stores/test_graph_staging.py` (new), `databasise/tests/seam/test_ingest_abort.py`
**Commit:** 76c17a1
**Applied fix:** new tests assert `_prepared_mt is not None` after `prepare`, that a second reader does not see the writes before `commit_prepared`, that commit still lands the writes after the buffers are cleared (so the data is in the transaction, not flushed at commit), that `abort_prepared` after a real prepare commits nothing (second reader and a reopened store), and that an unserializable attribute fails at `prepare`. Mutation check: with `prepare` a no-op, and with `prepare` a no-op plus a flushing `commit_prepared`, all three new tests fail. `test_a_successful_hipporag_ingest_still_commits` now asserts the HippoRAG graph committed.

## Skipped Issues

None.

## Deferred and not changed

- Node ids in consumer-visible `stop_reason` (CR-01 ruling): node-free consumer text is WIRE scope in Phase 13.
- IN-01 to IN-07: out of the `critical_warning` scope; IN-04 was accepted by the orchestrator.

## Notes for the verifier

- WR-05 and WR-06 share one commit (37e3b17) because both change `stores/vector.py` and share one test module; splitting would have required partial staging.
- The registry (`_ClientRegistry`) is process-wide, so leak assertions in the new tests are scoped to each test's own `store_root`.
- `tools/check_offline_suite.py` ran the whole offline suite (1844 passed) in addition to the five requested directories.

---

_Fixed: 2026-10-17_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
