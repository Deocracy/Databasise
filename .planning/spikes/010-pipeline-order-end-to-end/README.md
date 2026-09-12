---
spike: 010
idea: melodyscribe
name: pipeline-order-end-to-end
type: standard
validates: "Given the 20-document corpus, the shared query set, and the HotpotQA queries, when the harness runs end to end with W parallel workers (chunker, Score, one pass embedding plus ops, Proof, graph, SQL, and vector stores, retrieval payload), then documents per minute, gold-passage recall per retrieval mode, payload tokens, and the effect of stage order and worker count"
verdict: PENDING
related: [001, 002, 003, 005]
tags: [pipeline, stores, retrieval, workers]
---

# Spike 010: pipeline-order-end-to-end

## What This Validates

The pieces of the harness assembled once, end to end, so the order of the pieces and the rules for parallel workers are measured rather than argued. Pieces, in the owner's words: prompt, graph output, vector output, payload input to store, payload output to retrieve, parallel worker interaction. Read all three files in `.claude/skills/spike-findings-melodyscribe/references/` first; reuse spike 001's compiler and Proof and spike 003's student harness read-only through `sys.path`.

## Plan

Pipeline: chunker (one unit per document as in 003, plus a paragraph-split variant if documents have more than one paragraph) → Score with the v0.1 defaults → one pass on MiniCPM5-2B Q8: `⟦EMB⟧` state plus ops under the v0.2 grammar with spike 003's D0 instruction → Proof → stores: graph in networkx (nodes by normalised name, edges with evidence), SQL in sqlite (`facts` table: subject, attribute, value, value_type, quote, doc), vectors in Faiss (two indexes: the 2B `⟦EMB⟧` state and Qwen3-Embedding-0.6B, so the retrieval modes can be compared on both) → retrieval payload per `SCORE-IO-SPEC.md` recall-time I/O. Production targets Cozo, SQLite, and Faiss through Databasise; say so, do not build them here.

Retrieval modes on every query in `.planning/spikes/shared/queries-v1.json` and the two HotpotQA queries: vector-only (each index), graph-only (entity mention match, one-hop neighbourhood, documents by evidence), SQL-only (attribute lookup by subject), fused (vector top-k union graph neighbourhood union SQL facts, ranked by a stated rule). Metric: recall@1, @3, @10 of the gold document, payload tokens, latency.

Orderings to compare on identical inputs: one pass (embedding and ops from the same decode) versus two passes (embed, then ops); store writes streamed per op versus batched per document; entity merge at write time (normalised name) versus a post-pass revise that merges aliases. Workers W in 1, 2, 4, 8 as async tasks over one loaded model process (one model per process rule; workers never load their own model), with a write lock per store; record write conflicts, duplicate nodes, and documents per minute per W.

Pass conditions, stated before the run: the pipeline runs end to end on all 20 documents; fused recall@3 is at least vector-only recall@3 on the 0.6B index; the recommended order and worker rule are written to `results/pipeline-order.md` with the numbers; the parallel-worker interaction rules (idempotent op keys, merge rule, lock scope) are stated as requirements for the build.

Environment: `.venv`, `env.sh`, GPU lock on every model load, one model per process.

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
