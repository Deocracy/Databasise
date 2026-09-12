#!/usr/bin/env bash
# Spike 003: op-emission-size-sweep (comparison, v0.2 quote evidence).
# Reproduces everything: teacher labels (network; caller must first run
#   set -a; source v1/.env.parity; set +a
# from the repo root -- credentials are never printed or written), the
# 5-arm student sweep (one model per process, each load under the GPU
# lock), two follow-ups (chat-template confound check; 2048-cap
# sensitivity for truncated decodes), and both scorings.
# Run from the repo root. GPU steps need an idle GPU; network steps must
# NOT hold the GPU lock (they don't: only student.py loads a model).
set -u
ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
S="$ROOT/.planning/spikes/003-op-emission-size-sweep"
source "$ROOT/.planning/spikes/env.sh"

"$MELODYSCRIBE_PY" -c "import sys; sys.path.insert(0,'$S'); import v02_grammar, resolve; print('v0.2 self-check ok')" \
  || { echo "v0.2 module self-check FAILED"; exit 1; }

# 1. teacher (no GPU lock; network only). Reasoning disabled, Proof repair.
"$MELODYSCRIBE_PY" "$S/teacher.py" || exit 1

# 2. students, one process per arm, every load under the GPU lock.
for arm in minicpm1b minicpm2b qwen1p7b qwen4b qwen8b; do
  flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$S/student.py" "$arm" || exit 1
done

# 3. follow-ups (each under the lock):
# 3a. chat-template confound check: does MiniCPM-1B emit ops when prompted
#     through its own chat template instead of raw completion?
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$S/student.py" minicpm1b --chat || exit 1
# 3b. cap sensitivity: re-decode the six (arm,doc) pairs truncated at 1024
#     with max_tokens=2048. Unit indices into the sorted 20-doc corpus:
#     0=a_kiss_for_corliss 3=conrad_brooks 5=doctor_strange_2016_film
#     8=janet_waldo 12=meet_corliss_archer_tv_series 18=village_accountant
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$S/student.py" minicpm2b \
  --units=0 --max-tokens=2048 --out=minicpm2b_cap2048 || exit 1
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$S/student.py" qwen8b \
  --units=3,5,8,12,18 --max-tokens=2048 --out=qwen8b_cap2048 || exit 1

# 4. score primary (identical 1024 cap) + cap2048-merged secondary.
"$MELODYSCRIBE_PY" "$S/evaluate.py" minicpm1b minicpm2b qwen1p7b qwen4b qwen8b || exit 1
"$MELODYSCRIBE_PY" "$S/evaluate.py" minicpm1b minicpm2b qwen1p7b qwen4b qwen8b \
  --merge=qwen8b:qwen8b_cap2048 --merge=minicpm2b:minicpm2b_cap2048 \
  --out=results_cap2048.json || exit 1

echo "SPIKE-003 COMPLETE: teacher.json + students/*.json + results.json + results_cap2048.json in $S"
