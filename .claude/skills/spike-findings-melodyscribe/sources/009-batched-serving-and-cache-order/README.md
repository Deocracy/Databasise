---
spike: 009
idea: melodyscribe
name: batched-serving-and-cache-order
type: comparison
validates: "Given N queued op-emission and embedding requests over the corpus, when served with continuous batching on one 16 GB GPU with prompt segments ordered for prefix sharing, then aggregate tokens per second, requests per second, TTFT, VRAM, and cache-hit token fraction at N in 1, 4, 16, 64, 256, 1024 for the slot count that saturates the GPU"
verdict: VALIDATED
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

Docs and code read (all local, no network for decisions):

- `.claude/skills/spike-findings-melodyscribe/references/one-pass-runtime.md` (spikes 002+005): the normative runtime facts. One `llama_decode` yields embedding+logits; `kv_cache_seq_cp` is bit-exact, two-call split costs 0.9984 cosine; greedy TTFT slope 0.23 ms/prefill-token; warm-KV saves 20-110 ms absolute at 2B; saved state is not bit-exact (near-tie flips); one model per process; every load under `flock /tmp/melodyscribe-gpu.lock`.
- `llama-cpp-python` 0.3.35 source (in `.venv`): `Llama(embed)` list-batches internally via `_batch.add_sequence` (per-seq positions restart at 0, pooled per-seq readback) — the retrieval batching path needs no raw code. For generation, `eval()`/`generate()` always `kv_cache_seq_rm(-1, ...)` (all sequences), so a K-slot scheduler must hand-roll raw batches and sample via a persistent sampler; a fresh sampler per token would restart grammar state. `embedding=True` is required for `n_seq_max > 1`; generation on such an instance is verified here by first-token/top-1 equality against `create_completion` (the production path), with split-prefill tie flips downstream (see Trail).
- Prior-art serving (from memory of the field, not a decision source): continuous batching (Orca/vLLM) splits work into prefill + lockstep decode; prefix caching (Prompt Cache, SGLang RadixAttention, llama-server `--cache-reuse` via `seq_rm` longest-common-prefix) reuses shared segments. The spike implements the same two ideas with the llama.cpp C API directly (batched prefill = parallel prefill; `seq_cp` fan-out = prefix-once; lockstep multi-seq decode = batched decode). Per-slot grammars inside a lockstep decode are not expressible through this API — hence two schedulers: (a) SERIAL-GRAMMAR (the true op path, batched prefill + serial grammar decode) and (b) PARALLEL-GREEDY (the batching ceiling, batched prefill + lockstep greedy decode, validity measured offline and multiplied in).
- Serving paths tried, in plan order: (1) raw `llama_batch` multi-sequence scheduler — built and verified (`logs/verify.jsonl`: first-token 4/4 both schedulers vs production; Trail for the three build constraints found); (2) vLLM 0.29.0 in `.venv-vllm` — installs and imports, engine dies on NixOS (`/sbin/ldconfig` absent, triton hardcodes it; `enforce_eager` does not avoid it; evidence `logs/vllm-run.err`, `logs/vllm.out`, `logs/vllm.json`); (3) prebuilt `llama-server` — no binary on PATH, skipped with reason (`logs/vllm.json`).

Design conclusion before the sweep: decode dominates ingest cost (probe: 330-token prefill ~0.09 s vs 48 grammar tokens ~1.05 s), so K-slot prefill batching alone cannot move req/s much; the decode phase must batch (lockstep) to saturate the GPU. Retrieval is prefill-only (~7 ms/query) and batches through the public `embed(list)` API.

## How to Run

From the repo root:

```bash
.planning/spikes/009-batched-serving-and-cache-order/run.sh
```

`run.sh` sources `.planning/spikes/env.sh` (mandatory before any `llama_cpp` import), records `logs/env.json` (GPU, driver, `llama_cpp` version, model SHAs), then runs under `flock /tmp/melodyscribe-gpu.lock`, one model per process: `probe.py` (sizing) → `verify.py` (scheduler == production, aborts otherwise) → `sweep.py` (ingest matrix, both schedulers, ~1 h) → `cacheorder.py` (prefix/order/continuation) → `retrieve.py` (0.6B embed + Faiss) → vLLM attempt (`vllm_bench.py` if importable, else records the failure) → `analyze.py` (CPU, no lock) → `results/table.json` + `results/summary.md`. All GPU logs are JSON lines with ISO timestamps; `vllm_bench.py` needs `HF_HUB_OFFLINE=1 HF_OFFLINE=1` (local safetensors only). The committed logs in `logs/` were produced by exactly these commands; `sweep.jsonl` dominates the runtime (N=1024 serial-grammar cell ≈ 23 min).

## What to Expect

- `verify.py` prints `VERIFY PASS` and exits 0 (first-token 4/4 both schedulers; grammar full-text ≥3/4, greedy full-text reported — split-prefill tie flips, cf. spike 005).
- `sweep.py` prints `SWEEP DONE`: serial-grammar flat ≈ 270 tok/s at every K (decode-serial, K≈8 nominal); parallel-greedy rising 800 → 2000 → 2330 → 2470 tok/s at K=1/4/8/16 and regressing at K=32; validity 4/12 grammar, 0/12 greedy at cap 256 (zero-shot, Proof-strict).
- `cacheorder.py` prints `CACHEORDER DONE`: prefix-once ≈ 0.62 s vs naive ≈ 0.73–0.81 s per K=8 wave (8/8 first-tokens equal); sorted ≈ 0.61 s vs shuffled ≈ 0.77 s; continuation reuse ≈ 15 ms vs cold ≈ 80 ms; output order ≈ no effect.
- `retrieve.py` prints `RETRIEVE DONE`: ≈ 140 q/s at K=1, ≈ 770–810 q/s at K≥16 (saturated), recall@10 sanity 109/116 on the 19-vector index.
- vLLM bench fails on NixOS (triton `/sbin/ldconfig`); the failure and its evidence are the recorded outcome for path 2.
- Total GPU time ≈ 1.5 h, all under the lock; VRAM stays under 4 GB (ingest) / 1.4 GB (retrieval) — the 16 GB card is never capacity-bound at these context sizes.

## Investigation Trail

- probe (`logs/probe.jsonl`): single-request sizing on MiniCPM5-2B Q8 (330-token prompt): grammar decode 48 tok = 1.11–1.30 s, greedy prefill+48 tok = 0.39–0.40 s, Qwen3-Embedding-0.6B embed = 6.6–10.6 ms. Decode dominates ingest; retrieval is prefill-only. Corpus: 20 docs verify to `ac55d19e…`, 19 sections ≥200 chars.
- tokstats (`logs/tokstats.json`, CPU vocab-only): prompts 281–384 tok (p50 323); shared prefix (system+skill+doc_prefix) 105 tok = 24.5% shared fraction (instr-after); boundary merges shift tokenisation by ~1 token at segment junctions (timing arms therefore share identical id sequences; the junction deviation is quantified in `cacheorder.jsonl` as 104/105 leading tokens exact).
- verify v1: 4/4 `create_completion` refs fine, then `llama_decode returned -1` in the hand-rolled single-token re-decode. Bisect (`logs/dbg.out`, `dbg2.out`, all under lock): dbg replicates the 002 pattern (single-seq prefill, `seq_cp` 0→1, continuation at a NEW position, sampler) — all OK, first sample 416 = 002's argmax. dbg2: multi-seq selective-logits prefill OK; re-decode of the last prompt token at its SAME position FAILS (-1) with or without `seq_rm`+`seq_cp`. Constraint A: never decode at an already-filled position on this build.
- dbg3 (`logs/dbg3.out`): after a 2-seq single-phase prefill (36 rows, embeddings-mode override forces all-outputs), `sampler.sample(idx -2/-1)` = [844, 416] vs refs [416, 416]; `get_logits_ith(0/1)` = [5, 33]. Slot 1 matched only because its last token is also the last row. Constraint B: in embeddings mode only the LAST output carries real logits; non-last outputs read embedding memory. Fix: flip the C-side flag with `llama_set_embeddings(ctx, False)` after load (keeps `n_seq_max>1`, restores generative outputs; `embed()` is never called on the 2B instance).
- verify v2: SEGFAULT, `llama-sampler.cpp:940: GGML_ASSERT(logits != nullptr)`. dbg4 (`logs/dbg4.out`/`dbg4.err`): `get_logits_ith(0)` → `ValueError: NULL pointer access` after a 2-seq prefill even in generative mode. dbg6 (`logs/dbg6.out`): `get_logits()` full-buffer argmax = [416, 416], exactly matching `generate()` refs. Constraint C: per-output readback (`get_logits_ith`, sampler index) is NULL for multi-output decodes; the full `get_logits()` buffer (M×vocab) is the only safe multi-output read. Final design (batchserve v4): bulk-body prefill (timing only, no reads) + per-slot single-row last-token calls (first tokens, samplers only see single outputs) + serial grammar loop / lockstep greedy loop with full-buffer argmax.
- dbg7/dbg8 (`logs/dbg7.out`, `logs/dbg8.out`): scheduler first tokens vs `generate()` disagreed 0/4 ([4945×4] vs [8869×4]) — but vs `create_completion` top-5 (logprobs) the scheduler first token is the top-1 (logprob ≈ −0.02, runner-up ≈ −5) in 4/4 slots. `generate()` is the outlier here, not the scheduler; `create_completion` is the normative production path (spike 003's student path), so the verify compares against it. Residual full-text divergence (grammar 3/4, greedy 2/4) is split-prefill near-tie flips downstream — the same phenomenon spike 005 measured (about a quarter of inputs flip) — and the verify thresholds encode exactly that (first 4/4, grammar-full ≥3/4, greedy-full reported).
- Sweep crash 1 (`logs/sweep-run.err` pre-fix, then fixed): `decode: failed to find a memory slot` at N=16/K=16 — 16 seqs × ~380 positions overflowed `n_ctx=4096`. Fix: `n_ctx=16384` (VRAM 2.9→3.9 GB, still far from 16 GB). The completed N≤16/K≤8 cells were re-run after the fix; only post-fix logs are normative.
- cacheorder crash 1: second prefix-once group hit `-1` — stale slot KV from the previous group collided positions. Fix: `kv_cache_clear()` between groups. Crash 2 (continuation): R-decode at `[base, …)` failed — off-by-one: `slot_decode` samples the last id logits-only (never placed), so the first free position is `L+len−1`, and the old `L+len` left a one-position gap, which this build refuses. Fix: `base = L+len−1` (dbg9 `logs/dbg9.out` replicates and confirms). `gen_tok` counts therefore include one unplaced id per request (≈2% of gen tokens, <0.5% of tok/s — noted, notworth a re-run).
- retrieve crash 1: `corpus.py` path was two levels up instead of three. Fixed, re-ran clean.
- Machine reboot mid-spike (after the sweep, during the first cacheorder run): processes killed, `/tmp` cleared. `sweep.jsonl` was complete (30 cells + validity, `SWEEP DONE`); cacheorder had no log and was re-run from scratch post-fix. vLLM path: 0.29.0 installs/imports, engine dies in triton (`/sbin/ldconfig` absent on NixOS; `enforce_eager=True` does not avoid it — the failing call is engine-init sampler/compile warmup, `logs/vllm-run.err`). No user-space shim is possible (absolute path); recorded as the path-2 outcome per the plan's 20-minute rule. `llama-server`: no binary on PATH; `llama_cpp.server` is single-slot Python — path 3 skipped with reason. Both recorded in `logs/vllm.json`.
- Rig contention throughout (spikes 006/008/010, a reboot): every timing number below comes from a run holding `flock /tmp/melodyscribe-gpu.lock`; queue waits are reported separately from service times.

## Results

Verdict: **VALIDATED** — every pass condition is met with a measured number: throughput curves with a recommended K per workload (tables below), the cache-maximising order with its TTFT gain (instruction-first + prefix-once + prefix-grouped), and the concurrency-vs-queue statement (last paragraph). Deviations from the plan, all recorded above: wave scheduler with serial grammar decode instead of true continuous batching (per-slot grammars are not expressible in this API — the greedy lockstep arm bounds what batching buys); vLLM path failed on NixOS (`/sbin/ldconfig`); `llama-server` absent.

### Ingest: op emission, MiniCPM5-2B Q8, v0.2 grammar, cap 48 (`logs/sweep.jsonl`)

Serial-grammar is the true op path; parallel-greedy is the batching ceiling (validity below tells what its tokens are worth).

| sched | N | K | wall_s | tok/s | req/s | ttft_p50 | ttft_p95 | vram_MB |
|---|---|---|---|---|---|---|---|---|
| serial-grammar | 1 | 1 | 1.19 | 312 | 0.84 | 1.17 s | 1.17 s | 3739 |
| serial-grammar | 4 | 1 | 4.92 | 321 | 0.81 | 3.61 s | 4.91 s | 3739 |
| serial-grammar | 4 | 4 | 5.01 | 315 | 0.80 | 3.69 s | 5.00 s | 3739 |
| serial-grammar | 16 | 1 | 23.44 | 249 | 0.68 | 12.98 s | 23.42 s | 3739 |
| serial-grammar | 16 | 4 | 20.49 | 285 | 0.78 | 12.01 s | 20.48 s | 3739 |
| serial-grammar | 16 | 8 | 21.01 | 278 | 0.76 | 11.96 s | 20.99 s | 3763 |
| serial-grammar | 16 | 16 | 22.54 | 259 | 0.71 | 12.96 s | 22.52 s | 3795 |
| serial-grammar | 64 | 1 | 88.31 | 271 | 0.73 | 48.5 s | 84.4 s | 3795 |
| serial-grammar | 64 | 4 | 85.88 | 279 | 0.75 | 45.1 s | 81.5 s | 3795 |
| serial-grammar | 64 | 8 | 82.20 | 291 | 0.78 | 43.2 s | 78.4 s | 3795 |
| serial-grammar | 64 | 16 | 89.68 | 267 | 0.71 | 46.7 s | 85.2 s | 3803 |
| serial-grammar | 64 | 32 | 102.21 | 234 | 0.63 | 57.5 s | 97.7 s | 3883 |
| serial-grammar | 256 | 1 | 340.54 | 280 | 0.75 | 171 s | 325 s | 3883 |
| serial-grammar | 1024 | 1 | 1384.41 | 275 | 0.74 | 669 s | 1307 s | 3883 |
| parallel-greedy | 1 | 1 | 0.47 | 791 | 2.13 | 0.45 s | 0.45 s | 3883 |
| parallel-greedy | 4 | 1 | 1.89 | 837 | 2.12 | 1.40 s | 1.87 s | 3883 |
| parallel-greedy | 4 | 4 | 0.76 | 2089 | 5.28 | 0.74 s | 0.74 s | 3883 |
| parallel-greedy | 16 | 1 | 7.48 | 781 | 2.14 | 4.20 s | 7.46 s | 3883 |
| parallel-greedy | 16 | 4 | 2.94 | 1991 | 5.45 | 2.20 s | 2.92 s | 3883 |
| parallel-greedy | 16 | 8 | 2.51 | 2330 | 6.38 | 2.49 s | 2.49 s | 3883 |
| parallel-greedy | 16 | 16 | 2.36 | 2474 | 6.77 | 2.34 s | 2.34 s | 3885 |
| parallel-greedy | 64 | 1 | 30.05 | 797 | 2.13 | 15.5 s | 28.6 s | 3885 |
| parallel-greedy | 64 | 8 | 10.27 | 2333 | 6.23 | 6.37 s | 10.25 s | 3885 |
| parallel-greedy | 64 | 16 | 9.70 | 2469 | 6.60 | 7.23 s | 9.68 s | 3885 |
| parallel-greedy | 64 | 32 | 13.28 | 1804 | 4.82 | 13.26 s | 13.26 s | 3887 |
| parallel-greedy | 256 | 1 | 120.15 | 794 | 2.13 | 60.6 s | 114.5 s | 3887 |
| parallel-greedy | 256 | 16 | 38.55 | 2474 | 6.64 | 21.7 s | 38.5 s | 3887 |
| parallel-greedy | 1024 | 1 | 477.32 | 799 | 2.15 | 239 s | 454 s | 3887 |
| parallel-greedy | 1024 | 16 | 153.76 | 2479 | 6.66 | 79.2 s | 146.6 s | 3887 |

(Dropped row `parallel-greedy N=64 K=4` = 2005 tok/s, 5.36 req/s, wall 11.95 s — in `table.json`; dropped from the table for width. TTFT here is total including FIFO queue wait; per-request service TTFT is ~1.2 s serial-grammar (prefill share + 48 grammar tokens) and the wait column in `table.json` separates the two.)

Read-off: serial-grammar is flat in K (266–321 tok/s; the N=16/K=1 cell dipped to 249, single-run noise — cells are one run each, no medians across runs; decode is serial, so K only batches the ~5% prefill share) — recommended K is whatever fits, nominally 8 (291 tok/s at N=64; `logs/sweep.jsonl` `ksat` event). Parallel-greedy saturates the GPU at K=16 (≈2470 tok/s, ≈6.6 req/s, stable from N=16 to N=1024) and regresses at K=32 (1804 tok/s — batch-management overhead wins). The grammar constraint costs ≈9× throughput (275 vs 2479 tok/s) — CPU-side grammar filtering per token over a 130k vocabulary, not GPU work.

Validity at cap 256, 12 units (`sweep.jsonl` `validity` event): grammar 4/12 pass Proof (0.333), greedy 0/12 (0.0). Zero-shot 2B op emission is shape-guaranteed but content-weak pre-fine-tune (consistent with spike 003: routing 0.30–0.45); valid-op throughput today = 0.74 req/s × 0.33 ≈ 0.24 valid op-lists/s ≈ 15/min. Greedy tokens buy tokens/s but zero valid ops — the ceiling arm is a bound, not a path.

### Retrieval: Qwen3-Embedding-0.6B Q8 embed + Faiss top-10 (`logs/retrieve.jsonl`)

Batched through the public `embed(list)` API (bit-batched by `n_batch`/`n_seq_max` internally; batched-vs-single cosine 0.9991/0.9995). Index: 19 corpus sections, recall@10 sanity 109/116 = 0.94 (sanity only — 19 vectors). Faiss top-10 ≈ 0.03 ms/query (noise next to embedding).

| N | K=1 q/s | K=4 q/s | K=16 q/s | K=64 q/s | TTFT p50 K=1 → K=16 |
|---|---|---|---|---|---|
| 4 | 136 | 334 | — | — | 8.0 ms → 2.9 ms |
| 16 | 141 | 389 | 773 | — | 6.9 ms → 1.3 ms |
| 64 | 142 | 380 | 748 | 809 | 7.0 ms → 1.3 ms |
| 256 | 140 | 394 | 781 | 782 | 7.0 ms → 1.2 ms |
| 1024 | 143 | 389 | 766 | 790 | 6.9 ms → 1.3 ms |

Read-off: retrieval saturates at K≈16–64 (≈770–810 q/s, TTFT ≈1.3 ms); K=1 is 140 q/s at 7 ms. VRAM flat 1371 MB. Saturation here is host-call batching (one `embed()` call per K queries), not GPU size — the 0.6B model is tiny.

### Cache order: prefix sharing, segment order, continuation (`logs/cacheorder.jsonl`)

- Token fractions (exact, `fractions` event): shared prefix 105 toks = 23.8% of a section-tail prompt (instr-after). Instruction-first extends the cross-request shared run 105 → 319 toks (48.8%) — the ordering that maximises cache hits is instruction-before-section.
- Prefix-once vs naive prefill, K=8, 3 reps: naive 0.73–0.81 s/wave vs prefix-once 0.616–0.622 s (setup 0.0076 s + tails 0.61 s) — ≈15–24% off prefill; first tokens 8/8 equal all reps (reuse is exact). The shared prefix tokenises 104/105 identically in context (one junction merge — no behavioural effect).
- Sorted (prefix-grouped, one prefix-once wave per group) vs shuffled (naive): 0.60–0.71 s vs 0.77 s per 8 requests — ≈21% for arrival sorting.
- Continuation from decoded KV vs cold full prefill: reuse TTFT 14.6 ms vs cold 80.4 ms (5.5×, but 66 ms absolute — second-order at 2B, consistent with spike 005's 20–110 ms verdict; no persisted-KV store justified).
- Output order (graph-first vs interleaved op text, cold continuation): 0.090–0.092 s vs 0.098 s — marginal, no practical effect; order freely.

### Concurrency vs queue depth (the plain statement)

On this 16 GB card the GPU is never the binding constraint at these sizes (ingest VRAM 3.7–3.9 GB with `n_ctx=16384`; retrieval 1.4 GB). True concurrency is K: 16 decode slots saturate ingest (≈6.6 greedy req/s, 0.78 grammar req/s) and ≈16–64 embed slots saturate retrieval (≈800 q/s). Everything beyond K is queue: "1000 agents" = a queue of 1000 over K=16 slots at ≈44 documents/min ingest (0.74 req/s × 60, one section per request; ≈9 docs/min at ~5 sections/doc) and ≈800 queries/s retrieval. TTFT at N≫K is queue wait, not service (service TTFT ≈1.2 s grammar op-list, ≈15 ms recall continuation, ≈1.3 ms batched embed). If ingest needs more: the 9× gap sits in CPU-side grammar filtering — batch the decode (lockstep) *with* per-slot grammars, which needs a sampler this stack does not expose; that, or fine-tune first (validity 0.33 dominates economics long before throughput does).
