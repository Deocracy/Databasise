---
last_mapped_commit: 8044f9a
---

<!-- refreshed: 2026-09-08 -->
# Architecture

**Analysis Date:** 2026-09-08  

## System Overview

Databasise 2.0 is a **modality-agnostic machine** that executes wiring graphs (directed acyclic or cyclic) over embedded stores. The machine enforces a frozen contract (§18) between internal identity/execution traces and what consumers see. Two major codebase halves coexist: the v2.0 **agnostic rebuild** (`databasise/`) and the v1 **LightRAG legacy fork** (`v1/`), which serves as both a reference implementation and an opaque ingest core pending full decomposition in Phase 5.

```text
┌──────────────────────────────────────────────────────────────┐
│                    Consumer Boundary (§18)                   │
│  REST (FastAPI) | In-Process Async | Future: MCP Transport   │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│           Seam: databasise.seam.Databasise                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ query(QueryObject, Selector)                            │ │
│  │ → ResponseEnvelope (redacted, no internal IDs)          │ │
│  │ - Selector resolution (alias, capability, harness)      │ │
│  │ - Query injection & token allowance injection           │ │
│  │ - Evidence minting & trace reference (opaque token)     │ │
│  │ - MACH-11 seam event correlation                        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                    Machine-Internal (D-02)                   │
│                                                               │
│       Scheduler: databasise.runner.scheduler                 │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ run_wiring(ParsedWiring) → RunRecord (un-redacted)      │ │
│  │ - Validator: SCC-based depth, execution_mode            │ │
│  │ - Guard checks (self-declared refusals)                 │ │
│  │ - Part resolution from registry                         │ │
│  │ - Per-node semaphore & budget metering                  │ │
│  │ - Concurrent execution via asyncio.gather()            │ │
│  │ - Store-mutation event recording (MACH-11)             │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                    Storage Layer (Embedded Only)              │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Graph Store  │  │ Vector Store │  │ KV + Lexical +   │   │
│  │ Cozo + RDB   │  │ Faiss (CPU)  │  │ Blob Stores      │   │
│  │ (Datalog)    │  │ + MultiIdx   │  │ (SQLite + FTS5)  │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
│                                                               │
└──────────────────────────────────────────────────────────────┘

v1 Reference (Opaque Ingest Core)
┌──────────────────────────────────────────────────────────────┐
│ LightRAG (v1/lightrag/) — 4-stage query pipeline             │
│ Chunkers, Parsers, LLM bindings, Admin operations            │
│ → Imported via parts_core.lightrag (Phase 5 admits it)       │
└──────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File(s) |
|-----------|----------------|---------|
| **Seam Engine** | Consumer-facing async API; redaction & envelope assembly | `databasise/seam/engine.py` |
| **REST Transport** | Optional FastAPI endpoints; thin adapter to Seam | `databasise/seam/rest.py` |
| **Selector Resolution** | Map (alias, capability, harness) to wiring arm | `databasise/seam/selectors.py` |
| **Query Object** | Immutable request envelope (modality-agnostic) | `databasise/seam/query.py` |
| **ResponseEnvelope** | Redacted response; evidence refs, token breakdown, seam events | `databasise/seam/envelope.py` |
| **Evidence Minting** | Extract evidence from RunRecord; mint opaque refs | `databasise/seam/evidence.py` |
| **Trace Store** | Persist RunRecord per opaque trace_token | `databasise/seam/trace_store.py` |
| **Token Breakdown** | Assemble token_accounting across all nodes | `databasise/seam/tokens.py` |
| **Refusals** | Sealed hierarchy of SeamRefusalError subclasses | `databasise/seam/refusals.py` |
| **Scheduler** | Parse, validate, resolve, execute wiring graph | `databasise/runner/scheduler.py` |
| **Validator** | Wire-time checks (depth, execution_mode, self-declared guard refusals) | `databasise/validator/parse.py` |
| **Part Registry** | Name@version → Part(body, effects[], depth, artifact_scope) | `databasise/parts/registry.py` |
| **Part Schema** | NodeKind (tagged sum), Effect vocabulary, WiringNode, Part | `databasise/parts/schema.py` |
| **Graph Store** | Cozo (Datalog + RocksDB) adapter; entity/relation queries | `databasise/stores/graph.py` |
| **Vector Store** | Faiss (exact IndexFlatIP cosine) + multi-namespace indexing | `databasise/stores/vector.py` |
| **KV Store** | SQLite per-namespace key-value (doc status, LLM cache, doc-chunk mappings) | `databasise/stores/kv.py` |
| **Lexical Store** | SQLite FTS5 full-text search per-namespace | `databasise/stores/lexical.py` |
| **Blob Store** | Content-addressed file storage (artifacts, bundles) | `databasise/stores/blob.py` |
| **Identity System** | Component instance hashing (config_hash), workspace/namespace derivation | `databasise/identity/canon.py`, `instance.py` |
| **Wiring Resolver** | Load base.json + arm-*.json-patch.json; resolve selector to arm | `databasise/wirings/resolve.py` |
| **Ledger** | Append-only run audit log (Phase 1 complete, Phase 7 uses for promotions) | `databasise/ledger/ledger.py` |
| **Parity Harness** | End-to-end arm comparison: v2 vs v1; corpus fixture import | `databasise/parity/run_arm.py`, `run_comparison.py` |
| **Falsifier 2 Evidence** | Depth/execution_mode computed proof; three named wirings | `databasise/evidence/falsifier2.py` |
| **v1 Parts** | LightRAG query, embedding, reranking, etc., as fitted parts | `databasise/parts_core/lightrag/` |

## Pattern Overview

**Overall:** Wiring-based component composition with deny-by-default effects, late-binding dispatch, and redacted consumer envelope.

**Key Characteristics:**
- **Modality agnostic:** LightRAG and HippoRAG 2 both wire over the same machine primitives (stores, clients); swapping the wiring changes no field a consumer sees (§18 holds).
- **Embedded, single-process:** No external databases—Cozo (graph), Faiss (vector), SQLite (KV/lexical/blob) all in-process, file-backed in `store_root`.
- **Deny-by-default effects:** A part declares exactly what it reads/writes (17-member vocabulary); the runner refuses undeclared store access (Falsifier 2, MACH-08).
- **Identity-first composition:** Every Part, every wiring instance, every component gets a stable `config_hash` and `instance_hash`; swapping a param byte yields a different partition with separate state.
- **Structured concurrency:** `asyncio.gather()` per node; per-node budget semaphore; scheduler halts on exhaustion, runner records as `partial=True`.
- **Redacted seam:** `databasise.seam.Databasise` shields consumers from wiring_id, wiring_instance_hash, node_id, arm_id unless `debug=True`; ResponseEnvelope carries only evidence refs and token counts.
- **Async-first, streaming-capable:** `query()` returns assembled envelope; `query_stream()` yields events incrementally; both use identical `_execute()` internals.
- **Parity-first development:** Phase 3+ harness runs v2 arms against real v1 index in parallel, measuring variance, not asserting equivalence.

## Layers

**Seam Layer (D-01, §18):**
- **Purpose:** Consumer-facing async interface; redaction & envelope assembly; selector resolution; evidence & trace minting.
- **Location:** `databasise/seam/`
- **Contains:** `Databasise` engine, REST transport, QueryObject/ResponseEnvelope (frozen models per §18.1/§18.2), SeamRefusalError hierarchy, selector resolution (alias/capability/harness), evidence minting, opaque trace reference generation, token breakdown assembly, MACH-11 seam event correlation.
- **Depends on:** Scheduler, parts registry, wiring resolver, evidence extraction, token accounting.
- **Used by:** REST endpoints, in-process async callers, future MCP transport.
- **Redaction guarantee:** No wiring_id, wiring_instance_hash, node_id, or arm_id leave this layer (except via `debug=True` in trace resolution; CR-02 allow-list enforces this).

**Scheduler & Validation Layer (D-02, D-05):**
- **Purpose:** Parse wiring, validate (depth/execution_mode/guard refusals), resolve part instances, metered execution, trace assembly.
- **Location:** `databasise/runner/scheduler.py`, `databasise/validator/parse.py`.
- **Contains:** Wiring parsing (CONTRACT §1 structural validation), Falsifier 2 (SCC depth, execution_mode derivation), guard checks (self-declared refusals), part resolution from registry, per-node budget semaphore, node execution via asyncio.gather(), RunRecord (un-redacted) assembly.
- **Depends on:** Part registry, stores dict, clients dict, validators.
- **Used by:** Seam engine, parity harness.
- **Guarantee:** All nodes that execute are traced (CONTRACT §9); budget-halted runs marked `partial=True`; no silent fallbacks (MACH-01).

**Storage Abstraction Layer (D-03):**
- **Purpose:** Define pluggable interfaces for graph, vector, KV, lexical, blob stores.
- **Location:** `databasise/stores/base.py`, concrete implementations in `databasise/stores/`.
- **Contains:** Base classes (BaseGraphStorage, BaseVectorStorage, BaseKVStore), namespace derivation, workspace isolation.
- **Depends on:** None (pure interfaces).
- **Used by:** Scheduler (scoped store view), seam layer (evidence extraction), parity harness.
- **Storage lifecycle:** `initialize()` on first access per namespace, `index_done_callback()` on run completion (flush + cache invalidation), `finalize()` on shutdown.

**Storage Implementations (D-03, Phase 1):**
- **Graph:** `databasise/stores/graph.py` — Cozo (Datalog + RocksDB) adapter; entity/relation queries, SCC detection, transitive closure.
- **Vector:** `databasise/stores/vector.py` — Faiss (IndexFlatIP cosine, CPU-only) + multi-namespace indexing; upsert, query, delete by ID.
- **KV:** `databasise/stores/kv.py` — SQLite per-namespace; doc status, LLM cache, chunk mappings.
- **Lexical:** `databasise/stores/lexical.py` — SQLite FTS5 full-text search per-namespace.
- **Blob:** `databasise/stores/blob.py` — Content-addressed file storage; artifacts, eval bundles, corpus snapshots.

**Parts & Components Layer (D-04):**
- **Purpose:** Versioned, named component registry and execution.
- **Location:** `databasise/parts/schema.py` (Part, WiringNode, Effect, NodeKind), `databasise/parts/registry.py` (PartRegistry), `databasise/parts_core/` (built-in reference parts).
- **Contains:** Part(name@version, body, effects[], depth, artifact_scope), NodeKind tagged sum (fanout/join/fixpoint/subgraph/opaque), 17-member Effect vocabulary (reads_kv, writes_artifact, calls_llm, net, fs, etc.), PartRegistry with default entries and v1 LightRAG parts.
- **Depends on:** None (pure schema until body execution).
- **Used by:** Scheduler (part resolution), seam layer (MACH-11 event correlation with declared effects).
- **Guarantee:** A part's declared effects MUST NOT be bypassed (Falsifier 2 guard; MACH-08).

**v1 Integration (Phase 5 pending):**
- **Purpose:** Admit v1's opaque ingest core and codebase-memory-mcp under sealed contracts.
- **Location:** `databasise/parts_core/lightrag/`, `v1/lightrag/`.
- **Contains:** v1 LightRAG as fitted Part (chunking, LLM extraction, entity/relation synthesis), embedding/reranking clients, admin operations (delete, status).
- **Status:** Phase 1-4 complete; parts_core.lightrag provides stub/fixture parts; Phase 5 imports live v1 components.

**Wiring & Resolution Layer:**
- **Purpose:** Load base wiring JSON + arm-specific JSON patches; resolve selector to executable arm.
- **Location:** `databasise/wirings/resolve.py`, `databasise/wirings/lightrag/` (arm-naive.json-patch.json, arm-local.json-patch.json, arm-global.json-patch.json, arm-hybrid.json-patch.json, arm-bypass.json-patch.json).
- **Contains:** Base wiring structure (graph, parts, storage config), arm selectors (naive/local/global/hybrid/bypass for LightRAG query), selector dispatch (alias, capability, harness).
- **Depends on:** Wiring JSON files, selector models, part registry.
- **Used by:** Seam engine (selector resolution before scheduler).

**Identity System (D-04, D-07):**
- **Purpose:** Stable component identity (config_hash, instance_hash), workspace/namespace derivation, canonical representation.
- **Location:** `databasise/identity/canon.py` (canonicalise), `identity/instance.py`, `identity/env.py`.
- **Contains:** Deterministic JSON canonicalization (no re-ordering, no normalisation), SHA256-based hashing, workspace/namespace keys from storage config identity.
- **Guarantee:** Byte-identical wiring → identical wiring_instance_hash; changed param → different hash → separate storage partition.

**Evidence & Tracing (D-10, D-14):**
- **Purpose:** Extract evidence chunks from retrieval nodes, mint opaque trace references, persist run traces.
- **Location:** `databasise/seam/evidence.py` (EvidenceRef, mint_evidence_refs, resolve_evidence_ref), `databasise/seam/trace_store.py` (TraceStore), `databasise/runner/trace.py` (RunRecord, NodeTrace, TokenAccounting).
- **Contains:** Evidence namespace (CHUNKS_NAMESPACE), opaque trace token generation, RunRecord serialization (schema-compliant per rig-trace.schema.json), node-level trace fields (depth, effective_depth, wall_clock_ms, cache_hit, guards_fired, budget_state, realised_budget_share, tokens).
- **Depends on:** Scheduler output, storage layer.
- **Guarantee:** Every node that runs is traced; partial/degraded flags and reason fields are a required-together set (honesty invariant, RIG §TR.3).

**Parity Harness (Phase 3+):**
- **Purpose:** Real-time arm comparison against v1 LightRAG; variance measurement, not assertion.
- **Location:** `databasise/parity/run_arm.py` (end-to-end v2 arm run), `databasise/parity/v1_arm.py` (legacy v1 query path), `databasise/parity/run_comparison.py` (paired runs), `databasise/parity/corpus.py` (shared corpus fixture), `databasise/parity/import_index.py` (v1 index import).
- **Contains:** Arm driver (selector → wiring resolution → scheduler execution), client construction from `.env.parity`, store assembly (graph/vector/KV at parity namespace), paired RunRecord comparison, corpus snapshot import.
- **Depends on:** Scheduler, all stores, v1 modules (for parallel runs).
- **Used by:** Phase 3+ tests, acceptance suite.

## Data Flow

### Primary Query Path (Seam → Scheduler → Stores → Response)

1. **Query Entry** (`databasise.seam.engine.query()`)
   - Consumer calls `Databasise.query(QueryObject, Selector=None)`
   - Selector defaults to "naive" (hardcoded in this phase)

2. **Selector Resolution** (`databasise.seam.selectors.resolve_selector()`)
   - Map selector to wiring arm (alias, capability, harness)
   - Load base.json + arm-*.json-patch.json
   - Return ParsedWiring with named arm

3. **Query Injection** (`databasise.seam.engine._inject_query()`)
   - Insert QueryObject into "keywords"/"generate" nodes (hardcoded node_ids per arm)
   - Inject token_allowance into config (default: 1M per node, MACH-05)

4. **Wiring Parsing & Validation** (`databasise.validator.parse.parse_wiring()`)
   - CONTRACT §1 structural validation
   - Falsifier 2: SCC-based depth computation, execution_mode derivation
   - Guard refusals: self-declared values rejected (MACH-01)
   - Effect checking: deny-by-default, unknown effects refused

5. **Scheduler Execution** (`databasise.runner.scheduler.run_wiring()`)
   - Part resolution from registry (body lookup)
   - Per-node semaphore allocation
   - Concurrent execution: `asyncio.gather(node_factory(...) for node in dag_order)`
   - Budget tracking per node: `realised_budget_share = spent / allowed`
   - Store mutation recording: `(node_id, "store", store_key)` events
   - Guard firing: log any guards that fired (empty in this phase)

6. **Node Execution** (Part.body)
   - Each node receives `NodeContext(node_id, config, inputs, stores, clients)`
   - Reads from prior nodes via `inputs`
   - Mutates stores (if declared in effects)
   - Returns output dict

7. **RunRecord Assembly** (`databasise.runner.trace.RunRecord`)
   - Stamp un-redacted: `run_id`, `wiring_id`, `wiring_instance_hash`, `arm_id`, executor version, settings
   - Stamp nodes: list of NodeTrace (one per node that ran)
   - Honesty check: verify partial/degraded/stop_reason/degradation_reason are consistent

8. **Evidence Minting** (`databasise.seam.evidence.mint_evidence_refs()`)
   - Extract output from _EVIDENCE_RETRIEVAL_NODE_ID ("chunk-vector")
   - Mint opaque EvidenceRef per chunk (no consumer receives the actual chunk content at this phase)
   - Preserve node's output order verbatim

9. **Token Breakdown Assembly** (`databasise.seam.tokens.assemble_token_breakdown()`)
   - Aggregate per-node TokenAccounting across all nodes
   - Sum prompt_tokens, completion_tokens, cached_read_tokens, call_count
   - Raise UnbudgetableParticipantError if any node declares unbudgetable sentinel

10. **MACH-11 Seam Event Correlation** (`databasise.seam.engine._mach11_events()`)
    - For each node that declares `mutates_store`: compare touched keys vs. accounted keys from declared deps' effects
    - Touched key not in `_accounted_store_keys` → one SeamEvent per key
    - Part name@version (never node_id) in event; outcome from ResponseEnvelope vocabulary

11. **Trace Persistence** (`databasise.seam.trace_store.TraceStore.persist()`)
    - Store RunRecord in TraceStore
    - Mint opaque `trace_token` (SHA256(run_id + random nonce))

12. **Response Envelope Assembly** (`databasise.seam.envelope.ResponseEnvelope`)
    - Redaction (CR-02): copy only allow-listed RunRecord fields (partial, degraded, stop_reason, degradation_reason, etc.; exclude run_id, wiring_id, arm_id unless debug=True)
    - Evidence refs from step 8
    - Token breakdown from step 9
    - Seam events from step 10
    - Trace token from step 11

13. **Consumer Response** (`databasise.seam.engine.query()` returns, or REST endpoint serializes)
    - ResponseEnvelope(evidence: [EvidenceRef, ...], token_accounting: TokenBreakdownEntry, seam_events: [SeamEvent, ...], trace_token: str, ...)
    - Consumer receives no internal identities (wiring_id, node_id, arm_id)
    - Consumer can later call `resolve_trace(trace_token, debug=True)` to get node-by-node breakdown (if debug=True, same redaction rules apply)

### Streaming Path (§18.4, D-16)

- `query_stream()` is an async generator over identical `_execute()` call (shared impl, CR-01 gap closure)
- Yields incremental events: one per evidence chunk, then final event with token_accounting + seam_events
- REST endpoint `/query/stream` reuses same `stream_envelope_events()` function (no divergent impl)

### Wiring Parse/Validation Entry Points

**Seam Entry (D-02 shield):**
- `Databasise.query()` → calls `_execute()` → selector resolution → `parse_wiring()` + `scheduler.run_wiring()` inside try-catch for `SeamRefusalError`
- Any refusal (unknown effect, self-declared depth, unbudgetable) caught and converted to ResponseEnvelope with refusal in metadata

**Parity Harness Entry (machine-internal, unredacted):**
- `run_arm(arm_name, ...)` → directly calls `scheduler.run_wiring()` with RunRecord returned un-redacted
- Used for parity measurement; does not hit seam redaction

## Key Abstractions

**Wiring:** A DAG or cyclic directed graph of nodes, each node a Part instance with config and deps. Wiring is author-supplied untrusted JSON; parsed via CONTRACT §1 schema; validated (depth/execution_mode) via Falsifier 2.

**Part:** Versioned, named component (name@version) carrying: body (async callable or None for declaration-only), structural_depth (opaque/evidence/stage), effects[] (subset of 17-member vocabulary), artifact_scope (shared/quarantined/self_storage or None), upstream_ref (lineage pointer, §7).

**Selector:** Consumer-supplied choice (alias, capability, harness) that resolves to one wiring arm. Hardcoded in Phase 4: "naive" → arm-naive.json-patch.json (LightRAG query-only, no hybrid). Future phases add more selectors per capability.

**Arm:** One JSON-Patch over base.json, selecting a subset of nodes and configuring them for a specific query mode (naive/local/global/hybrid for LightRAG). Arm becomes the executable wiring after selector resolution and query injection.

**NodeKind (Tagged Sum):** Five structural kinds (fanout/join/fixpoint/subgraph/opaque) per CONTRACT §2. Structural dispatch (e.g., fanout → parallel execution of outputs) is a later plan; tracer uses primitive kinds (passthrough, kv-writer).

**Effect:** 17-member vocabulary (reads_kv, writes_vector, calls_llm, net, fs, mutates_store, etc.). Deny-by-default: a part MUST declare every store/net/fs access; undeclared access is caught by Falsifier 2 (MACH-08) and refused.

**Evidence:** Retrieved chunks from a retrieval node (e.g., chunk-vector in LightRAG naive arm). Minted as opaque EvidenceRef (SHA256 of content + random nonce); consumer never receives raw content, only reference + position. Phase 5+ will unfold evidence scopes (shared/quarantined).

**RunRecord:** Immutable trace of one wiring execution. Un-redacted internal form carries wiring_id, wiring_instance_hash, arm_id, node_ids. Redacted consumer form (ResponseEnvelope) omits all identities (CR-02 allow-list). Honesty invariant ensures partial/degraded flags and reason fields are consistent (RIG §TR.3).

## Entry Points

**REST API (Optional, D-15/D-16/D-17):**
- Module: `databasise.seam.rest`
- Endpoints:
  - `POST /query` — request body: `{"query": QueryObject, "selector": Selector or null}` → response: ResponseEnvelope (JSON)
  - `GET /query/stream` — same request params → EventSourceResponse (SSE) with incremental events
  - `POST /resolve_trace` — request body: `{"trace_reference": str, "debug": bool}` → response: RunRecord (redacted or full per debug flag)
  - Exception handler: maps SeamRefusalError subclasses to 422 + JSON detail
- Transport assumption: operator provides TLS termination, auth, rate limiting at reverse proxy boundary (T-04-25/T-04-26 threat register disposition: transfer)

**In-Process Async:**
- Class: `databasise.seam.Databasise`
- Methods:
  - `async query(QueryObject, Selector=None) → ResponseEnvelope`
  - `async query_stream(QueryObject, Selector=None) → AsyncIterator[SeamEvent]`
  - `async resolve_trace(trace_token: str, debug: bool = False) → dict`
- Initialization: `async with Databasise(store_root=Path(...), registry=PartRegistry()) as engine: ...`

**Parity Harness (Phase 3+, machine-internal):**
- Module: `databasise.parity.run_arm`
- Function: `async run_arm(arm_name, query_obj, *, store_root=None, workspace=None, clients=None) → RunRecord`
- Returns un-redacted RunRecord for comparison against v1 arm output
- Used by acceptance suite, parity measurement, variance analysis

**CLI Entry (Future Phase 5+):**
- Not yet implemented; POST-Phase-4 work

## Architectural Constraints

- **Threading:** Single Python event loop (async/await). Node concurrency via `asyncio.gather()` per wave. CPU-bound work (tokenization, canonicalization) runs in `loop.run_in_executor()`. No true parallelism; external I/O (LLM calls, store ops) awaitable.

- **Global state:** `shared_storage` dict in `databasise/namespaces.py` holds per-namespace metadata (chunking state, keyed locks, doc status cache). Initialized on first access per namespace; NOT thread-safe (async-safe via event loop single-threading). No cross-namespace state sharing.

- **Storage mutability:** Graph/vector/KV stores are mutable during run. Consistency guaranteed by:
  - Per-namespace storage isolation (separate RocksDB files, SQLite WAL)
  - `index_done_callback()` after every run (flush writes, invalidate LLM cache keys)
  - `finalize()` on shutdown (close connections, commit final state)

- **Circular imports:** Parser plugins (Part.body closures referencing v1) loaded late in `parts_core.__init__`. No module-level circular deps; all cyclic wiring detection (SCC) happens at validation time (Falsifier 2).

- **Workspace isolation:** Multiple workspaces can coexist in one process (separate directory trees under `store_root`). Each workspace has its own graph, vector, KV stores. No cross-workspace queries.

- **Identity stability:** `wiring_instance_hash` (SHA256 of canonical wiring_doc bytes) is stable—same wiring JSON always hashes to same value (same run_id, config_hash, partition key). Swapping one param byte → different instance_hash → different store partition with no collision risk.

- **Redaction boundary:** §18 seam guarantees: no consumer receives wiring_id, wiring_instance_hash, node_id, or arm_id in normal (debug=False) mode. All internal-identity fields stay in machine, never cross seam. CR-02 allow-list (not deny-list) enforces this at RunRecord serialization for trace resolution.

- **Token budget enforcement:** Per-node token_allowance (default 1M, overridable per node in config). Scheduler halts node execution when budget exhausted; run marked `partial=True`, `stop_reason="budget_exhausted"`. No token "borrowing" or "repayment" (MACH-05 budget metering is strict).

## Anti-Patterns

### Hardcoded Node IDs in Selector Resolution

**What happens:** Seam layer assumes "keywords", "embedder-query", "generate", "chunk-vector" node IDs are stable across all arms and LightRAG versions.

**Why it's wrong:** A future arm name change or structure reorg breaks evidence minting and query injection silently.

**Do this instead:** Phase 5+ should parameterize node IDs in arm metadata (e.g., `"_metadata": { "retrieval_node_id": "chunk-vector", "query_node_ids": {...} }`), and seam layer resolves from that, refusing arms with missing metadata rather than assuming a layout.

### Silent Fallback to Naive Arm

**What happens:** Selector resolves to "naive" if not specified or unknown selector is supplied.

**Why it's wrong:** Caller's intent ambiguous; could be a typo (capability='local' mistyped as 'calocal' silently falls back to naive, losing the caller's intent).

**Do this instead:** Refuse unknown selectors explicitly (SeamRefusalError subclass). Only fallback is documented in SELECTION.md and applies to the gate decision, not every query.

### Mutable Store State Without Flushing

**What happens:** A run completes, store writes are buffered but `index_done_callback()` is never called—subsequent runs see stale state.

**Why it's wrong:** Data corruption risk; two runs appear to execute in parallel even though they should be sequential.

**Do this instead:** Seam engine guarantees `index_done_callback()` is always called after `scheduler.run_wiring()` completes (success or error). Parity harness does the same. Never omit this step.

### Redacting RunRecord at Wrong Boundary

**What happens:** Serializing RunRecord to JSON at scheduler layer instead of seam layer; consumer sees wiring_id in the raw dict.

**Why it's wrong:** Contract §18.2 violated; internal identities leak to untrusted consumer.

**Do this instead:** Keep RunRecord as un-redacted dataclass inside machine; only serialize via ResponseEnvelope (redaction applied by seam layer at response boundary). Parity harness and internal tools receive un-redacted RunRecord as Python dict.

## Error Handling

**Strategy:** Fail fast at validation; propagate refusals as data (ResponseEnvelope with refusal metadata), never as silent fallbacks.

**Patterns:**
- **Parse errors** (malformed wiring JSON, unknown component): Raise `ValueError` or `SeamRefusalError` subclass; seam layer catches and returns 422 with refusal detail.
- **Guard refusals** (self-declared depth, undeclared effect, unknown selector): Checked at wire time (before execution); return SeamRefusalError subclass; seam REST endpoint maps to 422.
- **Execution errors** (part.body raises, store I/O fails): Caught by scheduler; node marked with `cross_process_failure_cause` (async exception message); run marked `partial=True`, `stop_reason="execution_halted"`, `degradation_reason` populated.
- **Budget exhaustion** (token spend exceeds allowance): Scheduler detects; halts node, subsequent nodes skipped; run marked `partial=True`, `stop_reason="budget_exhausted"`.
- **Trace persistence failures**: Caught before envelope assembly; SeamRefusalError subclass raised; consumer sees 422 + error detail (no trace_token issued).

## Cross-Cutting Concerns

**Logging:** Implicit via part.body implementations (standard `logging` module). Seam layer logs refusals at INFO level. Scheduler logs node execution summary at DEBUG level (wall_clock_ms per node).

**Metrics:** RunRecord carries per-node and aggregate metrics (token counts, wall_clock_ms, cache_hit, budget_state). Seam emits SeamEvent per MACH-11 violation; consumer inspects token_accounting and seam_events for observability.

**Validation:** Falsifier 2 (depth/execution_mode computation) and guard checks (effect vocabulary, self-declared value refusals) are the main validation gateways. Contract §1 (wiring schema) enforced by pydantic WiringNode validation.

**Caching:** LLM responses cached in KV store (keyed by content identity per utils.get_llm_cache_identity()); cache invalidated per-namespace on `index_done_callback()`. Budget-halted runs do NOT invalidate (cache left in place for retry).

**State Management:** Per-namespace shared_storage dict holds chunking metadata, keyed locks (per-entity/doc), doc status tracking. Initialized on first wiring execution in a namespace; persists across multiple runs in same workspace unless explicitly cleared.

---

*Architecture analysis: 2026-09-08*
