# Lane 3 findings: Agent memory systems with multiple typed stores

Scope: every open-source memory layer and paper proposing typed memory (episodic,
semantic, procedural, structured vault), with attention to which stores exist, who
decides placement, small-model support, temporal validity, and SQL/relational stores.
Screened 45 candidates; 34 admitted (30 papers with PDFs in `papers/`, 8 code-only
systems admitted on their repositories as primary source — 4 papers overlap both, i.e.
MemGPT/Letta, A-MEM, Mem0, SimpleMem have a paper row and a code row), 4 refutes,
7 abstains. Full rows in `inventory.tsv`.

## (a) Admitted items

**MemGPT (2310.08560, Packer et al. 2023).** Virtual-context OS metaphor: a working
context window plus recall and archival stores, moved by explicit function calls the
model emits. Take: the function-call paging interface is the direct template for
MelodyScribe capability 2 (grammar-constrained filing operations). Careful: placement
is model-discretionary with no schema enforcement, and the archival store is flat text,
not typed. Code lives on as letta-ai/letta (24702 stars, Apache-2.0).

**Generative Agents (2304.03442, Park et al. 2023).** A memory stream scored by
recency, importance, and relevance, plus plan-act-reflect loops that write higher-level
reflections back. Take: the oldest working recipe for a background revise pass
(capability 4). Careful: one untyped stream, no placement decision, no temporal
validity. Note: the brief lists this title without an id; 2306.03609 is a wrong lookalike
(graph PDEs) — verified the correct id at the abs page.

**Reflexion (2303.11366, Shinn et al. 2023).** Verbal reinforcement: episodic traces of
self-critique kept in a fixed slot, reused without weight updates. Take: cheapest typed
episodic slot demonstrated; useful precedent for a Folio scratch type. Careful: single
slot, no retrieval over it, no store choice.

**A-MEM (2502.12110, Xu et al. 2025, NeurIPS 2025).** Zettelkasten-style memory notes
the agent links, merges, and evolves with no fixed schema. Take: closest existing
answer to "who decides placement" — the agent itself, continuously. agiresearch/A-mem
(1175 stars, MIT). Careful: links are free-form LLM judgments, so re-linking cost and
drift are unmeasured; no SQL store, no temporal fields.

**Mem0 (2504.19413, Chhikara et al. 2025).** Two-phase pipeline (extract facts, then
ADD/UPDATE/DELETE against stored memories) with a graph-store variant. Take: the
operation set is directly reusable for MelodyScribe filing ops; mem0ai/mem0 (65151
stars, Apache-2.0) is the most adopted memory layer found. Careful: extraction is a
separate LLM pass per turn, the opposite of the one-pass goal; graph variant adds
latency the paper does not hide.

**MemOS (2507.03724, Li et al. 2025).** MemCube units carrying type metadata, governed
by a MemScheduler lifecycle across parametric, activation, and plaintext stores.
Take: the only system with an explicit parametric store type, and the only scheduler
treating placement as a managed decision. MemTensor/MemOS (11287 stars, Apache-2.0).
Careful: ambitious and new; scheduler policies are heuristic, and the parametric path
is the least evaluated part.

**MIRIX (2507.07957, Wang et al. 2025).** Six-component modular memory (episodic,
semantic, procedural, and more) routed by a multi-agent controller. Take: richest
typed-store decomposition found; best reference for capability-to-store mapping
tables. Careful: multi-agent routing multiplies inference cost per write — tension
with the near-zero-cost hypothesis.

**Zep / Graphiti (2501.13956, Rasmussen et al. 2025).** Bi-temporal property graph:
every fact carries valid-time and ingested-time, so contradictions resolve by
supersession instead of deletion. Take: copy the temporal-validity model wholesale;
getzep/zep (4908 stars, Apache-2.0). Careful: graph-only; no vector/SQL coordination
story.

**MemoryBank (2305.10250, Zhong et al. 2023).** Dual-tower memory with an Ebbinghaus
forgetting curve plus a user-portrait updater. Take: only concrete, parameterized
eviction policy found in a deployed-style system. Careful: forgetting curve is fitted
to dialogue, not to factual stores; porting it to graph/SQL needs validation.

**HippoRAG (2405.14831, Gutierrez et al. 2024, NeurIPS 2024) and HippoRAG 2
(2502.14802, ICML 2025).** OpenIE triples plus Personalized PageRank over passage
nodes; v2 adds deeper passage integration and online LLM use, fixing the factual-memory
regression of graph-augmented RAG. Take: the standard triple-extraction-plus-graph
baseline every graph store must beat; OSU-NLP-Group/HippoRAG (3999 stars, MIT).
Careful: retrieval-only — no placement, no lifecycle, no SQL. Note: the brief's
"2502.14802" attribution is correct (verified: the abstract names HippoRAG 2); my
first truncated curl parse wrongly suggested otherwise.

**Memanto (2604.22085, Abtahi et al. 2026).** Typed semantic memory with
information-theoretic retrieval that skips LLM entity extraction and graph-schema
maintenance. Take: direct evidence that typed stores need not pay LLM extraction per
write — the key cost objection to capability 2 partially answered. Careful: newest and
least replicated; retrieval-quality claims need independent reruns.

**Is Agent Memory a Database? (2605.26252, Orogat et al. 2026).** Argues memory
systems localize correctness at records/embeddings/edges and fail on growth, semantic
revision, capacity-driven forgetting, and read-only access; demands revision and
transaction semantics. Take: strongest primary-source case for the SQLite-backed
relational piece of MelodyScribe. Careful: position paper with more requirements than
mechanism.

**Beyond Semantic Organization (2606.06090, Chen et al. 2026).** Retrieval should
reconstruct execution state, not semantic neighborhoods; mixing valid and erroneous
traces poisons decisions. Take: retrieval keyed on trajectory/state, not just
similarity — relevant to how Folios should be indexed. Careful: no released system
attached.

**Harness the Memory (2608.15008, Huang et al. 2026).** Controlled harness comparing
substrates: dense, sparse, text, structural, hierarchical, refinement-based,
parametric, activation. Take: the only head-to-head substrate comparison found; use
its harness design when benchmarking MelodyScribe stores against each other.
Careful: benchmark, not a system; numbers are regime-specific.

**Episodic-Semantic Scientific Agents (2605.17625, Milosevic 2026).** Dual-process
split of a 10-message episodic buffer from a semantic store under saturated context.
Take: minimal viable two-store split with a fixed, auditable boundary. Careful:
single-author, thin evaluation; relevance capped accordingly.

**MemTX (2607.23929, Li et al. 2026).** A memory write is not a belief commit: staged
transactional commit before writes become actionable premises. Take: the commit-gate
design transfers directly to Folio admission control. Careful: protocol paper; no
throughput or contention numbers.

**HAGE (2605.09942, Jiang et al. 2026).** Weighted multi-relational graph with
query-conditioned traversal replacing static binary edges. Take: edge-confidence
model for the revise pass (capability 4). Careful: RL-driven weights need reward
signal design that the paper tunes per benchmark.

**eMEM (2606.03374, Rasheed et al. 2026).** Multi-index embodied memory: SQLite for
structured storage plus hnswlib semantic search plus space-time keys. Take: the only
system found explicitly pairing SQLite with a vector index — an existence proof for
the Databasise pairing. Careful: embodied/spatial framing; text-heavy generalization
unshown.

**REMem (2602.13530, Shu et al. 2026, ICLR 2026).** Offline hybrid graph of time-aware
gists and facts plus an online agentic retriever with tools; formalizes the
episodicity gap. Take: cleanest split of background consolidation from online
retrieval found. Careful: benchmarkDirective; engineering detail on the offline
pipeline is thin.

**SimpleMem (2601.02553, Liu et al. 2026).** Three-stage semantic structured
compression with intent-aware retrieval planning; aiming-lab/SimpleMem (3754 stars,
MIT). Take: compression-first pipeline relevant to keeping the revise pass cheap.
Careful: "30x token reduction" is a vendor-style claim inside an academic paper —
treat as reported, not independently verified.

**Omni-SimpleMem (2604.01007, Liu et al. 2026).** Autonomous research pipeline that
discovered memory architectures; bug fixes and architecture changes each beat all
hyperparameter tuning combined. Take: evidence that memory-system design transfers to
automated search. Careful: meta-result, thin on typed-store detail.

**MemInsight (2503.21760, Salama et al. 2025).** Autonomous augmentation enriching
stored interactions for later retrieval. Take: precedent for augmentation-during-revise
rather than rewrite-during-revise. Careful: gains reported on recommendation and
retrieval recall, not on multi-store placement.

**LightMem (2604.07798, Zhang et al. 2026, ACL 2026).** STM/MTM/LTM tiers with small
language models driving retrieval, writing, and offline consolidation. Take:
strongest direct support for the small-model-manages-memory half of the thesis
(lane 4 owns the training recipes; this is the systems evidence). Careful: see the
Reproducing-LightMem refute below — retriever choice dominates its headline numbers.

**DimMem (2605.15759, Qiu et al. 2026).** Atomic typed units with explicit time,
location, reason, purpose, and keyword fields; a fine-tuned Qwen3-4B extractor beats
larger extractors. Take: typed schema plus small-extractor evidence in one paper —
the single best citation for "small models can do the filing" (capability 2).
Careful: extraction still a separate pass, not unified with embedding.

**StructMem (2604.21748, Xu et al. 2026, ACL 2026).** Event-level bindings with
cross-event links and periodic semantic consolidation. Take: consolidation-schedule
precedent for the revise pass. Careful: overlaps LightMem's group and codebase
(zjunlp/LightMem).

**Code-only systems (admitted on repositories as primary source, no papers found).**
Cognee (topoteretes/cognee, 30646 stars, Apache-2.0) — ECL pipelines into temporal
graphs; largest-adoption graph-memory codebase. LangMem (langchain-ai/langmem, 1660
stars, MIT) — namespaced long-term memory SDK; closest to file-like procedural
memory in an SDK. Memobase (memodb-io/memobase, 2893 stars, Apache-2.0) —
profile-centric memory; last push January 2026, treat as stale. Nemori
(nemori-ai/nemori, 207 stars, MIT) — minimalist memory MVP; low adoption caps
relevance. Honcho (plastic-labs/honcho, 7128 stars, AGPL-3.0) — session-scoped
memory; AGPL blocks reuse without legal review. Supermemory
(supermemoryai/supermemory, 29634 stars, MIT) — fast memory engine, large adoption,
internals unverified by any paper. Memori (MemoriLabs/Memori, 16621 stars, license
NOASSERTION) — LLM-agnostic memory layer; license field unresolved, do not reuse
before clarifying. Letta (letta-ai/letta, 24702 stars, Apache-2.0) — production
MemGPT lineage, pairs with the MemGPT paper row.

## (b) Refutations of brief claims

1. **"Background revise pass improves the store" — contested.** Useful Memories
Become Faulty (2605.12978, Zhang et al. 2026): continuously LLM-rewritten
consolidated banks accumulate faults while raw episodic traces stay reliable. The
revise pass needs fault containment, not just scheduling.
2. **"Structure is necessary for memory quality" — contested.** ReFind (2608.12888,
Li et al. 2026): agent-controlled lexical search over raw unmodified chat logs beats
graph- and tree-based memory systems (incl. HippoRAG 2, 53.2 vs 58.2 mean accuracy)
with a matched GPT-4o-mini backbone. Structure must justify its construction cost.
3. **"Lookup counts as memory" — contested.** Memo, Not True Memory (2604.27707, Xu
et al. 2026): vector stores implement lookup, not memory; generalization needs
weight-based abstraction. Bounds what filing into stores can claim without a
learning component.
4. **"Memory construction beats raw retrieval" — contested.** Reproducing LightMem
(2607.29104, Zhou et al. 2026): retriever choice swings accuracy 58.1% to 75.5% on a
fixed store, and construction discards answer-relevant information. Tempers the
LightMem admission above.

## (c) Unresolved ledger

- MemDelta (2606.29914): evaluation protocol, belongs to lane 10 — abstain, out of scope.
- SF-AMS (2607.22562): forgetting/utility policy, belongs to lane 8 — abstain, out of scope.
- FluxMem (2605.28773): authors state code will be open-sourced; artefact unverifiable — abstain.
- ProGraph (2607.19359): abs page never opened, repo has 1 star — abstain, adoption unverifiable.
- TencentDB-Agent-Memory (26373 stars): search-API listing only, repo page never opened — abstain.
- LycheeMem (1079 stars, Apache-2.0): listing only, no paper — abstain.
- ClaudioDrews/memory-os (1358 stars, MIT): hobby project, no paper, not the MemoryOS of scope — abstain, relevance 0.

## (d) Security findings

Lane 3's brief asks for typed stores, not the security half (that is lane 6), and no
memory-poisoning paper fell inside this lane's scope. Two requirements still transfer,
traced to lane-3 sources: (1) the Folio gate SHALL stage writes before they become
actionable premises, per the MemTX transactional-commit model (2607.23929); (2) the
revise pass SHALL preserve raw episodic traces alongside consolidations so faulty
rewrites are recoverable, per the faulty-memory result (2605.12978). Poisoning-specific
requirements are deferred to lane 6.
