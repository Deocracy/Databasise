---
phase: 08-run-the-engine
plan: 09
subsystem: testing
tags: [pytest, offline-gate, socket-guard, run-12]

requires:
  - phase: 08-run-the-engine
    provides: "08-01..08-08 fixes (RUN-01 failures, RUN-04 found=False skip) that make the suite green"
provides:
  - "databasise/tools/check_offline_suite.py: RUN-12 dual-invocation gate (pytest and python -m pytest, sequential, exit 0/1)"
  - "NonLoopbackConnectionError and the autouse _offline_unless_live socket guard in tests/conftest.py"
affects: [08-10, phase 08 verification]

actuals:
  tokens: 2100
  tasks: 2
  commits: 3
plan_head_before: 9220993760710345f60672683cbf6dcd2f8baa5b
plan_head_after: e8d14448109ee8eeb423c09398345ea07943a8c4
commits: 3

tech-stack:
  added: []
  patterns:
    - "gate script keeps parsing in pure functions so its tests never start a pytest subprocess"
    - "offline is a checked claim: non-live tests cannot connect to a non-loopback address"

key-files:
  created:
    - databasise/tools/check_offline_suite.py
    - databasise/tests/test_check_offline_suite.py
  modified:
    - databasise/tests/conftest.py

key-decisions:
  - "The gate passes no marker expression; it relies on addopts '-m \"not live\"' and only checks that the default run's summary says 'deselected'"
  - "The guard wraps socket.socket.connect and connect_ex in this interpreter only; subprocesses are unaffected"
  - "The guard test matches NonLoopbackConnectionError by class name because tests/ is not an importable package"

patterns-established:
  - "Skip-reason audit: contradictory_skips flags found=False / 'mcp extra is not installed' lines while importlib.metadata resolves mcp"

requirements-completed: [RUN-12]

coverage:
  - id: D1
    description: "tools/check_offline_suite.py runs both pytest invocation styles sequentially and exits 1 on any failure, contradictory skip, or a default run with no deselected tests"
    requirement: RUN-12
    verification:
      - kind: unit
        ref: "databasise/tests/test_check_offline_suite.py#test_a_not_installed_skip_is_contradictory_when_mcp_is_installed"
        status: pass
      - kind: other
        ref: "databasise/.venv/bin/python databasise/tools/check_offline_suite.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "A non-live test cannot connect to a non-loopback address; loopback, AF_UNIX and live-marked tests are not guarded"
    requirement: RUN-12
    verification:
      - kind: unit
        ref: "databasise/tests/test_check_offline_suite.py#test_the_offline_guard_refuses_a_non_loopback_connect, #test_the_offline_guard_allows_loopback"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-17
status: complete
---

# Phase 08 Plan 09: Offline Suite Gate Summary

**RUN-12 gate script that runs `pytest` and `python -m pytest` back to back and fails on any failure or environment-contradicting skip, plus a conftest socket guard that refuses non-loopback connects from tests not marked live**

## Performance

- **Duration:** about 25 min (the gate run itself is 7m25s)
- **Completed:** 2026-10-17T01:53Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- `tools/check_offline_suite.py` exposes `parse_skip_lines`, `contradictory_skips`, `summary_line`, `has_deselected`, `mcp_is_installed`, `run_style`, `main`. Exit 0 only when both styles exit 0, no skip line contradicts an installed `mcp`, and the default run reports deselected tests.
- `tests/conftest.py` gains `NonLoopbackConnectionError` (attrs `address`, `nodeid`) and the autouse fixture `_offline_unless_live`, which wraps `socket.socket.connect` and `connect_ex`.
- Gate run, both styles green (quoted from `.venv/bin/python tools/check_offline_suite.py`):
  - `pytest -q -rs: 1215 passed, 1 skipped, 4 deselected in 219.41s (0:03:39)`
  - `python -m pytest -q -rs: 1215 passed, 1 skipped, 4 deselected in 222.61s (0:03:42)`
  - No contradictory-skip line printed. The one skip is the `DATABASISE_RUN_REAL_DELETE` opt-in, true to the environment. 1215 = 1207 baseline + 8 new tests.
- No test needed `NonLoopbackConnectionError` handling: none was re-marked live or given a stub, so there is no list of such tests.

## TDD record

- **RED** (`8655d79`): `tests/test_check_offline_suite.py` (6 gate tests) failed at collection with `ImportError: cannot import name 'check_offline_suite'`. Semantic assessment: the target module did not exist, so the import error is the intended failure for a new module; it is not a fixture or syntax fault. The format-based `check tdd-red-evidence` classifier was not run (plan is `type: execute`, not `type: tdd`).
- **GREEN** (`d9a93be`): module added, 6 passed.
- **Guard** (`e8d1444`): the two guard tests and the conftest fixture were committed together (task 2 is not marked `tdd`).
- No REFACTOR commit.

## Task Commits

1. **Task 1: gate script** - `8655d79` (test, RED), `d9a93be` (feat, GREEN)
2. **Task 2: offline guard and green gate** - `e8d1444` (test)

## Files Created/Modified

- `databasise/tools/check_offline_suite.py` - the RUN-12 gate
- `databasise/tests/test_check_offline_suite.py` - 8 tests: 6 gate parsers, 2 guard
- `databasise/tests/conftest.py` - `NonLoopbackConnectionError`, `_offline_unless_live`

## Decisions Made

- The gate adds no marker expression of its own; deselection of live tests stays owned by `addopts`.
- Guard covers this interpreter only; subprocess launcher tests (127.0.0.1) and the MCP stdio test (pipes) are unaffected, and they passed.
- `_is_local_host` accepts `""`, `localhost`, loopback and unspecified IPs including IPv4-mapped IPv6; any other string, including an unresolved hostname, is refused.

## Deviations from Plan

None - plan executed exactly as written. Small additions inside scope: `check=False` on `subprocess.run` to satisfy ruff PLW1510, and import sorting in the new test file.

## Issues Encountered

- `tests/` is not an importable package, so the guard test cannot `from tests.conftest import NonLoopbackConnectionError`; it matches by class name and `address` attribute instead.
- Pre-existing, not touched: ruff UP035 on `from typing import Callable` in `tests/conftest.py`.

## Known Stubs

None.

## Threat Flags

None.

## Next Phase Readiness

Plan 08-10 can cite `tests/test_check_offline_suite.py::test_a_not_installed_skip_is_contradictory_when_mcp_is_installed` as RUN-12's ledger test_ref. The phase gate command is `cd databasise && .venv/bin/python tools/check_offline_suite.py` (about 7.5 minutes).

## Self-Check: PASSED

- FOUND: databasise/tools/check_offline_suite.py, databasise/tests/test_check_offline_suite.py, databasise/tests/conftest.py
- FOUND commits: 8655d79, d9a93be, e8d1444 (rev-list count 3 from 9220993)

---
*Phase: 08-run-the-engine*
*Completed: 2026-10-17*
