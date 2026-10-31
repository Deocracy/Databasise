---
phase: 08-run-the-engine
verified: 2026-10-31T18:45:00Z
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
covered_digest: "v3:sha256:8a18a3d52cd24f7848357d468c56585770e07e3b2790d9e5c1306b3aafd2c573"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 5/5
  gaps_closed: []
  gaps_remaining: []
  regressions: []
deferred:
  - truth: "RUN-11: embedder reproduction test gives one verdict on repeated runs; _SIMILARITY_THRESHOLD set from five measured live runs"
    addressed_in: ".planning/TESTING-PLAN.md section 2 (owner-deferred, not a later roadmap phase)"
    evidence: "Owner, 2026-10-16: 'we dont need to run any of those mesherment untill everthing is build. we only run things for debugging'. The module docstring of tests/parity/test_embedder_index_reproduction.py still says the threshold is unmeasured and 0.999 stands."
human_verification:
  - test: "RUN-11 live measurement: run the five -m live passes of tests/parity/test_embedder_index_reproduction.py and set _SIMILARITY_THRESHOLD from the observed minimum"
    expected: "Same verdict on repeated runs; threshold, date and endpoint model recorded in the module docstring; then RUN-11 is genuinely complete"
    why_human: "Spends tokens against a real endpoint and needs the owner's env file (never read by agents). Owner-deferred to TESTING-PLAN.md section 2. NOTE: REQUIREMENTS.md currently shows RUN-11 as [x] / Complete (set by commit 6b8eca8) although this measurement has not been done; reconcile it."
  - test: "Parity-env builder compatibility (no spend), RUN-05: build_clients(load_env_file(v1/.env.parity)) prints ['embedding','llm']"
    expected: "Real parity env file satisfies the six required keys with no MissingParityEnvKeyError"
    why_human: "Reading v1/.env.* is blocked for agents. Owner-deferred to TESTING-PLAN.md section 2."
  - test: "Live rerank client (optional, D-10): DATABASISE_RERANK_ENV_FILE=<file> pytest -m live tests/clients/test_rerank_client.py"
    expected: "Live rerank call returns a ranking in index order against a real cohere/jina/aliyun endpoint"
    why_human: "Needs an owner-supplied RERANK_* env file and spends tokens. Owner-deferred."
  - test: "Confirm the post-review behaviour changes match intent: refusal of wildcard binds even with --allow-remote-unauthenticated (WR-03), cross-site write Origin guard (WR-01), builder refusals caught by every client-building CLI (WR-02)"
    expected: "Owner agrees these stricter refusals are wanted (08-REVIEW-FIX.md marks them 'requires human verification')"
    why_human: "Intent/policy judgment, not a defect check."
  - test: "Owner ledger steps: run the twelve ledger-amend set lines in 08-10-SUMMARY.md 'Owner ledger steps (pending)'; do not run the RUN-11 line until its live runs are done"
    expected: "BAK ledger rows RUN-01..RUN-12 get test_ref"
    why_human: "Ledger test_ref filling and record-fail are owner-only by design."
---

# Phase 8: Run the Engine Verification Report

**Phase Goal:** An operator can start the engine as a served process from the installed package, with real model clients and one engine process per store root, and the offline test suite is green so every later fix can be checked end to end
**Verified:** 2026-10-31
**Status:** human_needed
**Re-verification:** Yes, after the verification went stale. Eight covered files moved after 2026-10-17 (Phases 11 to 17 touched `seam/rest.py`, `launcher/serve_rest.py`, `foreign/_mcp_sdk_guard.py`, `evidence/COVERAGE.md`, `pyproject.toml`, `clients/builder.py` and two test modules). All five success criteria were re-checked against current code and by live launch; nothing regressed.

The goal is achieved in the codebase. Nothing is FAILED. The status is `human_needed` because the human-verification section is non-empty (rule 2 of the decision tree): RUN-11's live measurement and two live/no-spend checks are owner-deferred, and the post-review stricter refusals need an intent check. The previous report said `passed` while listing the same items, which did not follow the tree.

## Goal Achievement

### Observable Truths (ROADMAP success criteria, the contract)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | One installed command starts REST, GET /health is 200 with llm and embedding clients from the shared builder; missing required keys stop startup naming every key; rerank reported not available unless RERANK_BINDING + its three keys | VERIFIED | Re-ran the installed `databasise-rest` (this session) with a six-key stub env: `GET /health` returned 200 with `"clients":{"llm":true,"embedding":true,"rerank":false}`. An env file with only `LLM_MODEL` exited 1 naming `LLM_BINDING_HOST, LLM_BINDING_API_KEY, EMBEDDING_BINDING_HOST, EMBEDDING_MODEL, EMBEDDING_BINDING_API_KEY`. No env file and no `--no-clients` exited 2 (`--env-file is required unless --no-clients`). `clients/builder.py` `build_clients` is unchanged in logic: optional binding-aware rerank, `null`/empty = off, partial set = `MissingParityEnvKeyError` naming the absent rerank keys. `tests/clients` all pass. |
| 2 | `databasise-mcp --transport stdio` lists same tools as in-process server; second launcher on same store root or `--workers 2` exits non-zero with named store-lock error (root + holder PID) while first keeps answering /health | VERIFIED | With the first REST launcher up: a second `databasise-rest` and a second `databasise-mcp --transport stdio` on the same root each exited 1 with `store root <root> is held by databasise process 796529; one engine process per store root (G-36)`; `.engine.lock` content was `796529` and /health still returned 200. `--workers 2` exited 2 naming `<store_root>/.engine.lock (G-36)` and created no store dir. `store_lock.py` uses `fcntl.flock` LOCK_EX\|LOCK_NB, O_CLOEXEC, writes the PID. `tests/launcher` (including the stdio tool-set equality test in `test_launchers.py`) passed. Parity CLIs run_arm, import_index, build_hipporag_index, run_comparison, run_cross_modality, storage_audit all import and use the lock. |
| 3 | `--cors-origin <origin>`: preflight from that origin succeeds, unlisted origin gets no allow header; no flag = unchanged | VERIFIED | Live: `OPTIONS /query` with `Origin: http://localhost:5173` returned 200 with `access-control-allow-origin: http://localhost:5173`; `Origin: http://evil.example` returned 400 with no allow-origin header. `seam/rest.py` `validate_cors_origin` rejects non-exact origins and `CORSMiddleware` is only added `if cors_origins:` (line 378), so the default is unchanged. |
| 4 | No-usage response = one unbudgetable call; empty choices, None content, mis-sized embedding batch, out-of-order items raise named errors or are returned in input order | VERIFIED | `clients/openai_compat.py` (not among the moved files, re-read): `_token_accounting` returns `TokenAccounting(call_count=1, counted_by="unbudgetable")` for missing usage; `EmptyChoicesError`, `MissingCompletionContentError`, `EmbeddingBatchMismatchError` (count and index-set check at line 210); vectors sorted by `.index` (line 213). `tests/clients/test_openai_compat.py` passed. |
| 5 | From `databasise/`, `.venv/bin/pytest` and `.venv/bin/python -m pytest` both 0 failed; COVERAGE cross-check runs; mcp SDK detected; upload/delete round-trip tests fail under their mutations; live tests only under `-m live` | VERIFIED for every component; full-suite figure not re-run by this verifier | Not re-run here by instruction (the orchestrator's regression gate owns the whole-suite run; its log was at about 57% with no failure marks when I last read it). Targeted runs this session, 0 failed, 0 skipped: `tests/clients tests/launcher tests/mcp/test_tool_growth_invariant.py tests/seam/test_rest_corpus_endpoints.py` (186 passed, 1 deselected); `tests/seam/test_run01_coverage_crosscheck.py tests/foreign/test_mcp_sdk_guard.py tests/mcp/test_dual_transport_parity.py tests/test_check_offline_suite.py tests/test_phase_success_criteria.py tests/test_packaging.py tests/test_import_boundary.py` (63 passed). `pyproject.toml` has `addopts = '-m "not live"'` and the registered `live` marker; the embedder test shows as `1/6 collected (5 deselected)` under `-m live`. `_COVERAGE_PATH` resolves to `databasise/evidence/COVERAGE.md` (152 lines) and `_coverage_markdown` asserts the file exists; the roster cross-check has a non-vacuity test. `tools/check_offline_suite.py` still runs both styles and fails on contradictory mcp skips. The round-trip tests read the inbox on disk (`inbox.iterdir()`, 32-hex stem) and assert counts `1 -> 0` after delete, so a no-op delete hook or an empty inbox fails them. The 1251-passed gate from 2026-10-17 predates the moved files; rely on the orchestrator's current run for the final "0 failed". |

**Score:** 5/5 roadmap truths verified.

### Deferred Items

| # | Item | Addressed In | Evidence |
|---|------|--------------|----------|
| 1 | RUN-11 measured threshold and five live passes | Owner-deferred to `.planning/TESTING-PLAN.md` section 2 | `_SIMILARITY_THRESHOLD` is still 0.999 and the module docstring says it is unmeasured. The `live` marker, default deselection and the RUN-02-dependent `tokens.call_count > 0` assertion are in place; only the measurement is missing. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/clients/builder.py` | Shared builder, `BUILDER_REFUSALS` | VERIFIED | 211 lines; read in full |
| `databasise/clients/rerank.py` | `HttpRerankClient`, 3 bindings | VERIFIED | 197 lines; wired through the builder |
| `databasise/clients/openai_compat.py` | RUN-02/03 fixes | VERIFIED | See truth 4 |
| `databasise/store_lock.py` | flock store lock | VERIFIED | See truth 2 |
| `databasise/launcher/{__init__,serve_rest,serve_mcp}.py` | Two launchers | VERIFIED | `[project.scripts]` has `databasise-rest` and `databasise-mcp`; both console scripts exist in `.venv/bin` and in `entry_points` |
| `databasise/examples/mcp-client.stdio.json` | Example stdio client config | VERIFIED | Unchanged since the prior report |
| `databasise/foreign/_mcp_sdk_guard.py` | `mcp_sdk_is_installed` shadow-safe | VERIFIED | PathFinder lookup with project paths stripped (lines 92-95); guard tests pass. It now also holds an import lock (Phase 15); behavior for RUN-04 unchanged |
| `databasise/evidence/COVERAGE.md` | Live §18.5 record | VERIFIED | Present, parsed by the cross-check test, which passes |
| `databasise/tools/check_offline_suite.py` | RUN-12 gate | VERIFIED | Read in full; its unit tests pass. Not executed end to end (see truth 5) |
| `databasise/tests/seam/test_rest_corpus_endpoints.py` | RUN-09/10 rewrites | VERIFIED | Read lines 370-540 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `serve_rest.main` | `build_clients` | `open_engine` (lock first, then clients) | WIRED | `launcher/__init__.py:113-122`; lock fd closed on builder failure |
| `serve_rest.build_app` | `seam.rest.create_app` | `cors_origins=args.cors_origin` | WIRED | Plus TrustedHost and Origin guard middleware; Phase 16 added `--operator` and `--log-file`, both refused before the lock when invalid |
| `serve_mcp.main` | `mcp.create_server(...).run(transport)` | direct | WIRED | stdio, sse, streamable-http |
| `/health` clients map | builder clients | seam engine health | WIRED | Live /health showed `rerank:false` |
| Parity CLIs | `store_lock` | `main()` | WIRED | `store_lock(...)` context in run_comparison, build_hipporag_index, storage_audit, run_cross_modality; `acquire_store_lock` path in run_arm and import_index |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| /health clients map | `clients` | actual builder dict keys | Yes (llm/embedding true, rerank false observed live) | FLOWING |
| `.engine.lock` | holder PID | `os.getpid()` | Yes (file content `796529` matched the serving process) | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Installed REST serves /health | `databasise-rest --store-root <tmp> --workspace w --port 18770 --env-file <stub> --cors-origin http://localhost:5173`, curl | 200, clients map as above | PASS |
| CORS preflight listed / unlisted | curl OPTIONS /query | 200 + header / 400 + no header | PASS |
| Second REST and MCP launcher refused | run on same root | exit 1, root + PID named, first still 200 | PASS |
| `--workers 2` refused | `databasise-rest --workers 2 --no-clients` | exit 2, store-lock text, nothing created | PASS |
| Missing keys / no env file | see truth 1 | exit 1 / exit 2 | PASS |
| Targeted suites | see truth 5 | 186 + 63 passed, 0 failed, 0 skipped | PASS |

The scratch server was started in the session scratchpad and killed afterwards. Process note: my first attempt to read `check_offline_suite.py` ran it with `--help`, which starts the whole gate because the script ignores arguments. I killed it within about two minutes, so it produced no result and is not evidence.

### Probe Execution

SKIPPED: no `scripts/*/tests/probe-*.sh` probes declared by this phase's plans.

### Requirements Coverage

All twelve IDs are claimed by at least one PLAN frontmatter (08-01 to 08-10) and all appear in REQUIREMENTS.md. No orphaned requirements.

| Requirement | Source Plan(s) | Status | Evidence |
|-------------|----------------|--------|----------|
| RUN-01 | 08-03, 08-10 | SATISFIED | COVERAGE path `databasise/evidence/COVERAGE.md`; explicit existence assertion; cross-check and non-vacuity tests pass |
| RUN-02 | 08-02, 08-10 | SATISFIED | unbudgetable sentinel, call_count=1 |
| RUN-03 | 08-02, 08-10 | SATISFIED | four named behaviours in code and tests |
| RUN-04 | 08-03, 08-10 | SATISFIED | `mcp_sdk_is_installed` shadow-safe; guard tests pass |
| RUN-05 | 08-01, 08-05, 08-10 | SATISFIED (owner-amended wording) | Shared builder + optional rerank by binding; messages hold keys never values |
| RUN-06 | 08-01, 08-06, 08-10 | SATISFIED | Scripts, defaults, example config, live health |
| RUN-07 | 08-01, 08-06, 08-07, 08-10 | SATISFIED | flock lock, workers=1, named error with root and PID, parity CLIs lock |
| RUN-08 | 08-08, 08-10 | SATISFIED | Live preflight check |
| RUN-09 | 08-04, 08-10 | SATISFIED | Disk-reading upload test |
| RUN-10 | 08-04, 08-10 | SATISFIED | Counts 1 to 0 over REST and in-process |
| RUN-11 | 08-01 (claimed), 08-10 (excluded) | NOT COMPLETE, OWNER-DEFERRED | Marker, addopts and RUN-02 dependency done; threshold unmeasured. **REQUIREMENTS.md line 50 and traceability row 846 say `[x]` / Complete**, which overstates the state (commit 6b8eca8 flipped it). Needs reconciling by the owner or orchestrator |
| RUN-12 | 08-01, 08-09, 08-10 | SATISFIED | Gate script and its tests in place; suite-wide figure pending the orchestrator's run |

### Anti-Patterns Found

No TBD/FIXME/XXX markers in the phase's implementation files (grep over builder, openai_compat, rerank, store_lock, launcher, _mcp_sdk_guard, seam/rest.py, check_offline_suite.py). Open review items remain Info only (08-REVIEW-DISPOSITION.md): store-lock stale-PID race (IN-02), MCP transport security loopback-any-port (IN-01), parity-wording in launcher refusal text (IN-03), `_is_wildcard` UnicodeEncodeError on undecodable argv (IN-06), untested per-query catch in run_comparison (IN-07). The missing-keys message still ends with "see v1/README-PARITY.md ... run_arm()", confirmed live.

### Human Verification Required

1. **RUN-11 live measurement** - five `-m live` passes of `tests/parity/test_embedder_index_reproduction.py`; set `_SIMILARITY_THRESHOLD`; record date and endpoint model. Owner-deferred. Until then REQUIREMENTS.md should not show RUN-11 complete.
2. **Parity-env builder check (no spend)** - `build_clients(load_env_file(Path('../v1/.env.parity')))` prints `['embedding', 'llm']`. Agents may not read `v1/.env*`.
3. **Live rerank test (optional)** - `DATABASISE_RERANK_ENV_FILE=... pytest -m live tests/clients/test_rerank_client.py`.
4. **Review-fix intent check** - stricter refusals added after the plan SUMMARYs (wildcard binds refused even with `--allow-remote-unauthenticated`; Origin guard on state-changing requests; builder refusals caught in all client-building CLIs).
5. **Owner ledger steps** - the twelve `ledger-amend set` lines from 08-10-SUMMARY.md; skip the RUN-11 line until item 1 is done.

### Gaps Summary

No gaps. Every ROADMAP success criterion is evidenced in current code and in live runs of the installed launchers, and the Phase 11 to 17 edits to the moved files did not break any Phase 8 behavior. Remaining items are owner-deferred measurements and an intent check. One bookkeeping discrepancy needs attention: REQUIREMENTS.md marks RUN-11 complete although its measurement is open.

---

_Verified: 2026-10-31_
_Verifier: Claude (gsd-verifier)_

### Human Verification Resolution (orchestrator, 2026-10-31)

All five success criteria verified against current code; no behaviour item is open. The listed items are owner-run checks, carried as before:

| Item | Result |
|------|--------|
| RUN-11 five live measurement runs | Open: owner-deferred (TESTING-PLAN.md §2). REQUIREMENTS.md RUN-11 reverted to Pending in the same commit; it had been marked Complete in error. |
| No-spend parity-env builder check, optional live rerank test | Open: owner-run, carried in TESTING-PLAN.md. |
| Intent check on the stricter post-review refusals | Open: owner decision. |
| Owner record steps (RUN-11 test_ref, RUN-02..08 record-fail) | Open: owner steps, carried in STATE.md. |
| Full offline gate | Reported by the orchestrator's regression run. |
