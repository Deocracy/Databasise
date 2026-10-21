---
phase: 15-offline-tooling-packaging
plan: 04
subsystem: foreign-adapters
tags: [codebase-memory-mcp, mcp, allowlist, timeout, lazy-import]
requires: []
provides:
  - tool errors reach the caller as CbmToolCallError (TOOL-18, D-19)
  - one wall-clock scope over launch, initialize and the call
  - read-only allowlist enforced before any launch
  - section-4 tagged item kind and list derived_from
  - import-free-of-cost cbm part module (lazy admission and part)
  - RLock around import_real_mcp
actuals:
  tokens: 9500
  tasks: 3
  commits: 3
  # plan_head_before / plan_head_after below are measured from the persisted ledger
plan_head_before: 0770745a5306a8d9d198a2a9976c51cb43560c64
plan_head_after: 8c7521a64d52e0dcbd095b4fd8a846de02ea558a
tech-stack:
  added: []
  patterns:
    - "PEP 562 module __getattr__ + functools.cache for expensive module constants"
key-files:
  created:
    - databasise/tests/foreign/test_cbm_adapter.py
  modified:
    - databasise/foreign/codebase_memory_mcp_adapter.py
    - databasise/foreign/_mcp_sdk_guard.py
    - databasise/parts_core/codebase_memory_mcp.py
    - databasise/parts_core/declared_only.py
    - databasise/tests/parts_core/test_codebase_memory_mcp_admission.py
    - databasise/tests/evidence/test_falsifier4_evidence.py
key-decisions:
  - "kind is {member: payload}; derived_from is a list holding cbm-project:<project or tool>; item_kind_name(record) reads the member"
  - "The timeout bound is timeout + 4 s, not timeout + 1 s: the SDK waits about 2 s for the child on teardown (A6)"
  - "The allowlist excludes index_repository, so the two live tests and the falsifier-4 live test that used it through call_tool were adjusted"
requirements-completed: [TOOL-18]
status: complete
duration: 55min
completed: 2026-10-21
---

# Phase 15 Plan 04: codebase-memory-mcp adapter hardening Summary

The adapter refuses mutating tools by name before launching anything, bounds launch and handshake by the declared timeout, keeps a tool refusal under its own name, and emits section-4 shaped items; importing the cbm part module no longer reads the 293 MB binary.

## Commits

| Task | Commit | What |
|------|--------|------|
| 1 (tracer) | f206c89 | `_run_with_session` re-raises `CbmToolCallError` / `UntypedForeignItemError` unwrapped from anyio's exception group; row test file created |
| 2 | ad45464 | one `fail_after` scope over `stdio_client`, `ClientSession`, `initialize()` and the call; `_ALLOWED_TOOLS` + `CbmToolNotAllowedError` checked first in `call_tool`; tagged `kind`, list `derived_from`, `item_kind_name` |
| 3 | 8c7521a | lazy admission record and Part (`functools.cache` + module `__getattr__`); `_IMPORT_LOCK` RLock in `import_real_mcp` |

## Row test node ids (intended ledger test_ref) and fail-first evidence

The ledger test_ref is the file `databasise/tests/foreign/test_cbm_adapter.py`. Every node below failed by AssertionError on the unchanged source (the Task 2 and Task 3 source changes were absent when the tests first ran; for Task 3 the source was reverted from a saved patch, the nodes run, and the patch re-applied; nothing reverted was committed).

| Node | Pre-fix AssertionError |
|------|------------------------|
| `test_a_tool_error_reaches_the_caller_as_cbm_tool_call_error` | `assert 'CbmTransportError' == 'CbmToolCallError'` (the tool refusal text was wrapped in a transport failure) |
| `test_a_server_that_never_answers_initialize_times_out` | `assert 'CbmTransportError' == 'CbmToolTimeoutError'` (unbounded handshake; the fake server exits after 15 s so the test cannot hang) |
| `test_a_mutating_tool_is_refused_before_any_launch[delete_project, index_repository, manage_adr, ingest_traces]` | `assert 'CbmToolCallError' == 'CbmToolNotAllowedError'` (the fake server was launched and answered "Unknown tool") |
| `test_a_mutating_tool_is_refused_through_the_part_body` | same assertion, through `codebase_memory_mcp_body` with `adapter.DEFAULT_CBM_BINARY` pointed at the fake so the real binary never runs |
| `test_a_derived_finding_carries_a_list_derived_from_and_a_tagged_kind` | `AssertionError: item_kind_name is not defined` |
| `test_importing_the_part_module_hashes_nothing_and_runs_no_subprocess` | `AssertionError: 1 1` (one read of the binary, one `subprocess.run`) |
| `test_import_real_mcp_holds_a_lock` | `AssertionError: None` (`_IMPORT_LOCK` absent) |
| `test_the_lazy_record_and_part_are_the_same_object_on_every_access` | passes pre-fix (identity holds trivially); guards the new lazy path |
| `test_every_store_touch_the_part_records_is_declared` | passes pre-fix (the body records no touch); `mutates_store` stays declared |

Measured: the hang-server timeout test takes 4.4 s end to end for `timeout=2` (2 s timeout + about 2 s SDK teardown wait + process start), inside the `timeout + 4` bound.

## Test results

- Task 1 set (`test_cbm_adapter.py`, protected `test_mcp_sdk_guard.py`, `test_codebase_memory_mcp_admission.py`): 35 passed.
- Task 2 set (`test_cbm_adapter.py`, `tests/parts_core`, `test_falsifier4_evidence.py`, protected `tests/seam/test_refusal_reachability.py` WIRE-17): 286 passed.
- Task 3 set (`tests/foreign`, `tests/parts_core`, `tests/parts/test_admission.py`, WIRE-17, `tests/validator/test_falsifier2_evidence.py`, `tests/evidence`): 434 passed.
- Plan verification (`tests/foreign`, `tests/parts_core`, `tests/parts`, WIRE-17, `tests/evidence`): 433 passed.
- Protected sets named by the plan (RUN-04 `test_mcp_sdk_guard.py`, WIRE-17 `test_refusal_reachability.py`, every file under `tests/parts_core`): all green, none edited.
- The full offline gate (`check_offline_suite.py`) was not run by this plan; the orchestrator owns the wave run.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Live tests used `index_repository` through `call_tool`, now refused by the allowlist**
- **Found during:** Task 2 verify
- **Issue:** `test_a_timeout_raises_a_named_refusal_carrying_the_tool_name_and_ceiling` and `test_the_adapter_terminates_the_child_process_on_both_the_success_and_the_failure_path` (`test_codebase_memory_mcp_admission.py`) used `index_repository` with `timeout=0.01`; `test_the_native_leg_is_reproducible_live_get_code_snippet_still_derives_a_content_hash` (`test_falsifier4_evidence.py`) indexed the repo with it. All three run against the live binary installed on this machine.
- **Fix:** the two timeout tests use `search_graph` (allowed) and assert `tool_name == "search_graph"`; the falsifier-4 test builds its index through `adapter._run_with_session` directly, with a comment. The product allowlist is unchanged, as the plan requires. Both files are named in the plan's `files_modified` and are not ledger test_ref files.
- **Files modified:** `databasise/tests/parts_core/test_codebase_memory_mcp_admission.py`, `databasise/tests/evidence/test_falsifier4_evidence.py`
- **Commit:** ad45464

**2. [Rule 1 - Test scope] Import-cost row test counts reads of the cbm binary, not all large sha256 calls**
- **Found during:** Task 3
- **Issue:** other part modules (not this plan's) still hash large inputs at import (two sha256 calls over more than 1 MB remained after the cbm module went lazy), so a global counter could not reach zero.
- **Fix:** the subprocess script counts `Path.read_bytes` of `DEFAULT_CBM_BINARY` and any `subprocess.run`. On a machine with no binary installed the read count is vacuously zero; the `subprocess.run` count still guards the `--version` probe only when a binary exists, so the node is meaningful on this machine and weaker elsewhere.
- **Commit:** 8c7521a

### Planner-decision notes

- The row text "timeout + 1 s" does not hold under the SDK teardown wait; the bound is `timeout + 4` as the plan directs.
- `CODEBASE_MEMORY_MCP_ADMISSION` stays in `__all__` with `# noqa: F822` (served by `__getattr__`).

## Known Stubs

None.

## Threat Flags

None. T-15-12 (mutating tools), T-15-13 (hung handshake), T-15-14 (refusal disguised as transport fault) and T-15-15 (concurrent `sys.path` swap) are each mitigated and covered by a node above.

## Follow-ups

- Out-of-scope lint noted but left: `PLW1510` on `subprocess.run` in `parts_core/codebase_memory_mcp.py:76`, `v1_corpus_adapter.py`, and `test_codebase_memory_mcp_admission.py`; `RUF022` unsorted `__all__` in several files (pre-existing).
- `evidence/falsifier2.py:32` still imports `CODEBASE_MEMORY_MCP_PART` by name; the lazy `__getattr__` serves it, and 15-17 owns that file.

## Self-Check: PASSED

- `databasise/tests/foreign/test_cbm_adapter.py`, the adapter, guard, part and declared-only files exist.
- Commits f206c89, ad45464, 8c7521a are ancestors of HEAD.
- `git rev-list --count 0770745..HEAD` = 3 at the last code commit.
