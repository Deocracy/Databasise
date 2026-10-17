---
phase: 08-run-the-engine
plan: 01
subsystem: infra
tags: [uvicorn, fastapi, fcntl, console-script, pytest-markers, launcher]

requires:
  - phase: 05-seam
    provides: create_app REST app and Databasise engine
  - phase: 03-parity
    provides: run_arm client builder and DEFAULT_STORE_ROOT
provides:
  - "databasise-rest console script serving GET /health from the populated store with one worker"
  - "clients/builder.py: the one shipped env-file parser and client builder (moved from parity/run_arm.py)"
  - "store_lock.py: cross-process flock on <store_root>/.engine.lock holding the holder PID"
  - "launcher package: shared arguments, lock-then-clients start sequence, refusal printing"
  - "pytest live marker with addopts '-m \"not live\"' and three marked live tests"
affects: [08-02, 08-03, 08-05, 08-06, 08-07, 08-10]

actuals:
  tokens: 8256
  tasks: 2
  commits: 2
plan_head_before: f02e89f517a7ab0eca00caca9e0e416a42b1c548
plan_head_after: b2ae5f1764b4552a1b46ea5c989cfd854927b4d4
commits: 2

tech-stack:
  added: []
  patterns:
    - "lock-then-clients: the launcher takes the store lock before building clients or the app"
    - "re-export under the old underscore names so moved helpers keep every importer and monkeypatch seam"
    - "launcher tests import phase-created names inside test bodies so they collect on the pre-phase tree"

key-files:
  created:
    - databasise/clients/builder.py
    - databasise/store_lock.py
    - databasise/launcher/__init__.py
    - databasise/launcher/serve_rest.py
    - databasise/tests/launcher/__init__.py
    - databasise/tests/launcher/test_launchers.py
  modified:
    - databasise/parity/run_arm.py
    - databasise/pyproject.toml
    - databasise/tests/parity/test_embedder_index_reproduction.py
    - databasise/tests/parity/test_retrieval_parity.py
    - databasise/tests/parity/test_naive_arm_end_to_end.py

key-decisions:
  - "UnparseableProviderRoutingError message withholds the env value; raw_value stays as an attribute only (RUN-05 privacy)"
  - "No default env file: databasise-rest without --env-file or --no-clients exits 2 (D-11, RESEARCH OQ4)"
  - "DEFAULT_WORKSPACE is the literal shared-4fab18fef508b7bc3dda1cc2d8f12e36, so snapshot drift cannot stop the launcher serving the store"
  - "run_arm re-exports the builder with a single from-import under '# isort: off' (ruff otherwise splits aliased imports into one statement per name)"

patterns-established:
  - "Refusals print 'databasise: <message>' to stderr and return exit code 1; argparse errors return 2"

requirements-completed: [RUN-05, RUN-06, RUN-07, RUN-11, RUN-12]

coverage:
  - id: D1
    description: "Installed databasise-rest serves GET /health 200 with builder-built clients and holds .engine.lock with its PID"
    requirement: "RUN-06"
    verification:
      - kind: integration
        ref: "databasise/tests/launcher/test_launchers.py#test_databasise_rest_serves_health_from_the_installed_script"
        status: pass
    human_judgment: false
  - id: D2
    description: "Missing env keys and a malformed routing body stop startup by key name without echoing any env value"
    requirement: "RUN-05"
    verification:
      - kind: integration
        ref: "databasise/tests/launcher/test_launchers.py#test_missing_env_keys_stop_startup_naming_every_missing_key"
        status: pass
      - kind: integration
        ref: "databasise/tests/launcher/test_launchers.py#test_malformed_routing_body_is_refused_without_echoing_it"
        status: pass
    human_judgment: false
  - id: D3
    description: "--workers above 1 is refused naming the store lock before any lock file exists; the lock is taken before create_app"
    requirement: "RUN-07"
    verification:
      - kind: integration
        ref: "databasise/tests/launcher/test_launchers.py#test_workers_above_one_is_refused_naming_the_store_lock"
        status: pass
    human_judgment: false
  - id: D4
    description: "Launcher defaults are the populated store, the RUN-06 workspace literal and loopback; an env file is required unless --no-clients"
    requirement: "RUN-06"
    verification:
      - kind: unit
        ref: "databasise/tests/launcher/test_launchers.py#test_engine_argument_defaults_are_the_populated_store_on_loopback"
        status: pass
      - kind: integration
        ref: "databasise/tests/launcher/test_launchers.py#test_env_file_is_required_without_no_clients"
        status: pass
    human_judgment: false
  - id: D5
    description: "Shared builder moved out of parity/run_arm.py with every importer still working"
    requirement: "RUN-05"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_naive_arm_end_to_end.py -k build_clients; tests/eval; tests/test_import_boundary.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "Default pytest run deselects exactly the three live-endpoint tests; -m live selects exactly them"
    requirement: "RUN-12"
    verification:
      - kind: other
        ref: "pytest --collect-only tests/parity (3 deselected); pytest --collect-only -m live tests (3/1075)"
        status: pass
    human_judgment: false

duration: ~35min (not timed at start)
completed: 2026-10-17
status: complete
---

# Phase 8 Plan 01: Run the engine tracer Summary

**Installed `databasise-rest` console script: argparse, store flock, shared client builder, `create_app`, one-worker uvicorn, GET /health 200, plus a `live` pytest marker that makes the default suite offline**

## Performance

- **Duration:** ~35 min (start time not captured)
- **Completed:** 2026-10-17T00:14Z
- **Tasks:** 2
- **Files modified:** 11 (6 created, 5 modified)

## Accomplishments
- `databasise-rest` serves GET /health 200 from the installed script; `<store_root>/.engine.lock` holds the launcher PID while it runs.
- Builder moved to `databasise/clients/builder.py`; `parity/run_arm.py` re-exports it under the old underscore names, so `_build_clients is builder.build_clients` and every exception class keeps identity.
- Refusals: missing env keys, malformed `OPENAI_LLM_EXTRA_BODY`, missing `--env-file`, `--workers` above 1 all stop before serving, naming keys only; no env value reaches stderr.
- `live` marker registered with `addopts = '-m "not live"'`; exactly three tests marked; the embedder test prints a `LIVE-MEASURE` line for the D-14 measurement.

## Task Commits

1. **Task 1: End-to-end databasise-rest tracer** - `d5a85ed` (feat)
2. **Task 2: live marker and addopts** - `b2ae5f1` (test)

Tracer feedback gate: mode `end-of-phase`, automated-only `<verify>`; re-ran `tests/launcher/test_launchers.py` (6 passed) before Task 2, then expanded.

## Files Created/Modified
- `databasise/clients/builder.py` - env-file parser, six-key tuple, routing-body parser, `build_clients`, three error classes
- `databasise/store_lock.py` - `acquire_store_lock`, `store_lock`, `StoreLockedError`
- `databasise/launcher/__init__.py` - shared args, `open_engine` (lock first), `refuse`, `LAUNCH_REFUSALS`
- `databasise/launcher/serve_rest.py` - `databasise-rest` entry point
- `databasise/parity/run_arm.py` - builder block removed, re-exports added
- `databasise/pyproject.toml` - console script, `databasise.launcher` package, pytest marker and addopts
- `databasise/tests/launcher/` - six subprocess/argument tests
- three parity test files - `@pytest.mark.live`; embedder test gains the `LIVE-MEASURE` print

## Decisions Made
See `key-decisions` above; all follow the plan.

## Deviations from Plan

None - plan executed exactly as written. Implementation notes, not deviations:
- The aliased re-export in `run_arm.py` uses `# isort: off` / `# isort: on` with one `# noqa: F401`, because ruff's import sorter otherwise splits it into one statement per name.
- `launcher/__init__.py` closes the lock fd itself if client construction fails after the lock is taken, so a refused start never leaves the lock held.

## Issues Encountered
- A stray `cat > file` line in one shell call blocked on stdin and delayed the reinstall; killed and redone, no repo effect.
- `ruff check tests/parity` reports 5 findings in files this plan did not edit (`test_cross_modality_isolation.py`, `test_parity_evidence.py`, `test_storage_audit.py`, import order in `test_naive_arm_end_to_end.py`); all pre-existing, left alone.

## User Setup Required
None - no external service configuration required. The venv was reinstalled with `uv sync --inexact --extra rest --extra mcp --reinstall-package databasise`.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: unauthenticated-network-endpoint | databasise/launcher/serve_rest.py | `databasise-rest` serves the REST app (no authentication) on a TCP port; default host is 127.0.0.1, `--host` can widen it |

## Next Phase Readiness
- The MCP launcher, lock-refusal, rerank and CORS plans extend `launcher/` and `store_lock.py`, which now work end to end.
- Full-suite runs are offline from commit `b2ae5f1`.

## Self-Check: PASSED

---
*Phase: 08-run-the-engine*
*Completed: 2026-10-17*
