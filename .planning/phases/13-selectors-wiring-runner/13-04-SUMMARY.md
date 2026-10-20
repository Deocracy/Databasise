---
phase: 13-selectors-wiring-runner
plan: 04
subsystem: runner
tags: [scheduler, node-trace, sequential-dispatch, reason-codes, budget]
requires: ["13-03"]
provides:
  - sequential per-node dispatch in run_wiring (sorted node-id order, one body in flight)
  - exactly one NodeTrace per parsed node with status completed/failed/cancelled/not-scheduled
  - measured wall_clock_ms on failed nodes (NodeExecutionError.wall_clock_ms)
  - stop_reason and degradation_reason limited to the closed REASON_* codes
  - run_wiring result echoes determinism_setting and concurrency_setting
  - runner/budget.py without the apportionment API
affects: [13-08, 13-12]
actuals:
  tokens: 36000
  tasks: 3
  commits: 4
plan_head_before: 43859c347a9794283d9d0af831758000f4c928d0
plan_head_after: 20922efbf599b426af546a17157001ea10452f79
tech-stack:
  added: []
  patterns: ["a node-level failure is returned as data by one dispatch helper, never raised", "consumer-visible reasons are closed codes; node detail stays in the debug trace"]
key-files:
  created:
    - databasise/tests/runner/test_trace_completeness.py
    - databasise/tests/runner/test_runner_surface.py
    - databasise/tests/seam/test_run_record_identity.py
    - databasise/tests/seam/test_stop_reason_leak.py
  modified:
    - databasise/runner/scheduler.py
    - databasise/runner/budget.py
    - databasise/seam/promotion.py
    - databasise/tests/runner/test_budget.py
    - databasise/tests/runner/test_scheduler.py
    - databasise/tests/seam/test_query_store_fault.py
    - databasise/tests/seam/test_mach11_event.py
    - databasise/tests/test_embed_startup.py
key-decisions:
  - "Nodes run one at a time in sorted node-id order; the first failure, cancellation or budget halt stops the run and every unrun node gets a not-scheduled trace"
  - "A failed node's cross_process_failure_cause now names the exception class (NodeExecutionError: <Class>: <redacted message>); the consumer reasons are closed codes"
requirements-completed: [WIRE-10, WIRE-03, WIRE-12, WIRE-18]
status: complete
duration: 2h
completed: 2026-10-19
---

# Phase 13 Plan 04: Runner records every node truthfully Summary

**`run_wiring` now dispatches one node at a time and returns one NodeTrace per parsed node (completed, failed, cancelled, not-scheduled), a failed node reports its measured wall time, nothing a node or post-dispatch step does escapes, and consumer-visible stop reasons are the closed codes `node_failed`, `placement_refused`, `budget_halt`, `cancelled`.**

## Accomplishments

- `runner/scheduler.py`: the per-batch `TaskGroup` is replaced by a sequential loop over `sorted(ts.get_ready())` calling one `_dispatch_node` helper, which returns a `_NodeOutcome` (trace, completed flag, exception, stop code). Placement refusals, body failures, post-dispatch failures (`_body_report`, `meter`, `evaluate_guards`, NodeTrace construction) and a self-raised `CancelledError` (when `current_task().cancelling() == 0`) are all recorded against the node. A real cancellation of the run still propagates. After the loop, every parsed node without a trace gets a `not-scheduled` trace, sorted by node id. `NodeExecutionError` carries `wall_clock_ms` (ceil of elapsed time from the start of dispatch). The result echoes both settings.
- `seam/promotion.py`: `_dispatched_node_ids` counts only completed nodes (absent status reads as completed).
- `runner/budget.py`: `split_allowance`, `apportion`, `ApportionmentPolicy`, `Allowance`, `BudgetHalted` and the `"degraded"` state are deleted; the docstring notes that CONTRACT §9 D4's merge-side apportionment MUST is vacuous while nothing apportions a metered budget. `meter`, `realised_share`, `BudgetToken`, `ctx._semaphore` and per-node `max_concurrency` stay.

## Task Commits

1. Task 1 (tracer): 284e49c - sequential dispatch, one trace per node, measured failure wall time (also renamed `test_scheduler.py::test_8` to the sequential semantics)
2. Task 2: 249ef51 - post-dispatch guard, cancelled trace, closed reason codes, promotion filter, and (see Deviations 1) the settings echo in the run result
3. Task 3: 4c87059 - apportionment API deleted, `test_budget.py` trimmed, WIRE-18 row tests
4. Gate fix: 20922ef - `tests/test_embed_startup.py` fixture kinds (Deviations 3)

## Intended ledger test_refs and fail-first evidence

All fail-first runs were against the source as it stood before the change that fixes them (Task 1 tests vs 43859c3 source; Task 2 tests vs 284e49c; Task 3 tests vs 249ef51). Every failure is a plain `AssertionError`. Phase-base behaviour is the same for these paths: 13-01..13-03/13-05 did not touch dispatch, status stamping or reason construction beyond the NodeTrace fields 13-03 added.

**WIRE-10** - `databasise/tests/runner/test_trace_completeness.py`
- `::test_every_node_gets_one_trace_with_its_status`: `AssertionError: assert ['a-fail', 'z-sibling'] == ['a-fail', 'last', 'mid', 'z-sibling']`
- `::test_a_failed_node_reports_its_measured_wall_time`: `AssertionError: assert 0 >= 50`
- `::test_a_failure_in_the_last_batch_keeps_earlier_nodes_completed`: `{'tail-b': 'completed'} != {'tail-b': 'not-scheduled'}`
- `::test_traces_list_dispatched_nodes_then_not_scheduled_nodes_by_id`: `AssertionError: assert ['a', 'm'] == ['a', 'm', 'b-late', 'd-late', 'zz']`
- `::test_malformed_token_fields_fail_that_node_and_keep_the_siblings`: `AssertionError: TypeError` (`assert TypeError('can only concatenate str (not "int") to str') is None`)
- `::test_an_output_whose_comparison_raises_fails_that_node`: `AssertionError: ValueError`
- `::test_a_body_that_raises_cancelled_error_is_traced_cancelled`: `AssertionError: CancelledError`
- `::test_failure_reasons_are_closed_codes`: `assert ("node 'only'...RuntimeError") == ('node_failed', 'node_failed')`
- `::test_a_partial_run_is_not_matched_by_its_dispatched_set`: `AssertionError: assert frozenset({'b...r', 'legacy'}) == frozenset({'done', 'legacy'})`
- Pass by design before the fix (backstops): `::test_a_one_node_failing_wiring_gives_one_failed_trace`, `::test_a_real_cancellation_of_the_run_still_propagates`

**WIRE-18** - `databasise/tests/runner/test_runner_surface.py`
- `::test_the_unused_apportionment_api_is_deleted[split_allowance]` (and `apportion`, `ApportionmentPolicy`, `Allowance`, `BudgetHalted`): `AssertionError: databasise.runner.budget.split_allowance has no production caller` / `assert not True`
- `::test_budget_state_has_no_degraded_member`: `AssertionError: assert 'degraded' not in ('within_budget', 'halted', 'degraded')`
- `::test_run_wiring_echoes_both_settings`: `AssertionError: assert None == 'cache-bypassed'`
- `::test_the_node_semaphore_has_a_production_user`: passes (openie reads `getattr(ctx, "_semaphore", None)`; the first draft looked only for attribute access and failed with `assert []`, so the scan now also matches the string constant)
- The wiring-string leg is added by 13-12.

**WIRE-03** (ledger test_ref is set in 13-08) - `databasise/tests/seam/test_stop_reason_leak.py`
- `::test_a_naive_query_without_clients_returns_node_free_reasons`: `AssertionError: stop_reason="node 'embedder-query': NodeExecutionError: ClientNotWiredError" carries "node '"`
- `::test_the_non_debug_trace_reasons_are_node_free`: same assertion on the non-debug trace
- `::test_a_hipporag_query_on_a_fresh_root_returns_node_free_reasons`: `AssertionError: stop_reason="node 'fact-score': NodeExecutionError: ClientNotWiredError" carries "node '"`

**WIRE-12** (ledger test_ref is set in 13-12) - `databasise/tests/seam/test_run_record_identity.py`
- `::test_a_sequential_run_never_has_two_node_bodies_in_flight`: `assert 2 == 1` (peak in flight)

Supporting: `tests/seam/test_query_store_fault.py::test_a_non_store_node_failure_degrades_with_the_closed_node_failed_code` (rewritten, unprotected) now expects `"node_failed"` for both reasons and finds the exception class in the debug trace's failed-node cause.

## Verification

- `cd databasise && .venv/bin/python tools/check_offline_suite.py` (both styles): `pytest -q -rs: 2318 passed, 4 deselected`; `python -m pytest -q -rs: 2318 passed, 4 deselected`; exit 0.
- Protected tests pass unedited: `test_capability_scoping_modes.py`, `test_index_side_extraction.py`, `test_token_sum.py`, `test_dpr_fallback_guard.py`, `test_ingest_abort.py`, `test_query_trace_nodes.py`, `tests/foreign/test_secret_redaction.py`.

## Deviations from Plan

**1. [Wording] Settings echo landed in the Task 2 commit**
- `scheduler.py` is shared by Tasks 2 and 3 and non-interactive staging cannot split hunks, so the two-key echo in the return dict (Task 3 step 4) is in 249ef51. The WIRE-18 tests and the budget deletion are in 4c87059; the pre-fix evidence above was taken before the echo existed.

**2. [Rule 1 - Bug, unprotected fixture] `tests/seam/test_mach11_event.py`**
- `test_both_mutator_nodes_are_traced_as_halted_never_silently_dropped` pinned parallel dispatch (both refused mutators traced `halted` in one batch). Under D-17 the first mutator is refused (`failed`, `halted`) and the second is `not-scheduled`. Renamed to `test_both_mutator_nodes_are_traced_never_silently_dropped` and asserts that. Commit 249ef51.

**3. [Rule 3 - Blocking, unprotected fixture] `tests/test_embed_startup.py`**
- Three tests failed at the gate: the fixture wiring declared `kind: "stage"` for parts registered as `passthrough` and `kv-writer`; 13-01's kind-mismatch refusal rejects it. Not caused by this plan's changes (13-01), but the plan requires a green gate. Fixture kinds corrected. Commit 20922ef.

**4. [Rule 2 - Missing critical] `cross_process_failure_cause` names the exception class**
- The plan's `test_query_store_fault` rewrite requires the class name in the debug trace's failed-node cause, but the old cause carried only the redacted message. The cause is now `NodeExecutionError: <Class>: <redacted message>` (still starts with `NodeExecutionError: `, which `test_secret_redaction.py` checks), also for post-dispatch failures.

Other: `test_scheduler.py::test_8` kept its assertions (they hold under sequential order) and was renamed to the new semantics (Task 1).

**Total deviations:** 4. **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. T-13-07 (reason leak) is covered by the three leak tests over REST and the non-debug trace; T-13-08 by the malformed-token, raising-comparison and CancelledError tests; T-13-09 by the peak-in-flight test.

## Notes for later plans

- 13-08 should set the WIRE-03 test_ref to `databasise/tests/seam/test_stop_reason_leak.py` and add the gate legs; 13-12 owns the WIRE-12 test_ref and the identity/trace_token legs, plus the WIRE-18 wiring-string leg.
- A budget halt now stops the run at the halted node (later nodes of the same batch are not-scheduled); before, siblings in the batch had already run in parallel.

## Self-Check: PASSED

Created test files exist; commits 284e49c, 249ef51, 4c87059, 20922ef are ancestors of HEAD.
