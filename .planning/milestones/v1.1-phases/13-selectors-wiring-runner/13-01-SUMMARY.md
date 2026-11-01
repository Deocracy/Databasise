---
phase: 13-selectors-wiring-runner
plan: 01
subsystem: validator
tags: [wiring, validator, parse_wiring, execution_mode, rfc6901]
requires: []
provides:
  - parse_wiring that reports every malformed document instead of raising
  - RFC 6901 pointer escaping, deduplicated sorted cycles, kind-mismatch violation, no registry leak
  - CODE_INVALID_WIRING_DOCUMENT, CODE_KIND_MISMATCH, CODE_CYCLIC_WIRING in validator/errors.py
  - validator/execution_mode.py as the only placement source
affects: [13-06, 13-03]
actuals:
  tokens: 14000
  tasks: 3
  commits: 4
plan_head_before: b0b5a6c8de6090907d1ddeab19b7513f447f1a75
plan_head_after: 5d61a799abc0e0cc13af2a50fc2e40a59682c847
tech-stack:
  added: []
  patterns: ["report-not-raise for untrusted author input", "escape_pointer_token shared in validator/errors.py"]
key-files:
  created:
    - databasise/tests/validator/test_parse_report.py
    - databasise/tests/validator/test_execution_mode_single_source.py
  modified:
    - databasise/validator/parse.py
    - databasise/validator/errors.py
    - databasise/validator/blast_radius.py
    - databasise/validator/depth.py
    - databasise/validator/execution_mode.py
    - databasise/parts_core/fixpoint_body.py
    - databasise/seam/engine.py
    - databasise/tests/parts/test_reference_parts.py
    - databasise/tests/validator/test_taint_conformance.py
    - databasise/tests/validator/test_cycles_and_depth.py
key-decisions:
  - "A kind-mismatch is a violation; old fixtures that declared a different kind were corrected, not the check weakened"
  - "escape_pointer_token lives in validator/errors.py so parse.py and blast_radius.py share it without an import cycle"
  - "ParsedWiring docstring says 'immutable views' (not 'read-only') because the WIRE-07 test forbids the phrase"
requirements-completed: [WIRE-06, WIRE-07]
coverage:
  - id: D1
    description: "parse_wiring reports malformed documents, escapes pointers, lists cycles once, flags kind mismatch, leaks no registry content"
    requirement: WIRE-06
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_parse_report.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Execution placement has one source; dead and stale validator items removed"
    requirement: WIRE-07
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_execution_mode_single_source.py"
        status: pass
    human_judgment: false
duration: 55min
completed: 2026-10-20
status: complete
---

# Phase 13 Plan 01: Validator hardening and single placement source Summary

**parse_wiring now reports malformed wiring documents (RFC 6901 pointers, one entry per cyclic node, kind-mismatch, no registry leak) and `validator/execution_mode.py` is the only execution-placement source.**

## Accomplishments

- A non-object document or non-object `nodes` yields one `invalid-wiring-document` violation; a query on `{"nodes": None}` is refused as the existing 422 `UnparseableWiringError`.
- Pointers escape `~` then `/` in `parse.py` and `blast_radius.py`; a self-loop inside a larger cycle is no longer listed twice and `report.cycles` is sorted.
- The unknown-component message names only the wiring's own component; a node whose `kind` differs from its part's is `kind-mismatch`.
- `validator.depth.derive_execution_mode`, `_REQUIRES_CONTAINMENT` and `WiringValidationError` are deleted; stale "Phase 1" text is gone; `blast_radius` reads `part.artifact_scope` directly; the D-18 rule (machine-client callers are in-process) is documented and pinned.

## Task Commits

1. Task 1 (tracer): c813d85 - malformed document reported, engine refusal
2. Task 2: 9bffb16 - pointers, cycles, message leak
3. Task 3: 82529bf - one placement source, dead items removed
4. Follow-up: 5d61a79 - kind-mismatch check and fixture corrections

## Intended ledger test_refs and fail-first evidence

Phase base b0b5a6c; each failure is a plain AssertionError from the unchanged source.

**WIRE-06** - `databasise/tests/validator/test_parse_report.py`
- `::test_a_malformed_document_is_reported_not_raised[list|none|list-nodes]`: `AssertionError: parse_wiring raised AttributeError: 'list' object has no attribute 'items'`
- `::test_a_query_on_a_malformed_document_is_refused_by_name`: `AssertionError: AttributeError("'NoneType' object has no attribute 'values'")`
- `::test_a_self_loop_inside_a_larger_cycle_is_listed_once`: `assert [['a','b'],['a']] == [['a','b']]`
- `::test_a_node_id_with_a_slash_or_tilde_is_escaped_in_the_pointer[x/y|a~b]`: `'/nodes/x/y/component' != '/nodes/x~1y/component'`; `'/nodes/a~b/component' != '/nodes/a~0b/component'`
- `::test_a_kind_mismatch_is_a_violation`: `assert [] == ['/nodes/a/kind']`
- `::test_the_unknown_component_message_leaks_no_registry_content`: message began with a quote and embedded "registered parts: [...]"
- Pass at base (edge and guard legs): `test_an_empty_document_reports_empty_wiring`, `test_a_separate_self_loop_keeps_its_own_entry`, `test_every_shipped_wiring_still_parses_ok`

**WIRE-07** - `databasise/tests/validator/test_execution_mode_single_source.py`
- `::test_depth_defines_no_placement_function`: `AssertionError: assert not True where True = hasattr(depth, 'derive_execution_mode')`
- `::test_parse_defines_no_unraised_validation_error`: `hasattr(parse, 'WiringValidationError')` was True
- `::test_no_placement_text_names_phase_1`: 4 "Phase 1" hits
- `::test_parsed_wiring_docstring_does_not_claim_read_only`: `'read-only' not in ...` failed
- `::test_blast_radius_reads_artifact_scope_directly`: regex matched `getattr(part, "artifact_scope`
- Pass at base (D-18 pins, no behaviour change needed): `test_machine_client_callers_are_in_process[calls_llm|calls_embedding|calls_rerank]`, `test_an_empty_effect_list_derives_in_process`

## Deviations from Plan

**1. [Rule 3 - Blocking] engine.py injectors raised before parse_wiring**
- **Found during:** Task 1
- **Issue:** `_inject_token_allowance` and `_inject_max_total_tokens` call `.values()` on `resolved["nodes"]` before `parse_wiring`, so `{"nodes": None}` raised `AttributeError` and never reached the 422 refusal. The plan said no engine edit was needed.
- **Fix:** `_node_dicts` helper in `seam/engine.py` (yields only dict nodes of a dict `nodes`) used by both injectors, plus an isinstance guard in `_inject_query`.
- **Files modified:** databasise/seam/engine.py
- **Commit:** c813d85

**2. [Rule 1 - Bug] Fixtures declared a kind different from their part's kind**
- **Found during:** Task 2 (kind-mismatch check)
- **Issue:** D-08 makes a differing kind a violation; three fixture sites pinned the old behaviour. Both files were confirmed unprotected (not ledger test_refs) by the coordinator.
- **Fix:** `tests/validator/test_taint_conformance.py` (`_n()` now uses the fixture Part's kind, i.e. `spec["depth"]`; the inline ingest node uses `"opaque"`) and `tests/validator/test_cycles_and_depth.py` (nodes use `passthrough` or `kv-writer`; the unknown-component node is unchanged). The kind check was withheld from commits 9bffb16 and 82529bf and landed with the fixtures in 5d61a79.
- **Commit:** 5d61a79

**3. [Wording] "read-only" docstring**
- The plan action says to describe four members as read-only views, but its own test forbids "read-only"; the docstring says "immutable views".

**Total deviations:** 3 (1 Rule 3, 1 Rule 1, 1 wording). **Impact:** none on scope; `runner/scheduler.py` docstring still mentions the depth copy and is left to 13-03 as planned.

## Verification

`cd databasise && .venv/bin/pytest -q tests/seam tests/runner tests/validator tests/wirings tests/identity tests/parts tests/parts_core tests/evidence tests/parity`: 1608 passed, 3 deselected. All shipped wirings (`all_wirings()`, corpus-ingest and corpus-delete for both families) parse ok with the kind check active.

## Known Stubs

None.

## Threat Flags

None. T-13-01 and T-13-02 are mitigated and tested.

## Self-Check: PASSED

Created test files exist; commits c813d85, 9bffb16, 82529bf, 5d61a79 are ancestors of HEAD.
