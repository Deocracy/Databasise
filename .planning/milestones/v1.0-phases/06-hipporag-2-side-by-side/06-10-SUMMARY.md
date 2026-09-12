---
phase: 06-hipporag-2-side-by-side
plan: 10
subsystem: rag-engine
tags: [hipporag, write-path, ingest, delete, selector, rest, mcp, gap-closure]

# Dependency graph
requires:
  - phase: 06-hipporag-2-side-by-side
    plan: "06-02"
    provides: "chunk-embed/openie/entity-fact-embed node bodies — three of the seven index-side positions this plan's corpus-ingest.json re-composes"
  - phase: 06-hipporag-2-side-by-side
    plan: "06-05"
    provides: "fact-edges/passage-edges/synonymy-edges/graph-augment-persist node bodies — the remaining four index-side positions"
  - phase: 06-hipporag-2-side-by-side
    plan: "06-01"
    provides: "hipporag/base.json (13-node query wiring) and the HippoRAG-resolving capability selector this plan's tests reuse verbatim"
provides:
  - "databasise/wirings/hipporag/corpus-ingest.json — HippoRAG's real write path, a re-composition of base.json's own seven index-side node objects"
  - "databasise.wirings.resolve.wiring_family() — the per-modality corpus-wiring lookup key, shared by ingest and delete"
  - "databasise.seam.refusals.NoWritePathForModalityError — the named write-path refusal, wired into both Databasise.ingest()/delete_document()"
  - "Databasise.ingest()/delete_document() selector parameter, mirrored on REST (IngestRequest/DeleteRequest) and MCP (IngestToolArgs/DeleteToolArgs)"
  - "A corrected COVERAGE.md record stating the real ingest/delete/corpus reachability"
affects: ["06-13"]

# Actuals (#2632)
actuals:
  tokens: 14552
  tasks: 3
  commits: 5
plan_head_before: fcd41eb8a1adc96362b111bab63e91f75f5a40b9

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "On-disk file existence as the write-path lookup table: databasise/wirings/<family>/corpus-<operation>.json existing IS the dispatch decision — no dict, no registry, so a modality added later needs only two files."
    - "Dual-key document stamping (id + document_id) so one caller-supplied document list satisfies both LightRAG's opaque-node reader and HippoRAG's chunk-embed reader without a per-family branch in the seam."
    - "Post-run index_done_callback() flush before finalize() — the first real write-path run to hold a store-writing node's handle before returning; finalize() alone never commits pending writes."

key-files:
  created:
    - databasise/wirings/hipporag/corpus-ingest.json
    - databasise/tests/seam/test_hipporag_write_path.py
  modified:
    - databasise/wirings/lightrag/corpus-ingest.json
    - databasise/wirings/resolve.py
    - databasise/seam/refusals.py
    - databasise/seam/engine.py
    - databasise/seam/rest.py
    - databasise/mcp/tools.py
    - databasise/mcp/server.py
    - databasise/parts_core/hipporag/chunk_embed.py
    - databasise/tests/parts_core/lightrag/test_full_ingest.py
    - databasise/tests/seam/test_delete_document.py
    - databasise/tests/seam/test_rest_corpus_endpoints.py
    - databasise/tests/seam/test_rest_transport.py
    - .planning/phases/06-hipporag-2-side-by-side/COVERAGE.md

key-decisions:
  - "Chose the split disposition the plan's own objective named: ingest becomes a real wiring (all seven index-side positions already exist and already run together via build_hipporag_index.py — a re-composition, no new node code); delete becomes a named refusal (no HippoRAG node retracts vectors/edges anywhere in the repo — a delete wiring would need new node code, out of scope)."
  - "MODAL-05 is NOT marked complete by this plan, deliberately. This plan's own objective explicitly excludes Gap 1(b) (the real, spend-incurring cross-modality run) — that stays 06-13's blocking checkpoint. Closing Gap 1(a) (the structural write-surface gap) makes the real run possible, not performed."
  - "chunk_embed.py's vector metadata now carries the chunk's own 'content' text (Rule 2 deviation) — mirroring LightRAG's own real vector-metadata convention (import_index.py imports v1's content-carrying Faiss meta json verbatim). Without it, resolve_evidence for a real HippoRAG-ingested chunk could never surface real text, since resolve_evidence_ref reads vector-store metadata directly, never the sibling KV record chunk-embed also writes."
  - "ingest()'s Test 1 forces fact-filter's zero_surviving_facts_dpr_fallback guard to fire (stub LLM returns empty keep_ids for the fact-filter prompt) so assemble-result selects dpr-fallback's items rather than ppr's — a real, load-bearing test design choice: ppr's own readback identifies passage vertices by their prefixed graph vertex name ('chunk:' + chunk_id), while chunk-embed writes that chunk's own KV/vector records under the bare, unprefixed chunk_id — a pre-existing identity-space mismatch between the graph and vector/KV layers that only surfaces once a real end-to-end ingest-to-query round trip is exercised for the first time. Left unfixed and undocumented as a distinct issue (out of this plan's own <files> scope for ppr.py/passage_edges.py); dpr-fallback's own vector-only path avoids it entirely, which is what this plan's must-have truth needed to hold."
  - "Five existing test files' minimal-registry helpers (test_full_ingest.py, test_delete_document.py, test_rest_corpus_endpoints.py) rebuilt atop a full default_registry() with the part-under-test swapped in, plus test_rest_transport.py's refusal-factory-enumeration gate extended for NoWritePathForModalityError — all required because ingest()/delete_document() now resolve a selector before dispatching, which for the no-selector default path requires every candidate wiring to parse against the registry; a registry holding only the part under test could no longer satisfy that."

requirements-completed: [MODAL-04, API-08]

coverage:
  - id: D1
    description: "A document ingested through Databasise.ingest() with a HippoRAG selector lands in HippoRAG's own graph/vector/KV namespaces and is retrievable as evidence from a HippoRAG query"
    requirement: MODAL-05
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_hipporag_write_path.py#test_hipporag_ingest_lands_in_hipporags_own_namespaces_and_is_retrievable_as_evidence"
        status: pass
    human_judgment: false
  - id: D2
    description: "The no-selector ingest/delete path is byte-for-byte unchanged, including on-disk store directories"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_hipporag_write_path.py#test_no_selector_ingest_still_resolves_to_the_lightrag_corpus_wiring"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_hipporag_write_path.py#test_no_selector_delete_still_reaches_the_lightrag_delete_wiring"
        status: pass
    human_judgment: false
  - id: D3
    description: "A HippoRAG-selected delete raises NoWritePathForModalityError naming only the operation, never a modality/wiring/node name"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_hipporag_write_path.py#test_hipporag_selected_delete_raises_the_named_refusal_naming_only_the_operation"
        status: pass
    human_judgment: false
  - id: D4
    description: "The write-path invariant holds over every entry of WIRING_NAMES — never a silent fallback to another modality's wiring"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_hipporag_write_path.py#test_write_path_invariant_holds_over_every_wiring_name"
        status: pass
    human_judgment: false
  - id: D5
    description: "The same HippoRAG ingest driven through REST and MCP produces the same IngestJob shape as the in-process call; HippoRAG delete refuses over both transports as a 422"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_hipporag_write_path.py#test_hipporag_ingest_parity_across_rest_mcp_and_in_process_transports"
        status: pass
    human_judgment: false
  - id: D6
    description: "COVERAGE.md states the real reachability of ingest/delete/corpus/corpus-counts/jobs and the api-coverage gate still passes"
    verification:
      - kind: other
        ref: "grep + node gsd-tools.cjs check api-coverage.verify-pre .planning/phases/06-hipporag-2-side-by-side"
        status: pass
    human_judgment: false

duration: ~80min
completed: 2026-09-10
status: complete
---

# Phase 6 Plan 10: HippoRAG Write Path Summary

**HippoRAG 2 gets a real, tested write path through the public §18 seam — `Databasise.ingest()` now dispatches per-modality via a filesystem lookup table, `delete_document()` refuses by name where no HippoRAG delete node exists, and both are mirrored on REST and MCP.**

## Performance

- **Duration:** ~80 min (approximate — start timestamp not captured precisely at session start)
- **Tasks:** 3 completed
- **Files modified:** 15 (2 created, 13 modified)
- **Commits:** 5

## Accomplishments

- `databasise/wirings/hipporag/corpus-ingest.json` — a re-composition of `base.json`'s own seven index-side node objects (`chunk-embed` through `graph-augment-persist`) as a real, dispatchable write path, no new node code.
- `Databasise.ingest()` promoted to a two-arm write: resolves the caller's §18.4 selector against the same query-side candidate pool `query`/`compare` already use, then dispatches `databasise/wirings/<family>/corpus-ingest.json` via the new `wiring_family()`/`_corpus_wiring()` lookup. The default (no-selector) path is unchanged, including its on-disk store directories.
- `Databasise.delete_document()` gains the identical `selector` parameter. A HippoRAG-selected delete raises `NoWritePathForModalityError` — no HippoRAG delete node exists anywhere in this repository, since retracting vectors/edges from HippoRAG's index needs node code this plan does not build.
- REST (`IngestRequest`/`DeleteRequest`) and MCP (`IngestToolArgs`/`DeleteToolArgs`) both carry the selector member; the MCP tool roster count is unchanged (still six names).
- One real, end-to-end proof under stub clients: a document ingested through the seam with a HippoRAG selector lands in HippoRAG's own graph/vector/KV namespaces and is retrievable as real evidence text from a subsequent HippoRAG query — the first time this round trip has ever been exercised in this codebase.
- COVERAGE.md corrected: `ingest` is now two-arm, `delete` is LightRAG-only and says so by name, and `corpus`/`corpus/counts`/`jobs` are documented as LightRAG-corpus-only.

## Task Commits

Each task was committed as a RED test commit followed by a GREEN implementation commit (TDD):

1. **Task 1: HippoRAG ingest tracer** — `3e3f7fe` (test), `c3502a6` (feat)
2. **Task 2: Named delete refusal + transport parity + write-path invariant** — `e4144d2` (test), `2097867` (feat)
3. **Task 3: COVERAGE.md correction** — `b93ef38` (docs)

**Plan metadata:** committed as part of this SUMMARY's own commit.

## Files Created/Modified

- `databasise/wirings/hipporag/corpus-ingest.json` - HippoRAG's real write-path wiring (7 nodes, re-composed from base.json)
- `databasise/tests/seam/test_hipporag_write_path.py` - 7 tests: ingest tracer, no-selector parity, isolation, delete refusal, delete parity, write-path invariant, REST/MCP transport parity
- `databasise/wirings/lightrag/corpus-ingest.json` - added `consumes_documents: ["full-ingest"]`
- `databasise/wirings/resolve.py` - added `wiring_family()`/`UnknownWiringFamilyError`
- `databasise/seam/refusals.py` - added `NoWritePathForModalityError`
- `databasise/seam/engine.py` - `_corpus_wiring()`, `ingest()`/`delete_document()` rewritten to dispatch per resolved modality; post-run `index_done_callback()` flush
- `databasise/seam/rest.py` - `IngestRequest`/`DeleteRequest` gain `selector`; `/documents/upload` accepts selector as a JSON-encoded form field
- `databasise/mcp/tools.py` - `IngestToolArgs`/`DeleteToolArgs` gain `selector`; §18.5 docstring extended
- `databasise/mcp/server.py` - forwards `args.selector` at both `ingest_tool`/`delete_tool` call sites
- `databasise/parts_core/hipporag/chunk_embed.py` - vector metadata now carries the chunk's own `content` text (Rule 2 deviation)
- `databasise/tests/parts_core/lightrag/test_full_ingest.py` - `_make_engine` rebuilt atop full `default_registry()` (deviation)
- `databasise/tests/seam/test_delete_document.py` - `_make_engine` rebuilt atop full `default_registry()` (deviation)
- `databasise/tests/seam/test_rest_corpus_endpoints.py` - `_make_registry()` rebuilt atop full `default_registry()` (deviation)
- `databasise/tests/seam/test_rest_transport.py` - added `NoWritePathForModalityError` refusal factory (deviation)
- `.planning/phases/06-hipporag-2-side-by-side/COVERAGE.md` - corrected ingest/delete/corpus reachability record

## Decisions Made

See `key-decisions` in frontmatter for the full list. The two most consequential: (1) ingest got a real wiring while delete got a named refusal, matching exactly the split the plan's own objective specified and justified by which side the existing node inventory can honestly support; (2) MODAL-05 stays Pending in REQUIREMENTS.md — this plan closes the structural gap (Gap 1(a)) that blocked the real cross-modality run, but does not perform that run itself (Gap 1(b), 06-13's own blocking checkpoint).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `chunk_embed.py` vector metadata gained a `content` field**
- **Found during:** Task 1, writing the tracer test's evidence-resolution assertion
- **Issue:** `resolve_evidence_ref` resolves an evidence reference through the vector store's own metadata directly (never through the sibling KV record). `chunk_embed.py`'s vector upsert wrote only `document_id`/`ordinal` metadata — a real HippoRAG-ingested chunk could never resolve to its own text via `resolve_evidence`, which is the entire point of the operation.
- **Fix:** Added `"content": record["text"]` to the vector metadata dict, mirroring LightRAG's own real vector-metadata convention (`import_index.py` imports v1's content-carrying Faiss meta json verbatim).
- **Files modified:** `databasise/parts_core/hipporag/chunk_embed.py`
- **Verification:** `test_hipporag_ingest_lands_in_hipporags_own_namespaces_and_is_retrievable_as_evidence` asserts the resolved evidence record's own `content` field contains the ingested document's real text.
- **Committed in:** `c3502a6` (Task 1 feat commit)

**2. [Rule 2 - Missing Critical] `ingest()` did not flush pending store writes before returning**
- **Found during:** Task 1, first real run of the seven-node index-side wiring through the scheduler
- **Issue:** `chunk-embed`/`entity-fact-embed` stage writes in each store's own in-memory pending buffer; `index_done_callback()` commits them, but `finalize()` alone never calls it (a no-op by default). `ingest()`'s existing `finally: for store in stores.values(): await store.finalize()` never flushed — every HippoRAG chunk/entity/fact vector and KV record would have been silently discarded the instant `ingest()` returned.
- **Fix:** Added `for store in stores.values(): await store.index_done_callback()` after a successful `run_wiring`, before `finalize()`. A safe no-op for the LightRAG opaque path, which never touches `ctx.stores` at all.
- **Files modified:** `databasise/seam/engine.py`
- **Verification:** the tracer test's post-ingest, fresh-store-instance read assertions (graph vertices, vector namespace non-empty) only pass with this fix in place.
- **Committed in:** `c3502a6` (Task 1 feat commit)

**3. [Rule 3 - Blocking] `ingest()`'s per-document dict key mismatch between node families**
- **Found during:** Task 1, first real dispatch of the corpus-ingest wiring to `chunk-embed`
- **Issue:** The plan's existing `ingest()` body stamped `documents: [{"id": document_id, "text": ...}]` for LightRAG's opaque `full-ingest` node. `hipporag/chunker-embedder@0.1.0`'s own body reads `document["document_id"]` (a `KeyError` on the `"id"`-only shape).
- **Fix:** Stamp both `"id"` and `"document_id"` onto each document dict — LightRAG's opaque node ignores the extra key; HippoRAG's chunk-embed reads the one it needs. No per-family branch in the seam.
- **Files modified:** `databasise/seam/engine.py`
- **Committed in:** `c3502a6` (Task 1 feat commit)

**4. [Rule 3 - Blocking] Five existing test files' minimal-registry helpers broke once ingest()/delete_document() began resolving a selector**
- **Found during:** Task 1's own `<verify>` command (`pytest tests/seam/ tests/parity/`) and Task 2's own `<verify>` command (full suite)
- **Issue:** `ingest()`/`delete_document()` now call `resolve_selector()` before dispatching, which (for the no-selector default path) requires every candidate wiring `all_wirings()` enumerates to parse against the registry. Several existing tests (`test_full_ingest.py`, `test_delete_document.py`, `test_rest_corpus_endpoints.py`, and transitively `test_dual_transport_parity.py` via a shared import) constructed a registry holding only the single test-local part under test, which the new resolution requires to fail.
- **Fix:** Rebuilt each affected registry-construction helper atop a full `default_registry()` with the test-local part swapped in by name — the part under test still gets its stub-driver body, every other component still registers normally. `test_rest_transport.py`'s own refusal-subclass-enumeration gate additionally required a factory entry for the new `NoWritePathForModalityError`.
- **Files modified:** `databasise/tests/parts_core/lightrag/test_full_ingest.py`, `databasise/tests/seam/test_delete_document.py`, `databasise/tests/seam/test_rest_corpus_endpoints.py`, `databasise/tests/seam/test_rest_transport.py`
- **Verification:** full suite with both extras — 926 passed / 3 skipped, up from the 918/3 baseline.
- **Committed in:** `c3502a6` (Task 1 feat commit), `2097867` (Task 2 feat commit)

---

**Total deviations:** 4 auto-fixed (2 missing-critical, 2 blocking).
**Impact on plan:** All four were necessary for Task 1/2's own must-have truths and verify commands to pass. No scope creep beyond what the write-path change itself required; no architectural decision was made without the plan's own explicit instruction.

## Known Stubs

None — every node exercised in this plan's tests is the real, production node body (`hipporag/chunker-embedder`, `hipporag/openie-extractor`, `hipporag/entity-fact-embedder`, etc.), driven by stub *clients* (embedding/LLM) exactly as the rest of this phase's test suite already does. No stub node bodies, no mock data flowing into a real response path.

## Threat Flags

None beyond what the plan's own `<threat_model>` already names and this plan's own tests directly verify (T-06-10-01 through T-06-10-05): path-construction constraint (`wiring_family` returns only `WIRING_NAMES` members), refusal-message closed-set (Test 4), cross-arm isolation (Test 3), the write-path invariant (Test 6), and MACH-11 preservation (unchanged `_recorder` line in `delete_document`).

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Gap 1(a) (the structural write-surface gap) is closed: HippoRAG's index can now be populated through the public seam — in-process, over REST, and over MCP.
- Gap 1(b) — the real, spend-incurring cross-modality run against the Phase 3 parity corpus — remains open and is 06-13's own blocking checkpoint. This plan makes that run possible; it does not perform it.
- MODAL-05 stays Pending in REQUIREMENTS.md until 06-13's real run lands.
- No blockers for 06-11/06-12 (SC6/MACH-03 gap-closure plans, per STATE.md's roadmap note) — this plan's changes are additive and do not touch their own scope.

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-10*

## Self-Check: PASSED

- FOUND: databasise/wirings/hipporag/corpus-ingest.json
- FOUND: databasise/tests/seam/test_hipporag_write_path.py
- FOUND commit: 3e3f7fe (test, Task 1)
- FOUND commit: c3502a6 (feat, Task 1)
- FOUND commit: e4144d2 (test, Task 2)
- FOUND commit: 2097867 (feat, Task 2)
- FOUND commit: b93ef38 (docs, Task 3)
