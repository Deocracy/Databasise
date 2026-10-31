---
phase: 18-gui-live
plan: 02
subsystem: ui
tags: [console, launcher, csp, test-harness, playwright, uvicorn]

requires:
  - phase: 18-gui-live
    provides: databasise.console package data with the built operator-console.html (18-01)
provides:
  - "databasise-rest --console flag and GET /console route (loopback host, fixed port, hash-source CSP)"
  - "serve_rest.console_csp(page): sha256 hash-source policy computed once at start-up"
  - "databasise/tests/gui_live/ in-process live harness (start_live_app, LiveApp.hold/fail, LiveUI, open_live_ui, call-phase failure hooks) and shared LightRAG corpus fake"
  - "LIVE-01 serving tests (11) and the documented console invocation in API-INVENTORY 5.1a"
affects: [18-03, 18-gui-live]

actuals:
  tokens: 7100
  tasks: 2
  commits: 3
plan_head_before: 4873892c06b6e990643a4a014cd350f501f31471
plan_head_after: 65dd69989f77171ba9702cf69e1299d73bd59f3a

tech-stack:
  added: []
  patterns:
    - "Launcher app runs under uvicorn on a pre-bound 127.0.0.1 socket in a daemon thread, so build_app knows the real port for the Origin guard"
    - "Page errors and non-loopback requests fail the test in the call phase through a wrapper pytest_runtest_call hook"
    - "CSP uses sha256 hash sources computed from the shipped HTML at start-up; no inline-allow keyword"

key-files:
  created:
    - databasise/tests/gui_live/__init__.py
    - databasise/tests/gui_live/conftest.py
    - databasise/tests/gui_live/_corpus_fake.py
    - databasise/tests/gui_live/_opened.py
    - databasise/tests/gui_live/test_live_01_serving.py
  modified:
    - databasise/launcher/serve_rest.py
    - docs/gui/API-INVENTORY.md

key-decisions:
  - "The launcher computes the CSP hashes from the packaged page at start-up, so a rebuilt console needs no sidecar file and mockups/build.py stays unchanged"
  - "--console is refused for a non-loopback --host and for --port 0 by parser.error before the store lock is taken"

requirements-completed: []

duration: n/a
completed: 2026-10-31
status: complete
---

# Phase 18 Plan 02: Serve the console and stand up the live harness Summary

**`databasise-rest --console` serves the packaged console at GET /console with a sha256 hash-source CSP, and an in-process uvicorn + Chromium harness proves a page fetch POST /query returns 200 with no CORS message.**

## Accomplishments

- `--console` flag in `databasise/launcher/serve_rest.py`. `main` refuses a non-loopback `--host` (even with `--allow-remote-unauthenticated`) and `--port 0` with `parser.error`, before `open_engine` takes the store lock. `--console` does not imply `--operator`.
- `console_csp(page)` finds the one executable inline script and the one style block, hashes them, and returns the policy from the plan. It raises `RuntimeError` for any other count, so the launcher refuses to start; the `application/json` fixtures block is ignored. The policy contains no inline-allow keyword.
- `GET /console` (`include_in_schema=False`) returns the bytes read once through `importlib.resources`, with CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and `Cache-Control: no-store`. `/openapi.json` is equal with and without the flag.
- The live harness in `databasise/tests/gui_live/`. `start_live_app` binds a socket first, parses the real launcher arguments, builds the app with stub clients and the shared corpus fake, and runs uvicorn on that socket. A start failure (including argparse `SystemExit`) lands in `start_error` and is raised from `pytest_pyfunc_call`, so it reports as failed, not error. A page error or a non-loopback request raises in a `pytest_runtest_call` wrapper, on the test itself.
- `docs/gui/API-INVENTORY.md` section 5.1a records the console invocation.

## Task Commits

1. Task 1 RED: `8e40601` test(18-02): add the live harness and the failing LIVE-01 serving test
2. Task 1 GREEN: `eff8804` feat(18-02): serve the operator console at GET /console with --console
3. Task 2: `65dd699` test(18-02): server-side LIVE-01 checks and the documented console invocation

## Fail-first proof

RED commit: `8e40601`, proving LIVE-01 (serving). At that commit `test_page_fetch_post_query_returns_200_without_cors_errors` reported `1 failed` (not error) with `databasise-rest: error: unrecognized arguments: --console` and named `test_live_01_serving.py`. The ten server-side tests added in Task 2 check code Task 1 already wrote and pass on arrival; their fail-first proof is the Task 1 RED commit, where the HEAD version of the file fails because the flag does not exist. LIVE-01 is not marked complete here; the row closes in plan 18-11.

## Verification

- `databasise/tests/gui_live/test_live_01_serving.py`: 11 passed, including the wheel test (the offline uv build ran, no skip).
- With `test_inventory_map.py`, `test_console_surface.py`, `test_rest_cors.py` and `test_launchers.py`: 51 passed.
- Task 1 acceptance greps: `include_in_schema=False` 1, `def console_csp` 1, `unsafe-inline` 0, `def start_live_app` 1, `wrapper=True` 1, `mark.live` 0. Task 2: 11 test functions, the invocation line present once, `git status` clean for the locked files.

## Deviations from Plan

**1. [Rule 3 - Blocking] Added `databasise/tests/gui_live/_opened.py`**
- **Found during:** Task 2
- **Issue:** The test file imports `open_live_ui` from `databasise.tests.gui_live.conftest`, but pytest loads the conftest as `gui_live.conftest`. A second copy of the module has its own `_OPENED` list, so the call-phase page-error check would not see UIs a test opens itself.
- **Fix:** The list lives in the new `_opened.py`, imported by its full dotted name, so both copies share it.
- **Files modified:** `databasise/tests/gui_live/_opened.py`, `databasise/tests/gui_live/conftest.py`
- **Commit:** 65dd699

**Total deviations:** 1 auto-fixed (1 blocking). **Impact:** one extra 12-line test-support file; no behavior change.

## Known Stubs

None.

## Threat Flags

None. The new route and flag are the plan's T-18-03 to T-18-06 surface, mitigated as planned.

## Self-Check: PASSED

- All created files present; commits 8e40601, eff8804 and 65dd699 are ancestors of HEAD.
