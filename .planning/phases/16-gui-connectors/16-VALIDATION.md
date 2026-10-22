---
phase: "16"
slug: "gui-connectors"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-22"
---

# Phase 16: Validation Strategy

> This is the per-phase validation contract for feedback sampling during execution. Its source is 16-RESEARCH.md § Validation Architecture and § Row Test Design.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`, `addopts = '-m "not live"'`) |
| **Config file** | `databasise/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `PYTHONPATH="$PWD" databasise/.venv/bin/python -m pytest -q <path> -p no:cacheprovider`, run from the repo root. Never `cd databasise &&` (a hook blocks it). |
| **Phase guard suite** | Run with the quick command: test_rest_transport, test_refusal_status_codes, test_refusal_catalogue, test_tool_growth_invariant, test_run01_coverage_crosscheck, test_page_bounds, test_graph_lock, test_store_refusal_status, test_launchers, test_partial_run_evidence, test_promote_refuses_partial, test_promotion_posture, test_health_probe, test_selector_reachability, test_leak. Baseline at HEAD: 276 passed in 60 s. |
| **Full suite command** | `databasise/.venv/bin/python databasise/tools/check_offline_suite.py`, both styles, run in the background. Baseline: 2979 passed, 4 deselected (Phase 15 close). |
| **Never** | `-m live`; reading any `.env*` file, `v1/.env.parity` or `v1/parity-env.txt`; spending provider tokens; two suite runs at once |

---

## Sampling Rate

- **After every task commit:** the task's row test file, its directory, and every protected test_ref that constrains the touched module (16-RESEARCH §6).
- **After every plan:** the phase guard suite.
- **Before `/gsd-verify-work`:** the full suite green in both styles. Each row's pre-fix AssertionError is checked with `record-fail --at` at the plan base.

---

## Per-Requirement Verification Map

Each row test is a new file and is unprotected. Plain pytest must fail it on pre-fix code with an AssertionError: reach any new API through `getattr`, `inspect.signature` or `importlib.util.find_spec` plus an `assert`, never an import that crashes at collection.

| Req | Behavior | Row test file | Status |
|-----|----------|---------------|--------|
| CONN-01 | Operator routes are thin adapters: the AST rule plus a `Ledger(` mutant. Every route is a 404 without `--operator`. COVERAGE.md has REST-only absent rows. | `databasise/tests/seam/test_console_surface.py` | ⬜ |
| CONN-02 | `docs/gui/refusals.json` is in sync with the 50 refusal types and their `http_status` | `databasise/tests/seam/test_refusal_catalogue_file.py` | ⬜ |
| CONN-03 | The selector-resolution fixture is in sync | `databasise/tests/seam/test_selector_resolution_fixture.py` | ⬜ |
| CONN-04 | /info returns version, workspace and presence-only clients, with no store_root, URL, model or key | `databasise/tests/seam/test_console_info.py` | ⬜ |
| CONN-05 | /wirings returns six rows with node counts and reachable flags, cross-checked against the fixture | `databasise/tests/seam/test_console_wirings.py` | ⬜ |
| CONN-06 | /ledger/aliases creates no file and leaves no open handle | `databasise/tests/seam/test_console_ledger.py` | ⬜ |
| CONN-07 | /ledger/history: active and tombstoned flags, page bounds | `databasise/tests/seam/test_console_ledger.py` (history nodes) | ⬜ |
| CONN-08 | /traces: newest first, paging, scrubbed stop_reason | `databasise/tests/seam/test_console_traces.py` | ⬜ |
| CONN-09 | Preview and promote agree (differential); no ledger.db is created | `databasise/tests/seam/test_console_preview.py` | ⬜ |
| CONN-10 | /chunks per family: refs resolve, no reconstruct | `databasise/tests/seam/test_console_chunks.py` | ⬜ |
| CONN-11 | Node page with one degree query; a busy graph gives 409 (raw pycozo holder) | `databasise/tests/seam/test_console_graph.py` (nodes) | ⬜ |
| CONN-12 | Edge allowlist `{src,tgt,edge_types,weight}`; an unknown node gives 422 | `databasise/tests/seam/test_console_graph.py` (node edges) | ⬜ |
| CONN-13 | write_in_flight and graph_busy during a blocked ingest | `databasise/tests/seam/test_console_info.py` (busy nodes) | ⬜ |
| CONN-14 | /log tail; 404 without both flags; 422 on limit bounds | `databasise/tests/seam/test_console_log.py` | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

The ledger needs each row to have its own check. CONN-06 and CONN-07 share a file, as do CONN-04 and CONN-13, and CONN-11 and CONN-12, so each of those rows takes a distinct `::node` test_ref.

---

## Wave 0 Requirements

- [ ] Each row test file in the table, written test-first in the plan that completes its row.
- [ ] A shared `_operator_app(tmp_path, **kw)` helper. Put it in each file, or in `tests/seam/conftest.py` as a plain function only, never as a module-level import of new API.
- [ ] Store helper spies in `databasise/tests/stores/test_console_reads.py`: `list_ids` does not reconstruct, one degree query per page, `held_graph_paths`.

---

## Manual-Only Verifications

| Behavior | How | Why manual |
|----------|-----|------------|
| A real `databasise-rest --operator --log-file` writes a 500 traceback to the file | The scratchpad `p16/log_probe.py` variant B pattern, with `--no-clients` and a tmp store root | Needs a launched server. Record the result in the verification report. |

---

## Validation Sign-Off

- [ ] Every task has an `<automated>` verify, or depends on Wave 0.
- [ ] No three consecutive tasks lack an automated verify.
- [ ] Wave 0 covers every MISSING reference.
- [ ] No watch-mode flags.
- [ ] `nyquist_compliant: true` is set in the frontmatter.

**Approval:** pending
