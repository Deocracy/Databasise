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

## How to Run
(filled by the spike agent)

## What to Expect
(filled by the spike agent)

## Investigation Trail
(updated as the spike progresses: what was tried, what it revealed, what was tried next)

## Results
(verdict, evidence, surprises)
