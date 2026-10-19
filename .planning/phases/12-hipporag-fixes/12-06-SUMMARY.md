---
phase: 12-hipporag-fixes
plan: 06
subsystem: hipporag-corpus
tags: [hipporag, delete, document-remover, manifest, write-gate, D-12, D-14]
requires: ["12-01", "12-03", "12-04"]
provides:
  - "hipporag/document-remover@0.1.0 part, HIPPORAG_CORPUS_PARTS, wirings/hipporag/corpus-delete.json"
  - "doc:<document_id> manifest {chunk_ids, fact_ids, entities, ingested_at} in hipporag-text-chunks, written with the data"
  - "delete_document routes a HippoRAG selector to its own delete wiring and enters the v1 gate only for LightRAG"
  - "_serialising_write_gate: HippoRAG ingests and deletes queue per workspace, 409 only after the wait ceiling"
affects: [12-08, 12-13]
tech-stack:
  added: []
  patterns: ["manifest-driven removal staged in one all-or-none commit", "polling threading.Lock gate that never blocks the loop"]
key-files:
  created:
    - databasise/parts_core/hipporag/document_remover.py
    - databasise/wirings/hipporag/corpus-delete.json
    - databasise/tests/parts_core/hipporag/test_document_remover.py
    - databasise/tests/seam/test_hipporag_write_gate.py
  modified:
    - databasise/parts_core/hipporag/__init__.py
    - databasise/parts/registry.py
    - databasise/parts_core/hipporag/chunk_embed.py
    - databasise/parts_core/hipporag/entity_fact_embed.py
    - databasise/seam/engine.py
    - databasise/tests/seam/test_hipporag_write_path.py
    - databasise/tests/parts/test_registry.py
key-decisions:
  - "D-12: the remover reduces shared facts, edges and entities and deletes only what no surviving document supports; it stages only, the engine commits"
  - "D-14: the HippoRAG gate is taken before _build_stores and polls; _write_gate (LightRAG, LRAG-04) has no hunk"
requirements-completed: [HIPP-16]
status: complete
commits: 3
plan_head_before: d1958d3c1dd781b6dd30010f110fbd70ae35d675
plan_head_after: b73ba426c57c93835895b0ca30ec3eca9d7faa46
actuals:
  tokens: 12800
  tasks: 3
  commits: 3
metrics:
  completed: 2026-10-19
---

# Phase 12 Plan 06: HippoRAG document delete and serialised writes Summary

A HippoRAG-selected `delete_document` now removes a document's chunk vectors, chunk KV rows, `doc:<id>` manifest, chunk vertices and exactly the facts, edge weights and entities no other document supports, and HippoRAG writes queue on a per-workspace gate instead of interleaving.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 (tracer) delete through `delete_document` | 8859fd1 | remover part, `corpus-delete.json`, manifest writers in chunk-embed and entity-fact-embed, family-selected v1 gate, registry registration |
| 2 remover keeps shared contributions | 9ec90c9 | six tests in `test_document_remover.py` |
| 3 D-14 serialising gate | b73ba42 | `_serialising_write_gate`, `_hipporag_gate_path`, `AsyncExitStack` in ingest and delete, four gate tests |

Tracer gate: the Task 1 verify command (44 tests) passed before Tasks 2 and 3 started.

## Ledger test_ref (intended)

HIPP-16 is the only requirement in this plan. Its row test is not written here: it is `test_reingest_leaves_no_stale_chunk_and_delete_removes_everything`, added by 12-08 (the plan states "This plan adds no row test"). Supporting tests from this plan that 12-08's row builds on:

| Behaviour | test node id |
|-----------|--------------|
| delete removes the document, second delete not_found | `databasise/tests/seam/test_hipporag_write_path.py::test_a_hipporag_delete_removes_the_document_and_a_second_delete_is_not_found` |
| shared fact, entity and edge kept | `databasise/tests/parts_core/hipporag/test_document_remover.py::test_deleting_one_document_keeps_what_another_still_contributes` |
| gate serialises | `databasise/tests/seam/test_hipporag_write_gate.py::test_two_hipporag_ingests_on_one_workspace_never_run_their_store_phases_at_once` |
| gate 409 after ceiling | `databasise/tests/seam/test_hipporag_write_gate.py::test_a_waiter_past_the_ceiling_is_refused_with_a_409_and_builds_no_store` |

## Fail-first evidence

Run on the source before each change (unchanged HEAD d1958d3, tests written first).

Task 1, delete (captured exception, so an AssertionError):

```
E       AssertionError: NoWritePathForModalityError("NoWritePathForModalityError: no write path exists for operation 'delete'")
tests/seam/test_hipporag_write_path.py:290: AssertionError
```

Task 1, REST/MCP parity delete leg: `assert 422 == 200` (REST answered the old refusal).

Task 3, overlap (embedding intervals of two gathered ingests):

```
E       assert [((271147.920566571, 271147.970816951), (271147.920591708, 271147.971117963))] == []
E         Left contains 4 more items
```

Task 3, ceiling: `AssertionError: None / assert False where False = isinstance(None, StoreBusyError)` (the ingest simply ran).

Task 2 tests passed on their first run, because Task 1's remover already existed. They were checked by mutation instead, each reverted from a saved copy and never committed: always deleting a fact made `test_deleting_one_document_keeps_what_another_still_contributes` fail (`TypeError: 'NoneType' object is not subscriptable` on the shared fact); skipping the co-occurrence reduction made it fail on `assert 2.0 == 1.0`; deleting every reduced edge made it fail.

## Verification

- Task 1 command (`test_hipporag_write_path.py`, `test_delete_commit_contract.py`, `test_corpus_write_gate.py`, `test_delete_document.py`): 44 passed.
- Task 2 command: 6 new tests passed with `test_hipporag_write_path.py`.
- Task 3 command (`test_hipporag_write_gate.py`, `test_ingest_abort.py`, `test_concurrent_ingest_failure.py`, `test_corpus_write_gate.py`, `test_build_stores_cleanup.py`): 42 passed, all protected files unedited.
- Plan verification: `pytest -q tests/seam tests/stores tests/parts_core tests/parts tests/wirings tests/parity tests/mcp` -> 1526 passed, 3 deselected.
- Acceptance greps: `HIPPORAG_DOCUMENT_REMOVER_PART` in two files, `HIPPORAG_CORPUS_PARTS` in registry.py, corpus-delete `provides` prints `['document-remover']`, the old named-refusal delete test is absent, one `_serialising_write_gate` definition, `_HIPPORAG_GATE_WAIT_SECONDS` on four lines, no diff hunk inside `_write_gate`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Registry count pin**
- **Found during:** Task 1
- **Issue:** `tests/parts/test_registry.py::test_default_registry_holds_exactly_thirty_six_entries` pinned 36 registered parts; registering the remover makes 37. The file is not named in the plan, not a protected ledger file (the edit guard allowed the edit), and nothing else references the name.
- **Fix:** count 36 to 37, test renamed `..._thirty_seven_entries`, docstring extended.
- **Files modified:** `databasise/tests/parts/test_registry.py`
- **Commit:** 8859fd1

Later Phase 12 plans that add a part (12-09 `qa`) will need the same bump.

**Total deviations:** 1 auto-fixed (1 blocking). **Impact:** none beyond the pin.

## Known Stubs

None.

## Threat Flags

None. T-12-08 mitigated (removal driven only by the document's own manifest; a fact, edge or entity another document still supports is reduced, never removed; `test_document_remover.py`). T-12-09 mitigated (gate before stores are built; ceiling then 409; `test_hipporag_write_gate.py`).

## Notes

- Stores written before Phase 12 carry no `doc:` manifest; a delete of such a document reports `not_found`. They must be rebuilt (D-12, to be recorded by 12-13).
- `removed_entities` is returned by the part and consumed in 12-08 (re-ingest keeps synonymy edges); no consumer exists yet.
- Orphan detection treats an entity as orphaned when it has no neighbour starting with `chunk:` after the document's chunk vertices are hidden.

## Self-Check: PASSED

Commits 8859fd1, 9ec90c9 and b73ba42 are ancestors of HEAD; `document_remover.py`, `corpus-delete.json`, `test_document_remover.py` and `test_hipporag_write_gate.py` exist and are committed.
