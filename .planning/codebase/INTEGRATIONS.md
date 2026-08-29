# External Integrations

**Analysis Date:** 2026-08-29

## APIs & External Services

**LLM Providers (Switchable):**

Query-side LLM (entity extraction, keyword generation):
- OpenAI - Default. API: `https://api.openai.com/v1`. Auth: `OPENAI_API_KEY`. Models: `gpt-4o-mini` (default), `gpt-4o`, o1 family.
  - Client: `openai` package
  - Env vars: `LLM_BINDING=openai`, `LLM_BINDING_HOST`, `LLM_BINDING_API_KEY`, `LLM_MODEL`, `LLM_TIMEOUT`, `MAX_ASYNC_LLM`
  - Role-specific: `QUERY_LLM_*`, `KEYWORD_LLM_*` prefixes
  - Features: Streaming, `max_completion_tokens` (o1+), reasoning effort, reasoning control via `OPENAI_LLM_EXTRA_BODY`

- Azure OpenAI - Production enterprise. API: `https://<resource>.openai.azure.com/`. Auth: `AZURE_OPENAI_API_KEY`.
  - Client: `openai` package (Azure-specific endpoint handling)
  - Env vars: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION`
  - Note: Deployment name used as model identifier

- Google Gemini - Via Google AI Studio or Vertex AI. API: Auto-detected SDK or `https://generativelanguage.googleapis.com`.
  - Client: `google-genai` package
  - Auth: `GEMINI_API_KEY` (AI Studio) or `GOOGLE_APPLICATION_CREDENTIALS` (Vertex AI)
  - Env vars: `LLM_BINDING=gemini`, `LLM_MODEL=gemini-flash-latest`, `GEMINI_LLM_THINKING_CONFIG` (reasoning budget)
  - Vertex AI: Requires `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_GENAI_USE_VERTEXAI=true`

- Anthropic Claude - Via Bedrock or native API. Auth: `ANTHROPIC_API_KEY` or AWS credentials.
  - Client: `anthropic` package
  - Env vars: `LLM_BINDING=bedrock`, `LLM_MODEL=us.anthropic.claude-*-v1:0`
  - AWS Bedrock: `AWS_REGION`, `AWS_BEARER_TOKEN_BEDROCK` or IAM credentials, Bedrock-specific reasoning config

- Ollama - Local LLM. API: `http://localhost:11434` (default).
  - Client: `ollama` package
  - Env vars: `LLM_BINDING=ollama`, `LLM_BINDING_HOST`, `LLM_MODEL=qwen3.5:9b`, `OLLAMA_LLM_NUM_CTX`
  - Note: `OLLAMA_EMULATING_MODEL_TAG=latest` for model registry

- OpenRouter (OpenAI-compatible) - Route to 200+ models via one API. Auth: `OPENROUTER_API_KEY`.
  - Client: `openai` package with custom endpoint
  - Env vars: `LLM_BINDING=openai`, `LLM_BINDING_HOST=https://openrouter.ai/api/v1`, routing via model name

- AWS Bedrock - Unified AI service. Auth: IAM credentials or bearer token.
  - Client: Via `bedrock` binding and `aioboto3` (async)
  - Env vars: `LLM_BINDING=bedrock`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `AWS_BEARER_TOKEN_BEDROCK`
  - Models: Claude, Nova, Llama family

- LLaMA Index - Framework wrapper. Client: `llama-index`, `llama-index-llms-openai`

- ZhipuAI (Zhipu Claude) - Chinese provider. Auth: `ZHIPUAI_API_KEY`.
  - Client: `zhipuai` package
  - Env vars: `LLM_BINDING` not exposed; used via LLaMA Index

**Embedding Providers (Switchable):**

- OpenAI - Default embeddings. API: `https://api.openai.com/v1`. Model: `text-embedding-3-large` (3072 dims, default).
  - Client: `openai` package
  - Env vars: `EMBEDDING_BINDING=openai`, `EMBEDDING_BINDING_HOST`, `EMBEDDING_BINDING_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIM`, `EMBEDDING_SEND_DIM=false` (OpenAI ignores dim param by default)
  - Features: Base64 encoding (`EMBEDDING_USE_BASE64=true` default), dynamic dimension adjustment, asymmetric embeddings

- Azure OpenAI - Embeddings. API: `https://<resource>.openai.azure.com/`. Auth: `AZURE_EMBEDDING_DEPLOYMENT`.
  - Env vars: `EMBEDDING_BINDING=azure_openai`, `AZURE_EMBEDDING_API_VERSION`

- Ollama - Local embeddings. API: `http://localhost:11434` (default). Model: `qwen3-embedding:4b` (2560 dims).
  - Env vars: `EMBEDDING_BINDING=ollama`, `EMBEDDING_BINDING_HOST`, `EMBEDDING_MODEL`, `OLLAMA_EMBEDDING_NUM_CTX`

- Google Gemini - Embeddings. Auth: `GEMINI_API_KEY`. Model: `gemini-embedding-001` (1536 dims).
  - Env vars: `EMBEDDING_BINDING=gemini`, `EMBEDDING_SEND_DIM=true` (Gemini requires dimension)

- Jina AI - Asymmetric embeddings. API: `https://api.jina.ai/v1/embeddings`. Model: `jina-embeddings-v4` (2048 dims).
  - Auth: `EMBEDDING_BINDING_API_KEY`
  - Env vars: `EMBEDDING_BINDING=jina`

- VoyageAI - Asymmetric embeddings. Auth: `VOYAGEAI_API_KEY`.
  - Client: `voyageai` package
  - Supports task-specific embeddings (query vs. document)

- AWS Bedrock - Embeddings. Model: `amazon.titan-embed-text-v2:0` (1024 dims).
  - Env vars: `EMBEDDING_BINDING=bedrock`, `AWS_REGION`, AWS credentials (shared with LLM)

- vLLM/SGLang (OpenAI-compatible local) - Self-hosted embeddings. API: `http://localhost:8001` (default).
  - Env vars: `VLLM_EMBED_MODEL=BAAI/bge-m3`, `VLLM_EMBED_PORT=8001`, `VLLM_EMBED_DEVICE=cpu|cuda`, `VLLM_EMBED_API_KEY`, `VLLM_USE_CPU`

**Reranking Services (Optional, Switchable):**

- Cohere Rerank - API: `https://api.cohere.com/v2/rerank`. Model: `rerank-v3.5`.
  - Auth: `RERANK_BINDING_API_KEY`
  - Env vars: `RERANK_BINDING=cohere`, `RERANK_BINDING_HOST`, `RERANK_MODEL`, `RERANK_ENABLE_CHUNKING=true`, `RERANK_MAX_TOKENS_PER_DOC`

- Jina Rerank - API: `https://api.jina.ai/v1/rerank`. Model: `jina-reranker-v2-base-multilingual`.
  - Auth: `RERANK_BINDING_API_KEY`
  - Env vars: `RERANK_BINDING=jina`

- Aliyun DashScope - API: `https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank`. Model: `gte-rerank-v2`.
  - Auth: `RERANK_BINDING_API_KEY`
  - Env vars: `RERANK_BINDING=aliyun`

- vLLM/SGLang (OpenAI-compatible local) - Self-hosted reranking. API: `http://localhost:8000/rerank` (default).
  - Env vars: `RERANK_BINDING=cohere` (vLLM exposes Cohere-compatible API), `VLLM_RERANK_MODEL`, `VLLM_RERANK_PORT`, `VLLM_RERANK_DEVICE`, `VLLM_RERANK_API_KEY`

## Data Storage

**Databases (Switchable, configured at startup):**

**Graph/KG Storage:**
- Cozo (CozoDB) - Default embedded graph database. Embedded in process, RocksDB backend, MPL-2.0 (file-level weak copyleft).
  - Connection: In-process, no credentials required
  - Implementation: `v1/lightrag/kg/cozo_impl.py` (the Sourcerer fork's differentiator)
  - State: Default for v1; planned opaque-side node in 2.0 architecture

- Neo4j - Enterprise graph database. Protocol: `neo4j+s://` (TLS) or `neo4j://` (plain).
  - Connection: `NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io`
  - Auth: `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`
  - Env: `NEO4J_MAX_CONNECTION_POOL_SIZE=100`, `NEO4J_CONNECTION_TIMEOUT`, `NEO4J_KEEP_ALIVE`
  - Client: `neo4j` package
  - Implementation: `v1/lightrag/kg/neo4j_impl.py`

- Memgraph - Open-source Cypher-compatible graph DB. Protocol: `bolt://`.
  - Connection: `MEMGRAPH_URI=bolt://localhost:7687`
  - Auth: `MEMGRAPH_USERNAME`, `MEMGRAPH_PASSWORD`, `MEMGRAPH_DATABASE`
  - Client: Neo4j-compatible protocol
  - Implementation: `v1/lightrag/kg/memgraph_impl.py`

- NetworkX (In-memory) - Graph algorithms library, fast for prototyping.
  - Default for quick-start (dev/test only)
  - Implementation: `v1/lightrag/kg/networkx_impl.py`

**Vector Storage:**
- Nano VectorDB - In-process vector database (default fallback).
  - Connection: File-based, local to application
  - Implementation: `v1/lightrag/kg/nano_vector_db_impl.py`
  - Similarity: Cosine (faiss-compatible)

- FAISS (IndexFlatIP) - Facebook similarity search, CPU-based, exact cosine.
  - Connection: In-process, no credentials
  - Implementation: `v1/lightrag/kg/faiss_impl.py`
  - Note: `faiss-cpu` package (no GPU required)

- PostgreSQL with pgvector - Vector extension for PostgreSQL.
  - Connection: `postgresql://user:password@host:5432/database`
  - Env vars: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DATABASE`, `POSTGRES_MAX_CONNECTIONS`
  - Vector index: `POSTGRES_VECTOR_INDEX_TYPE=HNSW|IVFFlat|VCHORDRQ` (default HNSW)
  - Batching: `POSTGRES_UPSERT_MAX_PAYLOAD_BYTES`, `POSTGRES_UPSERT_MAX_RECORDS_PER_BATCH`
  - SSL: `POSTGRES_SSL_MODE=require`, `POSTGRES_SSL_CERT`, `POSTGRES_SSL_KEY`, `POSTGRES_SSL_ROOT_CERT`
  - HA: Connection retry config: `POSTGRES_CONNECTION_RETRIES=10`, `POSTGRES_CONNECTION_RETRY_BACKOFF=3.0`
  - Client: `asyncpg` (async), `pgvector` (Python bindings)
  - Implementation: `v1/lightrag/kg/postgres_impl.py`

- Milvus - Vector database service. Protocol: gRPC.
  - Connection: `MILVUS_URI=http://localhost:19530`
  - Auth: `MILVUS_USER`, `MILVUS_PASSWORD`, `MILVUS_TOKEN`
  - Database: `MILVUS_DB_NAME=lightrag`
  - Vector index: `MILVUS_INDEX_TYPE=AUTOINDEX|HNSW|IVF_FLAT` (default AUTOINDEX)
  - Metric: `MILVUS_METRIC_TYPE=COSINE|L2|IP` (default COSINE)
  - Batching: `MILVUS_UPSERT_MAX_PAYLOAD_BYTES`, `MILVUS_UPSERT_MAX_RECORDS_PER_BATCH`
  - MinIO dependency: `MINIO_ACCESS_KEY_ID`, `MINIO_SECRET_ACCESS_KEY`
  - Client: `pymilvus` package
  - Implementation: `v1/lightrag/kg/milvus_impl.py`

- Qdrant - Vector database service. Protocol: HTTP/gRPC.
  - Connection: `QDRANT_URL=http://localhost:6333`
  - Auth: `QDRANT_API_KEY` (optional)
  - Vector index: HNSW algorithm (Qdrant default)
  - Batching: `QDRANT_UPSERT_MAX_PAYLOAD_BYTES`, `QDRANT_UPSERT_MAX_POINTS_PER_BATCH`
  - Client: `qdrant-client` package
  - Implementation: `v1/lightrag/kg/qdrant_impl.py`

- OpenSearch - Search/vector engine. Protocol: HTTP.
  - Connection: `OPENSEARCH_HOSTS=localhost:9200` (comma-separated hosts)
  - Auth: `OPENSEARCH_USER`, `OPENSEARCH_PASSWORD`
  - SSL: `OPENSEARCH_USE_SSL=true`, `OPENSEARCH_VERIFY_CERTS=false`
  - Vector index: k-NN with HNSW. Params: `OPENSEARCH_KNN_EF_CONSTRUCTION`, `OPENSEARCH_KNN_M`, `OPENSEARCH_KNN_EF_SEARCH`
  - Batching: `OPENSEARCH_UPSERT_MAX_PAYLOAD_BYTES`, `OPENSEARCH_UPSERT_MAX_RECORDS_PER_BATCH`
  - Client: `opensearch-py` package
  - Implementation: `v1/lightrag/kg/opensearch_impl.py`

**Key-Value/Document Storage:**
- JSON (File-based) - Default development storage. No credentials.
  - Implementation: `v1/lightrag/kg/json_kv_impl.py`

- MongoDB/MongoDB Atlas - Document database.
  - Connection: `MONGO_URI=mongodb://localhost:27017/` or Atlas connection string
  - Database: `MONGO_DATABASE=LightRAG`
  - Vector Search: Atlas Vector Search or MongoDB Vector Search required
  - Batching: `MONGO_UPSERT_MAX_PAYLOAD_BYTES`, `MONGO_UPSERT_MAX_RECORDS_PER_BATCH`
  - Client: `pymongo` package
  - Implementation: `v1/lightrag/kg/mongo_impl.py`

- Redis - In-memory KV store/cache.
  - Connection: `REDIS_URI=redis://localhost:6379`
  - Timeouts: `REDIS_SOCKET_TIMEOUT`, `REDIS_CONNECT_TIMEOUT`
  - Pool: `REDIS_MAX_CONNECTIONS`, `REDIS_RETRY_ATTEMPTS`
  - Client: `redis` package
  - Implementation: `v1/lightrag/kg/redis_impl.py`

**Document Status Storage:**
- JSON (File-based) - Default. Tracks ingestion pipeline state per document.
  - Implementation: `v1/lightrag/kg/json_doc_status_impl.py`

**File Storage:**
- Local filesystem - Default. Configured via `INPUT_DIR`, `WORKING_DIR`, `PROMPT_DIR` env vars.
- S3/Bedrock integration - Implicit via `aioboto3` if using Bedrock LLM or embedding.

## Authentication & Identity

**API Authentication:**
- JWT Tokens - HTTP `Authorization: Bearer <token>` header.
  - Secret: `TOKEN_SECRET=lightrag-jwt-default-secret-key!`
  - Algorithm: `JWT_ALGORITHM=HS256` (default)
  - Expiry: `TOKEN_EXPIRE_HOURS=48` (default), `GUEST_TOKEN_EXPIRE_HOURS=24`
  - Auto-renewal: `TOKEN_AUTO_RENEW=true`, `TOKEN_RENEW_THRESHOLD=0.5` (renew at 50% time remaining)
  - Generated by: `PyJWT` package with `python-jose` crypto backend

- API Keys - HTTP `X-API-Key: <key>` header.
  - Key config: `LIGHTRAG_API_KEY=your-secure-api-key-here`
  - Whitelist paths (no auth): `WHITELIST_PATHS=/health,/api/*`
  - Rate limiting: Auto-skipped for `/health`, `/documents/paginated`, `/documents/pipeline_status` (60s min between renewals)

- Basic Auth (Legacy) - HTTP `Authorization: Basic <base64(user:password)>`.
  - User config: `AUTH_ACCOUNTS='admin:admin123,user1:{bcrypt}$2b$12$...'`
  - Password hashing: bcrypt (sha256 pre-hash)
  - Generated by: `lightrag-hash-password` CLI tool
  - Client: `bcrypt` package

**LLM Provider Authentication:**
- API Keys passed via environment: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, etc.
- AWS credentials for Bedrock: IAM, STS, instance profile, SSO, or `AWS_BEARER_TOKEN_BEDROCK`
- Service account JSON for Google Vertex AI: `GOOGLE_APPLICATION_CREDENTIALS`

## Monitoring & Observability

**Error Tracking:**
- Not built-in; manual integration via logging or external SIEMs

**Logs:**
- File-based (default) - Location: `LOG_DIR` env var (defaults to cwd)
- Structured logging: `LOG_LEVEL=INFO|DEBUG`, `LOG_MAX_BYTES=10485760`, `LOG_BACKUP_COUNT=5`
- Performance timing: `LIGHTRAG_PERFORMANCE_TIMING_LOGS=false` (optional per-call instrumentation)

**Tracing & Observability:**
- Langfuse - LLM trace/eval platform (optional, install `lightrag-hku[observability]`).
  - Auth: `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`
  - Endpoint: `LANGFUSE_HOST='https://cloud.langfuse.com'` (or self-hosted)
  - Enable: `LANGFUSE_ENABLE_TRACE=true`
  - Scope: OpenAI-compatible LLMs only

## CI/CD & Deployment

**Hosting:**
- Docker (preferred) - Multi-stage Dockerfile building Python 3.12-slim image with pre-built frontend assets
- Bare metal - Python 3.12+ environment with uv or pip install
- Kubernetes - Docker image deployable via Helm (not included; external)

**CI Pipeline:**
- Not configured in repo; pre-commit hooks available via `pyproject.toml[pytest]`
- Git hooks: `pre-commit` framework (`.pre-commit-config.yaml`)
  - Linting: `ruff` (Python)
  - Formatting: `black` (implied), `prettier` (frontend)

**Application Server:**
- Gunicorn - Multi-worker ASGI server (production). Workers: `WORKERS=2` (default), timeout `TIMEOUT=150s`.
  - Command: `lightrag-gunicorn` (entrypoint from `pyproject.toml`)
  - Per-worker async concurrency: `MAX_ASYNC_LLM`, `MAX_ASYNC_RERANK` (cross-worker global cap enforced)
  - Graceful shutdown: Lease heartbeats for abandoned requests

- Uvicorn - Single-worker ASGI server (development). Concurrency: `MAX_ASYNC_LLM`.
  - Command: `lightrag-server` (entrypoint from `pyproject.toml`)

**Port & Network:**
- API server: `HOST=0.0.0.0`, `PORT=9621` (default)
- SSL: `SSL=true`, `SSL_CERTFILE`, `SSL_KEYFILE` (optional)
- CORS: `CORS_ORIGINS=http://localhost:3000,http://localhost:8080` (configurable)
- Path prefix: `LIGHTRAG_API_PREFIX=/site01` (for reverse-proxy routing by prefix)

## Webhooks & Callbacks

**Incoming:**
- Not explicitly implemented; all operations are request/response or streaming.

**Outgoing:**
- Not implemented in v1; 2.0 architecture (CONTRACT.md) proposes seam-level trace events and mutation logging.

## External Services Implied by 2.0 Architecture

Per `docs/system-model/CONTRACT.md` and `PARTS.md`, the 2.0 modality-swap design anticipates:

**Machine Boundary (Admission § 8/§17):**
- Foreign-hosted LLM endpoint injection (e.g., external OpenAI server or competitor) for architecture comparison
- Opaque query adapters (e.g., HippoRAG 2 via native igraph + OpenIE, LightRAG ingest core as quarantined node)

**Cost Model (RIG.md § CM.3 residual inputs A1-A4):**
- LLM token counting (calibrated to tokenizer, currently heuristic-based)
- LLM output size estimation (4-1,500 tokens per gleaning call, 400-1,500 default)
- Index-side mutation measurement (unmeasured, deferred to build phase)

**Evaluation (RIG.md § EV.1):**
- RAGAS evaluation bundle (dev/holdout/sealed splits)
- Judge implementation for self-disagreement measurement (optional, deferred)

---

*Integration audit: 2026-08-29*
