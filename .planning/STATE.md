---
gsd_state_version: "1.0"
milestone: v1.1
milestone_name: Engine Fixes + Operator Console
current_phase: 10
current_phase_name: Stores, Locking & Data Integrity
status: executing
stopped_at: Completed 10-11-PLAN.md
last_updated: "2026-10-18T01:50:18.694Z"
last_activity: 2026-10-17
last_activity_desc: Phase 9 complete, transitioned to Phase 10
state_head: 56fd1442a45efe9d44aff287a859535f30db216a
progress:
  total_phases: 11
  completed_phases: 2
  total_plans: 32
  completed_plans: 31
  percent: 18
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-10-17 after Phase 9)

**Core value:** Modalities are swappable without consumers noticing — LightRAG and HippoRAG 2 both live behind one unchanging §18 envelope, comparable side-by-side on the rig.
**Current focus:** Phase 10 — Stores, Locking & Data Integrity

## Current Position

Phase: 10 (Stores, Locking & Data Integrity) — EXECUTING
Plan: 12 of 12
Status: Executing (10-02 complete)
Last activity: 2026-10-17 — 10-02 complete (lexical, blob, artifact registry removed, D-15)

Progress: [██░░░░░░░░] 18% (2/11 phases)

## Performance Metrics

**Velocity:**

- Total plans completed (v1.1): 0
- Average duration: —
- Total execution time: 0.0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 08 | 10 | - | - |
| 9 | 10 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

*Updated after each plan completion. v1.0 metrics (64 plans) are in git history at tag `v1.0`.*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 08 P01 | 35 min | 2 tasks | 11 files |
| Phase 08 P02 | ~10min | 2 tasks | 3 files |
| Phase 08 P03 | 8 min | 2 tasks | 5 files |
| Phase 08 P04 | 15 min | 2 tasks | 1 files |
| Phase 08 P05 | 25 min | 3 tasks | 8 files |
| Phase 08 P06 | 20 min | 2 tasks | 7 files |
| Phase 08 P07 | 12 min | 2 tasks | 7 files |
| Phase 08 P08 | 35 min | 3 tasks | 7 files |
| Phase 08 P09 | 25min | 2 tasks | 3 files |
| Phase 08 P10 | 2 min | 1 tasks | 4 files |
| Phase 09 P01 | 35 min | 2 tasks | 11 files |
| Phase 09 P02 | n/a (continuation) | 3 tasks | 5 files |
| Phase 09 P03 | n/a | 2 tasks | 10 files |
| Phase 09 P04 | 15min | 2 tasks | 6 files |
| Phase 09 P05 | 25 min | 2 tasks | 5 files |
| Phase 09 P06 | 20 min | 2 tasks | 10 files |
| Phase 09 P07 | 15 min | 2 tasks | 7 files |
| Phase 09 P08 | 25 min | 2 tasks | 7 files |
| Phase 09 P09 | 20 min | 2 tasks | 7 files |
| Phase 09 P10 | 25min | 3 tasks | 4 files |
| Phase 10 P02 | 15min | 2 tasks | 19 files |
| Phase 10 P03 | 11min | 2 tasks | 3 files |
| Phase 10 P01 | 24min | 3 tasks | 10 files |
| Phase 10 P04 | 22min | 2 tasks | 5 files |
| Phase 10 P05 | 35min | 2 tasks | 7 files |
| Phase 10 P06 | 25min | 2 tasks | 4 files |
| Phase 10 P07 | 20min | 2 tasks | 7 files |
| Phase 10 P08 | 23min | 2 tasks | 7 files |
| Phase 10 P09 | 16min | 2 tasks | 4 files |
| Phase 10 P10 | 25min | 2 tasks | 4 files |
| Phase 10 P11 | 20min | 2 tasks | 4 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table. The v1.0 per-plan decision log is in this file's history at tag `v1.0` and in the phase summaries under `.planning/milestones/v1.0-phases/`.
Recent decisions affecting current work:

- Roadmap v1.1: 11 phases (8-18), one per requirement category, in the owner-approved order — engine defects F1-F8 (Phases 8-15), then GUI connectors (16), GUI mockup (17), GUI live (18)
- Roadmap v1.1: every phase holds at most 20 requirements (BAK size gate); every defect requirement needs a regression test that fails before the fix
- Roadmap v1.1: owner design decisions ("Owner decision first" lines) are listed per phase in ROADMAP.md and settle in discuss-phase before planning; decisions consumed across phases are listed under "Cross-phase decisions" in ROADMAP.md
- [Phase 08]: 08-01: UnparseableProviderRoutingError message withholds the env value (raw_value attribute only); launcher has no default env file (D-11); DEFAULT_WORKSPACE is the literal RUN-06 workspace so snapshot drift cannot stop serving
- [Phase 08]: 08-02: clients/ keeps the literal 'unbudgetable' (cannot import seam/); no-usage response = one unbudgetable call, no estimate (D-05)
- [Phase 08]: 08-03: live section 18.5 record at databasise/evidence/COVERAGE.md is a verbatim copy; archived v1.0 record stays frozen (D-13). mcp_sdk_is_installed uses PathFinder over the project-stripped sys.path, bypassing sys.modules.
- [Phase 08]: 08-04: RUN-09 mutation run as an in-test monkeypatch of engine.generated_on_disk_name; engine.py untouched
- [Phase 08]: 08-05: rerank mirrors LightRAG v1 bindings (cohere, jina, aliyun) chosen by optional RERANK_BINDING; owner: 'Use a reranker the same way lightrag uses it or any other.'
- [Phase 08]: 08-05: rerank resolved_model_identity falls back to configured RERANK_MODEL when the response has no model (owner-approved, rerank-scoped exception to the base.py identity rule; LLM and embedding stay strict)
- [Phase 08]: 08-05: HealthReport gains additive clients map (llm, embedding, rerank), presence only, never affects status; TEI native shape and v1 chunking are OPT-OUT
- [Phase 08]: 08-06: example MCP client config is examples/mcp-client.stdio.json, never a repo-root .mcp.json, so no Claude session auto-starts the engine and holds the parity store lock
- [Phase 08]: 08-07: run_arm.main is the sixth locked parity CLI; eval/corpus_ingest, aa_run and remint stay unlocked (own v1/.eval_corpus_store root). Library functions take no lock.
- [Phase 08]: 08-08: seam hardening lives in the launchers (TrustedHostMiddleware, TransportSecuritySettings, non-loopback bind refusal); create_app keeps accepting any Host; seam authentication stays an open owner decision for the CONN phases
- [Phase 08]: 08-08: CORS origins are validated exact scheme://host[:port] values, GET/POST/DELETE + Content-Type only, no credentials, never '*' (D-12)
- [Phase 08]: 08-09: offline guard wraps socket connect/connect_ex in-process only; the RUN-12 gate adds no marker expression and relies on addopts
- [Phase 08]: 08-10: _SIMILARITY_THRESHOLD stays 0.999 and is documented unmeasured; the D-14 live measurement is owner-deferred to TESTING-PLAN section 2 (owner: run measurements only for debugging)
- [Phase 08]: 08-10: RUN-11 left open; the twelve ledger set lines, with RUN-05 evidence node names corrected, are parked in 08-10-SUMMARY.md for the owner
- [Phase 09]: 09-01: a request with both a schema error and a refusal returns the refusal body; moved refusals are re-exported from their old modules
- [Phase 09]: 404 limited to the four caller-supplied lookups; every other refusal is 422 via rest._status_for (D-03) — A not-found status must not disclose internal identities
- [Phase 09]: pydantic.ValidationError with no refusal inside is re-raised and stays a 500; upload selector null/empty/whitespace means default — A refusal-free schema failure is a server bug; matches JSON routes' selector null
- [Phase 09]: D-12 revised: only None is an absent document id; a blank upload FORM field is normalised to absent in the route, JSON/MCP '' and '   ' are refused as InvalidDocumentIdError
- [Phase 09]: Page and checked_page check the upper cap before lower bounds; PageBoundsError for limit<1 or offset<0; one shared checked_page for REST and MCP
- [Phase 09]: D-02:MCP-refusal-is-isError-bare-JSON-via-_DatabasiseServer.call_tool-override;_refusal_mapped-and-_refusal_detail-deleted
- [Phase 09]: 09-05: a v1 engine failure is a machine fault (502 run failed or malformed output, 503 v1 unavailable), cause private and logged once; failure_class tokens MalformedDriverOutput and UnclassifiedEngineFailure are executor-chosen
- [Phase 09]: D-05: an evidence namespace must fullmatch [A-Za-z0-9-]+; otherwise InvalidEvidenceNamespaceError before any store or directory; resolve_evidence builds only the vector store
- [Phase 09]: D-08: blank query text is EmptyQueryObjectError beside any member; blank ingest text and 0-byte raw are EmptyIngestDocumentError(member); MCP base64 is strict (validate=True)
- [Phase 09]: SEAM-10: Selector(capability=[]) is refused in resolve_selector and render_selector_key, not in Selector's validator, so construction still succeeds and every selector route is covered
- [Phase 09]: SEAM-12: Databasise.promote refuses an empty or hash-shaped alias with one InvalidPromotionAliasError using Selector's own _INSTANCE_HASH_PATTERN, before trace resolution and any ledger write
- [Phase 09]: 09-08 SEAM-11: compare checks every key (comparison_keys) before resolving any selector, resolves each once and executes the resolved wiring via _execute_resolved; keys stay unprefixed, envelope vs map is told by the number of selectors sent (D-09, D-10)
- [Phase 09]: D-11 discard-and-document for SEAM-15: file_name/content_type documented as not stored; citation carry-through deferred to M-04 (Phase 11)
- [Phase 09]: redact.py is a test-time gate; its checks raise AssertionError explicitly so python -O cannot disable them
- [Phase 09]: Selector candidate pool is all_wirings(); capability ties break by pool order; selectors._ARM_NAMES/_DEFAULT_ARM removed
- [Phase 10]: 10-02: lexical store, blob store and artifact registry deleted (D-15); STOR-13/14 met by removal; tests/test_removed_stores_absent.py guards it
- [Phase 10]: 10-03: gc_namespaces CLI treats a symlinked quarantined-* entry as present so gc_namespace raises NamespaceGCError on it
- [Phase 10]: 10-01: CozoGraphStore.finalize sets its released flag on the loop thread before the executor release, so concurrent finalizes release the shared client once
- [Phase 10]: 10-01: only the engine translates GraphStoreBusyError to StoreBusyError (409); parity run_arm lets it propagate under the store-root lock
- [Phase 10]: 10-04: a refused ingest (any node exception, partial, stop_reason or cycle) drops every store's pending writes; store errors surface as failure_class StoreFault, early stops as RunIncomplete (both 502)
- [Phase 10]: 10-04: ForeignEngineRefusalError message is now "operation 'x' failed (<class>)"; no test pinned the old text
- [Phase 10]: 10-05: _commit_all prepares every store then commits every store under one asyncio.Lock per (event loop, resolved store root); a prepare or commit failure aborts and raises StoreFault; cancellation aborts and re-raises
- [Phase 10]: 10-05: FaissVectorStore.prepare rebases on the on-disk (st_ino, st_mtime_ns, st_size) signature, so overlapping per-call writers keep each other's vectors
- [Phase 10]: 10-05: vector and graph drop_pending_index_ops delegate to abort_prepared; CozoGraphStore.finalize aborts an open prepared transaction before releasing the shared client
- [Phase 10]: load_committed caches read-only Faiss snapshots keyed on the stat triples of both files, LRU 32 with per-directory stale-key eviction; a half-written directory gets the same one retry before VectorStoreCorruptedError
- [Phase 10]: resolve_evidence maps VectorStoreCorruptedError to ForeignEngineRefusalError(failure_class=StoreCorrupted), 502 over REST
- [Phase 10]: 10-07: health probes are read-only; sqlite uses mode=ro plus immutable=1 when no -wal exists so no sidecar is left behind
- [Phase 10]: 10-08: every scoped store handle is a _StoreProxy (writable ones too, to hold back engine-only lifecycle methods); engine-only refusals carry the method name as .effect
- [Phase 10]: 10-09: delete_node marks the node's committed edges removed at delete time, so re-creating the node does not bring old edges back; the flush cascade still runs
- [Phase 10]: 10-10: delete_document commits for every non-fail status and drops on a refusal or fail (Q4); a vector delete of a never-committed id writes nothing
- [Phase 10]: 10-11: vector store refuses metadata keys id/score (ReservedMetadataKeyError) and top_k<=0 (InvalidTopKError); unselected MultiNamespaceVectorStore refuses every read, listing only dirs with vector.faiss

### Pending Todos

None yet.

### Blockers/Concerns

- Overlapping requirements across phases: STOR-06/HIPP-03 (ingest abort commits nothing), STOR-03/STOR-07/WIRE-14 (evidence-resolve and delete store construction), STOR-04/LRAG-13/LRAG-14/HIPP-15 (health), SEAM-08/LRAG-05 (page lower bounds), SEAM-12/LEDG-05 (promote alias validation), HIPP-04/WIRE-14 (real failing-node exception), WIRE-11/TOOL-12 (cache_hit None). The later phase's regression test may already pass on arrival; record it as satisfied by the earlier commit instead of fabricating a failing-first run.
- GUI-04, GUI-05 and CONN-03 hard-code hybrid and global as unreachable; WIRE-01 (Phase 13) makes every arm reachable, so those fixtures and the §3.0 table must be regenerated from the post-WIRE-01 resolution rules.
- ⚠️ [v1.0 Phase 07 WR-03] `sqlite3.connect()` sets no explicit `timeout=` and a lock-timeout `OperationalError` is not wrapped into a `SeamRefusalError`. Relevant to LEDG-06 (Phase 14).
- [Phase 08] Ledger test files for RUN-01..RUN-10 and RUN-12 are now protected: Phase 9+ edits to test_rest_corpus_endpoints.py, test_openai_compat.py, test_launchers.py etc. need the owner's grant-check-edit. RUN-11 test_ref and RUN-02..08 record-fail (BASE = parent of the first (08-NN) commit) remain owner steps.
- [Phase 08] `v1/.env.teachers` is untracked and not gitignored; move or ignore it before any record-fail run.
- [Phase 09] Six Info review items stay open in 09-REVIEW-DISPOSITION.md (IN-03 OpenAPI does not declare the 404/422 refusal shape; IN-04 every node exception labelled a foreign-engine fault; IN-05 unreachable `UnknownDocumentError`; IN-06 refusals echo unbounded caller input; IN-07 compare rule text copied three times; IN-08 accepted limits). WR-02 (crash orphan between staged create and owner record) is deferred.
- [Phase 09] SEAM-01..SEAM-16 ledger rows are still open with empty test_refs; once set, the 16 SEAM test files become protected (grant-check-edit needed in later phases).
- [Phase 09] One unexplained single failure in a `check_offline_suite.py` pytest-mode run during review fixes did not reproduce in five later full runs; watch for it.
- Cozo 0.7.6 is architecture-frozen with four known correctness bugs and no upstream fixes expected; relevant to STOR-01 and STOR-10 (Phase 10).

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 1 | Record Phase 6→7 gate deferral (MACH-03, MODAL-01) | 2026-09-11 | e64c694 | .planning/quick/260911-e7a-record-phase-6-to-7-gate-deferral/ |

## Deferred Verification

| Phase | State | Resume |
|-------|-------|--------|
| 03 | verification_deferred_human — carried out of v1.0; owner items in .planning/TESTING-PLAN.md §1 | archived under milestones/v1.0-phases/ |

## Deferred Items

Items acknowledged and deferred at milestone close, most recent first:

| Category | Item | Status | Deferred At | Milestone |
|----------|------|--------|-------------|-----------|
| verification_gaps | 06/06-VERIFICATION.md — MACH-03 A/A calibration never run (06-GATE-AMENDMENT.md) | gaps_found | 2026-09-12 | v1.0 |
| verification_gaps | 03/03-VERIFICATION.md — MODAL-01 two owner-only CONTRACT §5 items | human_needed | 2026-09-12 | v1.0 |
| uat_gaps | 03/03-UAT.md — tests 2 and 3 (answer spot-check, declared-deviation causes) | testing, 2 scenarios open | 2026-09-12 | v1.0 |
| todos | melodyscribe-interface-skill.md | (presence-only) | 2026-09-12 | v1.0 |
| todos | melodyscribe-spike-rig-experiments.md | (presence-only) | 2026-09-12 | v1.0 |
| deferred_items | HARD-01, HARD-02, HARD-04 — deferred out of Phase 7 by 07-GATE-AMENDMENT.md; TESTING-PLAN.md §2, §4 | acknowledged | 2026-09-12 | v1.0 |

## Session Continuity

Last session: 2026-10-18T01:50:18.595Z
Stopped at: Completed 10-11-PLAN.md
Resume file: None

## Operator Next Steps

- Phase 10 (Stores, Locking & Data Integrity) is next in the autonomous run
- Owner, when ready: TESTING-PLAN.md §2 RUN-11 live runs, parity-env check, optional live rerank test
