---
phase: "08"
slug: "run-the-engine"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-16"
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio (`asyncio_mode = "auto"`) |
| **Config file** | `databasise/pyproject.toml` `[tool.pytest.ini_options]` (`live` marker, `addopts = '-m "not live"'`) |
| **Quick run command** | `cd databasise && .venv/bin/pytest -q tests/<file>` |
| **Full suite command** | `cd databasise && .venv/bin/python tools/check_offline_suite.py` (runs `.venv/bin/pytest` and `.venv/bin/python -m pytest`) |
| **Estimated runtime** | ~220 seconds per invocation |

---

## Sampling Rate

- **After every task commit:** Run the task's quick command, plus `tests/test_import_boundary.py` and `tests/seam/test_rest_transport.py` when `rest.py`, `clients/` or new top-level modules change
- **After every plan wave:** Run `cd databasise && uv run pytest -q -rs`
- **Before `/gsd-verify-work`:** `databasise/tools/check_offline_suite.py` passes; owner-run `-m live` embedder runs are deferred to `.planning/TESTING-PLAN.md` §2
- **Max feedback latency:** 230 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | RUN-05, RUN-06, RUN-07 | — | env values never printed; `--host` defaults to 127.0.0.1 | integration | `.venv/bin/pytest -q tests/launcher/test_launchers.py tests/clients/test_build_clients.py` | ✅ | ✅ green |
| 08-01-02 | 01 | 1 | RUN-11, RUN-12 | — | N/A | collection | `.venv/bin/pytest -q --collect-only tests/parity` (3 deselected) | ✅ | ✅ green |
| 08-02-01 | 02 | 1 | RUN-02 | — | N/A | unit | `.venv/bin/pytest -q tests/clients/test_openai_compat.py tests/seam/test_token_accounting.py` | ✅ | ✅ green |
| 08-02-02 | 02 | 1 | RUN-03 | — | N/A | unit | `.venv/bin/pytest -q tests/clients/test_openai_compat.py` | ✅ | ✅ green |
| 08-03-01 | 03 | 1 | RUN-01 | — | N/A | unit | `.venv/bin/pytest -q tests/mcp/test_tool_growth_invariant.py` | ✅ | ✅ green |
| 08-03-02 | 03 | 1 | RUN-04 | — | N/A | unit + subprocess | `.venv/bin/python -m pytest -q tests/evidence/test_falsifier4_evidence.py tests/foreign` | ✅ | ✅ green |
| 08-04-01 | 04 | 1 | RUN-09 | — | no file written outside `corpus-inbox` | unit + mutation | `.venv/bin/pytest -q tests/seam/test_rest_corpus_endpoints.py -k generated_on_disk_name` | ✅ | ✅ green |
| 08-04-02 | 04 | 1 | RUN-10 | — | N/A | unit + mutation | `.venv/bin/pytest -q tests/seam/test_rest_corpus_endpoints.py -k round_trip` | ✅ | ✅ green |
| 08-05-02 | 05 | 2 | RUN-05 | — | rerank headers/API key never logged | unit | `.venv/bin/pytest -q tests/clients/test_rerank_client.py` | ✅ | ✅ green |
| 08-05-03 | 05 | 2 | RUN-05 | — | builder errors name keys, never values | unit | `.venv/bin/pytest -q tests/clients/test_build_clients.py tests/seam/test_corpus_status.py` | ✅ | ✅ green |
| 08-06-01 | 06 | 2 | RUN-06 | — | stdio mode writes nothing to stdout | integration | `.venv/bin/pytest -q tests/launcher/test_launchers.py` | ✅ | ✅ green |
| 08-06-02 | 06 | 2 | RUN-07 | — | lock error prints store root and PID only | unit + integration | `.venv/bin/pytest -q tests/launcher/test_launchers.py tests/launcher/test_store_lock.py` | ✅ | ✅ green |
| 08-07-01 | 07 | 2 | RUN-07 | — | N/A | unit | `.venv/bin/pytest -q tests/parity/test_parity_cli_store_lock.py` | ✅ | ✅ green |
| 08-07-02 | 07 | 2 | RUN-07 | — | N/A | unit | `.venv/bin/pytest -q tests/parity/test_parity_cli_store_lock.py` | ✅ | ✅ green |
| 08-08-01 | 08 | 2 | RUN-08 | — | exact-origin allow-list, never `*`, no credentials | unit | `.venv/bin/pytest -q tests/seam/test_rest_cors.py` | ✅ | ✅ green |
| 08-08-02 | 08 | 2 | RUN-08 | — | `--cors-origin` validated before the store lock | unit | `.venv/bin/pytest -q tests/launcher` | ✅ | ✅ green |
| 08-08-03 | 08 | 2 | RUN-06, RUN-07 | — | non-loopback bind refused without `--allow-remote-unauthenticated`; foreign Host → 400 | unit | `.venv/bin/pytest -q tests/launcher/test_bind_guard.py` | ✅ | ✅ green |
| 08-09-01 | 09 | 3 | RUN-12 | — | N/A | unit | `.venv/bin/pytest -q tests/test_check_offline_suite.py` | ✅ | ✅ green |
| 08-09-02 | 09 | 3 | RUN-12 | — | non-loopback sockets refused for non-`live` tests | gate script | `.venv/bin/python tools/check_offline_suite.py` | ✅ | ✅ green |
| 08-10-02 | 10 | 4 | RUN-11 | — | N/A | unit | `.venv/bin/pytest -q tests/parity/test_embedder_index_reproduction.py` (1 deselected) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

Checkpoint tasks 08-05-01, 08-10-01 and 08-10-03 are owner gates with no automated verify.

---

## Wave 0 Requirements

- [x] `databasise/tests/launcher/test_launchers.py`, `databasise/tests/launcher/test_store_lock.py` — RUN-06/07
- [x] `databasise/tests/clients/test_build_clients.py`, `databasise/tests/clients/test_rerank_client.py` — RUN-05
- [x] `databasise/tests/seam/test_rest_cors.py` — RUN-08
- [x] `databasise/tests/foreign/test_mcp_sdk_guard.py` — RUN-04
- [x] `databasise/tools/check_offline_suite.py` — RUN-12 gate
- [x] `databasise/evidence/COVERAGE.md` — RUN-01 data file
- [x] `databasise/pyproject.toml`: `markers`, `addopts`, `[project.scripts]`, `databasise.launcher` in `packages`, `httpx` dependency

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live embedder reproduction within endpoint noise; measured `_SIMILARITY_THRESHOLD` | RUN-11 | Spends real endpoint calls; owner deferred to after the build (TESTING-PLAN.md §2) | `cd databasise && for i in 1 2 3 4 5; do .venv/bin/pytest -q -s -m live tests/parity/test_embedder_index_reproduction.py; done` |
| Parity env file builds without a partial rerank set | RUN-05 | Reads the secret parity env file; owner-run (TESTING-PLAN.md §2) | No-spend `build_clients(load_env_file(...))` check printing key names only |
| Live rerank round trip | RUN-05 (D-10) | Needs owner-supplied `RERANK_*` env file | `cd databasise && .venv/bin/pytest -q -m live tests/clients/test_rerank_client.py` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 230s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-16 (orchestrator audit; live items owner-deferred)

## Validation Audit 2026-10-17

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
