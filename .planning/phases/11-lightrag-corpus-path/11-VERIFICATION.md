---
phase: 11-lightrag-corpus-path
verified: 2026-11-01T07:25:30Z
status: passed
score: 25/25 must-haves verified (5 success criteria, 20 LRAG requirements)
covered_files:
  - ".planning/phases/11-lightrag-corpus-path/11-01-PLAN.md"
  - ".planning/phases/11-lightrag-corpus-path/11-01-SUMMARY.md"
  - ".planning/phases/11-lightrag-corpus-path/11-02-PLAN.md"
  - ".planning/phases/11-lightrag-corpus-path/11-02-SUMMARY.md"
  - ".planning/phases/11-lightrag-corpus-path/11-03-PLAN.md"
  - ".planning/phases/11-lightrag-corpus-path/11-03-SUMMARY.md"
  - ".planning/phases/11-lightrag-corpus-path/11-04-PLAN.md"
  - ".planning/phases/11-lightrag-corpus-path/11-04-SUMMARY.md"
  - ".planning/phases/11-lightrag-corpus-path/11-05-PLAN.md"
  - ".planning/phases/11-lightrag-corpus-path/11-05-SUMMARY.md"
  - ".planning/phases/11-lightrag-corpus-path/11-06-PLAN.md"
  - ".planning/phases/11-lightrag-corpus-path/11-06-SUMMARY.md"
  - ".planning/phases/11-lightrag-corpus-path/11-07-PLAN.md"
  - ".planning/phases/11-lightrag-corpus-path/11-07-SUMMARY.md"
  - ".planning/phases/11-lightrag-corpus-path/11-08-PLAN.md"
  - ".planning/phases/11-lightrag-corpus-path/11-08-SUMMARY.md"
  - ".planning/phases/11-lightrag-corpus-path/11-09-PLAN.md"
  - ".planning/phases/11-lightrag-corpus-path/11-09-SUMMARY.md"
  - ".planning/phases/11-lightrag-corpus-path/11-10-PLAN.md"
  - ".planning/phases/11-lightrag-corpus-path/11-10-SUMMARY.md"
  - ".planning/phases/11-lightrag-corpus-path/11-11-PLAN.md"
  - ".planning/phases/11-lightrag-corpus-path/11-11-SUMMARY.md"
  - "databasise/eval/aa_run.py"
  - "databasise/foreign/v1_corpus_adapter.py"
  - "databasise/foreign/v1_corpus_driver_script.py"
  - "databasise/mcp/server.py"
  - "databasise/mcp/tools.py"
  - "databasise/parity/import_index.py"
  - "databasise/parts_core/lightrag/assemble.py"
  - "databasise/parts_core/lightrag/chunk_sel_kg.py"
  - "databasise/parts_core/lightrag/chunk_vector.py"
  - "databasise/parts_core/lightrag/full_delete.py"
  - "databasise/parts_core/lightrag/full_ingest.py"
  - "databasise/parts_core/lightrag/generate.py"
  - "databasise/parts_core/lightrag/prompts.py"
  - "databasise/parts_core/lightrag/v1_index_sync.py"
  - "databasise/seam/corpus.py"
  - "databasise/seam/engine.py"
  - "databasise/seam/jobs_store.py"
  - "databasise/seam/refusals.py"
  - "databasise/seam/rest.py"
  - "databasise/stores/vector.py"
  - "databasise/wirings/lightrag/base.json"
  - "databasise/wirings/lightrag/corpus-delete.json"
  - "databasise/wirings/lightrag/corpus-ingest.json"
  - "databasise/wirings/resolve.py"
covered_digest: "v3:sha256:0ce5a5efe9dd47ed16d457139ac535e657af309caf0c2fcdd3c3bef54f76c29c"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 25/25
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 11: LightRAG Corpus Path Verification Report

**Phase Goal:** A document ingested through the seam's LightRAG path is what the LightRAG query arms retrieve, uploads index their real content, health reports only facts it checked, and the KG arms answer the way v1 answers.
**Verified:** 2026-11-01 (re-verification after the audit fixes; earlier passes 2026-10-19 and 2026-10-31)
**Status:** passed (no failed truth, no blocker; all five human items resolved, deferred or routed by the owner, see below)
**Re-verification:** Yes. Stale-report refresh: 14 covered files moved after the 2026-10-19 report (Phases 12-16 touched `seam/engine.py`, `seam/rest.py`, `seam/refusals.py`, `mcp/server.py`, `mcp/tools.py`, `eval/aa_run.py`, `parity/import_index.py`, `stores/vector.py`, `wirings/resolve.py`, `wirings/lightrag/base.json`, and four lightrag parts). The must-haves are unchanged; they were re-checked against the current code. A second refresh on 2026-11-01 followed the debugging and security battery fixes to `seam/corpus.py`, `seam/engine.py`, `seam/refusals.py`, `seam/rest.py` and `parts_core/lightrag/full_ingest.py` (see "Re-verification 2026-11-01 (audit fixes)").

## Method

Goal-backward from ROADMAP success criteria 1-5 and LRAG-01..20. SUMMARY claims were not used as evidence.

- Targeted tests, run from `databasise/` with `.venv/bin/pytest -q`. No `-m live`.
  - 13 seam files: **103 passed**.
  - `tests/foreign`, the eval, parts_core/lightrag, parity arm-conformance and wiring files, plus the protected corpus, file-name, tool-growth and store-effect files: **273 passed**.
  - 0 failed, 0 skipped. The real-v1 tests ran against the v1 venv.
- Two own probes using the hermetic loopback stub (`tests/fixtures/v1_stub_server.py`, temp env overlay, temp store roots, real v1 driver):
  - `/tmp/claude-1000/-home-chris-coding-Databasise-2-0-fully-agnostic-system/32d1701b-4256-409c-a5a7-e305cc822f40/scratchpad/verify11/probe_sc.py`: 31 of 36 checks passed.
  - `/tmp/claude-1000/-home-chris-coding-Databasise-2-0-fully-agnostic-system/32d1701b-4256-409c-a5a7-e305cc822f40/scratchpad/verify11/probe_sc2.py`: 12 of 13 checks passed.
  - Every failure was classified. They are my probe's wrong assumptions or pre-existing behaviour outside LRAG text; none is a Phase 11 defect (see "Probe failures classified").
- The repo was left clean: `git status` shows only the pre-existing untracked entries. The operator corpus `v1/.corpus_working_dir` listing was identical before and after, and the `v1/` directory listing was unchanged.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

Line numbers below are as of HEAD on 2026-11-01 (`seam/engine.py` grew through Phases 12-16 and the audit fixes; the symbols are unchanged).

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | A doc ingested via POST /documents (default selector) is retrievable by /query and resolvable by /evidence/resolve; after DELETE it is gone from both; two store roots never see each other; eval ingest never writes the operator corpus | VERIFIED | Probe: ingest 200 enqueued 1 -> /query evidence `sc1doc-chunk-000` -> resolve content holds the ingested token -> DELETE `success` -> /query evidence empty -> resolve 404 `UnresolvableEvidenceReferenceError` -> /corpus empty -> second delete is a normal `not_found`. Store root B: /corpus empty, /query refused `EmptyNamespaceError` (422), `B/wsp` never created. Operator corpus listing unchanged. Tests: `tests/seam/test_lightrag_corpus_path.py` (ingest/delete, parity rows survive), `test_lightrag_working_dir.py`, `tests/parts_core/lightrag/test_v1_index_sync.py`, `tests/eval/test_lightrag_eval_store.py`. Code: `seam/engine.py:1240` (`_v1_working_dir`), `foreign/v1_corpus_adapter.py:187-193` |
| SC2 | Uploads index their own bytes; unsupported types refused by name; re-ingest reports what v1 enqueued; inbox per workspace and never outlives its job; concurrent writes serialized or refused | VERIFIED | Probe: two `.txt` uploads (`upa`, `upb`) -> both `processed`, no `dup-*` rows, each retrievable by its own token and neither chunk holds the other's text. `.xyz`, no-suffix and `.exe` -> 422 `UnsupportedUploadTypeError`. Inbox empty after success and after refusal. `.md` upload then DELETE: gone from query, resolve, /corpus and inbox. Concurrency probe: while a slow ingest held the dir, a second ingest got **409 `StoreBusyError(store_kind=corpus)`** and the first finished 200. Code: `seam/corpus.py:71,356,375`, `seam/engine.py:1261,1433,1609,1636`, `seam/engine.py:869-878`, driver `v1_corpus_driver_script.py:325`. Tests: `test_upload_suffixes.py`, `test_lightrag_inbox.py`, `test_corpus_write_gate.py`, `test_lightrag_corpus_path.py` (redo, same-bytes-new-id, two-suffix, held-id) |
| SC3 | v1 failures are readable and safe: missing config names keys (never values); a timed-out ingest is visible as stuck/interrupted with a retry action; failures are named refusals with no raw stderr | VERIFIED | Probe with `EMBEDDING_DIM` and `EMBEDDING_MODEL` blanked: GET /corpus -> **503** `ForeignEngineRefusalError`, `failure_class V1NotConfigured`, `missing_keys` = both names, no stub value or key in the body; /health `degraded` with `engine_reason` naming the keys. Retry route: processed doc -> 422 `DocumentNotInterruptedError`; unknown doc -> 422 `UnknownDocumentError`. Interrupted status: `engine.py:766-779,2008,2039`. Retry: `engine.py:1701-1760`, `rest.py:515-520`, `mcp/server.py:251-261`. Tests: `test_v1_not_configured.py`, `test_interrupted_documents.py`, `test_retry_tool.py`, `test_v1_corpus_adapter.py`, `test_v1_driver_protocol.py`, `test_corpus_adapter_failures.py` |
| SC4 | GET /health writes nothing; reports only what it checked; covers HippoRAG namespaces; not ok without model clients or on an empty root; degraded (not 500) when a store fails | VERIFIED | Probe on an empty root: 3 health calls changed nothing, and no `<ws>/`, `lightrag-v1`, `jobs.db`, `text_chunks` or `graph.cozo` exists. Status `degraded`, all 10 stores `absent` including `kv:hipporag-text-chunks`, `graph:hipporag-graph`, `vector:hipporag-*`. App without clients: `degraded`, wrote nothing. Code: `engine.py:425-437` (probe list), `engine.py:2044-2129`. Tests: `test_health_honesty.py` (6), `test_status_during_write.py` (2), `test_health_probe.py`. Note: the engine constructor creates `trace.db` at the store root (Phase 4 `seam/trace_store.py:58`); this is construction, not health, and LRAG-13 does not list it |
| SC5 | Hybrid/local/global use v1 kg_query context, prompts, ordering, selection; no no-op embedder-index in query traces; unpopulated namespace distinguishable; write spend metered; section 8 numbering; entity ops removed | VERIFIED | `generate.py` sends `PROMPTS["rag_response"]` / `naive_rag_response` as the system message with the query as the user message. `assemble.py:3,104-119` fills `kg_query_context` from budgeted entities and relations plus chunks, with a `max_total_tokens` cap. Prompts are byte-diffed against `v1/lightrag/prompt.py`. `without_recipe_only_nodes` is applied at `engine.py:2554`. `EmptyNamespaceError` is raised before any model call (`engine.py:454-469,2569`; probe: 422, `store_kind` only). Entity ops: `v1_corpus_driver_script.py:22` says `entities`/`entity_info` exit with `UnknownOpError`; stub clean. Tests: `test_kg_fidelity.py` (14), `test_kg_retrieval_fidelity.py` (11), `test_v1_prompt_drift.py` (3), `test_query_trace_nodes.py` (8; includes a real-ingest trace with no recipe node), `test_empty_namespace.py` (7) |

**Score:** 5/5 truths verified; 0 behavior-unverified.

### Requirements Coverage

| Req | Code (file:line) | Proving test (all green) | Status |
|-----|------------------|--------------------------|--------|
| LRAG-01 per-workspace v1 dir | `engine.py:1240` (`_v1_working_dir`), `1463,1726,1809` (`_stamp_v1_working_dir`, defined at `796`); adapter has no default dir (`v1_corpus_adapter.py:187-193`; `DEFAULT_V1_WORKING_DIR` no longer in `foreign/`) | `test_lightrag_working_dir.py` (4); probe store root B isolation | SATISFIED |
| LRAG-02 ingest -> query -> resolve -> delete -> gone | `corpus-ingest.json`/`corpus-delete.json` second node `lightrag/v1-index-sync@0.1.0`; `v1_index_sync.py`; `full_delete.py` no phantom touches | `test_lightrag_corpus_path.py` (9), `test_v1_index_sync.py` (7), `test_delete_document.py`; probe SC1 | SATISFIED |
| LRAG-03 mutates_store plus MACH-11 events | `corpus-ingest.json:7-21`, `corpus-delete.json:7-21` (`mutates_store`); recorder at `engine.py:1623-1629,1869-1876` | `test_lightrag_ingest_mach11.py`; probe shows `seam_events` with the sync component | SATISFIED |
| LRAG-04 serialized writes | `engine.py:869-878` (`_write_gate`), `1551,1834` | `test_corpus_write_gate.py` (9); probe 409 | SATISFIED |
| LRAG-05 adapter faults, stale docstrings | `v1_corpus_adapter.py:87` (`stderr[-2000:]`), `:120` (named non-JSON refusal); driver `v1_corpus_driver_script.py:401` limit/offset check | `test_v1_corpus_adapter.py`, `test_v1_driver_protocol.py` (17), `test_corpus_adapter_failures.py`, `test_error_message_scrub.py` | SATISFIED. A-WR-05 partial acceptance noted below |
| LRAG-06 v1 not configured | `v1_corpus_adapter.py:93` (`V1NotConfiguredError`), driver `:155,429`, `engine.py:2090-2092` | `test_v1_not_configured.py` (7); probe 503 plus keys, no values | SATISFIED |
| LRAG-07 interrupted state and retry | `engine.py:766-779,2008,2039`; `retry_document` at `1701-1760`; `rest.py:515`; `mcp/server.py:251-261` | `test_interrupted_documents.py` (3), `test_retry_tool.py` (2); probe retry refusals | SATISFIED. Retry-from-`parsing` is a human item |
| LRAG-08 upload indexes real bytes | `seam/corpus.py:71,356,375` (`upload_suffix`, `generated_on_disk_name`); `engine.py:1433`; driver file-ingest path | `test_lightrag_corpus_path.py` -k upload, `test_upload_suffixes.py` (17); probe 2 uploads plus 422 | SATISFIED |
| LRAG-09 inbox per workspace, cleaned | `engine.py:1261` (`_inbox`), `1609`, `1636`, `396` (`_remove_staged`) | `test_lightrag_inbox.py` (10); probe inbox empty after success, refusal and delete | SATISFIED |
| LRAG-10 enqueued truth | driver `v1_corpus_driver_script.py:325`; `engine.py:1481-1502` (`_held_by_v1`), `781` (`_v1_row_track_id`, now read via `asyncio.to_thread` under the gate) | `test_lightrag_corpus_path.py` redo, same-bytes, u3, held-id (5); `test_held_by_v1_offloop.py` | SATISFIED |
| LRAG-11 metering | driver `token_tracker=` (`:197-224`); `full_ingest.py:65-88,304-309`; `calls_llm` in both corpus wirings | `test_corpus_metering.py` (9) | SATISFIED (stub usage only; real provider is a human item) |
| LRAG-12 section 8 numbering | `full_ingest.py:14,173-190` | `test_full_ingest_compat.py` (11) | SATISFIED |
| LRAG-13 health writes nothing | `engine.py:2044-2129`; driver health op builds no facade; `stores/probes.py:43-63` (`probe_kv` opens `mode=ro` only when `-wal` and `-shm` both already exist, so it creates no file) | `test_health_honesty.py`; probe | SATISFIED |
| LRAG-14 health honesty | `engine.py:425-437,2090-2092`; `v1_reachable`, `engine_reason` | `test_health_honesty.py` (6), `test_health_probe.py`; probe | SATISFIED |
| LRAG-15 eval store | `eval/corpus_ingest.py:71`; `aa_run.py` `--arm` | `test_lightrag_eval_store.py` (7), `test_corpus_ingest.py`, `test_aa_run.py`; probe shows operator corpus untouched | SATISFIED |
| LRAG-16 empty namespace | `engine.py:454-469,2569`; `stores/vector.py:713` (`select` opens without creating) | `test_empty_namespace.py` (7); probe 422 | SATISFIED |
| LRAG-17 v1 answer fidelity | `generate.py` (system template), `assemble.py:3,104-154`, `prompts.py:18,72`, `engine.py:606,2553` (`_inject_max_total_tokens`) | `test_kg_fidelity.py` (14), `test_v1_prompt_drift.py` (3) | SATISFIED. `len//4` tokenizer is a marked `shortcut:` (`assemble.py:48`) |
| LRAG-18 retrieval ordering and selection | `keywords.py`, `entity_lookup.py`, `relation_lookup.py`, `entity_hydrate_expand.py`, `chunk_sel_kg.py`, `join_roundrobin.py` | `test_kg_retrieval_fidelity.py` (11) | SATISFIED. B-WR-06 (`chunk_top_k` 10 vs v1 20) is a marked `shortcut:` (`chunk_vector.py:17`) |
| LRAG-19 no recipe node in query traces | `engine.py:451,2554`; `wirings/resolve.py` `without_recipe_only_nodes`; `base.json` keeps the recipe node | `test_query_trace_nodes.py` (8), `test_arm_conformance.py` (9) | SATISFIED |
| LRAG-20 entity ops removed | driver `:22`; stub clean; `COVERAGE.md` rows removed | `test_full_ingest_compat.py`, `test_delete_document.py` | SATISFIED |

### Anti-patterns and debt markers

- The `shortcut:` markers are all with an upgrade path: `assemble.py:45`, `truncator_token_budget.py:69`, `chunk_vector.py:17`, `v1_index_sync.py:86`.
- No `TBD`, `FIXME` or `XXX` in the phase's modified source files.
- Review dispositions confirmed: every Critical and Warning is fixed except B-WR-06 (deferred, marked) and A-WR-05 (accepted partial).

### Probe failures classified (none is a Phase 11 defect)

| Probe check | Cause |
|-------------|-------|
| `SC4 health ... no files` (x2) | The probe compared the tree to `[]` after constructing the app. `trace.db*` exists from the engine constructor (Phase 4 `TraceStore`). The before/after delta around `GET /health` is empty (probe_sc2). |
| `SC2 upa/upb ... own id` (x2) | The probe assumed `full_doc_id` equals the caller's id. Before 8026d56 it was v1's `doc-<md5>` for uploads; the re-run now passes both checks. |
| `LRAG-16 read path created no store dirs` | `_build_stores` opens the kv and graph stores before `_refuse_empty_namespaces`, so `text_chunks/kv.sqlite3` and `graph.cozo` appear on a refused query. No vector directory is created, which is what LRAG-16 and D-15 name. The kv/graph open-on-read is Phase 10 behaviour. |
| `retry on an unknown doc is 404` | Phase 11 D-08 asked only for a named refusal. It returns 422 `UnknownDocumentError`. SEAM-04's 404 list covers the four lookups, not this route. |

## Re-verification 2026-10-31 (stale refresh)

Diff `4cf4dc0..HEAD` over the moved files was read, then the targeted Phase 11 tests were re-run from `databasise/` (no `-m live`, no full suite):

- **Moved-file review.** `v1_corpus_adapter.py`: one added redaction pattern (`?key=`/`&key=`) and a docstring edit; `stderr[-2000:]`, `V1NotConfiguredError` and the named non-JSON refusal are untouched. `assemble.py`: adds an `items` list (the evidence a KG arm returns); the budgeted entity/relation/chunk assembly and the `max_total_tokens` cap are untouched. `chunk_sel_kg.py`, `chunk_vector.py`, `entity_lookup.py`, `relation_lookup.py`: only `reads_namespaces` declarations added. `wirings/lightrag/base.json`: only the no-op `apportionment_policy` config keys removed (no part in `parts_core/lightrag` reads that key). `stores/vector.py`: adds `list_ids` and the `ids=` path of `self_knn`; the `select()` open-without-create behaviour (LRAG-16) is untouched. `wirings/resolve.py`: `without_recipe_only_nodes` now keeps the ancestors of `provides`; LightRAG's `provides` is `["generate"]` and `embedder-index` has `deps: []` and no dependent, so it is still dropped from every query run (LRAG-19). `seam/engine.py` still carries `_stamp_v1_working_dir`, `_write_gate` / `StoreBusyError(store_kind="corpus")`, `_remove_staged`, `_refuse_empty_namespaces` (run on the recipe-stripped copy before dispatch), `retry_document`, `_held_by_v1` and `_inject_max_total_tokens`. REST `POST /documents/{id}/retry` and the MCP `retry` tool still reach the same engine method. The `/corpus` selector added in Phase 12 defaults to the LightRAG corpus.
- **Tests, all green, 0 failed.**
  - 18 seam files (corpus path, working dir, upload suffixes, inbox, write gate, interrupted documents, health honesty and probe, status during write, empty namespace, query trace nodes, MACH-11, delete, adapter failures, error scrub, file name, corpus status, REST corpus endpoints): **195 passed**.
  - Foreign (adapter, driver protocol, not-configured), eval (eval store, corpus ingest, aa_run, store boundary), all of `parts_core/lightrag` (includes `test_kg_fidelity`, `test_kg_retrieval_fidelity`, `test_v1_prompt_drift`, `test_corpus_metering`, `test_full_ingest_compat`, `test_v1_index_sync`) and parity (arm conformance, import verification, naive end to end, v1 driver script): **268 passed, 1 deselected**.
  - MCP `test_retry_tool.py` and seam `test_hipporag_corpus_surface.py`: **7 passed**.
- **Debt markers.** No `TBD`, `FIXME` or `XXX` in any covered source file. The four `shortcut:` markers (`assemble.py:48`, `truncator_token_budget.py:68`, `chunk_vector.py:17`, `v1_index_sync.py:86`) remain, each with an upgrade path.
- **Not repeated.** The two hermetic loopback probes (`probe_sc.py`, `probe_sc2.py`) of the earlier report were not re-run; the tests above cover the same truths. Human items 1-5 below keep their earlier owner decisions.
- **Requirement IDs.** LRAG-01..20 all appear in REQUIREMENTS.md (lines 185-257; traceability rows 880-899, all `Complete`, mapped to Phase 11). No orphaned Phase 11 requirement.

### Re-verification 2026-11-01 (audit fixes)

Trigger: the 2026-10-31 report went stale when the debugging and security battery (commits `3aafcc62..HEAD`, 2026-10-31 20:25 to 2026-11-01 00:18 PDT) changed five covered files. Diff `3aafcc62 HEAD` over those files was read in full; the goal still holds and the status stays `passed`.

- **What changed, per file, and the Phase 11 truth it touches.**
  - `seam/corpus.py` (aa7a77d9, 5aec6294, 7a07da50): the document id token is now `[A-Za-z0-9_-]{1,251}` (`MAX_DOCUMENT_ID_CHARS = 255 - len(".bin")`) and `generated_on_disk_name` also refuses an id whose length plus the accepted suffix exceeds 255 bytes, so a raw upload can never fail at the `open` with `ENAMETOOLONG`; the refusal is still the named `InvalidDocumentIdError` (422), now with a bounded echo. `IngestDocument.text` is checked with `require_encodable` before the byte count (a lone surrogate is `NonEncodableTextError`, 422, not an encoder 500). `Page`/`checked_page` cap `offset` at `2**31-1` (`PageBoundsError`, same class as before). The staging contract (LRAG-08/09) is unchanged: the name is still `document_id + suffix`, built only from the validated id and the `upload_suffix` result.
  - `seam/engine.py` (62d7ba91 and the Phase 09/16 input-bound fixes): `_held_by_v1` now reads v1's doc-status track id with `await asyncio.to_thread(_v1_row_track_id, ...)` instead of a blocking read on the loop thread. It is still the `precheck` awaited at `engine.py:1552`, after `_build_stores` and after `_write_gate` is entered at `1551`, so the read is still under the gate and `enqueued: 0` under the held row's id (LRAG-10) is unchanged. The other engine edits are outside the LightRAG corpus path: `CanonicalisationError` -> `NonEncodableTextError` before dispatch, `require_encodable` on ledger aliases/versions/trace references, `OverflowError` folded into the `StoreFault` fault on paged reads, and `GET /log`'s limit check. `health()`, `_HEALTH_PROBES`, `_PROBES`, `_refuse_empty_namespaces`, `retry_document`, `_remove_staged`, `_stamp_v1_working_dir` and `_inject_max_total_tokens` are byte-identical apart from line shifts.
  - `seam/refusals.py` (13fda6a6, beec7c30, 00118d1e, 7a07da50): `_finite` became `json_safe` (also escapes lone surrogates); new `bounded_echo` (200 chars / 20 items) is applied in the constructors of every refusal that echoes a caller value, including the Phase 11 ones (`InvalidDocumentIdError`, `DuplicateDocumentIdError`, `UnknownDocumentError`, `DocumentNotInterruptedError`, `UnknownJobError`, `UnresolvableEvidenceReferenceError`). Class names, attribute names and the message prefixes the tests pin are unchanged; `PageBoundsError` keeps `non-negative` in its text. New `NonEncodableTextError` and `require_encodable` are exported. The new `shortcut:` marker at `refusals.py:72` carries an upgrade path.
  - `seam/rest.py` (5c00aabc, 13fda6a6): the schema-error branch of `_validation_response` no longer calls FastAPI's default handler (which echoed the unbounded `input`); it emits `{detail: [{type, loc, msg}]}` through `bounded_echo` and `json_safe`. Still a 422; the refusal branch (named refusals unwrapped from `ctx.error`) is untouched, so `UnsupportedUploadTypeError`, `InvalidDocumentIdError` and the other Phase 11 refusals keep their status codes and bodies. The retry route is at `rest.py:515-520`.
  - `parts_core/lightrag/full_ingest.py` (06d0eb09): `tokens_from_usage` treats a non-positive `total_tokens` or a negative `prompt_tokens`/`completion_tokens` as `unbudgetable` with the call count, the same rule as `clients/rerank.py`; a positive count is still `counted_by` v1 (LRAG-11). Section 8 numbering (LRAG-12) is untouched.
  - Not in the covered list but relevant to SC4: `stores/probes.py` (4bfdb8db) `probe_kv` opens plain `mode=ro` only when `kv.sqlite3-wal` and `kv.sqlite3-shm` both already exist (a live writer); otherwise `immutable=1` as before. Plain `mode=ro` creates a `-shm` only when it is missing, which that branch excludes, so health still writes nothing (LRAG-13), and a live writer's WAL checkpoint can no longer make a healthy store read as `corrupted` (LRAG-14). `stores/graph.py` (a895ef8a) only defers a refused Cozo client close with a warning.
- **Tests, all green, 0 failed** (from `databasise/`, `.venv/bin/python -m pytest ... -q -p no:cacheprovider`, no `-m live`, no full suite):
  - 22 seam files plus `tests/mcp/test_retry_tool.py` (raw upload staging, ingest file name, held-by-v1 off-loop, input bounds, surrogate inputs, upload suffixes, inbox, corpus path, working dir, write gate, interrupted documents, health honesty, health probe, status during write, empty namespace, query trace nodes, MACH-11, delete, adapter failures, error scrub, corpus status, REST corpus endpoints): **238 passed**. `test_raw_upload_staging.py` and `test_ingest_file_name.py` pass against the new id cap.
  - All of `tests/parts_core/lightrag` and `tests/foreign`, eval (eval store, corpus ingest, aa_run) and parity (arm conformance, import verification, naive end to end, v1 driver script): **287 passed, 1 deselected**.
  - `tests/stores/test_probe_kv_live_writer.py`: **1 passed**.
- **Debt markers.** No `TBD`, `FIXME` or `XXX` in the five moved files or `stores/probes.py`. `shortcut:` markers in covered code: `assemble.py:48`, `chunk_vector.py:17`, `v1_index_sync.py:86`, `refusals.py:72`, `engine.py:2501` (log tail, Phase 16), each with an upgrade path.
- **Regressions.** None found. Named refusals are still named, status codes are unchanged (422 for input refusals, 409 `StoreBusyError`, 503 `ForeignEngineRefusalError`, 404 `UnresolvableEvidenceReferenceError`), no new unvalidated path was added (every new check is a refusal before a store or sqlite touch), and the store lifecycle truths (per-workspace v1 dir, inbox removed after the run, write gate held through commit) hold.
- **Not repeated.** The hermetic loopback probes were not re-run; the human items keep their earlier owner decisions. The fingerprint covers the same file list as the 2026-10-31 report.

## Human verification resolved

Source: `.planning/phases/11-lightrag-corpus-path/11-UAT.md` (status complete: 1 pass, 1 issue now fixed, 2 skipped, 1 routed).

| # | Item | Owner decision | Verifier check |
|---|------|----------------|----------------|
| 1 | Re-ingest of a held id runs a full-corpus mirror (A3-WR-01) | Accepted; stays a marked `shortcut:` at `parts_core/lightrag/v1_index_sync.py:86` | Marker present |
| 2 | Live ingest/delete record real token counts (LRAG-11) | Deferred to `.planning/TESTING-PLAN.md` section 2 ("Live LightRAG write metering") | Hermetic metering tests pass (`test_corpus_metering.py`) |
| 3 | Uploaded file evidence shows the caller's document_id | Fixed in the sync by 8026d56 | Verified, see below |
| 4 | A-WR-05 in-process HippoRAG provider errors unredacted in the server log | Routed to Phase 12 (needs grant-check-edit on `test_foreign_engine_refusal.py`) | Out of Phase 11 scope (LRAG-05 concerns v1 stderr) |
| 5 | Retry of a raw upload stuck mid-parse (LRAG-07) | Deferred to `.planning/TESTING-PLAN.md` section 2 | Hermetic retry tests pass |

### UAT-3 fix re-verification (8026d56)

- `read_v1_snapshot(..., caller_doc_ids=False)` defaults off. The only caller passing `True` is `v1_index_sync.py:93`. `parity/import_index.py` `import_v1_index` and the parity readers do not pass it, so the parity import path is unchanged: `tests/parity/test_import_verification.py` and `test_naive_arm_end_to_end.py` pass.
- Tests: `test_uat3_an_uploaded_file_resolves_to_the_callers_document_id_and_a_delete_removes_it` passes alone. The set `test_lightrag_corpus_path.py`, `test_v1_index_sync.py`, `test_import_verification.py`, `test_naive_arm_end_to_end.py`, `test_lightrag_working_dir.py` and `test_delete_document.py`: **60 passed, 1 deselected, 0 failed**.
- Re-run of `probe_sc.py`: 33 of 36. Both SC2 "own id" checks now pass (the resolved `full_doc_id` is the caller's id). The 3 remaining failures are the previously classified probe artifacts (`trace.db` from the engine constructor, twice, and kv/graph opened on a refused query in Phase 10 code).
- Coordinator-reported full offline gate on HEAD: 2083 passed, both pytest styles (not re-run by me).

## Gaps

None. No truth failed, and no blocker was found.

## Advisory (not blocking, not scored)

1. Upload evidence ids: fixed by 8026d56 (see below).
2. A refused empty-namespace query still opens (and so creates) the kv and graph stores on a fresh root. Minimal fix if wanted: call `_refuse_empty_namespaces` before `_build_stores` in `_execute_resolved`, but this changes the STOR-02 error precedence the code comment describes, so it needs a deliberate choice.
3. The review info items (A-IN-01..05, B-IN-01..06) remain open and advisory.
4. `deferred-items.md`: the F-07 report prose still says two mutable-store components (the table lists three).
5. Known context, not gaps: the open LRAG ledger rows with empty test refs, undecided seam auth, node ids in `stop_reason` (Phase 13).
6. `stores/probes.py` is load-bearing for SC4/LRAG-13/14 but is not in this report's `covered_files` (the list was kept identical to the 2026-10-31 report); a future change to `probe_kv` will not trip this report stale.

---

_Verified: 2026-11-01_
_Verifier: Claude (gsd-verifier)_
