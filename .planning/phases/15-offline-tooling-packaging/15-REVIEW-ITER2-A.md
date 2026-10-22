---
phase: 15-offline-tooling-packaging
lane: A
iteration: 2
reviewed: 2026-10-21T00:00:00Z
depth: standard
scope: lane A fix commits a8dae39 8d68406 9bc6c3e 7b3379e 77e5da3 bca102f eef7173 d6db78d e75f04e 0d0eb19 79125b5
files_reviewed: 13
files_reviewed_list:
  - databasise/cli.py
  - databasise/eval/corpus_ingest.py
  - databasise/eval/aa_run.py
  - databasise/eval/remint.py
  - databasise/parity/v1_driver_script.py
  - databasise/parity/v1_arm.py
  - databasise/parity/import_index.py
  - databasise/stores/probes.py
  - databasise/parity/build_hipporag_index.py
  - databasise/parity/run_cross_modality.py
  - databasise/parity/run_arm.py
  - databasise/parity/run_comparison.py
  - v1/.gitignore
findings:
  critical: 0
  warning: 5
  info: 3
  total: 8
status: issues_found
---

# Phase 15 Lane A: Re-review of the review fixes (iteration 2)

**Depth:** standard. I read every fix diff and the code around it at HEAD. I ran the two new test files: 27 passed. I ran one probe in the scratchpad (WR-01). I read no protected test file, ran no `--spend` CLI and read no env file.

## Per-finding verdict

| Finding | Verdict | Evidence |
|---|---|---|
| A-CR-01 | fixed | `corpus_ingest.py:221` uses `cli.positive_int`, so a bad value exits 2. `estimate()` raises `NonPositiveLimitError` at `:155-157`, before the `> available` check, and that class is in the CLI tuple at `:228`. |
| A-WR-01 (+B-WR-05) | fixed | `cli.py:47-72` adds the four client classes, `RerankResponseError` and `VectorStoreCorruptedError` to the tuple. `remint.py:84-87` maps `ModelIdentityMissingError` to `UnresolvedJudgeIdentityError`, which is in remint's tuple (`:134`). No bare `ValueError` or `RuntimeError` was added, so D-03 holds. |
| A-WR-02 | fixed | `v1_driver_script.py:146` raises only on `status == "failure"`. This matches v1's three return shapes (`v1/lightrag/lightrag.py:2437-2480`). Shape 3 then yields empty ids and the `fail_response` content, which follows D-08. |
| A-WR-03 | fixed | `v1_arm.py:73-86` takes the last stderr line that is not a log line. v1's log format is `%(levelname)s: %(message)s` (`v1/lightrag/utils.py:96`), so the prefix filter matches it. The driver prints its failure line after `finalize_storages`. The reason for skipping the middle-cut is sound: the important text is now at the start of the message. |
| A-WR-04 | fixed, with a regression | `import_index.py:650-651` reads through `list_kv_prefix`, and `:766-771` takes no lock on a missing root. The new read path adds an uncaught sqlite error (WR-01). |
| A-WR-05 | fixed | `import_index.py:623-630` returns the precondition refusal. `:690-691` adds the reverse graph check. See IN-03 for an edge case. |
| A-WR-06 | fixed for new builds | The marker is written at `build_hipporag_index.py:241-242`, before any store opens. It is removed at `:340`, only after every check. Preflight refuses it at `run_cross_modality.py:273-279`. Builds that were refused before this commit are not covered (WR-03). |
| A-WR-07 | fixed in product; test residual open | `corpus_ingest.py:249` and `aa_run.py:771` take the lock only after `--spend` is checked, so D-04 holds. No nested `store_lock` exists on the same root (flock is per open file), so the lock cannot self-deadlock. The test residual is WR-04. |
| A-WR-08 | fixed | `run_arm.py:317-321`. `RunRecord.to_dict()` emits `partial` and `degraded` (`runner/trace.py:206`). The estimate path still returns 0. |
| A-WR-09 | partly fixed | The snapshot read is inside the `try` at `import_index.py:757-777` and `build_hipporag_index.py:366-375`. The RocksDB lock-held path is still a traceback (WR-02). |
| A-WR-10 | fixed | `run_comparison.py:803-812` writes `<arm>.refused.json` and leaves `<arm>.json` alone. The exit codes are unchanged (1 on a refusal, 3 on inconclusive). See IN-01. |

No fix contradicts D-01 to D-24. D-04 holds on every changed path: each new lock or write sits behind `--spend` or a non-verify import.

## Warnings

### WR-01: The A-WR-04 read path turns a recoverable WAL into a traceback in `import_index` and the `run_comparison` preflight (new, regression)

**File:** `databasise/parity/import_index.py:651`; `databasise/stores/probes.py:146-149`; `databasise/cli.py:65-84`
**Issue:** `verify_import` now reads v2 chunk text with `list_kv_prefix`. That function raises `sqlite3.OperationalError("kv.sqlite3-wal holds frames but kv.sqlite3-shm is missing")` when the `-wal` file has frames and the `-shm` file is absent. That class is not in `cli.offline_refusals()`, so `import_index.main` (`:776`) does not catch it. Every other `verify_import` caller is also exposed, including the `run_comparison` preflight.

Before the fix, `SqliteKVStore` opened the database read-write and replayed the WAL, so this store verified correctly.

**Reproduced:**
1. A scratchpad store was copied while its writer was still open, taking only `kv.sqlite3` and `kv.sqlite3-wal`, as a `cp` that skips `-shm` would.
2. `verify_import` on the copy failed with `RAISED sqlite3 OperationalError kv.sqlite3-wal holds frames but kv.sqlite3-shm is missing`.

**Failure scenario:** A store left by a crash or restored from a backup reaches this state. `import_index --verify` then prints a Python traceback where D-03 requires the one line `ClassName: message`.

**Fix:** In `verify_import`, catch the error and return the precondition refusal, which writes nothing:
```python
try:
    v2_rows, _ = list_kv_prefix(Path(store_root) / workspace / _TEXT_CHUNKS_KIND, "", limit=-1, offset=0)
except sqlite3.OperationalError as exc:
    return VerificationResult(status="refused", violations=(
        Violation(assertion="precondition", detail=f"v2 text_chunks KV is unreadable read-only: {exc}"),))
```

### WR-02: A-WR-09's RocksDB lock-held path is still a traceback (remaining)

**File:** `databasise/parity/import_index.py:580-592`, `:776`
**Issue:** `_v1_graph` opens v1's Cozo RocksDB with a raw `CozoClient("rocksdb", ...)`. When another process holds the v1 index, for example a running v1 server or the v1 driver subprocess, pycozo raises its own exception. That class is not a named refusal, so it escapes the handler. The fix report says this case is not covered. The reason it gives ("its pycozo exception class is not a named refusal") is not a reason to leave it: wrapping the error in a named refusal is a few lines.

**Failure scenario:** `import_index --verify` runs while v1 holds `cozo_graph_chunk_entity_relation.db`. It prints a traceback, not one stderr line.

**Fix:** Wrap the open in `_v1_graph` and raise a named `RuntimeError` subclass, for example `V1IndexLockedError(path)`. Then pass that class to `offline_refusals(MissingV1IndexError, V1IndexLockedError)`.

### WR-03: HippoRAG builds refused before eef7173 carry no marker, so preflight still accepts them (remaining A-WR-06 residual)

**File:** `databasise/parity/run_cross_modality.py:270-279`
**Issue:** The marker exists only for builds run after the fix. A store whose build was refused before the fix is still on disk with no marker. Preflight therefore checks only `hipporag-chunks`, which is the original defect, unchanged for every existing workspace.

The fix report says "a store built and verified before the fix has no marker and still passes". That is true, but it leaves out the other half: a store refused before the fix also passes. The review's second option (preflight repeats the cheap checks) covers old and new stores alike and forces no rebuild.

**Failure scenario:** An earlier `build_hipporag_index --spend` refused with `entities empty`, and its stores stayed on disk. `run_cross_modality --spend` then runs and records a comparison against that refused index.

**Fix:** Also run `_require_namespace` for `hipporag-entities` and `hipporag-facts` in preflight, which are two existing calls. Otherwise, record the residual and have the owner rebuild the existing workspace once.

### WR-04: The existing eval `--spend` tests now lock the real `v1/.eval_corpus_store`, and the residual is not raised as an owner item (remaining A-WR-07 residual)

**File:** `databasise/eval/corpus_ingest.py:78`, `:249`; `databasise/eval/aa_run.py:771`; the fix report, Lane A A-WR-07 row
**Issue:** The fix report says the existing `--spend` cases in `test_aa_run.py` and `test_corpus_ingest.py` do not patch `_EVAL_INGEST_STORE_ROOT`. After this fix, those cases take `flock` on the repo's real `v1/.eval_corpus_store/.engine.lock`. I did not read those files, because they may be protected; this finding relies on the fixer's statement.

Two consequences:
- The test suite writes into the source tree.
- Those cases fail with `StoreLockedError` (exit 1) whenever a real `corpus_ingest --spend` or `aa_run --spend` holds the lock, or when two test processes run them at the same time.

The report also lists "Needs owner grant: 0" while the remedy it names (an autouse fixture in those files) may need a protected edit.

**Failure scenario:** The owner runs `aa_run --spend` in one shell and the offline suite in another. The protected `--spend` cases fail, and nothing in the product changed.

**Fix:** Look for a product-side or unprotected fix first, for example an autouse fixture in an unprotected `conftest.py` that patches `corpus_ingest._EVAL_INGEST_STORE_ROOT` and `aa_run._EVAL_INGEST_STORE_ROOT` to `tmp_path`. If none exists, raise a `grant-check-edit` item with the exact fixture.

### WR-05: `import_index` exits 1 for an inconclusive verification, while D-03 and run_arm (after A-WR-08) use 3; A-WR-05 adds one more such case (pre-existing, widened)

**File:** `databasise/parity/import_index.py:779-787`, `:690-691`
**Issue:** D-03 says code 3 means "ran but inconclusive", and 15-09-PLAN line 97 repeats that table for every offline CLI. `import_index.main` returns 1 for `inconclusive`, the code for a named refusal, and A-WR-05's new v2-only-graph violation also exits 1. The `refused` precondition results print `[refused] precondition: ...` to stdout instead of the D-03 single stderr line.

This deviation is documented in the module docstring, and protected tests may pin it. Even so, after A-WR-08 the CLIs no longer agree.

**Failure scenario:** A script treats exit 1 as "fix the environment" and exit 3 as "the data differs". It reads a chunk-text or graph mismatch from `import_index` as an environment refusal.

**Fix:** Return `cli.EXIT_INCONCLUSIVE` for `inconclusive`, and print the `refused` precondition to stderr as one line. If a protected test pins exit 1, record the exception against D-03 in the verification report instead.

## Info

### IN-01: A stale `<arm>.refused.json` survives a later complete run

**File:** `databasise/parity/run_comparison.py:803-812`
**Issue:** A later complete run writes `<arm>.json` and leaves the older `<arm>.refused.json` beside it. Neither file has a timestamp, so a reader cannot tell which one is current. A refusal at the first query writes nothing.
**Fix:** On a complete write, call `(_RESULTS_DIR / f"{args.arm}.refused.json").unlink(missing_ok=True)`, or add a `written_at` field.

### IN-02: `run_arm --arm hipporag --spend` and `storage_audit` do not check the unverified-build marker

**File:** `databasise/parity/run_arm.py:311-312`
**Issue:** Only the `run_cross_modality` preflight reads the marker. The raw harnesses run and print a run record against a refused build. This is consistent with `run_arm` having no index preflight at all, so it is not a blocker.

### IN-03: The A-WR-05 check is `exists()`, not a v1 index check

**File:** `databasise/parity/import_index.py:623`
**Issue:** An existing but empty v1 dir, or a file at that path, passes the check. With an empty v2 workspace, it still verifies over nothing. `import_v1_index` uses the same check, so the two are consistent. A stricter check would look for `kv_store_text_chunks.json`.

---

_Reviewer: Claude (gsd-code-reviewer), lane A iteration 2. Not checked: protected test files (not read), live/`--spend` behaviour, and the full suite (only the two new test files were run). A BAK stall alarm fired on a read-only grep near the end. The stall skill was not run, because this lane is read-only._
