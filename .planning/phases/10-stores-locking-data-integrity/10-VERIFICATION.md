---
phase: 10-stores-locking-data-integrity
verified: 2026-11-01T07:21:34Z
status: passed
score: 5/5 must-haves verified (16/16 requirements)
covered_files:
  - .planning/phases/10-stores-locking-data-integrity/10-01-PLAN.md
  - .planning/phases/10-stores-locking-data-integrity/10-01-SUMMARY.md
  - .planning/phases/10-stores-locking-data-integrity/10-02-PLAN.md
  - .planning/phases/10-stores-locking-data-integrity/10-02-SUMMARY.md
  - .planning/phases/10-stores-locking-data-integrity/10-03-PLAN.md
  - .planning/phases/10-stores-locking-data-integrity/10-03-SUMMARY.md
  - .planning/phases/10-stores-locking-data-integrity/10-04-PLAN.md
  - .planning/phases/10-stores-locking-data-integrity/10-04-SUMMARY.md
  - .planning/phases/10-stores-locking-data-integrity/10-05-PLAN.md
  - .planning/phases/10-stores-locking-data-integrity/10-05-SUMMARY.md
  - .planning/phases/10-stores-locking-data-integrity/10-06-PLAN.md
  - .planning/phases/10-stores-locking-data-integrity/10-06-SUMMARY.md
  - .planning/phases/10-stores-locking-data-integrity/10-07-PLAN.md
  - .planning/phases/10-stores-locking-data-integrity/10-07-SUMMARY.md
  - .planning/phases/10-stores-locking-data-integrity/10-08-PLAN.md
  - .planning/phases/10-stores-locking-data-integrity/10-08-SUMMARY.md
  - .planning/phases/10-stores-locking-data-integrity/10-09-PLAN.md
  - .planning/phases/10-stores-locking-data-integrity/10-09-SUMMARY.md
  - .planning/phases/10-stores-locking-data-integrity/10-10-PLAN.md
  - .planning/phases/10-stores-locking-data-integrity/10-10-SUMMARY.md
  - .planning/phases/10-stores-locking-data-integrity/10-11-PLAN.md
  - .planning/phases/10-stores-locking-data-integrity/10-11-SUMMARY.md
  - .planning/phases/10-stores-locking-data-integrity/10-12-PLAN.md
  - .planning/phases/10-stores-locking-data-integrity/10-12-SUMMARY.md
  - databasise/__init__.py
  - databasise/launcher/gc_namespaces.py
  - databasise/namespaces.py
  - databasise/parity/build_hipporag_index.py
  - databasise/parity/import_index.py
  - databasise/parity/run_arm.py
  - databasise/parity/run_comparison.py
  - databasise/parity/run_cross_modality.py
  - databasise/parity/storage_audit.py
  - databasise/parts_core/__init__.py
  - databasise/parts_core/hipporag/graph_augment_persist.py
  - databasise/parts_core/lightrag/full_delete.py
  - databasise/parts_core/lightrag/full_ingest.py
  - databasise/runner/scheduler.py
  - databasise/seam/corpus.py
  - databasise/seam/engine.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/stores/base.py
  - databasise/stores/graph.py
  - databasise/stores/kv.py
  - databasise/stores/probes.py
  - databasise/stores/vector.py
  - databasise/validator/errors.py
  - databasise/validator/parse.py
covered_digest: "v3:sha256:35975dfff72d388376a153ccd68081b422c33298d13ad032e908cc4ced7137e0"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 5/5
  gaps_closed: []
  gaps_remaining: []
  regressions: []
advisory:
  - finding: "A commit-phase failure on the last store leaves the earlier stores committed (kv and vector hold the run's records, graph does not)"
    category: other
    reason: "Documented residual window of D-07. `_commit_all` (engine.py:931-953) still aborts only the stores not yet committed. Success criterion 3 was kept as written by D-07, so a prepare-phase failure is fully covered and a commit-phase failure after another store committed is not. Reproduced by probe in the initial verification; the code path is unchanged."
    evidence_status: "reproduced by probe at initial verification; accepted by D-07"
---

# Phase 10: Stores, Locking & Data Integrity Verification Report

**Phase Goal:** Concurrent engine calls on one store root produce named outcomes instead of 500s, and every store commits all of a run's writes or none of them.
**Verified:** 2026-11-01
**Status:** passed
**Re-verification:** Yes. The 2026-10-17 report went stale because 21 covered source files moved (Phases 11 to 16 and the start of 17 edited the engine, stores, scheduler, parse and the parity scripts). Every must-have was re-checked against the current code at HEAD (7147047). No regression found and no gap opened. A second staleness trip on 2026-11-01 (bug-fix commits from the debugging and security battery) was re-checked against HEAD 0d9cabcf; see "Re-verification 2026-11-01 (audit fixes)" below.

## What moved since the initial report

`git diff a9e545e..HEAD` over the covered files shows additive changes only, none of which touches a Phase 10 mechanism:

| File | Change since a9e545e | Effect on Phase 10 |
| ---- | -------------------- | ------------------ |
| `stores/graph.py` | docstring (a fifth Cozo bug) plus new `held_graph_paths()` | `_ClientRegistry` acquire/release and lock mapping unchanged |
| `stores/probes.py` | new read helpers `acquire_graph`, `graph_node_page`, `graph_node_edges`, `list_kv_prefix`; `GraphStoreCorruptedError` | `probe_kv`, `probe_graph`, `probe_vector` unchanged; the new helpers open through `_ClientRegistry` and create nothing |
| `stores/vector.py` | `mkdir` moved from `__init__` to the first staged write; `ensure_index`, `list_ids`, `self_knn(ids=...)` added; `_pending_create_dim` cleared by `commit_prepared`, `abort_prepared` and `drop` | buffered delete, corruption check, reserved keys and `top_k` refusal intact; reads of a missing directory are empty and create nothing |
| `parts_core/__init__.py` | `list_ids` added to the engine-only set, `ensure_index` to the write vocabulary | tightens the read-only proxy; `EFFECT_TO_STORE` untouched |
| `validator/parse.py`, `errors.py` | more codes; `unwired-store-effect` kept (`parse.py:79`, `parse.py:273-277`; `errors.py:49`) | STOR-12 refusal intact |
| `seam/engine.py`, `runner/scheduler.py` | large growth (operator surface, corpus, HippoRAG gate, MACH-11) | the Phase 10 paths below were re-read and are unchanged in behavior |

### Re-verification 2026-11-01 (audit fixes)

Trigger: eight covered files changed after the 2026-10-31 run, all in test-first bug-fix commits from the debugging and security battery (`git diff 3aafcc62 HEAD`). `runner/scheduler.py` has no net diff (e682f687 was reverted by 3500f131). Only two commits touch a Phase 10 mechanism; the rest are refusal-boundary additions that shift the engine line numbers cited below (updated in place).

| File | Change since 3aafcc62 | Effect on Phase 10 |
| ---- | -------------------- | ------------------ |
| `stores/graph.py` (a895ef8a) | `_ClientRegistry.release` wraps the last-reference `client.close()` in try/except: when pycozo refuses with `RuntimeError('Already borrowed')` (an executor thread still inside `run()` after an asyncio cancel) the entry is re-registered at refcount 0 and a warning is logged; `CozoGraphStore.finalize` docstring says the refusal is never raised | SC1 strengthened: a close refused inside the engine's `finally` no longer replaces the in-flight named refusal with a 500, and the next in-process acquire reuses the open client instead of reading RocksDB's held LOCK as `GraphStoreBusyError`. `held_graph_paths` filters `refcount > ...`, so a deferred-close client is not reported as a holder. A second OS process still gets the 409 while the client is open, which is the pre-existing named outcome. `acquire` on the kept entry increments 0 to 1; `_released` keeps a second `finalize` from decrementing it below 0. Test: `tests/stores/test_graph_release_under_run.py` (two tests: raw `_release` and `finalize`, each asserting kept client, refcount 0, logged warning, reuse without busy, and a successful close on the next last release) |
| `stores/probes.py` (4bfdb8db) | `probe_kv` opens plain `?mode=ro` when both `kv.sqlite3-wal` and `kv.sqlite3-shm` exist (a live writer), `?mode=ro&immutable=1` otherwise; same rule `list_kv_prefix` already used | SC2 / STOR-04 hold: plain `mode=ro` only creates a missing `-shm`, and the branch is taken only when `-shm` exists, so health still creates nothing on any root (`test_probe_hardening.py`, `test_health_probe.py` pass). The fix removes a false `corrupted` from an unlocked immutable read of a page torn by the writer's checkpoint; under a live writer the probe now reports `ok` or the named `busy`. Test: `tests/stores/test_probe_kv_live_writer.py` (four probe threads against 300 checkpointing commits; asserts no `corrupted`, outcomes within `{ok, busy}`) |
| `seam/engine.py` | `require_encodable` at the alias/version/trace/query boundaries, `CanonicalisationError` mapped to `NonEncodableTextError`, `PageBoundsError` for `GET /log` limits, `OverflowError` mapped to `StoreFault`, `_v1_row_track_id` moved off the loop thread | None of `_build_stores`, `_refuse_unparseable`, `_drop_pending`, `_commit_all`, `_node_result_or_refuse`, `health`, `resolve_evidence` or the `into=`/`finalize` pattern changed; only their line numbers moved (+4 to +16) |
| `seam/refusals.py`, `seam/rest.py`, `seam/corpus.py` | `bounded_echo`/`json_safe` on every echoed caller value, `NonEncodableTextError`, document-id and page-offset ceilings, schema-error 422 built without FastAPI's `input` echo | `StoreBusyError`, `UnparseableWiringError`, `StoreCorrupted`/`StoreFault` and their status codes are untouched (`test_store_refusal_status.py`, `test_store_open_faults.py` pass). No new store-touching path; every addition refuses before a store is opened |
| `validator/parse.py` (311d49d2) | non-string node ids reported as `invalid-wiring-document` before the cycle pass | `unwired-store-effect` check intact at `parse.py:79, 273-277`; `test_store_effects_wired.py` passes for every shipped wiring |

Targeted run on 2026-11-01: `tests/stores` (all, including the two new files) plus `test_build_stores_cleanup.py`, `test_store_refusal_status.py`, `test_evidence_resolve_stores.py`, `test_health_probe.py`, `test_ingest_abort.py`, `test_store_open_faults.py`, `test_store_isolation.py`, `test_delete_document.py`, `tests/wirings/test_store_effects_wired.py`: 261 passed in 57.1 s. The runner, namespace GC and removed-store tests were not re-run because their sources (`scheduler.py` net unchanged, `parts_core/__init__.py`, `namespaces.py`, `launcher/gc_namespaces.py`) did not move. The phase goal still holds: both fixes make a named outcome where a 500 or a false `corrupted` was possible, and neither touches the prepare/commit sequence. Status stays `passed`; no regression, no new gap.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Two overlapping engine calls on one graph namespace never return a 500: shared handle or a named store-busy refusal; a second OS process gets the same refusal; a failed open leaves no sqlite connection | VERIFIED | `_build_stores` (`engine.py:618-676`) builds kv, vector, graph into the caller's `into=` dict inside one try; `GraphStoreBusyError` becomes `StoreBusyError(store_kind="graph")` with the path logged once and not returned (`engine.py:663-667`); corrupt or OS open faults become `StoreCorrupted` or `StoreFault`. Callers pass `into=stores` inside their try and finalize every store in `finally` (`engine.py:1548, 1614-1615`; delete `1830, 1861-1862`; query `2567, 2580`). The refcounted `_ClientRegistry` is in `stores/graph.py`; since a895ef8a a last release whose `close()` is refused keeps the client registered at refcount 0 and logs instead of raising, so the engine's `finally` cannot mask a refusal with a 500. Tests: `tests/stores/test_graph_lock.py`, `tests/stores/test_graph_registry_close_race.py`, `tests/stores/test_graph_release_under_run.py`, `tests/seam/test_build_stores_cleanup.py`, `tests/seam/test_store_refusal_status.py`, `tests/seam/test_store_open_faults.py`, all passing. The second-OS-process 409 and overlapped-call probes of the initial report exercise code that has not changed. |
| 2 | `POST /evidence/resolve` opens only the named vector namespace, works while the graph is held, and reads the index once until it changes; `GET /health` on an empty root creates nothing and reports absent or corrupted stores as not ok | VERIFIED | `resolve_evidence` (`engine.py:2689-2710`) validates the namespace, requires the directory to exist, builds only `MultiNamespaceVectorStore`, maps `VectorStoreCorruptedError` to `StoreCorrupted`, and finalizes in `finally`. `health()` (`engine.py:2044-2118`) constructs no store: it runs `_PROBES[kind](root / namespace)` over the ten-entry `_HEALTH_PROBES` list (`engine.py:425-437`), and a raising probe reports `corrupted`. `probe_kv` (`probes.py:62`) opens plain `mode=ro` only when `-wal` and `-shm` both already exist, immutable otherwise, so no probe creates a file. The snapshot cache (`load_committed`) is unchanged. Tests: `tests/seam/test_evidence_resolve_stores.py`, `tests/seam/test_health_probe.py` (drift test included), `tests/stores/test_probe_hardening.py`, `tests/stores/test_probe_kv_live_writer.py`, all passing. |
| 3 | A failed ingest or delete commits nothing and a successful one commits everything; vector deletes are buffered and reverted; delete uses the wiring's declared namespaces | VERIFIED (with one accepted residual, see Advisory) | `_node_result_or_refuse` (`engine.py:976-1021`) refuses on a cycle, any node exception, `partial`, or a missing result. Ingest drops every store's pending writes on refusal (`engine.py:1586-1590`) and otherwise commits through `_commit_all` (`engine.py:931-953`: prepare all, then commit all, under one flush lock; a prepare failure aborts all). Delete resolves namespaces from the wiring (`engine.py:653-655, 1830`) and commits only on `success` or `not_found`, dropping otherwise (`engine.py:1853-1859`). `FaissVectorStore.delete_by_ids` still buffers into `_pending_deletes`, cleared by `abort_prepared`. Tests: `tests/seam/test_ingest_abort.py`, `tests/stores/test_prepared_commit.py`, `tests/stores/test_delete_commit_contract.py`, `tests/stores/test_delete_status_commit.py`, `tests/seam/test_delete_document.py`, all passing. |
| 4 | A node declaring only read effects cannot mutate any store; every store effect either resolves to a wired store or is refused at parse | VERIFIED | `parts_core/__init__.py` holds `EFFECT_TO_STORE`, the allowlists, the engine-only set and the write vocabulary (now including `ensure_index`, so the newer vector mutator is also refused on a read handle). `runner/scheduler.py:263-303` (`_ScopedStoresView`) resolves every access through `EFFECT_TO_STORE` and raises `UndeclaredEffectError` otherwise. `validator/parse.py:79, 273-277` refuses `reads_lexical`, `writes_lexical` and `reads_blob` with `unwired-store-effect`; the engine raises it as `UnparseableWiringError` through `_refuse_unparseable` (`engine.py:679`) before any store is built (called at 1467, 1665, 1729, 1813, 2556). Tests: `tests/runner/test_capability_scoping_modes.py`, `tests/runner/test_store_proxy_hardening.py`, `tests/wirings/test_store_effects_wired.py` (every shipped wiring, including those edited in Phases 11 to 13, parses), all passing. |
| 5 | Adapters keep their data consistent and refuse bad input by name: Faiss corruption, reserved metadata keys, no dangling edges, KV buffer isolation, blob digest safety, lexical AND, GC with a production caller that reports failures | VERIFIED | Corruption and reserved keys: `stores/vector.py:103, 351-353` (`_RESERVED_METADATA_KEYS = {"id", "score"}`, `ReservedMetadataKeyError`); `tests/stores/test_vector_crash_window.py`, `test_vector_reserved_keys.py`, `test_vector_validation.py`, `test_vector_snapshot_robustness.py`. Graph cascade: `tests/stores/test_graph_delete_cascade.py`. KV isolation: `tests/stores/test_kv_buffer_isolation.py`. Lexical and blob stores and `registry_artifact/` remain removed (`ls databasise/stores` shows only base, graph, kv, probes, vector; `registry_artifact` is absent); `tests/test_removed_stores_absent.py` passes. GC: `launcher/gc_namespaces.py` takes `store_lock`, catches `StoreLockedError` and `NamespaceGCError`; `namespaces.py:106-132` defines `NamespaceGCError` with no `ignore_errors`; `tests/test_namespaces_gc.py` passes. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `databasise/stores/graph.py` | shared client registry, cascade, prepare/commit | VERIFIED | used by `engine._build_stores`, `probes`, parity scripts; release never raises on a refused close (a895ef8a) |
| `databasise/stores/vector.py` | snapshot cache, corruption, reserved keys, buffered delete | VERIFIED | additions are additive and cleared on abort |
| `databasise/stores/kv.py` | buffer isolation, prepare/commit | VERIFIED | unchanged since the initial report |
| `databasise/stores/probes.py` | read-only health probes | VERIFIED | called from `engine.health` through `_PROBES`; `probe_kv` locks under a live writer, immutable otherwise (4bfdb8db) |
| `databasise/parts_core/__init__.py` | `EFFECT_TO_STORE`, allowlist proxies | VERIFIED | consumed by `runner/scheduler.py` and `parity/storage_audit.py` |
| `databasise/seam/engine.py` | atomic ingest/delete, StoreBusy, health, resolve | VERIFIED | re-read at every cited line |
| `databasise/seam/refusals.py` | `StoreBusyError`, `UnparseableWiringError` | VERIFIED | imported by the engine; `test_refusal_catalogue.py` family covers them |
| `databasise/launcher/gc_namespaces.py` | operator GC CLI | VERIFIED | `tests/test_namespaces_gc.py` |
| `databasise/validator/parse.py` | `unwired-store-effect` violation | VERIFIED | `parse.py:79, 273-277` |
| `stores/lexical.py`, `stores/blob.py`, `registry_artifact/` | removed (D-15) | VERIFIED | absent from the tree |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `engine._build_stores` | `GraphStoreBusyError` | except clause | WIRED | `engine.py:663-667` |
| `engine.ingest` | `_drop_pending` / `_commit_all` | refusal and success paths | WIRED | `engine.py:1586-1602` |
| `engine.delete_document` | wiring `store_namespaces` | `_build_stores(resolved)` | WIRED | `engine.py:1830` |
| `scheduler._ScopedStoresView` | `EFFECT_TO_STORE` | table lookup | WIRED | `scheduler.py:298-303` |
| `engine.health` | `probes` | `_HEALTH_PROBES` / `_PROBES` | WIRED | `engine.py:2062-2068` |
| `parse_wiring` | `UnparseableWiringError` | `_refuse_unparseable` | WIRED | five call sites |
| `engine.resolve_evidence` | `load_committed` cache | `MultiNamespaceVectorStore` | WIRED | `engine.py:2704-2705` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `HealthReport.stores` | per-namespace state | file and client probes on disk | Yes (`test_health_probe.py` observes ok, absent, corrupted, busy) | FLOWING |
| `resolve_evidence` record | vector entry metadata | committed Faiss snapshot | Yes (`test_evidence_resolve_stores.py` checks new content after a rewrite) | FLOWING |

### Behavioral Spot-Checks

Re-verification relied on the existing behavioral tests, which exercise the concurrency and atomicity invariants directly; the initial report's one-off probes target code paths that are unchanged. No state was mutated by this verification.

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Phase 10 store, seam, runner, wiring and namespace tests (28 store files plus the 13 files named above) | `.venv/bin/python -m pytest tests/stores tests/seam/test_build_stores_cleanup.py tests/seam/test_store_refusal_status.py tests/seam/test_evidence_resolve_stores.py tests/seam/test_health_probe.py tests/seam/test_ingest_abort.py tests/seam/test_store_open_faults.py tests/seam/test_store_isolation.py tests/runner/test_capability_scoping_modes.py tests/runner/test_store_proxy_hardening.py tests/wirings/test_store_effects_wired.py tests/test_namespaces_gc.py tests/test_removed_stores_absent.py tests/seam/test_delete_document.py -q -p no:cacheprovider` | 331 passed in 112.6 s (2026-10-31) | PASS |
| 2026-11-01 audit-fix re-check: every store test (including `test_graph_release_under_run.py` and `test_probe_kv_live_writer.py`) plus the seam store, delete, isolation and wiring tests | `.venv/bin/python -m pytest tests/stores tests/seam/test_build_stores_cleanup.py tests/seam/test_store_refusal_status.py tests/seam/test_evidence_resolve_stores.py tests/seam/test_health_probe.py tests/seam/test_ingest_abort.py tests/seam/test_store_open_faults.py tests/seam/test_store_isolation.py tests/seam/test_delete_document.py tests/wirings/test_store_effects_wired.py -q -p no:cacheprovider` | 261 passed in 57.1 s | PASS |

### Probe Execution

No `probe-*.sh` scripts are declared by the phase. Step 7c: not applicable.

### Requirements Coverage

All 16 IDs appear in plan frontmatter (10-01: STOR-01, 02; 10-02: STOR-12, 13, 14; 10-03: STOR-15; 10-04 and 10-05: STOR-06; 10-06: STOR-03, 08; 10-07: STOR-04; 10-08: STOR-05; 10-09: STOR-10, 11; 10-10: STOR-07; 10-11: STOR-09, 16; 10-12: STOR-12) and are marked `[x]` and `Complete` in REQUIREMENTS.md. REQUIREMENTS.md maps STOR-01 to STOR-16 to Phase 10 and no other ID, so there is no orphan.

| Requirement | Source Plan | Status | Evidence |
| ----------- | ----------- | ------ | -------- |
| STOR-01 | 10-01 | SATISFIED | `engine.py:663-667`; `test_graph_lock.py`, `test_store_refusal_status.py`, `test_graph_release_under_run.py` |
| STOR-02 | 10-01 | SATISFIED | `into=` pattern at `engine.py:1548, 1830, 2567`; `test_build_stores_cleanup.py` |
| STOR-03 | 10-06 | SATISFIED | `engine.py:2689-2710`; `test_evidence_resolve_stores.py` |
| STOR-04 | 10-07 | SATISFIED | `engine.py:2044-2068`, `probes.py:62`; `test_health_probe.py`, `test_probe_kv_live_writer.py` |
| STOR-05 | 10-08 | SATISFIED | `parts_core/__init__.py`, `scheduler.py:263-303`; `test_capability_scoping_modes.py` |
| STOR-06 | 10-04, 10-05 | SATISFIED | `engine.py:931-953, 976-1021, 1586-1602`; `test_ingest_abort.py`, `test_prepared_commit.py` |
| STOR-07 | 10-10 | SATISFIED | `engine.py:1830, 1853-1859`; `test_delete_commit_contract.py`. Proved on a fixture v2 wiring; LightRAG v1 delete stages no v2 writes (D-08) |
| STOR-08 | 10-06 | SATISFIED | `vector.py` corruption check; `test_vector_crash_window.py` |
| STOR-09 | 10-11 | SATISFIED | `test_vector_validation.py` |
| STOR-10 | 10-09 | SATISFIED | `test_graph_delete_cascade.py` |
| STOR-11 | 10-09 | SATISFIED | `test_kv_buffer_isolation.py` |
| STOR-12 | 10-02, 10-12 | SATISFIED | `parse.py:79, 273-277`; `test_store_effects_wired.py` |
| STOR-13 | 10-02 | SATISFIED by removal (D-15) | `test_removed_stores_absent.py` |
| STOR-14 | 10-02 | SATISFIED by removal (D-15) | `test_removed_stores_absent.py` |
| STOR-15 | 10-03 | SATISFIED (D-16 exception: operator CLI, not retire) | `gc_namespaces.py`, `namespaces.py:106-132`; `test_namespaces_gc.py` |
| STOR-16 | 10-11 | SATISFIED | `vector.py:103, 351-353`; `test_vector_reserved_keys.py` |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| none | - | `TBD`, `FIXME`, `XXX` scan over `stores/`, `namespaces.py`, `launcher/gc_namespaces.py` and `parts_core/__init__.py` | - | No debt markers |

### Advisory (open review items and one accepted limit)

| # | Finding | Category | Why Advisory |
| - | ------- | -------- | ------------ |
| A1 | Commit-phase failure on the last store leaves earlier stores committed | other | D-07 documents it; `_commit_all` still aborts only the not-yet-committed stores. SC3 stands as written for the prepare phase. Fixing it needs a recovery record or a single transactional backend |
| A2 | Review INFO items from the initial report (proxy bypass routes, `probe_kv` leniency, directory named `kv.sqlite3` reported `absent`, finalize loops stop at the first failing `finalize`) | other | Recorded limits that do not break a success criterion |
| A3 | `trace.db*` files are created by the `Databasise` constructor, not by health | other | STOR-04 concerns files created by health |
| A4 | A fresh install reports `degraded` with every store `absent` | other | By design (D-14) |
| A5 | A deferred graph close (a895ef8a) keeps the RocksDB LOCK held at refcount 0 until the next acquire/release cycle on that path; a second OS process gets `StoreBusyError` for that window | other | Named outcome, not a 500; the window existed before the fix (the executor thread held the client), the fix only stops the engine's `finally` from raising over the in-flight refusal |

### Human Verification Required

None. Concurrency (SC1) and atomicity (SC3) are behavior-dependent truths, and each has a passing behavioral test in the run above, so none is left present-but-unexercised.

### Gaps Summary

No gaps. All five success criteria and all 16 requirements are met in the current code. The one place where "none of them" does not hold is a failure inside the commit sequence after an earlier store has already committed; D-07 chose that trade-off and the engine docstring documents it (A1).

---

_Verified: 2026-11-01_
_Verifier: Claude (gsd-verifier)_
