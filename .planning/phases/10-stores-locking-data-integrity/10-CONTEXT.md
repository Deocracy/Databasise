# Phase 10: Stores, Locking & Data Integrity - Context

**Gathered:** 2026-10-17
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous). The owner was shown four grey areas, each with a recommended option, and answered "You decide" for all four. Every decision below is Claude's choice on the owner's delegation. Each is recorded as a numbered decision, so planning and verification treat it as binding.

<domain>
## Phase Boundary

Concurrent engine calls on one store root produce named outcomes instead of 500s, and every store commits all of a run's writes or none of them. Requirements: STOR-01 to STOR-16.

This phase changes:
- store handle sharing and the store-busy refusal;
- the Faiss read cache;
- read-only health;
- capability-scoped store handles;
- cross-store commit;
- the graph, KV and vector adapter semantics;
- the fate of the unwired lexical, blob and artifact stores;
- quarantined-namespace GC.

It does NOT carry the opaque LightRAG v1 ingest and delete into v2 stores. That is M-04, Phase 11. It also does not add seam authentication, which is an open owner decision for the CONN phases.

</domain>

<decisions>
## Implementation Decisions

### A. Concurrency and handles (STOR-01, STOR-02, STOR-03)

- **D-01 (STOR-01):** In one process, calls on the same `graph.cozo` path share one reference-counted pycozo `Client`. A class-level registry in `stores/graph.py` keys it by resolved path, so a directly opened `CozoGraphStore` shares it too.
  - Each call keeps its own `CozoGraphStore` instance with its own pending buffers. One call's uncommitted writes are never visible to another call, and one call's abort never drops another call's writes.
  - Flushes on one path are serialized. The last release closes the client.
  - If opening the client still fails with RocksDB's "lock hold" error (a second OS process, or any open that cannot share), the engine raises a new named refusal, `StoreBusyError(store_kind="graph")`, before any node runs. Its public fields never name an internal namespace or path.
  - The research must spike whether one pycozo `Client` is safe across concurrent executor threads. If it is not, access through the shared client is serialized by a per-path lock. That changes throughput, not the decision.
- **D-02 (STOR-01 status):** `StoreBusyError` maps to **HTTP 409** through a third branch in `rest.py` `_status_for`.
  - STOR-01 asks for a 4xx.
  - 422 would tell the caller to change their input.
  - 503 is reserved for v1 being unavailable (Phase 9 D-04).
  - 423 is WebDAV-specific.
  - MCP returns the same refusal JSON with `isError`, following Phase 9 D-02.
  - The refusal joins the `refusals.py` `__all__` catalogue and `_REFUSAL_FACTORIES`.
- **D-03 (G-36):** settled by Phase 8. Parity CLIs take the per-store-root lock, and `--workers` must be 1. Nothing new here.
- **D-04 (STOR-02):** store construction moves inside the try/finally of `ingest`, `delete_document`, `_execute` and `resolve_evidence`. A failed open finalizes every store already opened in that call. The same rule applies to `parity/run_arm.py`'s own store builder.
- **D-05 (STOR-03):** a process-level cache holds the read-only **committed snapshot** of a Faiss namespace (index plus entries). It does not hold store objects.
  - The key is `(resolved path, st_ino, st_mtime_ns, st_size)` of both `vector.faiss` and `vector.meta.json`.
  - Two `stat` calls per resolve replace a full read and hash. `_persist`'s `os.replace` changes the inode, so in-process flushes invalidate the cache with no hook.
  - Writers still construct fresh per-call instances.
  - Resolve opens only the named vector namespace, as Phase 9 already does. The cache must not create directories.

### B. Atomicity and delete (STOR-06, STOR-07)

- **D-06 (STOR-06):** every `node_exceptions` entry counts, not only the result node's. So does a run that stopped early (`stop_reason` set or `partial` true). In either case the engine calls `drop_pending_index_ops` on every store and raises `ForeignEngineRefusalError`. Such a run commits nothing.
- **D-07 (STOR-06 flush):** a successful run commits through **prepare-all, then commit-all**.
  1. Prepare: kv executes inside an uncommitted sqlite transaction; vector writes its `.tmp` file pair; graph stages its `multi_transact` without committing.
  2. Commit only after all three are prepared. A prepare failure aborts all three, commits nothing, and raises `ForeignEngineRefusalError`.
  - The remaining commit-phase window is documented in the engine docstring. A crash between the commits of different stores, or between the vector store's two `os.replace` calls, is caught by the vector checksum.
  - Success criterion 3 stands as written, with no amendment.
- **D-08 (STOR-07):** `delete_document` builds its stores from the resolved wiring's `store_namespaces`. It flushes when the delete succeeds and drops pending ops when it fails. `FaissVectorStore.delete_by_ids` buffers until `index_done_callback`, so a drop reverts it.
  - This covers v2 stores. The opaque LightRAG v1 delete mutates v1 only, until M-04 in Phase 11. Tests for "after delete, kv, vector and graph are gone" use a v2-store wiring such as HippoRAG.

### C. Store adapter semantics and scoping (STOR-05, STOR-08 to STOR-11, STOR-16)

- **D-09 (STOR-05):** an explicit `EFFECT_TO_STORE` table replaces suffix splitting, in `parts_core/__init__.py` and `runner/scheduler.py`.
  - `reads_kv`, `reads_vector` and `reads_graph` return a **read-only proxy built on an allowlist**:
    - kv: `get_by_id`, `get_by_ids`, `filter_keys`, `is_empty`.
    - vector: `select`, which returns a read proxy, `query`, `score_all`, `self_knn`, `iter_vectors`, `get_by_id`.
    - graph: `has_node`, `get_node`, `has_edge`, `get_edge`, `node_degree`, `get_node_edges`, `export_to_igraph`, `get_all_labels`.
  - Every other attribute raises `UndeclaredEffectError`. `writes_X` returns the writable handle.
  - Lifecycle methods (`index_done_callback`, `drop_pending_index_ops`, `finalize`, `drop`) are engine-only on every handle.
  - `mutates_store`, `self_storage`, `writes_artifact`, `calls_*`, `net` and `fs` have no backing store. `require()` refuses them with `UndeclaredEffectError` ("no store backs effect X") and never reads `raw_stores`.
  - The same table applies to the parity builder.
- **D-10 (STOR-10):** `delete_node` **cascades** to incident edges, matching the v1 Cozo adapter (`v1/lightrag/kg/cozo_impl.py:566-575`). Buffered incident edges are dropped at once, and disk-side incident edges are removed in the same `multi_transact` at flush. `upsert_edge` with a missing endpoint **auto-creates** that node with `{}` attributes (networkx semantics). No path ever leaves a dangling edge.
- **D-11 (STOR-16):** `FaissVectorStore.upsert` refuses metadata keys `id` and `score` with a named `ValueError` subclass in `stores/vector.py`, `ReservedMetadataKeyError(keys)`, in the house style of `VectorStoreCorruptedError`. `import_index` strips them. The result shape does not change.
- **D-12 (STOR-08, STOR-09, STOR-11):** these follow the requirement text exactly.
  - Store-level refusals (the STOR-09 `ValueError` subclass, `VectorNamespaceNotSelectedError`, `ReservedMetadataKeyError`, `VectorStoreCorruptedError`) stay in `stores/`. They are not part of the seam catalogue.
  - A store refusal that reaches a caller through a seam method keeps its existing mapping. Evidence resolve against a corrupted namespace returns the existing corruption refusal (STOR-08).
- **D-13 (store faults inside nodes):** a store error raised inside a node, or during the prepare or commit flush, surfaces as `ForeignEngineRefusalError` with a new `failure_class="StoreFault"`. It no longer carries the v1-flavoured classes, and the cause is logged server-side once (Phase 9 D-04). The code comment and message wording must not call a store fault a v1 failure.

### D. Health, unwired stores and GC (STOR-04, STOR-12 to STOR-15)

- **D-14 (STOR-04, settled once for LRAG-13, LRAG-14 and HIPP-15):** `GET /health` is read-only and probes every namespace of every shipped wiring (the LightRAG and HippoRAG kv, graph and vector namespaces) from one static list.
  - Probes create nothing: a directory existence check; sqlite opened `mode=ro`; graph read through the D-01 shared client without `_ensure_relations`; and the Faiss file pair plus checksum.
  - `HealthReport.stores` becomes `dict[str, Literal["ok", "absent", "corrupted", "busy"]]`. The top-level `status` stays `ok | degraded`, and any non-`ok` store makes it `degraded`.
  - There is no separate "not initialized" state. A fresh install is all `absent`, which a consumer can read from the map.
  - This is a §18 `HealthReport` shape change, made now before any GUI consumer exists. The REST and MCP schemas and docs are updated with it, and LRAG-13/14 and HIPP-15 build on it.
- **D-15 (STOR-12 with TOOL-17):** **delete** `stores/lexical.py`, `stores/blob.py` and `registry_artifact/` with their tests, and add a grep test that nothing imports them. This is TOOL-17's "removed" branch, so STOR-13 and STOR-14 are satisfied by removal: their stores no longer exist.
  - **All 17 effects stay** in the vocabulary, so CONTRACT §2 is not amended.
  - `parse_wiring` adds a `Violation` code `unwired-store-effect` for any node declaring `reads_lexical`, `writes_lexical` or `reads_blob`. Violations are accumulated, per `validator/parse.py`.
  - `writes_artifact` becomes a declaration-only marker that keeps its blast-radius and resumability meaning, with no store key (D-09).
  - A wiring refused this way never parses and fails later. It must reach a seam caller as a named refusal, never a 500. Shipped wirings declare none of these effects.
  - The planner reconciles the STOR-12 and TOOL-17 lists of parts declaring `writes_artifact` (`embedder-index`, `graph-augment-persist`, `full-ingest`, `graph-materializer`) and records which keep the marker.
- **D-16 (STOR-15, requirement wording amended on the owner's delegation):**
  - The production caller of `gc_namespace` is an **operator GC CLI**, in the style of the parity CLIs. It takes the per-store-root lock and accepts only `quarantined-*` tokens. There is no trigger from `retire()`: no generation-to-namespace record exists, and D-15 deletes the registry that could have held one.
  - `gc_namespace` raises a named `NamespaceGCError` for any `OSError` other than `FileNotFoundError`. `ignore_errors=True` is removed.
  - The `namespaces.py` D-07 docstring is corrected to say that seam stores use fixed names and only `parity/import_index.py` calls `derive_namespace`.
  - `.planning/REQUIREMENTS.md` STOR-15 gets an exception clause: "production caller" means the operator GC CLI, not instance retirement.

### Claude's Discretion
- Exact class placement and message wording for `StoreBusyError`, `ReservedMetadataKeyError` and `NamespaceGCError`, following `refusals.py` and `stores/` house style.
- The structure of the shared-client registry and the proxy implementation, provided the allowlists above hold.
- The GC CLI's name and argument shape.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md`: the Phase 10 goal, success criteria and owner-decision list.
- `.planning/REQUIREMENTS.md`: STOR-01 to STOR-16, each with its named test and source defects. Also TOOL-17 (Phase 15), and LRAG-13/14 and HIPP-15 for health.
- `docs/gui/DEFECTS.json`: the source defect uids, including G-01, G-20, G-36 and ST-01 to ST-17.
- `docs/system-model/CONTRACT.md`: §2, the 17-effect vocabulary (frozen), and §18, the seam and HealthReport.
- `.planning/phases/08-run-the-engine/08-CONTEXT.md`: D-01 to D-04, the store lock and one worker per store.
- `.planning/phases/09-inputs-errors-security/09-CONTEXT.md`: D-01 to D-04, the refusal shape, status map and the one machine-fault type.
- `v1/lightrag/kg/cozo_impl.py:566-575`: the v1 delete cascade that D-10 matches.

</canonical_refs>

<code_context>
## Existing Code Insights

- `stores/graph.py:102-113`: a Cozo client opened per instance, with pending buffers on the instance. Lines 190-224 are degree and edges, which ignore deletes. Lines 263-267 are the igraph export, which skips dangling edges. Lines 291-300 are upsert_edge and delete_node, which have no checks or cascade.
- `stores/vector.py`: lines 116-137 are the init (mkdir, then read, hash and load). Results are built as `{"id","score",**metadata}` at 235/267/312/338. `_persist` at 427-428 uses `os.replace`.
- `seam/engine.py`: lines 361-388 are `_build_stores`, which is eager and runs outside the try at 818/991/1174. Lines 450-452 wrap a node failure as a v1 fault. Lines 871-872 are the unconditional flush. Lines 1100-1120 are health, which constructs stores.
- `parts_core/__init__.py:64-71` and `runner/scheduler.py:270-277` map effects to stores by splitting the name suffix.
- `validator/parse.py`: violations accumulate. `validator/blast_radius.py:54` and `scheduler.py:167-176,648` key on `writes_artifact`.
- `store_lock.py`: the per-store-root lock (Phase 8). `launcher/serve_rest.py:74` enforces one worker.
- Commit messages need a `phase/10` trailer. Test files that carry a BAK ledger `test_ref` need the owner's `grant-check-edit` before a plan edits them. That is RUN-* now, and SEAM-* once set: test_rest_corpus_endpoints.py, test_tool_growth_invariant.py, the Phase 9 SEAM files and others.

</code_context>

<specifics>
## Specific Ideas

There are no owner requirements beyond the decisions above. The REQUIREMENTS.md test descriptions for each STOR ID are the acceptance contract, with the D-16 wording exception for STOR-15.

</specifics>

<deferred>
## Deferred Ideas

- Carrying the LightRAG v1 ingest and delete into v2 stores (M-04, Phase 11). Until then, STOR-06/07 v2-store assertions use HippoRAG wirings.
- A generation-to-namespace record and GC on retire. Revisit only if a future phase reintroduces an artifact registry.
- The crash-orphan reaper for staged uploads (Phase 9, deferred).

</deferred>

---

*Phase: 10-stores-locking-data-integrity*
*Context gathered: 2026-10-17*
