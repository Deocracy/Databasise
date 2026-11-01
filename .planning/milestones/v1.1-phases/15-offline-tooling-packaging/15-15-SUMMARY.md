---
phase: 15-offline-tooling-packaging
plan: 15
subsystem: cli
tags: [estimate-only, hipporag, index-build, chunk-count]

requires:
  - phase: 15-02
    provides: "databasise/cli.py (refuse, offline_refusals, EXIT_*) and the inert --spend flag"
provides:
  - "build_hipporag_index: estimate-only default, empty-root build, ChunkCountMismatchError"
affects: [15-17, 15-18]

actuals:
  tokens: 5500
  tasks: 2
  commits: 2

plan_head_before: 4de9e7c
plan_head_after: 9228a47be4d8b279120482d68855e9a303cc8994

key-files:
  modified:
    - databasise/parity/build_hipporag_index.py
    - databasise/tests/parity/test_build_hipporag_index.py

key-decisions:
  - "Expected chunk count comes from the same _split_into_chunks and the chunk node's own chunk_size/chunk_overlap config (IngestEstimate carries no chunk count)"
  - "ChunkCountMismatchError is checked before the generic empty-extraction failures, so a zero chunk namespace is named"

requirements-completed: []

status: complete
completed: 2026-10-21
---

# Phase 15 Plan 15: build_hipporag_index estimate-only, empty-root build, chunk-count check Summary

**A bare `build_hipporag_index` call prints the HippoRAG ingest estimate and `mode: estimate-only` and touches nothing; `--spend` builds on an empty store root and refuses a chunk namespace that is empty or differs from the corpus chunking.**

## Accomplishments

- `main`: loads the parity snapshot, prints `estimate(snapshot, limit=len(documents), arm="hipporag").to_dict()`; without `--spend` prints `mode: estimate-only` and returns 0 before the lock, env load, client build or any write. Refusals go through `cli.refuse` over `cli.offline_refusals(HippoRAGIndexBuildRefusedError)`.
- `MissingParityLightRAGIndexError` and the LightRAG-directory precondition are removed; `build_index` creates `store_root/workspace`.
- `ChunkCountMismatchError(HippoRAGIndexBuildRefusedError)` (fields `found`, `expected`) is raised when `chunk_vector_count` is zero or differs from the chunk count the same splitter yields.
- Module docstring now records the 2026-09-10 real runs, the Phase 12 rebuild note, the exit table and the source-checkout requirement. `run_arm._inject_query` is untouched; `test_3` still pins it.

## Row test node ids

This plan completes no row (TOOL-05's row file is 15-18's `databasise/tests/test_dry_run_default.py`). Supporting nodes in `databasise/tests/parity/test_build_hipporag_index.py`, with fail-first evidence run against the unchanged source of the relevant task (no `record-fail --at` needed, not a row file):

- `test_main_without_spend_is_estimate_only` - before: `AssertionError: main([]) raised AssertionError('store_lock was reached')`
- `test_spend_on_an_empty_store_root_builds` - before: `AssertionError: main(['--spend']) raised MissingParityLightRAGIndexError('the Phase 3 v1-built LightRAG index is not present at ...')`
- `test_an_empty_chunk_namespace_is_a_named_refusal` - before: `AssertionError: a build with no chunk vectors was reported as built`

## Test results

- Task 1 set (`test_build_hipporag_index`, `test_cli_builder_refusals`, `test_parity_cli_store_lock`): 17 passed.
- Plan verify (`databasise/tests/parity`, protected `tests/seam/test_hipporag_write_path.py`, protected `tests/parts_core/hipporag`): 314 passed, 3 deselected. No protected test failed or was edited.
- The full wave gate and `check_offline_suite.py` were not run (orchestrator-owned).

## Deviations from Plan

- **[Rule 1 - Bug, test only] Shared Part singleton.** The first draft of `test_an_empty_chunk_namespace_is_a_named_refusal` assigned the stub body straight onto the registry's `Part`, which is a module-level singleton shared by `default_registry()`; 16 later HippoRAG tests failed. Fixed with `monkeypatch.setattr` on the part's `body` before commit; the committed test restores it.
- The BAK edit hook refused a scripted (python heredoc) edit of the source; the edits were redone with the Edit tool. No content change.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- databasise/parity/build_hipporag_index.py and databasise/tests/parity/test_build_hipporag_index.py FOUND
- commits b92206c and 9228a47 are ancestors of HEAD
