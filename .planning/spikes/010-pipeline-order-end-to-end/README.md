---
spike: 010
idea: melodyscribe
name: pipeline-order-end-to-end
type: standard
validates: "Given the 20-document corpus, the shared query set, and the HotpotQA queries, when the harness runs end to end with W parallel workers (chunker, Score, one pass embedding plus ops, Proof, graph, SQL, and vector stores, retrieval payload), then documents per minute, gold-passage recall per retrieval mode, payload tokens, and the effect of stage order and worker count"
verdict: PARTIAL
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

Settled inputs reused read-only (never re-measured, never re-implemented):

- `.claude/skills/spike-findings-melodyscribe/SKILL.md` plus all three
  references (`score-io-contract.md`, `one-pass-runtime.md`,
  `model-size-and-training.md`): Score I/O contract, one-pass runtime
  recipe, size/embedding verdicts.
- Spike 001 (`score.py`, `ops_validate.py`, `grammar.py`): Score compiler
  and Proof, imported read-only via `sys.path` (`s10_common.py`).
- Spike 003 (`common.py` D0 `INSTRUCTION`, `student.py` decode recipe,
  `v02_grammar.py`, `resolve.py`, `teacher.json` ceiling labels):
  student prompt bytes, greedy raw-completion decode
  (temperature 0, seed 1234, cap 1024, file=graph,sql), quote resolution.
- Spike 004 (`arm_embed.py`, `common.py`): embedding recipes verbatim —
  2B `⟦EMB⟧` marker appended with pooling LAST (`armB_docs` line in
  004's `run.sh`); Qwen3-Embedding-0.6B native pooling, no prefix, no
  marker (`armA_docs` line).
- Spike 002: one `Llama(embedding=True)` instance serves generate and
  embed (`dual_use`); tokenise prefix+section as one string; never
  prepend BOS for MiniCPM5.
- Spike 005: `llm.eval` + `generate(reset=False)` continuation pattern
  inspected and deliberately NOT used — grammar-constrained continuation
  through the high-level API is unmeasured, so one-pass here means one
  load / one shared process (embed then grammar decode per section),
  two-pass means two loads (embed process + decode process). The
  comparison isolates the reload cost, honestly stated.

Deviations from the spike brief, with reasons (all stated in Results):

- Graph store is stdlib dicts, not networkx: networkx is absent from
  `.planning/spikes/.venv` and the brief's own CONVENTIONS say standard
  library where possible. Node/edge semantics are exactly the brief's
  (nodes by normalised name, edges with evidence). Production target
  stays Cozo through Databasise — not built here, as briefed.
- Payload tokens = whitespace words x measured MiniCPM fertility
  (no model-tokenizer call on CPU; fertility measured from 003's
  `students/minicpm2b.json` prompt_tokens against the same prompt bytes).
- Worker sweep runs on a fixed 6-document subset (indices 0,3,7,11,15,19)
  to bound GPU time; the model serialises workers by construction, so
  the subset measures the scaling shape, not absolute throughput. A
  CPU stub control (`cpu_workers_mock.py`, 60 pseudo-units) isolates
  harness overhead from GPU serialisation.

## How to Run

```bash
source .planning/spikes/env.sh
bash .planning/spikes/010-pipeline-order-end-to-end/run.sh
```

`run.sh` reproduces everything from scratch: (0) Score compile check on
20 docs x {whole, split} (CPU); (1) 2B one-pass whole + query embeds,
(2) 2B two-pass embed-only and decode-only, (3) 2B one-pass split,
(4) 0.6B embeds, (5) worker sweep W=1,2,4,8 — each GPU step in its own
process under `flock /tmp/melodyscribe-gpu.lock`, one model per process;
(6) stores (CPU: streamed/batched x write/revise x STU/SPL/TEA + Faiss);
(7) retrieval eval (CPU); (8) stub-worker control (CPU);
(9) one-pass vs two-pass comparison (CPU). Logs are JSON lines with ISO
timestamps in `logs/`; tables in `results/`; the order/worker
recommendation in `results/pipeline-order.md`.

## What to Expect

About 16 minutes of GPU (6 lock acquisitions: 2B whole one-pass ~160 s,
two-pass pair ~165 s, 2B split one-pass ~340 s incl. 118 query embeds,
0.6B embeds ~60 s, worker sweep ~270 s) plus queue time behind sibling
spikes sharing `/tmp/melodyscribe-gpu.lock`; everything else is CPU
seconds. Expected shape of the numbers: one-pass and two-pass identical
outputs with wall differing by one model reload (~0.8 s); streamed and
batched store checksums equal; write-merge and revise-merge equal
retrieval; vec06 r@3 near 0.89 with fused at or microscopically below it
(the +0.15 bonus lets a vec-#4 doc leapfrog an unbonused vec-#3 — read
`results/pipeline-order.md` before "fixing" the fusion rule, the flips
are diagnosed there); workers flat-to-degrading in docs/min with
identical outputs at every W.

## Investigation Trail

1. Pre-reboot build (2026-09-12 ~15:30Z): wrote `s10_common.py`,
   `gpu_ingest.py`, `gpu_workers.py`, `build_stores.py`, `retrieve.py`,
   `cpu_workers_mock.py`, `score_check.py`, `compare_passes.py`,
   `run.sh`. `score_check.py` passed: 40 Scores compile, I1 spot check
   holds (`logs/score-check-20260912T153718Z.jsonl`). Teacher-label smoke
   of the store builder: TEA 34 nodes / 121 edges / 83 rows; revise merged
   0 aliases (teacher subjects already consistent). Machine rebooted
   mid-smoke; `/tmp` cleared, spike folder intact.
2. Post-reboot: 2-unit GPU smoke timed out at 10 min with empty logs and
   no `vectors/` dir. `/proc` scan showed the lock held by spike 008's
   `student8.py` (PID 97785) with 007 queued — the wait was correct
   queueing, not a hang. Launched `run.sh` detached (`setsid nohup`,
   queued behind 008/007) and polled.
3. Fertility correction before any measurement: MiniCPM tokens per prompt
   word on the exact D0 bytes = 6736/3930 = **1.71** (003
   `students/minicpm2b.json` vs `student_prompt` words), not the 1.32
   placeholder drafted in `retrieve.py`. Fixed before `retrieve.py` ran.
4. First results: one-pass vs two-pass identical (emb cos 1.0, ops 20/20
   identical, Proof 70/28 both); fresh decodes 20/20 byte-identical to
   003's `minicpm2b.json` (5399 = 5399 completion tokens). Workers
   flat-to-degrading with identical outputs. All in `logs/`, see Results.
5. Fusion surprise followed, not assumed: fused r@3 0.8686 < vec06 r@3
   0.8856. Per-query forensics named the 2 flips (`janet_waldo#5`,
   `lord_high_treasurer#6`), the leapfrog arithmetic (0.25+0.15 > 0.333),
   and the headroom (vec top-10 holds gold on 117/118). Train/test split
   checked: no split effect (vec r@3 0.895/0.867). HotpotQA: q1 fully
   retrieved @3 by vec alone (ranks 1,3); q2 half (1,6).

## Results

Verdict: **PARTIAL**. The pipeline runs end to end on all 20 documents
and every ordering/worker question is answered with numbers, but pass
condition 2 (fused r@3 >= vec06 r@3) fails with a diagnosed mechanism, so
the fusion rule this spike stated is not shippable.

Sub-claims (all numbers in `results/`, all runs in `logs/`):

- E2E ingest→Proof→stores→retrieval on 20/20 docs: VALIDATED
  (`vectors/whole_onepass.json`, `logs/gpu-whole-20260912T162740Z.jsonl`).
- One-pass vs two-pass: no quality or throughput difference beyond one
  reload (~0.8 s on 161 s): VALIDATED (`results/passes.json`).
- Streamed vs batched writes: bit-identical stores: VALIDATED
  (`results/stores_report.json` checksums).
- Write-merge vs revise-merge: identical retrieval, ≤1 alias pair merged:
  VALIDATED (`results/stores_report.json`, `results/retrieval.json`).
- Whole-doc chunking beats title/body split on the vector index
  (r@3 0.8856 vs 0.6653): VALIDATED (`results/retrieval.json`).
- Fused r@3 >= vec06 r@3: INVALIDATED (0.8686 < 0.8856, 2 flips,
  mechanism in `results/pipeline-order.md`).
- W=1 per model process; per-store locks + idempotent keys give
  conflict-free determinism: VALIDATED (`results/workers.json`,
  `results/workers_mock.json`).
- 0.6B embedder stays the durable index (vec r@3 0.8856 vs 2B 0.3517 on
  118 queries): VALIDATED, replicates 004 at 59x queries.

Owner re-run (2026-09-12): `run.sh` re-run end to end under the GPU lock; all 139 retrieval and store
numbers in `results/retrieval.json` and `results/stores_report.json` equal, ops and vectors reproduced,
only wall-clock fields in `passes.json` and `workers.json` differ (within a few percent).

Payload: 118.9–119.7 words/query mean (203–205 MiniCPM tokens at 1.71
fertility); retrieval latency median 0.005–0.034 ms/mode (CPU).
Recommendation and worker rules: `results/pipeline-order.md`.
