---
title: Cross-Variant Red Team — D1 / D2 / D4 / D5
spike: 003
date: 2026-08-10
status: archived-with-standing — the cross-variant adversarial pass whose per-variant attacks and verdict summary SELECTION.md's ruling relies on as evidence, not itself superseded; tracked at SYSTEM-MODEL.md ## §ST
inputs: D-VARIANTS/BRIEF.md, D1, D2, D4, D5, RT-modularity, RT-upgradability, RT-selfimprove, ARCHITECTURE-RUBRIC, WIRING-SPEC-DRAFT, GAP-SWEEP
---

# Cross-Variant Red Team — spike 003

**Evidence provenance for this pass.** Everything quoted from `.planning/redteam/*`, `ARCHITECTURE-RUBRIC.md`, and `WIRING-SPEC-DRAFT.md` was read this session and is tagged `[docs-verified]`. **No `[code-verified]` claim in any of the four variants was checked against source this session** — the line counts (794 / 1,786), `_generate_collection_suffix()`, strategy-`V` embedder coupling, the `rename(2)` timing, and the 43-abstract-method count are all inherited from ANATOMY-REVIEW / spike 001 / spike 004 with attribution intact. Where I rely on one, it is tagged `[code-verified, inherited]`. My own analytical claims are `[inference]`.

---

## Verdict summary

| Rank | Variant | One-line rationale |
|---|---|---|
| **1** | **D4 One Machine** | The only variant whose central mechanism is both novel and mechanically checkable, and the only one that correctly states the bound that actually replaces D's promotion cliff. Its one unpatched hole is a laundering path through a stage-depth node, and its honest conclusion dissolves D into B-plus-a-label. |
| **2** | **D2 Instrument Bus** | Near-tie with D4 — the same structural bound reached from the other end, plus the three best contract items in the lineup (pooling key, veto-only cross-tier, `insufficient-depth`). Its headline claim is broken by a conflict with its own ingest rule, its pooling key contradicts its own S2, and it is the only variant that leaves a component owning its loop. |
| **3** | **D1 Two Kingdoms** | The cleanest boundary and the most honest refusals, but its promotion trigger is a human typing a `part_ref`, which makes the one decision the boundary exists to govern the one decision the machine cannot make. It also breaches its own population bound by admitted exception, and its re-promotion answer is a scheduled ritual where the other three have a structure. |
| **4** | **D5 Actor Kernel** | Highest contract yield in the lineup and the cleanest DQ-1.2 answer; worst operational risk. It moves two load-time refusals to run-time where they become *scored low arms* rather than rejections — that is measurement bias, not the latency cost D5 priced — and it has no prior art to adopt against an explicit adopt-list pointing the other way. |

Margins are stated honestly in §Ranking. D4/D2 is a near-tie. D1 is a clear step below on machine-operability and a clear step above on contract cleanliness. D5 is last on risk and first on contract contribution; if selection's job is to harvest clauses rather than pick an implementation, D5's yield is the highest in the set.

**The single most important finding in this pass is not in F1–F10.** All four variants converge — three by design, one by admitted exception — on *kernel population is bounded by the cost of decomposition, not by the regime boundary*. D1 reaches it in its own Disadvantage 1 ("D1 must therefore admit query-wiring-class parts **directly to the kernel**"), which punches the same hole D2/D4/D5 punch on purpose. Once all four agree on that, the regime boundary is doing less work than the lineup was built to test, and D4's conclusion — that D is B plus a computed label plus per-arm isolation — is not one variant's opinion but the lineup's emergent answer. [inference]

---

## Adjudication of F1–F10

### F1 (from D1) — the "same corpus feed" edge and the chunk-tier hazard

**Ruling: true as a hazard, false as a discriminator, and D1's answer is an over-correction that costs it.**

The hazard is real and code-verified upstream: chunker strategy `V` consumes the embedder, so chunk boundaries are a function of the embedding model [code-verified, inherited, ANATOMY-REVIEW F2/F3]. But D1's implication — that other variants keeping a chunk-tier feed assert something false — does not survive checking what they actually wrote:

- **D2**: chunkers declare `embedder_coupled: bool`; an embedder-coupled chunker's KV output is stamped with the embedding sub-recipe and **is not admitted to the shared lane** — recipe-bound like a graph.
- **D4**: the chunk artifact's SA-2 stamp includes embedder identity when the strategy is coupled; **the validator refuses** a wiring reading an embedder-stamped chunk artifact with a different embedder pinned. "The shared-KV claim survives only for `F`/`R`/`P`, and it survives as a checked property."
- **D5**: "embedder-dependent chunkers are recipe-bound and excluded from the shared lane, declared per-chunk in the provenance stamp."

All three handle it, and all three handle it *better* than D1 does: they keep the cheap shared feed for the three uncoupled strategies and refuse only the coupled one. D1 refuses the entire chunk tier unconditionally, then re-opens it as "a declared, optional upgrade for a sandbox part that accepts a *specific* chunker stamp" — which is D2/D4/D5's rule, arrived at two paragraphs later and called an exception. **D1 pays C's full N× re-chunk-and-re-embed bill to buy a property the other three get with one boolean.** [inference]

**Effect on ranking:** F1 costs D1, does not touch D2/D4/D5, and removes what D1 presented as a cross-variant indictment. D1's own Disadvantage 5 and falsifier 4 already price the cost it took on.

**The part of F1 nobody saw.** All four treat the feed tier as a *correctness* question (does the chunk stamp match?). None treats it as a *confound* question. A foreign engine tuned to 512-token chunks, handed the machine's 1,200-token chunks, is measured with a handicap the scoreboard attributes to the engine. D1's document-tier feed removes that confound and introduces its mirror (each part chunks differently, so the comparison is "part+its chunker" — which is the honest unit for a *whole-engine* claim and the wrong unit for an *engine-core* claim). Neither tier is right in general; the tier is a choice of what the comparison controls for, and no variant says so or proposes running both. See §Shared blind spots #6.

---

### F2 (from D1) — is amendment C-1 subsumed?

**Ruling: no. D1 has misread C-1. D1's operational conclusion is nevertheless correct, and D2's replacement mechanism is wrong in the mirror direction.**

C-1 reads: *"Embedder identity is a required manifest field; the broker refuses cross-engine comparison on mismatch"* [docs-verified, RT-upgradability §7 amendment index]. D1 reads the protected comparison as a *stage-tier* one and concludes the refusal only guards something D1 already refuses.

Read C-1 in its own context and that is not what it protects. RT-upgradability §2's C row: *"'upgrade the embedding model' is not one event in C — each engine pins its own embedder on its own upstream schedule, so at any moment the fleet is mixed and cross-engine comparison is quietly invalid"* [docs-verified]. The invalidity is **temporal, not tiered**: engine A has been re-indexed on the new embedder, engine B has not, and the measured delta partly encodes the upgrade schedule rather than the engines. That contaminates the *answer-tier* comparison specifically — the one D1 says it wants.

So C-1 is not subsumed. But D1's *policy* conclusion is right for the reason D1 gave second: at answer tier over one corpus and one eval bundle, the embedder is part of what the engine *is*, and refusing to compare two whole engines because they embed differently forbids the comparison the sandbox exists for. Both documents have half of it:

- D1 keeps the right policy (permit answer-tier cross-embedder comparison) on the wrong reason.
- D2 states the right reason (a pooling key makes comparability decidable) and then over-applies it: **`space_id` is in D2's pooling key unconditionally, at every tier including T0.** A self-embedding sandbox engine reports `space_id: opaque`, and "opaque-space evidence is never pooled with machine-space evidence." That makes D2's own S2 headline — *"`lightrag@2.0` runs in the sandbox the day it ships and produces T0 evidence against the same eval bundle"* — **illegal under D2's own contract.** This is an internal contradiction, not a nuance. [inference]

**The correct restatement of C-1**, which no variant has: *the refusal is on comparing one engine's evidence against its own evidence from a different embedder generation, not on comparing two engines with different embedders.* Mechanically: `space_id` belongs in the pooling key at T1 and deeper (where scores and refs are space-bound) and must be excluded at T0 (where the engine's embedder is an attribute of the thing under test, and the engine's *instance hash* already pins it).

**Effect on ranking:** neutral-to-negative for D1 (correct conclusion, wrong derivation, and it retires an amendment it did not correctly read), and a concrete defect in D2's most load-bearing single clause. D2's fix is one line; the defect is real as written.

---

### F3 (from D2) — the structural bound, and whether a priced bound is acceptable

**This is the selection's central axis and F3 is substantially correct, but not in the form D2 states it.**

Source: *"D bounds the explosion structurally if the improvement loop is declared kernel-only **and** the kernel population is capped (3–5 modalities). Registry growth then scales with kernel size, not with total modality count"* [docs-verified, RT-selfimprove §1.5]. And falsifier 4: *"Kernel population is not capped — attack 1's artifact/trace growth becomes unbounded and D loses its only structural advantage over B"* [docs-verified, §7].

They are not the *same* bound; they are the two multiplicands of one product. Registry growth = (parts inside the loop) × (mutations per part). "Kernel-only" bounds *which* parts are inside; port cost bounds *how many* there are. D2 is right about the operative consequence: **if promotion is cheap, "kernel-only" is vacuous, because everything ends up in the kernel.** [inference]

**Is a priced bound acceptable? Only if the price is structural.** Scored:

| Variant | What replaced the bound | Verdict |
|---|---|---|
| **D4** | *"An opaque node has nothing to mutate but its config and its position, so registry growth scales with the number of **decomposed** nodes — which is exactly D's bound, obtained without a regime, because 'kernel' and 'decomposed' were always the same set."* | **Structural, and correctly stated.** The strongest answer in the lineup. |
| **D2** | Forcing function 1: *"Mutation surface equals realized nodes. This is a mechanism, not discipline. You cannot mutate what is not a node."* | **Structural — and D2 disowns it.** Disadvantage 1 calls all three replacements "policy with instrumentation, not structure," which contradicts its own §Promotion. D2 under-scores itself here; the honest reading raises it. [inference] |
| **D1** | Nothing — the original bound is kept via expensive re-implementation. | **Intact on paper, breached in practice.** D1's Disadvantage 1 admits query-wiring-class parts *directly to the kernel* to avoid being worse than kernel-direct. That is the cheapest and most numerous class, entering free. D1's bound now has the same shape as D2/D4's — bounded by decomposition cost — reached by exception rather than design, and not named as such. [inference] |
| **D5** | Adopts D-1 and D-2 *"without modification"*; the partial-promotion ladder makes entry cheaper than any other variant. | **Not replaced.** D5 has the same mutable-surface argument available (a confined whole engine has no internal templates to mutate) and never makes it. This is the sharpest gap in D5's argument and F3 bites it hardest. |

**Ruling:** a priced bound is acceptable *iff* the price is "you cannot mutate what you have not decomposed." That is structural, it is enforced by the wiring format rather than by policy, and three of four variants either state it (D4), state-then-disown it (D2), or arrive at it by exception (D1). D5 alone leaves the bound to policy.

**Effect on ranking:** D4 up, D2 up (against its own self-assessment), D1 down (its distinguishing bound is not distinguishing), D5 down.

---

### F4 — the tier field is already settled; the live question is gate policy

**Ruling: verified. `WIRING-SPEC-DRAFT.md:132` reads verbatim** [docs-verified, checked this session]:

> *"Every arm's evidence records the instance hashes that produced it, and the evidence-depth tier, so cross-regime comparisons can never silently mix quality levels."*

Axis 5 is therefore not a design choice any variant was free to lose. It is pre-committed into settled arm mechanics, and all four correctly implement it. **Axis 5 discriminates far less than the lineup assumed.**

**Adjudicating the gate policy question.** The four positions, compared on mechanism rather than on prose:

| Variant | Rule for combining tiers | Assessment |
|---|---|---|
| D1 | Wiring tier = **minimum over its nodes**; cross-tier scoreboard joins return a typed refusal; gate accepts `kernel-deep` only | Minimum-over-path plus a policy of never gating on the shallow tier |
| D4 | Wiring depth = **minimum over the compared path**; rig refuses to pool across labels but may compare at the common denominator | Minimum-over-path — *the same computation as D1* |
| D2 | Rule 1: compute the **greatest common depth**, project both arms down, one paired test there | Greatest-common-depth — *again the same computation*, stated from the comparison's side rather than the wiring's |
| D5 | Compare on the **deepest common boundary type set**; flag underpowered when only the answer boundary is common | *The same computation again*, with boundary types instead of node labels |

All four compute the same thing. Only one adds a rule beyond it:

**D2's Rule 4 — cross-tier evidence may veto, never support** — is the only asymmetry in the lineup, and it is strictly correct. A T0-observable hard-gate regression (citation validity, `refs_resolved < refs_in`, latency/token ceiling, schema conformance) killing a promotion justified at T3 is conservative in the safe direction; the reverse never is. **Every variant should adopt Rule 4 regardless of who wins.** D2's second contribution, `insufficient-depth` as a verdict distinct from `inconclusive` — *"`inconclusive` tells you the change did not help; `insufficient-depth` names the instrument you are missing"* — is the same class of item and should also be adopted lineup-wide.

**What the gate may conclude from a labelled mix, settled here:** compute the greatest common depth; run exactly one statistic there; permit deeper-tier evidence to *veto* and never to *support*; return `insufficient-depth` (naming the missing instrument) rather than `inconclusive` when the claim class outruns the available tier; and never gate on evidence whose depth was downgraded by a runtime audit.

**Effect on ranking:** axis 5 nearly stops discriminating. What remains is D2's veto asymmetry and refusal vocabulary, which is a genuine and transferable D2 win.

**A hole in all four:** none states whether the *hard-gate* suite must itself be observable at the tier the promotion is decided at. D2's Rule 4 implies the answer (no — vetoes are evaluated wherever observable); the other three leave it open.

---

### F5 (from D4) — does D's isolation naming conflate two jobs?

**Ruling: true of the *drawn* D, already resolved by the settled set, and therefore not a variant discriminator.**

RT-selfimprove already made this exact move: *"CANDIDATES describes the sandbox as a hosting convenience for external engines, not as a security boundary. **Respecifying the sandbox as the isolation domain for untrusted mutations is the single change that most improves self-improvement safety across the whole design**"* [docs-verified, §3.1]. And machine service #2 as bound by BRIEF §2 already reads *"per-arm process"* — unconditional, for every variant.

So per-arm process isolation is mandatory in all four before any variant chooses anything. F5's operative content is settled, not discovered.

**Two consequences the drafters missed in opposite directions:**

1. **D1's Advantage 4 ("One isolation mechanism, two jobs") is not a D1 advantage.** Every variant builds service #2 for per-arm isolation and every variant then hosts foreign parts in it at the marginal cost of a unit file. D1 claims as a differentiator something the settled set gives to all four. [inference]
2. **F5 does narrow D's justification, correctly.** With isolation consumed by the per-arm requirement, the sandbox is left with exactly two jobs from RT-selfimprove §5: *cheap disqualification before paying the index bill* (a new index recipe trialed on a 500-chunk sub-corpus for ~5% of the token bill) and *hosting parts that structurally never port* (black boxes; "these never promote, and that is correct behaviour, not failure") [docs-verified]. Both survive. The sandbox is narrower than D drew it and is not eliminated.

**Effect on ranking:** removes one claimed D1 advantage; does not reorder.

---

### F6 (from D4) — D4 deletes the duplication, not the capability

**Ruling: true, self-reported, and it generalizes further than D4 took it.**

D4's own Disadvantage 3 states it: *"The foreign-node adapter — process lifecycle, RPC, health, corpus-feed handoff, evidence normalization — is C's broker folded into the executor. It still has to be written... Anyone scoring D4 as 'half the surface of D' is scoring it wrong."* Correct, and it should be honored in scoring.

**The generalization D4 did not draw: this is a fixed cost in all four.** D1 must feed documents into a jailed engine and normalize an answer back out — same lifecycle, same handoff, same normalization, plus a jail-policy satisfiability checker. D2's adapter node kind is the same object with a manifest. D5's confined-unit-as-actor is the same object behind a mailbox. **The foreign-part adapter is not a variant-specific cost and should be removed from every variant's cost accounting as a discriminator.** D1 gets partial credit for noticing half of it ("sandbox parts must be packaged as confined units, which is real per-part work and is where 'the sandbox is cheap to admit to' is least true in D1"); none of the four prices it as common. See §Shared blind spots #5. [inference]

**Effect on ranking:** removes a phantom D4 advantage and a phantom D1 advantage. Net neutral between them; net negative for any scoring that read either as cheap.

---

### F7 (from D5) — does the kernel-style dispute reduce to the semantics of one arrow?

**Ruling: very nearly true, and the one residue it leaves is a hole in the *other three*.**

D5's claim: *"Every static property a declared-graph kernel has that D5 lacks is a property that depended on an edge meaning 'exactly once, in this order.'"* Tested item by item against D5's own residue table:

- `provides` weakening — depends on exactly-once. ✓
- Multiplicity ("exactly one generator runs") — exactly-once. ✓
- Message ordering / protocol conformance — the "in this order" half. ✓
- Query-encoder `space_id` check moving load→spawn — depends on *when the instance set resolves*, which is the "zero or more times" half. ✓
- Deadlock — D5 correctly notes no declared-graph kernel proves termination of loop-with-condition either; not a differentiator. ✓

**The residue that breaks the reduction: scheduler nondeterminism is a consequence of concurrency, not of edge semantics.** D5 books it as its own cost (Disadvantage 2, *"D5 adds an independent variance source... this is D5's most expensive property"*). But a declared-graph kernel executing fan-out branches *concurrently* has exactly the same variance source. D1, D2, and D4 all specify fan-out with runtime arity, and **not one of them says whether branches execute concurrently, or what concurrency does to the A/A null.** D5 is the only variant that noticed the problem and it mis-attributed it to itself. [inference]

**Effect on ranking:** F7's operative recommendation — *the fitting contract must name edge semantics explicitly rather than inherit it* — is correct and should be adopted whoever wins; it is the most valuable single line D5 contributes. And the residue relatively *helps* D5 (part of its worst cost is lineup-wide) while exposing an unnamed variance source in the other three. See §Shared blind spots #4.

---

### F8 (from D5) — is the ephemeral-subgraph residue D5-specific?

**Ruling: not D5-specific — it generalizes a real cost to the lineup and leaves D5 with a smaller but genuine edge. D5's DQ-1.2 advantage is reduced, not neutralized.**

What the four actually do with a planner-emitted plan:

- **D1**: *"Because a planner-emitted plan is untrusted input authored at runtime, it passes through the **same** static validator as any mutation-authored wiring, against a restricted node-kind allowlist plus the caps the planner's own manifest declares."* A real answer — and it means a validator invocation, reading the component registry, **inside a run**, priced at ~22 ms per planner-bearing query [inherited, spike 004].
- **D2**: silent. The planner emits a plan recorded as trace data; nothing says it is validated. D2 simultaneously declares *"During a run the bus is **write-only** from the execution plane's perspective"* — which forbids the registry read D1's answer requires.
- **D4**: *"The executor executes that value under a budget derived from the enclosing enclosure, and records it as trace data."* No validation named. **By omission, D4 accepts an unvalidated runtime-emitted graph** — a real DQ-1.2-adjacent gap.
- **D5**: the emitted object is a `SpawnRequestList` — a multiset over a static, pre-validated alphabet. Three spawn-time checks (template membership, config schema, declared `max`). No graph validation because no graph.

So the residue is real for three of four, and D5's answer is genuinely the smallest unit. But D5 oversells the gap: D1 *has* an answer, and its cost is 22 ms of query latency plus one contested registry read, not an unbounded exposure.

**The more interesting finding underneath F8: three-way disagreement on a settled disqualifier's boundary.** May the executor read the artifact plane mid-run? D1 says yes (to validate an emitted plan), D2 says no (bus is write-only during a run), D5 says no (spawn-time frozen resolutions, stated as its single most important contract sentence), D4 is silent. DQ-2 forbids *a component* treating the artifact plane as a control channel and says nothing about the executor. **This is an unresolved contract question the selection must settle, and it is not currently in anyone's contract skeleton.** [inference]

**Effect on ranking:** small D5 win preserved; a specific gap opened in D4 (unvalidated emitted plans) and in D2 (silence plus a rule that forbids the obvious fix).

---

### F9 (from D5) — is D5's freedom query-side only, and does that halve its thesis?

**Ruling: literally true, and misleading as an argument. F9 damages D5 much less than it appears to.**

The literal claim is D5's own: *"The ingest lane is statically pinned... SA-1 requires recipe identity to be a content hash of resolved inputs, which is only computable before the run if the recipe's actors and their dependency closure are known before the run. D5's dynamic-topology freedom is therefore a query-side property only."* Correct, honest, and load-bearing on SA-1, which is settled.

The framing that the query side is "per spike 001 the *cheap* half" is a **port-cost** framing (794 lines vs 1,786) [code-verified, inherited]. The relevant framing for a machine whose central loop is machine-authored mutation is **mutation volume**, and there the numbers invert: *"one index-recipe mutation ≈ 7 days of query-side experimentation... Index-side mutations need a separate, far stricter rate limit"* [docs-verified, RT-selfimprove §2.7]. The improvement loop runs almost entirely on the query side. D5's freedom therefore applies to precisely the half where the loop lives.

**The counter that keeps D5 down anyway:** all of D5's costs land on the same half. The widened A/A null, the `provides` weakening, the spawn-time `space_id` check, and the multiplicity band all sit in the query lane. D5 concentrates both its benefit and its cost in the same place, and which dominates is unresolved by any evidence we have (D5's falsifiers 2 and 3).

**Effect on ranking:** F9 as stated should not be used against D5. The correct charge against D5 is on the *costs*, not on the coverage. [inference]

---

### F10 — the convergence on machine-computed depth

**Ruling: it is a four-way convergence, not two-way; it is substantially inherited from the brief and the settled spec; and the genuinely independent part of it is correct but has an unnoticed hole.**

**It is four-way.** D2 (Rule 5, machine-stamped), D4 (statically computed, dynamically audited), D5 (inferred from boundary types crossed) — and **D1 as well**: *"a wiring's evidence tier is the minimum over its nodes."* That is the same computation as D4's minimum-over-path. D1 dissents on *gating policy*, not on computing depth. The convergence claim as framed undercounts by one.

**It is substantially inherited.** `WIRING-SPEC-DRAFT.md:132` already commits the evidence-depth tier field, and BRIEF §6 required a "Comparison depth" section describing "how kernel-deep and sandbox-shallow evidence are labelled." Four drafters converging on a field the binding spec already contains is weak evidence.

**The genuinely independent part is "computed, never self-declared,"** which neither the brief nor the spec says. That part is correct — and it is also *partly a rediscovery of a settled clause*: contract clause 3 (`deref` raises loudly; runs record `refs_in`/`refs_resolved`; the gate fails runs where they differ) already converts a false ref-based depth claim into a loud failure. D2's Rule 5 and D4's runtime audit are both that clause pointed at the tier field. Where the rule is genuinely new is at the **stage/node** tiers, which are not ref-based and can only be computed from wiring structure; D4's formulation (registry-resolved non-opaque leaves) is the operational one.

**The hole none of the four found.** The deepest tier — the one that licenses a *causal* claim about one node — rests on an unverifiable self-declaration in every variant:

- D2's T3 requires *"realized nodes with declared **determinism**"* — self-declared, and Rule 5 explicitly does not cover it ("it protects the depth tier, not the debt denominator" — nor the determinism flag).
- D5 requires a scheduler determinism *setting*, also declared.
- D4's `held_constant` set is computed from recipe hashes, which is the strongest of the four, and still cannot establish that a node is deterministic.

**So "never self-declared" fails at exactly the tier that supports causal claims,** and the fix is cheap and proposed by nobody: re-run the node on identical input and compare the output; a node that fails is downgraded out of the intervention tier. [inference]

**Effect on ranking:** the convergence is a real signal for the *rule* and a weak signal for the *design*, because it discriminates nothing (all four have it). It gives D4 a small edge for having the only structure-derived formulation, and it opens a shared hole. See §Shared blind spots #7.

---

## Attacks on the strongest claims

### D1 — "refusing cross-regime deep comparison *deletes* RT-modularity's indictment"

**Verdict: DAMAGED, and the damage is at the system level, not the argument level.**

The indictment [docs-verified, RT-modularity Attack 4, D row]: *"the rig compares kernel parts deeply and sandbox parts shallowly, so any cross-regime metric is defined at the shallowest common denominator. **The promotion decision — 'is porting this worth it?' — is therefore always made on the least informative evidence the system produces.**"*

The indictment is about **the decision**, not about the gate. D1 removes the *machine* from the decision; it does not remove the decision. Someone still decides whether to port. In D1 that person decides on:

1. the answer-tier scoreboard rows — *the least informative evidence the system produces*, unchanged; plus
2. a **demand counter** — "explicit sandbox invocations per part per week."

D1 calls the counter *"the only honest cross-regime signal in a design that refuses cross-regime quality claims."* Attack: because D-1 excludes sandbox parts from the default selector, **every invocation is an operator or the rig typing a `part_ref`.** The counter measures operator curiosity, not quality, and it is strictly *less* informative than the answer-tier score it is meant to supplement. D1 has traded a weak measurement for a non-measurement plus a human judgment, and then correctly recorded the judgment as a judgment.

**The system-level hit is worse than the epistemic one.** The project's subject is a self-improving machine. D1's `port-authorized` record is triggered by a signal a machine cannot generate and gated by *"a recorded human or agent judgment; the machine explicitly declines to support that decision with a quality claim."* **D1's promotion path is not machine-operable.** The one decision the two-kingdoms boundary exists to govern is the one decision D1 hands back to a person. [inference]

Second line: D1's answer to "but shallow evidence might still be a useful *work-ordering* heuristic" is in its own Disadvantage section — *"D1 forbids even that... That is the sharpest live threat to this variant and it is testable"* (falsifier 1). D1 named the attack and did not answer it. Honest, and it stands.

**What survives:** D1 does delete the *false precision*. A gate output computed from shallowest-denominator evidence carries a statistical costume it has not earned; a `port-authorized` record with a reason does not. That is a genuine and unshared win on the honesty axis, and it is worth one line: **D1 is the only variant that cannot silently promote on bad cross-regime evidence, because it has no path by which such evidence reaches a decision the machine makes.** It is also the only variant where the machine makes no cross-regime decision at all.

---

### D2 — "depth-on-the-item yields gold-passage recall from an opaque part"

**Verdict: KILLED as a discriminator; survives as a correct design rule.** Two independent lines, either sufficient.

**Line 1 — the claim conflicts with D2's own cheapest-entry claim.** T1 requires the part to emit evidence whose refs resolve as `ChunkRef = (corpus_id, recipe@version, ordinal, content_hash)`. An engine that chunks internally — which is most of them; chunking is part of what LightRAG *is* — produces evidence at *its own* boundaries, which have no `ChunkRef`. So T1 from an opaque part requires the part to consume the machine's chunks verbatim, i.e. **to have surrendered its chunker**.

D2 has already made exactly that move: *"an adapter that declares `storage: machine` uses the machine ingest lane on admission, before any decomposition, because ingest is where the shared corpus lives."* And D2 also records, from its own citation, that *ingest is welded onto the modality object as `_PipelineMixin` reading `self.full_docs` / `self.doc_status` / `self.tokenizer`, and cutting it off is the single largest port cost* [code-verified, inherited, ANATOMY-REVIEW F6].

**Therefore: D2's admission cost is 1–3 days for a T0-only adapter, and the single largest port cost in the system for a T1-capable one.** The variant's two headline claims — cheap entry (Advantage 1) and retrieval-grade evidence from opacity (Advantage 2) — cannot both hold for the same part. D2 named the falsifier (*"take codebase-memory-mcp... attempt a `ChunkRef`-resolvable evidence emission"*) and did not notice that the mechanism of failure is the ingest coupling it cites three sections earlier. [inference]

**Line 2 — the statistical power claim is smaller than stated and is not D2's to claim.** RT-selfimprove §2.6 already lists both levers for *every* candidate: *"Measure retrieval, not answers, for retrieval-side mutations. Gold-passage recall@k / nDCG removes generator noise **and** judge noise entirely... the correct target for 5 of the 7 component types"*, and *"Continuous per-question scores... paired bootstrap at n=40 detects d≈0.44 SD at 80% power; at score SD≈0.25 that is ~11 pp absolute — better than 15–25 pp, **though still not enough alone**"* [docs-verified]. So the lever moves the MDE from ~20–25 pp to ~11 pp; it does not solve n=40, and it is available to all four (D4 uses it in S3 step 8; D1 has gold-passage targets in its eval bundle). **D2's only exclusive contribution is extending the lever to *opaque* parts — which is precisely what Line 1 kills for the black-box class.**

**What survives, and it is not small.** The tier ladder, the pooling key (once `space_id` is removed from T0 — see F2), Rule 4's veto asymmetry, and `insufficient-depth` as a verdict that names the missing instrument are all correct and all transferable. D2's contract yield is the second highest in the lineup. Its *thesis* is broken; its *clauses* are the best-engineered.

---

### D4 — "the second regime is unnecessary; the kernel is not a place, it is a depth"

**Verdict: SURVIVES the question it asked, with one unpatched hole — and its survival dissolves candidate D.**

**Attack 1 — the laundering path, and it is the real decisive test, not D4's falsifier 1.** D4 states the blast-radius rule per node: *"a node may write into a shared artifact namespace only if its computed depth is `stage`."* It then states, of a half-decomposed wiring `{ingest-adapter, opaque-query-core, assembler@2.2}`: *"Its depth is `opaque` (minimum over the path), so it is excluded from the default selector and **refused shared-artifact writes** until the opaque core is gone."*

Those are two different rules and D4 uses both. If the rule is **per node**, a `stage`-depth ingest-adapter in that wiring may write shared artifacts while the opaque core is still present, and opaque-derived state reaches the shared plane through a stage-depth relay. If the rule is **per wiring**, then a half-decomposed part cannot ingest at all, which destroys the "ratchet with a brake at each notch" that is D4's Advantage 5 — the middle state becomes useless and D1's cliff is vindicated.

The missing rule is a **taint rule**: a node's effective depth is the minimum over its transitive `deps`. The information is present (`deps` is in the wiring), so it is computable, and D4 does not state it. **This is the single most important unpatched hole in the lineup**, and it sits exactly where D4 predicts the pressure will come from: *"the fastest way to make a half-decomposed part useful is to grant its opaque core a store-write scope... nothing at all if the rule is relaxed once 'temporarily'."* [inference]

D4's own falsifier 1 ("depth cannot be computed statically") will **pass** — depth for a decomposed wiring, a `codebase-memory-mcp` node, and a half-decomposed LightRAG all fall out of the wiring plus registry mechanically. D4 has nominated the wrong decisive experiment. The decisive experiment is the laundering test.

**Attack 2 — the claim's consequence is larger than D4 books it.** D4 writes: *"'kernel' and 'decomposed' were always the same set,"* and *"D's lead over B collapses to 'B plus a computed label' — which is the 'B was right' outcome, reached with evidence."* Taken with RT-selfimprove §7's own framing — *"B is D minus the jail, plus the temptation to run mutated code in-process"* [docs-verified] — and with the settled per-arm process requirement supplying the jail, **D4 is an argument that the answer to spike 003 is B-with-amendments, presented as a D variant.** That is not a flaw in D4; it is the most valuable single output of the lineup and it must be handed to selection as such rather than absorbed as one variant's opinion. [inference]

**Attack 3 — the injected-endpoint dependency.** D4's token-comparability advantage (Advantage 6) is conditional on the machine being the engine's LLM provider. D4's falsifier 4 admits the failure mode. This is the one place where D4's "one rig" claim is contingent on third-party cooperation, and where it fails, D4 degrades to exactly the shallowest-denominator problem it exists to fix, having given up the two-regime clarity for nothing. D4 states this. It stands.

**Not attacked successfully:** the slogan itself. "The kernel is a depth, not a place" is correct, mechanically checkable, and strictly more expressive than a regime label. D4's examples (transparent-but-external, opaque-but-machine-stored) are both real and neither is nameable in D as drawn.

---

### D5 — "it survives static validation with a strictly smaller guarantee set"

**Verdict: SURVIVES narrowly on its own terms; the *consequence* is mispriced, and the mispricing is severe.**

**The claim itself holds.** The five static checks (mailbox types over declared send sites; capability monotonicity along `may_spawn`; supervision-tree well-formedness with finite restart budgets; spawn-cap presence; template-graph reachability and registry resolution) are all checks over a finite, static, JSON-encoded object, and the validator fails closed. Address unforgeability — D5's own falsifier 1 — is a real load-bearing assumption, and I could not construct a counter-example from the settled anatomy: the selector chooses a modality before the run's actors exist, harnesses interpose on addresses handed at spawn, and non-adjacent fan-in is a spawn-time handoff. I did not walk the 45 gap-sweep types (see §Provisional).

**The attack lands on the pricing.** D5 prices the smaller guarantee set as *latency*: *"D5 moves a band of defects from a 22 ms validator to a 2 M-token decision."* That is the wrong denomination. Two D5-specific paths deliver a structurally-invalid arm to the **scoreboard as a scored low arm** rather than to the validator as a rejection:

1. **Spawn-time `space_id` refusal.** D5 concedes it: *"the check 'the query encoder's `reads_space` equals the namespace's `space_id`' therefore runs at spawn, not at load. It still fails closed — the spawn is refused and the run produces a traced partial result."* And partial results are first-class: *traced and scored, never discarded*.
2. **`provides` reachability.** A wiring passes validation and emits no answer. D5's runtime hard gate catches the total case; it does not catch the *degraded* case where some questions answer and some do not.

In both, the arm arrives at the rig as a **legitimately-scored underperformer**, and the gate attributes the deficit to the mutation under test. D5's gate refusal list includes "any run that emitted no message of the declared `provides` type" but **does not include "any arm containing a spawn-time capability refusal."**

The consequence is not delay, it is **bias**, and it is directional: a systematic source of false-low scores *on challengers* in a loop whose power for a genuine +5 pp effect is already ≈0.10 [docs-verified, RT-selfimprove §2.1]. It inflates Type II error on an instrument that has none to spare. **That is a materially worse cost than the one D5 priced, and it is D5's most serious unaddressed defect.** [inference]

**Second attack — build cost, which D5 concedes and which is legitimate.** *"PRIOR-ART's recommendation is a Haystack-shaped executor... An actor kernel means writing a mailbox scheduler, a supervision tree, capability-carrying budgets, and a deterministic-replay test mode from nothing."* In a project whose deliverable is design and whose code is spikes, an adopt-list pointing the other way is a real discriminator, not an aesthetic one.

**What survives, and it is the highest contract yield in the lineup.** D5's four "contributions that stand regardless of which variant wins" are all correct, all transferable, and three of them are holes in the other variants (see §Shared blind spots #3 and #4). Naming edge semantics in the contract is the single most valuable line produced by this lineup.

---

## Original scenarios re-run

The originals ran against sketches. With variant detail, here is where each ranking moves.

### RT-modularity

The D-specific finding — *"any cross-regime metric is defined at the shallowest common denominator, so the promotion decision is always made on the least informative evidence"* — **no longer discriminates among the four.** D2/D4/D5 all repair it with computed depth plus comparison at the greatest common depth (F4); D1 bypasses it by refusing to let cross-regime evidence reach the gate at all (and pays for the bypass, above). The Attack 4 indictment is now a lineup-wide *solved* problem and should not be used to separate variants.

**What moves instead:**

- **Attack 4's fix list, item 3, is unimplemented in all four.** The fix reads *"`ItemKind` is an open registry declared by the recipe, and evidence is a **union**, not a node — restore SYNTHESIS's typed union"*: `text chunk | graph path | code snippet | fact-with-validity-interval | page image ref | SQL result set` [docs-verified]. All four carry `ScoredItem{..., kind, ...}` as a **field**; none specifies `ItemKind` as an open, recipe-declared registry, and none names the six kinds. This lands hardest on **D2**, whose T1 tier is *defined* as `ScoredItem[]` — so D2's highest-value measurement is under-specified for PathRAG paths (a sequence of edges with its own reliability score), MS-global scored points (no corpus ref at all), and ColPali page images [all code-verified, inherited]. D2's headline tier cannot hold four of six evidence kinds as written. See §Shared blind spots #2.
- **Attack 6 stress 3 (auto-merge loops internally, violating goal 10) separates the four.** D1 hosts it as a `fixpoint` node kind; D4 refuses the in-component loop and makes the executor own the iteration; D5 makes limits arrive in the spawn message. **D2 alone leaves the loop inside the component**: *"the machine cannot meter inside it, but it can kill it."* D2 scores itself 4/5 on goal 10; on RT-modularity's own reading that is a goal-10 miss, not a docked point. **D2's goal 10 should read 3.**
- Attack 1a (N tokenizers) — all four adopt central counting with `counted_by`. No separation. D4 additionally extends it across foreign parts by injecting its own LLM endpoint, which is the only variant-level improvement and is conditional (falsifier 4).

### RT-upgradability

The original ranked D first **conditional on D-1 and D-2**, with the explicit warning that *"D falls below C if D-1 and D-2 are not adopted"* [docs-verified, §7]. **All four adopt D-1/D-2 analogues** (D1 verbatim; D2 as debt-threshold selector exclusion + recorded renewal; D4 as `depth == opaque` exclusion + TTL; D5 verbatim). The condition is satisfied everywhere, so it no longer discriminates.

**What discriminates now: §1's named D defect — one-way promotion with no re-promotion ritual.**

| Variant | Re-promotion mechanism | Grade |
|---|---|---|
| D2 | Upstream deltas are more increments on the same gradient; `upstream_ref` **per realized node** | Structural |
| D4 | Decomposition is idempotent, so absorbing v2 uses the same mechanism as the first port | Structural |
| D5 | Sandbox engine and native set interchangeable at one mailbox; "sandbox@latest vs kernel@ours" is an ordinary two-arm wiring | Structural |
| D1 | Comparator population + a **standing scheduled rig job** on every upstream release | A ritual, correctly scheduled |

D1 turns the intention into a scheduled job, which is a real improvement over the drawn D, and it is still the only variant where absorbing an upstream improvement requires re-implementing it from scratch — and where, per its own S2, *"the answer-tier delta tells you that v2 is better and never why... D1 has no cheap screen for this."* **D1 drops to fourth on this lens.** [inference]

**Amendments checked against the four:**

- **SA-3 (migration component as the eighth primitive), marked "applies to all" — missing from all four.** All four have the reindex *planner* (which classifies and prices) and none has the *migrator* (which transforms `recipe@vN → vN+1`). The brief's §4 listed the planner among the four service boxes and never mentioned SA-3, so all four inherited the omission. This is the cleanest example in the pass of what independent drafting cannot catch. RT-upgradability calls it *"the amendment that converts every scenario in this document from 'a project' into 'a component someone writes on a Tuesday.'"* [docs-verified]
- **B-4 (blob sidecar provenance manifest)** — present in D1, D2, D5; **absent in D4**, whose anatomy lists only "Opaque blob — + addressable-subrange."
- **R7-c (retention tiers + scheduled reconstructability test)** — explicit in D1 and D4; absent in D2 and D5 (both discuss GC/retention without the reconstructability probe).
- **B-2 (decomposition ratio published per part)** — D2 (debt), D4 (decomposition ratio, explicitly the same number as depth), D5 (boundary-count falls out of the trace). **D1 has no analogue** and does not need one, since it has no partial states — correctly so.

### RT-selfimprove

The original ranked D first for one reason: *"improvement loop kernel-only, kernel population capped at 3–5 by promotion economics"* [docs-verified, §7]. F3 settles what happens to that. Re-ranked over variants:

**D4 ≈ D2 > D1 > D5.**

- **D4** states the replacement bound correctly and attaches isolation to the population that actually mutates (config and wiring changes to house parts — ranks 1 and 2 of the mutation ladder).
- **D2** has the same bound and disowns it, plus the only variant-level attack on §2's dominating falsifier (extending the retrieval-metric lever to opaque parts) — which the D2 attack above largely breaks. Its per-tier A/A calibration cost is real and honestly stated.
- **D1** preserves the original bound on paper and breaches it by exception, and its promotion trigger is not machine-operable.
- **D5** does not replace the bound at all and adds an independent variance source to a loop whose realistic MDE is already +20–25 pp against component mutations that move 1–5 pp [docs-verified, §2.1]. Its own falsifier 3 says this is *"close to disqualifying on its own"* and I agree with that self-assessment.

**And the finding that outranks all four:** RT-selfimprove falsifier 3 — *"The eval set stays at 30–50 questions — then no candidate matters, because none of them can tell a real improvement from noise. **This is the falsifier that dominates the architecture choice**"* [docs-verified]. No variant's advantage survives it. Three of four never mention it; D2 mentions it and its answer is the one attacked above. See §Shared blind spots #8.

---

## Self-softening check

Every drafter was told to report falsification rather than widen. Nobody hid a widening. Details, worst first:

**D1 — assigned "whole part re-implemented." Position held on promotion; softened on two adjacent axes, both declared.**
1. The chunk-tier feed is refused at the boundary and then re-opened one sentence later as *"a declared, optional upgrade for a sandbox part that accepts a specific chunker stamp."* That re-opening *is* D2/D4/D5's rule, presented as an exception to D1's stricter one.
2. Disadvantage 1 admits query-wiring-class parts **directly to the kernel**, bypassing the sandbox entirely for the cheapest and most numerous class of parts. That is not a softening of *promotion* — it is a change of *admission policy* that removes the sandbox from the majority path and quietly breaches D1's population bound (F3).
3. D1 retires amendment C-1 on a misreading (F2). C-1 is not in the settled set so this is in bounds, but it should have been flagged as a proposed amendment, not asserted as a corollary.

**D2 — assigned "adapter-first then decompose." Held.** The one named adjustment (containment's *owner* moves from the sandbox to the arm runner, depth unchanged) is declared and is compelled by the assigned position rather than by an attack. D2 also redefines the sandbox into a pre-admission staging area, which is a legitimate consequence of adapter-first and is stated (*"a smaller job than canonical D gives it"*). The one place D2 flinched is in its own scoring, not its design: it under-rates its structural bound (F3) and over-rates goal 10 (RT-modularity re-run).

**D4 — assigned "one executor only." Held absolutely, including through a conclusion adverse to the whole lineup.** The `opaque` node kind is arguably the second regime re-entering as a type; D4 says so and argues that a type is strictly better than a place. That is the position, not a retreat from it.

**D5 — assigned "actor / message-passing." Held, and it is the only variant that argues against parts of its own thesis in its own voice.** Two honest narrowings: the ingest lane is *"statically pinned actor singletons; NO dynamic spawn"* — a declared-graph kernel for half the machine wearing actor vocabulary — and the template-graph + `sends` + `may_spawn` + `supervision` object is closer to a declared graph with cardinality annotations than the Position paragraph implies. D5 anticipates and answers the second objection ("a type for the run, in the same sense a class is a type for its instances"); I accept the answer and note the gap is smaller than the framing.

**Nobody widened to survive an attack. D1 is the closest to drift and it declared every step.**

---

## Shared blind spots

All four inherited one brief. What all four missed, assumed identically, or got wrong in the same direction:

1. **SA-3, the migration component, is absent from all four.** RT-upgradability marks it "applies to all" and calls it the amendment that turns a project into a Tuesday's work. All four have the reindex *planner* and none has the *migrator*. Traced directly to BRIEF §4, which named the planner among the four service boxes and omitted SA-3. Its acceptance test is already specified (a rig run over pre/post artifacts; `run_substrate_parity.py` is the working precedent) and it is unclaimed in every variant. [docs-verified]

2. **`ItemKind` was never restored as an open, recipe-declared registry over a typed union.** All four kept `kind` as a scalar field on `ScoredItem` and none names the six evidence kinds. RT-modularity's Attack 4 fix item 3 is unimplemented lineup-wide, and it is the fix that keeps paths, LLM-authored scored points, page images, and SQL result sets expressible. Lands hardest on D2 (T1 is defined over `ScoredItem[]`) and on every stage-level diffing claim in the lineup. [docs-verified]

3. **Instance identity for a node inside a planner-emitted plan is undefined in D1, D2, and D4.** All three specify `config_hash` as a hash *over author-supplied input JSON* (RFC 8785). A planner-emitted node's config has no author — it was computed at runtime. **D5 alone solves it** (`H(template_instance_hash, JCS(spawn_config), parent_instance_hash, ordinal)`) and correctly generalizes: *"any variant that permits ephemeral subgraphs needs this shape; a contract that assumes the instance table is enumerable at load forecloses DQ-1.2 for everyone."* Since DQ-1.2 is a disqualifier, this is a conformance hole in three of four. [inference]

4. **Concurrency under fan-out is unnamed in D1, D2, and D4.** All three specify fan-out with runtime arity; none says whether branches run concurrently, and none says whether the A/A null must be calibrated under the same concurrency regime as the arms. D5 alone names scheduler variance and mis-attributes it to the actor model (F7). Given that the A/A null is *the single best defence* against noise promotion [docs-verified, RT-selfimprove §2.5.2], an uncontrolled variance source in the null is a lineup-wide instrument defect.

5. **The foreign-part adapter is a fixed cost in all four and is priced as variant-specific in all four** (F6 generalized). Process lifecycle, RPC, health, corpus-feed handoff, and evidence normalization must be written whether the part lives behind a jail (D1), an adapter node (D2), an opaque node kind (D4), or a confined actor (D5). Any cost comparison across variants that counts it once is wrong.

6. **The corpus-feed tier is a confound choice and no variant treats it as one.** All four debate document-vs-chunk feeding as a *correctness* question about embedder coupling. None asks what the comparison is controlling for. Chunk-tier holds chunking constant and handicaps engines tuned to other boundaries; document-tier lets each part chunk natively and makes the chunker part of what is measured. Both are defensible; the choice determines what an answer-tier number means, and it is not recorded on the scoreboard row in any variant. Minimum fix: `feed_tier` is a partition-key field, and any published cross-part comparison names it.

7. **Determinism is self-declared in every variant, at exactly the tier that licenses causal claims** (F10). D2's T3 requires "declared determinism"; D5 requires a declared scheduler setting; D4's `held_constant` is computed but cannot establish determinism. The "computed, never self-declared" rule that three variants converged on therefore has a hole at its deepest rung. Cheap fix proposed by nobody: re-run the node on identical input, compare, downgrade on mismatch.

8. **All four design around an instrument the red team already calls disqualifying, and none says so.** *"The eval set stays at 30–50 questions — then no candidate matters... This is the falsifier that dominates the architecture choice"* [docs-verified, RT-selfimprove §7]. Three variants never raise it; D2 raises it and offers an answer this document breaks. Every advantage claimed in every variant is downstream of an instrument that cannot resolve the effects the loop produces. A selection made on these four documents is a selection made under a dominating unresolved falsifier, and the honest statement of that belongs in the selection, not buried in one variant's Advantage 2.

9. **May the executor read the artifact plane mid-run? Three-way disagreement, in nobody's contract skeleton** (F8). D1 yes (validating an emitted plan), D2 no (bus is write-only during a run), D5 no (spawn-time frozen resolutions, its self-declared most important sentence), D4 silent. DQ-2 constrains *components* and is silent on the executor. This must be settled in the fitting contract regardless of which variant wins.

10. **The four rubric scorings are mutually incommensurable and a selection step will be tempted to compare them.** D1 uses Strong/Partial/Weak, D2 uses 1–5 summing to 39/50, D4 uses yes/partial, D5 uses Strong/Mixed/Partial. "39/50" against "five clear, five partial" is a comparison of nothing. Rubric scores should be re-derived by the selection step against one scale, or excluded from it.

---

## Ranking

Ordered, with the margin between each pair stated honestly.

**1. D4 One Machine**
**2. D2 Instrument Bus**

**Margin: near-tie. Say so rather than manufacture one.** These are the same architecture entered from opposite ends. Both bound registry growth by decomposed surface rather than by regime (F3). Both compute comparison depth and refuse to pool across labels (F4). Both make promotion a gradient with a computed debt/depth number, both attach isolation to the arm rather than to a location, and both concede the same residual hole (an under-decomposed part holding a shared-store write scope). Their disagreement is about *which computed field drives policy* — D4 derives containment from declared effects and gates writes on structural depth; D2 derives promotion pressure from evidence depth and gates claims on tier. That is a difference in where the pressure is applied, not in the mechanism.

D4 edges ahead on three points: it states the replacement bound correctly where D2 disowns its own (F3); its depth computation is structure-derived, which is the only formulation that reaches the stage/node tiers without a self-declaration (F10); and it takes the loop away from the component where D2 leaves it inside (RT-modularity Attack 6 stress 3). D2 edges ahead on two: the veto-only cross-tier asymmetry and `insufficient-depth` are the best contract items in the lineup and D4 has no equivalent, and D2's evidence protocol is buildable and testable before either regime exists, which is the settled sequencing made into a shape.

D4 carries one unpatched hole (the laundering path through a stage-depth node) that D2 carries in a different form and also does not patch. D2 carries two internal contradictions as written (the `space_id`-at-T0 pooling defect; cheap-admission versus T1-capability) that D4 does not.

**The tie-breaker is not architectural: what separates them is which unpatched item is cheaper to fix.** D4's is one taint rule. D2's is two independent corrections, one of which (cheap admission versus T1) is a conflict between its two headline advantages rather than an oversight.

**3. D1 Two Kingdoms**

**Margin to D2: one clear step, on one axis, in both directions.** D1 is a clear step *below* on machine-operability: its promotion trigger is a human typing a `part_ref`, its re-promotion path is a scheduled ritual where the other three have a structure, it pays C's full duplication bill for a property one boolean buys (F1), and it breaches its own population bound by admitted exception (F3). D1 is a clear step *above* on boundary honesty: it is the only variant with no path by which shallow cross-regime evidence reaches a machine decision, and its contract skeleton is the cleanest and most complete in the set.

If the project's goal were a system a person operates and audits, D1 would rank first. The project's goal is a self-improving machine, and D1 hands the machine's defining decision back to the operator.

**4. D5 Actor Kernel**

**Margin to D1: one clear step on operational risk, and an inversion on contract yield.** D5 is last because it moves two load-time refusals to run-time where they arrive as *scored low arms* rather than as rejections — directional Type II inflation on a loop with power ≈0.10 — because it does not replace D's structural bound at all (F3), and because it has no prior art to adopt against an explicit adopt-list pointing at a Haystack-shaped executor.

**But D5's contract yield is the highest in the lineup and the ranking should not be read as discarding it.** Four items — edge semantics must be named in the contract; identity must permit instances minted at spawn; budget must be a splittable capability; evidence depth is the set of boundaries a value crossed — are all correct, all transferable, and three of them are holes in the variants ranked above it (§Shared blind spots #3, #4). If selection's job is to harvest clauses for the fitting contract rather than to pick an implementation, D5 outperforms its rank.

**Two of the three ranking gaps are narrow.** 1↔2 is a tie. 3↔4 is a clear gap on risk and an inversion on yield. Only 2↔3 is a straightforward one-step gap.

---

## What would change this ranking

Concrete and observable, in descending order of decisiveness.

1. **The D4 laundering test.** Build a half-decomposed wiring where a `stage`-depth ingest node writes a shared artifact downstream of an `opaque` node. If depth-without-a-taint-rule permits the write, D4 needs the taint rule (one line, keeps rank 1). If adding the taint rule then makes every half-decomposed part unable to ingest, **D4's ratchet has no usable middle state, D2's gradient inherits the same defect, and D1's cliff is vindicated — D1 moves to first.** This is the single most decisive experiment in the set and neither D4 nor D2 nominated it.

2. **D2's falsifier 1, run correctly.** Attempt a `ChunkRef`-resolvable evidence emission from `codebase-memory-mcp` (self-contained storage, own compiled 768-d int8 vectors) [code-verified, inherited]. **Run it twice** — once with the part consuming machine chunks, once with the part chunking natively. If the *native-chunking* case can emit resolvable refs, D2's cheap-admission/T1 conflict dissolves and **D2 moves to first**. If only the machine-chunk case works, D2's headline is confirmed as costing the largest port cost in the system and D2 stays at 2.

3. **Per-tier A/A null widths, measured on our corpus.** If T1 nulls are not materially narrower than T0 nulls, the entire depth ladder is decoration for all four, axis 5 collapses completely, D2's headline advantage evaporates, and **D1's refusal-instead-of-labelling becomes the cheapest correct design.** Measurable from the first calibration run, before any architecture exists.

4. **A/A null width with fan-out branches concurrent versus sequential, for any variant.** This simultaneously decides D5's Disadvantage 2 and tells D1/D2/D4 whether they are carrying an unnamed variance source (§Shared blind spots #4). If concurrency materially widens the null for everyone, D5's largest self-assessed cost is lineup-wide and **D5 rises**.

5. **D1's falsifier 1, over ≥5 completed ports.** Does pre-port answer-tier evidence predict which kernel component change actually won its A/B? If yes, D1's refusal discarded a working work-ordering instrument and **D1 falls further**. If no, D1's central refusal is vindicated and **D1 rises above D2**. D1 is right that the data accrues from work done anyway; it is the cheapest test on this list.

6. **Decomposition increments actually completed in six months** (D2 falsifier 3 / D4 falsifier 3). If the top-traffic part's debt/depth is unchanged, the gradient variants have produced a graveyard *inside* the kernel — strictly worse than D1's, because those residents have store access — and **D1 wins by default**.

7. **Adapter cost for two differently-shaped engines** (D4 falsifier 2), measured against the broker C would need. If they are the same size, F6's generalization is confirmed quantitatively and every variant's cost accounting must drop it as a discriminator. Does not reorder; corrects the arithmetic.

8. **A settled answer to "may the executor read the artifact plane mid-run?"** If no, D1's planner-plan revalidation is illegal and D1's DQ-1.2 answer needs rebuilding; D4's silence becomes an unvalidated-plan hole it must close; **D5's SpawnRequestList becomes materially more valuable and D5 rises.** If yes, D5's cleanest-DQ-1.2 advantage shrinks to a 22 ms latency saving.

---

## Provisional / unattacked

Named explicitly, because a red team that does not say what it skipped is claiming coverage it does not have.

- **No `[code-verified]` claim was checked against source this session.** The 794 / 1,786 line counts, `_generate_collection_suffix()` returning `None`, strategy-`V` embedder coupling, the 43 abstract methods / 20 implemented, `storage_migrations.py`'s emptiness-sniffing, the ~1–1.4 ms `rename(2)` measurement, and the ~22 ms validator figure are all inherited with attribution from ANATOMY-REVIEW / spike 001 / spike 004. Several of my rulings (F1, D2's strongest-claim attack, F9) rest on them. **If any of those is wrong, the rulings resting on it are wrong.**
- **D5's falsifier 1 was not properly tested.** I probed address unforgeability against the selector, harnesses, and non-adjacent fan-in and found no counter-example. I did **not** walk the 45 gap-sweep component types or the 24-system survey looking for one that needs runtime mailbox lookup by name, which is the test D5 itself specifies. D5's entire validation argument still rests on an assumption I sampled rather than swept.
- **I did not re-run GAP-SWEEP §3.8's full DQ-1 list against each executor model.** Each variant's DQ-1 self-assessment was taken at face value except where F8 bit. Fan-out/join and non-adjacent fan-in in particular were not stress-tested against the specific shapes §3.8 enumerates.
- **The mermaid anatomies were spot-checked, not audited.** I verified the four service boxes, the harness wrapper with back-edge and self-edge, the budget enclosure over ingest, and `EMB -.binds.-> VEC` in each. I did not check all ten must-fix defects from ANATOMY-REVIEW against all four diagrams. The B-4 gap in D4 and the R7-c gaps in D2/D5 surfaced from prose, not from a systematic diagram audit; there may be more.
- **The S3 walk-throughs were not audited for service-ordering completeness.** All four look conformant to the settled sequence and I did not verify each against the six-service list step by step.
- **Rubric scorings were not adjudicated**, only flagged as incommensurable (§Shared blind spots #10). I did not re-score any variant against one scale. My two corrections (D2's goal 10 should be lower; D2 under-scores its own structural bound) are point findings from the scenario re-runs, not a re-scoring.
- **I did not attack the eval-bundle design itself**, only noted that all four inherit an instrument the red team calls dominating-and-disqualifying. Whether a bundle large enough to matter is affordable on this corpus is the question that outranks this entire lineup, and it is outside this document's mandate.
- **`as_of` / temporal threading was checked only superficially.** D1 and D4 thread it seam→selector→harness→node→store; D5 has it in the query object; **D2 has `as_of?` in its query object and graph sub-capability but never threads it to the adapter boundary** — D1's fail-closed rule ("a sandbox part that does not declare `temporal` is refused an `as_of`-bearing query") has no D2 analogue. I did not pursue this far enough to rule on it.

---
*Cross-variant red team, spike 003. Uncommitted. This document produces evidence for selection; it does not select.*
