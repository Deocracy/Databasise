---
status: testing
phase: 03-lightrag-query-side
source: [03-VERIFICATION.md]
started: 2026-09-01T22:36:05Z
updated: 2026-09-01T23:59:00Z
---

## Current Test

number: 2
name: Human spot-check of answer substance for the two corpus queries
expected: |
  With the v1 environment and imported index present, run q1 and q2 through `databasise.parity.run_comparison --arm hybrid` and through v1 directly, read both answers side by side, and record a match / no-match judgment with notes for each query pair.
awaiting: user response

## Tests

### 1. Live five-arm parity comparison after rebuilding the v1 environment
expected: Rebuild the v1 pinned environment (v1/README-PARITY.md), re-run v1's real ingest to produce v1/.venv, v1/.parity_working_dir, v1/.parity_v2_store, v1/.env.parity, then re-run `databasise.parity.run_comparison` for all five arms and `databasise.evidence.parity_report` to render PARITY-EVIDENCE.md. Each arm's status flips from `inconclusive` to `completed` with a real N=5 keyword variance band and real sym_diff numbers, or every out-of-tolerance excursion is named in DECLARED-DEVIATIONS.md.
result: issue
reported: "Live run succeeded (all 5 arms completed, real N=5 variance bands, hybrid/local/global sym_diff=0, storage audits clean) but PARITY-EVIDENCE.md cannot render: naive arm's tail-truncation excursions (sym_diff=2/4, agreement=1.000, first_disagreement=10) need a named cause and parity_report.py has no mechanism to accept one (_collect_deviations hardcodes cause=\"\"); prose sections also hardcode the environment-refusal narrative, now false. User: mark as issue."
severity: major

### 2. Human spot-check of answer substance for the two corpus queries
expected: With the v1 environment and imported index present, run q1 and q2 through `databasise.parity.run_comparison --arm hybrid` and through v1 directly, read both answers side by side, and record a match / no-match judgment with notes for each query pair.
result: [pending]
landing place: `databasise/evidence/human_findings.json`'s `answer_spotchecks` list (03-10-PLAN.md Task 3) — read and rendered by `databasise/evidence/parity_report.py`'s `_render_answer_spotcheck()` into `PARITY-EVIDENCE.md`'s "Human spot-check of answer substance" section, per query, on every render. Both q1 and q2 currently render as explicitly unrecorded; this test closes once an entry is added and the document re-rendered.

## Summary

total: 2
passed: 0
issues: 1
pending: 1
skipped: 0
blocked: 0

## Gaps

- gap_id: G-03-1
  truth: "PARITY-EVIDENCE.md and DECLARED-DEVIATIONS.md render from a completed live comparison, with every out-of-tolerance excursion individually named with a specific cause (CONTRACT §5)"
  status: failed
  reason: "User reported: renderer cannot produce the evidence documents from the first completed run — _collect_deviations() in databasise/evidence/parity_report.py hardcodes cause=\"\" with no input mechanism for a human-supplied cause (render raises UnreasonedDeviationError, and manual edits to DECLARED-DEVIATIONS.md are overwritten on next render); prose sections (What was compared, storage-audit narrative, What is not measured, Verdict) hardcode the environment-precondition-refusal narrative, which is false for a completed run. Known cause awaiting recording: naive arm sym_diff=2 (q1) / 4 (q2) is v1 naive returning tail chunks beyond top_k=10 under token-budget truncation while the decomposed chunk-vector node cuts strictly at top_k; ranking agreement 1.000, first_disagreement=10."
  severity: major
  test: 1
  status_update: "2026-09-02, 03-10-PLAN.md: closed. human_findings.json's declared_causes now supplies a grounded, human-authored cause for each of naive's two per-query excursions; parity_report.py's prose sections all derive from the completed-run records instead of the pre-run refusal narrative. PARITY-EVIDENCE.md and DECLARED-DEVIATIONS.md both render non-empty from the committed completed results. New finding surfaced by this fix (not part of G-03-1, recorded in REQUIREMENTS.md's MODAL-01 annotation and PARITY-EVIDENCE.md's Verdict): hybrid/local/global's decomposed runs degraded before completing retrieval, so their measured zero diffs are not yet a validated match — left unrepaired, out of this plan's scope."
  artifacts:
    - databasise/evidence/human_findings.json
    - databasise/evidence/parity_report.py
    - databasise/evidence/PARITY-EVIDENCE.md
    - databasise/evidence/DECLARED-DEVIATIONS.md
    - databasise/tests/parity/test_parity_evidence.py
  missing:
    - "hybrid/local/global's entity-hydrate-expand/relation-hydrate-expand NodeExecutionError (degraded run, not yet repaired — see PARITY-EVIDENCE.md's per-arm degradation notes and Verdict)"
    - "the human answer-substance spot-check for q1/q2 (test 2 below — landing place now exists, judgment not yet recorded)"
