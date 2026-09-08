---
phase: 05-opaque-side-admission
plan: 01
subsystem: modality
tags: [opaque-node, admission, subprocess, lightrag, ingest, contract-s8, contract-s17]

# Dependency graph
requires:
  - phase: 03-decomposition-and-parity
    provides: "the subprocess-boundary precedent (v1_driver_script.py / v1_arm.py) this plan's databasise/foreign/ package mirrors, plus the pinned v1/.venv interpreter"
  - phase: 04-the-seam
    provides: "the Databasise seam object, _execute()'s parse_wiring -> _build_stores -> scheduler.run_wiring sequence, MACH-11's recorder/_mach11_events mechanism, the SeamRefusalError hierarchy and REST's generic vars(exc) refusal mapping"
provides:
  - "A real, executable, admitted opaque Part: lightrag/full-ingest@0.1.0, hosted at the subprocess placement for the first time in this project"
  - "The §8 admission record type (AdmissionRecord/ConditionVerdict/validate_admission/cross_check_conditions) and its registration-time enforcement (UnadmittedOpaquePartError)"
  - "databasise/foreign/ — the CONTRACT §17 foreign-part adapter layer, reusable by later opaque parts (05-06's second engine)"
  - "Databasise.ingest() — the fourth §18 operation, accepting both a structured-text and a raw-byte payload"
affects: [05-02, 05-03, 05-04, 05-05, 05-06, 05-07]

# Actuals (#2632)
actuals:
  tokens: 27150
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subprocess-backed opaque Part body: databasise/foreign/v1_corpus_adapter.run_corpus_op launches databasise/foreign/v1_corpus_driver_script.py under v1's pinned interpreter, JSON over stdin/stdout, timeout-parameterized — the write-capable sibling to Phase 3's read-only v1_arm.py/v1_driver_script.py pattern"
    - "§8 admission-record enforcement at registration time (PartRegistry.register), not merely at run time"
    - "A per-node run_wiring dispatch failure's real exception object is now recoverable via the scheduler's additive node_exceptions map, rather than only a stringified trace field"

key-files:
  created:
    - databasise/parts/admission.py
    - databasise/foreign/__init__.py
    - databasise/foreign/v1_corpus_adapter.py
    - databasise/foreign/v1_corpus_driver_script.py
    - databasise/parts_core/lightrag/full_ingest.py
    - databasise/seam/corpus.py
    - databasise/wirings/lightrag/corpus-ingest.json
    - databasise/tests/fixtures/v1_corpus_driver_stub.py
    - databasise/tests/parts_core/lightrag/test_full_ingest.py
    - databasise/tests/parts/test_admission.py
  modified:
    - databasise/parts/schema.py
    - databasise/parts/registry.py
    - databasise/parts_core/declared_only.py
    - databasise/validator/execution_mode.py
    - databasise/runner/scheduler.py
    - databasise/seam/engine.py
    - databasise/seam/refusals.py
    - databasise/seam/rest.py
    - databasise/tools/check_import_boundary.py
    - databasise/pyproject.toml
    - databasise/tests/parts/test_registry.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/validator/test_execution_mode.py
    - v1/.gitignore

key-decisions:
  - "UnadmittedOpaquePartError gates on Part.kind == 'opaque', not structural_depth == 'opaque' — the plan's own Task 2 action text said structural_depth, but that would have refused registration of the already-shipped lightrag/embedder-index@0.1.0 (structural_depth='opaque', kind='embedder', no admission record); kind is what derive_execution_mode already keys its subprocess-placement decision on, so the two checks now agree"
  - "run_corpus_op's usage field is always null for the real v1 driver today — apipeline_process_enqueue_documents exposes no per-run token count back to the caller — so full_ingest_body reports tokens.counted_by='unbudgetable' rather than fabricating a zero; the seam's existing UnbudgetableParticipantError/assemble_token_breakdown mechanism (proven elsewhere) is exercised for the first time against this real, non-fixture part"
  - "A subprocess-level dispatch failure (CorpusOpTimeoutError/CorpusOpSubprocessError) never propagates out of scheduler.run_wiring by design (CONTRACT §9's 'partial outcomes are never discarded' rule) — added an additive node_exceptions map to run_wiring's returned dict so Databasise.ingest() can recover the real exception object and re-raise it as ForeignEngineRefusalError, rather than only a stringified NodeTrace.cross_process_failure_cause"
  - "v1's own docs_format string constants (FULL_DOCS_FORMAT_RAW/_PENDING_PARSE) are duplicated as bare literals in databasise/seam/engine.py rather than imported from lightrag.constants — importing lightrag anywhere under databasise/ outside the named subprocess-entry-point exclusion list is exactly what check_import_boundary.py forbids"

patterns-established:
  - "A SeamRefusalError raised inside a pydantic model_validator surfaces at the construction call site as pydantic.ValidationError (the original exception object is not recoverable) — tests assert on the wrapped message substring, matching the existing Selector/ForbiddenSelectorInputError precedent, not pytest.raises(TheTypedError) directly"

requirements-completed: []  # MODAL-02 and API-01 are both shared with sibling plans in this phase (05-03/05-05 and 05-04) not yet complete — gsd_run query requirements.ready-ids reports 0/2 ready; neither is marked complete by this plan alone

coverage:
  - id: D1
    description: "lightrag/full-ingest@0.1.0 is a real, executable opaque Part hosted at the subprocess placement, admitted under a genuine eleven-verdict §8 record"
    requirement: "MODAL-02"
    verification:
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest.py#test_derive_execution_mode_returns_subprocess_and_host_accepts_the_declared_ceiling"
        status: pass
      - kind: integration
        ref: "tests/parts_core/lightrag/test_full_ingest.py#test_ingest_returns_a_job_carrying_the_stub_echoed_track_id_and_enqueued_count"
        status: pass
      - kind: integration
        ref: "tests/parts_core/lightrag/test_full_ingest.py#test_the_real_driver_script_parses_and_speaks_the_protocol_for_an_empty_document_list"
        status: pass
    human_judgment: false
  - id: D2
    description: "A ceiling-less subprocess node is refused; a run that exceeds its declared wall-clock ceiling is refused by name carrying the ceiling value"
    requirement: "MODAL-02"
    verification:
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest.py#test_host_with_subprocess_placement_and_no_ceiling_raises_missing_wall_clock_ceiling_error"
        status: pass
      - kind: integration
        ref: "tests/parts_core/lightrag/test_full_ingest.py#test_a_stub_job_outlasting_a_tiny_ceiling_raises_foreign_engine_refusal_with_timeout_cause"
        status: pass
    human_judgment: false
  - id: D3
    description: "The ingest node's token spend reports the unbudgetable sentinel (never a fabricated zero) when the subprocess reports no usage, and the seam's existing token-breakdown mechanism refuses to count it"
    requirement: "MODAL-02"
    verification:
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest.py#test_an_ingest_with_no_reported_usage_reports_the_unbudgetable_sentinel_and_the_seam_refuses_to_count_it"
        status: pass
    human_judgment: false
  - id: D4
    description: "PartRegistry.register refuses an executable opaque part with no admission record, and refuses an invalid record (shared scope, self-reported manifest, incomplete verdict set) by name"
    requirement: "MODAL-02"
    verification:
      - kind: unit
        ref: "tests/parts/test_admission.py (all 11 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Two concurrent ingests each receive a distinct job_id; the import boundary check still exits 0 with exactly one new named exclusion"
    requirement: "API-01"
    verification:
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest.py#test_two_separately_minted_ingests_return_distinct_job_ids"
        status: pass
      - kind: unit
        ref: "uv run python -m databasise.tools.check_import_boundary"
        status: pass
    human_judgment: true
    rationale: "The plan's own <verification> block asks a human to read the new _SUBPROCESS_ENTRY_POINT_EXCLUSIONS entry and confirm the driver script genuinely runs only under v1's interpreter and is imported by nothing under databasise/ — an automated grep/AST proof of 'nothing imports this' already exists (check_import_boundary.py itself), but the plan explicitly asks for a human read of the diff as the one deliberate hole in an enforced boundary."
  - id: D6
    description: "Databasise.ingest() accepts both a structured text payload and a raw byte payload, refuses an ambiguous/oversized payload before any subprocess launch, and never lets a caller-supplied string reach a filesystem join"
    requirement: "API-01"
    verification:
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest.py#test_a_raw_upload_ingest_reaches_the_driver_via_a_server_side_path_never_a_caller_string"
        status: pass
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest.py#test_ingest_document_with_both_text_and_raw_or_neither_raises_ambiguous_payload"
        status: pass
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest.py#test_an_oversized_raw_payload_raises_before_any_bytes_reach_disk_or_a_subprocess"
        status: pass
      - kind: unit
        ref: "tests/parts_core/lightrag/test_full_ingest.py#test_generated_on_disk_name_refuses_a_document_id_that_could_escape_the_inbox_directory"
        status: pass
    human_judgment: false

duration: 165min
completed: 2026-09-08
status: complete
---

# Phase 5 Plan 1: Opaque-side admission — LightRAG's ingest core, for real Summary

**`lightrag/full-ingest@0.1.0` gained a real, subprocess-hosted body and a genuine eleven-verdict §8 admission record — Phase 1's `host()` refusal naming Phase 5 as the phase that earns `subprocess` hosting is now made good, and `Databasise.ingest()` proves one document flowing end to end through the real scheduler into v1's own pipeline and back as a job handle.**

## Performance

- **Duration:** ~165 min
- **Completed:** 2026-09-08T21:54Z
- **Tasks:** 3 completed
- **Files:** 10 created, 14 modified

## Accomplishments

- `databasise/parts/admission.py`: the §8 admission record type (`AdmissionRecord`, `ConditionVerdict`, `validate_admission`, `cross_check_conditions`) and its four named refusals.
- `databasise/validator/execution_mode.py`'s `host()` now hosts the `subprocess` placement for real — conditional on a positive `wall_clock_ceiling_seconds`, sourced by `runner/scheduler.py` from the resolved Part's own admission record.
- `databasise/foreign/` (new package): the CONTRACT §17 foreign-part adapter layer — `v1_corpus_driver_script.py` (a leaf that runs under v1's pinned interpreter) and `v1_corpus_adapter.run_corpus_op` (the timeout-parameterized launcher), mirroring Phase 3's `v1_arm.py`/`v1_driver_script.py` precedent for the write side.
- `lightrag/full-ingest@0.1.0` has a real body (`full_ingest_body`) and admission record, replacing the `body=None` stub — `PartRegistry.register` now refuses an executable opaque part with no admission record or an invalid one (`UnadmittedOpaquePartError`, `validate_admission`).
- `Databasise.ingest()` — the fourth §18 operation — dispatches the one-node `lightrag-corpus-ingest` wiring directly through the real scheduler and returns an `IngestJob` carrying v1's own `track_id`; accepts both a structured-text and a raw-byte payload (server-side on-disk naming, never a caller-supplied path).

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end — one document ingested through an admitted opaque subprocess node** - `61f582e` (feat)
2. **Task 2: The machine refuses an unadmitted or dishonest opaque part** - `e302aa5` (feat)
3. **Task 3: Raw upload and structured payload, both refused safely at the seam boundary** - `33dbb1f` (feat)

_No separate plan-metadata commit is issued by this executor run; STATE.md/ROADMAP.md updates are committed alongside this SUMMARY per the orchestrator's own final-commit step._

## Files Created/Modified

- `databasise/parts/admission.py` - §8 admission record type + registration-time/cross-check validation
- `databasise/foreign/__init__.py`, `v1_corpus_adapter.py`, `v1_corpus_driver_script.py` - CONTRACT §17 foreign-part adapter layer
- `databasise/parts_core/lightrag/full_ingest.py` - the real `full_ingest_body` + `LIGHTRAG_FULL_INGEST_ADMISSION`
- `databasise/parts_core/declared_only.py` - `LIGHTRAG_FULL_INGEST_PART` gets a real body + admission
- `databasise/parts/schema.py` - `Part.admission` field
- `databasise/parts/registry.py` - `UnadmittedOpaquePartError` + registration-time enforcement
- `databasise/validator/execution_mode.py` - `host()` hosts `subprocess` for real, given a ceiling
- `databasise/runner/scheduler.py` - ceiling sourced from the resolved Part's admission record; additive `node_exceptions` map
- `databasise/seam/corpus.py` - `IngestDocument`/`IngestJob`/`generated_on_disk_name`
- `databasise/seam/engine.py` - `Databasise.ingest()`
- `databasise/seam/refusals.py` - `ForeignEngineRefusalError`, `AmbiguousIngestPayloadError`, `OversizedDocumentError`
- `databasise/seam/rest.py` - `_refusal_response` stringifies a raw exception value in `vars(exc)`
- `databasise/wirings/lightrag/corpus-ingest.json` - the one-node ingest wiring
- `databasise/tools/check_import_boundary.py` - one new named subprocess-entry-point exclusion
- `databasise/pyproject.toml` - `databasise.foreign` package
- `databasise/tests/fixtures/v1_corpus_driver_stub.py`, `tests/parts_core/lightrag/test_full_ingest.py`, `tests/parts/test_admission.py` - new test coverage
- `databasise/tests/parts/test_registry.py`, `tests/seam/test_rest_transport.py`, `tests/validator/test_execution_mode.py` - updated for this plan's own behavior changes
- `v1/.gitignore` - ignores the new default corpus working directory

## Decisions Made

See `key-decisions` in frontmatter — four decisions: gating admission enforcement on `kind` rather than `structural_depth` (a plan-text/reality conflict resolved toward the must_haves.truths wording and toward not breaking `lightrag/embedder-index@0.1.0`); the `unbudgetable` sentinel for v1's un-exposed per-run token count; the additive `node_exceptions` map on `run_wiring`'s return; and duplicating v1's `docs_format` string constants as bare literals rather than importing them.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `PartRegistry.register`'s admission gate keyed on the wrong field**
- **Found during:** Task 2
- **Issue:** The plan's own Task 2 action text specified gating the admission requirement on `part.structural_depth == "opaque"`. `lightrag/embedder-index@0.1.0` (Phase 3, already shipped, already registered via `default_registry()`) is an executable part with `structural_depth="opaque"` but `kind="embedder"` and no admission record — gating on `structural_depth` would have broken `default_registry()` entirely (a hard `UnadmittedOpaquePartError` for a part with no relation to real opaque-node admission).
- **Fix:** Gated the check on `part.kind == "opaque"` instead — the literal value `derive_execution_mode` already keys its own `subprocess`-placement decision on, and the value both of this plan's two real admission-requiring parts (`CODEBASE_MEMORY_MCP_PART`, `LIGHTRAG_FULL_INGEST_PART`) declare alongside `structural_depth="opaque"`. This also matches the plan's own `must_haves.truths` wording ("`PartRegistry.register` refuses an executable part whose `kind` is `opaque`"), which the action text's `structural_depth` phrasing contradicted.
- **Files modified:** `databasise/parts/registry.py`
- **Verification:** `tests/parts/test_admission.py::test_registering_an_unadmitted_executable_opaque_part_raises_naming_the_part` plus the full suite (609 passed) confirms `lightrag/embedder-index@0.1.0` still loads.
- **Committed in:** `e302aa5`

**2. [Rule 1 - Bug] `ForeignEngineRefusalError.cause` broke the existing generic REST refusal-mapping mechanism**
- **Found during:** Task 1 (full-suite verification pass)
- **Issue:** `databasise/seam/rest.py`'s `_refusal_response` dumps every non-underscore attribute of a `SeamRefusalError` via `vars(exc)` directly into a `JSONResponse`. `ForeignEngineRefusalError.cause` is a raw exception object, not JSON-serializable — this broke `tests/seam/test_rest_transport.py`'s own generic, subclass-enumerating refusal-mapping test the moment the new refusal type was added.
- **Fix:** `_refusal_response` now stringifies a `BaseException`-valued attribute exactly as it already special-cases a `BaseModel`-valued one; the test's own equivalent comparison block does the same.
- **Files modified:** `databasise/seam/rest.py`, `databasise/tests/seam/test_rest_transport.py`
- **Verification:** `tests/seam/test_rest_transport.py` (20 passed)
- **Committed in:** `61f582e`

**3. [Rule 1 - Bug] Two existing tests broken by this plan's own required behavior changes**
- **Found during:** Task 1
- **Issue:** `tests/parts/test_registry.py::test_the_two_declaration_only_entries_have_no_body_and_a_non_empty_upstream_ref` asserted exactly 2 declaration-only entries — `lightrag/full-ingest@0.1.0` dropping to 1 real body is exactly this plan's own Task 1 deliverable. `tests/validator/test_execution_mode.py`'s Tests 15/16 asserted every non-in-process placement (including `subprocess`) always refuses — exactly the behavior this plan's Task 1 changes on purpose.
- **Fix:** Updated both tests in place to assert the new, intended behavior (1 remaining declaration-only entry; `subprocess` hosts given a positive ceiling and refuses with `MissingWallClockCeilingError` — not `UnimplementedPlacementError` — without one).
- **Files modified:** `databasise/tests/parts/test_registry.py`, `databasise/tests/validator/test_execution_mode.py`
- **Verification:** `tests/validator/ tests/parts/` (80/91 passed at time of each check)
- **Committed in:** `61f582e`

---

**Total deviations:** 3 auto-fixed (3 Rule 1 — all bugs directly caused by, or a plan-text/reality conflict resolved during, this plan's own required changes).
**Impact on plan:** No scope creep — every auto-fix was either a necessary correction to a plan-text error that would have broken the whole existing test suite, or the required update of a test whose old assertion was exactly what this plan set out to change.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The `databasise/foreign/` adapter layer and the §8 admission machinery are now real, tested infrastructure — 05-03 (delete) and 05-04 (status) extend the same driver script/adapter rather than inventing a second subprocess pattern; 05-06 (codebase-memory-mcp admission) reuses `AdmissionRecord`/`validate_admission`/`cross_check_conditions` directly.
- `MODAL-02` and `API-01` remain open (shared with 05-03/05-05 and 05-04 respectively) — neither is marked complete by this plan alone; `gsd_run query requirements.ready-ids` reports 0/2 ready as of this SUMMARY.
- <human-check> item from the plan's own `<verification>` block (confirm the new `v1_corpus_driver_script.py` exclusion is reviewable and genuinely imported by nothing under `databasise/`) is still open for a human reviewer — the automated `check_import_boundary.py` proof passes, but the plan explicitly asks for a human read of the diff too.
- No blockers for 05-02 through 05-07.

---
*Phase: 05-opaque-side-admission*
*Completed: 2026-09-08*
