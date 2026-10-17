---
phase: 10-stores-locking-data-integrity
plan: 04
subsystem: seam-engine
tags: [ingest-abort, drop-pending, store-fault, run-incomplete, refusals, rest-502, d-06, d-09, d-13]
status: complete

requires: ["10-01"]
provides:
  - "databasise/seam/engine.py: _drop_pending(stores) drops every store's pending writes, logging and continuing past one store's failure"
  - "databasise/seam/engine.py: _is_store_fault(exc): sqlite3.Error, or an exception type whose module starts with databasise.stores or pycozo"
  - "databasise/seam/engine.py: _node_result_or_refuse refuses on a cycle (RunIncomplete), on any node's recorded exception (result node first, then the first recorded; StoreFault for a store error), on partial/stop_reason (RunIncomplete), and on a missing result"
  - "Databasise.ingest: the refusal decision runs inside the try right after run_wiring; a refusal drops every store before propagating; the flush runs only on success"
  - "failure_class values StoreFault and RunIncomplete (REST 502)"
  - "databasise/tests/seam/test_ingest_abort.py: _assert_nothing_committed, _refused_ingest, _fake_run_wiring helpers (reusable by 10-05/10-10)"
affects: [10-05, 10-06, 10-08, 10-10, GUI-06, HIPP-04]

actuals:
  tokens: 5355
  tasks: 2
  commits: 2
plan_head_before: 7d513cd73601e3b7f5534957bfc452f21f43e3c7
plan_head_after: 673699c206a84bf5326c98ddccff9ca76a94f925

tech-stack:
  added: []
  patterns:
    - "Refuse-then-drop: the shared refusal helper runs before the flush, and its ForeignEngineRefusalError triggers drop_pending_index_ops on every store before re-raise"
    - "Store-fault classification by the exception type's module, so stores/ needs no shared exception base and never imports seam/"

key-files:
  created:
    - databasise/tests/seam/test_ingest_abort.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/refusals.py
    - databasise/seam/rest.py
    - databasise/parts_core/hipporag/graph_augment_persist.py

key-decisions:
  - "A cyclic wiring's run_wiring result ({'cycle': [...]}) refuses as RunIncomplete, checked first"
  - "When several nodes fail, the result node's exception is reported, else the first recorded (dict order); HIPP-04 adds the full set"
  - "ForeignEngineRefusalError message reworded to \"ForeignEngineRefusalError: operation 'x' failed (<class>)\"; the pin check found no test pinning the old text"
  - "_foreign_fault log line reads 'engine fault: operation=%s failure_class=%s'; the operation=/failure_class= substrings the protected test asserts are unchanged"

requirements-completed: [STOR-06]

duration: 22min
completed: 2026-10-17
---

# Phase 10 Plan 04: Failed ingest commits nothing; StoreFault and RunIncomplete Summary

A HippoRAG ingest whose run records any node exception, or that stopped early, now drops every store's staged kv, vector and graph writes and raises `ForeignEngineRefusalError`. A store error inside a node is reported as `failure_class="StoreFault"`, an early stop as `"RunIncomplete"`, both REST 502. `graph-augment-persist` no longer commits its own graph store, so the engine is the only committer.

STOR-06 is the first half here: the success path still flushes store by store. 10-05 replaces it with prepare-all/commit-all (D-07).

## Performance

- Duration: about 22 min
- Tasks: 2
- Files changed: 5 (1 created, 4 modified)

## Task Commits

1. Task 1 (tracer): `feadf3e` fix(10-04): a refused HippoRAG ingest drops every store's staged writes (STOR-06)
2. Task 2 (TDD): `673699c` feat(10-04): StoreFault and RunIncomplete failure classes; fault wording no longer says v1 (STOR-06)

## TDD and tracer evidence

### Task 1: `tests/seam/test_ingest_abort.py` against the unchanged source

`CozoGraphStore.upsert_edge` patched to raise `RuntimeError('boom')`; the refused ingest had already committed the chunk-embed and entity-fact-embed writes:

```
E           assert False          # await SqliteKVStore('hipporag-text-chunks', ...).is_empty()
E       AssertionError: assert [EvidenceRef(...0, tier=None)] == []
E         Left contains one more item: EvidenceRef(ref='bb1f5e8e...', namespace='hipporag-chunks', kind='text_chunk', score=1.0, tier=None)
FAILED tests/seam/test_ingest_abort.py::test_a_failing_graph_augment_persist_commits_no_kv_vector_or_graph_write
FAILED tests/seam/test_ingest_abort.py::test_a_query_after_a_refused_ingest_returns_no_evidence_from_it
2 failed, 1 passed in 1.55s
```

After the change: `tests/seam/test_ingest_abort.py tests/seam/test_hipporag_write_path.py tests/parts_core/hipporag`: 66 passed. `tests/seam tests/mcp tests/parity`: 883 passed, 1 skipped, 3 deselected. Tracer gate: the automated verify re-ran green before Task 2 started.

### Task 2: the new cases against the Task 1 source

```
E       AssertionError: assert 'UnclassifiedEngineFailure' == 'StoreFault'
FAILED tests/seam/test_ingest_abort.py::test_a_store_error_inside_a_node_is_a_store_fault
1 failed, 8 passed in 2.84s
```

Current classes before the change: `sqlite3.OperationalError` -> `UnclassifiedEngineFailure`; `RuntimeError` -> `UnclassifiedEngineFailure`. The non-result-node and early-stop cases already passed, because Task 1 extended `_node_result_or_refuse` as the plan's Task 1 action 4 required. The 502 mapping already held (every class outside `_ENGINE_UNAVAILABLE` is 502); that test is a guard.

After the change: `tests/seam/test_ingest_abort.py tests/seam/test_foreign_engine_refusal.py tests/seam/test_read_route_fault_breadth.py tests/seam/test_error_message_scrub.py`: 56 passed. `tests/seam tests/mcp tests/parity tests/parts_core`: 1050 passed, 1 skipped, 3 deselected.

## Pin check (W5) and message text

Each command printed nothing (no hit):

```
grep -rn "the foreign engine failed" databasise/tests
grep -rn "foreign engine fault" databasise/tests
grep -rn "the v1 engine run failed" databasise/tests
```

A wider search (`failed operation`, `Machine fault`, `foreign engine` over `databasise/` and `docs/`) found no test or doc pinning the message or the 502 description. So the reword branch applied:

- Message before: `ForeignEngineRefusalError: the foreign engine failed operation 'ingest' (StoreFault)`
- Message after: `ForeignEngineRefusalError: operation 'ingest' failed (StoreFault)`
- Log line before: `foreign engine fault: operation=%s failure_class=%s`; after: `engine fault: operation=%s failure_class=%s`
- REST 502 description before: `Machine fault: the v1 engine run failed or returned malformed output (ForeignEngineRefusalError)`; after: `Machine fault: an engine run, a store or the v1 engine failed, stopped early or returned malformed output (ForeignEngineRefusalError)`

The `str(refusal)` case (no `v1`, no `foreign engine`) is included in `test_a_store_error_inside_a_node_is_a_store_fault`. No protected test file was edited.

## Acceptance greps

- `grep -n "index_done_callback" databasise/parts_core/hipporag/graph_augment_persist.py`: no lines (the docstring says "lifecycle method", not the method name).
- `grep -n "_drop_pending(stores)" databasise/seam/engine.py`: line 916.
- `grep -n 'failure_class="StoreFault"' databasise/seam/engine.py`: line 492. `grep -n 'failure_class="RunIncomplete"'`: lines 484 and 498.
- `grep -n "def _is_store_fault" databasise/seam/engine.py`: line 262.

## Full gate

`cd databasise && .venv/bin/python tools/check_offline_suite.py`: `pytest -q -rs: 1645 passed, 1 skipped, 4 deselected`; `python -m pytest -q -rs: 1645 passed, 1 skipped, 4 deselected`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Acceptance grep literal for StoreFault**
- **Found during:** Task 2 acceptance check
- **Issue:** The first version selected the class with a conditional expression (`failure_class = "StoreFault" if ... else None`), which the plan's literal grep `failure_class="StoreFault"` and the key_links pattern do not match.
- **Fix:** Two explicit raises, one with `failure_class="StoreFault"`. Same behaviour. Folded into the Task 2 commit with `git commit --amend` before any later commit. The focused tests (81 passed) were re-run after it; the full gate ran just before this equivalent restructure.
- **Files modified:** databasise/seam/engine.py
- **Commit:** 673699c

Otherwise the plan executed as written.

## Notes for later plans

- `delete_document` now also refuses on any node exception, `partial`, `stop_reason` and `cycle` (shared helper), but it still finalizes its stores before the helper runs and has no flush or drop. 10-10 adds those (D-08).
- `degraded` alone does not refuse, per the plan's flagged assumption.
- `_drop_pending` logs at ERROR only when a store's drop raises, so the protected `test_the_full_cause_is_logged_once_server_side` (exactly one ERROR record) is unaffected.

## Self-Check: PASSED

- FOUND: databasise/tests/seam/test_ingest_abort.py
- FOUND: feadf3e, 673699c (both ancestors of HEAD)
