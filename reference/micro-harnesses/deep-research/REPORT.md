# MelodyScribe deep-research report

Scope: ten-lane survey testing the claim that every MelodyScribe piece exists
somewhere but no project combines them. Inputs: `lanes/<n>/findings.md` and
`lanes/<n>/method.md` for lanes 1–10, `merged/INVENTORY.tsv` (280 deduplicated
candidates: 226 admitted, 10 refuting, 44 abstained), `merged/SUMMARY.md`, and
240 admitted PDFs in `merged/papers/`. Per-lane appendices are the lane
`findings.md` files themselves, in `lanes/<n>/`. Nothing below comes from
memory; every item carries its arXiv id or URL inline, and any claim without a
source was moved to the unresolved ledger in part 4.

## 1. Verdict on the thesis

The thesis survives: after screening 280 deduplicated candidates (364 lane
rows), no project combines single-pass embedding-plus-generation, grammar-
constrained multi-store filing, modular KV-cache reuse, a background revise
pass, and sandboxed self-written skills behind one interface. The closest
existing system is MiniRAG (2501.06713, https://github.com/HKUDS/MiniRAG): a
small-LM-first graph RAG with a heterogeneous chunk-plus-entity graph designed
so small models match LLM-based RAG at 25% storage. What it lacks: no joint
embedding-and-generation in one forward pass (it retrieves, then generates);
no grammar-constrained filing operations into typed stores (graph only, no SQL
or procedural-memory outlet); no KV-cache reuse across chunks; no background
consolidation loop; no self-written skill library with a privilege boundary.
Runners-up each cover a different pair of capabilities and miss the rest:
RUBICON (2604.21413) couples agentic structuring with querying but has no
single-pass embedding, KV reuse, revision, or skill sandboxing; MemOS
(2507.03724, https://github.com/MemTensor/MemOS) has typed MemCube stores with
a scheduler but no unified embed/generate pass, no KV reuse, and no sandboxed
self-written skills; Mem-alpha (2509.25911,
https://github.com/wangyu-ustc/Mem-alpha) trains a 4B model to emit memory
ops but over a separate embedding/retrieval stack with no cache reuse. The
combination — one 1–3B model that embeds, files, reuses cached states, and
revises, with its own writings sandboxed — remains unbuilt.

## 2. Top twenty, ranked

1. **OneGen (2409.05152, https://github.com/zjunlp/OneGen).** The only work
found that truly generates and retrieves in one forward pass: autoregressively
emitted retrieval tokens double as embedding queries and reuse the live KV
cache, with no generation degradation reported. Take the file-while-generating
pattern as the architecture for capability 1 instead of GritLM-style
switch-and-re-encode. Careful: demonstrated only at 7B, and retrieval tokens
still consume generation budget.

2. **CacheBlend (2405.16444, https://github.com/LMCache/LMCache).** The
central repair result for capability 3: concatenating independently computed
chunk caches loses cross-chunk attention, and recomputing only the
highest-KV-deviation tokens restores full-prefill quality at 2.2–3.3x TTFT
reduction. Take selective recompute as the default compose operator for
retrieved chunks. Careful: a 2026 follow-up (2607.21599, abstained) contests
the no-loss claim at long contexts, so run our own length sweep.

3. **DeepRetrieval (2503.00223, https://github.com/pat-jj/DeepRetrieval).**
RLVR on retrieval metrics trains Qwen2.5-3B query/SQL rewriting that beats
GPT-4o and Claude-3.5 on retrieval and BIRD/Spider SQL tasks, with 3B
checkpoints released. Strongest direct support for the small-beats-frontier
hypothesis at exactly MelodyScribe scale, and the only item covering SQL
filing. Careful: gains are retriever-coupled; re-validate against our own
Faiss/SQLite stack.

4. **Mem-alpha (2509.25911, https://github.com/wangyu-ustc/Mem-alpha).** RL
trains a Qwen3-4B agent to emit store/structure/update ops over
core/episodic/semantic memory, rewarded by downstream QA accuracy; 4B trained
better than 8B because instruction-following, not scale, binds at this size.
Closest analogue of capabilities 2 and 4. Careful: sparse end-task reward
gives weak credit assignment per op, and no official weights are released.

5. **Search-R1 (2503.09516, https://github.com/PeterGriffinJin/Search-R1).**
GRPO/PPO teaches Qwen2.5-3B/7B when and how to call search mid-reasoning; the
transferable detail is masking retrieved tokens out of the loss. Adopt that
masking verbatim for any rollout containing retrieved text; 3B checkpoints are
released and fit one 16 GB GPU. Careful: outcome-only RL overfits its domain
(see RAG-Gym, 2502.13957).

6. **GritLM (2402.09906, https://github.com/ContextualAI/gritlm).** Joint
generative-plus-embedding training via instruction-switched attention with a
claimed no-loss unification and >60% RAG speedup. The core joint-training
recipe for capability 1. Careful: it switches attention modes per task, so
embedding and generating remain separate passes, and all artefacts are 7B+.

7. **LOTUS (2407.11418, https://github.com/lotus-data/lotus).** Formal
semantic operators (filter, join, group-by, top-k over natural-language
criteria) with gold-algorithm semantics and an accuracy-guaranteeing
optimizer. The formalism the op-list language wants: a 2B model emits
operators, not free text. Careful: guarantees are relative to the gold
program, not to ground truth.

8. **DocETL (2410.12189, https://github.com/ucbepic/docetl).** YAML document
pipelines where an agent rewrites operations and each op carries validation
directives that trigger retries. Reuse the per-op `validate:` pattern as the
grammar around filing ops: emit op plus checkable assertion, retry on
failure. Careful: validation is LLM-judged, so correlated errors can pass bad
extractions.

9. **ACE — Agentic Context Engineering (2510.04618,
https://github.com/ace-agent/ace).** Generator/Reflector/Curator playbook with
delta updates to an evolving context. The closest published Folio analog for
capability 5's sandboxed self-written skills. Careful: verify the ICLR 2026
venue claim against the primary source before citing it as peer-reviewed.

10. **Self-RAG (2310.11511, https://github.com/AkariAsai/self-rag).** 7B/13B
models instruction-tuned to emit retrieve/no-retrieve and critique reflection
tokens, so retrieve-decisions live inside the generator; critic and generators
released. The canonical small-model retrieve-decision recipe. Careful:
two-model serving cost plus reflection-token overhead on every segment.

11. **MINJA (2503.03704, https://github.com/dsh3n77/MINJA).** Query-only
memory poisoning via bridging steps and progressive shortening: 98.2%
injection, 76.8% attack success. Proves utility and integrity are independent
axes and forces the Folio gate requirements in part 5. Careful: evaluated on
agent memory benchmarks, not on file-shaped Folios specifically.

12. **PoisonedRAG (2402.07867, https://github.com/sleeepeer/PoisonedRAG).**
Two-condition poison texts reach ~97% attack success with 5 texts in millions,
and tested defenses (paraphrase, perplexity) fail. Rules out output-side
filtering as Folio hygiene. Careful: RAG-corpus setting; Folio promotion
needs its own replication of the two-condition test.

13. **CaMeL (2503.18813, https://github.com/google-research/camel-prompt-injection).**
Capability-based isolation separating data from instructions. The design
pattern the Folio gate should copy: Folio contents enter the frontier context
as data with a capability tag; only the human-authored skill carries
instruction privilege. Careful: authors state the code is unmaintained
research artifact — adopt the architecture, not the code.

14. **MiniRAG (2501.06713, https://github.com/HKUDS/MiniRAG).** SLM-first
graph RAG with topology-enhanced retrieval over a heterogeneous chunk-entity
graph plus an on-device benchmark. Study its entity-chunk edge design for
Score sections. Careful: compared mostly against its own benchmark suite;
independent replication is thin.

15. **HippoRAG 2 (2502.14802, https://github.com/OSU-NLP-Group/HippoRAG).**
Deeper passage integration plus online LLM use over an extracted-triple graph
with Personalized PageRank; fixes the factual-memory regression that graph
augmentation otherwise causes. The standard graph baseline every graph store
must beat. Careful: the paper recipe runs extraction on 70B-class models —
far above the 1–3B budget.

16. **KAG (2409.13731, https://github.com/OpenSPG/KAG).** KG–chunk mutual
indexing (every graph node points back to its chunk) plus logical-form-guided
hybrid reasoning. The concrete mechanism for the "link this section's vector
back to raw text and graph nodes" directive. Careful: heavyweight OpenSPG
stack; distil the ideas, not the code.

17. **Qwen3-Embedding (2506.05176, https://github.com/QwenLM/Qwen3-Embedding).**
Decoder-based embedders at 0.6B/4B/8B with multi-stage training plus model
merging, Apache-2.0. The 0.6B variant is the closest public artefact to a
MiniCPM-scale embedder — copy its data mix and merging strategy. Careful:
embed-only with no generation-preservation results.

18. **Distilling Step-by-Step (doi:10.18653/v1/2023.findings-acl.507).** A
540M student trained on teacher rationales as well as labels beats its much
larger teacher on NLI with far less data. Cleanest precedent for the
motivating hypothesis. Careful: wins are on short-output classification
tasks, not grammar-constrained multi-op emission.

19. **SGLang (2312.07104, https://github.com/sgl-project/sglang).**
Radix-tree KV reuse across requests and program branches plus compressed FSMs
for structured decoding: reuse plus grammar-constrained emission in one
runtime. Evaluate as the serving engine first. Careful: radix reuse is still
prefix-structured, and it is server-class software, not an on-device target.

20. **Mem0 (2504.19413, https://github.com/mem0ai/mem0).** Two-phase
extract-then-update pipeline with an ADD/UPDATE/DELETE operation set and an
optional graph store; the most adopted memory layer found (65k stars). Lift
the operation set and decay scores for the revise pass. Careful: extraction
is a separate LLM pass per turn — the opposite of the one-pass goal.

## 3. Refutations

Every brief/hypothesis claim a primary source contradicts:

1. "Cached chunk states compose out of order for free" — refuted by
CacheBlend (2405.16444), EPIC (2410.15332), TurboRAG (2410.07590), and KVLink
(2502.16002): raw concatenation loses cross-chunk attention and carries sink
distortion; each paper's contribution is the repair. Compose-plus-repair is
mandatory.
2. "Prefix caching suffices for RAG/agent assembly" — refuted by RAGCache
(2404.12457), EPIC (2410.15332), and CacheClip (2510.10129): shared prefixes
rarely occur in assembled prompts.
3. "Position-independent reuse is safe by default" — refuted by HijackKV
(2607.19957, context hijack via token-match retrieval) and CachePrune
(2605.23640, cross-user input leakage through sharing side channels).
4. "Compression and non-prefix reuse compose freely" — contradicted by C2KV
(2607.17715, abstained but abs/HTML/GitHub-verified): naive stacking severely
degrades accuracy.
5. "One forward pass does both" via GritLM — refuted as a reading of GritLM
(2402.09906): it switches attention modes per task, so embedding and
generating are separate passes. Only OneGen (2409.05152) unifies in a single
pass, at 7B.
6. "Embeddings from own hidden states are free" — contradicted by NV-Embed
(2405.17428, learned pooling head beats last-token; causal mask must go),
LLM2Vec (2404.05961, needs bidirectional enablement plus MNTP), and Echo
(2402.15449, costs 2x tokens).
7. "Grammar-constrained decoding improves small-model accuracy" as a blanket
claim — contradicted by Repair, Not Improvement (2608.13959): constraints
repair schema validity but do not improve, and can harm, tool-call
abstention decisions.
8. "Mixing different models helps" — contradicted by Rethinking
Mixture-of-Agents (2502.00674): mixing frequently underperforms the best
single model.
9. "LoRA matches full fine-tuning" as a blanket claim — contradicted by LoRA
Learns Less and Forgets Less (2405.09673): LoRA underperforms on acquiring
new facts while forgetting less.
10. "Router/ensemble judges are independent" — undermined by Great Models
Think Alike (2502.04313): correlated failures across frontier models weaken
routing and cascade independence assumptions.
11. "A background revise pass improves the store by itself" — contested by
Useful Memories Become Faulty (2605.12978, continuously rewritten banks
accumulate faults while raw traces stay reliable) and Cannot Self-Correct
(2310.01798, no self-correction without external feedback); reflection loops
lose to repeated sampling at equal cost at 1.5–7B (2607.28576).
12. "Structure is necessary for memory quality" — contested by ReFind
(2608.12888): agent-controlled lexical search over raw logs beats graph- and
tree-based memory systems with a matched backbone.
13. "Lookup counts as memory" — contested by Memo, Not True Memory
(2604.27707): vector stores implement lookup; generalization needs
weight-based abstraction.
14. "Memory construction beats raw retrieval" — tempered by Reproducing
LightMem (2607.29104): retriever choice dominates headline numbers and
construction discards answer-relevant information.
15. "Graph augmentation is a pure win" — refuted by HippoRAG 2 (2502.14802):
structure-augmented RAG scores below standard RAG on basic factual memory.
16. "Bigger retrieved context is better" — refuted by PathRAG (2502.14902):
the binding constraint is redundancy, not insufficiency.
17. "Graph retrieval needs a heavy joint model" — refuted by SubgraphRAG
(2410.20724): a lightweight MLP with structural-distance features wins at a
fraction of the cost.
18. "Multi-step agentic retrieval is required for multi-hop" — refuted by
HippoRAG 1 (2405.14831): single-step PPR matches iterative IRCoT at 10–30x
lower cost.
19. "Frontier judges evaluate retrieval best" — refuted by RAGBench
(2407.11005): a 400M fine-tuned DeBERTa beats billion-parameter few-shot LLM
judges.
20. "LLMs weigh retrieved evidence against their own knowledge" — refuted by
RGB (2309.01431): models prioritize retrieved text over correct parametric
knowledge even after explicit warnings.
21. "Vector similarity approximates reasoning relevance" — refuted by KAG
(2409.13731): measured similarity–relevance gap plus insensitivity to
numbers, time, and rules.
22. "Passages are the natural retrieval unit" — refuted by Dense X Retrieval
(2312.06648): proposition-level units beat passage-level at fixed budget.
23. "Retrieval always helps" — refuted by Adaptive-RAG (2403.14403): a large
share of queries are best answered with no retrieval; a query gate is
required.
24. "One embedding model suffices" at the margin — refuted by RouterRetriever
(2409.02685): a routed mixture of specialist embedders beats every single
embedder.
25. "LLM-extracted structure is trustworthy by construction" — refuted by the
LOTUS program (2407.11418) and DocETL (2410.12189): both exist because raw
LLM operators are unreliable without gold semantics, optimizers, and
per-op validation.
26. "Self-written memory can be trusted once it helps on benchmarks" —
refuted by MINJA (2503.03704): helpful-looking implanted records steer later
queries.
27. "Output-side filters are sufficient memory hygiene" — refuted by
PoisonedRAG (2402.07867), which evaluated paraphrase and perplexity defenses
and found them insufficient.
28. "Prompt-level guardrails around a frontier reader are enough" — refuted
by Greshake et al. (2302.12173): no effective mitigations existed for
retrieval-driven compromise, persisting across sessions via memory.
29. "Small/rare poison fractions are negligible" — refuted by AgentPoison
(2407.12784): under 0.1% poison rate with at least 80% attack success.
30. "The agent may freely rewrite its own memory" — contested by DeChant
(2501.11739): agents must not add, delete, or change their own memories
afterward.
31. "MiniCPM5-2B is the current candidate" — corrected by the fetched
OpenBMB/MiniCPM README (https://github.com/OpenBMB/MiniCPM): the shipped
small MiniCPM5 checkpoint is MiniCPM5-1B; no 2B artefact was found.
32. Broad "small matches frontier" readings — bounded by HELMET (2410.02694):
open models trail closed ones on full-context reasoning and complex
instruction following, with the gap widening by length. Parity must be
claimed per narrow task with a benchmark attached.

## 4. Per-lane findings

Admitted items with sources; then each lane's unresolved ledger with reasons.
One-line form here; full paragraphs live in `lanes/<n>/findings.md`.

### Lane 1 — Unified embedding and generation in one model (27 screened, 17 admitted)

Admitted: GritLM (2402.09906); LLM2Vec (2404.05961); NV-Embed (2405.17428);
E5-Mistral (2401.00368); Echo (2402.15449); Qwen3-Embedding (2506.05176);
OneGen (2409.05152); PromptEOL (2307.16645); KaLM-Embedding (2501.01028);
MetaEOL (2402.18458); EmbeddingGemma (2509.20354); BGE-M3 (2402.03216); SGPT
(2202.08904); Gemini Embedding (2503.07891); Gecko (2403.20327); E5
(2212.03533); AnglE (2309.12871). Core result: no admitted precedent for
capability 1 as stated (one pass, 1–3B, embed plus constrained op emission);
every unifier is 7B+, every sub-1B decoder-embedder is embed-only, and no
paper measures generation degradation from embedding duty at 1–3B — the
hypothesis stands unrefuted and unevidenced at target scale.
Unresolved: SFR-Embedding-Mistral, Seed1.5-Embedding, Google
text-embedding-004 (vendor-only, no paper); Arctic-Embed 2.0 (2412.04506),
Jina-v3 (2409.10173), Contriever (2112.09118) (verified but encoder-only,
out of scope); GTE-Qwen2, BGE-Multilingual-Gemma2 (weights only, no method
paper); LLM2Vec-Gen (2603.10913, Mar-2026 preprint, unverified); Hydra
(2603.28554, single-author preprint claiming GritLM-style training collapses
generation — do not cite until reproduced).

### Lane 2 — KV-cache reuse beyond the prefix (43 screened, 24 admitted)

Admitted: Prompt Cache (2311.04934); CacheBlend (2405.16444); EPIC
(2410.15332); RAGCache (2404.12457); TurboRAG (2410.07590); CacheGen
(2310.07240); ChunkAttention (2402.15220); KVLink (2502.16002);
Block-Attention (2409.15355); MiniPIC (2606.13126); HYPIC (2607.01299);
CacheClip (2510.10129); vLLM/PagedAttention (2309.06180); SGLang (2312.07104);
KV Packet (2604.13226); Grounded Cache Routing (2605.27494); HijackKV
(2607.19957); CachePrune (2605.23640); ReCache (2608.19662); CoinRAG
(2608.07458); LMCache, llama.cpp, TensorRT-LLM, MLX (code-only, GitHub-API
verified). Core result: out-of-order composition without repair is refuted;
selective recompute plus sink mitigation is the default compose operator.
Unresolved: TokenDance, SparseX, PCR, Mixture-of-Translators, Universal
Context-Reuse Layer, LinearKV, AgentKVShift, Block Distillation (2605.15913),
AdapShot, ObjectCache, Can-I-Buy-Your-KV-Cache (scope-bounded despite
verification); CacheProbe (2605.30613), KeyPooling (2608.17485) (security
overlap, cited not filed); DAF (2607.21599, contests CacheBlend — needs
replication), C2KV (2607.17715), Probing-the-Prompt-KV-Cache (2605.30574)
(quality-measurement cites); KVBoost, ProphetKV (surfaced as snippets only,
no id captured); KVShareArena (2609.10266, abs never opened, too fresh).

### Lane 3 — Agent memory systems with multiple typed stores (45 screened, 34 admitted, 4 refuted)

Admitted papers: MemGPT (2310.08560); Generative Agents (2304.03442);
Reflexion (2303.11366); A-MEM (2502.12110); Mem0 (2504.19413); MemOS
(2507.03724); MIRIX (2507.07957); Zep/Graphiti (2501.13956); MemoryBank
(2305.10250); HippoRAG (2405.14831); HippoRAG 2 (2502.14802); Memanto
(2604.22085); Is-Agent-Memory-a-Database (2605.26252); Beyond-Semantic
(2606.06090); Harness-the-Memory (2608.15008); Episodic-Semantic (2605.17625);
MemTX (2607.23929); HAGE (2605.09942); eMEM (2606.03374); REMem (2602.13530);
SimpleMem (2601.02553); Omni-SimpleMem (2604.01007); MemInsight (2503.21760);
LightMem (2604.07798); DimMem (2605.15759); StructMem (2604.21748). Admitted
code-only: Cognee, LangMem, Memobase, Nemori, Honcho, Supermemory, Memori,
Letta (repositories as primary source). Refuted rows (cited, not filed):
Useful-Memories-Faulty (2605.12978); ReFind (2608.12888); Memo-Not-Memory
(2604.27707); Reproducing-LightMem (2607.29104).
Unresolved: MemDelta (2606.29914, belongs to lane 10); SF-AMS (2607.22562,
belongs to lane 8); FluxMem (2605.28773, code promised, unverifiable);
ProGraph (2607.19359, abs never opened, 1-star repo); TencentDB-Agent-Memory,
LycheeMem, ClaudioDrews/memory-os (listing-only, no paper).

### Lane 4 — Small models trained to manage memory or decide retrieval (22 screened, 18 admitted)

Admitted: Mem-alpha (2509.25911); Memory-R1 (2508.19828); Search-R1
(2503.09516); Self-RAG (2310.11511); DeepRetrieval (2503.00223); RECOMP
(2310.04408); FilCo (2311.08377); RankRAG (2407.02485); Adaptive-RAG
(2403.14403); CRAG (2401.15884); RAG-Gym (2502.13957); MemAgent (2507.02259);
ReSearch (2503.19470); R1-Searcher (2503.05592); R1-Searcher++ (2505.17005);
RA-DIT (2310.01352); Toolformer (2302.04761); STaR (2203.14465). Core result:
no admitted source refutes the lane hypothesis; process supervision beats
outcome-only RL out-of-domain (RAG-Gym), and instruction-following binds
before scale inside the band (Mem-alpha 4B beats 8B).
Unresolved: ReST (2308.08998), Search-o1 (2501.05366), DSPy (2310.03714),
ActiveRAG (2305.06983) (verified but off-lane: no 1–8B model trained to
decide); Mem-alpha weights (community upload unverified); Memory-R1,
ReSearch, R1-Searcher(++), RankRAG, STaR, Toolformer (recipes only, no
released weights).

### Lane 5 — Documents to structured tables and SQL (57 screened, 52 admitted: 40 papers + 12 code)

Admitted: Evaporate (2304.09433); ZenDB-paper (2405.04674); LOTUS
(2407.11418); Palimpzest (2405.14696); DocETL (2410.12189); PalimpChat
(2502.03368); BlendSQL (2402.17882); HybridRAG (2408.04948); Adaptive-RAG
(2403.14403); RouterRetriever (2409.02685); RouteLLM (2406.18665);
LlamaIndex-routers, Vanna (code-only); TableRAG-million-token (2410.04739);
TableRAG-hetero (2506.10380); ReAcTable (2310.00815); Chain-of-Table
(2401.04398); StructGPT (2305.09645); Binder (2210.02875); BIRD (2305.03111);
DIN-SQL (2304.11015); CHESS (2405.16755); Chain-of-Query (2508.15809);
SemBench (2511.01716); Compilation-engine (2608.06677); NL-to-pipelines
(2606.04641); Larch (2606.07923); RUBICON (2604.21413); Multi-objective
rewrites (2512.02289); Type-rules (2509.20208); Small-LMs-for-large-DBs
(2606.31808); SQuaD-SQL (2607.08161); FINER-SQL (2605.03465); Schema-First
(2606.28387); Listwise-memory (2609.00834); Multi-turn-memory (2605.26394);
LoRA-trade-offs (2607.25583); T2-RAGBench (2506.12071); mmRAG (2505.11180);
Ontology-from-RDBs (2506.01232); Agentic-Context-Cracking (2608.31082);
VikingRAG (2609.11390). Core result: the declarative-operator stack
(Evaporate/LOTUS/Palimpzest/DocETL/BlendSQL) is the direct template for
capability 2; the combination claim holds but the ETL-plus-query half alone
does not (RUBICON, PalimpChat).
Unresolved: TAG, DATER, SemCEB, CSR-RAG (recalled, unverifiable within
budget); ZenDB code (no official repo); LlamaIndex-router and Vanna accuracy
claims (secondary sources only).

### Lane 6 — Self-written skills and procedural memory, plus security (27 screened, 20 admitted)

Admitted: Voyager (2305.16291); ExpeL (2308.10144); Reflexion (2303.11366);
Generative Agents (2304.03442); MemoryBank (2305.10250); ACE (2510.04618);
Dynamic Cheatsheet (2504.07952); Agent Workflow Memory (2409.07429); SOP-Agent
(2501.09316); Agent Skills specification (https://github.com/anthropics/skills);
AgentPoison (2407.12784); MINJA (2503.03704); PoisonedRAG (2402.07867);
indirect-prompt-injection (2302.12173); CaMeL (2503.18813); Signed-Prompt
(2401.07612); Episodic-memory-risks (2501.11739); prompt-injection survey
(2306.05499); memory-mechanism survey (2404.13501); INMS (2404.09982). Core
result: Voyager plus ExpeL plus ACE give the skill-writing lineage; the
attack papers (MINJA, AgentPoison, PoisonedRAG, Greshake) make the Folio gate
mandatory, with CaMeL as the design pattern.
Unresolved: BadChain (recalled id resolves to an unrelated physics paper);
MemFS file memory (no primary paper; term collides with the JS memfs
library); OpenAI instruction-hierarchy defenses (secondary only);
Progent-class tool policies (id/repo unverified); 2026 poisoning preprints
(MAFIA and others, listing titles only); LearnAct, EvoAgent, WorkflowLLM
(named but never verified).

### Lane 7 — Small versus frontier, and distillation (45 screened, 33 admitted: 32 papers + 1 code, plus 4 refuted rows)

Admitted: Distilling Step-by-Step (ACL Findings 2023); MiniLLM (2306.08543);
On-Policy Distillation (2306.13649); DistiLLM (2402.03898); DistiLLM-2
(2503.07067); Speculative KD (2410.11325); SeqKD (1606.07947); f-Divergence
SeqKD (2307.15190); Orca (2306.02707); Orca 2 (2311.11045); Phi-3
(2404.14219); LoRA (2106.09685); QLoRA (2305.14314); DoRA (2402.09353);
QLoRA-facts (2608.25677); Outlines (2307.09702); XGrammar (2411.15100);
SGLang (2312.07104); JSONSchemaBench (2501.10868); Where-vs-What
(2608.25358); Toolformer (2302.04761); RA-DIT (2310.01352); Gorilla
(2305.15334); ToolACE (2409.00920); APIGen (2406.18518); Granite-FC
(2407.00121); FrugalGPT (2305.05176); RouteLLM (2406.18665); MoA
(2406.04692); Guided-decoding-in-RAG (2509.06631); SLM-agentic-survey
(2510.03847); llama.cpp (code-only). Refuted rows (cited, not filed):
Repair-Not-Improvement (2608.13959); Rethinking-MoA (2502.00674); LoRA-Learns-
Less (2405.09673); Great-Models-Think-Alike (2502.04313). Core result:
rationale-augmented SFT plus on-policy distillation plus LoRA/QLoRA adapters
plus Outlines/XGrammar constraints give a complete single-GPU recipe for the
2B op-emitter; constraints guarantee format validity only, not decision
quality.
Unresolved: GKD (name unresolvable to one verified id); Self-MoA and CAPA
(brief ids resolve to different papers — Rethinking-MoA and Great-Models-
Think-Alike respectively; true ids unverified); guessed distillation/adapter
ids corrected to verified ones (see findings); BFCL (live leaderboard,
secondary only); gorilla/RouteLLM/MoA/llama.cpp star counts (rate-limited,
omitted not estimated).

### Lane 8 — Consolidation loops and failure modes (40 screened, 34 admitted, 2 refuted)

Admitted: Sleep-time Compute (2504.13171); Language-Models-Need-Sleep
(2606.03979); A-MEM (2502.12110); Mem0 (2504.19413); MemOS (2507.03724);
Reflexion (2303.11366); Generative Agents (2304.03442); MemoryBank
(2305.10250); Self-Refine (2303.17651); ExpeL (2308.10144); CRITIC
(2305.11738); Titans (2501.00663); MemGPT/Letta (2310.08560); Self-RAG
(2310.11511); Retain-or-Consolidate (2607.17545); Learning-to-Forget
(2603.14517); TRUSTMEM (2606.25161); TiMem (2601.02845); Mela (2605.10537);
StreamingLLM (2309.17453); EWC (1612.00796); Who's-Harry-Potter (2310.02238);
Textual-Relaxation (2607.22653); Sleeping-Agent (2608.11775); Agent-Drift
(2601.04170); SSGM (2603.11768); OEP (2605.18930); Provenance-firewall
(2607.29167); Hindsight (2512.12818); Mem-alpha (2509.25911); LifeAlign
(2509.17183); Function-Tokens (2510.08203); Human-like-recall (2404.00573);
MemGAS (2505.19549). Refuted rows (cited, not filed): Cannot-Self-Correct
(2310.01798); Sample-More-Reflect-Less (2607.28576). Core result: every
revise operator must be gated on an external signal (retrieval hit-rate, tool
check, human label) and benchmarked against best-of-N sampling at equal
budget; retain-vs-consolidate selection should be budget-aware.
Unresolved: 2310.09297 (abs-verified only, full text unreviewed); H2O KV
eviction and RMM (ids/names unverifiable); 2310.01417 (verified NOT ExpeL —
kept so the misidentification is not repeated).

### Lane 9 — On-device small models and small embedders (33 screened, 27 admitted)

Admitted: Qwen3 (2505.09388); SmolLM2 (2502.02737); SmolLM3-3B (repo/card,
no paper); Gemma 3 (2503.19786); Phi-4-Mini (2503.01743); LFM2 (2511.23404);
MiniCPM4 (2506.07900); MiniCPM-1.2B/2.4B (2404.06395); MiniCPM5-1B (repo
release, no paper); OLMo (2402.00838); Qwen3-Embedding (2506.05176);
EmbeddingGemma (2509.20354); Arctic-Embed 2.0 (2412.04506); Nomic v2 MoE
(2502.07972); Nomic v1 137M (2402.01613); jina-v3 (2409.10173); BGE-M3
(2402.03216); ModernBERT (2412.13663); E5-Mistral recipe (2401.00368);
Multilingual-E5 (2402.05672); MiniCPM-Embedding-Light (model card, no paper);
MTEB (2210.07316); MMTEB (2502.13595); LongEmbed (2404.12096); HELMET
(2410.02694); BFCL (PMLR v267, proceedings-only); LoCo/M2-BERT (2402.07440).
Core result: the substrate exists off the shelf under permissive licenses
(Qwen3-1.7B emitter, Qwen3-0.6B or EmbeddingGemma embedder), but no single
sub-3B artefact jointly trains embedding and generation; default shortlist is
Qwen3-1.7B for op emission with BFCL numbers required before trust.
Unresolved: OLMo 2 (2501.00656), Nemotron-H (2504.03624), Nemotron Nano 2
(2508.14444) (verified but out of the 0.3–3B band); Arctic-Embed v1
(2405.05374, superseded); IBM Granite small models (secondary sources only);
Gemma 1 2B/7B (2403.08295, superseded); several repo star/push fields
(rate-limited, marked not-fetched).

### Lane 10 — Graph, vector, and relational fusion (25 screened, 24 admitted)

Admitted: HippoRAG 2 (2502.14802); HippoRAG 1 (2405.14831); GraphRAG
(2404.16130); LightRAG (2410.05779); MiniRAG (2501.06713); KAG (2409.13731);
TableRAG-Google (2410.04739); TableRAG-Huawei (2506.10380); Zep/Graphiti
(2501.13956); Cognee (code-only); G-Retriever (2402.07630); GRAG
(2405.16506); Think-on-Graph (2307.07697); RAPTOR (2401.18059); SubgraphRAG
(2410.20724); PathRAG (2502.14902); StructRAG (2410.08815); LeanRAG
(2508.10391); Dense X Retrieval (2312.06648); GLiNER (2311.08526); REBEL
(EMNLP 2021 Findings); CRAG-benchmark (2406.04744); RGB (2309.01431);
RAGBench (2407.11005). Core result: file to the graph selectively (graph
augmentation regresses factual memory otherwise); proposition-level units
beat passages; mutual node-to-chunk indexing plus validity windows are the
two mechanisms to copy; mmRAG (2505.11180) plus CRAG plus RGB give the
compare-modalities-on-one-corpus harness.
Unresolved: StructRAG-scholarly (DOI 10.1145/3701716.3717819, secondary
snippets only, name-collides with the ICLR StructRAG); several star/push/
license cells (GitHub 403 windows, marked not-fetched); TAG, Fast-GraphRAG,
BERGEN, RAGAS and others (title-screened only during chaining, deprioritized
after the 20-candidate minimum was exceeded with verified items).

## 5. Security findings for the Folio gate, stated as requirements

- **F-1.** Treat every model-written Folio entry as untrusted input; require
provenance (source paragraph, model, run) on each entry (MINJA, 2503.03704).
- **F-2.** Admission screening must include embedding-space novelty/isolation
analysis, not text inspection alone; triggers transfer across embedders
(AgentPoison, 2407.12784).
- **F-3.** Evaluate candidate entries against both PoisonedRAG conditions:
would this entry be retrieved for unrelated queries, and would it steer
generation if retrieved (2402.07867).
- **F-4.** Folio reads are code-execution-equivalent; sandbox model-written
skills and never merge them into the human-authored skill's privilege tier
(Greshake et al., 2302.12173).
- **F-5.** Architect the gate as capability separation (data vs
instructions), not as a text filter; adopt the CaMeL pattern, not its
unmaintained code (2503.18813).
- **F-6.** Rate-limit and audit memory writes per principal so progressive
multi-query implantation is detectable in the write log (MINJA progressive
shortening, 2503.03704).
- **F-7.** Folios are append-only from the agent's perspective; only the
revise pass with human-tier authorization edits or deletes, with signed
human-tier instructions as the authorization mechanism (DeChant, 2501.11739;
Signed-Prompt, 2401.07612).
- **F-8.** Do not rely on paraphrasing or perplexity filtering as the gate;
both were measured and failed (PoisonedRAG, 2402.07867).
- **F-9.** Context-bind every reusable KV block on (content hash,
source-context hash, producer identity), never on surface token match alone;
re-verify binding at compose time (HijackKV, 2607.19957).
- **F-10.** Isolate KV pools by trust principal (human skill, model Folio,
third-party retrieval); cross-pool sharing defaults off; share only segments
explicitly labeled privacy-irrelevant, since sharing state is
timing-observable (CachePrune, 2605.23640; CacheProbe, 2605.30613; KeyPooling,
2608.17485).
- **F-11.** Gate every KV reuse on groundedness: backing evidence still
present and corpus version unchanged, else fall back to full prefill
(Grounded Cache Routing, 2605.27494).
- **F-12.** Trust-gate every revise-pass promotion with a trust score; never
consolidate untrustworthy content into long-term memory (TRUSTMEM,
2606.25161).
- **F-13.** Promote only learnings that improve held-out retrieval
(transferability), not merely locally-correct ones (OEP, 2605.18930).
- **F-14.** Preserve provenance across rewrites with a non-amplification
rule for low-trust sources (Provenance firewall, 2607.29167).
- **F-15.** Bound memory evolution with stability gates and rollback on
drift; gate all self-correction on external tool or retrieval verification,
never pure self-rewrite (SSGM, 2603.11768; Agent Drift, 2601.04170; CRITIC,
2305.11738; 2310.01798).
- **F-16.** Train and evaluate any filing policy against a held-out clean
store: RL rewards used here (retrieval recall, QA accuracy) assume a clean
corpus and will otherwise reinforce attacker-favorable filings (DeepRetrieval,
2503.00223; Mem-alpha, 2509.25911; RAG-Gym, 2502.13957).

## 6. Reusable artefacts runnable on one 16 GB GPU, with license

Checkpoints and weights: Qwen3-0.6B/1.7B/4B (2505.09388, Apache-2.0);
Qwen3-Embedding-0.6B (2506.05176, Apache-2.0); SmolLM2 135M/360M/1.7B plus
datasets (2502.02737, Apache-2.0); SmolLM3-3B (repo/card, Apache-2.0);
EmbeddingGemma-300M (2509.20354, Gemma Terms — research only for commercial
plans); KaLM-Embedding-0.5B (2501.01028, MIT); MiniCPM-Embedding-Light-440M
(model card, bilingual); ModernBERT 149M/395M (2412.13663, Apache-2.0); Nomic
Embed v1 137M and v2 MoE (2402.01613, 2502.07972, open); BGE-M3 569M
(2402.03216, MIT); Arctic-Embed-2 m/l (2412.04506, Apache-2.0); Search-R1
Qwen2.5-3B/7B checkpoints (2503.09516, Apache-2.0, via HF org PeterJinGo);
DeepRetrieval Qwen2.5-3B checkpoints (2503.00223, MIT); Self-RAG critic plus
7B/13B generators (2310.11511, MIT); RAG-Gym process-reward models plus SFT
and DPO actors (2502.13957, license NOASSERTION — clarify before reuse);
RECOMP 110M/775M compressors (2310.04408, MIT, code only); GLiNER zero-shot
NER plus relation head (2311.08526, Apache-2.0, CPU/ONNX-deployable); REBEL
BART-scale triple emitter plus pretraining data (EMNLP 2021, license unclear
— clarify); Granite 3B/8B function-calling models (2407.00121, Apache-2.0,
verify exact 3B variant); Phi-3-mini-4k-instruct (2404.14219, MIT-licensed
weights on HF); APIGen 60k function-calling dataset recipe (2406.18518).
Engines and libraries: SGLang (2312.07104, Apache-2.0); vLLM (2309.06180,
Apache-2.0); llama.cpp with GBNF grammars (https://github.com/ggml-org/llama.cpp,
MIT); LMCache tiered KV store (https://github.com/LMCache/LMCache,
Apache-2.0); Outlines (2307.09702, Apache-2.0); XGrammar (2411.15100,
Apache-2.0); MiniPIC vLLM-fork primitives (2606.13126, Apache-2.0). Memory
and retrieval code: Mem0 (2504.19413, Apache-2.0); Letta/MemGPT
(2310.08560, Apache-2.0); LightRAG (2410.05779, MIT); MiniRAG (2501.06713,
MIT); KAG (2409.13731, Apache-2.0); HippoRAG (2502.14802, MIT); GraphRAG
(2404.16130, MIT, maintenance mode); Cognee (Apache-2.0, no paper);
DocETL (2410.12189, MIT); LOTUS (2407.11418, Apache-2.0); Palimpzest
(2405.14696, MIT); BlendSQL (2402.17882, Apache-2.0, SQLite-only);
RouteLLM (2406.18665, Apache-2.0); Adaptive-RAG router (2403.14403,
Apache-2.0, sub-1B T5-large). Benchmarks and harnesses: MTEB (2210.07316,
Apache-2.0); MMTEB downsampled splits (2502.13595); LongEmbed (2404.12096,
no declared license — reference only); HELMET at 8k/16k (2410.02694, MIT);
BFCL pinned eval commit (PMLR v267; score instability across reruns is
noise); BIRD dev split plus efficiency metric (2305.03111); JSONSchemaBench
(2501.10868); RAGBench plus TRACe metrics (2407.11005); CRAG mock-KG+web
harness (2406.04744); RGB four-ability split (2309.01431); T2-RAGBench
(2506.12071); mmRAG with pinned configs (2505.11180); SemBench (2511.01716).
Blocked from commercial build paths: jina-embeddings-v3 weights
(CC-BY-NC-4.0); NV-Embed weights (CC-BY-NC-4.0); Honcho (AGPL-3.0); Memori
(license unresolved); PathRAG/LeanRAG/ToG/REBEL code (no detected license);
LongEmbed code (no declared license); YuhangWuAI/tablerag (GPL-3.0);
FilCo code (CC-BY-SA-4.0 copyleft — check compatibility).

## 7. Gaps: what nobody has built

1. One-forward-pass paragraph embedding plus grammar-constrained multi-store
op emission at 1–3B, with measured generation degradation — no admitted
precedent; OneGen (2409.05152) is the only one-pass unifier and is 7B with
retrieval tokens, not store ops.
2. Per-store embedding heads over a shared frozen 1–3B decoder with a
filing-quality comparison against separate embedders — closest analogues are
encoder-side (BGE-M3, 2402.03216; jina task-LoRA, 2409.10173).
3. KV-cache composition of cached paragraph states with joint
compression-plus-repair validation at 1–3B on one GPU — CacheGen (2310.07240)
plus C2KV (2607.17715) warn the combination degrades; nobody validates the
stack at small scale.
4. Modular KV reuse for hybrid linear/full-attention small models — HYPIC
(2607.01299) is first PIC for hybrids with no artefact and no small-model
evaluation.
5. A trained 1–3B filing router (graph vs SQL vs Folio vs delegate) with
process supervision — RAG-Gym (2502.13957) proves process supervision wins
but only for search agents at 8B; Toolformer-style (2302.04761)
self-supervision of the store-routing decision is untried.
6. LoRA-vs-full-finetune evidence at exactly 2B for schema emission plus
factual revision — nearest evidence is Biderman et al. (2405.09673) and
Zheng et al. (2608.25677) at other scales.
7. Revise-pass evaluation against best-of-N sampling at equal token budget
for a 2B model — required by 2607.28576, run by nobody in the admitted set.
8. Folio-shaped memory poisoning tests: the two-condition PoisonedRAG test
(2402.07867) and embedding-space trigger transfer (2407.12784) replicated on
file-memory skills rather than RAG corpora.
9. Prompt-embedding attack-surface measurement for PromptEOL/MetaEOL/Echo-
style methods (lane 1 gap, not a requirement).
10. A maintained, license-clean text-to-SQL memory loop for the SQL store —
Vanna and LlamaIndex routers are code-only with secondary-source claims;
CHESS (2405.16755) per-step accuracy with a 2B model is unmeasured.
11. Cross-architecture KV translation for upgrading the harness model without
re-filling stores — Mixture-of-Translators (2607.28979) is abs-only,
future work.
12. Temporal invalidation of filed facts outside vendor-authored Zep/Graphiti
(2501.13956): no independent replication of validity-window retrieval at
small scale.

## 8. Reading order for a maintainer with one day

Morning — the thesis and its bounds: OneGen (2409.05152); GritLM
(2402.09906); DeepRetrieval (2503.00223); Distilling Step-by-Step (ACL
Findings 2023, doi:10.18653/v1/2023.findings-acl.507); HELMET (2410.02694,
the scope limiter). Midday — filing and serving: LOTUS (2407.11418); DocETL
(2410.12189); CacheBlend (2405.16444); EPIC (2410.15332); SGLang
(2312.07104). Afternoon — memory and skills: Mem-alpha (2509.25911);
Self-RAG (2310.11511); RAG-Gym (2502.13957); ACE (2510.04618); Mem0
(2504.19413). Evening — security and fusion: MINJA (2503.03704);
PoisonedRAG (2402.07867); CaMeL (2503.18813); MiniRAG (2501.06713); KAG
(2409.13731). If one more hour: HippoRAG 2 (2502.14802); Qwen3-Embedding
(2506.05176); BlendSQL (2402.17882); TRUSTMEM (2606.25161); Dense X
Retrieval (2312.06648).

## 9. Full inventory

Every screened candidate, sorted by disposition (admit, refute, abstain)
then relevance descending, then name. Columns match `merged/INVENTORY.tsv`:
name, title, year, id, repo, stars, license, artefact, capability,
relevance, disposition, lanes. One-line descriptions and verify-reasons are
in `merged/INVENTORY.tsv` and `merged/SUMMARY.md`; nothing screened was
dropped.

| name | title | year | id | repo | stars | license | artefact | cap | rel | disp | lanes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A-MEM | A-MEM: Agentic Memory for LLM Agents | 2025 | 2502.12110 | https://github.com/agiresearch/A-mem | 1175 | MIT | yes | 2 | 3 | admit | 3,8 |
| ace | Agentic Context Engineering: Evolving Contexts for Self-Improving Language Model | 2025 | 2510.04618 | https://github.com/ace-agent/ace | 1300 (page shows 1.3k) | Apache-2.0 | yes (code) | 5 | 3 | admit | 6 |
| Adaptive-RAG | Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models throug | 2024 | 2403.14403 | https://github.com/starsuzi/Adaptive-RAG | 410 | Apache-2.0 | code only (checkpoints not confirmed) | 2 | 3 | admit | 4,5 |
| Agent-Memory-Database | Is Agent Memory a Database? Rethinking Data Foundations for Long-Term AI Agent M | 2026 | 2605.26252 | -- | -- | -- | unknown | 2 | 3 | admit | 3 |
| agentpoison | AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases | 2024 | 2407.12784 | https://github.com/AI-secure/AgentPoison | 243 | MIT | yes (code) | 5 | 3 | admit | 6 |
| apigen | APIGen: Automated Pipeline for Generating Verifiable and Diverse Function-Callin | 2024 | 2406.18518 | -- | -- | -- | dataset referenced on HF (xlam-function- | 2 | 3 | admit | 7 |
| arctic-embed-2 | Arctic-Embed 2.0: Multilingual Retrieval Without Compromise | 2024 | 2412.04506 | https://github.com/Snowflake-Labs/arctic-embed | 91 | Apache-2.0 | yes (m ~113M non-embedding params; l ~33 | 1 | 3 | admit | 1,9 |
| bfcl | The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic Evalu | 2025 | PMLR-v267:patil25a (no arXiv id) | https://github.com/ShishirPatil/gorilla | 13021 | Apache-2.0 | yes (live leaderboard + bfcl-eval packag | 2 | 3 | admit | 9 |
| BGE-M3 | Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings | 2024 | 2402.03216 | https://github.com/FlagOpen/FlagEmbedding | 12153 | MIT | yes (code + weights) | 1 | 3 | admit | 1,9 |
| BIRD | Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Datab | 2023 | 2305.03111 | -- | -- | -- | unverified | 2 | 3 | admit | 5 |
| BlendSQL | BlendSQL: A Scalable Dialect for Unifying Hybrid Question Answering in Relationa | 2024 | 2402.17882 | https://github.com/parkervg/blendsql | 169 | Apache-2.0 | yes | 2 | 3 | admit | 5 |
| Block-Attention | Block-Attention for Efficient Prefilling | 2024 | 2409.15355 | https://github.com/TemporaryLoRA/Block-Attention | 49 | None stated | code | 3 | 3 | admit | 2 |
| CacheBlend | CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusi | 2024 | 2405.16444 | https://github.com/YaoJiayi/CacheBlend (+ https://github.com | 203 (LMCache 11762) | LMCache: Apache-2.0 | code (research + production LMCache) | 3 | 3 | admit | 2 |
| CacheClip | CacheClip: Accelerating RAG with Effective KV Cache Reuse | 2025 | 2510.10129 | -- | -- | -- | -- | 3 | 3 | admit | 2 |
| CacheGen | CacheGen: KV Cache Compression and Streaming for Fast Large Language Model Servi | 2023 | 2310.07240 | https://github.com/UChi-JCL/CacheGen | 170 | None stated | code | 3 | 3 | admit | 2 |
| CachePrune | CachePrune: Privacy-Aware and Fine-Grained KV Cache Sharing for Efficient LLM In | 2026 | 2605.23640 | -- | -- | -- | -- | 3 | 3 | admit | 2 |
| camel | Defeating Prompt Injections by Design (CaMeL) | 2025 | 2503.18813 | https://github.com/google-research/camel-prompt-injection | 388 | Apache-2.0 | yes (research-artifact code) | 5 | 3 | admit | 6 |
| CHESS | CHESS: Contextual Harnessing for Efficient SQL Synthesis | 2024 | 2405.16755 | https://github.com/ShayanTalaei/CHESS | 281 | Apache-2.0 | yes | 2 | 3 | admit | 5 |
| CRAG | CRAG: Corrective Retrieval Augmented Generation | 2024 | 2401.15884 | https://github.com/HuskyInSalt/CRAG | 470 | not specified | code only (checkpoints not confirmed) | 2 | 3 | admit | 4 |
| critic | CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing | 2023 | 2305.11738 | -- | n/a | n/a | none found | 4 | 3 | admit | 8 |
| DeepRetrieval | DeepRetrieval: Hacking Real Search Engines and Retrievers with Large Language Mo | 2025 | 2503.00223 | https://github.com/pat-jj/DeepRetrieval | 719 | MIT | yes (HF org DeepRetrieval: 3B retrieval/ | 2 | 3 | admit | 4 |
| DimMem | DimMem: Dimensional Structuring for Efficient Long-Term Agent Memory | 2026 | 2605.15759 | https://github.com/ChowRunFa/DimMem | -- | -- | yes | 2 | 3 | admit | 3 |
| DIN-SQL | DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction | 2023 | 2304.11015 | -- | -- | -- | unverified | 2 | 3 | admit | 5 |
| distilling-step-by-step | Distilling Step-by-Step! Outperforming Larger Language Models with Less Training | 2023 | doi:10.18653/v1/2023.findings-acl.507 | -- | -- | -- | no (method only; public benchmarks) | 2 | 3 | admit | 7 |
| distillm | DistiLLM: Towards Streamlined Distillation for Large Language Models | 2024 | 2402.03898 | -- | -- | -- | unverified | 2 | 3 | admit | 7 |
| DocETL | DocETL: Agentic Query Rewriting and Evaluation for Complex Document Processing | 2024 | 2410.12189 | https://github.com/ucbepic/docetl | 4087 | MIT | yes | 2 | 3 | admit | 5 |
| dynamic-cheatsheet | Dynamic Cheatsheet: Test-Time Learning with Adaptive Memory | 2025 | 2504.07952 | https://github.com/suzgunmirac/dynamic-cheatsheet | 276 | MIT | yes (code) | 5 | 3 | admit | 6 |
| E5-Mistral | Improving Text Embeddings with Large Language Models | 2024 | 2401.00368 | https://github.com/microsoft/unilm | 22212 | MIT | yes (E5-mistral-7b-instruct + synthetic  | 1 | 3 | admit | 1,9 |
| Echo / Repetition Improves Language Model Embeddings | Repetition Improves Language Model Embeddings | 2024 | 2402.15449 | -- | n/a | -- | no (method only; no released checkpoint  | 1 | 3 | admit | 1 |
| EmbeddingGemma | Powerful and Lightweight Text Representations | 2025 | 2509.20354 | https://huggingface.co/google/embeddinggemma-300m | n/a (HF 2.1M downloads) | Gemma (gated) | yes (308M weights, quantized/truncated v | 1 | 3 | admit | 1,9 |
| eMEM | eMEM: A Hybrid Spatio-Temporal Memory System For Embodied Agents | 2026 | 2606.03374 | -- | -- | -- | unknown | 2 | 3 | admit | 3 |
| EPIC | EPIC: Efficient Position-Independent Caching for Serving Large Language Models | 2024 | 2410.15332 | https://github.com/DerekHJH/epic | 22 | Apache-2.0 | code | 3 | 3 | admit | 2 |
| Evaporate | Language Models Enable Simple Systems for Generating Structured Views of Heterog | 2023 | 2304.09433 | https://github.com/HazyResearch/evaporate | 498 | unverified | yes | 2 | 3 | admit | 5 |
| expel | ExpeL: LLM Agents Are Experiential Learners | 2024 | 2308.10144 | https://github.com/LeapLabTHU/ExpeL | 240 | Apache-2.0 | yes (code) | 5 | 3 | admit | 6,8 |
| FilCo | FilCo: Learning to Filter Context for Retrieval-Augmented Generation | 2023 | 2311.08377 | https://github.com/zorazrw/filco | 199 | CC-BY-SA-4.0 | code only (checkpoints not confirmed) | 2 | 3 | admit | 4 |
| frugalgpt | FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Pe | 2023 | 2305.05176 | -- | -- | -- | unverified | 2 | 3 | admit | 7 |
| gemma-3 | Gemma 3 Technical Report | 2025 | 2503.19786 | -- | not-fetched | Gemma Terms of Use (weights); paper CC-BY-4.0 | yes (1B/4B/12B/27B) | 2 | 3 | admit | 9 |
| Generative-Agents | Generative Agents: Interactive Simulacra of Human Behavior | 2023 | 2304.03442 | -- | -- | -- | yes (code per paper) | 4 | 3 | admit | 3,6,8 |
| gorilla | Gorilla: Large Language Model Connected with Massive APIs | 2023 | 2305.15334 | https://github.com/ShishirPatil/gorilla | unknown | unverified | code yes (README 200); weights claimed,  | 2 | 3 | admit | 7 |
| granite-function-calling | Granite-Function Calling Model: Introducing Function Calling Abilities via Multi | 2024 | 2407.00121 | -- | -- | -- | weights partially verified (ibm-granite  | 2 | 3 | admit | 7 |
| GraphRAG | From Local to Global: A Graph RAG Approach to Query-Focused Summarization | 2024 | 2404.16130 | https://github.com/microsoft/graphrag | 35949 (GitHub API, fetched 2026-09-12) | MIT | yes (code) | 2 | 3 | admit | 10 |
| GritLM | Generative Representational Instruction Tuning | 2024 | 2402.09906 | https://github.com/ContextualAI/gritlm | 700 | MIT | yes (7B + 8x7B weights, code) | 1 | 3 | admit | 1 |
| GroundedCacheRouting | Grounded Cache Routing for Retrieval-Augmented Generation: When Is It Safe to Re | 2026 | 2605.27494 | -- | -- | -- | -- | 3 | 3 | admit | 2 |
| helmet | HELMET: How to Evaluate Long-Context Language Models Effectively and Thoroughly | 2024 | 2410.02694 | https://github.com/princeton-nlp/HELMET | 227 | MIT | yes (7-category bench + code + data + 59 | 3 | 3 | admit | 9 |
| HijackKV | HijackKV: New Threat in Position-Independent KV Cache Reuse | 2026 | 2607.19957 | https://github.com/YichiCS/KV-Cache-Hijack | 6 | MIT | PoC exploit | 3 | 3 | admit | 2 |
| HippoRAG | HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models | 2024 | 2405.14831 | https://github.com/OSU-NLP-Group/HippoRAG | 3999 | MIT | yes | 2 | 3 | admit | 3,10 |
| HippoRAG-2 | HippoRAG 2 (in: From RAG to Memory: Non-Parametric Continual Learning for Large  | 2025 | 2502.14802 | https://github.com/OSU-NLP-Group/HippoRAG | 3999 | MIT | yes | 2 | 3 | admit | 3,10 |
| HybridRAG | HybridRAG: Integrating Knowledge Graphs and Vector Retrieval Augmented Generatio | 2024 | 2408.04948 | -- | -- | -- | unverified | 2 | 3 | admit | 5 |
| HYPIC | HYPIC: Accelerating Hybrid-Attention LLM Serving with Position-Independent Cachi | 2026 | 2607.01299 | -- | -- | -- | -- | 3 | 3 | admit | 2 |
| ipi | Not what you've signed up for: Compromising Real-World LLM-Integrated Applicatio | 2023 | 2302.12173 | https://github.com/greshake/llm-security | 2100 (page shows 2.1k) | MIT | yes (demo code) | 5 | 3 | admit | 6 |
| jsonschemabench | JSONSchemaBench: A Rigorous Benchmark of Structured Outputs for Language Models | 2025 | 2501.10868 | -- | -- | -- | yes: benchmark+harness (paper claims rel | 2 | 3 | admit | 7 |
| KAG | Boosting LLMs in Professional Domains via Knowledge Augmented Generation | 2024 | 2409.13731 | https://github.com/OpenSPG/KAG | 9048 (GitHub API, fetched 2026-09-12) | Apache-2.0 | yes (code, OpenSPG engine) | 2 | 3 | admit | 10 |
| KaLM-Embedding | Superior Training Data Brings A Stronger Embedding Model | 2025 | 2501.01028 | https://github.com/HITsz-TMG/KaLM-Embedding | 119 | MIT | yes (code + 0.5B Qwen2-based + multiling | 1 | 3 | admit | 1 |
| KVLink | KVLink: Accelerating Large Language Models via Efficient KV Cache Reuse | 2025 | 2502.16002 | https://github.com/UCSB-NLP-Chang/KVLink | 48 | None stated | code | 3 | 3 | admit | 2 |
| KVPacket | KV Packet: Recomputation-Free Context-Independent KV Caching for LLMs | 2026 | 2604.13226 | https://github.com/ChuangtaoChen-TUM/KVPacket | 37 | MIT | code | 3 | 3 | admit | 2 |
| language-models-need-sleep | Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories | 2026 | 2606.03979 | -- | n/a | n/a | none found | 4 | 3 | admit | 8 |
| learning-to-forget | Learning to Forget: Sleep-Inspired Memory Consolidation for Resolving Proactive  | 2026 | 2603.14517 | -- | n/a | n/a | none found | 4 | 3 | admit | 8 |
| lfm2 | LFM2 Technical Report | 2025 | 2511.23404 | -- | not-fetched | open weights (SPDX not-fetched) | yes (350M-2.6B dense, 8.3B MoE, VL/audio | 2 | 3 | admit | 9 |
| LightMem | Lightweight LLM Agent Memory with Small Language Models | 2026 | 2604.07798 | https://github.com/zjunlp/LightMem | -- | -- | yes | 2 | 3 | admit | 3 |
| LightRAG | Simple and Fast Retrieval-Augmented Generation | 2024 | 2410.05779 | https://github.com/HKUDS/LightRAG | ~39300 (search-index snapshot, fetched 2026-09-12) | MIT | yes (code) | 2 | 3 | admit | 10 |
| LLM2Vec | Large Language Models Are Secretly Powerful Text Encoders | 2024 | 2404.05961 | https://github.com/McGill-NLP/llm2vec | 1714 | MIT | yes (code + adapted 1.3B-8B checkpoints) | 1 | 3 | admit | 1 |
| LMCache | LMCache (production KV-cache layer; CacheBlend's serving home) | 2024 | -- | https://github.com/LMCache/LMCache | 11762 | Apache-2.0 | engine (production) | 3 | 3 | admit | 1,2,3,5,6,7,9,10 |
| longembed | LongEmbed: Extending Embedding Models for Long Context Retrieval | 2024 | 2404.12096 | https://github.com/dwzhu-pku/LongEmbed | 148 | none declared | yes (6-task bench + E5-Base-4k + E5-RoPE | 1 | 3 | admit | 9 |
| lora | LoRA: Low-Rank Adaptation of Large Language Models | 2021 | 2106.09685 | -- | -- | -- | unverified (method; implementations ubiq | 2 | 3 | admit | 7 |
| LOTUS | Semantic Operators: A Declarative Model for Rich, AI-based Data Processing | 2024 | 2407.11418 | https://github.com/lotus-data/lotus | 1672 | Apache-2.0 | yes | 2 | 3 | admit | 5 |
| Mem-alpha | Mem-alpha: Learning Memory Construction via Reinforcement Learning | 2025 | 2509.25911 | https://github.com/wangyu-ustc/Mem-alpha | 227 | not specified | unverified (community HF upload YuWangX/ | 2,4 | 3 | admit | 4,8 |
| Mem0 | Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory | 2025 | 2504.19413 | https://github.com/mem0ai/mem0 | 65151 | Apache-2.0 | yes | 2 | 3 | admit | 3,8 |
| Memanto | Memanto: Typed Semantic Memory with Information-Theoretic Retrieval for Long-Hor | 2026 | 2604.22085 | -- | -- | -- | unknown | 2 | 3 | admit | 3 |
| MemGPT | MemGPT: Towards LLMs as Operating Systems | 2023 | 2310.08560 | https://github.com/letta-ai/letta | 24702 | Apache-2.0 | yes | 2 | 3 | admit | 3,8 |
| Memory-R1 | Memory-R1: Enhancing Large Language Model Agents to Manage and Utilize Memories  | 2025 | 2508.19828 | -- | unknown | unknown | no (no code link in paper; no HF hits fo | 2,4 | 3 | admit | 4 |
| MemoryBank | MemoryBank: Enhancing Large Language Models with Long-Term Memory | 2023 | 2305.10250 | -- | -- | -- | yes (code per paper) | 4 | 3 | admit | 3,6,8 |
| MemOS | MemOS: A Memory OS for AI System | 2025 | 2507.03724 | https://github.com/MemTensor/MemOS | 11287 | Apache-2.0 | yes | 2 | 3 | admit | 3,8 |
| MemTX | MemTX: Transactional Belief Commit for Stateful Agent Memory | 2026 | 2607.23929 | -- | -- | -- | unknown | 2 | 3 | admit | 3 |
| minicpm4 | MiniCPM4: Ultra-Efficient LLMs on End Devices | 2025 | 2506.07900 | https://github.com/OpenBMB/MiniCPM | 10313 | Apache-2.0 | yes (0.5B/8B, cdf. CPM.cu, Eagle heads) | 2 | 3 | admit | 9 |
| minillm | MiniLLM: On-Policy Distillation of Large Language Models | 2023 | 2306.08543 | https://github.com/microsoft/LMOps (minillm) | unknown | unverified | yes: code+student models (HF org MiniLLM | 2 | 3 | admit | 7 |
| MiniPIC | MiniPIC: Flexible Position-Independent Caching in <100LOC | 2026 | 2606.13126 | https://github.com/IBM/vllm (vLLM fork) | 27 | Apache-2.0 | code (fork) | 3 | 3 | admit | 2 |
| MiniRAG | Towards Extremely Simple Retrieval-Augmented Generation | 2025 | 2501.06713 | https://github.com/HKUDS/MiniRAG | 1951 (search-index snapshot, fetched 2026-09-12) | MIT | yes (code + LiHua-World on-device benchm | 2 | 3 | admit | 10 |
| minja | Memory Injection Attacks on LLM Agents via Query-Only Interaction (MINJA) | 2025 | 2503.03704 | https://github.com/dsh3n77/MINJA | 37 | MIT | yes (code) | 5 | 3 | admit | 6 |
| MIRIX | MIRIX: Multi-Agent Memory System for LLM-Based Agents | 2025 | 2507.07957 | -- | -- | -- | unknown | 2 | 3 | admit | 3 |
| modernbert | Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder (ModernBERT) | 2024 | 2412.13663 | https://github.com/AnswerDotAI/ModernBERT | 1712 | Apache-2.0 | yes (149M base / 395M large, 8K native) | 1 | 3 | admit | 9 |
| mteb | MTEB: Massive Text Embedding Benchmark | 2022 | 2210.07316 | https://github.com/embeddings-benchmark/mteb | 3420 | Apache-2.0 | yes (benchmark + code + leaderboard) | 1 | 3 | admit | 9 |
| nomic-embed-v1 | Nomic Embed: Training a Reproducible Long Context Text Embedder | 2024 | 2402.01613 | -- | not-fetched | not-fetched | yes (137M; weights + code + data) | 1 | 3 | admit | 9 |
| nomic-embed-v2 | Training Sparse Mixture Of Experts Text Embedding Models (Nomic Embed v2) | 2025 | 2502.07972 | -- (code URL inside paper; not captured) | not-fetched | Apache-2.0 | yes (nomic-embed-text-v2-moe: 475M total | 1 | 3 | admit | 9 |
| NV-Embed | Improved Techniques for Training LLMs as Generalist Embedding Models | 2024 | 2405.17428 | https://huggingface.co/nvidia/NV-Embed-v2 | n/a (HF 23k downloads) | CC-BY-NC-4.0 | yes (v1 + v2 weights, gated) | 1 | 3 | admit | 1 |
| oep | OEP: Poisoning Self-Evolving LLM Agents via Locally Correct but Non-Transferable | 2026 | 2605.18930 | -- | n/a | n/a | none found | 4 | 3 | admit | 8 |
| on-policy-distillation-ag arwal | On-Policy Distillation of Language Models: Learning from Self-Generated Mistakes | 2023 | 2306.13649 | -- | -- | -- | unverified | 2 | 3 | admit | 7 |
| OneGen | Efficient One-Pass Unified Generation and Retrieval for LLMs | 2024 | 2409.05152 | https://github.com/zjunlp/OneGen | 148 | MIT | yes (code + Llama2-7B task models on HF) | 1 | 3 | admit | 1 |
| orca | Orca: Progressive Learning from Complex Explanation Traces of GPT-4 | 2023 | 2306.02707 | -- | -- | -- | no (weights unreleased; flan-style data  | 2 | 3 | admit | 7 |
| orca-2 | Orca 2: Teaching Small Language Models How to Reason | 2023 | 2311.11045 | -- | -- | -- | no (weights unreleased; prompt-strategy  | 2 | 3 | admit | 7 |
| outlines-guided-gen | Efficient Guided Generation for Large Language Models | 2023 | 2307.09702 | https://github.com/dottxt-ai/outlines | 15785 | Apache-2.0 | yes: library (repo API-verified) | 2 | 3 | admit | 7 |
| Palimpzest | A Declarative System for Optimizing AI Workloads | 2024 | 2405.14696 | https://github.com/mitdbg/palimpzest | 238 | MIT | yes | 2 | 3 | admit | 5 |
| phi-3 | Phi-3 Technical Report: A Highly Capable Language Model Locally on Your Phone | 2024 | 2404.14219 | https://github.com/microsoft/phi-3cookbook | unknown | unverified | yes: weights on HF verified (microsoft/P | 2 | 3 | admit | 7 |
| poisonedrag | PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of L | 2024 | 2402.07867 | https://github.com/sleeepeer/PoisonedRAG | 300 | MIT | yes (code) | 5 | 3 | admit | 6 |
| PromptCache | Prompt Cache: Modular Attention Reuse for Low-Latency Inference | 2023 | 2311.04934 | https://github.com/yale-sys/prompt-cache | 114 | MIT | code (prototype) | 3 | 3 | admit | 2 |
| PromptEOL | Scaling Sentence Embeddings with Large Language Models | 2023 | 2307.16645 | https://github.com/kongds/scaling_sentemb | 109 | none listed | yes (code + models per paper) | 1 | 3 | admit | 1 |
| provenance-firewall | Memory Provenance Laundering in LLM Agents: A Non-Amplification Firewall for Per | 2026 | 2607.29167 | -- | n/a | n/a | none found | 4 | 3 | admit | 8 |
| qlora | QLoRA: Efficient Finetuning of Quantized LLMs | 2023 | 2305.14314 | -- | -- | -- | unverified (method) | 2 | 3 | admit | 7 |
| qwen3 | Qwen3 Technical Report | 2025 | 2505.09388 | -- | not-fetched | Apache-2.0 | yes (weights incl. 0.6B/1.7B/4B) | 2 | 3 | admit | 9 |
| Qwen3-Embedding | Advancing Text Embedding and Reranking Through Foundation Models | 2025 | 2506.05176 | https://github.com/QwenLM/Qwen3-Embedding | 2029 | Apache-2.0 | yes (0.6B / 4B / 8B, open) | 1 | 3 | admit | 1,9 |
| RAG-Gym | RAG-Gym: Systematic Optimization of Language Agents for Retrieval-Augmented Gene | 2025 | 2502.13957 | https://github.com/RAG-Gym/RAG-Gym | 127 | NOASSERTION | yes (HF org RAG-Gym: process-reward mode | 2 | 3 | admit | 4 |
| RAGCache | RAGCache: Efficient Knowledge Caching for Retrieval-Augmented Generation | 2024 | 2404.12457 | -- | -- | -- | -- | 3 | 3 | admit | 2 |
| RankRAG | RankRAG: Unifying Context Ranking with Retrieval-Augmented Generation in LLMs | 2024 | 2407.02485 | -- | unknown | unknown | no (no code or weights released) | 2 | 3 | admit | 4 |
| ReCache | ReCache: Efficient KV Cache Reuse and Compression for Tool-Augmented LLM Agents | 2026 | 2608.19662 | https://github.com/EIT-NLP/ReCache | 10 | None stated | code | 3 | 3 | admit | 2 |
| RECOMP | RECOMP: Improving Retrieval-Augmented LMs with Compression and Selective Augment | 2023 | 2310.04408 | https://github.com/carriex/recomp | 149 | MIT | code only (checkpoints not confirmed) | 2 | 3 | admit | 4 |
| Reflexion | Reflexion: Language Agents with Verbal Reinforcement Learning | 2023 | 2303.11366 | -- | -- | -- | yes (code per paper) | 4 | 3 | admit | 3,6,8 |
| REMem | REMem: Reasoning with Episodic Memory in Language Agent | 2026 | 2602.13530 | -- | -- | -- | unknown | 2 | 3 | admit | 3 |
| retain-or-consolidate | Retain or Consolidate? Budget-Dependent Operator Selection for Language Agent Me | 2026 | 2607.17545 | -- | n/a | n/a | none found | 4 | 3 | admit | 8 |
| RouteLLM | RouteLLM: Learning to Route LLMs with Preference Data | 2024 | 2406.18665 | https://github.com/lm-sys/RouteLLM | 5477 | Apache-2.0 | yes | 2 | 3 | admit | 5,7 |
| RouterRetriever | RouterRetriever: Routing over a Mixture of Expert Embedding Models | 2024 | 2409.02685 | https://github.com/amy-hyunji/RouterRetriever | 14 | unverified | yes | 2 | 3 | admit | 5 |
| Search-R1 | Search-R1: Training LLMs to Reason and Leverage Search Engines with Reinforcemen | 2025 | 2503.09516 | https://github.com/PeterGriffinJin/Search-R1 | 5408 | Apache-2.0 | yes (HF org PeterJinGo: Qwen2.5 3B + 7B  | 2 | 3 | admit | 4 |
| Self-RAG | Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | 2023 | 2310.11511 | https://github.com/AkariAsai/self-rag | 2423 | MIT | yes (HF selfrag/selfrag_llama2_7b, _13b, | 2 | 3 | admit | 4,8 |
| SGLang | SGLang: Efficient Execution of Structured Language Model Programs | 2023 | 2312.07104 | https://github.com/sgl-project/sglang | 35834 | Apache-2.0 | engine (production) | 3 | 3 | admit | 2,7 |
| sleep-time-compute | Sleep-time Compute: Beyond Inference Scaling at Test-time | 2025 | 2504.13171 | https://github.com/letta-ai/sleep-time-compute | n/a | n/a | code | 4 | 3 | admit | 8 |
| smollm2 | SmolLM2: When Smol Goes Big -- Data-Centric Training of a Small Language Model | 2025 | 2502.02737 | https://github.com/huggingface/smollm | 3890 | Apache-2.0 | yes (135M/360M/1.7B base+instruct, datas | 2 | 3 | admit | 9 |
| ssgm | Governing Evolving Memory in LLM Agents: Risks, Mechanisms, and the Stability an | 2026 | 2603.11768 | -- | n/a | n/a | none found | 4 | 3 | admit | 8 |
| TableRAG-hetero | TableRAG: A Retrieval Augmented Generation Framework for Heterogeneous Document  | 2025 | 2506.10380 | https://github.com/yxh-y/TableRAG | 143 | unverified | yes | 2 | 3 | admit | 5,10 |
| TableRAG-million | TableRAG: Million-Token Table Understanding with Language Models | 2024 | 2410.04739 | -- | -- | -- | unverified | 2 | 3 | admit | 5,10 |
| toolace | ToolACE: Winning the Points of LLM Function Calling | 2024 | 2409.00920 | -- | -- | -- | code yes per paper; weights unverified ( | 2 | 3 | admit | 7 |
| Toolformer | Toolformer: Language Models Can Teach Themselves to Use Tools | 2023 | 2302.04761 | -- | unknown | unknown | no (no official code or weights released | 2 | 3 | admit | 4,7 |
| trustmem | TRUSTMEM: Learning Trustworthy Memory Consolidation for LLM Agents with Long-Ter | 2026 | 2606.25161 | -- | n/a | n/a | none found | 4 | 3 | admit | 8 |
| TurboRAG | TurboRAG: Accelerating Retrieval-Augmented Generation with Precomputed KV Caches | 2024 | 2410.07590 | https://github.com/MooreThreads/TurboRAG | 102 | None stated | code | 3 | 3 | admit | 2 |
| vLLM-PagedAttention | Efficient Memory Management for Large Language Model Serving with PagedAttention | 2023 | 2309.06180 | https://github.com/vllm-project/vllm | 91532 | Apache-2.0 | engine (production) | 3 | 3 | admit | 2 |
| voyager | Voyager: An Open-Ended Embodied Agent with Large Language Models | 2023 | 2305.16291 | https://github.com/MineDojo/Voyager | 7194 | MIT | yes (code) | 5 | 3 | admit | 6 |
| xgrammar | XGrammar: Flexible and Efficient Structured Generation Engine for Large Language | 2024 | 2411.15100 | https://github.com/mlc-ai/xgrammar | 1881 | Apache-2.0 | yes: engine (repo API-verified) | 2 | 3 | admit | 7 |
| ZenDB | Towards Accurate and Efficient Document Analytics with Large Language Models | 2024 | 2405.04674 | -- | -- | -- | unverified | 2 | 3 | admit | 5 |
| Zep-Graphiti | Zep: A Temporal Knowledge Graph Architecture for Agent Memory | 2025 | 2501.13956 | https://github.com/getzep/zep | 4908 | Apache-2.0 | yes | 2 | 3 | admit | 3,10 |
| agent-drift | Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems Over  | 2026 | 2601.04170 | -- | n/a | n/a | none found | 4 | 2 | admit | 8 |
| Agentic-Context-Cracking | Agentic Context Cracking: Token-Efficient Data Reasoning Agents via Adaptive Str | 2026 | 2608.31082 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| awm | Agent Workflow Memory | 2024 | 2409.07429 | https://github.com/zorazrw/agent-workflow-memory | 468 | Apache-2.0 | yes (code) | 5 | 2 | admit | 6 |
| Beyond-Semantic-Organization | Beyond Semantic Organization: Memory as Execution State Management for Long-Hori | 2026 | 2606.06090 | -- | -- | -- | unknown | 2 | 2 | admit | 3 |
| Binder | Binding Language Models in Symbolic Languages | 2022 | 2210.02875 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| Chain-of-Query | Chain-of-Query: Unleashing the Power of LLMs in SQL-Aided Table Understanding vi | 2025 | 2508.15809 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| Chain-of-Table | Chain-of-Table: Evolving Tables in the Reasoning Chain for Table Understanding | 2024 | 2401.04398 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| ChunkAttention | ChunkAttention: Efficient Self-Attention with Prefix-Aware KV Cache and Two-Phas | 2024 | 2402.15220 | https://github.com/microsoft/chunk-attention | 89 | MIT | code | 3 | 2 | admit | 2 |
| CoinRAG | CoinRAG: Contextualized Information Nugget KV Cache Reuse for Long-Context RAG | 2026 | 2608.07458 | -- | -- | -- | -- | 3 | 2 | admit | 2 |
| Compilation-engine | From Interpretation to Compilation: A Compilation-Based Execution Engine for Sem | 2026 | 2608.06677 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| CRAG | Comprehensive RAG Benchmark | 2024 | 2406.04744 | https://github.com/facebookresearch/CRAG | ~300 (search-index snapshots 288-301, fetched 2026-09-12) | Other (search index; unverified) | yes (4409 QA pairs + 220K pages + 2.6M-e | 2 | 2 | admit | 10 |
| DenseX | Dense X Retrieval: What Retrieval Granularity Should We Use? | 2023 | 2312.06648 | https://github.com/chentong0/factoid-wiki | not fetched (data repo only) | not fetched | partial (proposition-level FactoidWiki d | 2 | 2 | admit | 10 |
| distillm-2 | DistiLLM-2: A Contrastive Approach Boosts the Distillation of LLMs | 2025 | 2503.07067 | -- | -- | -- | unverified | 2 | 2 | admit | 7 |
| dora | DoRA: Weight-Decomposed Low-Rank Adaptation | 2024 | 2402.09353 | -- | -- | -- | unverified (method) | 2 | 2 | admit | 7 |
| episodic-risks | Episodic memory in AI agents poses risks that should be studied and mitigated | 2025 | 2501.11739 | -- | -- | -- | no (position paper) | 5 | 2 | admit | 6 |
| ewc | Overcoming catastrophic forgetting in neural networks | 2016 | 1612.00796 | -- | n/a | n/a | none found | 4 | 2 | admit | 8 |
| fdiv-seqkd | f-Divergence Minimization for Sequence-Level Knowledge Distillation | 2023 | 2307.15190 | -- | -- | -- | unverified | 2 | 2 | admit | 7 |
| FINER-SQL | FINER-SQL: Boosting Small Language Models for Text-to-SQL | 2026 | 2605.03465 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| G-Retriever | Retrieval-Augmented Generation for Textual Graph Understanding and Question Answ | 2024 | 2402.07630 | https://github.com/XiaoxinHe/G-Retriever | 551 (GitHub API, fetched 2026-09-12) | MIT | yes (code + GraphQA benchmark) | 2 | 2 | admit | 10 |
| Gecko | Versatile Text Embeddings Distilled from Large Language Models | 2024 | 2403.20327 | -- | n/a | -- | no (no public weights) | 1 | 2 | admit | 1 |
| Gemini Embedding | Generalizable Embeddings from Gemini | 2025 | 2503.07891 | -- | n/a | -- | no (API only) | 1 | 2 | admit | 1 |
| GLiNER | Generalist Model for Named Entity Recognition using Bidirectional Transformer | 2023 | 2311.08526 | https://github.com/urchade/GLiNER | 3591 (search-index snapshot, fetched 2026-09-12) | Apache-2.0 | yes (code + HF weights; CPU/ONNX-capable | 2 | 2 | admit | 10 |
| GRAG | Graph Retrieval-Augmented Generation | 2024 | 2405.16506 | https://github.com/HuieL/GRAG | 65 (GitHub API, fetched 2026-09-12) | MIT | yes (code + datasets) | 2 | 2 | admit | 10 |
| guided-decoding-rag | Guided Decoding and Its Critical Role in Retrieval-Augmented Generation | 2025 | 2509.06631 | -- | -- | -- | no (study) | 2 | 2 | admit | 7 |
| HAGE | HAGE: Harnessing Agentic Memory via RL-Driven Weighted Graph Evolution | 2026 | 2605.09942 | -- | -- | -- | unknown | 4 | 2 | admit | 3 |
| Harness-the-Memory | Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents | 2026 | 2608.15008 | -- | -- | -- | unknown | 2 | 2 | admit | 3 |
| hindsight | Hindsight is 20/20: Building Agent Memory that Retains, Recalls, and Reflects | 2025 | 2512.12818 | https://github.com/vectorize-io/hindsight | n/a | n/a | code | 4 | 2 | admit | 8 |
| jina-v3 | jina-embeddings-v3: Multilingual Embeddings With Task LoRA | 2024 | 2409.10173 | -- | not-fetched | CC-BY-NC-4.0 | yes (570M, 8K, 5 task LoRAs) | 1 | 2 | admit | 1,9 |
| LeanRAG | Knowledge-Graph-Based Generation with Semantic Aggregation and Hierarchical Retr | 2025 | 2508.10391 | https://github.com/RaZzzyz/LeanRAG | 259 (GitHub API via redirect to KnowledgeXLab/LeanRAG, fetched 2026-09-12) | none detected (API) | yes (code) | 2 | 2 | admit | 10 |
| learning-new-facts-qlora | Learning New Facts with QLoRA: An Acquisition-Retention Frontier | 2026 | 2608.25677 | -- | -- | -- | no (study) | 2 | 2 | admit | 7 |
| loco-m2bert | Benchmarking and Building Long-Context Retrieval Models with LoCo and M2-BERT | 2024 | 2402.07440 | -- | not-fetched | not-fetched | yes (80M M2-BERT, 32K; LoCoV1 12-task be | 1 | 2 | admit | 9 |
| me5 | Multilingual E5 Text Embeddings: A Technical Report | 2024 | 2402.05672 | https://github.com/microsoft/unilm/tree/master/e5 | not-fetched | not-fetched | yes (small/base/large + large-instruct) | 1 | 2 | admit | 9 |
| mela | Mela: Test-Time Memory Consolidation based on Transformation Hypothesis | 2026 | 2605.10537 | https://github.com/Musubi-ai/Mela | n/a | n/a | code | 4 | 2 | admit | 8 |
| MemAgent | MemAgent: Reshaping Long-Context LLM with Multi-Conv RL-based Memory Agent | 2025 | 2507.02259 | https://github.com/BytedTsinghua-SIA/MemAgent | 1106 | Apache-2.0 | yes (HF BytedTsinghua-SIA: RL-MemAgent-1 | 2 | 2 | admit | 4 |
| MemInsight | MemInsight: Autonomous Memory Augmentation for LLM Agents | 2025 | 2503.21760 | -- | -- | -- | unknown | 4 | 2 | admit | 3 |
| MetaEOL | Meta-Task Prompting Elicits Embeddings from Large Language Models | 2024 | 2402.18458 | https://github.com/Yibin-Lei/MetaEOL | 12 | none listed | code only (no checkpoint) | 1 | 2 | admit | 1 |
| minicpm-orig | MiniCPM: Unveiling the Potential of Small Language Models with Scalable Training | 2024 | 2404.06395 | https://github.com/OpenBMB/MiniCPM | 10313 | Apache-2.0 | yes (1.2B/2.4B, DPO/MoE/128K variants) | 2 | 2 | admit | 9 |
| mmRAG | mmRAG: A Modular Benchmark for Retrieval-Augmented Generation over Text, Tables, | 2025 | 2505.11180 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| mmteb | MMTEB: Massive Multilingual Text Embedding Benchmark | 2025 | 2502.13595 | https://github.com/embeddings-benchmark/mteb | 3420 | Apache-2.0 | yes (500+ tasks, 250+ languages, downsam | 1 | 2 | admit | 9 |
| moa | Mixture-of-Agents Enhances Large Language Model Capabilities | 2024 | 2406.04692 | https://github.com/togethercomputer/MoA | unknown | unverified | code yes (README 200) | 2 | 2 | admit | 7 |
| NL-to-semantic-pipelines | Bridge the Last-Mile Gap to Semantic Analytics: Compiling Natural-Language Queri | 2026 | 2606.04641 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| olmo | OLMo: Accelerating the Science of Language Models | 2024 | 2402.00838 | https://github.com/allenai/OLMo | 6675 | Apache-2.0 | yes (1B/7B weights + Dolma data + code + | 2 | 2 | admit | 9 |
| PalimpChat | PalimpChat: Declarative and Interactive AI analytics | 2025 | 2502.03368 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| PathRAG | Pruning Graph-Based Retrieval Augmented Generation with Relational Paths | 2025 | 2502.14902 | https://github.com/BUPT-GAMMA/PathRAG | 377 (GitHub API, fetched 2026-09-12) | none detected (API) | yes (code) | 2 | 2 | admit | 10 |
| phi-4-mini | Phi-4-Mini Technical Report: Compact yet Powerful Multimodal Language Models via | 2025 | 2503.01743 | -- | not-fetched | not-fetched | yes (3.8B LM + multimodal) | 2 | 2 | admit | 9 |
| R1-Searcher | R1-Searcher: Incentivizing the Search Capability in LLMs via Reinforcement Learn | 2025 | 2503.05592 | https://github.com/RUCAIBox/R1-Searcher | 725 | MIT | no (no official HF checkpoint found) | 2 | 2 | admit | 4 |
| R1-Searcher++ | R1-Searcher++: Incentivizing the Dynamic Knowledge Acquisition of LLMs via Reinf | 2025 | 2505.17005 | https://github.com/RUCAIBox/R1-Searcher-plus | 82 | MIT | no (no official HF checkpoint found) | 2 | 2 | admit | 4 |
| RA-DIT | RA-DIT: Retrieval-Augmented Dual Instruction Tuning | 2023 | 2310.01352 | https://github.com/facebookresearch/RA-DIT | 3 | NOASSERTION | none found (code repo exists but nearly  | 2 | 2 | admit | 4,7 |
| RAGBench | Explainable Benchmark for Retrieval-Augmented Generation Systems | 2024 | 2407.11005 | -- (dataset-only; HF rungalileo/ragbench) | n/a | n/a | yes (100k-example dataset + TRACe metric | 2 | 2 | admit | 10 |
| RAPTOR | Recursive Abstractive Processing for Tree-Organized Retrieval | 2024 | 2401.18059 | https://github.com/parthsarthi03/RAPTOR | 1704 (search-index snapshot, fetched 2026-09-12) | MIT | yes (code) | 2 | 2 | admit | 10 |
| ReAcTable | ReAcTable: Enhancing ReAct for Table Question Answering | 2023 | 2310.00815 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| REBEL | Relation Extraction By End-to-end Language generation | 2021 | DOI 10.18653/v1/2021.findings-emnlp.204 | https://github.com/Babelscape/rebel | 576 (GitHub API, fetched 2026-09-12) | none detected (API) | yes (weights + REBEL pretraining dataset | 2 | 2 | admit | 10 |
| recursive-self-refinement | Do Language Models Converge to Themselves? Recursive Self-Refinement as Textual  | 2026 | 2607.22653 | -- | n/a | n/a | none found | 4 | 2 | admit | 8 |
| ReSearch | ReSearch: Learning to Reason with Search for LLMs via Reinforcement Learning | 2025 | 2503.19470 | https://github.com/Agent-RL/ReSearch (renamed to Agent-RL/Re | 1434 | MIT | no (no official HF checkpoint found) | 2 | 2 | admit | 4 |
| RGB | Benchmarking Large Language Models in Retrieval-Augmented Generation | 2023 | 2309.01431 | https://github.com/chen700564/RGB | repo exists; count not fetched | not fetched | yes (code + EN/ZH data files) | 2 | 2 | admit | 10 |
| Schema-First-Retrieval | Schema-First Retrieval: Embedding Catalogs for Natural Language Analytics | 2026 | 2606.28387 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| self-refine | Self-Refine: Iterative Refinement with Self-Feedback | 2023 | 2303.17651 | -- | n/a | n/a | none found | 4 | 2 | admit | 8 |
| SemBench | SemBench: A Benchmark for Semantic Query Processing Engines | 2025 | 2511.01716 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| seqkd | Sequence-Level Knowledge Distillation | 2016 | 1606.07947 | -- | -- | -- | no (method only) | 2 | 2 | admit | 7 |
| SGPT | GPT Sentence Embeddings for Semantic Search | 2022 | 2202.08904 | https://github.com/Muennighoff/sgpt | 872 | MIT | yes (code + 125M-5.8B checkpoints) | 1 | 2 | admit | 1 |
| SimpleMem | SimpleMem: Efficient Lifelong Memory for LLM Agents | 2026 | 2601.02553 | https://github.com/aiming-lab/SimpleMem | 3754 | MIT | yes | 2 | 2 | admit | 3 |
| sleeping-agent | The Sleeping Agent: What Gist-Based Context Compression Loses and Why | 2026 | 2608.11775 | https://github.com/kyrkewood/sleeping-agent | n/a | n/a | code | 4 | 2 | admit | 8 |
| slm-agentic-survey | Small Language Models for Agentic Systems: A Survey of Architectures, Capabiliti | 2025 | 2510.03847 | -- | -- | -- | no (survey) | 2 | 2 | admit | 7 |
| sop-agent | SOP-Agent: Empower General Purpose AI Agent with Domain-Specific SOPs | 2025 | 2501.09316 | -- | -- | -- | no | 5 | 2 | admit | 6 |
| speculative-kd | Speculative Knowledge Distillation: Bridging the Teacher-Student Gap Through Int | 2024 | 2410.11325 | -- | -- | -- | unverified | 2 | 2 | admit | 7 |
| SQuaD-SQL | SQuaD-SQL: Efficient Text-to-SQL with Small Language Models via LLM-Guided Knowl | 2026 | 2607.08161 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| STaR | STaR: Bootstrapping Reasoning With Reasoning | 2022 | 2203.14465 | -- | unknown | unknown | no (no official code or weights released | 2 | 2 | admit | 4 |
| streaming-llm | Efficient Streaming Language Models with Attention Sinks | 2023 | 2309.17453 | https://github.com/mit-han-lab/streaming-llm | n/a | n/a | code | 4 | 2 | admit | 8 |
| StructGPT | StructGPT: A General Framework for Large Language Model to Reason over Structure | 2023 | 2305.09645 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| StructMem | StructMem: Structured Memory for Long-Horizon Behavior in LLMs | 2026 | 2604.21748 | https://github.com/zjunlp/LightMem | -- | -- | yes | 4 | 2 | admit | 3 |
| StructRAG | Boosting Knowledge Intensive Reasoning of LLMs via Inference-time Hybrid Informa | 2024 | 2410.08815 | https://github.com/icip-cas/StructRAG | ~170 (search-index snapshots 161-171, fetched 2026-09-12) | not fetched | yes (code; DPO-trained router) | 2 | 2 | admit | 10 |
| SubgraphRAG | Simple is Effective: The Roles of Graphs and Large Language Models in Knowledge- | 2024 | 2410.20724 | https://github.com/Graph-COM/SubgraphRAG | 185 (GitHub API, fetched 2026-09-12) | MIT | yes (code) | 2 | 2 | admit | 10 |
| T2-RAGBench | T2-RAGBench: Text-and-Table Benchmark for Evaluating Retrieval-Augmented Generat | 2025 | 2506.12071 | -- | -- | -- | unverified | 2 | 2 | admit | 5 |
| Think-on-Graph | Deep and Responsible Reasoning of Large Language Model on Knowledge Graph | 2023 | 2307.07697 | https://github.com/IDEA-FinAI/ToG | 659 (GitHub API, fetched 2026-09-12) | none detected (API) | yes (code) | 2 | 2 | admit | 10 |
| timem | TiMem: Temporal-Hierarchical Memory Consolidation for Long-Horizon Conversationa | 2026 | 2601.02845 | https://github.com/TiMEM-AI/timem | n/a | n/a | code | 4 | 2 | admit | 8 |
| titans | Titans: Learning to Memorize at Test Time | 2024 | 2501.00663 | -- | n/a | n/a | none found | 4 | 2 | admit | 8 |
| where-vs-what | Where vs What: Decomposing Structural and Content Failures in LLM-Generated Stru | 2026 | 2608.25358 | -- | -- | -- | no (study) | 2 | 2 | admit | 7 |
| whp-unlearning | Who's Harry Potter? Approximate Unlearning in LLMs | 2023 | 2310.02238 | -- | n/a | n/a | none found | 4 | 2 | admit | 8 |
| AnglE | AnglE-optimized Text Embeddings | 2023 | 2309.12871 | https://github.com/SeanLee97/AnglE | 573 | MIT | yes (code + checkpoints) | 1 | 1 | admit | 1 |
| E5 | Text Embeddings by Weakly-Supervised Contrastive Pre-training | 2022 | 2212.03533 | https://github.com/microsoft/unilm | 22212 | MIT | yes (checkpoints + CCPairs recipe) | 1 | 1 | admit | 1 |
| Episodic-Semantic-Scientific | Episodic-Semantic Memory Architecture for Long-Horizon Scientific Agents | 2026 | 2605.17625 | -- | -- | -- | unknown | 2 | 1 | admit | 3 |
| function-tokens | Memory Retrieval and Consolidation in Large Language Models through Function Tok | 2025 | 2510.08203 | -- | n/a | n/a | none found | 4 | 1 | admit | 8 |
| human-like-recall | My agent understands me better: Integrating Dynamic Human-like Memory Recall and | 2024 | 2404.00573 | -- | n/a | n/a | none found | 4 | 1 | admit | 8 |
| inms | INMS: Memory Sharing for Large Language Model based Agents | 2024 | 2404.09982 | -- | -- | -- | no | 5 | 1 | admit | 6 |
| Larch | Larch: Learned Query Optimization for Semantic Predicates | 2026 | 2606.07923 | -- | -- | -- | unverified | 2 | 1 | admit | 5 |
| lifealign | LifeAlign: Lifelong Alignment for Large Language Models with Memory-Augmented Fo | 2025 | 2509.17183 | https://github.com/real-ljs/LifeAlign | n/a | n/a | code | 4 | 1 | admit | 8 |
| Listwise-memory-text-to-SQL | Replacing Training with Memory: Listwise Selection for Text-to-SQL | 2026 | 2609.00834 | -- | -- | -- | unverified | 2 | 1 | admit | 5 |
| LoRA-tradeoffs-text-to-SQL | How Small Can You Go? A Controlled Study of LoRA Rank, Target Modules, and Quant | 2026 | 2607.25583 | -- | -- | -- | unverified | 2 | 1 | admit | 5 |
| memgas | From Single to Multi-Granularity: Toward Long-Term Memory Association and Select | 2025 | 2505.19549 | https://github.com/quqxui/MemGAS | n/a | n/a | code | 4 | 1 | admit | 8 |
| memory-mechanism-survey | A Survey on the Memory Mechanism of Large Language Model based Agents | 2024 | 2404.13501 | https://github.com/nuster1128/LLM_Agent_Memory_Survey | unknown | unknown | data-only (survey repo) | 5 | 1 | admit | 6 |
| Multi-objective-rewrites | Multi-Objective Agentic Rewrites for Unstructured Data Processing | 2025 | 2512.02289 | -- | -- | -- | unverified | 2 | 1 | admit | 5 |
| Multi-turn-text-to-SQL-memory | Memory Architectures for Multi-Turn Text-to-SQL: A Benchmark and Empirical Study | 2026 | 2605.26394 | -- | -- | -- | unverified | 2 | 1 | admit | 5 |
| Omni-SimpleMem | Omni-SimpleMem: Autoresearch-Guided Discovery of Lifelong Multimodal Agent Memor | 2026 | 2604.01007 | https://github.com/aiming-lab/SimpleMem | 3754 | MIT | yes | 4 | 1 | admit | 3 |
| Ontology-RAG-from-RDBs | Retrieval-Augmented Generation of Ontologies from Relational Databases | 2025 | 2506.01232 | -- | -- | -- | unverified | 2 | 1 | admit | 5 |
| prompt-injection-liu | Prompt Injection attack against LLM-integrated Applications | 2023 | 2306.05499 | -- | -- | -- | no | 5 | 1 | admit | 6 |
| RUBICON | RUBICON: Agentic AI for Messy Enterprise Data | 2026 | 2604.21413 | -- | -- | -- | unverified | 2 | 1 | admit | 5 |
| signed-prompt | Signed-Prompt: A New Approach to Prevent Prompt Injection Attacks Against LLM-In | 2024 | 2401.07612 | -- | -- | -- | no | 5 | 1 | admit | 6 |
| Small-LMs-for-large-DBs | Large Databases Need Small, Open-Weight Language Models | 2026 | 2606.31808 | -- | -- | -- | unverified | 2 | 1 | admit | 5 |
| Type-rules | Play by the Type Rules: Inferring Constraints for LLM Functions in Declarative P | 2025 | 2509.20208 | -- | -- | -- | unverified | 2 | 1 | admit | 5 |
| VikingRAG | VikingRAG: Accurate and Token-efficient Retrieval-augmented Generation over Stru | 2026 | 2609.11390 | -- | -- | -- | unverified | 2 | 1 | admit | 5 |
| lora-learns-less | LoRA Learns Less and Forgets Less | 2024 | 2405.09673 | -- | -- | -- | no (study) | refutes | 3 | refute | 7 |
| ReFind | When Your Agent Opens the Chat App: Agent-Controlled Search over Raw Chat Logs R | 2026 | 2608.12888 | -- | -- | -- | unknown | refutes | 3 | refute | 3 |
| repair-not-improvement | Repair, Not Improvement: Decomposing Constrained Decoding in Tool-Call Abstentio | 2026 | 2608.13959 | -- | -- | -- | no (study) | refutes | 3 | refute | 7 |
| sample-more-reflect-less | Sample More, Reflect Less: Self-Refine and Reflexion Lose to Repeated Sampling a | 2026 | 2607.28576 | -- | n/a | n/a | none found | refutes | 3 | refute | 8 |
| cannot-self-correct | Large Language Models Cannot Self-Correct Reasoning Yet | 2023 | 2310.01798 | -- | n/a | n/a | none found | refutes | 2 | refute | 8 |
| Memo-Not-Memory | Contextual Agentic Memory is a Memo, Not True Memory | 2026 | 2604.27707 | -- | -- | -- | unknown | refutes | 2 | refute | 3 |
| Reproducing-LightMem | Reproducing LightMem: Naive RAG Is Just as Good for Memory Management | 2026 | 2607.29104 | https://github.com/ielab/Reproducing-LightMem | -- | -- | yes | refutes | 2 | refute | 3 |
| rethinking-moa | Rethinking Mixture-of-Agents: Is Mixing Different Large Language Models Benefici | 2025 | 2502.00674 | -- | -- | -- | no (study) | refutes | 2 | refute | 7 |
| Useful-Memories-Faulty | Useful Memories Become Faulty When Continuously Updated by LLMs | 2026 | 2605.12978 | -- | -- | -- | unknown | refutes | 2 | refute | 3 |
| great-models-think-alike | Great Models Think Alike and this Undermines AI Oversight | 2025 | 2502.04313 | -- | -- | -- | no (study) | refutes | 1 | refute | 7 |
| AgentKVShift | AgentKVShift: Efficient KV Cache Reuse for Agentic Memory Systems | 2026 | 2607.21604 | -- | -- | -- | -- | 3 | 2 | abstain | 2 |
| C2KV | C2KV: Compressed and Composable KV Cache Reuse for Efficient LLM Inference | 2026 | 2607.17715 | https://github.com/s7a9/C2KV | 10 | None stated | -- | 3 | 2 | abstain | 2 |
| CacheProbe | CacheProbe: Auditing Prompt Cache Isolation in Gateway APIs | 2026 | 2605.30613 | -- | -- | -- | -- | 3 | 2 | abstain | 2 |
| DAF | Decoupled Attention Fusion: Accelerating RAG with Efficient KV Cache Reuse | 2026 | 2607.21599 | -- | -- | -- | -- | 3 | 2 | abstain | 2 |
| Hydra | Unifying Document Retrieval and Generation in a Single Vision-Language Model | 2026 | 2603.28554 | -- | n/a | -- | -- | 1 | 2 | abstain | 1 |
| KeyPooling | KeyPooling: Measuring Where LLM API Relay Paths Collapse Prompt Cache Isolation | 2026 | 2608.17485 | -- | -- | -- | -- | 3 | 2 | abstain | 2 |
| LLM2Vec-Gen | Generative Embeddings from Large Language Models | 2026 | 2603.10913 | -- | n/a | -- | -- | 1 | 2 | abstain | 1 |
| MoT | Mixture-of-Translators: Translating KV Caches Across Heterogeneous LLMs | 2026 | 2607.28979 | -- | -- | -- | -- | 3 | 2 | abstain | 2 |
| ProbingDispensable | Probing the Prompt KV Cache: Where It Becomes Dispensable | 2026 | 2605.30574 | -- | -- | -- | -- | 3 | 2 | abstain | 2 |
| SparseX | SparseX: Efficient Segment-Level KV Cache Sharing for Interleaved LLM Serving | 2026 | 2606.01751 | -- | -- | -- | -- | 3 | 2 | abstain | 2 |
| TokenDance | TokenDance: Scaling Multi-Agent LLM Serving via Collective KV Cache Sharing | 2026 | 2604.03143 | -- | -- | -- | -- | 3 | 2 | abstain | 2 |
| ActiveRAG | Active Retrieval Augmented Generation | 2023 | 2305.06983 | -- | unknown | unknown | n/a (prompting only, nothing trained) | 2 | 1 | abstain | 4 |
| AdapShot | AdapShot: Adaptive Many-Shot In-Context Learning with Semantic-Aware KV Cache Re | 2026 | 2605.03644 | -- | -- | -- | -- | 3 | 1 | abstain | 2 |
| arctic-embed-1 | Arctic-Embed: Scalable, Efficient, and Accurate Text Embedding Models | 2024 | 2405.05374 | https://github.com/Snowflake-Labs/arctic-embed | 91 | Apache-2.0 | yes (22M-334M suite) | 1 | 1 | abstain | 9 |
| BlockSegDistill | Towards Generalization of Block Attention via Automatic Segmentation and Block D | 2026 | 2605.15913 | -- | -- | -- | -- | 3 | 1 | abstain | 2 |
| CanIBuyKV | Can I Buy Your KV Cache? | 2026 | 2606.13361 | -- | -- | -- | -- | 3 | 1 | abstain | 2 |
| Contriever | Unsupervised Dense Information Retrieval with Contrastive Learning | 2021 | 2112.09118 | https://github.com/facebookresearch/contriever | 779 | NOASSERTION | -- | 1 | 1 | abstain | 1 |
| DSPy | DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines | 2023 | 2310.03714 | not verified this session | unknown | unknown | n/a (optimizes prompts, not weights) | 2 | 1 | abstain | 4 |
| FluxMem | Rethinking Memory as Continuously Evolving Connectivity (FluxMem) | 2026 | 2605.28773 | https://github.com/zjunlp/LightMem | -- | -- | no | 4 | 1 | abstain | 3 |
| KVShareArena | KVShareArena: KV-Cache Reuse Across Contexts and Model Checkpoints | 2026 | 2609.10266 | -- | -- | -- | -- | 3 | 1 | abstain | 2 |
| LinearKV | LinearKV: One Cached State Suffices for Position-Independent Caching in Hybrid L | 2026 | 2608.11231 | -- | -- | -- | -- | 3 | 1 | abstain | 2 |
| MemDelta | MemDelta: Controlled Baselines and Hidden Confounds in Agent Memory Evaluation | 2026 | 2606.29914 | -- | -- | -- | unknown | 2 | 1 | abstain | 3 |
| nemotron-h | Nemotron-H: A Family of Accurate and Efficient Hybrid Mamba-Transformer Models | 2025 | 2504.03624 | -- | not-fetched | not-fetched (paper CC-BY-4.0) | yes (8B/56B) | 3 | 1 | abstain | 9 |
| nemotron-nano-2 | NVIDIA Nemotron Nano 2: An Accurate and Efficient Hybrid Mamba-Transformer Reaso | 2025 | 2508.14444 | -- | not-fetched | not-fetched | yes (9B + 12B base + datasets) | 2 | 1 | abstain | 9 |
| ObjectCache | ObjectCache: Layerwise Object-Storage Retrieval for KV Cache Reuse | 2026 | 2605.22850 | -- | -- | -- | -- | 3 | 1 | abstain | 2 |
| olmo-2 | 2 OLMo 2 Furious | 2025 | 2501.00656 | https://github.com/allenai/OLMo | 6675 | Apache-2.0 | yes (7B/13B/32B + Dolmino Mix + RLVR) | 2 | 1 | abstain | 9 |
| PCR | PCR: A Prefetch-Enhanced Cache Reuse System for Low-Latency RAG Serving | 2026 | 2603.23049 | -- | -- | -- | -- | 3 | 1 | abstain | 2 |
| ProGraph | Profile-Graph Memory for LLM Agents (ProGraph) | 2026 | 2607.19359 | https://github.com/ShengtongZhu/ProGraph | 1 | MIT | yes | 2 | 1 | abstain | 3 |
| ReST | Reinforced Self-Training (ReST) for Language Modeling | 2023 | 2308.08998 | -- | unknown | unknown | no | 2 | 1 | abstain | 4 |
| Search-o1 | Search-o1: Agentic Search-Enhanced Large Reasoning Models | 2025 | 2501.05366 | https://github.com/RUC-NLPIR/Search-o1 | 1244 | MIT | n/a (inference framework, nothing traine | 2 | 1 | abstain | 4 |
| SF-AMS | SF-AMS: Strategic Forgetting for Structured Memory in LLM Agent | 2026 | 2607.22562 | -- | -- | -- | unknown | 4 | 1 | abstain | 3 |
| StructRAG-scholarly | Structure-Aware RAG Framework with Scholarly Knowledge Graph for Diverse Questio | 2025 | DOI 10.1145/3701716.3717819 | -- (implementation link w3id.org/kgcp/DPFusion seen but not  | not fetched | not fetched | unknown | 2 | 1 | abstain | 10 |
| UniversalReuse | A Universal Context-Reuse Layer for Cross-Model KV Sharing | 2026 | 2608.30963 | -- | -- | -- | -- | 3 | 1 | abstain | 2 |
| badchain | BadChain (backdoor chain-of-thought prompting; cited in AgentPoison) | -- | recalled id 2405.04619 is WRONG (that id is a physics paper) | -- | -- | -- | no | 5 | 0 | abstain | 6 |
| dora-wrong-id | DoRA (recalled id 2402.10974) | -- | 2402.10974 | -- | -- | -- | -- | 2 | 0 | abstain | 7 |
| dss-wrong-ids | Distilling Step-by-Step (recalled ids 2305.10586 / 2305.10688) | -- | 2305.10586 | -- | -- | -- | -- | 2 | 0 | abstain | 7 |
| expel-misid | The Feasibility of Electric Air Taxis (misidentified as ExpeL) | 2023 | 2310.01417 | -- | n/a | n/a | none found | 4 | 0 | abstain | 8 |
| gemma-1 | Gemma: Open Models Based on Gemini Research and Technology | 2024 | 2403.08295 | -- | not-fetched | not-fetched | yes (2B/7B) | 2 | 0 | abstain | 9 |
| h2o-eviction | H2O Heavy-Hitter Oracle KV-cache eviction | 2023 | unknown | -- | n/a | n/a | none found | 4 | 0 | abstain | 8 |
| human-memory-framework | A Framework for Inference Inspired by Human Memory Mechanisms | 2023 | 2310.09297 | -- | n/a | n/a | none found | 4 | 0 | abstain | 8 |
| memory-poisoning-2026-cluster | 2026 memory-poisoning preprints (e.g. MAFIA; Transferable End-to-End Optimizatio | 2026 | see method.md | -- | -- | -- | no | 5 | 0 | abstain | 6 |
| minillm-wrong-id | MiniLLM (recalled id 2312.13344) | -- | 2312.13344 | -- | -- | -- | -- | 2 | 0 | abstain | 7 |
| outlines-wrong-id | Outlines (recalled id 2307.06960) | -- | 2307.06960 | -- | -- | -- | -- | 2 | 0 | abstain | 7 |
| radit-wrong-id | RA-DIT (recalled id 2309.17402) | -- | 2309.17402 | -- | -- | -- | -- | 2 | 0 | abstain | 7 |

## 10. Method

Which queries, which sources, how many screened per lane, what failed.
Per-lane detail is in `lanes/<n>/method.md`; this is the assembly.

Common pattern across lanes: arXiv abs pages plus PDFs as the primary source
for every admitted paper (PDFs fetched from `https://arxiv.org/pdf/<id>` and
`%PDF`-verified; titles confirmed at `https://arxiv.org/abs/<id>`); GitHub
REST API plus repo pages for code facts (stars, push date, license); Hugging
Face Hub API for weights/license facts; vendor blogs and leaderboard pages as
secondary sources only, never as admit evidence. Semantic Scholar citation
chaining as specified in the brief failed in every lane (HTTP 429 without an
API key); forward/backward chaining was approximated with arXiv related-title
search plus related-work mining from fetched papers. The arXiv export API
rate-limited intermittently in most lanes and was replaced with per-id abs-
page fetches. The Papers with Code API returned no usable responses. No
recalled arXiv id was trusted: eight wrong recalls were caught by opening abs
pages and are recorded in the lane ledgers (not cited).

Per-lane screened and admitted counts (lane TSV rows; unique items after
cross-lane dedup: 280 from 364 rows):

- Lane 1 (unified embedding+generation): 27 screened, 17 admitted.
`export.arxiv.org` blocked early, so all verification used direct abs-page
fetches; two guessed ids corrected, two rejected as wrong-paper collisions.
GitHub API for 13 repos; HF API for 5 weight sets. Failed: Semantic Scholar
429 (no citation chaining); NV-Embed has no GitHub repo; SFR-Embedding-Mistral
has no paper; Echo has no official code.
- Lane 2 (KV-cache reuse): 43 screened, 24 admitted (20 papers with PDFs, 4
code-only engines). 10 arXiv API queries plus 32 abs-page fetches plus 19
paper-HTML repo-URL extractions plus 19 GitHub API lookups. Failed: arXiv API
429 after ~8 queries; Semantic Scholar fully 429; Papers with Code dead;
GitHub code search poor for academic repos (resolved via paper HTML); no
public repo for RAGCache, HYPIC, CacheClip, Grounded Cache Routing,
CachePrune, CoinRAG (recorded as missing, not invented). 13 of 20 admitted
papers are 2026 preprints: abs-verified but unreplicated.
- Lane 3 (typed memory stores): 45 screened, 34 admitted (26 papers + 8
code-only systems, 4 overlapping), 4 refuted. One working arXiv API query
(all:"agent memory system", 50 results) before throttling, then abs pages
(23 ids) plus 4 arXiv HTML search pages plus GitHub search and 15 repo
metadata fetches. Failed: Semantic Scholar 429 on every call; arXiv API
empty after first query; two brief-implied ids corrected (2306.03609 is not
Generative Agents; 2606.29914 is MemDelta).
- Lane 4 (small models deciding retrieval): 22 screened, 18 admitted. arXiv
API phrase queries plus 8 targeted web searches plus 22 abs-page fetches
plus ar5iv full-text mining plus 17 GitHub and 9 Hugging Face Hub lookups.
Failed: Semantic Scholar 429; ~4 arXiv API empties; ar5iv has no MemAgent
render (repo README used instead); RankRAG, Memory-R1, STaR, Toolformer have
no released code/weights (recipe-only); Mem-alpha weights only as an
unverified community upload.
- Lane 5 (documents to tables/SQL): 57 rows screened, 52 admitted (40 papers
with PDFs + 12 code artefacts), 5 abstained. ~30 arXiv queries (quoted-phrase
`all:"..."` silently matches nothing; reran bare) plus 3 id_list verification
batches (caught 3 wrong recalled ids) plus ~15 GitHub search queries and per-
repo metadata reads plus 2 abs-page opens. Failed: Semantic Scholar 429;
Papers with Code dead; only Adaptive-RAG's venue verified (rest recorded as
arXiv preprint, not recalled); TAG/DATER unconfirmable within budget.
- Lane 6 (skills + security): 27 screened, 20 admitted (19 papers + 1 spec).
arXiv API queries plus one bulk id_list verification (caught a BadChain id
misrecall: 2405.04619 is a physics paper) plus one successful Semantic
Scholar references call (MINJA references, surfaced 4 admits) plus web
search plus GitHub API then page-fetch fallback after quota exhaustion.
PDF repo URLs extracted from PDF bytes. Failed: S2 citation call for ExpeL
429; GitHub API quota hit mid-lane (8 repos lack push dates, recorded
unknown); no primary source for MemFS; no verified BadChain/Progent ids.
- Lane 7 (small vs frontier + distillation): 45 screened, 36 verified
admits/refutes (35 PDFs + 1 code-only), 9 abstained. ~21 arXiv API queries
then abs pages plus OpenAlex (~50 title queries, citation counts) after the
429; GitHub API for 3 repos then README-fetch fallback; Hugging Face API for
5 artefacts. Failed: Semantic Scholar 100% 429; GitHub quota after 3 calls
(4 repos lack star counts); 8 brief/recall ids wrong on fetch (corrected or
abstained); XGrammar-2 and Trie-Automata sighted but unverified; no study at
exactly 2B for LoRA-vs-full (gap stated explicitly).
- Lane 8 (consolidation loops): 40 screened, 34 admitted, 2 refuted, 4
abstained. arXiv API queries plus per-id abs fetches for all 40 plus PDF
`strings`-mined repo links plus GitHub API until the 60-req/hr limit, then
HTTP existence checks (15 repos lack stars/licenses, marked n/a). Failed:
Semantic Scholar 429; two recalled ids wrong (caught via abs pages);
recalled names without sources (RMM, H2O id) abstained; most novel 2026
consolidation results are codeless single-cluster preprints (treated as
design patterns unless they had code or a reusable mechanism).
- Lane 9 (on-device models + small embedders): 33 screened, 27 admitted (23
arXiv PDFs + 1 proceedings-only benchmark + 2 repo/card-only releases), 7
refuted/abstained rows. 18 rounds of web search plus arXiv abs/full-paper
fetches plus GitHub API and pages plus HF cards plus PMLR/ACL Anthology
venue checks. Failed: arXiv export API empty over shell curl (abs pages
instead); GitHub API rate-limited after ~6 calls (fields marked not-fetched);
S2 chaining not used (same egress limits; paper reference sections instead);
six papers lack full author lists (noted per row).
- Lane 10 (graph/vector/relational fusion): 25 screened, 24 admitted (22
arXiv PDFs + 1 ACL PDF + 1 code-only), 1 abstained. ~30 web-search queries
plus 8 direct abs fetches plus 23 PDFs (all HTTP 200, `%PDF`-verified) plus
proceedings/DOI pages plus GitHub API (paced, 10–20 s sleeps) with webfetch
and search-snapshot fallbacks. Failed: arXiv export API 429/empty all
session; Semantic Scholar 429 all session; GitHub API intermittent 403
windows (cells marked not fetched); one name collision (two StructRAGs —
the scholarly one abstained); REBEL has no arXiv version (ACL PDF filed,
documented deviation).

Refresh priorities if this is re-run: verify XGrammar-2 (2601.04426) and
Trie-Automata decoding (2608.12574); open the 2026 poisoning preprints
(MAFIA and transferable-indirect-poisoning cluster); fill not-fetched repo
cells; run a second Semantic Scholar pass with an API key for the citation
chaining this report lacked; replicate DAF-vs-CacheBlend and Reproducing-
LightMem before depending on either side.
