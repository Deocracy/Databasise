# Phase 7 Amendment — HARD-04, HARD-01 and HARD-02 Deferred to the Owner's Hardening Phase

This document amends `.planning/ROADMAP.md` Phase 7's success criteria 4 and 5 and its requirements
line, and follows GATE-01's own precedent: recorded in this project's own layer —
`docs/system-model/` is a verbatim upstream mirror of the ratified system model and is never edited;
this record cites into it instead. The governing document on disagreement is
`docs/system-model/D-VARIANTS/SELECTION.md`, exactly as `02-GATE-01-WAIVER.md`,
`03-GATE-AMENDMENT.md` and `06-GATE-AMENDMENT.md` each name it.

This is the **third** re-timing of HARD-01 and HARD-02 (rung 1 → Phase 7 → here) and the **first**
re-timing of HARD-04. Both counts are said plainly rather than left for a later reader to discover
by diffing dates.

## What is amended

**`.planning/ROADMAP.md` Phase 7 requirements line** (quoted in full):

> **Requirements**: MACH-07, API-09, HARD-04, HARD-01, HARD-02

**`.planning/ROADMAP.md` Phase 7 success criterion 4** (quoted in full):

> The owner's own document corpus is layered into the eval bundle before any promotion decision is
> taken on it

**`.planning/ROADMAP.md` Phase 7 success criterion 5** (quoted in full):

> The gate scripts fail on missing extraction instead of passing vacuously, and every ANATOMY §F
> row points at its landed repair with stale cross-document rows reconciled

**`.planning/ROADMAP.md`'s ordering constraint the first of these carries** (quoted in full):

> - **HARD-04 before promotion**: the owner's corpus is in the bundle before any promotion decision
>   rides on it (Phase 7).

### What HARD-04 is, restated from its rule rather than its ID

The owner asked mid-discussion on 2026-09-11 what HARD-04 actually is. It is written here from the
rule it came from, so the later phase starts from the rule rather than from a requirement id.

The system model's evidence discipline holds that **only measurement on this project's own corpus
counts**. A benchmark corpus someone else assembled tells you how a modality behaves on that
corpus; it does not tell you how it behaves on the documents the owner will actually put through
it. HARD-04 is the requirement that the owner's own documents be layered into the eval bundle
*before* a promotion decision rides on a measured number — so that the number a gate later reads
was produced against the corpus the promotion will actually serve. It is a hardening requirement
about the *evidence's provenance*, not about promotion mechanics.

### The contract clauses this record leans on, quoted rather than paraphrased

**`docs/system-model/RIG.md` §PR.3** (the operator path — quoted in `06-GATE-AMENDMENT.md` and
restated here because this record's whole argument stands on it):

> **What the record then carries.** `promotion_provenance` set to `operator_asserted`;
> `promotion_trace_ids`, a non-empty list of the trace ids the operator read to form the judgment,
> carried in place of an evidence pointer.
>
> **What the record does not carry, and why the absence is stated rather than filled.** No
> `verdict` and no `tier-of-decision`: `§5`'s "every verdict carries its evidence pointer and
> tier-of-decision" rule does not apply here, because an operator-asserted record is not a verdict
> at all — there was no gate comparison to produce one.

**`docs/system-model/CONTRACT.md` §6** (the promotion mechanism):

> the ledger append **is** the promotion decision; the active pointer is a projection derived from
> the ledger, not an independent record

## The amendment

Three clauses.

**First — HARD-04 moves to its true point of first need: the owner's in-depth testing / hardening
phase, or the first gate-adjudicated promotion, whichever comes first.** Phase 7 builds only the
operator-asserted promotion path. Under RIG §PR.3 and CONTRACT §7 that record carries no verdict, no
tier-of-decision and no evidence pointer; it carries trace ids in place of one. **An
operator-asserted promotion reads no eval bundle at all.** There is therefore nothing in Phase 7
that consumes the owner-corpus layer — the eval bundle is not read, not hashed against, and not
checked for coverage anywhere on the path Phase 7 builds. This is the identical argument
`06-GATE-AMENDMENT.md` made when it deferred MACH-03 out of Phase 6: the floor and the bundle are
both inputs to a *gate-adjudicated* decision, and no gate-adjudicated decision exists in this
milestone under MACH-09's default posture. The ROADMAP's "HARD-04 before promotion" ordering
constraint is preserved in substance, not withdrawn: it now reads *before any promotion decision
that rides on a measured number*, which is exactly the decision class the constraint was written
for and exactly the class Phase 7 does not build.

**When HARD-04 does run, its shape is already agreed** (owner, 2026-09-11) and is recorded here so
the later phase inherits decisions rather than re-opening them:

- The corpus is a **smaller subset the owner picks later**, not the whole document set.
- **Only hashes and an evidence record cross into git.** The documents, questions and gold answers
  live in a local-only directory named at mint time — this repository is public.
- Phase 7 builds **no coverage check on `promote()`** and **no question-authoring tool**. Whether
  `promote()` should later refuse a promotion without bundle coverage, and who authors the
  questions / gold answers / gold document ids, are open questions that travel with the deferral.

**Second — HARD-01 and HARD-02 are deferred to that same phase.** Neither is consumed by the
promote path either. HARD-01 is the gate-script vacuous-pass repair (`docs/system-model/parts-check.sh`:
5 extraction sites guarding ~6 checks; `docs/system-model/anatomy-check.sh`: 1 site guarding 3
checks). HARD-02 is the ANATOMY §F / PARTS Appendix A reconciliation, including the stale
cross-document rows (DR-06: ANATOMY reads "Answered", PARTS Appendix A still reads "not reached").
Both are document- and script-hygiene requirements over the frozen system model; nothing in
`databasise/ledger/`, `databasise/seam/` or `databasise/mcp/` reads either. Phase 7's requirement set
is therefore **MACH-07 + API-09**.

**Third — an open question travels with the HARD-01/HARD-02 deferral, unresolved.** Both requirements
name sites inside `docs/system-model/`, which is a **verbatim upstream mirror of
`ServerDestroyer/rag-modality-swap-system-model` and is never edited** — that rule is what
`02-GATE-01-WAIVER.md` established and what every gate record since has obeyed. Where the repairs
land is therefore genuinely undecided, and this record does not decide it. The three candidates:

1. **Fix upstream and re-mirror** — repair `ServerDestroyer/rag-modality-swap-system-model`, then
   re-copy the mirror. Keeps the never-edited rule intact; costs an upstream round trip and
   re-validates every downstream citation against a moved document.
2. **Edit in place with a recorded divergence** — repair the mirrored files here and record the
   divergence explicitly, as a dated entry. Cheapest; breaks the "verbatim" property the mirror's
   whole value rests on.
3. **Project-layer copies** — carry repaired scripts and a reconciliation table in this project's own
   layer, leaving the mirror untouched. Keeps the mirror verbatim; creates two documents a reader
   must know to reconcile.

The later phase picks one. Nothing in this record constrains that choice.

## What is substituted

For all three requirements: **nothing is substituted, because nothing in Phase 7 consumes any of
them.** No weaker check stands in for the owner corpus, no partial script repair stands in for
HARD-01, and no partial reconciliation stands in for HARD-02. The absence is total and is stated
rather than filled.

What keeps that absence sound is Phase 7's own success criterion 3, which survives this amendment
untouched: `promote-next` and `promote-now` refuse by name for the answer-level and index-side
classes under MACH-09's default posture, and the refusal quotes the posture and cites RIG §F3.2.
That refusal is what keeps the gate-adjudicated path — the only path that would read a bundle or a
floor — genuinely unreachable in this milestone, rather than merely unexercised.

## Residual risk

Stated plainly, not softened:

**Every promotion this milestone makes is provisional and unmeasured on the owner's own data.** An
operator-asserted record is a provisional state that RIG §PR.3 says the measured path later
resolves. Until a gate-adjudicated promotion supersedes it, no promoted wiring in this milestone has
a measured verdict behind it — and, with HARD-04 deferred, no measurement on the owner's own
documents exists to produce one from. `bundle@v1`'s 30-question corpus is a synthetic fixture, not
the owner's corpus; a later measured claim built on it would be a claim about that fixture.

**The gate scripts still pass vacuously.** HARD-01's six sites are unrepaired. A `parts-check.sh` or
`anatomy-check.sh` run that reports green today may be reporting green because an extraction
produced nothing, not because the checks passed. Any future use of those scripts as evidence
inherits that defect until HARD-01 lands.

**ANATOMY §F and PARTS Appendix A still disagree in at least one place on file.** DR-06 reads
"Answered" in one document and "not reached" in the other. A reader consulting either document alone
gets an answer the other contradicts.

**The phase holding all three does not exist yet.** It is the owner's to add (`/gsd-phase add`), and
until it exists these three requirements have a named point of first need but no scheduled home.

## What is not amended

- **HARD-01, HARD-02 and HARD-04 stay Pending** in `.planning/REQUIREMENTS.md`, checkboxes
  unchecked. The milestone cannot close on its own requirements until all three are discharged. They
  now sit in the milestone audit **beside MACH-03 and MODAL-01**, which `06-GATE-AMENDMENT.md`
  already left open — five open rows, not two.
- **Phase 7's success criteria 1, 2 and 3 are untouched.** They are what Phase 7 builds: MACH-07's
  ledger discipline, API-09's operator path, and the posture refusal.
- **Phase 7's success criterion 3 is load-bearing**, as `06-GATE-AMENDMENT.md` already recorded. If
  Phase 7 weakened that refusal, or the posture were flipped on, the first gate-adjudicated
  promotion would be reached and MACH-03 *and* HARD-04 would both be due at that moment.
- **The substance of criteria 4 and 5 is re-timed, not withdrawn.** The owner's corpus still precedes
  any measured promotion decision; the gate scripts still owe a non-vacuous pass.
- **`docs/system-model/` stays unedited.** This record cites into it and changes nothing in it.

## Reversibility

**Reversible.** Nothing is built or unbuilt by this deferral.

For HARD-04: the mint path the later phase reuses already exists and is tested —
`databasise.parity.corpus.load_snapshot` and `databasise.eval.bundle.mint_bundle` both accept any
directory, `databasise/eval/remint.py` resolves a real judge identity, and
`databasise/eval/corpus_ingest.py` gives a cost-bounded, document-count-capped ingest path. The later
phase mints against the owner's directory with **no new machinery** — it costs the owner's corpus
selection and the spend, and nothing else.

For HARD-01 and HARD-02: both are document and shell-script edits. Their sites are already located
and counted (5 + 1 extraction sites; eight ANATOMY §F rows plus DR-06's cross-document row). The
only open input is which of the three landing options above is chosen.

For this record itself: a roadmap edit and three dated notes.

## What this authorises

This record authorises the tracking changes made alongside it:

- `.planning/ROADMAP.md` Phase 7's requirements line becomes **`MACH-07, API-09`**.
- `.planning/ROADMAP.md` Phase 7's success criteria 4 and 5 are struck — their text kept, marked
  deferred, each carrying a pointer to this record.
- `.planning/REQUIREMENTS.md` rows **HARD-01**, **HARD-02** and **HARD-04** each gain a dated
  (2026-09-11) deferral note naming this record and the new point of first need. All three stay
  **Pending with checkboxes unchecked**.

Neither deferral is open-ended. The point of first need for all three is **the owner's in-depth
testing / hardening phase, or the first gate-adjudicated promotion, whichever comes first** — exactly
as GATE-01's, 03-GATE-AMENDMENT's and 06-GATE-AMENDMENT's deferrals each named theirs. That phase
does not exist in the roadmap yet; adding it is the owner's act (`/gsd-phase add`), and it should
hold HARD-01, HARD-02, HARD-04, the MACH-03 A/A spend, MODAL-01's two owner items, and the Phase 6
UAT refresh.

`/gsd-plan-phase 7` proceeds against **MACH-07 + API-09** and ROADMAP success criteria 1–3.

## Decision and date

**Decision:** HARD-04 (the owner's corpus into the eval bundle), HARD-01 (gate-script vacuous-pass
sites) and HARD-02 (ANATOMY §F / PARTS Appendix A reconciliation) are deferred out of Phase 7 to the
owner's in-depth testing / hardening phase, or the first gate-adjudicated promotion, whichever comes
first. Phase 7's effective requirement set is MACH-07 + API-09, and its effective success criteria
are 1–3. All three requirements stay Pending; the milestone stays open on them, beside MACH-03 and
MODAL-01.

**Provenance:** owner-originated. On 2026-09-11, asked whether the owner's corpus needed to be in the
eval bundle for this phase, the owner answered: *"Unless this testing is required I wanted to defer
it until the product is built and I do in-depth testing for an entirely different phase."* On the
corpus shape: *"smaller subset I pick later to test on."* The argument that an operator-asserted
promotion consumes no bundle, no floor and no verdict — and that HARD-01 and HARD-02 are therefore
deferrable on the same grounds — is Claude's, made under that direction and recorded here so a later
reader does not mistake the reasoning for an owner-originated position. The decision to defer is the
owner's.

**Owner:** Christopher (Deocracy)
**Date:** 2026-09-11
