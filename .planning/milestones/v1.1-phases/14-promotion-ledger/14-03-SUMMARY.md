---
phase: 14-promotion-ledger
plan: 03
subsystem: seam
tags: [refusals, rest, mcp, wirings, lookup]
requires: []
provides:
  - PartialRunEvidenceError(*, trace_ids) and GateNotCalibratedError(*, verb) in seam/refusals.py, both 422
  - one _REFUSAL_FACTORIES entry per class in tests/seam/test_rest_transport.py
  - wirings.resolve.wiring_for_name(name) -> dict | None
affects: [14-06, 14-08, 14-10]
status: complete
actuals:
  tokens: 5200
  tasks: 2
  commits: 2
plan_head_before: d9f71c5
plan_head_after: 0fdd44b
tech-stack:
  added: []
  patterns: ["membership check before any file read", "refusal naming only caller-supplied values"]
key-files:
  created:
    - databasise/tests/seam/test_promotion_refusals.py
    - databasise/tests/wirings/test_wiring_for_name.py
  modified:
    - databasise/seam/refusals.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/wirings/resolve.py
key-decisions:
  - "Neither new refusal is added to rest._NOT_FOUND_REFUSALS: 422 is the default"
  - "wiring_for_name returns None on a miss; resolve.py imports nothing from databasise.seam or databasise.ledger"
requirements-completed: []
---

# Phase 14 Plan 03: Shared refusals and name-to-wiring lookup Summary

Two new named refusals (`PartialRunEvidenceError`, `GateNotCalibratedError`) catalogued with REST factories, plus `wiring_for_name`, the single lookup that equals `all_wirings()` filtered by name and returns None otherwise.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 tracer: both refusals, `__all__`, `_REFUSAL_FACTORIES` entries | d827034 | refusal set green (247 passed) |
| 2: `wiring_for_name` and its equivalence test | 0fdd44b | wirings/selectors set green (84 passed) |

## Ledger rows

No row completes in this plan. Both new test files are non-row tests.

## Fail-first evidence (pre-change code, all plain AssertionError)

`test_promotion_refusals.py` (4 failed before the change):
- `test_both_classes_are_catalogued`: `AssertionError: PartialRunEvidenceError is not defined` / `assert None is not None where None = getattr(refusals, 'PartialRunEvidenceError', None)`
- `test_partial_run_evidence_names_only_the_trace_ids`, `test_gate_not_calibrated_names_only_the_verb`, `test_both_map_to_422_with_their_refusal_type`: `AssertionError: <Name> is not defined in databasise.seam.refusals`

`test_wiring_for_name.py` (3 failed before the change), each: `AssertionError: databasise.wirings.resolve.wiring_for_name is not defined`
- `test_every_candidate_resolves_to_its_all_wirings_dict`
- `test_names_outside_the_candidate_pool_return_none`
- `test_a_path_like_or_non_ascii_name_returns_none`

Both files import at module level only names that exist at the phase base and resolve the new names with `getattr`.

## Verification

- Task 1 command (test_promotion_refusals, test_rest_transport, and the protected test_refusal_catalogue, test_refusal_status_codes, test_refusal_body_shape, test_mcp_refusal_mapping, test_seam_doc_consistency, test_refusal_reachability): 247 passed.
- Task 2 command (databasise/tests/wirings, test_selectors, test_selector_reachability, test_measurement_posture): 84 passed.
- `grep -c "^from databasise.seam\|^import databasise.seam" databasise/wirings/resolve.py` prints 0.
- The full offline gate was not run (the plan scopes verification to the sets above).

## Deviations from Plan

None - plan executed exactly as written. Note: `ruff check` reports RUF022 (`__all__` not sorted) on `refusals.py` and `resolve.py`; both lists were already unsorted at the phase base, so it was left alone (out of scope).

## Threat Flags

None.

## Self-Check: PASSED

Files and commits d827034, 0fdd44b exist.
