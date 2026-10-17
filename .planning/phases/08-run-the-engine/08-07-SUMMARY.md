---
phase: 08-run-the-engine
plan: 07
subsystem: infra
tags: [store-lock, flock, parity, cli, d-03]

requires:
  - phase: 08-run-the-engine
    provides: "08-01 store_lock.py (store_lock, StoreLockedError) and the launcher default store root"
provides:
  - "Six parity CLI main() functions take store_lock(import_index.DEFAULT_STORE_ROOT) and refuse with StoreLockedError (stderr, exit 1)"
  - "test_parity_cli_refuses_while_the_store_root_is_held, six parametrised rows"
affects: [08-08, 10-storage]

actuals:
  tokens: 2400
  tasks: 2
  commits: 4
plan_head_before: d8be9fc7221e106957f996ad135d0788e25b65b9
plan_head_after: 05025db17efb8d440f14bb8034307ddbca737dd4
commits: 4

tech-stack:
  added: []
  patterns:
    - "Lock only in main(); the root is read as import_index.DEFAULT_STORE_ROOT at call time so one monkeypatch covers every CLI"

key-files:
  created:
    - databasise/tests/parity/test_parity_cli_store_lock.py
  modified:
    - databasise/parity/import_index.py
    - databasise/parity/build_hipporag_index.py
    - databasise/parity/run_arm.py
    - databasise/parity/run_comparison.py
    - databasise/parity/run_cross_modality.py
    - databasise/parity/storage_audit.py

key-decisions:
  - "run_arm.main is the sixth locked CLI (RESEARCH Open Question 3): it opens the same default store as the five named in D-03"
  - "eval/corpus_ingest.py, eval/aa_run.py and eval/remint.py are not locked: they use their own v1/.eval_corpus_store root, not the launcher default"
  - "Library functions (run_arm, build_index, run_cross_modality, run_audit, import_v1_index, verify_import) take no lock"

requirements-completed: [RUN-07]

coverage:
  - id: D1
    description: "While a store root is held, each of the six parity mains returns 1 and prints the StoreLockedError message (store root and holder PID) to stderr, before any work function runs"
    requirement: RUN-07
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_parity_cli_store_lock.py#test_parity_cli_refuses_while_the_store_root_is_held (6 rows)"
        status: pass
    human_judgment: false
  - id: D2
    description: "Library functions stay lock-free; existing parity and eval suites unaffected"
    requirement: RUN-07
    verification:
      - kind: unit
        ref: "cd databasise && .venv/bin/pytest -q tests/parity tests/eval (194 passed, 3 deselected)"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-10-16
status: complete
---

# Phase 8 Plan 07: Parity CLI Store Lock Summary

**All six parity entry points (import, HippoRAG build, single arm, comparison, cross-modality, storage audit) now take the cross-process store lock on `v1/.parity_v2_store` and refuse by name, with the holder PID, instead of failing later inside RocksDB.**

## Performance

- **Duration:** 12 min
- **Tasks:** 2
- **Files modified:** 7 (6 source, 1 new test)

## Accomplishments
- Each of the six `main()` functions wraps only its work call in `store_lock(import_index.DEFAULT_STORE_ROOT)`; `StoreLockedError` prints its message to stderr and returns 1.
- One parametrised test holds the lock in-process, replaces every work function with one that raises, and asserts exit 1 with the store root and PID in stderr.
- `import_index.main` sends this refusal to stderr even though its other refusals print to stdout.

## Task Commits

1. **Task 1: import, HippoRAG build, single-arm CLIs** - `31f0681` (test, RED), `fdc1af5` (feat, GREEN)
2. **Task 2: comparison, cross-modality, storage-audit CLIs** - `6dfbeeb` (test, RED), `05025db` (feat, GREEN)

## TDD Notes

- RED (Task 1): three non-xfail rows failed on the planned `AssertionError("work started while the store root was held")` raised from the monkeypatched work function; the other three were strict xfail. Assessment: the target test executed and failed on the intended assertion, not on import or fixture errors.
- RED (Task 2): with the xfail marks removed, the three remaining rows failed on the same assertion.
- GREEN: 6 passed after each task. No REFACTOR commit.

## Decisions Made
- `run_arm.main` is locked as the sixth CLI; `eval/corpus_ingest.py`, `eval/aa_run.py` and `eval/remint.py` are left out because they use `v1/.eval_corpus_store`, not the launcher default root (D-03 scope).
- In `run_comparison.main` and `storage_audit.main` the results-directory writes happen after the locked call returns, outside the lock.

## Deviations from Plan

None - plan executed exactly as written. Task 2 committed the xfail-mark removal as its own `test(08-07)` RED commit before the `feat` commit, which yields four commits instead of two.

## Issues Encountered

None. `ruff check parity` reports 8 pre-existing findings (unsorted imports in `build_hipporag_index.py` and `run_comparison.py`, unused `field` and `TouchRecorder` imports, others in `v1_arm.py`, `v1_driver_script.py`, `run_cross_modality.py`); none were introduced here and they are out of scope.

## Known Stubs

None.

## Threat Flags

None. No new network, auth or file-access surface; the change only adds refusal paths.

## Next Phase Readiness
- 08-08 can rely on every parity entry point honouring the store lock. No blockers.

## Self-Check: PASSED

- `databasise/tests/parity/test_parity_cli_store_lock.py` exists; `grep -c xfail` prints 0.
- Commits `31f0681`, `fdc1af5`, `6dfbeeb`, `05025db` are ancestors of HEAD.
- `pytest tests/parity/test_parity_cli_store_lock.py`: 6 passed. `pytest tests/parity tests/eval`: 194 passed, 3 deselected.
- `grep -n "store_lock(import_index.DEFAULT_STORE_ROOT)"` returns one line per file in run_comparison, run_cross_modality, storage_audit; `store_lock(` appears once in each of import_index, build_hipporag_index, run_arm, each inside `main`.
