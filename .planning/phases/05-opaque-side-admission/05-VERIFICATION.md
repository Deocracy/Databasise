---
phase: 05-opaque-side-admission
verified: 2026-09-08T00:00:00Z
status: gaps_found
score: 5/7 must-haves verified
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
  - ".planning/phases/05-opaque-side-admission/05-PATTERNS.md"
  - ".planning/phases/05-opaque-side-admission/05-RESEARCH.md"
  - ".planning/phases/05-opaque-side-admission/05-REVIEW.md"
  - ".planning/phases/05-opaque-side-admission/05-VALIDATION.md"
  - ".planning/phases/05-opaque-side-admission/COVERAGE.md"
  - "databasise/evidence/ADMISSION-CODEBASE-MEMORY-MCP.md"
  - "databasise/evidence/DR-04-DECISION.md"
  - "databasise/evidence/FALSIFIER-4-EVIDENCE.md"
  - "databasise/evidence/INJECTED-LLM-ENDPOINT-SURVEY.md"
  - "databasise/foreign/__init__.py"
  - "databasise/foreign/codebase_memory_mcp_adapter.py"
  - "databasise/foreign/v1_corpus_adapter.py"
  - "databasise/foreign/v1_corpus_driver_script.py"
  - "databasise/mcp/__init__.py"
  - "databasise/mcp/server.py"
  - "databasise/mcp/tools.py"
  - "databasise/parts/admission.py"
  - "databasise/parts/registry.py"
  - "databasise/parts/schema.py"
  - "databasise/parts_core/codebase_memory_mcp.py"
  - "databasise/parts_core/declared_only.py"
  - "databasise/parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md"
  - "databasise/parts_core/lightrag/__init__.py"
  - "databasise/parts_core/lightrag/full_delete.py"
  - "databasise/parts_core/lightrag/full_ingest.py"
  - "databasise/pyproject.toml"
  - "databasise/runner/scheduler.py"
  - "databasise/seam/corpus.py"
  - "databasise/seam/engine.py"
  - "databasise/seam/refusals.py"
  - "databasise/seam/rest.py"
  - "databasise/tests/evidence/__init__.py"
  - "databasise/tests/evidence/test_admission_docs.py"
  - "databasise/tests/evidence/test_falsifier4_evidence.py"
  - "databasise/tests/fixtures/v1_corpus_driver_stub.py"
  - "databasise/tests/mcp/test_dual_transport_parity.py"
  - "databasise/tests/mcp/test_tool_growth_invariant.py"
  - "databasise/tests/parts/test_admission.py"
  - "databasise/tests/parts_core/lightrag/test_full_delete.py"
  - "databasise/tests/parts_core/lightrag/test_full_ingest.py"
  - "databasise/tests/parts_core/lightrag/test_full_ingest_compat.py"
  - "databasise/tests/parts_core/test_codebase_memory_mcp_admission.py"
  - "databasise/tests/seam/test_corpus_status.py"
  - "databasise/tests/seam/test_delete_document.py"
  - "databasise/tests/seam/test_ingest_job_status.py"
  - "databasise/tests/seam/test_mach11_event.py"
  - "databasise/tests/seam/test_rest_corpus_endpoints.py"
  - "databasise/tests/seam/test_rest_transport.py"
  - "databasise/tools/check_import_boundary.py"
  - "databasise/validator/execution_mode.py"
  - "databasise/wirings/codebase-memory-mcp.json"
  - "databasise/wirings/lightrag/corpus-delete.json"
  - "databasise/wirings/lightrag/corpus-ingest.json"
covered_digest: "v1:sha256:e158db82750833c7e9a7a1a0e99350ee9aa8889de36365256faf81770aab4109"
gaps:
  - truth: "Databasise.ingest() never returns a successful IngestJob when the underlying corpus-side subprocess actually failed"
    status: failed
    reason: >
      databasise/seam/engine.py:512-524 only treats node_exceptions of type
      CorpusOpSubprocessError/CorpusOpTimeoutError as a refusal condition. Any other failure
      (confirmed live with MissingV1InterpreterError by pointing DEFAULT_V1_INTERPRETER at a
      nonexistent path) falls through the isinstance check, finds no entry in results, and the
      method still returns IngestJob(job_id=<minted-track_id>, enqueued=0) as if the ingest had
      succeeded — no exception is raised. Reproduced independently in this verification pass
      (not merely cited from 05-REVIEW.md's CR-02): `RETURNED (no exception): job_id=... enqueued=0`.
      This directly bears on ROADMAP Criterion 3's "polls the job to completion" guarantee — a
      caller who receives this fabricated job handle has no way to detect that ingest never ran.
      No test exercises this path; test_full_ingest.py only covers CorpusOpTimeoutError.
    artifacts:
      - path: "databasise/seam/engine.py"
        issue: "ingest() at lines 512-524 (and the same isinstance pattern in delete_document() at 578-591, WR-01) narrows the refusal condition to two known exception types instead of 'no result was produced'"
    missing:
      - "Invert the check in Databasise.ingest() (and delete_document()) to raise ForeignEngineRefusalError whenever node_exception is not None OR no result entry exists for the node — never fall through to a fabricated success/undifferentiated fail"
      - "A test exercising MissingV1InterpreterError (or another unclassified node failure) through ingest() and asserting ForeignEngineRefusalError is raised, not a fabricated IngestJob"
  - truth: "The MCP transport maps a page-cap violation and a malformed base64 payload to the same clean, mapped refusal REST already returns for the identical operation — never an unhandled crash"
    status: failed
    reason: >
      databasise/mcp/server.py:106-113 constructs Page(limit=args.limit, offset=args.offset)
      directly inside _status_job/_status_corpus rather than through a _checked_page-style
      pre-check; Page's model_validator raises PageSizeExceededError, which pydantic v2 wraps into
      pydantic_core.ValidationError at the construction call site. _refusal_mapped only catches
      SeamRefusalError, so the wrapped ValidationError propagates as the SDK's generic
      UnexpectedToolError. The identical failure mode fires from
      IngestToolArgs.to_ingest_document() for malformed raw_base64 (binascii.Error, also not a
      SeamRefusalError). Reproduced independently in this verification pass against the live code:
      calling the `status` tool with scope=corpus, limit=999999 raised
      `mcp.server.mcpserver.exceptions.UnexpectedToolError`; calling `ingest` with a malformed
      raw_base64 raised the same. REST's equivalent endpoints do not have this bug (_checked_page).
      This is a real, reproduced divergence between the two transports for the same operation,
      undermining ROADMAP Criterion 5's "the MCP surface exposes the same capabilities as REST."
      test_dual_transport_parity.py exercises neither a page-cap violation nor a malformed
      raw_base64 on the MCP transport, so the divergence was untested.
    artifacts:
      - path: "databasise/mcp/server.py"
        issue: "_status_job/_status_corpus (lines ~106-113) build Page(...) directly instead of validating limit against MAX_PAGE_SIZE before construction"
      - path: "databasise/mcp/tools.py"
        issue: "IngestToolArgs.to_ingest_document() (line ~74) calls base64.b64decode without catching binascii.Error into a SeamRefusalError-compatible refusal"
    missing:
      - "A _checked_page-equivalent in databasise/mcp/server.py that raises PageSizeExceededError directly, mirroring databasise/seam/rest.py's own pattern"
      - "A field validator or explicit try/except around the base64 decode that raises a SeamRefusalError subclass instead of letting binascii.Error escape"
      - "Dual-transport-parity test coverage for both edge cases (page-cap violation, malformed raw_base64) so a regression is caught"
---

# Phase 5: Opaque-Side Admission Verification Report

**Phase Goal:** The entangled ingest side is admitted under the contract's opaque conditions rather than smuggled in, and callers can feed and inspect the corpus (§BP rung 3)
**Verified:** 2026-09-08
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | LightRAG's ~1,786-line ingest core runs as an admitted opaque node in `quarantined` scope, with a written boundary rule a compat test enforces, and DR-04 decided either way | ✓ VERIFIED | `LIGHTRAG_FULL_INGEST_ADMISSION`/`LIGHTRAG_FULL_DELETE_ADMISSION` each carry 11 `ConditionVerdict`s, `manifest_source="code-inspected"` (confirmed by direct import); `artifact_scope="quarantined"` enforced by `ForbiddenSharedScopeError` in `parts/admission.py`; `OPAQUE-BOUNDARY-RULE.md` (135 lines) + `test_full_ingest_compat.py` (398 lines, includes `test_the_comparison_has_teeth_a_mutated_part_copy_differs_from_the_pin`) — all pass in full suite; `evidence/DR-04-DECISION.md` selects `two-covering-rationale` explicitly and checks both coverings against live code |
| 2 | codebase-memory-mcp admitted whole-engine, eleven §17/§8 verdicts recorded (three not-clean-yeses), backed by the five-engine survey, Falsifier 4 run twice with disposition recorded either way | ✓ VERIFIED | `CODEBASE_MEMORY_MCP_ADMISSION` carries 11 verdicts (confirmed live): condition 1 = `confirms-the-rule`, condition 3 = `open-question` (network namespace), conditions 7/8/9(counting half) = `machine-side-obligation` — matches the plan's required disposition exactly, none rounded up; ceiling = 120.0s derived from a measured 2.88s cold-start with ~40x margin recorded in-code; `INJECTED-LLM-ENDPOINT-SURVEY.md` carries the five-engine survey; `FALSIFIER-4-EVIDENCE.md` records Leg 1 (native chunking) run for real and Leg 2 (machine chunks) disposition "not runnable as worded," carrying `PARTS.md §X.5`'s finding forward verbatim |
| 3 | Caller uploads a document, polls the job to completion, then deletes it — shared entities cleaned up, survivors not orphaned | ✓ VERIFIED (happy path) | `test_full_ingest.py`, `test_ingest_job_status.py`, `test_delete_document.py` all pass (738/739 in full suite); the opt-in real-deletion leg (`DATABASISE_RUN_REAL_DELETE=1`) was run once against a real 20-doc v1 corpus per 05-03-SUMMARY.md's recorded before/after entity source-set numbers (shared entity `Shirley Temple` reduced, not removed; independently confirmed the test is the suite's "1 skipped" via `pytest -rs`) — **see gap 1 below: the underlying `ingest()` method fabricates success on unclassified subprocess failure, which this criterion's literal happy-path claim does not exercise but its implied reliability does** |
| 4 | Caller reads health, corpus status, document counts bounded/paginated; a full corpus or index dump is never returned | ✓ VERIFIED | `seam/corpus.py`: `Page` validator raises `PageSizeExceededError` above `MAX_PAGE_SIZE=100` before construction succeeds (via REST's `_checked_page`); `DocumentStatusEntry`/`CorpusStatus`/`DocumentCounts`/`HealthReport` are `extra="forbid"` frozen models carrying only identifiers/statuses/counts/timestamps — no content, chunk text, embedding, or graph payload field exists to leak; REST routes `GET /corpus`, `GET /corpus/counts`, `GET /health` confirmed present |
| 5 | MCP surface exposes the same capabilities as REST as intention-level tools; no selector-expressible capability becomes a tool; adding a modality adds no tool | ✓ VERIFIED (tool set / growth invariant) | `TOOL_NAMES = ("ingest", "query", "delete", "status", "resolve")` — five tools, confirmed live; `test_tool_growth_invariant.py`'s `test_registering_a_second_modality_leaves_the_tool_surface_byte_identical` and `test_no_tool_name_or_argument_field_contains_a_forbidden_modality_or_identity_token` both pass; `databasise/mcp/` proven to hold no selector resolution/redaction/envelope assembly via AST walk — **see gap 2 below: the same tools crash rather than cleanly refuse on a page-cap violation / malformed base64, a reproduced behavioral divergence from REST for the identical operation** |
| 6 | (derived) `Databasise.ingest()` never returns a fabricated success when the underlying subprocess actually failed | ✗ FAILED | Reproduced live: pointing `DEFAULT_V1_INTERPRETER` at a nonexistent path and calling `engine.ingest(...)` returns `IngestJob(job_id=..., enqueued=0)` with no exception raised — CR-02, confirmed independently in this pass, not merely cited from 05-REVIEW.md |
| 7 | (derived) The MCP transport maps a page-cap violation and malformed base64 to the same clean refusal REST returns for the identical operation | ✗ FAILED | Reproduced live: `server.call_tool("status", {"args": {"scope": "corpus", "limit": 999999}})` raises `mcp.server.mcpserver.exceptions.UnexpectedToolError`; malformed `raw_base64` on the `ingest` tool raises the same — CR-01, confirmed independently in this pass |

**Score:** 5/7 truths verified (2 failed; both reproduced independently in this verification pass, not merely inherited from the code review)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `databasise/parts/admission.py` | §8 admission record types + refusals | ✓ VERIFIED | 217 lines; `AdmissionRecord`, `ConditionVerdict`, `ForbiddenSharedScopeError`, `cross_check_conditions` all present and exercised by `test_admission.py`/`test_registry.py` |
| `databasise/foreign/v1_corpus_driver_script.py` / `v1_corpus_adapter.py` | §17 foreign-part adapter for LightRAG's corpus side | ✓ VERIFIED | Present, imported, exercised across ingest/delete/status tests |
| `databasise/parts_core/lightrag/full_ingest.py` / `full_delete.py` | Two separate opaque ports, distinct declared effects | ✓ VERIFIED | Both admitted with 11-verdict records; `full_delete.py` declares `artifact_scope=None` (no artifact) vs `full_ingest.py`'s `quarantined` — separate registrations confirmed |
| `databasise/parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md` | Written inside-vs-across-boundary change rule | ✓ VERIFIED | 135 lines; `test_full_ingest_compat.py` pins driver-protocol key sets and part-boundary values, and a mutation test proves the pin has teeth |
| `databasise/parts_core/codebase_memory_mcp.py` / `foreign/codebase_memory_mcp_adapter.py` | Second admitted whole-engine opaque part + §17 adapter | ✓ VERIFIED | 11-verdict `AdmissionRecord`; `normalise_to_item_kind` present and exercised against committed fixtures |
| `databasise/evidence/*.md` (4 files) | DR-04 decision, injected-LLM survey, codebase-memory-mcp admission manifest, Falsifier 4 evidence | ✓ VERIFIED | All substantive (103-145 lines each), all enforced by `test_admission_docs.py`/`test_falsifier4_evidence.py` |
| `databasise/seam/corpus.py` | Bounded corpus-side DTOs | ✓ VERIFIED | `IngestDocument`, `IngestJob`, `DeletionOutcome`, `Page`, `MAX_PAGE_SIZE`, `DocumentStatusEntry`, `JobStatus`, `CorpusStatus`, `DocumentCounts`, `HealthReport` all present |
| `databasise/seam/rest.py` | Corpus-side REST routes | ✓ VERIFIED | `POST /documents`, `POST /documents/upload`, `GET /jobs/{job_id}`, `DELETE /documents/{document_id}`, `GET /health`, `GET /corpus`, `GET /corpus/counts` all present |
| `databasise/mcp/server.py` / `tools.py` | MCP server factory + five tools | ⚠️ ORPHANED-BEHAVIOR (present, wired, but two refusal paths crash) | Present and wired to the same `Databasise` object REST uses; `create_server`/`TOOL_NAMES` present — but see gap 2 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `seam/engine.py` | `runner/scheduler.py` | `scheduler.run_wiring(...)` for ingest/delete wirings | ✓ WIRED | Confirmed by grep and passing `test_full_ingest.py`/`test_delete_document.py` |
| `parts_core/lightrag/full_ingest.py` | `foreign/v1_corpus_adapter.py` | `run_corpus_op` | ✓ WIRED | Confirmed |
| `mcp/server.py` | `seam/engine.py` | `await engine.<method>` per tool | ✓ WIRED | Confirmed — one `Databasise` instance per server, asserted by identity in `test_dual_transport_parity.py` |
| `foreign/codebase_memory_mcp_adapter.py` | `seam/evidence.py` | `ItemKind` normalization at the adapter boundary | ✓ WIRED | `normalise_to_item_kind` confirmed present, exercised against committed and live fixtures |
| `mcp/tools.py` | `seam/corpus.py` | Tool arguments deserialize into `IngestDocument`/`Page`/etc. | ⚠️ WIRED-BUT-UNGUARDED | Wired, but `Page(...)` construction and `base64.b64decode` inside the tool path are not pre-validated the way REST's `_checked_page` pre-validates them — see gap 2 |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite (all extras) | `cd databasise && uv run --extra rest --extra mcp pytest -q` | 738 passed, 1 skipped (the opt-in real-delete leg) — run twice in this verification pass, identical result both times | ✓ PASS |
| Import boundary | `cd databasise && uv run python tools/check_import_boundary.py` | exit 0 | ✓ PASS |
| CR-02 reproduction (fabricated ingest success) | Live Python: point `DEFAULT_V1_INTERPRETER` at a nonexistent path, call `engine.ingest(...)` | `RETURNED (no exception): job_id=... enqueued=0` | ✗ FAIL (confirms gap 1) |
| CR-01a reproduction (page-cap crash via MCP) | Live Python: `server.call_tool("status", {"args": {"scope": "corpus", "limit": 999999}})` | `UnexpectedToolError` | ✗ FAIL (confirms gap 2) |
| CR-01b reproduction (malformed base64 crash via MCP) | Live Python: `server.call_tool("ingest", {"args": {"raw_base64": "not-valid-base64!!!", "file_name": "x.txt"}})` | `UnexpectedToolError` | ✗ FAIL (confirms gap 2) |
| Admission verdict counts | Live Python: import all three admission records, count verdicts | 11/11/11 | ✓ PASS |
| Admission not-clean-yes disposition (codebase-memory-mcp) | Live Python: print each verdict | matches required disposition exactly (condition 1 confirms-the-rule, condition 3 open-question, 7/8/9 machine-side-obligation) | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|---|---|---|---|---|
| MODAL-02 | 05-01, 05-03, 05-05 | LightRAG ingest core admitted opaque, quarantined scope, boundary rule + compat test | ✓ SATISFIED | Truth 1 |
| MODAL-03 | 05-06 | codebase-memory-mcp admitted whole-engine, 11 verdicts, Falsifier 4 twice | ✓ SATISFIED | Truth 2 |
| MACH-04 | 05-02 | Injected-LLM-endpoint survey, five engines, non-gating | ✓ SATISFIED | `INJECTED-LLM-ENDPOINT-SURVEY.md` |
| API-01 | 05-01, 05-04 | Ingest + async job status polling | ⚠️ SATISFIED WITH DEFECT | Happy path verified; gap 1 (CR-02) is a confirmed, reproduced defect in this exact operation's failure-path honesty |
| API-02 | 05-03 | Delete with graph-aware cleanup | ✓ SATISFIED | Truth 3's delete half; WR-01 (a related but lower-severity downgrade, not a fabricated success) noted below, not gating |
| API-06 | 05-04 | Bounded health/corpus/counts, never a full dump | ✓ SATISFIED | Truth 4 |
| API-07 | 05-07 | MCP intention-level tool parity with REST | ⚠️ SATISFIED WITH DEFECT | Tool set and growth invariant verified; gap 2 (CR-01) is a confirmed, reproduced parity divergence on two refusal paths |
| HARD-03 | 05-02 | DR-04 decided | ✓ SATISFIED | `DR-04-DECISION.md` selects `two-covering-rationale` machine-readably |

No orphaned requirements — all 8 phase requirement IDs declared across the 7 plans match REQUIREMENTS.md's Phase 5 mapping exactly.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `databasise/seam/engine.py` | 512-524 | Narrow `isinstance` refusal check falls through to a fabricated success | 🛑 Blocker (gap 1 / CR-02) | Caller cannot distinguish a real ingest from a silently-failed one |
| `databasise/mcp/server.py` | 106-113 | `Page(...)` constructed without pre-validation, same for `mcp/tools.py:74`'s `base64.b64decode` | 🛑 Blocker (gap 2 / CR-01) | MCP transport crashes instead of refusing on two identifiable inputs |
| `databasise/seam/engine.py` | 578-591 | Same narrow `isinstance` pattern in `delete_document()`, downgrades an unclassified failure to `status="fail"` with no cause | ⚠️ Warning (WR-01) | Not a fabricated success (status is still "fail"), but loses diagnostic cause; same root cause as gap 1, not independently gating |
| `databasise/parts_core/codebase_memory_mcp.py` | 304-316 | `tool`/`arguments` forwarded to `call_tool` with no check against `CBM_KNOWN_TOOL_NAMES` | ⚠️ Warning (WR-02) | Not reachable through any currently-wired path (no wiring declares `config`); a future wiring could reach an unadmitted mutating tool |
| `databasise/seam/engine.py` | 684-688 | Vestigial empty `try: pass finally:` in `health()` | ℹ️ Info (IN-01) | Cosmetic only |
| `.planning/phases/05-opaque-side-admission/05-VALIDATION.md` | whole file | Still template placeholders (`status: draft`, `{quick command}`, `{full command}` etc.), never filled in | ℹ️ Info | Process artifact only — no roadmap success criterion depends on this file; not gating |

No `TBD`/`FIXME`/`XXX` debt markers found in any phase-5-touched file.

## Human Verification Required

None. Every observable truth for this phase resolves through code inspection, live reproduction, or the existing automated test suite — no visual, real-time, or external-service behavior is in scope.

## Gaps Summary

Five of the roadmap's five stated success criteria hold at the literal text level, and the phase's
own architectural work (two admitted opaque parts with 11-verdict records each, the boundary rule
and its compat test, the bounded/paginated read surface, the five-tool MCP transport with its
growth invariant) is substantive and well-tested — 738 of the suite's 739 tests pass, the one
skip being an opt-in, cost-gated real-deletion leg that was demonstrably run once with concrete
before/after evidence.

Two confirmed, independently-reproduced BLOCKER-level defects remain unresolved, both first found
by 05-REVIEW.md and both re-reproduced from scratch in this verification pass against the current
code (not merely cited):

1. **CR-02** — `Databasise.ingest()` (and, less severely, `delete_document()`) silently fabricates
   a successful result when the underlying v1 subprocess fails for any reason other than the two
   specifically-checked exception types. This is a genuine gap in ROADMAP Criterion 3's implicit
   reliability guarantee for "polls the job to completion" — a caller has no way to detect the
   ingest never happened.
2. **CR-01** — The MCP transport's `status`/`ingest` tools crash with the SDK's generic
   `UnexpectedToolError` instead of the documented mapped refusal on a page-cap violation or
   malformed base64 payload — REST's equivalent endpoints do not have this bug. This is a genuine,
   reproduced divergence between the two transports for identical operations, undermining ROADMAP
   Criterion 5's "the MCP surface exposes the same capabilities as REST."

Both fixes are narrow and mechanical (the review's own suggested fixes mirror existing patterns
already correct elsewhere in the same codebase: `_checked_page` in `rest.py`, and inverting the
refusal `isinstance` check to "no result produced" rather than an enumerated exception list). No
later milestone phase's goal or success criteria address either defect, so neither is deferred.

---

_Verified: 2026-09-08_
_Verifier: Claude (gsd-verifier)_
