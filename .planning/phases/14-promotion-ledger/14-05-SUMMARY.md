---
phase: 14-promotion-ledger
plan: 05
subsystem: seam
tags: [trace-resolve, strict-bool, tenancy, rest, mcp, row-tests]
requires: []
provides:
  - databasise/tests/seam/test_trace_resolve_strict_flag.py (LEDG-09 row test)
affects: [14-08, 14-10]
status: complete
actuals:
  tokens: 5500
  tasks: 2
  commits: 2
plan_head_before: 557235c7b6e399782779b5dd8920213f64138a73
plan_head_after: ede74ea3a65042cc6d63e1b2f527124e8fb6a1f0
tech-stack:
  added: []
  patterns: ["StrictBool on request DTO fields", "row test self-contained: stubs copied, new names resolved at call time"]
key-files:
  created:
    - databasise/tests/seam/test_trace_resolve_strict_flag.py
  modified:
    - databasise/seam/rest.py
    - databasise/mcp/tools.py
    - databasise/seam/engine.py
    - docs/gui/API-INVENTORY.md
key-decisions:
  - "The trace flag is StrictBool on rest.TraceRequest and mcp.tools.ResolveToolArgs; no route or handler changed"
  - "Tenancy rule written as 'one store_root is one tenant' in the Databasise docstring and API-INVENTORY (D-10, G-35); no workspace key added to trace.db or ledger.db"
requirements-completed: [LEDG-09]
---

# Phase 14 Plan 05: Strict trace flag and tenancy rule Summary

The trace flag accepts only a JSON boolean on REST and MCP (a string, number or null is a validation error with no run record field), and "one store_root is one tenant" is stated in the engine docstring and API-INVENTORY.

## Tasks

| Task | Commit | Result |
|------|--------|--------|
| 1 tracer: StrictBool on both DTOs, REST and MCP row tests | 8a2a7c8 | 227 passed (row file, test_rest_transport, tests/mcp, test_run_record_identity, test_query_trace_nodes, test_stop_reason_leak) |
| 2: tenancy rule in the engine and API-INVENTORY | ede74ea | 246 passed (the above plus test_seam_doc_consistency) |

Protected trace-resolving tests (WIRE-12 `test_run_record_identity.py`, LRAG-19 `test_query_trace_nodes.py`, WIRE-03 `test_stop_reason_leak.py`) and `test_rest_transport.py` (AST proof) all pass unedited. `grep -c "one store_root is one tenant" docs/gui/API-INVENTORY.md` prints 2.

## Ledger rows

| Row | Intended test_ref | Tests |
|-----|-------------------|-------|
| LEDG-09 | `databasise/tests/seam/test_trace_resolve_strict_flag.py` | `::test_rest_refuses_a_non_boolean_flag[...]`, `::test_rest_still_honours_a_boolean_flag`, `::test_mcp_refuses_a_non_boolean_flag[...]`, `::test_mcp_still_honours_a_boolean_flag`, `::test_the_engine_states_the_tenancy_rule`, `::test_the_inventory_states_the_tenancy_rule` |

The refusal tests are parametrized over `'yes'`, `'true'`, `'1'`, `1`, `None`; use the file as `test_ref`.

## Fail-first evidence

Run in a scratch worktree at the phase base bb52fbb with only the row file copied in: `PYTHONPATH=<wt> databasise/.venv/bin/python -P -m pytest -q <wt>/databasise/tests/seam/test_trace_resolve_strict_flag.py -p no:cacheprovider --rootdir=<wt>`. The file collects there. 10 failed, 4 passed; every failure is an AssertionError:
- `test_rest_refuses_a_non_boolean_flag['yes']`: `AssertionError: ('yes', 200)` / `assert 200 == 422` (same for `'true'`, `'1'`, `1`)
- `test_mcp_refuses_a_non_boolean_flag['yes']`: `AssertionError: 'yes' was accepted as the trace flag` (same for `'true'`, `'1'`, `1`)
- `test_the_engine_states_the_tenancy_rule`: `AssertionError: assert 'one store_root is one tenant' in 'The consumer-facing async seam object (D-01). ...'`
- `test_the_inventory_states_the_tenancy_rule`: `AssertionError: assert 'one store_root is one tenant' in '# Databasise API Inventory for the Operator Console ...'`

The 4 that pass at the base: the `None` cases (pydantic `bool` already rejects null, so that edge was never lax) and the two "still honours a boolean" tests. The scratch worktree was removed.

## Deviations from Plan

None - plan executed as written. A bash-scripted append to the test file was blocked by the check-edit hook, so the documentation tests were added with the Edit tool instead; no content change.

## Known Stubs

None.

## Threat Flags

None.

## Self-Check: PASSED

- databasise/tests/seam/test_trace_resolve_strict_flag.py: FOUND
- 8a2a7c8, ede74ea: FOUND on main
- `debug: StrictBool` present in rest.py:214 and mcp/tools.py:200
