---
phase: 06-hipporag-2-side-by-side
plan: 06
subsystem: eval
tags: [scipy, bootstrap, calibration, eval-bundle, falsifier-5, mach-03, evidence]

# Dependency graph
requires:
  - phase: 06-04
    provides: bundle@v1 (30-question corpus, both §EV.2 target families, judge_instance recorded as "unresolved")
provides:
  - "databasise/eval/calibration.py — the A/A calibration procedure (calibrate_aa_floor, CalibrationResult, NullIdentity, UnusableFloorError, StaleNullError, paired_differences, correct_for_batch_width), both §AA preconditions enforced as code refusals"
  - "databasise/evidence/FALSIFIER-5-EVIDENCE.md — Falsifier 5 recorded as BLOCKED (not discharged), both blockers and both entry preconditions named, no floor value claimed"
affects: [07-promotion-rollback]

# Actuals (#2632)
actuals:
  tokens: 22105
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: ["scipy>=1.11"]
  patterns:
    - "D-02 pre-flight-verification harness shape (mirrors run_comparison.py): verify a hard precondition before trusting any computed number, never compute-then-caveat"
    - "House-format BLOCKED evidence record: same house format as FALSIFIER-2/4-EVIDENCE.md (dated header, verbatim pass-criterion quote, findings table, verdict/status, method-and-limits) applied to an unrun falsifier rather than a passing or failing one"

key-files:
  created:
    - databasise/eval/calibration.py
    - databasise/tests/eval/test_calibration.py
    - databasise/evidence/FALSIFIER-5-EVIDENCE.md
    - databasise/tests/evidence/test_falsifier5_record.py
  modified:
    - databasise/eval/__init__.py
    - databasise/pyproject.toml
    - databasise/tests/test_embed_startup.py
    - .planning/config.json

key-decisions:
  - "Owner decision at Task 2's blocking-human checkpoint: defer-run. No real A/A calibration executes in this plan — no corpus ingested, no LLM calls made, no spend incurred. Both T0 (answer-level) and T1 (gold-passage) legs stay unrun."
  - "Task 3 adapted from a passing-verdict record to a BLOCKED record, per the owner's explicit instruction — an authorized deviation from the plan's literal text, not an executor judgment call."
  - "No numeric threshold for 'materially narrower' is pre-registered in this plan's evidence record, since there are no floors to compare it against; 06-RESEARCH's default (T1 floor at most half of T0's) remains the standing recommendation for whichever plan runs the real calibration."
  - "MACH-03 left Pending in REQUIREMENTS.md — this plan discharges the calibration instrument (Task 1) and the honest blocked-record (Task 3-adapted), not the calibration itself."

patterns-established:
  - "A BLOCKED evidence record is written in the same house format as a passing/failing one (dated header, verbatim requirement quote, findings table, status, method-and-limits) — a reader does not have to learn a second document shape to recognize an honestly-unrun falsifier."

requirements-completed: []

coverage:
  - id: D1
    description: "The A/A calibration procedure exists with both §AA preconditions (cache-bypass, staleness) enforced as code refusals, and its boundary/staleness rules pinned by fixture tests"
    requirement: MACH-03
    verification:
      - kind: unit
        ref: "tests/eval/test_calibration.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Falsifier 5 is recorded as BLOCKED, not discharged — both blockers (unresolved judge identity, unbudgetable eval-corpus ingest) and both entry preconditions are named verbatim and verifiably, and no floor value is claimed anywhere in the record"
    verification:
      - kind: unit
        ref: "tests/evidence/test_falsifier5_record.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "A real A/A calibration run against bundle@v1, producing two committed floors at T0 and T1"
    verification: []
    human_judgment: true
    rationale: "Deliberately not run this plan (owner's defer-run decision) — requires a resolved judge identity and a cost-bounded corpus-ingest path, neither of which exists yet. Not a deliverable of this plan; recorded here only so its absence is explicit rather than silently unmentioned."

# Metrics
duration: ~20min (continuation session; Task 1 landed in a prior session)
completed: 2026-09-09
status: complete
---

# Phase 6 Plan 6: A/A Calibration Instrument Built, Real Calibration Deliberately Deferred (Falsifier 5 BLOCKED)

**The A/A calibration procedure (`calibrate_aa_floor`, bootstrap-resampled p95 floor, both §AA preconditions enforced as code refusals) is built and tested against fixtures; the owner deferred the real calibration run at its spend/judge-identity checkpoint, so Falsifier 5/MACH-03 is recorded honestly as BLOCKED rather than passed, failed, or silently skipped.**

## Performance

- **Duration:** ~20 min this session (continuation after a prior-session Task 1; full plan spanned two sessions)
- **Tasks:** 2 of 3 planned tasks executed as code (Task 1 fully; Task 3 adapted); Task 2 deliberately not executed
- **Files modified:** 8 (databasise/ scope, this session's commit)

## Accomplishments

- `databasise/eval/calibration.py`: `calibrate_aa_floor`, `CalibrationResult`, `NullIdentity`, `UnusableFloorError`, `StaleNullError`, `paired_differences`, `correct_for_batch_width` — the full §AA.1/§AA.2/§AA.3 procedure, with the cache-bypass and staleness preconditions enforced as hard refusals rather than warnings, pinned by 15 fixture tests including a negative control proving the bootstrap reads real data rather than returning a constant (Task 1, prior session).
- `databasise/evidence/FALSIFIER-5-EVIDENCE.md`: an honest BLOCKED record — Falsifier 5/MACH-03 explicitly NOT discharged, no floor computed, no p95, no `NullIdentity` minted with a real value — naming both blockers verbatim (bundle@v1's `judge_instance` recorded `"unresolved"`; the 291-document eval-corpus's `unbudgetable` full-ingest cost) and both entry preconditions for a future run.
- `databasise/tests/evidence/test_falsifier5_record.py`: 11 structural tests pinning the BLOCKED shape — asserts the document names both blockers and both preconditions, and never reports a numeric floor/p95 value anywhere in its body.

## Task Commits

Each executed task was committed atomically:

1. **Task 1: The calibration procedure, with its two preconditions enforced in code** - `28524d7` (test — TDD, prior session)
2. **Task 2: Run one real A/A calibration at both target families** — NOT EXECUTED. The owner selected `defer-run` at this task's own `gate="blocking-human"` spend/judge-identity checkpoint. No commit exists for this task by design.
3. **Task 3 (adapted): Falsifier 5's BLOCKED verdict, not a passing/failing one** - `c5a6d4f` (test)

_Note: Task 1 used the full RED→GREEN→REFACTOR TDD cycle per its `tdd="true"` frontmatter; see its own prior-session commit for that history._

## Files Created/Modified

- `databasise/eval/calibration.py` - The A/A calibration procedure (Task 1, prior session)
- `databasise/eval/__init__.py` - Package init for the new `eval` module (Task 1, prior session)
- `databasise/pyproject.toml` - Added `scipy>=1.11` dependency (Task 1, prior session)
- `databasise/tests/eval/test_calibration.py` - 15 fixture tests for the calibration procedure (Task 1, prior session)
- `databasise/tests/test_embed_startup.py` - Rule 3 fix: pinned dependency count 8→9 after `scipy` landed (Task 1, prior session)
- `.planning/config.json` - Rule 3 fix: documented `git.allow_default_branch_commits` (Task 1, prior session)
- `databasise/evidence/FALSIFIER-5-EVIDENCE.md` - Falsifier 5 BLOCKED record (this session)
- `databasise/tests/evidence/test_falsifier5_record.py` - Structural tests pinning the BLOCKED shape (this session)

## Decisions Made

- **Owner decision: `defer-run`.** Presented with Task 2's own `gate="blocking-human"` checkpoint (T0 blocked by `bundle@v1`'s unresolved judge identity; T1 blocked by the un-budgeted cost of ingesting a 291-document corpus through the opaque v1 `full-ingest` path), the owner selected `defer-run` rather than running either leg. No corpus was ingested, no LLM calls were made, no spend was incurred.
- **Task 3 adapted to the blocked reality**, on the owner's explicit instruction — the evidence record and its test assert a BLOCKED shape, never a passing-verdict shape borrowed from the plan's original literal text. This is an authorized deviation, not an executor judgment call: see Deviations below.
- **No numeric "materially narrower" threshold is pre-registered** in this plan's evidence record — there is nothing to pre-register a threshold against when no floors exist. `06-RESEARCH.md`'s Open Question 1 default (T1's p95 floor at most half of T0's) remains the standing recommendation, unadopted and unrejected by this document, for whichever future plan runs the real calibration.
- **MACH-03 stays Pending in `.planning/REQUIREMENTS.md`.** This plan discharges the calibration instrument and an honest blocked-record of why the calibration itself has not run — not MACH-03 itself.

## Deviations from Plan

### Owner-Authorized Deviations

**1. [Owner-directed — not a Rule 1-4 auto-fix] Task 2 not executed; Task 3's shape adapted from passing-verdict to BLOCKED-verdict**
- **Found during:** Task 2's own precondition/checkpoint gate
- **Issue:** Task 2's action text required running a real A/A calibration at both §EV.2 target families. At execution time, both legs were genuinely blocked: T0 (answer-level) cannot run because `bundle@v1` records `judge_instance: "unresolved"` and the plan's own text forbids substituting a judge; T1 (gold-passage) requires ingesting a fresh 291-document corpus through the opaque v1 `full-ingest` path at real, un-budgeted (`unbudgetable`-accounted) spend.
- **Resolution:** Presented as a `gate="blocking-human"` checkpoint per the executor's own precondition-unmet protocol (never auto-approved, even under `--auto`). The owner, in a prior turn of this same continuation, selected `defer-run`: skip the real run entirely, close this plan with Task 1's procedure as the delivered artifact, and record Falsifier 5 as honestly BLOCKED rather than passed, failed, or silently omitted. Task 3's acceptance criteria (originally written for a two-floor comparison table and a pre-registered numeric threshold) were adapted accordingly — the findings table now carries one row per *blocker*, not per calibrated result, and the document states plainly that no floor value is reported anywhere in it.
- **Files modified:** `databasise/evidence/FALSIFIER-5-EVIDENCE.md`, `databasise/tests/evidence/test_falsifier5_record.py`
- **Verification:** `uv run pytest -q tests/evidence/test_falsifier5_record.py` (11 passed); full suite `uv run pytest -q` (855 passed, 1 skipped)
- **Committed in:** `c5a6d4f`

---

**Total deviations:** 1 owner-authorized (Task 2 skipped, Task 3 shape adapted). Task 1 also carried two Rule 3 auto-fixes (dependency-count pin, config documentation) — see `28524d7`'s own prior-session record.
**Impact on plan:** Falsifier 5/MACH-03 is not discharged by this plan. No fabricated or estimated floor value exists anywhere in the committed record. The blocked state is fully explicit and machine-checked (`test_falsifier5_record.py` fails if the document ever silently claims a floor).

## Issues Encountered

None beyond the checkpoint itself, which is documented above as an owner-authorized deviation rather than an issue.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **The calibration instrument is ready** for whichever future plan runs the real A/A calibration — `databasise/eval/calibration.py` needs no further code changes to accept a real run's data.
- **The real A/A calibration run is deferred to a later plan.** Its entry criteria are the two preconditions named in `FALSIFIER-5-EVIDENCE.md`: (1) a resolved judge identity in the bundle (bundle@v1 re-minted with a real, live-resolved `judge_instance`, never a substituted declared id), and (2) a cost-bounded indexing story for the 291-document eval-corpus (an ingest path whose spend is bounded or explicitly budgeted, rather than the opaque v1 path's `unbudgetable` accounting).
- **Phase 7 (Promotion & Rollback) is the consumer that will need this floor** — `.planning/ROADMAP.md`'s Ordering Constraints state the eval bundle and A/A floor must stand up "before any promotion or parity claim rides on a measured number." No promotion or parity claim in Phase 7 may proceed until `FALSIFIER-5-EVIDENCE.md` is superseded by a real calibration record carrying two real committed floors.
- **MACH-03 remains Pending** in `.planning/REQUIREMENTS.md` and is not marked complete by this plan.
- Wave 3 of Phase 6 is now complete (06-05 and this plan, 06-06); Wave 4 (`06-07-PLAN.md`) is unblocked.

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-09*
