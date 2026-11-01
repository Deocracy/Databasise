---
phase: 15-offline-tooling-packaging
plan: 06
subsystem: composer
tags: [run_wiring, canonicalise, finalize, TOOL-10]
requires: []
provides:
  - "databasise.run_wiring canonicalises the wiring before parse_wiring and before any node runs"
  - "pin: a scheduler exception finalizes the kv store exactly once"
affects: [databasise/__init__.py]
key-files:
  modified:
    - databasise/__init__.py
    - databasise/tests/test_tracer_end_to_end.py
key-decisions:
  - "canonicalise(wiring_doc) is the first statement of run_wiring; its bytes are reused for the hash and the wiring id (D-11)"
requirements-completed: [TOOL-10]
status: complete
duration: 10min
completed: 2026-10-21
commits: 1
plan_head_before: e165946
plan_head_after: 630f540
actuals:
  tokens: 2500
  tasks: 2
  commits: 1
---

# Phase 15 Plan 06: run_wiring canonicalises first Summary

`databasise.run_wiring` now hashes the wiring document before it parses or dispatches anything, so a top-level `2**70` raises `CanonicalisationError` with zero nodes run; the finalize-in-finally behaviour is pinned.

## What changed

- `databasise/__init__.py`: `wiring_bytes = canonicalise(wiring_doc)` moved to the first statement of `run_wiring`; the later call is deleted. The module docstring and function docstring no longer say `parity.run_arm` calls `run_wiring` (`run_arm.py:4-12` says it does not).
- `databasise/tests/test_tracer_end_to_end.py`: two row nodes plus two local helpers (`_recording_registry`, `_recorder_wiring`).

## Row test node ids and fail-first evidence

TOOL-10 intended test_ref file: `databasise/tests/test_tracer_end_to_end.py`

| Node id | Fail-first |
|---|---|
| `databasise/tests/test_tracer_end_to_end.py::test_a_top_level_integer_outside_int64_runs_no_node` | Failed on the unchanged source: `AssertionError: assert ['only'] == []` (the recording body ran before `CanonicalisationError` was raised). |
| `databasise/tests/test_tracer_end_to_end.py::test_a_scheduler_exception_still_finalizes_the_kv_store` | Passes at the base (met by `1ecfa34`); pin only. The row fails first through the node above. |

For `record-fail --at`, use the commit before `630f540`, which is `e165946`. The file imports only names that exist at the phase base.

## Test results

`databasise/.venv/bin/python -m pytest -q databasise/tests/test_tracer_end_to_end.py databasise/tests/runner databasise/tests/test_removed_stores_absent.py databasise/tests/test_tracer_composer_finalize.py databasise/tests/test_embed_startup.py databasise/tests/test_phase_success_criteria.py databasise/tests/test_docstring_currency.py -p no:cacheprovider` gave 199 passed. This includes the protected WIRE-10, WIRE-11 (`runner/test_node_trace_fields.py`), WIRE-18 and STOR-13/14 (`test_removed_stores_absent.py`) files, all green and untouched.

## Deviations from Plan

- Tasks 1 and 2 are in one commit (`630f540`) because both edit the same test file and the Task 2 node passes at the base; a split would have needed a partial-file stage with no gain. No Rule 1-3 fixes. No protected test touched.
- Bash heredoc edits to the test file were refused by the BAK check-edit hook; the Edit tool was used instead.

## Known Stubs

None.

## Commits

- 630f540: fix(15-06): run_wiring canonicalises the wiring before any node runs; finalize-on-failure pinned

## Self-Check: PASSED

- databasise/__init__.py contains `canonicalise(wiring_doc)` once.
- Commit 630f540 is an ancestor of HEAD.
