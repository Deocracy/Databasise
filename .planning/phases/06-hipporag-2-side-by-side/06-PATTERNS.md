# Phase 6: HippoRAG 2 & Side-by-Side - Pattern Map

**Mapped:** 2026-09-09
**Files analyzed:** 16 (new/modified, from RESEARCH.md's Recommended Project Structure + Wave 0 Gaps + Test Map)
**Analogs found:** 13 / 16

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `databasise/parts_core/hipporag/*.py` (13 node files) | service (Part body, compute node) | mostly CRUD/transform, `ppr.py` is compute-heavy | `databasise/parts_core/lightrag/chunk_vector.py` (retriever shape) + `join_roundrobin.py` (join shape) | exact (per-node-kind) |
| `databasise/parts_core/hipporag/graph_augment_persist.py` | service (Part body, `writes_graph`, bulk write) | file-I/O / batch write | `databasise/stores/graph.py`'s buffered-write convention + `chunk_vector.py`'s Part shape | role-match |
| `databasise/parts_core/hipporag/ppr.py` | service (Part body, compute) | bulk read + native compute | `chunk_vector.py` (Part/NodeContext shape) + `databasise/stores/graph.py` (new `export_to_igraph`) | role-match (novel compute, familiar socket shape) |
| `databasise/parts_core/hipporag/reset_vector_join.py` | service (Part body, `join` structural kind) | transform (fan-in sum) | `databasise/parts_core/lightrag/join_roundrobin.py` | exact (same structural kind, different merge semantics) |
| `databasise/stores/graph.py` (MODIFY: add `export_to_igraph()`) | service (storage adapter method) | file-I/O / bulk-export | itself — existing `get_node_edges`/`upsert_node` methods on `CozoGraphStore` | exact |
| `databasise/stores/vector.py` (MODIFY: add `self_knn()`/`score_all()` to `FaissVectorStore`) | service (storage adapter method) | batch / bulk read | itself — existing `query()` method (lines 217-266) on `FaissVectorStore` | exact |
| `databasise/runner/scheduler.py` (MODIFY or confirm: `join` structural-kind dispatch) | service (scheduler dispatch) | event-driven (node execution) | itself — `_run_node()`/`derive_execution_mode()` dispatch (lines 410-490) | role-match |
| `databasise/wirings/hipporag/base.json` | config (wiring declaration) | — | `databasise/wirings/lightrag/base.json` | exact |
| `databasise/seam/compare.py` (NEW) | service (seam fan-out wrapper) | request-response (fan-out over N arms) | `databasise/seam/engine.py`'s `_execute()` (lines 735-843) + `query()` (lines 455-467) | exact |
| `databasise/seam/rest.py` (MODIFY: add `POST /compare`) | route (REST endpoint) | request-response | itself — `post_query` (lines 179-199) | exact |
| `databasise/mcp/tools.py` (MODIFY: extend `compare` tool if not already present) | route (MCP transport) | request-response | itself — existing tool-registration shape (Phase 5) | exact |
| `databasise/foreign/codebase_memory_mcp_adapter.py` (MODIFY or NEW sibling: snapshot/reset method, F-07) | service (adapter method) | file-I/O (SQLite copy/restore) | itself — existing adapter's mutation-surface handling (`delete_project`'s unlink pattern) | role-match |
| `databasise/eval/bundle.py` (NEW) | model/service (EvalBundle schema + versioning) | CRUD (mint/read bundle versions) | `databasise/evidence/parity_report.py` (load committed inputs, render/version, pure functions) | role-match (closest available; genuinely new domain) |
| `databasise/eval/calibration.py` (NEW) | service (A/A bootstrap calibration) | batch / transform | `databasise/parity/run_comparison.py` (harness shape: load inputs, compute a statistic, emit a machine-readable result + human summary, non-zero exit means something) | role-match (closest available; genuinely new domain) |
| `databasise/tests/parts_core/hipporag/*.py` (NEW dir) | test | integration/unit | `databasise/tests/seam/test_mach11_event.py` + `databasise/tests/stores/test_graph_frozen_bugs.py` | role-match |
| `databasise/tests/eval/*.py` (NEW dir) | test | unit | none — genuinely greenfield | no analog |
| Isolated-venv `hipporag` parity harness (mirrors `databasise/parity/`) | utility (subprocess parity oracle) | request-response (JSON over stdin/stdout, or direct subprocess invocation) | `databasise/parity/v1_arm.py` + `run_comparison.py` | role-match |

## Pattern Assignments

### `databasise/parts_core/hipporag/*.py` — the thirteen node bodies (service, Part)

**Analog:** `databasise/parts_core/lightrag/chunk_vector.py` (read in full this session) for the eleven non-join/non-bulk-compute nodes; `join_roundrobin.py` for `reset-vector-join`; new store methods (below) for `graph-augment-persist`/`ppr`.

**Module docstring convention** (chunk_vector.py lines 1-8): name the position, cite the exact upstream source line/function this port replaces (`upstream_ref`), state which store/namespace it touches and why it never re-does work an upstream input already did (e.g. "never re-embedding"). Every HippoRAG node file must open with this same citation shape, quoting `PARTS.md ## §H`'s row for that node instead of `v1/lightrag/operate.py`.

**Body + registration pattern** (chunk_vector.py lines 22-45):
```python
async def _chunk_vector_body(ctx: NodeContext) -> dict[str, Any]:
    config = ctx.config or {}
    top_k = int(config.get("top_k", _DEFAULT_TOP_K))
    vector = ctx.inputs["embedder-query"]["vector"]
    store = ctx.stores["vector"].select(_CHUNKS_NAMESPACE)
    raw_items = await store.query(vector, top_k=top_k)
    items = sorted(raw_items, key=lambda item: (-item["score"], item["id"]))
    return {"items": items}

LIGHTRAG_RETRIEVER_CHUNK_TOPK_PART = Part(
    name_at_version=_NAME_AT_VERSION,
    kind="retriever",
    structural_depth="stage",
    effects=["reads_vector"],
    upstream_ref="v1/lightrag/operate.py",
    body=_chunk_vector_body,
)
```
Copy exactly: `NodeContext.inputs`/`.config`/`.stores` access shape, `_NAME_AT_VERSION` module constant, one `Part(...)` at module bottom. For every HippoRAG node, `structural_depth="opaque"` (per RESEARCH.md's Taint Rule finding — stays `opaque` until the upstream parity run lands), `upstream_ref="hipporag/src/hipporag/HippoRAG.py"`. RESEARCH.md's own `Code Examples` section already has this exact shape pre-written for `fact-score` (`hipporag/fact-scorer@0.1.0`) — reuse it verbatim as the template for the other retriever-typed nodes.

**`reset-vector-join`'s analog: `join_roundrobin.py`** (read in full this session, lines 1-160). Copy: the `_MERGE_FIELD_BY_NODE_ID`-style fixed-lookup-by-position-id pattern (never a free-text config key for socket identity), the arity-check-and-refuse pattern (`ValueError` on mismatched input count, never a best-effort merge), and `kind="join"` on the `Part`. Do NOT copy the round-robin dedup/interleave body itself — RIG's `reset-vector-join` semantics are a disjoint-support vector *sum* (RESEARCH.md Pattern 2's `dispatch_join_node` sketch), not an interleave-and-dedup. Note for the runner: `join_roundrobin.py` already runs today as a plain `Part` with `kind="join"` and a `body` callable — the scheduler's `_run_node()` dispatches on effects/kind only for `execution_mode` (opaque/fixpoint special-casing per `databasise/validator/execution_mode.py` lines 65-67), and otherwise just calls `part.body(ctx)` uniformly. This means a `join`-kind `Part` with an ordinary `body` **already executes** through the existing dispatch — `schema.py`'s docstring warning about "unconsumed structural-kind dispatch" refers to the `NodeKind` *pydantic union* (used for wiring-JSON validation/typing) not yet being consulted, not to the scheduler being unable to run a join node. Confirm this at Wave 0 before assuming new scheduler code is required; RESEARCH.md's Pitfall 3 may be resolved simply by writing `reset_vector_join.py` in `join_roundrobin.py`'s shape and registering it as a normal Part.

---

### `databasise/stores/graph.py` — new `export_to_igraph()` method (service, bulk-export)

**Analog:** `CozoGraphStore` itself (read in full this session) — `get_node_edges()` (lines 203-225) for the bulk-query shape, module docstring's Cozo-bug mitigations (explicit type assertions, String-not-UUID keys, never `count()` aggregation, dict-not-key-order for JSON columns).

**Bulk-export pattern** (RESEARCH.md's own Pattern 1, already written against this file's real conventions):
```python
async def export_to_igraph(self, *, weight_attr: str = "weight") -> "igraph.Graph":
    import igraph as ig
    node_rows = await self._run("?[id] := *nodes{id}")
    edge_rows = await self._run(f"?[src, tgt, {weight_attr}] := *edges{{src, tgt, {weight_attr}}}")
    vertex_names = [row[0] for row in node_rows]
    idx = {name: i for i, name in enumerate(vertex_names)}
    edges = [(idx[r[0]], idx[r[1]]) for r in edge_rows]
    weights = [r[2] for r in edge_rows]
    g = ig.Graph(n=len(vertex_names), edges=edges, directed=False)
    g.vs["name"] = vertex_names
    g.es["weight"] = weights
    return g
```
Use `self._run(...)` (the existing private dispatcher at line 136, which already wraps the Cozo call in `run_in_executor`) — never call `pycozo` directly from the new method. Read pending-buffer-first exactly as `get_node()`/`has_node()` do (module docstring's "read-your-writes before flush" rule) if the export must reflect an uncommitted in-memory write.

---

### `databasise/stores/vector.py` — new `self_knn()`/`score_all()` on `FaissVectorStore` (service, batch read)

**Analog:** `FaissVectorStore.query()` (lines 217-266, read this session).

**Existing single-query pattern to extend, not loop:**
```python
async def query(self, vector: Any, top_k: int = 10) -> list[dict[str, Any]]:
    ...  # single-vector, top_k nearest, existing Faiss index search
```
`self_knn()` batches this same Faiss index search across every stored vector at once (Faiss's own batched `search()` call over the whole matrix, or `range_search`), returning a dict keyed by source id; `score_all()` is an exhaustive dense dot product against every stored vector, no top-k truncation. Both must be genuinely new methods against the Faiss index object this class already holds — RESEARCH.md's Pitfall 2 names composing the existing `query()` in a loop as the exact anti-pattern to avoid (`O(N²)` pointwise emulation §14.2 forbids).

---

### `databasise/seam/compare.py` (NEW) — API-08 fan-out (service, request-response)

**Analog:** `databasise/seam/engine.py`'s `_execute()` (lines 735-843) and `query()` (lines 455-467), both read this session.

**Fan-out-over-existing-path pattern:**
```python
async def query(self, query_object, selector=None, *, debug=False):
    del debug
    return await self._execute(query_object, selector)
```
`compare()` loops this exact call once per caller-supplied selector, collecting `{selector_value: envelope}` — never a second scheduler, never a second envelope-assembly function (RESEARCH.md Pattern 4's explicit anti-pattern). Degenerate case: exactly one selector returns the bare `ResponseEnvelope` `query()` already returns (RIG §RUN.3's rule) — do not wrap a single result in a one-key dict. Strip any node-position/`provenance` identity from the response by relying on the same envelope-assembly path `_execute()` already uses for redaction (Pitfall 6) — never hand-assemble a new response shape.

---

### `databasise/seam/rest.py` — new `POST /compare` endpoint (route, request-response)

**Analog:** `post_query` (lines 179-199, read this session).

**Exact one-line-adapter shape:**
```python
@app.post("/query")
async def post_query(body: QueryRequest) -> ResponseEnvelope:
    return await engine.query(body.query, body.selector)
```
`POST /compare` follows identically: deserialize a new `CompareRequest(_RequestModel)` DTO (query + list of selectors, `extra="forbid"`), await `engine.compare(...)`, return the result — no logic in `rest.py` itself (D-17's AST-enforced thin-adapter rule, same as Phase 5's pattern).

---

### `databasise/mcp/tools.py` — extend/confirm `compare` tool (route, MCP transport)

**Analog:** `rest.py`'s thin-adapter shape, mirrored (Phase 5's `databasise/mcp/` package already exists per `05-PATTERNS.md`). If a `compare` tool was stubbed in Phase 5's five-tool roster, wire it to the new `engine.compare()`; if not, add it as the sixth tool only if §18.5's growth rule genuinely requires a new tool for a genuinely new operation (comparison, not covered by `query`) — update `test_tool_growth_invariant.py`'s pinned tool count accordingly.

---

### `databasise/foreign/codebase_memory_mcp_adapter.py` — F-07 snapshot/reset (service, file-I/O)

**Analog:** itself — existing mutation-surface handling for `delete_project` (unlinks SQLite + WAL/SHM files, per RESEARCH.md's own citation of `PARTS.md ## §X`).

**Pattern, if the owner chooses "build it" (checkpoint pending, per RESEARCH.md's F-07 section):** snapshot = copy the SQLite file plus `-wal`/`-shm` siblings to a side path before a comparison run; reset = restore those files after. No new machine primitive — a filesystem operation this adapter module already owns the shape for (mirrors its own `delete_project` file-unlink code). RESEARCH.md recommends the cheaper "declare permanent exclusion" alternative (zero code) as the lower-risk default; either way this file is the correct location if code is written.

---

### `databasise/eval/bundle.py`, `databasise/eval/calibration.py` (NEW, greenfield)

**Weakest analog available — flagged, not forced:** `databasise/evidence/parity_report.py` (read this session) for `bundle.py`'s shape (load/version committed inputs, pure functions of on-disk state, "zero deviations is a result, an absent file is not"-style explicit-empty-state rendering) and `databasise/parity/run_comparison.py` (read this session) for `calibration.py`'s shape (harness that loads inputs, computes one statistic, emits a machine-readable result + human-readable summary, non-zero exit means something, pre-flight verification gate before any number is trusted — mirror `run_comparison.py`'s D-02 pre-flight-verifier pattern for calibration's own cache-bypass precondition, RIG §AA.2). Neither file is a strong structural match — RESEARCH.md is explicit that "genuinely no code exists yet" for eval-bundle/calibration; treat these two as the closest available shape references, not exact-fit analogs. Use the `scipy.stats.bootstrap(..., paired=True, method="percentile")` call already spelled out in RESEARCH.md's Code Examples section verbatim for `calibration.py`'s bootstrap step.

---

### Isolated-venv `hipporag` parity harness (Wave 4, Falsifier 7's second application)

**Analog:** `databasise/parity/v1_arm.py` (subprocess-launch shape: build env, run in isolated interpreter, JSON in/out or direct call, timeout-parameterized, non-zero exit = hard refusal — Phase 5's `05-PATTERNS.md` already extracted this pattern in full) + `databasise/parity/run_comparison.py` (the comparison/diff harness shape: `verify_import` pre-flight, `ComparisonRecord`, distinguishable-key asymmetric result shapes). Pin the real upstream `hipporag` package by exact commit SHA in its own isolated venv (RESEARCH.md Open Question 3's recommendation), never imported into `databasise/`'s own environment — same D-14 import-boundary rule Phase 5 already enforced for v1's `lightrag` package.

**Optional-SDK lazy-import / skip-if-absent pattern** (for any test touching this harness):
```python
try:
    import mcp  # noqa: F401
except ImportError:
    pytest.skip("the `mcp` extra is not installed", allow_module_level=True)
```
(`databasise/tests/mcp/test_dual_transport_parity.py` lines 44-48, read this session). Mirror this exactly for the `hipporag` parity harness's own tests — `pytest.importorskip`-style guard at module level, never a hard import failure when the isolated venv/package is absent from the default dev environment.

---

## Shared Patterns

### Part registration shape (name_at_version, kind, structural_depth, effects, upstream_ref, body)
**Source:** `databasise/parts_core/lightrag/chunk_vector.py`, `join_roundrobin.py`
**Apply to:** all thirteen `databasise/parts_core/hipporag/*.py` files.
Every node is a module-level `_NAME_AT_VERSION` string constant, one async `_<name>_body(ctx: NodeContext) -> dict[str, Any]` function, one `Part(...)` instance built from it. `structural_depth="opaque"` for every HippoRAG node until the upstream parity run lands (Taint Rule).

### Thin-adapter transport shape (D-17)
**Source:** `databasise/seam/rest.py` (whole file, Phase 5's own extraction already in `05-PATTERNS.md`)
**Apply to:** the new `POST /compare` route and any new `mcp` tool — deserialize → await identical `Databasise` method → return, no logic duplicated.

### Fan-out over the existing single-arm execution path
**Source:** `databasise/seam/engine.py`'s `_execute()`/`query()`
**Apply to:** `databasise/seam/compare.py` — never a second scheduler or envelope-assembly function.

### Cross-arm storage isolation (already built, not new work)
**Source:** `databasise/namespaces.py`'s `derive_namespace()` (read this session)
**Apply to:** every HippoRAG Part that touches a graph/vector store — pass HippoRAG's own recipe identity through this existing function exactly as LightRAG's parts already do. No new isolation code.

### Bulk-export / batch-capability over pointwise-loop (§14.2)
**Source:** RESEARCH.md's own "Don't Hand-Roll" table; `databasise/stores/graph.py`/`vector.py`'s existing single-item methods as the pattern to extend, never loop
**Apply to:** `export_to_igraph()`, `self_knn()`, `score_all()` — genuinely new batched methods, never the existing `query()`/`get_node_edges()` called N times.

### Subprocess-boundary crossing for opaque parity oracles (D-14)
**Source:** `databasise/parity/v1_arm.py` + `databasise/parity/v1_driver_script.py` (Phase 5's own extraction)
**Apply to:** the isolated-venv `hipporag` package harness — never a direct `import hipporag` inside `databasise/`.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `databasise/tests/eval/*.py` | test | unit | `tests/eval/` is a wholly new directory; no prior eval-bundle or calibration test infrastructure exists anywhere in this codebase (RESEARCH.md's own Wave 0 Gaps list states this explicitly) |
| `databasise/eval/bundle.py` / `calibration.py`'s exact internal shape | service | batch/CRUD | Genuinely greenfield per RESEARCH.md; `parity_report.py`/`run_comparison.py` are the closest available shape references (documented above under Pattern Assignments) but neither is a structural match for eval-bundle versioning or bootstrap calibration specifically |

## Metadata

**Analog search scope:** `databasise/parts_core/`, `databasise/stores/`, `databasise/seam/`, `databasise/runner/`, `databasise/parts/`, `databasise/parity/`, `databasise/evidence/`, `databasise/foreign/`, `databasise/mcp/`, `databasise/tests/mcp/`, `databasise/namespaces.py`
**Files scanned:** `chunk_vector.py`, `join_roundrobin.py`, `schema.py`, `stores/graph.py` (full), `stores/vector.py` (method signatures), `runner/scheduler.py` (dispatch section), `seam/engine.py` (`query`/`_execute`/`ingest`/`delete_document`), `seam/rest.py` (route list), `seam/query.py`, `namespaces.py` (docstring + `derive_namespace` signature), `parity/run_comparison.py`, `evidence/parity_report.py`, `foreign/codebase_memory_mcp_adapter.py` (import head), `tests/mcp/test_dual_transport_parity.py`, `pyproject.toml` (extras), `.planning/phases/05-opaque-side-admission/05-PATTERNS.md` (precedent shape)
**Pattern extraction date:** 2026-09-09
