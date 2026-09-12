#!/usr/bin/env bash
# Spike 005: kv-composition-quality. Reproduces everything.
# GPU inference runs once under the GPU lock; analysis runs without it.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"
cd "$ROOT"
source .planning/spikes/env.sh
mkdir -p .planning/spikes/005-kv-composition-quality/logs \
         .planning/spikes/005-kv-composition-quality/results
echo "=== [005] GPU run (under lock) ==="
flock /tmp/melodyscribe-gpu.lock \
  "$MELODYSCRIBE_PY" .planning/spikes/005-kv-composition-quality/kv_arms.py \
  > .planning/spikes/005-kv-composition-quality/logs/run.jsonl 2> .planning/spikes/005-kv-composition-quality/logs/stderr.log
echo "gpu_exit=$?"
echo "=== [005] analysis (no lock) ==="
"$MELODYSCRIBE_PY" .planning/spikes/005-kv-composition-quality/analyze.py
