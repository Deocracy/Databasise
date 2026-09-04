# External Integrations

**Analysis Date:** 2026-09-03

## APIs & External Services

**LLM Providers (Switchable, v1):**

- OpenAI (default)
  - SDK: `openai` package
  - Endpoint: `https://api.openai.com/v1` (configurable)
  - Auth: `LLM_BINDING_API_KEY` or `OPENAI_API_KEY`
  - Models: `gpt-4o`, `gpt-4o-mini`, o1 family
  - Config: `LLM_BINDING=openai`, `LLM_MODEL`, `LLM_TIMEOUT`, `MAX_ASYNC_LLM`
  - Features: Streaming, reasoning effort control, max_completion_tokens, extra_body for reasoning
  - Role variants: `QUERY_LLM_*`, `KEYWORD_LLM_*` prefixes

- Azure OpenAI
  - SDK: `openai` package (Azure backend)
  - Endpoint: `https://<resource>.openai.azure.com/`
  - Auth: `AZURE_OPENAI_API_KEY`
  - Config: `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`, `AZURE_OPENAI_ENDPOINT`

- Google Gemini
  - SDK: `google-genai` package
  - Endpoint: Auto-detected (AI Studio) or Vertex AI
  - Auth: `EMBEDDING_BINDING_API_KEY` (AI Studio) or `GOOGLE_APPLICATION_CREDENTIALS` (Vertex AI)
  - Config: `LLM_BINDING=gemini`, `LLM_MODEL=gemini-flash-latest`, `GEMINI_LLM_THINKING_CONFIG`
  - Vertex AI: Requires `GOOGLE_GENAI_USE_VERTEXAI=true`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`

- Anthropic Claude
  - SDK: `anthropic` package
  - Endpoint: Native API or AWS Bedrock
  - Auth: `ANTHROPIC_API_KEY` or AWS credentials
  - Config: `LLM_BINDING=bedrock`, `LLM_MODEL=us.anthropic.claude-*-v1:0`

- Ollama (local)
  - SDK: `ollama` package
  - Endpoint: `http://localhost:11434` (default, configurable)
  - Auth: None (local) or optional API key
  - Config: `LLM_BINDING=ollama`, `LLM_BINDING_HOST`, `LLM_MODEL`, `OLLAMA_LLM_NUM_CTX`

- AWS Bedrock
  - SDK: `aioboto3` (async) + boto3 (sync)
  - Endpoint: Regional (auto-detected)
  - Auth: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, or `AWS_BEARER_TOKEN_BEDROCK`
  - Config: `LLM_BINDING=bedrock`, `AWS_REGION`, `BEDROCK_LLM_*` parameters
  - Models: Claude, Nova, Llama

- OpenRouter (OpenAI-compatible)
  - SDK: `openai` package with custom host
  - Endpoint: `https://openrouter.ai/api/v1`
  - Auth: `LLM_BINDING_API_KEY` as OpenRouter API key
  - Config: `LLM_BINDING=openai`, `LLM_BINDING_HOST=https://openrouter.ai/api/v1`
  - Models: 200+ models via routing

- Zhipu AI (ChatGLM)
  - SDK: `zhipuai` package
  - Endpoint: Zhipu API (SDK-provided)
  - Auth: `ZHIPUAI_API_KEY`
  - Config: Optional LLM binding

**Embedding Providers:**

- OpenAI (default)
  - SDK: `openai` package
  - Endpoint: `https://api.openai.com/v1` (configurable)
  - Auth: `EMBEDDING_BINDING_API_KEY`
  - Model: `text-embedding-3-large` (default), `text-embedding-3-small`
  - Dim: 3072 (large), 1536 (small)
  - Config: `EMBEDDING_BINDING=openai`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `EMBEDDING_USE_BASE64`

- Google Gemini Embeddings
  - SDK: `google-genai` package
  - Endpoint: Google API (SDK-provided)
  - Auth: `EMBEDDING_BINDING_API_KEY`
  - Config: `EMBEDDING_BINDING=gemini`, `EMBEDDING_SEND_DIM=true`

- Azure OpenAI Embeddings
  - SDK: `openai` package (Azure backend)
  - Endpoint: `https://<resource>.openai.azure.com/`
  - Auth: `EMBEDDING_BINDING_API_KEY`
  - Config: `EMBEDDING_BINDING=azure_openai`, `AZURE_EMBEDDING_DEPLOYMENT`, `AZURE_EMBEDDING_API_VERSION`

- Ollama Embeddings
  - SDK: `ollama` package
  - Endpoint: `http://localhost:11434` (configurable)
  - Auth: Optional API key
  - Config: `EMBEDDING_BINDING=ollama`, `EMBEDDING_BINDING_HOST`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `OLLAMA_EMBEDDING_NUM_CTX`

- Bedrock Embeddings
  - SDK: `aioboto3` (async)
  - Endpoint: Regional (auto-detected)
  - Auth: AWS credentials (same as LLM Bedrock config)
  - Model: `amazon.titan-embed-text-v2:0`, `cohere.embed-*`
  - Config: `EMBEDDING_BINDING=bedrock`, `AWS_REGION`

- Voyage AI Embeddings
  - SDK: `voyageai` package
  - Endpoint: Voyage API
  - Auth: `EMBEDDING_BINDING_API_KEY`
  - Config: Optional

- Jina AI Embeddings
  - SDK: `httpx` (HTTP client)
  - Endpoint: `https://api.jina.ai/v1/embeddings`
  - Auth: `EMBEDDING_BINDING_API_KEY`
  - Config: `EMBEDDING_BINDING=jina`, `EMBEDDING_BINDING_HOST`, `EMBEDDING_MODEL`

**Reranking Providers:**

- Cohere Rerank
  - Endpoint: `https://api.cohere.com/v2/rerank`
  - Auth: `RERANK_BINDING_API_KEY`
  - Config: `RERANK_BINDING=cohere`, `RERANK_MODEL=rerank-v3.5`, `RERANK_ENABLE_CHUNKING`, `RERANK_MAX_TOKENS_PER_DOC`

- Jina Rerank
  - Endpoint: `https://api.jina.ai/v1/rerank`
  - Auth: `RERANK_BINDING_API_KEY`
  - Config: `RERANK_BINDING=jina`, `RERANK_MODEL=jina-reranker-v2-base-multilingual`

- Aliyun Dashscope
  - Endpoint: `https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank`
  - Auth: `RERANK_BINDING_API_KEY`
  - Config: `RERANK_BINDING=aliyun`, `RERANK_MODEL=gte-rerank-v2`

- vLLM (local, OpenAI-compatible)
  - Endpoint: `http://localhost:8000/rerank` (configurable)
  - Auth: Optional (vLLM API key)
  - Config: `RERANK_BINDING=cohere` (uses Cohere binding), `RERANK_BINDING_HOST`, `RERANK_BINDING_API_KEY`

## Data Storage

**Graph Databases:**

- Cozo (embedded, default for Databasise 2.0)
  - Package: `pycozo[embedded]` 0.7.6
  - Backend: RocksDB (embedded)
  - License: MPL-2.0 (file-level weak copyleft, compatible with MIT shipping)
  - Config: Auto-initialized, no external config needed
  - File location: `WORKING_DIR` or `LIGHTRAG_GRAPH_STORAGE=CozoStorage`

- Neo4j (production graph database)
  - Package: `neo4j` 5.0-7.0
  - Endpoint: `neo4j+s://`, `neo4j+ssc://`, `bolt://`
  - Auth: `NEO4J_USERNAME`, `NEO4J_PASSWORD`
  - Config: `LIGHTRAG_GRAPH_STORAGE=Neo4jStorage`, `NEO4J_URI`, `NEO4J_DATABASE`, `NEO4J_MAX_CONNECTION_POOL_SIZE`, connection retry settings
  - Features: ACID transactions, full-text search

- NetworkX (in-memory, testing/quick-start)
  - Built-in (no external package)
  - Backend: Python dictionary (in-memory)
  - Config: `LIGHTRAG_GRAPH_STORAGE=NetworkXStorage`
  - Note: Data not persisted; replaced by Cozo or Neo4j in production

- PostgreSQL + pgvector (hybrid graph/vector)
  - Packages: `asyncpg`, `pgvector`
  - Extension: pgvector 0.7.0+ required
  - Endpoint: `postgresql://user:pass@host:5432/database`
  - Auth: `POSTGRES_USER`, `POSTGRES_PASSWORD`
  - Config: `LIGHTRAG_GRAPH_STORAGE=PostgresStorage`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DATABASE`, connection pool/retry settings
  - Features: ACID, full-text search, pgvector for embeddings

- Memgraph (graph database, Cypher-compatible)
  - Package: (built-in via BOLT protocol client)
  - Endpoint: `bolt://localhost:7687`
  - Auth: `MEMGRAPH_USERNAME`, `MEMGRAPH_PASSWORD`
  - Config: `LIGHTRAG_GRAPH_STORAGE=MemgraphStorage`, `MEMGRAPH_URI`, `MEMGRAPH_DATABASE`

**Vector Databases:**

- Faiss (CPU, default for v1)
  - Package: `faiss-cpu` 1.7.0-2.0
  - Index: IndexFlatIP (cosine similarity, exact)
  - Backend: File-based or in-memory
  - Config: `LIGHTRAG_VECTOR_STORAGE=FaissStorage`, `FAISS_INDEX_PATH`
  - Deployment: Embedded in-process, no external service

- Nano VectorDB (lightweight fallback)
  - Package: `nano-vectordb`
  - Backend: JSON-based (file-backed)
  - Config: `LIGHTRAG_VECTOR_STORAGE=NanoVectorDBStorage`

- Milvus (distributed vector database)
  - Package: `pymilvus` 2.6.2-4.0
  - Endpoint: `http://localhost:19530`
  - Auth: `MILVUS_USER`, `MILVUS_PASSWORD` (optional)
  - Config: `LIGHTRAG_VECTOR_STORAGE=MilvusStorage`, `MILVUS_URI`, `MILVUS_DB_NAME`, index type (HNSW, IVF_FLAT, AUTOINDEX), metric (COSINE)
  - Dependencies: MinIO (S3-compatible storage for Milvus)
  - Features: Distributed, scalable, schema migration with retry logic

- Qdrant (vector database)
  - Package: `qdrant-client` 1.11-2.0
  - Endpoint: `http://localhost:6333`
  - Auth: `QDRANT_API_KEY` (optional)
  - Config: `LIGHTRAG_VECTOR_STORAGE=QdrantStorage`, `QDRANT_URL`, upsert/delete batching limits
  - Features: Local or cloud hosted

- PostgreSQL + pgvector (vector storage)
  - Same as graph storage; pgvector extension provides vector operations
  - Config: `LIGHTRAG_VECTOR_STORAGE=PostgresVectorStorage`, same PostgreSQL connection settings
  - Index types: HNSW, IVFFlat, VCHORDRQ (custom)

- MongoDB Atlas Vector Search
  - Package: `pymongo` 4.0-5.0
  - Endpoint: `mongodb+srv://user:pass@cluster.mongodb.net/`
  - Auth: `MONGO_URI`
  - Config: `LIGHTRAG_VECTOR_STORAGE=MongoVectorDBStorage`, `MONGO_DATABASE`
  - Features: Native vector search, serverless

- OpenSearch (search + vector database)
  - Package: `opensearch-py` 3.0-4.0
  - Endpoint: Comma-separated hosts (e.g., `localhost:9200`)
  - Auth: `OPENSEARCH_USER`, `OPENSEARCH_PASSWORD`
  - Config: `LIGHTRAG_VECTOR_STORAGE=OpenSearchStorage`, `OPENSEARCH_HOSTS`, `OPENSEARCH_USE_SSL`, k-NN settings (HNSW)
  - Features: Full-text search, vector search, PPL graph lookups

**Key-Value / Document Status Storage:**

- JSON (file-based, default testing)
  - Backend: JSON files in `WORKING_DIR`
  - Config: `LIGHTRAG_KV_STORAGE=JsonKVStorage`, `LIGHTRAG_DOC_STATUS_STORAGE=JsonDocStatusStorage`
  - Deployment: No external dependencies

- PostgreSQL (production)
  - Config: `LIGHTRAG_KV_STORAGE=PostgresKVStorage`, same PostgreSQL connection settings
  - Tables: auto-created for KV and doc status

- Redis (in-memory cache)
  - Package: `redis` 5.0-9.0
  - Endpoint: `redis://localhost:6379`
  - Auth: Optional (inline in URI or REDIS_* env vars)
  - Config: `LIGHTRAG_KV_STORAGE=RedisKVStorage`, `REDIS_URI`, `REDIS_SOCKET_TIMEOUT`, `REDIS_MAX_CONNECTIONS`

- MongoDB (document storage)
  - Config: `LIGHTRAG_KV_STORAGE=MongoKVStorage`, same MongoDB connection settings

- OpenSearch (also supports KV)
  - Config: `LIGHTRAG_KV_STORAGE=OpenSearchKVStorage`

## Authentication & Identity

**API Authentication:**

- JWT (PyJWT)
  - Package: `PyJWT` 2.8-3.0
  - Secret: `TOKEN_SECRET`
  - Env vars: `TOKEN_SECRET`, `JWT_ALGORITHM`, `TOKEN_EXPIRE_HOURS`, `GUEST_TOKEN_EXPIRE_HOURS`, `TOKEN_AUTO_RENEW`, `TOKEN_RENEW_THRESHOLD`
  - Middleware: Header `Authorization: Bearer <token>`

- API Key (X-API-Key header)
  - Env vars: `LIGHTRAG_API_KEY`, `WHITELIST_PATHS`
  - Header: `X-API-Key: <key>`

- Password Hashing
  - Package: `bcrypt` 4.0+
  - Usage: User authentication via `AUTH_ACCOUNTS` (bcrypt hashes)
  - Config: `AUTH_ACCOUNTS='admin:admin123,user1:{bcrypt}$2b$...'`

- JOSE/Cryptography
  - Package: `python-jose[cryptography]`
  - Backend: Cryptography library for JWT signing/verification

## Document Processing Services

**Native Parser (built-in):**
- Markdown (.md, .textpack)
- PDF (via `pypdf`)
- DOCX (via `python-docx`)
- PPTX (via `python-pptx`)
- XLSX (via `openpyxl`)
- Config: `LIGHTRAG_PARSER=*:native-teP;*:legacy-R` (default routing)
- Remote image handling: `NATIVE_MD_IMAGE_DOWNLOAD_ENABLED`, SSRF-guarded

**MinerU (async PDF/document parsing):**
- Modes: Official API or local deployment
- Endpoint: `MINERU_LOCAL_ENDPOINT=http://127.0.0.1:8000` or official
- Auth: `MINERU_API_TOKEN` (official mode)
- Config: `MINERU_API_MODE=local`, `MINERU_LOCAL_BACKEND`, `MINERU_LOCAL_PARSE_METHOD`, `MINERU_LOCAL_IMAGE_ANALYSIS`
- Features: OCR, table extraction, formula recognition, VLM image analysis

**Docling (async document parsing):**
- Endpoint: `http://localhost:5001` (configurable via `DOCLING_ENDPOINT`)
- Auth: None
- Config: `DOCLING_DO_OCR`, `DOCLING_FORCE_OCR`, `DOCLING_DO_FORMULA_ENRICHMENT`, `DOCLING_OCR_PRESET`, polling budget
- Features: OCR, formula enrichment, semantic layout analysis

## Monitoring & Observability

**Error Tracking & Tracing:**

- Langfuse (optional observability)
  - Package: `langfuse` 3.8.1+
  - Endpoint: `https://cloud.langfuse.com` (or self-hosted)
  - Auth: `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`
  - Config: `LANGFUSE_ENABLE_TRACE=true`
  - Features: LLM call tracing, token usage tracking, cost analysis

**Logging:**

- Standard Python logging module (no external dependency)
- Configuration: `LOG_LEVEL`, `VERBOSE`, `LOG_DIR`, `LOG_MAX_BYTES`, `LOG_BACKUP_COUNT`
- Performance timing: `LIGHTRAG_PERFORMANCE_TIMING_LOGS`

**Evaluation (optional):**

- RAGAS (RAG Assessment)
  - Package: `ragas` 0.3.7+
  - Usage: RAG quality metrics (evaluation suite)
  - Config: `EVAL_LLM_MODEL`, `EVAL_EMBEDDING_MODEL`, `EVAL_MAX_CONCURRENT`, `EVAL_QUERY_TOP_K`

## CI/CD & Deployment

**Container Registry:**
- GitHub Container Registry (ghcr.io)
- Image: `ghcr.io/hkuds/lightrag:latest`

**Reverse Proxy:**
- Nginx or Caddy (for multi-instance deployment)
- Config: `LIGHTRAG_API_PREFIX` for site prefix routing

## Environment Configuration

**Required Variables (Core Functionality):**
- `LLM_BINDING`, `LLM_BINDING_HOST`, `LLM_BINDING_API_KEY`, `LLM_MODEL`
- `EMBEDDING_BINDING`, `EMBEDDING_BINDING_HOST`, `EMBEDDING_BINDING_API_KEY`, `EMBEDDING_MODEL`
- `LIGHTRAG_GRAPH_STORAGE`, `LIGHTRAG_VECTOR_STORAGE`, `LIGHTRAG_KV_STORAGE`
- Storage backend config (database connection strings as needed)

**Secrets Location:**
- `.env` file (not committed, local development only)
- Environment variables (production)
- Secrets manager (Docker Compose secrets, Kubernetes secrets)
- No hardcoded API keys in source code

**Workspaces:**
- `WORKSPACE` env var for data isolation (optional)
- Storage backends support per-workspace schemas

## Webhooks & Callbacks

**Incoming:**
- Document upload endpoints: `/documents/upload`, `/documents/upload_url`
- Query endpoints: `/query`, `/query_with_hybrid_search`
- No third-party webhook inbound configured

**Outgoing:**
- None detected in codebase
- Index callbacks: `index_done_callback()` for flush/cleanup (internal event)

---

*Integration audit: 2026-09-03*
