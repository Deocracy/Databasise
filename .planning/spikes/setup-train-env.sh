#!/usr/bin/env bash
# Training venv for the round-2 spikes (adapters, merges, batched serving): PyTorch CUDA wheels plus
# transformers, peft, sentence-transformers. Separate from .venv so llama-cpp-python stays untouched.
# No NixOS change: nix-ld plus the driver's libcuda cover the wheels. Re-runnable.
set -u; cd "$(dirname "$0")"; mkdir -p .logs
[ -d .venv-train ] || uv venv --python 3.12 .venv-train
uv pip install --python .venv-train/bin/python torch transformers peft accelerate safetensors huggingface_hub sentence-transformers numpy faiss-cpu httpx jsonschema datasets 2>>.logs/setup-train.log
uv pip install --python .venv-train/bin/python mergekit 2>>.logs/setup-train.log || echo "mergekit install failed (optional; see .logs/setup-train.log)"
source ./env.sh
.venv-train/bin/python - <<'PY'
import torch, transformers, peft
print("torch", torch.__version__, "cuda:", torch.cuda.is_available(), "device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else None)
print("transformers", transformers.__version__, "peft", peft.__version__)
PY
