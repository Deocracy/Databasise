---
phase: 12-hipporag-fixes
plan: 11
subsystem: hipporag-query-path
tags: [hipporag, top-k, assemble-result, evidence-bound]
status: complete
requires:
  - phase: 12-hipporag-fixes
    provides: 12-10 qa node reading assemble-result items
provides:
  - assemble-result config.top_k (default 5), one cut on both branches
  - zero-score PPR items dropped before the cut
  - HIPP-11 row test and assemble-result unit tests
affects: [12-13]
actuals:
  tokens: 9000
  tasks: 2
  commits: 2
plan_head_before: 0c003f8b0c92a9c22296a207015d39bffe0605b1
plan_head_after: 4ddf741bb570db7fe7725d7f471c7d24ee7f45c4
tech-stack:
  added: []
  patterns: ["one cut in the assembler bounds both the evidence and the qa input"]
key-files:
  created:
    - databasise/tests/parts_core/hipporag/test_assemble_result.py
  modified:
    - databasise/parts_core/hipporag/assemble_result.py
    - databasise/wirings/hipporag/base.json
    - databasise/tests/seam/test_hipporag_query_path.py
key-decisions:
  - "D-20: top_k (default 5, upstream qa_top_k) is applied after branch selection and before hydration; PPR items with score <= 0.0 are dropped first; dpr-fallback is never cut itself"
requirements-completed: [HIPP-11]
---

# Phase 12 Plan 11: HippoRAG top_k cut Summary

A HippoRAG query now returns at most `top_k` (default 5) items on both the PPR and the DPR branch, with zero-score PPR items dropped first, so answer and evidence size no longer grow with the corpus.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Tracer: a query over twenty documents returns at most top_k items on both branches (HIPP-11, D-20) | ddcd56c |
| 2 | top_k value change and zero-score PPR drop pinned (D-20, D-22) | 4ddf741 |

## HIPP row, intended ledger test_ref, fail-first evidence

| Row | Intended test_ref | Fail-first evidence |
|-----|-------------------|---------------------|
| HIPP-11 | `databasise/tests/seam/test_hipporag_query_path.py::test_a_query_returns_at_most_top_k_items_on_both_branches` | Run against the source as left by 12-12 (no cut), plain AssertionError: `assert {'dpr_within_top_k': False, 'ppr_within_top_k': False, 'ppr_scores_positive': True} == {... all True}` (differing items `dpr_within_top_k` and `ppr_within_top_k`). Passes after the fix. |

Supporting tests in `databasise/tests/parts_core/hipporag/test_assemble_result.py`: `test_top_k_value_change_changes_how_many_items_pass_on` (top_k 5 passes 5 items, top_k 2 passes 2, D-22), `test_top_k_defaults_to_five_and_returns_all_when_fewer`, `test_the_ppr_branch_drops_zero_score_items_and_keeps_order`, `test_an_all_zero_ppr_branch_passes_no_item_on`, `test_the_dpr_branch_keeps_zero_score_items_within_the_cut`. Fail-first for these: with only `assemble_result.py` reverted to its pre-Task-1 state in the working tree, 4 of the 5 failed (the DPR keep-zero test passes before and after, by design: it pins that DPR is not filtered); the change was then restored and not committed as a revert. Example failure: `AssertionError: assert ['c0', 'c1'] == []` (all-zero PPR branch).

Edges covered: boundary (more/fewer than top_k), adjacency (score exactly 0.0 dropped), empty (all-zero PPR yields no item), ordering (input order kept, no re-sort). The `empty` edge's end-to-end qa answer of `PROMPTS['fail_response']` rests on 12-10's `test_no_passage_content_answers_fail_response_without_an_llm_call`. Idempotency, precision and concurrency are inherent in the stateless slice/compare (precision and concurrency are backstop-verified per the plan).

## Verification

- Task 1 verify: `pytest -q tests/seam/test_hipporag_query_path.py tests/parts_core/hipporag`: 82 passed.
- Task 2 verify and wave command `pytest -q tests/seam tests/parts_core tests/wirings tests/parity tests/evidence tests/mcp tests/eval`: 1493 passed, 3 deselected.
- Acceptance: `"top_k": 5` appears once in base.json; `top_k` appears in assemble_result.py; the row test exists in test_hipporag_query_path.py.

## Deviations from Plan

None - plan executed exactly as written. The port record's statement of the default is carried by 12-13 (its plan lists the D-20 entry), not this plan's file list.

## Known Stubs

None.

## Threat Flags

None. T-12-26 (response and qa prompt size) is mitigated by the one cut, proven over twenty documents.

## Self-Check: PASSED

- Commits ddcd56c and 4ddf741 are ancestors of HEAD.
- `test_assemble_result.py` exists.
