#!/usr/bin/env bash
# Spike 008: graph-prompt-design (comparison, v0.2 quote evidence).
# Reproduces everything: 8 prompt designs x 2 student arms (MiniCPM5-2B,
# Qwen3-4B Q8) on the 16 scored docs (the 4 median-op-count docs are held out
# for few-shot examples), a greedy-decode repeat probe (the noise floor under
# every design delta), then scoring with the D0-vs-003 reproduction check.
# Run from the repo root. Every model load runs under the GPU lock, one model
# per process; merge/score hold no lock (stdlib only). qwen4b runs in two
# halves (merge8.py rejoins them) so a kill loses at most half the arm.
set -u
ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
S="$ROOT/.planning/spikes/008-graph-prompt-design"
source "$ROOT/.planning/spikes/env.sh"

"$MELODYSCRIBE_PY" -c "import sys; sys.path.insert(0,'$S'); sys.path.insert(0,'$ROOT/.planning/spikes/003-op-emission-size-sweep'); import prompts, v02_grammar, resolve; from llama_cpp import LlamaGrammar; LlamaGrammar.from_string(v02_grammar.grammar_v02(), verbose=False); LlamaGrammar.from_string(prompts.entity_grammar(), verbose=False); print('008 self-check ok')" \
  || { echo "008 module/grammar self-check FAILED"; exit 1; }

# Students: one process per arm (one model per process), every load under lock.
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$S/student8.py" minicpm2b || exit 1
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$S/student8.py" qwen4b \
  --units=0,1,2,3,4,5,6,7 --suffix=_h1 || exit 1
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$S/student8.py" qwen4b \
  --units=8,9,10,11,12,13,14,15 --suffix=_h2 || exit 1
"$MELODYSCRIBE_PY" "$S/merge8.py" qwen4b _h1 _h2 || exit 1

# Repeat probe: re-decode D0 on the docs where D0 diverged from spike 003
# (plus stable controls); measures run-to-run greedy agreement, the noise
# floor under every design delta. Units index the 16-doc scored list.
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$S/probe_repeat.py" minicpm2b \
  meet_corliss_archer_tv_series,conrad_brooks,tyler_bates || exit 1
flock /tmp/melodyscribe-gpu.lock "$MELODYSCRIBE_PY" "$S/probe_repeat.py" qwen4b \
  lord_high_treasurer,meet_corliss_archer_tv_series,kiss_and_tell_1945_film,janet_waldo,conrad_brooks,tyler_bates,charles_craft || exit 1

# Score (no lock): 16-doc head-to-head + D0 reproduction check.
"$MELODYSCRIBE_PY" "$S/evaluate8.py" || exit 1

# Recommendation artifact from the winning prompt bytes (no lock, no GPU).
"$MELODYSCRIBE_PY" "$S/make_best_prompt.py" || exit 1

echo "SPIKE-008 COMPLETE: students/*.json + results.json in $S"
