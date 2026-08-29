# Project Research Summary

**Project:** Databasise 2.0 — Embeddable Modality-Agnostic RAG Engine  
**Domain:** Decomposition/parity rebuild of a retrieval engine with interchangeable modalities (LightRAG fork → primitives; HippoRAG 2 ported; both compared on frozen comparison rig)  
**Researched:** 2026-08-29  
**Confidence:** MEDIUM (stack/architecture HIGH, features MEDIUM, pitfalls MEDIUM — no vendor lock-in assumptions, but project-specific decomposition strategy requires validation)

## Executive Summary

Databasise 2.0 is a modality-agnostic RAG machine: a decomposed version of LightRAG that separates the fitting (wiring contract, runner, storage layer) from swappable modalities (LightRAG, HippoRAG 2, future unknowns). The research recommends a Python 3.12 + embedded-stores stack (Cozo 0.7.6 for graph, LanceDB for vectors, SQLite for KV), a lightweight TopologicalSorter+TaskGroup-driven runner, and a contract-driven validation pipeline. The core differentiator is not a new algorithm but a *capability to run N modalities side-by-side on the same corpus and compare them* — every competitor researched (R2R, GraphRAG, Cognee) is locked to one modality, and none expose A/B comparison as a first-class API feature.

The critical risk is decomposition stalling at the storage layer while logic decomposition looks complete: 17 query-side node positions can be extracted on paper while every node still reaches into v1's singleton `shared_storage.py`. Mitigation is to track storage-ownership and lock ordering separately from call-graph decomposition, with mandatory per-node verification. Secondary risks cluster around parity validation (single-run parity is noise, not proof; A/A calibration needs an explicit Minimum Detectable Effect calculation before comparing modalities; embedding drift invalidates parity silently) and contract hygiene (the frozen Cozo 0.7.6 has four known correctness bugs; opaque-node scope is the first place contract-as-intention erodes into contract-as-escape-hatch under schedule pressure).

## Key Findings

### Recommended Stack

The stack prioritizes embedding and no external services. **Python 3.12** is the runtime (already v1 baseline, no migration needed). **Cozo 0.7.6 [embedded]** is the graph store primitive (architecture-frozen, dormant since 2023-12-11 but not archived, last repo push 2024-12-04; pin the exact version and vendor the wheel — do not expect upstream fixes). **LanceDB 0.37.x** replaces v1's faiss-cpu+nano-vectordb pairing (single embedded library, disk-backed Lance format, native metadata filtering, no server process). **SQLite3 (stdlib)** is the KV primitive (ACID, embedded, zero external server, correct by the "no external DB servers" constraint). **FastMCP 3.4.7** is the MCP server framework (actively developed, documented sibling-ASGI-app mount pattern that avoids an open upstream bug in the low-level `mcp` SDK). **FastAPI 0.141.x** provides the optional REST surface (keep as an extras group, not a hard dependency). **Pydantic v2** (2.13.x) for all data models and validation (3.5x faster than jsonschema at runtime). **igraph 1.0.0** for graph algorithms and PPR (PageRank/Personalized PageRank, 10-50x faster than NetworkX for graphs >100K nodes, which matters once the corpus is real). **jsonschema 4.26.x** specifically for CONTRACT §19's static schema validator (Pydantic generates schemas but does not validate arbitrary external ones). **ragas 0.4.x** for RAG eval metrics (reference-free, purpose-built for this use case, embeddable with no external services).

**Core technologies:**
- **Python 3.12** — runtime (v1 baseline, validated 3.10-3.12, no reason to drift)
- **pycozo[embedded] 0.7.6** — graph store primitive, architecture-frozen, embedded RocksDB, pinned forever
- **lancedb 0.37.x** — vector store (single library, disk-backed, metadata filtering, no server)
- **sqlite3 (stdlib)** — KV store primitive (ACID, embedded, no server)
- **fastmcp 3.4.7** — MCP server framework (actively maintained, sibling-ASGI-app pattern)
- **fastapi 0.141.x** — optional REST surface (keep optional via extras group)
- **pydantic v2.13.x** — data models and validation (3.5x faster than jsonschema)
- **igraph 1.0.0** — PPR/graph algorithms (built-in PRPACK solver, 10-50x faster than NetworkX)
- **jsonschema 4.26.x** — CONTRACT §19 static validator (for arbitrary external JSON Schema documents)
- **ragas 0.4.x** — RAG eval metrics for A/A calibration (reference-free, purpose-built)

No external database servers. No Docker as a deployment boundary. The embeddable core depends only on Cozo + LanceDB + Pydantic + igraph + jsonschema; REST and MCP surfaces stay opt-in.

### Expected Features

**Table stakes (every comparable product has these):**
- Document ingest (upload + structured payload) with async job polling — already a v1 primitive, just expose it
- Document deletion with graph-aware GC (flagged as decomposition work for whichever rung touches HippoRAG 2's shared-entity graph)
- Four named query modes over the CONTRACT §18 closed envelope (mode vocabulary does not leak modality internals, unlike all competitors)
- Citations/provenance on every answer (already tied to DR-04 per-chunk provenance, confirmed table-stakes by R2R and LlamaIndex)
- Corpus/status introspection (document count, index freshness, per-modality index state)
- MCP tool surface with curated intention-level tools (ingest, query, delete, status, compare) — NOT a 1:1 granular dump of REST endpoints

**Differentiators (competitive advantage, no competitor has these):**
- **Side-by-side modality comparison** — run the same query against two modalities, return both, on one call (rung 4 proof point, the actual Core Value statement)
- **A/B promotion + rollback ledger** — promote a configuration to production with explicit rollback (already contracted, expose over API once comparison is trusted)
- **Trace/seam-level inspection** — reveal node-by-node execution trace (which fitted parts ran, what each produced) — valuable for debugging decomposed modalities
- **Cost/budget-token accounting per query** — expose if/when callers need to route by cost, not just correctness

**Defer to v2+:**
- Self-improving/auto-promotion loop (contract-frozen as manual, caller-invoked only)
- Any UI/dashboard (explicitly out of scope; Sourcerer or other clients render the structured JSON response)

**MVP definition (launch with):**
All table stakes + side-by-side comparison. The four query modes and comparison are the milestone's actual success criteria. Promotion/rollback, trace inspection, and cost accounting follow in Phase 2+.

### Architecture Approach

The architecture is a contract-driven runner/scheduler sitting atop frozen primitives. **Wiring** is inert JSON (no eval semantics) describing a directed acyclic graph of nodes and their data dependencies. **Part registry** (loaded once at startup via `importlib.metadata.entry_points`) maps installed parts to their schema/effects declarations. **Validator** (Falsifier 2's deliverable) parses wiring JSON, type-checks against NodeKind tagged sums (Pydantic discriminated unions), detects cycles via Tarjan SCC algorithm, computes depth via SCC-condensation min-reduce, and derives execution_mode from effects[]. **Runner** (TopologicalSorter + asyncio.TaskGroup) executes the validated graph: reads readiness from the sorter, runs one ready batch as concurrent coroutines in a TaskGroup, respects per-node budget metering and execution_mode placement (in-process/subprocess/confined-unit/long-lived-service). **Machine-owned stores** (graph/vector/KV/lexical/blob primitives) are gated by effects[] — the runner never grants a capability a node didn't declare. **Artifact registry** (content-hash-addressed blob store in git-object-store layout + SQLite metadata index) records outputs at promotion time, never at runtime. **Ledger** (append-only SQLite table) is the single source of truth for promotion history; "active pointer" is a derived query, never an independently-written field.

The build order is: identity/keying first (everything downstream reads from it), part registry second, validator third, minimal runner fourth, artifact registry + ledger fifth. This order ensures each step's tests run against the previous step's real output, not stubs.

**Major components:**
1. **Identity/keying** — `(name@version, config_hash, resolved_dependency_ids)` tuple; config_hash from RFC 8785 JCS + SHA-256; used as cache partition key, artifact namespace, ledger arm-instance hash
2. **Part registry** — thin discovery layer via `importlib.metadata.entry_points`, loaded once at process start, no plugin lifecycle machinery
3. **Validator** — four independently testable passes: parse (Pydantic discriminated union), cycle detection (Tarjan SCC), depth computation (SCC-condensation min-reduce), execution_mode derivation (effects[] → {in-process, subprocess, confined-unit, long-lived-service})
4. **Runner/scheduler** — TopologicalSorter for readiness bookkeeping + asyncio.TaskGroup for structured concurrency of one ready batch; no retries/backoff built in (retry is wiring content, per contract)
5. **Machine-owned stores** — embedded engines only (Cozo, SQLite, LanceDB, no server processes); effects[]-gated access from nodes
6. **Artifact registry** — content-hash-addressed (git-object-store style fan-out layout) + SQLite metadata rows; supports deletion (tombstoning, GC)
7. **Ledger** — append-only INSERT-only table with monotonic id; active pointer is a derived query over the ledger, never an independent column

### Critical Pitfalls

1. **Storage/lock ownership hidden inside "decomposed" nodes** — Logic decomposition into 17 node positions can look complete while every node still reaches into v1's singleton `shared_storage.py` and process-wide locks. Mitigation: track storage-handle ownership and lock-ordering separately from call-graph boundaries. Mandatory per-node checklist: storage access routed through machine primitive, not direct singleton reference.

2. **Parity declared from single run, hiding real LLM variance** — Single-run evaluation is unreliable; output quality swings ~15% across nominally identical runs. Mitigation: run parity harness N times per side, hold LLM/embedding variance constant (same seeds, same provider), report variance band not a single diff.

3. **A/A calibration underpowered, so it "passes" without meaning anything** — Properly-sized A/A calibration computes the system's own noise floor before comparing modalities. Mitigation: before Phase 1 gate, run identical pipeline N times, measure empirical variance, derive Minimum Detectable Effect, document in A/A artifact.

4. **Dev/holdout/sealed eval splits leak under iteration pressure** — Using holdout as feedback loop during node-boundary iteration, unlogged. Mitigation: log every holdout evaluation; reserve sealed set only for promotion decisions; flag if holdout and sealed diverge.

5. **Fitting contract erodes at opaque ingest boundary under schedule pressure** — Opaque ingest core looks identical to opaque-node-as-escape-hatch from outside. Mitigation: write down explicitly at admission time what may change inside vs. across boundary; enforce with compat-test-suite gate.

## Implications for Roadmap

### Phase 1: Falsifier Baseline & Validator Foundation

**Rationale:** Foundational infrastructure (validator, A/A calibration harness) that every subsequent phase depends on. Before decomposing any node or comparing modalities, establish the measurement infrastructure.

**Delivers:**
- Identity/keying module (RFC 8785 canonicalization)
- Falsifier 2 (static depth/execution_mode validator)
- Falsifier 5 (A/A calibration with N-run variance band and MDE)
- Parity harness with byte-identical pre-embedding assertion and pinned model version

**Addresses:** Infrastructure only; no table-stakes features yet.

**Avoids:** Pitfalls 2, 3, 8 (parity variance, underpowered A/A, embedding drift).

**Research flags:** None — standard Python patterns, well-documented.

---

### Phase 2: Query-Side Decomposition & Parity Coverage

**Rationale:** Extract 17 query-side node positions once validator and A/A baseline exist. This is where logic decomposition happens and storage-decomposition risk is highest.

**Delivers:**
- 17 query-side nodes decomposed and fitted
- Parity harness coverage for each node (N runs, variance band)
- Storage-ownership audit per node
- Cozo-bug regression suite runs green against all graph-storage implementations

**Addresses:** Partial ingest exposure, partial query modes.

**Avoids:** Pitfalls 1, 6, 8 (storage stalls, Cozo bugs, embedding drift).

**Dependencies:** Requires Phase 1.

**Research flags:** HippoRAG 2 graph patterns (PPR, multi-hop latency); Cozo query refactoring edge cases.

---

### Phase 3: Opaque Ingest & Modality Nodes

**Rationale:** Admit ingest core as opaque node (with explicit boundary rules), complete LightRAG end-to-end, port HippoRAG 2, expose side-by-side comparison endpoint.

**Delivers:**
- Ingest core admitted as opaque with "what may change inside vs. across" rule documented
- LightRAG end-to-end running and compared to v1
- HippoRAG 2 ported as opaque node
- Side-by-side modality comparison endpoint (REST + MCP) — **rung 4 proof point**
- Corpus/status introspection endpoint
- Document deletion with graph-aware GC

**Addresses:** All table-stakes features + side-by-side comparison (Core Value statement).

**Avoids:** Pitfalls 4, 5 (eval leakage, contract erosion).

**Dependencies:** Requires Phase 2.

**Research flags:** HippoRAG 2 porting scope; graph-aware deletion semantics for shared entities.

---

### Phase 4: Evaluation & Promotion Infrastructure

**Rationale:** Quantify relative modality performance and operationalize promotion/rollback as a shipping feature.

**Delivers:**
- A/B promotion + rollback ledger exposed over REST + MCP
- Trace/seam-level inspection endpoint (read-only, debug flag)
- Sealed-set eval comparing LightRAG and HippoRAG 2 (effect sizes vs. MDE)
- Per-query cost accounting (optional)
- Artifact registry and ledger stores integrated with runner

**Addresses:** Phase 2+ differentiators (promotion, trace inspection, cost accounting).

**Avoids:** Pitfalls 2, 3, 7 (parity noise, underpowered A/A, concurrency).

**Dependencies:** Requires Phase 3 (side-by-side comparison working).

**Research flags:** Sealed-set sizing (corpus, queries) for realistic MDE; cost-accounting scope validation.

---

### Phase Ordering Rationale

1. **Phase 1 first:** Infrastructure (validator, A/A baseline) is the least risky and unblocks everything.
2. **Phase 2 before Phase 3:** Extract logic before admitting opaque nodes.
3. **Phase 3 before Phase 4:** Can't promote without proven comparison.
4. **All four phases ship table-stakes + differentiator together:** Don't subset these — they are interdependent.

### Research Flags

**Need deeper research during planning:**
- Phase 2: HippoRAG 2 graph patterns; Cozo query edge cases
- Phase 3: Graph-aware deletion semantics; ingest boundary definition; embedding alignment
- Phase 4: Sealed-set sizing; cost-accounting necessity

**Standard patterns (lower priority):**
- Phase 1: Identity/RFC 8785, validator, A/A calibration — all textbook

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| **Stack** | HIGH | PyPI/GitHub live data verified; Cozo state confirmed; no churn expected |
| **Features** | MEDIUM | Market consensus on table stakes; differentiators (comparison, promotion) are novel and need rig validation |
| **Architecture** | MEDIUM | Core patterns (TopologicalSorter+TaskGroup, artifact store, ledger) are stdlib/well-known; project structure inferred from CONTRACT.md |
| **Pitfalls** | MEDIUM | Sourced from code audit + decomposition literature; no public precedent for this exact rebuild, so treat as informed synthesis |

**Overall: MEDIUM.** Research is internally consistent and grounded in freeze-dried project docs. But this is novel — no precedent for "fully decomposed modality-agnostic RAG with side-by-side comparison" — so roadmap needs validation checkpoints in Phase 1–2.

### Gaps to Address

- **HippoRAG 2 porting scope:** Spike during Phase 2 planning to estimate effort.
- **Graph-aware deletion:** Needs Phase 3 design session before coding.
- **Sealed-set sizing:** Phase 1 planning should finalize MDE corpus/query counts.
- **Cost-accounting scope:** Phase 1 validation should confirm if table-stakes or Phase 2+.
- **Runner concurrency (§H1):** Phase 1 spike on execution_mode placement.

## Sources

**Primary (HIGH):**
- PyPI JSON API (live, 2026-08-29): pycozo, mcp, fastmcp, fastapi, pydantic, igraph, lancedb, jsonschema, ragas
- GitHub API: CozoDB repo state (2026-08-29)
- RFC 8785: JSON Canonicalization Scheme (IETF spec)
- Python 3 stdlib docs: graphlib, asyncio, importlib.metadata, hashlib, sqlite3
- Project frozen docs: CONTRACT.md, RIG.md, SYSTEM-MODEL.md, CONCERNS.md

**Secondary (MEDIUM):**
- Embedded vector DB comparison 2026 (vendor/blog sources)
- igraph vs. NetworkX PPR benchmarks
- Strangler fig pattern (AWS, Medium)
- LLM variance & A/B testing (GrowthBook, Towards Data Science)
- Embedding drift in RAG (blogs, community)
- Competitor docs (R2R, LightRAG, GraphRAG, Cognee, LlamaIndex)

**Tertiary (LOW, needs Phase planning validation):**
- HippoRAG 2 porting effort (no team estimate yet)
- Graph-aware deletion semantics (design TBD)

---

*Research completed: 2026-08-29*
*Ready for roadmap: yes*
