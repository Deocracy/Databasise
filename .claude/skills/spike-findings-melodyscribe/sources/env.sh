# source this before any Python that imports llama_cpp: driver libcuda + nix-ld libstdc++ + pip CUDA runtime/cuBLAS
_SP="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_NV="$_SP/.venv/lib/python3.12/site-packages/nvidia"
export LD_LIBRARY_PATH="/run/opengl-driver/lib:/run/current-system/sw/share/nix-ld/lib:$_NV/cuda_runtime/lib:$_NV/cublas/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export MELODYSCRIBE_PY="$_SP/.venv/bin/python"
export MELODYSCRIBE_MODELS="$_SP/.models"
