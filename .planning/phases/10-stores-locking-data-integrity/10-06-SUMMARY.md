---
phase: 10-stores-locking-data-integrity
plan: 06
subsystem: stores-and-seam-engine
tags: [snapshot-cache, evidence-resolve, faiss, crash-window, d-05, q6, stor-03, stor-08]
status: complete

requires: ["10-05"]
provides:
  - "databasise/stores/vector.py: _Committed (frozen; entries is a MappingProxyType), load_committed(dir_path), _SNAPSHOT_CACHE (OrderedDict LRU), _SNAPSHOT_CACHE_SIZE = 32, _SNAPSHOT_LOCK, _stat_signature, _read_snapshot"
  - "FaissVectorStore._read_committed adopts the shared snapshot (open and prepare rebase); _loaded_signature now comes from the snapshot"
  - "load_committed raises VectorStoreCorruptedError(present, None, '<missing vector.faiss>' | '<missing vector.meta.json>') on a half-written directory"
  - "Databasise.resolve_evidence: VectorStoreCorruptedError -> ForeignEngineRefusalError(failure_class='StoreCorrupted'), 502 over REST"
  - "databasise/tests/seam/test_evidence_resolve_stores.py (new, 8 cases), databasise/tests/stores/test_vector_crash_window.py (new, 9 cases)"
affects: [10-07]

actuals:
  tokens: 5489
  tasks: 2
  commits: 2
plan_head_before: a4846fbb5380072f1f32a3c865c11bf71a615dac
plan_head_after: f3111fb8b65a6de20d07419dd8c71735afaadf85

tech-stack:
  added: []
  patterns:
    - "Stat-keyed committed-snapshot cache: key (resolved dir, stat triple of vector.faiss, stat triple of vector.meta.json); stat-read-stat with one retry; per-directory stale-key eviction plus LRU cap"

key-files:
  created:
    - databasise/tests/seam/test_evidence_resolve_stores.py
    - databasise/tests/stores/test_vector_crash_window.py
  modified:
    - databasise/stores/vector.py
    - databasise/seam/engine.py

key-decisions:
  - "A half-written directory goes through the same one-retry loop as a signature change, so a reader inside the very first commit's two-rename window gets one more look before the corruption refusal"
  - "commit_prepared does not put the new state into the cache; the next reader loads it from disk because os.replace changed the inode"
  - "The snapshot is read-only at the top level only (MappingProxyType over entries); inner entry dicts are shared and no code path mutates them"

requirements-completed: [STOR-03, STOR-08]

duration: 25min
completed: 2026-10-17
---

# Phase 10 Plan 06: Evidence resolve snapshot cache and half-written Faiss refusal Summary

`/evidence/resolve` reads a Faiss namespace's committed snapshot from a bounded, stat-keyed process cache: five resolves against an unchanged index read and hash it once, and a writer's flush changes the inode, so the next resolve reads the new index (D-05, STOR-03). A namespace directory holding only one of its two files now raises `VectorStoreCorruptedError` instead of opening empty, and through the seam it is a 502 `StoreCorrupted` fault, never the 404 not-present refusal (STOR-08, Q6).

## What was built

- `load_committed(dir_path)` in `stores/vector.py`. It stats both files and returns `None` when both are absent. On a hit it returns the cached `_Committed`. On a miss it reads the sidecar, hashes the index, compares checksums, runs `faiss.read_index`, then stats again. A changed signature or a half-written directory is retried once and then raises `VectorStoreCorruptedError`. It never creates a directory.
- The cache is an `OrderedDict` behind one `threading.Lock`. It is capped at 32 entries (marked `shortcut:`), and an insert evicts other keys for the same directory.
- `FaissVectorStore._read_committed` uses `load_committed`, so every open and every prepare rebase goes through the cache. Writers still build their own instances and clone the index before changing it.
- `Databasise.resolve_evidence` catches `VectorStoreCorruptedError` and raises `_foreign_fault("resolve_evidence", exc, failure_class="StoreCorrupted")`. The cause and its path are logged server-side once and stay out of the body.

## TDD evidence

Task 1 RED (before the cache): `AssertionError: assert {'read': 5, 'hash': 5} == {'read': 1, 'hash': 1}`. 4 failed, 4 passed (the four that passed are the vector-only and held-graph checks, which Phase 9 already satisfied). GREEN: 8 passed.

Task 2 RED: `DID NOT RAISE VectorStoreCorruptedError` (4 cases, both missing-file variants), `UnresolvableEvidenceReferenceError` from `engine.resolve_evidence` (2), `assert 404 == 502` over REST (2). 8 failed, 1 passed. GREEN: 27 passed across test_vector_crash_window.py, test_vector.py (including the checksum-mismatch test at line 156, unchanged) and test_evidence_resolve_stores.py.

## Verification

- `pytest -q tests/seam/test_evidence_resolve_stores.py tests/stores tests/seam/test_evidence_namespace_guard.py tests/seam/test_evidence_refs.py`: 128 passed
- `pytest -q tests/seam tests/parity tests/parts_core`: 970 passed, 1 skipped, 3 deselected
- `pytest -q tests/stores tests/seam tests/mcp tests/parity`: 989 passed, 1 skipped, 3 deselected
- `tools/check_offline_suite.py`: exit 0; 1676 passed, 1 skipped, 4 deselected under both `pytest` and `python -m pytest`

## Deviations from Plan

None. The plan was executed as written. One choice inside the plan's scope: the half-written check uses the same single retry as the stat-changed case, so a resolve that lands inside the very first commit of a new namespace (index renamed, sidecar not yet) does not report corruption on its first look.

## Threat Flags

None. T-10-18 (bounded LRU and per-directory eviction), T-10-19 (MappingProxyType plus the assignment test), T-10-20 (REST test asserts no store path or file name in the 502 body) and T-10-21 (open refuses before any write; the test checks the surviving file's bytes) are all mitigated as planned.

## Known limits

- If a file disappears between the stat and the read (for example during `drop()`), the error is a `FileNotFoundError`, not a corruption refusal. No current path triggers this during resolve.
- Under a hot ingest the one retry can be exhausted, which gives a spurious `StoreCorrupted` (research A2). The fallback is the brief flush-lock read.

## Self-Check: PASSED

- FOUND: databasise/stores/vector.py (`def load_committed`, `MappingProxyType`, `shortcut:`, `<missing vector.meta.json>`, `<missing vector.faiss>`)
- FOUND: databasise/seam/engine.py (`failure_class="StoreCorrupted"`)
- FOUND: databasise/tests/seam/test_evidence_resolve_stores.py, databasise/tests/stores/test_vector_crash_window.py
- FOUND: 1e35445, f3111fb (ancestors of HEAD)
