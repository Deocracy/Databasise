# Technology Stack

**Analysis Date:** 2026-09-03

## Languages

**Primary:**
- Python 3.10+ (v1 / LightRAG-based engine) - Core RAG engine, API server, document processing, embeddings
- Python 3.11+ (databasise / 2.0 agnostic machine) - Modality-agnostic fitting contract and component orchestration
- TypeScript/React 19.2+ - Web UI frontend with graph visualization (v1/lightrag_webui/)
- JavaScript - Frontend build tooling (Vite, ESLint, Prettier)

**Secondary:**
- Rust - Build dependencies (Faiss native wheels, Cozo embedded compilation)
- YAML/JSON - Configuration files, Docker Compose, testing fixtures

## Runtime

**Environment:**
- Python 3.12-slim (Docker production runtime) in multi-stage build
- Node.js 18+ or Bun 1.x (frontend build and testing)
- Gunicorn + Uvicorn (ASGI application servers for v1)

**Package Managers:**
- `uv` (Python) - Primary package manager for dependency resolution and layer caching
- `pip` (Python) - Fallback, vendored wheels for offline installation
- Bun 1.x (JavaScript/Node) - Frontend package manager and test runner
- npm/yarn compatible (bun.lockb lockfile format)

## Frameworks

**Core API & Application:**
- FastAPI 0.108+ (`v1/pyproject.toml:85`) - REST API server with Pydantic v2 validation
- Pydantic v2 - Type validation, settings management, ConfigDict binding

**Frontend UI:**
- React 19.2+ (`v1/lightrag_webui/package.json:59`) - Component framework
- React Router 7.x - Client-side routing
- Vite 8.0+ - ESM build tool (faster than webpack)
- TailwindCSS 4.3 - Utility-first styling with @tailwindcss/vite plugin

**Graph Visualization:**
- Sigma.js 3.0 - Graph visualization library (underlying engine)
- @react-sigma/core 5.0+ - React wrapper for Sigma.js
- graphology 0.26.0 - Graph data structure
- Graphology layout plugins (force, forceatlas2, circular, noverlap)

**Document Processing & Chunking:**
- LightRAG 1.5.4 (fork with Cozo plugin, v1 only) - Base RAG engine implementation
- langchain-text-splitters (0.3-2.x) - Recursive, semantic, token-based chunking
- langchain-experimental (0.3.2+) - SemanticChunker with min_chunk_size support

**Testing:**
- pytest 8.4.2+ - Python unit/integration test runner
- pytest-asyncio 1.2+ - Async test support for Python
- Bun test - JavaScript/TypeScript test runner (native to Bun)

**Build & Development Tools:**
- pre-commit - Git hook framework for linting/formatting
- Docker (multi-stage) - Production image generation with layer caching
- Makefile - Development task automation
- setuptools 64+ - Python packaging/distribution
- ruff - Python linter and code quality checker
- ESLint (flat config format) - JavaScript linting
- Prettier 3.8+ - Code formatter (TypeScript/JavaScript)
- TypeScript ~6.0.3 - Static type checking for frontend

## Key Dependencies

**Data Storage Backends:**
- `pycozo[embedded]` 0.7.6 (v1/databasise) - Embedded graph database (RocksDB backend, MPL-2.0 file-level weak copyleft)
- `faiss-cpu` 1.7.0-2.0 - Vector similarity search (IndexFlatIP cosine, CPU-only, no GPU required)
- `nano-vectordb` - Lightweight fallback vector store (v1 default for testing)
- `networkx` - Graph algorithms (v1 quick-start, replaced by Cozo in production)

**LLM & Embedding Clients:**
- `openai` 2.0-3.0 (v1) / 2.0-4.0 (databasise) - OpenAI API client (also covers OpenRouter, Mistral, other OpenAI-compatible)
- `anthropic` 0.18-1.0 - Claude/Anthropic API
- `google-genai` 1.0-3.0 - Google Gemini API (via google-api-core)
- `ollama` 0.1-1.0 - Local LLM integration
- `voyageai` 0.2-1.0 - Voyage AI embeddings
- `zhipuai` 2.0-3.0 - Zhipu AI / ChatGLM embeddings
- `llama-index` 0.14+ - LLaMA Index framework (optional)

**Database Clients:**
- `asyncpg` 0.31-1.0 - PostgreSQL async driver
- `pgvector` 0.4-1.0 - PostgreSQL vector extension client
- `pymongo` 4.0-5.0 - MongoDB/Atlas integration
- `pymilvus` 2.6.2-4.0 - Milvus vector database client
- `qdrant-client` 1.11-2.0 - Qdrant vector database client
- `redis` 5.0-9.0 - Redis cache/KV store client
- `neo4j` 5.0-7.0 - Neo4j graph database client
- `opensearch-py` 3.0-4.0 - OpenSearch/Elasticsearch compatibility

**Document Processing:**
- `pypdf` 6.1+ - PDF text/metadata extraction
- `python-docx` 0.8-2.0 - DOCX file parsing
- `python-pptx` 0.6-2.0 - PPTX file parsing
- `openpyxl` 3.0-4.0 - XLSX spreadsheet parsing
- `cairosvg` 2.5-3.0 - SVG to PNG rasterization (for markdown images)
- `defusedxml` 0.7-1.0 - Safe XML parsing (XXE mitigation)

**HTTP & Async:**
- `aiohttp` - Async HTTP client/server
- `httpx` 0.28.1+ - Async HTTP client with streaming
- `asyncpg` - Async PostgreSQL driver
- `aioboto3` 12.0-16.0 - AWS S3/Bedrock async (optional)

**Utilities:**
- `tenacity` - Retry logic with exponential backoff
- `tiktoken` - GPT tokenizer (pre-cached in Docker)
- `pydantic-settings` - Environment variable binding (part of Pydantic v2)
- `python-dotenv` - .env file loading
- `PyYAML` 6.0-7.0 - YAML parsing
- `json_repair` - Fault-tolerant JSON parsing
- `bcrypt` 4.0+ - Password hashing (auth)
- `PyJWT` 2.8-3.0 - JWT token handling
- `python-jose[cryptography]` - JOSE/JWT with cryptography backend
- `xlsxwriter` 3.1+ - XLSX generation
- `pycryptodome` 3.0-4.0 - PDF encryption support
- `numpy` 1.24.0-3.0 - Numerical arrays
- `pandas` 2.0-2.4 - Tabular data processing
- `packaging` - Version parsing
- `rfc8785` 0.1.4 (databasise only) - RFC 8785 (JCS) canonicalization for config hashing
- `jsonpatch` (databasise only) - RFC 6902 JSON Patch application

**Observability (Optional):**
- `langfuse` 3.8.1+ - LLM trace/eval platform (optional observability)
- `ragas` 0.3.7+ - RAG quality assessment (evaluation)

**Frontend Dependencies:**
- `@radix-ui/*` - Accessible UI component primitives (dialog, select, checkbox, tabs, etc.)
- `axios` 1.17+ - HTTP client
- `zustand` 5.0+ - State management (alternative to Redux)
- `react-markdown` 10.1+ - Markdown rendering
- `react-syntax-highlighter` 16.1+ - Code syntax highlighting
- `mermaid` 11.15+ - Diagram rendering
- `katex` 0.17+ - LaTeX math rendering
- `react-dropzone` 15.0+ - File upload handling
- `react-error-boundary` 6.1+ - Error boundary component
- `react-i18next` 17.0+ - Internationalization
- `minisearch` 7.2+ - Client-side search
- `clsx` 2.1+ - Classname utilities
- `class-variance-authority` - CSS class generation

## Configuration

**Environment Setup:**
- `.env` file per deployment (host/compose)
- Environment variables override all defaults (Pydantic ConfigDict binding)
- Settings sourced via `LIGHTRAG_*`, `LLM_*`, `EMBEDDING_*`, provider-specific prefixes
- `env.example` - Comprehensive template (~1100 lines) with all configurable variables
- `.env.development` (frontend) - Vite dev server configuration
- Config loading for API key, JWT secrets, storage backends (database selection)

**Python Configuration:**
- `pyproject.toml` - Project metadata, dependencies, entry points, tool config
  - v1: `v1/pyproject.toml` with extras: [api], [offline-storage], [offline-llm], [offline], [test]
  - databasise: `databasise/pyproject.toml` with dependency-groups: [dev]
- `uv.lock` - Locked dependency versions (reproducible installs via uv)
- `setup.py` - Fallback setuptools entry point
- `tool.ruff` config (target-version py310 for v1, py311 for databasise)
- `tool.pytest.ini_options` - asyncio_mode auto, testpaths = ["tests"]

**Frontend Configuration:**
- `vite.config.ts` - React plugin, Tailwind integration, asset optimization, dev server config
- `tsconfig.json` - TypeScript compiler settings (strict mode, module resolution)
- `eslint.config.js` - Flat config format with react-refresh, typescript-eslint
- `.prettierrc` or `prettier.config.js` - Code formatting rules
- `tailwind.config.ts` - Tailwind theme/plugin customization with typography

**Docker & Deployment:**
- `Dockerfile` (v1) - Multi-stage: frontend build (Bun) → Python build (uv + Rust) → runtime
- `docker-compose.yml` - Minimal stack (LightRAG container only, external services via .env)
- `docker-compose-full.yml` - Full service stack with PostgreSQL, Neo4j, MongoDB, Redis, Milvus, etc.
- `docker-compose.podman.yml` - Podman-compatible compose file

**Git Hooks:**
- `.pre-commit-config.yaml` - Automated linting/formatting on commit

## Platform Requirements

**Development:**
- Python 3.10+ (v1) or 3.11+ (databasise)
- Node.js 18+ or Bun 1.0+
- Docker (for containerized testing/deployment)
- Git (for pre-commit hooks)
- Rust toolchain (optional, for building native wheels from source)
- Make (for task automation)

**Production:**
- Python 3.12-slim runtime (Docker container)
- Reverse proxy (nginx, Caddy) for multi-instance deployment behind API prefix
- Single machine minimum: 4GB RAM (testing), 8GB RAM + SSD (production with embedded Cozo + Nano VectorDB)
- Storage: 50GB+ SSD recommended (for document storage, graph data, cache)
- GPU optional (Faiss CPU-only by default; can swap for GPU if needed)

**Optional Services:**
- PostgreSQL 12+ (if using POSTGRES_* storage) with pgvector 0.7.0+ extension
- Redis 5.0+ (if using Redis storage)
- MongoDB 4.0+ or Atlas (if using MongoDB storage)
- Neo4j 5.0+ (if using Neo4j storage)
- Milvus 2.3+ (if using Milvus storage)
- Qdrant (if using Qdrant storage)
- OpenSearch 2.0+ (if using OpenSearch storage)
- Memgraph (if using Memgraph storage)
- MinIO or S3-compatible storage (Milvus dependency)
- vLLM or SGLang (optional, for local embedding/reranking)
- MinerU or Docling service (optional, for async document parsing)

---

*Stack analysis: 2026-09-03*
