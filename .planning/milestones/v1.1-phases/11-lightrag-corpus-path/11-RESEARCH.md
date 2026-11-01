# Phase 11: LightRAG Corpus Path - Research

**Researched:** 2026-10-17
**Domain:** Python seam engine (databasise) bridging an opaque v1 LightRAG 1.5.4 subprocess (ingest/delete/status) to the v2 kv/vector/graph stores the query arms read; v1 `kg_query` answer fidelity.
**Confidence:** HIGH for v1 behaviour (every behavioural claim below was run against the real v1 driver with a loopback stub model server this session); MEDIUM for design recommendations that go beyond D-01..D-16.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**A. Write path and scoping (M-04, M-12, LRAG-01/02/03/15/19/20)**

- **D-01 (M-04 = option b):**
  - v1 ingests and deletes through the existing driver, in a **per-workspace v1 working dir** under the store root: `<store_root>/<workspace>/lightrag-v1/` (LRAG-01).
  - A new opaque-boundary part, `lightrag/v1-index-sync`, runs as a second node in `corpus-ingest.json` and `corpus-delete.json`, after full-ingest or full-delete. It mirrors v1's committed index into the v2 stores the query arms read. It upserts every row of PROCESSED documents and deletes v2 ids that v1 no longer holds.
  - The sync declares `writes_kv`, `writes_vector` and `writes_graph`, and writes only through `ctx.stores`. It is therefore covered by Phase 10's prepare-all/commit-all (D-07) and drop-on-failure (D-06), and its MACH-11 touches are observed by the machine (LRAG-03).
  - It reuses `parity/import_index.import_v1_index`'s readers, refactored so they can be called with staged stores. It copies stored vectors and never re-embeds, so it spends nothing on LLM or embeddings.
  - The sync reads the v1 backends JsonKV, Faiss and Cozo. Any other configured v1 backend is refused by name at the start of the run.
  - `full_delete` stops reporting touches it never made (LRAG-02).
  - A residual window exists: v1 has already committed when v2 commits. If the v2 commit fails, the stores diverge until the next sync heals them. Document this in the engine docstring. A `shortcut:` comment marks the O(corpus) mirror cost per write.
- **D-02 (M-12):** `GET /jobs/{job_id}` dispatches on the modality family that minted the job. The engine records `job_id → family` at ingest in one small sqlite file under the store root. A HippoRAG job returns a terminal status (`processed` once its run committed), and a LightRAG job asks v1 as today. An unknown id stays `UnknownJobError` (404). This settles HIPP-15's job semantics for Phase 12.
- **D-03 (LRAG-15):** `aa_run` keeps the default selector (lightrag-base) and gains `--arm`, which TOOL-11 requires. The eval engine already has its own store root, so D-01's per-workspace dir keeps eval ingest out of the operator corpus.
- **D-04 (LRAG-19):** `embedder-index` is marked recipe-only and skipped in query runs. No node, no `calls_embedding` and no spend appear in query traces. `recipe.embedding` in `base.json` stays, so the recipe and RUN-11 paths keep working.
- **D-05 (LRAG-20):** remove the half-wired `entities` and `entity_info` driver ops from the driver and its stub. Rewrite the live proof in `tests/seam/test_delete_document.py` so it reads `source_id` from the v2 graph after the D-01 sync. Remove the two test-support rows from `COVERAGE.md`.
- **D-06 (opaque-boundary version):** every change to an opaque part's effects, verdicts or driver protocol in this phase (LRAG-03, 11, 12, working_dir, usage) is batched into **one** `@0.2.0` bump with re-admission per `OPAQUE-BOUNDARY-RULE.md` §2. Do not bump once per plan.

**B. Write lifecycle (LRAG-04, 07, 08, 09, 10)**

- **D-07 (LRAG-04):** a LightRAG ingest or delete takes an in-process lock per v1 working dir. Phase 8 already guarantees one engine process per store root. A second write while one holds the lock is refused **immediately** with `StoreBusyError(store_kind="corpus")`, which maps to 409 (Phase 10 D-02). It does not wait.
- **D-08 (LRAG-07, G-33):**
  - `GET /corpus` reports a document left in PARSING, ANALYZING or PROCESSING as `"interrupted"` when no job holds the D-07 lock.
  - A new route, `POST /documents/{id}/retry`, plus a matching MCP tool, runs a driver op that reprocesses only interrupted documents. It refuses a document that is not interrupted with a named refusal. The route and tool get §18.5 COVERAGE rows.
  - If the research finds that v1 cannot process only the named ids, v1's auto-recovery side effect stays. In that case the LRAG-07 clause "the next ingest does not reprocess it" is amended to "is reprocessed by v1's recovery; reported as interrupted until then". That is a Claude decision under the owner's delegation; record it as an exception clause in REQUIREMENTS.md.
- **D-09 (LRAG-08, LRAG-09):**
  - Raw uploads stay staged. The inbox becomes per-workspace: `<store_root>/<workspace>/corpus-inbox/`.
  - The staged file name keeps a validated suffix taken from `file_name`. The accepted suffixes are those v1's parser handles, listed explicitly from the v1 parser routing, at least `.txt`, `.md`, `.pdf` and `.docx`.
  - The driver enqueues the staged path through v1's file-ingest path. It no longer uses the `ids=` route, which forced RAW mode with empty text. That way v1 parses the real bytes.
  - An unsupported or missing suffix is refused by name before anything is written (`UnsupportedUploadTypeError`, 422).
  - The staged file is removed once the ingest returns (v1 has read it, since the driver waits for the pipeline) or is refused. On a timeout it stays and is logged, as Phase 9 does today. `DELETE /documents/{id}` removes any remaining inbox file for that id.
  - A per-workspace inbox makes the Phase 9 owner-record sidecar redundant: delete it.
  - `text ""` and whitespace-only text stay refused (Phase 9 D-08).
  - Path safety still holds (RUN-09): generated names only, inside the inbox.
  - The protected test `tests/seam/test_rest_corpus_endpoints.py` pins the old flat layout. The plan needs the owner's `grant-check-edit` for it.
- **D-10 (LRAG-10):** the driver reads v1's doc_status before and after the enqueue. When v1 dropped the document (existing id, same basename, same content hash), the response reports `enqueued: 0` with v1's track_id. No new refusal and no replace.

**C. Faults, health and metering (LRAG-05, 06, 11, 13, 14)**

- **D-11 (LRAG-05):** v1 stderr goes to the server log only (Phase 9 D-04 stands). The requirement's "unless operator" clause has no operator to apply to while seam authentication is undecided.
  - `CorpusOpSubprocessError` keeps the last 2000 characters of stderr (the tail, not the head) for the server log.
  - Non-JSON driver stdout raises a named refusal.
  - The driver checks its limits.
  - The stale docstrings are fixed.
- **D-12 (LRAG-06; narrow amendment of Phase 9 D-04):** a v1 configuration refusal **may name the missing configuration keys**, never their values, exactly as LRAG-06 asks. Every other refusal still carries no env-var names. Record this as an exception note on Phase 9 D-04 in this CONTEXT, and as a clause in REQUIREMENTS.md under LRAG-06. `/health` reports the reason through an existing or minimal new §18 field, which the planner settles.
- **D-13 (LRAG-11):**
  - The driver captures v1's token usage by passing `token_tracker=` into its LLM and embedding functions, and returns usage for ingest and delete.
  - `corpus-delete.json` and the full-delete part declare `calls_llm`.
  - full-ingest and full-delete report `counted_by` from the captured usage.
  - The dead branch at `full_ingest.py:227-234` becomes the real path.
- **D-14 (LRAG-13, LRAG-14; builds on Phase 10 D-14):**
  - Health performs no writes. The driver's health op no longer builds the v1 facade, because that created the working dir. Do the existence check on the engine side and merge `storages_initialized` into one "v1 reachable" fact.
  - `working_dir_present` reports the truth rather than false on any failure.
  - Health is not `ok` without model clients (LRAG-14). The HealthReport docstring sentence "clients never affect status" (Phase 8 D-08) is amended.
  - A single-modality install reads `degraded` while the other modality's stores are `absent`. This is accepted as the D-14 meaning: health reports every shipped namespace.

**D. Query fidelity (LRAG-16, 17, 18)**

- **D-15 (LRAG-16):** querying an arm whose vector namespace has never been populated is refused before the run, with a named `EmptyNamespaceError` (422, public field `store_kind` only), so no keyword LLM call is made. The read-path `select` opens without creating anything. The envelope shape is unchanged.
- **D-16 (LRAG-17, LRAG-18 = match v1):**
  - The hybrid, local and global arms use v1 `kg_query`'s context construction (`kg_query_context`, budgeted entity, relation and chunk sections, token allocation). They use the same prompt templates (context as the system prompt, query as the user message) and v1's retrieval ordering and selection.
  - The v1 prompt strings are duplicated, because lightrag cannot be imported. A test diffs them against `v1/lightrag/prompt.py`.
  - The LLM client gains system-message support.
  - The tokenizer stays the existing approximation. Any tokenizer dependency that fetches encodings at runtime would break the offline suite (RUN-12). Record the token-count deviation as `shortcut:` with its upgrade path.
  - Rerank gets no API toggle; it stays off in shipped wirings (Phase 8 D-09). Only fix the empty-query bug.

### Claude's Discretion
- Exact names and placement of new refusals (`UnsupportedUploadTypeError`, `EmptyNamespaceError`) and of the retry driver op, following `refusals.py` house style.
- The job-family record's schema.
- How the sync detects v2 ids that v1 no longer holds (a set difference per namespace is expected).
- Whether LRAG-12's §8 renumbering rides in the D-06 bump plan.

### Deferred Ideas (OUT OF SCOPE)
- **M-04 option (a)**, machine-native LightRAG ingest: revisit if v1's subprocess becomes a constraint.
- **Migration of `v1/.corpus_working_dir`:** the existing operator corpus is migrated with TOOL-02 (`import_index --v1-working-dir`, Phase 15). Until then, that data is not visible under the per-workspace dir.
- **A real tokenizer** for v1 token-allocation fidelity: wait for an offline-safe encoding.
- **An operator field exposing v1 stderr:** revisit with the seam authentication decision.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| LRAG-01 | Every LightRAG corpus op passes a per-app v1 working_dir, never `DEFAULT_V1_WORKING_DIR` | §Pattern A (working_dir plumbing), Pitfall 3 |
| LRAG-02 | Ingested doc retrievable via /query + /evidence/resolve; gone after DELETE; full-delete reports only real touches | §Pattern B (sync), spike 4 (import->query->resolve proven), Pitfall 6 |
| LRAG-03 | full-ingest declares mutates_store; admission names its storage; ingest emits MACH-11 events | §Pattern G, Pitfall 7 (IngestJob gains seam_events) |
| LRAG-04 | Concurrent writes serialized or refused | §Pattern C (lock), Finding 3 (RocksDB lock proven) |
| LRAG-05 | Adapter failures readable: 2000-char tail, non-JSON refusal, driver limits, stale docstrings | §Pattern A, Finding 3; SEAM-05/06 already done by Phase 9 |
| LRAG-06 | Missing v1 config -> named refusal listing key names | §Pattern D (exit code 3 protocol), Pitfall 9 |
| LRAG-07 | Interrupted docs visible; retry action; next ingest does not reprocess | Finding 2 (driver-side filter proven), §Pattern C |
| LRAG-08 | Uploads index real content; validated suffix; no dup- row for different content | Finding 1 (INPUT_DIR, `__parsed__`, id mapping), suffix list |
| LRAG-09 | Per-workspace inbox, removed after job / refusal / delete | Finding 1 (v1 MOVES the file to `__parsed__/`) |
| LRAG-10 | `enqueued` = what v1 enqueued; job_id = recorded track_id | Finding 4 (dup row shapes proven) |
| LRAG-11 | Write-side LLM spend metered | Finding 5 (TokenTracker shape), §Pattern A |
| LRAG-12 | §8 conditions numbered correctly in both admission records | §Pattern G (exact CONTRACT §8 text) |
| LRAG-13 | /health writes nothing | §Pattern E; Phase 10 already made store probes read-only |
| LRAG-14 | /health reports only checked facts; clients required for ok | §Pattern E; vector probe + HippoRAG namespaces already done by Phase 10 |
| LRAG-15 | Eval ingest never writes operator corpus; aa_run reads same store | §Pattern A (D-01 already satisfies), eval section |
| LRAG-16 | Unpopulated namespace refused by name; read-path select creates nothing | §Pattern F step D-15, Pitfall 5 (STOR-02 test ordering) |
| LRAG-17 | KG context + v1 prompt templates + token cap | §Pattern F gap table (file:line) |
| LRAG-18 | v1 ordering and selection | §Pattern F gap table |
| LRAG-19 | No embedder-index in query traces | §Pattern F, Pitfall 8 (promotion mutation-class ripple) |
| LRAG-20 | Entity driver ops exposed or removed | D-05 removal; §Pattern A protocol pin |
</phase_requirements>

## Summary

The v1 subprocess path already works end to end offline: I ran the real `v1_corpus_driver_script.py` under `v1/.venv/bin/python` against a loopback OpenAI-compatible stub server for ingest, status, delete-adjacent state, kill-on-timeout and retry, and imported the resulting working dir with the existing `import_v1_index` into v2 stores and queried it through the real `Databasise`. So the SC1 harness is feasible with **no driver stub mode**: point the existing env overlay at a loopback stub (RUN-12 only blocks non-loopback sockets in the test interpreter). The research changes the plan in twelve ways (Findings 1-12 below); the largest are: file ingest needs `INPUT_DIR` and gives v1-derived doc ids that must be mapped; v1 cannot restrict processing by public API but a driver-side filter on `doc_status.get_docs_by_statuses` does exactly that (so D-08 needs no amendment); every driver op fails while another driver process holds the same working dir (RocksDB lock), so reads during a write must be refused or serialized; and several protected tests collide with locked decisions.

**Primary recommendation:** Build in this order: (1) one boundary-bump plan (driver protocol, adapter, both parts at @0.2.0, new sync part, wirings, compat pin, OPAQUE-BOUNDARY-RULE.md) with the hermetic real-driver harness landing in the same wave as its first consumer; (2) engine write lifecycle (lock, per-workspace inbox, id mapping, job-family db, interrupted/retry); (3) sync + store read methods; (4) health; (5) query fidelity; (6) LRAG-19/15 and docs. Put ONE consolidated owner grant checkpoint before the first protected-file edit (list in §Protected Tests).

## Headline Findings (these change the plan)

1. **File ingest needs `INPUT_DIR`, moves the file, and changes the doc id.** [VERIFIED: spike2, v1/lightrag/pipeline.py:3127-3241, utils_pipeline.py:540-542] With `docs_format="pending_parse"` and no `ids=`, v1 stores only the canonical *basename* as `file_path` and looks for the file under `INPUT_DIR` (else `cwd/inputs`). Passing the absolute staged path with `INPUT_DIR` unset gave status `failed`, error `legacy source file not found: aaa.txt`. The driver must set `os.environ["INPUT_DIR"]` to the inbox before the enqueue (`configured_input_dir()` reads `os.getenv("INPUT_DIR", "")` on every call). After a successful parse v1 **moves** the source to `<INPUT_DIR>/__parsed__/<name>` (spike2: inbox listing shows `__parsed__/aaa.txt`, `__parsed__/bbb.txt`). The v1 doc id is `"doc-" + md5(canonical_basename)` (pipeline.py:497-499, confirmed: `md5(b"slow1.txt")` equals the id v1 minted). Our `document_id` therefore **cannot** be v1's doc id on this path; see Pattern C for the mapping.
2. **D-08 holds without the fallback amendment.** [VERIFIED: pipeline.py:107-113, 927-1137; spike3] `apipeline_process_enqueue_documents()` takes no arguments and processes every doc in `_INFLIGHT_DOC_STATUSES` (`DocStatus.PROCESSING, DocStatus.FAILED, DocStatus.PENDING, DocStatus.PARSING, DocStatus.ANALYZING`) - FAILED docs are retried on every call too. But the driver (a leaf script it owns) can wrap `rag.doc_status.get_docs_by_statuses` on the instance to return only chosen ids. Spike3: after a killed ingest the doc stays `processing`; an unrelated ingest with the wrapper left it `processing` (2 LLM calls = only the new doc); a retry op with the wrapper processed only it to `processed`. Use the same wrapper for **ingest** (restrict to this run's track) so "the next ingest does not reprocess it" is true as written.
3. **Any second driver process on a working dir fails while one runs.** [VERIFIED: spike7] A `status` op started while an ingest subprocess held the dir exited non-zero in 1.1 s: `CorpusOpSubprocessError ... cozo_impl.py", line 196, in __post_init__ ... CozoClient("rocksdb"...`. Every driver op builds the full `LightRAG` facade, which opens Cozo/RocksDB in `__post_init__`. Consequences: GET /corpus, /corpus/counts, /jobs, health, retry and delete all fail (502) during any write today, and two concurrent status calls collide too. D-08's "interrupted when no job holds the D-07 lock" is only evaluable when the lock is free. Recommendation: gate every driver op per working dir; a read that finds a write holding the gate raises `StoreBusyError(store_kind="corpus")` (409); reads wait for each other. The cleaner alternative (facade-free status that reads `kv_store_doc_status.json` directly) is an open question for the planner (Open Question 2).
4. **Duplicate drops: v1 returns `None` and the current driver reports `enqueued: 1` anyway.** [VERIFIED: spike6, pipeline.py:637-800] Existing-id and same-basename duplicates are detected before enqueue and recorded as `dup-<md5>` rows with `status: failed`, `metadata.is_duplicate: true`, `duplicate_kind` `"filename"` or `"content_hash"`, `track_id` = the track id the caller passed; `apipeline_enqueue_documents` then returns `None` (line 798-800) - the current driver already echoes `len(documents)`. Same content under a different basename on the **file** path is only detected after parse (`_mark_duplicate_after_parse`, pipeline.py:3048): the doc row itself becomes `failed` with `is_duplicate: true`, `duplicate_kind: "content_hash"` (spike2 case D). Rule: after the enqueue **and** after the process step, read `rag.aget_docs_by_track_id(our_track_id)`; `enqueued = requested - rows where metadata.is_duplicate`.
5. **`TokenTracker` plumbing works, with one caveat.** [VERIFIED: utils.py:4194-4248; llm/openai.py:249, 757-765, 904, 1028-1033; spike2 case B: `{'prompt_tokens': 34, 'completion_tokens': 14, 'total_tokens': 48, 'call_count': 5}`] `get_usage()` returns exactly `prompt_tokens`, `completion_tokens`, `total_tokens`, `call_count`. v1 core never passes `token_tracker` (grep of `v1/lightrag/*.py` finds none outside `llm/`), so the driver must pass it in both `openai_complete_if_cache(..., token_tracker=)` and `partial(openai_embed.func, ..., token_tracker=)`. Caveat: when a provider response has no `usage`, the LLM path still calls `add_usage` with zeros (`getattr(None, "prompt_tokens", 0)`), so `call_count > 0 and total_tokens == 0` must be read as **unbudgetable**, never as a real zero. Use two trackers (LLM, embedding): embedding tokens are a different tokenizer and must not be summed into the LLM figure.
6. **The sync part must be `kind="opaque"`.** [VERIFIED: validator/execution_mode.py:41-71, runner/scheduler.py:431-441, seam/engine.py:652-659] `mutates_store` is in `_NOT_IN_PROCESS_EFFECTS`; a non-opaque part declaring it derives `confined-unit`, which `host()` refuses (`UnimplementedPlacementError`). An opaque part derives `subprocess`, is hosted when its admission record carries a positive wall-clock ceiling, but its body still runs in the engine process with `ctx.stores`. `_mach11_events` emits events only for nodes whose Part declares `mutates_store`. So the sync part = `kind="opaque"`, effects `[mutates_store, writes_kv, writes_vector, writes_graph]`, a full 11-verdict admission record, and a self-enforced ceiling (`asyncio.wait_for`; nothing else kills an in-process body).
7. **Ingest/delete wirings need three safety rules for the sync.** (a) v1 working dir absent (or no `kv_store_doc_status.json`) -> **no-op**, never delete: existing tests (`test_hipporag_write_path.py:134`, `test_rest_corpus_endpoints.py`) run stub part bodies that never create the dir. (b) Present but unreadable/corrupt -> raise (fail closed; `_drop_pending` runs). (c) Backend refusal by name happens before any v1 op: the v1 backends in practice are JSON KV/doc-status + Faiss + Cozo [VERIFIED: file listing of `v1/.corpus_working_dir` and `README-PARITY.md` D-05]; the exact `LIGHTRAG_*_STORAGE` values live only in `v1/.env.parity` (not read). D-01 names KV, vector and graph only; the sync also reads `kv_store_doc_status.json`, so also refuse a non-`JsonDocStatusStorage` doc-status backend.
8. **Four protected test files must change and about eight more constrain the design** (full list in §Protected Tests). The ones that shape the design: `test_build_stores_cleanup.py` (STOR-02) pins that `engine.query/ingest/delete_document` on an empty root raise the raw `RuntimeError("graph open failed")` from `_build_stores` first, so the D-15 empty-namespace pre-check and any config pre-check must run **after** `_build_stores`; `test_refusal_status_codes.py` (SEAM-04) pins that every refusal in `refusals.__all__` except `ForeignEngineRefusalError`/`StoreBusyError` maps to 422 (or 404 for four lookups), so a "v1 not configured" 503 must ride `ForeignEngineRefusalError`; `test_tool_growth_invariant.py` (RUN-01) hardcodes `== 9` tools; `test_store_effects_wired.py` (STOR-12) pins `lightrag/full-ingest@0.1.0` and `writes_artifact`.
9. **LRAG-19 by removing the node changes promotion semantics.** [VERIFIED: seam/promotion.py:67-82, 232-250; tests/seam/test_promote.py:309-316; test_promotion_posture.py:61-72] `derive_mutation_class` returns `index-side` when the symmetric node difference contains `embedder-index`. `test_mutation_class_is_derived_not_supplied` expects naive->bypass to be `index-side`; `test_promote_now_refuses_at_index_side_naming_the_posture` expects naive's first promotion to be `index-side`. After the node is removed those become `retrieval-side` and `answer-level`. Neither test is a ledger test_ref (unprotected), but the behaviour change must be a conscious decision (Open Question 4).
10. **The LLM client already supports system messages.** [VERIFIED: clients/openai_compat.py:160-163, clients/base.py:56-61] `OpenAICompatibleClient.chat(messages, **kwargs)` forwards `messages` unchanged. The whole gap is `generate.py:30-35` (one user message from an f-string). D-16's "the LLM client gains system-message support" needs only a Protocol docstring and recording stubs that accept a system role.
11. **The operator corpus is 310 failed documents.** [VERIFIED: `v1/.corpus_working_dir/kv_store_doc_status.json`: Counter `{'failed': 310}`; ids such as `dup-22165f24...` with `file_path` `53d54090084941c6b243bf517339a821.bin`] This is LRAG-08/10 as lived defect (empty RAW upload then dup rows). It also means TOOL-02's migration has nothing worth migrating; do not spend plan effort on it.
12. **Secret exposure during this research.** `v1/.env.parity` is a symlink to `v1/parity-env.txt` (header of that file says so). That file is not dot-prefixed, so the secret-file hook does not guard it, and a `head -c 600` I ran printed a live provider API key into this session's transcript. The key is not reproduced here. Recommend rotating it and adding `parity-env.txt` to the hook's deny list.

## Direct Answers to the Planner's Ten Questions

| # | Question | Answer (details in the named section) |
|---|----------|----------------------------------------|
| 1 | D-01 backends, refactor boundaries, stale detection, PROCESSED-only | JSON KV + JSON doc-status + Faiss + Cozo (driver reads `LIGHTRAG_*_STORAGE` from env/`.env.parity`; values not readable here). Boundaries and set-difference in Pattern B. PROCESSED-only is exact (doc_status `chunks_list` -> chunk ids; entities/relations by `source_id`). |
| 2 | D-09 file ingest | `rag.apipeline_enqueue_documents(input=[""]*n, file_paths=[abs staged path], docs_format="pending_parse", track_id=..., ids=None)` with `INPUT_DIR`=inbox. Suffix list: 41 suffixes (below). Our document_id is NOT kept; map by `file_path` stem (Pattern C). |
| 3 | D-08 retry | Not by v1 public API; yes by driver-side `get_docs_by_statuses` filter (proven). No amendment needed. |
| 4 | D-10 duplicates | Pattern A, Finding 4. |
| 5 | D-13 usage | Finding 5. |
| 6 | D-16 fidelity | Pattern F table with file:line and prompt strings. |
| 7 | D-06 version | Pattern G. |
| 8 | Protected tests | §Protected Tests. |
| 9 | SC1 harness | §Hermetic Real-Driver Harness. |
| 10 | Validation Architecture | §Validation Architecture. |

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Upload staging, suffix validation, inbox cleanup | API / Backend (`seam/engine.py`, `seam/corpus.py`) | Browser/REST layer only forwards `file_name` | The engine owns paths (RUN-09); the suffix allowlist is a trust-boundary check |
| Parsing and extraction | v1 subprocess (opaque, inside boundary) | none | Unchanged; v1's legacy parser reads the bytes (D-09) |
| v1 doc-status truth, dedup, interrupted detection | v1 subprocess (driver ops) | Engine (lock state decides "interrupted") | Only v1 knows statuses; only the engine knows whether a job is in flight |
| Write serialization (D-07) | API / Backend (`engine`) | none | In-process lock per working dir; Phase 8 guarantees one engine process per store root |
| Mirror v1 index into v2 stores | API / Backend (new opaque part, runs in the engine process) | Database / Storage (kv/vector/graph proxies) | Reads v1 files (Faiss/JSON/Cozo) in the machine interpreter; writes only through `ctx.stores` |
| Atomic commit of mirror + drop on failure | Database / Storage via engine `_commit_all` (Phase 10 D-07) | none | Already exists; the sync only stages |
| Job -> family record | Database / Storage (small sqlite beside `trace.db`) | API (`get_job_status` dispatch) | D-02 |
| Health facts | API / Backend (`health()`), probes in `stores/probes.py` | v1 subprocess only for "configured" | D-14: no facade build, no writes |
| KG answer construction | API / Backend (query wiring parts) | Client tier (LLM client receives system+user messages) | D-16 |
| Token metering of write spend | v1 subprocess captures (TokenTracker) -> part reports `TokenAccounting` | `scheduler` meters the node | D-13 |

## Standard Stack

No new runtime packages. Everything below is already installed and exercised this session.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lightrag (v1, editable) | 1.5.4 [VERIFIED: `lightrag.__version__` printed `1.5.4` under `v1/.venv/bin/python`] | The opaque engine behind the driver | Pinned parity baseline; never imported from `databasise/` (import boundary) |
| pycozo[embedded] | 0.7.6 [CITED: CLAUDE.md Key Dependencies] | Read v1's `cozo_graph_chunk_entity_relation.db`; v2 `CozoGraphStore` | Already used by `import_index.py` |
| faiss-cpu | present in both venvs (import ran) | Read v1 `faiss_index_<kind>.index`; v2 `FaissVectorStore` | Already used |
| stdlib `http.server` + `threading` | Python 3.12.13 | Loopback OpenAI-compatible stub for the real-driver harness | Zero dependency; spike-verified |
| stdlib `sqlite3` | 3.12 | Job-family record (D-02), same pattern as `seam/trace_store.py` | House pattern |
| pytest | 9.1.1 [VERIFIED: `databasise/.venv/bin/pytest --version`], `asyncio_mode = "auto"` | Test runner | `pyproject.toml [tool.pytest.ini_options]` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `threading.Lock` (stdlib) | n/a | Per-working-dir write gate | Works across event loops (REST `TestClient` runs several loops; `asyncio.Lock` is per loop, see `_FLUSH_LOCKS` at engine.py:517-528) |
| `ast` (stdlib) | n/a | Drift tests: v1 prompt strings, v1 parser suffix set, driver protocol | Same technique as `test_full_ingest_compat.py:284-333` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| File-path ingest + id mapping (D-09) | Driver pre-extracts text with v1's own `lightrag.parser.legacy.extractors.extract_text(file_bytes, suffix)` [VERIFIED: extractors.py:170-185] and enqueues RAW with `ids=[document_id]` | Keeps our id as v1's id (no mapping), no `INPUT_DIR`/`__parsed__` handling, pre-enqueue dedup. Departs from D-09's letter ("no longer uses ids=") and bypasses v1 parser routing rules. Offered only if the mapping cost proves high (Open Question 1). |
| Gate per working dir + 409 for reads during writes | Facade-free `status` reading `kv_store_doc_status.json` directly | No subprocess, no RocksDB conflict, sub-millisecond; torn-read risk while v1 rewrites the JSON; deviates from "driver status op" (Open Question 2). |

**Installation:** none.

**Version verification:** `v1/.venv/bin/python -c "import lightrag; print(lightrag.__version__)"` -> `1.5.4`; `databasise/.venv/bin/python --version` -> `Python 3.12.13`.

## Package Legitimacy Audit

No external packages are installed or recommended in this phase (stdlib, already-installed v1 and databasise dependencies only). `gsd-tools query package-legitimacy check` was therefore not run.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | - | - | - | - | - | - |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
POST /documents (text)           POST /documents/upload (bytes + file_name)
        \                                  |
         \            validate id, suffix allowlist (422 before any write), size cap, non-empty
          \                                |
           +--------> Databasise.ingest ---+
                        | take write gate for <store_root>/<ws>/lightrag-v1   (busy -> 409 StoreBusyError(corpus))
                        | _build_stores (kv, vector, graph)   <-- raw store errors surface first (STOR-02)
                        | raw: stage <store_root>/<ws>/corpus-inbox/<document_id><suffix>   (exclusive create)
                        | stamp working_dir / input_dir / track_id / documents on node configs
                        v
       scheduler.run_wiring(corpus-ingest.json, recorder=...)      (HippoRAG: its own wiring, untouched)
          node 1: lightrag/full-ingest@0.2.0   --asyncio.to_thread--> run_corpus_op("ingest", ...)
                     |   v1 subprocess (cwd=v1, interpreter v1/.venv): INPUT_DIR=inbox, enqueue, process (filtered), usage
                     |   stdout: {track_id, enqueued, usage, doc_ids}      exit 3 = v1 not configured
          node 2: lightrag/v1-index-sync@0.1.0 (deps: full-ingest, in-process body, ctx.stores writes)
                     |   read v1 files (doc_status, text_chunks, 3 faiss, cozo) -> upsert PROCESSED rows, delete stale v2 ids
                     v
       _node_result_or_refuse  --failure--> _drop_pending(all stores) + FERE
                     | ok
       _commit_all (prepare-all, commit-all under flush lock)         <-- v1 already committed: documented window
                     | cleanup staged + __parsed__ copy (always on success/refusal, logged-and-kept on timeout)
                     v
       IngestJob(job_id, enqueued, seam_events[MACH-11 from sync node]) ; record job_id -> family in jobs db

GET /corpus, /corpus/counts, /jobs/{id}: gate held by a write -> 409 ; else driver "status" (facade) ;
   statuses PARSING/ANALYZING/PROCESSING -> reported "interrupted" (lock free) ; HippoRAG job id -> synthesized terminal
POST /documents/{id}/retry: gate -> refuse unless interrupted -> ingest wiring with retry_doc_ids -> sync -> commit
DELETE /documents/{id}: gate -> corpus-delete.json [full-delete -> v1-index-sync] -> commit on success|not_found ; remove inbox files for id
GET /health: probes (read-only) + engine-side working_dir.exists() + interpreter + cheap driver config probe + clients required
POST /query (LightRAG arms): _build_stores -> EmptyNamespaceError pre-check (no vector.faiss) -> run_wiring (KG-faithful parts)
```

### Recommended Project Structure
```
databasise/
├── foreign/v1_corpus_driver_script.py   # ops: ingest(+retry_doc_ids), delete, status, health; entities/entity_info removed
├── foreign/v1_corpus_adapter.py         # working_dir required, 2000-char tail, malformed-output + not-configured errors
├── parts_core/lightrag/full_ingest.py   # @0.2.0, usage -> TokenAccounting, record rewrite (storage, §8 numbering)
├── parts_core/lightrag/full_delete.py   # @0.2.0, calls_llm, no self-reported v2 touches
├── parts_core/lightrag/v1_index_sync.py # NEW opaque part body + admission record
├── parts_core/declared_only.py          # three corpus Parts (LIGHTRAG_CORPUS_PARTS gains the sync)
├── parity/import_index.py               # readers split from writers (Pattern B)
├── stores/{kv,graph,vector}.py          # additive read methods: all keys / edge keys / committed ids; lazy mkdir (D-15)
├── seam/engine.py                       # lock, inbox, mapping, jobs db, interrupted, retry, health, empty-namespace check
├── seam/{corpus,refusals,rest}.py       # IngestJob.seam_events, new refusals, retry route, status mapping
├── mcp/tools.py                         # retry tool (+ COVERAGE.md rows)
├── wirings/lightrag/{corpus-ingest,corpus-delete,base}.json + arm patches
└── parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md  # names + pins updated
```

### Pattern A: Working dir plumbing, adapter and driver protocol (the D-06 bump content)

**Working dir.** `Databasise._v1_working_dir() = self.store_root / self.workspace / "lightrag-v1"`; `inbox = self.store_root / self.workspace / "corpus-inbox"`. Stamp `working_dir` onto every `lightrag/*` node's config in the corpus wirings (the sync node needs it too), and pass `working_dir=` to every `run_corpus_op` call: `full_ingest.py:220-225`, `full_delete.py:219-224`, `engine._corpus_op_or_refuse` (engine.py:484-499), `engine.health` (engine.py:1278). Make `working_dir` a **required** keyword of `run_corpus_op` (adapter.py:101-131 currently falls back to `DEFAULT_V1_WORKING_DIR` = `v1/.corpus_working_dir`, line 31) so "never the repo-global" is structural. Keep the existing patch points: tests monkeypatch `databasise.seam.engine.run_corpus_op` and `full_ingest.run_corpus_op`/`full_delete.run_corpus_op` as module globals (test_foreign_engine_refusal.py:61,67,82), and fakes accept `**kwargs` so a `working_dir=` kwarg is invisible to them. LRAG-15 follows automatically: `eval/corpus_ingest.py:67-69` already uses `_EVAL_INGEST_STORE_ROOT = v1/.eval_corpus_store`, workspace `eval-corpus-ingest`, so the v1 dir becomes `v1/.eval_corpus_store/eval-corpus-ingest/lightrag-v1`.

**Adapter changes (v1_corpus_adapter.py).** Line 64: `stderr.strip()[:2000]` is the head slice -> keep `stderr[-2000:]` (store the tail on `self.stderr` too). Line 149: wrap `json.loads(proc.stdout)` and raise a named `CorpusOpMalformedOutputError(RuntimeError)`; add its name to `_FOREIGN_FAILURE_CLASSES` (refusals.py:736-742) mapping to `"MalformedDriverOutput"` and **keep** the `JSONDecodeError` entry (test_corpus_adapter_failures.py:29 injects a raw `json.JSONDecodeError`). Add exit-code-3 handling (Pattern D). Fix the stale module docstring (adapter.py:5-6 "ingest today, delete/status in 05-03/05-04") and the driver's (driver docstring and `UnknownOpError` text at lines 111-117 "plans 05-03/05-04 add the missing branches"), and `evidence/f07_report.py:46-48` ("the same file-unlink shape that adapter already owns for delete_project").

**Driver protocol after the bump** (pin these in `PINNED_DRIVER_PROTOCOL`; the compat test derives them by AST, so every `_run_<op>` must read job keys only as `job["k"]`/`job.get("k")` inside its own function and `return` a **literal-key dict** - a `**` unpack raises `_UnresolvableProtocolFieldError`, test_full_ingest_compat.py:260-281; dispatch must stay `if op == "x": return await _run_x(job)`, lines 298-324):

| op | stdin keys | stdout keys |
|----|-----------|-------------|
| `ingest` | `documents`, `track_id`, `working_dir`, `file_paths`, `docs_format`, `input_dir`, `retry_doc_ids` | `track_id`, `enqueued`, `usage`, `doc_ids` |
| `delete` | `doc_id`, `delete_llm_cache`, `working_dir` | `status`, `doc_id`, `message`, `status_code`, `file_path`, `usage` |
| `status` | `track_id`, `limit`, `offset`, `working_dir` | `counts`, `documents`, `total` |
| `health` | `working_dir` | `configured`, `missing_keys` (no facade, no mkdir) |
| `entities`, `entity_info` | removed (D-05) | removed |

`doc_ids` = `{our_document_id: v1_doc_id}` for the run (Pattern C). `usage` = `{"llm": {...get_usage()}, "embedding": {...get_usage()}}` or `None` only when `call_count == 0` on both and nothing ran. The driver's `status` op must refuse `limit < 1` or `offset < 0` itself (LRAG-05): today it slices `document_ids[offset:offset+limit]` (driver lines 299-301) and `limit=-1` returns `total-1` entries.

**Ingest branch skeleton** (names from driver lines 173-198 and spike3; the filter wrapper is spike-verified):

```python
# inside _run_ingest, after rag = await _build_rag(working_dir)
if retry_ids:                              # retry: process only these v1 ids
    targets = set(retry_ids); result_track = track_id
else:
    if docs_format == FULL_DOCS_FORMAT_PENDING_PARSE:
        os.environ["INPUT_DIR"] = str(job["input_dir"])        # v1 resolves the file under this dir
        result_track = await rag.apipeline_enqueue_documents(
            input=[""] * len(file_paths), file_paths=file_paths, track_id=track_id,
            docs_format=FULL_DOCS_FORMAT_PENDING_PARSE)           # NO ids= (forces RAW)
    else:                                                          # text: unchanged RAW + ids=
        result_track = await rag.apipeline_enqueue_documents(input=texts, ids=ids, track_id=track_id)
    rows = await rag.aget_docs_by_track_id(track_id)               # includes dup-* rows (they carry OUR track_id)
    targets = {k for k, d in rows.items() if not (d.metadata or {}).get("is_duplicate")}
orig = rag.doc_status.get_docs_by_statuses                         # instance-level wrapper, this process only
async def only_targets(statuses):
    return {k: v for k, v in (await orig(statuses)).items() if k in targets}
rag.doc_status.get_docs_by_statuses = only_targets
await rag.apipeline_process_enqueue_documents()
rows = await rag.aget_docs_by_track_id(track_id)                   # re-read: file path content-hash dups appear only now
dropped = sum(1 for d in rows.values() if (d.metadata or {}).get("is_duplicate"))
```
Return `track_id` = the caller's track id even when v1 returned `None` (every drop path returns `None`: pipeline.py:798-800), because the `dup-*` rows were stored under it (pipeline.py:770). `enqueued = requested - dropped`.

### Pattern B: The v1-index-sync part and the `import_index` refactor

**v1 on-disk layout (workspace empty, so no prefix)** [VERIFIED: `ls` of spike working dirs and `v1/.corpus_working_dir`]: `kv_store_doc_status.json`, `kv_store_text_chunks.json`, `kv_store_full_docs.json`, `kv_store_entity_chunks.json`, `kv_store_llm_response_cache.json`, `faiss_index_chunks.index`, `faiss_index_entities.index`, `faiss_index_relationships.index` (each + `.meta.json`), `cozo_graph_chunk_entity_relation.db`. The mirror needs only: doc_status, text_chunks, the three Faiss pairs and the Cozo db (same set `import_v1_index` reads; its constants `_VECTOR_KINDS`, `_GRAPH_KIND`, `_TEXT_CHUNKS_KIND` at import_index.py:80-82).

**Row shapes the filter relies on** [VERIFIED: spike2 artifacts]: doc_status record `status` (`"processed"`), `chunks_list`, `file_path`, `track_id`, `metadata.is_duplicate`; text_chunks key `<v1_doc_id>-chunk-NNN` with `full_doc_id`, `file_path`, `content`; chunks Faiss meta `{"__id__", "__created_at__", "full_doc_id", "file_path", "content"}`; entities meta `{"__id__": "ent-...", "source_id", "entity_name", "file_path", "content"}`; relationships meta `{"__id__": "rel-...", "src_id", "tgt_id", "source_id", "file_path", "content"}`; Cozo node attrs include `source_id`, `file_path`, `entity_type`, `description`; edge attrs include `source_id`, `weight`, `keywords`. `source_id` is `<SEP>`-joined chunk ids (`GRAPH_FIELD_SEP = "<SEP>"`, mirrored at chunk_sel_kg.py:46).

**PROCESSED-only rule (exact):** `processed_chunks = union(chunks_list of doc_status rows with status == "processed")`. Keep a text chunk/chunk vector iff its id is in `processed_chunks`; keep an entity/relationship vector, graph node or edge iff any chunk in its `source_id` is in `processed_chunks` (and for edges, both endpoint nodes are kept). `dup-*` rows have `chunks_list == []` and drop out naturally; an interrupted doc's chunks are excluded (v1 persists chunks at PROCESSING start: pipeline.py ~2484 "Stage 1: persist doc_status PROCESSING + chunks in parallel").

**Function boundaries** (keep `import_v1_index(v1_working_dir, store_root, workspace) -> str` and its CLI/test callers unchanged):

```python
# parity/import_index.py
@dataclass(frozen=True)
class V1Snapshot:                      # pure data; no v2 store touched
    text_chunks: dict[str, dict]
    vectors: dict[str, tuple[list[str], np.ndarray, list[dict]]]   # kind -> (ids, matrix, metadata)
    nodes: dict[str, dict]
    edges: dict[tuple[str, str], dict]

def read_v1_snapshot(v1_working_dir: Path, *, processed_only: bool = True) -> V1Snapshot | None:
    """None when kv_store_doc_status.json is absent (sync no-op). Raises on unreadable/corrupt. Blocking: call via to_thread."""
async def mirror_snapshot(snapshot, *, kv, vector, graph, prune: bool) -> MirrorReport:
    """Works through handles (raw stores or ctx.stores proxies): kv.upsert/delete, vector.select(k).upsert/delete_by_ids,
    graph.upsert_node/upsert_edge/delete_node/delete_edge. prune=True computes v2 - v1 per namespace and deletes."""
async def import_v1_index(...):       # as today: build raw stores, mirror_snapshot(prune=False, processed_only=False), then flush each
```
Existing readers to reuse: `_import_vector_kind` (import_index.py:164-198: `faiss.read_index` + `reconstruct`, strips `__id__`, `__vector__`, `__created_at__`, `id`, `score` from metadata), `_import_text_chunks` (:201-213), `_import_graph` (:216-239 via a plain `CozoClient("rocksdb", path)`; the warning "`pandas` feature was requested" is harmless noise).

**Stale detection needs additive read methods** [VERIFIED: stores/kv.py method list, graph.py:370 `get_all_labels`, vector.py:477 `iter_vectors`]: the kv store has no key listing (`get_by_id`, `get_by_ids`, `filter_keys`, `is_empty` only) and the graph has `get_all_labels()` for nodes but no edge listing. Add `SqliteKVStore.all_keys()`, `CozoGraphStore.all_edge_keys()` (`?[src, tgt] := *edges{src, tgt}` plus pending), and `FaissVectorStore.committed_ids()` (do not call `iter_vectors()`: it reconstructs every vector). The sync holds write proxies (mode `"w"` exposes everything but the `_ENGINE_ONLY` lifecycle names, parts_core/__init__.py:91 and :143-145), so no read-allowlist edit is needed. Then per namespace `stale = v2_ids - v1_keep_ids -> delete`. Order inside the node: upsert, then delete stale, so a failure drops cleanly.

**Part declaration (Pattern G has the full record):** `kind="opaque"`, `structural_depth="opaque"`, `effects=["mutates_store","writes_kv","writes_vector","writes_graph"]`, `artifact_scope=None`, body returns `{"synced": bool, "counts": {...}, "tokens": TokenAccounting(counted_by="none")}` (a real zero: nothing is embedded). `corpus-ingest.json`: node `v1-index-sync` with `deps: ["full-ingest"]`, keep `provides: ["full-ingest"]` and `consumes_documents: ["full-ingest"]` so `engine.ingest` (`resolved["provides"][0]`, engine.py:923-924) and cross-check condition 7 are unchanged. Same shape in `corpus-delete.json` with `provides: ["full-delete"]`.

**Bound the work:** `asyncio.wait_for(...)` with the admission ceiling inside the body (nothing else can kill an in-process body); read in `asyncio.to_thread`. `# shortcut: full O(corpus) mirror per write, upgrade by diffing doc_status snapshots`.

### Pattern C: Write lifecycle in the engine (lock, inbox, mapping, jobs, interrupted, retry)

- **Lock (D-07).** Module-level `dict[str, threading.Lock]` keyed by the resolved working-dir path; `acquire(blocking=False)` else `raise StoreBusyError(store_kind="corpus")` (409 via rest.py:139-144, already exempt from the SEAM-04 status test, test_refusal_status_codes.py:27). Hold across `_build_stores`... `_commit_all` and release in `finally`. A threading lock survives the REST `TestClient`'s multiple loops; the LRAG-04 test is `asyncio.gather` of two ingests against a sleeping stub.
- **Reads vs the gate (Finding 3).** Track holder kind. A read (`status`/`health` driver op, retry pre-check) that finds a **write** holding the gate raises `StoreBusyError(store_kind="corpus")` before spawning anything; reads serialize with each other. `health()` must keep returning 200 `degraded`, not raise: report "write in progress" through the health reason field.
- **Inbox (D-09).** Stage as `<inbox>/<document_id><suffix>` with `open(path, "xb")` (keeps the exclusive-create duplicate guard, engine.py:979). Validate `suffix` from `file_name` after reducing to a basename: lower-case `Path(name).suffix`, must be in the allowlist, regex `\.[a-z0-9]{1,8}`; a `text` ingest has no file. Refuse before any write with `UnsupportedUploadTypeError(suffix=...)`. **Clean both** `<inbox>/<name>` and `<inbox>/__parsed__/<name>` (Finding 1) after a successful or refused run; on `CorpusOpTimeoutError`/driver fault keep and log (engine.py:284-287 `_log_staged_left`). `DELETE` removes `<id>.*` in both directories using an exact `name.startswith(f"{id}.")` match on a validated bare-token id. Delete `_staged_owner_path`/`_release_staged_upload` and the `corpus-inbox-owners` writes (engine.py:944-1005, 1055-1084) and `tests/seam/test_raw_upload_staging.py`'s owner-record cases.
- **Accepted suffixes** [VERIFIED: `available_engine_suffixes()` printed under the v1 interpreter; parser/registry.py:96-139, 177-189, 277]: `bat c conf cpp css csv docx epub go h hpp htm html ini java js json less log md mdx odt pdf php pptx properties py rb rtf scss sh sql swift tex textpack ts txt xlsx xml yaml yml` (41). `textpack` needs the native bundle format and is the only suffix whose default engine is `native` (`_DEFAULT_ENGINE_BY_SUFFIX = {"textpack": native}`, routing.py:63); recommend the 40 legacy suffixes minus nothing and exclude `textpack`. Source of truth for a drift test: the `_LEGACY_SUFFIXES = frozenset({...})` literal in `v1/lightrag/parser/registry.py` (parse with `ast`). Unsupported suffix proof: `.xyz` enqueues, then fails at parse with `engine 'legacy' does not support .xyz` (spike2 case F), so the engine must pre-validate.
- **Doc id mapping (Finding 1).** Because the staged basename is `<document_id><suffix>`, `Path(file_path).stem == document_id` for every file-ingested v1 row, and text-ingested rows have `file_path == "unknown_source"` with v1 id == our id. Recommended: the **driver** resolves (delete/retry accept our `document_id`; scan `get_docs_by_statuses(list(DocStatus))` for the row whose `Path(file_path).stem` equals it, else `get_by_id`) and `status` reports `document_id` as that stem when `file_path != "unknown_source"` and the v1 id starts with `doc-`; `dup-*` rows keep their v1 id. No new persistent state; survives restarts. The ingest result's `doc_ids` map lets the engine log it. Evidence refs still carry the v1 chunk id (`<v1_doc_id>-chunk-000`) and the resolved record carries `full_doc_id` (spike4), so LRAG-02's test resolves document membership from `full_doc_id`.
- **Job-family record (D-02).** `jobs.db` beside `trace.db`, created in `Databasise.__init__` next to `TraceStore` (trace_store.py:56-75 pattern: WAL, `check_same_thread=False`): table `job_families(job_id TEXT PRIMARY KEY, family TEXT NOT NULL, document_id TEXT, created_at TEXT NOT NULL)`. Written after a committed ingest for both families. `get_job_status`: row with `family == "hipporag"` -> synthesize `JobStatus` with one `DocumentStatusEntry(status="processed")`; otherwise the current driver path; `total == 0` stays `UnknownJobError`. Do not create it inside `health()`.
- **Interrupted (D-08).** In `corpus_status`, `get_job_status` and `document_counts`, when the gate is free remap statuses `parsing|analyzing|processing` -> `"interrupted"` (counts too; keep `total` equal to the sum). Do the remap after the `_MALFORMED_RESULT` parse wrapper so a malformed entry still yields `MalformedDriverOutput` (test_corpus_adapter_failures.py:91-101).
- **Retry (D-08).** `Databasise.retry_document(document_id, selector=None) -> IngestJob`: take the write gate, driver `status` pre-check (refuse unless the doc is interrupted: new `DocumentNotInterruptedError(document_id, status)` 422; unknown -> existing `UnknownDocumentError`), then run the **same** `corpus-ingest` wiring with `documents=[]` and `retry_doc_ids=[...]` so it reuses the full-ingest port (identical declared effects, so no separate port under §19.6) and the sync. Route `POST /documents/{document_id}/retry` (declare `_FAULT_RESPONSES` like the others, rest.py:403-474) and an MCP tool `retry`. Adding the tool breaks `test_tool_growth_invariant.py`'s `== 9`.
- **Metering at the node.** `full_ingest_body` builds `TokenAccounting(prompt_tokens, completion_tokens, call_count, counted_by=...)` from `usage["llm"]`: `call_count == 0` -> `counted_by="none"` (real zero); `call_count > 0 and total == 0` -> `"unbudgetable"`; else a stable label such as `"v1-subprocess"` (the tracker has no tokenizer identity). Report `usage["embedding"]` in the result dict only. Replace the dead branch at full_ingest.py:227-239.

### Pattern D: New refusals and statuses

| Refusal | Where raised | Status | Public fields |
|---------|--------------|--------|---------------|
| `StoreBusyError(store_kind="corpus")` (exists, refusals.py:777) | write gate; reads during a write | 409 | `store_kind` |
| `UnsupportedUploadTypeError` (new) | engine, before staging | 422 | `suffix` (normalized; may be `""`) |
| `EmptyNamespaceError` (new) | engine, after `_build_stores`, before `run_wiring` | 422 | `store_kind` only (D-15) |
| `DocumentNotInterruptedError` (new) | retry pre-check | 422 | `document_id`, `status` |
| v1 not configured | driver exit code 3 -> adapter `V1NotConfiguredError` -> `ForeignEngineRefusalError(failure_class="V1NotConfigured")` | 503 (extend `_ENGINE_UNAVAILABLE`, rest.py:136) | `missing_keys` as a conditional attribute set only for this class, so every other fault body keeps its exact key set (`test_foreign_engine_refusal.py:46-56` asserts `operation` and `failure_class` and a <1 KB body) |

Each new `SeamRefusalError` subclass goes into `refusals.__all__` and needs a factory in `tests/seam/test_rest_transport.py::_REFUSAL_FACTORIES` (refusals.py:14-18); the parametrized SEAM-04 test then demands 422. A dedicated 503 refusal class would fail that test, which is why "not configured" rides `ForeignEngineRefusalError`.

**Driver-side detection (why).** The driver subprocess runs with `cwd=v1` and its imports execute `load_dotenv(dotenv_path=".env", override=False)` (v1/lightrag/utils.py:313), so only the subprocess sees the effective environment. A pre-check in the engine would have to parse `v1/.env*` and would break `test_build_stores_cleanup.py` and `test_foreign_engine_refusal.py`, which run the real engine with no v1 environment. The driver validates `EMBEDDING_DIM`, `EMBEDDING_MODEL`, `EMBEDDING_BINDING_HOST`, `EMBEDDING_BINDING_API_KEY`, `LIGHTRAG_KV_STORAGE`, `LIGHTRAG_GRAPH_STORAGE`, `LIGHTRAG_VECTOR_STORAGE`, `LIGHTRAG_DOC_STATUS_STORAGE` (read at driver lines 150-168) and, for ops that can call the model, `LLM_MODEL`, `LLM_BINDING_API_KEY`, `LLM_BINDING_HOST` (driver lines 133-139), prints `{"error": "v1_not_configured", "missing_keys": [...]}` and exits 3. Never include values.

### Pattern E: Health

Current: `health()` at engine.py:1258-1293 probes `_HEALTH_PROBES` (engine.py:305-316, already includes the HippoRAG namespaces and a real Faiss probe via `probe_vector`), then calls driver `health`, which builds the facade and creates the working dir (driver lines 319-329). Phase 10 (STOR-04) already satisfies: no store creation, HippoRAG namespaces, real vector probe, empty root -> `degraded`. Remaining for LRAG-13/14:
1. `working_dir_present = (working_dir).exists()` engine-side (no subprocess), `interpreter_present` as today, one `v1_reachable` fact from the cheap driver `health` op (imports, key check, **no** `LightRAG(...)`); a failed or timed-out driver call sets `v1_reachable=False` but leaves `working_dir_present` truthful. Drop `storages_initialized`.
2. Status `ok` requires every store `ok`, all engine facts true, and `clients["llm"]` and `clients["embedding"]` both wired; rerank stays optional. Amend the HealthReport docstring sentence "it never affects ``status``" (corpus.py:285-291).
3. Reason field: `HealthReport` is `extra="forbid"` with `engine: dict[str, bool]`, so a string reason needs a new optional field with a default (e.g. `reasons: list[str] = []` holding allow-listed codes, `v1_not_configured:<KEY,KEY>` only names). Open Question 5.
4. Wrap each probe call so an unexpected exception reports `corrupted`/degraded instead of a 500 (the finalize-failure case: the Phase 10 health no longer constructs stores, so test it by making a probe raise).
5. Edits to unprotected `test_corpus_status.py:166,190-192,240-241` (engine key set, "clients never change status", `storages_initialized`); `test_health_probe.py` (protected) needs none if `_HEALTH_PROBES` is untouched.

### Pattern F: D-16 gap table (v1 `kg_query` vs the v2 parts)

v1 flow [VERIFIED: operate.py:3792-4004 kg_query; 4321-4528 `_perform_kg_search`; 4531-4699 `_apply_token_truncation`; 4737-4842 `_merge_all_chunks`; 4845-5026 `_build_context_str`; 5030-5147 `_build_query_context`; 5150-5717 lookups/selection; utils.py:4335-4440 `process_chunks_unified`, 4929-4992 `generate_reference_list_from_chunks`, 2596-2610 `truncate_list_by_token_size`; constants.py:52-59]. Defaults: `DEFAULT_TOP_K = 40`, `DEFAULT_CHUNK_TOP_K = 20`, `DEFAULT_MAX_ENTITY_TOKENS = 6000`, `DEFAULT_MAX_RELATION_TOKENS = 8000`, `DEFAULT_MAX_TOTAL_TOKENS = 30000`, `DEFAULT_RELATED_CHUNK_NUMBER = 5`, `DEFAULT_KG_CHUNK_PICK_METHOD = "VECTOR"`.

| # | v1 step | v2 today | Gap and change |
|---|---------|----------|----------------|
| 1 | Keywords hl/ll; if both empty and `len(query) < 50`, `ll = [query]`, else return `fail_response` (operate.py:3850-3860) | keywords.py:105-137 returns lists only | Add the fallback in the body (after line 130); emit `ll_keywords_str = ", ".join(ll)` and `hl_keywords_str` |
| 2 | One batched embed of `[query (if chunks_vdb), ll_str (local/hybrid/mix), hl_str (global/hybrid/mix)]` (operate.py:4350-4403) | embedder_query.py:33-42 embeds only the query text; entity_lookup.py:34, relation_lookup.py:33 and chunk_vector.py:27 all read `["vector"]` | embedder-query embeds the non-empty strings in one `client.embed([...])` and emits `vector`, `ll_vector`, `hl_vector`; entity-lookup reads `ll_vector`, relation-lookup `hl_vector`, chunk-vector stays on `vector`. Naive arm keeps `deps: []` (arm-naive patch) and has no keywords output |
| 3 | `chunk_top_k or top_k` = 20 for chunk vector search (operate.py:4287) | chunk_vector.py:17 `_DEFAULT_TOP_K = 10` | v1 default is 20. Changing it moves parity numbers; check `tests/parity` pins before touching (Assumption A10) |
| 4 | Entity lookup `top_k=40`, batch get nodes + node_degrees, `rank = degree` (5150-5207) | entity_hydrate_expand.py:61-70 per-entity `get_node` + `node_degree` | Equivalent; memoize `node_degree` in a dict (called again at line 83 for every edge endpoint: LRAG-18 "at most once per node") |
| 5 | One-hop relations: dedup by sorted pair, `edge rank = degree(src)+degree(tgt)`, **sort by `(rank, weight)` descending** (5259-5261) | entity_hydrate_expand.py:72-91 builds the list unsorted | Sort `relations` by `(rank, weight)` desc before returning (after line 91) |
| 6 | Global: relation vector order preserved, endpoint nodes by first appearance (5425-5514) | relation_hydrate_expand.py:43-92 | Equivalent; no change |
| 7 | Round-robin merge, local first, dedup by entity name / sorted relation pair (4462-4516) | join_roundrobin.py:118-160 | Equivalent for entities and relations |
| 8 | Truncate entities and relations with `json.dumps` of `{entity,type,description}` / `{entity1,entity2,description}` only (`file_path`, `created_at` removed) at 6000 / 8000 tokens (4570-4657) | truncator_token_budget.py:53-76 costs the whole item JSON (source_id, derived_from, rank...) at `len//4` | Project items to the v1 fields before costing, and emit the projected `entities_context`/`relations_context` for assemble. Keep `len//4` (D-16 `shortcut:`: no offline tokenizer) |
| 9 | Chunks: entity chunks and relation chunks selected **separately** (relation chunks exclude entity chunk ids), each `pick_by_vector_similarity` (default VECTOR) falling back to weighted polling; `num_of_chunks = int(related_chunk_number * len(items)/2)` (5266-5717) | chunk_sel_kg.py:153-195 concatenates entities+relations into one pass; `config["query_vector"]` is never set by the base wiring (chunk_sel_kg.py:167) so VECTOR silently degrades to WEIGHT | Select entity and relation chunks separately with dedup; add `embedder-query` to chunk-sel-kg `deps` in base.json and read `ctx.inputs["embedder-query"]["vector"]`; rank candidates with `score_all(vector)` (in the read allowlist: `"vector": frozenset({"select", "query", "score_all", "self_knn", "iter_vectors", "get_by_id"})`, parts_core/__init__.py:75) filtered to candidates instead of `query(top_k=...)` |
| 10 | Merge: round-robin `[vector, entity, relation]` with `chunk_id` dedup (4783-4830) | join_roundrobin.py:110-115 `_item_key` returns `None` for chunks (no dedup); base.json `join-chunks` precedence names chunk-sel-kg first | Key chunks by `chunk_id`/`id`; set `arm_precedence` so chunk-vector is first (the string drives order via `_ordered_input_names`, join_roundrobin.py:85-94) |
| 11 | `process_chunks_unified`: optional rerank, `chunk_top_k` cap (20), token truncation to the dynamic limit, ids `DC{i}` (utils.py:4335-4440) | heading_backfill -> rerank -> assemble: no `chunk_top_k` cap | Cap at `chunk_top_k` in assemble (or a config on heading-backfill); rerank unchanged except the query fix below |
| 12 | `_build_context_str`: `available = max_total_tokens - (sys_prompt_tokens + kg_context_tokens + query_tokens + 200)`, then chunk JSON lines `{"reference_id","content"[,"content_headings"]}` and reference list `[n] file_path` ordered by frequency then first appearance (4895-4964; utils.py:4929-4992) | assemble.py:29-47 reads only `ctx.inputs["rerank"]["items"]`, joins with blank lines, applies a char budget only if `max_total_tokens` is configured | assemble gains deps `budget-entities`, `budget-relations` in base.json (kg arms) and builds `kg_query_context`; reference ids via the same frequency rule; budget formula with the `len//4` approximation; the engine always sets `max_total_tokens` (new `_inject_max_total_tokens`, `setdefault` 30000, beside `_inject_token_allowance`, engine.py:386-393) |
| 13 | System prompt = `PROMPTS["rag_response"].format(response_type="Multiple Paragraphs", user_prompt="n/a", context_data=ctx)`, user message = query, `history_messages` (operate.py:3888-3952) | generate.py:29-35 one user message `Context:\n...\n\nQuestion: ...` | `client.chat([{"role":"system","content":sys},{"role":"user","content":query}])`. Template chosen by config `prompt_template`: kg arms `rag_response` (`{context_data}`), naive `naive_rag_response` (`{content_data}`, arm-naive sets `"prompt_template": "naive"`), bypass sends the bare query (arm-bypass `"none - direct LLM call"`). No client change: openai_compat.py:160-163 passes `messages` through |
| 14 | No context built -> `kg_query` returns `None` -> `fail_response`, **no LLM call** (3878-3880, 3860) | generate.py:29-32 sends the bare query | Optional fidelity item: short-circuit with `PROMPTS["fail_response"]` text |
| 15 | `order_policy` n/a in v1; `priority_class` only sets scheduler priority | assemble.py:32 echoes `order_policy`; generate ignores `priority_class` (base.json) | Read both: `kg-template` orders entities, relations, chunks, reference list; `naive-template` chunks and references only; unknown value refuses by name. Read `priority_class` and echo it (avoids editing wirings and their pinned hashes); "removed" is the alternative |
| 16 | Rerank applies only when a rerank function is configured; query passed | rerank.py:35 reads `config["query"]`, but base.json `consumes_query` is `["keywords","embedder-query","generate"]` | Add `"rerank"` (and `"assemble"`, which needs the query for token accounting) to `consumes_query`. D-16 limits rerank to this fix (no score update, no toggle) |

**Prompt strings to duplicate** (source file `v1/lightrag/prompt.py`): `fail_response` lines 330-332; `rag_response` 334-386; `naive_rag_response` 388-440; `kg_query_context` 442-467; `naive_query_context` 469-482; `keywords_extraction` 484-515 (already duplicated at keywords.py:41-72). Drift test: `ast.parse` prompt.py, collect every module-level `PROMPTS["name"] = <str constant>` assignment, compare the exact string with the constant in the v2 module. `rag_response` formats `{response_type}`, `{user_prompt}`, `{context_data}`; `naive_rag_response` uses `{content_data}`; `kg_query_context` uses `{entities_str}`, `{relations_str}`, `{text_chunks_str}`, `{reference_list_str}`.

**D-15 step (LRAG-16).** `FaissVectorStore.__init__` does `self._dir.mkdir(parents=True, exist_ok=True)` (vector.py:274), so `MultiNamespaceVectorStore.select` (vector.py:695-702) creates directories on read. Fix once: construct without `mkdir` and create the directory in `prepare()` before `_write_staged` (alternative: a `create=False` argument that the read-mode `_StoreProxy.select` wrapper injects). Pre-check in `_execute_resolved` **after** `_build_stores` (Finding 8): map the resolved wiring's retrieval nodes to namespaces with a component-keyed table (`lightrag/retriever-chunk-topk@0.1.0 -> chunks`, `lightrag/entity-lookup@0.1.0 -> entities`, `lightrag/relation-lookup@0.1.0 -> relationships`) and raise `EmptyNamespaceError` if any `<root>/<ws>/<ns>/vector.faiss` is missing; add a drift test like `test_health_probe.py:181-189`. An emptied-but-existing index returns the plain no-match path.

**Wiring edits that ripple:** `assemble` gaining `deps` breaks the naive arm unless `arm-naive.json-patch.json` adds `{"op": "replace", "path": "/nodes/assemble/deps", "value": ["rerank"]}` (dangling dependency otherwise, `CODE_DANGLING_DEP`); the `resulting_node_id_set` lists and `tests/parity/test_arm_conformance.py` must follow; `wirings/lightrag/README.md` documents "exactly three edits" to the published set and needs a fourth/fifth.

**LRAG-19 mechanics.** `base.json` `recipe.embedding == "embedder-index"` is pinned by `test_embedder_index_reproduction.py:108-112`; leave base.json's node and recipe alone and add `{"op": "remove", "path": "/nodes/embedder-index"}` plus `{"op": "replace", "path": "/recipe", "value": {}}` to the naive, hybrid, local and global patches (bypass already does both), then update each `resulting_node_id_set`. See Pitfall 8 for the promotion ripple.

### Pattern G: The opaque-boundary version (D-06) and re-admission

OPAQUE-BOUNDARY-RULE.md §2 [VERIFIED: file read]: changing any of `name_at_version`, `kind`, `structural_depth`, `effects[]`, `upstream_ref`, `artifact_scope`, any `AdmissionRecord` field (`storage`, `wall_clock_ceiling_*`, `feed_tier`, `ttl_days`, `network_namespace`, `manifest_source`, every `(condition, verdict)` pair), or the driver's stdin/stdout key sets or op set requires a new `name@version` and a fresh 11-verdict record. `test_full_ingest_compat.py` pins all of it (`PINNED_INGEST_BOUNDARY` :115-152, `PINNED_DELETE_BOUNDARY` :154-192, `PINNED_DRIVER_PROTOCOL` :197-222) and `test_rule_document_and_check_agree` (:367-382) requires every pinned name and key to appear in the rule document.

What changes (all in ONE bump to `@0.2.0` for `lightrag/full-ingest` and `lightrag/full-delete`; the sync is new, so it starts at `@0.1.0` - Open Question 8):

| Part | name | effects | artifact_scope | admission `storage` |
|------|------|---------|----------------|---------------------|
| full-ingest | `lightrag/full-ingest@0.2.0` | `calls_llm`, `mutates_store`, `reads_kv`, `reads_graph` (drop `writes_artifact`; LRAG-03) | `None` | self-contained: v1's working dir `<store_root>/<workspace>/lightrag-v1/` (was `"machine"`) |
| full-delete | `lightrag/full-delete@0.2.0` | `calls_llm`, `mutates_store`, `reads_kv`, `reads_graph` (add `calls_llm`; LRAG-11) | `None` | self-contained (same dir) |
| v1-index-sync | `lightrag/v1-index-sync@0.1.0` | `mutates_store`, `writes_kv`, `writes_vector`, `writes_graph` | `None` | machine (the v2 kv/vector/graph stores) |

Wirings: `corpus-ingest.json` full-ingest `effects` -> `["calls_llm","mutates_store","reads_kv","reads_graph"]`; `corpus-delete.json` gains `calls_llm`; each gets the second node. `parse_wiring` flags a node effect not declared by its Part (`CODE_EFFECTS_EXCEED_PART`), so wiring effects are a subset of the Part's.

**§8 numbering fix (LRAG-12), exact CONTRACT text** [VERIFIED: docs/system-model/CONTRACT.md:368-388]: condition 3 = network namespace denied, machine acts as the injected provider, an engine that cannot accept the injected endpoint is admitted `unbudgetable`; condition 8 = TTL approximately 90 days, renewable only with a recorded reason, each renewal recorded in the ledger; condition 9 = explicit `part_ref` invocations of a selector-excluded node counted as data and not a promotion trigger. Today the LightRAG records put "no network-namespace isolation" under 8 (full_ingest.py:156-166) and "spend unbudgetable" under 9 (full_ingest.py:167-179; full_delete.py:168-179). Target: 3 carries network isolation by construction **and** the spend statement (metered by TokenTracker when v1 reports usage, unbudgetable otherwise); 8 carries `ttl_days=90` with ledger renewal; 9 carries part_ref counting. Mirror the wording style of `codebase_memory_mcp.py:225-268` (verdicts `"machine-side-obligation"` for 8 and 9). Also rewrite the condition 5 and 10 evidence in the ingest record that cites `artifact_scope='quarantined'` (full_ingest.py:130-138, 184-189). Update the module docstring (full_ingest.py:9-17).

Re-admission mechanics: `PartRegistry.register` calls `validate_admission` (registry.py:123-149): exactly conditions 1-11, no blank evidence, `manifest_source == "code-inspected"`, ceiling > 0, no `shared` scope. `environment_hash` is not pinned. Name occurrences to sweep: `declared_only.py`, both wirings, `OPAQUE-BOUNDARY-RULE.md`, `test_full_ingest_compat.py`, `test_store_effects_wired.py:193`, tests that build test-local part variants from `LIGHTRAG_FULL_*_PART` (they follow the constant automatically), `evidence/*.md` that cite the old names (historical; leave or add a note).

### Anti-Patterns to Avoid
- **Pre-checking v1 config in the engine.** Reads `.env` files from the wrong process and breaks STOR-02 / SEAM-05 tests (Pattern D).
- **Putting the D-15 or config check before `_build_stores`.** Changes the first error `engine.query/ingest/delete_document` raise on an empty root (test_build_stores_cleanup.py:40-60).
- **A sync that treats "v1 dir missing" as "v1 empty".** Would delete every v2 row (Finding 7).
- **Calling `apipeline_process_enqueue_documents()` unfiltered.** It reprocesses FAILED docs on every call (Finding 2) and bills for them.
- **Summing embedding tokens into the LLM `TokenAccounting`.** Different tokenizers (seam/tokens.py groups by `counted_by` for exactly this reason).
- **A new refusal class for 503.** Fails the SEAM-04 parametrized status test.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Restricting v1 processing to chosen ids | A reimplementation of the pipeline or status surgery in `doc_status` | The driver-side `get_docs_by_statuses` wrapper (Pattern A) | Spike-proven; v1 state machine untouched |
| Duplicate detection | md5/basename comparison in the engine | v1's own `metadata.is_duplicate` / `duplicate_kind` rows via `aget_docs_by_track_id` | v1 already decides all three kinds |
| Token usage | Estimating from text length | `lightrag.utils.TokenTracker.get_usage()` via `token_tracker=` | Real provider counts; zero-usage is detectable |
| Reading v1 indexes | New Faiss/Cozo readers | `import_index._import_vector_kind` / `_import_text_chunks` / `_import_graph` bodies (refactored) | Already verified by `verify_import` |
| Atomic multi-store commit | A second commit protocol | `engine._commit_all` / `_drop_pending` | Phase 10 D-06/D-07 |
| Parsing uploaded bytes | A parser in `databasise/` | v1's legacy parser (D-09) | Opaque-boundary rule §4: no new capability inside the engine |
| Suffix allowlist | A hand-typed list | A constant in `databasise` guarded by an AST drift test against `registry.py` `_LEGACY_SUFFIXES` | Keeps one source of truth |
| Prompt text | Paraphrase | Verbatim copy + AST drift test | D-16 |
| Job record | A new storage layer | sqlite file in the `trace_store.py` pattern | House pattern |
| Cross-loop lock | `asyncio.Lock` | `threading.Lock` with `acquire(blocking=False)` | REST TestClient uses several loops |

**Key insight:** every hard part of this phase already exists inside v1 or Phase 10; the work is boundary plumbing, ordering rules and honest status.

## Runtime State Inventory

Not a rename phase, but the working dir and inbox move, so the question "what still holds the old location" was answered explicitly.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `v1/.corpus_working_dir/` (operator corpus: 310 doc_status rows, all `failed`; [VERIFIED] file listing and Counter). `store_root/corpus-inbox/*.bin` and `store_root/corpus-inbox-owners/` on any dev store from Phase 9. `v1/.eval_corpus_store/eval-corpus-ingest/` (eval store; gains a `lightrag-v1/` child) | None for the operator corpus (deferred to TOOL-02; nothing usable in it). Stale flat inbox files are harmless leftovers - note in the plan, no code migrates them. Eval store: code edit only |
| Live service config | None - verified: no external service stores working-dir paths | None |
| OS-registered state | None - the launcher takes a store lock (`store_lock.py`), no scheduler tasks | None |
| Secrets/env vars | Driver reads `EMBEDDING_*`, `LIGHTRAG_*_STORAGE`, `LLM_*` by exact name; `v1/.env.parity` is a symlink to `v1/parity-env.txt` | Code edit only (key list in Pattern D). Names may appear in the v1-not-configured refusal; values never. Rotate the provider key exposed in this session (Finding 12) |
| Build artifacts | `v1/lightrag_hku.egg-info`, `databasise.egg-info` (editable installs) | None; no package rename |

## Protected Tests (item 8)

The guard hook blocks Bash commands that merely **name** a ledger `test_ref` file (observed: `grep`, `sed` on `test_rest_corpus_endpoints.py`, `test_build_stores_cleanup.py`, `test_corpus_adapter_failures.py` all refused); read them with the Read tool. `ledger/REQUIREMENTS.json` rows LRAG-01..20 have empty `test_ref`; the planner records them at plan time (Phase 10 did this in a `chore` commit). Ledger `test_ref` files, read via the Read tool this session:

- RUN: `tests/mcp/test_tool_growth_invariant.py` (RUN-01), `tests/clients/test_openai_compat.py` (RUN-02, RUN-03), `tests/foreign/test_mcp_sdk_guard.py` (RUN-04), `tests/clients/test_build_clients.py` (RUN-05), `tests/launcher/test_launchers.py` (RUN-06, RUN-07), `tests/seam/test_rest_cors.py` (RUN-08), `tests/seam/test_rest_corpus_endpoints.py` (RUN-09, RUN-10), `tests/test_check_offline_suite.py` (RUN-12).
- SEAM: `test_evidence_namespace_guard`, `test_refusal_body_shape`, `tests/mcp/test_mcp_refusal_mapping`, `test_refusal_status_codes`, `test_foreign_engine_refusal`, `test_corpus_adapter_failures`, `test_ingest_input_refusals`, `test_page_bounds`, `test_empty_inputs`, `test_empty_capability_selector`, `test_compare_keys`, `test_promote_alias_validation`, `test_upload_selector_field`, `test_refusal_catalogue`, `test_ingest_file_name`, `test_seam_doc_consistency` (all `tests/seam/`).
- STOR: `tests/stores/{test_graph_lock,test_delete_commit_contract,test_vector_crash_window,test_vector_validation,test_graph_delete_cascade,test_kv_buffer_isolation,test_vector_reserved_keys}.py`, `tests/seam/{test_build_stores_cleanup,test_evidence_resolve_stores,test_health_probe,test_ingest_abort}.py`, `tests/runner/test_capability_scoping_modes.py`, `tests/wirings/test_store_effects_wired.py`, `tests/test_removed_stores_absent.py`, `tests/test_namespaces_gc.py`.

**Must be edited by Phase 11 changes (one consolidated owner grant):**

| File | Why | Exact collision |
|------|-----|-----------------|
| `tests/seam/test_rest_corpus_endpoints.py` (RUN-09, RUN-10) | D-09 per-workspace inbox, suffix name, removal after ingest | `test_generated_on_disk_name_is_reachable_for_a_multipart_uploaded_document` (:358-377) lists `store_root/"corpus-inbox"`, expects exactly one file whose stem is 32 hex and name equals `generated_on_disk_name(stem)`. RUN-10 round-trip tests (:432-535) should survive (test-local bodies, status fakes take `**kwargs`) - verify rather than assume |
| `tests/seam/test_ingest_file_name.py` (SEAM-15) | Same layout and name change | `test_non_ascii_upload_filename_is_never_stored` (:~76-87) asserts `inbox_files(store_root)` has one file matching `[0-9a-f]{32}\.bin`; the "not stored" description assertions (:31-47) keep passing if the descriptions still say "not stored" |
| `tests/wirings/test_store_effects_wired.py` (STOR-12) | D-06 rename + LRAG-03 effects | `_ARTIFACT_PARTS` (:192-196) pins `"lightrag/full-ingest@0.1.0"` and `test_the_three_artifact_parts_still_declare_writes_artifact` (:205-207) requires `writes_artifact`; `_SHIPPED_WIRINGS` (:255-264) must still parse |
| `tests/mcp/test_tool_growth_invariant.py` (RUN-01) | D-08 new tool | `assert len(names) == len(TOOL_NAMES) == 9` (:~92) and the `_TOOL_ARG_MODELS` tuple (:~68-78) |

**Constraints that avoid further edits (design around them):** `test_build_stores_cleanup.py` (STOR-02) - empty-root `query/ingest/delete_document` must raise `RuntimeError("graph open failed")` first, `kv built == finalized == 1`; `test_refusal_status_codes.py` (SEAM-04) - new refusals 422 (see Pattern D); `test_refusal_catalogue.py` (SEAM-14) - `__all__` + factory; `test_foreign_engine_refusal.py` (SEAM-05) and `test_corpus_adapter_failures.py` (SEAM-06) - keep `full_ingest.run_corpus_op`, `full_delete.run_corpus_op`, `engine.run_corpus_op` as module globals, keep `JSONDecodeError -> MalformedDriverOutput`, keep `{}` driver result as empty-not-fault (:112-121), keep `/health` 200 `degraded` on any adapter failure (:64-70); `test_health_probe.py` (STOR-04) - `_HEALTH_PROBES` content and the two drift tests (:172-189); `test_ingest_abort.py` (STOR-06) - HippoRAG only, no change; `stores/test_vector_validation.py` and `test_vector_crash_window.py` - re-run if `FaissVectorStore.__init__` stops creating the directory (A7).

**Not protected, will need edits (no grant):** `tests/seam/test_raw_upload_staging.py` (rewrite: owner-record tests go away), `tests/seam/_probes.py::inbox_files`, `tests/fixtures/v1_corpus_driver_stub.py` (ops removed, `health` shape, `working_dir` echo, usage), `tests/parts_core/lightrag/{test_full_ingest,test_full_delete,test_full_ingest_compat}.py`, `tests/seam/{test_delete_document,test_mach11_event,test_corpus_status,test_hipporag_write_path,test_promote,test_promotion_posture,test_rest_transport}.py`, `tests/parity/test_arm_conformance.py`. Specific: `test_mach11_event.py:358-400` expects the delete event component to be `lightrag/full-delete@...` with `counted_by == "unbudgetable"` and node-reported touches; under D-01 the event comes from the sync node (observed touches, `counted_by == "none"`); `test_hipporag_write_path.py:134-166` builds a registry with a capturing full-ingest body returning only `{"track_id","enqueued"}` and then runs the real sync - which must no-op (Finding 7a).

## Hermetic Real-Driver Harness (item 9)

**Existing support:** none for a stub *mode*. `tests/fixtures/v1_corpus_driver_stub.py` is a stdlib stand-in for the driver protocol (no v1, no state); `_make_fake_run_corpus_op` (test_corpus_status.py:25-49) patches `engine.run_corpus_op` with the stub's `_run_status`/`_run_health`; the only real-v1 tests are gated (`DATABASISE_RUN_REAL_DELETE=1` plus `v1/.parity_working_dir`, test_delete_document.py:256-272; `skipif(not _V1_VENV_PYTHON.exists())` smoke at test_full_ingest.py:255). Neither covers the real enqueue/pipeline code.

**Minimum needed (all spike-verified; ~2-3 s per v1 subprocess op):**
1. A loopback OpenAI-compatible stub server thread (`127.0.0.1:0`): `POST /v1/chat/completions` returns `{"choices":[{"message":{"content": <entity rows or "stub answer">}}], "model":..., "usage":{...}}`; `POST /v1/embeddings` returns `data[i].embedding` as a float list (not base64) with `usage`. Extraction replies must use v1's delimiter format (`entity<|#|>name<|#|>type<|#|>description`, `relation<|#|>src<|#|>tgt<|#|>keywords<|#|>description`, `<|COMPLETE|>`, prompt.py:12-13, 54-123); derive entity names from a `UNIQ...` token in the prompt so each document yields distinct rows. A sleep flag (file-triggered) provokes timeouts for LRAG-07.
2. A temp env file passed by `monkeypatch.setattr(v1_corpus_adapter, "DEFAULT_V1_ENV_PARITY", tmp_env)` (`run_corpus_op` reads the global at call time and applies the file **over** `os.environ`, adapter.py:123-125). Keys: `LLM_MODEL`, `LLM_BINDING_API_KEY`, `LLM_BINDING_HOST=http://127.0.0.1:<port>/v1`, `EMBEDDING_MODEL`, `EMBEDDING_BINDING_HOST`, `EMBEDDING_BINDING_API_KEY`, `EMBEDDING_DIM=8`, `EMBEDDING_USE_BASE64=false` (default `"true"`, llm/openai.py:108-110 - without it the stub must return base64), `LIGHTRAG_KV_STORAGE=JsonKVStorage`, `LIGHTRAG_GRAPH_STORAGE=CozoGraphStorage`, `LIGHTRAG_VECTOR_STORAGE=FaissVectorDBStorage`, `LIGHTRAG_DOC_STATUS_STORAGE=JsonDocStatusStorage`.
3. The real driver, real interpreter (`DEFAULT_V1_INTERPRETER`), a tmp `store_root`; `skipif(not v1 venv)` like test_full_ingest.py:255. The conftest guard (`_offline_unless_live`, tests/conftest.py:82-119) only patches the **test** interpreter's `socket.connect` to refuse non-loopback; loopback and subprocesses are unaffected, so RUN-12 holds.
4. Caveat: the subprocess runs with `cwd = v1/` (adapter.py:139) and v1 loads `v1/.env` with `override=False`; any variable the test relies on must be set explicitly in the env file (an unknown `.env` could add `LIGHTRAG_PARSER`, `INPUT_DIR`, etc.; A2).

**Verified scenarios that become the SC1 / LRAG-08 / 07 / 10 tests:** text ingest `processed` with chunk id `textdoc1-chunk-000`; file ingest of two different `.txt` -> two `processed` rows with `file_path` `aaa.txt`/`bbb.txt`, chunk ids `doc-<md5>-chunk-000`; same content under a new name -> `failed`, `duplicate_kind: content_hash`; same basename -> `dup-*` row, `track_id: None` from v1; `.xyz` -> `failed` at parse; kill at timeout -> `processing`; filtered ingest leaves it `processing`; retry -> `processed`; `import_v1_index` of the result -> naive query returns the right chunks and `resolve_evidence` returns `{"id", "content", "full_doc_id", "file_path"}`. To reach the KG arms in-process use `engine._execute_resolved(QueryObject(...), resolve_arm("hybrid"))` (the path `compare` uses, engine.py:874); a capability selector cannot (it resolved `reads_graph` to HippoRAG and `calls_rerank` to naive in spike5).

## Common Pitfalls

### Pitfall 1: Staged file is moved, not read in place
**What goes wrong:** the inbox keeps `__parsed__/<name>` after success; `GET`/delete leaves a copy; LRAG-09 ("no inbox file outlives its job") fails on a `Path.iterdir()` check.
**Why:** `LegacyParser.parse` ends with `ctx.archive_source` (parser/legacy/parser.py:70) -> `archive_docx_source_after_full_docs_sync` (utils_pipeline.py:759).
**How to avoid:** cleanup walks both `<inbox>` and `<inbox>/__parsed__`; assert the whole inbox tree is empty after success, refusal and delete.
**Warning signs:** `__parsed__` directory appears under the inbox.

### Pitfall 2: v1 recovery bills for old failures on every ingest
**What goes wrong:** every unfiltered `apipeline_process_enqueue_documents()` retries all FAILED/PENDING/PARSING/ANALYZING/PROCESSING docs (spike2 B reprocessed case A's failed doc: 5 model calls for an ingest that enqueued nothing).
**How to avoid:** the driver wrapper in Pattern A for ingest and retry.

### Pitfall 3: A path with no `working_dir` silently falls back to the operator corpus
**Where:** `run_corpus_op` default (adapter.py:129) and the module constant `DEFAULT_V1_WORKING_DIR` (adapter.py:31) that `test_delete_document.py:301` monkeypatches. **Avoid:** required keyword; delete the constant from the adapter's `__all__` (parity code has its own constants in `parity/v1_arm.py:37`).

### Pitfall 4: Two driver processes on one working dir
**Proof:** Finding 3. **Avoid:** engine gate (Pattern C). The `status` op during a write is the common case (UI polling).

### Pitfall 5: Check ordering vs protected tests
See Finding 8: new pre-checks run after `_build_stores`; the config check lives in the driver.

### Pitfall 6: Sync deletes what it should not
Absent dir/doc_status -> no-op; unreadable -> raise. Dup and interrupted rows are excluded by the PROCESSED-only rule, so a timed-out ingest never exposes partial rows to queries. After a failed v2 commit the stores diverge until the next sync (D-01 residual window; document in the engine docstring).

### Pitfall 7: `IngestJob` growth is public API
LRAG-03's test needs events on the returned job: add `seam_events: list[SeamEvent] = []` (mirrors `DeletionOutcome`, corpus.py:122-139). `IngestJob` is `frozen`, `extra="forbid"`; REST and MCP return it unchanged, so schema consumers see a new optional field. Consider returning `document_id` too (LRAG-10 callers cannot otherwise learn a server-minted id; Open Question 7).

### Pitfall 8: LRAG-19 by node removal changes `derive_mutation_class`
Evidence in Finding 9. Decide: accept the new classes (update the two unprotected tests) or add a rule that keeps arms classed by recipe membership. Also `selectors._wiring_effects` unions lose `writes_artifact` and one `calls_embedding` for hybrid/local/global (naive keeps `calls_embedding` through `embedder-query`); no test found that selects a LightRAG arm by `writes_artifact` (test_selectors.py references only the opaque-provides rule).

### Pitfall 9: `status` reads facade-build failures as faults
Even without a write, a missing key makes the driver exit non-zero today (KeyError traceback -> CorpusOpSubprocessError -> 502 reasonless). The driver-side key check turns that into exit 3 and a named 503.

### Pitfall 10: AST pin constraints on the driver
Helpers that read `job[...]` outside the `_run_<op>` function body are invisible to the pin; dict returns must be literal. Keep the op functions flat (test_full_ingest_compat.py:232-333).

### Pitfall 11: `token_tracker` zero-usage
Finding 5; test with a stub server variant that omits `usage` (expect `unbudgetable`) and one with usage (expect `counted_by != "unbudgetable"`, LRAG-11 test).

### Pitfall 12: `chunk_top_k` default drift
Changing `chunk_vector.py:17` from 10 to v1's 20 shifts parity numbers (A10); decide explicitly and rerun `tests/parity`.

## Code Examples

### Loopback stub server (spike-verified, trimmed)
```python
# Source: this research's spike (scratchpad stub_server.py); stdlib only
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path.endswith("/chat/completions"):
            text = "\n".join(str(m.get("content")) for m in body["messages"])
            tok = (re.findall(r"UNIQ[A-Za-z0-9]+", text) or ["NOTOKEN"])[-1]
            out = (f"entity<|#|>{tok} Corp<|#|>Organization<|#|>{tok} Corp is an organization.\n"
                   f"entity<|#|>{tok} City<|#|>Location<|#|>{tok} City is a place.\n"
                   f"relation<|#|>{tok} Corp<|#|>{tok} City<|#|>located in<|#|>{tok} Corp is in {tok} City.\n<|COMPLETE|>"
                   ) if "entities and relationships" in text else "stub answer"
            self._send({"id": "c1", "object": "chat.completion", "created": 0, "model": "stub-llm",
                        "choices": [{"index": 0, "message": {"role": "assistant", "content": out}, "finish_reason": "stop"}],
                        "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}})
        elif self.path.endswith("/embeddings"):
            ins = body["input"] if isinstance(body["input"], list) else [body["input"]]
            self._send({"object": "list", "model": "stub-embed",
                        "data": [{"object": "embedding", "index": i, "embedding": _vec(t)} for i, t in enumerate(ins)],
                        "usage": {"prompt_tokens": 3 * len(ins), "total_tokens": 3 * len(ins)}})
srv = ThreadingHTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
```

### Usage capture in the driver (names from driver lines 125-170 and openai.py signatures)
```python
llm_tracker, embed_tracker = TokenTracker(), TokenTracker()          # lightrag.utils (utils.py:4194)
# _llm_model_func: pass token_tracker=llm_tracker to openai_complete_if_cache(...)  (openai.py:249)
# _build_rag:      partial(openai_embed.func, ..., token_tracker=embed_tracker)       (openai.py:904)
usage = {"llm": llm_tracker.get_usage(), "embedding": embed_tracker.get_usage()}
```
The trackers must be created per process run and handed to `_build_rag(working_dir, trackers)`.

### Prompt drift test shape
```python
# Source: technique of tests/parts_core/lightrag/test_full_ingest_compat.py:284-333
tree = ast.parse(Path("v1/lightrag/prompt.py").read_text())
v1 = {n.targets[0].slice.value: n.value.value for n in tree.body
      if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Subscript)
      and getattr(n.targets[0].value, "id", "") == "PROMPTS" and isinstance(n.value, ast.Constant)
      and isinstance(n.value.value, str)}
assert v1["rag_response"] == generate_module._RAG_RESPONSE   # likewise naive_rag_response, kg_query_context, naive_query_context, fail_response
```
(`PROMPTS["default_entity_types_guidance"]`-style multi-line assignments parse as `ast.Constant` too; the list-valued entries are skipped by the `isinstance` filter.)

### Gate skeleton
```python
_WRITE_GATES: dict[str, threading.Lock] = {}
def _acquire(working_dir: Path) -> threading.Lock:
    lock = _WRITE_GATES.setdefault(str(working_dir.resolve()), threading.Lock())
    if not lock.acquire(blocking=False):
        raise StoreBusyError(store_kind="corpus")
    return lock          # caller releases in finally
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v1 `ainsert`-style RAW ids path | `pending_parse` + parser routing (legacy default) | v1 1.5.x | `ids=` is documented to force RAW (pipeline.py:255-266); file docs get hash ids |
| Content-addressed chunk ids (CONTEXT note) | `<doc_id>-chunk-NNN` in 1.5.4 [VERIFIED: kv_store_text_chunks.json keys] | v1 1.5.4 | "unique token" in the test text still matters for entity names, not chunk ids |

**Deprecated/outdated:** none in scope.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `.env.parity` selects JsonKV + JsonDocStatus + Faiss + Cozo (inferred from file layout of existing working dirs and README-PARITY D-05; the file was not read) | Finding 7, Pattern B | The "refuse other backends by name" check would refuse the operator's real config |
| A2 | `v1/.env` (unread) does not set `LIGHTRAG_PARSER`, `INPUT_DIR`, `MINERU_*` or `DOCLING_ENDPOINT` | Suffix list, harness caveat | Suffix list could be larger; hermetic tests could behave differently on this machine |
| A3 | The `get_docs_by_statuses` instance wrapper behaves the same on non-JSON doc-status backends | Pattern A | Only matters if D-01's backend refusal is relaxed |
| A4 | Accepting all 40 legacy suffixes (not only txt/md/pdf/docx) is wanted | Pattern C | Owner may prefer a narrower allowlist; D-09 says "at least" the four |
| A5 | RocksDB lock conflict also applies to every other driver op (proven only for `status` vs a running `ingest`) | Finding 3 | Over-serialization only; harmless |
| A6 | The `len//4` approximation deviates from v1's tokenizer by an unmeasured margin | Pattern F step 8/12 | KG context may be truncated earlier or later than v1 |
| A7 | Moving `mkdir` out of `FaissVectorStore.__init__` does not break STOR-08/09 tests (not run) | Pattern F D-15 | Fall back to the `create=False` argument |
| A8 | A killed v1 subprocess leaves JSON/Faiss/Cozo files readable (spike3 read them fine after one kill; not stress-tested) | Pitfall 6 | A corrupt snapshot makes the sync raise (fail closed) |
| A9 | Retry returns an `IngestJob` whose `job_id` is the document's original v1 `track_id` | Pattern C | Caller-facing shape choice |
| A10 | Changing chunk vector `top_k` 10 -> 20 is acceptable to parity evidence | Pattern F step 3 | Parity regressions in `tests/parity` |

## Open Questions (RESOLVED — orchestrator rulings 2026-10-17 on the owner's "You decide" delegation; binding for planning)

- **Q1 RESOLVED:** use the stem rule. The staged file is `<document_id><suffix>` in the per-workspace inbox, the driver sets `INPUT_DIR` to the inbox, and it maps v1's `doc-<md5>` back to our id through `Path(file_path).stem`. Cleanup covers both `<inbox>/<name>` and `<inbox>/__parsed__/<name>`. If the planner finds the stem rule cannot hold, RAW-after-`extract_text` is the documented fallback.
- **Q2 RESOLVED:** status ops are **facade-free**. GET /corpus, /corpus/counts and /jobs read `kv_store_doc_status.json` directly, with no v1 facade and no Cozo open, so they work while a write is running. The operator console polls during ingests, which Phase 18 needs.
  - A JSON parse error is retried once.
  - A file that is still unreadable gives `StoreBusyError(store_kind="corpus")` (409).
  - Writes (ingest, delete, retry) take the D-07 per-working-dir lock. A second write gets a 409.
- **Q3 RESOLVED:** missing v1 config raises `ForeignEngineRefusalError(failure_class="V1NotConfigured")` (503) with a public `missing_keys` list. The list holds key names only (D-12).
  - Driver protocol: exit code 3 with `{"error": "v1_not_configured", "missing_keys": [...]}`.
- **Q4 RESOLVED:** for LRAG-19, `embedder-index` stays in the wiring's node set, marked recipe-only and skipped at query time. It is not removed, so `derive_mutation_class` and the promotion tests do not change.
  - If skipping still changes the derived class, keep the class stable through an explicit recipe marker.
- **Q5 RESOLVED:** `HealthReport` gains `engine_reason: str | None`. It holds short fixed text, for example `"v1 not configured: missing EMBEDDING_DIM, EMBEDDING_MODEL"` or `"model clients not configured"`, with key names only and no values.
- **Q6 RESOLVED:** correction to D-03. `aa_run` keeps the **default selector**, whatever it resolves to (currently `naive`), and gains `--arm`. `--arm` maps to selectors the way `corpus_ingest._ARM_SELECTORS` does. LRAG-15's test asserts non-empty evidence, not a score; scoring stays TOOL-11 (Phase 15).
- **Q7 RESOLVED:** `IngestJob` grows only by fields a requirement's test needs. Add `document_id` if the D-09 mapping needs it. LRAG-03's seam events stay in the trace/recorder and are not added to `IngestJob`, unless LRAG-03's test text requires them.
- **Q8 RESOLVED:** the new `lightrag/v1-index-sync` part starts at `@0.1.0`. The existing parts whose effects, verdicts or protocol change bump once to `@0.2.0` (D-06).
- **Q9 RESOLVED:** PENDING rows are not widened into "interrupted". Note it in the docstring only.

1. **Doc id mapping choice (file path vs RAW-after-extract).**
   - Known: on the file path v1's id is `doc-<md5(basename)>`; the stem rule maps back without state.
   - Unclear: whether the owner accepts the mapping layer or prefers the driver extracting text with `extract_text` and enqueuing RAW with our id.
   - Recommendation: implement D-09 as written with the stem rule; keep the alternative as the documented fallback.
2. **Facade-free `status`.** Recommendation: gate + 409 now (small, safe); consider a direct `kv_store_doc_status.json` read later if UI polling during ingest matters.
3. **"v1 not configured" status class.** Recommendation: `ForeignEngineRefusalError(failure_class="V1NotConfigured")`, 503, `missing_keys` attribute - avoids editing the protected SEAM-04 test.
4. **LRAG-19 promotion ripple.** Accept the new classes, or keep an index-recipe marker? Needs a one-line owner/planner call recorded in the plan.
5. **HealthReport reason field name and shape.**
6. **`aa_run` default arm.** CONTEXT D-03 says the default selector is "lightrag-base"; `_resolve_default` returns the first default-eligible wiring, which is `naive` (`resolve_arm("naive")`, test_selectors.py:276-285). `--arm` should map to selectors the way `corpus_ingest._ARM_SELECTORS` does (eval/corpus_ingest.py:84-87). `score_gold_passage` reads `record["document_id"]` (aa_run.py:243) which LightRAG chunk records do not carry (`full_doc_id`): that is TOOL-11 (Phase 15); LRAG-15's test should assert non-empty evidence, not a score.
7. **`IngestJob` additions** (`seam_events`, `document_id`).
8. **Sync part version label** (`@0.1.0` new part vs `@0.2.0` to match). CONTEXT D-06 says "one `@0.2.0` bump".
9. **Interrupted label scope:** PENDING (enqueued but never processed) is not covered by D-08; a killed multi-document batch would leave PENDING rows reported as `pending` forever. Single-document ingests make this rare; note, do not widen.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `v1/.venv/bin/python` | all real-driver work and the harness | yes | Python 3.12.13, lightrag 1.5.4 | tests `skipif` like test_full_ingest.py:255 |
| `databasise/.venv` | suite | yes | Python 3.12.13, pytest 9.1.1 | - |
| Loopback sockets | stub model server | yes (spikes ran) | - | - |
| Network / model endpoints | none (offline suite) | not used | - | RUN-12: `-m live` never run |
| pandas | pycozo optional feature | no (warning only) | - | harmless |
| `v1/.corpus_working_dir` | not touched | exists | 310 failed rows | - |

**Missing dependencies with no fallback:** none. **With fallback:** none.

## Validation Architecture

Config check: `.planning/config.json` has `workflow.nyquist_validation: true` (included).

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1, `asyncio_mode = "auto"` |
| Config file | `databasise/pyproject.toml` `[tool.pytest.ini_options]` (`addopts = '-m "not live"'`) |
| Quick run command | `cd databasise && .venv/bin/pytest tests/seam tests/parts_core/lightrag tests/foreign -x -q` |
| Full suite command | `cd databasise && .venv/bin/pytest` and `.venv/bin/python -m pytest` (RUN-12: both 0 failed) |

### Phase Requirements -> Test Map

REQUIREMENTS.md names a file only for LRAG-12 (`test_full_ingest_compat`) and LRAG-14 ("test_health module"); the rest say "Test ..." with no file. Proposed names (new files avoid editing protected ones; `test_health_probe.py` is STOR-04 protected, so LRAG-13/14 get a new file):

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| LRAG-01 | Two apps/two roots; every captured payload/kwarg carries `working_dir` under `store_root/workspace/lightrag-v1`; app B's GET /corpus empty | unit (patched `run_corpus_op`) | `pytest tests/seam/test_lightrag_working_dir.py -x` | no, Wave 0 |
| LRAG-02 | Real driver + stub server: ingest -> query arm -> evidence resolves; delete -> gone; `/evidence/resolve` refuses old ref | integration (real v1) | `pytest tests/seam/test_lightrag_corpus_path.py -x` | no, Wave 0 |
| LRAG-03 | Stubbed driver: job carries seam events; Part effects contain `mutates_store`, not `writes_artifact` | unit | `pytest tests/seam/test_lightrag_ingest_mach11.py -x` | no, Wave 0 |
| LRAG-04 | Two concurrent writes: second `StoreBusyError`; intervals do not overlap | unit | `pytest tests/seam/test_corpus_write_gate.py -x` | no, Wave 0 |
| LRAG-05 | Fake driver >2000 chars then `ValueError: boom` in error tail; non-JSON stdout named; driver `status` limit -1 refused; docstring checks | unit | `pytest tests/foreign/test_v1_corpus_adapter.py -x` | no, Wave 0 |
| LRAG-06 | Driver exit 3 -> adapter -> 503 with `missing_keys`, no values; /health reason | unit + real driver with empty env | `pytest tests/foreign/test_v1_not_configured.py -x` | no, Wave 0 |
| LRAG-07 | Kill at timeout -> `interrupted`; unrelated ingest leaves it; retry -> processed | integration (real v1) | `pytest tests/seam/test_interrupted_documents.py -x` | no, Wave 0 |
| LRAG-08 | Two different `.txt` -> processed with own tokens; `.xyz` refused 422; no `dup-` row | integration (real v1) | `pytest tests/seam/test_lightrag_corpus_path.py -k upload -x` | no, Wave 0 |
| LRAG-09 | Two workspaces -> two inbox paths; tree empty after success/refusal/delete (incl. `__parsed__`) | integration | `pytest tests/seam/test_lightrag_inbox.py -x` | no, Wave 0 |
| LRAG-10 | Re-ingest of same id/basename/content -> `enqueued == 0`; job_id equals recorded track | integration | `pytest tests/seam/test_lightrag_corpus_path.py -k duplicate -x` | no, Wave 0 |
| LRAG-11 | Stub returns usage -> `counted_by != "unbudgetable"`; no usage -> `unbudgetable`; delete effects contain `calls_llm` | unit + real | `pytest tests/parts_core/lightrag/test_corpus_metering.py -x` | no, Wave 0 |
| LRAG-12 | (condition, verdict) pairs for 3, 8, 9 pinned for both ports and the sync | unit | `pytest tests/parts_core/lightrag/test_full_ingest_compat.py -x` | yes (edit) |
| LRAG-13 | Snapshot store_root and v1 dir around GET /health; unchanged | unit | `pytest tests/seam/test_health_honesty.py -x` | no, Wave 0 |
| LRAG-14 | `clients=None` -> not ok; HippoRAG keys; `working_dir_present` true on driver failure; probe exception -> 200 degraded | unit | `pytest tests/seam/test_health_honesty.py -x` | no, Wave 0 |
| LRAG-15 | `corpus_ingest --arm lightrag` payload dirs under the eval store; query over the same store has evidence | unit | `pytest tests/eval/test_corpus_ingest.py tests/eval/test_aa_run.py -x` | yes (edit) |
| LRAG-16 | Fresh root -> `EmptyNamespaceError`, no LLM call, no `vector.faiss` created; populated no-match plain | unit | `pytest tests/seam/test_empty_namespace.py -x` | no, Wave 0 |
| LRAG-17 | Recording LLM: system message has entity/relation JSON lines, headers, within the cap; naive uses `naive_rag_response`; prompt drift test | unit | `pytest tests/parts_core/lightrag/test_kg_fidelity.py tests/parts_core/lightrag/test_v1_prompt_drift.py -x` | no, Wave 0 |
| LRAG-18 | Fixture-graph parity vs hand-computed v1 order; join dedup; VECTOR run reports `pick_method_used`; rerank query non-empty; one `node_degree` per node | unit | `pytest tests/parts_core/lightrag/test_kg_fidelity.py -x` | no, Wave 0 |
| LRAG-19 | No `embedder-index` node in any arm's trace; arm patches' `resulting_node_id_set` match | unit | `pytest tests/parity/test_arm_conformance.py tests/seam/test_query_trace_nodes.py -x` | partial |
| LRAG-20 | Driver rejects `entities`/`entity_info` as unknown ops; no fixture references them | unit | `pytest tests/parts_core/lightrag/test_full_ingest_compat.py -x` | yes (edit) |

### Sampling Rate
- **Per task commit:** the touched test file(s) with `-x -q`.
- **Per wave merge:** `pytest tests/seam tests/parts_core tests/foreign tests/stores tests/wirings tests/parity -q`.
- **Phase gate:** full suite green under both invocation styles before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] `tests/fixtures/v1_stub_server.py` - loopback model server + env-file builder (shared by the real-driver tests).
- [ ] Real-driver fixtures (`tests/seam/conftest.py` is unprotected; add a module-scoped server fixture).
- [ ] New test files listed above; update `tests/fixtures/v1_corpus_driver_stub.py` for the new protocol.
- [ ] Ledger: record `test_ref` for LRAG-01..20 (use `scripts/ledger-amend.py`, never Bash on `ledger/`).

## Security Domain

`security_enforcement` is not set to `false` in config (treated as enabled).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (seam authentication is undecided, deferred) | - |
| V3 Session Management | no | - |
| V4 Access Control | no | - |
| V5 Input Validation | yes | `fullmatch` token regex for document ids (corpus.py:62), suffix allowlist + `\.[a-z0-9]{1,8}`, size cap (corpus.py:49), generated names only (RUN-09) |
| V6 Cryptography | no | md5 used by v1 only for ids, not security |
| V7 Error handling and logging | yes | stderr tail goes to the server log once (engine `_foreign_fault`), never to the body; config refusals name keys, never values (D-12) |
| V12 Files and resources | yes | exclusive create (`"xb"`), staging inside the per-workspace inbox, removal on success/refusal/delete, `__parsed__` copy removed, v1 parser runs in a subprocess under a wall-clock ceiling |
| V14 Configuration | yes | no secret values in logs/bodies; `parity-env.txt` holds live credentials (Finding 12) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `file_name` (`../x.pdf`, `a.pdf/../..`, NUL, unicode) | Tampering | Reduce to basename, take only a validated lower-case suffix; the staged name is `<validated id><suffix>` - the caller's name never reaches disk |
| Parser-hint injection in a file name (`abc.[mineru].pdf`; `normalize_document_file_path` strips `[hint]` segments and `resolve_parser_directives` honours them, routing.py:1105-1141) | Tampering / EoP | Never include caller text in the staged name; suffix regex forbids brackets |
| Malicious document exploiting v1 extractors (pypdf, python-docx, openpyxl) | Tampering / DoS | Subprocess isolation, 900 s ceiling, 25 MB cap; keep timeouts enforced by `run_corpus_op` |
| Information disclosure through stderr or env names | Info disclosure | Server-log only; the single exception is D-12's key names |
| Stale staged files holding user documents | Info disclosure | Cleanup rules and the inbox-empty tests (Pitfall 1) |
| Sync destroying data from a bad snapshot | Tampering / DoS | No-op on absent, raise on corrupt, drop pending on any failure |
| Cross-workspace leakage | Info disclosure | Per-workspace working dir and inbox; the Phase 9 shared-inbox owner records go away |

## Sources

### Primary (HIGH confidence, read or executed this session)
- `databasise/foreign/v1_corpus_driver_script.py`, `v1_corpus_adapter.py`; `parts_core/lightrag/*.py`; `parts_core/declared_only.py`, `parts_core/__init__.py`; `parity/import_index.py`; `seam/{engine,corpus,refusals,rest,promotion,selectors,tokens,trace_store}.py`; `stores/{vector,probes}.py`; `runner/scheduler.py`; `validator/{execution_mode,parse,depth,blast_radius}.py`; `parts/{admission,registry,schema}.py`; `clients/{base,openai_compat}.py`; `eval/{corpus_ingest,aa_run}.py`; `mcp/tools.py`; `evidence/COVERAGE.md`; `wirings/lightrag/*`; `parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md`.
- v1: `lightrag/pipeline.py` (enqueue 232-851, process 927-1137, parse worker 1546+, `_resolve_source_file_for_parser` 3127), `operate.py` (kg_query 3792, context 4264-5717, naive_query 5746), `prompt.py`, `utils.py` (TokenTracker 4194, `process_chunks_unified` 4335, `generate_reference_list_from_chunks` 4929), `utils_pipeline.py`, `parser/{registry,routing,legacy/parser,base}.py`, `llm/openai.py`, `constants.py`, `README-PARITY.md`.
- docs/system-model/CONTRACT.md §8 (lines 368-388).
- Tests read: `test_rest_corpus_endpoints`, `test_health_probe`, `test_corpus_status`, `test_corpus_adapter_failures`, `test_foreign_engine_refusal`, `test_ingest_file_name`, `test_build_stores_cleanup`, `test_store_effects_wired`, `test_ingest_abort`, `test_refusal_status_codes`, `test_delete_document`, `test_full_ingest`, `test_full_ingest_compat`, `test_tool_growth_invariant`, `test_vector_validation`, parts of `test_mach11_event`, `test_hipporag_write_path`, `test_promote`, `test_promotion_posture`, `test_selectors`, `test_embedder_index_reproduction`.
- Executed spikes (scratchpad, not in repo): `/tmp/claude-1000/-home-chris-coding-Databasise-2-0-fully-agnostic-system/32d1701b-4256-409c-a5a7-e305cc822f40/scratchpad/{stub_server,spike1..7}.py` - real driver + real v1 + loopback stub; outputs quoted in the findings.

### Secondary (MEDIUM)
- `.planning/REQUIREMENTS.md` LRAG-01..20 test descriptions; `.planning/phases/11-lightrag-corpus-path/11-CONTEXT.md`; `ledger/REQUIREMENTS.json` (Read tool).

### Tertiary (LOW)
- None used for claims; unverified items are in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - nothing new; all components exercised.
- Architecture (driver, sync, lifecycle): HIGH for v1 behaviours, MEDIUM for engine-side design choices (gate semantics, mapping, health field).
- Pitfalls and protected-test collisions: HIGH - read from the actual test files.
- D-16 gap table: HIGH for v1 steps and v2 file:line; MEDIUM for the exact change shapes.

**Research date:** 2026-10-17
**Valid until:** 2026-11-16 (v1 is pinned at 1.5.4; re-check only if `v1/` is updated)
