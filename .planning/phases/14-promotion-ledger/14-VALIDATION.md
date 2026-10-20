---
phase: "14"
slug: "promotion-ledger"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-20"
---

# Phase 14: Validation Strategy

> This is the per-phase validation contract for feedback sampling during execution. Its source is 14-RESEARCH.md § Validation Architecture and § Section 7.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`, `addopts = '-m "not live"'`) |
| **Config file** | `databasise/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `databasise/.venv/bin/python -m pytest -q <path> -p no:cacheprovider`, run from the repo root |
| **Wave command** | `databasise/.venv/bin/python -m pytest -q databasise/tests/seam databasise/tests/ledger databasise/tests/parts databasise/tests/parts_core databasise/tests/evidence databasise/tests/validator databasise/tests/wirings databasise/tests/mcp databasise/tests/runner -p no:cacheprovider` |
| **Full suite command** | `databasise/.venv/bin/python databasise/tools/check_offline_suite.py`, run from the repo root. It runs the suite in both styles. |
| **Baseline** | 2482 passed, 4 deselected, in both styles (Phase 13 close, HEAD 2096270) |
| **Never** | `-m live`, or reading any `.env*` file or `v1/parity-env.txt` |

`test_operator_verb_concurrency.py::test_six_concurrent_promotes_mint_six_distinct_versions_with_zero_exceptions` can flake under parallel load. Run it alone when it fails.

---

## Sampling Rate

- **After every task commit:** run three things: the task's new test file, its directory, and every protected `test_ref` file that constrains the touched code (14-RESEARCH §6.3; D-16).
- **After every plan:** run the wave command, then the plan's protected set from 14-RESEARCH § Validation Architecture.
- **Before `/gsd-verify-work`:** the full suite must be green in both styles.

---

## Per-Requirement Verification Map

Every row test is a new node in an unprotected new file. It must fail on pre-fix code with a plain AssertionError: guard new API with `hasattr` or `getattr`. A row marked † already passes at HEAD, so its fail-first is `record-fail --at <fixing commit>^` (D-17).

| Req | Behavior | Test file | Plan | Status |
|-----|----------|-----------|------|--------|
| LEDG-01 | No verb ever returns a 500 on a partial trace. Promote gives 422 `PartialRunEvidenceError`; rollback and retire proceed using `arm_id`; an unidentified partial trace is refused by name | tests/seam/test_partial_run_evidence.py | 14-08 | ⬜ |
| LEDG-02 | Promote refuses `partial=true` traces, including the old-format record and a failed one-node bypass run; `partial=false` and degraded-but-not-partial runs still promote | tests/seam/test_promote_refuses_partial.py | 14-08 | ⬜ |
| LEDG-03 | Alias rows for hipporag, or for an arm that cannot be resolved, never 500 on any selector route | tests/seam/test_alias_resolution.py | 14-06 | ⬜ |
| LEDG-04 | Retire refuses a version in the active lineage; rollback refuses a tombstoned lineage | tests/seam/test_retire_lineage.py | 14-09 | ⬜ |
| LEDG-05 | Empty and hash-shaped aliases are refused by all three verbs, with no row written | tests/seam/test_operator_alias_validation.py | 14-08 | ⬜ |
| LEDG-06 | Connections are closed; refused verbs create no `ledger.db`; the docstring says no "stall" | tests/ledger/test_ledger_lifecycle.py | 14-09 | ⬜ |
| LEDG-07 | `history_for_alias` returns rows oldest first, with `id` and `created_at` | tests/ledger/test_ledger_history.py | 14-02 | ⬜ |
| LEDG-08 | All six arms × both gate verbs give `GateNotCalibratedError`, with no ledger file; plus the §3.5.1 doc check | tests/seam/test_promotion_posture.py (new node) | 14-08 | ⬜ |
| LEDG-09 | `debug` is a strict boolean on REST and MCP; the tenancy phrase is documented | tests/seam/test_trace_resolve_strict_flag.py (REST, MCP and doc legs in one file) | 14-05 | ⬜ |
| LEDG-10 † | `writes_*` never selects a read-only arm; per-arm effect table | tests/seam/test_capability_effects.py (`--at 3fd6e4c^`) | 14-04 | ⬜ |
| LEDG-11 † | A kind mismatch is reported by name; every shipped wiring parses | tests/validator/test_node_kind.py (`--at 5d61a79^`) | 14-04 | ⬜ |
| LEDG-12 | Every admitted registered part is reachable | tests/parts/test_registry_reachability.py | 14-07 | ⬜ |
| LEDG-13 | `_corpus_wiring` loads through `load_wiring`; a missing file gives `NoWritePathForModalityError` | tests/seam/test_corpus_wiring.py | 14-06 | ⬜ |
| LEDG-14 | The stale phrases are absent from the named modules | tests/test_docstring_currency.py | 14-10 | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] The 14 row test files above, each written test first in the plan that completes its row.
- [ ] Non-row tests: 14-02 creates `tests/ledger/test_ledger_store_api.py`; 14-03 creates `tests/wirings/test_wiring_for_name.py` and `tests/seam/test_promotion_refusals.py`; 14-08 creates `tests/seam/test_unresolvable_alias_row_verbs.py`.
- [ ] `_REFUSAL_FACTORIES` entries and imports for `PartialRunEvidenceError` and `GateNotCalibratedError`, in unprotected `tests/seam/test_rest_transport.py`. They go in 14-03, before any row points at that file.
- [ ] Stub LLM and embedding clients for the HippoRAG-alias ingest leg, copied into the new LEDG-03 test file.
- [ ] Owner `grant-check-edit` for `tests/seam/test_refusal_reachability.py` (WIRE-17), with the edit from 14-RESEARCH §6.4 (checkpoint plan 14-01, wave 1; 14-07 makes the edit).

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
