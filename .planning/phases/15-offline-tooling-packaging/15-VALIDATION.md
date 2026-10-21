---
phase: "15"
slug: "offline-tooling-packaging"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: "2026-10-21"
---

# Phase 15: Validation Strategy

> This is the per-phase validation contract for feedback sampling during execution. Its source is 15-RESEARCH.md § Validation Architecture and § Section 7.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.1.1 + pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`, `addopts = '-m "not live"'`) |
| **Config file** | `databasise/pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `databasise/.venv/bin/python -m pytest -q <path> -p no:cacheprovider`, run from the repo root |
| **Wave command** | `databasise/.venv/bin/python -m pytest -q databasise -p no:cacheprovider`. The whole package takes about 11 minutes; run it in the background. |
| **Full suite command** | `databasise/.venv/bin/python databasise/tools/check_offline_suite.py`, both invocation styles. Run it in the background. |
| **Baseline** | 2608 passed, 4 deselected, in both styles (Phase 14 close) |
| **Never** | `-m live`; reading any `.env*` file, `v1/.env.parity` or `v1/parity-env.txt`; spending provider tokens; two suite runs at once |

---

## Sampling Rate

- **After every task commit:** run the task's new test file, its directory, and every protected `test_ref` file that constrains the touched code (15-RESEARCH §6.3, §9; D-23).
- **After every plan:** run the wave command, then the plan's protected set.
- **Before `/gsd-verify-work`:** the full suite must be green in both styles.

---

## Per-Requirement Verification Map

Each row test is a new node in an unprotected file. Plain pytest must fail it on pre-fix code with an AssertionError (D-22). An "extend" row may add nodes only to a file that is not a ledger `test_ref`. A row marked † was already met at HEAD.

| Req | Behavior | Test file (see 15-RESEARCH § Validation Architecture) | Status |
|-----|----------|-------------------------------------------------------|--------|
| TOOL-01 | The wheel carries the tools, bundles and fixtures; the version has one source; `mcp<3`; the import-boundary scan fixes | tests/test_packaging.py, tests/test_import_boundary.py | ⬜ |
| TOOL-02 | `import_index` uses argparse: `--help` exits 0, a bad flag exits 2, nothing is written, the workspace line prints | tests/parity/test_import_index_cli.py | ⬜ |
| TOOL-03 | A missing v2 graph is reported as `graph-topology`; the `precondition` assertion | parity verify_import test | ⬜ |
| TOOL-04 | A named failure prints one stderr line and exits 1; a bad argument exits 2 | tests/test_cli_refusals.py | ⬜ |
| TOOL-05 | Every offline CLI defaults to estimate-only (D-04) | tests/test_dry_run_default.py | ⬜ |
| TOOL-06 | A partial, degraded or cyclic run is inconclusive and exits 3 | parity run_comparison test | ⬜ |
| TOOL-07 | One `aquery_llm` call; `no_results` handling; the env refusal | tests/parity/test_v1_driver_script.py | ⬜ |
| TOOL-08 | storage_audit exits 3 on partial or cycle; `--arm hipporag` | parity storage_audit test | ⬜ |
| TOOL-09 | Preflight refusal and the selector-to-wiring check | parity cross-modality test | ⬜ |
| TOOL-10 | run_wiring canonicalises first | tracer test | ⬜ |
| TOOL-11 | The eval store boundary; empty-index refusal | tests/eval/test_eval_store_boundary.py | ⬜ |
| TOOL-12 | Calibration refusals; two-sided floor; `floors.db`; the two-stage gate | tests/seam/test_promotion_floor.py and the floor store and calibration tests | ⬜ |
| TOOL-13 | Bundle identity covers question text and gold ids | eval bundle-versioning test | ⬜ |
| TOOL-14 | Parity records render only states they read; AI causes show `recorded_by` | evidence parity-report render test | ⬜ |
| TOOL-15 | Computed verdicts and exit codes; F-07 main; one MODAL-05 value | evidence falsifier2-verdict test | ⬜ |
| TOOL-16 | Admission at load; name match; kind-only shared scope | parts admission test (new node) | ⬜ |
| TOOL-17 † | Removed stores are absent | tests/test_removed_stores_absent.py (`--at 226b2cf^`) | ⬜ |
| TOOL-18 | Mutating-tool refusal, launch timeout, error mapping | tests/foreign/test_cbm_adapter.py | ⬜ |
| TOOL-19 | Ten tools, each with a non-empty description and no plan references | tests/mcp/test_tool_descriptions.py | ⬜ |
| TOOL-20 | Docstring facts | tests/evidence/test_docstring_facts.py | ⬜ |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Each row test file in the table, written test first in the plan that completes its row. New API is guarded with `getattr`, or by capturing the exception, so that the pre-fix failure is an AssertionError.
- [ ] The inert `--spend` flag on the six CLIs, plus `--spend` added to the shared unprotected tests, all before the dry-run default lands (15-RESEARCH §9). The shared tests are `test_cli_builder_refusals`, `test_parity_cli_store_lock`, `test_storage_audit`, `test_launch_refusals` and `test_remint`.
- [ ] Owner `grant-check-edit` for `databasise/tests/seam/test_seam_events.py` (WIRE-13; 15-RESEARCH §6.4).

---

## Manual-Only Verifications

| Behavior | How | Why manual |
|----------|-----|------------|
| The installed wheel runs `aa_run --split dev`, `remint --help` and `check_import_boundary` from a temp directory | Build the wheel, install it into a fresh venv, run with `python -I -m ...` | Needs a fresh venv outside the suite. Record the result in the verification report. |

---

## Validation Sign-Off

- [ ] Every task has an `<automated>` verify, or depends on Wave 0.
- [ ] No three consecutive tasks lack an automated verify.
- [ ] Wave 0 covers every MISSING reference.
- [ ] No watch-mode flags.
- [ ] `nyquist_compliant: true` is set in the frontmatter.

**Approval:** pending
