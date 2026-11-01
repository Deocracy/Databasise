---
phase: 10-stores-locking-data-integrity
reviewed: 2026-10-17T00:00:00Z
depth: standard
files_reviewed: 50
files_reviewed_list:
  - databasise/launcher/gc_namespaces.py
  - databasise/namespaces.py
  - databasise/parity/import_index.py
  - databasise/parity/run_arm.py
  - databasise/parity/storage_audit.py
  - databasise/parts_core/__init__.py
  - databasise/parts_core/codebase_memory_mcp.py
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
  - databasise/tools/check_import_boundary.py
  - databasise/tests/parity/test_storage_audit.py
  - databasise/tests/runner/test_capability_scoping_modes.py
  - databasise/tests/runner/test_scheduler.py
  - databasise/tests/seam/test_build_stores_cleanup.py
  - databasise/tests/seam/test_corpus_status.py
  - databasise/tests/seam/test_evidence_resolve_stores.py
  - databasise/tests/seam/test_health_probe.py
  - databasise/tests/seam/test_ingest_abort.py
  - databasise/tests/seam/test_refusal_status_codes.py
  - databasise/tests/seam/test_rest_transport.py
  - databasise/tests/seam/test_store_refusal_status.py
  - databasise/tests/stores/test_delete_commit_contract.py
  - databasise/tests/stores/test_graph_delete_cascade.py
  - databasise/tests/stores/test_graph_lock.py
  - databasise/tests/stores/test_kv_buffer_isolation.py
  - databasise/tests/stores/test_prepared_commit.py
  - databasise/tests/stores/test_vector.py
  - databasise/tests/stores/test_vector_crash_window.py
  - databasise/tests/stores/test_vector_reserved_keys.py
  - databasise/tests/stores/test_vector_validation.py
  - databasise/tests/test_embed_startup.py
  - databasise/tests/test_namespaces_gc.py
  - databasise/tests/test_phase_success_criteria.py
  - databasise/tests/test_removed_stores_absent.py
  - databasise/tests/validator/test_taint_conformance.py
  - databasise/tests/wirings/__init__.py
  - databasise/tests/wirings/test_store_effects_wired.py
findings:
  critical: 1
  warning: 10
  info: 7
  total: 18
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-10-17
**Depth:** standard
**Files Reviewed:** 50
**Status:** issues_found

## Summary

The phase delivers what D-01..D-16 describe: the shared Cozo client registry, prepare-all/commit-all,
the read-proxy allowlists, the snapshot cache, read-only probes and the removals. The 238 new and
changed store, seam, runner and wiring tests I ran pass. Most defects sit at the edges the tests do
not drive: the query path, store-open failures, concurrent failure/abort, and probe edge cases.

Every finding below marked "probe" was reproduced with a script in the session scratchpad. No repo
file was changed.

Answers to the eight executor risks:

1. Unreleased Cozo client: real (WR-09). Three paths leave a graph store unfinalized or open a raw
   `Client` on a registry path. The registry itself has a separate close/acquire race (WR-01).
2. Vacuous graph staging tests: real (WR-10). Run against a do-nothing `prepare` plus a do-nothing
   `commit_prepared`, 2 of 3 graph tests in test_prepared_commit.py still pass. Against "prepare
   does nothing, commit_prepared flushes", all 3 pass, as do the 37 tests in test_ingest_abort.py,
   test_delete_commit_contract.py, test_graph_lock.py and test_graph_delete_cascade.py. No test
   proves the staging happens inside `prepare`.
3. Snapshot cache: all three real (WR-05, WR-06).
4. Health probe: real (WR-07). An empty `graph.cozo` directory makes health create 10 files and
   report `ok`. A garbage `graph.cozo` file reports `corrupted` and creates nothing.
5. Edge upsert cost: not a problem on the shipped bulk paths (IN-01).
6. Delete commit on `not_allowed`: real (WR-03). Latent today, because no shipped v2 delete node
   stages writes.
7. Lifecycle methods engine-only: enforced by name, but bypassable on every proxy (WR-02).
8. Refusal bodies: `StoreBusyError`, `UnparseableWiringError`, `StoreFault`, `RunIncomplete` and
   `StoreCorrupted` bodies are clean. The query path leaks a path, a node id and checksums through
   the envelope instead (CR-01).

## Critical Issues

### CR-01: A store fault inside a query node returns 200 with the store path, an internal node id and checksums in the envelope

**File:** `databasise/seam/engine.py:1311-1324` (`_execute_resolved`), `databasise/runner/scheduler.py:596-626`, `databasise/stores/vector.py:94-99`
**Issue:** D-13 and Q6 say a store error must surface as a named fault. Only the write paths and
`resolve_evidence` do that. `_execute_resolved` never looks at `scheduled["node_exceptions"]`,
`partial` or `stop_reason`. The scheduler records a failed node as
`stop_reason = f"node {node_id!r}: NodeExecutionError: {exc.cause}"`, and `ResponseEnvelope` returns
`stop_reason` and `degradation_reason` unchanged. `_NON_DEBUG_TRACE_FIELDS` also exposes both fields
to `resolve_trace(debug=False)`.

Probe: ingest one HippoRAG document, damage `hipporag-chunks/vector.faiss`, then query. The call
returns normally with `partial=True` and:

`stop_reason = "node 'dpr-fallback': NodeExecutionError: vector store at /tmp/.../hipporag-chunks/vector.faiss is corrupted: sidecar recorded index_checksum '5ab2...', but the on-disk index file's actual checksum is '51ac...'. This is the signature of a crash landing between ..."`

This breaks the "never a path / never internal node ids" invariant (CONTRACT section 18.2, SEAM-02).
Phase 10 widened the exposure by adding the one-file-present corruption case (STOR-08), and
STOR-08 only closed the `resolve_evidence` route.

**Fix:** Apply the write paths' rule to `_execute_resolved`, then redact whatever remains.
```python
# after run_wiring, before building the record
if scheduled.get("node_exceptions"):
    first = next(iter(scheduled["node_exceptions"].values()))
    raise _foreign_fault("query", first, failure_class="StoreFault" if _is_store_fault(first) else None) from first
```
Also stop copying exception text into `stop_reason`: use `f"node failed: {type(cause).__name__}"` in
the scheduler, or map to a fixed vocabulary. A test must assert that no `store_root` string and no
node id appears in `envelope.stop_reason` or `degradation_reason`.

## Warnings

### WR-01: `_ClientRegistry.release` closes the client outside the lock, so a concurrent acquire gets a false `StoreBusyError` (409)

**File:** `databasise/stores/graph.py:160-170`
**Issue:** `release` deletes the entry under `_lock` and calls `entry.client.close()` after leaving
the lock. A thread that calls `acquire` in that gap finds no entry and opens a second RocksDB
`Client` while the first still holds the LOCK file. RocksDB answers "lock hold by current process",
which `_is_lock_error` maps to `GraphStoreBusyError`, which the engine maps to a 409. Nothing was
actually busy.

Probe: with `close()` slowed to 0.5 s, a second `CozoGraphStore` opened 0.1 s after `release`
started raised `GraphStoreBusyError`. In a stress run (3 threads, 540 acquire/release cycles; and
4 coroutines, 160 store lifecycles) I measured 0 false busy. The real window is a few bytecodes,
because the FFI close holds the GIL. The exposure grows with `/health` polling, since every health
call on an idle store opens and closes the client (`probe_graph`) in a worker thread while requests
acquire on the loop thread.
**Fix:** Close inside the critical section, or keep the dying entry in the registry until the close
returns.
```python
with cls._lock:
    ...
    del cls._entries[key]
    entry.client.close()   # still under the registry lock
```

### WR-02: The read-only and engine-only guarantees are bypassable through `_target`, `_mode` and raw attributes

**File:** `databasise/parts_core/__init__.py:114-132`
**Issue:** `_StoreProxy` uses `__slots__ = ("_target", "_kind", "_mode", "_declared")`. Slot
attributes resolve normally, so `__getattr__` never runs for them.
- `proxy._target` returns the raw store, with `index_done_callback`, `prepare`, `drop` and every
  writer. This defeats D-09's allowlist and its "engine-only on every handle" rule.
- `proxy._mode = "w"` turns a read proxy into a writable one.
- A write-mode proxy passes every non-lifecycle name through, so `proxy._conn.commit()` (sqlite),
  `proxy._client` (Cozo) and `proxy._children` (vector, real children with lifecycle methods) are
  reachable.

Probe: on a `reads_kv` proxy, `proxy._target.upsert(...)` plus `index_done_callback()` committed a
row, and `proxy._mode = "w"` made `upsert` succeed. The repo entrenches the escape hatch:
test_scheduler.py and test_storage_audit.py now assert `result["kv"]._target == "the-kv-store"`.
**Fix:** Hold the target in a closure instead of a public-looking slot, or at least refuse
underscore names in both modes.
```python
if name.startswith("_"):
    raise UndeclaredEffectError(name, self._declared, reason=f"store attribute {name!r} is not exposed")
```
Add a test that `proxy._target`, `proxy._mode = ...` and `writes_kv` `proxy._conn` raise.

### WR-03: `delete_document` commits staged writes when the delete reports `not_allowed`

**File:** `databasise/seam/engine.py:1152-1155`
**Issue:** The code drops pending ops only for `status == "fail"` and commits everything else,
including `not_allowed`. D-08 says "flush when the delete succeeds, drop when it fails", and Q4
(drop on `fail`) did not give `not_allowed` a meaning. `not_allowed` is a refusal. A v2 delete node
that stages `delete_node` or `delete_by_ids` and then reports `not_allowed` has those deletes
committed. Probe with the repo's own fixture (`_fixture_engine(..., "not_allowed")`): the outcome is
`not_allowed`, and the seeded kv, vector and graph records were all gone afterwards. Latent today,
because the only shipped delete (LightRAG) is opaque and stages nothing; it becomes data loss with
the first v2 delete node (Phase 11).
**Fix:** Commit only on an explicit success (and, if wanted, `not_found`).
```python
if result.get("status") in ("success", "not_found"):
    await _commit_all(stores, "delete", self.store_root)
else:
    await _drop_pending(stores)
```
Add a parametrized test for `not_allowed` and `not_found` next to the `fail` test.

### WR-04: `FaissVectorStore.abort_prepared` unlinks the shared `.tmp` pair even when this instance never prepared, and the engine drops outside the flush lock

**File:** `databasise/stores/vector.py:546-551`, `databasise/seam/engine.py:489-496,1003,1149-1150`
**Issue:** `_tmp_paths()` is a fixed path per namespace, and `abort_prepared` removes it
unconditionally. `_drop_pending` (called when a run is refused) does not take `_flush_lock`. So if
ingest A fails and drops while ingest B sits between its own `prepare` and `commit_prepared` on the
same namespace (B holds the lock but is awaiting a later store's prepare), A deletes B's staged
files. B's `commit_prepared` then raises `FileNotFoundError` at `os.replace(tmp_index, ...)`.
`_commit_all` commits kv first, so B ends with its kv rows committed and no vectors, reported as
`StoreFault`. Probe: instance B `prepare()`, unrelated instance A `drop_pending_index_ops()`,
`B.commit_prepared()` raised `FileNotFoundError`. Whether A's drop covers B's namespace depends on A
having selected that namespace, which is the normal case when two ingests target one modality.
**Fix:** Unlink only what this instance staged, and serialize the drop with the commit window.
```python
async def abort_prepared(self):
    if self._prepared is not None:
        for tmp in self._tmp_paths():
            tmp.unlink(missing_ok=True)
    ...
```
In `ingest` and `delete_document`, run `_drop_pending` under `_flush_lock(self.store_root)`. Add a
test with two concurrent ingests where one fails.

### WR-05: Snapshot load can report false corruption under concurrent commits, and non-`VectorStoreCorruptedError` read failures escape as raw errors

**File:** `databasise/stores/vector.py:169-227`, `databasise/seam/engine.py:1427-1428`
**Issue:**
- Retry bound: `load_committed` retries once when the stat signature changed during the read, then
  raises `VectorStoreCorruptedError(..., "<changed while being read>")` even when the second read
  produced a self-consistent, checksum-valid snapshot. Two commits within two reads of a large
  index (bulk ingest plus a resolve or health poll) therefore yield a 502 `StoreCorrupted` and a
  health `corrupted` for a healthy store. Probe: forcing a signature change on each read produced
  `VectorStoreCorruptedError`. On the first-ever commit of a namespace the "only one file exists"
  state is also treated as corruption on both attempts.
- Raw errors: `_read_snapshot` lets `FileNotFoundError` (file removed between stat and open),
  `json.JSONDecodeError` (garbage sidecar), `KeyError` (valid JSON without `entries` or
  `next_int_id`) and faiss `RuntimeError` escape. `resolve_evidence` catches only
  `VectorStoreCorruptedError`. Probe: a garbage `vector.meta.json` makes `resolve_evidence` raise a
  bare `JSONDecodeError` (a 500, against Q6), and a file removed mid-read raises
  `FileNotFoundError`.
**Fix:** When the checksum matched, return the snapshot uncached instead of raising. Wrap the read:
```python
try:
    ...read...
except (OSError, ValueError, KeyError, RuntimeError) as exc:
    raise VectorStoreCorruptedError(meta_path, None, f"<unreadable: {type(exc).__name__}>") from exc
```
Treat `FileNotFoundError` as a retry trigger, not corruption. Add tests for a garbage sidecar and a
file removed between stat and read.

### WR-06: Cached snapshots share mutable per-entry dicts and metadata values between all readers

**File:** `databasise/stores/vector.py:177-183,362,465-468`
**Issue:** The cache wraps only the top-level mapping in `MappingProxyType`. The inner
`{"int_id", "metadata"}` dicts and any nested metadata values (lists, dicts) are shared by every
`FaissVectorStore` instance in the process. `get_by_id` and the result builders use
`{"id": ..., **entry["metadata"]}`, which is a shallow copy. Probe: appending to
`reader1.get_by_id("a")["k"]` changed `reader2.get_by_id("a")` ("k": [1, 99]), and assigning
`reader1._entries["a"]["int_id"] = 12345` was visible to `reader2`. A node that edits a retrieved
record in place corrupts every later request until the file changes. The test
`test_the_cached_snapshot_is_read_only_and_writers_keep_their_own_state` only checks the top-level
mapping.
**Fix:** Deep-copy metadata on the way out (`copy.deepcopy(entry["metadata"])` in `get_by_id`,
`query`, `score_all`, `self_knn`), or freeze the entries when building the snapshot. Add a nested
mutation test.

### WR-07: Health probes create files and report `ok` for an empty `graph.cozo` directory, and the exception handling is blind

**File:** `databasise/stores/probes.py:26-69`
**Issue:**
- `probe_graph` only checks `db_path.exists()`. A `graph.cozo` that is an empty directory (for
  example left by a first open that died) is opened by RocksDB, which creates `data/`, `LOCK`,
  `MANIFEST`, `OPTIONS`, `LOG` and `manifest`. Probe: 10 files created, state `ok`, even though no
  relation exists. A directory containing a garbage `data` file reports `corrupted` but still
  creates `graph.cozo/manifest`. A garbage `graph.cozo` file reports `corrupted` and creates
  nothing. STOR-04's "health creates nothing" does not hold for these states, and `ok` is reported
  for a database `_ensure_relations` has never initialised.
- A populated graph is also rewritten on every probe. RocksDB rolls its own files inside
  `graph.cozo/data/` on each open, which the module docstring accepts, so a GUI polling `/health`
  churns the store. This also supplies the traffic behind WR-01.
- `except Exception` maps `PermissionError`, `OSError` and import errors in `probe_graph`, and any
  `OSError` raised in `probe_vector`, to `corrupted`. A zero-byte `kv.sqlite3` (which
  `SqliteKVStore` opens and repairs without complaint) is reported `corrupted` (probe), and the
  `immutable=1` read can race a writer that creates the `-wal` file after the existence check.
**Fix:** Require `graph.cozo/data/CURRENT` (or the `manifest` file) before opening; otherwise return
`absent` or `corrupted` without opening. Require `nodes` and `edges` in the `::relations` rows
before `ok`. Catch the specific exception types and let programming errors surface. Add tests for
the empty-directory, garbage-file and zero-byte states with a before/after tree comparison.

### WR-08: A corrupt kv or graph store fails at open with a raw exception (HTTP 500)

**File:** `databasise/seam/engine.py:425-440` (`_build_stores`); `databasise/stores/kv.py:55-61`; `databasise/stores/graph.py:183-191`
**Issue:** `_build_stores` only translates `GraphStoreBusyError`. Q6 rules that no store error may
reach a caller as a 500, and D-13 maps store errors from nodes and flushes to `StoreFault`, but the
opens happen before any node runs. Probe against `engine.query`: a non-database `kv.sqlite3` raises
`sqlite3.DatabaseError: file is not a database`, and a garbage `graph.cozo` raises a bare
`Exception: db::init ... cannot create directory /tmp/...` (the message carries the path). Health
reports `corrupted` for both, while every real call 500s. The same applies to `ingest` and
`delete_document`.
**Fix:** Wrap the three constructors in `_build_stores`:
```python
except (sqlite3.Error, GraphStoreBusyError) ...
except Exception as exc:
    raise _foreign_fault(operation, exc, failure_class="StoreFault") from exc
```
Use a fixed `failure_class`, and extend `_is_store_fault` to recognise bare pycozo `Exception`s by
origin, not only by exception module.

### WR-09: Three code paths leave a graph store open, or open a raw Client on a registry path

**File:** `databasise/parity/run_cross_modality.py:196`, `databasise/parity/import_index.py:228-234,377-392`, `databasise/parity/build_hipporag_index.py:220`, `databasise/parity/run_comparison.py:356`, `databasise/parity/storage_audit.py:185`
**Issue:**
- `_resolved_store_dirs` builds all stores through `_build_stores` only to read `._dir`, and never
  finalizes them. For each of the two wirings, the graph registry entry (refcount 1) and a sqlite
  connection stay open until the process exits.
- `_import_graph` calls `finalize()` after `index_done_callback()` outside any `try/finally`. An
  exception in upsert or flush leaks the shared client. `_import_text_chunks` and `verify_import`'s
  `v2_store` never finalize their `SqliteKVStore`.
- `_v2_graph` (the verify step) opens `CozoClient("rocksdb", <v2 graph.cozo>)` directly. Probe:
  with one `CozoGraphStore` open on that path, `_v2_graph` raised "RocksDB error: IO error: lock
  hold by current process". It succeeded only after `finalize()`. In the normal success sequence
  the store is finalized first, so the failure appears only after a leak (the two items above).
- The D-04 try-placement fix was applied to `run_arm` only. `build_hipporag_index.py:220`,
  `run_comparison.py:356` and `storage_audit.py:185` still call `_build_stores` before their `try`,
  so a failed graph open leaks the kv connection built just before it.
**Fix:** Compute the directories without opening stores (`Path(store_root)/workspace/ns`). Put the
`_import_graph` body in `try/finally: await store.finalize()`. Read the v2 graph in `_v2_graph`
through `_ClientRegistry.acquire` / `release` (or a read helper in `stores/graph.py`). Move the
remaining `_build_stores(...)` calls inside their `try` with `into=stores`.

### WR-10: Tests that pass without the behaviour they name

**File:** `databasise/tests/stores/test_prepared_commit.py:172-213`, `databasise/tests/seam/test_ingest_abort.py:85-99,213-226`, `databasise/tests/stores/test_delete_commit_contract.py`, `databasise/tests/seam/test_evidence_resolve_stores.py:127-140`, `databasise/tests/seam/test_health_probe.py`
**Issue:** Verified by running the suite against mutated store code.
- Graph staging: with `CozoGraphStore.prepare` replaced by a no-op and `commit_prepared`
  unchanged, `test_graph_prepare_stages_a_node...` fails but
  `test_graph_abort_prepared_leaves_nothing` and
  `test_graph_finalize_while_prepared_aborts_first_and_raises_nothing` pass (nothing is ever
  written, so nothing needs aborting). With `prepare` a no-op and `commit_prepared` calling
  `index_done_callback` (a commit-time flush with no staging), all three graph tests pass, and so
  do the 37 tests across test_ingest_abort.py, test_delete_commit_contract.py, test_graph_lock.py
  and test_graph_delete_cascade.py. `test_a_graph_prepare_failure_aborts_every_store...` replaces
  `prepare` with a function that raises, so it proves engine handling, not graph staging. No test
  asserts `_prepared_mt is not None` after `prepare`, or that a bad statement fails at `prepare`.
- `test_a_successful_hipporag_ingest_still_commits` asserts kv and the chunks vector only, never
  that the graph committed.
- No test covers delete statuses `not_allowed` or `not_found` (WR-03).
- No test mutates a nested snapshot value (WR-06), or drives health on an empty `graph.cozo`
  directory or a zero-byte `kv.sqlite3` (WR-07), or a garbage sidecar through `resolve_evidence`
  (WR-05).
- Concurrency tests never combine a failing ingest with a successful one (WR-04).
**Fix:** Add `assert store._prepared_mt is not None` after `prepare` plus a prepare-time failure
with a real malformed statement. Add the missing graph assertion to the success ingest test, and
the cases listed above.

## Info

### IN-01: `upsert_edge` disk queries are bounded on the shipped bulk paths
**File:** `databasise/stores/graph.py:382-390`
**Issue:** Each unbuffered endpoint costs one `has_node` executor round trip, up to two per edge.
`graph_augment_persist` upserts all nodes first and `import_index` upserts nodes before edges, so
those paths hit the buffer. `test_pending_endpoints_need_no_disk_lookup` pins that. A future part
that adds edges to disk-resident nodes pays 2 sequential queries per edge.
**Fix:** None now. If such a part appears, batch the existence check with one `?[id] := *nodes{id}`
query before the edge loop.

### IN-02: GC token namespace is the same flat space as workspace directories
**File:** `databasise/launcher/gc_namespaces.py:35-44`, `databasise/namespaces.py:79-90`
**Issue:** `namespace_dir` resolves `store_root/<token>`, while seam stores live in
`store_root/<workspace>/<ns>`. A workspace literally named `quarantined-...` would be removed whole
by the CLI. The CLI is operator-run and under the store lock, so the risk is low.
**Fix:** Document the collision, or refuse tokens that match a directory containing store files.

### IN-03: `_StoreProxy` error text for an unknown read attribute names the wrong effect
**File:** `databasise/parts_core/__init__.py:125-126`
**Issue:** `read_proxy.typo` raises `UndeclaredEffectError("writes_kv")`, which points a developer
at a write effect they do not need.
**Fix:** Use `reason=f"store attribute {name!r} is not in the read allowlist"` for non-write names.

### IN-04: Health still opens the Cozo database on every call
**File:** `databasise/stores/probes.py:46-62`
**Issue:** Even for a healthy populated graph the probe takes the process-wide client and rotates
RocksDB files, as the docstring notes. "Read-only" holds for relations and schema but not for the
files inside `graph.cozo/data/`.
**Fix:** If this matters for backups or read-only mounts, probe through a `rocksdb` read-only open,
or reuse an existing registry entry and report `ok` without opening when none exists and `CURRENT`
is present.

### IN-05: `SqliteKVStore.drop_pending_index_ops` does not roll back a prepared transaction
**File:** `databasise/stores/kv.py:138-140`
**Issue:** The graph and vector stores alias `drop_pending_index_ops` to `abort_prepared`; kv only
clears its buffers. The engine never calls it after a prepare today, so this is unreachable, but a
future caller would leave a `BEGIN IMMEDIATE` transaction open.
**Fix:** `async def drop_pending_index_ops(self): await self.abort_prepared()`.

### IN-06: Snapshot cache key can alias after an inode is reused
**File:** `databasise/stores/vector.py:161-166,196-211`
**Issue:** The key is `(ino, mtime_ns, size)`. `os.replace` frees the old inode, and ext4/tmpfs can
hand it back to the next temp file. If two same-size rewrites land inside one coarse mtime tick, a
changed file keeps the old key and the cache serves stale data. Unlikely, since writes take
milliseconds, but the design assumes the inode always changes.
**Fix:** Add `st_ctime_ns`, or a generation counter in the sidecar read cheaply with the stat.

### IN-07: Phase success criterion 4 lost its isolation assertions
**File:** `databasise/tests/test_phase_success_criteria.py:421-470`
**Issue:** The artifact-row, `Pin` and refused-shared-write assertions were deleted with the
registry (D-15). The remaining test checks directory separation and GC. The docstring points to
`tests/validator/test_blast_radius.py` for "an opaque node cannot write shared"; that coverage is
validator-level, not a runtime write refusal.
**Fix:** Keep as is if the owner accepts the D-15 trade, but record it in the phase summary so the
Phase 1 criterion is not read as still covering the runtime write path.

---

_Reviewed: 2026-10-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
