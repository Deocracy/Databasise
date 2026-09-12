#!/usr/bin/env bash
# Batch remaining GPU steps under one lock acquisition (each step still one
# model per process). Called with flock from the tool, not run directly.
set -u
ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
S="$ROOT/.planning/spikes/006-hybrid-embedder"
source "$ROOT/.planning/spikes/env.sh"
export TRITON_LIBCUDA_PATH=/run/opengl-driver/lib HF_HUB_OFFLINE=1
TPY="$ROOT/.planning/spikes/.venv-train/bin/python"
RUN="${1:-run1}"
WHICH="${2:-all}"

if [ "$WHICH" = "all" ] || [ "$WHICH" = "embed" ]; then
  "$TPY" -u "$S/embed_lora.py" "$RUN" "adapters/lora_distill_$RUN" C-minicpm2b --proj || exit 1
  "$TPY" -u "$S/embed_qwen.py" "$RUN" ".planning/spikes/.models/hf/Qwen__Qwen3-0.6B" D0-qwen06base || exit 1
  for w in 0.25 0.5 0.75; do
    "$TPY" -u "$S/embed_qwen.py" "$RUN" \
      ".planning/spikes/006-hybrid-embedder/merged/qwen06_linear_w${w}_${RUN}" "D-w${w}" || exit 1
  done
fi

if [ "$WHICH" = "all" ] || [ "$WHICH" = "gen12" ]; then
  "$TPY" -u "$S/gen_eval.py" "$RUN" minicpm_base || exit 1
  "$TPY" -u "$S/gen_eval.py" "$RUN" "minicpm_lora:adapters/lora_contrastive_$RUN" || exit 1
  "$TPY" -u "$S/gen_eval.py" "$RUN" "minicpm_lora:adapters/lora_distill_$RUN" || exit 1
fi

if [ "$WHICH" = "all" ] || [ "$WHICH" = "gen06" ]; then
  "$TPY" -u "$S/gen_eval.py" "$RUN" qwen06_base || exit 1
  for w in 0.25 0.5 0.75; do
    "$TPY" -u "$S/gen_eval.py" "$RUN" "qwen06_merged:merged/qwen06_linear_w${w}_${RUN}" || exit 1
  done
fi
echo "BATCH $WHICH DONE"
