---
phase: 03-lightrag-query-side
plan: 04
subsystem: rag-engine
tags: [lightrag, wiring, jsonpatch, rfc6902, openai-compatible, faiss, cozo, sqlite, tracer]

# Dependency graph
requires:
  - phase: 03-01
    provides: "databasise/clients/ package (CapabilityScopedClients, OpenAICompatibleClient), NodeContext.clients threaded through the scheduler"
  - phase: 03-02
    provides: "v1 parity environment, hash-verified corpus snapshot, verified read-and-reinsert import of v1's built index into the v2 namespace layout (databasise.parity.import_index, databasise.namespaces.derive_namespace)"
provides:
  - "databasise/wirings/lightrag/ — the registered eighteen-position base wiring plus five RFC 6902 arm patches (naive/bypass/hybrid/local/global), versioned per the owner's Task 1 checkpoint decision"
  - "databasise/wirings/resolve.py — resolve_arm/resolved_node_ids/declared_node_ids/load_base, the jsonpatch-backed base-plus-patch resolver"
  - "Seven registered, real-bodied LightRAG parts (embedder-query, retriever-chunk-topk, chunk-heading-backfiller, reranker-cross-encoder, assembler-kg-context, generator-llm, embedder-index) merged into default_registry()"
  - "databasise/parity/run_arm.py — the arm driver: resolves an arm, injects query text and a real per-node token_allowance, assembles the imported store namespace and pinned clients, drives runner.scheduler.run_wiring directly"
affects: [03-05, 03-06, 03-07, 03-08, 03-09]

# Actuals (#2632)
actuals:
  tokens: 25348
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "Base-plus-RFC-6902-patch wiring resolution via jsonpatch.apply_patch, never a hand-rolled JSON-Pointer walker — fail-closed on remove of a missing node is the library's own behavior, not custom code."
    - "A driver that needs the imported store namespace bypasses the public run_wiring composer (which hardcodes a single kv-only tracer store) and drives runner.scheduler.run_wiring directly, assembling its own kv/vector/graph stores and stamping its own RunRecord with a real arm_id."
    - "Every metered node's config must carry an explicit token_allowance — an absent one defaults to 0 (DEC-B) and halts the run on the very first real token spent; a driver assembling a real multi-node run must inject one."
    - "A part body reads chunk KV records via per-id get_by_id, never store.get_by_ids zipped positionally against the requested id list — get_by_ids silently drops missing ids rather than preserving alignment with None placeholders."

key-files:
  created:
    - databasise/wirings/lightrag/base.json
    - databasise/wirings/lightrag/arm-naive.json-patch.json
    - databasise/wirings/lightrag/arm-bypass.json-patch.json
    - databasise/wirings/lightrag/arm-hybrid.json-patch.json
    - databasise/wirings/lightrag/arm-local.json-patch.json
    - databasise/wirings/lightrag/arm-global.json-patch.json
    - databasise/wirings/lightrag/README.md
    - databasise/wirings/resolve.py
    - databasise/parts_core/lightrag/embedder_query.py
    - databasise/parts_core/lightrag/chunk_vector.py
    - databasise/parts_core/lightrag/heading_backfill.py
    - databasise/parts_core/lightrag/rerank.py
    - databasise/parts_core/lightrag/assemble.py
    - databasise/parts_core/lightrag/generate.py
    - databasise/parts_core/lightrag/embedder_index.py
    - databasise/parity/run_arm.py
    - databasise/tests/parts_core/lightrag/test_naive_arm_parts.py
    - databasise/tests/parity/test_naive_arm_end_to_end.py
    - databasise/tests/parity/test_embedder_index_reproduction.py
  modified:
    - databasise/parts_core/lightrag/__init__.py
    - databasise/parts/registry.py
    - databasise/tests/parts/test_registry.py
    - databasise/tests/parity/conftest.py

key-decisions:
  - "Task 1 checkpoint: owner selected `versioned` over the plan's recommended `unversioned` — all fifteen new LightRAG components (seven ported here, eight deferred to 03-05/03-06) are registered with an @0.1.0 suffix, matching the three existing Phase 1/2 stubs (lightrag/query-side@0.1.0, lightrag/full-ingest@0.1.0, codebase-memory-mcp@0.1.0), rather than the published wiring's own unversioned component names. This deviates from CONTRACT §0's version-minting-only-at-promotion rule; recorded as a deliberate deviation in databasise/wirings/lightrag/README.md, not an oversight."
  - "embedder-index's sample config is a list of {chunk_id, text} pairs, not a list of bare chunk ids to look up: the Part's own declared effects are calls_embedding + writes_artifact only, never reads_kv, so a run-time KV lookup inside the body would have nowhere to attach. The caller (databasise/parity/run_arm.py or a test) supplies both id and text directly."
  - "run_arm.py loads v1/.env.parity with a small stdlib KEY=VALUE parser rather than adding python-dotenv as a runtime dependency — not one of databasise/pyproject.toml's approved deps, and the file's flat format needs nothing more than string splitting."
  - "run_arm.py injects a per-node token_allowance=1_000_000 default into every resolved node's config before parsing — an absent allowance defaults to 0 (runner/scheduler.py's own DEC-B rule) and would otherwise halt the very first metered node (embedder-query) after a single real token, truncating every real run to one or two nodes. Never added to the committed wiring itself (which stays byte-identical to the checked docs/system-model source)."

patterns-established:
  - "Real per-part bodies over `ctx.stores`/`ctx.clients` plain-dict access, tested directly against `Part.body(ctx)` with a raw (unscoped) NodeContext — deny-by-default enforcement itself stays covered by the existing scheduler-level test suites, not re-proven per part."
  - "Stub client doubles (embed/chat/rerank) implementing the exact clients/base.py Protocol shape, used for the non-negotiable any-machine test path; skip-guarded fixtures (v1_env_parity_path, v2_parity_store_dir) gate the real-endpoint path."

requirements-completed: [MODAL-01]

coverage:
  - id: D1
    description: "Task 1 checkpoint (owner: versioned naming) applied to the registered base wiring, all five arm patches, and recorded in databasise/wirings/lightrag/README.md"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_naive_arm_end_to_end.py::test_base_wiring_shape_recipe_and_derived_field_removal"
        status: pass
    human_judgment: false
  - id: D2
    description: "Base-plus-arm-patch resolution (resolve_arm) reproduces every published arm's own resulting_node_id_set exactly, and fails closed on a remove targeting a missing node"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_naive_arm_end_to_end.py::test_resolved_node_ids_match_the_patch_files_own_resulting_node_id_set"
        status: pass
      - kind: unit
        ref: "databasise/tests/parity/test_naive_arm_end_to_end.py::test_a_patch_removing_a_node_absent_from_the_base_raises_rather_than_succeeding"
        status: pass
    human_judgment: false
  - id: D3
    description: "Seven ported LightRAG parts (embedder-query, retriever-chunk-topk, chunk-heading-backfiller, reranker-cross-encoder, assembler-kg-context, generator-llm, embedder-index) each behave per their <behavior> contract against a stub client/store double"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_naive_arm_parts.py (17 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The naive arm runs end to end (seven nodes, non-zero token accounting on embedder-query and generate, schema-valid run record) against a synthetic imported-store shape with stub clients — the non-negotiable, any-machine path"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_naive_arm_end_to_end.py::test_naive_arm_full_run_against_a_synthetic_store_with_stub_clients"
        status: pass
    human_judgment: false
  - id: D5
    description: "embedder-index is authored with a real body, registered, named by the base wiring's recipe.embedding field, and validated by sample reproduction against v1's stored vectors (cosine similarity, threshold 0.999) rather than by re-indexing the corpus"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_embedder_index_reproduction.py (offline cases: recipe assertion, no-sample path, violation-reporting shape)"
        status: pass
      - kind: other
        ref: "databasise/tests/parity/test_embedder_index_reproduction.py::test_embedder_index_reproduces_v1_stored_vectors_on_a_sample (skip-guarded — no real v1 build/live endpoint present in this worktree, see Deviations)"
        status: unknown
    human_judgment: true
    rationale: "The real sample-reproduction case against v1's actual stored vectors requires plan 03-02's gitignored build artifacts (v1/.parity_working_dir, v1/.parity_v2_store) and v1/.env.parity, none of which are present in this parallel worktree (they are untracked, worktree-local build products from a different execution session). The test is written correctly and skip-guards cleanly here; a human (or a future run on a machine holding those artifacts) must confirm it passes for real."
  - id: D6
    description: "A live CLI run (uv run python -m databasise.parity.run_arm --arm naive --query ...) against the real imported index and real OpenRouter/Ollama endpoints"
    requirement: "MODAL-01"
    verification: []
    human_judgment: true
    rationale: "Same precondition gap as D5 — this worktree lacks the plan 03-02 build artifacts and v1/.env.parity. The CLI fails cleanly with a named MissingParityEnvError rather than a raw traceback (confirmed manually), proving the code path is correct, but the actual live run has not been exercised in this session."

duration: ~50min (research-heavy; exact start not captured)
completed: 2026-09-01
status: complete
---

# Phase 3 Plan 04: LightRAG Query Side — Naive Arm Tracer Summary

**Seven §L.1 positions (embedder-query, retriever-chunk-topk, chunk-heading-backfiller, reranker-cross-encoder, assembler-kg-context, generator-llm, embedder-index) ported as real registered parts, wired via a committed base-plus-RFC-6902-patch set, and proven end to end through the naive arm — resolver, registry, scheduler, and token accounting all exercised on one path with a stub client double, real-endpoint path skip-guarded.**

## Performance

- **Duration:** ~50 min (research-heavy: extensive read-first pass across the published wiring, validator, registry, scheduler, clients, and v1's operate.py before any file was written)
- **Tasks:** 2 completed (Task 1 was a pre-approved checkpoint per the orchestrator; recorded, not re-verified)
- **Files modified:** 23 (19 created, 4 modified)

## Accomplishments

- Registered `databasise/wirings/lightrag/base.json` (the eighteen-position base wiring) and all five arm patches (`naive`/`bypass`/`hybrid`/`local`/`global`), applying the owner's Task 1 checkpoint `versioned` naming decision and the two remaining structural edits (dropping `status`/`status_note`, adding `wiring_id`/`title`; dropping the derived `artifact_scope` field from `embedder-index`) — every node, dep, config, recipe, harnesses, provides, and operation field otherwise byte-identical to the published `docs/system-model/wirings/lightrag-*` source (verified programmatically).
- Built `databasise/wirings/resolve.py`: a `jsonpatch`-backed arm resolver (`resolve_arm`, `resolved_node_ids`, `declared_node_ids`, `load_base`) whose fail-closed removal guarantee is `jsonpatch`'s own library behavior, not hand-rolled.
- Authored and registered seven real LightRAG part bodies under `databasise/parts_core/lightrag/`, merged into `default_registry()` — the `naive` and `bypass` arms both now parse clean against the live registry.
- Built `databasise/parity/run_arm.py`: the arm driver. Assembles the plan 03-02-imported kv/vector/graph store namespace and OpenAI-compatible clients pinned by `v1/.env.parity`, injects the query text and a real per-node token allowance, and drives `runner.scheduler.run_wiring` directly (not the public composer, which hardcodes a single kv-only tracer store).
- Proved the full seven-node `naive` arm end to end against a synthetic imported-store shape with a stub client double: `partial=False`, a schema-valid run record, non-zero `TokenAccounting` on both `embedder-query` and `generate`.
- Wrote D-03's sample-reproduction validation for `embedder-index` (cosine similarity against v1's own stored vectors, threshold 0.999 with its noise-floor derivation documented), plus its offline no-sample/recipe-identification coverage.

## Task Commits

1. **Task 1: Component naming convention checkpoint** — no commit (pre-resolved by the orchestrator per the owner's decision; recorded in `databasise/wirings/lightrag/README.md`'s "Naming convention" section, not re-verified)
2. **Task 2: End-to-end `naive` arm — one query, seven positions, one run record** — `452ee31` (feat)
3. **Task 3: `embedder-index` sample reproduction — D-03's validation** — `0606aee` (test)

_No plan-metadata commit yet — SUMMARY.md is the orchestrator's post-wave responsibility in worktree mode._

## Files Created/Modified

- `databasise/wirings/lightrag/base.json`, `arm-{naive,bypass,hybrid,local,global}.json-patch.json`, `README.md` — the registered wiring set
- `databasise/wirings/resolve.py` — `resolve_arm`/`resolved_node_ids`/`declared_node_ids`/`load_base`
- `databasise/parts_core/lightrag/{embedder_query,chunk_vector,heading_backfill,rerank,assemble,generate,embedder_index}.py` — the seven ported part bodies
- `databasise/parts_core/lightrag/__init__.py` — `LIGHTRAG_PARTS` tuple
- `databasise/parts/registry.py` — `default_registry()` now merges `LIGHTRAG_PARTS`
- `databasise/parity/run_arm.py` — the arm driver, `main()` CLI
- `databasise/tests/parts_core/lightrag/test_naive_arm_parts.py` — 17 per-body tests
- `databasise/tests/parity/test_naive_arm_end_to_end.py` — arm resolution conformance, fail-closed removal, `parse_wiring` acceptance, the stub-client full run, the skip-guarded real run
- `databasise/tests/parity/test_embedder_index_reproduction.py` — D-03's sample-reproduction validation
- `databasise/tests/parity/conftest.py` — new `v1_env_parity_path`/`v2_parity_store_dir` skip-guarded fixtures
- `databasise/tests/parts/test_registry.py` — updated the stale "exactly seven" registry-size invariant (see Deviations)

## Decisions Made

- **Task 1 checkpoint: owner selected `versioned` over the plan's recommended `unversioned`.** All fifteen new LightRAG component names carry an `@0.1.0` suffix. Recorded in full, including the CONTRACT §0 tension this creates, in `databasise/wirings/lightrag/README.md`.
- `embedder-index`'s sample config carries `(chunk_id, text)` pairs directly rather than bare ids the body would look up — its declared effects are `calls_embedding`/`writes_artifact` only, never `reads_kv`.
- `run_arm.py` parses `v1/.env.parity` with a small stdlib parser instead of adding `python-dotenv`.
- `run_arm.py` injects `config.token_allowance` (default 1,000,000) into every resolved node — see Deviations, Rule 2.

## Deviations from Plan

### Pre-approved checkpoint (not a deviation, recorded per orchestrator instruction)

**Task 1 — Component naming convention.** Already resolved by the owner via the orchestrator (`versioned`). Not re-issued as a checkpoint in this run; applied directly to the wiring set and recorded in `databasise/wirings/lightrag/README.md`.

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Functionality] Every metered node needs an explicit `token_allowance`, or the arm halts after one node**
- **Found during:** Task 2, first end-to-end smoke test of `run_arm.py`
- **Issue:** `runner/scheduler.py`'s own DEC-B rule defaults an absent `config.token_allowance` to 0. None of the published wiring's nodes declare one, so the very first metered node (`embedder-query`) halted the whole run after spending a single real token — the arm never reached `generate`, let alone all seven nodes.
- **Fix:** `run_arm.py` now injects a real, generous default `token_allowance` (1,000,000) into every resolved node's config before `parse_wiring`, via `_inject_token_allowance` — never added to the committed wiring itself, which stays byte-identical to the checked `docs/system-model` source per the README's "three edits, and only these three" rule.
- **Files modified:** `databasise/parity/run_arm.py`
- **Verification:** the synthetic-store stub-client end-to-end test (`test_naive_arm_full_run_against_a_synthetic_store_with_stub_clients`) asserts `partial is False` and all seven nodes present.
- **Committed in:** `452ee31` (Task 2 commit)

**2. [Rule 1 - Bug] `store.get_by_ids` does not preserve id alignment for missing entries**
- **Found during:** Task 2, writing `heading_backfill.py`
- **Issue:** `SqliteKVStore.get_by_ids` (`databasise/stores/kv.py`) silently drops missing ids rather than returning a same-length list with `None` placeholders. An initial `dict(zip(chunk_ids, kv_records, strict=True))` implementation would misalign records — or raise a spurious `ValueError` from `strict=True` — the moment any one requested chunk id was missing from the store.
- **Fix:** `heading_backfill.py` now calls `kv_store.get_by_id(item_id)` per item, preserving correct id-to-record mapping regardless of missing entries.
- **Files modified:** `databasise/parts_core/lightrag/heading_backfill.py`
- **Verification:** `test_heading_backfill_leaves_an_item_untouched_when_no_kv_record_exists` (a missing-chunk case) passes.
- **Committed in:** `452ee31` (Task 2 commit)

**3. [Rule 1 - Bug] Stale Phase-1-era "exactly seven registry entries" test invariant**
- **Found during:** Task 2, first full-suite run after merging `LIGHTRAG_PARTS` into `default_registry()`
- **Issue:** `tests/parts/test_registry.py::test_default_registry_holds_exactly_seven_entries` hardcoded a pre-this-plan invariant this plan's own Task 2 explicitly breaks by design — registering seven new parts is the task's stated deliverable, not a regression (identical pattern to 03-01-SUMMARY.md's own "exactly four runtime dependencies" fix).
- **Fix:** Updated the assertion and test name to expect 14 entries (7 D-04 Phase-1 entries + 7 new LightRAG parts), with a docstring noting the count grows again once 03-05/03-06 lands.
- **Files modified:** `databasise/tests/parts/test_registry.py`
- **Verification:** `cd databasise && uv run pytest -q` — 313/313 passed (was 279/280 before, one pre-existing failure).
- **Committed in:** `452ee31` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (1 Rule 2 missing-critical-functionality, 2 Rule 1 bugs)
**Impact on plan:** All three were necessary for the tracer's own stated goal (a complete, real seven-node run with real token accounting) to actually be achievable. No scope creep beyond that.

## TDD Gate Compliance

Task 2 (`tdd="true"`) combined its RED and GREEN content into a single `feat(...)` commit (`452ee31`) rather than a preceding `test(...)` commit followed by a `feat(...)` commit — the seven part bodies, the wiring set, the resolver, and their tests were all written and verified together before the first commit, since the plan's own `<action>` text describes "the wiring set" → "the resolver" → "the seven part bodies" → "the arm driver" → "the tests" as one integrated deliverable for this tracer task, not a strict test-first sequence. Task 3 (`tdd="true"`) is a genuine standalone `test(...)` commit (`0606aee`). No RED-then-GREEN pair exists for Task 2 in git history — flagged here rather than silently claimed.

## Known Stubs

None. Every part body is a real implementation reaching real store/client boundaries — no hardcoded empty values flowing to a consumer.

## Issues Encountered

- **Plan 03-02's build artifacts are absent in this parallel worktree.** `v1/.parity_working_dir`, `v1/.parity_v2_store`, and `v1/.env.parity` are gitignored, worktree-local build products from plan 03-02's own (different) execution session/worktree — they do not carry over to a freshly spawned parallel worktree the way committed files do. This blocks the live-endpoint acceptance criterion (`uv run python -m databasise.parity.run_arm --arm naive --query "..."`) and the real sample-reproduction test in this session. Both code paths are written correctly and skip/fail cleanly (confirmed manually: the CLI raises a named `MissingParityEnvError` rather than a raw traceback) — this is an environment/worktree-isolation fact, not unfinished implementation. Resolves itself on any machine that has run plan 03-02's real ingest and holds `v1/.env.parity`.
- **FaissVectorStore L2-normalises on write, so two test vectors differing only in magnitude produce identical scores.** Caught while writing `test_chunk_vector_returns_items_ordered_by_descending_score` — fixed by using vectors that differ in direction, not magnitude.
- `pycozo`'s own `logger.exception` fires a harmless (caught) pandas-import warning every time a `CozoGraphStore` is constructed — pre-existing, unrelated to this plan, not fixed (out of scope; `pandas` is deliberately not a dependency).

## User Setup Required

None for the code delivered here. To exercise the live-endpoint paths this plan leaves skip-guarded, a future session needs: (1) plan 03-02's real ingest re-run or its artifacts copied into this worktree (`v1/.parity_working_dir`, then `databasise.parity.import_index.import_v1_index()`), and (2) `v1/.env.parity` populated per `v1/README-PARITY.md`.

## Next Phase Readiness

- `databasise/wirings/resolve.py` and the registered wiring set are ready for plans 03-05/03-06 to extend: those plans port the remaining eight base-wiring positions (`keywords`, `entity-lookup`, `entity-hydrate-expand`, `relation-lookup`, `relation-hydrate-expand`, `join-roundrobin`, `truncator-token-budget`, `chunk-selector-kg`), after which the unpatched base itself parses clean and the `hybrid`/`local`/`global` arms become fully dispatchable.
- `databasise/parity/run_arm.py`'s `clients`/`store_root`/`workspace` override points make it directly reusable by 03-07/03-09's parity-comparison work without modification.
- The D5/D6 real-endpoint gaps (see `coverage` above) are the only items this plan could not close in this worktree; both are environment gaps, not code gaps, and are documented for the next session/machine holding the plan 03-02 artifacts.

---
*Phase: 03-lightrag-query-side*
*Completed: 2026-09-01*

## Self-Check: PASSED

All created/modified files confirmed present on disk; both task commit hashes (`452ee31`, `0606aee`) confirmed in `git log --oneline --all`.
