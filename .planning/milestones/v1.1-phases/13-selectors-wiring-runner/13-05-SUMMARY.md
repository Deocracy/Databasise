---
phase: 13-selectors-wiring-runner
plan: 05
subsystem: seam
tags: [depth-label, envelope, evidence-minting, engine-internals, dead-api]
requires: []
provides:
  - ResponseEnvelope.depth_label typed Depth | None, null unless a provides node answered
  - a retrieval output without 'items' refused as MalformedDriverOutput (cause MalformedEvidenceItemError)
  - query, query_stream and compare without the discarded debug keyword
affects: [13-07, 13-08]
actuals:
  tokens: 12000
  tasks: 2
  commits: 3
plan_head_before: 6e5ddee
plan_head_after: 6425ddbe2a2802139ea07d1e751320100988e370
tech-stack:
  added: []
  patterns: ["null means 'nothing answered', keyed on the answer, not on partial", "named fault inside the existing minting try"]
key-files:
  created:
    - databasise/tests/seam/test_depth_label.py
    - databasise/tests/seam/test_engine_internals.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/envelope.py
key-decisions:
  - "depth_label is Depth | None with no default; the 'stage' fallback in _select_answer is removed"
  - "An empty completion string counts as answered, so depth_label is that node's depth (flagged assumption, pinned by a test)"
  - "The missing-items refusal is raised inside the existing minting try so the existing handler maps it to MalformedDriverOutput"
requirements-completed: [WIRE-04, WIRE-14]
coverage:
  - id: D1
    description: "depth_label is null when no provides node answered, the answering node's depth otherwise, and refuses free text"
    requirement: WIRE-04
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_depth_label.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Malformed evidence output is a named fault; no discarded keyword remains; delete, resolve and openie legs pinned"
    requirement: WIRE-14
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_engine_internals.py"
        status: pass
    human_judgment: false
duration: 25min
completed: 2026-10-19
status: complete
---

# Phase 13 Plan 05: depth_label tells the truth, engine internals fail by name Summary

**`depth_label` is now `Depth | None` (null when no provides node returned a completion), a retrieval node output without `items` is a named `MalformedDriverOutput` refusal instead of a bare `KeyError`, and `query`/`query_stream`/`compare` no longer carry a `debug` keyword they discarded.**

## Accomplishments

- `seam/envelope.py`: `depth_label: Depth | None`, no default, `Depth` imported from `parts/schema.py`; `depth_label="bogus"` raises a validation error.
- `seam/engine.py`: `_select_answer` returns `tuple[str, Depth | None]` and starts from `None`; docstring states the rule. The two-answering-nodes `RuntimeError` branch is untouched (13-08 owns it).
- `seam/engine.py`: the `items` lookup moved into the minting `try`; a dict output without `items` raises `MalformedEvidenceItemError(... reason="carries no 'items' key")`, which the existing handler turns into `ForeignEngineRefusalError(failure_class="MalformedDriverOutput")`. 13-07 can rely on this guard.
- `seam/engine.py`: `debug` keyword and `del debug` removed from `query`, `query_stream`, `compare` (and their docstring sentences); `resolve_trace` keeps it. REST (`seam/rest.py`) and MCP (`mcp/server.py`) pass `debug` only to `resolve_trace`; no caller under `seam`, `mcp` or `tools` passes it to the three methods. The full `tests/seam tests/mcp` run (protected tests included) passes, so no grant item arose.
- `_build_stores` docstring names `ingest`, `retry_document` through `_run_corpus_ingest`, `delete_document` and `_execute_resolved`; it does not mention `health`.

## Task Commits

1. Task 1 (tracer): cccbb72 - depth_label nullable and typed, `_select_answer` without the stage fallback, `test_depth_label.py`
2. Task 2: a46736e - items guard, dead keyword removal, docstring fix, `test_engine_internals.py`
3. 6425ddb - import order of `test_engine_internals.py`

## Intended ledger test_refs and fail-first evidence

Pre-fix runs were made against the unchanged source at the point each test file was written (Task 1 against the plan-start source 6e5ddee; Task 2 against the Task 1 source). For the touched code these equal the phase base b0b5a6c, which the orchestrator's `record-fail --at` route re-checks. All failures below are plain `AssertionError`.

**WIRE-04** - `databasise/tests/seam/test_depth_label.py`
- `::test_a_run_whose_provides_node_failed_reports_null_depth`: `AssertionError: assert 'stage' is None`
- `::test_an_envelope_refuses_a_free_text_depth`: `AssertionError: assert None is not None` (the bogus label was accepted)
- `::test_no_answering_node_selects_a_null_depth`: `AssertionError: assert 'stage' is None`
- Pass pre-fix by design: `::test_a_naive_run_reports_the_answering_nodes_depth`, `::test_an_empty_completion_counts_as_answered` (flagged-assumption pin), `::test_an_envelope_requires_a_depth_label` (the field was already required)

**WIRE-14** - `databasise/tests/seam/test_engine_internals.py`
- `::test_an_evidence_node_without_items_is_refused_by_name`: `AssertionError: KeyError('items')` / `assert 'KeyError' == 'ForeignEngineRefusalError'`
- `::test_the_query_methods_take_no_discarded_keyword[query|query_stream|compare]`: `AssertionError: assert ('deb' + 'ug') not in mappingproxy(... 'debug': <Parameter "debug: 'bool' = False"> ...)` for each of the three
- `::test_build_stores_docstring_names_its_callers`: `AssertionError: assert 'retry_document' in "kv/vector/graph, all three, ..."`
- Pass pre-fix (legs already met, recorded as satisfied by the STOR-07, STOR-03 and HIPP-04 commits, not re-failed): `::test_delete_opens_the_corpus_delete_wirings_namespaces`, `::test_resolve_evidence_never_builds_the_graph_store`, `::test_resolve_evidence_succeeds_while_the_graph_namespace_is_held`, `::test_a_failed_openie_ingest_names_its_real_exception`, `::test_an_empty_items_list_mints_no_evidence`, `::test_an_undeclared_evidence_position_mints_no_evidence`, `::test_resolve_trace_keeps_its_keyword`, `::test_the_missing_items_refusal_is_raised_before_any_envelope_is_constructed` (no trace row is written; holds before and after)

## Deviations from Plan

**1. [Rule 2 - Missing critical] Extra tests for the plan's non-backstop edge truths**
- Added `test_an_envelope_requires_a_depth_label`, `test_no_answering_node_selects_a_null_depth`, `test_resolve_trace_keeps_its_keyword`, `test_resolve_evidence_succeeds_while_the_graph_namespace_is_held`, `test_an_undeclared_evidence_position_mints_no_evidence` and the ordering test, covering truths the plan lists without a named test. Commits cccbb72, a46736e.

**2. [Wording] Wiring node uses `parts-core/passthrough@1.0.0`, and the empty-items test registers a small `test/emit@1.0.0` part**
- The plan's passthrough already returns a dict without `items` (so no scheduler monkeypatch was needed); `{"items": []}` needs a part that emits it, registered on a fresh `default_registry()` inside the test.

**Total deviations:** 2. **Impact:** none on scope. No protected test was edited.

## Verification

- `cd databasise && .venv/bin/pytest -q tests/seam tests/mcp`: 992 passed (includes the new files).
- `cd databasise && .venv/bin/pytest -q tests/runner tests/validator tests/wirings tests/identity tests/parts tests/parts_core tests/evidence tests/parity tests/eval tests/ledger`: 865 passed, 3 deselected.
- Acceptance greps: `depth_label: Depth | None` present in `seam/envelope.py`; `depth_label = "stage"` absent from `seam/engine.py`; `carries no 'items' key` on one line of `seam/engine.py`.
- `ruff check` on `seam/engine.py` and `seam/envelope.py` reports only findings present at 6e5ddee (I001, 2x RUF100, ASYNC230, 3x RUF012); not fixed (out of scope). The new test file's import order was sorted in 6425ddb.

## Known Stubs

None.

## Threat Flags

None. T-13-10 mitigated (items lookup inside the minting try, test above); T-13-11 mitigated (null unless a provides node answered).

## Self-Check: PASSED

Created files exist (`test_depth_label.py`, `test_engine_internals.py`); commits cccbb72 and a46736e are ancestors of HEAD.
