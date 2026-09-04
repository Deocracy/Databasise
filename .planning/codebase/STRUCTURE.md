# Codebase Structure

**Analysis Date:** 2026-09-03

## Directory Layout

```
project-root/
├── databasise/                 # 2.0 Agnostic machine (D4 One Machine architecture)
│   ├── __init__.py             # Public entry point: run_wiring()
│   ├── namespaces.py           # Workspace/namespace management (TBD)
│   │
│   ├── validator/              # Wiring parse, validation, depth/blast-radius
│   │   ├── parse.py            # parse_wiring() — one-pass accumulating validator
│   │   ├── cycles.py           # Cycle detection (SCC-condensation)
│   │   ├── depth.py            # Effective depth (taint minimum)
│   │   ├── blast_radius.py     # Containment enforcement per depth tier
│   │   ├── execution_mode.py   # Placement (in-process, remote, etc.)
│   │   ├── errors.py           # Validation error codes (CODE_*)
│   │   └── __init__.py
│   │
│   ├── identity/               # Wiring canonicalisation, instance hashing
│   │   ├── canon.py            # Canonical wiring serialisation (SHA256)
│   │   ├── instance.py         # Instance resolution with SCC-based depth
│   │   ├── env.py              # Environment variable handling
│   │   └── __init__.py
│   │
│   ├── runner/                 # Execution scheduler, tracing
│   │   ├── scheduler.py        # TopologicalSorter, TaskGroup, per-node dispatch
│   │   ├── trace.py            # RunRecord, NodeRecord (honesty fields)
│   │   ├── budget.py           # Token budget enforcement (TBD)
│   │   ├── guards.py           # Guard checks (D-08 placement refusal, etc.)
│   │   └── __init__.py
│   │
│   ├── parts/                  # Part registry, schema, dispatch
│   │   ├── registry.py         # PartRegistry, component resolution
│   │   ├── schema.py           # Part, WiringNode, NodeKind (tagged sum), Effect
│   │   └── __init__.py
│   │
│   ├── parts_core/             # Reference & domain-specific parts
│   │   ├── __init__.py
│   │   ├── declared_only.py    # Declaration-only part (marker)
│   │   ├── fake_llm_caller.py  # Test stub LLM
│   │   ├── fake_retriever.py   # Test stub retriever
│   │   ├── fixpoint_body.py    # Fixed-point loop implementation
│   │   ├── passthrough.py      # Identity part (debugging)
│   │   │
│   │   └── lightrag/           # LightRAG-specific part implementations
│   │       ├── __init__.py
│   │       ├── assemble.py     # Assemble/combine results
│   │       ├── chunk_sel_kg.py # KG-based chunk selection
│   │       ├── chunk_vector.py # Vector-based chunk selection
│   │       ├── embedder_index.py # Embedding during indexing
│   │       ├── embedder_query.py # Embedding during query
│   │       ├── entity_hydrate_expand.py # Entity retrieval + expansion
│   │       ├── entity_lookup.py # Entity lookup in graph
│   │       ├── generate.py     # LLM response generation
│   │       ├── heading_backfill.py # Heading extraction/backfill
│   │       ├── join_roundrobin.py # Join/merge results (roundrobin)
│   │       ├── keywords.py     # Keyword extraction
│   │       ├── relation_hydrate_expand.py # Relation retrieval + expansion
│   │       ├── relation_lookup.py # Relation lookup in graph
│   │       ├── rerank.py       # Reranking retrieved chunks
│   │       └── truncator_token_budget.py # Token budget truncation
│   │
│   ├── stores/                 # Storage abstraction (pluggable backends)
│   │   ├── base.py             # StorageBase async lifecycle
│   │   ├── kv.py               # KeyValueStore (SQLite impl in tracer)
│   │   ├── vector.py           # VectorStore (pluggable, Faiss in v1)
│   │   ├── graph.py            # GraphStore (pluggable, Cozo in v1)
│   │   ├── blob.py             # BlobStore (pluggable)
│   │   ├── lexical.py          # LexicalStore (inverted index, TBD)
│   │   └── __init__.py
│   │
│   ├── wirings/                # Wiring resolution logic, structural kinds
│   │   ├── __init__.py
│   │   └── resolve.py          # Wiring resolve.py (fanout/join/fixpoint dispatch — TBD)
│   │
│   ├── clients/                # LLM/embedding client abstraction
│   │   ├── base.py             # LLMClient, EmbeddingClient base classes
│   │   ├── openai_compat.py    # OpenAI-compatible client
│   │   └── __init__.py
│   │
│   ├── registry_artifact/      # Component registry (namespace/name@version)
│   │   └── (JSON/YAML registry files TBD)
│   │
│   ├── evidence/               # Evidence tracking (T0..T3 tiers — TBD)
│   │   └── (Evidence models TBD)
│   │
│   ├── ledger/                 # Promotion ledger (version history — TBD)
│   │   └── (Ledger models TBD)
│   │
│   ├── parity/                 # Parity/versioning tooling
│   │   └── (Parity utilities TBD)
│   │
│   ├── tools/                  # CLI/utility scripts
│   │   └── (Admin tools TBD)
│   │
│   └── tests/                  # Unit & integration tests (mirrors source structure)
│       ├── conftest.py         # pytest fixtures, env validation
│       ├── clients/            # Client tests
│       ├── fixtures/           # Shared test data (wiring examples, etc.)
│       ├── identity/           # Identity resolver tests
│       ├── ledger/             # Ledger tests
│       ├── parity/             # Parity verification tests
│       ├── parts/              # Part dispatch, registry tests
│       ├── parts_core/         # Reference part tests
│       ├── registry_artifact/  # Registry tests
│       └── validator/          # Validator (parse, cycles, depth, blast_radius) tests
│
├── v1/                         # LightRAG monolithic engine (generation 1)
│   ├── lightrag/               # Core RAG library
│   │   ├── __init__.py
│   │   ├── lightrag.py         # LightRAG facade (init, query, insert, delete)
│   │   ├── base.py             # Storage abstractions (BaseGraphStorage, etc.)
│   │   ├── operate.py          # 4-stage query pipeline
│   │   ├── pipeline.py         # Document ingestion pipeline
│   │   ├── namespace.py        # Namespace (workspace) management
│   │   ├── chunk_schema.py     # Chunk data model
│   │   ├── constants.py        # Constants (timeouts, defaults)
│   │   ├── exceptions.py       # Custom exceptions
│   │   ├── addon_params.py     # Add-on configuration parameters
│   │   │
│   │   ├── api/                # FastAPI REST/Ollama emulation
│   │   │   ├── lightrag_server.py # Main FastAPI app
│   │   │   ├── routes.py       # Endpoints (/query, /document, /graph)
│   │   │   └── (Ollama compat endpoints)
│   │   │
│   │   ├── kg/                 # Knowledge graph backends (11 implementations)
│   │   │   ├── factory.py      # Runtime dispatch by env var
│   │   │   ├── neo4j_impl.py, postgres_impl.py, cozo_impl.py
│   │   │   ├── mongodb_impl.py, opensearch_impl.py
│   │   │   ├── milvus_impl.py, qdrant_impl.py, faiss_impl.py
│   │   │   ├── networkx_impl.py (dev), json_impl.py
│   │   │   ├── shared_storage.py # Global per-namespace data (anti-pattern D-11)
│   │   │   └── base.py         # BaseGraphStorage interface
│   │   │
│   │   ├── llm/                # LLM provider integrations
│   │   │   ├── openai_llm.py
│   │   │   ├── claude_llm.py
│   │   │   ├── gemini_llm.py
│   │   │   ├── ollama_llm.py
│   │   │   ├── bedrock_llm.py
│   │   │   ├── llama_index_llm.py
│   │   │   └── base.py         # BaseLLM interface
│   │   │
│   │   ├── embedding/          # Embedding model backends
│   │   │   ├── openai_embed.py
│   │   │   ├── voyage_embed.py
│   │   │   ├── ollama_embed.py
│   │   │   └── base.py
│   │   │
│   │   ├── chunker/            # Document chunking strategies
│   │   │   ├── token_chunker.py    # Token-size chunking
│   │   │   ├── semantic_chunker.py # Semantic/vector-based
│   │   │   ├── paragraph_chunker.py # Paragraph-aware
│   │   │   └── base.py
│   │   │
│   │   ├── parser/             # File format parsers
│   │   │   ├── pdf_parser.py
│   │   │   ├── docx_parser.py
│   │   │   ├── pptx_parser.py
│   │   │   ├── xlsx_parser.py
│   │   │   ├── txt_parser.py
│   │   │   └── base.py
│   │   │
│   │   └── utils.py            # Shared utilities
│   │
│   ├── lightrag_webui/         # React/TypeScript frontend
│   │   ├── src/
│   │   │   ├── components/     # React components
│   │   │   ├── pages/          # Page components (routing)
│   │   │   ├── hooks/          # Custom React hooks
│   │   │   ├── contexts/       # React Context providers
│   │   │   ├── services/       # API client services
│   │   │   ├── utils/          # Frontend utilities
│   │   │   └── App.tsx
│   │   ├── index.html          # Entry point
│   │   ├── vite.config.ts      # Vite build config
│   │   ├── tsconfig.json       # TypeScript config
│   │   ├── eslint.config.js    # ESLint rules
│   │   ├── .prettierrc          # Prettier formatting
│   │   ├── tailwind.config.ts  # Tailwind theming
│   │   └── package.json
│   │
│   ├── tests/                  # Tests (mirrors v1/lightrag structure)
│   │   ├── test_lightrag.py
│   │   ├── test_operate.py
│   │   ├── test_pipeline.py
│   │   └── kg/
│   │
│   ├── examples/               # Runnable demo scripts
│   │   ├── lightrag_openai_demo.py
│   │   ├── lightrag_claude_demo.py
│   │   ├── lightrag_ollama_demo.py
│   │   └── (other provider demos)
│   │
│   ├── prompts/                # LLM prompt templates
│   │   └── (*.json or *.yaml)
│   │
│   ├── scripts/                # Utility scripts (DB setup, etc.)
│   │   └── (scripts)
│   │
│   ├── reproduce/              # Reproducibility artifacts
│   │   └── (benchmark/parity traces)
│   │
│   ├── evaluation/             # Evaluation/benchmarking code
│   │   └── (eval scripts)
│   │
│   └── pyproject.toml          # Python project metadata, dependencies
│
├── docs/                       # Documentation
│   ├── system-model/           # CONTRACT.md, SELECTION.md, architecture specs
│   │   ├── CONTRACT.md         # Fitting contract (§0–§18, Appendices A–C)
│   │   ├── SELECTION.md        # Architecture decision record (D1–D14)
│   │   ├── SYSTEM-MODEL.md     # High-level overview
│   │   ├── ANATOMY.md          # Component anatomy/parts catalog
│   │   ├── PARTS.md            # Part specification (socket types, etc.)
│   │   ├── RIG.md              # Benchmarking rig (F1–F5)
│   │   ├── CATALOG.md          # Component catalog (namespace/name@version)
│   │   ├── D-VARIANTS/         # Architecture variant decision trees
│   │   │   └── SELECTION.md    # Frozen architecture choice (D4 One Machine)
│   │   └── wirings/            # Example wiring documents
│   │       └── (*.json)
│   │
│   └── (other markdown files)
│
├── .planning/                  # Planning artifacts (GSD workflow)
│   ├── codebase/              # Codebase map documents
│   │   ├── ARCHITECTURE.md    # (this file's sibling — architecture patterns)
│   │   ├── STRUCTURE.md       # (this file — directory layout & navigation)
│   │   ├── STACK.md           # (tech focus — languages, frameworks, deps)
│   │   ├── INTEGRATIONS.md    # (tech focus — external services, auth)
│   │   ├── CONVENTIONS.md     # (quality focus — naming, style, patterns)
│   │   ├── TESTING.md         # (quality focus — test framework, mocking)
│   │   └── CONCERNS.md        # (concerns focus — tech debt, bugs, risks)
│   │
│   ├── state.json             # Phase state (current phase, completed phases)
│   ├── milestone.lock         # Milestone lock file
│   └── (phase plans, phase summaries)
│
├── .claude/                    # Claude Code metadata
│   ├── CLAUDE.md              # Project-specific instructions
│   ├── skills/                # Available project skills
│   │   ├── spike-findings-rag-graph-vector-raw/
│   │   │   └── SKILL.md       # RAG/wiring blueprint from spike
│   │   └── (other skills)
│   │
│   └── worktrees/             # Git worktree state
│
├── reference/                  # Reference implementations / external specs
│   └── (external doc copies, RFCs, etc.)
│
├── pyproject.toml             # Root Python project (databasise package)
├── uv.lock                    # Locked dependencies (databasise + v1)
├── Dockerfile                 # Multi-stage Docker (v1 build)
├── docker-compose.yml         # Compose for dev/test
├── Makefile                   # Development tasks
├── .gitignore
├── .pre-commit-config.yaml    # Git hooks (linting, formatting)
├── .env.example               # Environment variables template
└── .github/                   # GitHub CI/workflows (if present)
```

## Directory Purposes

**databasise/**
- **Core**: Machine orchestration layer (2.0 agnostic system)
- **Contains**: Validator, identity resolver, scheduler, storage abstractions, part registry, LightRAG parts
- **Key entry point**: `databasise/__init__.py:run_wiring()`
- **Philosophy**: Schema-driven, modality-agnostic, deny-by-default security model

**databasise/validator/**
- **Purpose**: Parse wiring documents, validate schema, resolve components, compute containment
- **Key function**: `parse_wiring()` — accumulating (non-short-circuit) validator
- **Modules**: 
  - `parse.py` — main validation orchestrator
  - `cycles.py` — cycle detection (SCC-condensation)
  - `depth.py` — effective depth computation (taint minimum)
  - `blast_radius.py` — containment enforcement

**databasise/runner/**
- **Purpose**: Execute wiring nodes via scheduler, trace results
- **Key function**: `scheduler.run_wiring()` — topological sort + structured concurrency
- **Modules**:
  - `scheduler.py` — TaskGroup dispatch per ready batch
  - `trace.py` — RunRecord assembly (honesty fields)
  - `budget.py` — token budget enforcement (TBD)
  - `guards.py` — placement validation (D-08)

**databasise/parts_core/lightrag/**
- **Purpose**: RAG-specific part implementations
- **Scope**: 17 parts that compose RAG queries (keywords, embedders, rerankers, generators, entity/relation ops)
- **Pattern**: Each part is an async callable receiving NodeContext, returns outputs dict
- **Examples**: `embedder_query.py`, `entity_lookup.py`, `generate.py`, `rerank.py`

**databasise/stores/**
- **Purpose**: Pluggable storage backend abstractions
- **Philosophy**: Deny-by-default capability scoping (filtered by node's Effect declaration)
- **Abstractions**: KV, Vector, Graph, Blob stores
- **Current implementation**: SQLite for KV (tracer); v1/lightrag backends for Vector/Graph (Cozo, Faiss, Neo4j, etc.)

**v1/lightrag/**
- **Purpose**: Monolithic RAG engine (generation 1, pre-2.0)
- **Scope**: Complete RAG lifecycle (chunking, extraction, KG storage, vector embedding, querying)
- **Philosophy**: Tightly coupled to storage/LLM/embedding; served as reference for databasise parts
- **Integration with databasise**: Parts in `databasise/parts_core/lightrag/` delegate to v1's backends via store abstractions

**v1/lightrag/api/**
- **Purpose**: HTTP REST API and Ollama API emulation
- **Routes**: /query, /document, /graph, /chat
- **Entry point**: `lightrag_server.py` (FastAPI app)

**v1/lightrag/kg/**
- **Purpose**: Knowledge graph backend implementations (11 total)
- **Implementations**: Cozo, Neo4j, Postgres, MongoDB, Qdrant, Milvus, Faiss, NetworkX, OpenSearch, JSON, others
- **Factory**: `factory.py` dispatches to correct backend based on env vars
- **Anti-pattern**: `shared_storage.py` contains global per-namespace state (D-11 violation — replaced in databasise)

**v1/lightrag_webui/**
- **Purpose**: React/TypeScript web UI for RAG exploration
- **Components**: Graph visualization, query editor, document browser, results panel
- **Build**: Vite (ESM), TailwindCSS, Radix UI primitives, Sigma.js graph viz
- **Tests**: Bun test runner (TypeScript)

**docs/system-model/**
- **Purpose**: Contract, architecture, and specification documents
- **Key**: CONTRACT.md (§18 public seam), SELECTION.md (D4 decision), PARTS.md (component spec), RIG.md (benchmarking)
- **Traceability**: Every clause tagged with claim/trace tags and falsifier conditions

**.planning/codebase/**
- **Purpose**: Codebase map for future GSD phases
- **Scope**: ARCHITECTURE.md (patterns/layers), STRUCTURE.md (directory layout), STACK.md (tech), CONVENTIONS.md (style), TESTING.md (test patterns), CONCERNS.md (debt)

## Key File Locations

**Entry Points:**
- `databasise/__init__.py` — Public `run_wiring()` function (§18 seam)
- `v1/lightrag/api/lightrag_server.py` — FastAPI app (REST/Ollama)
- `v1/examples/*.py` — Standalone demo scripts

**Configuration:**
- `.env.example` — Environment variable template (~1100 lines, all configurable vars documented)
- `env.docker-compose-full` — Full Docker Compose preset with all services
- `env.aoi.example` — AOI-specific config template
- `pyproject.toml` — Python project metadata, dependencies, pytest/ruff config
- `v1/lightrag_webui/vite.config.ts` — Frontend build config (React plugin, Tailwind, asset optimization)
- `v1/lightrag_webui/tsconfig.json` — TypeScript compiler settings
- `v1/lightrag_webui/eslint.config.js` — JavaScript linting (flat config, React 19)
- `.prettierrc` — Code formatting config
- `.pre-commit-config.yaml` — Git hook framework (linting, formatting)

**Core Logic:**
- `databasise/validator/parse.py` — Wiring validation & component resolution
- `databasise/runner/scheduler.py` — Execution orchestration (TopologicalSorter, TaskGroup)
- `databasise/identity/canon.py` — Wiring canonicalisation, instance hashing
- `databasise/parts/registry.py` — Part dispatch & capability scoping
- `v1/lightrag/lightrag.py` — LightRAG facade (init, query, insert, delete)
- `v1/lightrag/operate.py` — 4-stage query pipeline (keyword → KG search → context → merge)
- `v1/lightrag/pipeline.py` — Document ingestion async pipeline
- `v1/lightrag/kg/factory.py` — Storage backend factory dispatch

**Testing:**
- `databasise/tests/conftest.py` — pytest fixtures, environment validation
- `databasise/tests/fixtures/` — Shared test data (wiring examples, schemas)
- `databasise/tests/parts/` — Part dispatch & registry tests
- `databasise/tests/validator/` — Validator (parse, cycles, depth, blast_radius) tests
- `v1/tests/test_lightrag.py` — Core RAG lifecycle tests
- `v1/lightrag_webui/` — Bun test runner (TypeScript component tests)

## Naming Conventions

**Files:**
- Python modules: lowercase with underscores (`parse.py`, `base.py`, `chunk_schema.py`, `constants.py`)
- Pattern: `module_name.py` for single logical units, backend-suffixed for implementations (`cozo_impl.py`, `neo4j_impl.py`)
- Test files: `test_*.py` or `*_test.py` (mirrors source structure)
- React components: PascalCase without spaces (e.g., `GraphVisualization.tsx`)

**Directories:**
- Lowercase with underscores: `databasise/`, `parts_core/`, `lightrag/`, `tests/`
- Package dirs mirror module scope: `databasise/validator/` groups all validation modules

**Functions & Variables:**
- **Python public**: snake_case (`insert()`, `query()`, `delete_by_entity()`, `run_wiring()`)
- **Python private/internal**: leading underscore (`_run_sync()`, `_owning_loop`)
- **Async variants**: prefixed `a` before snake_case (`ainsert()`, `aquery()` matching sync counterparts)
- **Boolean flags**: descriptive names (`keep_test_artifacts`, `determinism_setting`)
- **Classes**: PascalCase (`LightRAG`, `NodeContext`, `RuntimeError`)
- **Exceptions**: suffix with `Error` or `Exception` (`CODE_UNKNOWN_COMPONENT`, `DeclarationOnlyPartError`)
- **TypeScript**: camelCase (components, functions), PascalCase (component names, interfaces)

**Component names (Parts):**
- Format: `namespace/name@version` (e.g., `lightrag/entity-extractor@2.1.3`)
- Namespaces (fixed set): `core` (machine), `lightrag` (LightRAG port), `hipporag` (future), others per ported system
- Name segment: lowercase kebab-case (e.g., `chunker-token`, `embedder-bge-m3`)
- Version: semver (MAJOR = interface, MINOR/PATCH = internal only)

## Where to Add New Code

**New Part (RAG operation):**
- Implementation: `databasise/parts_core/lightrag/new_part.py`
- Register in: `databasise/parts/registry.py` (add to PartRegistry.register() call)
- Tests: `databasise/tests/parts_core/test_new_part.py`
- Example: New entity expansion part follows pattern in `entity_hydrate_expand.py`

**New Storage Backend:**
- Implementation: `v1/lightrag/kg/backend_impl.py` (e.g., `supabase_impl.py`)
- Factory dispatch: Add case to `v1/lightrag/kg/factory.py` keyed by env var
- Interface: Subclass `v1/lightrag/base.BaseGraphStorage` (or Vector, KV)
- Tests: `v1/tests/kg/test_backend_impl.py`

**New LLM Provider:**
- Implementation: `v1/lightrag/llm/provider_llm.py` (e.g., `cohere_llm.py`)
- Integration: Modify `v1/lightrag/lightrag.py` to select provider from config
- Tests: `v1/tests/llm/test_provider_llm.py`

**New Validator Check:**
- Implementation: New function in `databasise/validator/` module or extend existing (e.g., add case to `parse.py`)
- Call site: Ensure it's called from `parse_wiring()` before or after other checks per dependency order
- Pattern: Accumulate violations in `report`, never raise on first defect
- Tests: `databasise/tests/validator/test_check_name.py`

**Utility Helpers:**
- Shared Python: `v1/lightrag/utils.py`
- Frontend utilities: `v1/lightrag_webui/src/utils/`

**Frontend Components:**
- Location: `v1/lightrag_webui/src/components/`
- Co-located tests: `ComponentName.test.tsx` in same directory
- Naming: PascalCase with .tsx extension
- Import path alias: `@/components/ComponentName`

## Special Directories

**`.planning/`:**
- **Generated by**: GSD workflow (`/gsd-map-codebase`, `/gsd-plan-phase`, etc.)
- **Committed**: Yes (phase state, plans, summaries, codebase maps)
- **Regenerated**: `codebase/` documents refreshed by `/gsd-map-codebase`; phase files updated by phase commands

**`docs/system-model/`:**
- **Generated by**: Manual authorship (frozen design documents)
- **Committed**: Yes (contract, decision records, specifications)
- **Regenerated**: Never (frozen at version/phase boundaries)

**`v1/.parity_*`:**
- **Generated by**: Parity verification runs (evidence collection)
- **Committed**: No (git-ignored artifacts from benchmarking)
- **Regenerated**: Every parity run

**`databasise/tests/fixtures/`:**
- **Generated by**: Manual authorship (wiring examples, test data)
- **Committed**: Yes (test data)
- **Regenerated**: Never (fixtures are fixtures)

**`.venv/`, `node_modules/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`:**
- **Generated by**: pip/uv, npm/bun, pytest, ruff
- **Committed**: No (git-ignored)
- **Regenerated**: On dependency/environment setup

---

*Structure analysis: 2026-09-03*
