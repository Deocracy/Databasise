---
phase: 03-lightrag-query-side
plan: 05
subsystem: rag-engine
tags: [lightrag, cozo, faiss, graph-store, provenance, derived_from, parity]

# Dependency graph
requires:
  - phase: 03-04
    provides: "Registered wiring set (databasise/wirings/lightrag/), resolve_arm resolver, LIGHTRAG_PARTS tuple merged into default_registry(), the @0.1.0 versioned-naming convention (owner's Task 1 checkpoint), the naive arm's seven ported parts establishing this codebase's part-body/test conventions"
provides:
  - "CozoGraphStore.get_node_edges — a new read method enumerating a node's incident edges (either direction, buffer-consulted), proven against the frozen-bug regression suite before any node body depends on it"
  - "Five more registered LightRAG parts: lightrag/keyword-extractor@0.1.0, lightrag/entity-lookup@0.1.0, lightrag/relation-lookup@0.1.0, lightrag/entity-hydrate-expand@0.1.0, lightrag/relation-hydrate-expand@0.1.0 — twelve of the base wiring's eighteen positions now have real bodies"
  - "keywords' pinned-replay mechanism (config['pinned']/config['pinned_output']) — the D-12 pinning primitive plan 03-08/03-09's harness will drive to run the stochastic keyword-extraction node once per query and feed the same recorded output to both local/global arms"
  - "derived_from-carrying authored evidence from both hydrate-expand bodies, and a missing_seeds list making an absent graph node/edge observable instead of silently dropped"
affects: [03-06, 03-07, 03-08, 03-09]

# Actuals (#2632)
actuals:
  tokens: 11773
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "A store method extends an existing non-aggregating query's own shape (node_degree's src=$id or tgt=$id disjunction) to project one more column, rather than adding a second aggregation-shaped query for the same underlying scan — the frozen-bug #244 mitigation generalises this way without a new risk surface."
    - "edge_degree (v1's own node_degree(src)+node_degree(tgt) shape) is computed inline from two existing store calls rather than promoted to a new store method — a derived value composed from primitives already proven against the frozen-bug suite needs no new surface of its own."
    - "A part whose body must prove it never reaches an undeclared store threads the real _ScopedStoresView/CapabilityScopedStores wrapper (runner/scheduler.py's own deny-by-default pair) through NodeContext.stores in its test, rather than a bare dict — a bare dict would raise a raw KeyError, not the named UndeclaredEffectError the scheduler's real path produces."
    - "A stochastic node's pinned-replay path takes an explicit boolean config key (config['pinned']) rather than inferring replay from the mere presence of a recorded-output value — makes the replay visible in the wiring's own config_hash, and keeps a pinned run's TokenAccounting (counted_by='pinned-replay', call_count=0) structurally distinguishable from a live call's populated accounting."

key-files:
  created:
    - databasise/parts_core/lightrag/keywords.py
    - databasise/parts_core/lightrag/entity_lookup.py
    - databasise/parts_core/lightrag/relation_lookup.py
    - databasise/parts_core/lightrag/entity_hydrate_expand.py
    - databasise/parts_core/lightrag/relation_hydrate_expand.py
    - databasise/tests/parts_core/lightrag/test_graph_half_parts.py
  modified:
    - databasise/stores/graph.py
    - databasise/tests/stores/test_graph.py
    - databasise/tests/stores/test_graph_frozen_bugs.py
    - databasise/parts_core/lightrag/__init__.py
    - databasise/tests/parts/test_registry.py

key-decisions:
  - "keywords' prompt text is copied verbatim (never imported — D-14's import boundary) from v1/lightrag/prompt.py's PROMPTS['keywords_extraction']/PROMPTS['keywords_extraction_examples'], since a parity comparison against the ported node must exercise the identical prompt, not a paraphrase."
  - "keywords' JSON-payload parser is a stdlib-only, deliberately lenient port of v1's own _parse_keywords_payload (code-fence stripping + json.loads) rather than taking on json_repair as a new dependency — json_repair is not in databasise/pyproject.toml's approved runtime deps (only v1's own pyproject.toml lists it), and adding a dependency is out of this plan's scope."
  - "entity-hydrate-expand's and relation-hydrate-expand's edge_degree/rank fields are computed inline from two node_degree calls (v1's own edge_degree(src,tgt) = node_degree(src)+node_degree(tgt) shape, v1/lightrag/kg/cozo_impl.py:336-337) rather than as a new store method — Task 1's own instruction against a speculative batch method extends naturally to this derived value too."
  - "get_node_edges' returned src/tgt pairs are used as-is (no re-canonicalisation) since every write path (upsert_edge, the flush) already canonicalises via _canonical_edge_key before storing — the stored/buffered rows are already in canonical order."

patterns-established:
  - "Deny-by-default store-boundary tests thread the real _ScopedStoresView(CapabilityScopedStores(...), declared_effects) wrapper rather than a plain dict, so the assertion is about the named UndeclaredEffectError the scheduler's own path raises, not merely 'something raised' — mirrors 03-04's own rerank-client refusal test pattern, extended to the store side."
  - "A hydrate-expand node's output carries two lists (its own hydrated seeds, and the opposite evidence kind produced by its expansion sub-step) — entity-hydrate-expand emits {entities, relations}, relation-hydrate-expand emits {relations, entities} — matching v1's own crossover (an entity's incident-edge expansion emits relations; a relation's endpoint expansion emits entities), which is why the base wiring's join-entities and join-relations nodes both depend on both hydrate-expand nodes."

requirements-completed: [MODAL-01]

coverage:
  - id: D1
    description: "CozoGraphStore.get_node_edges enumerates a node's incident edges (either direction), buffer-consulted, proven against the frozen-bug regression suite (agreement with node_degree including unflushed buffered state) before any node body depends on it"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/stores/test_graph_frozen_bugs.py::test_bug244_get_node_edges_agrees_with_node_degree_on_a_populated_graph"
        status: pass
      - kind: unit
        ref: "databasise/tests/stores/test_graph.py::test_get_node_edges_agrees_with_node_degree_including_buffered_state"
        status: pass
    human_judgment: false
  - id: D2
    description: "keywords (lightrag/keyword-extractor@0.1.0) sends v1's own keyword-extraction prompt verbatim on the live path (populated TokenAccounting), and supports D-12's pinned-replay path (explicit config key, zero LLM calls, structurally distinguishable accounting)"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_graph_half_parts.py::test_keywords_live_call_sends_v1s_prompt_and_returns_a_populated_token_accounting"
        status: pass
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_graph_half_parts.py::test_keywords_pinned_path_returns_the_recorded_output_and_makes_zero_llm_calls"
        status: pass
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_graph_half_parts.py::test_keywords_pinned_and_live_accounting_are_distinguishable"
        status: pass
    human_judgment: false
  - id: D3
    description: "entity-lookup and relation-lookup (retriever, reads_vector) query the vector store with the query vector from embedder-query and emit scored items ordered by descending score, carrying entity_name / src_id+tgt_id as the provenance refs the hydrate-expand pair dereferences"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_graph_half_parts.py::test_entity_lookup_returns_items_ordered_by_descending_score_with_entity_name"
        status: pass
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_graph_half_parts.py::test_relation_lookup_returns_items_ordered_by_descending_score_with_endpoints"
        status: pass
    human_judgment: false
  - id: D4
    description: "entity-hydrate-expand and relation-hydrate-expand (retriever, reads_graph only) hydrate their own lookup node's seeds and expand to one-hop neighbours, report an absent seed in missing_seeds rather than dropping it, carry derived_from on every emitted item, and cannot reach ctx.stores['vector']/ctx.stores['kv'] (proven via the real deny-by-default wrapper)"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_graph_half_parts.py::test_entity_hydrate_expand_hydrates_seeds_and_expands_to_neighbour_relations"
        status: pass
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_graph_half_parts.py::test_entity_hydrate_expand_reports_a_missing_seed_rather_than_dropping_it"
        status: pass
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_graph_half_parts.py::test_entity_hydrate_expand_cannot_reach_the_vector_store"
        status: pass
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_graph_half_parts.py::test_relation_hydrate_expand_hydrates_seeds_and_expands_to_endpoint_entities"
        status: pass
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_graph_half_parts.py::test_relation_hydrate_expand_reports_a_missing_seed_rather_than_dropping_it"
        status: pass
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_graph_half_parts.py::test_relation_hydrate_expand_cannot_reach_the_kv_store"
        status: pass
    human_judgment: false

duration: ~40min
completed: 2026-09-01
status: complete
---

# Phase 3 Plan 05: LightRAG Query Side — Graph Half Summary

**Five more §L.1 positions (keyword extractor, entity/relation vector lookup, entity/relation graph hydrate-expand) ported as real registered parts over one new graph-store read method, taking the base wiring from seven to twelve real-bodied components — the `local`/`global`/`hybrid` arms' actual knowledge-graph retrieval now runs, reading storage only through the machine's graph primitive.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 3 completed
- **Files modified:** 11 (6 created, 5 modified)

## Accomplishments

- Added `CozoGraphStore.get_node_edges` — a read method enumerating a node's incident edges (either direction, buffer-consulted before flush), extending `node_degree`'s own non-aggregating query shape (frozen-bug #244's mitigation) rather than introducing a second aggregation-shaped query. Proven against `test_graph_frozen_bugs.py` (agreement with `node_degree`, including unflushed buffered puts/removals) before any node body depends on it.
- Registered `lightrag/keyword-extractor@0.1.0`: sends v1's own keyword-extraction prompt verbatim on the live path, and supports D-12's pinned-replay mechanism (`config["pinned"]`/`config["pinned_output"]`) — the mechanism plan 03-08/03-09's parity harness needs to run the phase's one stochastic query-side node once per query and feed the same recorded keywords into both `local` and `global` arm runs.
- Registered `lightrag/entity-lookup@0.1.0` and `lightrag/relation-lookup@0.1.0`: top-k vector search over the query embedding, porting v1's own scoring/ordering, emitting items carrying `entity_name` / `src_id`+`tgt_id` as the provenance refs the hydrate-expand pair dereferences.
- Registered `lightrag/entity-hydrate-expand@0.1.0` and `lightrag/relation-hydrate-expand@0.1.0`: hydrate their own lookup node's seed items from `ctx.stores["graph"]` and expand to one-hop neighbours (entity half → incident edges via `get_node_edges`; relation half → endpoint entities via `get_node`), mirroring v1's own `_find_most_related_edges_from_entities`/`_find_most_related_entities_from_relationships` crossover shape. A seed whose graph node/edge is absent is reported in `missing_seeds` rather than dropped; every hydrated or expanded item carries `derived_from`. Neither body can reach the vector or KV store — proven against the real `_ScopedStoresView`/`CapabilityScopedStores` deny-by-default wrapper.
- Twelve of the base wiring's eighteen positions now have real, tested bodies; `default_registry()` holds 19 entries.

## Task Commits

1. **Task 1: `CozoGraphStore.get_node_edges`** — `fc62ffc` (feat)
2. **Task 2: `keywords`, `entity-lookup`, `relation-lookup`** — `4070f95` (feat)
3. **Task 3: `entity-hydrate-expand` and `relation-hydrate-expand`** — `9cb6c8f` (feat)

_No plan-metadata commit yet — SUMMARY.md is the orchestrator's post-wave responsibility in worktree mode._

## Files Created/Modified

- `databasise/stores/graph.py` — `CozoGraphStore.get_node_edges`
- `databasise/parts_core/lightrag/{keywords,entity_lookup,relation_lookup,entity_hydrate_expand,relation_hydrate_expand}.py` — the five new ported part bodies
- `databasise/parts_core/lightrag/__init__.py` — `LIGHTRAG_PARTS` tuple extended to twelve entries
- `databasise/tests/parts_core/lightrag/test_graph_half_parts.py` — 11 per-body tests
- `databasise/tests/stores/test_graph.py`, `test_graph_frozen_bugs.py` — `get_node_edges` coverage (7 new tests total)
- `databasise/tests/parts/test_registry.py` — updated the registry-size invariant (see Deviations)

## Decisions Made

- `keywords`' prompt text is copied verbatim from `v1/lightrag/prompt.py` (never imported — D-14's import boundary); a parity comparison must exercise v1's identical prompt, not a paraphrase.
- `keywords`' JSON-payload parser is a stdlib-only, deliberately lenient port of v1's own `_parse_keywords_payload` — `json_repair` is not an approved `databasise/pyproject.toml` runtime dependency, so no new dependency was added.
- `edge_degree` (`node_degree(src) + node_degree(tgt)`, v1's own shape at `v1/lightrag/kg/cozo_impl.py:336-337`) is computed inline from two existing `node_degree` calls rather than promoted to a new store method — Task 1's own instruction against a speculative batch method extends naturally to this derived value.
- `get_node_edges`' returned `src`/`tgt` pairs are used as-is (no re-canonicalisation): every write path already canonicalises via `_canonical_edge_key` before storing, so the stored/buffered rows are already in canonical order.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale registry-size invariant, twice**
- **Found during:** Task 2 and Task 3, first full-suite run after each `LIGHTRAG_PARTS` extension
- **Issue:** `tests/parts/test_registry.py::test_default_registry_holds_exactly_fourteen_entries` hardcoded 03-04's own post-plan count (14). Both Task 2 (three new parts) and Task 3 (two more) break that count by design — the identical pattern 03-04-SUMMARY.md's own Deviations section already documents for its own predecessor invariant.
- **Fix:** Updated the assertion and test name twice: 14 → 17 (Task 2 commit), then 17 → 19 (Task 3 commit), with each docstring noting the count grows again once plan 03-06 lands.
- **Files modified:** `databasise/tests/parts/test_registry.py`
- **Verification:** `cd databasise && uv run pytest -q` — 330/333 passed both times (3 pre-existing skip-guarded live-endpoint tests from 03-04, unrelated to this plan).
- **Committed in:** `4070f95` (Task 2), `9cb6c8f` (Task 3)

---

**Total deviations:** 1 auto-fixed issue, applied twice (Rule 1 stale test invariant — same root cause as 03-04's own precedent)
**Impact on plan:** Both fixes were necessary for each task's own stated deliverable (registering new parts) to land without a false-negative test failure. No scope creep.

## Issues Encountered

- **The plan's acceptance-criteria grep for `test_graph_frozen_bugs.py`'s skip/xfail count (`grep -v '^\s*#' ... | grep -c 'skip\|xfail'` returning 0) was already non-zero before this plan touched the file** — the module's own docstring prose ("no test in this module may carry a pytest skip or xfail marker") contains the words "skip"/"xfail" outside of `#`-comments, so the literal grep as written counts prose, not markers. Confirmed via `git show HEAD:...` on the pre-plan file: the count was 7 before any edit in this plan and is still 7 after (my additions introduced zero new occurrences). The module's own real enforcement — `test_no_skip_or_xfail_markers_in_this_module`, which checks for the literal `mark.skip`/`mark.xfail` substrings via string concatenation to avoid self-matching — passes both before and after. Not fixed (pre-existing plan-authoring imprecision, out of this plan's scope; the actual invariant it protects held throughout).
- **No real corpus/build artifacts are present in this worktree** (same fact 03-04-SUMMARY.md's own Issues Encountered section records): `v1/.parity_working_dir`, `v1/.parity_v2_store`, and `v1/.env.parity` are gitignored, worktree-local products from a different execution session. This means the plan's own "if looping dominates wall-clock on the real corpus, record the measurement" instruction (Task 1's and Task 3's own text, from 03-RESEARCH.md's Open Question 1) could not be exercised for real — every test in this plan runs against small synthetic in-memory graphs, where looping single-item `get_node`/`node_degree`/`get_node_edges` calls is trivially fast. No measurement to record; the batch-method question stays open for a future session holding the real ingest artifacts, per the plan's own instruction to leave it unbuilt until a real measurement says otherwise.

## User Setup Required

None for the code delivered here. Exercising this plan's parts against the real imported v1 index needs the same setup 03-04-SUMMARY.md already documents: plan 03-02's real ingest artifacts (or a re-run) plus `v1/.env.parity`.

## Next Phase Readiness

- Twelve of the base wiring's eighteen positions have real bodies; `entity-hydrate-expand`/`relation-hydrate-expand`'s `{entities, relations, missing_seeds}` output shape is what plan 03-06's `join-roundrobin` nodes join over (`join-entities`/`join-relations` both depend on both hydrate-expand nodes per the base wiring, matching v1's own entity/relation crossover).
- The remaining three base-wiring positions (`join-roundrobin`, `truncator-token-budget`, `chunk-selector-kg`) are plan 03-06's deliverable — only once all fifteen new components are registered does the unpatched base itself parse clean and the `hybrid`/`local`/`global` arms become fully dispatchable.
- `keywords`' pinned-replay config shape (`config["pinned"]`/`config["pinned_output"]`) is ready for plan 03-08/03-09's parity harness to drive without further changes to this node.

---
*Phase: 03-lightrag-query-side*
*Completed: 2026-09-01*

## Self-Check: PASSED

All created/modified files confirmed present on disk; all three task commit hashes (`fc62ffc`, `4070f95`, `9cb6c8f`) confirmed in `git log --oneline --all`.
