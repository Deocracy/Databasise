<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

(Copied verbatim from `09-CONTEXT.md` `## Decisions`. The owner answered "You decide" for all three grey areas, so each is recorded as binding.)

#### Refusal wire format and status (SEAM-02, SEAM-03, SEAM-04, SEAM-05, SEAM-06)
- **D-01:** SEAM-02: every refusal reaches a REST client as a top-level JSON body `{refusal_type, message, <named public fields>}` with no FastAPI `detail` wrapper, on every route. A `RequestValidationError` handler unwraps a `SeamRefusalError` found in `ctx.error` (pydantic-wrapped refusals) into the same body. The multi-member selector refusal is named `MultiMemberSelectorError`. Every refusal_type is exported from one catalogue (`databasise/seam/refusals.py` `__all__` or an equivalent single list).
- **D-02:** SEAM-03: the MCP transport returns `CallToolResult(isError=True)` whose text content is the bare refusal JSON (the same body as REST), with no SDK "Error executing tool <name>: " prefix. The scope-precondition errors (job without job_id, evidence without evidence_ref, trace without trace_reference) become named refusals. `server.py`'s docstring states the exact text a client receives.
- **D-03:** SEAM-04: HTTP 404 for the four not-found lookups (`UnknownTraceReferenceError`, `UnknownJobError`, `UnresolvableEvidenceReferenceError`, `UnknownGenerationVersionError`); 422 for every other refusal. The status per refusal type comes from one mapping in `rest.py`, described by a comment there.
- **D-04:** SEAM-05/06: a v1 engine failure is a machine fault, not a caller refusal. `ForeignEngineRefusalError` is the one fault type on every route (ingest, delete, and the read routes GET /corpus, /corpus/counts, /jobs/{id}), with a public field naming the failure class (`MissingV1InterpreterError`, `CorpusOpSubprocessError`, `CorpusOpTimeoutError`, malformed driver output). Status: 502 when the v1 run fails or returns malformed output; 503 when v1 is unavailable (missing interpreter, timeout). The public body names only the operation and the failure class, stays under 1 KB, and never contains stderr, tracebacks, absolute server paths or env-var names; the full cause is logged server-side only. No operator/debug flag exposes the cause while seam authentication is undecided. The OpenAPI schema for the three read routes declares the fault response.

#### Input refusal names (SEAM-01, SEAM-07, SEAM-08, SEAM-09)
- **D-05:** SEAM-01: a path-like or otherwise malformed evidence namespace is refused as `InvalidEvidenceNamespaceError` before any store is opened or directory created.
- **D-06:** SEAM-07: a malformed caller `document_id` is refused as a new `InvalidDocumentIdError` before any lookup or file write; `UnknownDocumentError` stays for a well-formed id that does not exist.
- **D-07:** SEAM-08: a new `PageBoundsError` covers `limit < 1` and `offset < 0`; `PageSizeExceededError` is unchanged for the upper cap (no rename, consumers keep matching it).
- **D-08:** SEAM-09: whitespace-only text counts as empty and is refused by name, the same as empty text.

#### Compare keys and ingest metadata (SEAM-11, SEAM-15)
- **D-09:** SEAM-11 keys: keep the current unprefixed comparison keys (no §18 consumer-visible change). Every collision is detected before any arm executes (zero arms run, zero LLM/embedding calls, zero traces persisted); selectors are resolved once and the resolved wirings are passed to execution.
- **D-10:** SEAM-11 envelope rule: a consumer tells a single envelope from a keyed map by the number of selectors it sent (one selector gives a single envelope; two or more give a keyed map). The rule is documented in the compare docstrings and OpenAPI description; no wrapper field is added. An alias named `answer` therefore cannot make a keyed map look like an envelope.
- **D-11:** SEAM-15: `file_name` and `content_type` are discarded at ingest, and the `corpus.py` module docstring, the `IngestDocument` docstring and the REST/MCP field descriptions say so ("not stored"). Carrying them into citation metadata is deferred to the LightRAG write-path work (M-04, Phase 11).

### Claude's Discretion
- Exact class placement and message wording for the new refusals, following `databasise/seam/refusals.py` house style (named attributes carrying the caller's own offending value; leading-underscore attributes never exposed).
- Whether the unprefixed-key collision pre-check reuses `DuplicateComparisonKeyError` (expected) or needs an additional named refusal.
- The structured log format for the server-side fault cause.

### Deferred Ideas (OUT OF SCOPE)
- Carrying `file_name`/`content_type` into v1 citation metadata — with the LightRAG write-path work (M-04, Phase 11).
- An operator/debug flag exposing the server-side fault cause — revisit with the seam authentication decision (CONN phases).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SEAM-01 | Evidence namespace guard (`^[A-Za-z0-9-]+$` fullmatch, no dir created) | §R-01: guard in `Databasise.resolve_evidence` before `_build_stores`; pre-existence check replaces the mkdir in `FaissVectorStore.__init__`; reproduced dir creation outside store_root |
| SEAM-02 | One refusal body for validator-raised refusals | §R-02: `RequestValidationError` handler (verified `ctx.error` is the original exception), `pydantic.ValidationError` handler for the upload route, `MultiMemberSelectorError` |
| SEAM-03 | MCP JSON refusals for every refusal REST returns | §R-03: `MCPServer` subclass overriding `call_tool`, raising `RefusalToolError(ToolError)` whose text is bare JSON (verified on the wire with `mcp.Client`) |
| SEAM-04 | 404 for four lookups, 422 otherwise, one mapping | §R-04: `_status_for(exc)` mapping in rest.py |
| SEAM-05 | `ForeignEngineRefusalError` is a 5xx fault with no stderr | §R-05: private `_cause`, public `failure_class`, 502/503 mapping, server-side log |
| SEAM-06 | Read routes never 500 on adapter failure; OpenAPI declares it | §R-06: one engine helper around `run_corpus_op` (module-global name kept for monkeypatching), `responses=` on six routes |
| SEAM-07 | No ingest input yields 500/UnexpectedToolError | §R-07: upload-route ValidationError mapping, `generated_on_disk_name` fullmatch + `InvalidDocumentIdError` |
| SEAM-08 | Page bounds on every path | §R-08: `PageBoundsError`, drop `Query(ge=0)`, shared `checked_page`, `Page` docstring |
| SEAM-09 | Empty/whitespace/0-byte/bad-base64 refused | §R-09: `check_consumable` whitespace rule, `IngestDocument` empty rule, `b64decode(validate=True)` |
| SEAM-10 | `capability: []` refused | §R-10: refusal in `resolve_selector` (not in the `Selector` validator) |
| SEAM-11 | Compare collisions before any arm; resolve once | §R-11: keys first, then resolve all, then execute pre-resolved wirings |
| SEAM-12 | Unselectable promote aliases refused | §R-12: `InvalidPromotionAliasError` in `Databasise.promote` |
| SEAM-13 | Upload selector `null`/`''` = default | §R-13: one-line parse rule in the upload route |
| SEAM-14 | One refusal catalogue | §R-14: move 3 classes into refusals.py (re-export from old modules), extend `__all__` |
| SEAM-15 | file_name/content_type documented as discarded | §R-15: docstrings + `Field(description=...)` on REST and MCP models |
| SEAM-16 | Docstrings/dead code/`python -O` | §R-16: stale-phrase list with lines, `_ARM_NAMES` removal needs owner grant, `raise AssertionError` in redact.py |
</phase_requirements>

# Phase 9: Inputs, Errors & Security - Research

**Researched:** 2026-10-16
**Domain:** Brownfield hardening of the §18 seam (FastAPI REST + MCP 2.2.0 transports over one `Databasise` engine): refusal wire format, input validation, machine-fault reporting
**Confidence:** HIGH (every finding below was reproduced in-process or read from source this session; no external web research was needed)

## Project Constraints (from ./.claude/CLAUDE.md)

- GSD workflow: file edits go through a GSD command (`/gsd-execute-phase`); no direct repo edits outside it.
- Python, `ruff` (target py310 in CLAUDE.md, `py311` in `databasise/pyproject.toml`), pytest 8 + pytest-asyncio (`asyncio_mode = "auto"`), `uv` for installs.
- Refusals over silent fallbacks; refusal messages name only the caller's own input, never this machine's wirings, arms or node ids (`seam/refusals.py` module docstring).
- Commit messages carry a `phase/09` trailer (CONTEXT.md). Attribution trailer per the session reminder.
- Test files that carry a BAK ledger `test_ref` need the owner's `grant-check-edit` before a plan edits them (a PreToolUse hook blocks the edit, and also blocks any shell command whose text names such a file).
- Never read `v1/.env*`.
- Global: `[full absolute path](workspace-relative path)` link format in user-facing responses; no new files with spaces in the name.

## Summary

All sixteen SEAM requirements are reproducible against HEAD with small in-process calls (section "Reproduced baseline"). The offline baseline is **1251 passed, 1 skipped, 4 deselected in 224.57 s** (`cd databasise && uv run pytest -q -rs`), matching Phase 8's close. No new dependency is needed: every fix is code in `databasise/seam/*`, `databasise/mcp/*` and docstrings.

The architecture is already close to the target: `rest.py` registers one `SeamRefusalError` handler that dumps `vars(exc)` as a top-level body, and `mcp/server.py` mirrors it. The gaps are (1) refusals raised inside pydantic validators arrive wrapped in `ValidationError` and are not matched by either handler, (2) MCP always prefixes `Error executing tool <name>: ` because the SDK re-wraps every `ToolError` raised from a tool body, (3) `ForeignEngineRefusalError` copies stderr into both `message` and `cause`, (4) the read routes call `run_corpus_op` with no wrapper, (5) several inputs are validated with `re.match` + `$` (accepts a trailing newline) or not at all, (6) `Databasise.compare` runs arm 1 before it checks key collisions and resolves selectors twice.

**Primary recommendation:** build one shared, FastAPI-free kit in `databasise/seam/refusals.py` (catalogue, `refusal_body`, `refusal_from_errors`, new refusals, reworked `ForeignEngineRefusalError`), then wire it into REST (two exception handlers + a status mapping) and MCP (a thin `MCPServer` subclass whose `call_tool` converts any refusal, however wrapped, into a `ToolError` subclass whose text is the bare JSON). Fix input validation at engine level so REST, MCP and in-process callers share it.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Refusal vocabulary, catalogue, JSON body shape | Seam library (`seam/refusals.py`) | — | One FastAPI-free module both transports import; `mcp/` must not import fastapi |
| HTTP status mapping, OpenAPI `responses=`, validation-error unwrapping | REST transport (`seam/rest.py`) | — | HTTP concerns only; D-03 puts the mapping here |
| MCP text format (bare JSON, `isError`) | MCP transport (`mcp/server.py`) | SDK (`_handle_call_tool`) | SDK turns a raised `ToolError` into `CallToolResult(is_error=True)` using `str(exc)` |
| Input validation (ids, namespaces, emptiness, page bounds, selectors, aliases) | Engine / DTO layer (`seam/engine.py`, `corpus.py`, `query.py`, `selectors.py`) | Transports only translate | In-process callers must get the same guarantees; transports stay thin (AST proof) |
| Foreign-engine fault classification + server-side logging | Engine (`seam/engine.py`) | Foreign adapter (`foreign/`) | `run_corpus_op` is called via the engine module global; tests monkeypatch that name |
| Compare ordering (keys, resolve, mutates_store, execute) | Engine (`Databasise.compare`) | `seam/compare.py` (pure key helper) | Selector resolution may only happen in the engine (AST proof forbids it in rest/mcp) |
| Pre-seam guards (Host allow-list, Origin guard) | Launcher (`launcher/serve_rest.py`) | — | Phase 8 middleware outside the seam; not refusals (see Open Question 3) |

## Standard Stack

No new packages. Everything below is already locked in `databasise/uv.lock`.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | 0.141.1 | REST app, `RequestValidationError`, `responses=` OpenAPI | `[VERIFIED: uv pip list, this session]` |
| starlette | 1.6.0 | Exception-handler MRO matching, middleware ordering | `[VERIFIED: uv pip list]` |
| pydantic | 2.13.5 | Validators; `ValidationError.errors()[i]["ctx"]["error"]` is the original exception | `[VERIFIED: uv pip list; ctx.error identity checked in scratch prototype]` |
| mcp | 2.2.0 | `MCPServer`, `ToolError`, `mcp.Client(server)` in-memory client for wire-level tests | `[VERIFIED: uv pip list; source read in .venv/lib/python3.12/site-packages/mcp/server/mcpserver/]` |
| pytest / pytest-asyncio | 8.x / 1.2+ | Test runner (`asyncio_mode = "auto"`) | `[VERIFIED: databasise/pyproject.toml:109-113]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `MCPServer.call_tool` override raising a `ToolError` subclass | Each tool returns `CallToolResult(is_error=True)` | Returning a result is also valid in SDK 2.2.0, but it cannot intercept argument-validation refusals (the SDK validates `args` before the body runs) and it breaks 10 existing `pytest.raises(ToolError)` sites. Override wins. |
| Moving 3 classes into `refusals.py` and re-exporting | A separate `catalogue.py` listing them | Re-export keeps every existing import path working and keeps one `__all__`; a second list can drift (the exact defect SEAM-14 reports). |

**Installation:** none. **Version verification:** `uv pip list | grep -E "^(mcp|fastapi|starlette|pydantic) "` run this session (versions above).

## Package Legitimacy Audit

No external packages are installed or added by this phase. Audit not applicable. **Packages removed due to [SLOP] verdict:** none. **Packages flagged as suspicious [SUS]:** none.

## Reproduced baseline ("Fails today")

Run from `databasise/` with scratch scripts in the session scratchpad (TestClient with `raise_server_exceptions=False`; MCP via `create_server(...).call_tool`). Real v1 interpreter present; status ops were patched or hit the real read-only v1 status op only. `[VERIFIED: in-process repro this session]`

| Req | Call | Actual output today |
|-----|------|---------------------|
| SEAM-01 | POST /evidence/resolve ns `../../escape_probe`, abs tmp path, `chunks\n`, `zzz` | all four `422 UnresolvableEvidenceReferenceError`; new dirs created: `outer/escape_probe` (outside store_root), `abs_target`, `ws/chunks\n`, `ws/zzz`, plus `ws/text_chunks` and `ws/chunk_entity_relation/graph.cozo` (opened by `_build_stores`) |
| SEAM-02 | /query hash alias; /query alias+capability; /compare hash at idx 1; /documents `{document:{}}`; both text+raw; 26,214,401-byte text | `422 {"detail":[{"type":"value_error",...}]}` with no `refusal_type`; the oversize response was **26,214,635 bytes** (echoes `input`); the multi-member case has `"ctx":{"error":{}}` |
| SEAM-02 | upload with form `selector={"alias":"sha256:"+"a"*64}` | `422 MalformedSelectorPayloadError` (wrong name) |
| SEAM-03 | MCP: ingest `{}`, text+raw_base64, 26,214,401-byte text, status offset -1 | `UnexpectedToolError: 'Error executing tool <name>'` (no reason) |
| SEAM-03 | MCP: status `{scope:'job'}`, resolve `{scope:'evidence'}`, `{scope:'trace'}` | plain-text `ToolError: "Error executing tool status: status tool: scope 'job' requires a job_id"` |
| SEAM-03 | MCP: query with hash alias / multi-member selector | `ToolError: "Error executing tool query: 1 validation error for query_toolArguments\nargs.selector\n  Value error, ..."` (pydantic text, not JSON) |
| SEAM-04 | /trace/resolve `nope`; rollback unknown trace; /jobs/x unknown | all `422` (UnknownTraceReferenceError, UnknownJobError) |
| SEAM-05 | ingest with a part body raising `CorpusOpSubprocessError(1, 40 x "Traceback ... /home/chris/v1/x.py ...")` | REST `422`, 4,394 bytes, contains `/home/` and `Traceback` x46; MCP `ToolError` 4,430 chars containing `/home/` |
| SEAM-06 | `run_corpus_op` patched to raise Missing/Subprocess/Timeout/JSON-decode; GET /corpus, /corpus/counts, /jobs/x | all `500 text/plain` "Internal Server Error"; GET /health stays `200` "degraded" |
| SEAM-07 | upload of 26,214,401 bytes; POST /documents `document_id` `../x`, `a.b` | `500 text/plain` |
| SEAM-07 | POST /documents `document_id='a\n'`; DELETE /documents/a%0A | `200` (regex `^...$` + `.match` accepts the trailing newline); DELETE `a.b` gives `422 UnknownDocumentError`; MCP ingest `../evil` gives `UnexpectedToolError` |
| SEAM-08 | GET /corpus `?limit=0`, `?limit=-5`, `?limit=-1`, `?offset=-1`; /jobs/job-abc?limit=0 | limit 0 -> 200 `next_offset:0`; limit -1 -> 200 with total-1 rows; offset -1 -> FastAPI `{"detail":[{"type":"greater_than_equal",...}]}`; MCP status `limit:0` -> 200 |
| SEAM-09 | /query text `''` and `'   '` | `200` (degraded envelope; ran nodes, persisted a trace) |
| SEAM-09 | /documents text `''`; upload `b''`; MCP raw_base64 `''`, `'!!!!'`, `'YW*Jj'` | all `200 enqueued:1`; the 0-byte upload wrote `corpus-inbox/<uuid>.bin` |
| SEAM-10 | /query selector `{capability: []}`; /compare `[{capability:[]},{}]` | query `200` via bypass wiring; compare `200` keyed `""` plus `default`, LLM called twice |
| SEAM-11 | /compare `[{},{}]` (stub LLM/embedder, trace.db row counts) | `422 DuplicateComparisonKeyError` **after** arm 1 ran: llm 1, embed 1, `traces` rows +1 |
| SEAM-11 | `[{alias:'default'},{}]`, `[{alias:'x'},{harness:'x'}]`, `[{alias:'a+b'},{capability:['a','b']}]` with no such aliases | `422 UnsatisfiableSelectorError` (alias resolution wins today). **The tests must promote aliases `default`, `x`, `a+b` first** so the collision, not the unsatisfiable selector, is what is under test; after the fix keys are checked before resolution |
| SEAM-12 | POST /promote alias `''` and `sha256:`+`b`*64 with a real trace token | both `200` and wrote ledger rows (generation_ordinal 1 and 2); `/query` with alias `''` then resolved; the hash alias is rejected by `Selector` (unselectable) |
| SEAM-13 | upload selector `'null'` / `''` / omitted | `422 MalformedSelectorPayloadError` / `200` / `200` |
| SEAM-16 | `python -O -c "assert_no_forbidden_keys({'node-x':1},{'node-x'})"` | **no exception** (silently passes); without `-O`: `AssertionError: forbidden key 'node-x' found at $.node-x` |
| SEAM-16 | POST /promote `verb: null` | FastAPI `{"detail":[{"type":"string_type",...}]}` (already as the requirement wants; only docstrings are wrong) |

## Architecture Patterns

### System Architecture Diagram

```
                      caller input (JSON body / multipart / query params / MCP args)
                                        |
   +------------------------------------+------------------------------------+
   |  REST (FastAPI)                                         MCP (MCPServer)   |
   |  launcher guards: TrustedHost 400, Origin 403 (pre-seam, not refusals)    |
   |  body parse --> pydantic validators --> RequestValidationError            |
   |        |  handler: refusal_from_errors(exc.errors())                      |
   |        |     found -> refusal_body(exc) @ _status_for(exc)                |
   |        |     none  -> FastAPI default {"detail":[...]} 422                |
   |  route bodies: one awaited engine call (thin adapter, AST-proved)         |
   |  upload route: IngestDocument(...)/Selector.model_validate_json           |
   |        -> pydantic.ValidationError handler (same unwrap)                  |
   |                                                       SDK validates args  |
   |                                                       -> tool body        |
   |                                                       -> DatabasiseServer.call_tool
   |                                                          catches ToolError, walks __cause__
   |                                                          chain + ValidationError.errors()
   |                                                          -> RefusalToolError(bare JSON)
   |                                                          -> SDK _handle_call_tool
   |                                                          -> CallToolResult(is_error=True)
   +------------------------------------+------------------------------------+
                                        v
                         Databasise engine (single validation point)
   ingest: id fullmatch -> empty/size (DTO) -> resolve_selector (refuses capability [] ) -> write -> node
   resolve_evidence: namespace regex -> dir exists? -> vector store only (no kv/graph)
   compare: keys (pure) -> resolve all -> mutates_store check -> execute pre-resolved wirings
   promote: verb -> alias shape -> trace ids -> ledger
   status/read ops: Page bounds (caller) -> _corpus_op helper around module-global run_corpus_op
                                        |
                       node_exceptions / run_corpus_op failure
                                        v
              ForeignEngineRefusalError(operation, failure_class, _cause)  + server-side log
                                        v
              REST 502/503 (failure_class) | MCP bare JSON | in-process raises, .cause kept
```

### Recommended Project Structure (touch list, no new packages)

```
databasise/
├── seam/refusals.py      # catalogue, new refusals, refusal_body, refusal_from_errors, ForeignEngineRefusalError rework
├── seam/rest.py          # handlers, _status_for, responses=, Page bounds, upload parse, docstring fixes
├── mcp/server.py         # MCPServer subclass + RefusalToolError, scope refusals, drop _refusal_mapped/_refusal_detail/_checked_page copy
├── mcp/tools.py          # b64decode(validate=True), Field descriptions (file_name/content_type)
├── seam/corpus.py        # InvalidDocumentIdError via generated_on_disk_name (fullmatch), Page bounds + checked_page, empty rules, docstrings
├── seam/engine.py        # ingest/delete id, resolve_evidence, compare order, _execute_resolved, _corpus_op helper, promote alias, next_offset guard
├── seam/evidence.py      # validate_evidence_namespace, re-export Unresolvable...
├── seam/query.py         # whitespace text rule in check_consumable
├── seam/selectors.py     # capability [] refusal, MultiMemberSelectorError, dead-code + docstring removal
├── seam/compare.py       # comparison_keys() pure pre-check
├── seam/redact.py        # explicit raise AssertionError, "test-time gate" statement
├── seam/tokens.py        # docstring (three opaque parts), re-export UnbudgetableParticipantError
├── seam/trace_store.py   # re-export UnknownTraceReferenceError
└── namespaces.py         # optional: fullmatch in _NAMESPACE_TOKEN_RE use (defence in depth)
```

### Pattern 1: One refusal kit, two transports (SEAM-02/03/14)

Place in `refusals.py` (imports only `pydantic`, no FastAPI, no `mcp`):

```python
def refusal_body(exc: SeamRefusalError) -> dict[str, Any]:
    body = {"refusal_type": type(exc).__name__, "message": str(exc)}
    for key, value in vars(exc).items():
        if key.startswith("_"):          # CR-03: private attrs never exposed
            continue
        body[key] = value.model_dump() if isinstance(value, BaseModel) else value
    return body

def refusal_from_errors(errors) -> SeamRefusalError | None:
    """First SeamRefusalError found in pydantic/FastAPI error dicts (ctx.error). Accepts the list from
    ValidationError.errors() or RequestValidationError.errors()."""
    for err in errors:
        found = (err.get("ctx") or {}).get("error")
        if isinstance(found, SeamRefusalError):
            return found
    return None
```
Delete `rest._refusal_response`'s inline dump and `mcp.server._refusal_detail` (two copies today, `rest.py:214-240`, `server.py:79-92`) in favour of `refusal_body`.

### Pattern 2: REST handlers (SEAM-02/04/05/06)

```python
# Status per refusal type: ONE place (D-03/D-04). 404 = the four lookups; 502/503 = machine faults
# (ForeignEngineRefusalError, by failure_class); everything else is a caller refusal = 422.
_NOT_FOUND = (UnknownTraceReferenceError, UnknownJobError,
              UnresolvableEvidenceReferenceError, UnknownGenerationVersionError)
_UNAVAILABLE = frozenset({"MissingV1InterpreterError", "CorpusOpTimeoutError"})

def _status_for(exc: SeamRefusalError) -> int:
    if isinstance(exc, ForeignEngineRefusalError):
        return 503 if exc.failure_class in _UNAVAILABLE else 502
    return 404 if isinstance(exc, _NOT_FOUND) else 422

def _refusal_response(_request, exc):            # registered on SeamRefusalError (Starlette matches subclasses by MRO)
    return JSONResponse(status_code=_status_for(exc), content=refusal_body(exc))

async def _validation_response(request, exc: RequestValidationError):
    refusal = refusal_from_errors(exc.errors())
    if refusal is None:                           # schema error: FastAPI's own shape, the only other documented 4xx
        return await request_validation_exception_handler(request, exc)   # fastapi.exception_handlers
    return _refusal_response(request, refusal)
```
Register `RequestValidationError` and also `pydantic.ValidationError` (the latter covers `IngestDocument(...)` built inside the upload route; for a `ValidationError` with no refusal, re-raise so it stays a 500 and is visible). **Do not** pass `exc.errors()` to `JSONResponse` in the fallback: `ctx.error` is an exception object (not JSON-serialisable by `JSONResponse`); delegate to FastAPI's default handler.

### Pattern 3: MCP bare-JSON refusals (SEAM-03)

Verified facts about SDK 2.2.0 `[VERIFIED: source read]`:
- `Tool.run` re-raises every `ToolError` from a tool body as `ToolError(f"Error executing tool {self.name}: {exc}")` (`tools/base.py:205-207`) and every other exception as `UnexpectedToolError(f"Error executing tool {self.name}")` (`base.py:209-210`), so the prefix cannot be removed from inside a tool body.
- Argument validation runs before the body: `raise ToolError(f"Error executing tool {self.name}: {exc}") from exc` (`base.py:153`), with the pydantic `ValidationError` as `__cause__`. A `_refusal_mapped` decorator inside the body can never see a selector refusal; only a server-level interception can.
- Wire path: `_handle_call_tool` calls `self.call_tool(...)` and on any exception returns `CallToolResult(content=[TextContent(type="text", text=str(exc))], is_error=True)` (`server.py:447`). Therefore **raising a `ToolError` subclass whose `str()` is the bare JSON yields exactly the D-02 wire result.**
- A tool may also *return* a `CallToolResult`; `convert_result` passes it through (`func_metadata.py:204-207`).

Recommended mechanism (prototyped and run through `mcp.Client(server)` in-memory this session: `is_error True`, text begins `{"refusal_type": ...`):

```python
sdk = import_sdk("mcp.server.mcpserver"); ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError

class RefusalToolError(ToolError):
    """str() is the bare refusal JSON; deliberately NOT an UnexpectedToolError subclass."""

class _DatabasiseServer(sdk.MCPServer):
    async def call_tool(self, name, arguments, context=None):
        try:
            return await super().call_tool(name, arguments, context)
        except ToolError as exc:
            refusal = _find_refusal(exc)     # walk exc.__cause__ chain; for ValidationError use refusal_from_errors(e.errors()); a bare SeamRefusalError counts
            if refusal is None:
                raise                          # SDK shape stays for schema errors and crashes (documented)
            raise RefusalToolError(json.dumps(refusal_body(refusal))) from exc
```
Consequences: `_refusal_mapped`, `_refusal_detail` and the MCP `_checked_page` copy can be deleted; tool bodies become thinner. Existing `pytest.raises(ToolError)` tests and the `_tool_error_detail` helper (`text[text.index("{"):]`) keep passing unchanged. Import `CallToolResult`/`TextContent` (if ever needed) via `import_sdk("mcp.types")` (identical object to `mcp_types.CallToolResult`), never a bare `import mcp`.

Scope-precondition refusals (D-02): one class, e.g. `MissingScopeArgumentError(tool, scope, argument)` with `argument` in `job_id | evidence_ref | trace_reference`; raised at `server.py:128`, `:161`, `:167` in place of the three plain-text `ToolError`s.

### Pattern 4: Compare order (SEAM-11)

```python
keys = comparison_keys(selectors)                       # pure: render all keys, DuplicateComparisonKeyError on first repeat; before ANY resolution
wirings = [resolve_selector(s, registry=..., store_root=...) for s in selectors]   # all selector refusals (incl. capability []) before any arm
for w in wirings: mutates_store check                   # existing loop, now over the cached list
return {k: await self._execute_resolved(query_object, w) for k, w in zip(keys, wirings)}   # sequential, caller order
```
`_execute(query_object, selector)` becomes `check_consumable` + `resolve_selector` + `_execute_resolved(query_object, resolved)`. Keys-before-resolve is what makes `[{alias:'default'},{}]`, `[{alias:'x'},{harness:'x'}]`, `[{alias:'a+b'},{capability:['a','b']}]` return `DuplicateComparisonKeyError` (the alias would otherwise be refused first as unsatisfiable). Keep `compare_arms` exported (`seam/__init__.py:15,27`, `tests/seam/test_compare.py:27,282`, comment at `parity/run_cross_modality.py:327`); give it the same keys-first loop so the public helper is safe too. The single-selector path stays a bare envelope (RIG §RUN.3). D-10 rule goes into `Databasise.compare`, `rest.py` `/compare` route (`description=`), and the MCP `compare` tool docstring.

### Pattern 5: Foreign-engine fault (SEAM-05/06)

```python
class ForeignEngineRefusalError(SeamRefusalError):
    def __init__(self, *, operation: str, cause: BaseException, failure_class: str | None = None):
        self.operation = operation
        self.failure_class = failure_class or classify_failure(cause)   # allowlist by type NAME: MissingV1InterpreterError,
        self._cause = cause                                              # CorpusOpSubprocessError, CorpusOpTimeoutError,
        super().__init__(                                                # JSONDecodeError->MalformedDriverOutput, else UnclassifiedEngineFailure
            f"the foreign engine failed operation {operation!r}: {self.failure_class}")
    @property
    def cause(self) -> BaseException:       # property, not in vars(): in-process callers/tests keep .cause; the wire dump skips it
        return self._cause
```
Keep the `cause=` constructor kwarg and `.cause` attribute: `tests/parts_core/lightrag/test_full_ingest.py:154,178,196` and `tests/seam/test_delete_document.py:176,205` read `exc_info.value.cause`, and `tests/seam/test_rest_transport.py:419` constructs it with `cause=`. Message is operation + failure class only (well under 1 KB). Log the full cause once where the refusal is built (engine helper) with `logger.error(..., exc_info=cause)`.

Engine helper for the three read ops (keeps `run_corpus_op` as a **module global of `seam/engine.py`**, because `tests/seam/test_rest_corpus_endpoints.py::_patch_status_and_health` does `monkeypatch.setattr(engine_module, "run_corpus_op", _fake)` and SEAM-06's test patches the same name):

```python
async def _corpus_op_or_refuse(op: str, payload: dict, operation: str) -> dict:
    try:
        return await asyncio.to_thread(run_corpus_op, op, payload, timeout=STATUS_WALL_CLOCK_CEILING_SECONDS)
    except (MissingV1InterpreterError, CorpusOpSubprocessError, CorpusOpTimeoutError, json.JSONDecodeError) as exc:
        raise _fault(operation, exc) from exc          # logs + builds ForeignEngineRefusalError
```
Parse failures of a well-formed-JSON-but-wrong-shape result (`DocumentStatusEntry(**doc)`, `int(result["total"])`) should map to `failure_class="MalformedDriverOutput"`; wrap only that parse block, **not** the `UnknownJobError` raise (it is a `ValueError` too). `health()` keeps its own `except Exception` (stays 200 "degraded"). `document_counts` calls with `limit: 0` internally; it bypasses `Page`, so SEAM-08 does not affect it.

### Anti-Patterns to Avoid
- **Returning `exc.errors()` in a JSON response**: contains exception objects; delegate to `request_validation_exception_handler`.
- **Catching `ValueError` broadly around the read-op parse**: swallows `UnknownJobError` (a `SeamRefusalError(ValueError)`).
- **Resolving selectors in `rest.py`/`mcp/`**: the AST tests forbid *calling* any name in `selectors.__all__` minus `Selector`, any name in `redact.__all__`, and `ResponseEnvelope` (`tests/seam/test_rest_transport.py:195-200`, `tests/mcp/test_tool_growth_invariant.py:224-232`). Do not add new names to those two `__all__` lists that a transport would call.
- **`re.match` with `$`** for ids/namespaces: `$` matches before a trailing `\n`. Use `fullmatch`.
- **Keeping `document.document_id or uuid4().hex`**: an explicit `document_id=''` is silently replaced by a generated id; test `is None` instead so `''` is refused.

## Requirement implementation map

Line numbers are HEAD as of this session. `[VERIFIED: files read this session]`

### R-01 SEAM-01 evidence namespace
- `engine.py:1085-1096` `resolve_evidence` calls `_build_stores` (opens SqliteKV + Cozo + vector handle: creates `ws/text_chunks`, `ws/chunk_entity_relation/graph.cozo`) then `evidence.py:118-130` `resolve_evidence_ref` -> `vector_store.select(ref.namespace)`; `stores/vector.py:494-501` `select` builds `FaissVectorStore`, whose `__init__` does `self._dir = Path(store_root) / workspace / namespace` then `self._dir.mkdir(parents=True, exist_ok=True)` (`vector.py:115-116`) - that is how `../../escape_probe` is created outside store_root.
- Fix in `resolve_evidence`, before any store: `validate_evidence_namespace(ref.namespace)` (fullmatch `^[A-Za-z0-9-]+$`, raise `InvalidEvidenceNamespaceError(namespace=...)`, attribute is the caller's own value); then `if not (store_root/workspace/ns).is_dir(): raise UnresolvableEvidenceReferenceError(ref)`; then build only a `MultiNamespaceVectorStore` (do not call `_build_stores` - it opens two stores the resolve never uses) and `finalize()` it in `finally`.
- Existing namespaces all satisfy the regex: `"chunks"`, `"entities"`, `"relationships"` (`parity/run_cross_modality.py:74`), `"hipporag-chunks"`, `"hipporag-entities"`, `"hipporag-facts"` (`:75`).
- Defence in depth (optional, small): `namespaces.py:37` `_NAMESPACE_TOKEN_RE = re.compile(r"^[A-Za-z0-9-]+$")` is used with `.match` in `namespace_dir` (`:71-82`); switch to `fullmatch`.
- Verification caution: the test's "no new directory" check is only meaningful if the workspace already exists (use `synthetic_naive_store`), otherwise unrelated store handles are not the subject; with the fix no store is built at all for these inputs.

### R-02 SEAM-02 REST refusal body
- Handler registration at `rest.py:279`; `Selector` validators at `selectors.py:104-127`; at-most-one rule raises plain `ValueError` at `selectors.py:108` -> replace with `MultiMemberSelectorError(set_members=...)` (message must contain the literal class name, house convention for validator-raised refusals).
- Upload route `rest.py:363-374`: `IngestDocument(...)` (line 364) raises `ValidationError` -> currently an unhandled 500 (SEAM-07a); `Selector.model_validate_json(selector)` `except ValidationError` -> always `MalformedSelectorPayloadError` (line 373). New rule: unwrap with `refusal_from_errors(exc.errors())`; raise that refusal if found, else keep `MalformedSelectorPayloadError` (covers unparseable JSON and non-refusal schema errors; the requirement only changes the refusal-bearing case).
- Mixed errors (a schema error plus a refusal in one request): the refusal wins; documented in the rest.py module docstring. Oversize bodies are not echoed because the refusal body carries only `actual_bytes`/`limit_bytes`.

### R-03 SEAM-03 MCP - see Pattern 3. Sites: `server.py:106` (`ToolError(json.dumps(...))`), `:128`, `:161`, `:167` (plain-text scope errors), `tools.py:111-125` (`to_ingest_document`, body-raised `ValidationError`). `server.py` module docstring (`:1-40`) must state the exact client text: the bare JSON object, `isError=true`, no prefix; schema errors and crashes keep the SDK text (`Error executing tool <name>: ...`).

### R-04 SEAM-04 status mapping - Pattern 2. Replaces `_REFUSAL_STATUS_CODE = 422` (`rest.py:102`) and its comment (`rest.py:98-101`, which says 422 is "never a machine-fault 500" - rewrite). Existing generic tests only assert non-2xx plus the body (`test_rest_transport.py:506-533`); the one existing assertion that pins 422 for a lookup is `tests/seam/test_rest_corpus_endpoints.py:232-238` (protected file, see below).

### R-05 / R-06 SEAM-05/06 - Pattern 5. Sites: `refusals.py:490-502` (class), `engine.py:366-395` `_node_result_or_refuse` (keep signature `(scheduled, node_id, operation)`; the SEAM-05 test and `test_full_ingest.py:~188` call it directly), `engine.py:854-915` read ops. OpenAPI: add `responses={502: ..., 503: ...}` (model: a small `RefusalBody` pydantic model with `refusal_type`, `message`, `extra="allow"`) on `GET /corpus`, `GET /corpus/counts`, `GET /jobs/{job_id}`, and also on `POST /documents`, `POST /documents/upload`, `DELETE /documents/{id}`. Test: `app.openapi()["paths"]["/corpus"]["get"]["responses"]` contains `"502"` and `"503"`. Status for the four failure classes: Missing/Timeout -> 503; Subprocess/Malformed/Unclassified -> 502.

### R-07 SEAM-07 ingest ids and size
- `corpus.py:56` `_DOCUMENT_ID_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]+$")` used with `.match` at `corpus.py:221`: change to `fullmatch`, and raise `InvalidDocumentIdError(document_id=...)` from `generated_on_disk_name` itself (it is a `SeamRefusalError`, hence still a `ValueError` for `tests/parts_core/lightrag/test_full_ingest.py:353-359`). `engine.py:683` (ingest, currently an uncaught `ValueError` -> 500) and `engine.py:801-804` (delete wraps it as `UnknownDocumentError`) then share one raise; drop the delete wrapper. `UnknownDocumentError` stays in the catalogue (its docstring becomes "well-formed id that does not exist"; nothing raises it today, since v1 reports `not_found` as a normal outcome).
- `document.document_id or uuid.uuid4().hex` (`engine.py:679`) stays: per D-12 (added at plan-check iteration 1) an empty `document_id` means absent and gets a minted id; only a non-empty malformed id is refused.
- Upload oversize: caused by the unhandled `ValidationError` at `rest.py:364`; the pydantic handler from R-02 maps it to `OversizedDocumentError`. Starlette spools multipart uploads to a temp file before the route runs; the app has no body-size limit by design (`rest.py` exposure note) - out of scope (Open Question 9). `await file.read()` could cheaply become `file.read(MAX_DOCUMENT_BYTES + 1)`, optional.

### R-08 SEAM-08 page bounds
- `corpus.py:122-140` `Page._bounded`: add `limit < 1` and `offset < 0` -> `PageBoundsError` (keep the literal class name and the word "non-negative" in the message so `tests/seam/test_corpus_status.py:131-135` still passes, or update that unprotected test). In-process callers receive a `pydantic.ValidationError` whose text contains `PageBoundsError`; state that in the `Page` docstring.
- Replace the two `_checked_page` copies (`rest.py:193-211`, `server.py:111-123`) with one `checked_page(limit, offset)` in `corpus.py` that raises the refusals directly (so REST/MCP see the unwrapped class). Remove `ge=0` at `rest.py:380` and `:399` so offset -1 reaches `checked_page` (FastAPI's `ge=0` body is exactly what the requirement forbids). Non-integer `limit=abc` keeps FastAPI's shape (documented).
- `engine.py:878,900`: `next_offset = page.offset + len(documents)`; with limit >= 1 it advances, but guard against a driver returning zero rows below `total` (`next_offset if documents and next_offset < total else None`).
- Test must spy `engine_module.run_corpus_op` and assert zero calls for the refused inputs.

### R-09 SEAM-09 empties
- Query: `query.py:72-86` `check_consumable` treats a member as set when `is not None`; make `text` count only if `text.strip()`; `QueryObject(text='   ')` alone -> `EmptyQueryObjectError`; per the plan-check iteration 1 ruling, empty or whitespace-only text is refused as `EmptyQueryObjectError` whatever other members are set (checked before the consumability check). Called at `engine.py:640` (compare) and `:975` (`_execute`), before any resolution, so no node runs and no trace is persisted.
- Ingest: add to `IngestDocument._exactly_one_payload_shape_within_the_size_cap` (`corpus.py:77-89`): `text` empty/whitespace-only -> new `EmptyIngestDocumentError(member='text')`; `raw` of length 0 -> `member='raw'` (D-08 leaves the name to discretion; `AmbiguousIngestPayloadError` would give a misleading "exactly one of text/raw" message). Raised in a validator, so the message must contain the class name and REST/MCP rely on the unwrap paths.
- Base64: `tools.py:114` `base64.b64decode(self.raw_base64)` -> `base64.b64decode(self.raw_base64, validate=True)`; `binascii.Error` already maps to `MalformedBase64PayloadError` (`:115-116`). `raw_base64=''` decodes to `b''` and is then refused as empty.

### R-10 SEAM-10 `capability: []`
- `selectors.py:149-164` `_match_capability`: `requested <= effects` is vacuously true for an empty set, so the smallest wiring (bypass) wins (`selectors.py:163`); `render_selector_key` renders `""` (`compare.py:58`). Refuse in `resolve_selector` (`selectors.py:237`) with a new `EmptyCapabilitySelectorError` (not in the `Selector` validator: the requirement text says `resolve_selector(Selector(capability=[]))` raises it, which only works if construction succeeds; a validator would also be wrapped). Every route reaches `resolve_selector` (query/stream/compare/ingest/delete/MCP), and compare resolves all selectors before any arm (R-11). `[""]`/`""` already fall to `UnsatisfiableSelectorError`.

### R-11 SEAM-11 - Pattern 4. Sites: `engine.py:597-651`, `:646` (pre-check resolve), `:977` (`_execute` resolve), `compare.py:62-84`.

### R-12 SEAM-12 promote alias
- `engine.py:1148-1190`: after the verb membership/not-built checks (keep D-09 verb order), before `_resolve_operator_preconditions`, refuse an alias that is empty (`''`) or matches `selectors._INSTANCE_HASH_PATTERN` (`selectors.py:88`: `re.compile(r"^(sha256:)?[0-9a-f]{64}$", re.IGNORECASE)`) with a new `InvalidPromotionAliasError(alias=...)` (reusing `ForbiddenSelectorInputError` for the hash case is also allowed by the requirement text; one class for both is simpler). Expose the pattern through a small public helper in selectors that is **not** added to `selectors.__all__`'s transport-called names (the engine, not the transports, calls it). Rollback/retire cannot name an alias that was never minted, so only promote needs it. Note later requirements LEDG-01/02 will edit the same promote prologue (`_resolve_operator_preconditions`): keep this check as its own early block.

### R-13 SEAM-13 upload selector
- `rest.py:370-373`: `Selector.model_validate_json(selector) if selector else None` (empty string already works). Add: treat `selector.strip() == "null"` as `None`. Keep `'{"alias":'` (unparseable) as `MalformedSelectorPayloadError`.

### R-14 SEAM-14 catalogue
- Concrete subclasses today: 27 in `refusals.py` (26 in `__all__` plus `NoRawUploadPathForModalityError` at `refusals.py:149`, missing from `__all__` at `:505-533`) and 3 outside: `trace_store.py:52` `UnknownTraceReferenceError`, `evidence.py:82` `UnresolvableEvidenceReferenceError`, `tokens.py:52` `UnbudgetableParticipantError`. No test or other module defines further `SeamRefusalError` subclasses (grep clean), so the subclass-walk test will not be polluted.
- Move the three into `refusals.py` (no import cycle: the evidence class needs `EvidenceRef` only for annotation, use `Any`/`TYPE_CHECKING`), re-export from the old modules (tests import them from there, e.g. `test_rest_transport.py` factories). Add every new refusal and `NoRawUploadPathForModalityError` to `__all__`.
- Every new class needs a factory entry in `tests/seam/test_rest_transport.py::_REFUSAL_FACTORIES` (`:400-441`), otherwise the exhaustive parametrized test fails by design (unprotected file).

### R-15 SEAM-15 `file_name`/`content_type`
- Both are unused after `IngestDocument` (verified: `engine.ingest` reads only `document_id`, `raw`, `text`; v1 receives `file_paths=[<id>.bin]`). Edit `corpus.py:8-9` ("carried into the job payload for citation" - the stale phrase), `IngestDocument` docstring, add `Field(description="... not stored (discarded at ingest)")` to `IngestDocument.file_name`/`content_type` (`corpus.py:73,75`) and to `IngestToolArgs` (`tools.py:106,108`). The OpenAPI schema then carries "not stored".

### R-16 SEAM-16 docs and dead code
- Stale phrases to remove (exact lines): `rest.py:33-34` ("enumerated at runtime from `SeamRefusalError.__subclasses__()`" - the code registers one base-class handler, matched through the MRO); `selectors.py:35` (`registry is empty`), `:12,19,40,48,186,255-259,294` (`five arms`/empty-registry/`_ARM_NAMES` order claims), `:79-80` (`_DEFAULT_ARM`, `_ARM_NAMES` - delete); `corpus.py:215` ("built only from the server-minted"; `:46-55` already say ids may be caller-supplied); `refusals.py:367` and `rest.py:154-170` / `tools.py:175-187` (JSON `null` or a number "reaches `Databasise.promote()`": a non-string `verb` is a FastAPI validation error; only a non-member *string* gives `UnrecognisedPromotionVerbError`); `tokens.py:14-17` (name the three opaque parts `lightrag/full-ingest`, `lightrag/full-delete`, `codebase-memory-mcp`; `full_delete` always reports `counted_by='unbudgetable'`, `full_ingest` only when v1 returns no usage); `MutableStoreComparisonExcludedError` docstring (`refusals.py:283-299`): unreachable with current query candidates (no `all_wirings()` candidate declares `mutates_store`).
- `redact.py:77,103`: `assert` -> `if ...: raise AssertionError(msg)` (same type, so `pytest.raises(AssertionError)` users and `tests/seam/test_leak.py:341,365` keep working; precedent in `tests/mcp/test_tool_growth_invariant.py:56-60`: "An explicit raise (not `assert`) so it still fires under `python -O`"). Module docstring: state it is a test-time gate, not a response-time check. Only these two production `assert`s exist outside `eval/bundle.py:382,385`.
- `_ARM_NAMES` is imported by a protected test (below).

## Protected test files and existing-test impact

BAK ledger `test_ref` files (verified via `grep -o '"test_ref"'` on `ledger/REQUIREMENTS.json`): `tests/mcp/test_tool_growth_invariant.py`, `tests/clients/test_openai_compat.py`, `tests/foreign/test_mcp_sdk_guard.py`, `tests/clients/test_build_clients.py`, `tests/launcher/test_launchers.py`, `tests/seam/test_rest_cors.py`, `tests/seam/test_rest_corpus_endpoints.py`, `tests/test_check_offline_suite.py`. The hook blocks edits to them and also any shell command whose text names them.

| Needed edit | File:line | Why | Handling |
|-------------|-----------|-----|----------|
| `from databasise.seam.selectors import _ARM_NAMES as _PRODUCTION_ARM_NAMES` -> `from databasise.wirings.resolve import _ARM_NAMES as ...` | `tests/mcp/test_tool_growth_invariant.py:49` | SEAM-16 removes `selectors._ARM_NAMES`; this is its only importer (`resolve.py:30` defines the same tuple) | owner `grant-check-edit`, or sequence the deletion in a plan with a `checkpoint:human-action` |
| `422` -> `404` in `test_get_jobs_for_an_unknown_job_id_returns_422_with_the_refusal_type_name` | `tests/seam/test_rest_corpus_endpoints.py:232-238` | D-03 | owner `grant-check-edit` (this file also carries two ledger test_refs) |

Other tests that need updates (unprotected): `tests/seam/test_delete_document.py:149-160` (malformed id -> `InvalidDocumentIdError`, not `UnknownDocumentError`); `tests/seam/test_rest_transport.py:400-441` (factories for every new class; `ForeignEngineRefusalError` factory keeps `cause=`); `tests/seam/test_corpus_status.py:131-135` (negative offset message, see R-08). Tests that should keep passing unchanged if the Pattern 3 mechanism is used: all ten `pytest.raises(ToolError)` sites (`test_dual_transport_parity.py:201,224,245,260,286,318,652`; `test_dual_transport.py:445,493`; `test_hipporag_write_path.py:338`). Helpers to reuse from the protected file without editing it: `_make_registry`, `_patch_status_and_health`, `_patch_status_sequence`, `_ROUND_TRIP_STATUSES` (imported the same way by `tests/mcp/test_dual_transport_parity.py:74-79`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Unwrapping refusals out of pydantic errors | A regex over the error message text | `err["ctx"]["error"]` instance check (`refusal_from_errors`) | The original exception object is preserved in `ctx.error` `[VERIFIED: prototype]`; message parsing is what the "name in message" convention only exists to work around |
| Schema-error response in the new handler | A copy of FastAPI's `{"detail": ...}` builder | `fastapi.exception_handlers.request_validation_exception_handler` | Keeps the exact documented 4xx shape and JSON-safe encoding |
| Base64 strictness | A custom alphabet check | `base64.b64decode(s, validate=True)` | Raises `binascii.Error` for non-alphabet characters |
| Id/namespace token check | `.match` + `$` | `re.fullmatch` | `$` accepts a trailing newline (reproduced: `a\n` returned 200) |
| In-memory MCP wire test | Hand-built `ServerRequestContext` | `mcp.Client(server)` (`async with`) | Exercises `_handle_call_tool` and the real `CallToolResult` `[VERIFIED: ran this session]` |
| Server-side fault log | print/stderr capture | stdlib `logging` with `exc_info=cause` | Config discretion in CONTEXT; one structured line, e.g. `operation=... failure_class=...` |

**Key insight:** the seam already has one generic mapping per transport; the defect class here is "refusals that never reach the mapping" (pydantic-wrapped, SDK-wrapped, raised as plain `ValueError`/`RuntimeError`). Fix the entry into the mapping, not each site.

## Common Pitfalls

### Pitfall 1: Patching `run_corpus_op` in the wrong module
**What goes wrong:** the new read-op helper lives in another module, so `monkeypatch.setattr(engine_module, "run_corpus_op", ...)` (used by `_patch_status_and_health` and by the SEAM-06 test) no longer intercepts it.
**How to avoid:** keep the helper and the `run_corpus_op` import in `seam/engine.py`; call it by global name at call time.
**Warning signs:** SEAM-06 test passes locally with the real v1 interpreter but fails offline.

### Pitfall 2: `RefusalToolError` subclassing `UnexpectedToolError`
**What goes wrong:** `_handle_call_tool` logs it as a crash (`logger.exception`) and tests that distinguish crash from refusal break.
**How to avoid:** subclass `ToolError` directly; message is exactly `json.dumps(refusal_body(...))`.

### Pitfall 3: Adding names to `selectors.__all__` / `redact.__all__` that a transport calls
**What goes wrong:** the AST proofs (`test_rest_transport.py:182-200`, `test_tool_growth_invariant.py:224-232`) read those lists dynamically and fail the transport module. Calling `refusal_body`/`refusal_from_errors`/`checked_page` from transports is fine (they live in `refusals.py`/`corpus.py`).

### Pitfall 4: Collision tests that use unpromoted aliases
`[{alias:'x'},{harness:'x'}]` etc. give `UnsatisfiableSelectorError` at HEAD; the "fails today" behaviour only appears when the aliases exist. Promote `default`, `x`, `a+b` first (with a real trace token) so the test fails at HEAD for the right reason and passes only when keys are checked before resolution.

### Pitfall 5: Mutating a shared resolved wiring
`resolve_selector` returns fresh dicts per call (`all_wirings()` -> `resolve_arm`), and `_inject_query` / `_inject_token_allowance` mutate them in place. Resolving once and passing each dict to exactly one `_execute_resolved` is safe; passing one dict to two arms would not be.

### Pitfall 6: `Page(limit=0)` vs internal `limit: 0`
`document_counts` (`engine.py:908-913`) calls `run_corpus_op("status", {"limit": 0, ...})` directly. Do not route it through `Page`.

### Pitfall 7: `UnknownJobError` swallowed by a broad `except ValueError`
It is a `SeamRefusalError`, a `ValueError` subclass. Keep the `total == 0` raise outside any parse-error wrapper.

### Pitfall 8: Offline guard
The autouse fixture `_offline_unless_live` in `tests/conftest.py` (line 97) blocks non-loopback sockets. In-memory `mcp.Client(server)` and `TestClient` are unaffected; do not start a real HTTP/stdio server in a Phase 9 test.

## Code Examples

### Evidence guard (R-01)
```python
# seam/evidence.py
_NAMESPACE_RE = re.compile(r"[A-Za-z0-9-]+")
def validate_evidence_namespace(namespace: str) -> None:
    if not _NAMESPACE_RE.fullmatch(namespace):
        raise InvalidEvidenceNamespaceError(namespace=namespace)

# seam/engine.py
async def resolve_evidence(self, ref):
    validate_evidence_namespace(ref.namespace)
    if not (self.store_root / self.workspace / ref.namespace).is_dir():
        raise UnresolvableEvidenceReferenceError(ref)
    vector = MultiNamespaceVectorStore(workspace=self.workspace, store_root=self.store_root)
    try:
        return resolve_evidence_ref(ref, vector)
    finally:
        await vector.finalize()
```

### Wire-level MCP assertion (SEAM-03 test)
```python
mcp = import_sdk("mcp")
async with mcp.Client(server) as client:
    result = await client.call_tool("ingest", {"args": {}})
assert result.is_error
body = json.loads(result.content[0].text)          # bare JSON, no prefix
assert body["refusal_type"] == "AmbiguousIngestPayloadError"
```

### Page bounds (R-08)
```python
def checked_page(limit: int, offset: int) -> Page:
    if limit > MAX_PAGE_SIZE: raise PageSizeExceededError(requested=limit, limit=MAX_PAGE_SIZE)
    if limit < 1 or offset < 0: raise PageBoundsError(limit=limit, offset=offset)
    return Page(limit=limit, offset=offset)
```

## State of the Art

| Old (HEAD) | Target | Impact |
|------------|--------|--------|
| 3 error shapes (refusal body, FastAPI `detail`, SDK text) | refusal body everywhere + FastAPI schema shape as the only other 4xx | consumers branch on `refusal_type` only |
| Uniform 422 | 404 / 422 / 502 / 503 by one mapping | GUI can branch on status and on `refusal_type` |
| `ForeignEngineRefusalError` as a 422 with stderr | 5xx fault with `failure_class` only | no path/env-var disclosure |

Deprecated: `rest._refusal_response`'s inline dump and `mcp.server._refusal_detail`/`_refusal_mapped`/`_checked_page` (replaced by shared helpers).

## Suggested plan decomposition (file ownership, to avoid same-file parallel conflicts)

`engine.py` is touched by SEAM-01/05/06/07/08/09?/11/12; `refusals.py` by nearly all. Serialise those.

1. **Plan A (kit):** `refusals.py` catalogue + all new classes + `refusal_body`/`refusal_from_errors` + `ForeignEngineRefusalError` rework; re-exports in `evidence.py`/`trace_store.py`/`tokens.py`; `test_refusal_catalogue.py`, factories in `test_rest_transport.py`. (SEAM-14; prerequisite for all.)
2. **Plan B (REST):** handlers, `_status_for`, `responses=`, upload parse (`null`), `Query(ge=0)` removal, docstrings; `test_refusal_body_shape.py`, `test_refusal_status_codes.py`, `test_upload_selector_field.py`. (SEAM-02/04/13 + REST half of 05/06.)
3. **Plan C (MCP):** `_DatabasiseServer`/`RefusalToolError`, scope refusal, delete `_refusal_mapped`, base64 `validate=True`, docstring; `tests/mcp/test_mcp_refusal_mapping.py`. (SEAM-03.)
4. **Plan D (engine inputs):** `corpus.py` (ids, empties, `Page`, `checked_page`), `query.py`, `resolve_evidence`, foreign helper + `next_offset` guard; tests `test_evidence_namespace_guard.py`, `test_ingest_input_refusals.py`, `test_page_bounds.py`, `test_empty_inputs.py`, `test_foreign_engine_refusal.py`, `test_corpus_adapter_failures.py`. (SEAM-01/05/06/07/08/09.)
5. **Plan E (selectors/compare/promote):** `selectors.py`, `compare.py`, `engine.compare/_execute_resolved/promote`; tests `test_empty_capability_selector.py`, `test_compare_keys.py`, `test_promote_alias_validation.py`. (SEAM-10/11/12.)
6. **Plan F (docs + owner checkpoint):** SEAM-15/16 docstrings, `redact.py`, dead-code removal behind the owner's `grant-check-edit` for `test_tool_growth_invariant.py`; `test_ingest_file_name.py`, `test_seam_doc_consistency.py`. Then the owner-approved ledger `test_ref` step (Open Question 7).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Starlette spools multipart file parts to a temp file before the route runs, so the 25 MiB cap cannot prevent the temp write | R-07 | Low; the cap would still hold at the DTO. Out of scope either way |
| A2 | Mixed (refusal + schema) validation errors should surface the refusal | R-02 | Low; requirement only specifies each case separately |
| A3 | Non-refusal selector form errors keep `MalformedSelectorPayloadError` | R-02 | Low; only the refusal-bearing case is specified |
| A4 | Public `failure_class` tokens (`MalformedDriverOutput`, `UnclassifiedEngineFailure`) are acceptable names | Pattern 5 | Low; D-04 names only the first three classes; it is Claude's discretion |
| A5 | Launcher 403 `{"detail": ...}` / TrustedHost 400 text stay as-is | Open Q 3 | Medium; owner may want one shape there too |
| A6 | `EmptyIngestDocumentError` / `EmptyCapabilitySelectorError` / `InvalidPromotionAliasError` / `MissingScopeArgumentError` as class names | R-09/10/12/03 | Low; discretion area |
| A7 | Satisfying D-02 via a raised `ToolError` subclass (wire result is `CallToolResult(isError=True)`) rather than a returned `CallToolResult` matches the owner's intent | Pattern 3 | Low; the wire bytes are identical, and REQUIREMENTS SEAM-03's test wording ("raises a ToolError") matches this mechanism |

## Open Questions (RESOLVED)

1. **SEAM-03 mechanism: raise vs return** - D-02 says `CallToolResult(isError=True)`; REQUIREMENTS' test says "raises a ToolError".
   - **RESOLVED (by D-02, mechanism verified):** raise `RefusalToolError(ToolError)` from `call_tool`; the SDK converts it to `CallToolResult(is_error=True)` with the bare JSON as text. Prove with `mcp.Client` and with `pytest.raises(ToolError)` both.
2. **Two edits to ledger-protected test files** (`test_tool_growth_invariant.py:49`; `test_rest_corpus_endpoints.py:237`).
   - **RESOLVED (owner checkpoints planned):** `test_rest_corpus_endpoints.py` is granted at 09-02 Task 2 and `test_tool_growth_invariant.py` at 09-10 Task 2, each a blocking `checkpoint:human-action` naming the exact one-line edit. Until granted, do not delete `selectors._ARM_NAMES` and expect `test_get_jobs_for_an_unknown_job_id...` to fail on the 404.
3. **Launcher guard bodies** (`serve_rest.py:61` `{"detail": "origin not allowed"}` 403; Starlette TrustedHost 400 text) are not `SeamRefusalError`s and are pinned by `tests/launcher/test_bind_guard.py:155`.
   - **RESOLVED (locked as D-13):** leave unchanged; the `rest.py` module docstring (09-01 Task 1) and the `serve_rest.build_app` docstring state that they are transport guards in front of the seam. Owner can reopen; changing them needs `grant-check-edit` on `tests/launcher/*`.
4. **Name/shape of the empty-ingest refusal** (D-08 leaves the name open).
   - **RESOLVED (Claude's discretion):** `EmptyIngestDocumentError(member)`.
5. **Names for `capability: []` and promote alias refusals.**
   - **RESOLVED (Claude's discretion):** `EmptyCapabilitySelectorError`, `InvalidPromotionAliasError`.
6. **Where `capability: []` is refused.**
   - **RESOLVED:** in `resolve_selector` (REQUIREMENTS test text), not in the `Selector` validator.
7. **BAK ledger `test_ref` for SEAM-01..16** (rows exist with empty `test_ref`; the ledger is frozen except via `scripts/ledger-amend.py`).
   - **RESOLVED (post-verification ledger step, outside the code plans):** after verification passes, the orchestrator runs a final owner-approved ledger step as in Phase 8 (`d505c5d chore(bak): set test_refs for RUN-01..`). Not part of the code plans. Note the ledger gate currently reports RUN-01..12 open (Phase 8 leftovers, RUN-11 live items) - not Phase 9's to close.
8. **Generic non-refusal exceptions still produce text/plain 500** (e.g. the cyclic-wiring `RuntimeError`, `MalformedEvidenceItemError`).
   - **RESOLVED (out of scope):** success criterion 3 covers v1 engine failures; D-01..D-11 add no catch-all. Candidate for a later hardening item.
9. **Upload temp-file / body-size limits.**
   - **RESOLVED (out of scope):** `rest.py` exposure note makes body-size limits the operator's boundary.
10. **`stop_reason` text names internal node ids** (seen in degraded `/query` envelopes during the repro).
    - **RESOLVED (assigned to WIRE-03, Phase 13):** not a SEAM requirement; WIRE-03 owns node-free `stop_reason`/`degradation_reason` text.
11. **COVERAGE.md rows** - no new routes or tools are added by this phase and the table has no status-code column (`databasise/evidence/COVERAGE.md:89-112`).
    - **RESOLVED:** no COVERAGE.md edit required; `test_every_tool_has_a_coverage_row...` is unaffected. If a plan adds a route or tool anyway, add its row and map it in `_OPERATION_TO_TOOLS` (protected test).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv + project venv | all tests | yes | `databasise/.venv`, Python 3.12 | — |
| fastapi / starlette / httpx (TestClient) | REST tests | yes | 0.141.1 / 1.6.0 / 0.28.1 | — |
| mcp SDK | MCP tests, `mcp.Client` | yes | 2.2.0 | — |
| v1 interpreter `v1/.venv/bin/python` | only live/real-driver paths | present (health reports `interpreter_present: true`) | — | all Phase 9 tests use stubs/monkeypatch (`tests/fixtures/v1_corpus_driver_stub.py`, `_patch_status_and_health`); never run `-m live` |

**Missing dependencies with no fallback:** none. **Note:** a scratch run printed a `pandas feature was requested` traceback from `pycozo` on stderr for every Cozo open; it is noise, not a failure.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio (`asyncio_mode = "auto"`), `-m "not live"` by default |
| Config file | `databasise/pyproject.toml` `[tool.pytest.ini_options]` (lines 109-113) |
| Quick run command | `cd databasise && uv run pytest tests/seam/<file>.py -q -x` |
| Full suite command | `cd databasise && uv run pytest -q -rs` (baseline 1251 passed, 1 skipped, 4 deselected, 224.57 s) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SEAM-01 | namespace guard, no dirs, valid refs still resolve | integration (TestClient + MCP) | `cd databasise && uv run pytest tests/seam/test_evidence_namespace_guard.py -q` | Wave 0 (new) |
| SEAM-02 | refusal body, no `detail`, oversize < 4 KB, upload rule refusal | integration | `... tests/seam/test_refusal_body_shape.py -q` | Wave 0 (new) |
| SEAM-03 | MCP bare JSON for 8 listed calls + NoWritePath delete; wire-level via `mcp.Client` | integration | `... tests/mcp/test_mcp_refusal_mapping.py -q` | Wave 0 (new) |
| SEAM-04 | 404 for four lookups, 422 for `PageSizeExceededError` | integration | `... tests/seam/test_refusal_status_codes.py -q` | Wave 0 (new) |
| SEAM-05 | 3,000-char stderr with `/home/` + `Traceback` -> 5xx, body < 1 KB, clean; MCP same | integration | `... tests/seam/test_foreign_engine_refusal.py -q` | Wave 0 (new) |
| SEAM-06 | 4 exception types x 3 read routes -> SEAM-05 status + JSON; `/health` 200; OpenAPI declares 502/503 | integration (parametrised) | `... tests/seam/test_corpus_adapter_failures.py -q` | Wave 0 (new) |
| SEAM-07 | 26,214,401-byte upload 422; ids `../x`, `a.b`, `a\n` on 4 entry points; delete spy zero calls; inbox empty | integration | `... tests/seam/test_ingest_input_refusals.py -q` | Wave 0 (new) |
| SEAM-08 | limit 0/-1/-5, offset -1 on REST + MCP, `run_corpus_op` spy zero calls, `Page(limit=0)` | integration + unit | `... tests/seam/test_page_bounds.py -q` | Wave 0 (new) |
| SEAM-09 | `''`/whitespace query (zero stub calls, no trace row), empty ingest/upload (inbox empty), MCP bad base64 | integration | `... tests/seam/test_empty_inputs.py -q` | Wave 0 (new) |
| SEAM-10 | `Selector(capability=[])` refusal on query/compare/ingest; zero LLM calls | unit + integration | `... tests/seam/test_empty_capability_selector.py -q` | Wave 0 (new) |
| SEAM-11 | 4 colliding pairs (aliases promoted first): zero calls, trace rows unchanged; resolve-once hook test; `answer` alias rule | integration | `... tests/seam/test_compare_keys.py -q` | Wave 0 (new) |
| SEAM-12 | alias `''` and `sha256:`+`b`*64 -> 422, ledger count unchanged; valid alias promotes then queries | integration | `... tests/seam/test_promote_alias_validation.py -q` | Wave 0 (new) |
| SEAM-13 | upload selector `null`/`''`/omitted -> 200; `'{"alias":'` -> 422 Malformed | integration | `... tests/seam/test_upload_selector_field.py -q` | Wave 0 (new) |
| SEAM-14 | every `SeamRefusalError` subclass name in the catalogue | unit | `... tests/seam/test_refusal_catalogue.py -q` | Wave 0 (new) |
| SEAM-15 | OpenAPI field descriptions contain "not stored"; `corpus.py` no longer says "carried into the job payload for citation" | unit | `... tests/seam/test_ingest_file_name.py -q` | Wave 0 (new) |
| SEAM-16 | no `_DEFAULT_ARM`/`_ARM_NAMES`; verb null -> FastAPI shape, bad string -> `UnrecognisedPromotionVerbError`; `python -O` subprocess raises; stale phrases absent | unit + subprocess | `... tests/seam/test_seam_doc_consistency.py -q` | Wave 0 (new) |

### Sampling Rate
- **Per task commit:** the single new test file for the task, plus `cd databasise && uv run pytest tests/seam/test_rest_transport.py tests/mcp -q` when `refusals.py`, `rest.py` or `server.py` changed (~1 min).
- **Per wave merge:** `cd databasise && uv run pytest tests/seam tests/mcp tests/parts_core -q`.
- **Phase gate:** full suite green (baseline 1251 passed + new tests, 0 failed) before `/gsd-verify-work`.

### Wave 0 Gaps
- [ ] The 16 new test files above (all new; names are fixed by REQUIREMENTS.md).
- [ ] Shared helper for tests: promote an alias with a real trace token (pattern in the scratch repro: query with stub clients over `synthetic_naive_store`, then `POST /promote`); a stub-client builder (`_stub_clients` in `tests/mcp/test_dual_transport_parity.py:109`).
- [ ] Update `_REFUSAL_FACTORIES` and the two unprotected tests listed under "Protected test files and existing-test impact".
- [ ] Owner `grant-check-edit` for the two protected edits (Open Question 2).
- Framework install: none.

## Security Domain

`workflow.security_enforcement` is explicitly `false` in `.planning/config.json`; this short section is included because the phase goal is input/disclosure hardening.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | `fullmatch` allow-list regexes, pydantic validators, `b64decode(validate=True)`, size cap, named refusals before side effects |
| V7 Error Handling | yes | one refusal shape; machine faults carry only operation + failure class; full cause logged server-side |
| V12 File/Resources | yes | no caller string joins into a path before validation; no directory creation on lookup paths |
| V2/V3/V4 (authn/session/authz) | no | seam authentication stays an open owner decision (CONN phases) |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via evidence namespace (`../../x`, absolute path) | Tampering | `fullmatch` allow-list + `is_dir()` pre-check, before any store |
| Document id with trailing newline / separators | Tampering | `fullmatch` in `generated_on_disk_name`, raised before any write |
| Stderr / traceback / absolute path / env-var name disclosure in errors | Information disclosure | private `_cause`, allow-listed `failure_class`, server-side log only |
| Oversized body echoed back (26 MB response) | DoS / disclosure | refusal body never echoes input |
| Empty documents enqueued (0-byte file written to `corpus-inbox`) | Tampering / DoS | `IngestDocument` empty rule before the write |

## Sources

### Primary (HIGH confidence) - read or executed this session
- `databasise/seam/{refusals,rest,engine,corpus,selectors,compare,evidence,query,redact,tokens,trace_store}.py`, `databasise/mcp/{server,tools,_sdk}.py`, `databasise/foreign/{v1_corpus_adapter,__init__,_mcp_sdk_guard}.py`, `databasise/launcher/{__init__,serve_rest}.py`, `databasise/namespaces.py`, `databasise/stores/vector.py`
- `.venv/lib/python3.12/site-packages/mcp/server/mcpserver/{server.py,exceptions.py,tools/base.py,utilities/func_metadata.py}` (SDK 2.2.0)
- Scratch repro scripts and prototypes (session scratchpad): REST/MCP repro, compare/promote repro, fault repro, `RequestValidationError` ctx.error prototype, `mcp.Client` in-memory prototype, `python -O` redact check
- `.planning/REQUIREMENTS.md` SEAM-01..16, `.planning/ROADMAP.md` Phase 9, `docs/gui/DEFECTS.json` cited uids, `ledger/REQUIREMENTS.json` `test_ref` list
- Offline suite run: `1251 passed, 1 skipped, 4 deselected in 224.57s`

### Secondary / Tertiary
- None. No web sources were needed or used.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no change, versions read from the venv
- Architecture / mechanisms: HIGH - SDK behaviour read from source and confirmed with in-memory client; FastAPI `ctx.error` confirmed by prototype
- Pitfalls: HIGH - each reproduced or found by reading call sites
- Open decisions: MEDIUM for A5/A7 (owner intent), everything else locked by CONTEXT

**Research date:** 2026-10-16
**Valid until:** 2026-11-15 (code is local; re-check only if `mcp`, `fastapi` or `starlette` are upgraded, since the plan leans on SDK internals `ToolError` re-wrapping and `_handle_call_tool`)
