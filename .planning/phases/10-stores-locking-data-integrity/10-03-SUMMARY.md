---
phase: 10-stores-locking-data-integrity
plan: 03
subsystem: stores
tags: [namespaces, gc, operator-cli, store-lock, d-16]
status: complete

requires: []
provides:
  - "databasise/launcher/gc_namespaces.py: operator GC CLI, main(argv) -> int, the production caller of gc_namespace (STOR-15, D-16)"
  - "databasise/namespaces.py: NamespaceGCError(namespace, reason); gc_namespace no longer suppresses removal errors"
  - "namespaces.py module docstring describes the actual layout (fixed seam-store names, derive_namespace only in parity/import_index.py)"
affects: [10-12, phase-15]

actuals:
  tokens: 2950
  tasks: 2
  commits: 2
plan_head_before: 78c63706ebc5a9bcacf96b0cdf4a790ec02b32ec
plan_head_after: 03cb337ccc55007c8b1d6f3eeee308f7a363af97

tech-stack:
  added: []
  patterns:
    - "Operator CLI: argparse main(argv) -> int, validate all inputs before any side effect, then act inside `with store_lock(root)`; refusals are one stderr line and exit 1"

key-files:
  created:
    - databasise/launcher/gc_namespaces.py
    - databasise/tests/test_namespaces_gc.py
  modified:
    - databasise/namespaces.py

key-decisions:
  - "gc_namespaces CLI reports a symlinked quarantined-* entry as present (not absent) so gc_namespace raises NamespaceGCError on it instead of the CLI silently skipping it"
  - "No [project.scripts] entry for the GC CLI: it runs as `python -m databasise.launcher.gc_namespaces`, so the protected test_launchers.py script assertions stay unchanged"

requirements-completed: [STOR-15]

duration: 11min
completed: 2026-10-17
---

# Phase 10 Plan 03: Quarantined-namespace GC gets a production caller Summary

`python -m databasise.launcher.gc_namespaces --store-root <root> quarantined-<hex> ...` removes quarantined namespace directories under the per-store-root lock. It accepts only `quarantined-*` tokens and validates every token before it removes anything. `gc_namespace` now raises `NamespaceGCError` for any removal failure other than an absent directory.

## Accomplishments

- New CLI `databasise/launcher/gc_namespaces.py`. It refuses a missing `--store-root` with `parser.error` (exit 2) before taking the lock, because `store_lock` would create the root. It refuses any token without the `quarantined-` prefix or that `namespace_dir` rejects (exit 1, one stderr line naming the token). It then runs `gc_namespace` per token inside `with store_lock(store_root)`, printing `removed <token>` or `absent <token>`. `StoreLockedError` and `NamespaceGCError` each become one stderr line and exit 1.
- `namespaces.py`: `NamespaceGCError(RuntimeError)` with public `namespace` and `reason` fields (`reason` is the cause's exception class name) and the message `NamespaceGCError: could not remove namespace '<token>' (<reason>)`. `gc_namespace` calls `shutil.rmtree(target)` without `ignore_errors`, returns on `FileNotFoundError` and raises `NamespaceGCError ... from exc` for any other `OSError`. A symlinked entry fails this way too, and the symlink target is left untouched.
- The module docstring's D-07 paragraph now says the flat `store_root/<namespace>` layout belongs to derived namespaces only, the seam stores use fixed names under `store_root/<workspace>/<namespace>`, only `parity/import_index.py` calls `derive_namespace`, the artifact registry was removed (D-15), and retirement does not trigger GC. The `gc_namespace` docstring names the CLI as its production caller.
- Confirmed with no edit: `.planning/REQUIREMENTS.md` STOR-15 carries the "Phase 10 D-16 exception" clause (one match).

## TDD / tracer evidence

- Task 1 RED (new tests, no CLI module): `3 failed in 2.67s`, each with `No module named databasise.launcher.gc_namespaces`.
- Task 1 GREEN: `tests/test_namespaces_gc.py tests/stores/test_namespace_derivation.py`: `12 passed in 2.26s`. `python -m databasise.launcher.gc_namespaces --help` exits 0. The tracer gate's automated verify passed on this run, so expansion continued.
- Task 2 RED: the test module failed at collection (`1 error during collection`, `NamespaceGCError` not importable). A probe against the unchanged `gc_namespace` showed the two silent cases: on a namespace with a read-only `sub/file` it returned `None` and the file was still there; on a symlinked `quarantined-<hex>` entry it returned `None` and the symlink was still there.
- Task 2 GREEN: `tests/test_namespaces_gc.py tests/stores tests/test_phase_success_criteria.py`: `81 passed in 13.99s` (this is also the plan-level verification command).
- Full default offline suite after both tasks: `1621 passed, 1 skipped, 4 deselected in 276.94s`.
- `ruff check` on both source files: all checks passed.

## Task Commits

1. Task 1: `108f739` feat(10-03): operator GC CLI removes quarantined namespaces under the store lock
2. Task 2: `03cb337` fix(10-03): gc_namespace reports removal failures as NamespaceGCError

## Deviations from Plan

None. Two small additions inside the plan's scope:
- The refused-token parametrisation also covers `quarantined-../x`, so the `namespace_dir` regex path is tested and not only the prefix rule.
- The CLI treats a symlinked entry as present (`target.exists() or target.is_symlink()`). Without this a dangling symlink would print `absent` and never reach `gc_namespace`.

## Notes

- No protected test file was edited. The tests run the CLI with `cwd=tmp_path`.
- The read-only tests skip under root (`os.geteuid() == 0`) and restore permissions in `finally`.

## Self-Check: PASSED

- FOUND: databasise/launcher/gc_namespaces.py
- FOUND: databasise/tests/test_namespaces_gc.py
- FOUND: 108f739, 03cb337 (ancestors of HEAD)
