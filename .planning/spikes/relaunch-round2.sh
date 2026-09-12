#!/usr/bin/env bash
# After the 2026-09-12 reboot: resume 007/008/010 on their sessions, finish the training venv, then launch 006/009.
set -u; cd "$(dirname "$0")"; echo "round2 relaunch after reboot $(date -Is)" >> .logs/spikes.log
for n in 007 008 010; do ./resume-spike.sh $n & sleep 20; done
./setup-train-env.sh > .logs/setup-train.out 2>&1; echo "TRAIN-ENV-EXIT $?" >> .logs/setup-train.out
if grep -q 'cuda: True' .logs/setup-train.out && grep -q HF-WEIGHTS-DONE .logs/hf-weights.out; then
  echo "round2: train venv cuda true, weights down: launching 006 009" >> .logs/spikes.log
  for n in 006 009; do ./run-spike.sh $n & sleep 20; done
else
  echo "round2: TRAIN PREP NOT CLEAN (see .logs/setup-train.out, .logs/hf-weights.out): 006 009 not launched" >> .logs/spikes.log
fi
wait; echo "ROUND2 SPIKES FINISHED $(date -Is)" >> .logs/spikes.log
