# Phase 8: Run the Engine - Context

**Gathered:** 2026-10-16
**Status:** Ready for planning

<domain>
## Phase Boundary

An operator starts the engine as a served process from the installed package: `databasise-rest` (uvicorn over `seam.rest.create_app`) and `databasise-mcp` (stdio/sse/streamable-http over `create_server(...)`), both with real model clients from one shared builder, with one engine process per store root enforced by a store lock and an opt-in CORS allow-list. The offline suite is green under `.venv/bin/pytest` and `.venv/bin/python -m pytest`. Requirements: RUN-01 to RUN-12. No new seam operations; the MCP transport already exists (v1.0 Phase 5) and only gains a launcher.

</domain>

<decisions>
## Implementation Decisions

### Process topology and store lock (RUN-06, RUN-07)
- **D-01:** Two separate processes. `databasise-rest` and `databasise-mcp` are independent launchers; MCP streamable-http is NOT mounted into the FastAPI app. Only one launcher holds a store root at a time; the second exits non-zero with the named store-lock error (store root + holder PID).
- **D-02:** The MCP launcher is minimal: `databasise-mcp --transport stdio|sse|streamable-http` calling the matching run method on the existing `create_server(...)`, plus one example MCP client config invoking it over stdio. No new MCP tools or behaviour. Rationale recorded from discussion: the owner questioned whether MCP adds anything over REST; it adds no operation (all nine tools have REST equivalents, REST is a superset with SSE), only agent-client protocol access, and PROJECT.md keeps "REST + MCP is its voice". The launcher is kept because it is a few lines.
- **D-03:** Parity CLIs (import_index, build_hipporag_index, run_comparison, run_cross_modality, storage_audit) take the same store lock as the launchers and refuse with the same named error while a launcher holds the store root.
- **D-04:** The Phase 8 lock is cross-process only (G-36). In-process concurrency on graph.cozo (G-01, StoreBusy vs shared handle) stays with STOR-01 in Phase 10; the two mechanisms must not overlap.

### Model clients (RUN-02, RUN-03, RUN-05)
- **D-05:** RUN-02: a provider response with `usage=None` returns `TokenAccounting(call_count=1, counted_by='unbudgetable')` with zero token counts. No new sentinel, no tiktoken estimate.
- **D-06:** RUN-03: `content=None` (refusal or tool call) raises a named client error; never `ChatResult(text=None)` and never mapped to empty text. Empty choices, mis-sized embedding batches raise named errors; out-of-order embedding items are reordered by `.index`.
- **D-07:** RUN-05: **ship a rerank client in v1.1** (owner chose this over the "not available" default). It implements the existing `RerankClient` protocol (`databasise/clients/base.py:71-75`) and speaks the Cohere/Jina-compatible `/rerank` HTTP shape: request `{model, query, documents, top_n}`, response `results[{index, relevance_score}]` (covers Cohere, Jina, vLLM, TEI servers; aliyun not covered).
- **D-08:** Rerank env keys are optional in the shared builder: `RERANK_BINDING_HOST`, `RERANK_MODEL`, `RERANK_BINDING_API_KEY` (names follow v1 `env.example`). All present → builder returns `{'llm','embedding','rerank'}`. None present → `{'llm','embedding'}`, rerank unwired, `/health` reports rerank as not available, and `live_rerank=True` raises `ClientNotWiredError('rerank')`. Partial set → `MissingParityEnvKeyError` naming the missing rerank keys. The six existing required keys are unchanged.
- **D-09:** No shipped wiring turns `live_rerank` on in this phase. Client only; LightRAG parity answers are unchanged.
- **D-10:** Rerank tests use a fake HTTP transport offline. A `-m live` rerank test exists but waits for an owner-supplied env file with `RERANK_*` keys (sourced at runtime, never printed).
- **D-11:** The launcher refuses to start without model clients (missing/incomplete env file → error naming every missing key) unless `--no-clients` is given explicitly.
- **Requirement wording affected by D-07/D-08:** RUN-05 says "No rerank client is built" and ROADMAP Phase 8 success criterion 1 says "rerank is explicitly reported as not available". Both hold only when no `RERANK_*` keys are present. The ledger/requirement text needs an owner-approved amendment; planning must not treat the old wording as a contradiction to resolve by dropping the rerank client.

### Browser access (RUN-08)
- **D-12:** Explicit CORS allow-list: `databasise-rest --cors-origin <origin>`, repeatable, empty by default, never `'*'`. Exact `scheme://host:port` origins only; no localhost regex or wildcard shortcut. No flag → behaviour unchanged (OPTIONS still 405). Same-origin serving of the console is not built here. Seam auth stays a separate open decision.

### Test evidence (RUN-01, RUN-11)
- **D-13:** RUN-01: copy the live §18.5 coverage record to `databasise/evidence/COVERAGE.md` (next to the FALSIFIER and ADMISSION records); `test_tool_growth_invariant.py` points there, and a missing file fails with an assertion naming the expected path. v1.1 tools/routes add rows to this file. The archived `.planning/milestones/v1.0-phases/05-opaque-side-admission/COVERAGE.md` stays frozen.
- **D-14:** RUN-11: run the live re-embedding test N times (about 5), set `_SIMILARITY_THRESHOLD` just below the observed minimum (around 0.995), and record date, endpoint model and the measured runs in the test. The parity claim becomes "reproduces within endpoint noise". The test carries the registered `live` marker and is deselected by default.

### Claude's Discretion
- Lock mechanism and location (e.g. `fcntl.flock` on a lock file under the store root that records the holder PID; released by the OS on process exit), and the error class name.
- Module layout for the launchers (`python -m` modules) and the shared client builder's new home.
- Location and format of the example MCP client config (`.mcp.json` vs docs snippet).
- Name of the rerank client class and its error types, following `OpenAICompatibleClient` conventions.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope
- `.planning/ROADMAP.md` — Phase 8 goal, success criteria, owner decisions, cross-phase decision G-01/G-36
- `.planning/REQUIREMENTS.md` — RUN-01 to RUN-12 (lines 14-55), STOR-01 (line 121) for the G-01 boundary
- `docs/gui/DEFECTS.json` — source defect uids cited by each RUN requirement

### Transports and coverage
- `.planning/milestones/v1.0-phases/05-opaque-side-admission/COVERAGE.md` §4 — the §18.5 operations table to copy (D-13); shows every MCP tool has a REST equivalent
- `docs/system-model/` — CONTRACT.md §18 (seam, §18.5 tool-surface growth rule)
- `.planning/PROJECT.md` — "REST + MCP is its voice" key decision

### Clients
- `v1/env.example` lines 130-162 — v1 `RERANK_*` key names and binding shapes (D-08)
- `.planning/spikes/vllm-attempt.log` — prior attempt at a local deterministic endpoint (context for D-14)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `databasise/parity/run_arm.py:_build_clients`, `_REQUIRED_ENV_KEYS` (117-124), `MissingParityEnvKeyError`, `OPENAI_LLM_EXTRA_BODY` pin: move to a non-parity module as the shared builder (RUN-05), extend with optional rerank (D-08).
- `databasise/clients/base.py`: `RerankClient` protocol and `RerankResult` already defined; `ClientNotWiredError`.
- `databasise/clients/openai_compat.py`: `OpenAICompatibleClient` (lines 131, 149, 159-161 are the RUN-02/03 sites); pattern for the rerank client.
- `databasise/parts_core/lightrag/rerank.py`: body already calls `client.rerank(query, documents)` and uses `result.ranked_indices` and `result.tokens`.
- `databasise/seam/rest.py:create_app`, `databasise/mcp/server.py:create_server`: what the launchers serve.
- `databasise/foreign/_mcp_sdk_guard.py`: `import_real_mcp` project-path stripping to reuse in `mcp_sdk_is_installed` (RUN-04).

### Established Patterns
- Named refusals over silent fallbacks (`MissingParityEnvKeyError`, `UnparseableProviderRoutingError`).
- Secrets are sourced at runtime from env files and never printed (`v1/.env.parity` is not read by agents).

### Integration Points
- `databasise/pyproject.toml`: `[project.scripts]` entries, `live` marker and `addopts` deselection under `[tool.pytest.ini_options]`.
- `databasise/tests/mcp/test_tool_growth_invariant.py` `_COVERAGE_PATH` (RUN-01).
- `databasise/tests/seam/test_rest_corpus_endpoints.py` (RUN-09, RUN-10), `tests/parity/test_embedder_index_reproduction.py` (RUN-11).

</code_context>

<specifics>
## Specific Ideas

- Default store for launchers: `store_root=v1/.parity_v2_store`, `workspace=shared-4fab18fef508b7bc3dda1cc2d8f12e36` (RUN-06).
- Example console dev origin used in tests: `http://localhost:5173`.

</specifics>

<deferred>
## Deferred Ideas

- Mounting MCP streamable-http inside the FastAPI app (one process for console + agent clients): considered, not chosen. Revisit if console and MCP clients must share one live store.
- A wiring/arm with `live_rerank=True`: a new comparison arm, belongs with Phase 13 (selectors/wiring) or later.
- Same-origin serving of the console build: revisit in Phases 16-18 once the console exists.
- A deterministic pinned embedding endpoint to restore a 0.999 parity threshold.

### Reviewed Todos (not folded)
- melodyscribe-interface-skill.md, melodyscribe-spike-rig-experiments.md: keyword-only matches; MelodyScribe moved to its own repo.

</deferred>

---

*Phase: 08-run-the-engine*
*Context gathered: 2026-10-16*
