---
phase: 02-falsifier-gate
plan: 02
subsystem: testing
tags: [ast-scan, dataclasses, ledger, measurement-posture, structural-pin, rig-f3.2]

# Dependency graph
requires:
  - phase: 01-machine-core
    provides: "databasise/runner/trace.py's RunRecord honesty invariant, scheduler.py's degraded/degradation_reason population, ledger/ledger.py's append-only LedgerRecord"
provides:
  - "The recorded MACH-09 default measurement posture (.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md): F3.2's complete disabled and survivor lists, the reason the posture holds without a config switch, and the A1-A4 condition for changing it"
  - "A structural guard test (databasise/tests/runner/test_measurement_posture.py) proven to fail when the unbuilt-promotion-path claim stops being true"
affects: [phase-7-mach-07-promote-rollback, falsifier-gate-verification]

actuals:
  tokens: 3131
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "AST-scan structural pin (mirrors test_trusted_source_invariant.py): findings reported by file:line via a frozen dataclass, never a bare boolean"
    - "Posture-as-artifact: a checkable .planning/ document that cites landed code and tests rather than describing code yet to be written"

key-files:
  created:
    - .planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md
    - databasise/tests/runner/test_measurement_posture.py
  modified: []

key-decisions:
  - "No measurement_posture configuration surface added — a switch with no consumer would record a posture the machine does not actually hold (02-RESEARCH.md Pitfall 4)"
  - "Posture record placed under .planning/ rather than docs/system-model/, since docs/system-model/ is a verbatim upstream mirror per project CLAUDE.md"

patterns-established:
  - "Structural pin doubles as regression protection for a posture decision: a future PR that starts building the promotion path fails the guard test rather than silently invalidating the posture record"

requirements-completed: [MACH-09]

coverage:
  - id: D1
    description: "MACH-09 default measurement posture recorded with complete F3.2 disabled/survivor enumerations, the no-switch rationale, and the A1-A4 change condition"
    requirement: MACH-09
    verification:
      - kind: other
        ref: "grep -q for promote-next/degradation_reason in 02-MACH-09-POSTURE.md (plan's own <verify>)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Structural guard test pinning the unbuilt promotion path: no non-test ledger caller, no promotion verb defined, LedgerRecord.promotion_provenance has no default"
    requirement: MACH-09
    verification:
      - kind: unit
        ref: "databasise/tests/runner/test_measurement_posture.py::test_no_non_test_module_imports_the_ledger"
        status: pass
      - kind: unit
        ref: "databasise/tests/runner/test_measurement_posture.py::test_no_promotion_verb_is_defined_outside_tests"
        status: pass
      - kind: unit
        ref: "databasise/tests/runner/test_measurement_posture.py::test_promotion_provenance_has_no_default"
        status: pass
      - kind: other
        ref: "fail-first probe: injected def promote_now() into databasise/namespaces.py, confirmed test_no_promotion_verb_is_defined_outside_tests fails with a precise file:line finding, reverted (git diff clean)"
        status: pass
    human_judgment: false

duration: 9min
completed: 2026-08-31
status: complete
---

# Phase 2 Plan 2: MACH-09 Default Measurement Posture Summary

**Recorded MACH-09's default-off measurement posture as a checkable artifact and pinned it structurally with an AST-scan guard test proven to fail when the unbuilt promotion path starts to exist.**

## Performance

- **Duration:** 9 min (commit-to-commit; base at 16:30:29, task commits at 16:36:35 and 16:39:03)
- **Started:** 2026-08-31T23:30:29Z
- **Completed:** 2026-08-31T23:39:24Z
- **Tasks:** 2
- **Files modified:** 2 (both newly created)

## Accomplishments
- `.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md` records RIG §F3.2's default posture: measurement-gated promotion off for answer-level and index-side, on for retrieval-side; the complete disabled list (`promote-next`/`promote-now`, all eight §5 gate verdicts at those two tiers, the A/A-null floor, automatic semver minting, the mutation proposer loop, test dimension 11, empirical dimensions 13-15); the complete survivor list (`check`/`preview`/`run`, the full §RUN parallel-run model, §TR trace, manual/operator-asserted promotion, rollback, determinism verification); why it holds today with zero config surface; and the A1-A4 (RIG §CM.3) condition for changing it.
- `databasise/tests/runner/test_measurement_posture.py` pins the structural fact underneath that record with three AST/dataclass-based assertions, mirroring `test_trusted_source_invariant.py`'s scan shape.
- Cited rather than duplicated the already-landed `degraded`/`degradation_reason` labelling (`runner/trace.py`'s `RunRecord.__post_init__`, `runner/scheduler.py`'s population, `test_run_record.py::test_8_...`, `test_live_metering.py::test_metered_node_over_allowance_halts_...`).

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the MACH-09 default measurement posture record** - `4db12bc` (docs)
2. **Task 2: Pin the unbuilt promotion path with a structural guard test** - `3a71e8f` (test)

**Plan metadata:** (this commit, made by the orchestrator after wave merge)

## Files Created/Modified
- `.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md` - the recorded MACH-09 posture: disabled/survivor enumerations, no-switch rationale, degraded-labelling citation, D-04 operating mode, A1-A4 change condition
- `databasise/tests/runner/test_measurement_posture.py` - three-assertion structural guard: no non-test ledger import, no promotion verb defined outside tests, `LedgerRecord.promotion_provenance` has no default/default_factory

## Decisions Made
- No `measurement_posture` configuration surface added (per plan instruction and 02-RESEARCH.md Pitfall 4) — the posture holds structurally, not via a switch nothing reads.
- Posture record placed under `.planning/` rather than `docs/system-model/` (the latter is a verbatim upstream mirror per project CLAUDE.md; this is the project's own layer record).

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` content, `<verify>` commands, and `<acceptance_criteria>` were followed as specified; no auto-fixes, no architectural questions, no scope changes.

## Issues Encountered

None. Fail-first probe (required by Task 2's acceptance criteria) was performed as instructed: temporarily added `def promote_now(): pass` to `databasise/namespaces.py`, confirmed `test_no_promotion_verb_is_defined_outside_tests` fails with a precise `file:line` finding naming `namespaces.py:114`, then reverted the file from a backup copy and confirmed `git diff` shows no residual change. Full suite re-run green (236/236) after the revert.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- MACH-09's posture is now a checkable artifact any later reviewer (or Phase 7's MACH-07 build) can cite directly instead of re-deriving from RIG §F3.2.
- The guard test is a live tripwire: Phase 7 building the promote/rollback protocol will make `test_no_non_test_module_imports_the_ledger` and/or `test_no_promotion_verb_is_defined_outside_tests` fail — that failure is the posture decision surfacing, per the module's own docstring, and the posture record must be updated in the same change rather than the test relaxed.
- No blockers for the remaining Phase 2 plans (02-01, 02-03, 02-04) — this plan touched no production module and has no dependency edge into their work.

---
*Phase: 02-falsifier-gate*
*Completed: 2026-08-31*
