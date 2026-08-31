---
phase: 02-falsifier-gate
plan: 03
subsystem: validator
tags: [falsifier-2, mach-01, self-declaration, blast-radius, pydantic, wire-time-strictness]

requires:
  - phase: 02-falsifier-gate
    provides: "plan 02-01's databasise/evidence/ module (evaluate_wiring, load_wiring, render_markdown, main) and the three committed wiring documents"
provides:
  - "CODE_SELF_DECLARED_DERIVATION — a stable refusal code distinguishing an attempted self-declaration of a computed property from an ordinary node-schema typo"
  - "WiringNode.model_config = ConfigDict(extra=\"forbid\") — wire-time strictness on every wiring node, closing MACH-01's no-self-declaration clause"
  - "databasise.evidence.falsifier2.PROBES / probe_registry() / evaluate_probe() — a seven-probe, paired refusal-and-control suite rendered into the committed evidence document"
affects: ["phase 3 (LightRAG query-side decomposition writes wirings against the stricter node schema)", "phase 4 (§18 seam plans consume the same refusal codes)"]

actuals:
  tokens: 7904
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "paired refusal-and-control probe: every probe expecting a violation is paired with a probe over the same shape that must NOT violate, so a check that stops firing shows up as a failed test/evidence row instead of a quietly green suite"
    - "probe-only registry parts assembled fresh per call (probe_registry() = default_registry() + N) — never mutated into a shared or production registry instance"

key-files:
  created:
    - databasise/tests/validator/test_falsifier2_probes.py
  modified:
    - databasise/parts/schema.py
    - databasise/validator/errors.py
    - databasise/validator/parse.py
    - databasise/evidence/falsifier2.py
    - databasise/evidence/FALSIFIER-2-EVIDENCE.md

key-decisions:
  - "extra=\"forbid\" applies only at WiringNode's top level; a node's config dict stays dict[str, Any] and unrestricted, so existing fixtures that pass runtime values (e.g. effective_depth inside a writer part's config, not on the node itself) are unaffected"
  - "The derivation refusal message names the offending node id, the field, and the exact function that computes that value (e.g. databasise.validator.depth.effective_depth), so an author can act on it without reading the validator's source"
  - "All seven probes resolve against probe_registry() rather than default_registry(), including the c1/c2/c3 family built on W3 — probe_registry() is a superset so this is uniform and simpler than switching registries per probe"

patterns-established:
  - "Derived-field enumeration lives as a module-level frozenset in validator/parse.py (_DERIVED_FIELD_NAMES), explicitly flagged as this plan's own enumeration to extend when a future phase adds a computed property"

requirements-completed: [MACH-01]

coverage:
  - id: D1
    description: "A wiring node self-declaring a derived field (effective_depth, execution_mode, structural_depth, depth, artifact_scope, blast_radius) is refused under the stable code self-declared-derivation, naming the node and field, distinct from an ordinary unknown-key typo (invalid-node-schema)"
    requirement: "MACH-01"
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_falsifier2_probes.py#test_probe_matches_its_expected_code_exactly[c1-self-declared-effective-depth]"
        status: pass
      - kind: unit
        ref: "databasise/tests/validator/test_falsifier2_probes.py#test_probe_matches_its_expected_code_exactly[c2-unknown-node-key]"
        status: pass
    human_judgment: false
  - id: D2
    description: "The blast-radius threshold is demonstrated at all three rungs of the depth ladder: no violation at stage, a refusal at evidence, and a refusal at opaque reached via the taint rule (SELECTION.md Falsifier 1 limb (b))"
    requirement: "MACH-01"
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_falsifier2_probes.py#test_probe_matches_its_expected_code_exactly[b1-shared-write-at-stage]"
        status: pass
      - kind: unit
        ref: "databasise/tests/validator/test_falsifier2_probes.py#test_probe_matches_its_expected_code_exactly[b2-shared-write-at-evidence]"
        status: pass
      - kind: unit
        ref: "databasise/tests/validator/test_falsifier2_probes.py#test_b3_blast_radius_refusal_names_the_downstream_extractor_node"
        status: pass
    human_judgment: false
  - id: D3
    description: "A wiring node over-declaring an effect its resolved part does not carry is refused under effects-exceed-part, reproducing the scratchpad demonstration against a named part"
    requirement: "MACH-01"
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_falsifier2_probes.py#test_probe_matches_its_expected_code_exactly[a-effects-exceed-part]"
        status: pass
    human_judgment: false
  - id: D4
    description: "The committed evidence document records every probe with its wiring, expected refusal code, and observed code, and regenerates byte-identically (drift gate)"
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_falsifier2_evidence.py#test_committed_evidence_document_matches_a_fresh_render"
        status: pass
      - kind: other
        ref: "uv run python -m databasise.evidence.falsifier2 && git diff --exit-code -- evidence/FALSIFIER-2-EVIDENCE.md"
        status: pass
    human_judgment: false
  - id: D5
    description: "No probe-only part leaks into the production default_registry(); the probe suite runs against a fresh probe_registry() every call"
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_falsifier2_probes.py#test_probe_only_parts_never_leak_into_the_production_registry"
        status: pass
    human_judgment: false

duration: ~25min
completed: 2026-08-31
status: complete
---

# Phase 2 Plan 03: Self-Declaration Refusal + Probe Suite Summary

Wire-time strictness (`extra="forbid"`) on `WiringNode` plus a stable `self-declared-derivation`
refusal code that closes MACH-01's no-self-declaration clause, backed by a seven-probe suite
(effects-exceed-part, three blast-radius rungs, three self-declaration cases) rendered into the
committed `FALSIFIER-2-EVIDENCE.md`.

## Performance

- **Duration:** ~25 min
- **Tasks:** 2/2
- **Files modified:** 5 modified, 1 created

## Accomplishments

- `databasise/parts/schema.py`'s `WiringNode` now refuses any unknown node key at parse time
  (`extra="forbid"`), closing the wire-time-strictness gap plan 02-01's inline comment deferred to
  this phase.
- `databasise/validator/errors.py` gained `CODE_SELF_DECLARED_DERIVATION = "self-declared-derivation"`,
  and `databasise/validator/parse.py`'s `_classify_node_schema_error` now distinguishes an attempted
  self-declaration of one of the six derived fields (`effective_depth`, `execution_mode`,
  `structural_depth`, `depth`, `artifact_scope`, `blast_radius`) from every other unknown key
  (`invalid-node-schema`) — a typo and an attempted self-declaration are never conflated by code.
  The violation message names the node, the field, and the exact function that computes that
  value (e.g. `databasise.validator.depth.effective_depth`), mirroring
  `validator/blast_radius.py`'s own message-clarity property.
- `databasise/evidence/falsifier2.py` gained two probe-only parts
  (`probe/shared-artifact-writer@0.1.0`, `probe/evidence-writer@0.1.0`), `probe_registry()` (a
  fresh `default_registry()` plus those two, never mutated into the production registry), an
  ordered `PROBES` tuple of seven paired refusal-and-control probes, and `evaluate_probe()`.
  `render_markdown()` gained a `## Self-declaration probes` section recording expected-vs-observed
  refusal codes and a one-line "what it would mean if this stopped firing" note per probe; the
  closing `## Falsifier 2 verdict` was extended to state that all three named wirings compute
  without self-declaration and every probe fired as expected.
- `databasise/tests/validator/test_falsifier2_probes.py` (new) asserts every probe's observed
  code against its expectation, that `b3`'s refusal names the downstream `extract` node (not the
  opaque `cbm` node it taints from), that `c3` computes `query-side`'s `effective_depth` as
  `opaque` on unmodified W3, and that neither probe-only part appears in `default_registry().keys()`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Refuse a self-declared derived field on a wiring node under its own violation code** - `cc44c08` (feat)
2. **Task 2: Land the probe suite with paired controls and record it in the evidence document** - `8c08349` (feat)

_Note: worktree mode — STATE.md/ROADMAP.md metadata commit is made centrally by the orchestrator after wave merge, not by this plan._

## Files Created/Modified

- `databasise/parts/schema.py` - `WiringNode.model_config` now `ConfigDict(extra="forbid")`
- `databasise/validator/errors.py` - new `CODE_SELF_DECLARED_DERIVATION` code and docstring note
- `databasise/validator/parse.py` - `_DERIVED_FIELD_NAMES`, `_DERIVED_FIELD_COMPUTED_BY`, and the
  extended `_classify_node_schema_error` / message-building logic in `parse_wiring`
- `databasise/evidence/falsifier2.py` - two probe-only parts, `probe_registry()`, `Probe`,
  `PROBES`, `evaluate_probe()`, and the extended `render_markdown()`
- `databasise/evidence/FALSIFIER-2-EVIDENCE.md` - regenerated with the new
  `## Self-declaration probes` section and extended verdict text (generated output, never
  hand-edited; the drift gate stays green)
- `databasise/tests/validator/test_falsifier2_probes.py` (new) - the probe-suite test module

## Decisions Made

- `extra="forbid"` was verified against every existing wiring fixture in the repository
  (`tests/validator/test_cycles_and_depth.py`, `test_taint_conformance.py`,
  `test_phase_success_criteria.py`, `test_embed_startup.py`, `tests/fixtures/wiring-tracer.json`,
  all three `evidence/wirings/*.json` documents) before landing — none declares an unknown
  top-level node key, so no fixture needed repair. The one place `effective_depth` appears inside
  an existing fixture (`test_phase_success_criteria.py`'s arms wiring) is inside a node's `config`
  dict, which stays `dict[str, Any]` and unrestricted — `extra="forbid"` only governs
  `WiringNode`'s own top-level fields.
- All seven probes are resolved against `probe_registry()` uniformly (including the W3-derived
  `c1`/`c2`/`c3` family, which only needs `default_registry()`'s entries) rather than switching
  registries per probe — `probe_registry()` is a strict superset, so this is simpler with no
  behavioral difference.
- The probe suite's `evaluate_probe()` returns the observed violation-code set (used by both the
  test module and the evidence renderer); finer per-probe assertions (which node a refusal names,
  which depth a control computes) call `parse_wiring`/`effective_depth` directly in the test
  module rather than growing `evaluate_probe`'s return shape.

## Deviations from Plan

None — plan executed exactly as written. No existing fixture required repair under the stricter
schema (see Decisions Made above); the plan's explicit "if an existing fixture carries an unknown
node key, fix the fixture" contingency was never triggered.

## Known Stubs

None. This plan closes a validator-strictness gap and lands evidence over already-built Phase 1
machinery; no UI, no placeholder data paths.

## Threat Flags

None. The change narrows an existing wire-time acceptance surface (refusing more input, not
accepting more) and adds no new network endpoint, auth path, file access pattern, or schema
change at a trust boundary.

## Issues Encountered

None.

## Next Phase Readiness

- Falsifier 2's no-self-declaration clause (MACH-01) is now closed with a committed, re-runnable
  probe suite: `cd databasise && uv run python -m databasise.evidence.falsifier2` regenerates
  `FALSIFIER-2-EVIDENCE.md` byte-identically, and `uv run pytest -q` is green (259 tests) under
  the stricter `WiringNode` schema.
- Every wiring authored from Phase 3 onward is now written against the stricter node schema by
  construction — a later reversal to permissive parsing would silently re-admit the self-declared
  derivation fields this plan's evidence run exists to refuse (Task 1's `costly` reversibility
  rating).
- No blockers for Phase 2's remaining plan(s) or Phase 3.

## Self-Check: PASSED

- FOUND: databasise/tests/validator/test_falsifier2_probes.py
- FOUND: commit cc44c08 (Task 1)
- FOUND: commit 8c08349 (Task 2)
- FOUND: `CODE_SELF_DECLARED_DERIVATION = "self-declared-derivation"` in databasise/validator/errors.py
- FOUND: `extra="forbid"` in databasise/parts/schema.py; `extra="ignore"` count is 0
- FOUND: all seven probe ids (`a-effects-exceed-part`, `b1-shared-write-at-stage`,
  `b2-shared-write-at-evidence`, `b3-shared-write-tainted-to-opaque`,
  `c1-self-declared-effective-depth`, `c2-unknown-node-key`, `c3-computed-depth-governs`) and all
  three refusal codes (`self-declared-derivation`, `blast-radius-refusal`, `effects-exceed-part`)
  in databasise/evidence/FALSIFIER-2-EVIDENCE.md
- FOUND: `cd databasise && uv run pytest -q` — 259 passed
- FOUND: `cd databasise && uv run pytest -q tests/validator/test_falsifier2_probes.py -x` — 11 passed
- FOUND: `cd databasise && uv run python -m databasise.evidence.falsifier2 && git diff --exit-code -- evidence/FALSIFIER-2-EVIDENCE.md` — exit 0 (drift gate clean against HEAD)

---
*Phase: 02-falsifier-gate*
*Completed: 2026-08-31*
