---
phase: 12-hipporag-fixes
plan: 07
subsystem: hipporag-query-path
tags: [hipporag, embedding, query-vector, effects, port-record]
status: complete
requires:
  - phase: 12-hipporag-fixes
    provides: 12-01 shared dense_passage_retrieval helper; 12-05 query-side pruning (six nodes, write selector no longer resolves to HippoRAG)
provides:
  - fact-score output key query_vector (the single embed of the query)
  - dense_passage_retrieval(*, query_vector, chunks_store) returning the raw score_all items
  - reset-vector-join and dpr-fallback with fact-score as a direct dep and calls_embedding dropped
  - HIPP-12 row test
affects: [12-10, 12-11]
actuals:
  tokens: 9500
  tasks: 2
  commits: 2
plan_head_before: 0e767a436c86783ddce7443d6667a4a9d623a930
plan_head_after: 13fd6cb8e4864fd601c8c99aa01c8d54b399f148
tech-stack:
  added: []
  patterns: ["a shared per-query value travels as a named output key over a direct dep, never recomputed per node"]
key-files:
  created: []
  modified:
    - databasise/parts_core/hipporag/fact_score.py
    - databasise/parts_core/hipporag/dpr_fallback.py
    - databasise/parts_core/hipporag/reset_vector_join.py
    - databasise/wirings/hipporag/base.json
    - databasise/tests/seam/test_hipporag_query_path.py
    - databasise/tests/parts_core/hipporag/test_dpr_fallback_guard.py
    - databasise/tests/parts_core/hipporag/test_registration.py
    - databasise/tests/parts_core/hipporag/test_ppr.py
    - databasise/evidence/HIPPORAG-PORT-RECORD.md
key-decisions:
  - "D-17: the query is embedded once at fact-score; reset-vector-join and dpr-fallback read ctx.inputs['fact-score']['query_vector'] over a direct dep"
  - "reset-vector-join declares [reads_vector, reads_kv] and dpr-fallback [reads_vector]; both are recorded as narrowings of PARTS.md section H"
requirements-completed: [HIPP-12]
---

# Phase 12 Plan 07: One embed per HippoRAG query Summary

A HippoRAG query now embeds its text exactly once: fact-score emits `query_vector`, and reset-vector-join and dpr-fallback reuse that list over a direct dep instead of each calling the embedding client again (three calls before, one now).

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Tracer: a HippoRAG query embeds once and runs only query-side nodes (HIPP-12, D-17) | 010ce84 |
| 2 | Record the narrowed effects and added deps against section H (D-17) | 13fd6cb |

## HIPP row, intended ledger test_ref, fail-first evidence

| Row | Intended test_ref | Fail-first evidence |
|-----|-------------------|---------------------|
| HIPP-12 | `databasise/tests/seam/test_hipporag_query_path.py::test_a_query_runs_only_query_side_nodes_and_embeds_once` | Run against the source as left by 12-05 (before the fix), plain AssertionError: `Differing items: {'embed_calls': [['What did Ed Wood direct?'], ['What did Ed Wood direct?'], ['What did Ed Wood direct?']]} != {'embed_calls': [['What did Ed Wood direct?']]}`. The index-node and write-selector items were already identical at that point (12-05 landed the pruning). At the phase base 0807948 the trace leg also fails (thirteen trace nodes); that run was not repeated here. Passes after the fix. |

Supporting tests: `tests/parts_core/hipporag/test_dpr_fallback_guard.py::test_fact_score_emits_the_exact_vector_it_received_from_the_embedding_client` (encoding edge), `::test_dpr_fallback_scores_match_reset_vector_joins_own_passage_weight_scores` (precision edge: item scores equal `score_all` of that vector), `::test_dpr_fallback_declares_reads_vector_only_and_calls_no_cut` (renamed).

Edge coverage: the default stub LLM keeps no facts, so the row test exercises the guard-fired path (fact-score finds nothing usable, dpr-fallback reuses the vector, one embed). The blank-query edge is refused before any node runs by existing seam code and was not re-tested here.

## Verification

- `pytest -q tests/seam/test_hipporag_query_path.py tests/parts_core/hipporag tests/seam/test_cross_modality_run.py tests/seam/test_compare.py tests/parity/test_build_hipporag_index.py`: 89 passed (before the extra edge test).
- `pytest -q tests/seam tests/parts_core tests/wirings tests/parity tests/evidence tests/mcp`: 1408 passed, 3 deselected.
- `pytest -q tests/parts_core/hipporag tests/evidence/test_hipporag_port_record.py tests/wirings tests/runner`: 231 passed.
- Acceptance greps: `query_vector` present in all three part files; no `clients["embedding"]` in dpr_fallback.py or reset_vector_join.py; `top_k` count in dpr_fallback.py is 0.

## Deviations from Plan

**1. [Rule 3 - Blocking] Effects narrowing and registration pin moved into Task 1's commit.**
- Issue: the parts stop calling the embedding client in Task 1, so their Part effects had to change there (a part that still declared `calls_embedding` would be wrong), which made `test_registration.py` fail at the Task 1 commit.
- Fix: the Part and base.json effects, `test_registration.py::_EXPECTED_SHAPE` and the dpr-fallback effects pin went into Task 1's commit; Task 2 holds the port record only.
- Commit: 010ce84.

**2. [Rule 3 - Blocking] `tests/parts_core/hipporag/test_ppr.py` edited (not in the plan's file list).**
- Issue: `test_reset_vector_join_seeds_the_matching_chunk_vertex_and_ppr_ranks_it_first` builds a reset-vector-join context with no `fact-score` input and an embedding client, which the new signature no longer uses.
- Fix: the test embeds "q" itself and passes the vector as the `fact-score` input.
- Commit: 010ce84.

**3. Not changed: `tests/evidence/test_hipporag_port_record.py`.** The divergent-node set is computed from Part effects, so the two new reconciliation rows satisfied it without edits.

Also: `reset-vector-join` and `dpr-fallback` no longer emit a `tokens` key (they spend none); the embed's token accounting is carried by fact-score alone.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- Commits 010ce84 and 13fd6cb are ancestors of HEAD.
- All files listed under key-files exist.
