<!-- refreshed: 2026-09-03 -->
# Architecture

**Analysis Date:** 2026-09-03

## System Overview

Databasise 2.0 is a **modality-agnostic RAG engine** implemented as a machine + fitting contract + versioned components. The system decouples execution orchestration, validation, and storage from modality-specific logic, enabling LightRAG, HippoRAG 2, and future paradigms to coexist and swap without consumer code changes.

Two generations coexist:
- **v1/** — LightRAG monolithic engine: concrete RAG implementation with direct storage, LLM, and chunking integration
- **databasise/** — 2.0 agnostic machine: the D4 One Machine architecture, wiring-based composition, schema-driven validation

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                      Consumer (§18 Public Seam)                           │
│            Sourcerer, CLI, or any client calling run_wiring()            │
└────────────────────────┬─────────────────────────────────────────────────┘
                         │ wiring_doc: dict
                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    Orchestration Layer (databasise/)                      │
├──────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────┐    ┌─────────────┐    ┌──────────────┐    ┌────────────┐ │
│ │  Validator  │───▶│  Identity   │───▶│  Scheduler   │───▶│  Tracer    │ │
│ │             │    │  Resolver   │    │              │    │            │ │
│ │ `validator/ │    │ `identity/` │    │ `runner/`    │    │ `trace.py` │ │
│ │ parse.py`   │    │ canon.py    │    │ scheduler.py │    │            │ │
│ └─────────────┘    └─────────────┘    └──────────────┘    └────────────┘ │
│                                               │                           │
│                                               ▼                           │
│                                    ┌─────────────────┐                    │
│                                    │  TaskGroup per  │                    │
│                                    │  Ready Batch    │                    │
│                                    │  (structured    │                    │
│                                    │  concurrency)   │                    │
│                                    └─────────────────┘                    │
└──────────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         │ reads             │ reads              │ writes
         ▼                    ▼                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                   Parts & Components (databasise/parts_core/, wirings/)   │
├──────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐ ┌────────────────┐ ┌──────────────────────────┐     │
│ │ Reference Parts │ │ LightRAG Parts │ │ Structural Kinds         │     │
│ │ - passthrough   │ │ - assemble     │ │ (dispatch layer, TBD)    │     │
│ │ - kv-writer     │ │ - embedder     │ │ - fanout, join, fixpoint │     │
│ │ `parts_core/`   │ │ - reranker     │ │ - subgraph, opaque       │     │
│ │                 │ │ - generator    │ │                          │     │
│ │                 │ │ `lightrag/`    │ │ `wirings/resolve.py`     │     │
│ └─────────────────┘ └────────────────┘ └──────────────────────────┘     │
│                                                                           │
│ Part Registry (namespace/name@version): resolves components, effects     │
│ `parts/registry.py` — dispatch, capability-scoped store binding          │
└──────────────────────────────────────────────────────────────────────────┘
         │ emits                    │ consumed by
         │ NodeContext              │ each node's body
         ▼                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    Storage Abstraction (databasise/stores/)               │
├──────────────────────────────────────────────────────────────────────────┤
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐              │
│ │    KV      │ │   Vector   │ │   Graph    │ │   Blob     │              │
│ │  Store     │ │   Store    │ │   Store    │ │   Store    │              │
│ │            │ │            │ │            │ │            │              │
│ │ kv.py      │ │ vector.py  │ │ graph.py   │ │ blob.py    │              │
│ │ sqlite:// │ │ (abstract) │ │ (abstract) │ │ (abstract) │              │
│ └────────────┘ └────────────┘ └────────────┘ └────────────┘              │
│                                                                           │
│ Each store: async init/finalize, capability-scoped access (deny-by-def) │
└──────────────────────────────────────────────────────────────────────────┘
         │ connects to
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    Backends (LightRAG v1 layer integration)              │
├──────────────────────────────────────────────────────────────────────────┤
│ ┌────────────────────┐                                                    │
│ │ LightRAG fork      │  - Cozo graph DB (embedded, RocksDB)              │
│ │ (v1/lightrag/)     │  - Faiss vector search                            │
│ │                    │  - Chunking pipeline                              │
│ │ Storage backends:  │  - LLM roles (extraction, summarization)          │
│ │ - Cozo KG          │  - Provider integrations (OpenAI, Claude, etc.)   │
│ │ - Faiss vectors    │  - Async doc ingest & query execution             │
│ │ - NetworkX (dev)   │                                                    │
│ │ - Postgres/etc.    │                                                    │
│ └────────────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| **Entry point** | Parse wiring doc, validate, resolve identity, schedule, trace | `databasise/__init__.py:run_wiring()` |
| **Validator** | Parse wiring, check schema, resolve components, detect cycles, compute depth, enforce containment | `databasise/validator/parse.py`, `cycles.py`, `depth.py`, `blast_radius.py` |
| **Identity resolver** | Canonicalise wiring docs, compute instance hashes, resolve deps with SCC-based depth | `databasise/identity/canon.py`, `instance.py` |
| **Scheduler** | Topological sort, batch ready nodes, dispatch via TaskGroup, enforce per-node concurrency limits | `databasise/runner/scheduler.py` |
| **Tracer** | Record node execution results, build RunRecord with partial/degraded/stop_reason honesty fields | `databasise/runner/trace.py` |
| **Part registry** | Resolve namespace/name@version, dispatch to body, capability-scope stores | `databasise/parts/registry.py` |
| **KV store** | Persistent key-value storage (SQLite in tracer, pluggable backends later) | `databasise/stores/kv.py` |
| **Vector/Graph/Blob stores** | Pluggable storage abstractions (implementations in v1/lightrag/) | `databasise/stores/vector.py`, `graph.py`, `blob.py` |
| **LightRAG parts** | RAG-specific operations (embedder, reranker, generator, entity/relation lookup) | `databasise/parts_core/lightrag/` |
| **LightRAG fork** | Monolithic RAG: concrete storage, LLM bindings, chunking, 4-stage query pipeline | `v1/lightrag/` |

## Pattern Overview

**Overall:** Schema-driven, **wiring-based composition** of versioned components with machine-enforced containment and modality-agnostic execution.

**Key Characteristics:**
- **Contract-first design**: Fitting contract (§18 public seam) defines modality-agnostic interface; v1/v2 separation is clean at the seam
- **Deny-by-default capability scoping**: Every node's store access controlled by its registered `effects[]` declaration (not the wiring's self-declared fields)
- **Structured concurrency**: TopologicalSorter + per-ready-batch TaskGroup + per-node Semaphore (never global locks)
- **Honesty-stamped results**: Every partial run (budget halt, node failure) traced with `partial`, `degraded`, `stop_reason`, `degradation_reason`
- **No executable cycles**: SCC-condensation depth pass handles cycles as data; acyclic nodes dispatch; cyclic wirings return `{"cycle": [...]}` not error
- **Versioned components**: MAJOR = interface change (socket/capability), MINOR/PATCH = internal only (algorithm, prompt, weights)
- **Per-node depth tiers** (opaque, evidence, stage): Taint minimum (min of transitive deps' depth) controls what a node can write (`evidence` blocks shared writes, `opaque` blocks containment escape)

## Layers

**Input (API)**
- Purpose: Accept external requests (HTTP REST, Python function calls, eventually MCP)
- Location: `databasise/__init__.py` (public `run_wiring()` entry), future `databasise/api/`
- Contains: Wiring document parsing, parameter binding, output serialization
- Depends on: Validator, scheduler, tracer
- Used by: Sourcerer, CLI, test harnesses

**Orchestration**
- Purpose: Coordinate validation, identity resolution, execution scheduling, result tracing
- Location: `databasise/validator/`, `databasise/identity/`, `databasise/runner/`
- Contains: Wiring parse & schema check, cycle detection, depth computation, containment blast-radius, node identity, execution scheduling, traced run records
- Depends on: Part registry (component resolution), stores (capability scoping)
- Used by: Entry point, scheduler dispatches to parts

**Part Dispatch**
- Purpose: Resolve components by namespace/name@version, bind to part bodies, scope store access
- Location: `databasise/parts/registry.py`, `schema.py`
- Contains: Registry lookup, part body invocation, NodeContext assembly, capability-scoped store view
- Depends on: Registered parts, stored effects[], store implementations
- Used by: Scheduler (per node per ready batch)

**Parts & Components**
- Purpose: Implement domain-specific logic (RAG, future modalities)
- Location: `databasise/parts_core/` (reference parts), `databasise/parts_core/lightrag/` (RAG parts), `databasise/wirings/` (wiring resolve logic)
- Contains: Part bodies (async callables receiving NodeContext), component registration (namespace/name@version + effects[]), structural kind dispatch (fanout, join, fixpoint, subgraph, opaque — TBD)
- Depends on: NodeContext contract, stores, clients (LLM/embedding)
- Used by: Scheduler via registry dispatch

**Storage Abstraction**
- Purpose: Define pluggable backend interfaces; scope access by declared effects[]
- Location: `databasise/stores/base.py`, `kv.py`, `vector.py`, `graph.py`, `blob.py`
- Contains: Base classes for each storage type, capability-scoped view enforcement (`_ScopedStoresView`), async lifecycle (initialize, finalize, index_done_callback)
- Depends on: Effect enum (17-member vocabulary)
- Used by: Scheduler (assembly for each run), part bodies (scoped subscript access)

**Backend Implementations (v1 integration)**
- Purpose: Concrete storage logic, LLM/embedding clients, document pipeline
- Location: `v1/lightrag/` (monolithic RAG), future separate implementations
- Contains: Cozo graph DB, Faiss vectors, NetworkX (dev), Postgres/MongoDB backends, LLM providers (OpenAI, Claude, Gemini, Ollama, Bedrock), chunking strategies, doc ingestion
- Depends on: Storage abstractions (base classes), external SDKs
- Used by: Store instances in scheduler, part bodies via `ctx.stores[]`

## Data Flow

### Wiring Execution Path

```
1. Entry: run_wiring(wiring_doc, *, store_root, registry, determinism_setting, concurrency_setting)
   Location: databasise/__init__.py:43

2. Validation & parse_wiring(wiring_doc, registry)
   - Check schema (nodes present, components resolve, deps valid, empty-nodes guard)
   - Resolve component parts from registry (namespace/name@version)
   - Detect cycles (SCC-condensation) — returned as data if cyclic
   - Compute effective_depth per node (taint minimum over transitive deps)
   - Enforce blast_radius_violations (containment per depth tier)
   Location: databasise/validator/parse.py:40

3. Identity resolution: canonicalise(wiring_doc) → wiring_instance_hash (SHA256)
   Location: databasise/identity/canon.py, databasise/__init__.py:91

4. Store assembly: gather KV, vector, graph, blob stores for this run
   (Current tracer: hardcoded single SqliteKVStore)
   Location: databasise/__init__.py:64

5. Scheduler (run_wiring): TopologicalSorter → ready batches → TaskGroup per batch
   For each batch:
     - Sort nodes by ID (tie-break reproducibility)
     - Create per-node Semaphore (max_concurrency guard)
     - Dispatch each node: registry.dispatch(node_id, NodeContext)
   Location: databasise/runner/scheduler.py:100+

6. Part dispatch (per node):
   - Resolve Part from registry by node.component
   - Verify wiring.effects ⊆ Part.effects (CR-01)
   - Build _ScopedStoresView (deny-by-default, filtered by Part.effects)
   - Call Part.body(NodeContext(node_id, config, inputs, scoped_stores, scoped_clients))
   Location: databasise/parts/registry.py

7. Execution (node body):
   - Each part body receives NodeContext with scoped store/client access
   - Returns outputs dict
   Location: databasise/parts_core/lightrag/*.py (part implementations)

8. Tracing (per node):
   - Record execution result (success, error, partial_success)
   - Stamp with node_id, output, duration, any error message
   Location: databasise/runner/trace.py:NodeRecord

9. Finalization:
   - Call store.index_done_callback() (flush LLM cache, commit writes)
   - Call store.finalize() (cleanup, close connections)
   - Assemble RunRecord(run_id, wiring_id, wiring_instance_hash, nodes=..., partial=..., stop_reason=...)
   - Return record as dict to caller
   Location: databasise/__init__.py:87–112
```

### Query Path (v1 LightRAG, executed as parts inside databasise)

1. Query request arrives at part body (e.g., `lightrag/keywords.py`)
2. Part receives NodeContext with `ctx.stores["kv"]`, `ctx.stores["vector"]`, `ctx.stores["graph"]`
3. Part calls methods on store: `await store.query(...)` or `await store.get(...)`
4. Store dispatches to concrete backend (v1/lightrag/kg/cozo_impl.py, faiss_impl.py, etc.)
5. Backend executes and returns results
6. Part transforms and returns outputs dict

## Key Abstractions

**Wiring Document**
- Purpose: Declarative specification of node graph + component bindings
- Envelope: `{ nodes: {...}, edges: [...], config: {...} }`
- Per node: `{ component: "namespace/name@version", config: {...}, deps: [...], effects: [...] }`
- Pattern: Parsed once by `validator.parse.parse_wiring()`, never re-parsed; frozen per run

**Part**
- Purpose: Versioned, componentizable implementation unit (async callable + effects declaration)
- Fields: `name: namespace/name`, `version: semver`, `effects: [Effect...]`, `body: async callable`
- Examples: `core/chunker-token@1.0.0`, `lightrag/entity-extractor@2.1.3`, `hipporag/retriever@1.0.0`
- Pattern: Registered at startup in `PartRegistry`, resolved at wire time by namespace/name (version selection TBD in later phase)

**NodeContext**
- Purpose: Calling convention every part body receives
- Fields: `node_id: str`, `config: dict|None`, `inputs: dict[str, Any]` (dep outputs), `stores: dict[str, Any]` (scoped), `clients: dict[str, Any]` (scoped)
- Pattern: Frozen public schema (CONTRACT §13); `ctx._semaphore` is private scheduler extension for voluntary intra-node concurrency bounding

**Effect**
- Purpose: 17-member vocabulary of capabilities (reads_*, writes_*, calls_*, net, fs, self_storage, mutates_store)
- Pattern: Part declares via `effects[]`; wiring node MAY under-declare; scheduler scopes store access to Part.effects (not wiring node's self-declared field) — CR-01 fix
- Examples: `reads_graph`, `writes_vector`, `calls_llm`, `calls_embedding`, `mutates_store`

**Depth (taint rung)**
- Purpose: Structural containment ladder — opaque < evidence < stage
- Taint rule: node's effective depth = min(transitive deps' depth)
- Usage: Control what artifact scopes a node can write (opaque blocks shared/stage, evidence blocks shared)
- Computed by: `validator.depth.effective_depth()` with SCC-condensation; cyclic nodes resolved via strongly connected component

**RunRecord**
- Purpose: Machine-stamped result of one complete (or partial) wiring execution
- Fields: `run_id`, `wiring_id`, `wiring_instance_hash`, `arm_id`, `arm_execution_order`, `executor_version`, `nodes[]`, `partial`, `degraded`, `stop_reason`, `degradation_reason`
- Pattern: Honesty invariant (RunRecord.__post_init__) enforces: if any node is halted/failed, run must be `partial=True` (CONTRACT §9)
- Returned by: `run_wiring()` as dict; consumed by harness/Sourcerer for phase promotion and comparison

## Entry Points

**Public (§18 seam)**
- `databasise.run_wiring(wiring_doc: dict, *, store_root: str|Path, registry: PartRegistry|None, determinism_setting: str, concurrency_setting: str, clients: dict|None) → dict`
- Triggers: Sourcerer, CLI, test harnesses
- Responsibilities: Full orchestration (parse → validate → resolve identity → schedule → execute → trace)
- Returns: RunRecord as dict

**Internals (not public seam)**
- `validator.parse.parse_wiring(wiring_doc, registry) → ParsedWiring`
- `runner.scheduler.run_wiring(parsed, registry, stores, ...) → dict` (return before RunRecord wrapping)
- `parts.registry.PartRegistry.dispatch(node_id, NodeContext) → Any`

## Architectural Constraints

- **Threading**: Async/await throughout. Single Python event loop. Concurrency via `asyncio.gather()` in scheduler, per-node `asyncio.Semaphore` (never global lock). CPU-bound work (e.g., LLM tokenization in v1) via `loop.run_in_executor()`.
- **Global state**: `shared_storage` dict in v1 (`v1/lightrag/kg/shared_storage.py`); databasise-layer has no module-singletons. Part registry is process-level, never per-run (frozen at startup).
- **Circular imports**: Parser plugins, structural-kind dispatch bodies loaded late (plan 01-04+).
- **Workspace/namespace isolation**: Storage backends are per-run keyed by wiring instance. Multiple workspaces can coexist; no cross-workspace queries by design.
- **Store mutability**: All stores mutable during session; consistency via `index_done_callback()` flush semantics. Backends like Neo4j (direct DB) flush per-op; in-process stores (Faiss, Cozo) batch until flush.
- **Version immutability**: Once a Part version is registered, its effects[] and body are frozen. A new implementation requires a new MAJOR version (interface change) or MINOR/PATCH (internal only).

## Anti-Patterns

### Self-Declared Effects Override

**What happens:** A wiring node declares `effects: [writes_kv, calls_embedding]` while the resolved Part only declares `effects: [reads_kv]`. The wiring "upgrades" the Part's capability.

**Why it's wrong:** Violates CR-01 (containment must trust the registry, not the wiring). An untrusted wiring author could over-declare and bypass blast-radius enforcement. Scheduler sources store scoping from `parsed.parts[node_id].effects` (the Part's declaration), not `parsed.nodes[node_id].effects` (wiring's self-declared). The wiring's over-declaration is caught at parse time (CODE_EFFECTS_EXCEED_PART), logged, and ignored at dispatch time.

**Do this instead:** Part author declares all effects the body might need. Wiring author MAY under-declare to intentionally narrow the node's scope (e.g., a reusable part with `effects: [reads_kv, writes_kv]` can be scoped to read-only by declaring `effects: [reads_kv]` on the wiring node). See `databasise/validator/parse.py:13–22`.

### Global Concurrency Caps

**What happens:** A module-level semaphore or concurrency manager governs all nodes in parallel, e.g., `_global_concurrency_limits: dict[str, Semaphore]` shared across arms.

**Why it's wrong:** Violates D-11 (one arm's fan-out must never throttle an unrelated arm, contaminating phase-6 side-by-side comparison). Side-by-side experiments with different concurrency profiles become dependent on each other. v1's `v1/lightrag/kg/shared_storage.py:111` exhibits this anti-pattern.

**Do this instead:** Per-node Semaphore sized from `node.config.max_concurrency` (default 1), created fresh per node per run, exposed to body as `ctx._semaphore` for voluntary use. See `databasise/runner/scheduler.py:7–18`.

### Cyclic Wiring Raises Exception

**What happens:** Topological sort raises `graphlib.CycleError` for a cyclic wiring, terminating the run.

**Why it's wrong:** Cyclic wirings are legal content (CONTRACT §1); cycles are data, not errors. An author may write a cycle intentionally (e.g., iterative refinement, fixed-point computation). Raising discards the cycle information and blocks cycle-aware analysis.

**Do this instead:** SCC-condensation (strongly connected component) depth pass handles cycles; `validator.parse.parse_wiring()` computes `report.cycles` upfront; `scheduler.run_wiring()` reads `parsed.report.cycles` before any node dispatch; cyclic wiring returns `{"cycle": [...]}` as data. See `databasise/validator/cycles.py`, `databasise/validator/parse.py:25–28`, `databasise/runner/scheduler.py:65–74`.

## Error Handling

**Strategy**: Accumulate violations, never raise on first defect (wiring-spec-and-validation.md contract).

**Patterns:**
- **Parse errors** (unknown component, dangling dep, invalid schema): Accumulated in `ParsedWiring.report.violations[]`, returned for inspection. No exception raised unless `report.ok == False` and caller checks explicitly.
- **Validation errors** (effects exceed part, self-declared derivation, empty nodes): Same as parse — accumulated, returned via `report`.
- **Depth/blast-radius errors** (cycle, containment violation, insufficient depth): Reported in `report` if blocking (e.g., `CODE_CONTAINMENT_VIOLATION`); cyclic wirings returned as data under `report.cycles`.
- **Node execution errors** (part body raises, store unavailable, LLM timeout): Traced in `NodeRecord` with error message; run continues if scheduler-level concurrency allows; final RunRecord marked `partial=True` if any node halted or failed.
- **Partial outcomes** (budget halt, placement refusal, internal error): Never discarded. Returned as `partial=True` with `stop_reason` and `degradation_reason` (CONTRACT §9).

## Cross-Cutting Concerns

**Logging**: Implicit via pytest fixtures (`databasise/tests/conftest.py` environment validation) and v1's logging module. No centralized trace collection yet (MCP/observability TBD in later phase).

**Validation**: Multi-stage, none-short-circuit:
1. Schema (pydantic on WiringNode, Effect)
2. Component resolution (registry lookup)
3. Structural (deps, empty-nodes guard)
4. Consistency (effects-exceed-part, self-declared derivation)
5. Depth/containment (effective_depth, blast_radius)

**Authentication**: Not yet modeled. §18 public seam assumes a harness/caller (Sourcerer) handles auth; part bodies receive `clients` dict (D-06) scoped same way stores are (deny-by-default, keyed by Effect).

**Identity & Determinism**: Canonical wiring hash (SHA256 of sorted, type-normed dict) ensures reproducible run_id minting and instance traceability. Determinism & concurrency settings influence scheduler behavior (strict determinism forces sequential dispatch, default allows parallel batches). See `databasise/identity/canon.py`.

---

*Architecture analysis: 2026-09-03*
