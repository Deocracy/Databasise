---
phase: 16-gui-connectors
plan: 11
subsystem: api
tags: [operator-surface, log-tail, uvicorn-logging, launcher]
requires: [16-04]
provides:
  - "databasise-rest --log-file PATH and serve_rest.log_config_for(path)"
  - "create_app(log_path=) and Databasise(log_path=), Databasise.log_tail(limit)"
  - "GET /log?limit=1..1000, mounted only with --operator and --log-file"
affects: []
status: complete
commits: 4
plan_head_before: 5c8f96f0628c9dd9940da0eb64c43437c1e13319
plan_head_after: a0b69a908845b1fd22da57db83d792b813e8eeaf
actuals:
  tokens: 4500
  tasks: 2
  commits: 4
tech-stack:
  added: []
  patterns:
    - "uvicorn LOGGING_CONFIG copy with a FileHandler on uvicorn, uvicorn.access and root; disable_existing_loggers false"
    - "log lines redacted on read with redact_secrets then the URL scrub"
key-files:
  created:
    - databasise/tests/seam/test_console_log.py
  modified:
    - databasise/launcher/serve_rest.py
    - databasise/seam/rest.py
    - databasise/seam/engine.py
    - databasise/seam/operator_rest.py
key-decisions:
  - "GET /log needs both --operator and --log-file (D-18); --log-file alone still writes the file"
  - "No log_config kwarg is passed to uvicorn.run without --log-file (log_config=None would disable uvicorn logging)"
  - "D-19: the log tail narrows Phase 9 D-04 in one off-by-default, loopback-only place; recorded in the flag help, the route description and the log_tail docstring"
requirements-completed: [CONN-14]
---

# Phase 16 Plan 11: Server log tail Summary

`databasise-rest --operator --log-file PATH` now writes engine lines, access lines and 500 tracebacks to PATH and serves the last N (1..1000, default 100) as redacted lines on `GET /log`. Without both flags the route is a 404.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| RED (CONN-14 row) | e4aa2d2 | fails by AssertionError on the help-text assert |
| 1 (tracer) GREEN | 2881382 | flag, `create_app(log_path=)`, `Databasise.log_tail`, route |
| RED (Task 2 nodes) | e1c9edd | three nodes fail by AssertionError on `log_config_for` |
| 2 GREEN | a0b69a9 | `log_config_for`, `uvicorn.run(..., log_config=)` only with the flag |

## CONN row test node ids and fail-first evidence

| Row | Intended test_ref | Fail-first |
|-----|-------------------|------------|
| CONN-14 | `databasise/tests/seam/test_console_log.py::test_log_tails_the_launcher_log_and_is_404_without_both_flags` | At the plan base, `AssertionError: assert '--log-file' in 'usage: databasise-rest [-h] ...'` on the first line of the test. `record-fail --at e4aa2d2` (the RED commit: it holds the test and the unchanged source). |

Secondary nodes (all failed before `a0b69a9` by `AssertionError: assert False where False = callable(None) where None = getattr(serve_rest, 'log_config_for', None)`, run at e1c9edd):
- `test_log_file_flag_passes_a_file_log_config_only_when_given`
- `test_log_config_captures_engine_lines_and_tracebacks` (subprocess with dictConfig)
- `test_a_real_operator_launch_writes_lines_that_get_log_returns` (installed `databasise-rest --no-clients`, tmp store root, no env file; reads `GET /info` back out of `GET /log`)

## Verification

All passed, none edited:
- 142 passed: `test_console_log`, `tests/launcher/test_launchers.py`, `test_bind_guard`, `test_console_surface`, `test_console_info`, `test_rest_cors`, `test_seam_doc_consistency`, `test_refusal_body_shape`, `test_corpus_adapter_failures`.
- 186 passed: `test_tool_growth_invariant`, `test_store_refusal_status`, `test_console_graph`, `test_refusal_status_codes`, `test_rest_corpus_endpoints`, `test_health_probe`, `test_rest_transport`, `test_leak`.
- The full offline gate was not run (orchestrator). The VALIDATION manual item (a real 500 traceback in the file) is 16-12's; the dictConfig subprocess node covers the logging config shape.

## Deviations from Plan

None - plan executed as written. The row file was committed in two parts (Task 1 node first, Task 2 nodes after) so each RED commit held only the nodes whose code followed it. Pre-existing ruff findings in `serve_rest.py` (import placement) were left.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register. `log_tail` reads only the configured path; limit is schema-bounded.

## Self-Check: PASSED

e4aa2d2, 2881382, e1c9edd, a0b69a9 are ancestors of HEAD; the created and edited files exist.
