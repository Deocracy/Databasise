---
phase: 12-hipporag-fixes
plan: 02
subsystem: hipporag
tags: [hipporag, graph-construction, token-accounting, D-02, D-07]
requires: []
provides:
  - "openie `chunks` passthrough; passage-edges `vertices` stream; graph-augment-persist upserts it"
  - "runner.trace.UNBUDGETABLE_SENTINEL and runner.trace.sum_token_accountings (single definitions)"
affects: [12-03]
tech-stack:
  added: []
  patterns: ["one shared token-sum helper; mixed counted_by labels collapse to the sentinel"]
key-files:
  created:
    - databasise/tests/runner/test_token_sum.py
  modified:
    - databasise/parts_core/hipporag/openie.py
    - databasise/parts_core/hipporag/passage_edges.py
    - databasise/parts_core/hipporag/graph_augment_persist.py
    - databasise/parts_core/hipporag/entity_fact_embed.py
    - databasise/runner/trace.py
    - databasise/seam/tokens.py
    - databasise/tests/parts_core/hipporag/test_graph_construction.py
key-decisions:
  - "D-02: every chunk chunk-embed produces gets a chunk: vertex, carried openie -> passage-edges -> graph-augment-persist without changing the frozen deps"
  - "D-07: token-sum rule lives only in runner.trace; seam/tokens.py re-exports the sentinel"
requirements-completed: [HIPP-06, HIPP-19]
status: complete
commits: 2
plan_head_before: 2dc998cb24973f5323f94b47f4f66f851b0f50e3
plan_head_after: ccc92d02c5fea1ea5277670a6e248441a0b75349
actuals:
  tokens: 6500
  tasks: 2
  commits: 2
metrics:
  completed: 2026-10-19
---

# Phase 12 Plan 02: Chunk vertices for triple-less chunks and a single token-sum helper Summary

Every chunk now gets a passage vertex even when OpenIE finds no triple in it, and HippoRAG ingest token accounting reports `unbudgetable` instead of one tokenizer's label when two counters were mixed, through one shared `sum_token_accountings`.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 (tracer) HIPP-06 | b238bff | openie returns `chunks` on every path; passage-edges emits sorted `vertices`; persist upserts them |
| 2 HIPP-19 | ccc92d0 | `sum_token_accountings` + `UNBUDGETABLE_SENTINEL` in runner/trace.py; openie, entity-fact-embed, seam/tokens use them |

Tracer gate: the Task 1 tracer ran end to end (chunk-embed, openie, fact/passage edges, persist, `export_to_igraph`) and passed before Task 2 started.

## Ledger test_ref (intended)

| Row | test node id |
|-----|--------------|
| HIPP-06 | `databasise/tests/parts_core/hipporag/test_graph_construction.py::test_a_chunk_with_no_triples_still_gets_a_passage_vertex` |
| HIPP-19 | `databasise/tests/runner/test_token_sum.py::test_mixed_counters_never_share_one_label` |

Fail-first route for both: `record-fail --at 0807948ae0277f627b7bf51c37bcce82e91a40da` (phase base). Both files collect at that commit: no Phase 12 symbol is imported at module level (`test_token_sum.py` uses `getattr(trace, ...)` for the helper and an in-body import in the second test). `test_graph_construction.py` also receives HIPP-07/08 row tests in 12-03; record its rows only after 12-03.

## Fail-first evidence

Both row tests were written and run before any source change; both fail by plain AssertionError.

HIPP-06:

```
E       AssertionError: assert {'chunk:367b1...9eee2262edc6'} <= {'chunk:367b1... 'entity:mat'}
E         Extra items in the left set:
E         'chunk:bd99b7bf55175d524530ddbe222553d0c84f869cabab2208879c9eee2262edc6'
```

HIPP-19 (the helper-exists assertion is last, so the quoted failure is the first-label-wins behaviour):

```
E       AssertionError: assert 'tiktoken' == 'unbudgetable'
```

## Verification

- Task 1 command: `pytest -q tests/parts_core/hipporag/test_graph_construction.py tests/parts_core/hipporag/test_index_side_extraction.py tests/seam/test_hipporag_write_path.py` -> 37 passed.
- Task 2 command 1: `pytest -q tests/runner/test_token_sum.py tests/parts_core/hipporag tests/runner tests/seam/test_hipporag_write_path.py` -> 178 passed.
- Task 2 command 2 / plan verification: `pytest -q tests/parts_core tests/seam tests/stores tests/runner tests/parity tests/clients` -> 1537 passed, 4 deselected.
- Acceptance greps: `UNBUDGETABLE_SENTINEL = ` appears once under runner/seam/parts_core (runner/trace.py:65); no `_sum_token_accountings` in openie.py or entity_fact_embed.py; `sum_token_accountings` appears in both; `"vertices"` in passage_edges.py; `"chunks"` twice in openie.py.

## Deviations from Plan

### Auto-fixed Issues

None. One addition beyond the two named tests: `test_passage_edges_vertices_are_sorted_and_empty_for_no_chunks` in test_graph_construction.py pins the plan's ordering and zero-chunk edge truths (a non-row test; it is not a ledger test_ref).

## Known Stubs

None.

## Threat Flags

None. T-12-02 mitigated: mixed labels collapse to the sentinel `assemble_token_breakdown` already refuses.

## Notes

- The BAK edit-guard hook blocked Bash commands that touched test files by grep or scripted edits (error text names an unrelated test file); the Edit and Write tools were used for source edits and no protected file was touched.
- The persisted artifact `node_count` now counts isolated chunk vertices too (it counts all upserted vertices); no test pinned the old value.

## Self-Check: PASSED

Commits b238bff and ccc92d0 are ancestors of HEAD; all eight files exist and are committed.
