#!/usr/bin/env bash
# Structural checker for PARTS.md.
# Usage: bash parts-check.sh
#
# Unlike anatomy-check.sh, this script takes no expected-count argument: per
# D-02 its checks are per-row content checks, not counts against an external
# argument.
#
# Prints one "FAIL: <check name> — <observed> vs <expected>" line per failed
# check, prints "OK <n> checks" and exits 0 when all pass, exits 1 otherwise.
# A missing file is a named failure, never silently compared as zero-vs-zero.

set -u

DOC="$(dirname "$0")/PARTS.md"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

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
  echo "FAIL: all remaining checks skipped — PARTS.md not found at $DOC"
  exit 1
fi
if [ ! -s "$DOC" ]; then
  fail "file-non-empty" "empty" "non-empty"
  echo "FAIL: all remaining checks skipped — PARTS.md is empty"
  exit 1
fi
pass

# Check 2: all nine required headings present, fixed-string match, in order.
HEADINGS=(
  "# Part Anatomy — Three Stress Modalities"
  "## Reading order"
  "## Conventions"
  "## §L — LightRAG (native)"
  "## §H — HippoRAG 2 (declared-capability path)"
  "## §X — codebase-memory-mcp (opaque admission)"
  "## §R — Repair register"
  "## §P — Per-modality port cost"
  "## Appendix A — ANATOMY.md §F disposition (DR-01..DR-12)"
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

# Fourteen entry-field names fixed in ## Conventions. Comment lines (the
# script's own header) are filtered out of DOC scans below, but PARTS.md
# carries no comment lines of its own — the filter exists so this script's
# checks are never satisfied or invalidated by its own prose about itself.
FIELD_RE='^(Contract|Entry path|Node set|Declared capabilities|effects\[\]|Artifact scopes|Recipe|Arms|Admission|Port cost class|Advantages retained at entry|Advantages decomposition would earn|Crossings|Illustrative JSON): '

# Check 3: every entry-field line carries one of the four claim tags.
FIELD_LINES=$(grep -vE '^#' "$DOC" | grep -E "$FIELD_RE" || true)
BAD_CLAIM=0
if [ -n "$FIELD_LINES" ]; then
  BAD_CLAIM=$(printf '%s\n' "$FIELD_LINES" | grep -vcE '\[(code-verified|docs-verified|paper-claim|inference)\]' || true)
fi
[ "$BAD_CLAIM" -eq 0 ] && pass || fail "entry-field-claim-tag" "$BAD_CLAIM bad" "0"

# Check 4: every entry-field line carries at least one trace tag.
BAD_TRACE=0
if [ -n "$FIELD_LINES" ]; then
  BAD_TRACE=$(printf '%s\n' "$FIELD_LINES" | grep -vcE '\[(CONTRACT §|CONTEXT D-|03-|PARTS-0)' || true)
fi
[ "$BAD_TRACE" -eq 0 ] && pass || fail "entry-field-trace-tag" "$BAD_TRACE bad" "0"

# Check 5: the unresolved-to-register cross-reference. A python3 sub-pass,
# modelled on anatomy-check.sh's edge-consistency check: collect every
# "unresolved — <question>" occurrence in ## §L / ## §H / ## §X, collect the
# ## §R table's row text, and fail once per unmatched occurrence (a token
# overlap heuristic, never a bare count comparison). If python3 is
# unavailable, that is a named failure, not a skip.
if ! command -v python3 >/dev/null 2>&1; then
  fail "unresolved-register-crossref" "python3 not found" "available"
else
  UNRES_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys

DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    lines = f.readlines()
text = "".join(lines)

def section(start_marker, end_marker):
    m = re.search(re.escape(start_marker) + r'.*?\n(.*?)\n' + re.escape(end_marker), text, re.S)
    return m.group(1) if m else ""

modality_text = section("## §L —", "## §R —")
register_m = re.search(re.escape("## §R —") + r'.*?\n(.*?)\n## §P —', text, re.S)
register_text = register_m.group(1) if register_m else ""

STOPWORDS = {"the","a","an","and","or","to","from","of","in","on","at","for",
             "with","its","this","that","per","each","plus","is","are","as",
             "into","by","not","no","none","own","row","already","does",
             "any","may","must","never","only","under","where","which",
             "what","when","how","carry","carries"}

def tokens(s):
    s = s.replace('`', ' ')
    words = re.findall(r"[A-Za-z][A-Za-z0-9]*", s)
    return {w.lower() for w in words if w.lower() not in STOPWORDS and len(w) > 1}

register_tokens = tokens(register_text)

fails = []
n_checked = 0
for i, line in enumerate(lines, start=1):
    if "unresolved —" not in line and "unresolved -" not in line:
        continue
    if not (line.strip().startswith(tuple(
        f + ":" for f in [
            "Contract", "Entry path", "Node set", "Declared capabilities",
            "effects[]", "Artifact scopes", "Recipe", "Arms", "Admission",
            "Port cost class", "Advantages retained at entry",
            "Advantages decomposition would earn", "Crossings",
            "Illustrative JSON",
        ]
    ))):
        continue
    field = line.split(":", 1)[0].strip()
    n_checked += 1
    q_tokens = tokens(line)
    if not (q_tokens & register_tokens):
        fails.append(f"line {i} ({field}) — no matching ## §R row found by token overlap")

if fails:
    for f in fails:
        print(f"FAIL: unresolved-register-crossref {f}")
    sys.exit(1)
else:
    print(f"unresolved-register-crossref OK ({n_checked} occurrences checked)")
    sys.exit(0)
PYEOF
)
  UNRES_STATUS=$?
  if [ "$UNRES_STATUS" -eq 0 ]; then
    pass
  else
    echo "$UNRES_OUT"
    FAILCOUNT=$(printf '%s\n' "$UNRES_OUT" | grep -cE '^FAIL: unresolved-register-crossref' || true)
    [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
    FAILS=$((FAILS + FAILCOUNT))
  fi
fi

# Checks 6-7: the Appendix A DR-01..DR-12 disposition table.
APPENDIX_ROWS=$(awk '/^## Appendix A/,0' "$DOC" | grep -E '^\| DR-[0-9]{2} \|' || true)

# Check 6: every row's Disposition cell (the fourth pipe-delimited field)
# matches one of the three D-15 vocabulary forms, checked per row — never a
# count comparison. An unreached row's reason must be non-empty.
BAD_DISPOSITION=0
while IFS= read -r row; do
  [ -z "$row" ] && continue
  DISP_CELL=$(printf '%s' "$row" | awk -F'|' '{print $4}' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  case "$DISP_CELL" in
    "repaired in §"[0-9]*) ;;
    "not reached by any exercise, because "?*) ;;
    "re-raised as DR-"[0-9][0-9]) ;;
    *) BAD_DISPOSITION=$((BAD_DISPOSITION + 1)) ;;
  esac
done <<< "$APPENDIX_ROWS"
[ "$BAD_DISPOSITION" -eq 0 ] && pass || fail "appendix-disposition-vocabulary" "$BAD_DISPOSITION bad" "0"

# Check 7: Appendix A's key set is exactly DR-01..DR-12 — twelve distinct
# ids, no duplicate, no gap.
APPENDIX_IDS=$(printf '%s\n' "$APPENDIX_ROWS" | sed -E 's/^\| (DR-[0-9]{2}) \|.*/\1/')
APPENDIX_ROW_N=$(printf '%s\n' "$APPENDIX_ROWS" | grep -c '.' || true)
EXPECTED_IDS=$(printf 'DR-%02d\n' $(seq 1 12))
ACTUAL_SORTED=$(printf '%s\n' "$APPENDIX_IDS" | sort -u)
EXPECTED_SORTED=$(printf '%s\n' "$EXPECTED_IDS" | sort -u)
if [ "$APPENDIX_ROW_N" -eq 12 ] && [ "$ACTUAL_SORTED" = "$EXPECTED_SORTED" ]; then
  pass
else
  fail "appendix-key-set" "$APPENDIX_ROW_N rows, keys [$(printf '%s' "$APPENDIX_IDS" | tr '\n' ',')]" "12 rows, keys DR-01..DR-12 no dup/gap"
fi

# Checks 8-9: the ## §R repair register table. Row ids are a letter prefix
# (R/D/H/X/N) plus digits, e.g. R1, D3, H2, X1.
REGISTER_ROWS=$(awk '/^## §R —/,/^## §P —/' "$DOC" | grep -E '^\| [A-Za-z][0-9]+ \|' || true)

# Check 8: every register row's Forcing exercise cell (6th pipe-delimited
# field) and ANATOMY re-projection cell (7th) are non-empty — a per-row loop.
BAD_REGISTER_CELLS=0
while IFS= read -r row; do
  [ -z "$row" ] && continue
  FORCING=$(printf '%s' "$row" | awk -F'|' '{print $6}' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  REPROJ=$(printf '%s' "$row" | awk -F'|' '{print $7}' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  if [ -z "$FORCING" ] || [ -z "$REPROJ" ]; then
    BAD_REGISTER_CELLS=$((BAD_REGISTER_CELLS + 1))
  fi
done <<< "$REGISTER_ROWS"
[ "$BAD_REGISTER_CELLS" -eq 0 ] && pass || fail "register-row-cells-nonempty" "$BAD_REGISTER_CELLS bad" "0"

# Check 9: register row order is ascending by defect id within each id
# family, families in the fixed order R, D, H, X, N — a per-row comparison
# against the previous row, one failure per inversion.
REGISTER_IDS=$(printf '%s\n' "$REGISTER_ROWS" | sed -E 's/^\| ([A-Za-z][0-9]+) \|.*/\1/')
if ! command -v python3 >/dev/null 2>&1; then
  fail "register-row-order" "python3 not found" "available"
else
  ORDER_OUT=$(python3 - <<PYEOF
import sys
family_order = {"R": 0, "D": 1, "H": 2, "X": 3, "N": 4}
ids = """$REGISTER_IDS""".strip().splitlines()
prev = None
fails = 0
for rid in ids:
    rid = rid.strip()
    if not rid:
        continue
    fam, num = rid[0], int(rid[1:])
    key = (family_order.get(fam, 99), num)
    if prev is not None and key <= prev:
        print(f"FAIL: register-row-order {rid} out of order")
        fails += 1
    prev = key
sys.exit(1 if fails else 0)
PYEOF
)
  ORDER_STATUS=$?
  if [ "$ORDER_STATUS" -eq 0 ]; then
    pass
  else
    echo "$ORDER_OUT"
    FAILCOUNT=$(printf '%s\n' "$ORDER_OUT" | grep -cE '^FAIL: register-row-order' || true)
    [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
    FAILS=$((FAILS + FAILCOUNT))
  fi
fi

# Check 10: every path named on an Illustrative JSON: field exists on disk
# relative to the repository root, and the file it names declares itself
# illustrative. A field whose value begins "none — " is skipped with a pass.
ILLUS_LINES=$(grep -vE '^#' "$DOC" | grep -E '^Illustrative JSON: ' || true)
BAD_ILLUS=0
if [ -n "$ILLUS_LINES" ]; then
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    VALUE=$(printf '%s' "$line" | sed -E 's/^Illustrative JSON: //')
    case "$VALUE" in
      "none — "*) continue ;;
    esac
    JPATHS=$(printf '%s' "$VALUE" | grep -oE '[A-Za-z0-9_./-]+\.json[A-Za-z.-]*')
    if [ -z "$JPATHS" ]; then
      BAD_ILLUS=$((BAD_ILLUS + 1))
      continue
    fi
    while IFS= read -r JPATH; do
      [ -z "$JPATH" ] && continue
      FULL_PATH="$REPO_ROOT/$JPATH"
      if [ ! -f "$FULL_PATH" ] || ! grep -qi 'illustrative' "$FULL_PATH"; then
        BAD_ILLUS=$((BAD_ILLUS + 1))
      fi
    done <<< "$JPATHS"
  done <<< "$ILLUS_LINES"
fi
[ "$BAD_ILLUS" -eq 0 ] && pass || fail "illustrative-json-exists" "$BAD_ILLUS bad" "0"

# Check 11: every ## §L / ## §H / ## §X / ## §P / ## §R heading carries a
# **Satisfies:** line naming at least one PARTS-0N id.
SATISFIES_HEADINGS=(
  "## §L — LightRAG (native)"
  "## §H — HippoRAG 2 (declared-capability path)"
  "## §X — codebase-memory-mcp (opaque admission)"
  "## §R — Repair register"
  "## §P — Per-modality port cost"
)
BAD_SATISFIES=0
TOTAL_LINES=$(wc -l < "$DOC")
for h in "${SATISFIES_HEADINGS[@]}"; do
  LINE=$(grep -nF -- "$h" "$DOC" | head -1 | cut -d: -f1)
  if [ -z "$LINE" ]; then
    BAD_SATISFIES=$((BAD_SATISFIES + 1))
    continue
  fi
  WINDOW_END=$((LINE + 6))
  [ "$WINDOW_END" -gt "$TOTAL_LINES" ] && WINDOW_END="$TOTAL_LINES"
  WINDOW=$(sed -n "${LINE},${WINDOW_END}p" "$DOC")
  if ! printf '%s' "$WINDOW" | grep -qE '\*\*Satisfies:\*\*.*PARTS-0[0-9]'; then
    BAD_SATISFIES=$((BAD_SATISFIES + 1))
  fi
done
[ "$BAD_SATISFIES" -eq 0 ] && pass || fail "section-satisfies-line" "$BAD_SATISFIES missing" "0"

# Check 12: PARTS.md contains the governance sentence fixed in preamble
# clause (b).
if grep -qF 'the tagged entries govern; the JSON wiring documents are evidence the entries cite' "$DOC"; then
  pass
else
  fail "governance-sentence" "missing" "present"
fi

# Check 13: no stub markers.
STUB_N=$(grep -cE 'TODO|TBD|placeholder|to be written' "$DOC" || true)
[ "$STUB_N" -eq 0 ] && pass || fail "no-stub-markers" "$STUB_N found" "0"

# --- Closing-sweep checks, added at plan 03-07 ---

# Check 14: every Appendix A row whose disposition takes the "not reached"
# form carries a reason of at least a stated minimum length and is not one
# of a small list of generic placeholder strings — a per-row loop.
if ! command -v python3 >/dev/null 2>&1; then
  fail "unreached-reason-quality" "python3 not found" "available"
else
  REASON_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()
m = re.search(r'^## Appendix A.*?\n(.*)\Z', text, re.S | re.M)
body = m.group(1) if m else ""
GENERIC = {
    "no exercise reached it",
    "not reached",
    "no evidence available",
    "no evidence",
    "unreached",
    "not applicable",
    "n/a",
}
MIN_LEN = 40
fails = []
n_checked = 0
for line in body.splitlines():
    line = line.strip()
    if not line.startswith("| DR-"):
        continue
    cells = [c.strip() for c in line.strip("|").split("|")]
    if len(cells) < 3:
        continue
    dr_id, disposition = cells[0], cells[2]
    if not disposition.startswith("not reached by any exercise, because"):
        continue
    n_checked += 1
    reason = disposition.split("because", 1)[1].strip()
    reason_norm = reason.rstrip(".").strip().lower()
    if len(reason) < MIN_LEN:
        fails.append(f"{dr_id} - reason too short ({len(reason)} chars)")
    if reason_norm in GENERIC:
        fails.append(f"{dr_id} - reason is a generic placeholder: {reason!r}")
if fails:
    for f in fails:
        print(f"FAIL: unreached-reason-quality {f}")
    sys.exit(1)
else:
    print(f"unreached-reason-quality OK ({n_checked} rows checked)")
    sys.exit(0)
PYEOF
)
  REASON_STATUS=$?
  if [ "$REASON_STATUS" -eq 0 ]; then
    pass
  else
    echo "$REASON_OUT"
    FAILCOUNT=$(printf '%s\n' "$REASON_OUT" | grep -cE '^FAIL: unreached-reason-quality' || true)
    [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
    FAILS=$((FAILS + FAILCOUNT))
  fi
fi

# Check 15: every ## §R row's Status cell (8th pipe-delimited field) is
# non-empty, and where it names a clause (a "§N" token), that clause string
# appears somewhere in CONTRACT.md — a dangling repair is a named failure.
BAD_STATUS_CELLS=0
while IFS= read -r row; do
  [ -z "$row" ] && continue
  STATUS=$(printf '%s' "$row" | awk -F'|' '{print $8}' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  if [ -z "$STATUS" ]; then
    BAD_STATUS_CELLS=$((BAD_STATUS_CELLS + 1))
    continue
  fi
  CLAUSES=$(printf '%s' "$STATUS" | grep -oE '§[0-9]+(\.[0-9]+)*' || true)
  if [ -n "$CLAUSES" ]; then
    while IFS= read -r CLAUSE; do
      [ -z "$CLAUSE" ] && continue
      if ! grep -qF "$CLAUSE" "$(dirname "$0")/CONTRACT.md"; then
        BAD_STATUS_CELLS=$((BAD_STATUS_CELLS + 1))
      fi
    done <<< "$CLAUSES"
  fi
done <<< "$REGISTER_ROWS"
[ "$BAD_STATUS_CELLS" -eq 0 ] && pass || fail "register-status-clause-exists" "$BAD_STATUS_CELLS bad" "0"

# Check 16: every field name used at column 1 inside ## §L / ## §H / ## §X
# appears in the ## Conventions field list, and every field in that list is
# used by at least one entry — a two-way per-field check, never a count.
if ! command -v python3 >/dev/null 2>&1; then
  fail "field-list-consistency" "python3 not found" "available"
else
  FIELD_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

conv_m = re.search(r'^## Conventions.*?\n(.*?)\n## §L', text, re.S | re.M)
conv_body = conv_m.group(1) if conv_m else ""
declared = set(re.findall(r'\*\*`([^`]+):`\*\*', conv_body))

body_m = re.search(r'^## §L.*?\n(.*?)\n## §R', text, re.S | re.M)
body = body_m.group(1) if body_m else ""
FIELD_NAMES = [
    "Contract", "Entry path", "Node set", "Declared capabilities",
    "effects[]", "Artifact scopes", "Recipe", "Arms", "Admission",
    "Port cost class", "Advantages retained at entry",
    "Advantages decomposition would earn", "Crossings", "Illustrative JSON",
]
used = set()
for line in body.splitlines():
    for name in FIELD_NAMES:
        if line.startswith(name + ":"):
            used.add(name)

fails = []
for name in used:
    if name not in declared:
        fails.append(f"used but not in ## Conventions field list: {name!r}")
for name in declared:
    if name not in used and name in FIELD_NAMES:
        fails.append(f"in ## Conventions field list but never used: {name!r}")

if fails:
    for f in fails:
        print(f"FAIL: field-list-consistency {f}")
    sys.exit(1)
else:
    print(f"field-list-consistency OK ({len(used)} fields checked)")
    sys.exit(0)
PYEOF
)
  FIELD_STATUS=$?
  if [ "$FIELD_STATUS" -eq 0 ]; then
    pass
  else
    echo "$FIELD_OUT"
    FAILCOUNT=$(printf '%s\n' "$FIELD_OUT" | grep -cE '^FAIL: field-list-consistency' || true)
    [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
    FAILS=$((FAILS + FAILCOUNT))
  fi
fi

# Check 17: every ## §P row has a non-empty cell in every column — a per-row,
# per-cell loop, distinct from the whitespace-only-cell grep this plan's own
# Task 2 verify ran once; kept here so it stays proven on every future edit.
PSECTION=$(awk '/^## §P /,/^## Appendix A/' "$DOC")
PROWS=$(printf '%s\n' "$PSECTION" | grep -E '^\| (LightRAG|HippoRAG 2|codebase-memory-mcp) \|' || true)
BAD_P_CELLS=0
while IFS= read -r row; do
  [ -z "$row" ] && continue
  N=$(printf '%s' "$row" | awk -F'|' '{print NF}')
  i=2
  while [ "$i" -lt "$N" ]; do
    CELL=$(printf '%s' "$row" | awk -F'|' -v i="$i" '{print $i}' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
    [ -z "$CELL" ] && BAD_P_CELLS=$((BAD_P_CELLS + 1))
    i=$((i + 1))
  done
done <<< "$PROWS"
[ "$BAD_P_CELLS" -eq 0 ] && pass || fail "p-section-no-empty-cells" "$BAD_P_CELLS bad" "0"

# Check 18: every modality entry's `Port cost class:` value appears in that
# modality's ## §P row Class cell (the last pipe-delimited column).
BAD_CLASS_MATCH=0
for pair in "LightRAG:§L" "HippoRAG 2:§H" "codebase-memory-mcp:§X"; do
  MNAME="${pair%%:*}"
  MTAG="${pair##*:}"
  ENTRY_CLASS=$(awk -v tag="## $MTAG " 'index($0, tag)==1{found=1} found && /^Port cost class:/{print; exit}' "$DOC" \
    | sed -E 's/^Port cost class: //' | grep -oE '\*\*[^*]+\*\*' | head -1 | sed -E 's/^\*\*//; s/\*\*$//')
  ROW_CLASS=$(printf '%s\n' "$PROWS" | grep -E "^\| $MNAME \|" | awk -F'|' '{print $(NF-1)}' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')
  if [ -z "$ENTRY_CLASS" ] || [ -z "$ROW_CLASS" ] || [ "$ENTRY_CLASS" != "$ROW_CLASS" ]; then
    BAD_CLASS_MATCH=$((BAD_CLASS_MATCH + 1))
  fi
done
[ "$BAD_CLASS_MATCH" -eq 0 ] && pass || fail "port-cost-class-consistency" "$BAD_CLASS_MATCH bad" "0"

if [ "$FAILS" -eq 0 ]; then
  echo "OK $PASSES checks"
  exit 0
else
  echo "FAIL: $FAILS check(s) failed, $PASSES passed"
  exit 1
fi
