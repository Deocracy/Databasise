---
last_mapped_commit: 9160a53de8976defcfb11b138253156fd5050ecd
last_mapped_at: 2026-08-31
---
# Codebase Structure

**Analysis Date:** 2026-08-31

## Directory Layout

```
Databasise-2.0-fully-agnostic-system/
├── README.md                  # Repo overview, build ladder, system context
├── .planning/                 # Generated codebase maps (this dir)
├── .claude/                   # Claude Code local project config
├── .git/                      # Git repository metadata
├── docs/
│   └── system-model/          # v2.0 frozen architecture design (19 docs)
│       ├── SYSTEM-MODEL.md    # Entry point, build ladder, governance
│       ├── CONTRACT.md        # Fitting contract (20 sections)
│       ├── ANATOMY.md         # Machine anatomy, interfaces
│       ├── PARTS.md           # Three stress-test wirings
│       ├── CATALOG.md         # 72-system catalog + porting protocol
│       ├── RIG.md             # Comparison rig, versioning
│       ├── D-VARIANTS/        # Design variant reviews
│       ├── wirings/           # Example wiring JSON configs
│       └── *-check.sh         # 145-check gate scripts
├── reference/
│   └── hipporag2-2502.14802.pdf  # HippoRAG 2 paper
├── databasise/                # Agnostic machine (Phase 1, new)
│   ├── __init__.py            # Public entry point: run_wiring()
│   ├── README.md              # Package overview
│   ├── pyproject.toml         # Python 3.11+, 4 frozen dependencies
│   ├── namespaces.py          # Namespace isolation for later phases
│   │
│   ├── identity/              # Deterministic identity & canonicalisation (D-12)
│   │   ├── __init__.py
│   │   ├── canon.py           # JCS (RFC 8785) canonicalisation of wiring JSON
│   │   ├── env.py             # Environment-based identity derivation
│   │   └── instance.py        # Instance-hash generation
│   │
│   ├── parts/                 # Part registry & schema (D-13)
│   │   ├── __init__.py
│   │   ├── registry.py        # PartRegistry: dispatch to part implementations
│   │   └── schema.py          # NodeKind tagged sum, Effect vocabulary, WiringNode schema
│   │
│   ├── parts_core/            # Reference part implementations (proof of concept)
│   │   ├── __init__.py        # CapabilityScopedStores view
│   │   ├── declared_only.py   # Stub for declaration-only validation
│   │   ├── passthrough.py     # Identity transformation (input → output)
│   │   ├── fake_llm_caller.py # Stub LLM for rig testing
│   │   ├── fake_retriever.py  # Stub retriever for rig testing
│   │   └── fixpoint_body.py   # Fixed-point iteration for later phases
│   │
│   ├── validator/             # Wiring validation (pre-execution checks)
│   │   ├── parse.py           # Parse wiring JSON, schema validation
│   │   ├── cycles.py          # Cycle detection (Tarjan SCC)
│   │   ├── depth.py           # Effective depth derivation (opaque/evidence/stage)
│   │   ├── execution_mode.py  # Execution mode derivation (host placement)
│   │   ├── blast_radius.py    # Impact analysis for errors
│   │   └── errors.py          # Custom exception types
│   │
│   ├── runner/                # Wiring execution & tracing
│   │   ├── __init__.py
│   │   ├── scheduler.py       # TopologicalSorter + TaskGroup executor (D-09)
│   │   ├── trace.py           # RunRecord schema & tracing
│   │   ├── budget.py          # Token/time budget enforcement
│   │   └── guards.py          # Pre-flight validation guards
│   │
│   ├── stores/                # Machine-owned primitives (frozen, embedded)
│   │   ├── __init__.py
│   │   ├── base.py            # StoreLifecycle base class
│   │   ├── graph.py           # Cozo graph DB adapter (Datalog queries)
│   │   ├── vector.py          # Faiss vector DB adapter (cosine similarity)
│   │   ├── kv.py              # SQLite KV store adapter (blob + metadata)
│   │   ├── lexical.py         # Lexical search index
│   │   └── blob.py            # Binary blob storage interface
│   │
│   ├── ledger/                # Persistent ledger (later phases)
│   │   ├── __init__.py
│   │   └── ledger.py          # Run ledger persistence
│   │
│   ├── registry_artifact/     # Artifact indexing (later phases)
│   │   ├── __init__.py
│   │   ├── write_path.py      # Artifact path derivation
│   │   └── index.py           # Artifact index generation
│   │
│   ├── tools/                 # CLI utilities
│   │   ├── __init__.py
│   │   └── check_import_boundary.py # Verify no v1 imports (D-14 gate)
│   │
│   └── tests/                 # Comprehensive test suite (pytest)
│       ├── conftest.py        # Shared fixtures (store_root, rig_trace_schema)
│       ├── test_conftest_fixtures.py # Fixture validation
│       ├── test_tracer_end_to_end.py # Full run_wiring() path
│       ├── test_embed_startup.py     # Embedding initialization
│       ├── test_import_boundary.py   # D-14 boundary check (no v1 imports)
│       ├── test_phase_success_criteria.py # Phase 1 success gates
│       ├── fixtures/          # Test data
│       ├── identity/          # identity/ module tests
│       ├── parts/             # parts/ module tests
│       │   └── test_reference_parts.py # Reference part behavior
│       ├── validator/         # validator/ module tests
│       ├── runner/            # runner/ module tests
│       │   ├── test_budget.py
│       │   └── test_run_record.py
│       ├── stores/            # stores/ module tests
│       ├── ledger/            # ledger/ module tests
│       └── registry_artifact/ # registry_artifact/ module tests
│
├── v1/                        # LightRAG v1 — active codebase (Databasise 1.0)
│   ├── .github/
│   │   ├── workflows/         # CI/CD pipelines
│   │   ├── ISSUE_TEMPLATE/    # PR/issue templates
│   │   └── dependabot.yml     # Dependency updates
│   ├── .clinerules/           # Code linting rules
│   ├── docker-compose.yml     # Local dev environment
│   ├── docker-compose-full.yml  # Full stack (all backends)
│   ├── Dockerfile             # Container image
│   ├── Makefile               # Build targets
│   ├── pyproject.toml         # Python packaging config
│   ├── README.md              # v1 entry point
│   ├── SECURITY.md            # Vulnerability reporting
│   │
│   ├── lightrag/              # Core engine (31 subdirs)
│   │   ├── __init__.py        # Public API exports: LightRAG, ROLES, RoleSpec
│   │   ├── lightrag.py        # Main LightRAG class, async context manager
│   │   ├── base.py            # Storage abstraction: BaseGraphStorage, BaseVectorStorage, BaseKVStorage
│   │   ├── operate.py         # 4-stage query pipeline, kg_query(), naive_query() (3800+ lines)
│   │   ├── pipeline.py        # Document ingestion orchestration, _PipelineMixin (2900+ lines)
│   │   │
│   │   ├── api/               # FastAPI server & routes
│   │   │   ├── lightrag_server.py   # FastAPI app setup, middleware, static files
│   │   │   ├── routers/       # Endpoint handlers
│   │   │   │   ├── query_routes.py  # POST /api/query, streaming logic
│   │   │   │   ├── document_routes.py # POST/DELETE /api/insert, /api/delete
│   │   │   │   ├── graph_routes.py  # GET/POST /api/graph/* endpoints
│   │   │   │   └── ollama_api.py    # Ollama API emulation
│   │   │   ├── auth.py        # JWT/basic auth, password hashing
│   │   │   ├── config.py      # Global args, uvicorn config
│   │   │   ├── static/        # SwaggerUI dist (excluded from repo)
│   │   │   └── utils_api.py   # Helper utils (auth, validation, splash)
│   │   │
│   │   ├── kg/                # Knowledge graph storage (11 backends + factories)
│   │   │   ├── factory.py     # Runtime dispatch BaseGraphStorage → implementation
│   │   │   ├── __init__.py    # Storage verification utils
│   │   │   ├── shared_storage.py # Namespace data, keyed locks, doc status holder
│   │   │   ├── cozo_impl.py   # Cozo (Datalog) graph backend (39KB, new Databasise plugin)
│   │   │   ├── neo4j_impl.py  # Neo4j graph backend
│   │   │   ├── postgres_impl.py # PostgreSQL graph backend (375KB, largest)
│   │   │   ├── mongo_impl.py  # MongoDB graph backend
│   │   │   ├── memgraph_impl.py # Memgraph graph backend
│   │   │   ├── opensearch_impl.py # OpenSearch graph backend
│   │   │   ├── redis_impl.py  # Redis graph backend
│   │   │   ├── networkx_impl.py # NetworkX (in-memory) graph backend
│   │   │   ├── milvus_impl.py # Milvus vector backend (131KB)
│   │   │   ├── qdrant_impl.py # Qdrant vector backend
│   │   │   ├── faiss_impl.py  # FAISS vector backend
│   │   │   ├── nano_vector_db_impl.py # Nano vector backend
│   │   │   ├── json_kv_impl.py # JSON file KV backend
│   │   │   ├── json_doc_status_impl.py # JSON file doc status backend
│   │   │   └── deprecated/    # Chroma (archived)
│   │   │
│   │   ├── llm/               # LLM provider integrations (18 files)
│   │   │   ├── openai.py      # OpenAI API
│   │   │   ├── azure_openai.py # Azure OpenAI
│   │   │   ├── gemini.py      # Google Gemini
│   │   │   ├── anthropic.py   # Anthropic Claude
│   │   │   ├── bedrock.py     # AWS Bedrock
│   │   │   ├── ollama.py      # Local Ollama
│   │   │   ├── llama_index_impl.py # LlamaIndex integration
│   │   │   ├── nvidia_openai.py # NVIDIA Nemotron
│   │   │   ├── hf.py          # Hugging Face Transformers
│   │   │   ├── lmdeploy.py    # LMDeploy
│   │   │   ├── lollms.py      # LoLLMs
│   │   │   ├── voyageai.py    # VoyageAI embeddings
│   │   │   ├── jina.py        # Jina embeddings
│   │   │   ├── zhipu.py       # Zhipu GLM
│   │   │   ├── binding_options.py # Asymmetric embedding config
│   │   │   ├── _vision_utils.py # Multimodal image handling
│   │   │   └── deprecated/
│   │   │
│   │   ├── llm_roles.py       # Role-based LLM config (extraction, summarization, chat)
│   │   ├── addon_params.py    # Observable addon parameters for configs
│   │   │
│   │   ├── chunker/           # Document chunking strategies (5 files)
│   │   │   ├── token_size.py  # Token-based chunking
│   │   │   ├── recursive_character.py # Recursive char split
│   │   │   ├── semantic_vector.py # Semantic embedding-based
│   │   │   ├── paragraph_semantic.py # Paragraph-aware semantic
│   │   │   └── __init__.py    # chunking_by_token_size() dispatch
│   │   │
│   │   ├── parser/            # Document format dispatch (17 files)
│   │   │   ├── routing.py     # Parser routing rules from config
│   │   │   ├── native_dispatch.py # Native parser selection
│   │   │   ├── registry.py    # Plugin registry
│   │   │   ├── plugins.py     # Third-party parser loader
│   │   │   ├── base.py        # AbstractParser interface
│   │   │   ├── native_base.py # Base native implementations
│   │   │   ├── cli.py         # Parser debug CLI
│   │   │   ├── noop.py        # No-op parser (for testing)
│   │   │   ├── external/      # External parser implementations
│   │   │   │   └── mineru/, docling/, legacy/  # Third-party lib integrations
│   │   │   ├── markdown/      # Markdown-specific parsing
│   │   │   ├── docx/          # DOCX parsing
│   │   │   └── legacy/        # Old parser versions (archived)
│   │   │
│   │   ├── sidecar/           # Auxiliary data processing (5 files)
│   │   │   ├── writer.py      # Chunk metadata writer
│   │   │   ├── backfill.py    # Missing doc-chunk backfiller
│   │   │   ├── ir.py          # Internal representation
│   │   │   └── placeholders.py # Dynamic placeholder system
│   │   │
│   │   ├── prompt.py          # LLM prompt templates (entity/relation extraction, QA, etc.)
│   │   ├── prompt_multimodal.py # Multimodal prompt variants
│   │   ├── rerank.py          # Cross-encoder reranker
│   │   ├── utils.py           # Utilities (tokenizer, embedding func, logging, hashing)
│   │   ├── utils_graph.py     # Graph utility functions
│   │   ├── utils_pipeline.py  # Pipeline utility functions
│   │   ├── types.py           # Type definitions (KnowledgeGraph, etc.)
│   │   ├── constants.py       # Default constants, env var names
│   │   ├── exceptions.py      # Custom exceptions
│   │   ├── namespace.py       # Namespace class for isolated workspaces
│   │   ├── chunk_schema.py    # Chunk schema, heading breadcrumb
│   │   ├── table_markup.py    # HTML table parsing utils
│   │   ├── multimodal_context.py # Multimodal content handling
│   │   ├── file_atomic.py     # Atomic file write wrapper
│   │   ├── evaluation/        # RAG quality evaluation (RAGAS integration)
│   │   ├── tools/             # Utility CLI tools
│   │   │   ├── rebuild_vdb.py # Rebuild vector DB index
│   │   │   ├── clean_llm_query_cache.py # LLM cache cleanup
│   │   │   ├── migrate_llm_cache.py # Cache migration
│   │   │   ├── check_initialization.py # Storage validation
│   │   │   └── lightrag_visualizer/ # Graph visualization UI
│   │   │
│   │   ├── storage_migrations.py # Schema upgrade logic
│   │   ├── _version.py        # Version string
│   │   └── .env.aoi.example   # Asymmetric embedding config example
│   │
│   ├── lightrag_webui/        # React/TypeScript frontend (TypeScript)
│   │   ├── src/
│   │   │   ├── App.tsx        # Root component
│   │   │   ├── AppRouter.tsx  # Route definitions
│   │   │   ├── api/           # API client
│   │   │   ├── components/    # React components (graph, query, upload, etc.)
│   │   │   ├── contexts/      # React contexts (state management)
│   │   │   ├── hooks/         # Custom React hooks
│   │   │   ├── services/      # Business logic services
│   │   │   ├── stores/        # State stores
│   │   │   ├── types/         # TypeScript types
│   │   │   ├── utils/         # Utility functions
│   │   │   ├── locales/       # i18n translations
│   │   │   ├── main.tsx       # Vite entry point
│   │   │   └── i18n.ts        # i18n config
│   │   ├── vite.config.ts     # Vite build config
│   │   ├── tailwind.config.js # Tailwind CSS config
│   │   ├── eslint.config.js   # ESLint config
│   │   └── package.json       # npm dependencies
│   │
│   ├── examples/              # Demo scripts (20 files)
│   │   ├── lightrag_openai_demo.py # OpenAI + LightRAG demo
│   │   ├── lightrag_gemini_demo.py # Gemini + LightRAG demo
│   │   ├── lightrag_ollama_demo.py # Ollama + LightRAG demo
│   │   ├── lightrag_azure_openai_demo.py # Azure OpenAI demo
│   │   ├── lightrag_openai_mongodb_graph_demo.py # MongoDB backend demo
│   │   ├── lightrag_openai_opensearch_graph_demo.py # OpenSearch backend demo
│   │   ├── milvus_kwargs_configuration_demo.py # Milvus config demo
│   │   ├── opensearch_storage_demo.py # OpenSearch demo
│   │   ├── rerank_example.py  # Reranking demo
│   │   ├── insert_custom_kg.py # Manual KG construction
│   │   ├── generate_query.py  # Query generation
│   │   ├── graph_visual_with_neo4j.py # Neo4j visualization
│   │   ├── lightrag_ag2_multiagent_demo.py # AG2 multi-agent integration
│   │   ├── lightrag_vllm_demo.py # vLLM inference demo
│   │   └── unofficial-sample/ # Community-contributed examples
│   │       ├── lightrag_bedrock_demo.py # AWS Bedrock
│   │       ├── lightrag_cloudflare_demo.py # Cloudflare Workers
│   │       ├── lightrag_hf_demo.py # Hugging Face
│   │       ├── lightrag_llamaindex_litellm_demo.py # LiteLLM
│   │       ├── lightrag_nvidia_demo.py # NVIDIA
│   │       └── ... (5 more)
│   │
│   ├── tests/                 # Comprehensive test suite (18 subdirs, 150+ test files)
│   │   ├── api/               # API endpoint tests
│   │   ├── chunker/           # Chunker tests
│   │   ├── extraction/        # Entity/relation extraction tests
│   │   ├── kg/                # Storage backend tests (co-located with impl)
│   │   ├── llm/               # LLM binding tests
│   │   ├── parser/            # Parser tests
│   │   ├── pipeline/          # Ingestion pipeline tests
│   │   ├── parity/            # Parity tests across backends
│   │   ├── sidecar/           # Sidecar utility tests
│   │   ├── evaluation/        # RAG evaluation tests
│   │   ├── setup/             # Interactive setup tests
│   │   ├── tools/             # CLI tool tests
│   │   ├── workspace/         # Workspace isolation tests
│   │   └── conftest.py        # pytest fixtures
│   │
│   ├── k8s-deploy/            # Kubernetes deployment (Helm chart + scripts)
│   │   ├── lightrag/          # Helm chart
│   │   │   ├── Chart.yaml     # Helm metadata
│   │   │   ├── values.yaml    # Default values
│   │   │   └── templates/     # Helm templates
│   │   ├── databases/         # Database installation scripts
│   │   │   ├── 00-config.sh   # Env setup
│   │   │   ├── 01-prepare.sh  # Prerequisites
│   │   │   ├── 02-install-database.sh # Install DBs (Neo4j, Postgres, MongoDB, etc.)
│   │   │   ├── 03-uninstall-database.sh # Cleanup
│   │   │   ├── install-kubeblocks.sh # KubeBlocks operator
│   │   │   └── {mongodb,postgresql,redis,elasticsearch,neo4j}/
│   │   ├── install_lightrag.sh # Helm install wrapper
│   │   └── uninstall_lightrag.sh # Helm uninstall
│   │
│   ├── docs/                  # v1 documentation (24 markdown files)
│   │   ├── LightRAG-API-Server.md # API server guide
│   │   ├── FileProcessingPipeline.md # Doc ingestion details
│   │   ├── ProgramingWithCore.md # Developer guide
│   │   ├── DockerDeployment.md # Docker setup
│   │   ├── MultiSiteDeployment.md # Multi-region setup
│   │   ├── OfflineDeployment.md # Air-gapped deployment
│   │   ├── MilvusConfigurationGuide.md # Milvus tuning
│   │   ├── InteractiveSetup.md # Interactive setup CLI
│   │   ├── ParagraphSemanticChunking-*.md # Semantic chunking docs
│   │   ├── AsymmetricEmbedding.md # Asymmetric embedding config
│   │   ├── FrontendBuildGuide.md # WebUI build instructions
│   │   └── ... (10 more)
│   │
│   ├── reproduce/             # Reproducible steps (7 Python scripts)
│   │   ├── Step_0.py          # Basic setup
│   │   ├── Step_1.py          # Insert documents
│   │   ├── Step_2.py          # Compute metrics
│   │   ├── Step_3.py          # Query & evaluation
│   │   └── ...
│   │
│   ├── scripts/               # Build & release scripts
│   │   ├── setup/             # Interactive setup templates
│   │   │   ├── setup.sh       # Main setup runner
│   │   │   └── lib/           # Shell function library
│   │   ├── release/           # Release version management
│   │   └── test.sh            # Test runner
│   │
│   ├── prompts/               # Prompt template overrides
│   │   ├── UserCustomizePrompts.md # Customization guide
│   │   └── samples/           # Example prompts
│   │
│   └── README*.md             # v1 README (EN, ZH, JA)
```

## Directory Purposes

**Root level:**

- `.planning/codebase/`: Generated analysis documents (ARCHITECTURE.md, STRUCTURE.md, etc.)
- `README.md`: Repo overview, build ladder, system context (Databasise 1.0 vs agnostic machine)
- `docs/system-model/`: v2.0 frozen design (19 docs, read-only reference for Phase 1)
- `reference/`: External papers & reference implementations
- `databasise/`: Agnostic machine (Phase 1 deliverable, independent package)
- `v1/`: Active codebase (LightRAG v1.5.4 + Cozo plugin + Databasise refinements)

**databasise/ (agnostic machine):**

- Core: `__init__.py` (run_wiring entry), `namespaces.py` (workspace isolation for later phases)
- Validation: `validator/` (parse, cycles, depth, execution_mode, blast_radius, errors)
- Execution: `runner/` (scheduler, trace, budget, guards)
- Components: `parts/` (registry, schema), `parts_core/` (reference parts: passthrough, fake LLM caller, etc.)
- Primitives: `stores/` (Cozo graph, Faiss vector, SQLite KV, lexical index)
- Identity: `identity/` (JCS canonicalisation, config_hash, instance_hash)
- Persistence: `ledger/` (run ledger), `registry_artifact/` (artifact indexing)
- Testing: `tests/` (end-to-end, fixtures, conftest, module-specific tests)

**v1/lightrag/ (core engine):**

- Query execution: `operate.py` (4-stage pipeline), `lightrag.py` (facade)
- Storage: `base.py` (interfaces), `kg/` (11 backends), pluggable via factory
- LLM: `llm/` (18 provider integrations), role-based config in `llm_roles.py`
- Ingestion: `pipeline.py` (async orchestration), `parser/` (format dispatch), `chunker/` (segmentation strategies)
- API: `api/` (FastAPI server, auth, routes)
- Utilities: `utils.py` (tokenizer, embedding, logging), `prompt.py` (templates), `rerank.py` (ranking)

**v1/lightrag_webui/ (frontend):**

- React/TypeScript single-page app for query, graph visualization, document upload
- Communicates with API server over HTTP

**v1/examples/ & v1/reproduce/:**

- Standalone Python scripts demonstrating LightRAG usage
- Each example shows different LLM provider + storage backend combo
- `reproduce/` steps are reproducible parity tests

**v1/tests/ (150+ test files):**

- Co-located with implementations (e.g., `tests/kg/neo4j_impl/` tests `lightrag/kg/neo4j_impl.py`)
- Comprehensive: unit tests, integration tests, parity tests, regression tests
- CI runs all tests on each commit

**v1/k8s-deploy/ & docs/:**

- Production deployment guides (Docker, K8s, Helm)
- Configuration for all 11+ backends

## Key File Locations

### Databasise Machine

**Entry Points:**

- Wiring executor: `databasise/__init__.py:run_wiring()` — parse, validate, execute, trace one wiring
- Scheduler: `databasise/runner/scheduler.py:run_wiring()` — lower-level scheduler access for advanced use
- Part registry: `databasise/parts/registry.py:PartRegistry` — register custom modality parts (future phases)

**Configuration & Schema:**

- Wiring schema: `databasise/parts/schema.py` (NodeKind tagged sum, Effect vocabulary, WiringNode)
- Part implementation: `databasise/parts/registry.py` (Part class, dispatch logic)
- Validation config: `databasise/validator/parse.py` (pydantic schemas)

**Core Logic:**

- Wiring parsing: `databasise/validator/parse.py` (schema validation)
- Cycle detection: `databasise/validator/cycles.py` (Tarjan SCC algorithm)
- Depth derivation: `databasise/validator/depth.py` (opaque/evidence/stage classification)
- Execution scheduling: `databasise/runner/scheduler.py` (topological sort + TaskGroup dispatch)
- Run tracing: `databasise/runner/trace.py` (RunRecord schema, per-node timestamps)

**Storage Primitives:**

- Graph DB: `databasise/stores/graph.py` (Cozo adapter, Datalog queries)
- Vector DB: `databasise/stores/vector.py` (Faiss adapter, cosine similarity)
- KV store: `databasise/stores/kv.py` (SQLite adapter, blob + metadata)
- Lexical index: `databasise/stores/lexical.py` (search functionality)

**Testing:**

- Fixtures: `databasise/tests/conftest.py` (store_root, rig_trace_schema, assert_valid_trace)
- End-to-end: `databasise/tests/test_tracer_end_to_end.py` (full run_wiring() path)
- Boundary check: `databasise/tests/test_import_boundary.py` (verify no v1 imports — D-14 gate)
- Success criteria: `databasise/tests/test_phase_success_criteria.py` (Phase 1 gates)

### LightRAG v1

**Entry Points:**

- API server: `v1/lightrag/api/lightrag_server.py`
- Python library: `v1/lightrag/lightrag.py` (main `LightRAG` class)
- CLI examples: `v1/examples/*.py`
- Interactive setup: `v1/scripts/setup/setup.sh`

**Configuration:**

- Environment vars: `.env` (not in repo, use `.env.example` template)
- LLM role config: `v1/lightrag/llm_roles.py`, `v1/lightrag/addon_params.py`
- Prompt templates: `v1/lightrag/prompt.py`, `v1/lightrag/prompt_multimodal.py`
- Constants: `v1/lightrag/constants.py`
- Parser routing: `v1/lightrag/parser/routing.py`

**Core Logic:**

- Query pipeline: `v1/lightrag/operate.py` (3800+ lines, 4 stages)
- Ingestion pipeline: `v1/lightrag/pipeline.py` (2900+ lines, async workers)
- Storage abstraction: `v1/lightrag/base.py`, `v1/lightrag/kg/factory.py`
- LLM integrations: `v1/lightrag/llm/*.py` (18 providers)

**Testing:**

- Fixtures & setup: `v1/tests/conftest.py`
- API tests: `v1/tests/api/routes/*.py`
- Storage tests: `v1/tests/kg/` (matches backends in `kg/`)
- Parity tests: `v1/tests/parity/` (cross-backend consistency)

## Naming Conventions

### Databasise Machine

**Files:**

- Core modules: snake_case (e.g., `scheduler.py`, `trace.py`, `depth.py`)
- Adapter implementations: `{storage_type}.py` (e.g., `graph.py`, `vector.py`, `kv.py`)
- Test files: `test_*.py` (e.g., `test_tracer_end_to_end.py`)

**Directories:**

- Functional subsystems: lowercase (e.g., `validator/`, `runner/`, `stores/`)
- Module groupings: plural nouns (e.g., `parts/`, `parts_core/`, `tests/`)

**Classes:**

- Base classes: `{Concept}Lifecycle` or `{Concept}Base` (e.g., `StoreLifecycle`)
- Implementations: `{Backend}{Concept}Store` (e.g., `CozoGraphStore`, `FaissVectorStore`)
- Schemas: `{Concept}` or `{Concept}Schema` (e.g., `WiringNode`, `RunRecord`, `Part`)
- Exceptions: `{Issue}Error` or `{Issue}Exception` (e.g., `DeclarationOnlyPartError`, `PlacementError`)

**Functions & Methods:**

- Async entry points: `run_*` (e.g., `run_wiring()`)
- Validation: `validate_*` or `check_*` (e.g., `validate_wiring()`)
- Dispatch: `dispatch()` or `resolve_*` (e.g., `dispatch()`, `resolve_identities()`)
- Derivation: `derive_*` (e.g., `derive_execution_mode()`, `derive_depth()`)

### LightRAG v1

**Files:**

- Core modules: snake_case (e.g., `operate.py`, `llm_roles.py`)
- Implementation classes: `{Storage|LLM|Parser}*Impl` (e.g., `cozo_impl.py`, `openai.py`)
- Test files: `test_*.py` (e.g., `test_entity_extraction.py`)
- Examples: descriptive names (e.g., `lightrag_openai_demo.py`)

**Directories:**

- Core subsystems: plural nouns (e.g., `llm/`, `chunker/`, `parser/`)
- Implementation groups: named by backend (e.g., `kg/neo4j_impl/` tests, `llm/openai.py` impl)
- Test dirs: mirror source structure (e.g., `tests/kg/`, `tests/llm/`)

**Classes:**

- Storage: `Base{Graph|Vector|KV}Storage`, `{Backend}Storage` (e.g., `Neo4jGraphStorage`)
- LLM: `{Provider}LLM` (e.g., `OpenAILLM`, `GeminiLLM`)
- Parsers: `{Format}Parser` (e.g., `MarkdownParser`, `DocxParser`)
- Chunkers: `{Strategy}Chunker` (e.g., `SemanticVectorChunker`)

**Functions:**

- Query stages: `get_keywords_from_query()`, `_build_query_context()`, `_perform_kg_search()`, `_apply_token_truncation()`
- Utilities: `compute_mdhash_id()`, `sanitize_text_for_encoding()`, `truncate_list_by_token_size()`
- Async operations: prefix with `async` in function name or comment

## Where to Add New Code

### Databasise Machine (Phase 1)

**New Reference Part (for testing):**

1. Implementation: `databasise/parts_core/{part_name}.py` — async def body(ctx: NodeContext) -> dict
2. Tests: `databasise/tests/parts/test_{part_name}.py`
3. Registration: Add to `databasise/parts/registry.py:REFERENCE_PARTS` dict

**New Store Adapter (for later phases):**

1. Implementation: `databasise/stores/{store_type}.py` — subclass `StoreLifecycle`
2. Tests: `databasise/tests/stores/test_{store_type}.py`
3. Exposure: Add to `databasise/stores/__init__.py:StoreRegistry`

**New Validator Module (for enhancement):**

1. Implementation: `databasise/validator/{check_name}.py` — define validation function
2. Tests: `databasise/tests/validator/test_{check_name}.py`
3. Integration: Call from `databasise/validator/parse.py:parse_wiring()` during validation flow

### LightRAG v1

**New LLM Provider:**

1. Implementation: `v1/lightrag/llm/{provider_name}.py` — subclass `BaseEmbeddingFunc` and/or `BaseLLM`
2. Tests: `v1/tests/llm/{provider_name}_impl/test_*.py`
3. Export: Add to `v1/lightrag/llm/__init__.py`
4. Example: `v1/examples/lightrag_{provider_name}_demo.py`

**New Graph Storage Backend:**

1. Implementation: `v1/lightrag/kg/{backend_name}_impl.py` — subclass `BaseGraphStorage`
2. Tests: `v1/tests/kg/{backend_name}_impl/test_*.py`
3. Registration: Add case in `v1/lightrag/kg/factory.py` dispatch logic
4. Documentation: `v1/docs/{Backend}Guide.md`
5. Example: `v1/examples/lightrag_openai_{backend_name}_demo.py`

**New Chunker:**

1. Implementation: `v1/lightrag/chunker/{strategy_name}.py` — subclass or define `async def chunk()` function
2. Export: Add to `v1/lightrag/chunker/__init__.py`
3. Tests: `v1/tests/chunker/test_{strategy_name}.py`
4. Configuration: Add to `DEFAULT_CHUNKER` logic in `lightrag.py`

**New Query Mode:**

1. Function: `v1/lightrag/operate.py` — new `async def {mode}_query()` following 4-stage pattern
2. Dispatch: Add case in `LightRAG.query()` method
3. Tests: `v1/tests/pipeline/test_query_{mode}.py`
4. Documentation: Update `v1/docs/LightRAG-API-Server.md`

**Utility Helper:**

1. If domain-agnostic: `v1/lightrag/utils.py`
2. If query-specific: `v1/lightrag/utils_graph.py`
3. If pipeline-specific: `v1/lightrag/utils_pipeline.py`
4. Test: co-located `test_utils*.py`

**Prompt/Template:**

1. Add to `v1/lightrag/prompt.py` or `v1/lightrag/prompt_multimodal.py`
2. Register in `PROMPTS` dict with unique key
3. Reference from `operate.py` via key lookup (avoid string concatenation)
4. Override via env var: document in `v1/prompts/UserCustomizePrompts.md`

## Special Directories

### Databasise Machine

**databasise/.env (not in repo):**

- Purpose: Development environment (future phases; Phase 1 uses no env config)
- Generated: No (template not present in Phase 1)
- Committed: No

**databasise/tests/fixtures/:**

- Purpose: Test data (wiring examples, schema samples)
- Generated: No (hand-written)
- Committed: Yes

**databasise/.codebase-memory/ (optional):**

- Purpose: Compressed codebase-memory graph artifact (if persistence enabled)
- Generated: Yes (by codebase-memory-mcp)
- Committed: Optional (for team knowledge sharing)

### LightRAG v1

**v1/lightrag/api/static/:**

- Purpose: SwaggerUI dist (excluded from repo, built at deploy time)
- Generated: By `npm install && npm build` in vite.config.ts
- Committed: No (added to `.gitignore`; served at runtime from `lightrag/api/static/`)

**v1/tests/conftest.py:**

- Purpose: Shared pytest fixtures (storage instances, mocked LLMs, test data)
- Generated: No (hand-written, versioned)
- Scope: Conftest fixtures available to all test files; fixtures in specific test subdir conftest override

**v1/.codebase-memory/:**

- Purpose: Compressed codebase-memory graph artifact (if persistence enabled)
- Generated: Yes (by codebase-memory-mcp)
- Committed: Optional (for team knowledge sharing, not required)

**v1/lightrag/tools/lightrag_visualizer/:**

- Purpose: Interactive graph visualization UI
- Generated: No (hand-written, includes HTML + CSS + JS)
- Deployed: Standalone or embedded in webui

---

*Structure analysis: 2026-08-31*
