# Spike Wrap-Up Summary

**Date:** 2026-09-12 (round 1), 2026-09-12 (round 2)
**Spikes processed:** 10
**Feature areas:** Score I/O contract; One-pass runtime; Model size and training; Embedding training and hybrids; Graph prompt design; Serving and pipeline order
**Skill output:** `./.claude/skills/spike-findings-melodyscribe/`

## Processed Spikes
| # | Name | Type | Verdict | Feature Area |
|---|------|------|---------|--------------|
| 001 | score-io-model | standard | VALIDATED | Score I/O contract |
| 002 | one-pass-runtime | standard | VALIDATED | One-pass runtime |
| 003 | op-emission-size-sweep | comparison | VALIDATED | Model size and training (v0.2 evidence to Score I/O contract) |
| 004 | self-embedding-parity | comparison | PARTIAL | Model size and training |
| 005 | kv-composition-quality | standard | PARTIAL | One-pass runtime |
| 006 | hybrid-embedder | comparison | PARTIAL | Embedding training and hybrids |
| 007 | embedding-prompt-sensitivity | comparison | VALIDATED | Embedding training and hybrids |
| 008 | graph-prompt-design | comparison | VALIDATED | Graph prompt design |
| 009 | batched-serving-and-cache-order | comparison | VALIDATED | Serving and pipeline order |
| 010 | pipeline-order-end-to-end | standard | PARTIAL | Serving and pipeline order |

All five were built by Muse Spark 1.3 agents through `run-spike.sh` (total agent cost about USD 0.32) and accepted only after an owner-side re-run of each `run.sh` reproduced the numbers; 003's re-run reproduced all 126 student decodes byte-identically.

## Key Findings
1. The one-pass mechanism is real at 2B: embedding and logits from one decode, isolated sequences, bit-exact prefix copy, grammar-constrained ops, prefill about 3.7k tokens/s (002).
2. The contract holds: Score compilation is deterministic and neighbour-independent, and Proof passes 95/95 acceptance checks (001). Evidence must be a verbatim quote the harness resolves to offsets; model-emitted offsets fail for frontier and small models alike (003, spec v0.2 candidate, owner review pending).
3. Scale alone does not buy accuracy pre-fine-tune: 1B emits an empty op list on every document; routing is flat 0.30 to 0.45 from 2B to 8B while tokens and seconds per paragraph grow about a hundredfold. Cost is the size differentiator today; the starting candidate is 2B-class and the question reopens after training (003, D-MS-05).
4. Untrained self-embedding is not usable: the dedicated 0.6B embedder wins by a wide margin because untrained states are anisotropic (pairwise cosine 0.91 to 0.95 versus 0.28); a ridge head does not close the gap; the contrastive adapter is the open test and needs query-passage pairs (004).
5. KV modules are second-order at 2B: TTFT 2.4x to 8.5x relative but 20 to 110 ms absolute; shift reuse about 1.1x; saved state not bit-exact. Keep runtime prefix reuse, skip a persisted module store (005).
6. Fine-tune targets from Proof's failure categories: evidence quotes must contain the subject or value, ISO dates, termination under the cap (003).

## Round 2 key findings (2026-09-12, after deep research 2)
7. Contrastive LoRA on the 2B closes most of the untrained embedding gap in 147 s of GPU (test MRR 0.316 to 0.748 against the 0.6B embedder at 0.801, stable across seeds) but misses parity by 0.05 and collapses op emission to zero parses; distillation to the embedder is worse than plain contrastive; a linear merge of the 0.6B embedder into its generative base climbs monotonically to 0.82 of the embedder (006).
8. The embedder is prompt-insensitive for ranking on this corpus (no design past the 0.05 bar, wrong-domain control harmless); documents stay bare; the chat-template doc_prefix holds by default (007).
9. One-shot with a held-out teacher example is the prompt that clears the 0.10 bar on the 4B and keeps one pass; two-step scores higher at a second decode; LightRAG-style wording collapses; placement cost is model-dependent; few-shot gains are verbatim quoting (008).
10. Sixteen slots saturate greedy decode on the 16 GB card at about 2470 tokens/s; grammar filtering costs 9x on the CPU side; instruction-first ordering doubles the shared prefix and prefix-once saves 15 to 24 percent of prefill; "1000 agents" is a queue over K slots at about 44 sections per minute ingest and 800 queries per second retrieval (009).
11. One pass equals two passes, streamed equals batched writes, merge at write time equals a revise pass, whole-document chunks beat splits, one worker per model process; flat-bonus fusion loses to vector-only recall, so ship vector-first with graph and SQL as backoff (010).
12. Round-2 harness rules: pre-registered bars, held-out few-shot examples, noise-floor probes, per-model placement, teacher-generated labelled data with a fixed split, generation-retained reporting for every adapter or merge.
