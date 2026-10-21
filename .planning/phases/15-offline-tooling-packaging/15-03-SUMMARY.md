---
phase: 15-offline-tooling-packaging
plan: 03
subsystem: parts
tags: [admission, registry, TOOL-16]
requires: ["15-19"]
provides:
  - "admit_registry(registry): §8 conditions 7, 10 and 11 for every opaque part, run when a registry loads"
  - "AdmissionRecordPartMismatchError, InvalidAdmissionFieldError (admission.py) and InvalidPartFieldError (registry.py)"
  - "the shared-scope refusal keys on kind, not structural_depth"
affects: [databasise/parts/admission.py, databasise/parts/registry.py, databasise/seam/engine.py, databasise/tests/parts/test_admission.py, databasise/tests/seam/test_seam_events.py]
key-files:
  modified:
    - databasise/parts/admission.py
    - databasise/parts/registry.py
    - databasise/seam/engine.py
    - databasise/tests/parts/test_admission.py
    - databasise/tests/seam/test_seam_events.py
key-decisions:
  - "ttl_days must be an int (bool refused) in 1..90; the message cites CONTRACT §8 condition 8 (planner assumption A2)"
  - "cross_check_conditions takes resolved_wiring=None to skip condition 7 for a part no wiring provides (v1-index-sync)"
  - "The granted WIRE-13 edit is a single physical line (the keyword added in place) so the diff is 1 line"
requirements-completed: [TOOL-16]
status: complete
duration: 50min
completed: 2026-10-21
commits: 3
plan_head_before: 8fc7a25104a5f410b61d6e9b33761ed03f61ba87
plan_head_after: 3ef4990304372a52ccbec939e005f39b9657d81d
actuals:
  tokens: 9000
  tasks: 3
  commits: 3
---

# Phase 15 Plan 03: Admission enforced when the registry loads Summary

`default_registry()` and `Databasise(registry=...)` now run §8 conditions 7, 10 and 11 for every opaque part with an admission record; a record must name its part, its fields are validated, the shared-scope refusal keys on `kind`, and invalid depth, scope and kind values are refused at registration.

## What changed

- **Task 1 (commit 4f49463, tracer).** `admit_registry` in `parts/admission.py`: wirings are `all_wirings()` plus `load_wiring(family, variant)` for both corpus variants of every family; condition 7 runs once per wiring whose `provides` names a node whose component is the part, and a part no wiring provides gets conditions 10 and 11 only. Condition 10 counts an unset scope on a `writes_artifact` part as shared. `default_registry()` calls it before return; `Databasise.__init__` calls it on the injected-registry branch only. The tracer was re-verified end to end (75 tests in the plan's verify set passed).
- **Task 2 (commit 828a202).** The grant was read first with the Read tool: `check_edit_grants` holds `databasise/tests/seam/test_seam_events.py`, `granted_at` 730. `validate_admission` raises `AdmissionRecordPartMismatchError` first. The only protected-file change is line 156 of `test_seam_events.py`: the keyword `admission=dataclasses.replace(LIGHTRAG_FULL_INGEST_PART.admission, part_name_at_version=_MUTATOR)` added in place (`git show --stat`: 1 insertion, 1 deletion). The test passes with its assertions unchanged.
- **Task 3 (commit 3ef4990).** `InvalidAdmissionFieldError` (ttl_days, blank feed_tier or network_namespace, environment_hash via `fullmatch`); the shared-scope check is `part.kind == "opaque"`; `register` raises `InvalidPartFieldError(ValueError)` for depth, scope and a non-slug `kind`. No evidence string reworded; docstrings keep `keys()` and state no count.

## Row test node ids and fail-first evidence

Intended ledger `test_ref`: `databasise/tests/parts/test_admission.py` (TOOL-16). Fail-first route: `record-fail --at 8fc7a25` (the commit before the first code commit `4f49463`; the test file is collected there, imports only names that exist at the phase base, and resolves new names with `getattr`/`type(caught).__name__`). All nodes below were run against the unchanged source first.

- `test_tool16_1_an_as_of_effect_added_after_registration_is_refused_at_load`: `AssertionError: databasise.parts.admission.admit_registry does not exist`
- `test_admit_registry_skips_condition_7_for_a_part_no_wiring_provides`: same AssertionError (new name absent)
- `test_tool16_2_a_record_for_part_a_attached_to_part_b_is_refused`: `AssertionError: assert 'NoneType' == 'AdmissionRecordPartMismatchError'`
- `test_tool16_3_opaque_kind_with_stage_depth_and_shared_scope_is_refused`: `AssertionError: assert 'NoneType' == 'ForbiddenSharedScopeError'`
- `test_invalid_kind_depth_or_scope_is_refused_at_registration` (5 params): `AssertionError: assert 'NoneType' == 'InvalidPartFieldError'`
- `test_record_fields_are_validated` (8 params): `AssertionError: assert 'NoneType' == 'InvalidAdmissionFieldError'`
- `test_tool16_4_an_unknown_effect_is_refused` (WIRE-16) and `test_tool16_5_default_registry_still_builds`, `test_record_ttl_days_bounds_register`: pass at the base (pin behaviour that must not regress).

WIRE-13 (granted edit): test_ref unchanged, `databasise/tests/seam/test_seam_events.py::test_an_ingest_with_a_mutating_part_returns_one_seam_event`; plant runs belong to the orchestrator.

## Test results

- Task 1 set: 75 passed. Task 2 set: 97 passed. Task 3 set (`tests/parts`, `validator`, `parts_core`, `wirings`, plus protected seam-events, refusal-reachability, advanced-query-members, seam-doc-consistency, docstring-currency): 539 passed.
- Extra: `tests/seam`, `tests/foreign`, `tests/evidence`, `test_phase_success_criteria.py`: 1250 passed. No protected test failed; none was edited beyond the granted line.
- The full offline gate and the wave command were not run (orchestrator's wave run).

## Deviations from Plan

None - plan executed exactly as written. (The ledger base file `.git/gsd-plan-head-before-15-03` was not created; `plan_head_before` is the pre-plan HEAD 8fc7a25 and the count of 3 was measured with `git rev-list --count`.)

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

Commits 4f49463, 828a202, 3ef4990 exist on main; the modified files exist.
