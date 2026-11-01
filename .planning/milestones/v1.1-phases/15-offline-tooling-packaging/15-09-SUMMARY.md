---
phase: 15-offline-tooling-packaging
plan: 09
subsystem: parity
tags: [import-index, cli, argparse, verify-import, TOOL-02, TOOL-03]
requires: [15-02]
provides:
  - "parity.import_index main parses argv with argparse before store_lock: --help exits 0, a bad flag exits 2, neither imports, verifies or touches the store root"
  - "--v1-working-dir, --store-root, --workspace pass-throughs resolved at call time; every run prints 'workspace: <ws> (derived from parity corpus snapshot <hash12> | --workspace)'"
  - "MissingV1IndexError and StoreLockedError go through databasise.cli.refuse (one stderr line, exit 1)"
  - "verify_import: v1 graph present and v2 graph absent is a graph-topology violation; a missing v2 store is refused with assertion 'precondition'"
affects: [databasise/parity/import_index.py]
key-files:
  created:
    - databasise/tests/parity/test_import_index_cli.py
  modified:
    - databasise/parity/import_index.py
    - databasise/tests/parity/test_import_verification.py
key-decisions:
  - "Parser defaults are None and resolved inside main from the module attributes, so the parity-store-lock test that patches DEFAULT_STORE_ROOT still works"
  - "A non-verified verification still returns 1 (not the D-03 code 3): the plan did not ask for the change and callers/tests read 1"
  - "The launcher literal DEFAULT_WORKSPACE is kept (M-01 option a); a test pins it equal to _import_workspace()"
requirements-completed: [TOOL-02, TOOL-03]
status: complete
commits: 3
plan_head_before: 029a853e4e782993b85ef7378e1a8f1056a47207
plan_head_after: a73127b653a4fb8b82a72aa2ddd9296bc115881c
actuals:
  tokens: 14000
  tasks: 3
  commits: 3
---

# Phase 15 Plan 09: import_index parses before it locks, verify_import catches a missing graph Summary

`python -m databasise.parity.import_index` now parses its arguments first, passes its paths through, prints the workspace a launcher must use, and `verify_import` can no longer report `verified` with the v2 graph missing.

## What changed

- **Task 1 (10ab2d1, tracer).** `main` builds an `argparse.ArgumentParser` with `--verify` and parses before `store_lock`.
- **Task 2 (2d6f190).** Added `--v1-working-dir`, `--store-root` and `--workspace` (default None, resolved at call time). `import_v1_index` receives the workspace. The workspace line is printed before the work. Refusals use `databasise.cli.refuse`. The module docstring carries the exit table, the pass-through note (the `lightrag/v1-index-sync` node is the sanctioned write path) and the source-checkout requirement.
- **Task 3 (a73127b).** `"precondition"` added to the `Violation.assertion` Literal and used for the missing-store `refused` result. A `graph-topology` violation is appended when `v1_graph is not None and v2_graph is None`.

## Row test node ids and fail-first evidence

Intended ledger `test_ref` for TOOL-02: `databasise/tests/parity/test_import_index_cli.py` (7 nodes). For TOOL-03: `databasise/tests/parity/test_import_verification.py`, nodes `test_tool03_a_missing_v2_graph_is_a_graph_topology_violation` and `test_tool03_an_empty_store_root_is_refused_as_a_precondition`. Fail-first route for both: `record-fail --at 029a853` (the commit before this plan's first code commit 10ab2d1; the phase-base code of `import_index.py` is unchanged since a89f509). `test_import_index_cli.py` imports only names that exist at the base; both files collect and fail by assertion there. The synthetic fixtures in `test_import_verification.py` need no `v1/.venv`; nothing skipped.

Run against the unchanged module (Task 1 nodes) and against the Task-1 module (Task 2 nodes, which only add arguments):
- `test_help_exits_zero_and_touches_nothing`: `AssertionError: --help gave returned 0, expected SystemExit 0` (the import ran).
- `test_a_misspelt_flag_exits_two_and_touches_nothing`: `AssertionError: --verfiy gave returned 0, expected SystemExit 2`.
- `test_paths_pass_through_and_the_workspace_prints`, `test_an_explicit_workspace_is_used_and_labelled`, `test_a_full_run_passes_the_workspace_to_the_importer_too`: `AssertionError: expected a clean return of 0, got ('SystemExit', 2)` (at the phase base the first two fail the same way, as the flags are unknown).
- `test_a_missing_v1_index_is_one_stderr_line`: `AssertionError: expected a return of 1, got ('SystemExit', 2)`.
- `test_the_launcher_workspace_equals_the_derived_workspace`: passes at the base (the M-01 pin).
- `test_tool03_a_missing_v2_graph_is_a_graph_topology_violation`: `AssertionError: verify_import reported verified with the v2 graph missing`.
- `test_tool03_an_empty_store_root_is_refused_as_a_precondition`: `assert ['chunk-text'] == ['precondition']`.

## Test results

- `test_import_index_cli.py`, `test_parity_cli_store_lock.py`, `databasise/tests/launcher` (incl. protected `test_launchers.py`, `test_store_lock.py`): 81 passed.
- `test_import_verification.py`, `test_import_index_cli.py`, protected `test_naive_arm_end_to_end.py`: 37 passed.
- `databasise/tests/parity` plus `databasise/tests/launcher`: 230 passed, 3 deselected.
- No protected test failed. ruff clean on the three files.

## Deviations from Plan

None - plan executed as written. One test node beyond the plan was added (`test_a_full_run_passes_the_workspace_to_the_importer_too`) to pin the workspace reaching `import_v1_index`.

## Known Stubs

None.

## Self-Check: PASSED

Files exist (`databasise/tests/parity/test_import_index_cli.py`, `databasise/parity/import_index.py`); commits 10ab2d1, 2d6f190, a73127b are ancestors of HEAD.
