---
phase: 16-gui-connectors
plan: 08
subsystem: api
tags: [fastapi, operator-surface, cozo, graph, read-only]
requires: [16-04, 16-07]
provides:
  - "probes.graph_node_page(dir, prefix, limit, offset) and the probes._run_immutable query seam"
  - "Databasise._graph_dir(selector) and Databasise.graph_nodes(selector, prefix, page)"
  - "POST /graph/nodes returning {nodes: [{id, degree}], total, next_offset}"
affects: [16-09, 16-10]
status: complete
commits: 3
plan_head_before: 54f223316ff00e5178284bc4c848d56e9d6f48c6
plan_head_after: 975544e0033ba4ec5c269ec83cbfe560b63b34da
actuals:
  tokens: 5000
  tasks: 2
  commits: 3
tech-stack:
  added: []
  patterns:
    - "graph read path follows probe_graph: marker check under the registry lock, acquire, immutable run, release in finally; no CozoGraphStore"
key-files:
  created:
    - databasise/tests/seam/test_console_graph.py
  modified:
    - databasise/stores/probes.py
    - databasise/seam/engine.py
    - databasise/seam/operator_rest.py
    - databasise/tests/stores/test_console_reads.py
key-decisions:
  - "Graph namespace is the resolved wiring's store_namespaces.graph (default chunk_entity_relation), never a request field"
  - "Degrees: one batched is_in(src)/is_in(tgt) query per page, counted in Python over {src, tgt} so a self-loop counts once; total is len of the unpaged id query (no count(), Cozo #244)"
requirements-completed: [CONN-11]
---

# Phase 16 Plan 08: Graph node page Summary

`POST /graph/nodes {selector, prefix, limit, offset}` pages a modality's graph nodes with degrees, ordered by id and filtered by an id prefix. The read opens the graph the way `probe_graph` does (marker check, registry acquire, immutable run, release in `finally`) and never builds a `CozoGraphStore`, so it creates nothing. A graph held by another holder is `409 StoreBusyError(store_kind="graph")`; a directory without the RocksDB marker is `502 StoreCorrupted`.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 (RED) | 83fa107 | CONN-11 row test, failing (route absent) |
| 1 (GREEN) | d7bb30b | `graph_node_page`, `_run_immutable`, `GraphStoreCorruptedError`, `graph_nodes`, POST /graph/nodes |
| 2 | 975544e | `test_one_degree_query_per_page` and the corrupted-graph/OpenAPI node |

Tracer gate: the Task 1 verify set (7 files) passed, 35 passed, before Task 2. Degrees for the five-node graph are `[3, 2, 2, 2, 0]` (a3 has a self-loop and counts it once: 1 + 1).

## CONN row test node ids and fail-first evidence

| Row | Intended test_ref | Fail-first |
|-----|-------------------|------------|
| CONN-11 | `databasise/tests/seam/test_console_graph.py::test_graph_nodes_page_degrees_prefix_and_busy_409` | At 83fa107 (test present, source unchanged): `AssertionError: (404, '{"detail":"Not Found"}')` / `assert 404 == 200` at the first POST /graph/nodes. Use `record-fail --at 83fa107`. |
| CONN-11 (evidence) | `databasise/tests/stores/test_console_reads.py::test_one_degree_query_per_page` | With the three source files temporarily checked out at 83fa107 (not committed): `AssertionError: probes has no graph_node_page (CONN-11)`. Passing: one recorded script contains `is_in`; `CozoGraphStore.__init__` and `node_degree` are patched to raise and are never reached. |
| CONN-11 (evidence) | `databasise/tests/seam/test_console_graph.py::test_graph_nodes_corrupted_graph_is_a_named_fault_and_openapi_declares_409` | Same revert: `AssertionError: (404, ...)` / `assert 404 == 502`. |

The test file does not exist at the phase base, so 83fa107 is the earliest commit where the row node exists and fails.

## Test results

- Task 1 verify set: 35 passed. Task 2 verify set (`test_console_reads`, `test_console_graph`, `test_graph_lock`, `test_health_probe`): 20 passed.
- Phase guard suite plus `test_console_graph`, `test_console_chunks`, `test_console_surface`, `test_console_reads`, `test_graph_delete_cascade` and `test_build_stores_cleanup` (21 files): 300 passed, 0 errors. This includes the protected `test_graph_lock`, `test_store_refusal_status` and `test_refusal_status_codes`, all unedited and green.
- Full offline gate not run in this plan.

## Deviations from Plan

- Task 1 split into RED and GREEN commits so the row node has a committed failing state for `record-fail --at`, as 16-04, 16-06 and 16-07 did. Task 2's tests were committed after the code landed; their fail-first state was shown by a temporary checkout of the three source files at 83fa107, restored with `git checkout HEAD --` and never committed.
- The row test also asserts the no-graph case (`total 0`, `nodes []`, no `chunk_entity_relation` directory created), which the plan listed under the row's behavior.
- Commit trailer names Claude Sonnet 5.5 per the shared rules.
- Several Bash commands that named files under `databasise/tests` through shell variables, `find` or `ls` were refused by the BAK check-edit hook (a misread, no file was touched). Explicit literal paths worked.

## Known Stubs

None.

## Threat Flags

None. T-16-20 (409 on a held graph, release in `finally`), T-16-21 (marker check, no files created in a non-database directory, asserted) and T-16-22 (one degree query, spied) are covered by the tests above.

## Self-Check: PASSED

Files found: `databasise/tests/seam/test_console_graph.py`, `databasise/tests/stores/test_console_reads.py`, `databasise/stores/probes.py`, `databasise/seam/engine.py`, `databasise/seam/operator_rest.py`. Commits 83fa107, d7bb30b, 975544e are ancestors of HEAD.
