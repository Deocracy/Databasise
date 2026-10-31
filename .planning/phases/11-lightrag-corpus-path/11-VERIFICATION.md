---
phase: 11-lightrag-corpus-path
verified: 2026-10-31T00:00:00Z
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
covered_digest: "v3:sha256:3daa8300b745aa07bfd7ef0513c228ace99f4021c921f600a302d935650abd22"
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
**Verified:** 2026-10-31
**Status:** passed (no failed truth, no blocker; all five human items resolved, deferred or routed by the owner, see below)
**Re-verification:** Yes. Stale-report refresh: 14 covered files moved after the 2026-10-19 report (Phases 12-16 touched `seam/engine.py`, `seam/rest.py`, `seam/refusals.py`, `mcp/server.py`, `mcp/tools.py`, `eval/aa_run.py`, `parity/import_index.py`, `stores/vector.py`, `wirings/resolve.py`, `wirings/lightrag/base.json`, and four lightrag parts). The must-haves are unchanged; they were re-checked against the current code.

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

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| SC1 | A doc ingested via POST /documents (default selector) is retrievable by /query and resolvable by /evidence/resolve; after DELETE it is gone from both; two store roots never see each other; eval ingest never writes the operator corpus | VERIFIED | Probe: ingest 200 enqueued 1 -> /query evidence `sc1doc-chunk-000` -> resolve content holds the ingested token -> DELETE `success` -> /query evidence empty -> resolve 404 `UnresolvableEvidenceReferenceError` -> /corpus empty -> second delete is a normal `not_found`. Store root B: /corpus empty, /query refused `EmptyNamespaceError` (422), `B/wsp` never created. Operator corpus listing unchanged. Tests: `tests/seam/test_lightrag_corpus_path.py` (ingest/delete, parity rows survive), `test_lightrag_working_dir.py`, `tests/parts_core/lightrag/test_v1_index_sync.py`, `tests/eval/test_lightrag_eval_store.py`. Code: `seam/engine.py:1007-1010`, `foreign/v1_corpus_adapter.py:173-198` |
| SC2 | Uploads index their own bytes; unsupported types refused by name; re-ingest reports what v1 enqueued; inbox per workspace and never outlives its job; concurrent writes serialized or refused | VERIFIED | Probe: two `.txt` uploads (`upa`, `upb`) -> both `processed`, no `dup-*` rows, each retrievable by its own token and neither chunk holds the other's text. `.xyz`, no-suffix and `.exe` -> 422 `UnsupportedUploadTypeError`. Inbox empty after success and after refusal. `.md` upload then DELETE: gone from query, resolve, /corpus and inbox. Concurrency probe: while a slow ingest held the dir, a second ingest got **409 `StoreBusyError(store_kind=corpus)`** and the first finished 200. Code: `seam/corpus.py:76,358`, `seam/engine.py:1200-1216,1316-1330,1392-1393,1446-1457`, `seam/engine.py:708-722`, driver `v1_corpus_driver_script.py:325`. Tests: `test_upload_suffixes.py`, `test_lightrag_inbox.py`, `test_corpus_write_gate.py`, `test_lightrag_corpus_path.py` (redo, same-bytes-new-id, two-suffix, held-id) |
| SC3 | v1 failures are readable and safe: missing config names keys (never values); a timed-out ingest is visible as stuck/interrupted with a retry action; failures are named refusals with no raw stderr | VERIFIED | Probe with `EMBEDDING_DIM` and `EMBEDDING_MODEL` blanked: GET /corpus -> **503** `ForeignEngineRefusalError`, `failure_class V1NotConfigured`, `missing_keys` = both names, no stub value or key in the body; /health `degraded` with `engine_reason` naming the keys. Retry route: processed doc -> 422 `DocumentNotInterruptedError`; unknown doc -> 422 `UnknownDocumentError`. Interrupted status: `engine.py:611,1706-1711`. Retry: `engine.py:1459-1515`, `rest.py:485`, `mcp/server.py:232`. Tests: `test_v1_not_configured.py`, `test_interrupted_documents.py`, `test_retry_tool.py`, `test_v1_corpus_adapter.py`, `test_v1_driver_protocol.py`, `test_corpus_adapter_failures.py` |
| SC4 | GET /health writes nothing; reports only what it checked; covers HippoRAG namespaces; not ok without model clients or on an empty root; degraded (not 500) when a store fails | VERIFIED | Probe on an empty root: 3 health calls changed nothing, and no `<ws>/`, `lightrag-v1`, `jobs.db`, `text_chunks` or `graph.cozo` exists. Status `degraded`, all 10 stores `absent` including `kv:hipporag-text-chunks`, `graph:hipporag-graph`, `vector:hipporag-*`. App without clients: `degraded`, wrote nothing. Code: `engine.py:353-361` (probe list), `engine.py:1741-1811`. Tests: `test_health_honesty.py` (6), `test_status_during_write.py` (2), `test_health_probe.py`. Note: the engine constructor creates `trace.db` at the store root (Phase 4 `seam/trace_store.py:58`); this is construction, not health, and LRAG-13 does not list it |
| SC5 | Hybrid/local/global use v1 kg_query context, prompts, ordering, selection; no no-op embedder-index in query traces; unpopulated namespace distinguishable; write spend metered; section 8 numbering; entity ops removed | VERIFIED | `generate.py` sends `PROMPTS["rag_response"]` / `naive_rag_response` as the system message with the query as the user message. `assemble.py:3,104-119` fills `kg_query_context` from budgeted entities and relations plus chunks, with a `max_total_tokens` cap. Prompts are byte-diffed against `v1/lightrag/prompt.py`. `without_recipe_only_nodes` is applied at `engine.py:1843`. `EmptyNamespaceError` is raised before any model call (`engine.py:382,1858`; probe: 422, `store_kind` only). Entity ops: `v1_corpus_driver_script.py:22` says `entities`/`entity_info` exit with `UnknownOpError`; stub clean. Tests: `test_kg_fidelity.py` (14), `test_kg_retrieval_fidelity.py` (11), `test_v1_prompt_drift.py` (3), `test_query_trace_nodes.py` (8; includes a real-ingest trace with no recipe node), `test_empty_namespace.py` (7) |

**Score:** 5/5 truths verified; 0 behavior-unverified.

### Requirements Coverage

| Req | Code (file:line) | Proving test (all green) | Status |
|-----|------------------|--------------------------|--------|
| LRAG-01 per-workspace v1 dir | `engine.py:1007-1010`, `1225,1484,1564` (`_stamp_v1_working_dir`); adapter has no default dir (`v1_corpus_adapter.py:173-198`; `DEFAULT_V1_WORKING_DIR` no longer in `foreign/`) | `test_lightrag_working_dir.py` (4); probe store root B isolation | SATISFIED |
| LRAG-02 ingest -> query -> resolve -> delete -> gone | `corpus-ingest.json`/`corpus-delete.json` second node `lightrag/v1-index-sync@0.1.0`; `v1_index_sync.py`; `full_delete.py` no phantom touches | `test_lightrag_corpus_path.py` (9), `test_v1_index_sync.py` (7), `test_delete_document.py`; probe SC1 | SATISFIED |
| LRAG-03 mutates_store plus MACH-11 events | `corpus-ingest.json:7-21`, `corpus-delete.json:7-21` (`mutates_store`); recorder at `engine.py:1292-1295,1380` | `test_lightrag_ingest_mach11.py`; probe shows `seam_events` with the sync component | SATISFIED |
| LRAG-04 serialized writes | `engine.py:708-722` (`_write_gate`), `1307,1584` | `test_corpus_write_gate.py` (9); probe 409 | SATISFIED |
| LRAG-05 adapter faults, stale docstrings | `v1_corpus_adapter.py:87` (`stderr[-2000:]`), `:120` (named non-JSON refusal); driver `v1_corpus_driver_script.py:401` limit/offset check | `test_v1_corpus_adapter.py`, `test_v1_driver_protocol.py` (17), `test_corpus_adapter_failures.py`, `test_error_message_scrub.py` | SATISFIED. A-WR-05 partial acceptance noted below |
| LRAG-06 v1 not configured | `v1_corpus_adapter.py:91-96` (`V1NotConfiguredError`), driver `:155,429`, `engine.py:1786-1790` | `test_v1_not_configured.py` (7); probe 503 plus keys, no values | SATISFIED |
| LRAG-07 interrupted state and retry | `engine.py:611-618,1706-1711`; `retry_document` at `1459-1515`; `rest.py:485`; `mcp/server.py:232` | `test_interrupted_documents.py` (3), `test_retry_tool.py` (2); probe retry refusals | SATISFIED. Retry-from-`parsing` is a human item |
| LRAG-08 upload indexes real bytes | `seam/corpus.py:76,358` (`upload_suffix`); `engine.py:1200,1212-1217`; driver file-ingest path | `test_lightrag_corpus_path.py` -k upload, `test_upload_suffixes.py` (17); probe 2 uploads plus 422 | SATISFIED |
| LRAG-09 inbox per workspace, cleaned | `engine.py:1023-1026`, `1392-1395`, `1446-1457`, `328` (`_remove_staged`) | `test_lightrag_inbox.py` (10); probe inbox empty after success, refusal and delete | SATISFIED |
| LRAG-10 enqueued truth | driver `v1_corpus_driver_script.py:325`; `engine.py:1243-1263` (`_held_by_v1`) | `test_lightrag_corpus_path.py` redo, same-bytes, u3, held-id (5) | SATISFIED |
| LRAG-11 metering | driver `token_tracker=` (`:185-215`); `full_ingest.py:65-83,301-306`; `calls_llm` in both corpus wirings | `test_corpus_metering.py` (9) | SATISFIED (stub usage only; real provider is a human item) |
| LRAG-12 section 8 numbering | `full_ingest.py:14,170-187` | `test_full_ingest_compat.py` (11) | SATISFIED |
| LRAG-13 health writes nothing | `engine.py:1754-1811`; driver health op builds no facade | `test_health_honesty.py`; probe | SATISFIED |
| LRAG-14 health honesty | `engine.py:353-361,1798-1804`; `v1_reachable`, `engine_reason` | `test_health_honesty.py` (6), `test_health_probe.py`; probe | SATISFIED |
| LRAG-15 eval store | `eval/corpus_ingest.py:71`; `aa_run.py` `--arm` | `test_lightrag_eval_store.py` (7), `test_corpus_ingest.py`, `test_aa_run.py`; probe shows operator corpus untouched | SATISFIED |
| LRAG-16 empty namespace | `engine.py:382,1858`; `stores/vector.py:713` (`select` opens without creating) | `test_empty_namespace.py` (7); probe 422 | SATISFIED |
| LRAG-17 v1 answer fidelity | `generate.py` (system template), `assemble.py:3,104-154`, `prompts.py:18,72`, `engine.py` `max_total_tokens` injection | `test_kg_fidelity.py` (14), `test_v1_prompt_drift.py` (3) | SATISFIED. `len//4` tokenizer is a marked `shortcut:` (`assemble.py:45`) |
| LRAG-18 retrieval ordering and selection | `keywords.py`, `entity_lookup.py`, `relation_lookup.py`, `entity_hydrate_expand.py`, `chunk_sel_kg.py`, `join_roundrobin.py` | `test_kg_retrieval_fidelity.py` (11) | SATISFIED. B-WR-06 (`chunk_top_k` 10 vs v1 20) is a marked `shortcut:` (`chunk_vector.py:17`) |
| LRAG-19 no recipe node in query traces | `engine.py:377-379,1843`; `wirings/resolve.py` `without_recipe_only_nodes`; `base.json` keeps the recipe node | `test_query_trace_nodes.py` (8), `test_arm_conformance.py` (9) | SATISFIED |
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

---

_Verified: 2026-10-31_
_Verifier: Claude (gsd-verifier)_
