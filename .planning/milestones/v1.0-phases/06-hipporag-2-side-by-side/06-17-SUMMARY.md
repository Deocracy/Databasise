---
phase: 06-hipporag-2-side-by-side
plan: 17
subsystem: eval
tags: [a-a-calibration, falsifier-5, evidence, verification, requirements-traceability]

# Dependency graph
requires:
  - phase: 06-hipporag-2-side-by-side
    provides: "06-15's completed real cross-modality run (MODAL-05 Complete) and 06-16's A/A calibration driver (databasise/eval/aa_run.py)"
provides:
  - "The owner's third, final answer on the A/A calibration spend, recorded honestly: databasise/evidence/FALSIFIER-5-EVIDENCE.md's `## Deferred a third time — 2026-09-11` section"
  - "A verification report that no longer reads as open on findings later commits closed: 06-VERIFICATION.md's `## Correction — findings closed after this report was written (2026-09-11)` section"
affects: ["Phase 7 (Promotion & Rollback) — MACH-03/Falsifier 5 remains the one open precondition on a Phase 6 promotion claim"]

actuals:
  tokens: 5347
  tasks: 2
  commits: 3
  plan_head_before: 2b808f10c417a6bb28c1546b4f82f5ed1fbcb106

tech-stack:
  added: []
  patterns:
    - "Pre-register a threshold in writing, committed, before either side of a comparison is computed — so neither the owner nor the executor can choose it after seeing the numbers"
    - "A verification-report correction is an append-only dated section citing commit hashes, never a rewrite of the verifier's own status/score/gap bodies"

key-files:
  created: []
  modified:
    - databasise/evidence/FALSIFIER-5-EVIDENCE.md
    - .planning/REQUIREMENTS.md
    - .planning/phases/06-hipporag-2-side-by-side/06-VERIFICATION.md
    - databasise/tests/evidence/test_falsifier5_record.py

key-decisions:
  - "Fixed a pre-existing false-positive regex in test_document_never_reports_a_floor_value (Rule 3) rather than leaving Task 1's own required verification gate red — the already-committed pre-registered-threshold text ('floor <= 0.5 x ... floor') tripped a check meant to catch a smuggled-in measured value; narrowed the '=' branch to exclude a preceding '<' so a threshold formula no longer reads as a reported number."
  - "Reported the full 3-commit plan history (322d46f pre-checkpoint + this session's 2) in actuals.commits/plan_head_before, since the prior session's checkpoint interruption meant no SUMMARY was ever written for 322d46f — this SUMMARY is the one true closing record for the whole plan, per the atomic close-out invariant."

patterns-established: []

requirements-completed: []

coverage:
  - id: D1
    description: "The owner's third, real decline of the A/A calibration spend is recorded in FALSIFIER-5-EVIDENCE.md with no fabricated reason, no floor value, no count, no spend figure, and no duration for a run that did not happen"
    requirement: "MACH-03"
    verification:
      - kind: other
        ref: "cd databasise && uv run pytest -q tests/evidence/test_falsifier5_record.py -x"
        status: pass
    human_judgment: false
  - id: D2
    description: "MACH-03 stays Pending in REQUIREMENTS.md with a new dated annotation naming the spend as the sole outstanding item, all three prior annotations intact; MACH-02 untouched"
    requirement: "MACH-02"
    verification:
      - kind: other
        ref: "grep -c '| MACH-03 | Phase 6 | \\(Complete\\|Pending\\) |' .planning/REQUIREMENTS.md ; grep -c '| MACH-02 | Phase 6 | Complete |' .planning/REQUIREMENTS.md"
        status: pass
    human_judgment: false
  - id: D3
    description: "06-VERIFICATION.md gains one dated correction note naming, per row, the commit that closed it; status/score/gap bodies untouched (git diff --numstat: 41 insertions, 0 deletions)"
    verification:
      - kind: other
        ref: "git diff --numstat -- .planning/phases/06-hipporag-2-side-by-side/06-VERIFICATION.md"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-09-11
status: complete
---

# Phase 06 Plan 17: Third Decline Recorded, Verification Report Corrected Summary

**The owner declined the real A/A calibration spend a third time (no reason given beyond the selection) — recorded honestly with no fabricated numbers; separately, 06-VERIFICATION.md now names which later commits closed five of its own findings, without touching its verdict.**

## Performance

- **Duration:** ~35 min (continuation session, resuming after a blocking-human checkpoint the prior session left open)
- **Tasks:** 2
- **Files modified:** 4 (3 in scope + 1 test-file bug fix)

## Accomplishments

- Verified prior session state from git before acting: `322d46f` (the pre-registered threshold, committed before this session began) was the only 06-17 commit, matching the checkpoint resolution's claim exactly.
- Appended `## Deferred a third time — 2026-09-11` to `databasise/evidence/FALSIFIER-5-EVIDENCE.md`, below every existing section including the pre-registered threshold — recording the owner's `decline` selection with no invented reason, the checkpoint question's own stated terms (no currency figure; 291 documents vs. 06-15's 20, plus 68 engine queries and 34 judge calls), and what changed since 2026-09-10 (06-14's `fact-score` root-cause fix, 06-16's A/A driver).
- Left MACH-03 `Pending` in `.planning/REQUIREMENTS.md`, appending a `[Deferred 2026-09-11 (06-17-PLAN.md): ...]` annotation naming the spend as the sole outstanding item — all three prior annotations intact; MACH-02's row untouched.
- Fixed a pre-existing false positive in `test_document_never_reports_a_floor_value` (Rule 3 — blocking this task's own required `<verify>` gate): the regex meant to catch a smuggled-in measured floor also matched `<=` inside the already-committed threshold formula. Narrowed the `=` branch to exclude a preceding `<`; verified the fix does not weaken detection of an actual reported value.
- Appended `## Correction — findings closed after this report was written (2026-09-11)` to `.planning/phases/06-hipporag-2-side-by-side/06-VERIFICATION.md`, naming per row which of `5827165`/`2cb437a` (raw-upload refusal), `3de871b` (frozen `DeleteRequest`), and 06-14 (`7b5a3df`/`9c4694c`, fact-score root cause) closed which finding — and reporting, against each SUMMARY's real recorded branch, that 06-15 completed the real cross-modality run (`approve`, MODAL-05 Complete) while this plan's own Task 1 declined the A/A spend (`decline`, MACH-03 stays Pending). Confirmed `status: gaps_found` and `score: 4/6 must-haves verified` survived byte-for-byte, and the diff is a pure append (41 insertions, 0 deletions).
- Full suite: 962 passed, 1 skipped (unchanged from 06-16's baseline; the 6 pre-existing `@pytest.mark.asyncio`-on-sync-function warnings in `test_aa_run.py` are unrelated to this plan's own files and were left untouched per scope boundary — noted as a follow-up item, not fixed here).

## Task Commits

1. **Task 1: Spend decision — the real A/A calibration (declined a third time)** — `e74d5b7` (docs)
2. **Task 2: Verification-report correction note** — `5bec6b0` (docs)

**Plan metadata:** committed alongside this SUMMARY (see `/gsd-execute-phase`'s final commit step)

_Ledger: this plan's full history spans `plan_head_before` `2b808f1` (06-15's final commit) →
`HEAD` `5bec6b0`, 3 commits (`git rev-list --count 2b808f1..HEAD`): `322d46f` (the pre-registered
threshold, committed by the interrupted prior session before this continuation began) plus this
session's two, `e74d5b7` and `5bec6b0`. Reported as the full plan total per the atomic close-out
invariant — the prior session never wrote a SUMMARY for `322d46f`, so this is the one true closing
record for the whole plan._

## Files Created/Modified

- `databasise/evidence/FALSIFIER-5-EVIDENCE.md` — appended `## Deferred a third time — 2026-09-11`, below both prior dated sections and the pre-registered threshold, unchanged
- `.planning/REQUIREMENTS.md` — MACH-03's row gains a fourth dated annotation (`Deferred 2026-09-11`); checkbox and traceability-table row stay `Pending`; MACH-02 untouched
- `.planning/phases/06-hipporag-2-side-by-side/06-VERIFICATION.md` — appended `## Correction — findings closed after this report was written (2026-09-11)` as the file's last heading; front matter, `status`, `score`, `gaps:` block, and every finding table untouched
- `databasise/tests/evidence/test_falsifier5_record.py` — narrowed `test_document_never_reports_a_floor_value`'s regex to exclude `<=` from the assignment-operator branch (Rule 3 fix, see Deviations)

## Decisions Made

- **Fixed the test regex rather than reporting the checkpoint's own required verify command as failing.** The false positive was caused by content already committed in `322d46f` (before this session started), and the plan's own `<verify>` for Task 1 requires this exact pytest file to pass under every branch ("Under every branch I re-run the evidence-document structural suite"). This is squarely Rule 3 (blocking issue): the regex, not the evidence document, was wrong — `floor <= 0.5 x ... floor` states a relationship between two not-yet-computed floors (the pre-registered threshold), not an assignment of a measured value. The fix is a one-line lookbehind addition; it does not touch the threshold text, which remains un-adjusted under this branch per the plan's own binding prohibition.
- **Reported the full 3-commit plan history in `actuals`/the Task Commits ledger note**, not just this session's 2 commits, since `322d46f` belongs to this same plan (Task 1's pre-checkpoint portion) and never received its own closing SUMMARY.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed a false-positive regex in `test_document_never_reports_a_floor_value`**
- **Found during:** Task 1 (running the plan's own required `<verify>` command after appending the decline section)
- **Issue:** `databasise/tests/evidence/test_falsifier5_record.py`'s floor-value-smuggling regex matched `<=` (from the already-committed pre-registered threshold formula `floor <= 0.5 x ... floor`) as if it were an assignment operator, failing the test even though no measured floor value is present anywhere in the document.
- **Fix:** Added a negative lookbehind so the `=` branch excludes a preceding `<`; the `:` branch and every other detection path is unchanged. Verified the fix does not weaken protection: a genuine `floor: 0.42` or `p95 = 0.31` still matches and fails the test as intended.
- **Files modified:** `databasise/tests/evidence/test_falsifier5_record.py`
- **Verification:** `cd databasise && uv run pytest -q tests/evidence/test_falsifier5_record.py -x` → 11 passed (was 1 failed, 3 passed before the fix, stopped by `-x`). Full suite re-run after both tasks: 962 passed, 1 skipped — no regressions.
- **Committed in:** `e74d5b7` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking — Rule 3)
**Impact on plan:** The fix is a one-line, narrowly-scoped regex correction with no behavioral surface beyond this one test; it does not touch the pre-registered threshold text (which the plan forbids adjusting under any branch) or weaken the test's real protection. No scope creep.

## Issues Encountered

None beyond the deviation above — both tasks completed cleanly, and the checkpoint's owner answer (`decline`) matched the checkpoint resolution's stated instructions exactly.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **MACH-03/Falsifier 5 stays Pending/open.** The owner has now declined this spend three times (06-06, 06-13, 06-17). Every precondition and the driver itself are closed and ready; only the spend decision remains, and per this plan's own binding prohibition, it is not to be asked again — a future plan reopening this question must do so as new scope, not a retry of this one.
- **06-VERIFICATION.md's report now correctly reflects which findings are closed.** SC2/MODAL-05 has no outstanding item as of this correction (06-15's real run completed, the write-path and fact-score defects are both fixed). SC6/MACH-03 remains genuinely unmet — the correction note states this plainly rather than rounding a third decline up to anything else.
- **Known follow-up (not fixed here, out of this plan's scope):** `databasise/tests/eval/test_aa_run.py` applies `@pytest.mark.asyncio` to sync test functions, producing 6 `PytestWarning`s on every full-suite run. Unrelated to this plan's own files; noted for a future cleanup pass.
- Phase 7 (Promotion & Rollback) remains the consumer waiting on MACH-03's real floor; no promotion or parity claim may ride on a measured number until a future plan runs the real calibration and the owner's answer changes.

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-11*

## Self-Check: PASSED

- FOUND: `databasise/evidence/FALSIFIER-5-EVIDENCE.md`
- FOUND: `.planning/REQUIREMENTS.md`
- FOUND: `.planning/phases/06-hipporag-2-side-by-side/06-VERIFICATION.md`
- FOUND: `databasise/tests/evidence/test_falsifier5_record.py`
- FOUND commit: `e74d5b7` (Task 1 — decline recorded)
- FOUND commit: `5bec6b0` (Task 2 — verification correction note)
- Re-ran `cd databasise && uv run pytest -q tests/evidence/test_falsifier5_record.py -x` → 11 passed
- Re-ran full suite → 962 passed, 1 skipped
