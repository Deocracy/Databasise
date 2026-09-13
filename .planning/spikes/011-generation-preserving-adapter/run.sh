#!/usr/bin/env bash
# Spike 011: generation-preserving-adapter (comparison).
# Reproduces everything: 0.6B baseline (A) + untrained 2B (E) + bias probe,
# training-free controls, five adapter trainings (R/L/K01/K10/J), per-arm
# embedding, head-to-head recall, zero-shot generation-retained scoring,
# toggle verification, one-shot op emission on the 5 test docs (base + J).
# Run from the repo root: .planning/spikes/011-generation-preserving-adapter/run.sh [RUN]
# Every GPU step takes the GPU lock individually (one model per process);
# training/analysis never hold the lock on network (no network steps exist).
# Expected wall time ~90-120 min, most of it generation scoring.
set -u
ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
S="$ROOT/.planning/spikes/011-generation-preserving-adapter"
source "$ROOT/.planning/spikes/env.sh"
# triton hardcodes /sbin/ldconfig (absent on NixOS); the knob bypasses it.
export TRITON_LIBCUDA_PATH=/run/opengl-driver/lib
export HF_HUB_OFFLINE=1
TPY="$ROOT/.planning/spikes/.venv-train/bin/python"
RUN="${1:-run1}"

"$TPY" -c "import torch, transformers, peft, sentence_transformers, safetensors; print('train env ok', torch.cuda.is_available())" || exit 1

# 1. Baselines: arm A (0.6B embedder) + arm E (untrained 2B marker state).
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_a.py" "$RUN" || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_untrained.py" "$RUN" || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/bias_probe.py" "$RUN" || exit 1

# 2. Training-free controls (CPU) + early gate: controls vs embedder.
"$TPY" -u "$S/controls.py" "$RUN" || exit 1
"$TPY" "$S/eval_recall.py" "${RUN}controls" \
  "$S/results/vecs_A_${RUN}.json" \
  "$S/results/vecs_E_${RUN}.json" \
  "$S/results/vecs_Cmean_${RUN}.json" \
  "$S/results/vecs_Cwhiten_${RUN}.json" \
  "$S/results/vecs_Cbias_${RUN}.json" || exit 1

# 3. Trainings (<=30 min GPU each): R (006 reproduction), L (low-cap),
#    K01/K10 (KL anchor sweep), J (joint contrastive + op-emission LM).
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/train_r.py" "$RUN" || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/train_l.py" "$RUN" || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/train_k.py" "$RUN" --kl=0.1 || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/train_k.py" "$RUN" --kl=1.0 || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/train_j.py" "$RUN" || exit 1

# 4. Per-arm embedding (GPU, one process each).
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_lora.py" "$RUN" "adapters/lora_contrastive_$RUN" R-minicpm2b || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_lora.py" "$RUN" "adapters/lora_lowcap_$RUN" L-minicpm2b || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_lora.py" "$RUN" "adapters/lora_kl0.1_$RUN" K01-minicpm2b || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_lora.py" "$RUN" "adapters/lora_kl1_$RUN" K10-minicpm2b || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_lora.py" "$RUN" "adapters/lora_joint_$RUN" J-minicpm2b || exit 1

# 5. Head-to-head recall (CPU): identical inputs, all arms.
"$TPY" "$S/eval_recall.py" "$RUN" \
  "$S/results/vecs_A_${RUN}.json" \
  "$S/results/vecs_E_${RUN}.json" \
  "$S/results/vecs_Cmean_${RUN}.json" \
  "$S/results/vecs_Cwhiten_${RUN}.json" \
  "$S/results/vecs_Cbias_${RUN}.json" \
  "$S/results/vecs_R-minicpm2b_${RUN}.json" \
  "$S/results/vecs_L-minicpm2b_${RUN}.json" \
  "$S/results/vecs_K01-minicpm2b_${RUN}.json" \
  "$S/results/vecs_K10-minicpm2b_${RUN}.json" \
  "$S/results/vecs_J-minicpm2b_${RUN}.json" || exit 1

# 6. Generation retained, zero-shot 003 prompt (GPU, one process each).
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/gen_eval.py" "$RUN" minicpm_base || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/gen_eval.py" "$RUN" "minicpm_lora:adapters/lora_contrastive_$RUN" || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/gen_eval.py" "$RUN" "minicpm_lora:adapters/lora_lowcap_$RUN" || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/gen_eval.py" "$RUN" "minicpm_lora:adapters/lora_kl0.1_$RUN" || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/gen_eval.py" "$RUN" "minicpm_lora:adapters/lora_kl1_$RUN" || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/gen_eval.py" "$RUN" "minicpm_lora:adapters/lora_joint_$RUN" || exit 1

# 7. Toggle check (GPU): adapter-disabled forward == pure base.
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/verify_toggle.py" "$RUN" "adapters/lora_contrastive_$RUN" || exit 1

# 8. One-shot op emission on the 5 test docs, base vs J (GPU each).
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/gen_oneshot.py" "$RUN" base || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/gen_oneshot.py" "$RUN" "lora:adapters/lora_joint_$RUN" || exit 1

echo "SPIKE-011 COMPLETE: results/recall_${RUN}.json + results/gen_*_${RUN}.json + results/oneshot_*_${RUN}.json in $S"
