---
phase: 15-offline-tooling-packaging
plan: 10
subsystem: eval
tags: [aa-run, corpus-ingest, remint, calibration, eval-store, cli, TOOL-11]
requires: [15-02]
provides:
  - "aa_run --spend refuses an empty eval index by name (EmptyEvalIndexError) before any embedding or chat call: calibrate_family takes index_probe, main passes a read-only load_committed probe over the arm's evidence namespace"
  - "score_gold_passage maps LightRAG chunk evidence through full_doc_id; a record with neither key raises GoldPassageMappingError"
  - "corpus_ingest and aa_run run cli.check_named_arm (_ARM_WIRING_NAMES) before any client is built"
  - "aa_run: --n-resamples is cli.positive_int, one asyncio.run for all families, named ValueError subclasses mapped to exit 1 through cli.refuse"
  - "remint is estimate-only without --spend (reads snapshot, judge prompt, bundle root; prints 1 chat call and mode: estimate-only); _REPO_EVAL_DIR renamed _PACKAGE_DIR"
affects: [databasise/eval/aa_run.py, databasise/eval/corpus_ingest.py, databasise/eval/remint.py, databasise/eval/calibration.py]
key-files:
  created:
    - databasise/tests/eval/test_eval_store_boundary.py
  modified:
    - databasise/eval/aa_run.py
    - databasise/eval/corpus_ingest.py
    - databasise/eval/remint.py
    - databasise/eval/calibration.py
    - databasise/tests/eval/test_aa_run.py
    - databasise/tests/eval/test_corpus_ingest.py
    - databasise/tests/eval/test_remint.py
key-decisions:
  - "No --arm means the engine's default (naive) arm, so the index probe reads the LightRAG 'chunks' namespace (CHUNKS_NAMESPACE) for both lightrag and no arm; hipporag reads 'hipporag-chunks'"
  - "_refusals() in aa_run is one tuple (cli.offline_refusals plus the module's named classes, ArmSelectorMismatchError included) used for both the load/estimate stage and the spend stage; StaleNullError stays unmapped"
  - "The spend stage of aa_run and corpus_ingest is one try block, so the arm check, env load, client build and engine construction all end in cli.refuse"
requirements-completed: [TOOL-11]
status: complete
commits: 3
plan_head_before: 7e1282926a8203845551a95b253738a175ed56ab
plan_head_after: 9d96aff4ae314671b16eed38faf547b5134b0e0b
actuals:
  tokens: 12700
  tasks: 3
  commits: 3
---

# Phase 15 Plan 10: Eval CLIs stay in the eval store, refuse an empty index and follow the shared contract Summary

`aa_run --spend` now refuses an empty eval index by name before it spends, scores LightRAG evidence instead of raising `KeyError`, and `remint` spends nothing without `--spend`.

## What changed

- **Task 1 (e6781f1, tracer).** `EmptyEvalIndexError(RuntimeError)`; `calibrate_family(..., index_probe=None)` runs the probe once before the first pass; `main` passes `_eval_index_probe(args.arm)` (a `functools.partial` over `_assert_eval_index_populated`, which calls `load_committed(<eval root at call time>/eval-corpus-ingest/<namespace>)` and refuses on None or zero entries). The probe is never called in `main` (Pitfall 2), so protected LRAG-15's patched `calibrate_family` is still called once.
- **Task 2 (ebbb6ae).** `score_gold_passage` reads `document_id` or `full_doc_id` (`GoldPassageMappingError` otherwise); the empty-gold error is `EmptyGoldDocumentIdsError`. `_EVAL_INGEST_STORE_ROOT` comment states where each arm writes. `_ARM_WIRING_NAMES = {"lightrag": "naive", "hipporag": "hipporag"}` and `cli.check_named_arm` before `_load_env_file` in both mains; `_ARM_SELECTORS` and `_ARM_CHOICES` are untouched.
- **Task 3 (9d96aff).** `aa_run`: `--n-resamples` uses `cli.positive_int`; `NoMintedBundleError`, `MissingTargetFamilyCoverageError`, `QuestionNotInBundleError`; one `asyncio.run` over `_calibrate_all`; every refusal through `cli.refuse`. `calibration`: `UnpairedScoresError`, `EmptyPairedDifferencesError`, `UnknownBatchWidthTierError` (messages unchanged). `corpus_ingest`: refusals through `cli.refuse`, `load_snapshot` now inside the refusal try. `remint`: inputs read first, prints `1 chat call` and `mode: estimate-only`, returns 0 without `--spend`; `_PACKAGE_DIR`; docstring carries the exit table and the source-checkout note.

## Row test node ids and fail-first evidence (TOOL-11)

Intended ledger `test_ref`: `databasise/tests/eval/test_eval_store_boundary.py` (file). Fail-first route: `record-fail --at 7e12829` (the commit before this plan's first code commit e6781f1). The file imports only names that exist at the base and resolves new names with `getattr`; no `v1/.venv` is needed.

Nodes, with the pre-fix result (source files temporarily restored to 7e12829, test files as committed; source restored afterwards, never committed):
- `test_an_empty_hipporag_eval_index_is_refused_before_any_spend`: `AssertionError: exit code 'raised AssertionError', 1 engine queries, 1 embedding calls` (one embedding call was paid on the empty index).
- `test_a_populated_hipporag_eval_index_is_not_refused`: `AssertionError: aa_run has no _eval_index_probe`.
- `test_lightrag_chunk_evidence_scores_by_full_doc_id`: `AssertionError: assert KeyError('document_id') == 0.5`.
- `test_evidence_with_no_document_key_is_a_named_refusal`: `AssertionError: assert 'KeyError' == 'GoldPassageMappingError'`.
- `test_aa_run_refuses_a_selector_that_resolves_to_another_arm_before_clients`: `AssertionError` (`'ArmSelectorMismatchError' in err` false; the run went on to build clients).
- `test_lightrag_eval_ingest_uses_a_working_dir_under_the_eval_root` and `test_aa_run_forwards_the_arm_selector`: pass at the base (already met by 7be6968 and 6ff345c); they pin the behaviour.

Non-row nodes in the requirement-named files (all fail by AssertionError at 7e12829 unless noted):
- `test_corpus_ingest.py::test_a_selector_that_resolves_to_another_arm_is_refused_before_clients`: `assert 0 == 1`-style (returned 0, no refusal).
- `test_aa_run.py::test_n_resamples_zero_exits_two_before_any_client` (`isinstance(0, SystemExit)` false), `::test_two_families_run_inside_one_event_loop` (`asyncio.run was called 2 times`), `::test_a_bare_value_error_is_not_mapped_to_exit_1` (returned 1, not a propagated ValueError). `::test_both_eval_mains_print_the_shared_estimate_only_line` passes at the base and pins the D-04 line.
- `test_remint.py::test_remint_without_spend_is_estimate_only` (`['env', 'clients', 'resolve', 'mint'] == []`), `::test_the_bundle_root_still_resolves_to_the_package_bundles` (`getattr(remint, '_PACKAGE_DIR', None)` is None). `test_main_with_no_live_credentials_exits_1_and_never_mints` now passes `--spend`, patches `remint.DEFAULT_V1_ENV_PARITY` to a never-created temp path and asserts that name in stderr.

At 7e12829 the four files (row file, test_corpus_ingest, test_aa_run, test_remint) gave 11 failed, 28 passed.

## Test results

- Task 1 set (`test_eval_store_boundary.py`, `test_aa_run.py`, protected `test_lightrag_eval_store.py`): 24 passed.
- Task 2 set (`databasise/tests/eval`, protected `test_lightrag_working_dir.py`): 82 passed.
- Task 3 set / plan verification (`databasise/tests/eval`, `databasise/tests/parity/test_cli_builder_refusals.py`, `databasise/tests/seam/test_lightrag_working_dir.py`): 95 passed.
- Full `pytest -q databasise` at 9d96aff: exit 0.
- Protected LRAG-15 (`test_lightrag_eval_store.py`) and `test_lightrag_working_dir.py` green with no edit. The offline gate script (`check_offline_suite.py`, both styles) was not run by this plan.
- ruff `--select F,E9` clean on the touched files.

## Deviations from Plan

- Two nodes beyond the plan were added to the row file: `test_a_populated_hipporag_eval_index_is_not_refused` (the probe passes on a populated namespace) and `test_aa_run_refuses_a_selector_that_resolves_to_another_arm_before_clients` (the aa_run side of D-10).
- `corpus_ingest` and `remint` now catch `cli.offline_refusals` around `load_snapshot`, which was previously outside any try in `corpus_ingest`. Removed the now-unused `BUILDER_REFUSALS` imports from `corpus_ingest`, `remint` and `aa_run`, and the unused `SeamRefusalError` import from `aa_run` (both live in `cli.offline_refusals`).

## Known Stubs

None.

## Self-Check: PASSED

Files exist (`databasise/tests/eval/test_eval_store_boundary.py`, `databasise/eval/aa_run.py`, `databasise/eval/remint.py`); commits e6781f1, ebbb6ae, 9d96aff are ancestors of HEAD.
