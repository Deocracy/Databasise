# Stack Research

**Domain:** Embeddable modality-agnostic RAG engine (Python), REST + MCP surface, graph/vector/KV primitives, no external DB servers
**Researched:** 2026-08-29
**Confidence:** HIGH (version/maintenance data verified live against PyPI JSON API and GitHub API on 2026-08-29; qualitative comparisons from web search, dated where staleness matters)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12 | Runtime | Already the v1 baseline (3.10+ dev, 3.12-slim prod); no reason to move off it for an embeddable-in-process engine |
| `pycozo[embedded]` | 0.7.6 | Graph store primitive | **Architecture-frozen incumbent** (D4 One Machine, not up for debate). RocksDB-backed, embeds in-process, no server. Confirmed via PyPI + GitHub API: last PyPI release 2023-12-11, last repo push 2024-12-04, not archived, 4.1k stars, 50 open issues — dormant but not dead. Pin the exact version and vendor the wheel; do not expect upstream fixes |
| `mcp` (official Python SDK) | 2.1.1 | MCP protocol types + low-level server | Reference implementation of the wire protocol (Anthropic + community maintained). Databasise's own MCP surface (CONTRACT §18) should validate against this, not a third-party reimplementation. Actively released (2026-08-25) |
| `fastmcp` | 3.4.7 | MCP server framework | Decorator-based, lowest-boilerplate way to build the tool/resource surface on top of `mcp`'s types. More actively developed than the official SDK's own high-level layer (`mcp.server.fastmcp`, itself originally upstreamed from an earlier fastmcp). Actively released (2026-08-10). Ships documented patterns for mounting alongside a FastAPI app as sibling ASGI apps — the official low-level SDK has an **open bug mounting Streamable HTTP directly onto an existing FastAPI app** (modelcontextprotocol/python-sdk#1367); use `fastmcp`'s mount pattern to avoid it |
| FastAPI | 0.141.x | Optional REST surface | Already the v1 choice; nothing in 2026 displaces it for an ASGI JSON API with Pydantic-native validation. Keep it optional (extras group), not a hard dependency of the embeddable core |
| Pydantic v2 | 2.13.x | Internal data models, FastAPI validation, settings | Already the v1 choice. ~3.5x faster than `jsonschema` validation in benchmarks because validation is compiled into the model, not re-parsed per call. Use for everything that is a Python-native model: request/response bodies, config, node registry entries defined in code |
| `igraph` | 1.0.0 | PPR / graph algorithms (HippoRAG rung 4) | Install as `igraph` — `python-igraph` on PyPI is now explicitly labeled "(legacy package)" pointing at the same code. igraph's default PageRank/Personalized-PageRank solver **is** PRPACK (the exact library HippoRAG's original paper cites) — no separate `prpack` package exists on PyPI; it's built into igraph's C core. Benchmarks consistently show igraph 10-50x faster than NetworkX for graphs above ~100K nodes, which matters once the graph store holds a real corpus, not a toy one |
| `uv` | 0.12.x | Package manager | Already the v1 choice; remains the 2026-standard fast resolver/installer for Python. Keep `uv.lock` |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `lancedb` | 0.37.x | Vector store primitive | Recommended replacement for v1's `faiss-cpu` + `nano-vectordb` pairing. Single embedded library: disk-backed Lance columnar format (won't blow RAM as the corpus grows past what v1's in-memory FAISS index tolerates), native metadata filtering, no server process — matches "no external DB servers" directly. Actively maintained (Aug 2026 release) |
| `faiss-cpu` | 1.15.x | Optional exact-ANN fallback | Keep as an available backend, not the default. Still Meta-maintained and very actively released (2026-08-03), proven in v1's query path — but it's a bare index library with no metadata/persistence layer of its own, which is why v1 paired it with `nano-vectordb`. If a node position needs raw exact cosine search with nothing else, this is the tool; otherwise LanceDB covers the same ground plus persistence |
| `jsonschema` | 4.26.x | Validate externally-authored JSON Schema documents | Use specifically for CONTRACT §19's static depth/execution_mode validator and any ANATOMY node-registry entries expressed as pure JSON Schema (not Python classes). This is the actual JSON Schema spec implementation — Pydantic generates schemas but does not fully validate arbitrary external ones (`allOf`/`oneOf`/`patternProperties` edge cases). Actively maintained (2026-01) |
| `fastjsonschema` | 2.22.x | Fast-path JSON Schema validation | Swap in if the §19 static validator runs on every build/CI invocation and `jsonschema`'s pure-Python walk becomes a measured bottleneck — it compiles schemas to Python code ahead of time. Don't reach for it until `jsonschema` is proven slow; it has a smaller feature surface (some spec edge cases unsupported) |
| `sqlite3` (stdlib) | Python 3.12 stdlib | KV store primitive | No dependency to add — ships with Python. ACID, embedded, zero external server, and it's the correct default per the "no external DB servers, embeddable" constraint. Use for the KV primitive itself and for the promote/rollback ledger and F-08 seam-level trace records (structured rows, JSON columns for payload) — don't reach for a tracing framework when the KV primitive already is the right shape for a ledger |
| `lmdb` | 2.3.x | KV store escalation path | Only if profiling shows `sqlite3` write throughput is the bottleneck on the runner/scheduler's hot path. Adds a C dependency (same tradeoff Cozo already made via RocksDB) — don't add it speculatively. Actively maintained (2026-07) |
| `ragas` | 0.4.x | RAG eval metrics for A/A calibration | Reference-free metrics (faithfulness, answer relevancy, context precision/recall) purpose-built for RAG, not general LLM testing. It's a scoring library, not a test runner or a server — fits "embeddable, no external services" directly. Use it to compute the per-tier A/A calibration numbers RIG §EV.1 needs |
| `deepeval` | 4.2.x | Optional CI-gating layer | Only add if/when the eval bundle needs pytest-style pass/fail assertions wired into CI, not just calibration scores. Broader metric catalog (50+, including agent/MCP-specific) but that breadth isn't needed for the Phase-1 A/A gate. Don't install both `ragas` and `deepeval` until there's an actual CI-gating requirement — start with `ragas` alone |
| `langchain-text-splitters` | current (already pinned in v1) | Chunking | Already proven in v1's ingest path; no reason to replace for the quarantined ingest core |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `setuptools` (>=64) | Build backend | Keep — already what v1 uses in `pyproject.toml`/`setup.py`, works fine with `uv`. Don't migrate to `hatchling` for its own sake; that's a lateral move with no functional gain for this rebuild |
| `pytest` + `pytest-asyncio` | Test runner | Already the v1 choice, no reason to change |
| `ruff` | Lint/format | Already referenced in v1 `pyproject.toml` tool config |

## Installation

```bash
# Core embeddable engine (always installed)
uv add "pycozo[embedded]"==0.7.6 lancedb pydantic

# REST surface (optional extra)
uv add --optional rest fastapi uvicorn

# MCP surface (optional extra)
uv add --optional mcp mcp fastmcp

# Graph algorithms (HippoRAG rung / PPR node positions)
uv add igraph

# Contract/schema validation
uv add jsonschema

# Eval bundle (Falsifier 5 / RIG §EV.1)
uv add --group eval ragas

# Dev
uv add --dev pytest pytest-asyncio ruff
```

Use `pyproject.toml` `[project.optional-dependencies]` groups (`rest`, `mcp`, `eval`) so the embeddable core (`pip install databasise`) pulls in only Cozo + LanceDB + Pydantic + igraph + jsonschema — REST and MCP surfaces stay opt-in, matching "Databasise embeddable in-process" as the base install.

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `lancedb` | `sqlite-vec` (0.1.9, actively maintained) | If the corpus is small enough that brute-force search is fine and you want vector search living in the same SQLite file as the KV primitive — appealing for minimalism but brute-force degrades past ~1M high-dim vectors, and the eval corpus plan (public bootstrap → owner's own corpus) makes that ceiling a real near-term risk, not a hypothetical one |
| `lancedb` | `chromadb` (1.5.x) | If prototyping speed matters more than scale — `pip install chromadb` + two lines is the fastest path to something working, but it's memory-resident and degrades past ~1M vectors on constrained RAM, which conflicts with "8GB RAM + SSD recommended" from v1's own deployment notes |
| `igraph` | `networkx` (3.6.x) | Only for small graphs (<100K nodes) or where a v1 code path already depends on NetworkX's specific API and porting cost isn't justified yet — don't use it for the PPR computation itself |
| `ragas` | `arize-phoenix` (20.4.x) | If the eval bundle later needs a full OTel-based trace/observability UI, not just calibration scores — Phoenix normally runs as a local launched app (still no external server dependency), but it's a bigger surface than a scoring library and isn't needed to pass Falsifier 5 |
| official `mcp` SDK / `fastmcp` | hand-rolled JSON-RPC over the existing FastAPI app | Never — the protocol has enough surface area (capabilities negotiation, resources, tools, streaming) that reimplementing it against the spec is pure risk with no upside over the reference SDK |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `nano-vectordb` | Stale since 2024-11-11 (0.0.4.3), thin wrapper whose functionality LanceDB now covers natively with active maintenance behind it | `lancedb` |
| `diskcache` | Stale since 2023-08-31 (5.6.3) — three years with no release; don't add a new dependency that's already effectively unmaintained | `sqlite3` (stdlib) directly, or `lmdb` if profiling demands it |
| `mlflow` for trace/versioning storage | Full ML-lifecycle platform (model registry, tracking server, artifact store) — enormous surface for what the promote/rollback ledger and F-08 trace shape actually need, and its tracking server model fights "no external DB servers" even though it *can* run embedded | `sqlite3` (stdlib) with a structured ledger table; add a real tracking system only if a future milestone needs cross-run dashboards |
| Reimplementing JSON Schema validation on top of Pydantic alone | Pydantic v2 generates JSON Schema from models but is not a general validator for arbitrary externally-authored JSON Schema documents (spec edge cases: `allOf`, `oneOf`, `patternProperties`, `$ref` resolution) | `jsonschema` for validating CONTRACT/ANATOMY-authored schemas; Pydantic for internal Python-native models |
| Low-level `mcp` SDK's direct Streamable-HTTP mount onto an existing FastAPI app | Open upstream bug (modelcontextprotocol/python-sdk#1367) as of the most recent report found | `fastmcp`'s documented sibling-ASGI-app mount pattern |

## Stack Patterns by Variant

**If the §19 static validator becomes a CI hot path:**
- Swap `jsonschema` for `fastjsonschema` on that call site only
- Because compiled-schema validation removes the pure-Python walk overhead, but keep `jsonschema` elsewhere for its fuller spec coverage

**If a corpus exceeds LanceDB's comfortable single-machine disk-index size:**
- That's an architecture-level question (external vector service), not a library swap — flag it against RIG §F3 affordability rather than silently reaching for a different embedded library

**If Cozo's PyPI staleness (no release since 2023-12-11) blocks a needed fix:**
- Evaluate `cozo-redb` (Rust-first fork on `redb`, keeps Datalog + HNSW) only as a contingency — this is a SELECTION.md-level decision per the frozen architecture, not something to switch to opportunistically mid-build

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|------------------|-------|
| `pycozo[embedded]`==0.7.6 | Python 3.10-3.12 | No newer release exists to test against 3.13+; pin Python to what v1 already validated (3.12) rather than chasing a newer interpreter |
| `fastmcp`>=3.x | official `mcp`>=2.x | `fastmcp` 3.x builds on the official SDK's types; keep both current together, don't pin `mcp` far behind `fastmcp`'s minimum |
| `pydantic`>=2.x | `fastapi`>=0.141.x | Already validated together in v1; no known friction |
| `lancedb` | Rust-toolchain build only if installing from source | Prefer prebuilt wheels (available for standard Linux/NixOS glibc targets) to avoid pulling a Rust toolchain into the embeddable install path |

## Sources

- PyPI JSON API (`pypi.org/pypi/<pkg>/json`) — live version + upload-date verification for `pycozo`, `cozo-embedded`, `mcp`, `fastmcp`, `fastapi`, `pydantic`, `igraph`, `python-igraph`, `lancedb`, `sqlite-vec`, `chromadb`, `faiss-cpu`, `nano-vectordb`, `usearch`, `jsonschema`, `fastjsonschema`, `diskcache`, `lmdb`, `ragas`, `deepeval`, `mlflow`, `arize-phoenix`, `uv`, `hatchling`, `setuptools` — confidence: HIGH (direct registry data)
- GitHub API (`api.github.com/repos/cozodb/cozo`, `/releases`) — confirmed not archived, last push 2024-12-04, last release 2023-12-11 — confidence: HIGH
- WebSearch: CozoDB maintenance status — confidence: MEDIUM (secondary summaries, cross-checked against GitHub API above)
- WebSearch: official MCP Python SDK + FastAPI same-process mounting, including modelcontextprotocol/python-sdk#1367 — confidence: MEDIUM
- WebSearch: embedded vector database comparison (LanceDB/ChromaDB/sqlite-vec) 2026 — confidence: MEDIUM (vendor/blog sources, cross-checked against PyPI activity)
- WebSearch: igraph vs NetworkX PPR performance — confidence: MEDIUM (benchmarks referenced are several years old but directionally uncontested; no newer contradicting data found)
- WebSearch: RAGAS vs DeepEval 2026 positioning — confidence: MEDIUM
- WebSearch: HippoRAG + igraph + PRPACK — confidence: MEDIUM, resolved that PRPACK is igraph's built-in default PageRank solver, not a separate PyPI package
- WebSearch: jsonschema vs Pydantic v2 validation — confidence: MEDIUM

---
*Stack research for: Databasise 2.0 embeddable modality-agnostic RAG engine*
*Researched: 2026-08-29*
