---
phase: 10-stores-locking-data-integrity
plan: 09
subsystem: stores-data-integrity
tags: [graph-cascade, auto-create-endpoint, kv-buffer-isolation, d-10, stor-10, stor-11]
status: complete

requires: ["10-07"]
provides:
  - "databasise/stores/graph.py: delete_node cascades (buffer at once, disk edges marked removed, :rm edges before :rm nodes in _stage); _edge_hidden read filter; upsert_edge auto-creates a missing endpoint with {}"
  - "databasise/stores/kv.py: deep copies on pending read and on upsert; is_empty honours pending deletes"
  - "databasise/tests/stores/test_graph_delete_cascade.py (new, 8 cases)"
  - "databasise/tests/stores/test_kv_buffer_isolation.py (new, 6 cases)"
affects: [HIPP-16 HippoRAG delete, CONN-11/12 GUI graph browser, 10-10]

actuals:
  tokens: 2469
  tasks: 2
  commits: 2
plan_head_before: e69feff5d7bdd6391974cffe40da4b8e2f2c9a78
plan_head_after: a9840508176e40a1c48facb9e49afd9413c932c5

tech-stack:
  added: []
  patterns:
    - "Delete marks the node's disk edges in _pending_edge_rms at delete time, so a later re-create of the node does not expose its old edges; the _stage cascade still runs for edges written after that query"

key-files:
  created:
    - databasise/tests/stores/test_graph_delete_cascade.py
    - databasise/tests/stores/test_kv_buffer_isolation.py
  modified:
    - databasise/stores/graph.py
    - databasise/stores/kv.py

key-decisions:
  - "delete_node runs one disk query and adds the node's committed incident edges to _pending_edge_rms. Without this, delete_node('x') then upsert_edge('x', 'z') clears x from _pending_node_rms, so the old disk edge x-y would come back and survive the flush. networkx drops it; so does this store now"
  - "upsert_edge checks each endpoint through has_node, which answers from the pending buffers before any query, so an endpoint already pending costs no disk lookup"

requirements-completed: [STOR-10, STOR-11]

duration: 16min
completed: 2026-10-17
---

# Phase 10 Plan 09: Graph delete cascade and KV buffer isolation Summary

Deleting a graph node now removes its incident edges in the buffer and on disk in the same transaction as the node, and an edge to a missing endpoint creates that node with `{}` (D-10). The KV store hands out and stores deep copies, and `is_empty` counts pending deletes (STOR-11).

## What was built

- `stores/graph.py`:
  - `delete_node` drops buffered incident edges at once. It also reads the node's disk edges and adds them to `_pending_edge_rms`.
  - `_stage` runs `?[src, tgt] := *edges{src, tgt}, src = $id or tgt = $id :rm edges {src, tgt}` before `:rm nodes` for each removed node, inside the one `multi_transact`. This also catches edges another instance wrote after the delete-time query.
  - `_edge_hidden(key)` hides a disk edge that is removed or that has an endpoint pending removal. `has_edge`, `get_edge`, `node_degree`, `get_node_edges` and `export_to_igraph` use it. The export's dangling-edge skip is kept.
  - `upsert_edge` calls `upsert_node(endpoint, {})` for any endpoint that `has_node` reports absent. That also clears a pending removal.
  - Degree is still counted in Python, and the code has no aggregation call.
  - The module docstring now has one paragraph on the cascade and auto-create semantics.
- `stores/kv.py`: `get_by_id` returns `copy.deepcopy` of a pending record, and `upsert` stores `copy.deepcopy(value)`. `is_empty` is False with any pending upsert. Otherwise it scans `SELECT id FROM kv` and returns False at the first id that is not pending deletion.

## TDD evidence

- Task 1, before the change: `7 failed, 1 passed`. Examples: `node_degree('y')` was 1 after the flushed delete (`assert 1 == 0`), the buffered edge survived (`{('x', 'y'): {}} == {}`), and auto-create did not happen (`assert False is True`). The one passing case was the no-lookup spy, which passes trivially when there is no endpoint check.
- Task 1, after: `32 passed` (cascade, test_graph, frozen bugs, bulk export). Then `412 passed, 3 deselected` (stores, parts_core, parity, test_hipporag_write_path).
- Task 2, before: `4 failed, 2 passed`. The read-mutation case gave `2 == 1`, the caller-mutation case `3 == 1`, the nested case `[1, 2, 3] == [1]`, and is_empty after deleting every row `False is True`. The two passing cases (another row survives; empty store or pending upsert) were already correct.
- Task 2, after: `103 passed` (tests/stores).

## Verification

- `pytest -q tests/stores tests/parts_core tests/parity`: 410 passed, 3 deselected.
- `tools/check_offline_suite.py`: 1732 passed, 1 skipped, 4 deselected under both `pytest -q -rs` and `python -m pytest -q -rs`.
- Parity: no fixture holds a dangling v1 edge. The parity tests pass unchanged, so auto-create added no node to an imported topology (the plan's flagged assumption did not occur).
- `tests/stores/test_graph_frozen_bugs.py` passes, so the code still has no aggregation call.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Re-creating a deleted node brought back its old disk edges**
- **Found during:** Task 1
- **Issue:** With only read filtering by `_pending_node_rms`, `delete_node('x')` followed by `upsert_edge('x', 'z')` clears x from the removal set. The disk edge x-y then becomes visible again, and the flush keeps it because the cascade only runs for nodes still in the removal set.
- **Fix:** `delete_node` adds the node's committed incident edges to `_pending_edge_rms`. A test assertion covers it: `has_edge('x', 'y')` is False and `node_degree('y')` is 0 after the re-create.
- **Files modified:** databasise/stores/graph.py, databasise/tests/stores/test_graph_delete_cascade.py
- **Commit:** 946fdbe

### Acceptance-criterion note

`grep -n "src = \$id or tgt = \$id" databasise/stores/graph.py` returns four lines, not one. Before this plan it already matched two lines (`node_degree` and `get_node_edges` use the same predicate). This plan adds the delete-time query and the cascade. The cascade line is the one the key link names.

## Known Stubs

None.

## Threat Flags

None. T-10-28 (dangling edges) is mitigated by the buffered and disk-side cascade and the reopen tests. T-10-29 (mutation by reference) is mitigated by the deep copies and the mutation tests.

## Self-Check: PASSED

- FOUND: databasise/tests/stores/test_graph_delete_cascade.py
- FOUND: databasise/tests/stores/test_kv_buffer_isolation.py
- FOUND: 946fdbe, a984050 (ancestors of HEAD)
