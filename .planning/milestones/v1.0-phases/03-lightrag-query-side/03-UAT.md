---
status: testing
phase: 03-lightrag-query-side
source: [03-VERIFICATION.md]
started: 2026-09-01T22:36:05Z
updated: 2026-09-06T00:00:00Z
audit_acknowledged:
  milestone: v1.0
  at: 2026-09-12
  gap_snapshot: "testing::scenarios=2"
---

## Current Test

number: 3
name: CONTRACT §5 human-authored declared-deviation causes
expected: |
  Replace the two existing AI-authored `declared_causes` entries in `databasise/evidence/human_findings.json` with your own reasoning, and add a `declared_causes` entry for each of the 18 newly-measured `hybrid`/`local`/`global` excursions that currently render as `PENDING` in `DECLARED-DEVIATIONS.md`'s "Outstanding" section. See Test 3 below for the exact command, file, and field names.
awaiting: user response

## Tests

### 1. Live five-arm parity comparison after rebuilding the v1 environment

expected: Rebuild the v1 pinned environment (v1/README-PARITY.md), re-run v1's real ingest to produce v1/.venv, v1/.parity_working_dir, v1/.parity_v2_store, v1/.env.parity, then re-run `databasise.parity.run_comparison` for all five arms and `databasise.evidence.parity_report` to render PARITY-EVIDENCE.md. Each arm's status flips from `inconclusive` to `completed` with a real N=5 keyword variance band and real sym_diff numbers, or every out-of-tolerance excursion is named in DECLARED-DEVIATIONS.md.
result: issue
reported: "Live run succeeded (all 5 arms completed, real N=5 variance bands, hybrid/local/global sym_diff=0, storage audits clean) but PARITY-EVIDENCE.md cannot render: naive arm's tail-truncation excursions (sym_diff=2/4, agreement=1.000, first_disagreement=10) need a named cause and parity_report.py has no mechanism to accept one (_collect_deviations hardcodes cause=\"\"); prose sections also hardcode the environment-refusal narrative, now false. User: mark as issue."
severity: major
status_update: "2026-09-06, 03-13-PLAN.md: the graph-arm crash this test's own G-03-1 follow-on named (hybrid/local/global's entity-hydrate-expand/relation-hydrate-expand NodeExecutionError) is now repaired (03-11/03-12) and a fresh five-arm run against that fixed source is committed. All five arms complete a real, non-degraded retrieval on both sides — see test 3 below for what that run actually measured and what remains outstanding."

### 2. Human spot-check of answer substance for the two corpus queries

expected: With the v1 environment and imported index present, run q1 and q2 through `databasise.parity.run_comparison --arm naive` and through v1 directly, read both answers side by side, and record a match / no-match judgment with notes for each query pair.
result: [pending]
landing place: `databasise/evidence/human_findings.json`'s `answer_spotchecks` list (03-10-PLAN.md Task 3) — read and rendered by `databasise/evidence/parity_report.py`'s `_render_answer_spotcheck()` into `PARITY-EVIDENCE.md`'s "Human spot-check of answer substance" section, per query, on every render. Both q1 and q2 currently render as explicitly unrecorded; this test closes once an entry is added and the document re-rendered.
arm correction (2026-09-03, 03-10 fix cycle finding 5): the `expected` field above now names `--arm naive`, not `--arm hybrid` as originally written. `hybrid`/`local`/`global`'s decomposed runs degrade before reaching `generate` (`entity-hydrate-expand`/`relation-hydrate-expand` raise `NodeExecutionError`; see `PARITY-EVIDENCE.md`'s per-arm degradation notes and Verdict section), so none of the three ever produces a decomposed-side answer — v1's own answer for those pairs is also `"…[no-context]"`. Recording a judgment against `hybrid` today would mean judging two non-answers. `naive` is the arm whose pipeline completed end to end on both sides; this test stays `[pending]` (no judgment recorded by this fix cycle — that stays a human decision) until the owner performs the read against `naive` per `03-VALIDATION.md`'s corrected Manual-Only Verifications row, or the graph-arm crash is repaired and this row is re-pointed back.
arm status update (2026-09-06, 03-13-PLAN.md): the graph-arm crash named above is now repaired (03-11/03-12) — `hybrid`, `local`, and `global` all complete a real, non-degraded retrieval and produce a real generated answer on both sides too, so the "repaired" branch of the sentence above now applies. **The `naive` recommendation below is unchanged, kept for continuity and simplicity, not because the others are unavailable:**

- **Exact command (decomposed side, naive arm):**
  ```
  cd databasise
  set -a && . ../v1/.env.parity && set +a
  uv run python -m databasise.parity.run_comparison --arm naive
  ```
  The decomposed side's generated answer is not persisted in the run record — read it from this command's own stdout (the `[result] JSON result written to: ...` line's preceding human summary does not print the answer text either; capture the live LLM response as the command runs, or add a temporary print in a local copy — the harness does not currently commit this text anywhere).
- **Exact command (original v1 side):** the same query text, run directly against v1's own driver: `uv run python v1/scripts/run_parity_ingest.py`'s sibling query path is not the one to use for a read-only query — instead read the already-recorded answer at `databasise/evidence/parity_results/naive-comparison.json`'s `original_arm_result.answer` field for each query (`q1`, `q2`) — this is v1's real, already-captured answer from the same comparison run, requiring no second live call.
- **Exact JSON fields to add**, one object per query, to `human_findings.json`'s `answer_spotchecks` list (currently `[]`):
  ```json
  {
    "query_id": "q1",
    "arm": "naive",
    "judgment": "match",
    "notes": "<your own read of how the two answers compare>",
    "recorded_by": "<your name/identity>",
    "recorded_at": "<ISO date>"
  }
  ```
  `judgment` must be exactly one of `match`, `no-match`, `partial` (`parity_report.py`'s `InvalidJudgmentError` refuses anything else). Repeat for `query_id: "q2"`.
- **Re-render after editing:** `cd databasise && uv run python -m databasise.evidence.parity_report` — this re-renders `PARITY-EVIDENCE.md`'s "Human spot-check of answer substance" section from the new entries.

### 3. CONTRACT §5 human-authored declared-deviation causes

expected: |
  Every `declared_causes` entry in `databasise/evidence/human_findings.json` carries a cause the human owner (christopher@deocracy.org) personally holds, with `recorded_by` naming the owner, not an AI agent — CONTRACT §5's parity-not-gain rule requires a human-authored cause for each named excursion, and none on file today qualifies.
result: [pending]
landing place: `databasise/evidence/human_findings.json`'s `declared_causes` list, read and rendered by `databasise/evidence/parity_report.py`'s `render_deviations_document()` into `DECLARED-DEVIATIONS.md`'s "Named deviations" table (once caused) or its "Outstanding" section (while still pending).
details: |
  Two separate things are pending here, both requiring the owner's own reasoning:

  **(a) Two existing entries need the owner's own reasoning, not AI's.** `human_findings.json` today has two `declared_causes` entries (naive/q1/chunk_diff, naive/q2/chunk_diff), both `recorded_by: "Claude (AI agent, gsd-code-fixer) — commit 2ce3c30; NOT recorded by the human owner, despite this file's own name"`. The existing `cause` text is available to read (it is a technically-grounded explanation: v1's naive path keeps chunks past rank 10 under token-budget truncation while the decomposed `chunk-vector` node cuts strictly at `top_k=10`) but it is **not an answer to approve by leaving it as-is** — a cause the owner does not personally hold and re-record under their own `recorded_by` is not a CONTRACT §5 cause, however technically accurate its text is.

  **(b) 18 newly-measured excursions on `hybrid`/`local`/`global` have no cause at all yet** (03-13-PLAN.md's re-run — these did not exist in the prior committed evidence because those three arms previously crashed before producing any retrieval to compare). Full symmetric-difference lists for each are in `DECLARED-DEVIATIONS.md`'s "Outstanding — CONTRACT §5 cause not yet recorded" section; counts only, here, for orientation:

  | arm | query | field | count |
  |---|---|---|---|
  | hybrid | q1 | chunk_diff | 2 |
  | hybrid | q1 | entity_diff | 58 |
  | hybrid | q1 | relation_diff | 60 |
  | hybrid | q2 | chunk_diff | 5 |
  | hybrid | q2 | entity_diff | 46 |
  | hybrid | q2 | relation_diff | 44 |
  | local | q1 | chunk_diff | 4 |
  | local | q1 | entity_diff | 20 |
  | local | q1 | relation_diff | 33 |
  | local | q2 | chunk_diff | 4 |
  | local | q2 | entity_diff | 22 |
  | local | q2 | relation_diff | 30 |
  | global | q1 | chunk_diff | 8 |
  | global | q1 | entity_diff | 76 |
  | global | q1 | relation_diff | 78 |
  | global | q2 | chunk_diff | 8 |
  | global | q2 | entity_diff | 68 |
  | global | q2 | relation_diff | 68 |

  These are large enough (tens of entity/relation ids per query) that a per-item cause is unlikely to be practical for every single id; a single cause per (arm, query, field) row — naming the *class* of disagreement (e.g. "v2's shared query-vector embed vs v1's two separate keyword-derived vectors changes which graph neighborhood each side retrieves — see DECLARED-DEVIATIONS.md's Known design deviation section") — is exactly what the existing `cause` field is for. The owner may also conclude some of these are not tolerable variance at all but a real defect needing further engineering investigation before any cause can be written truthfully; that judgment is exactly what this test routes to the owner, not an outcome this plan may assume.

  **Exact file to edit:** `databasise/evidence/human_findings.json`

  **Exact JSON shape**, one object per `(arm, query_id, field)` row above, appended to (or replacing, for the two existing naive entries) the `declared_causes` list:
  ```json
  {
    "arm": "hybrid",
    "query_id": "q1",
    "field": "chunk_diff",
    "symmetric_difference": ["lord_high_treasurer-chunk-000", "village_accountant-chunk-000"],
    "cause": "<your own reasoning>",
    "recorded_by": "<your name/identity>",
    "recorded_at": "<ISO date>"
  }
  ```
  `symmetric_difference` must be copied verbatim from the matching row in `DECLARED-DEVIATIONS.md`'s "Outstanding" table or from `databasise/evidence/parity_results/{arm}-comparison.json`'s own `{field}.symmetric_difference` — `parity_report.py` raises `StaleDeviationCauseError` if it does not exactly match what was measured (a safeguard against a cause silently surviving a re-run that changed the underlying numbers).

  **Re-render after editing:** `cd databasise && uv run python -m databasise.evidence.parity_report` — a caused entry moves from `DECLARED-DEVIATIONS.md`'s "Outstanding" section into its "Named deviations" table; an entry still missing a cause (or with a blank/generic one) stays in "Outstanding", never silently dropped.

## Summary

total: 3
passed: 0
issues: 1
pending: 2
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
    - "hybrid/local/global's entity-hydrate-expand/relation-hydrate-expand NodeExecutionError (degraded run, not yet repaired — see PARITY-EVIDENCE.md's per-arm degradation notes and Verdict) — RESOLVED 2026-09-06 by 03-11/03-12; see G-03-2 for what the resulting real comparison surfaced in its place"
    - "the human answer-substance spot-check for q1/q2 (test 2 below — landing place now exists, judgment not yet recorded) — still open, see test 2"

- gap_id: G-03-2
  truth: "Every measured retrieval-level excursion on a completed, non-degraded comparison run carries a CONTRACT §5 human-authored cause before it is read as accepted variance"
  status: failed
  reason: "03-13-PLAN.md's fresh five-arm run (HEAD cee485f) closed G-03-1's own follow-on gap: hybrid/local/global's crash is repaired and all three now complete a real, non-degraded retrieval on both sides. But that real retrieval disagrees substantially with the original arm — 18 excursions across the three arms' two queries and three diff fields (chunk/entity/relation), none carrying a declared_causes entry. render_deviations_document() (this plan's own fix to render_deviations_markdown()'s all-or-nothing refusal, which stays untouched and correct) renders every one of them honestly as PENDING in DECLARED-DEVIATIONS.md's Outstanding section rather than fabricating a cause or silently dropping them — but PENDING is not the same as CONTRACT §5-satisfied, and REQUIREMENTS.md's MODAL-01 traceability row stays Pending until they are."
  severity: major
  test: 3
  artifacts:
    - databasise/evidence/human_findings.json
    - databasise/evidence/DECLARED-DEVIATIONS.md
    - databasise/evidence/PARITY-EVIDENCE.md
    - .planning/REQUIREMENTS.md
  missing:
    - "18 declared_causes entries (see test 3's table above for the exact arm/query/field/count breakdown), each with the owner's own reasoning and recorded_by"
    - "the two existing naive declared_causes entries re-recorded under the owner's own recorded_by, replacing the AI-authored text (WR-02, 03-REVIEW.md — unresolved, carried forward from G-03-1)"
