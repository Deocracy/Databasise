# Phase 2: Falsifier Gate - Pattern Map

**Mapped:** 2026-08-31
**Files analyzed:** 5 (2 code+test evidence files, 1 evidence doc, 1 GATE-01 waiver doc, 1 MACH-09 posture note)
**Analogs found:** 5 / 5 (3 exact/role-match code analogs, 2 no-precedent docs — new-synthesis noted)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `databasise/evidence/falsifier2_wirings.py` (or `.json`) | fixture/config | transform (data-in, validated-out) | `databasise/parts_core/declared_only.py` | exact (same "declared constants module, no I/O" shape) |
| `databasise/tests/validator/test_falsifier2_evidence.py` | test | transform/CRUD-over-in-memory-objects | `databasise/tests/validator/test_cycles_and_depth.py` + `databasise/tests/validator/test_blast_radius.py` | exact (same pytest-over-`parse_wiring`/`effective_depth`/`blast_radius_violations` shape) |
| `databasise/evidence/falsifier2_evidence.md` (generated or hand-written table) | doc/report | batch (one-shot table dump) | none in-repo — no prior "evidence doc" exists | no analog — synthesize from `docs/system-model/CONTRACT.md` §19.10's enumeration language + the test's own printed table |
| `.planning/phases/02-falsifier-gate/GATE-01-waiver.md` (or similar) | config/governance doc | event-driven (records a one-time decision) | none in-repo — grepped, no "waiver" precedent | no analog — new-synthesis, cite `docs/system-model/D-VARIANTS/SELECTION.md` directly |
| MACH-09 posture note (e.g. `databasise/evidence/mach09_posture.md` or inline in evidence doc) | doc/config | event-driven (posture record, not runtime code) | `databasise/runner/trace.py` (cited, not modified) | role-match (cites existing honesty-field mechanism rather than building new) |

## Pattern Assignments

### `databasise/evidence/falsifier2_wirings.py` (fixture/config, transform)

**Analog:** `databasise/parts_core/declared_only.py`

**Imports pattern** (whole file, 8 lines):
```python
from __future__ import annotations

from databasise.parts.schema import Part
```

**Core pattern** — module-level constants, each with a doc comment explaining *why* the values are what they are (not just what they are), collected into a tuple at the bottom:
```python
LIGHTRAG_QUERY_SIDE_PART = Part(
    name_at_version="lightrag/query-side@0.1.0",
    kind="subgraph",
    structural_depth="stage",
    effects=["reads_kv", "reads_vector", "reads_graph", "calls_llm", "calls_embedding"],
    upstream_ref="v1/lightrag/operate.py",
    body=None,
    artifact_scope=None,
)
...
DECLARED_ONLY_PARTS: tuple[Part, ...] = (
    LIGHTRAG_QUERY_SIDE_PART,
    CODEBASE_MEMORY_MCP_PART,
    LIGHTRAG_FULL_INGEST_PART,
)
```

For the wirings file, mirror this shape but build `dict` wiring documents (the input shape `parse_wiring(doc, registry)` accepts — see RESEARCH.md Pattern 1), one per named wiring, each referencing the already-registered component names verbatim (`"lightrag/query-side@0.1.0"`, `"codebase-memory-mcp@0.1.0"`, `"lightrag/full-ingest@0.1.0"`). Do **not** invent new component names — resolve against `default_registry()`.

---

### `databasise/tests/validator/test_falsifier2_evidence.py` (test, transform)

**Analogs:** `databasise/tests/validator/test_cycles_and_depth.py` (imports + module docstring shape), `databasise/tests/validator/test_blast_radius.py` (end-to-end `parse_wiring` fixture shape)

**Imports pattern** (from `test_blast_radius.py` lines 1-18 — the end-to-end variant, since the evidence test must go through the real registry, not hand-built `ParsedWiring`):
```python
from __future__ import annotations

from types import MappingProxyType

from databasise.parts.registry import PartRegistry
from databasise.parts.schema import NodeContext, Part, WiringNode
from databasise.validator.blast_radius import blast_radius_violations
from databasise.validator.errors import CODE_BLAST_RADIUS_REFUSAL
from databasise.validator.parse import ParsedWiring, parse_wiring
```
For the evidence test, additionally import:
```python
from databasise.parts.registry import default_registry
from databasise.validator.depth import effective_depth
from databasise.validator.execution_mode import derive_execution_mode  # CANONICAL — not validator.depth's copy
from databasise.validator.errors import CODE_EFFECTS_EXCEED_PART
```

**Module docstring pattern** (from `test_cycles_and_depth.py` lines 1-9) — state what the test covers and *why*, cross-referencing the plan/requirement:
```python
"""Falsifier 2 evidence: the three MACH-01 named wirings compute effective_depth/execution_mode
correctly against the real default_registry(), plus the two self-declaration probes
(effects-exceed-part, blast-radius-refusal) reproducing the 2026-08-31 scratchpad demonstration.
Covers .planning/phases/02-falsifier-gate/02-CONTEXT.md D-03.
"""
```

**Core evidence-run pattern** (RESEARCH.md Pattern 1, verified against real `default_registry()`):
```python
def test_named_wirings_compute_depth_and_execution_mode():
    registry = default_registry()
    for wiring_doc in (W1_DOC, W2_DOC, W3_DOC):
        parsed = parse_wiring(wiring_doc, registry)
        assert parsed.report.ok
        depths = effective_depth(parsed)
        modes = {
            node_id: derive_execution_mode(part.effects, part.kind)
            for node_id, part in parsed.parts.items()
        }
        # assert against the recorded computed-vs-declared table in the evidence doc
```

**Probe (a) pattern** — `effects-exceed-part`, mirror `test_cycles_and_depth.py`'s existing CR-01 test (referenced at module docstring lines 5-9, actual test body not yet read but same shape as `test_blast_radius.py`'s assertion style):
```python
def test_over_declared_effects_refused():
    doc = {"nodes": {"n": {"component": "codebase-memory-mcp@0.1.0", "kind": "opaque",
                            "effects": ["self_storage", "fs", "writes_artifact"], "deps": []}}}
    parsed = parse_wiring(doc, default_registry())
    assert not parsed.report.ok
    assert any(v.code == CODE_EFFECTS_EXCEED_PART for v in parsed.report.violations)
```

**Probe (b) pattern** — `blast-radius-refusal` (from `test_blast_radius.py` lines 44-51, Test 2, adapted to go through `parse_wiring` end-to-end per that file's own Test-3-style regression note):
```python
def test_shared_write_at_opaque_depth_is_refused_naming_node_and_depth():
    parsed = _single_node_parsed(["writes_artifact"], scope="shared")
    violations = blast_radius_violations(parsed, {"n": "opaque"})
    assert len(violations) == 1
    assert "n" in violations[0].message
    assert "opaque" in violations[0].message
```

**Error handling pattern:** None needed — `parse_wiring` never raises for ordinary defects (accumulates into `report.violations`); tests assert `report.ok`/violation codes, never wrap in try/except.

---

### `databasise/evidence/falsifier2_evidence.md` (doc/report, batch)

**No in-repo analog.** Synthesize using:
- `docs/system-model/CONTRACT.md` §19.10's boundary-enumeration language (the "node set so a second author can check the candidate set, not only the verdicts" framing from 02-CONTEXT.md line 115) as the structural template for the enumeration section.
- A per-node table with columns: node id, declared depth (if any), computed `effective_depth`, computed `execution_mode`, blast-radius verdict — one row group per named wiring.
- Owner's explicit requirement (02-CONTEXT.md line 172): "visible in a working environment... re-run and read, not a buried pytest assertion" — the doc should either be generated by the test (printed/written) or hand-maintained alongside it, not purely aspirational prose.

---

### `.planning/phases/02-falsifier-gate/GATE-01-waiver.md` (governance doc)

**No in-repo analog** — grepped `docs/system-model/*.md` and `SELECTION.md` for "waiver", no hits (RESEARCH.md Assumption A3).

**Required content shape** (from 02-CONTEXT.md D-02 and canonical_refs):
- Cite `docs/system-model/D-VARIANTS/SELECTION.md` explicitly (the document it amends).
- State the original ratified §VD verdict's condition (Falsifiers 2 and 5).
- State the amendment: Falsifier 2 stays in Phase 2 (near-free, demonstrated); Falsifier 5 moves to point of first need (Phase 3 parity at earliest); ladder proceeds.
- State that a Falsifier 2 failure still halts (the waiver is scoped, not a blanket skip).

**Placement:** `.planning/` layer per RESEARCH.md Open Question 2's recommendation — `docs/system-model/` is a verbatim upstream mirror (per project CLAUDE.md) and should not be edited directly; the waiver is this project's own amendment record with a citation into the frozen doc.

---

### MACH-09 posture note (doc/config)

**Analog (cited, not modified):** `databasise/runner/trace.py` — the `RunRecord`/`NodeTrace` `degraded`/`degradation_reason`/`stop_reason`/`partial` required-together honesty invariant is already built and schema-validated against `docs/system-model/rig-trace.schema.json`.

**Pattern:** Per RESEARCH.md Pitfall 4 (Common Pitfalls), do NOT build a new config/settings module — no promotion-gated code exists anywhere yet to switch. Write a short doc/assertion recording that the default-off posture holds because the on-path is unbuilt, and cite `trace.py`'s already-complete labelling mechanism rather than re-implementing it. If a guard is wanted, a minimal grep-based or existence-check test suffices (e.g., assert no `promote-now`-shaped verb exists in `runner/`), not a new abstraction.

## Shared Patterns

### Registry resolution — always through `default_registry()`, never hand-rolled
**Source:** `databasise/parts/registry.py:122` (`default_registry()`), used identically by every evidence/probe file
**Apply to:** `falsifier2_wirings.py`, `test_falsifier2_evidence.py`
```python
from databasise.parts.registry import default_registry
registry = default_registry()
assert "lightrag/query-side@0.1.0" in registry.keys()
```

### Canonical `derive_execution_mode` import — the duplication trap
**Source:** `databasise/validator/execution_mode.py` (canonical, 4-value) vs. `databasise/validator/depth.py` (tracer-era duplicate, dead code outside one test)
**Apply to:** Any evidence/probe file computing `execution_mode`
```python
from databasise.validator.execution_mode import derive_execution_mode  # correct
# NEVER: from databasise.validator.depth import derive_execution_mode
```
Grep-verify before trusting any printed `execution_mode` value: `grep -rn "derive_execution_mode" databasise/evidence databasise/tests/validator`.

### One-pass violation accumulation — never raise for ordinary defects
**Source:** `databasise/validator/parse.py` module docstring — `parse_wiring` never raises; every violation lands in `report.violations`, inspected via `report.ok`
**Apply to:** All new tests in `test_falsifier2_evidence.py` — assert on `report.ok`/`violations`, never wrap `parse_wiring` calls in try/except.

### Refusals over silent fallbacks (house style)
**Source:** Phase 1 house style, cited in 02-CONTEXT.md line 153; concrete instance is `registry.dispatch()`'s explicit `DeclarationOnlyPartError` refusal for `body=None` parts
**Apply to:** Evidence artifact must call `parse_wiring`/`effective_depth`/`derive_execution_mode`/`blast_radius_violations` only — never `run_wiring`/`dispatch()` against the three declaration-only parts (RESEARCH.md Pitfall 3).

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `databasise/evidence/falsifier2_evidence.md` | doc/report | batch | No prior "evidence doc" artifact type exists in repo; synthesize from CONTRACT §19.10 language + test output (see above) |
| `.planning/phases/02-falsifier-gate/GATE-01-waiver.md` | governance doc | event-driven | No "waiver" precedent anywhere in repo (grep-confirmed); new-synthesis, cite SELECTION.md directly |

## Metadata

**Analog search scope:** `databasise/validator/`, `databasise/parts_core/`, `databasise/parts/`, `databasise/tests/validator/`, `databasise/runner/trace.py`, `docs/system-model/`, `.planning/`
**Files scanned:** `validator/parse.py`, `validator/depth.py`, `validator/execution_mode.py`, `validator/blast_radius.py`, `parts_core/declared_only.py`, `parts/registry.py`, `tests/validator/test_cycles_and_depth.py`, `tests/validator/test_blast_radius.py`, `docs/system-model/wirings/README.md` (confirmed illustrative-only, not used as analog per RESEARCH.md's explicit anti-pattern)
**Pattern extraction date:** 2026-08-31
</content>
