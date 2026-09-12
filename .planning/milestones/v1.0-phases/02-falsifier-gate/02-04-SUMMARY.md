---
phase: 02-falsifier-gate
plan: 04
subsystem: planning
tags: [gate-01, waiver, roadmap, requirements, re-scope, selection-md]
dependency graph:
  requires:
    - phase: 02-falsifier-gate
      provides: "02-01's committed FALSIFIER-2-EVIDENCE.md and 02-03's self-declaration/probe-suite evidence that Falsifier 2 did not fire"
  provides:
    - ".planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md — the written, cited, scoped amendment to SELECTION.md's Falsifier 5 timing, GATE-01's deliverable"
    - "ROADMAP.md and REQUIREMENTS.md re-scoped so MACH-02/MACH-03 sit with Phase 3 and HARD-01/HARD-02 sit with Phase 7"
  affects:
    - "phase-3-lightrag-query-side (inherits MACH-02/MACH-03 and the banked eval-run decisions D-06..D-13)"
    - "phase-7-promotion-rollback (inherits HARD-01/HARD-02)"
tech-stack:
  added: []
  patterns:
    - "amendment-by-citation: the frozen upstream mirror (docs/system-model/) is never edited; the project's own layer quotes it and amends via a dated, cited record"
key-files:
  created:
    - .planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md
  modified:
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md
decisions:
  - "Falsifier 2 is satisfied now (evidence: databasise/evidence/FALSIFIER-2-EVIDENCE.md); Falsifier 5 moves to Phase 3's parity comparison, the point of first need, per D-01"
  - "A Falsifier 2 failure still halts the ladder as a SELECTION.md-level reversal — the waiver amends timing, not the halt condition"
  - "Phase 3's substitute parity gate until the A/A floor exists: deterministic retrieval-level comparison plus human spot-checks (D-05), added as Phase 3 success criterion 6"
  - "Phase 3 criterion 2's 'inside Phase 2's A/A floor' language corrected to reference this phase's own calibrated floor (criterion 5), since the floor's calibration moved into Phase 3 alongside it — a doc-consistency fix required by moving MACH-03 into this phase, not a separately scoped edit"
metrics:
  duration: "~15 min"
  completed: 2026-08-31
status: complete
actuals:
  tokens: 5100
  tasks: 3
  commits: 3
---

# Phase 2 Plan 04: GATE-01 Waiver + ROADMAP/REQUIREMENTS Re-scope Summary

Recorded GATE-01's deliverable — the written owner decision amending SELECTION.md's Falsifier 5
timing — and re-scoped ROADMAP.md and REQUIREMENTS.md so coverage tracking matches the phase that
was actually planned and executed (Falsifier 2 evidence + MACH-09 posture + the waiver itself),
with MACH-02/MACH-03 moved to Phase 3 and HARD-01/HARD-02 moved to Phase 7.

## What Was Built

**Task 1 — the waiver record** (`.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md`):
quotes `docs/system-model/D-VARIANTS/SELECTION.md`'s `## Conditions on the selection` item 6 (the
eval-instrument-precedes-every-claim sequencing) and `## Falsifiers` item 5 (per-tier A/A nulls)
as the clauses amended, and `## Falsifiers` item 2 (depth cannot be computed statically) as the
clause left untouched. States the amendment in three clauses (Falsifier 2 satisfied now, Falsifier
5 deferred to Phase 3's parity comparison per D-01's own rationale, the ladder proceeds), what is
not amended (a Falsifier 2 failure still halts the ladder as a SELECTION.md-level reversal), the
standing condition under which the waiver holds (no promotion or parity claim before the A/A floor
exists; Phase 3's D-05 substitute gate and its accepted risk stated in the owner's own terms),
D-01's reversibility rating, the full banked eval-run decision set D-06 through D-13 (each on its
own line, D-08 rated one-way and D-10 rated costly), what it authorises, and the decision/date
line. `docs/system-model/` is never touched — verified by `git status --porcelain`.

**Task 2 — ROADMAP.md re-scope**: six scoped edits — the Overview rung-1 sentence now names
Falsifier 2 alone as rung 1's gate with the A/A floor's standing-up point cited to the waiver;
Phase 2's requirements line drops to `GATE-01, MACH-01, MACH-09`; Phase 2's goal and success
criteria drop the eval-bundle-mint and A/A-calibration criteria (moved verbatim into Phase 3) and
trim the gate-reality criterion to what this phase delivers; Phase 3 gains `MACH-02, MACH-03`, the
two moved criteria, and a new criterion 6 for D-05's retrieval-level substitute gate; Phase 7 gains
`HARD-01, HARD-02` and a new criterion 5 for the moved hardening clauses; the Requirement Coverage
table and both relevant Ordering Constraints bullets are updated and cite the waiver record. Totals
still sum to 34 across all seven surviving phase headings.

**Task 3 — REQUIREMENTS.md re-scope**: the traceability table rows for `MACH-02`, `MACH-03` now
read `Phase 3`; `HARD-01`, `HARD-02` now read `Phase 7`; `GATE-01`, `MACH-01`, `MACH-09` stay
`Phase 2`. Each of the four moved requirements' own text gained a bracketed amendment note naming
the new phase, the point of first need, and the waiver record as authority, explicitly superseding
the original rung-1 timing language rather than deleting it.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the GATE-01 waiver record** - `67994e2` (docs)
2. **Task 2: Re-scope ROADMAP.md** - `1f3ae0f` (docs)
3. **Task 3: Re-scope REQUIREMENTS.md traceability** - `f37ea30` (docs)

## Files Created/Modified

- `.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md` - GATE-01's deliverable: the cited,
  scoped amendment record
- `.planning/ROADMAP.md` - Overview sentence, Phase 2/3/7 detail blocks, Requirement Coverage
  table, two Ordering Constraints bullets
- `.planning/REQUIREMENTS.md` - traceability rows and amendment notes for the four moved
  requirements

## Decisions Made

- Falsifier 2 evidence and probes (02-01, 02-03) are the named authority the waiver rests on;
  Falsifier 5 moves to Phase 3's parity comparison per D-01, with D-05's retrieval-level substitute
  gate standing in until the A/A floor exists.
- A Falsifier 2 failure remains a halting, SELECTION.md-level reversal — the waiver re-times
  condition 6's substance, it does not withdraw it.
- Phase 3's existing criterion 2 (band inside "Phase 2's A/A floor") was corrected to point at this
  phase's own calibrated floor, since MACH-03's calibration now lands in Phase 3 itself — an
  in-scope consistency fix caused directly by moving MACH-03 into this phase, not a separate edit
  outside the plan's authorized changes.

## Deviations from Plan

**1. [Rule 1 - doc consistency] Corrected Phase 3 criterion 2's stale cross-reference**
- **Found during:** Task 2
- **Issue:** Existing Phase 3 success criterion 2 read "the band sits inside Phase 2's A/A floor" — became false the moment MACH-02/MACH-03 (and their A/A-floor criteria) moved into Phase 3 itself in this same task.
- **Fix:** Reworded to "the band sits inside this phase's own calibrated A/A floor (criterion 5)".
- **Files modified:** `.planning/ROADMAP.md`
- **Commit:** `1f3ae0f`

No other deviations — the remaining edits followed the plan's six-edit and traceability
instructions exactly as written.

## Known Stubs

None. No source code is modified by this plan; all three files are planning/governance documents.

## Threat Flags

None. No network endpoint, auth path, file access pattern, or schema change at a trust boundary.

## Self-Check: PASSED

- FOUND: .planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md
- FOUND: commit 67994e2 (Task 1)
- FOUND: commit 1f3ae0f (Task 2)
- FOUND: commit f37ea30 (Task 3)
- FOUND: `docs/system-model/` untouched (`git status --porcelain docs/system-model/` empty)
- FOUND: Requirement Coverage table sums to 34 (4+3+3+7+8+4+5) across all seven `### Phase N:` headings
- FOUND: REQUIREMENTS.md and ROADMAP.md agree on every requirement's phase (script-verified, 34/34, zero mismatches)

## Next Phase Readiness

- GATE-01's waiver record is the authority Phase 3 planning cites for its retrieval-level parity
  gate (D-05) and inherits the banked eval-run decisions D-06 through D-13 when it stands up
  MACH-02/MACH-03.
- Phase 3 is now authorised to start once Falsifier 2 has passed (already true, per 02-01/02-03's
  evidence) without waiting on a Falsifier 5 calibration that would have run against a stand-in arm.
- No blockers for Phase 3 planning.

---
*Phase: 02-falsifier-gate*
*Completed: 2026-08-31*
