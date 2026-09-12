---
phase: 02-falsifier-gate
plan: 01
subsystem: evidence
tags: [falsifier-2, validator, depth, execution-mode, mach-01]
dependency graph:
  requires: []
  provides:
    - "databasise.evidence.falsifier2 (evaluate_wiring, enumerate_boundaries, render_markdown, main)"
    - "databasise/evidence/wirings/{w1,w2,w3}*.json — MACH-01's three named wirings"
    - "databasise/evidence/FALSIFIER-2-EVIDENCE.md — committed, re-runnable Falsifier 2 evidence"
  affects:
    - "databasise/pyproject.toml (packages, package-data)"
tech-stack:
  added: []
  patterns:
    - "declaration-only Part evaluation (parse_wiring/effective_depth/derive_execution_mode/blast_radius_violations, never dispatch())"
    - "generated-artifact drift gate: committed Markdown pinned byte-identical against a fresh render"
key-files:
  created:
    - databasise/evidence/__init__.py
    - databasise/evidence/falsifier2.py
    - databasise/evidence/wirings/w1-lightrag-query-side.json
    - databasise/evidence/wirings/w2-codebase-memory-mcp.json
    - databasise/evidence/wirings/w3-lightrag-half-decomposed.json
    - databasise/evidence/FALSIFIER-2-EVIDENCE.md
    - databasise/tests/validator/test_falsifier2_evidence.py
  modified:
    - databasise/pyproject.toml
decisions:
  - "Evidence artifact lives under databasise/evidence/ (must resolve against live default_registry()), not docs/system-model/wirings/ (illustrative-only by that dir's own README)"
  - "W1's five-node set is authored evidence about the validator's derivation, not a claim about LightRAG's final Phase-3 decomposition"
  - "confined-unit is confirmed unreachable from the seven registered parts — the exact three-value execution_mode set (in-process/subprocess/long-lived-service) is asserted, not a count"
metrics:
  duration: "~35 min"
  completed: 2026-08-31
status: complete
actuals:
  tokens: 8700
  tasks: 2
  commits: 2
---

# Phase 2 Plan 01: Falsifier 2 Evidence Run Summary

Committed, re-runnable Falsifier 2 evidence: MACH-01's three named wirings computed against the
real validator (`parse_wiring`/`effective_depth`/`derive_execution_mode`/`blast_radius_violations`)
and rendered into a Markdown document, with CONTRACT §19.10's boundary enumeration recorded
alongside each node set.

## What Was Built

`databasise/evidence/falsifier2.py` — a `python -m`-runnable module that loads three committed
wiring JSON documents, resolves every node against `default_registry()`, and computes
`effective_depth`/`execution_mode`/blast-radius verdict per node through the exact same functions
`databasise/runner/scheduler.py` calls (never a reimplementation, never the superseded tracer-era
`derive_execution_mode` also present in `databasise/validator/depth.py`). `render_markdown()`
produces a per-wiring computed-vs-declared table, a divergence list naming every node whose
computed depth overrides its part's own declared `structural_depth`, a CONTRACT §19.10 boundary
enumeration (`effects-change` / `value-crossing` / `knob` rows), and a closing verdict quoting
SELECTION.md's Falsifiers list item 2. The committed `FALSIFIER-2-EVIDENCE.md` is pinned
byte-identical against a fresh render (the drift gate) — it is generated output, never hand-edited.

Task 1 (tracer) built the end-to-end shape against W1 alone (decomposed lightrag-local query
side, 5 nodes) and was verified — `pytest` and `python -m` both passed — before Task 2 expanded to
W2 (opaque `codebase-memory-mcp` arm) and W3 (half-decomposed full LightRAG), both of which
exercise the taint rule: a node with its own part's `structural_depth` `stage` computes
`effective_depth` `opaque` once it transitively depends on an opaque node.

## Verification Results

- `cd databasise && uv run pytest -q` — 245 passed (full suite, no regressions)
- `cd databasise && uv run pytest -q tests/validator/test_falsifier2_evidence.py -x` — 12 passed
- `cd databasise && uv run python -m databasise.evidence.falsifier2` — exits 0, regenerates
  `FALSIFIER-2-EVIDENCE.md` byte-identical to the committed copy (`git diff --exit-code` clean)
- Grep-verified: `falsifier2.py` imports `derive_execution_mode` only from
  `databasise.validator.execution_mode` (canonical, four-value); zero occurrences of
  `validator.depth import derive_execution_mode`, `run_wiring`, or `dispatch(`
- All three wiring JSON documents parse and every `component` value resolves through
  `default_registry().get(...)` without raising
- `boundary_knobs` present as a top-level key (never inside a node object) in all three wiring
  documents
- Human-check (read-through): the rendered document is readable end to end — node tables, taint
  divergence lists, §19.10 boundary tables, and the closing Falsifier 2 verdict all present per
  wiring, without opening a test file

**Computed values, confirmed against the real validator (matching every `must_haves` truth in the
plan):**

| Wiring | Node | structural_depth | effective_depth | execution_mode |
|---|---|---|---|---|
| W1 | retrieve, query-side, generate, assemble | stage | stage | in-process |
| W1 | refine | stage | stage | long-lived-service |
| W2 | cbm | opaque | opaque | subprocess |
| W2 | normalise, answer | stage | **opaque** (taint) | in-process |
| W3 | ingest | opaque | opaque | subprocess |
| W3 | query-side, assemble | stage | **opaque** (taint) | in-process |

Distinct `execution_mode` set across all three wirings: exactly `{in-process, subprocess,
long-lived-service}` — `confined-unit` confirmed unreachable from these seven registered parts, as
expected (02-RESEARCH.md).

## Deviations from Plan

None — plan executed exactly as written. All computed values matched the plan's stated
expectations on first render; no divergence between the computed table and the validator required
stopping to report (the plan's explicit "STOP if any computed value disagrees" clause was never
triggered).

## Known Stubs

None. This is a validation/evidence-generation tool over already-built Phase 1 machinery
(`validator/`, `parts/registry.py`, `parts_core/`); no UI, no placeholder data paths.

## Self-Check: PASSED

- FOUND: databasise/evidence/__init__.py
- FOUND: databasise/evidence/falsifier2.py
- FOUND: databasise/evidence/wirings/w1-lightrag-query-side.json
- FOUND: databasise/evidence/wirings/w2-codebase-memory-mcp.json
- FOUND: databasise/evidence/wirings/w3-lightrag-half-decomposed.json
- FOUND: databasise/evidence/FALSIFIER-2-EVIDENCE.md
- FOUND: databasise/tests/validator/test_falsifier2_evidence.py
- FOUND: commit 6645be2 (Task 1)
- FOUND: commit 1e6793e (Task 2)
