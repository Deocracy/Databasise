---
phase: 11-lightrag-corpus-path
plan: 06
subsystem: api
tags: [lightrag, hipporag, write-gate, jobs, d-07, d-02, m-12, lrag-04, lrag-01, store-busy]
status: complete

requires:
  - phase: 11-01
    provides: per-workspace v1 working dir and the v1-index-sync node with its prune manifest
  - phase: 11-03
    provides: the @0.2.0 driver protocol (the caller's track id is the job id)
  - phase: 11-05
    provides: the per-workspace inbox and its cleanup, now inside the write gate
provides:
  - "_WRITE_GATES / _gate_for / _write_gate in seam/engine.py: one threading.Lock per resolved v1 working dir, refusal with StoreBusyError(store_kind='corpus')"
  - "Databasise._write_gate_held(), the non-acquiring check 11-08's interrupted remap uses"
  - "seam/jobs_store.py JobFamilyStore (record, lookup) over <store_root>/jobs.db, table job_families"
  - "family dispatch in Databasise.get_job_status: HippoRAG jobs answered from the record, everything else from v1"
affects: [11-07, 11-08, 11-09, HIPP-15, LRAG-13]

estimate:
  tokens: 35000
  tasks: 2
actuals:
  tokens: 7400
  tasks: 2
  commits: 2
plan_head_before: ac03da5fbf8dc15e774977957c04d90779cf76f0
plan_head_after: 438166a91a976fece059d3b15fa504ea79de09fd

tech-stack:
  added: []
  patterns:
    - "contextlib.ExitStack holds a conditional gate across a try/except/finally and the post-commit cleanup"
    - "a read-only sqlite lookup (mode=ro URI) that returns None when the file is absent, so reads create nothing"

key-files:
  created:
    - databasise/seam/jobs_store.py
    - databasise/tests/seam/test_corpus_write_gate.py
    - databasise/tests/seam/test_job_families.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/refusals.py

key-decisions:
  - "The D-07 gate is entered right after _build_stores and released only after the commit or drop, the store finalize and the inbox cleanup, so the v1 call, the sync's manifest read and the staging all sit inside it"
  - "Only LightRAG ingests are gated; delete_document is always gated, since only LightRAG ships a delete wiring"
  - "LightRAG jobs are recorded under the minted track id before the run, HippoRAG jobs only after a committed run; a jobs.db error is ForeignEngineRefusalError(StoreFault)"
  - "JobFamilyStore opens one connection per call, so concurrent requests from several threads share no transaction state"

requirements-completed: [LRAG-04, LRAG-01]

duration: 35min
completed: 2026-10-18
---

# Phase 11 Plan 06: Per-working-dir write gate and job-family dispatch Summary

A LightRAG ingest or delete now holds a per-working-dir `threading.Lock` from just after the store open until after the commit and cleanup. A second write gets `StoreBusyError(store_kind="corpus")` (409) at once. `GET /jobs/{job_id}` answers a committed HippoRAG job from `<store_root>/jobs.db` without asking v1.

## What was built

- **Write gate (D-07, LRAG-04).** `_write_gate(working_dir)` keys on the resolved v1 working dir and calls `acquire(blocking=False)`. It refuses with `StoreBusyError(store_kind="corpus")` and releases in `finally`. `ingest` (LightRAG family only) and `delete_document` enter it inside a `contextlib.ExitStack` right after `_build_stores`. The gate covers the v1 subprocess, the v1-index-sync's manifest read, mirror and staging, `_commit_all` or `_drop_pending`, the store finalize, and the inbox cleanup. This meets the orchestrator's security-review requirement: two writes can never read the same prune manifest.
- **Job families (D-02, M-12).** `JobFamilyStore` wraps one table, `job_families(job_id PK, family, document_id, created_at)`, in WAL mode. `record` creates `jobs.db` lazily. `lookup` returns `None` when the file is absent and otherwise opens it read-only. `get_job_status` checks the record first. A `hipporag` row returns `JobStatus` with one `processed` entry and `counts={"processed": 1}`. Anything else takes the unchanged v1 path, `UnknownJobError` placement included.
- `StoreBusyError`'s docstring and message now cover the corpus case. The message reads "held by another process or write" instead of only "another process".

## Test evidence

### Task 1 (tracer): `tests/seam/test_corpus_write_gate.py`

- **RED, unchanged source:** `7 failed, 2 passed in 18.15s`. Failures:
  - two ingests and ingest+delete each produced 2 jobs (`assert (2 == 1)`): both writes ran, overlapping;
  - all three phase-arrival cases: `Failed: DID NOT RAISE StoreBusyError`;
  - the REST second POST: `assert 200 == 409`;
  - the released-gate case: `AttributeError: 'Databasise' object has no attribute '_write_gate_held'`.
  - The two that passed were the non-refusal cases (two workspaces, HippoRAG beside LightRAG), which needed no gate.
- **GREEN:** `tests/seam/test_corpus_write_gate.py tests/seam/test_build_stores_cleanup.py` gave `15 passed in 24.51s`.
- **Broader verify:** `tests/seam tests/mcp tests/stores` gave `988 passed in 225.25s`.
- **Tracer feedback gate (interactive, end-of-phase, automated-only verify):** re-ran the verify, which passed, then expanded.

The orchestrator-required interleave proof is `test_a_write_arriving_in_any_phase_of_another_never_interleaves_the_manifest`, parametrized over `driver-start`, `sync-start` and `commit-start`:
- The second write is launched while the first is inside the v1 call, the sync's `read_v1_snapshot`, or `_commit_all`. It gets `StoreBusyError(store_kind="corpus")`.
- The recorded event sequence is exactly one uninterleaved run: `driver-start, driver-end, sync-start, sync-end, commit-start, commit-end`.
- A follow-up ingest succeeds. The prune manifest then lists exactly `["a-chunk-000", "b-chunk-000"]`, and both ids resolve in the v2 kv store.

### Task 2 (TDD): `tests/seam/test_job_families.py`

- **RED, unchanged source:** `2 failed, 3 passed in 1.77s`:
  - the HippoRAG job got `404 UnknownJobError` from v1 (`assert 404 == 200`);
  - `jobs.db` did not exist after the first ingest.
  - The three that passed pin unchanged behaviour (LightRAG via v1, unknown id 404, refused ingest records nothing).
- **GREEN:** `test_job_families.py test_ingest_job_status.py test_corpus_adapter_failures.py test_rest_corpus_endpoints.py` gave `53 passed in 9.75s`.
- **Broader verify:** `tests/seam tests/mcp tests/stores tests/parity` gave `1146 passed, 3 deselected in 243.47s`.
- `tests/seam/test_ingest_job_status.py` needed no change: its ids have no record, so they still reach v1.

### Full gate

`cd databasise && .venv/bin/python tools/check_offline_suite.py`: **exit 0**, `pytest -q -rs: 1968 passed, 4 deselected in 433.76s` and `python -m pytest -q -rs: 1968 passed, 4 deselected in 432.49s`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] StoreBusyError message said "held by another process" for an in-process write**
- **Found during:** Task 1
- **Issue:** The corpus refusal would have told a client another process held the store, which is false for D-07.
- **Fix:** The message now says "held by another process or write", and the docstring names the `corpus` kind. No test matches the message text.
- **Files modified:** databasise/seam/refusals.py (not in the plan's files_modified)
- **Commit:** ac2044b

**2. [Rule 2 - Missing critical] jobs.db errors are named faults**
- **Found during:** Task 2
- **Issue:** A raw `sqlite3.Error` from `record` or `lookup` would reach REST as a bare 500.
- **Fix:** `_record_job` and the `get_job_status` lookup map it to `ForeignEngineRefusalError(StoreFault)`.
- **Commit:** 438166a

**3. Orchestrator requirement folded into Task 1**
- The manifest-interleave test (three arrival phases, a consistent manifest afterwards) is added beside the plan's behaviours in `test_corpus_write_gate.py`.

## Known limits

- A HippoRAG `JobStatus` ignores `page`: the job always holds exactly one document, so it returns that one entry for any offset.
- The gate is in-process only. Cross-process exclusion rests on Phase 8's one-engine-per-store-root guarantee, as D-07 states.
- A HippoRAG record is written after the commit. If writing it fails, the caller gets a StoreFault for a write that did commit. This needs a jobs.db failure on a store root whose other stores just committed.

## Threat Flags

None. T-11-12 is mitigated by the gate and the overlap tests. T-11-13 is covered: the 409 body carries only `refusal_type`, `message` and `store_kind`, and the test asserts no store-root path and no `lightrag-v1` in it.

## Next Phase Readiness

- 11-08 can use `Databasise._write_gate_held()` to report a document left mid-pipeline as `interrupted`.
- Phase 12 (HIPP-15) inherits the job semantics: a HippoRAG job is terminal `processed` once committed.

## Self-Check: PASSED

- Files exist: databasise/seam/jobs_store.py, databasise/tests/seam/test_corpus_write_gate.py, databasise/tests/seam/test_job_families.py.
- Commits are ancestors of HEAD: ac2044b (Task 1), 438166a (Task 2). `git rev-list --count ac03da5..438166a` = 2.
