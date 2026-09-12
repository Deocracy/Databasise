---
phase: 06-hipporag-2-side-by-side
plan: 02
subsystem: rag-engine
tags: [hipporag, openie, chunking, embedding, faiss, sqlite, wiring, tdd]

# Dependency graph
requires:
  - phase: 06-hipporag-2-side-by-side
    plan: "06-01"
    provides: "the HippoRAG base wiring, HIPPORAG_PARTS registration pattern, the store_namespaces/consumes_query/evidence_position seam couplings, and reset-vector-join's own expectation of a per-fact `entities` field"
provides:
  - "Three registered executable HippoRAG 2 index-side parts: hipporag/chunker-embedder@0.1.0 (chunk-embed), hipporag/openie-extractor@0.1.0 (openie), hipporag/entity-fact-embedder@0.1.0 (entity-fact-embed)"
  - "The HippoRAG base wiring grown from 5 to 8 nodes (docs/system-model/wirings/hipporag-base.json's 13-position table, first 3 of the 7 index-side positions landed)"
  - "seeded_hipporag_source_documents fixture (three short documents with overlapping entities) for 06-05's shared-entity graph-construction tests"
  - "ENTITY_VERTEX_PREFIX/CHUNK_VERTEX_PREFIX constants (entity_fact_embed.py) — the vertex-ref identity space 06-05's graph-construction nodes import rather than re-spell"
affects: [06-05, 06-07, 06-09]

# Actuals (#2632)
actuals:
  tokens: 12334
  tasks: 3
  commits: 6
plan_head_before: 1ad326b9fcb2574457465c7603864b670d88a1fd

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Per-task TDD RED/GREEN commit pairs within a single execute-type plan: a deliberately wrong stub body (ignoring config/inputs, making zero client calls) lands in the test(...) commit so the target tests fail on real assertions rather than a collection error, then the real body replaces it in the feat(...) commit"
    - "Sum-of-TokenAccounting helper (_sum_token_accountings) for nodes making more than one client call per dispatch: sums prompt/completion/cached_read/call_count fields, propagates the unbudgetable sentinel if any individual call carried it, otherwise inherits the first call's counted_by"

key-files:
  created:
    - databasise/parts_core/hipporag/chunk_embed.py
    - databasise/parts_core/hipporag/openie.py
    - databasise/parts_core/hipporag/entity_fact_embed.py
    - databasise/tests/parts_core/hipporag/test_index_side_extraction.py
  modified:
    - databasise/parts_core/hipporag/__init__.py
    - databasise/wirings/hipporag/base.json
    - databasise/tests/parts_core/hipporag/conftest.py
    - databasise/tests/parts_core/hipporag/test_registration.py
    - databasise/tests/parts/test_registry.py

key-decisions:
  - "chunk-embed's chunker is a deterministic, dependency-free sliding-window character splitter (1200/100 defaults) — a stand-in with the same input/output shape, not HippoRAG's own upstream chunker, since the real algorithm lives inside the still-opaque, quarantined index-side chain this node is one position of. Only the SHA-256(document_id:ordinal) chunk-id determinism and the batched-embed/store-write contract are load-bearing for this plan's own acceptance criteria."
  - "openie's malformed-triple-response handling fails open per-chunk (drops only that chunk's findings, never aborts the dispatch) — mirrors keywords.py/fact_filter.py's own established graceful-degradation precedent rather than inventing a new failure mode."
  - "entity-fact-embed's fact vector metadata carries both chunk_ids and the fact's own entity refs directly, rather than only what Task 3's literal action text named (chunk_ids alone) — the entities field is what reset-vector-join.py (06-01) already reads off each scored fact item to accumulate phrase weight onto graph vertices; omitting it would leave reset-vector-join's own read with nothing to consume from this plan's writes."
  - "Registered wiring nodes carry no `note` field, unlike the illustrative docs/system-model/wirings/hipporag-base.json's own copy — WiringNode's schema (parts/schema.py, `extra='forbid'`) does not permit an undeclared key. Caught during the first full-suite verify (WiringRefusedError cascading into the seam cross-modality tests) and fixed before landing; recorded here since a future position added to this wiring will hit the same refusal if it copies a `note` field from the governing docs copy."

requirements-completed: [MODAL-04]

coverage:
  - id: D1
    description: "The chunk-embed -> openie -> entity-fact-embed chain lands chunk vectors in hipporag-chunks, chunk text in hipporag-text-chunks, and entity/fact vectors in hipporag-entities/hipporag-facts"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/parts_core/hipporag/test_index_side_extraction.py#test_full_chain_dispatch_has_bounded_embed_calls_and_matching_fact_ids"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_index_side_extraction.py#test_chunk_embed_writes_chunk_vectors_and_text_for_three_documents"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_index_side_extraction.py#test_entity_fact_embed_writes_four_entities_and_three_facts_never_chunks"
        status: pass
    human_judgment: false
  - id: D2
    description: "openie makes two LLM calls per chunk (NER, then triple extraction) as one fused operation, the second call carrying that chunk's own NER result"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/parts_core/hipporag/test_index_side_extraction.py#test_openie_makes_exactly_two_calls_per_chunk_ner_then_triples"
        status: pass
    human_judgment: false
  - id: D3
    description: "Dispatched with no documents/chunks configured, each index-side node makes zero client calls and returns an empty result"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/parts_core/hipporag/test_index_side_extraction.py#test_chunk_embed_makes_zero_calls_with_no_documents_configured"
        status: pass
      - kind: unit
        ref: "tests/parts_core/hipporag/test_index_side_extraction.py#test_openie_makes_zero_calls_with_empty_chunks_input"
        status: pass
    human_judgment: true
    rationale: "chunk-embed and openie's zero-call paths are each directly unit-tested; entity-fact-embed's own zero-findings short-circuit (`if not findings: return {...}` before any client is touched) is implemented identically but has no dedicated unit test in this plan — verified only by code inspection, not an executed assertion."
  - id: D4
    description: "Token spend from every LLM/embedding call in this chain reaches the run record through the TokenAccounting channel, never a fabricated zero"
    requirement: MODAL-04
    verification:
      - kind: unit
        ref: "tests/parts_core/hipporag/test_index_side_extraction.py#test_chunk_embed_reports_the_embedding_clients_own_token_accounting"
        status: pass
    human_judgment: true
    rationale: "chunk-embed's single-call token passthrough is directly asserted. openie's and entity-fact-embed's own _sum_token_accountings summation (multiple calls per dispatch, unbudgetable-sentinel propagation) is implemented and exercised indirectly by the passing behavior tests, but no test asserts the summed TokenAccounting's own field values for either node — a human/code review confirms the logic, not an executed value assertion."

# Metrics
duration: ~70 min
completed: 2026-09-09
status: complete
---

# Phase 6 Plan 2: HippoRAG 2 Index-Side Extraction (chunk-embed, openie, entity-fact-embed) Summary

**Three of HippoRAG 2's seven index-side node positions now run as registered, TDD-built parts — a deterministic chunker-and-embedder, a fused two-call OpenIE extractor, and a two-namespace entity/fact embedder — proven end to end by a chain test over three overlapping-entity documents, growing the HippoRAG base wiring from 5 to 8 nodes.**

## Performance

- **Duration:** ~70 min
- **Completed:** 2026-09-09
- **Tasks:** 3 (each RED → GREEN, no REFACTOR commits needed)
- **Files created/modified:** 9

## Accomplishments

- `databasise/parts_core/hipporag/chunk_embed.py`: `hipporag/chunker-embedder@0.1.0` — a deterministic sliding-window chunker fused with one batched embedding call, SHA-256(document_id:ordinal) stable chunk ids, writes to `hipporag-chunks` (vector) and `hipporag-text-chunks` (KV); zero calls on an unconfigured dispatch
- `databasise/parts_core/hipporag/openie.py`: `hipporag/openie-extractor@0.1.0` — per-chunk NER-then-triple-extraction as one fused two-call operation, `_NER_PROMPT`/`_TRIPLE_PROMPT` carried inside the component, malformed triple responses degrade only their own chunk, `fact_id` = SHA-256 of the canonicalised triple so the same fact from two chunks collapses to one id
- `databasise/parts_core/hipporag/entity_fact_embed.py`: `hipporag/entity-fact-embedder@0.1.0` — dedupes entities/facts, two batched embed calls (never one per item), writes `hipporag-entities`/`hipporag-facts`, defines `ENTITY_VERTEX_PREFIX`/`CHUNK_VERTEX_PREFIX` for 06-05's graph-construction nodes to import
- HippoRAG base wiring (`databasise/wirings/hipporag/base.json`) grown from 5 to 8 nodes; parses clean against `default_registry()` with zero violations
- `seeded_hipporag_source_documents` fixture: three short documents whose entities ("cat", "mat", "rug") overlap, for 06-05's shared-entity edge cases
- Full chain proven: `chunk-embed` → `openie` → `entity-fact-embed` over the seeded documents, with bounded embed calls (1 batched call at chunk-embed, 2 at entity-fact-embed — never one per item) and `hipporag-facts` holding exactly the fact ids `openie` emitted
- Full suite: 702 passed, 13 skipped (bare) — exactly the 688/13 Phase-6-Plan-1 baseline plus this plan's 14 new tests, zero regressions

## Task Commits

Each task followed RED → GREEN (TDD, no REFACTOR needed — the GREEN implementation needed no follow-up cleanup):

1. **Task 1: chunk-embed** — RED `cf0b903` (test), GREEN `be4eec2` (feat)
2. **Task 2: openie** — RED `9fb4593` (test), GREEN `99ab87d` (feat)
3. **Task 3: entity-fact-embed** — RED `45749fd` (test), GREEN `2cb6be7` (feat, includes the two Rule-3 pinned-count fixes)

_No REFACTOR commits — each GREEN implementation was already clean once passing._

## TDD Gate Compliance

All three tasks (`type="auto" tdd="true"`) followed RED → GREEN:

- **Task 1 RED (`cf0b903`):** `chunk_embed.py` committed with a stub body that unconditionally returns `{"chunks": []}`, ignoring `config["documents"]`. Verified via `uv run pytest -q tests/parts_core/hipporag/test_index_side_extraction.py -k chunk_embed`: **3 of 4 target tests failed on real assertions** (`assert []` where 3 chunks expected; `KeyError: 'tokens'` where a populated `TokenAccounting` was expected) — genuine RED evidence, not a collection error.
- **Task 1 GREEN (`be4eec2`):** real chunking/embedding/store-write logic restored; all 4 target tests pass.
- **Task 2 RED (`9fb4593`):** `openie.py` committed with a stub body that unconditionally returns `{"findings": []}` and never calls the LLM client. Verified: **3 of 4 target tests failed** (`0 == 4` calls, `0 == 1` findings) — genuine RED.
- **Task 2 GREEN (`99ab87d`):** real NER-then-triples call logic restored; all 4 target tests pass.
- **Task 3 RED (`45749fd`):** `entity_fact_embed.py` committed with a stub body that unconditionally returns `{"entities": [], "facts": []}` and never calls the embedding client. Verified: **5 of 6 target tests failed** (0 entities/facts vs. expected counts; 1 embed call vs. 3 across the chain) — genuine RED.
- **Task 3 GREEN (`2cb6be7`):** real dedup/embed/store-write logic restored; all 14 tests in the file pass, plus the full suite (702 passed/13 skipped) and the two Rule-3 pinned-count fixes.
- **Tool note:** `gsd_run check tdd-red-evidence` is TAP/Node-test-runner-oriented and does not natively parse pytest's default output format for this Python project (same finding recorded in 06-01-SUMMARY.md); RED evidence was verified manually via pytest's own exit code and per-test failure attribution instead of running that tool mechanically.

## Files Created/Modified

- `databasise/parts_core/hipporag/chunk_embed.py` - `hipporag/chunker-embedder@0.1.0`
- `databasise/parts_core/hipporag/openie.py` - `hipporag/openie-extractor@0.1.0`
- `databasise/parts_core/hipporag/entity_fact_embed.py` - `hipporag/entity-fact-embedder@0.1.0`
- `databasise/tests/parts_core/hipporag/test_index_side_extraction.py` - 14 tests covering all three tasks' `<behavior>` blocks plus the chain test
- `databasise/parts_core/hipporag/__init__.py` - `HIPPORAG_PARTS` grown from 5 to 8 members
- `databasise/wirings/hipporag/base.json` - `chunk-embed`/`openie`/`entity-fact-embed` nodes added (8 nodes total)
- `databasise/tests/parts_core/hipporag/conftest.py` - `seeded_hipporag_source_documents` fixture
- `databasise/tests/parts_core/hipporag/test_registration.py` - pinned shape table/count updated 5 → 8 members
- `databasise/tests/parts/test_registry.py` - pinned registry count updated 27 → 30

## Decisions Made

See `key-decisions` in frontmatter. Most load-bearing: entity-fact-embed's fact vector metadata carries the fact's own entity refs (not just `chunk_ids`) so 06-01's already-committed `reset_vector_join.py` — which reads `fact.get("entities")` off each scored fact item — has something real to consume from this plan's writes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed the invalid `note` field from registered wiring nodes**
- **Found during:** Task 1's first full-suite verify (before the RED/GREEN split was finalized)
- **Issue:** The plan's action text for Tasks 1 and 2 names a `note` field the governing `docs/system-model/wirings/hipporag-base.json` copy carries for each node, and the first draft of `databasise/wirings/hipporag/base.json`'s new nodes copied it. `WiringNode`'s schema (`databasise/parts/schema.py`, `model_config = ConfigDict(extra="forbid")`) does not permit an undeclared key, so this raised `WiringRefusedError` at parse time — cascading into `tests/seam/test_cross_modality_run.py`'s two HippoRAG query tests (both failed with the same refusal before the fix).
- **Fix:** Dropped `note` from the `chunk-embed`/`openie` nodes, matching the 5 pre-existing nodes' own convention (none of them carries a `note` field in the *registered* wiring, only in the illustrative `docs/system-model/` copy).
- **Files modified:** `databasise/wirings/hipporag/base.json`
- **Verification:** `parse_wiring` reports `ok: True` with zero violations; both previously-failing `test_cross_modality_run.py` tests pass again.
- **Committed in:** `be4eec2` (the field was never present in any committed state — caught and fixed before the first commit landed)

**2. [Rule 3 - Blocking] Two pre-existing pinned-count tests updated to their new correct values**
- **Found during:** Task 3's full-suite verify step
- **Issue:** `tests/parts/test_registry.py` asserted exactly 27 registered parts; `tests/parts_core/hipporag/test_registration.py` asserted exactly 5 `HIPPORAG_PARTS` members with a hand-written shape table. Adding this plan's own three new parts (its explicit goal) makes both stale assertions fail.
- **Fix:** Updated both assertions/tables to the new correct counts (30, 8), extended `test_registration.py`'s `_EXPECTED_SHAPE` with the three new parts' pinned `kind`/`effects`/`structural_depth`, and updated docstrings/test names accordingly — mirroring 06-01-SUMMARY.md's own precedent for this exact class of fix.
- **Files modified:** `databasise/tests/parts/test_registry.py`, `databasise/tests/parts_core/hipporag/test_registration.py`
- **Verification:** Full suite green (702 passed, 13 skipped).
- **Committed in:** `2cb6be7`

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both necessary for correctness/consistency; no scope creep. The wiring-schema fix corrects a literal copy from the governing (illustrative-only) document that the registered wiring's own stricter schema does not accept; the pinned-count fix is a direct, expected consequence of this plan's own additions.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Three of HippoRAG 2's seven index-side positions (`chunk-embed`, `openie`, `entity-fact-embed`) are registered, tested and wired — plan 06-05 can add the remaining four (`fact-edges`, `passage-edges`, `synonymy-edges`, `graph-augment-persist`) onto this same `databasise/wirings/hipporag/base.json` file, importing `ENTITY_VERTEX_PREFIX`/`CHUNK_VERTEX_PREFIX` from `entity_fact_embed.py` rather than re-spelling the vertex-ref prefixes.
- `entity-fact-embed`'s fact vector metadata carries `chunk_ids` directly (not via a KV `fact:<id>` record) — this differs from 06-01's already-committed `reset_vector_join.py`, which reads the per-fact chunk association from the KV store under that key. The two are not yet reconciled: a real end-to-end run from `chunk-embed` through `reset-vector-join` would need either `entity-fact-embed` to also write the `fact:<id>` KV record, or `reset-vector-join` to read `chunk_ids` off the fact vector's own metadata instead. Left unresolved for 06-05/06-07 to settle, since neither this plan's `<files>` nor its acceptance criteria touch `reset_vector_join.py`.
- `entity-fact-embed`'s zero-findings short-circuit (D3's `human_judgment: true` coverage entry) and both new nodes' summed-`TokenAccounting` correctness (D4's `human_judgment: true` coverage entry) are implemented but not independently unit-tested with dedicated assertions — flagged for a verifier's judgment rather than silently claimed as auto-passing.

## Self-Check: PASSED

- All `key-files.created` verified present on disk.
- `git log --oneline --all | grep -E "cf0b903|be4eec2|9fb4593|99ab87d|45749fd|2cb6be7"` returns all six commits.
- Every task's `<acceptance_criteria>` re-verified: `HIPPORAG_CHUNKER_EMBEDDER_PART.effects == ["calls_embedding", "writes_vector", "writes_kv"]`; `HIPPORAG_PARTS` has 8 members and `default_registry()` resolves all 8 `hipporag/` names; `chunk-embed` node's `deps == []`; `_NER_PROMPT`/`_TRIPLE_PROMPT` defined as module constants; `HIPPORAG_OPENIE_EXTRACTOR_PART.effects == ["calls_llm"]`; `openie` node's `deps == ["chunk-embed"]`; `entity_fact_embed.py` defines `ENTITY_VERTEX_PREFIX`/`CHUNK_VERTEX_PREFIX` at module level; chain test asserts `hipporag-facts` holds exactly `openie`'s own fact ids.
- Plan-level `<verification>`: `cd databasise && uv run pytest -q` exits 0 (702 passed, 13 skipped); `uv run python -m databasise.tools.check_import_boundary` exits 0; HippoRAG base wiring declares 8 nodes and parses clean against `default_registry()` (`report.ok == True`, zero violations).

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-09*
