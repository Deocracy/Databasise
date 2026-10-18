---
phase: 11-lightrag-corpus-path
plan: 02
subsystem: eval
tags: [lightrag, v1-subprocess, working-dir, eval, aa-run, selector]

requires:
  - phase: 11-01
    provides: per-workspace v1 working dir on every corpus op, the hermetic real-driver harness
provides:
  - LRAG-01 two-root isolation proof over REST (ingest, delete, /corpus, /corpus/counts, /jobs, /health)
  - LRAG-15 eval-store proof through the real v1 driver
  - aa_run --arm lightrag|hipporag, and selector= on run_one_pass and calibrate_family
affects: [11-06, TOOL-11, Phase 15]

actuals:
  tokens: 5145
  tasks: 2
  commits: 2
plan_head_before: 7397ea9f84cd6f16db5cbb45ceb194f8fb2db8d0
plan_head_after: 6ff345c01e79173fc7339fde7f5138e6a9bfc0f8

tech-stack:
  added: []
  patterns:
    - "per-working-dir recording fake: one document table per working_dir the fake receives, so a misrouted op shows in both the call log and GET /corpus"

key-files:
  created:
    - databasise/tests/seam/test_lightrag_working_dir.py
    - databasise/tests/eval/test_lightrag_eval_store.py
  modified:
    - databasise/eval/aa_run.py

key-decisions:
  - "aa_run --arm defaults to None, so no flag keeps the engine's default selector (D-03 as corrected by research Q6); the arm maps through corpus_ingest._ARM_SELECTORS, imported, not copied"
  - "Only LRAG-15 is marked complete: LRAG-01 is also owned by 11-06 (D-02/M-12 job-family dispatch)"

requirements-completed: [LRAG-15]

coverage:
  - id: D1
    description: "Two apps on two store roots: every corpus op on each carries only <own root>/iso/lightrag-v1, never v1/.corpus_working_dir; app B lists none of A's documents"
    requirement: "LRAG-01"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_lightrag_working_dir.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "corpus_ingest --spend --arm lightrag through the real v1 driver writes only <eval store>/eval-corpus-ingest/lightrag-v1, leaves the operator corpus unchanged, and the LightRAG arm selector then returns evidence from that store"
    requirement: "LRAG-15"
    verification:
      - kind: integration
        ref: "databasise/tests/eval/test_lightrag_eval_store.py#test_eval_lightrag_ingest_stays_in_the_eval_store_and_aa_runs_arm_reads_it_back"
        status: pass
    human_judgment: false
  - id: D3
    description: "aa_run --arm parses, refuses an unknown arm (exit 2), shows the arm in the projection, and threads the mapped selector through calibrate_family and run_one_pass into every engine.query"
    requirement: "LRAG-15"
    verification:
      - kind: unit
        ref: "databasise/tests/eval/test_lightrag_eval_store.py"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-10-18
status: complete
---

# Phase 11 Plan 02: LightRAG Working Dir Isolation and Eval Arm Summary

**Two apps on two store roots now provably send every LightRAG corpus op their own `<store_root>/<workspace>/lightrag-v1` and never list each other's documents, and `aa_run --arm` queries the eval store with the same selector `corpus_ingest --arm` ingested with, returning evidence through the real v1 driver.**

## Performance

- **Duration:** about 12 min (7397ea9 at 00:57 to 6ff345c at 01:08, then the 10-minute offline gate)
- **Tasks:** 2/2
- **Files modified:** 3

## Accomplishments

- LRAG-01 isolation proof over REST: ingest, DELETE, GET /corpus, /corpus/counts, /jobs/<id> and /health on two apps each carry only that app's v1 dir; B lists 0 documents after A ingests; A's job id is 404 on B; `run_corpus_op` puts `working_dir` in the job only when passed.
- LRAG-15 through the real v1 driver and pipeline (loopback stub model server): `corpus_ingest.main(["--limit","2","--arm","lightrag","--spend"])` with `_EVAL_INGEST_STORE_ROOT` redirected to tmp in both eval modules records exactly two ingest calls, both at `<tmp>/eval/eval-corpus-ingest/lightrag-v1`; `v1/.corpus_working_dir` listing and mtimes unchanged; a query with `aa_run._ARM_SELECTORS["lightrag"]` on the engine `aa_run --spend` builds returns evidence that resolves to one of the two ingested `full_doc_id`s.
- `aa_run --arm lightrag|hipporag` (default none), `selector=` on `run_one_pass` and `calibrate_family`, arm printed in the projection JSON (`"arm": "lightrag"` or `null`).

## Task Commits

1. **Task 1: Tracer — two store roots keep their own v1 working dir and documents** - `f52a852` (test)
2. **Task 2: aa_run --arm queries the eval store with the arm it names** - `6ff345c` (feat)

## Test Evidence

Pre-change runs (each new test run first against the unchanged source):

- Task 1, `tests/seam/test_lightrag_working_dir.py`: **passed on arrival**, `4 passed in 2.05s`. LRAG-01's code landed in 11-01 Task 1, commit `7be6968` (removed `DEFAULT_V1_WORKING_DIR` from the adapter, engine stamps the per-workspace dir on every corpus node and passes it to the status and health calls). No failing-first run was fabricated. The tracer gate (interactive, `end-of-phase`, automated-only verify) re-ran the verify and it passed.
- Task 2, `tests/eval/test_lightrag_eval_store.py` against the unchanged `aa_run.py`: `6 failed, 1 passed in 6.19s`. Failures: `AttributeError: module 'databasise.eval.aa_run' has no attribute '_ARM_SELECTORS'` (the real-driver test, after its ingest assertions had already passed), `TypeError: run_one_pass() got an unexpected keyword argument 'selector'`, `TypeError: calibrate_family() got an unexpected keyword argument 'selector'`, `SystemExit: 2` (no `--arm` flag, twice for the projection test and once per spend case), `KeyError: 'selector'` (main passed no selector). The passing one was the unknown-arm argparse case, which exits 2 with or without the flag.
- The plan's acceptance line asks for the "empty evidence before 11-01" run. That run was not repeated here: the ingest half of LRAG-15 passed on arrival against 11-01's code (the recorded working dirs were already under the eval store). The pre-11-01 failure is recorded in 11-01-SUMMARY.md: the real driver opened `v1/.corpus_working_dir` and failed on a Faiss dimension mismatch.

Passing runs:

- `pytest -q tests/seam/test_lightrag_working_dir.py`: `4 passed`.
- `pytest -q tests/eval/test_lightrag_eval_store.py tests/eval`: `63 passed in 8.57s`; `-rs` on the new file: `7 passed`, 0 skipped (the real-driver case ran).
- Plan verification `pytest -q tests/seam tests/eval`: `760 passed in 143.67s`, 0 failed.
- Offline gate `.venv/bin/python tools/check_offline_suite.py`: **exit 0**, `pytest -q -rs: 1896 passed, 4 deselected` and `python -m pytest -q -rs: 1896 passed, 4 deselected`.
- After the runs, `v1/.eval_corpus_store` does not exist and nothing in `v1/.corpus_working_dir` is newer than the plan start.

## Files Created/Modified

- `databasise/tests/seam/test_lightrag_working_dir.py`: recording `run_corpus_op` fake patched on the engine, full-ingest and full-delete modules; four tests.
- `databasise/tests/eval/test_lightrag_eval_store.py`: the real-driver eval-store case, selector threading through `run_one_pass` and `calibrate_family`, `--arm` parsing and projection, and the `--spend` path's store root and mapped selector.
- `databasise/eval/aa_run.py`: `--arm`, `selector` on `run_one_pass` and `calibrate_family`, imports `_ARM_CHOICES`/`_ARM_SELECTORS` from `corpus_ingest`, docstring invocation line.

## Decisions Made

- `--arm` maps through the imported `corpus_ingest._ARM_SELECTORS`; no copy of the selectors in `aa_run`.
- The projection JSON gains an `arm` key rather than a separate print line, so the existing estimate output stays one JSON document.
- `requirements-completed` lists only LRAG-15. LRAG-01's working-dir and isolation clauses are proven here, but 11-06 also lists LRAG-01 (D-02 job-family dispatch for `/jobs/{job_id}`), so marking it complete now would overstate the evidence.

## Deviations from Plan

### Auto-fixed Issues

None in production code.

### Scope notes

**1. Eval ingest driven through `corpus_ingest.main`, not `ingest_documents` alone**
- The behaviour line names `ingest_documents`; the test runs `corpus_ingest.main([... "--spend"])`, which calls `ingest_documents` on an engine built from `_EVAL_INGEST_STORE_ROOT`. This also proves the CLI really uses the redirected root (the LRAG-15 Test line says "runs corpus_ingest --arm lightrag"). `load_snapshot` is patched to two small UNIQ-token documents, and `corpus_ingest._load_env_file` returns the stub client env, so no real env file is read.

**2. Delete added to the isolation proof**
- LRAG-01 lists delete among the corpus ops, so the Task 1 file also checks DELETE on each app reaches only that app's dir (B's delete of A's id answers `not_found`).

**3. Evidence asserted on the engine `aa_run` builds, not a full `aa_run` calibration**
- Per research Q6, a full `aa_run` pass would score through `score_gold_passage`, which reads `document_id` (absent from LightRAG chunk records, TOOL-11). The test builds the engine exactly as `aa_run --spend` does and queries with `aa_run._ARM_SELECTORS["lightrag"]`; the `--spend` path's store root and selector are asserted separately with fakes.

**Total deviations:** 0 auto-fixed; 3 scope notes.
**Impact on plan:** none. No protected test file edited.

## Issues Encountered

- `ruff check` reports I001 (import order) on `eval/aa_run.py` (pre-existing: `dataclass, asdict`) and on the new eval test (ruff groups `databasise` with third-party here, as in other test files). Cosmetic, not fixed.

## Threat Model Coverage

- T-11-04: the eval ingest writes only `<eval store>/eval-corpus-ingest/lightrag-v1`; the test asserts the operator corpus listing and mtimes are unchanged.
- T-11-SC: no package installed.

## User Setup Required

None.

## Next Phase Readiness

- 11-06 can close LRAG-01 with the D-02 job-family dispatch; this plan's isolation tests are the regression guard for the working-dir half.
- TOOL-11 (Phase 15) still owns scoring LightRAG records (`full_doc_id` vs `document_id`).

## Self-Check: PASSED

- FOUND: databasise/tests/seam/test_lightrag_working_dir.py
- FOUND: databasise/tests/eval/test_lightrag_eval_store.py
- FOUND: f52a852, 6ff345c (both ancestors of HEAD)
