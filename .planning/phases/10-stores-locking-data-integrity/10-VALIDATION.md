---
phase: "10"
slug: "stores-locking-data-integrity"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-17"
---

# Phase 10: Validation Strategy

> The per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`), `-m "not live"` by default |
| **Config file** | `databasise/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd databasise && .venv/bin/python -m pytest tests/stores -q -p no:cacheprovider` (baseline: 77 passed in 4.7 s) |
| **Full suite command** | `cd databasise && .venv/bin/python tools/check_offline_suite.py` (after phase: 1783 passed, 1 skipped, 4 deselected, both pytest styles) |
| **Estimated runtime** | ~280 seconds per pytest style |

---

## Sampling Rate

- **After every task commit:** the task's new test file, plus `tests/stores`.
- **After every plan wave:** `cd databasise && .venv/bin/python -m pytest tests/stores tests/seam tests/runner tests/parts tests/parts_core tests/validator -q -p no:cacheprovider`
- **Before `/gsd-verify-work`:** `tools/check_offline_suite.py` passes with 0 failed.
- **Max feedback latency:** 300 seconds

---

## Per-Task Verification Map

This map is seeded per requirement from 10-RESEARCH.md. Task IDs are filled in once the plans exist.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-02 | 01 | 1 | STOR-01 | — | busy refusal carries no path or namespace | integration + subprocess | `cd databasise && .venv/bin/python -m pytest tests/stores/test_graph_lock.py -q` | ✅ (6 + 1 (test_store_refusal_status) tests) | ✅ green |
| 10-01-03 | 01 | 1 | STOR-02 | — | no leaked sqlite connection | unit | `cd databasise && .venv/bin/python -m pytest tests/seam/test_build_stores_cleanup.py -q` | ✅ (6 tests) | ✅ green |
| 10-06-01 | 06 | 4 | STOR-03 | — | resolve creates no kv or graph directories | integration | `cd databasise && .venv/bin/python -m pytest tests/seam/test_evidence_resolve_stores.py -q` | ✅ (8 tests) | ✅ green |
| 10-07-01, 10-07-02 | 07 | 5 | STOR-04 | — | health creates nothing | integration | `cd databasise && .venv/bin/python -m pytest tests/seam/test_health_probe.py -q` | ✅ (9 tests) | ✅ green |
| 10-08-01, 10-08-02 | 08 | 6 | STOR-05 | — | a read-only node cannot mutate | unit | `cd databasise && .venv/bin/python -m pytest tests/runner/test_capability_scoping_modes.py -q` | ✅ (33 tests) | ✅ green |
| 10-04-01, 10-04-02, 10-05-01, 10-05-02 | 04, 05 | 2–3 | STOR-06 | — | a refused run commits nothing | integration | `cd databasise && .venv/bin/python -m pytest tests/seam/test_ingest_abort.py -q` | ✅ (12 + 11 (test_prepared_commit) tests) | ✅ green |
| 10-10-01, 10-10-02 | 10 | 7 | STOR-07 | — | N/A | integration | `cd databasise && .venv/bin/python -m pytest tests/stores/test_delete_commit_contract.py -q` | ✅ (11 tests) | ✅ green |
| 10-06-02 | 06 | 4 | STOR-08 | — | corruption refused, never a 500 | unit + integration | `cd databasise && .venv/bin/python -m pytest tests/stores/test_vector_crash_window.py -q` | ✅ (9 tests) | ✅ green |
| 10-11-02 | 11 | 8 | STOR-09 | — | N/A | unit | `cd databasise && .venv/bin/python -m pytest tests/stores/test_vector_validation.py -q` | ✅ (6 tests) | ✅ green |
| 10-09-01 | 09 | 6 | STOR-10 | — | N/A | unit | `cd databasise && .venv/bin/python -m pytest tests/stores/test_graph_delete_cascade.py -q` | ✅ (8 tests) | ✅ green |
| 10-09-02 | 09 | 6 | STOR-11 | — | N/A | unit | `cd databasise && .venv/bin/python -m pytest tests/stores/test_kv_buffer_isolation.py -q` | ✅ (6 tests) | ✅ green |
| 10-02-01, 10-12-01, 10-12-02 | 02, 12 | 1, 9 | STOR-12 | — | an unwired effect is refused at parse | unit + integration | `cd databasise && .venv/bin/python -m pytest tests/wirings/test_store_effects_wired.py -q` | ✅ (26 tests) | ✅ green |
| 10-02-01 | 02 | 1 | STOR-13 | — | blob digest path removed with the store | unit (grep) | `cd databasise && .venv/bin/python -m pytest tests/test_removed_stores_absent.py -q` | ✅ (5 tests) | ✅ green |
| 10-02-01 | 02 | 1 | STOR-14 | — | N/A | unit (grep) | `cd databasise && .venv/bin/python -m pytest tests/test_removed_stores_absent.py -q` | ✅ (5 tests) | ✅ green |
| 10-03-01, 10-03-02 | 03 | 1 | STOR-15 | — | GC confined to `quarantined-*` under store_root | unit + subprocess | `cd databasise && .venv/bin/python -m pytest tests/test_namespaces_gc.py -q` | ✅ (14 tests) | ✅ green |
| 10-11-01 | 11 | 8 | STOR-16 | — | N/A | unit | `cd databasise && .venv/bin/python -m pytest tests/stores/test_vector_reserved_keys.py -q` | ✅ (5 tests) | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] The 15 new test files above (STOR-13 and STOR-14 share one grep test) and `databasise/tests/wirings/__init__.py`.
- [x] A shared fixture for a HippoRAG ingest with stubbed clients and a node that raises, plus a fixture delete wiring and registry (pattern: `tests/seam/test_delete_document.py`, `tests/seam/test_hipporag_write_path.py`).
- [x] A test-only helper that holds `graph.cozo` open in a subprocess (STOR-01 part b).
- [x] `_REFUSAL_FACTORIES` in `tests/seam/test_rest_transport.py` gains `StoreBusyError` and `UnparseableWiringError`.

---

## Manual-Only Verifications

All phase behaviours have automated verification.

---

## Validation Sign-Off

- [x] All tasks have an `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without an automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 300s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-17 (orchestrator audit; 0 gaps)

## Validation Audit 2026-10-18

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
