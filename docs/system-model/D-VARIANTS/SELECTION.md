---
title: Selection — spike 003 D-variants
spike: 003
date: 2026-08-10
role: judgment step; consumes BRIEF (incl. §2 amendment), D1/D2/D4/D5, RED-TEAM, COMPLIANCE, CANDIDATES, RT-*, GAP-SWEEP, WIRING-SPEC-DRAFT, MANIFEST
status: SELECTED — feeds SPIKE-PLAN step 8 (fitting contract); AMENDED 2026-08-10 by spike 005 (Condition 1's justifying premise falsified; quarantined artifact scope added — see §Amendment at end)
---

# Selection — spike 003

## The verdict

**D4 One Machine is selected — and the selection simultaneously rules that D does not survive as a two-regime architecture.** The two rulings are the same act, because D4 *is* candidate B with the amendments the evidence forced: one executor, one trace schema, one identity discipline, per-arm process isolation, and an `opaque` node kind whose containment, comparison depth, selector exclusion, TTL, and artifact confinement are computed and machine-enforced per node rather than granted by a location. This is the outcome the spike's decision rule names in advance — "D's lead collapsed, B was right, reached with evidence" — and the concrete artifact that embodies it is D4's document, amended with the repairs and grafts below. The fitting contract that step 8 writes describes **one machine**; no sandbox regime appears in it. What D contributed is not discarded: every property the regime bought (blast-radius confinement, bounded registry growth, disposable trials, permanent black-box residency, upstream measurement) is re-provided per node, as contract, and each re-provision is named in this document with its mechanism. [inference, on the docs-verified evidence chain below]

## Why

The reasoning that decided it, in the order it actually carried weight:

1. **The lineup converged on the bound that made D lead, and the bound does not need the regime.** Spike 002's case for D was that registry growth and blast radius are both structurally bounded [docs-verified, RT-selfimprove §1.5, §7]. All four variants — three by design, D1 by admitted exception (its Disadvantage 1 admits query-wiring-class parts directly to the kernel) — replace that bound with *"you cannot mutate what you have not decomposed"*: an opaque node's only mutable surface is its config and position, so registry growth scales with decomposed surface, which is D's bound obtained without a regime [docs-verified, RED-TEAM F3]. The red team ruled a priced bound acceptable iff it is structural in exactly this form, and D4 is the variant that states it correctly (D2 states then disowns it; D1 breaches it by exception; D5 never replaces it). Once the bound is per-node, the regime boundary has no remaining work on the two axes that justified D. [inference]

2. **The sandbox's surviving jobs are policies, not a regime.** After F5 consumed isolation into the settled per-arm process requirement, RT-selfimprove leaves the sandbox exactly two jobs: cheap disqualification before the index bill (a 500-chunk sub-corpus trial at ~5% of tokens) and permanent residency for structurally unportable black boxes [docs-verified, RT-selfimprove §5]. My adjudication: neither needs a second executor, second trace schema, or second identity vocabulary. A sub-corpus trial is an opaque node run under a budget against a smaller corpus feed; a permanent resident is an opaque node that never decomposes, TTL-renewed with recorded reasons, excluded from the default selector, its storage instance-scoped and refcounted. Both are one registry entry plus policy fields. This — not the ranking — is the reason "no second execution regime" is correct. [inference]

3. **D4's central mechanism survived attack; its one hole costs one line.** Computed depth ("the kernel is a depth, not a place") was attacked and survived: it is statically computed from wiring plus registry, dynamically audited by `refs_in/refs_resolved` (contract clause 3), and strictly more expressive than the regime label — transparent-but-external and opaque-but-machine-stored parts are both nameable, and neither is nameable in D as drawn [docs-verified, RED-TEAM D4 attack section]. The unpatched hole is the laundering path (per-node vs per-wiring write gating); the repair is a taint rule adopted below, and I rule — with reasoning, not just hope — that it preserves the ratchet's middle state (see Conditions §1). [inference]

4. **D1's promotion path is not machine-operable, which is disqualifying for this project's subject.** Its promotion trigger is a human typing a `part_ref`; the machine "explicitly declines to support that decision with a quality claim" [docs-verified, D1 §Promotion; RED-TEAM D1 attack]. The one decision the two-kingdoms boundary exists to govern is the one decision the machine cannot make. D1's honesty wins (no path by which shallow evidence reaches a machine decision) are real and are harvested as gate refusals — but a self-improving machine whose defining decision requires an operator is the wrong selection, whatever its audit trail looks like. [inference]

5. **D2's thesis broke on its own ingest coupling; its clauses are the best in the lineup and are grafted wholesale.** T1-from-opacity requires the part to consume machine chunks verbatim — i.e., to have surrendered its chunker, the single largest code-verified port cost — so cheap admission and T1 cannot both hold for the same part [docs-verified, RED-TEAM D2 attack, on ANATOMY-REVIEW F6 [code-verified, inherited]]. The pooling key (amended per F2), the veto-only cross-tier rule, `insufficient-depth`, per-tier A/A nulls, and the claim-class→tier table all survive and enter the contract. [docs-verified]

6. **D5 mispriced its cost.** It booked the smaller static-guarantee set as latency (22 ms → 2 M tokens); the real denomination is *directional Type II bias* — spawn-time refusals and reachability-passing non-answering wirings arrive at the rig as scored-low challenger arms in a loop whose power for a genuine +5 pp effect is ≈0.10 [docs-verified, RED-TEAM D5 attack; RT-selfimprove §2.1]. Plus no structural bound (F3), plus a from-scratch build against an adopt-list pointing at a Haystack-shaped executor. Its four transferable clauses are adopted (below); the kernel style is not. [inference]

7. **Naming the collapse is part of the selection.** Selecting D4 while asserting "D survives" would launder the lineup's emergent answer through a label. The red team put it plainly: D4 is an argument that the answer to spike 003 is B-with-amendments, presented as a D variant [docs-verified, RED-TEAM Attack 2 on D4]. I ratify that reading and act on it rather than absorbing it.

Rubric-score comparisons across the four documents played no role in this decision: the four scales are mutually incommensurable (Strong/Partial vs 39/50 vs yes/partial), per RED-TEAM shared blind spot #10, and were excluded rather than re-derived.

## The D4/D2 near-tie

It did not need breaking so much as consolidating, and the consolidation has a definite base document. D4 and D2 are the same architecture entered from opposite ends — same structural bound, same computed-depth commitment, same arm-attached isolation, same residual hole (an under-decomposed part near a shared-store write scope) [docs-verified, RED-TEAM Ranking]. Three things make D4 the base rather than D2:

1. **D4's depth is structure-derived; D2's tiers ultimately rest on manifest self-reports at the edges.** D4's formulation (registry-resolved non-opaque leaves) is the only one that reaches stage-level depth without a self-declaration [docs-verified, RED-TEAM F10]. D2's `declared_stages` denominator is a self-report its own Rule 5 cannot protect [docs-verified, D2 Disadvantage 7].
2. **D4's unpatched item is one taint rule; D2's are two internal contradictions**, one of which (cheap admission vs T1) is a conflict between its two headline advantages, not an oversight [docs-verified, RED-TEAM Ranking tie-breaker]. Repair cost is the honest tie-breaker between near-identical designs.
3. **D4 takes the loop away from the component** (`fixpoint`, goal 10 held structurally); D2 alone leaves it inside ("the machine can kill but not meter") — a goal-10 miss on RT-modularity's own reading [docs-verified, RED-TEAM RT-modularity re-run].

D2 wins on gate engineering, and everything it wins on is portable without carrying its adapter-first thesis: the grafts in §Inherits transfer D2's five best mechanisms into D4's frame. The result is one architecture completed from both ends, not a compromise between two.

## Did D's lead collapse?

**Yes. Ruled explicitly, per the decision rule.** The collapse test (D4) won, its own §"Is the second regime needed?" answers *no as an execution regime*, and my independent adjudication (§Why 1–2) confirms that every load-bearing property of the regime is re-providable per node. Candidate B is therefore re-opened — and re-opening it terminates immediately, because B *as originally drafted* is not what the evidence supports either:

- B has no isolation domain; "mutated code runs in-process beside the champion" is B's named hole [docs-verified, RT-selfimprove §7: "B is D minus the jail"]. The settled per-arm process requirement supplies the jail; B-as-drafted does not contain it.
- B's named aging failure — "opaque nodes tempt teams to stuff whole modalities into one node, quietly becoming Candidate C" [docs-verified, CANDIDATES §B] — is exactly what D4's machinery repairs: computed depth, published decomposition ratio, default-selector exclusion at `opaque`, TTL with recorded renewals, and the shared-artifact write gate. B with those amendments *is* D4.
- B has no admission story for foreign engines at all; D4's opaque node kind with derived containment is that story.

So the precise ruling is: **D's lead collapsed to B-with-amendments, and D4's document is the drafted form of B-with-amendments.** What was wrong in spike 002 was not the direction — the mechanisms D contributed are all retained — but the claim that they require a second *regime* rather than a computed label, four effect declarations, and two policies. The fitting contract carries no `regime` field. It carries `depth`, `effects[]`, `execution_mode`, and the opaque-node admission conditions. [inference]

One honesty note D1 earns here: D1 is the only variant with no path by which bad cross-population evidence reaches a machine decision. That property is preserved in the selected design not by refusing comparison but by the gate's refusal list — the machine may compare at a labeled depth, and may never *gate* on evidence shallower than the claim class requires, never on runtime-downgraded depth, and never across pooling-key mismatches. Refusal-with-a-reason survives; the two kingdoms do not.

## What the winner inherits from the losers

Grafted into D4's frame, named per source. These are selection decisions, not suggestions.

**From D2 (the gate and evidence engineering):**
- **The evidence-tier ladder T0–T3 on the item**, machine-stamped from what actually arrived, never self-declared; with the **claim-class → minimum-tier table** and `insufficient-depth` as a verdict distinct from `inconclusive` (it names the missing instrument) [docs-verified, D2 §Comparison depth].
- **The pooling key**, amended per F2: `(eval_bundle@v, corpus@v, judge_instance, tier, counted_by, feed_tier)` with `space_id` **included at T1 and deeper, excluded at T0** — at answer tier the embedder is an attribute of the thing under test and the instance hash already pins it [docs-verified, RED-TEAM F2 corrected restatement of C-1].
- **Rule 4 — cross-tier evidence may veto, never support**; hard gates are evaluated wherever observable and are always vetoes [docs-verified, RED-TEAM F4: "every variant should adopt Rule 4 regardless of who wins"].
- **Per-tier A/A nulls and floors** — floor = the A/A 95th percentile per `(bundle@v, tier, metric)`, never a policy constant.
- **`upstream_ref` per realized node** in the decomposition record, so upstream drift has an owner per node, not per part; **`storage: machine | self-contained`** as an explicit opaque-node declaration.

**From D1 (the refusal discipline and the operational honesty):**
- **The gate refusal list** (S3 step 8): arms with differing resolved artifact ids; differing `(eval@v, judge@v, corpus@v)`; `refs_resolved < refs_in`; mixed `counted_by` without central recount; stale A/A null for the artifact set; claims gated on evidence shallower than the claim class — as contract, not policy.
- **Two target families in one eval bundle**: gold-passage targets (measurable wherever T1 exists) and answer-level targets (universal) — a bundle designed only for stage scoring cannot evaluate an opaque part at all.
- **The standing scheduled upstream-comparison rig job** — `upstream@latest` vs `ours`, same corpus, same bundle, run on every upstream release rather than remembered.
- **`as_of` fail-closed at the node boundary**: a part that does not declare `temporal` is refused an `as_of`-bearing query, never silently answers as-of-now.
- **Admission satisfiability check**: the confinement policy materialized for a node must be at least as strict as its manifest; undeclared is denied.
- **The explicit-invocation counter** on selector-excluded nodes — kept as *data* (demand legibility), never as a promotion trigger; the red team's finding that it measures operator curiosity stands [docs-verified, RED-TEAM D1 attack].
- The **permanent-resident class is correct behavior, not failure** — carried into the opaque-node policy vocabulary.

**From D5 (the contract yield the red team called highest in the lineup):**
- **Edge semantics are a named contract property**: this contract's edges mean *exactly-once dataflow per run*; fan-out branch concurrency is a declared executor property, and the A/A null must be calibrated under the same concurrency/determinism setting as the arms it judges [docs-verified, RED-TEAM F7 + shared blind spot #4].
- **Runtime-minted instance identity**: `instance_hash = H(component_instance_hash, JCS(runtime_config), parent_instance_hash, ordinal)` for nodes inside planner-emitted plans — closes the conformance hole F8/blind-spot-#3 found in D1/D2/D4, whose `config_hash` assumed an author [docs-verified].
- **Budget is a splittable capability token, not a global counter** — multiplicative fan-out accounting becomes structural (a branch cannot spend what it was not handed) [docs-verified, GAP-SWEEP §3.7.2].
- **Cross-process trace obligations**: every subprocess/confined-node invocation records the placement of both endpoints and, on failure, the failure cause (deadline vs kill vs capability denial) — D5's location-transparency mitigation, which D4's subprocess nodes need just as much.

**From the red team itself (attributable to no variant):**
- **Determinism is verified, never declared**: a node claiming determinism is re-run on identical input; mismatch downgrades it out of the intervention tier (T3) [docs-verified, RED-TEAM F10 fix].
- **`feed_tier` is a confound choice**: recorded as a scoreboard partition field; any published cross-part comparison names it [docs-verified, shared blind spot #6].

## Conditions on the selection

This selection holds only if all of the following are adopted. Each is a named repair with a mechanism; none is a design change to D4's frame.

1. **The taint rule** (repairs RED-TEAM's "single most important unpatched hole"): *a node's effective depth is the minimum over its transitive `deps`; a node may write into a shared artifact namespace only if its effective depth is `stage`.* My ruling on the feared consequence — that taint destroys the ratchet's middle state — is that it does not, for a structural reason: in every surveyed decomposition the ingest lane sits upstream of (or parallel to) the query-side opaque core, so an ingest-adapter's transitive deps are clean and its shared writes remain legal; what taint blocks is opaque-*derived* data entering the shared plane (e.g., an extractor consuming opaque-core output), which is precisely the shared-artifact-corruption blast radius that must be blocked [inference; RT-selfimprove §3 row 4 [docs-verified]]. A half-decomposed part therefore keeps ingesting, serving, and being A/B'd; it cannot launder. The laundering test remains Falsifier 1 because this ruling is an argument, not a measurement.
2. **DQ-2 wording repair** (COMPLIANCE, D4 ASSERTED): replace "artifact plane is read-only to components at runtime" with the D1/D2/D5 form — artifact-plane values are resolved before the run and passed in; components cannot query the registry, ledger, scoreboard, or artifact registry during a run. A control channel is a read.
3. **Planner-plan validation declared** (COMPLIANCE, D4 DQ-5 UNCLEAR / systematic issue 2): an emitted plan is JSON over the declared node-kind alphabet, validated **before execution** by the same static validator against a restricted allowlist plus the caps the planner's own manifest declares (D1's mechanism), recorded verbatim as trace data, never registered, aliased, or ledgered. Plan-node identity per the D5 mint rule above.
4. **The executor/plane access rule settled** (shared blind spot #9): registry and artifact-plane resolutions are frozen at load; the execution plane may invoke the validator on an emitted plan *against that frozen snapshot*; it may never read mutable decision state (scoreboard, ledger, active pointer) mid-run — D2's adaptive-arm-allocation temptation stays forbidden. This grants D1's plan validation without merging the planes.
5. **RFC 6902 for subtractive deltas** (BRIEF §2 amendment, binding): merge-patch for additive/overriding deltas; RFC 6902 `remove` (or an explicitly fail-closed equivalent) for any subtractive operation. All four variants restated the unsatisfiable form; the contract takes the amended one.
6. **The eval instrument precedes every claim this architecture makes** (shared blind spot #8, stated here rather than buried): at 30–50 questions no variant's advantage exists — power for +5 pp is ≈0.10 and a naive adopt-if-higher rule promotes noise ~5:1 [docs-verified, RT-selfimprove §2]. The settled sequencing (eval bundle + gate → isolation → architecture) stands, with the bundle carrying both target families, continuous scoring where possible, T1 retrieval metrics for retrieval-side mutations, and a size honestly derived from the target MDE. **Benchmarks never settle decisions; only local measurement on our own corpus does.**
7. **Depth computation and `execution_mode` derivation are implementable in the validator** — D4's own largest cost; if these two computations cannot be implemented, D4 is not implementable and Falsifier 2 fires.
8. **The injected-LLM-endpoint mechanism is built**; an engine that cannot take it is admitted `unbudgetable` and the rig refuses token comparisons including it — an explicit refusal, never a wrong number.
9. **B-4 sidecar manifests** on blob artifacts (absent from D4's anatomy [docs-verified, RED-TEAM RT-upgradability re-run]); **R7-c retention tiers + scheduled reconstructability probe** retained as D4 drew them.
10. **Per-arm process isolation unconditional** (settled; D4's clarification stands: in-process describes node hosting inside an arm; the arm is always its own confined process).

## Lineup-wide adoptions

Adopted regardless of winner; all traced to gaps no variant caught alone.

1. **SA-3 — the migration component** as the eighth primitive part type: a versioned artifact transforming stored artifacts `recipe@vN → recipe@vN+1`, declaring the pairs it bridges, lineage-tracked, with the acceptance test already specified — a rig parity run over pre/post artifacts (`run_substrate_parity.py` precedent). All four variants had the reindex *planner* and none had the *migrator*; traced to BRIEF §4's omission [docs-verified, RT-upgradability §5; RED-TEAM shared blind spot #1]. Companion policy: `unknown` provenance is readable, never declared-compatible.
2. **`ItemKind` restored as an open, recipe-declared registry over a typed union** — evidence is a union, not a node: `text_chunk | graph_path | code_snippet | fact_with_validity_interval | page_image_ref | sql_result_set`, plus `derived_finding` carrying `derived_from: [Ref]` [docs-verified, RT-modularity Attack 4 fix 3 + Attack 6 stress 4]. All four kept `kind` as a scalar field; the stage-diffing and T1 claims of every variant depend on this restoration.
3. **RFC 7386 + RFC 6902 split** for arm deltas (Condition 5 — listed here because it applies to every wiring the machine will ever author).
4. **Per-arm process isolation** with deny-by-default net/FS/store-write, wall-clock watchdog, capability-scoped store tokens over CoW overlays, cache keys including the instance hash (settled set, restated as adopted).
5. **The depth-tier gate policy** (F4 settlement): compute the greatest common depth across arms; run exactly one paired statistic there; deeper-tier evidence may veto, never support; return `insufficient-depth` naming the missing instrument when the claim class outruns the tier; never gate on evidence whose depth was downgraded by the runtime audit; hard gates evaluated wherever observable, always as vetoes.
6. **Concurrency is named**: whether fan-out branches execute concurrently is a declared executor property; the A/A null is calibrated under the arms' setting (shared blind spot #4).
7. **Determinism-by-re-run** for T3 admission (shared blind spot #7).
8. **`feed_tier` on every scoreboard row** (shared blind spot #6).
9. **Node ids are positions, never instance identities** — explicit contract text, with the measured fan-out-dedup failure behind it (COMPLIANCE systematic issue 4).
10. **Canonicalization rules restated in the contract**: RFC 8785, no integers outside int64, `1 ≡ 1.0` (absent from D2/D5; measured failures behind both).
11. **The foreign-part adapter is priced as a fixed cost**, not a variant discriminator — process lifecycle, RPC, health, corpus-feed handoff, evidence normalization exist in any design that hosts a foreign engine (RED-TEAM F6).

## The shallowest-denominator ruling

**Spike 002's condition — "cross-regime comparison honestly labeled shallowest-denominator" — is REJECTED, and this is an explicit amendment to a spike-002 condition, not merely a variant pick.** The condition was never in the settled set (it appears in `architecture-selection.md:20` and was not carried into BRIEF §2), and three of four variants independently replaced it [docs-verified, COMPLIANCE systematic issue 3]. The replacement is ratified: comparison depth is a computed property of what was actually observed — per node structurally, per evidence item as stamped — and cross-population comparison is defined at the **greatest common depth of the two arms**, which is deeper than the answer tier whenever both arms share deeper boundaries. What survives of the original condition is its honesty half, which was already pre-committed in the settled wiring spec (`WIRING-SPEC-DRAFT.md:132`: every arm's evidence records the depth tier so quality levels are never silently mixed): every row is labeled, every join across labels is refused or explicitly projected, and the gate's claim-class table decides what a labeled mix may support. The *resignation* half — "the promotion decision always runs on the least informative evidence" — is repaired rather than accepted, and D1's compliance-by-deletion, while honest, deletes a working instrument along with the broken one. [inference]

## Falsifiers

Concrete and observable, in decreasing order of decisiveness, each with its cheapest experiment:

1. **The laundering test fails both ways.** Build the half-decomposed wiring `{ingest-adapter(stage), opaque-query-core, assembler(stage)}` plus an index-side variant where the opaque core feeds an extractor. The taint rule must (a) permit the ingest-adapter's shared writes and (b) refuse the opaque-fed extractor's. If (a) fails — taint blocks every middle state — D4's ratchet has no usable middle, D1's cliff is vindicated, and the two-regime design re-opens. If (b) fails, the blast-radius mechanism is fiction. *Experiment:* a paper wiring walk plus one validator prototype; no corpus needed. [RED-TEAM's nominated decisive test, adopted]
2. **Depth cannot be computed statically.** Over three real parts (decomposed `lightrag-local`, opaque `codebase-memory-mcp`, half-decomposed LightRAG), the validator cannot derive `depth` from wiring + registry without a self-declaration. Then D4 has no brake and D's regime was doing structural work. *Experiment:* write the depth computation against the three wirings' specs; days, no execution.
3. **The eval bundle cannot be made big enough to matter on our corpus.** If the affordable bundle stays at 30–50 questions with binary answer-judging only, no promotion claim in this architecture is meaningful and the improvement loop is a random walk with a scoreboard. *Experiment:* cost out a bundle with gold-passage T1 targets + continuous scores at the n the target MDE requires (RT-selfimprove §2.6 levers) before any build step. This falsifier outranks the selection itself.
4. **Opaque parts cannot emit machine-resolvable refs, run correctly both ways.** D2 falsifier 1, run twice on `codebase-memory-mcp`: once consuming machine chunks, once chunking natively. If even the native case can map to `ChunkRef`, T1 coverage for black boxes is real and the depth ladder pays immediately; if only the machine-chunk case works, T1 costs the chunker surrender and the ladder's value concentrates on house parts. Either result calibrates the contract; total failure plus Falsifier 5 firing would revive D1's refusal design.
5. **Per-tier A/A nulls are not materially narrower at T1 than T0.** Then the ladder buys no statistical power and is decoration; D1's refusal-instead-of-labeling becomes the cheapest correct design. *Experiment:* first A/A calibration run, measurable before any architecture exists.
6. **The foreign-node adapter is broker-sized per engine.** Implement it for two differently-shaped engines (`codebase-memory-mcp`: no LLM, own storage; a LightRAG server: LLM-heavy, injectable endpoint). If each needs C's broker rewritten, the one-machine saving is arithmetic error — F6 says the cost is fixed lineup-wide, so this corrects pricing more than ranking, but a per-engine broker would also revive the case for a genuinely separate hosting tier.
7. **A parity decomposition cannot be brought inside the A/A band.** Decompose LightRAG's query side (~794 lines, plain-data boundaries [code-verified, inherited]) against the opaque original; if parity cannot be reached, promotion is a rewrite, not a refactor, and deserves D1's ceremony. *Experiment:* the first real decomposition increment, which the build performs anyway.
8. **Engines refuse the injected endpoint in the common case.** Token comparability collapses to the shallowest-denominator problem the selection exists to fix. *Experiment:* survey the endpoint-injection surface of the five sandbox-candidate engines already named in the lineup; a documentation pass.

## Contract skeleton implied

The boundaries this selection freezes into the fitting contract. Step 8 writes the spec from this list; where this list and any variant document disagree, this list governs.

**1. Wiring format and identity**
- Wirings are JSON with no evaluation semantics; `nodes` (id → instance; **ids are positions, never instance identities**), `deps` (partial order; cycles legal, reported as `{cycle:[...]}` data), `recipe` (SA-2 stamp sources), `harnesses` (ordered array), `provides`.
- **Edge semantics named**: an edge is exactly-once dataflow per run; fan-out branch concurrency is a declared executor property.
- `config_hash` = SHA-256 over author-supplied JSON, RFC 8785, no ints outside int64, `1 ≡ 1.0`, environment hash included. Instance = `(name@version, config_hash, resolved_dependency_ids)`; for an opaque node the environment hash covers the **whole resolved runtime closure**. Runtime-minted instances (plan nodes): `H(component_instance_hash, JCS(runtime_config), parent_instance_hash, ordinal)`.
- Spec pins contract-version ranges; a per-run lock records resolved behavior versions, artifact ids, and resolved model per role (R7-b). Artifacts content-addressed by NAR-style hash.
- Arm = base + RFC 7386 merge-patch (additive/override; differing kind tag replaces the whole `kind` subtree) + RFC 6902 for subtraction. Base independently re-validated with no arms applied.

**2. Node kinds and effects**
- `NodeKind` tagged sum (single-key object, per-kind schema, portable vocabulary): the ~10 primitive part types + `fanout`, `join`, `fixpoint`, `subgraph`, `opaque`.
- `effects[] ⊆ {reads_kv, reads_vector, reads_graph, reads_lexical, writes_artifact, calls_llm, calls_rerank, net, fs, self_storage}` + `iterative`, `space_id`, `presumes_graph`, `accepts/emits kinds`, `accepts/emits score semantics`, `order_stable`, `hierarchy_aware`, `checkpoint?`. Undeclared is denied.
- Iterative components are hosted as `fixpoint` nodes; the executor owns every loop and its halt.
- `join` sockets: `List[List[X]] → List[X]` and `List[Draft] → Draft`. `fanout` arity static or from an upstream node's output socket; budget accounting multiplicative.

**3. Depth and containment**
- `depth ∈ {opaque, evidence, stage}` per node, **computed by the validator, never declared**; **effective depth = min over transitive `deps` (the taint rule)**; wiring depth = min over the compared path; stamped on every run record and board row.
- `execution_mode ∈ {in-process, subprocess, confined-unit, long-lived-service}` **derived from `effects`, never requested**; the arm is always its own confined process; pure non-iterative nodes only may be in-process.
- **The blast-radius rule**: a node may write into a shared artifact namespace only if its *effective* depth is `stage`. `self_storage` is always legal, instance-scoped, refcounted to the instance, GC'd on unpin.
- Cross-process invocations record placement of both endpoints and failure cause.

**4. Evidence and measurement**
- `ScoredItem{ref, kind, score, provenance, payload}`; `Score{value, semantics, space_id}`; **`ItemKind` is an open recipe-declared registry over the typed union** (§Lineup-wide 2). `ChunkRef = (corpus_id, recipe@version, ordinal, content_hash)`; deref raises; `refs_in/refs_resolved` per run; positional indices only as part-local projections with auditable bijections; `derived_from` on authored evidence.
- Evidence-item tier `∈ {T0 answer, T1 evidence, T2 stage, T3 node}`, machine-stamped from what arrived; T2 requires stage-depth producing boundaries with instance hashes; T3 requires an actually-performed intervention + `held_constant` computed from recipe hashes + determinism verified by re-run.
- **Pooling key**: `(eval_bundle@v, corpus@v, judge_instance, tier, counted_by, feed_tier)`; `space_id` joins the key at T1+; scheduler/concurrency setting is a gate-admission condition and keys the A/A null.
- `counted_by` on every token number; central recount for cross-part comparison; `unbudgetable` nodes excluded from token comparisons by refusal.
- `EmbeddingSpace` id hashed from `(model_id, revision, dim, metric, normalization, query_prefix, doc_prefix, pooling, namespace_text_convention)`; namespaces immutable in space; `reads_space`/`writes_space` typechecked at load; embedder identity mandatory — the machine refuses to write vectors it cannot attribute.
- `ContextPackage` blocks with `order_policy`; machine-owned renderer; `requires_block_kinds`; assemblers return `List[ContextPackage]`.

**5. The gate**
- One implementation, verb ladder `check | preview | run | promote-next | promote-now`.
- Verdict vocabulary: `promote | reject | inconclusive | insufficient-depth | below-floor | unconfirmed | regression-veto | straddle`, each carrying the evidence pointer and tier-of-decision.
- Policy: greatest common depth; one paired statistic there (exact McNemar binary / paired bootstrap continuous); per-`(bundle@v, tier, metric)` A/A nulls, floor = A/A p95; confirmation on disjoint subsets; epoch FDR; hard gates as vetoes wherever observable; cross-tier evidence vetoes, never supports.
- Refusals (contract): mixed pooling keys; `refs_resolved < refs_in`; runtime-downgraded depth; stale A/A null for the artifact set; differing resolved artifact ids across arms; `held_constant` diff exceeding the declared mutation; mixed `counted_by` without recount; mismatched determinism/concurrency setting; claims gated below their minimum tier.
- **A decomposition is gated on parity, not gain**: its difference must fall inside the A/A band or name its declared deviations; an improving port is as suspicious as a regressing one.

**6. Promotion, decomposition, migration**
- Mutation promotion: atomic alias repoint + generation record (~1 ms, `rename(2)`, multi-artifact); ledger append is the decision; the active pointer is a projection; ledger wins on disagreement; running an arm never appends.
- Part promotion = **node → subgraph in place**; node id unchanged; depth recomputed; idempotent, so upstream absorption reuses the mechanism. Losers tombstoned (~200 bytes).
- **SA-3 migration component**: eighth primitive; versioned; declares bridged recipe pairs; acceptance = rig parity over pre/post artifacts; `unknown` provenance readable-never-compatible.
- Reindex planner classifies `{reuse | re-embed | re-extract | rebuild}` + cost, walking SA-2 stamps; `consumes_embedder` chunkers make their KV recipe-bound and escalate re-embed → rebuild.

**7. Registries and retention**
- Component registry (bytes, never deleted): `upstream_ref (repo, tag/commit, file/symbol)` per entry **and per realized node**; decomposition record with computed ratio, published beside every board result.
- Artifact registry (gigabytes, deletion required): namespace → sub-recipe stamps + corpus + `space_id` + producing instance; **blob artifacts carry machine-owned sidecar provenance manifests (B-4)**; retention tiers `runnable | readable | tombstoned` + scheduled reconstructability probe (R7-c); GC keyed on recipe-version reachability, counting runtime-minted instances.
- Ledger records carry: mutation id, class, parent, arm instance hashes, effect size, verdict, evidence pointer, proposer id, **depth label, tier-of-decision, decomposition ratio**, opaque-node TTL renewals with reasons, parity records for decompositions. Proposer hit-rate per class derivable by query.

**8. Opaque-node admission conditions**
- Manifest validated; whole-closure environment hash; denied network namespace with the machine as injected LLM provider (or `unbudgetable`); wall-clock ceiling; `storage: machine | self-contained` declared (machine-storage writes still subject to the blast-radius rule); corpus feed at a declared `feed_tier` (chunk feed refused for embedder-coupled recipes); excluded from the default selector at `opaque` effective depth; TTL (~90 days) with recorded-reason renewal; explicit `part_ref` invocations counted as data; no SA-1-shareable artifacts (resolved inputs not enumerable — enforced, not discovered); `as_of` refused without a declared `temporal` capability.

**9. Budget**
- A splittable capability token: spend (steps/tokens/time) and capacity (consumer context window) separated; multiplicative under fan-out by construction; standing-corpus budget with eviction owned by the store; encloses ingest and query; partial and budget-halted runs first-class — traced, scored, tier-labeled, never discarded; degradation paths declarable in manifests.

**10. Versioned instruments**
- Eval bundle (questions + gold + judge instance + judge prompt hash + corpus snapshot hash + determinism/concurrency setting; dev/holdout/sealed; **two target families**), judge, selector policy, mutation proposer, **and the executor** — each named in every trace it touched.

**11. Plane rules**
- Artifact-plane values are resolved at load and passed in; components cannot query registry, ledger, scoreboard, or artifact registry during a run. The execution plane may invoke the validator on a planner-emitted plan against the load-frozen snapshot; it may never read mutable decision state mid-run. Emitted plans: JSON over the declared alphabet, validated pre-execution against a restricted allowlist + planner-manifest caps, recorded verbatim as trace data, never registered/aliased/ledgered.

**12. Declared non-goals**
- `model-weight-access` (DSI, ROME/MEMIT, RAFT, RL retrieval): named in the contract. No live RAG-framework dependency; Haystack-*shaped* executor, vendored pins only. Nix substrate-only; store paths name nothing; no dependency on `ca-derivations` / `dynamic-derivations` / `impure-derivations`.

## Open questions carried forward

1. **The laundering test has not been run.** Condition 1's taint-rule ruling is an argument; Falsifier 1 is the measurement. Until it passes, the selection is correct-by-reasoning, not correct-by-evidence.
2. **T1 coverage for black boxes is unmeasured** — D2's falsifier 1 run both ways (Falsifier 4) decides how much of the depth ladder applies beyond house parts.
3. **Whether the tier ladder buys statistical power on our corpus** (per-tier A/A widths, Falsifier 5) — measurable before any build step and cheap.
4. **Eval-bundle affordability at the required n** — the question that outranks this document (Falsifier 3). This spike inherited it and could not settle it; step 10's rig design must.
5. **Adapter size for two engine shapes** (Falsifier 6) — corrects the cost arithmetic; C's broker knowledge should be mined when it is built.
6. **The socket type system and capability vocabulary** — deliberately not decided here; step 8's own work, now with `ItemKind`'s union and the `effects[]` vocabulary as fixed points.
7. **The `evidence` structural depth value** — once `ItemKind` and machine-refs land, whether `evidence` remains a distinct structural depth or collapses into "opaque node that passes clause 3 at its boundary" is a step-8 simplification question.
8. **Validator implementation choice** (bespoke / `evalModules`-hardened / CUE) — build phase; the contract stays implementable by all three; the two provisional items in WIRING-SPEC-DRAFT §9 (violation-channel completeness under schema evolution) still deserve their refutation pass.
9. **D5's address-unforgeability sweep was never run** — moot for this selection; recorded in case actor-style scheduling returns inside the executor.
10. **Concurrency's effect on the A/A null width** (Falsifier-adjacent, shared blind spot #4) — one calibration experiment, informs whether eval runs pin a sequential setting.

---

## AMENDMENT — spike 005, 2026-08-10 (Falsifier 1 was run)

Falsifier 1, nominated above as the decisive test, was executed as spike 005 (`.planning/spikes/005-laundering-test/`, runnable `taint.py`, 12 cases). **The selection stands. Condition 1's justifying premise does not.**

**What was wrong.** Condition 1 argued that taint preserves the ratchet's middle state because *"in every surveyed decomposition the ingest lane sits upstream of (or parallel to) the query-side opaque core, so an ingest-adapter's transitive deps are clean."* The decomposition runs the other way. Spike 001 [code-verified]: *"Query path is already a named 4-stage component pipeline; index side is entangled (~1,786 lines, ontology-welded)."* The query side decomposes **first** because it is already component-shaped; ingest stays opaque **longest** because it is the hard side. The premise is inverted against evidence that predates this document.

**What holds.** The taint rule itself is sound and was not the problem — confirmed on opaque→stage chains, non-adjacent fan-in through a sibling, `evidence`-tier propagation, and non-over-blocking of parallel lanes. Decomposition credit also survives the artifact boundary: a decomposed query run reading an opaque-produced index still computes `stage` throughout. The blocker is the **base blast-radius rule applied to the opaque node itself** — an opaque ingest cannot write the shared index, and producing the shared index is what ingest is.

**The repair, verified.** Artifact scopes become **three**, not two:

| Scope | Who may write | Shareable |
|---|---|---|
| `shared` | effective depth `stage` only | yes, SA-1-addressed |
| `quarantined` | any depth, incl. `opaque` | **never** — instance-scoped, single-provenance, readable only by explicit pin, GC'd with the instance |
| `self_storage` | any depth | no, private |

The standing disqualifier holds: opaque-derived data still never enters the shared plane. Cost, stated rather than hidden: **no artifact sharing in the middle state** — two modalities over an opaque index each re-index, which is candidate C's N× token cost, confined to the middle state and paid only until decomposition. Decomposition becomes the way to *earn* artifact sharing, which prices the ratchet's incentive in tokens instead of asserting it as discipline.

**Effect on the contract skeleton.** §3 gains the third scope and the rule "an opaque node may write `quarantined`, never `shared`." §8 (opaque-node admission) restates the same. §Conditions 1 is amended: it is the quarantined scope, not clean transitive deps, that makes the middle state legal. Open question 1 ("the laundering test has not been run") is closed.

**D1's cliff is not vindicated** — the ratchet has a usable middle once the scope exists. Falsifiers 2–8 remain unrun, and Falsifier 3 still outranks this document.

---
*Selection, spike 003. Uncommitted. Every non-trivial claim tagged; `[code-verified, inherited]` marks line counts and source facts carried from ANATOMY-REVIEW / spike 001 / spike 004 with attribution — nothing was re-verified against source in this pass, per RED-TEAM's provenance note.*
