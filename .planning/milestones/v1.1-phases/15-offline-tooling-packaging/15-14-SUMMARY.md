---
phase: 15-offline-tooling-packaging
plan: 14
subsystem: parity
tags: [cross-modality, preflight, check-named-arm, estimate-only, exit-codes]

requires:
  - phase: 15-02
    provides: "databasise/cli.py check_named_arm/refuse/offline_refusals/EXIT_OK, inert --spend"
provides:
  - "run_cross_modality refuses by name, before any store read or client, when a capability selector resolves to another arm"
  - "read-only preflight over stores.vector.load_committed for the chunks and hipporag-chunks namespaces"
  - "a partial or degraded arm stops the run; main keeps the records so far in cross_modality.json marked refused"
  - "queries_hash on the record; custom queries change corpus_hash"
  - "estimate-only default and a current module docstring"
affects: [15-01, 15-17, 15-18]

actuals:
  tokens: 9000
  tasks: 3
  commits: 3

plan_head_before: 9e9234a794aac73c40300ce31dc5065d8f755a19
plan_head_after: a4c249ea7bc0e708f7b744784c6a2ecb8a5eea39

key-files:
  created: []
  modified:
    - databasise/parity/run_cross_modality.py
    - databasise/tests/parity/test_cross_modality_isolation.py

key-decisions:
  - "The two check_named_arm calls are the first statements of run_cross_modality and read nothing from preflight; the per-query compare keeps its capability selectors (§18.4)"
  - "preflight's per-namespace check is one helper, _require_namespace, over load_committed; VectorStoreCorruptedError maps to MissingArmIndexError; _vector_namespace_non_empty (which built a FaissVectorStore) is deleted"
  - "DegradedCrossModalityRunError carries query_id, arm_key and the CrossModalityRecord of every query run so far; main writes it with status/reason/query_id/arm_key and returns 1 through cli.refuse"
  - "CrossModalityRecord.to_dict adds queries_hash only when queries were supplied, so the default run's JSON is byte-identical to before"
  - "ArmSelectorMismatchError is added to main's refusal tuple (it is not in cli.offline_refusals' base tuple), so it is a one-line refusal and not a traceback"
  - "The estimate reuses run_arm.estimate_arm for both arms and runs the read-only preflight only when the workspace directory exists"

requirements-completed: [TOOL-09]

duration: 30min
completed: 2026-10-21
status: complete
---

# Phase 15 Plan 14: cross-modality run Summary

**`run_cross_modality` proves before any read or spend that its two capability selectors resolve to arms `naive` and `hipporag`, refuses an unusable workspace through `load_committed` without creating anything, keeps the records of a refused run, records `queries_hash` for custom query lists, and is estimate-only without `--spend`.**

## Commits

- 3a3de69 feat(15-14): selector resolves to the named arm, checked before preflight and clients (Task 1, tracer)
- 3762019 feat(15-14): read-only preflight over `load_committed`, refusing by namespace (Task 2)
- a4c249e feat(15-14): refused run keeps its records, `queries_hash`, estimate-only, current docstring (Task 3)

## Row test node ids (TOOL-09)

Intended ledger test_ref: `databasise/tests/parity/test_cross_modality_isolation.py`. `record-fail --at 9e9234a` (the commit before 3a3de69, this plan's first code commit). The file imports at module level only names that exist at the phase base (`run_cross_modality` module attributes are reached through the module object and `getattr`); each new node was run against the source as it stood before its task's change.

| Node | Pre-change result |
| ---- | ----------------- |
| `test_tool09_a_selector_resolving_to_another_arm_is_refused_before_clients` | `AssertionError: run raised _ClientsBuilt('clients were built')` (`assert '_ClientsBuilt' == 'ArmSelectorMismatchError'`) |
| `test_tool09_a_hipporag_only_workspace_is_refused_naming_lightrag_chunks` | `AssertionError: a HippoRAG-only workspace passed preflight: PreflightResult(directories_disjoint=True, ...)` |
| `test_tool09_preflight_leaves_the_store_root_listing_unchanged` | passes before and after (the old code also created nothing; regression guard, the plan allowed this) |
| `test_tool09_a_degraded_second_query_leaves_the_first_record_on_disk` | `AssertionError: the refusal names no query and arm: 'at least one arm reported partial or degraded on at least one query - refusing to record a confounded run as a clean comparison'` (also no `cross_modality.json`) |
| `test_tool09_custom_queries_change_the_corpus_hash` | `AssertionError: custom queries recorded the default corpus_hash` |
| `test_without_spend_the_cli_is_estimate_only` | `AssertionError: main raised AssertionError('work started without --spend')` |

The `--spend` degraded-run test patches `cross_modality.DEFAULT_V1_ENV_PARITY` to an empty temp file, `import_index.DEFAULT_STORE_ROOT`, `_import_workspace`, `_RESULTS_DIR`, `_load_env_file`, `_build_clients`, `preflight` and `Databasise`; no env file is read and no provider client is built (D-24).

## Test results

- Task 1 set (`test_cross_modality_isolation`, `test_cli_builder_refusals`, protected `test_selector_reachability`): 30 passed.
- Task 2 set: `test_cross_modality_isolation` 9 passed; parity + `test_selector_reachability`: 211 passed, 3 deselected.
- Final set (`databasise/tests/parity` including protected `test_naive_arm_end_to_end`, protected `tests/seam/test_selector_reachability.py`, `databasise/tests/launcher`): 282 passed, 3 deselected.
- No protected test failed. The full wave gate and `check_offline_suite.py` were not run (orchestrator-owned).
- Manual read-only check: `python -m databasise.parity.run_cross_modality` printed `queries: 2 x 2 arms = 4 arm runs`, both arms' node counts (7 and 7), the preflight result for the real parity store and `mode: estimate-only`, exit 0.

## Deviations from Plan

None - plan executed as written. Notes:

- Ruff findings left alone as pre-existing: `TRY004` on the bare-envelope `RuntimeError` in `run_cross_modality.py` and `BLE001` at `test_cross_modality_isolation.py:53` (`_real_hipporag_index_present`).
- A Bash call that scripted an edit to the test file and a `grep -r` over `databasise/` (which holds protected tests) were refused by the BAK hook; the edits were redone with the Edit tool and the grep narrowed to non-test directories. Nothing was changed by the refused calls.
- Interaction with 15-17: the module docstring no longer contains the strings "never invoked" or "BLOCKED"; it names the 2026-09-10 runs, the Phase 12 rebuild, the exit table and the source-checkout need.

## Known Stubs

None.

## Self-Check: PASSED

- databasise/parity/run_cross_modality.py, databasise/tests/parity/test_cross_modality_isolation.py: found, committed.
- 3a3de69, 3762019, a4c249e: ancestors of HEAD.
