# Phase 12: HippoRAG Fixes - Pattern Map

**Mapped:** 2026-10-19
**Files analyzed:** 22 new/modified
**Analogs found:** 21 / 22
**Scope:** all paths are under `databasise/` (package root) unless stated. All analogs were verified git-tracked (no `.gsd` mirrors involved). No `.env*` or protected seam test files were read.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match |
|---|---|---|---|---|
| `parts_core/hipporag/document_remover.py` (NEW) | part (opaque corpus op) | CRUD delete, batch | `parts_core/lightrag/full_delete.py` (shape) + `parts_core/hipporag/graph_augment_persist.py` (store-proxy body) | role-match |
| `wirings/hipporag/corpus-delete.json` (NEW) | wiring config | batch | `wirings/lightrag/corpus-delete.json` | exact |
| `wirings/hipporag/corpus-ingest.json` (MOD: remover first) | wiring config | batch | itself + `wirings/lightrag/corpus-delete.json` | exact |
| `wirings/hipporag/base.json` (MOD: qa, top_k, consumes_query, prune keys) | wiring config | request-response | itself | exact |
| `parts_core/hipporag/qa.py` (NEW) | part (generator) | request-response | `parts_core/lightrag/generate.py` + `parts_core/lightrag/prompts.py` | exact |
| `parts_core/hipporag/vertices.py` (NEW) | utility | transform | `entity_fact_embed.py:56`, `ppr.py:41`, `passage_edges.py:41` (the three copies) | exact |
| `parts_core/hipporag/__init__.py` (MOD: register 2 parts) | registry | config | itself | exact |
| `parts_core/hipporag/graph_augment_persist.py` (MOD: read-merge-write) | part | CRUD | itself (lines 60-90) | exact |
| `parts_core/hipporag/chunk_embed.py` (MOD: id mint, line ~80) | part | transform | itself | exact |
| `parts_core/hipporag/openie.py` (MOD: chunk passthrough, bounded concurrency, ExtractionFailed) | part | batch | itself (calls at :149/:157) | exact |
| `parts_core/hipporag/{ppr,reset_vector_join,fact_score,dpr_fallback,assemble_result,synonymy_edges,entity_fact_embed}.py` (MOD) | part | request-response | themselves | exact |
| `stores/vector.py` (MOD: `self_knn(ids=)`) | store | batch | itself (:436) | exact |
| `stores/kv.py` or `stores/probes.py` (NEW read-only prefix lister) | store | file-I/O read | `seam/jobs_store.py:45-53` | role-match |
| `seam/refusals.py` (MOD: `ExtractionFailed`, `node_id`) | refusal | request-response | `ForeignEngineRefusalError` V1NotConfigured branch (:787-793) | exact |
| `seam/engine.py` (MOD: `_foreign_fault`, HippoRAG gate, `delete_document`, `corpus_status`, `_node_result_or_refuse`) | engine | request-response | `_write_gate` (:708-730) | exact |
| `foreign/v1_corpus_adapter.py` (MOD: `redact_secrets` `key=` pattern) | utility | transform | `_SECRET_PATTERNS` (:60-64) | exact |
| `seam/rest.py` (MOD: optional selector on `/corpus`, `/corpus/counts`) | route | request-response | `get_corpus` (:496-505) + Phase 11 selector-bearing routes (:358, :414) | role-match |
| `mcp/tools.py` + `mcp/server.py` (MOD: status selector) | route | request-response | the REST change | partial (not read) |
| `wirings/resolve.py` (MOD: `without_recipe_only_nodes` -> ancestors-of-provides) | utility | transform | itself (:148-162) | exact |
| `runner/trace.py`, `runner/scheduler.py` (MOD: token helper, relaxed invariant, degraded from guards) | runner | transform | themselves | exact |
| `tests/parts_core/hipporag/*`, `tests/seam/test_hipporag_write_path.py` (MOD/NEW tests) | test | - | existing files in `tests/parts_core/hipporag/` | exact |
| `evidence/HIPPORAG-PORT-RECORD.md` (MOD) | doc | - | itself | exact |

## Pattern Assignments

### `parts_core/hipporag/document_remover.py` (part, CRUD delete)

**Analog A, wiring and part shape:** `wirings/lightrag/corpus-delete.json` (whole file) and `parts_core/lightrag/full_delete.py` (config carries `doc_id`; `delete_document` stamps it at `seam/engine.py:~1565-1568`).

```json
{ "wiring_id": "lightrag-corpus-delete", "wiring_version": "1",
  "nodes": { "full-delete": { "component": "lightrag/full-delete@0.2.0", "kind": "opaque",
      "effects": ["calls_llm","mutates_store","reads_kv","reads_graph"], "deps": [] } },
  "harnesses": [], "provides": ["full-delete"] }
```
HippoRAG copy: one node `document-remover`, `effects` = `["mutates_store","reads_kv","writes_kv","writes_vector","reads_graph","writes_graph"]` (check against the effect union the scheduler's `CapabilityScopedStores.require` needs), `provides: ["document-remover"]`, plus `"store_namespaces": { "kv": "hipporag-text-chunks", "graph": "hipporag-graph" }` copied from `wirings/hipporag/corpus-ingest.json` (last line). `delete_document` reads `resolved["provides"][0]` and writes `config["doc_id"]` onto it, so the remover must read `ctx.config["doc_id"]`. In `corpus-ingest.json` the ingest path stamps `consumes_documents`; make the remover tolerate empty `documents` (parity `build_hipporag_index.py` runs the ingest wiring directly).

**Analog B, store-proxy body (stage-only, no commit):** `parts_core/hipporag/graph_augment_persist.py:60-90`
```python
graph_store = ctx.stores["graph"]
for vertex_ref in sorted(vertex_refs):
    await graph_store.upsert_node(vertex_ref, {})
...
await graph_store.upsert_edge(src, tgt, {"weight": weight, "edge_types": types_by_pair[pair]})
```
and `chunk_embed.py:~90-115` for the vector/KV handles:
```python
vector_store = ctx.stores["vector"].select(_CHUNKS_NAMESPACE)
kv_store = ctx.stores["kv"]
await kv_store.upsert({record["chunk_id"]: {"content": record["text"]} ...})
```
Remover uses `kv.get_by_id("doc:<id>")`, `kv.delete([...])`, `vector.select(ns).delete_by_ids([...])`, `graph.delete_node(...)` (cascade hidden from `get_edge`/`get_node_edges` per research probe), `graph.get_node_edges(entity)`, `get_edge`, `upsert_edge`. Missing manifest returns `{"removed_entities": []}`, never raises. Part registration: `Part(name_at_version=..., kind=..., structural_depth="opaque", effects=[...], upstream_ref=..., body=..., artifact_scope=...)` as at `graph_augment_persist.py:93-101`.

**Return contract:** `{"removed_entities": [...]}` so `entity-fact-embed` (dep on remover in ingest wiring only) computes `is_new = get_by_id(ref) is None or ref in removed_entities` and emits `new_entities` for `synonymy-edges` (F3).

---

### `parts_core/hipporag/graph_augment_persist.py` (part, CRUD merge)

**Analog:** itself. Current collapse loop (lines 66-85) sums weights per canonical pair then calls `upsert_edge` unconditionally. Change to: `existing = await graph_store.get_edge(src, tgt)` then merge (`cooccurrence_by_chunk` dict summed, synonymy `max`, passage-entity 1.0, `edge_types` union), then still call `upsert_edge` (STOR-06 monkeypatches it). Keep `_canonical_pair` (:52-53). Upsert the `passage-edges` `vertices` stream too (D-02); add `"passage-edges"` vertices to `vertex_refs`.

---

### `parts_core/hipporag/qa.py` (part, request-response generator)

**Analog:** `parts_core/lightrag/generate.py`

**Imports and constants** (lines 20-33): `from databasise.parts.schema import NodeContext, Part`; `from databasise.parts_core.lightrag.prompts import PROMPTS`; `from databasise.runner.trace import TokenAccounting`; `_NAME_AT_VERSION = "lightrag/generator-llm@0.1.0"`.

**Core pattern** (lines 50-76):
```python
query = str(config.get("query", ""))           # consumes_query injects config.query
...
if not context:
    return {"completion": PROMPTS["fail_response"], "tokens": TokenAccounting(counted_by="none"), **echoed}
...
result = await ctx.clients["llm"].chat(messages)
return {"completion": result.text, "tokens": result.tokens,
        "resolved_model_identity": result.resolved_model_identity, **echoed}
```
Part definition (lines 79-86): `kind="generator"`, `structural_depth="stage"`, `effects=["calls_llm"]`. Reuse `PROMPTS["fail_response"]` for the no-passage answer (D-19). Input is `ctx.inputs["assemble-result"]` hydrated passages (not `"assemble"`). Prompt text comes from upstream `rag_qa_musique.py` at `/home/chris/coding/reference-repos/HippoRAG` (d5c8329); avoid the markers `---Candidate Facts---` and `---Recognised Entities---`. Upstream-only: keep qa out of `lightrag/prompts.py`; put the HippoRAG prompt in the new module.

---

### `parts_core/hipporag/vertices.py` (utility)

**Analogs (three duplicates to merge):** `entity_fact_embed.py:56 CHUNK_VERTEX_PREFIX = "chunk:"`, `ppr.py:41 _PASSAGE_VERTEX_PREFIX = "chunk:"`, `passage_edges.py:40-41`:
```python
def _chunk_vertex(chunk_id): return f"{CHUNK_VERTEX_PREFIX}{chunk_id}"
```
ppr readback to change (`ppr.py:84-89`): emit `name[len(prefix):]` for `name.startswith(prefix)` so `items[].id` is the bare sha. reset-vector-join (`reset_vector_join.py:86-93`): key `passage_weights` by `chunk_vertex(doc_id)` instead of bare `doc_id`.

---

### `parts_core/hipporag/openie.py` (part, batch with bounded concurrency)

**Analog:** itself; concurrency bound from scheduler: `runner/scheduler.py:348-365` (`_validated_max_concurrency`), `:446-448` (`asyncio.Semaphore(max_concurrency)`), `:474` (`ctx._semaphore`). Body builds its own `asyncio.Semaphore(int(config.get("max_concurrency", 1)))` (hand-built `NodeContext`s in part tests have no `_semaphore`). Collect with `gather(..., return_exceptions=True)`; on any failure raise an exception whose type maps to `ExtractionFailed` carrying `failed_chunks` and `failure_reasons` (closed codes only). Output gains `chunks` passthrough (D-02). Sentinel: replace `_UNBUDGETABLE_SENTINEL` (line 37) with the shared import from `runner/trace.py`. Existing LLM call shape at `openie.py:149` (`ner_result = await client.chat(`) and `:157` (triples).

---

### `seam/refusals.py` ExtractionFailed + `node_id` (refusal)

**Analog:** `ForeignEngineRefusalError` (`seam/refusals.py:761-797`)

Vocabulary entry (`_FOREIGN_FAILURE_CLASSES`, lines 750-758): add e.g. `"ExtractionFailedError": "ExtractionFailed"` keyed by the cause type name.

Public-attribute-refusal precedent (lines 787-789) to copy for `failed_chunks` / `failure_reasons`:
```python
if self.failure_class == "V1NotConfigured":
    self.missing_keys = sorted(str(key) for key in getattr(cause, "missing_keys", ()))
    self.unsupported_keys = sorted(str(key) for key in getattr(cause, "unsupported_keys", ()))
```
Private-attribute precedent for `node_id` (lines 790, 795-797) and CR-03 (`_internal_node_id`, line 743):
```python
self._cause = cause
@property
def cause(self) -> BaseException: return self._cause
```
Add `self._node_id = node_id` plus read-only `node_id` property; never in `super().__init__` message. REST: `seam/rest.py:137` has the 503-set `{"MissingV1InterpreterError","CorpusOpTimeoutError","DriverUnavailable","V1NotConfigured"}`; `ExtractionFailed` is deliberately not in it (502).

---

### `seam/engine.py` pieces

**HippoRAG gate (D-14, serialise):** analog `_gate_for` / `_write_gate` (`seam/engine.py:708-730`):
```python
gate = _gate_for(working_dir)
if not gate.acquire(blocking=False):
    raise StoreBusyError(store_kind="corpus")
```
Per research F1, wrap this in an `await asyncio.sleep` polling loop with a ceiling for the HippoRAG key (e.g. `store_root / workspace / "hipporag-write"`) and keep `_write_gate` itself unchanged for LightRAG (LRAG-04). Acquire point: after the `_build_stores` call, existing code `engine.py:1307 gate.enter_context(_write_gate(self._v1_working_dir()))` under `gated = family == "lightrag"` (:1294); F1 recommends acquiring before `_build_stores` for HippoRAG. Delete path at `:1584` is unconditional today: select the gate by `wiring_family(query_wiring)`.

**`_foreign_fault` redaction (D-11):** current body (lines 299-308) ends with `logger.error("engine fault: operation=%s failure_class=%s", operation, refusal.failure_class, exc_info=cause)`. Replace `exc_info=cause` with type name + `redact_secrets(...)` of the formatted traceback. `redact_secrets` is at `foreign/v1_corpus_adapter.py:67-73`; add a `key=` pattern to `_SECRET_PATTERNS` (:60-64), e.g. `(re.compile(r"(?i)([?&]key=)[^\s'\",&]+"), r"\1[REDACTED]")`. Apply also at `runner/scheduler.py:606` (`cross_process_failure_cause`).

**`_node_result_or_refuse` (D-09/D-21):** lines 818-826. Pass the failing node id into `_foreign_fault`/the refusal; narrow `if scheduled.get("partial") or stop_reason:` to `if scheduled.get("partial"):`.

**Read-only lister (D-13):** analog `seam/jobs_store.py:45-53`:
```python
if not self._path.is_file():
    return None
with contextlib.closing(sqlite3.connect(f"{self._path.resolve().as_uri()}?mode=ro", uri=True)) as conn:
    row = conn.execute("SELECT ... WHERE job_id = ?", (job_id,)).fetchone()
```
Copy: return empty when the KV sqlite file is absent; open `mode=ro`; `SELECT key ... WHERE key LIKE 'doc:%'`. Confirm the KV table/column names in `stores/kv.py` (not read in full). `corpus_status`/`document_counts` (`engine.py:1681`, `:1721`) gain an optional selector; no-selector path stays byte-identical.

---

### `seam/rest.py` corpus selector routes

**Analogs:** `get_corpus` / `get_corpus_counts` (`rest.py:496-505`) take `Query` params only; selector-bearing routes use a body model `selector: Selector | None = None` (`rest.py:193, 211, 220, 227`) and `engine.query(body.query, body.selector)` (:358). Selector import at `rest.py:113`. For GET routes there is no body; the selector must arrive as a query parameter, parsed in the route body (precedent: the multipart route parses `Selector.model_validate_json(selector)` in the route, not a validator, at `rest.py:458-466`, mapping errors with `refusal_from_errors(exc.errors()) or MalformedSelectorPayloadError(field="selector")`).

`EmptyNamespaceError` (`seam/refusals.py:815-828`, public `store_kind` only) pre-check code is `_refuse_empty_namespaces` (`engine.py:382-397`). D-15 is deferred, so do not add a HippoRAG table.

---

### `wirings/resolve.py` `without_recipe_only_nodes` (D-16)

**Analog:** itself, lines 148-162 (deepcopy, delete recipe-only nodes no one depends on). Generalise in place to keep only ancestors of `provides` (walk `deps` transitively). Keep `engine._without_recipe_only_nodes = without_recipe_only_nodes` alias (`engine.py:~379`). Do not touch `_wiring_effects`.

---

### `runner/trace.py` / `runner/scheduler.py` (D-07, D-21)

- Honesty invariant to relax: `runner/trace.py:123` `if self.partial != self.degraded: raise ValueError(...)`.
- Scheduler result dict (`scheduler.py:698-703`): `"degraded": partial` and `"degradation_reason": stop_reason` become `partial or any(node.guards_fired ...)` with a closed node-free reason code.
- Token helper: model on `entity_fact_embed.py:62-63`:
```python
unbudgetable = any(acc.counted_by == "unbudgetable" for acc in accountings)
counted_by = "unbudgetable" if unbudgetable else accountings[0].counted_by
```
Move to one `sum_token_accountings()` plus the single `UNBUDGETABLE_SENTINEL` in `runner/trace.py`; `openie.py:37` and `seam/tokens.py` import it.

---

### `stores/vector.py` `self_knn(ids=)` (D-05)

**Analog:** itself, `self_knn(self, *, top_k)` at :436, `iter_vectors` at :486. Keep the `ids=None` path unchanged (STOR-09/16 protected). New branch searches pending buffer too, for only the given ids, still one batched search.

---

### `parts_core/hipporag/__init__.py` (registration)

**Analog:** itself (lines 17-47). Add `from databasise.parts_core.hipporag.<new> import HIPPORAG_..._PART`, append to the `HIPPORAG_PARTS` tuple, update module docstring ("thirteen" -> fourteen plus remover). `parts/registry.py:178-182` already merges `HIPPORAG_PARTS`; no registry edit needed.

---

### Tests

**Analogs:** `tests/parts_core/hipporag/` (`conftest.py`, `test_graph_construction.py`, `test_index_side_extraction.py`, `test_ppr.py`, `test_registration.py`, `test_thirteen_positions.py`, `test_dpr_fallback_guard.py`), and `tests/seam/test_hipporag_write_path.py` (do not rename `_DOCUMENT_TEXT`, `_HIPPORAG_CAPABILITY`, `_WORKSPACE`, `_make_engine`, `_StubEmbeddingClient`, `_StubIngestQueryLLMClient`; imported by protected tests). Rules from research F7: import new symbols inside test bodies, one test per HIPP row, assertion-style failures (no bare `pytest.raises` on not-yet-raising paths).

## Shared Patterns

### Stage-only store writes (no commit in parts)
**Source:** `parts_core/hipporag/graph_augment_persist.py` module docstring ("No commit here") and `seam/engine.py` `_commit_all` / `_drop_pending`. **Apply to:** remover, entity-fact-embed, graph-augment-persist.

### Refusal with private cause / allow-listed public fields
**Source:** `seam/refusals.py:761-797`. **Apply to:** `ExtractionFailed`, `node_id`.

### Part declaration
**Source:** `Part(name_at_version, kind, structural_depth, effects, upstream_ref, body, [artifact_scope])` (`parts_core/lightrag/generate.py:79-86`). **Apply to:** remover, qa.

### Sentinel/constants single-definition
**Source:** the three-way `chunk:` prefix duplication and the `unbudgetable` string. **Apply to:** `vertices.py`, `runner/trace.py`.

## No Analog Found

| File | Role | Reason |
|---|---|---|
| Manifest `doc:<id>` record writer/reader | KV record | No per-document manifest exists; use `kv.upsert`/`get_by_id` (`chunk_embed.py` KV pattern) with schema `{chunk_ids, fact_ids, entities, ingested_at}` |

## Findings the planner must carry (from 12-RESEARCH.md, still binding in CONTEXT.md amendments)

- D-14 gate serialises (poll with ceiling), key distinct from the v1 dir; refuse-at-once breaks protected `test_ingest_abort.py` / `test_concurrent_ingest_failure.py`.
- D-15 deferred; no pre-check added.
- F3: thread `removed_entities` -> `new_entities` so re-ingest keeps synonymy edges.
- F4: manifest need not store pairs; walk `get_node_edges` per manifest entity.
- Concurrency bound reuses `config.max_concurrency` (no new key).
- Protected-edit needed (owner `grant-check-edit`): `tests/seam/test_foreign_engine_refusal.py:118` (D-11).
- Use the Read tool, not Bash, for any `tests/seam/` protected file.

## Metadata

**Analog search scope:** `databasise/parts_core/{hipporag,lightrag}`, `wirings/`, `seam/`, `foreign/`, `stores/`, `runner/`
**Files scanned:** ~20 (targeted reads; `mcp/*` and `stores/kv.py` internals not read)
**Pattern extraction date:** 2026-10-19
