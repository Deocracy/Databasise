---
phase: 13-selectors-wiring-runner
plan: 10
subsystem: seam
tags: [trace-token, persist-before-raise, refusals, reason-codes, leak-gate]
requires: ["13-04", "13-08"]
provides:
  - RunRecord built and persisted right after the run returns, before any post-dispatch refusal
  - public trace_token on every SeamRefusalError raised after dispatch on the query path (REST and MCP bodies)
  - AmbiguousAnswerPositionError (422, no public attribute) replacing the bare RuntimeError for two answering provides nodes
  - redact.node_free_reason, the never-raising response-time reason check, applied to the envelope and the non-debug trace
  - redact.REASON_VALUE_KEYS substring check in assert_no_forbidden_values
affects: [13-12]
actuals:
  tokens: 30000
  tasks: 3
  commits: 3
plan_head_before: 4b22542f0b12a4a3168a3cbc35d224a2ce2ab98b
plan_head_after: 4567a0faa777b337c4e78d99a0e999610c21de5c
tech-stack:
  added: []
  patterns: ["persist the run record before anything that can refuse; the refusal carries the token", "response-time reason check maps and logs, never raises"]
key-files:
  created: []
  modified:
    - databasise/seam/engine.py
    - databasise/seam/refusals.py
    - databasise/seam/redact.py
    - databasise/tests/seam/test_run_record_identity.py
    - databasise/tests/seam/test_stop_reason_leak.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/seam/test_seam_tracer.py
    - databasise/tests/seam/test_engine_internals.py
key-decisions:
  - "Persist the raw RunRecord; the closed-code mapping happens only on the envelope and the non-debug resolve_trace, so the debug view keeps the stored text untouched"
  - "A stored record of an older shape that lacks identity keys still resolves: the low-entropy set is only used for the log line, so a KeyError there degrades to an empty set"
requirements-completed: [WIRE-12, WIRE-03]
status: complete
duration: 1h 15m
completed: 2026-10-19
---

# Phase 13 Plan 10: Post-dispatch refusals keep their trace; reasons are checked at response time Summary

**A query that runs nodes and then refuses now leaves a resolvable trace (the refusal carries a public `trace_token`), two answering provides nodes are a named 422 refusal instead of a 500, and both consumer reason fields are mapped to the closed codes at response time by a check that never raises.**

## Accomplishments

- `seam/engine.py` `_execute_resolved` (D-04): hash, wiring id and `RunRecord` are built right after `run_wiring` returns, then `self._trace_store.persist(...)`. The store-fault check, `_select_answer`, evidence minting, `assemble_token_breakdown` and `_mach11_events` run inside one `try`; its `except SeamRefusalError as exc` sets `exc.trace_token` and re-raises. `refusal_body` already exports public attributes, so REST and MCP bodies carry the key with no transport change. Pre-dispatch refusals (empty namespace, unsatisfiable selector) carry none.
- `seam/refusals.py`: `AmbiguousAnswerPositionError` (no public attribute, in `__all__`); the `SeamRefusalError` and `ForeignEngineRefusalError` docstrings say a post-dispatch query refusal carries `trace_token`.
- `seam/engine.py` `_select_answer` raises that refusal; the two node ids stay in one server log line.
- `seam/redact.py`: `REASON_VALUE_KEYS`, a substring check on those two keys in `assert_no_forbidden_values` (every other key keeps equality), and `node_free_reason(value, low_entropy)` (None stays None, a closed code passes, anything else becomes `node_failed` with one error log line stating whether a forbidden identity was found, never the value). The docstring keeps the phrase "test-time gate".
- The engine applies `node_free_reason` to the envelope's `stop_reason` and `degradation_reason` and to the same two keys in the non-debug `resolve_trace`; `debug=True` returns the stored record untouched.

## Task Commits

1. Task 1 (tracer): a8e8fd7 - persist-before-raise, public `trace_token`
2. Task 2: 6ac9028 - `AmbiguousAnswerPositionError`
3. Task 3: 4567a0f - response-time reason check and the value-walk substring leg

## Intended ledger test_refs and fail-first evidence

Pre-fix runs were against the source immediately before each task's change (Task 1 tests vs 4b22542 source; Task 2 vs a8e8fd7; Task 3 vs 6ac9028). Every failure is a plain `AssertionError`. Phase-base behaviour on these paths is the same: 13-05 and 13-08 did not touch persist order, `_select_answer` or reason mapping.

**WIRE-12** (ledger test_ref set in 13-12) - `databasise/tests/seam/test_run_record_identity.py`
- `::test_an_unbudgetable_refusal_leaves_a_resolvable_trace`: `AssertionError` at `assert isinstance(token, str), "the refusal carries no trace_token: ..."` (test line 105; `getattr(caught, "trace_token", None)` was `None`)
- `::test_the_trace_token_reaches_the_rest_body`: `AssertionError: {"refusal_type":"UnbudgetableParticipantError","message":"a participant is admitted unbudgetable; no token comparison may include it"}` (`assert isinstance(None, str)`)
- `::test_two_answering_provides_nodes_are_refused_with_a_trace`: `AssertionError: RuntimeError("wiring declares more than one provides position with a completion ('first-answer' and 'second-answer' both did); ...")` / `assert 'RuntimeError' == 'AmbiguousAnswerPositionError'`
- `::test_a_malformed_evidence_refusal_carries_a_trace_token`: passes only once Task 1 lands (written after it; the same `trace_token` attribute is what it asserts, and pre-Task-1 the engine persisted nothing on that path - `tests/seam/test_engine_internals.py` pinned 0 trace rows)
- `::test_a_pre_dispatch_refusal_carries_no_trace_token`: passes by design before and after (negative guard)
- `::test_a_sequential_run_never_has_two_node_bodies_in_flight` (13-04): unchanged

**WIRE-03** (ledger test_ref `databasise/tests/seam/test_stop_reason_leak.py`, set in 13-08) - gate legs added here
- `::test_the_value_walk_flags_a_node_id_inside_a_reason`: `AssertionError: None` / `assert isinstance(None, AssertionError)`
- `::test_a_leaky_scheduler_reason_is_served_as_node_failed`: `assert ("node 'chunk...tionError: X") == ('node_failed', 'node_failed')`
- `::test_a_legacy_stored_reason_resolves_as_node_failed`: same diff on the non-debug resolve
- `::test_closed_codes_pass_unchanged[...]` (six codes), `::test_an_appended_code_is_mapped`, `::test_clean_run_reasons_stay_none`, `::test_a_non_string_reason_is_mapped_and_never_raises`, `::test_the_quoted_and_bare_forms_of_a_node_id_are_both_logged_as_forbidden`: `AssertionError: seam.redact has no node_free_reason`
- `::test_an_answer_containing_a_node_word_is_not_flagged`: passes before and after by design (precision backstop)

## Verification

- `cd databasise && .venv/bin/pytest -q tests/seam tests/mcp tests/runner tests/validator tests/wirings tests/identity tests/parts tests/parts_core tests/evidence tests/parity`: `1915 passed, 3 deselected`.
- `.venv/bin/python -O -m pytest -q tests/seam/test_stop_reason_leak.py`: 17 passed under `-O`.
- Protected `tests/seam/test_seam_doc_consistency.py` (SEAM-16): 17 passed in normal mode; it spawns its own `python -O` subprocesses for the key and value checks, which passed. Running the whole file under `python -O` or `PYTHONOPTIMIZE=1` is blocked by the BAK check-edit-guard hook on that file name, so that exact command was not run.
- Protected `test_foreign_engine_refusal.py`, `test_refusal_body_shape.py`, `tests/mcp/test_mcp_refusal_mapping.py`, `test_refusal_catalogue.py`, `test_refusal_status_codes.py`: pass unedited. No grant item.

## Deviations from Plan

**1. [Rule 1 - Bug, unprotected test] `tests/seam/test_engine_internals.py`**
- `test_the_missing_items_refusal_is_raised_before_any_envelope_is_constructed` asserted `trace_row_count(tmp_path) == 0`, pinning the pre-D-04 behaviour (no trace on a post-dispatch refusal). It now asserts 1 row and a string `trace_token` on the refusal. The file is not in the plan's `files_modified` and not a ledger test_ref (checked). Commit a8e8fd7.

**2. [Wording] `test_a_malformed_evidence_refusal_carries_a_trace_token` has no fail-first run of its own**
- It was written in Task 2 after Task 1 made the behaviour true, so it passed on first run; the fail-first evidence for the same attribute is Task 1's two tests and the changed `test_engine_internals` assertion.

**3. [Wording] Task 3 `-O` verification**
- See Verification: the protected file cannot be run under `-O` from this environment; its internal `-O` subprocess tests pass.

**Total deviations:** 3. **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. `trace_token` on a refusal is the same opaque reference a successful envelope returns (T-13-21, accepted); node detail stays debug-only.

## Self-Check: PASSED

- a8e8fd7, 6ac9028, 4567a0f are ancestors of HEAD; the four plan source files and the test files exist.
