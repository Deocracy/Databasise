---
phase: 15-offline-tooling-packaging
plan: 08
subsystem: evidence
tags: [parity-report, evidence, TOOL-14]
requires: []
provides:
  - "evidence.parity_report renders run state, counts, verdicts and corpus size from parity_results per record"
  - "ParityRecordFormatError: one named refusal for malformed JSON or a findings entry missing a key, through one validator"
  - "every .planning path the parity evidence cites resolves under .planning/milestones/v1.0-phases/"
affects: [databasise/evidence/parity_report.py, databasise/evidence/DECLARED-DEVIATIONS.md, databasise/evidence/PARITY-EVIDENCE.md, databasise/evidence/FALSIFIER-5-EVIDENCE.md]
key-files:
  created:
    - databasise/tests/evidence/test_parity_report_render.py
  modified:
    - databasise/evidence/parity_report.py
    - databasise/evidence/DECLARED-DEVIATIONS.md
    - databasise/evidence/PARITY-EVIDENCE.md
    - databasise/evidence/FALSIFIER-5-EVIDENCE.md
    - databasise/tests/parity/test_parity_evidence.py
key-decisions:
  - "The validator runs inside load_human_findings(), so check_results, _collect_deviations and the spot-check renderer all share it (15-RESEARCH Open Question 7)"
  - "The verdict reads causes leniently (no stale/orphan refusal) because that refusal belongs to _collect_deviations, which main() runs first; render_markdown on a retargeted RESULTS_DIR with the real findings file stays usable in the existing tests"
  - "The '20 documents' count was dropped: parity_results carries no document count, and the plan's prohibition forbids stating a count not read from it"
requirements-completed: [TOOL-14]
status: complete
duration: 75min
completed: 2026-10-21
commits: 4
plan_head_before: 81e11c4d73b578d2200bed92d1e370cd8abd20eb
plan_head_after: 9e4125d29d1c602cfd6ce3b110d55a72797bf11d
actuals:
  tokens: 45000
  tasks: 3
  commits: 4
---

# Phase 15 Plan 08: parity_report renders only what it reads Summary

`evidence.parity_report` now computes every run state, count, verdict and corpus size from `parity_results` per record, refuses malformed inputs with `ParityRecordFormatError`, shows `recorded_by` for every cause (table and verdict), and cites only `.planning` paths that exist.

## What changed

- **Deviations record (Task 1, commit 0626da5).** `render_deviations_markdown(deviations, pending=None)` prints the zero-deviations heading only when both lists are empty; with only pending excursions it prints a "Named deviations" note pointing at the Outstanding table. `render_deviations_document` passes the pending list. The outstanding text now cites CONTRACT §5 line 308 (declared deviations are named explicitly, a cause records who recorded it) instead of "requires human reasoning".
- **Computed states (Task 2, commit 067c8d4).**
  - `mixed` has its own text in the zero-deviations note, "What was compared", the storage-audit section, "What is not measured", the spot-check guidance and the verdict (a per-arm state summary, no every-arm-refused sentence). Arm-level state comes from `_arm_state`.
  - The verdict is built per arm by `_arm_verdict_line`; naive and bypass are no longer hardcoded. `_arm_cause_sentence` counts excursions with a named cause and prints their `recorded_by` values; an AI-recorded cause is shown and not read as owner-verified. The opening sentence says "All five arms completed" only when no arm is degraded.
  - Corpus size is `_queries_phrase()` ("N queries") from the result files; the unsourced "20 documents" is gone. The known-design-deviation heading is "(measured)" or "(pending measurement)" by whether graph-arm records exist, and the entity/relation sentence says "every completed arm/query record" or "k of n (list)". The spot-check section lists the queries named in the results.
  - Spot-check guidance checks all five arms and names the arms that can host the read. Spot-checks are keyed by `(query_id, arm)`; an exact duplicate raises `DuplicateSpotCheckError` (a `ParityRecordFormatError`).
  - `ParityRecordFormatError(ValueError)`, `_load_json` and `_validate_human_findings` (required keys for `declared_causes` and `answer_spotchecks`). `main` turns the error into `databasise.cli.refuse` (one stderr line, exit 1). Named-deviation and pending cells go through `_escape_cell`.
  - Both documents regenerated; `test_parity_evidence.py` pins updated for two changed phrases ("Known design deviation (measured)", "each one needs a CONTRACT §5 named cause").
- **Paths (Task 3, commit f73545a).** The three `_GATE_*`/`_VALIDATION_REF` constants and the `03-UAT.md` literals, and `FALSIFIER-5-EVIDENCE.md` lines 15, 16 and 92, point at `.planning/milestones/v1.0-phases/...`. Both rendered documents regenerated. `evidence/COVERAGE.md:69` left alone, as the plan says.
- **Commit 9e4125d** makes the `main` refusal test capture its exception, so it fails by `AssertionError` on the pre-change module.

## Row test node ids and fail-first evidence

Intended ledger `test_ref`: `databasise/tests/evidence/test_parity_report_render.py` (whole file, 13 nodes). Fail-first route: `record-fail --at 81e11c4` (the commit before this plan's first code commit `0626da5`); the file imports only `databasise.evidence.parity_report`, which exists there, and resolves new names through `type(caught).__name__` strings.

Task 1 nodes, run against the unchanged module:
- `test_all_uncaused_excursions_never_render_zero_declared_deviations`: `AssertionError: assert 'Zero declared deviations' not in '# Declared ...'` (the text printed "## Zero declared deviations ... a completed comparison that found no excursion" beside the outstanding table).
- `test_an_ai_recorded_cause_shows_recorded_by`: passes at the base (the table already had the column; it pins the half that must not regress).

Task 2 nodes and Task 3 node, run with the module as of `0626da5` (source reverted in the working tree, then restored; never committed):
- `test_the_mixed_state_has_its_own_text`: `assert 'Every one of the five arms' not in '# Parity Ev...'`
- `test_a_degraded_naive_arm_never_reads_all_five_completed`: `AssertionError: assert 'All five arms completed' not in 'All five ar...y of them.'`
- `test_one_query_with_empty_ids_never_claims_non_empty_on_every_query`: `AssertionError: assert 'non-empty on every query' not in '# Declared ...'`
- `test_the_corpus_size_comes_from_the_results`: `assert '3 queries' in "# Parity Evidence ..."`
- `test_two_spot_checks_for_one_query_with_different_arms_both_appear`: `assert 'NOTE-HYBRID' in '## Human spot-check of answer substance ...'`
- `test_an_exact_duplicate_spot_check_is_refused_by_name`: `AssertionError: assert 'NoneType' == 'DuplicateSpotCheckError'`
- `test_malformed_json_and_a_missing_field_raise_the_named_refusal`: `AssertionError: assert [('check_results/truncated', 'JSONDecodeError', ...), ...] == []` (six scenario rows wrong)
- `test_a_cause_with_a_pipe_and_a_newline_keeps_the_row_count`: `assert 'third' in "| naive | q1 | chunk_diff: ... | first | second"`
- `test_recorded_by_appears_in_the_verdict`: `assert 'claude-agent' in "## Verdict ..."`
- `test_main_check_results_refuses_a_malformed_file_with_one_line_and_exit_1`: `AssertionError: assert JSONDecodeError('Expecting value: line 1 column 13 (char 12)') is None`
- `test_every_planning_path_resolves` (module as of `067c8d4`): `AssertionError: assert ['DECLARED-DE...MENT.md', ...] == []` (11 distinct missing paths).

The whole file at the pre-Task-2 module: 11 failed, 2 passed at the time of the run (the `main` node then failed with `JSONDecodeError`; commit 9e4125d fixed that to an assertion).

## Tests

- `databasise/tests/evidence`, `databasise/tests/parity/test_parity_evidence.py`, `databasise/tests/test_removed_stores_absent.py`: 142 passed after Task 3.
- `databasise/.venv/bin/python -m databasise.evidence.parity_report --check-results`: exit 0 ("clean (5 arms)").
- Full package run `databasise/.venv/bin/python -m pytest -q databasise -p no:cacheprovider` (HEAD 9e4125d, background): 2668 passed, 4 deselected. It includes every protected test file.
- No protected test failed. The full offline gate (`check_offline_suite.py`, both invocation styles) was not run by this plan; the orchestrator owns it.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] more hardcoded claims than the nine bullets named**
- **Found during:** Task 2
- **Issue:** Besides the sites in the plan, the "naive/bypass" run description and the known-design-deviation sentence stated counts and outcomes ("two named tail-length excursions per query", "20 documents", "a grounded cause", "both corpus queries", the unconditional "none is recorded yet for this arm") that the committed results do not support (naive's chunk symmetric differences are 2 chunks on q1 and 4 on q2, not "two per query"; the cause for each is AI-recorded). The prohibition on stating a verdict or count not read from `parity_results` covers them.
- **Fix:** computed per record (`_arm_verdict_line`, `_arm_cause_summary`, `_queries_phrase`, `_spotcheck_gap`); the document count was removed.
- **Files modified:** `databasise/evidence/parity_report.py`, both rendered documents
- **Commit:** 067c8d4

**2. [Rule 1 - Bug] the pinned models clause assumed naive's first record was completed**
- **Issue:** `load_comparison("naive")[0]["resolved_model_identities"]` would `KeyError` in a mixed state.
- **Fix:** the first completed record across arms, with `.get`; arms that never ran `generate` are limited to arms with a completed record.
- **Commit:** 067c8d4

### Notes

- `render_deviations_markdown` gained an optional `pending=None` parameter; existing callers are unchanged.
- The Bash hook refused one heredoc append to the new test file (it misread a path); the node was added with the Edit tool.

## Known Stubs

None.

## Threat Flags

None. T-15-20 (recorded_by shown in table and verdict), T-15-21 (verdict and counts computed per record) and T-15-22 (`_escape_cell` on every named-deviation cell) are mitigated by tests.

## Self-Check: PASSED

- `databasise/tests/evidence/test_parity_report_render.py` exists; commits 0626da5, 067c8d4, f73545a and 9e4125d are ancestors of HEAD.
- `grep -n "class ParityRecordFormatError" databasise/evidence/parity_report.py` returns one line (71).
