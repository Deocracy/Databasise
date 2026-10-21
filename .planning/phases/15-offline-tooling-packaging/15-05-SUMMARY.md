---
phase: 15-offline-tooling-packaging
plan: 05
subsystem: testing
tags: [eval-bundle, content-hash, sealed-split, versioning]
requires: []
provides:
  - bundle content hash covering question text and gold document ids
  - recomputing dedup that keeps the committed bundle@v1 matching unchanged input
  - sealed_opened flag and sealed_open log on both source and new version
  - split_counts recorded in newly minted bundle.json
affects: [calibration, aa_run, remint]
status: complete
actuals:
  tokens: 3900
  tasks: 2
  commits: 2
plan_head_before: 0aff830
plan_head_after: c468d2d3fef75ba212d17d33f554c100538e5c4e
tech-stack:
  added: []
  patterns: [dedup recomputes from stored content, derived flags come from the usage log, not the serialised file]
key-files:
  created: []
  modified:
    - databasise/eval/bundle.py
    - databasise/evidence/EVAL-BUNDLE-V1.md
    - databasise/tests/eval/test_bundle_versioning.py
key-decisions:
  - "Dedup recomputes each stored version's hash from its own content (_recomputed_content_hash), never the stored content_hash field"
  - "sealed_opened is derived from usage.jsonl on load and never serialised, so no committed bytes change"
requirements-completed: [TOOL-13]
---

# Phase 15 Plan 05: Bundle versioning (TOOL-13) Summary

Eval bundle identity now covers question text and gold document ids, an opened sealed split is logged on both versions and surfaced as `sealed_opened`, and new bundles record `split_counts`; bundle@v1 bytes are untouched and still dedup.

## Commits

- 59a400b feat(15-05): bundle content hash covers question text and gold ids; dedup recomputes
- c468d2d feat(15-05): an opened sealed split is logged on both versions and never returned as unopened; split counts recorded

## TOOL-13 row nodes and fail-first evidence

Intended ledger test_ref file: `databasise/tests/eval/test_bundle_versioning.py`. Fail-first was run on the unchanged source (HEAD 0aff830 plus the new tests only).

| Node id | Fail-first |
|---|---|
| `databasise/tests/eval/test_bundle_versioning.py::test_editing_one_question_text_mints_a_new_version_and_hash` | `AssertionError: an edited question text reused the old bundle version` (`'bundle@v1' != 'bundle@v1'`) |
| `databasise/tests/eval/test_bundle_versioning.py::test_editing_one_gold_document_id_mints_a_new_version_and_hash` | `AssertionError: an edited gold document id reused the old bundle version` |
| `databasise/tests/eval/test_bundle_versioning.py::test_the_committed_v1_still_dedups_for_the_unchanged_fixture` | passes at the base by design (guards the recomputing dedup) |
| `databasise/tests/eval/test_bundle_versioning.py::test_open_sealed_logs_on_the_source_version_too` | `AssertionError: source version usage kinds: []` |
| `databasise/tests/eval/test_bundle_versioning.py::test_reminting_after_open_sealed_returns_a_version_flagged_opened` | `AssertionError: re-mint returned bundle@v1 without an opened flag` |
| `databasise/tests/eval/test_bundle_versioning.py::test_a_new_bundle_json_records_split_counts` | `AssertionError: assert None == {'dev': 17, 'holdout': 9, 'sealed': 4}` |
| `databasise/tests/eval/test_bundle_versioning.py::test_the_v1_evidence_doc_states_the_realised_split_counts` | `AssertionError: no paragraph outside the findings table mentions v1's content_hash scheme` |

All new tests import only names present at the phase base and use `getattr` for the new `sealed_opened`; the committed-v1 test copies `evidence/eval-bundles` into `tmp_path`.

## Test results

- `databasise/tests/eval databasise/tests/evidence`: 148 passed.
- Protected `databasise/tests/eval/test_lightrag_eval_store.py` (LRAG-15): passed, untouched.
- `git status --short databasise/evidence/eval-bundles`: empty (bundle@v1 unchanged).
- ruff on `bundle.py`: clean. Two ruff findings in the test file (I001 import order, RUF059 at the old line 296) predate this plan and were left alone.

## Deviations from Plan

None - plan executed exactly as written. The full offline gate (`check_offline_suite.py`) was not run by this plan; it is the orchestrator's wave step.

## Known Stubs

None.

## Self-Check: PASSED

- 59a400b and c468d2d are ancestors of HEAD; the three modified files exist.
