# Phase 10: Stores, Locking & Data Integrity - Pattern Map

**Mapped:** 2026-10-17
**Files analyzed:** 27 new/modified (plus deletions)
**Analogs found:** 25 / 27
All paths are relative to `databasise/` (the package dir at repo root). Every analog below is git-tracked source (`git ls-files` checked on `stores/graph.py`, `tests/stores/test_kv.py`, `tests/seam/test_delete_document.py`, `tests/runner/*`; the rest are siblings in the same tracked packages).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `stores/graph.py` (modify: `_ClientRegistry`, `GraphStoreBusyError`, cascade, prepare/commit/abort) | store | CRUD / event-driven | itself (`stores/graph.py:97-140, 287-360`) + `stores/vector.py:68-86` (named-error style) | exact (self) |
| `stores/kv.py` (modify: copies, `is_empty`, prepare/commit/abort) | store | CRUD | itself (`stores/kv.py:64-120`) | exact (self) |
| `stores/vector.py` (modify: `ReservedMetadataKeyError`, buffered delete, validation, rebase, prepare/commit/abort, no-mkdir read open) | store | CRUD / file-I/O | itself (`stores/vector.py:68-137, 344-428`) | exact (self) |
| `stores/base.py` (modify: `prepare`, `commit_prepared`, `abort_prepared`) | model (ABC) | pub-sub lifecycle | itself (`stores/base.py:24-42`) | exact (self) |
| `stores/snapshot.py` (new: committed-snapshot cache + probe helpers) | utility | file-I/O | `stores/vector.py:89-94, 113-137` (`_sha256_of`, checksum load) | role-match |
| `stores/lexical.py`, `stores/blob.py`, `registry_artifact/` + their tests (delete) | store | - | n/a (deletion) | - |
| `parts_core/__init__.py` (modify: `EFFECT_TO_STORE`, `ReadOnlyProxy`, `require`) | middleware (capability guard) | request-response | itself (`parts_core/__init__.py:17-71`) | exact (self) |
| `runner/scheduler.py` (modify `_ScopedStoresView.__getitem__`) | middleware | request-response | itself (`runner/scheduler.py:258-277`) + `_ScopedClientsView` (280+) which already uses an explicit table (`CLIENT_EFFECT_TO_KEY`) | exact |
| `seam/engine.py` (modify: `stores_scope`, `_flush`, `_build_stores(into=)`, health, parse-report check) | service | CRUD / transaction | itself (`engine.py:248-258, 361-388, 805-880, 1091-1139`) | exact (self) |
| `seam/refusals.py` (add `StoreBusyError`, `UnparseableWiringError`, `StoreFault` wording) | model (error catalogue) | request-response | `UnresolvableEvidenceReferenceError` / `InvalidEvidenceNamespaceError` (`refusals.py:684-710`) | exact |
| `seam/rest.py` (`_status_for` 409 branch, `_FAULT_RESPONSES` wording) | route | request-response | itself (`rest.py:114-159`) | exact (self) |
| `seam/corpus.py` (`HealthReport.stores` type) | model | request-response | itself (`corpus.py:285-300`) | exact (self) |
| `validator/parse.py` + `validator/errors.py` (`unwired-store-effect`) | validator | transform | `CODE_EFFECTS_EXCEED_PART` block (`parse.py:204-217`, `errors.py:23-30`) | exact |
| `namespaces.py` (`NamespaceGCError`, `gc_namespace`, docstring) | utility | file-I/O | itself (`namespaces.py:72-111`) | exact (self) |
| `launcher/gc_namespaces.py` (new operator CLI) | CLI | batch / file-I/O | `parity/run_arm.py:234-255` `main()` with `store_lock` | exact |
| `parity/run_arm.py` (modify its `_build_stores` try/finally, `:77-105, 185-203`) | service | CRUD | `seam/engine.py` `_build_stores` | exact |
| `parity/import_index.py` (strip `id`/`score` at upsert sites ~191, 319) | utility | batch | itself | exact (self) |
| `parts_core/hipporag/graph_augment_persist.py` (delete line 84 flush) | part | transform | n/a (removal) | - |
| `parts_core/lightrag/full_ingest.py:186`, `full_delete.py:186`, `parts_core/codebase_memory_mcp.py:271` (admission text) | part | - | n/a (text edit) | - |
| `pyproject.toml:136` (drop `databasise.registry_artifact`) | config | - | n/a | - |
| Tests: `tests/stores/test_graph_lock.py`, `test_graph_delete_cascade.py`, `test_kv_buffer_isolation.py`, `test_vector_validation.py`, `test_vector_reserved_keys.py`, `test_vector_crash_window.py`, `test_delete_commit_contract.py` | test | - | `tests/stores/test_graph.py`, `tests/stores/test_kv.py` | exact |
| Tests: `tests/seam/test_build_stores_cleanup.py`, `test_evidence_resolve_stores.py`, `test_health_probe.py`, `test_ingest_abort.py` | test | - | `tests/seam/test_delete_document.py:92-115`, `tests/seam/test_raw_upload_staging.py:175`, `tests/seam/test_hipporag_write_path.py` | role-match |
| `tests/runner/test_capability_scoping_modes.py` | test | - | `tests/parts/test_reference_parts.py:13,110-115` | role-match |
| `tests/wirings/test_store_effects_wired.py` (+ `tests/wirings/__init__.py`) | test | - | `tests/runner/__init__.py` layout | partial |
| `tests/test_namespaces_gc.py`, `tests/test_removed_stores_absent.py` | test | - | `tests/stores/test_namespace_derivation.py` | role-match |
| `tests/seam/test_refusal_status_codes.py`, `test_rest_transport.py::_REFUSAL_FACTORIES`, `tests/mcp/test_mcp_refusal_mapping.py`, `tests/seam/test_corpus_status.py:166`, `tests/stores/test_vector.py:197-212`, `tests/test_embed_startup.py:207-235`, `tests/test_phase_success_criteria.py` (edit) | test | - | themselves | exact |

## Pattern Assignments

### `stores/graph.py` (store, CRUD) - shared client registry, busy error, cascade, prepare/commit/abort

**Analog:** itself. The registry replaces the per-instance open at `stores/graph.py:102-113`.

**Current open (to be replaced by `_ClientRegistry.acquire`)** (lines 102-113):
```python
def __init__(self, namespace: str, workspace: str, store_root: str | Path) -> None:
    super().__init__(namespace=namespace, workspace=workspace)
    self._dir = Path(store_root) / workspace / namespace
    self._dir.mkdir(parents=True, exist_ok=True)
    self._db_path = self._dir / "graph.cozo"
    self._client = CozoClient("rocksdb", str(self._db_path))
    self._ensure_relations()
    self._pending_node_puts: dict[str, dict[str, Any]] = {}
    ...
```
Keep the four `_pending_*` attribute names (`tests/stores/test_graph.py:25-31` asserts them via `vars(store)`). Pass `dataframe=False` to `CozoClient` (research S5). Registry key = `str(Path(...).resolve())`; a failed open leaves no entry; `finalize()` releases once (idempotent).

**Lock-error detection** (research R7/R8, never forward the text, it embeds the absolute path):
```python
def _is_lock_error(exc: BaseException) -> bool:
    text = str(exc.args[0]) if exc.args else str(exc)
    return "kIOError" in text and ("lock hold by current process" in text or "While lock file" in text)
```
Raise `GraphStoreBusyError(RuntimeError)` defined in this module, `from None`. House style for the named store error: copy `VectorStoreCorruptedError` (`stores/vector.py:68-86`: class docstring explaining the signature, `__init__` storing public fields then `super().__init__(msg)`). Do NOT import `seam.refusals` here (circular, research Pitfall 8).

**Executor dispatch to keep** (lines 136-140):
```python
async def _run(self, script, params=None) -> list[list]:
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, lambda: self._client.run(script, params or {}))
    return _cozo_rows(result)
```

**Core flush pattern to split into prepare / commit_prepared / abort_prepared** (lines 311-354): current `_do_flush` opens `mt = self._client.multi_transact(write=True)`, runs `:put nodes`, `:put edges`, per-id `:rm nodes`, per-edge `:rm edges`, then `mt.commit()`, with `except Exception: with contextlib.suppress(Exception): mt.abort(); raise`. Prepare = same body minus `mt.commit()`, keep `self._prepared_mt`; commit = `mt.commit()` in an executor thread then clear the four buffers; abort = `mt.abort()` in an executor. Add the cascade statement from research R9 before `:rm nodes`:
```
?[src, tgt] := *edges{src, tgt}, src = $id or tgt = $id :rm edges {src, tgt}
```
Constraint: `tests/stores/test_graph_frozen_bugs.py:96-103` scans this file's source for the substring `count(` - never write it (code or string).

**Semantics edits** (lines 287-305): `delete_node` today only pops the pending put and adds to `_pending_node_rms`; `upsert_edge` has no endpoint check. D-10: `delete_node` also drops buffered incident edges from `_pending_edge_puts` and records the id for the flush cascade; `upsert_edge` awaits `has_node` for each endpoint and buffers a `{}` node when missing. `node_degree` / `get_node_edges` / `export_to_igraph` (lines 190-274) must hide disk edges whose endpoint is in `_pending_node_rms`. v1 cascade reference: `v1/lightrag/kg/cozo_impl.py:566-575`.

---

### `stores/kv.py` (store, CRUD) - buffer isolation, `is_empty`, prepare/commit/abort

**Analog:** itself.

**Aliasing bugs to fix** (lines 64-70, 84-87): `get_by_id` returns `self._pending_upserts[id]` by reference; `upsert` stores the caller's dict. Use `copy.deepcopy` at both.

**`is_empty`** (lines 94-99) returns `False` if any pending upsert exists and ignores pending deletes. Fix: committed ids minus `_pending_deletes`, plus `_pending_upserts`.

**Flush pattern to split** (lines 101-116):
```python
async def index_done_callback(self) -> None:
    try:
        for key, value in self._pending_upserts.items():
            self._conn.execute("INSERT INTO kv (id, value) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET value = excluded.value", (key, json.dumps(value)))
        for key in self._pending_deletes:
            self._conn.execute("DELETE FROM kv WHERE id = ?", (key,))
        self._conn.commit()
    except Exception:
        self._conn.rollback()
        raise
    self._pending_upserts.clear()
    self._pending_deletes.clear()
```
prepare = `BEGIN IMMEDIATE` then the same DML, no `commit()`; `commit_prepared` = `commit()` then clear buffers; `abort_prepared` = `rollback()`. Keep `_pending_upserts` surviving a failed flush (`tests/stores/test_kv.py:102-107` swaps `_conn` for a failing wrapper). Sqlite calls stay synchronous inline (module docstring WR-03 exception), so the engine must take its asyncio flush lock BEFORE prepare (research Pitfall 2).

---

### `stores/vector.py` (store, CRUD + file-I/O)

**Analog:** itself.

**Named-error style for `ReservedMetadataKeyError(keys)`** (lines 68-86): `class X(ValueError-subclass)` with docstring, public attrs, then `super().__init__(f"...")`. STOR-09 error is also a `ValueError` subclass here. Keep `VectorStoreCorruptedError.__init__(index_path, expected, actual)` positional signature (`tests/stores/test_vector.py:156`); a missing-file case reuses it (`expected=None, actual="<missing ...>"`).

**Open-time checksum load, to factor into a no-mkdir read path** (lines 113-137):
```python
self._dir.mkdir(parents=True, exist_ok=True)
...
if self._index_path.exists() and self._meta_path.exists():
    meta = json.load(f)
    expected_checksum = meta.get("index_checksum")
    actual_checksum = _sha256_of(self._index_path)
    if expected_checksum != actual_checksum:
        raise VectorStoreCorruptedError(self._index_path, expected_checksum, actual_checksum)
    self._index = faiss.read_index(str(self._index_path)); self._dim = self._index.d
    self._entries = meta["entries"]; self._next_int_id = meta["next_int_id"]
```
Add: exactly one of the two files present raises `VectorStoreCorruptedError` (STOR-08).

**Flush/persist pattern to split** (lines 344-428): `index_done_callback` clones the index, removes replaced ids, `add_with_ids`, then `_persist` writes `vector.faiss.tmp` + `vector.meta.json.tmp` (checksum computed on the tmp index) and finishes with two `os.replace`. Prepare = everything up to and including writing both tmp files, keep `(staging, entries, next_int_id)` in `self._prepared`; commit = the two `os.replace` calls (lines 427-428) then assign `_index/_entries/_next_int_id` on the loop thread; abort = unlink both tmp files. Inside the flush lock, rebase on disk when the committed `(ino, mtime_ns, size)` changed since this instance loaded (research Pitfall 3); use a unique tmp suffix.

**Result-shape sites for D-11** are `{"id": ..., "score": ..., **entry["metadata"]}` at lines 235/267/312 and `{"id": doc_id, **...}` at 338: refuse `id`/`score` keys in `upsert` before touching `_pending` (same place as the length checks at 153-170). Validate `top_k <= 0` before the empty-index early return at 218-219. `MultiNamespaceVectorStore` (line ~492+; fan-out pattern at 534-540) gets `score_all`, `self_knn`, `get_by_id`, `iter_vectors`, each raising `VectorNamespaceNotSelectedError` at call time (`iter_vectors` a plain method, not a generator). `_available_namespaces` (503-510) lists only dirs containing `vector.faiss`.

---

### `stores/base.py` (ABC lifecycle)

**Analog:** itself (`stores/base.py:24-42`). Add three non-abstract async defaults so fixture stores implementing only `index_done_callback` keep working:
```python
async def prepare(self) -> None: return
async def commit_prepared(self) -> None: await self.index_done_callback()
async def abort_prepared(self) -> None: await self.drop_pending_index_ops()
```
Match the existing docstring-per-method style (lines 28-38).

---

### `stores/snapshot.py` (utility, file-I/O) - committed-snapshot cache

**Analog:** `stores/vector.py:89-94` (`_sha256_of`) and 126-137 (checksum + `faiss.read_index` load). Module-level `dict[key, _Snapshot]` + `threading.Lock`; key `(str(resolved dir), (st_ino, st_mtime_ns, st_size) of vector.faiss, same of vector.meta.json)`; stat, read, stat again, retry once, then `VectorStoreCorruptedError` (Pitfall 4). Never `mkdir`. Bounded LRU. Raise the same corruption errors as `FaissVectorStore.__init__`. Same module hosts the read-only probes (kv `mode=ro`, graph `::relations` with `immutable=True`, vector via snapshot).

---

### `parts_core/__init__.py` and `runner/scheduler.py` (capability guard, request-response)

**Analog:** `parts_core/__init__.py:51-71` and `runner/scheduler.py:258-277`.

**Current suffix-split to replace** (`parts_core/__init__.py:64-71`):
```python
def require(self, effect: Effect) -> Any:
    if effect not in self._declared_effects:
        raise UndeclaredEffectError(effect, self._declared_effects)
    store_key = effect.split("_", 1)[-1]
    try:
        return self._raw_stores[store_key]
    except KeyError:
        raise StoreNotWiredError(effect, store_key) from None
```
Replace the `store_key` line with an `EFFECT_TO_STORE` lookup (table in research Pattern 4; values from `parts/schema.py:31-49`). Entries mapped to `None` raise `UndeclaredEffectError` ("no store backs effect X") BEFORE reading `raw_stores`. Mode `"r"` returns a `__slots__` proxy whose `__getattr__` allows only the D-09 per-kind allowlist and raises `UndeclaredEffectError("writes_<kind>", declared)` otherwise. Keep `StoreNotWiredError` for a declared effect whose key is missing (`tests/parts/test_reference_parts.py:13,110-115`).

**Scheduler view to change** (`runner/scheduler.py:270-277`, first-match-wins on suffix):
```python
def __getitem__(self, store_key: str) -> Any:
    for effect in self._declared_effects:
        if effect.split("_", 1)[-1] == store_key:
            handle = self._scoped.require(effect)
            if self._recorder is not None:
                self._recorder(self._node_id, TOUCH_KIND_OBSERVED, store_key)
            return handle
    raise UndeclaredEffectError(f"*_{store_key}", self._declared_effects)
```
New rule: collect all declared effects mapping to `store_key`; if any is `"w"` require that one (a part declaring `["reads_kv","writes_kv"]` must get the writable handle), else the reader. Keep the recorder call. The sibling `_ScopedClientsView` (`scheduler.py:280+`) is the in-repo precedent for an explicit effect-to-key dict instead of suffix splitting (`CLIENT_EFFECT_TO_KEY` from `databasise.clients`).

---

### `seam/engine.py` (service, transaction)

**Analog:** itself.

**Fault builder to reuse for `StoreFault` / `RunIncomplete`** (lines 248-258):
```python
def _foreign_fault(operation, cause, *, failure_class=None) -> ForeignEngineRefusalError:
    refusal = ForeignEngineRefusalError(operation=operation, cause=cause, failure_class=failure_class)
    logger.error("foreign engine fault: operation=%s failure_class=%s", operation, refusal.failure_class, exc_info=cause)
    return refusal
```
Cause logged once server-side; message never carries path/namespace.

**`_build_stores`** (lines 361-388) builds all three in one dict expression, so a graph-open failure leaks the kv connection. Keep name and `(store_root, workspace, resolved=None) -> dict` signature (patched by `tests/seam/test_raw_upload_staging.py:175`, `test_evidence_namespace_guard.py:116-118`, `test_leak.py:47,134`, etc.); add `into: dict | None = None` filled store by store, plus an async context manager (`stores_scope`) that finalizes whatever landed in `into` in `finally`. Translate `GraphStoreBusyError` to `refusals.StoreBusyError(store_kind="graph")` there (`from None`).

**Ingest call-site shape to rework** (lines 818-879): stores built at 818 outside the `try`; staged-upload block (821-852) must stay AFTER store construction (Pitfall 9); unconditional flush loop at 871-872 and `finally` finalize at 877-879. New: after `run_wiring`, if `node_exceptions` empty and not `partial` and no `stop_reason`, run prepare-all then commit-all under one per-(loop, store_root) `asyncio.Lock`; otherwise `drop_pending_index_ops` on every store and `raise _foreign_fault("ingest", cause, failure_class="StoreFault"|"RunIncomplete")`. Same treatment for `delete_document` (flush on success; drop on exception or `status == "fail"`, Q4) and `parse_wiring` calls at 811/982/1165 (check `parsed.report.ok`, raise `UnparseableWiringError(violations=[codes])`, Q5). `_execute_resolved` and `resolve_evidence` get construct+finalize only, never flush.

**Health to replace** (lines 1100-1139): current code instantiates stores (creating dirs/db files) and returns `dict[str, bool]`. Replace with a static `(kind, namespace)` list probed read-only (directory exists -> `absent`; kv `sqlite3.connect("file:...?mode=ro", uri=True)`; graph shared client + `c.run("::relations", {}, True)`; vector via snapshot), keys `"<kind>:<namespace>"` (Q3). Keep the `engine_report` block and the `"ok" if overall_ok else "degraded"` rule (any non-`ok` store makes it degraded).

---

### `seam/refusals.py` (error catalogue)

**Analog:** `InvalidEvidenceNamespaceError` (lines 699-710) for a refusal with a public field; `UnbudgetableParticipantError` (713-730) for the "never expose internals" leading-underscore convention.
```python
class InvalidEvidenceNamespaceError(SeamRefusalError):
    """..."""
    def __init__(self, *, namespace: str):
        self.namespace = namespace
        super().__init__(f"InvalidEvidenceNamespaceError: evidence namespace {namespace!r} must be ...")
```
`StoreBusyError(*, store_kind: str)`: fixed message, public field `store_kind` only. `UnparseableWiringError(*, violations: list[str])`: codes only. Register both in `__all__` (lines 774-815) and in `tests/seam/test_rest_transport.py::_REFUSAL_FACTORIES`. `_FOREIGN_FAILURE_CLASSES` (736-742) is keyed by cause type name; `StoreFault`/`RunIncomplete`/`StoreCorrupted` are passed explicitly as `failure_class=` instead, so no entry is needed. Reword the "foreign (v1) engine failed" docstring/message at 746-767 so a store fault is not called a v1 failure (D-13).

---

### `seam/rest.py` (route)

**Analog:** itself, `_status_for` (lines 134-137) and `_FAULT_RESPONSES` (150-159):
```python
def _status_for(exc: SeamRefusalError) -> int:
    if isinstance(exc, ForeignEngineRefusalError):
        return 503 if exc.failure_class in _ENGINE_UNAVAILABLE else 502
    return 404 if isinstance(exc, _NOT_FOUND_REFUSALS) else 422
```
Add a third branch `if isinstance(exc, StoreBusyError): return 409` (import from refusals), add a `409` entry in `_FAULT_RESPONSES` with `{"model": RefusalBody, "description": ...}`, and reword the 502 description (no longer "the v1 engine run failed"). `tests/seam/test_refusal_status_codes.py:30-34` computes `_CATALOGUE` from `refusals.__all__` minus `_MAPPED_ELSEWHERE`; add `StoreBusyError` to `_MAPPED_ELSEWHERE` with its own 409 test. MCP mapping test: `tests/mcp/test_mcp_refusal_mapping.py`.

---

### `validator/parse.py` + `validator/errors.py` (validator, transform)

**Analog:** the `CODE_EFFECTS_EXCEED_PART` check, `parse.py:204-217`, and codes in `errors.py:23-30`.
```python
extra_effects = set(node.effects) - set(part.effects)
if extra_effects:
    violations.append(Violation(code=CODE_EFFECTS_EXCEED_PART,
        pointer=f"/nodes/{node_id}/effects", message=(...)))
```
Add `CODE_UNWIRED_STORE_EFFECT = "unwired-store-effect"` next to the others in `errors.py`; in `parse_wiring` inside the same `else:` branch, test `set(node.effects) | set(part.effects)` against `{"reads_lexical","writes_lexical","reads_blob"}` and append a `Violation` (accumulate, do not raise). Pointer style `/nodes/{node_id}/effects`.

---

### `namespaces.py` (utility, file-I/O) and `launcher/gc_namespaces.py` (CLI)

**Analog for `gc_namespace`:** itself (lines 103-111, `shutil.rmtree(target, ignore_errors=True)`). New:
```python
target = namespace_dir(store_root, namespace)
try:
    shutil.rmtree(target)
except FileNotFoundError:
    return
except OSError as exc:
    raise NamespaceGCError(namespace) from exc
```
Define `NamespaceGCError` in `namespaces.py` in the `StoreLockedError` style (`store_lock.py:27-37`: store public fields, `super().__init__(f"...")`). Correct the D-07 docstring per D-16. `namespace_dir` (72-84) already validates the `^[A-Za-z0-9-]+$` token; the CLI additionally requires the `quarantined-` prefix.

**Analog for the CLI:** `parity/run_arm.py:234-255` `main()`:
```python
try:
    with store_lock(import_index.DEFAULT_STORE_ROOT):  # D-03
        result = asyncio.run(run_arm(args.arm, args.query))
except (StoreLockedError, *BUILDER_REFUSALS) as exc:
    print(str(exc), file=sys.stderr)
    return 1
```
plus the `if __name__ == "__main__": sys.exit(main())` tail and `argparse` with `main(argv: list[str] | None = None) -> int`. Shape: `python -m databasise.launcher.gc_namespaces --store-root PATH quarantined-<hex> [...]`; map `StoreLockedError`, `NamespaceGCError`, `ValueError` to exit 1 with a stderr message. Launcher layout reference: `launcher/serve_rest.py:70-101` (`main(argv)` returning int, `parser.error` for bad args). Do not register in `[project.scripts]` (tests call `python -m`; `tests/launcher/test_launchers.py:165-170` is ledger-protected and only asserts the two existing scripts).

---

### `parity/run_arm.py` (service)

**Analog:** `seam/engine.py` `_build_stores`/`stores_scope`. `run_arm.py:77-105` has a copy of `_build_stores` and `:185-203` its own try/finally; apply the same incremental-fill + finalize-in-`finally` rule (D-04 last sentence) and the same `EFFECT_TO_STORE` table (D-09).

---

### Tests (new)

**Store unit tests - analog `tests/stores/test_graph.py:1-60`:** module docstring naming plan/behaviours, `from __future__ import annotations`, plain `async def test_*(store_root)` (pytest-asyncio `asyncio_mode = "auto"`, no decorator), `CozoGraphStore(namespace="graph", workspace="ws", store_root=store_root)`, `await store.finalize()` at the end. `store_root` fixture is `tests/conftest.py:36`. Reuse for `test_graph_lock.py`, `test_graph_delete_cascade.py`, `test_kv_buffer_isolation.py`, `test_vector_*`. Subprocess lock holder: run a script with `python -I` kept outside the repo cwd (research Wave 0).

**Engine/seam tests - analog `tests/seam/test_delete_document.py:92-115`** (`_registry_with(part)`, `_make_engine`) and `tests/seam/test_hipporag_write_path.py`; monkeypatch `engine._build_stores` / `engine._corpus_wiring` as in `test_raw_upload_staging.py:175`. HippoRAG has no delete wiring, so STOR-07 supplies a fixture delete wiring (research Pitfall 22).

**REST tests - analog `tests/seam/test_refusal_status_codes.py:1-50`:** `TestClient(create_app(store_root=tmp_path, workspace=..., registry=_make_registry()))`, `_assert_refusal(response, status, refusal_type)`.

**New directory:** `tests/wirings/` needs `__init__.py` (tests are a package; see `tests/runner/__init__.py`).

## Shared Patterns

### Refusals over silent fallbacks, named errors in `stores/`
**Source:** `stores/vector.py:68-86` (`VectorStoreCorruptedError`), `stores/lexical.py` / `parts_core/__init__.py:31-48` (`StoreNotWiredError` docstring states the house style).
**Apply to:** `GraphStoreBusyError`, `ReservedMetadataKeyError`, STOR-09 error, `NamespaceGCError`. Store-level errors stay in `stores/` or `namespaces.py` and never import `databasise.seam.*` (circular import via `seam/__init__.py`).

### Machine-fault logging and no leak of path/cause
**Source:** `seam/engine.py:248-258` `_foreign_fault`; `seam/refusals.py:745-771` (private `_cause`, `refusal_body` skips leading-underscore attrs).
**Apply to:** `StoreBusyError`, every `StoreFault`/`RunIncomplete`/`StoreCorrupted`. Both RocksDB lock texts embed the absolute path, so raise `from None`.

### Executor dispatch for blocking store calls
**Source:** `stores/graph.py:136-140` and `348-349`: `asyncio.get_running_loop().run_in_executor(None, ...)`. kv is the deliberate exception (synchronous inline, `kv.py` module docstring WR-03).

### Cross-process store lock (CLIs only, never library code)
**Source:** `store_lock.py` (`store_lock`, `StoreLockedError`); use pattern at `parity/run_arm.py:248-250`.
**Apply to:** the new GC CLI.

### Tracked-source and ledger discipline
**Apply to all plans:** commit trailer `phase/10`. Protected (ledger `test_ref`) files need no edit per research; if one becomes necessary (e.g. `tests/launcher/test_launchers.py`, `tests/seam/test_rest_corpus_endpoints.py`, `tests/mcp/test_tool_growth_invariant.py`), stop and request the owner's `grant-check-edit`. Re-read `check_edit_grants` at plan time. Never read `.env*`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `_ClientRegistry` (inside `stores/graph.py`) | registry | refcounted resource | No refcounted shared-handle registry exists in the codebase; use research Pattern 1 and the spike-verified error texts. |
| `stores_scope` / `_flush` prepare-all-commit-all helper | service | transaction | No existing two-phase helper; use research Pattern 2 and the "Flush helper shape" code block. |
| `tests/wirings/` directory | test | - | Directory does not exist yet. |

## Planner notes (deviations the excerpts expose)

- `parts_core/hipporag/graph_augment_persist.py:84` calls `await graph_store.index_done_callback()` inside a node; D-09 makes it illegal. Remove it; its four tests (`tests/parts_core/hipporag/test_graph_construction.py:207-300`) read the same pending buffer and need no edit.
- Tests that contradict new semantics (unprotected, must edit): `tests/stores/test_vector.py:197-212` (flush before asserting delete), `tests/seam/test_corpus_status.py:166` (key set), `tests/test_embed_startup.py:207-235`, `tests/test_phase_success_criteria.py` criterion 4 (lines 42-44, 357-358, 498-531; keep 563-571), `tests/seam/test_refusal_status_codes.py`.
- Admission-text edits (research Pitfall 21) need a prior search that no test or hash pins `ConditionVerdict.evidence` text (assumption A4, unverified).
- `writes_artifact` stays a declaration-only marker on three Parts (`lightrag/full-ingest`, `lightrag/embedder-index`, `hipporag/graph-materializer` = node id `graph-augment-persist`); consumers: `validator/blast_radius.py:54`, `runner/scheduler.py:167-176,648`.

## Metadata

**Analog search scope:** `databasise/{stores,seam,runner,validator,parts_core,parity,launcher,tests}`, `namespaces.py`, `store_lock.py`
**Files read:** about 14 source files in full or by range, plus CONTEXT and RESEARCH
**Pattern extraction date:** 2026-10-17
