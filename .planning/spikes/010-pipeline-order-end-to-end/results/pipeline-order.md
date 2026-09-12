# Spike 010: recommended pipeline order and worker rules

Measured on the 20-document parity corpus (`ac55d19e…`), MiniCPM5-2B-Q8_0
one-pass ingest, Qwen3-Embedding-0.6B-Q8_0, 118 queries (116 teacher
queries-v1 + 2 HotpotQA). Every number traces to `logs/`; the full tables
are `results/retrieval.json`, `results/stores_report.json`,
`results/passes.json`, `results/workers.json`, `results/workers_mock.json`.

## Head-to-head results

Ingest order, identical 20 whole-unit inputs (`results/passes.json`,
`logs/passes-20260912T173352Z.jsonl`):

| arm | wall (20 docs) | docs/min | emb cos 1v2 | ops identical | Proof |
|---|---|---|---|---|---|
| one-pass (1 load 0.85 s) | 161.4 s | 7.44 | — | — | 70 pass / 28 fail |
| two-pass (2 loads 1.67 s) | 161.4 s | 7.44 | 1.000 (min 0.9999999999999999) | 20/20 | 70 pass / 28 fail |

Fresh one-pass decodes are 20/20 byte-identical to spike 003's
`students/minicpm2b.json` (completion tokens 5399 = 5399) — third
independent reproduction of 003 determinism.

Store-write order, identical inputs (`results/stores_report.json`,
`logs/stores-20260912T173338Z.jsonl`): streamed vs batched checksums are
**equal** in all 6 variant pairs (e.g. STU-write `1bd50cb5b81e0958` both).
Write cost is ~0.1 ms total single-threaded — five orders of magnitude
below one op decode.

Entity merge (`results/stores_report.json`): write-time norm keys vs
post-pass revise. STU: 17 nodes either way, 0 aliases merged. SPL: 22
nodes either way, revise merges 1 alias pair. TEA: 34 nodes, 0 merged.
Retrieval is identical under write vs revise in all 6 pairs
(`results/retrieval.json`: graph/sql/fused numbers equal to 4 decimals),
because retrieval normalises names at query time anyway.

Chunker: whole-doc vs title/body split (`results/retrieval.json`):
vec06 whole r@3 **0.8856** vs vec06_split r@3 **0.6653** (r@1 0.6949 vs
0.4619; MRR 0.8014 vs 0.6007). Splitting one-paragraph docs into
title+body sections loses document-level recall on both indexes.
STU-split files more ops (110 pass vs 70) but graph/sql recall barely
moves (graph r@3 0.309 vs 0.284; sql 0.254 vs 0.220).

Retrieval modes, 118 queries (`results/retrieval.json`,
`logs/retrieval-20260912T173340Z.jsonl`):

| mode | r@1 | r@3 | r@10 | MRR | lat med |
|---|---|---|---|---|---|
| vec06 whole | 0.6949 | **0.8856** | 0.9915 | 0.8014 | faiss µs |
| vec2b whole | 0.1780 | 0.3517 | 0.6610 | 0.3226 | faiss µs |
| vec06 split | 0.4619 | 0.6653 | 0.8814 | 0.6007 | faiss µs |
| graph STU/SPL/TEA | 0.186/0.225/0.242 | 0.284/0.309/0.326 | 0.555/0.568/0.589 | 0.309/0.337/0.356 | 0.016–0.031 ms |
| sql STU/SPL/TEA | 0.102/0.140/0.153 | 0.220/0.254/0.246 | 0.517/0.551/0.555 | 0.240/0.273/0.279 | 0.016–0.034 ms |
| fused (any store set) | 0.6949 | **0.8686** | 0.9915 | ~0.798 | 0.005 ms |

Pass condition 2 **fails**: fused r@3 0.8686 < vec06 r@3 0.8856.
Mechanism (verified per query): the +0.15 graph/sql bonus lets a vec-#4
doc (0.25 + 0.15 = 0.40) leapfrog an unbonused vec-#3 (0.333). The two
flips are `janet_waldo#5` and `lord_high_treasurer#6`; both bumpers are
spurious subject-mention hits. Vec06 top-10 already contains the gold on
117/118 queries, so fusion has headroom of at most 1 rescue against a
measured downside of 2. Better teacher-filed stores do not change this:
fused is 0.8686 under STU, SPL, and TEA alike — the bonuses, not the
store contents, are the problem.

Payload per query (recall-list JSON + fenced top-3 blocks at 200 chars):
118.9–119.7 words mean, i.e. **203–205 MiniCPM tokens** at measured
fertility 1.71 tok/word (`payload_*` in `results/retrieval.json`).

Workers over one loaded 2B process, 6-doc subset
(`results/workers.json`, `logs/workers-20260912T172907Z.jsonl`):

| W | wall | docs/min | graph/sql/dups |
|---|---|---|---|
| 1 | 63.49 s | 5.67 | 17/3/2 |
| 2 | 67.59 s | 5.33 | 17/3/2 |
| 4 | 68.18 s | 5.28 | 17/3/2 |
| 8 | 71.08 s | 5.06 | 17/3/2 |

Outputs are identical at every W (same op counts, same 2 duplicate keys:
deterministic greedy decode + idempotent keys, zero write conflicts).
Throughput is flat-to-degrading: the model lock serialises everything and
threading adds ~12% overhead at W=8. Stub control (60 pseudo-units, 0.05 s
"decode", same locks: `results/workers_mock.json`): 3.017/3.016/3.019/3.023 s
— harness/lock overhead is ~nil; the GPU is the whole bottleneck.

HotpotQA spot checks: q1 both gold docs at vec ranks 1 and 3 (fused same);
q2 ranks 1 and 6 (fused same) — the rank-6 gold is outside every r@3.

## Recommendations for the build

1. **One loaded model process serves embed + ops** (one-pass at the
   process level). Two-pass buys nothing: identical vectors (cos 1.0),
   identical ops (20/20), identical Proof. The only delta is one reload
   (~0.8 s). Never pay a load per stage.
2. **File ops streamed** (per op, as Proof passes). Bit-identical to
   batched, bounds memory, fails narrow. Batching buys nothing here.
3. **Merge entities at write time by normalised name** (v0.1 default).
   The revise pass found ≤1 alias pair on 20 docs and changes no
   retrieval number; keep revise as a periodic job, not in the hot path.
4. **Chunk whole documents** for the durable index until a multi-paragraph
   corpus says otherwise. Title/body splitting cost 0.22 r@3 on the
   strong index and its extra ops did not pay back in graph/sql recall.
5. **W = 1 worker per model process.** More workers add overhead, never
   throughput, while one process owns the GPU. Scale by processes/GPUs
   (spike 009's question), not by threads. Keep the per-store write locks
   and idempotent op keys: they cost nothing (stub control flat) and the
   W sweep proves conflict-free determinism.
6. **Do not fuse with flat bonuses.** Fused r@3 < vec r@3 by 2 queries on
   118 with the stated rule, identically under student and teacher stores.
   Fusion needs rank-gated or score-calibrated rules (only bonus inside
   the vector top-k, or a trained ranker) — an open experiment, not a
   default. Ship vector-first ranking; graph/sql as backoff for queries
   the vector index misses (1/118 here).
7. **Keep the 0.6B embedder as the durable index.** vec2b r@3 0.3517 vs
   vec06 0.8856 on 118 queries replicates spike 004's gap (MRR 0.31 vs
   1.00) at 59x the query count. Untrained 2B states are not embeddings.

## Parallel-worker interaction rules (build requirements)

- One model per process; workers are asyncio tasks sharing the process
  through one model lock. Workers never load a model.
- One write lock per store (graph, sql, vector); op keys idempotent
  ((norm subject, norm predicate, norm value)) so retries and duplicate
  deliveries collapse — measured: identical stores at W=1..8.
- Proof rejects never block the section embedding (spec §6); measured
  dup/conflict counts are reported per W run (here: 0 conflicts).
- Store checksums per run; streamed and batched must hash equal
  (regression gate for the filing path).
