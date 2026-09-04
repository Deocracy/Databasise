<!-- refreshed: 2026-09-03 -->
# Codebase Concerns

**Analysis Date:** 2026-09-03

## Known Bugs & Frozen Defects

**Cozo 0.7.6 Latent Correctness Bugs:**

- **Issue:** Four known silent-wrong-result bugs in frozen Cozo 0.7.6 engine (not data corruption, but incorrect query results)
  - Bug #244: aggregation returning 0 rows (MITIGATED — CozoGraphStorage never uses Cozo count() aggregation)
  - Bug #275: wrong DataValue types on round-trip (MITIGATED — attrs survive round-trip, types asserted in tests)
  - Bug #253: JSON object key-order loss (MITIGATED — consuming as dict, completeness verified)
  - Bug #296/#269: UUID sort/coercion (AVOIDED — all keys stored as Cozo String, never UUID type)
- **Files:** `v1/lightrag/kg/cozo_impl.py`, `v1/tests/kg/test_cozo_frozen_bugs.py`, `databasise/stores/graph.py`, `databasise/tests/stores/test_graph_frozen_bugs.py`
- **Impact:** Silent query result errors if mitigations are bypassed; data correctness depends on maintaining the exact query shapes documented in test_cozo_frozen_bugs.py
- **Status:** PINNED BY DESIGN — Cozo version is frozen at 0.7.6 forever (decision D-P1.1-08, D-05); regression tests lock in mitigations in both v1 and databasise

**LLM Cache Persistence Bug:**

- **Issue:** `LengthFinishReasonError` should not persist into LLM cache, but currently does
- **File:** `v1/lightrag/llm/openai.py:225`
- **Impact:** Cached errors can cause misleading responses on cache hits
- **Priority:** Low — likely edge case related to token length handling

**Phase 3 Entity/Relation Hydration Crashes:**

- **Issue:** Three decomposed query arms (`hybrid`, `local`, `global`) crash before completing retrieval
  - `hybrid`/`local`: node 'entity-hydrate-expand' raises `NodeExecutionError: 'entity_name'`
  - `global`: node 'relation-hydrate-expand' raises `NodeExecutionError: 'src_id'`
- **Files:** `databasise/parts_core/lightrag/entity_hydrate_expand.py`, `databasise/parts_core/lightrag/relation_hydrate_expand.py`
- **Impact:** Cannot measure retrieval-level parity for these arms; they degrade and halt before reaching answer generation
- **Scope:** Out of Phase 3 scope; discovered and documented in `databasise/evidence/PARITY-EVIDENCE.md`'s per-arm degradation notes
- **Priority:** High — blocks Phase 3's full MODAL-01 verification; requires repair before Phase 6's cross-modality comparison

## Tech Debt & Code Complexity

**Overly Large Functions (Ingest Pipeline):**

- **Component:** `merge_nodes_and_edges()` (1,817 lines)
  - File: `v1/lightrag/operate.py:2914-4731`
  - Impact: Core ingest orchestration; extremely difficult to test, refactor, or reason about; single point of failure
  - Dependencies: Calls `_merge_nodes_then_upsert()` (329 lines), `_merge_edges_then_upsert()` (585 lines), heavily coupled
  - Status: MARKED AS OPAQUE (Phase 2 build ladder item 3) — will remain untouched in Databasise 2.0 during decomposition

- **Component:** `_merge_all_chunks()` (1,264 lines)
  - File: `v1/lightrag/operate.py:4731-5995`
  - Impact: Complex multi-stage chunk processing; intertwined extraction, merging, and upsert orchestration
  - Risk: High defect risk if modified; hard to isolate bugs

- **Component:** `_merge_edges_then_upsert()` (585 lines)
  - File: `v1/lightrag/operate.py:2329-2914`
  - Impact: Entity relationship extraction and graph upsert; relies on global concurrency state
  - Risk: Concurrency bugs, race conditions with parallel chunk processing

**Large Utility Modules:**

- `v1/lightrag/utils.py` (5,033 lines): Utility functions scattered across, low cohesion
- `v1/lightrag/lightrag.py` (4,469 lines): Main orchestrator; many concerns mixed (storage init, pipeline orchestration, API surface)
- `v1/lightrag/kg/shared_storage.py` (2,381 lines): Complex concurrency management; multiprocessing + asyncio hybrid

## Architecture & Design Issues

**Hybrid Concurrency Model (Multiprocessing + Asyncio):**

- **Location:** `v1/lightrag/kg/shared_storage.py`
- **Concern:** Mixed multiprocessing.Manager locks and asyncio.Lock objects; requires careful coordination
  - Single-process mode: asyncio.Lock only
  - Multi-process mode: multiprocessing.Manager.Lock + Process-local asyncio.Lock hybrids
  - `UnifiedLock` wrapper attempts to abstract both (L175–390)
- **Risk:** 
  - Deadlocks if async/sync lock boundaries crossed incorrectly
  - Process crashes can leave multiprocessing.Manager locks held indefinitely (no cleanup guaranteed)
  - Context switch between sync and async lock acquisition under high contention could cause performance cliffs
- **Mitigation:** Comprehensive logging available via `DEBUG_LOCKS=True` (`v1/lightrag/kg/shared_storage.py:21`)
- **No Fix in v1:** Design is intentional; Phase 2+ will decompose this

**Global State & Singletons:**

- `v1/lightrag/kg/shared_storage.py`: Module-level singletons for locks, managers, and storage instances
  - `_manager` (Manager instance — multiprocessing)
  - `_registry_guard`, `_internal_lock`, `_data_init_lock` (module-level locks)
  - `_storage_instance` (per-namespace singleton dict)
  - `_global_concurrency_limits` (Dict[str, asyncio.Semaphore])
- **Risk:** Difficult to test in isolation; process lifecycle dependencies; resurrection via `initialize_share_data()` has side effects
- **Impact:** Integration tests must call `finalize_share_data()` then `initialize_share_data()` between test runs (every fixture in test_cozo_frozen_bugs.py does this)

**Broad Exception Catches:**

- **Instances:** ~30 bare `except Exception:` blocks across codebase
- **Files:** `v1/lightrag/llm_roles.py`, `v1/lightrag/api/lightrag_server.py`, `v1/lightrag/utils.py`, `v1/lightrag/kg/shared_storage.py`, etc.
- **Risk:** Hides bugs; swallows OOM errors, KeyboardInterrupt, SystemExit; makes debugging difficult
- **Examples:**
  - `v1/lightrag/llm_roles.py:343` — swallows any exception during LLM role initialization
  - `v1/lightrag/kg/shared_storage.py:213,1766,1784` — swallows storage operation failures
  - `v1/lightrag/utils.py:400, 1923, 1930, 1935, 2061, 2214, 2660, 2674, 2814, 2841` — utility function failures masked

## Databasise (Phase 1) Constraints & Limitations

**Placeholder Trace Fields — Intentional, Phase 2+ Deliverables:**

- **Fields:** `bundle_ref`, `corpus_snapshot_hash`, `tier`, `feed_tier` in run records
- **Location:** `databasise/runner/trace.py` (lines 42-44)
- **Status:** Documented sentinels (`BUNDLE_REF_SENTINEL`, `CORPUS_SNAPSHOT_HASH_SENTINEL`, `TIER_PLACEHOLDER`)
- **Impact:** Emitted run records are schema-valid but carry placeholder values for fields Phase 2 evaluates
  - `bundle_ref`: "sentinel:no-eval-bundle-until-phase-2"
  - `corpus_snapshot_hash`: "sentinel:no-corpus-snapshot-until-phase-2"
  - `tier`/`feed_tier`: "T3" (no scored evidence item flows through a tracer node)
- **Mitigation:** Every placeholder is explicitly documented in `trace.py`'s own module docstring and field defaults
- **No Fix in Phase 1:** By design; Phase 2's RIG machinery will mint real values

**"No External DB Servers" Claim Depends on Dependency List:**

- **Claim:** EMBED-01 requirement: "no external DB servers"
- **Enforcement Location:** `databasise/pyproject.toml` (dependencies only, D-14)
- **Current Runtime Dependencies:** `pycozo[embedded]==0.7.6`, `faiss-cpu>=1.7.0,<2.0.0`, `rfc8785==0.1.4`, `pydantic>=2.0,<3.0`
- **Risk:** If v1's server-dependent dependencies (Neo4j client, asyncpg, pymilvus, etc.) are ever transitively pulled in via a later phase's changes, the embedding nature would revert from property-of-dependency-list to property-of-resolver-decision
- **Mitigation:** D-14 keeps `databasise/` independent from `v1/` workspace; no shared `uv` workspace means v1's server backends don't land on databasise's graph
- **Verification:** `databasise/tools/check_import_boundary.py` enforces no imports from `v1/` at load time

**RFC 8785 (JCS) Config Canonicalisation Thread-Safety:**

- **Location:** `databasise/identity/canon.py:32-35` (`_domain_patch_lock`)
- **Issue:** RFC 8785 library's int64 domain must be temporarily widened to accept CONTRACT-legal signed 64-bit integers
- **Concern:** This widening happens inside a lock; thread-safety is necessary but adds latency on multi-threaded hashing
- **Risk:** If config_hash is called from many threads concurrently (unlikely in asyncio but possible with `loop.run_in_executor`), contention on `_domain_patch_lock` could become a bottleneck
- **Mitigation:** Lock is held only during the hash computation, not the whole canonicalisation; single-threaded asyncio callers never contend
- **Impact:** Low in Phase 1 (tracer is single-threaded); potential concern if future phases use thread pools for config hashing

**FTS5 Availability is Strict (No Fallback):**

- **Location:** `databasise/stores/lexical.py:33-64`
- **Pattern:** SQLite FTS5 availability is checked at store construction, not at query time
- **Behavior:** If FTS5 is unavailable, raises `Fts5UnavailableError` immediately; never silently falls back to LIKE scan
- **Risk:** SQLite builds without FTS5 compiled in will fail store construction, not just fail searches
- **Impact:** Deployment must verify target Python's sqlite3 has FTS5 built in before initializing a lexical store
- **Mitigation:** Error message names FTS5 explicitly and suggests `pip install` of `pycozo[embedded]` (which vendors a compilable sqlite3)

**Ledger Append-Only Design Incomplete for Production:**

- **Location:** `databasise/ledger/ledger.py`
- **Status:** Append-only table is built and tested; SQLite BEFORE UPDATE/DELETE triggers prevent any mutation
- **Missing:** Operator path, `change_origin`, tombstone-lifting prohibition, atomic alias repoint (MACH-07, Phase 7)
- **Scope:** Phase 1 stands the table and projection up; no runner code calls `append()` (only promotions do, and Phase 1 does not exercise real promotion)
- **Risk:** The ledger API is intentionally incomplete; any code attempting to call `ledger.append()` in Phase 1 is an architectural violation

**Cozo Query Shape Constraints are Permanent in databasise:**

- **Issue:** `databasise/stores/graph.py` reproduces v1's Cozo mitigations by copy, not import
- **Testing:** `databasise/tests/stores/test_graph_frozen_bugs.py` explicitly forbids skip/xfail markers (lines 11-13)
- **Risk:** A future adapter reintroducing any of the four frozen bugs would silently produce wrong results, not test failures
- **Mitigation:** Every mitigation in `databasise/stores/graph.py` is documented in its own module docstring; regression suite locks them in
- **Fragility:** If someone refactors the query construction to "improve" it without understanding the frozen bugs, the schema would silently corrupt

**Concurrency is Per-Node, Never Process-Wide:**

- **Design:** D-09 and D-11 explicitly reject a process-wide concurrency cap
- **Implementation:** `databasise/runner/scheduler.py` (lines 1-71 docstring) creates per-node `asyncio.Semaphore` sized from node config
- **Semaphore Exposure:** Exposed as `ctx._semaphore` (private extension attribute, not part of public NodeContext schema)
- **Risk:** A node body that ignores the semaphore and spawns unbounded concurrency will not be throttled by the runner
- **Impact:** LLM rate limits, vector DB connections, and other shared resources can be exhausted by a single misbehaving node
- **Mitigation:** Reference parts use the semaphore; custom bodies must opt in

## Deprecated & Legacy APIs

**Deprecated Methods Still in API:**

- `extract_incremental()` — deprecated, use `insert()` instead (`v1/lightrag/lightrag.py:1497`)
- `aextract_incremental()` — deprecated, use `ainsert()` instead (`v1/lightrag/lightrag.py:1511`)
- `_setup_logger()` — deprecated, use `setup_logger()` in utils instead (`v1/lightrag/lightrag.py:294`)
- `__aexit__` auto-finalize — deprecated; finalize must be called explicitly (`v1/lightrag/lightrag.py:731`)
- `/documents/paginated` endpoint — deprecated API route (`v1/lightrag/api/routers/document_routes.py:3361`)
- `anthropic_embed()` — deprecated alias, removed in next release (`v1/lightrag/llm/anthropic.py:360-371`)
- `PREPROCESSED` status enum — deprecated, use `ANALYZING` instead (`v1/lightrag/base.py:796-803`)

**Impact:** Downstream projects may still call these; removal without grace period will break compatibility

**Deprecated Boolean Flags:**

- `keyword_extraction` boolean in `anthropic_complete_if_cache()` — replaced by response_format parameter
- `entity_extraction` boolean in `anthropic_complete_if_cache()` — replaced by response_format parameter
- Files: `v1/lightrag/llm/anthropic.py:91-103`
- **Risk:** Legacy code path still executed; parameter parsing and validation duplicated

## Performance Bottlenecks

**VDB Upsert Timeouts Under Concurrency:**

- **Location:** `v1/lightrag/operate.py:95-110` (`_get_relationship_vdb_timeout_seconds()`)
- **Issue:** NetworkX storage is in-memory and fast; relationship VDB performs embedding calls + remote I/O. Defensive timeout derived from global config.
- **Risk:** Under high concurrent chunk processing, VDB upserts can timeout, causing partial entity/edge ingestion
- **Current:** Timeout calculation is defensive but opaque; no metrics on actual VDB latency

**Sequential Python-Side Aggregation:**

- **Location:** `v1/lightrag/kg/cozo_impl.py` — `node_degree()`, `get_popular_labels()`
- **Pattern:** Enumerate edges from Cozo, count in Python instead of using SQL COUNT aggregate (due to bug #244)
- **Risk:** O(N) scan for every label popularity query; scales linearly with edge count
- **Impact:** Queries slow down as knowledge graph grows; no index optimization possible

**JSON Repair & String Parsing:**

- **Location:** Multiple LLM completion handlers use `json_repair` + regex post-processing
- **Risk:** LLM-generated JSON corruption is repaired lazily; cascading repairs can mask malformed data
- **Examples:** `_handle_single_entity_extraction()`, `_handle_single_relationship_extraction()`, `_parse_keywords_payload()`
- **Cost:** CPU overhead; no per-handler metrics

**Multi-Stage Extraction Pipeline:**

- **Merge orchestration:** `merge_nodes_and_edges()` coordinates extraction → normalization → merge → upsert across:
  - Entity extraction (LLM call)
  - Relation extraction (LLM call)
  - Keyword extraction (LLM call)
  - Node/edge merge logic (graph storage)
  - Vector DB upserts (two phases: entity embeddings, relation embeddings)
- **Coordination:** Serialized by design; high LLM token cost per chunk
- **Scaling:** Bounded by LLM concurrency limits and embedding throughput

## Fragile Areas & Modification Risks

**Entity Name Length Truncation:**

- **Location:** `v1/lightrag/operate.py:120-160` (`_truncate_entity_identifier()`)
- **Concern:** Entity IDs are truncated to fit MD5 constraints; truncation logic is separate from naming logic
- **Risk:** Two truncation paths exist:
  1. `_truncate_entity_identifier()` — max 256 chars (DEFAULT_ENTITY_NAME_MAX_LENGTH)
  2. Normalization in `_normalize_text_extraction_record_attributes()` — max 512 bytes (DEFAULT_ENTITY_NAME_MAX_BYTES)
- **Fragility:** If either limit is changed without coordinating the other, entity name collisions can occur
- **Tests:** `v1/tests/kg/test_cozo_frozen_bugs.py` validates round-trip but does not stress name collision scenarios

**Chunk Size & Token Truncation:**

- **Functions:** `_truncate_section_context()`, `_truncate_vdb_content()`, others
- **Risk:** Multiple truncation strategies (token-based, char-based, byte-based); if Tokenizer changes, silent data loss
- **Impact:** Extraction quality degrades silently if context is truncated too early

**LLM Completion Parsing:**

- **Pattern:** Multiple fallback strategies for parsing LLM JSON output:
  1. Direct JSON parse
  2. `json_repair` with automatic correction
  3. Regex extraction from markdown code fences
  4. Manual field extraction with defaults
- **Risk:** If LLM format changes, parser may degrade gracefully but silently with incomplete data
- **Example:** `_normalize_keyword_list()` tries four different parse paths (`v1/lightrag/operate.py:4033-4080`)

**Relationship Extraction & Edge Canonicalization:**

- **Location:** `v1/lightrag/kg/cozo_impl.py:63-74` (`_canonical_edge_key()`), `databasise/stores/graph.py:78-84` (copy)
- **Pattern:** Edge direction is normalized; direction reversal is order-dependent
- **Risk:** If edge model changes (e.g., adding direction enum instead of binary swap), silent graph corruption
- **Impact:** Duplicate edges with opposite directions could be created if canonicalization is bypassed

**Configuration & Environment Loading:**

- **Location:** `v1/lightrag/operate.py:87-92` (loads .env from module directory)
- **Concern:** Each LightRAG instance loads its own .env file; instance-specific configs can conflict
- **Risk:** Credential confusion if multiple instances point to different .env files but share storage
- **Mitigation:** OS environment variables take precedence; `.env` is fallback only

## Security Considerations

**No Secrets in Repo (Post-Sanitization):**

- **Status:** Root `.env` removed; credential values in `env.docker-compose-full` blanked
- **Files:** `env.example` documents required keys without values
- **Risk Mitigated:** Secrets are not accidentally committed

**LLM Prompt Injection via Extracted Text:**

- **Pattern:** User documents are extracted → chunked → passed to LLM prompts for entity/relation extraction
- **Mitigation:** Text is sanitized via `sanitize_text_for_encoding()`, `sanitize_and_normalize_extracted_text()` before LLM calls
- **Risk:** If sanitization is incomplete, adversarial document content could inject LLM instructions
- **Files:** `v1/lightrag/utils.py`, multiple call sites in `operate.py`

**SQL-Like Injection via Cozo Queries:**

- **Pattern:** CozoGraphStorage constructs queries with string interpolation (node IDs, edge keys)
- **Defense:** IDs are enforced as canonical strings; no user-supplied SQL/Datalog
- **Risk:** Low — all node IDs are derived from MD5 hashes or entity names; no free-form SQL accepted

**Vector DB Client Credentials:**

- **Location:** Multiple vector DB implementations (Milvus, Weaviate, Qdrant, etc.)
- **Risk:** Credentials passed via environment variables; no per-request auth rotation
- **Impact:** Compromise of any one credential exposes entire vector space

**JWT & API Authentication:**

- **Location:** `v1/lightrag/api/` — uses `python-jose[cryptography]` + `PyJWT` for token handling
- **Risk:** Token expiry and refresh not explicitly shown in config examples; default to long lifetimes if not set
- **Files:** `v1/lightrag/api/config.py`, token validators in routers

## Missing or Incomplete Features

**No Built-In Query Caching:**

- **Status:** LLM call results cached (prompt + completion), but query results not cached
- **Impact:** Identical queries to the same corpus issue new LLM calls every time
- **Workaround:** Would need to implement at API layer or add query-level cache decorator

**No Explicit TTL for Embeddings:**

- **Pattern:** Entity and relation embeddings are computed once and stored; no refresh mechanism
- **Risk:** If embedding model changes, stale embeddings degrade retrieval quality
- **Mitigation:** Requires manual re-extraction and merge to update; no automatic versioning

**Limited Error Recovery:**

- **Pattern:** Failed chunk processing is logged but does not auto-retry with exponential backoff
- **Impact:** Network blips or transient LLM errors can skip document chunks silently
- **Current:** Application must retry entire document manually

**No Multi-Tenancy Isolation:**

- **Pattern:** `namespace` and `workspace` separate storage, but no authorization layer
- **Risk:** If storage is exposed via API, any authenticated user can access any namespace
- **Current:** API does not enforce namespace ACLs; delegated to application layer

## Test Coverage Gaps

**Ingest Pipeline Edge Cases:**

- **Untested:** `merge_nodes_and_edges()` under concurrent chunk streams with LLM rate-limit errors
- **Untested:** Partial entity/edge extraction (one of three LLM calls fails)
- **Untested:** Node merging when extracted entities partially overlap existing graph
- **Risk:** Silent data inconsistency (orphaned edges, duplicate nodes)
- **Files:** `v1/lightrag/operate.py:2914-4731`, `v1/tests/` — no integration tests covering end-to-end concurrency

**Cozo Query Shape Variations:**

- **Covered:** Bug regression tests lock in specific query patterns
- **Uncovered:** Edge enumeration performance with >10M edges; aggregation correctness across shards (if Cozo ever partitions)
- **Files:** `v1/tests/kg/test_cozo_frozen_bugs.py`, `databasise/tests/stores/test_graph_frozen_bugs.py` (comprehensive but narrow scope)

**Multi-Process Lock Scenarios:**

- **Untested:** Process crashes while holding multiprocessing.Manager locks; recovery behavior
- **Untested:** Timeouts on Manager.Lock acquisition under extreme contention
- **Untested:** Context switch between async and sync lock contexts under load
- **Files:** `v1/lightrag/kg/shared_storage.py` — unit tests exist but not stress-tested
- **Risk:** Production deadlocks with no monitoring visibility

**Chunk Truncation Boundaries:**

- **Untested:** Entity name truncation boundary conditions (exactly at 256 char, exactly at 512 byte)
- **Untested:** Section context truncation when context token size equals budget exactly
- **Untested:** VDB content truncation with multi-byte UTF-8 sequences at boundary
- **Risk:** Off-by-one truncation errors, data loss at scale

**Databasise Integration Tests:**

- **Coverage:** Phase 1's four acceptance criteria are tested (transparent wiring, arms wiring, multi-engine touch, artifact registry)
- **Gap:** No stress tests for concurrent node execution with real semaphore contention
- **Gap:** No integration test for ledger append-only correctness under concurrent access (Phase 1 does not exercise real promotion)
- **Gap:** No end-to-end test of artifact scope filtering (write scope vs. discover scope)
- **Gap:** No recovery test for hydration nodes with missing or malformed entity/relation attributes

## Scaling Limits

**Entity Graph Scalability:**

- **Current Limit:** `max_graph_nodes` configuration (default 1,000) enforced
- **Enforcement:** `v1/lightrag/operate.py` — nodes pruned if exceeding limit
- **Issue:** No documented algorithm for which nodes to prune; appears to be FIFO or LRU
- **Risk:** Important entities evicted without warning; query quality degrades silently

**Embedding Vector Dimension:**

- **Current:** Fixed per embedding model (e.g., OpenAI text-embedding-3-small = 1536 dims)
- **Cozo Integration:** Vector DB (Milvus, Qdrant, Faiss) indexed by dimension
- **Risk:** Changing embedding model mid-pipeline requires re-embedding entire corpus and reindexing
- **No Versioning:** No schema migration tool for embedding model changes

**VDB Index Types:**

- **Current Default:** Faiss IndexFlatIP cosine (exact, brute-force L2 dot product) per `databasise/stores/vector.py:14` and `v1/pyproject.toml` comment
- **Limitation:** O(N) per query; no approximate indexes (HNSW, IVF)
- **Scaling:** ~100K vectors practical; >1M vectors become slow
- **Workaround:** Manual index tuning not exposed via API

**Concurrent LLM Calls:**

- **Controlled By:** `MAX_ASYNC_LLM` and per-role `max_async` settings in `v1/lightrag/llm_roles.py`
- **Default:** Falls back to base `MAX_ASYNC_LLM` if unset
- **Risk:** Unbounded concurrency can exhaust LLM rate limits; no adaptive backoff implemented
- **Monitoring:** No built-in metrics on LLM call latency or error rates

## Dependencies at Risk

**Frozen Cozo 0.7.6:**

- **Status:** Pinned forever by design (decision D-P1.1-08, D-05)
- **Risk:** No upstream bug fixes; if critical correctness bug discovered in Cozo, stuck with workaround-in-app
- **Mitigation:** Regression tests lock in known bugs; avoiding those query patterns avoids triggering them
- **Alternative:** HippoRAG 2 reference implementation may use different storage; Phase 3+ may change

**Deprecated LLM SDKs:**

- **OpenAI:** `openai>=2.0.0,<3.0.0` — current but will eventually be EOL
- **Google Genai:** `google-genai>=1.0.0,<3.0.0` — relatively new; may have stability issues
- **Anthropic SDK:** Used only for embedding (deprecated path); LLM calls go through OpenAI SDK
- **Risk:** If LLM provider changes API, downstream code breaks; no abstraction layer

**Pandas Version Constraint:**

- **Current:** `pandas>=2.0.0,<2.4.0` (narrow range)
- **Issue:** Excludes 3.x; compatibility with 2.4+ not tested
- **Risk:** Pandas 2.4+ may introduce breaking changes; codebase will need updates when Pandas 3 ships

**Tenacity (Retry Library):**

- **Usage:** LLM API calls retry with exponential backoff
- **Version:** No constraint; latest version used
- **Risk:** Major version bump could change retry behavior; tests do not mock this lib

**RFC 8785 (JCS) Package:**

- **Status:** Pinned at `==0.1.4` in `databasise/pyproject.toml` (D-05 decision)
- **Risk:** Library is young and may have bugs or breaking changes in minor updates
- **Mitigation:** Pinned version locks behavior; `canonicalise()` contract is frozen per CONTRACT.md §1
- **Dependency Flow:** Only used by databasise, not by v1; no transitive risk

## Operational Concerns

**Gunicorn Timeout Configuration:**

- **Location:** `v1/lightrag/api/run_with_gunicorn.py:223-224`
- **Pattern:** Gunicorn timeout = LLM timeout + 30 seconds
- **Risk:** If LLM call takes exactly timeout time, race condition possible; request cancelled while response being written
- **Mitigation:** 30-second grace period is heuristic; no adaptive adjustment

**Background Process Lifecycle:**

- **Issue:** Multiprocessing.Manager spawns background process; no explicit cleanup if main process crashes
- **Risk:** Orphaned Manager process; zombie processes on unclean shutdown
- **Mitigation:** Cleanup via `finalize_share_data()` — must be called in __del__ or atexit handler (not guaranteed)

**Logging Configuration:**

- **Location:** `v1/lightrag/api/config.py`, `v1/lightrag/utils.py`
- **Pattern:** DEBUG logs are noisy with lock/concurrency details; no separate concurrency trace logger
- **Risk:** Production logs filled with DEBUG_LOCKS output if verbose mode enabled; makes troubleshooting harder

**SQLite Connection Lifecycle in databasise Stores:**

- **Pattern:** Each store (KV, lexical) opens its own SQLite connection at `__init__`, holds it until `finalize()`
- **Risk:** If finalize() is not called, connection remains open indefinitely (SQLite WAL files also held)
- **Mitigation:** Store lifecycle must be coordinated by runner; databasise doesn't provide resource pooling
- **Impact:** Long-running processes accumulating store instances (unlikely in Phase 1, possible if stores are created per-namespace dynamically)

## Stray Artifacts & Environment Issues

**Audit Stderr Output Files:**

- **Files:** `databasise/audit_stderr_bypass.txt`, `audit_stderr_global.txt`, `audit_stderr_hybrid.txt`, `audit_stderr_local.txt`, `audit_stderr_naive.txt` (all empty, Sep 1 2026)
- **Purpose:** Captured stderr from Phase 3 parity comparison runs (one per arm)
- **Status:** Untracked; left in repo by audit/comparison script
- **Impact:** No functional impact; should be gitignored or removed

**Pinned Parity Environment Configuration:**

- **File:** `v1/parity-env.txt` (997 bytes, Sep 1 2026)
- **Purpose:** Frozen config for deterministic parity runs (provider pin, storage family, rerank disabled, LLM cache disabled)
- **Status:** Untracked; symlinked to `v1/.env.parity` for parity run isolation
- **Impact:** Necessary for Phase 3 reproducibility; should be documented and possibly tracked

---

*Concerns audit: 2026-09-03*
