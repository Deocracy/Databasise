---
phase: "08"
slug: "run-the-engine"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-16"
---

# Phase 08 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio (`asyncio_mode = "auto"`) |
| **Config file** | `databasise/pyproject.toml` `[tool.pytest.ini_options]` (Phase 8 adds `markers` and `addopts`) |
| **Quick run command** | `cd databasise && .venv/bin/pytest -q tests/<file>` |
| **Full suite command** | `cd databasise && .venv/bin/pytest -q -rs && .venv/bin/python -m pytest -q -rs` |
| **Estimated runtime** | ~210 seconds per invocation |

---

## Sampling Rate

- **After every task commit:** Run the task's quick command, plus `tests/test_import_boundary.py` and `tests/seam/test_rest_transport.py` when `rest.py`, `clients/` or new top-level modules change
- **After every plan wave:** Run `cd databasise && .venv/bin/pytest -q -rs`
- **Before `/gsd-verify-work`:** Both invocation styles show 0 failed, `databasise/tools/check_offline_suite.py` passes, owner-run `-m live` embedder test passed 5 times
- **Max feedback latency:** 230 seconds

---

## Per-Task Verification Map

Seeded per requirement from 08-RESEARCH.md; task IDs are filled once plans exist.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | RUN-01 | — | N/A | unit | `.venv/bin/pytest -q tests/mcp/test_tool_growth_invariant.py` | ✅ edit | ⬜ pending |
| TBD | TBD | TBD | RUN-02 | — | N/A | unit | `.venv/bin/pytest -q tests/clients/test_openai_compat.py -k usage` | ✅ add cases | ⬜ pending |
| TBD | TBD | TBD | RUN-03 | — | N/A | unit | `.venv/bin/pytest -q tests/clients/test_openai_compat.py -k "choices or content or mis_sized or order"` | ✅ add cases | ⬜ pending |
| TBD | TBD | TBD | RUN-04 | — | N/A | unit + subprocess | `.venv/bin/python -m pytest -q tests/evidence/test_falsifier4_evidence.py tests/foreign` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RUN-05 | — | env values never printed, key names only | unit | `.venv/bin/pytest -q tests/clients/test_build_clients.py tests/clients/test_rerank_client.py tests/seam/test_corpus_status.py tests/parity/test_naive_arm_end_to_end.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RUN-06 | — | `--host` defaults to 127.0.0.1 | integration | `.venv/bin/pytest -q tests/launcher/test_launchers.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RUN-07 | — | lock error prints store root and PID only | unit + integration | `.venv/bin/pytest -q tests/launcher/test_launchers.py tests/launcher/test_store_lock.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RUN-08 | — | exact-origin allow-list, never `*`, no credentials | unit | `.venv/bin/pytest -q tests/seam/test_rest_cors.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | RUN-09 | — | no file written outside `corpus-inbox` | unit + mutation | `.venv/bin/pytest -q tests/seam/test_rest_corpus_endpoints.py -k generated_on_disk_name` | ✅ rewrite | ⬜ pending |
| TBD | TBD | TBD | RUN-10 | — | N/A | unit + mutation | `.venv/bin/pytest -q tests/seam/test_rest_corpus_endpoints.py -k round_trip` | ✅ rewrite | ⬜ pending |
| TBD | TBD | TBD | RUN-11 | — | N/A | live (owner-run) | `.venv/bin/pytest -q tests/parity/test_embedder_index_reproduction.py` (shows `1 deselected`) | ✅ edit | ⬜ pending |
| TBD | TBD | TBD | RUN-12 | — | N/A | gate script | `cd databasise && .venv/bin/python tools/check_offline_suite.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `databasise/tests/launcher/test_launchers.py`, `databasise/tests/launcher/test_store_lock.py` — RUN-06/07 (free-port helper, stub env writer with the six keys, `/health` readiness poll ~30 s)
- [ ] `databasise/tests/clients/test_build_clients.py`, `databasise/tests/clients/test_rerank_client.py` — RUN-05
- [ ] `databasise/tests/seam/test_rest_cors.py` — RUN-08
- [ ] `databasise/tests/foreign/test_mcp_sdk_guard.py` — RUN-04
- [ ] `databasise/tools/check_offline_suite.py` — RUN-12 gate
- [ ] `databasise/evidence/COVERAGE.md` — RUN-01 data file
- [ ] `databasise/pyproject.toml`: `markers`, `addopts`, `[project.scripts]`, `databasise.launcher` in `packages`, `httpx` dependency; then `uv lock` and `uv sync --extra rest --extra mcp`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live embedder reproduction passes within endpoint noise | RUN-11 | Spends real endpoint calls; owner-run | `cd databasise && for i in 1 2 3 4 5; do .venv/bin/pytest -q -m live tests/parity/test_embedder_index_reproduction.py; done` |
| Live rerank round trip | RUN-05 (D-10) | Needs owner-supplied `RERANK_*` env file | `cd databasise && .venv/bin/pytest -q -m live tests/clients/test_rerank_client.py` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 230s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
