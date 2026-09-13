#!/usr/bin/env bash
# usage: [MAXPAR=k] run-lanes.sh [lane numbers]  — Muse Spark 1.3 lanes, four at a time, each in its lane folder with the brief attached,
# nudge-and-retry by captured session id, then deterministic merge (integrate.py). No LLM integrator: the owner's main session assembles the report.
set -u; R=$(cd "$(dirname "$0")" && pwd); cd "$R"; mkdir -p .logs
lanes="${*:-1 2 3 4 5 6 7 8 9 10}"; M=opencode-go/muse-spark-1.3-contributor
run_lane() { local n=$1 d="$R/lanes/$1" L="$R/.logs/$1.session.log" rc sid start; start=$(date +%s)
  local msg; msg="$(cat "$R/LANE-PROMPT.md")
$(cat "$d/lane.txt")"
  cd "$d"; sid=$(grep -oE 'ses_[A-Za-z0-9]+' "$L" 2>/dev/null | head -1); rc=0
  if [ -n "$sid" ] && ! [ -s findings.md ]; then echo "lane $n: resuming session $sid" >> "$R/.logs/lanes.log"
  else timeout 5400 opencode run "$msg" --file="$R/BRIEF.md" --pure --auto --format json -m $M --title "melodyscribe-research4-lane-$n" > "$L" 2>&1; rc=$?
    sid=$(grep -oE 'ses_[A-Za-z0-9]+' "$L" | head -1); fi
  for attempt in 1 2 3; do
    if [ -s findings.md ] && [ -s inventory.tsv ] && [ -s method.md ] && grep -q "Harness implications" findings.md; then break; fi
    [ -n "$sid" ] || { echo "lane $n: no session id, retry skipped" >> "$R/.logs/lanes.log"; break; }
    timeout 2400 opencode run "$(cat "$R/NUDGE.md")" -s "$sid" --pure --auto --format json -m $M >> "$L" 2>&1; rc=$?
    echo "lane $n retry $attempt rc=$rc" >> "$R/.logs/lanes.log"
  done
  echo "lane $n rc=$rc $(( $(date +%s)-start ))s findings=$([ -s findings.md ] && echo yes || echo no) rows=$(( $(wc -l < inventory.tsv 2>/dev/null || echo 1) - 1 )) pdfs=$(ls papers/*.pdf 2>/dev/null | wc -l)" >> "$R/.logs/lanes.log"; }
for n in $lanes; do run_lane "$n" & sleep 15; while [ "$(jobs -rp | wc -l)" -ge "${MAXPAR:-4}" ]; do sleep 30; done; done
wait; echo "LANES FINISHED $(date -Is)" >> .logs/lanes.log
cd "$R"; python3 integrate.py >> .logs/lanes.log 2>&1
echo "RESEARCH4 LANES DONE $(date -Is)" >> .logs/lanes.log
