---
spike: 006
idea: melodyscribe
name: hybrid-embedder
type: comparison
validates: "Given teacher-generated query-passage pairs with a held-out document split, when the small model's [EMB] state is trained by a LoRA contrastive adapter and by distillation to the 0.6B embedder, and when the 0.6B embedder is weight-merged with its same-architecture generative base, then recall@k and MRR versus the dedicated 0.6B embedder, and generation retained (op emission under grammar) for each mixed model"
verdict: PARTIAL
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

Read first, in order: `.planning/spikes/MANIFEST.md` (idea + requirements),
`001-score-io-model/SCORE-IO-SPEC.md` + `ops.schema.json` (contract),
`reference/micro-harnesses/README.md` (orientation), and
`.claude/skills/spike-findings-melodyscribe/SKILL.md` +
`references/model-size-and-training.md` (settled results — not re-measured:
dedicated 0.6B gold MRR 1.00/self 0.91 vs untrained 2B 0.31/0.55;
anisotropy 0.28 vs 0.91; ridge head lowers recall; 003 prompt bytes,
teacher labels, v0.2 grammar + Proof in `003-op-emission-size-sweep/`
reused read-only).

Design decisions taken from the references:
- Arm A baseline: Qwen3-Embedding-0.6B, bare text, native last-token
  pooling. Spike 004 found prefix choice insensitive, so bare matches its
  GGUF arm; backend here is sentence-transformers safetensors (needed
  anyway for arm C teacher vectors), stated and fixed across arms.
- Arms B/C pooling: literal `⟦EMB⟧` marker (6 MiniCPM tokens), last-token
  state, causal attention (the one-pass design needs it; no bidirectional
  variant — it would break the design it serves).
- Arm B: InfoNCE query→passage, tau 0.03, in-batch + all other train-doc
  passages as hard negatives (15 train docs), LoRA r16 on q/k/v/o/gate/up/
  down, bf16, grad checkpointing, seq ≤ 512, 6 epochs × 11 steps.
- Arm C: mean(1−cos) of a trainable Linear(2048→1024) projection to A's
  frozen vectors (train queries + train passages) + InfoNCE (λ=1).
- Arm D: Qwen3-Embedding-0.6B × Qwen3-0.6B. Same Qwen3Config (1024/28) but
  different namespaces (`layers.*` vs `model.layers.*`, embedder has no
  lm_head) and vocabs (emb rows 151669 vs gen 151936; added tokens
  byte-identical ids 151643–151668, gen tail 151669+ reserved). Merge rule:
  strip `model.`, interpolate shared tensors at w∈{0.25,0.5,0.75} embed
  fraction, interpolate shared embed rows, keep gen reserved rows + gen
  lm_head verbatim. TIES attempted through mergekit (installed) — see
  Investigation Trail for what happened.
- Generation-retained: greedy HF decode of 003's exact student prompt
  bytes, scored by 003's Proof + teacher.json (routing_exact, Proof-pass).
  No llama-cpp grammar: adapters/merged weights are HF-native with no
  GGUF path, so change-on vs change-off share one unconstrained decoder
  and Proof scores the difference (disclosed deviation, head-to-head fair).
- Metrics: recall@1/3/10 + MRR on the 30-query test split (5 held-out
  docs, ranked over all 20 docs), HotpotQA gold, train-split diagnostic,
  mean pairwise doc cosine, ms/text, training wall/VRAM.

## How to Run

```
cd .planning/spikes/006-hybrid-embedder
./run.sh [RUN]     # RUN defaults to run1; reproduces everything (~75-100 min)
```

`run.sh` sources `../env.sh`, exports `TRITON_LIBCUDA_PATH` (triton
hardcodes `/sbin/ldconfig`, absent on NixOS — the knob bypasses it) and
`HF_HUB_OFFLINE=1`. Every GPU step runs under
`flock /tmp/melodyscribe-gpu.lock`, one model per process; merges and
scoring are CPU-only without the lock. Scripts: `embed_a.py` (A +
teacher vectors), `embed_untrained.py` (E), `train_b.py`/`train_c.py`
(LoRA runs, ≤30 min GPU each), `embed_lora.py` (B/C eval vectors),
`merge_d.py` (D), `embed_qwen.py` (D + Qwen base vectors),
`eval_recall.py` (head-to-head, CPU), `gen_eval.py` (generation retained).
Logs: `logs/*.jsonl` (ISO timestamps) + `logs/stdout-*.log`.
Never train on test documents (asserted in both trainers); never hold the
lock on network (no network steps exist — labels are pre-generated).

Deviations from the plan (all head-to-head fair, both sides alike):
- Generation-retained runs without the llama-cpp grammar (adapters and
  merged weights are HF-native, no GGUF path exists); change-on vs
  change-off share one unconstrained greedy decoder, Proof scores the
  difference. Absolute routing is therefore below 003's levels.
- `gen_eval.py` writes partial results per decode and resumes from them
  (greedy = deterministic); `train_b.py` gained `--seed`; per-epoch
  adapter ckpts. All added after kills/reboots, all logged in the trail.
- `gpu_batch.sh` batches short GPU steps under one lock acquisition
  (one model per process throughout) — an operational response to the
  lock siege, not part of the reproduced path (`run.sh` wraps each step
  individually).

## What to Expect

~75–100 min wall (two ~2.5 min LoRA trains dominate less than expected;
the cost is GPU-lock contention with sibling spikes plus ~35 min of greedy
generation scoring). Head-to-head table with A on top, B close behind on
retrieval but generation-collapsed, C behind B, D climbing with embed
weight. `run.sh` reuses 003's `teacher.json`/`resolve.py`/`ops_validate`
read-only and asserts the corpus hash at every load.

## Investigation Trail

1. **Recon.** 86 train / 30 test queries, 5 test docs, corpus hash
   `ac55d19e…` everywhere; MiniCPM5-2B bf16 5.0 GB, hidden 2048×42;
   Qwen pair both Qwen3Config 1024×28 but different key namespaces and
   vocabs (emb rows 151669 vs gen 151936). `⟦EMB⟧` = 6 MiniCPM tokens.
2. **triton blocks every CUDA encode.** First `sentence-transformers`
   encode died in `triton/backends/nvidia/driver.py:libcuda_dirs`, which
   hardcodes `/sbin/ldconfig` (absent on NixOS). Fix: export
   `TRITON_LIBCUDA_PATH=/run/opengl-driver/lib` (knob bypasses the call);
   recorded in `run.sh`/`gpu_batch.sh`. Log: `logs/base1.jsonl`
   (model_loaded events of the failed attempts precede the fix).
3. **Detached background GPU jobs do not survive.** Two `setsid` launches
   died with their tool calls; a foreground `flock` waiter survived one
   "interrupted" call (pid 322926) and is still queued. Lesson recorded:
   GPU steps run foreground under `flock`; `gen_eval.py` is resume-aware
   (reloads decoded docs from its results file, greedy = deterministic)
   so kills become progress, not loss.
4. **Wrong interpreter once.** A retry used `$MELODYSCRIBE_PY` (`.venv`,
   no `sentence_transformers`) instead of `.venv-train`. `run.sh` uses
   `$TPY` throughout; the manual command was the bug.
5. **Arm A** (`logs/base1.jsonl`, `results/vecs_A_base1.json`): dim 1024,
   99.6 ms/doc, 2.45 ms/q. Test MRR 0.801, gold 1.00, aniso 0.279 —
   matches 004's GGUF profile through a different backend.
   (`results/recall_base1.json`.)
6. **Arm E** (`logs/run1.jsonl` model_loaded + `run1e` recall): test MRR
   0.316, gold 0.125, aniso 0.903 — reproduces 004's arm B (0.31/0.914)
   through HF. The gap to close: 0.316 → 0.801.
7. **Arm B trained** (`logs/run1.jsonl` steps, 66 steps/147 s, peak
   7.1 GB): loss noisy 0.9→0.02. Retrieval: test MRR 0.748 (Δ0.053 from
   A — just misses the 0.05 bar), train 0.956 (memorisation gap),
   gold 0.750, aniso 0.679. (`results/recall_run1b.json`.)
8. **Arm C trained** (66 steps/145 s, 7.1 GB; dist term stuck ~0.55
   while NCE fell): test MRR 0.638, train 0.966, aniso 0.680 — the
   distillation-to-A objective ranks WORSE than pure contrastive, an
   against-interest result. (`results/recall_run1cd.json`.)
9. **Arm D merged** (`logs/m1.jsonl`/`m2.jsonl`, `merged/manifest_run1.json`;
   m1/m2 SHAs byte-identical): 309 shared tensors + shared embed rows
   interpolated, gen reserved rows + lm_head verbatim. Retrieval climbs
   with embed weight — MRR 0.384 (base) → 0.538 → 0.617 → 0.660; w0.75
   reaches 0.82× A. (`results/recall_run1d.json`.)
10. **TIES INVALIDATED (tooling).** mergekit is installed but both the
    API (`run_merge` — `MergeRunner` does not exist in this version) and
    the CLI fail at config validation with
    `ConfiguredModuleArchitecture is not fully defined` (pydantic v2
    incompatibility inside mergekit, unrelated to the merge inputs; the
    padded aligned copy was built and is left in `merged/`).
    Log: `logs/m2.jsonl` `ties_failed`; CLI error captured in the trail.
    Linear merges stand as the D arm.
11. **Generation retained, MiniCPM side.** Unconstrained greedy HF decode
    (no grammar — disclosed deviation): base route 0.10 / parse 0.15 /
    Proof-pass 1.0 (9/9), 856 tok/para. With B: route 0.0 / parse 0.0
    (20/20 cap-looping repetitive gibberish). With C: route 0.0 /
    parse 0.0 (same collapse mode). Both adapters catastrophically
    destroy instruction-following at r16/lr1e-4/6ep. Logs:
    `logs/gen-gen-minicpm-base-….jsonl`,
    `logs/gen-gen-lora_contrastive_run1-….jsonl`,
    `logs/gen-gen-lora_distill_run1-….jsonl`.
12. **Generation retained, Qwen side.** Raw 0.6B base: route 0.0 /
    parse 0.0 (1023 tok/para cap-loop) — the base keeps nothing to keep,
    so D's generation bar is vacuous; all three merged ratios also 0.0 /
    0.0 (Proof-pass 1.0 on 0/0 both sides). A reboot cut the w0.75 run at
    7/20; `gen_eval.py`'s resume (reloads decoded docs, greedy =
    deterministic) completed it exactly. Logs: `logs/gen-gen-qwen06-*.jsonl`.
13. **Seed robustness for B.** Same recipe, seed 999: test MRR 0.740 vs
    0.748 (seed 1234), train 0.949, aniso 0.581. The Δ0.05 miss is stable,
    not seed noise. (`results/recall_final.json`, adapter
    `adapters/lora_contrastive_run1seed999`.)
14. **Lock siege as method note.** Sibling spikes (007/008/010) held the
    GPU lock for 25–60 min stretches; short steps starved until batched
    under one acquisition (`gpu_batch.sh`, one model per process) or run
    as resume-aware single steps. Two machine reboots killed GPU jobs
    twice; per-epoch adapter ckpts + `gen_eval` resume meant zero lost
    training and exact completion of scoring.

## Results

Verdict: **PARTIAL**.

Head-to-head retrieval (identical inputs, 30 test queries over 5 held-out
docs ranked against all 20; `results/recall_final.json`):

| arm | test r@1 / r@3 / r@10 / MRR | train MRR | gold MRR | aniso |
|---|---|---|---|---|
| A dedicated 0.6B | 0.700 / 0.867 / 1.000 / 0.801 | 0.788 | 1.000 | 0.279 |
| E 2B untrained | 0.233 / 0.267 / 0.633 / 0.316 | 0.315 | 0.125 | 0.903 |
| B 2B + LoRA contrastive | 0.567 / 0.933 / 1.000 / 0.748 | 0.956 | 0.750 | 0.679 |
| B seed 999 | 0.633 / 0.800 / 1.000 / 0.740 | 0.949 | 0.500 | 0.581 |
| C 2B + LoRA distill | 0.433 / 0.767 / 1.000 / 0.638 | 0.966 | 0.750 | 0.680 |
| D0 Qwen3-0.6B base | 0.233 / 0.433 / 0.667 / 0.384 | 0.480 | 0.600 | 0.846 |
| D w0.25 | 0.367 / 0.633 / 0.967 / 0.538 | 0.584 | 0.750 | 0.762 |
| D w0.5 | 0.433 / 0.700 / 1.000 / 0.617 | 0.644 | 1.000 | 0.625 |
| D w0.75 | 0.467 / 0.800 / 1.000 / 0.660 | 0.664 | 1.000 | 0.479 |

Generation retained (greedy HF decode of 003's prompt bytes, v0.2 Proof vs
`teacher.json`; no grammar — disclosed deviation; `results/gen_*.json`):

| arm | routing_exact | parse_rate | Proof-pass | tok/para | s/para |
|---|---|---|---|---|---|
| minicpm base | 0.100 | 0.150 | 1.000 (9/9) | 856.6 | 17.57 |
| minicpm +B | 0.000 | 0.000 | 1.000 (0/0) | 1020.5 | 49.37 |
| minicpm +C | 0.000 | 0.000 | 1.000 (0/0) | 989.3 | 49.54 |
| qwen06 base | 0.000 | 0.000 | 1.000 (0/0) | 1023.0 | 19.40 |
| qwen06 +w0.25/0.5/0.75 | 0.000 | 0.000 | 1.000 (0/0) | ~1024 | ~18 |

(Caveat: the +B/+C s/para ~49 includes GPU contention with an unlocked
orphan run; the base-side numbers were lock-held throughout. Absolute
timings, not the comparison, are affected.)

Sub-claims:

- **PARTIAL (near-miss, stable)**: B reaches test MRR 0.748/0.740 vs A
  0.801 (Δ0.053/0.061 — misses the 0.05 bar on both seeds) with
  train MRR 0.95+ (memorisation gap on 15 docs). Contrastive LoRA closes
  most of the untrained gap (0.316 → 0.748) but does not reach parity.
- **INVALIDATED**: C (distillation to A + InfoNCE) ranks worse than pure
  contrastive (0.638 vs 0.748) despite fitting A's vectors on train
  texts; the projection bottleneck + dual objective hurts ranking. The
  "embedding model mixed into the small model" direction fails here.
- **INVALIDATED**: generation retained for B/C. Both adapters collapse
  unconstrained op emission to 0/20 parse (cap-looping repetition)
  against a weak-but-nonzero base (route 0.10, parse 0.15). A LoRA
  embedding adapter and the generative pass do NOT coexist at
  r16/lr1e-4/6ep — the one-pass design needs a generation-preserving
  recipe (lower rank/lr, KL anchor, or joint LM loss), untested here.
- **PARTIAL**: D retrieval climbs monotonically to 0.82× A at w0.75
  (0.660 vs 0.801 — passes the 0.8 bar) with gold MRR 1.00; D generation
  is a vacuous hold (base and all merges parse 0.0 — a raw 0.6B base
  cannot emit ops unconstrained, so there is nothing to retain).
- **INVALIDATED (tooling, not idea)**: TIES/DARE via mergekit — the
  installed mergekit is broken under pydantic v2 (config validation
  raises before any tensor is touched, API and CLI alike). Linear
  interpolation stands as the D arm.
- Harness facts: both LoRA trains fit easily (147/145 s, peak 7.1 GB of
  16 GB — the 30-min budget is 10× headroom); MiniCPM5 marker = 6 tokens;
  added Qwen tokens byte-identical across the pair (merge alignment
  exact); `TRITON_LIBCUDA_PATH` required on NixOS; never prepend BOS
  applies to llama-cpp only (HF defaults used symmetrically on both
  sides here).
- Caveats: generation comparison is grammar-free (adapters are
  HF-native), so absolute routing is far below 003's grammar-constrained
  numbers — the on-vs-off deltas are the evidence, not the levels;
  test set is n=30 over 5 docs; docs are short paragraphs.

Owner re-run (2026-09-12, `run.sh repro`, separate run name so this run's adapters and merges stay on disk): arms A, E, D0, and the three linear merges reproduce every retrieval number exactly (`results/recall_repro.json`); the retrained LoRA arms land within 0.025 MRR (B 0.748 to 0.724, B-seed999 0.740 to 0.726, C 0.638 to 0.618), so GPU LoRA training is not bit-exact across runs and the parity gap is 0.05 to 0.08 depending on the run; generation retained reproduces exactly (base route 0.10, parse 0.15, 9/9 Proof; both adapters 0/20 parses; every 0.6B arm 0/20). The PARTIAL verdict and its ordering hold.

Adapter SHAs (`logs/run1.jsonl` train_done; `logs/run1seed999.jsonl`):
B `aa761ddc…` (seed 1234), B-seed999 `72d4140c…`, C `4d93a229…`.
Merged SHAs (`merged/manifest_run1.json`): w0.25 `4a8ce74b…`, w0.5
`b556e72f…`, w0.75 `71fae1a3…` (m1/m2 byte-identical).

