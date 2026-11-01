---
phase: 13-selectors-wiring-runner
plan: 02
subsystem: seam
tags: [selectors, capability, reads_namespaces, part-registry, effect-literal]
requires: []
provides:
  - Part.reads_namespaces trailing field carrying read-namespace capability tokens
  - selectors._wiring_read_namespaces and a matcher over effects union tokens
  - tokens on entity-lookup, relation-lookup, retriever-chunk-topk, chunk-selector-kg
  - PartRegistry.register refusals UnknownPartEffectError and InvalidReadNamespaceTokenError
affects: [13-03]
actuals:
  tokens: 5900
  tasks: 3
  commits: 3
plan_head_before: 75bd946293a1d5d6aacf80b6f72aabef46f9f70b
plan_head_after: 7e47f82d4e368f7300312461b8b9d7f5cc7e6d8d
tech-stack:
  added: []
  patterns: ["matching-only token set kept apart from effects", "named ValueError subclass per registration refusal"]
key-files:
  created:
    - databasise/tests/seam/test_selector_reachability.py
    - databasise/tests/seam/test_advanced_query_members.py
  modified:
    - databasise/parts/schema.py
    - databasise/parts/registry.py
    - databasise/parts_core/lightrag/entity_lookup.py
    - databasise/parts_core/lightrag/relation_lookup.py
    - databasise/parts_core/lightrag/chunk_vector.py
    - databasise/parts_core/lightrag/chunk_sel_kg.py
    - databasise/seam/selectors.py
    - databasise/seam/query.py
key-decisions:
  - "Read-namespace tokens live on Part.reads_namespaces, never in effects; _wiring_effects is untouched so promotion and compare read the same union as before"
  - "The four advanced query members are refused for this contract version by registry effect validation, not by absence"
requirements-completed: [WIRE-01, WIRE-16]
coverage:
  - id: D1
    description: "Each of the six candidates resolves from a production capability selector without a promote; the docstring states every mapping"
    requirement: WIRE-01
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_selector_reachability.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Registration refuses effects outside the Effect literal; the four advanced members stay refused"
    requirement: WIRE-16
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_advanced_query_members.py"
        status: pass
    human_judgment: false
duration: 40min
completed: 2026-10-19
status: complete
---

# Phase 13 Plan 02: Selector reachability and advanced-member refusal Summary

**Local, global and hybrid are now selectable by `reads_vector:<namespace>` capability tokens declared on a new `Part.reads_namespaces` field, and part registration refuses any effect outside the frozen 17-member `Effect` literal.**

## Accomplishments

- `[reads_vector:entities]` -> local, `[reads_vector:relationships]` -> global, both tokens (either order) -> hybrid, `[reads_vector:chunks]` -> naive; the effect-only mappings (`[reads_vector]` naive, `[calls_llm]` bypass, `[reads_graph, reads_kv]`/`[reads_graph]`/`[reads_graph, calls_llm]` hipporag, `[reads_graph, calls_rerank]` local, `[writes_graph]` refused) resolve as at HEAD and are pinned.
- `selectors.py` docstring lists every mapping and the one-node margin (hipporag 14 full nodes against local and global at 15); it no longer claims effects alone distinguish the arms.
- `PartRegistry.register` refuses an effect outside `typing.get_args(Effect)` (`UnknownPartEffectError`) and a malformed or undeclared namespace token (`InvalidReadNamespaceTokenError`), both before filing.
- `query.py` docstring states the four advanced members are refused for this contract version.

## Task Commits

1. Task 1 (tracer): 5d6bd8a - Part.reads_namespaces, matcher helper, entity-lookup token, local arm selectable
2. Task 2: 57c3ef0 - relation, chunk-vector and chunk-selector tokens; docstring rewrite; mapping pins
3. Task 3: 7e47f82 - effect validation in register; query.py docstring; WIRE-16 tests; token-validation test

## Intended ledger test_refs and fail-first evidence

Phase base b0b5a6c; selectors.py, registry.py and query.py are unchanged between the base and plan start (13-01 touched neither), so each failure below is from the unchanged source. All are plain AssertionErrors.

**WIRE-01** - `databasise/tests/seam/test_selector_reachability.py`
- `::test_each_candidate_has_a_selector[local]`: `AssertionError: UnsatisfiableSelectorError` (selector `['reads_vector:entities']`)
- `::test_each_candidate_has_a_selector[global]`: `AssertionError: UnsatisfiableSelectorError` (`['reads_vector:relationships']`)
- `::test_each_candidate_has_a_selector[hybrid]`: `AssertionError: UnsatisfiableSelectorError` (both tokens)
- `::test_namespace_token_order_does_not_matter`: `assert UnsatisfiableSelectorError(...) == {'wiring_id': 'lightrag-base', ...}`
- `::test_a_chunks_token_selects_naive`: same shape, for `['reads_vector:chunks']`
- `::test_docstring_states_every_mapping`: `AssertionError: reads_vector:entities` (missing from the module docstring)
- `::test_registration_refuses_a_malformed_or_undeclared_namespace_token[...]`: added with Task 3; at the base `Part` has no `reads_namespaces` field, so this was not run against the base (see Deviations).
- Pass at base by design: `test_each_candidate_has_a_selector[naive|bypass|hipporag]` and `test_documented_reads_graph_mappings`. `test_an_entity_token_never_selects_global_and_a_relation_token_never_selects_local` passed at the base in its first form (an exception is not equal to an arm); it was then strengthened to also assert the result is not an exception, and that form was not run against the base, though it would fail there.

**WIRE-16** - `databasise/tests/seam/test_advanced_query_members.py`
- `::test_an_effect_outside_the_literal_is_refused`: `AssertionError: registration accepted an effect outside the Effect literal`
- `::test_a_corrected_registration_succeeds_after_a_refusal`: `assert None is not None` (the first registration of `reads_space` was accepted)
- `::test_query_docstring_states_the_members_are_refused_for_this_contract_version`: `'A later phase that registers' not in <docstring>` failed
- Pass at base (D-10): `test_each_advanced_member_is_refused[embedding|predicates|profile_ref|formal_query]`, `test_each_frozen_effect_registers[*]`, `test_no_effects_registers`

## Deviations from Plan

**1. [Rule 2 - Missing critical] Token-validation test added**
- **Found during:** Task 3
- **Issue:** `register`'s `reads_namespaces` validation is new non-trivial logic and the plan listed no test for it.
- **Fix:** `test_registration_refuses_a_malformed_or_undeclared_namespace_token` (5 tokens) in `test_selector_reachability.py`, committed with Task 3. It has no base-run evidence because the field does not exist at the base.
- **Commit:** 7e47f82

**2. [Wording] Test file trimmed for the tracer commit**
- The Task 1 file held only the candidate test with `xfail(strict=True)` on global and hybrid; the rest was written in the Task 2 commit. The fail-first runs above were taken from the full file against the unchanged source before the split.

**Total deviations:** 2. **Impact:** none on scope.

## Verification

`cd databasise && .venv/bin/pytest -q tests/seam tests/runner tests/validator tests/wirings tests/identity tests/parts tests/parts_core tests/evidence tests/parity`: 1649 passed, 3 deselected. Protected `test_seam_doc_consistency.py`, `test_selectors.py`, `test_empty_capability_selector.py`, the HippoRAG query and write path tests and `test_ingest_abort.py` pass unedited.

## Known Stubs

None.

## Threat Flags

None. T-13-03 (tokens read from the registered Part, `_wiring_effects` unchanged) and T-13-04 (validation before filing, registry unchanged after a refusal) are mitigated and tested.

## Self-Check: PASSED

Both created test files exist; commits 5d6bd8a, 57c3ef0, 7e47f82 are ancestors of HEAD.
