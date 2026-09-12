#!/usr/bin/env bash
# Spike 010 run.sh — reproduces everything from scratch.
# CPU steps run without the lock; every model load runs under flock.
set -euo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$D/../env.sh"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$D/logs/run-$STAMP.jsonl"
mkdir -p "$D/logs" "$D/vectors" "$D/results"
echo "{\"ts\":\"$(date -u +%FT%TZ)\",\"event\":\"run_start\",\"stamp\":\"$STAMP\"}" >> "$LOG"

# 0. Score compile check on all 20 docs x both chunker variants (CPU, stdlib)
"$MELODYSCRIBE_PY" "$D/score_check.py" 2>&1 | tee -a "$LOG"

# 1. GPU: 2B one-pass whole (embed+decode, one load) + query embeds (LOCK)
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$D/gpu_ingest.py" onepass \
  --variant=whole --tag=whole 2>>"$D/logs/stderr-$STAMP.log" | tee -a "$LOG"
# 2. GPU: 2B two-pass arms (embed-only load, decode-only load) (LOCK)
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$D/gpu_ingest.py" embed2b \
  --variant=whole --tag=whole2 2>>"$D/logs/stderr-$STAMP.log" | tee -a "$LOG"
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$D/gpu_ingest.py" ops2b \
  --variant=whole --tag=whole2 2>>"$D/logs/stderr-$STAMP.log" | tee -a "$LOG"
# 3. GPU: 2B one-pass split variant (LOCK)
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$D/gpu_ingest.py" onepass \
  --variant=split --tag=split 2>>"$D/logs/stderr-$STAMP.log" | tee -a "$LOG"
# 4. GPU: 0.6B embeds of all sections + all queries (LOCK)
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$D/gpu_ingest.py" embed06 \
  --tag=all 2>>"$D/logs/stderr-$STAMP.log" | tee -a "$LOG"
# 5. GPU: worker sweep W=1,2,4,8 on 6-doc subset, one shared process (LOCK)
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$D/gpu_workers.py" \
  2>>"$D/logs/stderr-$STAMP.log" | tee -a "$LOG"

# 6. CPU: stores (streamed/batched x write/revise x STU/SPL/TEA) + faiss
"$MELODYSCRIBE_PY" "$D/build_stores.py" 2>&1 | tee -a "$LOG"
# 7. CPU: retrieval eval (all modes, payload, latency)
"$MELODYSCRIBE_PY" "$D/retrieve.py" 2>&1 | tee -a "$LOG"
# 8. CPU: worker control with stub model (harness scaling without GPU)
"$MELODYSCRIBE_PY" "$D/cpu_workers_mock.py" 2>&1 | tee -a "$LOG"
# 9. CPU: one-pass vs two-pass comparison + final report inputs
"$MELODYSCRIBE_PY" "$D/compare_passes.py" 2>&1 | tee -a "$LOG"

echo "{\"ts\":\"$(date -u +%FT%TZ)\",\"event\":\"run_done\",\"stamp\":\"$STAMP\"}" >> "$LOG"
echo "run done stamp=$STAMP log=$LOG"
