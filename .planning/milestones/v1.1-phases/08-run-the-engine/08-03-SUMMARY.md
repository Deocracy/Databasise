---
phase: 08-run-the-engine
plan: 03
subsystem: testing
tags: [coverage-record, mcp-sdk-detection, cwd-shadow, tdd, pytest]

requires:
  - phase: 08-run-the-engine
    provides: "08-01 live marker so default pytest stays offline"
provides:
  - "databasise/evidence/COVERAGE.md: live section 18.5 record (D-13), archived v1.0 copy untouched"
  - "tool-growth cross-check reads the live record, names the path when it is missing, and is proven to fail for an unlisted tool (RUN-01)"
  - "mcp_sdk_is_installed() detects the real SDK from inside databasise/ and ignores sys.modules (RUN-04)"
affects: [08-10]

actuals:
  tokens: 6285
  tasks: 2
  commits: 4
plan_head_before: e3d6641def4314c4c2f701d80befb026b5652cc6
plan_head_after: 31c57a10359e8345d1a84fbb252eff9c7c81c863
commits: 4

tech-stack:
  added: []
  patterns:
    - "an explicit-raise file guard at module level so a missing fixture file fails collection with its path"
    - "SDK detection = PathFinder.find_spec over the project-stripped sys.path, never sys.modules"

key-files:
  created:
    - databasise/evidence/COVERAGE.md
    - databasise/tests/foreign/__init__.py
    - databasise/tests/foreign/test_mcp_sdk_guard.py
  modified:
    - databasise/tests/mcp/test_tool_growth_invariant.py
    - databasise/foreign/_mcp_sdk_guard.py

key-decisions:
  - "Live record is a verbatim copy plus one blockquote; the archived v1.0 COVERAGE.md stays frozen (D-13)"
  - "_require_coverage_file uses an explicit raise, not assert, so it still fires under python -O"
  - "mcp_sdk_is_installed bypasses sys.modules so a cached shadow cannot make the answer order-dependent"

requirements-completed: [RUN-01, RUN-04]

duration: 8min
completed: 2026-10-17
status: complete
---

# Phase 8 Plan 03: Coverage cross-check and mcp SDK detection Summary

**The section 18.5 tool-roster cross-check now reads a live `databasise/evidence/COVERAGE.md` and is proven non-vacuous, and `mcp_sdk_is_installed()` finds the real SDK through `PathFinder` on the project-stripped `sys.path` instead of reporting False when the CWD shadows `mcp`.**

## Performance

- **Duration:** about 8 min
- **Completed:** 2026-10-17T00:22Z
- **Tasks:** 2 (both TDD, RED then GREEN)
- **Files modified:** 5 (3 created, 2 modified)

## Accomplishments

- RUN-01: `tests/mcp/test_tool_growth_invariant.py` reports 9 passed (7 existing plus 2 new). A missing coverage file now raises an AssertionError naming `databasise/evidence/COVERAGE.md` at collection. An extra tool registered with `add_tool` and no coverage row makes `_check_coverage` raise.
- RUN-04: the subprocess run with cwd `databasise/` prints `True`; `tests/evidence/test_falsifier4_evidence.py` reports 8 passed and no `found=False` skip. A shadow-only tree still reports False.
- The archived `.planning/milestones/v1.0-phases/05-opaque-side-admission/COVERAGE.md` is byte-identical to HEAD; section 4 of the live copy diffs empty against it.

## TDD Evidence

**Task 1 RED (`a280685`).** `pytest tests/mcp/test_tool_growth_invariant.py`: 4 failed, 5 passed. The target `test_require_coverage_file_names_the_expected_path` failed with `NameError: name '_require_coverage_file' is not defined`; `test_coverage_check_fails_for_a_registered_tool_with_no_coverage_row` failed on `FileNotFoundError` for the old `.planning/phases/05-.../COVERAGE.md` path (the two existing cross-check tests failed the same way). Semantic assessment: both failures are the planned gaps (helper absent, record not at a stable path), not collection or fixture faults.

**Task 2 RED (`fa6592e`).** `pytest tests/foreign`: 1 failed, 2 passed. Target `test_sdk_detected_from_inside_the_project_directory` failed with `AssertionError: assert 'False' == 'True'` (the planned assertion; the SDK is installed). Semantic assessment: the old `importlib.util.find_spec` resolved `mcp` to the project's own `databasise/mcp/` through the `''` sys.path entry. The shadow-only and in-process tests passed before the fix because they do not exercise the CWD entry, so they are regression guards, not RED drivers.

**GREEN.** `d024e88` (Task 1) and `31c57a1` (Task 2). No REFACTOR commit.

`tdd_mode` is off in this project's config, so `gsd_run check tdd-red-evidence` was not run; the pytest output above is the RED record.

## Task Commits

1. **Task 1 RED** - `a280685` (test)
2. **Task 1 GREEN** - `d024e88` (feat)
3. **Task 2 RED** - `fa6592e` (test)
4. **Task 2 GREEN** - `31c57a1` (fix)

## Verification

- `pytest -q tests/mcp tests/evidence tests/foreign` from `databasise/`: 109 passed, no skip line with `found=False`.
- `pytest -q -rs tests/evidence/test_falsifier4_evidence.py tests/foreign tests/parts_core/test_codebase_memory_mcp_admission.py` (via `python -m pytest`): 42 passed.
- `pytest -q -rs tests/evidence/test_falsifier4_evidence.py tests/foreign tests/mcp` (bare `pytest`): 44 passed.
- `python -c '... print(mcp_sdk_is_installed())'` from `databasise/`: `True`.
- Acceptance greps: one match each for the blockquote, `"evidence" / "COVERAGE.md"`, `def _check_coverage`, `PathFinder.find_spec`; `tests/mcp/__init__.py` absent.
- `ruff check` clean on the touched files.

## Files Created/Modified

- `databasise/evidence/COVERAGE.md` - live section 18.5 record, verbatim copy plus one blockquote
- `databasise/tests/mcp/test_tool_growth_invariant.py` - `_require_coverage_file`, `_check_coverage`, two new tests, `_COVERAGE_PATH` repointed, `_REPO_ROOT` dropped
- `databasise/foreign/_mcp_sdk_guard.py` - `mcp_sdk_is_installed` body and docstring; `import importlib.machinery` replaces the now-unused `importlib.util`
- `databasise/tests/foreign/__init__.py`, `databasise/tests/foreign/test_mcp_sdk_guard.py` - three RUN-04 tests

## Decisions Made

See `key-decisions` above. `import importlib.util` was removed because nothing else in the module used it.

## Deviations from Plan

None - plan executed exactly as written. Two small notes: the plan's verify line expects "9 passed", which matches; ruff's import-sort and ISC004 rules required reformatting the new test file's imports and one string, done before the GREEN commit.

## Issues Encountered

None. No ImportError from the 08-01 reinstall overlap occurred.

## Known Stubs

None.

## Threat Flags

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Both baseline failures and the contradictory falsifier-4 skip are gone under both invocation styles. v1.1 tools and routes add their rows to `databasise/evidence/COVERAGE.md`.

## Self-Check: PASSED

Created files exist (`databasise/evidence/COVERAGE.md`, `databasise/tests/foreign/__init__.py`, `databasise/tests/foreign/test_mcp_sdk_guard.py`); commits `a280685`, `d024e88`, `fa6592e`, `31c57a1` are ancestors of HEAD; all task acceptance criteria and the plan-level verification re-ran green.

---
*Phase: 08-run-the-engine*
*Completed: 2026-10-17*
