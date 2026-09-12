---
spike: 006
idea: melodyscribe
name: hybrid-embedder
type: comparison
validates: "Given teacher-generated query-passage pairs with a held-out document split, when the small model's [EMB] state is trained by a LoRA contrastive adapter and by distillation to the 0.6B embedder, and when the 0.6B embedder is weight-merged with its same-architecture generative base, then recall@k and MRR versus the dedicated 0.6B embedder, and generation retained (op emission under grammar) for each mixed model"
verdict: PENDING
related: [002, 003, 004]
tags: [embeddings, adapter, merge, training]
---

# Spike 006: hybrid-embedder

## What This Validates

Spike 004 showed that untrained last-token states are anisotropic and that a ridge head over frozen states makes retrieval worse; the open test was training. This spike runs the three cheapest ways to mix an embedding model with a small generative model and measures both retrieval quality and what the generative side keeps. Read `.claude/skills/spike-findings-melodyscribe/references/model-size-and-training.md` first: it holds spike 004's numbers and the harness rules.

## Plan

Data: `.planning/spikes/shared/queries-v1.json` (teacher-generated, six per document, `split` train or test by document, provenance and counts inside the file). Passages are the corpus documents (`databasise/tests/fixtures/corpus/`, one unit per document as in spike 003). Negatives: in-batch plus the other documents' passages as hard negatives. Never train on test documents or on the two HotpotQA gold queries.

Arms, identical test inputs:

- A: Qwen3-Embedding-0.6B, the baseline from spike 004 (GGUF through llama_cpp in `.venv`, or safetensors through sentence-transformers in `.venv-train`; choose one, state it, keep it fixed across arms).
- B: MiniCPM5-2B plus a LoRA contrastive adapter: InfoNCE over query to passage, temperature 0.02 to 0.05, in-batch and hard negatives, pooled at the `⟦EMB⟧` marker state (last token), causal attention kept because the one-pass design needs it. Weights `.models/hf/openbmb__MiniCPM5-2B`, venv `.venv-train`, bf16, gradient checkpointing, sequence length at most 512, LoRA rank 16 on attention and MLP projections, at most 30 minutes GPU per training run. Report a bidirectional-attention variant only if it costs less than one extra run.
- C: MiniCPM5-2B plus a LoRA adapter distilled to A: minimise one minus cosine between a linear projection of the marker state and A's vector for the same text, plus the InfoNCE term. This is the "embedding model mixed into the small model" arm.
- D: weight merge of `Qwen/Qwen3-Embedding-0.6B` with `Qwen/Qwen3-0.6B` (same architecture): linear interpolation at 0.25, 0.5, 0.75, and TIES or DARE through mergekit if it is installed in `.venv-train`, otherwise plain safetensors arithmetic. Embed with last-token pooling and A's instruction format; generate with the untouched base's chat template.
- E (control): MiniCPM5-2B untrained (spike 004's arm B) on the new query set.

Metrics: recall@1, @3, @10 and MRR on the test split and on the HotpotQA gold queries; mean pairwise document cosine (anisotropy); generation retained: op emission under the v0.2 grammar with the adapter on versus off using spike 003's `student.py` and `evaluate.py` against its `teacher.json` (routing_exact and Proof-pass rate), and for D the merged 0.6B versus the untouched Qwen3-0.6B base; training wall time, peak VRAM, and embedding milliseconds per text for every arm.

Pass conditions, stated before the run: B or C reaches MRR within 0.05 of A on the test split with routing_exact and Proof-pass within 0.05 of the untouched 2B; D keeps at least 90 percent of the base's Proof-pass rate while reaching at least 0.8 of A's MRR. Anything short is PARTIAL with the curve. A run that cannot fit in 16 GB is a recorded INVALIDATED sub-claim, never a silent downgrade.

Environment: `source .planning/spikes/env.sh` before any Python. Training and merging under `.planning/spikes/.venv-train/bin/python` (torch CUDA, transformers, peft, sentence-transformers, safetensors; mergekit if `.logs/setup-train.out` says it installed). GGUF inference under `.planning/spikes/.venv/bin/python`. Every GPU process under `flock /tmp/melodyscribe-gpu.lock`; one model per process. Save adapters and merged weights under this folder in `adapters/` and `merged/` (git-ignored) and record their SHA-256 in the README.

## Research

(to fill: docs read, approaches compared)

## How to Run

(to fill)

## What to Expect

(to fill)

## Investigation Trail

(to fill: every iteration with its log)

## Results

(to fill: verdict with sub-claims and the head-to-head table)
