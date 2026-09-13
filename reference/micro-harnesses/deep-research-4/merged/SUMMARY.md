# Merge summary

Rows read: 461 across 10 lanes ({'1': 41, '2': 44, '3': 28, '4': 38, '5': 36, '6': 39, '7': 23, '8': 30, '9': 144, '10': 38}). Unique items after dedup: 348. Dispositions: {'admit': 173, 'refute': 1, 'abstain': 174}. Admitted PDFs staged: 162. Malformed rows skipped: 0.

## Admitted, by relevance

| relevance | lanes | title | id / repo | one line |
|---|---|---|---|---|
| 3 | 2,8 | A-MEM: Agentic Memory for LLM Agents | 2502.12110 | Zettelkasten notes with attributes/keywords/tags, agent-created links, and evolution of old notes on new arrivals; routing is link-and-merge |
| 3 | 1 | APIGen: Automated Pipeline for Generating Verifiable and Diverse Function-Calling Datasets | 2406.18518 | Three-stage verifier (format checker plus real execution plus semantic LLM judge) over 3673 executable APIs; closest published analog of Pro |
| 3 | 5 | Accelerating Large Language Model Decoding with Speculative Sampling | 2302.01318 | Distribution-preserving rejection sampling for draft verification; 2-2.5x on 70B. |
| 3 | 9 | Accurate and Efficient Long-Term Memory for LLM Agents | 2607.16211 | Entity-typed graph storage with conflict-aware writes without expensive LLM classification |
| 3 | 3,5 | Active Retrieval Augmented Generation | 2305.06983 | Confidence-thresholded forward-looking active retrieval |
| 3 | 3 | Adaptive-RAG: Learning to Adapt Retrieval-Augmented Large Language Models through Question | 2403.14403 | Small-LM complexity classifier routing no/single/multi-step retrieval |
| 3 | 8 | Agent Workflow Memory | 2409.07429 | Induces reusable routines (workflows) from trajectories offline or online and injects them as agent memory; +24.6%/+51.1% relative on Mind2W |
| 3 | 2,9 | AgentMemBench: A Systematic Benchmark for Evaluating Long-Term Memory Management Strategie | 2608.00009 | Five strategies (ICW/EKV/GEM/CBS/WAM) compared under identical conditions on LoCoMo and document-grounding sets; first apples-to-apples mana |
| 3 | 8 | AgentPoison: Red-teaming LLM Agents via Poisoning Memory or Knowledge Bases | 2407.12784 | Optimized-trigger backdoor on agent long-term memory/RAG; >=80% attack success at <0.1% poison rate with <=1% benign impact; triggers transf |
| 3 | 1 | An LLM Compiler for Parallel Function Calling | 2312.04511 | Splits orchestration into planner plus task-fetching unit plus executor; parallel dispatch gives up to 3.7x latency speedup over ReAct. |
| 3 | 10 | BRIGHT: A Realistic and Challenging Benchmark for Reasoning-Intensive Retrieval | 2407.12883 | 1384 real-world queries where relevance needs multi-step reasoning; SOTA dense retrievers collapse and explicit reasoning adds up to 12.2 po |
| 3 | 4 | Between Underthinking and Overthinking: An Empirical Study of Reasoning Length and correct | arXiv:2505.00127 | 1.5B reasoning models overthink easy items and underthink hard ones; prefer-shorter tuning keeps accuracy shorter |
| 3 | 6 | Cache Saver: A Modular Framework for Efficient, Affordable, and Reproducible LLM Inference | doi:10.18653/v1/2025.findings-emnlp.1402 | Namespace-aware list-valued response cache preserving i.i.d. sampling; ~25% cost and ~35% CO2 cut (vendor-reported). |
| 3 | 6 | CacheBlend: Fast Large Language Model Serving for RAG with Cached Knowledge Fusion | 2405.16444 | Reused non-prefix chunk KV needs selective recompute for cross-attention; RAG prefill speedup with small quality loss. |
| 3 | 9 | Can LLM Already Serve as A Database Interface? A BIg Bench for Large-Scale Database Ground | 2305.03111 | 12751 NL-SQL pairs over 95 DBs (33.4GB); dirty values, external knowledge, SQL efficiency |
| 3 | 6 | ChunkAttention: Efficient Self-Attention with Prefix-Aware KV Cache and Two-Phase Partitio | doi:10.18653/v1/2024.acl-long.623 | Chunked KV in a prefix tree plus two-phase partitioned attention kernel; 3.2-4.8x kernel speedup for 1-4k shared prompts. |
| 3 | 7,10 | CodeRAG-Bench: Can Retrieval Augment Code Generation? | 2406.14497 | Holistic retrieval-augmented code generation benchmark: 9k tasks, 5 doc sources, 10 retrievers x 10 LMs |
| 3 | 7 | CodexGraph: Bridging Large Language Models and Code Repositories via Code Graph Databases | 2408.03910 | Static-analysis code graph (MODULE/CLASS/FUNCTION + CONTAINS/INHERITS/USES) queried by an LLM via write-then-translate to Cypher |
| 3 | 7 | CrossCodeEval: A Diverse and Multilingual Benchmark for Cross-File Code Completion | 2310.11248 | Cross-file completion benchmark: ~10k examples from ~1k repos in 4 languages, mined by static analysis |
| 3 | 3,5 | DRAGIN: Dynamic Retrieval Augmented Generation based on the Information Needs of Large Lan | 2403.10081 | Token-need-weighted real-time retrieval trigger (QFS) |
| 3 | 3 | DeepRAG: Thinking to Retrieve Step by Step for Large Language Models | 2502.01142 | MDP retrieve-or-rely-on-parametric per-subquery decisions |
| 3 | 4,10 | DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning | arXiv:2501.12948 | Pure-RL reasoning with emergent reflection; distilled 1.5B open reasoning weights exist |
| 3 | 10 | DeepSeekMath: Pushing the Limits of Mathematical Reasoning in Open Language Models | 2402.03300 | Introduces GRPO and RLVR-style verifiable-reward RL; 7B reaches 51.7% MATH without tools. |
| 3 | 4 | Do NOT Think That Much for 2+3=? On the Overthinking of o1-Like LLMs | arXiv:2412.21187 | o1-like models spend 1953% more tokens on 2+3; self-training pruning cuts ~49% tokens at equal accuracy |
| 3 | 4 | Does Thinking More always Help? Mirage of Test-Time Scaling in Reasoning Models | arXiv:2506.04210 | Wait-appending gains are variance mirage; parallel thinking beats sequential up to +20% at equal budget |
| 3 | 4 | Don't Overthink it. Preferring Shorter Thinking Chains for Improved LLM Reasoning | arXiv:2505.17813 | Shortest-of-k beats longest by up to 34.5%; short-3@k beats majority vote faster; train on short chains |
| 3 | 6,10 | Efficient Memory Management for Large Language Model Serving with PagedAttention | 2309.06180 | Block-paged KV cache with near-zero fragmentation and cross-request sharing; 2-4x vLLM throughput. |
| 3 | 2,3,10 | Evaluating Very Long-Term Conversational Memory of LLM Agents | 2402.17753 | Machine-human pipeline generating very-long multi-session dialogues grounded on personas and temporal event graphs; QA over them. |
| 3 | 8 | ExpeL: LLM Agents Are Experiential Learners | 2308.10144 | Extracts natural-language insights from past trajectories (successes and fails) and retrieves them at test time; learning without parameter  |
| 3 | 5 | Fast Inference from Transformers via Speculative Decoding | 2211.17192 | Draft-then-verify exact decoding; 2-3x with identical outputs. |
| 3 | 2,3,9 | From RAG to Memory: Non-Parametric Continual Learning for LLMs | 2502.14802 | HippoRAG-team continual-learning framing: memory as non-parametric accumulation with PPR-based organization across sessions. |
| 3 | 1 | Gorilla/BFCL codebase (repo artefact) | none (same papers) | Executable AST evaluator plus leaderboard harness plus retriever code MelodyScribe can reuse for op scoring. |
| 3 | 1,10 | Gorilla: Large Language Model Connected with Massive APIs | 2305.15334 | Retriever plus fine-tuned LLaMA for API selection; retrieval grounds arguments and absorbs doc changes without retraining. |
| 3 | 7 | GraphCodeAgent: Dual Graph-Guided LLM Agent for Retrieval-Augmented Repo-Level Code Genera | 2504.10046 | Dual Requirement Graph + Structural-Semantic Code Graph guiding an LLM agent's multi-hop supportive-code retrieval |
| 3 | 7 | GraphCoder: Enhancing Repository-Level Code Completion via Code Context Graph-based Retrie | 2406.07003 | Statement-level code-context graph (control-flow + data/control dependence) with coarse-to-fine structural retrieval |
| 3 | 2,9 | Graphiti (real-time temporal knowledge graphs for agents) | https://github.com/getzep/graphiti | OSS implementation of the Zep temporal-graph ingest: episode ingestion, entity/edge extraction, contradiction-aware invalidation. |
| 3 | 1 | Hammer: Robust Function-Calling for On-Device Language Models via Function Masking | 2410.04587 | Function-name masking during training plus irrelevance-augmented negatives teach abstention; diagnoses cross-benchmark instability as name-m |
| 3 | 2,5,8 | Hindsight is 20/20: Building Agent Memory that Retains, Recalls, and Reflects | 2512.12818 | Retain/recall/reflect split that keeps evidence separate from inference and organizes memory beyond snippet extraction; commercial system wi |
| 3 | 2,3,9 | HippoRAG: Neurobiologically Inspired Long-Term Memory for LLMs | 2405.14831 | OpenIE entity/relation extraction into a KG plus Personalized PageRank; single-step retrieval matches iterative IRCoT at 10-30x lower cost. |
| 3 | 6 | Hydragen: High-Throughput LLM Inference with Shared Prefixes | 2402.05099 | Batches sequences sharing long prefixes with one shared-prefix attention pass; paper also links jordan-benjamin/hydragen. |
| 3 | 3 | Interleaving Retrieval with Chain-of-Thought Reasoning for Knowledge-Intensive Multi-Step  | 2212.10509 | Interleaved CoT-retrieval loop for multi-step QA |
| 3 | 9 | Iteration Without Elaboration: A Simple ReAct Architecture Suffices for Text-to-SQL Genera | 2608.22651 | 15-op typed DSL with execution feedback; 84.5pct BIRD mini-dev and 73.9pct EHR-SQL at up to 8x speed |
| 3 | 4 | L1: Controlling How Long A Reasoning Model Thinks With Reinforcement Learning | arXiv:2503.04697 | RL length control (LCPO); 1.5B Short-Reasoning-Model beats GPT-4o at equal length |
| 3 | 1 | LLMCompiler reference implementation (repo artefact) | none (same as paper) | Executable planner plus DAG plus parallel executor the harness can port for op batching. |
| 3 | 8 | Large Language Models as Tool Makers | 2305.17126 | Splits tool maker from tool user with a dispatcher; candidate tools admitted only after passing unit tests (execution gate); tools cached fo |
| 3 | 4 | Latent Chain-of-Thought? Decoding the Depth-Recurrent Transformer | arXiv:2507.02199 | Probing Huginn-3.5B finds no structured latent CoT; recurrence 4->32 steps barely moves GSM8K vs explicit CoT |
| 3 | 5 | Learning to Decode Collaboratively with Multiple Language Models | 2403.03870 | Unsupervised token-level deferral between generalist base and expert assistants. |
| 3 | 4 | Let Me Speak Freely? A Study on the Impact of Format Restrictions on Performance of Large  | arXiv:2408.02442 | Format constraints degrade reasoning; JSON-mode answer-before-reason zeroes Last-Letter; 38pp gap on LLaMA-3-8B |
| 3 | 2,3 | LightRAG: Simple and Fast Retrieval-Augmented Generation | 2410.05779 | Dual-level (low/high) keyword extraction into entities/relations with hybrid graph+vector retrieval; entity names double as index keys. |
| 3 | 2,3,10 | LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory | 2410.10813 | 500 curated questions over scalable histories testing extraction, multi-session/temporal reasoning, knowledge updates, abstention. |
| 3 | 9 | MIRIX multi-agent memory system (implementation) | https://github.com/Mirix-AI/MIRIX | Six-store memory system implementation including the Knowledge Vault |
| 3 | 2,3,9 | MIRIX: Multi-Agent Memory System for LLM-Based Agents | 2507.07957 | Six typed stores (Core/Episodic/Semantic/Procedural/Resource/Knowledge Vault), each with a dedicated Memory Manager plus a Meta Memory Manag |
| 3 | 2,8 | Mem-α: Learning Memory Construction via Reinforcement Learning | 2509.25911 | RL framework training the agent to decide what to store, how to structure it, and when to update; construction policy is learned, not prompt |
| 3 | 2,9 | Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory | 2504.19413 | Two-phase add (extract facts, then ADD/UPDATE/DELETE against similar memories) plus an optional graph store; the model decides the op and th |
| 3 | 10 | MemBench: Towards More Comprehensive Evaluation on the Memory of LLM-based Agents | 2506.21605 | Factual plus reflective memory over participation and observation scenarios, scored on effectiveness, efficiency and capacity. |
| 3 | 2 | MemOS: A Memory OS for AI System | 2507.03724 | MemCube uniform memory unit plus MemScheduler that schedules across plaintext/activation/parameter tiers; type-and-tier decision is schedule |
| 3 | 8 | Memory Injection Attacks on LLM Agents via Query-Only Interaction | 2503.03704 | Query-only memory injection via indication prompts plus progressive shortening; 98.2% injection success, 76.8% attack success; evades perple |
| 3 | 2,10 | Memory-R1: Enhancing LLM Agents to Manage and Utilize Memories via RL | 2508.19828 | GRPO-trained manage-and-utilize loop over an external memory bank; static heuristic store/update/retrieve replaced by learned policy. |
| 3 | 1,3,4,5,6,7 | MiniCPM cookbook / Agent Skills / MCP adaptations (repo artefact) | n/a | Vendor cookbook plus Agent Skills plus MCP tool-use adaptations: the deployment harness the brief names, verified live and maintained. |
| 3 | 1,4 | MiniCPM4: Ultra-Efficient LLMs on End Devices | 2506.07900 | InfLLM-v2 trainable sparse attention plus CPM.cu inference stack plus hybrid MiniCPM4.1 think/no-think modes; reports MCP tool-use adaptatio |
| 3 | 6 | Mooncake: A KVCache-centric Disaggregated Architecture for LLM Serving | 2407.00079 | Disaggregated prefill/decode with paged KV pooled in CPU DRAM/SSD and RDMA transfer; overload-oriented scheduling. |
| 3 | 1 | Octopus v2: On-device language model for super agent | 2404.01744 | Functional tokens replace RAG retrieval: one token selects the function and restructures args, cutting context 95 percent. |
| 3 | 3 | OneGen: Efficient One-Pass Unified Generation and Retrieval for LLMs | 2409.05152 | Autoregressive [RQ]/[RD] retrieval tokens in one forward pass |
| 3 | 6 | Orca: A Distributed Serving System for Transformer-Based Generative Models | https://www.usenix.org/conference/osdi22/presentation/yu | Iteration-level scheduling plus selective batching; 36.9x throughput gain over FasterTransformer on GPT-3 175B (vendor-reported). |
| 3 | 4 | Qwen3 Technical Report | arXiv:2505.09388 | Hybrid thinking/non-thinking switch with thinking-budget control in one model family |
| 3 | 10 | R1-Searcher: Incentivizing the Search Capability in LLMs via Reinforcement Learning | 2503.05592 | Two-stage outcome RL (retrieval/format reward first, answer reward second) learns search invocation even from a base model with no cold star |
| 3 | 1,3,10 | ReAct: Synergizing Reasoning and Acting in Language Models | 2210.03629 | Canonical harness loop: interleaved thought plus action plus observation with a deterministic executor owning the environment. |
| 3 | 4,5 | ReTool: Reinforcement Learning for Strategic Tool Use in LLMs | arXiv:2504.11536 | RL interleaved think/code-execution from cold start; 32B 67% AIME in 400 steps; emergent self-correction |
| 3 | 1 | ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models | 2305.18323 | Planner emits the full tool-use plan without observations, then workers execute; 5x token saving and reasoning offloaded from 175B to 7B. |
| 3 | 4 | Reasoning Models Can Be Effective Without Thinking | arXiv:2504.09858 | Empty prefilled thinking box matches/beats thinking at equal tokens (51.3 vs 28.9 AMC23 @700); 7-9x latency win |
| 3 | 8,10 | Reflexion: Language Agents with Verbal Reinforcement Learning | 2303.11366 | Agent keeps episodic memory of past trajectories plus self-reflection text and retries; verbal (language) reinforcement instead of weight up |
| 3 | 7 | RepoBench: Benchmarking Repository-Level Code Auto-Completion Systems | 2306.03091 | Repository-level completion benchmark split into Retrieval / Completion / Pipeline tasks, Python + Java |
| 3 | 7 | RepoCoder: Repository-Level Code Completion Through Iterative Retrieval and Generation | 2303.12570 | Iterative retrieval-generation loop for repo-level completion plus the RepoEval benchmark (line/API/function) |
| 3 | 7 | RepoGraph: Enhancing AI Software Engineering with Repository-level Code Graph | 2410.14684 | Parser-built line-level def-ref graph with ego-graph retrieval plugged into SWE-agent/Agentless |
| 3 | 7 | Repoformer: Selective Retrieval for Repository-Level Code Completion | 2403.10059 | Selective-RAG code LM that self-assesses whether retrieval helps; SOTA on RepoEval/CrossCodeEval with up to 70% speedup |
| 3 | 6 | SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills | 2308.16369 | Chunked prefills piggybacked on decodes; no own repo link found in PDF bytes. |
| 3 | 1,6,10 | SGLang: Efficient Execution of Structured Language Model Programs | 2312.07104 | Frontend primitives for generation plus parallelism plus control flow; RadixAttention KV reuse and compressed-FSM structured decoding, up to |
| 3 | 6 | SQLite Write-Ahead Logging (documentation) | https://www.sqlite.org/wal.html | WAL: readers never block writer, single writer, autocheckpoint at 1000 pages, checkpoint starvation, SQLITE_BUSY edge cases, 2026 WAL-reset  |
| 3 | 6 | Same Request, Different Answer: Quantization Amplifies Cache-Induced Divergence in LLM Ser | 2609.04748 | Prefix caching changes agentic tool-use trajectories on 36.2% of episodes at 16-bit and 75.0% at quantized weights (vendor-reported); reuse  |
| 3 | 4 | Scaling up Test-Time Compute with Latent Reasoning: A Recurrent Depth Approach | arXiv:2502.05171 | Depth-recurrent block looped r times per forward pass; 3.5B rivals larger models with test-time recurrence |
| 3 | 3,4,5,10 | Search-R1: Training LLMs to Reason and Leverage Search Engines with Reinforcement Learning | 2503.09516 | RL-trained <information> retrieval-token search loop |
| 3 | 3,5 | Search-o1: Agentic Search-Enhanced Large Reasoning Models | 2501.05366 | Agentic search loop wrapped around long reasoning chains |
| 3 | 3,5 | Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | 2310.11511 | Reflection-token gated adaptive retrieval and self-critique |
| 3 | 8 | SkillWeaver: Web Agents can Self-Improve by Discovering and Honing Skills | 2504.07079 | Three-stage explore-practice-distill pipeline synthesizing reusable Python APIs; test/debug gate before library admission; +31.8%/+39.8% rel |
| 3 | 5 | Sleep-time Compute: Beyond Inference Scaling at Test-time | 2504.13171 | Offline precompute of predictable queries cuts test-time compute ~5x. |
| 3 | 9 | SodaMem: Evidence-Grounded Temporal Graph Memory for LLM Agents | 2608.08055 | Typed FactEvents with provenance spans, mention/occurrence/validity times, SUPERSEDES/CONTRADICTS/UPDATES edges; 92.8pct LongMemEval-S |
| 3 | 4 | Soft Chain-of-Thought for Efficient Reasoning with LLMs | arXiv:2502.12134 | 1B-class assistant emits soft thought tokens projected into frozen LLM; no backbone fine-tune |
| 3 | 5 | Speculative RAG: Enhancing Retrieval Augmented Generation through Drafting | 2407.08223 | Small specialist drafts in parallel; large generalist verifies and selects. |
| 3 | 9 | State Compression in Two-Agent LLM Relays: A Closed-World Study of Constraint Preservation | 2607.18265 | Schema-constrained JSON hand-off preserves numeric/categorical constraints better than narrative summary |
| 3 | 9 | TRACE: State-Aware Query Processing over Temporal Evidence Graphs for Conversational Data | 2607.00339 | Hierarchical event/session/topic graph with validity annotations and typed update/contradiction relations |
| 3 | 9 | TableRAG: A Retrieval Augmented Generation Framework for Heterogeneous Document Reasoning | 2506.10380 | Iterative loop of query decomposition, text retrieval, SQL programming and execution over mixed docs |
| 3 | 9 | TableRAG: Million-Token Table Understanding with Language Models | 2410.04739 | Query expansion with schema and cell retrieval; new million-token Arcade and BIRD-SQL benchmarks |
| 3 | 6,10 | Taming Throughput-Latency Tradeoff in LLM Inference with Sarathi-Serve | 2403.02310 | Stall-free chunked-prefill scheduler; 2.6x capacity on Mistral-7B/A100 and up to 5.6x with pipeline parallelism (vendor-reported). |
| 3 | 1,10 | The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic Evaluation of L | https://proceedings.mlr.press/v267/patil25a.html | AST-based executable grading of serial plus parallel plus multi-turn/stateful calls; de-facto standard MelodyScribe op-emission should be sc |
| 3 | 4 | ThinkBrake: Efficient Reasoning via Log-Probability Margin Guided Decoding | arXiv:2510.00546 | Stop thinking when </think> log-margin narrows; oracle +8%/-72% tokens; BFCL-v2 holds accuracy at -32% tokens |
| 3 | 4 | Thinking Before Constraining: A Unified Decoding Framework for Large Language Models | arXiv:2601.07525 | Free-think first, constrain after trigger token: +27% accuracy, 100% validity, +5-20 tokens; constrain-all worse |
| 3 | 1 | TinyAgent: Function Calling at the Edge | 2409.00608 | End-to-end recipe for task-specific 1.1B/7B edge function-callers: LLMCompiler plans plus ToolRAG retrieval of tools and examples plus quant |
| 3 | 4,5 | ToRL: Scaling Tool-Integrated RL | arXiv:2503.23383 | Tool-integrated RL from base models; 1.5B avg 48.5%; default max 1 tool call; RL-from-scratch beats SFT-first |
| 3 | 10 | ToolSandbox: A Stateful, Conversational, Interactive Evaluation Benchmark for LLM Tool Use | 2408.04682 | 1032 stateful multi-turn tool-use cases with an LLM user simulator and milestone/minefield trajectory scoring. |
| 3 | 2,5 | Total Recall at What Cost? Benchmarking the Serving Cost of Agentic Memory Systems | 2608.11879 | Mem0 vs Hindsight vs Mastra observational memory vs rolling-window vs full-transcript on 665 LoCoMo questions to 400 turns: serving cost is  |
| 3 | 4 | Training Large Language Models to Reason in a Continuous Latent Space | arXiv:2412.06769 | Feed last hidden state back as next input embedding; latent BFS beats CoT on planning-heavy logic |
| 3 | 8 | Voyager: An Open-Ended Embodied Agent with Large Language Models | 2305.16291 | Lifelong Minecraft agent holding an ever-growing library of code skills admitted only after self-verification in the environment plus curric |
| 3 | 8 | WebXSkill: Skill Learning for Autonomous Web Agents | 2604.13318 | Executable+guiding skills organized in an explicit skill graph (page nodes, ~4.2 skills/node); 3.8 ops/skill vs SkillWeaver 1.6; usage rate  |
| 3 | 2 | When Does Memory Help? A Cost-Aware Evaluation of Long-Term Memory in Tool-Using Agents | 2609.05441 | MERIT measures marginal utility of memory for task-executing agents with explicit cost accounting, leak-checked episodic tool-use tasks plus |
| 3 | 4 | When More is Less: Understanding Chain-of-Thought Length in LLMs | arXiv:2502.07266 | Accuracy is inverted-U in CoT length; optimal length rises with difficulty, falls with capability; RL simplicity bias |
| 3 | 6 | XGrammar: Flexible and Efficient Structured Generation Engine for Large Language Models | 2411.15100 | Byte-level pushdown automaton with token-mask cache and co-designed persistent-stack execution; near-zero grammar overhead claim (vendor-rep |
| 3 | 2,3,9 | Zep: A Temporal Knowledge Graph Architecture for Agent Memory | 2501.13956 | Ingest extracts entities/edges/facts from messages into a bi-temporal episode graph (invalid_at invalidation); beats MemGPT on the DMR retri |
| 3 | 9 | prem-1B-SQL text-to-SQL model (weights) | https://huggingface.co/prem-research/prem-1B-SQL | 1B text-to-SQL model; 1B scale can emit SQL with fine-tuning |
| 3 | 4 | s1: Simple test-time scaling | arXiv:2501.19393 | Budget forcing (kill thinking or append Wait) on 1K-curated traces; +27% over o1-preview |
| 3 | 10 | tau-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains | 2406.12045 | Retail/airline agent benchmark with LM-simulated users, policy documents, DB-state matching eval and a pass-k consistency metric. |
| 3 | 6 | vLLM Automatic Prefix Caching (documentation) | https://docs.vllm.ai/en/latest/features/automatic_prefix_caching/ | enable_prefix_caching reuses block-granular KV for shared prefixes; helps prefill only, never decode; no gain without shared prefix. |
| 3 | 1 | xLAM: A Family of Large Action Models to Empower AI Agent Systems | 2409.03215 | Unified data pipeline across action datasets; 1B model beats GPT-3.5-Turbo and 7B tops BFCL over GPT-4 (vendor-reported). |
| 2 | 8 | AFlow: Automating Agentic Workflow Generation | 2410.10762 | Workflow optimization as MCTS search over code-represented node/edge graphs with execution feedback; +5.7% over manual, +19.5% over automate |
| 2 | 5 | An Emulator for Fine-Tuning Large Language Models using Small Language Models | 2310.12962 | Test-time logit arithmetic mixing pre-train and fine-tune scales. |
| 2 | 1 | Apple Intelligence Foundation Language Models | 2407.21075 | 3B on-device model distilled plus pruned plus 3.7-bit palettized; per-task rank-16 LoRA adapters swapped on the fly; on-device plus server s |
| 2 | 6 | Characterizing Contention-Induced Reliability Collapse in KV-Cache Timing Side Channels fo | 2609.06853 | Measures prefix-cache timing-signal reliability under contention on live vLLM (DeepSeek-R1-Distill-Llama-8B); effect size collapses with wor |
| 2 | 5 | Contrastive Decoding: Open-ended Text Generation as Optimization | 2210.15097 | Expert-minus-amateur logit arithmetic under a plausibility constraint. |
| 2 | 6 | Deadline-Aware Adaptive Prefill Chunking for Efficient Large Language Model Serving | 2609.07883 | Online scheduler picking the largest prefill chunk that finishes before the earliest decode deadline; no per-workload tuning. |
| 2 | 8 | Deep Knowledge Tracing | 1506.05908 | RNN that predicts student performance from interaction sequences; models latent knowledge state without an explicit skill graph. |
| 2 | 6 | DistServe: Disaggregating Prefill and Decoding for Goodput-optimized Large Language Model  | 2401.09670 | Goodput (SLO-meeting throughput) optimizer placing prefill/decode across GPUs; placement + parallelism search. |
| 2 | 3 | Enhancing Retrieval-Augmented Large Language Models with Iterative Retrieval-Generation Sy | 2305.15294 | Prior-generation-as-context iterated retrieve-generate loop |
| 2 | 6 | Fast Distributed Inference Serving for Large Language Models | 2305.05920 | Skip-join multi-level feedback queue with proactive KV-cache upload/download overlap; no own repo link in PDF. |
| 2 | 2 | From Local to Global: A Graph RAG Approach to Query-Focused Summarization | 2404.16130 | Leiden community detection over an LLM-extracted graph with community summaries (plus gleanings) for global questions. |
| 2 | 8 | Generative Agents: Interactive Simulacra of Human Behavior | 2304.03442 | Memory stream of observations with importance scoring plus periodic reflection; retrieval by recency+importance+relevance; reflection admitt |
| 2 | 3 | Generative Representational Instruction Tuning | 2402.09906 | One model for embedding and generation via instruction switch |
| 2 | 5 | Hindsight Memory-PRM: Supervising Memory Management with Auditable Hindsight Credit | 2608.29605 | Intervention-calibrated credit for memory ops from retrieval/citation audit trails. |
| 2 | 8 | InjecMEM: Memory Injection Attack on LLM Agent Memory Systems | 2608.23471 | Single-interaction memory injection with retriever-agnostic anchor plus optimized adversarial command; robust to memory drift and placement; |
| 2 | 8 | Knowledge Tracing: A Survey | 2201.06953 | Systematic review incl. graph-based KT: KC nodes with dependency edges, statistics-built vs end-to-end-learned graphs, forgetting-aware and  |
| 2 | 1 | LFM2 Technical Report | 2511.23404 | Hardware-in-loop hybrid conv-attention backbone; tool-call special tokens plus LFM2-Nano task specialists (function calling, extraction, RAG |
| 2 | 9 | LINK-KG: LLM-Driven Coreference-Resolved Knowledge Graphs for Human Smuggling Networks | 2510.26486 | Three-stage LLM coreference pipeline with type-specific prompt cache for alias tracking in KG build |
| 2 | 2 | Learn to Memorize: Optimizing LLM-based Agents with Adaptive Memory Framework | 2508.16629 | Data-driven adaptive memory modeling the memory-cycle effect in interactive settings instead of expert-predefined mechanisms. |
| 2 | 2 | Letta (platform for stateful agents) | https://github.com/letta-ai/letta | Maintained MemGPT lineage: archival/recall agents, sleep-time consolidation, conversation-grounded memory blocks. |
| 2 | 4 | LightThinker: Thinking Step-by-Step Compression | arXiv:2502.15589 | Compress each thought into gist tokens and discard the chain; cuts memory/time at equal accuracy |
| 2 | 5 | Llama Guard: LLM-based Input-Output Safeguard for Human-AI Conversations | 2312.06674 | 7B instruction-tuned input-output safety classifier sidecar. |
| 2 | 6 | Llumnix: Dynamic Scheduling for Large Language Model Serving | 2406.03243 | Live migration of requests across instances to balance load; preemption-safe rescheduling primitive. |
| 2 | 8 | LongMemEval-V2: Evaluating Long-Term Agent Memory Toward Experienced Colleagues | 2605.12493 | 451 questions over up to 500 trajectories testing static recall, dynamic tracking, workflow knowledge, environment gotchas, premise awarenes |
| 2 | 6 | MeanCache: User-Centric Semantic Caching for LLM Web Services | 2403.02694 | Client-side federated semantic cache with per-user precision control; reports hit-rate/precision tradeoffs (numbers inside PDF, unextracted) |
| 2 | 3 | Measuring and Narrowing the Compositionality Gap in Language Models | 2210.03350 | Follow-up-question decomposition (Self-Ask) vs single-hop recall |
| 2 | 9 | Mem0 memory layer (implementation) | https://github.com/mem0ai/mem0 | Production memory-layer implementation with extraction lifecycle |
| 2 | 2,3,5,8 | MemGPT: Towards LLMs as Operating Systems | 2310.08560 | Virtual context management: main context plus recall/archival stores paged by model-issued function calls; the model itself is the router vi |
| 2 | 2 | Memori: A Persistent Memory Layer for Efficient, Context-Aware LLM Agents | 2603.19935 | Advanced Augmentation pipeline turning dialogue into compact semantic triples plus summaries; LLM-agnostic persistent layer cutting token co |
| 2 | 2 | MemoryBank: Enhancing Large Language Models with Long-Term Memory | 2305.10250 | Memory with Ebbinghaus forgetting curve and memory updating; long-term personality-carrying store with retrieval over decayed strengths. |
| 2 | 4 | Mind Your Step (by Step): Chain-of-Thought can Reduce Performance on Tasks where Thinking  | arXiv:2410.21333 | CoT drops accuracy up to 36.3pp where verbalization hurts humans (implicit learning, unverbalizable stimuli) |
| 2 | 1 | MiniCPM: Unveiling the Potential of Small Language Models with Scalable Training Strategie | 2404.06395 | WSD scheduler plus model wind-tunnel scaling law; 2.4B matches 7B-13B class and is the base of the rig's current 2B model. |
| 2 | 1 | Octopus v3: Technical Report for On-device Sub-billion Multimodal AI Agent | 2404.11459 | Functional-token agent under 1B parameters handling text plus vision plus audio on edge devices down to Raspberry Pi. |
| 2 | 1 | Octopus v4: Graph of language models | 2404.19296 | Master-node router: a 3B model maps queries to specialist worker models via functional tokens; only two small models activate per query. |
| 2 | 9 | OmniSQL: Synthesizing High-quality Text-to-SQL Data at Scale | 2503.02240 | Scalable synthesis framework producing SynSQL-2.5M for text-to-SQL fine-tuning |
| 2 | 2 | Optimizing the Interface Between Knowledge Graphs and LLMs for Complex Reasoning | 2505.24478 | Modular ECL (extract/cognify/load) pipelines over chunks with tuned chunking/graph-construction hyperparams; routing is pipeline configurati |
| 2 | 9 | PaVeRL-SQL: Text-to-SQL via Partial-Match Rewards and Verbal Reinforcement Learning | 2509.07159 | Verbal plus CoT RL for text-to-SQL with a small OmniSQL-7B backbone on industry-scale DBs |
| 2 | 8 | PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of Large Langu | 2402.07867 | Attacker injects crafted texts into the retrieval corpus so they are retrieved for target questions and steer generation; studied under blac |
| 2 | 6 | Prompt Cache: Modular Attention Reuse for Low-Latency Inference | 2311.04934 | Prompt modules (PML) with precomputed attention states reused position-independently; CPU/GPU tiering. |
| 2 | 6 | Punica: Multi-Tenant LoRA Serving | 2310.18547 | One base model serves many LoRA adapters in one batch via segmented gather-GEMM; nearest analog of one-process-two-jobs colocation. |
| 2 | 2 | RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval | 2401.18059 | Recursive embed-cluster (GMM)-summarize tree giving multi-abstraction retrieval; ingest is purely statistical, no per-fact routing model. |
| 2 | 2 | RuleMem: Active Rule Memory for Long-Term Conversational Agents | 2609.03915 | Natural-language Horn-clause rules induced from dialogue, validated by a Rule Perplexity check, actively guiding retrieval and reasoning. |
| 2 | 9 | SQLCoder-7B-2 text-to-SQL model (weights) | https://huggingface.co/defog/sqlcoder-7b-2 | 7B open text-to-SQL model family widely used as small SQL emitter |
| 2 | 8 | STaR: Bootstrapping Reasoning With Reasoning | 2203.14465 | Generate-filter-retrain loop: rationalize answers, keep rationales that lead to correct answers, fine-tune; repeated bootstrapping improves  |
| 2 | 7 | SWE-bench: Can Language Models Resolve Real-World GitHub Issues? | 2310.06770 | Execution-verified GitHub issue-resolution benchmark; the substrate RepoGraph/CodexGraph deltas are measured on |
| 2 | 9 | ScrapeGraphAI-100k: Dataset for Schema-Constrained LLM Generation | 2602.15189 | 93695 schema-constrained extraction events, 18k schemas, per-example jsonschema conformance labels |
| 2 | 4 | Self-Consistency Improves Chain of Thought Reasoning in Language Models | arXiv:2203.11171 | Sample diverse paths then marginalize; GSM8K +17.9%; the parallel-thinking baseline all later work compares to |
| 2 | 9 | Spider: A Large-Scale Human-Labeled Dataset for Complex and Cross-Domain Semantic Parsing  | 1809.08887 | 10181 questions, 5693 SQL queries, 200 multi-table DBs across 138 domains; cross-domain split |
| 2 | 6 | Splitwise: Efficient generative LLM inference using phase splitting | 2311.18677 | Split prefill and decode onto different machines; phase-aware provisioning and scheduling. |
| 2 | 2,8 | The Chronos Vulnerability: A Taxonomy of Temporal Persistence and Memory-Based Deception | 2607.19433 | Taxonomy of memory-based attacks (MINJA memory injection, sleeper agents) against stateful agents with persistent memory. |
| 2 | 4 | Thoughts Are All Over the Place: On the Underthinking of o1-Like LLMs | arXiv:2501.18585 | Thought-switching without depth causes failures; TIP switching penalty fixes it incl. Best-of-N settings |
| 2 | 9 | TokenMizer: Graph-Structured Session Memory for Long-Horizon LLM Context Management | 2606.06337 | Typed session graph: 14 node and 7 edge types, 8-state lifecycle, bitemporal validity, decision transitions |
| 2 | 1 | ToolAlpaca: Generalized Tool Learning for Language Models with 3000 Simulated Cases | 2306.05301 | Multi-agent simulation synthesizes 3938 tool-use cases over 400-plus APIs; compact models reach GPT-3.5-level generalization to unseen tools |
| 2 | 1 | ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs | 2307.16789 | DFSDT search expands reasoning traces at data time; neural API retriever at inference is the retriever-in-harness precedent for ToolRAG. |
| 2 | 1 | Toolformer: Language Models Can Teach Themselves to Use Tools | 2302.04761 | Self-supervised API-call insertion: sampling-based admission gate keeps only calls that reduce loss; model emits call sites, harness execute |
| 2 | 9 | When Your Agent Opens the Chat App: Agent-Controlled Search over Raw Chat Logs Rivals Stru | 2608.12888 | Iterative lexical search over raw logs with session-aware fusion rivals structured-memory pipelines |
| 2 | 9 | WorldDB: A Vector Graph-of-Worlds Memory Engine with Ontology-Aware Write-Time Reconciliat | 2604.18478 | Content-addressed immutable nodes with Merkle-style audit trail and write-time ontology reconciliation |
| 2 | 9 | Zep memory-layer service (implementation) | https://github.com/getzep/zep | Memory-layer service built on Graphiti |
| 1 | 1 | Phi-4-Mini Technical Report: Compact yet Powerful Multimodal Language Models via Mixture-o | 2503.01743 | Synthetic math/code data recipe at 3.8B; frozen backbone plus modality LoRA routers is the closest vendor analog of shared-backbone adapters |
| 1 | 3 | RAG-Fusion: a New Take on Retrieval-Augmented Generation | 2402.03367 | Multi-query generation fused with reciprocal rank fusion |
| 1 | 6 | Uncovering and Understanding Hidden Dependencies in the LLM API Reseller Ecosystem via Pre | 2608.20732 | API-only measurement of hidden reseller dependencies using prefix-cache reuse as a timing side channel; shows the channel is practical, not  |

## Refutations

- CodeGraph: Enhancing Graph Reasoning of LLMs with Code (2408.13863): Primary abs page contradicts the brief's candidate label: this CodeGraph is LLM graph-reasoning-via-code, not a repository code graph

## Abstained (unresolved ledger)

- Reciprocal rank fusion outperforms Condorcet and individual rank learning methods (10.1145/1571941.1572114): Claims verified on ACM page and author PDF 2026-09-13, but no arXiv id so no papers/ PDF per naming rule; fusion claims therefore rest on non-filed primary.
- The Berkeley Function Calling Leaderboard (BFCL) (none (PMLR v267/patil25a)): Lane-10 benchmark territory; used here only as the eval harness behind ThinkBrake/Qwen3 claims, not independently studied
- A Survey of Knowledge Tracing: Models, Variants, and Applications (2105.15106): Abstract verified via search excerpt; paper not opened. Prefer admitted ACM survey (2201.06953); libraries noted as tooling follow-up.
- Automating Agentic Workflow Generation via Self-Adaptive Abstraction Operators (): Title/abstract verified via search excerpt from abs page; paper not opened. Follow-up to admitted AFlow (operator-memory mechanism); recommend promotion next ro
- Block-Attention for Efficient LLM Serving (unresolved) (): Could not verify any primary source; brief names it but no fetchable record was found.
- Building py-kvcache: A Performance Characterization of External KV Caching for vLLM with N (2609.11744 (S2 citation record; abs not opened)): Title-screened in S2 forward-chain sweep; primary source not opened.
- Business Logic-Driven Text-to-SQL Data Synthesis for Business Intelligence (2601.14518): Abs page opened during screening; ranked below admit cutoff (tangential to facts-schema question)
- CacheRoute: Planned Prefix-Affinity Routing for Large-Scale LLM Serving (2608.19677 (S2 citation record; abs not opened)): Title-screened in S2 forward-chain sweep; primary source not opened.
- Capacity, Not Format: Rethinking Structured Reasoning Failures (arXiv:2606.09410): Seen only on a fetched search page; primary source not opened
- Compressed Chain of Thought: Efficient Reasoning Through Dense Representations (arXiv:2412.13171): Abs page title/date verified only; full paper not opened, so no admitted claim; covered by Coconut/SoftCoT/Huginn
- DroidSpeak: KV Cache Sharing for Cross-LLM Communication and Multi-LLM Serving (2411.02820 (OpenAlex; abs page not opened)): Screened via OpenAlex record only; primary source not opened.
- Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions (2507.05257): Abstract verified via search excerpt from abs page; paper not opened. Eval benchmark = lane-10 territory; test-time-learning split is the only learning-graph ov
- FlashInfer: Efficient and Customizable Attention Engine for LLM Inference Serving (2501.01005 (OpenAlex; abs page not opened)): Screened via OpenAlex record only; arXiv abs page never opened, so no admit.
- FluctlightDB: A Memory Model of Data for AI Agents (2608.12365): Title verified on search page; abs page not opened in budget. High-priority follow-up, not admitted.
- GIKT: A Graph-based Interaction Model for Knowledge Tracing (2009.05991): Abstract verified via search excerpt from abs page; paper not opened. Graph-KT instance; coverage carried by admitted KT-Survey + DKT.
- GraniKV: Asymmetric Granularity KV-Cache Paging for Multi-Agent Systems with Long Shared P (2608.15584 (S2 citation record; abs not opened)): Title-screened in S2 forward-chain sweep; primary source not opened.
- Graph-Native Cognitive Memory: Formal Belief Revision Semantics (2603.17244): Title verified on abs page during id triage; paper not opened. Formal-verification angle for Proof deferred.
- HyphaeDB: A Living Knowledge Topology for Agent-First Memory (2606.28781): Abs opened; single-author perspective piece, architectural claims unverified, no artefact traced
- KVMem: Virtualizing Million-Token Agent Workspaces on a Consumer GPU (2609.04852 (S2 citation record; abs not opened)): Title-screened in S2 forward-chain sweep; primary source not opened.
- MemOS: An Operating System for Memory-Augmented Generation (2505.22101): Abs page opened and title verified; not downloaded to avoid double-counting one system. Prefer 2507.03724.
- OptimalThinkingBench: Evaluating Over and Underthinking in LLMs (arXiv:2508.13141): Seen only as a reference line; benchmark not opened or evaluated
- PEEK: Context Map as an Orientation Cache for Long-Context LLM Agents (2605.19932): Abs opened; orientation caching is tangential to the facts schema question
- RankRAG (unverified candidate) (unknown): Identified as candidate; primary source not opened within budget; no id or number is asserted.
- ReCache: Efficient KV Cache Reuse and Compression for Tool-Augmented LLM Agents (2608.19662 (S2 citation record; abs not opened)): Title-screened in S2 forward-chain sweep; primary source not opened.
- SEAL: Self-Evolving Agentic Learning for Conversational Question Answering over Knowledge  (2512.04868): Abs opened; conversational KBQA accuracy, not write-time memory design
- Schema Lineage Extraction at Scale: Multilingual Pipelines, Composite Evaluation, and Lang (2508.07179): Abs opened; enterprise ETL lineage, not agent memory
- Stop Overthinking: A Survey on Efficient Reasoning for Large Language Models (arXiv:2503.16419): Seen only as a citing-reference line on a fetched page; survey content not verified at primary source
- SuperLocalMemory V3: Information-Geometric Foundations for Zero-LLM Enterprise Agent Memor (2603.14588): Abs opened; formal proposal with no traced artefact or eval; needs full read before any claim
- Supra Cognitive Modes: A Routed Architecture for Agent Memory (2607.19096): Title verified on search page; abs page not opened in budget. Most on-point title seen; recommend promotion to admit next round.
- TOPAS: Workflow-Aware Prefix-State Scheduling for Multi-Agent LLM Serving (2608.25523 (S2 citation record; abs not opened)): Title-screened in S2 forward-chain sweep; primary source not opened.
- TRUSTMEM: Learning Trustworthy Memory Consolidation for LLM Agents (2606.25161): Title verified on search page; not opened further. Security-adjacent follow-up.
- The AI Hippocampus: How Far are We From Human Memory? (2601.09113): Title verified on search page; not opened further. Survey slot already covered by older prior-art rounds.
- Trusted Knowledge Extraction for Operations and Maintenance Intelligence (2507.22935): Abs opened; component list only, no memory architecture
- When Cache Poisoning Meets LLM Systems: Semantic Cache Poisoning and Its Countermeasures (doi:10.14722/ndss.2026.240200): Existence corroborated (DOI resolution + OpenAlex record) but authorship/title not verified at a readable primary source.
- When Correct Isn't Usable: Improving Structured Output ... (arXiv:2605.02363): Seen only on a fetched search page; primary source not opened
- When Memory Lies: An Empirical Study of Spatial Memory Staleness in VLM Agents (2608.04574): Abs opened; staleness framing relevant but spatial-VLM modality out of scope; MOSAIC/SodaMem cover the need
- ZenBrain: A Neuroscience-Inspired 7-Layer Memory Architecture (2604.23878): Title verified on search page; not opened further. Layered-vs-typed comparison deferred.
- memoria (secure memory management for agents) (https://github.com/matrixorigin/memoria): Search-snippet screening only; repo not opened. Security-adjacent follow-up.
- memoripy (evidence-first local memory) (https://github.com/caspianmoon/memoripy): Search-snippet screening only; repo not opened. Evidence-first framing is close to MelodyScribe quotes; follow-up candidate.
- (recalled Co-LLM id, actually AI-metaphor education) (2401.08711): Memory-suggested Co-LLM id verified as unrelated; true referent found via quoted arXiv search (2403.03870, repo clinicalml/co-llm).
- (recalled DRAGIN id, actually warp-drive physics) (2309.10072): Memory-suggested DRAGIN id verified as unrelated GR paper; true DRAGIN id found via arXiv search UI (2403.10081). Recorded as verification hygiene.
- (recalled proxy-tuning id, actually inflation cosmology) (2312.12286): Memory-suggested id verified as unrelated cosmology paper; do not cite near proxy tuning.
- (recalled proxy-tuning id, actually tau-decay physics) (2307.09228): Memory-suggested id verified as unrelated particle-physics paper; do not cite near proxy tuning.
- (unable to isolate a paper by this name) (—): arXiv quoted searches for proxy tuning / tuning by proxy did not surface a matching LM paper; admitted Emulated Fine-Tuning (2310.12962) as the verified proxy-a
- APIBench component of Gorilla (part of 2305.15334): Screened via Gorilla paper; no standalone record opened. Covered by admitted Gorilla row.
- Agent Skill Induction / WALT (skill methods cited by WebXSkill) (): Known only via WebXSkill Table-1 citations (Wang et al. 2025b; Prabhu et al. 2026); no arXiv id verified, pages not opened. Follow-up candidates.
- AgentKVShift: Efficient KV Cache Reuse for Agentic Memory Systems (2607.21604): Title verified on abs page during id triage; lane 6 territory, recorded only.
- Assumed HippoRAG 2 arXiv id 2505.03234 (2505.03234): Abs page opened; id rejected. Continual-learning coverage carried by admitted 2502.14802 from the same team.
- ESceme: Vision-and-Language Navigation with Episodic Scene Memory (2303.01032): Abs page opened during id triage; irrelevant.
- Evaluating Memory in LLM Agents via Incremental Multi-Turn Interactions (2507.05257 (seen in excerpts only)): Abs page never opened; seen only in search excerpts.
- Generalised ultracategories (id 2507.07922, near-miss of MIRIX id) (2507.07922): Abs page opened; irrelevant. Documents why ids are verified digit-by-digit in this lane.
- HammerBench: Fine-Grained Function-Calling Evaluation in Real Mobile Device Scenarios (2412.16516 (seen in excerpts only)): Abs page never opened; seen only in search excerpts.
- IDP AutoOpt: Agent-Driven Optimization of Document Processing Pipeline Configurations (2607.26075): Abs opened; document-processing config tuning, out of lane scope
- Impact of Medical Data Imprecision on Learning Results (NOT attentive KT) (2007.12375): Abs page opened: assumed AKT id resolves to an unrelated medical-data paper. AKT (Ghosh et al., KDD 2020) has no verified arXiv id; guard row.
- Mem0: Building production-ready AI agents with scalable long-term memory (2504.19413 (seen in excerpts only)): Lane 2 territory; seen only as a baseline inside Memory-R1 excerpts.
- MemoryBench: A Benchmark for Memory and Continual Learning in LLM Systems (2510.17281 (seen in excerpts only)): Abs page never opened; seen only in search excerpts. Name collision with MemBench noted.
- Metric Ensembles For Hallucination Detection (NOT ExpeL) (2310.10495): Abs page opened: recalled ExpeL id resolves to an unrelated hallucination-detection paper. Guard row against id confusion; true ExpeL is 2308.10144.
- NOT CodeS: Signals of Detailed Balance Violation in Nonequilibrium Stationary States (2402.14738): Abs page opened: id does not match the expected text-to-SQL paper; CodeS/DIN-SQL not located via search
- No memory-harness benchmark under the name MemBench found (): Screened via GitHub search; nothing matching the brief's MemBench seed exists as a memory-harness benchmark. Treated as naming gap, not a refutation.
- OPT-BENCH: Evaluating Iterative Self-Optimization of LLM Agents (2605.08904): Abs page opened during id triage; irrelevant to ingest routing.
- Optical study of charge dynamics in topological insulators (NOT Agent Workflow Memory) (2405.15283): Abs page opened: recalled AWM id resolves to a condensed-matter physics paper. Guard row; true AWM is 2409.07429.
- Profile-Graph Memory: Implicit Cross-Entity Traversal (2607.19359): Title verified on abs page during id triage; recall-side, left to lane 3.
- R1-Searcher++: Incentivizing the Dynamic Knowledge Acquisition of LLMs via Reinforcement L (2505.17005 (seen in excerpts only)): Abs page never opened; seen only in search excerpts.
- Recalled arXiv id 2311.05390 for NexusRaven (2311.05390 (WRONG)): Could not verify recalled id; NexusRaven admitted as repo artefact instead. Do not cite 2311.05390.
- Recalled arXiv id 2406.03600 for APIGen (2406.03600 (WRONG)): Could not verify recalled id; corrected and admitted under true id. Do not cite 2406.03600 for APIGen.
- Recalled arXiv id 2409.13324 for TinyAgent (2409.13324 (WRONG)): Could not verify recalled id; corrected and admitted under true id. Do not cite 2409.13324 for TinyAgent.
- SARATHI: Efficient LLM Inference by Piggybacking Decodes with Chunked Prefills (2308.16369 (seen in excerpts only)): Abs page never opened; superseded by admitted Sarathi-Serve.
- SQLMesh data-pipeline tool (lookup attempt) (https://github.com/TobikoData/sqlmesh): GitHub API rate-limited before verification; data-pipeline tool tangential to agent fact vault
- Towards Reasoning Era: A Survey of Long Chain-of-Thought (arXiv:2503.09567): Survey; not opened, no admitted claim
- Training Web Agents via End-to-End Multi-Turn Reinforcement Learning (2505.16421 (seen in excerpts only)): Abs page never opened.
- memory-alpha-kit (OpenClaw portable memory kit) (https://github.com/ApeironOne/memory-alpha-kit): Search-snippet screening only; recorded to prevent confusion with admitted Mem-α (2509.25911).
- unverified (title not fetched) (1808.09602): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2503.18596): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2503.19988): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2505.18122): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2506.07423): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2506.18951): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2507.02529): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2507.17896): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2507.22478): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2508.04623): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2509.00581): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2509.01055): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2509.01308): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2509.05899): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2509.23338): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2510.07642): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2510.08958): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2510.10661): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2510.13853): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2510.26495): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2511.00805): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2511.01008): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2511.04153): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2511.10192): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2511.13590): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2511.13907): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2512.22250): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2601.03785): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2601.05451): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2601.08778): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2601.09876): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2601.17942): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2602.05385): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2602.11745): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2602.12064): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2602.13530): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2602.16720): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2603.04740): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2603.05996): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2603.13390): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2603.20004): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2604.04853): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2604.07041): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2604.13686): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2604.16511): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2604.19795): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2604.21284): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2605.02815): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2605.03354): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2605.03720): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2605.04897): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2605.07313): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2605.09863): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2605.27785): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2605.28969): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2605.29670): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2605.30538): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.01338): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.02109): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.03145): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.03363): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.03463): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.05906): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.06054): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.08018): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.08245): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.13174): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.14201): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.15598): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.18108): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.26511): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.28327): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.28601): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.29733): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.30133): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2606.30851): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2607.03991): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2607.05577): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2607.06799): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2607.13311): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2607.20489): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2607.22622): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2607.22624): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2607.23340): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.00017): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.00485): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.00693): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.05906): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.07213): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.07946): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.09260): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.09588): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.15145): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.15389): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.24921): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.27796): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.29345): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2608.29543): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2609.00367): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2609.00834): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2609.02944): Not opened; secondary screening only, no claim made
- unverified (title not fetched) (2609.10413): Not opened; secondary screening only, no claim made
- vAttention: Dynamic Memory Management for Serving LLMs without PagedAttention (2405.04437 (seen in excerpts only)): Abs page never opened; seen only in excerpts.
