---
phase: 03-lightrag-query-side
plan: 01
subsystem: api
tags: [openai, jsonpatch, capability-scoping, node-context, deny-by-default, python]

# Dependency graph
requires:
  - phase: 01-machine-core
    provides: "NodeContext, Part/WiringNode schema, runner/scheduler.py's structured-concurrency dispatch, CapabilityScopedStores (the mirror source)"
  - phase: 02-falsifier-gate
    provides: "CR-01 fix (registry-sourced effects, not the wiring's self-declared ones) that _ScopedClientsView reuses the same way _ScopedStoresView does"
provides:
  - "databasise/clients/ package: LLMClient/EmbeddingClient/RerankClient protocols, OpenAICompatibleClient, CapabilityScopedClients/ClientNotWiredError"
  - "NodeContext.clients field, populated at the scheduler's single NodeContext(...) construction site"
  - "openai and jsonpatch as approved runtime dependencies; four new subpackages registered in pyproject.toml"
affects: [03-02, 03-03, 03-04, 03-05, 03-06, 03-07, 03-08, 03-09]

# Actuals (#2632)
actuals:
  tokens: 19128
  tasks: 4
  commits: 3

tech-stack:
  added: ["openai>=2.0.0,<4.0.0", "jsonpatch"]
  patterns:
    - "CapabilityScopedClients mirrors CapabilityScopedStores structurally, but keys the effect->handle mapping through an explicit dict (CLIENT_EFFECT_TO_KEY) instead of the store side's suffix-split trick, because calls_embedding/calls_rerank don't split cleanly."
    - "_ScopedClientsView mirrors _ScopedStoresView, threaded through the exact same single NodeContext(...) construction site rather than a second path."
    - "Client implementations accept an injectable `client` override (bypassing the real openai.AsyncOpenAI construction) purely so tests can stub the SDK surface with no network reachable."

key-files:
  created:
    - databasise/clients/base.py
    - databasise/clients/openai_compat.py
    - databasise/clients/__init__.py
    - databasise/parts_core/lightrag/__init__.py
    - databasise/parity/__init__.py
    - databasise/wirings/__init__.py
    - databasise/tests/clients/test_capability_scoped_clients.py
    - databasise/tests/clients/test_openai_compat.py
    - databasise/tests/runner/test_clients_threading.py
  modified:
    - databasise/pyproject.toml
    - databasise/parts/schema.py
    - databasise/runner/scheduler.py
    - databasise/__init__.py
    - databasise/tests/test_embed_startup.py

key-decisions:
  - "openai's version range widened to >=2.0.0,<4.0.0 (not the plan's copied >=2.0.0,<3.0.0) after querying PyPI directly showed the current release is 3.6.0 — closing 03-RESEARCH.md assumption A1 for real rather than leaving the copied range in place."
  - "Client-effect-to-key mapping made a public CLIENT_EFFECT_TO_KEY constant (not the private name PATTERNS.md's illustrative snippet used) so runner/scheduler.py can import it per the plan's own instruction to 'import the mapping rather than restating it.'"
  - "resolved_model_identity is derived solely from the response's own `model` field (confirmed against the installed openai 3.6.0 SDK's ChatCompletion/CreateEmbeddingResponse schemas) — there is no separate 'provider' field in the real SDK response shape, so 'provider and model' in the plan's wording collapses to the one field the SDK actually reports."

patterns-established:
  - "Deny-by-default client scoping (CapabilityScopedClients) — same CR-01 concern as store scoping, applied to calls_llm/calls_embedding/calls_rerank."
  - "Guarded SDK import (try: import openai / except ImportError: raise with install command) — same idiom as stores/vector.py's faiss guard."

requirements-completed: [MODAL-01]

coverage:
  - id: D1
    description: "CapabilityScopedClients denies an undeclared effect and refuses an unwired client by name (never returns None)"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/clients/test_capability_scoped_clients.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "OpenAICompatibleClient serves chat + embeddings through one construction shape, deriving resolved_model_identity from the response and raising when that field is absent"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/clients/test_openai_compat.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "NodeContext.clients threaded through the scheduler's single construction site; a part reaches its client only through a declared effect, an unwired client is refused by name, and a run with no clients argument behaves exactly as before"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/runner/test_clients_threading.py"
        status: pass
      - kind: integration
        ref: "cd databasise && uv run pytest -q (274 passed)"
        status: pass
    human_judgment: false
  - id: D4
    description: "openai and jsonpatch installed behind an approved package-legitimacy gate; four new subpackages registered and importable"
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "uv run python -c \"import openai, jsonpatch, databasise.clients, databasise.parity, databasise.wirings, databasise.parts_core.lightrag\""
        status: pass
    human_judgment: false

duration: 9min
completed: 2026-08-31
status: complete
---

# Phase 3 Plan 01: LightRAG Query Side — Client Primitive Summary

**`databasise/clients/` package (protocols, an OpenAI-compatible chat+embeddings implementation, deny-by-default `CapabilityScopedClients`) threaded onto `NodeContext.clients` at the scheduler's single construction site, so every later ported part reaches an LLM/embedding/rerank endpoint through a boundary MACH-05's meter can see.**

## Performance

- **Duration:** 9 min (18:49:20 → 18:58:17, three task commits)
- **Tasks:** 4 (Task 1 was a pre-approved checkpoint, recorded not re-verified)
- **Files modified:** 16 (9 created, 5 modified, 2 lockfile/pyproject config)

## Accomplishments

- Added `openai` (D-06/D-07's LLM/embedding client) and `jsonpatch` (D-13's RFC 6902 arm-patch application) as approved runtime dependencies, and registered the four new subpackages this phase introduces (`databasise.clients`, `databasise.parity`, `databasise.wirings`, `databasise.parts_core.lightrag`) in `pyproject.toml` so an editable install resolves them.
- Built `databasise/clients/base.py`: three `typing.Protocol` definitions (`LLMClient`, `EmbeddingClient`, `RerankClient`) plus frozen result dataclasses (`ChatResult`, `EmbeddingResult`, `RerankResult`), each carrying a real `TokenAccounting` and a `resolved_model_identity` derived from the response, never the requested id.
- Built `databasise/clients/openai_compat.py`: `OpenAICompatibleClient` — one construction shape (`base_url`/`model`/`api_key`) reaches OpenRouter, a local Ollama endpoint, or plain OpenAI. Raises `ModelIdentityMissingError` rather than substituting the requested model id when a response carries no `model` field.
- Built `databasise/clients/__init__.py`: `CapabilityScopedClients` and `ClientNotWiredError`, mirroring `CapabilityScopedStores`/`StoreNotWiredError` structurally, keyed through an explicit `CLIENT_EFFECT_TO_KEY` dict (the store side's suffix-split trick doesn't transfer to `calls_embedding`/`calls_rerank`).
- Threaded `NodeContext.clients` through `runner/scheduler.py`'s single `NodeContext(...)` construction site via a new `_ScopedClientsView`, and forwarded an optional `clients` parameter through `databasise/__init__.py`'s public `run_wiring` composer.

## Task Commits

1. **Task 1: Package legitimacy gate — `openai` and `jsonpatch`** — no commit (checkpoint; see Deviations below for the pre-approval record)
2. **Task 2: Add the two dependencies and register this phase's new subpackages** - `bd1406d` (feat)
3. **Task 3: The `databasise/clients/` package** - `dd03d49` (feat)
4. **Task 4: `NodeContext.clients` and the scheduler/composer threading** - `38790df` (feat)

_No plan-metadata commit yet — SUMMARY.md/STATE.md/ROADMAP.md are the orchestrator's post-wave responsibility in worktree mode._

## Files Created/Modified

- `databasise/pyproject.toml` - Added `openai`/`jsonpatch` deps, registered 4 new subpackages + wirings package-data
- `databasise/clients/base.py` - `LLMClient`/`EmbeddingClient`/`RerankClient` protocols and result dataclasses
- `databasise/clients/openai_compat.py` - `OpenAICompatibleClient`, `ModelIdentityMissingError`
- `databasise/clients/__init__.py` - `CapabilityScopedClients`, `ClientNotWiredError`, `CLIENT_EFFECT_TO_KEY`
- `databasise/parts/schema.py` - `NodeContext.clients` field (default empty dict)
- `databasise/runner/scheduler.py` - `_ScopedClientsView`, `clients` parameter threaded through `run_wiring`/`_run_node`
- `databasise/__init__.py` - Public composer forwards `clients` to the scheduler
- `databasise/parts_core/lightrag/__init__.py`, `databasise/parity/__init__.py`, `databasise/wirings/__init__.py` - New empty package roots
- `databasise/tests/clients/test_capability_scoped_clients.py`, `test_openai_compat.py` - 11 new tests
- `databasise/tests/runner/test_clients_threading.py` - 4 new tests covering all four D-06 behaviors
- `databasise/tests/test_embed_startup.py` - Updated the stale "exactly four runtime deps" invariant to six (see Deviations)

## Decisions Made

- Widened `openai`'s upper bound to `<4.0.0` after a live PyPI query (Task 2's own instruction) showed the current release is 3.6.0 — the plan's copied `<3.0.0` bound would have installed nothing.
- Named the effect-to-client-key mapping `CLIENT_EFFECT_TO_KEY` (public) rather than the private `_CLIENT_EFFECT_TO_KEY` PATTERNS.md's illustrative snippet used, so `runner/scheduler.py` could import it per the plan's own "import the mapping rather than restating it" instruction without reaching across a private name.
- `resolved_model_identity` is derived solely from the response's `model` field — the installed `openai` 3.6.0 SDK's `ChatCompletion`/`CreateEmbeddingResponse` schemas (confirmed by reading `model_fields` this session) carry no separate "provider" field, so the plan's "provider and model" phrasing collapses to the one field the SDK actually reports.

## Deviations from Plan

### Pre-approved checkpoint (not a deviation, recorded per orchestrator instruction)

**Task 1 — Package legitimacy gate for `openai` and `jsonpatch`.** A prior executor run for this same plan already surfaced this `checkpoint:human-verify` gate and the user explicitly approved both packages. Per the orchestrator's explicit instruction for this run, the gate was not re-issued; this executor proceeded directly to Task 2's install and Tasks 3–4, recording the prior approval here rather than re-blocking on an already-settled decision.

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated a stale "exactly four runtime dependencies" test invariant**
- **Found during:** Task 2 (installing `openai`/`jsonpatch`)
- **Issue:** `tests/test_embed_startup.py::test_5_the_declared_runtime_dependency_set_is_exactly_four_and_none_is_a_db_client` hardcoded a Phase-1-era invariant (`len(requires) == 4`, `names == {"pycozo", "faiss-cpu", "rfc8785", "pydantic"}`) that this plan's own Task 2 explicitly breaks by design — adding two new runtime dependencies is the task's stated deliverable, not a regression.
- **Fix:** Updated the assertion to `len(requires) == 6` and the expected name set to include `openai`/`jsonpatch`, renamed the test function accordingly, and confirmed neither new dependency matches the test's own "separately-hosted database server client" exclusion list (`psycopg`, `pymongo`, `redis`, `neo4j`, `pymilvus`, `qdrant`, `opensearch`) — the substantive invariant the test protects (no DB-server client sneaks into a supposedly server-free dependency set) still holds.
- **Files modified:** `databasise/tests/test_embed_startup.py`
- **Verification:** `cd databasise && uv run pytest -q` — 259/259 passed after the fix (was 258/259 before)
- **Committed in:** `bd1406d` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug), 1 pre-approved checkpoint carried forward (not a deviation)
**Impact on plan:** The test fix was necessary for the suite to reflect the plan's own intended dependency change; no scope creep beyond it.

## Issues Encountered

None beyond the deviation documented above.

## Next Phase Readiness

- `ctx.clients["llm"]`/`["embedding"]`/`["rerank"]` is now a real, tested calling convention every later part body in `parts_core/lightrag/` can rely on.
- `databasise/clients/`, `databasise/parity/`, `databasise/wirings/`, `databasise/parts_core/lightrag/` all exist and import cleanly, ready for plan 03-02 onward to populate with real content.
- No `RerankClient` implementation exists yet (only the protocol) — in scope per this plan's own Task 3 action text ("chat-completions + embeddings client"); a later plan implements rerank if/when a part needs `calls_rerank`.
- Full suite: 274/274 passed, no regressions.

---
*Phase: 03-lightrag-query-side*
*Completed: 2026-08-31*
