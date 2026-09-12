#!/usr/bin/env bash
# Overnight orchestration: 001 now; 002-005 once the venv proves CUDA offload and the models are down. GPU lock serialises model loads.
set -u; cd "$(dirname "$0")"
./run-spike.sh 001 &
until grep -q PREP-DONE .logs/models.out 2>/dev/null; do sleep 30; done
if grep -q 'gpu_offload: True' .logs/setup.out 2>/dev/null; then
  echo "prep done, gpu offload true: launching 002-005" >> .logs/spikes.log
  for n in 002 003 004 005; do ./run-spike.sh $n & sleep 20; done
else
  echo "GPU OFFLOAD NOT TRUE: 002-005 not launched (see .logs/setup.out)" >> .logs/spikes.log
fi
wait; echo "ALL SPIKES FINISHED" >> .logs/spikes.log
