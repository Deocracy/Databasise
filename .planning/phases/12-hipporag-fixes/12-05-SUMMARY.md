---
phase: 12-hipporag-fixes
plan: 05
subsystem: wirings
tags: [hipporag, query-pruning, capability-selector, fact-filter]
status: complete

requires:
  - phase: 12-hipporag-fixes
    provides: 12-04 ingest-side fixes (OpenIE failure counting, fact chunk-id union)
provides:
  - "without_recipe_only_nodes keeps the ancestors of provides over deps (same name, same engine alias)"
  - "capability matching unions effects over the pruned copy, so write effects of index-side nodes never select a query wiring"
  - "fact-filter is in the HippoRAG consumes_query, so it receives the query text"
  - "tests/seam/test_hipporag_query_path.py, the module 12-07, 12-10 and 12-11 add row tests to"
affects: [12-07, 12-10, 12-11, 12-13]

actuals:
  tokens: 6500
  tasks: 2
  commits: 2
plan_head_before: 2fc25efa2bb29d3ede6bb5726809a789863f62e9
plan_head_after: 65cf15e1070b901492ad079170861b764821bec0
commits: 2

tech-stack:
  added: []
  patterns: ["run copy = closure of provides over deps; recipe-only rule kept as the fallback when provides names no node"]

key-files:
  created:
    - databasise/tests/wirings/test_query_run_pruning.py
    - databasise/tests/seam/test_hipporag_query_path.py
  modified:
    - databasise/wirings/resolve.py
    - databasise/seam/selectors.py
    - databasise/wirings/hipporag/base.json

key-decisions:
  - "D-16 applied as planned: pruning generalised in place, _wiring_effects untouched, node-count tie-break still on the full wiring"
  - "D-18 applied as planned: fact-filter added to base.json consumes_query; no engine edit"

requirements-completed: [HIPP-12, HIPP-05]

duration: 20min
completed: 2026-10-19
---

# Phase 12 Plan 05: Query-run pruning and the fact-filter query Summary

A HippoRAG query run now dispatches only its six query-side nodes, no write-effect capability selector resolves to the HippoRAG wiring, and `fact-filter` receives the query text.

## Accomplishments

- `without_recipe_only_nodes` (`databasise/wirings/resolve.py`) keeps the closure of `provides` over `deps`, `provides` included. When `provides` is empty or names no node it applies the old recipe-only rule. HippoRAG drops exactly its seven index nodes; the five LightRAG arms keep the node set the old rule gave (asserted per arm by the new tests). The engine alias `_without_recipe_only_nodes` is untouched, and the protected LRAG-19 file `tests/seam/test_query_trace_nodes.py` passes unedited.
- `_match_capability` (`databasise/seam/selectors.py`) filters on the effect union of the candidate's pruned copy. `[writes_graph]` no longer resolves to HippoRAG, `[writes_artifact]` now resolves to nothing, `[reads_graph, reads_kv]` still resolves to HippoRAG. `_wiring_effects` has no hunk in the commit, so promotion's `declared_surface` and the compare `mutates_store` refusal still see full wirings.
- `databasise/wirings/hipporag/base.json` `consumes_query` is `["fact-score", "fact-filter", "reset-vector-join", "dpr-fallback"]`.

## Ledger rows (intended test_ref, fail-first evidence)

Fail-first runs were made on the unchanged source (HEAD 2fc25ef) before any source edit; the failures are plain `AssertionError`s.

| Row | Intended test_ref | Fail-first evidence (pre-fix) |
|-----|-------------------|-------------------------------|
| HIPP-05 | `databasise/tests/seam/test_hipporag_query_path.py::test_fact_filter_prompt_carries_the_query_between_the_markers` | `AssertionError: assert {'What did Ed...e film ?': ''} == {...}` with `{'What did Ed Wood direct?': ''} != {'What did Ed Wood direct?': 'What did Ed Wood direct?'}` (captured query section is `''`) |
| HIPP-12 (trace and selector legs only; the row test is `test_a_query_runs_only_query_side_nodes_and_embeds_once` in 12-07) | supporting: `databasise/tests/seam/test_hipporag_query_path.py::test_a_hipporag_query_trace_names_only_query_side_nodes`, `databasise/tests/wirings/test_query_run_pruning.py::test_hipporag_pruning_keeps_exactly_the_query_side_nodes`, `::test_a_write_effect_selector_no_longer_resolves_to_the_hipporag_wiring`, `::test_writes_artifact_is_unsatisfiable` | trace test: `AssertionError: {'assemble-result', 'chunk-embed', 'dpr-fallback', 'entity-fact-embed', 'fact-edges', 'fact-filter', ...}` with `assert {'chunk-embed...e-edges', ...} == set()`; pruning test: `AssertionError: assert {'assemble-re...-filter', ...} == {'assemble-re...-vector-join'}` (extra `chunk-embed`, `openie`, `graph-augment-persist`, `entity-fact-embed`, `fact-edges`...); write selector: `AssertionError: hipporag` / `assert 'hipporag' != 'hipporag'`; writes_artifact: `AssertionError: lightrag` / `assert False where False = isinstance('lightrag', UnsatisfiableSelectorError)` |

Passing runs: Task 1 targeted run (pruning, query path, `test_query_trace_nodes.py`, `test_promote.py`) 41 passed. Task 2 targeted run (query path, parity build, parts_core hipporag) 71 passed. Plan verification `pytest -q tests/seam tests/wirings tests/parity tests/parts_core tests/mcp`: 1322 passed after Task 1, 1323 passed after Task 2 (3 deselected, no live runs).

The HIPP-05 row test lives in the same module as the HIPP-12 trace test, so the module was committed with only the trace test in Task 1 and gained the HIPP-05 test and `_CapturingFactFilterLLMClient` in Task 2. Edge rows: the one-character and blank-query rows hold structurally (SEAM-09 refuses a blank query before any node runs; the engine stamps the query verbatim), and the non-ASCII row is asserted by the second query in the HIPP-05 test. The no-truncation row is a backstop.

## Task Commits

1. Task 1 (tracer): `3fd6e4c` fix(12-05): a query run keeps only the ancestors of provides and capability matching sees that pruned run (HIPP-12). Tracer gate: the end-to-end verify command passed before the commit, so the plan expanded to Task 2.
2. Task 2: `65cf15e` fix(12-05): fact-filter receives the query text (HIPP-05)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None.

## Threat Flags

None. T-12-07 is mitigated: a query run never dispatches write-effect index nodes and write effects no longer select a query wiring.

## Issues Encountered

None. Note for the ledger owner: `[writes_artifact]` formerly resolved to a LightRAG arm and now raises `UnsatisfiableSelectorError`, the intended D-16 consequence.

## Self-Check: PASSED

Files found: resolve.py, selectors.py, hipporag/base.json, test_query_run_pruning.py, test_hipporag_query_path.py. Commits 3fd6e4c and 65cf15e are ancestors of HEAD.
