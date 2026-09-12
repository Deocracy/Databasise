#!/usr/bin/env bash
# One shared environment for the MelodyScribe spikes: Python 3.12 venv with a prebuilt CUDA llama-cpp-python wheel.
# No NixOS change: nix-ld plus the driver's libcuda cover the wheel. Re-runnable.
set -u; cd "$(dirname "$0")"

[ -d .venv ] || uv venv --python 3.12 .venv
for idx in cu125 cu124 cu123 cu122 cu121; do
  if uv pip install --python .venv/bin/python --extra-index-url "https://abetlen.github.io/llama-cpp-python/whl/$idx" "llama-cpp-python" 2>>.logs/setup.log; then echo "installed llama-cpp-python from $idx"; break; fi
done
uv pip install --python .venv/bin/python numpy faiss-cpu httpx jsonschema "nvidia-cuda-runtime-cu12==12.5.*" "nvidia-cublas-cu12==12.5.*" 2>>.logs/setup.log
source ./env.sh
.venv/bin/python - <<'PY'
import llama_cpp
print("llama_cpp", llama_cpp.__version__, "gpu_offload:", llama_cpp.llama_supports_gpu_offload())
PY
