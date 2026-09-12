# Merge summary

Rows read: 364 across 10 lanes ({'1': 27, '2': 43, '3': 45, '4': 22, '5': 57, '6': 27, '7': 45, '8': 40, '9': 33, '10': 25}). Unique items after dedup: 280. Dispositions: {'admit': 226, 'refute': 10, 'abstain': 44}. Admitted PDFs staged: 240. Malformed rows skipped: 0.

## Admitted, by relevance

| relevance | lanes | title | id / repo | one line |
|---|---|---|---|---|
| 3 | 5 | A Declarative System for Optimizing AI Workloads | 2405.14696 | Declarative AI pipelines over unstructured data with a cost/quality optimizer. |
| 3 | 3,8 | A-MEM: Agentic Memory for LLM Agents | 2502.12110 | Zettelkasten-style evolving notes where the agent builds links and descriptions without fixed schema. |
| 3 | 7 | APIGen: Automated Pipeline for Generating Verifiable and Diverse Function-Calling Datasets | 2406.18518 | Multi-stage verifiable synthesis of 60k function-calling examples; reusable data recipe for MelodyScribe op-emission SFT |
| 3 | 4,5 | Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question | 2403.14403 | T5-large (770M) classifier trained on auto-collected silver labels routes each query to no-retrieval / single-step / multi-step. |
| 3 | 1,9 | Advancing Text Embedding and Reranking Through Foundation Models | 2506.05176 | Decoder-based embedders at 0.6B scale with multi-stage training + model merging; smallest strong open recipe |
| 3 | 6 | AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases | 2407.12784 | Optimized backdoor triggers mapping to unique embedding region; >=80% ASR at <0.1% poison rate |
| 3 | 6 | Agentic Context Engineering: Evolving Contexts for Self-Improving Language Models | 2510.04618 | Generator/Reflector/Curator playbook with delta updates; closest Folio analog |
| 3 | 1,9 | Arctic-Embed 2.0: Multilingual Retrieval Without Compromise | 2412.04506 | Multilingual retrievers that keep English quality (prior work degraded it); two-stage MRL keeps quality at 256 dims; 8x16-bit to 128-byte ve |
| 3 | 5 | BlendSQL: A Scalable Dialect for Unifying Hybrid Question Answering in Relational Algebra | 2402.17882 | SQL dialect embedding LLM calls as ingredients evaluated inside relational algebra. |
| 3 | 2 | Block-Attention for Efficient Prefilling | 2409.15355 | Per-passage independent KV blocks (last block excepted) with reuse; same-family follow-up adds auto-segmentation + block distillation (2605. |
| 3 | 10 | Boosting LLMs in Professional Domains via Knowledge Augmented Generation | 2409.13731 | KG-vector mutual indexing + logical-form-guided hybrid reasoning for professional QA. |
| 3 | 5 | CHESS: Contextual Harnessing for Efficient SQL Synthesis | 2405.16755 | Multi-stage text-to-SQL pipeline (retrieve, filter, synthesize, verify) topping BIRD-style tasks. |
| 3 | 4 | CRAG: Corrective Retrieval Augmented Generation | 2401.15884 | Fine-tuned T5-large (770M) retrieval evaluator scores query-doc pairs into Correct/Incorrect/Ambiguous actions triggering refine, web-search |
| 3 | 8 | CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing | 2305.11738 | Self-correction works when critiques come from external tools, not the model itself. |
| 3 | 2 | CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion | 2405.16444 | Selective recompute of high-KV-deviation tokens fuses out-of-order chunk caches; 2.2-3.3x TTFT, 2.8-5x throughput. |
| 3 | 2 | CacheClip: Accelerating RAG with Effective KV Cache Reuse | 2510.10129 | Small auxiliary LLM's last-layer attention predicts which tokens need recompute; positions itself vs APE and CacheBlend. |
| 3 | 2 | CacheGen: KV Cache Compression and Streaming for Fast Large Language Model Serving | 2310.07240 | Distribution-aware KV tensor codec + bandwidth-adaptive compression; 3.5-4.3x smaller caches, 3.2-3.7x faster fetch+process. |
| 3 | 2 | CachePrune: Privacy-Aware and Fine-Grained KV Cache Sharing for Efficient LLM Inference | 2605.23640 | Shares only privacy-irrelevant segments; shows unrestricted cross-user KV sharing leaks inputs via side channels. |
| 3 | 5 | Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Ground | 2305.03111 | Large-scale text-to-SQL benchmark on dirty, large real databases with efficiency scoring. |
| 3 | 5 | DIN-SQL: Decomposed In-Context Learning of Text-to-SQL with Self-Correction | 2304.11015 | Decomposes text-to-SQL into schema-linking/classification/generation/self-correction subtasks. |
| 3 | 4 | DeepRetrieval: Hacking Real Search Engines and Retrievers with Large Language Models via R | 2503.00223 | RLVR on retrieval metrics (recall, NDCG, SQL execution accuracy) trains Qwen2.5-3B query/SQL rewriting that beats GPT-4o and Claude-3.5 on t |
| 3 | 6 | Defeating Prompt Injections by Design (CaMeL) | 2503.18813 | Capability-based isolation separating data from instructions; defense design pattern for the Folio gate |
| 3 | 3 | DimMem: Dimensional Structuring for Efficient Long-Term Agent Memory | 2605.15759 | Atomic typed units with time location reason purpose keyword fields; fine-tuned Qwen3-4B extractor beats larger. |
| 3 | 7 | DistiLLM: Towards Streamlined Distillation for Large Language Models | 2402.03898 | Skewed KL/SRKL losses unify on/off-policy KD; 1B-7B students keep instruction-following on a single GPU budget |
| 3 | 7 | Distilling Step-by-Step! Outperforming Larger Language Models with Less Training Data and  | doi:10.18653/v1/2023.findings-acl.507 | 540M PaLM learns from GPT-3.5/PaLM-540B rationales and beats the teacher on NLI with far less data |
| 3 | 5 | DocETL: Agentic Query Rewriting and Evaluation for Complex Document Processing | 2410.12189 | YAML document pipelines with agent-driven rewrite + validation directives per operation. |
| 3 | 6 | Dynamic Cheatsheet: Test-Time Learning with Adaptive Memory | 2504.07952 | Single evolving text memory at test time; cumulative and retrieval-synthesis variants |
| 3 | 2 | EPIC: Efficient Position-Independent Caching for Serving Large Language Models | 2410.15332 | LegoLink algorithm suppresses per-document attention-sink distortion; formalizes PIC; up to 8x TTFT. |
| 3 | 7 | Efficient Guided Generation for Large Language Models | 2307.09702 | Regex/CFG-constrained decoding with near-zero overhead; the reference implementation of grammar-constrained emission |
| 3 | 2 | Efficient Memory Management for Large Language Model Serving with PagedAttention | 2309.06180 | Paged KV-cache memory + automatic prefix caching; the baseline reuse API every PIC system builds on or compares against. |
| 3 | 1 | Efficient One-Pass Unified Generation and Retrieval for LLMs | 2409.05152 | Autoregressive retrieval tokens let one LLM generate AND retrieve in a single forward pass reusing KV cache |
| 3 | 6,8 | ExpeL: LLM Agents Are Experiential Learners | 2308.10144 | Extracts voted natural-language insights from success/failure pools; no weight updates |
| 3 | 4 | FilCo: Learning to Filter Context for Retrieval-Augmented Generation | 2311.08377 | Flan-T5-XL (3B) filter + LLaMA-2-7B (LoRA) trained on silver sentence-level labels (StrInc/lexical/CXMI); cuts prompts 44-64%. |
| 3 | 10 | From Local to Global: A Graph RAG Approach to Query-Focused Summarization | 2404.16130 | LLM-derived entity KG + Leiden communities + map-reduce community summaries for global sensemaking. |
| 3 | 7 | FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance | 2305.05176 | Cascades/routers over heterogeneous LLMs cut cost 98% while beating GPT-4 accuracy; routing evidence |
| 3 | 9 | Gemma 3 Technical Report | 2503.19786 | 1B text-only at 32K plus 4B-27B multimodal at 128K; function calling + structured output; 5:1 local/global attention shrinks KV cache. |
| 3 | 3,6,8 | Generative Agents: Interactive Simulacra of Human Behavior | 2304.03442 | Memory stream with salience retrieval plus plan-act-reflect loop; earliest reflection-based consolidation. |
| 3 | 1 | Generative Representational Instruction Tuning | 2402.09906 | Joint generative+embedding training via instruction-switched attention; no-loss unification claim; >60% RAG speedup |
| 3 | 7 | Gorilla: Large Language Model Connected with Massive APIs | 2305.15334 | LLaMA-7B fine-tuned on API docs beats GPT-4 on APIBench; direct precedent for small-model schema emission |
| 3 | 8 | Governing Evolving Memory in LLM Agents: Risks, Mechanisms, and the Stability and Safety G | 2603.11768 | Governance framework bounding stability/safety risks of self-evolving memory. |
| 3 | 7 | Granite-Function Calling Model: Introducing Function Calling Abilities via Multi-task Lear | 2407.00121 | 3B/8B Granite function-calling models via multi-task learning; closest released 3B-class tool-calling artefact |
| 3 | 2 | Grounded Cache Routing for Retrieval-Augmented Generation: When Is It Safe to Reuse an Ans | 2605.27494 | Reuse-as-decision framing: when cached answers are unsafe (evidence drift, collisions); surveys RAGCache/TurboRAG/CacheBlend/EPIC/PCR/LMCach |
| 3 | 9 | HELMET: How to Evaluate Long-Context Language Models Effectively and Thoroughly | 2410.02694 | Controllable-length (to 128K) eval across recall/RAG/rerank/citation/summ/ICL/QA; NIAH does not predict downstream; open models trail closed |
| 3 | 2 | HYPIC: Accelerating Hybrid-Attention LLM Serving with Position-Independent Caching | 2607.01299 | First PIC for hybrid linear/full-attention models; per-token KV primitives do not transfer to recurrent state. |
| 3 | 2 | HijackKV: New Threat in Position-Independent KV Cache Reuse | 2607.19957 | Token-match-retrieved KV encodes its original context; attacker chunk steers victim generation. Directly constrains PIC. |
| 3 | 3,10 | HippoRAG 2 (in: From RAG to Memory: Non-Parametric Continual Learning for Large Language M | 2502.14802 | Deeper passage integration plus online LLM use; fixes factual-memory drop of graph-augmented RAG. |
| 3 | 3,10 | HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models | 2405.14831 | OpenIE triples plus Personalized PageRank over passage nodes for associative retrieval. |
| 3 | 5 | HybridRAG: Integrating Knowledge Graphs and Vector Retrieval Augmented Generation for Effi | 2408.04948 | Fuses KG triples with vector RAG for extraction over financial documents. |
| 3 | 1 | Improved Techniques for Training LLMs as Generalist Embedding Models | 2405.17428 | Latent-attention pooling beats last-token/mean; causal mask removed for contrastive training; two-stage instruction tuning |
| 3 | 1,9 | Improving Text Embeddings with Large Language Models | 2401.00368 | Synthetic-data-only contrastive fine-tune of decoder LLM, last-token pooling, <1k steps |
| 3 | 3 | Is Agent Memory a Database? Rethinking Data Foundations for Long-Term AI Agent Memory | 2605.26252 | Argues memory systems fail on growth revision and forgetting; demands database-style revision and transaction semantics. |
| 3 | 7 | JSONSchemaBench: A Rigorous Benchmark of Structured Outputs for Language Models | 2501.10868 | First rigorous structured-output benchmark across engines; measures validity AND quality incl. small models |
| 3 | 2 | KV Packet: Recomputation-Free Context-Independent KV Caching for LLMs | 2604.13226 | Immutable cached-document packets wrapped in trainable soft prompts; zero-recompute alternative to CacheBlend/EPIC-style repair. |
| 3 | 2 | KVLink: Accelerating Large Language Models via Efficient KV Cache Reuse | 2502.16002 | Independent per-document precompute + link techniques to repair missing cross-document attention on concat. |
| 3 | 9 | LFM2 Technical Report | 2511.23404 | Hybrid gated-conv + sparse-attention backbone, 2x CPU prefill/decode vs same-size transformers; 32K; task Nanos for tool-calling/RAG/extract |
| 3 | 1,2,3,5,6,7,9,10 | LMCache (production KV-cache layer; CacheBlend's serving home) | -- | Production disaggregated prefill/decode KV store (CPU/DRAM/remote tiers) used by CacheBlend-line research. |
| 3 | 5 | Language Models Enable Simple Systems for Generating Structured Views of Heterogeneous Dat | 2304.09433 | Synthesizes code + weak-supervision to extract structured views without training data. |
| 3 | 8 | Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories | 2606.03979 | LM learns a sleep-time self-modification/consolidation operator over its own memory. |
| 3 | 1 | Large Language Models Are Secretly Powerful Text Encoders | 2404.05961 | Three-step decoder-to-encoder conversion: bidirectional attention + MNTP + contrastive |
| 3 | 8 | Learning to Forget: Sleep-Inspired Memory Consolidation for Resolving Proactive Interferen | 2603.14517 | Sleep-inspired consolidation that forgets interfering memories to cut proactive interference. |
| 3 | 3 | Lightweight LLM Agent Memory with Small Language Models | 2604.07798 | STM MTM LTM tiers with SLMs driving retrieval write and offline consolidation; small-model memory operators. |
| 3 | 7 | LoRA: Low-Rank Adaptation of Large Language Models | 2106.09685 | Rank-8/16 adapters match full fine-tuning on GPT-3 175B; the baseline adapter method for 2B fine-tunes |
| 3 | 9 | LongEmbed: Extending Embedding Models for Long Context Retrieval | 2404.12096 | Two synthetic plus four dispersed-answer real tasks to 32K; 512-context models collapse; training-free PI/NTK/SelfExtend recovers length; Ro |
| 3 | 3 | MIRIX: Multi-Agent Memory System for LLM-Based Agents | 2507.07957 | Six-component modular memory (episodic semantic procedural etc.) routed by a multi-agent controller. |
| 3 | 9 | MTEB: Massive Text Embedding Benchmark | 2210.07316 | 8 tasks / 58 datasets / 112 languages; no single method dominates all tasks. |
| 3 | 4,8 | Mem-alpha: Learning Memory Construction via Reinforcement Learning | 2509.25911 | RL (verl) trains a Qwen3-4B agent to emit store/structure/update ops over core/episodic/semantic memory; reward is downstream QA accuracy. |
| 3 | 3,8 | Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory | 2504.19413 | Two-phase extract-then-update pipeline over facts plus optional graph store; ADD/UPDATE/DELETE operations. |
| 3 | 3,8 | MemGPT: Towards LLMs as Operating Systems | 2310.08560 | Virtual-context OS metaphor: working context plus recall/archival stores with explicit read-write calls. |
| 3 | 3,8 | MemOS: A Memory OS for AI System | 2507.03724 | MemCube units with type metadata governed by MemScheduler lifecycle across parametric activation and plaintext stores. |
| 3 | 3 | MemTX: Transactional Belief Commit for Stateful Agent Memory | 2607.23929 | A memory write is not a belief commit: staged commit protocol before writes become actionable. |
| 3 | 3 | Memanto: Typed Semantic Memory with Information-Theoretic Retrieval for Long-Horizon Agent | 2604.22085 | Typed semantic memory that skips LLM entity extraction and graph maintenance for cheaper ingestion. |
| 3 | 6 | Memory Injection Attacks on LLM Agents via Query-Only Interaction (MINJA) | 2503.03704 | Query-only memory poisoning via bridging steps + progressive shortening; 98.2% inject / 76.8% ASR |
| 3 | 8 | Memory Provenance Laundering in LLM Agents: A Non-Amplification Firewall for Persistent Me | 2607.29167 | Non-amplification firewall blocking provenance laundering in persistent memory. |
| 3 | 4 | Memory-R1: Enhancing Large Language Model Agents to Manage and Utilize Memories via Reinfo | 2508.19828 | Two RL agents (Memory Manager with ADD/UPDATE/DELETE/NOOP + Answer Agent) fine-tuned with PPO/GRPO on 152 QA pairs; tested on LLaMA-3.1-8B a |
| 3 | 3,6,8 | MemoryBank: Enhancing Large Language Models with Long-Term Memory | 2305.10250 | Memory tower with Ebbinghaus forgetting curve plus user-portrait updater for personality retention. |
| 3 | 9 | MiniCPM4: Ultra-Efficient LLMs on End Devices | 2506.07900 | 0.5B/8B end-side models; sparse attention + quantization + speculative sampling; MiniCPM4-MCP tool-use section; 7x faster 128K prefilling th |
| 3 | 7 | MiniLLM: On-Policy Distillation of Large Language Models | 2306.08543 | Reverse-KL + policy-gradient on student samples fixes exposure bias; GPT-2-760M students improve on RougeL/exact-match |
| 3 | 2 | MiniPIC: Flexible Position-Independent Caching in <100LOC | 2606.13126 | Unrotated-K storage with late RoPE + user-controlled reuse primitives; minimal-diff PIC inside vLLM. |
| 3 | 1,9 | Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings | 2402.03216 | Single encoder unifies dense+sparse+multi-vector retrieval via self-distillation; 8k context |
| 3 | 9 | Nomic Embed: Training a Reproducible Long Context Text Embedder | 2402.01613 | 137M, 8K context; beats ada-002 and text-embedding-3-small on MTEB and LoCo; fully reproducible pipeline. |
| 3 | 6 | Not what you've signed up for: Compromising Real-World LLM-Integrated Applications with In | 2302.12173 | Founding indirect-prompt-injection taxonomy incl. persistent cross-session compromise via agent memory |
| 3 | 8 | OEP: Poisoning Self-Evolving LLM Agents via Locally Correct but Non-Transferable Experienc | 2605.18930 | Attack injecting locally-correct but non-transferable experiences into evolving memory. |
| 3 | 7 | On-Policy Distillation of Language Models: Learning from Self-Generated Mistakes | 2306.13649 | Student-generated outputs as distillation data with teacher correction; GKD-style on-policy recipe at 77M-7B scale |
| 3 | 7 | Orca 2: Teaching Small Language Models How to Reason | 2311.11045 | 7B/13B taught 27 reasoning strategies (step-by-step, recall-then-generate) beat larger models on reasoning evals |
| 3 | 7 | Orca: Progressive Learning from Complex Explanation Traces of GPT-4 | 2306.02707 | 13B Orca trained on GPT-4 explanation traces matches ChatGPT on reasoning; imitation + explanations recipe |
| 3 | 7 | Phi-3 Technical Report: A Highly Capable Language Model Locally on Your Phone | 2404.14219 | 3.8B Phi-3-mini competitive with 7B+ on MMLU/MT-bench via data curation; existence proof for 2-4B narrow-task quality |
| 3 | 6 | PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of Large Langu | 2402.07867 | Retrieval+generation two-condition poison texts; ~97% ASR with 5 texts in millions; tested defenses fail |
| 3 | 1,9 | Powerful and Lightweight Text Representations | 2509.20354 | 308M decoder-derived encoder via T5Gemma init + Gemini-Embedding distillation; SOTA <500M |
| 3 | 2 | Prompt Cache: Modular Attention Reuse for Low-Latency Inference | 2311.04934 | Schema-defined prompt modules with precomputed attention states reused across prompts; 8x GPU / 60x CPU TTFT cut. |
| 3 | 7 | QLoRA: Efficient Finetuning of Quantized LLMs | 2305.14314 | 4-bit NF4 + paged optimizers fine-tune 65B on one 48GB GPU; implies 2B fits easily in 16GB |
| 3 | 9 | Qwen3 Technical Report | 2505.09388 | Unified thinking/non-thinking dense models 0.6B-32B plus MoE; 0.6B/1.7B at 32K context, 4B+ at 128K; smalls distilled from 32B/235B flagship |
| 3 | 4 | RAG-Gym: Systematic Optimization of Language Agents for Retrieval-Augmented Generation (ar | 2502.13957 | Systematic SFT/DPO/PPO + process-critic tuning of Llama-3.1-8B search agents; DPO with process supervision beats outcome-RL (Search-R1, R1-S |
| 3 | 2 | RAGCache: Efficient Knowledge Caching for Retrieval-Augmented Generation | 2404.12457 | Knowledge-tree cache of retrieved chunks across GPU/host memory with RAG-aware replacement; 4x TTFT on vLLM+Faiss. |
| 3 | 4 | RECOMP: Improving Retrieval-Augmented LMs with Compression and Selective Augmentation | 2310.04408 | 110M extractive + 775M abstractive compressors trained with end-task signal; emit empty string when retrieval is useless (selective augmenta |
| 3 | 3 | REMem: Reasoning with Episodic Memory in Language Agent | 2602.13530 | Offline hybrid memory graph of time-aware gists and facts plus online agentic retriever with tools. |
| 3 | 4 | RankRAG: Unifying Context Ranking with Retrieval-Augmented Generation in LLMs | 2407.02485 | Single Llama3-8B SFT blend for both context ranking (True/False + index selection) and answer generation; beats 10x-data rankers and GPT-4 o |
| 3 | 2 | ReCache: Efficient KV Cache Reuse and Compression for Tool-Augmented LLM Agents | 2608.19662 | Resource-local positions + contribution-selected layer/head routes; caches tool/skill schemas reused in varying orders. |
| 3 | 3,6,8 | Reflexion: Language Agents with Verbal Reinforcement Learning | 2303.11366 | Episodic memory of verbal self-reflections in a slot, no weight updates; actor-evaluator loop. |
| 3 | 1 | Repetition Improves Language Model Embeddings | 2402.15449 | Repeat-input trick gives causal decoders bidirectional-like embeddings with zero architecture change |
| 3 | 8 | Retain or Consolidate? Budget-Dependent Operator Selection for Language Agent Memory | 2607.17545 | Selects retain-vs-consolidate operators based on memory budget; direct revise-pass policy. |
| 3 | 5,7 | RouteLLM: Learning to Route LLMs with Preference Data | 2406.18665 | Preference-data router sending easy queries to small/cheap models, hard ones to frontier. |
| 3 | 5 | RouterRetriever: Routing over a Mixture of Expert Embedding Models | 2409.02685 | Per-query routing over specialist embedding models beats any single embedder. |
| 3 | 2,7 | SGLang: Efficient Execution of Structured Language Model Programs | 2312.07104 | RadixAttention: radix-tree KV reuse across requests/programs + compressed FSM for structured decoding. |
| 3 | 1 | Scaling Sentence Embeddings with Large Language Models | 2307.16645 | Explicit one-word-limitation prompt extracts causal-LM embeddings; scaling study 125M-66B; 2.7B beats 4.8B prior SOTA |
| 3 | 4 | Search-R1: Training LLMs to Reason and Leverage Search Engines with Reinforcement Learning | 2503.09516 | GRPO/PPO teaches Qwen2.5-3B/7B when and how to call a search engine mid-reasoning, masking retrieved tokens in the loss. |
| 3 | 4,8 | Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | 2310.11511 | LLaMA2-7B/13B fine-tuned to emit retrieve/no-retrieve and critique reflection tokens controlling on-demand retrieval. |
| 3 | 5 | Semantic Operators: A Declarative Model for Rich, AI-based Data Processing | 2407.11418 | Formal semantic operators (filter/join/group-by/top-k in NL) with accuracy guarantees vs a gold algorithm. |
| 3 | 10 | Simple and Fast Retrieval-Augmented Generation | 2410.05779 | Dual-level (low/high) graph+vector retrieval with incremental update algorithm. |
| 3 | 8 | Sleep-time Compute: Beyond Inference Scaling at Test-time | 2504.13171 | Offline precomputation of context into reusable state amortizes test-time cost. |
| 3 | 9 | Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder (ModernBERT) | 2412.13663 | Modernized encoder on 2T tokens with RoPE + alternating local/global attention; SOTA short- and long-context retrieval per size; fastest mea |
| 3 | 9 | SmolLM2: When Smol Goes Big -- Data-Centric Training of a Small Language Model | 2502.02737 | Fully-open 1.7B/360M/135M models overtrained on ~11T tokens; 1.7B-Instruct supports function calling; 16k variant reports HELMET scores. |
| 3 | 1 | Superior Training Data Brings A Stronger Embedding Model | 2501.01028 | Decoder-based embedder on Qwen2-0.5B SOTA among <1B models; persona synthetic data + ranking-consistency filter |
| 3 | 8 | TRUSTMEM: Learning Trustworthy Memory Consolidation for LLM Agents with Long-Term Memory | 2606.25161 | Trust-scored consolidation filtering untrustworthy content before it enters memory. |
| 3 | 5,10 | TableRAG: A Retrieval Augmented Generation Framework for Heterogeneous Document Reasoning | 2506.10380 | Joint retrieval over text and tables in mixed documents. |
| 3 | 5,10 | TableRAG: Million-Token Table Understanding with Language Models | 2410.04739 | Schema + cell retrieval to query million-token tables without full-table prompts. |
| 3 | 9 | The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic Evaluation | PMLR-v267:patil25a (no arXiv id) | AST-plus-execution grading of serial/parallel/multi-turn/multi-step tool calls; de-facto standard; small models are directly comparable on i |
| 3 | 7 | ToolACE: Winning the Points of LLM Function Calling | 2409.00920 | 8B model tops function-calling leaderboard via formalized data pipeline; small-model function-calling SOTA recipe |
| 3 | 4,7 | Toolformer: Language Models Can Teach Themselves to Use Tools | 2302.04761 | GPT-J (6B) self-supervises API-call decisions (when/what/where to call search, QA, calculator) from its own sampled-and-filtered traces. |
| 3 | 5 | Towards Accurate and Efficient Document Analytics with Large Language Models | 2405.04674 | Template-based table discovery over document collections with cost/accuracy trade-offs. |
| 3 | 10 | Towards Extremely Simple Retrieval-Augmented Generation | 2501.06713 | Heterogeneous chunk-entity graph + topology-enhanced retrieval letting SLMs match LLM-RAG at 25% storage. |
| 3 | 9 | Training Sparse Mixture Of Experts Text Embedding Models (Nomic Embed v2) | 2502.07972 | First general-purpose MoE embedder; beats its parameter class monolingually and multilingually, rivals 2x-size models; code+models+eval data |
| 3 | 2 | TurboRAG: Accelerating Retrieval-Augmented Generation with Precomputed KV Caches for Chunk | 2410.07590 | Offline-precomputed per-document KV + mask/position redesign + fine-tune to recover accuracy; ~8.6x mean TTFT cut. |
| 3 | 6 | Voyager: An Open-Ended Embodied Agent with Large Language Models | 2305.16291 | Ever-growing retrieved skill library of executable code; first self-written-skills system |
| 3 | 7 | XGrammar: Flexible and Efficient Structured Generation Engine for Large Language Models | 2411.15100 | Pushdown-automaton constrained decoding co-designed with serving; ~100x lower per-token overhead vs outlines-style |
| 3 | 3,10 | Zep: A Temporal Knowledge Graph Architecture for Agent Memory | 2501.13956 | Bi-temporal property graph with valid and ingested timestamps for entity and edge versioning. |
| 3 | 3 | eMEM: A Hybrid Spatio-Temporal Memory System For Embodied Agents | 2606.03374 | Multi-index memory: SQLite structured storage plus hnswlib semantic search plus space-time keys. |
| 2 | 8 | Agent Drift: Quantifying Behavioral Degradation in Multi-Agent LLM Systems Over Extended I | 2601.04170 | Quantifies behavioral drift over long multi-agent interactions; drift metric. |
| 2 | 6 | Agent Workflow Memory | 2409.07429 | Induces reusable workflows offline/online; +24.6%/+51.1% on Mind2Web/WebArena |
| 2 | 5 | Agentic Context Cracking: Token-Efficient Data Reasoning Agents via Adaptive Structuring o | 2608.31082 | Agent adaptively structures unstructured data once so later queries run cheaply (index-time ETL). |
| 2 | 10 | Benchmarking Large Language Models in Retrieval-Augmented Generation | 2309.01431 | Four testbeds: noise robustness, negative rejection, information integration, counterfactual robustness. |
| 2 | 9 | Benchmarking and Building Long-Context Retrieval Models with LoCo and M2-BERT | 2402.07440 | 80M Monarch-Mixer state-space retriever outscores transformer baselines by 23+ points on unchunkable long docs; single-sample-batch finetuni |
| 2 | 3 | Beyond Semantic Organization: Memory as Execution State Management for Long-Horizon Agents | 2606.06090 | Retrieval should reconstruct execution state not semantic neighborhoods; mixes of valid and erroneous traces hurt. |
| 2 | 5 | Binding Language Models in Symbolic Languages | 2210.02875 | LLM emits program + API calls bound to symbolic executors (SQL/Python) for QA. |
| 2 | 10 | Boosting Knowledge Intensive Reasoning of LLMs via Inference-time Hybrid Information Struc | 2410.08815 | Hybrid structure router picks optimal format (table/graph/chunk/algorithm/catalogue) then structurizes + decomposes. |
| 2 | 5 | Bridge the Last-Mile Gap to Semantic Analytics: Compiling Natural-Language Queries into Se | 2606.04641 | Compiles NL questions directly into semantic-operator pipelines (NL front-end for LOTUS-class systems). |
| 2 | 5 | Chain-of-Query: Unleashing the Power of LLMs in SQL-Aided Table Understanding via Multi-Ag | 2508.15809 | Multi-agent collaboration generating and chaining SQL sub-queries for table QA. |
| 2 | 5 | Chain-of-Table: Evolving Tables in the Reasoning Chain for Table Understanding | 2401.04398 | Iterative table-transformation chain (filter/select/group) as the reasoning trace. |
| 2 | 2 | ChunkAttention: Efficient Self-Attention with Prefix-Aware KV Cache and Two-Phase Partitio | 2402.15220 | Prefix-tree chunked KV sharing across requests + locality-aware kernel; 3.2-4.8x self-attention speedup. Prefix-only. |
| 2 | 2 | CoinRAG: Contextualized Information Nugget KV Cache Reuse for Long-Context RAG | 2608.07458 | Sub-chunk nugget-level offline KV reuse to cut redundancy/noise of coarse chunks under prefill-latency budgets. |
| 2 | 10 | Comprehensive RAG Benchmark | 2406.04744 | 4409 QA pairs over 5 domains x 8 types with mock web+KG APIs; penalizes hallucination over abstention. |
| 2 | 10 | Deep and Responsible Reasoning of Large Language Model on Knowledge Graph | 2307.07697 | LLM agent beam-search over KGs (LLM x KG tight coupling); small-model+ToG rivals GPT-4 on some sets. |
| 2 | 10 | Dense X Retrieval: What Retrieval Granularity Should We Use? | 2312.06648 | Proposition-level indexing beats passage-level retrieval and downstream QA under fixed budget. |
| 2 | 7 | DistiLLM-2: A Contrastive Approach Boosts the Distillation of LLMs | 2503.07067 | Contrastive on-policy distillation; small students gain on reasoning benchmarks |
| 2 | 8 | Do Language Models Converge to Themselves? Recursive Self-Refinement as Textual Relaxation | 2607.22653 | Models recursive self-refinement as textual relaxation with convergence analysis. |
| 2 | 7 | DoRA: Weight-Decomposed Low-Rank Adaptation | 2402.09353 | Magnitude+direction decomposition beats LoRA with same parameter budget; drop-in LoRA upgrade |
| 2 | 8 | Efficient Streaming Language Models with Attention Sinks | 2309.17453 | Attention-sink KV eviction policy enabling infinite-length streaming inference. |
| 2 | 6 | Episodic memory in AI agents poses risks that should be studied and mitigated | 2501.11739 | Risks/benefits of episodic memory + four principles incl. agents must not edit own memories |
| 2 | 10 | Explainable Benchmark for Retrieval-Augmented Generation Systems | 2407.11005 | 100k examples x 5 domains with TRACe (Utilization, Relevance, Adherence, Completeness); 400M DeBERTa beats LLM judges. |
| 2 | 5 | FINER-SQL: Boosting Small Language Models for Text-to-SQL | 2605.03465 | Training recipe lifting small-LM text-to-SQL accuracy. |
| 2 | 5 | From Interpretation to Compilation: A Compilation-Based Execution Engine for Semantic Oper | 2608.06677 | Compiles semantic-operator pipelines to optimized plans instead of interpreting them. |
| 2 | 1 | GPT Sentence Embeddings for Semantic Search | 2202.08904 | First decoder-as-bi-encoder recipe: position-weighted mean pooling + BitFit; same author as GritLM |
| 2 | 10 | Generalist Model for Named Entity Recognition using Bidirectional Transformer | 2311.08526 | Small bidirectional encoder for zero-shot NER + single-pass KG triple building. |
| 2 | 1 | Generalizable Embeddings from Gemini | 2503.07891 | Frontier decoder (Gemini) converted to embedder via filtering + synthetic data + model soup; SOTA on MMTEB |
| 2 | 10 | Graph Retrieval-Augmented Generation | 2405.16506 | Divide-and-conquer ego-graph retrieval + soft pruning + dual hard/soft-prompt generation. |
| 2 | 7 | Guided Decoding and Its Critical Role in Retrieval-Augmented Generation | 2509.06631 | Guided/constrained decoding materially changes RAG faithfulness; relevant to grounding op-emission in retrieved chunks |
| 2 | 3 | HAGE: Harnessing Agentic Memory via RL-Driven Weighted Graph Evolution | 2605.09942 | Weighted multi-relational graph with query-conditioned traversal replacing static binary edges. |
| 2 | 3 | Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents | 2608.15008 | Controlled comparison of substrates: dense sparse text structural hierarchical refinement parametric activation. |
| 2 | 8 | Hindsight is 20/20: Building Agent Memory that Retains, Recalls, and Reflects | 2512.12818 | Retain-recall-reflect agent memory pipeline with hindsight reflection step. |
| 2 | 10 | Knowledge-Graph-Based Generation with Semantic Aggregation and Hierarchical Retrieval | 2508.10391 | Semantic aggregation with explicit inter-cluster relations + bottom-up LCA path retrieval; -46% redundancy. |
| 2 | 7 | Learning New Facts with QLoRA: An Acquisition-Retention Frontier | 2608.25677 | Maps QLoRA acquisition-retention frontier for factual updates; ranks close to full-FT at low forgetting budgets |
| 2 | 9 | MMTEB: Massive Multilingual Text Embedding Benchmark | 2502.13595 | Community-built 500-task multilingual expansion; best public model is a 560M instruct embedder, not an LLM; adds instruction-following, long |
| 2 | 8 | Mela: Test-Time Memory Consolidation based on Transformation Hypothesis | 2605.10537 | Test-time consolidation operator derived from a transformation hypothesis of memory. |
| 2 | 4 | MemAgent: Reshaping Long-Context LLM with Multi-Conv RL-based Memory Agent | 2507.02259 | Multi-conversation DAPO extension trains a segment-reading overwrite-memory agent that extrapolates 8K training to 3.5M-context QA. |
| 2 | 3 | MemInsight: Autonomous Memory Augmentation for LLM Agents | 2503.21760 | Autonomous augmentation of stored interactions to enrich semantic representation and retrieval. |
| 2 | 1 | Meta-Task Prompting Elicits Embeddings from Large Language Models | 2402.18458 | Training-free frozen-decoder embeddings via 8 meta-task prompts; beats PromptEOL/Echo, competitive with LLM2Vec-7B on STS |
| 2 | 9 | MiniCPM: Unveiling the Potential of Small Language Models with Scalable Training Strategie | 2404.06395 | 1.2B/2.4B SLMs matching 7-13B models; WSD scheduler plus ModelTunnel scaling-law search transferred from tiny proxies. |
| 2 | 7 | Mixture-of-Agents Enhances Large Language Model Capabilities | 2406.04692 | Layered open-model proposers + strong aggregator beat GPT-4o; small models as proposal ensemble |
| 2 | 9 | Multilingual E5 Text Embeddings: A Technical Report | 2402.05672 | 1B-pair contrastive pretraining recipe for small multilingual encoders; large-instruct tops multilingual MTEB (vendor-reported). |
| 2 | 9 | OLMo: Accelerating the Science of Language Models | 2402.00838 | Truly-open 1B/7B programme: data, code, logs and intermediate checkpoints released; explicit decontamination. |
| 2 | 8 | Overcoming catastrophic forgetting in neural networks | 1612.00796 | Elastic weight consolidation: Fisher-weighted penalty protecting important weights. |
| 2 | 5 | PalimpChat: Declarative and Interactive AI analytics | 2502.03368 | Conversational NL front-end compiling to Palimpzest pipelines for non-expert users. |
| 2 | 9 | Phi-4-Mini Technical Report: Compact yet Powerful Multimodal Language Models via Mixture-o | 2503.01743 | 3.8B, 200K vocab, GQA, 128K via LongRoPE; matches 2x-size models on math/code; mixture-of-LoRAs adds vision/speech while backbone stays froz |
| 2 | 10 | Pruning Graph-Based Retrieval Augmented Generation with Relational Paths | 2502.14902 | Flow-based pruning to key relational paths + reliability-ordered path prompting; diagnoses redundancy, not insufficiency. |
| 2 | 4 | R1-Searcher++: Incentivizing the Dynamic Knowledge Acquisition of LLMs via Reinforcement L | 2505.17005 | Extends R1-Searcher with dynamic knowledge acquisition rewards on Qwen-2.5 backbones. |
| 2 | 4 | R1-Searcher: Incentivizing the Search Capability in LLMs via Reinforcement Learning | 2503.05592 | Two-stage RL (format + outcome reward) on Llama-3.1-8B / Qwen-2.5-7B backbones for autonomous multi-turn search. |
| 2 | 4,7 | RA-DIT: Retrieval-Augmented Dual Instruction Tuning | 2310.01352 | Co-fine-tunes retriever (Dragon+) and generator (LLaMA up to 65B) with retrieval-augmented instruction data. |
| 2 | 5 | ReAcTable: Enhancing ReAct for Table Question Answering | 2310.00815 | ReAct agent whose tools are SQL executors over tables, with intermediate-table voting. |
| 2 | 4 | ReSearch: Learning to Reason with Search for LLMs via Reinforcement Learning | 2503.19470 | GRPO with retrieval masking trains Qwen2.5-7B to interleave thinking, search queries, and results with no supervised reasoning traces. |
| 2 | 10 | Recursive Abstractive Processing for Tree-Organized Retrieval | 2401.18059 | Recursive embed-cluster-summarize tree; collapsed-tree retrieval across abstraction levels. |
| 2 | 10 | Relation Extraction By End-to-end Language generation | DOI 10.18653/v1/2021.findings-emnlp.204 | BART-based seq2seq linearization emitting 220+ relation types end-to-end. |
| 2 | 10 | Retrieval-Augmented Generation for Textual Graph Understanding and Question Answering | 2402.07630 | kNN retrieval + Prize-Collecting Steiner Tree subgraph + GNN soft prompt; halves graph-LLM hallucination. |
| 2 | 6 | SOP-Agent: Empower General Purpose AI Agent with Domain-Specific SOPs | 2501.09316 | Human-authored pseudocode SOPs as decision graphs; the one-human-skill model |
| 2 | 5 | SQuaD-SQL: Efficient Text-to-SQL with Small Language Models via LLM-Guided Knowledge Disti | 2607.08161 | Distils frontier text-to-SQL skill into small LMs; direct support for the 1-3B hypothesis. |
| 2 | 4 | STaR: Bootstrapping Reasoning With Reasoning | 2203.14465 | GPT-J (6B) bootstraps rationales by generating, filtering on correct answers, and retraining iteratively, with rationalization for failures. |
| 2 | 5 | Schema-First Retrieval: Embedding Catalogs for Natural Language Analytics | 2606.28387 | Embeds the data catalog/schema first so NL analytics queries route to the right tables. |
| 2 | 8 | Self-Refine: Iterative Refinement with Self-Feedback | 2303.17651 | Iterative generate-feedback-refine loop with the same model playing all roles. |
| 2 | 5 | SemBench: A Benchmark for Semantic Query Processing Engines | 2511.01716 | Benchmark comparing semantic query engines (Palimpzest/LOTUS/DocETL class) head-to-head. |
| 2 | 7 | Sequence-Level Knowledge Distillation | 1606.07947 | Teacher beam outputs as training targets beat word-level KD; foundation of all sequence-distillation recipes |
| 2 | 10 | Simple is Effective: The Roles of Graphs and Large Language Models in Knowledge-Graph-Base | 2410.20724 | Lightweight MLP + parallel triple scoring with structural-distance features; flexible top-K subgraphs. |
| 2 | 3 | SimpleMem: Efficient Lifelong Memory for LLM Agents | 2601.02553 | Three-stage semantic structured compression with intent-aware retrieval planning; 30x token reduction claim. |
| 2 | 7 | Small Language Models for Agentic Systems: A Survey of Architectures, Capabilities, and De | 2510.03847 | 2025 survey of SLM agentic architectures/capabilities/deployment; secondary map of the small-model agent space |
| 2 | 7 | Speculative Knowledge Distillation: Bridging the Teacher-Student Gap Through Interleaved S | 2410.11325 | Interleaved teacher/student sampling keeps student on-policy without full rollouts; cheap to run |
| 2 | 5 | StructGPT: A General Framework for Large Language Model to Reason over Structured Data | 2305.09645 | Interfaces letting an LLM read/extract over tables, KGs and DBs via function calls. |
| 2 | 3 | StructMem: Structured Memory for Long-Horizon Behavior in LLMs | 2604.21748 | Event-level bindings with cross-event links and periodic semantic consolidation. |
| 2 | 5 | T2-RAGBench: Text-and-Table Benchmark for Evaluating Retrieval-Augmented Generation | 2506.12071 | Benchmark for RAG over mixed text-and-table corpora. |
| 2 | 8 | The Sleeping Agent: What Gist-Based Context Compression Loses and Why | 2608.11775 | Measures information loss from gist-based sleep-time compression; a cautionary result. |
| 2 | 8 | TiMem: Temporal-Hierarchical Memory Consolidation for Long-Horizon Conversational Agents | 2601.02845 | Temporal-hierarchical consolidation with time-aware indexing for long conversations. |
| 2 | 8 | Titans: Learning to Memorize at Test Time | 2501.00663 | Neural long-term memory module updated by gradient surprise at test time. |
| 2 | 1 | Versatile Text Embeddings Distilled from Large Language Models | 2403.20327 | Two-step LLM distillation (FRet synthetic + LLM relabel) makes 1B-compact embedders beat 7B models |
| 2 | 7 | Where vs What: Decomposing Structural and Content Failures in LLM-Generated Structured Out | 2608.25358 | Separates structural from content errors in structured outputs; tells MelodyScribe whether to fix grammar or model |
| 2 | 8 | Who's Harry Potter? Approximate Unlearning in LLMs | 2310.02238 | Targeted unlearning by fine-tuning on relabeled forget-set tokens. |
| 2 | 7 | f-Divergence Minimization for Sequence-Level Knowledge Distillation | 2307.15190 | General f-divergence view of seqKD; mode-seeking divergences suit small students |
| 2 | 1,9 | jina-embeddings-v3: Multilingual Embeddings With Task LoRA | 2409.10173 | XLM-R-based 570M model with RoPE to 8K and per-task LoRA adapters; beats OpenAI/Cohere embeddings on English MTEB (vendor-reported). |
| 2 | 5 | mmRAG: A Modular Benchmark for Retrieval-Augmented Generation over Text, Tables, and Knowl | 2505.11180 | Modular benchmark comparing text, table and KG retrieval modalities on one setup. |
| 1 | 6 | A Survey on the Memory Mechanism of Large Language Model based Agents | 2404.13501 | Taxonomy of agent memory mechanisms; forward/backward chaining index |
| 1 | 1 | AnglE-optimized Text Embeddings | 2309.12871 | Angle-over-cosine loss fixes saturation zones; ablates 5 pooling strategies and AnglE-LLaMA variant |
| 1 | 3 | Episodic-Semantic Memory Architecture for Long-Horizon Scientific Agents | 2605.17625 | Dual-process split of 10-message episodic buffer from semantic store for saturated scientific contexts. |
| 1 | 8 | From Single to Multi-Granularity: Toward Long-Term Memory Association and Selection of Con | 2505.19549 | Multi-granularity memory association and selection policy for dialogue agents. |
| 1 | 5 | How Small Can You Go? A Controlled Study of LoRA Rank, Target Modules, and Quantization Tr | 2607.25583 | Controlled LoRA-rank/module/quantization study for small-model text-to-SQL on one GPU. |
| 1 | 6 | INMS: Memory Sharing for Large Language Model based Agents | 2404.09982 | Shared-memory protocol across agents; multi-tenant memory precedent |
| 1 | 5 | Larch: Learned Query Optimization for Semantic Predicates | 2606.07923 | Learned cost/quality optimizer for semantic (LLM) predicates in queries. |
| 1 | 5 | Large Databases Need Small, Open-Weight Language Models | 2606.31808 | Argues small open-weight LMs suffice for large-database QA when paired with execution/verification. |
| 1 | 8 | LifeAlign: Lifelong Alignment for Large Language Models with Memory-Augmented Focalized Pr | 2509.17183 | Memory-augmented preference optimization for lifelong alignment without forgetting. |
| 1 | 5 | Memory Architectures for Multi-Turn Text-to-SQL: A Benchmark and Empirical Study | 2605.26394 | Benchmarks memory designs for conversational text-to-SQL agents. |
| 1 | 8 | Memory Retrieval and Consolidation in Large Language Models through Function Tokens | 2510.08203 | Retrieval/consolidation triggered through learned function-token interface. |
| 1 | 5 | Multi-Objective Agentic Rewrites for Unstructured Data Processing | 2512.02289 | Agentic pipeline rewrites trading off cost, latency and quality for document processing. |
| 1 | 8 | My agent understands me better: Integrating Dynamic Human-like Memory Recall and Consolida | 2404.00573 | Recall/consolidation loop modeled on human memory dynamics for companion agents. |
| 1 | 3 | Omni-SimpleMem: Autoresearch-Guided Discovery of Lifelong Multimodal Agent Memory | 2604.01007 | Autonomous research pipeline discovering memory architectures; bug fixes beat hyperparameter tuning. |
| 1 | 5 | Play by the Type Rules: Inferring Constraints for LLM Functions in Declarative Programs | 2509.20208 | Type/constraint inference for LLM-valued functions inside declarative (BlendSQL-style) programs. |
| 1 | 6 | Prompt Injection attack against LLM-integrated Applications | 2306.05499 | Systematic PI threat analysis for LLM-integrated apps |
| 1 | 5 | RUBICON: Agentic AI for Messy Enterprise Data | 2604.21413 | Agentic preparation + structuring of messy enterprise data before querying. |
| 1 | 5 | Replacing Training with Memory: Listwise Selection for Text-to-SQL | 2609.00834 | Retrieved-experience (memory) selection replaces fine-tuning for text-to-SQL adaptation. |
| 1 | 5 | Retrieval-Augmented Generation of Ontologies from Relational Databases | 2506.01232 | Reverse direction: builds ontologies/KG schema out of relational databases for RAG. |
| 1 | 6 | Signed-Prompt: A New Approach to Prevent Prompt Injection Attacks Against LLM-Integrated A | 2401.07612 | Signed instructions authorized by role; lightweight authorized-write precedent |
| 1 | 1 | Text Embeddings by Weakly-Supervised Contrastive Pre-training | 2212.03533 | Weakly-supervised contrastive pretraining recipe every decoder-embedder inherits; first to beat BM25 zero-shot |
| 1 | 5 | VikingRAG: Accurate and Token-efficient Retrieval-augmented Generation over Structured Doc | 2609.11390 | Token-efficient RAG tuned for structured documents. |

## Refutations

- LoRA Learns Less and Forgets Less (2405.09673): Abs verified; PDF downloaded. Refutes 'LoRA matches full fine-tune' as a blanket claim.
- Repair, Not Improvement: Decomposing Constrained Decoding in Tool-Call Abstention (2608.13959): Abs verified; PDF downloaded. Refutes 'constraints improve small-model accuracy' as blanket claim.
- Sample More, Reflect Less: Self-Refine and Reflexion Lose to Repeated Sampling at Equal To (2607.28576): Abs page verified; title-level claim directly refutes small-model reflection cost-benefit. Not downloaded per rules.
- When Your Agent Opens the Chat App: Agent-Controlled Search over Raw Chat Logs Rivals Stru (2608.12888): Abs page opened and abstract verified; contradicts structure-is-necessary claim with matched-backbone numbers.
- Contextual Agentic Memory is a Memo, Not True Memory (2604.27707): Abs page opened and abstract verified; bounds what typed-store filing can claim.
- Large Language Models Cannot Self-Correct Reasoning Yet (2310.01798): Abs page verified; title-level claim contradicts unsupervised revise-pass optimism. Not downloaded per rules.
- Reproducing LightMem: Naive RAG Is Just as Good for Memory Management (2607.29104): Abs verified via search listing; tempers LightMem admission and construction-always-helps claims.
- Rethinking Mixture-of-Agents: Is Mixing Different Large Language Models Beneficial? (2502.00674): Abs verified; PDF downloaded. Refutes MoA-style 'mixing helps' reading. (This id is NOT Self-MoA; see ledger.)
- Useful Memories Become Faulty When Continuously Updated by LLMs (2605.12978): Abs page opened and abstract verified; contradicts always-on revise-pass assumption.
- Great Models Think Alike and this Undermines AI Oversight (2502.04313): Abs verified; PDF downloaded. (This id is NOT CAPA; see ledger.) Limits router-ensemble reliability claims.

## Abstained (unresolved ledger)

- AgentKVShift: Efficient KV Cache Reuse for Agentic Memory Systems (2607.21604): Verified at arXiv abs only (authors not captured); not filed; overlaps ReCache which is admitted with code.
- C2KV: Compressed and Composable KV Cache Reuse for Efficient LLM Inference (2607.17715): Verified at arXiv abs + HTML + GitHub API; not filed to bound scope; cited for the compression-interaction warning.
- CacheProbe: Auditing Prompt Cache Isolation in Gateway APIs (2605.30613): Verified at arXiv abs only; not filed; security-audit angle overlaps lane 6; cited in security requirements.
- Decoupled Attention Fusion: Accelerating RAG with Efficient KV Cache Reuse (2607.21599): Verified at arXiv abs only; not filed to bound scope. Cited in findings as contesting CacheBlend's no-loss claim; needs independent replication before depending
- Generative Embeddings from Large Language Models (2603.10913): Primary source opened but Mar-2026 preprint, too recent to verify claims/code; frozen-head idea flagged for capability 1
- KeyPooling: Measuring Where LLM API Relay Paths Collapse Prompt Cache Isolation (2608.17485): Verified at arXiv abs only; not filed; same reason as CacheProbe; cited in security requirements.
- Mixture-of-Translators: Translating KV Caches Across Heterogeneous LLMs (2607.28979): Verified at arXiv abs only; not filed; cross-architecture translation is future work for MelodyScribe, noted as gap-adjacent.
- Probing the Prompt KV Cache: Where It Becomes Dispensable (2605.30574): Verified at arXiv abs only; not filed; quality-measurement result cited in findings.
- SparseX: Efficient Segment-Level KV Cache Sharing for Interleaved LLM Serving (2606.01751): Verified at arXiv abs only; not filed to bound scope; overlaps admitted PIC neighbours.
- TokenDance: Scaling Multi-Agent LLM Serving via Collective KV Cache Sharing (2604.03143): Verified at arXiv abs only; not filed; multi-agent-collective angle is out of MelodyScribe's single-harness scope.
- Unifying Document Retrieval and Generation in a Single Vision-Language Model (2603.28554): Single-author Mar-2026 preprint; generation-collapse claim directly relevant but authority unverified; do not cite as refutation until reproduced
- 2 OLMo 2 Furious (2501.00656): Verified but 7B+ exceeds the lane 0.3-3B band; recipe otherwise relevant.
- A Universal Context-Reuse Layer for Cross-Model KV Sharing (2608.30963): Verified at arXiv abs only; not filed; same reason as MoT; very fresh (31 Aug 2026) preprint.
- Active Retrieval Augmented Generation (2305.06983): Verified at arXiv abs for title/authors; abstained as off-lane (prompting-only, predates and motivates the trained successors above).
- AdapShot: Adaptive Many-Shot In-Context Learning with Semantic-Aware KV Cache Reuse (2605.03644): Verified at arXiv abs only (authors not captured); not filed; ICL-shot focus is marginal to MelodyScribe.
- Arctic-Embed: Scalable, Efficient, and Accurate Text Embedding Models (2405.05374): Verified; superseded by the 2.0 report except for the tiny xs/s/long size points.
- Can I Buy Your KV Cache? (2606.13361): Verified at arXiv abs only (authors not captured); not filed; manifesto-style, no mechanism artefact.
- DSPy: Compiling Declarative Language Model Calls into Self-Improving Pipelines (2310.03714): Verified at arXiv abs only for title/authors; abstained as off-lane (no weight training) and repo/artefact facts not verified this session.
- KVShareArena: KV-Cache Reuse Across Contexts and Model Checkpoints (2609.10266): Surfaced in arXiv search snippet; abs page not opened; too fresh (Sep 2026) to depend on.
- LinearKV: One Cached State Suffices for Position-Independent Caching in Hybrid LLMs (2608.11231): Verified at arXiv abs only (authors not captured); not filed; HYPIC admitted as the representative hybrid-PIC item.
- MemDelta: Controlled Baselines and Hidden Confounds in Agent Memory Evaluation (2606.29914): Abs page opened; evaluation methodology belongs to lane 10, out of lane scope.
- NVIDIA Nemotron Nano 2: An Accurate and Efficient Hybrid Mamba-Transformer Reasoning Model (2508.14444): Verified, but 9B exceeds the band; throughput-per-watt datapoint only.
- Nemotron-H: A Family of Accurate and Efficient Hybrid Mamba-Transformer Models (2504.03624): Verified, but 8B/56B exceeds the lane 0.3-3B band; hybrid KV-light architecture noted for capability 3 only.
- ObjectCache: Layerwise Object-Storage Retrieval for KV Cache Reuse (2605.22850): Verified at arXiv abs only (authors not captured); not filed; storage-tiering, marginal to one-GPU harness.
- PCR: A Prefetch-Enhanced Cache Reuse System for Low-Latency RAG Serving (2603.23049): Verified at arXiv abs only; not filed; prefetch scheduling is serving-ops, marginal to MelodyScribe.
- Profile-Graph Memory for LLM Agents (ProGraph) (2607.19359): Search listing only; abs page never opened; repo has 1 star, adoption unverifiable.
- Reinforced Self-Training (ReST) for Language Modeling (2308.08998): Verified at primary source, but off-lane: machine-translation alignment with no store/update/delete/retrieve decision and no released artefact.
- Rethinking Memory as Continuously Evolving Connectivity (FluxMem) (2605.28773): Search listing only; authors state code will be open-sourced, artefact unverifiable.
- SF-AMS: Strategic Forgetting for Structured Memory in LLM Agent (2607.22562): Search listing only; forgetting policy belongs to lane 8, out of lane scope.
- Search-o1: Agentic Search-Enhanced Large Reasoning Models (2501.05366): Verified at primary sources, but off-lane: inference-only framework on a 32B backbone, no 1-8B model is trained to decide anything.
- Structure-Aware RAG Framework with Scholarly Knowledge Graph for Diverse Question Answerin (DOI 10.1145/3701716.3717819): Could not verify: only secondary search-result snippets seen; paper and implementation link never opened; name collides with ICLR StructRAG above.
- Towards Generalization of Block Attention via Automatic Segmentation and Block Distillatio (2605.15913): Verified at arXiv abs only (authors not captured); not filed; follow-up to admitted item, cited in its paragraph.
- Unsupervised Dense Information Retrieval with Contrastive Learning (2112.09118): Verified at primary source but out of lane scope (encoder-only, no generation); repo stars fetched, weights unverified here
- 2026 memory-poisoning preprints (e.g. MAFIA; Transferable End-to-End Optimization for Indi (see method.md): Reason: listing titles only, primary sources not opened; flag for next sweep
- A Framework for Inference Inspired by Human Memory Mechanisms (2310.09297): Abs page verified only; full text not reviewed, mechanism detail unknown.
- BadChain (backdoor chain-of-thought prompting; cited in AgentPoison) (recalled id 2405.04619 is WRONG (that id is a physics paper)): Reason: could not verify; recalled arXiv id resolves to an unrelated physics paper, genuine id not established this session
- Distilling Step-by-Step (recalled ids 2305.10586 / 2305.10688) (2305.10586): Recalled ids falsified against abs pages; corrected source admitted as distilling-step-by-step.
- DoRA (recalled id 2402.10974) (2402.10974): Recall corrected by primary source; do not cite 2402.10974 for DoRA.
- Gemma: Open Models Based on Gemini Research and Technology (2403.08295): Verified; superseded by Gemma 3 in every lane-relevant dimension.
- H2O Heavy-Hitter Oracle KV-cache eviction (unknown): Could not verify arXiv id (guessed 2311.13856 resolved to an unrelated paper); no primary source opened.
- MiniLLM (recalled id 2312.13344) (2312.13344): Recall corrected by primary source; do not cite 2312.13344 for MiniLLM.
- Outlines (recalled id 2307.06960) (2307.06960): Recall corrected by primary source; do not cite 2307.06960 for Outlines.
- RA-DIT (recalled id 2309.17402) (2309.17402): Recall corrected by primary source; do not cite 2309.17402 for RA-DIT.
- The Feasibility of Electric Air Taxis (misidentified as ExpeL) (2310.01417): Abs page verified it is NOT ExpeL; kept in ledger so the misidentification is not repeated.
