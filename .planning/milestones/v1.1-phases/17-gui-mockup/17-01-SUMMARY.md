---
phase: 17-gui-mockup
plan: 01
subsystem: testing
tags: [playwright, pytest, nixos, gui, mockup, html-parser]
requires: []
provides:
  - "Playwright 1.59.0 dev dependency (greenlet, pyee) and nixpkgs Chromium 1217 under pytest"
  - "databasise/tests/gui harness: mockup_path, browser, ui fixtures and MockUI"
  - "GUI-01, GUI-02 and build-stability test nodes, failing on the missing mockup (fail-first base)"
affects: [17-02, 17-03, 17-04, 17-05, 17-06, 17-07, 17-08, 17-09, 17-10, 17-11, 17-12, 17-13]
tech-stack:
  added: [playwright==1.59.0, greenlet, pyee]
  patterns:
    - "missing mockup is raised in pytest_pyfunc_call so a fail-first run reports failed, not ERROR"
    - "GUI tests are plain sync functions that use ui.expect and never import playwright"
key-files:
  created:
    - databasise/tests/gui/__init__.py
    - databasise/tests/gui/conftest.py
    - databasise/tests/gui/test_playwright_smoke.py
    - databasise/tests/gui/test_gui_01_shell.py
    - databasise/tests/gui/test_gui_02_ids.py
    - databasise/tests/gui/test_mockup_build.py
  modified:
    - databasise/pyproject.toml
    - databasise/uv.lock
key-decisions:
  - "Missing-mockup assertion lives in a conftest pytest_pyfunc_call hook, not in the mockup_path fixture, because a failing fixture is reported as ERROR and the plan requires '8 failed'"
  - "ui fetches browser lazily (request.getfixturevalue) after the file check, so a missing file fails before any browser work even when the browser would skip"
  - "Bundled playwright node driver runs on legion (nix-ld); PLAYWRIGHT_NODEJS_PATH is not needed"
requirements-completed: []
duration: resumed run (two executors)
completed: 2026-10-29
status: complete
commits: 3
plan_head_before: 43a6caa8b9ad9a043ba0394611acdb1d6bf442e7
plan_head_after: 6e392799cb58e78ebe085df3b1776d12910d0880
actuals:
  tokens: 9000
  tasks: 2
  commits: 3
---

# Phase 17 Plan 01: Playwright harness and GUI fail-first base Summary

Playwright for Python 1.59.0 drives nixpkgs Chromium 1217 under pytest on legion, and the GUI-01, GUI-02 and build-stability tests are committed in full with no mockup, all eight nodes failing on the missing file.

Requirements GUI-01 and GUI-02 are NOT marked complete: this plan only writes their failing tests. 17-02 builds the mockup that makes them pass, and the orchestrator records the ledger rows. `requirements-completed` is therefore empty on purpose.

## What was built

- Task 1 (tracer): `playwright==1.59.0` in `[dependency-groups].dev` with `uv.lock` updated (greenlet, pyee); browsers via the GC-rooted symlink `~/.cache/databasise/playwright-browsers` -> `/nix/store/nrbrqc9172dja86w0xdcjafswd4qsml3-playwright-browsers`, which holds `chromium-1217`, `chromium_headless_shell-1217`, `ffmpeg-1011`, `firefox-1511`, `webkit-2272`. `playwright install` was never run. Smoke test passes (`1 passed`) with the bundled node driver and no `PLAYWRIGHT_NODEJS_PATH`.
- Task 2: `test_gui_01_shell.py` (4 nodes), `test_gui_02_ids.py` (3 nodes), `test_mockup_build.py` (1 node), as specified. The GUI-02 predicate is proven on a fixed id-less sample (7 missing + 2 marker mismatches) inside the row node, and I checked it separately: it reports exactly 7 and 2, and passes a well-formed sample whose ids also match `scripts/mockup-id-check.py`.
- The `ui` fixture and `MockUI` methods were exercised once against a throwaway fake page (nav, show, set_state, inject, load, resize, no_horizontal_scroll, request capture); the scratch test and page were deleted and are not committed.

## GUI fail-first base

Commit `6e39279` (`test(17-01): failing GUI-01, GUI-02 and build-stability tests`). `git ls-tree -r --name-only 6e39279 mockups` prints nothing. Run:
`DATABASISE_REQUIRE_BROWSER=1 databasise/.venv/bin/python -m pytest -q databasise/tests/gui/test_gui_01_shell.py databasise/tests/gui/test_gui_02_ids.py databasise/tests/gui/test_mockup_build.py -p no:cacheprovider` gives `8 failed in 0.11s`. Row-node failure lines:

- `FAILED databasise/tests/gui/test_gui_01_shell.py::test_gui_01_six_screens_switch_with_header_health_and_no_requests` - `AssertionError: /home/chris/coding/Databasise-2.0-fully-agnostic-system/mockups/operator-console.html is missing (GUI mockup not built yet)` (databasise/tests/gui/conftest.py:36)
- `FAILED databasise/tests/gui/test_gui_02_ids.py::test_gui_02_every_control_has_a_unique_id_matching_the_checked_in_list` - same AssertionError at conftest.py:36

All eight nodes fail with that message; none errors or skips.

## Commits

- `cf94eda` test(17-01): Playwright harness on nixpkgs Chromium (pyproject.toml, uv.lock, tests/gui `__init__`, conftest, smoke test)
- `6e39279` test(17-01): failing GUI-01, GUI-02 and build-stability tests

`commits: 3` is the measured `git rev-list --count` from the ledger base; it includes the orchestrator's `6a9f72a chore(17): owner resume-gate recorded (ledger v853)`, which sits between the recorded base and this plan's first commit. The plan's own code commits are 2.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing mockup produced 8 ERRORs, not 8 failed**
- **Found during:** Task 2 fail-first run
- **Issue:** the plan specifies `assert MOCKUP.is_file()` inside the `mockup_path` fixture, but pytest reports a fixture exception as ERROR, and the plan's verify requires the summary line to be exactly `8 failed` (any `error` fails it).
- **Fix:** `mockup_path` now just returns the path; a `pytest_pyfunc_call` hook in conftest.py asserts the file exists for any test whose fixture closure contains `mockup_path` (so also via `ui`). `ui` returns early without launching a browser when the file is missing and obtains `browser` through `request.getfixturevalue` afterwards.
- **Files modified:** databasise/tests/gui/conftest.py
- **Commit:** 6e39279 (conftest edit rides in the Task 2 commit; Task 1's commit holds the first version)

**2. [Plan wording] `test_hash_route_opens_the_named_screen` takes `ui`, not `(mockup_path, browser)`**
- The spec forbids test modules importing playwright and the node needs `expect`; the test reuses `ui`, navigates to `<url>#ledger` and reloads, which exercises the load-time hash route and also gets the page-error assertion. Node id unchanged.

**3. [Plan wording] network-reference scan uses regexes**
- `test_file_references_no_network_resource` matches `<link`, `<script ... src=`, `<img ... src=`, `@import`, `url(http` case-insensitively with regexes (a superset of the literal strings in the plan, so `<script  src=` with extra spaces is also caught).

None of these changes weaken a required assertion.

## Notes for later plans

- `grep -n 'name = "pyee"' databasise/uv.lock` returns two lines (the package entry and a `{ name = "pyee" }` dependency reference); same for greenlet. Both packages are present as required.
- Branch was `main` (isolation none, orchestrator-directed); the HEAD protected-branch assertion was not applied for that reason.
- conftest.py is final per the plan; `MockUI` exposes only the listed methods.

## Known Stubs

None.

## Threat Flags

None. T-17-01 mitigation is in place before the file exists: `test_file_references_no_network_resource` and the `ui` request capture (offline context, GUI-01 asserts `ui.requests == []`). T-17-SC: packages installed by the owner under D-15, pinned and hashed in uv.lock; no `playwright install`.

## Self-Check: PASSED

- databasise/tests/gui/{__init__,conftest,test_playwright_smoke,test_gui_01_shell,test_gui_02_ids,test_mockup_build}.py present.
- Commits cf94eda and 6e39279 are ancestors of HEAD.
- Smoke test `1 passed`; fail-first run `8 failed`.
