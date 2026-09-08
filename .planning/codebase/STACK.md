---
last_mapped_commit: 8044f9a
---

# Technology Stack

**Analysis Date:** 2026-09-08

## Languages

**Primary:**
- Python 3.10+ (v1/lightrag) - Core RAG engine, API server, document processing, embeddings
- Python 3.11+ (databasise/2.0) - Agnostic machine rebuild; higher floor than v1 to use stdlib `asyncio.TaskGroup` instead of anyio dependency
- TypeScript (~6.0.3) - Frontend component types and logic
- JavaScript (Node.js) - Frontend build tooling via Bun

**Secondary:**
- Rust - Build dependencies for native wheels (Faiss, Cozo embedding, PDF encryption)
- YAML/JSON - Configuration files, Docker Compose, testing fixtures

## Runtime

**Environment:**
- **Development/Testing:** Local NixOS (host legion), bare Python 3.10+ or 3.11+, Node.js 18+ or Bun 1.x
- **Production:** Python 3.12-slim Docker image (official CPython), multi-stage build with Bun for frontend, uv for dependencies
- **Package Managers:**
  - `uv` (Python) - Primary dependency resolver and installer; vendored wheels for offline installation
  - `pip` (Python) - Fallback, used inside Docker for runtime re-installation and consistency
  - Bun 1.x (JavaScript/Node) - Frontend package manager, lockfile: `bun.lock`

## Frameworks

**Core API (v1):**
- FastAPI 0.108+ - REST API server with Pydantic v2 validation, root_path override support for multi-site deployment
- Uvicorn - ASGI application server
- Gunicorn - WSGI/ASGI wrapper for multi-worker deployments

**Core Engine (v1 & v2):**
- LightRAG 1.5.4 (v1 only; v2.0 will decompose into modalities) - Monolithic RAG engine with Cozo plugin
- Pydantic v2 - Type validation, environment variable binding (pydantic-settings part of v2)

**Frontend (v1):**
- React 19.2+ - Component framework
- React Router 7.x - Client-side routing
- Vite 8.0+ - ESM build tool with Tailwind plugin
- TailwindCSS 4.3 - Utility-first CSS framework
- Radix UI 1.x - Accessible component primitives (dialog, select, tabs, popover, checkbox, etc.)
- Sigma.js 3.0 / react-sigma 5.0 - Graph visualization engine with layout algorithms (force, circular, forceatlas2, noverlap, etc.)
- Mermaid 11.x - Markdown diagram rendering
- React Markdown - Markdown to React component conversion with KaTeX math, syntax highlighting

**Testing & Linting (both v1 and v2):**
- pytest 8.4.2+ - Python test framework
- pytest-asyncio 1.2+ - Async test support with auto mode
- Bun test - JavaScript/TypeScript test runner
- Ruff - Python linter and code quality checker (target version py310 for v1, py311 for v2)
- ESLint (flat config format) - JavaScript linting with typescript-eslint parser
- Prettier 3.x - Code formatter for TypeScript/JavaScript
- pre-commit - Git hook framework for linting/formatting enforcement

**Build & Deployment (v1):**
- Docker (multi-stage) - Production image generation with layer caching (Bun → uv Python build → python:3.12-slim runtime)
- Makefile - Development task automation
- setuptools 64+ - Python packaging and distribution
- uv sync - Locked dependency installation from `uv.lock`

## Key Dependencies

### Core Storage & Search (v1 & v2)

- `pycozo[embedded]` 0.7.6 (v1 flexible range; v2 exactly pinned) - Embedded graph database with Cozo/Datalog, RocksDB backend, MPL-2.0 file-level weak copyleft (compatible with MIT shipping)
- `faiss-cpu` 1.7.0–2.0.0 - Vector similarity search (exact IndexFlatIP cosine metric, CPU-only by default)
- `nano-vectordb` - Lightweight fallback vector store for testing/small deployments
- `networkx` - Graph algorithms (v1 default for quick-start, replaced by Cozo in production)

### LLM & Embedding Providers (v1)

- `openai` 2.0–3.0 - OpenAI API client, also used for OpenAI-compatible endpoints (e.g., OpenRouter, vLLM, SGLang)
- `anthropic` 0.18–1.0 - Claude/Anthropic API
- `google-genai` 1.0–3.0 - Google Gemini API
- `ollama` 0.1–1.0 - Local LLM integration via Ollama API
- `voyageai` 0.2–1.0 - Voyage AI embeddings
- `llama-index` 0.14+ - LLaMA Index framework (optional, for integration patterns)
- `zhipuai` 2.0–3.0 - Chinese LLM provider

### Storage Backends (v1, optional via offline-storage extra)

- `asyncpg` 0.31–1.0 - PostgreSQL async driver with pgvector extension support
- `pgvector` 0.4–1.0 - PostgreSQL vector extension client (HNSW, IVFFlat, VCHORDRQ index types)
- `pymongo` 4.0–5.0 - MongoDB/Atlas integration
- `pymilvus` 2.6.2–4.0 - Milvus vector database gRPC client
- `qdrant-client` 1.11–2.0 - Qdrant vector database HTTP client
- `redis` 5.0–9.0 - Redis cache and KV store
- `neo4j` 5.0–7.0 - Neo4j graph database Bolt client
- `opensearch-py` 3.0–4.0 - OpenSearch/Elasticsearch compatibility

### Document Processing (v1, optional via api extra)

- `pypdf` 6.1+ - PDF text/metadata extraction and encryption support
- `python-docx` 0.8–2.0 - DOCX (Word) file parsing
- `python-pptx` 0.6–2.0 - PPTX (PowerPoint) file parsing
- `openpyxl` 3.0–4.0 - XLSX (Excel) spreadsheet parsing
- `cairosvg` 2.5–3.0 - SVG to PNG rasterization for native markdown image embedding
- `defusedxml` 0.7–1.0 - Safe XML parser (XXE mitigation, used by python-docx)
- `pycryptodome` 3.0–4.0 - PDF encryption/decryption support

### Text Chunking (v1, optional via api extra)

- `langchain-text-splitters` 0.3–2 - RecursiveCharacterTextSplitter for semantic chunking (CJK sentence awareness)
- `langchain-experimental` 0.3.2+ - SemanticChunker with vector-based breakpoint detection and min_chunk_size support

### Authentication & Security (v1)

- `bcrypt` 4.0+ - Password hashing for AUTH_ACCOUNTS
- `PyJWT` 2.8–3.0 - JWT token generation and validation
- `python-jose` - JOSE/JWT with cryptography backend (alternative JWT path)

### Utilities

- `aiohttp` - Async HTTP client/server (v1 core dependency, v2 removed)
- `tenacity` - Retry logic with exponential backoff
- `tiktoken` - GPT tokenizer (pre-cached in Docker for offline use)
- `json_repair` - Fault-tolerant JSON parsing (handles LLM output malformations)
- `PyYAML` 6.0–7.0 - YAML parsing (entity type prompts, configuration)
- `numpy` 1.24–3.0 - Numeric arrays (Faiss dependency)
- `pandas` 2.0–2.4 - Data manipulation (used in chunking, analysis)
- `xlsxwriter` 3.1+ - XLSX generation for export
- `setuptools` 64+ - Packaging utilities
- `packaging` - Version parsing and comparison
- `python-dotenv` - .env file loading
- `python-multipart` - FastAPI multipart form data handling
- `httpx` 0.28.1+ - Async HTTP client (FastAPI TestClient dependency)
- `httpcore` - HTTP/1.1 and HTTP/2 implementation
- `jiter` - Fast JSON parsing (Pydantic v2 accelerator)
- `ascii_colors` - Colored terminal output
- `distro` - Linux distribution detection
- `psutil` - System monitoring (memory, process info)
- `pytz` - Timezone database
- `pipmaster` - Package management utilities

### Databasise 2.0 Specific

- `rfc8785` 0.1.4 - JCS (JSON Canonicalization Scheme) for deterministic config hashing
- `jsonpatch` - RFC 6902 JSON Patch application (arm-patch removal semantics)
- `openai` 2.0–4.0 (widened range from v1's 2.0–3.0) - OpenAI-compatible LLM/embedding client construction

### Frontend Dependencies (v1 WebUI)

- `react` 19.2.7 - Core component library
- `react-dom` 19.2.7 - DOM rendering
- `react-router-dom` 7.17 - Client-side routing with loader/action pattern
- `zustand` 5.x - State management (alternative to Redux)
- `axios` 1.17 - HTTP client for API calls
- `@faker-js/faker` 10.x - Fake data generation (testing)
- `graphology` 0.26 - Graph data structure library
- `graphology-layout-*` - Layout algorithms (force, forceatlas2, noverlap, etc.)
- `mermaid` 11.x - Diagram rendering
- `react-markdown` 10.x - Markdown to JSX with plugin support
- `rehype-katex`, `rehype-raw`, `remark-gfm`, `remark-math` - Markdown extensions
- `react-syntax-highlighter` 16.x - Code block highlighting
- `katex` 0.17 - Math rendering
- `lucide-react` 1.17 - Icon library
- `react-select` 5.x - Accessible select component
- `react-number-format` 5.x - Number formatting input
- `react-dropzone` 15.x - File upload handling
- `react-error-boundary` 6.x - Error boundary wrapper
- `react-i18next` 17.x - Internationalization (i18n)
- `i18next` 26.x - i18n core library
- `sonner` 2.x - Toast notifications
- `cmdk` 1.x - Command palette component
- `minisearch` 7.x - Full-text search in browser
- `seedrandom` 3.x - Seeded PRNG (deterministic randomization)
- `class-variance-authority`, `clsx`, `tailwind-merge` - CSS utility helpers
- `tailwind-scrollbar` 4.x - TailwindCSS scrollbar styling
- `typography` 0.16 - TailwindCSS typography plugin
- `unist-util-visit` 5.x - AST visitor utility

### Frontend Dev Dependencies (v1 WebUI)

- `typescript` ~6.0.3 - TypeScript compiler
- `vite` 8.0+ - Build tool
- `@vitejs/plugin-react` 6.x - React Fast Refresh support
- `@tailwindcss/vite` 4.3 - Tailwind CSS Vite plugin
- `tailwindcss` 4.3 - Utility CSS framework
- `tailwind-scrollbar` 4.x - Scrollbar styling
- `tailwindcss-animate` 1.x - Animation utilities
- `@tailwindcss/typography` 0.5 - Typography plugin
- `eslint` 10.x with typescript-eslint - Linting
- `prettier` 3.x with tailwind plugin - Code formatting
- `@types/*` - TypeScript type definitions for React, Node, ESLint, etc.

## Configuration

**Environment Variables:**
- `.env` file per deployment (host/compose) or Docker-injected
- Environment variables override all defaults via Pydantic ConfigDict
- Settings sourced via prefixes: `LIGHTRAG_*`, `LLM_*`, `EMBEDDING_*`, `POSTGRES_*`, `NEO4J_*`, `MONGO_*`, `REDIS_*`, `MILVUS_*`, `QDRANT_*`, `OPENSEARCH_*`, provider-specific (OpenAI, Bedrock, Gemini, etc.)
- API key configuration: `X-API-Key` header, `TOKEN_SECRET` (JWT), `AUTH_ACCOUNTS` (bcrypt hashes)
- `LIGHTRAG_API_PREFIX` for multi-site deployment behind reverse proxy

**Python Configuration Files:**
- `pyproject.toml` - Project metadata, dependencies, entry points, tool config (pytest, ruff, setuptools)
- `uv.lock` - Locked dependency versions for reproducible installs (both v1 and databasise)
- `setup.py` - Fallback setuptools entry point (v1)

**Frontend Configuration:**
- `vite.config.ts` - Build config with React plugin, Tailwind integration, asset optimization, dev proxy
- `tsconfig.json` - TypeScript compiler settings with path aliases (`@` → `src/`)
- `eslint.config.js` - ESLint rules (flat config format, React 19 with refresh plugin)
- `.prettierrc.json` - Code formatting (print width, semi, trailing comma, tailwind class sort)
- `tailwind.config.ts` - TailwindCSS theme customization and plugin registration

**Deployment Configuration:**
- `Dockerfile` - Multi-stage: frontend (Bun) → Python build (uv + Rust) → runtime (python:3.12-slim)
- `.env.example` - Template with ~1100 documented environment variables
- `env.docker-compose-full` - Full Docker Compose preset with all services enabled
- `.pre-commit-config.yaml` - Git hooks for linting/formatting pre-commit enforcement

**Runtime Behavior:**
- Server listens on `HOST:PORT` (default 0.0.0.0:9621)
- Multi-worker mode via Gunicorn with cross-worker concurrency gates for LLM/embedding/rerank limits
- Token caching in `TIKTOKEN_CACHE_DIR` for offline use
- Workspace isolation via `WORKSPACE` env var (alphanumeric + underscore)
- Document status tracking in pluggable `LIGHTRAG_DOC_STATUS_STORAGE` (JSON, Postgres, Mongo, Redis backends)

## Platform Requirements

**Development:**
- Python 3.10+ (v1) or 3.11+ (v2) with pip/uv
- Node.js 18+ or Bun 1.0+
- Git (for pre-commit hooks)
- Rust toolchain (optional, for building native wheels from source)
- Make (for Makefile automation)

**Testing:**
- pytest 8.4.2+ (Python tests)
- Bun test (JavaScript tests)
- pytest-asyncio for async test support

**Production:**
- Docker container runtime (official images available at ghcr.io/astral-sh/uv:python3.12-bookworm-slim → python:3.12-slim)
- Or bare Python 3.12+ on Linux (NixOS on dev machine)
- Single machine minimum: 4GB RAM (testing), 8GB RAM + SSD recommended for production with embedded Cozo + Nano VectorDB
- Reverse proxy (nginx, Caddy) for multi-instance deployment or multi-site deployment behind API prefix
- Optional: GPU for Faiss (CPU-only by default, swappable)

**External Services (optional, pluggable):**
- PostgreSQL 12+ with pgvector 0.7.0+ extension (if using POSTGRES storage)
- Redis 5.0+ (if using Redis KV/doc-status storage)
- MongoDB 4.0+ or Atlas (if using MongoDB storage)
- Neo4j 5.0+ (if using Neo4j graph storage)
- Milvus 2.3+ (if using Milvus vector storage)
- Qdrant (if using Qdrant vector storage)
- OpenSearch 2.0+ (if using OpenSearch multi-purpose storage)
- MinerU API / Docling service (optional, async document parsing)
- vLLM or SGLang (optional, for local embedding/reranking)

---

*Stack analysis: 2026-09-08*
