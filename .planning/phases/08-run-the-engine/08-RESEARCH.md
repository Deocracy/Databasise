# Phase 8: Run the Engine - Research

**Researched:** 2026-10-16
**Domain:** Brownfield Python engine (FastAPI REST seam + MCP SDK 2.2.0 transport): launchers, shared model-client builder, rerank client, cross-process store lock, CORS, test-suite repair
**Confidence:** HIGH (everything below was read in the repo or reproduced in this session; the few `[ASSUMED]` items are listed in the Assumptions Log)

## Summary

Phase 8 is almost entirely additive glue over code that already works. Nothing launches either transport today (`create_app` at `databasise/seam/rest.py:235`, `create_server` at `databasise/mcp/server.py`), so the phase adds: a shared client builder moved out of `parity/run_arm.py`, a rerank client, a `flock`-based cross-process store lock, two launchers wired into `[project.scripts]`, an opt-in CORS allow-list, and a set of test repairs that turn the offline suite green under both invocation styles.

**Baseline measured this session (from `databasise/`).** Both failures are RUN-01; the only contradictory skip is RUN-04. Nothing else is red.

| Invocation | Result |
|---|---|
| `.venv/bin/pytest -q -rs` | `2 failed, 1066 passed, 1 skipped in 218.91s` |
| `.venv/bin/python -m pytest -q -rs` (3 live tests deselected, see pitfall 1) | `2 failed, 1062 passed, 2 skipped, 3 deselected in 177.67s` |

- The 2 failures in both runs are `tests/mcp/test_tool_growth_invariant.py::test_every_tool_has_a_coverage_row_and_every_both_transport_row_has_a_tool` and `::test_compare_is_present_in_tool_names_and_absent_from_the_deliberately_absent_table`, both `FileNotFoundError` on `.planning/phases/05-opaque-side-admission/COVERAGE.md` (RUN-01).
- The extra skip under `python -m pytest` is `tests/evidence/test_falsifier4_evidence.py:138` with reason `... or the 'mcp' extra is not installed (found=False)` while `mcp 2.2.0` is installed (RUN-04). Under `.venv/bin/pytest` that same test ran and passed.
- The remaining skip in both runs is `tests/seam/test_delete_document.py:256`, an opt-in real-delete test gated on `DATABASISE_RUN_REAL_DELETE=1`. Its reason is true to the environment, so it does not violate RUN-12.

**Primary recommendation:** Build bottom-up in dependency order: (1) test-hygiene fixes (RUN-01, 04, 09, 10) and the `live` marker (RUN-12), (2) client hardening (RUN-02, 03), (3) `clients/builder.py` + rerank client (RUN-05), (4) `databasise/store_lock.py` (RUN-07 core), (5) the `databasise/launcher/` package, `[project.scripts]`, `create_app(cors_origins=...)` and the `HealthReport.clients` field (RUN-06/07/08), (6) the two live-endpoint owner steps (RUN-11) and the dual-pytest gate script (RUN-12). Every new behaviour lives outside `databasise/mcp/` and outside `rest.py` route bodies, so the two AST "thin adapter" proof tests keep passing.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Two separate processes. `databasise-rest` and `databasise-mcp` are independent launchers; MCP streamable-http is NOT mounted into the FastAPI app. Only one launcher holds a store root at a time; the second exits non-zero with the named store-lock error (store root + holder PID).
- **D-02:** The MCP launcher is minimal: `databasise-mcp --transport stdio|sse|streamable-http` calling the matching run method on the existing `create_server(...)`, plus one example MCP client config invoking it over stdio. No new MCP tools or behaviour. Rationale recorded from discussion: the owner questioned whether MCP adds anything over REST; it adds no operation (all nine tools have REST equivalents, REST is a superset with SSE), only agent-client protocol access, and PROJECT.md keeps "REST + MCP is its voice". The launcher is kept because it is a few lines.
- **D-03:** Parity CLIs (import_index, build_hipporag_index, run_comparison, run_cross_modality, storage_audit) take the same store lock as the launchers and refuse with the same named error while a launcher holds the store root.
- **D-04:** The Phase 8 lock is cross-process only (G-36). In-process concurrency on graph.cozo (G-01, StoreBusy vs shared handle) stays with STOR-01 in Phase 10; the two mechanisms must not overlap.
- **D-05:** RUN-02: a provider response with `usage=None` returns `TokenAccounting(call_count=1, counted_by='unbudgetable')` with zero token counts. No new sentinel, no tiktoken estimate.
- **D-06:** RUN-03: `content=None` (refusal or tool call) raises a named client error; never `ChatResult(text=None)` and never mapped to empty text. Empty choices, mis-sized embedding batches raise named errors; out-of-order embedding items are reordered by `.index`.
- **D-07:** RUN-05: **ship a rerank client in v1.1** (owner chose this over the "not available" default). It implements the existing `RerankClient` protocol (`databasise/clients/base.py:71-75`) and speaks the Cohere/Jina-compatible `/rerank` HTTP shape: request `{model, query, documents, top_n}`, response `results[{index, relevance_score}]` (covers Cohere, Jina, vLLM, TEI servers; aliyun not covered).
- **D-08:** Rerank env keys are optional in the shared builder: `RERANK_BINDING_HOST`, `RERANK_MODEL`, `RERANK_BINDING_API_KEY` (names follow v1 `env.example`). All present -> builder returns `{'llm','embedding','rerank'}`. None present -> `{'llm','embedding'}`, rerank unwired, `/health` reports rerank as not available, and `live_rerank=True` raises `ClientNotWiredError('rerank')`. Partial set -> `MissingParityEnvKeyError` naming the missing rerank keys. The six existing required keys are unchanged.
- **D-09:** No shipped wiring turns `live_rerank` on in this phase. Client only; LightRAG parity answers are unchanged.
- **D-10:** Rerank tests use a fake HTTP transport offline. A `-m live` rerank test exists but waits for an owner-supplied env file with `RERANK_*` keys (sourced at runtime, never printed).
- **D-11:** The launcher refuses to start without model clients (missing/incomplete env file -> error naming every missing key) unless `--no-clients` is given explicitly.
- **Requirement wording affected by D-07/D-08:** RUN-05 says "No rerank client is built" and ROADMAP Phase 8 success criterion 1 says "rerank is explicitly reported as not available". Both hold only when no `RERANK_*` keys are present. The ledger/requirement text needs an owner-approved amendment; planning must not treat the old wording as a contradiction to resolve by dropping the rerank client.
- **D-12:** Explicit CORS allow-list: `databasise-rest --cors-origin <origin>`, repeatable, empty by default, never `'*'`. Exact `scheme://host:port` origins only; no localhost regex or wildcard shortcut. No flag -> behaviour unchanged (OPTIONS still 405). Same-origin serving of the console is not built here. Seam auth stays a separate open decision.
- **D-13:** RUN-01: copy the live §18.5 coverage record to `databasise/evidence/COVERAGE.md` (next to the FALSIFIER and ADMISSION records); `test_tool_growth_invariant.py` points there, and a missing file fails with an assertion naming the expected path. v1.1 tools/routes add rows to this file. The archived `.planning/milestones/v1.0-phases/05-opaque-side-admission/COVERAGE.md` stays frozen.
- **D-14:** RUN-11: run the live re-embedding test N times (about 5), set `_SIMILARITY_THRESHOLD` just below the observed minimum (around 0.995), and record date, endpoint model and the measured runs in the test. The parity claim becomes "reproduces within endpoint noise". The test carries the registered `live` marker and is deselected by default.

### Claude's Discretion
- Lock mechanism and location (e.g. `fcntl.flock` on a lock file under the store root that records the holder PID; released by the OS on process exit), and the error class name.
- Module layout for the launchers (`python -m` modules) and the shared client builder's new home.
- Location and format of the example MCP client config (`.mcp.json` vs docs snippet).
- Name of the rerank client class and its error types, following `OpenAICompatibleClient` conventions.

### Deferred Ideas (OUT OF SCOPE)
- Mounting MCP streamable-http inside the FastAPI app (one process for console + agent clients): considered, not chosen. Revisit if console and MCP clients must share one live store.
- A wiring/arm with `live_rerank=True`: a new comparison arm, belongs with Phase 13 (selectors/wiring) or later.
- Same-origin serving of the console build: revisit in Phases 16-18 once the console exists.
- A deterministic pinned embedding endpoint to restore a 0.999 parity threshold.
- Reviewed todos (not folded): melodyscribe-interface-skill.md, melodyscribe-spike-rig-experiments.md (MelodyScribe moved to its own repo).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RUN-01 | COVERAGE.md cross-check runs again | Copy `.planning/milestones/v1.0-phases/05-opaque-side-admission/COVERAGE.md` to `databasise/evidence/COVERAGE.md`; repoint `_COVERAGE_PATH` (test line 54-56); add path-naming assertion; non-vacuity test needs the check refactored into a function over `(markdown, tool_names)` |
| RUN-02 | `usage=None` -> `call_count=1`, `counted_by='unbudgetable'` | Single site `openai_compat.py:159-161`; sentinel and aggregators confirmed; side effect: such a response now makes `/query` refuse (see pitfall 4) |
| RUN-03 | Malformed provider responses raise named errors / reorder by `.index` | Sites `openai_compat.py:131` and `:149`; existing test stub has no `.index` and must gain it |
| RUN-04 | `mcp_sdk_is_installed()` shadow-safe | Reproduced `False` from `databasise/`; fix is `PathFinder.find_spec("mcp", <stripped sys.path>)` (verified to return the site-packages path) |
| RUN-05 | One shipped builder + optional rerank | Move block `run_arm.py:60-183` to `databasise/clients/builder.py`; re-export under old names so 7 importers + monkeypatch seams keep working; new `HttpRerankClient`; `HealthReport` gains `clients` |
| RUN-06 | Installed launchers + example MCP config | New `databasise/launcher/` package, `[project.scripts]`, package list entry, reinstall step; mcp 2.2.0 run API verified |
| RUN-07 | One engine process per store root | Reproduced RocksDB second-open error (generic, no PID); `fcntl.flock` design verified in-process and cross-process; `--workers>1` refused at argument validation |
| RUN-08 | Opt-in CORS allow-list | Starlette `CORSMiddleware` behaviour reproduced: must pass `allow_methods` and normalise origins |
| RUN-09 | Upload path-safety test checks the disk | Rewrite lines 345-356 of `tests/seam/test_rest_corpus_endpoints.py`; engine write site `seam/engine.py:707-709` |
| RUN-10 | Round-trip tests prove counts drop after delete | Status fake and delete stub share no state today; add shared state + `on_delete` hook |
| RUN-11 | Stable parity verdict, `live` marker | No `live` marker exists anywhere today; threshold and docstring edits in `tests/parity/test_embedder_index_reproduction.py`; needs ~5 owner-run live executions |
| RUN-12 | Both pytest styles green; live only under `-m live` | `addopts = '-m "not live"'` plus registered marker (override with `-m live` verified); 3 live-endpoint tests identified; gate script |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Source: `.claude/CLAUDE.md` (project) and `~/.claude/CLAUDE.md` (global).

- Python 3.11+ for `databasise/` (`requires-python = ">=3.11"`), ruff target `py311`. Tests are pytest 8.4.2+ with pytest-asyncio; `asyncio_mode = "auto"` is already set.
- Storage agnosticism / named refusals over silent fallbacks is the house style (`MissingParityEnvKeyError`, `UnparseableProviderRoutingError`). New errors must be named classes carrying their specifics as attributes.
- Contract vocabulary (§18 envelope, 17-member effects[]) is frozen input. The §18 seam must stay modality-agnostic: no launcher, lock or CORS code may add a field a consumer sees except the approved `HealthReport.clients` (see Open Question 2).
- Runtime: local NixOS, embeddable in-process, no external DB servers, no Docker. The lock must therefore be a local-filesystem primitive.
- GSD workflow: file edits happen through a GSD command (`/gsd-execute-phase`). Research files are exempt.
- Secrets: never read `v1/.env.parity`, `v1/parity-env.txt` or any `.env*`; tests build stub env files in `tmp_path`.
- Evidence standard: every promotion claim priced; the RUN-11 threshold change must record date, endpoint model and measured runs (D-14).
- Global answer style rules (plain technical language, clickable links) apply to chat output, not to this file.
- Mandatory BAK rule for every defect requirement: a regression test that fails before the fix and passes after. The ledger rows RUN-01..RUN-12 currently have an empty `test_ref`; fill them through `scripts/ledger-amend.py` (the ledger is hook-protected against any other edit).
- `security_enforcement` is `false` in `.planning/config.json`, so no ASVS section is emitted (see Security note at the end).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Process entry points (`databasise-rest`, `databasise-mcp`) | Launcher layer (new `databasise/launcher/`) | `pyproject.toml` `[project.scripts]` | Neither transport module may own process concerns; both stay thin adapters (AST-proved) |
| Model client construction | `databasise/clients/builder.py` (new) | Parity CLIs and launchers as callers | One builder; moves out of `parity/` so a served process does not depend on the parity package |
| Rerank HTTP client | `databasise/clients/` | Part body `parts_core/lightrag/rerank.py` as consumer (unchanged) | Same protocol as llm/embedding; body already calls `client.rerank(query, documents)` |
| Cross-process store exclusion | `databasise/store_lock.py` (new, top level) | Launchers and 5-6 parity `main()` functions as callers | Outside `stores/` so it is not confused with the in-process handle Phase 10 will add (D-04) |
| CORS | `seam/rest.py:create_app` parameter | Launcher parses `--cors-origin` | Middleware belongs to the app factory so tests exercise the same app the launcher builds |
| Client availability report | `seam/engine.py:health` + `seam/corpus.py:HealthReport` | REST `/health`, MCP `status(scope=health)` | D-08 requires `/health` to report rerank as not available |
| Offline/live test separation | `pyproject.toml` pytest config + test markers | Gate script | Marker registration and `addopts` are the single switch |

## Standard Stack

All versions read from the installed `.venv` with `importlib.metadata` this session `[VERIFIED: .venv metadata]`.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| mcp | 2.2.0 | `MCPServer.run("stdio"\|"sse"\|"streamable-http", **kwargs)`; client `ClientSession`, `StdioServerParameters`, `stdio_client` | Already the transport dependency (`mcp>=2.2.0` extra) |
| fastapi | 0.141.1 | REST app; `Starlette CORSMiddleware` re-exported | Already the `rest` extra |
| uvicorn | 0.52.4 | `uvicorn.run(app, host=, port=, workers=1)` | Already the `rest` extra; `mcp` SSE/streamable-http also use it internally (`server.py` `run_sse_async`) |
| starlette | 1.6.0 | `starlette.middleware.cors.CORSMiddleware` | Transitive of fastapi |
| httpx | 0.28.1 | Rerank HTTP client (`httpx.AsyncClient(transport=...)`, `httpx.MockTransport` for offline tests) | Already installed (dev group, and a transitive of `openai`); no new package |
| openai | 3.6.0 | Existing `OpenAICompatibleClient` | Unchanged |
| stdlib `fcntl` | 3.12 | `flock(LOCK_EX\|LOCK_NB)` store lock | POSIX-only is fine: NixOS host; no dependency |
| stdlib `argparse` | 3.12 | Launcher CLIs | Parity CLIs already use it |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest / pytest-asyncio | 9.1.1 / per lock | Test runner | Existing |
| jsonschema | in dev group | n/a for this phase | n/a |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `fcntl.flock` | `filelock`, `portalocker` | New dependency for 20 lines; rejected (no new package) |
| `fcntl.flock` | PID file only | Stale after crash; needs liveness check; flock is released by the kernel on exit, including SIGKILL |
| `httpx` for rerank | `aiohttp` (what v1 uses) | `aiohttp` is not installed in `databasise/.venv` (verified: `ModuleNotFoundError`); `httpx` is |
| Prefix-free `RERANK_BINDING_HOST` | base_url + "/rerank" | v1 convention is the full URL including path (see Code Examples); follow v1 |

**Installation:** no new packages. `httpx` should move from the dev group to `[project].dependencies` (it is already in `uv.lock`; this is a metadata change, run `uv lock`). Console scripts require a reinstall: `uv sync --extra rest --extra mcp` (or `uv pip install -e .`).

**Version verification:** `.venv/bin/python -c "import importlib.metadata as m; ..."` returned the versions above on 2026-10-16.

## Package Legitimacy Audit

No new external package is introduced. `httpx` (already installed 0.28.1, already in the approved dev group per `pyproject.toml` comment "Package legitimacy confirmed by the developer 2026-09-06") only changes from dev to runtime dependency. `fcntl`, `argparse`, `socket` are stdlib.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| httpx | PyPI | pre-approved, in uv.lock | n/a | github.com/encode/httpx | pre-approved 2026-09-06 | Approved (dev -> runtime move only) |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
 operator shell / MCP client config / systemd
        |
        |  databasise-rest --store-root R --workspace W --env-file E [--cors-origin O]* [--no-clients] [--host --port --workers]
        |  databasise-mcp  --transport stdio|sse|streamable-http   (same store/workspace/env flags)
        v
 launcher/<rest|mcp> main()
   1. parse args; refuse --workers>1 (message names the store-lock reason)  -----> exit 2, holder (if any) untouched
   2. acquire_store_lock(R)  ---- flock(R/.engine.lock, LOCK_EX|LOCK_NB) ----> held? raise StoreLockedError(root, holder_pid) -> stderr, exit 1
   3. load env file E -> clients.builder.build_clients(env)   (--no-clients skips; missing keys -> MissingParityEnvKeyError names all) -> exit 1
   4. create_app(store_root=R, workspace=W, clients=C, cors_origins=O)   | create_server(store_root=R, workspace=W, clients=C)
   5. uvicorn.run(app, workers=1)                                        | server.run(transport, **host/port kwargs)
        |                                                                    (lock fd stays open for the life of the process)
        v
 Databasise engine (seam/engine.py)  -- opens TraceStore at construction (R/trace.db), kv/vector/graph stores per request
        |
        +--> GET /health -> HealthReport{status, stores, engine, clients{llm,embedding,rerank}}
        +--> parts -> ctx.clients["llm"|"embedding"|"rerank"] -> OpenAICompatibleClient / HttpRerankClient -> provider

 parity CLIs (import_index, build_hipporag_index, run_comparison, run_cross_modality, storage_audit, run_arm.main)
        main(): with store_lock(R): asyncio.run(...)   -> same StoreLockedError while a launcher holds R
```

### Recommended Project Structure
```
databasise/
├── store_lock.py            # StoreLockedError, acquire_store_lock(store_root) / context manager  (top level, beside namespaces.py)
├── clients/
│   ├── builder.py           # NEW: load_env_file, build_clients, REQUIRED_ENV_KEYS, RERANK_ENV_KEYS, 3 named errors
│   ├── rerank.py            # NEW: HttpRerankClient + RerankResponseError family
│   ├── openai_compat.py     # RUN-02/03 edits
│   └── base.py              # unchanged
├── launcher/                # NEW package (add "databasise.launcher" to [tool.setuptools] packages)
│   ├── __init__.py
│   ├── _common.py           # shared argparse options, defaults, client wiring, lock acquisition
│   ├── serve_rest.py        # main() for databasise-rest, also `python -m databasise.launcher.serve_rest`
│   └── serve_mcp.py         # main() for databasise-mcp
├── evidence/COVERAGE.md     # NEW (copy of archived §18.5 record; rows are added here from now on)
└── tests/
    ├── clients/test_build_clients.py, test_rerank_client.py     # NEW
    ├── launcher/test_launchers.py, test_store_lock.py           # NEW
    └── seam/test_rest_cors.py                                   # NEW
.mcp.json (repo root) or docs/ snippet                           # example stdio config
```
Do not name any module or test directory `mcp`, `fastapi` or `uvicorn`: `foreign/_mcp_sdk_guard.py` documents that a test directory named `mcp` already acts as a namespace shadow of the SDK. `launcher/serve_mcp.py` is safe.

### Pattern 1: Re-export the moved builder under the old names (zero importer churn)
**What:** `clients/builder.py` owns the code; `parity/run_arm.py` does `from databasise.clients.builder import (MissingParityEnvError, MissingParityEnvKeyError, UnparseableProviderRoutingError, build_clients as _build_clients, load_env_file as _load_env_file, ...)`.
**Why:** exception identity is preserved (`pytest.raises(MissingParityEnvKeyError)` keeps matching) and every `from databasise.parity.run_arm import ...` and every `monkeypatch.setattr(<importer>, "_build_clients"|"_load_env_file", ...)` keeps working, because monkeypatching targets the importer module's own attribute.
**Importers found by grep (all keep working unchanged under this pattern):**
- Source: `parity/run_comparison.py:58-68`, `parity/run_cross_modality.py:52-57`, `parity/build_hipporag_index.py:56-67`, `parity/storage_audit.py:184-185` (via `_run_arm._build_clients`/`_run_arm._load_env_file`), `eval/remint.py:37-42`, `eval/corpus_ingest.py:48-53`, `eval/aa_run.py:76-81`.
- Tests: `tests/parity/test_naive_arm_end_to_end.py:20-26`, `tests/parity/test_embedder_index_reproduction.py:31` (`_load_env_file`), `tests/eval/test_remint.py:16` (`MissingParityEnvError`), monkeypatch seams at `tests/eval/test_aa_run.py:421-422,488-489`, `tests/eval/test_corpus_ingest.py:136-137`, `tests/eval/test_remint.py:143`.
- Do **not** touch the deliberately separate duplicates `parity/v1_arm.py:98` and `foreign/v1_corpus_adapter.py:79` (`_load_env_file` returning `{}` on an absent file).
- RUN-05 check (3) ("run_arm uses the shared builder, no private copy") is a plain assertion: `run_arm._build_clients is clients.builder.build_clients` and `inspect.getsourcefile(run_arm._build_clients)` ends with `clients/builder.py`.

### Pattern 2: Lock first, then build, then serve
Order in each launcher `main()`: argparse (incl. `--workers`) -> `acquire_store_lock` -> env/clients -> `create_app`/`create_server` -> run. The lock must precede `create_app` because `Databasise.__init__` opens `TraceStore(store_root)` immediately (`seam/engine.py:560`), while graph/kv/vector stores open lazily per request (`_build_stores`, `engine.py:319-346`). Without a launcher-level lock the second process starts, answers `/health`, and fails inside its first graph call. Keep the lock fd referenced for the process lifetime (module global or context-manager object living in `main`).

### Pattern 3: Lock implementation (verified behaviour)
- `os.open(path, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644)`, `fcntl.flock(fd, LOCK_EX | LOCK_NB)`; on success `os.ftruncate(fd, 0)`, write `str(os.getpid())`.
- On `BlockingIOError`: read the file for the holder PID; if empty (holder is between flock and write) retry briefly (~1 s total), then report `holder_pid=None` ("unknown").
- Verified this session: a second `open()` of the same file in the **same** process also gets `BlockingIOError` from `flock` (so in-process unit tests work without subprocesses), the PID written by the holder is readable by the refused opener, and `os.get_inheritable(fd)` is `False` (so the engine's v1 driver subprocesses do not inherit the lock and cannot keep it alive after the launcher exits).
- Lock file location: `<store_root>/.engine.lock` (discretion; any dotfile at store root). `store_root` must be `mkdir(parents=True, exist_ok=True)`'d first. Confirmed nothing enumerates children of `store_root` itself: the only directory iteration found is `stores/vector.py:507` which iterates inside a workspace directory.
- `StoreLockedError(RuntimeError)` attributes `store_root: Path`, `holder_pid: int | None`; message must contain both, e.g. `store root /x is held by databasise process 4242; one engine process per store root`.

### Pattern 4: `create_app(..., cors_origins=())`
Add a keyword-only `cors_origins: Sequence[str] = ()`. Only when non-empty: `app.add_middleware(CORSMiddleware, allow_origins=list(origins), allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type"])`; leave `allow_credentials` at its default `False`. Validate in the launcher (and, defensively, in `create_app`) that each origin matches `^https?://[^/*]+$` with no path, no trailing slash, not `*` (a trailing slash or `*` silently fails to match, see pitfall 6).

### Pattern 5: Rerank client shape
`HttpRerankClient(*, url, model, api_key=None, transport=None, timeout=...)`; `async def rerank(self, query, documents, **kwargs) -> RerankResult`. POST JSON `{model, query, documents, top_n?}` with headers `Content-Type: application/json` and `Authorization: Bearer <key>` (the exact v1 shape, `v1/lightrag/rerank.py:219-222`). Response: `results` list of `{index, relevance_score}`; `ranked_indices = [r["index"] for r in sorted(results, key=-relevance_score)]`.
Validate and raise named errors for: non-200 status, non-JSON body, missing/non-list `results`, an `index` outside `range(len(documents))`, duplicate indices, an empty `documents` list (mirror `EmptyEmbeddingInputError`). Tokens: if the response carries a usable count (Jina/vLLM style `usage.total_tokens`) report `prompt_tokens=total_tokens, call_count=1`; otherwise `TokenAccounting(call_count=1, counted_by='unbudgetable')` (same rule as D-05). Tests inject `httpx.MockTransport`.

### Anti-Patterns to Avoid
- **Passing `--workers` through to uvicorn.** Accept the flag only to refuse values above 1; never forward it. A multi-worker supervisor would respawn the failing worker 2 (`[ASSUMED]` restart behaviour, A3) and make "first launcher keeps answering" depend on supervisor details.
- **Taking the lock inside library functions** (`run_arm()`, `build_index()`, `Databasise.__init__`). Only `main()` functions take it; tests call the library functions in-process and must not contend.
- **Printing to stdout in `databasise-mcp --transport stdio`.** stdout is the protocol channel. Errors, the lock message and the client-build messages go to stderr.
- **Editing `rest.py` route bodies for CORS or health.** `tests/seam/test_rest_transport.py` walks `rest.py`'s AST (forbidden call names: `ResponseEnvelope`, selector names, redact names). `add_middleware(CORSMiddleware, ...)` inside `create_app` is outside that list `[VERIFIED: tests/seam/test_rest_corpus_endpoints.py:325-340 shows the forbidden set]`.
- **A launcher module under `databasise/mcp/`.** `tests/mcp/test_tool_growth_invariant.py` AST-checks `databasise/mcp/*`; keep launchers in `databasise/launcher/`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-process exclusion | PID-file liveness polling, `os.kill(pid, 0)` | `fcntl.flock` on a dedicated lock file | Kernel releases it on any exit incl. SIGKILL; no stale-PID window |
| CORS | Custom OPTIONS route / header injection | `starlette.middleware.cors.CORSMiddleware` | Handles preflight, Vary, simple-request headers |
| HTTP rerank transport + test fake | A raw socket client or a bespoke fake server | `httpx.AsyncClient` + `httpx.MockTransport` | Already installed; no network in tests |
| MCP stdio plumbing | A hand-written JSON-RPC loop | `MCPServer.run("stdio")` and the SDK's `stdio_client` in tests | Verified end to end (see Code Examples) |
| Shadow-safe SDK lookup | A second copy of the sys.path stripping | `_resolves_inside_project` in `foreign/_mcp_sdk_guard.py` + `importlib.machinery.PathFinder` | Already in the module |
| Free port for tests | A fixed port | `socket.socket().bind(("127.0.0.1", 0))` | Avoids CI collisions |
| `.env` parsing | `python-dotenv` | existing `_load_env_file` (moved) | Not an approved dependency (`run_arm.py` docstring) |

**Key insight:** every hard piece already exists in the repo or stdlib; the phase's risk is in ordering and in not breaking the seven importers, two AST proofs and the frozen `HealthReport` shape.

## Runtime State Inventory

This phase adds files and moves code; it does not rename a string or migrate data. The one runtime-state item is the lock file.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None - no key, collection name or id changes. `v1/.parity_v2_store` (gitignored, `v1/.gitignore:26`) holds workspace `shared-4fab18fef508b7bc3dda1cc2d8f12e36` and `trace.db`; lock file will be added next to `trace.db` | Code edit only |
| Live service config | None | None - verified: no service config references the moved names |
| OS-registered state | None today. Operators may later register `databasise-rest` in systemd/launchd | None |
| Secrets/env vars | Env key *names* move modules but do not change: six required keys plus optional `OPENAI_LLM_EXTRA_BODY` and the new optional `RERANK_BINDING_HOST`, `RERANK_MODEL`, `RERANK_BINDING_API_KEY` | Code edit only; never read `v1/.env.parity` |
| Build artifacts | `databasise.egg-info` and the editable finder (`__editable___databasise_0_1_0_finder.py` maps `databasise` to the source dir) have no `entry_points.txt`; console scripts do not exist until reinstall | Run `uv sync --extra rest --extra mcp` after editing `pyproject.toml`; add `databasise.launcher` to the `packages` list |

## Common Pitfalls

### Pitfall 1: The default suite already hits live endpoints
**What goes wrong:** No `live` marker exists anywhere in the tests and `pyproject.toml` has no `markers`/`addopts`. Three tests skip only if `v1/.env.parity` / the v1 index are absent; on this machine they are present, so `.venv/bin/pytest` called the real embedding and LLM endpoints (this session's baseline run did, which is how the research run came to spend a few real calls despite the instruction not to run `-m live`).
**Tests to mark `live`** (identified by fixture `v1_env_parity_path` plus `run_arm`/`compare_arm_on_query` calls without `clients=`):
- `tests/parity/test_embedder_index_reproduction.py::test_embedder_index_reproduces_v1_stored_vectors_on_a_sample` (line 165)
- `tests/parity/test_retrieval_parity.py::test_real_naive_arm_comparison_runs_end_to_end_against_the_real_index` (line 173)
- `tests/parity/test_naive_arm_end_to_end.py::test_real_naive_arm_run_against_the_imported_index_and_live_endpoints` (line 325)
**Not live:** `tests/seam/test_delete_document.py:256` is already opt-in via `DATABASISE_RUN_REAL_DELETE=1` and copies the working dir; leave it (optionally add the marker as well). `tests/parts_core/lightrag/test_full_ingest.py:255` and `test_full_delete.py:102` use a real v1 interpreter against stub inputs; no endpoint.
**How to avoid:** `addopts = '-m "not live"'` plus `markers = ["live: ..."]`. Verified in a scratch project that a later `-m live` on the command line overrides the `addopts` expression (output: `1 passed, 1 deselected` for both default and `-m live`, each selecting the opposite test).
**Warning signs:** a default run that takes network time or spends tokens. Add a guard that fails any non-live test attempting a non-loopback socket connection (autouse fixture patching `socket.socket.connect`) to make "offline suite" a checked claim; loopback must stay allowed for the launcher subprocess tests.

### Pitfall 2: `python -m pytest` vs `.venv/bin/pytest` differ in `sys.path[0]`
**What goes wrong:** `python -m pytest` puts the CWD (`databasise/`) first on `sys.path`, so a bare `find_spec("mcp")` resolves to `databasise/mcp/__init__.py`. Reproduced: `cd databasise && .venv/bin/python -c 'from databasise.foreign._mcp_sdk_guard import mcp_sdk_is_installed; print(mcp_sdk_is_installed())'` printed `False`; from `/tmp` it prints `True`.
**Fix verified:** compute the spec with `importlib.machinery.PathFinder.find_spec("mcp", [e for e in sys.path if not _resolves_inside_project(e)])` and return `spec is not None`. This ignores `sys.modules`, which matters: `find_spec` returns a cached module's `__spec__` when `mcp` is already imported, so the shadow can be cached and leak order-dependent results (probably why only one of the two guarded test modules skipped in the baseline). Keep the "namespace package means shadow" branch irrelevant: PathFinder over the stripped path cannot return the project's own directory.
**Tests for it:** subprocess with `cwd=databasise/` printing `True`; a synthetic shadow case (monkeypatch `_PROJECT_ROOT` to a tmp tree containing only `mcp/__init__.py`, `sys.path` stripped of site-packages) printing `False`; the 8 tests in `tests/evidence/test_falsifier4_evidence.py` under `python -m pytest` pass.

### Pitfall 3: The embedding stub has no `.index`
`tests/clients/test_openai_compat.py:66-70` builds `data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])]`. Reordering by `.index` raises `AttributeError` against it. Update the stub helper to emit `index=i` per item, and decide whether a missing `.index` is a named error (recommended: strict, because the real SDK always sets it) rather than falling back to positional order. Also validate that indices form `0..n-1` exactly (duplicates or gaps are a mis-sized batch in disguise).

### Pitfall 4: RUN-02 makes a no-usage provider refuse queries
`seam/tokens.py:72-85` `assemble_token_breakdown` raises `UnbudgetableParticipantError` for any node whose `tokens.counted_by == 'unbudgetable'`. Today a no-usage response reports `counted_by=<model id>` with `call_count=0` and silently passes. After D-05, any `/query` through a provider that omits `usage` refuses with `UnbudgetableParticipantError` instead of answering. That is the owner-chosen behaviour (D-05, consistent with `full_ingest.py:47` and `hipporag/openie.py:21`), but the planner should state it in the plan and test it once end to end with a no-usage stub. The same rule should govern the rerank client when its response has no usage.

### Pitfall 5: `HealthReport` is frozen and `extra="forbid"`
`seam/corpus.py:194-206`: `class HealthReport(BaseModel)` with `model_config = ConfigDict(frozen=True, extra="forbid")` and fields `status: Literal["ok", "degraded"]`, `stores: dict[str, bool]`, `engine: dict[str, bool]`. D-08's "`/health` reports rerank as not available" needs a new field, recommended `clients: dict[str, bool]` keyed `llm`/`embedding`/`rerank` computed from `self.clients` in `Databasise.health()` (`engine.py:916-963`). Do **not** fold it into `status` (rerank is optional; an unwired rerank must not make the server `degraded`). Existing test `tests/seam/test_corpus_status.py:163-165` asserts only `set(report.engine)`, so it keeps passing; a schema/OpenAPI or dual-transport test that enumerates `HealthReport` fields should be grepped before the change (`tests/seam/test_corpus_status.py:192` iterates model names). The `clients=None` ("ok" with no clients) behaviour is REST-15 / map row M-03 territory (a later phase); Phase 8 only adds the report plus the `--no-clients` flag.

### Pitfall 6: CORS defaults reject the seam's own calls
Reproduced with `fastapi.testclient.TestClient` (starlette 1.6.0), origin `http://localhost:5173`, request `OPTIONS /query` with `Access-Control-Request-Method: POST` and `Access-Control-Request-Headers: content-type`:
- No middleware: `405 {"detail":"Method Not Allowed"}`, no `access-control-*` headers (matches the REST-18 defect; this is the required default).
- `allow_origins=[O]` alone: `400 'Disallowed CORS method'` even though the origin is listed, because Starlette's default `allow_methods` is `GET` only. Must pass `allow_methods=["GET","POST","DELETE"]`.
- `allow_origins=[O], allow_methods=["GET","POST","DELETE"], allow_headers=["Content-Type"]`: preflight `200` with `access-control-allow-origin: http://localhost:5173`; `DELETE` preflight `200`; `GET /health` with the Origin carries the allow header.
- Unlisted origin: preflight `400 'Disallowed CORS origin'` with **no** `access-control-allow-origin`; `GET /health` from it returns 200 with no allow header (the requirement only asks for "no allow header", so 400 is acceptable).
- `allow_origins=["http://localhost:5173/"]` (trailing slash) never matches. Reject such values at argument validation with a clear message.
Route inventory for the allowed-method list (`seam/rest.py` decorators): POST `/query /compare /query/stream /evidence/resolve /trace/resolve /documents /documents/upload /promote /rollback /retire`; GET `/jobs/{id} /health /corpus /corpus/counts`; DELETE `/documents/{id}`.

### Pitfall 7: RocksDB gives no PID and no warning
Reproduced: two processes opening the same `pycozo` rocksdb path; the second raises a bare `Exception: rocksdb::kIOError::kNone` with `IO error: While lock file: <path>/data/LOCK: Resource temporarily unavailable`. No PID, no store-root context, and it happens lazily inside the first graph call. `flock` on a launcher-level file fixes all three. (pandas is not installed and pycozo prints a harmless `pandas feature was requested` notice on stderr; do not treat that as an error.)

### Pitfall 8: Default paths are source-tree relative
`parity/import_index.py:83-85`: `_REPO_ROOT = Path(__file__).resolve().parent.parent.parent`, `DEFAULT_STORE_ROOT = _REPO_ROOT / "v1" / ".parity_v2_store"`. In the current editable install this resolves correctly; a wheel install would resolve under `site-packages`. The launcher should import `DEFAULT_STORE_ROOT` (a `Path`, so the import-boundary scan for the literal `"../v1/"` is not triggered, `tools/check_import_boundary.py:60`) and default the workspace to `shared-4fab18fef508b7bc3dda1cc2d8f12e36` as CONTEXT specifics say. The `.mcp.json` example must use an absolute path or `cwd` for the same reason.

### Pitfall 9: Rerank URL and identity conventions differ from the OpenAI client
- v1's `RERANK_BINDING_HOST` is the **full endpoint URL** including the path (`v1/env.example:134,152`: `http://localhost:8000/rerank`, `https://api.cohere.com/v2/rerank`), and v1 POSTs to it directly (`v1/lightrag/rerank.py` `session.post(base_url, ...)`). Do the same; do not append `/rerank`.
- `RerankResult.resolved_model_identity` must come from the response per the repo rule (`clients/base.py:8-14`, `ModelIdentityMissingError`). Cohere's v2 `/rerank` response has no `model` field `[CITED: docs.cohere.com/reference/rerank]`, so a strict client cannot serve Cohere. See Open Question 1.

### Pitfall 10: Console scripts and extras
`uv run pytest -q` (the configured `workflow.test_command`) syncs default groups only; `rest` and `mcp` are optional extras, so a clean checkout lacks `fastapi`/`mcp` and the RUN-04/RUN-06 tests would skip or fail. Either document `uv sync --extra rest --extra mcp` in the plan's Wave 0 or add both extras to the `dev` dependency group. `[project.scripts]` entries only appear after a reinstall; the entry-point test (RUN-06 check 3) needs it.

## Code Examples

### RUN-04 fix (verified to return the site-packages origin)
```python
# Source: reproduced in this session against databasise/.venv (mcp 2.2.0)
import importlib.machinery, sys

def mcp_sdk_is_installed() -> bool:
    stripped = [e for e in sys.path if not _resolves_inside_project(e)]
    return importlib.machinery.PathFinder.find_spec("mcp", stripped) is not None
```
Output of the probe: `/home/chris/coding/Databasise-2.0-fully-agnostic-system/databasise/.venv/lib/python3.12/site-packages/mcp/__init__.py`.

### MCP launcher core (stdio verified end to end)
```python
# Source: mcp/server/mcpserver/server.py (installed 2.2.0), lines 367-418; verified with ClientSession below
server = create_server(store_root=args.store_root, workspace=args.workspace, clients=clients)
if args.transport == "stdio":
    server.run("stdio")
else:  # host/port are run() kwargs in 2.2.0, not constructor settings
    server.run(args.transport, host=args.host, port=args.port)
```
`run()` signature `[VERIFIED: server.py:367-418]`: `transport: Literal["stdio","sse","streamable-http"] = "stdio"`, `**kwargs`; sse accepts `host, port, sse_path, message_path, ...`; streamable-http accepts `host, port, streamable_http_path, json_response, stateless_http, ...`. Defaults `host="127.0.0.1", port=8000`. Localhost hosts enable DNS-rebinding protection automatically (`server.py:1155-1156`).

### Test client for the stdio launcher (works as written)
```python
# Source: prototype run this session; tools returned
# ['compare','delete','ingest','promote','query','resolve','retire','rollback','status']
from mcp import ClientSession, StdioServerParameters      # import via import_real_mcp in tests (cwd shadow)
from mcp.client.stdio import stdio_client
params = StdioServerParameters(command=str(venv_bin / "databasise-mcp"),
                               args=["--transport", "stdio", "--store-root", str(root), "--workspace", "w", "--no-clients"])
async with stdio_client(params) as (r, w):
    async with ClientSession(r, w) as s:
        await s.initialize()
        names = sorted(t.name for t in (await s.list_tools()).tools)
```
In the test, import these through `databasise.foreign._mcp_sdk_guard.import_real_mcp("mcp")` / `import_real_mcp("mcp.client.stdio")` because `databasise/tests/mcp/` and `databasise/mcp/` can shadow `mcp`. Compare with `sorted(t.name for t in await create_server(...).list_tools())` and with `databasise.mcp.TOOL_NAMES`.

### Store lock
```python
# Source: verified semantics this session (same-process second open refused; PID readable; fd not inheritable)
import fcntl, os
from pathlib import Path

class StoreLockedError(RuntimeError):
    def __init__(self, store_root: Path, holder_pid: int | None):
        self.store_root, self.holder_pid = store_root, holder_pid
        super().__init__(f"store root {store_root} is held by databasise process {holder_pid or 'unknown'}; "
                         "one engine process per store root")

def acquire_store_lock(store_root: Path) -> int:
    store_root.mkdir(parents=True, exist_ok=True)
    fd = os.open(store_root / ".engine.lock", os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raw = os.pread(fd, 32, 0).decode().strip()
        os.close(fd)
        raise StoreLockedError(store_root, int(raw) if raw.isdigit() else None) from None
    os.ftruncate(fd, 0); os.write(fd, str(os.getpid()).encode())
    return fd          # caller keeps it open until exit
```
Wrap in a context manager for the parity CLIs (`with store_lock(root): ...`) and add the retry-on-empty-PID read.

### RUN-09 rewrite (replaces `tests/seam/test_rest_corpus_endpoints.py:345-356`)
```python
# Engine write site: databasise/seam/engine.py:707-709
#   inbox_dir = self.store_root / "corpus-inbox"
#   on_disk_path = inbox_dir / generated_on_disk_name(document_id)      # id = uuid.uuid4().hex (engine.py:678)
def test_generated_on_disk_name_is_reachable_for_a_multipart_uploaded_document(client, store_root):
    response = client.post("/documents/upload", files={"file": ("../escape.pdf", b"raw pdf bytes", "application/pdf")})
    assert response.status_code == 200
    written = list((store_root / "corpus-inbox").iterdir())
    assert len(written) == 1
    stem = written[0].name.removesuffix(".bin")
    assert re.fullmatch(r"[0-9a-f]{32}", stem)
    assert written[0].name == generated_on_disk_name(stem)
    assert not (store_root / "escape.pdf").exists() and not (store_root.parent / "escape.pdf").exists()
```
`store_root` fixture is `tmp_path / "store_root"` (`tests/conftest.py:34-38`), so `store_root.parent` is the tmp dir that a `../escape.pdf` write from `corpus-inbox` would reach one level up (`store_root/escape.pdf`) and two levels up. Mutation (per RUN-09): change the write to `inbox_dir / <caller file_name>`; `rest.py:330` passes `file_name=file.filename`.

### RUN-10 shared state (replaces `:441-442` and `:480-481`)
`_patch_status_sequence` (line ~366) returns a mutable `state` and its fake reports `{current_status: 1}` counts. The stub delete body (`_make_stub_delete_body`, line ~85) runs in the test process, so it can mutate that state: add `on_success: Callable[[], None] | None` to `_make_stub_delete_body` and a `_make_registry(on_delete=...)` pass-through; the fake status handler returns an empty `documents`/`_stub_counts={}` once `state["deleted"]` is true. Assertions after the delete: `by_status.get("processed", 0) == 0` and `total == 0` (it was `1` before; assert the before-value too). Mutation check: a delete body that returns `success` without calling the hook leaves counts at 1 and both rewritten tests fail.

### RUN-01 repoint plus non-vacuity
```python
_COVERAGE_PATH = Path(__file__).resolve().parents[2] / "evidence" / "COVERAGE.md"   # parents[2] = databasise/
assert _COVERAGE_PATH.is_file(), f"§18.5 coverage record not found; expected at {_COVERAGE_PATH}"
```
Put the assertion at module level so a missing file fails collection with the path in the message (RUN-01: "the module fails with an assertion that names the expected path"). The table headers the parser needs are `| operation | transports | plan |` and `| operation | decision | reason |` (`test_tool_growth_invariant.py`, `_parse_markdown_table`, uses `startswith`), both present in the archived file's §4. Copy the whole file verbatim and add a one-paragraph header saying "live record; v1.0 archive stays frozen". Refactor the body of `test_every_tool_has_a_coverage_row...` into `_check_coverage(markdown, tool_names)` so the non-vacuity test can call it with `TOOL_NAMES | {"__extra__"}` and `pytest.raises(AssertionError)`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `FastMCP` (`mcp.server.fastmcp`) | `MCPServer` (`mcp.server.mcpserver`), `run(transport, **kwargs)` | mcp 2.x | Already used by `databasise/mcp/server.py`; host/port are `run()` kwargs |
| `python-igraph` | `igraph` | n/a | unrelated; unchanged |

**Deprecated/outdated:** the `parity/run_arm.py` module docstring wording "reads `v1/.env.parity`" for client construction is now only the parity default; update the docstring when the builder moves.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | vLLM's `/rerank` response includes `model` and `usage.total_tokens` (Jina-compatible). Only "compatible with Cohere v1/v2 and implements Jina's v1 rerank API" was confirmed from vLLM's docs; the field list was not | Pattern 5, Pitfall 9 | Client raises `ModelIdentityMissingError` against a server that omits `model`; fix by owner decision in Open Question 1 |
| A2 | Text Embeddings Inference (TEI) can be driven through the same request/response shape (D-07 asserts this). TEI's native `/rerank` is believed to return a bare list with `score`, not `{results:[{relevance_score}]}` | D-07 scope | Client rejects TEI's native shape with a named error; document that only Cohere/Jina-shaped servers (incl. vLLM) are supported |
| A3 | uvicorn's multi-worker supervisor respawns a worker that exits non-zero | Anti-patterns | Only affects the reason for refusing `--workers>1` up front; the design does not depend on it |
| A4 | The endpoint's embedding noise stays near the cosine 0.9961-0.9965 seen in DEFECTS `tests-run/T2` run A; the D-14 threshold of about 0.995 must be set from the new ~5 measured runs, not from this value | RUN-11 | Threshold too tight (flaky) or too loose (weak parity claim); mitigated by measuring |
| A5 | Cohere charges per "search unit" so its usage is not a token count; treating Cohere tokens as unbudgetable is acceptable | Pattern 5 | Cohere runs would be flagged unbudgetable and refuse queries; only matters if the owner points `RERANK_*` at Cohere |

## Open Questions

1. **`resolved_model_identity` for rerank servers that do not echo a model (Cohere).**
   - Known: repo rule forbids substituting the requested model id (`clients/base.py:8-14`); Cohere's response has no `model` `[CITED: docs.cohere.com/reference/rerank]`.
   - Unclear: whether the owner will point `RERANK_*` at Cohere or at a self-hosted vLLM.
   - Recommendation: follow the rule (raise `ModelIdentityMissingError`), tell the owner Cohere is unsupported until an explicit, recorded exception is approved (for example `RERANK_MODEL_IDENTITY` env key). Do not decide this silently in code.
2. **Adding `clients` to `HealthReport` changes the REST/MCP health payload.**
   - Known: D-08 requires `/health` to report rerank unavailability; the model is frozen/forbid-extra.
   - Unclear: whether the §18 contract text (`docs/system-model/CONTRACT.md` §18) pins the health field set.
   - Recommendation: add `clients: dict[str, bool]` (additive field), grep `docs/system-model/` and `docs/gui/API-INVENTORY.md` for health shape pins before the change, and list the field in `evidence/COVERAGE.md` notes.
3. **Which parity entry points take the lock.** D-03 names five; `parity/run_arm.py:344 main()` also opens the same default store (`run_arm(args.arm, args.query)` with `DEFAULT_STORE_ROOT`). Recommendation: include it as the sixth. `eval/corpus_ingest.py` and `eval/aa_run.py` use their own `_EVAL_INGEST_STORE_ROOT`, not the parity store; leave them out and say so.
4. **Whether `--env-file` has a default.** Parity CLIs default to `DEFAULT_V1_ENV_PARITY` (`run_arm.py:49`). For the launcher, a default of that path is convenient but silently ties a served process to parity credentials. Recommendation: no default; required unless `--no-clients` (D-11), error names the flag.
5. **Amending the ledger/requirement text for RUN-05 and ROADMAP criterion 1** (D-07/D-08 note). Needs the owner's approval through `scripts/ledger-amend.py`; the plan must include that step and must not drop the rerank client to satisfy the old wording.
6. **Live executions in this phase.** RUN-11 (5 runs of the embedder test) and the optional `-m live` rerank test spend real endpoint calls and need the owner's env file at runtime. Plan them as an explicit end-of-phase human step with the recorded numbers committed into the test docstring.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (venv) | everything | yes | 3.12.13 (`databasise/.venv`) | none |
| uv | reinstall for console scripts | yes | 0.11.21 | `.venv/bin/python -m pip install -e .` if absent |
| mcp SDK | RUN-04, RUN-06 | yes | 2.2.0 | none (extra must be installed) |
| fastapi / uvicorn / starlette | RUN-06, RUN-08 | yes | 0.141.1 / 0.52.4 / 1.6.0 | none |
| httpx | rerank client and tests | yes | 0.28.1 | none |
| aiohttp | (v1 only) | no | n/a | not needed; use httpx |
| codebase-memory-mcp binary | falsifier-4 native-leg test | yes | `/home/chris/.local/bin/codebase-memory-mcp` | test skips with a true reason |
| v1 venv | opaque-part smoke tests | yes | `v1/.venv/bin/python` | tests skip |
| Live embedding/LLM endpoint | RUN-11 only | env file present (not read) | n/a | `-m live` deselected |
| Rerank endpoint | optional `-m live` rerank test (D-10) | unknown; waits on owner env file | n/a | offline `MockTransport` tests |
| Free localhost TCP port | launcher subprocess tests | yes | ephemeral via bind(0) | none |

**Missing dependencies with no fallback:** none.
**Missing dependencies with fallback:** rerank live endpoint (offline tests cover the code).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-asyncio (`asyncio_mode = "auto"`) |
| Config file | `databasise/pyproject.toml` `[tool.pytest.ini_options]` (today only `asyncio_mode`, `testpaths`; Phase 8 adds `markers` and `addopts`) |
| Quick run command | `cd databasise && .venv/bin/pytest -q tests/<file>` |
| Full suite command | `cd databasise && .venv/bin/pytest -q -rs && .venv/bin/python -m pytest -q -rs` |
| Full-suite runtime (measured) | ~3 to 3.7 minutes per invocation |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RUN-01 | coverage cross-check runs; missing file names path; extra tool name fails the check | unit | `.venv/bin/pytest -q tests/mcp/test_tool_growth_invariant.py` (expect 7 passed + new non-vacuity case) | exists; edit |
| RUN-02 | `usage=None` -> `call_count==1`, `counted_by=='unbudgetable'` for chat and embed; usage present unchanged | unit | `.venv/bin/pytest -q tests/clients/test_openai_compat.py -k usage` | exists; add cases |
| RUN-03 | empty choices / None content / 2 vectors for 3 inputs raise named errors; index `[1,0]` returns input order | unit | `.venv/bin/pytest -q tests/clients/test_openai_compat.py -k "choices or content or mis_sized or order"` | exists; add cases; fix stub `.index` |
| RUN-04 | subprocess `cwd=databasise/` prints `True`; synthetic shadow prints `False`; falsifier-4 native leg runs under `python -m pytest` | unit + subprocess | `.venv/bin/python -m pytest -q tests/evidence/test_falsifier4_evidence.py tests/foreign` | evidence test exists; add `tests/foreign/test_mcp_sdk_guard.py` (new dir, no `mcp` in name) |
| RUN-05 | builder returns `{llm,embedding}`; names every missing key; partial `RERANK_*` names missing rerank keys; all `RERANK_*` returns `rerank` too; `run_arm` uses shared builder; `live_rerank=True` with builder clients raises `ClientNotWiredError` naming `rerank`; rerank client request/response/error cases via `MockTransport`; `/health` reports `clients` | unit | `.venv/bin/pytest -q tests/clients/test_build_clients.py tests/clients/test_rerank_client.py tests/seam/test_corpus_status.py tests/parity/test_naive_arm_end_to_end.py` | build/rerank new; others exist |
| RUN-06 | `databasise-rest` subprocess serves `/health` 200; `databasise-mcp --transport stdio` lists same tools as in-process; both console scripts in entry points | integration (subprocess, localhost only) | `.venv/bin/pytest -q tests/launcher/test_launchers.py` | new (Wave 0) |
| RUN-07 | `--workers 2` exits non-zero naming the store-lock reason; second REST and second MCP launcher exit non-zero with root and PID while first keeps answering `/health`; in-process lock unit tests; parity `main()` refuses while held | unit + integration | `.venv/bin/pytest -q tests/launcher/test_launchers.py tests/launcher/test_store_lock.py` | new |
| RUN-08 | allowed preflight 200 with matching header; GET with Origin carries header; unlisted origin has no allow header; no origins -> 405 | unit (TestClient) | `.venv/bin/pytest -q tests/seam/test_rest_cors.py` | new |
| RUN-09 | exactly one 32-hex `.bin` in `corpus-inbox`; no `escape.pdf` in or above store root; fails under the write-path mutation | unit + mutation | `.venv/bin/pytest -q tests/seam/test_rest_corpus_endpoints.py -k generated_on_disk_name` | exists; rewrite |
| RUN-10 | after delete, `by_status['processed']==0` and `total==0` (REST and in-process); fails under the stub-delete mutation | unit + mutation | `.venv/bin/pytest -q tests/seam/test_rest_corpus_endpoints.py -k round_trip` | exists; rewrite |
| RUN-11 | live reproduction passes 5 times with `-m live`; deselected by default | live (owner-run) | `for i in 1 2 3 4 5; do .venv/bin/pytest -q -m live tests/parity/test_embedder_index_reproduction.py; done`; default: `.venv/bin/pytest -q tests/parity/test_embedder_index_reproduction.py` shows `1 deselected` | exists; edit threshold, docstring, marker |
| RUN-12 | both invocation styles report 0 failed; no skip reason contradicts the environment; live tests only under `-m live` | gate script | `python scripts/check_offline_suite.py` (new; runs both styles with `-rs`, fails on any failure, and fails on a `found=False` skip while `importlib.metadata.version("mcp")` succeeds) | new (Wave 0) |

### Sampling Rate
- **Per task commit:** the task's own quick command above (seconds), plus `tests/test_import_boundary.py` and `tests/seam/test_rest_transport.py` when `rest.py`, `clients/` or new top-level modules change.
- **Per wave merge:** `cd databasise && .venv/bin/pytest -q -rs` (about 3.5 minutes).
- **Phase gate:** both `.venv/bin/pytest -q -rs` and `.venv/bin/python -m pytest -q -rs` show `0 failed`, the gate script passes, and the owner-run `-m live` embedder test has passed 5 times, before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/launcher/test_launchers.py`, `tests/launcher/test_store_lock.py` - RUN-06/07 (shared fixtures: free-port helper, stub env writer with the six keys, readiness poll on `/health` with ~30 s timeout because engine import loads faiss/igraph/scipy)
- [ ] `tests/clients/test_build_clients.py`, `tests/clients/test_rerank_client.py` - RUN-05
- [ ] `tests/seam/test_rest_cors.py` - RUN-08
- [ ] `tests/foreign/test_mcp_sdk_guard.py` - RUN-04
- [ ] `scripts/check_offline_suite.py` - RUN-12 gate
- [ ] `databasise/evidence/COVERAGE.md` - RUN-01 (data file the test depends on)
- [ ] `pyproject.toml`: `markers`, `addopts`, `[project.scripts]`, `databasise.launcher` in `packages`, `httpx` dependency; then `uv lock` and `uv sync --extra rest --extra mcp`
- [ ] Optional guard fixture blocking non-loopback sockets for non-live tests (Pitfall 1)

## Security Domain

`security_enforcement` is `false` in `.planning/config.json`, so no ASVS table is produced. Phase-relevant notes for the planner (not an ASVS audit): the REST app has no authentication (documented exposure note in `seam/rest.py`), so the launcher must default `--host` to `127.0.0.1`; CORS must stay an exact-origin allow-list without credentials; the lock error message prints the store root and a PID only; env values (API keys) must never be printed in launcher errors (name keys only, as `MissingParityEnvKeyError` already does); the rerank client must not log request headers.

## Sources

### Primary (HIGH confidence)
- Repository files read this session: `databasise/parity/run_arm.py` (1-330), `databasise/clients/{openai_compat,base,__init__}.py`, `databasise/parts_core/lightrag/rerank.py`, `databasise/seam/{rest,engine,corpus,tokens}.py` (relevant ranges), `databasise/mcp/{server,_sdk,__init__}.py`, `databasise/foreign/_mcp_sdk_guard.py`, `databasise/pyproject.toml`, `databasise/tests/mcp/test_tool_growth_invariant.py`, `tests/seam/test_rest_corpus_endpoints.py`, `tests/parity/{test_embedder_index_reproduction,conftest,test_naive_arm_end_to_end}.py`, `tests/clients/test_openai_compat.py`, `tests/evidence/test_falsifier4_evidence.py`, `tools/check_import_boundary.py`, `parity/import_index.py`, `v1/env.example:125-165`, `v1/lightrag/rerank.py:182-345`, `docs/gui/DEFECTS.json` (uids cited by RUN-01..12), `.planning/{REQUIREMENTS,ROADMAP}.md`, `08-CONTEXT.md`.
- Installed mcp 2.2.0 source: `.venv/lib/python3.12/site-packages/mcp/server/mcpserver/server.py` lines 360-418 and 1060-1140.
- Reproductions in this session: full-suite runs (both invocation styles), `mcp_sdk_is_installed()` from `databasise/` (False) and `/tmp` (True), `PathFinder` fix, CORS matrix with `TestClient`, RocksDB second-open error, `flock` same-process refusal and PID read, `os.get_inheritable`, pytest `addopts -m` override, stdio client/server round trip listing nine tools.

### Secondary (MEDIUM confidence)
- [CITED: docs.cohere.com/reference/rerank] request fields `model, query, documents, top_n, max_tokens_per_doc, priority`; response `results[{index, relevance_score}]`, `id`, `meta` with `billed_units.search_units`; no `model` field in the response.
- [CITED: docs.vllm.ai/en/latest/serving/online_serving/] `/rerank`, `/v1/rerank`, `/v2/rerank` "Implements Jina AI's v1 rerank API", "compatible with Cohere's v1 & v2 rerank APIs".

### Tertiary (LOW confidence)
- vLLM response field list, TEI native shape, uvicorn worker respawn (Assumptions A1-A3).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - versions read from the venv; no new package.
- Architecture: HIGH - every integration point read in code; lock and CORS behaviour reproduced.
- Pitfalls: HIGH for items 1-8, 10 (reproduced or read); MEDIUM for item 9 (rerank provider details partly assumed).
- Rerank wire shape: MEDIUM - Cohere documented; vLLM/TEI field lists assumed.

**Research date:** 2026-10-16
**Valid until:** 2026-11-15 (stable repo; re-check mcp SDK API if the dependency is bumped past 2.2.x)
