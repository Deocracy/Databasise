#!/usr/bin/env bash
# Structural + content checker for RIG.md.
# Usage: bash rig-check.sh
#
# Per-row and per-clause content checks, never row-count checks (D-02,
# carried from Phase 3's own D-02 precedent). Prints one
# "FAIL: <check name> — <observed> vs <expected>" line per failed check,
# prints "OK <n> checks" and exits 0 when all pass, exits 1 otherwise.
# A missing file is a named failure, never silently compared as zero-vs-zero.
#
# Unlike its three predecessors (anatomy-check.sh, parts-check.sh,
# catalog-check.sh), this gate also validates *content*: D-09's worked
# trace example (wirings/rig-trace-example.json) against D-09's JSON
# Schema (rig-trace.schema.json), via ajv-cli. This is the project's
# first executable content-level check.

set -u

DOC="$(dirname "$0")/RIG.md"

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
  echo "FAIL: all remaining checks skipped — RIG.md not found at $DOC"
  exit 1
fi
if [ ! -s "$DOC" ]; then
  fail "file-non-empty" "empty" "non-empty"
  echo "FAIL: all remaining checks skipped — RIG.md is empty"
  exit 1
fi
pass

# Check 2: twelve "## " headings present, fixed-string match, in order.
HEADINGS=(
  "# The Comparison Rig and Versioning Mechanics"
  "## Reading order"
  "## Conventions"
  "## §RUN — The parallel-run model"
  "## §TR — The trace schema"
  "## §CM — Cost-model provenance and anatomy"
  "## §EV — Eval-bundle versioning and target-MDE sizing"
  "## §F3 — The Falsifier 3 verdict"
  "## §PR — The promote/rollback protocol"
  "## §AA — The A/A calibration procedure"
  "## §LC — The run lifecycle"
  "## §R — Repair register"
  "## Appendix A — Requirement-to-section map"
)
LAST_LINE=0
for h in "${HEADINGS[@]}"; do
  LINE=$(grep -n -F -- "$h" "$DOC" | head -1 | cut -d: -f1)
  if [ -z "$LINE" ]; then
    fail "heading-present" "missing: $h" "present"
    continue
  fi
  if [ "$LINE" -le "$LAST_LINE" ]; then
    fail "heading-order" "$h at line $LINE" "after line $LAST_LINE"
  fi
  LAST_LINE="$LINE"
done
pass

if ! command -v python3 >/dev/null 2>&1; then
  fail "python3-available" "missing" "available"
  FAILS=$((FAILS + 4))
  echo "FAIL: checks 3-6 skipped (4 checks) — python3 missing"
else

# Check 3: check_trace_schema() — the content-level check. Both
# rig-trace.schema.json and wirings/rig-trace-example.json present, and the
# worked instance validates against the schema via ajv-cli (draft-07).
check_trace_schema() {
  local schema
  local instance
  schema="$(dirname "$0")/rig-trace.schema.json"
  instance="$(dirname "$0")/wirings/rig-trace-example.json"
  if [ ! -f "$schema" ] || [ ! -f "$instance" ]; then
    fail "trace-schema-content-check" "missing file(s)" "both present"
    return
  fi
  if HOME="${TMPDIR:-/tmp}" npx --yes -p ajv-cli ajv validate -s "$schema" -d "$instance" >/tmp/rig-check-ajv.log 2>&1; then
    pass
  else
    fail "trace-schema-content-check" "$(cat /tmp/rig-check-ajv.log)" "valid against schema"
  fi
}
check_trace_schema

# Check 4: every field name in §TR.1's field table appears as a property in
# rig-trace.schema.json, and every property in the schema appears in the
# field table — both directions, failing per missing name and naming which
# side is missing it.
FIELD4_OUT=$(python3 - "$DOC" "$(dirname "$0")/rig-trace.schema.json" <<'PYEOF'
import re, sys, json
DOC, SCHEMA = sys.argv[1], sys.argv[2]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §TR .*?\n(.*?)\n## §CM', text, re.S | re.M)
body = m.group(1) if m else ""

# Field names appear as the first cell of a table row inside the two field
# tables (backtick-wrapped identifiers only, excludes header/separator rows).
doc_fields = set(re.findall(r'^\| `([a-z_]+)` \|', body, re.M))

with open(SCHEMA, encoding="utf-8") as f:
    schema = json.load(f)

run_props = set(schema.get("properties", {}).keys()) - {"status", "status_note"}
node_props = set(schema.get("$defs", {}).get("NodeTrace", {}).get("properties", {}).keys())
token_props = set(schema.get("$defs", {}).get("TokenAccounting", {}).get("properties", {}).keys())
schema_fields = run_props | node_props | token_props

missing_in_schema = sorted(doc_fields - schema_fields - {"tokens"})
missing_in_doc = sorted(schema_fields - doc_fields)

fails = []
for f in missing_in_schema:
    fails.append(f"field {f!r} in RIG.md's table but not in rig-trace.schema.json")
for f in missing_in_doc:
    fails.append(f"field {f!r} in rig-trace.schema.json but not in RIG.md's table")

if fails:
    for f in fails:
        print(f"FAIL: field-table-schema-parity {f}")
    sys.exit(1)
else:
    print(f"field-table-schema-parity OK ({len(doc_fields)} doc fields, {len(schema_fields)} schema fields)")
    sys.exit(0)
PYEOF
)
FIELD4_STATUS=$?
if [ "$FIELD4_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD4_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD4_OUT" | grep -cE '^FAIL: field-table-schema-parity' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 5: $defs.TokenAccounting requires all four D-14 fields plus
# counted_by, failing per missing field.
FIELD5_OUT=$(python3 - "$(dirname "$0")/rig-trace.schema.json" <<'PYEOF'
import sys, json
SCHEMA = sys.argv[1]
with open(SCHEMA, encoding="utf-8") as f:
    schema = json.load(f)

required = set(schema.get("$defs", {}).get("TokenAccounting", {}).get("required", []))
expected = {"prompt_tokens", "completion_tokens", "cached_read_tokens", "call_count", "counted_by"}

missing = sorted(expected - required)
if missing:
    for m in missing:
        print(f"FAIL: token-accounting-required missing {m!r}")
    sys.exit(1)
else:
    print("token-accounting-required OK (all five required)")
    sys.exit(0)
PYEOF
)
FIELD5_STATUS=$?
if [ "$FIELD5_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD5_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD5_OUT" | grep -cE '^FAIL: token-accounting-required' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 6: no stub markers.
STUB_N=$(grep -cE 'TODO|TBD|placeholder|to be written' "$DOC" || true)
[ "$STUB_N" -eq 0 ] && pass || fail "no-stub-markers" "$STUB_N found" "0"

# Check 7: every normative clause line inside ## §RUN, ## §TR, ## §CM, ## §EV,
# ## §F3, ## §PR, ## §AA and ## §LC carries one of the four claim tags.
# Table rows (their own "Tags" column already carries the tag, checked
# separately by Check 4) and fenced-code-block lines are excluded, along
# with blank/heading/"**Satisfies:**" lines and bold-only caption lines
# (e.g. "**Run-level fields.**") that introduce a table with no independent
# claim of their own.
FIELD78_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

SECTIONS = ["§RUN", "§TR", "§CM", "§EV", "§F3", "§PR", "§AA", "§LC"]
CLAIM_RE = re.compile(r'\[(code-verified|docs-verified|paper-claim|inference)\]')
TRACE_RE = re.compile(r'\[(CONTRACT §|CONTEXT D-|PARTS §|PARTS-0|CATALOG §|SELECTION §|ROADMAP §|05-RESEARCH|ANATOMY §|RT-selfimprove §|new-synthesis)')
LABEL_ONLY_RE = re.compile(r'^\*\*[^*]+\*\*\.?$')

heading_positions = [(m.start(), m.group(1)) for m in re.finditer(r'^## (.+)$', text, re.M)]
missing_claim = []
missing_trace = []
for i, (pos, title) in enumerate(heading_positions):
    sec_id = None
    for s in SECTIONS:
        if title.startswith(s + " ") or title == s:
            sec_id = s
    if not sec_id:
        continue
    end = heading_positions[i + 1][0] if i + 1 < len(heading_positions) else len(text)
    body = text[pos:end]
    in_code = False
    for lineno, line in enumerate(body.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("**Satisfies:**"):
            continue
        if stripped.startswith("|"):
            continue
        if LABEL_ONLY_RE.match(stripped):
            continue
        if not CLAIM_RE.search(line):
            missing_claim.append(f"[{sec_id}] line ~{lineno}: {stripped[:70]!r}")
        if not TRACE_RE.search(line):
            missing_trace.append(f"[{sec_id}] line ~{lineno}: {stripped[:70]!r}")

if missing_claim:
    for f in missing_claim:
        print(f"FAIL: section-claim-tag {f}")
    print("__CLAIM_FAIL__")
if missing_trace:
    for f in missing_trace:
        print(f"FAIL: section-trace-tag {f}")
    print("__TRACE_FAIL__")
if not missing_claim and not missing_trace:
    print("section-claim-tag OK; section-trace-tag OK")
sys.exit(0)
PYEOF
)
if printf '%s\n' "$FIELD78_OUT" | grep -q '__CLAIM_FAIL__'; then
  printf '%s\n' "$FIELD78_OUT" | grep -E '^FAIL: section-claim-tag'
  FAILCOUNT=$(printf '%s\n' "$FIELD78_OUT" | grep -cE '^FAIL: section-claim-tag' || true)
  FAILS=$((FAILS + FAILCOUNT))
else
  pass
fi
if printf '%s\n' "$FIELD78_OUT" | grep -q '__TRACE_FAIL__'; then
  printf '%s\n' "$FIELD78_OUT" | grep -E '^FAIL: section-trace-tag'
  FAILCOUNT=$(printf '%s\n' "$FIELD78_OUT" | grep -cE '^FAIL: section-trace-tag' || true)
  FAILS=$((FAILS + FAILCOUNT))
else
  pass
fi

# Check 9: every ## §R row's Status cell matches one of the permitted
# terminal forms; an inherited prefix alone — from either PARTS.md or
# CATALOG.md — fails as non-terminal. Generalizes catalog-check.sh Check 26
# to accept the CATALOG.md-inherited prefix as a fourth recognised form.
FIELD9_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §R .*?\n(.*?)\n## Appendix A', text, re.S | re.M)
body = m.group(1) if m else ""

ID_RE = re.compile(r'^\| [A-Za-z]\d+ \|')
fails = []
n_checked = 0
for line in body.splitlines():
    if not ID_RE.match(line):
        continue
    row_id = line.strip().strip('|').split('|')[0].strip()
    n_checked += 1
    status_cell = line.rstrip().rsplit('|', 2)[-2].strip() if line.count('|') >= 2 else line
    is_repaired = "repaired in §" in status_cell
    is_no_amendment = status_cell.startswith("recorded, no amendment")
    is_deferred = "deferred —" in status_cell
    is_bare_inherited = (
        (status_cell.startswith("inherited from PARTS.md") or status_cell.startswith("inherited from CATALOG.md"))
        and not is_deferred
        and not is_repaired
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
FIELD9_STATUS=$?
if [ "$FIELD9_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD9_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD9_OUT" | grep -cE '^FAIL: register-completeness' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 10: every ## §R row has a non-empty cell in every one of the seven
# columns; ANATOMY re-projection is either a list of entry ids or the
# explicit value "none — <reason>".
FIELD10_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §R .*?\n(.*?)\n## Appendix A', text, re.S | re.M)
body = m.group(1) if m else ""

ID_RE = re.compile(r'^\| [A-Za-z]\d+ \|')
fails = []
n_checked = 0
for line in body.splitlines():
    if not ID_RE.match(line):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    row_id = cells[0]
    n_checked += 1
    if len(cells) != 7:
        fails.append(f"row {row_id}: {len(cells)} columns, expected 7")
        continue
    for col_name, val in zip(
        ["#", "Clause", "Defect", "Repair direction", "Forcing requirement", "ANATOMY re-projection", "Status"],
        cells,
    ):
        if not val:
            fails.append(f"row {row_id}: empty cell in column {col_name!r}")
    anatomy_cell = cells[5]
    if not (anatomy_cell.startswith("none —") or anatomy_cell.startswith("none -")) and "entry" not in anatomy_cell and "not yet re-projected" not in anatomy_cell:
        fails.append(f"row {row_id}: ANATOMY re-projection {anatomy_cell!r} is neither an entry-id list nor 'none — <reason>'")

if n_checked == 0:
    print("FAIL: register-no-empty-cells zero-rows-matched — ## §R section anchor not found or no rows matched")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: register-no-empty-cells {f}")
    sys.exit(1)
else:
    print(f"register-no-empty-cells OK ({n_checked} rows checked)")
    sys.exit(0)
PYEOF
)
FIELD10_STATUS=$?
if [ "$FIELD10_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD10_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD10_OUT" | grep -cE '^FAIL: register-no-empty-cells' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 11: every ## Appendix A row's Status cell is a member of the closed
# pair written / pending — plan 05-NN, and every pending row names a plan id
# whose PLAN.md file exists on disk.
PHASE_DIR="$(dirname "$0")/../phases/05-comparison-rig-versioning-mechanics"
FIELD11_OUT=$(python3 - "$DOC" "$PHASE_DIR" <<'PYEOF'
import re, sys, os
DOC, PHASE_DIR = sys.argv[1], sys.argv[2]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## Appendix A.*?\n(.*)\Z', text, re.S | re.M)
body = m.group(1) if m else ""

ROW_RE = re.compile(r'^\|.+\|$')
fails = []
n_checked = 0
for line in body.splitlines():
    if not ROW_RE.match(line):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if len(cells) != 4:
        continue
    if cells[0] in ("Requirement", "---") or set(cells[0]) <= {"-", " "}:
        continue
    req, status = cells[0], cells[3]
    n_checked += 1
    if status == "written":
        continue
    pm = re.match(r'^pending — plan (05-\d+)$', status)
    if not pm:
        fails.append(f"row {req!r}: Status {status!r} not in the closed pair written / pending — plan 05-NN")
        continue
    plan_path = os.path.join(PHASE_DIR, f"{pm.group(1)}-PLAN.md")
    if not os.path.isfile(plan_path):
        fails.append(f"row {req!r}: {plan_path} does not exist")

if n_checked == 0:
    print("FAIL: appendix-status-vocabulary zero-rows-matched — ## Appendix A anchor not found or no rows matched")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: appendix-status-vocabulary {f}")
    sys.exit(1)
else:
    print(f"appendix-status-vocabulary OK ({n_checked} rows checked)")
    sys.exit(0)
PYEOF
)
FIELD11_STATUS=$?
if [ "$FIELD11_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD11_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD11_OUT" | grep -cE '^FAIL: appendix-status-vocabulary' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 12: every requirement id RIG-01 through RIG-07 appears in exactly
# one ## Appendix A row's Requirement cell, and is named at least once
# inside the section that row's Discharged-by cell points at.
FIELD12_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## Appendix A.*?\n(.*)\Z', text, re.S | re.M)
appendix_body = m.group(1) if m else ""

ROW_RE = re.compile(r'^\|.+\|$')
rows = []
for line in appendix_body.splitlines():
    if not ROW_RE.match(line):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    if len(cells) != 4:
        continue
    if cells[0] in ("Requirement",) or set(cells[0]) <= {"-", " "}:
        continue
    rows.append(cells)

SECTION_HEADING_RE = {
    "§RUN": r'^## §RUN .*?\n(.*?)\n## ',
    "§TR": r'^## §TR .*?\n(.*?)\n## ',
    "§CM": r'^## §CM .*?\n(.*?)\n## ',
    "§EV": r'^## §EV .*?\n(.*?)\n## ',
    "§F3": r'^## §F3 .*?\n(.*?)\n## ',
    "§PR": r'^## §PR .*?\n(.*?)\n## ',
    "§AA": r'^## §AA .*?\n(.*?)\n## ',
    "§LC": r'^## §LC .*?\n(.*?)\n## ',
}

def section_body(sec_id):
    pattern = SECTION_HEADING_RE[sec_id]
    m2 = re.search(pattern, text, re.S | re.M)
    return m2.group(1) if m2 else ""

fails = []
seen = {}
for cells in rows:
    req, discharged_by = cells[0], cells[1]
    rm = re.match(r'^RIG-0[1-7]$', req)
    if not rm:
        continue
    seen[req] = seen.get(req, 0) + 1
    sec_ids = re.findall(r'§[A-Z0-9]+', discharged_by)
    if not sec_ids:
        fails.append(f"{req}: Discharged-by cell {discharged_by!r} names no section")
        continue
    found = False
    for sec_id in sec_ids:
        if sec_id in SECTION_HEADING_RE and req in section_body(sec_id):
            found = True
            break
    if not found:
        fails.append(f"{req}: not named inside the section(s) {sec_ids} its Appendix A row points at")

for n in range(1, 8):
    rig = f"RIG-{n:02d}"
    count = seen.get(rig, 0)
    if count == 0:
        fails.append(f"{rig}: missing from ## Appendix A entirely")
    elif count > 1:
        fails.append(f"{rig}: appears in {count} Appendix A rows, expected exactly 1")

if fails:
    for f in fails:
        print(f"FAIL: requirement-coverage {f}")
    sys.exit(1)
else:
    print("requirement-coverage OK (RIG-01..RIG-07 each in exactly one row, each named in its own section)")
    sys.exit(0)
PYEOF
)
FIELD12_STATUS=$?
if [ "$FIELD12_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD12_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD12_OUT" | grep -cE '^FAIL: requirement-coverage' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 13: ### §RUN.1 through ### §RUN.4 present, in order, inside ## §RUN.
FIELD13_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §RUN .*?\n(.*?)\n## §TR', text, re.S | re.M)
body = m.group(1) if m else ""

subs = ["### §RUN.1", "### §RUN.2", "### §RUN.3", "### §RUN.4"]
last = -1
fails = []
for s in subs:
    idx = body.find(s)
    if idx == -1:
        fails.append(f"missing {s}")
        continue
    if idx <= last:
        fails.append(f"{s} out of order (found before a preceding sub-clause)")
    last = idx

if fails:
    for f in fails:
        print(f"FAIL: run-subsections {f}")
    sys.exit(1)
else:
    print("run-subsections OK (§RUN.1..4 present, in order)")
    sys.exit(0)
PYEOF
)
FIELD13_STATUS=$?
if [ "$FIELD13_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD13_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD13_OUT" | grep -cE '^FAIL: run-subsections' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 14: ## §RUN names both VT-1 and GR-1 (D-11's worked example, not
# abstracted to arm A / arm B), and names N11 together with a Phase 6
# reference on the same clause line, so the deferral is machine-visible.
FIELD14_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §RUN .*?\n(.*?)\n## §TR', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if "VT-1" not in body:
    fails.append("'VT-1' not found inside ## §RUN")
if "GR-1" not in body:
    fails.append("'GR-1' not found inside ## §RUN")

n11_with_phase6 = False
for line in body.splitlines():
    if "N11" in line and "Phase 6" in line:
        n11_with_phase6 = True
        break
if not n11_with_phase6:
    fails.append("no ## §RUN line names both 'N11' and 'Phase 6' together")

if fails:
    for f in fails:
        print(f"FAIL: run-worked-example-and-n11 {f}")
    sys.exit(1)
else:
    print("run-worked-example-and-n11 OK (VT-1, GR-1 and N11/Phase 6 all present)")
    sys.exit(0)
PYEOF
)
FIELD14_STATUS=$?
if [ "$FIELD14_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD14_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD14_OUT" | grep -cE '^FAIL: run-worked-example-and-n11' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 15: ## §RUN states a distinct, named outcome for a zero-arm
# comparison request and for a one-arm fan-out — two different sentences,
# not the same one reused.
FIELD15_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §RUN .*?\n(.*?)\n## §TR', text, re.S | re.M)
body = m.group(1) if m else ""

zero_m = re.search(r'\*\*Zero arms\.\*\*\s+(.*)', body)
one_m = re.search(r'\*\*Exactly one arm\.\*\*\s+(.*)', body)

fails = []
if not zero_m:
    fails.append("no '**Zero arms.**' bullet found inside ## §RUN")
if not one_m:
    fails.append("no '**Exactly one arm.**' bullet found inside ## §RUN")
if zero_m and one_m and zero_m.group(1)[:80] == one_m.group(1)[:80]:
    fails.append("zero-arm and one-arm outcomes read as the same sentence")

if fails:
    for f in fails:
        print(f"FAIL: run-degenerate-widths {f}")
    sys.exit(1)
else:
    print("run-degenerate-widths OK (zero-arm and one-arm each state a distinct named outcome)")
    sys.exit(0)
PYEOF
)
FIELD15_STATUS=$?
if [ "$FIELD15_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD15_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD15_OUT" | grep -cE '^FAIL: run-degenerate-widths' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 16: ### §LC.1 through ### §LC.3 present, in order, inside ## §LC.
FIELD16_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §LC .*?\n(.*?)\n## §R ', text, re.S | re.M)
body = m.group(1) if m else ""

subs = ["### §LC.1", "### §LC.2", "### §LC.3"]
last = -1
fails = []
for s in subs:
    idx = body.find(s)
    if idx == -1:
        fails.append(f"missing {s}")
        continue
    if idx <= last:
        fails.append(f"{s} out of order (found before a preceding sub-clause)")
    last = idx

if fails:
    for f in fails:
        print(f"FAIL: lc-subsections {f}")
    sys.exit(1)
else:
    print("lc-subsections OK (§LC.1..3 present, in order)")
    sys.exit(0)
PYEOF
)
FIELD16_STATUS=$?
if [ "$FIELD16_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD16_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD16_OUT" | grep -cE '^FAIL: lc-subsections' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 17: ## §LC names all three stop modes (Budget-halt, Watchdog, Manual
# stop), each with its own distinct stop_reason value.
FIELD17_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §LC .*?\n(.*?)\n## §R ', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if "**Budget-halt**" not in body:
    fails.append("no '**Budget-halt**' stop mode found inside ## §LC")
if "**Watchdog**" not in body:
    fails.append("no '**Watchdog**' stop mode found inside ## §LC")
if "**Manual stop**" not in body:
    fails.append("no '**Manual stop**' stop mode found inside ## §LC")

reasons = {"budget_halt", "watchdog_timeout", "manual_stop"}
missing_reasons = sorted(r for r in reasons if f"`{r}`" not in body)
if missing_reasons:
    fails.append(f"missing distinct stop_reason value(s): {missing_reasons}")

if fails:
    for f in fails:
        print(f"FAIL: lc-stop-modes {f}")
    sys.exit(1)
else:
    print("lc-stop-modes OK (all three stop modes named, each with its own stop_reason value)")
    sys.exit(0)
PYEOF
)
FIELD17_STATUS=$?
if [ "$FIELD17_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD17_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD17_OUT" | grep -cE '^FAIL: lc-stop-modes' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 18: ### §LC.3 contains both halves of D-13's conjunction (a
# determinism-stamp condition and a store-mutation condition), not only one,
# and contains an explicit statement of the otherwise-branch ("rerun from
# start").
FIELD18_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §LC\.3.*?\n(.*?)\n## §R ', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if not re.search(r'determinism stamp', body, re.I):
    fails.append("no determinism-stamp condition found inside ### §LC.3")
if not re.search(r'store mutation', body, re.I):
    fails.append("no store-mutation condition found inside ### §LC.3")
if "rerun from start" not in body:
    fails.append("no explicit 'rerun from start' otherwise-branch statement found inside ### §LC.3")

if fails:
    for f in fails:
        print(f"FAIL: lc-resume-conjunction {f}")
    sys.exit(1)
else:
    print("lc-resume-conjunction OK (both conjunction halves and the otherwise-branch are present)")
    sys.exit(0)
PYEOF
)
FIELD18_STATUS=$?
if [ "$FIELD18_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD18_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD18_OUT" | grep -cE '^FAIL: lc-resume-conjunction' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 19: every schema-defined trace field name that appears backticked
# inside ## §LC also appears backticked somewhere inside ## §TR — ## §LC
# mints no field name ## §TR.1 does not already publish.
FIELD19_OUT=$(python3 - "$DOC" "$(dirname "$0")/rig-trace.schema.json" <<'PYEOF'
import re, sys, json
DOC, SCHEMA = sys.argv[1], sys.argv[2]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

lc_m = re.search(r'^## §LC .*?\n(.*?)\n## §R ', text, re.S | re.M)
if not lc_m:
    print("FAIL: lc-fields-published-in-tr — ## §LC section anchor not found")
    sys.exit(1)
lc_body = lc_m.group(1)
tr_m = re.search(r'^## §TR .*?\n(.*?)\n## §CM', text, re.S | re.M)
if not tr_m:
    print("FAIL: lc-fields-published-in-tr — ## §TR section anchor not found")
    sys.exit(1)
tr_body = tr_m.group(1)

with open(SCHEMA, encoding="utf-8") as f:
    schema = json.load(f)
run_props = set(schema.get("properties", {}).keys()) - {"status", "status_note"}
node_props = set(schema.get("$defs", {}).get("NodeTrace", {}).get("properties", {}).keys())
token_props = set(schema.get("$defs", {}).get("TokenAccounting", {}).get("properties", {}).keys())
schema_fields = run_props | node_props | token_props

lc_tokens = set(re.findall(r'`([a-z_]+)`', lc_body))
lc_field_tokens = lc_tokens & schema_fields

fails = []
for tok in sorted(lc_field_tokens):
    if f"`{tok}`" not in tr_body:
        fails.append(f"field {tok!r} used inside ## §LC but not backticked anywhere inside ## §TR")

if fails:
    for f in fails:
        print(f"FAIL: lc-fields-published-in-tr {f}")
    sys.exit(1)
else:
    print(f"lc-fields-published-in-tr OK ({len(lc_field_tokens)} schema fields referenced in ## §LC, all published in ## §TR)")
    sys.exit(0)
PYEOF
)
FIELD19_STATUS=$?
if [ "$FIELD19_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD19_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD19_OUT" | grep -cE '^FAIL: lc-fields-published-in-tr' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 20: ### §CM.1 through ### §CM.3 present, in order, inside ## §CM.
FIELD20_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §CM .*?\n(.*?)\n## §EV', text, re.S | re.M)
body = m.group(1) if m else ""

subs = ["### §CM.1", "### §CM.2", "### §CM.3"]
last = -1
fails = []
for s in subs:
    m2 = re.search(re.escape(s) + r'(?:\s|$)', body, re.M)
    idx = m2.start() if m2 else -1
    if idx == -1:
        fails.append(f"missing {s}")
        continue
    if idx <= last:
        fails.append(f"{s} out of order (found before a preceding sub-clause)")
    last = idx

if fails:
    for f in fails:
        print(f"FAIL: cm-subsections {f}")
    sys.exit(1)
else:
    print("cm-subsections OK (§CM.1..3 present, in order)")
    sys.exit(0)
PYEOF
)
FIELD20_STATUS=$?
if [ "$FIELD20_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD20_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD20_OUT" | grep -cE '^FAIL: cm-subsections' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 21: ## §CM contains the D-10 code-verified anchor strings (both digit
# and comma-grouped forms accepted) plus the pin string.
FIELD21_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §CM .*?\n(.*?)\n## §EV', text, re.S | re.M)
body = m.group(1) if m else ""

checks = [
    ("30,000 ceiling", any(s in body for s in ("30,000", "30000"))),
    ("1,200-token chunk", any(s in body for s in ("1,200", "1200"))),
    ("DEFAULT_MAX_EXTRACT_INPUT_TOKENS ceiling (20480)", "20480" in body or "20,480" in body),
    ("DEFAULT_MAX_GLEANING", "DEFAULT_MAX_GLEANING" in body),
    ("run_gleaning", "run_gleaning" in body),
    ("pin commit b93f7c31f", "b93f7c31f" in body),
]
fails = [name for name, ok in checks if not ok]

if fails:
    for f in fails:
        print(f"FAIL: cm-anchor-strings missing {f}")
    sys.exit(1)
else:
    print("cm-anchor-strings OK (all six D-10 anchor strings present)")
    sys.exit(0)
PYEOF
)
FIELD21_STATUS=$?
if [ "$FIELD21_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD21_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD21_OUT" | grep -cE '^FAIL: cm-anchor-strings' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 22: ## §CM states both the RT-selfimprove.md original figure and this
# phase's corrected figure, side by side, for both the query-side and
# index-side anchors -- never one figure carried forward silently.
FIELD22_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §CM .*?\n(.*?)\n## §EV', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if "~10,000" not in body and "~10k" not in body:
    fails.append("no '~10,000 tokens/query' original RT-selfimprove figure found")
if not any(s in body for s in ("30,000", "30000")):
    fails.append("no '30,000' corrected ceiling figure found")
if "15M" not in body and "15 M" not in body:
    fails.append("no '15M tokens per recipe version' original RT-selfimprove figure found")
if not (("83.9" in body or "~84" in body) and ("116.9" in body or "~117" in body)):
    fails.append("corrected index-side band (83.9/116.9 or ~84/~117) not both present")

if fails:
    for f in fails:
        print(f"FAIL: cm-original-and-corrected {f}")
    sys.exit(1)
else:
    print("cm-original-and-corrected OK (both original and corrected figures present, query-side and index-side)")
    sys.exit(0)
PYEOF
)
FIELD22_STATUS=$?
if [ "$FIELD22_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD22_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD22_OUT" | grep -cE '^FAIL: cm-original-and-corrected' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 23: ## §CM names both VT-1 and GR-1, and states VT-1's index side has
# no LLM extraction call to price.
FIELD23_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §CM .*?\n(.*?)\n## §EV', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if "VT-1" not in body:
    fails.append("'VT-1' not found inside ## §CM")
if "GR-1" not in body:
    fails.append("'GR-1' not found inside ## §CM")
if not re.search(r'VT-1.{0,400}no LLM extraction', body, re.S) and not re.search(r'no LLM extraction.{0,400}VT-1', body, re.S):
    fails.append("no clause states VT-1 has no LLM extraction call to price")

if fails:
    for f in fails:
        print(f"FAIL: cm-vt1-gr1-no-extraction {f}")
    sys.exit(1)
else:
    print("cm-vt1-gr1-no-extraction OK (VT-1, GR-1 both named; VT-1's zero-extraction stated)")
    sys.exit(0)
PYEOF
)
FIELD23_STATUS=$?
if [ "$FIELD23_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD23_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD23_OUT" | grep -cE '^FAIL: cm-vt1-gr1-no-extraction' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 24: ## §CM states the 2x sensitivity result with both the low-end and
# high-end percentage movements (D-10's own requirement).
FIELD24_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §CM\.3.*?\n(.*?)\n## §EV', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if "14%" not in body:
    fails.append("no low-end '+14%' sensitivity movement found inside ### §CM.3")
if "38%" not in body:
    fails.append("no high-end '+38%' sensitivity movement found inside ### §CM.3")

if fails:
    for f in fails:
        print(f"FAIL: cm-sensitivity {f}")
    sys.exit(1)
else:
    print("cm-sensitivity OK (both the +14% and +38% movements stated)")
    sys.exit(0)
PYEOF
)
FIELD24_STATUS=$?
if [ "$FIELD24_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD24_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD24_OUT" | grep -cE '^FAIL: cm-sensitivity' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 25: every markdown table row inside ## §CM that contains a digit
# carries at least one of the four claim tags on that same row -- D-10's
# per-input-tagging rule, enforced mechanically rather than trusted. A looser
# tag pattern than Checks 7/8 is intentional here: a table cell is allowed to
# carry a colon-qualified tag (e.g. "[code-verified: constants.py:56]") that
# names its own provenance inline, which Checks 7/8's exact-bracket form does
# not need to accommodate since those checks exclude table rows entirely.
FIELD25_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §CM .*?\n(.*?)\n## §EV', text, re.S | re.M)
body = m.group(1) if m else ""

TAG_RE = re.compile(r'\[(code-verified|docs-verified|paper-claim|inference)')
SEP_RE = re.compile(r'^\|[\s:|-]+\|$')
lines = body.splitlines()
fails = []
n_checked = 0
for lineno, line in enumerate(lines, start=1):
    stripped = line.strip()
    if not stripped.startswith("|"):
        continue
    if SEP_RE.match(stripped):
        continue  # a separator row, e.g. |---|---|
    # A header row is any row immediately followed by a separator row --
    # skip it regardless of whether a header cell happens to contain a
    # digit (e.g. a column whose header text cites "RT-selfimprove §2.7").
    next_stripped = lines[lineno].strip() if lineno < len(lines) else ""
    if SEP_RE.match(next_stripped):
        continue
    if not re.search(r'\d', stripped):
        continue
    n_checked += 1
    if not TAG_RE.search(stripped):
        fails.append(f"line ~{lineno}: {stripped[:90]!r}")

if n_checked == 0:
    print("FAIL: cm-table-row-tags zero-rows-matched — no digit-bearing table row found inside ## §CM")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: cm-table-row-tags {f}")
    sys.exit(1)
else:
    print(f"cm-table-row-tags OK ({n_checked} digit-bearing table rows checked, all tagged)")
    sys.exit(0)
PYEOF
)
FIELD25_STATUS=$?
if [ "$FIELD25_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD25_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD25_OUT" | grep -cE '^FAIL: cm-table-row-tags' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 26: ### §EV.1 through ### §EV.3 present, in order, inside ## §EV.
FIELD26_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §EV .*?\n(.*?)\n## §F3', text, re.S | re.M)
body = m.group(1) if m else ""

subs = ["### §EV.1", "### §EV.2", "### §EV.3"]
last = -1
fails = []
for s in subs:
    m2 = re.search(re.escape(s) + r'(?:\s|$)', body, re.M)
    idx = m2.start() if m2 else -1
    if idx == -1:
        fails.append(f"missing {s}")
        continue
    if idx <= last:
        fails.append(f"{s} out of order (found before a preceding sub-clause)")
    last = idx

if fails:
    for f in fails:
        print(f"FAIL: ev-subsections {f}")
    sys.exit(1)
else:
    print("ev-subsections OK (§EV.1..3 present, in order)")
    sys.exit(0)
PYEOF
)
FIELD26_STATUS=$?
if [ "$FIELD26_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD26_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD26_OUT" | grep -cE '^FAIL: ev-subsections' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 27: ## §EV names dev/holdout/sealed, both target families, and both
# paired-statistic test names.
FIELD27_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §EV .*?\n(.*?)\n## §F3', text, re.S | re.M)
body = m.group(1) if m else ""

required = ["dev", "holdout", "sealed", "gold-passage", "answer-level", "McNemar", "bootstrap"]
fails = [f"{r!r} not found inside ## §EV" for r in required if r not in body]

if fails:
    for f in fails:
        print(f"FAIL: ev-vocabulary {f}")
    sys.exit(1)
else:
    print("ev-vocabulary OK (dev/holdout/sealed, both target families, both test names all present)")
    sys.exit(0)
PYEOF
)
FIELD27_STATUS=$?
if [ "$FIELD27_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD27_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD27_OUT" | grep -cE '^FAIL: ev-vocabulary' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 28: ### §EV.3 contains the 2.8016 constant and at least three distinct
# (n, d) pairs — 0.44 at n=40, 0.28 at n=100, 0.129 at n=470 — so an asserted
# MDE with no shown working fails the gate.
FIELD28_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §EV\.3.*?\n(.*?)\n## §F3', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if "2.8016" not in body:
    fails.append("constant '2.8016' not found inside ### §EV.3")
if "40" not in body or ("0.44" not in body and "0.443" not in body):
    fails.append("n=40 / d≈0.44 pair not found inside ### §EV.3")
if "100" not in body or ("0.28" not in body and "0.280" not in body):
    fails.append("n=100 / d≈0.28 pair not found inside ### §EV.3")
if "470" not in body or "0.129" not in body:
    fails.append("n=470 / d≈0.129 pair not found inside ### §EV.3")

if fails:
    for f in fails:
        print(f"FAIL: ev-mde-derivation {f}")
    sys.exit(1)
else:
    print("ev-mde-derivation OK (2.8016 constant and all three (n, d) pairs present)")
    sys.exit(0)
PYEOF
)
FIELD28_STATUS=$?
if [ "$FIELD28_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD28_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD28_OUT" | grep -cE '^FAIL: ev-mde-derivation' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 29: ### §EV.3 contains the judge-noise compounding expression and
# states the answer-level reason as independent of the cost argument.
FIELD29_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §EV\.3.*?\n(.*?)\n## §F3', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if not re.search(r'SD_effective|sqrt\(SD_true', body):
    fails.append("no judge-noise compounding expression (SD_effective / sqrt(SD_true...)) found inside ### §EV.3")
if "independent of" not in body:
    fails.append("no 'independent of' phrase attached to the judge-noise reason inside ### §EV.3")

if fails:
    for f in fails:
        print(f"FAIL: ev-judge-noise-independent {f}")
    sys.exit(1)
else:
    print("ev-judge-noise-independent OK (compounding expression and 'independent of' both present)")
    sys.exit(0)
PYEOF
)
FIELD29_STATUS=$?
if [ "$FIELD29_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD29_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD29_OUT" | grep -cE '^FAIL: ev-judge-noise-independent' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 30: ## §EV either discharges or explicitly hands on ANATOMY.md entry
# 10's (MIG) costing fence, naming the four-way reindex classification; and
# ## §EV cites CONTRACT §10 at least three times (D-11/D-09 precedent: a
# section built on §10 should read like it, not merely gesture at it once).
FIELD30_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §EV .*?\n(.*?)\n## §F3', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if "MIG" not in body:
    fails.append("ANATOMY.md entry 10 (MIG) not named inside ## §EV")
if not re.search(r're-embed', body) or not re.search(r'rebuild', body):
    fails.append("§6's four-way reindex classification (re-embed/rebuild) not named inside ## §EV")

contract10_count = len(re.findall(r'CONTRACT §10', body))
if contract10_count < 3:
    fails.append(f"CONTRACT §10 cited only {contract10_count} time(s) inside ## §EV, expected at least 3")

if fails:
    for f in fails:
        print(f"FAIL: ev-mig-fence {f}")
    sys.exit(1)
else:
    print(f"ev-mig-fence OK (MIG's costing fence discharged, CONTRACT §10 cited {contract10_count} times)")
    sys.exit(0)
PYEOF
)
FIELD30_STATUS=$?
if [ "$FIELD30_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD30_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD30_OUT" | grep -cE '^FAIL: ev-mig-fence' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 31: ### §F3.1 and ### §F3.2 present, in order, inside ## §F3.
FIELD31_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §F3 .*?\n(.*?)\n## §PR', text, re.S | re.M)
body = m.group(1) if m else ""

subs = ["### §F3.1", "### §F3.2"]
last = -1
fails = []
for s in subs:
    m2 = re.search(re.escape(s) + r'(?:\s|$)', body, re.M)
    idx = m2.start() if m2 else -1
    if idx == -1:
        fails.append(f"missing {s}")
        continue
    if idx <= last:
        fails.append(f"{s} out of order (found before a preceding sub-clause)")
    last = idx

if fails:
    for f in fails:
        print(f"FAIL: f3-subsections {f}")
    sys.exit(1)
else:
    print("f3-subsections OK (§F3.1..2 present, in order)")
    sys.exit(0)
PYEOF
)
FIELD31_STATUS=$?
if [ "$FIELD31_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD31_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD31_OUT" | grep -cE '^FAIL: f3-subsections' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 32: ## §F3 names all three mutation classes.
FIELD32_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §F3 .*?\n(.*?)\n## §PR', text, re.S | re.M)
body = m.group(1) if m else ""

required = ["retrieval-side", "answer-level", "index-side"]
fails = [f"{r!r} not found inside ## §F3" for r in required if r not in body]

if fails:
    for f in fails:
        print(f"FAIL: f3-three-classes {f}")
    sys.exit(1)
else:
    print("f3-three-classes OK (retrieval-side, answer-level, index-side all named)")
    sys.exit(0)
PYEOF
)
FIELD32_STATUS=$?
if [ "$FIELD32_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD32_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD32_OUT" | grep -cE '^FAIL: f3-three-classes' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 33: ### §F3.1 states a distinct, named disposition sentence per
# mutation class -- one shared verdict reused three times fails this gate.
FIELD33_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §F3\.1.*?\n(.*?)\n### §F3\.2', text, re.S | re.M)
body = m.group(1) if m else ""

markers = {
    "retrieval-side": r'\*\*Retrieval-side.*?affordable,\s*confirmed',
    "answer-level": r'\*\*Answer-level.*?escalated-survivors-only posture',
    "index-side": r'\*\*Index-side.*?not affordable outside',
}
fails = []
for name, pat in markers.items():
    if not re.search(pat, body, re.S):
        fails.append(f"no distinct disposition sentence found for {name}")

if fails:
    for f in fails:
        print(f"FAIL: f3-distinct-dispositions {f}")
    sys.exit(1)
else:
    print("f3-distinct-dispositions OK (three distinct per-class disposition sentences found)")
    sys.exit(0)
PYEOF
)
FIELD33_STATUS=$?
if [ "$FIELD33_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD33_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD33_OUT" | grep -cE '^FAIL: f3-distinct-dispositions' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 34: ### §F3.2 names each of the literal capability names promote-next,
# promote-now, check, preview, run -- D-05's two enumerations cannot silently
# shrink.
FIELD34_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §F3\.2.*?\n(.*?)\n## §PR', text, re.S | re.M)
body = m.group(1) if m else ""

required = ["`promote-next`", "`promote-now`", "`check`", "`preview`", "`run`"]
fails = [f"{r!r} not found inside ### §F3.2" for r in required if r not in body]

if fails:
    for f in fails:
        print(f"FAIL: f3-posture-capabilities {f}")
    sys.exit(1)
else:
    print("f3-posture-capabilities OK (promote-next/promote-now/check/preview/run all present)")
    sys.exit(0)
PYEOF
)
FIELD34_STATUS=$?
if [ "$FIELD34_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD34_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD34_OUT" | grep -cE '^FAIL: f3-posture-capabilities' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 35: ### §F3.3 present inside ## §F3, after ### §F3.2.
FIELD35_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §F3 .*?\n(.*?)\n## §PR', text, re.S | re.M)
body = m.group(1) if m else ""

subs = ["### §F3.1", "### §F3.2", "### §F3.3"]
last = -1
fails = []
for s in subs:
    m2 = re.search(re.escape(s) + r'(?:\s|$)', body, re.M)
    idx = m2.start() if m2 else -1
    if idx == -1:
        fails.append(f"missing {s}")
        continue
    if idx <= last:
        fails.append(f"{s} out of order (found before a preceding sub-clause)")
    last = idx

if fails:
    for f in fails:
        print(f"FAIL: f3-3-present {f}")
    sys.exit(1)
else:
    print("f3-3-present OK (§F3.1..3 present, in order)")
    sys.exit(0)
PYEOF
)
FIELD35_STATUS=$?
if [ "$FIELD35_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD35_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD35_OUT" | grep -cE '^FAIL: f3-3-present' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 36: ### §F3.3 contains four distinct rung blocks, each with its own
# sacrifice statement — a rung with no stated sacrifice fails the gate.
FIELD36_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §F3\.3.*?\n(.*?)\n## §PR', text, re.S | re.M)
body = m.group(1) if m else ""

rungs = re.findall(r'\*\*Rung \d — [^*]+\*\*.*', body)
fails = []
if len(rungs) != 4:
    fails.append(f"found {len(rungs)} rung blocks, expected exactly 4")
for i, r in enumerate(rungs, start=1):
    if "Sacrifice:" not in r:
        fails.append(f"rung {i} has no 'Sacrifice:' statement")

if fails:
    for f in fails:
        print(f"FAIL: f3-rung-sacrifices {f}")
    sys.exit(1)
else:
    print(f"f3-rung-sacrifices OK ({len(rungs)} rungs, each with a stated sacrifice)")
    sys.exit(0)
PYEOF
)
FIELD36_STATUS=$?
if [ "$FIELD36_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD36_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD36_OUT" | grep -cE '^FAIL: f3-rung-sacrifices' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 37: ### §F3.3 names both a within-batch early-stopping mechanism and
# states that the across-batch multiple-comparisons correction belongs to
# ## §AA, in the same paragraph — so the sequential-vs-batch tension is
# visibly resolved rather than left for a reader to reconstruct.
FIELD37_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §F3\.3.*?\n(.*?)\n## §PR', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
rung3_m = re.search(r'\*\*Rung 3.*', body)
rung3 = rung3_m.group(0) if rung3_m else ""
if not re.search(r'\bwithin\b', rung3):
    fails.append("no within-batch early-stopping mechanism named inside Rung 3")
if "## §AA" not in rung3:
    fails.append("Rung 3 does not name ## §AA as owner of the across-batch multiple-comparisons correction")
if not re.search(r'\bacross\b', rung3):
    fails.append("no across-batch correction named inside Rung 3")

if fails:
    for f in fails:
        print(f"FAIL: f3-sequential-tension {f}")
    sys.exit(1)
else:
    print("f3-sequential-tension OK (within-batch and across-batch mechanisms both named, same paragraph)")
    sys.exit(0)
PYEOF
)
FIELD37_STATUS=$?
if [ "$FIELD37_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD37_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD37_OUT" | grep -cE '^FAIL: f3-sequential-tension' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 38: ### §F3.3 names both degraded and degradation_reason, wiring the
# labelling rule to the trace's own fields.
FIELD38_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §F3\.3.*?\n(.*?)\n## §PR', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if "`degraded`" not in body:
    fails.append("'`degraded`' not found inside ### §F3.3")
if "`degradation_reason`" not in body:
    fails.append("'`degradation_reason`' not found inside ### §F3.3")

if fails:
    for f in fails:
        print(f"FAIL: f3-labelling-fields {f}")
    sys.exit(1)
else:
    print("f3-labelling-fields OK (degraded and degradation_reason both named)")
    sys.exit(0)
PYEOF
)
FIELD38_STATUS=$?
if [ "$FIELD38_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD38_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD38_OUT" | grep -cE '^FAIL: f3-labelling-fields' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 39: ## §R contains at least one R-family row, and the R-family row
# whose Clause cell names CONTRACT.md §6 has a terminal Status beginning
# "repaired in §".
FIELD39_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §R .*?\n(.*?)\n## Appendix A', text, re.S | re.M)
body = m.group(1) if m else ""

ROW_RE = re.compile(r'^\| (R\d+) \|(.*)\|$')
fails = []
r_rows = []
for line in body.splitlines():
    m2 = ROW_RE.match(line.strip())
    if not m2:
        continue
    row_id = m2.group(1)
    cells = [c.strip() for c in m2.group(2).split('|')]
    r_rows.append((row_id, cells))

if not r_rows:
    fails.append("no R-family row found in ## §R")
else:
    found_contract_6 = False
    for row_id, cells in r_rows:
        clause_cell = cells[0] if cells else ""
        status_cell = cells[-1] if cells else ""
        if "CONTRACT.md §6" in clause_cell:
            found_contract_6 = True
            if not status_cell.startswith("repaired in §"):
                fails.append(f"row {row_id}: Status {status_cell!r} does not begin 'repaired in §'")
    if not found_contract_6:
        fails.append("no R-family row's Clause cell names CONTRACT.md §6")

if fails:
    for f in fails:
        print(f"FAIL: r-family-repair-row {f}")
    sys.exit(1)
else:
    print(f"r-family-repair-row OK ({len(r_rows)} R-family row(s) checked)")
    sys.exit(0)
PYEOF
)
FIELD39_STATUS=$?
if [ "$FIELD39_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD39_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD39_OUT" | grep -cE '^FAIL: r-family-repair-row' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 40: cross-file check — CONTRACT.md §6 contains the D-07 field name
# and both value names, plus the cross-field required/never-defaulted/
# never-inferable-by-absence rule; CONTRACT.md §7's ledger schema
# enumeration carries the same field name. A missing CONTRACT.md is a
# named failure, never a silent skip.
CONTRACT_DOC="$(dirname "$0")/CONTRACT.md"
FIELD40_OUT=$(python3 - "$CONTRACT_DOC" <<'PYEOF'
import re, sys, os
CONTRACT_DOC = sys.argv[1]

if not os.path.isfile(CONTRACT_DOC):
    print(f"FAIL: contract-provenance-repair CONTRACT.md not found at {CONTRACT_DOC}")
    sys.exit(1)

with open(CONTRACT_DOC, encoding="utf-8") as f:
    text = f.read()

m6 = re.search(r'^## §6 .*?\n(.*?)\n## §7', text, re.S | re.M)
sec6 = m6.group(1) if m6 else ""
m7 = re.search(r'^## §7 .*?\n(.*?)\n## §8', text, re.S | re.M)
sec7 = m7.group(1) if m7 else ""

fails = []
if not sec6:
    fails.append("CONTRACT.md §6 section not found")
if not sec7:
    fails.append("CONTRACT.md §7 section not found")

for token in ["promotion_provenance", "gate_adjudicated", "operator_asserted"]:
    if token not in sec6:
        fails.append(f"'{token}' not found inside CONTRACT.md §6")
if "never defaulted" not in sec6:
    fails.append("'never defaulted' not found inside CONTRACT.md §6")
if "never inferable by absence" not in sec6:
    fails.append("'never inferable by absence' not found inside CONTRACT.md §6")
if "no special case" not in sec6:
    fails.append("'no special case' not found inside CONTRACT.md §6")

if "promotion_provenance" not in sec7:
    fails.append("'promotion_provenance' not found inside CONTRACT.md §7's ledger record schema")
if "promotion_trace_ids" not in sec7:
    fails.append("'promotion_trace_ids' not found inside CONTRACT.md §7's ledger record schema")

if fails:
    for f in fails:
        print(f"FAIL: contract-provenance-repair {f}")
    sys.exit(1)
else:
    print("contract-provenance-repair OK (field name, both values, cross-field rule and §7 widening all present)")
    sys.exit(0)
PYEOF
)
FIELD40_STATUS=$?
if [ "$FIELD40_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD40_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD40_OUT" | grep -cE '^FAIL: contract-provenance-repair' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 41: ### §PR.1 through ### §PR.4 present, in order, inside ## §PR.
FIELD41_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §PR .*?\n(.*?)\n## §AA', text, re.S | re.M)
body = m.group(1) if m else ""

subs = ["### §PR.1", "### §PR.2", "### §PR.3", "### §PR.4"]
last = -1
fails = []
for s in subs:
    # Anchor to a heading line (start of line), not an inline forward-citation
    # such as "the operator path ### §PR.3 states" appearing before the
    # actual heading.
    m2 = re.search(r'^' + re.escape(s) + r'(?:\s|$)', body, re.M)
    idx = m2.start() if m2 else -1
    if idx == -1:
        fails.append(f"missing {s}")
        continue
    if idx <= last:
        fails.append(f"{s} out of order (found before a preceding sub-clause)")
    last = idx

if fails:
    for f in fails:
        print(f"FAIL: pr-subsections {f}")
    sys.exit(1)
else:
    print("pr-subsections OK (§PR.1..4 present, in order)")
    sys.exit(0)
PYEOF
)
FIELD41_STATUS=$?
if [ "$FIELD41_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD41_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD41_OUT" | grep -cE '^FAIL: pr-subsections' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 42: ## §PR names both provenance values and the D-07 field name.
FIELD42_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §PR .*?\n(.*?)\n## §AA', text, re.S | re.M)
body = m.group(1) if m else ""

required = ["promotion_provenance", "gate_adjudicated", "operator_asserted"]
fails = [f"{r!r} not found inside ## §PR" for r in required if r not in body]

if fails:
    for f in fails:
        print(f"FAIL: pr-provenance-values {f}")
    sys.exit(1)
else:
    print("pr-provenance-values OK (field name and both values named)")
    sys.exit(0)
PYEOF
)
FIELD42_STATUS=$?
if [ "$FIELD42_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD42_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD42_OUT" | grep -cE '^FAIL: pr-provenance-values' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 43: ### §PR.4 states both branches of the batch rule — one-winner
# and composite-re-run — as two distinct branches, not one.
FIELD43_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §PR\.4.*?\n(.*?)\n## §AA', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if not re.search(r'one winner', body, re.I):
    fails.append("no 'one winner' branch found inside ### §PR.4")
if not re.search(r'composite re-run', body, re.I):
    fails.append("no 'composite re-run' branch found inside ### §PR.4")

if fails:
    for f in fails:
        print(f"FAIL: pr4-batch-branches {f}")
    sys.exit(1)
else:
    print("pr4-batch-branches OK (both branches present)")
    sys.exit(0)
PYEOF
)
FIELD43_STATUS=$?
if [ "$FIELD43_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD43_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD43_OUT" | grep -cE '^FAIL: pr4-batch-branches' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 44: ## §PR names ## §AA as the owner of the multiple-comparisons
# correction and does not itself state a floor correction.
FIELD44_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §PR .*?\n(.*?)\n## §AA', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if "## §AA" not in body:
    fails.append("'## §AA' not named inside ## §PR")
if not re.search(r'multiple.comparisons', body, re.I):
    fails.append("no reference to the multiple-comparisons correction inside ## §PR")
if re.search(r'## §PR.{0,400}states\s+(a|its own)\s+floor correction', body, re.I | re.S):
    fails.append("## §PR appears to state its own floor correction")

if fails:
    for f in fails:
        print(f"FAIL: pr-aa-ownership {f}")
    sys.exit(1)
else:
    print("pr-aa-ownership OK (## §AA named as owner, no floor correction stated here)")
    sys.exit(0)
PYEOF
)
FIELD44_STATUS=$?
if [ "$FIELD44_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD44_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD44_OUT" | grep -cE '^FAIL: pr-aa-ownership' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 45: ### §AA.1 and ### §AA.2 present, in order, inside ## §AA.
FIELD45_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §AA .*?\n(.*?)\n## §LC', text, re.S | re.M)
body = m.group(1) if m else ""

subs = ["### §AA.1", "### §AA.2"]
last = -1
fails = []
if not body:
    fails.append("## §AA body not found")
for s in subs:
    m2 = re.search(r'^' + re.escape(s) + r'(?:\s|$)', body, re.M)
    idx = m2.start() if m2 else -1
    if idx == -1:
        fails.append(f"missing {s}")
        continue
    if idx <= last:
        fails.append(f"{s} out of order (found before a preceding sub-clause)")
    last = idx

if fails:
    for f in fails:
        print(f"FAIL: aa-subsections-12 {f}")
    sys.exit(1)
else:
    print("aa-subsections-12 OK (§AA.1, §AA.2 present, in order)")
    sys.exit(0)
PYEOF
)
FIELD45_STATUS=$?
if [ "$FIELD45_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD45_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD45_OUT" | grep -cE '^FAIL: aa-subsections-12' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 46: ## §AA contains the literal triple "(bundle@v, tier, metric)"
# at least twice.
FIELD46_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §AA .*?\n(.*?)\n## §LC', text, re.S | re.M)
body = m.group(1) if m else ""

count = body.count("(bundle@v, tier, metric)")
if count < 2:
    print(f"FAIL: aa-triple-count found {count} vs at least 2")
    sys.exit(1)
else:
    print(f"aa-triple-count OK ({count} occurrences)")
    sys.exit(0)
PYEOF
)
FIELD46_STATUS=$?
if [ "$FIELD46_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD46_OUT"
  FAILS=$((FAILS + 1))
fi

# Check 47: ### §AA.1 resolves a delta landing exactly on the p95 floor as
# one unambiguous clause.
FIELD47_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §AA\.1.*?\n(.*?)\n### §AA\.2', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if not body:
    fails.append("### §AA.1 body not found")
if not re.search(r'exactly.{0,80}floor', body, re.I | re.S) and not re.search(r'floor.{0,80}exactly', body, re.I | re.S):
    fails.append("no clause reading a delta 'exactly' on the floor")
if not re.search(r'does\s+\*\*not\*\*\s+promote|MUST NOT promote', body, re.I):
    fails.append("no unambiguous 'does not promote' resolution for the boundary case")

if fails:
    for f in fails:
        print(f"FAIL: aa1-floor-boundary {f}")
    sys.exit(1)
else:
    print("aa1-floor-boundary OK (boundary resolved in one clause)")
    sys.exit(0)
PYEOF
)
FIELD47_STATUS=$?
if [ "$FIELD47_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD47_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD47_OUT" | grep -cE '^FAIL: aa1-floor-boundary' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 48: ### §AA.1 contains 'bootstrap' and a citation of ## §CM, so the
# replicate design is priced, not asserted.
FIELD48_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §AA\.1.*?\n(.*?)\n### §AA\.2', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if not re.search(r'bootstrap', body, re.I):
    fails.append("'bootstrap' not found inside ### §AA.1")
if "§CM" not in body:
    fails.append("no citation of §CM inside ### §AA.1")

if fails:
    for f in fails:
        print(f"FAIL: aa1-bootstrap-priced {f}")
    sys.exit(1)
else:
    print("aa1-bootstrap-priced OK (bootstrap design cited against §CM)")
    sys.exit(0)
PYEOF
)
FIELD48_STATUS=$?
if [ "$FIELD48_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD48_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD48_OUT" | grep -cE '^FAIL: aa1-bootstrap-priced' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 49: ### §AA.2 states cache bypass as a MUST precondition, states an
# unstamped null is unusable, names all three variance sources (judge
# self-disagreement tagged [inference]), cites SELECTION.md's open question
# on concurrency, and does not resolve N11.
FIELD49_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §AA\.2.*?\n(.*?)\n## §LC', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if not body:
    fails.append("### §AA.2 body not found")
if not (re.search(r'cache', body, re.I) and re.search(r'\bMUST\b', body)):
    fails.append("no 'cache' clause carrying a MUST obligation")
if not re.search(r'not usable as a floor|unusable as a floor', body, re.I):
    fails.append("no statement that an unstamped null is unusable as a floor")
if "judge self-disagreement" not in body.lower() and "judge self-disagreement" not in body:
    if not re.search(r'judge self-disagreement', body, re.I):
        fails.append("judge self-disagreement not named")
if not re.search(r'judge self-disagreement.{0,120}\[inference\]|\[inference\].{0,120}judge self-disagreement', body, re.I | re.S):
    fails.append("judge self-disagreement not tagged [inference] nearby")
if not re.search(r'sampling nondeterminism', body, re.I):
    fails.append("LLM sampling nondeterminism variance source not named")
if not re.search(r'concurrency-induced nondeterminism|concurrency.induced', body, re.I):
    fails.append("concurrency-induced nondeterminism variance source not named")
if "Open questions carried forward" not in body:
    fails.append("SELECTION.md's own open-question wording not cited")
if re.search(r'N11 is (resolved|closed)|closes N11|resolving N11', body, re.I):
    fails.append("### §AA.2 appears to resolve N11")

if fails:
    for f in fails:
        print(f"FAIL: aa2-cache-variance {f}")
    sys.exit(1)
else:
    print("aa2-cache-variance OK (cache precondition, unstamped-null rule, three variance sources, open concurrency question, N11 untouched)")
    sys.exit(0)
PYEOF
)
FIELD49_STATUS=$?
if [ "$FIELD49_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD49_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD49_OUT" | grep -cE '^FAIL: aa2-cache-variance' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 50: ### §AA.3 present inside ## §AA, after ### §AA.2.
FIELD50_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §AA .*?\n(.*?)\n## §LC', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
m2 = re.search(r'^### §AA\.2(?:\s|$)', body, re.M)
m3 = re.search(r'^### §AA\.3(?:\s|$)', body, re.M)
if not m2:
    fails.append("missing ### §AA.2")
if not m3:
    fails.append("missing ### §AA.3")
if m2 and m3 and m3.start() <= m2.start():
    fails.append("### §AA.3 out of order relative to ### §AA.2")

if fails:
    for f in fails:
        print(f"FAIL: aa3-present-ordered {f}")
    sys.exit(1)
else:
    print("aa3-present-ordered OK (§AA.3 present, after §AA.2)")
    sys.exit(0)
PYEOF
)
FIELD50_STATUS=$?
if [ "$FIELD50_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD50_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD50_OUT" | grep -cE '^FAIL: aa3-present-ordered' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 51: ### §AA.3 names BH/Benjamini-Hochberg, Dunnett, Holm and
# Bonferroni, with Bonferroni stated as not recommended for a reason in the
# same clause.
FIELD51_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §AA\.3.*?\n(.*?)\n## §LC', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if not body:
    fails.append("### §AA.3 body not found")
if not re.search(r'Benjamini-Hochberg|(?<![A-Za-z])BH(?![A-Za-z])', body):
    fails.append("no Benjamini-Hochberg/BH reference")
if "Dunnett" not in body:
    fails.append("'Dunnett' not found")
if "Holm" not in body:
    fails.append("'Holm' not found")
if not re.search(r'Bonferroni.{0,300}not recommended', body, re.I | re.S) and not re.search(r'not recommended.{0,300}Bonferroni', body, re.I | re.S):
    fails.append("Bonferroni not stated as not-recommended, with a reason, in the same clause")

if fails:
    for f in fails:
        print(f"FAIL: aa3-tier-schemes {f}")
    sys.exit(1)
else:
    print("aa3-tier-schemes OK (BH, Dunnett, Holm named; Bonferroni named and rejected with reason)")
    sys.exit(0)
PYEOF
)
FIELD51_STATUS=$?
if [ "$FIELD51_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD51_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD51_OUT" | grep -cE '^FAIL: aa3-tier-schemes' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 52: ### §AA.3 states the N/20 false-promotion quantity, an explicit
# reconciliation with §5's epoch-level FDR rule, and names ### §PR.4 as the
# owner of the sibling hazard without restating that hazard's own rule.
FIELD52_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §AA\.3.*?\n(.*?)\n## §LC', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if "N/20" not in body:
    fails.append("'N/20' false-promotion quantity not found")
if not re.search(r'epoch-level.{0,200}(nested|reconcil)', body, re.I | re.S) and not re.search(r'(nested|reconcil).{0,200}epoch-level', body, re.I | re.S):
    fails.append("no explicit reconciliation clause naming the epoch-level FDR correction")
if "### §PR.4" not in body:
    fails.append("### §PR.4 not named as owner of the sibling hazard")
if re.search(r'single arm', body, re.I):
    fails.append("### §AA.3 appears to restate ### §PR.4's own composite-re-run rule")

if fails:
    for f in fails:
        print(f"FAIL: aa3-reconcile-boundaries {f}")
    sys.exit(1)
else:
    print("aa3-reconcile-boundaries OK (N/20 stated, epoch-level FDR reconciled, ### §PR.4 named without restating its rule)")
    sys.exit(0)
PYEOF
)
FIELD52_STATUS=$?
if [ "$FIELD52_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD52_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD52_OUT" | grep -cE '^FAIL: aa3-reconcile-boundaries' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 53: cross-file — CONTRACT.md §5 carries the batch-width floor
# correction with a claim tag and a trace tag on the same line, and RIG.md's
# ## §R has an R-family row naming CONTRACT.md §5 with a Status beginning
# "repaired in §5".
CONTRACT_DOC="$(dirname "$0")/CONTRACT.md"
FIELD53_OUT=$(python3 - "$DOC" "$CONTRACT_DOC" <<'PYEOF'
import re, sys, os
DOC, CONTRACT_DOC = sys.argv[1], sys.argv[2]

fails = []
if not os.path.isfile(CONTRACT_DOC):
    print(f"FAIL: aa3-contract-r-repair CONTRACT.md not found at {CONTRACT_DOC}")
    sys.exit(1)

with open(CONTRACT_DOC, encoding="utf-8") as f:
    ctext = f.read()
m5 = re.search(r'^## §5 .*?\n(.*?)\n## §6', ctext, re.S | re.M)
sec5 = m5.group(1) if m5 else ""
if "batch-width" not in sec5.lower() and "batch width" not in sec5.lower():
    fails.append("no batch-width clause found inside CONTRACT.md §5")
else:
    claim_tags = ["[docs-verified]", "[code-verified]", "[paper-claim]", "[inference]"]
    ok_line = False
    for line in sec5.splitlines():
        if "batch-width" not in line.lower() and "batch width" not in line.lower():
            continue
        brackets = re.findall(r'\[[^\]]+\]', line)
        has_claim_tag = any(t in brackets for t in [ct.strip() for ct in claim_tags])
        # a trace tag is any bracket that is not itself one of the four claim tags
        has_trace_tag = any(b not in claim_tags for b in brackets)
        if has_claim_tag and has_trace_tag:
            ok_line = True
            break
    if not ok_line:
        fails.append("no line inside CONTRACT.md §5 carries both a claim tag and a trace tag alongside the batch-width clause")

with open(DOC, encoding="utf-8") as f:
    text = f.read()
mr = re.search(r'^## §R .*?\n(.*?)\n## Appendix A', text, re.S | re.M)
rbody = mr.group(1) if mr else ""
ROW_RE = re.compile(r'^\| (R\d+) \|(.*)\|$')
found = False
for line in rbody.splitlines():
    m2 = ROW_RE.match(line.strip())
    if not m2:
        continue
    cells = [c.strip() for c in m2.group(2).split('|')]
    clause_cell = cells[0] if cells else ""
    status_cell = cells[-1] if cells else ""
    if "CONTRACT.md §5" in clause_cell:
        found = True
        if not status_cell.startswith("repaired in §5"):
            fails.append(f"row {m2.group(1)}: Status {status_cell!r} does not begin 'repaired in §5'")
if not found:
    fails.append("no R-family row's Clause cell names CONTRACT.md §5")

if fails:
    for f in fails:
        print(f"FAIL: aa3-contract-r-repair {f}")
    sys.exit(1)
else:
    print("aa3-contract-r-repair OK (§5 batch-width clause tagged; R-family row terminal)")
    sys.exit(0)
PYEOF
)
FIELD53_STATUS=$?
if [ "$FIELD53_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD53_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD53_OUT" | grep -cE '^FAIL: aa3-contract-r-repair' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 54: ### §AA.4 present inside ## §AA, after ### §AA.3.
FIELD54_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §AA .*?\n(.*?)\n## §LC', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
m3 = re.search(r'^### §AA\.3(?:\s|$)', body, re.M)
m4 = re.search(r'^### §AA\.4(?:\s|$)', body, re.M)
if not m3:
    fails.append("missing ### §AA.3")
if not m4:
    fails.append("missing ### §AA.4")
if m3 and m4 and m4.start() <= m3.start():
    fails.append("### §AA.4 out of order relative to ### §AA.3")

if fails:
    for f in fails:
        print(f"FAIL: aa4-present-ordered {f}")
    sys.exit(1)
else:
    print("aa4-present-ordered OK (§AA.4 present, after §AA.3)")
    sys.exit(0)
PYEOF
)
FIELD54_STATUS=$?
if [ "$FIELD54_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD54_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD54_OUT" | grep -cE '^FAIL: aa4-present-ordered' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 55: ## §AA names both minted comparison modes, each at least twice.
FIELD55_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §AA .*?\n(.*?)\n## §LC', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
c1 = body.count("decomposition-parity mode")
c2 = body.count("architecture-comparison mode")
if c1 < 2:
    fails.append(f"'decomposition-parity mode' found {c1} times, need at least 2")
if c2 < 2:
    fails.append(f"'architecture-comparison mode' found {c2} times, need at least 2")

if fails:
    for f in fails:
        print(f"FAIL: aa4-mode-names {f}")
    sys.exit(1)
else:
    print(f"aa4-mode-names OK (decomposition-parity mode x{c1}, architecture-comparison mode x{c2})")
    sys.exit(0)
PYEOF
)
FIELD55_STATUS=$?
if [ "$FIELD55_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD55_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD55_OUT" | grep -cE '^FAIL: aa4-mode-names' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 56: ### §AA.4 states "parity, not gain" as not applicable in
# architecture-comparison mode, names §5's sixth refusal condition in the
# same context, and states an explicit A6 finding about held_constant
# between VT-1 and GR-1.
FIELD56_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^### §AA\.4.*?\n(.*?)\n## §LC', text, re.S | re.M)
body = m.group(1) if m else ""

fails = []
if not body:
    fails.append("### §AA.4 body not found")
if not re.search(r'parity,\s*not\s*gain.{0,200}not applicable', body, re.I | re.S) and not re.search(r'not applicable.{0,200}parity,\s*not\s*gain', body, re.I | re.S):
    fails.append("'parity, not gain' not stated as not applicable")
if not re.search(r'sixth.{0,200}(held_constant|refusal condition)', body, re.I | re.S):
    fails.append("§5's sixth refusal condition not named in the parity-not-gain context")
if not re.search(r'held_constant', body):
    fails.append("no held_constant finding present")
if not ("VT-1" in body and "GR-1" in body):
    fails.append("A6 finding does not name both VT-1 and GR-1")
if not re.search(r'trivially satisfied|share[s]? (almost )?nothing', body, re.I):
    fails.append("no stated A6 verdict (trivially satisfied / shares nothing)")

if fails:
    for f in fails:
        print(f"FAIL: aa4-parity-a6 {f}")
    sys.exit(1)
else:
    print("aa4-parity-a6 OK (parity-not-gain inapplicable, sixth condition named, A6 finding stated)")
    sys.exit(0)
PYEOF
)
FIELD56_STATUS=$?
if [ "$FIELD56_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD56_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD56_OUT" | grep -cE '^FAIL: aa4-parity-a6' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 57: RIG.md ## §R carries N6 and N9 each with seven non-empty cells
# and a terminal Status ("repaired in §" or "recorded, no amendment"), never
# "deferred — Phase 5"; N6's closure states both the fourth-condition
# consistency argument and the self-defeat argument as two distinct
# arguments; N9's closure names VT-1, GR-1 and the LightRAG arm family.
FIELD57_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

mr = re.search(r'^## §R .*?\n(.*?)\n## Appendix A', text, re.S | re.M)
rbody = mr.group(1) if mr else ""
ROW_RE = re.compile(r'^\| (N6|N9) \|(.*)\|$')

rows = {}
for line in rbody.splitlines():
    m2 = ROW_RE.match(line.strip())
    if m2:
        rows[m2.group(1)] = [c.strip() for c in m2.group(2).split('|')]

fails = []
for rid in ("N6", "N9"):
    if rid not in rows:
        fails.append(f"row {rid} not found in ## §R")
        continue
    cells = rows[rid]
    if len(cells) != 6 or any(c == "" for c in cells):
        fails.append(f"row {rid}: expected 6 further non-empty cells (7 total with id), got {cells}")
    status = cells[-1] if cells else ""
    if "deferred — Phase 5" in status:
        fails.append(f"row {rid}: Status still reads 'deferred — Phase 5'")
    if not (status.startswith("repaired in §") or status.startswith("recorded, no amendment")):
        fails.append(f"row {rid}: Status {status!r} not a permitted terminal form")

# N6 closure body (### §AA.4) — check for two distinct arguments.
maa4 = re.search(r'^### §AA\.4.*?\n(.*?)\n## §LC', text, re.S | re.M)
aa4 = maa4.group(1) if maa4 else ""
if not re.search(r'[Tt]extual consistency', aa4):
    fails.append("N6 closure missing the textual-consistency argument label")
if not re.search(r'[Ss]elf-defeat', aa4):
    fails.append("N6 closure missing the self-defeat argument label")

# N9 closure — VT-1, GR-1, LightRAG arm family named as evidence.
if "VT-1" not in aa4 or "GR-1" not in aa4:
    fails.append("N9 closure does not name both VT-1 and GR-1")
if not re.search(r'hybrid.{0,40}local.{0,40}global.{0,40}naive.{0,40}bypass|LightRAG.{0,80}(arm|merge-patch)', aa4, re.I | re.S):
    fails.append("N9 closure does not name the LightRAG arm family as evidence")

if fails:
    for f in fails:
        print(f"FAIL: n6-n9-terminal {f}")
    sys.exit(1)
else:
    print("n6-n9-terminal OK (N6/N9 terminal, seven cells, arguments and evidence present)")
    sys.exit(0)
PYEOF
)
FIELD57_STATUS=$?
if [ "$FIELD57_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD57_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD57_OUT" | grep -cE '^FAIL: n6-n9-terminal' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 58: cross-file — CATALOG.md's N6/N9 rows each contain "closed in
# RIG.md"; RIG.md's Appendix A RIG-06 row reads "written"; RIG.md contains
# no clause resolving N11; CATALOG.md's N11 row carries no closure pointer.
CATALOG_DOC="$(dirname "$0")/CATALOG.md"
FIELD58_OUT=$(python3 - "$DOC" "$CATALOG_DOC" <<'PYEOF'
import re, sys, os
DOC, CATALOG_DOC = sys.argv[1], sys.argv[2]

fails = []
if not os.path.isfile(CATALOG_DOC):
    print(f"FAIL: aa4-closure-crossfile CATALOG.md not found at {CATALOG_DOC}")
    sys.exit(1)

with open(CATALOG_DOC, encoding="utf-8") as f:
    cat = f.read()

for rid in ("N6", "N9"):
    m = re.search(r'^\| ' + rid + r' \|.*\|$', cat, re.M)
    if not m or "closed in RIG.md" not in m.group(0):
        fails.append(f"CATALOG.md row {rid} does not contain 'closed in RIG.md'")

m11 = re.search(r'^\| N11 \|.*\|$', cat, re.M)
if m11 and "closed in RIG.md" in m11.group(0):
    fails.append("CATALOG.md's N11 row unexpectedly carries a closure pointer")

with open(DOC, encoding="utf-8") as f:
    text = f.read()

m_appA = re.search(r'^\| RIG-06 \|(.*)\|$', text, re.M)
if not m_appA:
    fails.append("RIG.md Appendix A RIG-06 row not found")
else:
    cells = [c.strip() for c in m_appA.group(1).split('|')]
    if not cells or cells[-1] != "written":
        fails.append(f"RIG.md Appendix A RIG-06 row Status is {cells[-1] if cells else '(missing)'!r}, expected 'written'")
    if "## §AA" not in m_appA.group(0):
        fails.append("RIG.md Appendix A RIG-06 row does not name ## §AA")

if re.search(r'N11 is (resolved|closed)|closes N11|resolving N11', text, re.I):
    fails.append("RIG.md appears to contain a clause resolving N11")

if fails:
    for f in fails:
        print(f"FAIL: aa4-closure-crossfile {f}")
    sys.exit(1)
else:
    print("aa4-closure-crossfile OK (CATALOG.md closure pointers present for N6/N9 only, Appendix A written, N11 untouched)")
    sys.exit(0)
PYEOF
)
FIELD58_STATUS=$?
if [ "$FIELD58_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD58_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD58_OUT" | grep -cE '^FAIL: aa4-closure-crossfile' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 59: cross-file — CATALOG.md's ### §C.4 closing fence names, for
# each of RIG-01 through RIG-07 on the same line as the id itself, the
# RIG.md section that now fills it (05-07 close-out: a fence discharged
# by pointer alone, with no section named, is worse than an open fence).
FIELD59_OUT=$(python3 - "$CATALOG_DOC" <<'PYEOF'
import re, sys, os
CATALOG_DOC = sys.argv[1]

fails = []
if not os.path.isfile(CATALOG_DOC):
    print(f"FAIL: c4-rig-section-coverage CATALOG.md not found at {CATALOG_DOC}")
    sys.exit(1)

with open(CATALOG_DOC, encoding="utf-8") as f:
    cat = f.read()

m = re.search(r'^### §C\.4.*?\n(.*?)\n## §D', cat, re.S | re.M)
body = m.group(1) if m else ""

# A trailing trace-tag list (e.g. "[RIG §RUN] [RIG §TR] ...") sits at the
# very end of the fence paragraph and would trivially satisfy a whole-line
# substring check regardless of which id it followed. Checking a
# semicolon-delimited clause window around each RIG-NN mention instead
# means the section must actually be paired with that id's own clause,
# not merely present anywhere later in the same physical line.
clauses = body.split(';')
rig_to_section = {
    "RIG-01": "§RUN", "RIG-02": "§TR", "RIG-03": "§EV", "RIG-04": "§F3",
    "RIG-05": "§PR", "RIG-06": "§AA", "RIG-07": "§LC",
}
for rig, section in rig_to_section.items():
    if rig not in body:
        fails.append(f"missing {rig}")
        continue
    clauses_with_rig = [c for c in clauses if rig in c]
    if not any(section in c for c in clauses_with_rig):
        fails.append(f"{rig} not paired with {section} in its own clause")

if fails:
    for f in fails:
        print(f"FAIL: c4-rig-section-coverage {f}")
    sys.exit(1)
else:
    print("c4-rig-section-coverage OK (RIG-01..RIG-07 each paired with their filling RIG.md section)")
    sys.exit(0)
PYEOF
)
FIELD59_STATUS=$?
if [ "$FIELD59_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD59_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD59_OUT" | grep -cE '^FAIL: c4-rig-section-coverage' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 60: cross-file — neither CONTRACT.md nor ANATOMY.md contains a
# "Phase 5 scope" or "Phase 5 (RIG-" fence sentence that does not also
# name a RIG.md section on the same line. A missing sibling file is a
# named failure, never a silent skip.
CONTRACT_DOC="$(dirname "$0")/CONTRACT.md"
ANATOMY_DOC="$(dirname "$0")/ANATOMY.md"
FIELD60_OUT=$(python3 - "$CONTRACT_DOC" "$ANATOMY_DOC" <<'PYEOF'
import re, sys, os
CONTRACT_DOC, ANATOMY_DOC = sys.argv[1], sys.argv[2]

fails = []
for label, path in (("CONTRACT.md", CONTRACT_DOC), ("ANATOMY.md", ANATOMY_DOC)):
    if not os.path.isfile(path):
        fails.append(f"{label} not found at {path}")
        continue
    with open(path, encoding="utf-8") as f:
        text = f.read()
    for line in text.splitlines():
        if re.search(r'Phase 5 scope|Phase 5 \(RIG-', line):
            if "RIG.md" not in line:
                fails.append(f"{label}: fence line defers to Phase 5 without naming a RIG.md section: {line[:120]!r}")

if fails:
    for f in fails:
        print(f"FAIL: no-bare-phase5-fence {f}")
    sys.exit(1)
else:
    print("no-bare-phase5-fence OK (no bare Phase 5 scope-fence sentence remains in CONTRACT.md or ANATOMY.md)")
    sys.exit(0)
PYEOF
)
FIELD60_STATUS=$?
if [ "$FIELD60_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD60_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD60_OUT" | grep -cE '^FAIL: no-bare-phase5-fence' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 61: no ## §R row Status reads "deferred — Phase 5" — self-contradictory
# inside RIG.md itself, since this document is Phase 5's own governing file.
FIELD61_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §R .*?\n(.*?)\n## Appendix A', text, re.S | re.M)
body = m.group(1) if m else ""

ID_RE = re.compile(r'^\| [A-Za-z]\d+ \|')
fails = []
n_checked = 0
for line in body.splitlines():
    if not ID_RE.match(line):
        continue
    row_id = line.strip().strip('|').split('|')[0].strip()
    n_checked += 1
    if "deferred — Phase 5" in line or "deferred - Phase 5" in line:
        fails.append(f"row {row_id}: Status defers to 'Phase 5', self-contradictory inside RIG.md")

if n_checked == 0:
    print("FAIL: no-defer-to-phase5 zero-rows-matched — ## §R section anchor not found or no rows matched")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: no-defer-to-phase5 {f}")
    sys.exit(1)
else:
    print(f"no-defer-to-phase5 OK ({n_checked} rows checked)")
    sys.exit(0)
PYEOF
)
FIELD61_STATUS=$?
if [ "$FIELD61_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD61_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD61_OUT" | grep -cE '^FAIL: no-defer-to-phase5' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 62: ## §R row ids are ascending within their own family (N, then R),
# and a family does not reappear once a later family has started — matching
# the register's own "ascending by id within family, families in order of
# introduction" rule.
FIELD62_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §R .*?\n(.*?)\n## Appendix A', text, re.S | re.M)
body = m.group(1) if m else ""

ID_RE = re.compile(r'^\| ([A-Za-z])(\d+) \|')
rows = []
for line in body.splitlines():
    rm = ID_RE.match(line)
    if not rm:
        continue
    rows.append((rm.group(1), int(rm.group(2)), rm.group(1) + rm.group(2)))

fails = []
if not rows:
    print("FAIL: register-ascending-order zero-rows-matched — ## §R section anchor not found or no rows matched")
    sys.exit(1)

closed_families = set()
current_family = None
last_num = None
for letter, num, row_id in rows:
    if letter != current_family:
        if letter in closed_families:
            fails.append(f"row {row_id}: family {letter!r} reappears after a later family already started")
        else:
            if current_family is not None:
                closed_families.add(current_family)
            current_family = letter
            last_num = num
    else:
        if num <= last_num:
            fails.append(f"row {row_id}: id {num} does not ascend past prior {letter}{last_num} in its own family")
        last_num = num

if fails:
    for f in fails:
        print(f"FAIL: register-ascending-order {f}")
    sys.exit(1)
else:
    print(f"register-ascending-order OK ({len(rows)} rows checked)")
    sys.exit(0)
PYEOF
)
FIELD62_STATUS=$?
if [ "$FIELD62_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD62_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD62_OUT" | grep -cE '^FAIL: register-ascending-order' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 63: every superseded per-query or per-recipe-version figure this
# phase's own cost-model correction replaced is paired with its correction
# on the same line, per ### §CM.2's own pairing rule — a bare superseded
# figure anywhere in RIG.md is a defect (05-07 close-out sweep).
FIELD63_OUT=$(python3 - "$DOC" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

# (superseded figure substring, corrected figure substring that must appear
# on the same line whenever the superseded figure does)
PAIRS = [
    ("~10,000 [inference — order-of-magnitude band]", "30,000"),
    ("| ~10,000 |", "30,000"),
    ("~2M tokens", "5.1-5.2M"),
    ("~15M", "84-117M"),
    ("~7-day", "16-23"),
    ("~175", "692"),
    ("~178", "704"),
]

fails = []
n_checked = 0
for line in text.splitlines():
    for superseded, corrected in PAIRS:
        if superseded in line:
            n_checked += 1
            if corrected not in line:
                fails.append(f"line contains superseded figure {superseded!r} without its correction {corrected!r}: {line[:120]!r}")

if n_checked == 0:
    print("FAIL: superseded-figures-paired zero-occurrences-matched — none of the tracked superseded figures found in RIG.md")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: superseded-figures-paired {f}")
    sys.exit(1)
else:
    print(f"superseded-figures-paired OK ({n_checked} occurrences checked)")
    sys.exit(0)
PYEOF
)
FIELD63_STATUS=$?
if [ "$FIELD63_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD63_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD63_OUT" | grep -cE '^FAIL: superseded-figures-paired' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

fi # python3 available

if [ "$FAILS" -eq 0 ]; then
  echo "OK $PASSES checks"
  exit 0
else
  echo "FAIL: $FAILS check(s) failed, $PASSES passed"
  exit 1
fi
