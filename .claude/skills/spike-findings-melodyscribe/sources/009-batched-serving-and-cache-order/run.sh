#!/usr/bin/env bash
# Spike 009 repro: serving paths in order, then workloads, then analysis.
# Run from the repo root: .planning/spikes/009-batched-serving-and-cache-order/run.sh
# Every model load runs under flock; analysis is CPU-only (no lock).
set -u
D="$(cd "$(dirname "$0")" && pwd)"
source "$D/../env.sh"   # LD_LIBRARY_PATH + MELODYSCRIBE_PY + MELODYSCRIBE_MODELS (mandatory pre-llama_cpp)
mkdir -p "$D/logs" "$D/results"

echo "== env record =="
{
  echo -n '{"gpu":"'; nvidia-smi --query-gpu=name --format=csv,noheader | head -1 | tr -d '\n'
  echo -n '","vram_mib":'; nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1 | tr -d '\n'
  echo -n ',"driver":"'; nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1 | tr -d '\n'
  echo -n '","llama_cpp":"'; "$MELODYSCRIBE_PY" -c "import llama_cpp; print(llama_cpp.__version__)" | tr -d '\n'
  echo -n '","2b_sha":"'; sha256sum "$MELODYSCRIBE_MODELS/MiniCPM5-2B-Q8_0.gguf" | cut -d' ' -f1 | tr -d '\n'
  echo -n '","06b_sha":"'; sha256sum "$MELODYSCRIBE_MODELS/Qwen3-Embedding-0.6B-Q8_0.gguf" | cut -d' ' -f1 | tr -d '\n'
  echo '"}'
} > "$D/logs/env.json"
cat "$D/logs/env.json"

echo "== tokstats: token fractions (CPU vocab-only, no lock, no GPU) =="
"$MELODYSCRIBE_PY" "$D/tokstats.py" > /dev/null || exit 1

echo "== probe: single-request sizing (GPU, under flock) =="
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$D/probe.py" 2>"$D/logs/stderr.log" | tee "$D/logs/probe.jsonl" || exit 1

echo "== verify: scheduler == public path (GPU, under flock) =="
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$D/verify.py" 2>>"$D/logs/stderr.log" > "$D/logs/verify.out" || exit 1
cat "$D/logs/verify.out"

echo "== sweep: ingest matrix, both schedulers (GPU, under flock, long) =="
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$D/sweep.py" 2>>"$D/logs/stderr.log" > "$D/logs/sweep.out" || exit 1
cat "$D/logs/sweep.out"

echo "== cache order (GPU, under flock) =="
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$D/cacheorder.py" 2>>"$D/logs/stderr.log" > "$D/logs/cacheorder.out" || exit 1
cat "$D/logs/cacheorder.out"

echo "== retrieval sweep (GPU, under flock) =="
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$D/retrieve.py" 2>>"$D/logs/stderr.log" > "$D/logs/retrieve.out" || exit 1
cat "$D/logs/retrieve.out"

echo "== vllm path (serving path 2 of the plan) =="
export HF_HUB_OFFLINE=1 HF_OFFLINE=1  # local safetensors only, never the Hub
if [ -x "$D/../.venv-vllm/bin/python" ] && "$D/../.venv-vllm/bin/python" -c "import vllm" 2>/dev/null; then
  echo "vllm imports; attempting offline benchmark (log: logs/vllm-run.err)"
  if flock /tmp/melodyscribe-gpu.lock "$D/../.venv-vllm/bin/python" "$D/vllm_bench.py" > "$D/logs/vllm.out" 2> "$D/logs/vllm-run.err"; then
    echo '{"event":"vllm_path","ok":true,"note":"see logs/vllm.jsonl"}' > "$D/logs/vllm.json"
  else
    echo "vllm bench failed (see logs/vllm-run.err); recording outcome"
    "$MELODYSCRIBE_PY" -c "import json; json.dump({'event':'vllm_path','ok':False,'installed':'imports','engine':'FAILED: see logs/vllm-run.err (this rig: triton needs /sbin/ldconfig, absent on NixOS)','llama_server':'no binary on PATH; skipped with reason'}, open('$D/logs/vllm.json','w'), indent=1)"
  fi
  cat "$D/logs/vllm.out" 2>/dev/null | tail -2
else
  echo "vllm not installed (see logs/vllm-attempt.log); path 2 recorded as failed"
  echo '{"event":"vllm_path","ok":false,"installed":false}' > "$D/logs/vllm.json"
  cp "$D/../vllm-attempt.log" "$D/logs/vllm-attempt.log" 2>/dev/null || true
fi

echo "== analyze (CPU, no lock) =="
"$MELODYSCRIBE_PY" "$D/analyze.py" || exit 1

echo "SPIKE-009 DONE (inspect results/summary.md)"
