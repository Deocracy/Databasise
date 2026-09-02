---
phase: 03-lightrag-query-side
plan: 10
subsystem: testing
tags: [parity-evidence, markdown-rendering, gap-closure, lightrag, contract-5, declared-deviations]

# Dependency graph
requires:
  - phase: 03-lightrag-query-side
    provides: "03-09's parity harness (databasise/parity/run_comparison.py, storage_audit.py) and the first completed five-arm live comparison run whose committed parity_results/*.json this plan renders"
provides:
  - "A human-authored cause-input mechanism (human_findings.json) so a completed retrieval-level excursion can be named and rendered rather than aborting the render (CONTRACT §5)"
  - "Every PARITY-EVIDENCE.md/DECLARED-DEVIATIONS.md prose section deriving its claims from committed run records via a new _run_state() helper, instead of a hardcoded pre-run narrative"
  - "A committed landing place (human_findings.json's answer_spotchecks) for the still-pending human answer-substance judgment, rendered per query and surviving re-render"
  - "A dated MODAL-01 annotation in REQUIREMENTS.md stating the measured outcome and the one outstanding condition"
affects: [phase-4-seam-work, phase-6-side-by-side-run]

# Actuals (#2632)
actuals:
  tokens: 22280
  tasks: 3
  commits: 4

tech-stack:
  added: []
  patterns:
    - "Run-state derivation (_run_state()) as the single source every prose-rendering function reads, instead of each function independently asserting what state the run is in"
    - "Human-authored findings as a committed JSON input (human_findings.json) read by the renderer, separate from machine-written parity_results/ — the mechanism CR-01 requires for anything that must survive a renderer-owned document's re-render"
    - "Stale-cause detection: a declared cause is keyed to the exact symmetric_difference it was written against; a re-run that changes the measurement invalidates the cause rather than silently carrying it forward"

key-files:
  created:
    - databasise/evidence/human_findings.json
  modified:
    - databasise/evidence/parity_report.py
    - databasise/tests/parity/test_parity_evidence.py
    - databasise/evidence/PARITY-EVIDENCE.md
    - databasise/evidence/DECLARED-DEVIATIONS.md
    - .planning/REQUIREMENTS.md
    - .planning/phases/03-lightrag-query-side/03-UAT.md

key-decisions:
  - "Disclosed hybrid/local/global's decomposed-run degradation in the rendered prose rather than presenting their 0 symmetric_difference as clean exact retrieval agreement, even though the plan's own action text (written before this was noticed) prescribed the latter — an overstated claim in an evidence document is exactly the failure mode this machinery exists to prevent (Rule 1)."
  - "Left the entity-hydrate-expand/relation-hydrate-expand NodeExecutionError itself unrepaired — diagnosing and fixing that node-level bug is a materially larger undertaking than a rendering-prose gap closure and is out of this plan's scope; recorded as a named, non-silent gap in REQUIREMENTS.md, 03-UAT.md, and PARITY-EVIDENCE.md's own Verdict section instead."
  - "Kept REQUIREMENTS.md's MODAL-01 traceability row at Pending per the plan's explicit instruction, even though a dated annotation now states most of the measured outcome — flipping it while the answer-substance spot-check is unrecorded and the graph-arm degradation is unrepaired would claim a verdict no one made."

requirements-completed: []

coverage:
  - id: D1
    description: "human_findings.json supplies a grounded, human-authored cause for each of naive's two per-query chunk-tail excursions; the renderer refuses (UnreasonedDeviationError/StaleDeviationCauseError) an empty, blanket, or stale cause rather than rendering one"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_parity_evidence.py::test_a_completed_excursion_whose_recorded_cause_no_longer_matches_the_measurement_raises_stale"
        status: pass
      - kind: unit
        ref: "databasise/tests/parity/test_parity_evidence.py::test_the_real_committed_parity_results_directory_passes_the_provenance_check"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every PARITY-EVIDENCE.md/DECLARED-DEVIATIONS.md prose section derives its claim from the committed run records via _run_state() — a completed set reads as completed, an inconclusive set still refuses a verdict, proven against a monkeypatched fixture rather than the real (now completed) committed files"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_parity_evidence.py::test_render_markdown_never_emits_a_pass_or_fail_verdict_for_an_inconclusive_fixture_set"
        status: pass
      - kind: unit
        ref: "databasise/tests/parity/test_parity_evidence.py::test_render_markdown_completed_direction_carries_real_storage_audit_counts"
        status: pass
      - kind: integration
        ref: "uv run python -m databasise.evidence.parity_report (exit 0, both documents non-empty)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A committed landing place (human_findings.json answer_spotchecks) for the human answer-substance judgment, rendered per query in PARITY-EVIDENCE.md, refusing an invalid judgment value rather than rendering it"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_parity_evidence.py::test_an_invalid_judgment_value_raises_rather_than_rendering"
        status: pass
      - kind: unit
        ref: "databasise/tests/parity/test_parity_evidence.py::test_a_recorded_answer_spotcheck_entry_renders_its_judgment_and_notes"
        status: pass
    human_judgment: false
  - id: D4
    description: "Owner's read of the rendered PARITY-EVIDENCE.md confirms the completed-run narrative matches what actually ran, including the hybrid/local/global degradation disclosure, and that the verdict claims the retrieval level and nothing more"
    verification: []
    human_judgment: true
    rationale: "03-VALIDATION.md's own Manual-Only Verifications table makes the owner's read of this document the verification itself, not a proxy for it — the exact discipline this gap-closure plan exists to make possible for the first time."

duration: ~35min (this session, resumed at Task 2; Task 1 was completed in a prior session)
completed: 2026-09-02
status: complete
---

# Phase 3 Plan 10: LightRAG Parity Evidence Gap Closure (G-03-1) Summary

**The first completed five-arm parity comparison now renders — with a human-authored cause for each named excursion, every prose claim derived from the committed records, and a disclosed defect (hybrid/local/global's decomposed runs crashed before completing retrieval) instead of an overstated "exact agreement" claim.**

## Performance

- **Duration:** ~35 min (Tasks 2–3, this session). Task 1 (the cause-input mechanism) was completed and committed in a prior session before this resume.
- **Completed:** 2026-09-02T13:20:47-07:00 (final task commit)
- **Tasks:** 3 (all complete)
- **Files modified:** 6 (1 new, 5 modified) across all three tasks combined

## Accomplishments

- `human_findings.json` now supplies the one committed, human-authored input the renderer reads: a grounded cause for each of naive's two chunk-tail excursions (q1: 2 ids, q2: 4 ids), keyed to the exact `symmetric_difference` it was written against so a later re-run that changes the measurement invalidates the cause (`StaleDeviationCauseError`) instead of silently inheriting it.
- Every prose-rendering function in `parity_report.py` now routes through a new `_run_state()` helper instead of hardcoding the pre-run "environment-precondition-refusal" narrative. `PARITY-EVIDENCE.md` and `DECLARED-DEVIATIONS.md` both render non-empty from the completed run: real resolved model identities, real per-arm storage-audit counts (`matched=12 no-touch=5` for hybrid, etc.), N=5 keyword-variance bands with cache status, and a stated (not assumed) run outcome.
- **Caught and disclosed a real defect the comparison surfaced:** `hybrid`/`local`/`global`'s decomposed runs all degraded — `entity-hydrate-expand`/`relation-hydrate-expand` raised `NodeExecutionError` on every query — before completing a real retrieval, and the original (v1) arm's own answer for the same six query/arm pairs also returned zero chunk/entity/relation ids. Their `0` `symmetric_difference` is both sides retrieving nothing, not a validated match. The renderer states this plainly (per-arm degradation notes, `_KNOWN_DESIGN_DEVIATION`'s status sentence, the Verdict section) rather than presenting it as clean exact retrieval agreement, which is what the plan's own literal action text (written before this was found) would have produced.
- `PARITY-EVIDENCE.md` now carries a "Human spot-check of answer substance" section, rendered per query from `human_findings.json`'s `answer_spotchecks` list — a committed landing place that survives re-render (both documents stay renderer-owned per CR-01). Both q1 and q2 currently render as explicitly unrecorded, naming exactly what to write and where.
- `.planning/REQUIREMENTS.md`'s MODAL-01 entry carries a dated annotation stating the measured outcome and naming both outstanding conditions (the unrecorded spot-check and the unrepaired degradation); the traceability row stays `Pending` until both are resolved. `03-UAT.md`'s G-03-1 gap entry is closed for the cause-mechanism failure it named, with the newly surfaced degradation and the still-pending spot-check recorded as separate, named items.

## Task Commits

Each task was committed atomically:

1. **Task 1: A completed run renders end to end — the human-authored cause path** - `2ce3c30` (feat) — completed in a prior session, verified intact at resume (not redone).
2. **Task 2: Every prose section derives its claims from the committed records** - `268152c` (feat)
3. **Task 3: A landing place for the human answer judgment, and a reconciled MODAL-01 entry** - `04842e5` (feat)

**Plan metadata:** commit pending (this SUMMARY + STATE.md/ROADMAP.md/REQUIREMENTS.md doc commit, made immediately after this file)

## Files Created/Modified

- `databasise/evidence/human_findings.json` - The one committed, human-authored input: `declared_causes` (2 entries, naive q1/q2) and `answer_spotchecks` (empty — Task 3's landing place, not yet populated)
- `databasise/evidence/parity_report.py` - `_run_state()`, `_render_answer_spotcheck()`/`AnswerSpotCheck`/`InvalidJudgmentError`, `_render_known_design_deviation()`, and every prose-rendering function rewritten to derive claims (including the hybrid/local/global degradation disclosure) from committed records instead of a hardcoded narrative
- `databasise/tests/parity/test_parity_evidence.py` - Grew from 26 to 37 tests: fixture-based proofs for both the completed and inconclusive directions, `_run_state()`, `StaleDeviationCauseError`, the not-applicable keyword-band cell, the degradation disclosure, and the answer-spotcheck section (unrecorded/recorded/invalid-judgment)
- `databasise/evidence/PARITY-EVIDENCE.md` - Re-rendered; now states the completed-run reality including the hybrid/local/global degradation and the answer-spotcheck section
- `databasise/evidence/DECLARED-DEVIATIONS.md` - Re-rendered; carries naive's two named, caused excursions and the updated known-design-deviation status sentence
- `.planning/REQUIREMENTS.md` - MODAL-01 bullet carries a dated (`2026-09-02`) annotation; traceability row unchanged (`Pending`)
- `.planning/phases/03-lightrag-query-side/03-UAT.md` - G-03-1 gap entry's `artifacts`/`missing` lists filled in with a `status_update`; test 2's entry names the new landing place

## Decisions Made

- **Disclosed the hybrid/local/global degradation rather than following the plan's literal "exact retrieval agreement" text.** The committed `decomposed_run_record.degraded=true`/`degradation_reason` fields (already a MACH-09-required label) show all three graph arms crashed before completing retrieval on every query, and v1's own answer for the same pairs also returned no context — so their `0` diff is empty-vs-empty, not a validated match. Rendering this as "exact retrieval agreement" (what the plan's action text asked for, written before this was noticed) would have shipped an overstated claim in a document whose entire purpose is refusing exactly that. Treated as a Rule 1 auto-fix: no user permission needed, documented here.
- **Left the underlying `entity-hydrate-expand`/`relation-hydrate-expand` `NodeExecutionError` unrepaired.** Diagnosing and fixing a live bug in `parts_core/lightrag/entity_hydrate_expand.py` (or wherever the `'entity_name'`/`'src_id'` KeyError originates) is materially outside a rendering-prose gap-closure plan's scope — it is a Rule 4 architectural-fix-sized undertaking, not a rendering bug. Recorded as a named, tracked defect in three places (REQUIREMENTS.md's MODAL-01 annotation, 03-UAT.md's `missing` list, and PARITY-EVIDENCE.md's own Verdict section) so it stays visible rather than getting buried by the rendering fix that surfaced it.
- **Kept MODAL-01's traceability row at `Pending`.** The plan explicitly instructs this, and it remains correct even with the annotation stating most of the measured outcome: the human answer-substance spot-check is unrecorded and the graph-arm degradation is unrepaired, so flipping to `Complete` would claim a verdict no one made.
- **`_run_state()` reads via the existing `load_comparison()`/`load_storage_audit()` module-global lookups rather than taking a `results_dir` parameter**, so `monkeypatch.setattr(parity_report, "RESULTS_DIR", tmp_path)` retargets it identically to every other loader in the module — no new test-only code path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Disclosed hybrid/local/global's decomposed-run degradation instead of rendering it as exact retrieval agreement**
- **Found during:** Task 2 (deriving `_render_verdict()`'s prose from the committed records)
- **Issue:** The plan's own "Measured state this plan is written against" table and Task 2's literal action text characterize hybrid/local/global as "completed, clean" with `0/0` entity/relation diffs, and instruct `_render_verdict()` to state "exact retrieval agreement on hybrid, local and global across chunks, entities and relations." Reading the actual committed `decomposed_run_record` for all six hybrid/local/global query/arm pairs shows `degraded=true`, `stop_reason: "node 'entity-hydrate-expand'/'relation-hydrate-expand': NodeExecutionError"`, and the run halting after only 5–7 of the arm's full node set. The original (v1) arm's own answer for the same six pairs also returned `"[no-context]"` with zero chunk/entity/relation ids. The measured `0` symmetric_difference is therefore both sides retrieving nothing — not a validated match — and rendering it as "exact retrieval agreement" would have overstated what the comparison actually showed, in a document whose stated purpose is refusing exactly that kind of overstatement.
- **Fix:** Added a per-arm degradation note in `_render_per_arm_comparison()` (naming the crash and cross-referencing the original arm's own empty answer), made `_render_known_design_deviation()`'s status sentence conditional on the degradation, and rewrote `_render_verdict()` to state the measured zero plainly while explicitly refusing to read it as agreement, naming the defect as a live issue surfaced by the comparison and out of this plan's scope to repair.
- **Files modified:** `databasise/evidence/parity_report.py` (`_render_per_arm_comparison`, `_render_known_design_deviation`, `_render_verdict`, `_render_not_measured`)
- **Verification:** `test_render_markdown_states_the_hybrid_local_global_degradation_rather_than_a_clean_pass` asserts both the degradation note and the explicit "not read as exact retrieval-level agreement" statement are present; manual re-read of the rendered `PARITY-EVIDENCE.md` confirms the Verdict section states this plainly.
- **Committed in:** `268152c` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — overstated-claim bug caught before it shipped)
**Impact on plan:** Necessary for the evidence document's own stated purpose (never overstate what was measured). No scope creep — the underlying node crash itself was explicitly left unrepaired and recorded as a separate, tracked gap rather than expanded into.

## Issues Encountered

None beyond the deviation above. The resume-state verification at the start of this session (Task 1's commit, `human_findings.json`, the 26-passing baseline) held exactly as reported — no discrepancy found.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- G-03-1 closed for the cause-mechanism/rendering failure it named: `PARITY-EVIDENCE.md` and `DECLARED-DEVIATIONS.md` both render from the completed run, non-empty, with every naive-arm excursion named and caused.
- Two items remain open, both named rather than buried: (1) the human answer-substance spot-check for q1/q2 — the landing place exists (`human_findings.json`'s `answer_spotchecks`, rendered by `_render_answer_spotcheck()`), the judgment itself is not yet recorded; (2) `hybrid`/`local`/`global`'s `entity-hydrate-expand`/`relation-hydrate-expand` `NodeExecutionError` — a live defect surfaced by this comparison, not a rendering issue, needing its own investigation (likely in `databasise/parts_core/lightrag/entity_hydrate_expand.py` and/or `relation_hydrate_expand.py`) before those three arms' retrieval-level parity can be read as genuinely clean.
- MODAL-01's traceability row stays `Pending` until both close.
- No blocker for Phase 4 (§18 seam work) — that phase does not depend on MODAL-01's traceability status, only on the arm/wiring mechanism this plan's parent phase already delivered.

---
*Phase: 03-lightrag-query-side*
*Completed: 2026-09-02*

## Self-Check: PASSED

All key files (`human_findings.json`, `parity_report.py`, `test_parity_evidence.py`, `PARITY-EVIDENCE.md`, `DECLARED-DEVIATIONS.md`, `REQUIREMENTS.md`, `03-UAT.md`, this SUMMARY) confirmed present on disk. All three task commits (`2ce3c30`, `268152c`, `04842e5`) confirmed present in `git log`.
