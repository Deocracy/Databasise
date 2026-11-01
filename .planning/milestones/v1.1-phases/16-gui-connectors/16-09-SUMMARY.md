---
phase: 16-gui-connectors
plan: 09
subsystem: api
tags: [fastapi, operator-surface, cozo, graph, refusals, read-only]
requires: [16-02, 16-08]
provides:
  - "probes.graph_node_edges(dir, node_id, limit, offset) -> (found, degree, edges)"
  - "Databasise.graph_node(selector, node_id, page)"
  - "POST /graph/node returning {id, degree, edges: [{src, tgt, edge_types, weight}], next_offset}"
  - "refusals.UnknownGraphNodeError(node_id) at 422, in __all__, with a _REFUSAL_FACTORIES entry"
  - "docs/gui/refusals.json regenerated with 51 types"
affects: [16-10]
status: complete
commits: 3
plan_head_before: a19508afd04c4bac67d0d75bf3c75dc99df3127b
plan_head_after: ea24a912939de61c59e6f34afcd17d4123987bea
actuals:
  tokens: 5000
  tasks: 2
  commits: 3
tech-stack:
  added: []
  patterns:
    - "graph read path follows graph_node_page: marker check under the registry lock, acquire, immutable run, release in finally; no CozoGraphStore"
    - "edge attrs are projected to an allowlist, never returned as a dict"
key-files:
  created: []
  modified:
    - databasise/stores/probes.py
    - databasise/seam/engine.py
    - databasise/seam/operator_rest.py
    - databasise/seam/refusals.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/seam/test_console_graph.py
    - docs/gui/refusals.json
key-decisions:
  - "UnknownGraphNodeError is 422, not in _NOT_FOUND_REFUSALS: 404 never discloses whether an internal identity exists (rest.py); the protected status test is unedited and green"
  - "A selected graph with no graph.cozo answers UnknownGraphNodeError (422), while /graph/nodes answers total 0 (16-RESEARCH correction 5); CONN-12 text is silent, so the orchestrator records it"
  - "Edges are exactly {src, tgt, edge_types, weight}; edge_types and weight are null when absent; no direction field (D-16)"
requirements-completed: [CONN-12]
---

# Phase 16 Plan 09: Graph node edges Summary

`POST /graph/node {selector, node_id, limit, offset}` returns `{id, degree, edges, next_offset}`. Each edge is `{src, tgt, edge_types, weight}` in stored lexicographic order (undirected, no direction field); `degree` is the unpaged incident-edge count with a self-loop counted once. LightRAG description text and HippoRAG `cooccurrence_by_chunk` never cross the seam. An unknown node id, or a selected graph with no `graph.cozo`, is `422 UnknownGraphNodeError(node_id)`; the refusal is in `refusals.__all__`, has its `_REFUSAL_FACTORIES` entry, and `docs/gui/refusals.json` now lists 51 types.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| RED (both tests) | aa62e1b | secondary node and CONN-12 row node, both failing by AssertionError |
| 1 (tracer) GREEN | ce5adee | `graph_node_edges`, `Databasise.graph_node`, `GraphNodeRequest`, POST /graph/node |
| 2 | ea24a91 | `UnknownGraphNodeError`, engine raise, `_REFUSAL_FACTORIES` entry, regenerated catalogue |

Tracer gate: the Task 1 verify set (secondary node, the 16-08 row node, `test_console_surface`, `test_graph_lock`, `test_graph_delete_cascade`) passed, 19 passed, before Task 2.

## CONN row test node ids and fail-first evidence

| Row | Intended test_ref | Fail-first |
|-----|-------------------|------------|
| CONN-12 | `databasise/tests/seam/test_console_graph.py::test_graph_node_edges_and_unknown_node_422` | At aa62e1b (test present, source unchanged): `AssertionError: refusals has no UnknownGraphNodeError (CONN-12)` / `assert None is not None`. Use `record-fail --at aa62e1b`. |
| CONN-12 (secondary) | `databasise/tests/seam/test_console_graph.py::test_graph_node_lists_a_known_nodes_edges_with_paging` | At aa62e1b: `AssertionError: (404, '{"detail":"Not Found"}')` / `assert 404 == 200`. Passes at ce5adee. |
| CONN-02 (contribution) | `databasise/tests/seam/test_refusal_catalogue_file.py::test_the_refusal_catalogue_file_matches_the_code` | After the class landed and before regeneration: `AssertionError: docs/gui/refusals.json differs from the code: missing=['UnknownGraphNodeError']`. Passes after `DATABASISE_REGENERATE=1`. |

The row test is a single node and still fails at ce5adee (after Task 1 code), as designed; it passes at ea24a91.

## Test results

- Task 2 verify set (7 files: `test_console_graph`, `test_refusal_catalogue_file`, `test_rest_transport`, `test_refusal_catalogue`, `test_refusal_status_codes`, `test_mcp_refusal_mapping`, `test_refusal_reachability`): 220 passed.
- Phase guard suite from 16-01 plus `test_console_graph`, `test_console_chunks`, `test_console_reads`, `test_refusal_catalogue_file`, `test_mcp_refusal_mapping`, `test_refusal_reachability`, `test_graph_delete_cascade` (24 files): 375 passed. This includes the protected `test_refusal_catalogue.py`, `test_refusal_status_codes.py`, `test_graph_lock.py` and the CONN-02 catalogue sync test, all unedited and green.
- `docs/gui/refusals.json`: 51 `"refusal_type"` entries; `UnknownGraphNodeError` is `http_status` 422 with `attribute_keys == ["node_id"]`.
- Full offline gate not run in this plan.

## Deviations from Plan

- The RED commit holds both Task 1's secondary node and Task 2's row node, so the row node has one committed failing state before any code commit; no protected file was edited.
- The new tests were appended to `test_console_graph.py` with a new helper `_build_graph_with_attrs`; 16-08's `_build_graph` and tests are untouched. The module gained one import line, `from databasise.seam import refusals, rest`.
- `UnknownGraphNodeError` is raised in `graph_node` after the busy/corruption mapping, so a held or corrupted graph still reports 409/502 and never 422.
- Commit trailer names Claude Sonnet 5.5 per the shared rules.

## Known Stubs

None.

## Threat Flags

None. T-16-23 (allowlist projection; the secret-text and `cooccurrence_by_chunk` asserts), T-16-24 (422, not in `_NOT_FOUND_REFUSALS`; protected status test green) and T-16-25 (named refusal for an absent graph and an absent id) are covered by the tests above.

## Self-Check: PASSED

Files found: the seven modified files above. Commits aa62e1b, ce5adee, ea24a91 are ancestors of HEAD.
