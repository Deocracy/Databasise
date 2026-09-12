#!/usr/bin/env bash
# Spike 011 starts once the 006 and 009 owner-side reproductions have released the GPU.
set -u; cd "$(dirname "$0")"
until ! pgrep -f '006-hybrid-embedder/run.sh' >/dev/null && ! pgrep -f '009-batched-serving-and-cache-order/run.sh' >/dev/null; do sleep 60; done
echo "011: reproductions finished, launching $(date -Is)" >> .logs/spikes.log
./run-spike.sh 011
echo "SPIKE 011 RUNNER FINISHED $(date -Is)" >> .logs/spikes.log
