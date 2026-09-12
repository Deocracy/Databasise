#!/usr/bin/env bash
# usage: resume-spike.sh <NNN>  — continue a spike agent whose session was cut (reboot, crash) on its captured session id,
# so its context survives. Falls back to run-spike.sh when no session id exists. Logs to .planning/spikes/.logs/.
set -u; n=$1; ROOT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel); S="$ROOT/.planning/spikes"; d=$(ls -d "$S/$n-"* | head -1); L="$S/.logs/$n.session.log"
sid=$(grep -oE 'ses_[A-Za-z0-9]+' "$L" 2>/dev/null | head -1)
[ -n "$sid" ] || { echo "spike $n: no session id, fresh start" >> "$S/.logs/spikes.log"; exec "$S/run-spike.sh" "$n"; }
msg="The machine rebooted and every process was killed, including any GPU job you had running; /tmp was cleared. The files you already wrote are still in your spike folder: check them, re-run whatever was cut short, and continue from there.
$(cat "$S/SPIKE-NUDGE.md")"
cd "$ROOT"; start=$(date +%s); rc=0
for attempt in 1 2 3 4; do
  v=$(grep -m1 '^verdict:' "$d/README.md" | awk '{print $2}')
  if [ -n "$v" ] && [ "$v" != "PENDING" ] && [ -f "$d/run.sh" ]; then break; fi
  timeout 7200 opencode run "$msg" -s "$sid" --pure --auto --format json -m opencode-go/muse-spark-1.3-contributor >> "$L" 2>&1; rc=$?
  echo "spike $n resume $attempt rc=$rc verdict=$(grep -m1 '^verdict:' "$d/README.md" | awk '{print $2}')" >> "$S/.logs/spikes.log"
done
echo "spike $n rc=$rc $(( $(date +%s)-start ))s verdict=$(grep -m1 '^verdict:' "$d/README.md" | awk '{print $2}') runsh=$([ -f "$d/run.sh" ] && echo yes || echo no)" >> "$S/.logs/spikes.log"
