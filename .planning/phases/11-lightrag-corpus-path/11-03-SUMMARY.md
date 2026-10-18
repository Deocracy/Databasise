---
phase: 11-lightrag-corpus-path
plan: 03
subsystem: api
tags: [lightrag, v1-subprocess, opaque-part, admission, token-metering, driver-protocol]

requires:
  - phase: 11-01
    provides: per-workspace v1 working dir, lightrag/v1-index-sync@0.1.0, hermetic real-driver harness (StubModelServer, write_env_overlay, real_v1)
provides:
  - lightrag/full-ingest@0.2.0 and lightrag/full-delete@0.2.0 with fresh 11-verdict admission records (storage self-contained, CONTRACT §8 numbering)
  - the @0.2.0 driver protocol: file ingest through INPUT_DIR, targets filter with retry_doc_ids, duplicate-aware enqueued, TokenTracker usage for ingest and delete, id stem rule, exit 3 configuration refusal, facade-free health and status, page refusal, exit 4 on a torn doc-status file
  - PINNED_SYNC_BOUNDARY for lightrag/v1-index-sync@0.1.0
  - tokens_from_usage, the shared metering rule for both corpus ports
affects: [11-05, 11-07, 11-08, 11-09, LRAG-05, LRAG-06, LRAG-07, LRAG-08, LRAG-10]

actuals:
  tokens: 17900
  tasks: 4
  commits: 4
plan_head_before: 40f6d1ff45f132d636d2694ad330c4ebe7602b00
plan_head_after: d80a70a458cf1c5426fdd2de054065437a52011c

tech-stack:
  added: []
  patterns:
    - "instance-level wrap of rag.doc_status.get_docs_by_statuses restricts v1 processing to a run's targets"
    - "id stem rule: a file-ingested doc-<md5> row maps back to our id through Path(file_path).stem"
    - "facade-free driver reads: status and health never build LightRAG, so they never collide with a write's RocksDB lock"

key-files:
  created:
    - databasise/tests/foreign/test_v1_driver_protocol.py
    - databasise/tests/parts_core/lightrag/test_corpus_metering.py
    - databasise/tests/seam/test_status_during_write.py
  modified:
    - databasise/foreign/v1_corpus_driver_script.py
    - databasise/parts_core/lightrag/full_ingest.py
    - databasise/parts_core/lightrag/full_delete.py
    - databasise/parts_core/declared_only.py
    - databasise/wirings/lightrag/corpus-ingest.json
    - databasise/wirings/lightrag/corpus-delete.json
    - databasise/parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md
    - databasise/seam/engine.py
    - databasise/seam/tokens.py
    - databasise/evidence/COVERAGE.md
    - databasise/evidence/f07_report.py
    - databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md
    - databasise/evidence/FALSIFIER-2-EVIDENCE.md
    - databasise/evidence/wirings/w3-lightrag-half-decomposed.json
    - databasise/tests/fixtures/v1_corpus_driver_stub.py
    - databasise/tests/parts_core/lightrag/test_full_ingest_compat.py
    - databasise/tests/parts_core/lightrag/test_full_ingest.py
    - databasise/tests/parts_core/lightrag/test_full_delete.py
    - databasise/tests/wirings/test_store_effects_wired.py
    - databasise/tests/evidence/test_f07_record.py
    - databasise/tests/validator/test_falsifier2_evidence.py

key-decisions:
  - "Both corpus ports bump once to @0.2.0 (D-06); full-ingest declares calls_llm, mutates_store, reads_kv, reads_graph with no artifact scope; full-delete adds calls_llm; both records say storage self-contained and number §8 as CONTRACT does (3 network + spend, 8 TTL, 9 part_ref counting)"
  - "Metering rule (tokens_from_usage): no model call is counted_by none; calls with zero tokens are unbudgetable with that call count; otherwise v1-subprocess with real counts; embedding usage stays in the usage dict and is never summed into the LLM figure"
  - "The config check requires the four EMBEDDING_* and four LIGHTRAG_*_STORAGE keys for every op, the three LLM_* keys for ingest, delete and health; status checks only the store keys"
  - "The status op counts only statuses present in kv_store_doc_status.json (a missing file gives counts {}), where v1's get_processing_status zero-filled every status"
  - "Until 11-09, engine.health checks working_dir_present itself and carries the driver's configured fact under the old storages_initialized key, so a real install is not reported degraded for a renamed driver key"

patterns-established:
  - "A driver op reads job keys only inside its own _run_<op> and returns a literal-key dict; helpers take values, so the AST protocol pin stays exact"
  - "Exit codes are channels: 0 success, 1 failure, 3 v1_not_configured (key names only), 4 doc_status_unreadable"

requirements-completed: [LRAG-03, LRAG-11, LRAG-12, LRAG-20]

coverage:
  - id: D1
    description: "full-ingest@0.2.0 through the real driver indexes a staged .txt from its own bytes via INPUT_DIR (no ids= path) and the doc row is processed"
    requirement: "LRAG-08"
    verification:
      - kind: integration
        ref: "databasise/tests/foreign/test_v1_driver_protocol.py#test_a_file_ingest_indexes_the_files_own_bytes_through_input_dir"
        status: pass
    human_judgment: false
  - id: D2
    description: "Re-ingesting an id returns enqueued 0 under the caller's track id"
    requirement: "LRAG-10"
    verification:
      - kind: integration
        ref: "databasise/tests/foreign/test_v1_driver_protocol.py#test_re_ingesting_an_id_reports_zero_enqueued_under_the_callers_track_id"
        status: pass
    human_judgment: false
  - id: D3
    description: "An interrupted document stays processing through an unrelated ingest (no model call for it) and retry_doc_ids processes it"
    requirement: "LRAG-07"
    verification:
      - kind: integration
        ref: "databasise/tests/foreign/test_v1_driver_protocol.py#test_an_interrupted_document_is_left_alone_until_retry_doc_ids_names_it"
        status: pass
    human_judgment: false
  - id: D4
    description: "Ingest and delete spend is metered: v1-subprocess with the stub's counts, unbudgetable without provider usage, none without a call; the scheduled full-delete NodeTrace carries the driver's usage; corpus-delete.json declares calls_llm"
    requirement: "LRAG-11"
    verification:
      - kind: integration
        ref: "databasise/tests/parts_core/lightrag/test_corpus_metering.py"
        status: pass
    human_judgment: false
  - id: D5
    description: "Pins: both ports at @0.2.0 with the §8 pairs, the sync at @0.1.0, the AST-derived driver protocol, and every pinned name and protocol key in the rule document"
    requirement: "LRAG-12"
    verification:
      - kind: unit
        ref: "databasise/tests/parts_core/lightrag/test_full_ingest_compat.py"
        status: pass
    human_judgment: false
  - id: D6
    description: "Missing or blank keys exit 3 naming keys only (no overlay value in stdout); an unsupported backend exits 3 by key name; health reports configured false and creates no working dir"
    requirement: "LRAG-06"
    verification:
      - kind: integration
        ref: "databasise/tests/foreign/test_v1_driver_protocol.py#test_missing_configuration_exits_3_naming_keys_only"
        status: pass
    human_judgment: false
  - id: D7
    description: "entities and entity_info are refused as unknown ops; the stub carries neither"
    requirement: "LRAG-20"
    verification:
      - kind: integration
        ref: "databasise/tests/foreign/test_v1_driver_protocol.py#test_the_entity_ops_are_refused_as_unknown"
        status: pass
    human_judgment: false
  - id: D8
    description: "Facade-free status: document_id stem filter, page refusal by name, exit 4 on a torn file, empty corpus on a missing dir, and engine.corpus_status/document_counts answer while an ingest holds the working dir"
    requirement: "LRAG-05"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_status_during_write.py"
        status: pass
      - kind: integration
        ref: "databasise/tests/foreign/test_v1_driver_protocol.py#test_a_torn_doc_status_file_exits_4_and_a_missing_dir_is_an_empty_corpus"
        status: pass
    human_judgment: false
  - id: D9
    description: "full-ingest@0.2.0 declares mutates_store and not writes_artifact (granted protected edit)"
    requirement: "LRAG-03"
    verification:
      - kind: unit
        ref: "databasise/tests/wirings/test_store_effects_wired.py#test_full_ingest_at_0_2_0_declares_mutates_store_not_writes_artifact"
        status: pass
    human_judgment: false

duration: 2h35m
completed: 2026-10-18
status: complete
---

# Phase 11 Plan 03: The @0.2.0 Opaque-Boundary Bump Summary

**Both LightRAG corpus ports are now `@0.2.0`, with fresh admission records that number CONTRACT §8 correctly. Through the real v1 driver, a staged file is indexed from its own bytes, spend is metered with `TokenTracker`, duplicates count as zero, and processing touches only the run's targets. Missing configuration exits 3 and names keys only. Health and status are facade-free, and a torn doc-status file exits 4.**

## Performance

- **Duration:** about 2 h 35 min. Most of it was test wall time: real-driver suites, five broad runs and two offline-gate runs.
- **Completed:** 2026-10-18
- **Tasks:** 4/4. Task 1, the owner grant checkpoint, was done before this run. The owner ran all six grants.
- **Files modified:** 24, of which 3 are new tests

## Accomplishments

- **Ingest (Task 2):**
  - A `pending_parse` job sets `INPUT_DIR` and enqueues with no `ids=`, so v1 parses the file.
  - An instance-level `get_docs_by_statuses` wrapper limits processing to this track's non-duplicate rows. With `retry_doc_ids`, it limits processing to the named documents.
  - `enqueued` subtracts v1's duplicate rows.
  - `usage` is `{"llm", "embedding"}`, read from two `TokenTracker`s.
- **Delete, configuration and health (Task 3):**
  - Delete resolves our id by the stem rule and returns usage.
  - `main` refuses missing, blank or unsupported configuration with exit 3, naming keys only.
  - Health builds no facade.
  - The `entities` and `entity_info` ops are gone from the driver and its stub.
- **Status (Task 4):**
  - The status op reads `kv_store_doc_status.json` directly.
  - It filters by `document_id`, refuses bad pages by name, and exits 4 on a torn file.
  - `engine.document_counts` now sends `limit: 1`.
- **Pins:**
  - `test_full_ingest_compat.py` pins both ports at `@0.2.0`, the sync part at `@0.1.0` (`PINNED_SYNC_BOUNDARY`), the four-op protocol, and the §8 pairs for both records.
  - The rule-document check now requires every pinned field and every protocol op and key to appear, backticked, in `OPAQUE-BOUNDARY-RULE.md`.

## Task Commits

1. **Task 1: Owner grants** (checkpoint). Done by the owner on 2026-10-18 in the ledger working tree, which the orchestrator commits.
2. **Task 2: full-ingest@0.2.0 tracer**: `a66fabf` (feat)
3. **Task 3: full-delete@0.2.0, config check, facade-free health, no entity ops**: `e587d04` (feat)
4. **Task 4: facade-free status op**: `50a6298` (feat)
5. **Gate fix: Falsifier-2 W3 blast radius**: `d80a70a` (fix)

## Test Evidence

Each new test was run against the unchanged source first:

- **Task 2 RED:** `8 failed, 1 passed in 138.02s`.
  - The file ingest left no `kv_store_text_chunks.json` (`FileNotFoundError`): RAW mode indexed empty text.
  - The duplicate assertion failed with `1 == 0`.
  - In the interrupted-document test, the unrelated ingest reprocessed `slowdoc` and hit the stub delay, timing out with `CorpusOpTimeoutError` after 120 s.
  - The metering unit cases failed because the dead branch ran for every truthy usage.
  - The real metering test returned `'unbudgetable' == 'v1-subprocess'`, because usage was always null.
- **Task 3 RED:** collecting the compat file errored, because no `full-delete@0.2.0` was registered. The other tests gave `12 failed, 17 passed`:
  - Delete by our id returned `'not_found'`.
  - A blank `EMBEDDING_DIM` exited 1 (`ValueError: invalid literal for int()`), not 3.
  - An unsupported backend exited 0.
  - Health returned `working_dir_present`/`storages_initialized`, which come from the facade.
  - Neither entity op raised.
  - The stub still named `entity_info`.
  - `corpus-delete.json` lacked `calls_llm`.
  - The delete trace read `unbudgetable`.
- **Task 4 RED:** `9 failed, 12 passed, 9 deselected in 70.70s`:
  - The `document_id` filter was ignored: the result was `['doc-86d64a8...', 'tdoc'] == ['stemdoc']`.
  - `limit -1`, `limit 0` and `offset -1` did not raise.
  - A missing dir returned all-zero facade counts and created the dir.
  - Status during a write failed with `ForeignEngineRefusalError(CorpusOpSubprocessError)` at `cozo_impl.py __post_init__`, because the ingest held RocksDB (research Finding 3).
  - Counts sent `limit 0`.

Passing runs:

- Task 2 verify 1: `60 passed in 30.59s`, with the real-driver cases run, not skipped.
- Task 2 verify 2 (`tests/seam tests/parts_core tests/wirings tests/parity tests/mcp`): `1156 passed, 3 deselected in 198.61s`. An earlier run that also covered `tests/evidence tests/parts` gave 4 failures, all F-07 or Falsifier-2 renders; they were fixed in the same commit.
- Task 3 verify 1: `40 passed in 50.30s`.
- Task 3 broad (`tests/stores tests/seam tests/mcp tests/parity tests/runner tests/parts_core tests/wirings tests/foreign tests/evidence tests/parts`): `1 failed, 1539 passed, 3 deselected in 328.54s`. The failure was `test_f07_record`'s verdict pin, which was fixed; `tests/evidence` then gave `73 passed`.
- Task 4 verify 1 (`test_v1_driver_protocol`, `test_status_during_write`, the compat file, the protected `test_page_bounds` and `test_corpus_status`): `65 passed in 70.90s`.
- Task 4 verify 2 / plan verification (`tests/stores tests/seam tests/mcp tests/parity tests/runner tests/parts_core tests/wirings tests/foreign`): `1451 passed, 3 deselected in 386.13s`, exit 0.
- **Offline gate** `.venv/bin/python tools/check_offline_suite.py`:
  - First run: **exit 1**, with `1 failed, 1926 passed` in both invocation styles. The failure was `tests/validator/test_falsifier2_evidence.py`, which expected the W3 ingest blast radius `permitted`.
  - After `d80a70a`: **exit 0**, with `pytest -q -rs: 1927 passed, 4 deselected` and `python -m pytest -q -rs: 1927 passed, 4 deselected`.

### Granted protected edit (test_store_effects_wired.py, grant reason "11-03 Task 2 (LRAG-03, D-06)")

```diff
 _ARTIFACT_PARTS = (
-    "lightrag/full-ingest@0.1.0",
     "lightrag/embedder-index@0.1.0",
     "hipporag/graph-materializer@0.1.0",
 )
@@
 @pytest.mark.parametrize("name", _ARTIFACT_PARTS)
-def test_the_three_artifact_parts_still_declare_writes_artifact(name):
+def test_the_two_artifact_parts_still_declare_writes_artifact(name):
     assert "writes_artifact" in default_registry().get(name).effects
 
 
+def test_full_ingest_at_0_2_0_declares_mutates_store_not_writes_artifact():
+    # 11-03 (LRAG-03, D-06): v1 mutates its own working dir and writes no artifact.
+    effects = default_registry().get("lightrag/full-ingest@0.2.0").effects
+    assert "mutates_store" in effects
+    assert "writes_artifact" not in effects
```

No other protected file was edited.

## Decisions Made

The frontmatter `key-decisions` list them. The configuration-key split and the facade-free status counts are interpretations of the plan text, explained under Deviations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Registry-derived evidence followed the rename**
- **Found during:** Task 2 and Task 3 broad runs, and the offline gate.
- **Issue:**
  - `render_f07_record` refuses a registered `mutates_store` part that has no disposition reason. Full-ingest became one, and full-delete changed name.
  - The Falsifier-2 W3 evidence wiring named `full-ingest@0.1.0`, which no longer exists, so the render raised `KeyError`.
  - `test_f07_record` pinned the old delete name in the Verdict.
  - `test_falsifier2_evidence` expected the W3 ingest blast radius `permitted`. With no artifact scope it is now `n/a`.
- **Fix:**
  - Added `_LIGHTRAG_FULL_INGEST_REASON` and renamed the delete key and prose in `f07_report.py`.
  - Moved W3's ingest node to `@0.2.0` with the new effects.
  - Applied the exact re-rendered rows to `F-07-MUTABLE-STORE-DISPOSITION.md` and `FALSIFIER-2-EVIDENCE.md` with the Edit tool. Both byte-identical re-render tests pass.
  - Updated the two unprotected test assertions. The taint-rule assertions are unchanged.
- **Commits:** `a66fabf`, `e587d04`, `d80a70a`.

**2. [Rule 1 - Bug] Engine health would read a renamed driver key**
- **Found during:** Task 3.
- **Issue:** The driver's health op no longer returns `working_dir_present`/`storages_initialized`. Without a change, `engine.health()` would report a real install `degraded` from now until 11-09.
- **Fix:** Two lines in `seam/engine.py`: `working_dir_present` now comes from `self._v1_working_dir().exists()`, and `storages_initialized` carries `result["configured"]`. 11-09 renames the key (logged in `deferred-items.md`).
- **Commit:** `e587d04`.

**3. [Interpretation] Which keys each op checks.** The plan says every op needs the store keys and ingest and delete also need the model keys. Its health behaviour expects `missing_keys` to list both `EMBEDDING_DIM` and `LLM_MODEL`. Health therefore checks the full set and status checks only the store keys. The tests pin this per op.

**4. [Interpretation] Status counts.** The facade-free status op counts the statuses present in the file. A missing file gives `counts {}`, as the plan requires. The old facade path zero-filled every v1 status. `DocumentCounts.by_status` still holds only v1 status names.

**5. [Ordering] Status pin and stub filter.** `document_id` joins the status stdin pin in Task 4, because the driver first reads it there. The plan text lists it in Task 3's protocol. The stub's `document_id` filter landed in the Task 3 commit, together with the stub rewrite. The Task 3 commit also carried the Task 4 status test cases, which were red until `50a6298`.

**6. [Strengthening] Rule-document check.** `test_rule_document_and_check_agree` now requires the sync part's name and every protocol op and key, each wrapped in backticks. Before, it checked only the ingest field names.

**7. [Reuse] `tokens_from_usage`.** The metering rule lives in `full_ingest.py`, and `full_delete.py` imports it. The two admission records stay separate.

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug), plus 5 recorded interpretation, ordering and reuse notes.
**Impact on plan:** No behaviour beyond the plan was added. Every protected edit is the granted one.

## Process note

The run executed `git stash list` once, in a command chained after `ruff`. It is read-only, its output was discarded, and no stash was created, applied or dropped. The executor rules forbid every `git stash` subcommand, and this one was not needed.

## Issues Encountered

- The interrupted-document test's delayed stub request finishes after the killed subprocess is gone. The fixture's server thread then prints a `BrokenPipeError` traceback to the test output. This is noise and does not cause a failure.
- These ruff findings were already present before this plan and are unchanged: BLE001 on `main`'s blind `except` in the driver and the stub.

## Threat Model Coverage

- T-11-05: exit 3 prints key names only. The test asserts that no overlay value of five or more characters appears in stdout. The unsupported-backend test asserts that the backend value `NanoVectorDBStorage` is absent.
- T-11-06: the targets filter is proven on an interrupted document. The stub sees no chat request for it during an unrelated ingest.
- T-11-07: one `@0.2.0` bump, an AST-derived protocol pin, the sync pin, and a rule-document check that now covers every protocol key.
- T-11-25: one retry on a torn read, then exit 4 with no partial list. The test uses a corrupt file.

## User Setup Required

None.

## Next Phase Readiness

- 11-05 can stage `<inbox>/<document_id><suffix>`. The engine already stamps `input_dir`, and the driver maps v1 rows back by the stem rule.
- 11-07 maps exits 3 and 4 in the adapter. Stdout carries `{"error": "v1_not_configured", ...}` and `{"error": "doc_status_unreadable"}`.
- 11-08 can run the corpus-ingest wiring with `documents=[]` and `retry_doc_ids=[...]`. The driver returns the document's own track id.
- 11-09 reads `configured`, `missing_keys` and `unsupported_keys` from the health op.

## Self-Check: PASSED

- Created files: `databasise/tests/foreign/test_v1_driver_protocol.py`, `databasise/tests/parts_core/lightrag/test_corpus_metering.py` and `databasise/tests/seam/test_status_during_write.py` all exist.
- Commits `a66fabf`, `e587d04`, `50a6298` and `d80a70a` are ancestors of HEAD.
