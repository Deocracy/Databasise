---
phase: 02-falsifier-gate
reviewed: 2026-09-01T00:14:11Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - databasise/evidence/__init__.py
  - databasise/evidence/falsifier2.py
  - databasise/evidence/FALSIFIER-2-EVIDENCE.md
  - databasise/evidence/wirings/w1-lightrag-query-side.json
  - databasise/evidence/wirings/w2-codebase-memory-mcp.json
  - databasise/evidence/wirings/w3-lightrag-half-decomposed.json
  - databasise/parts/schema.py
  - databasise/pyproject.toml
  - databasise/tests/runner/test_measurement_posture.py
  - databasise/tests/validator/test_falsifier2_evidence.py
  - databasise/tests/validator/test_falsifier2_probes.py
  - databasise/validator/errors.py
  - databasise/validator/parse.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 02: Code Review Report

**Reviewed:** 2026-09-01T00:14:11Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Reviewed the Falsifier 2 evidence module (`evidence/falsifier2.py` + its committed wiring
fixtures and rendered `FALSIFIER-2-EVIDENCE.md`), the `WiringNode` self-declared-derivation
refusal (`parts/schema.py`'s `extra="forbid"` change plus `validator/parse.py`'s
`_classify_node_schema_error`/`_DERIVED_FIELD_NAMES` machinery and the new
`CODE_SELF_DECLARED_DERIVATION` code in `validator/errors.py`), the probe suite
(`tests/validator/test_falsifier2_probes.py`), the evidence drift gate
(`tests/validator/test_falsifier2_evidence.py`), the MACH-09 posture pin
(`tests/runner/test_measurement_posture.py`), and the packaging change in `pyproject.toml`.

Verification performed beyond reading:
- Ran the full test suite (`uv run pytest -q`): 259 passed, including the 26 new/phase tests.
- Confirmed `WiringNode`'s `extra="ignore"` → `extra="forbid"` change (a real behavioral
  tightening — any previously-silently-discarded extra node key is now a parse violation)
  introduced no regressions anywhere else in the suite.
- Probed the self-declaration classifier with a hand-built two-field-at-once case
  (`effective_depth` + `execution_mode` on one node) — both fire as independent, correctly
  distinguished `CODE_SELF_DECLARED_DERIVATION` violations. No false-positive or false-negative
  found in the classifier's pydantic-`err["loc"]` matching for any representable error shape.
- Verified the evidence renderer's byte-stability claim empirically, not just via the
  same-process `test_render_markdown_is_idempotent` test: ran `render_markdown()` in five
  separate subprocesses with `PYTHONHASHSEED` set to five different values and hashed the
  output — identical digest every time. The claim holds.
- Found and reproduced two rendering/detection gaps (below): a markdown-table-corrupting
  unescaped-pipe path in the evidence renderer, and an AST-import-shape blind spot in the
  MACH-09 ledger-import guard.

The self-declaration refusal path itself (the main asked-about surface) is sound: it refuses
exactly the six named derived fields and nothing else, distinguishes a self-declaration from an
ordinary schema typo correctly (confirmed by the c1/c2 probe pair and by direct testing), and
does not appear to reject any wiring shape a legitimate author would plausibly need to write
(node-level annotation/documentation fields are the one now-refused shape or note below).

## Warnings

### WR-01: Evidence tables have no escaping for `|`/newline in wiring-derived strings

**File:** `databasise/evidence/falsifier2.py:398-467`
**Issue:** `_render_node_table`, `_render_boundaries`, `_render_probe_table`, and
`_wiring_shape_summary` build markdown table rows by directly f-string-interpolating strings
that originate from a wiring document (`component`, `boundary_knobs[].between`,
`boundary_knobs[].rationale`) or from a registered part's own identity string. `parse.py`'s own
module docstring calls a wiring "untrusted, author-supplied input," and CONTRACT §19.10's whole
point for this renderer is that "a second author can check the candidate set" from the document
it produces — but a `|` character in any interpolated value silently splits a table row into
extra columns with no error raised. Reproduced directly:

```
>>> _render_boundaries((BoundaryRow(boundary_id='x', boundary_class='knob',
...     between='a -> b', rationale='contains a | pipe character'),))
| boundary_id | class | between | rationale |
|---|---|---|---|
| x | knob | a -> b | contains a | pipe character |
```

The three committed wiring fixtures happen not to contain `|` or newline characters today, so
`FALSIFIER-2-EVIDENCE.md` itself is unaffected — but nothing prevents a future named wiring (or
a probe's own component string) from silently corrupting the rendered evidence document the
moment one is added.

**Fix:** Escape `|` (and normalize/escape embedded newlines) in every interpolated cell before
building a row, e.g.:

```python
def _escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
```

and apply it to `component`, `between`, `rationale`, `effects_cell`, `scope_cell`, and the probe
table's `wiring shape`/`observed_cell` values.

### WR-02: `enumerate_boundaries` raises uncaught `KeyError` on a malformed `boundary_knobs` entry

**File:** `databasise/evidence/falsifier2.py:384-393`
**Issue:** `boundary_knobs` is read raw from the wiring document (`doc.get("boundary_knobs", [])`)
with no pydantic validation at all — it's outside `WiringNode`'s schema entirely. Within the
loop, `knob["between"]` and `knob["rationale"]` are indexed directly (only `boundary_id` uses
`.get(...)` with a fallback). A `boundary_knobs` entry missing either key crashes
`render_markdown()`/`main()` with an unhandled `KeyError`, in contrast to every other check in
this codebase, which — per `validator/errors.py`'s own stated contract — accumulates violations
into a report rather than raising on the first defect. This confined blast radius is limited to
the evidence-generation tool (not the production validator path), but it means a hand-edited or
newly-authored wiring fixture with a typo'd knob key fails with a bare traceback rather than an
actionable message.
**Fix:** Validate the knob shape up front (or use `.get()` with an explicit "malformed
boundary_knobs entry" error) rather than relying on bare `KeyError` propagation.

### WR-03: MACH-09 ledger-import guard misses the `from databasise import ledger` shape

**File:** `databasise/tests/runner/test_measurement_posture.py:69-91`
**Issue:** `_ledger_import_findings` only inspects `ast.ImportFrom.module` (checking whether it
*is* or *starts with* `"databasise.ledger"`) and, separately, `ast.Import` alias names. It never
inspects the imported *alias names* of an `ast.ImportFrom` node whose `module` is the parent
package. Reproduced directly:

```
>>> import ast
>>> tree = ast.parse("from databasise import ledger\nledger.ledger.Ledger()\n")
>>> [(n.module, [a.name for a in n.names]) for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
[('databasise', ['ledger'])]
```

`node.module` here is `"databasise"`, which fails both of the check's conditions — this import
shape is invisible to the scanner. The whole point of this test (per its own docstring) is to be
"what keeps that claim true going forward" and to force MACH-09's posture record to be updated
"when Phase 7 builds MACH-07's promote/rollback path" — a caller reaching the ledger via
`from databasise import ledger` (or `from databasise import ledger as l`) defeats that
enforcement silently, with the test staying green.
**Fix:** Also flag an `ast.ImportFrom` whose `module` is a *prefix* of `"databasise.ledger"`
(e.g. `"databasise"`) when any imported alias name is `"ledger"` or a dotted path into it —
concretely, check `f"{module}.{alias.name}"` against the same `"databasise.ledger"`/
`"databasise.ledger."` predicate already used for the `ast.Import` branch.

## Info

### IN-01: Promotion-verb guard doesn't catch alias/assignment-style definitions

**File:** `databasise/tests/runner/test_measurement_posture.py:94-107`
**Issue:** `_promotion_verb_findings` matches only `ast.FunctionDef`/`ast.AsyncFunctionDef` nodes
named `promote`/`promote_next`/`promote_now`/`rollback`. A promotion verb introduced instead as
`promote = _internal_impl` (a plain name binding, not a `def`) would not be caught. Lower
severity than WR-03 since it requires a more deliberate evasion, but the same "structural pin"
framing applies.
**Fix:** Optionally also scan top-level/class-level `ast.Assign` targets whose name matches
`_PROMOTION_VERB_NAMES`, if this guard is meant to survive that shape too.

### IN-02: Redundant re-parse/re-registry-construction per rendered wiring

**File:** `databasise/evidence/falsifier2.py:298-341, 384, 486-488`
**Issue:** For each named wiring, `render_markdown()` calls `_parse(stem)` directly (line 487)
*and* calls `evaluate_wiring(stem)` (line 488), which internally calls `_parse(stem)` again
(line 302) — each `_parse` call builds a brand-new `default_registry()` and re-parses the same
JSON document. `enumerate_boundaries` then independently calls `load_wiring(evidence.stem)` a
third time (line 384) to re-read and re-`json.loads` the same file just to reach
`boundary_knobs`. Purely a duplication/maintainability nit (explicitly out of this review's
performance scope, and the result is still correct and deterministic) — noted for anyone
touching this module next.
**Fix (optional):** Thread the single `(doc, parsed)` pair already produced by `render_markdown`'s
loop into `evaluate_wiring`/`enumerate_boundaries` instead of re-deriving it.

### IN-03: Full wire-time strictness leaves no supported per-node annotation field

**File:** `databasise/parts/schema.py:132`, `databasise/validator/parse.py:126-138`
**Issue:** With `extra="forbid"`, any node-level key outside `component`/`kind`/`effects`/
`config`/`deps` — including an author's own documentation/annotation field such as `"notes"` or
`"description"` — is now refused as `CODE_INVALID_NODE_SCHEMA` (this is exactly what the c2 probe
demonstrates on purpose). This is clearly deliberate given the module's own docstring ("Full
wire-time strictness... An unknown node key is therefore refused rather than silently
discarded"), and is not a bug, but it's worth recording: there is no supported channel for a
wiring author to leave a per-node comment other than repurposing `config` (which is semantically
the part's own opaque configuration, not documentation). Not actionable unless a future phase
wants to add an explicitly-allowed metadata key.

---

_Reviewed: 2026-09-01T00:14:11Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
