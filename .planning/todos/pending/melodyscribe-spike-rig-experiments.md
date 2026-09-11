---
title: MelodyScribe spike — the two rig experiments that settle feasibility
date: 2026-09-11
priority: medium
---

Run as `/gsd-spike melodyscribe` when there is GPU time. Two experiments, each with a pass condition stated before the run.

1. **2B self-embedding quality.** Train an LLM2Vec-style adapter (bidirectional attention + MNTP + SimCSE) on MiniCPM5-2B (standard `LlamaForCausalLM`, so the recipe applies without model code). Compare retrieval on the Phase 3 20-document parity corpus against a dedicated embedder (Qwen3-Embedding-0.6B or MiniCPM-Embedding-Light). Pass: retrieval parity within a margin stated before the run. Record tokens/sec for embedding at 2B versus the dedicated embedder, since index-time cost is the known structural loss (feasibility.md reason 2).

2. **2B routing accuracy.** Given extracted pieces from the same corpus, does MiniCPM5-2B choose graph / vector / SQL / Folio correctly against a frontier-labelled set, with grammar-constrained decoding on so only semantic errors count. Pass: accuracy threshold stated before the run. If it fails, the fine-tune path is MiniCPM's own recipe: frontier teacher on our schema, on-policy distillation into the 2B, producing `MelodyScribe-2B-v0.1`.

Evidence standard: no vendor benchmark number settles either; the rig does. Sources and prior art: `reference/micro-harnesses/`.
