---
phase: 06-hipporag-2-side-by-side
plan: 01
subsystem: rag-engine
tags: [hipporag, igraph, prpack, personalized-pagerank, faiss, cozo, wiring, seam, modality-agnostic]

# Dependency graph
requires:
  - phase: 04-the-seam
    provides: "the §18 Databasise seam object (query/_execute), selector resolution, evidence minting"
  - phase: 05-opaque-side-admission
    provides: "opaque-part admission machinery, package-legitimacy checkpoint precedent (05-LEARNINGS.md)"
provides:
  - "Five executable HippoRAG 2 query-side parts (fact-score, fact-filter, reset-vector-join, ppr, assemble-result), all structural_depth=opaque"
  - "Two new store capabilities: CozoGraphStore.export_to_igraph() (§14.2 bulk-export, two Cozo queries regardless of graph size) and FaissVectorStore.score_all() (§14.2 exhaustive scoring, no top-k truncation)"
  - "databasise/wirings/hipporag/base.json — HippoRAG's 5-of-13-position base wiring, no arm patches"
  - "A modality-agnostic wiring pool (wirings/resolve.py's all_wirings()/load_wiring()/WIRING_NAMES) replacing the LightRAG-only five-arm candidate list in seam/selectors.py"
  - "Three seam couplings made declarative on each wiring's own top-level keys (consumes_query, evidence_position, store_namespaces), read by seam/engine.py and parity/run_arm.py instead of hardcoded LightRAG-only constants"
  - "A passing cross-modality run: one capability-selector query resolves to HippoRAG's own wiring and returns evidence from its own hipporag-chunks namespace, over stores disjoint from LightRAG's"
affects: [06-02, 06-03, 06-05, 06-07, 06-09]

# Actuals (#2632)
actuals:
  tokens: 23687
  tasks: 3
  commits: 4

# Tech tracking
tech-stack:
  added: [igraph>=0.11,<2.0, numpy>=1.24,<3.0]
  patterns:
    - "Declarative wiring-level seam couplings (consumes_query/evidence_position/store_namespaces) read off the resolved dict instead of hardcoded per-modality constants in seam/engine.py"
    - "Modality-agnostic candidate pool: all_wirings() generalizes the seam's selector resolution over every registered base wiring, not just LightRAG's five arms"
    - "§14.2 bulk-export/exhaustive-scoring store capabilities as a second method alongside the existing pointwise one (export_to_igraph beside get_node_edges; score_all beside query), never composed from the pointwise path in a loop"

key-files:
  created:
    - databasise/parts_core/hipporag/__init__.py
    - databasise/parts_core/hipporag/fact_score.py
    - databasise/parts_core/hipporag/fact_filter.py
    - databasise/parts_core/hipporag/reset_vector_join.py
    - databasise/parts_core/hipporag/ppr.py
    - databasise/parts_core/hipporag/assemble_result.py
    - databasise/wirings/hipporag/__init__.py
    - databasise/wirings/hipporag/base.json
    - databasise/tests/parts_core/hipporag/conftest.py
    - databasise/tests/parts_core/hipporag/test_registration.py
    - databasise/tests/parts_core/hipporag/test_ppr.py
    - databasise/tests/stores/test_graph_bulk_export.py
    - databasise/tests/stores/test_vector_score_all.py
    - databasise/tests/seam/test_cross_modality_run.py
    - databasise/tests/seam/test_store_isolation.py
    - .planning/phases/06-hipporag-2-side-by-side/06-CHECKPOINT-ANSWERS.md
  modified:
    - databasise/pyproject.toml
    - databasise/stores/graph.py
    - databasise/stores/vector.py
    - databasise/parts/registry.py
    - databasise/wirings/resolve.py
    - databasise/wirings/lightrag/base.json
    - databasise/seam/engine.py
    - databasise/seam/selectors.py
    - databasise/parity/run_arm.py
    - databasise/tests/parts/test_registry.py
    - databasise/tests/seam/test_leak.py
    - databasise/tests/test_embed_startup.py

key-decisions:
  - "igraph, numpy confirmed legitimate (checkpoint approved) — same sandbox missing-metadata blind spot documented in 05-LEARNINGS.md for mcp/python-multipart; both land in databasise/pyproject.toml's core [project.dependencies], not an optional extra, since HippoRAG 2 is a first-class modality of this milestone"
  - "ctx.stores['graph'] is a single, already-namespaced CozoGraphStore per run (not a MultiNamespaceVectorStore-style .select() handle) — ppr.py deviates from the plan's own literal action prose accordingly; the store_namespaces coupling's own stated architecture (only the vector store selects per-node by name) is the consistent reading"
  - "reset-vector-join's reads_kv effect is exercised via a per-fact chunk-association record (key fact:<id> -> {chunk_ids}) in the KV store — a 06-01-PLAN.md design decision for computing each surviving fact's own chunk-count divisor, not specified verbatim by the governing wiring document"
  - "Passage-node vertex identity uses a chunk: prefix convention (this plan's own fixture/part convention, not upstream HippoRAG's literal scheme) so ppr's readback partition is a simple, testable string check"

patterns-established:
  - "Wiring-level declarative seam coupling: a new cross-modality behavior (query injection, evidence position, store namespace) is added as a top-level wiring key read by the seam, with every existing wiring (including LightRAG's) updated to declare its own prior hardcoded value — byte-identical behavior preserved by construction, never by re-testing"

requirements-completed: [MODAL-04, MODAL-05]

coverage:
  - id: D1
    description: "HippoRAG 2's five-node query-side chain resolves through a capability selector and returns a §18.2 envelope with evidence from its own hipporag-chunks namespace"
    requirement: MODAL-04
    verification:
      - kind: integration
        ref: "tests/seam/test_cross_modality_run.py#test_hipporag_query_returns_evidence_from_its_own_chunks_namespace"
        status: pass
    human_judgment: false
  - id: D2
    description: "CozoGraphStore.export_to_igraph() issues exactly two Cozo queries regardless of graph size, with a round-tripping and negative-control proof"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/stores/test_graph_bulk_export.py#test_export_issues_exactly_two_cozo_queries_regardless_of_graph_size"
        status: pass
    human_judgment: false
  - id: D3
    description: "FaissVectorStore.score_all() returns every stored vector, never a top-k truncation, visibly distinct from query()"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/stores/test_vector_score_all.py#test_score_all_returns_one_entry_per_stored_vector_never_a_top_k_truncation"
        status: pass
    human_judgment: false
  - id: D4
    description: "HippoRAG's resolved graph/KV store directories are disjoint from LightRAG's on the same store_root/workspace; LightRAG's own directories are unchanged"
    requirement: MODAL-05
    verification:
      - kind: unit
        ref: "tests/seam/test_store_isolation.py#test_lightrags_own_directories_are_unchanged_from_before_this_plan"
        status: pass
      - kind: unit
        ref: "tests/seam/test_store_isolation.py#test_seeding_one_modalitys_graph_leaves_the_others_empty_cross_read_refusal"
        status: pass
    human_judgment: false
  - id: D5
    description: "Every HippoRAG part resolves opaque effective depth and none needs subprocess containment"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/parts_core/hipporag/test_registration.py#test_effective_depth_over_the_parsed_hipporag_wiring_is_opaque_at_every_node"
        status: pass
    human_judgment: false
  - id: D6
    description: "ppr's whole-graph PPR call is served by one native igraph/prpack call with the pinned argument shape, NaN/negative reset entries zeroed, readback partitioned to passage vertices only"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/parts_core/hipporag/test_ppr.py#test_nan_and_negative_reset_entries_are_zeroed_before_the_call"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_ppr.py#test_changing_damping_produces_a_different_score_vector_negative_control"
        status: pass
    human_judgment: false
  - id: D7
    description: "The wiring pool and seam couplings are generalized to be modality-agnostic without changing LightRAG's own observable behavior"
    requirement: MODAL-05
    verification:
      - kind: integration
        ref: "cd databasise && uv run pytest -q (688 passed, 13 skipped, full suite including every pre-existing LightRAG-arm/seam/parity test)"
        status: pass
    human_judgment: false

# Metrics
duration: continuation session (resumed from Task 1's checkpoint)
completed: 2026-09-09
status: complete
---

# Phase 6 Plan 1: HippoRAG 2 Tracer Summary

**HippoRAG 2's five-node query-side chain answers a real query end to end through the §18 seam over its own isolated Cozo/Faiss namespaces, reached by a capability selector, with whole-graph PPR served by one native igraph/prpack call over a two-query bulk export — proving a second modality can register, resolve, run and return through machinery built for one.**

## Performance

- **Duration:** Continuation session (Task 1's checkpoint was answered by the developer in a prior halted run; this session resumed from that point)
- **Completed:** 2026-09-09
- **Tasks:** 3 (checkpoint answered, tracer implemented, capability/isolation tests added)
- **Files modified/created:** 29

## Accomplishments

- Recorded the developer's checkpoint answers (`06-CHECKPOINT-ANSWERS.md`): `igraph`/`numpy`/`scipy` all confirmed legitimate, dependencies land in core (not an optional extra)
- Added `igraph>=0.11,<2.0` and `numpy>=1.24,<3.0` to `databasise/pyproject.toml`'s core dependencies; `uv sync` clean, `igraph` (never `python-igraph`) in `uv.lock`
- `CozoGraphStore.export_to_igraph()`: §14.2's Graph bulk-export sub-capability — two Cozo queries whatever the graph's size, proven against both a 3-node and a 30-node/60-edge graph in the same test
- `FaissVectorStore.score_all()`: §14.2's exhaustive dense-scoring sub-capability — never a top-k truncation, visibly distinct from `query()` against the same seeded store
- Five HippoRAG 2 parts under `databasise/parts_core/hipporag/` — `fact-score`, `fact-filter`, `reset-vector-join`, `ppr`, `assemble-result` — all `structural_depth="opaque"`, all resolving `execution_mode="in-process"`
- `databasise/wirings/hipporag/base.json`: the tracer's 5-of-13-position base wiring, no arm patches (HippoRAG has none per the settled 03-RESEARCH.md §H.5 verdict)
- Modality-agnostic wiring pool: `wirings/resolve.py`'s `all_wirings()`/`load_wiring()`/`WIRING_NAMES` replace the hardcoded five-arm candidate list `seam/selectors.py` previously used
- Three seam couplings made declarative on each wiring's own top-level keys — `consumes_query`, `evidence_position`, `store_namespaces` — read by `seam/engine.py` and `parity/run_arm.py`; LightRAG's own behavior is byte-identical (its base now declares the exact values those modules previously hardcoded)
- One real cross-modality query resolves through a capability selector to HippoRAG's own wiring and returns `evidence[*].namespace == "hipporag-chunks"`, over stores fully disjoint from LightRAG's on the same `store_root`/`workspace`
- Full suite: 688 passed, 13 skipped (bare); 749 passed, 1 skipped with `--extra rest --extra mcp` — exactly 4 more than the 745/1 baseline recorded at Phase 5 close, matching this plan's 4 new cross-modality tests

## Task Commits

Each task was committed atomically (RED→GREEN for Task 2's `tdd="true"` cycle):

1. **Task 1: Package legitimacy checkpoint answers recorded** - `7682613` (docs)
2. **Task 2 (tracer, tdd): RED — failing cross-modality test** - `fd9551d` (test)
2. **Task 2 (tracer, tdd): GREEN — HippoRAG query chain implementation** - `ca9c3dc` (feat)
3. **Task 3: capability/isolation proof tests** - `e6ba9d9` (test)

_No REFACTOR commit — the GREEN implementation needed no follow-up cleanup once green._

## TDD Gate Compliance

Task 2 (`type="tracer" tdd="true"`) followed RED→GREEN:

- **RED:** `fd9551d` — `test_cross_modality_run.py` + `seeded_hipporag_store` fixture committed first, against pre-implementation code (implementation files temporarily stashed via `git stash push` for the RED run). Verified via `uv run pytest -q tests/seam/test_cross_modality_run.py`: **2 of 4 tests failed on real assertions** tied to the planned behavior (`assert envelope.evidence` failed with `[]` — the capability selector fell through to the default LightRAG arm since HippoRAG had no registered wiring; `assert "chunk_entity_relation" not in on_disk` failed since store namespaces weren't yet wiring-declared). This is genuine RED evidence — a real assertion failure on the target tests, not a collection/import error — not merely a nonzero exit.
- **GREEN:** `ca9c3dc` — implementation restored via `git stash pop`; all 4 target tests pass, full suite green (688 passed/13 skipped bare; 749/1 with extras, +4 over the 745/1 Phase 5 baseline).
- **Tool note:** `gsd_run check tdd-red-evidence` is TAP/Node-test-runner-oriented (`parseNodeTestSummary`) and does not natively parse pytest's default output format for this Python project; RED evidence was verified manually via pytest's own exit code and per-test failure attribution instead of running that tool mechanically.

## Files Created/Modified

- `databasise/parts_core/hipporag/{fact_score,fact_filter,reset_vector_join,ppr,assemble_result}.py` - the five ported parts
- `databasise/stores/graph.py` - `CozoGraphStore.export_to_igraph()`
- `databasise/stores/vector.py` - `FaissVectorStore.score_all()`
- `databasise/wirings/hipporag/base.json` - HippoRAG's base wiring
- `databasise/wirings/resolve.py` - `load_wiring`, `WIRING_NAMES`, `all_wirings`
- `databasise/wirings/lightrag/base.json` - added `consumes_query`/`evidence_position`/`store_namespaces`
- `databasise/seam/engine.py` - `_inject_query`/`_build_stores`/`_execute` read the three new declarative wiring keys; `_EVIDENCE_RETRIEVAL_NODE_ID` constant removed
- `databasise/seam/selectors.py` - `_capability_candidates` now sources `all_wirings()`
- `databasise/parity/run_arm.py` - `_build_stores` reads `store_namespaces` too
- `databasise/parts/registry.py` - `default_registry()` merges `HIPPORAG_PARTS`
- `databasise/tests/parts_core/hipporag/*`, `databasise/tests/stores/test_graph_bulk_export.py`, `test_vector_score_all.py`, `databasise/tests/seam/test_cross_modality_run.py`, `test_store_isolation.py` - new test coverage
- `databasise/tests/parts/test_registry.py`, `databasise/tests/test_embed_startup.py` - two pre-existing pinned-count regression tests updated to their new correct values (22→27 registry entries, 6→8 unconditional runtime deps)
- `databasise/tests/seam/test_leak.py` - fixed to read the retrieval position off the resolved wiring's own `evidence_position` instead of the removed module-level constant

## Decisions Made

See `key-decisions` in frontmatter. Most load-bearing: HippoRAG's `ctx.stores["graph"]` handle is a single already-namespaced store per run, not a `.select()`-style multi-namespace handle — the plan's own literal action prose for `ppr.py` named a `.select("hipporag-graph")` call that doesn't exist on `CozoGraphStore`; resolved per the plan's own `store_namespaces` architecture description (only the vector store selects per-node by name), documented as a Rule 1 auto-fix in `ppr.py`'s own module docstring.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `ppr.py`'s graph-store access corrected to match the plan's own declared architecture**
- **Found during:** Task 2 (implementing `ppr.py`)
- **Issue:** The plan's action prose for `ppr.py` names `ctx.stores["graph"].select("hipporag-graph").export_to_igraph()`, but `CozoGraphStore` has no `.select()` method — only the vector store is multi-namespace. The same plan's `store_namespaces` seam-coupling paragraph states explicitly that only the vector store selects per-node by name; kv/graph are each a single store already scoped to the resolved wiring's own declared namespace by `_build_stores`.
- **Fix:** Implemented `ctx.stores["graph"].export_to_igraph()` directly (no `.select()` call), matching the architecture the same plan's own `store_namespaces` paragraph establishes.
- **Files modified:** `databasise/parts_core/hipporag/ppr.py`
- **Verification:** `tests/parts_core/hipporag/test_ppr.py` and the end-to-end `test_cross_modality_run.py` both drive this code path and pass.
- **Committed in:** `ca9c3dc`

**2. [Rule 3 - Blocking] Two pre-existing pinned-count tests updated to their new correct values**
- **Found during:** Task 2's full-suite verify step
- **Issue:** `tests/parts/test_registry.py` asserted exactly 22 registered parts; `tests/test_embed_startup.py` asserted exactly 6 unconditional runtime dependencies. Adding 5 HippoRAG parts and 2 dependencies (as this plan's own explicit goal) makes both stale assertions fail.
- **Fix:** Updated both assertions and their surrounding docstrings to the new correct counts (27, 8) with an added provenance note, mirroring the codebase's own established pattern for this class of test (05-04's own note about extending an assertion when a legitimately new optional extra lands).
- **Files modified:** `databasise/tests/parts/test_registry.py`, `databasise/tests/test_embed_startup.py`
- **Verification:** Full suite green.
- **Committed in:** `ca9c3dc`

**3. [Rule 3 - Blocking] `tests/seam/test_leak.py` fixed after `_EVIDENCE_RETRIEVAL_NODE_ID` removal**
- **Found during:** Task 2's full-suite verify step
- **Issue:** `seam/engine.py`'s `_EVIDENCE_RETRIEVAL_NODE_ID` module constant was removed (superseded by reading `evidence_position` off the resolved wiring, per this plan's own seam-coupling instruction, and required by the plan's own acceptance criterion that `chunk-vector` appear nowhere in `engine.py`). `test_leak.py` imported that constant directly, breaking test collection.
- **Fix:** `test_leak.py` now reads the retrieval node id off its own locally-resolved wiring's `evidence_position` field, mirroring `_execute()`'s own new pattern, instead of importing the removed constant.
- **Files modified:** `databasise/tests/seam/test_leak.py`
- **Verification:** Full suite green (this test's own 8 assertions still pass unchanged).
- **Committed in:** `ca9c3dc`

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All three necessary for correctness/consistency; no scope creep. The `ppr.py` fix corrects the plan's own action prose to match its own stated architecture; the other two are direct, expected consequences of this plan's own additions (more registered parts, more dependencies, a generalized evidence-position lookup) breaking pinned-count/constant-import tests that exist specifically to catch such changes.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Five HippoRAG parts, the base wiring, the two new store capabilities, and the modality-agnostic seam are proven end to end — plans 06-02, 06-05 and 06-07 can add the remaining eight `## §H` positions (`chunk-embed`, `openie`, `entity-fact-embed`, `fact-edges`, `passage-edges`, `synonymy-edges`, `graph-augment-persist`, `dpr-fallback`) onto this same `databasise/wirings/hipporag/base.json` file.
- `fact-filter`'s `guard_fired` output (the `zero_surviving_facts_dpr_fallback` guard) has no consumer in this plan — plan 06-07 wires `dpr-fallback` to it, as already flagged in `fact_filter.py`'s own module docstring.
- MODAL-04's unclassified edge behaviour (a degenerate graph: zero passage vertices, an all-zero reset vector, a disconnected graph) remains carried as `unresolved`, per the plan's own `<flagged_assumptions>` — `ppr.py`'s all-zero-reset branch returns an all-zero score vector rather than letting `igraph`'s own exception propagate, but nothing asserts that is the *correct* behavior for a degenerate input; a later phase's own falsifier work owns settling that boundary.
- The upstream `hipporag` PyPI package is not installed and is not this plan's oracle (by design) — plan 06-09 records what a real upstream-package parity run would additionally settle.

## Self-Check: PASSED

- All `key-files.created` verified present on disk.
- `git log --oneline --all | grep -E "7682613|fd9551d|ca9c3dc|e6ba9d9"` returns all four commits.
- Every task's `<acceptance_criteria>` re-verified: `grep -v '^#' databasise/seam/engine.py | grep -c 'chunk-vector'` → `0`; `export_to_igraph`'s body contains no `implementation` string; `ppr.py` contains `implementation="prpack"`, `damping`, `directed=False`, `weights="weight"` in one call; `HIPPORAG_PARTS` has exactly 5 members, all `structural_depth == "opaque"`; `wirings/hipporag/base.json` parses with `report.ok` true; `resolve_selector(None, ...)` still resolves a LightRAG wiring and `_is_default_eligible` is `False` for HippoRAG's.
- Plan-level `<verification>`: `cd databasise && uv run pytest -q` exits 0 (688 passed, 13 skipped); `uv run python -m databasise.tools.check_import_boundary` exits 0; one real seam call resolves to HippoRAG and returns evidence from `hipporag-chunks`; no LightRAG store directory moved (pinned by `test_store_isolation.py`).

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-09*
