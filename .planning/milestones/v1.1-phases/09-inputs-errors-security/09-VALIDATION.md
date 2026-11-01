---
phase: "09"
slug: "inputs-errors-security"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-16"
---

# Phase 09 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (`asyncio_mode = "auto"`), `-m "not live"` by default |
| **Config file** | `databasise/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd databasise && uv run pytest tests/seam/<file>.py -q -x` |
| **Full suite command** | `cd databasise && .venv/bin/python tools/check_offline_suite.py` (after phase: 1560 passed, 1 skipped, 4 deselected, both pytest styles) |
| **Estimated runtime** | ~225 seconds |

---

## Sampling Rate

- **After every task commit:** the task's new test file, plus `cd databasise && uv run pytest tests/seam/test_rest_transport.py tests/mcp -q` when `refusals.py`, `rest.py` or `server.py` changed
- **After every plan wave:** `cd databasise && uv run pytest tests/seam tests/mcp tests/parts_core -q`
- **Before `/gsd-verify-work`:** full suite green (1251 + new tests, 0 failed)
- **Max feedback latency:** 240 seconds

---

## Per-Task Verification Map

One row per requirement; task IDs from the ten plans. All 16 files run green together (301 passed, 2026-10-17).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 09-06-01 | 06 | 6 | SEAM-01 | — | path traversal refused before any mkdir | integration | `cd databasise && uv run pytest tests/seam/test_evidence_namespace_guard.py -q` | ✅ (22 tests) | ✅ green |
| 09-01-01, 09-02-01 | 01, 02 | 1–2 | SEAM-02 | — | oversize body < 4 KB | integration | `cd databasise && uv run pytest tests/seam/test_refusal_body_shape.py -q` | ✅ (15 tests) | ✅ green |
| 09-04-01, 09-04-02 | 04 | 4 | SEAM-03 | — | N/A | integration | `cd databasise && uv run pytest tests/mcp/test_mcp_refusal_mapping.py -q` | ✅ (55 tests) | ✅ green |
| 09-02-03 | 02 | 2 | SEAM-04 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_refusal_status_codes.py -q` | ✅ (44 tests) | ✅ green |
| 09-05-01 | 05 | 5 | SEAM-05 | — | no server paths or tracebacks leak | integration | `cd databasise && uv run pytest tests/seam/test_foreign_engine_refusal.py -q` | ✅ (9 tests) | ✅ green |
| 09-05-02 | 05 | 5 | SEAM-06 | — | no stderr in 5xx body | integration | `cd databasise && uv run pytest tests/seam/test_corpus_adapter_failures.py -q` | ✅ (27 tests) | ✅ green |
| 09-02-01, 09-03-01 | 02, 03 | 2–3 | SEAM-07 | — | no file written outside corpus-inbox | integration | `cd databasise && uv run pytest tests/seam/test_ingest_input_refusals.py -q` | ✅ (22 tests) | ✅ green |
| 09-03-02 | 03 | 3 | SEAM-08 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_page_bounds.py -q` | ✅ (23 tests) | ✅ green |
| 09-06-02 | 06 | 6 | SEAM-09 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_empty_inputs.py -q` | ✅ (20 tests) | ✅ green |
| 09-07-01 | 07 | 7 | SEAM-10 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_empty_capability_selector.py -q` | ✅ (9 tests) | ✅ green |
| 09-08-01, 09-08-02 | 08 | 8 | SEAM-11 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_compare_keys.py -q` | ✅ (12 tests) | ✅ green |
| 09-07-02 | 07 | 7 | SEAM-12 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_promote_alias_validation.py -q` | ✅ (7 tests) | ✅ green |
| 09-02-01 | 02 | 2 | SEAM-13 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_upload_selector_field.py -q` | ✅ (9 tests) | ✅ green |
| 09-01-02 | 01 | 1 | SEAM-14 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_refusal_catalogue.py -q` | ✅ (5 tests) | ✅ green |
| 09-09-01 | 09 | 9 | SEAM-15 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_ingest_file_name.py -q` | ✅ (5 tests) | ✅ green |
| 09-09-02, 09-10-01, 09-10-03 | 09, 10 | 9–10 | SEAM-16 | — | leak check survives -O | integration | `cd databasise && uv run pytest tests/seam/test_seam_doc_consistency.py -q` | ✅ (17 tests) | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `databasise/tests/seam/test_evidence_namespace_guard.py` — SEAM-01
- [x] `databasise/tests/seam/test_refusal_body_shape.py` — SEAM-02
- [x] `databasise/tests/mcp/test_mcp_refusal_mapping.py` — SEAM-03
- [x] `databasise/tests/seam/test_refusal_status_codes.py` — SEAM-04
- [x] `databasise/tests/seam/test_foreign_engine_refusal.py` — SEAM-05
- [x] `databasise/tests/seam/test_corpus_adapter_failures.py` — SEAM-06
- [x] `databasise/tests/seam/test_ingest_input_refusals.py` — SEAM-07
- [x] `databasise/tests/seam/test_page_bounds.py` — SEAM-08
- [x] `databasise/tests/seam/test_empty_inputs.py` — SEAM-09
- [x] `databasise/tests/seam/test_empty_capability_selector.py` — SEAM-10
- [x] `databasise/tests/seam/test_compare_keys.py` — SEAM-11
- [x] `databasise/tests/seam/test_promote_alias_validation.py` — SEAM-12
- [x] `databasise/tests/seam/test_upload_selector_field.py` — SEAM-13
- [x] `databasise/tests/seam/test_refusal_catalogue.py` — SEAM-14
- [x] `databasise/tests/seam/test_ingest_file_name.py` — SEAM-15
- [x] `databasise/tests/seam/test_seam_doc_consistency.py` — SEAM-16
- [x] Shared test helper: promote an alias with a real trace token; stub-client builder (pattern `tests/mcp/test_dual_transport_parity.py` `_stub_clients`)
- [x] `_REFUSAL_FACTORIES` in `tests/seam/test_rest_transport.py` gains every new refusal
- [x] Owner `grant-check-edit` for `tests/mcp/test_tool_growth_invariant.py` and `tests/seam/test_rest_corpus_endpoints.py`

---

## Manual-Only Verifications

All phase behaviors have automated verification. Checkpoint tasks 09-02-02 and 09-10-02 are owner grant gates with no automated verify.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 240s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-10-17 (orchestrator audit; 0 gaps)

## Validation Audit 2026-10-17

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
