#!/usr/bin/env bash
# Structural + content checker for SYSTEM-MODEL.md and MODEL-RED-TEAM.md.
# Usage: bash model-check.sh
#
# The fifth gate in the fleet, built in rig-check.sh's image: per-row and
# per-clause content checks, never row-count checks (D-02, carried forward
# unbroken since Phase 3). Prints one "FAIL: <check name> — <diagnosis>"
# line per failed check, prints "OK <n> checks" and exits 0 when all pass,
# exits 1 otherwise. A missing file is a named failure, never silently
# compared as zero-vs-zero.
#
# CR-01 guard class (closed at rig-check.sh Check 19, this same plan):
# every check below that derives a candidate set from a section extraction
# fails loudly when that *structural* extraction returns zero candidates —
# a heading or a status-marker line the check expects to find but doesn't.
# This is distinct from a *filtered* candidate set (e.g. "sections marked
# written") legitimately containing zero members once correctly extracted —
# RIG.md ## §R's own no-empty-register clause is the precedent: a
# correctly-parsed zero is an honest result, not a failure, and this
# script's checks preserve that distinction rather than collapsing it.

set -u

DOC_SM="$(dirname "$0")/SYSTEM-MODEL.md"
DOC_MRT="$(dirname "$0")/MODEL-RED-TEAM.md"

FAILS=0
PASSES=0

fail() {
  echo "FAIL: $1 — $2 vs $3"
  FAILS=$((FAILS + 1))
}

pass() {
  PASSES=$((PASSES + 1))
}

# Check 0: both files exist and are non-empty.
for f in "$DOC_SM" "$DOC_MRT"; do
  if [ ! -f "$f" ]; then
    fail "file-exists" "missing: $f" "present"
    echo "FAIL: all remaining checks skipped — $f not found"
    exit 1
  fi
  if [ ! -s "$f" ]; then
    fail "file-non-empty" "empty: $f" "non-empty"
    echo "FAIL: all remaining checks skipped — $f is empty"
    exit 1
  fi
done
pass

if ! command -v python3 >/dev/null 2>&1; then
  fail "python3-available" "missing" "available"
  FAILS=$((FAILS + 4))
  echo "FAIL: checks 1-4 skipped (4 checks) — python3 missing"
else

# Check 1: system-model-sections-present — SYSTEM-MODEL.md carries its
# stated section headings, fixed-string match, in order.
FIELD1_OUT=$(python3 - "$DOC_SM" <<'PYEOF'
import sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

HEADINGS = [
    "# RAG Modality-Swap System Model — Entry Point",
    "## Reading order",
    "## What this document is not",
    "## §VD — The verdict",
    "## §PC — Per-modality port cost",
    "## §BP — Databasise build phases",
    "## §RK — Ranked assumption and falsifier register",
    "## §H1 — Handoff ledger 1: the Databasise build",
    "## §H2 — Handoff ledger 2: Sourcerer across the seam",
    "## §ST — Document status table",
    "## Appendix A — Requirement-to-section map",
]

fails = []
last = -1
for h in HEADINGS:
    idx = text.find(h)
    if idx == -1:
        fails.append(f"missing heading: {h!r}")
        continue
    if idx <= last:
        fails.append(f"heading out of order: {h!r}")
    last = idx

if fails:
    for f in fails:
        print(f"FAIL: system-model-sections-present {f}")
    sys.exit(1)
else:
    print(f"system-model-sections-present OK ({len(HEADINGS)} headings present, in order)")
    sys.exit(0)
PYEOF
)
FIELD1_STATUS=$?
if [ "$FIELD1_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD1_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD1_OUT" | grep -cE '^FAIL: system-model-sections-present' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 2: reading-order-names-five — SYSTEM-MODEL.md's ## Reading order
# names all five governing documents by filename. Guards the section
# extraction itself: an empty body here (heading found but no text before
# the next "## ") is the CR-01-class failure, not a legitimate zero.
FIELD2_OUT=$(python3 - "$DOC_SM" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## Reading order\s*\n(.*?)\n## ', text, re.S | re.M)
if not m:
    print("FAIL: reading-order-names-five — ## Reading order section anchor not found")
    sys.exit(1)
body = m.group(1)
if not body.strip():
    print("FAIL: reading-order-names-five — ## Reading order body is empty")
    sys.exit(1)

REQUIRED = ["CONTRACT.md", "ANATOMY.md", "PARTS.md", "CATALOG.md", "RIG.md"]
missing = [name for name in REQUIRED if name not in body]

if missing:
    print(f"FAIL: reading-order-names-five missing: {missing}")
    sys.exit(1)
else:
    print(f"reading-order-names-five OK (all 5 governing documents named)")
    sys.exit(0)
PYEOF
)
FIELD2_STATUS=$?
if [ "$FIELD2_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD2_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD2_OUT" | grep -cE '^FAIL: reading-order-names-five' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 3: scoring-vocabulary-closed — every Verdict cell in
# MODEL-RED-TEAM.md ## §S holds one of the four closed vocabulary tokens.
# Fails when zero rows are matched: an established ## §S table with zero
# data rows is a broken extraction, never a legitimate state (unlike
# ## §R's no-empty-register clause, ## §S is never legitimately empty once
# this document exists, since S-G7 lands in the same plan that creates it).
FIELD3_OUT=$(python3 - "$DOC_MRT" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §S .*?\n(.*?)\n## §A ', text, re.S | re.M)
if not m:
    print("FAIL: scoring-vocabulary-closed — ## §S section anchor not found")
    sys.exit(1)
body = m.group(1)

VOCAB = {"holds", "holds-with-named-risk", "does-not-hold", "unmeasurable-on-paper"}

rows = []
for line in body.splitlines():
    line = line.strip()
    if not line.startswith("| S-"):
        continue
    cells = [c.strip() for c in line.strip("|").split("|")]
    if len(cells) < 3:
        continue
    rows.append((cells[0], cells[2]))

if not rows:
    print("FAIL: scoring-vocabulary-closed zero-rows-matched — no '| S-...' data row found in ## §S")
    sys.exit(1)

fails = []
for row_id, verdict in rows:
    if verdict not in VOCAB:
        fails.append(f"row {row_id!r} verdict {verdict!r} not in closed vocabulary {sorted(VOCAB)}")

if fails:
    for f in fails:
        print(f"FAIL: scoring-vocabulary-closed {f}")
    sys.exit(1)
else:
    print(f"scoring-vocabulary-closed OK ({len(rows)} row(s) checked, all verdicts closed-vocabulary)")
    sys.exit(0)
PYEOF
)
FIELD3_STATUS=$?
if [ "$FIELD3_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD3_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD3_OUT" | grep -cE '^FAIL: scoring-vocabulary-closed' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 4: pointer-discipline — every SYSTEM-MODEL.md section marked
# `written` carries at least one citation naming a governing document and
# a section id. The structural extraction (finding the 8 frame headings
# and their status marker) is guarded per the CR-01 class above; the
# *filtered* count of sections actually marked `written` is legitimately
# zero at this tracer plan's close (every frame heading reads
# `pending — plan 06-NN` by design, per this plan's own Move 3) — a
# correctly-parsed zero, not a broken extraction, matching ## §R's
# no-empty-register precedent. Proven fail-first by mutation: temporarily
# mark a heading `written` with no citation in its body and confirm this
# check fires (see 06-01-SUMMARY.md's fail-first ledger).
FIELD4_OUT=$(python3 - "$DOC_SM" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

FRAME_HEADINGS = [
    "## §VD — The verdict",
    "## §PC — Per-modality port cost",
    "## §BP — Databasise build phases",
    "## §RK — Ranked assumption and falsifier register",
    "## §H1 — Handoff ledger 1: the Databasise build",
    "## §H2 — Handoff ledger 2: Sourcerer across the seam",
    "## §ST — Document status table",
]

# Structural extraction: locate each frame heading and the body up to the
# next "## " or "---" (whichever comes first). Zero headings found at all
# is the CR-01-class failure.
positions = [text.find(h) for h in FRAME_HEADINGS]
if all(p == -1 for p in positions):
    print("FAIL: pointer-discipline zero-candidates-matched — none of the frame section headings found")
    sys.exit(1)

CITATION_RE = re.compile(r'(CONTRACT\.md|ANATOMY\.md|PARTS\.md|CATALOG\.md|RIG\.md|SELECTION\.md)\s*§[\w.]+|§\w[\w.]*\s*\((CONTRACT|ANATOMY|PARTS|CATALOG|RIG)\.md\)')

fails = []
written_count = 0
for i, h in enumerate(FRAME_HEADINGS):
    idx = positions[i]
    if idx == -1:
        fails.append(f"missing heading: {h!r}")
        continue
    start = idx + len(h)
    rest = text[start:]
    next_marker = len(rest)
    for stop in ("\n## ", "\n---"):
        p = rest.find(stop)
        if p != -1:
            next_marker = min(next_marker, p)
    body = rest[:next_marker]
    if "written" in body.lower() and "pending" not in body.lower():
        written_count += 1
        if not CITATION_RE.search(body):
            fails.append(f"{h!r} marked written but carries no governing-document citation")

if fails:
    for f in fails:
        print(f"FAIL: pointer-discipline {f}")
    sys.exit(1)
else:
    print(f"pointer-discipline OK ({written_count} written section(s) checked, all carry a citation)")
    sys.exit(0)
PYEOF
)
FIELD4_STATUS=$?
if [ "$FIELD4_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD4_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD4_OUT" | grep -cE '^FAIL: pointer-discipline' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 5: frame-status-no-pending — none of SYSTEM-MODEL.md's seven "## §"
# frame sections (the sections plan 06-01's tracer established, excluding
# ## Appendix A which carries its own dedicated status lifecycle) still
# carries a "pending" status marker in its own body. Structural extraction
# guarded per the CR-01 class: zero headings found at all is a failure: a
# section legitimately containing no literal "pending" once correctly
# extracted is the honest pass state this check exists to confirm, not a
# vacuous one, since at least one heading is always found once the frame
# exists at all.
FIELD5_OUT=$(python3 - "$DOC_SM" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

FRAME_HEADINGS = [
    "## §VD — The verdict",
    "## §PC — Per-modality port cost",
    "## §BP — Databasise build phases",
    "## §RK — Ranked assumption and falsifier register",
    "## §H1 — Handoff ledger 1: the Databasise build",
    "## §H2 — Handoff ledger 2: Sourcerer across the seam",
    "## §ST — Document status table",
]

positions = [text.find(h) for h in FRAME_HEADINGS]
if all(p == -1 for p in positions):
    print("FAIL: frame-status-no-pending zero-candidates-matched — none of the frame section headings found")
    sys.exit(1)

fails = []
for i, h in enumerate(FRAME_HEADINGS):
    idx = positions[i]
    if idx == -1:
        fails.append(f"missing heading: {h!r}")
        continue
    start = idx + len(h)
    rest = text[start:]
    next_marker = len(rest)
    for stop in ("\n## ", "\n---"):
        p = rest.find(stop)
        if p != -1:
            next_marker = min(next_marker, p)
    body = rest[:next_marker]
    if re.search(r'\bpending\b', body, re.I):
        fails.append(f"{h!r} still carries a pending status marker")

if fails:
    for f in fails:
        print(f"FAIL: frame-status-no-pending {f}")
    sys.exit(1)
else:
    print(f"frame-status-no-pending OK ({len(FRAME_HEADINGS)} section(s) checked, none pending)")
    sys.exit(0)
PYEOF
)
FIELD5_STATUS=$?
if [ "$FIELD5_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD5_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD5_OUT" | grep -cE '^FAIL: frame-status-no-pending' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 6: banner-status-table-forward — for every ## §ST row whose status
# is superseded or archived-with-standing, the named file carries a matching
# in-file banner (a **Status:** or frontmatter status: line at the top of
# the file, before its first "## " heading, naming that same status token).
# D-14's first mechanism direction. Zero superseded/archived-with-standing
# rows found is a guard failure (this table always carries at least the ten
# MODEL-02 rows once written), distinct from the legitimate zero of "no
# governing row" (governing rows are skipped by construction, not checked).
FIELD6_OUT=$(python3 - "$DOC_SM" <<'PYEOF'
import re, sys, os
DOC = sys.argv[1]
ARCH_DIR = os.path.dirname(os.path.abspath(DOC))
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §ST .*?\n(.*?)\n## Appendix A', text, re.S | re.M)
if not m:
    print("FAIL: banner-status-table-forward — ## §ST section anchor not found")
    sys.exit(1)
body = m.group(1)

SEP_RE = re.compile(r'^\|[\s:|-]+\|$')
rows = []
for line in body.splitlines():
    stripped = line.strip()
    if not stripped.startswith('|'):
        continue
    if SEP_RE.match(stripped):
        continue
    cells = [c.strip() for c in stripped.strip('|').split('|')]
    if len(cells) < 2 or cells[0] == "Document":
        continue
    rows.append(cells)

if not rows:
    print("FAIL: banner-status-table-forward zero-rows-matched — ## §ST table anchor not found or no rows matched")
    sys.exit(1)

STATUSES = ("superseded", "archived-with-standing")
fails = []
n_checked = 0
for cells in rows:
    doc_name = cells[0].strip('`')
    status = cells[1].strip()
    if status not in STATUSES:
        continue
    n_checked += 1
    path = os.path.join(ARCH_DIR, doc_name)
    if not os.path.isfile(path):
        fails.append(f"{doc_name}: file not found at {path!r}")
        continue
    with open(path, encoding="utf-8") as ff:
        filetext = ff.read()
    preamble = filetext.split("\n## ", 1)[0]
    banner_re = re.compile(r'(?im)^\s*(?:\*\*Status:\*\*|status:)\s*' + re.escape(status) + r'\b')
    if not banner_re.search(preamble):
        fails.append(f"{doc_name}: ## §ST row status {status!r} not matched by an in-file banner")

if n_checked == 0:
    print("FAIL: banner-status-table-forward zero-rows-matched — no superseded/archived-with-standing row found in ## §ST")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: banner-status-table-forward {f}")
    sys.exit(1)
else:
    print(f"banner-status-table-forward OK ({n_checked} row(s) checked, each backed by a matching in-file banner)")
    sys.exit(0)
PYEOF
)
FIELD6_STATUS=$?
if [ "$FIELD6_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD6_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD6_OUT" | grep -cE '^FAIL: banner-status-table-forward' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 7: banner-status-table-reverse — the converse of Check 6: every
# markdown file in .planning/architectures/ or .planning/architectures/D-VARIANTS/
# whose own top-of-file banner reads superseded or archived-with-standing has
# a matching ## §ST row naming the same status. D-14's second mechanism
# direction — a banner without a table row is a different defect than a
# table row without a banner, and this check catches the direction Check 6
# cannot. Zero markdown files found in either directory is a guard failure
# (the directories are never legitimately empty on this record).
FIELD7_OUT=$(python3 - "$DOC_SM" <<'PYEOF'
import re, sys, os, glob
DOC = sys.argv[1]
ARCH_DIR = os.path.dirname(os.path.abspath(DOC))
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §ST .*?\n(.*?)\n## Appendix A', text, re.S | re.M)
if not m:
    print("FAIL: banner-status-table-reverse — ## §ST section anchor not found")
    sys.exit(1)
body = m.group(1)

SEP_RE = re.compile(r'^\|[\s:|-]+\|$')
table = {}
for line in body.splitlines():
    stripped = line.strip()
    if not stripped.startswith('|'):
        continue
    if SEP_RE.match(stripped):
        continue
    cells = [c.strip() for c in stripped.strip('|').split('|')]
    if len(cells) < 2 or cells[0] == "Document":
        continue
    table[cells[0].strip('`')] = cells[1].strip()

files = sorted(glob.glob(os.path.join(ARCH_DIR, "*.md"))) + sorted(glob.glob(os.path.join(ARCH_DIR, "D-VARIANTS", "*.md")))
if not files:
    print("FAIL: banner-status-table-reverse zero-candidates-matched — no markdown files found in the architecture directories")
    sys.exit(1)

BANNER_RE = re.compile(r'(?im)^\s*(?:\*\*Status:\*\*|status:)\s*(superseded|archived-with-standing)\b')
fails = []
n_checked = 0
for fpath in files:
    with open(fpath, encoding="utf-8") as ff:
        filetext = ff.read()
    preamble = filetext.split("\n## ", 1)[0]
    mm = BANNER_RE.search(preamble)
    if not mm:
        continue
    status_found = mm.group(1)
    n_checked += 1
    relname = os.path.relpath(fpath, ARCH_DIR)
    if relname not in table:
        fails.append(f"{relname}: carries a {status_found!r} banner but has no ## §ST row")
    elif table[relname] != status_found:
        fails.append(f"{relname}: banner says {status_found!r}, ## §ST row says {table[relname]!r}")

if n_checked == 0:
    print("FAIL: banner-status-table-reverse zero-rows-matched — no file in either architecture directory carries a superseded/archived-with-standing banner")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: banner-status-table-reverse {f}")
    sys.exit(1)
else:
    print(f"banner-status-table-reverse OK ({n_checked} banner(s) checked, each backed by a matching ## §ST row)")
    sys.exit(0)
PYEOF
)
FIELD7_STATUS=$?
if [ "$FIELD7_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD7_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD7_OUT" | grep -cE '^FAIL: banner-status-table-reverse' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 8: scoring-table-completeness — MODEL-RED-TEAM.md ## §S carries
# exactly twenty-six rows, the S-G family runs 1 through 10 with no gaps,
# the S-D family runs 1 through 16 with no gaps, and no row id repeats.
# Complements Check 3 (vocabulary closure) with the completeness half of
# D-12's own "scoring-table completeness and closed vocabulary" pairing.
# Zero rows matched is a guard failure, never a legitimate empty state,
# since ## §S has carried all twenty-six rows since plan 06-04.
FIELD8_OUT=$(python3 - "$DOC_MRT" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §S .*?\n(.*?)\n## §A ', text, re.S | re.M)
if not m:
    print("FAIL: scoring-table-completeness — ## §S section anchor not found")
    sys.exit(1)
body = m.group(1)

ids = []
for line in body.splitlines():
    line = line.strip()
    if not line.startswith("| S-"):
        continue
    cells = [c.strip() for c in line.strip("|").split("|")]
    if not cells:
        continue
    ids.append(cells[0])

if not ids:
    print("FAIL: scoring-table-completeness zero-rows-matched — no '| S-...' data row found in ## §S")
    sys.exit(1)

fails = []
if len(ids) != 26:
    fails.append(f"{len(ids)} rows found, expected exactly 26")

g_nums = sorted(int(i.split("S-G")[1]) for i in ids if i.startswith("S-G"))
d_nums = sorted(int(i.split("S-D")[1]) for i in ids if i.startswith("S-D"))

if g_nums != list(range(1, 11)):
    fails.append(f"S-G family {g_nums} is not exactly 1..10 with no gaps")
if d_nums != list(range(1, 17)):
    fails.append(f"S-D family {d_nums} is not exactly 1..16 with no gaps")
if len(set(ids)) != len(ids):
    fails.append("duplicate row id(s) found")

if fails:
    for f in fails:
        print(f"FAIL: scoring-table-completeness {f}")
    sys.exit(1)
else:
    print(f"scoring-table-completeness OK ({len(ids)} rows: S-G1..10, S-D1..16, no gaps, no duplicates)")
    sys.exit(0)
PYEOF
)
FIELD8_STATUS=$?
if [ "$FIELD8_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD8_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD8_OUT" | grep -cE '^FAIL: scoring-table-completeness' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 9: register-terminal-disposition (MODEL-RED-TEAM.md ## §R) — every
# row in the V-family repair register carries a terminal status from the
# document's own closed vocabulary (repaired in §<clause> / recorded, no
# amendment — handed to the build with repair direction: <direction> /
# deferred — <owning phase>, reason: … / an inherited-prefix form that
# additionally resolves to one of the first three). ## §R has no dedicated
# "## §R" heading in this document (it is a table embedded inside ## §A,
# after every F-NN write-up) — the table's own header row, not a heading,
# anchors the extraction. Zero rows matched is a guard failure.
FIELD9_OUT=$(python3 - "$DOC_MRT" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^\| # \| Clause \| Defect \| Repair direction \| Forcing requirement \| ANATOMY re-projection \| Status \|\n\|[-\s|]+\|\n(.*?)\n## Appendix A', text, re.S | re.M)
if not m:
    print("FAIL: register-terminal-disposition — ## §R register table header not found")
    sys.exit(1)
body = m.group(1)

ID_RE = re.compile(r'^\| [A-Za-z]-?\d+ \|')
fails = []
n_checked = 0
for line in body.splitlines():
    if not ID_RE.match(line):
        continue
    cells = [c.strip() for c in line.strip().strip('|').split('|')]
    row_id = cells[0]
    n_checked += 1
    status = cells[-1]
    is_repaired = status.startswith("repaired in §")
    is_no_amendment = status.startswith("recorded, no amendment")
    is_deferred = status.startswith("deferred —") or status.startswith("deferred -")
    is_inherited = status.startswith("inherited from")
    terminal = is_repaired or is_no_amendment or is_deferred
    if is_inherited:
        terminal = ("repaired in §" in status) or ("recorded, no amendment" in status) or ("deferred —" in status) or ("deferred -" in status)
    if not terminal:
        fails.append(f"row {row_id}: Status {status!r} not a permitted terminal form")

if n_checked == 0:
    print("FAIL: register-terminal-disposition zero-rows-matched — ## §R table anchor not found or no rows matched")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: register-terminal-disposition {f}")
    sys.exit(1)
else:
    print(f"register-terminal-disposition OK ({n_checked} rows checked)")
    sys.exit(0)
PYEOF
)
FIELD9_STATUS=$?
if [ "$FIELD9_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD9_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD9_OUT" | grep -cE '^FAIL: register-terminal-disposition' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 10: rk-disposition-closed (SYSTEM-MODEL.md ## §RK) — every row's
# Disposition cell (the table's last column) is one of the two closed
# vocabulary tokens: must-run-before-build-commits / accepted-as-stated-risk.
# The register-terminal-disposition minimum's second half (D-12). Zero rows
# matched is a guard failure — ## §RK is never legitimately empty once
# written, since SELECTION.md's own eight falsifiers alone guarantee rows.
FIELD10_OUT=$(python3 - "$DOC_SM" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §RK .*?\n(.*?)\n## §H1', text, re.S | re.M)
if not m:
    print("FAIL: rk-disposition-closed — ## §RK section anchor not found")
    sys.exit(1)
body = m.group(1)

DISPOSITIONS = {"must-run-before-build-commits", "accepted-as-stated-risk"}
SEP_RE = re.compile(r'^\|[\s:|-]+\|$')
fails = []
n_checked = 0
for line in body.splitlines():
    stripped = line.strip()
    if not stripped.startswith('|'):
        continue
    if SEP_RE.match(stripped):
        continue
    cells = [c.strip() for c in stripped.strip('|').split('|')]
    if cells and cells[0] == "Assumption":
        continue
    if len(cells) < 6:
        continue
    n_checked += 1
    disp = cells[-1]
    if disp not in DISPOSITIONS:
        fails.append(f"row {cells[0][:40]!r}: disposition {disp!r} not in closed set {sorted(DISPOSITIONS)}")

if n_checked == 0:
    print("FAIL: rk-disposition-closed zero-rows-matched — ## §RK table anchor not found or no rows matched")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: rk-disposition-closed {f}")
    sys.exit(1)
else:
    print(f"rk-disposition-closed OK ({n_checked} rows checked)")
    sys.exit(0)
PYEOF
)
FIELD10_STATUS=$?
if [ "$FIELD10_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD10_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD10_OUT" | grep -cE '^FAIL: rk-disposition-closed' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 11: rk-no-blank-cells — every ## §RK row has a non-empty cell in
# every one of its six columns. Beyond D-12's named minimum, per this plan's
# own "cell-completeness (no blank cells, the alternative spelled out)"
# instruction. Zero rows matched is a guard failure, same anchor as Check 10.
FIELD11_OUT=$(python3 - "$DOC_SM" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

m = re.search(r'^## §RK .*?\n(.*?)\n## §H1', text, re.S | re.M)
if not m:
    print("FAIL: rk-no-blank-cells — ## §RK section anchor not found")
    sys.exit(1)
body = m.group(1)

SEP_RE = re.compile(r'^\|[\s:|-]+\|$')
fails = []
n_checked = 0
for line in body.splitlines():
    stripped = line.strip()
    if not stripped.startswith('|'):
        continue
    if SEP_RE.match(stripped):
        continue
    cells = [c.strip() for c in stripped.strip('|').split('|')]
    if cells and cells[0] == "Assumption":
        continue
    if len(cells) < 6:
        continue
    n_checked += 1
    for i, val in enumerate(cells):
        if not val:
            fails.append(f"row {cells[0][:40]!r}: empty cell at column {i}")

if n_checked == 0:
    print("FAIL: rk-no-blank-cells zero-rows-matched — ## §RK table anchor not found or no rows matched")
    sys.exit(1)

if fails:
    for f in fails:
        print(f"FAIL: rk-no-blank-cells {f}")
    sys.exit(1)
else:
    print(f"rk-no-blank-cells OK ({n_checked} rows checked, no blank cells)")
    sys.exit(0)
PYEOF
)
FIELD11_STATUS=$?
if [ "$FIELD11_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD11_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD11_OUT" | grep -cE '^FAIL: rk-no-blank-cells' || true)
  [ "$FAILCOUNT" -eq 0 ] && FAILCOUNT=1
  FAILS=$((FAILS + FAILCOUNT))
fi

# Check 12: ledger-both-sides-non-empty — SYSTEM-MODEL.md ## §H1 (Inherits
# as settled / Must decide itself) and ## §H2 (Can rely on / Must change)
# each carry at least one bulleted entry on both of their own two sides.
# Beyond D-12's named minimum, per this plan's own "ledger non-emptiness
# with both sides present in each of ## §H1 and ## §H2" instruction.
FIELD12_OUT=$(python3 - "$DOC_SM" <<'PYEOF'
import re, sys
DOC = sys.argv[1]
with open(DOC, encoding="utf-8") as f:
    text = f.read()

h1_m = re.search(r'^## §H1 .*?\n(.*?)\n## §H2', text, re.S | re.M)
if not h1_m:
    print("FAIL: ledger-both-sides-non-empty — ## §H1 section anchor not found")
    sys.exit(1)
h1_body = h1_m.group(1)

h2_m = re.search(r'^## §H2 .*?\n(.*?)\n## §ST', text, re.S | re.M)
if not h2_m:
    print("FAIL: ledger-both-sides-non-empty — ## §H2 section anchor not found")
    sys.exit(1)
h2_body = h2_m.group(1)

def side_body(container, start_heading, end_heading):
    if end_heading:
        m2 = re.search(re.escape(start_heading) + r'\s*\n(.*?)\n' + re.escape(end_heading), container, re.S)
    else:
        m2 = re.search(re.escape(start_heading) + r'\s*\n(.*)\Z', container, re.S)
    return m2.group(1) if m2 else None

def has_bullet(body):
    return body is not None and re.search(r'^-\s+\S', body, re.M) is not None

fails = []
h1_settled = side_body(h1_body, "### Inherits as settled", "### Must decide itself")
h1_decide = side_body(h1_body, "### Must decide itself", None)
if not has_bullet(h1_settled):
    fails.append("## §H1 'Inherits as settled' side has no bullet entry")
if not has_bullet(h1_decide):
    fails.append("## §H1 'Must decide itself' side has no bullet entry")

h2_rely = side_body(h2_body, "### Can rely on", "### Must change")
h2_change = side_body(h2_body, "### Must change", "### Joint completeness")
if not has_bullet(h2_rely):
    fails.append("## §H2 'Can rely on' side has no bullet entry")
if not has_bullet(h2_change):
    fails.append("## §H2 'Must change' side has no bullet entry")

if fails:
    for f in fails:
        print(f"FAIL: ledger-both-sides-non-empty {f}")
    sys.exit(1)
else:
    print("ledger-both-sides-non-empty OK (## §H1 and ## §H2 each have both sides populated)")
    sys.exit(0)
PYEOF
)
FIELD12_STATUS=$?
if [ "$FIELD12_STATUS" -eq 0 ]; then
  pass
else
  echo "$FIELD12_OUT"
  FAILCOUNT=$(printf '%s\n' "$FIELD12_OUT" | grep -cE '^FAIL: ledger-both-sides-non-empty' || true)
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
