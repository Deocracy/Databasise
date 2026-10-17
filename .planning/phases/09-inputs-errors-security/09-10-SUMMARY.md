---
phase: 09-inputs-errors-security
plan: 10
subsystem: api
tags: [seam, redact, selectors, python-O, dead-code, docs]
status: complete

requires:
  - phase: 09-09
    provides: "tests/seam/test_seam_doc_consistency.py (docstring half)"
provides:
  - "redact.py leak checks raise AssertionError explicitly, so they fire under python -O (SEAM-16)"
  - "selectors._DEFAULT_ARM and selectors._ARM_NAMES removed; selector docstrings describe the all_wirings() pool"
  - "protected growth test imports _ARM_NAMES from databasise.wirings.resolve (owner grant, ledger v354)"
affects: []

commits: 2
plan_head_before: 7ca2adf6ef92539f10a484fc706096aa318e3536
plan_head_after: 2b310c4c71afe373cf9e26a61ddf0ade85ca7c5c

actuals:
  tokens: 5000
  tasks: 3
  commits: 2

tech-stack:
  added: []
  patterns:
    - "test-time gates raise AssertionError explicitly instead of using assert, so python -O cannot strip them"
    - "python -O behaviour is checked in a subprocess with sys.executable and cwd=tmp_path"

key-files:
  created: []
  modified:
    - databasise/seam/redact.py
    - databasise/seam/selectors.py
    - databasise/tests/mcp/test_tool_growth_invariant.py
    - databasise/tests/seam/test_seam_doc_consistency.py

key-decisions:
  - "redact.py is a test-time gate (tests and the leak gate over recorded responses), never called on the serving path; its checks raise explicitly"
  - "The selector candidate pool is documented as all_wirings(); capability ties break by pool order (stable sort), not by a separate arm tuple"

metrics:
  duration: "~25 min (continuation, Task 3 + SUMMARY)"
  completed: 2026-10-17
---

# Phase 9 Plan 10: Leak gate under python -O and dead selector constants Summary

The redact identity-leak checks now raise `AssertionError` explicitly and still fire under `python -O`; the dead `selectors._DEFAULT_ARM` / `selectors._ARM_NAMES` constants are gone, the selector docstrings describe the `all_wirings()` pool, and the one protected test import moved to `databasise.wirings.resolve._ARM_NAMES` under the owner's grant.

## Tasks

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Tracer: redact leak checks fire under python -O | c6e8782 | databasise/seam/redact.py, databasise/tests/seam/test_seam_doc_consistency.py |
| 2 | Owner grant-check-edit for the protected growth test | (owner action, ledger v354; ledger files left to the orchestrator) | — |
| 3 | Remove dead selector constants and stale docstrings; phase gate | 2b310c4 | databasise/seam/selectors.py, databasise/tests/mcp/test_tool_growth_invariant.py, databasise/tests/seam/test_seam_doc_consistency.py |

## Evidence

**Task 1, python -O before and after.**
- Pre-change `redact.py` (from 7ca2adf), run under `python -O` with `assert_no_forbidden_keys({'node-x': 1}, {'node-x'})` then `assert_no_forbidden_values({'component': 'node-x'}, {'node-x'})`: `pre_exit=0` (both planted leaks passed silently).
- Post-change, same key check under `python -O`: `AssertionError: forbidden key 'node-x' found at $.node-x`, `post_exit=1`.
- The clean envelope `{'answer': 'node-x', 'evidence': []}` with an empty forbidden set exits 0 under `-O` (test `test_clean_envelope_with_an_empty_forbidden_set_passes_both_checks_under_python_dash_o`).

**Task 3, RED then GREEN.**
- RED (before the selectors edit): `6 failed, 11 deselected` for `-k selectors` in `tests/seam/test_seam_doc_consistency.py` (attribute check, four stale-phrase cases, all_wirings() docstring check).
- GREEN: `tests/seam/test_seam_doc_consistency.py tests/seam/test_selectors.py tests/mcp/test_tool_growth_invariant.py tests/seam/test_leak.py`: `58 passed`.
- `python -c "import databasise.seam.selectors as s; assert not hasattr(s, '_DEFAULT_ARM') and not hasattr(s, '_ARM_NAMES')"` printed `dead constants gone`.

**Protected-file diff (one line, owner-granted).** `databasise/tests/mcp/test_tool_growth_invariant.py` line 49:
- before: `from databasise.seam.selectors import _ARM_NAMES as _PRODUCTION_ARM_NAMES`
- after: `from databasise.wirings.resolve import _ARM_NAMES as _PRODUCTION_ARM_NAMES`
- `git show --stat` for 2b310c4 reports `1 insertion, 1 deletion` (`2 +-`) on that file.

**Phase gate (`databasise/.venv/bin/python tools/check_offline_suite.py`, exit 0):**
- `pytest -q -rs: 1560 passed, 1 skipped, 4 deselected in 258.75s (0:04:18)`
- `python -m pytest -q -rs: 1560 passed, 1 skipped, 4 deselected in 256.56s (0:04:16)`

## Deviations from Plan

None in code. Process notes:
- The plan's "confirm no other importer" check could not grep the `databasise/tests/` tree: the BAK check-edit guard blocks recursive grep over protected test files. Production packages were grepped (no importer of the removed constants), and the full offline suite (1560 passed) imports every test module, so a remaining test importer would have failed as an ImportError.
- Task 3 was committed as one commit (tests plus implementation), with the RED run recorded above, following Task 1's single-commit pattern.

## Known Stubs

None.

## Self-Check: PASSED

- FOUND: databasise/seam/redact.py, databasise/seam/selectors.py, databasise/tests/seam/test_seam_doc_consistency.py, databasise/tests/mcp/test_tool_growth_invariant.py
- FOUND: c6e8782, 2b310c4 (ancestors of HEAD)
