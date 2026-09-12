#!/usr/bin/env bash
# Spike 006: hybrid-embedder (comparison).
# Reproduces everything: arm A baseline + teacher vectors, arm E control,
# LoRA contrastive (B) + distillation (C) training, linear + TIES merges (D),
# head-to-head recall scoring, generation-retained op-emission scoring.
# Run from the repo root. Each GPU step takes the GPU lock individually
# (one model per process); training/analysis never hold the lock on network.
# Expected wall time ~75-100 min, most of it two LoRA training runs.
set -u
ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
S="$ROOT/.planning/spikes/006-hybrid-embedder"
source "$ROOT/.planning/spikes/env.sh"
# triton hardcodes /sbin/ldconfig (absent on NixOS); the knob bypasses it.
export TRITON_LIBCUDA_PATH=/run/opengl-driver/lib
export HF_HUB_OFFLINE=1
TPY="$ROOT/.planning/spikes/.venv-train/bin/python"
RUN="${1:-run1}"

"$TPY" -c "import torch, transformers, peft, sentence_transformers, safetensors; print('train env ok', torch.cuda.is_available())" || exit 1

# 1. Arm A baseline (sentence-transformers) + teacher vectors for arm C.
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_a.py" base1 || exit 1

# 2. Arm E control: untrained MiniCPM5-2B marker state (HF backend).
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_untrained.py" "$RUN" || exit 1

# 3. Arm B: LoRA contrastive (<=30 min GPU per training run).
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/train_b.py" "$RUN" || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_lora.py" "$RUN" "adapters/lora_contrastive_$RUN" B-minicpm2b || exit 1
# 3b. Seed robustness: same recipe, seed 999 (tests whether B's near-miss is noise).
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/train_b.py" "${RUN}seed999" --seed=999 || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_lora.py" "${RUN}seed999" "adapters/lora_contrastive_${RUN}seed999" B-seed999 || exit 1

# 4. Arm C: LoRA distillation to A + InfoNCE (needs results/teacher_A_train.json).
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/train_c.py" "$RUN" || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_lora.py" "$RUN" "adapters/lora_distill_$RUN" C-minicpm2b --proj || exit 1

# 5. Arm D: merges are CPU-only (no lock); TIES attempted, linear guaranteed.
"$TPY" -u "$S/merge_d.py" "$RUN" --ties || exit 1

# 6. Arm D + Qwen base retrieval (GPU, one process each).
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_qwen.py" "$RUN" \
  ".planning/spikes/.models/hf/Qwen__Qwen3-0.6B" D0-qwen06base || exit 1
for w in 0.25 0.5 0.75; do
  flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_qwen.py" "$RUN" \
    ".planning/spikes/006-hybrid-embedder/merged/qwen06_linear_w${w}_${RUN}" "D-w${w}" || exit 1
done
if [ -d "$S/merged/qwen06_ties_$RUN" ]; then
  flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/embed_qwen.py" "$RUN" \
    ".planning/spikes/006-hybrid-embedder/merged/qwen06_ties_$RUN" D-ties || exit 1
fi

# 7. Head-to-head recall (CPU).
"$TPY" "$S/eval_recall.py" "$RUN" \
  "$S/results/vecs_A_base1.json" \
  "$S/results/vecs_E_${RUN}.json" \
  "$S/results/vecs_B-minicpm2b_${RUN}.json" \
  "$S/results/vecs_B-seed999_${RUN}seed999.json" \
  "$S/results/vecs_C-minicpm2b_${RUN}.json" \
  "$S/results/vecs_D0-qwen06base_${RUN}.json" \
  "$S/results/vecs_D-w0.25_${RUN}.json" \
  "$S/results/vecs_D-w0.5_${RUN}.json" \
  "$S/results/vecs_D-w0.75_${RUN}.json" || exit 1

# 8. Generation retained (GPU, one process each; Proof on CPU inside).
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/gen_eval.py" "$RUN" minicpm_base || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/gen_eval.py" "$RUN" "minicpm_lora:adapters/lora_contrastive_$RUN" || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/gen_eval.py" "$RUN" "minicpm_lora:adapters/lora_distill_$RUN" || exit 1
flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/gen_eval.py" "$RUN" qwen06_base || exit 1
for w in 0.25 0.5 0.75; do
  flock /tmp/melodyscribe-gpu.lock "$TPY" -u "$S/gen_eval.py" "$RUN" \
    "qwen06_merged:merged/qwen06_linear_w${w}_${RUN}" || exit 1
done

echo "SPIKE-006 COMPLETE: results/recall_${RUN}.json + results/gen_*_${RUN}.json in $S"
