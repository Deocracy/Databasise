---
spike: 002
idea: melodyscribe
name: one-pass-runtime
type: standard
validates: "Given llama-cpp-python with CUDA on legion and MiniCPM5-2B, when one decode runs over prefix+section+[EMB], then embeddings and logits come from the same call, ops decode under grammar, isolated sequences are neighbour-independent, and throughput is recorded"
verdict: PENDING
related: []
tags: [llama.cpp, cuda, kv, embeddings]
---

# Spike 002: one-pass-runtime

## What This Validates
Given llama-cpp-python with CUDA on legion and MiniCPM5-2B, when one decode runs over prefix+section+[EMB], then embeddings and logits come from the same call, ops decode under grammar, isolated sequences are neighbour-independent, and throughput is recorded

## Research
(filled by the spike agent: docs checked, approaches compared, chosen approach)

Known before the spike started (environment smoke test, 2026-09-12, under the GPU lock):
- `llama_cpp` 0.3.35 with CUDA offload loads MiniCPM5-2B Q8 in 1.5 s with `n_gpu_layers=-1`; greedy generation is correct ("The capital of France is" → " Paris"); `Llama(embedding=True).embed()` returns a 2048-dim vector.
- llama.cpp prints `init: embeddings required but some input tokens were not marked as outputs -> overriding` when `embedding=True`: the high-level wrapper marks outputs for you; the low-level `llama_batch` path needs the output flag set on the positions you read, which is what `[EMB]` positions require.
- `source .planning/spikes/env.sh` is mandatory before importing llama_cpp; `$MELODYSCRIBE_PY` and `$MELODYSCRIBE_MODELS` are exported by it.
- Spike 001 hands over: token plans mark post-decode read positions as `cap_relative`; resolve them from the decoded count. Re-run 001's I1 invariant against real tokenizer ids (001 used tokenizer version `toy-word-v1`).

## How to Run
(filled by the spike agent)

## What to Expect
(filled by the spike agent)

## Investigation Trail
(updated as the spike progresses: what was tried, what it revealed, what was tried next)

## Results
(verdict, evidence, surprises)
