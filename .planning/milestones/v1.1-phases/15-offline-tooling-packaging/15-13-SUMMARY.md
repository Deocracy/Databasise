---
phase: 15-offline-tooling-packaging
plan: 13
subsystem: parity
tags: [storage-audit, run-arm, hipporag, estimate-only, exit-codes]

requires:
  - phase: 15-02
    provides: "databasise/cli.py refuse/offline_refusals/EXIT_INCONCLUSIVE, inert --spend"
provides:
  - "storage_audit and run_arm accept --arm hipporag (query nodes only, stores from the resolved wiring)"
  - "storage_audit: unreached state, unreached=N summary count, exit 3 on partial or cyclic runs"
  - "run_arm and storage_audit estimate-only by default, named refusals via cli.refuse"
affects: [15-01, 15-18]

actuals:
  tokens: 9500
  tasks: 3
  commits: 3

plan_head_before: e0cf13f990d11e72810a7eda18bf0dcf1eb570ac
plan_head_after: 7b6ac15385d350e140a747c5c6b605553acda7c8

key-files:
  created: []
  modified:
    - databasise/parity/run_arm.py
    - databasise/parity/storage_audit.py
    - databasise/tests/parity/test_storage_audit.py

key-decisions:
  - "run_arm.resolve_query_arm is the one place an arm becomes a stamped query wiring: LightRAG arms keep resolve_arm, other modalities go through wiring_for_name and without_recipe_only_nodes; the query is stamped by the engine's consumes_query-driven _inject_query, imported inside the function"
  - "run_arm._inject_query is byte-for-byte unchanged (protected test_naive_arm_end_to_end and test_build_hipporag_index test_3 import it) but is no longer called by run_arm itself"
  - "A degraded but complete run prints 'degraded: <reason>' and keeps exit 0; only partial or cyclic runs exit 3"
  - "run_audit also returns store_namespaces, stop_reason, degraded and degradation_reason; main reads all of them with .get so the fakes in existing tests still work"
  - "A violation (exit 1) takes precedence over partial (exit 3)"

requirements-completed: [TOOL-08]

duration: 25min
completed: 2026-10-21
status: complete
---

# Phase 15 Plan 13: storage audit and run_arm Summary

**`storage_audit` and `run_arm` accept `--arm hipporag` (HippoRAG's seven index nodes never dispatch), the audit exits 3 with `partial:` or `cycle:` and reports never-dispatched nodes as `unreached`, and both CLIs print an estimate and `mode: estimate-only` unless `--spend` is given.**

## Commits

- f5bec33 feat(15-13): hipporag arm, stores built from the resolved wiring (Task 1, tracer)
- 858320e feat(15-13): partial or cyclic audit exits 3, unreached state (Task 2)
- 7b6ac15 feat(15-13): estimate-only default, named refusals, no in-function json import (Task 3)

## Row test node ids (TOOL-08)

Intended ledger test_ref: `databasise/tests/parity/test_storage_audit.py`. `record-fail --at e0cf13f` (the commit before f5bec33, this plan's first code commit; it carries 15-02's inert `--spend`, so the edited `main` tests collect and pass there).

Seven new nodes, each failing by a plain AssertionError against the source as it stood before its task's change:

| Node | Pre-change failure |
| ---- | ------------------ |
| `test_tool08_storage_audit_audits_the_hipporag_arm` | `AssertionError: the hipporag arm was refused: SystemExit 2` (argparse: invalid choice 'hipporag') |
| `test_tool08_run_arm_accepts_hipporag` | `AssertionError: run_arm refused hipporag: SystemExit 2` (`assert SystemExit(2) is None`) |
| `test_tool08_a_budget_halted_run_exits_three_and_marks_unreached_nodes` | `AssertionError: main raised KeyError: 'unreached'` (`assert KeyError('unreached') is None`) |
| `test_tool08_a_cyclic_wiring_exits_three_with_cycle` | `assert 0 == 3` (a cyclic run exited 0) |
| `test_tool08_audit_run_marks_a_not_scheduled_node_unreached_never_no_touch` | `AssertionError: audit_run takes no statuses: audit_run() got an unexpected keyword argument 'statuses'` |
| `test_storage_audit_without_spend_is_estimate_only` | `AssertionError: main raised AssertionError: work started without --spend` |
| `test_run_arm_without_spend_is_estimate_only` | `AssertionError: main raised AssertionError: work started without --spend` |

`test_audit_run_still_accepts_two_arguments` passes before and after (a regression guard). The two existing `main` tests now pass `--spend` and call `_isolate_audit_paths`, which points `DEFAULT_STORE_ROOT` (import_index, run_arm, storage_audit), `run_arm.DEFAULT_V1_ENV_PARITY` and `run_arm._parity_workspace` at temp values. The new file imports at module level only names that exist at the phase base; new behaviour is reached through `main`/`audit_run` calls whose exceptions are captured.

## Test results

- Task 1 set (`test_storage_audit`, `test_build_hipporag_index`, protected `test_naive_arm_end_to_end`, `test_cli_builder_refusals`, `test_parity_cli_store_lock`): 51 passed, 1 deselected.
- Task 2 set (`test_storage_audit`, protected `test_trace_completeness`): 32 passed.
- Task 3 set (`databasise/tests/parity`, `databasise/tests/launcher`, protected `tests/clients/test_build_clients.py`): 280 passed, 3 deselected.
- Final combined run (parity, launcher, `test_build_clients`, `test_trace_completeness`): 291 passed, 3 deselected.
- No protected test failed. The full wave gate and `check_offline_suite.py` were not run (orchestrator-owned).
- Manual read-only checks: `python -m databasise.parity.storage_audit --arm hipporag` printed `{"arm": "hipporag", "nodes": 7, "calls_llm": 2, "calls_embedding": 1, "calls_rerank": 0}` and `mode: estimate-only`, exit 0 (seven query-side nodes, no index nodes); `run_arm --arm naive --query q` printed the naive estimate (7 nodes), exit 0.

## Deviations from Plan

None - plan executed as written. Notes:

- Test 1's "a `hipporag-` namespace" in stdout needed a place to come from: `run_audit` now returns `store_namespaces` and `main` prints one `store_namespaces: kv=... graph=...` line. Output addition only.
- An ad-hoc `git stash list` was run once (read-only, no refs touched) before noticing the rule against any stash subcommand; nothing was stashed or changed.
- Pre-existing ruff finding `RUF059` at `test_storage_audit.py:130` (unused `rows`) was left alone (out of scope).

## Known Stubs

None.

## Self-Check: PASSED

- databasise/parity/run_arm.py, databasise/parity/storage_audit.py, databasise/tests/parity/test_storage_audit.py: found, committed.
- f5bec33, 858320e, 7b6ac15: ancestors of HEAD.
