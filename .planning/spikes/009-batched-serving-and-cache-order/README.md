---
spike: 009
idea: melodyscribe
name: batched-serving-and-cache-order
type: comparison
validates: "Given N queued op-emission and embedding requests over the corpus, when served with continuous batching on one 16 GB GPU with prompt segments ordered for prefix sharing, then aggregate tokens per second, requests per second, TTFT, VRAM, and cache-hit token fraction at N in 1, 4, 16, 64, 256, 1024 for the slot count that saturates the GPU"
verdict: PENDING
related: [002, 005]
tags: [serving, batching, prefix-cache, throughput]
---

# Spike 009: batched-serving-and-cache-order

## What This Validates

What "a thousand parallel agents" means on one GPU: how many concurrent sequences saturate it, what throughput that gives for ingest (one-pass op emission per paragraph) and for retrieval (embedding plus top-k), and how prompt and output ordering change the share of the KV cache that is reused. Read `.claude/skills/spike-findings-melodyscribe/references/one-pass-runtime.md` first (spike 002's sequence API use, spike 005's TTFT numbers).

## Plan

Serving paths, try in this order and report which worked on this rig:

1. llama_cpp low-level multi-sequence batching in `.venv` (the `llama_batch` with sequence ids that spike 002 used): implement a small scheduler with K slots over a queue of N requests, interleaving prefill and decode, with grammar sampling per slot for op emission. This path must work; it is the floor.
2. vLLM in a fresh `.venv-vllm` (pip, using the same interpreter as `.venv-train`) with `Qwen/Qwen3-1.7B` from `.models/hf/` and automatic prefix caching on, if it installs and runs under nix-ld within 20 minutes of trying; otherwise record the failure and move on.
3. A prebuilt llama.cpp `llama-server` CUDA binary only if it runs without any system change (nix-ld plus the pip CUDA libraries in `env.sh`); otherwise skip and say so.

Workloads: (a) ingest: op emission under the v0.2 grammar on the 20 corpus units repeated to fill N, MiniCPM5-2B Q8; (b) retrieval: embed a query with Qwen3-Embedding-0.6B and take top-10 from a Faiss index of the corpus, repeated to fill N.

Sweep: N in 1, 4, 16, 64, 256, 1024 queued requests; K slots in 1, 4, 8, 16, 32, and higher while VRAM allows at context 1024. Report aggregate tokens per second, requests per second, TTFT median and p95, peak VRAM, and the K that saturates the GPU for each workload. Derive documents per minute for ingest and queries per second for retrieval.

Cache order: with the shared prefix of a Score (system turn, skill text, document prefix) and per-request tails, measure the prefix-cache hit fraction and TTFT for segment orders that put the instruction before versus after the section, and for requests sorted by shared prefix versus arriving in random order. Output order: op lists emitted graph first, then SQL, then Folio, versus interleaved; measure whether the recall-time continuation from a section's KV (spike 002's sequence copy) reuses the decoded state, by TTFT of the continuation.

Pass conditions, stated before the run: a throughput curve with a recommended K per workload; the ordering that maximises cache hits with its measured TTFT gain; a plain statement of true concurrency versus queue depth on this GPU, so "1000 agents" is stated as a queue of 1000 over K slots at X documents per minute.

Environment: `.venv`, `env.sh`, every model load under the GPU lock (a batched server holds the lock for its whole run); one model per process; timings only from lock-held runs.

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
