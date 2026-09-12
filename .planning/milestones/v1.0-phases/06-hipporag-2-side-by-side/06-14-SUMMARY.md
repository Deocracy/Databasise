---
phase: 06-hipporag-2-side-by-side
plan: 14
subsystem: rag-modality-fitting
tags: [hipporag, wirings, openai-compat, embedding-client, gap-closure]

# Dependency graph
requires:
  - phase: 06-hipporag-2-side-by-side
    provides: "06-10's committed corpus-ingest.json wiring, 06-13's real-run refusal evidence naming the fact-score empty-string defect"
provides:
  - "load_wiring's variant keyword — the index-side/query-side wiring lookup generalized to any <wiring_name>/<variant>.json on disk"
  - "build_hipporag_index.build_index dispatching only HippoRAG's seven index-side positions"
  - "EmptyEmbeddingInputError — a named refusal at OpenAICompatibleClient.embed for any empty or whitespace-only batch item, before any provider request is constructed"
  - "WINDOWS.md entry id 3 closed as fixed"
affects: ["06-15 (the re-attempted real cross-modality run)", "any future client callsite reaching OpenAICompatibleClient.embed"]

actuals:
  tokens: 5892
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "wiring variant lookup: <wiring_name>/<variant>.json on disk is the lookup table (mirrors Databasise.ingest's _corpus_wiring convention), never a registry dict"
    - "one named refusal at the single client method every callsite routes through, rather than per-caller guards"

key-files:
  created:
    - databasise/tests/parity/test_build_hipporag_index.py
  modified:
    - databasise/wirings/resolve.py
    - databasise/parity/build_hipporag_index.py
    - databasise/clients/openai_compat.py
    - databasise/tests/clients/test_openai_compat.py
    - .planning/WINDOWS.md

key-decisions:
  - "Read the index-build stamping target off the resolved wiring's own consumes_documents[0], mirroring Databasise.ingest()'s already-shipped convention, rather than a module constant"
  - "Guard OpenAICompatibleClient.embed itself (the one method all seven embedding call sites route through) rather than each call site individually"
  - "The synthetic test corpus (2-3 short documents, monkeypatched over load_snapshot) proves the harness's own dispatch logic without touching the real 20-document fixture or any live provider"

patterns-established:
  - "A wiring's on-disk directory layout (<family>/<variant>.json) is the lookup table for which positions a given operation dispatches — no registry duplicates it"

requirements-completed: []

coverage:
  - id: D1
    description: "A HippoRAG index build dispatches only the seven index-side node positions -- no query-side node (fact-score, reset-vector-join, dpr-fallback, fact-filter, ppr, assemble-result) ever reaches the scheduler at index time"
    requirement: "MODAL-05"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_build_hipporag_index.py#test_2_the_corpus_ingest_wirings_node_ids_are_disjoint_from_the_base_wirings_query_side_positions"
        status: pass
      - kind: unit
        ref: "databasise/tests/parity/test_build_hipporag_index.py#test_3_fact_score_has_empty_deps_and_run_arms_own_inject_query_never_stamps_a_base_wiring_query_side_node"
        status: pass
    human_judgment: false
  - id: D2
    description: "A real-shaped HippoRAG index build completes end to end (partial=False, degraded=False, every count non-zero) against a client double that would fail the build the instant it received an empty/whitespace-only embedding input"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_build_hipporag_index.py#test_1_a_hipporag_index_build_completes_end_to_end_against_a_client_double_that_refuses_empty_input"
        status: pass
    human_judgment: false
  - id: D3
    description: "OpenAICompatibleClient.embed refuses an empty batch, a zero-length item, or a whitespace-only item by name, before any provider request is constructed, naming the offending zero-based index"
    requirement: "API-08"
    verification:
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_11_embed_handed_a_zero_length_string_raises_before_reaching_the_provider"
        status: pass
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_12_embed_handed_a_whitespace_only_string_raises_the_same_error"
        status: pass
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_13_embed_handed_an_empty_list_raises_the_same_error"
        status: pass
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_14_the_raised_error_names_the_offending_batch_index_as_a_reachable_attribute"
        status: pass
    human_judgment: false
  - id: D4
    description: "embed()'s good path (ordinary non-empty strings) is unchanged -- the guard adds no behavior on a well-formed batch"
    verification:
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py#test_15_embed_handed_ordinary_non_empty_strings_still_reaches_the_provider_unchanged"
        status: pass
    human_judgment: false
  - id: D5
    description: "WINDOWS.md entry id 3 closed as fixed via the ledger tool, open_count 0"
    verification:
      - kind: other
        ref: "grep -c '\"open_count\": 0' .planning/WINDOWS.md"
        status: pass
    human_judgment: false

duration: ~40min
completed: 2026-09-10
status: complete
---

# Phase 06 Plan 14: Fact-Score Root-Cause Fix — Index-Side Wiring Swap and a Named Empty-Embedding Refusal Summary

**Swapped HippoRAG's index build onto the already-committed seven-position corpus-ingest wiring and added one named `EmptyEmbeddingInputError` refusal at `OpenAICompatibleClient.embed` — closing WINDOWS.md entry id 3, the empty-string provider 400 that refused 06-13 Task 1's real index build.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2
- **Files modified:** 5 (1 created)

## Accomplishments

- `load_wiring` gained an optional `variant` keyword (default `"base"`), reading `<wiring_name>/<variant>.json` — additive, every existing caller (including `all_wirings()`) unchanged
- `build_hipporag_index.build_index` now resolves HippoRAG's seven-position `corpus-ingest` wiring instead of the thirteen-position base wiring; verified the two wirings' `store_namespaces` are byte-equal (the plan's own precondition) before making the swap, so an index built through the new path lands in the exact directories the query side already reads
- `_inject_documents` reads its stamping target off the resolved wiring's own `consumes_documents[0]`, mirroring `Databasise.ingest()`'s already-shipped convention, replacing the removed `_CHUNK_EMBED_NODE_ID` module constant
- Added `EmptyEmbeddingInputError` to `OpenAICompatibleClient.embed` — one guard at the single method all seven embedding call sites route through, refusing an empty batch or any whitespace-only/zero-length item before any provider request is constructed, naming the offending index
- Closed `.planning/WINDOWS.md` entry id 3 via `gsd-tools windows fixed 3` (the ledger tool, never hand-edited)

## Precondition Check (Task 1)

`databasise/wirings/hipporag/corpus-ingest.json`'s `store_namespaces` is `{"kv": "hipporag-text-chunks", "graph": "hipporag-graph"}` — byte-identical to `base.json`'s own declaration. Confirmed by direct file comparison before editing, and re-confirmed by the `<verify>` one-liner (`b['store_namespaces']==i['store_namespaces']` → `True`). The swap does not change which on-disk directories an index build writes to or the query side reads from.

## Task Commits

1. **Task 1: End-to-end — a HippoRAG index build completes against a client double that refuses the exact input that killed the real run** - `7b5a3df` (feat)
2. **Task 2: One named refusal at the single method every embedding caller routes through, and the ledger entry closed** - `9c4694c` (feat, TDD: tests 11-15 written RED — `ImportError: cannot import name 'EmptyEmbeddingInputError'` — then implemented GREEN, single commit per house convention)

_Ledger: `plan_head_before` `fefae98` → `HEAD` `9c4694c`, 2 commits measured via `git rev-list --count fefae98..HEAD`._

## Files Created/Modified
- `databasise/wirings/resolve.py` - `load_wiring` gains `variant` keyword, defaulting to `"base"`
- `databasise/parity/build_hipporag_index.py` - resolves the `corpus-ingest` variant; `_inject_documents` reads its target off `consumes_documents[0]`; `_CHUNK_EMBED_NODE_ID` removed, `_INDEX_WIRING_VARIANT` added
- `databasise/tests/parity/test_build_hipporag_index.py` (new) - end-to-end build test against a refusing embedding double, a structural disjointness test, and the fact-score root-cause pin
- `databasise/clients/openai_compat.py` - `EmptyEmbeddingInputError` and the `embed()` guard
- `databasise/tests/clients/test_openai_compat.py` - tests 11-15
- `.planning/WINDOWS.md` - entry id 3 closed (`fixed`, `resolved_at` stamped, `open_count: 0`)

## Decisions Made

- **Root cause was in the harness, not `fact_score.py`.** `build_hipporag_index.py` was calling `load_wiring("hipporag")` — the full 13-node base wiring, including three query-side positions declared under `consumes_query` and their downstream chain. `fact-score` declares `deps: []`, so it dispatched in the very first scheduler batch with no query ever injected (the harness never calls `_inject_query` at all — it is an index build), evaluating `str(config.get("query", ""))` to `""` and reaching the provider with a zero-length string. 06-10 had already built the correct wiring (`corpus-ingest.json`, the seven index-side positions) — the harness simply never used it. Fixing this at the wiring-swap level, rather than adding a guard inside `fact_score.py`, addresses the actual defect: an unauthorized dispatch, not a missing input check on an authorized one.
- **The client-level guard is the second, independent half.** Even with the wiring swap eliminating the *unauthorized* dispatch, three other query-side call sites (`fact_score.py`, `dpr_fallback.py`, `embedder_query.py`) still carry the same unguarded `str(config.get("query", ""))` pattern for legitimate query-time dispatch, and `entity_fact_embed.py` can hand `embed()` an empty list whenever OpenIE extracts nothing. One refusal at `OpenAICompatibleClient.embed` — the single method all seven call sites route through — turns every one of those into a diagnosable local refusal instead of a live provider `400`, without touching any part body.
- Used a small monkeypatched synthetic corpus snapshot (2-3 short documents) for Task 1's end-to-end test, rather than the real committed 20-document parity fixture — the test proves the harness's own dispatch logic against a client double, not corpus content, so a small synthetic snapshot keeps the test fast (1.3s for the whole file) while still exercising every index-side position.

## Deviations from Plan

None — plan executed exactly as written. Both `<precondition>` checks (Task 1's `store_namespaces` byte-equality) held, so no stop-and-report branch was triggered.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Verification (actually observed, never projected)

- `cd databasise && uv run pytest -q tests/parity/test_build_hipporag_index.py -x` → **3 passed**
- `cd databasise && uv run python -c "from databasise.wirings.resolve import load_wiring; ..."` → printed exactly `hipporag-base 13 hipporag-corpus-ingest 7 True []`
- `cd databasise && uv run python -m databasise.tools.check_import_boundary` → exit 0, no forbidden `lightrag` import
- `cd databasise && uv run pytest -q tests/clients/test_openai_compat.py -x` → **15 passed**
- `grep -c '"open_count": 0' .planning/WINDOWS.md` → **1**
- `cd databasise && uv run pytest -q` (full suite, twice — once after each task) → **942 passed, 3 skipped** after Task 1; **947 passed, 3 skipped** after Task 2 (pre-task baseline recorded as 938 passed / 4 skipped in the plan; the observed skip count differs by one test unrelated to either task's own files — a pre-existing environmental skip resolved between runs, not a regression this plan introduced. Passed count exceeds the plan's stated floor in both measurements: 942 ≥ 938 after Task 1 and 947 ≥ 943 after Task 2.)
- Backstop `must_haves` (Databasise.compare() over 0/1-selector, selector-key equality, repeated-compare keying, MutableStoreComparisonExcludedError) re-checked directly: `cd databasise && uv run pytest -q tests/seam/test_compare.py` → **7 passed** — unchanged by this plan, guarded by the existing suite as instructed.
- No live provider call occurred anywhere in this plan — every test in both new/extended test files reaches a client double (`_RefusingOnEmptyBatchEmbeddingClient`, `_StubOpenIEChatClient`, `_StubOpenAIClient`), never a reachable endpoint. No `openai.AsyncOpenAI` was constructed.

## Known Stubs

None.

## Threat Flags

None — every threat named in this plan's own `<threat_model>` (T-06-14-01 through T-06-14-05, T-06-14-SC) was addressed by this plan's own tasks; no new, undeclared security-relevant surface was introduced.

## Next Phase Readiness

- WINDOWS.md entry id 3 is closed (`fixed`, `open_count: 0`) — the blocker 06-13 Task 1 hit is now a fixed code defect, not an open item.
- `MODAL-05` **stays Pending** in `.planning/REQUIREMENTS.md`, exactly as this plan's own `must_haves.prohibitions` require: this plan fixed a defect, it performed no run. No requirement row was flipped on the strength of a code fix alone.
- 06-15 (the re-attempted real cross-modality run) can now proceed: the harness dispatches only the seven index-side positions, and the empty-batch/whitespace-only failure mode that produced the 2026-09-10 provider `400` is refused locally before any request is constructed — the concrete blocker `CROSS-MODALITY-EVIDENCE.md`'s "Real run attempted — refused" section named is closed.
- No live spend was incurred anywhere in this plan, per its own binding prohibition.

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-10*

## Self-Check: PASSED

All key files found on disk; both task commits (`7b5a3df`, `9c4694c`) found in `git log --oneline --all`.
