---
phase: 15-offline-tooling-packaging
plan: 12
subsystem: parity
tags: [v1-arm, driver, refusals, env-file]

requires:
  - phase: 15-02
    provides: "databasise/cli.py refuse/offline_refusals, inert --spend"
provides:
  - "v1 driver makes one aquery_llm call; V1QueryFailedError; None keywords"
  - "v1_arm: load_env_file refusal before launch; estimate-only main; Optional keyword fields"
affects: [15-01, 15-18]

actuals:
  tokens: 9000
  tasks: 3
  commits: 3

plan_head_before: e9a61c6
plan_head_after: 8ac3559a529725260146f3dbc9118f62fe49f13d

key-files:
  created:
    - databasise/tests/parity/test_v1_driver_script.py
  modified:
    - databasise/parity/v1_driver_script.py
    - databasise/parity/v1_arm.py

key-decisions:
  - "v1_arm.main is estimate-only without --spend (planner decision); the protected tests never call v1_arm.main, so the old default was not kept"
  - "no_results is the only failure treated as an empty retrieval; every other non-success raises V1QueryFailedError"

requirements-completed: [TOOL-07]

duration: 20min
completed: 2026-10-21
status: complete
---

# Phase 15 Plan 12: v1 parity arm Summary

**The v1 driver makes one `aquery_llm` call per job, reports a v1 failure as `V1QueryFailedError` (exit 1), and returns `None` keywords when v1 reports none; `run_v1_arm` loads the env through `load_env_file` first, so a missing file is `MissingParityEnvError` before anything launches.**

## Commits

- beef544 feat(15-12): one aquery_llm call per job (Task 1, tracer)
- 938ac57 feat(15-12): named v1 failure, no_results as empty answer, None keywords (Task 2)
- 8ac3559 feat(15-12): env refusal before launch, estimate-only main (Task 3)

## Row test node ids (TOOL-07)

Intended ledger test_ref: `databasise/tests/parity/test_v1_driver_script.py` (8 nodes). `record-fail --at e9a61c6` (the commit before beef544, this plan's first code commit).

Fail-first evidence, each run against the source as it stood before that task's change (plain AssertionErrors):

| Node | Pre-change failure |
| ---- | ------------------ |
| `test_an_unpinned_hybrid_job_calls_aquery_llm_once` | `AssertionError: ['aquery_data', 'aquery']` (`assert ['aquery_data', 'aquery'] == ['aquery_llm']`) |
| `test_a_v1_failure_exits_one_with_a_named_error` | `AssertionError: a v1 failure came back as a result` |
| `test_absent_keywords_are_none_not_an_echo` | `AssertionError: ['caller-hl']` (`assert ['caller-hl'] is None`) |
| `test_v1_arm_result_accepts_none_keywords` | `AssertionError: TypeError("'NoneType' object is not iterable")` |
| `test_a_missing_env_file_is_refused_before_any_launch` | `AssertionError: AssertionError('a subprocess was launched')`, `'AssertionError' == 'MissingParityEnvError'` fails |
| `test_v1_arm_main_prints_one_named_line` | `AssertionError: SystemExit(2)` (`v1_arm.main` had no `--spend` flag, so argparse exited 2) |
| `test_v1_arm_main_without_spend_is_estimate_only` | `AssertionError: AssertionError('run_v1_arm was called without --spend')` |
| `test_no_results_is_an_empty_retrieval_with_the_fail_answer` | passes after Task 1 (a regression guard for Task 2's failure mapping); at the phase base it fails because the second `aquery` call returns a different answer |

The file imports only stdlib and pytest at module level; `v1_arm` names are imported inside tests. At the commit before beef544 the whole file collects and the Task 1 node fails by AssertionError as shown.

## Test results

- Task 1 set (row file, `test_import_boundary`, protected `test_v1_driver_protocol`): 34 passed.
- Task 2 set (row file, `test_retrieval_parity`, protected `test_v1_driver_protocol`): 34 passed, 1 deselected.
- Task 3 set (row file, protected `test_v1_not_configured`, protected `test_naive_arm_end_to_end`, `tests/clients`, `test_import_boundary`): 138 passed, 2 deselected.
- Plan verification `databasise/tests/parity databasise/tests/foreign`: 245 passed, 3 deselected.
- No protected test failed. The full wave gate and `check_offline_suite.py` were not run (orchestrator-owned).

## Deviations from Plan

None - plan executed as written. Notes:

- The first draft of `test_v1_arm_result_accepts_none_keywords` raised a bare TypeError on the pre-change code; the test was changed to capture the exception and assert on it, so it fails by AssertionError.
- Protected tests read for the Task 3 default check: `test_v1_driver_protocol.py` exercises the corpus driver only, and `test_naive_arm_end_to_end.py` and `test_retrieval_parity.py` do not reference `v1_arm`; none calls `v1_arm.main`, so the estimate-only default stands.
- `databasise/clients/builder.py::load_env_file` and `foreign/v1_corpus_adapter.py` still carry docstrings that describe `v1_arm._load_env_file` as a returns-`{}` copy. Neither file is in this plan; the text is now stale (15-01 or a docs pass can fix it).
- `databasise/parity/.comparison_results/*.json` and `evidence/parity_results/*.json` hold committed `hl_keywords_used` lists; they are not regenerated here.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- databasise/tests/parity/test_v1_driver_script.py FOUND
- commits beef544, 938ac57, 8ac3559 are ancestors of HEAD
