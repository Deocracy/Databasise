---
phase: 03-lightrag-query-side
verified: 2026-09-06T22:30:00Z
status: human_needed
score: 3/4 must-haves verified (criteria 4/5 remain N/A — legitimately deferred to Phase 6, unchanged)
behavior_unverified: 0
overrides_applied: 0
covered_files:

  - ".planning/REQUIREMENTS.md"
  - ".planning/phases/03-lightrag-query-side/03-01-PLAN.md"
  - ".planning/phases/03-lightrag-query-side/03-01-SUMMARY.md"
  - ".planning/phases/03-lightrag-query-side/03-02-PLAN.md"
  - ".planning/phases/03-lightrag-query-side/03-02-SUMMARY.md"
  - ".planning/phases/03-lightrag-query-side/03-03-PLAN.md"
  - ".planning/phases/03-lightrag-query-side/03-03-SUMMARY.md"
  - ".planning/phases/03-lightrag-query-side/03-04-PLAN.md"
  - ".planning/phases/03-lightrag-query-side/03-04-SUMMARY.md"
  - ".planning/phases/03-lightrag-query-side/03-05-PLAN.md"
  - ".planning/phases/03-lightrag-query-side/03-05-SUMMARY.md"
  - ".planning/phases/03-lightrag-query-side/03-06-PLAN.md"
  - ".planning/phases/03-lightrag-query-side/03-06-SUMMARY.md"
  - ".planning/phases/03-lightrag-query-side/03-07-PLAN.md"
  - ".planning/phases/03-lightrag-query-side/03-07-SUMMARY.md"
  - ".planning/phases/03-lightrag-query-side/03-08-PLAN.md"
  - ".planning/phases/03-lightrag-query-side/03-08-SUMMARY.md"
  - ".planning/phases/03-lightrag-query-side/03-09-PLAN.md"
  - ".planning/phases/03-lightrag-query-side/03-09-SUMMARY.md"
  - ".planning/phases/03-lightrag-query-side/03-10-PLAN.md"
  - ".planning/phases/03-lightrag-query-side/03-10-SUMMARY.md"
  - ".planning/phases/03-lightrag-query-side/03-11-PLAN.md"
  - ".planning/phases/03-lightrag-query-side/03-11-SUMMARY.md"
  - ".planning/phases/03-lightrag-query-side/03-12-PLAN.md"
  - ".planning/phases/03-lightrag-query-side/03-12-SUMMARY.md"
  - ".planning/phases/03-lightrag-query-side/03-13-PLAN.md"
  - ".planning/phases/03-lightrag-query-side/03-13-SUMMARY.md"
  - ".planning/phases/03-lightrag-query-side/03-UAT.md"
  - "databasise/evidence/DECLARED-DEVIATIONS.md"
  - "databasise/evidence/PARITY-EVIDENCE.md"
  - "databasise/evidence/human_findings.json"
  - "databasise/evidence/parity_report.py"
  - "databasise/parity/import_index.py"
  - "databasise/parity/run_arm.py"
  - "databasise/parts_core/lightrag/entity_hydrate_expand.py"
  - "databasise/parts_core/lightrag/relation_hydrate_expand.py"
  - "databasise/stores/vector.py"

covered_digest: "v1:sha256:31af7c5a3acfa3bc6c78b14b0fea18c1572233399db50a56941506ce52c1b3c8"
re_verification:
  previous_status: gaps_found
  previous_score: 2/4
  gaps_closed:
    - "Gap 2 (stale evidence) closed: 03-13-PLAN.md re-ran all five arms against the CR-01-fixed source (commit cee485f), replacing all ten committed parity_results/*.json records in one sitting. Verified live: all ten per-query records now read status='completed', decomposed_run_record.degraded=False."
    - "Gap 3 (no valid retrieval-level parity for hybrid/local/global) closed: the corpus-index root cause (v1's ingest silently failing extraction on every document, discovered by 03-11) and the shared-vector-namespace bug (discovered by 03-12) are both fixed. All five arms — including hybrid/local/global — now complete a real, non-degraded retrieval on both sides. The measured result is substantial graph-half disagreement (entity sym_diff 20-76, relation sym_diff 30-78 per query), honestly reported as disagreement, not folded into a vacuous zero."
    - "A three-iteration code review ran over the gap-closure wave, catching and fixing a rendering bug that asserted measured agreement the data contradicted (CR-01) and a coarsened comparison primitive that had been weakened to clear a boundary case (CR-02, replaced with a per-vector tolerance check). Full suite: 466 passed, 0 failed (confirmed by direct re-run this session, not taken from SUMMARY.md)."
  gaps_remaining:
    - "Gap 1 (AI-authored declared-deviation causes) not code-closeable — reclassified from FAILED to a human-verification item (see below); the mechanism is real and tested, only the human owner's own reasoning is missing."
    - "Gap 4 (human answer-substance spot-check) not code-closeable — reclassified from FAILED to a human-verification item; same reasoning."
    - "18 newly-measured hybrid/local/global excursions (03-13's own finding) have no declared_causes entry yet — an extension of gap 1, same human-only closure path, itemized in 03-UAT.md test 3."
  regressions: []
gaps: []
behavior_unverified_items: []
human_verification:

  - test: "CONTRACT §5 human-authored declared-deviation causes (naive's 2 existing entries + 18 new hybrid/local/global excursions)"
    expected: "The human owner (christopher@deocracy.org) personally reviews each named excursion and records their own cause and recorded_by in databasise/evidence/human_findings.json's declared_causes list, replacing the two AI-authored entries and adding one entry per (arm, query, field) row DECLARED-DEVIATIONS.md's 'Outstanding' section lists. Exact commands, JSON shape, and the full 18-row breakdown are in 03-UAT.md test 3."
    why_human: "CONTRACT §5 requires a human-authored cause naming the human owner as recorded_by; an executor authoring this on the owner's behalf would be a false attestation of human review that did not happen (03-REVIEW-FIX.iter1.md's WR-02 explicitly declined to fabricate one for this reason). No code change closes this — it requires the owner's own judgment about whether each excursion is tolerable variance or a real defect."
  - test: "Human spot-check of answer substance for q1/q2 (criterion 6, D-05 substitute gate)"
    expected: "The owner runs q1 and q2 through databasise.parity.run_comparison --arm naive, compares the decomposed answer against v1's recorded original_arm_result.answer, and records a match/no-match/partial judgment with notes in human_findings.json's answer_spotchecks list. Exact commands and JSON fields are in 03-UAT.md test 2."
    why_human: "Answer substance from a stochastic generator is not mechanically checkable, and no A/A calibration floor exists yet to substitute a numeric threshold (MACH-02/MACH-03 deferred to Phase 6). This is the explicit human half of the D-05 substitute gate — 03-UAT.md test 2 has been [pending] since the prior verification and remains so; the landing mechanism is real and tested (parity_report.py's _render_answer_spotcheck renders it), only the judgment itself is missing."
audit_acknowledged:
  milestone: v1.0
  at: 2026-09-12
  status: human_needed
---

# Phase 3: LightRAG Query Side Verification Report

**Phase Goal:** LightRAG's query path runs as fitted primitive parts and its parity against the original is measured, not asserted (§BP rung 2)
**Verified:** 2026-09-06T22:30:00Z
**Status:** human_needed
**Re-verification:** Yes — after a three-plan gap-closure wave (03-11, 03-12, 03-13) plus a three-iteration code-review fix cycle (previous verification 2026-09-05, status gaps_found, 2/4)

## Goal Achievement

### Observable Truths (ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Seventeen of eighteen §L.1 query-side positions run as fitted primitive-part nodes; the eighteenth (`embedder-index`) is authored as the one index-recipe node | ✓ VERIFIED | Live import this session confirms `databasise.parts_core.lightrag.LIGHTRAG_PARTS` still holds 15 registered `@0.1.0` parts (14 `stage` + `embedder-index@0.1.0` with `structural_depth='opaque'`, `artifact_scope='quarantined'`) — unchanged, no regression. |
| 2 | Owner runs the same corpus through the decomposed query side and the pre-decomposition original and reads an N-run variance band, or every excursion outside it is a named declared deviation under CONTRACT §5 | ⚠️ Measurement complete; deviation-naming incomplete | The N=5 keyword-variance band and the retrieval-level comparison are now real and complete for all five arms (verified live: all 10 per-query records read `status='completed'`, `degraded=False`). But CONTRACT §5's "named declared deviation" bar is not yet met: naive's 2 excursions have a technically-grounded cause whose `recorded_by` names an AI agent, not the human owner, and 18 new hybrid/local/global excursions have no cause at all — both honestly disclosed as outstanding, not silently absorbed. Routed to human verification below. |
| 3 | Every fitted node reaches storage through a machine primitive only; the per-node ownership audit ships as part of the parity evidence | ✓ VERIFIED | `grep -rn "^import v1\|^from v1" parts_core/lightrag/*.py` returns zero matches (confirmed live this session). The storage-ownership audit table ships inside `PARITY-EVIDENCE.md` for all five arms, all reporting `outcome: completed` with real matched/no-touch/over-declared counts. |
| 4 | Eval bundle minted per RIG §EV.1/§EV.2 before decomposition work reads holdout | N/A — deferred to Phase 6 | Unchanged: `03-GATE-AMENDMENT.md` records the deferral. |
| 5 | A/A calibration read, Falsifier 5 pass criterion met | N/A — deferred to Phase 6 | Unchanged: same amendment covers MACH-03. |
| 6 | Until the A/A floor exists, parity is checked at the retrieval level with deterministic, zero-token comparisons, plus human spot-checks of answers (D-05 substitute gate) | ⚠️ Retrieval-level half complete; human spot-check outstanding | A real, non-degraded retrieval-level comparison now exists for all five arms (previously only 2 of 5). `hybrid`/`local`/`global` disagree substantially with the original (entity sym_diff 20-76, relation sym_diff 30-78 per query, ranking agreement 0.50-0.86) — `PARITY-EVIDENCE.md`'s own Verdict section states this plainly, does not call it agreement, and does not fold it into a vacuous zero. `bypass` correctly renders "no retrieval to compare" (a single-node wiring with nothing to diff) rather than a 0-vs-0 masquerading as agreement. The human answer-substance spot-check has not been performed — routed to human verification below. |

**Score:** 3/4 truths fully verified for Phase 3's own obligation (criteria 1, 3, and the measurement half of 2/6); criteria 2 and 6's CONTRACT §5 / human-spot-check halves route to human verification; criteria 4/5 remain correctly N/A (deferred to Phase 6, unchanged).

### Interpreting criterion 2/6 (per this verification's explicit framing)

The phase's obligation, per its own goal text, is that parity **is measured, not asserted** — not that parity is achieved. That obligation is now met for all five arms: the corpus-index root cause (v1's ingest silently failing extraction on every document — an unquoted JSON value under `set -a && . .env.parity`) and the shared-vector-namespace bug (every §L.1 vector position reading the `chunks` namespace) are both fixed and verified live this session (466 passed, 0 failed; all 10 per-query comparison records `completed`/non-degraded). What the measurement shows is substantial graph-half divergence, not agreement — and `PARITY-EVIDENCE.md` says so directly, in its Verdict section, for every arm, rather than asserting a clean pass the data does not support. That is a genuine measurement, honestly reported, which is the phase's actual deliverable.

What remains open is a second, distinct obligation — CONTRACT §5's requirement that every excursion carry a **human-authored** cause before it is "read as accepted, declared variance," plus criterion 6's human answer-substance spot-check. Both are explicitly human-only: an executor cannot author a human's cause without producing a false attestation (documented and declined in 03-REVIEW-FIX.iter1.md's WR-02), and an LLM-generated answer's substance is not mechanically checkable pending Phase 6's A/A floor. Neither is a code defect — the landing mechanisms for both (`human_findings.json`, `parity_report.py`'s renderer) are built, tested, and correctly wired. This is why the overall status is `human_needed` rather than `gaps_found`: there is no further engineering work that closes either item, only the owner's own judgment, and `03-UAT.md` already gives the owner the exact commands and JSON fields to do it.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/parts_core/lightrag/*` (15 parts) | Decomposed query-side node bodies | ✓ VERIFIED | Live import confirms 15 registered parts, unchanged. |
| `databasise/parts_core/lightrag/entity_hydrate_expand.py`, `relation_hydrate_expand.py` | Malformed-seed handling (CR-01, prior wave) | ✓ VERIFIED (code) | Unchanged from prior verification, still present. |
| `databasise/stores/vector.py` | `MultiNamespaceVectorStore` — each §L.1 vector position bound to its own namespace, no silent `chunks` fallback | ✓ VERIFIED (code) | Confirmed present (`MultiNamespaceVectorStore`, `select()`-before-use refusal). 03-REVIEW.md independently confirmed no silent default survives. |
| `databasise/evidence/parity_results/*.json` (10 files) | One comparison record per arm×query, from one post-fix run | ✓ VERIFIED | Live check this session: all 10 records read `status='completed'`, `decomposed_run_record.degraded=False` — genuinely re-run against the CR-01-fixed source (commit `cee485f`), not stale. |
| `databasise/evidence/PARITY-EVIDENCE.md`, `DECLARED-DEVIATIONS.md` | Rendered parity evidence from the completed run, describing current source behavior | ✓ VERIFIED | Re-read live this session. Confirms all five arms `completed`, states the real hybrid/local/global disagreement numbers directly, and does not claim measured agreement anywhere (the CR-01 rendering bug that made this false in an earlier draft of this same wave was caught by 03-REVIEW.iter3.md and fixed by 03-REVIEW-FIX.md before this evidence was committed). |
| `databasise/evidence/human_findings.json` | Committed human-authored cause + answer-spotcheck input | ⚠️ PARTIAL (human verification required) | Mechanism is real, tested, and correctly wired into the renderer. Its two populated `declared_causes` entries are still AI-authored (`recorded_by: "Claude (AI agent, gsd-code-fixer)..."`), 18 new excursions have no entry at all, and `answer_spotchecks` is still `[]`. This is the phase's one remaining gap, and it is human-only — see Human Verification below. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `parity_results/*-comparison.json` (current, post-fix) | `PARITY-EVIDENCE.md` prose | `_run_state()` / `_arm_degraded()` / `_arm_excursion_summary()` helpers | ✓ WIRED, CURRENT | Confirmed live: the rendered document's per-arm numbers match the live JSON files exactly (spot-checked hybrid/local/global entity/relation sym_diff and ranking_agreement). No longer stale. |
| `human_findings.json` | `render_deviations_document()` | `load_human_findings()` → `_collect_deviations()` | ✓ WIRED | 2 naive causes render into "Named deviations"; 18 uncaused excursions render into "Outstanding" as `PENDING`, never silently dropped or fabricated — confirmed by reading the live `DECLARED-DEVIATIONS.md`. |
| `entity_hydrate_expand.py` / `relation_hydrate_expand.py` malformed seed | `missing_seeds` output | `seed.get(...)` + `is None` guard | ✓ WIRED | Unchanged from prior verification. |
| `MultiNamespaceVectorStore` | each §L.1 vector position's own namespace | `select(namespace)` refusal-before-use | ✓ WIRED | 03-12's fix; confirmed present in `stores/vector.py`, exercised by the now-completing hybrid/local/global comparisons themselves (a wiring bug here would have reproduced the old crash, not a clean completion). |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite (run directly this session, not taken from SUMMARY.md) | `cd databasise && uv run pytest -q` | `466 passed in 124.58s` | ✓ PASS |
| Parts registry regression | live `LIGHTRAG_PARTS` import | 15 parts, `embedder-index` opaque/quarantined, unchanged | ✓ PASS |
| No v1 singleton imports in ported parts | `grep -rn "^import v1\|^from v1" parts_core/lightrag/*.py` | zero matches | ✓ PASS |
| Debt-marker scan | `grep -rn "TBD\|FIXME\|XXX"` across `parts_core`, `parity`, `evidence`, `clients`, `wirings`, `stores` | zero matches | ✓ PASS |
| All 5 arms' comparison records are `completed`/non-degraded (the phase's central claim) | direct JSON read of all 10 `parity_results/*-comparison.json` records | 10/10 `status='completed'`, `degraded=False` | ✓ PASS |
| `bypass`'s "no retrieval" is by-design, not a vacuous zero | read `PARITY-EVIDENCE.md`'s `bypass` section and `run_comparison.py`'s `_no_retrieval_to_compare_note` | `bypass` resolves to a single `generate` node with no chunk-source node at all — the arm structurally has nothing to diff, distinct from a computed zero | ✓ PASS — by design, not vacuous |

### Code Review Findings Carried Into This Verification

The gap-closure wave went through three review/fix iterations (`03-REVIEW.iter2.md` → `03-REVIEW-FIX.iter2.md` → `03-REVIEW.iter3.md` → `03-REVIEW-FIX.md` (iteration 3) → `03-REVIEW.md`, the final re-review). The final re-review (`03-REVIEW.md`, reviewed 2026-09-06T21:10:00Z) found **0 critical, 3 warnings, 1 info** — none of which misstate the phase's central measurement claim:

- **WR-01**: `_render_not_measured()`'s branching is a priority chain, not a per-arm loop — would silently under-report if a future re-run mixed a degraded arm with an excursion arm simultaneously. Does not affect the current committed data (confirmed: `PARITY-EVIDENCE.md` re-renders byte-for-byte identical from current code and current data). Latent completeness gap, not a live defect.
- **WR-02**: A code comment claims "two orders of magnitude" margin where the real ratio is one order of magnitude (10x, not 100x) — a documentation/math error, not a functional defect; the underlying 10x margin is itself defended as reasonable in the same review.
- **WR-03**: The new tolerance-check regression test proves the mechanism still fires but not the specific "strictly stronger than the old rounding grid" claim CR-02 made — a test-coverage gap, not a functional defect (the reviewer independently exercised `_compare_vector_sets` directly and confirmed it behaves correctly on id-missing/id-extra/below-tolerance/above-tolerance cases).
- **IN-01**: `verify_import`'s graph-topology assertion checks id/edge-pair sets only, not attribute payloads — an out-of-scope note carried forward from the prior review, not new.

None of these four items block this phase's goal or contradict any of the truths above; none touch a debt marker (the debt-marker gate scan is independently clean). They are recorded here for completeness, not as gaps.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| MODAL-01 | 03-01, 02, 04–13 | LightRAG query side re-cut into primitive-part nodes with N-run variance-banded parity or declared deviations | ⚠️ PARTIALLY SATISFIED — human action pending | Decomposition (17/18 positions, no v1 singleton reference) is real, complete, and unchanged. The measurement half is now real and complete for all five arms (previously only 2 of 5) — this is the substantive close since the prior verification. The CONTRACT §5 declared-cause and human-spot-check halves remain open, both human-only. REQUIREMENTS.md line 29's `[ ]` checkbox and its 2026-09-06 annotation (superseding the 2026-09-02 note) already state this precisely and correctly — it names the measured outcome, names both remaining owner-only items, and states the row stays Pending until both are recorded. This verification does not need to correct that annotation; it already matches what this session independently confirmed live. |
| MACH-02 | 03-03, 03-09 | Eval bundle (RIG §EV.1) | N/A for Phase 3 — correctly deferred to Phase 6 | Unchanged. |
| MACH-03 | 03-03, 03-09 | A/A calibration, Falsifier 5 | N/A for Phase 3 — correctly deferred to Phase 6 | Unchanged. |

No orphaned requirements — ROADMAP.md's Phase 3 requirements field lists only `MODAL-01`; MACH-02/MACH-03 appear in plan frontmatter only for the deferral-recording plans, and REQUIREMENTS.md already attributes their substance to Phase 6.

### Anti-Patterns Found

None. Debt-marker scan (`TBD`/`FIXME`/`XXX`) across every file this phase's gap-closure wave and review-fix cycle touched is clean, confirmed live this session.

### Human Verification Required

See `human_verification` in this document's frontmatter for the full detail. Summary:

1. **CONTRACT §5 human-authored declared-deviation causes** — the owner replaces the 2 existing AI-authored causes and adds 18 new ones (naming their own reasoning, not an AI's) for the hybrid/local/global excursions this wave's fix newly surfaced. Exact commands and JSON shape: `03-UAT.md` test 3.
2. **Human spot-check of answer substance for q1/q2** — the owner reads the decomposed `naive` arm's answer against v1's recorded answer and records a match/no-match/partial judgment. Exact commands and JSON shape: `03-UAT.md` test 2.

Both landing mechanisms (`human_findings.json`, `parity_report.py`'s renderer) are built and tested; no further code change closes either item.

### Gaps Summary

No code-level gaps remain. The gap-closure wave (03-11, 03-12, 03-13) plus its three-iteration review-fix cycle closed both of the prior verification's central defects: the corpus index had no knowledge graph at all (root cause: a silently-swallowed extraction failure across every document, from an unquoted env value), and every §L.1 vector position was reading the wrong namespace. Both are fixed and independently re-confirmed live this session — 466 tests pass, all five arms' comparison records read `completed`/non-degraded, no `v1.*` import survives in any ported part, and the rendered evidence documents match the live data exactly with no overstated claim of agreement.

What the now-working measurement reveals is that `hybrid`/`local`/`global` disagree substantially with the original arm on which entities/relations are retrieved (symmetric differences of 20-78 per query) — a real, disclosed finding, not a defect in this phase's own deliverable (which was to measure, not to achieve agreement). Two items remain, both explicitly human-only per CONTRACT §5's own design (no AI-authored cause is a valid cause) and both already routed to the owner via `03-UAT.md`'s exact instructions: recording a human-authored cause for all 20 excursions, and performing the q1/q2 answer-substance spot-check. Neither blocks the measurement claim this phase makes; both block the CONTRACT §5 "named declared deviation" bar and criterion 6's human-spot-check bar from being fully closed.

---

_Verified: 2026-09-06T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
