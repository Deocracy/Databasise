---
last_mapped_commit: 9160a53de8976defcfb11b138253156fd5050ecd
last_mapped_at: 2026-08-31
---
# Technology Stack

**Analysis Date:** 2026-08-31

## Languages

**Primary:**

- Python 3.10+ - Core RAG engine, API server, document processing, embeddings
- Python 3.11+ - Databasise 2.0 agnostic machine (runner uses `asyncio.TaskGroup`)
- TypeScript/React 19 - Web UI frontend with graph visualization
- JavaScript - Frontend build tooling (Vite, ESLint, Prettier)

**Secondary:**

- Rust - Build dependencies (Faiss, Cozo embedding, some native extensions)
- YAML/JSON - Configuration, Docker Compose, testing fixtures

## Runtime

**Environment:**

- Python 3.12-slim (Docker production runtime) in multi-stage build
- Python 3.11+ (Databasise agnostic machine, separate from v1)
- Node.js via Bun 1.x (frontend build and testing)
- Gunicorn + Uvicorn (ASGI application servers)

**Package Manager:**

- `uv` (Python) - Primary package manager for dependency resolution and caching
- `pip` (Python) - Fallback, vendored wheels for offline installation
- Bun (JavaScript/Node) - Frontend package and test runner
- npm/yarn compatible (bun.lockb lockfile)

## Frameworks

**Core (v1 — LightRAG):**

- FastAPI 0.108+ - REST API server with Pydantic v2 validation
- Pydantic v2 - Type validation, settings management
- LightRAG 1.5.4 (fork with Cozo plugin) - Base RAG engine (v1 only, v2.0 will decompose)

**Agnostic Machine (Databasise 2.0 — CONTRACT.md §8-18):**

- `asyncio.TaskGroup` (stdlib, Python 3.11+) - Async task scheduling in runner
- `graphlib.TopologicalSorter` (stdlib, Python 3.9+) - Dependency ordering for component execution
- `pydantic>=2.0` - Schema validation for parts registry and execution config
- `rfc8785==0.1.4` - JCS canonicalization (RFC 8785) for config_hash computation (D-12 identity system)

**Frontend:**

- React 19.2+ - Component framework
- React Router 7.x - Client-side routing
- Vite 8.0+ - ESM build tool (faster than webpack)
- TailwindCSS 4.3 - Utility-first styling
- Radix UI - Accessible component primitives
- Sigma.js 3.0 / react-sigma 5.0 - Graph visualization

**Testing:**

- pytest 8.4.2+ - Python unit/integration tests (v1)
- pytest-asyncio 1.2+ - Async test support
- jsonschema>=4.0 - Validates run records against rig-trace.schema.json (databasise tests)
- Bun test - JavaScript/TypeScript tests
- pre-commit - Git hook framework for linting/formatting

**Build/Dev:**

- Docker (multi-stage) - Production image generation with layer caching
- Makefile - Development task automation
- setuptools 64+ - Python packaging/distribution
- uv sync - Locked dependency installation (uv.lock)

## Key Dependencies

**Critical (Embedded, v1):**

- `pycozo[embedded]` 0.7.6 - Embedded graph database (RocksDB, MPL-2.0 copyleft, file-level weak)
- `faiss-cpu` 1.7.0-2.0 - Vector similarity search (exact IndexFlatIP cosine, no GPU required)
- `nano-vectordb` - Lightweight fallback vector store
- `networkx` - Graph algorithms (default in v1 for quick-start, replaced by Cozo in production)

**Agnostic Machine Primitives (Databasise 2.0):**

- `pycozo[embedded]` 0.7.6 - Graph store primitive (exact pin, D-05 architecture frozen)
- `faiss-cpu` >=1.7.0,<2.0.0 - Vector store primitive
- `rfc8785` 0.1.4 - JCS canonicalization for config identity hashing (D-12)
- `pydantic` >=2.0,<3.0 - Data validation for parts registry and execution

**LLM Providers (v1):**

- `openai` 2.0-3.0 - OpenAI API client
- `anthropic` 0.18-1.0 - Claude/Anthropic API
- `google-genai` 1.0-3.0 - Google Gemini API
- `ollama` 0.1-1.0 - Local LLM integration
- `voyageai` 0.2-1.0 - Voyage AI embeddings
- `llama-index` 0.14+ - LLaMA Index framework (optional)

**Storage Backends (v1):**

- `asyncpg` 0.31-1.0 - PostgreSQL async driver
- `pgvector` 0.4-1.0 - PostgreSQL vector extension
- `pymongo` 4.0-5.0 - MongoDB/Atlas integration
- `pymilvus` 2.6.2-4.0 - Milvus vector database
- `qdrant-client` 1.11-2.0 - Qdrant vector database
- `redis` 5.0-9.0 - Redis cache/KV store
- `neo4j` 5.0-7.0 - Neo4j graph database
- `opensearch-py` 3.0-4.0 - OpenSearch/Elasticsearch compatibility

**Document Processing (v1):**

- `pypdf` 6.1+ - PDF text/metadata extraction
- `python-docx` 0.8-2.0 - DOCX file parsing
- `python-pptx` 0.6-2.0 - PPTX file parsing
- `openpyxl` 3.0-4.0 - XLSX spreadsheet parsing
- `cairosvg` 2.5-3.0 - SVG to PNG rasterization
- `defusedxml` 0.7-1.0 - Safe XML parsing (XXE mitigation)
- `langchain-text-splitters` 0.3-2.0 - Text chunking (recursive, semantic, token-based)
- `langchain-experimental` 0.3.2+ - SemanticChunker with min_chunk_size support

**Utilities (v1):**

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

**Observability (v1):**

- `langfuse` 3.8.1+ - LLM trace/eval platform (optional)
- `aioboto3` 12.0-16.0 - AWS S3/Bedrock async (optional)

## Configuration

**Environment:**

- `.env` file per deployment (host/compose)
- Environment variables override all defaults
- Settings sourced via Pydantic ConfigDict from `LIGHTRAG_*`, `LLM_*`, `EMBEDDING_*`, provider-specific prefixes
- API key configuration: `X-API-Key` header, `TOKEN_SECRET` (JWT), `AUTH_ACCOUNTS` (bcrypt hashes)

**Build:**

- `pyproject.toml` - Python project metadata, dependencies, entry points, tool config (pytest, ruff, setuptools)
  - `v1/pyproject.toml` - v1/LightRAG engine dependencies (requires Python 3.10+)
  - `databasise/pyproject.toml` - Agnostic machine dependencies (requires Python 3.11+, minimal set)
- `uv.lock` - Locked dependency versions per directory (reproducible installs)
  - `v1/uv.lock` - v1 lock file
  - `databasise/uv.lock` - Databasise lock file (separate workspace)
- `Dockerfile` - Multi-stage: frontend build (Bun) → Python build (uv + Rust) → runtime (Python 3.12-slim)
- `.pre-commit-config.yaml` - Git hooks for linting/formatting
- `setup.py` - Fallback setuptools entry point
- `vite.config.ts` - Frontend build config (React plugin, Tailwind, asset optimization)
- `tsconfig.json` - TypeScript compiler settings
- `eslint.config.js` - JavaScript linting rules
- `.prettierrc` - Code formatting (Prettier)
- `tailwind.config.ts` - Tailwind theme/plugin customization

**Runtime Configuration Files:**

- `env.example` - Template with all configurable variables documented (~1100 lines)
- `env.docker-compose-full` - Full Docker Compose preset with all services
- `.env.development` (frontend) - Vite dev server configuration
- `env.aoi.example` - AOI-specific configuration template

**Databasise 2.0 Artifacts:**

- `databasise/pyproject.toml` - Agnostic machine package (separate from v1, Python 3.11+ required)
- `databasise/uv.lock` - Minimal locked dependencies (Cozo, Faiss, RFC8785, Pydantic only)
- `docs/system-model/rig-trace.schema.json` - JSON schema for validating execution traces

## Platform Requirements

**Development:**

- Python 3.10+ with pip/uv (v1/LightRAG development)
- Python 3.11+ with pip/uv (databasise/agnostic machine development)
- Node.js 18+ or Bun 1.0+
- Docker (for containerized testing/deployment)
- Git (for pre-commit hooks)
- Rust toolchain (optional, for building native wheels from source)

**Production:**

- Docker container runtime OR bare Python 3.12+ environment (v1/LightRAG)
- Python 3.11+ environment (databasise/agnostic machine)
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

**Minimum Deployment:**

- Single machine with Python 3.12, 4GB RAM (testing)
- 8GB RAM + SSD recommended for production with embedded Cozo + Nano VectorDB
- GPU optional (Faiss CPU-only by default; can swap for GPU if needed)

**Databasise 2.0 (Agnostic Machine):**

- Python 3.11+ (strict requirement for `asyncio.TaskGroup`)
- No external database servers required (embedded Cozo + Faiss only)
- 4GB RAM minimum for in-process stores
- Runs in same process as application (no sidecar services)

---

*Stack analysis: 2026-08-31*
