---
phase: 15-offline-tooling-packaging
lane: A
iteration: 3
reviewed: 2026-10-21T00:00:00Z
depth: standard
scope: lane A iteration-2 fix commits ecdaa5a b48c2b4 4fa6bf6 2d328f9, against 15-REVIEW-ITER2-A.md
files_reviewed: 5
files_reviewed_list:
  - databasise/parity/import_index.py
  - databasise/parity/run_comparison.py
  - databasise/parity/run_cross_modality.py
  - databasise/parity/build_hipporag_index.py
  - databasise/parts_core/lightrag/v1_index_sync.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 15 Lane A: Re-review of the iteration-2 fixes (iteration 3)

**Depth:** standard. I read every product diff and the code around it at HEAD, including the callers of `verify_import`, `_read_graph` and `_v1_graph`.

Tests I ran:
- `databasise/tests/parity` and `databasise/tests/eval`: 370 passed, 3 deselected.
- The two lane A review-fix test files: 22 passed.

I ran one scratchpad probe (see WR-01 below). I also ran `tests/eval` and the three top-level CLI test files under `strace`, to check WR-04 without reading the edited test files. I read no protected test file, ran no `--spend` CLI and no `-m live` test, and read no env file.

## Per-finding verdict

| Finding | Verdict | Evidence |
|---|---|---|
| A-ITER2-WR-01 | fixed for the WAL case; a sibling case remains (WR-01 below) | `import_index.py:653-660` catches `sqlite3.OperationalError` from `list_kv_prefix` and returns `refused` with a `precondition` violation. This writes nothing and matches D-06. |
| A-ITER2-WR-02 | fixed | `import_index.py:117-123` defines `V1IndexLockedError(RuntimeError)`. `_open_v1_cozo` (`:130-136`) is used by both `_read_graph` (`:277`) and `_v1_graph` (`:603`), and re-raises only when `stores.graph._is_lock_error` matches. The class is in `import_index.main` (`:807`) and in `run_comparison._refusals()` (`:723-724`). Both are named classes, not bare `RuntimeError`, so D-03 holds. Changing `_v1_graph` to `dataframe=False` is safe, because `_cozo_rows` (`:174-182`) handles both result shapes. See IN-01 and IN-02. |
| A-ITER2-WR-03 | not fixed; the reason is sound; the residual remains (WR-02 below) | Any preflight check for `hipporag-entities` and `hipporag-facts` also refuses the protected fixture, which has neither namespace. Pre-marker stores refused for partial, degraded or chunk-count reasons look the same on disk as passed ones under any cheap check. The grant-check-edit item is concrete. |
| A-ITER2-WR-04 | fixed | `strace -f` over `databasise/tests/eval`, `test_cli_refusals.py`, `test_dry_run_default.py` and `test_cli_support.py` (237 passed) recorded no `open`/`mkdir` under `v1/.eval_corpus_store` or `v1/.parity_v2_store`. The change is test-only, and D-04 is unaffected. |
| A-ITER2-WR-05 | fixed | `import_index.py:810-822` gives the D-03 codes: 0 verified; `refused` is one stderr line through `cli.refuse(ImportPreconditionError(...))` and exits 1; `inconclusive` exits `EXIT_INCONCLUSIVE` (3). The module docstring (`:44-49`) and the `main` docstring match. The workspace line still goes to stdout first. No doc in `docs/`, `v1/README-PARITY.md` or `launcher/` states the old exit-1-for-inconclusive behaviour. See IN-03. |

No fix contradicts 15-CONTEXT D-01 to D-24. D-04 holds: no new lock, write or provider call was added, and `--verify` on a missing root still takes no lock (`:799-803`).

## Warnings

### WR-01: A corrupt `text_chunks` KV is still a traceback, because the fix catches `OperationalError` and not `DatabaseError` (remaining, next to A-ITER2-WR-01)

**File:** `databasise/parity/import_index.py:655`
**Issue:** `sqlite3.OperationalError` is a subclass of `sqlite3.DatabaseError`. A `kv.sqlite3` that is not a valid database (truncated, overwritten, or a partial copy) raises the parent class, `DatabaseError("file is not a database")`. That class is neither caught here nor in `cli.offline_refusals()`.

The fix report says the catch also covers "any other read-only open failure". That is not accurate.

**Reproduced:** in the scratchpad, a 4 KiB random `kv.sqlite3` under `<store>/ws/text_chunks` and an empty v1 KV. `verify_import` raised `sqlite3.DatabaseError: file is not a database`.

**Failure scenario:** `import_index --verify`, or the `run_comparison --spend` preflight, runs on a damaged store. It prints a Python traceback, where D-03 requires one `ClassName: message` line and exit 1.

**Fix:** widen the catch by one class. This still writes nothing:
```python
except sqlite3.DatabaseError as exc:  # OperationalError (WAL without -shm) and a corrupt file alike
```

### WR-02: HippoRAG stores refused before eef7173 still pass `run_cross_modality` preflight (remaining, owner-gated)

**File:** `databasise/parity/run_cross_modality.py:269-279`
**Issue:** This is unchanged from iteration 2. The fixer's reason is sound:
- The protected `test_tool09_preflight_leaves_the_store_root_listing_unchanged` fixture builds only `chunks` and `hipporag-chunks`, so any check on `hipporag-entities` or `hipporag-facts` refuses it.
- Stores refused for partial, degraded or chunk-count reasons (`build_hipporag_index.py:285-319`) have every namespace populated, so no cheap check can tell them apart from a passed build.

The defect still ships until the owner acts.
**Fix:** the owner applies the grant-check-edit recorded in 15-REVIEW-FIX.md (A-ITER2-WR-03), then the `_HIPPORAG_VECTOR_NAMESPACES` preflight loop. Or the owner rebuilds the existing HippoRAG workspace once with `build_hipporag_index --spend`. Record whichever path is taken in the verification report, because the loop still does not cover the builder's graph and chunk-count checks.

## Info

### IN-01: `V1IndexLockedError` says "another process" for a same-process lock

**File:** `databasise/parity/import_index.py:123`
`_is_lock_error` matches both RocksDB texts: R7, "lock hold by current process", and R8, "While lock file". The new message always names another process. The P2 test itself holds the lock in-process. Wording such as "is locked (by this or another process)" would be accurate.

### IN-02: The seam's `lightrag/v1-index-sync` now gets `V1IndexLockedError`, which the engine does not map to `StoreBusyError`

**File:** `databasise/parity/import_index.py:268-277`; `databasise/parts_core/lightrag/v1_index_sync.py:93`
`read_v1_snapshot` calls `_read_graph`, so the seam's sync node now raises the named class instead of the raw pycozo exception. It is not a `SeamRefusalError`, so the caller-facing result is unchanged (a generic failure, with staged writes dropped). This is not a regression. The engine maps `GraphStoreBusyError` to a 409 `StoreBusyError` (`engine.py:607-611`), and the same mapping could apply here.

### IN-03: The two CLIs give different exit codes for the same precondition

**File:** `databasise/parity/run_comparison.py:563-573`, `:819-820`
After WR-05, a missing or unreadable v2 store gives exit 1 from `import_index`, but exit 3 from `run_comparison`. `run_comparison` turns every non-`verified` result into an inconclusive record. Its docstring documents this ("the index-identity precondition failed" leads to 3), so it is consistent with its own contract. It is still a split that a script reading both CLIs would see.

---

_Reviewer: Claude (gsd-code-reviewer), lane A iteration 3. Not checked: the edited `test_aa_run.py` and `test_corpus_ingest.py` content (possibly protected; WR-04 was checked by syscall trace only), live or `--spend` behaviour, a cross-process v1 RocksDB lock (the new test holds it in-process), and the suites outside parity, eval and the three CLI test files._
