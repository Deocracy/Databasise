---
phase: 16-gui-connectors
plan: 02
subsystem: testing
tags: [refusal-catalogue, selector-resolution, generated-artefact, sync-test]
requires: []
provides:
  - "docs/gui/refusals.json: 50 runtime refusal types with module, attribute_keys, http_status"
  - "databasise/tests/fixtures/selector-resolution.json: 29 resolution rows plus a reachable map over the six arms"
  - "DATABASISE_REGENERATE=1 flag read by both sync tests"
affects: [16-03, 17]
status: complete
commits: 4
plan_head_before: 3e1b6188d24a31a422cdb8a2a856f92816b4ecb0
plan_head_after: e56634413ce71f44f5000ac23fa1ea42e2136585
actuals:
  tokens: 6300
  tasks: 2
  commits: 4
tech-stack:
  added: []
  patterns:
    - "generated JSON written only by its sync test under DATABASISE_REGENERATE=1; pinned facts asserted on computed rows before any write"
key-files:
  created:
    - docs/gui/refusals.json
    - databasise/tests/seam/test_refusal_catalogue_file.py
    - databasise/tests/fixtures/selector-resolution.json
    - databasise/tests/seam/test_selector_resolution_fixture.py
  modified: []
key-decisions:
  - "Pinned selector facts are asserted before the regenerate write, so a regeneration cannot record a wrong state"
  - "The not-yet-existing file is asserted first when not regenerating, so the RED state is a plain AssertionError"
requirements-completed: [CONN-02, CONN-03]
---

# Phase 16 Plan 02: Refusal catalogue and selector-resolution fixture Summary

`docs/gui/refusals.json` (50 refusal types) and `databasise/tests/fixtures/selector-resolution.json` (29 rows, six reachable arms) are committed, each held in sync with the code by a test that rebuilds it from `_REFUSAL_FACTORIES`/`refusal_body`/`_status_for` and from `resolve_selector`.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 (RED) | cdfbf0b | `test_refusal_catalogue_file.py`, committed failing (file absent) |
| 1 (GREEN) | 9388d04 | `docs/gui/refusals.json` generated |
| 2 (RED) | 0d61503 | `test_selector_resolution_fixture.py`, committed failing (file absent) |
| 2 (GREEN) | e566344 | `selector-resolution.json` generated |

Tracer gate: Task 1 verify set (4 files, 139 passed) re-run before Task 2 started.

## CONN row test node ids and fail-first evidence

| Row | Intended test_ref | Fail-first |
|-----|-------------------|------------|
| CONN-02 | `databasise/tests/seam/test_refusal_catalogue_file.py::test_the_refusal_catalogue_file_matches_the_code` | At cdfbf0b (test present, file absent): `AssertionError: /home/chris/coding/Databasise-2.0-fully-agnostic-system/docs/gui/refusals.json is missing; regenerate with: DATABASISE_REGENERATE=1 ...` (`assert False` where `is_file()`). Use `record-fail --at cdfbf0b`. |
| CONN-03 | `databasise/tests/seam/test_selector_resolution_fixture.py::test_every_fixture_row_resolves_as_recorded` | At 0d61503 (test present, file absent): `AssertionError: .../databasise/tests/fixtures/selector-resolution.json is missing; regenerate with: ...`. Use `record-fail --at 0d61503`. |

Both nodes exist only from their RED commit onward (neither file is in the phase base), and both pass at their GREEN commit and at HEAD.

## Generated content checked

- `refusals.json`: 50 entries; `UnknownTraceReferenceError` 404, `StoreBusyError` 409, `ForeignEngineRefusalError` 502.
- `selector-resolution.json`: default -> naive (7); `[]` -> `EmptyCapabilitySelectorError`; `reads_vector:entities` -> local (15); `reads_vector:relationships` -> global (15); both -> hybrid (17); every alias row resolves to its own arm; 17 Effect rows, 11 of them `UnsatisfiableSelectorError`; harness `hotpotqa` -> `UnsatisfiableSelectorError`.
- `reachable`: naive true, bypass true, hybrid true, local true, global true, hipporag true.

## Test results

- Task 1 verify set (4 files): 139 passed.
- Task 2 verify set (5 files, includes protected `test_selector_reachability.py`, `test_capability_effects.py`, `test_empty_capability_selector.py`): 36 passed.
- Phase guard suite (the 17 files in 16-01's verification block) plus the two new test files: 283 passed.
- No protected test failed; none was edited. No product module was edited.
- Full offline gate (`check_offline_suite.py`) not run in this plan.

## Deviations from Plan

- Each task was split into a RED test commit and a GREEN generated-file commit (4 commits instead of 2), so each row node has a committed failing state for `record-fail --at`. No scope change.
- The pinned-facts assertions live inside the single row test (no second test node), ordered before the regenerate write.

## Known Stubs

None.

## Threat Flags

None. T-16-04 (catalogue drift) and T-16-05 (wrong-state regeneration) are mitigated by the two sync tests.

## Self-Check: PASSED

Files found: `docs/gui/refusals.json`, `databasise/tests/seam/test_refusal_catalogue_file.py`, `databasise/tests/fixtures/selector-resolution.json`, `databasise/tests/seam/test_selector_resolution_fixture.py`. Commits cdfbf0b, 9388d04, 0d61503, e566344 are ancestors of HEAD.
