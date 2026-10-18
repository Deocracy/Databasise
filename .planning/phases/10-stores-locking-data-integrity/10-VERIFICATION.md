---
phase: 10-stores-locking-data-integrity
verified: 2026-10-17T00:00:00Z
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
covered_digest: "v3:sha256:87039de3f52d277f8e2ae647ccf30ddc3c2c4227e006c3690f513cfe753e90e3"
behavior_unverified: 0
overrides_applied: 0
advisory:
  - finding: "A commit-phase failure on the last store leaves the earlier stores committed (kv and vector hold the run's records, graph does not)"
    category: other
    reason: "Documented residual window of D-07 (engine.py docstring lines 147-150). Success criterion 3 was kept as written by D-07, so a prepare-phase failure is fully covered and a commit-phase failure after another store committed is not. Probe: graph.commit_prepared raising left kv non-empty and 4 vectors."
    evidence_status: "reproduced by probe; accepted by D-07"
---

# Phase 10: Stores, Locking & Data Integrity Verification Report

**Phase Goal:** Concurrent engine calls on one store root produce named outcomes instead of 500s, and every store commits all of a run's writes or none of them.
**Verified:** 2026-10-17
**Status:** passed
**Re-verification:** No, initial verification. Verified at HEAD a9e545e (code identical at da2101d).

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Two overlapping engine calls on one graph namespace never return a 500: both complete through a shared handle or the later one gets a named store-busy refusal; a second OS process gets the same refusal; a failed store open leaves no sqlite connection | VERIFIED | Shared refcounted client: `stores/graph.py:135-173` (`_ClientRegistry.acquire/release`), lock text mapped to `GraphStoreBusyError` at `graph.py:152-155` (`_is_lock_error`, `graph.py:122`). Engine translation to `StoreBusyError(store_kind="graph")` at `engine.py:440-444`; 409 at `rest.py:140-141`; catalogue entry `refusals.py:777`. Cleanup of already opened stores: `_build_stores(..., into=stores)` is called inside the try at `engine.py:973`, `1150`, `1331`, and the `finally` finalizes every store (`engine.py:1037-1039`, `1175-1177`, `1344-1346`). Probes in the Behavioral Spot-Checks table: a real HippoRAG ingest parked mid-run (graph open) with query, health and resolve overlapped in one process all completed; a second OS process holding the graph gave 409 `StoreBusyError` on `POST /query`, `POST /documents` and `DELETE /documents/{id}`, and `/health` reported `busy`; no response contained the store root or a namespace. Tests: `tests/stores/test_graph_lock.py`, `tests/seam/test_build_stores_cleanup.py`, `tests/seam/test_store_refusal_status.py`. |
| 2 | `POST /evidence/resolve` opens only the named vector namespace, works while the graph is held, and reads the index once until it changes; `GET /health` on an empty root creates nothing and reports absent or corrupted stores as not ok | VERIFIED | `engine.py:1439-1460` builds only `MultiNamespaceVectorStore`; snapshot cache keyed by `(path, st_ino, st_mtime_ns, st_size)` in `stores/vector.py:157-248` (`load_committed`). `health()` at `engine.py:1258-1293` constructs no store and calls `stores/probes.py:probe_kv/probe_graph/probe_vector`. Probe: 5 resolves after a warm health call made 0 `sha256` calls; after a writer rewrote the index the next resolve returned the new content with 1 extra hash; no `text_chunks` or `chunk_entity_relation` directory appeared. Empty root: all 10 stores `absent`, status `degraded`, and the only files in the tree were `trace.db*`, which the `Databasise` constructor creates before health runs (confirmed with a construct-only probe). Half-written Faiss pair: resolve gave `ForeignEngineRefusalError(StoreCorrupted)` and health gave `vector:chunks = corrupted`. Tests: `tests/seam/test_evidence_resolve_stores.py` (8), `tests/seam/test_health_probe.py` (9), `tests/stores/test_probe_hardening.py`. |
| 3 | A failed ingest or delete commits nothing and a successful one commits everything: after a refused run kv, vector and graph hold no records; vector deletes are buffered and reverted; delete uses the wiring's declared namespaces | VERIFIED (with one accepted residual, see Advisory) | Refusal decision `_node_result_or_refuse` at `engine.py:564-605` covers any node exception, `partial`, `stop_reason` and `cycle`; ingest drops every store on refusal (`engine.py:1016-1020`) and commits through `_commit_all` (prepare-all then commit-all under one lock, `engine.py:539-561`, called at `1032`). Delete builds stores from the resolved wiring (`engine.py:1150`, namespaces at `430-432`) and commits only for `success` or `not_found` (`1171-1174`). Store primitives: `kv.py:105-136`, `vector.py:504-585`, `graph.py:477-498`; vector `delete_by_ids` buffers until the flush. Probe on a real HippoRAG ingest: failures injected at graph.prepare, vector prepare, kv.prepare, graph.upsert_node and kv.upsert each left kv empty, 0 vectors in all three namespaces, 0 graph labels. A refused-ingest query returns no evidence (`test_ingest_abort.py`). Tests: `tests/seam/test_ingest_abort.py`, `tests/stores/test_prepared_commit.py`, `tests/stores/test_delete_commit_contract.py`, `tests/stores/test_delete_status_commit.py`. Delete atomicity is proved on a fixture v2 wiring because the LightRAG v1 delete stages no v2 writes until M-04 (D-08, deferred to Phase 11). |
| 4 | A node declaring only read effects cannot mutate any store, and every store effect in the vocabulary resolves to a wired store or is refused at parse; no wiring parses and then fails with `StoreNotWiredError` | VERIFIED | `parts_core/__init__.py:53-71` (`EFFECT_TO_STORE`, all 17 effects), `73-101` (allowlists, engine-only set), `113-166` (`_StoreProxy`), `192-205` (`require`). `runner/scheduler.py:243-287` routes every `ctx.stores[...]` access through the table. `validator/parse.py:68, 222-234` refuses `reads_lexical`, `writes_lexical`, `reads_blob` with code `unwired-store-effect`; `engine.py:456-460` makes that `UnparseableWiringError` (422) before any store is built, at `961`, `1137`, `1320`. Probe on read-only handles: `upsert`, `delete`, `index_done_callback`, `drop`, `finalize`, `drop_pending_index_ops` on kv; `upsert_node`, `upsert_edge`, `delete_node`, `delete_edge`, `drop`, `index_done_callback` on graph; and `upsert`, `delete_by_ids`, `index_done_callback` on `select()` of a read vector handle each raised `UndeclaredEffectError`; `get_by_id`, `has_node` still worked; `writes_kv` yielded a writable handle with `index_done_callback` refused; `mutates_store`, `self_storage`, `writes_artifact`, `reads_lexical` raised `UndeclaredEffectError` without reading `raw_stores`. Tests: `tests/runner/test_capability_scoping_modes.py` (33), `tests/runner/test_store_proxy_hardening.py`, `tests/wirings/test_store_effects_wired.py` (26). |
| 5 | Adapters keep their data consistent and refuse bad input by name: half-written Faiss dirs raise corruption, reserved metadata keys refused, no dangling edges after a graph delete, KV buffers isolated, blob digests cannot escape, lexical queries match all terms, quarantined GC has a production caller that reports failures | VERIFIED | Corruption: `vector.py:200-252`; probe: `vector.faiss` alone and `vector.meta.json` alone both raised `VectorStoreCorruptedError`. Reserved keys: `vector.py:106, 341-343`; probe: metadata `id` and `score` raised `ReservedMetadataKeyError`, `get_by_id` returned the real id. STOR-09: probe gave `InvalidTopKError` (a `ValueError`) for `top_k` 0 and -3; `query`, `score_all`, `iter_vectors`, `get_by_id`, `upsert` on an unselected `MultiNamespaceVectorStore` raised `VectorNamespaceNotSelectedError`, and its available list named only the directory holding `vector.faiss`. Graph cascade: `graph.py:381-404, 447-454`; probe: after a flushed `delete_node('x')`, `get_node_edges('x') == []`, `node_degree('y') == 0`, igraph edge count 0; `upsert_edge('p','q')` on missing endpoints created both nodes and 1 edge. KV isolation: probe showed the buffered record unchanged after the caller mutated both the source dict and a returned copy; `is_empty()` was True when every row was pending deletion. Blob and lexical stores: `stores/lexical.py`, `stores/blob.py` and `registry_artifact/` do not exist; `tests/test_removed_stores_absent.py` (5) passes. GC: `launcher/gc_namespaces.py:1-60` (takes `store_lock`, accepts only `quarantined-*`, validates all tokens first), `namespaces.py:106-132` (`NamespaceGCError`, no `ignore_errors`), docstring corrected at `namespaces.py:15-20`. Tests: 14 in `tests/test_namespaces_gc.py`, plus the store test files listed below. |

**Score:** 5/5 truths verified (0 present, behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `databasise/stores/graph.py` | shared client registry, cascade, prepare/commit | VERIFIED | 552 lines; used by `engine._build_stores`, `probes.probe_graph`, `parity/run_arm.py` |
| `databasise/stores/vector.py` | snapshot cache, corruption, reserved keys, buffered delete | VERIFIED | 776 lines |
| `databasise/stores/kv.py` | buffer isolation, prepare/commit | VERIFIED | 157 lines |
| `databasise/stores/probes.py` | read-only health probes | VERIFIED | 126 lines; called from `engine.health` |
| `databasise/parts_core/__init__.py` | `EFFECT_TO_STORE`, allowlist proxies | VERIFIED | consumed by `runner/scheduler.py` and `parity/storage_audit.py` |
| `databasise/seam/engine.py` | atomic ingest/delete, StoreBusy, health, resolve | VERIFIED | 1905 lines |
| `databasise/seam/refusals.py` | `StoreBusyError`, `UnparseableWiringError` | VERIFIED | in `__all__` and `_REFUSAL_FACTORIES` |
| `databasise/launcher/gc_namespaces.py` | operator GC CLI | VERIFIED | 14 tests |
| `databasise/validator/parse.py` | `unwired-store-effect` violation | VERIFIED | `parse.py:68, 222-234` |
| `stores/lexical.py`, `stores/blob.py`, `registry_artifact/` | removed (D-15) | VERIFIED | absent from the tree; absence test passes |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `engine._build_stores` | `GraphStoreBusyError` | except clause | WIRED | `engine.py:440-444` |
| `rest._status_for` | `StoreBusyError` | isinstance branch | WIRED | `rest.py:140`, 409 observed over HTTP |
| `engine.ingest` | `_drop_pending` / `_commit_all` | refusal and success paths | WIRED | `engine.py:1016-1032` |
| `engine.delete_document` | `store_namespaces` | `_build_stores(resolved)` | WIRED | `engine.py:1150` |
| `scheduler._ScopedStoresView` | `EFFECT_TO_STORE` | table lookup | WIRED | `scheduler.py:277-284` |
| `engine.health` | `probes._PROBES` | `_HEALTH_PROBES` list | WIRED | `engine.py:1272-1275`, drift test passes |
| `parse_wiring` | `UnparseableWiringError` | `_refuse_unparseable` | WIRED | `engine.py:961, 1137, 1320` |
| `engine.resolve_evidence` | `load_committed` cache | `MultiNamespaceVectorStore` | WIRED | `engine.py:1455`, probe shows one hash per index change |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `HealthReport.stores` | per-namespace state | file and client probes on disk | Yes (probe: `absent`, `ok`, `corrupted`, `busy` each observed) | FLOWING |
| `resolve_evidence` record | vector entry metadata | committed Faiss snapshot | Yes (new content seen after a rewrite) | FLOWING |

### Behavioral Spot-Checks

All probes were written to `/tmp/claude-1000/-home-chris-coding-Databasise-2-0-fully-agnostic-system/32d1701b-4256-409c-a5a7-e305cc822f40/scratchpad/` and nothing was left in the repo.

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| 17 phase test files plus 4 hardening files | `cd databasise && .venv/bin/pytest -q -p no:cacheprovider <21 files>` | 221 passed in 30.7 s | PASS |
| In-process overlap: ingest parked mid-run + query + health + resolve | `probe_sc1.py` | query, health, resolve, ingest all OK; health showed `graph:hipporag-graph = ok` | PASS |
| Second OS process holds `hipporag-graph` | `probe_sc1.py`, `probe_sc1b.py` | `POST /query` 409, `POST /documents` 409, `/health` 200 with `busy`; no path in body | PASS |
| Second OS process holds `chunk_entity_relation` | `probe_sc1b.py` | ingest 409, `DELETE /documents/d1` 409, `/health` 200 | PASS |
| Refused HippoRAG ingest, five failure points | `probe_sc3.py` | kv empty, 0 vectors in 3 namespaces, 0 graph labels each time | PASS |
| Commit-phase failure on the last store | `probe_sc3.py` | refused `StoreFault`; kv non-empty, 4 vectors, 0 graph labels | Accepted residual (D-07) |
| Read-only handles and effect table | `probe_sc45.py` | 15 mutators refused, reads work | PASS |
| Adapter refusals and cascade | `probe_sc45.py`, `probe_sc5b.py` | named errors as listed in criterion 5 | PASS |
| Health and resolve | `probe_sc2.py` | as listed in criterion 2 | PASS |

### Probe Execution

No `probe-*.sh` scripts are declared by the phase. Step 7c: not applicable.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ----------- | ----------- | ------ | -------- |
| STOR-01 | 10-01 | Named outcome for a held graph | SATISFIED | `graph.py:135-173`, `engine.py:440-444`, `rest.py:140`; `test_graph_lock.py` (6) + probe |
| STOR-02 | 10-01 | Failed open finalizes opened stores | SATISFIED | `engine.py:973, 1150, 1331`; `test_build_stores_cleanup.py` (6) |
| STOR-03 | 10-06 | Resolve opens only the vector namespace, reads once | SATISFIED | `engine.py:1439-1460`, `vector.py:157-248`; `test_evidence_resolve_stores.py` (8) + probe |
| STOR-04 | 10-07 | Read-only health | SATISFIED | `engine.py:1258-1293`, `probes.py`; `test_health_probe.py` (9) + probe |
| STOR-05 | 10-08 | Per-mode capability scoping | SATISFIED | `parts_core/__init__.py:53-205`; `test_capability_scoping_modes.py` (33) + probe |
| STOR-06 | 10-04, 10-05 | Failed ingest commits nothing | SATISFIED | `engine.py:539-605, 1016-1032`; `test_ingest_abort.py`, `test_prepared_commit.py` + probe |
| STOR-07 | 10-10 | Delete uses declared namespaces and is atomic | SATISFIED | `engine.py:1146-1177`; `test_delete_commit_contract.py` (11). Fixture wiring; v1 delete deferred to M-04 per D-08 |
| STOR-08 | 10-06 | Half-written Faiss pair is corruption | SATISFIED | `vector.py:200-252`, `engine.py:1456-1457`; `test_vector_crash_window.py` (9) + probe |
| STOR-09 | 10-11 | Named refusals for invalid vector input | SATISFIED | `vector.py:121, 646`; `test_vector_validation.py` (6) + probe |
| STOR-10 | 10-09 | No dangling edges | SATISFIED | `graph.py:385-404, 447-454`; `test_graph_delete_cascade.py` (8) + probe |
| STOR-11 | 10-09 | KV buffer isolation | SATISFIED | `kv.py:69-103`; `test_kv_buffer_isolation.py` (6) + probe |
| STOR-12 | 10-02, 10-12 | Store effects wired or refused at parse | SATISFIED | `parse.py:68, 222-234`, `engine.py:456-460`; `test_store_effects_wired.py` (26) |
| STOR-13 | 10-02 | Blob digest safety | SATISFIED by removal (D-15); the store no longer exists | `test_removed_stores_absent.py` (5) |
| STOR-14 | 10-02 | Lexical AND query | SATISFIED by removal (D-15) | same test |
| STOR-15 | 10-03 | GC has a production caller, reports failures | SATISFIED (D-16 exception: operator CLI, not retire) | `gc_namespaces.py`, `namespaces.py:106-132`; `test_namespaces_gc.py` (14) |
| STOR-16 | 10-11 | Reserved metadata keys refused | SATISFIED | `vector.py:106, 341-343`; `test_vector_reserved_keys.py` (5) + probe |

No orphaned requirements: REQUIREMENTS.md maps STOR-01 to STOR-16 to Phase 10 and every ID is claimed by a plan. Ledger STOR rows showing `open` with empty `test_ref`, RUN-11 deferral and seam authentication are outside this report (known context).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| none | - | `TBD`, `FIXME`, `XXX` scan over the touched store, engine, scheduler, parse, namespaces and launcher files | - | No debt markers |

### Advisory (open review items and one accepted limit)

| # | Finding | Category | Why Advisory |
| - | ------- | -------- | ------------ |
| A1 | Commit-phase failure on the last store leaves earlier stores committed (reproduced) | other | D-07 documents it; SC3 stands as written for the prepare phase, which is where a store can fail on bad data. Window sits between `commit_prepared` calls (kv, vector, graph in that order) |
| A2 | IN-01: proxy bypass routes, node ids in `stop_reason` (Phase 13), RocksDB `data/` rotation, `_is_store_fault` classification by top-level type | other | Recorded limits, not defects |
| A3 | IN-02: `no such table` plus `-wal` leniency in `probe_kv`; kv `busy` is unreachable because the probe is immutable | other | Health accuracy only |
| A4 | IN-03: a directory named `kv.sqlite3` is reported `absent` | other | Health accuracy only; one-line fix recorded in the review |
| A5 | IN-04: drift test comment overstates what it checks | other | Test wording |
| A6 | IN-05: finalize loops stop at the first failing `finalize` (tracer composer; the same loop shape is in `engine.py:1037-1039, 1175-1177, 1344-1346`) | other | `SqliteKVStore.finalize` is `conn.close()` and does not raise in practice; a raise would leave the graph client referenced |
| A7 | IN-06: misleading corruption log text for vanished files; `_committed_signature` catches only `FileNotFoundError` | other | Server log only; needs a permission change after open |
| A8 | `trace.db*` files are created by the `Databasise` constructor, not by health | other | STOR-04 concerns store files created by health; unchanged by this phase |
| A9 | A fresh install reports `degraded` with every store `absent` | other | By design (D-14); consumers read the map |

None of these breaks a success criterion.

### Human Verification Required

None. Concurrency (SC1) and atomicity (SC3) are behavior-dependent truths, and each has a passing behavioral test plus an independent probe above, so none is left as present-but-unexercised.

### Gaps Summary

No gaps. All five success criteria and all 16 requirements are met in the code at HEAD. The one place where the wording "none of them" does not hold is a failure inside the commit sequence after an earlier store has already committed. D-07 chose that trade-off and documents it in the engine docstring; it is listed as A1 so the owner sees it, and fixing it would need a recovery record or a single transactional backend rather than a code patch in this phase.

---

_Verified: 2026-10-17_
_Verifier: Claude (gsd-verifier)_
