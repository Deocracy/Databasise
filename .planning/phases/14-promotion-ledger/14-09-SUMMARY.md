---
phase: 14-promotion-ledger
plan: 09
subsystem: seam
tags: [retire, rollback, lineage, tombstone, ledger-lifecycle, connections, row-tests]
requires: ["14-02", "14-08"]
provides:
  - databasise/seam/engine.py lineage guards in the retire and rollback closures
  - databasise/seam/engine.py with/open_existing in all three verb closures
  - databasise/tests/seam/test_retire_lineage.py (LEDG-04 row test)
  - databasise/tests/ledger/test_ledger_lifecycle.py (LEDG-06 row test)
affects: [14-10, phase-16]
status: complete
actuals:
  tokens: 6300
  tasks: 2
  commits: 2
plan_head_before: dbf7f884089af21710ce6cf2a305d024a24302b8
plan_head_after: 5ad711ef996ef67c3094c3d9c7df7a49f2e7aa93
tech-stack:
  added: []
  patterns: ["guards by version through Ledger.lineage, never by wiring identity", "read-only open for verbs that may run on a fresh root", "with Ledger(...) as ledger, ledger.transaction() on the executor thread"]
key-files:
  created:
    - databasise/tests/seam/test_retire_lineage.py
    - databasise/tests/ledger/test_ledger_lifecycle.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/refusals.py
    - databasise/tests/seam/test_operator_verb_concurrency.py
key-decisions:
  - "retire refuses when the version is anywhere in ledger.lineage(alias, active.minted_version); rollback refuses TombstonedGenerationError naming the requested version when any version in ledger.lineage(alias, version) has a tombstone as its generation_state"
  - "rollback and retire open the ledger with Ledger.open_existing; None refuses as UnknownGenerationVersionError and creates no file"
  - "the retire-vs-rollback race test accepts TombstonedGenerationError or ActiveGenerationRetirementError and asserts the alias never ends active on a tombstoned lineage version"
requirements-completed: [LEDG-04, LEDG-06]
---

# Phase 14 Plan 09: Lineage guards and ledger connection lifecycle Summary

Retire and rollback now guard generations by rollback lineage, so an alias never serves a tombstoned generation, and all three operator verbs close their ledger connection on the executor thread, with rollback and retire opening it read-only so a refused verb on a fresh root creates no file.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 tracer: lineage guards in `retire` and `rollback`, docstrings, race-test update | dbf2de9 | 107 passed (retire, rollback, dual transport, status codes, catalogue, doc consistency) plus the concurrency file alone: 2 passed |
| 2: `with`/`open_existing` in the three closures | 5ad711e | 156 passed (plan verify set) |

## Ledger rows

| Row | Intended test_ref (node ids) |
|-----|------------------------------|
| LEDG-04 | `databasise/tests/seam/test_retire_lineage.py` (nodes: `::test_retiring_the_target_of_an_active_rollback_is_refused`, `::test_every_version_in_the_active_lineage_is_protected`, `::test_a_rollback_onto_a_tombstoned_lineage_is_refused`, `::test_a_repromoted_arm_keeps_its_older_generation_retirable`, `::test_rest_retire_of_an_active_rollback_target_is_a_422`) |
| LEDG-06 | `databasise/tests/ledger/test_ledger_lifecycle.py` (nodes: `::test_no_ledger_connection_is_left_open`, `::test_refused_verbs_on_a_fresh_root_create_no_ledger_file`, `::test_the_transaction_docstring_makes_no_stall_claim`) |

## Fail-first evidence

Two runs: in the main tree against the unchanged source before each fix, and in a scratch worktree at the phase base bb52fbb with only the two row files copied in from 5ad711e (`PYTHONPATH=<wt> databasise/.venv/bin/python -P -m pytest ... --rootdir=<wt>`). Both files collect at the base. 8 failed, 1 passed, 0 errors; every failure is an `AssertionError` (the pass is `test_a_repromoted_arm_keeps_its_older_generation_retirable`, which asserts behaviour true at the base: a guard by identity would break it). The worktree was removed.

LEDG-04 (the same four failures in the main tree before the fix and at the base):
- `test_retiring_the_target_of_an_active_rollback_is_refused`: `AssertionError: retire of the rollback's target gave PromotionResult: alias='lineage-alias' version='1.0.0' record_kind='tombstone' provenance='operator_asserted' generation_ordinal=4`
- `test_every_version_in_the_active_lineage_is_protected`: `AssertionError: retire of lineage version 1.0.0 gave PromotionResult: ... record_kind='tombstone' ... generation_ordinal=6`
- `test_a_rollback_onto_a_tombstoned_lineage_is_refused`: `AssertionError: rollback onto a tombstoned lineage gave PromotionResult: alias='lineage-alias' version='5.0.0' record_kind='rollback' ... generation_ordinal=6`
- `test_rest_retire_of_an_active_rollback_target_is_a_422`: `AssertionError: 200 {"alias":"lineage-alias","version":"1.0.0","record_kind":"tombstone",...,"generation_ordinal":4}`

LEDG-06:
- `test_no_ledger_connection_is_left_open`: at the base `AssertionError: 23 of 23 ledger.db connections were left open` (the alias read still leaked there); in the main tree before Task 2 (14-06 had closed the alias read) `AssertionError: 3 of 23 ledger.db connections were left open` (the promote, rollback and retire connections).
- `test_refused_verbs_on_a_fresh_root_create_no_ledger_file`: main tree before Task 2: `AssertionError: refused verbs left ['ledger.db', 'ledger.db-wal', 'ledger.db-shm'] on a fresh root`. At the base it fails earlier, on the gate leg: `AssertionError: promote-next gave MeasurementPostureRefusalError: ... mutation class 'index-side' ...`.
- `test_the_transaction_docstring_makes_no_stall_claim`: at the base `AssertionError: assert 'stall' not in 'G-07-1: wid...'` (fixed by 14-02; passes in the main tree).

## Verification

- Task 1 verify set (minus the concurrency file): 107 passed (15 s).
- `test_operator_verb_concurrency.py` run on its own, three times (after Task 1 and twice after Task 2): 2 passed each (17-19 s). It did not flake.
- Task 2 verify set: 156 passed (39 s). Includes the protected `test_refusal_status_codes.py`, `test_health_honesty.py`, `test_promote_alias_validation.py`.
- Wave command `pytest databasise/tests/seam databasise/tests/ledger databasise/tests/mcp` with `test_operator_verb_concurrency.py` ignored (run separately as above): 1214 passed in 450 s. 14-07 had not run; no 14-07 or 14-11 file was touched.
- Acceptance greps: `lineage(alias, active.minted_version)` one line; `lineage(alias, version)` one line; `open_existing(self.store_root)` count 2.
- The full offline gate was not run (the plan scopes verification to the sets above).

## Deviations from Plan

**1. [Scope] Docstring and race-test additions.** The `ActiveGenerationRetirementError` and `TombstonedGenerationError` docstrings in `refusals.py` and the `rollback`/`retire` docstrings in `engine.py` describe the lineage rule as the plan asks. In the race test the new "alias never ends active on a tombstoned generation" assertion walks `ledger.lineage(...)` and checks `generation_state` of each version.

**2. [Wording] LEDG-06(a) record counts.** The wrapper records `>= 23` `ledger.db` connections (20 alias reads, promote, rollback, retire); the observed count is exactly 23.

**3. [Lint] Pre-existing ruff findings left.** `ruff check` on the touched files reports eight findings; the engine.py and refusals.py ones (I001, two RUF100, ASYNC230, RUF022) exist at the previous commit, and the three in `test_retire_lineage.py` (import order, the two `E402` noqa markers) copy the style of `test_operator_alias_validation.py`. Not changed.

Otherwise the plan was executed as written. `test_operator_verb_concurrency.py` is not a ledger `test_ref` file (14-CONTEXT: "Unprotected follow-up"), so editing it needed no grant.

## Known Stubs

None.

## Threat Flags

None. T-14-20 (lineage guards in both closures inside one `BEGIN IMMEDIATE` span; row sequence, deep chain, rollback-side hole and the race are covered), T-14-21 (`with` in all three closures; 23 connections counted closed) and T-14-22 (`open_existing`; the three files checked on a fresh root) are mitigated and asserted.

## Self-Check: PASSED

- databasise/tests/seam/test_retire_lineage.py, databasise/tests/ledger/test_ledger_lifecycle.py: FOUND
- dbf2de9, 5ad711e: FOUND on main
