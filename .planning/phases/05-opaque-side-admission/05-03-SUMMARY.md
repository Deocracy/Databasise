---
phase: 05-opaque-side-admission
plan: 03
subsystem: modality
tags: [opaque-node, admission, mach-11, delete, mutates-store, contract-s19-6, lightrag, api-02]

# Dependency graph
requires:
  - phase: 05-opaque-side-admission
    provides: "05-01's databasise/foreign/ adapter layer (run_corpus_op, v1_corpus_driver_script.py), the §8 admission-record machinery (AdmissionRecord/ConditionVerdict/validate_admission), and databasise/seam/engine.py's ingest()/MACH-11 (_mach11_events/_accounted_store_keys) precedent this plan extends rather than duplicates"
provides:
  - "lightrag/full-delete@0.1.0 — the second, separately-admitted opaque port of the LightRAG corpus engine, declaring mutates_store where lightrag/full-ingest@0.1.0 declares writes_artifact (CONTRACT §19.6)"
  - "Databasise.delete_document() — the fifth §18 operation, returning v1's own four-value DeletionResult status vocabulary and the correlated MACH-11 SeamEvent list"
  - "MACH-11's two-touch-kind correlation (TOUCH_KIND_OBSERVED / TOUCH_KIND_NODE_REPORTED) — the machine-observed vs node-reported distinction a subprocess-hosted mutator's touches require, re-checked for the first time against a real (non-fixture) mutates_store part"
  - "A real, measured graph-aware-cleanup proof against the Phase 3 parity build: a shared entity survives deletion with its source set reduced; an orphan-only entity is removed"
affects: [05-06, 05-07]

# Actuals (#2632)
actuals:
  tokens: 20130
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two ports of one engine, one admission record each: lightrag/full-delete@0.1.0 mirrors lightrag/full-ingest@0.1.0's subprocess/admission shape exactly but states every verdict in its own words with its own evidence — never importing the sibling record's tuple (§19.6)"
    - "Node-reported vs machine-observed store touches: NodeContext.record_store_touch lets a subprocess-hosted mutates_store node self-report a mutation the scheduler's own _ScopedStoresView cannot observe; the two touch kinds (TOUCH_KIND_OBSERVED='store', TOUCH_KIND_NODE_REPORTED='store-declared') are correlated together but never merged into one undifferentiated tuple"
    - "monkeypatching a module's own function-default global (databasise.foreign.v1_corpus_adapter.DEFAULT_V1_WORKING_DIR) to redirect a real, unmodified production Part's subprocess launch at a test's copied working directory, with zero test-only override plumbing added to production code"

key-files:
  created:
    - databasise/parts_core/lightrag/full_delete.py
    - databasise/wirings/lightrag/corpus-delete.json
    - databasise/tests/parts_core/lightrag/test_full_delete.py
    - databasise/tests/seam/test_delete_document.py
  modified:
    - databasise/foreign/v1_corpus_driver_script.py
    - databasise/parts/schema.py
    - databasise/parts_core/declared_only.py
    - databasise/runner/scheduler.py
    - databasise/seam/corpus.py
    - databasise/seam/engine.py
    - databasise/seam/refusals.py
    - databasise/tests/fixtures/v1_corpus_driver_stub.py
    - databasise/tests/parts/test_registry.py
    - databasise/tests/seam/test_mach11_event.py
    - databasise/tests/seam/test_rest_transport.py

key-decisions:
  - "Widened databasise/seam/corpus.py's document-id bare-token regex from [A-Za-z0-9-]+ to [A-Za-z0-9_-]+ (Rule 1) — every real document id in the Phase 3 parity corpus (e.g. 'a_kiss_for_corliss') contains an underscore, which introduces no path-traversal risk; the prior hex-only pattern refused every real document this plan's own Task 3 needed to delete."
  - "Extended the entities driver op (Task 1) to also return the document's own chunk_ids, and added a new entity_info op (Task 3) that looks entities up by name rather than by doc_id — a completed deletion removes the document's doc-status record, so the doc_id-keyed entities op can no longer find anything for it on the 'after' side of the real proof. Both additions touch databasise/foreign/v1_corpus_driver_script.py, which sits outside Task 3's own <files> list but inside the plan's declared files_modified set."
  - "The delete node's subprocess is redirected at a test's copied working directory via monkeypatch.setattr on databasise.foreign.v1_corpus_adapter.DEFAULT_V1_WORKING_DIR (a module-level global run_corpus_op re-reads at call time) rather than adding a working_dir override parameter to full_delete_body — keeps the real proof driving the unmodified production Part end to end through Databasise.delete_document() with zero test-only plumbing in production code."
  - "DELETE_WALL_CLOCK_CEILING_SECONDS stays 300.0 — the real run measured 2.91s, two orders of magnitude under the declared ceiling, so no basis to raise it (Task 3's own instruction: raise only on measured evidence, never to make a test pass)."

patterns-established:
  - "A second port of an already-admitted opaque engine gets its own admission record stating every verdict in its own words — copying the sibling record's tuple would violate §19.6's 'two ports, two records' reading even when the underlying evidence (environment hash, network-denial technique) is identical."

requirements-completed: [API-02]
# MODAL-02 stays open — shared with a sibling plan in this phase not yet complete
# (gsd_run query requirements.ready-ids reports 1/2 ready: API-02 ready, MODAL-02 blocked).

coverage:
  - id: D1
    description: "lightrag/full-delete@0.1.0 is a second, separate part and node registration from lightrag/full-ingest@0.1.0 — same underlying engine, different declared effects (mutates_store vs writes_artifact), neither part exposes the other's operation"
    requirement: "MODAL-02"
    verification:
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_delete.py::test_the_delete_part_declares_mutates_store_and_the_ingest_part_declares_writes_artifact"
        status: pass
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_delete.py::test_the_delete_admission_record_carries_its_own_eleven_verdicts_not_the_ingest_records"
        status: pass
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_delete.py::test_derive_execution_mode_returns_subprocess_and_host_accepts_the_declared_ceiling"
        status: pass
    human_judgment: false
  - id: D2
    description: "Databasise.delete_document() returns a DeletionOutcome whose status is drawn from v1's own four-value vocabulary; deleting the same document twice returns success then not_found; a not_allowed status surfaces unchanged"
    requirement: "API-02"
    verification:
      - kind: integration
        ref: "tests/seam/test_delete_document.py::test_deleting_the_same_document_twice_yields_success_then_not_found"
        status: pass
      - kind: integration
        ref: "tests/seam/test_delete_document.py::test_a_not_allowed_status_from_the_driver_surfaces_unchanged_never_remapped_or_raised"
        status: pass
      - kind: unit
        ref: "tests/seam/test_delete_document.py::test_a_malformed_document_id_raises_unknown_document_error_before_any_wiring_loads"
        status: pass
    human_judgment: false
  - id: D3
    description: "MACH-11's correlation re-checked against a real deleting part — the first non-fixture mutates_store part — and the machine-observed-vs-node-reported distinction is recorded in the code, not assumed"
    requirement: "API-02"
    verification:
      - kind: integration
        ref: "tests/seam/test_mach11_event.py::test_the_real_deleting_part_produces_exactly_one_seam_event"
        status: pass
      - kind: integration
        ref: "tests/seam/test_mach11_event.py::test_the_real_deleting_nodes_recorded_touches_carry_the_node_reported_kind"
        status: pass
      - kind: integration
        ref: "tests/seam/test_mach11_event.py::test_the_real_deleting_events_component_equals_the_registered_name_at_version_not_a_node_id"
        status: pass
    human_judgment: false
  - id: D4
    description: "A real delete against a real v1 working directory leaves a shared entity reduced (deleted document's chunks absent, at least one surviving chunk present) and removes an orphan-only entity — v1's own reference-counting algorithm is exercised, not reimplemented"
    requirement: "API-02"
    verification:
      - kind: integration
        ref: "tests/seam/test_delete_document.py::test_deleting_a_real_document_reduces_shared_entities_and_removes_orphan_only_ones"
        status: pass
    human_judgment: true
    rationale: "The plan's own <verification> block asks a human to run this test once against the real Phase 3 build and read the recorded before/after entity source sets below, confirming the surviving entity's remaining sources are the ones expected — an automated pass is necessary but the plan explicitly wants a human read of the recorded numbers too."

duration: 95min
completed: 2026-09-08
status: complete
---

# Phase 5 Plan 3: Opaque-side admission — LightRAG's delete port, and MACH-11's first real correlation Summary

**`lightrag/full-delete@0.1.0` joined `lightrag/full-ingest@0.1.0` as a second, separately-admitted opaque port (mutates_store, not writes_artifact); `Databasise.delete_document()` now returns v1's own deletion-status vocabulary with correlated MACH-11 events, and a real delete against the Phase 3 parity build measurably reduced a shared entity's source set while removing an orphan-only one.**

## Performance

- **Duration:** ~95 min
- **Tasks:** 3 completed
- **Files:** 4 created, 11 modified

## Accomplishments

- `databasise/parts_core/lightrag/full_delete.py`: the second opaque port, `LIGHTRAG_FULL_DELETE_PART` (`effects=["mutates_store", "reads_kv", "reads_graph"]`, `artifact_scope=None`) with its own eleven-`ConditionVerdict` §8 admission record, stated in its own words per §19.6 rather than importing the ingest port's record.
- `databasise/foreign/v1_corpus_driver_script.py`: `op == "delete"` calls v1's own `adelete_by_doc_id` (never reimplementing its reference-counting); `op == "entities"` and the new `op == "entity_info"` support Task 3's real proof (the latter needed because a completed deletion removes the doc-status record the doc_id-keyed `entities` op depends on).
- `databasise/parts/schema.py` + `databasise/runner/scheduler.py`: `NodeContext.record_store_touch` and the two touch kinds (`TOUCH_KIND_OBSERVED`, `TOUCH_KIND_NODE_REPORTED`) — a subprocess-hosted `mutates_store` node self-reports the mutations the machine holds no handle to observe.
- `databasise/seam/engine.py`: `Databasise.delete_document()` — the fifth §18 operation — plus `_mach11_events`'s re-checked correlation and its docstring's corrected finding (two real parts now declare `mutates_store`, not zero).
- `databasise/seam/corpus.py`: `DeletionOutcome` (v1's own status vocabulary, `seam_events`); the document-id token regex widened to permit underscore (a real bug this plan's own real-corpus test surfaced).
- Real proof: deleting `a_kiss_for_corliss` against a copy of the Phase 3 parity build reduced the shared entity **Shirley Temple**'s source set from `['a_kiss_for_corliss-chunk-000', 'kiss_and_tell_1945_film-chunk-000']` to `['kiss_and_tell_1945_film-chunk-000']`, and removed all 8 orphan-only entities that document alone contributed — measured wall-clock: **2.91 seconds** (well under the declared 300s ceiling; 2 shared entities, 8 orphan-only entities total).

## Task Commits

Each task was committed atomically:

1. **Task 1: The delete port — a second registration, not a second operation on the first** - `96e8519` (feat)
2. **Task 2: delete_document() at the seam, and MACH-11's first real correlation** - `2060a80` (feat)
3. **Task 3: Graph-aware cleanup proved against a real v1 working directory** - `4f43097` (feat)

## Files Created/Modified

- `databasise/parts_core/lightrag/full_delete.py` - the second opaque port + its own §8 admission record
- `databasise/wirings/lightrag/corpus-delete.json` - the one-node delete wiring
- `databasise/tests/parts_core/lightrag/test_full_delete.py` - one test per Task 1 `<behavior>` bullet
- `databasise/tests/seam/test_delete_document.py` - idempotency, concurrency-status, and the real graph-aware-cleanup proof
- `databasise/foreign/v1_corpus_driver_script.py` - `delete`/`entities`/`entity_info` branches
- `databasise/parts/schema.py` - `NodeContext.record_store_touch`
- `databasise/parts_core/declared_only.py` - `LIGHTRAG_FULL_DELETE_PART` registered; `LIGHTRAG_CORPUS_PARTS` tuple
- `databasise/runner/scheduler.py` - `TOUCH_KIND_OBSERVED`/`TOUCH_KIND_NODE_REPORTED`; binds `record_store_touch` per node
- `databasise/seam/corpus.py` - `DeletionOutcome`; widened document-id token regex
- `databasise/seam/engine.py` - `Databasise.delete_document()`; `_mach11_events` accepts both touch kinds
- `databasise/seam/refusals.py` - `UnknownDocumentError`
- `databasise/tests/fixtures/v1_corpus_driver_stub.py` - stub `delete`/`entities`/`entity_info` branches
- `databasise/tests/parts/test_registry.py` - default registry count 21 -> 22
- `databasise/tests/seam/test_mach11_event.py` - a real (non-fixture) `mutates_store` part exercises the correlation
- `databasise/tests/seam/test_rest_transport.py` - `UnknownDocumentError` refusal-mapping factory entry

## Decisions Made

See `key-decisions` in frontmatter — four decisions: widening the document-id regex to permit underscore (a real bug the real-corpus test surfaced), extending the driver script beyond Task 3's own `<files>` list (but within the plan's own declared `files_modified`) to support the "after deletion" re-check by entity name, redirecting the real Part's subprocess via a module-global monkeypatch rather than new production plumbing, and leaving the declared ceiling unchanged (300s) against a measured 2.91s real run.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Document-id token regex refused every real document id in the corpus**
- **Found during:** Task 3
- **Issue:** `databasise/seam/corpus.py`'s `_DOCUMENT_ID_TOKEN_RE` (`^[A-Za-z0-9-]+$`) forbids underscore. Every document id in the Phase 3 parity corpus (`a_kiss_for_corliss`, `ed_wood_film`, etc.) contains one, so `Databasise.delete_document("a_kiss_for_corliss")` raised `UnknownDocumentError` before this plan's own Task 3 test could reach the real deletion path at all.
- **Fix:** Widened the pattern to `^[A-Za-z0-9_-]+$` — underscore introduces no path-traversal risk (no `/`, `\`, or bare `.` is newly permitted), so the actual security requirement (`generated_on_disk_name` can never escape the corpus-inbox directory) is unaffected.
- **Files modified:** `databasise/seam/corpus.py`
- **Verification:** `tests/seam/test_delete_document.py`'s real leg now reaches and passes the deletion; `tests/parts_core/lightrag/test_full_ingest.py`'s existing escape-refusal test (`../x`, `a/b`, `a\b`, `.`) still passes unchanged.
- **Committed in:** `4f43097` (Task 3 commit)

**2. [Rule 3 - Blocking] `test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value` failed for the new `UnknownDocumentError`**
- **Found during:** Task 2 (full-suite verification pass)
- **Issue:** `databasise/tests/seam/test_rest_transport.py`'s own generic, subclass-enumerating refusal-mapping test walks every `SeamRefusalError` subclass and requires a registered test factory for each — adding `UnknownDocumentError` without one is exactly the silent-fall-through that test exists to prevent.
- **Fix:** Registered `UnknownDocumentError: lambda: UnknownDocumentError(document_id="../escape")` in `_REFUSAL_FACTORIES`.
- **Files modified:** `databasise/tests/seam/test_rest_transport.py`
- **Verification:** `tests/seam/test_rest_transport.py` (full file) passes.
- **Committed in:** `2060a80` (Task 2 commit)

**3. [Rule 3 - Blocking] `default_registry()`'s exact-count test broke on the new registration**
- **Found during:** Task 1
- **Issue:** `tests/parts/test_registry.py::test_default_registry_holds_exactly_twenty_one_entries` asserted exactly 21 entries — registering `lightrag/full-delete@0.1.0` is exactly this plan's own Task 1 deliverable, raising the real count to 22.
- **Fix:** Updated the test (renamed, docstring, assertion) to assert 22.
- **Files modified:** `databasise/tests/parts/test_registry.py`
- **Verification:** `tests/validator/ tests/parts/` (91 passed).
- **Committed in:** `96e8519` (Task 1 commit)

**4. [Rule 1 - Bug] The `entities` op's "after deletion" call found nothing, because the doc-status record it keys on was already gone**
- **Found during:** Task 3
- **Issue:** The real proof's post-deletion re-check called the same `entities` op (keyed on `doc_id`) used before deletion — but `adelete_by_doc_id` had already removed the document's own doc-status record, so the op's own doc-status lookup returned nothing and reported an empty entity map regardless of the graph's real post-deletion state, which would have made the shared-entity assertion fail for the wrong reason (a design gap, not a real over-deletion).
- **Fix:** Added a new `entity_info` op that looks a caller-supplied list of entity names up directly via `get_entity_info`, independent of any doc-status record; the test's "after" check uses this instead of a second `entities` call.
- **Files modified:** `databasise/foreign/v1_corpus_driver_script.py`, `databasise/tests/fixtures/v1_corpus_driver_stub.py`, `databasise/tests/seam/test_delete_document.py`
- **Verification:** the real leg (`DATABASISE_RUN_REAL_DELETE=1`) passes, confirming the shared entity's source set is genuinely reduced and the orphan-only entities are genuinely gone.
- **Committed in:** `4f43097` (Task 3 commit)

---

**Total deviations:** 4 auto-fixed (2 Rule 1 bugs, 2 Rule 3 blocking issues).
**Impact on plan:** All four were necessary corrections directly caused by, or required to prove, this plan's own real-corpus deletion claim. No scope creep — deviation 4 stayed inside the plan's own declared `files_modified` set even though it touched a file outside Task 3's own `<files>` tag.

## Issues Encountered

None beyond the deviations documented above.

## Real-Deletion Evidence (Task 3 item D)

A one-time reconnaissance pass over the Phase 3 parity build (20 documents) found every document except three (`ed_wood`, `secretary_of_state_for_constitutional_affairs`, `village_accountant`) already contributes both a shared and an orphan-only entity, so the first document alphabetically (`a_kiss_for_corliss`) was used without a search loop.

| Field | Value |
|---|---|
| Document deleted | `a_kiss_for_corliss` |
| Shared entities (before) | 2 |
| Orphan-only entities (before) | 8 |
| Example shared entity | `Shirley Temple` |
| Source set before | `['a_kiss_for_corliss-chunk-000', 'kiss_and_tell_1945_film-chunk-000']` |
| Source set after | `['kiss_and_tell_1945_film-chunk-000']` |
| Measured wall-clock duration | 2.91 seconds |
| Declared ceiling | 300.0 seconds (unchanged — measured duration is two orders of magnitude under it) |

This run reached no LLM call (no partial-rebuild path was exercised for this particular deleted document — the shared entity's remaining source list needed no rebuild beyond removing the deleted chunk id from the tracked set), so its real-world cost floor for a rebuild-triggering deletion is not yet measured; a future re-run against a document whose deletion does trigger a partial rebuild would be the next data point.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Two ports of one engine (`lightrag/full-ingest@0.1.0`, `lightrag/full-delete@0.1.0`) are now real, admitted, and tested — 05-04 (status/health) and 05-05/05-06 (remaining corpus-side work, second engine admission) extend the same `databasise/foreign/` adapter and `AdmissionRecord` machinery rather than inventing a second pattern.
- `MODAL-02` stays open (shared with a sibling plan in this phase not yet complete — `gsd_run query requirements.ready-ids` reports 1/2 ready, `API-02` ready and marked complete by this plan, `MODAL-02` blocked). `API-02` is now fully proved: idempotency, concurrency-status pass-through, and the real graph-aware-cleanup claim, all with automated coverage.
- <human-check> item from the plan's own `<verification>` block (run the real-deletion test once against the real Phase 3 build and read the recorded before/after entity source sets above, confirming the surviving entity's remaining sources are the ones expected) is harvested into end-of-phase UAT per `workflow.human_verify_mode: end-of-phase` — this SUMMARY's own evidence table above is exactly what that check reads.
- No blockers for 05-04 through 05-07.

## Self-Check: PASSED

- FOUND: `databasise/parts_core/lightrag/full_delete.py`
- FOUND: `databasise/wirings/lightrag/corpus-delete.json`
- FOUND: `databasise/tests/parts_core/lightrag/test_full_delete.py`
- FOUND: `databasise/tests/seam/test_delete_document.py`
- FOUND commit: `96e8519`
- FOUND commit: `2060a80`
- FOUND commit: `4f43097`
- Re-ran all `<acceptance_criteria>` from every task: all pass (registry effect/artifact_scope checks, `derive_execution_mode`/`host`, `adelete_by_doc_id`/`subtract_source_ids` grep counts, wiring node-list check, `record_store_touch` no-op default, `TOUCH_KIND_NODE_REPORTED` grep counts, envelope.py untouched, `SeamEvent.component` equality, real-leg skip-message and copytree checks, before/after entity-source assertions).
- Re-ran the plan-level `<verification>`: `cd databasise && uv run pytest -q` — 636 passed, 1 skipped (real-delete leg skipped without `DATABASISE_RUN_REAL_DELETE=1`, and separately confirmed passing with it set — see Real-Deletion Evidence above). `uv run python -m databasise.tools.check_import_boundary` — exit 0. `databasise/seam/envelope.py` confirmed untouched (`git diff --name-only c17837e..HEAD -- databasise/seam/envelope.py` empty).

---
*Phase: 05-opaque-side-admission*
*Completed: 2026-09-08*
