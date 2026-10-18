# Roadmap: Databasise 2.0 — Fully Agnostic System

## Milestones

- ✅ **v1.0 Fully Agnostic System** — Phases 1-7 (shipped 2026-09-12) — archive: `.planning/milestones/v1.0-ROADMAP.md`
- 🚧 **v1.1 Engine Fixes + Operator Console** — Phases 8-18 (in progress)

Owner testing carried out of v1.0 (A/A calibration, MODAL-01 owner items, Nyquist validation, doc hardening) is tracked in `.planning/TESTING-PLAN.md`, not as a phase.

## Phases

<details>
<summary>✅ v1.0 Fully Agnostic System (Phases 1-7) — SHIPPED 2026-09-12</summary>

- [x] Phase 1: Machine Core (10/10 plans) — completed 2026-08-31
- [x] Phase 2: Falsifier Gate (4/4 plans) — completed 2026-08-31
- [x] Phase 3: LightRAG Query Side (13/13 plans) — executed 2026-09-06; MODAL-01 owner items deferred (06-GATE-AMENDMENT.md)
- [x] Phase 4: The Seam (5/5 plans) — completed 2026-09-06
- [x] Phase 5: Opaque-Side Admission (9/9 plans) — completed 2026-09-08
- [x] Phase 6: HippoRAG 2 & Side-by-Side (18/18 plans) — executed 2026-09-12; MACH-03 A/A run deferred (06-GATE-AMENDMENT.md)
- [x] Phase 7: Promotion & Rollback (5/5 plans) — completed 2026-09-12; HARD-01/02/04 deferred (07-GATE-AMENDMENT.md)

Full phase details, success criteria and ordering constraints: `.planning/milestones/v1.0-ROADMAP.md`.
Audit: `.planning/milestones/v1.0-MILESTONE-AUDIT.md` (29/34 requirements, 7/7 integration, 4/4 flows).

</details>

## v1.1 Engine Fixes + Operator Console

**Milestone Goal:** Fix every confirmed engine defect in `docs/gui/CODEBASE-MAP.md` §4 (356 defect uids, each fixed against a regression test that failed first), then build an operator console as a client of the §18 REST API: operator read routes first, then a clickable mockup, then the mockup connected to the live API screen by screen.

**Overview:** Phase 8 makes the engine runnable as a served process (launcher, model clients, store lock, CORS) and gets the offline suite green, so every later fix can be checked end to end. Phases 9-15 fix the engine defects by area: the seam's inputs and error shapes, the stores and their locking, the LightRAG corpus path, HippoRAG, the selector/wiring/runner layer, promotion and the ledger, and the offline tooling. Phase 16 adds the operator read routes the console needs. Phase 17 builds a static mockup of all six console screens against fixtures; Phase 18 connects it to the live API. Order is owner-decided: every engine phase (8-15) completes before any GUI phase (16-18) starts, and the connectors come before the console.

**Phase Numbering:**

- Integer phases (8, 9, 10): Planned milestone work, continuing from v1.0's Phase 7
- Decimal phases (8.1, 8.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 8: Run the Engine** - Installed launchers for REST and MCP, one shared client builder, one engine process per store root, CORS decision, and a green offline suite (F1) (completed 2026-10-16)
- [x] **Phase 9: Inputs, Errors & Security** - One refusal shape on both transports, caller input refused before it touches disk or a node, machine faults without leaked stderr (F2) (completed 2026-10-17)
- [x] **Phase 10: Stores, Locking & Data Integrity** - Graph lock contention as a named outcome, all-or-nothing ingest/delete commits, read-only handles, consistent store adapters (F3) (completed 2026-10-17)
- [ ] **Phase 11: LightRAG Corpus Path** - Ingested documents reach the queried stores, uploads index their content, honest health, and v1-faithful KG answers (F4)
- [ ] **Phase 12: HippoRAG Fixes** - Resolvable PPR evidence, a graph that accumulates correctly across ingests, query-only runs, and a full document lifecycle (F5)
- [ ] **Phase 13: Selectors, Wiring & Runner** - Every arm selectable, node-free consumer text, complete and truthful run records, guards that fire on what they declare (F6)
- [ ] **Phase 14: Promotion & Ledger** - Operator verbs that never 500, aliases that always resolve, no tombstoned generation served, alias history readable (F7)
- [ ] **Phase 15: Offline Tooling & Packaging** - Wheel-runnable CLIs that refuse by name and never spend by default, honest parity/eval/evidence records, admission enforced at load (F8)
- [ ] **Phase 16: GUI Connectors** - Operator read routes: info, wirings, aliases, history, traces, promote preview, chunks, graph nodes, store-busy status, log tail
- [ ] **Phase 17: GUI Mockup** - Static six-screen operator console mockup on fixtures, every control id-stamped, missing backends badged
- [ ] **Phase 18: GUI Live** - The mockup connected to the live §18 REST API and operator routes, screen by screen

### Cross-phase decisions

Some owner decisions are taken in one phase and consumed by later ones. Settle each in the earliest phase listed; later phases inherit it.

- **M-04 LightRAG write path** — decided in Phase 11 (LRAG-01/02/03/15); consumed by SEAM-15 (Phase 9, default: document that file_name is discarded unless the decision is pulled forward), TOOL-02 and TOOL-11 (Phase 15), LIVE-05 (Phase 18)
- **M-12 HippoRAG corpus surface** — raised in Phase 11 (LRAG-01), decided in Phase 12 (HIPP-15/16); consumed by LEDG-03 option (a) (Phase 14)
- **G-01 graph lock vs G-36 process lock** — RUN-07 (Phase 8) and STOR-01 (Phase 10) must not overlap; CONN-11/13 (Phase 16) and LIVE-08 (Phase 18) depend on the outcome
- **G-20 meaning of health 'ok'** — split across STOR-04 (Phase 10), LRAG-13/14 (Phase 11) and HIPP-15 (Phase 12); decide once in Phase 10
- **SEAM-05 machine-fault status and stderr exposure** — decided in Phase 9; reused by LRAG-05 (Phase 11) and CONN-14 (Phase 16)
- **G-27 v1 answer fidelity** — decided in Phase 11 (LRAG-17/18); consumed by TOOL-07 (Phase 15)
- **M-08 hybrid/global selection** — decided in Phase 13 (WIRE-01); consumed by TOOL-09 (Phase 15), CONN-03/05 (Phase 16), GUI-04/05 (Phase 17)
- **Arm identity on RunRecord** — decided in Phase 13 (WIRE-12); required by LEDG-01 option (b) (Phase 14)
- **Wire or delete the lexical/blob/artifact stores** — STOR-12 (Phase 10) and TOOL-17 (Phase 15) decide together
- **codebase-memory-mcp registration** — LEDG-12 (Phase 14) decides; TOOL-15 and TOOL-18 (Phase 15) follow
- **Gate verbs and the calibrated floor** — LEDG-08 (Phase 14) refuses gate verbs up front; TOOL-12 (Phase 15) persists a floor the gate reads, so it must lift LEDG-08's refusal for an arm with a floor
- **Console exposure (open questions 1-6, 12, 14)** — decided in Phase 16 (CONN); consumed by GUI-11 (Phase 17) and LIVE-01/07/08 (Phase 18)

## Phase Details

### Phase 8: Run the Engine

**Goal**: An operator can start the engine as a served process from the installed package, with real model clients and one engine process per store root, and the offline test suite is green so every later fix can be checked end to end
**Depends on**: Nothing in v1.1 (builds on v1.0 Phase 7)
**Requirements**: RUN-01, RUN-02, RUN-03, RUN-04, RUN-05, RUN-06, RUN-07, RUN-08, RUN-09, RUN-10, RUN-11, RUN-12
**Success Criteria** (what must be TRUE):

  1. An operator starts the REST seam with one installed command (`databasise-rest --store-root --workspace --env-file`) and GET /health returns 200 with the llm and embedding clients built by the shared builder; an env file missing required keys stops startup with an error naming every missing key, and rerank is explicitly reported as not available unless RERANK_BINDING selects a binding and its three RERANK_* keys are present (owner decision D-07/D-08)
  2. An MCP client started through `databasise-mcp --transport stdio` lists the same tools as the in-process server; a second launcher on the same store root, or `databasise-rest --workers 2`, exits non-zero with a named store-lock error giving the store root and holder PID while the first launcher keeps answering /health
  3. With `--cors-origin <origin>` a browser preflight from that origin succeeds and an unlisted origin gets no allow header; with no flag the seam behaves exactly as before
  4. A provider response with no usage is counted as one unbudgetable call, and empty choices, None content, a mis-sized embedding batch and out-of-order embedding items raise named client errors or are returned in input order — never passed on silently
  5. From `databasise/`, `.venv/bin/pytest` and `.venv/bin/python -m pytest` both report 0 failed; the COVERAGE.md cross-check runs, the mcp SDK is detected, the upload and delete round-trip tests fail under the mutations they claim to catch, and live-endpoint tests run only under `-m live`

**Owner decisions to settle in discuss-phase**:

- RUN-01: where the live §18.5 COVERAGE.md record lives (default: a stable non-`.planning` path)
- RUN-02: representation of unreported tokens (default: call_count=1 with the existing 'unbudgetable' sentinel)
- RUN-03: refusal/tool-call content=None raises or maps to empty text plus stop_reason (default: raise a named error)
- RUN-05: ship a rerank client or record rerank as not available (default: not available); launcher refuses to start without clients unless `--no-clients` (default: refuse)
- RUN-06: one process (MCP streamable-http mounted in the FastAPI app) or two processes — interacts with the RocksDB lock in RUN-07
- RUN-07: how parity CLIs coexist with a running launcher (default: take the same lock and refuse); coordinate with G-01 in Phase 10
- RUN-08: CORS allow-list or same-origin serving (default: explicit allow-list, empty by default, never '*')
- RUN-11: parity similarity threshold (lower it, pin a deterministic endpoint, or retry and report flakiness)

**Plans**: 10/10 plans complete

Plans:
**Wave 1**

- [x] 08-01-PLAN.md — Tracer: installed `databasise-rest` serves /health with builder-built clients and the store lock; `live` marker excludes live tests by default (wave 1)
- [x] 08-02-PLAN.md — OpenAI-compatible client: no-usage = one unbudgetable call; named errors for malformed responses (RUN-02, RUN-03; wave 1)
- [x] 08-03-PLAN.md — Live §18.5 COVERAGE.md record and non-vacuous cross-check; shadow-safe mcp SDK detection (RUN-01, RUN-04; wave 1)
- [x] 08-04-PLAN.md — Upload test checks the disk; round trips prove counts drop after delete (RUN-09, RUN-10; wave 1)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 08-05-PLAN.md — Rerank client, optional RERANK_* in the shared builder, /health clients map, API coverage table (RUN-05; wave 2, owner decision checkpoint)
- [x] 08-06-PLAN.md — `databasise-mcp` launcher, example stdio config, cross-process lock refusal tests (RUN-06, RUN-07; wave 2)
- [x] 08-07-PLAN.md — Parity CLIs take the store lock and refuse while a launcher holds it (RUN-07 D-03; wave 2)
- [x] 08-08-PLAN.md — Opt-in exact-origin CORS allow-list via `--cors-origin` (RUN-08; wave 2)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 08-09-PLAN.md — Dual-invocation offline gate script and non-loopback socket guard (RUN-12; wave 3)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 08-10-PLAN.md — Owner live measurements set the parity threshold; amended RUN-05 wording; ledger test_refs (RUN-11 + ledger; wave 4, owner checkpoints)

### Phase 9: Inputs, Errors & Security

**Goal**: Every caller-facing failure on REST and MCP is a named refusal in one documented shape, and no caller input reaches the disk, a store or a node before it is validated (the Phase 8 launcher transport guards keep their own shape; owner-ratified D-13)
**Depends on**: Phase 8
**Requirements**: SEAM-01, SEAM-02, SEAM-03, SEAM-04, SEAM-05, SEAM-06, SEAM-07, SEAM-08, SEAM-09, SEAM-10, SEAM-11, SEAM-12, SEAM-13, SEAM-14, SEAM-15, SEAM-16
**Success Criteria** (what must be TRUE):

  1. Every refusal reaches a REST client as a JSON body with refusal_type and no FastAPI `detail` wrapper, at the status the owner-chosen mapping assigns, and the MCP transport returns the same refusal_type as parseable JSON for every refusal REST returns; every refusal_type is exported from one catalogue
  2. Path-like evidence namespaces and document ids, oversized uploads, empty or whitespace-only text, 0-byte uploads, invalid base64 and out-of-range page limits or offsets are refused by name before any store is opened, any node runs or any file is written — no such input produces a 500 or creates a directory inside or outside store_root
  3. A v1 engine failure (subprocess error, timeout, missing interpreter, malformed driver output) on any route returns a structured machine-fault response containing no stderr, server paths or traceback text
  4. Selectors that cannot mean anything are refused before work starts: `capability: []`, colliding compare keys (zero arms run, zero traces persisted, each arm executing the wiring the pre-check resolved) and promote aliases no selector could carry; an upload selector field of `null` or `''` means the default selector
  5. Seam docstrings and field descriptions match behaviour (file_name handling stated or carried through, stale selector/refusal/corpus text removed) and the redact leak check still fires under `python -O`

**Owner decisions to settle in discuss-phase**:

- SEAM-01: name of the malformed-namespace refusal (proposed: InvalidEvidenceNamespaceError)
- SEAM-02: confirm one refusal shape for every SeamRefusalError (proposed: RequestValidationError handler unwrapping ctx.error) and name the multi-member selector refusal (proposed: MultiMemberSelectorError)
- SEAM-03: MCP refusal text — keep the SDK's 'Error executing tool <name>: ' prefix and document it, or return CallToolResult(isError=True) with bare JSON
- SEAM-04: uniform 422 for every refusal or 404 for not-found lookups
- SEAM-05: status for machine faults (500 or 502/503) and whether the diagnostic cause is withheld, truncated or exposed behind an operator flag
- SEAM-06: reuse ForeignEngineRefusalError for read-route adapter failures or add a dedicated 'v1 engine unavailable' refusal
- SEAM-07: refusal for a malformed caller document_id (reuse UnknownDocumentError or add InvalidDocumentIdError)
- SEAM-08: extend PageSizeExceededError to lower bounds or add PageBoundsError
- SEAM-09: whether whitespace-only text counts as empty (proposed: yes)
- SEAM-11: compare key format (kind-prefixed keys change consumer-visible keys) and how a consumer tells a single envelope from a keyed map
- SEAM-15: store file_name/content_type as citation metadata (needs the M-04 write path from Phase 11) or drop and document

**Plans**: 10/10 plans complete

Plans (one plan per wave; every plan edits the shared refusal, engine or transport modules, so the waves run in sequence):

- [x] 09-01-PLAN.md — Tracer: one refusal body for validator-raised refusals on every JSON route; one refusal catalogue (SEAM-02, SEAM-14; wave 1)
- [x] 09-02-PLAN.md — Upload route reports the broken rule, null/'' selector means default, 404 for the four lookups (SEAM-02, SEAM-04, SEAM-07, SEAM-13; wave 2, owner grant checkpoint)
- [x] 09-03-PLAN.md — InvalidDocumentIdError on every ingest/delete entry point; PageBoundsError and one shared checked_page (SEAM-07, SEAM-08; wave 3)
- [x] 09-04-PLAN.md — MCP returns every refusal as bare JSON with isError; named scope-precondition refusals (SEAM-03; wave 4)
- [x] 09-05-PLAN.md — v1 engine failures are 502/503 machine faults with no stderr on every route; OpenAPI declares them (SEAM-05, SEAM-06; wave 5)
- [x] 09-06-PLAN.md — Evidence namespace guard before any store; empty and whitespace inputs and invalid base64 refused (SEAM-01, SEAM-09; wave 6)
- [x] 09-07-PLAN.md — capability [] refused on every selector route; unselectable promote aliases refused (SEAM-10, SEAM-12; wave 7)
- [x] 09-08-PLAN.md — Compare checks keys before any arm and runs each pre-resolved wiring once; envelope-versus-map rule documented (SEAM-11; wave 8)
- [x] 09-09-PLAN.md — file_name/content_type documented as not stored; stale seam docstrings corrected (SEAM-15, SEAM-16; wave 9)
- [x] 09-10-PLAN.md — redact checks fire under python -O; dead selector constants removed; phase offline gate (SEAM-16; wave 10, owner grant checkpoint)

### Phase 10: Stores, Locking & Data Integrity

**Goal**: Concurrent engine calls on one store root produce named outcomes instead of 500s, and every store commits all of a run's writes or none of them
**Depends on**: Phase 8
**Requirements**: STOR-01, STOR-02, STOR-03, STOR-04, STOR-05, STOR-06, STOR-07, STOR-08, STOR-09, STOR-10, STOR-11, STOR-12, STOR-13, STOR-14, STOR-15, STOR-16
**Success Criteria** (what must be TRUE):

  1. Two overlapping engine calls on the same graph namespace (an ingest plus a query, evidence resolve, delete or health check) never return a 500: both complete through a shared handle or the later one receives a named store-busy refusal, a second OS process gets the same refusal, and a failed store open leaves no sqlite connection behind
  2. POST /evidence/resolve opens only the named vector namespace (it works while the graph is held and reads the index once until the index changes), and GET /health on an empty store root creates nothing and reports absent or corrupted stores as not ok
  3. A failed ingest or delete commits nothing and a successful one commits everything: after a refused run the kv, vector and graph stores hold no records from it, vector deletes are buffered and reverted like the other stores, and delete uses the wiring's declared namespaces
  4. A node that declares only read effects cannot mutate any store, and every store effect in the vocabulary either resolves to a wired store or is refused at parse time — no wiring parses and then fails with StoreNotWiredError
  5. Store adapters keep their own data consistent and refuse bad input by name: half-written Faiss directories raise corruption, reserved metadata keys are refused, a deleted graph node leaves no dangling edges, KV buffers are isolated from callers, blob digests cannot escape the blob root, lexical queries match all terms, and quarantined-namespace GC has a production caller that reports failures

**Owner decisions to settle in discuss-phase**:

- STOR-01: G-01 shared reference-counted CozoGraphStore per namespace, or a named StoreBusy refusal callers retry; G-36 parity-CLI handling (coordinate with RUN-07)
- STOR-03: cache key and invalidation for opened FaissVectorStore instances (path + mtime/size, or explicit invalidation by import_index and flushes)
- STOR-04: which namespaces health probes, and whether an absent store on a fresh install is 'degraded' or 'not initialized' (G-20; settle once here for LRAG-13/14 and HIPP-15)
- STOR-05: read/write method split per store kind, and how mutates_store/self_storage resolve (explicit table or refusal)
- STOR-06: cross-store atomicity — compensation/two-phase commit, or accepted and documented as non-atomic
- STOR-10: delete_node cascades incident edges or refuses; whether upsert_edge requires both endpoints to exist
- STOR-12: wire the lexical and blob/artifact stores or delete them and drop the effects (decide together with TOOL-17); what writes_artifact means on embedder-index and graph-augment-persist. STOR-13 and STOR-14 apply only if the stores are kept
- STOR-15: what triggers quarantined-namespace GC (generation retire, instance teardown, operator route), and derive_namespace layout vs docstring fix
- STOR-16: reserved metadata keys rejected at upsert or moved under a sub-key

**Plans**: 12/12 plans complete

Plans (nine waves; the shared engine and store modules force most plans into sequence, and wave 1 and wave 6 each hold plans with no shared file):

- [x] 10-01-PLAN.md — Shared refcounted Cozo client, StoreBusyError 409, a failed store open finalizes every opened store (STOR-01, STOR-02; wave 1, owner grant checkpoint for one protected test line)
- [x] 10-02-PLAN.md — Remove the lexical store, blob store and artifact registry; grep test; admission text (STOR-12, STOR-13, STOR-14; wave 1)
- [x] 10-03-PLAN.md — Operator GC CLI under the store lock; NamespaceGCError; layout docstring (STOR-15; wave 1)
- [x] 10-04-PLAN.md — A failed or early-stopped ingest commits nothing; StoreFault and RunIncomplete; no in-node flush (STOR-06; wave 2)
- [x] 10-05-PLAN.md — Prepare-all then commit-all across kv, vector and graph under one lock; Faiss rebase (STOR-06; wave 3)
- [x] 10-06-PLAN.md — Faiss committed-snapshot cache for evidence resolve; half-written directory is corruption (STOR-03, STOR-08; wave 4)
- [x] 10-07-PLAN.md — Read-only health over every shipped namespace: ok, absent, corrupted, busy (STOR-04; wave 5)
- [x] 10-08-PLAN.md — EFFECT_TO_STORE table and read-only allowlist proxies; engine-only lifecycle (STOR-05; wave 6)
- [x] 10-09-PLAN.md — Graph delete cascades and auto-creates endpoints; KV buffer isolation (STOR-10, STOR-11; wave 6)
- [x] 10-10-PLAN.md — Delete uses the wiring's namespaces and commits all or nothing; buffered vector delete (STOR-07; wave 7)
- [x] 10-11-PLAN.md — Reserved metadata keys refused; named vector input refusals (STOR-09, STOR-16; wave 8)
- [x] 10-12-PLAN.md — unwired-store-effect parse refusal and UnparseableWiringError; writes_artifact marker; phase offline gate (STOR-12; wave 9)

### Phase 11: LightRAG Corpus Path

**Goal**: A document ingested through the seam's LightRAG path is what the LightRAG query arms retrieve, uploads index their real content, health reports only facts it checked, and the KG arms answer the way v1 answers
**Depends on**: Phase 10
**Requirements**: LRAG-01, LRAG-02, LRAG-03, LRAG-04, LRAG-05, LRAG-06, LRAG-07, LRAG-08, LRAG-09, LRAG-10, LRAG-11, LRAG-12, LRAG-13, LRAG-14, LRAG-15, LRAG-16, LRAG-17, LRAG-18, LRAG-19, LRAG-20
**Success Criteria** (what must be TRUE):

  1. Under the chosen M-04 write path, a document ingested through POST /documents with the default selector is retrievable by POST /query on the LightRAG arms and resolvable by /evidence/resolve, and after DELETE it is gone from both (or, under option (c), the query data is labelled as the last parity import); two apps on different store roots never see each other's documents, and eval ingest never writes into the operator corpus
  2. Uploads index their actual content: two different .txt uploads each reach processed with chunk text from their own bytes, unsupported types are refused by name, re-ingest reports what v1 actually enqueued, inbox files are scoped per workspace and never outlive their job, and concurrent writes to one working dir are serialized or refused
  3. v1 failures are readable and safe: missing v1 configuration names the missing keys (never values), a timed-out ingest leaves its document in a visible stuck/interrupted state with an explicit retry action, and driver failures surface as named refusals with no raw stderr for non-operator callers
  4. GET /health writes nothing and reports only what it checked: it covers the HippoRAG namespaces, is not 'ok' without model clients or on an empty store root, and returns a degraded report instead of a 500 when a store fails to finalize
  5. LightRAG hybrid/local/global answers use v1 kg_query's entity and relation context, prompt templates, retrieval ordering and selection (or the arms are relabelled per G-27); query traces carry no no-op embedder-index node; an unpopulated namespace is distinguishable from no match; write-side LLM spend is metered or declared unbudgetable; §8 conditions are numbered correctly; the half-wired entity driver ops are exposed or removed

**Owner decisions to settle in discuss-phase**:

- M-04 LightRAG write path (LRAG-01/02/03/15): (a) machine-native ingest writing v2 stores, (b) import_v1_index after every v1 ingest/delete, or (c) keep the split and label query data 'last parity import' — consumed by SEAM-15, TOOL-02, TOOL-11 and LIVE-05
- M-12 (LRAG-01): whether GET /jobs/{job_id} for a HippoRAG job returns a final status or a named refusal (decide with HIPP-15)
- LRAG-04: wait behind a per-working-dir lock or refuse immediately with 'write in progress'
- LRAG-05: who may see the full v1 stderr cause (operator field, debug flag, server log only) — follow SEAM-05
- LRAG-07: G-33 stuck-state semantics, retry surface (new route or reuse ingest), and whether v1's auto-recovery side effect stays
- LRAG-08: accepted upload types and suffix validation; whether text "" is rejected at validation
- LRAG-10: re-ingest of an existing document_id — refuse, report enqueued 0, or replace
- LRAG-11: capture v1's token tracker inside the driver, or accept 'unbudgetable' and delete the dead branch
- LRAG-14: G-20 meaning of 'ok' and whether HippoRAG namespaces share the report (settled in Phase 10)
- LRAG-15: which wiring aa_run queries (lightrag-base default or naive)
- LRAG-16: refusal or envelope flag for an unpopulated namespace
- LRAG-17/18: G-27 v1 answer fidelity — match v1 kg_query prompts exactly or relabel the arms; whether live rerank gets an API toggle
- LRAG-20: expose a delete-impact/per-document entity view or remove the ops

**Plans**: 2/11 plans executed

Plans (nine waves; `seam/engine.py` is touched by nine plans, so those run one per wave. Wave 1 and wave 2 each hold two plans that share no file):

- [x] 11-01-PLAN.md — Tracer: per-workspace v1 working dir and the v1-index-sync mirror; ingest and delete reach the query stores; ingest seam events (LRAG-01, LRAG-02, LRAG-03; wave 1)
- [ ] 11-02-PLAN.md — Two store roots never share a v1 dir; eval ingest stays in the eval store; aa_run --arm (LRAG-01, LRAG-15; wave 2)
- [ ] 11-03-PLAN.md — The one @0.2.0 opaque-boundary bump holding every driver change of the phase: file ingest, targets filter, usage, config check (exit 3), facade-free status and health, page refusal and exit 4, entity ops removed; owner grant checkpoint for the phase (LRAG-03, 05, 06, 07, 08, 10, 11, 12, 20; wave 2)
- [x] 11-04-PLAN.md — v1 retrieval ordering and selection for the KG arms (LRAG-18; wave 1)
- [ ] 11-05-PLAN.md — Uploads index their real content; suffix allowlist; per-workspace inbox emptied after each job; honest enqueued (LRAG-08, LRAG-09, LRAG-10; wave 3)
- [ ] 11-06-PLAN.md — Per-working-dir write gate (409) and job-family dispatch for GET /jobs (LRAG-04, LRAG-01; wave 4)
- [ ] 11-07-PLAN.md — v1 not configured names its keys (503); stderr tail, named malformed output, torn status read is a 409; adapter and engine only (LRAG-06, LRAG-05; wave 5)
- [ ] 11-08-PLAN.md — Interrupted documents and the retry route and MCP tool (LRAG-07; wave 6)
- [ ] 11-09-PLAN.md — Health writes nothing, needs model clients for ok, carries engine_reason (LRAG-13, LRAG-14, LRAG-06; wave 7)
- [ ] 11-10-PLAN.md — EmptyNamespaceError before any model call; recipe-only embedder-index skipped in query runs (LRAG-16, LRAG-19; wave 8)
- [ ] 11-11-PLAN.md — v1 kg_query context and prompt templates; engine-set token cap; phase offline gate (LRAG-17; wave 9)

### Phase 12: HippoRAG Fixes

**Goal**: HippoRAG ingests build a graph whose evidence resolves and accumulates correctly, its queries run only query-side work, and its documents have the same corpus lifecycle as LightRAG's
**Depends on**: Phase 10
**Requirements**: HIPP-01, HIPP-02, HIPP-03, HIPP-04, HIPP-05, HIPP-06, HIPP-07, HIPP-08, HIPP-09, HIPP-10, HIPP-11, HIPP-12, HIPP-13, HIPP-14, HIPP-15, HIPP-16, HIPP-17, HIPP-18, HIPP-19
**Success Criteria** (what must be TRUE):

  1. After a real HippoRAG ingest, a query on the PPR path returns non-empty hydrated content and every evidence ref resolves; passage vertices get non-zero reset weight from matching chunks, the fact-filter prompt contains the query text, and every chunk has a passage vertex even when OpenIE extracted no triples
  2. The HippoRAG graph accumulates correctly across ingests: a synonymy edge appears on the ingest that introduces it and is not re-emitted, co-occurrence weights follow the decided merge rule, facts keep the union of their source chunks, and token accounting never reports different counters under one label
  3. A failed HippoRAG ingest commits nothing and its refusal names the failing node and its real exception; per-chunk OpenIE failures are counted and reported in the ingest outcome, and extraction runs with bounded concurrency
  4. A HippoRAG query runs only query-side nodes with the query embedded once, returns at most top_k non-zero-score items, carries an answer with the same meaning as LightRAG's (never the evidence texts joined), and the non-debug envelope shows when the DPR fallback fired
  5. HippoRAG documents have a full lifecycle: GET /jobs returns a terminal status for a HippoRAG ingest job, /corpus, /corpus/counts and /health cover HippoRAG, delete removes the document's records, re-ingest leaves no stale chunks, old evidence refs never resolve silently to new text, and every wiring config key and docstring claim is backed by code

**Owner decisions to settle in discuss-phase**:

- HIPP-04: in-process modality failures keep ForeignEngineRefusalError or get a distinct non-'foreign' refusal (changes the consumer-visible error code)
- HIPP-08: merge rule for edge weights across ingests (sum co-occurrence; max or recompute synonymy)
- HIPP-10: a per-chunk LLM failure refuses the whole ingest, or yields a partial ingest with a failure count (new IngestJob/§18 field)
- HIPP-11: top_k from a new QueryObject field (§18 change shared with LightRAG) or HippoRAG wiring config only
- HIPP-12: remove index nodes from base.json (breaks the MODAL-04 13-position test) or prune the run to ancestors of provides in the scheduler/selectors (shared with LightRAG)
- HIPP-13: M-12/G-22 generated answer — add an LLM generator node, or evidence only with a §18 statement of the no-answer form
- HIPP-14: fired-guard envelope shape — reuse degraded/partial or add a modality-neutral field
- HIPP-15/16: M-12 corpus surface — selector parameter on jobs/corpus/counts/health or an engine-owned job registry; whether HippoRAG ingest returns a final job record; whether delete removes entities/facts that lose all provenance; re-ingest as delete-then-ingest
- HIPP-17: chunk identity — content-addressed chunk ids or a content_hash on EvidenceRef (§18 change shared with LightRAG)

**Plans**: TBD

### Phase 13: Selectors, Wiring & Runner

**Goal**: Every query arm is selectable, the runner records every node truthfully, and consumers never see internal node ids or an unstructured 500 from the wiring layer
**Depends on**: Phase 9
**Requirements**: WIRE-01, WIRE-02, WIRE-03, WIRE-04, WIRE-05, WIRE-06, WIRE-07, WIRE-08, WIRE-09, WIRE-10, WIRE-11, WIRE-12, WIRE-13, WIRE-14, WIRE-15, WIRE-16, WIRE-17, WIRE-18
**Success Criteria** (what must be TRUE):

  1. Each of the six query arms (naive, bypass, hybrid, local, global, hipporag) can be selected by a production §18.4 selector without a promote, the selector docstring states which capability set selects which arm, every resolved wiring names only nodes it contains, and a local-arm query that retrieves chunks returns non-empty evidence
  2. Consumers never see internals: stop_reason and degradation_reason come from a fixed node-free vocabulary (node detail only under debug), preflight refusals, cyclic wirings and invalid concurrency or budget values reach REST as named refusals, malformed wiring documents yield a validation report instead of an exception, and depth_label is null on partial runs and typed
  3. Every run record is complete and truthful: one NodeTrace per wiring node with completed/failed/cancelled/not-scheduled status, measured wall-clock time on failure, execution_mode stamped, unreported fields null rather than guessed, wiring identity that distinguishes the five LightRAG arms and is stable across queries on one arm, and runs that raise after executing nodes still persist a resolvable trace
  4. Guards fire only on the value they declare and misdeclared guards are refused before dispatch; the LightRAG keyword fall-through guards either fire on empty keywords or are removed with their documentation; seam events report failed versus halted correctly and ingest returns its seam events
  5. Engine internals fail by name and expose no dead API: malformed evidence output, the four advanced query members and environment-digest failures (reported by /health) are refused by name, execution placement has one source, partly-reachable refusals have tests pinning where they occur, and unused scheduling and budget APIs are wired or deleted

**Owner decisions to settle in discuss-phase**:

- WIRE-01: M-08 hybrid/global selection — a non-node-count tie-break, a distinguishing capability per arm, or an arm-name route without promote; whether {reads_graph} alone keeps resolving to HippoRAG (consumed by TOOL-09, CONN-03/05, GUI-04/05)
- WIRE-02: M-11 which node's output counts as evidence for local/hybrid/global (join-chunks, rerank or assemble)
- WIRE-03: G-21 closed set of node-free reason codes, and whether the debug trace keeps node-qualified text
- WIRE-04: depth_label as whole-wiring depth or answering node's depth; partial runs report null or omit the field
- WIRE-07: VAL-03 whether nodes calling machine-owned LLM/embedding/rerank clients count as 'pure' under CONTRACT.md:238
- WIRE-08: which output key or signal a guard reads (affects HippoRAG fact-filter and LightRAG guards)
- WIRE-09: implement v1's keyword fall-through chain switch or drop the declared guards
- WIRE-11: D-15 compute tier/feed_tier from performed interventions or report null
- WIRE-12: arm identity (wiring_id from arm name or a separate arm field) and how a refusal carries the trace_token of a persisted failed run (needed by LEDG-01 option (b))
- WIRE-13: G-26/T-17 SeamEvent.component as resolved capability or part name@version
- WIRE-15: G-31 keep platform.platform() in environment_hash or reduce it to OS and architecture
- WIRE-17: keep or delete MutableStoreComparisonExcludedError and the ingest NoWritePathForModalityError mapping
- WIRE-18: wire or delete per-node max_concurrency and budget apportionment (coordinate with WIRE-12)

**Plans**: TBD

### Phase 14: Promotion & Ledger

**Goal**: The operator verbs never fail with a 500 on any trace, every alias with a generation can be selected and resolves, and an alias's history is readable from the ledger
**Depends on**: Phase 11, Phase 12, Phase 13
**Requirements**: LEDG-01, LEDG-02, LEDG-03, LEDG-04, LEDG-05, LEDG-06, LEDG-07, LEDG-08, LEDG-09, LEDG-10, LEDG-11, LEDG-12, LEDG-13, LEDG-14
**Success Criteria** (what must be TRUE):

  1. Promote, rollback and retire never return a 500 on any trace: traces from partial or failed runs are refused by name with no ledger row written (or accepted by rollback/retire under M-06 option (b)), and the gate verbs are refused up front with one named 'gate not calibrated' refusal for every arm
  2. Every promoted alias is selectable and every alias row resolves or refuses by name: empty and hash-shaped aliases are refused by all three verbs, a HippoRAG alias either resolves or its promotion is refused before a row is written, and an alias whose row names an unresolvable arm returns a named refusal on every selector-taking route
  3. The ledger never keeps serving a tombstoned generation: retiring the version an active rollback targets is refused with ActiveGenerationRetirementError and appends nothing
  4. An operator can read an alias's full history oldest first (generation ordinal, created_at, versions, record kind); ledger connections close after every call, refused verbs on a fresh store root create no ledger.db, trace debug accepts only a JSON boolean, and trace and alias isolation follows the G-35 tenancy decision
  5. Selection, validation and the registry agree with what wirings do: capability selection matches the effects an arm exercises (writes_* never selects a read-only arm), node-kind mismatches are refused by name, every registered part is reachable or unregistered, corpus wirings load through one path, and registry/ledger/selector docstrings are current

**Owner decisions to settle in discuss-phase**:

- LEDG-01: M-06 (a) refuse every partial trace for all three verbs, or (b) let rollback and retire accept partial traces (needs WIRE-12 arm identity); name the new refusal class
- LEDG-02: G-18 whether rollback and retire apply the same partial=true rule (decide with M-06)
- LEDG-03: M-07 (a) alias resolution covers every all_wirings() name, including hipporag, or (b) refuse promotion of non-LightRAG traces until HippoRAG aliases are supported
- LEDG-04: G-17 retire guard by version or by wiring identity
- LEDG-07: add id/created_at to LedgerRecord or return a projection type; engine read only here, REST/MCP routes in Phase 16 (CONN-06/07)
- LEDG-08: G-19 confirm gate verbs are refused up front until a floor is persisted (TOOL-12), and name the refusal class
- LEDG-09: G-35 per-workspace trace/ledger namespaces or one store_root = one tenant; whether debug=true is operator-only
- LEDG-10: capability matching on wiring-node effects or Part effects; whether HippoRAG's index-side nodes count at query time
- LEDG-12: wire codebase-memory-mcp as a selectable wiring or unregister it (TOOL-15 and TOOL-18 follow)

**Plans**: TBD

### Phase 15: Offline Tooling & Packaging

**Goal**: The offline CLIs run from an installed wheel, refuse by name instead of crashing, never spend or write outside their store by default, and the evaluation and evidence records they produce state only what was measured
**Depends on**: Phase 11, Phase 12
**Requirements**: TOOL-01, TOOL-02, TOOL-03, TOOL-04, TOOL-05, TOOL-06, TOOL-07, TOOL-08, TOOL-09, TOOL-10, TOOL-11, TOOL-12, TOOL-13, TOOL-14, TOOL-15, TOOL-16, TOOL-17, TOOL-18, TOOL-19, TOOL-20
**Success Criteria** (what must be TRUE):

  1. A non-editable wheel runs the offline CLIs (aa_run, remint, check_import_boundary) with one version source and a bounded mcp extra, or the CLIs are declared source-checkout-only and excluded; the import-boundary scan skips virtualenvs, reports unparseable files as violations and catches `import_module('lightrag')`
  2. Every offline CLI parses its arguments (exit 2 on bad arguments), maps named configuration, input and provider failures to one stderr line and exit 1, spends nothing without `--spend`, and writes only into its own store — eval ingest never touches the operator corpus
  3. Parity and audit tools report what happened: partial, degraded or cyclic runs are 'inconclusive' or a non-zero exit, never 'completed'; verify_import catches a missing v2 graph; the v1 driver fails on a v1 failure and answers from the context it reports; cross-modality preflight refuses an unusable workspace without writing anything; HippoRAG can be audited
  4. Evaluation and evidence records are honest: calibration refuses unusable passes and persists a two-sided floor the promotion gate reads; bundle versions change when question text or gold ids change; parity, Falsifier 2, F-07 and cross-modality records render only states they read, compute verdicts and exit codes from results, and cite paths that exist
  5. Admission is enforced when the registry loads (§8 conditions 7, 10 and 11 for every opaque part; invalid effects, kinds and scopes refused), the artifact registry is wired or removed, the codebase-memory-mcp adapter refuses mutating tools and times out on launch, and every MCP tool publishes a non-empty description with no plan references

**Owner decisions to settle in discuss-phase**:

- TOOL-01: ship the fixture corpus and eval bundles as package data, or declare the offline CLIs source-checkout-only
- TOOL-02: M-04 (from Phase 11) — whether re-import from v1/.corpus_working_dir is the sanctioned path; M-01 how the workspace string reaches the launcher
- TOOL-07: G-27 (from Phase 11) — v1 arm answers from the aquery_data context or calls aquery unchanged; whether IN-01 (missing .env.parity treated as empty) is reversed
- TOOL-09: M-08 (from Phase 13) — cross-modality arms named explicitly by wiring id
- TOOL-11: M-04; G-34 whether eval ingest may touch the live corpus at all
- TOOL-12: G-19 where floors persist and their staleness key; lifting LEDG-08's up-front refusal once a floor exists
- TOOL-14: EV-02 accept AI-recorded causes (shown with recorded_by) or refuse them as not human-authored
- TOOL-15: MODAL-05 status — discharged by the 2026-09-10 run, or unproven
- TOOL-17: D5 wire the artifact registry into the runner or delete registry_artifact/ and stores/blob.py (decide with STOR-12)
- TOOL-18: codebase-memory-mcp stays registered or is removed (from LEDG-12); whether it keeps declaring mutates_store
- TOOL-19: MCP tools keep the single 'args' input and generic output schema, or publish per-tool schemas (affects every MCP client)

**Plans**: TBD

### Phase 16: GUI Connectors

**Goal**: The operator console has every read route it needs, served by the launcher's single engine through thin adapters, with nothing leaking store internals or credentials
**Depends on**: Phase 14 (and starts only after every engine phase, 8-15, is complete)
**Requirements**: CONN-01, CONN-02, CONN-03, CONN-04, CONN-05, CONN-06, CONN-07, CONN-08, CONN-09, CONN-10, CONN-11, CONN-12, CONN-13, CONN-14
**Success Criteria** (what must be TRUE):

  1. The operator read routes are served from the launcher's process by the single `Databasise` engine through thin adapters (no route body reads the ledger, trace store, registry or stores directly), and each new operation has an MCP tool with a COVERAGE.md row or is recorded as REST-only
  2. An operator can fetch instance info (version, workspace, client presence, write-in-flight and graph-busy flags readable during an in-progress ingest) and the wiring list (node counts, default, reachability computed from the selector rules) without the response exposing store_root, base URLs, model names or keys, and without any provider call
  3. An operator can list aliases, page an alias's history with active and tombstoned flags, list recent traces newest first, and preview a promotion (arm, mutation class, next version, promotable with reason) that writes nothing and matches the version /promote then mints
  4. An operator can page chunk refs and graph nodes (degrees computed in one batched query, optional id prefix filter) and open a node's edges, always chosen by selector and never by namespace name; an unknown node and a busy graph return named refusals, never a 500
  5. The repo holds a generated refusal catalogue and a selector-resolution fixture that tests keep in sync with the code, and a flag-gated GET /log tails the launcher's log file (404 without the flag)

**Owner decisions to settle in discuss-phase**:

- CONN-01/05 (open question 1): operator routes on the §18 app behind an explicit flag, or a separate operator app on its own localhost port (conflicts with §18.3 'no privileged client'); MCP tools plus COVERAGE.md rows, or REST-only
- CONN-06 (open question 2): relax the no-enumeration decision D-12/FA-06 for an operator alias listing, or keep a client-side ledger log
- CONN-07/08 (open question 3): return promotion_trace_ids and list trace tokens on an unauthenticated localhost app, or keep traces client-side; open question 14: filter traces to the app's workspace or treat one store root as one workspace
- CONN-09 (open question 12): HippoRAG trace previews follow whatever /promote does after LEDG-03
- CONN-12 (open question 6): return node and edge attrs (overrides API-06) or references only with a separate dereference call
- CONN-13: where the store-busy fields live (recommended: GET /info)
- CONN-14 (open questions 1 and 5): a localhost-only flag-gated log tail, or the console reads the log out of band only

**Plans**: TBD

### Phase 17: GUI Mockup

**Goal**: The operator can click through a complete static mockup of the six console screens on fixture data shaped like the real API, with every control id-stamped and every missing backend visibly marked
**Depends on**: Phase 16
**Requirements**: GUI-01, GUI-02, GUI-03, GUI-04, GUI-05, GUI-06, GUI-07, GUI-08, GUI-09, GUI-10, GUI-11
**Success Criteria** (what must be TRUE):

  1. The operator opens one static mockup file from file:// with no network access and switches between six screens (Query & Compare, Evidence & Trace, Documents & Jobs, Corpus & Health, Ledger, Graph/vector browser) with a health indicator in the header, and every control and display region carries a unique data-mock-id that matches the checked-in id list
  2. Every console control from API-INVENTORY §3 and §5.1 is present and usable against fixtures; controls whose route does not exist carry data-needs-backend naming the proposed route and show a visible 'needs backend' badge
  3. On Query & Compare the operator runs a query or an N-column compare against fixtures and sees answer, badges, evidence, tokens, seam events and the trace link in every run state, and is blocked client-side from empty text, empty capability sets, hash-shaped aliases, multi-member selectors and duplicate compare keys
  4. Every screen that issues a call renders the three server error shapes distinctly: a typed refusal banner keyed on refusal_type, field errors for a validation 422, a server-failure banner with ForeignEngineRefusalError's cause behind a toggle, and a generic 5xx view
  5. The operator walks through evidence and trace inspection, paste/upload ingest with jobs and delete, corpus and health, the ledger promote form and alias timeline (Retire disabled on the active row, the active rollback's target and tombstoned rows), and the graph/vector browser by selector — each with the client-side pre-checks that stop the inputs behind the fixed defects

**Owner decisions to settle in discuss-phase**:

- GUI-01: headless-browser tool for the test suite (proposed: Playwright for Python under the dev extra)
- GUI-02: data-mock-id naming scheme (proposed: `<screen>.<region>.<control>`) and where the id list lives (proposed: docs/gui/MOCK-IDS.json)
- GUI-03: whether 'later' §5.1 rows with no proposed route get a placeholder control or one 'planned' list entry per screen
- GUI-06: refusal catalogue generated from code (CONN-02 already generates one) or hand-written
- GUI-11: fixture shape follows open question 6 (attrs or references only, settled in Phase 16)
- End of phase: the owner freezes a mockup variant (mockup_freeze) after recording new needs back into API-INVENTORY.md (required by LIVE-09)

**Plans**: TBD
**UI hint**: yes

### Phase 18: GUI Live

**Goal**: The operator runs the whole console against the live engine — query, compare, evidence, trace, ingest, corpus, health, ledger and graph/vector browsing — from a browser served by the launcher
**Depends on**: Phase 17
**Requirements**: LIVE-01, LIVE-02, LIVE-03, LIVE-04, LIVE-05, LIVE-06, LIVE-07, LIVE-08, LIVE-09
**Success Criteria** (what must be TRUE):

  1. The operator starts the launcher bound to 127.0.0.1, opens the console in a browser, and a query run from the UI completes with no CORS error while the header shows the live /health result
  2. Query, streamed query and compare run against the live API (a stream that closes early shows 'disconnected'; one-selector and keyed-map compare responses are parsed correctly), every run lands in a client-side history, and live refusals, validation errors and 500s render through the mockup's error states
  3. The operator inspects evidence (one request per ref per session) and traces (re-requested with debug), ingests, uploads and deletes documents with Query disabled while a write is in flight and the corpus refreshing after a delete, and health and counts poll only when allowed
  4. The operator promotes a query's trace to an alias and then queries through that alias, rolls back and retires from the timeline, and browses graph nodes, node edges and chunks by selector, with the store-busy refusal rendered while the graph is held
  5. A control keeps its needs-backend badge exactly when its route is absent from the live /openapi.json, no mockup control is removed, and the frozen mockup id check exits 0

**Owner decisions to settle in discuss-phase**:

- LIVE-01 (open questions 4 and 5): same-origin static serving from the FastAPI app, a Vite dev proxy, or an opt-in allow-list; localhost-only no-auth or a reverse proxy with auth; the build stack after the mockup (React 19 + Vite + Sigma.js, or plain HTML/JS)
- LIVE-05 (open question 8): until M-04 (Phase 11) unifies LightRAG's write and read stores, the screen keeps the 'different stores' notice and the test asserts only the corpus-status path
- LIVE-07 (open questions 2 and 3): if alias enumeration and trace listing stay closed (Phase 16), the pickers stay client-side with their needs-backend badges
- LIVE-08: depends on the Phase 16 connector routes and open question 6
- LIVE-09: depends on the mockup_freeze set at the end of Phase 17

**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18. Dependencies allow 9 and 10 in parallel after 8, and 11, 12 and 13 in parallel once their prerequisites close; the owner's rule that every engine phase (8-15) completes before any GUI phase (16-18) still holds.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 8. Run the Engine | 10/10 | Complete    | 2026-10-16 |
| 9. Inputs, Errors & Security | 10/10 | Complete    | 2026-10-17 |
| 10. Stores, Locking & Data Integrity | 12/12 | Complete    | 2026-10-17 |
| 11. LightRAG Corpus Path | 2/11 | In Progress | - |
| 12. HippoRAG Fixes | 0/TBD | Not started | - |
| 13. Selectors, Wiring & Runner | 0/TBD | Not started | - |
| 14. Promotion & Ledger | 0/TBD | Not started | - |
| 15. Offline Tooling & Packaging | 0/TBD | Not started | - |
| 16. GUI Connectors | 0/TBD | Not started | - |
| 17. GUI Mockup | 0/TBD | Not started | - |
| 18. GUI Live | 0/TBD | Not started | - |

v1.0 (Phases 1-7, 64 plans) shipped 2026-09-12 — see `.planning/MILESTONES.md`.

---
*Last updated: 2026-10-14 at v1.1 roadmap creation*
