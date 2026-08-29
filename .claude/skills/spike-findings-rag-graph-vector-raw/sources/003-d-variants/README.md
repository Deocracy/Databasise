---
spike: 003
name: d-variants
type: theory
validates: "Given amended-D as the leading architecture and the spike-002 amendment set, when 3-4 concrete D-variants are drafted (differing on kernel style, sandbox containment, promotion mechanics, instrument placement, comparison depth) and scored against the 10-goal rubric + red-team amendments, then one variant wins with rationale and becomes the input to the fitting contract spec — or D's lead collapses under variant-level detail and B is re-examined"
verdict: VALIDATED — BOTH BRANCHES; D4 selected AND D's two-regime lead collapsed to B-with-amendments (they are the same act)
related: [002, 004]
tags: [architecture, kernel-sandbox, variants, selection, collapse]
---

# Spike 003: D-Variants — which Kernel+Sandbox do we actually mean?

**Status: DEFINED, not started. Designed to run in a fresh session.**
On start: load skill `spike-findings-rag-graph-vector-raw` (auto-routes via project CLAUDE.md) — it carries everything from spikes 001–002. Re-read `.planning/spikes/MANIFEST.md` Requirements before drafting.

## Goal (one sentence)

Turn "amended-D wins" from a direction into a decision: draft 3–4 concrete, differently-shaped versions of the Kernel+Sandbox architecture, score them, pick one.

## Clear goals (numbered)

1. **Enumerate D's free axes** — spike 002 fixed some properties (Conductor-style kernel, enforced sandbox isolation, improvement loop kernel-only, A's machine-owned boundaries, SA-1/SA-2 hashing) but left others open. Minimum open axes to vary:
   - **Kernel graph-execution style**: full declared-graph engine vs typed-pipeline-with-loop-nodes vs code-parts-with-manifests (how much of B lives in the kernel?)
   - **Sandbox containment depth**: process isolation vs container/systemd-unit (NixOS substrate!) vs in-process with enforced manifests only
   - **Promotion mechanics**: what exactly crosses the sandbox→kernel boundary (whole part re-implemented vs decomposed stage-by-stage vs adapter-first-then-decompose), and what evidence gates promotion
   - **Instrument placement**: eval bundle + promotion gate as kernel services vs regime-independent third block that both regimes report into
   - **Comparison depth handling**: how the rig labels kernel-deep vs sandbox-shallow evidence so promotion never runs on silently-mixed quality (RT-modularity's D-cost)
2. **Draft 3–4 named variants** as coherent positions on those axes (not a matrix sweep — each variant must be a design someone would actually build), each with: mermaid diagram, walk-through of the same three scenarios (embedder swap, LightRAG-v2 upstream, one full mutate→A/B→promote cycle), advantages, disadvantages, and what would falsify its choice
3. **Score each variant** against the 10-goal rubric (ARCHITECTURE-RUBRIC.md) + the six self-improvement machine services + the five contract clauses — table form, honest, no variant claims all ten
4. **Select one** with rationale, or report that variant-level detail collapsed D's lead (in which case re-open B and say exactly why)
5. **Output feeds step 8** (fitting contract spec) of `.planning/SPIKE-PLAN.md` — the winning variant's boundaries become the contract's skeleton

## Constraints (from MANIFEST Requirements — binding)

- Documents only; subagents Opus/Sonnet, Fable for final integration/selection only
- Every claim tagged; no live-framework dependencies assumed; Nix-alignment is a plus (Sourcerer v2.0 substrate is NixOS — sandbox-as-Nix-unit is a legitimate variant axis)
- Eval-first sequencing is settled — variants may not re-litigate it, only place the instruments
- The five contract clauses and SA-1/SA-2 are settled amendments — variants must incorporate, not debate them

Added by pre-003 exploration (2026-08-10):

- **Executor-primitive disqualifier**: any kernel style that cannot host fan-out/join, ephemeral-subgraph (planner versioned, emitted plan recorded as trace data), and non-adjacent fan-in (GAP-SWEEP §3.8) is disqualified at drafting time
- **Environment hash in instance identity** is a settled requirement — all variants incorporate it. It is justified independently of spike 004 (Feast version-skew, PRIOR-ART avoid list); Nix is one possible source of the hash, not its justification.
- **Two-plane separation** is binding (`.planning/notes/two-plane-separation.md`): artifact/lineage plane is a DAG; execution plane owns loops; a variant that merges the planes is disqualified. A cyclic *wiring* is not a merged plane — the spec is DAG-plane data whose content describes cycles.
- **D3 (Nix-native variant) drafts from spike 004 findings** (`.planning/research/NIX-LEVERAGE.md`). If 004's verdict is deployment-only, D3 degrades to a substrate-only containment choice and says so

## Variant lineup (approved 2026-08-10)

| Variant | Kernel style | Sandbox containment | Promotion | Instruments | Comparison depth |
|---|---|---|---|---|---|
| **D1 Two Kingdoms** (orthodox D) | full declared-graph engine | OS container / Nix unit, hard | whole part re-implemented; sandbox artifacts discarded | kernel services | rig refuses cross-regime deep compare; sandbox always answer-tier |
| **D2 Instrument Bus** | full declared-graph engine | process isolation | adapter-first → decompose incrementally; registry tracks decomposition debt | regime-independent third block both regimes report into | evidence-depth tier is a first-class field in the evidence protocol |
| ~~**D3 Nix Unit**~~ (retired) | typed spine + explicit loop/branch nodes | Nix derivation + systemd unit, content-addressed | stage-by-stage against the typed spine; no other entry | kernel services; eval bundle content-addressed | depth follows the typed spine; sandbox evidence hashed to its derivation |
| **D4 One Machine** (collapse test) | one executor only | in-process/subprocess with enforced manifest — sandbox is a capability, not a regime | node → subgraph decomposition | kernel (no second regime) | wiring validator enforces depth labels |
| **D5 Actor Kernel** (replaces D3) | actor / message-passing executor; subgraph = spawned actor set | confined systemd unit (spike 004 substrate finding) | sandbox actor swapped for an actor set behind the same mailbox contract | kernel services | depth inferred from mailbox boundaries crossed |

D4 deliberately tests whether D's second regime is needed at all — if it wins, that is the "D's lead collapsed, B was right" outcome reached with evidence.

**D3 did not survive — spike 004 landed DEPLOYMENT-ONLY (2026-08-10).** Its distinguishing properties were a Nix-derivation sandbox and content-addressed promotion through the Nix store; the build sandbox is build-time only, and the store path is not SA-1 (see `.planning/research/NIX-LEVERAGE.md`). With Nix removed it differed from D1 mainly by its typed spine, and that spine was the lineup's most likely failure on the executor-primitive disqualifier.

**Decision (2026-08-10, session start): D3 replaced by D5 Actor Kernel.** Rationale: D1, D2 and D4 all run a full declared-graph engine or a single graph executor, so retiring D3 left **kernel-execution style — goal 1's first open axis — effectively unvaried**, and the fitting contract would have inherited "declared-graph engine" as an assumption no variant ever argued against. D5 varies exactly that axis and clears the executor-primitive disqualifier on its own terms (fan-out/join, non-adjacent fan-in and ephemeral subgraphs are native to message passing). Its real cost is the one no surviving variant pressured: a topology that is emergent at runtime is hard to statically validate, which stresses machine service #5 (Static Mutation Validator). If D5 cannot be type-checked before it runs, it falls — and that is a finding worth having.

**Two variants are pre-committed only as scoping.** The lineup exists so drafting agents cover different positions, not so they converge on these four — a drafter who finds a fifth coherent position should say so rather than force-fit.

## Method (decided 2026-08-10)

Subagents as briefed, user-approved at session start: one Opus agent per variant drafting independently from the same shared brief (diversity beats iteration), then a cross-variant red-team pass (Opus), then Fable selects.

**Landing pads** (declared before the work runs, per CONVENTIONS):

- `.planning/architectures/D-VARIANTS/BRIEF.md` — the shared drafting brief; binding constraints, disqualifiers, scenarios, document contract
- `.planning/architectures/D-VARIANTS/D1-two-kingdoms.md`
- `.planning/architectures/D-VARIANTS/D2-instrument-bus.md`
- `.planning/architectures/D-VARIANTS/D4-one-machine.md`
- `.planning/architectures/D-VARIANTS/D5-actor-kernel.md`
- `.planning/architectures/D-VARIANTS/RED-TEAM.md` — cross-variant adversarial pass
- `.planning/architectures/D-VARIANTS/SELECTION.md` — winner, rationale, falsifiers, contract skeleton

## Inputs

- Skill: `spike-findings-rag-graph-vector-raw` (references + sources)
- `.planning/architectures/CANDIDATES.md` (D as drafted), `ANATOMY-REVIEW.md` (the 10 must-fix edits — variants should draw the *fixed* anatomy)
- `.planning/redteam/RT-*.md` (the attack scenarios to re-run per variant)
- `.planning/ARCHITECTURE-RUBRIC.md`, `.planning/spikes/MANIFEST.md` Requirements

## What to Expect

3–4 variant documents + a selection document naming the winner, its falsifiers, and the contract skeleton it implies.

## Investigation Trail

- 2026-08-10: Spike defined at wrap-up of 002; deliberately not started (fresh-session start intended)
- 2026-08-10 (run session): D3 retired, replaced by **D5 Actor Kernel** — with D3 gone, kernel-execution style would have been the one open axis left unvaried, and the contract would have inherited "declared-graph engine" as an assumption no variant ever argued against
- Shared `BRIEF.md` written and **committed before any drafting** (`f17ea3f`), fixing the settled set, five disqualifiers, three scenarios, and the document contract in advance
- Four Opus agents drafted D1/D2/D4/D5 independently, none seeing the others (`2353541`, 1,978 lines)
- Two adversarial passes in parallel (`d47dd4b`): cross-variant red team, plus a **compliance verifier** added because every drafter had self-certified its own disqualifier checks — 3 of 20 self-certified passes were downgraded
- Fable selected; D4 wins **and** D collapses — the same act

## Results

**Verdict: VALIDATED — both branches of the decision rule fired simultaneously.**

The rule fixed in advance was "one variant wins with rationale, **or** D's lead collapses and B is re-examined." The answer is both, because **D4 One Machine *is* candidate B with the amendments the evidence forced**. Selecting D4 and ruling that D's two-regime lead collapsed are one action, not two.

**Why D collapsed.** All four variants — three by design, D1 only by admitted exception — independently replaced D's structural bound with the same per-node rule: *you cannot mutate what you have not decomposed*. An opaque node's only mutable surface is its config and position, so registry growth scales with decomposed surface. That is exactly the bound spike 002 credited to the regime, obtained without one. After the settled per-arm process requirement absorbed isolation, the sandbox had two jobs left — cheap disqualification before the index bill, and permanent residency for unportable black boxes — and both are policies on an opaque node, not a regime. **The fitting contract carries no `regime` field.** It carries `depth`, `effects[]`, `execution_mode`, and opaque-node admission conditions.

Re-opening B terminated immediately: B as drafted has no isolation domain ("B is D minus the jail"), no admission story for foreign engines, and its named aging failure is opaque nodes quietly swelling into whole modalities — which is precisely what D4's computed depth, published decomposition ratio, default-selector exclusion, TTL-with-recorded-renewal, and shared-artifact write gate repair. B with those amendments *is* D4.

**Ranking:** D4 1st, D2 a declared near-tie, D1 3rd, D5 4th. D4 became the base rather than D2 on three grounds: its depth is structure-derived where D2's rests on manifest self-reports at the edges; its one unpatched item is a single taint rule where D2's are two internal contradictions (one between its own two headline advantages); and it takes the loop away from the component, which D2 alone leaves inside. D2 wins on gate engineering, and all of it was grafted across without its adapter-first thesis.

**Two of four strongest claims died.** D2's T1-from-opacity was killed as a discriminator — extracting evidence-tier measurement from a black box requires the part to consume machine chunks verbatim, i.e. to have surrendered its chunker, the largest code-verified port cost, so cheap admission and T1 cannot both hold. D1's promotion path proved **not machine-operable**: its trigger is a human typing a `part_ref`, and the machine explicitly declines to support that decision with a quality claim — the one decision the two-kingdoms boundary exists to govern is the one decision the machine cannot make. D5 mispriced its own cost as latency when the real denomination is directional Type II bias into a loop whose power for a genuine +5 pp effect is ≈0.10.

**Three gaps no variant caught alone** — the failure mode independent drafting is structurally blind to, since all four inherited the same brief:

- **SA-3, the migration component**, is absent from all four. All four have the reindex *planner* (classifies and prices); none has the *migrator* (transforms `recipe@vN → vN+1`). RT-upgradability marks it "applies to all" and calls it the amendment that turns every upgrade scenario from a project into a component someone writes on a Tuesday. Traced to BRIEF §4's omission.
- **`ItemKind` was never restored** as an open recipe-declared registry over a typed union; all four kept `kind` as a scalar field. Every stage-diffing and T1 claim in the lineup depends on the restoration.
- **The RFC 7386 + fail-closed-subtraction rule was unsatisfiable as briefed** — 7386 expresses removal as a `null` sentinel, so a mistyped key is a silent no-op by construction. The defect was introduced in BRIEF §2, not by the variants; all four restated it verbatim. Amended in place: merge-patch for additive deltas, RFC 6902 for subtractive. Spike 004 had already measured the failure — a one-character typo produced an arm reporting "reranker dropped" that shipped with the reranker still in it.

**Compliance: no VIOLATED cells, nothing disqualified**, but 3 of 20 self-certified passes were downgraded — D1 DQ-4 (digests the *declared* closure, not the resolved one — the exact Feast skew the environment hash exists to kill), D4 DQ-2 (guard written read-only-at-runtime guards the wrong direction; a control channel *is* a read), D5 DQ-1 on the ephemeral-subgraph clause (hosts a runtime multiset over a static alphabet, not a per-query sub-query DAG — the clause D5 claimed as its cleanest win). D2/D4 DQ-5 UNCLEAR. All are repaired as conditions on the selection.

**Spike-002 amendment.** The condition that cross-regime comparison be "honestly labeled shallowest-denominator" is **rejected** — it was never in the settled set, and three of four variants independently replaced it. Comparison is now defined at the **greatest common depth of the two arms**, which is deeper than the answer tier whenever both arms share deeper boundaries. The honesty half survives (every row labeled, every cross-label join refused or explicitly projected); the resignation half is repaired rather than accepted.

**The selection is correct-by-reasoning, not yet correct-by-evidence.** The taint rule that patches D4's laundering hole is an argument, and Falsifier 1 is its measurement: build the half-decomposed wiring and confirm taint both permits the ingest-adapter's shared writes and refuses an opaque-fed extractor's. If it blocks every middle state, D4's ratchet has no usable middle, D1's cliff is vindicated, and the two-regime design re-opens. Needs a paper wiring walk plus one validator prototype — no corpus.

**One falsifier outranks the selection itself:** if an affordable eval bundle stays at 30–50 questions with binary answer-judging only, no promotion claim in this architecture is meaningful and the improvement loop is a random walk with a scoreboard. That is inherited, not created here, and step 10's rig design must settle it.

**Output:** `.planning/architectures/D-VARIANTS/SELECTION.md` §Contract skeleton — twelve numbered sections, spec-grade, and the direct input to SPIKE-PLAN step 8. Where it and any variant document disagree, it governs.
