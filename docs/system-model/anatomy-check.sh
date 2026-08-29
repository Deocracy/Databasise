#!/usr/bin/env bash
# Structural checker for ANATOMY.md.
# Usage: bash anatomy-check.sh <expected_entry_count>
#
# Prints one "FAIL: <check name> — <observed> vs <expected>" line per failed
# check, prints "OK <n> checks" and exits 0 when all pass, exits 1 otherwise.
# A missing file is a named failure, never silently compared as zero-vs-zero.

set -u

DOC="$(dirname "$0")/ANATOMY.md"
EXPECTED="${1:-}"

if [ -z "$EXPECTED" ]; then
  echo "FAIL: usage — <expected_entry_count> argument is required" >&2
  exit 1
fi

FAILS=0
PASSES=0

fail() {
  echo "FAIL: $1 — $2 vs $3"
  FAILS=$((FAILS + 1))
}

pass() {
  PASSES=$((PASSES + 1))
}

# Check 1: file exists and is non-empty.
if [ ! -f "$DOC" ]; then
  fail "file-exists" "missing" "present"
  echo "FAIL: all remaining checks skipped — ANATOMY.md not found at $DOC"
  exit 1
fi
if [ ! -s "$DOC" ]; then
  fail "file-non-empty" "empty" "non-empty"
  echo "FAIL: all remaining checks skipped — ANATOMY.md is empty"
  exit 1
fi
pass

# Check 2: all thirteen (fourteen-item, per the plan's own list) required
# headings present, fixed-string match, in order.
HEADINGS=(
  "# Machine Anatomy and Component Inventory"
  "## Reading order"
  "## Conventions"
  "## §A — The two planes"
  "### §A.1 — Standing rules"
  "### §A.2 — Plane-value legend"
  "### §A.3 — Crossing catalogue (open)"
  "### §A.4 — Boundary table"
  "## §B — The machine, drawn"
  "## §C — Boundary types"
  "## §D — Component inventory"
  "## §E — What a part may call, per machine service"
  "## §F — Defect register"
  "## Appendix A — ANATOMY-REVIEW disposition"
)
LAST_LINE=0
HEADINGS_OK=1
for h in "${HEADINGS[@]}"; do
  LINE=$(grep -nF -- "$h" "$DOC" | head -1 | cut -d: -f1)
  if [ -z "$LINE" ]; then
    fail "heading-present" "missing: $h" "present"
    HEADINGS_OK=0
    continue
  fi
  if [ "$LINE" -le "$LAST_LINE" ]; then
    fail "heading-order" "$h at line $LINE" "after line $LAST_LINE"
    HEADINGS_OK=0
  fi
  LAST_LINE="$LINE"
done
[ "$HEADINGS_OK" -eq 1 ] && pass

# Check 3: per-field line counts equal the expected entry count.
count_prefix() {
  grep -cE "^$1 " "$DOC" || true
}
PLANE_N=$(count_prefix "Plane:")
CROSSINGS_N=$(count_prefix "Crossings:")
ACCEPTS_N=$(count_prefix "Accepts:")
EMITS_N=$(count_prefix "Emits:")
ENTRY_N=$(grep -cE '^### [0-9]+\. `' "$DOC" || true)

[ "$PLANE_N" -eq "$EXPECTED" ] && pass || fail "plane-count" "$PLANE_N" "$EXPECTED"
[ "$CROSSINGS_N" -eq "$EXPECTED" ] && pass || fail "crossings-count" "$CROSSINGS_N" "$EXPECTED"
[ "$ACCEPTS_N" -eq "$EXPECTED" ] && pass || fail "accepts-count" "$ACCEPTS_N" "$EXPECTED"
[ "$EMITS_N" -eq "$EXPECTED" ] && pass || fail "emits-count" "$EMITS_N" "$EXPECTED"
[ "$ENTRY_N" -eq "$EXPECTED" ] && pass || fail "entry-heading-count" "$ENTRY_N" "$EXPECTED"

# Check 4: every Plane: line's value is one of the five legend values.
BAD_PLANE=$(grep -E '^Plane: ' "$DOC" | sed -E 's/^Plane: //' | awk '{print $1}' \
  | grep -vE '^(artifact|execution|both|outside|—)$' | wc -l | tr -d ' ')
[ "$BAD_PLANE" -eq 0 ] && pass || fail "plane-value-vocabulary" "$BAD_PLANE bad" "0"

# Check 5: no Crossings: line reads a bare "none".
BAD_CROSSINGS=$(grep -E '^Crossings: none$' "$DOC" | wc -l | tr -d ' ')
[ "$BAD_CROSSINGS" -eq 0 ] && pass || fail "crossings-bare-none" "$BAD_CROSSINGS" "0"

# Check 6: every non-em-dash Plane: line carries a §-citation or names
# two-plane-separation.
BAD_PLANE_CITE=$(grep -E '^Plane: ' "$DOC" | grep -vE '^Plane: —' \
  | grep -vE '§[0-9]|two-plane-separation' | wc -l | tr -d ' ')
[ "$BAD_PLANE_CITE" -eq 0 ] && pass || fail "plane-citation" "$BAD_PLANE_CITE" "0"

# Check 7: every Plane: and Crossings: line carries a claim tag.
BAD_TAGGED=$(grep -E '^(Plane|Crossings): ' "$DOC" \
  | grep -vcE '\[(code-verified|docs-verified|paper-claim|inference)\]')
[ "$BAD_TAGGED" -eq 0 ] && pass || fail "claim-tag-presence" "$BAD_TAGGED" "0"

# Check 8: all six D-10 glossary type names present.
GLOSSARY_TYPES=("ScoredItem" "Score" "ChunkRef" "ItemKind" "ContextPackage" "Answer")
GLOSSARY_OK=1
for t in "${GLOSSARY_TYPES[@]}"; do
  grep -qF -- "$t" "$DOC" || { fail "glossary-type-present" "missing: $t" "present"; GLOSSARY_OK=0; }
done
[ "$GLOSSARY_OK" -eq 1 ] && pass

# Check 9: Kind-column counts in §A.4.
BINDS_N=$(grep -cF '| BINDS |' "$DOC" || true)
ENCLOSES_N=$(grep -cF '| ENCLOSES |' "$DOC" || true)
FANIN_N=$(grep -cF '| FAN-IN |' "$DOC" || true)
[ "$BINDS_N" -ge 2 ] && pass || fail "binds-count" "$BINDS_N" ">=2"
[ "$ENCLOSES_N" -eq 6 ] && pass || fail "encloses-count" "$ENCLOSES_N" "6"
[ "$FANIN_N" -eq 5 ] && pass || fail "fanin-count" "$FANIN_N" "5"

# Check 10: §D legend has exactly 44 rows.
LEGEND_N=$(grep -cE '^\| [0-9]+ \| ' "$DOC" || true)
[ "$LEGEND_N" -eq 44 ] && pass || fail "legend-row-count" "$LEGEND_N" "44"

# Check 11: exactly six **Satisfies:** lines (one per ## §A .. ## §F section).
SATISFIES_N=$(grep -cF '**Satisfies:**' "$DOC" || true)
[ "$SATISFIES_N" -eq 6 ] && pass || fail "satisfies-count" "$SATISFIES_N" "6"

# Check 12: three-way edge-consistency across §A.4's boundary table and §D's
# entries (D-09's accepted cost, made mechanical). For every `call` row,
# resolves From/To (expanding the STORES/APICL aggregates), asserts the
# From entry's Emits: line names the To id, the To entry's Accepts: line
# names the From id, and a keyword from the row's What-crosses cell appears
# on both lines. Non-call rows (BINDS/ENCLOSES/FAN-IN) are checked more
# weakly: both ids must resolve to real entries and at least one of the two
# entries must mention the row's Kind word. An unresolvable id is a named
# failure, never a skipped or vacuously-passing row.
if ! command -v python3 >/dev/null 2>&1; then
  fail "edge-consistency" "python3 not found" "available"
else
  EDGE_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys

DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

entries = {}
pat = re.compile(r'^### \d+\. `([^`]+)`.*?\n(.*?)(?=\n### \d+\.|\n## §E)', re.S | re.M)
for m in pat.finditer(text):
    entries[m.group(1)] = m.group(2)

table_m = re.search(r'^### §A\.4.*?\n(.*?)\n## §B', text, re.S | re.M)
if not table_m:
    print("FAIL: edge-consistency <table> -> <table> — §A.4 boundary table not found")
    sys.exit(1)

rows = []
for line in table_m.group(1).splitlines():
    line = line.strip()
    if not line.startswith('|'):
        continue
    cells = [c.strip() for c in line.strip('|').split('|')]
    if len(cells) != 5:
        continue
    if cells[0] in ('From',) or set(cells[0]) <= {'-'}:
        continue
    rows.append(cells)

AGGREGATES = {
    'STORES': ['KV', 'VEC', 'GR', 'LEX', 'BLOB'],
    'APICL': ['IDX', 'QRY'],
}

def extract_ids(cell):
    for agg, members in AGGREGATES.items():
        if re.match(r'^`?' + agg, cell):
            return members
    return re.findall(r'`([A-Za-z0-9_/.\-]+)`', cell)

STOPWORDS = {"the","a","an","and","or","to","from","of","in","on","at","for",
             "with","its","this","that","per","each","plus","is","are","as",
             "into","by","not","no","none","own","row","§a","already"}

def tokens(s):
    s = s.replace('`', ' ')
    words = re.findall(r"[A-Za-z][A-Za-z0-9]*", s)
    return {w.lower() for w in words if w.lower() not in STOPWORDS and len(w) > 1}

def field(entry_body, field_name):
    m = re.search(r'^' + field_name + r': (.*)$', entry_body, re.M)
    return m.group(1) if m else ''

fails = []
n_checked = 0
for cells in rows:
    from_cell, to_cell, crosses, kind, clause = cells
    from_ids = extract_ids(from_cell)
    to_ids = extract_ids(to_cell)
    label = f"{from_cell} -> {to_cell}"
    if not from_ids or not to_ids:
        fails.append(f"{label} — unresolved id in From/To cell")
        continue
    missing = [i for i in from_ids + to_ids if i not in entries]
    if missing:
        fails.append(f"{label} — unresolved id(s): {missing}")
        continue
    n_checked += 1
    if kind == 'call':
        for fid in from_ids:
            emi = field(entries[fid], 'Emits')
            if not any(f'`{tid}`' in emi for tid in to_ids):
                fails.append(f"{label} — {fid}'s Emits does not name {to_ids}")
        for tid in to_ids:
            acc = field(entries[tid], 'Accepts')
            if not any(f'`{fid}`' in acc for fid in from_ids):
                fails.append(f"{label} — {tid}'s Accepts does not name {from_ids}")
        cross_tokens = tokens(crosses)
        if cross_tokens:
            emi_all = ' '.join(field(entries[fid], 'Emits') for fid in from_ids)
            acc_all = ' '.join(field(entries[tid], 'Accepts') for tid in to_ids)
            if not (cross_tokens & tokens(emi_all)):
                fails.append(f"{label} — What-crosses keyword not found in Emits")
            if not (cross_tokens & tokens(acc_all)):
                fails.append(f"{label} — What-crosses keyword not found in Accepts")
    else:
        found = any(kind in entries[i] for i in from_ids + to_ids)
        if not found:
            fails.append(f"{label} — neither entry mentions '{kind}'")

if fails:
    for f in fails:
        print(f"FAIL: edge-consistency {f}")
    sys.exit(1)
else:
    print(f"edge-consistency OK ({n_checked} rows)")
    sys.exit(0)
PYEOF
)
  EDGE_STATUS=$?
  if [ "$EDGE_STATUS" -eq 0 ]; then
    pass
  else
    echo "$EDGE_OUT"
    FAILCOUNT=$(printf '%s\n' "$EDGE_OUT" | grep -cE '^FAIL: edge-consistency' || true)
    [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
    FAILS=$((FAILS + FAILCOUNT))
  fi
fi

# Checks 13-15: Appendix A's twenty-row ANATOMY-REVIEW disposition table.
# Extract the appendix's `| #N | ...` rows only (the summary table, not the
# reasoning-block prose below it, which also uses `**#N.**` headers).
APPENDIX_ROWS=$(awk '/^## Appendix A/,0' "$DOC" | grep -E '^\| #[0-9]+ \|' || true)

# Check 13: exactly twenty rows keyed #1..#20, no duplicate, no gap.
APPENDIX_NUMS=$(printf '%s\n' "$APPENDIX_ROWS" | sed -E 's/^\| #([0-9]+) \|.*/\1/')
APPENDIX_ROW_N=$(printf '%s\n' "$APPENDIX_ROWS" | grep -c '.' || true)
EXPECTED_SET=$(seq 1 20)
ACTUAL_SORTED=$(printf '%s\n' "$APPENDIX_NUMS" | sort -n | tr -d ' ')
if [ "$APPENDIX_ROW_N" -eq 20 ] && [ "$ACTUAL_SORTED" = "$EXPECTED_SET" ]; then
  pass
else
  fail "appendix-row-count-and-keys" "$APPENDIX_ROW_N rows, keys [$(printf '%s' "$APPENDIX_NUMS" | tr '\n' ',')]" "20 rows, keys 1..20 no dup/gap"
fi

# Check 14: rows appear in ascending numeric order (not merely a matching set).
ASCENDING=1
PREV=0
while IFS= read -r n; do
  [ -z "$n" ] && continue
  if [ "$n" -le "$PREV" ]; then
    ASCENDING=0
  fi
  PREV="$n"
done <<< "$APPENDIX_NUMS"
[ "$ASCENDING" -eq 1 ] && pass || fail "appendix-ascending-order" "out of order" "strictly ascending #1..#20"

# Check 15: every row's Status cell holds one of the three vocabulary values;
# every rejection row's Status cell also carries a SELECTION or §-prefixed
# citation in the same cell.
BAD_STATUS=0
BAD_REJECTION=0
while IFS= read -r row; do
  [ -z "$row" ] && continue
  # Column 4 (1-indexed after the leading empty split) is Status.
  STATUS_CELL=$(printf '%s' "$row" | awk -F'|' '{print $5}' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  case "$STATUS_CELL" in
    "fixed by contract construction"|"fixed in this anatomy") ;;
    rejected*)
      if ! printf '%s' "$STATUS_CELL" | grep -qE 'SELECTION|§[0-9]'; then
        BAD_REJECTION=$((BAD_REJECTION + 1))
      fi
      ;;
    *) BAD_STATUS=$((BAD_STATUS + 1)) ;;
  esac
done <<< "$APPENDIX_ROWS"
[ "$BAD_STATUS" -eq 0 ] && pass || fail "appendix-status-vocabulary" "$BAD_STATUS bad" "0"
[ "$BAD_REJECTION" -eq 0 ] && pass || fail "appendix-rejection-citation" "$BAD_REJECTION missing SELECTION/§ citation" "0"

if [ "$FAILS" -eq 0 ]; then
  echo "OK $PASSES checks"
  exit 0
else
  echo "FAIL: $FAILS check(s) failed, $PASSES passed"
  exit 1
fi
