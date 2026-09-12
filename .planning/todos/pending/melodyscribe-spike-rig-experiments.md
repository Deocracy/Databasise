---
title: MelodyScribe spike — the two rig experiments that settle feasibility
date: 2026-09-11
priority: medium
---

Run as `/gsd-spike melodyscribe` when there is GPU time. Per D-MS-05 the model size is a variable: run experiment 2 (and where cheap, experiment 1) across a size sweep, 1B to 8B dense locally plus one mixture of experts with expert offload, and report the size-versus-accuracy curve before any size is chosen. The 2B references below are the current candidate, not a constraint. Two experiments, each with a pass condition stated before the run.

1. **2B self-embedding quality.** Train an LLM2Vec-style adapter (bidirectional attention + MNTP + SimCSE) on MiniCPM5-2B (standard `LlamaForCausalLM`, so the recipe applies without model code). Compare retrieval on the Phase 3 20-document parity corpus against a dedicated embedder (Qwen3-Embedding-0.6B or MiniCPM-Embedding-Light). Pass: retrieval parity within a margin stated before the run. Record tokens/sec for embedding at 2B versus the dedicated embedder, since index-time cost is the known structural loss (feasibility.md reason 2).

2. **2B routing accuracy.** Given extracted pieces from the same corpus, does MiniCPM5-2B choose graph / vector / SQL / Folio correctly against a frontier-labelled set, with grammar-constrained decoding on so only semantic errors count. Pass: accuracy threshold stated before the run. If it fails, the fine-tune path is MiniCPM's own recipe: frontier teacher on our schema, on-policy distillation into the 2B, producing `MelodyScribe-2B-v0.1`.

3. **Cache reuse quality (added 2026-09-11).** On the same corpus, compare answer quality when retrieved chunks are composed as isolated KV modules (llama.cpp `seq_cp` + `seq_add`) versus fully prefilled, and versus llama-server `--cache-reuse` shift reuse. See `reference/micro-harnesses/score-format-and-cache.md` §4-5. Pass: stated non-inferiority margin.

Evidence standard: no vendor benchmark number settles either; the rig does. Sources and prior art: `reference/micro-harnesses/`.
