---
phase: 11-lightrag-corpus-path
plan: 04
subsystem: retrieval
tags: [lightrag, kg-query, fidelity, d-16, lrag-18, chunk-selection, wiring]
status: complete

requires:
  - phase: 03
    provides: the eighteen LightRAG query-side parts and the base wiring plus five arm patches
provides:
  - keywords emits ll_keywords_str / hl_keywords_str and applies v1's short-query fallback
  - embedder-query emits vector, ll_vector and hl_vector from one batched embed call on the KG arms
  - entity-lookup searches with ll_vector, relation-lookup with hl_vector
  - entity-hydrate-expand sorts one-hop relations by (rank, weight) desc and reads each node degree once
  - chunk-sel-kg selects entity and relation chunks separately with a working VECTOR pick (score_all), pick_method_used and pick_method_used_by_side
  - join-chunks dedups by chunk_id/id; base.json emits chunk-vector first
  - rerank receives the query through consumes_query
  - databasise/tests/parts_core/lightrag/test_kg_retrieval_fidelity.py (LRAG-18 parity tests)
affects: [11-11, LRAG-17, LRAG-18]

actuals:
  tokens: 11500
  tasks: 3
  commits: 3
plan_head_before: c9de2e0b533430f1238228c09bc3424784b4f675
plan_head_after: 6fdb0b5e314be51a941ca51fbbe0c2801da60410

tech-stack:
  added: []
  patterns:
    - "one score_all per query, filtered to candidate ids, replaces a top-k query for candidate-restricted vector ranking"
    - "per-call memo dict for graph reads that repeat across a node body"

key-files:
  created:
    - databasise/tests/parts_core/lightrag/test_kg_retrieval_fidelity.py
  modified:
    - databasise/parts_core/lightrag/keywords.py
    - databasise/parts_core/lightrag/embedder_query.py
    - databasise/parts_core/lightrag/entity_lookup.py
    - databasise/parts_core/lightrag/relation_lookup.py
    - databasise/parts_core/lightrag/entity_hydrate_expand.py
    - databasise/parts_core/lightrag/chunk_sel_kg.py
    - databasise/parts_core/lightrag/join_roundrobin.py
    - databasise/wirings/lightrag/base.json
    - databasise/wirings/lightrag/README.md
    - databasise/parity/run_arm.py
    - databasise/tests/parts_core/lightrag/test_graph_half_parts.py
    - databasise/tests/parts_core/lightrag/test_transform_parts.py
    - databasise/tests/parity/test_graph_arm_real_index.py
    - databasise/tests/parity/test_naive_arm_end_to_end.py

key-decisions:
  - "Relation chunks exclude the chunk ids the entity side actually selected (v1 operate.py:5592-5626), not every entity candidate id"
  - "VECTOR count is v1's int(related_chunk_number * len(items) / 2) with no clamp; a count of 0 falls back to WEIGHT for that side, as v1 does"
  - "A VECTOR pick where any candidate has no stored vector falls back to WEIGHT (v1 utils.py:4143)"
  - "pick_method_used is the method both sides used, MIXED when they differ, WEIGHT when no side had candidates; pick_method_used_by_side names each side"
  - "Relation sort compares weight as float because Cozo returns weights as strings"
  - "All part versions unchanged (body-only changes, effects unchanged)"

patterns-established:
  - "KG lookups read their own keyword vector (ll_vector / hl_vector); a None vector returns no items without a store query"

duration: 45min
completed: 2026-10-18
---

# Phase 11 Plan 04: LightRAG KG Retrieval Fidelity Summary

**The hybrid, local and global arms now retrieve the way v1 `kg_query` does. Entity and relation lookups search with the embeddings of v1's ", "-joined keyword strings, produced by one batched embed call. One-hop relations are sorted by (rank, weight). KG chunks are selected per side with a working VECTOR pick. join-chunks dedups by chunk id and emits vector chunks first. Rerank receives the query.**

## Performance

- Duration: about 45 min
- Tasks: 3 of 3
- Files modified: 15 (1 created)

## Accomplishments

- **Row 1 (keywords):** v1's fallback. When both lists are empty and the query is under 50 characters, `ll = [query]`. The node emits `ll_keywords_str` and `hl_keywords_str` on both the pinned and the live branch.
- **Row 2 (embedder-query):** on the KG arms, one `client.embed` call over the non-empty members of `[query, ll_str, hl_str]`. It emits `vector`, `ll_vector` and `hl_vector`, and each is None when its string is empty. The naive arm (no keywords input) is unchanged.
- **Lookups:** `entity-lookup` reads `ll_vector` and `relation-lookup` reads `hl_vector`. When the vector is None the node returns `{"items": []}` without querying the store. The namespace constants are unchanged.
- **Rows 4-5 (entity-hydrate-expand):** `node_degree` is memoised per call. Relations are sorted by `(rank, weight)` descending with a stable sort.
- **Row 9 (chunk-sel-kg):** entity chunks are selected first. Relation candidates drop the chunk ids the entity side selected. The two lists are merged round-robin. VECTOR uses `ctx.inputs["embedder-query"]["vector"]`, with `config["query_vector"]` kept as an override, and ranks with one `score_all` filtered to the candidates.
- **Row 10 (join-chunks):** `_item_key` keys chunks by `chunk_id`, falling back to `id`.
- **base.json:** three edits, listed as edits 4-6 in the README's "Provenance and edits" section. The section now says six edits. `chunk-sel-kg` deps gain `embedder-query`. The `join-chunks` precedence is `chunk-vector-emitted-first-then-chunk-sel-kg`. `consumes_query` gains `rerank`. `tests/parity/test_arm_conformance.py` passes unchanged, and every arm's `resulting_node_id_set` is unchanged.

## TDD evidence (RED then GREEN)

- Task 1 RED (unchanged source): `4 failed, 2 passed in 0.10s`. The embed spy saw `['What did UNIQalpha Corp build in UNIQalpha City?']` only, both lookups queried the same vector, and `ll_keywords_str` was missing. GREEN: `tests/parts_core/lightrag/test_kg_retrieval_fidelity.py tests/parts_core/lightrag` gave `88 passed in 8.36s`.
- Task 2 RED: `1 failed, 6 passed in 0.10s`. The failure was `At index 0 diff: ('A', 'B') != ('A', 'D')` (unsorted relations). GREEN: `20 passed in 1.42s` over the fidelity and graph-half files.
- Task 3 RED: `4 failed, 7 passed in 0.38s`. Failures: VECTOR output `['c2', 'c1', 'c3', 'c4', 'c5']` (one concatenated pass, not two sides); WEIGHT output `['c2', 'c1', 'c3', 'c4', 'c5']`; join `['c1', 'c1', 'c4', 'c9']` (no dedup, kg first); base wiring assertions. GREEN: `tests/parts_core tests/parity tests/wirings` gave `358 passed, 3 deselected`, and `tests/seam tests/mcp tests/runner` gave `894 passed`.

## Verification

- Plan verification (`tests/parts_core tests/parity tests/wirings tests/seam tests/mcp tests/runner`): 0 failed.
- Full gate `cd databasise && .venv/bin/python tools/check_offline_suite.py`: **exit 0**, `pytest -q -rs: 1885 passed, 4 deselected` and `python -m pytest -q -rs: 1885 passed, 4 deselected`.
- Acceptance greps: `ll_vector` appears in entity_lookup.py and embedder_query.py, `hl_vector` in relation_lookup.py, `ll_keywords_str` in keywords.py, `sort` in entity_hydrate_expand.py, and `pick_method_used` and `score_all` in chunk_sel_kg.py. The `chunk-vector-emitted-first-then-chunk-sel-kg` line appears once in base.json, and the `python3 -c` base.json assertion exits 0.

## Task Commits

1. **Task 1 (tracer): KG lookups search with v1's keyword-string embeddings.** Commit `927cdba`. The tracer gate re-ran the verify suite end to end and it passed.
2. **Task 2: one-hop relations sort like v1, with one degree lookup per node.** Commit `e5edbb5`.
3. **Task 3: KG chunk selection, chunk merge and the rerank query follow v1.** Commit `6fdb0b5`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Four tests outside the plan's file list pinned the old inputs**
- **Found during:** Task 1 and Task 3
- **Issue:** `tests/parity/test_naive_arm_end_to_end.py::test_hybrid_arm_embedder_query_embeds_the_real_query_text_via_run_wiring` asserted `spy.calls == [[query]]`. `tests/parity/test_graph_arm_real_index.py` fed the lookups `{"vector": ...}` and is skip-guarded on the imported parity store.
- **Fix:** the spy now expects `[[query, "Ed Wood", "film direction"]]`, and the real-index tests pass `ll_vector` / `hl_vector`. Neither file is a protected ledger test_ref.
- **Commits:** 927cdba

**2. [Rule 1 - Bug] Relation sort compared string weights**
- **Found during:** Task 2
- **Issue:** Cozo returns edge weights as strings (`"1.0"`), so a `(rank, weight)` sort would compare them lexicographically.
- **Fix:** the sort key uses `float(weight)`, and a value that does not parse counts as 0.0. The emitted value is unchanged.
- **Commit:** e5edbb5

**3. [Rule 1 - Doc accuracy] Stale "three edits" comment in parity/run_arm.py**
- The comment cited the README's "three edits, and only these three". It now says six listed edits.
- **Commit:** 6fdb0b5

### Interpretations (D-16 "match v1" over the plan's wording)

- **Relation-chunk exclusion.** The plan says "Relation candidates exclude every entity chunk id". v1 excludes only the chunk ids the entity side selected and hydrated (operate.py:5592-5626). This implementation follows v1. The plan's fixture gives the same result either way.
- **"At least one when there are items."** v1 has no clamp: a count of 0 makes `pick_by_vector_similarity` return [], and v1 falls back to WEIGHT for that side. That is implemented as v1 does it. It only matters when `related_chunk_number * len(items) < 2`.
- **pick_method_used with two sides.** The plan names one value. Each side falls back on its own, as v1 does, so `pick_method_used` is the shared method, `"MIXED"` when the sides differ, or `"WEIGHT"` when no side had candidates. `pick_method_used_by_side` gives the detail.
- **fallback_pick_method.** Only WEIGHT exists as a fallback, as before. The body no longer reads the key, which every shipped config sets to "WEIGHT".

## Known Residual Differences (for 11-11 and the verifier)

- **v1 merges three chunk lists (vector, entity, relation) in a single round-robin** (operate.py:4783-4830). v2 merges entity and relation inside chunk-sel-kg, then join-chunks merges vector and KG. On the base (mix) wiring this interleaves in a different order than v1, for example v0, e0, v1, r0 instead of v0, e0, r0. The hybrid, local and global arms have no chunk-vector, so this does not affect them. The plan scoped it this way and the difference is not fixed here.
- **`parity/run_arm.py::_inject_query` still hardcodes `("keywords", "embedder-query", "generate")`.** Parity runs therefore do not stamp the query on rerank. Rerank is off in every shipped wiring, so no output changes. `seam/engine.py::_inject_query` reads `consumes_query` and does stamp it.
- Row 3 (`chunk_top_k` 20 vs 10) is out of scope, as the plan says.

## Known Stubs

None.

## Threat Flags

None. T-11-08 is mitigated: the counting stub proves one `node_degree` call per node.

## Next Phase Readiness

11-11 can build the KG context on this ordering. `budget-entities` and `budget-relations` now receive relations in v1's order.

## Self-Check: PASSED

- FOUND: databasise/tests/parts_core/lightrag/test_kg_retrieval_fidelity.py
- FOUND: 927cdba, e5edbb5, 6fdb0b5 (ancestors of HEAD)
