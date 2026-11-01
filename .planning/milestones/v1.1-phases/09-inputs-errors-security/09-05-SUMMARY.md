---
phase: 09-inputs-errors-security
plan: 05
subsystem: api
tags: [refusals, foreign-engine, rest, openapi, fault-status, seam]
status: complete

requires:
  - phase: 09-04
    provides: call_tool refusal mapping (MCP delivers any refusal as bare JSON)
provides:
  - "ForeignEngineRefusalError as the one machine-fault type: operation, allow-listed failure_class, private _cause, read-only cause property"
  - "_foreign_fault: the single place a fault is built and logged (once, with exc_info)"
  - "_corpus_op_or_refuse: read-route wrapper around run_corpus_op for GET /corpus, /corpus/counts, /jobs/{id}"
  - "rest._status_for: 502 (run failed / malformed output) and 503 (v1 unavailable); RefusalBody and _FAULT_RESPONSES in OpenAPI"
affects: [09-06]

commits: 2
plan_head_before: 974c8bb051afdbadf73b58c13ee7596073647770
plan_head_after: 11c9ff1c0db446b8f7f0e9e378d0c146805d3022

actuals:
  tokens: 11000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "private cause behind a read-only property; refusal_body skips leading-underscore attributes"
    - "fault built and logged in one helper so each fault produces exactly one ERROR record"

key-files:
  created:
    - databasise/tests/seam/test_foreign_engine_refusal.py
    - databasise/tests/seam/test_corpus_adapter_failures.py
  modified:
    - databasise/seam/refusals.py
    - databasise/seam/engine.py
    - databasise/seam/rest.py

key-decisions:
  - "D-04: a v1 engine failure is a machine fault: 502 when the run fails or returns malformed output, 503 when v1 is unavailable (MissingV1InterpreterError, CorpusOpTimeoutError); never 4xx"
  - "The cause is never on the wire: message names only operation and failure_class; the cause is logged server-side once with exc_info"
  - "failure_class tokens MalformedDriverOutput and UnclassifiedEngineFailure are executor-chosen (flagged assumption A4)"
  - "Only the four adapter exception types and result-shape parse failures become read-route faults; any other exception stays a visible 500"

requirements-completed: [SEAM-05, SEAM-06]

coverage:
  - id: D1
    description: "A v1 subprocess failure on DELETE /documents and POST /documents is 502/503 with operation, failure_class, a body under 1,024 bytes and no '/home/', 'Traceback' or env-var name; the same over MCP"
    requirement: "SEAM-05"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_foreign_engine_refusal.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "The full cause is logged once per fault (caplog: one ERROR record, exc_info is the original exception) and stays readable in-process via .cause while absent from vars(exc)"
    requirement: "SEAM-05"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_foreign_engine_refusal.py::test_the_full_cause_is_logged_once_server_side"
        status: pass
    human_judgment: false
  - id: D3
    description: "GET /corpus, /corpus/counts and /jobs/{id} return the structured 503/502/503/502 fault for missing interpreter, subprocess failure, timeout and malformed driver output; /health stays 200 degraded; wrong-shape results are MalformedDriverOutput while UnknownJobError stays 404"
    requirement: "SEAM-06"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_corpus_adapter_failures.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "app.openapi() declares 502 and 503 on the six fault-bearing routes"
    requirement: "SEAM-06"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_corpus_adapter_failures.py::test_openapi_declares_the_machine_fault_responses"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-17
---

# Phase 9 Plan 05: Foreign engine fault Summary

**A v1 engine failure on any route is now one structured ForeignEngineRefusalError fault (502 run failed or malformed output, 503 v1 unavailable) with an allow-listed failure_class, no stderr on the wire, and the full cause logged server-side once.**

## Performance

- **Duration:** about 25 min
- **Tasks:** 2
- **Files modified:** 5 (3 source, 2 new test files)

## Accomplishments

- `ForeignEngineRefusalError(operation, cause, failure_class=None)`: public `operation` and `failure_class`, private `_cause`, read-only `cause` property. The message is built from operation and failure class only. `refusal_body` lost its exception-stringifying branch because no public exception attribute remains.
- `_foreign_fault` in the engine builds and logs each fault once (`logger.error(..., exc_info=cause)`); both `_node_result_or_refuse` branches use it, so delete and ingest share it.
- `_corpus_op_or_refuse` wraps `run_corpus_op` for the three read routes (looked up as a module global at call time, so the protected corpus-endpoint test's monkeypatch still works); result-shape parse failures are `MalformedDriverOutput`. `UnknownJobError` is raised outside every parse wrapper, so a zero-total job is still 404.
- `rest._status_for` maps faults by `failure_class` (`_ENGINE_UNAVAILABLE` gives 503, else 502). `RefusalBody` and `_FAULT_RESPONSES` declare 502/503 on `GET /corpus`, `GET /corpus/counts`, `GET /jobs/{job_id}`, `POST /documents`, `POST /documents/upload` and `DELETE /documents/{document_id}`.

## Red and green evidence

- Task 1 before the change: `DELETE /documents/deadbeef` with a faulting `full_delete.run_corpus_op` returned `422` and the stderr text (Traceback, path, `LIGHTRAG_API_KEY`) in the body twice (`assert 422 == 502`); 9 new tests failed. After: `9 passed`.
- Task 2 before the change: the three read routes returned a text/plain `500 Internal Server Error` (`assert 500 == 502`) and OpenAPI lacked 502/503; 21 of 27 new tests failed. After: all 27 pass.
- Plan verification `cd databasise && .venv/bin/pytest -q tests/seam tests/mcp tests/parts_core`: `705 passed, 1 skipped`, 0 failed.

## Task Commits

1. **Task 1: tracer, a v1 subprocess failure on delete/ingest is a clean 5xx fault** - `071fe58` (feat)
2. **Task 2: read routes report adapter failures as the structured fault; OpenAPI declares it** - `11c9ff1` (feat)

## Files Created/Modified

- `databasise/seam/refusals.py` - reworked `ForeignEngineRefusalError`, `_FOREIGN_FAILURE_CLASSES`
- `databasise/seam/engine.py` - `logger`, `_foreign_fault`, `_corpus_op_or_refuse`, `_MALFORMED_RESULT`, three read methods
- `databasise/seam/rest.py` - `_ENGINE_UNAVAILABLE`, fault rows in `_status_for`, `RefusalBody`, `_FAULT_RESPONSES`
- `databasise/tests/seam/test_foreign_engine_refusal.py` - SEAM-05 tests
- `databasise/tests/seam/test_corpus_adapter_failures.py` - SEAM-06 tests

## Decisions Made

See `key-decisions`. No existing test needed editing: every reader of `.cause` still passes, and `test_rest_transport.py`'s generic body check already skips leading-underscore keys (its `BaseException` branch is now unreachable but harmless).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

One Bash call carrying a multi-file Python edit script was rejected by the BAK check-edit guard (it named a protected test path in its message although the script did not touch it); nothing had been applied. The edits were redone with the Edit tool.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

09-06 can rely on the fault being a distinct, non-4xx status with a documented body. The hosted-authentication decision is untouched: no flag exposes the cause.

## Self-Check: PASSED

- Files exist: refusals.py, engine.py, rest.py, both new test files.
- Commits `071fe58` and `11c9ff1` are ancestors of HEAD.
- Acceptance: `self._cause = cause` 1 line, `def cause` 1 line, `def _foreign_fault` 1 line, `_foreign_fault(` count 8, `_ENGINE_UNAVAILABLE` 2 lines, `await _corpus_op_or_refuse(` count 3, `responses=_FAULT_RESPONSES` count 6.

---
*Phase: 09-inputs-errors-security*
*Completed: 2026-10-17*
