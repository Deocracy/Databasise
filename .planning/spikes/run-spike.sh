#!/usr/bin/env bash
# usage: run-spike.sh <NNN>  — runs one Muse Spark spike agent in the repo root, with nudge-and-retry. Logs to .planning/spikes/.logs/.
set -u; n=$1; ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); S="$ROOT/.planning/spikes"; d=$(ls -d "$S/$n-"* | head -1); L="$S/.logs/$n.session.log"
task="$(cat "$S/$n-"*/README.md | sed -n '1,12p')"
msg="$(cat "$S/SPIKE-AGENT-PROMPT.md")
Spike folder: ${d#$ROOT/}
$task"
cd "$ROOT"; start=$(date +%s)
timeout 7200 opencode run "$msg" --pure --auto --format json -m opencode-go/muse-spark-1.3-contributor --title "melodyscribe-spike-$n" > "$L" 2>&1; rc=$?
sid=$(grep -oE 'ses_[A-Za-z0-9]+' "$L" | head -1)
for attempt in 1 2 3; do
  v=$(grep -m1 '^verdict:' "$d/README.md" | awk '{print $2}')
  if [ -n "$v" ] && [ "$v" != "PENDING" ] && [ -f "$d/run.sh" ]; then break; fi
  if [ -n "$sid" ]; then timeout 3600 opencode run "$(cat "$S/SPIKE-NUDGE.md")" -s "$sid" --pure --auto --format json -m opencode-go/muse-spark-1.3-contributor >> "$L" 2>&1; rc=$?; else echo "spike $n: no session id captured, retry skipped" >> "$S/.logs/spikes.log"; break; fi
  echo "spike $n retry $attempt rc=$rc verdict=$(grep -m1 '^verdict:' "$d/README.md" | awk '{print $2}')" >> "$S/.logs/spikes.log"
done
echo "spike $n rc=$rc $(( $(date +%s)-start ))s verdict=$(grep -m1 '^verdict:' "$d/README.md" | awk '{print $2}') runsh=$([ -f "$d/run.sh" ] && echo yes || echo no)" >> "$S/.logs/spikes.log"
