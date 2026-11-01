---
phase: 13-selectors-wiring-runner
plan: 03
subsystem: runner
tags: [run-record, trace-schema, node-trace, execution-mode, budget, derived-schema]
requires: []
provides:
  - databasise/evidence/rig-trace.databasise.schema.json, the frozen trace schema plus declared amendments
  - databasise/evidence/RIG-TRACE-DEVIATIONS.md, one RIG section-R row per amendment
  - NodeTrace status, execution_mode, spent, allowance; nullable cache_hit, tier, feed_tier
  - REASON_CODES and four reason constants in runner/trace.py (the six D-05 codes)
  - databasise_trace_schema fixture; assert_valid_trace on the derived schema
affects: [13-04]
actuals:
  tokens: 14000
  tasks: 3
  commits: 3
plan_head_before: 26cfccdd9bf0d9eb2a94faa1eb538ae82bf5bf8f
plan_head_after: 95f56e43d28eacd5bf0603a1f781f17610f7a4a3
tech-stack:
  added: []
  patterns: ["derived schema = frozen file + RFC 6902 amendment list held by a drift test", "trace field is measured or null, never guessed"]
key-files:
  created:
    - databasise/evidence/rig-trace.databasise.schema.json
    - databasise/evidence/RIG-TRACE-DEVIATIONS.md
    - databasise/tests/runner/test_node_trace_fields.py
    - databasise/tests/evidence/test_derived_trace_schema.py
  modified:
    - databasise/runner/trace.py
    - databasise/runner/scheduler.py
    - databasise/seam/evidence.py
    - databasise/tests/conftest.py
    - databasise/tests/runner/test_run_record.py
key-decisions:
  - "Databasise validates run records against a derived schema; docs/system-model/rig-trace.schema.json and RIG.md stay unedited and a test checks them against git HEAD"
  - "cache_hit is the part's own bool or None; tier and feed_tier default None; no placeholder constant remains"
  - "An overspend is reported in spent/allowance while realised_budget_share stays capped at 1.0"
requirements-completed: [WIRE-11]
coverage:
  - id: D1
    description: "NodeTrace fields report what was measured on the success and refusal paths and validate against the derived schema"
    requirement: WIRE-11
    verification:
      - kind: unit
        ref: "databasise/tests/runner/test_node_trace_fields.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "The derived schema equals the frozen schema plus the declared amendments, each recorded in a section-R row"
    requirement: WIRE-11
    verification:
      - kind: unit
        ref: "databasise/tests/evidence/test_derived_trace_schema.py"
        status: pass
    human_judgment: false
duration: 35min
completed: 2026-10-19
status: complete
---

# Phase 13 Plan 03: Run record reports what was measured Summary

**Run records now validate against a derived Databasise trace schema (frozen schema plus 11 recorded amendments); NodeTrace carries `status`, `execution_mode`, `spent` and `allowance`, and `cache_hit`, `tier` and `feed_tier` are null instead of guessed.**

## Accomplishments

- `rig-trace.databasise.schema.json`: nullable `cache_hit`/`tier`/`feed_tier`; required `status` (completed, failed, cancelled, not-scheduled), `execution_mode`, `spent`, `allowance`; run-level `stop_reason`/`degradation_reason` limited to the six D-05 codes or null; `realised_budget_share` still at most 1. `RIG-TRACE-DEVIATIONS.md` has 11 section-R rows, one per amendment group.
- `runner/trace.py`: `REASON_NODE_FAILED`, `REASON_PLACEMENT_REFUSED`, `REASON_BUDGET_HALT`, `REASON_CANCELLED`, `REASON_CODES`; `TIER_PLACEHOLDER` deleted; docstring rewritten.
- `runner/scheduler.py`: both NodeTrace sites stamp `execution_mode` (success: the hosted placement; failure: the refused placement, else derived from the registered part). Completed nodes carry `spent`/`allowance` from `meter()`; failed nodes carry `status="failed"`, their allowance and `spent=None`. `_body_report` returns the part's `cache_hit` only when it is a `bool`. Stale in-process-only comments and the `validator.depth` paragraph rewritten.
- `conftest.py`: `databasise_trace_schema` fixture; `assert_valid_trace` uses it; `rig_trace_schema` still loads the frozen file.

## Task Commits

1. Task 1 (tracer): 123444d - derived schema, NodeTrace fields, reason codes, conftest flip, execution_mode stamped, `test_run_record.py` fixtures updated
2. Task 2: af96aa5 - spent/allowance/status stamps, `seam/evidence.py` docstring, measured-field tests
3. Task 3: 95f56e4 - deviation record and drift test

## Intended ledger test_refs and fail-first evidence

Pre-fix run: `runner/trace.py` and `runner/scheduler.py` temporarily restored to the plan start (26cfccd), the full new file run, then both files restored from HEAD (working tree clean). 9 of 10 tests fail with plain AssertionErrors; the tenth is the fake-llm-caller guard that passes by design.

**WIRE-11** - `databasise/tests/runner/test_node_trace_fields.py`
- `::test_a_passthrough_node_is_stamped_in_process_and_reports_no_cache_hit`: `AssertionError: assert None == 'in-process'`
- `::test_the_run_record_validates_against_the_derived_schema`: `AssertionError: assert None == 'in-process'` (the record's node has no `execution_mode`; the frozen schema leg is never reached)
- `::test_an_admitted_opaque_node_is_stamped_subprocess`: `AssertionError: assert None == 'subprocess'`
- `::test_a_refused_placement_is_stamped_on_the_failed_trace`: `AssertionError: assert None == 'confined-unit'`
- `::test_a_failed_body_is_stamped_failed_with_its_derived_placement`: `AssertionError: assert None == 'in-process'`
- `::test_an_overspending_node_reports_spent_and_allowance`: `assert None == 1500`
- `::test_spending_exactly_the_allowance_stays_within_budget`: `AssertionError: assert None == 1000`
- `::test_a_zero_allowance_node_with_no_spend_is_within_budget`: `AssertionError: assert None == 0`
- `::test_node_trace_defaults_carry_no_placeholder_tier`: `AssertionError: assert 'T3' is None`
- `::test_fake_llm_caller_still_reports_its_cache_hit`: passes at the plan start by design (guards the part-reported path, first False then True)

The row's fail-first route for the ledger is the phase base b0b5a6c; these runs are against the pre-plan source (26cfccd), where the touched files differ from the base only by 13-01/13-02 changes unrelated to these fields.

**Derived-schema record (D-12)** - `databasise/tests/evidence/test_derived_trace_schema.py` (supporting evidence for WIRE-11, not a separate row)
- Written before the record existed: `::test_every_amendment_has_a_deviation_row` and `::test_the_deviation_record_uses_the_rig_section_r_columns` failed with `AssertionError: the deviation record could not be read: FileNotFoundError`. `::test_the_derived_schema_is_the_frozen_schema_plus_the_declared_amendments` and `::test_the_frozen_files_are_unedited` passed (the derived file already existed from Task 1; the frozen files are untouched).

## Deviations from Plan

**1. [Rule 2 - Missing critical] Extra row tests**
- `test_a_failed_body_is_stamped_failed_with_its_derived_placement` (a raising body, not only a refused placement, gets `status="failed"` and its derived placement) and `test_a_zero_allowance_node_with_no_spend_is_within_budget` (the plan lists the zero-allowance edge as backstop-verified; a test was cheap and pins the 0/0 convention). Commit af96aa5.

**2. [Wording] `_body_report` and the failure-site `cache_hit=None` landed in Task 1**
- The Task 1 tracer test requires `cache_hit is None` for passthrough, so the `_body_report` change and the failure-site `cache_hit=None` were committed in 123444d rather than Task 2. `spent`, `allowance` and `status="failed"` landed in Task 2 as planned.

**Total deviations:** 2. **Impact:** none on scope.

## Follow-up for 13-04

The scheduler's run-level `stop_reason` for a failed or refused node is still the free-text string it built before this plan (`node 'n1': ...`). The derived schema now restricts `stop_reason` and `degradation_reason` to the six codes, so a real failed-node record would fail `assert_valid_trace` until 13-04 switches the dispatch loop to `REASON_NODE_FAILED` / `REASON_PLACEMENT_REFUSED`. No test in the suite validates such a record today (budget-halt and clean runs already use closed codes); `tests/runner/test_run_record.py` hand-built records were moved to codes. The `status` values `cancelled` and `not-scheduled` are in the schema but nothing stamps them yet (WIRE-10, 13-04).

## Verification

`cd databasise && .venv/bin/pytest -q tests/seam tests/runner tests/validator tests/wirings tests/identity tests/parts tests/parts_core tests/evidence tests/parity`: 1663 passed, 3 deselected. `git diff --stat HEAD -- docs/system-model` is empty. Protected parity test `test_naive_arm_end_to_end.py` passes unedited against the derived-schema fixture.

## Known Stubs

None.

## Threat Flags

None. T-13-05 is mitigated (drift test plus frozen-file git check); T-13-06 holds (`nodes` stay out of the non-debug trace fields).

## Self-Check: PASSED

Created files exist (schema, deviation record, both test files); commits 123444d, af96aa5, 95f56e4 are ancestors of HEAD.
