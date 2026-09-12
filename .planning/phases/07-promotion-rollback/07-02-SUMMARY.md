---
phase: 07-promotion-rollback
plan: 02
subsystem: database
tags: [sqlite, promotion-ledger, seam, semver, tombstone]

# Dependency graph
requires:
  - phase: 07-promotion-rollback (07-01)
    provides: "Databasise.promote(), the four additive ledger columns, Ledger.generation_state(), promotion.py's mint_version/derive_mutation_class, and the six-refusal SeamRefusalError ladder this plan builds on directly"
provides:
  - "Databasise.rollback(alias, version, trace_ids, change_origin) — an explicitly named semver target, no default 'previous' (D-05)"
  - "Databasise.retire(alias, version, trace_ids, change_origin) — a tombstone on the same append-only path, with the active-generation and already-tombstoned guards (D-07)"
  - "Databasise._resolve_operator_preconditions — the one shared place promote()/rollback()/retire()'s operator-path preconditions live"
  - "Three new SeamRefusalError subclasses: UnknownGenerationVersionError, TombstonedGenerationError, ActiveGenerationRetirementError"
affects: [07-03-rest-mcp-surface]

# Actuals (#2632)
actuals:
  tokens: 12654
  tasks: 2
  commits: 3
plan_head_before: 097d3758087714e6d25821e3bd3a28a631858dba

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Shared operator-path precondition helper (_resolve_operator_preconditions) extracted from promote()'s own former prologue, so three verbs' validation lives in exactly one place rather than three near-identical copies"
    - "Ledger.generation_state(alias, version) read (latest-record-for-a-generation, ORDER BY id DESC LIMIT 1) reused identically by rollback() and retire() for both the unknown-version and tombstone checks — never a full history() scan"

key-files:
  created:
    - databasise/tests/seam/test_rollback.py
    - databasise/tests/seam/test_retire.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/refusals.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/runner/test_measurement_posture.py
    - .planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md

key-decisions:
  - "_resolve_operator_preconditions returns (resolved_records, arm_name, arm_instance_hashes) as a plain method on Databasise (not a promotion.py function) — the shared prologue needs self._trace_store, and the plan left the choice to Claude's discretion ('one shared private helper on Databasise, or one function in promotion.py')."
  - "rollback()'s mutation_class is derived from (target generation's wiring, current active generation's wiring) — the same two-wiring-diff pattern promote() uses, read as 'new vs. prior' even though nothing is newly running; retire()'s mutation_class uses the identical pattern with (retirement target, still-active generation), since the plan's own text only said 'derived the same way' without naming the two operands explicitly."
  - "MACH-09 posture guard's _PROMOTION_VERB_NAMES already listed 'rollback' from Phase 2, before this codebase's real rollback() was settled as an operator-asserted path (never a CONTRACT §5 ladder member) — widened the guard's exempt-detail set to also cover 'def rollback(...)' on the same already-named seam/engine.py file, mirroring promote()'s own exemption exactly; retire needed no exemption since it was never in that scanned vocabulary."
  - "No __init__.py export was added for rollback/retire — PromotionResult (their shared return type) was already exported by 07-01, and neither promote nor rollback/retire are bare module-level functions (they are Databasise methods), so there is no new top-level symbol to export."

requirements-completed: [MACH-07]

coverage:
  - id: D1
    description: "Databasise.rollback() repoints an alias to an explicitly named semver generation by one new append; an unknown, foreign-alias, or tombstoned target refuses by name with nothing written"
    requirement: "MACH-07"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_rollback.py#test_rollback_repoints_the_alias_to_the_named_generation"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_rollback.py#test_rollback_appends_rather_than_rewinds"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_rollback.py#test_unknown_version_refuses_by_name"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_rollback.py#test_version_minted_under_a_different_alias_refuses"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_rollback.py#test_rollback_has_no_default_previous"
        status: pass
    human_judgment: false
  - id: D2
    description: "A rollback mints a genuinely new semver (never reuses the target's), carries no verdict/tier-of-decision, and shares promote()'s trace/change_origin refusal vocabulary"
    requirement: "MACH-07"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_rollback.py#test_rollback_mints_a_new_version_never_reuses_the_target"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_rollback.py#test_rollback_carries_no_verdict"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_rollback.py#test_rollback_shares_promotes_trace_and_change_origin_refusals"
        status: pass
    human_judgment: false
  - id: D3
    description: "Databasise.retire() appends a tombstone record (mints no version) for a named generation; retiring an already-tombstoned or the alias's own currently-active generation refuses by name"
    requirement: "MACH-07"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_retire.py#test_retire_appends_a_tombstone_record"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_retire.py#test_retire_mints_no_version"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_retire.py#test_retiring_the_active_generation_refuses"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_retire.py#test_rollback_to_a_retired_generation_refuses"
        status: pass
    human_judgment: false
  - id: D4
    description: "No act lifts a tombstone: re-promoting a retired wiring mints a new generation while the retired generation's own state stays a tombstone forever, and the alias never derives from a retirement record — proven against the real write path, not a hand-seeded row (SC1)"
    requirement: "MACH-07"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_retire.py#test_never_lifted_repromotion_is_a_new_generation"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_retire.py#test_alias_never_derives_from_a_retirement_record"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_retire.py#test_the_ledger_still_refuses_update_and_delete_for_tombstones"
        status: pass
    human_judgment: false

duration: ~50min
completed: 2026-09-12
status: complete
---

# Phase 7 Plan 2: rollback() and retire() — Reading the Ledger Back Before Writing to It Summary

**`Databasise.rollback(alias, version, trace_ids, change_origin)` and `Databasise.retire(alias, version, trace_ids, change_origin)` — the two operator verbs that read `Ledger.generation_state()` before appending, making SC1's "tombstoned losers are never lifted" true against the real write path.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-09-12
- **Tasks:** 2 of 2
- **Files modified:** 7 (2 created, 5 modified)

## Accomplishments

- `Databasise.rollback()` — a required, no-default `version` parameter (D-05: no silent
  "previous"); resolves the target generation through `Ledger.generation_state(alias, version)`,
  refusing an unknown-or-foreign-alias version (`UnknownGenerationVersionError`, one refusal
  covering both facts since both mean "this alias has no such generation") or a tombstoned target
  (`TombstonedGenerationError`); appends one new `operator_asserted` record whose
  `mutation_id`/`parent` both name the target's own `mutation_id`, minting a genuinely new semver
  via the same `mint_version`/`derive_mutation_class` rule `promote()` already uses.
- `Databasise.retire()` — appends a tombstone record (`minted_version=None`,
  `targets_version=<the retired version>`); refuses an already-tombstoned target and refuses
  retiring the alias's own currently-active generation (`ActiveGenerationRetirementError`, stating
  the operator must roll back first). The resolved trace arm is recorded but deliberately not
  matched against the retirement target (RESEARCH.md Open Question 2) — stated in the method's own
  docstring.
- `Databasise._resolve_operator_preconditions` — `promote()`'s former validation prologue
  (invalid `change_origin`, trace resolution, `resolve_single_arm` agreement check) extracted into
  one shared helper all three verbs now call, so the operator-path preconditions live in exactly
  one place.
- `test_never_lifted_repromotion_is_a_new_generation` is the load-bearing new test: promote/
  promote/retire/re-promote against the real write path proves a retired generation stays
  tombstoned forever while the re-promotion mints a genuinely new generation — SC1's rule, real for
  the first time rather than only against a hand-seeded ledger row.
- Three new `SeamRefusalError` subclasses (`UnknownGenerationVersionError`,
  `TombstonedGenerationError`, `ActiveGenerationRetirementError`), each naming only the caller's
  own `alias`/`version` per this module's no-enumeration house style.

## Task Commits

1. **Tasks 1-2 (production code): rollback(), retire(), shared precondition helper, three
   refusals** — `94e36b5` (feat)
2. **Tasks 1-2 (test coverage): 18 behavior tests across test_rollback.py/test_retire.py** —
   `9d2df53` (test)
3. **Rule 1/3 fix: REST refusal-factory growth-invariant entries + MACH-09 posture guard update
   for rollback** — `ab4f88c` (fix)

_Note: as in 07-01, production code and tests for both tasks were implemented and verified
together as one interdependent unit rather than per-task RED/GREEN commits — see "TDD Gate
Compliance" below — and committed in two passes (feat, then test) plus one required fix commit,
mirroring 07-01's own established shape for this phase._

## Files Created/Modified

- `databasise/seam/engine.py` - `Databasise.rollback()`, `Databasise.retire()`,
  `_resolve_operator_preconditions` shared helper
- `databasise/seam/refusals.py` - `UnknownGenerationVersionError`, `TombstonedGenerationError`,
  `ActiveGenerationRetirementError`
- `databasise/tests/seam/test_rollback.py` - Task 1 behavior coverage (9 tests)
- `databasise/tests/seam/test_retire.py` - Task 2 behavior coverage (9 tests)
- `databasise/tests/seam/test_rest_transport.py` - refusal-factory entries for the three new
  refusal types
- `databasise/tests/runner/test_measurement_posture.py`,
  `.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md` - MACH-09 guard's promotion-verb
  exemption widened to also cover `rollback`, with the reasoning recorded in a new dated section

## Decisions Made

See `key-decisions` in frontmatter. In short: the shared precondition helper landed as a
`Databasise` method (needs `self._trace_store`) rather than a `promotion.py` function, per the
plan's own stated discretion; `rollback()`/`retire()`'s `mutation_class` derivation reuses
`derive_mutation_class`'s existing two-wiring-diff signature, reading "new" as the generation in
play (rolled-back-to, or being retired) and "prior" as the alias's still-current active generation;
and no `__init__.py` change was needed since `PromotionResult` (the shared return type) was already
exported by 07-01 and neither verb is a bare module-level function.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `test_rest_transport.py`'s refusal-factory growth-invariant test had no
entry for the three new refusal subclasses**
- **Found during:** running the full test suite after landing `rollback()`/`retire()`
- **Issue:** `test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value`
  walks `SeamRefusalError.__subclasses__()` transitively and requires a test-factory entry per
  subclass; `ActiveGenerationRetirementError` (and, transitively, the other two new subclasses)
  failed this pre-existing check.
- **Fix:** Added a factory-callable entry for each of the three new refusal types to
  `_REFUSAL_FACTORIES`.
- **Files modified:** `databasise/tests/seam/test_rest_transport.py`
- **Verification:** `uv run pytest -q tests/seam/test_rest_transport.py` passes.
- **Committed in:** `ab4f88c`

**2. [Rule 1/3 - Bug/Blocking] The MACH-09 measurement-posture guard failed exactly as its own
docstring anticipated**
- **Found during:** running the full test suite after landing `rollback()`
- **Issue:** `tests/runner/test_measurement_posture.py::test_no_promotion_verb_is_defined_outside_tests`
  scans for a real function/method named `promote`/`promote_next`/`promote_now`/`rollback` outside
  the test suite, exempting only `def promote(...)` on `seam/engine.py`. `_PROMOTION_VERB_NAMES`
  already listed `"rollback"` — a Phase 2 guess at what CONTRACT §5's own gate-adjudicated ladder
  rollback mechanism might be named, before Phase 7 settled that this codebase's real `rollback()`
  is instead RIG §PR.2's operator-asserted path, never a member of that ladder — so landing the
  real `rollback()` tripped this guard, per the guard's own stated purpose ("Update
  02-MACH-09-POSTURE.md in the same change rather than relaxing this test").
- **Fix:** Widened `_PROMOTION_VERB_EXEMPT_FILES`'s matching detail set from `{"def
  promote(...)"}` to `{"def promote(...)", "def rollback(...)"}` for the one already-named exempt
  file (`seam/engine.py`); `retire` needed no exemption since it was never in
  `_PROMOTION_VERB_NAMES`'s scanned vocabulary in the first place. Updated the test's own module
  docstring (item 2) and added a new "07-02-PLAN.md: rollback/retire — the same operator-asserted
  exception, extended" section to `02-MACH-09-POSTURE.md`, following the 07-01 section's own
  precedent, recording why this does not mean the gate-adjudicated ladder has started to exist.
- **Files modified:** `databasise/tests/runner/test_measurement_posture.py`,
  `.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md`
- **Verification:** `uv run pytest -q tests/runner/test_measurement_posture.py` passes (3/3).
- **Committed in:** `ab4f88c`

---

**Total deviations:** 2 auto-fixed (1 bug/blocking growth-invariant guard, 1 blocking test-factory
gap)
**Impact on plan:** Both were required for the plan's own `<verification>` block ("`uv run
pytest -q` is green at or above the count 07-01 recorded") to hold. No scope creep — no feature was
added beyond what the plan's two tasks specify; both fixes are the same class of pre-existing
growth-invariant guard 07-01 itself already hit and documented for `promote()`.

## TDD Gate Compliance

Both of this plan's tasks carry `tdd="true"`. `workflow.tdd_mode` is not set in
`.planning/config.json`, so the RED/GREEN/REFACTOR gate is advisory, not enforced — the identical
posture 07-01-SUMMARY.md recorded for this same phase. Both tasks' production code
(`rollback()`/`retire()`, the shared precondition helper, three refusals) was implemented as one
interdependent unit rather than incrementally per task, because `retire()`'s active-generation
guard and tombstone check reuse the identical `generation_state`/`mint_version`/
`derive_mutation_class` machinery `rollback()` exercises first — the two are not independently
correct in isolation any more than 07-01's own promote-path pieces were. Every task's own
`<behavior>`-block test is present, named exactly as specified in the plan, and passing (verified
individually via each task's own `<verify>` command before committing: `test_rollback.py` alone,
then `test_retire.py` alone, then the plan-level `tests/seam tests/ledger` and full-suite
verification). No `test(...)` commit strictly precedes every corresponding `feat(...)` commit per
task; instead, one `feat` commit (`94e36b5`) landed both tasks' production code and one `test`
commit (`9d2df53`) landed both tasks' test files — verified together before either commit was
made, exactly as 07-01 did and documented for this same phase.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All three ledger-writing seam methods (`promote`, `rollback`, `retire`) now exist and are
  fully tested against the real write path — 07-03's REST/MCP transports can route to all three
  unchanged, following `ingest`/`delete_document`'s existing thin-adapter shape.
- `PromotionResult` already covers all three verbs' response shape (`record_kind` disambiguates
  `"promotion"`/`"rollback"`/`"tombstone"`); no new response model is needed for 07-03.
- MACH-07 is now fully discharged by this plan's own success criteria (SC1's tombstone-never-lifted
  rule, rollback's explicit-target rule); API-09 remains 07-03's to complete for the REST/MCP
  transport parity half. Per the shared-ID gate (#2388), MACH-07 was marked complete via
  `requirements.mark-complete` below since no sibling plan in this phase also declares it;
  API-09 stays Pending until 07-03's own SUMMARY lands.
- Full suite: 1027 passed, 1 skipped (baseline was 1006 passed/1 skipped at 07-01) — 18 new
  behavior tests plus 3 new parametrized refusal-factory cases, no regressions.

---

*Phase: 07-promotion-rollback*
*Completed: 2026-09-12*

## Self-Check: PASSED

All key files confirmed present on disk (`databasise/tests/seam/test_rollback.py`,
`databasise/tests/seam/test_retire.py`, this SUMMARY). All three commit hashes (`94e36b5`,
`9d2df53`, `ab4f88c`) confirmed present in `git log`. Re-ran the plan's own `<verify>` blocks
(`test_rollback.py -x`: 9 passed; `test_retire.py -x`: 9 passed; `test_retire.py -k never_lifted -x`:
1 passed; `tests/seam tests/ledger -x`: 267 passed/1 skipped) and the plan-level `<verification>`
block (full `uv run pytest -q`: 1027 passed, 1 skipped — at or above 07-01's recorded 1006/1
baseline) — all pass. Grep-verified acceptance criteria: `rollback`'s signature is exactly
`(self, alias, version, trace_ids, change_origin)` with no default on `version`; both new refusal
classes are `SeamRefusalError` subclasses in `refusals.py`'s `__all__`; `rollback`/`retire` each
contain exactly one `ledger.append(` call; `retire`'s docstring names "RESEARCH.md Open Question 2"
and states the resolved arm is recorded, not matched; `engine.py` has exactly three
`ledger.append(` call sites total (promote/rollback/retire); `Ledger` issues no `UPDATE`/`DELETE`
statement.
