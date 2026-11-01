# Milestones

## v1.1 Engine Fixes + Operator Console (Shipped: 2026-11-01)

**Phases completed:** 11 phases, 136 plans, 66 tasks
**Timeline:** 2026-10-14 → 2026-11-01 (18 days, 1,096 commits)
**Closeout:** override_closeout — all 11 phases verified passed; 168/169 requirements satisfied
**Known verification overrides:** 3 newly acknowledged, 5 carried forward from a prior close (see STATE.md Deferred Items)
**Audit:** `.planning/milestones/v1.1-MILESTONE-AUDIT.md` (tech_debt); debugging and security battery: `.planning/v1.1-DEBUG-SECURITY-BATTERY.md`

### Known Gaps

- RUN-11 — live embedder index-reproduction runs (`tests/parity/test_embedder_index_reproduction.py`); owner-deferred to TESTING-PLAN.md §2, deferred-approved in the BAK records.

**Key accomplishments:**
- Installed `databasise-rest` console script: argparse, store flock, shared client builder, `create_app`, one-worker uvicorn, GET /health 200, plus a `live` pytest marker that makes the default suite offline
- A provider response with no usage is now one unbudgetable call, and empty choices, None content and mis-sized or badly indexed embedding batches raise named errors; out-of-order embeddings come back in input order
- The section 18.5 tool-roster cross-check now reads a live `databasise/evidence/COVERAGE.md` and is proven non-vacuous, and `mcp_sdk_is_installed()` finds the real SDK through `PathFinder` on the project-stripped `sys.path` instead of reporting False when the CWD shadows `mcp`.
- Upload path-safety test now inspects the inbox file on disk, and the delete round trips assert counts fall from 1 to 0 through a stub-delete hook shared with the status fake; both fail under the mutations they claim to catch.
- HttpRerankClient over the LightRAG v1 cohere, jina and aliyun bindings, wired into the shared builder only when RERANK_BINDING and its three keys are all present, with GET /health reporting an additive `clients` presence map so an unwired rerank reads `false`.
- `databasise-mcp` console script serving the nine §18 tools over stdio, sse or streamable-http behind the same store flock as `databasise-rest`, with `httpx` promoted to a runtime dependency and cross-process tests proving a second launcher is refused by name while the first keeps answering `/health`.
- All six parity entry points (import, HippoRAG build, single arm, comparison, cross-modality, storage audit) now take the cross-process store lock on `v1/.parity_v2_store` and refuse by name, with the holder PID, instead of failing later inside RocksDB.
- RUN-12 gate script that runs `pytest` and `python -m pytest` back to back and fails on any failure or environment-contradicting skip, plus a conftest socket guard that refuses non-loopback connects from tests not marked live
- Strict-boundary parity test, owner-approved rerank wording in RUN-05 and the ROADMAP, and the deferred live runs and ledger steps parked in TESTING-PLAN and this file; no live run, no ledger write.
- The multipart upload route now reports the refusal a selector or file actually breaks (oversize is a 422, never a 500), a null or empty selector field means the default selector, and rest._status_for gives 404 to the four not-found lookups and 422 to every other refusal.
- A malformed caller document id is refused as InvalidDocumentIdError before any write or wiring on every ingest and delete entry point, and page limits/offsets are bounded on REST, MCP and in-process by PageBoundsError through one shared checked_page.
- A v1 engine failure on any route is now one structured ForeignEngineRefusalError fault (502 run failed or malformed output, 503 v1 unavailable) with an allow-listed failure_class, no stderr on the wire, and the full cause logged server-side once.
- A path-like evidence namespace is refused by a fullmatch allow-list before any store is opened or directory created (resolve_evidence now builds only the vector store), and blank query text, blank or 0-byte documents and non-alphabet base64 are refused by name.
- `Selector(capability=[])` is refused by name in `resolve_selector` and `render_selector_key`, so it never reaches the bypass wiring or renders an empty compare key on any route, and `Databasise.promote` refuses an empty or hash-shaped alias before any ledger write.
- `Databasise.compare` now checks every comparison key, resolves each selector once, runs the `mutates_store` check, and only then executes the resolved wirings, so a colliding or unresolvable comparison spends no LLM call and writes no trace, and a mid-compare alias repoint cannot change what runs.
- A seam ingest now runs v1 in a per-workspace dir and a new opaque `lightrag/v1-index-sync` part mirrors v1's PROCESSED rows into the staged v2 stores, so the naive arm retrieves and resolves the document, and a delete prunes it through a mirror manifest that never touches parity-imported rows.
- Two apps on two store roots now provably send every LightRAG corpus op their own `<store_root>/<workspace>/lightrag-v1` and never list each other's documents, and `aa_run --arm` queries the eval store with the same selector `corpus_ingest --arm` ingested with, returning evidence through the real v1 driver.
- Both LightRAG corpus ports are now `@0.2.0`, with fresh admission records that number CONTRACT §8 correctly. Through the real v1 driver, a staged file is indexed from its own bytes, spend is metered with `TokenTracker`, duplicates count as zero, and processing touches only the run's targets. Missing configuration exits 3 and names keys only. Health and status are facade-free, and a torn doc-status file exits 4.
- The hybrid, local and global arms now retrieve the way v1 `kg_query` does. Entity and relation lookups search with the embeddings of v1's ", "-joined keyword strings, produced by one batched embed call. One-hop relations are sorted by (rank, weight). KG chunks are selected per side with a working VECTOR pick. join-chunks dedups by chunk id and emits vector chunks first. Rerank receives the query.
- A raw upload keeps only a v1-pinned, validated suffix, is staged as `<store_root>/<workspace>/corpus-inbox/<id><suffix>` so v1 parses its real bytes, and is removed with its `__parsed__` copy after the job; unsupported types are refused by name before any write, and re-ingests report `enqueued 0` under v1's track id.
- GET /health now writes nothing, reports `v1_reachable` instead of `storages_initialized`, names missing v1 keys in a new `engine_reason` field, needs both model clients for `ok`, and reports a raising probe as a `corrupted` store instead of a 500.
- A query on a never-populated LightRAG vector namespace is now a named 422 `EmptyNamespaceError` raised before any model call. Reading a namespace creates no directory. Query traces no longer carry the no-op `embedder-index` node, which stays in every wiring as the index recipe.
- The hybrid, local and global arms now answer the way v1 `kg_query` does. The model receives v1's `rag_response` as the system message, filled with a `kg_query_context` of budgeted entity rows, relation rows, chunks and a reference list, and the query as the user message. The naive arm uses `naive_rag_response`, and bypass sends the bare query. The engine always caps the context. The full offline gate passes under both pytest styles: 2036 passed each, exit 0.
- A HippoRAG write refusal now names the failing node privately (chunk-embed) with its real ClientNotWiredError cause, a declared fallback can no longer refuse a write, and in-process provider errors reach the server log and debug trace with keys and URLs removed.
- parse_wiring now reports malformed wiring documents (RFC 6901 pointers, one entry per cyclic node, kind-mismatch, no registry leak) and `validator/execution_mode.py` is the only execution-placement source.
- Local, global and hybrid are now selectable by `reads_vector:<namespace>` capability tokens declared on a new `Part.reads_namespaces` field, and part registration refuses any effect outside the frozen 17-member `Effect` literal.
- Run records now validate against a derived Databasise trace schema (frozen schema plus 11 recorded amendments); NodeTrace carries `status`, `execution_mode`, `spent` and `allowance`, and `cache_hit`, `tier` and `feed_tier` are null instead of guessed.
- `run_wiring` now dispatches one node at a time and returns one NodeTrace per parsed node (completed, failed, cancelled, not-scheduled), a failed node reports its measured wall time, nothing a node or post-dispatch step does escapes, and consumer-visible stop reasons are the closed codes `node_failed`, `placement_refused`, `budget_halt`, `cancelled`.
- `depth_label` is now `Depth | None` (null when no provides node returned a completion), a retrieval node output without `items` is a named `MalformedDriverOutput` refusal instead of a bare `KeyError`, and `query`/`query_stream`/`compare` no longer carry a `debug` keyword they discarded.
- LightRAG `assemble` now emits the chunks it put into the context as `items`, the local, global and hybrid arms mint evidence from it, bypass declares `evidence_position: null`, and `parse_wiring` reports any `provides` entry or evidence node the wiring does not contain.
- `compare` with one selector now refuses a `mutates_store` wiring before any node runs, `/health` reports an environment-digest failure instead of `ok`, and a mutating node that raised reports a `failed` seam event instead of `halted`.
- A cyclic wiring is now one named 422 on all four write and query paths, `max_concurrency` and `token_allowance` are never coerced, a misdeclared guard is refused before any node runs, and every runner pre-flight error reaches REST as a named refusal instead of a 500.
- The unread top-level `guards` arrays are gone from the local and global LightRAG arm patches, the README and CODEBASE-MAP no longer claim them, and the resolved arms hash identically before and after.
- A query that runs nodes and then refuses now leaves a resolvable trace (the refusal carries a public `trace_token`), two answering provides nodes are a named 422 refusal instead of a 500, and both consumer reason fields are mapped to the closed codes at response time by a check that never raises.
- Run identity names the arm and is stable across queries on one arm; guards read one declared signal key; the environment hash drops the kernel string; the dead apportionment strings are gone; every shifted hash is annotated once.
- Every SeamEvent now reports `component == "mutates_store"`; the LightRAG ingest and full-delete events no longer name `lightrag/...@version`.
- The offline wheel now ships databasise.tools, the eval bundles and both corpus fixtures with a single version source and an `mcp<3` bound, and the import-boundary scan skips virtualenvs, reports unparseable files, catches `from importlib import import_module`, and runs from a wheel.
- `databasise/cli.py` holds the exit table, the one-line `refuse`, the TOOL-04 refusal tuple, `positive_int` and the selector-vs-named-wiring check; six spend-by-default CLIs accept `--spend` with unchanged behaviour and the shared tests already pass it.
- `parity.run_comparison` records a partial, degraded or cyclic decomposed run as inconclusive (exit 3), verifies the index the v1 arm really reads, refuses bad variance settings and unknown queries before anything is spent or written, and defaults to a call-count projection.
- The v1 driver makes one `aquery_llm` call per job, reports a v1 failure as `V1QueryFailedError` (exit 1), and returns `None` keywords when v1 reports none; `run_v1_arm` loads the env through `load_env_file` first, so a missing file is `MissingParityEnvError` before anything launches.
- `storage_audit` and `run_arm` accept `--arm hipporag` (HippoRAG's seven index nodes never dispatch), the audit exits 3 with `partial:` or `cycle:` and reports never-dispatched nodes as `unreached`, and both CLIs print an estimate and `mode: estimate-only` unless `--spend` is given.
- `run_cross_modality` proves before any read or spend that its two capability selectors resolve to arms `naive` and `hipporag`, refuses an unusable workspace through `load_committed` without creating anything, keeps the records of a refused run, records `queries_hash` for custom query lists, and is estimate-only without `--spend`.
- A bare `build_hipporag_index` call prints the HippoRAG ingest estimate and `mode: estimate-only` and touches nothing; `--spend` builds on an empty store root and refuses a chunk namespace that is empty or differs from the corpus chunking.
- A calibrated two-sided A/A floor is persisted per arm hash in `floors.db`, `aa_run --spend` writes it, and `promote` lifts `GateNotCalibratedError` for an arm whose own traces have a fresh floor, reaching the RIG F3.2 posture without appending anything.
- Falsifier 2's verdict and exit code now follow its probe results, f07_report has a computed-record `main`, MODAL-05 has one stated value in both committed records, and the evidence, registry and env-loader docstrings state current facts.
- All nine spending CLIs are pinned estimate-only by one parametrised row, all six refusing CLIs are pinned to one stderr line and exit 1 across 58 injected failures (which also exposed that `remint` let a mint-time `BundleDriftError` or `MissingTargetFamilyError` escape as a traceback, now fixed), and `check_offline_suite.py` passes in both styles with 2877 passed, 4 deselected.
- mockups/build.py gained --src/--out/--check; a byte-identical live console is built from a copied source tree as databasise.console package data, and console-a is frozen with the id check exiting 0.
- `databasise-rest --console` serves the packaged console at GET /console with a sha256 hash-source CSP, and an in-process uvicorn + Chromium harness proves a page fetch POST /query returns 200 with no CORS message.
- One transport (`api`), a live `GET /health` header with a 60 s abort, a run-time badge rule driven by the live `/openapi.json`, absent-route disabling with a visible reason, hidden mock chrome, and `GET /info` instance and store-busy chips.
- Query mode runs against the real server: one `POST /query` or an SSE `POST /query/stream` read with a ReadableStream parser, every evidence row rendered (clones past the literal slots), a reload-safe run history in sessionStorage, and every real error shape (typed refusal with the real status, validation field marks, 500 with the log tail, unreachable) on the Query screen.
- Compare runs against the real server: one `POST /compare` per run, Default sent as `{}`, a bare envelope for one selector and a map read by comparison key for two or more (a key named `answer` is just a column), per-column trace tokens, extra server keys as cloned columns, blocker re-check, abort on mode switch or screen leave, and every picker listing `alias (active_version)` from `GET /ledger/aliases` or the browser's ledger log.
- Open on a live evidence row sends the envelope's EvidenceRef to `POST /evidence/resolve` unchanged and caches the record per (namespace, ref) for the session; Load trace and every Debug toggle send `POST /trace/resolve` with the current flag; the inspector's Open trace loads the trace of the run the row came from.
- The first show of Corpus & Health sends `GET /corpus?limit=50&offset=0` and `GET /corpus/counts`, paging follows `next_offset`, both polls obey their skip and pause rules, the health error survives table actions, and Retry posts for the document on the pressed row.
- Submit document sends `POST /documents`, the job id lands in the client job list and loads in the drawer, upload is real multipart with an indeterminate line, Run is disabled while any write is in flight, and a delete is sent only from Confirm, keeps its dialog open until the answer and reloads the Corpus table and counts.
- Promote sends `POST /promote` only from the dialog's Promote and the promoted alias answers a query through the Query this alias link; the timeline follows the server's `active` and `tombstoned` flags, Roll back and Retire are sent only from Confirm with dialogs that stay open until the answer, and without `--operator` the pickers, timeline, Preview and trace source fall back to this browser's ledger log.
- The Graph screen reads POST /graph/nodes, /graph/node and /chunks by selector with next_offset paging, opens a chunk in the Evidence Inspector with its EvidenceRef unchanged, renders UnknownGraphNodeError and a StoreBusyError refusal (proved with a raw pycozo lock) with a Retry request that repeats the failed read, and keeps the attrs and count controls disabled and badged.
- The live console ships with no screen fixtures and every present route wired; the owner approved the click-through with real clients; R18-07 is fixed test-first so a streamed query blocks the health poll until its SSE body settles; and LIVE-01 to LIVE-09 are linked, proven fail-first at their RED commits and done through the kit script.
- A closing debugging and security battery (three STRIDE audits all SECURED, a 1,161-request REST probe, a ~60,000-input fuzz pass, a six-dimension adversarially verified sweep) found 27 defects, all fixed test-first: no caller input can turn a named refusal into a 500 (lone surrogates, NaN/Infinity, deep nesting, oversize ids, offsets and query text), echoed caller values are bounded, and the Cozo release race, kv probe false-corruption and five console bugs are closed.

---

## v1.0 Fully Agnostic System (Shipped: 2026-09-12)

**Phases completed:** 7 phases, 64 plans, 163 tasks
**Timeline:** 2026-08-29 → 2026-09-12 (15 days, 569 commits)
**Codebase:** `databasise/` 48,485 lines of Python, 105 test modules, suite 1068 passed / 1 skipped at close
**Closeout type:** override_closeout (see Known Gaps)

**Delivered:** An embeddable, in-process RAG machine (Cozo, Faiss, SQLite; no server, no container) that runs any modality as a wiring of versioned parts behind one closed §18 envelope, reachable identically in-process, over REST and over MCP. LightRAG's query side is decomposed into 17 primitive parts; its ingest core and codebase-memory-mcp are admitted opaque under §8; HippoRAG 2 is fully decomposed into 13 parts; both modalities run side-by-side on one corpus and are compared in one call with no consumer-visible field changing (MODAL-05, the core-value proof point). Promotion and rollback ride an append-only ledger with atomic operator verbs.

**Key accomplishments:**

- Machine core: structured-concurrency runner metering spend at each node's declared boundary, RFC 8785 + SHA-256 component identity, content-addressed artifact registry, KV shared/quarantined scope rule enforced at load time (Phase 1).
- Falsifier 2 passed: `effective_depth` and `execution_mode` computed from wiring + registry, self-declaration refused by name; measurement posture pinned off by default (Phase 2).
- LightRAG query side re-cut into 17 of 18 §L.1 positions with a five-arm parity harness that refuses rather than fabricates verdicts; hybrid/local/global excursions disclosed, not hidden (Phase 3).
- The §18 seam: query object, four selectors, explicit refusals, citations, budget tokens with `counted_by`, trace reference, single event-shaping path shared by REST streaming and in-process streaming (Phase 4).
- Opaque admission of LightRAG ingest/delete (subprocess-hosted, quarantined) and codebase-memory-mcp (whole-engine, Falsifier 4 run twice), plus MCP tool set with proven REST parity (Phase 5).
- HippoRAG 2 fully decomposed (13 positions, whole-graph PPR via bulk export), eval bundle minted, and the first real LightRAG-vs-HippoRAG side-by-side run on the 20-document parity corpus (Phase 6).
- Append-only promote/rollback/retire ledger with `BEGIN IMMEDIATE` spans and a `UNIQUE(alias, minted_version)` backstop, identical over in-process, REST and MCP (Phase 7).

### Known Gaps

Carried out of v1.0 under written, owner-originated gate amendments. Tracked in `.planning/TESTING-PLAN.md`, not in a phase.

- **MACH-03** (Phase 6): first A/A calibration / Falsifier 5 never run; no p95 floor exists. Driver `databasise/eval/aa_run.py` and all preconditions are built and tested; only real judge spend is missing. Deferred a fourth time by `06-GATE-AMENDMENT.md` to the first gate-adjudicated promotion.
- **MODAL-01** (Phase 3): decomposition and measurement complete; two owner-only CONTRACT §5 items open (human-authored causes for 20 excursions, q1/q2 answer spot-check). Deferred by `06-GATE-AMENDMENT.md`.
- **HARD-01, HARD-02, HARD-04** (Phase 7): deferred out of the milestone by `07-GATE-AMENDMENT.md` to the owner's hardening pass or the first gate-adjudicated promotion.

Known verification overrides: 5 newly acknowledged, 0 carried forward from a prior close (see STATE.md Deferred Items). Phases 3 and 6 closed at `human_needed` / `gaps_found`; phases 4, 5 and 7 read stale in the projection but their VERIFICATION.md reports are `passed`.

**Audit:** `.planning/milestones/v1.0-MILESTONE-AUDIT.md` — 29/34 requirements satisfied, 7/7 integration points wired, 4/4 end-to-end flows complete.

---
