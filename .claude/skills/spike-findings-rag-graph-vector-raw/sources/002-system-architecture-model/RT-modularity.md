# Red Team — Modularity / Hidden Coupling

**Lens:** is the claimed modularity real, or does the capability-manifest story paper over couplings that survive it?
**Targets:** CANDIDATES.md §0 (Shared Anatomy) and Candidates A/B/C/D.
**Evidence tags:** `[code-verified]` (read from source in the research pass), `[docs-verified]`, `[paper-claim]`, `[inference]`. No benchmark numbers used.
**Posture:** assume every declaration not checked by a machine is decoration.

---

## 0. Opening shot — the sharing story is validated by a non-independent example

The Shared Anatomy diagram proves component sharing with two wirings: `lightrag-local@3.1` and `pathrag@0.9`, sharing `seed-selector@1.0`, `assembler@2.2`, `generator@1.0`.

**PathRAG is a fork of LightRAG's `operate.py`** [code-verified — MODALITIES-GRAPH §5: "Identical skeleton to LightRAG (it forked `operate.py`)... Shared: everything index-side and the keyword seeding — literally LightRAG code"]. The two wirings share components because they *are the same program* with a different middle stage. That demonstration establishes nothing about hosting HippoRAG 2, a code-symbol graph, ColPali, or CAG in the same component set.

The same applies to the artifact-sharing claim. Across ~24 surveyed systems there is exactly **one** code-verified instance of one modality reading another's index: PathRAG over LightRAG's — a fork [code-verified]. HippoRAG 2 cannot read a LightRAG graph (no passage nodes, no fact store, no synonymy edges) [code-verified]; MS GraphRAG cannot (no community hierarchy) [code-verified]; Fast-GraphRAG cannot (no e2r/r2c incidence matrices, different edge-weight meaning) [code-verified].

Honest restatement of goal 6: **paradigm-shaped artifact sharing is a within-family property (the GraphRAG-prompt-lineage family), not a machine-wide one.** The genuinely broad sharing layer is chunk-level — KV chunks + chunk vectors given the same chunker and embedder [SYNTHESIS §5]. That layer is real and valuable. It is also, per Attacks 1 and 2 below, precisely the layer carrying the most undeclared coupling. **The only broadly shareable artifact layer is the one with the worst hidden coupling.**

---

## Attack 1 — Tokenizer coupling and chunk-ID identity

### 1a. Token budgets assume a tokenizer that lives inside the component

Token-budget logic is confirmed inside the assembly stage of at least five surveyed systems:
LightRAG `_apply_token_truncation(search_result: dict) -> dict`, a named stage of its 4-stage query path [code-verified, spike 001]; RAPTOR accumulates nodes "until `total_tokens + node_tokens > max_tokens`" [code-verified]; MS GraphRAG local builds "token-budgeted mixed context tables" and global "token-batches" reports for map calls [code-verified]; Fast-GraphRAG packs context "to token budget" [code-verified]; PathRAG inherits LightRAG's truncation [code-verified]. The *identity* of the tokenizer each uses is component-internal in every case [inference — the research recorded the budget stage, not the counter].

**Failure narrative.** `assembler@2.2` is pinned with `max_tokens: 8000`, counted with the tokenizer it was written against. The self-improvement loop (goal 7) branches the wiring to A/B a different generator — a local Llama-class model whose tokenizer emits materially more tokens for the same text, worse on code and non-English [inference, but a standard property of BPE vocabulary differences]. Nothing throws. Three consequences fire at once:

1. The provider silently truncates the tail of the prompt. For PathRAG that tail is the *most reliable paths* — its assembler orders paths ascending specifically so the best sit closest to the answer position [code-verified mechanics; ordering rationale is [paper-claim]]. Truncation deletes the highest-value evidence first.
2. The trace records `assembler@2.2`, `generator@2.0`, a token count, and an answer. Quality dropped. Lineage attributes the drop to the generator swap. **The machine has learned a false fact and will avoid that generator forever.** Goal 7's promise — "a quality regression is attributable to a version diff" — is satisfied syntactically and violated in substance.
3. The Budget enforcer (a machine service in the Shared Anatomy) meters using provider-returned usage; the assembler meters using a local count. They disagree, so a "budget-obedient" component (goal 10) can be halted mid-run for exceeding a budget it believed it was under.

**Worse than a correctness bug: it is a measurement bug.** Test dimension 13 is token use, and Candidate C's *only* deep comparison axis is tokens. If N parts count tokens with N tokenizers, "token use" is not a comparable quantity, and the rig's headline number is unit-inconsistent across parts.

### 1b. Chunk IDs must match across KV / vector / graph — and the ID schemes are not the same shape

Four ID schemes, all code-verified, all in scope:

| Part | Chunk identity | Shape |
|---|---|---|
| LightRAG | `source_id` fields on entities/edges join to chunk KV [code-verified] | string key |
| HippoRAG 2 | passage node `chunk-<md5>`; entity node `entity-<md5(phrase)>`; `ent_node_to_chunk_ids` map [code-verified] | content hash, prefixed |
| Fast-GraphRAG | chunk = a **column index** in a `csr_matrix` (`_relationships_to_chunks`) [code-verified] | dense positional int |
| RAPTOR | `Node.index: int`, `children: Set[int]` [code-verified] | dense positional int, layer-ordered |
| Auto-merging | `node_id` with `parent_node`/`next_node` relationship ids in payload [code-verified] | string key + FK graph |

**Failure narrative A (positional drift).** Shared KV keyed by chunk id [PROJECT.md key decision: "Shared KV across parts"]. `chunker@1.2 → 1.3` ships a whitespace-normalization fix — a *behavior-only* rev, explicitly permitted under goal 7's two-axis model. Content-hash parts correctly invalidate and re-index. Positional-index parts (Fast-GraphRAG's csr, RAPTOR's ints) keep resolving: the rows still exist, they now point at different text. No exception. Provenance still reads `recipe ER1@v2`, which is true of the graph and false of the chunk join.

**Failure narrative B (namespace mismatch → the worst RAG failure).** Two wirings share `assembler@2.2` on the same recipe. Wiring 1 hands it entity nodes carrying bare `source_id` strings; wiring 2 hands it PPR passage-node ids of the form `chunk-<md5>` [code-verified]. If deref is lenient — a `.get(id, None)` with a filter — the assembler emits a context package with zero resolved chunks, the generator answers from parametric memory, and the trace records a successful run with a normal token count. **A confident sourceless answer that no observability field distinguishes from a good one.** Candidate A's stage-diffing will faithfully show that the two ASSEMBLE outputs differ and explain nothing.

### Vulnerability

- **A — high.** Fixed slots with "plain-data contracts"; LightRAG's real stage boundaries pass bare `dict`/`list[dict]` [code-verified], and nothing typechecks an ID namespace. A's headline feature (stage diffing) reports the symptom without the cause.
- **B — high, amplified.** Loops re-enter assembly; miscounts and unresolved refs compound per iteration, and a budget halt mid-loop produces a truncated trace indistinguishable from a quality regression.
- **C — low for correctness, worst for measurement.** Each engine owns its IDs and its counter end-to-end, so no cross-part ID contract exists to break. But C's one comparison axis is tokens counted N different ways.
- **D — inherits both, and the promotion path is the seam.** Porting a sandbox engine into kernel components is exactly the refactor where a positional ID scheme gets kept "temporarily"; and a part measured cheap in sandbox becomes expensive in kernel purely from a tokenizer change, corrupting the promotion decision itself.

### Fix — what must be in the contract

1. **Token counting is a machine service, not component code.** `machine.pack(blocks, budget, consumer_model_ref)`; the budget is defined against the *consuming* client, and wiring validation fails if an assembler carrying a token budget is wired to a generator whose tokenizer is unresolvable.
2. **Every reported token number carries `counted_by` (tokenizer id + revision).** The rig refuses to compare counts with differing `counted_by` unless it re-counts centrally on a canonical tokenizer. Store raw text alongside counts so re-counting is always possible.
3. **Budgets expressed as a fraction of the consumer's context window**, not absolute integers, removes most of this coupling for free.
4. **Chunk identity is a machine-minted opaque handle**, not a part-computed hash: `ChunkRef = (corpus_id, recipe@version, ordinal, content_hash)`. Positional/dense indices are permitted only as a *part-local projection* with a declared bijection the machine can audit — HippoRAG already keeps exactly this (`node_name_to_vertex_idx`, `passage_node_idxs`) [code-verified], so the contract only has to name what the code already does.
5. **Deref fails loudly.** `machine.deref(ref)` raises on unknown; an assembler may not emit a package containing unresolved refs; every run records `refs_in / refs_resolved` and the rig fails any run where `resolved < in`. This single invariant converts the worst silent failure into a loud one.

---

## Attack 2 — Embedding-space coupling: `seed-selector@1.0` shared by two wirings

The diagram shares one seed selector across `lightrag-local@3.1` and `pathrag@0.9`. What LightRAG's seeding actually is [code-verified]: one LLM call extracts high-level and low-level keywords, then searches the entity VDB (built from *entity name + description*) and the relationship VDB (built from *relationship keywords + description*) with **top-k cosine plus a similarity threshold**.

So `seed-selector@1.0` is not `f(query) -> seeds`. It is `f(query, embedding_model, namespace_text_convention, threshold_calibration) -> seeds`. Three of those four are invisible in `name@version`.

**Failure narrative (space poisoning).** The A/B loop branches the recipe to test a cheaper embedder. Dimension mismatch is the *lucky* outcome — it throws. The unlucky ones:

- **Same dimension, different space** (e.g. two 1024-d encoders). Cosine values stay in range and look plausible, typically compressing toward the middle with poor separation [inference]. LightRAG's threshold is now calibrated against the wrong distribution: either it returns nothing (empty seeds → empty context → the sourceless-answer failure from Attack 1b) or, with the threshold at zero, it returns the top-k *nearest noise* — a roughly arbitrary entity set. The rig reports "wiring 2 is worse." True, and for the wrong reason. Lineage records "embedder change hurt quality." **The self-improvement loop has been poisoned with a false causal claim, and nothing in the trace can distinguish it from a real one.**
- **Same model, different convention.** e5/bge-family encoders expect asymmetric `query:` / `passage:` prefixes or an instruction on the query side [docs-verified for the model families; not re-verified this pass]. A seed selector that hardcodes no prefix is correct for one provider and silently degraded for another.
- **Same model, same space, different text distribution.** The index side embedded *entity name + description*; the query side embeds a bare keyword. Identical `space_id`, still a mismatch — this one is a property of the *namespace convention*, which no "embedding model id" field catches [inference].

Add the hard cases the survey already contains: HippoRAG 2 needs dense scoring against **all** fact embeddings, not top-k [code-verified]; ColBERT/ColPali need `encode_multi -> matrix` and MaxSim, a different space *shape* [code-verified]; codebase-memory-mcp compiles `nomic-embed-code` 768-d int8 vectors into its binary [code-verified] — a space the machine cannot participate in at all.

### Vulnerability

- **A, B — highest.** They share components most aggressively, and the sharing is exactly what breaks the moment the recipe is branched — which is goal 7's core operation.
- **C — immune by construction.** Each engine brings its own embedder; C is the only candidate where this is honest. Its price: cbm-style parts can never share artifacts with anything, ever.
- **D — inherits, plus a specific promotion cost.** A sandbox part with its own embedding space cannot have its artifacts promoted; "promotion" is not a refactor, it is a full re-index. CANDIDATES.md's D section does not say this.

### Fix

1. **`EmbeddingSpace` is a first-class identity**, hashed from `(model_id, revision, dim, metric, normalization, query_prefix, doc_prefix, pooling, namespace_text_convention)`.
2. **Vector namespaces are stamped with `space_id` at creation and are immutable in space.** Changing any field mints a new namespace; it never mutates one.
3. **Every vector-touching component declares `reads_space` / `writes_space`**, and wiring validation is a typecheck: a seed selector reading namespace N must have a query encoder whose `space_id == N.space_id`.
4. **A shared component must be space-polymorphic or space-pinned, and declare which.** `seed-selector@1.0` is legitimately shareable only if the encoder is an *injected, wiring-pinned dependency* — otherwise the version identity is a lie, because one version behaves differently in each wiring. **Version identity must cover the dependency closure, not just the code.**
5. **Absolute similarity thresholds are space-bound.** Prefer rank- or percentile-based selection; if an absolute threshold is used it travels with its `space_id` and the machine refuses to apply it cross-space.

---

## Attack 3 — Prompt-format coupling: `generator@1.0` shared by two wirings

What the survey's assemblers actually emit [all code-verified]:

| Modality | Context shape |
|---|---|
| LightRAG | entities table + relations table + chunks, per-section budgets |
| PathRAG | entities table + relations table + **paths as text, ordered ascending by reliability** |
| HippoRAG 2 | plain top-k passages, no tables |
| MS GraphRAG global | report batches → **N map prompts** → 1 reduce prompt over scored points |
| RAPTOR | greedy flat concatenation to budget |
| RAG-Anything | modality-tagged blocks, images routed to a VLM |
| CAG | the whole corpus, no selection |

**Failure narrative A (the shared generator).** `generator@1.0` works across the two diagrammed wirings because both emit tables — because they are the same fork (§0). Wire it after a HippoRAG-style assembler emitting plain passages: the generator's system prompt instructs the model to read entity and relationship tables that do not exist. The model does not error. It hedges, or hallucinates section references, and any downstream reference extraction — Sourcerer's Library/Graph applets render citations [inference from PROJECT.md] — loses its anchors. Silent again.

**Failure narrative B (the harness splice — this one is structural).** FLARE re-enters retrieval mid-answer with `ctx_increase: 'replace'`: it swaps new passages into the prompt and regenerates the sentence [code-verified]. To splice, the harness must know where in the prompt the context lives. If the assembler returns an opaque string, the harness will regex for a section header. `assembler@2.2 → 2.3` renames `-----Entities-----` to `## Entities`. The regex misses, the harness appends instead of replacing, context is duplicated, tokens blow out, the budget enforcer halts the run.

That version bump was *behavior-only under a stable contract* — explicitly sanctioned by goal 7 ("behavior version — its internals — free to rev under a stable contract"). **Therefore: the two-axis version model mis-classifies rendered output format as internals.** Any consumer that parses, splices, or positionally depends on rendered text makes format a contract surface. Today `List[ScoredNode] -> str` typechecks perfectly and carries an entire undeclared schema. *Every stringly-typed boundary in a modular system is an undeclared schema.*

Extreme case for completeness: Self-RAG's generator requires a model whose **vocabulary** contains reflection tokens (`[Retrieval]`, `[Relevant]`, `[Utility:1..5]`, `<paragraph>`) and reads their logprobs [code-verified]. A component that constrains the machine's model choice has no field to say so in the current manifest.

### Vulnerability

- **A — high.** The ASSEMBLE→GENERATE boundary is where the string lives, and "plain-data contract" is exactly the phrase that lets a `str` through.
- **B — highest.** B's entire value is control flow, and control flow over an opaque string is string surgery. Loops re-render; harnesses splice.
- **C — immune, at a cost.** Each engine owns its prompt end-to-end. But prompt format is among the highest-leverage improvement knobs, and C forecloses A/B-ing it across parts permanently.
- **D — kernel high, plus a unique failure.** Sandbox→kernel promotion is precisely where a monolith's prompt is cut into assembler + generator, and the port loses the implicit format agreement that made the original work. **Expect the first several ports to look like kernel regressions when they are format-decoupling bugs**, which will discredit the kernel and stall the promotion path — the exact rot mode CANDIDATES.md flags for D, arriving through a mechanism it does not name.

### Fix

1. **Assembler emits a `ContextPackage`, not a string**: an ordered list of typed blocks `{kind, ref(s), content, token_count, role}` where `kind ∈ {entity_table, relation_table, path, passage, community_report, code_snippet, page_image, sql_result, derived_finding}` — an open registry declared per recipe.
2. **Rendering happens exactly once, in a machine-owned renderer pinned by the wiring** (or in the generator). Harnesses manipulate blocks; they never touch text.
3. **Generators declare `requires_block_kinds` / `accepts_block_kinds`**; wiring validation fails when the assembler cannot emit a required kind. This kills the shared-generator bug at wire time instead of at answer time.
4. **Block order is a declared property** (`order_policy: best_last | best_first`) because PathRAG's ascending order is load-bearing [code-verified mechanics].
5. **Components may pin machine clients**: `requires_model: <id>` / `requires_client_capability: [logprobs, prefix_continuation, prompt_cache]` — the survey already demands logprobs (Self-RAG, FLARE), prefix continuation (FLARE), and prompt-cache control (CAG) [all code-verified or concept-verified].
6. **Assembler returns `List[ContextPackage]`**, not one. MS-global's map-reduce forces it [code-verified], and it is one of only two surveyed ways to answer corpus-global questions; a single-package signature quietly excludes it.

---

## Attack 4 — Ontology leakage: is "paradigm-neutral vocabulary" real or a euphemism?

Rubric goal 2 claims "plain-data in/out at every boundary, paradigm-neutral vocabulary (seeds/evidence, not entities/relations)". Tested against three genuinely different paradigms:

**LightRAG.** Seeds = entities and relations, each carrying description text, degree, and a `source_id` chunk list. Rank = node/edge degree [code-verified].

**HippoRAG 2.** The seed stage does not produce a candidate list. It produces a **probability mass distribution over every vertex in the graph** — the PPR reset vector — assembled from: fact scores, each fact decomposed to subject/object phrases, phrase weight divided by the number of chunks containing that entity (specificity), averaged across facts, blended with min-max-normalized dense passage scores at a fixed `passage_node_weight = 0.05`, placed on **passage nodes** which coexist with phrase nodes in one heterogeneous graph; PPR runs undirected weighted with `damping=0.5` via prpack, and scores are read back **only at passage-node indices** [all code-verified].

**Code symbol graphs (cgr / cbm).** Seeds = symbols identified by *qualified name* with hierarchical matching semantics — the Cypher generation prompt mandates `qualified_name ENDS WITH` for matching and `STARTS WITH` for project scoping [code-verified]. Node labels are Project/Package/Folder/File/Module/Class/Function/Method/Interface/Enum/Type/Route/Resource; edges CALLS, DEFINES, IMPORTS, INHERITS, IMPLEMENTS, HANDLES, FLOWS_TO, TESTS, FILE_CHANGES_WITH [code-verified, both repos, converged independently].

### Three leaks, in increasing severity

**Leak 1 — score semantics.** LightRAG's score is a cosine similarity; HippoRAG's seed score is reset mass and its final score is a PPR stationary probability; Fast-GraphRAG's is a normalized sparse reset; BM25's is unbounded; RRF's is reciprocal-rank sum; a grader LLM's is an ordinal label [all code-verified]. All of them are `float`. LlamaIndex's fusion component offers `relative-score` and `dist-based` modes alongside RRF [code-verified] — the first two *normalize by score range*. Feed a PPR distribution and a cosine list into a range-normalizing fuser and it returns confident garbage. No exception, no warning, and the type signature is satisfied.

**Leak 2 — item kind, and units that are not nodes.** `List[ScoredNode]` cannot hold PathRAG's primary evidence unit: a **path** is a sequence of edges with its own reliability score computed as the mean of its edge weights [code-verified]. Representing it as a "node" with a synthetic id is a lie the assembler must then decode. Same for MS-global's map output — LLM-authored *scored points* with no corpus ref at all [code-verified] — and for ColPali's page images and text-to-SQL's result sets [code-verified/concept-verified]. Meanwhile a heterogeneous list mixing phrase and passage nodes needs a partition tag or downstream stages silently mix them; HippoRAG's readback is partition-specific [code-verified].

The research already got this right — MODALITIES-CODE-AND-ALIEN §(b) specifies "`evidence[]` is a typed union: text chunk | graph path | code snippet | fact-with-validity-interval | page image ref | SQL result set". **Candidate A's RANK slot regresses it to `List[ScoredNode] -> List[ScoredNode]`.** That is a documented narrowing between SYNTHESIS and CANDIDATES, and it drops four of six evidence kinds.

**Leak 3 — edge-weight semantics (the deepest one).** `weight` on a graph edge means:
- LightRAG / PathRAG: an LLM-emitted relation weight, i.e. extraction confidence [code-verified]
- HippoRAG 2: **co-occurrence count** for fact edges, `1.0` for passage-membership edges, **cosine similarity** for synonymy edges — three incommensurable quantities collapsed into one weighted undirected view [code-verified]
- MS GraphRAG: combined degree / PMI in the NLP path [code-verified]
- Code graphs: unweighted, or call-site counts [code-verified schema]

Now wire a "PPR ranker" component — legitimately shareable between HippoRAG 2 and Fast-GraphRAG [code-verified: both use igraph personalized PageRank] — onto a LightRAG graph, whose nodes and edges have the same *shape*. It runs. It returns a ranked list. The numbers are meaningless, because random-walk mass is flowing along LLM confidence scores rather than co-occurrence counts. `recipe@version` compatibility checking cannot express "same node/edge shape, different weight semantics" — a version string is not a type.

And the mirror case: `degree-ranker@1.0`, shared by construction in the diagram's spirit, applied to a code graph. A utility function called 500 times has enormous degree and near-zero query relevance; degree ranking on call graphs is plausibly *anti*-correlated with relevance [inference — strong, and cheap to falsify in a spike]. Nothing in `List[ScoredNode] -> List[ScoredNode]` declares that this component's ranking signal presumes an entity-cooccurrence graph.

### Verdict on the claim

**The vocabulary is neutral. The interpretation is not.** "Seeds" and "evidence" are honest as *names* and euphemistic wherever a downstream component reasons about *why* an item scored what it scored — which is every ranker, every fuser, every whole-graph algorithm, and every assembler that renders by kind. Neutral names over non-neutral semantics is not modularity; it is a type system that accepts every wiring and validates none.

### Vulnerability

- **A — most damaged.** A's headline feature is "diff any slot output between two wirings." Across paradigms those outputs are not commensurable, so the diffs are confident nonsense. Honest restatement of A's win: **A can diff stages within one index-recipe family, not across paradigms** — which is a much smaller claim than the one in CANDIDATES.md.
- **B — survivable.** B permits a node to stay opaque and normalize only at declared boundaries, so a paradigm can keep its native type internally. B is the only candidate whose structure accommodates the typed-union fix without redesign.
- **C — no leak because no sharing.** C's evidence normalizer meets the same union problem exactly once, at the shallowest point. That is C's genuine, under-credited virtue.
- **D — kernel inherits B's exposure, plus a structural flaw CANDIDATES.md omits:** the rig compares kernel parts deeply and sandbox parts shallowly, so any *cross-regime* metric is defined at the shallowest common denominator. **The promotion decision — "is porting this worth it?" — is therefore always made on the least informative evidence the system produces.**

### Fix

1. **`ScoredItem`** replaces `ScoredNode`: `{ref: Ref, kind: ItemKind, score: Score, provenance: recipe@version, payload: opaque}`.
2. **`Score = {value, semantics, space_id?}`** with `semantics ∈ {cosine_similarity, rank_reciprocal, probability_mass, stationary_probability, bm25, count, llm_grade, path_reliability}`. Generic transformers declare which semantics they accept: RRF accepts any (rank-only); range-normalizing fusion accepts only matching semantics. One field kills a whole bug family.
3. **`ItemKind` is an open registry declared by the recipe**, and evidence is a union, not a node — restore SYNTHESIS's typed union into the candidate contracts.
4. **Whole-graph-algorithm components declare `requires_edge_weight_semantics`**; recipes declare what they wrote; wiring validation compares. This is the specific clause that stops PPR-on-LightRAG-weights, and it is the highest-value single line in this document.
5. **Rankers declare their presumed graph semantics** (`presumes_graph: entity_cooccurrence | citation | call_graph | hierarchy | none`), so `degree-ranker` is refused on a call graph at wire time.

---

## Attack 5 — Shared-component version conflicts: fork (registry sprawl) or config (config explosion)?

Two modalities want different behavior from `assembler@2.2`. Per Attack 3's table, the real demand spans: 1-prompt vs N-prompt, sectioned vs flat, best-last vs best-first ordering, text vs multimodal, budgeted vs unbudgeted, table-rendered vs passage-rendered.

### The fork path and its actual failure

`assembler-tables@2.2`, `assembler-paths@1.0`, `assembler-passages@1.0`, `assembler-mapreduce@1.0`, `assembler-greedy@1.0`, `assembler-multimodal@1.0`, `assembler-whole-corpus@1.0`. Seven components, each re-implementing token budgeting, ref resolution, and block ordering.

Then the Attack-1 tokenizer fix lands. It must land seven times. It will land five times. The two stragglers now differ from their siblings in a way the version graph **cannot express**: lineage records parent-of-a-branch, and seven sibling forks needing one shared patch have no representation in a tree. Worse, the rig will faithfully measure the missing fix as a quality difference between wirings and attribute it to whatever else changed. **Registry sprawl's real cost is not count; it is that shared defects become unrepresentable in the lineage model.**

### The config path and its actual failure

`assembler@2.2` with `{mode, sections, order, budget, multimodal, batch}`. Now the config surface *is* the contract, and it is untyped. But the sharper problem:

Goal 7 states "a version is immutable once referenced." The config lives in the wiring, not the version. **Two wirings using `assembler@2.2` with different configs are two different behaviors under one identity.** The trace records `assembler@2.2` for both. The A/B diff is invisible. **Configuration is an unversioned back door straight through the immutability guarantee that goal 7 is built on.**

It compounds with goal 8. Self-improvement mutates components; if behavior lives in config, mutation mutates config; config is not a versioned artifact, so lineage is lost and "rollback is re-pinning" does not restore it. **The specified rollback mechanism is incomplete.**

### Vulnerability

- **A — forced onto the fork path.** A slot has one signature, so N behaviors mean N components. A's registry sprawls fastest, and its "maximal artifact sharing" claim erodes in proportion. A also *cannot express map-reduce assembly at all*: one ASSEMBLE slot producing N prompts consumed by N GENERATE calls plus a reduce is a fan-out graph, not a slot.
- **B — best positioned.** A subgraph can stand in for a node, so map-reduce is native fan-out; and B's graph spec is the natural place to freeze a config into a pinned instance.
- **C — the worst long-run position.** N engines, N packers, N copies of every shared defect, and no mechanism to ever fix one once.
- **D — pays both.** The same defect exists in two regimes with two independent fixes, forever.

### Fix

1. **Configuration is part of component identity.** A wiring pins a `ComponentInstance = (name@version, frozen_config_hash, resolved_dependency_ids)`, and **the instance hash — not the name — is what traces, lineage, and A/B results record.** Lineage reads `assembler@2.2[cfg:ab12] ← assembler@2.2[cfg:default], change: order=best_last`. One clause, and the entire back door closes.
2. **Share the service, not the component.** Token budgeting, ref resolution, and block packing move into a machine service `machine.pack(...)`. The seven variants become seven ~30-line policy components over one centrally fixable packer. The rubric currently has no notion of machine-provided *pure services* beyond stores and clients — that is the gap this exploits, and filling it is the cheap answer to the fork-vs-config dilemma. Neither horn: fork the policy, share the mechanism.
3. **Assembly returns `List[ContextPackage]`** (from Attack 3), making map-reduce expressible without a special component.

---

## Attack 6 — Stress-testing `List[ScoredNode] -> List[ScoredNode]`

The claim [SYNTHESIS §4, VECTOR-TREE §6]: one signature unifies rerank, fusion, window-replacement, and auto-merge.

### Stress 1 — reranking needs the query, and "the query" is not one thing

A cross-encoder reranker is `rerank(query, docs) -> scores` [code-verified]. The signature has no query, so the query arrives via closure or an ambient context object. Once it does, the transformer is no longer a pure function of the candidate set — which silently voids Candidate A's stage-diffing premise, because a stage's output now depends on hidden state the diff cannot see.

And "the query" is itself variable across the survey [all code-verified]:
- HippoRAG 2's fact filter is a **DSPy-optimized LLM call** needing the natural-language question.
- FLARE's retrieval query is the **look-ahead sentence with low-confidence tokens masked out** — generated mid-answer, not the user's question.
- IRCoT's query source is configurable: `original_question | last_answer | question_or_last_generated_sentence`.
- CRAG's grader consumes a query plus an evaluator model; the LangGraph reimplementation substitutes grader LLM calls for logprobs.

**Fix:** `transform(ctx: RetrievalContext, items) -> items`, with `RetrievalContext = {query_text, query_vectors?, turn_index, prior_answer?, session_id?, budget_remaining}`. Query text *and* embedding both required — VECTOR-TREE §3 already established that a contract handing retrievers only an embedding cannot host BM25 [code-verified].

### Stress 2 — dedup needs embeddings, and there is no primitive to read them

Semantic dedup needs either stored vectors or a re-embed call. The vector primitives named anywhere in the research are `upsert`, `search(top_k)`, `score_all`, `knn`, `multivector_search` — **there is no `get_vectors(ids)`**. Dedup, MMR diversification, and any cross-part score comparison all need it. That is a concrete, cheap, currently-missing primitive.

Dedup is also not one operation. It is at least three with different requirements: exact-ref identity; semantic near-duplicate (needs vectors + a threshold, hence a `space_id`, hence Attack 2); and hierarchical subsumption — auto-merging replaces retrieved children with their parent when `retrieved_children / total_children > 0.5` [code-verified]. Calling all three "dedup" in one slot is the same euphemism as Attack 4.

### Stress 3 — merge needs KV access, loops internally, and violates goal 10

`AutoMergingRetriever` [code-verified]: groups hits by `parent_node.node_id`, calls `storage_context.docstore.get_document(parent_id)` **inside the transformer**, and loops `while is_changed` because merges cascade up multiple hierarchy levels. So the transformer (a) performs store I/O, (b) runs its own loop, and (c) changes the cardinality *and the kind* of the candidate set.

Goal 10 states "the machine meters and can halt any component; no component owns its own loop limits." **Auto-merge owns one, and it is [code-verified] in a modality already in scope.** Either the machine can meter inside a component — which requires a step/yield protocol nothing in the candidates provides — or goal 10 is already violated by a surveyed part. In Candidate A this is terminal: a slot is a single call, so auto-merge is either unmetered or unhostable. Add it to A's "loses" column alongside loops and branches.

### Stress 4 — the signature cannot shrink to zero refs or grow to N prompts

MS-global's map stage emits **LLM-authored scored points** [code-verified] — evidence with no corpus ref. Under Attack 1's rule (every item resolves), that either fails validation or needs an explicit `derived` item kind carrying `derived_from: [Ref]`. Without it, global-mode answers lose their citation chain entirely, which breaks Sourcerer's reference rendering [inference] and makes global-mode answers unauditable.

### Verdict

The signature describes a **family**, not a slot. It is real only with its manifest:

```
transform(ctx: RetrievalContext, items: List[ScoredItem]) -> List[ScoredItem]
manifest:
  accepts_kinds / emits_kinds
  accepts_score_semantics / emits_score_semantics
  effects: [reads_kv, reads_vector, reads_graph, calls_llm, calls_rerank]
  iterative: bool          # iterative transformers are fixpoint NODES in the wiring, machine-budgeted
  space_id: <id | any>
  presumes_graph: <semantics | none>
```

Without those fields the signature accepts every wiring and validates none. **A signature that accepts everything checks nothing** — and `effects` is load-bearing beyond typing: codebase-memory-mcp requires *zero* machine primitives and has no LLM anywhere [code-verified], so an LLM-requiring transformer wired into a cbm-hosted part must be refused at wire time, not discovered at runtime.

---

## Cross-cutting finding — the missing machine service

Every fix above reduces to the same shape: *declare X, and refuse the wiring when X mismatches.* None of the four candidates names a component that performs the refusal.

- **A** has fixed slots — an implicit shape check only, and shape is exactly what these attacks pass.
- **B** has a graph spec in JSON/DSL; nothing states it is typechecked before execution.
- **C** has a broker that "reads manifests, routes, and meters" — capability *matching*, which is not compatibility *checking*.
- **D** inherits all three gaps and adds a cross-regime one.

**The load-bearing missing piece across all four candidates is a wiring validator: a machine service that runs before execution and can fail a wiring closed.** Without it, every manifest field in this document is documentation, and documentation does not prevent the silent failures — every single narrative above produces a plausible answer with a normal-looking trace.

The rig has a matching obligation: a run record must carry `refs_in/refs_resolved`, every `space_id` touched, every `counted_by`, and component **instance** hashes. Otherwise A/B results are not attributable, and goal 7's central promise — "a quality regression is attributable to a version diff" — is false in exactly the cases that matter.

---

## Scorecard — vulnerability by attack

Severity: ●●● structural (needs a design change), ●● serious (needs a contract clause), ● contained.

| Attack | A Stage Bus | B Conductor | C Federation | D Kernel+Sandbox |
|---|---|---|---|---|
| 1a Tokenizer / token budgets | ●●● diffs symptom, not cause | ●●● loops amplify | ●● measurement axis corrupted | ●●● corrupts promotion decisions |
| 1b Chunk-ID identity | ●●● plain dicts, no ID typing | ●●● amplified per iteration | ● engines own their IDs | ●●● port is where positional IDs survive |
| 2 Embedding space | ●●● sharing breaks on recipe branch | ●●● same | ● own embedder, honest | ●●● promotion = full re-index, unstated |
| 3 Prompt format | ●●● `str` passes "plain data" | ●●● splicing is string surgery | ● engine owns prompt end-to-end | ●●● ports misread as kernel regressions |
| 4 Ontology leakage | ●●● cross-paradigm diffs are nonsense | ●● opaque nodes survive it | ● one shallow normalization point | ●●● cross-regime metric = shallowest |
| 5 Fork vs config | ●●● forced to fork; no map-reduce | ● graph pins instances natively | ●●● N copies of every fix, forever | ●● two regimes, two fixes |
| 6 Transformer signature | ●●● auto-merge unhostable or unmetered | ●● fixpoint nodes are native | ● internal to engines | ●● kernel only |

### What this lens changes about the prior

CANDIDATES.md's honest prior — B and D are the only candidates consistent with the versioning mandate — **survives, with two corrections**:

1. **B's advantage over A is conditional, not inherent.** With opaque strings, untyped scores, and unpinned configs, B is *worse* than A, because loops and splices amplify every coupling above. B wins only if the five clauses below are contract, not aspiration.
2. **C is more honest than credited, and A less.** C has no fake modularity to break; its weakness is that a shared defect can never be fixed once. A's "diff any stage" is real only within one index-recipe family, and A cannot host auto-merge, map-reduce assembly, or any iterative transformer — three [code-verified] surveyed behaviors, on top of the loops/branches it already concedes.
3. **D carries an unstated structural cost**: cross-regime comparison collapses to the shallowest denominator, so the promotion decision runs on the weakest evidence the machine has. That should be added to D's "loses" list before scoring.

---

## The five contract clauses most load-bearing for real modularity

**1. Declarations are preconditions the machine enforces, not documentation.**
A wiring validator runs before execution and fails closed on any unsatisfied declaration. Every other clause here is inert without it — and every failure narrative in this document produces a plausible answer and a normal trace, so runtime discovery is not an option.

**2. Identity closes over the whole closure: `ComponentInstance = (name@version, frozen_config_hash, resolved_dependency_ids)`.**
Traces, lineage, and A/B results record the *instance* hash, never the bare name. This closes the unversioned-config back door through goal 7's immutability rule, makes rollback-by-re-pinning complete, and makes a "shared component" honest — sharing a name while injecting a different encoder is not sharing.

**3. Refs are machine-minted, carry recipe provenance, and must resolve loudly.**
`ChunkRef = (corpus_id, recipe@version, ordinal, content_hash)`; positional indices are part-local projections with an auditable bijection; `deref` raises on unknown; an assembler may not emit unresolved refs; derived evidence carries `derived_from`; every run records `refs_in / refs_resolved` and the rig fails runs where they differ. This converts the worst failure in the system — a confident sourceless answer — from silent to loud.

**4. Interpretation travels with the value.**
`ScoredItem` carries `kind` (open registry, an evidence *union*, not a node) and `Score = {value, semantics, space_id?}`. Vector namespaces are stamped immutably with an `EmbeddingSpace` id; absolute thresholds are space-bound. Graph edges declare weight semantics, and whole-graph algorithms declare which semantics they require. Generic transformers declare `accepts/emits kinds`, `accepts/emits semantics`, `effects[]`, `iterative`, and `presumes_graph`. This is the clause that stops PPR on LLM-confidence weights, range-normalizing fusion across incommensurable scores, degree ranking on call graphs, and cross-space seeding — four silent failures with one mechanism.

**5. The prompt boundary is structured, and counting belongs to the machine.**
Assemblers emit `List[ContextPackage]` of typed blocks with declared ordering; generators declare `requires_block_kinds` and may pin model/client capabilities (`logprobs`, `prefix_continuation`, `prompt_cache`); rendering happens once in a machine-owned renderer so harnesses splice blocks and never text; token counting is a machine service that counts with the *consuming* model's tokenizer and stamps every number with `counted_by`. This kills format coupling, makes map-reduce and multimodal assembly expressible, and makes the rig's token axis a comparable quantity.

---

## What would falsify this critique

- A spike showing `List[ScoredNode]` with a `kind` tag alone (no score semantics) suffices for cross-paradigm fusion without measurable degradation → clause 4 shrinks.
- A spike showing an assembler that renders to string and a harness that splices by a *stable, versioned* delimiter contract survives three assembler revs → clause 5 weakens to a naming convention.
- Evidence that no two wirings in practice ever share a component across index recipes → most of Attacks 2 and 4 become theoretical, and Candidate C's position strengthens sharply.
- A demonstration that positional-index parts (Fast-GraphRAG csr, RAPTOR ints) can be hosted without a bijection audit → clause 3 shrinks to content-hash refs only.

---
*Red team pass, modularity/hidden-coupling lens. Drafted 2026-08-10 against CANDIDATES.md, SYNTHESIS.md, ARCHITECTURE-RUBRIC.md, GOALS.md, PROJECT.md and the four MODALITIES-*.md research passes. Not committed.*
