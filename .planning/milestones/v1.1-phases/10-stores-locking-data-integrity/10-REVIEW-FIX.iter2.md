---
phase: 10-stores-locking-data-integrity
fixed_at: 2026-10-17T00:00:00Z
review_path: .planning/phases/10-stores-locking-data-integrity/10-REVIEW.md
iteration: 2
findings_in_scope: 6
fixed: 6
skipped: 0
status: all_fixed
---

# Phase 10: Code Review Fix Report

**Iteration 1 (summary):** fixed CR-01 and WR-01 to WR-10 (11 of 11, commits fa4dcfe to 76c17a1); the full report is in `10-REVIEW-FIX.iter1.md`.

**Fixed at:** 2026-10-17
**Source review:** .planning/phases/10-stores-locking-data-integrity/10-REVIEW.md
**Iteration:** 2

**Summary:**
- Findings in scope: 6 (WR-01 to WR-04, plus IN-02 and IN-03 at the orchestrator's request)
- Fixed: 6
- Skipped: 0

Edits were made in the main checkout (`workflow.use_worktrees=false`): no worktree, no recovery sentinel.
Verification ran in the main checkout, so the numbers are reproducible from the tree. Every code fix has
a regression test; each was run before the fix and failed (WR-01: 4 tests; WR-02/WR-03: 5 tests;
IN-02: 3 cases; IN-03: 1 test). No protected test file was edited.

**Verification (main checkout, after the last commit 1356fb1):**
- `cd databasise && .venv/bin/pytest -q tests/stores tests/seam tests/mcp tests/parity tests/runner`: 1201 passed, 1 skipped, 3 deselected, exit 0.
- `.venv/bin/python tools/check_offline_suite.py`: 1860 passed, 1 skipped, 4 deselected (both runs), exit 0.

## Fixed Issues

### WR-01: `load_committed` reported a namespace as absent when its files vanished mid-read

**Files modified:** `databasise/stores/vector.py`, `databasise/tests/stores/test_vector_snapshot_robustness.py`
**Commit:** ed705b7
**Applied fix:** `error` is kept across attempts (a vanish never overwrites an earlier corruption; a later corruption replaces a vanish). After the loop the code returns a valid snapshot or raises that error. `None` is returned only when one stat shows both files missing. `_stat_signature` maps any `OSError` other than `FileNotFoundError` (`PermissionError`, `NotADirectoryError`) to `VectorStoreCorruptedError`. Tests: the unprotected `test_a_file_that_keeps_vanishing_means_the_namespace_is_absent` was replaced by `..._is_refused_as_corruption_not_absent`; new tests cover a checksum failure followed by two vanishes (probe P1b) and a stat that raises `PermissionError` or `NotADirectoryError`.
**Status:** fixed: requires human verification (logic fix)

### WR-02: Health raised a bare `ValueError` for a relative `store_root`

**Files modified:** `databasise/stores/probes.py`, `databasise/tests/stores/test_probe_hardening.py`
**Commit:** 9289371 (shared with WR-03: same function and one test module)
**Applied fix:** `probe_kv` resolves `dir_path / "kv.sqlite3"` before `as_uri()`. Tests: `probe_kv` on a relative directory, and `Databasise.health()` with `store_root=Path("rel_root")` reports the kv store `ok`.

### WR-03: Health created files for a `-wal` without `-shm` and for a graph without `manifest`

**Files modified:** `databasise/stores/probes.py`, `databasise/tests/stores/test_probe_hardening.py`
**Commit:** 9289371
**Applied fix:** the kv probe always opens `mode=ro&immutable=1`, with a comment explaining that it only checks that the file opens and the schema reads, so stale WAL content is acceptable. The graph marker check (`_rocksdb_marker_present`) also requires `graph.cozo/manifest`, the one file Cozo writes outside `data/` (listed from a real store); a directory missing it is `corrupted` and never opened. The module docstring is corrected. Tests assert an unchanged directory listing for a `-wal`-without-`-shm` copy, a missing `manifest` (probe and through `health()`).
**Deviation from the ruling, for the orchestrator to confirm:** always-immutable on a live kv store (a writer open, `CREATE TABLE` not yet checkpointed) fails with `no such table: kv`, because immutable ignores the WAL. Measured: it would have reported every freshly opened kv store `corrupted`. The probe therefore returns `ok` for that one error when a `-wal` file exists. A garbage or truncated database still gives `corrupted`. A test pins the live-writer case (`test_a_live_kv_store_whose_schema_is_still_in_the_wal_is_ok`).

### WR-04: The proxy hands a part the raw store through ordinary Python attributes

**Files modified:** `databasise/parts_core/__init__.py`, `databasise/runner/scheduler.py`
**Commit:** 1356fb1
**Applied fix:** fixed by documented threat model (D-09 intent: misuse prevention), per the orchestrator ruling. The `_StoreProxy` and `unwrap_store_handle` docstrings and the `_ScopedStoresView` docstring now state that the guard targets accidental misuse by admitted in-process parts and is not a sandbox against hostile code; the `__self__`, `__globals__` and `object.__setattr__` routes are deliberately not chased. `unwrap_store_handle` stays in `__all__`. No behaviour change, so there is no regression test (a docstring-presence test would pin wording, not behaviour).

### IN-02: `hasattr` and `getattr` with a default raised `UndeclaredEffectError`

**Files modified:** `databasise/parts_core/__init__.py`, `databasise/tests/runner/test_store_proxy_hardening.py`
**Commit:** b939683
**Applied fix:** `_StoreProxy.__getattribute__` raises `AttributeError` for a refused name the target does not have (and that is not a proxy slot or a store mutator name). A real but withheld attribute (underscore names the target has, engine-only methods, writes on a read proxy) still raises `UndeclaredEffectError`, which is unchanged and is not an `AttributeError` subclass.
**Adaptation:** the existing `test_read_proxies_refuse_writes_naming_the_write_effect` calls `upsert_node` on a kv read proxy, a name the kv store lacks, and expects `UndeclaredEffectError(writes_kv)`. That test is protected, so a module-level `_WRITE_VOCABULARY` (the mutator names of all three store kinds) is treated as known: asking any read proxy for a mutator is a write attempt, not a typo. A drift test asserts that every public method one store kind has and another lacks is in the allowlist, the engine-only set or that vocabulary.

### IN-03: The tracer composer opened a kv store with no finalize on error

**Files modified:** `databasise/__init__.py`, `databasise/tests/test_tracer_composer_finalize.py` (new)
**Commit:** 1ecfa34
**Applied fix:** the scheduler run, the cycle return and the `index_done_callback` loop are in a `try`, and the store finalize is in its `finally`, so a refused or cancelled run closes the connection. Behaviour on success and on a cycle is unchanged (finalize still runs once, a cycle still skips `index_done_callback`). Test: a scheduler that raises still finalizes the store once.

## Skipped Issues

None.

## Not in scope

- IN-01 (`_is_store_fault` classifies by module and top-level type) and IN-04 (misleading log text for an unreadable snapshot): not requested for this iteration.

## Notes for the verifier

- WR-02 and WR-03 share one commit (9289371) because both change `probe_kv` and share one test module.
- The commit-time hook rejected one heredoc-based Bash command (`cat > file`); the scratch scripts were then written with the Write tool. One source restore during a mutation check of WR-01 used `cp` from a saved copy of the fixed file back over `vector.py` (after `git checkout --` of the unfixed state); the restored content is byte-identical to the committed file.

---

_Fixed: 2026-10-17_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
