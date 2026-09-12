# Merge summary

Rows read: 326 across 10 lanes ({'1': 26, '2': 34, '3': 39, '4': 47, '5': 32, '6': 36, '7': 24, '8': 31, '9': 22, '10': 35}). Unique items after dedup: 288. Dispositions: {'admit': 221, 'refute': 6, 'abstain': 58, '': 3}. Admitted PDFs staged: 227. Malformed rows skipped: 0.

## Admitted, by relevance

| relevance | lanes | title | id / repo | one line |
|---|---|---|---|---|
| 3 | 10 | A Neural Corpus Indexer for Document Retrieval | 2206.02743 | Seq2seq retriever with prefix-aware weight-adaptive decoder, semantic docids from hierarchical k-means, query-generation augmentation and co |
| 3 | 5 | A Rank Stabilization Scaling Factor for Fine-Tuning with LoRA | 2312.03732 | Standard alpha/r scaling collapses gradients as rank grows; alpha/sqrt(r) stabilizes and unlocks gains from r up to 2048 on Llama 2 + OpenOr |
| 3 | 8 | A comparison of statistical significance tests for information retrieval evaluation | 10.1145/1321440.1321528 | Randomization, bootstrap-shift, and paired t-tests agree on TREC runs; Wilcoxon and sign tests mislead and should be discontinued. |
| 3 | 1 | APIGen: Automated Pipeline for Generating Verifiable and Diverse Function-Calling Datasets | 2406.18518 | Format+execution+semantic 3-stage verification; 1.3B beats GPT-3.5 |
| 3 | 8,9 | ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems | 2311.09476 | Fine-tunes lightweight judges on synthetic data; scores context relevance, faithfulness, answer relevance with PPI confidence intervals from |
| 3 | 9 | Adapting Language Models to Compress Contexts | 2305.14788 | Unsupervised summary-vector compression with summary accumulation; OPT/LLaMA-2 to 30k tokens on one 80GB GPU. |
| 3 | 1 | An LLM Compiler for Parallel Function Calling | 2312.04511 | Plan-then-DAG-execute grammar for parallel calls; TinyAgent builds on it |
| 3 | 7 | Anchored Preference Optimization and Contrastive Revisions: Addressing Underspecification  | 2408.06266 | APO-zero/APO-down controllable DPO family; 32K CLAIR revision pairs + APO closes Llama-3-8B to GPT-4-turbo gap by 45% on MixEval-Hard |
| 3 | 6,10 | Autoregressive Entity Retrieval | 2010.00904 | Generates entity names with constrained beam search; cross-encodes mention and entity |
| 3 | 10 | Autoregressive Search Engines: Generating Substrings as Document Identifiers | 2204.10628 | Generates corpus-grounded n-gram identifiers under FM-index-constrained decoding and scores documents by aggregating identifier scores. |
| 3 | 4 | BACK TO BASICS: REVISITING REINFORCE STYLE OPTIMIZATION FOR LEARNING FROM HUMAN FEEDBACK I | 2402.14740 | REINFORCE leave-one-out baseline outperforms PPO and DPO/RAFT at lower cost; no critic network |
| 3 | 8 | BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models | 2104.08663 | 18-dataset zero-shot retrieval benchmark with nDCG@10/Recall@100 protocol; BM25 stays a hard baseline. |
| 3 | 8 | Benchmark Data Contamination of Large Language Models: A Survey | 2406.04244 | Taxonomy of contamination types plus detection (n-gram overlap, membership inference, order tests) and mitigation; documents paraphrase-evas |
| 3 | 3 | Beyond LoRA vs. Full Fine-Tuning: Gradient-Guided Optimizer Routing for LLM Adaptation | 2605.07111 | Optimizer-level routing between FFT and LoRA experts tested at Gemma-3-1B and Qwen2.5-1.5B/3B |
| 3 | 6 | Combining Constrained and Unconstrained Decoding via Boosting: BoostCD and Its Application | 2506.14901 | Boosted model fuses constrained+unconstrained base runs; BoostIE beats SynthIE by +17 micro-F1 in-dist, +11 OOD |
| 3 | 10 | CorpusLM: Towards a Unified Language Model on Corpus for Knowledge-Intensive Tasks | 2402.01176 | One model unifies generative retrieval, closed-book generation and RAG in a single greedy DocIDs-References-Answer decode with ranking-orien |
| 3 | 4 | DAPO: AN OPEN-SOURCE LLM REINFORCEMENT LEARNING SYSTEM AT SCALE | 2503.14476 | decoupled-clip plus dynamic-sampling GRPO variant; 50 points on AIME 2024 with Qwen2.5-32B; fully open |
| 3 | 4 | DEEPSEEK-PROVER-V1.5: HARNESSING PROOF ASSISTANT FEEDBACK FOR REINFORCEMENT LEARNING AND M | 2408.08152 | RLPAF: Lean 4 proof-assistant verdict as RL reward on a 7B prover; closest published validator-as-reward analogue |
| 3 | 4 | DEEPSEEK-R1: INCENTIVIZING REASONING CAPABILITY IN LLMS VIA REINFORCEMENT LEARNING | 2501.12948 | R1-Zero pure rule-reward RL plus distillation of reasoning traces into small models down to 1.5B |
| 3 | 4 | DEEPSEEKMATH: PUSHING THE LIMITS OF MATHEMATICAL REASONING IN OPEN LANGUAGE MODELS | 2402.03300 | GRPO origin paper: critic-free RL with group-normalized advantage; 7B reaches 51.7 percent on MATH |
| 3 | 4 | DISTILLM: TOWARDS STREAMLINED DISTILLATION FOR LARGE LANGUAGE MODELS | 2402.03898 | skew-KL loss plus adaptive off-policy use of student outputs; up to 4.3x speedup over on-policy KD |
| 3 | 4 | EVALUATING PARAMETER EFFICIENT METHODS FOR RLVR | 2512.23165 | first systematic PEFT-under-RLVR study on R1-Distill models: DoRA/AdaLoRA/MiSS beat LoRA; PiSSA spectral collapse; rank-1 bottlenecks |
| 3 | 1 | Efficient Guided Generation for Large Language Models | 2307.09702 | FSM-index constrained decoding at ~O(1) per step |
| 3 | 6 | Exploiting Asymmetry for Synthetic Training Data Generation: SynthIE and the Case of Infor | 2303.04132 | Generates 1.8M synthetic text-from-triples points with an LLM; small fine-tunes beat prior SOTA by +57 micro-F1 |
| 3 | 6 | Extract, Define, Canonicalize: An LLM-based Framework for Knowledge Graph Construction | 2404.03868 | Three-phase extract/define/canonicalize KGC with a trained schema retriever for large schemas |
| 3 | 1 | FoFo: A Benchmark to Evaluate LLMs' Format-Following Capability | 2402.18667 | Format-following is independent of content quality; open models lag |
| 3 | 6 | GLiNER: Generalist Model for Named Entity Recognition using Bidirectional Transformer | 2311.08526 | Span/type dot-product matching with DeBERTa-v3 encoder beats ChatGPT zero-shot NER; CPU/ONNX/INT8 deployable |
| 3 | 6 | GLiREL: Generalist Model for Zero-Shot Relation Extraction | 2501.03172 | All entity pairs x all labels classified in one forward pass; SOTA on FewRel/WikiZSL zero-shot |
| 3 | 7 | Gemma 2: Improving Open Language Models at a Practical Size | 2408.00118 | 2B/9B trained with KD instead of next-token prediction (>50x Chinchilla tokens); SFT (behavioral cloning + on-student distillation) + RLHF + |
| 3 | 7 | Gemma 3 Technical Report | 2503.19786 | 256-logit sampled KD pre-training; post-training = IT-teacher KD + RL phase (BOND/WARM/WARP variants); Gemma3-4B-IT competitive with Gemma2- |
| 3 | 6,8 | GenIE: Generative Information Extraction | 2112.08340 | First end-to-end autoregressive closed IE with bi-level constrained generation over a Wikidata schema |
| 3 | 10 | Generative Retrieval as Dense Retrieval | 2306.11397 | Analytic result: DSI/NCI-style generative retrieval decomposes into dot products between query and document vectors, i.e. a bi-encoder. |
| 3 | 6 | GoLLIE: Annotation Guidelines improve Zero-Shot Information-Extraction | 2310.03668 | Fine-tunes LLMs to follow annotation guidelines (label schemas as class definitions) for zero-shot IE |
| 3 | 1 | Gorilla: Large Language Model Connected with Massive APIs | 2305.15334 | First SFT recipe for API-call emission (LLaMA + retriever + APIBench) |
| 3 | 1 | Granite-Function Calling Model: Introducing Function Calling Abilities via Multi-task Lear | 2407.00121 | 7-task granular multi-task SFT with QLoRA r8 on 142k examples |
| 3 | 1 | Hammer: Robust Function-Calling for On-Device Language Models via Function Masking | 2410.04587 | Function masking + irrelevance augmentation; SFT harms abstention w/o negatives |
| 3 | 10 | How Does Generative Retrieval Scale to Millions of Passages? | 2305.11841 | At 8.8M passages only synthetic-query document representations matter; PAWA/2D-IDs/consistency-loss add nothing net of parameters, and naive |
| 3 | 10 | Improving Language Models by Retrieving from Trillions of Tokens | 2112.04426 | Frozen BERT retriever plus differentiable encoder and chunked cross-attention matches GPT-3-scale Pile performance with 25x fewer parameters |
| 3 | 9 | In-context Autoencoder for Context Compression in a Large Language Model | 2307.06945 | LoRA encoder (~1% params) compresses context to memory slots for a frozen LLM; AE+LM pretrain then instruction fine-tune; 4x. |
| 3 | 10 | InstructRetro: Instruction Tuning post Retrieval-Augmented Pretraining | 2310.07713 | Continued retrieval-augmented pre-training of a 43B GPT on 100B tokens over 1.2T-token store, then instruction tuning; the Retro encoder can |
| 3 | 9 | Is ChatGPT Good at Search? Investigating Large Language Models as Re-Ranking Agents | 2304.09542 | Instructional permutation generation with sliding window; GPT-4 beats supervised rankers; distilled 435M student beats 3B monoT5 on BEIR. |
| 3 | 8 | KILT: a Benchmark for Knowledge Intensive Language Tasks | 2009.02252 | Unifies 5 knowledge-intensive tasks on one snapshot; KILT score requires provenance (R-precision 1) AND downstream output correct: joint ret |
| 3 | 3 | KaLM: Knowledge-aligned Autoregressive Language Modeling via Dual-view Knowledge Graph Con | 2412.04948 | Joint explicit KG-alignment plus implicit AR objectives; reports prior attempts compromised generation |
| 3 | 6 | KnowCoder: Coding Structured Knowledge into LLMs for Universal Information Extraction | 2403.07969 | Python-class schema representation; 1.5B-token code pretrain then instruction tune; +49.8% few-shot vs LLaMA2 |
| 3 | 3 | Knowing but Not Saying: Preventing Factual Access Failures in LLM SFT via Recall-Anchored  | 2608.20794 | Base-anchored self-distillation on unlabeled OOD text; soft-distribution signal beats replay on same text |
| 3 | 7 | LFM2 Technical Report | 2511.23404 | SFT 3 epochs cosine 3e-5 to 1e-7 (500-step warmup, AdamW 0.9/0.95, wd 0.1); length-normalized offline+on-policy preference opt; model mergin |
| 3 | 2 | LIMA: Less Is More for Alignment | 2305.11206 | 1,000 curated examples align a 65B model (superficial-alignment hypothesis). |
| 3 | 4 | LITEGUI: DISTILLING COMPACT GUI AGENTS WITH REINFORCEMENT LEARNING | 2605.07505 | SFT-free on-policy (GKD-style) distillation plus dual-level GRPO unlocks 2B/3B agents past imitation-learning limits |
| 3 | 9 | LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression | 2403.12968 | Distils GPT-4 compression into a token-classification compressor (XLM-R/mBERT); task-agnostic, 3-6x faster. |
| 3 | 9 | LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models | 2310.05736 | Small-LM perplexity coarse-to-fine prompt compression with budget controller and distribution alignment, up to 20x compression. |
| 3 | 9 | Learning to Compress Prompts with Gist Tokens | 2304.08467 | Attention-mask trick that learns gist-token compression during instruction tuning at no extra cost; up to 26x. |
| 3 | 9 | Learning to Filter Context for Retrieval-Augmented Generation | 2311.08377 | Sentence-level context filtering trained on StrInc/lexical/CXMI silver labels; +3 pts avg, 44-64% shorter prompts. |
| 3 | 2 | Learning to Generate Instruction Tuning Datasets for Zero-Shot Task Adaptation (Bonito) | 2402.18334 | Conditional task generator turning unannotated text into instruction data; trained on 1.65M remixed examples. |
| 3 | 3,5 | LoRA Learns Less and Forgets Less | 2405.09673 | LoRA underperforms full FT on target but forgets less; full-FT perturbations are 10-100x the rank of LoRA |
| 3 | 5 | LoRA vs Full Fine-tuning: An Illusion of Equivalence | 2410.21228 | LoRA creates high-ranking intruder singular vectors that cause forgetting; scaling them down cuts forgetting with minimal task loss; fixed-a |
| 3 | 5 | LoRA+: Efficient Low Rank Adaptation of Large Models | 2402.12354 | Same LR for A and B is inefficient at width; fixed ratio eta_B >> eta_A gives ~2x speedup and 1-2% gains at LoRA cost. |
| 3 | 5 | LoRA-Null: Low-Rank Adaptation via Null Space for Large Language Models (v2 retitled Put t | 2503.02659 | Init A in null space of sampled pre-trained activations, freeze A, train B; higher rank trades retention for capacity; compares directly vs  |
| 3 | 5 | LoRA: Low-Rank Adaptation of Large Language Models | 2106.09685 | Freezes base weights, trains rank-r BA adapters; includes rank-deficiency and W_q/W_v-only ablations. |
| 3 | 3 | LoRAMoE: Alleviate World Knowledge Forgetting in Large Language Models via MoE-Style Plugi | 2312.09979 | Frozen backbone + routed LoRA experts with a world-knowledge expert split; forgetting worsens with more instruction data |
| 3 | 9 | LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compre | 2310.06839 | Question-aware compression via contrastive perplexity plus document reordering; NQ +21.4% with 4x fewer tokens. |
| 3 | 3 | LoraHub: Efficient Cross-Task Generalization via Dynamic LoRA Composition | 2307.13269 | Gradient-free composition of a library of task LoRAs for few-shot transfer |
| 3 | 9 | Lost in the Middle: How Language Models Use Long Contexts | 2307.03172 | U-shaped position bias; reader QA saturates by ~20 docs; recommends reranking and truncation. |
| 3 | 4 | MINILLM: ON-POLICY DISTILLATION OF LARGE LANGUAGE MODELS | 2306.08543 | reverse-KL on-policy distillation for generative LMs; scales 120M to 13B |
| 3 | 4 | MODEL ALIGNMENT AS PROSPECT THEORETIC OPTIMIZATION | 2402.01306 | matches/exceeds preference methods at 1B to 30B from binary desirable/undesirable signals only |
| 3 | 8 | MTEB: Massive Text Embedding Benchmark | 2210.07316 | 8-task embedding benchmark (retrieval, STS, clustering, rerank, classification...); no single method dominates all tasks. |
| 3 | 2 | Magpie: Alignment Data Synthesis from Scratch by Prompting Aligned LLMs with Nothing | 2406.08464 | Extracts instruction data from an aligned teacher using only its pre-query template; SFT-only rivals SFT+DPO pipelines. |
| 3 | 7 | MiniCPM4: Ultra-Efficient LLMs on End Devices | 2506.07900 | UltraChat v2 SFT dataset; ModelTunnel v2 hyperparam search; chunk-wise rollout load-balanced RL; BitCPM ternary QAT |
| 3 | 7 | MiniCPM: Unveiling the Potential of Small Language Models with Scalable Training Strategie | 2404.06395 | WSD LR schedule; decay-stage annealing on pretrain+SFT mix (20B tokens); separate ~6B-token SFT; DPO family member |
| 3 | 10 | MiniRAG: Towards Extremely Simple Retrieval-Augmented Generation | 2501.06713 | Heterogeneous chunk-entity graph plus lightweight topology retrieval lets 1.5B-4B SLMs (incl. MiniCPM3-4B, Qwen2.5-3B) match LLM RAG at 25 p |
| 3 | 3 | MoLoRA: Composable Specialization via Per-Token Adapter Routing | 2603.15965 | Per-token adapter routing proven optimal vs per-sequence; Qwen3-1.7B exceeds Qwen3-8B via specialization |
| 3 | 3 | NV-Embed: Improved Techniques for Training LLMs as Generalist Embedding Models | 2405.17428 | Latent-attention pooling plus causal-mask removal plus two-stage contrastive instruction tuning with hard negatives |
| 3 | 4 | ON-POLICY DISTILLATION OF LANGUAGE MODELS: LEARNING FROM SELF-GENERATED MISTAKES | 2306.13649 | trains student on its own generated sequences with teacher feedback; unifies distillation with RLHF |
| 3 | 5 | OPLoRA: Orthogonal Projection LoRA Prevents Catastrophic Forgetting during Parameter-Effic | 2510.13003 | Double-sided projections constrain updates to orthogonal complement of top-k singular subspace with preservation proof; rho_k interference m |
| 3 | 3 | On-Policy Replay for Continual Supervised Fine-Tuning | 2605.29495 | Replay of reward-filtered own-outputs as plain SFT; no teacher; KL-shrinkage interpretation; BWT -13.93 to -0.65 |
| 3 | 7 | Phi-4 Technical Report | 2412.08905 | 50-type synthetic data factory (~400B tokens: multi-agent prompting, self-revision, instruction reversal); SFT then pivotal-token DPO + judg |
| 3 | 7 | Phi-4-Mini Technical Report: Compact yet Powerful Multimodal Language Models via Mixture-o | 2503.01743 | 3.8B on synthetic-heavy reasoning/code mix with enlarged function-calling + summarization SFT; frozen backbone + per-modality LoRA routers ( |
| 3 | 7 | Phi-4-Mini-Reasoning: Exploring the Limits of Small Reasoning Language Models in Math | 2504.21233 | 3.8B: large-scale mid-training on distilled long-CoT, SFT on 200K curated CoT, rollout DPO on 300K pairs (LR 5e-7, 1 epoch), then verifiable |
| 3 | 8 | Prediction-Powered Inference | 2301.09633 | Valid confidence intervals combining a small labeled set with many model predictions; more accurate predictor means tighter intervals. |
| 3 | 8 | Prometheus 2: An Open Source Language Model Specialized in Evaluating Other Language Model | 2405.01535 | Adds pairwise ranking via weight-merged direct-assessment and preference models; 0.6-0.7 Pearson with GPT-4, 72-85pct human agreement. |
| 3 | 8 | Prometheus: Inducing Fine-grained Evaluation Capability in Language Models | 2310.08491 | Open 13B evaluator trained on 1K rubrics/100K GPT-4 feedbacks; Pearson 0.897 with humans, on par with GPT-4 when reference materials accompa |
| 3 | 7 | Qwen2.5 Technical Report | 2412.15115 | SFT on 1M+ samples, 2 epochs, seq 32768, LR 7e-6 to 7e-7, wd 0.1; then offline DPO + online GRPO |
| 3 | 7 | Qwen3 Technical Report | 2505.09388 | 4-stage post-training (long-CoT cold start, reasoning GRPO on 3995 pairs, mode-fusion SFT, general RL); small models via off-policy + on-pol |
| 3 | 10 | RA-DIT: Retrieval-Augmented Dual Instruction Tuning | 2310.01352 | Lightweight two-step retrofit of any LLM (7B/13B/65B tested): retrieval-augmented instruction tuning for the LM plus LM-supervised retriever |
| 3 | 2,10 | RAFT: Adapting Language Model to Domain Specific RAG | 2403.10131 | Trains with golden + distractor documents and CoT answers so the model reasons over retrieved context. |
| 3 | 9 | RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval | 2401.18059 | Recursive embed-cluster-summarize tree; collapsed-tree retrieval mixes abstraction levels; QuALITY +20pp with GPT-4. |
| 3 | 10 | REALM: Retrieval-Augmented Language Model Pre-Training | 2002.08909 | First unsupervised joint pre-training of a dense retriever with an LM via backprop through MIPS over millions of docs with async index refre |
| 3 | 9 | RECOMP: Improving Retrieval-Augmented LMs with Compression and Selective Augmentation | 2310.04408 | End-task-trained extractive and abstractive query-focused compressors with selective (possibly empty) augmentation. |
| 3 | 4 | REINFORCEMENT LEARNING FOR REASONING IN LARGE LANGUAGE MODELS WITH ONE TRAINING EXAMPLE | 2504.20571 | 1-example RLVR lifts Qwen2.5-Math-1.5B MATH500 36.0 to 73.6 percent; matches 1.2k-example run; entropy bonus critical |
| 3 | 10 | REPLUG: Retrieval-Augmented Black-Box Language Models | 2301.12652 | Black-box LM with a tunable retriever supervised by LM perplexity (REPLUG LSR); improves GPT-3 175B LM likelihood 6.3 percent and Codex 5-sh |
| 3 | 4 | RLAIF VS. RLHF: SCALING REINFORCEMENT LEARNING FROM HUMAN FEEDBACK WITH AI FEEDBACK | 2309.00267 | AI-labeled preferences match RLHF; works even when labeler equals policy size; direct-RLAIF scores rewards straight from an off-the-shelf LL |
| 3 | 8 | Ragas: Automated Evaluation of Retrieval Augmented Generation | 2309.15217 | Reference-free RAG metrics (faithfulness, answer relevance, context relevance) via LLM prompts; validated against human judgments on WikiEva |
| 3 | 10 | RankRAG: Unifying Context Ranking with Retrieval-Augmented Generation in LLMs | 2407.02485 | One instruction-tuned LLM does both context ranking and answer generation; a small ranking-data fraction beats expert rankers and lifts nine |
| 3 | 6 | ReLiK: Retrieve and LinK, Fast and Accurate Entity Linking and Relation Extraction on an A | 2408.00103 | Retriever-reader EL+RE with shared reader doing closed IE in one forward pass; SOTA on academic budget |
| 3 | 3 | Repetition Improves Language Model Embeddings | 2402.15449 | Echo (repeat-input) embeddings from causal LMs gain 5%+ zero-shot with no architecture change |
| 3 | 6,8 | Revisiting DocRED - Addressing the False Negative Problem in Relation Extraction | 2205.12696 | Re-annotated 4053 docs (64.6% triples were missing); models gain ~13 F1; adds freq/long-tail/intra/inter metrics |
| 3 | 4 | SCALING FLAWS OF VERIFIER-GUIDED SEARCH IN MATHEMATICAL REASONING | 2502.00271 | imperfect verifiers misrank and prune all valid paths at scale; repeated sampling overtakes verifier search; holds at 7B |
| 3 | 4 | SCALING RELATIONSHIP ON LEARNING MATHEMATICAL REASONING WITH LARGE LANGUAGE MODELS | 2308.01825 | rejection-sampling fine-tuning on self-generated correct paths; log-linear data scaling; LLaMA-7B GSM8K 35.9 to 49.3 percent |
| 3 | 4 | SEQUENCE-LEVEL KNOWLEDGE DISTILLATION | 1606.07947 | train student on teacher-generated sequences rather than token labels; best student 10x faster with little loss |
| 3 | 4 | STAR: BOOTSTRAPPING REASONING WITH REASONING | 2203.14465 | iterative loop: generate rationales, keep those yielding correct answers (validator filter), retrain; matches 30x larger SOTA |
| 3 | 4 | SUPERCORRECT: ADVANCING SMALL LLM REASONING WITH THOUGHT TEMPLATE DISTILLATION AND SELF-CO | 2410.09008 | teacher thought-templates plus cross-model DPO teach 7B student self-correction; beats DeepSeekMath-7B by 7.8/5.3 percent |
| 3 | 5 | Scaling Laws for Forgetting When Fine-Tuning Large Language Models | 2401.05605 | PEFT still forgets: forgetting is inverse-linear in FT loss and a shifted power law in params-tuned and steps; proposes pre/post cross-entro |
| 3 | 2 | Scaling Synthetic Data Creation with 1,000,000,000 Personas | 2406.20094 | 1B web-mined personas as generation lenses for math, instructions, knowledge, NPC and tool data. |
| 3 | 2 | Self-Alignment with Instruction Backtranslation | 2308.06259 | Backtranslates instructions from unannotated web segments (502K) and filters by self-consistency; beats text-davinci-003 win-rate. |
| 3 | 2 | Self-Instruct: Aligning Language Models with Self-Generated Instructions | 2212.10560 | Bootstraps 52K instructions from seed tasks with similarity filtering; +33% absolute on SuperNI. |
| 3 | 9,10 | Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | 2310.11511 | Reflection tokens for on-demand retrieval and self-critique distilled offline from GPT-4; 7B beats ChatGPT on ODQA/reasoning. |
| 3 | 7 | SmolLM2: When Smol Goes Big -- Data-Centric Training of a Small Language Model | 2502.02737 | 1.7B on 11T tokens multi-stage; SFT on SmolTalk 2 epochs LR 3e-4 BS128 seq8192; DPO on UltraFeedback 2 epochs LR 1e-6 beta 0.5 |
| 3 | 7 | SmolTulu: Higher Learning Rate to Batch Size Ratios Can Lead to Better Reasoning in SLMs | 2412.08347 | Tulu-3 pipeline adapted to SmolLM2-1.7B: reasoning (ARC/GSM8K) wants high LR/BS ratio (SFT LR/BS 11.25e-6), DPO 8e-7/BS12 len-normed beta 5. |
| 3 | 1 | SynCode: LLM Generation with Grammar Augmentation | 2403.01632 | Sound/complete CFG decoding; 100% JSON-schema validity on Gemma2-2B |
| 3 | 6,8 | Text2KGBench: A Benchmark for Ontology-Driven Knowledge Graph Generation from Text | 2308.02357 | Ontology-conditioned fact extraction eval: P/R/F1 + ontology conformance + subject/relation/object hallucination |
| 3 | 1 | The Berkeley Function Calling Leaderboard: From Tool Use to Agentic Evaluation of Large La | none (PMLR v267 patil25a) | AST/execution function-call eval; de-facto standard small-model gate |
| 3 | 1 | TinyAgent: Function Calling at the Edge | 2409.00608 | Narrow-task SFT takes 1.1B 12.7%->80% success, beating GPT-4-Turbo |
| 3 | 1 | ToolACE: Winning the Points of LLM Function Calling | 2409.00920 | API self-evolution + complexity-guided dialogs + dual verification; LoRA r16 |
| 3 | 1 | ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs | 2307.16789 | DFSDT multi-agent data pipeline + ToolBench 16k-API benchmark |
| 3 | 3 | Towards Modular LLMs by Building and Reusing a Library of LoRAs | 2405.11157 | Zero-shot Arrow routing over an MBC-clustered LoRA library; matches/outperforms joint training |
| 3 | 10 | Transformer Memory as a Differentiable Search Index | 2202.06991 | Single Transformer maps queries directly to docids; indexing and retrieval trained jointly with atomic and semantic-string docids. |
| 3 | 2,7 | Tulu 3: Pushing Frontiers in Open Language Model Post-Training | 2411.15124 | Fully open SFT + length-normalized DPO + RLVR (verifiable-reward RL) pipeline; decontaminated evals; recipe SmolTulu replicates |
| 3 | 4 | UNDERSTANDING R1-ZERO-LIKE TRAINING: A CRITICAL PERSPECTIVE | 2503.20783 | identifies GRPO length/normalization bias; Dr.GRPO unbiased objective; minimalist 7B recipe reaches 43.3 percent AIME 2024 |
| 3 | 6 | Universal Information Extraction as Unified Semantic Matching | 2301.03282 | Three directed token-linking ops replace generation; 356M model beats UIE-large by 5.11 few-shot |
| 3 | 6 | UniversalNER: Targeted Distillation from Large Language Models for Open Named Entity Recog | 2308.03279 | Distills ChatGPT NER annotations on Pile passages into 7B/13B students; beats ChatGPT by 7-9 F1 |
| 3 | 6 | WEBIE: Faithful and Robust Information Extraction on the Web | 2305.14293 | C4-based generative IE with negatives and ~21K crowdsourced triples + 4-language mWebIE; entity-linking aux improves faithfulness |
| 3 | 8 | WebIE: Faithful and Robust Information Extraction on the Web | 10.18653/v1/2023.acl-long.428 | 1.6M-sentence web closed-IE set WITH negatives; REBEL-only models score 0pct on negatives; entity-linking auxiliary head best for faithfulne |
| 3 | 3 | When Synthetic Data Hurts: On Catastrophic Forgetting in Skill Retrieval for LLM Agents | 2609.10750 | Synthetic retrieval fine-tuning causes forgetting at 0.6B; embedding-anchor reg/LwF/EWC/L2 recover OOD and gain +13.98% in-distribution |
| 3 | 2 | WizardLM: Empowering large pre-trained language models to follow complex instructions | 2304.12244 | Evolves seed instructions in-depth/in-breadth then mixes all levels for SFT. |
| 3 | 2,4,7 | code artefact: minimal R1-Zero reproduction | n/a | verifiable-reward RL on 3B-scale models for a counting task; canonical tiny RL starter |
| 3 | 1 | xLAM: A Family of Large Action Models to Empower AI Agent Systems | 2409.03215 | SFT+DPO function-calling family incl. 1B model; data reused by Hammer |
| 2 | 10 | A Survey of Generative Information Retrieval | 2406.01197 | Taxonomy of DocID strategies (single-token, sequential, text-based) and indexing-versus-retrieval training, with future directions on learna |
| 2 | 1 | API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs | 2304.08244 | 73-API executable dialogue benchmark used by Granite/Hammer for generalisation |
| 2 | 10 | Active Retrieval Augmented Generation | 2305.06983 | Forward-looking active retrieval: draft the next sentence, use it as the retrieval query, and regenerate only when low-confidence tokens app |
| 2 | 5 | AdaLoRA: Adaptive Budget Allocation for Parameter-Efficient Fine-Tuning | 2303.10512 | Allocates rank budget by importance across matrices with SVD parametrization + cubic schedule; biggest wins at low budgets. |
| 2 | 2 | AlpaGasus: Training A Better Alpaca with Fewer Data | 2307.08701 | ChatGPT-judge filters 52K Alpaca to 9K; trains 7B/13B faster and better. |
| 2 | 10 | Atlas: Few-shot Learning with Retrieval Augmented Language Models | 2208.03299 | Contriever plus FiD jointly pre-trained with periodic index refresh and query-side fine-tuning; 64-shot NQ beats a 540B model with 50x fewer |
| 2 | 2 | Beyond neural scaling laws: beating power law scaling via data pruning | 2206.14486 | Prototype-based pruning beats power-law data scaling on CIFAR/ImageNet/SVHN; only scaling-law-shaped pruning evidence found. |
| 2 | 10 | Bridging the Gap Between Indexing and Retrieval for Differentiable Search Index with Query | 2206.10128 | Diagnoses DSI train-serve mismatch (long documents indexed, short queries retrieved) and fixes it by indexing cross-encoder-filtered generat |
| 2 | 6 | ChatIE: Zero-Shot Information Extraction via Chatting with ChatGPT | 2302.10205 | Two-stage multi-turn QA decomposition of RE/NER/EE; beats some full-shot models (e.g. NYT11-HRL) |
| 2 | 9 | Compressing Context to Enhance Inference Efficiency of Large Language Models | 2310.06201 | Self-information filtering of lexical units; 50% context cut at minor quality loss; thresholds are domain-dependent. |
| 2 | 10 | CorpusBrain++: A Continual Generative Pre-Training Framework for Knowledge-Intensive Langu | 2402.16767 | Pre-trained CorpusBrain catastrophically forgets on the new KILT++ continual benchmark; rehearsal-plus-regularization continual generative p |
| 2 | 10 | CorpusBrain: Pre-train a Generative Retrieval Model for Knowledge-Intensive Language Tasks | 2208.07652 | Generative-retrieval pre-training with inner-sentence-selection, lead-paragraph-selection and hyperlink-identifier-prediction tasks, then si |
| 2 | 4 | DIRECT PREFERENCE OPTIMIZATION: YOUR LANGUAGE MODEL IS SECRETLY A REWARD MODEL | 2305.18290 | solves RLHF with a classification loss, no reward model or RL loop; stable and cheap |
| 2 | 4 | DISTILLM-2: A CONTRASTIVE APPROACH BOOSTS THE DISTILLATION OF LLMS | 2503.07067 | contrastive distillation: raise likelihood of teacher responses while lowering student ones; covers instruction-following, code, preference  |
| 2 | 6 | DREEAM: Guiding Attention with Evidence for Improving Document-Level Relation Extraction | 2302.08675 | Supervises transformer attention with sentence-evidence distributions (zero extra parameters) + ER self-training on distant data |
| 2 | 2 | Deduplicating Training Data Makes Language Models Better | 2107.06499 | Near + exact dedup of C4/RealNews/LM1B/Wiki40B improves perplexity and cuts memorization. |
| 2 | 10 | Dense Passage Retrieval for Open-Domain Question Answering | 2004.04906 | Dual-encoder trained with one BM25 hard negative plus in-batch negatives; +9-19 point top-20 gains over BM25 and the initializer for RAG joi |
| 2 | 5 | DoRA: Weight-Decomposed Low-Rank Adaptation | 2402.09353 | Decomposes weights into magnitude + direction, LoRA on direction; mimics FT learning pattern and beats LoRA on LLaMA/LLaVA/VL-BART. |
| 2 | 2 | DoReMi: Optimizing Data Mixtures Speeds Up Language Model Pretraining | 2305.10429 | 280M proxy + group-DRO finds domain weights; 8B Pile training speeds up 2.6x. |
| 2 | 6 | DocRED: A Large-Scale Document-Level Relation Extraction Dataset | 1906.06127 | 132k-entity human-annotated document-level RE from Wikipedia/Wikidata plus distant supervision |
| 2 | 2 | Enhancing Chat Language Models by Scaling High-quality Instructional Conversations (UltraC | 2305.14233 | Topic-scaffolded two-agent generation of 1.5M multi-turn dialogues. |
| 2 | 7 | Enhancing Small LLM Alignment through Margin-Based Objective Modifications under Resource  | 2508.08466 | Hinge-margin APO-zero variant for 0.5B-scale: zero gradient on easy pairs (hard-example mining), best AlpacaEval WR 36.02 / LC 17.07 |
| 2 | 8 | FLASK: Fine-grained Language Model Evaluation based on Alignment Skill Sets | 2307.10928 | 12-skill instance-wise rubric eval; fine-grained scoring raises human-model correlation and robustness to verbosity gaming. |
| 2 | 1 | FireAct: Toward Language Agent Fine-tuning | 2310.05915 | ReAct-trajectory fine-tuning: small models beat prompted large ones |
| 2 | 10 | From Matching to Generation: A Survey on Generative Information Retrieval | 2404.14851 | Two-branch survey: generative document retrieval plus reliable response generation (memorization, augmentation, attribution), with increment |
| 2 | 1,6 | Functionary (MeetKai function-calling SFT codebase + Small/Medium v2.x models) | none | Open SFT recipe for chat-with-tools at small scale incl. Small models |
| 2 | 6 | GLiDRE: Generalist Lightweight model for Document-level Relation Extraction | 2508.00757 | GLiNER-style bi-encoder extended to document-level relation extraction |
| 2 | 6 | GLiNER2: An Efficient Multi-Task Information Extraction System with Schema-Driven Interfac | 2507.18546 | Multi-task IE (NER+RE+hierarchical) behind a schema-driven interface |
| 2 | 5 | GaLore: Memory-Efficient LLM Training by Gradient Low-Rank Projection | 2403.03507 | Full-parameter learning with low-rank gradient projections; 65.5% optimizer memory cut; Llama 7B pre-train on 24GB without ReLoRA-style warm |
| 2 | 10 | Generation-Augmented Retrieval for Open-domain Question Answering | 2009.08553 | Reverse direction: a generator expands the query with heuristically discovered contexts and BM25 over expansions matches or beats DPR; fusin |
| 2 | 9 | Generative Agents: Interactive Simulacra of Human Behavior | 2304.03442 | Memory stream with relevance-recency-importance retrieval plus reflection synthesis; ablations and failure taxonomy (retrieval failure, conf |
| 2 | 8 | Holistic Evaluation of Language Models | 2211.09110 | Multi-metric standard (accuracy, calibration, robustness, fairness, toxicity, efficiency) over 16 core scenarios; reporting template for joi |
| 2 | 10 | In-Context Retrieval-Augmented Language Models | 2302.00083 | Prepending retrieved passages with no LM changes gives gains equivalent to 2-3x parameters across 110M-66B models; ranking the retriever for |
| 2 | 10 | IncDSI: Incrementally Updatable Document Retrieval | 2307.10323 | New documents indexed in 20-50 ms by constrained optimization over the added docid vector only, matching full-retrain retrieval quality with |
| 2 | 6 | InstructUIE: Multi-task Instruction Tuning for Unified Information Extraction | 2304.08085 | IE INSTRUCTIONS (32 datasets) instruction-tuned FlanT5-11B; matches BERT supervised, beats GPT-3.5 zero-shot |
| 2 | 2 | Instruction Mining: Instruction Data Selection for Tuning Large Language Models | 2307.06290 | Lightweight metric rule blending quality/diversity for picking small high-performing subsets. |
| 2 | 3 | Internalizing Tool Knowledge in Small Language Models via QLoRA Fine-Tuning | 2605.17774 | 4B QLoRA on ~1700 tool-use traces internalizes structured planning; rank 32 best quality, smaller ranks retain more |
| 2 | 6 | KGGen: Extracting Knowledge Graphs from Plain Text with Language Models | 2502.09956 | LLM pipeline for open KG extraction from plain text |
| 2 | 6 | KnowCoder-X: Boosting Multilingual Information Extraction via Code | 2411.04794 | IE cross-lingual alignment phase + code schemas; 64 benchmarks, +30% over ChatGPT cross-lingual, 20 African languages |
| 2 | 3 | LAMOL: LAnguage MOdeling for Lifelong Language Learning | 1909.03329 | LM head generates pseudo-samples of old tasks as replay; within 2-3% of multitask upper bound |
| 2 | 2 | LESS: Selecting Influential Data for Targeted Instruction Tuning | 2402.04333 | Gradient datastore (LoRA warmup) + influence picks 5% subsets beating full data on MMLU/TyDiQA/BBH. |
| 2 | 8 | Large Language Models for Generative Information Extraction: A Survey | 2312.17617 | Technique taxonomy (augmentation, prompts, constrained decoding, SFT) with empirical finding that SFT dominates few/zero-shot and universal  |
| 2 | 5 | Learning Rate Scaling across LoRA Ranks and Transfer to Full Finetuning | 2602.06204 | muA theory: optimal LR is rank-invariant under alpha=r^-1 but scales ~1/sqrt(r) under constant alpha; LoRA-tuned LRs transfer to full FT. |
| 2 | 3 | Learning without Forgetting | 1606.09282 | Self-distillation against old-task outputs using only new-task data |
| 2 | 3 | Length-Induced Embedding Collapse in PLM-based Models | 2410.24200 | Long-text embeddings cluster via attention low-pass filtering; TempScale temperature mitigation |
| 2 | 10 | Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering | 2007.01282 | Fusion-in-Decoder encodes each retrieved passage independently and fuses evidence in the decoder; accuracy keeps improving to ~100 passages. |
| 2 | 5 | LoRA-FA: Memory-efficient Low-rank Adaptation for Large Language Models Fine-tuning (v3 re | 2308.03303 | Freezes A, trains B only: removes A-activation memory (1.4x vs LoRA), matches LoRA/FT; poor on Math/Code noted by LoRA-Null authors. |
| 2 | 5 | LoftQ: LoRA-Fine-Tuning-Aware Quantization for Large Language Models | 2310.08659 | Jointly optimizes quantized Q + LoRA init to close QLoRA gap; converges at 2-bit where QLoRA fails; Llama-2-7B/13B evidence. |
| 2 | 8 | MMTEB: Massive Multilingual Text Embedding Benchmark | 2502.13595 | Community expansion of MTEB: 500+ quality-controlled tasks incl. instruction-following and long-document retrieval. |
| 2 | 3 | Mechanistic origins of catastrophic forgetting: why RL preserves circuits better than SFT? | 2605.28860 | Head-level circuit analysis on Qwen2.5-3B: SFT adapts faster but disrupts circuits; RL preserves base circuit |
| 2 | 9 | MemGPT: Towards LLMs as Operating Systems | 2310.08560 | OS-style virtual context management: hierarchical memory with function-call paging and heartbeat chaining. |
| 2 | 5 | MiLoRA: Harnessing Minor Singular Components for Parameter-Efficient LLM Finetuning | 2406.09044 | Updates only minor singular components, freezes principal ones; init orthogonal to principal subspace; wins on commonsense/math/instruction/ |
| 2 | 2 | Nemotron-CC: Transforming Common Crawl into a Refined Long-Horizon Pretraining Dataset | 2412.02595 | Classifier ensembling + synthetic rephrasing keep 6.3T tokens for 15T-horizon training; +5.6 MMLU over DCLM at 8B/1T. |
| 2 | 3 | On the Sentence Embeddings from Pre-trained Language Models | 2011.05864 | Untuned contextual embeddings live in an anisotropic cone; flow-based isotropy transform restores STS |
| 2 | 5 | Orthogonal Subspace Learning for Language Model Continual Learning (O-LoRA) | 2310.14152 | Sequential tasks in mutually orthogonal LoRA subspaces without replay; +24% over LFPT5; preserves unseen-task generalization. |
| 2 | 3 | Overcoming catastrophic forgetting in neural networks | 1612.00796 | Fisher-weighted anchor to old-task weights enables sequential task learning |
| 2 | 4 | PART I: TRICKS OR TRAPS? A DEEP DIVE INTO RL FOR LLM REASONING | 2508.08221 | systematic reproduction of RL-for-reasoning techniques in one framework with selection guidelines; vanilla-PPO-loss minimalist combo beats G |
| 2 | 6 | PIVOINE: Instruction Tuning for Open-world Entity Profiling | 10.18653/v1/2023.findings-emnlp.1009 | Instruction tuning for open-world entity profiling (open-world IE sub-task) |
| 2 | 5 | PiSSA: Principal Singular Values and Singular Vectors Adaptation of Large Language Models | 2404.02948 | Init A/B from principal SVD components, freeze residual; faster convergence than LoRA across 184M-70B; QPiSSA beats QLoRA 4-bit. |
| 2 | 5 | QA-LoRA: Quantization-Aware Low-Rank Adaptation of Large Language Models | 2309.14717 | Group-wise quant + adaptation balances degrees of freedom; INT4 fine-tune merges back losslessly, beats QLoRA at 2-4 bit. |
| 2 | 9 | QMSum: A New Benchmark for Query-based Multi-domain Meeting Summarization | 2104.05938 | 1808 query-summary pairs over 232 meetings in 3 domains; locate-then-summarize baseline; cross-domain generalization fails. |
| 2 | 6 | R1-RE: Cross-Domain Relation Extraction with RLVR | 2507.04642 | RL with verifiable rewards for cross-domain relation extraction |
| 2 | 6 | REBEL: Relation Extraction By End-to-end Language generation | 10.18653/v1/2021.findings-emnlp.204 | Seq2seq triplet linearization on BART for 200+ relation types; SOTA on RE/RC benchmarks after few-epoch fine-tunes |
| 2 | 6 | REDFM: a Filtered and Multilingual Relation Extraction Dataset | 2306.09802 | NLI-filtered silver RE data with Triplet Critic; mREBEL extracts typed triplets in 7 languages |
| 2 | 4 | REINFORCEMENT LEARNING WITH VERIFIABLE REWARDS IMPLICITLY INCENTIVIZES CORRECT REASONING I | 2506.14245 | answer-only verifiable rewards still extend the reasoning boundary (CoT-Pass@K) rather than merely sharpening sampling |
| 2 | 4 | REMAX: A SIMPLE, EFFECTIVE, AND EFFICIENT REINFORCEMENT LEARNING METHOD FOR ALIGNING LARGE | 2310.10505 | greedy-baseline REINFORCE with no value model; removes 4-plus PPO hyperparameters; about 46 percent less GPU memory than PPO at 7B |
| 2 | 1 | ReAct: Synergizing Reasoning and Acting in Language Models | 2210.03629 | Thought-action-observation prompting scaffold for harness tool loops |
| 2 | 5 | ReLoRA: High-Rank Training Through Low-Rank Updates | 2307.05695 | Periodic merge-and-restart with jagged LR + partial optimizer reset turns sequential low-rank updates into high-rank training to 1.3B; needs |
| 2 | 9 | Reflexion: Language Agents with Verbal Reinforcement Learning | 2303.11366 | Actor/Evaluator/Self-Reflection loop storing verbal feedback in a small episodic buffer; 91% HumanEval. |
| 2 | 2 | RegMix: Data Mixture as Regression for Language Model Pre-training | 2407.01492 | Rank-invariance lets tiny proxies + LightGBM regression predict the best mix (Pile-CC, 1M-token proxies). |
| 2 | 2 | Rephrasing the Web: A Recipe for Compute and Data-Efficient Language Modeling | 2401.16380 | Uses an instruction-tuned model to rephrase web docs (Wikipedia/QA styles) and trains jointly on real + synthetic. |
| 2 | 10 | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | 2005.11401 | RAG-Sequence and RAG-Token jointly fine-tune a DPR retriever with a BART generator treating documents as latents; index is hot-swappable. |
| 2 | 10 | Retrieval-Augmented Generation for Large Language Models: A Survey | 2312.10997 | Naive, Advanced and Modular RAG paradigms with pre-retrieval, post-retrieval and evaluation taxonomies. |
| 2 | 6 | RexUIE: A Recursive Method with Explicit Schema Instructor for Universal Information Extra | 2304.14770 | Recursive token-linking queries extract n-ary schemas (quadruples/quintuples); 3M distant JERE pretrain |
| 2 | 4 | SIMPO: SIMPLE PREFERENCE OPTIMIZATION WITH A REFERENCE-FREE REWARD | 2405.14734 | average-logprob implicit reward removes the reference model from memory; margin objective |
| 2 | 10 | Scalable and Effective Generative Information Retrieval | 2311.09134 | Prefix-oriented ranking optimization plus multi-stage distillation makes GR work on large standard benchmarks (MS MARCO, NQ) for the first t |
| 2 | 1 | Seal-Tools: Self-Instruct Tool Learning Dataset for Agent Tuning and Detailed Benchmark | 2405.08355 | Self-instruct tool/instance generation with nested calls; Tool/Param F1 eval |
| 2 | 2 | SemDeDup: Data-efficient learning at web-scale through semantic deduplication | 2303.09540 | K-means on embeddings + intra-cluster pruning keeps ~50% of data at parity (OPT experiments). |
| 2 | 3 | SimCSE: Simple Contrastive Learning of Sentence Embeddings | 2104.08821 | Dropout-noise unsupervised contrastive plus NLI entailment/contradiction supervised contrastive recipe |
| 2 | 2 | The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale | 2406.17557 | Fully documented dedup/filter pipeline (MinHash, C4-style rules, classifiers) with ablations. |
| 2 | 1 | ToolAlpaca: Generalized Tool Learning for Language Models with 3000 Simulated Cases | 2306.05301 | 3000-case simulated tool-use SFT showing compact-model gains |
| 2 | 1 | Toolformer: Language Models Can Teach Themselves to Use Tools | 2302.04761 | Self-supervised API-call insertion via execution-filtered sampling |
| 2 | 3 | Training Prompt Matters: State-Adaptive Optimization for Robust Fine-Tuning | 2606.01967 | Paraphrased training prompts match in-task but differ sharply in forgetting; SAPO selects prompts by pre-learning loss |
| 2 | 10 | Ultron: An Ultimate Retriever on Corpus with a Model-based Indexer | 2208.09257 | Semantically rich URL-plus-title-plus-title docids with a three-stage (general, search-oriented, supervised) training workflow; beats DSI-st |
| 2 | 6 | Unified Structure Generation for Universal Information Extraction | 10.18653/v1/2022.acl-long.395 | T5 text-to-structure with structural schema instructor and structured extraction language |
| 2 | 2 | Unnatural Instructions: Tuning Language Models with (Almost) No Human Labor | 2212.09689 | Expands 15 seed instructions to ~64K examples by paraphrase; core of the minimal-diversity recipe. |
| 2 | 10 | Unsupervised Dense Information Retrieval with Contrastive Learning | 2112.09118 | MoCo-style contrastive pre-training with cropping-based positives yields an unsupervised dense retriever competitive with BM25 and a strong  |
| 2 | 5 | VeRA: Vector-based Random Matrix Adaptation | 2310.11454 | Frozen shared random A/B across layers, trains only scaling vectors; 10x fewer params than LoRA at same GLUE/E2E quality. |
| 2 | 9 | Voyager: An Open-Ended Embodied Agent with Large Language Models | 2305.16291 | Ever-growing library of model-written code skills indexed by description embedding with iterative self-verification. |
| 2 | 2 | What Makes Good Data for Alignment? A Comprehensive Study of Automatic Data Selection in I | 2312.15685 | Scores complexity/quality/diversity (Evol-Complexity/Evol-Quality + embeddings) and selects small high-performing subsets. |
| 2 | 2 | WizardCoder: Empowering Code Large Language Models with Evol-Instruct | 2306.08568 | Evol-Instruct applied to a narrow task (code) on a StarCoder base. |
| 2 | 3 | X-LoRA: Mixture of Low-Rank Adapter Experts, a Flexible Framework for Large Language Model | 2402.07148 | Token-level deep layer-wise mixing of frozen pretrained adapters with a hidden-state gate |
| 2 | 6 | YAYI-UIE: A Chat-Enhanced Instruction Tuning Framework for Universal Information Extractio | 2312.15548 | Two-step chat-then-IE instruction tuning; largest Chinese IE instruction benchmark; keeps English ability |
| 1 | 6 | Empowering Document-level Relation Extraction with Efficient Evidence Extraction and Infer | 2106.08657 | Joint RE + lightweight evidence extractor with heuristic silver labels and inference-stage fusion |
| 1 | 6 | MR-UIE: Multi-Perspective Reasoning with Reinforcement Learning for Universal Information  | 2509.09082 | RL with multi-perspective reasoning for universal IE |
| 1 | 6 | Multilingual Autoregressive Entity Linking | 2103.12528 | Multilingual GENRE resolving mentions in 100+ languages to a multilingual KB |

## Refutations

- Agreement Among Statistical Significance Tests for Information Retrieval Evaluation at Var (10.1145/1571941.1572050): Verified at UMass CIIR publication list (venue/year/pages) and author-hosted PDF (title text confirmed inside PDF).
- G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment (2303.16634): Abs page and full PDF opened. Repo URL is as printed in paper; stars/push not recorded, left blank rather than invented.
- Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena (2306.05685): Abs page and full PDF opened. Refutes the brief's implicit claim that a frontier model is a neutral scorer of payload quality.
- Length-Controlled AlpacaEval: A Simple Way to Debias Automatic Evaluators (2404.04475): Abs page and full PDF opened; id-title match verified.
- NLP Evaluation in trouble: On the Need to Measure LLM Data Contamination for each Benchmar (2310.18018): Abs page and full PDF opened; id-title match verified. Position paper, no released artefact.
- RL IN NAME ONLY? ANALYZING THE STRUCTURAL ASSUMPTIONS IN RL POST-TRAINING FOR LLMS (2505.13697): verified via arXiv abs page and downloaded PDF; refutes claim that GRPO-style RL adds reasoning beyond filtered SFT

## Abstained (unresolved ledger)

- QLoRA: Efficient Finetuning of Quantized LLMs (2305.14314): In round-1/round-2 inventories; not re-found per brief section 2.
- LQ-LoRA: Low-rank Plus Quantized Matrix Decomposition for Efficient Language Model Finetun (2311.12023): Verified at abs/ICLR pages but omitted from admits as third quant-LoRA recipe after LoftQ/QA-LoRA; no PDF downloaded.
- -XKD: GENERAL EXPERIENTIAL KNOWLEDGE DISTILLATION FOR LARGE LANGUAGE MODELS (2602.12674): verified via arXiv search snippet only; tangential framing, no harness-transferable recipe beyond baselines
- A Survey on Data Contamination for Large Language Models (2502.14425): Primary source never opened; superseded for our purposes by admitted 2406.04244 survey.
- A comparison of the optimality of statistical significance tests for information retrieval (10.1145/2484028.2484163): Primary source (paywalled ACM) never opened; claims taken only from secondary excerpts. Covered for our purposes by admitted Smucker papers.
- ADELIE: Aligning Large Language Models on Information Extraction (n/a (ACL id 2024.emnlp-main.419)): Primary source never opened; belongs partly to lane 6 as well. Flagged, not cited.
- AFLoRA: Adaptive Freezing of Low Rank Adaptation in Parameter Efficient Fine-Tuning of Lar (doi:10.18653/v1/2024.acl-short.16): ACL Anthology excerpt only, no arXiv id for papers/ naming; no PDF.
- Bottleneck Tokens for Unified Multimodal Retrieval (2604.11095): Screened via arXiv search snippet only; multimodal scope; not opened at primary source
- Catastrophic Forgetting in LLMs: A Comparative Analysis Across Language Tasks (2504.01241): Abs page opened; single-author, no PEFT-vs-FT isolation, prompting confound; weak evidence.
- CoMoL: Efficient Mixture of LoRA Experts via Dynamic Core Space Merging (2603.00573): Screened via arXiv search snippet; representative coverage via admitted MoLoRA; not opened at abs page
- DEEPSEEK-MATH-V2: TOWARDS SELF-VERIFIABLE MATHEMATICAL REASONING (2511.22570): verified via arXiv search snippet only; frontier scale, no single-GPU recipe
- DEEPSEEK-PROVER: ADVANCING THEOREM PROVING IN LLMS THROUGH LARGE-SCALE SYNTHETIC DATA (2405.14333): verified via arXiv search snippet only; large-scale synthetic SFT, lane-2 overlap
- DEMYSTIFYING GROUP RELATIVE POLICY OPTIMIZATION: ITS POLICY GRADIENT IS A U-STATISTIC (2603.01162): verified via arXiv search snippet only; pure theory, no actionable recipe
- DP-OPD: DIFFERENTIALLY PRIVATE ON-POLICY DISTILLATION FOR LANGUAGE MODELS (2604.04461): verified via arXiv search snippet only; differential-privacy scope, tangential
- Detecting Pretraining Data from Large Language Models (Min-K% Prob) (2310.16789): Verified at primary source but deferred: contamination detection is evaluation-side (lane 8 territory), not dataset construction.
- Distilling Knowledge from Reader to Retriever for Question Answering (none (OpenReview primary; no arXiv id)): No arXiv PDF to file (OpenReview is the primary); content covered by the Atlas and REPLUG-LSR admits; repo not resolved.
- DynamicRetriever: A Pre-training Model-based IR System with Neither Sparse nor Dense Index (2203.00537 (id from PDF search-result URL only)): Abs page never opened (only a PDF search-result excerpt); venue and details unconfirmed; same-group successor Ultron admitted instead.
- Few-Shot Parameter-Efficient Fine-Tuning is Better and Cheaper than In-Context Learning (( (2205.05638): Verified at abs/NeurIPS/HF-docs pages; few-shot-era, no forgetting measurement; repo not verified; no PDF.
- HAPO: TRAINING LANGUAGE MODELS TO REASON CONCISELY VIA HISTORY-AWARE POLICY OPTIMIZATION (2505.11225): verified via arXiv search snippet only; length-efficiency only, tangential
- Investigating Data Contamination in Modern Benchmarks for Large Language Models (n/a (DOI not recorded)): Primary source never opened; cited here only as screened. Covered by admitted BDC survey and Sainz.
- L-MoE: End-to-End Training of a Lightweight Mixture of Low-Rank Adaptation Experts (2510.17898): Screened via arXiv search snippet; overlaps admitted MoLoRA; not opened at abs page
- LONGWRITER-ZERO: MASTERING ULTRA-LONG TEXT GENERATION VIA REINFORCEMENT LEARNING (2506.18841): verified via arXiv search snippet only; 32B long-form scope, not transferable to 2B harness
- Lamer-SSL: Layer-aware Mixture of LoRA Experts for Continual Multilingual Expansion (2602.12746): Screened via arXiv search snippet; speech setting; replay-plus-MoLE pattern already covered by admitted items
- Language Models are Super Mario (DARE) (2311.03099): In round-2 inventory; not re-screened in this lane
- LoRA Without Forgetting: Freezing and Sparse Masking for Low-Rank Adaptation (none found): ICLR workshop page excerpt only; no arXiv id opened; no PDF.
- Low-Rank Quantization-Aware Training for LLMs (2406.06385): Abs excerpt via search only, full abs page never opened; narrow QAT scope; no PDF.
- MATHFUSION: ENHANCING MATHEMATICAL PROBLEM-SOLVING OF LLM THROUGH INSTRUCTION FUSION (2503.16212): verified via arXiv search snippet only; lane-2 (data) overlap, math-only
- Macaron-V1: Towards Open Continual Learning with Self-Improvement and Mixture-of-LoRA (2608.09819): Screened via arXiv search snippet; two orders of magnitude above our scale; no transferable 1-3B measurement
- Nemotron-4 340B Technical Report (2406.11704): Verified at primary source but screened out: base-model-scale report; document-synthetic detail thinner than Nemotron-CC for this lane; kept as background.
- ON-POLICY DISTILLATION OF LANGUAGE MODELS FOR AUTONOMOUS VEHICLE MOTION PLANNING (2604.07944): verified via arXiv search snippet only; single-domain application, low transfer
- ProtoAda: Prototype-Guided Adaptive Adapter Expansion and Geometric Consolidation (2606.02576): Screened via arXiv search snippet; vision-language setting; routing insight covered by admitted Arrow/MoLoRA
- QuAILoRA: Quantization-Aware Initialization for LoRA (2410.14713): Abs excerpt via search only; workshop; no PDF.
- RANK-DISTILLM: CLOSING THE EFFECTIVENESS GAP BETWEEN CROSS-ENCODERS AND LLMS FOR PASSAGE R (2405.07920): verified via arXiv search snippet only; re-ranking scope, not generative harness
- ReMix: Reinforcement routing for mixtures of LoRAs in LLM finetuning (2603.10160): Screened via arXiv search snippet; router-collapse finding noted but not verified at primary source
- S-GRPO: EARLY EXIT VIA REINFORCEMENT LEARNING IN REASONING MODELS (2505.07686): verified via arXiv search snippet only; conciseness-only, tangential
- SAMoRA: Semantic-Aware Mixture of LoRA Experts for Task-Adaptive Learning (2604.19048): Screened via arXiv search snippet; representative coverage via admitted MoLoRA/Arrow; not opened at abs page
- TIES-Merging: Resolving Interference When Merging Models (2306.01708): In round-2 inventory; not re-screened in this lane
- The BigGen Bench: A Principled Benchmark for Fine-grained Evaluation of Language Models wi (2406.05761): Primary source never opened. Listed so the integrator knows the Prometheus-2-BGB claim is second-hand.
- Towards Data Contamination Detection for Modern Large Language Models: Limitations, Incons (2409.09927): Primary source never opened. Listed so the gap (no agreed detector) is not silently dropped.
- WALK BEFORE YOU RUN! CONCISE LLM REASONING VIA REINFORCEMENT LEARNING (2505.21178): verified via arXiv search snippet only; conciseness-only, tangential
- WHAT IS THE ALIGNMENT OBJECTIVE OF GRPO? (2502.18548): verified via arXiv search snippet only; theory note, no recipe
- Designing metainterfaces with specified friction laws (NOT DoRA) (2402.10960): Opened to disprove; listed so the error is on record, not silently dropped.
- Discrete-Time I and I Adaptive Interconnection and Damping Passivity-Based Control (2405.19944): Opened abs page to check a recalled id; title mismatch proves the guess wrong; recorded as verification trap
- Feasibility Enhancement of Constrained Receding Horizon Control Using Generalized Control  (2102.13304): Opened abs page to check a recalled id; title mismatch proves the guess wrong
- Finetuned Language Models Are Zero-Shot Learners (FLAN) (2109.01652): Verified at primary source but out of scope: human-written data, no synthetic-generation recipe for the lane.
- Generative Representational Instruction Tuning (2402.09906): Seed from brief/round-2; used only as forward-chaining source via OpenAlex, not re-found
- Hydra: Unifying Document Retrieval and Generation in a Single Vision-Language Model (2603.28554): Seed from brief/round-2; chaining source only, not re-found
- LLM2Vec paper (title not verified in this lane) (2404.05961): Seed from brief/round-2; chaining source only, not re-found
- OneGen paper (title not verified in this lane) (2409.05152): Seed from brief/round-2; chaining source only, not re-found
- Proportional Representation in Metric Spaces and Low-Distortion Committee Selection (2312.10369): Opened abs page to check a recalled id; title mismatch proves the guess wrong
- Record of miss: 2307.06215 is an unrelated paper (rotating black holes) (2307.06215 (wrong)): Resolved miss, kept in inventory so nothing screened is dropped silently.
- Super-NaturalInstructions: Generalization via Declarative Instructions on 1600+ NLP Tasks (2204.07705): Verified at primary source but out of scope: human-written data, no synthetic-generation recipe for the lane.
- Topotactic Transition (materials science; NOT a LoRA paper) (2305.16605): Opened to disprove; listed so the error is on record, not silently dropped.
- When Does Pretraining Help? Assessing Self-Supervised Learning for Law and the CaseHOLD Da (2104.08671): Opened abs page to rule it out: it is the correct paper for 2104.08671, not BEIR (2104.08663). Screened, out of scope.
- unverified candidate (monolithic preference optimization) (unverified (guessed 2404.10019 disproven via abs fetch: unrelated astrophysics paper)): could not verify arXiv id; follow-up search timed out; do not cite
- unverified candidate (open post-training recipe) (unverified (guessed 2411.15134 disproven via abs fetch: toric invariance)): could not verify arXiv id; do not cite
- unverified candidate (reward-ranked fine-tuning) (unverified (guessed 2309.07487 disproven via abs fetch: biomechanics)): could not verify arXiv id; do not cite
- unverified candidate (verifier-augmented STaR) (unverified (guessed 2310.05689 disproven via abs fetch: opinion dynamics; text searches empty)): could not verify arXiv id after three attempts; do not cite
