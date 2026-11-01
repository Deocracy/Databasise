---
phase: 10-stores-locking-data-integrity
plan: 05
subsystem: stores-and-seam-engine
tags: [prepared-commit, two-phase, flush-lock, faiss-rebase, multi-transact, d-07, stor-06]
status: complete

requires: ["10-04"]
provides:
  - "databasise/stores/base.py: StorageNameSpace.prepare (no-op), commit_prepared (index_done_callback), abort_prepared (drop_pending_index_ops) defaults"
  - "SqliteKVStore.prepare: BEGIN IMMEDIATE plus the pending DML, uncommitted; commit_prepared commits; abort_prepared rolls back; index_done_callback = prepare + commit_prepared"
  - "FaissVectorStore: _committed_signature, _read_committed, _loaded_signature, _write_staged, _commit_staged, _prepared; prepare rebases on the on-disk pair when another writer committed"
  - "MultiNamespaceVectorStore: prepare/commit_prepared/abort_prepared fan out to every selected child"
  - "CozoGraphStore: _snapshot, _stage(snapshot), _commit_or_abort, _prepared_mt; finalize aborts an open prepared transaction before releasing the shared client"
  - "databasise/seam/engine.py: _FLUSH_LOCKS (WeakKeyDictionary loop -> {resolved root: asyncio.Lock}), _flush_lock(store_root), _abort_prepared(stores), _commit_all(stores, operation, store_root)"
  - "databasise/tests/stores/test_prepared_commit.py (new, 13 cases)"
affects: [10-10, GUI-06]

actuals:
  tokens: 9811
  tasks: 2
  commits: 2
plan_head_before: 69cab8b053f8888bc0c45d8540b98c8e7abd1863
plan_head_after: fd579143ad9bdc3b3ea447f0642495998bafe428

tech-stack:
  added: []
  patterns:
    - "Prepare-all, then commit-all under one asyncio.Lock per (event loop, resolved store root), taken before any prepare DML"
    - "Stat-signature rebase: a per-call Faiss instance compares (st_ino, st_mtime_ns, st_size) of the committed pair with what it loaded and reloads before staging"

key-files:
  created:
    - databasise/tests/stores/test_prepared_commit.py
  modified:
    - databasise/stores/base.py
    - databasise/stores/kv.py
    - databasise/stores/vector.py
    - databasise/stores/graph.py
    - databasise/seam/engine.py
    - databasise/tests/seam/test_ingest_abort.py

key-decisions:
  - "_commit_all catches BaseException: a cancelled run still aborts every store (releasing the sqlite write lock and the Cozo transaction); only Exception is wrapped as StoreFault, cancellation re-raises unchanged"
  - "A commit failure aborts only the stores not yet committed and raises StoreFault; earlier commits stay (the documented D-07 residual window)"
  - "drop_pending_index_ops on the vector and graph stores now calls abort_prepared, so the 10-04 refusal path also removes a staged .tmp pair or open transaction"
  - "SqliteKVStore commits and rolls back unconditionally (no in_transaction check), because test_kv.py's failing-connection wrapper exposes only execute/commit/rollback/close"
  - "delete_by_ids refreshes _loaded_signature after its immediate persist, so the next prepare does not reload its own write"

requirements-completed: [STOR-06]

duration: 35min
completed: 2026-10-17
---

# Phase 10 Plan 05: Prepare-all, then commit-all Summary

A successful ingest now commits through prepare-all, then commit-all (D-07). The kv store stages its DML in an uncommitted `BEGIN IMMEDIATE` transaction, the vector store writes only its `.tmp` pair, and the graph store stages a `multi_transact`. No store commits until all three have prepared. A prepare failure aborts all three and raises `ForeignEngineRefusalError(failure_class="StoreFault")`. One `asyncio.Lock` per (event loop, store root) covers the window from the first prepare to the last commit. The vector store rebases on the on-disk committed state, so two overlapping ingests on one root both keep all their vectors.

This completes STOR-06: 10-04 delivered "a failed run commits nothing" and this plan delivers "a successful one commits everything".

## Performance

- Duration: about 35 min
- Tasks: 2
- Files changed: 7 (1 created, 6 modified)

## Task Commits

1. Task 1 (tracer): `3f08cba` feat(10-05): the engine commits an ingest through prepare-all then commit-all under one lock (STOR-06)
2. Task 2 (TDD): `fd57914` feat(10-05): the vector and graph stores stage for real; overlapping writers keep each other's vectors (STOR-06)

## TDD and tracer evidence

### Task 1 before the change (new tests against HEAD 69cab8b)

```
E           AttributeError: 'SqliteKVStore' object has no attribute 'prepare'
E       AttributeError: 'SqliteKVStore' object has no attribute 'prepare'
E               AttributeError: type object 'SqliteKVStore' has no attribute 'prepare'
E       AttributeError: <class 'databasise.stores.graph.CozoGraphStore'> has no attribute 'prepare'
4 failed, 10 passed in 3.24s
```

### Task 1 after

```
tests/stores/test_prepared_commit.py tests/seam/test_ingest_abort.py tests/stores/test_kv.py: 21 passed in 4.43s
tests/stores tests/seam tests/parity: 872 passed, 1 skipped, 3 deselected in 121.21s
```

Tracer gate: auto mode. The `<verify>` commands were re-run end to end and passed before expansion.

### Task 2 before the change (new tests against 3f08cba, where vector and graph use the default prepare)

The rebase case loses the first writer's vector, and the concurrent-ingest case loses one document's chunk:

```
E       AssertionError: assert None == {'id': 'a'}
E        +  where None = get_by_id('a')
E        +    where get_by_id = FaissVectorStore(namespace='vec', workspace='ws').get_by_id
E       AssertionError: assert ({'2f209ddcf1...593dfd60bc9'}) == ({'2f209ddcf1...593dfd60bc9'})
E         At index 0 diff: {'2f209ddcf16fa87feb8a04d3421144fa2aff85524bbf4544823330771ec1107f'} != {'2f209ddcf16fa87feb8a04d3421144fa2aff85524bbf4544823330771ec1107f', 'f6daedefa0053a9254f59542cd81ada70d09aeab2ff9c3fc7c972dfcf035d07c'}
FAILED tests/stores/test_prepared_commit.py::test_vector_prepare_writes_only_the_tmp_pair_on_a_fresh_namespace
FAILED tests/stores/test_prepared_commit.py::test_two_vector_instances_opened_before_either_flushes_keep_both_ids
FAILED tests/stores/test_prepared_commit.py::test_multi_namespace_vector_lifecycle_fans_out_to_every_selected_child
FAILED tests/seam/test_ingest_abort.py::test_two_concurrent_hipporag_ingests_on_one_root_both_commit_in_full
4 failed, 19 passed in 5.34s
```

### Task 2 after

```
tests/stores/test_prepared_commit.py tests/seam/test_ingest_abort.py tests/stores: 92 passed in 10.03s
tests/seam tests/parity tests/parts_core: 962 passed, 1 skipped, 3 deselected in 134.83s
tools/check_offline_suite.py: pytest -q -rs: 1659 passed, 1 skipped, 4 deselected; python -m pytest -q -rs: 1659 passed, 1 skipped, 4 deselected
```

The three graph cases (staged node invisible to a second instance until commit, abort leaves nothing, finalize while prepared raises nothing) also passed against the default prepare, because a no-op prepare followed by a one-call commit shows the same results. They pin the contract. The staging itself appears in `CozoGraphStore.prepare` running `_stage` and in the engine ordering test, where all three prepares run before the first commit.

## Acceptance greps

- `async def prepare`, `async def commit_prepared`, `async def abort_prepared` in `stores/base.py`: 3 lines
- `BEGIN IMMEDIATE` in `stores/kv.py`: 1 line
- `async def _commit_all` and `_commit_all(stores, "ingest"` in `seam/engine.py`: 1 line each
- `_loaded_signature` in `stores/vector.py`: 5 lines; `_prepared_mt` in `stores/graph.py`: 5 lines
- `def _write_staged` and `def _commit_staged` in `stores/vector.py`: 2 lines

## Finalize and release coverage (the 10-01 shared-client caveat)

- Engine: `ingest` still finalizes every store in its existing `finally`. `_commit_all` aborts on every prepare or commit failure, including cancellation.
- `CozoGraphStore.finalize` aborts any still-open `_prepared_mt` (suppressing its error) inside a `try`, and releases the registry reference in the `finally`. A prepared transaction therefore never pins the shared client, and the client never closes under an open transaction (R10).
- `commit_prepared` clears `_prepared_mt` before committing. A failed commit is aborted once (`_commit_or_abort`) and is never committed or aborted twice.
- `abort_prepared` and `drop_pending_index_ops` remove the vector `.tmp` pair and roll back the kv transaction. The prepare-failure engine test asserts that no `*.tmp` file is left under the workspace.

## Deviations from Plan

None that change behaviour. Choices the plan left open:

- `drop_pending_index_ops` on `FaissVectorStore` and `CozoGraphStore` delegates to `abort_prepared`, so the 10-04 refusal path also cleans up anything staged.
- The graph `_stage` takes a snapshot of the buffers made on the loop thread, as the plan names it (`_stage(snapshot)`), so a worker thread never iterates a buffer the loop could be mutating.
- `delete_by_ids` refreshes `_loaded_signature` after its immediate persist. Without this, the next prepare would reload the instance's own write from disk. The result would be correct, but the reload is wasted work.

## Known limits

- `commit_prepared` clears every pending buffer, including writes buffered after `prepare`. The engine buffers nothing between the two calls. A direct caller that writes between `prepare` and `commit_prepared` loses those writes.
- The `.tmp` names stay fixed, as the plan's flagged assumption states. The engine lock serializes in-process writers and the store-root lock serializes processes. A direct `index_done_callback` caller that runs at the same time as an engine flush on the same vector namespace in one process is not serialized by the engine lock.

## Threat Flags

None. No new endpoint, auth path or trust-boundary schema. T-10-14, T-10-15 and T-10-16 are mitigated as planned, and T-10-17 is documented in the engine module docstring.

## Self-Check: PASSED

- FOUND: databasise/tests/stores/test_prepared_commit.py
- FOUND: 3f08cba (ancestor of HEAD)
- FOUND: fd57914 (ancestor of HEAD)
