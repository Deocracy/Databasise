# Phase 10: Stores, Locking & Data Integrity - Research

**Researched:** 2026-10-17
**Domain:** Embedded store adapters (pycozo 0.7.6 / RocksDB, Faiss, sqlite3), in-process handle sharing, cross-store commit, capability-scoped handles, read-only health
**Confidence:** HIGH (all behaviour claims about pycozo, sqlite3 and the shipped code were measured or read this session; the remaining ASSUMED items are listed in the Assumptions Log)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

(Copied verbatim from `10-CONTEXT.md` `## Implementation Decisions`. The owner answered "You decide" on all four grey areas, so D-01..D-16 are Claude's choices on delegation and are binding for planning and verification.)

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

### Deferred Ideas (OUT OF SCOPE)
- Carrying the LightRAG v1 ingest and delete into v2 stores (M-04, Phase 11). Until then, STOR-06/07 v2-store assertions use HippoRAG wirings.
- A generation-to-namespace record and GC on retire. Revisit only if a future phase reintroduces an artifact registry.
- The crash-orphan reaper for staged uploads (Phase 9, deferred).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STOR-01 | Overlapping calls on one Cozo namespace never 500; shared handle or named refusal; second OS process gets the same refusal | Spike R1-R6 (shared Client is thread-safe; exact error texts; per-key write locks with 1 s timeout force serialized flush windows); Pattern 1; Pitfalls 1, 8, 17 |
| STOR-02 | A failed store open finalizes every store already opened; no leaked sqlite connection | Pattern 3 (stores scope); Pitfall 9 (test monkeypatch contract, staged-upload ordering) |
| STOR-03 | `/evidence/resolve` opens only the named vector namespace; index read and hashed once until it changes | Pattern 5 (snapshot cache); Pitfall 4 (two-rename window) |
| STOR-04 | `/health` read-only, accurate | Pattern 6 (probes); spike S1-S3 (Cozo creates files on open, sqlite `mode=ro`, `immutable=True`); Consumers table |
| STOR-05 | Capability scoping per access mode | Pattern 4 (EFFECT_TO_STORE + proxy); Allowlist audit table; Pitfalls 5, 6 |
| STOR-06 | A failed ingest commits nothing | Pattern 2 (prepare/commit anchors); spike R7-R10; Pitfalls 2, 3 |
| STOR-07 | Delete uses the wiring's namespaces; vector delete buffered | Pattern 2; Pitfall 14, 22 (no HippoRAG delete wiring exists) |
| STOR-08 | Half-written Faiss dir raises corruption | Verified live (`only vector.faiss -> opens, _index: None`); Pitfall 15 |
| STOR-09 | Named errors for invalid vector input | Verified live (`top_k=0 -> AssertionError`); Pitfalls 12, 13, 15 |
| STOR-10 | Graph edges stay consistent with nodes | Spike R9 (cascade `:rm` inside one multi_transact works); Pattern 7 |
| STOR-11 | KV buffer isolation | Code anchors (kv.py:68, kv.py:86, kv.py:94-99); Pattern 7 |
| STOR-12 | Every store effect resolves or is refused at parse | D-15 blast-radius section; `writes_artifact` reconciliation; Pitfall 18 |
| STOR-13 | Blob digest validation | Satisfied by removal (D-15) |
| STOR-14 | Lexical AND query | Satisfied by removal (D-15) |
| STOR-15 | Quarantined-namespace GC is real | Pattern 8; Pitfall 20; Security Domain |
| STOR-16 | Reserved Faiss metadata keys refused | Pattern 7; code anchors (vector.py:235/267/312/338 build `{"id","score",**metadata}`) |
</phase_requirements>

## Summary

Every concurrency and atomicity question the decisions left open was answered by measurement. **One pycozo `Client` is safe across concurrent executor threads** (16 threads x 40 write-then-read loops: 0 errors, 640/640 rows; 8 concurrent write `multi_transact` on distinct keys: 0 errors). The decision to share one reference-counted `Client` per resolved path stands, and no per-path *read* lock is needed. **Write conflicts are not free, though:** RocksDB takes pessimistic per-key locks, and a second transaction (or plain `run`) that writes a key already written by an open, uncommitted write transaction blocks for exactly 1.00 s and then fails with `rocksdb::kTimedOut::kLockTimeout`. D-07's prepare-all/commit-all keeps a graph transaction open across the other stores' prepare, so two overlapping flushes on one path **must** be serialized for the whole prepare-to-commit window, not just inside `_do_flush`. The same is true of sqlite (a second writer gets `database is locked` after the 5 s default busy timeout, and `SqliteKVStore` runs sqlite calls synchronously on the event-loop thread, so an un-awaited contention would stall the very coroutine that must release the lock).

`multi_transact(write=True)` supports exactly the staged commit/abort D-07 needs: staged writes are invisible to plain `run()` until `commit()`, `commit()` works from a different thread than the one that opened the transaction, `abort()` leaves nothing, and a new write transaction can be opened straight after an abort. Concrete prepare/commit/abort mechanisms and file:line anchors for all three stores are in Pattern 2. The second-open error is a plain `builtins.Exception` (not `QueryException`) whose first argument is a string; the in-process text contains `lock hold by current process` and the cross-process text contains `While lock file`, and **both embed the absolute path**, so the refusal must be built without forwarding the message.

Four findings change the plan's shape beyond the decisions: (1) a shipped part, `parts_core/hipporag/graph_augment_persist.py:84`, calls `await graph_store.index_done_callback()` inside the node, which D-09 makes illegal and which would commit the graph before the other stores; it must be removed in this phase. (2) With per-call Faiss instances, two overlapping writers both flush from a stale base and the second `os.replace` silently drops the first writer's vectors (and both use the same fixed `.tmp` names); prepare must rebase on the on-disk state under the flush lock. (3) `stores/` cannot import `seam.refusals` (importing any `databasise.seam.*` module runs `seam/__init__.py`, which imports the engine, which imports the stores), so the store raises a store-level error and the engine translates it into the catalogue `StoreBusyError`. (4) Of the eight ledger-protected test files, **none** needs editing for Phase 10; the files that do need edits (health, refusal catalogue, phase-1 acceptance, vector delete) are unprotected.

**Primary recommendation:** Build one `stores_scope` async context manager in the engine (construct incrementally, flush with prepare-all/commit-all under one per-(loop, store root) `asyncio.Lock`, finalize in `finally`) on top of three new lifecycle methods on `StorageNameSpace` (`prepare`, `commit_prepared`, `abort_prepared`, defaulting to `index_done_callback`/`drop_pending_index_ops`), a path-keyed refcounted Cozo `Client` registry, and an `EFFECT_TO_STORE` table with allowlist proxies; delete `lexical`/`blob`/`registry_artifact` first so the rest of the work does not have to carry them.

## Spike Results (D-01) — measured this session

Scripts: `/tmp/claude-1000/-home-chris-coding-Databasise-2-0-fully-agnostic-system/32d1701b-4256-409c-a5a7-e305cc822f40/scratchpad/spike_cozo.py`, `spike_cozo2.py`, `spike3.py`, `spike4.py`. Run with `databasise/.venv/bin/python -I <script>`. Environment: Python 3.12.13, pycozo 0.7.6, cozo-embedded 0.7.6, sqlite 3.53.1, faiss-cpu 1.15.0. Nothing was written to the repo.

| # | Question | Observed output (verbatim where it matters) | Verdict |
|---|----------|---------------------------------------------|---------|
| R1 | One `Client`, 16 threads, 40 put-then-read loops each (distinct keys) | `1. concurrent run(): errors=0 [] nodes=640 (expect 640) t=0.07s` | Safe. No per-path read lock needed. |
| R2 | 8 threads each open a write `multi_transact`, put a distinct key, sleep 50 ms, commit | `2. concurrent write multi_transact x8: errors= 0 [] mt nodes= 8` | Safe. Distinct keys never conflict. |
| R3 | Staged (uncommitted) write visible to a plain `run()`? | `3a. uncommitted staged visible to plain run(): []` | Invisible until commit. |
| R4 | `commit()` from a different thread than the opener | `3c. commit from different thread: ok` | Works. Prepare and commit can be separate executor calls. |
| R5 | `abort()`, then open a new write mt | `4. after abort present: []` and `4b. reopen mt after abort ok` | Works. |
| R6 | Two overlapping write mts / mt vs plain `run` touching the SAME key | `m2 put ERR 1.00s rocksdb::kTimedOut::kLockTimeout`; `plain run put of same key while mt holds it: ERR 1.00s when executing against relation 'nodes'`; a DIFFERENT key: `ok 0.00s` | Pessimistic per-key locks, 1.00 s timeout. A failed statement does not poison the transaction (`m2 commit ok` afterwards, committing nothing). Two write mts that touch different keys never block (`5. second write mt while first open: opened after 0.00s`). |
| R7 | Second open of the same path in the same process | `builtins.Exception` , first arg (a `str`): `rocksdb::kIOError::kNone\n\n  × RocksDB error: IO error: lock hold by current process, acquire time 1792269192 acquiring thread 138498526299968: /tmp/cozospike_sxssw217/graph.cozo/data/LOCK: No locks available\n  help: This error is usually outside Cozo's control` | Detect with `"kIOError" in text and "lock hold by current process" in text`. Text embeds the absolute path. |
| R8 | Second open from another OS process | `builtins.Exception` : `rocksdb::kIOError::kNone\n\n  × RocksDB error: IO error: While lock file: /tmp/cozospike_sxssw217/graph.cozo/data/LOCK: Resource temporarily unavailable` | Detect with `"kIOError" in text and "While lock file" in text`. Embeds the absolute path. |
| R9 | Cascade inside one mt | `cascade: edges left: [] x present: []` after running `?[src, tgt] := *edges{src, tgt}, src = $id or tgt = $id :rm edges {src, tgt}` then `:rm nodes` in one `multi_transact` | D-10's disk-side cascade works in the flush transaction. |
| R10 | Misuse | `run after commit ERR ... sending on a disconnected channel`; `double commit ERR 'sending on a disconnected channel'`; `commit after close ok` (a mt survives `Client.close()`); after `close()`, `run` gives `QueryException {"ok":false,"message":"database closed"}`; reopen after `close()` works | A prepared transaction must be committed or aborted exactly once; the refcount must not reach zero while a prepared transaction is open. |
| S1 | `Client("rocksdb", missing_path)` | `exists: True ['data', 'manifest']`, `::relations: []` | **Opening creates the database.** Health must test existence before opening. |
| S2 | Read-only query: `c.run(script, {}, True)` (`immutable`) | read ok; write refused with `write lock required for read-only query` | `immutable=True` is a usable read-only guard for probes. |
| S3 | `sqlite3.connect("file:...kv.sqlite3?mode=ro", uri=True)` | missing file: `OperationalError unable to open database file | created: False`; against a WAL db with an open uncommitted writer it reads `[(1,)]` | `mode=ro` creates nothing and does not block on a writer. |
| S4 | sqlite prepared transaction | `BEGIN IMMEDIATE` -> `in_transaction True`, INSERT stays in the same transaction; a second connection's `BEGIN IMMEDIATE` -> `OperationalError database is locked`; `PRAGMA busy_timeout` default `5000` ms | `BEGIN IMMEDIATE` in the prepare step takes the write lock up front, so contention surfaces at prepare (before anything is committed). |
| S5 | `pandas` | `pandas` is not installed; every `Client(...)` construction logs `` `pandas` feature was requested, but pandas is not installed `` with a traceback via `logger.exception` | Pass `dataframe=False` when constructing the shared client; `_cozo_rows` already handles the dict shape (`stores/graph.py:68-75`). |

**State whether `multi_transact` supports staged commit/abort as D-07 needs:** yes (R3-R5). The one constraint is R6: a staged transaction holds key locks, so any other writer to the same keys fails after 1.00 s until it is committed or aborted.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Shared Cozo client, refcount, per-path flush serialization | Database / Storage (`stores/graph.py`) | — | Direct `CozoGraphStore` users (tests, parity, GC) must share it too (D-01). |
| `StoreBusyError` translation and HTTP 409 | API / Backend (`seam/engine.py`, `seam/refusals.py`, `seam/rest.py`) | Database / Storage raises the store-level error | `stores/` cannot import `seam.refusals` (circular import, Pitfall 8). |
| Prepare-all / commit-all, abort on failure | API / Backend (engine flush helper) | Database / Storage (three new lifecycle methods) | Only the engine sees all three stores of a run. |
| Read-only proxies, `EFFECT_TO_STORE` | Runner (`parts_core/__init__.py`, `runner/scheduler.py`) | — | Capability scoping is a runner/part-boundary concern (CONTRACT §2). |
| Faiss committed-snapshot cache | Database / Storage (`stores/vector.py`) | API / Backend (`engine.resolve_evidence` is the caller) | Cache key is file stat state; callers never see it. |
| Read-only health probes | API / Backend (`engine.health`) | Database / Storage exposes probe helpers | Probes must not create files, which the constructors do. |
| Wiring refusal for unwired store effects | Validator (`validator/parse.py`) | API / Backend (engine converts the parse report to a seam refusal) | `parse_wiring` accumulates violations; the engine must not let `WiringRefusedError` (a `ValueError`) surface as a 500. |
| Quarantined-namespace GC | Operator CLI (new module under `launcher/`) | `namespaces.gc_namespace` | Not reachable over REST/MCP (D-16). |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pycozo / cozo-embedded | 0.7.6 (pinned exactly in `pyproject.toml`) [VERIFIED: importlib.metadata this session] | Graph store; `Client.run`, `Client.multi_transact`, `MultiTransact.commit/abort` | Architecture-frozen (`stores/graph.py:7-16`). |
| faiss-cpu | 1.15.0 installed (pyproject range `>=1.7.0,<2.0.0`) [VERIFIED: importlib.metadata] | Vector store | Existing. |
| sqlite3 (stdlib) | SQLite 3.53.1 [VERIFIED: sqlite3.sqlite_version] | KV store; `BEGIN IMMEDIATE` prepare, `mode=ro` probes | Existing. |
| pytest / pytest-asyncio | 9.1.1 / 1.4.0, `asyncio_mode = "auto"` [VERIFIED: pyproject.toml:109-113] | Tests | Existing. |

### Supporting
Python stdlib only: `threading`, `asyncio`, `os`, `contextlib`, `weakref`, `shutil`, `argparse`. No new dependency is needed for any decision.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Engine-level `asyncio.Lock` for the flush window | Only a `threading.Lock` per path inside the stores | Store-level locks held across two executor calls would pin pool threads and cannot cover the synchronous sqlite calls on the event-loop thread (Pitfall 2). Use both: asyncio lock in the engine, `threading.Lock` per path in the registry as the backstop for direct users. |

**Installation:** none. **Version verification:** versions above were read from the installed venv; there is nothing to install.

## Package Legitimacy Audit

No external packages are added, removed or upgraded by this phase (stdlib plus already-pinned dependencies). Packages removed from the dependency graph: none (`registry_artifact` is first-party). Audit table: not applicable.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                 REST /query /compare /evidence/resolve /health  DELETE /documents  POST /documents
                 MCP  query compare resolve status ingest delete
                                  |
                                  v
                       seam/engine.py  Databasise.*
                                  |
        +-------------------------+----------------------------+
        |                         |                            |
   read paths                write paths                  health()
 (_execute_resolved)      (ingest, delete_document)     (static namespace list)
        |                         |                            |
        |                  resolve wiring -> parse_wiring      |  for each probe: exists? -> open ro
        |                  (violations -> named refusal)       |  kv: sqlite mode=ro
        v                         v                            |  graph: shared client, immutable read
  async with stores_scope(root, workspace, resolved)  <--------+  vector: committed-snapshot cache
   |  build kv -> vector -> graph INCREMENTALLY into one dict
   |  (graph open: registry.acquire(path); lock error -> GraphStoreBusyError -> StoreBusyError 409)
   |  finally: finalize every store that was opened
        |
        v
  scheduler.run_wiring(parsed, stores)  -- each node gets ScopedStoresView
        |                                   EFFECT_TO_STORE[effect] -> (kind, mode)
        |                                   mode r -> allowlist proxy (UndeclaredEffectError on anything else)
        |                                   mode w -> writable handle ; lifecycle methods engine-only
        v
  scheduled = {results, node_exceptions, partial, stop_reason, ...}
        |
   clean? (no node_exceptions, not partial, no stop_reason)
     no  -> drop_pending_index_ops on all stores -> ForeignEngineRefusalError(failure_class=...)
     yes -> async with flush_lock[(loop, root)]:
              prepare(kv: BEGIN IMMEDIATE + DML ; vector: write .tmp pair (rebased) ; graph: multi_transact, no commit)
              any prepare fails -> abort_prepared on all -> ForeignEngineRefusalError(StoreFault)
              commit_prepared(kv.commit ; vector os.replace x2 ; graph mt.commit)
```

### Recommended Project Structure
```
databasise/
├── stores/
│   ├── base.py          # + prepare / commit_prepared / abort_prepared defaults
│   ├── graph.py         # + _ClientRegistry, GraphStoreBusyError, cascade, prepare/commit/abort
│   ├── kv.py            # + copies, is_empty fix, prepare/commit/abort
│   ├── vector.py        # + ReservedMetadataKeyError, buffered delete, validation, prepare/commit/abort
│   └── snapshot.py      # NEW  committed-snapshot cache + read-only probe helpers (no mkdir)
├── parts_core/__init__.py   # EFFECT_TO_STORE, ReadOnlyProxy, CapabilityScopedStores.require
├── runner/scheduler.py      # _ScopedStoresView uses EFFECT_TO_STORE
├── seam/engine.py           # stores_scope, flush helper, health probes
├── seam/refusals.py         # + StoreBusyError ; _FOREIGN_FAILURE_CLASSES gets StoreFault wording
├── seam/rest.py             # _status_for 409 branch ; _FAULT_RESPONSES wording
├── validator/{parse,errors}.py  # unwired-store-effect
├── namespaces.py            # NamespaceGCError, gc_namespace, corrected docstring
└── launcher/gc_namespaces.py # NEW operator CLI (name is discretionary)
```
Deleted: `stores/lexical.py`, `stores/blob.py`, `registry_artifact/`, `tests/stores/test_lexical.py`, `tests/stores/test_blob.py`, `tests/registry_artifact/`.

### Pattern 1: Reference-counted Cozo client registry (D-01)
**What:** class-level `dict[str, _Entry]` keyed by `str(Path(...).resolve())` of `graph.cozo`; `_Entry` holds `client`, `refcount`, `threading.Lock` (flush lock for direct users). `acquire(path)` opens on first use, `release(path)` closes at refcount 0. Each `CozoGraphStore` instance keeps its own four pending buffers (`stores/graph.py:110-113`), so isolation between calls is unchanged. `_run` and `_do_flush` keep dispatching through `run_in_executor` (graph.py:136-140, 348-349); no read lock is needed (R1).
**When to use:** every `CozoGraphStore.__init__`; also the health probe.
**Detecting the lock error (verified texts, R7/R8):**
```python
# Source: spike_cozo.py output (this session). Both texts embed the absolute path: never forward them.
def _is_lock_error(exc: BaseException) -> bool:
    text = str(exc.args[0]) if exc.args else str(exc)
    return "kIOError" in text and ("lock hold by current process" in text or "While lock file" in text)
```
In the registry, a failed open must not leave an entry or a half-incremented refcount. `finalize()` must be idempotent (release once) because engine `finally` blocks can run after a partial construction.

### Pattern 2: Prepare / commit / abort anchors (D-07)

Add three methods to `StorageNameSpace` (`stores/base.py:157-175`) with safe defaults so fixture stores that implement only `index_done_callback` keep working: `prepare()` -> no-op; `commit_prepared()` -> `await self.index_done_callback()`; `abort_prepared()` -> `await self.drop_pending_index_ops()`.

| Store | Prepare (stage) | Commit | Abort | Code anchors [VERIFIED: files read this session] |
|-------|-----------------|--------|-------|----------------------------------------------------|
| `SqliteKVStore` | `BEGIN IMMEDIATE`, then the same INSERT ... ON CONFLICT and DELETE statements; leave the transaction open (S4) | `self._conn.commit()`, then clear `_pending_*` | `self._conn.rollback()`, keep or clear buffers per caller | `stores/kv.py:101-116` (`index_done_callback`: INSERT at 103-108, DELETE at 109-110, `commit()` at 111, `rollback()` at 113); buffers `kv.py:61-62`, `drop_pending_index_ops` 118-120 |
| `FaissVectorStore` | Rebase on disk if the committed signature changed (Pitfall 3), then the body of `_do_flush` (`faiss.clone_index`, `remove_ids`, `add_with_ids`) and the **first half** of `_persist`: write `vector.faiss.tmp`, compute `index_checksum`, write `vector.meta.json.tmp`; keep `(staging, entries, next_int_id)` in `self._prepared` | the two `os.replace` calls, then assign `_index/_entries/_next_int_id` on the loop thread and clear `_pending` | unlink both `.tmp` files, drop `_prepared` | `stores/vector.py:344-394` (`index_done_callback`), `396-428` (`_persist`: tmp writes 412-425, `os.replace` 427-428), `179-211` (`delete_by_ids`, to be buffered), `430-431` (`drop_pending_index_ops`) |
| `MultiNamespaceVectorStore` | fan out over `_children` | fan out | fan out | `stores/vector.py:534-540` (fan-out pattern), `492` (`_children`) |
| `CozoGraphStore` | `mt = client.multi_transact(write=True)`; run the `:put nodes`, `:put edges`, cascade `:rm edges`, `:rm nodes`, `:rm edges` statements; **do not commit**; keep `mt` | `mt.commit()` in an executor thread (R4), then clear buffers | `mt.abort()` in an executor thread (R5) | `stores/graph.py:311-354` (`index_done_callback`; `multi_transact` at 327, statements 329-341, `commit()` at 342, `abort()` at 345) |

Engine call sites that change: `seam/engine.py` ingest `818` (build), `853-860` (run), `871-872` (unconditional `index_done_callback` loop), `877-879` (finalize); `delete_document` `991-1004` (no flush today); `_execute_resolved` `1174-1187` (read path: construct + finalize only, never flush). After a successful prepare-all, a failure in a later commit cannot be rolled back across stores; D-07 accepts and documents that window (vector checksum covers the vector pair).

### Pattern 3: Incremental `stores_scope` (D-04)
`_build_stores` (`seam/engine.py:361-388`) builds kv, vector, graph in one expression; if graph raises, the kv connection is leaked. Tests call `_build_stores(...)` directly and monkeypatch it (`tests/seam/test_raw_upload_staging.py:175`, `tests/seam/test_evidence_namespace_guard.py:116-118`, `tests/seam/test_leak.py:47,134`, `tests/parity/test_cross_modality_isolation.py:131-132`, `tests/seam/test_store_isolation.py:18-19`, `tests/parity/test_cli_builder_refusals.py:44`), so keep the name and the `(store_root, workspace, resolved=None) -> dict` signature working. Add an optional `into: dict | None = None` parameter that is filled as each store is created, and an `async` context manager that passes its own dict and finalizes whatever landed in it in `finally`. `parity/run_arm.py:77-105` has a copy of `_build_stores` and `run_arm.py:185-203` its own try/finally; give it the same treatment (D-04 last sentence).

### Pattern 4: `EFFECT_TO_STORE` and allowlist proxies (D-09)
```python
# Source: values quoted verbatim from parts/schema.py:31-49 (the 17-member Effect Literal).
EFFECT_TO_STORE: dict[str, tuple[str, str] | None] = {
    "reads_kv": ("kv", "r"), "writes_kv": ("kv", "w"),
    "reads_vector": ("vector", "r"), "writes_vector": ("vector", "w"),
    "reads_graph": ("graph", "r"), "writes_graph": ("graph", "w"),
    # no backing store -> require() raises UndeclaredEffectError("no store backs effect X")
    "reads_lexical": None, "writes_lexical": None, "reads_blob": None,
    "writes_artifact": None, "mutates_store": None, "self_storage": None,
    "calls_llm": None, "calls_rerank": None, "calls_embedding": None, "net": None, "fs": None,
}
```
`_ScopedStoresView.__getitem__` (`runner/scheduler.py:270-277`) currently loops `self._declared_effects` and returns on the **first** effect whose suffix equals the key. Replace with: collect all declared effects mapping to that store key; if any is `"w"` return the writable handle, else if any is `"r"` return the proxy. STOR-05 case (3) declares `['reads_kv','writes_kv']` in that order, so first-match-wins would wrongly return the read proxy. Keep the recorder call (`_recorder(self._node_id, TOUCH_KIND_OBSERVED, store_key)`) and keep `StoreNotWiredError` when the store key is absent from `raw_stores` (`tests/parts/test_reference_parts.py:13,110-115` asserts it).

The proxy is a small class with `__slots__`, `__getattr__(name)` that returns `getattr(target, name)` only if `name` is in the per-kind allowlist and raises `UndeclaredEffectError(f"writes_{kind}" ...)` otherwise (STOR-05 test (1) expects the error to name `writes_kv`). The vector proxy's `select` wraps the returned `FaissVectorStore` in a vector read proxy. `iter_vectors` and `get_by_id` are **synchronous** on `FaissVectorStore` and the others are `async`; the proxy returns the bound method either way, so it needs no awaiting logic.

### Pattern 5: Committed-snapshot cache (D-05)
New `stores/snapshot.py` (or inside `vector.py`): `read_snapshot(dir) -> _Snapshot(index, entries, dim, next_int_id)` with module-level `dict[key, _Snapshot]`, `threading.Lock`, key `(str(resolved dir), (ino, mtime_ns, size) of vector.faiss, (ino, mtime_ns, size) of vector.meta.json)`. Procedure: `stat` both -> hit? return; miss -> read meta, hash the index file, compare checksum, `faiss.read_index`, **stat again**; if the signature changed during the read, retry once, then raise `VectorStoreCorruptedError`. It must not `mkdir`. It must return the same corruption errors as `FaissVectorStore.__init__` (STOR-08). `FaissVectorStore.__init__` (`vector.py:113-137`) mkdirs and reads inline today; a read-only open path (no `mkdir`) is needed for resolve and health. Bound the cache (small LRU) so a long-lived server does not pin every historical index; stale-key entries are evicted on insert.

### Pattern 6: Health probes (D-14)
Static list (derive-and-assert test against the part constants, Pitfall 19):

| Wiring | kv | graph | vector namespaces |
|--------|----|-------|-------------------|
| LightRAG (`wirings/lightrag/base.json` `store_namespaces`) | `text_chunks` | `chunk_entity_relation` | `chunks`, `entities`, `relationships` |
| HippoRAG (`wirings/hipporag/base.json` `store_namespaces`) | `hipporag-text-chunks` | `hipporag-graph` | `hipporag-chunks`, `hipporag-entities`, `hipporag-facts` |

[VERIFIED: printed from the two `base.json` files and the `_*_NAMESPACE` constants in `parts_core/{lightrag,hipporag}/*.py` this session; the vector namespaces are not declared in any wiring JSON, only in part constants, which is why a static list is needed.]

Probe algorithm per entry: directory/file existence check first -> `absent` if missing. kv: `sqlite3.connect(f"file:{path}?mode=ro", uri=True)` and `SELECT 1 FROM kv LIMIT 1` -> `ok`; an `OperationalError` mentioning `locked` -> `busy`. graph: `graph.cozo` must exist (S1), then `registry.acquire(path)`; a lock error -> `busy`; run `c.run("::relations", {}, True)` (immutable, S2) -> `ok`; always `release`. vector: both files present and checksum/meta valid via the snapshot cache -> `ok`; one file only or checksum mismatch -> `corrupted`. Report key format is not fixed by D-14 (Open Question 3). `status` is `ok` only when every store is `ok` and the existing engine fields are `ok`, so a fresh install is `degraded` with all stores `absent`.

### Pattern 7: Adapter semantics
- **Graph (STOR-10):** `delete_node` pops the pending node put, adds to `_pending_node_rms`, drops buffered incident edges from `_pending_edge_puts`, and records the id so flush also runs the cascade `:rm edges` (R9). `node_degree` (`graph.py:190-201`), `get_node_edges` (203-224) and `export_to_igraph` (226-274) must also hide disk edges whose endpoint is in `_pending_node_rms` (read-your-writes before flush). `upsert_edge` (291-296) adds a buffered `{}` node for any endpoint that is neither pending nor on disk (needs an awaited `has_node`; it is already `async`). The `export_to_igraph` dangling-edge skip (263-267) stays as defence. `tests/stores/test_graph_frozen_bugs.py:96-103` scans `stores/graph.py` source and forbids the substring `count(`; do not introduce it in code or string literals outside comments and docstrings.
- **KV (STOR-11):** `get_by_id` returns `self._pending_upserts[id]` by reference (`kv.py:68`) and `upsert` stores the caller's dict (`kv.py:86`); use `copy.deepcopy` at both. `is_empty` (`kv.py:94-99`) returns False if any pending upsert exists and ignores pending deletes; correct form: committed ids minus pending deletes, plus pending upserts, is empty. `tests/stores/test_kv.py:102-107` replaces `store._conn` with a failing wrapper and asserts `_pending_upserts` survive a failed flush; keep those attribute names and make the failing path roll back and keep the buffers.
- **Vector (STOR-16, STOR-09, STOR-08):** result dicts are built as `{"id": ..., "score": ..., **entry["metadata"]}` at `vector.py:235, 267, 312` and `{"id": doc_id, **entry["metadata"]}` at `338` [VERIFIED: file read]; `ReservedMetadataKeyError` in `upsert` (before the pending buffer is touched, like the existing length checks at 153-170). `parity/import_index.py` calls `FaissVectorStore` at lines 191 and 319 (`upsert` sites) and must strip `id`/`score` (D-11). `query` must validate `top_k` **before** the empty-index early return at 218-219 (verified live: `top_k=0 -> AssertionError`). `VectorNamespaceNotSelectedError`'s list (`_available_namespaces`, 503-510) lists every directory; filter to directories that contain `vector.faiss`. `MultiNamespaceVectorStore` has no `score_all`, `self_knn`, `get_by_id`, `iter_vectors`, so today those raise `AttributeError`; add methods that raise `VectorNamespaceNotSelectedError`, and make `iter_vectors` a plain method (not a generator function) so it raises at call time, not at first `next()`.

### Pattern 8: GC CLI and `NamespaceGCError` (D-16)
`gc_namespace` (`namespaces.py:103-111`) is `shutil.rmtree(target, ignore_errors=True)`. Replace with `try: shutil.rmtree(target) except FileNotFoundError: return except OSError as exc: raise NamespaceGCError(namespace) from exc`. `namespace_dir` is flat (`store_root / namespace`, `namespaces.py:72-86`) while seam stores live at `store_root/<workspace>/<namespace>`; the CLI therefore can only remove `store_root/<quarantined-hex>` directories and can never touch seam stores. CLI shape (discretionary): `python -m databasise.launcher.gc_namespaces --store-root PATH quarantined-<hex> [...]`; wrap in `with store_lock(root)` and map `StoreLockedError` to a non-zero exit exactly like `parity/run_arm.py:248-250`. A `[project.scripts]` entry is optional; tests should invoke `python -m` because an editable install does not pick up a new script until reinstalled.

### Anti-Patterns to Avoid
- **Flushing inside a node** (`graph_augment_persist.py:84`): commits a store before the engine's all-or-nothing decision.
- **Caching `FaissVectorStore` objects** (D-05 forbids it): they hold writer state.
- **Forwarding the pycozo error text** into `StoreBusyError`: it embeds the absolute path (R7, R8).
- **Opening `Client("rocksdb", path)` to find out whether the path exists** (S1).
- **Awaiting nothing while a sqlite write transaction is open on the event-loop thread**: a second coroutine's `BEGIN IMMEDIATE` blocks the loop for the 5 s busy timeout (Pitfall 2).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-statement graph atomicity | A custom write-ahead log | `Client.multi_transact(write=True)` + `commit()/abort()` | Verified staged, thread-agnostic, abortable (R3-R5). |
| KV atomicity | A shadow table | sqlite `BEGIN IMMEDIATE` ... `commit()/rollback()` | Verified to take the write lock at prepare (S4). |
| Read-only graph probe | Parsing RocksDB files | `Client.run(script, {}, True)` (`immutable`) | Verified: writes are refused (S2). |
| Read-only sqlite probe | `os.path.exists` + reading bytes | `file:...?mode=ro` URI | Verified: creates nothing (S3). |
| Directory removal | A manual walker | `shutil.rmtree` without `ignore_errors` | Raises `OSError` subtypes the CLI can name; refuses a symlinked top level. |
| Index checksum | A new format | the existing `index_checksum` in `vector.meta.json` (`vector.py:416-421`) | Already the crash-window detector D-07 relies on. |

**Key insight:** every atomicity primitive needed already exists in the three engines; the work is sequencing (one flush window, one lock) and not letting a node bypass it.

## Runtime State Inventory

> This phase deletes modules (D-15) and changes store semantics, so the inventory applies.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `<store_root>/artifact_registry.db` is created by `registry_artifact/index.py` (`ArtifactRegistry(store_root)`); blob directories by `FilesystemBlobStore`; lexical dbs by `SqliteLexicalStore`. Nothing in the engine or any shipped wiring creates them (no importer outside tests and docstrings). Existing store roots on disk (`v1/.parity_v2_store`, gitignored) hold only kv/vector/graph namespaces. [VERIFIED: grep of the package this session] | None for shipped runtime. If an operator root contains a stray `artifact_registry.db`, it becomes inert; document, do not migrate. |
| Live service config | None. No external service references these modules. | None. |
| OS-registered state | None. | None. |
| Secrets / env vars | None reference the removed modules. | None. |
| Build artifacts / installed packages | `databasise/databasise.egg-info/SOURCES.txt` lists `stores/blob.py`, `stores/lexical.py`, `registry_artifact/*`; `pyproject.toml:136` lists `"databasise.registry_artifact"` in `[tool.setuptools] packages`. `tests/fixtures/codebase_memory_mcp_raw_items.json` contains the directory names as recorded graph data (lines 277, 812, 826). | Remove the `pyproject.toml` package entry. Leave the fixture JSON alone (recorded data). The egg-info is regenerated by an install; do not hand-edit. |

## Common Pitfalls

### Pitfall 1: Overlapping flushes fail after exactly 1 s
**What goes wrong:** two calls both prepare a graph transaction that writes the same node or edge key; the second `mt.run` (or a plain `run`) blocks 1.00 s then raises `rocksdb::kTimedOut::kLockTimeout` (R6). With D-07 the first transaction stays open until the other stores are prepared, widening the window.
**Why:** RocksDB pessimistic key locks, default 1 s lock timeout.
**How to avoid:** hold one per-(loop, store root) `asyncio.Lock` across prepare-all through commit-all/abort-all. Map a `kLockTimeout` that still escapes to `StoreFault`, not `StoreBusyError`.
**Warning signs:** `kLockTimeout` in logs; `1.00s` durations in flush timings.

### Pitfall 2: sqlite contention on the event-loop thread
**What goes wrong:** `SqliteKVStore` runs `execute` synchronously inline (`kv.py:20-28`). If call A holds a prepared `BEGIN IMMEDIATE` and call B's coroutine runs `BEGIN IMMEDIATE` on the same loop thread, B blocks the whole loop up to 5000 ms (S4), so A cannot reach its commit; B then fails with `database is locked`.
**How to avoid:** acquire the asyncio flush lock (an `await`) before any prepare DML, so contention is resolved by awaiting, never by blocking.
**Warning signs:** `database is locked` in an otherwise idle run; a 5 s stall in `/health`.

### Pitfall 3: Faiss lost update and shared `.tmp` names with per-call instances
**What goes wrong:** each call constructs its own `FaissVectorStore`, which loads the committed index at construction (`vector.py:126-137`). Two overlapping ingests both flush from their own stale base (`index_done_callback` copies `self._entries` and `self._next_int_id` at 361-364), and the later `os.replace` discards the earlier writer's vectors; `next_int_id` can also collide. Both also write the same `vector.faiss.tmp` / `vector.meta.json.tmp` (`vector.py:412-413`).
**How to avoid:** inside the flush lock, prepare first compares the on-disk `(ino, mtime_ns, size)` pair to what this instance loaded; if different, reload `_index`, `_entries`, `_next_int_id` from disk, then apply `_pending` and the buffered deletes. Use a unique suffix for the tmp files as defence.
**Warning signs:** a document's chunks missing after two concurrent ingests; duplicate `int_id` values in `vector.meta.json`.

### Pitfall 4: Snapshot cache sees the two-rename window
**What goes wrong:** `_persist` replaces `vector.faiss` then `vector.meta.json` (`vector.py:427-428`). A reader between the two sees a new index with the old sidecar and raises `VectorStoreCorruptedError` spuriously (this is the WR-02 signature).
**How to avoid:** read with stat-read-stat and one retry (Pattern 5), or take the per-path flush lock briefly on a mismatch before declaring corruption.
**Warning signs:** intermittent corruption refusals on `/evidence/resolve` during ingest.

### Pitfall 5: A shipped part flushes inside the node
**What goes wrong:** `parts_core/hipporag/graph_augment_persist.py:84` is `await graph_store.index_done_callback()`. Under D-09 it raises `UndeclaredEffectError`, and even if allowed it commits the graph before the engine decides the run is clean (it is the only such call: `grep` for `index_done_callback|drop_pending_index_ops|.finalize(|.drop()` over `parts_core parts runner validator foreign eval` returns that one line).
**How to avoid:** delete that line and rely on the engine flush. Its four unit tests (`tests/parts_core/hipporag/test_graph_construction.py:207-300`) read through the same store object (`export_to_igraph`, `get_edge`) and pass on the pending buffer, so they need no change.

### Pitfall 6: First-match-wins in the store view
`_ScopedStoresView.__getitem__` returns the first declared effect with a matching suffix (`runner/scheduler.py:270-277`). A part declaring read before write gets the read proxy. See Pattern 4.

### Pitfall 7: `Client()` side effects
Constructing `Client` without `dataframe=False` logs a pandas traceback each time (S5); opening a missing path creates it (S1). Health and the GC CLI must check existence first and the shared client must pass `dataframe=False`.

### Pitfall 8: Circular import blocks a single `StoreBusyError`
`databasise/seam/__init__.py` imports `databasise.seam.engine` (lines 15-16), which imports the stores; so `stores/graph.py` cannot import `databasise.seam.refusals` at module scope. Define `GraphStoreBusyError(RuntimeError)` in `stores/graph.py` (house style next to `VectorStoreCorruptedError`) and have the engine's `stores_scope` translate it into `refusals.StoreBusyError(store_kind="graph")`. Direct `CozoGraphStore` users and the STOR-01 test part (b) (store-level open) see the store-level class; engine/REST see the catalogue class. If the planner prefers one class, a function-scope import at the raise site works but inverts the layering (Open Question 1).

### Pitfall 9: D-04 versus the staged-upload ordering and test monkeypatches
`ingest` stages the raw upload only after `parse_wiring` and `_build_stores` "can no longer fail" (comment at `engine.py:793-794`). Moving construction into the `try` must keep store construction **before** the staging block so a failed open still leaves no file (`tests/seam/test_raw_upload_staging.py:175` patches `_build_stores` to raise and checks that). Keep `_build_stores` a module-level name looked up at call time.

### Pitfall 10: Health shape change breaks one unprotected test
`tests/seam/test_corpus_status.py:166` asserts `set(report.stores) == {"kv", "vector", "graph"}`. `tests/seam/test_rest_corpus_endpoints.py:256-259` compares `response.json() == in_process.model_dump()` (shape-agnostic, passes). No other test pins the store keys.

### Pitfall 11: Existing tests that contradict the new semantics (unprotected, must be edited)
- `tests/stores/test_vector.py:197-212` `test_delete_by_ids_removes_entries_and_stays_consistent`: asserts the delete is visible and persisted immediately; under D-08 it must flush first.
- `tests/test_embed_startup.py:207-235` imports `FilesystemBlobStore` and `SqliteLexicalStore` and loops over five classes.
- `tests/test_phase_success_criteria.py:42-44, 357-358, 498-531` (Phase 1 criterion 4) builds on `ArtifactRegistry`, `write_artifact`, `FilesystemBlobStore`, `BlastRadiusRefusal`, `Pin`; criterion 4 needs a rewrite that keeps the quarantined-namespace-separation and GC assertions (lines 563-571) but drops the registry/blob assertions.
- `tests/seam/test_refusal_status_codes.py:30-34` parametrizes every `refusals.__all__` name except `ForeignEngineRefusalError` as a 422; add `StoreBusyError` to the mapped-elsewhere set with its own 409 test. `tests/seam/test_rest_transport.py::_REFUSAL_FACTORIES` and `tests/mcp/test_mcp_refusal_mapping.py` also enumerate the catalogue.

### Pitfall 12: `iter_vectors` is lazy
A generator function raises on first `next()`, not on call. STOR-09 says "calling ... raises". On `MultiNamespaceVectorStore` define it as a normal method that raises immediately.

### Pitfall 13: `top_k` validation order
`query` returns `[]` for an empty index before searching (`vector.py:218-219`); validate `top_k <= 0` first or the empty-index case hides the error.

### Pitfall 14: Buffered vector delete interacts with upsert
Define the order: `upsert(id)` after `delete_by_ids([id])` cancels the delete; `delete_by_ids` after `upsert` drops the pending upsert (the current code already does that at `vector.py:191`) and also schedules a disk delete if the id is committed. Reads (`query`, `get_by_id`) stay committed-only (module docstring "only committed (flushed) data is queryable").

### Pitfall 15: `VectorStoreCorruptedError` signature
`__init__(self, index_path, expected, actual)` (`vector.py:77`) is checksum-shaped. A missing-file case needs a reason (e.g. `expected=None, actual="<missing vector.meta.json>"` or a new optional `reason`). Keep the current positional signature so `tests/stores/test_vector.py:156` still passes. The STOR-08 resolve path must also see this error (today resolve returns `UnresolvableEvidenceReferenceError` because the half-written dir opens empty).

### Pitfall 16: Opaque LightRAG ingest still builds the stores
`ingest` builds kv/vector/graph for LightRAG too (the opaque node never touches them). With D-01 the held graph no longer blocks `/query` or `/health`; prepare/commit are no-ops there.

### Pitfall 17: Leaking the path
Both RocksDB lock errors embed the absolute store path (R7, R8). `StoreBusyError` carries only `store_kind` and a fixed message; raise it `from None` and log the cause once server-side (`_foreign_fault` precedent, `engine.py:248-258`).

### Pitfall 18: A refused wiring currently becomes a 500
`scheduler.run_wiring` raises `WiringRefusedError(ValueError)` when `parsed.report` has violations (`runner/scheduler.py:179, 526`); no engine call site checks `parsed.report` first, and `WiringRefusedError` is not a `SeamRefusalError`. D-15 requires a named refusal, so the engine must check `parsed.report.ok` right after each `parse_wiring` (`engine.py:811, 982, 1165`) and raise a catalogue refusal (new type; name is discretionary). The check belongs in `validator/parse.py` next to `CODE_EFFECTS_EXCEED_PART` (`validator/parse.py:204-216`), testing both `node.effects` and the resolved `part.effects` (the scheduler scopes from `part.effects`, so a wiring that omits the effect still reaches the store).

### Pitfall 19: Static namespace list drift
The vector namespaces live only in part constants. Add a test that imports the part constants (`parts_core/lightrag/{chunk_vector,entity_lookup,relation_lookup}.py`, `parts_core/hipporag/{chunk_embed,entity_fact_embed,fact_score}.py`) and asserts they equal the health list.

### Pitfall 20: GC target layout
`gc_namespace` operates on `store_root/<token>` (flat); seam stores are `store_root/<workspace>/<ns>`. Validate the token with `namespace_dir` (regex `^[A-Za-z0-9-]+$`) **and** require the `quarantined-` prefix; `shutil.rmtree` raises on a symlinked top level, which now surfaces as `NamespaceGCError` instead of being swallowed.

### Pitfall 21: Admission strings mention the removed registry
`parts_core/lightrag/full_ingest.py:186`, `parts_core/lightrag/full_delete.py:186`, `parts_core/codebase_memory_mcp.py:271` carry `ArtifactRegistry.discover` inside `ConditionVerdict.evidence` text. Editing them is required for the TOOL-17 grep test; first confirm no test or hash pins that text (search `tests/parts` for `ConditionVerdict`/`evidence`). Scope the grep test to import statements and dotted module paths in `*.py` outside `evidence/`, `tests/fixtures/`, and the test file itself.

### Pitfall 22: No HippoRAG delete wiring exists
`wirings/hipporag/` ships `base.json` and `corpus-ingest.json` only; `_corpus_wiring(query_wiring, "delete")` raises `NoWritePathForModalityError` for HippoRAG (`engine.py:391-409`; HIPP-16 owns the real one in Phase 12). STOR-07's test must supply a fixture delete wiring by monkeypatching `engine._corpus_wiring` and using a fixture registry, the pattern in `tests/seam/test_delete_document.py:92-115` (`_registry_with(part)`, `_make_engine`).

## Code Examples

### Staged graph commit (verified behaviour)
```python
# Source: spike_cozo.py / spike_cozo2.py (this session), pycozo 0.7.6 client.py:275-341
mt = client.multi_transact(write=True)            # prepare (executor thread A)
mt.run("?[id, attrs] <- $rows :put nodes {id => attrs}", {"rows": rows})
mt.run("?[src, tgt] := *edges{src, tgt}, src = $id or tgt = $id :rm edges {src, tgt}", {"id": nid})
mt.run("?[id] <- [[$id]] :rm nodes {id}", {"id": nid})
...                                               # other stores prepare while mt is open
mt.commit()                                       # commit (executor thread B) -- or mt.abort()
```

### Flush helper shape
```python
# Source: design; behaviour of each call verified in the spike table above.
async def _flush(stores: dict[str, Any], lock: asyncio.Lock) -> None:
    async with lock:
        prepared: list[Any] = []
        try:
            for s in stores.values():
                await s.prepare(); prepared.append(s)
        except BaseException as exc:
            for s in prepared + [x for x in stores.values() if x not in prepared]:
                with contextlib.suppress(Exception):
                    await s.abort_prepared()
            raise _foreign_fault("ingest", exc, failure_class="StoreFault") from exc
        for s in stores.values():
            await s.commit_prepared()      # D-07's documented residual window
```

### Read-only probe of an existing graph (verified calls)
```python
# Source: spike3.py -- Client opens/creates on a missing path, so check existence first.
if not graph_dir.is_dir():
    return "absent"
try:
    client = _ClientRegistry.acquire(graph_dir)           # shared; lock error -> "busy"
except GraphStoreBusyError:
    return "busy"
try:
    client.run("::relations", {}, True)                    # immutable=True
    return "ok"
finally:
    _ClientRegistry.release(graph_dir)
```

## Allowlist Audit (D-09 against every shipped caller)

Method calls on `ctx.stores[...]` found by scanning every file under `parts_core/`, `parts/`, `runner/`, `validator/`, `foreign/`, `eval/` for store method calls [VERIFIED: scan output this session]:

| Part (file) | Declared effects (verbatim) | Calls | In allowlist? |
|-------------|------------------------------|-------|----------------|
| `lightrag/chunk_sel_kg.py` | `["reads_kv", "reads_vector"]` | `vector.select(ns).query`, `kv.get_by_id` | yes |
| `lightrag/chunk_vector.py` | `["reads_vector"]` | `select(ns).query` | yes |
| `lightrag/entity_lookup.py` | `["reads_vector"]` | `select(ns).query` | yes |
| `lightrag/relation_lookup.py` | `["reads_vector"]` | `select(ns).query` | yes |
| `lightrag/entity_hydrate_expand.py` | `["reads_graph"]` | `get_node`, `node_degree`, `get_node_edges` | yes |
| `lightrag/relation_hydrate_expand.py` | `["reads_graph"]` | `get_edge`, `get_node` | yes |
| `lightrag/heading_backfill.py` | `["reads_kv"]` | `get_by_id` | yes |
| `hipporag/assemble_result.py` | `["reads_kv"]` | `get_by_id` | yes |
| `hipporag/dpr_fallback.py` | `["calls_embedding", "reads_vector"]` | `select(ns).score_all` | yes |
| `hipporag/fact_score.py` | `["reads_vector", "calls_embedding"]` | `select(ns).score_all` | yes |
| `hipporag/ppr.py` | `["reads_graph"]` | `export_to_igraph` | yes |
| `hipporag/reset_vector_join.py` | `["reads_vector", "calls_embedding", "reads_kv"]` | `kv.get_by_id`, `select(ns)` (then read calls) | yes |
| `hipporag/synonymy_edges.py` | `["reads_vector"]` | `select(ns).self_knn` | yes |
| `hipporag/chunk_embed.py` | `["calls_embedding", "writes_vector", "writes_kv"]` | `vector.select(ns).upsert`, `kv.upsert` | writable handle |
| `hipporag/entity_fact_embed.py` | `["calls_embedding", "writes_vector", "writes_kv"]` | `select(ns).upsert` x2, `kv.upsert` | writable handle |
| `hipporag/graph_augment_persist.py` | `["writes_graph", "writes_artifact"]` | `upsert_node`, `upsert_edge`, **`index_done_callback`** | writable handle; **`index_done_callback` is NOT allowed: remove line 84** |
| `fake_llm_caller.py` | `["calls_llm", "writes_kv"]` | `get_by_id`, `upsert` | writable handle |
| `parts/registry.py:82` | `["writes_kv"]` | `upsert` | writable handle |

`iter_vectors` is in D-09's allowlist and has no shipped caller (only `FaissVectorStore.self_knn`, `vector.py:293`, and tests use it). `get_by_ids`, `filter_keys`, `is_empty`, `has_node`, `has_edge`, `get_all_labels`, `get_by_id` (vector) have no shipped caller either; the allowlist is a superset of use, so no shipped part breaks except the one flush call. `full-ingest`, `full-delete` and `embedder-index` declare `reads_kv`/`reads_graph` or `calls_embedding` but their bodies do not touch `ctx.stores` (opaque v1 subprocess or direct client call), so the read proxy never sees them.

## D-15 Deletion Blast Radius

### `stores/lexical.py`, `stores/blob.py`, `registry_artifact/`
Importers and references found by scanning the package (excluding `.venv`, `__pycache__`, `evidence/`):

| Reference | File:line | Action |
|-----------|-----------|--------|
| Module itself | `stores/lexical.py`, `stores/blob.py`, `registry_artifact/{__init__,index,write_path}.py` | delete |
| Its own tests | `tests/stores/test_lexical.py`, `tests/stores/test_blob.py`, `tests/registry_artifact/{__init__,test_index,test_write_path_blast_radius}.py` | delete (`test_write_path_blast_radius.py` imports `registry_artifact` and `FilesystemBlobStore` at lines 6-11) |
| Cross-test imports | `tests/test_embed_startup.py:207,210,235` | edit: drop the two classes from the import and the loop |
| Phase-1 acceptance | `tests/test_phase_success_criteria.py:42-44, 357-358, 498-531, 563-571` | rewrite criterion 4 (Pitfall 11) |
| Package list | `pyproject.toml:136` `"databasise.registry_artifact"` | remove |
| Admission text | `parts_core/lightrag/full_ingest.py:186`, `parts_core/lightrag/full_delete.py:186`, `parts_core/codebase_memory_mcp.py:271` | edit text (Pitfall 21) |
| Comments | `ledger/ledger.py:76`, `parts_core/__init__.py:38`, `tools/check_import_boundary.py:164`, `validator/depth.py:29`, `README.md:39` | edit wording |
| Docs referencing the dir | `evidence/DR-04-DECISION.md:27,38,103` | historical evidence; leave, exclude from the grep test |
| Build artifact | `databasise.egg-info/SOURCES.txt:124,127,269,272` | regenerated; do not edit |
| Recorded fixture data | `tests/fixtures/codebase_memory_mcp_raw_items.json:277,812,826` | leave |

`check_upstream_refs` (`tools/check_import_boundary.py:160-186`) globs `stores/*.py`; deleting two modules needs no change there. No engine, runner, seam, launcher or parity module imports any of the three.

### `writes_artifact` declarers — reconciliation of STOR-12, TOOL-17 and D-15
[VERIFIED by reading `parts_core/declared_only.py:70-78`, `parts_core/lightrag/embedder_index.py:52-59`, `parts_core/hipporag/graph_augment_persist.py:92-100` and printing `wirings/**.json` node effects this session]

| Part (registry name) | Where declared | Node id(s) in shipped wirings | Node-level `effects` in wiring JSON | Keep marker? |
|----------------------|----------------|-------------------------------|-------------------------------------|--------------|
| `lightrag/full-ingest@0.1.0` | `declared_only.py:76` `effects=["calls_llm", "writes_artifact", "reads_kv", "reads_graph"]`, `artifact_scope="quarantined"` | `full-ingest` in `wirings/lightrag/corpus-ingest.json` | `["calls_llm","writes_artifact","reads_kv","reads_graph"]` (lines 8-13) | yes (opaque, quarantined; blast-radius rule keys on it) |
| `lightrag/embedder-index@0.1.0` | `embedder_index.py:56` `effects=["calls_embedding", "writes_artifact"]` | `embedder-index` in `wirings/lightrag/base.json` | `["calls_embedding"]` only (narrower than the Part, allowed by `CODE_EFFECTS_EXCEED_PART`'s subset rule) | yes (Part-level) |
| `hipporag/graph-materializer@0.1.0` | `graph_augment_persist.py:96` `effects=["writes_graph", "writes_artifact"]` | node id `graph-augment-persist` in `wirings/hipporag/base.json:52` and `corpus-ingest.json:52` | `["writes_graph","writes_artifact"]` | yes |

So the four names in D-15 and in STOR-12/TOOL-17 are three distinct Parts: `graph-augment-persist` (node id) and `graph-materializer` (part name) are the same thing. None of the five `arm-*.json-patch.json` files mention `writes_artifact` (STOR-12's phrase "and every arm patch" is loose: the arms inherit `embedder-index` from `base.json`). `lightrag/full-delete` declares `mutates_store`, not `writes_artifact`. All three keep the marker; none gets a store key. Consumers of the marker that must keep working: `validator/blast_radius.py:54` (keys on `"writes_artifact" not in part.effects`), `runner/scheduler.py:167-176` and `:648` (`_STORE_MUTATING_EFFECTS`, `resumable`), `evidence/falsifier2.py` and `evidence/wirings/w3-lightrag-half-decomposed.json`.

## HealthReport Consumers (D-14)

Definition: `seam/corpus.py:285-300` (`stores: dict[str, bool]` at line 297). Producer: `seam/engine.py:1091-1139` (constructs stores via lambdas 1100-1110 and reports `True` on success, line 1116). Exposure and consumers:

| Consumer | File:line | Change needed |
|----------|-----------|---------------|
| REST route | `seam/rest.py:466-468` `get_health() -> HealthReport` | none (response model follows the class); OpenAPI schema updates automatically |
| MCP | `mcp/server.py:144-146` returns `engine.health()` directly; `mcp/tools.py:85` `StatusScope` | none (serialised from the model) |
| Docstring | `seam/corpus.py:286-292`, `seam/engine.py:1092-1099` | update (map of `"ok"/"absent"/"corrupted"/"busy"`) |
| Test pinning the keys | `tests/seam/test_corpus_status.py:166` | edit to the new key set |
| Tests that call `/health` and only check status/200 | `tests/seam/test_corpus_adapter_failures.py:67-70`, `tests/launcher/test_bind_guard.py:116-173`, `tests/launcher/test_launchers.py:102,261,281`, `tests/seam/test_rest_cors.py:62,83` | none |
| Equality test | `tests/seam/test_rest_corpus_endpoints.py:256-259` | none |
| Docs | `docs/gui/API-INVENTORY.md` (GUI inventory row 10 "GET /health"), `docs/gui/CODEBASE-MAP.md` | update wording (not system-model) |
| `docs/system-model/CONTRACT.md` | §18 does not define `HealthReport` or its fields (the only `health` hits are §17's transport health at lines 731, 739, 1042, 1046 and a §-cross-reference at 630) | no amendment needed [VERIFIED: grep of CONTRACT.md for `health` this session] |
| `databasise/evidence/COVERAGE.md:98` | row text describes health generically | optional wording; `tests/mcp/test_tool_growth_invariant.py` cross-checks table rows against tools, so keep the table structure |

`engine` fields (`working_dir_present`, `storages_initialized`, v1 working-dir creation) are LRAG-13/14 (Phase 11); Phase 10 changes only `stores` and the `status` rule.

## Protected Test Files

Rule source: `check-edit-guard.py` protects the file part of every ledger row's `test_ref`, plus `check_locks.files` and `check_guard` [VERIFIED: read `/home/chris/coding/GUI-research/adapters/claude-code/hooks/check-edit-guard.py:99-125`]. In `ledger/REQUIREMENTS.json` (read with the Read tool, plus one plain `grep` for non-empty `test_ref`): `check_locks: null`, `check_guard: []`, and `check_edit_grants` currently holds `databasise/tests/seam/test_rest_corpus_endpoints.py` (granted_at 353) and `databasise/tests/mcp/test_tool_growth_invariant.py` (granted_at 354). Eleven non-empty `test_ref` values give exactly these eight protected files (RUN-11 has an empty `test_ref`; every SEAM row has an empty `test_ref` today):

| Protected file | Row | Does Phase 10 need to edit it? |
|----------------|-----|--------------------------------|
| `databasise/tests/mcp/test_tool_growth_invariant.py` | RUN-01 | No. No tool is added; keep `evidence/COVERAGE.md` table rows intact if its text is touched. |
| `databasise/tests/clients/test_openai_compat.py` | RUN-02, RUN-03 | No. |
| `databasise/tests/foreign/test_mcp_sdk_guard.py` | RUN-04 | No. |
| `databasise/tests/clients/test_build_clients.py` | RUN-05 | No. |
| `databasise/tests/launcher/test_launchers.py` | RUN-06, RUN-07 | No. It asserts the two existing console scripts exist (`:165-170`) and only status 200 on `/health`; a third script (GC CLI) does not break it. |
| `databasise/tests/seam/test_rest_cors.py` | RUN-08 | No. Uses `/health` only for CORS headers. |
| `databasise/tests/seam/test_rest_corpus_endpoints.py` | RUN-09, RUN-10 | No. Health test is shape-agnostic; delete tests run the LightRAG stub whose namespaces are the defaults. |
| `databasise/tests/test_check_offline_suite.py` | RUN-12 | No (mentions a delete test name only inside a string). |

**Result: no owner grant-check-edit checkpoint is required by the planned work.** Files cited only in a row's `evidence` text (`tests/launcher/test_store_lock.py`, `tests/seam/test_corpus_status.py`, `tests/parity/test_naive_arm_end_to_end.py`) are not guarded, which is why `test_corpus_status.py` can be edited. Contingency: the planner should add one conditional step ("if any edit to a file in this table becomes necessary, stop and request the owner's grant-check-edit") and should re-read `check_edit_grants` and the `test_ref` list at plan time, because the SEAM rows may acquire `test_ref` values when Phase 9 is closed in the ledger (CONTEXT notes this). Operational note: the guard also blocks Bash commands whose arguments name an ancestor folder of a protected file (for example `.`) unless the command is a single plain read-only command, so executor shell commands that use `python`/`awk`/`git grep` with `.` can be refused.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| One `CozoClient` per `CozoGraphStore` instance (`graph.py:107`) | One refcounted client per resolved path | this phase (D-01) | Overlapping calls complete instead of failing with `lock hold by current process` |
| Unconditional engine flush even after node failures (`engine.py:871-872`) | prepare-all/commit-all only on a clean run | this phase (D-06, D-07) | Failed ingest commits nothing |
| Suffix split `effect.split("_", 1)[-1]` (`parts_core/__init__.py:67`, `scheduler.py:270-277`) | Explicit table + proxies | this phase (D-09) | `mutates_store`/`self_storage` no longer map to nonexistent keys `store`/`storage` |

**Deprecated/outdated:** `stores/lexical.py`, `stores/blob.py`, `registry_artifact/` (removed). The `store_lock.py` docstring still says "not the Phase 10 in-process graph handle (STOR-01)"; keep, it remains true.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `kLockTimeout` is a per-transaction default of 1 s that this project does not tune; measured once on this host (1.00 s both times). It may differ on a slower filesystem. | Spike R6 / Pitfall 1 | Low: the flush lock removes the dependency on the value. |
| A2 | A stat-read-stat retry plus a bounded LRU is enough for the snapshot cache; no measurement of resolve latency under concurrent ingest was made. | Pattern 5 | Medium: a hot ingest could cause repeated retries; add the brief lock fallback. |
| A3 | Opening an existing RocksDB for the health probe only rewrites its own `LOG`/manifest files and creates no new top-level entries; the empty-root assertion in STOR-04 covers the absent case only. Not measured on an existing populated db. | Pattern 6 | Low-medium: STOR-04's test is on an empty root, so it passes either way; a populated-root "tree unchanged" check would need a measurement in Wave 0. |
| A4 | `admission` evidence text (`ConditionVerdict.evidence`) is not pinned by any test or hash. Not searched. | Pitfall 21 | Medium: editing it could change a hash or break a snapshot test. Search before editing. |
| A5 | Returning `502` for `failure_class="StoreFault"` (via `_status_for`, because it is not in `_ENGINE_UNAVAILABLE`) is acceptable; 500 or a distinct code might be preferred by the owner. D-13 does not pick a status. | Open Question 2 | Low. |
| A6 | The STOR-07 and STOR-06 tests can obtain a deterministic "node raises after chunk-embed" by a fixture registry (pattern in `tests/seam/test_delete_document.py`) rather than editing the shipped HippoRAG parts. | Validation Architecture | Low. |
| A7 | pytest-asyncio's `asyncio_mode = "auto"` with the REST `TestClient` (separate anyio portal loop per client) means one engine can see more than one event loop in tests; per-(loop, root) lock keys avoid cross-loop `asyncio.Lock` errors. Not reproduced. | Pitfall 1 / Pattern 2 | Low-medium. |

## Open Questions (RESOLVED — orchestrator rulings 2026-10-17 on the owner's "You decide" delegation; binding for planning)

- **Q1 RESOLVED:**
  - The store-level `GraphStoreBusyError` lives in `stores/graph.py`. The engine translates it to the catalogue `StoreBusyError(store_kind="graph")`, which maps to 409.
  - STOR-01 test (b) runs against the engine, with a subprocess holding the path.
  - Separately, a store-level unit test covers the store class.
- **Q2 RESOLVED:**
  - `StoreFault` maps to 502.
  - A run with no exception but `partial`/`stop_reason` set raises `ForeignEngineRefusalError(failure_class="RunIncomplete")` with a synthesized cause, which maps to 502.
  - `_FAULT_RESPONSES` descriptions are reworded so they no longer say "the v1 engine run failed".
- **Q3 RESOLVED:** health `stores` keys are `"<kind>:<namespace>"`, built from one static list. A drift test checks that list against the wirings and part constants.
- **Q4 RESOLVED:** yes. `delete_document` drops pending ops when the result `status == "fail"`, the same as on an exception.
- **Q5 RESOLVED:**
  - The catalogue refusal is `UnparseableWiringError(violations: list[str])`, with codes only and no node ids or wiring internals.
  - It maps to 422 (the Phase 9 D-03 default), and gets a `_REFUSAL_FACTORIES` entry.
  - The engine raises it after each `parse_wiring` call whose report carries violations.
- **Q6 RESOLVED (amends D-12 for the seam boundary):**
  - No store error may reach a caller as a 500.
  - `engine.resolve_evidence` translates `VectorStoreCorruptedError` to `ForeignEngineRefusalError(failure_class="StoreCorrupted")`, which maps to 502.
  - STOR-08's store-level test still asserts the store raises `VectorStoreCorruptedError`, and the seam test asserts the 502 refusal.
  - The store classes themselves stay out of the catalogue.

1. **Where does `StoreBusyError` live relative to the circular import?**
   - What we know: D-01/D-02 want a catalogue refusal; `stores/` cannot import `seam.refusals` at module scope (Pitfall 8).
   - What's unclear: whether STOR-01 test part (b) ("an in-test open of the same path raises the named store-busy refusal") means the store-level class or the catalogue class.
   - Recommendation: store-level `GraphStoreBusyError` raised by `CozoGraphStore`; engine translates to `refusals.StoreBusyError(store_kind="graph")`; write part (b) against the engine (`engine.query` while a subprocess holds the path) and add a store-level unit test for the store class.

2. **`failure_class="StoreFault"` HTTP status and the clean-run predicate for non-exception stops.**
   - What we know: `_status_for` gives 502 unless the class is in `_ENGINE_UNAVAILABLE` (`rest.py:131-137`). D-06 also refuses a run with `partial`/`stop_reason` but no exception (for example a `budget_halt`, `scheduler.py:654-655`), where no real cause exists.
   - Recommendation: accept 502 for `StoreFault` and use a distinct allow-listed `failure_class` (for example `"RunIncomplete"`) with a synthesized `RuntimeError` cause for the no-exception case, mirroring `_node_result_or_refuse`'s synthesized-cause branch (`engine.py:454-458`). Update `_FAULT_RESPONSES` descriptions (`rest.py:150-159`), which still say "the v1 engine run failed".

3. **Health `stores` key format.**
   - What we know: D-14 gives the value type and says "every namespace of every shipped wiring" but not the keys.
   - Recommendation: `"<kind>:<namespace>"` (for example `"graph:hipporag-graph"`); namespaces are already public via `EvidenceRef.namespace`. Confirm during planning; the test in `test_corpus_status.py` is then written against the list.

4. **Delete when the node returns `status == "fail"` without raising.**
   - What we know: D-08 flushes on success and drops on failure; `delete_document` currently treats a `fail` result as an outcome, not an exception.
   - Recommendation: use the D-06 clean-run predicate, and additionally drop pending ops when `result.get("status") == "fail"`. Flag to the planner as a small addition beyond D-08's text.

5. **Name of the refusal for a wiring rejected at parse (D-15).**
   - Discretionary; avoid the existing `runner.scheduler.WiringRefusedError` name. Needs a catalogue entry, a `_REFUSAL_FACTORIES` factory, and the default 422.

6. **`VectorStoreCorruptedError` through REST.**
   - What we know: it is a plain `RuntimeError` (`vector.py:68`), D-12 keeps it out of the catalogue and keeps its "existing mapping", which for `engine.resolve_evidence` is propagation, so REST would answer a generic 500.
   - Recommendation: follow D-12 literally (the STOR-08 test asserts the engine raises the corruption error). If the owner wants no 500 here, that is a catalogue addition and should be raised at plan time, because success criterion 1 says "never a 500" only for lock contention.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python venv `databasise/.venv` | all tests, spikes | ✓ | 3.12.13 | — |
| pycozo / cozo-embedded | graph store | ✓ | 0.7.6 | — |
| faiss-cpu | vector store | ✓ | 1.15.0 | — |
| sqlite3 | kv store | ✓ | 3.53.1 | — |
| pytest, pytest-asyncio | tests | ✓ | 9.1.1 / 1.4.0 | — |
| pandas | pycozo result frames | ✗ | — | `Client(..., dataframe=False)` (already handled by `_cozo_rows`) |
| Non-root user for the GC read-only-subdirectory test | STOR-15 | ✓ | uid 1000 | — |
| External DB servers, Docker | — | not needed | — | — |

**Missing dependencies with no fallback:** none. **Missing with fallback:** pandas.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-asyncio 1.4.0, `asyncio_mode = "auto"`, `addopts = '-m "not live"'` [VERIFIED: pyproject.toml:109-113] |
| Config file | `databasise/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd databasise && PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest tests/stores -q -p no:cacheprovider` (measured: 77 passed in 4.73 s before this phase) |
| Full suite command | `cd databasise && .venv/bin/python -m pytest -q` (do not pass `-m live`) — see timing note below |
| Import style | tests are a package (`databasise.tests...`; `from databasise.tests.seam.test_rest_cors import _patch_health` is used), so every new test directory needs an `__init__.py` (`tests/wirings/` does not exist yet) |

### Phase Requirements -> Test Map (test file named in each STOR requirement)

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| STOR-01 | concurrent query/resolve/health while a graph is held; second OS process gets the named refusal; REST 409 JSON with `refusal_type` | integration (+subprocess) | `.venv/bin/python -m pytest tests/stores/test_graph_lock.py -x -q` | ❌ Wave 0 |
| STOR-02 | monkeypatch `CozoGraphStore.__init__` to raise; `SqliteKVStore.finalize` called exactly once per request across query, ingest, delete_document, resolve_evidence | unit | `.venv/bin/python -m pytest tests/seam/test_build_stores_cleanup.py -x -q` | ❌ Wave 0 |
| STOR-03 | resolve opens only the vector namespace; `faiss.read_index` counter 1 after 5 calls, 2 after rewrite; no kv/graph dirs | integration | `.venv/bin/python -m pytest tests/seam/test_evidence_resolve_stores.py -x -q` | ❌ Wave 0 |
| STOR-04 | `engine.health()` on an empty root leaves the tree empty and reports `absent`; garbage `vector.faiss` reports `corrupted` | integration | `.venv/bin/python -m pytest tests/seam/test_health_probe.py -x -q` | ❌ Wave 0 |
| STOR-05 | four cases: read-only `upsert` refused naming `writes_kv`; `select().delete_by_ids` refused; `reads_kv`+`writes_kv` upserts; `require('mutates_store')` does not read `raw_stores` | unit | `.venv/bin/python -m pytest tests/runner/test_capability_scoping_modes.py -x -q` | ❌ Wave 0 |
| STOR-06 | HippoRAG ingest with a failing later node raises `ForeignEngineRefusalError`; kv and `hipporag-chunks` empty after reopen | integration | `.venv/bin/python -m pytest tests/seam/test_ingest_abort.py -x -q` | ❌ Wave 0 |
| STOR-07 | (a) vector delete reverted by `drop_pending_index_ops`; (b) `delete_document` with a fixture wiring declaring `store_namespaces`: success empties kv/vector/graph in the declared namespaces, failure leaves all unchanged | integration | `.venv/bin/python -m pytest tests/stores/test_delete_commit_contract.py -x -q` | ❌ Wave 0 |
| STOR-08 | either file missing raises `VectorStoreCorruptedError`; `engine.resolve_evidence` on it raises the corruption error | unit + integration | `.venv/bin/python -m pytest tests/stores/test_vector_crash_window.py -x -q` | ❌ Wave 0 |
| STOR-09 | `top_k=0` named error; namespace list excludes dirs without `vector.faiss`; unselected `score_all`/`get_by_id` (and `self_knn`, `iter_vectors`) raise `VectorNamespaceNotSelectedError` | unit | `.venv/bin/python -m pytest tests/stores/test_vector_validation.py -x -q` | ❌ Wave 0 |
| STOR-10 | cascade: after flushed `delete_node('x')`, `node_degree('y')==0`, `get_node_edges('x')==[]`, igraph export has 0 edges; `upsert_edge('y','missing')` creates the node | unit | `.venv/bin/python -m pytest tests/stores/test_graph_delete_cascade.py -x -q` | ❌ Wave 0 |
| STOR-11 | returned dict mutation and caller dict mutation do not change the buffer; `is_empty` True when everything is pending delete | unit | `.venv/bin/python -m pytest tests/stores/test_kv_buffer_isolation.py -x -q` | ❌ Wave 0 |
| STOR-12 | `parse_wiring` reports `unwired-store-effect` for fixture nodes declaring `reads_lexical`/`writes_lexical`/`reads_blob`; engine converts it to a named refusal; shipped `lightrag/base.json` (every arm) and `hipporag/corpus-ingest.json` still parse and run | unit + integration | `.venv/bin/python -m pytest tests/wirings/test_store_effects_wired.py -x -q` | ❌ Wave 0 (directory + `__init__.py` too) |
| STOR-13 | satisfied by removal: grep test that no module imports `stores.blob` | unit (grep) | `.venv/bin/python -m pytest tests/test_removed_stores_absent.py -x -q` (name discretionary) | ❌ Wave 0 (file named by D-15, not by STOR-13) |
| STOR-14 | satisfied by removal (same grep test) | unit (grep) | same | ❌ Wave 0 |
| STOR-15 | (a) `gc_namespace` on a tree with a read-only subdirectory raises `NamespaceGCError` (run as non-root); missing dir does nothing; (b) CLI removes `quarantined-*`, refuses other tokens and a held lock | unit + subprocess | `.venv/bin/python -m pytest tests/test_namespaces_gc.py -x -q` | ❌ Wave 0 |
| STOR-16 | `upsert(['a'], vecs, [{'id':'SHADOW','score':99}])` raises `ReservedMetadataKeyError`; `import_index` strips the keys | unit | `.venv/bin/python -m pytest tests/stores/test_vector_reserved_keys.py -x -q` | ❌ Wave 0 |

Existing tests Phase 10 must keep green or edit (all unprotected): `tests/stores/{test_graph,test_graph_frozen_bugs,test_graph_bulk_export,test_kv,test_vector,test_vector_namespaces,test_vector_score_all,test_vector_self_knn,test_namespace_derivation}.py`, `tests/seam/{test_corpus_status,test_refusal_status_codes,test_rest_transport,test_refusal_catalogue,test_raw_upload_staging,test_evidence_namespace_guard,test_delete_document,test_hipporag_write_path,test_store_isolation,test_leak}.py`, `tests/mcp/test_mcp_refusal_mapping.py`, `tests/parts/test_reference_parts.py`, `tests/parts_core/hipporag/test_graph_construction.py`, `tests/test_embed_startup.py`, `tests/test_phase_success_criteria.py`, `tests/parity/test_cli_builder_refusals.py`.

### Sampling Rate
- **Per task commit:** the single new test file for the touched requirement plus `tests/stores` (about 5 s).
- **Per wave merge:** `tests/stores tests/seam tests/runner tests/parts tests/parts_core tests/validator` with `-p no:cacheprovider`.
- **Phase gate:** full suite green (both `.venv/bin/pytest` and `.venv/bin/python -m pytest`, as RUN-12 requires) before `/gsd-verify-work`.
- **Full-suite baseline (measured this session, before any Phase 10 change):** `1637 passed, 1 skipped, 4 deselected in 273.06s (0:04:33)`. The 4 deselected are the `live` marker. Run it only at wave boundaries.

### Wave 0 Gaps
- [ ] The 14 new test files above (STOR-13/14 collapse into one grep test) and `tests/wirings/__init__.py`.
- [ ] A shared fixture for "HippoRAG ingest with stubbed clients and a node that raises" and a fixture delete wiring + registry (reuse `tests/seam/test_delete_document.py:92-115` and `tests/seam/test_hipporag_write_path.py`).
- [ ] A test-only helper that holds a `graph.cozo` open in a **subprocess** (STOR-01 part b); use `python -I` with the script path outside the repo working directory.
- [ ] No framework install needed.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (seam authentication is an open owner decision for the CONN phases) | — |
| V3 Session Management | no | — |
| V4 Access Control | yes | capability-scoped read-only proxies and engine-only lifecycle methods (D-09); GC CLI accepts only `quarantined-*` tokens (D-16) |
| V5 Input Validation | yes | `ReservedMetadataKeyError`, `top_k` validation, `namespace_dir` token regex `^[A-Za-z0-9-]+$` (`namespaces.py:37`), `validate_evidence_namespace` (exists, `evidence.py:131-135`) |
| V6 Cryptography | no (SHA-256 checksum is integrity, existing) | — |
| V8 Data Protection / error handling | yes | `StoreBusyError` and `StoreFault` bodies never carry the cause, an absolute path or a namespace (R7, R8; `_foreign_fault` precedent) |
| V12 Files | yes | GC `shutil.rmtree` confined to `store_root/<token>`; symlinked top level refused; read-only health probes |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal through a GC token or a digest | Tampering / EoP | `namespace_dir` regex + `quarantined-` prefix + `store_lock`; blob store removed so its digest path disappears |
| Absolute store path disclosed in a refusal | Information disclosure | build `StoreBusyError`/`StoreFault` from fixed text; log the cause once server-side |
| Node mutates a store it declared read-only | EoP | allowlist proxy; every other attribute raises `UndeclaredEffectError` |
| Partial commit leaves a wrong answer on disk | Tampering | prepare-all/commit-all; vector checksum detects the residual window |
| Store-busy used as a probe for internal namespaces | Information disclosure | `store_kind="graph"` only |
| Denial of service by an unbounded snapshot cache | DoS | bounded LRU, stale-key eviction |

## Project Constraints (from CLAUDE.md)

- Work through a GSD command; do not edit outside a GSD workflow.
- Python (>=3.11 per `databasise/pyproject.toml`), local NixOS, embeddable in-process, no external DB servers, no Docker.
- The §18 seam must stay modality-agnostic: the `HealthReport` change must not expose modality names, wiring ids or node ids.
- Contract vocabulary (17 effects, three artifact scopes) is frozen input: do not remove an effect from the `Effect` Literal.
- Evidence standard: no benchmark number settles a decision.
- Style: ruff, target `py311` (`pyproject.toml:115-116`); refusals over silent fallbacks (house style named throughout `stores/`); store modules stay free of `lightrag` imports (`tools/check_import_boundary.py`).
- Commit messages need the `phase/10` trailer (CONTEXT); end commits with the attribution line supplied by the harness.
- Never read `.env*`; never run `-m live`; test files carrying a ledger `test_ref` need the owner's `grant-check-edit` (none required by the plan above).
- Known GSD hazards from project memory: the planner may write `&amp;&amp;` into verify commands and omit `D-NN` citations (one-line orchestrator fixes); GSD reverts all phase requirement IDs on `gaps_found`.

## Sources

### Primary (HIGH confidence)
- Live measurements this session: spike scripts listed under Spike Results, run against `databasise/.venv/bin/python` (pycozo 0.7.6, sqlite 3.53.1). Baseline `tests/stores`: 77 passed in 4.73 s.
- Source read this session: `stores/{graph,kv,vector,base,blob,lexical}.py`, `seam/engine.py` (240-260, 330-470, 727-1139, 1141-1288), `seam/{corpus,evidence,refusals,rest}.py` (relevant ranges), `runner/scheduler.py` (140-330, 425-470, 540-690), `parts_core/__init__.py`, `parts_core/**` store-touching bodies, `parts/schema.py:31-49`, `validator/{parse,errors,blast_radius}.py`, `namespaces.py`, `store_lock.py`, `parity/run_arm.py:72-105`, `pyproject.toml`, `wirings/**.json`.
- `ledger/REQUIREMENTS.json` (Read tool) and `/home/chris/coding/GUI-research/adapters/claude-code/hooks/check-edit-guard.py` (protection rule).
- `.planning/phases/10-stores-locking-data-integrity/10-CONTEXT.md`, `.planning/REQUIREMENTS.md` (STOR-01..16, TOOL-17, LRAG-13/14, HIPP-15), `.planning/ROADMAP.md` Phase 10.

### Secondary (MEDIUM confidence)
- `docs/system-model/CONTRACT.md` grep for `health` (no §18 `HealthReport` definition found).

### Tertiary (LOW confidence)
- None used.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; versions read from the venv.
- Architecture: HIGH for the three prepare/commit mechanisms and the shared-client safety (measured); MEDIUM for the snapshot-cache retry policy and the lock-key design under multiple loops (A2, A7).
- Pitfalls: HIGH — each was found by reading the cited lines or by running the spike.

**Research date:** 2026-10-17
**Valid until:** 2026-11-16 (stable; pycozo is pinned and frozen). Re-verify the protected-test list and `check_edit_grants` at plan time.
