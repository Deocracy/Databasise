---
last_mapped_commit: 8044f9a
---

# Codebase Structure

**Analysis Date:** 2026-09-08  

## Directory Layout

```
project-root/
├── databasise/                     # 2.0 Agnostic machine (D4 One Machine)
│   │
│   ├── seam/                       # Consumer-facing API (§18 public envelope)
│   │   ├── engine.py               # Databasise async engine: query(), query_stream()
│   │   ├── rest.py                 # FastAPI REST transport (optional, requires [rest] extra)
│   │   ├── envelope.py             # ResponseEnvelope, SeamEvent (frozen models)
│   │   ├── query.py                # QueryObject (frozen model, consumer input)
│   │   ├── selectors.py            # Selector resolution (alias → arm)
│   │   ├── evidence.py             # Evidence minting, EvidenceRef, resolve_evidence_ref
│   │   ├── trace_store.py          # Opaque trace token → RunRecord persistence
│   │   ├── tokens.py               # TokenBreakdownEntry, assemble_token_breakdown
│   │   ├── refusals.py             # SeamRefusalError sealed hierarchy (CR-03)
│   │   ├── redact.py               # Redaction functions (CR-02 allow-list)
│   │   └── __init__.py
│   │
│   ├── validator/                  # Wiring parse & validation
│   │   ├── parse.py                # parse_wiring(), ParsedWiring (CONTRACT §1 + Falsifier 2)
│   │   └── __init__.py
│   │
│   ├── runner/                     # Execution scheduler & tracing
│   │   ├── scheduler.py            # run_wiring(), node dispatch, budget tracking
│   │   ├── trace.py                # RunRecord, NodeTrace, TokenAccounting (RIG §TR)
│   │   ├── budget.py               # Token budget enforcement per node
│   │   ├── guards.py               # Guard checks (self-declared refusals)
│   │   └── __init__.py
│   │
│   ├── parts/                      # Component schema & registry
│   │   ├── schema.py               # Part, WiringNode, NodeKind (tagged sum), Effect (17-member)
│   │   ├── registry.py             # PartRegistry, default_registry (name@version dispatch)
│   │   └── __init__.py
│   │
│   ├── parts_core/                 # Reference & domain-specific parts
│   │   ├── __init__.py             # Default parts: passthrough, kv-writer, fake stubs
│   │   ├── declared_only.py        # Declaration-only marker part (no body)
│   │   ├── fake_llm_caller.py      # Test stub LLM client
│   │   ├── fake_retriever.py       # Test stub retriever
│   │   ├── fixpoint_body.py        # Fixed-point loop body (primitive)
│   │   ├── passthrough.py          # Identity part (debugging)
│   │   │
│   │   └── lightrag/               # LightRAG query-side parts (Phase 3 decompose)
│   │       ├── __init__.py
│   │       ├── assemble.py         # Result assembly/merge
│   │       ├── chunk_kg.py         # KG-based chunk retrieval
│   │       ├── chunk_vector.py     # Vector-based chunk retrieval
│   │       ├── embedder_query.py   # Embedding for query
│   │       ├── entity_lookup.py    # Entity retrieval from graph
│   │       ├── generate.py         # LLM response generation
│   │       ├── keywords.py         # Keyword extraction
│   │       ├── relation_lookup.py  # Relation retrieval from graph
│   │       ├── rerank.py           # Reranking retrieved chunks
│   │       └── truncator.py        # Token budget truncation
│   │
│   ├── stores/                     # Storage abstraction (embedded, pluggable)
│   │   ├── base.py                 # BaseStorage (async lifecycle: init, index_done, finalize)
│   │   ├── kv.py                   # SqliteKVStore (per-namespace key-value)
│   │   ├── vector.py               # MultiNamespaceVectorStore (Faiss, CPU-only)
│   │   ├── graph.py                # CozoGraphStore (Datalog + RocksDB)
│   │   ├── lexical.py              # LexicalStore (SQLite FTS5, full-text search)
│   │   ├── blob.py                 # BlobStore (content-addressed files)
│   │   └── __init__.py
│   │
│   ├── identity/                   # Component identity & canonicalization
│   │   ├── canon.py                # canonicalise() (deterministic JSON serialization)
│   │   ├── instance.py             # Instance resolution with SCC-based depth
│   │   ├── env.py                  # Environment config handling
│   │   └── __init__.py
│   │
│   ├── wirings/                    # Wiring resolution & arm dispatch
│   │   ├── resolve.py              # resolve_arm() (selector → executable wiring)
│   │   ├── lightrag/               # LightRAG wiring definitions
│   │   │   ├── base.json           # Base wiring structure
│   │   │   ├── arm-naive.json-patch.json         # Query-only (no hybrid/local/global)
│   │   │   ├── arm-local.json-patch.json         # Local KG + vector
│   │   │   ├── arm-global.json-patch.json        # Global KG + vector
│   │   │   ├── arm-hybrid.json-patch.json        # Hybrid mode
│   │   │   └── arm-bypass.json-patch.json        # Bypass all retrieval
│   │   │
│   │   └── __init__.py
│   │
│   ├── clients/                    # LLM/embedding client abstraction
│   │   ├── base.py                 # LLMClient, EmbeddingClient base classes
│   │   ├── openai_compat.py        # OpenAI-compatible client impl
│   │   └── __init__.py
│   │
│   ├── evidence/                   # Evidence collection & Falsifier 2
│   │   ├── falsifier2.py           # Falsifier 2 evidence (depth, execution_mode proof)
│   │   ├── parity_report.py        # Parity measurement report
│   │   └── __init__.py
│   │
│   ├── ledger/                     # Append-only audit log
│   │   ├── ledger.py               # RunRecord ledger (Phase 1 complete)
│   │   └── __init__.py
│   │
│   ├── parity/                     # Real-time comparison harness (Phase 3+)
│   │   ├── run_arm.py              # end-to-end v2 arm execution (unredacted)
│   │   ├── v1_arm.py               # Legacy v1 query execution (reference)
│   │   ├── run_comparison.py       # Paired arm runs + variance analysis
│   │   ├── corpus.py               # Shared corpus fixture
│   │   ├── import_index.py         # v1 index import to v2 namespace
│   │   ├── storage_audit.py        # Storage state audit post-run
│   │   └── __init__.py
│   │
│   ├── registry_artifact/          # Part registry (TBD: JSON/YAML files)
│   │   └── __init__.py
│   │
│   ├── tests/                      # Unit & integration tests (59 test files)
│   │   ├── conftest.py             # pytest fixtures, store setup
│   │   ├── clients/
│   │   ├── evidence/
│   │   ├── fixtures/
│   │   ├── identity/
│   │   ├── ledger/
│   │   ├── parts/
│   │   ├── parts_core/
│   │   ├── parity/
│   │   ├── registry_artifact/
│   │   ├── runner/
│   │   ├── seam/
│   │   ├── stores/
│   │   └── validator/
│   │
│   ├── __init__.py                 # Public: run_wiring() (machine-internal, unredacted)
│   └── namespaces.py               # Workspace/namespace management
│
├── v1/                             # LightRAG legacy fork (reference impl)
│   ├── lightrag/
│   │   ├── lightrag.py             # LightRAG facade (main API)
│   │   ├── api/                    # FastAPI server (legacy)
│   │   ├── chunker/                # Document chunking (token, semantic, paragraph)
│   │   ├── kg/                     # Knowledge graph storage (Cozo, Neo4j, Postgres, etc.)
│   │   ├── llm/                    # LLM provider integrations
│   │   ├── parser/                 # File format parsers (PDF, DOCX, PPTX, etc.)
│   │   ├── operate.py              # Query orchestration (4-stage pipeline)
│   │   ├── pipeline.py             # Async document ingest pipeline
│   │   ├── base.py                 # Storage abstractions
│   │   ├── evaluation/             # Evaluation tools
│   │   ├── tools/                  # Utilities (visualizer, etc.)
│   │   └── tests/                  # v1 test suite
│   │
│   ├── lightrag_webui/             # React 19 frontend
│   │   ├── src/
│   │   │   ├── components/         # React components (hooks, graph viz)
│   │   │   ├── pages/              # Page components (routing via React Router)
│   │   │   ├── App.tsx             # Root component
│   │   │   └── main.tsx            # Vite entry point
│   │   │
│   │   ├── vite.config.ts          # Vite build config
│   │   ├── tsconfig.json
│   │   ├── eslint.config.js        # ESLint (flat config format)
│   │   ├── .prettierrc.json        # Prettier formatting
│   │   ├── package.json
│   │   └── index.html
│   │
│   ├── examples/                   # Standalone demo scripts
│   ├── prompts/                    # Prompt templates
│   ├── scripts/                    # Utility scripts (setup, release)
│   ├── tests/                      # v1 test suite
│   ├── docs/
│   ├── README.md
│   └── pyproject.toml              # v1 project metadata (fork of LightRAG)
│
├── docs/                           # System model documentation (frozen from rag-modality-swap)
│   └── system-model/               # CONTRACT.md, RIG.md, PARTS.md, SYSTEM-MODEL.md
│
├── .planning/                      # Orchestration artifacts
│   ├── ROADMAP.md                  # Phase 1-7 schedule (updated per completion)
│   ├── STATE.md                    # Current execution state
│   ├── REQUIREMENTS.md             # Acceptance criteria (frozen per phase gate)
│   ├── phases/                     # Completed phase artifacts
│   │   ├── 01-machine-core/
│   │   ├── 02-falsifier-gate/
│   │   ├── 03-lightrag-query-side/
│   │   └── 04-the-seam/
│   │
│   └── codebase/                   # (This directory — maps persist here)
│       ├── ARCHITECTURE.md         # System layers, data flow, abstractions
│       ├── STRUCTURE.md            # File/directory layout, where to add code
│       ├── STACK.md                # Technology stack (Python, FastAPI, etc.)
│       ├── INTEGRATIONS.md         # External services (LLMs, vector stores, etc.)
│       ├── CONVENTIONS.md          # Code style, naming, patterns
│       └── TESTING.md              # Test framework, patterns, coverage
│
├── .claude/                        # Claude project settings
│   └── CLAUDE.md                   # Project constraints & architecture rubric
│
├── pyproject.toml                  # Root project metadata (databasise package)
├── uv.lock                         # Locked Python dependencies (uv)
├── Makefile                        # Development tasks
├── Dockerfile                      # Multi-stage container build
├── docker-compose.yml              # Local dev environment
└── .pre-commit-config.yaml         # Git hooks (ruff, black, isort)
```

## Directory Purposes

**`databasise/`** — The v2.0 agnostic machine (phases 1-4 complete)
- Public consumer-facing seam (§18) in `seam/`
- Machine-internal orchestration (validator, runner, parts, stores)
- Parity harness for real-time v1/v2 comparison
- Embedded stores only (Cozo, Faiss, SQLite) — no external DB servers
- 59 integration & unit tests across 14 test directories

**`databasise/seam/`** — The §18 contract boundary
- `engine.py`: `Databasise` class with `query()`, `query_stream()`, `resolve_trace()` methods
- `rest.py`: Optional FastAPI transport (install via `uv sync --extra rest`)
- `envelope.py`: Frozen ResponseEnvelope model (redacted, no internal IDs)
- `evidence.py`: Evidence extraction & opaque reference minting
- `trace_store.py`: Trace persistence & retrieval (via opaque token)
- `refusals.py`: SeamRefusalError sealed hierarchy (4+ subclasses)
- Redaction boundary: All internal identities (wiring_id, node_id, arm_id) stay inside machine

**`databasise/runner/`** — Execution scheduler & tracing
- `scheduler.py`: Topological sort, per-node semaphore, asyncio.gather() dispatch
- `trace.py`: RunRecord, NodeTrace, TokenAccounting (honesty invariant per RIG §TR.3)
- `budget.py`: Per-node token allowance enforcement, halt on exhaustion

**`databasise/parts/`** — Component system (name@version)
- `schema.py`: Part, WiringNode, NodeKind (fanout/join/fixpoint/subgraph/opaque), 17-member Effect vocabulary
- `registry.py`: PartRegistry (default + v1 LightRAG parts)

**`databasise/stores/`** — Embedded storage layer
- `kv.py`: SQLite key-value store (doc status, LLM cache)
- `vector.py`: Faiss + multi-namespace indexing (exact cosine similarity)
- `graph.py`: Cozo graph database (Datalog + RocksDB)
- `lexical.py`: SQLite FTS5 full-text search
- `blob.py`: Content-addressed file storage

**`databasise/wirings/lightrag/`** — LightRAG wiring definitions
- `base.json`: Immutable base structure (nodes, edges, storage config)
- `arm-naive.json-patch.json`: Query-only arm (default, Phase 4)
- `arm-local.json-patch.json`: Local KG + vector
- `arm-global.json-patch.json`: Global KG + vector
- `arm-hybrid.json-patch.json`: Hybrid mode
- `arm-bypass.json-patch.json`: Bypass all retrieval (testing)

**`databasise/parity/`** — Parity harness (Phase 3+)
- `run_arm.py`: Execute v2 arm against real v1 index (unredacted RunRecord)
- `v1_arm.py`: Legacy v1 query execution (reference)
- `run_comparison.py`: Paired runs + variance analysis
- `import_index.py`: v1 index import to v2 namespace

**`databasise/tests/`** — Test suite (mirrors source structure)
- 59 test files across 14 directories
- Fixtures: store setup, corpus, client stubs
- Parity tests: end-to-end arm comparison
- Seam tests: refusal hierarchy, redaction, evidence minting

**`v1/`** — LightRAG legacy fork
- `lightrag/lightrag.py`: Main facade (still used as reference + opaque ingest core until Phase 5)
- `lightrag/kg/`: 11 storage backends (Cozo, Neo4j, Postgres, etc.)
- `lightrag/llm/`: 12+ LLM provider integrations
- `lightrag_webui/`: React 19 frontend with Sigma.js graph visualization
- Still active: docs, examples, tests, sidecar mode

**`docs/system-model/`** — Frozen architecture specification
- `CONTRACT.md`: §1-§18 seam contract (251KB)
- `RIG.md`: Run record schema & evidence tiers (155KB)
- `PARTS.md`: Part capability matrix (185KB)
- `SYSTEM-MODEL.md`: Architecture rubric (69KB)

**`.planning/`** — Orchestration & mapping artifacts
- `ROADMAP.md`: Phase 1-7 schedule
- `phases/`: Completed phase deliverables (01-machine-core, 02-falsifier-gate, 03-lightrag-query-side, 04-the-seam)
- `codebase/`: Architecture/structure maps (this directory)

## Key File Locations

### Entry Points

| Purpose | File | Function/Class |
|---------|------|-----------------|
| **REST API** | `databasise/seam/rest.py` | `app = FastAPI(...)` endpoints |
| **In-process async** | `databasise/seam/engine.py` | `Databasise` class |
| **Machine-internal** | `databasise/__init__.py` | `run_wiring()` (unredacted, for parity only) |
| **Parity harness** | `databasise/parity/run_arm.py` | `run_arm(arm_name, query_obj, ...)` |

### Configuration

| Item | File |
|------|------|
| **v2 project metadata** | `pyproject.toml` (root) |
| **Python dependencies** | `uv.lock` (locked, reproducible) |
| **Docker build** | `Dockerfile` (multi-stage: frontend → Python) |
| **Dev environment** | `docker-compose.yml` + `.env.example` |
| **Pre-commit hooks** | `.pre-commit-config.yaml` (ruff, black, isort) |
| **Claude project rules** | `.claude/CLAUDE.md` (architecture rubric) |
| **Parity configuration** | `v1/.env.parity` (client keys for real LLM runs) |

### Core Logic

| Module | Files | Purpose |
|--------|-------|---------|
| **Seam** | `databasise/seam/*.py` | Consumer API (query, response envelope, redaction) |
| **Validation** | `databasise/validator/parse.py` | Wiring schema + Falsifier 2 (depth, execution_mode) |
| **Scheduling** | `databasise/runner/scheduler.py` | Node dispatch, budget tracking, tracing |
| **Storage** | `databasise/stores/{kv,vector,graph,lexical,blob}.py` | Embedded backends |
| **Parts** | `databasise/parts/{schema,registry}.py` | Component system (name@version) |
| **Evidence** | `databasise/seam/evidence.py` | Chunk extraction, opaque reference minting |
| **Tracing** | `databasise/runner/trace.py` | RunRecord assembly, honesty invariant |

### Testing

| Test Directory | Scope |
|---|---|
| `databasise/tests/seam/` | Refusal hierarchy, redaction, envelope assembly |
| `databasise/tests/runner/` | Scheduler, budget enforcement, node tracing |
| `databasise/tests/stores/` | Graph/vector/KV storage operations |
| `databasise/tests/parity/` | End-to-end v2 vs v1 arm comparison |
| `databasise/tests/validator/` | Wiring parsing, Falsifier 2 depth/execution_mode |
| `v1/tests/` | Legacy LightRAG test suite |

## Naming Conventions

### Files

| Pattern | Example | Location |
|---------|---------|----------|
| **Python modules** | `engine.py`, `scheduler.py` | `databasise/**/*.py` |
| **Test files** | `test_engine.py` | `databasise/tests/**/*.py` |
| **Wiring patches** | `arm-naive.json-patch.json` | `databasise/wirings/lightrag/` |
| **Config files** | `.env.parity`, `pyproject.toml` | Root, v1/ |
| **Component files** | `PascalCase` (React) | `v1/lightrag_webui/src/components/` |

### Directories

| Pattern | Example | Purpose |
|---------|---------|---------|
| **Module packages** | `seam/`, `stores/`, `runner/` | Logical grouping (same as Python namespace) |
| **Test mirrors** | `tests/seam/`, `tests/stores/` | Mirrors source structure |
| **Domain parts** | `parts_core/lightrag/` | Modality-specific components |
| **Wiring arms** | `wirings/lightrag/` | Query mode variants (naive, local, global) |

## Where to Add New Code

### New Modality (Phase 6+: HippoRAG 2)

**Wiring & parts:**
```
databasise/wirings/hipporag2/
├── base.json                       # Base structure
└── arm-*.json-patch.json          # Query mode variants

databasise/parts_core/hipporag2/
├── __init__.py
├── entity_linker.py               # HippoRAG-specific entity linking
├── entity_vector_search.py        # Entity-vector retrieval
└── ...
```

**Part registry entry:**
- Add to `databasise/parts_core/__init__.py`: register Part instances
- Selector in `databasise/seam/selectors.py`: capability="hipporag2" → resolve to hipporag2 wiring

### New Seam Operation (Phase 5+)

**Refusal subclass:**
```python
# databasise/seam/refusals.py
class MyNewRefusal(SeamRefusalError):
    def __init__(self, user_input: str):
        self.user_input = user_input
        super().__init__(f"Cannot process: {user_input}")
```

**REST endpoint (if exposing via REST):**
```python
# databasise/seam/rest.py
@app.post("/my_new_operation")
async def my_new_operation(...) -> MyResponseModel:
    try:
        # call Databasise method
    except SeamRefusalError as e:
        # REST exception handler converts to 422
```

### New Store Backend (Phase 5+)

**Implementation:**
```
databasise/stores/postgres_impl.py   # New backend (or extend existing)
```

**Base inheritance:**
```python
from databasise.stores.base import BaseGraphStorage

class PostgresGraphStore(BaseGraphStorage):
    async def initialize(self): ...
    async def query_relations(self, ...): ...
    async def finalize(self): ...
```

**Part registration:**
- Seam layer passes store dict to scheduler; scheduler passes to nodes
- Store accessed via `stores["graph"]` (keyed by interface, not impl)

### New Test

**Pattern:**
```
databasise/tests/{module}/{test_name}.py
```

**Structure:**
- Fixtures from `conftest.py` (store setup, corpus, client stubs)
- One test per focused behavior
- Use async fixtures with `scope="function"` (store cleanup between tests)
- Parity tests: paired runs via `run_comparison.py`

## Special Directories

**`databasise/tests/fixtures/`:**
- Shared test data (corpus snapshots, index imports)
- Corpus JSON files, v1 index snapshots

**`databasise/tests/seam/`:**
- Refusal testing: each SeamRefusalError subclass tested
- Redaction testing (CR-02 allow-list verification)
- Evidence & trace minting

**`.planning/phases/`:**
- `01-machine-core/01-VERIFICATION.md` — Phase 1 acceptance suite results
- `02-falsifier-gate/02-GATE-01-WAIVER.md` — Falsifier 5 deferral record
- `03-lightrag-query-side/03-GATE-AMENDMENT.md` — Phase 3 gate conditions
- `04-the-seam/04-RESEARCH.md` — Phase 4 design decisions

---

*Structure analysis: 2026-09-08*
