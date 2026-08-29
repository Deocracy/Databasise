# The Selected Architecture — contract skeleton

**One machine. No sandbox regime. No `regime` field.** This is the frozen boundary set from spike 003's selection, and it is the direct input to SPIKE-PLAN step 8. Where this file and any variant document disagree, this file governs; where this file and `sources/003-d-variants/SELECTION.md` disagree, SELECTION.md governs.

## Requirements

- One executor runs everything: decomposed components, harnesses, planners, and whole foreign engines are all nodes in one JSON wiring
- Depth is **computed by the validator, never declared**; containment is **derived from declared effects, never requested**
- A node may write into a shared artifact namespace **only if its effective depth is `stage`**
- Every mutation is a version operation: branch → A/B → promote/rollback, nothing edited in place
- The eval bundle and promotion gate exist before the architecture is built — sequencing is unchanged and binding

## How to Build It

### 1. Wiring format and identity

JSON with no evaluation semantics. `nodes` (id → instance), `deps` (partial order; cycles legal, reported as `{cycle:[...]}` data), `recipe` (SA-2 stamp sources), `harnesses` (ordered array), `provides`.

- **Node ids are positions, never instance identities.** Keying by identity silently drops fan-out branches — measured.
- **Edge semantics are named in the contract**: an edge means *exactly-once dataflow per run*. Whether fan-out branches run concurrently is a **declared executor property**, and the A/A null must be calibrated under the same concurrency/determinism setting as the arms it judges. Inheriting edge semantics silently was a lineup-wide blind spot.
- `config_hash` = SHA-256 over author-supplied JSON, RFC 8785 (JCS), no ints outside int64, `1 ≡ 1.0`, **environment hash included**. Instance = `(name@version, config_hash, resolved_dependency_ids)`. For an opaque node the environment hash covers the **whole resolved runtime closure** — not the declared one (D1 got this wrong; it is the exact Feast skew the environment hash exists to kill).
- **Runtime-minted instances** (nodes inside planner-emitted plans): `H(component_instance_hash, JCS(runtime_config), parent_instance_hash, ordinal)`. Without this, `config_hash` assumes an author and ephemeral plan nodes have no identity.
- Spec pins contract-version ranges; a per-run lock records resolved behavior versions, artifact ids, and **resolved model per role** (role→binding is hot-updatable at runtime, so recording the role name is not enough).
- Arm = base + RFC 7386 merge-patch (additive/override; a differing kind tag replaces the whole `kind` subtree) + **RFC 6902 for subtraction**. Validate the base independently with no arms applied.

### 2. Node kinds and effects

- `NodeKind` is a tagged sum (single-key object, per-kind schema, portable vocabulary): the ~10 primitive part types plus `fanout`, `join`, `fixpoint`, `subgraph`, `opaque`.
- `effects[] ⊆ {reads_kv, reads_vector, reads_graph, reads_lexical, writes_artifact, calls_llm, calls_rerank, net, fs, self_storage}`, plus `iterative`, `space_id`, `presumes_graph`, `accepts/emits kinds`, `accepts/emits score semantics`, `order_stable`, `hierarchy_aware`, `checkpoint?`. **Undeclared is denied.**
- **Iterative components are hosted as `fixpoint` nodes — the executor owns every loop and its halt.** Leaving the loop inside the component means the machine can kill but not meter it, which fails rubric goal 10.
- `join` sockets: `List[List[X]] → List[X]` and `List[Draft] → Draft`. `fanout` arity static or from an upstream output socket; budget accounting multiplicative.

### 3. Depth and containment — the load-bearing mechanism

- `depth ∈ {opaque, evidence, stage}` per node, **computed by the validator from wiring + registry**, never declared.
- **The taint rule:** effective depth = **minimum over transitive `deps`**. Wiring depth = min over the compared path. Stamped on every run record and board row.
- **The blast-radius rule:** a node may write into a **shared** artifact namespace **only if its effective depth is `stage`**.
- **Artifact scopes are three, not two** (amended by spike 005, which ran Falsifier 1):

  | Scope | Who may write | Shareable |
  |---|---|---|
  | `shared` | effective depth `stage` only | yes, SA-1-addressed, recipe-compatible |
  | `quarantined` | any depth, including `opaque` | **never** — instance-scoped, single-provenance, readable only by explicit pin, GC'd with the instance |
  | `self_storage` | any depth | no, private |

  Without the middle scope the architecture forbids its own entry state: an opaque LightRAG cannot write the shared index, and producing the index is what ingest *is*. Spike 001 [code-verified] fixes the order — the query path is already component-shaped and decomposes first; the index side is the entangled ~1,786-line side and stays opaque longest. **Cost, stated rather than hidden:** no artifact sharing in the middle state, so two modalities over an opaque index each re-index (candidate C's N× token cost), paid only until decomposition. Decomposition is thereby how a part *earns* artifact sharing — the ratchet priced in tokens instead of asserted as discipline.
- `execution_mode ∈ {in-process, subprocess, confined-unit, long-lived-service}` **derived from `effects`**. Pure non-iterative nodes only may be in-process. **The arm is always its own confined process** — `in-process` describes node hosting *inside* an arm, and the two never conflict.
- Cross-process invocations record placement of both endpoints and, on failure, the failure cause (deadline vs kill vs capability denial).

### 4. Evidence and measurement

- `ScoredItem{ref, kind, score, provenance, payload}`; `Score{value, semantics, space_id}`.
- **`ItemKind` is an open, recipe-declared registry over a typed union** — evidence is a union, not a node: `text_chunk | graph_path | code_snippet | fact_with_validity_interval | page_image_ref | sql_result_set`, plus `derived_finding` carrying `derived_from: [Ref]`. Every stage-diffing and evidence-tier claim depends on this.
- `ChunkRef = (corpus_id, recipe@version, ordinal, content_hash)`; deref raises loudly; `refs_in`/`refs_resolved` per run; positional indices only as part-local projections with auditable bijections.
- **Evidence-item tier** `∈ {T0 answer, T1 evidence, T2 stage, T3 node}`, machine-stamped from what actually arrived. T2 requires stage-depth producing boundaries with instance hashes; T3 requires an actually-performed intervention plus `held_constant` computed from recipe hashes plus **determinism verified by re-run** (never declared).
- **Pooling key:** `(eval_bundle@v, corpus@v, judge_instance, tier, counted_by, feed_tier)`. `space_id` joins the key **at T1 and deeper, excluded at T0** — at answer tier the embedder is an attribute of the thing under test and the instance hash already pins it.
- `counted_by` on every token number; central recount for cross-part comparison; `unbudgetable` nodes excluded from token comparison **by explicit refusal, never a wrong number**.
- `EmbeddingSpace` id hashed from `(model_id, revision, dim, metric, normalization, query_prefix, doc_prefix, pooling, namespace_text_convention)`; namespaces immutable in space; `reads_space`/`writes_space` typechecked at load; **embedder identity mandatory — the machine refuses to write vectors it cannot attribute.**
- `ContextPackage` blocks with `order_policy`; machine-owned renderer; `requires_block_kinds`; assemblers return `List[ContextPackage]`.

### 5. The gate

One implementation, verb ladder `check | preview | run | promote-next | promote-now`.

Verdicts: `promote | reject | inconclusive | insufficient-depth | below-floor | unconfirmed | regression-veto | straddle`, each carrying the evidence pointer and the tier of decision. `insufficient-depth` is distinct from `inconclusive` because it **names the missing instrument**.

Policy: greatest common depth across arms → exactly one paired statistic there (exact McNemar binary / paired bootstrap continuous) → per-`(bundle@v, tier, metric)` A/A nulls with **floor = A/A p95, never a policy constant** → confirmation on disjoint subsets → epoch FDR. Hard gates are vetoes wherever observable. **Cross-tier evidence may veto, never support.**

Refusals, as contract rather than policy: mixed pooling keys; `refs_resolved < refs_in`; runtime-downgraded depth; stale A/A null for the artifact set; differing resolved artifact ids across arms; `held_constant` diff exceeding the declared mutation; mixed `counted_by` without recount; mismatched determinism/concurrency setting; claims gated below their minimum tier.

**A decomposition is gated on parity, not gain** — its difference must fall inside the A/A band or name its declared deviations. An improving port is as suspicious as a regressing one.

### 6. Promotion, decomposition, migration

- Mutation promotion: atomic alias repoint plus generation record (~1 ms, `rename(2)`, multi-artifact in one swap). **The ledger append is the decision; the active pointer is a projection; the ledger wins on disagreement; running an arm never appends.**
- Part promotion = **node → subgraph in place**, node id unchanged, depth recomputed. Idempotent, so absorbing upstream v2 reuses the same mechanism — this is the re-promotion path RT-upgradability said D lacked. Losers tombstoned (~200 bytes).
- **SA-3 migration component** — the eighth primitive: a versioned artifact transforming `recipe@vN → recipe@vN+1`, declaring the pairs it bridges, lineage-tracked. Acceptance test = rig parity run over pre/post artifacts (`run_substrate_parity.py` is the working precedent). Companion policy: `unknown` provenance is readable, never declared-compatible.
- Reindex planner classifies `{reuse | re-embed | re-extract | rebuild}` plus cost, walking SA-2 stamps. `consumes_embedder` chunkers make their KV recipe-bound and escalate re-embed → rebuild.

### 7. Registries and retention

- **Component registry** (bytes, never deleted): `upstream_ref (repo, tag/commit, file/symbol)` per entry **and per realized node**, so upstream drift has an owner per node rather than per part; decomposition record with computed ratio, published beside every board result.
- **Artifact registry** (gigabytes, deletion required): namespace → sub-recipe stamps + corpus + `space_id` + producing instance. Blob artifacts carry machine-owned **sidecar provenance manifests**. Retention tiers `runnable | readable | tombstoned` plus a scheduled reconstructability probe. GC keyed on recipe-version reachability, counting runtime-minted instances.
- **Ledger records** carry: mutation id, class, parent, arm instance hashes, effect size, verdict, evidence pointer, proposer id, depth label, tier-of-decision, decomposition ratio, opaque-node TTL renewals with reasons, and parity records for decompositions. Proposer hit-rate per class must be derivable by query.

### 8. Opaque-node admission conditions

Manifest validated · whole-closure environment hash · denied network namespace with the machine as **injected LLM provider** (or admitted `unbudgetable`) · wall-clock ceiling · `storage: machine | self-contained` declared, with machine-storage writes still subject to the blast-radius rule — **an opaque node may write `quarantined`, never `shared`** · corpus feed at a declared `feed_tier`, **chunk feed refused for embedder-coupled recipes** · excluded from the default selector at `opaque` effective depth · TTL (~90 days) with recorded-reason renewal · explicit `part_ref` invocations counted as data · **no SA-1-shareable artifacts** (resolved inputs are not enumerable — enforced, not discovered) · `as_of` refused without a declared `temporal` capability.

### 9. Budget, instruments, planes

- **Budget is a splittable capability token**, not a global counter: spend (steps/tokens/time) and capacity (consumer context window) separated; multiplicative under fan-out **by construction** — a branch cannot spend what it was not handed. Encloses ingest and query. Partial and budget-halted runs are first-class: traced, scored, tier-labeled, never discarded. Degradation paths declarable in manifests.
- **Versioned instruments** — eval bundle (questions + gold + judge instance + judge prompt hash + corpus snapshot hash + determinism/concurrency setting; dev/holdout/sealed; **two target families**: gold-passage targets and answer-level targets), judge, selector policy, mutation proposer, **and the executor** — each named in every trace it touched.
- **Plane rules:** artifact-plane values are resolved at load and passed in; components cannot query registry, ledger, scoreboard, or artifact registry during a run. The execution plane **may** invoke the validator on a planner-emitted plan against the **load-frozen snapshot**; it may **never** read mutable decision state mid-run. Emitted plans are JSON over the declared alphabet, validated pre-execution against a restricted allowlist plus planner-manifest caps, recorded verbatim as trace data, and never registered, aliased, or ledgered.

## What to avoid

- **Never let a part declare its own depth or request its own containment.** Both are computed. This is the entire selection.
- **Never allow a shared-artifact write from a node whose *effective* depth is below `stage`** — per-node checking without the taint rule is the laundering path, D4's one unpatched hole.
- **Never digest a declared closure where a resolved one is required.** D1 did; it is the Feast version-skew failure with extra steps.
- **Never write "the artifact plane is read-only to components at runtime"** — that guards the wrong direction. A control channel *is* a read. The rule is that artifact-plane values are resolved before the run and passed in.
- **Never gate on evidence shallower than the claim class requires**, on runtime-downgraded depth, or across a pooling-key mismatch. Return `insufficient-depth` and name the missing instrument.
- **Never let cross-tier evidence support a promotion.** It may veto only.
- **Never treat a decomposition's *improvement* as success** — parity is the gate; an improving port means something changed that was not declared.
- **Never adaptively allocate arms mid-run.** It is the one attractive way this design merges the two planes.
- **Never ship a chunk-tier corpus feed to an embedder-coupled recipe.** Chunk boundaries are a function of the embedding model under chunker strategy `V` [code-verified], so paradigm-neutral chunks do not exist there.

## Constraints

- **Falsifier 1 has been run** (spike 005, runnable `taint.py`, 12 cases). The taint rule is measured sound; the *argument* that justified it was inverted against spike 001 and is falsified; the selection survives on the quarantined scope above. Falsifiers 2–8 remain unrun.
- Statistical power is the binding constraint on everything above: at 30–50 eval questions, power for a genuine +5 pp effect is ≈0.10 and a naive adopt-if-higher rule promotes noise ~5:1. **Benchmarks never settle decisions; only local measurement on our own corpus does.**
- Validator cost: 22 ms in-process. Promotion: ~1 ms. Artifact hashing: ~1.3 GB/s hash-only.
- Open and deliberately undecided here: the socket type system and capability vocabulary (step 8's own work, now with `ItemKind`'s union and the `effects[]` vocabulary as fixed points); whether `evidence` survives as a distinct structural depth or collapses into "opaque node that passes clause 3 at its boundary"; validator implementation choice (bespoke / hardened `evalModules` / CUE).

## Origin

Synthesized from spike 003 — `sources/003-d-variants/SELECTION.md` §Contract skeleton, with mechanisms grafted from all four variants and the red team. Builds on the five contract clauses and six machine services from spike 002 (`references/fitting-contract-and-safety.md`) and the wiring format from spike 004 (`references/wiring-spec-and-validation.md`).
