---
last_mapped_commit: 8044f9a
---

# External Integrations

**Analysis Date:** 2026-09-08

## APIs & External Services

**LLM Providers (v1 only; v2 will integrate via OpenAI-compatible base_url):**
- OpenAI - GPT-4, GPT-4o, GPT-4-mini, GPT-5.4, Grok, etc.
  - SDK: `openai` 2.0–3.0
  - Auth: `LLM_BINDING_API_KEY` or `OPENAI_LLM_BINDING_API_KEY`
  - Endpoint: `LLM_BINDING_HOST=https://api.openai.com/v1` (default) or override for OpenRouter, local vLLM, etc.
  - Role-specific config: `KEYWORD_LLM_*`, `QUERY_LLM_*`, `EXTRACT_LLM_*` prefixes
  - Options: temperature, max_tokens, extra_body, reasoning_effort (o1 models)

- Anthropic Claude - Claude 3, Claude 3.5 Sonnet, Opus, Haiku
  - SDK: `anthropic` 0.18–1.0
  - Auth: `LLM_BINDING_API_KEY=<anthropic-key>`
  - Endpoint: Default CloudFront CDN via SDK (no override)
  - Via OpenRouter also supported (set `LLM_BINDING_HOST=https://openrouter.ai/api/v1`)

- Google Gemini - Gemini Flash, Pro, Gemini 2.5, etc.
  - SDK: `google-genai` 1.0–3.0
  - Auth: `LLM_BINDING_API_KEY=<gemini-api-key>`
  - Endpoint: `LLM_BINDING_HOST=DEFAULT_GEMINI_ENDPOINT` (SDK default) or manual
  - Config: GEMINI_LLM_TEMPERATURE, GEMINI_LLM_MAX_OUTPUT_TOKENS, GEMINI_LLM_THINKING_CONFIG (JSON object for thinking budget)
  - Vertex AI support via `GOOGLE_GENAI_USE_VERTEXAI=true` + `GOOGLE_APPLICATION_CREDENTIALS`

- AWS Bedrock - Nova, Claude on Bedrock, Llama 3, etc.
  - SDK: `aioboto3` 12.0–16.0 (async)
  - Auth: AWS_BEARER_TOKEN_BEDROCK or AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY or IAM role
  - Region: `AWS_REGION=us-west-1` (required; Bedrock endpoints are regional)
  - Endpoint: `LLM_BINDING_HOST=DEFAULT_BEDROCK_ENDPOINT`
  - Config: BEDROCK_LLM_TEMPERATURE, BEDROCK_LLM_MAX_TOKENS, BEDROCK_LLM_TOP_P, reasoningConfig (extended thinking)

- Ollama - Local LLM (Qwen 3, Llama 2, Mistral, Phi, etc.)
  - SDK: `ollama` 0.1–1.0
  - Endpoint: `LLM_BINDING_HOST=http://localhost:11434` (default)
  - Config: OLLAMA_LLM_NUM_CTX (required, context window), OLLAMA_LLM_NUM_PREDICT, OLLAMA_LLM_TEMPERATURE, OLLAMA_LLM_STOP

- Voyage AI - Proprietary embeddings
  - SDK: `voyageai` 0.2–1.0
  - Auth: `EMBEDDING_BINDING_API_KEY`
  - Used primarily for embeddings, not LLM generation

- Jina AI - Embeddings and reranking
  - Embeddings: `EMBEDDING_BINDING=jina`
  - Reranking: `RERANK_BINDING=jina`
  - Endpoint: `https://api.jina.ai/v1/...`

- Aliyun Dashscope - Chinese LLM and reranking provider
  - Reranking: `RERANK_BINDING=aliyun`, `RERANK_BINDING_HOST=https://dashscope.aliyuncs.com/api/v1/services/rerank/...`

- Cohere - Reranking only
  - Reranking: `RERANK_BINDING=cohere`, `RERANK_BINDING_HOST=https://api.cohere.com/v2/rerank`
  - Config: RERANK_MODEL (default rerank-v3.5), RERANK_ENABLE_CHUNKING, RERANK_MAX_TOKENS_PER_DOC

- Zhipuai - Chinese LLM provider
  - SDK: `zhipuai` 2.0–3.0

**Embedding Providers (v1 only):**
- OpenAI text-embedding-3-large (default) or text-embedding-3-small
  - Binding: `EMBEDDING_BINDING=openai`
  - Endpoint: `EMBEDDING_BINDING_HOST=https://api.openai.com/v1` (default)
  - Dimensions: EMBEDDING_DIM=3072 (large), supports dynamic dimension via EMBEDDING_SEND_DIM=true
  - Base64 encoding: EMBEDDING_USE_BASE64=true (default, improves performance)

- Ollama embedding models (qwen-embedding:4b, bge-m3, etc.)
  - Binding: `EMBEDDING_BINDING=ollama`
  - Endpoint: `http://localhost:11434` (default)
  - Config: OLLAMA_EMBEDDING_NUM_CTX=8192

- Gemini (google-genai SDK)
  - Binding: `EMBEDDING_BINDING=gemini`
  - Requires EMBEDDING_SEND_DIM=true
  - Dimensions typically 1536

- Bedrock embedding models (amazon.titan-embed-text-v2, etc.)
  - Binding: `EMBEDDING_BINDING=bedrock`
  - Shares AWS region and auth with LLM config

- Jina embedding API
  - Binding: `EMBEDDING_BINDING=jina`
  - Endpoint: `https://api.jina.ai/v1/embeddings`
  - Supports asymmetric mode (EMBEDDING_ASYMMETRIC=true)

- VoyageAI embedding (v2 only, via OpenAI-compatible wrapper)

**Document Parsing Services:**
- MinerU (precision PDF parser)
  - Modes: `MINERU_API_MODE=official` (MinerU Precision API v4) or `local` (self-hosted mineru-api)
  - Official endpoint: `MINERU_OFFICIAL_ENDPOINT=https://mineru.net`, requires `MINERU_API_TOKEN`
  - Local endpoint: `MINERU_LOCAL_ENDPOINT=http://127.0.0.1:8000`
  - Backend options: `hybrid-auto-engine` (VLM + pipeline), `pipeline` (CPU-only), `vlm-auto-engine`
  - OCR: MINERU_LOCAL_PARSE_METHOD (auto, txt, ocr), MINERU_LOCAL_IMAGE_ANALYSIS (VLM for images/charts)
  - Polling: MINERU_POLL_INTERVAL_SECONDS=2, MINERU_MAX_POLLS=600

- Docling (structured PDF to Markdown + JSON)
  - Endpoint: `DOCLING_ENDPOINT=http://localhost:5001`
  - OCR: DOCLING_DO_OCR=true, DOCLING_FORCE_OCR=true, DOCLING_OCR_PRESET (engine selection)
  - Formula enrichment: DOCLING_DO_FORMULA_ENRICHMENT=false (optional)
  - Polling: DOCLING_POLL_INTERVAL_SECONDS=5 (server-side long-poll), DOCLING_MAX_POLLS=240
  - Cache: DOCLING_ENGINE_VERSION (version mismatch forces cache miss)

**Reranking Services (optional):**
- vLLM or SGLang (local deployment)
  - Binding: `RERANK_BINDING=cohere` (OpenAI-compatible API on vLLM)
  - Endpoint: `http://localhost:8000/rerank`
  - Used for vector-based or neural reranking (BAAI/bge-reranker-v2-m3, etc.)

**Image Download & Embedding (Native Markdown):**
- SSRF-guarded external image downloads for native .md files
  - Configuration: NATIVE_MD_IMAGE_DOWNLOAD_ENABLED=true (default), NATIVE_MD_IMAGE_DOWNLOAD_TIMEOUT=30
  - Private/loopback IP guard: NATIVE_MD_IMAGE_ALLOWED_NON_PUBLIC_CIDRS=<comma-sep CIDR list> (optional override)
  - SVG rasterization via cairosvg

## Data Storage

**Graph Databases (pluggable via LIGHTRAG_GRAPH_STORAGE):**
- Cozo (embedded, RocksDB, v1 & v2 default)
  - Connection: In-process, no external service
  - Package: `pycozo[embedded]==0.7.6`
  - Query language: Datalog

- Neo4j (remote, Bolt protocol, 5.0–7.0)
  - Connection: `NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io`
  - Auth: `NEO4J_USERNAME`, `NEO4J_PASSWORD`
  - Config: NEO4J_MAX_CONNECTION_POOL_SIZE=100, NEO4J_CONNECTION_TIMEOUT=30
  - Package: `neo4j` 5.0–7.0

- PostgreSQL (via pgvector extension for both KG and vector)
  - Connection: `POSTGRES_HOST=localhost`, `POSTGRES_PORT=5432`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DATABASE=rag`
  - Vector index type: POSTGRES_VECTOR_INDEX_TYPE (HNSW, IVFFlat, VCHORDRQ)
  - Connection pool & retry: POSTGRES_MAX_CONNECTIONS=25, POSTGRES_CONNECTION_RETRIES=10, exponential backoff
  - Package: `asyncpg` 0.31–1.0, `pgvector` 0.4–1.0

- MongoDB (graph via custom schema)
  - Connection: `MONGO_URI=mongodb://localhost:27017/`, `MONGO_DATABASE=LightRAG`
  - Atlas Vector Search or local MongoDB 5.0+ required for vector operations
  - Package: `pymongo` 4.0–5.0

- OpenSearch (multi-purpose: KV, vector, graph via PPL graphlookup)
  - Connection: `OPENSEARCH_HOSTS=localhost:9200` (comma-sep list)
  - Auth: `OPENSEARCH_USER`, `OPENSEARCH_PASSWORD`, `OPENSEARCH_USE_SSL=true`
  - k-NN index for vectors: OPENSEARCH_KNN_M=16, OPENSEARCH_KNN_EF_CONSTRUCTION=200
  - Package: `opensearch-py` 3.0–4.0

- NetworkX (in-memory, v1 only, testing default)
  - Connection: In-process dictionary
  - Package: `networkx`

**Vector Databases (pluggable via LIGHTRAG_VECTOR_STORAGE):**
- Faiss (embedded, exact IndexFlatIP cosine, v1 & v2 default)
  - Connection: In-process, no external service
  - Package: `faiss-cpu` 1.7.0–2.0.0 (CPU-only by default)
  - Index type: Exact cosine similarity (IndexFlatIP)

- Nano VectorDB (embedded, lightweight fallback)
  - Connection: In-process
  - Package: `nano-vectordb`

- Milvus (remote, gRPC/HTTP)
  - Connection: `MILVUS_URI=http://localhost:19530`, `MILVUS_DB_NAME=lightrag`
  - Auth: `MILVUS_USER`, `MILVUS_PASSWORD`, `MILVUS_TOKEN` (optional)
  - MinIO S3 storage (Milvus dependency): `MINIO_ACCESS_KEY_ID`, `MINIO_SECRET_ACCESS_KEY`
  - Index config: MILVUS_INDEX_TYPE (AUTOINDEX, HNSW, IVF_FLAT, DISKANN), MILVUS_METRIC_TYPE (COSINE, L2, IP)
  - Upsert batching: MILVUS_UPSERT_MAX_PAYLOAD_BYTES=33554432, MILVUS_UPSERT_MAX_RECORDS_PER_BATCH=128
  - Package: `pymilvus` 2.6.2–4.0

- Qdrant (remote, gRPC/HTTP)
  - Connection: HTTP API (gRPC also supported)
  - Config: Snapshot management, collection recreation on schema mismatch
  - Package: `qdrant-client` 1.11–2.0

- PostgreSQL pgvector (same as graph DB, but vector-specific operations)
  - Index types: HNSW (recommended), IVFFlat (approximate), VCHORDRQ (experimental)
  - HNSW tuning: POSTGRES_HNSW_M=16, POSTGRES_HNSW_EF=200

- MongoDB Atlas Vector Search
  - Connection: Same as graph MongoDB (`MONGO_URI`)
  - Requires Atlas Search feature enabled

- OpenSearch k-NN (same as graph OpenSearch, but vector-specific operations)
  - Plugin: requires OpenSearch k-NN plugin installed
  - Approximate nearest neighbor search via HNSW or Faiss plugin

**Key-Value Storage (pluggable via LIGHTRAG_KV_STORAGE):**
- JSON files (v1 default for testing)
  - Connection: Local filesystem, `./rag_storage/<workspace>/kv/`
  - Storage type: `JsonKVStorage`

- PostgreSQL (same connection as graph/vector, separate table namespace)
  - Storage type: `PostgresKVStorage`
  - Supports key filtering and batch operations

- MongoDB
  - Storage type: `MongoKVStorage`
  - Batch write limits: MONGO_UPSERT_MAX_RECORDS_PER_BATCH=128

- Redis
  - Connection: `REDIS_HOST=localhost`, `REDIS_PORT=6379`, `REDIS_PASSWORD` (optional)
  - Package: `redis` 5.0–9.0
  - Expiration: Configurable TTL per key

- OpenSearch
  - Storage type: `OpenSearchKVStorage`
  - Same connection as graph/vector OpenSearch

**Document Status Storage (pluggable via LIGHTRAG_DOC_STATUS_STORAGE):**
- JSON files (default)
  - Storage type: `JsonDocStatusStorage`
  - Location: `./rag_storage/<workspace>/doc_status/`

- PostgreSQL
  - Storage type: `PostgresDocStatusStorage`
  - Tracks parse, analyze, insert stages and error messages per document

- MongoDB
  - Storage type: `MongoDocStatusStorage`

- Redis
  - Storage type: `RedisDocStatusStorage`
  - TTL-based expiration for doc status records

## Caching & Session Management

**LLM Response Cache:**
- Enabled by default: `ENABLE_LLM_CACHE=true` (v1)
- Backend: Same as selected KV storage
- Cache key: Identity hash of input content (via `get_llm_cache_identity()`)
- Invalidation: `index_done_callback()` on document completion or explicit cache flush
- Disabled: For streaming responses (incompatible with incremental output)

**Tiktoken Cache:**
- Pre-cached in Docker: `/app/data/tiktoken/`
- Offline mode: Download via `lightrag-download-cache --cache-dir /app/data/tiktoken`
- Directory: `TIKTOKEN_CACHE_DIR=/app/data/tiktoken` (optional, speeds up token counting)

## Authentication & Identity

**API Authentication (v1):**
- Type: Custom bearer token or API key
- Header: `X-API-Key: <token>`
- Alternative: JWT token in Authorization header
- JWT Secret: `TOKEN_SECRET=lightrag-jwt-default-secret-key!`
- Algorithm: `JWT_ALGORITHM=HS256`
- Expiration: `TOKEN_EXPIRE_HOURS=48` (sliding window auto-renewal if `TOKEN_AUTO_RENEW=true`)

**User Accounts (v1):**
- Format: `AUTH_ACCOUNTS='admin:admin123,user1:{bcrypt}$2b$...'`
- Password hashing: bcrypt via `bcrypt` 4.0+
- Guest tokens: `GUEST_TOKEN_EXPIRE_HOURS=24` (optional shorter expiry)

## Monitoring & Observability

**Logging (v1):**
- Framework: Standard `logging` module (no external aggregation in dependencies)
- Level: `LOG_LEVEL=INFO` (default)
- Output: Console + file (if `LOG_DIR=/path/to/log` set)
- Performance timing: `LIGHTRAG_PERFORMANCE_TIMING_LOGS=false` (optional, records LLM/vector/graph latencies)
- File rotation: `LOG_MAX_BYTES=10485760` (10MB), `LOG_BACKUP_COUNT=5`

**Tracing & Eval (optional):**
- Langfuse (optional): `langfuse` 3.8.1+ for LLM trace/eval platform integration
  - Not in default pyproject.toml, installed separately if needed
  - Used for tracing query execution and LLM calls

**No Built-in Metrics:**
- Prometheus/Grafana: Not included; can be added via reverse proxy or sidecar
- Datadog, New Relic: Not included; API calls can be instrumented separately

## CI/CD & Deployment

**Hosting (Development & Production):**
- Production Docker image: Multi-stage (Bun → uv Python → python:3.12-slim)
- Entrypoint: `gunicorn --workers N --timeout 150 --bind 0.0.0.0:9621 lightrag.api.lightrag_server:app`
  - Or: `uvicorn lightrag.api.lightrag_server:app --host 0.0.0.0 --port 9621`
- Reverse proxy (optional): nginx, Caddy (for SSL, multi-site via LIGHTRAG_API_PREFIX, rate limiting)

**No Built-in CI/CD:**
- git hooks: `pre-commit` framework (linting, formatting enforcement at commit time)
- Makefiles: Developer task automation (build, test, serve, etc.)
- GitHub Actions, GitLab CI, etc.: Not present; can be added externally

**Offline Deployment:**
- Vendor dependencies: `uv sync --offline` with pre-cached wheels in Docker build
- Pre-cache tiktoken: `lightrag-download-cache` utility
- No internet access required after Docker image build (dependencies and models pre-staged)

## Webhooks & Callbacks

**Incoming Webhooks:**
- Not implemented in v1
- REST endpoints can be called externally (POST /query, POST /documents, etc.)

**Outgoing Webhooks:**
- Document status callbacks: `index_done_callback()` fired when document parsing/analysis completes
  - Used internally to flush LLM cache and update doc status
  - No external webhook integration currently

**Async Document Processing Callbacks:**
- MinerU/Docling task polling: Client polls `/v1/status/poll/{task_id}` for async parse completion
- No push notification; pull-based polling only

---

*Integration audit: 2026-09-08*
