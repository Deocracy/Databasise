# Falsifier 5 Evidence — MACH-03 (A/A Calibration): BLOCKED, Not Discharged

**Date:** 2026-09-09

`.planning/REQUIREMENTS.md` MACH-03's pass criterion, quoted verbatim:

> First A/A calibration per RIG §AA.1: one A/A run at n questions producing n paired per-question
> differences, bootstrap-resampled, the resampled distribution's p95 taken as the calibrated floor
> at `(bundle@v, tier, metric)` inseparable from the run's declared determinism/concurrency
> setting; §AA.2 precondition holds (a null with unknown bypass status is not usable as a floor).
> **Pass criterion: per-tier null width at T1 materially narrower than T0** (SELECTION Falsifier
> 5) — **Falsifier 5 gate**

Both amendment notes carried forward on that requirement — moved to Phase 3 per
`.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md`, then moved a second time to this phase
per `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md` — brought MACH-03 here, to Phase
6's cross-modality run, as its point of first need.

## Status

**BLOCKED. Falsifier 5 is NOT discharged. MACH-03 is not met.** No calibrated floor exists at
either target family. No p95 was computed. No `(bundle@v, tier, metric)` `NullIdentity` key was
minted with a real, run-derived value. Plan 06-06's Task 1 landed the calibration procedure itself
(`databasise/eval/calibration.py` — `calibrate_aa_floor`, `CalibrationResult`, `NullIdentity`,
`UnusableFloorError`, `StaleNullError`, `paired_differences`, `correct_for_batch_width`), fully
tested against fixture data (`databasise/tests/eval/test_calibration.py`, 15 tests, all passing),
with both `§AA` preconditions — the cache-bypass precondition and the staleness precondition —
enforced as refusals in code, not warnings. That is the *instrument*. It has not yet been pointed
at a real run of either `§EV.2` target family, and this document is the honest record of why, and
of what would have to change for it to be.

**This document does not imply Falsifier 5 passed.** It also does not imply Falsifier 5 failed —
no comparison ran, so there is no adverse verdict to record either. The falsifier is **open**, not
settled in either direction.

## Findings — both blockers, verbatim and verifiable

| # | Target family | Tier | Blocker | Cited authority |
|---|---|---|---|---|
| 1 | `answer_level` | `T0` | `bundle@v1`'s `judge_instance` is recorded as the explicit sentinel `"unresolved"` — not a resolved model identity. This plan's own Task 2 action text states: "If the judge identity was recorded unresolved in `bundle@v1`, this leg cannot run: halt and say so plainly rather than substituting a judge, which would key the null to an instance the bundle does not name." | `[code-verified]` `databasise/evidence/EVAL-BUNDLE-V1.md` findings table, `judge_instance` row: `"unresolved" — see Limits below; not a fabricated plausible string`; also that document's own Limits section: `"judge_instance is recorded as 'unresolved', not a resolved model identity. ... No such live call was made in this environment for this plan"` |
| 2 | `gold_passage` | `T1` | Computing this leg's metric requires the LightRAG arm to actually retrieve against `bundle@v1`'s 291-document eval-corpus, which requires ingesting that corpus through the opaque v1 `full-ingest` path first — a real, un-budgeted spend. The engine's own accounting reports `full_ingest` spend as `"unbudgetable"`, never a bounded estimate this plan can commit to spending against. | `[code-verified]` `databasise/parts_core/lightrag/full_ingest.py` (`_UNBUDGETABLE_TOKENS_SENTINEL = "unbudgetable"`; `verdict="partially satisfied — spend reported as unbudgetable, never estimated"`); `[code-verified]` `databasise/tests/fixtures/eval-corpus/` — 291 document files (`06-04-SUMMARY.md`: `"Built databasise/tests/fixtures/eval-corpus/: 291 documents, 30 questions"`) |

Per this plan's own Task 2 action text, the cheap leg (gold-passage, `§EV.2`'s own ~1-5%-of-bill
pricing) was to run first, with the expensive leg (answer-level) second and priced before starting.
Neither ran: the gold-passage leg's own cost is cheap in per-token terms, but it is not
*bounded* — the 291-document corpus has no committed, cost-bounded ingest path today, and the
answer-level leg cannot run at all while the judge identity is unresolved. Both blockers are
independent of each other; either alone is sufficient to halt this plan short of a real run.

## Owner decision: defer-run

Presented as a `gate="blocking-human"` checkpoint during Task 2 (the spend/judge-identity
checkpoint), the owner selected **defer-run**: no real A/A calibration runs in this plan. No
corpus is ingested, no LLM calls are made, no spend is incurred. Both the T0 and T1 legs stay
unrun. This is a deliberate, recorded deferral — not an oversight, and not a silent skip of Task 2's
own acceptance criteria, which are adapted below to the blocked reality (see Deviations, in
`06-06-SUMMARY.md`).

## Two preconditions that must hold before this run can happen

1. **A resolved judge identity in the bundle.** `bundle@v1` must be re-minted (or a new bundle
   version minted, per `§EV.1`'s own "judge instance ... changing" invalidating-change rule) with
   `judge_instance` set to a real, live-resolved model identity — never a declared/requested id
   substituted for one, per this project's own "hash what is installed, never what is declared"
   convention (Phase 1 D-12 / Phase 2 D-08, the same convention `EVAL-BUNDLE-V1.md` already applies
   to this exact field). This unblocks the T0 (answer-level) leg.
2. **A cost-bounded indexing story for the eval-corpus.** The 291-document
   `databasise/tests/fixtures/eval-corpus/` must be ingested through a path whose spend is either
   genuinely bounded or explicitly budgeted for, rather than the opaque v1 `full-ingest` path's
   `unbudgetable` accounting. This unblocks the T1 (gold-passage) leg.

Neither precondition is met as of this document's date.

## Method and limits

**Method.** Task 1 of this plan built and tested the calibration procedure against fixture data
only (`databasise/tests/eval/test_calibration.py`) — no real run of either target family is claimed
or implied by that work, and none is claimed here. This document records the deliberate decision
not to proceed past Task 1 into a real calibration, and states plainly why.

**Limits, stated plainly:**

- **No floor value is reported anywhere in this document, for either tier.** Reporting a number
  here — even a placeholder, an estimate, or a number offered "for illustration" — would be exactly
  the kind of fabricated-plausible-value substitution this project's own conventions forbid (the
  same discipline `EVAL-BUNDLE-V1.md` already applies to `judge_instance`, and that
  `databasise/parts_core/lightrag/full_ingest.py`/`full_delete.py` already apply to token
  accounting: `unbudgetable`, never a fabricated zero).
- **Falsifier 5's own ladder-halt consequence is not triggered by this document.** A Falsifier 5
  *failure* — a real comparison that ran and did not clear a pre-registered threshold — halts the
  ladder as a SELECTION.md-level reversal, per Phase 2's own record
  (`.planning/phases/02-falsifier-gate/02-04-SUMMARY.md`: "A Falsifier 2 failure remains a halting,
  SELECTION.md-level reversal"; Falsifier 5 is named alongside Falsifier 2 in the same waiver
  document as carrying the same halt consequence). This is not that case: no comparison ran, so no
  verdict — adverse or otherwise — exists to trigger it. The falsifier is **open**, not failed.
- **MACH-03 stays Pending in `.planning/REQUIREMENTS.md`.** This document is not the
  "MACH-03 complete" record; it is the record of why MACH-03 is not yet complete, and of the two
  concrete preconditions that would make it completable.
- **No numeric threshold for "materially narrower" is pre-registered here.** Task 3's own action
  text calls for fixing that threshold before reading the two floors; with no floors computed,
  pre-registering a threshold now would have nothing to be pre-registered against, and would read
  as more settled than the actual state of this work. `06-RESEARCH.md`'s Open Question 1 default
  (T1's calibrated p95 floor, in the same score units, at most half of T0's) remains the standing
  recommendation for whichever plan runs the real calibration next; it is not adopted or rejected by
  this document.

## Next Phase Readiness

The real A/A calibration run is **deferred to a later plan**. Its entry criteria are the two
preconditions named above: a resolved judge identity in the bundle, and a cost-bounded indexing
story for the eval-corpus. Phase 7 (Promotion & Rollback) is the consumer that will need this
floor — `.planning/ROADMAP.md`'s own Ordering Constraints section states plainly that the eval
bundle and A/A floor stand up "before any promotion or parity claim rides on a measured number"
(`.planning/ROADMAP.md`, Ordering Constraints, "Eval infrastructure at point of need"). No
promotion or parity claim in Phase 7 may ride on a measured number until this document is
superseded by a real calibration record carrying two real committed floors.

---
*Falsifier 5 (MACH-03) — BLOCKED, not discharged*
*Recorded: 2026-09-09*

## Deferred again — 2026-09-10

**Date:** 2026-09-10

The owner declined the real A/A calibration a second time, at this plan's Task 2
`gate="blocking-human"` checkpoint (`decline`). Their stated reason, verbatim:

> a real run in this same session (Task 1) had just incurred spend and then died on a live-data
> edge case — the `fact-score` empty-string defect — that no test caught; the same class of defect
> could waste the far more expensive T0 leg, so fixing `fact-score` first makes both spends cheaper
> to attempt.

No corpus is ingested, no judge-identity call is made, no LLM call of any kind occurs, no spend is
incurred, and no bundle version is minted. Both the T0 and T1 legs stay unrun. The entry criterion
for the real calibration run is **unchanged** — it is still: a resolved judge identity in the
bundle, and a cost-bounded indexing story for the eval-corpus, followed by the owner's
authorization of the spend itself.

**What did change since 2026-09-09:** 06-12 closed both of the preconditions this document's own
"Two preconditions that must hold before this run can happen" section named as outstanding —
`databasise/eval/remint.py` resolves a real judge identity from a live provider response (never a
declared/substituted one) and mints the next bundle version carrying it, and
`databasise/eval/corpus_ingest.py` turns the 291-document eval-corpus's ingest from
`full_ingest`'s `unbudgetable` accounting into a cost-bounded, dry-run-by-default path with a
printed projection under an enforced `--limit` cap. Both preconditions this document names are now
met in code. The only remaining blocker is the spend decision itself, which the owner has now
declined twice — at 06-06 and again here.

MACH-03 stays **Pending** in `.planning/REQUIREMENTS.md`, with a dated annotation naming the spend
as the single outstanding item. A recorded decline is this task's success state, not its failure
state — Falsifier 5 remains **open**, not failed: no comparison ran, so there is no adverse verdict
to record.

---
*Recorded: 2026-09-10*
