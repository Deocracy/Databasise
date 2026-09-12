---
spike: 004
idea: melodyscribe
name: self-embedding-parity
type: comparison
validates: "Given the corpus and its queries, when embedded by a dedicated 0.6B embedder, by untrained last-token states, and by a trained head over frozen states, then recall@k per method"
verdict: PARTIAL
related: []
tags: [embeddings, recall, head]
---

# Spike 004: self-embedding-parity

## What This Validates

Given the corpus and its queries, when embedded by (A) a dedicated 0.6B
embedder, (B) untrained last-token states, and (C) a trained head over frozen
states, then recall@k per method — all arms on identical inputs, head-to-head.

## Research

- SCORE-IO-SPEC §2: vector read at one position, pooling `last` at `[EMB]`;
  per-model token policy recorded with the model revision. Untrained state =
  base-model last-token representation; trained = head/adapter over it.
  This spike measures exactly that gap.
- `reference/micro-harnesses/runtime-one-pass.md`: three routes for one-pass
  embedding (llama.cpp C API sequences, prompt cache, SGLang hidden states);
  adapter-vs-head decision open. This spike uses llama-cpp-python
  `embedding=True` with forced `LLAMA_POOLING_TYPE_LAST` as the stand-in for
  "read state at [EMB]", and a ridge-distillation linear head as the weakest
  form of "trained".
- Corpus: 20 docs (title + one paragraph each, ~9.6 KB total), 2 HotpotQA gold
  queries (2 gold docs each). n=2 is too little power on its own, so the spike
  adds 20 self-retrieval probes (each doc's first content sentence as query,
  gold = itself) and 75 sentence chunks for head training and chunk-level eval.
- Supervision decision: with only 2 gold queries, query-supervised training of
  a 2048-dim head is vacuous, so arm C is ridge regression from frozen B
  states to arm-A states (distillation) on the 75 chunks. Eval queries are
  never training inputs. A linear head is the floor of "trained", not the
  ceiling: contrastive adapter tuning (the real MelodyScribe plan) is NOT
  tested here and is named as the follow-up.

## How to Run

```
cd .planning/spikes/004-self-embedding-parity
./run.sh
```

`run.sh` sources `../env.sh` (GPU libs, `$MELODYSCRIBE_PY`, `$MELODYSCRIBE_MODELS`).
Every model load runs under `flock /tmp/melodyscribe-gpu.lock`; training,
eval, and analysis use plain CPU (`numpy` only) with no lock. One model per
process: two live `Llama` instances (or reuse after a decode error) crash at
exit with `double free or corruption` on this rig — `edge.py`/`edgeB.py` are
split accordingly. Scripts: `eval_common.py --build` (inputs), `arm_embed.py`
(one arm, one input list → vectors JSON), `evaluate.py` (head-to-head recall),
`train_head.py` (ridge B→A), `controls.py` (centering control, chunk recall),
`diagnose.py` (anisotropy), `edge.py`/`edgeB.py` (edge cases). Every run
appends JSON-lines logs with ISO timestamps under `logs/`; vectors and reports
under `results/`.

## What to Expect

~15 min wall clock, ~2 min of it GPU (tiny corpus; each full-corpus embed is
< 1 s load + < 1 s embed). Head-to-head table (below) with arm A far ahead,
arm B/B2 behind, trained linear heads failing to close the gap. `run.sh`
re-embeds arm A docs to prove determinism (max abs diff 0.0).

## Investigation Trail

1. **Smoke test.** Qwen3-Embedding-0.6B embeds natively (effective pooling 3 =
   LAST, dim 1024, 25 ms/text). MiniCPM5-2B (generative, native pooling −1 =
   UNSPECIFIED) forced to LAST, dim 2048; plain vs `⟦EMB⟧`-marked text cosine
   0.30 — the marker moves the state a lot. Log: `logs/armA_docs.jsonl`.
2. **Head-to-head (identical inputs).** A: gold mrr 1.00, self mrr 0.91.
   B: gold mrr 0.31, self mrr 0.55. B2 (Qwen3-1.7B): gold mrr 0.13, self
   mrr 0.43. Dedicated embedder wins by a wide margin on both query sets.
   Log: `logs/head2head.jsonl`, report `results/head2head_report.json`.
3. **Is it the marker? No.** B-without-marker: gold mrr 0.33, self mrr 0.56 —
   marker vs plain is 0.31 vs 0.33. The gap is in the states, not the policy.
   Log: `logs/ablation1.jsonl`.
4. **Anisotropy is the mechanism.** Mean pairwise doc cosine: A 0.278,
   B 0.914, B2 0.949, B-plain 0.776. Untrained last-token states all point
   nearly the same way, so cosine has almost no signal. Surprise: the `⟦EMB⟧`
   marker makes anisotropy *worse* (0.914 vs 0.776). Log: `logs/diag1.jsonl`.
5. **Trained head (ridge B→A on 75 chunks, λ sweep 1/100/1e5).** Train cos
   0.65 at λ=1 — but query→doc recall gets *worse*: gold mrr 0.31→0.17, self
   mrr 0.55→0.49. Larger λ degrades further (mrr 0.09). The linear map
   overfits (d=2048 ≫ n=75) and destroys ranking structure. Logs:
   `logs/headB_lam*.jsonl`, `logs/headBeval_lam*.jsonl`.
6. **Centering control.** Corpus-mean centering barely moves B (gold r@3
   0.25→0.25) but helps B2 a lot (gold r@3 0.00→0.50, self r@1 0.25→0.55):
   B2's deficit is mostly a shared-direction offset; B's is structural.
   Centering leaves A unchanged (0.75). Log: `logs/ctrl1.jsonl`.
7. **Head, in-distribution (chunk→chunk, same-doc hit).** Plain+head improves
   slightly (r@1 0.32→0.37); marker+head degrades (0.31→0.29). So the head
   learns *something* on declarative chunks but does not transfer to
   interrogative queries — a distribution story on top of the overfit story.
   Log: `logs/headIndistrib.jsonl`.
8. **Head over better-conditioned input still fails.** Plain-state head fits
   better (train cos 0.74 vs 0.65) yet query recall still drops (gold mrr
   0.33→0.15; self mrr ties 0.56). Better fit ≠ better ranking. Logs:
   `logs/headBplain_lam1.jsonl`, `logs/headBplainEval.jsonl`.
9. **Determinism (I1-adjacent).** Re-embedded arm-A docs byte-identical
   (max abs diff 0.0). Isolated embedding sequences are reproducible across
   runs. `results/armA_redo_docs.json`.
10. **Edges.** Empty input: A returns a degenerate vector silently (norm 118
    vs ~1 for real text — harness must guard); B hard-errors
    (`llama_decode returned -1`) and poisons the process (later calls crash),
    so empty sections must be rejected *before* embedding. Over-ctx (4201
    tokens > 2048): both silently truncate, no error — chunker must enforce
    limits. Marker-in-content: harmless for A (cos 0.990 with/without
    trailing marker), moves B a lot (cos 0.478) — the spec's escape rule
    matters for the generative path. Prefix asymmetry (`Passage:`/`Query:` vs
    bare): no effect on A gold r@3 (0.75 × 3) — prefix choice is insensitive
    here. Logs: `logs/edge1–4.jsonl`, `logs/edgeVerify.jsonl`.

## Results

Verdict: **PARTIAL**. The head-to-head measurement is complete and decisive,
but parity was not reached and the "trained" arm is a linear proxy, not the
contrastive adapter training MelodyScribe actually plans.

Head-to-head (recall@k, mean over query set; gold n=2, self n=20):

| arm | gold r@1 / r@3 / r@10 / mrr | self r@1 / r@3 / r@10 / mrr |
|---|---|---|
| A dedicated 0.6B embedder | 0.50 / 0.75 / 1.00 / 1.00 | 0.85 / 1.00 / 1.00 / 0.91 |
| B MiniCPM5-2B last-token + `⟦EMB⟧` | 0.00 / 0.25 / 0.50 / 0.31 | 0.40 / 0.60 / 0.80 / 0.55 |
| B2 Qwen3-1.7B last-token + `⟦EMB⟧` | 0.00 / 0.00 / 0.50 / 0.13 | 0.25 / 0.50 / 0.75 / 0.43 |
| B + ridge head (λ=1, distill to A) | 0.00 / 0.00 / 0.25 / 0.17 | 0.30 / 0.55 / 0.85 / 0.49 |
| B-plain + ridge head (λ=1) | 0.00 / 0.00 / 0.75 / 0.15 | 0.35 / 0.70 / 0.95 / 0.56 |
| B2 centered (no training) | 0.25 / 0.50 / 0.50 / — | 0.55 / 0.65 / 0.90 / — |

Sub-claims:

- **VALIDATED**: a dedicated 0.6B embedder beats untrained last-token states
  from 1.7B/2B generative models by a wide margin on this corpus (gold mrr
  1.00 vs 0.31/0.13; self mrr 0.91 vs 0.55/0.43), on identical inputs.
- **VALIDATED**: the mechanism is anisotropy — untrained last-token states
  have mean pairwise cosine 0.78–0.95 vs 0.28 for the trained embedder.
- **INVALIDATED**: a ridge-distillation linear head over frozen states closes
  the gap. It fits the training chunks (cos 0.65–0.74) yet *lowers*
  query→doc recall at every λ, and only trivially helps in-distribution
  chunk retrieval. d ≫ n overfitting plus train(declarative)/test
  (interrogative) shift defeat it.
- **INVALIDATED (proxy scope)**: "trained head" here means linear ridge only.
  Contrastive adapter/LoRA tuning with query-gold supervision — the actual
  MelodyScribe plan — is untested (the corpus has 2 gold queries; a real
  training set needs frontier-labelled query→passage pairs, cf. spike 003's
  teacher labelling). That experiment, not this one, decides whether
  self-embedding can reach parity.
- Harness rules established: reject empty sections before embedding (B
  hard-errors and poisons the process; A silently returns garbage norm-118);
  enforce chunker-side ctx limits (both paths silently truncate past n_ctx);
  escape the literal marker for the generative path (cos 0.48 sensitivity);
  record per-model token policy (`emb=native:last` for Qwen3-Embedding-0.6B,
  `emb=literal:⟦EMB⟧/last` for the generative arms); one model per process
  on this rig.
- Caveats: gold set is n=2 (exact numbers reported, low power — the n=20
  self set carries the statistical weight); docs are short (title +
  paragraph), so long-document behaviour is untested; all GPU runs held the
  lock, one model per process, Q8 quantisation throughout.
