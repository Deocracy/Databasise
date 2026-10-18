---
phase: 11-lightrag-corpus-path
plan: 08
subsystem: api
tags: [lightrag, interrupted, retry, d-08, lrag-07, mcp, coverage, write-gate]
status: complete

requires:
  - phase: 11-03
    provides: the driver's targets filter and retry_doc_ids (only the named ids are processed; the first target's original track id is returned), and the status op's document_id filter
  - phase: 11-05
    provides: a timed-out upload keeps its staged file in the per-workspace inbox
  - phase: 11-06
    provides: _write_gate(working_dir) and Databasise._write_gate_held()
  - phase: 11-07
    provides: the facade-free status op and its 409 on a torn doc-status file
provides:
  - "corpus_status / document_counts report parsing, analyzing and processing as 'interrupted' when no write holds the D-07 gate (gate checked before and after the read); pending is never remapped; /jobs keeps v1's raw status"
  - "Databasise.retry_document(document_id, selector=None) -> IngestJob, LightRAG only; status pre-check inside the gate"
  - "Databasise._run_corpus_ingest: the run/commit/cleanup block ingest and retry_document share"
  - "POST /documents/{document_id}/retry (RetryRequest) and the MCP 'retry' tool (RetryToolArgs)"
  - "DocumentNotInterruptedError(document_id, status), 422"
  - "COVERAGE.md §18.5 row 'retry interrupted document'; tool surface pinned at 10"
affects: [11-09, LRAG-07, HIPP-15]

estimate:
  tokens: 40000
  tasks: 2
actuals:
  tokens: 10000
  tasks: 2
  commits: 3
plan_head_before: 21014e591161b4bd970b50c993fd79fdc5beb030
plan_head_after: ef036fa9c5c1820ff420e3e4940017d24f89c1aa

tech-stack:
  added: []
  patterns:
    - "a precheck coroutine awaited inside the write gate, so a status read and the write it guards cannot be split by another write"
    - "a corpus-level status remap gated on the in-process write lock, checked on both sides of the read"

key-files:
  created:
    - databasise/tests/seam/test_interrupted_documents.py
    - databasise/tests/mcp/test_retry_tool.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/refusals.py
    - databasise/seam/rest.py
    - databasise/mcp/tools.py
    - databasise/mcp/server.py
    - databasise/evidence/COVERAGE.md
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/mcp/test_tool_growth_invariant.py
    - databasise/tests/mcp/test_dual_transport_parity.py

key-decisions:
  - "The interrupted remap applies only when no write holds the D-07 gate before and after the status read, so a document a write in flight is advancing is never reported as interrupted"
  - "get_job_status is not remapped: a job id names one run, and 'interrupted' is a corpus-level view of a document no run holds (the protected RUN-10 round trip polls /jobs)"
  - "retry_document refuses a non-LightRAG selector with NoWritePathForModalityError(operation='retry') before any store opens: only LightRAG has a v1 pipeline to resume"
  - "The interrupted pre-check runs inside the gate (after _build_stores, STOR-02), so no write can change the document between the check and the retry run"
  - "No D-08 fallback amendment: the 11-03 driver filter means the next unrelated ingest does not reprocess an interrupted document, so LRAG-07 holds as written"

requirements-completed: [LRAG-07]

duration: 35min
completed: 2026-10-18
---

# Phase 11 Plan 08: Interrupted documents and the retry action Summary

A LightRAG ingest killed by its wall-clock ceiling now leaves its document reported as `interrupted` on `GET /corpus` and `GET /corpus/counts`. The next unrelated ingest does not touch it. `POST /documents/{document_id}/retry`, or the MCP `retry` tool, reprocesses only that document under its original track id.

## What was built

- **Interrupted label (D-08, Q9).** `corpus_status` and `document_counts` check `Databasise._write_gate_held()` before and after the status read. When neither check finds the gate held, every `parsing`, `analyzing` or `processing` row is reported as `interrupted`, and those counts fold into an `interrupted` bucket. `total` stays equal to the sum. `pending` is never remapped. While a write holds the gate, v1's own status is reported unchanged. `get_job_status` keeps v1's raw status, and its docstring records why.
- **`Databasise.retry_document`.** The method validates the id with `generated_on_disk_name` and resolves the selector. A family other than `lightrag` raises `NoWritePathForModalityError(operation="retry")`. It then builds the corpus-ingest wiring with `documents=[]`, `retry_doc_ids=[id]`, a minted `track_id`, the working dir and the inbox as `input_dir`. Inside the gate, the status op runs with `document_id` set. No row raises `UnknownDocumentError`, and a status outside parsing, analyzing and processing raises `DocumentNotInterruptedError`. After that, the run, the sync and `_commit_all` proceed as in `ingest`, with drop-on-refusal. A committed retry removes the document's inbox files. The returned job id is the driver's track id, which is the document's original one.
- **Shared block.** The ingest block that opens the stores, enters the gate, stages, runs, commits or drops, finalizes and cleans up is now `Databasise._run_corpus_ingest`. `ingest` and `retry_document` both call it. It takes a `precheck` coroutine, awaited inside the gate, and a `remove_inbox_files` flag. `ingest`'s behaviour is unchanged: the full `tests/seam` suite passes.
- **Transports.** `RetryRequest` and `POST /documents/{document_id}/retry` form a one-statement route with `_FAULT_RESPONSES`. `RetryToolArgs` adds `"retry"` to `TOOL_NAMES`, and the `retry` tool calls `engine.retry_document`. COVERAGE.md §18.5 has the row `retry interrupted document`.
- **Refusal.** `DocumentNotInterruptedError(document_id, status)` is in `__all__` and `_REFUSAL_FACTORIES`, and maps to 422. `UnknownDocumentError` now has a raiser, and its docstring says so.

## Test evidence

### Task 1 (tracer): `tests/seam/test_interrupted_documents.py`

- **RED, unchanged source:** `3 failed in 12.74s`.
  - The real-driver case got its 503 `CorpusOpTimeoutError` and then `assert {'slow1': 'processing'} == {'slow1': 'interrupted'}`.
  - The fake no-write case failed with `{'a': 'processing'} != {'a': 'interrupted'}`, plus the same for `parsing` and `analyzing`.
  - The gate-held case failed with `AttributeError: 'Databasise' object has no attribute 'retry_document'`.
- **GREEN:** `3 passed in 23.27s`. The real-driver case ran; `v1/.venv/bin/python` is present and nothing was skipped.
- **Plan verify** (`test_interrupted_documents.py test_rest_transport.py test_rest_corpus_endpoints.py test_refusal_status_codes.py test_refusal_catalogue.py`): `144 passed in 41.40s`, including the protected RUN-10 round trips, unchanged.
- **Tracer feedback gate:** interactive mode, `end-of-phase`, automated-only verify. The verify was re-run, passed, and the plan expanded to Task 2.

The real-driver case covers the following:
1. The slow ingest returns 503 `CorpusOpTimeoutError`.
2. `/corpus` then shows `{"slow1": "interrupted"}`, and `/corpus/counts` has `interrupted == 1` with total equal to the sum.
3. `fast1` returns 200, and its `/jobs` rows list only `fast1`.
4. The stub server received no new `UNIQslow` chat call during that ingest, and `slow1` is still `interrupted`.
5. The retry returns 200 with `enqueued == 1` and `job_id` equal to `slow1`'s original track id, read from v1's `kv_store_doc_status.json` in the test's temp dir.
6. `/corpus` then shows both documents `processed`, and `/query "UNIQslow freight"` returns evidence that resolves to `UNIQslow` content.
7. Retrying `fast1` returns 422 `DocumentNotInterruptedError` with `document_id` `fast1` and `status` `processed`. Retrying `nosuch` returns 422 `UnknownDocumentError`.

### Task 2 (TDD): `tests/mcp/test_retry_tool.py`

- **RED:** `2 failed in 1.08s`. `assert 'retry' in [...]` failed (no tool), and the processed-document call returned the SDK's unknown-tool text, not refusal JSON.
- **GREEN, plan verify 1** (`tests/mcp/test_retry_tool.py tests/mcp/test_tool_growth_invariant.py tests/mcp`): `97 passed in 20.75s`.
- **Plan verify 2** (`tests/seam tests/launcher tests/stores`): `973 passed in 264.34s`.

### Full gate

`cd databasise && .venv/bin/python tools/check_offline_suite.py` exited **0**:
- `pytest -q -rs`: 1995 passed, 4 deselected in 467.91s;
- `python -m pytest -q -rs`: 1995 passed, 4 deselected in 466.97s.

The gate started after b5da5b4. The ef036fa import reorder landed while it ran, and the touched test was re-run on its own afterwards.

### Granted protected edit (`databasise/tests/mcp/test_tool_growth_invariant.py`, grant at ledger_version 439)

The grant reason was confirmed with the Read tool before editing. The one-file diff:

```diff
@@ from databasise.mcp.tools import (
     RetireToolArgs,
+    RetryToolArgs,
     RollbackToolArgs,
@@ _TOOL_ARG_MODELS = (
     RetireToolArgs,
+    RetryToolArgs,
 )
@@ test_the_registered_tool_set_equals_tool_names_as_a_set_and_by_count
-    # docstring).
-    assert len(names) == len(TOOL_NAMES) == 9
+    # docstring). 11-08-PLAN.md (D-08): grew to ten — `retry` is a genuinely new §18 operation.
+    assert len(names) == len(TOOL_NAMES) == 10
@@ _OPERATION_TO_TOOLS
     "retire": ("retire",),
+    "retry interrupted document": ("retry",),
```

The edit touches nothing else. The import line is needed for the `_TOOL_ARG_MODELS` entry the grant names.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `tests/mcp/test_dual_transport_parity.py` pinned nine tools and had no retry scenario**
- **Found during:** Task 2
- **Issue:** The plan's facts list named only the growth test as pinning the count. `test_the_registered_tool_set_equals_tool_names_and_has_nine_members` asserted `len(TOOL_NAMES) == 9`, and `test_mcp_rest_and_in_process_agree_for_every_tool[retry]` failed with `KeyError: 'retry'` because it is parametrized over `TOOL_NAMES`.
- **Fix:** Renamed the test to `..._has_ten_members` and changed it to `== 10`. Added `_retry_scenario`, which retries a fake `processing` document over MCP, REST and in-process and compares every field except the minted `job_id`, plus its `elif tool_name == "retry"` setup. The file is not BAK-protected. A read-only probe through the guard was allowed for this file and refused for `test_mcp_refusal_mapping.py`.
- **Commit:** b5da5b4

**2. [Rule 2 - Correctness] The gate is checked on both sides of the status read**
- **Found during:** Task 1
- **Issue:** One check alone can misreport a document. If the gate is checked only after the read, a write that finishes during the read makes its in-flight row look interrupted. If it is checked only before, a write that starts during the read does the same.
- **Fix:** `held = before or after`. This adds one line to each of the two methods.
- **Commit:** 5db8ed4

**3. Real-driver ceiling 10 s, not 6 s.** The test lowers `INGEST_WALL_CLOCK_CEILING_SECONDS` to 10 and holds `UNIQslow` for 30 s, matching 11-03's proven driver test. With 6 s, the timeout could fire before v1 enqueues the document on a slow start, and the test would then fail for the wrong reason. The test still asserts that the slow call started.

**4. Style commit.** ef036fa sorts the new test's imports (ruff I001). No behaviour changed; the test was re-run: `3 passed in 24.61s`.

**Process note.** One ruff command was chained with `git stash list >/dev/null` by mistake. The executor rules forbid every stash subcommand, including this one. The command is read-only, its output was discarded, and no stash was created, applied or dropped.

## Known limits

- The retry minted `track_id` is recorded in `jobs.db` (the shared block records before the run) even though the returned job id is the original track id. The extra row is never returned to a caller and causes no lookup change.
- The gate is in-process (D-07). Another process writing the same working dir is excluded by Phase 8's one-engine-per-store-root rule, not by this remap.
- Ruff on the touched source files reports only findings already present before this plan (engine I001/RUF100/ASYNC230/BLE001, the rest.py B008 `Depends`/`DeleteRequest()` pattern that `RetryRequest()` follows, and RUF022 `__all__` order).

## Threat Flags

None beyond the plan's register. T-11-17 is mitigated: retry refuses unless the document is mid-pipeline with no write in flight, takes the write gate, and the driver processes only the named id. The test checks that no `UNIQslow` call happened during an unrelated ingest. T-11-18 is mitigated: the id passes `generated_on_disk_name` first, the driver resolves it against doc_status rows only, and the inbox cleanup is by exact `<id>.` prefix.

## Next Phase Readiness

- LRAG-07 is fully delivered: the label, the untouched-by-next-ingest proof and the retry on all three transports.
- 11-09 (`/health` reason) is unaffected by this plan.

## Self-Check: PASSED

- Files exist: databasise/tests/seam/test_interrupted_documents.py, databasise/tests/mcp/test_retry_tool.py.
- Commits are ancestors of HEAD: 5db8ed4 (Task 1), b5da5b4 (Task 2), ef036fa (style). `git rev-list --count 21014e5..ef036fa` = 3.
