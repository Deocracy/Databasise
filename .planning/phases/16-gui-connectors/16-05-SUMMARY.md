---
phase: 16-gui-connectors
plan: 05
subsystem: api
tags: [fastapi, operator-surface, traces, read-only]
requires: [16-04]
provides:
  - "TraceStore.list_page(limit, offset): newest-first page plus total"
  - "Databasise.list_traces(page) and GET /traces"
  - "_scrub_reasons(record, public): the one reason scrub for /trace/resolve and /traces"
affects: [16-12]
status: complete
commits: 4
plan_head_before: 498d988c0f123f34bd14421cf5ec590659f5db52
plan_head_after: e12ba65198006d951a43ea8ed74df39b217d6bf5
actuals:
  tokens: 4000
  tasks: 2
  commits: 4
tech-stack:
  added: []
  patterns:
    - "reason fields are scrubbed through one module-level helper shared by every trace-reading method"
key-files:
  created:
    - databasise/tests/seam/test_console_traces.py
  modified:
    - databasise/seam/trace_store.py
    - databasise/seam/engine.py
    - databasise/seam/operator_rest.py
key-decisions:
  - "list_traces reads trace.db on the loop thread, like resolve_trace, with sqlite3.Error mapped once to a StoreFault"
requirements-completed: [CONN-08]
---

# Phase 16 Plan 05: Operator trace list Summary

`GET /traces?limit&offset` returns recent traces newest first as `{items, total, next_offset}`, with each item holding only `trace_reference`, `created_at`, `partial`, `degraded` and a `stop_reason` scrubbed by the same `_scrub_reasons` helper that `/trace/resolve` now calls.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 (RED) | 1d3792f | CONN-08 row test, failing (route absent) |
| 1 (GREEN) | f39b225 | `TraceStore.list_page`, `Databasise.list_traces`, GET /traces |
| 2 (RED) | 2064e63 | scrub row test, failing (raw stop_reason returned) |
| 2 (GREEN) | e12ba65 | `_scrub_reasons` extracted; `resolve_trace` and `list_traces` both call it |

Tracer gate: the Task 1 verify set (5 files, 29 passed) was clean before Task 2.

## CONN row test node ids and fail-first evidence

| Row | Intended test_ref | Fail-first |
|-----|-------------------|------------|
| CONN-08 | `databasise/tests/seam/test_console_traces.py::test_traces_list_newest_first_with_paging` | At 1d3792f (test present, source unchanged): `AssertionError: (404, '{"detail":"Not Found"}')` / `assert 404 == 200` at the first GET /traces, after three POST /query calls succeeded. Use `record-fail --at 1d3792f`. |
| (supporting) | `databasise/tests/seam/test_console_traces.py::test_trace_list_scrubs_stop_reason_like_trace_resolve` | At 2064e63 (list_traces returned the raw text): `AssertionError: assert 'chunk-vector' not in "node 'chunk...ream refused"`. |

The test file does not exist at the phase base, so 1d3792f is the earliest commit where the CONN-08 node exists and fails.

## Test results

- Task 1 verify set: 29 passed. Task 2 verify set (`test_console_traces.py`, `test_stop_reason_leak.py`, `test_trace_resolve_strict_flag.py`, `test_leak.py`): 44 passed.
- Phase guard suite from 16-01's block, plus `test_console_traces.py`, `test_console_ledger.py`, `test_console_wirings.py`, `test_stop_reason_leak.py`, `test_trace_resolve_strict_flag.py`, `test_docstring_currency.py`: 329 passed.
- No protected test failed; none was edited. `ruff` is clean on the new code; `trace_store.py` (import order) and `engine.py` (5 findings) have pre-existing findings outside this plan's lines.
- Full offline gate not run in this plan.

## Deviations from Plan

- Each task was split into a RED test commit and a GREEN code commit so the row nodes have committed failing states for `record-fail --at`. No scope change.
- [Rule 1 - Bug in plan text] The plan says each POST /query envelope carries `trace_reference`; the envelope field is `trace_token`, so the row test reads `trace_token` from envelopes and `trace_reference` from the list items.
- The plan's commit trailer names Claude Opus 5.5; the shared rules specify the executing model, so commits end with `Co-Authored-By: Claude Sonnet 5.5`.

## Known Stubs

None.

## Threat Flags

None. T-16-12 is covered by the shared `_scrub_reasons` helper and the equality test against `/trace/resolve`; T-16-11 and T-16-13 are accepted per the plan (the `shortcut:` comment sits above the unindexed sort).

## Self-Check: PASSED

Files found: `databasise/tests/seam/test_console_traces.py`, `databasise/seam/trace_store.py`, `databasise/seam/engine.py`, `databasise/seam/operator_rest.py`. Commits 1d3792f, f39b225, 2064e63, e12ba65 are ancestors of HEAD.
