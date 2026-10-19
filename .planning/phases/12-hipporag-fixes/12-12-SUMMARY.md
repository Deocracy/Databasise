---
phase: 12-hipporag-fixes
plan: 12
subsystem: runner-degradation-reporting
tags: [hipporag, dpr-fallback, degraded, run-record, d-21]
status: complete
requires:
  - phase: 12-hipporag-fixes
    provides: 12-02 and 12-07 (HippoRAG query path with the fact-filter guard and fallback)
provides:
  - scheduler degraded rule: degraded = partial or any NodeTrace.guards_fired
  - STOP_REASON_DECLARED_FALLBACK and DEGRADATION_REASON_FALLBACK_PATH in runner/trace.py
  - RunRecord without the partial == degraded refusal
  - HIPP-14 row test and runner-level pins
affects: [12-14, WIRE-03, WIRE-08]
actuals:
  tokens: 6500
  tasks: 2
  commits: 2
plan_head_before: 96e36742657e5ca4b2c547afb67751dfb457eb8b
plan_head_after: 03c302f88b05707b6eda967f7138693165d673ba
tech-stack:
  added: []
  patterns: ["a completed run on a declared degradation path is degraded without being partial; reasons are closed, node-free codes"]
key-files:
  created:
    - databasise/tests/runner/test_degraded_on_guard.py
  modified:
    - databasise/runner/scheduler.py
    - databasise/runner/trace.py
    - databasise/tests/parts_core/hipporag/test_dpr_fallback_guard.py
key-decisions:
  - "D-21: a fired guard on a completed run reads degraded true, partial false, stop_reason declared_fallback, degradation_reason fallback_path_taken; a partial run keeps its own stop_reason as degradation_reason"
  - "RunRecord keeps the both-reasons-or-neither rule and drops only the partial != degraded refusal (RIG section LC.2 allows partial without degraded)"
requirements-completed: [HIPP-14]
---

# Phase 12 Plan 12: DPR fallback visible as degraded Summary

A HippoRAG query whose fact-filter guard fires now returns a non-debug envelope with `degraded` true, `partial` false and the node-free codes `declared_fallback` / `fallback_path_taken`; the PPR path stays clean.

## Tasks

| Task | Name | Commit |
|------|------|--------|
| 1 | Tracer: a fired DPR fallback is degraded in the non-debug envelope (HIPP-14, D-21) | 5e3821a |
| 2 | Runner-level pins for the degraded rule (D-21) | 03c302f |

Tracer gate: the Task 1 `<verify>` (`tests/parts_core/hipporag/test_dpr_fallback_guard.py tests/runner tests/seam/test_cross_modality_run.py`) passed, 128 passed, before Task 2 began.

## HIPP row, intended ledger test_ref, fail-first evidence

| Row | Intended test_ref | Fail-first evidence |
|-----|-------------------|---------------------|
| HIPP-14 | `databasise/tests/parts_core/hipporag/test_dpr_fallback_guard.py::test_a_fired_fallback_is_degraded_with_a_node_free_reason_and_ppr_is_not` | Run against the unchanged source (HEAD 96e3674, before the trace.py and scheduler.py edits): `assert (fallback.degraded, fallback.partial) == (True, False)` failed with `AssertionError: assert (False, False) == (True, False)  At index 0 diff: False != True`; `1 failed, 12 passed`. After the fix: `128 passed` on the Task 1 verify set. |

For the orchestrator's `record-fail --at <phase base>`: the failure is a plain `AssertionError` at line 278 of the test file (the first assertion). The test imports no Phase-12-only symbol at module level and uses no `pytest.raises`.

## What changed

- `runner/trace.py`: two closed constants; `RunRecord.__post_init__` drops the `partial != degraded` refusal and keeps the both-reasons-when-flagged and no-reason-when-clean rules; the budget-halted-node-must-be-partial rule is unchanged. Module docstring rewritten for the relaxed invariant.
- `runner/scheduler.py`: the final return computes `degraded = partial or any(trace.guards_fired ...)`; a non-partial degraded run gets the two constants; a partial run keeps `degradation_reason = stop_reason`. `evaluate_guards`, `runner/guards.py` and `fact_filter.py` untouched (WIRE-08 owns that).
- `test_dpr_fallback_guard.py`: the old degraded-false pin is replaced by the HIPP-14 row test (fallback run degraded with reasons containing no node id, "guard" or "@"; PPR run all-clean). `test_guard_name_appears_nowhere_in_the_serialised_envelope` still passes.
- `tests/runner/test_degraded_on_guard.py` (new, 7 cases): fired guard gives degraded/not partial/closed codes, unfired guard is clean, `RunRecord` accepts degraded-without-partial and partial-without-degraded, and still refuses a missing reason or a reason on a clean run.

## Verification

- Plan wave command `pytest -q tests/runner tests/seam tests/parts_core tests/parity tests/eval`: 1396 passed, 3 deselected.
- Acceptance greps: `STOP_REASON_DECLARED_FALLBACK = "declared_fallback"` at trace.py:40, `guards_fired` in the scheduler's final computation (scheduler.py:703), row test name present.

## Deviations from Plan

None - plan executed exactly as written.

Note: Task 2's tests passed on first run (they pin the Task 1 behaviour), so no defect in the Task 1 change was exposed.

## Known Stubs

None.

## Threat Flags

None. The reason codes are closed constants with no node id, part name or guard name (T-12-19); a fallback-taken run can no longer read as clean (T-12-20).

## Notes for later plans

- `engine._node_result_or_refuse` still refuses on `partial or stop_reason`; no shipped ingest or delete wiring declares a guard, so a guard-degraded ingest cannot occur yet. 12-14 narrows that check to `partial` as D-21 requires.
- Reason strings are the planner's choice; WIRE-03 (Phase 13) may rename them inside its closed set.

## Self-Check: PASSED

- FOUND: databasise/tests/runner/test_degraded_on_guard.py
- FOUND commits 5e3821a and 03c302f as ancestors of HEAD
