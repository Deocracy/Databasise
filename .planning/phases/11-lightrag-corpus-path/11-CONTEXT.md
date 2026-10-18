# Phase 11: LightRAG Corpus Path - Context

**Gathered:** 2026-10-17
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous). The owner was shown four grey areas, each with a recommended option, and answered "You decide" for all four. Every decision below is Claude's choice under that delegation. Each is recorded as a numbered decision, so planning and verification treat it as binding.

<domain>
## Phase Boundary

A document ingested through the seam's LightRAG path is what the LightRAG query arms retrieve. Uploads index their real content, health reports only facts it checked, and the KG arms answer the way v1 answers. Requirements: LRAG-01 to LRAG-20.

**In scope:**
- the v1 working dir per workspace
- the v1-to-v2 sync (M-04 option b)
- write-lifecycle semantics
- adapter faults and metering
- health facts
- KG-arm fidelity to v1 `kg_query`

**Out of scope:**
- machine-native LightRAG ingest (M-04 option a)
- seam authentication (CONN phases)
- migrating the existing operator corpus in `v1/.corpus_working_dir` (TOOL-02, Phase 15; see Deferred)

</domain>

<decisions>
## Implementation Decisions

### A. Write path and scoping (M-04, M-12, LRAG-01/02/03/15/19/20)

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

### B. Write lifecycle (LRAG-04, 07, 08, 09, 10)

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

### C. Faults, health and metering (LRAG-05, 06, 11, 13, 14)

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

### D. Query fidelity (LRAG-16, 17, 18)

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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md`: the Phase 11 goal, success criteria and owner-decision list.
- `.planning/REQUIREMENTS.md`: LRAG-01 to LRAG-20, plus SEAM-15, TOOL-02, TOOL-11, LIVE-05 and HIPP-15 (the M-04 and M-12 consumers).
- `docs/gui/DEFECTS.json`: source defect uids, including M-04, M-12, G-20, G-27 and G-33.
- `docs/system-model/CONTRACT.md` and `OPAQUE-BOUNDARY-RULE.md`: §8 conditions, the version bump, re-admission, and §18 with the §18.5 tool growth rule.
- `databasise/evidence/COVERAGE.md`: the new retry route needs rows here, and the entity-op test-support rows are removed.
- `.planning/phases/08-*/08-CONTEXT.md`, `09-*/09-CONTEXT.md` and `10-*/10-CONTEXT.md`: locked decisions. D-12 here amends Phase 9 D-04 narrowly for config key names.
- `v1/lightrag/operate.py` (`kg_query`, `kg_query_context`, `rag_response` formatting), `v1/lightrag/prompt.py` and `v1/lightrag/pipeline.py` (enqueue, dedup, status, recovery): the v1 behaviour D-08, D-10 and D-16 must match.

</canonical_refs>

<code_context>
## Existing Code Insights

- `parts_core/lightrag/full_ingest.py:220-234`: `run_corpus_op("ingest", ...)` with no working_dir, plus the dead usage branch. `foreign/v1_corpus_adapter.py:31,64,129,149`: `DEFAULT_V1_WORKING_DIR`, the stderr head slice and the JSON parse. `foreign/v1_corpus_driver_script.py:125-142,180-198,299-329`: the LLM func, enqueue with `ids=`, limits and the health op.
- `parity/import_index.py:167-265`: `import_v1_index` readers and separate flushes, to be refactored for staged stores.
- `seam/engine.py`: ingest, delete, status, jobs (1193-1211) and health (1278-1285). The Phase 9 staging and owner records (945-1005, 1055-1084) are replaced by D-09.
- `parts_core/lightrag/generate.py:30`, `assemble.py:31-35` and the kg arms: the D-16 fidelity targets.
- `stores/vector.py:695-702`: `select` creates on read (D-15).
- `eval/aa_run.py:357` and `eval/corpus_ingest.py:67-69`: D-03.
- Commits need a `phase/11` trailer.
- **Protected tests (the BAK ledger `test_ref` files) need the owner's `grant-check-edit`:** the 8 RUN files, the 16 SEAM files and the 16 STOR files. At least `tests/seam/test_rest_corpus_endpoints.py` (D-09) is expected. Re-check `test_full_ingest_compat` (LRAG-12) and every other file a task edits against the ledger at plan time. Use the Read tool, not Bash, on `ledger/`.

</code_context>

<specifics>
## Specific Ideas

There are no owner requirements beyond the decisions above. The REQUIREMENTS.md test descriptions for each LRAG ID are the acceptance contract, with the D-08 (conditional) and D-12 exception clauses.

The SC1 proof uses the real v1 driver and pipeline with stub LLM and embedding functions. LRAG-08's test needs the same harness. It ingests a document with a unique token, because chunk ids are content-addressed.

</specifics>

<deferred>
## Deferred Ideas

- **M-04 option (a)**, machine-native LightRAG ingest: revisit if v1's subprocess becomes a constraint.
- **Migration of `v1/.corpus_working_dir`:** the existing operator corpus is migrated with TOOL-02 (`import_index --v1-working-dir`, Phase 15). Until then, that data is not visible under the per-workspace dir.
- **A real tokenizer** for v1 token-allocation fidelity: wait for an offline-safe encoding.
- **An operator field exposing v1 stderr:** revisit with the seam authentication decision.

</deferred>

---

*Phase: 11-lightrag-corpus-path*
*Context gathered: 2026-10-17*
