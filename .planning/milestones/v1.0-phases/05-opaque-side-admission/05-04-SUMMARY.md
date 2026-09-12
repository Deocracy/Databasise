---
phase: 05-opaque-side-admission
plan: 04
subsystem: api
tags: [opaque-node, admission, subprocess, lightrag, corpus-status, health, pagination, rest, api-01, api-06, mcp]

# Dependency graph
requires:
  - phase: 05-opaque-side-admission
    provides: "05-01's databasise/foreign/ adapter layer (run_corpus_op, v1_corpus_driver_script.py) and Databasise.ingest(); 05-03's delete port, MACH-11 correlation, and Databasise.delete_document()"
provides:
  - "Databasise.get_job_status/health/corpus_status/document_counts — the sixth through ninth §18 operations, reaching databasise.foreign.run_corpus_op directly (never through a registered Part/wiring), bounded and paginated by construction (API-06)"
  - "Seven new REST routes (POST /documents, POST /documents/upload, GET /jobs/{job_id}, DELETE /documents/{document_id}, GET /health, GET /corpus, GET /corpus/counts) over the identical thin-adapter shape Phase 4 established"
  - "The two optional dependencies (python-multipart, mcp) plan 05-07 needs, installed behind a checkpoint-confirmed package legitimacy gate"
affects: [05-05, 05-06, 05-07]

# Actuals (#2632)
actuals:
  tokens: 19775
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added:
    - "python-multipart>=0.0.32 (rest extra) — FastAPI's own documented multipart/form-data dependency for the upload route"
    - "mcp>=2.2.0 (new mcp extra, installed but unused until 05-07 wires databasise/mcp/ against it)"
  patterns:
    - "Bounded read surface owned by the §17 adapter directly, never a registered port: get_job_status/health/corpus_status/document_counts reach databasise.foreign.run_corpus_op directly rather than dispatching a Part through the scheduler — a status/health read produces no evidence, mutates nothing, and declares no effect"
    - "Refuse a REST-side page-cap breach by raising the named SeamRefusalError directly in a small route-adjacent helper before Page is ever constructed, rather than letting Page's own model_validator raise it — pydantic wraps a validator-raised exception into a ValidationError at the construction call site, which Starlette's exception middleware cannot match against the registered SeamRefusalError handler"

key-files:
  created:
    - databasise/tests/seam/test_ingest_job_status.py
    - databasise/tests/seam/test_corpus_status.py
    - databasise/tests/seam/test_rest_corpus_endpoints.py
  modified:
    - databasise/foreign/v1_corpus_adapter.py
    - databasise/foreign/v1_corpus_driver_script.py
    - databasise/tests/fixtures/v1_corpus_driver_stub.py
    - databasise/seam/corpus.py
    - databasise/seam/refusals.py
    - databasise/seam/engine.py
    - databasise/seam/rest.py
    - databasise/pyproject.toml
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/test_embed_startup.py

key-decisions:
  - "Checkpoint resolved: mcp 2.2.0 and python-multipart 0.0.32 both confirmed legitimate before either package was added — the research audit's [SUS] verdicts were download-count blind spots in the checking sandbox, not slopsquat signatures; both resolve to their real official upstream repos and major versions match what 05-RESEARCH.md and 05-07 need."
  - "get_job_status/health/corpus_status/document_counts reach databasise.foreign.run_corpus_op directly, never through a registered Part/wiring/scheduler step — matches the plan's own key_links, and keeps a bounded liveness/status read structurally distinct from ingest/delete_document's opaque-Part dispatch."
  - "[Rule 1 - Bug] REST's page-cap refusal (_checked_page in rest.py) raises PageSizeExceededError directly rather than letting Page(limit=..., offset=...) raise it inside the route body. A Page constructed by hand from already-parsed query parameters is not the same code path FastAPI's own request-body parsing uses; pydantic wraps a validator-raised exception into a ValidationError at that construction call site, which is not a SeamRefusalError subclass and which Starlette's exception middleware therefore cannot match against the app's registered handler — this would have produced an unhandled 500 instead of the documented 422 carrying requested/limit as integers."
  - "mcp lands as its own new [project.optional-dependencies] extra, separate from rest, with no corresponding entry in [tool.setuptools] packages yet — that entry belongs to plan 05-07's own commit (which also creates the package directory it names), so a uv sync between the two plans never names a directory that does not exist."

requirements-completed: [API-01, API-06]

coverage:
  - id: D1
    description: "A caller polls an ingest job by the id ingest() returned and receives per-document status drawn from v1's own DocProcessingStatus vocabulary; an unknown job id raises UnknownJobError rather than returning None or an empty result"
    requirement: "API-01"
    verification:
      - kind: unit
        ref: "tests/seam/test_ingest_job_status.py#test_get_job_status_for_a_known_job_returns_one_entry_per_document"
        status: pass
      - kind: unit
        ref: "tests/seam/test_ingest_job_status.py#test_get_job_status_for_an_unknown_job_id_raises_unknown_job_error"
        status: pass
      - kind: unit
        ref: "tests/seam/test_ingest_job_status.py#test_get_job_status_error_message_is_present_only_for_the_failed_document"
        status: pass
    human_judgment: false
  - id: D2
    description: "health()/document_counts() return fixed-size records, and corpus_status() returns at most MAX_PAGE_SIZE document entries per call with an explicit next_offset; a caller requesting a page larger than the cap is refused by name, never silently clamped"
    requirement: "API-06"
    verification:
      - kind: unit
        ref: "tests/seam/test_corpus_status.py#test_corpus_status_pages_across_the_whole_corpus_in_at_least_three_pages"
        status: pass
      - kind: unit
        ref: "tests/seam/test_corpus_status.py#test_page_limit_above_the_cap_is_refused_never_clamped"
        status: pass
      - kind: unit
        ref: "tests/seam/test_corpus_status.py#test_health_returns_the_fixed_field_set"
        status: pass
      - kind: unit
        ref: "tests/seam/test_corpus_status.py#test_document_counts_by_status_keys_match_and_total_is_their_sum"
        status: pass
    human_judgment: false
  - id: D3
    description: "No status, health or corpus method returns document content, chunk text, an embedding vector, or a graph node payload — only identifiers, statuses, counts, and timestamps"
    requirement: "API-06"
    verification:
      - kind: unit
        ref: "tests/seam/test_corpus_status.py#test_no_corpus_status_model_declares_a_content_bearing_field"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every corpus-side operation is reachable through both transports — in-process and REST — and the REST layer holds no logic; test_rest_transport.py's existing AST proof still passes with the new endpoints present"
    requirement: "API-01, API-06"
    verification:
      - kind: integration
        ref: "tests/seam/test_rest_corpus_endpoints.py (dual-transport equivalence tests for /documents, /documents/upload, /jobs/{job_id}, /documents/{document_id}, /health, /corpus, /corpus/counts)"
        status: pass
      - kind: unit
        ref: "tests/seam/test_rest_corpus_endpoints.py#test_rest_module_still_calls_no_selector_resolution_redaction_or_envelope_assembly_function"
        status: pass
      - kind: unit
        ref: "tests/seam/test_rest_transport.py::test_rest_module_calls_no_selector_resolution_redaction_or_envelope_assembly_function"
        status: pass
    human_judgment: false
  - id: D5
    description: "A raw multipart upload and a JSON structured payload reach the identical Databasise.ingest() call — two delivery shapes of one §18 operation, exactly as /query and /query/stream already are"
    requirement: "API-01"
    verification:
      - kind: integration
        ref: "tests/seam/test_rest_corpus_endpoints.py#test_post_documents_upload_returns_an_ingest_job_via_the_deferred_parse_path"
        status: pass
      - kind: integration
        ref: "tests/seam/test_rest_corpus_endpoints.py#test_generated_on_disk_name_is_reachable_for_a_multipart_uploaded_document"
        status: pass
    human_judgment: false
  - id: D6
    description: "Upload, poll to completion (observing the full status sequence, not just the terminal state), read counts, delete, read counts again, confirm a second delete reports not_found — as one sequence, over both transports, producing the same statuses (ROADMAP criterion 3)"
    requirement: "API-01, API-06"
    verification:
      - kind: integration
        ref: "tests/seam/test_rest_corpus_endpoints.py#test_upload_poll_delete_round_trip"
        status: pass
      - kind: integration
        ref: "tests/seam/test_rest_corpus_endpoints.py#test_upload_poll_delete_round_trip_in_process_matches_the_rest_status_sequence"
        status: pass
      - kind: integration
        ref: "tests/seam/test_rest_corpus_endpoints.py#test_the_rest_and_in_process_round_trips_observe_the_identical_status_sequence"
        status: pass
    human_judgment: false
  - id: D7
    description: "The two optional dependencies plan 05-07 needs are installed behind a human-confirmed legitimacy gate"
    requirement: "API-01, API-06"
    verification:
      - kind: other
        ref: "checkpoint resolution recorded in this SUMMARY's key-decisions; databasise/pyproject.toml's rest/mcp extras"
        status: pass
    human_judgment: true
    rationale: "The checkpoint resolution came from the orchestrator relaying the user's package-legitimacy verdict, not from an automated verification this executor ran itself — recorded here for the record, not re-derived."

duration: 40min
completed: 2026-09-08
status: complete
---

# Phase 5 Plan 4: Opaque-side admission — bounded status/health/counts and the corpus-side REST routes Summary

**API-01's polling half and all of API-06 landed as four new seam methods that reach the §17 foreign-engine adapter directly (never a registered Part), seven new REST routes carrying every corpus-side operation as thinly as Phase 4's query routes, and the two `[SUS]`-flagged-but-checkpoint-cleared optional dependencies (`python-multipart`, `mcp`) plan 05-07 needs.**

## Performance

- **Duration:** ~40 min (continuation after a pre-task `blocking-human` checkpoint; the human's answer is recorded in this SUMMARY's key-decisions, not re-litigated)
- **Tasks:** 3 completed
- **Files:** 3 created, 10 modified

## Accomplishments

- `databasise/foreign/v1_corpus_driver_script.py`: `op == "status"` (counts via `get_processing_status`, document list via `aget_docs_by_track_id` or a corpus-wide `get_docs_by_statuses` listing, sorted and sliced by offset/limit on the v1 side) and `op == "health"` (a real facade-construction probe, not a file-existence check) — both read-only, calling no mutating v1 API.
- `databasise/seam/corpus.py`: `Page`/`MAX_PAGE_SIZE`, `DocumentStatusEntry`, `JobStatus`, `CorpusStatus`, `DocumentCounts`, `HealthReport` — every model frozen, `extra="forbid"`, and free of any content-bearing field.
- `databasise/seam/engine.py`: `Databasise.get_job_status/health/corpus_status/document_counts` — the sixth through ninth §18 operations. `get_job_status` raises `UnknownJobError` (raise-not-None, mirroring `TraceStore.resolve`); `health()` probes the machine's own kv/vector/graph stores and the foreign engine's own liveness, never raising for an unreachable participant.
- `databasise/seam/rest.py`: seven new one-line thin-adapter routes carrying every corpus-side operation, plus `IngestRequest`/`DeleteRequest` DTOs. Fixed a real bug (Rule 1) in the page-cap refusal path that would otherwise have 500'd instead of 422'ing.
- `databasise/pyproject.toml`: `python-multipart>=0.0.32` joined the `rest` extra; a new `mcp` extra (`mcp>=2.2.0`) was added for plan 05-07 — both behind the resolved package-legitimacy checkpoint.
- `databasise/tests/seam/test_rest_corpus_endpoints.py`: dual-transport equivalence for every corpus-side operation, the multipart upload path, and the upload-poll-delete round trip (ROADMAP criterion 3) proved once end to end, over both transports, with the observed status sequence compared directly.

## Task Commits

Each task was committed atomically:

1. **Task 1: Bounded job status, health, counts and a paginated corpus list** - `e560338` (feat)
2. **Task 2: The corpus-side REST routes, as thin as Phase 4's** - `2b879b2` (feat)
3. **Task 3: The upload-poll-delete round trip, proved once end to end** - `1f7626a` (test)

## Files Created/Modified

- `databasise/foreign/v1_corpus_adapter.py` - `STATUS_WALL_CLOCK_CEILING_SECONDS=60.0`
- `databasise/foreign/v1_corpus_driver_script.py` - `op == "status"`/`op == "health"` branches
- `databasise/tests/fixtures/v1_corpus_driver_stub.py` - matching stub branches, configurable to exercise pagination across several pages
- `databasise/seam/corpus.py` - `Page`, `MAX_PAGE_SIZE`, `DocumentStatusEntry`, `JobStatus`, `CorpusStatus`, `DocumentCounts`, `HealthReport`
- `databasise/seam/refusals.py` - `UnknownJobError`, `PageSizeExceededError`
- `databasise/seam/engine.py` - `Databasise.get_job_status/health/corpus_status/document_counts`
- `databasise/seam/rest.py` - seven new routes, `IngestRequest`/`DeleteRequest`, `_checked_page`
- `databasise/pyproject.toml` - `python-multipart` in `rest`; new `mcp` extra
- `databasise/tests/seam/test_ingest_job_status.py`, `test_corpus_status.py`, `test_rest_corpus_endpoints.py` - new test coverage
- `databasise/tests/seam/test_rest_transport.py` - refusal-mapping test factories for `UnknownJobError`/`PageSizeExceededError`
- `databasise/tests/test_embed_startup.py` - widened the optional-extra assertion to accept `mcp` alongside `rest`

## Decisions Made

See `key-decisions` in frontmatter — the checkpoint resolution (both packages confirmed legitimate), the direct-adapter-not-a-Part design for the four read methods, the REST page-cap bug fix, and the `mcp` extra's deliberate lack of a `[tool.setuptools] packages` entry (left for 05-07).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] REST's page-cap refusal would have 500'd instead of 422'ing**
- **Found during:** Task 2
- **Issue:** Constructing `Page(limit=limit, offset=offset)` directly inside a route body, from already-FastAPI-parsed query parameters, is not the same code path FastAPI's own request-body parsing uses. `Page`'s `model_validator` raising `PageSizeExceededError` gets wrapped by pydantic into a `pydantic.ValidationError` at that construction call site — a class Starlette's exception middleware cannot match against the app's registered `SeamRefusalError` handler, so the response would have been an unhandled 500 rather than the documented 422 carrying `requested`/`limit` as integers.
- **Fix:** Added `_checked_page(limit, offset)` — a small route-adjacent helper that raises `PageSizeExceededError` directly (never through `Page`'s own validator) when `limit` exceeds `MAX_PAGE_SIZE`, before `Page` is ever constructed.
- **Files modified:** `databasise/seam/rest.py`
- **Verification:** `tests/seam/test_rest_corpus_endpoints.py::test_get_corpus_over_the_cap_returns_422_carrying_requested_and_cap` and `::test_get_corpus_over_the_cap_refusal_body_parses_as_json_with_integer_requested_and_limit`
- **Committed in:** `2b879b2`

**2. [Rule 3 - Blocking] The existing refusal-mapping test failed for the two new refusal types**
- **Found during:** Task 1 (full-suite verification pass)
- **Issue:** `databasise/tests/seam/test_rest_transport.py`'s own generic, subclass-enumerating refusal-mapping test walks every `SeamRefusalError` subclass and requires a registered test factory for each — adding `UnknownJobError`/`PageSizeExceededError` without one is exactly the silent-fall-through that test exists to prevent.
- **Fix:** Registered both in `_REFUSAL_FACTORIES`.
- **Files modified:** `databasise/tests/seam/test_rest_transport.py`
- **Verification:** `tests/seam/test_rest_transport.py` (full file) passes.
- **Committed in:** `e560338`

**3. [Rule 3 - Blocking] The existing optional-extra metadata test assumed exactly one extra**
- **Found during:** Task 2 (full-suite verification pass)
- **Issue:** `databasise/tests/test_embed_startup.py::test_5_the_declared_runtime_dependency_set_is_exactly_six_and_none_is_a_db_client` asserted every conditional (`extra == "..."`) `Requires-Dist` entry names the `rest` extra — adding the new `mcp` extra broke that assumption, which was never actually load-bearing for D-15's real claim (mandatory dependencies unchanged by adding an optional transport).
- **Fix:** Widened the assertion to accept either known extra (`rest` or `mcp`).
- **Files modified:** `databasise/tests/test_embed_startup.py`
- **Verification:** `tests/test_embed_startup.py` passes; full suite (664 passed, 1 skipped with no extra; 668 passed, 1 skipped with `--extra rest`).
- **Committed in:** `2b879b2`

---

**Total deviations:** 3 auto-fixed (1 Rule 1 bug, 2 Rule 3 blocking issues).
**Impact on plan:** No scope creep — the Rule 1 fix was necessary for the REST page-cap refusal to actually behave as the plan's own acceptance criteria require; both Rule 3 fixes were required updates to tests whose old assumptions this plan's own required changes broke.

## Issues Encountered

None beyond the deviations documented above.

## Authentication Gates

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- API-01 and API-06 are both now complete (API-01 was shared with 05-01, already complete; API-06 was declared only by this plan) — `.planning/REQUIREMENTS.md` updated accordingly.
- The plan's own `<verification>` block includes one `<human-check>` item, deferred to end-of-phase UAT per `workflow.human_verify_mode: end-of-phase`: read the field sets of `JobStatus`/`CorpusStatus`/`DocumentCounts`/`HealthReport` in `databasise/seam/corpus.py` and confirm nothing there could be used to pull the corpus out one page at a time. `test_no_corpus_status_model_declares_a_content_bearing_field` is the automated half of that same claim; the human read is still open.
- The plan's own `UNRESOLVED — API-06, category unclassified` flag (what a status read returns while the corpus is empty, and while an ingest is mid-pipeline and counts are therefore momentarily inconsistent with the document list) was not resolved by this plan — carried forward for a reviewer, per the plan's own framing that this is a review question, not a blocking gap.
- `mcp>=2.2.0` is installed (via the new `mcp` extra) but unused — plan 05-07 wires `databasise/mcp/` against it and adds the corresponding `[tool.setuptools] packages` entry in the same commit.
- No blockers for 05-05, 05-06, or 05-07.

## Self-Check: PASSED

- FOUND: `databasise/tests/seam/test_ingest_job_status.py`
- FOUND: `databasise/tests/seam/test_corpus_status.py`
- FOUND: `databasise/tests/seam/test_rest_corpus_endpoints.py`
- FOUND commit: `e560338`
- FOUND commit: `2b879b2`
- FOUND commit: `1f7626a`
- Re-ran all `<acceptance_criteria>` from every task: all pass (`Page`/`PageSizeExceededError` refusal script, no-content-field script, `get_processing_status`/`aget_docs_by_track_id` grep count, status-branch mutating-call absence, `test_trace_token.py` unchanged; `await engine.` count +7, forbidden-name grep 0, no-fastapi import, `python-multipart`/`mcp` extras present, `databasise.mcp` grep 0; round-trip status-sequence assertion, dual-transport sequence equality, over-cap JSON-integer parse).
- Re-ran the plan-level `<verification>`: `cd databasise && uv run pytest -q` — 664 passed, 1 skipped, exit 0. `cd databasise && uv run --extra rest pytest -q` — 668 passed, 1 skipped, exit 0. `cd databasise && uv run python -m databasise.tools.check_import_boundary` — exit 0.

---
*Phase: 05-opaque-side-admission*
*Completed: 2026-09-08*
