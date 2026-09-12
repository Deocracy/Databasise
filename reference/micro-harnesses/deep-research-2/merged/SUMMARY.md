# Merge summary

Rows read: 287 across 10 lanes ({'1': 24, '2': 29, '3': 21, '4': 33, '5': 25, '6': 32, '7': 25, '8': 39, '9': 22, '10': 37}). Unique items after dedup: 191. Dispositions: {'admit': 153, 'abstain': 38}. Admitted PDFs staged: 150. Malformed rows skipped: 0.

## Admitted, by relevance

| relevance | lanes | title | id / repo | one line |
|---|---|---|---|---|
| 3 | 10 | ANN-Benchmarks: A Benchmarking Tool for Approximate Nearest Neighbor Algorithms | 1807.05614 | Standard recall-vs-QPS harness; graph methods win high recall but fail some datasets |
| 3 | 10 | Accelerating Large-Scale Inference with Anisotropic Vector Quantization | 1908.10396 | Loss penalizing parallel residual component for MIPS; SOTA on ann-benchmarks |
| 3 | 6 | All-but-the-Top: Simple and Effective Postprocessing for Word Representations | 1702.01417 | Removes dominant common directions to repair degenerate word-embedding geometry (per title). |
| 3 | 7 | An Empirical Study on Information Extraction using Large Language Models (v1: Is Informati | 2305.14450 | GPT-4 vs SOTA gap plus soft-matching, robustness and dominant-error-type analysis over 14 IE subtasks |
| 3 | 1,2,10 | Approximate Nearest Neighbor Negative Contrastive Learning for Dense Text Retrieval | 2007.00808 | Async-refreshed ANN index mines corpus-representative hard negatives during training. |
| 3 | 2,3 | Arctic-Embed: Scalable, Efficient, and Accurate Text Embedding Models | 2405.05374 | Efficiency-first recipe: data filtering and long-context handling; 22M to 334M models, SOTA-for-size on MTEB Retrieval. |
| 3 | 6 | BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models | 2104.08663 | 18-dataset zero-shot retrieval benchmark; BM25 robust, late-interaction/rerank best, dense often lags. |
| 3 | 8 | BatchLLM: Optimizing Large Batched LLM Inference with Global Prefix Sharing and Throughput | 2412.03594 | Global prefix tree + prefix-group scheduling + decode-ratio-first reorder; 1.3-10.8x vs vLLM/SGLang |
| 3 | 10 | Billion-scale similarity search with GPUs | 1702.08734 | GPU k-selection at 55% of peak, 8.5x faster than prior GPU SOTA; IVF-PQ on GPU |
| 3 | 8 | CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion | 2405.16444 | Selective recompute fuses non-prefix cached chunks; TTFT 2.2-3.3x lower, 2.8-5x throughput vs full recompute |
| 3 | 1,6,10 | ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over B | 2004.12832 | Token-level late-interaction (MaxSim) over BERT encodings; per-pair NN cost avoided. |
| 3 | 1,10 | ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction | 2112.01488 | Residual compression plus denoised supervision shrinking late-interaction footprint. |
| 3 | 7 | Combining Constrained and Unconstrained Decoding via Boosting: BoostCD and Its Application | 2506.14901 | Boosted model fuses constrained and unconstrained drafts; constrained-only output shown to corrupt entities |
| 3 | 1,2,6,10 | Dense Passage Retrieval for Open-Domain Question Answering | 2004.04906 | Dual-encoder dense retriever beating BM25 9-19pp top-20 on open QA. |
| 3 | 8 | DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model  | 2401.09670 | Co-optimised prefill/decode placement; 4.48x more requests / 10.2x tighter SLO vs SOTA |
| 3 | 8 | Efficient Memory Management for Large Language Model Serving with PagedAttention | 2309.06180 | OS-style paging of KV cache blocks; near-zero fragmentation; 2-4x throughput vs FasterTransformer/Orca |
| 3 | 10 | Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Smal | 1603.09320 | Log-layered proximity-graph ANN index with neighbor-selection heuristic |
| 3 | 2 | Efficiently Teaching an Effective Dense Retriever with Balanced Topic Aware Sampling | 2104.06967 | Topic-aware balanced sampling plus MarginMSE distillation from cross-encoder into 6-layer DistilBERT. |
| 3 | 3 | EmbeddingGemma: Powerful and Lightweight Text Representations | 2509.20354 | 300M decoder-derived embedder; closest public analogue to MelodyScribe one-model goal |
| 3 | 7 | Exploiting Asymmetry for Synthetic Training Data Generation: SynthIE and the Case of Infor | 2303.04132 | Reverse-direction synthesis (triples to text) yields 1.8M pairs training 220M/770M extractors |
| 3 | 7,9 | Extract, Define, Canonicalize: An LLM-based Framework for Knowledge Graph Construction | 2404.03868 | Open few-shot extraction first, then schema definition and post-hoc canonicalization |
| 3 | 8 | FlashInfer: Efficient and Customizable Attention Engine for LLM Inference Serving | 2501.01005 | JIT attention templates + block-sparse KV formats + StreamK scheduling; 29-69% inter-token-latency cut; cascade attention for shared prefixe |
| 3 | 5 | FollowIR: Evaluating and Teaching Information Retrieval Models to Follow Instructions | 2403.15246 | TREC-narrative instruction benchmark with p-MRR metric plus training data that teaches instruction following. |
| 3 | 7,9 | From Local to Global: A Graph RAG Approach to Query-Focused Summarization | 2404.16130 | LLM extracts entity/relation graph with one-shot gleaning prompt, then community summaries |
| 3 | 7,9 | From RAG to Memory: Non-Parametric Continual Learning for Large Language Models | 2502.14802 | OpenIE NER plus query-to-triple generation and LLM triple filtering before PageRank |
| 3 | 2,6 | GPL: Generative Pseudo Labeling for Unsupervised Domain Adaptation of Dense Retrieval | 2112.07577 | Query generation plus cross-encoder pseudo-labels plus hard negatives for label-free domain adaptation. |
| 3 | 7 | GPT-NER: Named Entity Recognition via Large Language Models | 2304.10428 | @@## marker-token copy formulation plus self-verification QA to suppress NULL-input hallucinations |
| 3 | 4 | GRC: Unifying Reasoning-Driven Generation, Retrieval and Compression | 2605.09100 | Meta latent tokens plus unified generative/representational/compressive tuning unify generation, text representation and context compression |
| 3 | 2,3,5,6 | Gecko: Versatile Text Embeddings Distilled from Large Language Models | 2403.20327 | Two-step LLM distillation: synthetic pair generation then LLM relabeling of positives and hard negatives into a compact retriever. |
| 3 | 1,4,5 | Generative Representational Instruction Tuning | 2402.09906 | Instruction-switched joint generative+embedding training at no loss to either. |
| 3 | 7 | GoLLIE: Annotation Guidelines improve Zero-Shot Information-Extraction | 2310.03668 | Models fine-tuned to follow code-formatted annotation guidelines (Python classes) on unseen schemas |
| 3 | 9 | HippoRAG: Neurobiologically Inspired Long-Term Memory for Large Language Models | 2405.14831 | Two-step OpenIE plus embedding synonym edges, single-step PPR retrieval; 10-30x cheaper / 6-13x faster than IRCoT |
| 3 | 6 | How Contextual are Contextualized Word Representations? Comparing the Geometry of BERT, EL | 1909.00512 | Compares the geometry of BERT, ELMo and GPT-2 embeddings (per title), the only admitted study covering a causal decoder. |
| 3 | 4 | Hydra: Unifying Document Retrieval and Generation in a Single Vision-Language Model | 2603.28554 | Single LoRA trained only for retrieval is toggled at inference: on gives ColBERT-style multi-vector embeddings, off recovers base generation |
| 3 | 8 | Hydragen: High-Throughput LLM Inference with Shared Prefixes | 2402.05099 | Prefix/suffix attention decomposition; inter-sequence batching; up to 32x CodeLlama-13B throughput vs vLLM |
| 3 | 5 | INSTRUCTIR: A Benchmark for Instruction Following of Information Retrieval Models | 2402.14334 | Instance-wise user-aligned instructions with Robustness@10 metric; instruction-tuned retrievers can underperform. |
| 3 | 1,2,3,4,5 | Improving Text Embeddings with Large Language Models | 2401.00368 | Decoder-only LLM fine-tuned on synthetic multilingual data, under 1k steps, no labels. |
| 3 | 2,6 | InPars: Data Augmentation for Information Retrieval using Large Language Models | 2202.05144 | GPT-3 generated synthetic queries per document with consistency filtering, then standard finetune. |
| 3 | 7 | InstructUIE: Multi-task Instruction Tuning for Unified Information Extraction | 2304.08085 | Instruction+options+text in, structured sentence out, with auxiliary span/typing subtasks |
| 3 | 6 | IsoScore: Measuring the Uniformity of Embedding Space Utilization | 2108.07344 | A score for how uniformly an embedding space is utilised (per title). |
| 3 | 7,9 | KGGen: Extracting Knowledge Graphs from Plain Text with Language Models | 2502.09956 | Two-stage DSPy extraction (entities then relations) plus iterative LM clustering for resolution |
| 3 | 4 | LLM2Vec-Gen: Generative Embeddings from Large Language Models | 2603.10913 | Trainable special tokens compress the frozen LLM's own potential response into a fixed-length embedding in output space, trained on unlabele |
| 3 | 1,2,4,5 | LLM2Vec: Large Language Models Are Secretly Powerful Text Encoders | 2404.05961 | Bidirectional-attention swap plus MNTP plus contrastive tuning; 1.3B-8B; unsupervised SOTA on MTEB. |
| 3 | 8 | LMCache: An Efficient KV Cache Layer for Enterprise-Scale LLM Inference | 2510.09665 | Engine-independent KV layer: chunked offload, PD disaggregation, CacheBlend non-prefix reuse; up to 15x vLLM throughput |
| 3 | 7,9 | LightRAG: Simple and Fast Retrieval-Augmented Generation | 2410.05779 | Single-pass LLM extraction of entities/relations plus keyword profiling and dedup |
| 3 | 1,2,3,10 | M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Thr | 2402.03216 | 100+ languages; dense+multi-vector+sparse in one model; 8k tokens; self-distillation across heads. |
| 3 | 4 | MAGNET: Augmenting Generative Decoders with Representation Learning and Infilling Capabili | 2501.08648 | Three self-supervised objectives plus a new attention mechanism adapt a decoder-only LLM to emit robust representations and infill spans whi |
| 3 | 1,6 | MMTEB: Massive Multilingual Text Embedding Benchmark | 2502.13595 | 500+ tasks, 250+ languages; LLM-embedders lead some languages, not uniformly. |
| 3 | 1,6 | MTEB: Massive Text Embedding Benchmark | 2210.07316 | 58 datasets x 8 tasks; no single method dominates all tasks. |
| 3 | 5 | Making Text Embedders Few-Shot Learners | 2409.15700 | Train with 0-5 sampled in-context examples prepended to queries so the embedder gains few-shot ability without losing zero-shot. |
| 3 | 1,3,10 | Matryoshka Representation Learning | 2205.13147 | Nested coarse-to-fine representation; truncate dims at query time, no retraining. |
| 3 | 8 | MemServe: Context Caching for Disaggregated LLM Serving with Elastic Memory Pool | 2406.17565 | MemPool unifying context caching + disaggregated inference; global prompt-tree routing; JCT/TTFT cuts up to 53%/85% |
| 3 | 5 | Meta-Task Prompting Elicits Embeddings from Large Language Models | 2402.18458 | Average embeddings over eight meta-task prompts with explicit one-word limitation, no training. |
| 3 | 10 | MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Tran | 2002.10957 | Distill last-layer attention + value relations; 6-layer student 2.0x faster at >99% accuracy |
| 3 | 7,9 | MiniRAG: Towards Extremely Simple Retrieval-Augmented Generation | 2501.06713 | SLM-friendly design: entity extraction (not abstract summarization) as the small-model task |
| 3 | 8 | Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving | 2407.00079 | KVCache-centric disaggregation + Conductor scheduler + early rejection; Kimi +75% requests; TE 87-190 GB/s |
| 3 | 1,2,5 | NV-Embed: Improved Techniques for Training LLMs as Generalist Embedding Models | 2405.17428 | Latent-attention pooling beats mean/last-token; causal mask removed for contrastive train; 2-stage instruction tuning. |
| 3 | 1,2,3,10 | Nomic Embed: Training a Reproducible Long Context Text Embedder | 2402.01613 | Fully reproducible 137M-param, 8192-context embedder beating Ada-002 |
| 3 | 6 | On the Sentence Embeddings from Pre-trained Language Models | 2011.05864 | Diagnoses anisotropic BERT sentence space, fixes it with unsupervised normalising flows. |
| 3 | 5 | One Embedder Any Task: Instruction-Finetuned Text Embeddings | 2212.09741 | Concatenate a natural-language task instruction to every input and contrastive-train one encoder on 330 tasks. |
| 3 | 5 | One prompt is not enough: Instruction Sensitivity Undermines Embedding Model Evaluation | 2605.22544 | Fifteen prompts per task over 6 models and 11 datasets show single-prompt scores misrepresent the distribution and rankings are gameable. |
| 3 | 4 | OneGen: Efficient One-Pass Unified Generation and Retrieval for LLMs | 2409.05152 | One forward pass emits retrieval tokens and generation tokens together via retrieval-token markers; single-pass RAG/EL without a separate re |
| 3 | 8 | Orca: A Distributed Serving System for Transformer-Based Generative Models | doi:10.5555/3542929.3542970 (no arXiv) | Iteration-level (continuous) batching + selective batching; 36.9x throughput vs FasterTransformer on GPT-3 175B |
| 3 | 10 | PLAID: An Efficient Engine for Late Interaction Retrieval | 2205.09707 | Centroid interaction + pruning engine: 2.5-6.8x GPU / 9.2-45x CPU speedups at 140M passages |
| 3 | 8 | Preble: Efficient Distributed Prompt Scheduling for LLM Serving | 2407.00023 | E2 exploit/explore scheduler co-optimising KV reuse + load balance; 1.5-14.5x avg latency, 2-10x p99 |
| 3 | 8 | Prompt Cache: Modular Attention Reuse for Low-Latency Inference | 2311.04934 | Schema-declared prompt modules with position-correct KV reuse; 8x GPU / 60x CPU TTFT cuts |
| 3 | 2,6 | Promptagator: Few-shot Dense Retrieval From 8 Examples | 2209.11755 | Few-shot prompted LLM writes per-task synthetic queries, then task-specific dual-encoder training. |
| 3 | 5 | Promptriever: Instruction-Trained Retrievers Can Be Prompted Like Language Models | 2409.11136 | Per-instance instruction training with instruction negatives makes a bi-encoder promptable like an LM. |
| 3 | 2 | QLoRA: Efficient Finetuning of Quantized LLMs | 2305.14314 | Frozen 4-bit base with LoRA adapters; 65B fine-tunable on one 48GB GPU at full 16-bit quality. |
| 3 | 1,2,3,5 | Qwen3 Embedding: Advancing Text Embedding and Reranking Through Foundation Models | 2506.05176 | 0.6B-8B series; unsupervised pretrain plus supervised FT plus model merging; 0.6B hits the MelodyScribe size band. |
| 3 | 1,5 | Repetition Improves Language Model Embeddings | 2402.15449 | Repeat-input prompting gives causal LMs bidirectional-like embeddings, +5% zero-shot, no training. |
| 3 | 6 | Representation Degeneration Problem in Training Natural Language Generation Models | 1907.12009 | Diagnoses why likelihood training degenerates token-embedding geometry (per title). |
| 3 | 6 | Resources for Brewing BEIR: Reproducible Reference Models and an Official Leaderboard | 2306.07471 | Reproducible BEIR baselines plus effect-size meta-analysis replacing naive cross-dataset averaging. |
| 3 | 4,10 | Rethinking the Role of Token Retrieval in Multi-Vector Retrieval (XTR) | 2304.01982 | Retrieve-top-tokens objective; +2.8 nDCG@10 on BEIR; scoring stage 4000x fewer FLOPs |
| 3 | 4 | RetroLLM: Empowering Large Language Models to Retrieve Fine-grained Evidence within Genera | 2412.11919 | One LLM integrates retrieval and generation in a single process, generating fine-grained evidence from the corpus via constrained decoding;  |
| 3 | 2 | RocketQA: An Optimized Training Approach to Dense Passage Retrieval for Open-Domain Questi | 2010.08191 | Cross-batch negatives, denoised hard negatives, and data augmentation for dual-encoders. |
| 3 | 8 | SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills | 2308.16369 | Chunked prefills + decode-maximal batching; decode piggybacking; up to 10x decode throughput (LLaMA-13B/A6000) |
| 3 | 8 | SGLang: Efficient Execution of Structured Language Model Programs | 2312.07104 | RadixAttention tree-structured KV reuse across forked programs; compressed FSM for structured decode; up to 6.4x throughput |
| 3 | 10 | SPANN: Highly-efficient Billion-scale Approximate Nearest Neighbor Search | 2111.08566 | Memory-disk hybrid inverted index; 2x faster than DiskANN at 90% recall, ~1ms, 32GB |
| 3 | 1,10 | SPLADE v2: Sparse Lexical and Expansion Model for Information Retrieval | 2109.10086 | MLM-head sparse expansion with FLOPS regularization; inverted-index retrieval. |
| 3 | 5 | Scaling Sentence Embeddings with Large Language Models | 2307.16645 | The This-sentence-means-in-one-word template plus in-context demonstrations for training-free decoder embeddings. |
| 3 | 1,2,3,6,10 | Sentence-BERT: Sentence Embeddings using Siamese BERT-Networks | 1908.10084 | Siamese/triplet fine-tune of BERT producing cosine-comparable sentence vectors; 65h->seconds pair search. |
| 3 | 2,6 | SimCSE: Simple Contrastive Learning of Sentence Embeddings | 2104.08821 | Dropout-as-augmentation unsupervised positives; supervised NLI entailment/contradiction variant. |
| 3 | 8 | Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve | 2403.02310 | Stall-free chunked-prefill scheduler; 2.6x capacity vs vLLM (Mistral-7B/1xA100), up to 5.6x with pipeline parallelism |
| 3 | 1,2,3,6,10 | Text Embeddings by Weakly-Supervised Contrastive Pre-training | 2212.03533 | Weakly-supervised CCPairs contrastive pretraining; first to beat BM25 zero-shot on BEIR. |
| 3 | 7 | Text2KGBench: A Benchmark for Ontology-Driven Knowledge Graph Generation from Text | 2308.02357 | Ontology-guided fact extraction task with 7 metrics for extraction, conformance, hallucination |
| 3 | 6 | Understanding Contrastive Representation Learning through Alignment and Uniformity on the  | 2005.10242 | Contrastive loss asymptotically optimises alignment of positives plus uniformity on the hypersphere. |
| 3 | 7 | Unified Structure Generation for Universal Information Extraction | 2203.12277 | SEL linearization plus structural schema instructor (spot/associate/generate control) |
| 3 | 7 | UniversalNER: Targeted Distillation from Large Language Models for Open Named Entity Recog | 2308.03279 | ChatGPT-distilled open NER via mission-focused instruction tuning on diverse web text |
| 3 | 2,6 | Unsupervised Dense Information Retrieval with Contrastive Learning | 2112.09118 | Unsupervised contrastive pretraining with ICT and cropping augmentations. |
| 3 | 6 | Whitening Sentence Representations for Better Semantics and Faster Retrieval | 2103.15316 | Closed-form whitening (mean-subtract + PCA-whiten + truncate) fixes anisotropy and speeds retrieval. |
| 3 | 7,9 | Zep: A Temporal Knowledge Graph Architecture for Agent Memory | 2501.13956 | Episodic ingest with entity/fact/temporal extraction, edge dedup and bi-temporal invalidation |
| 3 | 7 | Zero- and Few-Shots Knowledge Graph Triplet Extraction with Large Language Models | 2312.01954 | Head-to-head triplet-extraction prompts across LLM sizes in zero- and few-shot settings |
| 3 | 7 | Zero-Shot Information Extraction via Chatting with ChatGPT | 2302.10205 | Two-stage multi-turn QA: find candidate types first, then chain-extract per type |
| 3 | 7 | iText2KG: Incremental Knowledge Graphs Construction Using Large Language Models | 2409.03284 | Four-module zero-shot pipeline separating entity and relation extraction with matcher-based resolution |
| 3 | 3,10 | jina-embeddings-v3: Multilingual Embeddings With Task LoRA | 2409.10173 | 570M multilingual model with task-specific LoRA adapters; long-context retrieval |
| 3 | 3,4,7,9 | mergekit: tools for merging pretrained large language models | n/a | Implementation of SLERP/TIES/DARE/task-arithmetic merges with YAML recipes; the practical route to fuse an embed-tuned LoRA/full model with  |
| 3 | 8,10 | vLLM serving engine (repo + docs) | - | APC via enable_prefix_caching with hash-chained KV blocks + cache_salt tenant isolation; chunked prefill + continuous batching built in |
| 2 | 4 | A Unified Model and Document Representation for On-Device Retrieval-Augmented Generation | 2604.14403 | Unified model+document representation so the whole RAG pipeline runs on-device for private local querying; small-model unified relevance. |
| 2 | 6 | AIR-Bench: Automated Heterogeneous Information Retrieval Benchmark | 2412.13102 | Automated heterogeneous IR benchmark (per title); the closest public recipe for private-corpus eval sets. |
| 2 | 6 | ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems | 2311.09476 | Automated RAG-system eval over synthetic queries and judgments (per title). |
| 2 | 4 | Activation-Informed Merging of Large Language Models | 2502.02421 | AIM folds activation-space information into any merging method to preserve critical base weights; a guard against generation degradation whe |
| 2 | 5 | Answer is All You Need: Instruction-following Text Embedding via Answering the Question | 2402.09642 | Embed the expected answer to the instruction-as-question instead of the instruction-text concatenation, trained on abstractive QA only. |
| 2 | 6 | BIRCO: A Benchmark of Information Retrieval Tasks with Complex Objectives | 2402.14151 | Retrieval tasks with complex objectives (per title). |
| 2 | 4 | Bagging-Based Model Merging for Robust General Text Embeddings | 2602.05787 | Systematic study of multi-task embedding training (scheduling) vs model merging for general embeddings and domain adaptation; merging as an  |
| 2 | 1,3,10 | C-Pack: Packed Resources For General Chinese Embeddings | 2309.07597 | BGE-family training resources: data, small-model baselines, C-MTEB evaluation |
| 2 | 7 | Decoding on Graphs: Faithful and Sound Reasoning on Knowledge Graphs through Generation of | 2410.18415 | KG-topology token mask forces well-formed triplet chains during generation |
| 2 | 8 | DeepSpeed-FastGen: High-throughput Text Generation for LLMs via MII and DeepSpeed-Inferenc | 2401.08671 | Dynamic SplitFuse token-budget batching; 2.3x effective throughput, 2x avg latency vs vLLM |
| 2 | 10 | Document Ranking with a Pretrained Sequence-to-Sequence Model | 2003.06713 | Relevance labels as target words; T5-base MRR@10 0.363, T5-large 0.383 on MS MARCO |
| 2 | 8 | EAGLE-2: Faster Inference of Language Models with Dynamic Draft Trees | 2406.16858 | Confidence-driven dynamic draft trees, no extra training over EAGLE; 3.05-4.26x, 20-40% over EAGLE |
| 2 | 8 | EAGLE: Speculative Sampling Requires Rethinking Feature Uncertainty | 2401.15077 | Feature-level autoregression + shifted tokens; 2.7-3.5x latency cut on LLaMA2-Chat 70B, 2x throughput |
| 2 | 4 | Editing Models with Task Arithmetic | 2212.04089 | Add/subtract task vectors (fine-tune minus base) to steer one set of weights toward combined behaviours without joint retraining. |
| 2 | 3 | Embedding And Clustering Your Data Can Improve Contrastive Pretraining | 2407.18887 | Cluster-aware sampling for contrastive pretraining data; quality over quantity |
| 2 | 8 | FlashAttention: Fast and Memory-Efficient Exact Attention with IO-Awareness | 2205.14135 | IO-aware tiled exact attention; 15% BERT-large e2e, 3x GPT-2 train speedups; basis of all serving kernels |
| 2 | 9 | From Louvain to Leiden: guaranteeing well-connected communities | 1810.08473 | Leiden community detection with connectivity guarantees; faster and better partitions than Louvain |
| 2 | 4 | GEM: A Generative Embedding Model Bridging Reasoning and Retrieval | 2608.13200 | One model reasons over the query in generation mode, then appends an embedding token encoding the enriched context for retrieval; evaluated  |
| 2 | 7 | GenIE: Generative Information Extraction | 2112.08340 | Autoregressive closed IE with bi-level trie-constrained beam search over KB schema |
| 2 | 7 | Generating Structured Outputs from Language Models: Benchmark and Studies | 2501.10868 | 10K real-world JSON schemas comparing 6 constrained-decoding frameworks on efficiency/coverage/quality |
| 2 | 4 | Giga-Embeddings: Mixture-of-Experts Encoders for High-Throughput Text Embeddings | 2608.23806 | Sparse 10B MoE encoder (1.8B active/token) tops its family on four MTEB suites and reports 114.5k tok/s in vLLM at 1024-token inputs; MoE em |
| 2 | 3 | Granite Embedding Models | 2502.20204 | 125M RoBERTa-style embedder family with enterprise retrieval focus |
| 2 | 4 | Improving General Text Embedding Model: Tackling Task Conflict and Data Imbalance through  | 2410.15035 | Joint multi-task embedding training shows task-conflict gradient interference; merging per-task models beats joint training for general embe |
| 2 | 6 | InPars-v2: Large Language Models as Efficient Dataset Generators for Information Retrieval | 2301.01820 | Efficient LLM synthetic query-generation recipe for retrieval datasets. |
| 2 | 9 | Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step  | 2212.10509 | Alternate CoT-reason and retrieve steps; the expensive iterative baseline HippoRAG beats 10-30x on cost |
| 2 | 7 | Iterative Zero-Shot LLM Prompting for Knowledge Graph Construction | 2307.01128 | Iterative zero-shot prompts per graph component without examples or external resources |
| 2 | 4 | LLM-based Embeddings: Attention Values Encode Sentence Semantics Better Than Hidden States | 2602.01572 | Value Aggregation pools attention value vectors across layers/tokens and reportedly beats hidden-state pooling training-free; a cheap-versio |
| 2 | 4 | LM-Cocktail: Resilient Tuning of Language Models via Model Merging | 2311.13534 | Merge a fine-tuned model back toward its base to recover general ability while keeping target-task gains; directly measures the generation s |
| 2 | 4 | Language Models are Super Mario: Absorbing Abilities from Homologous Models as a Free Lunc | 2311.03099 | DARE drops most delta parameters then rescales, so merged homologous models keep abilities with no retraining or GPU; sparsified merges pres |
| 2 | 9 | LazyGraphRAG: Setting a new standard for quality and cost | n/a (https://www.microsoft.com/en-us/research/blog/lazygraphrag-setting-a-new-standard-for-quality-and-cost/) | Deferred-LLM indexing (NLP noun phrases + co-occurrence); indexing cost 0.1% of GraphRAG, query budget scales quality |
| 2 | 5 | Linq-Embed-Mistral Technical Report | 2412.03223 | E5-Mistral fine-tune with task-tailored data crafting and one-sided instruction prefixes; documents encoded once and cached. |
| 2 | 8 | Llumnix: Dynamic Scheduling for Large Language Model Serving | 2406.03243 | Live migration of requests + KV state across instances; 10x tail-latency cut, 36% cost saving |
| 2 | 6 | MS MARCO: A Human Generated MAchine Reading COmprehension Dataset | 1611.09268 | Large-scale human-generated queries for passage ranking and comprehension (per title). |
| 2 | 8 | Medusa: Simple LLM Inference Acceleration Framework with Multiple Decoding Heads | 2401.10774 | Extra decoding heads + tree attention; Medusa-1 2.2x lossless frozen, Medusa-2 2.3-3.6x with joint tuning |
| 2 | 4 | Merging: Resolving Interference When Merging Models | 2306.01708 | Trim low-magnitude deltas, elect per-parameter sign, merge disjoint means; reduces interference when fusing models tuned from one base. |
| 2 | 5 | Multilingual E5 Text Embeddings: A Technical Report | 2402.05672 | Instruction tuning with 150k unique synthetic instructions over 93 languages on an encoder backbone. |
| 2 | 8 | NanoFlow: Towards Optimal Large Language Model Serving Throughput | 2408.12757 | Intra-device parallelism via nano-batches; serving is compute-bound at scale; 1.91x vs vLLM/FastGen/TRT-LLM |
| 2 | 9 | Optimizing the Interface Between Knowledge Graphs and LLMs for Complex Reasoning | 2505.24478 | Hyperparameter sweep over Cognee chunking/graph/retrieval/prompting on HotPotQA/2Wiki/MuSiQue; tuning gains real but uneven |
| 2 | 2 | PROD: Progressive Distillation for Dense Retrieval | 2209.13335 | Teacher-progressive distillation bridging the teacher-student capacity gap. |
| 2 | 9 | PathRAG: Pruning Graph-Based Retrieval Augmented Generation with Relational Paths | 2502.14902 | Flow-based pruning of relational paths with reliability-ascending prompt ordering to cut retrieval tokens |
| 2 | 5 | PromptBERT: Improving BERT Sentence Embeddings with Prompts | 2201.04337 | Manual and continuous prompt templates with template-denoised contrastive learning for encoder embeddings. |
| 2 | 9,10 | RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval | 2401.18059 | Recursive SBERT-embed, UMAP+GMM-cluster (BIC), LLM-summarize tree; collapsed-tree retrieval |
| 2 | 10 | RankT5: Fine-Tuning T5 for Text Ranking with Ranking Losses | 2210.10634 | Listwise losses beat monoT5 by +1.8% MRR@10 (MARCO) / +2.8% (NQ), better zero-shot |
| 2 | 4 | SGPT: GPT Sentence Embeddings for Semantic Search | 2202.08904 | Contrastive fine-tune of GPT decoders (biased + weighted-mean pooling) for symmetric/asymmetric search; earliest proof decoders embed withou |
| 2 | 8 | SpecInfer: Accelerating Generative LLM Serving with Tree-based Speculative Inference and V | 2305.09781 | Small-model draft trees verified in parallel by target LLM; 1.5-2.8x distributed, 2.6-3.5x offloading |
| 2 | 8 | Splitwise: Efficient Generative LLM Inference Using Phase Splitting | 2311.18677 | Split prefill/decode onto different machines; 1.4x throughput at 20% lower cost, 2.35x same budget |
| 2 | 5 | Task-aware Retrieval with Instructions | 2211.09260 | BERRI multi-task instruction tuning with query-side-only instructions and instruction-unfollowing negatives. |
| 2 | 4 | The Embedder's Dilemma: LLMs Are Better, but at What Cost? | 2608.12875 | Controlled cost-aware comparison of 10 LLMs vs 26 embedding models on 37 tasks: tied in aggregate (0.4 pts), LLMs lead reasoning-heavy retri |
| 2 | 4 | The Truth Lies Somewhere in the Middle (of the Generated Tokens) | 2605.09969 | Mean pooling across autoregressively generated tokens beats any single token as a representation (kernel-alignment evidence); generated-stat |
| 2 | 3 | Training Sparse Mixture Of Experts Text Embedding Models | 2502.07972 | Sparse-MoE embedder: capacity without proportional inference cost |
| 2 | 7 | XGrammar: Flexible and Efficient Structured Generation Engine for Large Language Models | 2411.15100 | Byte-level PDA with token-mask cache and GPU-overlapped grammar execution, ~100x faster |
| 1 | 4,5 | Embedding-based In-Context Prompt Training for Enhancing LLMs as Text Encoders | 2605.01372 | EPIC replaces discrete demonstration tokens with trained embedding-based in-context prompts to keep ICL gains for embeddings while cutting t |
| 1 | 4 | Evaluating Embedding Generalization: How LLMs, LoRA, and SLERP Shape Representational Geom | 2511.21703 | Tests whether SLERP merging mitigates LoRA over-specialisation in embedding space; single-author study on synthetic numerical-sequence clust |
| 1 | 4 | Layer-wise Representation Dynamics: An Empirical Investigation Across Embedders and Base L | 2605.12714 | LRD framework (subspace motion, neighbourhood retention, final-layer alignment) applied to 31 models on 30 MTEB tasks; measurement toolkit f |
| 1 | 4 | Model soups: averaging weights of multiple fine-tuned models improves accuracy without inc | 2203.05482 | Plain weight averaging of same-base fine-tunes improves accuracy at zero inference cost; baseline every fancier merge must beat. |

## Refutations


## Abstained (unresolved ledger)

- Document Expansion by Query Prediction (1904.08375): Abs verified at primary source; mechanism covered by admitted synthetic-data items (Promptagator, InPars, GPL, E5-Mistral).
- Jina Embeddings 2: 8192-Token General-Purpose Text Embeddings for Long Documents (2310.19923): Verified; long-doc architecture relevant but BGE-M3 covers 8k context among admits.
- LoRA: Low-Rank Adaptation of Large Language Models (2106.09685): Abs verified at primary source; covered via admitted QLoRA which builds on it.
- MiniCPM-Embedding (no paper; HF model card only) (none): Verified HF card carries no paper link; method claims unverifiable. Secondary source only.
- MiniCPM4: efficient end-side LLM (2506.07900): Generative base model, not an embedder; background only.
- RAGAs: Automated Evaluation of Retrieval Augmented Generation (no-arXiv-id): Could not verify at a primary source: no arXiv id, ACL Anthology page not fetched, and GitHub API was rate-limited when resolving the code repo. Secondary sourc
- Representation Learning with Contrastive Predictive Coding (1807.03748): Abs verified at primary source; objective background only, no training recipe per se.
- Smarter, Better, Faster, Longer: A Modern Bidirectional Encoder for Fast, Memory Efficient (2412.13663): Verified; efficient-encoder counterpoint, but no head-to-head vs decoder-embedders fetched; thin for verdict.
- Towards General Text Embeddings with Multi-stage Contrastive Learning (2308.03281): Verified relevant via arXiv API; deprioritized under lane budget, subsumed by admitted two-stage items (E5, Qwen3-Embedding).
- AnglE-optimized Text Embeddings (2309.12871): Verified relevant via arXiv API; objective variant, deprioritized under lane budget.
- Augmented SBERT: Data Augmentation Method for Improving Bi-Encoders for Pairwise Sentence  (2010.08240): Abs page opened for title/authors but abstract not read; abstaining regardless as training augmentation (lane 2 scope).
- BiXSE: Improving Dense Retrieval via Probabilistic Graded Relevance Distillation (2508.06781): Screened via arXiv API title search only; abs page not opened under lane budget.
- Curriculum Learning for Dense Retrieval Distillation (2204.13679): Screened via arXiv API title search only; abs page not opened under lane budget.
- DiskANN: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node (no-arXiv-found): No arXiv id found via fetched title search; repo admitted instead
- Evaluating the Zero-Shot Robustness of Instruction-Tuned Models (https://proceedings.iclr.cc/paper_files/paper/2024/file/d3221cdb27e49d9c1cd35ad254feccfe-Paper-Conference.pdf): Proceedings PDF excerpt fetched but arXiv id and authorship not verified at a primary landing page.
- InPars-Light: Cost-Effective Unsupervised Training of Efficient Rankers (2301.02998): Verified at abs page but abstaining: reranker training is lane 10 scope.
- KV-Embedding: Training-free Text Embedding via Internal KV Re-routing in Decoder-only LLMs (2601.01046): Seen only as a citing excerpt inside another fetched page; abs page never opened and numbers not verified.
- Llama2Vec: Unsupervised Adaptation of Large Language Models for Dense Retrieval (2312.15503): Abs page verified; belongs to lanes 2/4 - screened for dedupe only
- Pairwise Relevance Distillation for Dense Retrieval (2410.01383): Screened via arXiv API title search only; abs page not opened under lane budget.
- Product quantization for nearest neighbor search (no-arXiv): No arXiv PDF available; covered indirectly via admitted Faiss paper which builds on it
- Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods (no-arXiv-DOI-only): Could not verify at primary source (no arXiv PDF per lane rules); do not cite numbers
- SFR-Embedding-Mistral: Enhance Text Retrieval with Transfer Learning (unverified): Secondary sources only (vendor blog plus HF card fetched); no paper or primary recipe found, so nothing quotable on instruction design.
- SPLADE: Sparse Lexical and Expansion Model for First Stage Ranking (2107.05720): Abs page verified; not separately filed - content subsumed by admitted SPLADEv2, recorded for dedupe
- TSDAE: Using Transformer-based Sequential Denoising Auto-Encoder for Unsupervised Sentence (2104.06979): Verified at abs page but abstaining: training method is lane 2 scope; GPL (admitted) covers private-corpus adaptation for this lane.
- A Dual-Task Paradigm to Investigate Sentence Comprehension Strategies in Language Models (2604.26351): Abs page opened; off-lane. Recorded so the miss is not silently dropped.
- Analysis of Local Anisotropy Fluctuations in Compact Objects (2310.01730): Wrong id from memory; GTE-line coverage deferred to Qwen3-Embedding row (successor series).
- IMAGINE: An Integrated Model of Artificial Intelligence-Mediated Communication Effects (2212.08658): Recalled as IRCoT id from memory; abs page shows it is a different paper. Correct IRCoT id is 2212.10509.
- Multi-view Intent Learning and Alignment with Large Language Models for Session-based Reco (2402.13840): Wrong id from memory; correct echo-embeddings id resolved separately (2402.15449).
- On Pruning State-Space LLMs (2502.18886): Recalled as PathRAG id from memory; abs page shows it is a different paper. Recorded to prevent re-screening.
- WRONG ID probe: A Communication Theory Perspective on Prompting Engineering Methods (2310.18358): Opened arxiv abs: mismatch. FastGen admitted separately as 2401.08671.
- WRONG ID probe: Blow-up of solutions for semilinear parabolic equation (2402.05040): Opened arxiv abs: mismatch. HydraGen admitted separately as 2402.05099.
- WRONG ID probe: Drag-guided diffusion models for vehicle image generation (2306.09935): Opened arxiv abs: title/authors do not match. Recorded to prevent re-screening; Orca admitted separately via USENIX.
- WRONG ID probe: Statistical Guarantees for Link Prediction using GNNs (2402.02692): Opened arxiv abs: mismatch. DistServe admitted separately as 2401.09670.
- When Does Pretraining Help? Assessing Self-Supervised Learning for Law and the CaseHOLD Da (2104.08671): Wrong id from memory; correct BEIR paper id not resolved. BEIR coverage deferred to MTEB/MMTEB rows.
- n/a (recalled id actually a Collatz paper) (2304.10491): Abs page contradicts recall. Correct RepLLaMA id not established this session.
- n/a (recalled id actually a QCD paper) (2311.16402): Could not verify as merging work; abs page contradicts recall. Correct DARE paper admitted as SuperMario-DARE 2311.03099.
- n/a (recalled id actually a phylogeny paper) (2311.10913): Abs page contradicts recall. Correct LM-Cocktail admitted as 2311.13534.
- uniCOIL: Unified and Effective Weighting for Contextualized Inverted Lists (unresolved): Could not resolve a verified arXiv id from fetched search results; will not cite
