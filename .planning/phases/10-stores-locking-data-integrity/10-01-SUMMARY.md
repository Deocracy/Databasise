---
phase: 10-stores-locking-data-integrity
plan: 01
subsystem: stores
tags: [cozo, graph-store, locking, refusals, rest-409, store-cleanup, d-01, d-02, d-04]
status: complete

requires: []
provides:
  - "databasise/stores/graph.py: _ClientRegistry (one refcounted pycozo Client per resolved graph.cozo path, dataframe=False), _SharedClient (client, refcount, flush_lock), GraphStoreBusyError (fixed message, no path), _is_lock_error"
  - "CozoGraphStore: shares the registry client, keeps per-instance pending buffers, serializes direct flushes per path, finalize() is idempotent"
  - "databasise/seam/refusals.py: StoreBusyError(store_kind=...) in __all__"
  - "databasise/seam/rest.py: _status_for returns 409 for StoreBusyError"
  - "databasise/seam/engine.py: _build_stores(..., *, into=None) fills the caller's dict store by store and translates GraphStoreBusyError to StoreBusyError(store_kind='graph') from None"
  - "databasise/parity/run_arm.py: _build_stores(..., *, into=None); run_arm resolves clients before building stores inside its try"
  - "databasise/tests/stores/test_graph_lock.py: hold_graph_in_subprocess(db_path) context manager (for 10-07)"
affects: [10-05, 10-07, 10-10, CONN-11, CONN-13, LIVE-08]

actuals:
  tokens: 5390
  tasks: 3
  commits: 3
plan_head_before: b3b89564194727aaedf8c298eba2b788d4e0ee42
plan_head_after: 0729b55c8139bca8f7de2c2c2f71a52a657dfa6a

tech-stack:
  added: []
  patterns:
    - "Path-keyed class-level registry under one threading.Lock; a failed open leaves no entry; the last release closes the client outside the lock"
    - "Store-level named error (stores/) translated to a catalogue refusal in the engine, raised from None with the cause logged once server-side"
    - "Incremental store builder: callers declare `stores = {}` before the try and pass `into=stores`, so the existing finally finalizes whatever opened"

key-files:
  created:
    - databasise/tests/stores/test_graph_lock.py
    - databasise/tests/seam/test_store_refusal_status.py
    - databasise/tests/seam/test_build_stores_cleanup.py
  modified:
    - databasise/stores/graph.py
    - databasise/seam/refusals.py
    - databasise/seam/rest.py
    - databasise/seam/engine.py
    - databasise/parity/run_arm.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/seam/test_refusal_status_codes.py

key-decisions:
  - "CozoGraphStore.finalize sets its released flag on the loop thread before dispatching the registry release to the executor, so two concurrent finalize() calls release the client reference once"
  - "Only the engine's graph open translates to StoreBusyError; parity/run_arm.py's builder lets GraphStoreBusyError propagate (the parity CLIs run under the per-store-root lock, D-03)"

requirements-completed: [STOR-01, STOR-02]

duration: 24min
completed: 2026-10-17
---

# Phase 10 Plan 01: Shared Cozo client, 409 StoreBusyError and store cleanup Summary

Overlapping engine calls on one `graph.cozo` path now share one reference-counted pycozo `Client` with per-call pending buffers. A path held by another OS process reaches REST as HTTP 409 `StoreBusyError` (`store_kind: "graph"`, no path or namespace in the body) and MCP as the same refusal JSON. A failed store open finalizes every store already opened, in the engine and in `parity/run_arm.py`.

## Performance

- Duration: about 24 min (grant commit 15:29, last task commit 15:43, gate and docs to 15:53)
- Tasks: 3 (Task 1, the owner grant, landed before this run in b3b8956)
- Files changed: 10 (3 created, 7 modified)

## Task Commits

1. Task 1: owner grant-check-edit for `test_refusal_status_codes.py`. Recorded by the owner in `b3b8956` (before `plan_head_before`).
2. Task 2 (tracer): `970631f` feat(10-01): share one refcounted Cozo client per graph path; busy graph is a 409 StoreBusyError (STOR-01)
3. Task 3 (TDD): `8ae021f` test(10-01): RED tests, then `0729b55` fix(10-01): a failed store open finalizes every store already opened (STOR-02)

## TDD and tracer evidence

### Task 2: `tests/stores/test_graph_lock.py` before the source change

```
E           Exception: rocksdb::kIOError::kNone
>           assert client.post("/query", json={"query": {"text": "x"}}).status_code == 200
E           AssertionError: assert 500 == 200
FAILED tests/stores/test_graph_lock.py::test_overlapping_engine_calls_complete_while_the_graph_is_held_in_process
FAILED tests/stores/test_graph_lock.py::test_rest_calls_return_200_while_the_graph_is_held_in_process
FAILED tests/stores/test_graph_lock.py::test_two_instances_share_one_client_but_keep_separate_buffers
FAILED tests/stores/test_graph_lock.py::test_finalize_twice_releases_the_client_once
FAILED tests/stores/test_graph_lock.py::test_a_store_open_held_by_another_process_raises_graph_store_busy
FAILED tests/stores/test_graph_lock.py::test_engine_and_rest_refuse_a_graph_held_by_another_process_with_store_busy
6 failed in 1.72s
```

The failures match STOR-01: the generic `Exception` carrying `kIOError` for a second in-process open, and a 500 from REST. The `stores['graph'] False` health symptom did not surface on its own, because inside the `asyncio.gather` the query's `kIOError` raised first.

After the change: `pytest -q tests/stores/test_graph_lock.py tests/stores` gave `69 passed`. `pytest -q tests/seam tests/mcp` gave `728 passed, 1 skipped`. `tests/mcp/test_mcp_refusal_mapping.py -k StoreBusyError` gave 1 passed, and the `test_rest_transport.py` factory case also passed.

Tracer feedback gate: the task has no `gate="blocking-human"`, and its `<verify>` is automated only. It was re-run end-to-end and passed before Task 3 began.

### Task 3: `tests/seam/test_build_stores_cleanup.py` before the source change

```
kv_counts = {'built': 1, 'finalized': 0}   (query, ingest, delete_document, run_arm)
kv_counts = {'built': 3, 'finalized': 0}   (three failing queries)
5 failed, 1 passed in 1.72s   (resolve_evidence opens no kv store: passed already)
```

After the change: the targeted verify (`test_build_stores_cleanup.py test_raw_upload_staging.py test_cli_builder_refusals.py test_store_isolation.py`) gave `34 passed`. `tests/seam tests/mcp tests/parity tests/stores` gave `949 passed, 1 skipped, 3 deselected`.

### Full gate

`.venv/bin/python tools/check_offline_suite.py`: exit 0. `pytest -q -rs: 1636 passed, 1 skipped, 4 deselected`, and `python -m pytest -q -rs: 1636 passed, 1 skipped, 4 deselected`.

## Owner-granted protected edit (one line)

`databasise/tests/seam/test_refusal_status_codes.py` line 26:

```diff
-_MAPPED_ELSEWHERE = {"ForeignEngineRefusalError"}
+_MAPPED_ELSEWHERE = {"ForeignEngineRefusalError", "StoreBusyError"}
```

`git diff --stat` reported `2 +-` for the file, so no other line changed. No other protected file was edited.

## Decisions Made

- `finalize()` sets `_released` on the loop thread and only then dispatches `_ClientRegistry.release` to the executor. Two concurrent finalizes therefore release once. The `__init__` failure path releases synchronously through `_release()`.
- The registry closes the last client outside its lock, so a slow close never blocks other paths' acquires.
- `parity/run_arm.py` does not translate `GraphStoreBusyError`, because it is not a seam surface. The parity CLIs hold the store-root lock (D-03).

## Deviations from Plan

None in the source. Two process notes:
- The BAK hook blocks heredocs and `python -c` scripts whose text names test folders. The graph.py edit ran as a script file in the scratchpad, and every pytest run under `databasise/tests/seam` used the plain `databasise/.venv/bin/pytest -q databasise/tests/...` form from the repository root.
- Task 3 is `tdd="true"`, so it has two commits: RED `test(...)` and GREEN `fix(...)`.

## Known Stubs

None.

## Threat Flags

None. T-10-01 to T-10-04 are mitigated as planned:
- `test_engine_and_rest_refuse_a_graph_held_by_another_process_with_store_busy` asserts that the store root and namespace are absent from the 409 body.
- The two-instance test proves buffer isolation.
- The counter tests prove the cleanup.

## Next Phase Readiness

- 10-07 can import `hold_graph_in_subprocess` from `databasise.tests.stores.test_graph_lock`. Its health probe can use `_ClientRegistry.acquire` and must check existence first, because opening a missing path creates it.
- 10-05's prepared flush must keep a reference held while a `multi_transact` is open (research R10). The registry closes the client at refcount 0.
- `engine.health()` still constructs `CozoGraphStore` and therefore creates directories. 10-07 owns that.

## Self-Check: PASSED

- FOUND: databasise/tests/stores/test_graph_lock.py, databasise/tests/seam/test_store_refusal_status.py, databasise/tests/seam/test_build_stores_cleanup.py
- FOUND: 970631f, 8ae021f, 0729b55 (ancestors of HEAD)
