---
spike: 013
idea: melodyscribe
name: train-through-the-harness
type: comparison
validates: "Given spike 012's harness module and harness-shaped dataset, when MiniCPM5-2B is trained as a two-adapter toggle and as a KL-anchored single adapter warm-started from op SFT, and MiniCPM5-1B is fully fine-tuned in bf16 with fp32 optimizer state (optionally also a 1B adapter), on identical data and evaluated through the harness after GGUF conversion, then test MRR against the 0.6B embedder, op-emission Proof-pass and routing under the runtime grammar on held-out documents, and the curve of both against dataset size, per arm"
verdict: PENDING
related: [003, 006, 011, 012]
tags: [training, adapter, full-finetune, bf16, generation-retained, size-curve, MelodyScribe-v0.1]
---

# Spike 013: train-through-the-harness

## What This Validates

Spike 011 mapped the trade-off curve on 15 documents through an approximation of the harness. This spike trains on spike 012's harness-shaped dataset and lets the runtime decoder judge. It separates three variables on identical data and identical evaluation: dataset size, adapter versus full fine-tune, and 1B versus 2B.

**Pre-registered pass condition (before any run).** An arm passes if, on the 012 test split, (a) test MRR is within 0.05 of the dedicated Qwen3-Embedding-0.6B on the same queries and (b) op-emission Proof-pass under the runtime grammar is above the untrained MiniCPM5-2B's on the same sections, with (c) one weight set (the toggle counts: one weight set, two passes). Materiality bar for any comparison between arms: 0.05 MRR or 0.10 Proof-pass, as in 007 and 008; a difference under the bar is reported as not material. The best arm is repeated with a second seed to state the noise floor. Whichever arm passes is `MelodyScribe-{size}-v0.1`; if the toggle alone passes, v0.1 ships two-pass.

## Plan

**Arms (identical data, identical evaluation).**

| Arm | Model | Recipe | What it isolates |
|---|---|---|---|
| A | Qwen3-Embedding-0.6B | none | retrieval reference |
| E | MiniCPM5-2B untrained | none | emission reference (Proof-pass floor) |
| T2 | MiniCPM5-2B | two adapters: contrastive embed adapter (011 R recipe, longer) plus op-emission SFT adapter (one-shot prompt, teacher ops as target); per-pass toggle | the shipping baseline |
| K+ | MiniCPM5-2B | one adapter: warm start from the op SFT adapter, then joint contrastive plus KL anchor to the base (011 K recipe) at rank 32, longer schedule, loss weights swept over two settings | the one-pass candidate |
| F1 | MiniCPM5-1B | full fine-tune, bf16 weights and activations, fp32 optimizer state and master weights, gradient checkpointing, same joint objective as K+ | full plasticity at the size the card affords |
| A1 (optional) | MiniCPM5-1B | K+ recipe as an adapter | adapter versus full at equal size |

Every training arm runs at three dataset fractions, 25, 50, and 100 percent of the train split by whole document with the same seed, so the curve of MRR and Proof-pass against dataset size is measured on the rig. Dev split is used for early stopping only; test is touched once per arm.

**Data.** `012/dataset/` only. Embedding side: query to section pairs from `queries.jsonl`, in-batch negatives plus hard negatives from the same document. Emission side: `sections.jsonl` prompts (the exact bytes) with the Proof-passing op list as the target, empty lists included, store names masked at a ratio swept over 0 and 0.33 (Hammer 2410.04587) as a sub-arm of the SFT adapter only. No thinking traces anywhere. Never train on dev or test documents.

**Evaluation, every arm, through the harness module.** (1) Merge the adapter into the base (or take F1's weights), convert to GGUF with llama.cpp's converter, quantise to Q8 as the runtime does; the T2 arm converts both states. (2) `harness.evaluate_end_to_end` on the test documents: op emission under the v0.2 grammar with the one-shot prompt on MiniCPM5 through llama.cpp, Proof-pass, routing_exact, subject and value recall, syntax versus grounding failures, tokens per section, documents per minute. (3) Retrieval: the `[EMB]` state of each test section from the same GGUF against the test queries, ranked with 010's retrieval stack; recall@1, @3, @10, MRR; the 0.6B reference on the same queries. (4) pass^3: op emission repeated three times per section at temperature 0 with different seeds where sampling applies, reporting the share of sections whose Proof verdict is stable. (5) The HF-side grammar-free decode as a diagnostic only, labelled as such.

**Budget.** Each training run at most 120 minutes GPU under `flock /tmp/melodyscribe-gpu.lock`, one model per process; conversion and evaluation lock-held per step; the full run inside one overnight window. Peak memory logged per arm (011 reference: 7 to 10 GB for 2B adapters; expected 8 to 12 GB for F1 before activations). Environment: `.planning/spikes/.venv-train` for training, `.venv` for evaluation; `TRITON_LIBCUDA_PATH=/run/opengl-driver/lib HF_HUB_OFFLINE=1`; weights under `.models/hf/`; adapters and merges git-ignored with hashes recorded in the README.

**Not in this spike.** RL (015 waits for Proof's hack-probe precision from 012); recall-time training of [RQ] and payload assembly (014); the 4B arm (016 re-runs the size sweep on this dataset once 013 names a weight set).

## Research

`.planning/notes/spike-012-planning-conversation.md` (full fine-tune versus adapters, precision recipe, arm design); `.planning/notes/melodyscribe-harness-frameworks.md` section 8 (training targets the harness defines); `reference/micro-harnesses/deep-research-3/REPORT.md` section 5b (joint training on one 16 GB GPU: toggle first, KL anchor, rank and learning-rate regime, staging) and section 5c (evaluation protocol); `reference/micro-harnesses/deep-research-4/lanes/1/findings.md` (abstention, name masking), `lanes/4` (no thinking data), `lanes/10` (pass^k, AST plus execution grading, syntax versus grounding); spike 011 README (K and T results, deviations closed here).

## How to Run

```bash
source .planning/spikes/env.sh
bash .planning/spikes/013-train-through-the-harness/run.sh [RUN]
```

`run.sh` steps: (0) assert `012/dataset/MANIFEST.json` exists and 012's identity check passed; (1) A and E references; (2) T2 embed adapter and op SFT adapter at three fractions; (3) K+ at three fractions and two loss settings; (4) F1 at three fractions; (5) A1 if enabled; (6) merge, convert, quantise per arm; (7) harness evaluation per arm and fraction; (8) second-seed repeat of the best arm; (9) tables in `results/`, curve in `results/size-curve.md`, verdict. Logs as JSON lines with ISO timestamps in `logs/`, one file per arm and fraction.

## What to Expect

- T2 reproduces 011's T shape at 15 documents and improves with data; it is the floor v0.1 ships on.
- K+ closes some of the 0.57 to 0.62 versus 0.71 gap with more data and the SFT warm start; whether it reaches the 0.05 bar is the open question.
- F1 is the unmeasured point: a trained 1B could match the 2B adapters at lower cost or could sit below the emission floor as the untrained 1B did.
- Proof-pass rises with dataset fraction; if it does not, the dataset, not the recipe, is the suspect.

## Investigation Trail

(filled during the run)

## Results

(filled during the run; verdict set to VALIDATED, INVALIDATED, or PARTIAL with evidence)
