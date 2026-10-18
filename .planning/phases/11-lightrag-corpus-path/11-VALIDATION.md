---
phase: "11"
slug: "lightrag-corpus-path"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-17"
---

# Phase 11: Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio (`asyncio_mode = "auto"`), `-m "not live"` by default |
| **Config file** | `databasise/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd databasise && .venv/bin/pytest tests/seam tests/parts_core/lightrag tests/foreign -x -q` |
| **Full suite command** | `cd databasise && .venv/bin/python tools/check_offline_suite.py` (baseline: 1861 passed, 1 skipped, 4 deselected, both pytest styles) |
| **Real-v1 harness** | real driver plus v1 against a loopback OpenAI-compatible stub server (RUN-12 allows loopback). Skips when `v1/.venv/bin/python` is absent. |
| **Estimated runtime** | ~300 seconds per pytest style |

---

## Sampling Rate

- **After every task commit:** the task's test file plus `tests/seam tests/foreign -q`.
- **After every plan wave:** `cd databasise && .venv/bin/pytest -q tests/seam tests/mcp tests/foreign tests/parts_core tests/eval tests/parity`.
- **Before `/gsd-verify-work`:** `tools/check_offline_suite.py` passes with 0 failed.
- **Max feedback latency:** 300 seconds.

---

## Per-Task Verification Map

This map is seeded per requirement from 11-RESEARCH.md. Task IDs are filled once plans exist.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | LRAG-01 | — | two store roots never share a v1 dir | unit | `cd databasise && .venv/bin/pytest -q tests/seam/test_lightrag_working_dir.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-02 | — | N/A | integration (real v1) | `cd databasise && .venv/bin/pytest -q tests/seam/test_lightrag_corpus_path.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-03 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/seam/test_lightrag_ingest_mach11.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-04 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/seam/test_corpus_write_gate.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-05 | — | no stderr in bodies | unit | `cd databasise && .venv/bin/pytest -q tests/foreign/test_v1_corpus_adapter.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-06 | — | key names only, never values | unit + real driver | `cd databasise && .venv/bin/pytest -q tests/foreign/test_v1_not_configured.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-07 | — | N/A | integration (real v1) | `cd databasise && .venv/bin/pytest -q tests/seam/test_interrupted_documents.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-08 | — | suffix validated before any write | integration (real v1) | `cd databasise && .venv/bin/pytest -q tests/seam/test_lightrag_corpus_path.py -k upload` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-09 | — | inbox scoped per workspace and emptied | integration | `cd databasise && .venv/bin/pytest -q tests/seam/test_lightrag_inbox.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-10 | — | N/A | integration | `cd databasise && .venv/bin/pytest -q tests/seam/test_lightrag_corpus_path.py -k duplicate` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-11 | — | N/A | unit + real | `cd databasise && .venv/bin/pytest -q tests/parts_core/lightrag/test_corpus_metering.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-12 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/parts_core/lightrag/test_full_ingest_compat.py` | ✅ (edit) | ⬜ pending |
| TBD | TBD | TBD | LRAG-13 | — | health writes nothing | unit | `cd databasise && .venv/bin/pytest -q tests/seam/test_health_honesty.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-14 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/seam/test_health_honesty.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-15 | — | eval never writes the operator corpus | unit | `cd databasise && .venv/bin/pytest -q tests/eval/test_corpus_ingest.py tests/eval/test_aa_run.py` | ✅ (edit) | ⬜ pending |
| TBD | TBD | TBD | LRAG-16 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/seam/test_empty_namespace.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-17 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/parts_core/lightrag/test_kg_fidelity.py tests/parts_core/lightrag/test_v1_prompt_drift.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-18 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/parts_core/lightrag/test_kg_fidelity.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | LRAG-19 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/parity/test_arm_conformance.py tests/seam/test_query_trace_nodes.py` | partial | ⬜ pending |
| TBD | TBD | TBD | LRAG-20 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/parts_core/lightrag/test_full_ingest_compat.py` | ✅ (edit) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] The new test files listed above.
- [ ] A shared real-v1 harness fixture: driver plus v1 against a loopback OpenAI-compatible stub server, with the env overlay pointed at a temp file. Never read `v1/.env.parity` or its target `v1/parity-env.txt`.
- [ ] `_REFUSAL_FACTORIES` in `tests/seam/test_rest_transport.py` gains every new refusal.
- [ ] One consolidated owner `grant-check-edit` for the ledger-protected test files the phase must edit. Per research these are `test_rest_corpus_endpoints.py`, `test_ingest_file_name.py`, `test_store_effects_wired.py` and `test_tool_growth_invariant.py`; re-check at plan time.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have an `<automated>` verify or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without an automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 300s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
