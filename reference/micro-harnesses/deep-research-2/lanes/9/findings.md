# Lane 9 findings: pipeline orchestration for extraction at scale

Screened 22 candidates; 16 admitted (13 papers with PDFs in `papers/`, 2 repos, 1 vendor blog as secondary-only).
All figures below were read from the fetched paper text, arXiv abs page, repo page, or vendor page named in each entry.
Nothing in this file is recalled from memory without a fetched source.

## (a) Admitted items

### 1. GraphRAG pipeline — the reference batch design (2404.16130)
GraphRAG (Edge et al., 2024) is the canonical five-stage ingestion pipeline this lane measures everything
against: Source Documents → Text Chunks → Entities & Relationships → Knowledge Graph → Graph Communities →
Community Summaries, with query time as map-reduce over community summaries (paper §3.1, Fig. 1).
Two pipeline facts matter for MelodyScribe. First, extraction uses a self-reflection "gleaning" loop: after
entities are extracted from a chunk, the extracted set is fed back with a logit bias of 100 forcing a
yes/no "were entities missed" decision, iterating to a cap; this is what lets them use larger chunks without
recall collapse (GPT-4 extracted ~2x more entity references at 600-token chunks than at 2400). Second,
community summarization is embarrassingly parallel at both indexing and query time, and Leiden
hierarchical communities mean one query can be answered at several granularity levels. Take: the
chunk → extract → merge → Leiden → summarize ordering, with gleaning=1 as the cost/quality knob
(LightRAG reuses gleaning=1 for comparability). Careful: the paper's entity matching analysis uses
**exact string matching** (§3.1.3) and relies on community clustering to absorb duplicates — it is not a
dedup design, and community reports are the dominant token cost (see LightRAG §4.5 numbers below).

### 2. LightRAG — union-merge incremental indexing and the cost table (2410.05779)
LightRAG (Guo et al., EMNLP 2025) keeps GraphRAG-style LLM extraction (entities, relations, keywords,
`Dedupe ∘ Prof` over per-segment recognitions, Eq. 2) but replaces community traversal at retrieval with
dual-level (low/high) keyword retrieval over graph + vectors, and replaces full rebuilds on new data with
a union-merge incremental update: new document D′ goes through the same indexing steps φ and the result
is unioned (`V̂ ∪ V̂′`, `Ê ∪ Ê′`) with the existing graph, no reconstruction (paper §3, §4.5).
The legal-dataset cost table is the hardest ingestion-cost number in the lane: retrieval phase GraphRAG
≈ 610 level-2 communities × 1,000 tokens ≈ 610,000 tokens plus hundreds of API calls vs LightRAG <100
tokens and 1 API call; incremental phase GraphRAG ≈ 1,399 × 2 × 5,000 tokens to dismantle and regenerate
community structure vs LightRAG extraction-only overhead. Take: union-merge is the minimum viable
incremental design for MelodyScribe (append + merge, never rebuild). Careful: numbers are GPT-4o-mini,
chunk size 1200, gleaning 1, one legal corpus — a token/API-call comparison, not wall-clock or
docs-per-hour, and LLM-judge win rates, not independent replication.

### 3. HippoRAG — offline extraction, online single-step PPR, priced vs IRCoT (2405.14831)
HippoRAG (NeurIPS 2024) splits the pipeline into an offline indexing pass (LLM two-step OpenIE per
passage: named entities first, then triples seeded with them; retrieval-encoder synonym edges E′ added
where phrase cosine ≥ τ=0.8; passage↔phrase count matrix P) and an online retrieval pass (link query
entities to KG nodes, run Personalized PageRank with damping 0.5, score passages via n′·P).
The reported price of staging: single-step online retrieval matches or beats iterative IRCoT while being
10–30× cheaper and 6–13× faster (paper §1/§4; abstract says 10–20× — see refutations). Take: push every
LLM call offline except a cheap query-entity extraction + PPR walk; never run an LLM reasoning loop per
query on the serving path. Careful: synonym-edge count explodes with τ choice (e.g. ~146k–191k E′ edges
in their tables); MelodyScribe must budget E′ explicitly or PPR neighborhoods blow up.

### 4. HippoRAG 2 — passage nodes and the embedder's place in the order (2502.14802)
HippoRAG 2 (ICML 2025) answers the lane's stage-ordering question directly: keep the offline OpenIE KG,
but (1) add **passage nodes** to the graph so dense and graph signals live in one structure, (2) use the
**embedding model at retrieval time to seed PPR** (it scores both passages and triples as seed nodes),
and (3) add an **online LLM recognition-memory filter** over top triples to drop irrelevant ones
(paper Fig. 2, §3). It also documents the failure mode of ordering badly: structure-only augmentation
drops below plain dense RAG on factual benchmarks (NQ/PopQA), which the passage-node + dense-seed
design repairs (+7% associative over the best embedder). Take: MelodyScribe's order should be
extract-offline → embed-everything (chunks AND triples/passages) → dense-seed → graph-walk →
LLM-filter, i.e. embeddings serve retrieval, not indexing. Careful: the online LLM filter reintroduces a
per-query LLM call — budget it as a small classifier-style call, not generation.

### 5. RAPTOR — recursive embed/cluster/summarize tree and its build bill (2401.18059)
RAPTOR (ICLR 2024) builds a summary tree bottom-up: SBERT (`multi-qa-mpnet-base-din` family) leaf
embeddings → UMAP → BIC-selected GMM clustering (global pass then local pass) → LLM summary per
cluster → re-embed → repeat; retrieval uses the collapsed tree (all levels searchable). It couples to
+20pp absolute on QuALITY with GPT-4. Take: clustering-before-summarizing is the alternative to
Leiden when the corpus is long documents rather than entity-dense text, and the collapsed tree removes
a query-time traversal stage. Careful: every tree level is an LLM summarization bill over the whole
corpus; there is no incremental story in the paper (new documents invalidate upper levels), so it is a
batch-only design — the opposite of what a streaming harness wants unless subtrees are frozen.

### 6. MiniRAG — the small-model ingestion pipeline (2501.06713)
MiniRAG (HKUDS, 2025; repo HKUDS/MiniRAG, MIT, 2013 stars) is the closest published analog of a
MelodyScribe ingestion path: a heterogeneous chunk+entity graph built with SLM-friendly steps, then a
two-stage retrieval (lightweight sentence-embedding seed match → topology-enhanced path discovery with
entity relevance + structural importance + connectivity scores), reporting LLM-comparable quality at
**25% of the storage**. Its diagnosis section is directly reusable: SLMs fail at query interpretation and
semantic matching, so the pipeline compensates with explicit structure and decomposed steps rather than
bigger prompts. Take: when the extractor is a 1–2B model, index design (heterogeneous graph, short
inputs per call) matters more than prompt cleverness. Careful: 25% is storage vs LLM baselines on
their on-device benchmark, not an indexing-cost or latency claim; embedding model was
text-embedding-3-small in the LLM setting.

### 7. PathRAG — prune before prompting, order by reliability (2502.14902)
PathRAG (AAAI, Chen et al., 2025; repo BUPT-GAMMA/PathRAG) keeps a standard indexing graph but
changes the retrieval payload: keyword-seeded nodes → flow-based pruning with distance awareness
(resource-allocation inspired) to keep top-K reliable relational paths → concatenate each path as text →
place paths in the prompt in **ascending reliability order** (most reliable last) to exploit LLM
recency against "lost in the middle". Reports ~59.9%/57.1% average win rates vs GraphRAG/LightRAG
across six datasets × five dimensions. Take: the retrieval-payload ordering rule (weak evidence first,
strongest last, query first) is cheap and portable to any MelodyScribe payload assembler. Careful:
wins are LLM-judged; the pruning algorithm's "low time complexity" is not wall-clock profiled, and
indexing is unoptimized standard extraction — the paper improves the read path, not the write path.

### 8. KGGen — iterative clustering as the dedup worker (2502.09956)
KGGen (NeurIPS 2025; `pip install kg-gen`, repo stair-lab/kg-gen, 1269 stars) extracts triples with an
LM then applies an **iterative clustering algorithm** over nodes and edges (crowd-sourcing-inspired
entity resolution) to consolidate same-entity nodes and equivalent edges, explicitly targeting the
pathology it documents: OpenIE/GraphRAG-style graphs with nearly as many relation types as edges.
It ships the MINE benchmark and reports GraphRAG-comparable retrieval with better compression/sparsity
scaling as corpus length grows into the millions of tokens. Take: this is the concrete cross-worker
resolution recipe — resolve by clustering after extraction, not during — and the sparsity-vs-length
scaling test is the right acceptance test for MelodyScribe's merge step. Careful: clustering is another
offline bill (embedding + LLM verification per candidate pair); it is a batch refinement, not a
streaming operator.

### 9. Zep/Graphiti — the streaming design: episodes, bi-temporal edges, invalidation (2501.13956)
The Zep paper (2025) plus the getzep/graphiti repo (Apache-2.0, ~30.8k stars, 3.1k forks) is the only
admitted source built for **continuous ingestion**: raw units arrive as typed Episodes (message/text/JSON)
with reference timestamps; extraction derives entities/edges carrying four timestamps (created/expired on
the transactional timeline T′, valid/invalid on the event timeline T); new edges trigger LLM
contradiction checks against semantically related edges and invalidate (never delete) losers by setting
t_invalid. Episodes keep bidirectional indices to derived facts (provenance both ways). Reported: DMR
94.8 vs MemGPT 93.4; LongMemEval up to +18.5pp with −90% latency vs baselines. Take: episode-first
(non-lossy raw store), invalidate-don't-delete, and per-episode concurrency (repo default
`SEMAPHORE_LIMIT=10`, raisable) are the streaming template; the repo runs on Ollama + nomic-embed
locally, which is the MelodyScribe-compatible serving proof. Careful: latency/accuracy numbers are
vendor-reported on conversation memory, not document extraction; the managed Zep backend is
proprietary (Context Graph Engine) while the OSS core needs a self-hosted graph DB.

### 10. IRCoT — the expensive ordering to avoid (2212.10509)
IRCoT (ACL 2023) interleaves CoT sentences with retrieval (reason → retrieve → reason…), capping at 15
collected paragraphs; with GPT-3/codex it gains +11–21 recall points and +15 QA F1, and a 3B Flan-T5-XL
with IRCoT beats a 58× larger GPT-3 with one-step retrieval. Admitted as the **cost baseline**: every
HippoRAG-family saving is priced against exactly this loop. Take: interleaving is a quality ceiling
reference and a latency anti-pattern for serving — relegate it to offline hard-negative mining or eval,
never the query path. Careful: gains are with 2022-era GPT-3/Flan-T5 and BM25-style base retrievers;
absolute numbers do not transfer to modern embedders.

### 11. EDC — post-hoc canonicalization with a trained schema retriever (2404.03868)
EDC (EMNLP 2024; repo clear-nus/edc, MIT, 193 stars) decomposes KGC into Extract (open IE) →
Define (LLM writes a natural-language definition per induced schema element) → Canonicalize (embed
definitions with a sentence transformer, vector-nearest candidates, **LLM verifies** each merge to avoid
over-generalization), plus an optional refinement loop (EDC+R) driven by a schema retriever fine-tuned
from E5-mistral-7b-instruct. Take: definition-then-verify is the precision guard every embedding-only
dedup lacks, and the schema-retriever idea ports to MelodyScribe as "retrieve relevant existing entities
before deciding a merge" at insertion time. Careful: per its own README, the released code
**canonicalizes relations only** — entity-type canonicalization is future work, so it is half a dedup
worker as shipped.

### 12. Cognee tuning paper — pipeline knobs need per-corpus search (2505.24478)
Markovic et al. (2025, preliminary) sweep Cognee's chunking/graph/retrieval/prompting parameters on
HotPotQA/2Wiki/MuSiQue with EM/F1/DeepEval scoring: targeted tuning gives consistent but uneven gains
across datasets and metrics. The cognee repo itself (topoteretes/cognee, Apache-2.0, ~30.7k stars)
documents the orchestration surface relevant here: `remember` (add+cognify+improve) vs session-memory
`remember(..., session_id=...)` with background graph sync, batched multi-repo ingestion, conflict
resolution, Postgres-single-instance mode, and local-Ollama support. Take: expose chunking, resolution
thresholds, and retrieval routing as tuned config (Spike 010 material), and use session-then-graph
two-tier writes for interactive ingestion. Careful: the paper is explicitly preliminary and reports no
throughput; BEAM scores on the repo (0.79 @100K, 0.67 @10M exploratory) use benchmark-specific
formatting and warn against cross-system comparison.

### 13. Leiden — the community stage's guarantees (1810.08473)
Traag et al. (Sci Rep 2019) prove Leiden communities are guaranteed connected (Louvain can emit up to
25% badly-connected / 16% disconnected communities in their experiments) and that iterated Leiden
converges to subset-optimal partitions, while running faster than Louvain via fast local moves. Take:
use Leiden over Louvain for the community stage — disconnected communities produce incoherent
report-summarization units, which is exactly the failure a parallel summarize stage cannot detect.
Careful: guarantees hold at convergence/iteration; single-pass Leiden can still emit badly-connected
communities, so pin iteration counts in config.

### 14. nano-graphrag — the hackable single-node orchestrator (repo, MIT, 3988 stars)
gusye1234/nano-graphrag (~1100 lines excl. tests/prompts) is the most MelodyScribe-shaped artifact in
the lane: async everything (`ainsert`/`aquery` twins of every method), batch `insert([...])`, incremental
insert with **md5 content-hash chunk keys** (no duplicate chunks), storage split into KV (file) + vector
(nano-vectordb/hnswlib/faiss) + graph (networkx/Neo4j), per-call LLM/embedding concurrency caps
(`best_model_max_async`, `embedding_func_max_async`, `embedding_batch_num`), and a two-model split
(gpt-4o plans, gpt-4o-mini summarizes) with Ollama/sentence-transformer examples. It is also the
honest incremental design: chunk dedup is free, but **every insert recomputes communities and
regenerates all reports** — the recurring bill LightRAG's union-merge avoids. Take: copy the storage
split, the hash-key idempotency, and the async+e
...[truncated 7371 chars]