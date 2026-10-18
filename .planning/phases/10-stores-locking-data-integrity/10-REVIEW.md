---
phase: 10-stores-locking-data-integrity
reviewed: 2026-10-17T00:00:00Z
depth: standard
iteration: 3
files_reviewed: 65
files_reviewed_list:
  - databasise/__init__.py
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
  - databasise/tests/test_tracer_composer_finalize.py
  - databasise/tests/validator/test_taint_conformance.py
  - databasise/tests/wirings/__init__.py
  - databasise/tests/wirings/test_store_effects_wired.py
findings:
  critical: 0
  warning: 1
  info: 6
  total: 7
status: issues_found
---

# Phase 10: Code Review Report (iteration 3)

**Reviewed:** 2026-10-17
**Depth:** standard
**Files Reviewed:** 65
**Status:** issues_found

## Summary

Scope: the iteration-2 list plus the two files the iteration-2 fixes added (`databasise/__init__.py`,
`databasise/tests/test_tracer_composer_finalize.py`). Review effort went to the nine files in
`git diff 76c17a1 HEAD -- databasise/` (commits ed705b7..1356fb1); files those commits did not touch were
not re-read. The 60 tests in `test_vector_snapshot_robustness.py`, `test_probe_hardening.py`,
`test_store_proxy_hardening.py`, `test_tracer_composer_finalize.py` and `test_health_probe.py` pass. Every
"probe" claim below was reproduced with a script in the session scratchpad (outside the repo); the repo
tree is unchanged by the review.

All four iteration-2 Warnings are resolved or accepted. The one new Warning is a gap the iteration-2 fix
did not cover: the kv and graph probes still raise `PermissionError` for an unreadable namespace
directory.

### Iteration-2 findings

| Id | Status | Note |
|----|--------|------|
| WR-01 | Resolved | `load_committed` returns `None` only on a single stat showing both files missing (line 217). Every other loop exit returns a valid snapshot or raises `error`. See answer 1. |
| WR-02 | Resolved | `probe_kv` resolves before `as_uri()`. Probe: `probe_kv(Path("ws/kv"))` returned `ok` from a relative path. |
| WR-03 | Resolved | A `-wal` copy without `-shm` returns `ok` and the directory listing is unchanged; a graph without `manifest` returns `corrupted`, nothing created. The fixer's deviation is acceptable, see answer 2. |
| WR-04 | Accepted | Resolved by a documented threat model (accepted limit, not re-reported). |
| IN-02 | Resolved | `hasattr` and `getattr(..., default)` work for names the target lacks. See answer 3. |
| IN-03 | Resolved | See answer 4. |

### Answers to the focus questions

1. **`load_committed`.** Traced every exit of the loop.
   - `return None` occurs only at line 217, when both stats of one attempt are `None`.
   - A half-present pair, a vanish during read and a failed validation each set `error` and continue or
     raise. `error` is never reset: a vanish never replaces an earlier corruption (`error or ...`), and a
     later corruption replaces an earlier vanish.
   - A last-attempt read that passed validation but saw a changed stat is returned uncached; a stale
     `signature` on it only makes the next `prepare()` re-read, so it is safe.
   - `raise error` at line 252 cannot see `None`: every path that reaches the loop end without a valid
     snapshot set `error` first (a corruption, a vanish or a half-present pair).
   - `_stat_signature` maps `PermissionError` and `NotADirectoryError` to `VectorStoreCorruptedError`.
   - One consequence worth knowing, not a defect: if attempt 1 saw a corruption and attempt 2 sees both
     files missing, the result is `None`. That follows the stated rule (both files absent in one stat) and
     the earlier corruption concerned files that no longer exist.
2. **`probes.py`.** Probe results (script in scratchpad, real stores):
   - Relative path: `ok`, no `ValueError`.
   - Live kv store with `-wal` and `-shm`: `ok`, listing unchanged.
   - `-wal` copy without `-shm`: `ok`, listing unchanged (no file created).
   - Garbage `kv.sqlite3` plus a `-wal`: `corrupted`.
   - Graph copy of a real populated store: `ok`; `manifest` removed: `corrupted`, listing unchanged;
     `manifest` only with no `data/`: `corrupted`, listing unchanged; empty `graph.cozo`: `corrupted`
     (existing test).
   - Missing directory: `absent` for all three probes.
   - Namespace directory with mode 000: `probe_vector` returns `corrupted`; **`probe_kv` and `probe_graph`
     raise `PermissionError`** (WR-01 below).
   - The `no such table: kv` plus `-wal` leniency: acceptable. See IN-02.
3. **IN-02 and `_WRITE_VOCABULARY`.** Correct. The refusal still fires for a name the target has, and for
   a name in `_PROXY_SLOTS | _WRITE_VOCABULARY` even when the target lacks it, so the protected
   `upsert_node`-on-kv test keeps its `UndeclaredEffectError(writes_kv)`. No store method set is missing
   from the three sets: I listed the public callables of all four store classes; the only name outside
   them is `initialize`, which every store has, so a read proxy refuses it with `UndeclaredEffectError`.
   The drift test is weaker than its comment (IN-04).
4. **IN-03.** `finally` runs on success, cycle (the `return` inside `try`) and failure. Success order
   changed from per-store callback-then-finalize to all callbacks then all finalizes; the dict holds one
   store, so there is no effect. One robustness note in IN-05.

## Warnings

### WR-01: `probe_kv` and `probe_graph` raise `PermissionError` when the namespace directory is not searchable

**File:** `databasise/stores/probes.py:44` (`db_path.is_file()`), `databasise/stores/probes.py:88` (`db_path.exists()`); reached from `databasise/seam/engine.py:1269-1274`
**Issue:** On Python 3.12, `Path.is_file()` and `Path.exists()` swallow only `ENOENT`, `ENOTDIR`, `EBADF`
and `ELOOP`; `EACCES` propagates. Both calls sit outside the probes' `try` blocks. Probe: a namespace
directory with mode 000 makes `probe_kv` raise `PermissionError: ... kv.sqlite3` and `probe_graph` raise
`PermissionError: ... graph.cozo`, while `probe_vector` returns `corrupted` for the same directory. The
module docstring ("never raises for a store state") and the `health()` docstring ("Never raises for an
unreachable store") promise otherwise, and `_is_store_error` explicitly lists `PermissionError` as a
store failure. `health()` wraps nothing, so `GET /health` returns 500 for a store root the process cannot
search (a root owned by another user, a restored backup with wrong modes). That is the case a health
check exists to report. The iteration-2 review asked specifically about permission errors; the WR-02 and
WR-03 fixes did not touch this.
**Fix:**
```python
def _present(path: Path) -> bool | None:
    """True or False for presence; None when the path cannot be examined."""
    try:
        return path.is_file()
    except OSError:
        return None

# probe_kv
present = _present(db_path)
if present is None:
    return "corrupted"
if not present:
    return "absent"

# probe_graph: same with path.exists(); None -> "corrupted"
```
Add a test with `os.chmod(dir, 0)` for `probe_kv` and `probe_graph` (skip when running as root).

## Info

### IN-01: Accepted limits (not defects, listed for the record)

**File:** `databasise/parts_core/__init__.py:113-124`, `databasise/seam/engine.py:278-282`, `databasise/stores/probes.py:86-111`
**Issue:**
- iteration-2 WR-04: proxy bypass routes (`__self__`, `__globals__`, `object.__setattr__`,
  `unwrap_store_handle`, `_raw_stores`) are documented as outside the threat model. The docstrings in
  `parts_core/__init__.py` and `runner/scheduler.py` now state it.
- Node ids in `stop_reason`: Phase 13 WIRE.
- Opening a populated graph rotates RocksDB files inside `graph.cozo/data/` (000010.sst, MANIFEST,
  OPTIONS, `LOG.old.*`); nothing outside `data/` changes now that `manifest` is required.
- iteration-2 IN-01: `_is_store_fault` classifies by module and top-level type only.
**Fix:** none requested.

### IN-02: The `no such table: kv` plus `-wal` leniency can hide a database that lost its `kv` table, and the kv `busy` state is now unreachable

**File:** `databasise/stores/probes.py:60-64`
**Issue:** Judged against the fixer's deviation:
- The leniency is needed. With `immutable=1` the WAL is ignored, so a store that has just been opened
  (its `CREATE TABLE` still in the WAL) would report `corrupted` on every health call. Probe: a live store
  reports `ok`.
- What it masks: a valid SQLite file with a different schema plus a `-wal` also reports `ok`
  (probe: `create table other(a)` plus an empty `-wal` returned `ok`). A garbage or truncated file still
  gives `corrupted` (probe), so real file corruption is not hidden. The residual case is not data
  corruption of the store's own format: `SqliteKVStore.__init__` runs `CREATE TABLE IF NOT EXISTS kv`,
  so the next open succeeds and recreates an empty table. The same schema without a `-wal` is classified
  `corrupted`, so the two outcomes are inconsistent, but neither blocks an open. Acceptable.
- Because the probe is immutable, SQLite never takes a lock, so the `"locked"` branch on line 64 and the
  `busy` state for kv are dead. D-14 listed `busy`, and its text says "opened `mode=ro`"; the fixer's
  comment records the reason for `immutable=1`. A writer in the middle of a checkpoint could in theory
  produce a torn page read and a spurious `corrupted` (SQLite documents `immutable` as unsafe on a file
  that changes); I could not provoke it.
**Fix:** Delete the dead `"locked"` branch or comment that kv never reports `busy`. Add one sentence to
D-14's deviation record. No behaviour change needed.

### IN-03: A directory named `kv.sqlite3` is reported `absent`

**File:** `databasise/stores/probes.py:44-45`
**Issue:** `is_file()` is false for a directory, so the probe returns `absent` (probe: `kv is dir ->
absent`). `SqliteKVStore.__init__` would fail on that path, so the store is unusable but health says it
does not exist.
**Fix:** `if db_path.exists() and not db_path.is_file(): return "corrupted"`, folded into the WR-01
helper.

### IN-04: The new drift test is weaker than its comment

**File:** `databasise/tests/runner/test_store_proxy_hardening.py:64-82`
**Issue:** The comment says a name another kind has but this one lacks "must still be refused, not
missing". The assertion only checks that the name is in `known`, which includes every kind's read
allowlist. A read-allowlisted method of another kind (`get_node` on a kv read proxy) is therefore
accepted by the test while the proxy raises `AttributeError`, not `UndeclaredEffectError`. That is
correct behaviour (the attribute does not exist); the comment is wrong. The test does guard its real
purpose: a new mutator on one store kind fails the test until it joins `_WRITE_VOCABULARY`.
**Fix:** Reword the comment to say the test guards mutator names only.

### IN-05: The finalize loop in the tracer composer stops at the first failing `finalize`

**File:** `databasise/__init__.py:101-102`
**Issue:** If one `finalize()` raises inside the `finally`, later stores are not finalized and the
exception replaces any in-flight one. With one kv store today this cannot matter; the loop is written
for several.
**Fix:** `for store in stores.values(): try: await store.finalize() except Exception: log` and re-raise
the first failure afterwards, only when a second store is added.

### IN-06: Carry-overs from iteration 2 not addressed

**File:** `databasise/stores/vector.py:91-100`, `databasise/stores/vector.py:291-298`
**Issue:**
- Iteration-2 IN-04 (misleading log text) is unfixed and now broader: the new "vanished while being
  read", "missing vector.faiss" and "unreadable: PermissionError" cases all produce a message that says
  "sidecar recorded index_checksum None, but the on-disk index file's actual checksum is '<...>'". The
  text goes to the server log only.
- `_committed_signature` (used by `prepare()` and `commit_prepared()`) still catches only
  `FileNotFoundError`, so a `PermissionError` there reaches the caller raw, where `load_committed` now
  maps the same error to `VectorStoreCorruptedError`. `__init__` runs `load_committed` first, so this
  needs the permission to change after open.
**Fix:** Give `VectorStoreCorruptedError` an optional `reason`; route `_committed_signature` through
`_stat_signature`.

---

_Reviewed: 2026-10-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
_Iteration: 3_
