# Phase 3 Amendment — MACH-02 / MACH-03 Second Deferral

This document amends `.planning/ROADMAP.md` Phase 3's success criteria 4 and 5, and follows
GATE-01's own precedent: recorded in this project's own layer — `docs/system-model/` is a verbatim
upstream mirror of the ratified system model and is never edited; this record cites into it
instead. The governing document on disagreement is `docs/system-model/D-VARIANTS/SELECTION.md`,
exactly as `02-GATE-01-WAIVER.md` names it.

## What is amended

**`.planning/ROADMAP.md` Phase 3 success criterion 4** (quoted in full):

> Owner mints an eval bundle with dev/holdout/sealed splits carrying questions, gold answers,
> judge instance, judge prompt hash, corpus snapshot hash, determinism/concurrency setting, and
> both §EV.2 target families — and cannot edit a minted version in place; opening `sealed` mints a
> new version and every holdout consultation is logged before any decomposition work reads it

**`.planning/ROADMAP.md` Phase 3 success criterion 5** (quoted in full):

> Owner runs one A/A calibration and reads a bootstrap-resampled p95 floor keyed to
> `(bundle@v, tier, metric)` inseparable from the run's declared determinism/concurrency setting,
> with T1's null width materially narrower than T0's — Falsifier 5

The specific RIG clauses being re-timed, quoted rather than paraphrased:

**`docs/system-model/RIG.md` §EV.1** (bundle versioning, quoted):

> A new `bundle@v` is minted, never edited in place, on any of: a question added or removed; a
> gold answer corrected; the judge instance or judge prompt hash changing; the corpus snapshot
> hash changing; the determinism or concurrency setting changing.

**`docs/system-model/RIG.md` §EV.2** (both-target-families requirement, quoted):

> `§10` requires a bundle to carry **both** target families... A bundle carrying only one family
> cannot evaluate the components the other family covers — a bundle scoped to gold-passage targets
> alone cannot judge a generator mutation at all, and a bundle scoped to answer-level targets alone
> pays the full judging bill even for a retrieval-only mutation. Both families are therefore
> mandatory bundle content, never a configuration choice a bundle author trades off.

**`docs/system-model/RIG.md` §AA.1** (bootstrap-resampled p95 floor, quoted):

> the gate MUST calibrate a per-`(bundle@v, tier, metric)` A/A null and set its promotion floor at
> that null's p95, never at a policy constant... one A/A run at n questions produces n *paired
> per-question* differences between the two runs of the same arm under one fixed
> `(bundle@v, tier, metric)` triple and one fixed concurrency/determinism setting... Bootstrap-
> resample those n paired differences — with replacement, the ordinary nonparametric bootstrap —
> to build the null distribution, and take that resampled distribution's p95 as the calibrated
> floor.

GATE-01 already moved both requirements from rung 1 (Phase 2) into Phase 3, citing
`docs/system-model/D-VARIANTS/SELECTION.md`'s Falsifiers 5 and Conditions item 6 as the governing
clauses. This is the **second** move of the same pair of requirements — Phase 3 to Phase 6 — and
this record says so plainly rather than letting a later reader discover it by diffing two dates.

## The amendment

MACH-02 and MACH-03 move to Phase 6's side-by-side run.

D-10's reason is stated as the technical argument it is, not as a schedule note: with one shared
index (D-01 — v1's ingest builds the index once, both arms read it) and both arms pinned to one
model identity (D-07's one OpenAI-compatible client shape, D-08's carried-forward model pins),
everything downstream of keyword extraction is a **deterministic function** of the query embedding
and the store contents. At that point the retrieval-level comparison is not a weak substitute for
an A/A floor — it is a *sharper* instrument for what rung 2 actually tests: did the re-cut change
what gets retrieved? An A/A floor measures answer-level noise, which is exactly what MACH-09's
default-off posture says not to measure yet.

The point of first need is named explicitly, not left open-ended: **Phase 6's cross-modality run**,
where LightRAG and HippoRAG 2 answer the same corpus and no shared-index, shared-model-identity
retrieval-level comparison exists to lean on — the first comparison in the roadmap that genuinely
needs an answer-level floor.

## What is substituted

Criterion 6's deterministic, zero-token retrieval-level gate is Phase 3's parity instrument:
comparison of retrieved chunk sets and rankings between the original and the decomposed query side,
plus human spot-checks of answers (D-05's substitute gate, carried from GATE-01's own standing
condition).

D-12's N-run variance band over `keywords`' own output joins it: `keywords` is the one genuinely
stochastic node upstream of retrieval, so it is pinned per query — run once, its output recorded,
and the same recorded keywords fed to both arms, making everything downstream exactly comparable.
The `keywords` node itself is compared on its own — N runs, a variance band over its output — which
is how criterion 2's "N-run variance band rather than a single diff" is satisfied without an eval
bundle.

## Residual risk

Stated plainly, in D-11's own words, not softened and not buried in a subordinate clause:

**Answer-level drift originating in `keywords` and `generate` stays unmeasured until a floor
exists.**

## What is not amended

Condition 6's substance — no promotion or parity claim rides on an unmeasured comparison — is
re-timed, not withdrawn. GATE-01's standing condition continues to hold: no promotion decision and
no parity claim is taken before the A/A floor exists.

## Reversibility

D-10's own rating: **reversible**. `docs/system-model/RIG.md` §EV and §AA fully specify the bundle
and calibration design, and Phase 2's banked decisions D-06 through D-13 (reproduced by reference
to `02-GATE-01-WAIVER.md`'s own "Banked decisions" list, not restated here) hold every parameter
the calibration needs. Standing it up in Phase 6 costs nothing that standing it up now would have
saved.

Two of those banked ratings carry forward by name, because they bound how costly a later reversal
of *this* amendment would be: **D-08**'s `one-way` rating on the judge (changing the judge mints a
new bundle version and voids every null calibrated under it) and **D-10**'s `costly` rating on
declared concurrency (changing it requires recalibrating the floor). Note — `D-10` in GATE-01's
"Banked decisions" list (declared concurrency) is a different decision from this record's own
`D-10` (the criteria-4/5 deferral); the numbering collision is between the two phases' own
decision logs, not a contradiction within either.

## What this authorises

This record authorises the tracking changes made alongside it in
`.planning/ROADMAP.md` and `.planning/REQUIREMENTS.md`: MACH-02 and MACH-03 move from Phase 3 to
Phase 6 (point of first need: Phase 6's cross-modality run), and Phase 6's success criteria gain an
obligation carrying the eval-bundle and A/A-calibration work forward. Neither deferral is
open-ended — it carries a named phase and a named point of first need, exactly as GATE-01's own
MACH-02/MACH-03 and HARD-01/HARD-02 deferrals did.

## Decision and date

**Decision:** MACH-02 (eval bundle) and MACH-03 (A/A calibration, Falsifier 5) are deferred a
second time, from Phase 3 to Phase 6's side-by-side run, on the technical argument that Phase 3's
shared-index/shared-model-identity design makes the deterministic retrieval-level comparison a
sharper rung-2 instrument than an answer-level A/A floor would be. The deferral is recorded, never
silent, and the residual risk — unmeasured answer-level drift in `keywords` and `generate` — is
named plainly rather than dropped.

**Provenance:** the owner reviewed the four gray areas Phase 3's context-gathering surfaced (index
provenance, the original arm, model clients, parity gate depth) and directed "no area needs
covered, go with recommendations" on 2026-08-31. D-10 and D-11 are Claude's calls, made under that
direction — recorded here so a later reader does not mistake this deferral for an owner-originated
position.

**Owner:** Christopher (Deocracy)
**Date:** 2026-08-31
