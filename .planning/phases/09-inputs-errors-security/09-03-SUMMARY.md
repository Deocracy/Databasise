---
phase: 09-inputs-errors-security
plan: 03
subsystem: api
tags: [refusals, document-id, pagination, rest-seam, mcp, input-validation]
status: complete

requires:
  - phase: 09-02
    provides: rest._status_for (422 for every non-lookup refusal) and the app-level ValidationError handler
provides:
  - "InvalidDocumentIdError: fullmatch token check in generated_on_disk_name, raised before any write or wiring on ingest and delete"
  - "PageBoundsError and corpus.checked_page: the one page check both transports call"
  - "next_offset guard: None for a zero-row page below total"
affects: [09-04, 09-05, 09-06]

commits: 2
plan_head_before: 0bec2e1f4444e2059ce4299859025b47f2c1073f
plan_head_after: d449e343cf78b4d942893d131484893851e34f93

actuals:
  tokens: 9000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "one shared page check (corpus.checked_page) imported by REST and MCP, no transport-local copy"
    - "id check runs first in ingest/delete, stateless, so a refused request leaves no partial file"

key-files:
  created:
    - databasise/tests/seam/test_ingest_input_refusals.py
    - databasise/tests/seam/test_page_bounds.py
  modified:
    - databasise/seam/refusals.py
    - databasise/seam/corpus.py
    - databasise/seam/engine.py
    - databasise/seam/rest.py
    - databasise/mcp/server.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/seam/test_delete_document.py
    - databasise/tests/seam/test_corpus_status.py

key-decisions:
  - "D-12 (revised): only None is an absent document id in the engine; a blank document_id FORM field on /documents/upload is normalised to absent in the route (document_id or None); '   ' and a JSON/MCP '' are caller ids and refused"
  - "UnknownDocumentError stays in the catalogue for a well-formed id that does not exist; delete_document no longer rewraps the id check into it (D-06)"
  - "Page validator and checked_page check the upper cap before the lower bounds, so limit 101 with offset -1 is PageSizeExceededError (D-07)"

requirements-completed: [SEAM-07, SEAM-08]

coverage:
  - id: D1
    description: "A malformed document id ('', '../x', 'a.b', 'a\\n') is refused as InvalidDocumentIdError (422 over REST, ToolError JSON over MCP) before any corpus-inbox write or v1 delete call; DELETE of 'a.b' and 'a%0A' never reaches full_delete.run_corpus_op"
    requirement: "SEAM-07"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_ingest_input_refusals.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Blank upload form document_id means absent (200, enqueued 1, 32-hex minted name); '   ' is refused"
    requirement: "SEAM-07"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_ingest_input_refusals.py::test_a_blank_upload_form_field_is_absent_and_gets_a_minted_id"
        status: pass
    human_judgment: false
  - id: D3
    description: "limit below 1 and negative offset are refused as PageBoundsError on GET /corpus, GET /jobs/{id}, MCP status and in-process Page; no refused input reaches run_corpus_op; the upper cap is checked first"
    requirement: "SEAM-08"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_page_bounds.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "next_offset is offset plus rows while below total and rows exist, else null"
    requirement: "SEAM-08"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_page_bounds.py::test_next_offset_is_offset_plus_rows_or_none"
        status: pass
    human_judgment: false
  - id: D5
    description: "A refused ingest leaves no partial file for a concurrent request (the check is stateless and runs before any write)"
    requirement: "SEAM-07"
    verification: []
    human_judgment: true
    rationale: "Concurrency edge declared verification: backstop in the plan; the order (check before write) is asserted by the inbox-empty tests, the absence of shared state is a review judgment"

duration: n/a
completed: 2026-10-17
---

# Phase 9 Plan 03: Document-id and page-bounds refusals Summary

**A malformed caller document id is refused as InvalidDocumentIdError before any write or wiring on every ingest and delete entry point, and page limits/offsets are bounded on REST, MCP and in-process by PageBoundsError through one shared checked_page.**

## Performance

- **Tasks:** 2 (Task 1 tracer, Task 2 TDD)
- **Files:** 10 (2 created, 8 modified), +473/-92 lines
- **Completed:** 2026-10-17

## Accomplishments

- `generated_on_disk_name` uses `fullmatch` against `[A-Za-z0-9_-]+` and raises `InvalidDocumentIdError(document_id=...)`; `'a\n'` no longer slips through. `Databasise.ingest` mints an id only for `None`; `delete_document` calls the check directly with no rewrap.
- `POST /documents/upload` passes `document_id or None`, so a blank form field mints an id; `POST /documents` and MCP ingest with `''` are refused.
- `PageBoundsError(limit, offset)` is raised by `Page` (limit below 1 or negative offset) and by `checked_page`; REST dropped `ge=0` on `offset` so a negative offset reaches the named refusal instead of FastAPI's `detail` body. Both transport-local `_checked_page` copies are deleted.
- `_next_offset` in the engine returns `None` for a zero-row page below `total`.

## Task Commits

1. **Task 1 (tracer): document id refusal (SEAM-07, D-06, D-12)** - `fc8205d` (feat)
2. **Task 2: page bounds (SEAM-08, D-07)** - `d449e34` (feat)

## RED evidence (failing pre-change runs)

- Task 1: with only the `InvalidDocumentIdError` class added, `pytest -q tests/seam/test_ingest_input_refusals.py` gave `17 failed, 5 passed`. Failures: `generated_on_disk_name` raising `ValueError` for `''`, `../x`, `a.b`, `a\n`; POST /documents and upload with `../x`, `a.b`, `a\n` returning 500 or 200; upload `'   '`, POST /documents `''` and MCP `''` ingesting with a minted id; MCP `../evil` as UnexpectedToolError; DELETE `a.b` returning UnknownDocumentError and `a%0A` returning 200. The oversize upload test passed already (09-02).
- Task 2: `pytest -q tests/seam/test_page_bounds.py` failed at collection (`ImportError: cannot import name 'checked_page'`). Pre-change behaviour measured directly against the old code: `GET /corpus?limit=0` 200, `?limit=-1` 200, `?offset=-1` 422 with FastAPI `{'detail': [{'type': 'greater_than_equal', ...}]}`, `GET /jobs/job-abc?limit=0` 404 UnknownJobError (limit 0 was accepted).

## Verification

- `pytest -q tests/seam tests/mcp`: 455 passed, 1 skipped, 0 failed.
- `pytest -q tests/parts_core tests/launcher`: 229 passed.
- Task 1 verify commands: 253 passed 1 skipped, then 49 passed.
- `python -c "...assert not hasattr(r, '_checked_page')..."` prints `one page check`.
- Acceptance greps: `_DOCUMENT_ID_TOKEN_RE.fullmatch` one line, `raise InvalidDocumentIdError` one line, `document.document_id or uuid` 0 non-comment lines, `document.document_id is not None` one line, `document_id=document_id or None` one line, `D-12` in engine.py and rest.py, `checked_page(` four call lines in rest.py and mcp/server.py, `def checked_page` one line.

## Deviations from Plan

None - plan executed exactly as written. Two small additions inside the plan's own scope: the `UnknownDocumentError` message now says the id "does not exist in the corpus" (it no longer describes a token failure), and `Page`'s docstring plus a new `checked_page` docstring carry the pydantic-wrapping reasoning moved from `rest._checked_page`.

## Issues Encountered

None. The BAK edit guard blocked one python heredoc edit; the same edits were made with the Edit tool.

## Known Stubs

None.

## Threat Flags

None. T-09-05 (path-like id) mitigated by the fullmatch allow-list raised before `resolve_selector` and any write; T-09-06 (negative limit slicing the corpus) mitigated by `PageBoundsError` before any `run_corpus_op` call (spy-asserted).

## Next Phase Readiness

- Requirement IDs SEAM-07 and SEAM-08: SEAM-07 is also declared by 09-02 (done); marked complete per `requirements.ready-ids`.
- 09-04 can drop the `Error executing tool <name>:` prefix; the new MCP tests parse from the first `{` and work either way.

## Self-Check: PASSED

- FOUND: databasise/tests/seam/test_ingest_input_refusals.py, databasise/tests/seam/test_page_bounds.py
- FOUND commits: fc8205d, d449e34 (ancestors of HEAD)

---
*Phase: 09-inputs-errors-security*
*Completed: 2026-10-17*
