---
phase: "17"
slug: "gui-mockup"
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: validated
nyquist_compliant: true
wave_0_complete: true
created: "2026-10-25"
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2+ (pytest-asyncio auto mode) with Playwright for Python 1.59.0, sync API |
| **Config file** | `databasise/pyproject.toml` `[tool.pytest.ini_options]` (no new config) |
| **Quick run command** | `cd databasise && DATABASISE_REQUIRE_BROWSER=1 .venv/bin/python -m pytest tests/gui/test_gui_0N_<name>.py -q -x` |
| **Full suite command** | `cd databasise && DATABASISE_REQUIRE_BROWSER=1 .venv/bin/python -m pytest -q` |
| **Estimated runtime** | ~60 seconds for tests/gui (estimate, not measured) |

---

## Sampling Rate

- **After every task commit:** the single GUI test file for the screen being built, run with `DATABASISE_REQUIRE_BROWSER=1`
- **After every plan wave:** `cd databasise && DATABASISE_REQUIRE_BROWSER=1 .venv/bin/python -m pytest tests/gui -q`
- **Before `/gsd-verify-work`:** the full suite must be green, plus `python3 scripts/plan-gate.py --root . --phase 17 --plans .planning/phases/17-gui-mockup`
- **Max feedback latency:** 120 seconds

---

## Per-Task Verification Map

| Requirement | Test file | Test Type | Automated Command | File Exists | Status |
|-------------|-----------|-----------|-------------------|-------------|--------|
| GUI-01 | tests/gui/test_gui_01_shell.py | browser | `pytest tests/gui/test_gui_01_shell.py -q` | ✅ | ✅ green |
| GUI-02 | tests/gui/test_gui_02_ids.py | unit | `pytest tests/gui/test_gui_02_ids.py -q` | ✅ | ✅ green |
| GUI-03 | tests/gui/test_gui_03_needs_backend.py | unit + app routes | `pytest tests/gui/test_gui_03_needs_backend.py -q` | ✅ | ✅ green |
| GUI-04 | tests/gui/test_gui_04_query_mode.py | browser | `pytest tests/gui/test_gui_04_query_mode.py -q` | ✅ | ✅ green |
| GUI-05 | tests/gui/test_gui_05_compare.py | browser | `pytest tests/gui/test_gui_05_compare.py -q` | ✅ | ✅ green |
| GUI-06 | tests/gui/test_gui_06_errors.py | browser + unit | `pytest tests/gui/test_gui_06_errors.py -q` | ✅ | ✅ green |
| GUI-07 | tests/gui/test_gui_07_evidence_trace.py | browser | `pytest tests/gui/test_gui_07_evidence_trace.py -q` | ✅ | ✅ green |
| GUI-08 | tests/gui/test_gui_08_documents.py | browser | `pytest tests/gui/test_gui_08_documents.py -q` | ✅ | ✅ green |
| GUI-09 | tests/gui/test_gui_09_corpus.py | browser | `pytest tests/gui/test_gui_09_corpus.py -q` | ✅ | ✅ green |
| GUI-10 | tests/gui/test_gui_10_ledger.py | browser | `pytest tests/gui/test_gui_10_ledger.py -q` | ✅ | ✅ green |
| GUI-11 | tests/gui/test_gui_11_graph.py | browser + unit | `pytest tests/gui/test_gui_11_graph.py -q` | ✅ | ✅ green |
| support | tests/gui/test_playwright_smoke.py | smoke | `pytest tests/gui/test_playwright_smoke.py -q` | ✅ | ✅ green |
| inventory | tests/gui/test_inventory_map.py | unit | `pytest tests/gui/test_inventory_map.py -q` | ✅ | ✅ green |

*Commands run from `databasise/` with `.venv/bin/python -m`. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `databasise/tests/gui/__init__.py`, `conftest.py`, and the 11 requirement test files plus the smoke test. The tests must fail, not skip, when the mockup file is absent.
- [x] `playwright==1.59.0` in `[dependency-groups].dev` and `uv lock` (owner-approved, CONTEXT D-15)
- [x] Browsers: `nix-build '<nixpkgs>' -A playwright-driver.browsers -o ~/.cache/databasise/playwright-browsers`, with `PLAYWRIGHT_BROWSERS_PATH` set
- [x] `docs/gui/MOCK-IDS.json` generator and `docs/gui/GAP-ROUTES.json`
- [x] REQUIREMENTS.md and UI-SPEC amendments for D-06 to D-10 and D-14, landed before the screen plans
- [ ] Ledger `test_ref`/`code_ref` set for each GUI row, then `record-fail` (through `scripts/ledger-amend.py`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Owner click-through approval of the mockup | GUI-01 to GUI-11 (D-12) | Visual and owner judgement | Open `mockups/operator-console.html` from file:// in a local browser, walk all six screens, approve, and record the sha256 in `docs/gui/MOCKUP-APPROVAL.md` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 120s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-10-31 (68 passed in tests/gui, 29.5 s, DATABASISE_REQUIRE_BROWSER=1)

## Validation Audit 2026-10-31

| Metric | Count |
|---|---|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
