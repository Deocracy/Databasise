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
