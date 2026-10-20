---
phase: "13"
slug: "selectors-wiring-runner"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-19"
---

# Phase 13: Validation Strategy

> This is the per-phase validation contract for feedback sampling during execution. Its source is 13-RESEARCH.md § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`, `addopts = '-m "not live"'`) |
| **Config file** | `databasise/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `cd databasise && .venv/bin/pytest -q tests/<dir>/<file>.py -x` |
| **Wave command** | `cd databasise && .venv/bin/pytest -q tests/seam tests/runner tests/validator tests/wirings tests/identity tests/parts tests/parts_core tests/evidence tests/parity` |
| **Full suite command** | `cd databasise && .venv/bin/python tools/check_offline_suite.py`. It runs the suite in both styles and takes about 20 minutes. |
| **Baseline** | At HEAD, `.venv/bin/pytest -q` gives 2203 passed and 4 deselected, in 590 s. |
| **Never** | `-m live`, or reading any `.env*` file |

---

## Sampling Rate

- **After every task commit:** run the task's new test file and the directory it lives in.
- **After every plan wave:** run the wave command, then the protected files that the touched decisions rely on (13-RESEARCH §10).
- **Before `/gsd-verify-work`:** the full suite must be green in both styles.

---

## Per-Requirement Verification Map

Each row has its own test node in an unprotected new file. That node must fail on pre-fix code with a plain AssertionError. A row marked † already passes at HEAD on one leg; its fail-first proof comes from another leg, or from `record-fail --at` an older commit (13-CONTEXT specifics).

| Req | Behavior | Test file | Status |
|-----|----------|-----------|--------|
| WIRE-01 | All six candidates are reachable, and the mapping is documented | tests/seam/test_selector_reachability.py | ⬜ |
| WIRE-02 | Ghost provides and evidence references are refused; KG arms return evidence | tests/validator/test_top_level_refs.py, tests/seam/test_evidence_position.py | ⬜ |
| WIRE-03 | Reason codes are closed and node-free | tests/seam/test_stop_reason_leak.py | ⬜ |
| WIRE-04 | depth_label is the answering node's depth, or null | tests/seam/test_depth_label.py | ⬜ |
| WIRE-05 † | Pre-dispatch problems are refused by name | tests/seam/test_preflight_refusals.py | ⬜ |
| WIRE-06 | parse_wiring never raises | tests/validator/test_parse_report.py | ⬜ |
| WIRE-07 † | Execution placement has one source | tests/validator/test_execution_mode_single_source.py | ⬜ |
| WIRE-08 | A guard reads its declared signal | tests/runner/test_guard_evaluation.py | ⬜ |
| WIRE-09 | No ignored guards key remains | tests/wirings/test_lightrag_guards.py | ⬜ |
| WIRE-10 | One NodeTrace per pruned node | tests/runner/test_trace_completeness.py | ⬜ |
| WIRE-11 | NodeTrace fields are truthful | tests/runner/test_node_trace_fields.py | ⬜ |
| WIRE-12 | Arm identity, persistence before refusal, and a truthful concurrency setting | tests/seam/test_run_record_identity.py | ⬜ |
| WIRE-13 † | Seam events name the capability and report failed vs halted | tests/seam/test_seam_events.py | ⬜ |
| WIRE-14 † | Engine internals fail by name | tests/seam/test_engine_internals.py | ⬜ |
| WIRE-15 | Environment inputs, and health on digest failure | tests/identity/test_env.py | ⬜ |
| WIRE-16 † | The registry validates effects | tests/seam/test_advanced_query_members.py | ⬜ |
| WIRE-17 † | Tests pin where each partly reachable refusal occurs | tests/seam/test_refusal_reachability.py | ⬜ |
| WIRE-18 † | Runner surface is wired or deleted | tests/runner/test_runner_surface.py | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Create the 18 row test files and `tests/evidence/test_derived_trace_schema.py`. Each is written in the plan that implements its row, test first, and must fail by assertion.
- [ ] Add a probe helper in `tests/seam/_probes.py` (unprotected) for the local-arm partial run.
- [ ] Owner `grant-check-edit`:
  - `tests/seam/test_query_trace_nodes.py` (LRAG-19, D-03)
  - `tests/seam/test_lightrag_ingest_mach11.py` (LRAG-03, D-15)

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] Every task has an `<automated>` verify, or depends on Wave 0.
- [ ] No three consecutive tasks lack an automated verify.
- [ ] Wave 0 covers every MISSING reference.
- [ ] No watch-mode flags.
- [ ] `nyquist_compliant: true` is set in the frontmatter.

**Approval:** pending
