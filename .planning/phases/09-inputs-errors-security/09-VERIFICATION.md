---
phase: 09-inputs-errors-security
verified: 2026-10-17T00:00:00Z
status: passed
score: 5/5 must-haves verified (16/16 requirements)
covered_files:
  - .planning/phases/09-inputs-errors-security/09-01-PLAN.md
  - .planning/phases/09-inputs-errors-security/09-01-SUMMARY.md
  - .planning/phases/09-inputs-errors-security/09-02-PLAN.md
  - .planning/phases/09-inputs-errors-security/09-02-SUMMARY.md
  - .planning/phases/09-inputs-errors-security/09-03-PLAN.md
  - .planning/phases/09-inputs-errors-security/09-03-SUMMARY.md
  - .planning/phases/09-inputs-errors-security/09-04-PLAN.md
  - .planning/phases/09-inputs-errors-security/09-04-SUMMARY.md
  - .planning/phases/09-inputs-errors-security/09-05-PLAN.md
  - .planning/phases/09-inputs-errors-security/09-05-SUMMARY.md
  - .planning/phases/09-inputs-errors-security/09-06-PLAN.md
  - .planning/phases/09-inputs-errors-security/09-06-SUMMARY.md
  - .planning/phases/09-inputs-errors-security/09-07-PLAN.md
  - .planning/phases/09-inputs-errors-security/09-07-SUMMARY.md
  - .planning/phases/09-inputs-errors-security/09-08-PLAN.md
  - .planning/phases/09-inputs-errors-security/09-08-SUMMARY.md
  - .planning/phases/09-inputs-errors-security/09-09-PLAN.md
  - .planning/phases/09-inputs-errors-security/09-09-SUMMARY.md
  - .planning/phases/09-inputs-errors-security/09-10-PLAN.md
  - .planning/phases/09-inputs-errors-security/09-10-SUMMARY.md
  - databasise/launcher/serve_rest.py
  - databasise/mcp/server.py
  - databasise/mcp/tools.py
  - databasise/seam/compare.py
  - databasise/seam/corpus.py
  - databasise/seam/engine.py
  - databasise/seam/evidence.py
  - databasise/seam/query.py
  - databasise/seam/redact.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/seam/selectors.py
  - databasise/seam/tokens.py
covered_digest: "v3:sha256:e0c55dcf75ac6a66e5b92fba2a24e0e63081dfa9351657b3675135b37848518d"
behavior_unverified: 0
overrides_applied: 0
---

# Phase 9: Inputs, Errors & Security Verification Report

**Phase Goal:** Every caller-facing failure on REST and MCP is a named refusal in one documented shape, and no caller input reaches the disk, a store or a node before it is validated. The Phase 8 launcher transport guards keep their own shape (D-13).
**Verified:** 2026-10-17
**Status:** passed
**Re-verification:** No, initial verification. Re-verified after d4316bf (URL scrub widened in corpus.py): scrub, adapter-failure and foreign-engine-refusal tests 63 passed; SEAM-05, SEAM-06 and criterion 3 unchanged.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every refusal is a top-level JSON body with `refusal_type` and no `detail` wrapper, at the mapped status; MCP returns the same `refusal_type` as parseable JSON; one catalogue | VERIFIED | `rest.py` `_status_for` (404 for four lookups, 502/503 for faults, else 422), `_refusal_response`, `_validation_response` and `_pydantic_validation_response` handlers all build `refusal_body`. A probe ran 47 request cases against `create_app` (TestClient) and, in the same cases, against the real MCP server over `mcp.Client`. No REST body had `detail`. REST and MCP `refusal_type` matched in every paired case, and MCP returned `isError=True` with bare JSON (`mcp/server.py` `_DatabasiseServer.call_tool`). A subclass walk over the whole package found 40 `SeamRefusalError` subclasses, all exported by `refusals.__all__` (41 entries, none missing). |
| 2 | Path-like namespaces and ids, oversize, empty, 0-byte, bad base64 and out-of-range page bounds are refused by name before any store, node or write; no 500, no directory | VERIFIED | The probe covered `../../escape_probe`, `../other-ws/chunks`, `/etc/x`, `chunks\n`, ids `../x`, `a.b`, `a\n`, `''`, blank and empty text, 0-byte and 26,214,401-byte uploads, `YW!Jj`, `!!!!`, `YW*Jj`, `limit` 0, -1 and 101, `offset` -1. Every one returned its named refusal (`InvalidEvidenceNamespaceError`, `InvalidDocumentIdError`, `EmptyIngestDocumentError`, `OversizedDocumentError`, `MalformedBase64PayloadError`, `PageBoundsError`, `PageSizeExceededError`) with status 422. A filesystem snapshot of the temp tree before and after showed no new entry inside or outside `store_root`. The well-formed unknown namespace `zzz` returned 404 `UnresolvableEvidenceReferenceError` and created no directory. The oversize body was 167 bytes, so the input is not echoed. Code: `engine.ingest` calls `generated_on_disk_name` first (`engine.py` ~line 770); `corpus.py:303`. |
| 3 | A v1 engine failure on any route returns a structured machine fault with no stderr, server path or traceback | VERIFIED | Probe patched `engine.run_corpus_op` to raise six failures (subprocess error carrying a traceback, secret path and key text; timeout; missing interpreter; `JSONDecodeError`; `PermissionError`; arbitrary `RuntimeError`) and hit GET /corpus, /corpus/counts and /jobs/x. All 18 returned 502 or 503 with `refusal_type=ForeignEngineRefusalError` and a `failure_class`, under 240 bytes, `application/json`, with no `detail` and none of the planted strings. GET /health stayed 200 `degraded`. `refusals.ForeignEngineRefusalError` stores the cause on private `_cause`, which `refusal_body` skips; `engine._foreign_fault` logs it server-side. Ingest and delete go through `_node_result_or_refuse` (tests `test_foreign_engine_refusal.py`: ingest, delete, MCP delete, log-once). The v1 subprocess is reached only through `run_corpus_op` (the only `subprocess` use under `seam/`, `mcp/`, `foreign/`), so the query routes have no v1 subprocess to fail. OpenAPI declares 502/503 on the six fault-capable routes. |
| 4 | Unmeaningful selectors refused before work; compare resolves once, zero arms and traces on collision; upload `null`/`''` selector means default | VERIFIED | Probe: `capability: []` gave `EmptyCapabilitySelectorError` on /query, /compare, /documents/upload (form field), DELETE /documents and MCP query, compare and delete. `[{},{}]`, `[{alias:'default'},{}]`, `[{alias:'a+b'},{capability:['a','b']}]` and `[{alias:'x'},{harness:'x'}]` gave 422 `DuplicateComparisonKeyError` on both transports. Promote aliases `<64 hex>`, `sha256:<64 hex>` and `''` gave `InvalidPromotionAliasError`. Code: `engine.compare` checks `comparison_keys` before `resolve_selector`, then runs `_execute_resolved`, which never resolves. `test_compare_keys.py` asserts zero LLM and embedding calls and an unchanged trace row count for each colliding pair, and that a repoint between pre-check and execution does not change the wiring run. Upload route: `selector.strip() not in ("", "null")` (`rest.py`), covered by `test_upload_selector_field.py`. |
| 5 | Docstrings and field descriptions match behaviour; redact leak check fires under `python -O` | VERIFIED | `python -O` probe (`sys.flags.optimize == 1`): `assert_no_forbidden_keys` and `assert_no_forbidden_values` both raised `AssertionError` on a planted leak. `redact.py` has no `assert` statement and its docstring states it is a test-time gate. `_DEFAULT_ARM` and `_ARM_NAMES` are gone from `selectors.py` (only `wirings/resolve.py` keeps `_ARM_NAMES`). `tokens.py` names the three opaque parts and the `full_delete`/`full_ingest` rule. `refusals.py:475` documents `MutableStoreComparisonExcludedError` as currently unreachable. `corpus.py` and `IngestToolArgs` state `file_name`/`content_type` are "not stored". `rest.py` promote docstrings and module docstring state the non-string verb and MRO behaviour. `test_seam_doc_consistency.py` passes (17 tests). |

**Score:** 5/5 truths verified, 0 behavior-unverified.

### Requirements Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| SEAM-01 | SATISFIED | `InvalidEvidenceNamespaceError` raised before any store; `test_evidence_namespace_guard.py` (22) and probe |
| SEAM-02 | SATISFIED | one body on every route incl. validator-raised refusals and upload `ValidationError`; `test_refusal_body_shape.py` (15) and probe; `MultiMemberSelectorError` seen live |
| SEAM-03 | SATISFIED | `RefusalToolError` bare JSON with `isError`; scope preconditions are `MissingScopeArgumentError`; `test_mcp_refusal_mapping.py` (55) and probe; `server.py` docstring states client text |
| SEAM-04 | SATISFIED | 404 for the four lookups, 422 otherwise, from `_status_for`; `test_refusal_status_codes.py` (44) and probe (trace and evidence 404) |
| SEAM-05 | SATISFIED | 502/503 by `failure_class`, no stderr; `test_foreign_engine_refusal.py` (9) and probe |
| SEAM-06 | SATISFIED | three read routes structured faults, OpenAPI declares 502/503; `test_corpus_adapter_failures.py` (27) and probe |
| SEAM-07 | SATISFIED | oversize upload 422, `InvalidDocumentIdError` on POST /documents, upload, MCP ingest, DELETE; blank multipart id mints one (D-12); `test_ingest_input_refusals.py` (22) and probe |
| SEAM-08 | SATISFIED | `PageBoundsError` plus `PageSizeExceededError`, shared `checked_page` on REST and MCP; `test_page_bounds.py` (23) and probe |
| SEAM-09 | SATISFIED | blank query, blank text, 0-byte, empty and invalid base64 refused; `test_empty_inputs.py` (20) and probe |
| SEAM-10 | SATISFIED | `EmptyCapabilitySelectorError` on every selector route and MCP; `test_empty_capability_selector.py` (9) and probe |
| SEAM-11 | SATISFIED | see truth 4; `test_compare_keys.py` (12) |
| SEAM-12 | SATISFIED | `InvalidPromotionAliasError` for hash-shaped and empty alias; `test_promote_alias_validation.py` (7) and probe |
| SEAM-13 | SATISFIED | `test_upload_selector_field.py` (9); garbage JSON still `MalformedSelectorPayloadError` (probe) |
| SEAM-14 | SATISFIED | catalogue walk found no missing subclass; `test_refusal_catalogue.py` (5) |
| SEAM-15 | SATISFIED | docstrings and field descriptions state "not stored" (D-11); `test_ingest_file_name.py` (5) |
| SEAM-16 | SATISFIED | see truth 5; `test_seam_doc_consistency.py` (17) |

No orphaned requirements: all 16 SEAM IDs are claimed by the ten plans.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 17 SEAM and transport test files | `.venv/bin/pytest -q` on the 16 SEAM files plus `test_rest_transport.py` | 372 passed in 65s | PASS |
| Review-fix regressions and MCP suite | `.venv/bin/pytest -q` on `test_error_message_scrub`, `test_evidence_refs`, `test_non_finite_numbers`, `test_raw_upload_staging`, `test_read_route_fault_breadth`, `test_rest_corpus_endpoints`, `tests/mcp` | 186 passed in 54s | PASS |
| REST vs MCP refusal parity, no side effects | scratchpad `probe_rest_mcp.py` (47 cases) | all paired `refusal_type` equal, no `detail`, no new filesystem entries | PASS |
| Machine-fault leak check | scratchpad `probe_fault.py` (6 failure kinds x 3 routes) | 18/18 clean 502/503, `bad: 0` | PASS |
| Catalogue completeness | scratchpad `probe_catalogue.py` | 40 subclasses, 0 missing | PASS |
| Leak check under -O | scratchpad `probe_O.py` with `python -O` | both checks fired | PASS |

Probe scripts live in the session scratchpad; nothing was added to the repo (git status shows only the pre-existing untracked entries). No `-m live` test was run, and no `.env*` file was read.

### Probe Execution

No PLAN or SUMMARY declares a `probe-*.sh`. Step 7c: SKIPPED.

### Anti-Patterns Found

None blocking. No `TBD`, `FIXME` or `XXX` marker exists in any of the 13 covered source files (grep, no match). One cosmetic duplicate: `engine.py` assigns `node_config["file_paths"]` twice in a row in `ingest` (harmless).

### Advisory (open Info review items, not gaps)

| # | Item | Effect on criteria |
|---|------|--------------------|
| IN-03 | OpenAPI declares only 502/503 for the fault routes; it does not declare the 404 refusal, and the default 422 entry that FastAPI generates describes `{detail: [...]}` although refusals now return the refusal body. Duplicate-id 422 vs 409 also noted. | Not a gap. See the decision below. Minimal fix: add `404` and `422` `RefusalBody` entries to the shared `responses=` dict in `rest.py`. |
| IN-04 | Any node or read-route exception is labelled `ForeignEngineRefusalError` (a local `TypeError` becomes `UnclassifiedEngineFailure` 502). | Safe: no leak, traceback is logged. |
| IN-05 | `UnknownDocumentError` is unreachable but stays in `__all__`; stale `MalformedSelectorPayloadError` docstring. | None. |
| IN-06 | Some refusals (`EmptyQueryObjectError`, `InvalidDocumentIdError`, `DuplicateDocumentIdError`) echo caller input without a length cap. | SEAM-02 only requires that oversized-text refusals do not echo, and that holds (167-byte body). |
| IN-07 | Compare envelope-rule text copied in three places; a mid-run arm failure leaves earlier arms' traces. | None. |
| IN-08 | Accepted limits: staged id unique per store not per workspace; post-run fault orphans have no reaper; error-message scrub is best effort. | None. |
| WR-02 | Deferred and documented in the `ingest` docstring: a crash between exclusive create and owner-record write leaves an orphan staged file that an operator removes by hand. | Not a criterion. |

**IN-03 decision.** Success criterion 1 says "a JSON body with refusal_type and no FastAPI detail wrapper ... every refusal_type is exported from one catalogue." Neither it nor SEAM-02 requires the OpenAPI document to declare the refusal shape. SEAM-02 calls FastAPI's validation shape "the only other documented 4xx shape", which is satisfied by the `rest.py` module docstring, `RefusalBody` and the `_status_for` comment (SEAM-04 asks for exactly that comment). SEAM-06 is the only requirement that demands an OpenAPI declaration, and only for the machine-fault response on three routes, which is present. SEAM-14 ties typed-client coverage to the `refusals.__all__` catalogue, not to OpenAPI. So IN-03 does not break a criterion. It is a typed-client quality issue worth a later fix.

### Human Verification Required

None. Every behaviour-dependent truth (single resolution in compare, zero traces on collision, no directory creation, staged-file release rules) has a passing test that exercises the transition, and the probes above confirmed the main ones independently.

### Gaps Summary

No gaps. The ledger rows for SEAM-01 to SEAM-16 still read `open` with empty `test_ref`; that is the owner's or orchestrator's update after this verification and is not counted. RUN-11 live runs and seam authentication are out of scope as stated.

---

_Verified: 2026-10-17_
_Verifier: Claude (gsd-verifier)_
