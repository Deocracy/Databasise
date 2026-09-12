---
phase: 05-opaque-side-admission
plan: 09
subsystem: api
tags: [mcp, rest, refusals, pydantic, gap-closure]

# Dependency graph
requires:
  - phase: 05-opaque-side-admission
    provides: "05-07's MCP transport (databasise/mcp/server.py, mcp/tools.py) and 05-04's REST _checked_page pattern (databasise/seam/rest.py)"
provides:
  - "databasise/mcp/server.py's own _checked_page pre-check, closing the page-cap crash-vs-refuse divergence between MCP and REST"
  - "MalformedBase64PayloadError (databasise/seam/refusals.py) — a named refusal for an undecodable raw_base64 argument"
  - "Dual-transport parity test coverage for both reproduced edge cases plus the page-cap boundary"
affects: [phase-06-review, api-07-mcp-parity]

# Actuals (#2632)
actuals:
  tokens: 3520
  tasks: 2
  commits: 2

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Transport-local _checked_page pre-check mirroring rest.py's own pattern, never importing across the fastapi boundary"
    - "Named refusal raised directly (not inside a pydantic validator) needs no embedded-class-name workaround in its message"

key-files:
  created: []
  modified:
    - databasise/mcp/server.py
    - databasise/mcp/tools.py
    - databasise/seam/refusals.py
    - databasise/tests/mcp/test_dual_transport_parity.py
    - databasise/tests/seam/test_rest_transport.py

key-decisions:
  - "IN-02 (IngestDocument(...) construction inside a transport body losing its wrapped-ValidationError shape, present in both mcp/tools.py and rest.py identically) deferred per the plan's own scope-decision section — it is a both-transports defect, not a parity divergence, and outside gap G-05-2's mandate."
  - "MalformedBase64PayloadError lives in databasise/seam/refusals.py, not in the MCP transport, so REST's transitive SeamRefusalError subclass walk discovers it regardless of which extras are installed in a given test run."

patterns-established:
  - "A refusal raised directly (never inside a pydantic model_validator) does not need its class name embedded in its own message text — only PageSizeExceededError/AmbiguousIngestPayloadError need that workaround, because pydantic wraps their ValueError into a ValidationError at construction and loses the original exception object."

requirements-completed: [API-07]

coverage:
  - id: D1
    description: "A page-cap violation (status tool, scope=corpus and scope=job) refuses by name over MCP exactly as REST's GET /corpus already does, compared value-for-value across both transports; the MAX_PAGE_SIZE boundary is proven non-clamping on both sides of both transports."
    requirement: "API-07"
    verification:
      - kind: integration
        ref: "databasise/tests/mcp/test_dual_transport_parity.py#test_a_page_cap_violation_refuses_by_name_over_mcp_exactly_as_it_does_over_rest"
        status: pass
      - kind: integration
        ref: "databasise/tests/mcp/test_dual_transport_parity.py#test_the_page_cap_boundary_separates_rather_than_clamps_over_both_transports"
        status: pass
    human_judgment: false
  - id: D2
    description: "A malformed raw_base64 argument to the ingest tool refuses by name (MalformedBase64PayloadError) through the shared mapper instead of crashing as UnexpectedToolError; the well-formed base64 path is unmodified; the new refusal is registered in test_rest_transport.py's transitive-subclass factory map."
    requirement: "API-07"
    verification:
      - kind: integration
        ref: "databasise/tests/mcp/test_dual_transport_parity.py#test_a_malformed_raw_base64_refuses_by_name_rather_than_crashing_the_tool"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_rest_transport.py#test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value[MalformedBase64PayloadError]"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-09-09
status: complete
---

# Phase 5 Plan 9: MCP transport refuses page-cap and malformed-base64 the way REST already does

**Mirrored `rest.py`'s `_checked_page` into `mcp/server.py` and added a named `MalformedBase64PayloadError`, closing gap G-05-2's two reproduced MCP-vs-REST parity crashes with dual-transport tests proving both.**

## Performance

- **Duration:** ~40 min
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- `databasise/mcp/server.py` now has its own `_checked_page(limit, offset)` helper, placed right after `_refusal_mapped`, raising `PageSizeExceededError(requested=limit, limit=MAX_PAGE_SIZE)` directly — never via `Page(...)`'s own constructor, which would let pydantic wrap the refusal into an unmatched `ValidationError`. `_status_job` and `_status_corpus` both route through it; `_status_counts`/`_status_health` are explicitly left unchecked (they take no page, matching REST's own parameter-free routes for the same two operations), with a comment recording why so a later reader does not "fix" the asymmetry.
- Added `MalformedBase64PayloadError(SeamRefusalError)` to `databasise/seam/refusals.py` — a keyword-only `field: str` refusal naming only the caller's input slot, never the rejected payload's content. `IngestToolArgs.to_ingest_document()` (`databasise/mcp/tools.py`) now wraps only the `base64.b64decode` call in `try/except binascii.Error`, re-raising the new refusal chained from the original; the `IngestDocument(...)` construction on the next line is untouched (that's IN-02, deferred — see Decisions).
- Registered the new refusal's factory in `databasise/tests/seam/test_rest_transport.py`'s `_REFUSAL_FACTORIES`, keeping the transitive `SeamRefusalError` subclass walk (`test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value`) complete — a missing entry there would have failed loudly the moment the new subclass landed.
- Added three new tests to `databasise/tests/mcp/test_dual_transport_parity.py`: the page-cap violation reproduced over MCP and compared value-for-value against REST's `GET /corpus?limit=999999` (both `scope="corpus"` and `scope="job"` legs); the `MAX_PAGE_SIZE`/`MAX_PAGE_SIZE + 1` boundary proven non-clamping on both sides of both transports; and the malformed-`raw_base64` reproduction over the `ingest` tool, including the well-formed base64 round trip staying unmodified.
- Both live reproductions from 05-VERIFICATION.md's behavioural spot-check table (`status` with `limit=999999`, `ingest` with malformed `raw_base64`) now print `ok` instead of raising `UnexpectedToolError`, confirmed by direct `server.call_tool(...)` calls against the live code (not merely via the test suite).

## Task Commits

1. **Task 1: Tracer — a page-cap violation refuses by name over MCP, end to end** - `cf83fe6` (feat)
2. **Task 2: The malformed-payload refusal, and the subclass parametrization kept complete** - `17dfa65` (feat)

**Plan metadata:** committed separately by the orchestrator after wave merge (worktree mode — STATE.md/ROADMAP.md are not touched by this plan).

## Files Created/Modified

- `databasise/mcp/server.py` - Added `_checked_page`; routed `_status_job`/`_status_corpus` through it; added `MAX_PAGE_SIZE`/`PageSizeExceededError` imports.
- `databasise/mcp/tools.py` - `to_ingest_document()` catches `binascii.Error` around the decode, re-raising `MalformedBase64PayloadError(field="raw_base64")`.
- `databasise/seam/refusals.py` - Added `MalformedBase64PayloadError(SeamRefusalError)` and its `__all__` entry.
- `databasise/tests/mcp/test_dual_transport_parity.py` - Added `MAX_PAGE_SIZE` import and three new tests (page-cap parity, page-cap boundary, malformed-base64 parity).
- `databasise/tests/seam/test_rest_transport.py` - Added `MalformedBase64PayloadError` import and its `_REFUSAL_FACTORIES` entry.

## Decisions Made

- **IN-02 deferred, per the plan's own written scope decision.** `IngestToolArgs.to_ingest_document()`'s `IngestDocument(...)` construction (the line immediately after the now-guarded decode) has the identical wrapped-`ValidationError`-escapes-as-`UnexpectedToolError` shape — but `databasise/seam/rest.py`'s `POST /documents/upload` route constructs `IngestDocument(...)` the same unguarded way, so both transports mishandle it identically. Closing it is a both-transports fix to `rest.py` and `mcp/tools.py`, not a parity repair, and is out of gap G-05-2's mandate (whose subject is a divergence between the two transports). Left exactly as-is, with the plan's own trigger recorded: raise it in the Phase 6 review, or the next time either transport's ingest path is opened.
- **`MalformedBase64PayloadError` placed in the seam, not the MCP transport** — so REST's transitive `SeamRefusalError` subclass walk discovers it regardless of which optional extras are installed in a given test run, and so both transports could in principle map it generically through their one shared refusal-to-response mapper (REST currently has no base64-ingest shape to reach it through, but the type lives where the vocabulary is owned).
- **No `validate=True` added to `base64.b64decode`.** Confirmed empirically that the reproduction string (`"not-valid-base64!!!"`) already raises `binascii.Error` under the decoder's default (non-strict) mode via its padding check — adding `validate=True` would be an unrequested behavior change to the well-formed-but-loosely-encoded input space, not required to close this gap.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Docstring text literally matched an acceptance-criteria grep pattern**
- **Found during:** Task 1
- **Issue:** `_checked_page`'s first-draft docstring explained the mechanism using the literal substring `Page(limit=limit, offset=offset)`, which made `grep -v '^\s*#' mcp/server.py | grep -cE 'Page\(limit='` return 2 instead of the required 1 (the acceptance criterion excludes `#`-comment lines but not docstring prose).
- **Fix:** Reworded the docstring to describe the same mechanism without literally reproducing the constructor call shape.
- **Files modified:** `databasise/mcp/server.py`
- **Verification:** `grep -v '^\s*#' mcp/server.py | grep -cE 'Page\(limit='` now returns exactly 1.
- **Committed in:** `cf83fe6` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 1).
**Impact on plan:** Cosmetic self-correction during authoring; no behavioral change, no scope creep.

## Issues Encountered

- **Pre-existing environment gap, not caused by this plan's changes.** This worktree has no `v1/.venv` and no `v1/.parity_working_dir` built (both are large, gitignored artifacts built once outside git, not present in a freshly-checked-out parallel worktree). The plan's own `<verify>` block asserts "fewer than 738 tests reported passed" would signal a regression; this worktree's full-extras run reports 731 passed, 12 skipped (vs. 05-VERIFICATION.md's recorded 738 passed, 1 skipped in an environment that had those artifacts built). All 12 skips are `v1`-build-dependent tests unrelated to `databasise/mcp/`, `databasise/seam/refusals.py`, or either changed test file — confirmed by reading each skip reason (`v1-built index not found`, `v1/.venv/bin/python not built`, `imported v2 parity store not found`, plus the pre-existing opt-in real-deletion skip). No test that exercises this plan's own changes was skipped; every test in `tests/mcp/` (27/27) and `tests/seam/test_rest_transport.py` (26/26) passed, and the full suite reports zero failures. This is an out-of-scope, pre-existing worktree/environment characteristic (Scope Boundary), not a regression from this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Gap G-05-2 (05-VERIFICATION.md's failed truth 7 / 05-REVIEW.md CR-01a and CR-01b) is closed: both live reproductions now refuse by name over MCP, matching REST's own refusal shape, proven by dual-transport parity tests that fail if the fix is reverted.
- `TOOL_NAMES` and `COVERAGE.md`'s §18.5 operations table are unchanged — confirmed by an empty diff on `mcp/tools.py`'s `TOOL_NAMES` tuple across both commits.
- IN-02 (the shared `IngestDocument(...)` wrapped-`ValidationError` escape in both transports) is a written, evidenced deferral with a named trigger — worth surfacing explicitly in the Phase 6 review per the plan's own instruction.
- CR-02/WR-01 (`Databasise.ingest()`/`delete_document()` fabricating success or losing cause on an unclassified subprocess failure) remain the other open item from 05-VERIFICATION.md's gap list — out of this plan's scope (gap G-05-2 covers only the MCP transport-parity gap), still pending a separate gap-closure plan.

---
*Phase: 05-opaque-side-admission*
*Completed: 2026-09-09*

## Self-Check: PASSED

- `databasise/mcp/server.py` — FOUND
- `databasise/seam/refusals.py` — FOUND
- `.planning/phases/05-opaque-side-admission/05-09-SUMMARY.md` — FOUND
- Commits `cf83fe6`, `17dfa65`, `1922d2a` — all present in `git log --oneline --all --grep="05-09"`
