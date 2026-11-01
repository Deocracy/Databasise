---
phase: 10-stores-locking-data-integrity
plan: 11
subsystem: stores-data-integrity
tags: [vector-store, named-refusals, reserved-metadata, d-11, d-12, stor-09, stor-16]
status: complete

requires: ["10-10"]
provides:
  - "databasise/stores/vector.py: _RESERVED_METADATA_KEYS, ReservedMetadataKeyError(ValueError) raised by FaissVectorStore.upsert before _pending changes"
  - "databasise/stores/vector.py: InvalidTopKError(ValueError) for top_k <= 0 in query and self_knn, checked before the empty-index return"
  - "databasise/stores/vector.py: MultiNamespaceVectorStore._available_namespaces lists only dirs holding vector.faiss; score_all/self_knn/get_by_id/iter_vectors raise VectorNamespaceNotSelectedError"
  - "databasise/parity/import_index.py: _import_vector_kind strips id and score from v1 metadata"
  - "databasise/tests/stores/test_vector_reserved_keys.py (new, 5 cases), databasise/tests/stores/test_vector_validation.py (new, 6 cases)"
affects: [every vector writer (parts_core hipporag chunk_embed, entity_fact_embed; parity import)]

actuals:
  tokens: 3578
  tasks: 2
  commits: 2
plan_head_before: b0b01dde42a03c2549b1e4102643efc735cf8d7e
plan_head_after: 56fd1442a45efe9d44aff287a859535f30db216a

tech-stack:
  added: []
  patterns:
    - "Store-level input refusals are named ValueError subclasses in stores/, in the VectorStoreCorruptedError house style, outside the seam catalogue (D-12)"

key-files:
  created:
    - databasise/tests/stores/test_vector_reserved_keys.py
    - databasise/tests/stores/test_vector_validation.py
  modified:
    - databasise/stores/vector.py
    - databasise/parity/import_index.py

key-decisions:
  - "ReservedMetadataKeyError.keys is the sorted list of reserved keys found in the first offending metadata dict; the check runs after the length checks and before the dimension check, so nothing is buffered"
  - "MultiNamespaceVectorStore._available_namespaces keeps its fallback to the selected children when the workspace directory does not exist"

requirements-completed: [STOR-09, STOR-16]

duration: 20min
completed: 2026-10-17
---

# Phase 10 Plan 11: Vector store named refusals and reserved metadata keys Summary

`FaissVectorStore.upsert` refuses metadata keys `id` and `score` with `ReservedMetadataKeyError`, and the v1 importer strips them, so every result carries its real id and score (STOR-16, D-11). `top_k <= 0` raises `InvalidTopKError`. An unselected `MultiNamespaceVectorStore` refuses every read with `VectorNamespaceNotSelectedError`, and that refusal lists only real vector namespaces (STOR-09, D-12).

## What was built

- `stores/vector.py`:
  - `_RESERVED_METADATA_KEYS = frozenset({"id", "score"})` and `ReservedMetadataKeyError(ValueError)` with a public `keys` field. `upsert` checks each metadata dict right after the existing length checks and raises before `_pending` changes.
  - `InvalidTopKError(ValueError)` with a public `top_k` field. `query` and `self_knn` check `top_k <= 0` first, before the empty-index return.
  - `MultiNamespaceVectorStore._available_namespaces` keeps only directories that contain `vector.faiss`.
  - `MultiNamespaceVectorStore` gains async `score_all` and `self_knn` and sync `get_by_id` and `iter_vectors`. Each raises `VectorNamespaceNotSelectedError`. `iter_vectors` is a plain method, so it raises at call time (research Pitfall 12).
  - The docstrings for both error classes and both store classes are updated to match.
- `parity/import_index.py` `_import_vector_kind`: `"id"` and `"score"` join the keys it leaves out of each record's metadata, with a D-11 comment.
- I checked every non-test vector writer (`parts_core/hipporag/chunk_embed.py`, `parts_core/hipporag/entity_fact_embed.py` and `parity/import_index.py`). None writes `id` or `score` metadata.

## Test evidence

Before the change, a probe against the unchanged source showed:
- `get_by_id('a')` returned `{'id': 'SHADOW', 'score': 99}` and `query` returned `[{'id': 'SHADOW', 'score': 99}]`.
- On a populated store, `query(top_k=0)` and `query(top_k=-1)` raised a bare `AssertionError`. On an empty store, `query(top_k=0)` returned `[]`. `self_knn(top_k=0)` returned `{'a': []}`.
- With `text_chunks/` and `chunk_entity_relation/` next to `chunks/`, `available` was `['chunk_entity_relation', 'chunks', 'text_chunks']`.
- `score_all`, `self_knn`, `get_by_id` and `iter_vectors` on the unselected handle raised `AttributeError`.

Neither new test file could be collected against the unchanged source, because it imports a class that did not exist yet: `ImportError: cannot import name 'ReservedMetadataKeyError'` for Task 1, and the same for `InvalidTopKError` in Task 2.

After the change:
- Task 1: `tests/stores/test_vector_reserved_keys.py tests/stores tests/parity` gave 265 passed, 3 deselected. `tests/parts_core tests/seam` gave 833 passed, 1 skipped.
- Task 2: `tests/stores/test_vector_validation.py tests/stores` gave 125 passed. `tests/parts_core tests/seam tests/parity` gave 979 passed, 1 skipped, 3 deselected.
- Full gate `tools/check_offline_suite.py` gave 1754 passed, 1 skipped, 4 deselected, under both `pytest` and `python -m pytest`.

## Deviations from Plan

None. The plan was executed as written.

## Known Stubs

None.

## Threat Flags

None. T-10-32 (metadata shadowing id/score) is fixed by the upsert refusal and the importer strip, and tests cover both. T-10-33 (refusal listing non-vector directories) is fixed by the `vector.faiss` filter, and a test covers it.

## Self-Check: PASSED

- FOUND: databasise/tests/stores/test_vector_reserved_keys.py
- FOUND: databasise/tests/stores/test_vector_validation.py
- FOUND: 41730ba, 56fd144 (ancestors of HEAD)
- `grep "class ReservedMetadataKeyError(ValueError)"`: 1 line; `grep "class InvalidTopKError(ValueError)"`: 1 line
- `grep "def iter_vectors" stores/vector.py`: 2 lines (447, 701)
- `grep '"score"' parity/import_index.py`: lines 187 and 192, in `_import_vector_kind`
