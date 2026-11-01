---
phase: 11-lightrag-corpus-path
plan: 01
subsystem: api
tags: [lightrag, v1-subprocess, faiss, cozo, sqlite, mach-11, opaque-part]

requires:
  - phase: 10
    provides: prepare-all/commit-all (D-07) and drop-on-failure (D-06) over the staged kv/vector/graph stores
provides:
  - lightrag/v1-index-sync@0.1.0 opaque part (second node of corpus-ingest.json and corpus-delete.json)
  - parity/import_index.py readers split from writers (V1Snapshot, read_v1_snapshot, mirror_snapshot)
  - per-workspace v1 working dir <store_root>/<workspace>/lightrag-v1 on every corpus op (no adapter default)
  - IngestJob.seam_events and the MACH-11 recorder on engine.ingest
  - hermetic real-driver harness databasise/tests/fixtures/v1_stub_server.py (StubModelServer, write_env_overlay, real_v1, requires_v1)
affects: [11-02, 11-03, 11-05, 11-06, 11-08, 11-09, SEAM-15, TOOL-02, TOOL-11, LIVE-05]

actuals:
  tokens: 16900
  tasks: 2
  commits: 3
plan_head_before: 23c0ca0d5cb5dc77eaa4ff9b9ad8dd6fd3b13b59
plan_head_after: 19c6bb33ccc93986b6ecba7b9a7d9bb9ba10b2ad

tech-stack:
  added: []
  patterns:
    - "v1 then mirror: v1's subprocess commits its own dir, an in-process opaque part mirrors it into staged v2 stores"
    - "manifest-based prune: delete only ids the previous sync wrote, never a set difference over the whole namespace"
    - "hermetic real-driver tests: loopback OpenAI-compatible stub server plus a temp env overlay patched into DEFAULT_V1_ENV_PARITY"

key-files:
  created:
    - databasise/parts_core/lightrag/v1_index_sync.py
    - databasise/tests/fixtures/v1_stub_server.py
    - databasise/tests/seam/test_lightrag_corpus_path.py
    - databasise/tests/seam/test_lightrag_ingest_mach11.py
    - databasise/tests/parts_core/lightrag/test_v1_index_sync.py
  modified:
    - databasise/parity/import_index.py
    - databasise/foreign/v1_corpus_adapter.py
    - databasise/seam/engine.py
    - databasise/seam/corpus.py
    - databasise/parts_core/declared_only.py
    - databasise/parts_core/lightrag/full_ingest.py
    - databasise/parts_core/lightrag/full_delete.py
    - databasise/wirings/lightrag/corpus-ingest.json
    - databasise/wirings/lightrag/corpus-delete.json
    - databasise/tests/seam/test_delete_document.py
    - databasise/evidence/f07_report.py
    - databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md
    - databasise/tests/parts/test_registry.py

key-decisions:
  - "D-01 prune uses a mirror manifest (kv record lightrag-v1-index-sync-manifest in text_chunks) so parity-imported rows are never deleted"
  - "The v1 working dir is <store_root>/<workspace>/lightrag-v1; run_corpus_op has no default and omits working_dir from the job when none is passed, so the real driver fails rather than reaching v1/.corpus_working_dir"
  - "IngestJob gains seam_events (LRAG-03 test needs events on the returned job; ingest persists no trace)"
  - "Only LRAG-02 is marked complete: LRAG-01 is also owned by 11-02/11-06 (isolation proof) and LRAG-03 by 11-03 (full-ingest effects/admission half)"

patterns-established:
  - "A store-writing opaque part runs in the engine process at the subprocess placement, writes only through ctx.stores and bounds itself with asyncio.wait_for"
  - "A no-op corpus part touches no ctx.stores key, so MACH-11 records nothing and stub-body corpus tests stay unchanged"

requirements-completed: [LRAG-02]

coverage:
  - id: D1
    description: "A text document ingested through the real v1 driver lands in <store_root>/<ws>/lightrag-v1, is mirrored into v2, answers a naive query and resolves to full_doc_id lragdoc1; v1/.corpus_working_dir is untouched"
    requirement: "LRAG-02"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_lightrag_corpus_path.py#test_an_ingested_document_is_what_the_naive_arm_retrieves_and_resolves"
        status: pass
    human_judgment: false
  - id: D2
    description: "After REST DELETE returns success, /query no longer returns the document's ref and /evidence/resolve on it is refused"
    requirement: "LRAG-02"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_lightrag_corpus_path.py#test_a_deleted_document_leaves_the_query_stores_and_its_ref_is_refused"
        status: pass
    human_judgment: false
  - id: D3
    description: "PROCESSED-only snapshot filter, no-op on absent dir, fail-closed on corrupt doc_status with nothing committed, manifest prune"
    verification:
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_v1_index_sync.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Parity-imported rows survive a seam ingest and delete in the same workspace"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_lightrag_corpus_path.py#test_parity_imported_rows_survive_seam_writes_in_the_same_workspace"
        status: pass
    human_judgment: false
  - id: D5
    description: "Ingest and delete each return one MACH-11 event from lightrag/v1-index-sync@0.1.0 with counted_by none; full-delete self-reports no touch"
    requirement: "LRAG-03"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_lightrag_ingest_mach11.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "D-05 hermetic shared-entity delete proof read from the v2 graph after the sync"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_delete_document.py#test_deleting_a_document_reduces_shared_entities_and_removes_orphan_only_ones"
        status: pass
    human_judgment: false

duration: 50min
completed: 2026-10-18
status: complete
---

# Phase 11 Plan 01: LightRAG Corpus Path Tracer Summary

**A seam ingest now runs v1 in a per-workspace dir and a new opaque `lightrag/v1-index-sync` part mirrors v1's PROCESSED rows into the staged v2 stores, so the naive arm retrieves and resolves the document, and a delete prunes it through a mirror manifest that never touches parity-imported rows.**

## Performance

- **Duration:** about 50 min (29 min to the Task 2 commit, then two offline-gate runs and one fix)
- **Started:** 2026-10-17T23:22:52-07:00 (plan_head_before commit)
- **Completed:** 2026-10-18 (gate fix commit `19c6bb3`)
- **Tasks:** 2/2
- **Files modified:** 18

## Accomplishments

- LRAG-02 end to end through the real v1 driver and pipeline against a loopback stub model server: ingest, naive query, evidence resolve, REST delete, refused resolve.
- `lightrag/v1-index-sync@0.1.0` with an 11-verdict §8 admission record, wired as the second node of both corpus wirings; it writes only through `ctx.stores`, so Phase 10's commit-all and drop-on-failure cover it.
- LRAG-01 plumbing: `DEFAULT_V1_WORKING_DIR` removed from the adapter; the engine stamps `<store_root>/<workspace>/lightrag-v1` onto every `lightrag/*` corpus node and passes it to the three status calls and health.
- LRAG-03 engine half: `engine.ingest` passes the MACH-11 recorder and returns `IngestJob.seam_events`; `full_delete_body` no longer self-reports touches.
- Hermetic harness reusable by later plans (LRAG-07/08/10/11 tests): `StubModelServer` with `omit_usage` and `delay_for`, `write_env_overlay(omit=, blank=)`.

## Task Commits

1. **Task 1: Tracer — ingest mirrored into v2 answers a naive query** - `7be6968` (feat)
2. **Task 2: Delete reaches the query stores, manifest prune, MACH-11 events from the sync** - `f4d9753` (feat)
3. **Gate fix: F-07 disposition row and registry count for the new part** - `19c6bb3` (fix)

## Test Evidence

Pre-change runs (each new test run first against the unchanged source):

- Task 1, `tests/seam/test_lightrag_corpus_path.py` before the engine/adapter change: FAILED with `ForeignEngineRefusalError: operation 'ingest' failed (CorpusOpSubprocessError)`; the captured stderr shows `CozoGraphStorage opened: .../v1/.corpus_working_dir/cozo_graph_chunk_entity_relation.db` and `Dimension mismatch: loaded Faiss index has dimension 4096, but embedding function expects dimension 8`. The ingest reached the repo-global operator corpus, which is the LRAG-01 defect. The plan expected "the query returns no evidence"; the real pre-change failure happens one step earlier.
- Task 1, `test_v1_index_sync.py` was written after the readers refactor had started, so its import of `read_v1_snapshot` would have failed on the old source; it was not run against the old source.
- Task 2, against Task 1's code: `4 failed, 28 passed`. Failures: the deleted ref `lragdoc1-chunk-000` still returned by `/query` (no delete sync); `'IngestJob' object has no attribute 'seam_events'`; `full-delete self-reported a 'graph' touch it never made`; `an orphan-only entity survived the deletion` (`UNIQonlya Corp` still in the v2 graph). The parity-survival test passed before the change (a regression guard for the prune that Task 2 added).

Passing runs:

- `pytest -q tests/seam/test_lightrag_corpus_path.py tests/parts_core/lightrag/test_v1_index_sync.py` (Task 1): `7 passed in 5.12s` (real-driver test ran, not skipped).
- `pytest -q tests/seam tests/parity tests/parts_core tests/stores tests/wirings` (Task 1): `1195 passed, 1 skipped, 3 deselected`. The skip was the old env-gated real-delete proof, replaced in Task 2.
- `pytest -q tests/seam/test_lightrag_corpus_path.py tests/seam/test_lightrag_ingest_mach11.py tests/parts_core/lightrag/test_v1_index_sync.py tests/seam/test_delete_document.py tests/seam/test_mach11_event.py` (Task 2): `32 passed in 27.70s`; with the prune unit test added, the sync file reports `7 passed`.
- `pytest -q tests/stores tests/seam tests/mcp tests/parity tests/runner tests/parts_core tests/wirings` (Task 2 and the plan's overall verification): `1402 passed, 3 deselected in 217.13s`, 0 skipped.
- Baseline before any change (same suites plus mcp and runner): `1389 passed, 1 skipped, 3 deselected`.
- Offline gate `.venv/bin/python tools/check_offline_suite.py`, first run after Task 2: exit 1, `4 failed, 1870 passed, 4 deselected` in both invocation styles (`tests/evidence/test_f07_record.py` x3, `tests/parts/test_registry.py::test_default_registry_holds_exactly_thirty_five_entries`). After `19c6bb3`: **exit 0**, `pytest -q -rs: 1874 passed, 4 deselected` and `python -m pytest -q -rs: 1874 passed, 4 deselected`.

## Files Created/Modified

- `databasise/parts_core/lightrag/v1_index_sync.py`: sync body (to_thread read, wait_for ceiling, manifest read/prune/write) and `LIGHTRAG_V1_INDEX_SYNC_ADMISSION`.
- `databasise/parity/import_index.py`: `V1Snapshot`, `read_v1_snapshot` (PROCESSED-only rule, Cozo opened `dataframe=False` and closed in `finally`), `mirror_snapshot` (upsert then manifest prune); `import_v1_index`, `_import_vector_kind`, `_import_text_chunks`, `_import_graph` keep their signatures and now use the shared readers.
- `databasise/foreign/v1_corpus_adapter.py`: no default working dir; `working_dir` enters the job only when passed.
- `databasise/seam/engine.py`: `_v1_working_dir()`, `_stamp_v1_working_dir`, `_corpus_op_or_refuse(..., working_dir)`, health passes it, ingest recorder and `seam_events`, D-01 residual-window docstring.
- `databasise/seam/corpus.py`: `IngestJob.seam_events`.
- `databasise/parts_core/declared_only.py`: `LIGHTRAG_V1_INDEX_SYNC_PART` in `LIGHTRAG_CORPUS_PARTS`.
- `databasise/parts_core/lightrag/full_ingest.py`, `full_delete.py`: forward `working_dir`; full-delete drops `record_store_touch`.
- `databasise/wirings/lightrag/corpus-ingest.json`, `corpus-delete.json`: `v1-index-sync` node; `provides`/`consumes_documents` unchanged.
- `databasise/tests/fixtures/v1_stub_server.py`: the hermetic harness.
- `databasise/tests/seam/test_lightrag_corpus_path.py`, `test_lightrag_ingest_mach11.py`, `databasise/tests/parts_core/lightrag/test_v1_index_sync.py`: new proofs.
- `databasise/tests/seam/test_delete_document.py`: env-gated real-delete proof replaced by the hermetic D-05 proof; the helpers imported by the protected `test_delete_commit_contract.py` are unchanged.

## Decisions Made

- Prune by mirror manifest, as the plan specified (research Pattern B's whole-namespace set difference would delete a parity corpus).
- `import_v1_index` keeps its per-store writers (`_import_vector_kind`, `_import_text_chunks`, `_import_graph`) because two tests import them, one of them protected (STOR-16 `test_vector_reserved_keys.py`); they now go through the shared readers and `mirror_snapshot`.
- `requirements-completed` lists only LRAG-02. LRAG-01's isolation proof is 11-02/11-06 and LRAG-03's full-ingest effects/admission half is 11-03; marking them complete now would overstate the evidence.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Protected test imports `_import_vector_kind`**
- **Found during:** Task 1 broad verify
- **Issue:** `tests/stores/test_vector_reserved_keys.py` (STOR, protected) imports `_import_vector_kind(kind, dir, store_root, workspace)`; the first refactor removed it and collection failed.
- **Fix:** kept `_import_vector_kind` and `_import_text_chunks` as thin writers over the new readers; `import_v1_index` calls them (it does not call `read_v1_snapshot(processed_only=False)` itself, but reads with the same functions, so behaviour is identical). No protected file edited.
- **Files modified:** `databasise/parity/import_index.py`
- **Committed in:** `7be6968`

**2. [Rule 1 - Bug in plan text] Evidence-resolve refusal status**
- **Found during:** Task 2
- **Issue:** the plan's behaviour line says `/evidence/resolve` on the deleted ref answers 422; the seam maps `UnresolvableEvidenceReferenceError` to 404 (SEAM-04 lookup class).
- **Fix:** the test asserts `(404, "UnresolvableEvidenceReferenceError")`; production code unchanged.
- **Files modified:** `databasise/tests/seam/test_lightrag_corpus_path.py`
- **Committed in:** `f4d9753`

**3. [Scope note] `tests/seam/test_mach11_event.py` not edited**
- Its delete cases use a test-local body that records its own touches, not the production `full_delete_body`, so step 7's "update only the delete expectations that relied on the real full-delete body" matched nothing. The sync-sourced delete event is asserted in the new `test_lightrag_ingest_mach11.py`.

**4. [Rule 1 - Bug] A new `mutates_store` part broke the F-07 record and the registry count**
- **Found during:** the offline gate after Task 2 (the plan's verify suites do not include `tests/evidence` or `tests/parts`)
- **Issue:** `render_f07_record` refuses to render while a registered `mutates_store` part has no named disposition reason; `test_registry` pinned 35 parts.
- **Fix:** added `_LIGHTRAG_V1_INDEX_SYNC_REASON` (permanent-exclusion, the same structural exclusion as full-delete) to `_KNOWN_REASONS`, inserted the identical rendered row into `F-07-MUTABLE-STORE-DISPOSITION.md` (with the Edit tool, so the byte-identical re-render test holds), and moved the registry count to 36. Neither test file is a ledger `test_ref`.
- **Files modified:** `databasise/evidence/f07_report.py`, `databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md`, `databasise/tests/parts/test_registry.py`
- **Committed in:** `19c6bb3`
- **Left as is:** the record's fixed Verdict prose still says "both real, registered mutable-store components"; the table now lists three. Rewording that template text is outside this plan; logged in `deferred-items.md`.

---

**Total deviations:** 3 auto-fixed (1 blocking, 2 bugs) plus 1 scope note.
**Impact on plan:** none on behaviour; no protected test file was edited.

## Issues Encountered

- Side effect of the required pre-change run: the Task 1 test, run against the old adapter default, made the real v1 driver open `v1/.corpus_working_dir`'s RocksDB (`cozo_graph_chunk_entity_relation.db/data`: new LOG, OPTIONS, MANIFEST and .log files), then fail on the Faiss dimension check before any v1 write. No document, chunk or vector there changed. After the change no test reaches that dir (the corpus-path test asserts its listing and mtimes are unchanged).
- Pre-existing ruff findings in `seam/engine.py`, `seam/corpus.py` and `foreign/v1_corpus_adapter.py` (import order, unsorted `__all__`, unused noqa); out of scope, not fixed. The new files are ruff-clean.

## Threat Model Coverage

- T-11-01: prune touches manifest ids only; absent dir or doc_status is a no-op (no `ctx.stores` access); unreadable doc_status raises and the engine drops staged writes (tested); parity rows survive (tested).
- T-11-02: `asyncio.wait_for(..., 300.0)` around read and mirror; `# shortcut: full O(corpus) mirror per write` recorded.
- T-11-03: per-workspace v1 dir and stores; no adapter default.

## User Setup Required

None.

## Next Phase Readiness

- 11-02 can prove LRAG-01 isolation (two store roots) with `real_v1`.
- 11-03 owns the D-06 `@0.2.0` bump, the backend-name refusal at sync start, full-ingest `mutates_store`, and removal of the driver's `entities`/`entity_info` ops (the rewritten D-05 proof no longer uses them).
- Known limit, documented in the sync docstring: an id held by both the sync and a parity import is overwritten by the sync; TOOL-02 owns merging.

## Self-Check: PASSED
