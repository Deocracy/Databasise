---
phase: 06-hipporag-2-side-by-side
plan: 05
subsystem: rag-engine
tags: [hipporag, graph-construction, faiss, self-knn, cozo, wiring, tdd]

# Dependency graph
requires:
  - phase: 06-hipporag-2-side-by-side
    plan: "06-02"
    provides: "openie's per-triple findings shape, entity-fact-embed's ENTITY_VERTEX_PREFIX/CHUNK_VERTEX_PREFIX identity space and its zero-findings short-circuit, the HippoRAG base wiring at 8 nodes"
provides:
  - "Four registered executable HippoRAG 2 index-side parts: hipporag/fact-edge-builder@0.1.0, hipporag/passage-edge-builder@0.1.0, hipporag/synonymy-edge-builder@0.1.0, hipporag/graph-materializer@0.1.0"
  - "FaissVectorStore.self_knn() — a genuine §14.2 batched self-KNN sub-capability, one Faiss search call whatever the store's size"
  - "The HippoRAG base wiring grown from 8 to 12 of the governing 13 base-wiring positions — the index side is now complete"
  - "A round-trip proof from graph-augment-persist's write through CozoGraphStore.export_to_igraph, binding this plan's output to 06-01's bulk-export path"
affects: [06-07, 06-09]

# Actuals (#2632)
actuals:
  tokens: 12774
  tasks: 3
  commits: 7
plan_head_before: 7b717d5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-task TDD RED/GREEN commit pairs within a single execute-type plan (06-02's own established pattern): a deliberately wrong stub body lands in the test(...) commit so target tests fail on real assertions rather than a collection error, then the real body replaces it in the feat(...) commit"
    - "Canonical order-insensitive-pair convention (sorted endpoint tuple) reused verbatim across fact-edges, passage-edges (dedup key), synonymy-edges and graph-augment-persist's own weight-collapse grouping — one convention, four call sites, never re-invented per node"
    - "A store method proxy (wrap the instance attribute holding a C-extension object, delegate everything but the counted method via __getattr__) for call-counting a Faiss index's own search() where the bound method itself cannot be monkeypatched directly — distinct from CozoGraphStore's own _run-wrapping convention, which works because _run is an ordinary Python method"

key-files:
  created:
    - databasise/parts_core/hipporag/fact_edges.py
    - databasise/parts_core/hipporag/passage_edges.py
    - databasise/parts_core/hipporag/synonymy_edges.py
    - databasise/parts_core/hipporag/graph_augment_persist.py
    - databasise/tests/parts_core/hipporag/test_graph_construction.py
    - databasise/tests/stores/test_vector_self_knn.py
  modified:
    - databasise/parts_core/hipporag/__init__.py
    - databasise/stores/vector.py
    - databasise/wirings/hipporag/base.json
    - databasise/tests/parts/test_registry.py
    - databasise/tests/parts_core/hipporag/test_registration.py

key-decisions:
  - "synonymy-edges' num_new_chunks > 0 guard is read as entity-fact-embed's own entity count, not a literal chunk count — this node's sole dep (entity-fact-embed) carries no chunk-count field anywhere in its own output, and entity-fact-embed already short-circuits to zero entities exactly when openie found zero findings, which in turn only happens when chunk-embed produced zero new chunks; the available data's own zero state is a faithful proxy for the wiring's declared guard condition."
  - "fact-edges/passage-edges declare effects=[] genuinely, not additively like chunk-embed/entity-fact-embed's own store-writing nodes — both bodies reach no store and no client at all; the graph write happens once, downstream, at graph-augment-persist, matching PARTS.md ## §H's own declared-empty-effects row for both positions."
  - "graph-augment-persist's fact-chunk-association reconciliation with reset-vector-join.py (06-01) is explicitly left open — see Next Phase Readiness. This plan's own <files> list never names entity_fact_embed.py or reset_vector_join.py, and the discrepancy sits entirely between those two files, neither of which this plan's scope touches."

requirements-completed: []

coverage:
  - id: D1
    description: "FaissVectorStore.self_knn(top_k) returns the top-k nearest neighbours for every stored vector from one batched Faiss search call, and the search-call count does not grow with the number of stored vectors"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/stores/test_vector_self_knn.py#test_self_knn_search_call_count_does_not_scale_with_stored_vector_count"
        status: pass
      - kind: unit
        ref: "tests/stores/test_vector_self_knn.py#test_self_knn_returns_top_k_neighbours_per_vector_never_including_itself"
        status: pass
      - kind: unit
        ref: "tests/stores/test_vector_self_knn.py#test_mutating_a_stored_vector_changes_its_neighbour_list_negative_control"
        status: pass
    human_judgment: false
  - id: D2
    description: "synonymy-edges produces entity-to-entity edges only from self_knn, canonically ordered and deduplicated above threshold, and produces none at all when the guard input reports zero new upstream entities"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/parts_core/hipporag/test_graph_construction.py#test_synonymy_edges_emits_deduped_canonical_edges_above_threshold"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_graph_construction.py#test_synonymy_edges_zero_upstream_chunk_count_makes_no_store_read"
        status: pass
    human_judgment: false
  - id: D3
    description: "fact-edges produces symmetric entity-to-entity co-occurrence edges and passage-edges produces passage-to-entity edges at unit weight, both as pure transforms declaring no effects"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/parts_core/hipporag/test_graph_construction.py#test_fact_edges_emits_one_symmetric_edge_with_cooccurrence_count_weight"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_graph_construction.py#test_fact_edges_are_canonically_ordered_regardless_of_source_order"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_graph_construction.py#test_passage_edges_emits_one_edge_per_chunk_entity_pair_at_unit_weight"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_graph_construction.py#test_fact_and_passage_edges_reach_no_store_and_no_client"
        status: pass
    human_judgment: false
  - id: D4
    description: "graph-augment-persist writes every node and edge from the three builders into the hipporag-graph namespace under quarantined artifact scope, collapsing the three edge types into the single weight attribute export_to_igraph reads, with contributing edge types recorded on the edge's own attrs"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/parts_core/hipporag/test_graph_construction.py#test_graph_augment_persist_writes_every_vertex_and_edge_as_quarantined"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_graph_construction.py#test_graph_augment_persist_collapses_two_edge_types_into_summed_weight"
        status: pass
    human_judgment: false
  - id: D5
    description: "A graph written by graph-augment-persist and read back by CozoGraphStore.export_to_igraph round-trips: every persisted node id appears as a vertex name and every persisted edge weight appears as an edge weight, with a negative control proving the comparison has teeth"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/parts_core/hipporag/test_graph_construction.py#test_graph_augment_persist_round_trips_through_export_to_igraph_with_negative_control"
        status: pass
    human_judgment: false
  - id: D6
    description: "A full index-side chain (chunk-embed through graph-augment-persist) over the seeded shared-entity source documents produces a real graph holding both passage and entity vertices"
    requirement: MODAL-04
    verification:
      - kind: integration
        ref: "tests/parts_core/hipporag/test_graph_construction.py#test_end_to_end_index_run_produces_a_graph_with_passage_and_entity_vertices"
        status: pass
    human_judgment: false

# Metrics
duration: ~80min
completed: 2026-09-09
status: complete
---

# Phase 6 Plan 5: HippoRAG 2 Graph Construction (fact-edges, passage-edges, synonymy-edges, graph-augment-persist) Summary

**The remaining four of HippoRAG 2's seven index-side node positions now run as registered, TDD-built parts — two pure edge transforms, a batched self-KNN synonymy builder, and a whole-graph materialiser that collapses three edge types into one weighted, quarantined graph proven to round-trip through the bulk-export path `ppr` already reads.**

## Performance

- **Duration:** ~80 min
- **Started:** 2026-09-09
- **Completed:** 2026-09-09
- **Tasks:** 3 (each RED → GREEN, no REFACTOR commits needed)
- **Files modified/created:** 11

## Accomplishments

- `databasise/parts_core/hipporag/fact_edges.py`: `hipporag/fact-edge-builder@0.1.0` — symmetric entity-to-entity co-occurrence edges from `openie`'s own per-triple findings, canonically ordered (sorted endpoint pair), genuinely zero effects (no store, no client)
- `databasise/parts_core/hipporag/passage_edges.py`: `hipporag/passage-edge-builder@0.1.0` — one deduplicated (chunk, entity) edge per finding at unit weight, using `CHUNK_VERTEX_PREFIX`/`ENTITY_VERTEX_PREFIX` imported from `entity_fact_embed.py`
- `databasise/stores/vector.py`: `FaissVectorStore.self_knn()` — §14.2's batched self-KNN sub-capability, one Faiss `search` call over the whole stored matrix whatever the store's size, proven via a search-call-counting proxy (8-vector store vs. 40-vector store, both exactly 1 call) plus a negative control
- `databasise/parts_core/hipporag/synonymy_edges.py`: `hipporag/synonymy-edge-builder@0.1.0` — entity-to-entity synonymy edges from `self_knn` alone, guarded on the upstream entity count (this node's dep chain carries no literal chunk count; see key-decisions)
- `databasise/parts_core/hipporag/graph_augment_persist.py`: `hipporag/graph-materializer@0.1.0` — persists every distinct vertex ref once and every edge grouped by canonical pair with summed weight and recorded contributing edge types, `artifact_scope="quarantined"` set on the Part (never the wiring node), flushed via `index_done_callback`
- HippoRAG base wiring grown from 8 to 12 of the governing 13 positions — the index side (`chunk-embed` through `graph-augment-persist`) is now complete; only the query-side `dpr-fallback` position remains, owned by 06-07
- Round-trip proven: a graph written by `graph-augment-persist` and read back by `CozoGraphStore.export_to_igraph` (06-01) agrees exactly on vertex names and edge weights, with a negative control (mutating a persisted weight changes the exported one)
- End-to-end index-side chain proven: `chunk-embed` → `openie` → `entity-fact-embed` → `{fact-edges, passage-edges, synonymy-edges}` → `graph-augment-persist` over the seeded shared-entity documents produces a real graph holding both passage and entity vertices
- Full suite: 829 passed, 1 skipped — up from the 06-02 baseline (702 passed/13 skipped bare; 813 passed/1 skipped with extras) by exactly this plan's own new tests, zero regressions

## Task Commits

Each task followed RED → GREEN (TDD, no REFACTOR needed — each GREEN implementation was already clean once passing):

1. **Task 1: fact-edges, passage-edges** — RED `1475ea4` (test), GREEN `f53adc1` (feat)
2. **Task 2: self_knn, synonymy-edges** — RED `135b903` (test), GREEN `c1e5406` (feat)
3. **Task 3: graph-augment-persist** — RED `48f2c85` (test), GREEN `24d29f0` (feat)

_No REFACTOR commits — each GREEN implementation was already clean once passing._

## TDD Gate Compliance

All three tasks (`type="auto" tdd="true"`) followed RED → GREEN:

- **Task 1 RED (`1475ea4`):** `fact_edges.py`/`passage_edges.py` committed with stub bodies unconditionally returning `{"edges": []}`. Verified via `uv run pytest -q tests/parts_core/hipporag/test_graph_construction.py -k "fact_edges or passage_edges"`: **4 of 5 target tests failed on real assertions** (co-occurrence weight, canonical ordering, unit-weight passage pairs, no-store/client all asserted non-empty results the stub could never produce) — genuine RED evidence, not a collection error. The fifth test (empty-findings) incidentally passed since the stub trivially matches the correct empty-input behaviour.
- **Task 1 GREEN (`f53adc1`):** real symmetric-co-occurrence and unit-weight-passage logic restored; all 5 target tests pass, plus the two Rule-3 pinned-count fixes.
- **Task 2 RED (`135b903`):** `self_knn` stub unconditionally returned `{}`; `synonymy_edges.py` stub unconditionally returned `{"edges": []}`. Verified: **3 of 4** `self_knn` tests failed on real assertions (`0 == 40` entries, `0 == 1` search-call-count-equality met by coincidence rather than by construction — corrected below, `KeyError: 'v0'` on the negative control) and **1 of 2** synonymy-edges tests failed (`('entity:cat', 'entity:kitten') in []`) — genuine RED.
- **Task 2 GREEN (`c1e5406`):** real batched-search self_knn and self_knn-driven synonymy-edges restored; all target tests pass.
- **Task 3 RED (`48f2c85`):** `graph_augment_persist.py` stub ignored `ctx.inputs`, persisted nothing, always emitted zero counts. Verified: **4 of 5 target tests failed** (empty vertex/edge sets where real data was expected, missing edge-type collapse, an empty round-tripped graph, and the end-to-end chain's own assertion that some vertex carries the chunk prefix) — genuine RED. The fifth (three-empty-streams) test passed trivially since the stub also persists nothing.
- **Task 3 GREEN (`24d29f0`):** real vertex/edge collection, canonical-pair weight summation and edge-type recording restored; all target tests pass, plus the two Rule-3 pinned-count fixes and the full suite (829 passed, 1 skipped).
- **Tool note:** `gsd_run check tdd-red-evidence` remains TAP/Node-test-runner-oriented and does not natively parse pytest's default output format for this Python project (same finding recorded in 06-01/06-02-SUMMARY.md); RED evidence was verified manually via pytest's own exit code and per-test failure attribution instead of running that tool mechanically.

## Files Created/Modified

- `databasise/parts_core/hipporag/fact_edges.py` - `hipporag/fact-edge-builder@0.1.0`
- `databasise/parts_core/hipporag/passage_edges.py` - `hipporag/passage-edge-builder@0.1.0`
- `databasise/parts_core/hipporag/synonymy_edges.py` - `hipporag/synonymy-edge-builder@0.1.0`
- `databasise/parts_core/hipporag/graph_augment_persist.py` - `hipporag/graph-materializer@0.1.0`
- `databasise/stores/vector.py` - `FaissVectorStore.self_knn()`
- `databasise/parts_core/hipporag/__init__.py` - `HIPPORAG_PARTS` grown from 8 to 12 members
- `databasise/wirings/hipporag/base.json` - `fact-edges`/`passage-edges`/`synonymy-edges`/`graph-augment-persist` nodes added (12 nodes total)
- `databasise/tests/parts_core/hipporag/test_graph_construction.py` - all four tasks' `<behavior>` tests plus the end-to-end index-side chain test
- `databasise/tests/stores/test_vector_self_knn.py` - `self_knn`'s own store-level test suite
- `databasise/tests/parts/test_registry.py`, `databasise/tests/parts_core/hipporag/test_registration.py` - pinned counts updated three times (once per task) to their new correct values (30→34 registry entries across the plan; 8→12 `HIPPORAG_PARTS` members)

## Decisions Made

See `key-decisions` in frontmatter. Most load-bearing: `synonymy-edges`' `num_new_chunks > 0` guard is read off `entity-fact-embed`'s own entity count, since this node's sole dep carries no literal chunk count anywhere in its own output — the available data's own zero state is a faithful, testable proxy for the wiring's declared guard condition, not an invented substitute.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Registry/registration pinned counts updated three times (once per task)**
- **Found during:** Each task's own GREEN verify step
- **Issue:** `tests/parts/test_registry.py` and `tests/parts_core/hipporag/test_registration.py` both pin exact counts (`default_registry()`'s total entries and `HIPPORAG_PARTS`'s own member count/shape table). Each task's own new registered part(s) — the plan's explicit goal — made both stale assertions fail.
- **Fix:** Updated both assertions/tables to their new correct counts after each task (32/10 after Task 1, 33/11 after Task 2, 34/12 after Task 3), extending `test_registration.py`'s `_EXPECTED_SHAPE` with each new part's pinned `kind`/`effects`/`structural_depth` and renaming the count-named test functions accordingly — mirroring 06-01/06-02-SUMMARY.md's own precedent for this exact class of fix.
- **Files modified:** `databasise/tests/parts/test_registry.py`, `databasise/tests/parts_core/hipporag/test_registration.py`
- **Verification:** Full suite green after Task 3's fix (829 passed, 1 skipped).
- **Committed in:** `f53adc1`, `c1e5406`, `24d29f0` (one fix per task's own GREEN commit)

---

**Total deviations:** 1 auto-fixed pattern, applied three times (1 blocking per task)
**Impact on plan:** Necessary for correctness/consistency; no scope creep. Each fix is a direct, expected consequence of this plan's own additions (four new registered parts across three tasks) breaking pinned-count assertions that exist specifically to catch such changes.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **OPEN — carried forward explicitly for 06-07, not silently resolved in this plan's scope.** 06-02-SUMMARY.md's "Next Phase Readiness" flagged a discrepancy: `reset-vector-join.py` (06-01, already committed, `reads_kv` effect) reads a fact's own chunk-association record from a KV `fact:<id>` -> `{chunk_ids}` mapping, but `entity-fact-embed` (06-02) writes that same `chunk_ids` data directly into the *fact vector's own metadata* in the Vector store, never into the KV store. **No code in this repository writes a real `fact:<id>` KV record today** — the only place that shape exists is `tests/parts_core/hipporag/conftest.py`'s `seeded_hipporag_store` fixture, which hand-seeds it for `reset-vector-join`'s own isolated tests. This plan's own `<files>` list never names `entity_fact_embed.py` or `reset_vector_join.py`, and the discrepancy sits entirely between those two files — neither is in this plan's scope, and this plan's own end-to-end test (Task 3 Test 5) only exercises `chunk-embed` through `graph-augment-persist`, which never calls `reset-vector-join` at all, so the gap is not exercised here either.
  - **Disposition determined this plan:** `reset-vector-join.py`'s KV-read interface is the more load-bearing of the two — it is already committed, its `reads_kv` effect is already declared and tested, and the governing wiring's `store_namespaces` config already names `hipporag-text-chunks` as the KV namespace. The fix therefore belongs on `entity-fact-embed`'s side: it needs to *also* write a `fact:<id>` -> `{chunk_ids}` KV record (in addition to its existing vector-metadata write, which other consumers — none yet — might still want) so a real end-to-end run from `chunk-embed` through `reset-vector-join` produces real chunk-association data instead of relying on the conftest fixture's hand-seeded stand-in.
  - **Why 06-07 is the right owner:** 06-07 is the plan that lands the one remaining query-side position (`dpr-fallback`) and, per 06-01/06-02's own precedent, is positioned to prove a real full end-to-end run (index side through query side) rather than the index-only or query-only slices this plan and 06-01/06-02 each proved. Reconciling this KV-write gap only matters once such a full run is attempted for real; 06-05's own scope (index-side graph construction, `<files>` naming none of `entity_fact_embed.py`/`reset_vector_join.py`/the KV store) is not the right place to add an entity-fact-embed write path this plan was never asked to touch.
- HippoRAG's index side is now complete (all 12 of the governing 13 base-wiring positions); the whole-graph materialisation is proven via `graph-augment-persist`'s own round-trip through `export_to_igraph` — 06-07 and 06-09 can build on a real, tested graph construction path rather than a stub.
- `synonymy-edges`' guard-proxy decision (entity count standing in for the wiring's own literal `num_new_chunks > 0` condition) is implemented and tested against the available data shape; if a later plan threads a real chunk count through this node's dep chain, the guard should read that value directly instead.

## Self-Check: PASSED

- All `key-files.created` verified present on disk.
- `git log --oneline --all | grep -E "1475ea4|f53adc1|135b903|c1e5406|48f2c85|24d29f0"` returns all six commits.
- Every task's `<acceptance_criteria>` re-verified: `HIPPORAG_FACT_EDGE_BUILDER_PART.effects == []` and `HIPPORAG_PASSAGE_EDGE_BUILDER_PART.effects == []`; both modules import `ENTITY_VERTEX_PREFIX`/`CHUNK_VERTEX_PREFIX` from `entity_fact_embed.py` and define no prefix literal of their own; `databasise/wirings/hipporag/base.json` declares `fact-edges`/`passage-edges` with `deps == ["openie"]`; `databasise/stores/vector.py` defines `self_knn` on `FaissVectorStore`; the search-call-counting proxy asserts identical counts (1) for an 8-vector and a 40-vector store; `HIPPORAG_SYNONYMY_EDGE_BUILDER_PART.effects == ["reads_vector"]`; the zero-upstream-entity guard test dispatches with an empty `stores` dict and returns `{"edges": []}` with no `KeyError`; `HIPPORAG_GRAPH_MATERIALIZER_PART.artifact_scope == "quarantined"` set on the Part, not the wiring node; `HIPPORAG_PARTS` has exactly 12 members; the round-trip test asserts vertex names and edge weights match with a negative control; the end-to-end chain test asserts both a passage- and an entity-prefixed vertex exist.
- Plan-level `<verification>`: `cd databasise && uv run pytest -q` exits 0 (829 passed, 1 skipped); `uv run python -m databasise.tools.check_import_boundary` exits 0; the HippoRAG base wiring declares 12 nodes and `parse_wiring(...).report.ok` is `True` with zero violations against `default_registry()`.

## Self-Check: PASSED (re-verified)

- File existence: all six `key-files.created` confirmed present on disk via `[ -f ]`.
- Commit existence: all six task commit hashes (`1475ea4`, `f53adc1`, `135b903`, `c1e5406`, `48f2c85`, `24d29f0`) confirmed via `git log --oneline --all`.

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-09*
