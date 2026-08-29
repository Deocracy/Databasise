# Pitfalls Research

**Domain:** Decomposition-and-parity rebuild of a RAG/retrieval engine (LightRAG fork → primitive-part nodes behind a frozen fitting contract; HippoRAG 2 ported; both compared on an eval rig)
**Researched:** 2026-08-29
**Confidence:** MEDIUM (web-sourced, cross-corroborated across independent articles/docs; no project-specific case study exists for this exact shape of rebuild — treat as informed synthesis, not a verified playbook)

## Critical Pitfalls

### Pitfall 1: Database/storage decomposition stalls while logic decomposition looks done

**What goes wrong:**
Strangler-fig writeups agree that peeling application logic into components is the easy 80%; the storage layer is where the migration actually stalls. In this project, `v1/lightrag/kg/cozo_impl.py` and `v1/lightrag/kg/shared_storage.py` are the storage/concurrency seam — decomposing the query-side operate.py pipeline into 17 node positions can look complete while the graph/vector/KV stores underneath are still one entangled Cozo instance with process-wide locks and singleton state (`_manager`, `_storage_instance`, `_global_concurrency_limits` per CONCERNS.md). A phase can report "17 of 18 positions decomposed" and still be sharing un-decomposed storage state across every node.

**Why it happens:**
Storage state is invisible in a call graph. Node boundaries (the fitting contract's effects[] and artifact scopes) describe data flow, not who owns the lock. It is easy to draw clean primitive-part boundaries on paper while every part still reaches into the same `shared_storage.py` singleton at runtime.

**How to avoid:**
Treat storage/locking ownership as its own decomposition axis, tracked separately from node-position count. For each of the 17 query-side positions, explicitly record which storage handle(s) it touches and whether that handle is still shared mutable state or has been given a scoped, node-owned interface. Do not count a node "decomposed" until its storage access is expressed through the machine-owned database primitives (CONTRACT.md's graph/vector/KV primitives), not a direct singleton reference.

**Warning signs:**
- A node's tests pass in isolation but fail when run alongside another node in the same process (shared lock/singleton leaking).
- `initialize_share_data()` / `finalize_share_data()` calls still required between per-node test runs (CONCERNS.md notes every fixture in `test_cozo_frozen_bugs.py` already needs this — a sign the storage layer isn't node-scoped yet).
- Grep for `_storage_instance`, `_manager`, `_global_concurrency_limits` still being referenced directly from decomposed node code instead of through the primitive interface.

**Phase to address:**
Phase where the 17 query-side node positions are cut (§BP rung 2) — track storage-handle ownership as an explicit per-node checklist item, not an afterthought at rung 3/4.

---

### Pitfall 2: "Parity" is declared from a single run, hiding real LLM-output variance

**What goes wrong:**
A single parity run between the old monolith path and the new decomposed path can agree by chance. Public evidence on LLM regression testing states plainly: a single-run evaluation is an unreliable basis for a shipping decision because output quality can swing double digits (~15% in cited cases) across runs under nominally identical conditions — the evaluations are non-deterministic on top of the system under test being non-deterministic.

**Why it happens:**
Temperature=0 is assumed to mean determinism. It does not — infra-level batching, provider-side model updates, and floating-point non-associativity in matrix ops mean identical prompts can still produce different completions and different embeddings run to run. A one-shot parity check that passes gets treated as proof of equivalence.

**How to avoid:**
Never gate a promotion decision (rung transitions, Falsifier 2/5 checks) on a single parity run. Run the parity harness (`v1/tests/parity/run_substrate_parity.py` precedent) N times per side with the LLM/embedding variance held constant (same seeds, same provider, same day if using a hosted API) and report a variance band, not a single diff. Structural diff (already used per PROJECT.md's validated precedent) plus a distributional check (e.g., repeated-run agreement rate) both need to pass.

**Warning signs:**
- Parity harness reports "PASS" from exactly one run per side.
- No variance/repeat-count field in parity run output.
- Flaky CI: the same commit passes parity on one run and fails on a rerun with no code change (the honest signal that a single-run gate was hiding real variance).

**Phase to address:**
Phase 1 — this is the mechanism Falsifier 2 (static depth/execution_mode validator) and Falsifier 5 (A/A calibration) both implicitly depend on; if the parity harness itself is single-shot, the two gating falsifiers are testing against noise.

---

### Pitfall 3: A/A calibration run is underpowered, so it "passes" without meaning anything

**What goes wrong:**
A/A tests exist to measure the system's own noise floor before ever comparing two real variants. If the A/A run's sample size is too small, it doesn't detect the noise it should — the test look "clean" (no significant difference between two identical arms) not because the pipeline is stable, but because the test lacked the power to see instability that is actually there. Later, when LightRAG and HippoRAG 2 are compared for real, any "significant" difference could be pipeline noise mistaken for a modality effect.

**Why it happens:**
Nobody defines a Minimum Detectable Effect (MDE) before running A/A. Corpus/query counts get chosen for convenience (whatever fits in a dev session) rather than derived from the actual variance observed in repeated identical runs. Underpowered A/A calibration is invisible — it doesn't crash, it just quietly certifies noise as signal for every comparison built on top of it.

**How to avoid:**
Before the Phase 1 gate: run the identical pipeline against itself N times, measure the empirical variance in the chosen eval metrics, derive the MDE the corpus size actually supports, and write that MDE down as part of the A/A calibration artifact (RIG §EV.1). Any later LightRAG-vs-HippoRAG comparison must state its effect size against that same MDE — a "difference" smaller than the calibrated noise floor is not a finding.
Recommendation over three small A/A batches: one properly-sized A/A run beats three underpowered ones — it gives one reliable noise-floor number instead of three unreliable ones.

**Warning signs:**
- A/A calibration report has no MDE or confidence interval, just a pass/fail.
- Corpus size for A/A was chosen by what ran fast, not by a power calculation.
- Every subsequent modality comparison reports a "difference" — real pipelines never look perfectly tied, so if every comparison is "significant," the noise floor is probably wrong.

**Phase to address:**
Phase 1, gating Falsifier 5 explicitly — the roadmap's own gate condition. Do not let this phase close on a single A/A run.

---

### Pitfall 4: Dev/holdout/sealed eval splits leak into each other under iteration pressure

**What goes wrong:**
The three-tier eval split (dev/holdout/sealed per RIG §EV.1) exists specifically to prevent the team from unconsciously tuning the decomposition against its own test set. The most common leak isn't a bug — it's iterating against the holdout because the sealed set is inconvenient to touch, then treating a holdout-tuned result as if it generalizes. Reusing the same holdout across many candidate node-boundary choices "informs" those choices the same way reusing a test set across many model variants does in ML — each look at the holdout to decide "should we refactor this node differently" is a small leak, and they compound.

**Why it happens:**
Under deadline pressure, running against the sealed set feels wasteful ("we're not ready yet") so the holdout gets used as a proxy — repeatedly. Nobody logs how many times the holdout was consulted, so the leak is invisible until the sealed-set number disagrees sharply with the holdout number and nobody can explain why.

**How to avoid:**
Log every holdout evaluation as a numbered event (what changed, what the holdout scored) so "how many times did we peek" is answerable. Reserve the sealed set exclusively for promotion decisions (§BP rung transitions), never for day-to-day node-boundary iteration. If the holdout number and the eventual sealed number diverge by more than the calibrated A/A noise floor (Pitfall 3), treat that as a leak signal, not bad luck — re-derive node boundaries were probably shaped by holdout feedback.

**Warning signs:**
- Holdout evaluation run count is unlogged / unknown.
- Sealed-set results are consistently worse than holdout results by more than the A/A noise floor — the classic signature of holdout overfitting.
- A phase plan references "check against holdout" as a routine step inside node-by-node iteration rather than as a periodic checkpoint.

**Phase to address:**
Phase where the eval bundle is stood up (Phase 1, before Falsifier 5) — the split-usage policy must exist before any node decomposition work starts consulting it, not be retrofitted after leakage has already happened.

---

### Pitfall 5: The fitting contract erodes silently under deadline pressure at the ingest boundary

**What goes wrong:**
Plugin/contract literature is consistent: "we don't break the contract" is only an enforced invariant if it's backed by an explicit version, additive-only evolution rules, and an automated compat test suite — otherwise it degrades into an intention that erodes the first time a deadline makes the contract inconvenient. This project has a named, sharp edge for exactly that failure: the ~1,786-line ingest core is deliberately admitted as an **opaque node** under `quarantined` scope (§BP rung 3) specifically because it's too entangled to decompose cleanly yet. The temptation under schedule pressure is to let opaque-node "quarantine" quietly become a dumping ground — new logic gets bolted onto the opaque core instead of onto a fitted node, because that's faster, and the frozen §18 envelope stops actually constraining what crosses the seam.

**Why it happens:**
An opaque node with a real contract boundary and an opaque node used as an escape hatch look identical from the outside — both are "a big blob behind an interface." Only discipline about what's allowed to change inside vs. across the boundary tells them apart, and that discipline is exactly what deadline pressure erodes first.

**How to avoid:**
Write down, at the moment the ingest core is admitted as opaque (rung 3), the explicit list of what may change inside it without a contract review (implementation details) versus what may not (its effects[] signature, the artifact scopes it touches, its NodeKind classification). Any PR that changes the opaque node's boundary triggers the same compat-test-suite gate a real node change would. Do not let "it's already opaque, so anything goes" become the working assumption.

**Warning signs:**
- The opaque ingest node's effects[] signature or artifact scope grows without a corresponding CONTRACT.md repair-log entry (PROJECT.md states contract repairs are recorded, not silent — a growing opaque node with no repair entries is the tell).
- New ingest logic gets added by editing inside the 1,786-line block rather than by adding a new fitted node, "because it's faster and it's already opaque."
- The static depth/execution_mode validator (Falsifier 2) starts needing special-cased exceptions for the opaque node to keep passing.

**Phase to address:**
Phase covering §BP rung 3 (ingest core admission) — write the "what may change inside vs. across" rule into that phase's own definition of done, not as a later audit.

---

### Pitfall 6: Cozo's frozen 0.7.6 correctness bugs get silently re-triggered by refactoring

**What goes wrong:**
Four known silent-wrong-result bugs in Cozo 0.7.6 are currently mitigated by specific query shapes (avoid `count()` aggregation, store all keys as String never UUID, consume JSON as dict not relying on key order, assert types on round-trip) — documented in CONCERNS.md and locked in by `test_cozo_frozen_bugs.py`. Decomposing the graph storage node and rewriting its query construction is exactly the kind of change that can reintroduce one of these query shapes without anyone intending to — the bugs are silent (wrong results, not exceptions), so a regression doesn't fail loudly.

**Why it happens:**
The mitigations live as tribal knowledge in test comments and CONCERNS.md, not as an enforced constraint in the code that touches Cozo. A new node implementation of the graph-storage interface has no mechanical reason to know "don't use `count()` here."

**How to avoid:**
Carry `test_cozo_frozen_bugs.py` forward as a mandatory, non-skippable regression suite that runs against every new graph-storage node implementation, not just the original CozoGraphStorage class. Since Cozo is pinned forever (decision D-P1.1-08), this isn't a one-time migration check — it's a permanent constraint on any code that constructs Cozo queries, for the life of the project.

**Warning signs:**
- A decomposed graph-storage node passes its own unit tests but wasn't run against `test_cozo_frozen_bugs.py`.
- Query construction for the new node uses `count()`, UUID-typed keys, or relies on JSON key order — any of the four previously-avoided patterns.
- Aggregation/counting logic reappears in Python-side workarounds without a comment explaining why (the reason — bug #244 — needs to travel with the code, not just live in CONCERNS.md).

**Phase to address:**
Whichever phase decomposes/re-implements the Cozo graph-storage boundary (part of §BP rung 2/4 node work) — make `test_cozo_frozen_bugs.py` a required check on that phase's node, explicitly, not an inherited assumption.

---

### Pitfall 7: Asyncio + multiprocessing hybrid locking gets carried into new nodes instead of designed out

**What goes wrong:**
`shared_storage.py`'s `UnifiedLock` wraps both `asyncio.Lock` and `multiprocessing.Manager.Lock` to support single- and multi-process modes (CONCERNS.md). General guidance on this pattern is unambiguous: `asyncio.Lock` has no timeout and no non-blocking acquire, so a coroutine that fails to release it wedges every future acquisition; inconsistent lock-acquisition ordering across processes is the standard cause of deadlock; and mixing fork-based multiprocessing with async carries the usual fork-safety hazards. This project's own runner/scheduler/storage-keying design (§H1 must-decide, explicitly still open) is the first place this either gets fixed or gets propagated into every new node.

**Why it happens:**
The hybrid lock already "works" in v1 (no fix, by design, per CONCERNS.md), so the path of least resistance when building the new node/runner layer is to keep calling into the same `UnifiedLock`/`shared_storage` machinery rather than designing the new runner's concurrency model from scratch.

**How to avoid:**
Treat the runner/scheduler/storage-keying decision (§H1) as the place to define a new concurrency model for the machine — not as a decision about which of v1's existing lock primitives to keep using. At minimum, adopt consistent lock ordering across all nodes, and prefer timeout-bounded acquisition (even a coarse hard-coded timeout with a clear error beats an unbounded wait) over the current unbounded `asyncio.Lock` pattern for any new code path.

**Warning signs:**
- The new runner directly imports `UnifiedLock` or reaches into `shared_storage.py`'s module-level singletons rather than defining its own scoped concurrency primitive.
- No documented lock-acquisition order across the runner's components.
- Tests for the new runner never exercise concurrent multi-process execution (CONCERNS.md already flags this as an untested area in v1 — inheriting the pattern without testing it is inheriting the gap too).

**Phase to address:**
The phase that resolves §H1 (runner, scheduler, storage-keying) — first faced at rung 1 per PROJECT.md's own note.

---

### Pitfall 8: Embedding-generation mismatch between old and new paths silently invalidates parity comparisons

**What goes wrong:**
Embedding drift is described consistently across sources as a silent failure: the same text produces a different vector after a model update, a preprocessing change, or partial re-embedding, and the downstream symptom is gradual (irrelevant top results, chunks disappearing from context, more hallucination) rather than a hard error. In a decomposition where the same corpus is meant to be indexed by both the legacy monolith path and the new decomposed nodes for a parity check, any difference in chunking boundaries, preprocessing, or embedding model/version between the two paths invalidates the comparison — the parity harness will report a "difference" that's actually just embedding drift, not a behavioral regression in the decomposition.

**Why it happens:**
Chunking and preprocessing code often move during decomposition (they're exactly the kind of logic getting extracted into nodes), and it's easy for the new node's chunk boundaries or text-normalization order to differ subtly from the old monolith's, especially since v1 already has multiple truncation strategies (token/char/byte-based, per CONCERNS.md) whose interaction is fragile.

**How to avoid:**
Pin the embedding model and version identically across both sides of every parity comparison. Before attributing any parity diff to "the decomposition changed behavior," first check whether chunk boundaries and pre-embedding text normalization are byte-identical between the two paths for the same input — if not, the diff is inconclusive by construction and the harness should flag it as such rather than reporting a plain pass/fail.

**Warning signs:**
- Parity diffs correlate with chunk-boundary or truncation code paths rather than with the node logic actually under test.
- The embedding model/version isn't pinned as a fixed input to the parity harness config.
- Diffs appear only near truncation boundaries (256-char entity name limit, 512-byte normalization limit — CONCERNS.md's two-truncation-path fragility) rather than being distributed across the corpus.

**Phase to address:**
Phase where the parity harness is extended to cover the newly-decomposed nodes (§BP rung 2 onward) — add an explicit "inputs are byte-identical pre-embedding" precondition check to the harness itself.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|--------------------|-----------------|------------------|
| Single parity run per node instead of repeated runs | Faster iteration during node cutting | False confidence in equivalence; noise mistaken for regression or for a clean pass | Only for quick local sanity checks during dev, never as the recorded gate evidence |
| Editing inside the opaque ingest node instead of adding a fitted node | Ships faster under deadline pressure | Contract erosion (Pitfall 5); opaque scope becomes a dumping ground | Never for anything that changes effects[]/artifact scope; acceptable only for genuinely internal implementation tweaks |
| Reusing v1's `UnifiedLock`/`shared_storage` singletons in the new runner | Avoids designing a new concurrency model up front | Inherits untested multi-process deadlock/crash-recovery gaps into the new machine | Acceptable as a temporary bridge only if explicitly flagged and revisited at the §H1 decision point, not left as the permanent design |
| Peeking at the holdout set repeatedly during node-boundary iteration | Fast feedback on whether a refactor helped | Holdout overfitting; sealed-set numbers diverge from holdout numbers later (Pitfall 4) | Acceptable a small, logged number of times per phase; never as the default iteration loop |
| Skipping `test_cozo_frozen_bugs.py` on a new node's graph-storage implementation because "it's a rewrite, not the old code" | Saves a test-writing/adaptation step | Silent reintroduction of one of the four known Cozo correctness bugs (Pitfall 6) | Never — Cozo is frozen forever, so the bug list is frozen too |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|-----------------|--------------------|
| Cozo 0.7.6 (embedded graph/vector/KV store) | Assuming a rewritten query is safe because it "looks equivalent" | Run every new query shape against `test_cozo_frozen_bugs.py`'s four documented bug patterns before trusting results |
| SQLite (if used for any embedded metadata/state store) | Assuming WAL mode gives free multi-process write concurrency | WAL gives unlimited concurrent *readers* but still one writer at a time; design for write contention, ensure "reader gaps" exist so checkpoints can complete, and don't rely on SQLite for genuinely concurrent multi-process writes |
| LLM/embedding providers (injected per Falsifier 8's endpoint survey) | Treating temperature=0 as full determinism for parity purposes | Pin provider, model version, and endpoint per comparison run; still expect run-to-run variance and measure it (Pitfall 2/3), don't assume it away |
| codebase-memory-mcp admission (Falsifier 4) | Assuming "admitted whole-engine" behaves identically under machine-chunking vs. native-chunking without measurement | Run both configurations and compare on the rig — this is explicitly a Falsifier for a reason; don't skip the second run because the first one worked |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Sequential Python-side aggregation for graph queries (inherited from Cozo bug #244 workaround) | Label-popularity / degree queries slow down linearly as graph grows | Carry the workaround forward deliberately (it's correctness-driven, not laziness) but budget for its O(N) cost explicitly in the rig's affordability model (RIG §F3) | Becomes the dominant cost once the corpus grows past the point where in-memory Python enumeration of edges is cheap — no fixed threshold documented, must be measured on the rig |
| Faiss `IndexFlatIP` exact brute-force vector search (v1 default per CONCERNS.md) | Query latency grows linearly with corpus size; fine at small corpus, slow past ~100K vectors per v1's own documented practical limit | If HippoRAG 2 or the eval corpus pushes past that scale, budget for an approximate index (HNSW/IVF) as a follow-up decision, not a silent default carried forward unexamined | Documented practical ceiling ~100K vectors, "1M vectors become slow" per v1 pyproject comment |
| Graph-hop retrieval latency (HippoRAG 2 side, once decomposed) | Comparison rig shows HippoRAG 2 consistently slower than LightRAG at query time | Expect this going in — graph-enhanced retrieval is inherently higher-latency (order 200-500ms vs 50-100ms for vector-only, hop-depth dependent) than pure vector search; don't mistake expected architectural latency difference for a bug in the new node decomposition | Present at any scale; widens with hop depth |
| WAL checkpoint starvation under continuous readers (if SQLite used for any always-open metadata store) | File size for the store grows without bound over a long-running comparison rig session | Ensure the rig's process design includes periodic reader gaps, or use a store/mode where this doesn't apply | Triggers whenever there is always at least one open reader — plausible for a long-running comparison rig process |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Letting the decomposed nodes construct Cozo queries via string interpolation of IDs derived from LLM-extracted entity names | Entity names come from LLM extraction over untrusted document text; if truncation/canonicalization (already fragile per CONCERNS.md) is bypassed, malformed IDs could reach the Datalog query construction | Keep the existing constraint that all node IDs are canonical (MD5-hash-derived) strings, enforced at the primitive boundary, not re-validated ad hoc per node |
| Assuming the frozen §18 contract's invariance rule is a security boundary as well as a compatibility one | A modality swap that's contract-compliant on shape (fields, types) could still leak more than the old modality did (e.g., different opaque-node internals expose different data) if only structural conformance is checked | Treat contract conformance checks and any data-exposure review as separate concerns; structural parity is not a security review |
| Letting REST + MCP surface auth/tenancy assumptions inherit v1's "no namespace ACL enforcement, delegated to application layer" posture (CONCERNS.md) silently into the new standalone product surface | Databasise 2.0 is explicitly a standalone product now (own REST + MCP voice, any consumer), which is a materially different trust boundary than v1's embedded-library posture | Explicitly decide and document the new product's auth/tenancy story at the phase that builds the REST + MCP surface — don't assume the old "delegated to application" answer still applies now that Databasise itself is the API surface |

## "Looks Done But Isn't" Checklist

Framed for this project's actual audience — API/MCP consumers and the comparison rig, not end users (no UI is in scope).

- [ ] **Node decomposition claimed complete:** verify storage/lock ownership per node (Pitfall 1), not just call-graph boundaries — check for direct references to `shared_storage.py` singletons from "decomposed" node code.
- [ ] **Parity check passing:** verify it was run more than once with variance reported (Pitfall 2), and that pre-embedding inputs were byte-identical across both sides (Pitfall 8).
- [ ] **A/A calibration passing:** verify an MDE was computed and documented, not just a pass/fail bit (Pitfall 3).
- [ ] **Opaque ingest node admitted:** verify the "what may change inside vs. across the boundary" rule is written down at admission time, not implied (Pitfall 5).
- [ ] **New graph-storage node implementation:** verify `test_cozo_frozen_bugs.py` (or its successor) actually runs against it, not just the original class (Pitfall 6).
- [ ] **§18 envelope "unchanged":** verify this was checked against an automated compat test suite, not asserted by inspection — plugin-contract literature is explicit that this is the difference between an enforced invariant and an intention.
- [ ] **REST + MCP surface "ready":** verify an explicit auth/tenancy decision was made for the new standalone-product trust boundary, not inherited silently from v1's embedded-library assumptions.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|-----------------|-------------------|
| Silent Cozo bug reintroduction (Pitfall 6) | LOW if caught by the regression suite before merge; HIGH if caught after the eval bundle has already run comparisons on corrupted results | Re-run `test_cozo_frozen_bugs.py` against the offending node, fix the query shape, invalidate and re-run any eval/parity results computed while the bug was live |
| Underpowered A/A calibration discovered late (Pitfall 3) | MEDIUM — requires re-running calibration with a corrected sample size before trusting any downstream comparison | Recompute MDE from a properly-sized A/A run; re-audit every modality comparison made against the old, uncalibrated noise floor; flag any "finding" smaller than the corrected MDE as inconclusive |
| Holdout leakage detected via sealed/holdout divergence (Pitfall 4) | HIGH — implies node-boundary decisions may have been shaped by holdout feedback | Re-run the sealed-set evaluation as the sole source of truth for the affected decisions; if divergence is large, consider the affected node boundaries provisional pending a fresh, unleaked evaluation |
| Contract erosion at the opaque ingest boundary (Pitfall 5) | MEDIUM–HIGH depending on how much drifted before detection | Diff the opaque node's current effects[]/scope against its rung-3 admission baseline; write the missing CONTRACT.md repair-log entries retroactively; decide case by case whether drifted behavior is kept (with a proper contract repair) or reverted |
| Hybrid lock deadlock in the new runner (Pitfall 7) | MEDIUM | Add timeout-bounded acquisition and consistent lock ordering retroactively; this is the point at which §H1's concurrency design should actually get made, rather than deferred again |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|--------------------|----------------|
| Storage/lock ownership hidden inside "decomposed" nodes | §BP rung 2 (17 query-side node positions) | Per-node checklist: storage handle routed through machine primitive, not a direct singleton reference |
| Single-run parity declared as proof of equivalence | Phase 1 (parity harness extension), gates Falsifier 2 | Parity harness reports a repeat count and variance band, not a single pass/fail |
| Underpowered A/A calibration | Phase 1, gates Falsifier 5 | A/A calibration artifact includes a documented MDE derived from measured variance |
| Dev/holdout/sealed split leakage | Phase 1 (eval bundle stand-up), before any node decomposition begins consulting it | Holdout-evaluation event log exists; sealed set never touched outside promotion decisions |
| Fitting-contract erosion at the opaque ingest boundary | §BP rung 3 (ingest core admission) | "Change inside vs. across boundary" rule is written at admission time; every boundary change has a CONTRACT.md repair-log entry |
| Cozo frozen-bug reintroduction | Whichever phase re-implements the graph-storage boundary (rung 2/4) | `test_cozo_frozen_bugs.py` runs green against the new implementation as a required check, not an inherited assumption |
| Hybrid asyncio/multiprocessing locking carried forward undesigned | Phase resolving §H1 (runner/scheduler/storage-keying) | New runner defines its own lock-ordering and timeout policy; does not import v1's `UnifiedLock` singletons directly |
| Embedding/chunking mismatch invalidating parity | §BP rung 2 onward (parity harness extension) | Harness asserts byte-identical pre-embedding input and pinned embedding model/version as a precondition, not an assumption |

## Sources

- [The Strangler Fig Architecture Pattern — Safely Decompose a Monolith into Microservices](https://medium.com/@ankit.vashishta/the-strangler-fig-architecture-pattern-safely-decompose-a-monolith-into-microservices-379d57eb807b) — MEDIUM confidence (community writeup, cross-corroborated by AWS Prescriptive Guidance and multiple independent sources on the same pitfalls)
- [Strangler fig pattern — AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-decomposing-monoliths/strangler-fig.html) — MEDIUM-HIGH (vendor architecture guidance)
- [How We Are Testing Our Agents in Dev — Towards Data Science](https://towardsdatascience.com/how-we-are-testing-our-agents-in-dev/) — MEDIUM
- [How do you A/B test an LLM when outputs aren't deterministic? — GrowthBook](https://www.growthbook.io/insights/ab-testing-llms) — MEDIUM
- [Underpowered A/B Tests – Confusions, Myths, and Reality — Analytics-Toolkit.com](https://blog.analytics-toolkit.com/2020/underpowered-a-b-tests-confusions-myths-reality/) — MEDIUM (specialist experimentation-methodology source)
- [The power and pitfalls of underpowered studies — Pharmacotherapy (Wiley)](https://accpjournals.onlinelibrary.wiley.com/doi/10.1002/phar.4605) — MEDIUM-HIGH (peer-reviewed)
- [How to Avoid Data Leakage When Performing Data Preparation — MachineLearningMastery.com](https://machinelearningmastery.com/data-preparation-without-data-leakage/) — MEDIUM
- [Preventing Training Data Leakage in AI Systems — Tonic.ai](https://www.tonic.ai/blog/prevent-training-data-leakage-ai) — MEDIUM
- [feat(plugins): plugin API versioning, stability contract, and compat test suite — GitHub issue](https://github.com/NousResearch/hermes-agent/issues/64179) — MEDIUM (concrete engineering proposal, directly on-topic for fitting-contract erosion)
- [Plugin Architecture in Practice (Part 4) — Versioning, Distribution, and Ecosystem](https://oninebx.github.io/blog/architecture/plugin-architecture-in-practice-part-4-versioning-distribution-and-ecosystem/) — MEDIUM
- [File Locking And Concurrency In SQLite Version 3 — sqlite.org](https://sqlite.org/lockingv3.html) — HIGH (primary/official documentation)
- [Write-Ahead Logging — sqlite.org](https://sqlite.org/wal.html) — HIGH (primary/official documentation)
- [SQLite concurrent writes and "database is locked" errors](https://tenthousandmeters.com/blog/sqlite-concurrent-writes-and-database-is-locked-errors/) — MEDIUM
- [Embedding Drift: The Quiet Killer of Retrieval Quality in RAG Systems](https://medium.com/@anindyasinghobi/embedding-drift-the-quiet-killer-of-retrieval-quality-in-rag-systems-b5d46bee3bba) — MEDIUM
- [Detecting Embedding Drift: The Silent Killer of RAG Accuracy — Decompressed Learn](https://decompressed.io/learn/embedding-drift) — MEDIUM
- [Multiprocessing Deadlock in Python — SuperFastPython](https://superfastpython.com/multiprocessing-deadlock/) — MEDIUM
- [Synchronization Primitives — Python 3.14 official docs](https://docs.python.org/3/library/asyncio-sync.html) — HIGH (primary/official documentation)
- [RAG Gone Wrong: The 7 Most Common Mistakes — kapa.ai](https://www.kapa.ai/blog/rag-gone-wrong-the-7-most-common-mistakes-and-how-to-avoid-them) — MEDIUM
- [Architectural patterns for graph-enhanced RAG — VentureBeat](https://venturebeat.com/orchestration/architectural-patterns-for-graph-enhanced-rag-moving-beyond-vector-search-in-production) — MEDIUM
- [LLM Regression Testing Pipeline for QA Engineers: RAG Triad & Gold Sets — TestQuality](https://testquality.com/llm-regression-testing-pipeline/) — MEDIUM
- [GitHub — cozodb/cozo](https://github.com/cozodb/cozo) — HIGH (primary source project documentation)
- Project-internal source (authoritative for this codebase): `.planning/codebase/CONCERNS.md` — HIGH (direct code-verified audit of the v1 fork)

---
*Pitfalls research for: Databasise 2.0 decomposition-and-parity rebuild*
*Researched: 2026-08-29*
