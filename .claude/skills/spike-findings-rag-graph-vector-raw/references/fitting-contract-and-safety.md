# Fitting Contract & Safety (inputs to the contract spec)

## Requirements

- Universal core: `ingest(source)` + at least one of `retrieve | answer`; everything else declared capabilities, machine-enforced
- Capability manifests are enforced preconditions (deny-by-default), never documentation
- Budget is a first-class machine object; traces name component versions

## The five load-bearing contract clauses (RT-modularity)

1. **Declarations are machine-enforced preconditions** — wiring validator runs before execution, fails closed
2. **Identity closes over the closure**: `ComponentInstance = (name@version, frozen_config_hash, resolved_dependency_ids)`; traces/lineage/A-B record the instance hash
3. **Machine-minted refs with provenance**: `ChunkRef = (corpus_id, recipe@version, ordinal, content_hash)`; deref raises loudly; runs record refs_in/refs_resolved
4. **Interpretation travels with the value**: ScoredItem carries `kind`; Score = {value, semantics, space_id}; vector namespaces stamped with EmbeddingSpace id; graph edges declare weight semantics; whole-graph algorithms declare required semantics
5. **Structured prompt boundary**: assemblers emit typed ContextPackage blocks; machine-owned renderer; token counting is a machine service using the consuming model's tokenizer, stamped `counted_by`

## Added by spike 003 — apply regardless of anything else

These were adopted lineup-wide during the architecture selection. The first two were **absent from all four variant documents** because they were omitted from the shared drafting brief — independent drafting cannot catch what every drafter was handed identically.

- **SA-3 — the migration component, the eighth primitive part type.** A versioned artifact that transforms stored artifacts `recipe@vN → recipe@vN+1`, declares the pairs it bridges, carries lineage like any component, and is testable. Acceptance test = a rig parity run over pre/post artifacts (`run_substrate_parity.py` is the working precedent). RT-upgradability marks it "applies to all" and calls it the amendment that turns every upgrade scenario "from a project into a component someone writes on a Tuesday." Every design has the reindex *planner* (classifies and prices) and forgets the *migrator* (transforms). Companion policy: `unknown` provenance is readable, never declared-compatible.
- **`ItemKind` is an open, recipe-declared registry over a typed union** — evidence is a **union, not a node**: `text_chunk | graph_path | code_snippet | fact_with_validity_interval | page_image_ref | sql_result_set`, plus `derived_finding` carrying `derived_from: [Ref]`. Keeping `kind` as a scalar field on `ScoredItem` under-specifies paths, LLM-authored scored points, page images, and SQL result sets — and every stage-diffing or evidence-tier claim in the system depends on the restoration.
- **Gate policy over mixed depth**: greatest common depth across arms, exactly one paired statistic there, deeper-tier evidence may **veto but never support**, floor = A/A p95 per `(bundle@v, tier, metric)` rather than a policy constant, and `insufficient-depth` as a verdict distinct from `inconclusive` because it names the missing instrument.
- **Determinism is verified, never declared** — a node claiming determinism is re-run on identical input; a mismatch downgrades it out of the intervention tier.
- **A decomposition is gated on parity, not gain.** An improving port is as suspicious as a regressing one.
- **Machine service #2 clarified**: per-arm process isolation is unconditional in every design and is not an architecture discriminator. Store-write confinement is *not* covered by process isolation — store access is a service call, not a syscall — so it comes from service #3's capability token.
- **The foreign-part adapter is a fixed cost**, not a discriminator: process lifecycle, RPC, health, corpus-feed handoff, and evidence normalization exist in any design that hosts a foreign engine.

## Machine primitives the survey demands (SYNTHESIS)

- 5 store types: KV/linked-record, vector (score_all, multi-vector+MaxSim, namespaces), graph (pointwise + bulk-export for PPR-with-reset-vector and community detection), lexical, opaque blob. **No sixth store needed** (gap sweep, 45 types checked)
- Role-addressable LLM clients (extract/filter/map/reduce/answer) with capability flags: logprobs, prefix-continuation (degradation paths required)
- Gap-sweep capability additions: `self-ingesting`, `deferred-extraction`, `parse-derived-graph`, `pass-through-retrieve`, `live-external-retrieval`
- Declared out of scope: `model-weight-access` (DSI, ROME/MEMIT, RAFT, RL retrieval) — chosen non-goal, state it in the verdict

## Self-improvement machine services (RT-selfimprove — all six mandatory)

0. Eval bundle@version (questions+gold+judge+corpus-hash, dev/holdout, sealed holdout)
1. Promotion Gate (A/A null, paired significance, confirmation, FDR, hard-gate regression suite)
2. Isolation Domain + manifest enforcement (deny-by-default net/FS/store-write, wall-clock watchdog, per-arm process)
3. Artifact Ownership + CoW + reference-counted GC (write scoped to recipe@version+namespace; cache keys include component version — cache poisoning is the insidious one)
4. Promotion Ledger (append-only decisions; distinct from lineage tree)
5. Static Mutation Validator (type-check wirings, caps, before execution)

Budgets cover only 1 of 6 mutation-failure classes. Shared-artifact corruption is the largest uncovered blast radius.

## Prior-art adopt/avoid (PRIOR-ART; 18 systems)

**Nothing does all four capabilities; the novel seam is versioned-with-lineage node identity in a declared graph.**

Adopt: Haystack-SHAPED executor (typed sockets, wiring-time validation, cycles, subgraph-as-node) but never the dependency; AutoRAG three-artifact promote split + strategy.py (vendor from legacy tag); DSPy narrowly for prompt-shaped components (compile = the mutation operator); Nix content-addressing at promotion only (cheap hashes in flight); immutable-version + mutable-alias namespace (promote = repoint); lineage IS the version graph + reachability GC (three Cozo relations + recursive Datalog, not a service); Pareto survivor retention (GEPA); sticky bucketing + exposure events (GrowthBook/Statsig).

Avoid: import-path identity (Haystack); DAG-only (LlamaIndex removed theirs); shared-base-class-as-contract (FlashRAG drift); unversioned executor; version pin without environment pin (Feast skew); blind age/count GC; greedy per-node search; discarding losing trials; live-framework dependencies (AutoRAG repurposed, Verba/Canopy archived, fastRAG dead).

## Origin

Synthesized from spike 002. Sources: sources/002-system-architecture-model/ (SYNTHESIS, PRIOR-ART, GAP-SWEEP, RT-modularity, RT-selfimprove)
