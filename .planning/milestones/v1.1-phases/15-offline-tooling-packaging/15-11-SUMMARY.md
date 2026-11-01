---
phase: 15-offline-tooling-packaging
plan: 11
subsystem: parity
tags: [run_comparison, inconclusive, exit-codes, dry-run, variance-guard]

requires:
  - phase: 15-offline-tooling-packaging
    provides: "15-02 databasise/cli.py (EXIT_*, refuse, offline_refusals) and the inert --spend flag"
provides:
  - "partial, degraded and cyclic decomposed runs yield inconclusive ComparisonRecords (exit 3)"
  - "preflight verifies the v1 working dir the v1 arm uses; variance guard before any call; true run_count; wiring-aware stores"
  - "run_comparison CLI: estimate-only default, unknown --query exits 2 before lock and write, one-line refusals"
affects: [15-18]

actuals:
  tokens: 5500
  tasks: 3
  commits: 3

plan_head_before: 4aea867
plan_head_after: 0919622

tech-stack:
  added: []
  patterns:
    - "inconclusive record built from _inconclusive_record plus dataclasses.replace to keep the decomposed run record"

key-files:
  created:
    - databasise/tests/parity/test_run_comparison.py
  modified:
    - databasise/parity/run_comparison.py

key-decisions:
  - "The keyword variance band now runs after a clean decomposed run (pin call, decomposed run, band, v1), so an incomplete run spends no band calls"
  - "run_count is 2 for a completed record (decomposed run plus v1 run); the band keeps its own run_count"
  - "On the first refusal inside _run_cli the loop stops after one stderr line (a missing key or interpreter holds for every query)"
  - "The results file is written only when there is at least one record, so a refused run never overwrites it with []"

requirements-completed: [TOOL-06]

coverage:
  - id: D1
    description: "partial/degraded/cycle decomposed run is inconclusive with no diff or band; CLI exits 3"
    requirement: "TOOL-06"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_run_comparison.py::test_a_partial_decomposed_run_is_inconclusive_with_no_diff"
        status: pass
    human_judgment: false
  - id: D2
    description: "preflight dir, variance guard, run_count, resolved wiring"
    requirement: "TOOL-06"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_run_comparison.py::test_the_preflight_sees_the_v1_working_dir_override"
        status: pass
    human_judgment: false
  - id: D3
    description: "unknown query exits 2 without writing; estimate-only default; one-line builder refusal"
    requirement: "TOOL-06"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_run_comparison.py::test_an_unknown_query_exits_two_and_leaves_the_results_file_unchanged"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-21
status: complete
---

# Phase 15 Plan 11: run_comparison reports what happened Summary

**`parity.run_comparison` records a partial, degraded or cyclic decomposed run as inconclusive (exit 3), verifies the index the v1 arm really reads, refuses bad variance settings and unknown queries before anything is spent or written, and defaults to a call-count projection.**

## Accomplishments

- Task 1 (tracer): `_incomplete_reason` maps `cycle`, `partial` and `degraded` to `cycle: ...`, `partial: <stop_reason>`, `degraded: <degradation_reason>`; the record keeps `decomposed_run_record`, all diffs and the band are None, band calls and the v1 arm are skipped, status Literal unchanged. `main` returns `cli.EXIT_INCONCLUSIVE`.
- Task 2: `InsufficientVarianceRunsError` is the first statement of `compare_arm_on_query`; `verify_fn` receives `v1_working_dir` (the same value the v1 arm gets); `_run_decomposed_arm` passes the resolved wiring to `_build_stores`; `run_count` is 0 on preflight failure, 1 after an inconclusive decomposed run, 2 when completed.
- Task 3: `load_snapshot`, then `parser.error` for unknown `--query` ids before the lock and any write; projection plus `mode: estimate-only` without `--spend`; refusals (builder, `MissingV1InterpreterError`, `V1ArmSubprocessError`, `StoreLockedError`) print through `cli.refuse` and exit 1; module docstring carries the exit table, the source-checkout note and the site-packages note (D-01).

## Row test node ids and fail-first evidence

Row TOOL-06, intended ledger test_ref: `databasise/tests/parity/test_run_comparison.py` (14 nodes), `record-fail --at 4aea867` (the commit before this plan's first code commit 18b0025). With only `run_comparison.py` reverted to 4aea867, all 14 nodes fail by plain AssertionError:

- `test_a_partial_decomposed_run_is_inconclusive_with_no_diff`: `AssertionError: assert 'completed' == 'inconclusive'`
- `test_degraded_and_cyclic_runs_are_inconclusive_too[degraded|cycle]` and `test_an_inconclusive_keyword_arm_makes_no_band_calls`: same `'completed' == 'inconclusive'`
- `test_an_inconclusive_record_exits_three`: `AssertionError: assert 2 == 3`
- `test_the_preflight_sees_the_v1_working_dir_override`: `AssertionError: assert [None] == [PosixPath('/...v1dir')]`
- `test_a_single_variance_run_is_refused_before_any_llm_call[0|1]`: `AssertionError: assert 'SingleRunBandError' == 'InsufficientVarianceRunsError'`
- `test_a_completed_naive_or_bypass_record_has_a_non_zero_run_count[naive|bypass]`: `AssertionError: assert 0 == 2`
- `test_decomposed_stores_are_built_from_the_resolved_wiring`: `AssertionError: assert False` (`isinstance(None, dict)`)
- `test_an_unknown_query_exits_two_and_leaves_the_results_file_unchanged`: `AssertionError: assert False` (`isinstance(0, SystemExit)`; the file was overwritten)
- `test_without_spend_the_cli_is_estimate_only`: `AssertionError: assert AssertionError('must not be reached') == 0`
- `test_a_builder_refusal_is_one_stderr_line`: `AssertionError: assert 2 == 1` (two `error comparing query` lines)

The file imports only names present at the phase base, copies every fake, needs no `v1/.venv`.

## Test results

- Task 1 set (new file, `test_retrieval_parity`, `test_store_leaks`, protected `test_naive_arm_end_to_end`): 42 passed.
- Task 2 set: 30 passed.
- Task 3 set (new file, `test_parity_cli_store_lock`, `test_cli_builder_refusals`): 27 passed.
- Plan verification `databasise/tests/parity`: 176 passed, 3 deselected (live).
- Wider run `tests/parity`, `tests/evidence`, `tests/launcher`, `tests/test_cli_support.py`: 344 passed, 3 deselected.
- Protected set named by the plan (`test_naive_arm_end_to_end.py`): passes untouched.
- `.comparison_results` sha256 digests identical before Task 1 and after Task 3:
  - bypass 3e66ecea843e..., cross_modality f0fdd72bed59..., global 5e50f08ec0ed..., hybrid 579b40677dbc..., local 8bca9633ead0..., naive 65739228b856...

## Deviations from Plan

None in behavior. Notes:

- `ComparisonRecord.to_dict` needed no change for 15-12's `*_keywords_used = None`: it only stores `v1_result.to_dict()` (a dict); the tuple handling lives in `v1_arm.py`, which this plan does not edit.
- The plan-head ledger file (protocol 0c) was not written at the first commit; `plan_head_before` is 4aea867 (HEAD at plan start) and `git rev-list --count 4aea867..HEAD` returned 3 after the task commits.
- I ran `git stash list` once by mistake (read-only; no stash subcommand that changes state was run).
- Ruff reports 3 pre-existing findings in `run_comparison.py` (import order, unused `field`, `collections.abc`); out of scope.

## Known Stubs

None.

## Task commits

- 18b0025: feat(15-11): partial, degraded or cyclic decomposed run is inconclusive, CLI exits 3
- 2b939ec: feat(15-11): preflight dir, variance guard first, true run_count, wiring-aware stores
- 0919622: feat(15-11): unknown queries exit 2 without writing, estimate-only default, one-line refusals

## Self-Check: PASSED

Files exist (`databasise/parity/run_comparison.py`, `databasise/tests/parity/test_run_comparison.py`); commits 18b0025, 2b939ec, 0919622 are ancestors of HEAD.
