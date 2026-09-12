---
spike: 011
idea: melodyscribe
name: generation-preserving-adapter
type: comparison
validates: "Given the shared query set and spike 003's teacher ops, when MiniCPM5-2B is trained with adapter recipes designed to keep op emission alive (lower capacity, a KL anchor to the base, a joint contrastive plus op-emission loss, and a per-pass adapter toggle), then test MRR against the 0.6B embedder and op emission retained or improved, per recipe, on identical inputs"
verdict: PENDING
related: [003, 004, 006, 008]
tags: [embeddings, adapter, training, generation-retained, MelodyScribe-2B]
---

# Spike 011: generation-preserving-adapter

## What This Validates

Spike 006 showed a contrastive LoRA (rank 16, lr 1e-4, 6 epochs) takes the 2B's `⟦EMB⟧` state from test MRR 0.316 to 0.748 against the 0.6B embedder at 0.801, and that the same adapter collapses op emission to zero parses. The one-pass design needs one set of weights that embeds near parity and still emits ops. This spike tests the recipes that could give that, and it is the first attempt at `MelodyScribe-2B-v0.1`. Read `.claude/skills/spike-findings-melodyscribe/SKILL.md`, then `references/embedding-training-and-hybrids.md` and `references/graph-prompt-design.md`, before building. Reuse spike 006's `data.py`, `train_b.py`, `embed_lora.py`, `eval_recall.py`, `gen_eval.py` and spike 003's `student.py`, `evaluate.py`, `teacher.json`, `ops.v0.2.schema.json`, `v02_grammar.py`, `resolve.py` read-only through `sys.path` (copy what you must change into this folder; never edit an earlier spike).

## Plan

Data. Retrieval: `.planning/spikes/shared/queries-v1.json`, train split for training, test split (30 queries over 5 held-out documents) for scoring, the 2 HotpotQA gold queries reported separately. Op emission: spike 003's `teacher.json` ops for the 15 train documents only, formatted with spike 008's recommended one-shot prompt (`008-graph-prompt-design/results/best-prompt.md`, example document `shirley_temple` is a test document, so pick the example from a train document by the same median-op rule and record it); the 5 test documents are never trained on. Negatives as in 006 (in-batch plus other documents).

Training-free controls first (all arms score these before any training, per the research recipe): mean-centering, whitening on the 20 document states plus the train queries, and marker template-bias subtraction on the untrained `⟦EMB⟧` state. If a control alone reaches within 0.05 MRR of the embedder, say so and stop the training arms early.

Arms, all on MiniCPM5-2B in `.venv-train`, identical test inputs, identical evaluation:

- R: spike 006's recipe reproduced (rank 16, lr 1e-4, 6 epochs, InfoNCE, temperature 0.03). Expected test MRR about 0.75 and generation collapse; the reference point.
- L: lower capacity: rank 4, lr 2e-5, 2 epochs, attention projections only. Measures how much retrieval survives when the update is small enough to leave generation alone.
- K: R's objective plus a KL anchor: KL(base logits, adapted logits) on the next-token distribution over spike 003's op-emission prompts (train documents), weight swept over two values (0.1, 1.0). Keeps the language model's predictions near the base while the marker state moves.
- J: joint loss: InfoNCE on the marker state plus causal language-model loss on the one-shot op-emission prompt with the teacher ops as the target (supervised fine-tuning on the train documents). This arm is the `MelodyScribe-2B-v0.1` candidate: it should improve op emission over the base, not merely retain it.
- T: toggle: R's adapter enabled for the embedding pass and disabled for the op pass (peft `disable_adapter`), two decodes. Measures what the one-pass property costs if the build falls back to two passes with one set of weights.

Budget: at most 30 minutes GPU per training run; bf16, gradient checkpointing, sequence length at most 768 for J (one-shot prompt plus ops), 512 elsewhere; every GPU process under `flock /tmp/melodyscribe-gpu.lock`; one model per process.

Metrics, every arm: recall@1, @3, @10 and MRR on the test split and on the gold queries; mean pairwise document cosine; generation retained by spike 006's `gen_eval.py` path (greedy HF decode of the 003 prompt bytes, Proof, grammar-free) with the adapter on versus off: parse rate, routing_exact, Proof-pass, tokens per paragraph; for J also op emission on the 5 test documents with the one-shot prompt, scored against the teacher (routing_exact, subject/value recall, Proof-pass and failure categories). Stretch, only if it fits in 30 minutes of trying: merge J's adapter into the base, convert to GGUF with llama.cpp's converter (a clone may exist under `reference/micro-harnesses/sources/*/code/`; otherwise `pip install` nothing new, record the failure), and score it with spike 003's grammar-constrained `student.py` and `evaluate.py` as arm `minicpm2b-v0.1` next to 003's `minicpm2b` row. Record adapter SHA-256 hashes and training wall time and peak VRAM per arm.

Pass conditions, stated before the run: an arm passes if test MRR is at least 0.75 (006's contrastive level) and generation retained is within 0.05 routing and Proof-pass of the base with the adapter on; J passes if it also improves routing or Proof-pass on the test documents over the base. If no arm passes, PARTIAL with the trade-off curve (MRR against generation retained) and the best arm named; if a control passes without training, VALIDATED with the control as the recommendation.

Environment: `source .planning/spikes/env.sh`; `export TRITON_LIBCUDA_PATH=/run/opengl-driver/lib HF_HUB_OFFLINE=1`; training under `.planning/spikes/.venv-train/bin/python`; weights `.models/hf/openbmb__MiniCPM5-2B`; adapters under this folder in `adapters/` (git-ignored) with hashes in the README. The GPU may be shared with other spike processes; every number reported comes from a lock-held run.

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
