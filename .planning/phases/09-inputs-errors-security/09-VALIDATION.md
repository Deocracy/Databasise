---
phase: "09"
slug: "inputs-errors-security"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| **Full suite command** | `cd databasise && uv run pytest -q -rs` (baseline 1251 passed, 1 skipped, 4 deselected) |
| **Estimated runtime** | ~225 seconds |

---

## Sampling Rate

- **After every task commit:** the task's new test file, plus `cd databasise && uv run pytest tests/seam/test_rest_transport.py tests/mcp -q` when `refusals.py`, `rest.py` or `server.py` changed
- **After every plan wave:** `cd databasise && uv run pytest tests/seam tests/mcp tests/parts_core -q`
- **Before `/gsd-verify-work`:** full suite green (1251 + new tests, 0 failed)
- **Max feedback latency:** 240 seconds

---

## Per-Task Verification Map

Seeded per requirement from 09-RESEARCH.md; task IDs are filled once plans exist.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | SEAM-01 | — | path traversal refused before any mkdir | integration | `cd databasise && uv run pytest tests/seam/test_evidence_namespace_guard.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-02 | — | oversize body < 4 KB | integration | `cd databasise && uv run pytest tests/seam/test_refusal_body_shape.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-03 | — | N/A | integration | `cd databasise && uv run pytest tests/mcp/test_mcp_refusal_mapping.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-04 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_refusal_status_codes.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-05 | — | no server paths or tracebacks leak | integration | `cd databasise && uv run pytest tests/seam/test_foreign_engine_refusal.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-06 | — | no stderr in 5xx body | integration | `cd databasise && uv run pytest tests/seam/test_corpus_adapter_failures.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-07 | — | no file written outside corpus-inbox | integration | `cd databasise && uv run pytest tests/seam/test_ingest_input_refusals.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-08 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_page_bounds.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-09 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_empty_inputs.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-10 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_empty_capability_selector.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-11 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_compare_keys.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-12 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_promote_alias_validation.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-13 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_upload_selector_field.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-14 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_refusal_catalogue.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-15 | — | N/A | integration | `cd databasise && uv run pytest tests/seam/test_ingest_file_name.py -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEAM-16 | — | leak check survives -O | integration | `cd databasise && uv run pytest tests/seam/test_seam_doc_consistency.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `databasise/tests/seam/test_evidence_namespace_guard.py` — SEAM-01
- [ ] `databasise/tests/seam/test_refusal_body_shape.py` — SEAM-02
- [ ] `databasise/tests/mcp/test_mcp_refusal_mapping.py` — SEAM-03
- [ ] `databasise/tests/seam/test_refusal_status_codes.py` — SEAM-04
- [ ] `databasise/tests/seam/test_foreign_engine_refusal.py` — SEAM-05
- [ ] `databasise/tests/seam/test_corpus_adapter_failures.py` — SEAM-06
- [ ] `databasise/tests/seam/test_ingest_input_refusals.py` — SEAM-07
- [ ] `databasise/tests/seam/test_page_bounds.py` — SEAM-08
- [ ] `databasise/tests/seam/test_empty_inputs.py` — SEAM-09
- [ ] `databasise/tests/seam/test_empty_capability_selector.py` — SEAM-10
- [ ] `databasise/tests/seam/test_compare_keys.py` — SEAM-11
- [ ] `databasise/tests/seam/test_promote_alias_validation.py` — SEAM-12
- [ ] `databasise/tests/seam/test_upload_selector_field.py` — SEAM-13
- [ ] `databasise/tests/seam/test_refusal_catalogue.py` — SEAM-14
- [ ] `databasise/tests/seam/test_ingest_file_name.py` — SEAM-15
- [ ] `databasise/tests/seam/test_seam_doc_consistency.py` — SEAM-16
- [ ] Shared test helper: promote an alias with a real trace token; stub-client builder (pattern `tests/mcp/test_dual_transport_parity.py` `_stub_clients`)
- [ ] `_REFUSAL_FACTORIES` in `tests/seam/test_rest_transport.py` gains every new refusal
- [ ] Owner `grant-check-edit` for `tests/mcp/test_tool_growth_invariant.py` and `tests/seam/test_rest_corpus_endpoints.py`

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 240s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
