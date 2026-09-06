---
phase: 03-lightrag-query-side
verified: 2026-09-05T23:15:00Z
status: gaps_found
score: 2/4 must-haves verified (criteria 4/5 remain N/A — legitimately deferred to Phase 6, unchanged)
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: human_needed
  previous_score: 4/6
  gaps_closed:
    - "Environment gap closed: v1/.venv, v1/.parity_working_dir, v1/.parity_v2_store, v1/.env.parity were rebuilt and a real five-arm comparison actually ran (previously blocked all measurement)."
    - "G-03-1 (evidence renderer crashing with UnreasonedDeviationError, PARITY-EVIDENCE.md 0 bytes) closed by 03-10-PLAN.md — the renderer now produces a non-empty, derived document from the completed run."
  gaps_remaining:
    - "Human spot-check of answer substance for q1/q2 — still not recorded (human_findings.json's answer_spotchecks is still an empty list)."
  regressions: []
gaps:
  - truth: "Declared deviations carry a specific human-authored cause, per CONTRACT §5 and 03-10-PLAN.md's own must-have truth #2 ('...carrying a specific human-authored cause')"
    status: failed
    reason: "human_findings.json's two declared_causes entries (naive q1, q2) are recorded_by 'Claude (AI agent, gsd-code-fixer) — commit 2ce3c30; NOT recorded by the human owner, despite this file's own name'. 03-10-SUMMARY.md self-documents this as a finding (downgraded to 'MINOR' by the executor); 03-REVIEW.md's WR-02 independently re-raises it as an open Warning requiring human action, unresolved as of this verification's HEAD. The mechanism CR-01 built (a committed human-authored-cause input file) is real and tested, but no human has actually used it yet — the only two causes on file are AI-authored, which is exactly what CONTRACT §5 says must not stand in for a human's reasoning."
    artifacts:
      - path: "databasise/evidence/human_findings.json"
        issue: "declared_causes[0].recorded_by and [1].recorded_by both name an AI agent, not the human owner"
      - path: "databasise/evidence/DECLARED-DEVIATIONS.md"
        issue: "Renders the AI-authored causes verbatim into the committed document without qualification beyond the honest recorded_by string"
    missing:
      - "The human owner (christopher@deocracy.org) reviews the two named naive excursions (q1: 2 chunk ids past rank 10, q2: 4 chunk ids past rank 10) and re-records declared_causes with their own reasoning and recorded_by, per WR-02's fix."
  - truth: "The committed parity evidence (PARITY-EVIDENCE.md, DECLARED-DEVIATIONS.md, parity_results/{hybrid,local,global}-comparison.json) accurately reflects the current source code's behavior"
    status: failed
    reason: "Commit 1827695 (CR-01, landed today) changed entity_hydrate_expand.py/relation_hydrate_expand.py so the exact malformed-seed shape that produced 'NodeExecutionError: entity_name' / 'src_id' no longer raises at all — it now degrades one seed into missing_seeds and lets the node continue. The committed evidence documents were rendered before this fix (03-REVIEW.md's own WR-04 finding, still open) and still assert, as the current/live state, that hybrid/local/global 'degrade before completing a real retrieval' with this exact crash. No re-run has happened since the fix landed, so today's committed evidence describes pre-fix behavior that the current source no longer exhibits, and — separately — provides no evidence either way about whether the fixed code now completes a real retrieval for these three arms."
    artifacts:
      - path: "databasise/evidence/PARITY-EVIDENCE.md"
        issue: "Verdict and per-arm sections (lines ~50,59,68,117,119,121,133,135,137) describe hybrid/local/global's NodeExecutionError crash as the current state; commit 1827695 has since changed this behavior"
      - path: "databasise/evidence/parity_results/hybrid-comparison.json"
        issue: "decomposed_run_record.stop_reason/degradation_reason still name the pre-fix KeyError('entity_name') crash"
      - path: "databasise/evidence/parity_results/local-comparison.json"
        issue: "Same stale stop_reason (KeyError('entity_name'))"
      - path: "databasise/evidence/parity_results/global-comparison.json"
        issue: "Same stale stop_reason (KeyError('src_id'))"
    missing:
      - "Re-run databasise.parity.run_comparison for hybrid/local/global and re-render databasise.evidence.parity_report now that CR-01 has landed, replacing the stale crash-based record with whatever the current code actually measures — or, if a re-run is deliberately deferred, an explicit dated note in PARITY-EVIDENCE.md stating the NodeExecutionError this document describes was patched by commit 1827695 after this evidence was rendered."
  - truth: "Retrieval-level parity is measured (not a vacuous both-sides-empty zero) for the graph-half arms — hybrid, local, global (ROADMAP criterion 6)"
    status: failed
    reason: "hybrid/local/global's decomposed runs each halted before completing any real retrieval (NodeExecutionError on entity-hydrate-expand / relation-hydrate-expand); the original (v1) arm's recorded answer for the same query/arm pairs is also empty ('...[no-context]'). The recorded symmetric_difference=0 for chunk/entity/relation diffs on these 3 arms is both sides retrieving nothing, not a validated match — PARITY-EVIDENCE.md's own Verdict section states this explicitly ('not evidence of parity... a live defect this comparison surfaced'). No valid retrieval-level parity measurement exists today for 3 of the 5 wiring arms, including the two arms (hybrid, global) that most heavily exercise the KG-half decomposition this phase built."
    artifacts:
      - path: "databasise/evidence/parity_results/hybrid-comparison.json"
        issue: "decomposed_run_record.partial=true, degraded=true — run never reached generate"
      - path: "databasise/evidence/parity_results/local-comparison.json"
        issue: "Same partial/degraded shape"
      - path: "databasise/evidence/parity_results/global-comparison.json"
        issue: "Same partial/degraded shape"
    missing:
      - "A completed retrieval-level comparison for hybrid/local/global where the decomposed run actually reaches generate on both sides (or at minimum reaches a real, non-empty retrieval to diff), following the CR-01 fix — or, absent that, an explicit declared deviation naming the crash as an accepted, out-of-scope defect for this phase rather than a vacuous zero standing in for parity."
  - truth: "Criterion 6's human spot-checks of answers are performed and recorded alongside the deterministic retrieval-level comparison"
    status: failed
    reason: "human_findings.json's answer_spotchecks list is still empty. 03-UAT.md's test 2 remains [pending] (unchanged since the prior verification, now correctly re-pointed at the naive arm instead of hybrid). PARITY-EVIDENCE.md's own 'Human spot-check of answer substance' section renders both q1 and q2 as 'Not yet recorded.' The landing mechanism (03-10-PLAN.md's deliverable) is real, tested, and correctly wired into the renderer — but no human has performed the read yet."
    artifacts:
      - path: "databasise/evidence/human_findings.json"
        issue: "answer_spotchecks: [] — no entries"
    missing:
      - "The human owner runs q1 and q2 through databasise.parity.run_comparison --arm naive and through v1 directly, reads both answers side by side, and records a match/no-match judgment with notes in human_findings.json's answer_spotchecks list, per 03-UAT.md test 2's corrected instructions."
---

# Phase 3: LightRAG Query Side Verification Report

**Phase Goal:** LightRAG's query path runs as fitted primitive parts and its parity against the original is measured, not asserted (§BP rung 2)
**Verified:** 2026-09-05T23:15:00Z
**Status:** gaps_found
**Re-verification:** Yes — after gap closure (previous verification 2026-09-01, status human_needed, 4/6)

## Goal Achievement

### Observable Truths (ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Seventeen of eighteen §L.1 query-side positions run as fitted primitive-part nodes; the eighteenth (`embedder-index`) is authored as the one index-recipe node | ✓ VERIFIED | `databasise.parts_core.lightrag.LIGHTRAG_PARTS` has 15 registered `@0.1.0` parts (confirmed by live import this session — unchanged from prior verification). `embedder-index@0.1.0` has `structural_depth='opaque'`, `artifact_scope='quarantined'`. |
| 2 | Owner runs the same corpus through the decomposed query side and the pre-decomposition original and reads an N-run variance band, or every excursion is a named declared deviation under CONTRACT §5 | ✗ FAILED | The live five-arm comparison did run this time (environment gap closed). `naive`/`bypass` produced real, informative measurements. But the two naive excursions' declared causes are AI-authored, not human-authored as CONTRACT §5 and the plan's own must-have require (see gap 1); and `hybrid`/`local`/`global`'s measured "zero diff" is both sides retrieving nothing, not a real variance band or a validated deviation (see gap 3). |
| 3 | Every fitted node reaches storage through a machine primitive only; the per-node ownership audit ships as part of the parity evidence | ✓ VERIFIED | No ported part imports `v1.*` (grep confirmed, unchanged). The audit ships inside `PARITY-EVIDENCE.md` and honestly distinguishes `naive`/`bypass`'s clean audits from `hybrid`/`local`/`global`'s crash-truncated ones — it does not claim compliance for nodes that never ran. This transparency is itself the correct behavior for this criterion. |
| 4 | Eval bundle minted per RIG §EV.1/§EV.2 before decomposition work reads holdout | N/A — deferred to Phase 6 | Unchanged: `03-GATE-AMENDMENT.md` records the deferral, cross-referenced in ROADMAP.md and REQUIREMENTS.md. |
| 5 | A/A calibration read, Falsifier 5 pass criterion met | N/A — deferred to Phase 6 | Unchanged: same amendment covers MACH-03. |
| 6 | Until the A/A floor exists, parity is checked at the retrieval level with deterministic, zero-token comparisons, plus human spot-checks of answers (D-05 substitute gate) | ✗ FAILED | Real retrieval-level comparison exists for `naive`/`bypass` only. `hybrid`/`local`/`global` never completed a real retrieval on either side (see gap 3) — no valid comparison exists for 3 of 5 arms. The human answer-substance spot-check required by this criterion has not been performed at all (`human_findings.json`'s `answer_spotchecks` is empty; see gap 4). |

**Score:** 2/4 truths verified for Phase 3's own obligation (criteria 1, 3); criteria 2 and 6 FAILED; criteria 4/5 remain correctly N/A (deferred to Phase 6, unchanged from prior verification).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/parts_core/lightrag/*` (15 parts) | Decomposed query-side node bodies | ✓ VERIFIED | Unchanged from prior verification — live import confirms 15 registered parts. |
| `databasise/parts_core/lightrag/entity_hydrate_expand.py`, `relation_hydrate_expand.py` | Malformed-seed handling (CR-01 fix) | ✓ VERIFIED (code) | `seed.get("entity_name")`/`seed.get("src_id")`/`seed.get("tgt_id")` with explicit `is None` checks confirmed in current source, routing to `missing_seeds` with `malformed_seed: True` instead of raising `KeyError`. Two new regression tests confirmed present and passing. |
| `databasise/parity/run_arm.py` | Named refusal for missing `.env.parity` keys (WR-01 fix) | ✓ VERIFIED (code) | `MissingParityEnvKeyError` and `_REQUIRED_ENV_KEYS` present; confirmed by commit diff and code review's independent verification. |
| `databasise/evidence/parity_report.py` | Qualifies `--check-results` clean line for degraded-but-vacuous arms (WR-03 fix) | ✓ VERIFIED (code) | `_degraded_but_vacuous_arms()` present, tested against real committed data (asserted to name exactly hybrid/local/global). |
| `databasise/evidence/human_findings.json` | Committed human-authored cause + answer-spotcheck input | ⚠️ PARTIAL | Mechanism exists and is wired into the renderer correctly, but its two populated entries are AI-authored (not human-authored, contradicting the file's own stated purpose and CONTRACT §5), and `answer_spotchecks` is empty. |
| `databasise/evidence/PARITY-EVIDENCE.md`, `DECLARED-DEVIATIONS.md` | Rendered parity evidence from the completed run | ⚠️ STALE | Renders non-empty and derives its prose from committed records (G-03-1 genuinely closed) — but the records it derives from predate today's CR-01 fix and are not yet re-run, so 3 of 5 arms' sections describe behavior the current source no longer produces (WR-04, unresolved). |
| `databasise/evidence/parity_results/{hybrid,local,global}-comparison.json` | Real per-arm comparison records | ⚠️ STALE | Real committed data, but pre-CR-01; `decomposed_run_record.stop_reason`/`degradation_reason` still name the exact crash the fix landed today addresses. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `human_findings.json` | `render_deviations_markdown()` | `load_human_findings()` → `_collect_deviations()` | ✓ WIRED | Confirmed: renders non-empty, refuses on stale/blanket/missing cause (tested against real committed data per WR-03/03-10 test suite). |
| `entity_hydrate_expand.py` malformed seed | `missing_seeds` output | `seed.get(...)` + `is None` guard | ✓ WIRED | Confirmed in source; new regression tests exercise exactly this path per code review's independent verification. |
| `parity_results/*-comparison.json` (current, pre-fix) | `PARITY-EVIDENCE.md` prose | `_run_state()` helper | ⚠️ WIRED BUT STALE | The link itself works correctly (derives prose from records) — the records themselves are stale relative to source (see gaps 2/3). |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `cd databasise && uv run pytest -q` | 445 passed, 0 failed | ✓ PASS |
| CR-01 fix present in source | `grep -n "seed.get(" entity_hydrate_expand.py` | `raw_entity_name = seed.get("entity_name")` with `is None` guard confirmed | ✓ PASS |
| Parts registry count | live `LIGHTRAG_PARTS` import | 15 parts, `embedder-index` opaque/quarantined | ✓ PASS |
| Debt-marker scan | grep `TBD\|FIXME\|XXX` across evidence/parity/parts_core/clients/wirings | zero matches | ✓ PASS |
| Live 5-arm comparison currency | diff between commit 1827695's fix and committed `hybrid/local/global-comparison.json` stop_reason | Stop reason still names the pre-fix `KeyError` string the fix removed | ✗ FAIL — flagged as gap 2 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|--------------|--------|----------|
| MODAL-01 | 03-01, 02, 04–10 | LightRAG query side re-cut into primitive-part nodes with N-run variance-banded parity or declared deviations | ⚠️ PARTIALLY SATISFIED | Decomposition (17/18 positions) is real and complete. The parity-measurement half of MODAL-01 is real for `naive`/`bypass` only; `hybrid`/`local`/`global` (the graph-half arms) have no valid retrieval-level parity measurement yet, and the two recorded declared-deviation causes are AI- not human-authored. REQUIREMENTS.md line 29's own dated annotation (2026-09-02) already documents the graph-arm degradation as "a live defect surfaced by this comparison, not yet repaired" and correctly keeps the traceability row unchecked/`Pending` — that row has not been updated since CR-01 landed today, which is consistent with (not contradicted by) this verification. |
| MACH-02 | 03-03, 03-09 | Eval bundle (RIG §EV.1) | N/A for Phase 3 — correctly deferred to Phase 6 | Unchanged. |
| MACH-03 | 03-03, 03-09 | A/A calibration, Falsifier 5 | N/A for Phase 3 — correctly deferred to Phase 6 | Unchanged. |

No orphaned requirements — ROADMAP.md's Phase 3 requirements field lists only `MODAL-01`; MACH-02/MACH-03 appear in plan frontmatter only for the deferral-recording plans and REQUIREMENTS.md already attributes their substance to Phase 6.

### Anti-Patterns Found

None (debt-marker scan clean; no `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` in files touched by this phase's plans or its review-fix cycle).

### Code Review Findings Carried Into This Verification

`03-REVIEW.md` (2026-09-06, post-fix re-review, `status: issues_found`) has two open items not resolved by today's three fix commits:

- **WR-02** (requires human action, not a code change): `human_findings.json`'s two `declared_causes` entries are AI-authored. Carried into this verification as gap 1.
- **WR-04** (a fix or a re-run is needed): the committed parity evidence describes a crash CR-01 has since changed the behavior of, without any note that the code has moved since the evidence was rendered. Carried into this verification as gap 2.

Both were independently re-confirmed against current source/evidence in this verification session, not taken on the review's word.

### Gaps Summary

The phase made real, substantive progress since the prior verification: the v1 parity environment was rebuilt, a genuine five-arm live comparison ran, and the evidence-rendering machinery (G-03-1) that was previously completely broken (0-byte `PARITY-EVIDENCE.md`) now renders a real, derived document. The decomposition itself (criteria 1 and 3) remains solid and unchanged.

However, the phase's central claim — "parity ... is measured, not asserted" — does not yet hold across the board:

1. **The two recorded declared-deviation causes are AI-authored, not human-authored**, contradicting both CONTRACT §5 and the plan's own must-have truth. This is a self-acknowledged gap (03-10-SUMMARY.md calls it "MINOR"; the independent code review calls it a Warning requiring human action) that remains open.
2. **The committed evidence is stale relative to the current source.** Three fix commits landed on `main` today, including one (CR-01) that directly changes the behavior the evidence describes for `hybrid`/`local`/`global`. The evidence was never re-rendered after the fix, so it currently misdescribes what today's code does for 3 of 5 arms — and, separately, provides no information about whether the fix actually produces a real, completed retrieval for those arms.
3. **No valid retrieval-level parity measurement exists yet for `hybrid`/`local`/`global`.** Their recorded "zero diff" is both sides retrieving nothing (a crash on one side, an empty answer on the other), which `PARITY-EVIDENCE.md`'s own Verdict section already states plainly is not evidence of parity. This affects the two arms (`hybrid`, `global`) that most directly exercise the graph-half decomposition this phase built.
4. **The human answer-substance spot-check (criterion 6) has still not been performed** — unchanged from the prior verification, now correctly re-pointed at the `naive` arm.

None of these are regressions — they are either newly measured (the environment gap closing let real problems surface that were previously masked by "cannot verify") or a currency problem introduced by today's own fix commits landing without a matching evidence re-render. A closure plan for this phase should: (a) re-run the comparison for `hybrid`/`local`/`global` now that CR-01 has landed and re-render the evidence, honestly reporting whatever that run actually measures; (b) route the human-authored-cause and answer-spot-check items to the owner explicitly, since no further code change closes either one.

---

_Verified: 2026-09-05T23:15:00Z_
_Verifier: Claude (gsd-verifier)_
