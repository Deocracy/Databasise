---
phase: 15-offline-tooling-packaging
plan: 18
subsystem: tooling
tags: [cli, dry-run, refusals, offline-gate, tool-04, tool-05, tool-17]

requires:
  - phase: 15-02
    provides: "databasise/cli.py refuse, offline_refusals, positive_int; inert --spend"
  - phase: 15-10
    provides: "aa_run one event loop, cli.positive_int, remint estimate-only, _PACKAGE_DIR"
  - phase: 15-12
    provides: "v1_arm estimate-only default"
  - phase: 15-15
    provides: "build_hipporag_index estimate-only, empty-store build, ChunkCountMismatchError"
provides:
  - "TOOL-05 row file: every spending CLI is estimate-only without --spend; the HippoRAG build cases"
  - "TOOL-04 row file: every named failure is one stderr line and exit 1 on the six CLIs; exit 2 on a bad flag on fourteen"
  - "remint maps a mint-time BundleDriftError or MissingTargetFamilyError to exit 1 (product fix found by the row)"
  - "CODEBASE-MAP section 5 and STATE carry the phase's recorded limits; the offline gate is green in both styles"
affects: [phase-15-verification]

actuals:
  tokens: 21000
  tasks: 3
  commits: 4

plan_head_before: 2d5ac3c82c39279ddcababbe91f901c9eb4d1e83
plan_head_after: a8d863a18ac275d503ac08a6d06a0be20c072115

tech-stack:
  added: []
  patterns:
    - "row files import only stdlib, pytest, httpx and openai at module level and resolve every package name inside the test"
    - "one error table x one injection table, with the injection point chosen per CLI (env loader, client builder, work function, mint)"

key-files:
  created:
    - databasise/tests/test_dry_run_default.py
    - databasise/tests/test_cli_refusals.py
  modified:
    - databasise/eval/remint.py
    - docs/gui/CODEBASE-MAP.md
    - .planning/STATE.md

key-decisions:
  - "TOOL-17 is met by removal (D-20): no code written; test_removed_stores_absent.py is the row check"
  - "A loop-bound fake client is exercised through a stubbed calibrate_family (the only family that calls the judge client is answer_level), so the two-family case binds the client on its first family and fails on a second loop"
  - "FloorStore persistence runs for real in the one-loop case (a SimpleNamespace result carries the instance hash); the engine, vector store and calibrate_family are the stubs"

requirements-completed: [TOOL-04, TOOL-05, TOOL-17]

duration: 75min
completed: 2026-10-22
status: complete
---

# Phase 15 Plan 18: Row files for TOOL-04 and TOOL-05, TOOL-17 by removal, and the green offline gate Summary

**All nine spending CLIs are pinned estimate-only by one parametrised row, all six refusing CLIs are pinned to one stderr line and exit 1 across 58 injected failures (which also exposed that `remint` let a mint-time `BundleDriftError` or `MissingTargetFamilyError` escape as a traceback, now fixed), and `check_offline_suite.py` passes in both styles with 2877 passed, 4 deselected.**

## Accomplishments

- `databasise/tests/test_dry_run_default.py` (11 nodes): `test_a_call_without_spend_is_estimate_only[<cli>]` over build_hipporag_index, remint, run_arm, storage_audit, run_comparison, run_cross_modality, v1_arm, corpus_ingest, aa_run. Each case replaces every lock, env loader, client builder, work function, engine and `subprocess.run` with a counting fake that raises, points every store root and results directory into `tmp_path`, and asserts exit 0, `mode: estimate-only` on stdout, zero fake calls and an unchanged `tmp_path` tree. Two more nodes: `--spend` on an empty store root builds, and a chunk embedder that writes nothing raises `ChunkCountMismatchError` (found 0, expected 3).
- `databasise/tests/test_cli_refusals.py` (70 nodes): 58 `test_a_named_failure_is_one_stderr_line_and_exit_one` cases, `test_n_resamples_zero_exits_two_before_any_client`, `test_a_two_family_spend_run_uses_one_event_loop`, `test_the_committed_bundle_root_is_unchanged`, and `test_every_offline_cli_exits_two_on_an_unknown_flag` over 14 CLIs.
- Product fix (Rule 1): `remint.main` called `remint(...)` after its refusal try, so `mint_bundle`'s `BundleDriftError` and `MissingTargetFamilyError` surfaced as tracebacks. The mint now sits inside the try (commit 2d4e649).
- TOOL-17: `databasise/tests/test_removed_stores_absent.py` passes (5 passed). No code written (D-20).
- `docs/gui/CODEBASE-MAP.md` section 5 states ten MCP tools (`TOOL_NAMES`), the D-03 exit table, the estimate-only default for the nine CLIs, run_comparison exit 0/1/2/3, storage_audit exit 3, every `all_wirings()` arm, the `import_index` flags and printed workspace, falsifier2 exit 1, and that the eval CLIs plus `check_import_boundary` run from a wheel while the parity CLIs need a source checkout.
- `STATE.md`: a Phase 15 Blockers/Concerns bullet with the recorded limits, and decision lines for the v1_arm default (SC2) and the cbm `timeout + 4 s` bound.

## Task Commits

1. **Task 1 (tracer): TOOL-05 row file** - `e85dc9d` (test)
2. **Task 2: TOOL-04 row file** - `0ca5f73` (test), preceded by the product fix `2d4e649` (fix)
3. **Task 3: codebase map** - `a8d863a` (docs)

Gate and TOOL-17 need no commit of their own. Planning metadata: the docs commit that follows this file.

## Row test node ids and fail-first evidence

Ledger intent (orchestrator): both `record-fail --at 00eeae8` (the `docs(15): create phase plan` commit). Each file was copied alone into a detached worktree of `00eeae8` (since removed) with `PYTHONPATH` set to that worktree; it collects and every failure is an AssertionError (no other exception type).

**TOOL-05** - `databasise/tests/test_dry_run_default.py`, 9 failed, 2 passed at `00eeae8`:

| Node | Failure at 00eeae8 |
| ---- | ------------------ |
| `test_a_call_without_spend_is_estimate_only[build_hipporag_index]` | `AssertionError: ...build_hipporag_index.main([]) raised AssertionError('build_hipporag_index.store_lock was reached without --spend')` |
| `[remint]` | `...remint.main([]) raised AssertionError('remint._load_env_file was reached without --spend')` |
| `[run_arm]`, `[storage_audit]`, `[run_comparison]`, `[run_cross_modality]` | `...store_lock was reached without --spend` |
| `[v1_arm]` | `...v1_arm.main([...]) raised AssertionError('v1_arm.run_v1_arm was reached without --spend')` |
| `[corpus_ingest]`, `[aa_run]` | pass at the base (already estimate-only; the node pins them) |
| `test_build_hipporag_index_spend_builds_on_an_empty_store_root` | `AssertionError: main(['--spend']) raised SystemExit(2)` (no `--spend` flag at the base) |
| `test_build_hipporag_index_refuses_an_empty_chunk_namespace_by_name` | `AssertionError: a build with no chunk vectors was reported as built` |

Seven CLIs, not the six the plan estimated, spend on a bare call at the base. All 11 nodes pass at HEAD.

**TOOL-04** - `databasise/tests/test_cli_refusals.py`, 58 failed, 12 passed at `00eeae8`. Grouped (every line begins `AssertionError`):

- `main returned SystemExit(2); stderr: 'usage: ... unrecognized arguments: --spend'` for 32 cases (run_arm, storage_audit, run_comparison, run_cross_modality and remint: no `--spend` flag at the base). `aa_run` already had the flag, so its failures are the cases below.
- aa_run named errors: `AssertionError: databasise.eval.aa_run has no NoMintedBundleError` (also `QuestionNotInBundleError`, `MissingTargetFamilyCoverageError`, `GoldPassageMappingError`, `EmptyGoldDocumentIdsError`, `EmptyEvalIndexError`, `UnkeyableFloorError`) and `databasise.eval.calibration has no UnpairedScoresError` / `EmptyPairedDifferencesError`.
- Unmapped errors reached the caller: `main returned FileNotFoundError('no such file'); stderr: ''`, the same for `CorpusDriftError`, `MissingTargetFamilyError`, `BundleDriftError`, `APIConnectionError('Connection error.')`.
- Event loop: `AssertionError: main returned APIConnectionError('Event loop is closed')` (`test_a_two_family_spend_run_uses_one_event_loop`).
- `test_n_resamples_zero_exits_two_before_any_client`: `AssertionError: 0` (the run was accepted).
- `test_every_offline_cli_exits_two_on_an_unknown_flag`: fails for import_index (`AssertionError('work started on a bad argument')`), check_import_boundary, falsifier2 and f07_report (they took no argv or did work first); the other ten CLIs already exit 2 there.
- `test_the_committed_bundle_root_is_unchanged` passes at the base and pins the path.

Each error name fails on at least one CLI at the base (the criterion): MissingParityEnvKeyError, UnparseableProviderRoutingError, EmptyQueryObjectError (SeamRefusalError subclass), FileNotFoundError, CorpusDriftError, MissingTargetFamilyError, BundleDriftError and APIConnectionError fail on every CLI that lacked `--spend`, and on `aa_run` and `remint` via the named-error and mint paths above.

Pairs covered (58 failure cases):

- run_arm, storage_audit, run_comparison, run_cross_modality (6 each): MissingParityEnvKeyError, UnparseableProviderRoutingError, FileNotFoundError, EmptyQueryObjectError, CorpusDriftError, APIConnectionError. run_arm and storage_audit inject the builder errors at `_build_clients` and FileNotFoundError at `_load_env_file`; the other four inject at the work function.
- aa_run (21): the same six (builder at `_build_clients`, FileNotFoundError at `_load_env_file`), BundleDriftError at `load_bundle`, MissingTargetFamilyError, and the 13 named errors (SplitNotCalibratableError, NoMintedBundleError, MissingTargetFamilyCoverageError, QuestionNotInBundleError, EmptyGoldDocumentIdsError, GoldPassageMappingError, UnpairedScoresError, EmptyPairedDifferencesError, UnparseableJudgeVerdictError, UnusableFloorError, UnkeyableFloorError, ConfoundedPassError, EmptyEvalIndexError) at `calibrate_family`.
- remint (8): MissingParityEnvKeyError and UnparseableProviderRoutingError at `_build_clients`, FileNotFoundError at `_load_env_file`, CorpusDriftError at `load_snapshot`, BundleDriftError and MissingTargetFamilyError at the mint (`remint`), APIConnectionError and UnresolvedJudgeIdentityError at `resolve_judge_identity`.

On the pre-Task-2 HEAD (before commit 2d4e649) the two remint mint cases fail: `main returned MissingTargetFamilyError('a question has no gold document ids'); stderr: ''` and the BundleDriftError counterpart.

**TOOL-17** - `databasise/tests/test_removed_stores_absent.py` (existing, protected): 5 passed. Orchestrator: `record-fail --at 226b2cf^` (D-20).

## Ledger row-to-file mapping (all twenty rows, for the orchestrator)

| Row | Intended test_ref | Fail-first route (from each plan's SUMMARY) |
| --- | ----------------- | ------------------------------------------- |
| TOOL-01 | `databasise/tests/test_packaging.py` (node `test_the_wheel_record_lists_the_tools_the_bundles_and_both_fixtures`) | in-tree fail-first (15-01); no `--at` |
| TOOL-02 | `databasise/tests/parity/test_import_index_cli.py` | 15-09 |
| TOOL-03 | `databasise/tests/parity/test_import_verification.py` (`test_tool03_a_missing_v2_graph_is_a_graph_topology_violation`, `test_tool03_an_empty_store_root_is_refused_as_a_precondition`) | 15-09 |
| TOOL-04 | `databasise/tests/test_cli_refusals.py` | `--at 00eeae8` |
| TOOL-05 | `databasise/tests/test_dry_run_default.py` | `--at 00eeae8` |
| TOOL-06 | `databasise/tests/parity/test_run_comparison.py` | `--at 4aea867` |
| TOOL-07 | `databasise/tests/parity/test_v1_driver_script.py` | `--at e9a61c6` |
| TOOL-08 | `databasise/tests/parity/test_storage_audit.py` | `--at e0cf13f` |
| TOOL-09 | `databasise/tests/parity/test_cross_modality_isolation.py` | `--at 9e9234a` |
| TOOL-10 | `databasise/tests/test_tracer_end_to_end.py` | `--at e165946` |
| TOOL-11 | `databasise/tests/eval/test_eval_store_boundary.py` | `--at 7e12829` |
| TOOL-12 | `databasise/tests/seam/test_promotion_floor.py` (node `test_a_floor_for_the_arms_own_hash_lifts_the_gate_to_not_built`) | `--at 9a7c7f5` |
| TOOL-13 | `databasise/tests/eval/test_bundle_versioning.py` | 15-05 (HEAD 0aff830 plus new tests) |
| TOOL-14 | `databasise/tests/evidence/test_parity_report_render.py` | `--at 81e11c4` |
| TOOL-15 | `databasise/tests/evidence/test_falsifier2_verdict.py` | `--at 7a8e54da7eddd146fa3bc800a76a09b8b3b78501` |
| TOOL-16 | `databasise/tests/parts/test_admission.py` | `--at 8fc7a25` |
| TOOL-17 | `databasise/tests/test_removed_stores_absent.py` | `--at 226b2cf^` |
| TOOL-18 | `databasise/tests/foreign/test_cbm_adapter.py` | 15-04 |
| TOOL-19 | `databasise/tests/mcp/test_tool_descriptions.py` | `--at dedcbe6` |
| TOOL-20 | `databasise/tests/evidence/test_docstring_facts.py` | `--at 00eeae8` |

Rows whose route reads "15-NN" take the exact commit from that plan's own SUMMARY (TOOL-13 and TOOL-18 name a working-tree fail-first, not an `--at` commit).

## Test results

- Task 1 set (`test_dry_run_default.py`, `parity/test_build_hipporag_index.py`): 17 passed.
- Task 2 set (`test_cli_refusals.py`, `test_cli_support.py`, `parity/test_cli_builder_refusals.py`, `eval/test_remint.py`): 93 passed.
- Protected sets named by the plan: `test_removed_stores_absent.py` 5 passed; `test_check_offline_suite.py` and `test_packaging.py` pass (18 passed with the former, no skips). No protected test failed and none was edited.
- **Offline gate** `databasise/.venv/bin/python databasise/tools/check_offline_suite.py`: exit 0, no contradictory skip, no skip line in either style.
  - `pytest -q -rs: 2877 passed, 4 deselected in 720.58s (0:12:00)`
  - `python -m pytest -q -rs: 2877 passed, 4 deselected in 684.21s (0:11:24)`
  - Phase 14 baseline 2608 passed, 4 deselected: +269 passed, deselected unchanged.
  - The packaging test ran and passed (no skip, warm uv cache). A skip would not have counted as a pass.
- The separate wave command `pytest -q databasise` was not run: the dispatch asked for the gate once, and the gate runs the whole suite in both styles.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] remint's mint ran outside its refusal try**
- **Found during:** Task 2 (row cases `remint-BundleDriftError-remint`, `remint-MissingTargetFamilyError-remint`)
- **Issue:** `remint.main` called `remint(...)` (which calls `mint_bundle`) after the `except refusals` block, so the two named errors TOOL-04 lists for remint escaped as a traceback.
- **Fix:** Moved the mint call into the existing try; the refusal tuple already held both classes.
- **Files modified:** `databasise/eval/remint.py`
- **Commit:** 2d4e649

### Other notes

- The plan's behaviour list gave TOOL-05 as "six CLIs spend on a bare call at the base"; seven do (v1_arm also did). The nine-CLI table covers all.
- `test_cli_refusals.py` covers more injection pairs than the plan's minimum (every parity CLI gets all six common errors, including the provider error), because the shared refusal tuple is the one thing each `main` must route through.
- The two-family loop test stubs `calibrate_family` (it is the call that awaits the judge client); the real FloorStore persistence runs against `tmp_path`.
- A leftover worktree `.claude/worktrees/agent-aa9dde19a41b39acb` belongs to the orchestrator; this plan's `p15-base` worktree was removed.

**Total deviations:** 1 auto-fixed (Rule 1). **Impact:** one product-side change in an already-landed CLI, found by the row.

## Notes for the verification report (recorded limits)

- No project LICENSE while the wheel ships HotpotQA fixture text under CC BY-SA 4.0 (Deferred).
- From an installed wheel, `remint --spend` and `.comparison_results` would write into site-packages; covered by the estimate-only default and the source-checkout docstrings.
- The committed `parity_results/*.json` carry the old `run_count` meaning; re-running needs spend.
- The packaging test skips on a cold uv cache and a skip is not a pass (it ran and passed in this gate).
- No production part reports `cache_hit`, so no real floor exists yet, and only an engine started on the eval store root reads floors.
- The cbm launch timeout bound is timeout + 4 s (SDK teardown).
- The TOOL-05 row text is read as covering every spending CLI (D-04).
- `v1_arm.main` gained the estimate-only default by planner decision (SC2); no protected test calls it.
- The orchestrator owns all ledger steps (test_ref, record-fail, plant runs); nothing here ran `scripts/ledger-amend.py`.

## Known Stubs

None.

## Threat Flags

None. No endpoint, auth path or schema change; T-15-50 (env file), T-15-51 (dry-run regression) and T-15-52 (skip counted as pass) are mitigated by the temp env paths and loader fakes, the nine-CLI parametrised row, and the explicit skip accounting above.

## Self-Check: PASSED

- databasise/tests/test_dry_run_default.py FOUND
- databasise/tests/test_cli_refusals.py FOUND
- databasise/eval/remint.py FOUND
- commits e85dc9d, 2d4e649, 0ca5f73, a8d863a are ancestors of HEAD
