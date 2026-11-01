---
phase: 16-gui-connectors
plan: 04
subsystem: api
tags: [fastapi, operator-surface, ledger, read-only]
requires: [16-01]
provides:
  - "Ledger.aliases(): the active row of every alias in one SELECT"
  - "Databasise.ledger_aliases() and GET /ledger/aliases"
  - "Databasise.ledger_history(alias, page) and POST /ledger/history"
  - "_OPERATOR_STORE_RESPONSES (502, 503, 409) for store-reading operator routes"
affects: [16-12]
status: complete
commits: 4
plan_head_before: b23f2b8
plan_head_after: aeb108c
actuals:
  tokens: 5000
  tasks: 2
  commits: 4
tech-stack:
  added: []
  patterns:
    - "operator ledger reads open ledger.db with open_existing(read_only=True) inside one executor closure, closed with `with`"
key-files:
  created:
    - databasise/tests/seam/test_console_ledger.py
  modified:
    - databasise/ledger/ledger.py
    - databasise/seam/engine.py
    - databasise/seam/operator_rest.py
key-decisions:
  - "history active = membership in lineage(alias, by_alias.minted_version); tombstoned = membership in tombstone targets_version set"
requirements-completed: [CONN-06, CONN-07]
---

# Phase 16 Plan 04: Ledger aliases and history Summary

`GET /ledger/aliases` lists one row per alias from a new `Ledger.aliases()`, and `POST /ledger/history` pages an alias's rows with `active` and `tombstoned` flags. Both read through `open_existing(read_only=True)`, so a fresh store root stays empty (no `ledger.db`) and no connection stays open.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 (RED) | efb2dc7 | CONN-06 row test, failing (route absent) |
| 1 (GREEN) | cd758a8 | `Ledger.aliases()`, `Databasise.ledger_aliases()`, `_OPERATOR_STORE_RESPONSES`, GET /ledger/aliases |
| 2 (RED) | de8c8c8 | CONN-07 row test, failing (route absent) |
| 2 (GREEN) | aeb108c | `Databasise.ledger_history()`, `LedgerHistoryRequest`, POST /ledger/history |

Tracer gate: Task 1 verify set (7 files, 52 passed) re-run clean before Task 2.

## CONN row test node ids and fail-first evidence

| Row | Intended test_ref | Fail-first |
|-----|-------------------|------------|
| CONN-06 | `databasise/tests/seam/test_console_ledger.py::test_aliases_lists_each_alias_once_and_creates_no_file` | At efb2dc7 (test present, source unchanged): `AssertionError: (404, '{"detail":"Not Found"}')` / `assert 404 == 200`. Use `record-fail --at efb2dc7`. |
| CONN-07 | `databasise/tests/seam/test_console_ledger.py::test_history_flags_active_and_tombstoned_and_bounds_the_page` | At de8c8c8 (CONN-06 code already landed, /ledger/history absent): `AssertionError: (404, ...)` / `assert 404 == 200` at the first `/ledger/history` call, after the promote, rollback and retire setup succeeded. Use `record-fail --at de8c8c8`. |

The test file does not exist at the phase base, so efb2dc7 and de8c8c8 are the earliest commits where each node exists and fails.

## Test results

- Task 1 verify set: 52 passed.
- Task 2 verify set (7 files): 49 passed.
- Phase guard suite from 16-01's block, plus `test_console_ledger.py`, `test_console_wirings.py`, `test_retire_lineage.py`, `test_alias_resolution.py`, `tests/ledger/test_ledger_history.py`, `tests/ledger/test_ledger_lifecycle.py`, `tests/test_docstring_currency.py`: 312 passed.
- No protected test failed; none was edited. `selectors.py` and the FA-06 docstring passages are untouched. `ruff` is clean on the new and edited code; `engine.py` has 5 pre-existing findings outside this plan's lines.
- Full offline gate not run in this plan.

## Deviations from Plan

- Each task was split into a RED test commit and a GREEN code commit so the row nodes have committed failing states for `record-fail --at`. No scope change.
- The plan's commit trailer names Claude Opus 5.5; the shared rules specify the executing model, so commits end with `Co-Authored-By: Claude Sonnet 5.5`.

## Known Stubs

None.

## Threat Flags

None. T-16-08 and T-16-10 are covered by the no-file and fd-count assertions; T-16-09 is accepted per D-10.

## Self-Check: PASSED

Files found: `databasise/tests/seam/test_console_ledger.py`, `databasise/ledger/ledger.py`, `databasise/seam/engine.py`, `databasise/seam/operator_rest.py`. Commits efb2dc7, cd758a8, de8c8c8, aeb108c are ancestors of HEAD.
