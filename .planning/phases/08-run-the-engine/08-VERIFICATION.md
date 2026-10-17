---
phase: 08-run-the-engine
verified: 2026-10-17T03:30:00Z
status: passed
score: 5/5 roadmap success criteria verified (RUN-11 measurement owner-deferred, tracked as human item)
covered_files:
  - ".planning/phases/08-run-the-engine/08-01-PLAN.md"
  - ".planning/phases/08-run-the-engine/08-01-SUMMARY.md"
  - ".planning/phases/08-run-the-engine/08-02-PLAN.md"
  - ".planning/phases/08-run-the-engine/08-02-SUMMARY.md"
  - ".planning/phases/08-run-the-engine/08-03-PLAN.md"
  - ".planning/phases/08-run-the-engine/08-03-SUMMARY.md"
  - ".planning/phases/08-run-the-engine/08-04-PLAN.md"
  - ".planning/phases/08-run-the-engine/08-04-SUMMARY.md"
  - ".planning/phases/08-run-the-engine/08-05-PLAN.md"
  - ".planning/phases/08-run-the-engine/08-05-SUMMARY.md"
  - ".planning/phases/08-run-the-engine/08-06-PLAN.md"
  - ".planning/phases/08-run-the-engine/08-06-SUMMARY.md"
  - ".planning/phases/08-run-the-engine/08-07-PLAN.md"
  - ".planning/phases/08-run-the-engine/08-07-SUMMARY.md"
  - ".planning/phases/08-run-the-engine/08-08-PLAN.md"
  - ".planning/phases/08-run-the-engine/08-08-SUMMARY.md"
  - ".planning/phases/08-run-the-engine/08-09-PLAN.md"
  - ".planning/phases/08-run-the-engine/08-09-SUMMARY.md"
  - ".planning/phases/08-run-the-engine/08-10-PLAN.md"
  - ".planning/phases/08-run-the-engine/08-10-SUMMARY.md"
  - "databasise/clients/builder.py"
  - "databasise/clients/openai_compat.py"
  - "databasise/clients/rerank.py"
  - "databasise/evidence/COVERAGE.md"
  - "databasise/examples/mcp-client.stdio.json"
  - "databasise/foreign/_mcp_sdk_guard.py"
  - "databasise/launcher/__init__.py"
  - "databasise/launcher/serve_mcp.py"
  - "databasise/launcher/serve_rest.py"
  - "databasise/pyproject.toml"
  - "databasise/seam/rest.py"
  - "databasise/store_lock.py"
  - "databasise/tests/mcp/test_tool_growth_invariant.py"
  - "databasise/tests/parity/test_embedder_index_reproduction.py"
  - "databasise/tests/seam/test_rest_corpus_endpoints.py"
  - "databasise/tools/check_offline_suite.py"
covered_digest: "v3:sha256:c091dee14e40134ec856a5a4f2a9a6d51b2bdd9ce4a63f3aad4adf51dc6f1444"
behavior_unverified: 0
overrides_applied: 0
deferred:
  - truth: "RUN-11: embedder reproduction test gives one verdict on repeated runs; _SIMILARITY_THRESHOLD set from five measured live runs"
    addressed_in: ".planning/TESTING-PLAN.md section 2 (owner-deferred, not a later roadmap phase)"
    evidence: "Owner, 2026-10-16: 'we dont need to run any of those mesherment untill everthing is build. we only run things for debugging'. RUN-11 is intentionally left Pending in REQUIREMENTS.md."
human_verification:
  - test: "RUN-11 live measurement: run the five -m live passes of tests/parity/test_embedder_index_reproduction.py and set _SIMILARITY_THRESHOLD from the observed minimum"
    expected: "Same verdict on repeated runs; threshold, date and endpoint model recorded in the module docstring; then RUN-11 can be marked complete"
    why_human: "Spends tokens against a real endpoint and needs the owner's env file (never read by agents). Owner-deferred to TESTING-PLAN.md section 2."
  - test: "Parity-env builder compatibility (no spend), RUN-05: build_clients(load_env_file(v1/.env.parity)) prints ['embedding','llm']"
    expected: "Real parity env file satisfies the six required keys with no MissingParityEnvKeyError"
    why_human: "Reading v1/.env.* is blocked for agents. Owner-deferred to TESTING-PLAN.md section 2."
  - test: "Live rerank client (optional, D-10): DATABASISE_RERANK_ENV_FILE=<file> pytest -m live tests/clients/test_rerank_client.py"
    expected: "Live rerank call returns a ranking in index order against a real cohere/jina/aliyun endpoint"
    why_human: "Needs an owner-supplied RERANK_* env file and spends tokens. Owner-deferred."
  - test: "Confirm the post-review behaviour changes match intent: refusal of wildcard binds even with --allow-remote-unauthenticated (WR-03, IN-05 b), cross-site write Origin guard (WR-01), builder refusals now caught by every client-building CLI (WR-02)"
    expected: "Owner agrees these stricter refusals are wanted (08-REVIEW-FIX.md marks them 'requires human verification')"
    why_human: "Intent/policy judgment, not a defect check. The run_comparison per-query catch (IN-07) has no test."
  - test: "Owner ledger steps: run the twelve ledger-amend set lines in 08-10-SUMMARY.md 'Owner ledger steps (pending)'; do not run the RUN-11 line until its live runs are done"
    expected: "BAK ledger rows RUN-01..RUN-12 get test_ref (the SessionStart hook currently reports all 12 as open with empty test_ref)"
    why_human: "Ledger test_ref filling and record-fail are owner-only by design."
---

# Phase 8: Run the Engine Verification Report

**Phase Goal:** An operator can start the engine as a served process from the installed package, with real model clients and one engine process per store root, and the offline test suite is green so every later fix can be checked end to end
**Verified:** 2026-10-17
**Status:** passed (owner-approved 2026-10-16: "All good — continue"; live items owner-deferred to TESTING-PLAN.md §2)
**Re-verification:** No, initial verification (no prior VERIFICATION.md existed)

The goal is achieved in the codebase. Nothing is FAILED. The status is `human_needed` only because RUN-11 (measured threshold, five live runs) and two no-spend/live checks were deliberately deferred by the owner, and because the post-execution review fixes ask for a human intent check.

## Goal Achievement

### Observable Truths (ROADMAP success criteria, the contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | One installed command starts REST, GET /health is 200 with llm and embedding clients from the shared builder; missing required keys stop startup naming every key; rerank reported not available unless RERANK_BINDING + its three keys | VERIFIED | Ran the installed `databasise-rest` against a stub env (six keys): /health returned `"clients":{"llm":true,"embedding":true,"rerank":false}`. Env file with one key exits 1 naming the other five (`LLM_MODEL, LLM_BINDING_API_KEY, EMBEDDING_BINDING_HOST, EMBEDDING_MODEL, EMBEDDING_BINDING_API_KEY`). No env file and no `--no-clients` exits 2. `clients/builder.py` `build_clients` implements binding-aware optional rerank, `null`/empty = off, partial set = `MissingParityEnvKeyError` naming rerank keys. Amended wording (owner-approved) matches code. |
| 2 | `databasise-mcp --transport stdio` lists same tools as in-process server; second launcher on same store root or `--workers 2` exits non-zero with named store-lock error (root + holder PID) while first keeps answering /health | VERIFIED | Live: first REST launcher held `.engine.lock` (content = its PID 1523814). A second `databasise-mcp` and a second `databasise-rest` on the same root each exited 1 with `store root <root> is held by databasise process 1523814; one engine process per store root (G-36)`; first still returned /health 200. `--workers 2` exits 2 naming `<store_root>/.engine.lock (G-36)` and creates no lock file. `store_lock.py` uses `fcntl.flock` LOCK_EX\|LOCK_NB, O_CLOEXEC, PID written. Tool-list equality covered by `test_databasise_mcp_stdio_lists_the_in_process_tool_set` (passed in the gate). All five parity CLIs (import_index, build_hipporag_index, run_arm, run_comparison, run_cross_modality, storage_audit) import and use the lock (D-03). |
| 3 | `--cors-origin <origin>`: preflight from that origin succeeds, unlisted origin gets no allow header; no flag = unchanged | VERIFIED | Live: OPTIONS /query with `Origin: http://localhost:5173` returned 200 with `access-control-allow-origin: http://localhost:5173`; an unlisted origin returned 400 with no allow-origin header. `seam/rest.py` `validate_cors_origin` rejects non-exact origins; `create_app(cors_origins=())` adds nothing by default. |
| 4 | No-usage response = one unbudgetable call; empty choices, None content, mis-sized embedding batch, out-of-order items raise named errors or are returned in input order | VERIFIED | `clients/openai_compat.py`: `_token_accounting(None)` returns `call_count=1, counted_by="unbudgetable"` (equals `seam/tokens.UNBUDGETABLE_SENTINEL`); `EmptyChoicesError`, `MissingCompletionContentError`, `EmbeddingBatchMismatchError` (count and index set 0..n-1 check); vectors sorted by `.index`. Tests `test_16/20/21/23/24/25` in `tests/clients/test_openai_compat.py` passed in the gate. |
| 5 | From `databasise/`, `.venv/bin/pytest` and `.venv/bin/python -m pytest` both 0 failed; COVERAGE cross-check runs; mcp SDK detected; upload/delete round-trip tests fail under their mutations; live tests only under `-m live` | VERIFIED | Gate run by this verifier after the review fixes (`tools/check_offline_suite.py`, exit 0): `pytest -q -rs: 1251 passed, 1 skipped, 4 deselected in 233.70s` and `python -m pytest -q -rs: 1251 passed, 1 skipped, 4 deselected in 214.73s`. The gate exits 1 on any contradictory "not installed" skip while mcp is installed, so the 1 skip is not contradictory (I did not identify its reason; the 52 tests in the mcp/falsifier-4/import-boundary modules ran with 0 skips). `addopts = '-m "not live"'` and the `live` marker are registered in pyproject.toml; 4 deselected. `_COVERAGE_PATH` points at `databasise/evidence/COVERAGE.md` (exists) and `_require_coverage_file` raises an `AssertionError` naming the expected path via an explicit `raise` (survives `python -O`). Mutation controls recorded in 08-04-SUMMARY (RUN-09: `0 == 1`; RUN-10: `assert 1 == 0` under mutated delete hook). |

**Score:** 5/5 roadmap truths verified.

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|--------------|----------|
| 1 | RUN-11 measured threshold and five live passes | Owner-deferred to `.planning/TESTING-PLAN.md` section 2 | Owner quote in the file header. `_SIMILARITY_THRESHOLD` stays 0.999 and its docstring says it is unmeasured. The `live` marker, default deselection and the RUN-02-dependent `tokens.call_count > 0` assertion (line 207) are in place; only the measurement is missing. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/clients/builder.py` | Shared builder, `BUILDER_REFUSALS` | VERIFIED | 212 lines; used by launcher and by run_arm/storage_audit/run_cross_modality/build_hipporag_index/aa_run/corpus_ingest/remint |
| `databasise/clients/rerank.py` | `HttpRerankClient`, 3 bindings | VERIFIED | 197 lines; type-checks model, scores (non-finite and overflow refused), no key in messages |
| `databasise/clients/openai_compat.py` | RUN-02/03 fixes | VERIFIED | See truth 4 |
| `databasise/store_lock.py` | flock store lock | VERIFIED | See truth 2 |
| `databasise/launcher/{__init__,serve_rest,serve_mcp}.py` | Two launchers | VERIFIED | `[project.scripts]` has `databasise-rest` and `databasise-mcp`; `entry_points` lists both; `python -m` modules have `__main__` guards |
| `databasise/examples/mcp-client.stdio.json` | Example stdio client config | VERIFIED | Invokes `databasise-mcp --transport stdio` with store/workspace/env-file |
| `databasise/foreign/_mcp_sdk_guard.py` | `mcp_sdk_is_installed` shadow-safe | VERIFIED | Uses PathFinder with project paths stripped; same stripping as `import_real_mcp` |
| `databasise/evidence/COVERAGE.md` | Live §18.5 record | VERIFIED | Exists, differs from frozen archive copy (new rows), archive untouched |
| `databasise/tools/check_offline_suite.py` | RUN-12 gate | VERIFIED | Ran it: exit 0 |
| `databasise/tests/seam/test_rest_corpus_endpoints.py` | RUN-09/10 rewrites | VERIFIED | Reads the inbox on disk; counts asserted 1 to 0 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `serve_rest.main` | `build_clients` | `open_engine` (lock first, then clients) | WIRED | `launcher/__init__.py:open_engine`; lock fd closed on builder failure |
| `serve_rest.build_app` | `seam.rest.create_app` | `cors_origins=args.cors_origin` | WIRED | Plus TrustedHost and Origin guard middleware |
| `serve_mcp.main` | `mcp.create_server(...).run(transport)` | direct | WIRED | stdio, sse, streamable-http |
| `/health` clients map | builder clients | `seam/engine.py:964` | WIRED | Live /health showed `rerank:false` |
| `parts_core/lightrag/rerank.py` | `ctx.clients["rerank"]` | unwired raises `ClientNotWiredError` | WIRED | Covered by `test_live_rerank_with_builder_clients_raises_client_not_wired_naming_rerank` |
| Parity CLIs | `store_lock` | `main()` | WIRED | grep confirms import and `StoreLockedError` handling in each |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| /health clients map | `clients` | actual builder dict keys | Yes (llm/embedding true, rerank false observed live) | FLOWING |
| `.engine.lock` | holder PID | `os.getpid()` | Yes (file content matched the process PID) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Installed REST serves /health | `databasise-rest --store-root <tmp> --workspace w --port 18765 --env-file <stub> --cors-origin http://localhost:5173` then curl | 200, clients map as above | PASS |
| CORS preflight listed / unlisted | curl OPTIONS /query | 200 + header / 400 + no header | PASS |
| Second MCP and REST launcher refused | run on same root | exit 1, root + PID named, first still 200 | PASS |
| `--workers 2` refused | `databasise-rest --workers 2 --no-clients` | exit 2, store-lock message, no lock file | PASS |
| Missing keys / no env file | see truth 1 | exit 1 / exit 2 | PASS |
| Entry points installed | `entry_points(group='console_scripts')` | `['databasise-mcp','databasise-rest']` | PASS |
| Falsifier-4 / import boundary / mcp SDK modules | `pytest -q -rs` on 4 modules | 52 passed, 0 skipped | PASS |

### Probe Execution

SKIPPED: no `scripts/*/tests/probe-*.sh` probes declared by this phase's plans.

### Requirements Coverage

All twelve IDs are claimed by at least one PLAN frontmatter and all appear in REQUIREMENTS.md. No orphaned requirements.

| Requirement | Source Plan(s) | Status | Evidence |
|-------------|----------------|--------|----------|
| RUN-01 | 08-03, 08-10 | SATISFIED | COVERAGE path fixed to `databasise/evidence/COVERAGE.md`; explicit missing-file assertion; tests pass |
| RUN-02 | 08-02, 08-10 | SATISFIED | unbudgetable sentinel, call_count=1 |
| RUN-03 | 08-02, 08-10 | SATISFIED | four named behaviours in code and tests |
| RUN-04 | 08-03, 08-10 | SATISFIED | `mcp_sdk_is_installed` shadow-safe; native leg runs under both styles |
| RUN-05 | 08-01, 08-05, 08-10 | SATISFIED (owner-amended wording) | Shared builder + optional rerank by binding; messages hold keys never values |
| RUN-06 | 08-01, 08-06, 08-10 | SATISFIED | Scripts, `python -m`, defaults, example config, live health |
| RUN-07 | 08-01, 08-06, 08-07, 08-10 | SATISFIED | flock lock, workers=1, named error with root and PID, parity CLIs lock |
| RUN-08 | 08-08, 08-10 | SATISFIED | Live preflight check |
| RUN-09 | 08-04, 08-10 | SATISFIED | Disk-reading test with 32-hex stem |
| RUN-10 | 08-04, 08-10 | SATISFIED | Counts 1 to 0 over REST and in-process |
| RUN-11 | 08-01 (claimed), 08-10 (excluded) | NOT COMPLETE, OWNER-DEFERRED | Marker/addopts/RUN-02 dependency done; threshold unmeasured. REQUIREMENTS.md correctly shows Pending. Note 08-01-SUMMARY lists RUN-11 under `requirements-completed`; that claim is wrong and 08-10-SUMMARY corrects it. |
| RUN-12 | 08-01, 08-09, 08-10 | SATISFIED | Gate rerun after review fixes: both styles 1251 passed, 0 failed |

### Anti-Patterns Found

No TBD/FIXME/XXX debt markers or stubs in the launcher, builder, store lock, rerank or guard files (all substantive; no return-null/placeholder paths on rendered data). Open review items are Info only (08-REVIEW-DISPOSITION.md: IN-01..IN-07 open, WR-01..WR-04 fixed):

| File | Finding | Severity | Impact |
|------|---------|----------|--------|
| `store_lock.py` | IN-02 stale-PID race and fd leak | Info | A lock refusal can report PID `unknown`; no safety loss |
| `launcher/serve_mcp.py` | IN-01 MCP transport security accepts any loopback origin on any port | Info | Looser than the REST exact-origin list; loopback only |
| `launcher/__init__.py` | IN-03 refusal text reuses parity wording ("see v1/README-PARITY.md ... run_arm()") | Info | Seen live in the missing-keys message; cosmetic for launcher users |
| `launcher/__init__.py` | IN-06 `_is_wildcard` can raise `UnicodeEncodeError` on undecodable argv host | Info | Traceback on pathological input |
| `parity/run_comparison.py` | IN-07 per-query builder-refusal catch untested | Info | Behavior unproven |
| several | IN-04 lint violations, IN-05 origin guard literal-only | Info | Not goal-blocking |

### Human Verification Required

1. **RUN-11 live measurement** - Run the five `-m live` passes of `tests/parity/test_embedder_index_reproduction.py`, set `_SIMILARITY_THRESHOLD` from the minimum, record date and endpoint model. Expected: same verdict every run. Why human: spends tokens, needs the owner's env file. Owner-deferred.
2. **Parity-env builder check (no spend)** - `build_clients(load_env_file(Path('../v1/.env.parity')))` prints `['embedding', 'llm']`. Why human: agents may not read `v1/.env*`. Owner-deferred.
3. **Live rerank test (optional)** - `DATABASISE_RERANK_ENV_FILE=... pytest -m live tests/clients/test_rerank_client.py`. Why human: owner env file plus spend. Owner-deferred.
4. **Review-fix intent check** - confirm the stricter refusals added after the plan SUMMARYs (wildcard binds refused even with `--allow-remote-unauthenticated`; Origin guard on state-changing requests; builder refusals caught in all client-building CLIs). These commits (b5e143c..bb825b0) were verified here only through the gate and live launch, which pass.
5. **Owner ledger steps** - run the twelve `ledger-amend set` lines from 08-10-SUMMARY.md. The ledger hook currently reports all twelve rows open with empty `test_ref`. This is an owner step by design, not a code gap, but the ledger completion gate will stay red until done. Skip the RUN-11 line until item 1 is done.

### Gaps Summary

No gaps. Every ROADMAP success criterion and every requirement except RUN-11 is evidenced in code, in the passing dual-style gate (1251 passed under each style, both exit 0 through `check_offline_suite.py`) and in live runs of the installed launchers. RUN-11's measurement is intentionally open per the owner. Seam authentication is an open owner decision for the CONN phases, not a phase-8 gap. Phase 8 may proceed once the owner accepts the deferred items above; do not mark RUN-11 complete.

---

_Verified: 2026-10-17_
_Verifier: Claude (gsd-verifier)_
