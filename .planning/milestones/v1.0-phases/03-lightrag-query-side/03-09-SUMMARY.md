---
phase: 03-lightrag-query-side
plan: 09
subsystem: rag-engine
tags: [lightrag, parity, evidence, contract-5, declared-deviations, storage-audit, validation]

# Dependency graph
requires:
  - phase: 03-02
    provides: "v1 parity environment, hash-verified corpus snapshot (20 docs, 2 queries), verified import of v1's built index into the v2 namespace layout"
  - phase: 03-07
    provides: "databasise/parity/run_comparison.py — the pre-flight index-identity gate, D-12 keyword pinning, the N-run keywords variance band, the deterministic retrieval-level diff"
  - phase: 03-08
    provides: "databasise/parity/storage_audit.py — the per-node storage-ownership audit; Falsifier 2 evidence regenerated against the real ported node set"
provides:
  - "databasise/evidence/parity_results/ — committed real output from running the five-arm comparison and the five-arm storage audit on this machine: every arm reports status=inconclusive/a named MissingParityEnvError, never a fabricated verdict"
  - "databasise/evidence/parity_report.py — renders PARITY-EVIDENCE.md and DECLARED-DEVIATIONS.md from the committed results, plus a --check-results provenance validator"
  - "databasise/evidence/PARITY-EVIDENCE.md — the committed parity evidence document, stating plainly that no comparison has actually run on this machine and citing 03-GATE-AMENDMENT.md wherever the absent A/A floor bears on reading a number"
  - "databasise/evidence/DECLARED-DEVIATIONS.md — the CONTRACT §5 record; currently a stated zero with an explicit 'nothing measured yet' qualifier, and a renderer that refuses any future entry carrying an empty or generic cause"
  - "A Rule 2 fix to databasise/parity/run_comparison.py: the bypass arm's chunk comparison now records 'no retrieval to compare' via a new retrieval_note field, distinct from a computed zero symmetric difference"
  - ".planning/phases/03-lightrag-query-side/03-VALIDATION.md — filled in from all 28 tasks across plans 03-01 through 03-09, status: validated, nyquist_compliant: true"
affects: []

# Actuals (#2632)
actuals:
  tokens: 24573
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "A committed evidence document that states an inconclusive/refused precondition outcome as faithfully and completely as a passing one — never a fabricated verdict, always re-runnable once the precondition clears (databasise/evidence/parity_report.py following falsifier2.py's own committed/re-runnable precedent)"
    - "A declared-deviation renderer that refuses to render at all (raises before writing anything) when any entry's cause is empty or matches a small denylist of generic/blanket phrases — the whole document fails rather than emitting one unreasoned row, so a bad cause can never slip into a committed document silently"
    - "A 'no comparison to make' outcome (bypass arm) is a distinct sentinel field (retrieval_note), never a computed empty-vs-empty diff — an empty diff reads as perfect agreement, which is a different (and false) claim"

key-files:
  created:
    - databasise/evidence/parity_results/naive-comparison.json
    - databasise/evidence/parity_results/naive-storage-audit.json
    - databasise/evidence/parity_results/bypass-comparison.json
    - databasise/evidence/parity_results/bypass-storage-audit.json
    - databasise/evidence/parity_results/hybrid-comparison.json
    - databasise/evidence/parity_results/hybrid-storage-audit.json
    - databasise/evidence/parity_results/local-comparison.json
    - databasise/evidence/parity_results/local-storage-audit.json
    - databasise/evidence/parity_results/global-comparison.json
    - databasise/evidence/parity_results/global-storage-audit.json
    - databasise/evidence/parity_report.py
    - databasise/evidence/PARITY-EVIDENCE.md
    - databasise/evidence/DECLARED-DEVIATIONS.md
    - databasise/tests/parity/test_parity_evidence.py
  modified:
    - databasise/parity/run_comparison.py
    - databasise/tests/parity/test_retrieval_parity.py
    - .planning/phases/03-lightrag-query-side/03-VALIDATION.md

key-decisions:
  - "N=5 for the keywords variance band (databasise.parity.run_comparison._DEFAULT_KEYWORD_VARIANCE_RUNS, already coded by plan 03-07): large enough to show repeats in the per-keyword frequency table for a typical HotpotQA question (2-4 keywords per level), small enough that 5 extra live keywords calls per query stays well within a rung-2 comparison's affordability per RIG §F3, and compute_keyword_variance_band itself accepts any N ≥ 2 so raising N on a future real run needs no code change — recorded in PARITY-EVIDENCE.md's own band table."
  - "requirements-completed lists only MODAL-01, not MACH-02/MACH-03, even though this plan's frontmatter requirements field names all three. MACH-02/MACH-03 were deferred a second time to Phase 6 by plan 03-03's own amendment (03-GATE-AMENDMENT.md) — REQUIREMENTS.md and ROADMAP.md already track them as Phase 6 items ('MACH-02 | Phase 6 | Pending'). This plan's only obligation toward them is citing the amendment wherever the absent floor bears on reading a number (done, in PARITY-EVIDENCE.md's 'What is not measured' section) — it does not build the eval bundle or run the A/A calibration, so marking them complete here would misrepresent still-open Phase 6 work as done."
  - "Storage-audit results are hand-authored JSON files (databasise/evidence/parity_results/{arm}-storage-audit.json), not machine-generated by storage_audit.py itself, because that CLI prints to stdout only and has no JSON output mode. Each file faithfully records the real captured command, exit code, and MissingParityEnvError message from actually running `uv run python -m databasise.parity.storage_audit --arm <arm>` this session — never fabricated numbers."
  - "Fixed a Rule 2 gap in run_comparison.py (03-07's file, outside this plan's <files_modified>, but directly required by this plan's own Task 1 acceptance criterion): the bypass arm has no chunk-source node, so diff_ranked_ids([], []) previously computed sym_diff=() / agreement=1.0 for its chunk_diff — indistinguishable from a real, measured zero difference. Added _no_retrieval_to_compare_note() and a new retrieval_note field on ComparisonRecord so bypass records the distinction explicitly, with a regression-guard test on the fact it depends on (resolve_arm('bypass') has no 'rerank' node)."

patterns-established:
  - "check_results()/ProvenanceViolation mirrors check_import_boundary.py's own Violation/print/exit convention, and is the single shared implementation between Task 1's own <verify> command and Task 2's rendering of what a 'complete' committed result file looks like — they can never silently disagree."

requirements-completed: [MODAL-01]

coverage:
  - id: D1
    description: "The five-arm parity comparison and the five-arm storage audit were run for real on this machine; every result faithfully records the harness's own inconclusive/refusal outcome (never a fabricated pass/fail), committed under databasise/evidence/parity_results/"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "cd databasise && uv run python -m databasise.evidence.parity_report --check-results (exit 0, 'provenance check: clean (5 arms)')"
        status: pass
      - kind: other
        ref: "cd databasise && uv run python -m databasise.parity.run_comparison --arm <naive|bypass|hybrid|local|global> — exit 2 for all five, status=inconclusive on both queries (real run, this session)"
        status: pass
    human_judgment: false
  - id: D2
    description: "The bypass arm's 'no retrieval to compare' state is recorded distinctly from a computed zero symmetric difference (a Rule 2 fix to run_comparison.py)"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_retrieval_parity.py::test_an_arm_with_no_chunk_source_node_gets_a_distinct_note_not_a_computed_diff and ::test_the_bypass_arms_resolved_node_set_actually_has_no_chunk_source_node"
        status: pass
    human_judgment: false
  - id: D3
    description: "parity_report.py renders PARITY-EVIDENCE.md and DECLARED-DEVIATIONS.md from the committed results — both documents are byte-identical across two renders, PARITY-EVIDENCE.md cites 03-GATE-AMENDMENT.md, states the keywords band's N in the band table, and renders the storage-audit table with matched/no-touch/over-declared counted separately"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "cd databasise && uv run pytest -q tests/parity/test_parity_evidence.py -x (25 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "render_deviations_markdown refuses to render any entry whose cause is empty or a generic/blanket phrase, proven against 7 generic-cause cases plus the empty-cause case, and proven not to silently drop one bad row among good ones"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_parity_evidence.py::test_a_deviation_with_an_empty_cause_makes_the_render_fail, ::test_a_deviation_with_a_generic_blanket_cause_makes_the_render_fail[...], ::test_one_bad_cause_among_several_good_ones_still_fails_the_whole_render"
        status: pass
    human_judgment: false
  - id: D5
    description: "03-VALIDATION.md is filled in from all 28 tasks across plans 03-01 through 03-09, its sign-off checklist passes, and its frontmatter is set to status: validated, nyquist_compliant: true"
    requirement: "MODAL-01"
    verification:
      - kind: other
        ref: ".planning/phases/03-lightrag-query-side/03-VALIDATION.md — Per-Task Verification Map has one row per task, sign-off checklist all checked"
        status: pass
    human_judgment: false
  - id: D6
    description: "criterion 6's human spot-check of three query pairs, and the owner's own read of PARITY-EVIDENCE.md, giving a verdict on the (currently inconclusive) evidence"
    requirement: "MODAL-01"
    verification: []
    human_judgment: true
    rationale: "This is the environment-fact gap named in this plan's own launch instructions: v1/.venv, v1/.parity_working_dir, v1/.parity_v2_store, and v1/.env.parity are all absent on this machine (gitignored, worktree-local build artifacts from plan 03-02's own separate execution session — the same gap 03-04 through 03-08-SUMMARY.md all independently document). No live comparison could actually run this session, so there is no answer pair for a human to compare yet. Separately, the plan's own instruction to pick three query pairs cannot be satisfied literally even once the environment is rebuilt: the committed corpus snapshot carries exactly 2 queries (confirmed this session via load_snapshot()), not 3 — recorded as a discrepancy in 03-VALIDATION.md's Manual-Only Verifications table, not silently worked around. The owner must rebuild the v1 environment, re-run the five comparisons (commands below), and then perform the spot-check and read PARITY-EVIDENCE.md — closeable via /gsd-verify-work once done."
  - id: D7
    description: "The real live comparison and storage audit against the actual imported v1 index and live model endpoints (the clean-pass path, as opposed to the refusal path proven in D1)"
    requirement: "MODAL-01"
    verification: []
    human_judgment: true
    rationale: "Same environment gap as D6. The refusal/precondition-gate code path is proven correct and exercised for real in this session (D1); the clean-pass path requires the owner to rebuild v1/.venv and re-run plan 03-02's real ingest (v1/README-PARITY.md), or copy an existing build's artifacts into this worktree, then re-run the exact commands named in Next Phase Readiness below."

duration: ~50min
completed: 2026-09-01
status: complete
---

# Phase 3 Plan 09: LightRAG Query Side — Parity Evidence Summary

**Ran the five-arm parity comparison and storage audit for real on a machine that lacks the v1 build artifacts, and committed exactly what the harness produced — a faithful, re-runnable `inconclusive` record across all five arms, never a fabricated verdict — plus the rendering, refusal, and validation-map infrastructure needed to turn that into a real verdict the moment the owner rebuilds the environment.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 3/3 completed
- **Files modified:** 17 (14 created, 3 modified)

## Accomplishments

- Ran `databasise.parity.run_comparison` and `databasise.parity.storage_audit` for real against all five arms (`naive`, `hybrid`, `local`, `global`, `bypass`). Both preconditions (an imported v2 store, `v1/.env.parity`) are genuinely absent on this machine — every comparison run reports `status=inconclusive`/exit 2 before either arm is touched (the index-identity gate refuses first), and every storage-audit run raises a named `MissingParityEnvError`/exit 1 before the scheduler runs a single node. Committed the real captured output as ten JSON files under `databasise/evidence/parity_results/`.
- Fixed a Rule 2 gap in `run_comparison.py` (03-07's file): the `bypass` arm's chunk-diff previously computed as an empty-vs-empty "perfect agreement" rather than "nothing to compare" — added `retrieval_note`/`_no_retrieval_to_compare_note()` with a regression-guard test, so this plan's own must-have prohibition ("record it explicitly as having nothing to compare... which would read as perfect agreement") holds once a real run lands.
- Built `databasise/evidence/parity_report.py` following `falsifier2.py`'s committed/re-runnable/human-readable pattern: `--check-results` validates every committed result file's provenance fields and refuses a comparison number alongside an inconclusive status; `render_markdown()`/`render_deviations_markdown()` are pure functions of the committed inputs, proven byte-identical across two calls and against the files on disk.
- `PARITY-EVIDENCE.md` states plainly, before any number, that no comparison has actually run on this machine — the "What was compared" section names exactly which artifacts are absent, the "Verdict" section states no pass/fail is recorded, and "What is not measured" cites `03-GATE-AMENDMENT.md`'s second MACH-02/MACH-03 deferral wherever the absent A/A floor bears on reading a number. The storage-audit table renders `matched`/`no-touch`/`over-declared` counted separately per arm (all zero today, with the reason stated).
- `DECLARED-DEVIATIONS.md` records a stated zero with an explicit "nothing measured yet" qualifier — and its renderer raises `UnreasonedDeviationError` before writing anything if any future entry's cause is empty or a generic/blanket phrase (`"expected variance"`, `"noise"`, `"n/a"`, ...), proven against 7 generic-cause cases and a mixed-good/bad case.
- Filled in `.planning/phases/03-lightrag-query-side/03-VALIDATION.md`: one row per task across all 28 tasks in plans 03-01 through 03-09, each carrying its real `<verify><automated>` command, re-verified green this session where the environment allows (415 passed, 4 skipped full suite; ~2.1s quick, ~34.8s full, both measured). Sign-off checklist passes; `status: validated`, `nyquist_compliant: true`.

## Task Commits

1. **Task 1: Run the comparison across all five arms and commit the results** — `8cb2802` (feat)
2. **Task 2: Render the parity evidence and the declared-deviation record** — `6e420b1` (test)
3. **Task 3: Fill in the validation map and complete the phase's human verification** — `98ed524` (docs)

## Files Created/Modified

- `databasise/evidence/parity_results/{naive,bypass,hybrid,local,global}-comparison.json` — real, committed `run_comparison.py` output (all `status=inconclusive`)
- `databasise/evidence/parity_results/{naive,bypass,hybrid,local,global}-storage-audit.json` — hand-authored records of the real, captured `storage_audit.py` CLI runs (all `MissingParityEnvError`, exit 1)
- `databasise/evidence/parity_report.py` — the renderer, `check_results()`, `render_deviations_markdown()`, `main()`
- `databasise/evidence/PARITY-EVIDENCE.md` — the committed parity evidence document
- `databasise/evidence/DECLARED-DEVIATIONS.md` — the CONTRACT §5 record (stated zero, qualified)
- `databasise/tests/parity/test_parity_evidence.py` — 25 tests covering the provenance validator, the deviation refusal, and render stability/content
- `databasise/parity/run_comparison.py` — added `retrieval_note`/`_no_retrieval_to_compare_note()` (Rule 2 fix)
- `databasise/tests/parity/test_retrieval_parity.py` — 3 new tests for the fix
- `.planning/phases/03-lightrag-query-side/03-VALIDATION.md` — filled in, `status: validated`

## Decisions Made

See `key-decisions` in frontmatter for the full list. Highlights: N=5 for the keywords variance band (reasoning above); `requirements-completed` deliberately omits MACH-02/MACH-03 (deferred to Phase 6, this plan only cites the amendment); storage-audit results are hand-authored JSON since `storage_audit.py` has no JSON output mode, faithfully transcribing the real captured CLI run.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] `bypass` arm's chunk comparison read as perfect agreement instead of "nothing to compare"**
- **Found during:** Task 1, designing the committed result shape for the `bypass` arm per the plan's own stated prohibition
- **Issue:** `run_comparison.py`'s `compare_arm_on_query` computed `chunk_diff = diff_ranked_ids(decomposed_chunk_ids, v1_result.chunk_ids)` unconditionally. For `bypass` (a single `generate` node, no retrieval at all — confirmed via `resolve_arm("bypass")`), both lists are always empty, so `diff_ranked_ids([], [])` returns `symmetric_difference=(), ranking_agreement=1.0` — indistinguishable from a genuinely measured zero difference. The plan's own Task 1 acceptance criteria state this explicitly: "Record it explicitly as having nothing to compare rather than recording an empty diff, which would read as perfect agreement."
- **Fix:** Added `_no_retrieval_to_compare_note(arm_name, has_chunk_node)` — a small pure function — and a new `retrieval_note` field on `ComparisonRecord`. `chunk_diff` is now `None` (not a computed empty diff) whenever the resolved arm has no `rerank` node; `retrieval_note` carries the stated reason instead. The human-summary renderer and `PARITY-EVIDENCE.md`'s per-arm table both surface the note.
- **Files modified:** `databasise/parity/run_comparison.py`, `databasise/tests/parity/test_retrieval_parity.py`
- **Verification:** 3 new tests, including a regression guard on the fact the fix depends on (`resolve_arm("bypass")` has no `"rerank"` node); full `tests/parity/` suite still green (61 passed, 4 skipped) after the change.
- **Committed in:** `8cb2802` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 2 missing-critical-functionality)
**Impact on plan:** Necessary for Task 1's own stated acceptance criterion (bypass records "no retrieval to compare" distinctly) to hold true once a real run lands — the current committed inconclusive results don't exercise this code path (they never reach it), but the harness must behave correctly the moment the precondition clears. No scope creep — the fix touches exactly the one field this plan's own criterion names.

## Issues Encountered

- **The v1 parity build artifacts are absent on this machine** (`v1/.venv`, `v1/.parity_working_dir`, `v1/.parity_v2_store`, `v1/.env.parity`) — the exact environment fact stated in this plan's own launch instructions, and the same gap 03-04-SUMMARY.md through 03-08-SUMMARY.md all independently document. Every comparison run this session hit the index-identity precondition gate before touching either arm (real, exit 2, `status=inconclusive` on both queries for all five arms); every storage-audit run raised a named `MissingParityEnvError` before the scheduler ran a single node (real, exit 1). Both are the harness's own designed refusal behavior, not a code defect — confirmed by running the actual CLIs, not by inspection.
- **The plan's human-check instruction ("Pick three queries from the snapshot query set") cannot be satisfied literally**: the committed corpus snapshot carries exactly 2 queries (`q1`, `q2` — confirmed this session via `load_snapshot()`), not 3. Recorded as a discrepancy in `03-VALIDATION.md`'s Manual-Only Verifications table rather than silently substituting 2 for 3 or fabricating a third. A real third pair is available by running a second arm over one of the two existing queries (still a genuine pair), or the owner can extend the corpus snapshot — neither attempted here, both out of this plan's scope.
- `storage_audit.py` has no JSON output mode (stdout-only, matching `check_import_boundary.py`'s reporting convention). Since Task 1 requires "one storage-audit output per arm" committed as machine-readable JSON, the five `{arm}-storage-audit.json` files are hand-authored, transcribing the real captured CLI stdout/stderr/exit-code from actually running the command — not generated by a new script, since `storage_audit.py` itself is outside this plan's `<files_modified>` list and adding a JSON mode to it was not required by this plan's own acceptance criteria.

## User Setup Required

**External environment rebuild required to close D6/D7 above.** See `v1/README-PARITY.md` for the exact steps: `cd v1 && uv venv --python 3.12 && uv sync && uv sync --extra api`, populate `v1/.env.parity` per its documented table, and either re-run the real OpenRouter ingest (`v1/scripts/run_parity_ingest.py`, D-01: costly, run at most once) or copy an existing build's `v1/.parity_working_dir/` from a prior session, then run `databasise.parity.import_index.import_v1_index()` to populate `v1/.parity_v2_store/`.

## Next Phase Readiness

- Once the environment above is rebuilt, re-run the exact five commands this plan ran (`cd databasise && uv run python -m databasise.parity.run_comparison --arm <naive|bypass|hybrid|local|global>` and `uv run python -m databasise.parity.storage_audit --arm <same>`), overwrite the corresponding files under `databasise/evidence/parity_results/`, then `cd databasise && uv run python -m databasise.evidence.parity_report` to re-render `PARITY-EVIDENCE.md` and `DECLARED-DEVIATIONS.md` against the real completed data — no code change needed anywhere in this pipeline for that to happen.
- Once real data lands, `render_deviations_markdown`'s refusal behavior means any completed excursion with an unreasoned cause will hard-fail the render rather than silently pass — whoever performs that re-render will need to name a real cause for each excursion the retrieval-level diff surfaces (the tolerance starts at zero per this plan's own flagged assumption).
- Criterion 6's human spot-check and the owner's read of `PARITY-EVIDENCE.md` (D6) and the clean-pass live comparison (D7) are the only items this plan could not close in this environment — both are environment gaps, not code gaps, and are closeable via `/gsd-verify-work` once the owner performs the rebuild above.
- `.planning/phases/03-lightrag-query-side/03-VALIDATION.md` is now `status: validated`, `nyquist_compliant: true` — this phase's automated-verification contract is fully satisfied; only the live-environment items above remain open.

---
*Phase: 03-lightrag-query-side*
*Completed: 2026-09-01*

## Self-Check: PASSED

All created/modified files confirmed present on disk; all three task commit hashes (`8cb2802`, `6e420b1`, `98ed524`) confirmed in `git log --oneline` on this worktree's own branch.
