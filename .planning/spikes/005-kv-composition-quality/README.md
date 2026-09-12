---
spike: 005
idea: melodyscribe
name: kv-composition-quality
type: standard
validates: "Given a retrieved set, when composed as isolated KV modules versus full prefill versus shift reuse, then answer quality and TTFT per method"
verdict: PARTIAL
related: []
tags: [kv, cacheblend, ttft]
---

# Spike 005: kv-composition-quality

## What This Validates

Given a retrieved set, when composed as isolated KV modules versus full prefill
versus shift reuse, then answer quality and TTFT per method. Model:
MiniCPM5-2B-Q8_0.gguf on legion CUDA via llama-cpp-python 0.3.35
(`n_gpu_layers=-1`, `n_ctx=8192`), greedy decode (`top_k=1`), 3 reps per cell,
2 HotpotQA queries x 10 retrieved-set variants, identical final token strings
per row (asserted: ctx tokens are a byte-prefix of full tokens in every row).

Arms (see Research for the mapping to the literature forms):

- `full`: cold joint prefill of all chunk tokens + question, then decode.
- `warm`: chunk KV prebuilt once (`eval` + `save_state`), per query
  `load_state` + question-only prefill + decode. This is the TTFT of the
  isolated-module warm state (chunk tokens never re-prefilled); the KV itself
  was built jointly, so it is a warm-reuse proxy, NOT a neighbor-blind build.
- `shift`: a differently-suffixed prompt sharing `CTX_PREFIX` + first paragraph
  populates the KV, then the real prompt reuses the longest-common-prefix KV
  through llama-cpp-python's `kv_cache_seq_rm` path (= llama-server
  `--cache-reuse` / `n_cache_reuse` "KV shifting" semantics).

## Research

Docs checked: `score-format-and-cache.md` section 4 (the 1A/1X2 table: shift
reuse is approximate, isolation is exact-but-blind, isolation+repair is
CacheBlend), `runtime-one-pass.md` (one prefill yields states + logits),
`efficiency-design.md` section 3 (KV modules are second-order at 2B: ~43 KB KV
per token in bf16 vs tens of ms to recompute; "measure TTFT with and without
composition before building anything" — this spike is that measurement).

Approaches compared: (a) true per-module build with `llama_memory_seq_cp` /
`seq_add` through raw ctypes batches — rejected: the high-level `Llama` class
owns model/context/sampler setup and has no multi-sequence API; driving raw
`llama_model` + `llama_context` + manual `llama_batch` with `seq_id` arrays is
~200 lines of ctypes for this verdict. (b) Chosen: high-level `generate` /
`eval` / `save_state` / `load_state` + the built-in prefix-match reuse in
`generate(reset=True)`. This measures exactly what the rig decision needs:
query-time TTFT with prebuilt KV vs without, and whether reuse paths change
answers. Quality of a TRUE neighbor-blind build is bounded, not measured:
order-swap rows (AB vs BA) quantify cross-chunk attention dependence.

## How to Run

```bash
bash .planning/spikes/005-kv-composition-quality/run.sh
```

`run.sh` sources `.planning/spikes/env.sh` (mandatory before importing
`llama_cpp`), runs `kv_arms.py` once under `flock
/tmp/melodyscribe-gpu.lock` (single GPU process, all reps inside), then runs
`analyze.py` without the lock. Logs: `logs/run.jsonl` (254 JSON lines, ISO
timestamps, one object per event), `logs/stderr.log`. Results:
`results/table.json`, `results/summary.md`. Re-run overwrites logs/results.
No network, no teacher API, no project deps (stdlib corpus loader mirrors
`databasise/parity/corpus.py` checks: per-doc sha256 + corpus hash, refuses
drift). GPU time ~5 min.

## What to Expect

- Head-to-head table (20 rows): `full` TTFT 15–126 ms at 31–692 prompt tokens;
  `warm` TTFT flat ~13–15 ms (2.4–8.5x relative win, 20–110 ms absolute);
  `shift` TTFT 0.9–1.2x of full (no win: only the shared prefix is skipped,
  the suffix dominates).
- TTFT fit: full 0.23 ms/prefill-token, warm 0.0007 ms/token + 13 ms
  question/decode floor. Sweep points (tokens, full TTFT): (650, 119 ms),
  (1192, 229 ms), (2093, 449 ms); warm 13.5/13.8/14.5 ms.
- Quality: per-arm correctness equal in 14/20 rows; the 6 differing rows flip
  in BOTH directions and always late in generation (first divergence at
  char 53–332 of ~300, i.e. single near-tie tokens like are/were) — noise from
  state round-trips, not a method signal. Order swap never changes correctness.
- q1 is confounded by parametric memory (empty/distractor-only score "correct");
  q2 is the discriminating query (needs both hops; single-doc and 5-distractor
  variants fail on ALL arms). Verdict PARTIAL: TTFT per method is solid;
  quality comparison is bounded by one discriminating query and a proxy
  isolation arm.

## Investigation Trail

1. Smoke test (GPU lock): plain `Context:/Question:/Answer:` prompt, MiniCPM5-2B
   answers both queries correctly; full prefill + 24-token gen ~0.21 s at
   ~150–200 tokens. Format works, proceed.
2. Low-level API probe: `llama_memory_seq_cp` / `seq_add` / `seq_rm` and
   multi-`seq_id` batches exist in 0.3.35, but `Llama` exposes no sequences;
   chose high-level `eval` + `save_state`/`load_state` + built-in prefix reuse.
   Recorded the isolation-proxy limitation in the arm definition.
3. Iteration 1 (`Q:/A:` format, `[i] Title:` blocks, 24 tokens): q2 fails 10/10 —
   the model echoes `[N] Title:` blocks (budget eaten) and asks itself
   follow-up questions (`Q:` triggers self-questioning). Warm/shift texts differ
   from full in 6/20 rows despite identical tokens. Two surprises to chase.
4. Iteration 2 (plain `Title/text` blocks, anti-copy instruction, 64 tokens):
   echo gone; q2 still self-questions under `Q:/A:`. Partition probe added
   (same tokens, eval split at 3 positions vs one-shot): ALL IDENTICAL —
   batch-partition numerics hypothesis REFUTED.
5. Iteration 3 (`Question:/Answer:` wording): q2 gold variants pass on all arms.
   State-path diagnostics on q1 gold-AB: exact-repeat-no-reset SAME,
   warm-without-save/load SAME, warm-with-save/load SAME — so the round-trip
   paths are deterministic per input, yet flip near-tie tokens on ~25% of other
   inputs (both directions). Conclusion: serialization/`seq_rm` reuse perturbs
   logits at tie positions only; below the quality-signal floor at this scale.
6. Metric audit: q1 `empty`/`distr-only` "correct" = model recites nationalities
   from memory (MiniCPM5 knows Derrickson/Wood are American) — q1 cannot
   validate retrieval use; q2 (bridge entity + exact office) can. `long`
   (gold + 4 distractors) fails q2 on ALL arms with "mixing up the roles" —
   a retrieval-set-size effect, not a composition effect.

## Results

Verdict: PARTIAL. Every number below comes from `logs/run.jsonl` (command:
`bash .planning/spikes/005-kv-composition-quality/run.sh`); the table is also
in `results/summary.md` / `results/table.json`.

Head-to-head (TTFT medians of 3 reps, greedy, identical tokens per row;
ok = must_contain rate; =full = text equality vs full rep0):

| q | variant | tok | full TTFT | full ok | warm TTFT | warm x | warm=full | shift TTFT | shift x | shift=full |
|---|---|---|---|---|---|---|---|---|---|---|
| q1 | distr+gold | 339 | 0.055 | 1.0 | 0.013 | 4.2 | 1.0 | 0.051 | 1.1 | 1.0 |
| q1 | distr-only | 208 | 0.036 | 1.0 | 0.013 | 2.8 | 1.0 | 0.032 | 1.1 | 1.0 |
| q1 | dup | 250 | 0.040 | 1.0 | 0.013 | 3.1 | 1.0 | 0.039 | 1.0 | 1.0 |
| q1 | empty | 31 | 0.015 | 1.0 | 0.013 | 1.2 | 1.0 | 0.015 | 1.0 | 1.0 |
| q1 | gold+distr | 339 | 0.055 | 1.0 | 0.013 | 4.2 | 0.0 | 0.051 | 1.1 | 0.0 |
| q1 | gold-AB | 162 | 0.031 | 1.0 | 0.013 | 2.4 | 1.0 | 0.029 | 1.1 | 1.0 |
| q1 | gold-BA | 162 | 0.031 | 1.0 | 0.013 | 2.4 | 1.0 | 0.029 | 1.1 | 1.0 |
| q1 | long | 637 | 0.115 | 1.0 | 0.014 | 8.5 | 0.0 | 0.126 | 0.9 | 0.0 |
| q1 | single-1 | 119 | 0.025 | 1.0 | 0.013 | 2.0 | 1.0 | 0.022 | 1.2 | 1.0 |
| q1 | single-2 | 74 | 0.020 | 1.0 | 0.013 | 1.6 | 1.0 | 0.018 | 1.1 | 1.0 |
| q2 | distr+gold | 394 | 0.071 | 1.0 | 0.014 | 4.9 | 0.0 | 0.058 | 1.2 | 0.0 |
| q2 | distr-only | 217 | 0.036 | 0.0 | 0.014 | 2.6 | 0.0 | 0.036 | 1.0 | 1.0 |
| q2 | dup | 301 | 0.050 | 1.0 | 0.014 | 3.5 | 1.0 | 0.045 | 1.1 | 1.0 |
| q2 | empty | 40 | 0.016 | 0.0 | 0.014 | 1.1 | 1.0 | 0.015 | 1.1 | 1.0 |
| q2 | gold+distr | 394 | 0.071 | 1.0 | 0.014 | 4.9 | 0.0 | 0.057 | 1.2 | 1.0 |
| q2 | gold-AB | 217 | 0.036 | 1.0 | 0.014 | 2.6 | 1.0 | 0.032 | 1.1 | 0.0 |
| q2 | gold-BA | 217 | 0.036 | 1.0 | 0.014 | 2.6 | 1.0 | 0.036 | 1.0 | 1.0 |
| q2 | long | 692 | 0.125 | 0.0 | 0.015 | 8.3 | 0.0 | 0.134 | 0.9 | 0.0 |
| q2 | single-1 | 124 | 0.025 | 0.0 | 0.014 | 1.8 | 1.0 | 0.022 | 1.2 | 1.0 |
| q2 | single-2 | 133 | 0.028 | 0.0 | 0.014 | 2.0 | 1.0 | 0.023 | 1.2 | 1.0 |

Findings, each tied to log evidence:

- TTFT VALIDATED: prebuilt chunk KV (`warm`) removes the prefill slope
  (0.23 ms/tok -> 0.0007 ms/tok, 13 ms floor); relative win 2.4x at 162
  tokens, 8.5x at ~650 tokens. Absolute savings at rig scale: 20–110 ms.
  `shift` saves only the shared prefix: 1.0–1.2x, once 0.9x (noise) — no
  practical win when the suffix (the retrieved set) dominates. This confirms
  efficiency-design section 3: composition is a query-latency optimisation for
  LARGE retrieved sets, second-order at 2B scale (cold full prefill of a
  2-chunk set is 31–36 ms).
- Quality PARTIAL: no arm is systematically better. 14/20 rows fully equal;
  6 rows differ by single late tie-flips in both directions
  (`warm=full`/`shift=full` 0.0 with unchanged-or-flipped correctness).
  Order swap (AB vs BA) keeps correctness 1.0/1.0 on both queries while
  changing wording — cross-chunk attention carries no correctness signal here,
  which bounds (not measures) the cost of true neighbor-blind modules.
- Controls behave: `empty`/`distr-only` fail q2 on all arms (refusal or
  distractor-grounded wrong answer); `single-1` fails q2 everywhere (bridge
  doc missing); `q2 long` fails everywhere (distractor dilution). q1
  `empty`/`distr-only`/`single-*` score 1.0 from PARAMETRIC MEMORY, not
  retrieval — q1 is INVALIDATED as a retrieval-use probe; only q2
  discriminates.
- Against-interest result for the MelodyScribe plan: KV round-trips through
  `save_state`/`load_state` (the persistence path modules would use) and
  through `seq_rm` prefix reuse are NOT bit-exact continuations — each path is
  deterministic per input (3/3 reps identical, `stability` events clean), but
  they flip near-tie greedy tokens on ~25% of inputs. Persisted-module quality
  claims must budget this noise; grammar-constrained op decode (spike 002's
  territory) is less exposed than free-text answers.

What VALIDATED would need: (1) a true neighbor-blind module build
(`seq_cp` composition, the rejected approach above) instead of the warm proxy;
(2) more queries that require retrieval (q1-class memory-answerable queries
excluded); (3) repeating the sweep on 1B/4B/8B for the size trend (D-MS-05).
Caveat for deployment math: warm TTFT here excludes KV load from disk
(~30 MB state at 700 tokens); measure `state_seq_save/load_file` cost before
crediting the full 8.5x.
