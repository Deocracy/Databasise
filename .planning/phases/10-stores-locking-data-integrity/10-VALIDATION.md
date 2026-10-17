---
phase: "10"
slug: "stores-locking-data-integrity"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| **Full suite command** | `cd databasise && .venv/bin/python tools/check_offline_suite.py` (baseline: 1637 passed, 1 skipped, 4 deselected, both pytest styles) |
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
| TBD | TBD | TBD | STOR-01 | — | busy refusal carries no path or namespace | integration + subprocess | `cd databasise && .venv/bin/python -m pytest tests/stores/test_graph_lock.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-02 | — | no leaked sqlite connection | unit | `cd databasise && .venv/bin/python -m pytest tests/seam/test_build_stores_cleanup.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-03 | — | resolve creates no kv or graph directories | integration | `cd databasise && .venv/bin/python -m pytest tests/seam/test_evidence_resolve_stores.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-04 | — | health creates nothing | integration | `cd databasise && .venv/bin/python -m pytest tests/seam/test_health_probe.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-05 | — | a read-only node cannot mutate | unit | `cd databasise && .venv/bin/python -m pytest tests/runner/test_capability_scoping_modes.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-06 | — | a refused run commits nothing | integration | `cd databasise && .venv/bin/python -m pytest tests/seam/test_ingest_abort.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-07 | — | N/A | integration | `cd databasise && .venv/bin/python -m pytest tests/stores/test_delete_commit_contract.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-08 | — | corruption refused, never a 500 | unit + integration | `cd databasise && .venv/bin/python -m pytest tests/stores/test_vector_crash_window.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-09 | — | N/A | unit | `cd databasise && .venv/bin/python -m pytest tests/stores/test_vector_validation.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-10 | — | N/A | unit | `cd databasise && .venv/bin/python -m pytest tests/stores/test_graph_delete_cascade.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-11 | — | N/A | unit | `cd databasise && .venv/bin/python -m pytest tests/stores/test_kv_buffer_isolation.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-12 | — | an unwired effect is refused at parse | unit + integration | `cd databasise && .venv/bin/python -m pytest tests/wirings/test_store_effects_wired.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-13 | — | blob digest path removed with the store | unit (grep) | `cd databasise && .venv/bin/python -m pytest tests/test_removed_stores_absent.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-14 | — | N/A | unit (grep) | `cd databasise && .venv/bin/python -m pytest tests/test_removed_stores_absent.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-15 | — | GC confined to `quarantined-*` under store_root | unit + subprocess | `cd databasise && .venv/bin/python -m pytest tests/test_namespaces_gc.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | STOR-16 | — | N/A | unit | `cd databasise && .venv/bin/python -m pytest tests/stores/test_vector_reserved_keys.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] The 15 new test files above (STOR-13 and STOR-14 share one grep test) and `databasise/tests/wirings/__init__.py`.
- [ ] A shared fixture for a HippoRAG ingest with stubbed clients and a node that raises, plus a fixture delete wiring and registry (pattern: `tests/seam/test_delete_document.py`, `tests/seam/test_hipporag_write_path.py`).
- [ ] A test-only helper that holds `graph.cozo` open in a subprocess (STOR-01 part b).
- [ ] `_REFUSAL_FACTORIES` in `tests/seam/test_rest_transport.py` gains `StoreBusyError` and `UnparseableWiringError`.

---

## Manual-Only Verifications

All phase behaviours have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have an `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without an automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
