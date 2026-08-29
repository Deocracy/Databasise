# Architecture Selection — SETTLED

**The architecture is chosen. This file used to say "amended-D leads, formal selection deferred." That is superseded.** Spike 003 selected **D4 One Machine**, and in the same act ruled that D's two-regime structure collapsed: D4 *is* candidate B with the amendments the evidence forced.

Full reasoning: `sources/003-d-variants/SELECTION.md`. The contract skeleton it implies is `references/selected-architecture.md` — that is what you build from.

## Requirements

- **There is one machine. There is no sandbox regime, and the fitting contract carries no `regime` field.** It carries `depth`, `effects[]`, `execution_mode`, and opaque-node admission conditions.
- A whole foreign engine is a **node of opaque kind** in the same wiring, run by the same executor, traced into the same schema, identified by the same `(name@version, config_hash, resolved_dependency_ids)` tuple, gated by the same promotion gate.
- **Promotion is node → subgraph decomposition in place.** The node id is unchanged, depth is recomputed, and every wiring naming that node keeps working because a subgraph *is* a node. Decomposition is therefore idempotent.
- **Depth is computed by the validator, never declared.** Containment is derived from declared effects, never requested.
- Eval bundle + promotion gate → isolation domain → architecture. Sequencing unchanged and still binding.

## What was decided, and why

### The four candidates, final standing

| Candidate | Final status |
|---|---|
| A Stage Bus | Disqualified (cannot loop; cannot host black boxes/CAG). Its boundary-ownership property was imported and survives. |
| B Conductor | **Effectively selected, as amended.** D4 is B plus the jail, the opaque node kind, and computed depth. |
| C Federation | Not an architecture. Its only surviving contribution is the foreign-part adapter, now priced as a fixed cost in any design. |
| D Kernel+Sandbox | **Collapsed.** Every property the regime bought is re-provided per node. |

### Why D collapsed

Spike 002's case for D was that registry growth and blast radius are both *structurally* bounded by a regime that may be thrown away. All four variants — three by design, D1 only by admitted exception — independently replaced that with the same per-node rule:

> **You cannot mutate what you have not decomposed.**

An opaque node's only mutable surface is its config and position, so registry growth scales with decomposed surface. That is D's bound, obtained without a regime. Once per-arm process isolation absorbed the isolation job, the sandbox had exactly two jobs left — cheap disqualification before the index bill, and permanent residency for structurally unportable black boxes — and both are **policies on an opaque node**, not a second execution regime.

Re-opening B terminated immediately: B as originally drafted has no isolation domain ("B is D minus the jail"), no admission story for foreign engines, and its named aging failure is opaque nodes quietly swelling into whole modalities. D4's computed depth, published decomposition ratio, default-selector exclusion at `opaque`, TTL-with-recorded-renewal, and shared-artifact write gate are exactly the repairs for that failure.

### The variant lineup and what each proved

| Variant | Position | Outcome |
|---|---|---|
| **D4 One Machine** | one executor; sandbox is a capability set, not a regime | **Selected.** "The kernel is not a place, it is a depth." |
| **D2 Instrument Bus** | instruments as a regime-independent third block; adapter-first promotion; depth on the evidence item | Near-tie. Gate and evidence engineering grafted wholesale. |
| **D1 Two Kingdoms** | hard boundary everywhere; promotion = full re-implementation | Rejected — its promotion trigger is a human, so the one decision the boundary exists to govern is the one decision the machine cannot make. |
| **D5 Actor Kernel** | actor/message-passing executor | Rejected — no structural bound, and its cost is directional Type II bias, not latency. Four contract clauses survive. |

D3 "Nix Unit" was retired before drafting: spike 004 removed both its distinguishing properties.

## What to avoid

- **Do not reintroduce a `regime` field, a second executor, a second trace schema, or a second identity vocabulary.** The whole selection is the finding that these have no work left to do.
- **Do not let depth be self-declared.** D4's depth is structure-derived from wiring + registry; D2's edge-case self-report was the reason D2 lost the tie. A part that can name its own depth can inflate it.
- **Do not let capabilities buy freedom.** Declaring an effect must *cost* containment. A foreign engine's large capability set forces the heaviest containment automatically, with no human deciding it belongs "in the sandbox".
- **Do not treat the foreign-part adapter as a discriminator.** Process lifecycle, RPC, health, corpus-feed handoff, and evidence normalization exist in any design that hosts a foreign engine. It is a fixed cost.
- **Do not compare rubric scores across the four variant documents.** The four scales are mutually incommensurable (Strong/Partial vs 39/50 vs yes/partial) and were excluded from the selection rather than re-derived.
- **Do not treat this selection as measured.** See Constraints.

## Constraints

- **The selection is correct-by-reasoning, not correct-by-evidence.** The taint rule patching D4's one hole is an argument, not a measurement.
- **Falsifier 1 (decisive, cheap, unrun):** build the half-decomposed wiring `{ingest-adapter(stage), opaque-query-core, assembler(stage)}` plus an index-side variant where the opaque core feeds an extractor. The taint rule must **both** permit the ingest-adapter's shared writes **and** refuse the opaque-fed extractor's. If it blocks every middle state, D4's ratchet has no usable middle, D1's cliff is vindicated, and the two-regime design re-opens. Paper wiring walk plus one validator prototype; no corpus needed.
- **Falsifier 2:** if `depth` and `execution_mode` cannot be computed statically over three real parts (decomposed `lightrag-local`, opaque `codebase-memory-mcp`, half-decomposed LightRAG), D4 has no brake and D's regime was doing structural work.
- **Falsifier 3 outranks the selection itself:** if an affordable eval bundle stays at 30–50 questions with binary answer-judging only, no promotion claim in this architecture is meaningful and the improvement loop is a random walk with a scoreboard. Power for a genuine +5 pp effect is ≈0.10; a naive adopt-if-higher rule promotes noise ~5:1. Inherited from spike 002, unsettled, and step 10's rig design must resolve it.

## Amendments to earlier spikes

- **Spike 002's "shallowest-denominator" condition is REJECTED.** It was never in the settled set, and three of four variants independently replaced it. Comparison is defined at the **greatest common depth of the two arms**, which is deeper than the answer tier whenever both arms share deeper boundaries. Its honesty half survives (every row labeled, every cross-label join refused or explicitly projected); its resignation half — "the promotion decision always runs on the least informative evidence" — is repaired, not accepted.
- **Spike 004's arm-delta requirement is amended:** RFC 7386 alone cannot express fail-closed subtraction. See `references/wiring-spec-and-validation.md`.

## Origin

Synthesized from spike 003 (four independent Opus drafts, cross-variant red team, compliance verification, Fable selection), superseding the spike-002 selection state.
Sources in `sources/003-d-variants/` — SELECTION.md governs; RED-TEAM.md and COMPLIANCE.md carry the evidence; the four variant documents are preserved because losing variants document the roads not taken and their falsifiers.
