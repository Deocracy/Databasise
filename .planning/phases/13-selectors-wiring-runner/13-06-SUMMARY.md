---
phase: 13-selectors-wiring-runner
plan: 06
subsystem: validator
tags: [evidence, ghost-references, lightrag-assemble, arm-patches]
requires: ["13-01", "13-05"]
provides:
  - LightRAG assemble emits items (the chunks it put into the context, {id, score}, context order)
  - local, global, hybrid evidence_position {assemble, chunks}; bypass evidence_position null
  - parse_wiring violations unknown-provides and unknown-evidence-node
affects: [13-12]
actuals:
  tokens: 14000
  tasks: 2
  commits: 2
plan_head_before: de135fb00763f7d9a9ab06fe9e8154e136fb2249
plan_head_after: c5c46ccabed2914f0c0d00078b2747947d5da49e
tech-stack:
  added: []
  patterns: ["top-level references checked against the wiring's own nodes", "evidence minted from the node that assembled the context"]
key-files:
  created:
    - databasise/tests/seam/test_evidence_position.py
    - databasise/tests/validator/test_top_level_refs.py
  modified:
    - databasise/parts_core/lightrag/assemble.py
    - databasise/wirings/lightrag/arm-local.json-patch.json
    - databasise/wirings/lightrag/arm-global.json-patch.json
    - databasise/wirings/lightrag/arm-hybrid.json-patch.json
    - databasise/wirings/lightrag/arm-bypass.json-patch.json
    - databasise/validator/parse.py
    - databasise/validator/errors.py
key-decisions:
  - "Evidence for the KG arms is assemble's truncated chunk list (v1's reference list), not join-chunks or rerank (D-02)"
  - "The ghost check runs independently of the other checks and gates the depth/blast-radius pass like any other violation"
requirements-completed: [WIRE-02]
coverage:
  - id: D1
    description: "Every resolved wiring (all arms, both modalities, corpus wirings; full and pruned) names only nodes it contains; the validator reports a ghost provides or evidence node"
    requirement: WIRE-02
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_top_level_refs.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "A local-arm query after a real-driver ingest returns non-empty evidence that resolves; bypass returns []"
    requirement: WIRE-02
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_evidence_position.py::test_a_local_arm_query_returns_non_empty_evidence_that_resolves"
        status: pass
    human_judgment: false
duration: 30min
completed: 2026-10-19
status: complete
---

# Phase 13 Plan 06: KG arms return evidence, ghost references are reported Summary

**LightRAG `assemble` now emits the chunks it put into the context as `items`, the local, global and hybrid arms mint evidence from it, bypass declares `evidence_position: null`, and `parse_wiring` reports any `provides` entry or evidence node the wiring does not contain.**

## Accomplishments

- `parts_core/lightrag/assemble.py`: returns `items`, one `{id: chunk_id or id, score}` per chunk of the truncated list, in context order (no re-sort). The id is the chunk id that keys the `chunks` vector namespace. KG items carry no score, so `score` is `None` there, which `EvidenceRef` accepts.
- Arm patches: local, global, hybrid gain `replace /evidence_position {node: assemble, namespace: chunks}`; bypass gains `replace /evidence_position null`. `base.json` and `arm-naive` are untouched (naive keeps `chunk-vector`).
- `validator/errors.py` + `validator/parse.py`: `CODE_UNKNOWN_PROVIDES` (pointer `/provides/<i>`) and `CODE_UNKNOWN_EVIDENCE_NODE` (pointer `/evidence_position/node`). Empty `provides`, null or absent `evidence_position` add nothing. The check needs no other check to pass first.
- A real-driver local-arm query returns non-empty evidence and every ref resolves through `Databasise.resolve_evidence`; a bypass query returns `[]` without error. The real-driver tests ran (not skipped).

## Task Commits

1. Task 1 (tracer): 6fe2918 - assemble `items`, arm-local evidence position, `test_evidence_position.py`
2. Task 2: c5c46cc - global, hybrid, bypass patches, violation codes and ghost check, `test_top_level_refs.py`, remaining evidence-position tests

Verification: `tests/seam tests/runner tests/validator tests/wirings tests/identity tests/parts tests/parts_core tests/evidence tests/parity` -> 1738 passed, 3 deselected (protected tests included, none needed a grant).

## Intended ledger test_refs and fail-first evidence

Pre-fix runs were made against the unchanged source at the point each test was written (Task 1 tests against plan-start source de135fb; Task 2 tests against Task 1's source). For the code these tests touch, that equals the phase base b0b5a6c, which the orchestrator's `record-fail --at` route re-checks. All failures are plain `AssertionError`.

**WIRE-02** - intended test_ref `databasise/tests/validator/test_top_level_refs.py` (ghost and per-arm legs), plus the evidence legs in `databasise/tests/seam/test_evidence_position.py`.

`databasise/tests/validator/test_top_level_refs.py`
- `::test_a_ghost_provides_entry_is_a_violation`: `AssertionError: assert ('unknown-provides', '/provides/0') in []`
- `::test_only_the_ghost_provides_entry_is_reported`: `AssertionError: assert ('unknown-provides', '/provides/1') in []`
- `::test_a_ghost_evidence_node_is_a_violation`: `AssertionError: assert ('unknown-evidence-node', '/evidence_position/node') in []`
- `::test_a_node_removed_by_a_patch_but_still_named_is_a_violation`: `AssertionError: assert ('unknown-evidence-node', '/evidence_position/node') in [] `
- `::test_every_resolved_wiring_names_only_its_own_nodes[bypass-full]` (also `bypass-pruned`, `hybrid-full|pruned`, `global-full|pruned`): `AssertionError: bypass (full) names missing nodes ['chunk-vector']`. The parametrize ids are `<wiring>-<full|pruned>`, not the bare `[bypass]` of the plan acceptance text. The test checks `provides` and `evidence_position.node` against `nodes` directly as well as through the validator, because the validator check does not exist before the fix and a validator-only assertion could not fail there. `local-full|pruned` fail only before Task 1.
- `::test_bypass_names_no_removed_node`: `AssertionError: assert {'node': 'chunk-vector', 'namespace': 'chunks'} is None`
- Pass at the base by design (no-regression): `test_a_real_provides_and_evidence_node_are_fine`, `test_empty_provides_and_null_evidence_position_add_no_ghost_violation[*]`, and the `naive`, `hipporag` and four corpus legs of the per-wiring test.

`databasise/tests/seam/test_evidence_position.py`
- `::test_a_local_arm_query_returns_non_empty_evidence_that_resolves`: `AssertionError: assert 0 > 0` (`envelope.evidence == []`)
- `::test_assemble_emits_the_chunks_it_put_into_the_context`: `AssertionError: assert None == [{'id': 'c1', 'score': 0.5}]` (no `items` key)
- `::test_assemble_items_follow_the_context_order_and_carry_no_invented_score`: `AssertionError: assert None == [{'id': 'z', 'score': None}, ...]`
- `::test_bypass_declares_no_evidence_position`: `AssertionError: assert {'node': 'chunk-vector', 'namespace': 'chunks'} is None`
- `::test_the_kg_arms_point_evidence_at_assemble[global|hybrid]`: `AssertionError: assert {'node': 'chunk-vector', 'namespace': 'chunks'} == {'node': 'assemble', 'namespace': 'chunks'}`
- `::test_a_bypass_query_returns_no_evidence_without_error` and `::test_naive_keeps_the_chunk_vector_as_evidence` pass at the base (bypass already minted `[]` because the missing node reads as no output; naive is unchanged). They pin the D-02 "bypass returns [] without error" and "naive keeps chunk-vector" clauses against regression.

Edge rows: ordering is pinned by the `items_follow_the_context_order` test; adjacency (a provides/evidence entry naming a node only base.json has) by `test_a_node_removed_by_a_patch_but_still_named_is_a_violation`; empty by the empty/null/absent test; encoding by the real-driver resolve leg. Idempotency and concurrency stay `backstop`.

## Deviations from Plan

None - plan executed as written. The extra direct-assertion leg in the per-wiring test (above) is a test-design choice to give the row a base failure, not a source deviation.

## Notes

- `ruff format --check` reports reformatting for the touched files; the repo does not enforce it (lefthook ran clean), so no reformat was applied to avoid unrelated churn.
- The patch edits shift the four arms' `wiring_instance_hash`; 13-12's D-24 annotation covers them (per the plan).

## Known Stubs

None.

## Threat Flags

None. T-13-12 is mitigated by the ghost check (the engine already refuses a non-ok report via `_refuse_unparseable`).

## Self-Check: PASSED

- 6fe2918 and c5c46cc are ancestors of HEAD; all listed files exist.
