---
phase: 02-falsifier-gate
fixed_at: 2026-09-01T00:28:58Z
review_path: .planning/phases/02-falsifier-gate/02-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-09-01T00:28:58Z
**Source review:** .planning/phases/02-falsifier-gate/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3 (fix_scope: critical_warning — WR-01, WR-02, WR-03; IN-01/IN-02/IN-03
  excluded as Info-tier, out of scope)
- Fixed: 3
- Skipped: 0

**Verification environment:** Fixes were made and syntax-checked (`python -c "import ast;
ast.parse(...)"`) inside an isolated git worktree (`.claude/worktrees/rf-02-1458866-1788222362`,
branch `gsd-reviewfix/02-1458866`), which has no project virtualenv, so each fix's specific
reproduction case from REVIEW.md was re-verified there with a standalone Python snippet
extracting the exact logic changed (see per-finding notes below). After the worktree's commits
were fast-forwarded onto `main` and the worktree torn down (cleanup tail), the full test suite
was re-run in the main checkout (which has the project `.venv`): `uv run pytest -q` from
`databasise/` — **259 passed**, matching REVIEW.md's pre-fix baseline exactly, and
`uv run pytest -q tests/validator/test_falsifier2_probes.py tests/validator/test_falsifier2_evidence.py tests/runner/test_measurement_posture.py`
— **26 passed**, confirming zero regressions from all three fixes.

## Fixed Issues

### WR-01: Evidence tables have no escaping for `|`/newline in wiring-derived strings

**Files modified:** `databasise/evidence/falsifier2.py`
**Commit:** 1e6b483
**Applied fix:** Added a `_escape_cell()` helper (`.replace("|", "\\|").replace("\n", " ")`) and
applied it to every wiring-derived or part-derived string interpolated into a markdown table
cell: `component`/`effects_cell`/`scope_cell` in `_render_node_table`, `between`/`rationale` in
`_render_boundaries`, and the node/component summary in `_wiring_shape_summary` (used by
`_render_probe_table`). `_render_probe_table`'s `observed_cell` was left untouched — it is built
from a set of internal violation-code enum members, not wiring-derived free text, so it cannot
contain a `|`. Re-ran the review's exact repro (`between='a -> b'`, `rationale='contains a |
pipe character'`) against the extracted escaping logic: output row now reads
`| x | knob | a -> b | contains a \| pipe character |` — a single well-formed 4-column row
instead of a silently-corrupted 5-column one.

### WR-02: `enumerate_boundaries` raises uncaught `KeyError` on a malformed `boundary_knobs` entry

**Files modified:** `databasise/evidence/falsifier2.py`
**Commit:** 8e13157
**Applied fix:** Replaced the direct `knob["between"]`/`knob["rationale"]` indexing with
`.get()` reads plus an explicit up-front check that raises `ValueError` naming the wiring stem,
the offending `boundary_knobs` index, and exactly which key(s) are missing (matching the
existing actionable-`ValueError` convention already used in
`databasise/validator/execution_mode.py`). A hand-edited or newly-authored wiring fixture with a
typo'd knob key now fails with a clear, targeted message instead of a bare `KeyError`
traceback pointing at an internal dict-index line.

### WR-03: MACH-09 ledger-import guard misses the `from databasise import ledger` shape

**Files modified:** `databasise/tests/runner/test_measurement_posture.py`
**Commit:** ca94096
**Applied fix:** `_ledger_import_findings` now also inspects, for every `ast.ImportFrom` node
that didn't already match on `module`, each imported alias's combined `f"{module}.{alias.name}"`
path against the same `"databasise.ledger"`/`"databasise.ledger."` predicate already used for
the `ast.Import` branch — exactly the fix REVIEW.md specified. Re-ran the review's exact repro
(`ast.parse("from databasise import ledger\nledger.ledger.Ledger()\n")`) against the updated
function logic: it now returns a finding
`(1, "from databasise import ledger")`, closing the previously-silent evasion path. Confirmed no
existing non-exempt (`tests/`, `ledger/`) source file in the repo currently uses this import
shape, so the tightened guard introduces no new failures against current code.

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-09-01T00:28:58Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
