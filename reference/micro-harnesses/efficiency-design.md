# MelodyScribe efficiency design, after the deep-research run

Date: 2026-09-11. Answers "how do we maximise efficiency, does OneGen help, what else to consider", using `deep-research/REPORT.md` as the evidence base. Every claim below cites the report item it rests on; owner analysis is marked.

## 0. What efficiency means here, so it can be measured

| Metric | Why it dominates |
|---|---|
| Generated tokens per paragraph at ingest | Decode is memory-bound and serial; it is the cost that scales with corpus size |
| Prefill tokens per paragraph | Batched and compute-bound; cheap on a GPU for a 2B model |
| Frontier tokens per user query | The only cost paid in money; MelodyScribe exists to drive it to distilled context only |
| Wall-clock per 1,000 paragraphs, and query TTFT | What the operator feels |
| Re-index cost on model change | Hidden cost of self-embedding: a new model revision is a new embedding space (CONTRACT §4) |
| VRAM | 16 GB on legion bounds batch size, quantisation, and training |

Quality gates travel with every metric: retrieval recall@k, op accuracy against the teacher, SQL execution accuracy, graph validator pass rate. An efficiency gain that fails a gate is not a gain.

## 1. Does OneGen help? Yes, and it changes the embedding mechanism

OneGen (2409.05152, report #1) is the only admitted work that generates and retrieves in one forward pass: retrieval tokens emitted autoregressively double as embedding queries and reuse the live KV cache, with no generation degradation reported at 7B. Lane 1 also **refutes the assumption in our `runtime-one-pass.md` that pooling the paragraph's own hidden states is free**: untrained last-token causal embeddings underperform a learned head (NV-Embed 2405.17428), LLM2Vec needs bidirectional enablement plus MNTP, SGPT needs position-weighted pooling.

So the mechanism becomes a **trained token, not a pooled span**:

- At ingest, the harness appends one special token `[EMB]` after every Score section marked `embed`. That token's last-layer state is the section's embedding. It costs one token of prefill per section, no extra pass, no pooling heuristic.
- At query time the model itself emits `[RQ]` when it wants to recall; its state is the query embedding; the harness retrieves and appends results; generation continues on the same cache. That is OneGen's mechanism and it gives multi-hop recall for free.
- Training: OneGen's joint objective, generation loss plus contrastive loss on the `[EMB]`/`[RQ]` positions, as a LoRA on MiniCPM5-2B. This is the concrete experiment for report gap 1 and the lane-1 unknown "generation degradation at 1–3B is unmeasured".

Caution carried from the report: OneGen is demonstrated at 7B only; retrieval tokens consume generation budget (one token each, which is the cheapest possible); PromptEOL (2307.16645) is the zero-training baseline to beat.

## 2. First-order levers: generated tokens and batching

1. **Fewest output tokens.** Thinking mode off for the transcriber. A terse op schema: short keys, entity ids instead of repeated strings, a list of ops per paragraph, and an explicit empty list as the cheapest legal output. Grammar-constrained via compressed FSMs so constraint checking is near-free per token (SGLang, report #19; XGrammar 2411.15100). The report is explicit that constraints buy format validity only, not decision quality (2608.13959); accuracy comes from training (section 5 below).
2. **Batch the prefill.** Paragraphs are independent; run dozens per decode call. The fixed `doc_prefix` is shared, and SGLang's radix-tree cache reuses it across all of them. This is the prefix-structured reuse the report says is what radix caching actually gives.
3. **Speculative decoding** with the vendor's DSpark draft model for MiniCPM5-2B keeps outputs identical and speeds decode; on a 2B model decode is memory-bound, so this is where a draft pays.
4. **Quantise the base, keep the adapter in bf16.** Q8 or GPTQ-4bit weights; QLoRA-facts (2608.25677) and LoRA-learns-less (2405.09673) bound what to expect: LoRA learns less and forgets less, which is the right trade for a narrow filing task on a general base.

## 3. KV-cache reuse is second-order at 2B, and the arithmetic says why (owner analysis)

MiniCPM5-2B: 42 layers, 2 KV heads, head dim 128 → about 43 KB of KV per token in bf16. A 250-token paragraph is about 11 MB; a 10,000-chunk corpus is about 107 GB of cached state. Prefilling that same paragraph on a 2B model takes tens of milliseconds. Storing per-paragraph KV modules for the whole corpus therefore costs more than recomputing them, at this model size.

What survives from lane 2:

- **Runtime prefix reuse** (radix cache) for the shared prefix, the Folios, and the live session: always on, no storage cost.
- **Query-time composition** of the retrieved set only, with CacheBlend's selective recompute (2405.16444, report #2) as the compose operator, because out-of-order composition without repair is refuted. Run our own length sweep: DAF (2607.21599) contests the no-loss claim at long contexts.
- **No compression-plus-repair stack** at small scale: CacheGen (2310.07240) plus C2KV (2607.17715) warn the combination degrades, and nobody has validated it at 1–3B (report gap 3).

Net: KV modules are a query-latency optimisation for large retrieved sets, not an ingest-cost lever. Measure TTFT with and without composition before building anything.

## 4. Structure must earn its cost

Three refutations bear directly on the filing design: agent-controlled search over raw chat logs rivals structured memory (2608.12888); naive RAG is as good as LightMem for memory management (2607.29104); "contextual agentic memory is a memo, not true memory" (2604.27707). The efficient design keeps **raw text plus embedding retrieval as the baseline that every store must beat on the rig**. Graph and SQL filing are enabled per query type only when the rig shows a gain, and the transcriber's cheapest output, an empty op list, is the default it should reach for. "File less" is an efficiency lever, and MiniRAG (2501.06713, report #14) shows a small-model graph design that files at a quarter of the storage.

## 5. Training for accuracy, not decoding tricks

The single-GPU recipe the report assembles (lane 7): rationale-augmented SFT (Distilling Step-by-Step, report #18: train with the teacher's rationale, infer without it, so rationales cost nothing at runtime), then on-policy or sequence-level distillation (DistiLLM 2402.03898, MiniLLM 2306.08543), as LoRA or QLoRA, with grammars for format only. **DeepRetrieval (2503.00223, report #3) is the strongest support for the whole hypothesis at our scale**: reinforcement learning with verifiable rewards trained Qwen2.5-3B query and SQL rewriting that beats GPT-4o and Claude 3.5 on retrieval and on BIRD/Spider SQL, with 3B checkpoints released under MIT. Our rewards are already verifiable: retrieval hit rate, SQL execution correctness, graph validator pass. That is the second training stage after distillation, and it is the answer to report gap 5 (a trained filing router with process supervision).

## 6. Use the cheapest component that can do each step (owner analysis, artefacts from report section 6)

- **GLiNER** (2311.08526, Apache-2.0, CPU/ONNX) finds entity spans before the LLM sees the paragraph, so the 2B only links and decides.
- **Qwen3-Embedding-0.6B** (Apache-2.0) is the dedicated-embedder baseline the `[EMB]` token must match, and the fallback durable index (section 7).
- **Adaptive-RAG's sub-1B router** (2403.14403, Apache-2.0) decides whether a query needs the 2B at all.
- **RECOMP compressors** (2310.04408, MIT) shrink retrieved context before it reaches the frontier model, which is the frontier-token lever.
- **SGLang** as the first serving engine to evaluate: radix reuse, compressed-FSM grammars, DSpark, and the native MiniCPM5 tool-call parser in one runtime.

## 7. What else to consider

1. **Decouple the durable index from the model version.** Self-embedding couples every vector to the 2B revision; each fine-tune is a re-index (CONTRACT §4 space hash). Option: the frozen 0.6B embedder owns the durable index; the 2B's `[EMB]`/`[RQ]` tokens serve session recall and the small, cheap-to-re-embed Folios. Decide on the rig by re-index cost against retrieval gain.
2. **Revise rarely, gated, and benchmarked.** Lane 8's core result: every revise operator gated on an external signal (retrieval miss, validator conflict, human label) and compared with best-of-N sampling at equal token budget (2607.28576); continuously LLM-updated memories degrade (2605.12978). This is cheaper and safer than a scheduled loop.
3. **Security requirements from report section 5** for the Folio gate: PoisonedRAG's two-condition test (2402.07867) and MINJA (2503.03704) replicated on file-memory skills (report gap 8); CaMeL (2503.18813) as the control-flow pattern that keeps untrusted data out of the privileged planner.
4. **Temporal validity and forgetting.** Validity windows outside Zep are unreplicated at small scale (gap 12); Learning-to-Forget (2603.14517) and Retain-or-Consolidate (2607.17545) give budget-aware eviction.
5. **Licenses.** NV-Embed and jina-embeddings-v3 are non-commercial; Honcho is AGPL; REBEL and PathRAG have no detected license. Section 6 lists the clean set.
6. **Benchmarks to pin now**: JSONSchemaBench (2501.10868) for constrained ops, BIRD dev (2305.03111) for SQL, HELMET at 8k/16k (2410.02694) and LongEmbed for embeddings, RAGBench (2407.11005); and our own rig corpus, because the memory-layer benchmarks the report screened do not replicate well.
7. **Measure generation degradation from embedding duty at 2B** before anything else (gap 1, gap 6). It is the one unknown that decides whether one model or two.

## 8. The experiment order this implies

1. Baseline: Qwen3-Embedding-0.6B index plus MiniCPM5-2B no-think op emission with grammar, batched on SGLang. Record every metric in section 0.
2. Add `[EMB]`/`[RQ]` tokens via OneGen-style joint LoRA; measure retrieval parity against the baseline and generation degradation on the op task.
3. Distil the filing ops from the frontier teacher (rationale-augmented SFT), then RLVR on rig rewards (DeepRetrieval recipe).
4. Query-time KV composition with selective recompute; length sweep; keep only if TTFT improves at equal quality.
5. Revise pass, gated, versus best-of-N at equal budget.
