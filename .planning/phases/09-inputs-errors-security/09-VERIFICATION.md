---
phase: 09-inputs-errors-security
verified: 2026-11-01T00:48:43Z
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
covered_digest: "v3:sha256:b7102b92098c2d68bc77c0b4405aed90ff5e3c37ea49693785c0c212f23174a5"
behavior_unverified: 0
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 5/5
  gaps_closed: []
  gaps_remaining: []
  regressions: []
---

# Phase 9: Inputs, Errors & Security Verification Report

**Phase Goal:** Every caller-facing failure on REST and MCP is a named refusal in one documented shape, and no caller input reaches the disk, a store or a node before it is validated. The Phase 8 launcher transport guards keep their own shape (D-13).
**Verified:** 2026-10-31 (re-verified 2026-10-31 PDT / 2026-11-01T00:48Z after the Phase 18 staleness trip; see the subsection below)
**Status:** passed
**Re-verification:** Yes. The prior report (2026-10-17, passed) went stale because Phases 14, 15 and 16 changed 12 covered source files (`serve_rest.py`, `mcp/server.py`, `mcp/tools.py`, `seam/corpus.py`, `engine.py`, `evidence.py`, `query.py`, `redact.py`, `refusals.py`, `rest.py`, `selectors.py`, `tokens.py`). Every truth was re-checked against the current code. No regression.

## What changed since the last report

Git history on the moved files since 2026-10-17 is Phase 14 (ledger verbs, alias reads, gate refusals), Phase 15 (tool descriptions, floors store, wheel packaging) and Phase 16 (operator surface: `/info`, `/wirings`, `/traces`, `/chunks`, `/graph/*`, `/log`, `--log-file`). None of these commits removed a Phase 9 guard. Two growths matter here. The refusal catalogue grew from 40 to 51 `SeamRefusalError` subclasses, and the engine gained operator read paths. The checks below confirm the catalogue is still complete and that the Phase 9 tests still bind the current code.

### Re-verification 2026-10-31 (Phase 18 staleness)

The 2026-10-31 report went stale because exactly one covered file changed afterwards: `databasise/launcher/serve_rest.py`, in commit `eff8804` (Phase 18-02, `feat(18-02): serve the operator console at GET /console with --console`, +65 lines, no deletions). No other covered file moved (`seam/rest.py` last changed 2026-10-22 in `2881382`, before the prior report). The diff was read in full. It adds:

- a `--console` flag (`build_parser`) and two `parser.error` rules in `main` (loopback host required; `--port 0` refused), both evaluated before the store lock and in the launcher's own argparse shape, which D-13 permits;
- `console_csp(page)`, a hash-source CSP builder that reads the shipped page bytes and raises at start-up if the page does not hold exactly one executable inline script and one style block;
- inside `build_app`, under `if args.console`, a `GET /console` route (`include_in_schema=False`) that returns bytes read once at start-up via `importlib.resources.files("databasise.console").joinpath("operator-console.html")` with five fixed headers (`Content-Security-Policy`, `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`).

What was re-checked, against the live `build_app` with `console=True` on an empty temp store root (scratchpad `p9_console.py` plus two inline probes):

| Check | Result |
|-------|--------|
| `GET /console` takes no caller input | The handler has no path, query or body parameter. `GET /console?path=../../etc/passwd&id=x` returned the identical 382,661-byte page; `POST /console` returned 405. The served bytes come from the installed package resource (`pyproject.toml` `[tool.setuptools.package-data] "databasise.console" = ["operator-console.html"]`), never from a caller-supplied path. No new store or disk entry after any probe. |
| Security headers do not alter refusal bodies | Headers are attached to the one `Response` object in `get_console`, not to a middleware. Refusals on `/query` (`EmptyQueryObjectError`), `/compare` (`EmptyQueryObjectError`), `/promote` (`InvalidPromotionAliasError`), `/documents` (`InvalidDocumentIdError` for `../x`, `a.b`, `a\n`, `''`; `EmptyIngestDocumentError` for blank text; `OversizedDocumentError` with the same 167-byte body as before) all returned 422 with `refusal_type`, no `detail`, and no `Content-Security-Policy` or `X-Frame-Options` header. |
| D-13 transport guards keep their own shape | Cross-site `POST /query` with `Origin: http://evil.example` returned 403 `{"detail": "origin not allowed"}`; `GET /health` with `Host: evil.example` returned 400 (TrustedHost). Both middleware blocks are byte-identical to the prior report's code (diff context only). |
| Route is opt-in and off the schema | `/console` is absent from `/openapi.json`; without `--console` the same app returns 404 for `GET /console`. |
| CSP has no inline-allow keyword | `console_csp` on the shipped page produced `default-src 'none'; script-src 'sha256-...'; style-src 'sha256-...'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'`; `'unsafe-inline'` absent. |
| Debt markers | None (`TBD`, `FIXME`, `XXX`) in `serve_rest.py`. |
| Targeted tests | `.venv/bin/python -m pytest` on the seam and launcher suites (`-q -p no:cacheprovider -x`) from `databasise/`: 1249 passed in 1390s (23m10s), exit 0. Covers every Phase 9 SEAM test file, `test_rest_transport`, and the Phase 18 launcher tests for `--console`. |

Verdict: the Phase 18 change adds a read-only, input-free route behind an opt-in flag and leaves every Phase 9 guard, handler and refusal body untouched. The goal still holds. `covered_digest` regenerated over the same `covered_files` list.

One probe note for the record: a request that is a pure schema error (missing required field, forbidden extra key) still returns FastAPI's `{"detail": [...]}` shape. That is the documented D-01 design in `rest.py:293-303` (`_validation_response` unwraps only a refusal raised inside a validator) and was so at the prior verification; it is not a Phase 18 regression.

## Goal Achievement

### Observable Truths (ROADMAP success criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Every refusal is a top-level JSON body with `refusal_type`, no `detail` wrapper, at the mapped status; MCP returns the same `refusal_type` as parseable JSON; one catalogue | VERIFIED | Live `TestClient` probe on `create_app` against current code: `EmptyQueryObjectError`, `EmptyCapabilitySelectorError`, `DuplicateComparisonKeyError`, `InvalidPromotionAliasError`, `InvalidEvidenceNamespaceError`, `InvalidDocumentIdError`, `EmptyIngestDocumentError`, `OversizedDocumentError` all returned at 422 with no `detail` key. `UnresolvableEvidenceReferenceError` returned 404. `mcp/server.py` still defines `RefusalToolError(ToolError)` returning bare refusal JSON, not `UnexpectedToolError`. Subclass walk (`SeamRefusalError` descendants after importing engine, rest and mcp.server): 51 subclasses, 52 entries in `refusals.__all__`, 0 missing. Tests: `test_refusal_body_shape`, `test_mcp_refusal_mapping`, `test_refusal_status_codes`, `test_refusal_catalogue` all pass. Re-confirmed 2026-10-31 through the `--console` launcher app (see subsection above). |
| 2 | Path-like namespaces and ids, oversize, empty, 0-byte, bad base64 and out-of-range page bounds are refused by name before any store, node or write; no 500, no directory | VERIFIED | Probe: namespaces `../../escape`, `../other-ws/chunks`, `/etc/x`, `chunks\n` gave 422 `InvalidEvidenceNamespaceError`; well-formed unknown `zzz` gave 404 and created nothing. Document ids `../x`, `a.b`, `a\n`, `''` gave 422 `InvalidDocumentIdError` on POST /documents; `DELETE /documents/a.b` and a multipart upload with id `../x` gave the same. 0-byte upload and blank text gave `EmptyIngestDocumentError`; a 26,214,401-byte upload gave `OversizedDocumentError` with a 167-byte body (input not echoed). A before/after filesystem snapshot of the store root showed zero new entries across all cases. Tests `test_evidence_namespace_guard`, `test_ingest_input_refusals`, `test_page_bounds`, `test_empty_inputs` pass. Document-id, blank-text and oversize cases re-run 2026-10-31 through the `--console` launcher app with identical results and zero new entries. |
| 3 | A v1 engine failure on any route returns a structured machine fault with no stderr, server path or traceback | VERIFIED | Probe patched `run_corpus_op` in `engine` and `corpus` to raise six failure kinds (subprocess error with a 30x traceback carrying a `/home/` path and `LIGHTRAG_API_KEY`; timeout; missing interpreter; `JSONDecodeError`; `PermissionError`; arbitrary `RuntimeError`) and hit GET /corpus, /corpus/counts and /jobs/x: 18 of 18 returned 502 or 503, `ForeignEngineRefusalError`, no `detail`, none of the planted strings. GET /health stayed 200 `degraded`. The traceback seen on stderr is the server-side log, as intended. Tests `test_foreign_engine_refusal`, `test_corpus_adapter_failures`, `test_read_route_fault_breadth`, `test_error_message_scrub` pass. |
| 4 | Unmeaningful selectors refused before work; compare resolves once, zero arms and traces on collision; upload `null`/`''` selector means default | VERIFIED | Probe: `capability: []` gave `EmptyCapabilitySelectorError` on /query and /compare. `selectors [{},{}]` and `[{alias:x},{harness:x}]` gave 422 `DuplicateComparisonKeyError`. Promote aliases `'a'*64` and `''` gave `InvalidPromotionAliasError`. `rest.py` line 322 treats upload selector `raw.strip() in ("", "null")` as default (line unchanged at re-verification; `rest.py` last changed 2026-10-22). Tests `test_empty_capability_selector`, `test_compare_keys` (zero LLM and embedding calls, unchanged trace row count), `test_promote_alias_validation`, `test_upload_selector_field` pass. |
| 5 | Docstrings and field descriptions match behaviour; redact leak check fires under `python -O` | VERIFIED | Run under `python -O` (`sys.flags.optimize == 1`): `assert_no_forbidden_keys` and `assert_no_forbidden_values` both raised `AssertionError` on a planted leak. `redact.py` contains no `assert` statement. `_DEFAULT_ARM` and `_ARM_NAMES` are absent from `selectors.py`. `IngestDocument` still states `file_name` and `content_type` are "not stored". `test_seam_doc_consistency` and `test_ingest_file_name` pass. |

**Score:** 5/5 truths verified, 0 behavior-unverified.

### Requirements Coverage

All 16 IDs (SEAM-01 to SEAM-16) appear in the ten PLAN frontmatters and in `.planning/REQUIREMENTS.md` (checked `[x]`). No orphaned requirement.

| Requirement | Status | Evidence on current code |
|-------------|--------|--------------------------|
| SEAM-01 | SATISFIED | namespace guard before any store; `test_evidence_namespace_guard`; probe |
| SEAM-02 | SATISFIED | one body on every route including validator-raised refusals; `test_refusal_body_shape`; probe |
| SEAM-03 | SATISFIED | `RefusalToolError` bare JSON; `test_mcp_refusal_mapping` |
| SEAM-04 | SATISFIED | 404 for lookups, 422 otherwise; `test_refusal_status_codes`; probe |
| SEAM-05 | SATISFIED | 502/503 by `failure_class`, no stderr; `test_foreign_engine_refusal`; probe |
| SEAM-06 | SATISFIED | three read routes structured faults; `test_corpus_adapter_failures`; probe (18/18) |
| SEAM-07 | SATISFIED | oversize 422, `InvalidDocumentIdError` on POST, upload, DELETE; `test_ingest_input_refusals`; probe |
| SEAM-08 | SATISFIED | `PageBoundsError` and `PageSizeExceededError`; `test_page_bounds` |
| SEAM-09 | SATISFIED | blank query, blank text, 0-byte refused; `test_empty_inputs`; probe |
| SEAM-10 | SATISFIED | `EmptyCapabilitySelectorError`; `test_empty_capability_selector`; probe |
| SEAM-11 | SATISFIED | `DuplicateComparisonKeyError` before execution; `test_compare_keys`; probe |
| SEAM-12 | SATISFIED | `InvalidPromotionAliasError`; `test_promote_alias_validation`; probe |
| SEAM-13 | SATISFIED | `rest.py:322`; `test_upload_selector_field` |
| SEAM-14 | SATISFIED | catalogue walk: 51 subclasses, 0 missing from `__all__`; `test_refusal_catalogue` |
| SEAM-15 | SATISFIED | "not stored" text in `IngestDocument`; `test_ingest_file_name` |
| SEAM-16 | SATISFIED | `-O` probe, dead names gone; `test_seam_doc_consistency` |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 17 Phase 9 test files (16 SEAM files plus `test_rest_transport`) | `.venv/bin/python -m pytest` on the 17 files | 405 passed in 121s (372 at first verification; growth is later phases' additions to the same files) | PASS |
| Review-fix regressions and MCP suite | `.venv/bin/python -m pytest` on `test_error_message_scrub`, `test_read_route_fault_breadth`, `test_raw_upload_staging`, `test_non_finite_numbers`, `test_rest_corpus_endpoints`, `tests/mcp` | 181 passed in 66s | PASS |
| REST refusal shape and no side effects | scratchpad `p9f.py` and `p9d.py` | all refusals named, no `detail`, no new filesystem entries | PASS |
| Machine-fault leak check | scratchpad `p9g.py` (6 failure kinds x 3 routes) | `bad 0` | PASS |
| Catalogue completeness | scratchpad `p9.py` | 51 subclasses, `missing []` | PASS |
| Leak check under -O | inline `python -O` | both checks raised | PASS |
| Phase 18 `--console` route against the refusal contract (2026-10-31) | scratchpad `p9_console.py` plus two inline probes | console 200 with five headers, no input accepted, refusals unchanged and header-free, D-13 guards 403/400 in their own shape, no new fs entries, route absent without the flag | PASS |
| Seam and launcher suites after `eff8804` (2026-10-31) | `.venv/bin/python -m pytest` on the seam and launcher suites, `-q -p no:cacheprovider -x` | 1249 passed in 1390s, exit 0 | PASS |

Probe scripts live in the session scratchpad; nothing was added to the repo. No `.env*` file was read. The full suite was not run here (the orchestrator runs it as the regression gate).

### Probe Execution

No PLAN or SUMMARY declares a `probe-*.sh`. Step 7c: SKIPPED.

### Anti-Patterns Found

None blocking. No `TBD`, `FIXME` or `XXX` marker in `databasise/seam/*.py`, `databasise/mcp/*.py` or `databasise/launcher/serve_rest.py` (re-checked on `serve_rest.py` after `eff8804`).

### Advisory (carried from the first report, unchanged)

IN-03 (OpenAPI does not declare the 404/422 refusal body for most routes), IN-04, IN-05, IN-06, IN-07, IN-08 and WR-02 remain open Info items. None breaks a success criterion or a requirement. The MCP-surface limitation of my probe: the MCP transport was checked by `test_mcp_refusal_mapping` and the `tests/mcp` suite (both pass), not re-probed live this round.

### Human Verification Required

None.

### Gaps Summary

No gaps. The moved files carry Phase 14 to 16 growth (new refusals, operator routes, ledger verbs) layered over the Phase 9 guards; every guard is still in place and every Phase 9 test passes against the current code. The requirement ledger rows for SEAM-01 to SEAM-16 were not inspected here and are the orchestrator's to update.

---

_Verified: 2026-10-31 (Phase 18 staleness re-verification 2026-11-01T00:48:43Z)_
_Verifier: Claude (gsd-verifier)_
