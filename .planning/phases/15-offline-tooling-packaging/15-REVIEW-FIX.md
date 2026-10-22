---
phase: 15
---
# Phase 15: Code Review Fix Report

**Source review:** .planning/phases/15-offline-tooling-packaging/15-REVIEW.md

## Lane A

**Fixed at:** 2026-10-21. Findings in scope: 11. Fixed: 11. Not fixed: 0. Needs owner grant: 0.

Edits and commits were made on the main checkout, with no worktree. Every test listed below ran there with `databasise/.venv/bin/python -m pytest -q <paths> -p no:cacheprovider`. The final run covered `tests/eval`, `tests/parity`, `tests/stores`, `tests/launcher`, `test_cli_refusals.py`, `test_cli_support.py`, `test_dry_run_default.py`, `test_import_boundary.py` and `test_docstring_currency.py`: 686 passed, 3 deselected. `tests/seam` (1109 passed) also ran after the A-WR-04 change to `stores/probes.py`. No protected test failed. No protected test was edited.

The new tests are in two new files, which no ledger row names: `databasise/tests/eval/test_review_fix_15_lane_a.py` (E) and `databasise/tests/parity/test_review_fix_15_lane_a.py` (P).

| Finding | Status | Commit | Test node | Notes |
|---|---|---|---|---|
| A-CR-01 | fixed | a8dae39 | E::test_corpus_ingest_limit_below_one_exits_2, E::test_corpus_ingest_estimate_refuses_limit_below_one | `--limit` is `cli.positive_int` (exit 2); `estimate()` raises the new `NonPositiveLimitError` for the library path. |
| A-WR-01 (+B-WR-05) | fixed | 8d68406 | E::test_offline_refusals_cover_client_and_vector_store_refusals, E::test_resolve_judge_identity_maps_a_model_less_response_to_its_own_refusal, E::test_remint_spend_client_refusal_is_one_line_and_exit_1 | Six client and store classes added to `cli.offline_refusals`. `resolve_judge_identity` re-raises `ModelIdentityMissingError` as `UnresolvedJudgeIdentityError`. |
| A-WR-02 | fixed | 9bc6c3e | P::test_status_less_fail_response_is_an_empty_retrieval, P::test_failure_status_with_empty_metadata_still_raises | Only `status == "failure"` (other than `no_results`) raises. The test loads the driver with stand-in `lightrag` modules; v1 is never imported. |
| A-WR-03 | fixed | 7b3379e | P::test_v1_arm_subprocess_error_names_the_driver_failure_line | The message takes the last stderr line that is not an `INFO:`/`WARNING:`/`DEBUG:` line; the full stderr stays on `.stderr`. Not done: the review's optional middle-cut for `cli.refuse`'s 500-character limit. |
| A-WR-04 | fixed | 77e5da3 | P::test_verify_import_creates_no_text_chunks_namespace, P::test_verify_import_reads_v2_chunk_text_without_rewriting_the_store, P::test_import_index_verify_on_a_missing_store_root_writes_nothing | v2 chunk text is read through `stores.probes.list_kv_prefix`, which now accepts an empty prefix. `--verify` on a missing store root takes no lock. |
| A-WR-05 | fixed | bca102f | P::test_verify_import_refuses_a_missing_v1_index, P::test_verify_import_flags_a_v2_graph_with_no_v1_graph | A missing v1 dir returns `refused`/`precondition`. A v2-only graph is a `graph-topology` violation. |
| A-WR-06 | fixed | eef7173 | P::test_a_refused_hipporag_build_leaves_the_unverified_marker, P::test_cross_modality_preflight_refuses_an_unverified_hipporag_build | `build_index` writes `.hipporag-build-unverified.json` before any store opens and removes it only after verification passes; preflight refuses a workspace that carries it. Of the review's three options this one forces no rebuild: a store built and verified before the fix has no marker and still passes. |
| A-WR-07 | fixed | d6db78d | E::test_eval_spend_paths_take_the_store_lock[corpus_ingest], E::test_eval_spend_paths_take_the_store_lock[aa_run] | Both `--spend` paths run inside `store_lock(_EVAL_INGEST_STORE_ROOT)`. `v1/.gitignore` now ignores `.eval_corpus_store/`. Residual: the existing `--spend` cases in `test_aa_run.py` and `test_corpus_ingest.py` do not patch the root, so they create the ignored file `v1/.eval_corpus_store/.engine.lock`. Fixing that needs an autouse fixture in those files that patches `_EVAL_INGEST_STORE_ROOT` to `tmp_path`. They were not read or edited, because they may be protected. |
| A-WR-08 | fixed | e75f04e | P::test_run_arm_exit_code_reports_an_inconclusive_run (4 cases) | Exit 3 for cyclic, partial or degraded, matching D-07/D-09 (the review's snippet checked only partial). The docstring exit table is updated. |
| A-WR-09 | fixed | 0d0eb19 | P::test_import_index_refuses_a_drifted_snapshot_by_name, P::test_import_index_refuses_a_corrupted_vector_store_by_name, P::test_build_hipporag_index_estimate_refuses_a_drifted_snapshot_by_name | Snapshot and workspace derivation moved inside the `try`; `import_index` catches `cli.offline_refusals(MissingV1IndexError)`. Not covered: the RocksDB "lock held" error from `_v1_graph`, because its pycozo exception class is not a named refusal. |
| A-WR-10 | fixed | 79125b5 | P::test_a_refused_comparison_run_never_overwrites_the_last_complete_result | A refused run writes `<arm>.refused.json` with `{status: "refused", reason, records}` and leaves `<arm>.json` unchanged. `cli.refusal_line` is split out of `cli.refuse`. |

No fix contradicts D-01..D-24. A-WR-02 follows D-08: exit 1 only on v1's exception path. A-WR-04 and A-WR-05 extend D-06 and use its `precondition` assertion.

_Fixer: Claude (gsd-code-fixer), lane A_

## Lane B

**Fixed at:** 2026-10-21. Findings in scope: 8. Fixed: 8. Not fixed: 0. Needs owner grant: 0.

Edits and commits were made on the main checkout, with no worktree, on top of lane A's commits. Every test listed below ran there with `databasise/.venv/bin/python -m pytest -q <paths> -p no:cacheprovider`. The final run covered `tests/eval`, `tests/parity`, `test_cli_refusals.py`, `test_cli_support.py`, `test_dry_run_default.py`, `test_import_boundary.py`, `test_docstring_currency.py`, and `tests/seam/test_floors_store.py`, `test_promotion_floor.py`, `test_promotion_posture.py` and `test_promote.py`: 537 passed, 3 deselected. All of `tests/seam` (1125 passed) ran after the B-WR-02 change to `seam/floors_store.py`. No protected test failed at a commit, and no protected test was edited.

All new tests are in one new file that no ledger row names: `databasise/tests/eval/test_review_fix_15_lane_b.py` (B).

| Finding | Status | Commit | Test node | Notes |
|---|---|---|---|---|
| B-CR-01 | fixed | 0869ea4 | B::test_judge_verdict_parses_a_leading_verdict (7 cases), B::test_judge_verdict_refuses_a_negated_or_echoed_verdict (5 cases) | The reply must open with the verdict, after punctuation or markdown and at most one `Verdict:` label, and must contain no second distinct verdict word. The TOOL-12 forms still parse. This is a logic change, so a human should check it: a judge that writes "CORRECT, not INCORRECT" is now refused. |
| B-WR-01 | fixed | 11eeba8 | B::test_a_repeated_family_is_estimated_and_run_once | `families = tuple(dict.fromkeys(args.family))`. |
| B-WR-02 | fixed | 9c4f337 | B::test_floor_store_reads_create_no_side_files, B::test_floor_store_reads_a_floor_in_a_read_only_directory, B::test_floor_store_refuses_a_wal_without_its_shm | The read paths follow `stores.probes.list_kv_prefix`'s pattern. They open `immutable` unless a live writer's `-wal` and `-shm` both exist, and they refuse a `-wal` that has frames but no `-shm`. Only a "no such table" error reads as no floor. Any other sqlite error now propagates out of `promote`. |
| B-WR-03 | fixed | 2e0fe3e | B::test_floor_store_record_many_writes_all_rows_or_none, B::test_aa_run_prints_its_result_before_a_persist_refusal (2 cases) | Adds `FloorStore.record_many`, which writes all rows in one transaction; `record` calls it. `aa_run` prints `AARunResult` before it persists. A sqlite or OS error on the write is the new `FloorPersistError`, which `_refusals()` maps to exit 1. |
| B-WR-04 | fixed | 1e1b196 | B::test_calibration_stops_at_the_first_question_a_bypass_check_refuses (2 cases) | `run_one_pass` takes a `node_check` and resolves each trace before it scores, so the check runs before the judge call. `calibrate_family` passes `_verify_cache_bypassed` (same refusal text) for both passes. A real run now stops at the first question of run_a. The module docstring is updated. |
| B-WR-06 | fixed | 1a2e13b | B::test_a_truncated_usage_line_is_a_named_refusal | `_load_usage_entries` raises the new `CorruptUsageLogError` (version, path, line), and `cli.offline_refusals` includes it. Corrupt lines are refused, not skipped, because a skipped line could be the `sealed_open` entry. |
| B-WR-07 | fixed | c0cb857 | B::test_an_opened_version_is_never_used_as_sealed | The new `SealedPartitionOpenedError` is in `cli.offline_refusals`. `open_sealed` refuses a version that is already opened, and `remint.main` refuses a mint that dedups to an opened version (exit 1). `mint_bundle` itself still returns the opened version flagged `sealed_opened`, because the existing `test_bundle_versioning.py::test_reminting_after_open_sealed_returns_a_version_flagged_opened` pins that; the first attempt refused inside `mint_bundle` and failed that test, so it was reverted before commit. The review's "mint fresh" option was rejected: it would re-label opened questions as sealed. "Report the flag in remint's output" is covered by the refusal line, since a successful remint can no longer return an opened version. The floor-staleness statement is in bundle.py's docstring and API-INVENTORY (B-WR-08). |
| B-WR-08 | fixed | d00e8ec | none (documentation); `test_docstring_currency.py` passes | Rewrote `docs/gui/API-INVENTORY.md` :654 (ten tools, descriptions, the `RefusalToolError` bare-JSON mapping, the `databasise-mcp` launcher), :736 (no CLI spends without `--spend`; `open_sealed` makes floors stale), :836 (the gate's lazy eval imports; the wheel ships `databasise.tools` and the package data), :866 (corpus_ingest write locations), :867 (aa_run's current behaviour, including lane A and B fixes), :868 (remint `--spend`), and :869 (TOOL-13 hash, the opening log, the new refusals). The `cd databasise && uv run python -m <module>` command in :836 was left as it was, because it runs inside the `databasise` project. C-WR-05 is about CODEBASE-MAP.md. |

No fix contradicts D-01..D-24. B-WR-03 keeps D-13's keying and adds no gate refusal class. B-WR-04 applies D-13's cache-bypass refusal earlier and leaves its text unchanged. B-WR-06 and B-WR-07 follow D-03: named classes that print one line and exit 1.

_Fixer: Claude (gsd-code-fixer), lane B_
