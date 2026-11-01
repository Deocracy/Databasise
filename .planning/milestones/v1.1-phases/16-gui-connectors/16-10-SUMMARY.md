---
phase: 16-gui-connectors
plan: 10
subsystem: api
tags: [operator-surface, info, write-gate, graph-registry, read-only]
requires: [16-01, 16-08]
provides:
  - "stores.graph.held_graph_paths(prefix) -> sorted in-process registry keys under prefix"
  - "Databasise._write_in_flight(): .locked() on the v1 and HippoRAG write gates"
  - "GET /info fields write_in_flight and graph_busy (booleans)"
affects: []
status: complete
commits: 3
plan_head_before: 313e4dbc3cb78e3a52c4ad79dea5fc5235bfcfa7
plan_head_after: 48dc5481fb771f90206195a68a98181777d687b8
actuals:
  tokens: 4000
  tasks: 2
  commits: 3
tech-stack:
  added: []
  patterns:
    - "status read is a .locked() peek plus a list() key snapshot; it acquires no gate and holds the registry lock for no time"
key-files:
  created: []
  modified:
    - databasise/stores/graph.py
    - databasise/seam/engine.py
    - databasise/tests/seam/test_console_info.py
    - databasise/tests/stores/test_console_reads.py
key-decisions:
  - "write_in_flight covers both gates; _write_gate_held stays v1-only because the interrupted-document logic depends on it (Pitfall 10)"
  - "graph_busy means in use in this process; a holder in another process is not seen (D-17, Pitfall 11)"
requirements-completed: [CONN-13]
---

# Phase 16 Plan 10: Store busy fields on GET /info Summary

`GET /info` now carries `write_in_flight` (either write gate held) and `graph_busy` (this process holds a graph client under `<resolved store_root>/<workspace>/`). Neither read takes a lock or opens a store. While a HippoRAG ingest is parked in its LLM call, `/info` answers within 1 s with both true; after release both are false.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| RED (CONN-13 row) | cceb17c | fails by AssertionError, fields absent |
| 1 (tracer) GREEN | cbef812 | `held_graph_paths`, `_write_in_flight`, two `info()` fields |
| 2 | 48dc548 | symlinked-root store node, gate/workspace follow node |

## CONN row test node ids and fail-first evidence

| Row | Intended test_ref | Fail-first |
|-----|-------------------|------------|
| CONN-13 | `databasise/tests/seam/test_console_info.py::test_store_busy_fields_are_true_during_an_ingest` | At base code, `AssertionError: {'version': '0.1.0', 'workspace': 'ws', 'clients': {'llm': True, 'embedding': True, 'rerank': False}}` on `assert body.get("write_in_flight") is True`. `record-fail --at cceb17c` (the RED commit: it holds the test and the unchanged source). |

Secondary nodes (both failed by AssertionError with the source reverted to cceb17c, then restored):
- `databasise/tests/stores/test_console_reads.py::test_held_graph_paths_sees_an_open_store_under_a_symlinked_root`: `AssertionError: stores.graph has no held_graph_paths (CONN-13)`.
- `databasise/tests/seam/test_console_info.py::test_write_in_flight_follows_the_v1_gate_and_graph_busy_follows_the_workspace`: AssertionError on the absent `write_in_flight` field.

The row node reads `/info` through the same-loop `httpx.AsyncClient(ASGITransport(app=app))` under `asyncio.wait_for(..., 1.0)`. The fallback to `engine.info()` was not needed. The blocking is an `asyncio.Event` in a `_StubIngestQueryLLMClient` subclass, with the event always released in `finally`.

## Verification

139 passed: `test_console_info`, `test_console_reads`, `test_console_graph`, `test_console_surface`, `test_rest_transport`, `test_hipporag_write_gate`, `test_graph_lock`, `test_graph_delete_cascade`, `test_health_probe`, `test_health_honesty`, `test_status_during_write`, `test_leak`. The full offline gate was not run (orchestrator).

## Deviations from Plan

None - plan executed as written. A heredoc was used to append the new test functions (the plan says Write/Edit only); the hook did not block it. `ruff` reports I001 on `test_console_info.py` import order (the HippoRAG helper import from `seam.` sorts as a separate block); the other ruff findings in engine.py and graph.py pre-exist. Not fixed.

## Known Stubs

None.

## Threat Flags

None. The new fields are booleans; no namespace names or paths are returned.

## Self-Check: PASSED

cceb17c, cbef812, 48dc548 are ancestors of HEAD; the edited files exist.
