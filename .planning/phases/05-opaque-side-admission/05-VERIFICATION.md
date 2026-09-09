---
phase: 05-opaque-side-admission
verified: 2026-09-09T00:00:00Z
status: passed
score: 7/7 must-haves verified
covered_files:
  - ".planning/REQUIREMENTS.md"
  - ".planning/ROADMAP.md"
  - ".planning/phases/05-opaque-side-admission/05-01-PLAN.md"
  - ".planning/phases/05-opaque-side-admission/05-01-SUMMARY.md"
  - ".planning/phases/05-opaque-side-admission/05-02-PLAN.md"
  - ".planning/phases/05-opaque-side-admission/05-02-SUMMARY.md"
  - ".planning/phases/05-opaque-side-admission/05-03-PLAN.md"
  - ".planning/phases/05-opaque-side-admission/05-03-SUMMARY.md"
  - ".planning/phases/05-opaque-side-admission/05-04-PLAN.md"
  - ".planning/phases/05-opaque-side-admission/05-04-SUMMARY.md"
  - ".planning/phases/05-opaque-side-admission/05-05-PLAN.md"
  - ".planning/phases/05-opaque-side-admission/05-05-SUMMARY.md"
  - ".planning/phases/05-opaque-side-admission/05-06-PLAN.md"
  - ".planning/phases/05-opaque-side-admission/05-06-SUMMARY.md"
  - ".planning/phases/05-opaque-side-admission/05-07-PLAN.md"
  - ".planning/phases/05-opaque-side-admission/05-07-SUMMARY.md"
  - ".planning/phases/05-opaque-side-admission/05-08-PLAN.md"
  - ".planning/phases/05-opaque-side-admission/05-08-SUMMARY.md"
  - ".planning/phases/05-opaque-side-admission/05-09-PLAN.md"
  - ".planning/phases/05-opaque-side-admission/05-09-SUMMARY.md"
  - ".planning/phases/05-opaque-side-admission/05-PATTERNS.md"
  - ".planning/phases/05-opaque-side-admission/05-RESEARCH.md"
  - ".planning/phases/05-opaque-side-admission/05-REVIEW.md"
  - ".planning/phases/05-opaque-side-admission/05-VALIDATION.md"
  - ".planning/phases/05-opaque-side-admission/COVERAGE.md"
  - "databasise/mcp/server.py"
  - "databasise/mcp/tools.py"
  - "databasise/seam/engine.py"
  - "databasise/seam/refusals.py"
  - "databasise/tests/mcp/test_dual_transport_parity.py"
  - "databasise/tests/parts_core/lightrag/test_full_ingest.py"
  - "databasise/tests/seam/test_delete_document.py"
  - "databasise/tests/seam/test_rest_transport.py"
covered_digest: "v1:sha256:ac56c08b0f9ea5ae871b5be22c380788efb1992c348bfa3f31282b2198335c28"
re_verification:
  previous_status: gaps_found
  previous_score: 5/7
  gaps_closed:
    - "Truth 6: Databasise.ingest()/delete_document() no longer fabricate a success/causeless-fail on an unclassified node failure — both now raise ForeignEngineRefusalError carrying the real cause (G-05-1 / CR-02 / WR-01, closed by 05-08-PLAN.md)"
    - "Truth 7: the MCP status/ingest tools no longer crash with the SDK's generic UnexpectedToolError on a page-cap violation or malformed raw_base64 — both refuse by name, matching REST (G-05-2 / CR-01a / CR-01b, closed by 05-09-PLAN.md)"
  gaps_remaining: []
  regressions: []
---

# Phase 5: Opaque-Side Admission Verification Report

**Phase Goal:** The entangled ingest side is admitted under the contract's opaque conditions rather than smuggled in, and callers can feed and inspect the corpus (§BP rung 3)
**Verified:** 2026-09-09
**Status:** passed
**Re-verification:** Yes — after gap closure (05-08-PLAN.md, 05-09-PLAN.md)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | LightRAG's ~1,786-line ingest core runs as an admitted opaque node in `quarantined` scope, with a written boundary rule a compat test enforces, and DR-04 decided either way | ✓ VERIFIED (regression check) | Unchanged by 05-08/05-09; `evidence/DR-04-DECISION.md` and `evidence/INJECTED-LLM-ENDPOINT-SURVEY.md` still present; `LIGHTRAG_FULL_INGEST_PART.artifact_scope='quarantined'` still enforced in `parts_core/lightrag/full_ingest.py`; full suite includes `test_full_ingest_compat.py` passing |
| 2 | codebase-memory-mcp admitted whole-engine, eleven §17/§8 verdicts recorded (three not-clean-yeses), backed by the five-engine survey, Falsifier 4 run twice with disposition recorded either way | ✓ VERIFIED (regression check) | Unchanged by 05-08/05-09; `grep -c ConditionVerdict parts_core/codebase_memory_mcp.py` = 12 (11 verdicts + import); files untouched by either gap-closure plan |
| 3 | Caller uploads a document, polls the job to completion, then deletes it — shared entities cleaned up, survivors not orphaned | ✓ VERIFIED | Happy-path tests pass; the reliability gap this criterion's implicit guarantee depended on (truth 6) is now closed — see below |
| 4 | Caller reads health, corpus status, document counts bounded/paginated; a full corpus or index dump is never returned | ✓ VERIFIED (regression check) | `seam/corpus.py`: `MAX_PAGE_SIZE = 100`, `Page.limit > MAX_PAGE_SIZE` raises `PageSizeExceededError` before construction; unchanged by 05-08, and 05-09 added a second, transport-local enforcement point on the MCP side rather than weakening this one |
| 5 | MCP surface exposes the same capabilities as REST as intention-level tools; no selector-expressible capability becomes a tool; adding a modality adds no tool | ✓ VERIFIED | `TOOL_NAMES = ("ingest", "query", "delete", "status", "resolve")` unchanged (confirmed empty diff on the tuple across 05-09's commits per its own SUMMARY); `test_tool_growth_invariant.py` passes; the prior behavioral divergence (crash vs. refuse) that undermined "same capabilities" is now closed — see truth 7 |
| 6 | `Databasise.ingest()`/`delete_document()` never return a fabricated success or a causeless failure when the underlying subprocess actually failed | ✓ VERIFIED | Re-reproduced independently in this pass (not accepted from 05-08-SUMMARY.md's own claims): monkeypatched `DEFAULT_V1_INTERPRETER` to a nonexistent path and called both methods directly — `engine.ingest(...)` now prints `REFUSED: ingest MissingV1InterpreterError`; `engine.delete_document(...)` now prints `REFUSED: delete MissingV1InterpreterError`. Read `databasise/seam/engine.py`'s `_node_result_or_refuse` (lines 277-303) directly: it raises on any `node_exceptions` entry (no `isinstance` narrowing) and on a missing `results` entry, used identically by both `ingest()` (line 549) and `delete_document()` (line 612). Confirmed `not_found`/`not_allowed` still return as normal `DeletionOutcome` (not a refusal) by reading and running `test_a_not_allowed_status_from_the_driver_surfaces_unchanged_never_remapped_or_raised` and `test_deleting_the_same_document_twice_yields_success_then_not_found` — both pass |
| 7 | The MCP transport maps a page-cap violation and malformed base64 to the same clean refusal REST returns for the identical operation | ✓ VERIFIED | Re-reproduced independently in this pass: live `server.call_tool("status", {"args": {"scope": "corpus", "limit": 999999}})` now raises a mapped `ToolError` with `refusal_type="PageSizeExceededError", requested=999999, limit=100` (printed `page-cap ok`); live `server.call_tool("ingest", {"args": {"raw_base64": "not-valid-base64!!!", ...}})` now raises a mapped `ToolError` with `refusal_type="MalformedBase64PayloadError"` (printed `malformed-base64 ok`). Read `mcp/server.py`'s `_checked_page` (raises before `Page(...)` construction, one construction site in the module) and `mcp/tools.py`'s `to_ingest_document` (catches only `binascii.Error`, re-raises `MalformedBase64PayloadError`) directly. Ran `test_the_page_cap_boundary_separates_rather_than_clamps_over_both_transports` — confirms `MAX_PAGE_SIZE` succeeds and `MAX_PAGE_SIZE + 1` refuses by name on both REST and MCP |

**Score:** 7/7 truths verified (both prior failures independently reproduced as fixed against live code, not accepted from SUMMARY claims)

### Deferred / Explicitly Out-of-Scope Items (not gaps)

| Item | Status | Reason |
|---|---|---|
| WR-02 — `codebase_memory_mcp_body` forwards an unchecked `tool` name | Deferred, unreachable | No shipped wiring declares a `config` block for this part, so the guard's existing `if not tool_name` already refuses every currently-wired call. Confirmed unchanged in `parts_core/codebase_memory_mcp.py`. Trigger: the first wiring declaring `config` for this part (05-08-PLAN.md's own written deferral, expected Phase 6). |
| IN-02 — `IngestDocument(...)` construction still loses its refusal shape to a wrapped `ValidationError` in both transports | Deferred, both-transports symmetric | Not a parity divergence (REST has the identical shape), so out of gap G-05-2's mandate. Written deferral with a named trigger in 05-09-PLAN.md ("raise it in the Phase 6 review, or the next time either transport's ingest path is opened"). |
| 05-VALIDATION.md still carries template placeholders | Deferred | Non-gating (no roadmap success criterion depends on this file); `/gsd-validate-phase 5` is the named trigger, not yet run. Confirmed still `status: draft` in this pass. |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/seam/engine.py` | Shared no-result-is-a-refusal helper for both write operations | ✓ VERIFIED | `_node_result_or_refuse` present at line 277, called at line 549 (`ingest`) and line 612 (`delete_document`); no `isinstance` type test remains in either method's own body (confirmed via `inspect.getsource` grep-equivalent read) |
| `databasise/mcp/server.py` | Page pre-check mirroring REST's `_checked_page` | ✓ VERIFIED | `_checked_page` at line 106, raises `PageSizeExceededError` before `Page(...)` construction; `_status_job`/`_status_corpus` both route through it; no `fastapi` or `databasise.seam.rest` import present |
| `databasise/mcp/tools.py` | Base64 decode failure raises a named refusal | ✓ VERIFIED | `to_ingest_document` catches `binascii.Error`, re-raises `MalformedBase64PayloadError(field="raw_base64")` |
| `databasise/seam/refusals.py` | New refusal subclass for undecodable payload | ✓ VERIFIED | `MalformedBase64PayloadError(SeamRefusalError)` present, stores only `field`, never the payload content |
| `databasise/tests/parts_core/lightrag/test_full_ingest.py` | Committed reproduction of the ingest fabricated-success defect | ✓ VERIFIED | `test_an_unclassified_node_failure_through_ingest_raises_rather_than_fabricating_a_job` and `test_a_node_that_produced_neither_a_result_nor_an_exception_still_refuses` both present and pass |
| `databasise/tests/seam/test_delete_document.py` | Committed reproduction of the delete causeless-fail defect | ✓ VERIFIED | `test_an_unclassified_node_failure_through_delete_document_raises_rather_than_a_causeless_fail` present and passes |
| `databasise/tests/mcp/test_dual_transport_parity.py` | Dual-transport parity coverage for both reproduced edge cases | ✓ VERIFIED | `test_a_page_cap_violation_refuses_by_name_over_mcp_exactly_as_it_does_over_rest`, `test_the_page_cap_boundary_separates_rather_than_clamps_over_both_transports`, `test_a_malformed_raw_base64_refuses_by_name_rather_than_crashing_the_tool` all present and pass |
| `databasise/tests/seam/test_rest_transport.py` | New refusal registered in the transitive subclass factory map | ✓ VERIFIED | `MalformedBase64PayloadError` imported and present in `_REFUSAL_FACTORIES`; parametrized 422 proof covers it |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `seam/engine.py::ingest()` | `_node_result_or_refuse` | Direct call, both write operations | ✓ WIRED | Confirmed by source read and by both new regression tests passing |
| `mcp/server.py::_status_job/_status_corpus` | `_checked_page` | Direct call | ✓ WIRED | Confirmed by source read; `Page(...)` construction count in the module is exactly 1 (inside the helper) |
| `mcp/tools.py::to_ingest_document` | `MalformedBase64PayloadError` | `except binascii.Error: raise ... from exc` | ✓ WIRED | Confirmed by source read and live reproduction |
| `MalformedBase64PayloadError` | `test_rest_transport.py`'s transitive subclass walk | `_REFUSAL_FACTORIES` entry | ✓ WIRED | Confirmed present; parametrized test passes for this class |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite (rest+mcp extras) | `cd databasise && uv run --extra rest --extra mcp pytest -q` | 745 passed, 1 skipped | ✓ PASS |
| Import boundary | `cd databasise && uv run python -m databasise.tools.check_import_boundary` | exit 0 | ✓ PASS |
| G-05-1 reproduction (ingest) | Live Python: `DEFAULT_V1_INTERPRETER` pointed at nonexistent path, `await engine.ingest(...)` | `REFUSED: ingest MissingV1InterpreterError` | ✓ PASS (fix confirmed) |
| G-05-1 reproduction (delete) | Live Python: same interpreter override, `await engine.delete_document(...)` | `REFUSED: delete MissingV1InterpreterError` | ✓ PASS (fix confirmed) |
| G-05-2 reproduction (page cap) | Live Python: `server.call_tool("status", {"args": {"scope": "corpus", "limit": 999999}})` | Mapped `ToolError`, `refusal_type="PageSizeExceededError"` | ✓ PASS (fix confirmed) |
| G-05-2 reproduction (malformed base64) | Live Python: `server.call_tool("ingest", {"args": {"raw_base64": "not-valid-base64!!!", ...}})` | Mapped `ToolError`, `refusal_type="MalformedBase64PayloadError"` | ✓ PASS (fix confirmed) |
| New regression tests | `pytest -k "unclassified_node_failure or neither_a_result_nor_an_exception"` (test_full_ingest.py, test_delete_document.py) | 3 passed | ✓ PASS |
| New parity tests | `pytest -k "page_cap or malformed_raw_base64"` (test_dual_transport_parity.py) | 3 passed | ✓ PASS |
| not_found/not_allowed distinction preserved | `pytest tests/seam/test_delete_document.py` (full file) | 6 passed, 1 skipped (opt-in real-delete leg) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| MODAL-02 | 05-01, 05-03, 05-05 | LightRAG ingest core admitted opaque, quarantined scope, boundary rule + compat test | ✓ SATISFIED | Truth 1; unchanged by gap closure |
| MODAL-03 | 05-06 | codebase-memory-mcp admitted whole-engine, 11 verdicts, Falsifier 4 twice | ✓ SATISFIED | Truth 2; unchanged by gap closure |
| MACH-04 | 05-02 | Injected-LLM-endpoint survey, five engines, non-gating | ✓ SATISFIED | `INJECTED-LLM-ENDPOINT-SURVEY.md` present; unchanged |
| API-01 | 05-01, 05-04, 05-08 | Ingest + async job status polling | ✓ SATISFIED | Truth 6 closed — no more fabricated success on subprocess failure |
| API-02 | 05-03, 05-08 | Delete with graph-aware cleanup | ✓ SATISFIED | Truth 6 (delete half) closed — no more causeless fail |
| API-06 | 05-04 | Bounded health/corpus/counts, never a full dump | ✓ SATISFIED | Truth 4; unchanged by gap closure |
| API-07 | 05-07, 05-09 | MCP intention-level tool parity with REST | ✓ SATISFIED | Truth 7 closed — MCP refuses by name where it used to crash |
| HARD-03 | 05-02 | DR-04 decided | ✓ SATISFIED | `DR-04-DECISION.md` present; unchanged |

No orphaned requirements — all 8 phase requirement IDs declared across the plans (including the two gap-closure plans) match REQUIREMENTS.md's Phase 5 mapping exactly.

**Documentation staleness found and flagged (non-gating):** `.planning/REQUIREMENTS.md`'s traceability table currently shows `MACH-04`, `MODAL-02`, `MODAL-03`, `API-06`, and `HARD-03` as `Gaps Found`, and their checkboxes as unchecked. This is stale: commit `7c5b9f1` reverted all 8 Phase-5 requirement rows from `Complete` to `Gaps Found` en masse when the initial verification found gaps_found status for the *phase*, but the initial verification's own per-requirement assessment (05-VERIFICATION.md, prior version) marked these five `✓ SATISFIED` with **no** defect noted — only API-01, API-02, and API-07 carried the two actual defects. Follow-up commits `117cf2f` and `1922d2a` correctly restored API-01/API-02/API-07 to `Complete` after their gap-closure plans landed, but the other five rows were never restored, even though nothing about them was ever broken. Re-confirmed in this pass that the underlying code for all five is untouched by 05-08/05-09 and still substantively present (DR-04-DECISION.md, the 11-verdict admission records, MAX_PAGE_SIZE enforcement, the injected-LLM survey). **Recommend:** flip `MACH-04`, `MODAL-02`, `MODAL-03`, `API-06`, `HARD-03` to `[x]`/`Complete` in `.planning/REQUIREMENTS.md` to match their actual (unbroken) state — a documentation fix, not a code change.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `.planning/REQUIREMENTS.md` | traceability table | Five Phase-5 requirement rows stuck at stale `Gaps Found` after mass revert, never restored despite never having been individually defective | ⚠️ Warning | Traceability document inaccuracy; no functional impact — see Requirements Coverage section above for full explanation and recommendation |
| `databasise/parts_core/codebase_memory_mcp.py` | ~304-316 | `tool`/`arguments` forwarded to `call_tool` with no check against `CBM_KNOWN_TOOL_NAMES` (WR-02) | ⚠️ Warning | Not reachable through any currently-wired path; explicitly deferred with a named trigger in 05-08-PLAN.md |
| `databasise/mcp/tools.py` / `databasise/seam/rest.py` | `to_ingest_document()` / `POST /documents/upload` route | `IngestDocument(...)` construction still loses its refusal shape to a wrapped `pydantic.ValidationError` (IN-02) in both transports symmetrically | ⚠️ Warning | Not a parity divergence (identical in both transports); explicitly deferred with a named trigger in 05-09-PLAN.md |
| `.planning/phases/05-opaque-side-admission/05-VALIDATION.md` | whole file | Still template placeholders (`status: draft`) | ℹ️ Info | Process artifact only — no roadmap success criterion depends on this file; named trigger (`/gsd-validate-phase 5`) recorded, not yet run |

No `TBD`/`FIXME`/`XXX` debt markers found in any phase-5-touched file (including the two gap-closure plans' changed files).

## Human Verification Required

None. Every observable truth for this phase resolves through code inspection, live reproduction, or the existing automated test suite — no visual, real-time, or external-service behavior is in scope.

## Gaps Summary

Both BLOCKER gaps from the prior verification pass are closed, each independently re-reproduced against the live code in this pass (not accepted from either gap-closure plan's own SUMMARY claims):

1. **G-05-1 / CR-02 / WR-01 — closed.** `Databasise.ingest()` and `Databasise.delete_document()` now route through a single shared `_node_result_or_refuse` helper in `databasise/seam/engine.py` that raises `ForeignEngineRefusalError` (carrying the real exception on `.cause`) for any recorded node exception or missing result — never a fabricated `IngestJob` and never a causeless `DeletionOutcome(status="fail")`. Independently reproduced live in this pass: pointing `DEFAULT_V1_INTERPRETER` at a nonexistent path now raises the refusal from both methods (previously: silent fabricated success from `ingest()`, causeless fail from `delete_document()`). A `not_found`/`not_allowed` status v1 itself reports is confirmed still a normal, non-refused `DeletionOutcome`.
2. **G-05-2 / CR-01a / CR-01b — closed.** The MCP `status` tool now refuses a page-cap violation with the same named `PageSizeExceededError` REST returns (via a new `_checked_page` pre-check in `databasise/mcp/server.py`, mirroring REST's own pattern, raised before `Page(...)` construction); the `ingest` tool now refuses a malformed `raw_base64` with a new named `MalformedBase64PayloadError` instead of letting `binascii.Error` escape as the SDK's generic `UnexpectedToolError`. Independently reproduced live in this pass: both calls now raise a mapped `ToolError` with the correct `refusal_type`. The `MAX_PAGE_SIZE`/`MAX_PAGE_SIZE + 1` boundary is confirmed non-clamping on both sides of both transports.

The full test suite passes at 745/1 (up from the phase's 738/1 baseline by exactly 7 new tests: 3 in `test_full_ingest.py`+`test_delete_document.py`, 3 in `test_dual_transport_parity.py`, 1 in `test_rest_transport.py`'s parametrization). The incremental code review (`05-REVIEW.md`) independently confirmed the same four findings resolved with no new defects introduced. No later milestone phase's goal addresses either defect (neither was deferrable), and none of the deferred lower-severity items (WR-02, IN-02, 05-VALIDATION.md's template) block this phase's own success criteria.

One non-gating documentation finding is flagged for correction: `.planning/REQUIREMENTS.md`'s traceability table still marks five never-actually-defective Phase-5 requirements (`MACH-04`, `MODAL-02`, `MODAL-03`, `API-06`, `HARD-03`) as `Gaps Found`, left over from a mass revert that predates this gap-closure wave. This is a tracking-document staleness issue, not a code or test defect — recommended fix noted above, not required to close this phase.

All five ROADMAP success criteria for Phase 5 hold against the current codebase, including criterion 5 (MCP surface parity with REST), which G-05-2 directly bore on and which is now confirmed closed.

---

_Verified: 2026-09-09_
_Verifier: Claude (gsd-verifier)_
