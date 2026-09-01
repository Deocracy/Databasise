---
phase: 03-lightrag-query-side
plan: 06
subsystem: rag-engine
tags: [lightrag, wiring, join, budget, provenance, derived_from, parity, rfc6902]

# Dependency graph
requires:
  - phase: 03-04
    provides: "Registered wiring set (databasise/wirings/lightrag/), resolve_arm/load_base resolver, the @0.1.0 versioned-naming convention (owner's Task 1 checkpoint), seven ported LightRAG parts establishing this codebase's part-body/test conventions"
  - phase: 03-05
    provides: "Five graph-half parts (keywords, entity-lookup, relation-lookup, entity-hydrate-expand, relation-hydrate-expand), the {entities, relations, missing_seeds} crossover output shape join-roundrobin merges over, CozoGraphStore.get_node_edges"
provides:
  - "lightrag/join-roundrobin@0.1.0 — one component serving three positions (join-entities, join-relations, join-chunks), config-selected precedence/arity, rank_position stamped per CONTRACT §13.2 ¶4's D6 repair, dedup-collapse derived_from union per CONTRACT §4's D9 repair"
  - "lightrag/truncator-token-budget@0.1.0 — one component serving two positions (budget-entities, budget-relations), first-come-over-joined-list tail truncation, per-position default allowance"
  - "lightrag/chunk-selector-kg@0.1.0 — WEIGHT chunk selection ported from v1's pick_by_weighted_polling, VECTOR exposed via an optional config[\"query_vector\"] hook, reads_kv/reads_vector declared unconditionally per §19.9"
  - "databasise/tests/parity/test_arm_conformance.py — the unpatched mix base and all five arms parse clean, resolve to their published node id sets, derive in-process/stage (opaque for embedder-index) everywhere, zero blast-radius violations, union to exactly the eighteen §L.1 positions"
  - "All eighteen §L.1 positions now resolve against a registered part; default_registry() holds 22 entries"
affects: [03-07, 03-08, 03-09]

# Actuals (#2632)
actuals:
  tokens: 11946
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "A fan-in component serving multiple wiring positions with the same config shape (join-entities/join-relations both consume {entities, relations, missing_seeds}) resolves which field to merge via a fixed node-id lookup, not a free-text config key — the published wiring declares no such key, and inventing one would desync the test from what actually ships."
    - "A fan-in's dedup collapse unions the discarded contributor's own derived_from into the survivor's rather than dropping it — CONTRACT §4 D9's named case (a merge that re-projects survivors into a narrower shape is authoring, not pass-through) applied concretely."
    - "Where a node's own declared effect (reads_vector) has no wiring-supplied input to actually exercise it (chunk-sel-kg has no embedder-query dependency), the body exposes an explicit config hook for the path and degrades to the reachable method without fabricating input — the declaration stays honest to §19.9's fallback-reachability rule without the runtime body pretending a path is live when the real wiring never feeds it."
    - "Task-scoped registry-size test invariants and part-registration __init__.py edits are staged and committed in per-task slices, not as one combined diff, even when all three tasks' final code was drafted together — matching 03-04/03-05's own atomic-commit precedent for a plan-wide __init__.py file touched by every task."

key-files:
  created:
    - databasise/parts_core/lightrag/join_roundrobin.py
    - databasise/parts_core/lightrag/truncator_token_budget.py
    - databasise/parts_core/lightrag/chunk_sel_kg.py
    - databasise/tests/parity/test_arm_conformance.py
  modified:
    - databasise/parts_core/lightrag/__init__.py
    - databasise/tests/parts_core/lightrag/test_transform_parts.py
    - databasise/tests/parts/test_registry.py

key-decisions:
  - "join-roundrobin's per-position merge field (entities/relations/items) is a fixed dict keyed by ctx.node_id, not a config['merge_field'] key — the published base.json (03-04's committed, read-only content) declares no such key for any of the three join positions, and inventing one for this plan's own convenience would desync the test suite from the wiring it claims to conform to."
  - "join-roundrobin dedups join-entities too (by entity_name), not just join-relations — v1's own round-robin merge (operate.py) dedups both entities (seen_entities set) and relations (sorted src_tgt pair) identically; the base wiring's config text only narrates join-relations' dedup rule in its arm_precedence field, but the behavior is symmetric in the source this plan ports from."
  - "chunk-sel-kg's VECTOR pick method is exposed via an optional config['query_vector'] hook rather than silently no-op'd or hard-refused: the node's own base-wiring deps (budget-entities/budget-relations only) carry no query-embedding input, so a real run against the unpatched base always falls through to WEIGHT — recorded here as an honest architectural fact, not fixed by adding a new dependency edge to the committed base.json (out of this plan's scope; base.json is 03-04's read-only committed content)."
  - "truncator-token-budget estimates each item's token cost from its own JSON-serialised form at assemble.py's existing four-chars-per-token heuristic, rather than adding a tokenizer dependency — matches the precedent 03-04's assemble.py already set for this same tracer-scale limitation."

patterns-established:
  - "A join/budget node with empty declared effects (a pure transform, no store or client access) is tested with a plain unscoped NodeContext and no deny-by-default wrapper, matching test_naive_arm_parts.py's own convention for zero-effect nodes."
  - "Task 3's arm-conformance test computes every derived property (effective_depth, execution_mode, blast_radius_violations) through the real validator functions, never a reimplementation — the same discipline databasise/evidence/falsifier2.py already established for the committed Falsifier 2 evidence."

requirements-completed: [MODAL-01]

coverage:
  - id: D1
    description: "join-roundrobin (lightrag/join-roundrobin@0.1.0) serves all three join positions from one body — round-robin interleave with config-selected precedence, join-chunks' declared arity enforced (raises on mismatch), rank_position stamped per CONTRACT §13.2 ¶4's D6 repair, and a dedup collapse unions the discarded contributor's derived_from into the survivor per CONTRACT §4's D9 repair"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_transform_parts.py (join-roundrobin cases, 7 tests)"
        status: pass
    human_judgment: false
  - id: D2
    description: "truncator-token-budget (lightrag/truncator-token-budget@0.1.0) serves both budget positions — first-come-over-joined-list, tail-only truncation preserving input order, an allowance below the first item's cost yields an empty list and zero consumed, per-position default allowance overridable via config"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_transform_parts.py (truncator-token-budget cases, 3 tests)"
        status: pass
    human_judgment: false
  - id: D3
    description: "chunk-selector-kg (lightrag/chunk-selector-kg@0.1.0) declares reads_kv/reads_vector unconditionally, selects chunks by WEIGHT (ported from v1's pick_by_weighted_polling) with a fall-through report of which method actually ran, and reaches the vector store for real when a query vector is supplied"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_transform_parts.py (chunk-selector-kg cases, 3 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The unpatched mix base and all five arms (naive, bypass, hybrid, local, global) parse with zero violations, each arm resolves to exactly its own published resulting_node_id_set, every node derives execution_mode=in-process and effective_depth=stage except embedder-index (opaque), zero blast-radius violations, and the union of all node ids across base plus arms equals exactly the eighteen §L.1 positions"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_arm_conformance.py (9 tests, including the plan's own acceptance-criteria script reproduced verbatim)"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-09-01
status: complete
---

# Phase 3 Plan 06: LightRAG Query Side — Closing the Node Set Summary

**Three more §L.1 positions closed (join-roundrobin serving three, truncator-token-budget serving two, chunk-selector-kg serving one) over fifteen total registered components — the unpatched `mix` base and all five arms now parse clean, and the union of their node ids equals exactly the eighteen published positions, proven through the real validator functions rather than a reimplementation.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3 completed
- **Files modified:** 7 (4 created, 3 modified)

## Accomplishments

- Registered `lightrag/join-roundrobin@0.1.0`: one component serving `join-entities`, `join-relations`, and `join-chunks`. Config-selected arm precedence (falling back to the wiring's own natural deps order where `arm_precedence`'s text doesn't name a dep directly — which is always the same "local-first" order v1's own code hard-codes), `join-chunks`' declared `arity` enforced as a hard refusal on mismatch, `rank_position` stamped on every emitted item per CONTRACT §13.2 ¶4's D6 repair (the fan-in family's declared score semantics for a positional interleave with no score read). A dedup collapse (the reversed-endpoint-pair case `join-relations`' own config narrates) unions the discarded contributor's `derived_from` into the survivor's rather than silently dropping it — CONTRACT §4's D9 repair applied concretely, not just cited.
- Registered `lightrag/truncator-token-budget@0.1.0`: one component serving `budget-entities` and `budget-relations`. First-come-over-joined-list truncation, tail-only, input order preserved, never re-sorted (re-sorting here would corrupt the ranking the retrieval-level parity comparison measures). Per-position default allowance (v1's own `DEFAULT_MAX_ENTITY_TOKENS`/`DEFAULT_MAX_RELATION_TOKENS`), overridable via `config["max_token_allowance"]` per CONTRACT §19.4.
- Registered `lightrag/chunk-selector-kg@0.1.0`: WEIGHT pick method ported by copy from v1's own `pick_by_weighted_polling` (occurrence counting, earlier-position-wins dedup, linear-gradient allocation), VECTOR exposed via an optional `config["query_vector"]` hook since this node's own base-wiring deps carry no query embedding — the unpatched base's own committed config degrades straight to WEIGHT without ever fabricating a vector to query with, an honest recorded fact rather than a silently masked gap. `reads_kv`/`reads_vector` declared unconditionally per CONTRACT §19.9's fallback-reachability rule.
- All eighteen `§L.1` positions now resolve against a registered part; `default_registry()` holds 22 entries.
- Wrote `databasise/tests/parity/test_arm_conformance.py`: the unpatched `mix` base parses clean for the first time (previously unparseable — eleven of its components were unregistered before this plan), every arm resolves to exactly its own published `resulting_node_id_set`, every node derives `execution_mode=in-process` and `effective_depth=stage` (except `embedder-index`, `opaque`), zero blast-radius violations anywhere, and the union of node ids across all five arms plus the base equals exactly the eighteen published positions — every derived property computed through the real validator functions, matching `databasise/evidence/falsifier2.py`'s own discipline.

## Task Commits

1. **Task 1: `join-roundrobin` — one component, three positions** — `d11d92a` (feat)
2. **Task 2: `truncator-token-budget` and `chunk-selector-kg`** — `407b7b4` (feat)
3. **Task 3: Base and all five arms — parse clean and conform to their published node id sets** — `681289d` (test)

_No plan-metadata commit yet — SUMMARY.md is the orchestrator's post-wave responsibility in worktree mode._

## Files Created/Modified

- `databasise/parts_core/lightrag/join_roundrobin.py` — the join-roundrobin component (three positions)
- `databasise/parts_core/lightrag/truncator_token_budget.py` — the truncator-token-budget component (two positions)
- `databasise/parts_core/lightrag/chunk_sel_kg.py` — the chunk-selector-kg component
- `databasise/parts_core/lightrag/__init__.py` — `LIGHTRAG_PARTS` tuple extended to fifteen entries
- `databasise/tests/parts_core/lightrag/test_transform_parts.py` — 13 per-body tests (7 join, 3 truncator, 3 chunk-selector)
- `databasise/tests/parts/test_registry.py` — registry-size invariant updated in two steps (19→20→22, see Deviations)
- `databasise/tests/parity/test_arm_conformance.py` — 9 tests, including the plan's own acceptance-criteria script reproduced verbatim as a pytest case

## Decisions Made

- `join-roundrobin`'s per-position merge field (`entities`/`relations`/`items`) is a fixed lookup keyed by `ctx.node_id`, not a `config["merge_field"]` key — the published `base.json` declares no such key, and inventing one would desync the test suite from the wiring it claims to conform to.
- `join-roundrobin` dedups `join-entities` too (by `entity_name`), not just `join-relations` — v1's own round-robin merge dedups both entities and relations identically; the base wiring's `arm_precedence` field only narrates `join-relations`' dedup rule in its text, but the source behavior this plan ports is symmetric.
- `chunk-sel-kg`'s VECTOR pick method is exposed via an optional `config["query_vector"]` hook rather than silently no-op'd or hard-refused — the node's own base-wiring deps carry no query-embedding input, so a real run against the unpatched base always degrades to WEIGHT. Recorded as an honest architectural fact, not repaired by adding a new dependency edge to the committed `base.json` (out of this plan's scope).
- `truncator-token-budget` estimates token cost from each item's own JSON-serialised form at `assemble.py`'s existing four-chars-per-token heuristic, matching that file's own precedent rather than adding a tokenizer dependency.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale registry-size invariant, twice**
- **Found during:** Task 1 and Task 2, first full-suite run after each `LIGHTRAG_PARTS` extension
- **Issue:** `tests/parts/test_registry.py::test_default_registry_holds_exactly_nineteen_entries` hardcoded 03-05's own post-plan count (19). Both Task 1 (one new part) and Task 2 (two more) break that count by design — the identical pattern 03-04-SUMMARY.md and 03-05-SUMMARY.md both already document for their own predecessor invariants.
- **Fix:** Updated the assertion and test name twice: 19 → 20 (Task 1 commit), then 20 → 22 (Task 2 commit), with the final docstring noting this is by design the final count for the LightRAG query side.
- **Files modified:** `databasise/tests/parts/test_registry.py`
- **Verification:** `cd databasise && uv run pytest -q` — 337/340 passed after Task 1, 343/346 after Task 2 (3 pre-existing skip-guarded live-endpoint tests from 03-04, unrelated to this plan).
- **Committed in:** `d11d92a` (Task 1), `407b7b4` (Task 2)

---

**Total deviations:** 1 auto-fixed issue, applied twice (Rule 1 stale test invariant — same root cause as 03-04's and 03-05's own precedent)
**Impact on plan:** Both fixes were necessary for each task's own stated deliverable (registering new parts) to land without a false-negative test failure. No scope creep.

## Issues Encountered

- **`databasise/parts_core/lightrag/heading_backfill.py` (03-04's own file, not touched by this plan) reads `ctx.inputs["chunk-vector"]` unconditionally**, but the base/hybrid/local/global wirings declare `heading-backfill`'s dep as `join-chunks`, not `chunk-vector` directly (only the `naive` arm patch overrides this dep to `chunk-vector`). This means `heading_backfill.py`'s body would `KeyError` if actually *executed* against the base/hybrid/local/global node graph. This plan's Task 3 does not execute any node body — it only parses wirings and computes `effective_depth`/`execution_mode`/`blast_radius_violations` through the validator, never dispatching a `Part.body` — so this latent bug is not exercised here and stays out of this plan's scope (`heading_backfill.py` is not in this plan's `<files>` list; Rule 1's scope boundary applies). Flagged for whichever future plan (likely 03-07's real end-to-end run) first drives a full `hybrid`/`local`/`global` arm through the scheduler.
- No real corpus/build artifacts are present in this worktree (the same fact 03-04-SUMMARY.md and 03-05-SUMMARY.md both record): `v1/.parity_working_dir`, `v1/.parity_v2_store`, and `v1/.env.parity` are gitignored, worktree-local products from a different execution session. Not relevant to this plan's own deliverable (this plan touches only pure in-memory transforms and static wiring conformance, no live endpoints), noted for completeness.

## User Setup Required

None for the code delivered here.

## Next Phase Readiness

- All eighteen `§L.1` positions resolve against a registered part; the unpatched `mix` base and all five arms parse clean and conform to their own published node id sets — criterion 1 (all eighteen positions, not "most positions run") is now checkable in full and passing.
- `databasise/tests/parity/test_arm_conformance.py` is a static conformance suite (parse + derived properties only, no node execution) — the next plan that drives a real end-to-end run through `hybrid`/`local`/`global` will need to fix `heading_backfill.py`'s hardcoded `chunk-vector` input key (see Issues Encountered) before that arm can actually execute past `heading-backfill`.
- `chunk-sel-kg`'s VECTOR pick method needs a query-embedding input the base wiring's own `deps` don't currently supply; a future plan wiring `embedder-query` as an additional dep (an architectural change to the committed `base.json`, out of this plan's scope) is the only way to make VECTOR reachable on a real run rather than always degrading to WEIGHT.

---
*Phase: 03-lightrag-query-side*
*Completed: 2026-09-01*

## Self-Check: PASSED

All created/modified files confirmed present on disk; all three task commit hashes (`d11d92a`, `407b7b4`, `681289d`) confirmed in `git log --oneline --all`.
