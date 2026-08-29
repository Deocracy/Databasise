#!/usr/bin/env bash
# Structural checker for CATALOG.md.
# Usage: bash catalog-check.sh
#
# Per-row content checks, never row-count checks (Phase 3 D-02 precedent).
# Prints one "FAIL: <check name> — <observed> vs <expected>" line per failed
# check, prints "OK <n> checks" and exits 0 when all pass, exits 1 otherwise.
# A missing file is a named failure, never silently compared as zero-vs-zero.

set -u

DOC="$(dirname "$0")/CATALOG.md"

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
  echo "FAIL: all remaining checks skipped — CATALOG.md not found at $DOC"
  exit 1
fi
if [ ! -s "$DOC" ]; then
  fail "file-non-empty" "empty" "non-empty"
  echo "FAIL: all remaining checks skipped — CATALOG.md is empty"
  exit 1
fi
pass

# Check 2: nine top-level "## " headings present, fixed-string match, in
# order, plus the document's own H1 title before all of them.
HEADINGS=(
  "# Snap-in Catalog and Porting Protocol"
  "## Reading order"
  "## Conventions"
  "## §V — Vocabulary"
  "## §T — Master table"
  "## §E — Per-system entries"
  "## §C — Porting protocol"
  "## §D — PathRAG dry-run"
  "## §R — Repair register"
  "## Appendix A — Frozen roster"
)
LAST_LINE=0
HEADINGS_OK=1
for h in "${HEADINGS[@]}"; do
  LINE=$(grep -n -E -- "^$(printf '%s\n' "$h" | sed 's/[][\.^$*\/]/\\&/g')" "$DOC" | head -1 | cut -d: -f1)
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

# Nine entry-field names fixed in ## Conventions.
FIELD_NAMES_RE='Entry path|Node kinds|Declared capabilities|Artifact scopes|Port cost class|Buckets \(discard/replace/recut/carry over\)|Advantages retained at entry|Advantages decomposition would earn|Evidence'
FIELD_RE="^(${FIELD_NAMES_RE}): "

# Scope entry-field checks (3/4) to the ## §E body only — matching the
# same ## §E .. ## §C window checks 5-10 already use — so a field-name-shaped
# definitional line under ## Conventions is never mistaken for an entry field.
SECTION_E=$(awk '/^## §E/{flag=1; next} /^## §C/{flag=0} flag' "$DOC")

# Anchor guard for checks 3/4 (04-REVIEW.md CR-01). Without it an unmatched
# ## §E .. ## §C window leaves SECTION_E empty, FIELD_LINES empty, and both
# BAD_ counters at their 0 initializer — so both checks would pass vacuously
# over a real defect. Same failure mode the 29 python-side guards close; this
# is the file's only bash-level section extraction, so it needs its own.
if [ -z "$SECTION_E" ]; then
  fail "entry-field-claim-tag" "## §E .. ## §C section window not matched" "matched"
  fail "entry-field-trace-tag" "## §E .. ## §C section window not matched" "matched"
else

# Check 3: every entry-field line carries one of the four claim tags.
FIELD_LINES=$(printf '%s\n' "$SECTION_E" | grep -vE '^#' | grep -E "$FIELD_RE" || true)
BAD_CLAIM=0
if [ -n "$FIELD_LINES" ]; then
  BAD_CLAIM=$(printf '%s\n' "$FIELD_LINES" | grep -vcE '\[(code-verified|docs-verified|paper-claim|inference)\]' || true)
fi
[ "$BAD_CLAIM" -eq 0 ] && pass || fail "entry-field-claim-tag" "$BAD_CLAIM bad" "0"

# Check 4: every entry-field line carries at least one trace tag.
BAD_TRACE=0
if [ -n "$FIELD_LINES" ]; then
  BAD_TRACE=$(printf '%s\n' "$FIELD_LINES" | grep -vcE '\[(CONTRACT §|CONTEXT D-|PARTS §|SELECTION §|MODALITIES-|GAP-SWEEP §)' || true)
fi
[ "$BAD_TRACE" -eq 0 ] && pass || fail "entry-field-trace-tag" "$BAD_TRACE bad" "0"

fi

if ! command -v python3 >/dev/null 2>&1; then
  fail "python3-available" "missing" "available"
  FAILS=$((FAILS + 6))
  echo "FAIL: checks 5-10 skipped (6 checks) — python3 missing"
else

# Check 5: every field name at column 1 inside ## §E is a member of the
# nine-field whitelist.
FIELD5_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §E.*?\n(.*?)\n## §C', text, re.S | re.M)
if not m:
    print("FAIL: field-whitelist — ## §E section anchor not found")
    sys.exit(1)
body = m.group(1)

WHITELIST = [
    "Entry path", "Node kinds", "Declared capabilities", "Artifact scopes",
    "Port cost class", "Buckets (discard/replace/recut/carry over)",
    "Advantages retained at entry", "Advantages decomposition would earn",
    "Evidence",
]

fails = []
for i, line in enumerate(body.splitlines(), start=1):
    m2 = re.match(r'^([A-Za-z][A-Za-z0-9 /()\-]*): ', line)
    if not m2:
        continue
    name = m2.group(1)
    if name not in WHITELIST:
        fails.append(f"line ~{i} (relative to ## §E): unknown field name {name!r}")

if fails:
    for f in fails:
        print(f"FAIL: field-whitelist {f}")
    sys.exit(1)
else:
    print("field-whitelist OK")
    sys.exit(0)
PYEOF
)
FIELD5_STATUS=$?
if [ "$FIELD5_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD5_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD5_OUT" | grep -cE '^FAIL: field-whitelist' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 6: every "### <id> — <system>" entry heading in ## §E carries all
# nine fields, each non-empty.
FIELD6_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §E.*?\n(.*?)\n## §C', text, re.S | re.M)
if not m:
    print("FAIL: entry-field-complete — ## §E section anchor not found")
    sys.exit(1)
body = m.group(1)

FIELDS = [
    "Entry path", "Node kinds", "Declared capabilities", "Artifact scopes",
    "Port cost class", "Buckets (discard/replace/recut/carry over)",
    "Advantages retained at entry", "Advantages decomposition would earn",
    "Evidence",
]

entries = list(re.finditer(r'^### (\S+) — (.+)$', body, re.M))
fails = []
n_checked = 0
for idx, em in enumerate(entries):
    entry_id = em.group(1)
    start = em.end()
    end = entries[idx + 1].start() if idx + 1 < len(entries) else len(body)
    chunk = body[start:end]
    n_checked += 1
    for field in FIELDS:
        fm = re.search(r'^' + re.escape(field) + r': (.*)$', chunk, re.M)
        if not fm or not fm.group(1).strip():
            fails.append(f"{entry_id}: missing or empty field {field!r}")

if n_checked == 0:
    print("FAIL: entry-field-complete zero-rows-matched — ## §E section anchor not found or no entries matched")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: entry-field-complete {f}")
    sys.exit(1)
else:
    print(f"entry-field-complete OK ({n_checked} entries checked)")
    sys.exit(0)
PYEOF
)
FIELD6_STATUS=$?
if [ "$FIELD6_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD6_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD6_OUT" | grep -cE '^FAIL: entry-field-complete' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 7: every ## §T table row (identified by an entry-id first cell) has
# a non-empty cell in every column.
FIELD7_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §T.*?\n(.*?)\n## §E', text, re.S | re.M)
if not m:
    print("FAIL: t-section-no-empty-cells — ## §T section anchor not found")
    sys.exit(1)
body = m.group(1)

ID_RE = re.compile(r'^\| (GR|VT|AG|CA|MC|GS)-[A-Za-z0-9]+ \|')
fails = []
n_checked = 0
for line in body.splitlines():
    if not ID_RE.match(line):
        continue
    n_checked += 1
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    row_id = cells[0] if cells else "?"
    for ci, cell in enumerate(cells):
        if not cell:
            fails.append(f"row {row_id}: empty cell at column {ci + 1}")

if n_checked == 0:
    print("FAIL: t-section-no-empty-cells zero-rows-matched — ## §T section anchor not found or no rows matched")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: t-section-no-empty-cells {f}")
    sys.exit(1)
else:
    print(f"t-section-no-empty-cells OK ({n_checked} rows checked)")
    sys.exit(0)
PYEOF
)
FIELD7_STATUS=$?
if [ "$FIELD7_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD7_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD7_OUT" | grep -cE '^FAIL: t-section-no-empty-cells' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 8: every ## §V advantage id used inside an entry's two advantage
# fields is a member of the ## §V closed list.
FIELD8_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

vm = re.search(r'^## §V.*?\n(.*?)\n## §T', text, re.S | re.M)
if not vm:
    print("FAIL: adv-id-closed-list — ## §V section anchor not found")
    sys.exit(1)
vbody = vm.group(1)
declared = set(re.findall(r'^\| (ADV-\d+) \|', vbody, re.M))

em = re.search(r'^## §E.*?\n(.*?)\n## §C', text, re.S | re.M)
if not em:
    print("FAIL: adv-id-closed-list — ## §E section anchor not found")
    sys.exit(1)
ebody = em.group(1)

fails = []
n_checked = 0
for line in ebody.splitlines():
    if not (line.startswith("Advantages retained at entry:") or
            line.startswith("Advantages decomposition would earn:")):
        continue
    ids = re.findall(r'ADV-\d+', line)
    for uid in ids:
        n_checked += 1
        if uid not in declared:
            fails.append(f"unknown id {uid!r} used in line starting {line[:40]!r}")

if n_checked == 0:
    print("FAIL: adv-id-closed-list zero-rows-matched — no advantage ids found to check (## §V/## §E anchors missing or no ids referenced)")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: adv-id-closed-list {f}")
    sys.exit(1)
else:
    print(f"adv-id-closed-list OK ({n_checked} ids checked, {len(declared)} declared)")
    sys.exit(0)
PYEOF
)
FIELD8_STATUS=$?
if [ "$FIELD8_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD8_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD8_OUT" | grep -cE '^FAIL: adv-id-closed-list' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 9: every "Port cost class:" value and every ## §T port-cost cell is
# one of the four ## §V class names.
FIELD9_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

CLASSES = {"rehost", "rewire", "recut", "rebuild"}
fails = []
n_checked = 0

em = re.search(r'^## §E.*?\n(.*?)\n## §C', text, re.S | re.M)
if not em:
    print("FAIL: port-cost-class-vocab — ## §E section anchor not found")
    sys.exit(1)
ebody = em.group(1)
for line in ebody.splitlines():
    if not line.startswith("Port cost class:"):
        continue
    val = line[len("Port cost class:"):].strip()
    if val.startswith("n-a"):
        continue  # out-of-scope entry per D-11 — exempt, not a class
    n_checked += 1
    # Require the class name to be the leading bold token (the document's
    # own "**recut** — explanation..." convention), not merely present
    # anywhere in the line — a prose line like "unclear, maybe rehost or
    # rewire" must not pass just because a class word appears in it.
    cm = re.match(r'\*\*(\w+)\*\*', val)
    if not (cm and cm.group(1) in CLASSES):
        fails.append(f"no valid class name found in {line[:60]!r}")

tm = re.search(r'^## §T.*?\n(.*?)\n## §E', text, re.S | re.M)
if not tm:
    print("FAIL: port-cost-class-vocab — ## §T section anchor not found")
    sys.exit(1)
tbody = tm.group(1)
ID_RE = re.compile(r'^\| (GR|VT|AG|CA|MC|GS)-[A-Za-z0-9]+ \|')
for line in tbody.splitlines():
    if not ID_RE.match(line):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if len(cells) < 7:
        continue
    class_cell = cells[6]
    if class_cell.startswith("n-a"):
        continue  # out-of-scope row per D-11 — exempt, not a class
    n_checked += 1
    if class_cell not in CLASSES:
        fails.append(f"row {cells[0]}: port-cost cell {class_cell!r} not a valid class")

if n_checked == 0:
    print("FAIL: port-cost-class-vocab zero-rows-matched — no port-cost-class values found to check (## §E/## §T anchors missing)")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: port-cost-class-vocab {f}")
    sys.exit(1)
else:
    print(f"port-cost-class-vocab OK ({n_checked} values checked)")
    sys.exit(0)
PYEOF
)
FIELD9_STATUS=$?
if [ "$FIELD9_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD9_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD9_OUT" | grep -cE '^FAIL: port-cost-class-vocab' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 10: every ## §R row has a non-empty cell in every column.
FIELD10_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §R.*?\n(.*?)\n## Appendix A', text, re.S | re.M)
if not m:
    print("FAIL: r-section-no-empty-cells — ## §R section anchor not found")
    sys.exit(1)
body = m.group(1)

ID_RE = re.compile(r'^\| [A-Za-z]\d+ \|')
fails = []
n_checked = 0
for line in body.splitlines():
    if not ID_RE.match(line):
        continue
    n_checked += 1
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    row_id = cells[0] if cells else "?"
    for ci, cell in enumerate(cells):
        if not cell:
            fails.append(f"row {row_id}: empty cell at column {ci + 1}")

if n_checked == 0:
    print("FAIL: r-section-no-empty-cells zero-rows-matched — ## §R section anchor not found or no rows matched")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: r-section-no-empty-cells {f}")
    sys.exit(1)
else:
    print(f"r-section-no-empty-cells OK ({n_checked} rows checked)")
    sys.exit(0)
PYEOF
)
FIELD10_STATUS=$?
if [ "$FIELD10_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD10_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD10_OUT" | grep -cE '^FAIL: r-section-no-empty-cells' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

fi # python3 available

# Check 11: every ## §E, ## §C, ## §D, ## §R and ## §V heading carries a
# **Satisfies:** line within a short window after the heading.
SATISFIES_HEADINGS=(
  "## §V — Vocabulary"
  "## §E — Per-system entries"
  "## §C — Porting protocol"
  "## §D — PathRAG dry-run"
  "## §R — Repair register"
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

# Check 12: no stub markers.
STUB_N=$(grep -cE 'TODO|TBD|placeholder|to be written' "$DOC" || true)
[ "$STUB_N" -eq 0 ] && pass || fail "no-stub-markers" "$STUB_N found" "0"

if ! command -v python3 >/dev/null 2>&1; then
  fail "python3-available-part2" "missing" "available"
  FAILS=$((FAILS + 17))
  echo "FAIL: checks 13-29 skipped (17 checks) — python3 missing"
else

PHASE_DIR="$(dirname "$0")/../phases/04-snap-in-catalog-porting-protocol"

# Check 13: every Appendix A row's Status cell matches one of the four
# permitted forms, failing per offending row naming the row and the value.
FIELD13_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## Appendix A.*?\n(.*)\Z', text, re.S | re.M)
if not m:
    print("FAIL: status-vocabulary — ## Appendix A section anchor not found")
    sys.exit(1)
body = m.group(1)

ID_RE = re.compile(r'^\| \d+ \|')
fails = []
n_checked = 0
for line in body.splitlines():
    if not ID_RE.match(line):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if len(cells) < 6:
        continue
    entry_id, status = cells[4], cells[5]
    n_checked += 1
    ok = (
        status == "entry drafted"
        or status.startswith("projected — see PARTS.md")
        or status.startswith("out of scope — CONTRACT §")
        or status.startswith("pending — plan 04-")
    )
    if not ok:
        fails.append(f"row {entry_id}: status {status!r} not a permitted form")

if n_checked == 0:
    print("FAIL: status-vocabulary zero-rows-matched — ## Appendix A section anchor not found or no rows matched")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: status-vocabulary {f}")
    sys.exit(1)
else:
    print(f"status-vocabulary OK ({n_checked} rows checked)")
    sys.exit(0)
PYEOF
)
FIELD13_STATUS=$?
if [ "$FIELD13_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD13_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD13_OUT" | grep -cE '^FAIL: status-vocabulary' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 14: roster to entry, both directions (D-03's first requirement). A
# terminal Appendix A row (Status not the pending form) must have a matching
# ## §E entry, and every ## §E entry must have a roster row — never a count
# comparison, fails per unmatched id in each direction.
FIELD14_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

am = re.search(r'^## Appendix A.*?\n(.*)\Z', text, re.S | re.M)
if not am:
    print("FAIL: roster-entry-crossref — ## Appendix A section anchor not found")
    sys.exit(1)
abody = am.group(1)
ID_RE = re.compile(r'^\| \d+ \|')
terminal_ids = set()
all_roster_ids = set()
for line in abody.splitlines():
    if not ID_RE.match(line):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if len(cells) < 6:
        continue
    entry_id, status = cells[4], cells[5]
    all_roster_ids.add(entry_id)
    if not status.startswith("pending — plan"):
        terminal_ids.add(entry_id)

em = re.search(r'^## §E.*?\n(.*?)\n## §C', text, re.S | re.M)
if not em:
    print("FAIL: roster-entry-crossref — ## §E section anchor not found")
    sys.exit(1)
ebody = em.group(1)
entry_ids = set(re.findall(r'^### (\S+) — ', ebody, re.M))

fails = []
for eid in sorted(terminal_ids - entry_ids):
    fails.append(f"terminal roster row {eid} has no ## §E entry")
for eid in sorted(entry_ids - all_roster_ids):
    fails.append(f"## §E entry {eid} has no Appendix A roster row")

if fails:
    for f in fails:
        print(f"FAIL: roster-entry-crossref {f}")
    sys.exit(1)
else:
    print(f"roster-entry-crossref OK ({len(terminal_ids)} terminal rows, {len(entry_ids)} entries)")
    sys.exit(0)
PYEOF
)
FIELD14_STATUS=$?
if [ "$FIELD14_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD14_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD14_OUT" | grep -cE '^FAIL: roster-entry-crossref' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 15: master table to entry, both directions — the same sub-pass shape
# over ## §T row ids and ## §E entry headings.
FIELD15_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

tm = re.search(r'^## §T.*?\n(.*?)\n## §E', text, re.S | re.M)
if not tm:
    print("FAIL: table-entry-crossref — ## §T section anchor not found")
    sys.exit(1)
tbody = tm.group(1)
ID_RE = re.compile(r'^\| (GR|VT|AG|CA|MC|GS)-[A-Za-z0-9]+ \|')
table_ids = set()
for line in tbody.splitlines():
    m2 = ID_RE.match(line)
    if m2:
        table_ids.add(line.strip().strip('|').split('|')[0].strip())

em = re.search(r'^## §E.*?\n(.*?)\n## §C', text, re.S | re.M)
if not em:
    print("FAIL: table-entry-crossref — ## §E section anchor not found")
    sys.exit(1)
ebody = em.group(1)
entry_ids = set(re.findall(r'^### (\S+) — ', ebody, re.M))

fails = []
for eid in sorted(table_ids - entry_ids):
    fails.append(f"## §T row {eid} has no ## §E entry")
for eid in sorted(entry_ids - table_ids):
    fails.append(f"## §E entry {eid} has no ## §T row")

if fails:
    for f in fails:
        print(f"FAIL: table-entry-crossref {f}")
    sys.exit(1)
else:
    print(f"table-entry-crossref OK ({len(table_ids)} rows, {len(entry_ids)} entries)")
    sys.exit(0)
PYEOF
)
FIELD15_STATUS=$?
if [ "$FIELD15_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD15_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD15_OUT" | grep -cE '^FAIL: table-entry-crossref' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 16: row order. ## §T row ids ascending in group order GR, VT, AG,
# CA, MC, GS, ascending numerically within a group and by N-id within GS;
# ## §E's entry-heading order is byte-identical to ## §T's row-id order.
# Fails naming the first pair out of order.
FIELD16_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

GROUP_ORDER = {"GR": 0, "VT": 1, "AG": 2, "CA": 3, "MC": 4, "GS": 5}
GS_SHAPE_RE = re.compile(r'^N\d+$')

def sort_key(entry_id):
    prefix, num = entry_id.split("-", 1)
    if prefix == "GS":
        if not GS_SHAPE_RE.match(num):
            raise ValueError(f"GS id {entry_id!r} does not match expected shape GS-N<digits>")
        return (GROUP_ORDER[prefix], int(num[1:]))  # NNN after 'N'
    return (GROUP_ORDER[prefix], int(num))

tm = re.search(r'^## §T.*?\n(.*?)\n## §E', text, re.S | re.M)
if not tm:
    print("FAIL: row-order — ## §T section anchor not found")
    sys.exit(1)
tbody = tm.group(1)
ID_RE = re.compile(r'^\| (GR|VT|AG|CA|MC|GS)-[A-Za-z0-9]+ \|')
table_ids = []
for line in tbody.splitlines():
    m2 = ID_RE.match(line)
    if m2:
        table_ids.append(line.strip().strip('|').split('|')[0].strip())

em = re.search(r'^## §E.*?\n(.*?)\n## §C', text, re.S | re.M)
if not em:
    print("FAIL: row-order — ## §E section anchor not found")
    sys.exit(1)
ebody = em.group(1)
entry_ids = re.findall(r'^### (\S+) — ', ebody, re.M)

fails = []
prev = None
try:
    for eid in table_ids:
        key = sort_key(eid)
        if prev is not None and key <= prev:
            fails.append(f"## §T row {eid} out of order")
            break
        prev = key
except (ValueError, KeyError) as e:
    fails.append(f"row-id shape mismatch: {e}")

if table_ids != entry_ids:
    fails.append(
        f"## §E entry order {entry_ids} does not match ## §T row order {table_ids}"
    )

if fails:
    for f in fails:
        print(f"FAIL: row-order {f}")
    sys.exit(1)
else:
    print(f"row-order OK ({len(table_ids)} rows)")
    sys.exit(0)
PYEOF
)
FIELD16_STATUS=$?
if [ "$FIELD16_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD16_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD16_OUT" | grep -cE '^FAIL: row-order' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 17: every pending row names a plan id whose PLAN.md file exists
# under the phase directory; fails per row naming an absent plan file.
FIELD17_OUT=$(python3 - "$DOC" "$PHASE_DIR" <<'PYEOF'
import re, sys, os
DOC, PHASE_DIR = sys.argv[1], sys.argv[2]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## Appendix A.*?\n(.*)\Z', text, re.S | re.M)
if m is None:
    print("FAIL: pending-plan-exists section-not-found — ## Appendix A anchor not matched")
    sys.exit(1)
body = m.group(1)

ID_RE = re.compile(r'^\| \d+ \|')
fails = []
n_checked = 0
for line in body.splitlines():
    if not ID_RE.match(line):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if len(cells) < 6:
        continue
    entry_id, status = cells[4], cells[5]
    pm = re.match(r'^pending — plan (04-\d+)$', status)
    if not pm:
        continue
    n_checked += 1
    plan_id = pm.group(1)
    plan_path = os.path.join(PHASE_DIR, f"{plan_id}-PLAN.md")
    if not os.path.isfile(plan_path):
        fails.append(f"row {entry_id}: {plan_path} does not exist")

if fails:
    for f in fails:
        print(f"FAIL: pending-plan-exists {f}")
    sys.exit(1)
else:
    print(f"pending-plan-exists OK ({n_checked} pending rows checked)")
    sys.exit(0)
PYEOF
)
FIELD17_STATUS=$?
if [ "$FIELD17_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD17_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD17_OUT" | grep -cE '^FAIL: pending-plan-exists' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 18: advantage marking completeness. Every ## §E entry's two
# advantage fields between them mark every ADV- id declared in ## §V, with
# no id marked twice and none omitted; fails per entry naming the missing
# or duplicated id. An out-of-scope entry (Entry path: out of scope — ...)
# is exempt.
FIELD18_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

vm = re.search(r'^## §V.*?\n(.*?)\n## §T', text, re.S | re.M)
if not vm:
    print("FAIL: advantage-marking-completeness — ## §V section anchor not found")
    sys.exit(1)
vbody = vm.group(1)
declared = set(re.findall(r'^\| (ADV-\d+) \|', vbody, re.M))

em = re.search(r'^## §E.*?\n(.*?)\n## §C', text, re.S | re.M)
if not em:
    print("FAIL: advantage-marking-completeness — ## §E section anchor not found")
    sys.exit(1)
ebody = em.group(1)

entries = list(re.finditer(r'^### (\S+) — (.+)$', ebody, re.M))
fails = []
n_checked = 0
for idx, entrym in enumerate(entries):
    entry_id = entrym.group(1)
    start = entrym.end()
    end = entries[idx + 1].start() if idx + 1 < len(entries) else len(ebody)
    chunk = ebody[start:end]

    epm = re.search(r'^Entry path: (.*)$', chunk, re.M)
    if epm and epm.group(1).strip().startswith("`out of scope"):
        continue

    n_checked += 1
    seen = []
    for line in chunk.splitlines():
        if not (line.startswith("Advantages retained at entry:") or
                line.startswith("Advantages decomposition would earn:")):
            continue
        seen.extend(re.findall(r'ADV-\d+', line))

    missing = sorted(declared - set(seen))
    dup = sorted({x for x in seen if seen.count(x) > 1})
    if missing:
        fails.append(f"{entry_id}: missing {missing}")
    if dup:
        fails.append(f"{entry_id}: duplicated {dup}")

if n_checked == 0:
    print("FAIL: advantage-marking-completeness zero-rows-matched — ## §E section anchor not found or no in-scope entries matched")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: advantage-marking-completeness {f}")
    sys.exit(1)
else:
    print(f"advantage-marking-completeness OK ({n_checked} entries checked, {len(declared)} ADV ids)")
    sys.exit(0)
PYEOF
)
FIELD18_STATUS=$?
if [ "$FIELD18_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD18_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD18_OUT" | grep -cE '^FAIL: advantage-marking-completeness' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 19: the four "### §C.n" sub-headings are present, in order, inside
# ## §C (before ## §D).
FIELD19_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §C.*?\n(.*?)\n## §D', text, re.S | re.M)
if not m:
    print("FAIL: c-subheading-order — ## §C section anchor not found")
    sys.exit(1)
body = m.group(1)

EXPECTED = [
    "### §C.1 — Dissection procedure",
    "### §C.2 — The four-bucket carry-over map",
    "### §C.3 — Target code shape",
    "### §C.4 — Exit test",
]

fails = []
last_pos = -1
for h in EXPECTED:
    pos = body.find(h)
    if pos == -1:
        fails.append(f"missing sub-heading: {h}")
        continue
    if pos <= last_pos:
        fails.append(f"sub-heading out of order: {h}")
    last_pos = pos

if fails:
    for f in fails:
        print(f"FAIL: c-subheading-order {f}")
    sys.exit(1)
else:
    print("c-subheading-order OK (4 sub-headings, in order)")
    sys.exit(0)
PYEOF
)
FIELD19_STATUS=$?
if [ "$FIELD19_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD19_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD19_OUT" | grep -cE '^FAIL: c-subheading-order' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 20: ### §C.2 quotes all four bucket names and the quotation carries a
# [PARTS-07] trace tag.
FIELD20_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §C\.2.*?\n(.*?)\n### §C\.3', text, re.S | re.M)
if not m:
    print("FAIL: c2-bucket-quote — ### §C.2 section anchor not found")
    sys.exit(1)
body = m.group(1)

fails = []
for bucket in ["discard", "replace", "recut", "carry over"]:
    if f"*{bucket}*" not in body:
        fails.append(f"bucket name not quoted: {bucket}")

if "[PARTS-07]" not in body:
    fails.append("quotation missing [PARTS-07] trace tag")

if fails:
    for f in fails:
        print(f"FAIL: c2-bucket-quote {f}")
    sys.exit(1)
else:
    print("c2-bucket-quote OK (four buckets quoted, [PARTS-07] tagged)")
    sys.exit(0)
PYEOF
)
FIELD20_STATUS=$?
if [ "$FIELD20_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD20_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD20_OUT" | grep -cE '^FAIL: c2-bucket-quote' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 21: ### §C.3 carries a [code-verified] claim tag together with a
# commit SHA and a named source file — the code-verification claim cannot be
# made without its provenance.
FIELD21_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §C\.3.*?\n(.*?)\n### §C\.4', text, re.S | re.M)
if not m:
    print("FAIL: c3-code-verified-provenance — ### §C.3 section anchor not found")
    sys.exit(1)
body = m.group(1)

fails = []
if "[code-verified]" not in body:
    fails.append("no [code-verified] claim tag found")
if not re.search(r'\b[0-9a-f]{7,40}\b', body):
    fails.append("no commit SHA found")
if "operate.py" not in body:
    fails.append("no named source file (operate.py) found")

if fails:
    for f in fails:
        print(f"FAIL: c3-code-verified-provenance {f}")
    sys.exit(1)
else:
    print("c3-code-verified-provenance OK (claim tag, SHA, source file all present)")
    sys.exit(0)
PYEOF
)
FIELD21_STATUS=$?
if [ "$FIELD21_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD21_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD21_OUT" | grep -cE '^FAIL: c3-code-verified-provenance' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 22: ### §C.4 names each of RIG-01 through RIG-07 at least once, so
# the scope fence cannot be silently narrowed.
FIELD22_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §C\.4.*?\n(.*?)\n## §D', text, re.S | re.M)
if not m:
    print("FAIL: c4-rig-coverage — ### §C.4 section anchor not found")
    sys.exit(1)
body = m.group(1)

fails = []
for n in range(1, 8):
    rig = f"RIG-{n:02d}"
    if rig not in body:
        fails.append(f"missing {rig}")

if fails:
    for f in fails:
        print(f"FAIL: c4-rig-coverage {f}")
    sys.exit(1)
else:
    print("c4-rig-coverage OK (RIG-01..RIG-07 all named)")
    sys.exit(0)
PYEOF
)
FIELD22_STATUS=$?
if [ "$FIELD22_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD22_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD22_OUT" | grep -cE '^FAIL: c4-rig-coverage' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Checks 23-24: every normative clause line inside ## §C (before ## §D)
# carries a claim tag (23) and at least one trace tag (24) — the same
# generalized per-line check shape checks 3 and 4 already apply to entry
# fields, generalized here to prose rather than a whitelisted field name.
# Excluded: blank lines, heading lines, the "**Satisfies:**" line, and
# numbered/lettered list markers with no tagged content of their own.
FIELD2324_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §C.*?\n(.*?)\n## §D', text, re.S | re.M)
if not m:
    print("FAIL: c-claim-tag — ## §C section anchor not found")
    sys.exit(1)
body = m.group(1)

CLAIM_RE = re.compile(r'\[(code-verified|docs-verified|paper-claim|inference)\]')
TRACE_RE = re.compile(r'\[(CONTRACT §|CONTEXT D-|PARTS §|PARTS-0|SELECTION §|MODALITIES-|GAP-SWEEP §|03-D8-DISPOSITION-AUDIT)')

missing_claim = []
missing_trace = []
for i, line in enumerate(body.splitlines(), start=1):
    stripped = line.strip()
    if not stripped:
        continue
    if stripped.startswith('#'):
        continue
    if stripped.startswith('**Satisfies:**'):
        continue
    if not CLAIM_RE.search(line):
        missing_claim.append(f"line ~{i}: {stripped[:60]!r}")
    if not TRACE_RE.search(line):
        missing_trace.append(f"line ~{i}: {stripped[:60]!r}")

if missing_claim:
    for f in missing_claim:
        print(f"FAIL: c-claim-tag {f}")
    sys.exit(1)
else:
    print("c-claim-tag OK")
    sys.exit(0)
PYEOF
)
FIELD23_STATUS=$?
if [ "$FIELD23_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD2324_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD2324_OUT" | grep -cE '^FAIL: c-claim-tag' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

FIELD24_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §C.*?\n(.*?)\n## §D', text, re.S | re.M)
if not m:
    print("FAIL: c-trace-tag — ## §C section anchor not found")
    sys.exit(1)
body = m.group(1)

TRACE_RE = re.compile(r'\[(CONTRACT §|CONTEXT D-|PARTS §|PARTS-0|SELECTION §|MODALITIES-|GAP-SWEEP §|03-D8-DISPOSITION-AUDIT)')

missing_trace = []
for i, line in enumerate(body.splitlines(), start=1):
    stripped = line.strip()
    if not stripped:
        continue
    if stripped.startswith('#'):
        continue
    if stripped.startswith('**Satisfies:**'):
        continue
    if not TRACE_RE.search(line):
        missing_trace.append(f"line ~{i}: {stripped[:60]!r}")

if missing_trace:
    for f in missing_trace:
        print(f"FAIL: c-trace-tag {f}")
    sys.exit(1)
else:
    print("c-trace-tag OK")
    sys.exit(0)
PYEOF
)
FIELD24_STATUS=$?
if [ "$FIELD24_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD24_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD24_OUT" | grep -cE '^FAIL: c-trace-tag' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 25: roster completeness (closing). No ## Appendix A row's Status is
# in the pending form — the roster's both-directions guarantee is total, not
# partial, only satisfiable once every plan in the phase has landed.
FIELD25_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## Appendix A.*?\n(.*)\Z', text, re.S | re.M)
if not m:
    print("FAIL: roster-completeness — ## Appendix A section anchor not found")
    sys.exit(1)
body = m.group(1)

ID_RE = re.compile(r'^\| \d+ \|')
fails = []
n_checked = 0
for line in body.splitlines():
    if not ID_RE.match(line):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if len(cells) < 6:
        continue
    entry_id, status = cells[4], cells[5]
    n_checked += 1
    if status.startswith("pending — plan"):
        fails.append(f"row {entry_id}: still pending ({status!r})")

if n_checked == 0:
    print("FAIL: roster-completeness zero-rows-matched — ## Appendix A section anchor not found or no rows matched")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: roster-completeness {f}")
    sys.exit(1)
else:
    print(f"roster-completeness OK ({n_checked} rows checked, 0 pending)")
    sys.exit(0)
PYEOF
)
FIELD25_STATUS=$?
if [ "$FIELD25_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD25_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD25_OUT" | grep -cE '^FAIL: roster-completeness' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 26: register completeness. Every ## §R row's Status matches one of the
# permitted terminal forms: a landed repair naming a clause, an explicit
# no-amendment record, or a deferral naming an owning phase and a reason (an
# "inherited from PARTS.md" Status MUST also state its own disposition here,
# never stand alone as bare provenance).
FIELD26_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §R.*?\n(.*?)\n## Appendix A', text, re.S | re.M)
if not m:
    print("FAIL: register-completeness — ## §R section anchor not found")
    sys.exit(1)
body = m.group(1)

ID_RE = re.compile(r'^\| [A-Za-z]\d+ \|')
fails = []
n_checked = 0
for line in body.splitlines():
    if not ID_RE.match(line):
        continue
    row_id = line.strip().strip('|').split('|')[0].strip()
    n_checked += 1
    status = line.rstrip()
    status_cell = status.rsplit('|', 2)[-2].strip() if status.count('|') >= 2 else status
    is_repaired = "repaired in §" in status_cell
    # "in" check, not startswith: an inherited-prefix row (e.g. "inherited
    # from PARTS.md ## §R N1; recorded, no amendment — ...") resolves to this
    # form exactly as validly as a same-phase row that starts with it
    # directly — the phrase MUST additionally resolve after the prefix, not
    # stand alone as bare provenance, but "additionally resolve" means the
    # phrase is present, not that it opens the cell. Fixed alongside
    # is_bare_inherited below, since the previous startswith-only check made
    # this permitted form structurally undetectable on any inherited row —
    # a checker bug, not a rule this project's own D-13 vocabulary states
    # (Phase 6 CONTEXT.md; MODEL-RED-TEAM.md ## Conventions' terminal-status
    # vocabulary names "recorded, no amendment — handed to the build with
    # repair direction: <direction>" as D-13's own terminal form for exactly
    # an inherited row no attack forces).
    is_no_amendment = "recorded, no amendment" in status_cell
    is_deferred = "deferred —" in status_cell
    is_bare_inherited = (
        status_cell.startswith("inherited from PARTS.md")
        and not is_deferred
        and not is_repaired
        and not is_no_amendment
    )
    if is_bare_inherited or not (is_repaired or is_no_amendment or is_deferred):
        fails.append(f"row {row_id}: Status {status_cell!r} not a permitted terminal form")

if n_checked == 0:
    print("FAIL: register-completeness zero-rows-matched — ## §R section anchor not found or no rows matched")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: register-completeness {f}")
    sys.exit(1)
else:
    print(f"register-completeness OK ({n_checked} rows checked)")
    sys.exit(0)
PYEOF
)
FIELD26_STATUS=$?
if [ "$FIELD26_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD26_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD26_OUT" | grep -cE '^FAIL: register-completeness' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 27: governance sentence. The document carries its D-04 projected-rows
# governance sentence and its D-07 repair-discipline sentence, fixed-string,
# in the preamble — the analogue of parts-check.sh check 12.
FIELD27_OUT=$(python3 - "$DOC" <<'PYEOF'
import sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

preamble_end = text.find("## Reading order")
preamble = text[:preamble_end] if preamble_end != -1 else text

D04_SENTENCE = "**The three deep modalities are projected, not restated (D-04).**"
D07_SENTENCE = "repaired in place in `CONTRACT.md`, never stated as a rule here — per `CONTEXT D-07`"

fails = []
if D04_SENTENCE not in preamble:
    fails.append("D-04 projected-rows governance sentence not found in preamble")
if D07_SENTENCE not in preamble:
    fails.append("D-07 repair-discipline sentence not found in preamble")

if fails:
    for f in fails:
        print(f"FAIL: governance-sentence {f}")
    sys.exit(1)
else:
    print("governance-sentence OK (D-04 and D-07 sentences both present)")
    sys.exit(0)
PYEOF
)
FIELD27_STATUS=$?
if [ "$FIELD27_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD27_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD27_OUT" | grep -cE '^FAIL: governance-sentence' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 28: advantage completeness across the whole, closed roster (not just
# whatever ## §E headers happen to exist) — every terminal, non-out-of-scope
# ## Appendix A row has a corresponding ## §E entry that passes the same
# marking-completeness test check 18 already runs, generalising check 18 (run
# at plan 04-01 against five tracer entries) to the finished 72-row roster.
FIELD28_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

am = re.search(r'^## Appendix A.*?\n(.*)\Z', text, re.S | re.M)
if not am:
    print("FAIL: advantage-completeness-whole-catalog — ## Appendix A section anchor not found")
    sys.exit(1)
abody = am.group(1)
ID_RE = re.compile(r'^\| \d+ \|')
roster_terminal_nonoos = set()
for line in abody.splitlines():
    if not ID_RE.match(line):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if len(cells) < 6:
        continue
    entry_id, status = cells[4], cells[5]
    if status.startswith("pending") or status.startswith("out of scope"):
        continue
    roster_terminal_nonoos.add(entry_id)

vm = re.search(r'^## §V.*?\n(.*?)\n## §T', text, re.S | re.M)
if not vm:
    print("FAIL: advantage-completeness-whole-catalog — ## §V section anchor not found")
    sys.exit(1)
vbody = vm.group(1)
declared = set(re.findall(r'^\| (ADV-\d+) \|', vbody, re.M))

em = re.search(r'^## §E.*?\n(.*?)\n## §C', text, re.S | re.M)
if not em:
    print("FAIL: advantage-completeness-whole-catalog — ## §E section anchor not found")
    sys.exit(1)
ebody = em.group(1)
entry_list = list(re.finditer(r'^### (\S+) — (.+)$', ebody, re.M))
entry_index = {m2.group(1): idx for idx, m2 in enumerate(entry_list)}

fails = []
n_checked = 0
for eid in sorted(roster_terminal_nonoos):
    if eid not in entry_index:
        fails.append(f"roster row {eid} (terminal, non-out-of-scope) has no ## §E entry")
        continue
    n_checked += 1
    idx = entry_index[eid]
    start = entry_list[idx].end()
    end = entry_list[idx + 1].start() if idx + 1 < len(entry_list) else len(ebody)
    chunk = ebody[start:end]
    seen = []
    for line in chunk.splitlines():
        if not (line.startswith("Advantages retained at entry:") or
                line.startswith("Advantages decomposition would earn:")):
            continue
        seen.extend(re.findall(r'ADV-\d+', line))
    missing = sorted(declared - set(seen))
    if missing:
        fails.append(f"{eid}: roster-driven scan finds missing {missing}")

if fails:
    for f in fails:
        print(f"FAIL: advantage-completeness-whole-catalog {f}")
    sys.exit(1)
else:
    print(f"advantage-completeness-whole-catalog OK ({n_checked} terminal roster rows checked against ## §E)")
    sys.exit(0)
PYEOF
)
FIELD28_STATUS=$?
if [ "$FIELD28_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD28_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD28_OUT" | grep -cE '^FAIL: advantage-completeness-whole-catalog' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 29: master table and register cross-reference. Every ## §R row's own
# Forcing entry cell (column 5) names either an existing ## §E entry id, a
# ## §D dry-run finding (§D-n), or a named PARTS.md/breadth-plan exercise (a
# backtick-quoted .md filename, a CONTEXT D-NN decision, or a PARTS-0N
# requirement id); a cell naming none of those fails. Splits on an unescaped
# pipe only, since two existing rows (G2, G9) carry a literal `\|` inside a
# cell's own quoted content.
FIELD29_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §R.*?\n(.*?)\n## Appendix A', text, re.S | re.M)
if not m:
    print("FAIL: register-forcing-entry-crossref — ## §R section anchor not found")
    sys.exit(1)
body = m.group(1)

ID_RE = re.compile(r'^\| [A-Za-z]\d+ \|')
SPLIT_RE = re.compile(r'(?<!\\)\|')
NAMED_RE = re.compile(
    r'(GR|VT|AG|CA|MC|GS)-[A-Za-z0-9]+|§D-\d+|\.md|CONTEXT D-\d+|PARTS-0\d'
)

fails = []
n_checked = 0
for line in body.splitlines():
    if not ID_RE.match(line):
        continue
    # Strip exactly one leading/trailing pipe (the outer table delimiters,
    # not a filter over all cells) so column positions stay stable even
    # when an earlier cell in the row is empty — matching checks 7/10/26's
    # "keep empty cells between real pipes" approach instead of the
    # position-fragile "if c.strip() != ''" filter this check used before.
    row = line.strip()
    if row.startswith('|'):
        row = row[1:]
    if row.endswith('|'):
        row = row[:-1]
    cells = [c.strip() for c in SPLIT_RE.split(row)]
    if len(cells) < 5:
        continue
    row_id, forcing = cells[0], cells[4]
    n_checked += 1
    if not NAMED_RE.search(forcing):
        fails.append(f"row {row_id}: Forcing entry cell {forcing[:60]!r} names no ## §E entry, §D finding, or PARTS.md exercise")

if fails:
    for f in fails:
        print(f"FAIL: register-forcing-entry-crossref {f}")
    sys.exit(1)
else:
    print(f"register-forcing-entry-crossref OK ({n_checked} rows checked)")
    sys.exit(0)
PYEOF
)
FIELD29_STATUS=$?
if [ "$FIELD29_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD29_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD29_OUT" | grep -cE '^FAIL: register-forcing-entry-crossref' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

fi # python3 available (part 2)

if [ "$FAILS" -eq 0 ]; then
  echo "OK $PASSES checks"
  exit 0
else
  echo "FAIL: $FAILS check(s) failed, $PASSES passed"
  exit 1
fi
