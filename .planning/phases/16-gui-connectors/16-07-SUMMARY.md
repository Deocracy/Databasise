---
phase: 16-gui-connectors
plan: 07
subsystem: api
tags: [fastapi, operator-surface, faiss, evidence, read-only]
requires: [16-04]
provides:
  - "FaissVectorStore.list_ids(offset, limit): sorted committed ids and total, no reconstruct, no directory"
  - "Databasise.chunk_page(selector, page) and POST /chunks returning {refs, total, next_offset}"
  - "tests/stores/test_console_reads.py: first store-level spy file for console reads"
affects: [16-08, 16-10]
status: complete
commits: 3
plan_head_before: ba7fc0d
plan_head_after: 78e257f6f5e27af0d0a19168fffef94e8ce44796
actuals:
  tokens: 4000
  tasks: 2
  commits: 3
tech-stack:
  added: []
  patterns:
    - "namespace for a chunk page = evidence_position.namespace of the resolved family's base wiring; a request never names a namespace"
key-files:
  created:
    - databasise/tests/seam/test_console_chunks.py
    - databasise/tests/stores/test_console_reads.py
  modified:
    - databasise/stores/vector.py
    - databasise/seam/engine.py
    - databasise/seam/operator_rest.py
key-decisions:
  - "chunk_page builds one FaissVectorStore for the namespace only; _build_stores, graph and KV stores are never touched"
requirements-completed: [CONN-10]
---

# Phase 16 Plan 07: Chunk page Summary

`POST /chunks {selector, limit, offset}` pages the chunk references of the modality a selector resolves to (`chunks` for LightRAG, `hipporag-chunks` for HippoRAG). References carry no text and each opens through `/evidence/resolve`. The read pages `sorted(load_committed(dir).entries)` via a new `FaissVectorStore.list_ids`, so it reconstructs no vector, builds no graph or KV store, and creates no directory for a never-populated namespace.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 (RED) | b7ea3b3 | CONN-10 row test, failing (route absent) |
| 1 (GREEN) | 88a4837 | `list_ids`, `chunk_page`, `ChunksRequest`, POST /chunks |
| 2 | 78e257f | `test_list_ids_never_reconstructs` and `test_chunks_read_builds_no_store_and_refuses_by_name` |

Tracer gate: the Task 1 verify set (8 files) passed, 65 passed, before Task 2. HippoRAG `total` after one stub ingest was 1.

## CONN row test node ids and fail-first evidence

| Row | Intended test_ref | Fail-first |
|-----|-------------------|------------|
| CONN-10 | `databasise/tests/seam/test_console_chunks.py::test_chunks_page_lists_the_selected_modalitys_refs` | At b7ea3b3 (test present, source unchanged): the HippoRAG ingest returned 200, then `AssertionError: (404, '{"detail":"Not Found"}')` / `assert 404 == 200` at the first POST /chunks. Use `record-fail --at b7ea3b3`. |
| CONN-10 (evidence) | `databasise/tests/stores/test_console_reads.py::test_list_ids_never_reconstructs` | With the three source files temporarily reverted to b7ea3b3 (not committed): `AssertionError: FaissVectorStore has no list_ids (CONN-10)`. |
| CONN-10 (evidence) | `databasise/tests/seam/test_console_chunks.py::test_chunks_read_builds_no_store_and_refuses_by_name` | Same revert: `AssertionError: (404, '{"detail":"Not Found"}')`. |

The test file does not exist at the phase base, so b7ea3b3 is the earliest commit where the node exists and fails.

## Test results

- Task 1 verify set: 65 passed.
- Task 2 verify set (`test_console_reads`, `test_console_chunks`, `test_build_stores_cleanup`, `test_page_bounds`): 32 passed.
- Phase guard suite plus the console files and the protected vector and evidence files named in the plan (34 files): 413 passed, 1 error. The error is `test_build_stores_cleanup.py::test_resolve_evidence_opens_no_kv_store`, `fixture 'synthetic_naive_store' not found`. It is a collection-order artifact of that mixed command: the same error appears with this plan's source reverted to b7ea3b3 and without the new test files, and the file passes alone (6 passed) and in the plan's verify sets. No protected test failed or was edited.
- Full offline gate not run in this plan.

## Deviations from Plan

- Task 1 split into RED and GREEN commits so the row node has a committed failing state for `record-fail --at`, as 16-04 and 16-06 did. Task 2's tests were committed after the code landed; their fail-first state was shown by a temporary working-tree revert of the source files, never committed.
- The row test imports the HippoRAG stub helpers as `databasise.tests.seam.test_hipporag_write_path`, matching `test_console_ledger.py`'s import style. The helper file is unchanged.
- Commit trailer names Claude Sonnet 5.5 per the shared rules.

## Known Stubs

None.

## Threat Flags

None. T-16-17 (no text key in refs), T-16-18 (the `_build_stores` spy and no-directory asserts) and T-16-19 (the `reconstruct` spy) are covered by the tests above.

## Self-Check: PASSED

Files found: `databasise/tests/seam/test_console_chunks.py`, `databasise/tests/stores/test_console_reads.py`, `databasise/stores/vector.py`, `databasise/seam/engine.py`, `databasise/seam/operator_rest.py`. Commits b7ea3b3, 88a4837, 78e257f are ancestors of HEAD.
