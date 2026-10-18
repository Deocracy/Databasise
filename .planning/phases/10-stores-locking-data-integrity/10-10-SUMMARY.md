---
phase: 10-stores-locking-data-integrity
plan: 10
subsystem: stores-data-integrity
tags: [delete-commit, buffered-vector-delete, store-namespaces, d-08, q4, stor-07]
status: complete

requires: ["10-08"]
provides:
  - "databasise/stores/vector.py: FaissVectorStore.delete_by_ids buffers ids in _pending_deletes; prepare applies them to the rebased entries before _pending; commit/abort/drop/drop() clear them; _persist removed"
  - "databasise/seam/engine.py: delete_document builds stores from the resolved wiring's store_namespaces, drops pending ops on a refusal or a 'fail' status, otherwise commits through _commit_all(stores, 'delete', ...)"
  - "databasise/tests/stores/test_delete_commit_contract.py (new, 11 cases: 4 engine-level, 7 store-level)"
affects: [HIPP-16 HippoRAG delete, M-04 Phase 11 v1 delete port]

actuals:
  tokens: 5913
  tasks: 2
  commits: 2
plan_head_before: cc7459eb1d28fdff3386b69065f5f13f0720e3ef
plan_head_after: 2b486d28f82f8514341b8f2a591f6b261223de7d

tech-stack:
  added: []
  patterns:
    - "Every v2 store write (kv, vector, graph) is now buffered until prepare/commit, so one _drop_pending reverts a whole refused delete"

key-files:
  created:
    - databasise/tests/stores/test_delete_commit_contract.py
  modified:
    - databasise/stores/vector.py
    - databasise/seam/engine.py
    - databasise/tests/stores/test_vector.py

key-decisions:
  - "FaissVectorStore.prepare returns without writing when the only buffered deletes name ids absent from the rebased committed entries, so a delete of a never-committed id changes no file (the test checks the inode pair is unchanged)"
  - "delete_document commits for every non-'fail' status (success, not_found, not_allowed); only a refusal or 'fail' drops (Q4). For the opaque LightRAG delete this commit is a no-op until M-04"

requirements-completed: [STOR-07]

duration: 25min
completed: 2026-10-17
---

# Phase 10 Plan 10: Delete commit contract and buffered vector delete Summary

`delete_document` now builds its stores from the delete wiring's `store_namespaces`. It commits every store through prepare-all/commit-all when the delete succeeds, and drops pending ops when the delete node raises or reports `fail`. `FaissVectorStore.delete_by_ids` buffers until the flush, so a drop reverts a vector delete like the kv and graph deletes (D-08, Q4).

## What was built

- `stores/vector.py`:
  - `_pending_deletes: set[str]`. `delete_by_ids` pops the id from `_pending` and adds it to `_pending_deletes`. It does no I/O.
  - `upsert` discards its ids from `_pending_deletes`, so a later upsert cancels a buffered delete.
  - `prepare` treats `_pending_deletes` as pending work. After the rebase it keeps only the deleted ids present in the committed entries. It removes them from the staging index and entries before it applies `_pending`. If nothing is left to do, it writes nothing.
  - `commit_prepared`, `abort_prepared` (and so `drop_pending_index_ops`) and `drop` clear `_pending_deletes`.
  - The immediate-persist path (`_do_delete`, `_persist`) is removed. Reads stay committed-only. The module and method docstrings say so.
- `seam/engine.py` `delete_document`: `_build_stores(self.store_root, self.workspace, resolved, into=stores)`. Inside the `try`, `_node_result_or_refuse` runs. A `ForeignEngineRefusalError` drops pending ops and re-raises. A `fail` status drops. Anything else commits through `_commit_all(stores, "delete", self.store_root)`. `_release_staged_upload` and the MACH-11 correlation still run after the `finally`. The `_build_stores` docstring no longer says delete passes no `resolved`.
- `tests/stores/test_vector.py`: the delete test checks that `a` is still readable before the flush, then calls `index_done_callback()` before it asserts the delete.

## Test evidence

New test file run against the unchanged source (Task 1, step 1): `4 failed`.
- success: `assert (True, False, True) == (False, False, False)`. The kv and graph deletes were discarded at finalize; only the vector delete landed, because it persisted at once.
- raise: `assert (True, False, True) == (True, True, True)`. The refused delete still removed the vector.
- fail: `assert (True, False, True) == (True, True, True)`. Same.
- default LightRAG: `assert [] == ['CozoGraphStore', 'SqliteKVStore']`. No store was prepared, because delete never committed.

After the change:
- `tests/stores/test_delete_commit_contract.py tests/stores/test_vector.py tests/seam/test_delete_document.py tests/seam/test_raw_upload_staging.py`: 38 passed, 1 skipped.
- `tests/stores tests/seam tests/mcp tests/parity`: 1016 passed, 1 skipped, 3 deselected.
- Task 2, `tests/stores/test_delete_commit_contract.py tests/stores`: 114 passed.
- Full gate `tools/check_offline_suite.py`: 1743 passed, 1 skipped, 4 deselected (both `pytest` and `python -m pytest`).

Task 2's store-level cases were written after Task 1 had implemented the buffer, so they passed at once. To show they are real checks, I ran them against the pre-plan `vector.py` (cc7459e) and then restored the file. 2 of 7 failed: `test_a_dropped_vector_delete_is_reverted_after_reopen` (the id was gone before the flush) and `test_an_aborted_prepare_keeps_the_deleted_entry`. The other five pass on both versions. Under the old immediate delete, those orderings were trivially correct. They now guard the buffered path.

## Deviations from Plan

None. The plan was executed as written. No ordering case needed a fix in Task 2.

## Known Stubs

None.

## Threat Flags

None. T-10-30 (partial delete) and T-10-31 (delete in another modality's default namespaces) are mitigated and tested. The success test asserts that `text_chunks` and `chunk_entity_relation` are never created under the fixture namespaces.

## Self-Check: PASSED

- FOUND: databasise/tests/stores/test_delete_commit_contract.py
- FOUND: 3cb6a1a, 2b486d2 (ancestors of HEAD)
- `grep "_build_stores(self.store_root, self.workspace, resolved, into=stores)"`: 3 lines (ingest, delete_document, _execute_resolved)
- `grep '_commit_all(stores, "delete"'`: 1 line
- `grep "_pending_deletes" stores/vector.py`: 9 lines
