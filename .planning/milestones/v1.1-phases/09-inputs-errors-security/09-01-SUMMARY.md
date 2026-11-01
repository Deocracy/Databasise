---
phase: 09-inputs-errors-security
plan: 01
subsystem: api
tags: [fastapi, pydantic, refusals, rest-seam]
status: complete

requires:
  - phase: 08
    provides: launcher guards (TrustedHost 400, Origin 403) that keep their own shapes (D-13)
provides:
  - "refusal_body / refusal_from_errors shared helpers in databasise/seam/refusals.py"
  - "REST RequestValidationError handler that unwraps ctx.error into the one refusal body"
  - "MultiMemberSelectorError for selectors that set more than one member"
  - "refusals.__all__ as the single refusal catalogue (all SeamRefusalError subclasses)"
affects: [09-02, 09-04, 09-05]

commits: 3
plan_head_before: 56001a43686fcde743ce5fd9145bca9cbb72a67d
plan_head_after: 8f566a068e0403d4e45e0fce70fcc961ddbe3c31

actuals:
  tokens: 5100
  tasks: 2
  commits: 3

tech-stack:
  added: []
  patterns:
    - "validator-raised refusal unwrapped from RequestValidationError ctx.error"
    - "refusals.__all__ is the catalogue; test walks SeamRefusalError.__subclasses__()"

key-files:
  created:
    - databasise/tests/seam/test_refusal_body_shape.py
    - databasise/tests/seam/test_refusal_catalogue.py
    - .planning/phases/09-inputs-errors-security/COVERAGE.md
  modified:
    - databasise/seam/refusals.py
    - databasise/seam/selectors.py
    - databasise/seam/rest.py
    - databasise/launcher/serve_rest.py
    - databasise/seam/evidence.py
    - databasise/seam/trace_store.py
    - databasise/seam/tokens.py
    - databasise/tests/seam/test_rest_transport.py

key-decisions:
  - "A request carrying both a schema error and a refusal returns the refusal body (A2)"
  - "Moved classes are re-exported from evidence/trace_store/tokens so every existing import path keeps working"

requirements-completed: [SEAM-02, SEAM-14]

completed: 2026-10-16
---

# Phase 9 Plan 01: One refusal body and one refusal catalogue Summary

Refusals raised inside pydantic validators on JSON REST routes now reach the client as the single top-level `{refusal_type, message, ...}` body (no `detail` wrapper), a multi-member selector gets the named `MultiMemberSelectorError`, and `refusals.__all__` lists every refusal type.

## Accomplishments

- `refusal_body` (moved unchanged from `rest._refusal_response`) and `refusal_from_errors` live in `refusals.py`; `_refusal_response` is now one line over `refusal_body`.
- `_validation_response` handler registered for `RequestValidationError`: unwraps the first `SeamRefusalError` from `exc.errors()[i]["ctx"]["error"]`; schema-only errors fall through to FastAPI's own handler (`{detail: [...]}`).
- `Selector._at_most_one_member_set` raises `MultiMemberSelectorError(set_members=[...])` instead of a plain `ValueError`.
- `UnknownTraceReferenceError`, `UnresolvableEvidenceReferenceError`, `UnbudgetableParticipantError` moved into `refusals.py` (private `_internal_node_id` convention kept); `NoRawUploadPathForModalityError` and the three moved classes added to `__all__`.
- D-13 boundary stated in the `rest.py` module docstring and the `build_app` docstring; no launcher test edited.
- `COVERAGE.md` records "No external API integration".

## Test-first evidence

`tests/seam/test_refusal_body_shape.py`, pre-change (RED), 10 of 12 failed with FastAPI `detail` bodies and no `refusal_type`:

```
E       assert 'detail' not in {'detail': [{'type': 'value_error', 'loc': ['body', 'selectors', 0], 'msg': "Value error, selector member 'alias' carr...
10 failed, 2 passed in 1.85s
```

The two passes were the schema-only shape and the idempotency check, both already true. Post-change: `91 passed` for body-shape + rest_transport + selectors.

`tests/seam/test_refusal_catalogue.py`, pre-change (RED, commit 4cc7a19):

```
Extra items in the left set: 'NoRawUploadPathForModalityError' 'UnknownTraceReferenceError' 'UnresolvableEvidenceReferenceError' 'UnbudgetableParticipantError'
AttributeError: module 'databasise.seam.refusals' has no attribute 'UnknownTraceReferenceError' (x3 for the moved classes)
4 failed, 1 passed
```

Post-change: all pass.

## Verification

- `pytest -q tests/seam tests/mcp tests/parts_core`: 518 passed, 1 skipped.
- `pytest -q tests/launcher`: 68 passed.
- Task acceptance greps all return the expected lines; `COVERAGE.md` grep count is 1.

## Deviations from Plan

**1. [Rule 1 - cleanup] Dropped now-unused `SeamRefusalError` imports** from `evidence.py`, `trace_store.py`, `tokens.py` after the classes moved (the plan said "replace each class body with an import"; the base-class import became dead).
- Files modified: `databasise/seam/evidence.py`, `trace_store.py`, `tokens.py`. Commit 8f566a0.

**2. TDD sequencing for Task 2:** committed the RED test alone (4cc7a19) before the GREEN commit, per tdd.md; the plan listed one commit per task. Total commits: 3.

**Total deviations:** 2 minor, no behavioural impact.

## Known Stubs

None.

## Threat Flags

None. T-09-01 and T-09-02 mitigated: the oversized-text response is asserted under 4096 bytes and FastAPI's default 422 (which echoes `input`) is no longer reached for refusal-bearing errors.

## Issues Encountered

- A heredoc `python3` file-edit command was blocked by the BAK check-edit hook (it named an unrelated protected file); redone with the Edit tool. No protected file was edited.
- `ruff check` reports pre-existing style findings (import sort, `__all__` sort, B008) in touched files; left as out of scope.

## Self-Check: PASSED

Created files exist (both new test files, `COVERAGE.md`); commits 5a816f6, 4cc7a19, 8f566a0 are on `main`.
