---
phase: 09-inputs-errors-security
plan: 09
subsystem: api
tags: [seam, docs, ingest, openapi, mcp, promote, tokens]
status: complete

requires:
  - phase: 09-08
    provides: seam compare keys; tests/seam/_probes.py inbox_files
provides:
  - "file_name and content_type documented as 'not stored' on IngestDocument, the REST OpenAPI schema and the MCP ingest input schema (D-11)"
  - "corrected promote-verb, SeamRefusalError handler, opaque-part and mutable-store docstrings"
  - "tests/seam/test_seam_doc_consistency.py (docstring and behaviour half; 09-10 extends it)"
affects: [09-10]

commits: 2
plan_head_before: 49bb21e2dd3b50e97a74b34bd7e9cdbcee4fd816
plan_head_after: d889f950bce407a43298381298a849cc7f40c3ac

actuals:
  tokens: 6000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "pydantic Field(description=...) on the DTO flows into both the OpenAPI and MCP tool schemas"
    - "doc-consistency tests read sources as UTF-8 and collapse whitespace so a stale phrase cannot hide behind a line wrap"

key-files:
  created:
    - databasise/tests/seam/test_ingest_file_name.py
    - databasise/tests/seam/test_seam_doc_consistency.py
  modified:
    - databasise/seam/corpus.py
    - databasise/mcp/tools.py
    - databasise/seam/rest.py
    - databasise/seam/refusals.py
    - databasise/seam/tokens.py

key-decisions:
  - "D-11 discard-and-document branch for SEAM-15: citation carry-through stays deferred to M-04 (Phase 11)"

requirements-completed: [SEAM-15, SEAM-16]

duration: 20 min
completed: 2026-10-17
---

# Phase 9 Plan 09: Seam documentation matches the code Summary

`file_name` and `content_type` are documented as "not stored" on the DTO, REST schema and MCP schema, and the stale promote-verb, refusal-handler, opaque-part and mutable-store text is corrected and pinned by tests.

## Accomplishments

- SEAM-15 (D-11): `IngestDocument` and `IngestToolArgs` carry `Field(description="Advisory only and not stored: ...")` on both fields; `corpus.py` no longer says they are "carried into the job payload for citation". Empty strings are accepted, and a non-ASCII upload name (`résumé.pdf`) leaves exactly one `<32 hex>.bin` in the inbox with that name stored nowhere.
- SEAM-16: `rest.py` describes one handler on `SeamRefusalError` matched through the MRO; `PromoteRequest`, `UnrecognisedPromotionVerbError` and `PromoteToolArgs` say a non-string verb is a validation error and only a non-member string yields the refusal; `tokens.py` names the three opaque parts; `MutableStoreComparisonExcludedError` is documented as unreachable with current candidates.

## Test evidence

Pre-change (red) runs:
- `test_ingest_file_name.py`: 2 failed, 3 passed after the first draft (OpenAPI and MCP descriptions missing `description`); the stale-phrase check initially passed only because the sentence wraps a line, so it was changed to whitespace-collapsed text, after which it also failed (3 failed).
- `test_seam_doc_consistency.py`: 4 failed, 3 passed (REST/MRO, refusals, MCP promote docstring, tokens); the three behavioural verb/corpus checks already passed, as REQUIREMENTS notes.

Post-change: `pytest tests/seam tests/mcp tests/parts_core` gives 799 passed, 1 skipped, 0 failed.

## Task Commits

1. Task 1 (tracer): `486fe1d` feat(09-09) file_name/content_type documented as not stored
2. Task 2: `d889f95` docs(09-09) stale promote-verb, handler, opaque-part, mutable-store text corrected and pinned

## Deviations from Plan

**1. [Rule 1 - Bug in own test] Stale-phrase check wrapped across a line break**
- **Found during:** Task 1
- **Issue:** the plan's exact-substring check on `corpus.py` passed vacuously because the sentence is split by a newline.
- **Fix:** both new test files collapse whitespace before substring checks (still UTF-8 text, exact phrases).
- **Files modified:** the two new test files. **Commit:** 486fe1d, d889f95.

**2. [Minor] `PromoteToolArgs` had no `_refusal_mapped` reference**
- The docstring already named `call_tool`; it was rewritten to the plan's wording anyway, and the test asserts the decorator name is absent.

**Total deviations:** 2 (1 test-robustness fix, 1 no-op). **Impact:** none on scope.

## Known Stubs

None.

## Threat Flags

None. T-09-16 mitigated: schema descriptions say "not stored" and tests pin the wording on REST and MCP.

## Next

Ready for 09-10 (dead-code and `python -O` checks added to `test_seam_doc_consistency.py`).

## Self-Check: PASSED

- Files exist: test_ingest_file_name.py, test_seam_doc_consistency.py (both created); commits 486fe1d and d889f95 are ancestors of HEAD.
- Acceptance greps: "not stored" 4x in corpus.py, 2x in tools.py; "MRO" in rest.py module docstring; "codebase-memory-mcp" in tokens.py; "unreachable" in refusals.py.
