#!/usr/bin/env bash
# Spike 002 repro: tokenizer probe (no GPU) + one-pass GPU experiments (under lock).
# Run from the repo root: .planning/spikes/002-one-pass-runtime/run.sh
set -u
D="$(cd "$(dirname "$0")" && pwd)"
source "$D/../env.sh"   # LD_LIBRARY_PATH + MELODYSCRIBE_PY + MELODYSCRIBE_MODELS (mandatory pre-llama_cpp)
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
LOG="$D/logs/run-$STAMP.jsonl"
mkdir -p "$D/logs"

echo "== tok probe (vocab_only, no GPU, no lock) =="
"$MELODYSCRIBE_PY" "$D/tok_probe.py" 2>"$D/logs/stderr-$STAMP.log" | tee -a "$LOG" || exit 1

echo "== gpu experiments (single process, under flock) =="
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$D/one_pass.py" 2>>"$D/logs/stderr-$STAMP.log" | tee -a "$LOG" || exit 1

echo "== log: $LOG =="
echo "SPIKE-002 DONE (inspect verdicts in log)"
