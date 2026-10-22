---
phase: 16-gui-connectors
plan: 03
subsystem: api
tags: [fastapi, operator-surface, wirings, selector-reachability]
requires: [16-01, 16-02]
provides:
  - "Databasise.wirings(): one row per all_wirings() arm with the eleven D-06 fields"
  - "GET /wirings on the operator surface"
affects: [16-04, 16-12]
status: complete
commits: 3
plan_head_before: eef54912f23ed05ab4c3793eebdc65c2cf53f0bd
plan_head_after: 069e10f6543eb9365fe2ce56823ec3eb40b660d9
actuals:
  tokens: 3000
  tasks: 2
  commits: 3
tech-stack:
  added: []
  patterns:
    - "reachability computed by resolving a capability selector built from each arm's own tokens"
key-files:
  created:
    - databasise/tests/seam/test_console_wirings.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/operator_rest.py
key-decisions:
  - "Rows keyed on name: the five LightRAG arms share one title"
  - "operator_rest.py never calls resolve_selector; the route body is `return await engine.wirings()`"
requirements-completed: [CONN-05]
---

# Phase 16 Plan 03: GET /wirings Summary

`Databasise.wirings()` and `GET /wirings` list the six arms (naive 7, bypass 1, hybrid 17, local 15, global 15, hipporag 14 nodes) with the default arm, default eligibility and a `reachable` flag computed from `resolve_selector` over each arm's own capability tokens. No provider is called.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 (RED) | e4e75df | row test, committed failing (route absent) |
| 1 (GREEN) | d0fc3fa | `Databasise.wirings()` in the Phase 16 block, GET /wirings, new imports `_capability_tokens`, `_is_default_eligible`, `all_wirings` |
| 2 | 069e10f | `test_reachable_is_computed_from_selector_resolution`, `test_an_injected_codebase_memory_mcp_part_adds_no_wirings_row` |

Tracer gate: Task 1 verify set (7 files, 49 passed) re-run before Task 2.

## CONN row test node id and fail-first evidence

| Row | Intended test_ref | Fail-first |
|-----|-------------------|------------|
| CONN-05 | `databasise/tests/seam/test_console_wirings.py::test_wirings_lists_six_reachable_rows_matching_the_fixture` | At e4e75df (test present, source unchanged): `AssertionError: (404, '{"detail":"Not Found"}')` / `assert 404 == 200`. Use `record-fail --at e4e75df`. The file does not exist at the phase base, so e4e75df is the earliest commit where the node exists and fails. |

The two Task 2 nodes also fail by the same AssertionError with `operator_rest.py` reverted to e4e75df (3 failed), and pass at HEAD. The monkeypatch node passing proves `reachable` is computed, not hard-coded.

## Probed rows (HEAD)

| name | node_count | reachable | is_default | default_eligible | provides |
|------|-----------|-----------|-----------|------------------|----------|
| naive | 7 | true | true | true | generate |
| bypass | 1 | true | false | true | generate |
| hybrid | 17 | true | false | true | generate |
| local | 15 | true | false | true | generate |
| global | 15 | true | false | true | generate |
| hipporag | 14 | true | false | false | qa |

`wiring_version` is `"1"` and `harnesses` is `[]` for all six. `reachable` equals the CONN-03 fixture's `reachable` map.

## Test results

- Task 1 verify set (7 files): 49 passed.
- Task 2 verify set (`test_console_wirings.py`, protected `test_refusal_reachability.py`): 10 passed.
- Phase guard suite (17 files from 16-01's verification block) plus `test_console_wirings.py`, `test_selector_resolution_fixture.py`, `test_refusal_catalogue_file.py`, `test_refusal_reachability.py`, `test_capability_effects.py`, `test_empty_capability_selector.py`, `test_docstring_currency.py`: 321 passed.
- No protected test failed; none was edited. `ruff check` clean on the two new/edited small files.
- Full offline gate (`check_offline_suite.py`) not run in this plan.

## Deviations from Plan

- Task 1 split into a RED test commit (e4e75df) and a GREEN code commit (d0fc3fa) so the row node has a committed failing state for `record-fail --at`. No scope change.
- The engine imports from `wirings.resolve` were reformatted from one line to a parenthesised list to add `all_wirings`.

## Known Stubs

None.

## Threat Flags

None. T-16-07 (hard-coded reachable list) is mitigated by the monkeypatch node; T-16-06 is accepted per D-02.

## Self-Check: PASSED

Files found: `databasise/tests/seam/test_console_wirings.py`, `databasise/seam/engine.py`, `databasise/seam/operator_rest.py`. Commits e4e75df, d0fc3fa, 069e10f are ancestors of HEAD.
