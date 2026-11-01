# Phase 11: LightRAG Corpus Path - Pattern Map

**Mapped:** 2026-10-17
**Files analyzed:** 27 new/modified (paths under `databasise/` unless noted)
**Analogs found:** 25 / 27
**Tracked-source gate:** all analogs verified in `git ls-files` (foreign/, parity/, parts_core/lightrag/, parts_core/codebase_memory_mcp.py, seam/, mcp/, wirings/). No gitignored mirror paths used.
**Authority:** 11-RESEARCH.md Patterns A-G carry the design and file:line gap table (Pattern F). This map adds the concrete in-repo code to copy.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `parts_core/lightrag/v1_index_sync.py` (NEW) | opaque part (store writer) | batch / transform | `parts_core/lightrag/full_ingest.py` (admission record) + `parity/import_index.py` (readers) | role-match |
| `parts_core/lightrag/full_ingest.py` (@0.2.0) | opaque part | request-response (subprocess) | itself | exact |
| `parts_core/lightrag/full_delete.py` (@0.2.0) | opaque part | request-response | `full_ingest.py` | exact |
| `parts_core/declared_only.py` | config (Part decls) | n/a | itself (`LIGHTRAG_CORPUS_PARTS`) | exact |
| `parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md` | doc/pin | n/a | itself; §8 wording from `parts_core/codebase_memory_mcp.py:225-268` | exact |
| `foreign/v1_corpus_adapter.py` | adapter | request-response | itself | exact |
| `foreign/v1_corpus_driver_script.py` | driver | request-response | itself (`_run_status`, `_run_health`) | exact |
| `parity/import_index.py` (split read/write) | utility | batch | itself | exact |
| `stores/{kv,graph,vector}.py` additive read methods, lazy mkdir | store | CRUD | existing methods in same files (`graph.py:370 get_all_labels`, `vector.py:477 iter_vectors`) | role-match |
| `seam/engine.py` (lock, inbox, mapping, retry, health, empty-ns) | service | request-response | `_flush_lock` (engine.py:517-528), staging block (945-1005), `_corpus_op_or_refuse` (484-499) | exact |
| `seam/jobs_store.py` (NEW, job-family sqlite) | store | CRUD | `seam/trace_store.py:56-75` | exact |
| `seam/refusals.py` (3 new refusals, FERE class) | model | n/a | `StoreBusyError` (refusals.py:777-787) | exact |
| `seam/corpus.py` (`IngestJob.seam_events`, `HealthReport` reasons) | model | n/a | `DeletionOutcome` (corpus.py:122-139) | role-match |
| `seam/rest.py` (retry route, 503 map) | controller | request-response | `delete_document` / `post_documents` routes (rest.py:403-474) | exact |
| `mcp/tools.py` (+ server) retry tool | controller | request-response | `DeleteToolArgs` (tools.py ~140) + `TOOL_NAMES` (:73) | exact |
| `parts_core/lightrag/generate.py` | part | request-response | itself | exact |
| `parts_core/lightrag/assemble.py` | part | transform | itself | exact |
| `parts_core/lightrag/{keywords,embedder_query,entity_lookup,relation_lookup,entity_hydrate_expand,truncator_token_budget,chunk_sel_kg,join_roundrobin,rerank}.py` | part | transform | each file itself (Pattern F table rows 1-16) | exact |
| `parts_core/lightrag/prompts.py` (NEW, duplicated v1 strings) | utility | n/a | `keywords.py:41-72` (already duplicates `keywords_extraction`) | role-match |
| `wirings/lightrag/{corpus-ingest,corpus-delete,base}.json`, `arm-*.json-patch.json` | config | n/a | `corpus-ingest.json` above; `arm-bypass.json-patch.json` (already removes embedder-index + empties recipe) | exact |
| `eval/aa_run.py` (`--arm`) | CLI | batch | itself | exact |
| `tests/fixtures/v1_corpus_driver_stub.py` | test fixture | request-response | itself | exact |
| `tests/seam/test_*` hermetic real-driver harness (NEW) | test | request-response | `tests/parts_core/lightrag/test_full_ingest.py:255` real-venv smoke (skipif pattern) | role-match |
| `tests/seam/test_prompt_drift.py` etc. (NEW AST drift tests) | test | transform | `tests/parts_core/lightrag/test_full_ingest_compat.py:284-333` | exact |
| `evidence/COVERAGE.md` | doc | n/a | existing rows | exact |
| Protected tests (grant-check-edit): `test_rest_corpus_endpoints.py`, `test_ingest_file_name.py`, `test_store_effects_wired.py`, `test_tool_growth_invariant.py` | test | n/a | edit in place | n/a |
| `seam/engine.py` recovery of v1 sync "no-op when dir absent" | (in sync part) | n/a | none | no analog |

## Pattern Assignments

### `parts_core/lightrag/v1_index_sync.py` (opaque part, batch)

**Analog A (admission record + Part declaration):** `parts_core/lightrag/full_ingest.py`

Imports (lines 20-36):
```python
from __future__ import annotations
import asyncio
import hashlib
from pathlib import Path
from typing import Any

from databasise.foreign import run_corpus_op
from databasise.parts.admission import (
    MANIFEST_SOURCE_CODE_INSPECTED,
    AdmissionRecord,
    ConditionVerdict,
)
from databasise.parts.schema import NodeContext
from databasise.runner.trace import TokenAccounting
```
Record skeleton (lines 73-92): `AdmissionRecord(part_name_at_version=..., entry_path=..., storage=..., wall_clock_ceiling_seconds=..., wall_clock_ceiling_basis=..., feed_tier="document", ttl_days=90, network_namespace=..., environment_hash=..., manifest_source=MANIFEST_SOURCE_CODE_INSPECTED, verdicts=(ConditionVerdict(condition=N, verdict=..., evidence=...), ... 1..11))`. Exactly 11 verdicts, non-blank evidence, ceiling > 0 (`validate_admission`, registry.py:123-149).

For conditions 8 and 9 use verdict string `"machine-side-obligation"` and wording style from `parts_core/codebase_memory_mcp.py:238-262` (cond 8 = ttl_days=90 + ledger renewal; cond 9 = part_ref counted as data). Cond 3 carries network isolation by construction plus the spend statement (RESEARCH Pattern G).

**Part kind:** `kind="opaque"`, `structural_depth="opaque"`, `effects=["mutates_store","writes_kv","writes_vector","writes_graph"]` (RESEARCH Finding 6; non-opaque with `mutates_store` derives `confined-unit` and is refused by `host()`).

**Analog B (readers to reuse):** `parity/import_index.py`. After the refactor, the sync calls `read_v1_snapshot(...)` in `asyncio.to_thread`, then `mirror_snapshot(snapshot, kv=ctx.stores["kv"], ...)`. Current reader bodies to lift:

`_import_vector_kind` (import_index.py:175-197):
```python
index = faiss.read_index(str(index_path))
meta = json.loads(meta_path.read_text(encoding="utf-8"))
for fid_str, record in meta.items():
    fid = int(fid_str)
    vectors.append(index.reconstruct(fid))
    ids.append(record["__id__"])
    metadatas.append({k: v for k, v in record.items()
                      if k not in ("__id__", "__vector__", "__created_at__", "id", "score")})
store = FaissVectorStore(namespace=kind, workspace=workspace, store_root=store_root)
await store.upsert(ids=ids, embeddings=np.vstack(vectors), metadatas=metadatas)
await store.index_done_callback()      # <- drop in the sync path; engine._commit_all owns commit
```
`_import_graph` (:221-239): `CozoClient("rocksdb", str(db_path))`, `?[id, attrs] := *nodes{id, attrs}`, `?[src, tgt, attrs] := *edges{src, tgt, attrs}`, `_attrs_to_dict`, `upsert_node/upsert_edge`; flush and `finalize()` removed from the staged path. `import_v1_index` (:242-265) keeps its signature and callers, builds raw stores, calls `mirror_snapshot(prune=False)`, then flushes each (the "separate flushes" the CONTEXT calls out).

**Core rules (RESEARCH Findings 7, Pitfall 6):** absent dir or no `kv_store_doc_status.json` -> no-op return `{"synced": False, ...}`; unreadable -> raise (engine runs `_drop_pending`); order = upsert, then delete stale; self-enforce ceiling with `asyncio.wait_for`; comment `# shortcut: full O(corpus) mirror per write, upgrade by diffing doc_status snapshots`. Return `{"synced": bool, "counts": {...}, "tokens": TokenAccounting(counted_by="none")}`.

---

### `parts_core/lightrag/full_ingest.py` / `full_delete.py` (@0.2.0, opaque, request-response)

**Analog:** self. Single D-06 bump covering all of: effects, `storage`, §8 verdict renumbering, usage, working_dir.

Core call to change (full_ingest.py:220-225), add `working_dir=` and payload keys:
```python
result = await asyncio.to_thread(
    run_corpus_op, "ingest", payload, timeout=INGEST_WALL_CLOCK_CEILING_SECONDS,
)
```
Keep `run_corpus_op` as a module global (test monkeypatch points: `full_ingest.run_corpus_op`, `full_delete.run_corpus_op`, `engine.run_corpus_op`).

Usage branch to make real (:227-239). Replace with the RESEARCH Pattern C rule: `usage["llm"]["call_count"] == 0` -> `TokenAccounting(counted_by="none")`; `call_count > 0 and total == 0` -> `"unbudgetable"` (reuse `_UNBUDGETABLE_TOKENS_SENTINEL`, :47); else `counted_by="v1-subprocess"`. Embedding usage returned in result dict only:
```python
tokens = TokenAccounting(
    prompt_tokens=int(usage.get("prompt_tokens", 0)),
    completion_tokens=int(usage.get("completion_tokens", 0)),
    call_count=int(usage.get("call_count", 1)),
    counted_by=str(usage.get("model") or "v1-subprocess"),
)
```
Result keys stay literal. `full_delete.py` copies the same shape (verdict lines 168-179 there) and adds `calls_llm`; remove any self-reported v2 touches (LRAG-02).

Admission edits: name `@0.2.0`; `storage` from `"machine"` to the v1 working-dir description; drop `writes_artifact`; cond 5/10 evidence stops citing `artifact_scope='quarantined'` (lines 134-138, 184-189); cond 3 and 8 and 9 as in Pattern G. Update module docstring (:9-17).

---

### `foreign/v1_corpus_adapter.py` (adapter, request-response)

**Analog:** self.

Lines to change:
- `working_dir: Path | None = None` (:108) -> required keyword; remove fallback `str(working_dir or DEFAULT_V1_WORKING_DIR)` (:129); drop `DEFAULT_V1_WORKING_DIR` from `__all__` (:~170).
- `CorpusOpSubprocessError.__init__` (:62-65): `stderr.strip()[:2000]` is a head slice; change to `stderr.strip()[-2000:]` and keep tail on `self.stderr`.
- `return json.loads(proc.stdout)` (:149): wrap, raise `CorpusOpMalformedOutputError(RuntimeError)`; add to `_FOREIGN_FAILURE_CLASSES` (refusals.py:736-742) as `"CorpusOpMalformedOutputError": "MalformedDriverOutput"`, keep the `JSONDecodeError` entry.
- exit code 3: `if proc.returncode == 3:` parse stdout `{"error":"v1_not_configured","missing_keys":[...]}` -> `V1NotConfiguredError(missing_keys)` before the generic `CorpusOpSubprocessError`.
Existing named-error house style to copy for new errors (:44-66): `class X(RuntimeError): def __init__(...): self.attr = ...; super().__init__(f"...")`.

---

### `foreign/v1_corpus_driver_script.py` (driver, request-response)

**Analog:** self. Op dispatch must stay `if op == "x": return await _run_x(job)` and each `_run_<op>` must return a literal-key dict and read `job["k"]`/`job.get("k")` only inside itself (AST pin, test_full_ingest_compat.py:232-333).

`_run_status` (driver ~290-327) is the template for new ops; its finalize pattern:
```python
rag = await _build_rag(working_dir)
try:
    counts = await rag.get_processing_status()
    docs_by_id = await rag.aget_docs_by_track_id(track_id) if track_id else await rag.doc_status.get_docs_by_statuses(list(DocStatus))
finally:
    await rag.finalize_storages()
```
Add: `limit < 1 or offset < 0` refusal at top of `_run_status`; `retry_doc_ids` branch and `get_docs_by_statuses` wrapper in `_run_ingest` (RESEARCH Pattern A skeleton); `os.environ["INPUT_DIR"] = job["input_dir"]` before pending-parse enqueue; `token_tracker=` into `_llm_model_func` (:125-142, currently passes `**kwargs` to `openai_complete_if_cache`) and the embedding partial. `_run_health` (:319-329) loses `_build_rag`: return `{"configured": bool, "missing_keys": [...]}` only. Delete `entities`/`entity_info` ops and the `_KNOWN_OPS` entries; fix `UnknownOpError` text (:111-117).

---

### `seam/engine.py` (service, request-response)

**Lock (D-07).** Analog `_flush_lock` (engine.py:517-528), but use `threading.Lock` (cross-loop), not `asyncio.Lock`:
```python
_FLUSH_LOCKS: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, dict[str, asyncio.Lock]] = ...
def _flush_lock(store_root: Path) -> asyncio.Lock:
    locks = _FLUSH_LOCKS.setdefault(asyncio.get_running_loop(), {})
    key = str(Path(store_root).resolve())
```
Copy the `str(Path(...).resolve())` keying; module-level `dict[str, threading.Lock]`; `acquire(blocking=False)` else `raise StoreBusyError(store_kind="corpus")`; release in `finally`.

**Corpus op wrapper (reads).** `_corpus_op_or_refuse` (:484-499) is the template; add `working_dir=self._v1_working_dir()` to the `run_corpus_op` call and gate check. Keep `run_corpus_op` looked up as module global.

**Ingest staging (D-09).** Replace staging block (:945-1005). Keep the exclusive-create idea from:
```python
with open(staged, "xb") as handle:
    wrote_staged = True
    handle.write(document.raw)
...
except FileExistsError:
    if not wrote_staged:
        raise DuplicateDocumentIdError(document_id=document_id) from None
```
Delete `_staged_owner_path`, `_release_staged_upload`, owner-record writes (`os.replace(pending, owner)`). Path becomes `self.store_root / self.workspace / "corpus-inbox" / f"{document_id}{suffix}"`. Keep order: `parse_wiring` -> `_build_stores` -> stage -> `run_wiring` (WR-04).

**Failure and commit path** (:1006-1035), keep unchanged: `_node_result_or_refuse` -> on `ForeignEngineRefusalError` `_drop_pending(stores, self.store_root)`; success -> `await _commit_all(stores, "ingest", self.store_root)`; `except BaseException: if wrote_staged: _log_staged_left(staged)`.

**Job status** (:1193-1220): insert family dispatch before `_corpus_op_or_refuse("status", ...)`; keep `UnknownJobError` raised outside the parse wrapper (comment at :1209).

**Health** (:1258-1293, `_HEALTH_PROBES` :305-316): replace driver `working_dir_present` with `self._v1_working_dir().exists()`; wrap each probe call in try/except -> degraded.

---

### `seam/jobs_store.py` (NEW, store, CRUD)

**Analog:** `seam/trace_store.py:56-75`.
```python
class TraceStore:
    def __init__(self, store_root: str | Path) -> None:
        db_path = Path(store_root) / "trace.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_schema()
```
Copy as `JobFamilyStore` -> `jobs.db`, table `job_families(job_id TEXT PRIMARY KEY, family TEXT NOT NULL, document_id TEXT, created_at TEXT NOT NULL)`. Construct in `Databasise.__init__` beside `TraceStore`. Do not create inside `health()`.

---

### `seam/refusals.py` (model; new `UnsupportedUploadTypeError`, `EmptyNamespaceError`, `DocumentNotInterruptedError`)

**Analog:** `StoreBusyError` (refusals.py:777-787):
```python
class StoreBusyError(SeamRefusalError):
    def __init__(self, *, store_kind: str):
        self.store_kind = store_kind
        super().__init__(f"StoreBusyError: the {store_kind} store is held by another process; retry once it is released")
```
Each new class: keyword-only public fields, name-prefixed message, no paths. Add to `refusals.__all__`, add factory in `tests/seam/test_rest_transport.py::_REFUSAL_FACTORIES`, all map to 422 (SEAM-04 test). "v1 not configured" must NOT be a new class: extend `ForeignEngineRefusalError` (refusals.py:762-770) with `failure_class="V1NotConfigured"` and a conditional `missing_keys` attribute; map to 503 via `_ENGINE_UNAVAILABLE` (rest.py:136).

---

### `seam/rest.py` retry route and `mcp/tools.py` retry tool (controller, request-response)

**REST analog:** `delete_document` (rest.py ~455-465):
```python
@app.delete("/documents/{document_id}", responses=_FAULT_RESPONSES)
async def delete_document(document_id: str, body: DeleteRequest = DeleteRequest()) -> DeletionOutcome:
    return await engine.delete_document(document_id, body.selector)
```
New: `@app.post("/documents/{document_id}/retry", responses=_FAULT_RESPONSES)` returning `IngestJob`, body with optional selector, one statement body (test_rest_transport AST proof requires thin routes except upload).

**MCP analog:** `DeleteToolArgs(_ToolArgs)` (tools.py): `document_id: str; selector: Selector | None = None`. Add `RetryToolArgs`, append `"retry"` to `TOOL_NAMES` (tools.py:73-83), extend its growth comment, register in `mcp/server.py` beside `delete`. Protected `test_tool_growth_invariant.py` (`== 9`, `_TOOL_ARG_MODELS`) needs owner grant. Add §18.5 rows to `evidence/COVERAGE.md`; remove the two entity-op test-support rows.

---

### `seam/corpus.py` (model)

**Analog:** `DeletionOutcome` (corpus.py:122-139) for `seam_events: list[SeamEvent] = []` on `IngestJob` (frozen, `extra="forbid"`). `HealthReport` (corpus.py:285-291) is `extra="forbid"`: add `reasons: list[str] = []` with default; amend the "never affects status" docstring.

---

### `parts_core/lightrag/generate.py` (part, request-response)

**Analog:** self (lines 23-40). Change at :29-35 only:
```python
if context:
    prompt = f"Context:\n{context}\n\nQuestion: {query}"
else:
    prompt = query
client = ctx.clients["llm"]
result = await client.chat([{"role": "user", "content": prompt}])
```
to `client.chat([{"role":"system","content": PROMPTS[template].format(...)}, {"role":"user","content": query}])`, template by `config["prompt_template"]`; no client code change (openai_compat.py:160-163 forwards messages). Short-circuit empty context to `fail_response` text (optional, row 14).

### `parts_core/lightrag/assemble.py` (part, transform)

**Analog:** self (:23-47). Current body reads only `ctx.inputs["rerank"]["items"]` and char budget `int(max_total_tokens) * _CHARS_PER_TOKEN`. Extend with `budget-entities`/`budget-relations` inputs and `kg_query_context` formatting; keep `_CHARS_PER_TOKEN = 4` with `# shortcut: no offline tokenizer, upgrade when one ships`. Naive arm patch must set `/nodes/assemble/deps` back to `["rerank"]` (dangling dep otherwise).

### Remaining kg parts (keywords, embedder_query, entity_lookup, relation_lookup, entity_hydrate_expand, truncator_token_budget, chunk_sel_kg, join_roundrobin, rerank)

Per-file edit targets are in RESEARCH Pattern F table (rows 1-16, with file:line); each is a self-edit, no external analog needed. Part declaration shape to preserve (generate.py:43-50): `Part(name_at_version=..., kind=..., structural_depth="stage", effects=[...], upstream_ref="v1/lightrag/operate.py", body=...)`. Changing any body's effects forces a version bump per the part rules; body-only fixes do not.

### `prompts.py` drift test

**Analog:** `tests/parts_core/lightrag/test_full_ingest_compat.py:284-333` (AST-derive from the v1 source). Parse `v1/lightrag/prompt.py` with `ast`, collect module-level `PROMPTS["name"] = <str constant>`, compare exact strings against the v2 constants; same technique for the `_LEGACY_SUFFIXES` frozenset in `v1/lightrag/parser/registry.py`.

### Wirings

`corpus-ingest.json` (shown above) -> add node:
```json
"v1-index-sync": {"component": "lightrag/v1-index-sync@0.1.0", "kind": "opaque",
  "effects": ["mutates_store","writes_kv","writes_vector","writes_graph"], "deps": ["full-ingest"]}
```
Change `full-ingest` component to `@0.2.0`, effects `["calls_llm","mutates_store","reads_kv","reads_graph"]` (wiring effects must be a subset of the Part's, `CODE_EFFECTS_EXCEED_PART`). Keep `provides: ["full-ingest"]` and `consumes_documents`. Same for `corpus-delete.json` (`provides: ["full-delete"]`, adds `calls_llm`). For LRAG-19 copy `arm-bypass.json-patch.json` ops (`remove /nodes/embedder-index`, `replace /recipe {}`) into naive, hybrid, local, global patches and update each `resulting_node_id_set`; leave `base.json` node and `recipe.embedding` alone (test_embedder_index_reproduction pins it).

### Test harness (hermetic real driver)

**Analog:** `tests/parts_core/lightrag/test_full_ingest.py:255` (`skipif(not _V1_VENV_PYTHON.exists())`) and `_make_fake_run_corpus_op` in `tests/seam/test_corpus_status.py:25-49`. Build per RESEARCH "Hermetic Real-Driver Harness": loopback stdlib `http.server` stub, temp env file via `monkeypatch.setattr(v1_corpus_adapter, "DEFAULT_V1_ENV_PARITY", tmp_env)`. Never read `v1/.env.parity` or `v1/parity-env.txt`; env keys are listed in RESEARCH (values are stub-local). Read protected tests with the Read tool only.

## Shared Patterns

### Refusal-over-silent-fallback (named errors)
**Source:** `foreign/v1_corpus_adapter.py:44-66`, `seam/refusals.py:777-787`.
**Apply to:** every new error (adapter malformed output, V1NotConfigured, three seam refusals). Public fields only; no paths, env values, or env var names except `missing_keys` names for V1NotConfigured (D-12).

### Staged writes then atomic commit; drop on failure
**Source:** `seam/engine.py:1006-1035` (`_node_result_or_refuse`, `_drop_pending`, `_commit_all`).
**Apply to:** ingest, delete, retry, and the sync part (writes only via `ctx.stores`, never calls `index_done_callback`).

### Module-global `run_corpus_op` as patch point
**Source:** `parts_core/lightrag/full_ingest.py:27`, `engine._corpus_op_or_refuse`.
**Apply to:** every caller; fakes accept `**kwargs`, so adding `working_dir=` is invisible to them.

### Driver protocol pin (AST-derived)
**Source:** `tests/parts_core/lightrag/test_full_ingest_compat.py:115-222, 232-333`.
**Apply to:** driver edits and the single `@0.2.0` bump; update `PINNED_INGEST_BOUNDARY`, `PINNED_DELETE_BOUNDARY`, `PINNED_DRIVER_PROTOCOL` and the rule document together (`test_rule_document_and_check_agree`).

### Check ordering vs protected tests
`_build_stores` runs first on every path; D-15 empty-namespace and any new pre-check go after it (`test_build_stores_cleanup.py`).

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| Sync no-op / fail-closed behavior in `v1_index_sync.py` | opaque part | batch | No existing part mirrors an external index into staged stores; use RESEARCH Findings 7 and Pitfall 6 |
| Driver-side `get_docs_by_statuses` wrapper (retry filter) | driver | batch | No precedent; spike-verified skeleton in RESEARCH Pattern A |

## Metadata

**Analog search scope:** `databasise/{foreign,parity,parts_core,seam,mcp,wirings,stores,tests/fixtures}`, plus `git ls-files` tracked check.
**Files read directly:** full_ingest.py, generate.py, assemble.py, corpus-ingest.json, import_index.py (70-300), adapter (40-170), driver (115-335), engine (484-535, 940-1035, 1193-1220), refusals (734-800), trace_store.py (1-75), mcp/tools.py (60-215), rest.py (395-480), codebase_memory_mcp.py (225-270), stub fixture header.
**Not read (hooks blocked or protected):** `ledger/`, `.env*`, `v1/parity-env.txt`, `tests/seam/test_foreign_engine_refusal.py` (guard hook; content taken from RESEARCH).
**Pattern extraction date:** 2026-10-17
