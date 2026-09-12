# Phase 3: LightRAG Query Side - Pattern Map

**Mapped:** 2026-08-31
**Files analyzed:** ~30 (17 part bodies + embedder-index + clients package + wirings + parity harness + schema/registry edits)
**Analogs found:** 30 / 30 (all have a same-repo analog; several share one analog)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `databasise/parts/schema.py` (edit: add `clients` field to `NodeContext`) | model | request-response | `databasise/parts/schema.py` itself (existing `NodeContext`/`Part`) | exact — in-place edit |
| `databasise/parts_core/lightrag/keywords.py` | service (LLM-calling part) | request-response | `databasise/parts_core/fake_llm_caller.py` | exact (role+flow) |
| `databasise/parts_core/lightrag/embedder_query.py` | service (embedding-calling part) | request-response | `databasise/parts_core/fake_llm_caller.py` (calls_llm→calls_embedding swap) | role-match |
| `databasise/parts_core/lightrag/entity_lookup.py` | service (vector-read part) | CRUD (read) | `databasise/parts_core/fake_retriever.py` | exact |
| `databasise/parts_core/lightrag/relation_lookup.py` | service (vector-read part) | CRUD (read) | `databasise/parts_core/fake_retriever.py` | exact |
| `databasise/parts_core/lightrag/entity_hydrate_expand.py` | service (graph-read part, looped single-item calls) | CRUD (read) | `databasise/stores/graph.py` (`get_node`/`node_degree`/`has_edge` single-item methods) + `databasise/parts_core/fake_retriever.py` for the part shape | role-match |
| `databasise/parts_core/lightrag/relation_hydrate_expand.py` | service (graph-read part) | CRUD (read) | same as above | role-match |
| `databasise/parts_core/lightrag/join_entities.py`, `join_relations.py`, `join_chunks.py` | transform (join/merge, no effects) | transform | `databasise/parts_core/passthrough.py` | role-match |
| `databasise/parts_core/lightrag/budget_entities.py`, `budget_relations.py` | transform (token-budget truncation, no effects) | transform | `databasise/parts_core/passthrough.py` | role-match |
| `databasise/parts_core/lightrag/chunk_vector.py` | service (vector-read part) | CRUD (read) | `databasise/parts_core/fake_retriever.py` | exact |
| `databasise/parts_core/lightrag/chunk_sel_kg.py` | transform (declares `reads_vector` per §19.9 fallback-reachability even on `WEIGHT`-only config) | transform | `databasise/parts_core/fake_retriever.py` (for the declare-but-may-not-use pattern) | role-match |
| `databasise/parts_core/lightrag/heading_backfill.py` | service (KV-read part) | CRUD (read) | `databasise/parts_core/fake_llm_caller.py` (for the `ctx.stores["kv"]` access shape only, not the LLM part) | role-match |
| `databasise/parts_core/lightrag/rerank.py` | service (pass-through, declares `calls_rerank` per D-09/§19.9) | request-response (no-op) | `databasise/parts_core/passthrough.py` + `databasise/parts_core/fake_llm_caller.py` (for the "declare effect, minimal real body" shape) | role-match |
| `databasise/parts_core/lightrag/assemble.py` | transform | transform | `databasise/parts_core/passthrough.py` | role-match |
| `databasise/parts_core/lightrag/generate.py` | service (LLM-calling part, terminal node) | request-response | `databasise/parts_core/fake_llm_caller.py` | exact |
| `databasise/parts_core/lightrag/embedder_index.py` | service (index-recipe node, `writes_artifact` scope=`quarantined`) | file-I/O / batch | `databasise/parts_core/declared_only.py`'s `LIGHTRAG_FULL_INGEST_PART` (for the `artifact_scope="quarantined"` + opaque-adjacent shape) + `databasise/parts_core/fake_llm_caller.py` (for a real embedding-calling body) | role-match |
| `databasise/clients/__init__.py` | provider (capability-scoped client accessor) | request-response | `databasise/parts_core/__init__.py`'s `CapabilityScopedStores` | exact (structural mirror) |
| `databasise/clients/base.py` | model (protocol/ABC) | request-response | `databasise/stores/base.py`'s `StorageNameSpace` lifecycle ABC | role-match |
| `databasise/clients/openai_compat.py` | service (external HTTP client wrapper) | request-response | `databasise/stores/vector.py` (module-docstring provenance/guard-import style) — no direct analog exists for an HTTP client; treat as **no analog**, build from RESEARCH.md's `openai` SDK guidance | no analog (see below) |
| `databasise/runner/scheduler.py` (edit: thread `clients` into `NodeContext` construction, mirror `_ScopedStoresView`) | middleware (dispatch/execution) | event-driven | `databasise/runner/scheduler.py` itself (`_ScopedStoresView`, `_resolve_identities`, node-dispatch loop) | exact — in-place edit |
| `databasise/parts/registry.py` (edit: register 18 new parts, retire `LIGHTRAG_QUERY_SIDE_PART` stub) | config/registry | CRUD (register) | `databasise/parts/registry.py` itself (`_TRACER_PARTS` dict pattern) | exact |
| `databasise/parts_core/declared_only.py` (edit: remove `LIGHTRAG_QUERY_SIDE_PART`) | config | CRUD | itself | exact |
| `databasise/wirings/lightrag/base.json` (or `databasise/evidence/wirings/`) | config (wiring document) | config | `docs/system-model/wirings/lightrag-base.json` (copy content) + `databasise/evidence/wirings/w1-lightrag-query-side.json` (repo's own registered-wiring JSON shape) | exact |
| `databasise/wirings/lightrag/arm-{hybrid,local,global,naive,bypass}.json-patch.json` | config (RFC 6902 patch) | config | `docs/system-model/wirings/lightrag-arm-*.json-patch.json` | exact |
| `databasise/parity/import_index.py` | service (file-I/O, one-time import + hash verification) | file-I/O / batch | `databasise/stores/vector.py` (SHA-256 checksum + `os.replace` commit pattern) + `databasise/tools/check_import_boundary.py` (checked-artifact + `Violation` dataclass reporting style) | role-match |
| `databasise/parity/run_comparison.py` | service (orchestrates two arms, deterministic diff) | batch / event-driven | `databasise/evidence/falsifier2.py` (loads named wirings, resolves against registry, renders committed Markdown evidence) | exact (closest available precedent) |
| `databasise/parity/storage_audit.py` | service (machine-checked per-node audit) | batch | `databasise/tools/check_import_boundary.py` (`Violation` dataclass, `scan_tree`-style walk-and-report, exit-code `main()`) | exact |
| `databasise/tools/check_import_boundary.py` (edit: extend to assert no `parts_core/lightrag/*` reaches `v1.`) | utility | batch | itself (`_FORBIDDEN_IMPORT_ROOTS`, `scan_tree`) | exact — in-place edit |
| `databasise/tests/parts_core/lightrag/test_*.py` | test | request-response | `databasise/tests/parts/test_reference_parts.py` (pattern for testing a `Part.body` against a raw `NodeContext`) | exact |
| `databasise/tests/parity/test_*.py` | test | batch | `databasise/tests/stores/test_graph_frozen_bugs.py` (non-skippable regression-suite style: "no test in this module may carry a pytest skip or xfail marker") | role-match |
| `.planning/phases/03-lightrag-query-side/03-GATE-AMENDMENT.md` | doc (amendment record) | — | `.planning/phases/02-falsifier-gate/02-GATE-01-WAIVER.md` | exact |

## Pattern Assignments

### `databasise/parts/schema.py` — add `clients` to `NodeContext`

**Analog:** itself, lines 84-95 (`databasise/parts/schema.py`)

```python
@dataclass
class NodeContext:
    node_id: str
    config: dict[str, Any] | None
    inputs: dict[str, Any]
    stores: dict[str, Any]
    clients: dict[str, Any]   # NEW, D-06 — same shape/placement as `stores`
```

Follow the existing docstring convention (explain the calling-convention contract) rather than adding a bare field.

---

### LLM/embedding-calling parts (`keywords.py`, `embedder_query.py`, `generate.py`, `embedder_index.py`)

**Analog:** `databasise/parts_core/fake_llm_caller.py` (73 lines, read in full)

**Imports pattern:**
```python
from __future__ import annotations
from typing import Any
from databasise.identity.canon import config_hash
from databasise.identity.instance import cache_partition_key
from databasise.parts.schema import NodeContext, Part
from databasise.runner.trace import TokenAccounting
```

**Core pattern — cache-keyed call + TokenAccounting (lines 33-63):**
```python
def _prompt_cache_key(prompt: str) -> str:
    return cache_partition_key(_NAME_AT_VERSION, config_hash({}), [], {"prompt": prompt})

async def _fake_llm_caller_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    prompt = str(config.get("prompt", ""))
    cache_store = ctx.stores["kv"]
    partition_key = _prompt_cache_key(prompt)
    cached = await cache_store.get_by_id(partition_key)
    cache_hit = cached is not None
    call_count = (cached["call_count"] if cache_hit else 0) + 1
    ...
    accounting = TokenAccounting(
        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
        cached_read_tokens=prompt_tokens if cache_hit else 0,
        call_count=call_count, counted_by=_TOKENIZER_ID,
    )
    await cache_store.upsert({partition_key: {"completion": ..., "call_count": call_count}})
    return {"completion": ..., "cache_hit": cache_hit, "tokens": accounting}
```

**Real ported nodes must replace the canned completion with `ctx.clients["llm"]` / `ctx.clients["embedding"]` calls** (D-06) — this fake is the return-shape and cache-discipline template only, not the network-call template (see Shared Patterns → LLM/embedding client below).

**Effects declaration lesson (module docstring lines 6-16):** this part originally declared `effects=["calls_llm"]` alone and broke the first time it ran through the real scheduler, because touching `ctx.stores["kv"]` requires a matching `*_kv` effect too. Every new part touching a store AND a client must declare both — do not copy only the "headline" effect.

**Registration pattern:**
```python
FAKE_LLM_CALLER_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="llm-caller",
    structural_depth="stage",
    effects=["calls_llm", "writes_kv"],
    upstream_ref=None,
    body=_fake_llm_caller_body,
)
```
For the real ports, set `upstream_ref="v1/lightrag/operate.py"` (or the specific function's file) per CONTRACT §7 — **locate the actual function by grep, never trust PARTS.md's cited line numbers** (confirmed stale in RESEARCH.md's Pitfall 5).

---

### Vector/graph-read parts (`entity_lookup.py`, `relation_lookup.py`, `chunk_vector.py`, hydrate/expand nodes)

**Analog:** `databasise/parts_core/fake_retriever.py` (34 lines, read in full)

```python
async def _fake_retriever_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    query = str(config.get("query", ""))
    results = list(_FIXTURE_CORPUS.get(query, []))
    return {"query": query, "results": results}

FAKE_RETRIEVER_PART = Part(
    name_at_version="parts-core/fake-retriever@1.0.0",
    kind="retriever",
    structural_depth="stage",
    effects=["reads_vector"],
    upstream_ref=None,
    body=_fake_retriever_body,
)
```

Real bodies replace the fixture dict lookup with `ctx.stores["vector"].query(...)` / `ctx.stores["graph"].get_node(...)` etc. For `entity-hydrate-expand`/`relation-hydrate-expand`: `databasise/stores/graph.py` exposes **only single-item methods** (`get_node`, `has_edge`, `node_degree`, `get_all_labels`) — no batch equivalent. RESEARCH.md's own recommendation (Open Question 1): loop single-item calls rather than writing a new Cozo aggregation query, since `count()`-shaped aggregation re-triggers frozen bug #244. Do not add a batch method without running it against `databasise/tests/stores/test_graph_frozen_bugs.py` first.

---

### Transform/join/budget parts with no store or client effects (`join_*`, `budget_*`, `assemble.py`)

**Analog:** `databasise/parts_core/passthrough.py` (same shape as `registry.py`'s `_passthrough_body`, lines 51-53)

```python
async def _passthrough_body(ctx: NodeContext) -> dict[str, Any]:
    return {"node_id": ctx.node_id, "inputs": dict(ctx.inputs)}
```

Real join/budget bodies read `ctx.inputs[dep_name]` for each declared `deps` entry, merge/truncate, and return the merged dict — no `ctx.stores`/`ctx.clients` access, `effects=[]`.

---

### `rerank.py` — declared-but-off pass-through (D-09)

**Analog:** `databasise/parts_core/passthrough.py` (no-op shape) + `databasise/parts_core/declared_only.py`'s declare-without-behaving pattern (lines 27-38, `CODEBASE_MEMORY_MCP_PART`) for the "declare an effect the config doesn't currently exercise" idea.

```python
RERANK_PART = Part(
    name_at_version="lightrag/rerank@0.1.0",
    kind="rerank",
    structural_depth="stage",
    effects=["calls_rerank"],   # declared per §19.9 fallback-reachability even though config
                                 # below makes the body a no-op — mirrors chunk-sel-kg's
                                 # declare-reads_vector-on-WEIGHT-only-config precedent
    upstream_ref="v1/lightrag/operate.py",
    body=_rerank_body,           # returns ctx.inputs["chunks"] unchanged when config disables rerank
)
```

---

### `embedder_index.py` — the 18th, index-recipe node

**Analog:** `databasise/parts_core/declared_only.py`'s `LIGHTRAG_FULL_INGEST_PART` (lines 43-51) for the `artifact_scope="quarantined"` shape, combined with `fake_llm_caller.py`'s real-body/TokenAccounting pattern (this node gets a real body, unlike the declaration-only ingest stub).

```python
LIGHTRAG_FULL_INGEST_PART = Part(
    name_at_version="lightrag/full-ingest@0.1.0",
    kind="opaque",
    structural_depth="opaque",
    effects=["calls_llm", "writes_artifact", "reads_kv", "reads_graph"],
    upstream_ref="v1/lightrag/pipeline.py",
    body=None,
    artifact_scope="quarantined",
)
```
`embedder-index` mirrors the `artifact_scope="quarantined"` field (its effective depth is `opaque` per §L.2) but MUST have a real `body` (D-03: authored, registered, validated by sample reproduction against v1's stored vectors) — do not leave it `body=None`.

---

### `databasise/clients/__init__.py` — `CapabilityScopedClients`

**Analog:** `databasise/parts_core/__init__.py`'s `CapabilityScopedStores` (lines 51-71, read in full) — mirror exactly, per RESEARCH.md Pattern 1.

```python
class CapabilityScopedStores:
    def __init__(self, raw_stores: dict[str, Any], declared_effects: list[Effect]):
        self._raw_stores = raw_stores
        self._declared_effects = list(declared_effects)

    def require(self, effect: Effect) -> Any:
        if effect not in self._declared_effects:
            raise UndeclaredEffectError(effect, self._declared_effects)
        store_key = effect.split("_", 1)[-1]  # "reads_kv" -> "kv"
        try:
            return self._raw_stores[store_key]
        except KeyError:
            raise StoreNotWiredError(effect, store_key) from None
```

Mirror as:
```python
_CLIENT_EFFECT_TO_KEY = {"calls_llm": "llm", "calls_embedding": "embedding", "calls_rerank": "rerank"}

class CapabilityScopedClients:
    def __init__(self, raw_clients: dict[str, Any], declared_effects: list[Effect]):
        self._raw_clients = raw_clients
        self._declared_effects = list(declared_effects)

    def require(self, effect: Effect) -> Any:
        if effect not in self._declared_effects:
            raise UndeclaredEffectError(effect, self._declared_effects)
        client_key = _CLIENT_EFFECT_TO_KEY[effect]
        try:
            return self._raw_clients[client_key]
        except KeyError:
            raise ClientNotWiredError(effect, client_key) from None
```
Reuse `UndeclaredEffectError` from `databasise.parts_core` rather than redefining it; add a `ClientNotWiredError` sibling to `StoreNotWiredError`.

**Error handling pattern** (same file, lines 31-48, `StoreNotWiredError`) — copy its exact refusal-with-both-names style rather than a bare `KeyError`.

---

### `databasise/runner/scheduler.py` — threading `clients` through dispatch

**Analog:** itself, `_ScopedStoresView` (lines 213-236) and the node-dispatch body (lines ~350-365)

```python
class _ScopedStoresView:
    def __init__(self, scoped: CapabilityScopedStores, declared_effects: list[str]) -> None:
        self._scoped = scoped
        self._declared_effects = list(declared_effects)

    def __getitem__(self, store_key: str) -> Any:
        for effect in self._declared_effects:
            if effect.split("_", 1)[-1] == store_key:
                return self._scoped.require(effect)
        raise UndeclaredEffectError(f"*_{store_key}", self._declared_effects)
```
and the construction call site:
```python
scoped_stores = _ScopedStoresView(CapabilityScopedStores(stores, part.effects), part.effects)
ctx = NodeContext(node_id=node_id, config=node.config, inputs=inputs, stores=scoped_stores)
```
Add a `_ScopedClientsView` mirroring `_ScopedStoresView`, and thread a `clients: dict[str, Any]` parameter through the same call chain (`run_wiring` → the per-node dispatch function → `NodeContext(...)`), exactly parallel to how `stores` already flows. This is the **single call site** RESEARCH.md's own confirmed-by-reading note identifies (`scheduler.py:353`-equivalent construction line) — do not thread `clients` through any other path.

---

### `databasise/parts/registry.py` — registering the 17+1 new parts

**Analog:** itself, `_TRACER_PARTS` dict (lines 64-80) and `DeclarationOnlyPartError` (lines 37-48)

```python
_TRACER_PARTS: dict[str, Part] = {
    "core/passthrough@1.0.0": Part(
        name_at_version="core/passthrough@1.0.0",
        kind="passthrough",
        structural_depth="stage",
        effects=[],
        upstream_ref=None,
        body=_passthrough_body,
    ),
    ...
}
```
Add a parallel `_LIGHTRAG_PARTS: dict[str, Part] = {...}` in `databasise/parts_core/lightrag/__init__.py`, imported and merged into the same registry dict `default_registry()` builds from (check `registry.py`'s `default_registry()`/equivalent assembly function for the merge point). Retire `LIGHTRAG_QUERY_SIDE_PART` from `databasise/parts_core/declared_only.py`'s `DECLARED_ONLY_PARTS` tuple (lines 53-57) in the same change — do not leave both a stub and a real part registered under different names, since `docs/system-model/wirings/lightrag-base.json`'s node table must resolve entirely against the real ports.

---

### Wiring JSON files

**Analog:** `docs/system-model/wirings/lightrag-base.json` and its five `lightrag-arm-*.json-patch.json` siblings (content must be byte-for-byte reproduced, modulo `illustrative-only` status fields) + `databasise/evidence/wirings/w1-lightrag-query-side.json` (repo's own registered-wiring JSON shape, read in full):

```json
{
  "wiring_id": "w1-lightrag-query-side",
  "title": "Decomposed lightrag-local query side",
  "nodes": {
    "retrieve": {
      "component": "parts-core/fake-retriever@1.0.0",
      "kind": "retriever",
      "effects": ["reads_vector"],
      "deps": []
    }
  },
  "boundary_knobs": [ ... ]
}
```
Copy this top-level shape (`wiring_id`, `title`, `nodes: {node_id: {component, kind, effects, deps, config?}}`) for the real `databasise/wirings/lightrag/base.json`. Location is Claude's Discretion per CONTEXT.md — either `databasise/wirings/lightrag/` or alongside `databasise/evidence/wirings/`; either way it must sit beside `docs/system-model/wirings/lightrag-base.json`'s node/dep/config content, never re-derive it.

---

### Parity harness (`parity/import_index.py`, `run_comparison.py`, `storage_audit.py`)

**Analog for `run_comparison.py`:** `databasise/evidence/falsifier2.py` (loads named wirings, resolves against `default_registry()`, computes derived fields through the real validator functions — "never a reimplementation" — renders committed Markdown a second author can read):
```python
from databasise.parts.registry import PartRegistry, default_registry
from databasise.validator.blast_radius import blast_radius_violations
from databasise.validator.depth import effective_depth
from databasise.validator.execution_mode import derive_execution_mode
```
Mirror this shape: load both arms' resolved wirings, run each through the real `run_wiring`/scheduler path (not a reimplementation), diff `ScoredItem` sets, and render a committed Markdown report — same "evidence ships as committed, re-runnable files" house style stated in CONTEXT.md's Established Patterns.

**Analog for `storage_audit.py` and `import_index.py`'s reporting shape:** `databasise/tools/check_import_boundary.py`'s `Violation` frozen dataclass + `scan_tree`/`main()` exit-code convention (lines 51-62, 122-180):
```python
@dataclass(frozen=True)
class Violation:
    path: str
    line: int
    reference: str
    kind: str

def main(argv: list[str] | None = None) -> int:
    ...
    if not violations:
        return 0
    for v in violations:
        print(f"{v.path}:{v.line}: [{v.kind}] {v.reference}")
    return 1
```
D-15's per-node storage-ownership audit and D-02's import-verification checks both want this exact "collect `Violation`-shaped records, print one line each, exit 1 if any exist, exit 0 clean" convention rather than a bespoke report format.

**Analog for `import_index.py`'s commit-atomicity discipline:** `databasise/stores/vector.py`'s module docstring (SHA-256 `index_checksum` sidecar + `os.replace` two-file swap + refuse-don't-silently-load on mismatch, described in detail in its docstring). D-02's byte-identity/hash assertions should follow the same "hash what's on disk, refuse rather than trust" convention this store already uses, using stdlib `hashlib.sha256` per RESEARCH.md's Don't-Hand-Roll table.

---

### `databasise/tools/check_import_boundary.py` — extending the boundary check

**Analog:** itself (lines 44-48, `_FORBIDDEN_IMPORT_ROOTS`/`_FORBIDDEN_PATH_SEGMENT`)
```python
_FORBIDDEN_IMPORT_ROOTS: tuple[str, ...] = ("lightrag", "v1")
_FORBIDDEN_PATH_SEGMENT = "../v1/"
```
No code change is needed here per RESEARCH.md ("already walks the whole `databasise/` tree by AST") — this check already covers new files under `databasise/parts_core/lightrag/`. The only addition is a new test in `databasise/tests/test_import_boundary.py` exercising the ported files, not a change to the scanner itself.

---

### `databasise/clients/openai_compat.py` — NO ANALOG (new subsystem)

See "No Analog Found" below. Do not force-fit this to `stores/vector.py`'s guard-import style beyond the import-guard idiom (`try: import faiss / except ImportError: ...`) — use the same guarded-import idiom for `try: import openai`, but the HTTP-client body itself has no in-repo precedent. Build from RESEARCH.md's Code Examples / Standard Stack section (the `openai` SDK, `base_url` override for OpenRouter/Ollama).

## Shared Patterns

### Deny-by-default capability scoping (stores AND clients)
**Source:** `databasise/parts_core/__init__.py` (`CapabilityScopedStores`, `UndeclaredEffectError`, `StoreNotWiredError`)
**Apply to:** Every part in `parts_core/lightrag/` that touches `ctx.stores` or `ctx.clients`; the new `CapabilityScopedClients` in `databasise/clients/__init__.py` (mirror, not reuse — see above); `databasise/runner/scheduler.py`'s `_ScopedStoresView`/new `_ScopedClientsView`.

### Refusals over silent fallbacks
**Source:** `databasise/parts_core/__init__.py`'s `StoreNotWiredError` docstring ("refusals over silent fallbacks — this codebase's own stated house style"); `databasise/stores/vector.py`'s checksum-refuse-rather-than-load pattern; `databasise/parts/registry.py`'s `DeclarationOnlyPartError`.
**Apply to:** D-02's import-verification (report `inconclusive`, never pass/fail on a failed precondition); D-15's storage-ownership audit (undeclared store touch is a refusal, not a report line); `ClientNotWiredError` in the new clients package.

### `Part` registration shape
**Source:** `databasise/parts_core/fake_llm_caller.py` / `fake_retriever.py` / `passthrough.py` — every registered `Part` names `name_at_version`, `kind`, `structural_depth`, `effects`, `upstream_ref`, `body`, optional `artifact_scope`.
**Apply to:** All 18 new part registrations in `databasise/parts_core/lightrag/`.

### Evidence ships as committed, re-runnable files
**Source:** `databasise/evidence/falsifier2.py` + `databasise/evidence/FALSIFIER-2-EVIDENCE.md` + `databasise/evidence/wirings/*.json`.
**Apply to:** The parity harness's declared-deviation record, the storage-ownership audit output, and the `03-GATE-AMENDMENT.md` (precedented directly by `02-GATE-01-WAIVER.md`).

### Provenance discipline (`upstream_ref`, never import v1)
**Source:** `databasise/stores/graph.py`/`vector.py`/`kv.py` module docstrings ("ported by deliberate copy — never import — from v1's ..."); `databasise/tools/check_import_boundary.py`.
**Apply to:** Every part body in `parts_core/lightrag/` — set `upstream_ref` to the real v1 file (located by grep per Pitfall 5, not the possibly-stale PARTS.md line number), and never `import` anything from `v1.`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `databasise/clients/openai_compat.py` | service | request-response | No LLM/embedding/rerank HTTP client exists anywhere in `databasise/` today (RESEARCH.md's own "Notable absences" finding) — build from the `openai` Python SDK per RESEARCH.md's Standard Stack/Code Examples, using `stores/vector.py`'s guarded-import idiom (`try: import X / except ImportError`) as the only reusable fragment. |
| `databasise/clients/base.py` (protocol) | model | request-response | No client protocol/ABC exists; `databasise/stores/base.py`'s `StorageNameSpace` lifecycle ABC is the nearest structural cousin (init/finalize/drop lifecycle) but the actual method set (`chat`, `embed`, `rerank`) has no precedent — author fresh, matching the `LLMClient`/`EmbeddingClient`/`RerankClient` protocol shape RESEARCH.md's Recommended Project Structure names. |
| v1 pinned-venv standup (`v1/pyproject.toml`+lock, D-04) | config | file-I/O | No existing venv-standup precedent for `v1/` in this repo (RESEARCH.md: "v1 has no venv today"). Not a `databasise/` file at all — out of pattern-mapping scope, flagged for the planner as real, unbudgeted work. |

## Metadata

**Analog search scope:** `databasise/parts/`, `databasise/parts_core/`, `databasise/runner/`, `databasise/stores/`, `databasise/tools/`, `databasise/evidence/`, `docs/system-model/wirings/`, `.planning/phases/02-falsifier-gate/`
**Files scanned:** `schema.py`, `registry.py`, `parts_core/__init__.py`, `fake_llm_caller.py`, `fake_retriever.py`, `declared_only.py`, `runner/scheduler.py`, `stores/{vector,graph,kv}.py`, `tools/check_import_boundary.py`, `evidence/falsifier2.py`, `evidence/wirings/w1-lightrag-query-side.json`, `docs/system-model/wirings/lightrag-base.json` (listing only, content not re-read — already verified per RESEARCH.md)
**Pattern extraction date:** 2026-08-31
