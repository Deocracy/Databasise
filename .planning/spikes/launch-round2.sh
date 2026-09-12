#!/usr/bin/env bash
# Round 2 orchestration: 007/008/010 once the shared query set exists; 006/009 once the training venv proves CUDA and the
# HF weights are down. GPU lock serialises model loads. Logs in .logs/spikes.log.
set -u; cd "$(dirname "$0")"
until grep -q QUERIES-DONE .logs/queries.out 2>/dev/null; do sleep 30; done
echo "round2: queries ready: launching 007 008 010" >> .logs/spikes.log
for n in 007 008 010; do ./run-spike.sh $n & sleep 20; done
until grep -q PREP2-DONE .logs/prep2.out 2>/dev/null; do sleep 60; done
if grep -q 'cuda: True' .logs/setup-train.out 2>/dev/null && grep -q HF-WEIGHTS-DONE .logs/hf-weights.out 2>/dev/null; then
  echo "round2: train venv cuda true, weights down: launching 006 009" >> .logs/spikes.log
  for n in 006 009; do ./run-spike.sh $n & sleep 20; done
else
  echo "round2: TRAIN PREP NOT CLEAN (see .logs/setup-train.out, .logs/hf-weights.out): 006 009 not launched" >> .logs/spikes.log
fi
wait; echo "ROUND2 SPIKES FINISHED $(date -Is)" >> .logs/spikes.log
