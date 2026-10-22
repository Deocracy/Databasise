---
phase: 16-gui-connectors
plan: 01
subsystem: api
tags: [fastapi, operator-surface, rest, launcher, ast-test]
requires: []
provides:
  - "create_app(operator=True) and databasise-rest --operator mount seam/operator_rest.py"
  - "GET /info backed by Databasise.info() and the shared _client_presence helper"
  - "AST thin-adapter rule (with Ledger mutant) and call ban over both REST modules"
affects: [16-02, 16-03, 16-04, 16-05, 16-06, 16-07, 16-08, 16-09, 16-10, 16-11, 16-12]
status: complete
commits: 3
plan_head_before: 962060f96020e82d82596b345915f24a0137d6e4
plan_head_after: f0979a1890767ea99d894875bc942b098997fb25
actuals:
  tokens: 5200
  tasks: 2
  commits: 3
tech-stack:
  added: []
  patterns:
    - "flag-gated lazy include of operator routes; route body is one awaited engine call"
key-files:
  created:
    - databasise/seam/operator_rest.py
    - databasise/tests/seam/test_console_surface.py
    - databasise/tests/seam/test_console_info.py
  modified:
    - databasise/seam/rest.py
    - databasise/seam/engine.py
    - databasise/launcher/serve_rest.py
    - databasise/tests/seam/test_rest_transport.py
key-decisions:
  - "--operator refusal is a parser.error placed after the --workers check and before check_engine_arguments, so it fires before the store lock and even with --allow-remote-unauthenticated"
  - "launcher reads the flag with getattr(args, 'operator', False) in build_app so hand-built Namespaces in protected tests keep working"
requirements-completed: [CONN-04]
---

# Phase 16 Plan 01: Operator surface tracer and GET /info Summary

`create_app(operator=True)` and `databasise-rest --operator` now mount a new `seam/operator_rest.py`, whose first route is GET /info, served by `Databasise.info()` (version, workspace, presence-only client flags); a default app mounts none of it.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 (RED) | 079b4ba | `test_console_surface.py` and `test_console_info.py` row nodes, committed failing |
| 1 (GREEN) | cd203ac | `operator=` kwarg, `operator_rest.py`, `_client_presence`, `Databasise.info()` |
| 2 | f0979a1 | `--operator` flag, loopback-only parser error, launcher nodes, call-ban parametrized over both modules |

Tracer gate: the slice was re-verified end to end by the verify set (150 passed after Task 1) before Task 2 expanded it.

## CONN row test node ids and fail-first evidence

| Row | Intended test_ref | Fail-first |
|-----|-------------------|------------|
| CONN-04 | `databasise/tests/seam/test_console_info.py::test_info_reports_version_workspace_and_client_presence` | At 079b4ba (tests present, source unchanged): `AssertionError: create_app has no operator flag (CONN-01)` from the `inspect.signature` assert. Use `record-fail --at 079b4ba`. |
| CONN-01 | `databasise/tests/seam/test_console_surface.py::test_operator_routes_are_thin_adapters_and_absent_without_the_flag` | At 079b4ba: `AssertionError: databasise/seam/operator_rest.py does not exist (CONN-01)` / `assert None is not None` from the `find_spec` assert. The file does not exist at the phase base d608162, so 079b4ba is the earliest commit where the node exists and fails. |

Supporting nodes in `test_console_surface.py` (CONN-01 partial): `test_the_launcher_operator_flag_mounts_the_routes_only_when_given` and `test_operator_with_a_remote_host_is_refused_before_the_store_lock`. Both failed by `AssertionError: databasise-rest has no --operator flag (CONN-01)` before the launcher change (run on the uncommitted test file, since they were added in the Task 2 commit f0979a1).

## Test results

- Task 1 verify set (9 files): 150 passed.
- Task 2 verify set (9 files, includes protected `tests/launcher/test_launchers.py`, `test_trace_resolve_strict_flag.py`, `test_rest_corpus_endpoints.py`, `test_run10_upload_poll_delete_counts.py`, `test_upload_selector_field.py`, `test_ingest_input_refusals.py`): 161 passed.
- Phase guard suite from the plan's `<verification>` (17 files): 281 passed (276 baseline + 1 extra call-ban case + 4 new nodes).
- Both parametrized call-ban cases (`databasise.seam.rest`, `databasise.seam.operator_rest`) pass.
- No protected test failed; none was edited.
- Full offline gate (`check_offline_suite.py`) not run in this plan.

## Deviations from Plan

- Split Task 1 into a RED test commit (079b4ba) and a GREEN code commit (cd203ac) so the row nodes have a committed failing state for `record-fail --at`. No scope change.
- The two launcher nodes were appended to `test_console_surface.py` with a shell append rather than the Write tool. The content is the same as planned.

## Notes for later plans

- `ruff check` reports four pre-existing findings in `seam/rest.py` (B008 x3, RUF022); none come from this plan and they were left alone.
- `info()` carries no `write_in_flight` or `graph_busy` yet; 16-11 adds them to the Phase 16 block in `engine.py`.
- 16-02 imports `_REFUSAL_FACTORIES` from `test_rest_transport.py`; this plan only added an `importlib` import and the parametrization there.

## Known Stubs

None.

## Threat Flags

None beyond the plan's threat model: T-16-01 (presence booleans only, asserted by the row test), T-16-02 (parser error off loopback, tested), T-16-03 (AST rule plus call ban, tested).

## Self-Check: PASSED

Files found: `databasise/seam/operator_rest.py`, `databasise/tests/seam/test_console_surface.py`, `databasise/tests/seam/test_console_info.py`. Commits 079b4ba, cd203ac, f0979a1 are ancestors of HEAD.
