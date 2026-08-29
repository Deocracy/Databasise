# GAP-SWEEP — Consolidated Missing-RAG-Types Map

Consolidates three parallel sweeps — [gap-1-retrieval-techniques.md](.planning/research/gap-1-retrieval-techniques.md) (19 techniques), [gap-2-data-modalities.md](.planning/research/gap-2-data-modalities.md) (12 modalities), [gap-3-meta-control.md](.planning/research/gap-3-meta-control.md) (13 meta/control families) — against the 24-system survey distilled in [SYNTHESIS.md](.planning/research/SYNTHESIS.md) and the four candidates in [CANDIDATES.md](.planning/architectures/CANDIDATES.md).

**45 unique new types** after deduplication (Speculative RAG, DRIFT, LazyGraphRAG and RARR each appeared in two sweeps).

**Evidence standard.** Nothing here is [code-verified] — the sweeps were WebSearch-only. Types carry the strongest tag their sweep earned: [docs-verified] (official vendor/repo docs read directly), [paper-claim] (abstract or paper, unread code), [paper-claim, aggregate] (no single authoritative source). Every *fitting-impact verdict* in §2–§4 is **[inference]** — this document's own analysis, not a sourced claim. No benchmark number anywhere below is a decision input (PROJECT.md constraint); numbers were dropped in consolidation precisely because they cannot settle anything.

---

## 1. The RAG-it-any-and-every-way map

Eight axes. A real system is a point in *all eight* simultaneously — LightRAG is (no query transform) × (LLM-extracted graph recipe) × (entity-seed + one-hop) × (linear) × (text docs) × (concatenate-and-generate) × (no meta layer) × (knowledge in stores). The tree is a coordinate system, not a partition; that is why "how many RAG types are there" has no answer and "which axis does this type move on" always does.

Legend: `✓` in the 24-system survey · `+` newly found this sweep (with ID for §2) · `⊘` newly found and recommended out of scope.

### A. Query transformation — what happens to the question before retrieval
- **None** — query used verbatim `✓` (LightRAG, vanilla, BM25)
- **Semantic rewrite**
  - HyDE — embed a hypothetical answer document `+N1` [paper-claim]
  - Step-back prompting — abstract the question first `+N4` [paper-claim]
- **Multiplication**
  - RAG-Fusion — N reformulations + Reciprocal Rank Fusion `+N2` [paper-claim]
  - RQ-RAG — learned per-turn choice of rewrite/decompose/disambiguate `+N3` [paper-claim]
- **Decomposition into structure**
  - IRCoT — interleave reasoning steps with retrieval `✓`
  - Plan-RAG / Plan\*RAG / TreeRare — LLM emits a sub-query **DAG or tree at query time** `+N5` [paper-claim]
- **Routing instead of transforming**
  - Agentic routers `✓`
  - Adaptive-RAG — complexity classifier picks no-/single-/multi-step `+N6` [paper-claim]
  - Self-Route / Route-Before-Retrieve — RAG vs long-context-dump `+N7` [paper-claim]

### B. Index recipe — what gets built, and by what
- **LLM-extracted graph** — entity/relation `✓` (LightRAG, MS GraphRAG, Fast-GraphRAG, nano-graphrag), phrase/passage `✓` (HippoRAG 2)
- **LLM-summarized hierarchy** — RAPTOR tree (KV + ANN, not a graph) `✓`
- **LLM-augmented chunks**
  - Contextual Retrieval — situating blurb prepended per chunk, into both vector and BM25 `+N8` [docs-verified]
- **Parse-derived graph (zero LLM calls)** — the recipe fork the survey never saw
  - PKM / wikilink vault — link graph is author-declared `+N11` [docs-verified, plugin listings only]
  - Citation graph — edges from reference lists `+N12` [paper-claim]
  - Symbol graph — code `✓` (code-graph-rag, codebase-memory-mcp) *(survey member; belongs to this fork)*
- **Statistical-only index, extraction deferred to query time**
  - LazyGraphRAG — noun-phrase + co-occurrence communities at index time `+N10` [paper-claim, vendor eval]
- **Structure-preserving recipes**
  - Hierarchy-aware legal/medical — sub-document position path for pinpoint citation `+N13` [paper-claim]
  - KAG mutual index — bidirectional entity↔chunk pointers `+N14` [paper-claim]
- **Embedding-order inversions**
  - Late chunking — encode whole doc, apply chunk boundaries *after*, mean-pool spans `+N9` [docs-verified]
- **No index at all** — CAG (whole corpus into a cached prompt) `✓`

### C. Retrieval mechanism — how candidates are found
- **Dense vector** `✓` · **Lexical/BM25 + hybrid** `✓` · **Multi-vector late interaction** `✓` (ColBERT, ColPali)
- **Learned sparse** — SPLADE, MLM-head term expansion into an inverted index `+N15` [paper-claim]
- **Unified multi-representation** — BGE-M3, one forward pass → dense + sparse + multi-vector `+N16` [docs-verified]
- **Truncatable** — Matryoshka, coarse pass at low dim then full-dim rerank `+N17` [paper-claim]
- **Graph traversal** — one-hop `✓`, PPR `✓`, path-DFS `✓` (PathRAG), agent walk `✓` (GraphReader), community map-reduce `✓` (MS GraphRAG)
  - DRIFT — global seed → LLM-spawned local follow-ups → merge `+N21` [docs-verified]
  - Hypergraph — higher-order (n-ary) relations `+N18` [paper-claim]
- **Formal query generation** — text-to-SQL `✓`
  - Text-to-SPARQL / KGQA over a schema'd triple store `+N19` [paper-claim, aggregate]
  - Geospatial predicates — bbox/radius/polygon/route-buffer fused with semantic `+N23` [paper-claim]
- **Ensemble of retrievers**
  - MoR / MixRAG / Retriever Portfolios — learned per-query weighting or expert selection `+N20` [paper-claim]
- **Live external** — web search at query time, freshness as a scored property `+N22` [industry-claim, lowest confidence in sweep]
- **Pass-through** — return everything, bounded by context window (the long-context fallback of `+N7`)

### D. Control flow — the harness tier
- **Linear** `✓` · **Grade-and-correct loop** `✓` (CRAG, Self-RAG) · **Generation-triggered** `✓` (FLARE) · **Interleaved reasoning** `✓` (IRCoT) · **Stacked harnesses** `✓` (Self-CRAG)
- **Fan-out / join (map-reduce over branches)** — *the shape none of the four candidates draw*
  - Self-consistency / multi-sample vote `+N24` [paper-claim]
  - Speculative RAG — drafters over document subsets + verifier `+N25` [paper-claim]
- **Post-hoc verification loops** — loop key is the *answer*, not the query
  - Chain-of-Verification / RARR / RAGAR — decompose answer into claims, re-retrieve per claim `+N26` [paper-claim]
  - Attributed QA / ALCE — citation-first generation, entailment-scored `+N30` [paper-claim]
- **Multi-agent deliberation**
  - MADAM-RAG / MAIN-RAG / courtroom P-RAG — advocate/judge/aggregator over rounds `+N27` [paper-claim]
- **Inline quality gating**
  - RAGAS / ARES run online per request, gating or logging `+N28` [paper-claim]
- **Safety rails** — input / retrieval / output rails, tiered classifier sizes `+N29` [paper-claim, product docs]

### E. Data modality and source
- **Text documents** `✓` · **Code repos** `✓` · **PDF-as-image** `✓` (ColPali) · **Tables** `✓` (text-to-SQL) · **Mixed media** `✓` (RAG-Anything) · **Event streams → temporal graph** `✓` (Graphiti)
- **Video** — frame/clip evidence, LVLM generation, frame-selection `+N34` [paper-claim, code "release soon"]
- **Audio/speech** — transcription-free audio-native retrieval `+N35` [paper-claim]
- **Time-series** — retrieve similar historical segments to condition a forecast `+N36` [paper-claim]
- **Geospatial** — spatial DB + predicates `+N23` (also C) [paper-claim]
- **Personal linked notes / vault** `+N11` (also B) [docs-verified]
- **Conversation history as corpus** — MemoryOS, DH-RAG, CALMem `+N37` [paper-claim]
- **Live stream with standing index** — incremental upsert under a memory budget `+N38` [paper-claim]
- **User interaction history → item recommendation** — K-RagRec, KERAG_R `+N39` [paper-claim]
- **Scientific literature + citation graph** `+N12` (also B) [paper-claim]
- **Regulated corpora with authority hierarchy** `+N13` (also B) [paper-claim]

### F. Generation integration — how evidence reaches the model
- **Concatenate into prompt** `✓` (everything surveyed)
- **Encode-separately, fuse-in-decoder** — FiD `+N32` [paper-claim, aggregate]
- **Ensemble output distributions across parallel calls** — REPLUG `+N31` [paper-claim]
- **Reuse attention state across calls** — RAGCache / TurboRAG KV-cache reuse `+N33` [paper-claim]
- **Non-text answer** — numeric forecast `+N36` [paper-claim]

### G. Meta layer — what improves the system
- **Nothing** `✓` (all 24 surveyed)
- **Selection** — router picks part/harness per query `✓`, `+N6`, `+N20`
- **Comparison** — the rig this project mandates (goal 4)
- **Gradient training of the policy** — Search-R1, R1-Searcher, DeepRetrieval, ZeroSearch `⊘N43` [paper-claim]

### H. Where knowledge lives — the load-bearing axis
- **Machine-owned stores** `✓` — everything surveyed except CAG
- **Prompt/context cache** `✓` (CAG) — traceable, machine-readable
- **Part-owned opaque storage** `✓` (codebase-memory-mcp, ColBERT/PLAID dirs) — the declared black-box extreme
- **Model weights** — no machine-readable artifact at all
  - DSI / Differentiable Search Index — corpus memorized, docids generated `⊘N40` [paper-claim, aggregate]
  - ROME / MEMIT knowledge editing `⊘N41` [paper-claim]
  - RAFT — tuned reader, retrieval intact `⊘N42` [paper-claim]
  - RL-trained retrieval policy `⊘N43` [paper-claim]
  - REALM / RETRO / Atlas — retrieval fused into pretraining `⊘N44` [paper-claim, aggregate]
- **Distributed across silos** — federated/privacy-preserving RAG `⊘N45` [paper-claim]

**Reading of the map:** axes A–G are all *orchestration* — the fitting's home turf. Axis H is the only one that asks a different question ("what is an index?"), and it is exactly where the recommended out-of-scope line falls. That is a clean, defensible boundary rather than an arbitrary one.

---

## 2. Verdicts — every newly found type

Verdict vocabulary: **YES** (expressible now — the wiring is named) · **YES\*** (expressible, but only in a declared-graph engine, and requires fan-out/join to be a *named* executor primitive) · **CAP** (needs a new declared capability or manifest field — named) · **STORE-SUB** (needs a new sub-capability on an existing store — named; no new store type) · **CONTRACT** (needs a shape change to the query/evidence/answer contract) · **OUT** (recommended declared-out-of-scope, with reason).

All verdicts [inference].

### YES — wire it today

| ID | Type | Wiring |
|---|---|---|
| N1 | HyDE | `rewriter@v` (LLM role) → existing vector-seed; seed input already typed as text, not "the user's query" |
| N4 | Step-back | same as N1; both queries feed the seed set |
| N3 | RQ-RAG | conditional `rewriter` node with a self-loop — B/D only; corroborates the existing "A can't loop" finding |
| N6 | Adaptive-RAG | the `Selector` already in Shared Anatomy; only note = selector may be a small trained classifier, so keep the role model-agnostic |
| N8 | Contextual Retrieval | new index-recipe stage `context-enricher@v` between chunker and embedder/lexical writer; recipe already permits LLM stages |
| N12 | Citation-graph RAG | parse-derived graph recipe + existing graph `bulk-export` (PPR) — a recipe variant of an already-modeled paradigm |
| N17 | Matryoshka | coarse seed at low dim → rerank at full dim; declared client property `matryoshka.dims[]` |
| N21 | DRIFT | harness composing two already-surveyed wirings (community-global, entity-local) with an LLM decomposition step |
| N30 | Attributed QA (ALCE half) | assembler already carries provenance IDs; citation markers are generator output detail |
| N30 | RARR half | corrective harness (CRAG shape) with the grader targeting *citation support* instead of *sufficiency* |
| N28 | Eval-in-the-loop | grader node — but must fan **in** from two non-adjacent upstreams (pre-assembly evidence + generated answer); wiring, not a new primitive |
| N18 | Hypergraph | n-ary relations by reification (hyperedge becomes a node linking N members) on the existing graph store — modeling cost, not a store gap |
| N16 | BGE-M3 | one `encode()` → N declared output shapes, fanned into three store writes; manifest refinement on the embed client |
| N15 | SPLADE | existing lexical/inverted store with a learned encoder; embed manifest gains `output_shape: sparse\|dense` |
| N14 | KAG | router/planner harness + external-tool for numeric ops; the *mutual index* is an index-recipe requirement (see STORE-SUB) |
| N22 | Web-live | already covered by declared `external-resource`; needs the evidence `as_of` field (see CONTRACT). Document "retrieve-only, no index" as legal — the mirror image of CAG's "index-only, no retrieve" |

### YES\* — declared-graph only, and fan-out/join must be named

| ID | Type | Shape |
|---|---|---|
| N2 | RAG-Fusion | fan-out per query variant → **multi-list** fusion ranker `List[List[ScoredNode]] -> List[ScoredNode]` keyed on *rank*, not score |
| N25 | Speculative RAG | document-clustering component → generator fan-out under `drafter`/`verifier` roles → `List[Draft] -> Draft` selector |
| N24 | Self-consistency | `map(pipeline, N) → reduce(vote)` at *whole-pipeline* level, not just node level |
| N20 | Mixture-of-retrievers | N parallel retrievers → learned fusion ranker; also needs checkpoint-bearing component identity (see CAP) |

Candidate A (Stage Bus) cannot express any of these four. Candidate C expresses them only if a single engine already implements them internally.

### CAP — new declared capability or manifest field (named)

| ID | Type | Capability to declare |
|---|---|---|
| N37, N38, N39 | Chat memory / streaming / recommendation | **`self-ingesting`** — the corpus grows as a side effect of answering. Three independent sightings; declare once, not three times. |
| N10 | LazyGraphRAG | **`deferred-extraction`** — LLM extraction is a *query-wiring* component for this part. Machine must nowhere hardcode "extraction is index-side". |
| N11, N12 | PKM vault, citation graph | **`parse-derived-graph`** — an index recipe with zero LLM calls; edges arrive at parse time. Makes cost model and recipe compatibility honest. |
| N7 | Long-context routing | **`pass-through-retrieve`** — `retrieve()` returns the corpus unranked, bounded by target context window. A legal manifest edge, currently undocumented. |
| N9 | Late chunking | **`encode-tokens`** client capability (per-token embeddings for a whole doc) + new component `chunk-pooler`. Breaks chunker→embedder independence. |
| N31 | REPLUG | **`cross-call-logprob-merge`** — merging raw next-token distributions across parallel `generate()` calls; a step beyond the existing single-call logprobs declaration |
| N33 | KV-cache reuse | **`prefix-cache-aware`** client flag + assembler manifest flag **`order_stable`** — rerank-then-assemble silently defeats cache reuse; invisible until hit rates are ~0 |
| N29 | Guardrails | **`classify-lite`** client role — tiny non-LLM classifier run per chunk; costing it as an LLM role misrepresents it, the way embed/rerank are already split out |
| N35 | Audio RAG | **`encode-audio`** client role. (`audio-LM` speech-in/speech-out: named but **deferred**, not excluded — only needed if voice UX becomes a Sourcerer goal.) |
| N13 | Legal/medical | **`hierarchy_aware`** chunker flag (preserves document > title > § > subsection path) |
| N20, N43 | Trained routers/policies | **`checkpoint`** in version identity — `name@version` must be able to pin a model-checkpoint hash alongside code/prompts, even though the machine never trains one |
| N27 | Multi-agent debate | role-roster additions (`advocate`/`judge`/`aggregator`), plus scratchpad + halting, below |
| N5 | Plan-then-retrieve | **`ephemeral-subgraph`** executor node — see §4.1; the sharpest capability gap in the sweep |

### STORE-SUB — new sub-capability on an existing store (no sixth store type)

| ID | Type | Sub-capability |
|---|---|---|
| N34, N35 | Video, audio | **blob: `addressable-subrange`** — timestamp or byte span addressing inside an opaque blob. One convention serves both ("temporal-span-over-blob") |
| N19 | Text-to-SPARQL | **graph: `formal-query-language`** — schema-validated query-string execution, a third mode alongside pointwise ops and bulk-export |
| N14 | KAG | **index recipe: `bidirectional-mutual-index`** — entity→chunk *and* chunk→entity; LightRAG-family graphs are one-directional |
| N27 | Debate | **KV: `run` scope, multi-writer** — a third scope alongside corpus-scoped chunks and session-scoped memory. Ephemeral, per-run, many writers. Reuse KV; do not invent a store type |

### CONTRACT — shape changes to query / evidence / answer

| ID | Type | Change |
|---|---|---|
| N23, N39, N36 | Geospatial, recommendation, time-series | **Query object, not query string** — `{text?, embedding?, predicates?, profile_ref?, formal_query?}`. Recommendation may have no text at all; lexical still needs verbatim text |
| N22, N13, + Graphiti | Web-live, legal/medical, temporal | **Evidence `metadata` bag** — one extensible dict rather than per-property plumbing. Reserved keys: `as_of`/`published_at`, `valid_at`/`invalid_at`, `authority_rank`, `hierarchy_path`, `span{start,end,unit}`, `blob_ref` |
| N34, N35, N36, N39 | Video, audio, time-series, recommendation | **Typed evidence payload** — `text \| blob-span \| numeric-window \| item-ref` |
| N36 | Time-series | **Typed answer** — `generate()` output declared per part (`text \| numeric-array \| ranked-items`). Only modality in 45 that stretches *answer* shape rather than query or evidence shape |
| N26 | Chain-of-Verification | **Per-sub-claim provenance** — trace records claim → verification-query → evidence chains, one level below today's per-query trace |
| N26 | Chain-of-Verification | **New primitive part type `claim-extractor`** — splits generated text into atomic verifiable statements, each becoming a new query. Grader/filter does not cover it (grading scores existing evidence; this *generates queries from output*) |

### OUT — recommended declared-out-of-scope

| ID | Type | Reason |
|---|---|---|
| N40 | DSI / generative retrieval | `ingest()` is a fine-tuning job; the "index" is model parameters with **no machine-readable artifact**. Worse than CAG for our goals — CAG at least keeps a traceable prompt. Sharpest single violation found. |
| N41 | ROME / MEMIT editing | Needs weight-write access *and* a model-serving tier the machine would have to own. Literature itself frames this as RAG's alternative, not a variant. |
| N42 | RAFT | Query side intact; the *recipe output* is a checkpoint/LoRA adapter. Out under the same exclusion, but note it is the **cheapest re-entry point** if the exclusion is ever revisited (adapter deltas + a job runner, not full weights). |
| N43 | RL retrieval policies | Out under the same exclusion — but the versioning model already fits it perfectly (a policy checkpoint is a `name@version` artifact; traces are the training signal; branch→A/B→promote is the loop). Only a **job runner** is missing. Good news framed as a gap. |
| N44 | REALM / RETRO / Atlas | Training-integrated retrieval; requires owning weights and a training loop. Categorically outside "part = orchestration over machine-owned clients". |
| N32 | FiD | Portable half (encode-separately, fuse-in-decoder) needs a multi-passage-encoding generation mode hosted LLM APIs do not expose. **Inference-API-infeasible, not merely contract-infeasible.** |
| N45 | Federated / privacy-preserving | Deployment topology *above* the fitting — N machines, each independently fitted, plus a cross-instance protocol. The unit of federation is the **machine instance**, so nothing in the component/part/harness vocabulary must change to leave the door open. |

**One exclusion covers six of seven:** N40–N44 all want **`model-weight-access`**. Declare it as a capability the fitting *chooses not to host*, named in the viability verdict, rather than a silent gap — three unrelated families arriving at the same request is a family boundary, not an oddity.

---

## 3. Delta list — the actionable additions

Everything the fitting contract and Shared Anatomy need. Grouped by artifact to edit.

### 3.1 Part manifest — new declared capabilities (6)
1. `self-ingesting` — writes corpus during `answer()`; implies the rig must snapshot/freeze the corpus for A/B, and implies (3.7) a standing-corpus budget
2. `deferred-extraction` — LLM extraction runs query-side; forbids hardcoding extraction as index-side anywhere in the machine
3. `parse-derived-graph` — zero-LLM index recipe; edges available at parse time
4. `pass-through-retrieve` — `retrieve()` returns everything, bounded by target context capacity
5. `live-external-retrieval` — retrieve-only, no index (instance of existing `external-resource`; document the shape, do not add a name if `external-resource` suffices)
6. `model-weight-access` — **declared NOT hosted**; the named exclusion covering N40–N44

### 3.2 Store sub-types / sub-capabilities (4) — **no sixth store type**
1. **blob**: `addressable-subrange` (timestamp or byte spans)
2. **graph**: `formal-query-language` (schema-validated SPARQL/Cypher-style execution) — third mode beside pointwise and bulk-export
3. **KV**: `run` scope with multi-writer semantics — third scope beside corpus and session
4. **recipe**: `bidirectional-mutual-index` (entity↔chunk both ways)

All 45 types fit the five existing stores. The **only** demanded sixth store — a weight/checkpoint store with a serving tier — belongs entirely to the out-of-scope family. That is the sweep's single most reassuring finding.

### 3.3 Ingest source types — extend `documents | repo | stream | nothing` (+3)
1. `vault` — a directory of interlinked documents whose **link structure is data, not something to infer**
2. `interaction-log` — conversation turns / user events arriving continuously (pairs with `self-ingesting`)
3. `live-only` — no ingest phase; evidence fetched per query. Distinct from `nothing` (CAG has a corpus, just no index)
4. *Rejected:* `facts/triples` — belongs to the excluded weight family

### 3.4 Evidence contract (4)
1. `metadata: dict` — one extensible bag; reserved keys `as_of`, `published_at`, `valid_at`, `invalid_at`, `authority_rank`, `hierarchy_path`, `span{start,end,unit}`, `blob_ref`
2. Typed payload: `text | blob-span | numeric-window | item-ref`
3. Per-sub-claim provenance chains (claim → verification query → evidence set)
4. Note: `valid_at/invalid_at` belongs on **evidence generally**, not only on graph edges — web freshness and Graphiti bi-temporality are the same field

### 3.5 Query and answer contracts (2)
1. Query becomes an **object**: `{text?, embedding?, predicates?, profile_ref?, formal_query?}` — text optional, not mandatory
2. `generate()` output type declared per part: `text | numeric-array | ranked-items`

### 3.6 API-client seam (roles + flags)
- New roles: `encode-tokens` (doc-level per-token embeddings), `encode-audio`, `classify-lite` (tiny non-LLM, per-chunk cost profile)
- New LLM role names: `drafter`, `verifier`, `judge`, `advocate`, `aggregator`, `planner`, `claim-extractor`
- New client flags: `output_shape: sparse|dense`, `multi_output_per_call`, `matryoshka.dims[]`, `prefix_cache_aware`, `cross_call_logprob_merge`
- Declared NOT hosted: `fine-tune` / `weight-write`. Deferred (named, unbuilt): `audio-LM` (speech-in/out)

### 3.7 Budget object — four extensions (goal 10)
1. Separate **`capacity`** (target model's context window) from **`spend`** (steps/tokens/time) — today's object conflates them; long-context routing needs capacity as a routing signal
2. **Multiplicative** accounting under fan-out — N branches, not one accumulating loop
3. **Convergence/consensus halting** — "sample until agreement, cap at max-N"; debate and adaptive self-consistency halt on agreement, not step count
4. **Standing-corpus budget + eviction policy** — index-level, store-owned, independent of any query. Genuinely new object; `BUD` in Shared Anatomy is described purely in query-time terms

### 3.8 Executor / wiring primitives (Candidates B and D)
1. **`fan-out / join`** named as a first-class node type alongside the documented loop-with-condition
2. **`ephemeral-subgraph`** — a planner-emitted runtime graph, explicitly distinguished from the versioned modality graph. The trace must record *the planner's version + the generated plan as data* so the run stays reconstructable
3. **Non-adjacent fan-in** — a node may read a sibling's output (eval component needs pre-assembly evidence *and* the final answer)

### 3.9 New primitive part types — the ~7 becomes ~10
1. `planner` — query → sub-query DAG/tree
2. `claim-extractor` — generated text → atomic claims → new queries
3. `chunk-pooler` — token embeddings + boundaries → chunk vectors
- Plus two signature variants of existing types (not new types): multi-list fusion ranker `List[List[ScoredNode]] -> List[ScoredNode]`; draft selector `List[Draft] -> Draft`
- `frame-selector` / `segment-selector` are **ranker variants over blob spans** — no new type

### 3.10 Component manifest flags (3)
1. `assembler.order_stable: bool` — prefix-cache viability
2. `chunker.hierarchy_aware: bool` — sub-document citation paths
3. `version.checkpoint: hash?` — a component's pinned identity may include a model checkpoint

### 3.11 Shared Anatomy diagram — concrete edits to CANDIDATES.md §0
- **STORES**: annotate `BLOB` "+ sub-range addressable"; annotate `KV` "scopes: corpus | session | run(multi-writer)"; annotate `GR` "pointwise | bulk-export | formal-query"
- **CLIENTS**: add `classify-lite`, `encode-tokens`, `encode-audio`; expand the LLM role list to name drafter/verifier/judge/planner
- **SERVICES**: rename `BUD` → "Budget enforcer (spend + capacity + standing corpus)"; add **`Corpus manager`** (snapshot/freeze for A/B, eviction under standing budget); add **`Job runner`** drawn as *declared-not-built*, so the weight-family exclusion is legible on the diagram rather than absent from it
- **PARTS**: the `PARTS --> STORES` arrow becomes bidirectional-at-query-time for parts declaring `self-ingesting`
- **New box**: an explicit "Not hosted: model-weight write / model-serving tier" boundary marker

---

## 4. The five stress tests — best paper-tests for the candidates

Chosen for *discrimination*, not novelty: each one is predicted to separate the four candidates rather than cost all four the same.

### 4.1 Plan\*RAG / TreeRare — the runtime-planned DAG `+N5`
**What it breaks:** an LLM emits a fresh sub-query DAG **per query**. Candidates B and D are built on "a modality *is* a declared graph of `name@version` nodes, branched and A/B'd" — goal 7's whole mechanism. A planner-emitted graph is a graph the machine executes that was never authored, versioned, or pinned. If the two lifecycles are conflated, every planned query silently becomes an untracked modality and goal 7's "the system as run yesterday is reconstructable" quietly fails.
**Paper-test:** *Can this candidate execute an LLM-generated graph while keeping the run reproducible?* The passing answer is a lifecycle split — versioned wirings vs ephemeral plans — where the plan is recorded **as trace data** and the *planner* is the versioned artifact.
**Prediction:** A cannot express it at all. B and D pass only by adding the split (3.8.2) — this is the cheapest test that forces the distinction into the open. C hosts it free but learns nothing (the plan is inside the engine).

### 4.2 LazyGraphRAG — extraction moved to query time `+N10`
**What it breaks:** SYNTHESIS §7 axis 2 treats extraction as *the* expensive, entangled, index-side stage, and spike 001 documents index-side-entangled / query-side-clean as a general finding. LazyGraphRAG deliberately inverts it: statistical index, LLM reasoning at query time. Any candidate whose rationale leans on that asymmetry has a counter-example.
**Paper-test:** *Does anything in this candidate hardcode "extraction is index-side"?* And: *can a part share the shared corpus feed while running zero LLM calls at index time?*
**Prediction:** A's fixed slot vocabulary is where the assumption would be frozen — the sharpest test of A's stated risk ("freezing today's paradigms into the machine"). D's kernel/sandbox split has to decide which regime an inverted-cost part belongs to.

### 4.3 The self-ingesting family — chat memory + streaming + recommendation `+N37/N38/N39`
**What it breaks:** goal 4's premise. Side-by-side truth assumes N parts on **one corpus**; these parts *change the corpus while answering*. Two parts A/B'd concurrently no longer share a baseline, and comparison stops meaning what it claims. Separately, it demands an index-level budget and eviction policy no candidate names — `BUD` is described entirely in per-query terms.
**Paper-test:** *What exactly does the comparison rig hold constant when a part writes during retrieval?* And: *who owns corpus eviction — the store, the machine, or the part?*
**Prediction:** this is the sweep's most under-modeled finding (three independent sightings, zero coverage) and the one that most stresses the **rig** rather than the executor — a dimension none of the four candidates were designed against.

### 4.4 Multi-agent debate — MADAM-RAG / P-RAG `+N27`
**What it breaks:** three things at once — fan-out/join (no candidate draws it), a per-run multi-writer scratchpad (a state category below session and above stateless call), and consensus-based halting (a budget shape that isn't steps/tokens/time).
**Paper-test:** *Can this candidate run N agents over R rounds against shared mutable per-run state, under a machine-enforced halt, and still trace who wrote what?*
**Prediction:** eliminates A outright. Tests whether B's executor is genuinely general or only loop-shaped. C hosts a debate engine trivially but yields answer-level comparison only — the clearest demonstration of C's ceiling.

### 4.5 Late chunking — Jina `+N9`
**What it breaks:** the index-recipe spine, `chunker@v → extractor@v → artifact`, which assumes chunking and embedding are independent and sequential. Late chunking encodes the whole document first and applies boundaries after. Since artifact-shareability (goal 6) is *defined* as "same or declared-compatible index recipe", a recipe whose stages don't compose in the assumed order attacks the sharing rule itself.
**Paper-test:** *Can the recipe model express a stage that runs before chunking and a component that consumes token-level output, without special-casing?* And: *does provenance still make compatibility checkable?*
**Prediction:** cheapest of the five to reason about on paper and the one where **C wins outright** (a whole engine does it internally, free) while A/B/D each pay a real extension — the sharpest single measurement of what normalization costs.

**Sixth, a boundary marker rather than a test: DSI `+N40` / the weight family.** Not a stress test, because the recommended answer is one line ("declared not hosted"). Its value is forcing the fitting to say *no* explicitly and name the capability it declines (`model-weight-access`), rather than discovering the gap during a build. Worth an explicit non-foreclosure note in PROJECT.md alongside late chunking.

---

## Provenance and caveats

- Zero [code-verified] claims in this sweep. The 24-system survey it extends had many; this does not. Nothing here should be treated as equal in weight to SYNTHESIS.md's findings.
- The three source sweeps were independent, which is why triple-sightings (write-on-query; fan-out/join; model-weight access) carry more signal than any single entry — three unconnected searches converging is the strongest evidence structure available at this evidence level.
- Re-verify any [paper-claim] against primary sources before a decision rests on it. `+N22` (web-live) is industry-blog-sourced and the weakest entry in the map; `+N34` (video) had a repo marked "release soon", so its architecture claims are abstract-level only.
- The delta list in §3 is the actionable output: 6 capabilities, 4 store sub-capabilities (**zero new store types**), 3 ingest source types, 4 evidence-contract additions, 2 query/answer contract changes, 3 new primitive part types, 3 executor primitives, 4 budget extensions, 3 manifest flags, and 6 named Shared Anatomy diagram edits.

---
*Drafted 2026-08-10. Consolidates gap-1/gap-2/gap-3. Not committed, per task instruction. Next: fold §3 into the fitting contract and CANDIDATES.md §0 before the red-team round; run §4's five tests against all four candidates.*
