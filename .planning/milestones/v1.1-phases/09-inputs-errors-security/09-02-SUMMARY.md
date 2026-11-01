---
phase: 09-inputs-errors-security
plan: 02
subsystem: api
tags: [fastapi, pydantic, refusals, rest-seam, http-status, multipart-upload]
status: complete

requires:
  - phase: 09-01
    provides: refusal_body / refusal_from_errors helpers and the refusals.__all__ catalogue
provides:
  - "rest._status_for: the one mapping from refusal type to HTTP status (404 for four lookups, 422 otherwise)"
  - "app-level pydantic.ValidationError handler: a carried refusal is returned, a refusal-free ValidationError stays a 500"
  - "upload selector parse rule: omitted, empty, whitespace or 'null' field means the default selector"
affects: [09-05, 09-06]

commits: 3
plan_head_before: 49a374b4d5e718772be5232e6a1a42a90f374f59
plan_head_after: 641556920734631da1faf06e9a06d9cd1648d6b1

actuals:
  tokens: 3400
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "status derives from refusal type through one function (rest._status_for), not a constant"
    - "route-body pydantic errors reach the client through an app-level ValidationError handler"

key-files:
  created:
    - databasise/tests/seam/test_upload_selector_field.py
    - databasise/tests/seam/test_refusal_status_codes.py
  modified:
    - databasise/seam/rest.py
    - databasise/tests/seam/test_refusal_body_shape.py
    - databasise/tests/seam/test_rest_corpus_endpoints.py

key-decisions:
  - "404 is limited to the four caller-supplied lookups (UnknownTraceReferenceError, UnknownJobError, UnresolvableEvidenceReferenceError, UnknownGenerationVersionError); every other refusal is 422 (D-03)"
  - "A pydantic.ValidationError with no SeamRefusalError inside is re-raised and stays a 500: a schema failure with no refusal is a server bug"
  - "A valid-JSON upload selector that breaks a schema rule without a refusal ({\"alias\": 5}) keeps MalformedSelectorPayloadError (research A3)"

patterns-established:
  - "Not-found statuses never disclose internal identities (wiring, arm, node); /query with an unpromoted alias stays 422 UnsatisfiableSelectorError"

requirements-completed: [SEAM-02, SEAM-04, SEAM-07, SEAM-13]

coverage:
  - id: D1
    description: "Upload selector form field reports the refusal a selector rule breaks (hash alias is ForbiddenSelectorInputError); unparseable JSON and non-refusal schema errors stay MalformedSelectorPayloadError"
    requirement: "SEAM-02"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_refusal_body_shape.py + databasise/tests/seam/test_upload_selector_field.py (cd databasise && .venv/bin/pytest -q tests/seam)"
        status: pass
    human_judgment: false
  - id: D2
    description: "An oversized upload (26,214,401 bytes) returns 422 OversizedDocumentError under 4096 bytes and leaves corpus-inbox empty, never a 500"
    requirement: "SEAM-07"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_refusal_body_shape.py (oversized upload case)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Upload selector omitted, '', whitespace-only, 'null' and padded 'null' all mean the default selector (resolve_selector receives None); 'NULL' is malformed"
    requirement: "SEAM-13"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_upload_selector_field.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "rest._status_for returns 404 for the four not-found lookups and 422 for every other refusal in refusals.__all__ except ForeignEngineRefusalError (09-05)"
    requirement: "SEAM-04"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_refusal_status_codes.py (parametrized mapping check)"
        status: pass
      - kind: integration
        ref: "databasise/tests/seam/test_rest_corpus_endpoints.py::test_get_jobs_for_an_unknown_job_id_returns_404_with_the_refusal_type_name"
        status: pass
    human_judgment: false
  - id: D5
    description: "404 does not disclose whether an internal identity exists (prohibition on SEAM-04)"
    requirement: "SEAM-04"
    verification: []
    human_judgment: true
    rationale: "A safety prohibition judged by reading the four lookups; the test pins the four classes and an adjacent 422, but whether a lookup leaks an internal identity is a review judgment"

duration: n/a (continuation after owner checkpoint)
completed: 2026-10-17
---

# Phase 9 Plan 02: Upload refusals, null selector, one status mapping Summary

**The multipart upload route now reports the refusal a selector or file actually breaks (oversize is a 422, never a 500), a null or empty selector field means the default selector, and rest._status_for gives 404 to the four not-found lookups and 422 to every other refusal.**

## Performance

- **Tasks:** 3 (Task 2 was the owner-grant checkpoint, no commit)
- **Files modified:** 5 (2 created, 3 modified), +278/-22 lines
- **Completed:** 2026-10-17

## Accomplishments

- Upload selector: omitted, `''`, whitespace-only and `null` (padded or not) mean no selector, the same as `selector: null` on the JSON routes. A valid-JSON selector that breaks a rule returns that rule's refusal_type (hash alias returns ForbiddenSelectorInputError). Unparseable JSON, `NULL` and `{"alias": 5}` keep MalformedSelectorPayloadError.
- App-level `pydantic.ValidationError` handler: `IngestDocument` refusals (oversize) now reach the client as 422; a ValidationError that carries no refusal is re-raised and stays a visible 500.
- `rest._status_for` replaces the uniform-422 constant: 404 for UnknownTraceReferenceError, UnknownJobError, UnresolvableEvidenceReferenceError, UnknownGenerationVersionError; 422 otherwise. `/query` with an unpromoted alias stays 422 UnsatisfiableSelectorError; `GET /corpus?limit=101` stays 422 PageSizeExceededError.

## Task Commits

1. **Task 1 (tracer): upload refusals, null/'' selector means default (SEAM-02, SEAM-07a, SEAM-13)** - `45d6860` (feat)
2. **Task 2: owner grant of the check-edit for the protected corpus-endpoint test** - no commit; the owner ran `ledger-amend.py grant-check-edit`. Confirmed by reading `ledger/REQUIREMENTS.json`: `check_edit_grants` lists `databasise/tests/seam/test_rest_corpus_endpoints.py` (granted_at 353).
3. **Task 3: one status mapping (SEAM-04, D-03)** - `e4a73d9` (feat), then the owner-granted protected test edit `6415569` (test)

**Plan metadata:** the docs commit that follows this file (SUMMARY, STATE, ROADMAP, REQUIREMENTS).

## RED evidence (failing pre-change runs, recorded by the previous agent)

- Task 1, before the change: 6 failed / 17 passed across the new and extended upload tests. `null` and the hash-alias selector returned MalformedSelectorPayloadError; the 26,214,401-byte upload was an unhandled 500 (the `IngestDocument(...)` ValidationError at `rest.py:380`).
- Task 3, before the change: `test_refusal_status_codes.py` failed at collection with ImportError on `_status_for` (the HTTP cases also returned 422 for the four lookups).
- After the change: `pytest -q tests/seam/test_refusal_status_codes.py tests/seam/test_rest_corpus_endpoints.py tests/seam/test_rest_transport.py` gives 111 passed; the renamed node alone gives "1 passed".

## Protected file diff (`databasise/tests/seam/test_rest_corpus_endpoints.py`)

Checked with the Read tool (lines 232-238) and `git diff --stat` (2 insertions, 2 deletions): exactly the two granted lines changed.

- line 232: `test_get_jobs_for_an_unknown_job_id_returns_422_with_the_refusal_type_name` renamed to `test_get_jobs_for_an_unknown_job_id_returns_404_with_the_refusal_type_name`
- line 237: `assert response.status_code == 422` changed to `assert response.status_code == 404`

## Verification

Plan-level: `cd databasise && .venv/bin/pytest -q tests/seam tests/mcp tests/parts_core tests/launcher` gives 635 passed, 1 skipped, 0 failed.

## Deviations from Plan

None - plan executed exactly as written. (Task 3 step 3, the docstring updates, was done in `e4a73d9`; the one remaining "documented 422" at `rest.py:235` describes the page-size refusal, which is correctly 422.)

## Issues Encountered

None.

## Known Stubs

None.

## Threat Flags

None. T-09-03 mitigated (the upload selector goes through the same `Selector` validators as the JSON routes); T-09-04 accepted (404 limited to caller-supplied references).

## Next Phase Readiness

- `_status_for` is ready for 09-05 to add the fault statuses and the ForeignEngineRefusalError mapping.
- The app-level ValidationError handler is ready for 09-06's EmptyIngestDocumentError.
- Requirement IDs SEAM-02, SEAM-07 are declared by sibling plans in this phase; they are marked complete only once the last declaring plan finishes.

## Self-Check: PASSED

- FOUND: databasise/tests/seam/test_upload_selector_field.py, databasise/tests/seam/test_refusal_status_codes.py
- FOUND commits: 45d6860, e4a73d9, 6415569 (ancestors of HEAD)

---
*Phase: 09-inputs-errors-security*
*Completed: 2026-10-17*
