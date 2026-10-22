---
phase: 16-gui-connectors
plan: 06
subsystem: api
tags: [fastapi, operator-surface, promote, dry-run, read-only]
requires: [16-04]
provides:
  - "Databasise._promotion_prologue and Databasise._plan_promotion: the code /promote and the preview share"
  - "Databasise.preview_promotion and POST /promote/preview"
affects: [16-12]
status: complete
completed: 2026-10-22
commits: 3
plan_head_before: ee14a4c70785b0ca12af564e4d5ff346411f3815
plan_head_after: 825e6fcc4ce96e64281b8c42b42018f0bd83e5e5
actuals:
  tokens: 7000
  tasks: 2
  commits: 3
tech-stack:
  added: []
  patterns:
    - "preview and promote call one prologue and one version plan, so refusal order and minted version cannot drift"
key-files:
  created:
    - databasise/tests/seam/test_console_preview.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/operator_rest.py
key-decisions:
  - "_promotion_prologue extraction kept: no protected promote suite needed the documented fallback"
requirements-completed: [CONN-09]
---

# Phase 16 Plan 06: Promote preview Summary

`POST /promote/preview` returns `{arm, mutation_class, next_version, promotable, reason}` for a promote body and writes nothing. It runs the same `_promotion_prologue` and `_plan_promotion` that `/promote` now calls, over a read-only ledger handle (or none on a fresh root).

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 (RED) | 92be227 | CONN-09 row test, failing (route absent) |
| 1 (GREEN) | bfaf2be | prologue and `_plan_promotion` extracted from `promote`; `preview_promotion`; POST /promote/preview |
| 2 | 825e6fc | differential matrix (16 cases) and the no-row test; both passed on first run, since Task 1 already held the product code |

Tracer gate: the Task 1 verify set (10 files, 84 passed) was clean before Task 2.

## Prologue extraction path

`_promotion_prologue` was kept. The fallback (inline steps in `promote`) was not needed. `promote` keeps its docstring, its refusal order, and `with Ledger(self.store_root) as ledger, ledger.transaction():` as before. The only reorder: the unreachable `verb != "operator-asserted"` backstop now runs after `_plan_promotion` instead of between the class derivation and the mint. It has no side effects and cannot be reached, so the order is not observable.

## CONN row test node id and fail-first evidence

| Row | Intended test_ref | Fail-first |
|-----|-------------------|------------|
| CONN-09 | `databasise/tests/seam/test_console_preview.py::test_preview_matches_what_promote_mints_and_refuses` | At 92be227 (test present, source unchanged): `AssertionError: (404, '{"detail":"Not Found"}')` / `assert 404 == 200` at the first POST /promote/preview. Use `record-fail --at 92be227`. |
| (supporting) | `databasise/tests/seam/test_console_preview.py::test_preview_and_promote_agree_on_every_body[<case>]` (16 cases), `::test_preview_writes_no_ledger_row` | Added after the code in 825e6fc; no committed failing state. |

The test file does not exist at the phase base, so 92be227 is the earliest commit where the CONN-09 node exists and fails.

## Differential matrix (preview, then /promote, each on a fresh root)

| Case | Preview | /promote |
|------|---------|----------|
| complete-naive-trace | 200 promotable, 1.0.0 | 200 1.0.0 |
| complete-hipporag-trace | 200 promotable, 1.0.0 | 200 1.0.0 |
| degraded-complete-trace | 200 promotable, 1.0.0 | 200 1.0.0 |
| partial-trace | 200 reason PartialRunEvidenceError | 422 PartialRunEvidenceError |
| promote-next-no-floor-known-trace | 200 reason GateNotCalibratedError | 422 GateNotCalibratedError |
| promote-next-no-floor-unknown-trace | 200 reason GateNotCalibratedError | 422 GateNotCalibratedError |
| verb-check, verb-preview, verb-run | 200 reason GateVerbNotBuiltError | 422 GateVerbNotBuiltError |
| unrecognised-verb | 422 UnrecognisedPromotionVerbError | 422 UnrecognisedPromotionVerbError |
| empty-alias, hash-shaped-alias | 422 InvalidPromotionAliasError | 422 InvalidPromotionAliasError |
| invalid-change-origin | 422 InvalidChangeOriginError | 422 InvalidChangeOriginError |
| no-trace-ids | 422 EmptyPromotionTraceIdsError | 422 EmptyPromotionTraceIdsError |
| disagreeing-arms (naive + local) | 422 DisagreeingPromotionTraceIdsError | 422 DisagreeingPromotionTraceIdsError |
| unknown-trace | 404 UnknownTraceReferenceError | 404 UnknownTraceReferenceError |

`MeasurementPostureRefusalError` is an outcome refusal in `preview_promotion` but is not in the matrix: it needs a calibrated floor, and no test seeds one.

## Test results

- Task 1 verify set (10 files): 84 passed. Task 2 verify set (`test_console_preview.py`, `test_operator_verb_concurrency.py`, `test_promotion_floor.py`): 31 passed.
- Protected promote suites, all unchanged and green: `test_partial_run_evidence.py`, `test_promote_refuses_partial.py`, `test_operator_alias_validation.py`, `test_promotion_posture.py`, `test_promotion_floor.py`, plus `test_promote_alias_validation.py`, `test_retire_lineage.py`, `tests/ledger/test_ledger_lifecycle.py`, `test_operator_verb_concurrency.py` (82 passed on the extraction alone, before preview existed).
- Phase guard suite from 16-01's block plus the console files, the protected promote suites and `test_docstring_currency.py`: 350 passed.
- `ruff` is clean on `operator_rest.py` and the new test file; `engine.py` keeps its 5 pre-existing findings.
- Full offline gate not run in this plan.

## Deviations from Plan

- The first test commit is a separate RED commit (92be227) and the code lands in bfaf2be, so the row node has a committed failing state for `record-fail --at`. No scope change.
- The plan's commit trailer names Claude Opus 5.5; the shared rules specify the executing model, so commits end with `Co-Authored-By: Claude Sonnet 5.5`.
- Task 2's tests passed on first run (no RED step), because the engine code was finished in Task 1. No product defect surfaced.

## Known Stubs

None.

## Threat Flags

None. T-16-14 is covered by the `ledger.db`-absent and unchanged-row-count assertions; T-16-15 by the differential matrix, with the race documented in the `preview_promotion` docstring; T-16-16 is accepted per D-02.

## Self-Check: PASSED

Files found: `databasise/tests/seam/test_console_preview.py`, `databasise/seam/engine.py`, `databasise/seam/operator_rest.py`. Commits 92be227, bfaf2be, 825e6fc are ancestors of HEAD.
