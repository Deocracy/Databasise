#!/usr/bin/env bash
# Spike 012 (harness module + dataset), then 013 (train through the harness) once 012 has a dataset and a non-INVALIDATED verdict.
# usage: DOC_BUDGET=300 ./launch-012.sh    (DOC_BUDGET is the owner's decision; no default here on purpose)
set -u; cd "$(dirname "$0")"
: "${DOC_BUDGET:?set DOC_BUDGET (teacher document budget) before launching 012}"
export DOC_BUDGET
until ! pgrep -f 'spikes/0[0-9][0-9]-[a-z-]*/run.sh' >/dev/null; do sleep 60; done
echo "012: GPU free, launching DOC_BUDGET=$DOC_BUDGET $(date -Is)" >> .logs/spikes.log
./run-spike.sh 012
v=$(grep -m1 '^verdict:' 012-harness-module-and-dataset/README.md | awk '{print $2}')
if [ "$v" != "INVALIDATED" ] && [ -f 012-harness-module-and-dataset/dataset/MANIFEST.json ]; then
  echo "013: 012 verdict=$v with dataset, launching $(date -Is)" >> .logs/spikes.log
  ./run-spike.sh 013
else
  echo "013: not launched (012 verdict=$v, dataset=$([ -f 012-harness-module-and-dataset/dataset/MANIFEST.json ] && echo yes || echo no)) $(date -Is)" >> .logs/spikes.log
fi
echo "SPIKE 012/013 RUNNER FINISHED $(date -Is)" >> .logs/spikes.log
