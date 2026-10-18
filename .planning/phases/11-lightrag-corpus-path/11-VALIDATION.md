---
phase: "11"
slug: "lightrag-corpus-path"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
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
| **Full suite command** | `cd databasise && .venv/bin/python tools/check_offline_suite.py` (after phase: 2036 passed, 4 deselected, both pytest styles, ~8 min each) |
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
| 11-01, 11-02, 11-06 | 11-01, 11-02, 11-06 | 1, 2, 4 | LRAG-01 | — | two store roots never share a v1 dir | unit | `cd databasise && .venv/bin/pytest -q tests/seam/test_lightrag_working_dir.py` | ✅ (4 tests) | ✅ green |
| 11-01 | 11-01 | 1 | LRAG-02 | — | N/A | integration (real v1) | `cd databasise && .venv/bin/pytest -q tests/seam/test_lightrag_corpus_path.py` | ✅ (9 tests) | ✅ green |
| 11-01, 11-03 | 11-01, 11-03 | 1, 2 | LRAG-03 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/seam/test_lightrag_ingest_mach11.py` | ✅ (2 + 7 (test_v1_index_sync) tests) | ✅ green |
| 11-06 | 11-06 | 4 | LRAG-04 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/seam/test_corpus_write_gate.py` | ✅ (9 tests) | ✅ green |
| 11-03, 11-07 | 11-03, 11-07 | 2, 5 | LRAG-05 | — | no stderr in bodies | unit | `cd databasise && .venv/bin/pytest -q tests/foreign/test_v1_corpus_adapter.py` | ✅ (11 + 17 (test_v1_driver_protocol) tests) | ✅ green |
| 11-03, 11-07, 11-09 | 11-03, 11-07, 11-09 | 2, 5, 7 | LRAG-06 | — | key names only, never values | unit + real driver | `cd databasise && .venv/bin/pytest -q tests/foreign/test_v1_not_configured.py` | ✅ (7 tests) | ✅ green |
| 11-03, 11-08 | 11-03, 11-08 | 2, 6 | LRAG-07 | — | N/A | integration (real v1) | `cd databasise && .venv/bin/pytest -q tests/seam/test_interrupted_documents.py` | ✅ (3 + 2 (test_retry_tool) tests) | ✅ green |
| 11-03, 11-05 | 11-03, 11-05 | 2, 3 | LRAG-08 | — | suffix validated before any write | integration (real v1) | `cd databasise && .venv/bin/pytest -q tests/seam/test_lightrag_corpus_path.py -k upload` | ✅ (9 + 17 (test_upload_suffixes) tests) | ✅ green |
| 11-05 | 11-05 | 3 | LRAG-09 | — | inbox scoped per workspace and emptied | integration | `cd databasise && .venv/bin/pytest -q tests/seam/test_lightrag_inbox.py` | ✅ (10 tests) | ✅ green |
| 11-03, 11-05 | 11-03, 11-05 | 2, 3 | LRAG-10 | — | N/A | integration | `cd databasise && .venv/bin/pytest -q tests/seam/test_lightrag_corpus_path.py -k duplicate` | ✅ (9 tests) | ✅ green |
| 11-03 | 11-03 | 2 | LRAG-11 | — | N/A | unit + real | `cd databasise && .venv/bin/pytest -q tests/parts_core/lightrag/test_corpus_metering.py` | ✅ (9 tests) | ✅ green |
| 11-03 | 11-03 | 2 | LRAG-12 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/parts_core/lightrag/test_full_ingest_compat.py` | ✅ (11 tests) | ✅ green |
| 11-09 | 11-09 | 7 | LRAG-13 | — | health writes nothing | unit | `cd databasise && .venv/bin/pytest -q tests/seam/test_health_honesty.py` | ✅ (6 + 2 (test_status_during_write) tests) | ✅ green |
| 11-09 | 11-09 | 7 | LRAG-14 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/seam/test_health_honesty.py` | ✅ (6 tests) | ✅ green |
| 11-02 | 11-02 | 2 | LRAG-15 | — | eval never writes the operator corpus | unit | `cd databasise && .venv/bin/pytest -q tests/eval/test_corpus_ingest.py tests/eval/test_aa_run.py` | ✅ (7 (test_lightrag_eval_store) tests) | ✅ green |
| 11-10 | 11-10 | 8 | LRAG-16 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/seam/test_empty_namespace.py` | ✅ (7 tests) | ✅ green |
| 11-11 | 11-11 | 9 | LRAG-17 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/parts_core/lightrag/test_kg_fidelity.py tests/parts_core/lightrag/test_v1_prompt_drift.py` | ✅ (14 + 3 tests) | ✅ green |
| 11-04 | 11-04 | 1 | LRAG-18 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/parts_core/lightrag/test_kg_fidelity.py` | ✅ (11 (test_kg_retrieval_fidelity) tests) | ✅ green |
| 11-10 | 11-10 | 8 | LRAG-19 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/parity/test_arm_conformance.py tests/seam/test_query_trace_nodes.py` | ✅ (9 + 8 tests) | ✅ green |
| 11-03 | 11-03 | 2 | LRAG-20 | — | N/A | unit | `cd databasise && .venv/bin/pytest -q tests/parts_core/lightrag/test_full_ingest_compat.py` | ✅ (11 tests) | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] The new test files listed above.
- [x] A shared real-v1 harness fixture: driver plus v1 against a loopback OpenAI-compatible stub server, with the env overlay pointed at a temp file. Never read `v1/.env.parity` or its target `v1/parity-env.txt`.
- [x] `_REFUSAL_FACTORIES` in `tests/seam/test_rest_transport.py` gains every new refusal.
- [x] One consolidated owner `grant-check-edit` for the ledger-protected test files the phase must edit. Per research these are `test_rest_corpus_endpoints.py`, `test_ingest_file_name.py`, `test_store_effects_wired.py` and `test_tool_growth_invariant.py`; re-check at plan time.

---

## Manual-Only Verifications

All phase behaviors have automated verification. Checkpoint task 11-03-01 is the owner grant gate with no automated verify.

---

## Validation Sign-Off

- [x] All tasks have an `<automated>` verify or a Wave 0 dependency
- [x] Sampling continuity: no 3 consecutive tasks without an automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 300s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-18 (orchestrator audit; 0 gaps)

## Validation Audit 2026-10-18

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
