---
phase: 17-gui-mockup
plan: 12
subsystem: ui
tags: [gui, mockup, graph, vector, playwright, needs-backend]
requires:
  - phase: 17-05
    provides: "GUI-11 Wave 0 checks and the graph contract pins"
  - phase: 17-08
    provides: "Evidence Inspector open-evidence handler"
  - phase: 17-11
    provides: "Console, wireErrors/renderError, Picker, wrapper conventions"
provides:
  - "Graph/vector browser screen: selector, count tiles, node list, node detail with edges, chunk browser, store-busy and unknown-node states, planned list"
  - "fixtures/graph.json: lightrag, hipporag, store-busy, unknown-node"
  - "Every GAP-ROUTES.json route string now appears as a data-needs-backend value (GUI-03 row node)"
affects: [17-13]
key-files:
  created:
    - mockups/src/js/70-graph.js
    - mockups/src/css/70-graph.css
    - mockups/src/fixtures/graph.json
  modified:
    - mockups/src/screens/graph.html
    - mockups/operator-console.html
    - docs/gui/MOCK-IDS.json
key-decisions:
  - "Edge rows for nodes without explicit fixture rows are derived from the node degree at runtime; only ACME CORP carries explicit edges and attributes"
  - "Second fixture page of nodes and chunks has next_offset null (last fixture page) while total stays 214 / 96, as in the corpus screen"
  - "Retry request reloads the currently selected family (equals lightrag in every tested flow)"
requirements-completed: []
duration: one executor session
completed: 2026-10-30
status: complete
commits: 1
plan_head_before: 0ab653b8b0a0aac5e433d7ada633123218a25f14
plan_head_after: a9a3a24a351d3a1b7d877aff9b123459f8310d7b
actuals:
  tokens: 9000
  tasks: 3
  commits: 1
---

# Phase 17 Plan 12: Graph/vector browser Summary

The last screen is built: a selector-driven graph browser with a paged node list (prefix filter, degree column), node detail with paged incident edges as references, attributes only after `Load attributes` (D-05), a chunk browser that opens the Evidence Inspector, count tiles, a HippoRAG graph fixture, store-busy and unknown-node refusal states, and a text-only planned list. Every one of the 67 GUI row nodes passes.

Requirements GUI-11 and GUI-03 are NOT marked complete here; the orchestrator records the ledger rows.

## What was built

- `screens/graph.html`: wrappers `POST /graph/nodes` (selector + family, node list; operator), `POST /graph/node` (node panel and edges; operator), `POST /graph/node/attrs` (Load attributes; needs backend, nested in the node wrapper), `POST /chunks` (operator), `POST /stores/counts` (needs backend). The two refusal banners sit in their own operator wrappers and are shown by toggling the wrapper.
- `js/70-graph.js`: `GraphScreen` with `setState` (idle, populated, loading, empty), `loadFixture` (lightrag, hipporag, store-busy, unknown-node), `inject`; mock outcome select drives refusal/validation/server-failure/generic per call; `Picker.attach("graph", ...)` switches the family (`Reading: LightRAG graph` / `Reading: HippoRAG graph`); chunk Open emits `open-evidence` with namespace `chunks` or `hipporag-chunks`; text reaches the DOM through `textContent` only (`grep -c .innerHTML` prints 0).
- `fixtures/graph.json`, `css/70-graph.css` (node list left of the detail panel from 768 px, stacked below).
- `docs/gui/MOCK-IDS.json`: 87 ids added, none removed.

## Test results

`DATABASISE_REQUIRE_BROWSER=1 databasise/.venv/bin/python -m pytest -q -rA -p no:cacheprovider <67 literal node ids>`: `67 passed in 26.46s`, no skips. By file: smoke 1, build 1, GUI-01 4, GUI-02 3, GUI-03 5 (4 supporting + row), GUI-04 6, GUI-05 6, GUI-06 9 (catalogue, 6 screens including `[graph]`, branching, row), GUI-07 6, GUI-08 7, GUI-09 6, GUI-10 6, GUI-11 7 (including row `test_gui_11_graph_browser`). The 58 nodes that passed before still pass. `build.py --check` passes.

Beyond the tests, a scratch Playwright run (in the session scratchpad, not committed) confirmed: selector to HippoRAG switches nodes, edges (cooccurrence / synonymy chips, weights) and chunk namespace (`hipporag-chunks` header in the Inspector); a prefix with no match, zero-edge and one-edge nodes, the empty and loading states, the lookup validation, the unknown-node mark, the refusal outcome to store-busy and Retry, and no horizontal scroll at 375 px; no page errors.

## Deviations from Plan

### Auto-fixed Issues

None needed. Judgment calls:

- One commit for all three tasks (the orchestrator allowed it) instead of three; the tracer gate was verified by running the whole GUI-11 file and then the full suite.
- Extra ids beyond the plan list, all inside the graph wrappers: `graph.nodes.panel`, `graph.chunks.panel`, `graph.{nodes,edges,chunks}.{loading,empty}`, `graph.node.loading`, `graph.node.lookup-error`, `graph.edges.page-size-error`, `graph.chunks.page-size-error`. The `<div class="state-view">`/`panel`/`banner` regions need an id under GUI-02, and the extra page-size inputs need an error element for `setFieldError`.
- Banners `graph.state.store-busy` and `graph.state.unknown-node` carry class `banner state-view` (the GUI-02 marker rule for `*.state.*` ids).
- The empty chunk list heading `No chunks to show` and the edge heading `No edges to show` are not in the UI-SPEC Copywriting Contract (it lists only the graph nodes empty state); worded to match its style.
- Retry reloads the selected family rather than hard-coding `lightrag`.

## Test/plan conflicts

None. No test file was edited; no assertion conflicted with the plan or UI-SPEC.

## Hook blocks met

- BAK check-edit-guard blocked `git ls-files databasise/tests/gui | xargs wc -l` and `pytest --collect-only` over `test_gui_05_compare.py` ("is a check, harness or helper file; only the owner can allow this edit (grant-check-edit)"). Not worked around; node ids were taken by reading the files with the Read tool instead.

## Known Stubs

None that block the plan goal. Fixture pages are fixed size (8 nodes, 8 chunks, 6 edges) and ignore the page-size input beyond validating it; the second fixture page is the last (`next_offset: null`) although the totals (214, 96) imply more. Both mirror the corpus screen and are fixture-only mock behaviour.

## Threat Flags

None. T-17-18: `textContent` only, `.innerHTML` count 0. T-17-19: attributes appear only through the explicit, badged `POST /graph/node/attrs` action.

## Self-Check: PASSED

- Created files exist: `mockups/src/js/70-graph.js`, `mockups/src/css/70-graph.css`, `mockups/src/fixtures/graph.json`.
- Commit `a9a3a24` is an ancestor of HEAD; `git rev-list --count 0ab653b..HEAD` was 1 before this SUMMARY commit.
