<!-- GSD:project-start source:PROJECT.md -->

## Project

**Databasise 2.0 — Fully Agnostic System**

Databasise 2.0: the RAG engine rebuilt as an **agnostic machine + fitting contract + versioned components**, implementing the v1.0 system model shipped by the RAG Modality Swap project (`docs/system-model/`, verbatim copy of `ServerDestroyer/rag-modality-swap-system-model`). A modality (LightRAG, HippoRAG 2, future paradigms) becomes a wiring of components over machine-owned primitives — databases (graph, vector, KV), LLM/embedding/reranker clients — instead of a monolithic library. Databasise is a **standalone product**: an embeddable, in-process engine whose public voice is its own REST + MCP surface (CONTRACT.md §18); Sourcerer is one consumer among any.

**Core Value:** **Modalities are swappable without consumers noticing:** the same corpus, the same seam, N modalities running side-by-side and comparable on the rig — proven by LightRAG and HippoRAG 2 both live behind one unchanging §18 envelope by milestone end.

### Constraints

- **Architecture**: D4 One Machine per SELECTION.md — settled, not re-litigated; contract vocabulary (NodeKind tagged sum, 17-member effects[], three artifact scopes, budget tokens, promote/rollback ledger) is frozen input
- **Language**: Python — all candidate modalities are Python; the fitting contract assumes Python parts
- **Runtime**: local NixOS (host legion), embeddable in-process; no external DB servers, no Docker
- **Gate discipline**: Phase 1 → 2 gate is Falsifiers 2 and 5 passing; rung N+1 never starts before rung N's gate
- **Evidence standard**: every promotion claim priced against RIG §F3's per-mutation-class affordability; no benchmark number settles a decision
- **Compatibility**: the §18 seam must stay modality-agnostic — swapping the fitted modality changes no field a consumer sees

<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->

## Technology Stack

## Languages

- Python 3.10+ - Core RAG engine, API server, document processing, embeddings
- TypeScript/React 19 - Web UI frontend with graph visualization
- JavaScript - Frontend build tooling (Vite, ESLint, Prettier)
- Rust - Build dependencies (Faiss, Cozo embedding, some native extensions)
- YAML/JSON - Configuration, Docker Compose, testing fixtures

## Runtime

- Python 3.12-slim (Docker production runtime) in multi-stage build
- Node.js via Bun 1.x (frontend build and testing)
- Gunicorn + Uvicorn (ASGI application servers)
- `uv` (Python) - Primary package manager for dependency resolution and caching
- `pip` (Python) - Fallback, vendored wheels for offline installation
- Bun (JavaScript/Node) - Frontend package and test runner
- npm/yarn compatible (bun.lockb lockfile)

## Frameworks

- FastAPI 0.108+ - REST API server with Pydantic v2 validation
- Pydantic v2 - Type validation, settings management
- LightRAG 1.5.4 (fork with Cozo plugin) - Base RAG engine (v1 only, v2.0 will decompose)
- React 19.2+ - Component framework
- React Router 7.x - Client-side routing
- Vite 8.0+ - ESM build tool (faster than webpack)
- TailwindCSS 4.3 - Utility-first styling
- Radix UI - Accessible component primitives
- Sigma.js 3.0 / react-sigma 5.0 - Graph visualization
- pytest 8.4.2+ - Python unit/integration tests
- pytest-asyncio 1.2+ - Async test support
- Bun test - JavaScript/TypeScript tests
- pre-commit - Git hook framework for linting/formatting
- Docker (multi-stage) - Production image generation with layer caching
- Makefile - Development task automation
- setuptools 64+ - Python packaging/distribution
- uv sync - Locked dependency installation (uv.lock)

## Key Dependencies

- `pycozo[embedded]` 0.7.6 - Embedded graph database (RocksDB, MPL-2.0 copyleft, file-level weak)
- `faiss-cpu` 1.7.0-2.0 - Vector similarity search (exact IndexFlatIP cosine, no GPU required)
- `nano-vectordb` - Lightweight fallback vector store
- `networkx` - Graph algorithms (default in v1 for quick-start, replaced by Cozo in production)
- `openai` 2.0-3.0 - OpenAI API client
- `anthropic` 0.18-1.0 - Claude/Anthropic API
- `google-genai` 1.0-3.0 - Google Gemini API
- `ollama` 0.1-1.0 - Local LLM integration
- `voyageai` 0.2-1.0 - Voyage AI embeddings
- `llama-index` 0.14+ - LLaMA Index framework (optional)
- `asyncpg` 0.31-1.0 - PostgreSQL async driver
- `pgvector` 0.4-1.0 - PostgreSQL vector extension
- `pymongo` 4.0-5.0 - MongoDB/Atlas integration
- `pymilvus` 2.6.2-4.0 - Milvus vector database
- `qdrant-client` 1.11-2.0 - Qdrant vector database
- `redis` 5.0-9.0 - Redis cache/KV store
- `neo4j` 5.0-7.0 - Neo4j graph database
- `opensearch-py` 3.0-4.0 - OpenSearch/Elasticsearch compatibility
- `pypdf` 6.1+ - PDF text/metadata extraction
- `python-docx` 0.8-2.0 - DOCX file parsing
- `python-pptx` 0.6-2.0 - PPTX file parsing
- `openpyxl` 3.0-4.0 - XLSX spreadsheet parsing
- `cairosvg` 2.5-3.0 - SVG to PNG rasterization
- `defusedxml` 0.7-1.0 - Safe XML parsing (XXE mitigation)
- `langchain-text-splitters` 0.3-2.0 - Text chunking (recursive, semantic, token-based)
- `langchain-experimental` 0.3.2+ - SemanticChunker with min_chunk_size support
- `aiohttp` - Async HTTP client/server
- `tenacity` - Retry logic with exponential backoff
- `tiktoken` - GPT tokenizer (pre-cached in Docker)
- `pydantic-settings` - Environment variable binding (part of Pydantic v2)
- `python-dotenv` - .env file loading
- `PyYAML` 6.0-7.0 - YAML parsing
- `json_repair` - Fault-tolerant JSON parsing
- `bcrypt` 4.0+ - Password hashing
- `PyJWT` 2.8-3.0 - JWT token handling
- `python-jose` - JOSE/JWT with cryptography backend
- `xlsxwriter` 3.1+ - XLSX generation
- `pycryptodome` 3.0-4.0 - PDF encryption support
- `pipmaster` - Package management utilities
- `langfuse` 3.8.1+ - LLM trace/eval platform (optional)
- `aioboto3` 12.0-16.0 - AWS S3/Bedrock async (optional)

## Configuration

- `.env` file per deployment (host/compose)
- Environment variables override all defaults
- Settings sourced via Pydantic ConfigDict from `LIGHTRAG_*`, `LLM_*`, `EMBEDDING_*`, provider-specific prefixes
- API key configuration: `X-API-Key` header, `TOKEN_SECRET` (JWT), `AUTH_ACCOUNTS` (bcrypt hashes)
- `pyproject.toml` - Python project metadata, dependencies, entry points, tool config (pytest, ruff, setuptools)
- `uv.lock` - Locked dependency versions (reproducible installs)
- `Dockerfile` - Multi-stage: frontend build (Bun) → Python build (uv + Rust) → runtime (Python 3.12-slim)
- `.pre-commit-config.yaml` - Git hooks for linting/formatting
- `setup.py` - Fallback setuptools entry point
- `vite.config.ts` - Frontend build config (React plugin, Tailwind, asset optimization)
- `tsconfig.json` - TypeScript compiler settings
- `eslint.config.js` - JavaScript linting rules
- `.prettierrc` - Code formatting (Prettier)
- `tailwind.config.ts` - Tailwind theme/plugin customization
- `env.example` - Template with all configurable variables documented (~1100 lines)
- `env.docker-compose-full` - Full Docker Compose preset with all services
- `.env.development` (frontend) - Vite dev server configuration
- `env.aoi.example` - AOI-specific configuration template

## Platform Requirements

- Python 3.10+ with pip/uv
- Node.js 18+ or Bun 1.0+
- Docker (for containerized testing/deployment)
- Git (for pre-commit hooks)
- Rust toolchain (optional, for building native wheels from source)
- Docker container runtime OR bare Python 3.12+ environment
- PostgreSQL 12+ (if using POSTGRES_* storage) with pgvector 0.7.0+ extension
- Redis 5.0+ (if using Redis storage)
- MongoDB 4.0+ or Atlas (if using MongoDB storage)
- Neo4j 5.0+ (if using Neo4j storage)
- Milvus 2.3+ (if using Milvus storage)
- Qdrant (if using Qdrant storage)
- OpenSearch 2.0+ (if using OpenSearch storage)
- MinIO or S3-compatible storage (Milvus dependency, if used)
- vLLM or SGLang (optional, for local embedding/reranking)
- MinerU or Docling service (optional, for async document parsing)
- Reverse proxy (nginx, Caddy) for multi-instance deployment behind API prefix
- Single machine with Python 3.12, 4GB RAM (testing)
- 8GB RAM + SSD recommended for production with embedded Cozo + Nano VectorDB
- GPU optional (Faiss CPU-only by default; can swap for GPU if needed)

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

## Naming Patterns

- Lowercase with underscores: `addon_params.py`, `base.py`, `chunk_schema.py`, `constants.py`, `exceptions.py`
- Pattern: `module_name.py` for single logical units
- Test files: `test_*.py` or `*_test.py` (test directory structure mirrors source)
- Component files: PascalCase without spaces
- Example: `lightrag_webui/` subdirectories and component files follow consistent naming
- Test files: `.test.tsx`, `.test.ts` (co-located with source)
- camelCase for private/internal: `_run_sync()`, `_owning_loop`
- snake_case for public: `insert()`, `query()`, `delete_by_entity()`, `initialize_rag()`
- Async variants prefixed with `a`: `ainsert()`, `aquery()` (matching sync alternatives)
- Test functions: `test_*()` pattern (e.g., `test_run_sync_runs_coroutine_when_no_loop_running()`)
- snake_case throughout: `owning_loop`, `test_artifacts`, `run_integration_tests`
- Private/internal: leading underscore `_hermetic_mineru_env`
- Boolean fixtures/flags: descriptive names like `keep_test_artifacts`, `stress_test_mode`, `parallel_workers`
- PascalCase: `LightRAG`, `RuntimeError`, `ThreadPoolExecutor`
- Exception classes suffix with `Error` or `Exception`: `RuntimeError`
- Interfaces and Types: PascalCase
- Enums: PascalCase
- Example from eslint config: React version `19.0` implies typed component props

## Code Style

- Tool: None explicitly configured (inferred from pyproject.toml defaults)
- Line length: Not specified in config
- Indent: Python default (4 spaces assumed)
- Convention: Follows PEP 8 style guide (observed from test structure)
- Tool: Prettier
- Config file: `v1/lightrag_webui/.prettierrc.json`
- Settings:
- Tool: ruff
- Config: `pyproject.toml` section `[tool.ruff]`
- Target version: `py310` (Python 3.10)
- Scope: Code quality and style checks (specific rules configured via ruff)
- Tool: ESLint (flat config format)
- Config file: `v1/lightrag_webui/eslint.config.js`
- Parser: TypeScript ESLint (`typescript-eslint`)
- Environment: Browser globals
- React version: 19.0
- Key rules:

## Import Organization

- Example from eslint.config.js shows imports grouped before re-export
- Python: Package-relative imports using `lightrag.*` namespace
- TypeScript: Inferred alias for `@` (common React pattern); verify in `tsconfig.json`
- Example: `from lightrag.lightrag import _run_sync`

## Error Handling

- Async context: Errors in event-loop validation are raised eagerly before coroutine creation
- Example from `test_sync_wrapper_guard.py`: `_run_sync()` raises `RuntimeError` with actionable messages pointing to async alternatives
- Pattern: Guard checks run *before* lazy factory invocation, preventing dangling un-awaited coroutines
- Async-safe: Use try/finally blocks to ensure cleanup in async context managers
- React context: Error boundaries implied by plugin configuration
- API patterns (inferred from FastAPI backend): HTTP error responses with clear status codes
- Guard against error states with early validation (same pattern as Python)

## Logging

- Assumed: `logging` module (standard library)
- Pattern: Used implicitly in test fixtures for environment setup messages
- No external log aggregation dependency in pyproject.toml
- Not explicitly configured in web UI config
- Browser console logging assumed (standard `console.*`)
- No structured logging dependency detected
- Tests log setup state via pytest fixtures (informational level)
- Example: `_hermetic_mineru_env` fixture documents why each env var is stripped (self-documenting monkeypatch)

## Comments

- Document non-obvious guard conditions
- Example from conftest: Multi-line comments explain why environment variables are stripped across tests (prevents test isolation leaks)
- Example from test_sync_wrapper_guard.py: Detailed module-level docstring explains event-loop synchronization rules and two misuse modes
- Pragma comments used for test coverage: `# pragma: no cover` marks code never reached on success path
- Not explicitly documented in config; assume React conventions
- JSDoc for component props inferred from React 19 setup
- Python: Module-level and class-level docstrings expected (seen in test files)
- TypeScript: Inferred JSDoc comments for function signatures and types

## Function Design

- Test functions: Focused on a single guard or behavior (e.g., `test_run_sync_raises_clear_error_inside_running_loop` tests one error condition)
- Helper functions: Named clearly to express intent (e.g., `side_body()` in gate scripts extracts structured sections)
- Anti-pattern: Avoid monolithic test functions; prefer one assertion per test or grouped assertions with clear section comments
- Async functions: Parameters passed through wrapper functions (`_run_sync(factory, sync_name="insert", async_name="ainsert", owning_loop=loop)`)
- Fixtures: Named to describe their role (`keep_test_artifacts`, `stress_test_mode`, `parallel_workers`)
- CLI option forwarding: Via `request.config.getoption()` with fallback to environment variables
- Async wrappers: Return same type as inner coroutine
- Test fixtures: Return boolean (mode flags) or integer (worker counts)
- Early validation: Functions return or raise early, no sentinel values for success (fail-fast principle)
- Components: Assume modular, single-responsibility pattern (inferred from plugin configuration for React Hooks)
- Functions: Leverage TypeScript for type safety instead of runtime checks

## Module Design

- Pattern: Package-level `__all__` declarations (assumed from structure)
- Example: `lightrag.lightrag` exports `_run_sync` for public use in wrappers
- Async/sync pairing: Public API exposes both sync and async variants
- ESLint rule: `react-refresh/only-export-components` enforced with warning level
- Pattern: React components are default exports or named exports
- Rule allows `allowConstantExport: true` for constants alongside components
- Not explicitly configured; assume standard pattern (index files re-export from subdirectories)
- Example inferred: `lightrag/api/webui/` likely has index.ts/index.js

<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

## System Overview

```text

```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| LightRAG facade | Main API, doc/query lifecycle | `v1/lightrag/lightrag.py` |
| Query orchestration | 4-stage pipeline execution | `v1/lightrag/operate.py` |
| Pipeline mixin | Async doc ingestion & status tracking | `v1/lightrag/pipeline.py` |
| Storage abstraction | Abstract base classes for pluggable backends | `v1/lightrag/base.py` |
| Graph storage factory | Runtime dispatch to correct KG backend | `v1/lightrag/kg/factory.py` |
| Cozo KG storage | Cozo (Datalog DB) graph backend | `v1/lightrag/kg/cozo_impl.py` |
| Other KG backends | Neo4j, PostgreSQL, MongoDB, etc. | `v1/lightrag/kg/*.py` |
| LLM bindings | Provider integrations (OpenAI, Gemini, Ollama, etc.) | `v1/lightrag/llm/*.py` |
| Chunker | Document segmentation (token, semantic, paragraph) | `v1/lightrag/chunker/*.py` |
| Parser | File format dispatch (native, external plugins) | `v1/lightrag/parser/*.py` |
| API server | FastAPI routes & request handling | `v1/lightrag/api/lightrag_server.py` |
| WebUI | React/TypeScript frontend | `v1/lightrag_webui/src/` |

## Pattern Overview

- **Storage agnosticism**: Graph/vector/KV storage interfaces (`BaseGraphStorage`, `BaseVectorStorage`, `BaseKVStorage`) allow runtime selection of 12+ implementations without code changes.
- **Late-binding dispatch**: `factory.py` routes storage creation at runtime based on env vars; no compile-time coupling to any backend.
- **4-stage query pipeline**: Operates in phases (keyword extraction → KG search → token control → context merging) enabling incremental result filtering and budget management.
- **Async-first orchestration**: `pipeline.py` uses `_PipelineMixin` with queues and worker pools for concurrent document processing.
- **Modular LLM layer**: Each provider (OpenAI, Gemini, Ollama, Anthropic, Bedrock, etc.) is a separate subclass; role-based config allows per-role LLM selection.
- **Pluggable chunkers**: Multiple chunking strategies (token-size, semantic-vector, paragraph-semantic) switchable per-namespace.
- **Dual query modes**: `kg_query()` (knowledge graph + entity/relation retrieval) vs `naive_query()` (pure vector search); `hybrid` mode combines both.

## Layers

- Purpose: Accept external requests (HTTP, Python function calls)
- Location: `v1/lightrag/api/`, `v1/examples/`
- Contains: FastAPI routes, CLI demos, Ollama API emulation
- Depends on: LightRAG facade
- Used by: Web clients, Python applications, third-party integrations
- Purpose: Coordinate document ingestion and query execution
- Location: `v1/lightrag/pipeline.py` (ingest), `v1/lightrag/operate.py` (query)
- Contains: Async pipelines, queue management, status tracking, 4-stage query
- Depends on: Storage abstractions, LLM layer, chunkers
- Used by: API layer, LightRAG facade
- Purpose: Define contracts for pluggable backends
- Location: `v1/lightrag/base.py`, `v1/lightrag/kg/factory.py`
- Contains: Base classes (`BaseGraphStorage`, `BaseVectorStorage`, `BaseKVStorage`), factory dispatch
- Depends on: None (pure interfaces)
- Used by: All storage implementations, orchestration layer
- Purpose: Concrete backend logic for 12+ data stores
- Location: `v1/lightrag/kg/*.py` (11 graph backends + 6 vector backends + KV stores)
- Contains: Database-specific queries, serialization, connection pooling
- Depends on: External DB SDKs, storage abstractions
- Used by: Storage abstraction factory
- Purpose: Integrate 12+ LLM providers and embedding models
- Location: `v1/lightrag/llm/*.py`, `v1/lightrag/llm_roles.py`
- Contains: Provider-specific clients, response parsing, caching, role-based config
- Depends on: External LLM SDKs, utilities
- Used by: Operate (query), pipeline (extraction/summarization)
- Purpose: Transform documents into retrievable chunks
- Location: `v1/lightrag/chunker/`, `v1/lightrag/parser/`
- Contains: Chunking algorithms, file format dispatch, external parser plugins
- Depends on: Tokenizer utilities
- Used by: Pipeline (ingest)

## Data Flow

### Primary Request Path (Query)

- If `only_need_context=True`: stop at step 8, return chunks
- If `only_need_prompt=True`: stop at step 8, return formatted prompt only
- If `stream=True`: yield chunks at step 9 via async generator

### Document Ingestion Path (Ingest)

### State Management

- **Document status**: Tracked in `DocStatusStorage` (JSON, Postgres, Mongo, Redis backend-selectable), records parse/analysis/insert progress per-document
- **Chunking state**: Metadata in `shared_storage` (per-namespace data structures in `v1/lightrag/kg/shared_storage.py`)
- **LLM cache**: Keyed by content hash (identity in `v1/lightrag/utils.py:get_llm_cache_identity()`), stored in same backend as vector DB, invalidation via `storage.index_done_callback()`
- **Keyed locks**: Per-entity/doc locking via `get_storage_keyed_lock()` to prevent concurrent writes to same entity

## Key Abstractions

- Purpose: Abstract graph query interface (entity neighborhood, relation paths, degree queries)
- Examples: `v1/lightrag/kg/neo4j_impl.py`, `v1/lightrag/kg/postgres_impl.py`, `v1/lightrag/kg/cozo_impl.py`
- Pattern: Subclass implements `query_relations()`, `query_entities_by_...()`, `upsert_entity()`, `delete_entity_by_source_id()`
- Purpose: Abstract vector embedding & similarity search (upsert, query, delete)
- Examples: `v1/lightrag/kg/milvus_impl.py`, `v1/lightrag/kg/qdrant_impl.py`, `v1/lightrag/kg/faiss_impl.py`
- Pattern: Subclass implements `upsert()`, `query()`, `delete_by_ids()`; embedding happens here or via `EmbeddingFunc` callback
- Purpose: Abstract key-value store (doc status, LLM cache, doc-chunk mappings)
- Examples: `v1/lightrag/kg/json_kv_impl.py`, `v1/lightrag/kg/postgres_impl.py`
- Pattern: Subclass implements `get()`, `set()`, `delete()`, optional `filter_by_source()` for batch deletes
- Purpose: Lifecycle container for a workspace + namespace combo (initialization, finalization, dropping)
- Examples: All `*Impl` classes inherit and implement `async initialize()`, `async drop()`
- Pattern: Factory creates per-namespace instances; cleanup happens on `index_done_callback()` (flush) and `finalize()` (shutdown)
- Purpose: Typed config object for query modes, token budgets, ranking, response format
- Examples: `mode: "hybrid"`, `top_k: 10`, `max_total_tokens: 4000`, `enable_rerank: True`
- Pattern: Passed from API to `kg_query()/naive_query()`, controls which stages execute and how
- Purpose: Per-role LLM configuration (separate models for extraction, summarization, chat)
- Examples: `v1/lightrag/llm_roles.py` defines extraction/summarization/chat roles with per-role provider + model selection
- Pattern: Query can specify `extraction_role`, `summarization_role`; LightRAG selects appropriate LLM + parameters

## Entry Points

- Location: `v1/lightrag/api/lightrag_server.py`
- Triggers: `python -m lightrag.api.run_with_gunicorn` (or `uvicorn lightrag.api.lightrag_server:app`)
- Responsibilities: FastAPI app setup, route registration (query, document, graph, Ollama API emulation), auth middleware, CORS, WebUI static serving
- Location: `v1/lightrag/lightrag.py:LightRAG` class
- Triggers: `rag = LightRAG(working_dir=..., llm_model_name=..., chunk_db_model_name=..., embed_model_name=...)`
- Responsibilities: Async context manager for RAG instance; `insert()`, `query()`, `delete()`, and utility methods; facade to pipeline & operate
- Location: `v1/examples/*.py`
- Triggers: `python v1/examples/lightrag_openai_demo.py`
- Responsibilities: Demonstrate various configurations (providers, chunkers, backends) in reproducible scripts
- Location: `v1/lightrag/tools/lightrag_visualizer/`
- Triggers: Interactive UI for graph visualization (NetworkX, Neo4j, OpenSearch backends supported)
- Responsibilities: Visual exploration of extracted entities and relations

## Architectural Constraints

- **Threading**: Single Python event loop (async/await). Internal concurrency via `asyncio.gather()`, `PriorityQueue` in pipeline. External I/O (API calls, DB ops) is awaitable; CPU-bound LLM tokenization uses `loop.run_in_executor()` to avoid blocking.
- **Global state**: `shared_storage` dict in `v1/lightrag/kg/shared_storage.py` holds per-namespace data (chunking metadata, keyed locks, doc status). Initialized per-namespace on first access.
- **Circular imports**: Parser plugins loaded late (in `load_third_party_parsers()`) to avoid circular dependency on external libs.
- **Storage mutability**: All storage backends are mutable during a session; consistency guaranteed by `index_done_callback()` flush semantics (except immediate-write backends like Neo4j which flush on each op).
- **Workspace isolation**: Multiple workspaces can coexist in same process (namespaced storage). Doc status & KG are separate per workspace; no cross-workspace queries by design.

## Anti-Patterns

### Hardcoded Backend Type

### Synchronous I/O in Async Code

### Prompt Injection in Direct Concatenation

## Error Handling

- **Extraction errors** (LLM, parser): Log, store in `doc_status.error_msg`, continue to next chunk. Partial knowledge graph is better than no ingest.
- **Query errors** (KG unavailable, vector DB timeout): Return empty context, LLM generates response from history alone; or raise `QueryException` with fallback prompt.
- **Parse errors** (malformed DOCX, PDF corruption): Mark doc `PARSE_FAILED` in status, do not proceed to analysis. User can retry after fixing file.
- **Pipeline aborts** (cancellation, internal error): Call `drop_pending_index_ops()` to discard buffered writes; mark doc status appropriately; re-enqueue on next run.

## Cross-Cutting Concerns

<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| spike-findings-rag-graph-vector-raw | Implementation blueprint from spike experiments. Requirements, proven patterns, and verified knowledge for the RAG modality-swap system model (Databasise/Sourcerer). Auto-loaded during implementation work. | `.claude/skills/spike-findings-rag-graph-vector-raw/SKILL.md` |
| spike-findings-melodyscribe | Implementation blueprint from the MelodyScribe spikes: Score I/O contract, one-pass runtime, model size and training. Auto-loaded during MelodyScribe implementation work. | `.claude/skills/spike-findings-melodyscribe/SKILL.md` |

- **Spike findings for MelodyScribe** (contract, runtime patterns, size curve, constraints, gotchas) → `Skill("spike-findings-melodyscribe")`
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
