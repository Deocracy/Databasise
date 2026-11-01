---
phase: 14-promotion-ledger
plan: 02
subsystem: ledger
tags: [sqlite, ledger, history, lineage, connection-lifecycle]
requires: []
provides:
  - LedgerEntry read projection (id = generation ordinal, created_at)
  - Ledger.history_for_alias, Ledger.close/__enter__/__exit__, Ledger.open_existing, Ledger.lineage
  - transaction() docstring without the "stall" claim
affects: [14-06, 14-09, phase-16]
status: complete
actuals:
  tokens: 8600
  tasks: 2
  commits: 3
plan_head_before: bb52fbb6517882746b21ad8e11453df24f5b1c6c
plan_head_after: bd3eaf097e7e1ac2203a37ed92fb4a91580fae78
tech-stack:
  added: []
  patterns: ["read-only open returns None instead of creating the file", "lineage walk with visited list"]
key-files:
  created:
    - databasise/tests/ledger/test_ledger_history.py
    - databasise/tests/ledger/test_ledger_store_api.py
  modified:
    - databasise/ledger/ledger.py
key-decisions:
  - "LedgerEntry is a frozen kw_only subclass so LedgerRecord's CONTRACT section 7 field list and the no-default promotion_provenance are untouched"
  - "_row_to_record(row, cls=LedgerRecord) keeps the one-argument call used by tests/seam/test_rollback.py"
requirements-completed: [LEDG-07]
---

# Phase 14 Plan 02: Ledger store reads and lifecycle Summary

Alias-keyed history with generation ordinals and timestamps, deterministic connection closing, a read-only open that never creates `ledger.db`, and a cycle-safe rollback lineage walk, all in `databasise/ledger/ledger.py`.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 tracer: `LedgerEntry`, `history_for_alias`, `cls` on `_row_to_record`, `history` marked test-only | 4c8aed5 | LEDG-07 row test green |
| 2: `close`/`__enter__`/`__exit__`, close on failed construction, `open_existing`, `lineage`, docstring fix | 846602b | store API tests green |
| ruff nits (`Self` return type, unused name) | bd3eaf0 | style only |

## Ledger row (for the orchestrator)

| Row | Intended test_ref | Fail-first evidence on pre-change code |
|-----|-------------------|-----------------------------------------|
| LEDG-07 | `databasise/tests/ledger/test_ledger_history.py::test_history_for_alias_returns_the_alias_rows_oldest_first` | `AssertionError: Ledger.history_for_alias does not exist` / `assert None is not None` (setup through real promote, promote, rollback, retire ran fine; the file collects with no new module-level import). The other two tests in the file fail the same way. |

Other tests in `test_ledger_store_api.py` (non-row), failing before the change by AssertionError:
- `test_lineage_follows_rollbacks_to_their_promotion`: `AssertionError: Ledger.lineage does not exist` / `assert None is not None`
- `test_open_existing_on_a_fresh_root_returns_none_and_creates_nothing`: `AssertionError: Ledger.open_existing does not exist`
- `test_a_ledger_closes_as_a_context_manager`: `AssertionError: Ledger.close does not exist`
- `test_a_failed_constructor_closes_its_connection`: `AssertionError: the failed constructor left its connection open` (`'NoneType' == 'ProgrammingError'`)
- `test_the_transaction_docstring_makes_no_stall_claim`: AssertionError, "stall" present in the docstring
- `test_exit_does_not_swallow_an_exception` failed with `TypeError` (no context manager protocol), not AssertionError; it is a non-row guard.

## Verification

- Task 1 command (ledger tests, test_rollback, test_promote, test_retire, test_measurement_posture): 59 passed.
- Plan verification command (ledger tests plus test_alias_registry, test_rollback, test_retire, test_promote, test_dual_transport, test_measurement_posture, test_health_honesty, test_refusal_status_codes): 142 passed.
- After the ruff commit: `databasise/tests/ledger` 26 passed; test_measurement_posture and test_rollback 12 passed; `ruff check` clean on the touched files.
- `'stall' not in Ledger.transaction.__doc__` exits 0.
- The full offline gate was not run (plan scopes verification to the sets above).

## Deviations from Plan

None in behaviour. One addition: a third commit (ruff `UP`/`RUF059` fixes: `Self` return type on `__enter__`, `_retired` unused name) found by running ruff after Task 2.

## Known Stubs

None.

## Threat Flags

None. T-14-02 and T-14-03 are mitigated as planned (`close`/`__exit__`/close-on-failed-construction; `open_existing` returns None and leaves no `ledger.db`, `-wal` or `-shm`).

## Notes for later plans

- No source caller of `Ledger(...)` was changed (`seam/selectors.py`, `seam/engine.py`); 14-06 and 14-09 adopt `with` and `open_existing`.
- Module docstring paragraphs and the "only caller" sentences of `by_alias`/`generation_state` were left for 14-10.
- `lineage` appends a rollback's `targets_version` even when it is NULL (not reachable through the verbs, which always set it).

## Self-Check: PASSED

Files exist (`ledger.py`, both test files); commits 4c8aed5, 846602b, bd3eaf0 are ancestors of HEAD.
