# Phase 9: Inputs, Errors & Security - Context

**Gathered:** 2026-10-16
**Status:** Ready for planning
**Mode:** Smart discuss (autonomous). The owner answered "You decide" for all three grey areas, so every decision below is Claude's choice on the owner's delegation; each is recorded as a numbered decision so planning and verification treat it as binding.

<domain>
## Phase Boundary

Every caller-facing failure on REST and MCP becomes a named refusal in one documented shape, and no caller input reaches the disk, a store or a node before it is validated. Requirements SEAM-01 to SEAM-16. This phase changes the refusal wire format, status mapping, input validation and seam docstrings. It does not add seam authentication (open owner decision for the CONN phases), and it does not carry `file_name` through the LightRAG write path (M-04, Phase 11).

</domain>

<decisions>
## Implementation Decisions

### Refusal wire format and status (SEAM-02, SEAM-03, SEAM-04, SEAM-05, SEAM-06)
- **D-01:** SEAM-02: every refusal reaches a REST client as a top-level JSON body `{refusal_type, message, <named public fields>}` with no FastAPI `detail` wrapper, on every route. A `RequestValidationError` handler unwraps a `SeamRefusalError` found in `ctx.error` (pydantic-wrapped refusals) into the same body. The multi-member selector refusal is named `MultiMemberSelectorError`. Every refusal_type is exported from one catalogue (`databasise/seam/refusals.py` `__all__` or an equivalent single list).
- **D-02:** SEAM-03: the MCP transport returns `CallToolResult(isError=True)` whose text content is the bare refusal JSON (the same body as REST), with no SDK "Error executing tool <name>: " prefix. The scope-precondition errors (job without job_id, evidence without evidence_ref, trace without trace_reference) become named refusals. `server.py`'s docstring states the exact text a client receives.
- **D-03:** SEAM-04: HTTP 404 for the four not-found lookups (`UnknownTraceReferenceError`, `UnknownJobError`, `UnresolvableEvidenceReferenceError`, `UnknownGenerationVersionError`); 422 for every other refusal. The status per refusal type comes from one mapping in `rest.py`, described by a comment there.
- **D-04:** SEAM-05/06: a v1 engine failure is a machine fault, not a caller refusal. `ForeignEngineRefusalError` is the one fault type on every route (ingest, delete, and the read routes GET /corpus, /corpus/counts, /jobs/{id}), with a public field naming the failure class (`MissingV1InterpreterError`, `CorpusOpSubprocessError`, `CorpusOpTimeoutError`, malformed driver output). Status: 502 when the v1 run fails or returns malformed output; 503 when v1 is unavailable (missing interpreter, timeout). The public body names only the operation and the failure class, stays under 1 KB, and never contains stderr, tracebacks, absolute server paths or env-var names; the full cause is logged server-side only. No operator/debug flag exposes the cause while seam authentication is undecided. The OpenAPI schema for the three read routes declares the fault response.

### Input refusal names (SEAM-01, SEAM-07, SEAM-08, SEAM-09)
- **D-05:** SEAM-01: a path-like or otherwise malformed evidence namespace is refused as `InvalidEvidenceNamespaceError` before any store is opened or directory created.
- **D-06:** SEAM-07: a malformed caller `document_id` is refused as a new `InvalidDocumentIdError` before any lookup or file write; `UnknownDocumentError` stays for a well-formed id that does not exist.
- **D-07:** SEAM-08: a new `PageBoundsError` covers `limit < 1` and `offset < 0`; `PageSizeExceededError` is unchanged for the upper cap (no rename, consumers keep matching it).
- **D-08:** SEAM-09: whitespace-only text counts as empty and is refused by name, the same as empty text.

### Compare keys and ingest metadata (SEAM-11, SEAM-15)
- **D-09:** SEAM-11 keys: keep the current unprefixed comparison keys (no §18 consumer-visible change). Every collision is detected before any arm executes (zero arms run, zero LLM/embedding calls, zero traces persisted); selectors are resolved once and the resolved wirings are passed to execution.
- **D-10:** SEAM-11 envelope rule: a consumer tells a single envelope from a keyed map by the number of selectors it sent (one selector gives a single envelope; two or more give a keyed map). The rule is documented in the compare docstrings and OpenAPI description; no wrapper field is added. An alias named `answer` therefore cannot make a keyed map look like an envelope.
- **D-11:** SEAM-15: `file_name` and `content_type` are discarded at ingest, and the `corpus.py` module docstring, the `IngestDocument` docstring and the REST/MCP field descriptions say so ("not stored"). Carrying them into citation metadata is deferred to the LightRAG write-path work (M-04, Phase 11).

### Added during planning (Claude's decisions on the owner's delegation, plan-check iteration 1)
- **D-12 (revised, plan-check iteration 2):** On `/documents/upload` only, a blank `document_id` form field (`''`, which HTML forms send for an empty optional input) is normalised to absent at the form-parsing boundary, so the server mints the id — a blank form field is not a caller-supplied id (same reasoning as SEAM-13's upload selector `null`/`''` rule). A caller-supplied `document_id` that is `''` in a JSON body (POST /documents) or an MCP ingest argument, or any non-empty id failing the token check (`../x`, `a.b`, `a\n`, ...), is refused as `InvalidDocumentIdError` before any write, exactly as SEAM-07(b) states. No requirement text is amended.
- **D-13:** The Phase 8 launcher guards in `databasise/launcher/serve_rest.py` (Origin guard 403 `{"detail": ...}`, `TrustedHostMiddleware` 400) are transport-level defences in front of the seam and keep their own shapes; the Phase 9 refusal shape (D-01) covers every refusal raised by the seam (`create_app` routes and MCP tools). The `rest.py` module docstring and the launcher docstring state this boundary.

### Claude's Discretion
- Exact class placement and message wording for the new refusals, following `databasise/seam/refusals.py` house style (named attributes carrying the caller's own offending value; leading-underscore attributes never exposed).
- Whether the unprefixed-key collision pre-check reuses `DuplicateComparisonKeyError` (expected) or needs an additional named refusal.
- The structured log format for the server-side fault cause.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope
- `.planning/ROADMAP.md` — Phase 9 goal, success criteria, owner decisions list
- `.planning/REQUIREMENTS.md` — SEAM-01 to SEAM-16 (each with its named test file and source defects)
- `docs/gui/DEFECTS.json` — source defect uids cited by each SEAM requirement

### Contract
- `docs/system-model/` — CONTRACT.md §18 (seam envelope, §18.5 tool-surface growth rule)
- `databasise/evidence/COVERAGE.md` — live §18.5 coverage record (Phase 8 RUN-01); new tools/routes add rows here

### Phase 8 carry-over
- `.planning/phases/08-run-the-engine/08-CONTEXT.md` and `08-VERIFICATION.md` — launcher, store lock, origin guard, `BUILDER_REFUSALS`; seam authentication stays undecided

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `databasise/seam/refusals.py`: `SeamRefusalError(ValueError)` base and ~30 named refusals (`PageSizeExceededError`, `UnknownDocumentError`, `DuplicateComparisonKeyError`, `ForeignEngineRefusalError` at line ~490, ...). New refusals follow the same named-attribute pattern.
- `databasise/seam/rest.py`: `_refusal_response` (line ~214) is the one `SeamRefusalError` handler, dumping `vars(exc)` minus leading-underscore attributes; registered at line ~279. The per-type status mapping (D-03, D-04) belongs here.
- `databasise/mcp/server.py`: `_refusal_detail` / `_refusal_mapped` (lines ~79-106) raise `ToolError(json.dumps(...))`; `_status_job`, `_resolve_evidence_scope`, `_resolve_trace_scope` raise plain-text `ToolError` for scope preconditions (D-02 replaces both).
- `databasise/seam/engine.py` `compare` (line ~597) calls `resolve_selector` in the pre-check (line ~646) and again during execution (D-09: resolve once).

### Established Patterns
- Named refusals over silent fallbacks; refusal messages name only the caller's own input, never this machine's wirings, arms or node ids.
- Pydantic validators wrap raised refusals in `ValidationError`; refusal names are kept in the message text for that reason (`PageSizeExceededError` docstring).
- Commit messages need a `phase/09` trailer; test files that carry a BAK ledger `test_ref` (`tests/seam/test_rest_corpus_endpoints.py`, `tests/clients/test_openai_compat.py`, `tests/launcher/*`, `tests/seam/test_rest_cors.py`, ...) need the owner's `grant-check-edit` before a plan edits them.

### Integration Points
- REST: `rest.py` exception handlers and route OpenAPI `responses=`.
- MCP: `server.py` tool wrappers; tests use the real SDK via `import_real_mcp`.
- `databasise/foreign/` corpus adapter (`run_corpus_op`, `CorpusOpSubprocessError`, `CorpusOpTimeoutError`, `MissingV1InterpreterError`) for D-04.

</code_context>

<specifics>
## Specific Ideas

No specific owner requirements beyond the decisions above; the REQUIREMENTS.md test descriptions for each SEAM ID are the acceptance contract.

</specifics>

<deferred>
## Deferred Ideas

- Carrying `file_name`/`content_type` into v1 citation metadata — with the LightRAG write-path work (M-04, Phase 11).
- An operator/debug flag exposing the server-side fault cause — revisit with the seam authentication decision (CONN phases).

</deferred>

---

*Phase: 09-inputs-errors-security*
*Context gathered: 2026-10-16*
