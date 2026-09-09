# API Coverage — Phase 5: Opaque-Side Admission

## This phase consumes external surfaces — unlike Phase 4, which only exposed one

Phase 4's own `COVERAGE.md` opens by stating it integrates no third-party API — it builds the
machine's own consumer-facing seam. Phase 5 is the opposite shape: this phase's adapter
(`databasise/foreign/codebase_memory_mcp_adapter.py`) calls a third-party engine's own served MCP
tool surface directly, and admits a second in-repo engine (`codebase-memory-mcp`) whole, across a
process boundary, alongside the LightRAG corpus-side subprocess boundary plans 05-01/05-03/05-04
already built. This is therefore a real capability matrix, not a no-integration declaration —
every row below states a genuine consume/opt-out decision against a live-enumerated surface, never
a remembered one.

## 1. codebase-memory-mcp's tool surface

Enumerated from a live `list_tools()` call against the installed binary this session — never from
memory or from a docs list. **Version: `codebase-memory-mcp 0.10.8`** (installed at
`/home/chris/.local/bin/codebase-memory-mcp`; `PARTS.md ## §X`'s eleven verdicts were code-verified
against the pinned clone `codebase-memory-mcp@61b3b1b2` — the version drift between the two, and
the confirmation that the tool surface itself has not moved between them, is recorded in full in
`databasise/evidence/ADMISSION-CODEBASE-MEMORY-MCP.md`).

`INTEGRATE` is the default decision; every `OPT-OUT` carries a one-line reason — an opt-out with no
reason is the undecided hole this matrix exists to close.

| tool | decision | reason |
|---|---|---|
| `index_repository` | INTEGRATE | The admitting machine's own §8 condition 4 ceiling measurement (`databasise/parts_core/codebase_memory_mcp.py`) and Falsifier 4's native-chunking leg both call it directly against a real repository (`FALSIFIER-4-EVIDENCE.md`). |
| `search_graph` | INTEGRATE | One of Falsifier 4's three named evidence-returning tools (the "graph search" tool); normalizes to `graph_path` (`normalise_to_item_kind`), exercised against committed fixtures and a live re-run. |
| `get_code_snippet` | INTEGRATE | Falsifier 4's "code snippet" tool; normalizes to `code_snippet` and is the only tool this session's adapter derives a `content_hash` from (its raw output is the only one carrying the symbol's actual source text). |
| `search_code` | INTEGRATE | Falsifier 4's "code search" tool; normalizes to `code_snippet`, exercised against committed fixtures. |
| `trace_path` | INTEGRATE | Normalizes to `graph_path`; the adapter's own `_parse_tool_text` does not match this tool's nested per-module grouping format, so it normalizes via the tool-name mapping over a `_raw_text` fallback item rather than a parsed row — recorded as a real, observed rendering-format limitation, not silently worked around. |
| `query_graph` | INTEGRATE | Normalizes to `graph_path`; its Cypher-query result rows do parse via the adapter's `"cols:"` table convention, exercised against a committed fixture. |
| `get_architecture` | INTEGRATE | Normalizes to `derived_finding` (a computed summary over the whole indexed graph, carrying `derived_from` naming the project); exercised against a committed fixture. |
| `get_graph_schema` | INTEGRATE | Normalizes to `derived_finding`; populates `structured_content` (one of the six tools that do), exercised against a committed fixture. |
| `list_projects` | INTEGRATE | Normalizes to `derived_finding`; exercised against a committed fixture (trimmed to this project's own entry before committing — see `tests/fixtures/codebase_memory_mcp_raw_items.json`'s own note). |
| `index_status` | INTEGRATE | Normalizes to `derived_finding`; used to confirm the live tool surface and node/edge counts this session. |
| `check_index_coverage` | INTEGRATE | Normalizes to `derived_finding`; populates `structured_content`, exercised against a committed fixture. |
| `detect_changes` | INTEGRATE | Normalizes to `derived_finding`; its own text format ("`rows:`", not "`cols:`") does not match the adapter's parser, so — like `trace_path` — it normalizes via the tool-name mapping over a `_raw_text` fallback rather than a parsed row. |
| `manage_adr` | OPT-OUT | `PARTS.md ## §X`'s X1 mutation-surface repair already documents this as an active mutator (writes into the SQLite `project_summaries` table) and is why `CODEBASE_MEMORY_MCP_PART` declares `mutates_store`. The mutation surface is admitted and declared this phase, not driven — nothing in this phase calls it. |
| `delete_project` | OPT-OUT | The second, more destructive active mutator §X's X1 repair names. Same disposition as `manage_adr`: declared and admitted, not driven. |
| `ingest_traces` | OPT-OUT | Confirmed a no-op stub with zero store side effect at the pinned SHA (`PARTS.md ## §X`'s mutation-surface scan) and unchanged behaviorally at the installed 0.10.8 binary (tool surface comparison, `ADMISSION-CODEBASE-MEMORY-MCP.md`) — there is no implemented feature here to integrate against. |

Row count: **15**, equal to the live `list_tools()` call's own tool count.

## 2. v1 LightRAG's corpus-side API

The operations this phase (plans 05-01, 05-03, 05-04) consumes across the v1 subprocess boundary
(`databasise/foreign/v1_corpus_driver_script.py`), called against v1's own `LightRAG` facade —
never reimplemented, never wrapped in a machine-side equivalent.

| v1 operation | decision | reason |
|---|---|---|
| `apipeline_enqueue_documents` | INTEGRATE | The ingest port's first pipeline stage (05-01); returns v1's own `track_id`. |
| `apipeline_process_enqueue_documents` | INTEGRATE | The ingest port's extraction/graph-upsert stage (05-01) — the ~1,786-line opaque core this phase admits, not decomposed. |
| `adelete_by_doc_id` | INTEGRATE | The delete port's whole operation (05-03) — v1's own graph-aware reference-counting algorithm, exercised against a real corpus, never reimplemented. |
| `get_processing_status` | INTEGRATE | The status port's whole-corpus counts (05-04's `corpus_status`/`document_counts`). |
| `aget_docs_by_track_id` | INTEGRATE | The job-status port's per-job document list when a `track_id` is known (05-04's `get_job_status`). |
| `doc_status.get_docs_by_statuses` | INTEGRATE | The corpus-status port's whole-corpus document list when no `track_id` is given (05-04's `corpus_status`), sorted and paginated on the v1 side. |
| `get_entity_info` | INTEGRATE | Test-support only (05-03 Task 3's real graph-aware-cleanup proof) — looks entities up by name, independent of the doc-status record `adelete_by_doc_id` already removed. Not reachable through any seam method; recorded here because it crosses the same subprocess boundary this table otherwise covers. |
| `chunk_entity_relation_graph.get_all_labels` | INTEGRATE | Test-support only (05-03 Task 3), same disposition as `get_entity_info` above. |
| facade construction (`initialize_storages`/`finalize_storages`) | INTEGRATE | The health port's own liveness probe (05-04) — a real facade construction against v1's own backend stores, not a file-existence check. |
| `aquery`/`aquery_data` (query-side) | OPT-OUT | Phase 3's query-side decomposition already ports this operation's own eighteen positions (`databasise/parts_core/lightrag/`); this phase's corpus-side ports never call it — ingest/delete/status are a disjoint operation set from query. |
| `ainsert` (v1's own convenience wrapper) | OPT-OUT | The ingest port calls the two lower-level pipeline stages (`apipeline_enqueue_documents` + `apipeline_process_enqueue_documents`) directly, matching v1's own async job-status model (API-01) rather than `ainsert`'s synchronous convenience shape, which does not expose the enqueue/process split this phase's job-polling surface needs. |

## 3. The OpenAI-compatible model endpoint

Not restated here. `.planning/phases/03-lightrag-query-side/COVERAGE.md` is the authoritative
matrix, exactly as Phase 4's own record points at it. This phase changes no row's *integration* —
the ingest/delete ports reach the machine's own injected `LLM_BINDING_HOST`/
`EMBEDDING_BINDING_HOST` env (the same network-denial-by-construction technique Phase 3's parity
harness already uses), never a second client shape.

One row's status in the *product* changes without its integration changing: Phase 3's matrix marks
`files (upload / retrieval-file API)` `OPT-OUT` with the reason "corpus ingestion is Phase 5's
opaque-admission concern (MODAL-02), not a Phase 3 query-side capability." That reason is now
discharged by this phase's ingest port (05-01) and its REST upload route (05-04) — but discharged
at the machine's own corpus-ingest surface, never by beginning to call the provider's own files
API. Phase 3's row stands as written; no provider-side capability moved.

## 4. The §18.5 surface record

CONTRACT §18.5: *"The tool surface MAY grow per part and MUST NOT grow per modality."* This phase
extends Phase 4's own operations table with the corpus-side operations plans 05-01/05-03/05-04
added — none of them modality-named, all reachable through both transports.

| operation | transports | plan | why an operation and not a selector |
|---|---|---|---|
| query (non-streaming) | in-process, REST | 04-01, 04-05 | *(carried forward from Phase 4's table, unchanged.)* |
| query (streaming, SSE) | in-process (async generator), REST | 04-05 | *(carried forward, unchanged.)* |
| evidence dereference | in-process, REST | 04-02, 04-05 | *(carried forward, unchanged.)* |
| trace resolution | in-process, REST | 04-04, 04-05 | *(carried forward, unchanged.)* |
| ingest (structured text + raw upload) | in-process, REST (`POST /documents`, `POST /documents/upload`) | 05-01, 05-04 | The seam's fourth answering-adjacent operation. Every modality's corpus ingests through it; §18.5's growth rule means a second modality adds no second ingest operation — it is reached by the same `Databasise.ingest()` call regardless of which modality's own opaque port the resolved wiring names. |
| job status (poll) | in-process, REST (`GET /jobs/{job_id}`) | 05-01, 05-04 | A distinct read shape from ingest itself — polling an already-returned job handle cannot be expressed as a selector over a call that has already returned, the same reasoning Phase 4's table already applies to streaming. |
| delete document | in-process, REST (`DELETE /documents/{document_id}`) | 05-03 | §19.6 requires delete be a separate port from ingest (different declared effect, `mutates_store` vs `writes_artifact`) — and separately, a mutation is not an answering variant a selector could express. |
| health | in-process, REST (`GET /health`) | 05-04 | A liveness probe over the machine's own stores plus the foreign engine, not a modality-scoped answer; no selector expresses "is the machine up." |
| corpus status (paginated) | in-process, REST (`GET /corpus`) | 05-04 | A bounded, paginated read over the whole corpus's document list — API-06's own bounded/paginated-by-construction requirement, not a variant of any answering operation. |
| document counts | in-process, REST (`GET /corpus/counts`) | 05-04 | A fixed-size aggregate read, distinct from the paginated document list above (no `page`/`offset` parameter exists because there is nothing to page through). |

### Operations deliberately absent

Carried forward from Phase 4's own table; the two rows this phase discharges are marked
`DISCHARGED` rather than removed, so a reader who remembers Phase 4's record sees the change rather
than a silent disappearance. Every remaining row's reason is unchanged from Phase 4's own record.

| operation | decision | reason |
|---|---|---|
| MCP transport (API-07) | OPT-OUT | Unchanged from Phase 4's record — still a later plan's (05-07's) own deliverable, out of this phase's scope. |
| ingest | **DISCHARGED** | Was `OPT-OUT` in Phase 4's table ("the seam is locked before ingest ships precisely so the ingest endpoints land against a frozen envelope"). Discharged by 05-01/05-04 — see the operation row above. The envelope itself was not reopened to discharge it. |
| delete / document status | **DISCHARGED** | Was `OPT-OUT` alongside ingest in Phase 4's table. Discharged by 05-03/05-04 — see the delete/health/corpus-status/document-counts rows above. |
| promote / rollback | OPT-OUT | Unchanged from Phase 4's record — still Phase 7's own deliverable. |
| comparison-rig operations | OPT-OUT | Unchanged from Phase 4's record — the rig remains a peer client of this seam (§18.3), not an operation on it. |
| a per-modality tool of any kind | **FORBIDDEN** | Unchanged from Phase 4's record — §18.5's invariance rule; not an opt-out a later phase may revisit. |

### Authentication and transport hardening

Unchanged from Phase 4's own disposition, restated here because this phase adds routes to the same
unauthenticated REST layer: the new `/documents`, `/documents/upload`, `/jobs/{job_id}`,
`/documents/{document_id}`, `/health`, `/corpus`, `/corpus/counts` routes carry no authentication,
authorization, TLS termination or rate limiting of their own — the same transfer disposition Phase
4's threat register already records (T-04-25, T-04-26) for the transport as a whole.
