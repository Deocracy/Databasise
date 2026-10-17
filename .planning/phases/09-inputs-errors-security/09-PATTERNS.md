# Phase 9: Inputs, Errors & Security - Pattern Map

**Mapped:** 2026-10-16
**Files analyzed:** 22 (14 modified source, 1 optional, 7 test groups)
**Analogs found:** 22 / 22 (all in-repo; every file is its own analog because this is brownfield hardening)

All paths are under `databasise/` and are git-tracked (`git ls-files seam mcp` verified). Line numbers are HEAD. Line numbers inside `09-RESEARCH.md` "Requirement implementation map" are the authoritative edit sites; this file supplies the code to copy.

## File Classification

| File | Role | Data Flow | Closest Analog | Match |
|------|------|-----------|----------------|-------|
| `seam/refusals.py` (catalogue, new refusals, `refusal_body`, `refusal_from_errors`, Foreign rework) | model/exception | request-response | itself: `PageSizeExceededError` (190-206), `ForeignEngineRefusalError` (490-502) | exact |
| `seam/rest.py` (handlers, `_status_for`, `responses=`) | route/transport | request-response | itself: `_refusal_response` (~214-240), registration `add_exception_handler` | exact |
| `mcp/server.py` (`MCPServer` subclass, `RefusalToolError`, scope refusals) | transport | request-response | itself: `_refusal_detail`/`_refusal_mapped` (79-106), `_status_job` etc. (126-170) | exact |
| `mcp/tools.py` (`validate=True`, Field descriptions) | DTO | transform | itself: `IngestToolArgs.to_ingest_document` (111-125) | exact |
| `seam/corpus.py` (`InvalidDocumentIdError`, `Page`, `checked_page`, empties) | model/validator | transform | itself: `IngestDocument` validator (77-89), `Page._bounded` (122-140) | exact |
| `seam/engine.py` (resolve_evidence, compare order, `_corpus_op_or_refuse`, promote alias) | service | CRUD / request-response | itself: `_node_result_or_refuse` (366-395), `compare` (636-651), `get_job_status` (855-885) | exact |
| `seam/compare.py` (`comparison_keys`) | utility | transform | itself: `compare_arms` (62-84) | exact |
| `seam/evidence.py` (`validate_evidence_namespace`) | utility | transform | `seam/corpus.py` `_DOCUMENT_ID_TOKEN_RE` + `generated_on_disk_name` | role-match |
| `seam/query.py` (whitespace rule) | validator | transform | itself: `check_consumable` (72-86) | exact |
| `seam/selectors.py` (`EmptyCapabilitySelectorError`, `MultiMemberSelectorError`, dead code) | validator | transform | itself: validators 104-127, `resolve_selector` 237 | exact |
| `seam/redact.py` (`assert` to explicit raise) | utility | transform | `tests/mcp/test_tool_growth_invariant.py:56-60` explicit-raise precedent | role-match |
| `seam/tokens.py`, `seam/trace_store.py` (re-exports, docstring) | model | n/a | `seam/seam/refusals.py` re-export pattern (research R-14) | role-match |
| New tests (16 files, `tests/seam/*`, `tests/mcp/test_mcp_refusal_mapping.py`) | test | request-response | `tests/seam/test_rest_transport.py`, `tests/mcp/test_dual_transport_parity.py` | role-match |

## Pattern Assignments

### `seam/refusals.py` (new refusals + shared kit)

**Imports/house style** (lines 1-17): module docstring rule "name only the consumer's own input, never machine wirings/arms/node ids"; `from __future__ import annotations`; `from typing import Any`. Add `from pydantic import BaseModel` for `refusal_body`; do not import fastapi or mcp here.

**New refusal template** (copy from `PageSizeExceededError`, 190-206):
```python
class PageSizeExceededError(SeamRefusalError):
    def __init__(self, *, requested: int, limit: int):
        self.requested = requested
        self.limit = limit
        # literal class name in message is load-bearing: pydantic wraps validator-raised refusals
        super().__init__(
            f"PageSizeExceededError: requested page size {requested} exceeds the {limit}-entry cap"
        )
```
Apply to: `InvalidEvidenceNamespaceError(namespace)`, `InvalidDocumentIdError(document_id)`, `PageBoundsError(limit, offset)`, `EmptyIngestDocumentError(member)`, `EmptyCapabilitySelectorError`, `InvalidPromotionAliasError(alias)`, `MultiMemberSelectorError(set_members)`, `MissingScopeArgumentError(tool, scope, argument)`. Keyword-only args, public attribute = the caller's own value, class name in message when raised inside a pydantic validator (`Page`, `IngestDocument`, `Selector`). Add each to `__all__` (505-533; `NoRawUploadPathForModalityError` at 149 is missing from it today).

**Foreign fault rework** (current, 490-502, to replace):
```python
def __init__(self, *, operation: str, cause: BaseException):
    self.operation = operation
    self.cause = cause                       # public: leaks into vars(exc) wire dump
    super().__init__(f"the foreign engine refused operation {operation!r}: {cause}")  # leaks stderr
```
Target (research Pattern 5): keep `cause=` kwarg; store `self._cause` (leading underscore, skipped by dump); add public `failure_class`; `cause` as a `@property`; message = operation + failure class only.

**Shared kit** (research Pattern 1): `refusal_body(exc)` is the verbatim body of `rest._refusal_response` (lines ~230-240) and `mcp.server._refusal_detail` (79-92): `{"refusal_type": type(exc).__name__, "message": str(exc)}` then loop `vars(exc)`, skip `key.startswith("_")`, `model_dump()` BaseModel values. Delete the `BaseException -> str(value)` branch (no public exception attrs remain). `refusal_from_errors(errors)` walks `err["ctx"]["error"]` for a `SeamRefusalError`.

### `seam/rest.py`

**Existing handler to replace** (`_refusal_response`, ~214-240, registered `app.add_exception_handler(SeamRefusalError, _refusal_response)`):
```python
return JSONResponse(status_code=_REFUSAL_STATUS_CODE, content=detail)
```
Change to `status_code=_status_for(exc), content=refusal_body(exc)`. Replace `_REFUSAL_STATUS_CODE = 422` (line ~102) and its comment (98-101) with the `_NOT_FOUND` tuple + `_status_for` (research Pattern 2). Register two extra handlers beside it: `RequestValidationError` (fallback delegates to `fastapi.exception_handlers.request_validation_exception_handler`, never serialises `exc.errors()`) and `pydantic.ValidationError` (re-raise if no refusal found).

**`_checked_page`** (~193-211): replace with import of `corpus.checked_page`; remove `Query(ge=0)` at ~380 and ~399. Docstring there documents the pydantic-wrap mechanism; keep the reasoning, move it to `corpus.py`.

**Upload route** (~363-374): wrap `IngestDocument(...)` in `except ValidationError as exc: refusal_from_errors(exc.errors())`; selector parse: `Selector.model_validate_json(selector) if selector and selector.strip() != "null" else None`.

**OpenAPI**: add `responses={502: {...}, 503: {...}}` with a small `RefusalBody` model (`extra="allow"`) to the six routes listed in research R-05/06.

### `mcp/server.py`

**Existing mapping to delete** (79-106):
```python
def _refusal_mapped(fn):
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await fn(*args, **kwargs)
        except SeamRefusalError as exc:
            raise ToolError(json.dumps(_refusal_detail(exc))) from exc
```
Replace with `_DatabasiseServer(MCPServer).call_tool` override raising `RefusalToolError(ToolError)` (research Pattern 3). SDK classes come via `import_sdk` (lines 70-72), never bare `import mcp`:
```python
MCPServer = import_sdk("mcp.server.mcpserver").MCPServer
ToolError = import_sdk("mcp.server.mcpserver.exceptions").ToolError
```
**Scope preconditions** (128, 161, 167): `raise ToolError("status tool: scope 'job' requires a job_id")` and siblings become `raise MissingScopeArgumentError(tool="status", scope="job", argument="job_id")`.
**`_checked_page` copy** (111-123): delete; import shared `checked_page`. `mcp/` must not import fastapi (import `refusals.py`/`corpus.py` only).

### `mcp/tools.py` (`IngestToolArgs`, 100-125)

```python
raw = base64.b64decode(self.raw_base64)          # add validate=True
except binascii.Error as exc:
    raise MalformedBase64PayloadError(field="raw_base64") from exc
```
Add `Field(description="... not stored (discarded at ingest)")` on `file_name`/`content_type` (lines ~106/108).

### `seam/corpus.py`

**Id regex** (56): `re.compile(r"^[A-Za-z0-9_-]+$")` used with `.match` at ~221; switch to `fullmatch` and raise `InvalidDocumentIdError` inside `generated_on_disk_name`.
**IngestDocument validator** (77-89) is the place for the empty rule; copy its structure:
```python
set_members = [name for name in ("text", "raw") if getattr(self, name) is not None]
if len(set_members) != 1:
    raise AmbiguousIngestPayloadError(set_members=set_members)
if self.raw is not None and len(self.raw) > MAX_DOCUMENT_BYTES:
    raise OversizedDocumentError(actual_bytes=len(self.raw), limit_bytes=MAX_DOCUMENT_BYTES)
```
Add after the size checks: `text.strip() == ""` or `len(raw) == 0` -> `EmptyIngestDocumentError(member=...)`.
**Page** (122-140): add `limit < 1 or offset < 0 -> PageBoundsError` in `_bounded` (replace the plain `ValueError` at the offset branch; keep "non-negative" wording so `tests/seam/test_corpus_status.py:131-135` passes). Add module-level `checked_page` (research "Page bounds (R-08)").

### `seam/engine.py`

**Foreign fault site** (`_node_result_or_refuse`, 366-395): keep signature; construct `ForeignEngineRefusalError(operation=..., cause=node_exception)` as today, add one server-side `logger.error(..., exc_info=cause)` where it is built.
**Read ops** (`get_job_status` ~855-885): current shape is `await asyncio.to_thread(run_corpus_op, "status", {...}, timeout=STATUS_WALL_CLOCK_CEILING_SECONDS)` followed by `int(result.get("total", 0))` / `UnknownJobError` / `DocumentStatusEntry(**doc)`. Replace the call with `_corpus_op_or_refuse(...)` that stays in this module and calls `run_corpus_op` by global name (monkeypatch target, Pitfall 1). Keep `UnknownJobError` raise outside the parse wrapper (Pitfall 7). Same for `corpus_status` (~885-905) and `document_counts` (908-913; keep internal `limit: 0`, bypass `Page`).
**compare** (636-651), current:
```python
check_consumable(query_object, self.registry)
if len(selectors) == 0: raise EmptyComparisonRequestError()
if len(selectors) == 1: return await self._execute(query_object, selectors[0])
for selector in selectors:
    resolved = resolve_selector(selector, registry=self.registry, store_root=self.store_root)
    if "mutates_store" in _wiring_effects(resolved, self.registry):
        raise MutableStoreComparisonExcludedError(component=_mutates_store_component(resolved, self.registry))
return await compare_arms(self._execute, query_object, selectors)
```
Target (research Pattern 4): `comparison_keys(selectors)` first, resolve all once into a list, keep the `mutates_store` loop over that list, then `_execute_resolved` per pre-resolved wiring. Split `_execute` (~975, resolve at ~977) into `check_consumable` + `resolve_selector` + `_execute_resolved`.
**ingest** (679, 683): `document.document_id if document.document_id is not None else uuid.uuid4().hex`; drop the delete wrapper that rewraps to `UnknownDocumentError` (801-804).
**resolve_evidence** (1085-1096): code in research "Code Examples / Evidence guard (R-01)". **promote** (1148-1190): own early block after verb checks, before `_resolve_operator_preconditions`.

### `seam/compare.py`

`compare_arms` (62-84) is the analog for `comparison_keys`:
```python
results = {}
for selector in selectors:
    key = render_selector_key(selector)
    if key in results:
        raise DuplicateComparisonKeyError(key=key)
```
`comparison_keys` returns the list of keys with the same raise; `compare_arms` keeps its signature (exported at `seam/__init__.py:15,27`) and calls `comparison_keys` first.

### `seam/query.py`, `seam/selectors.py`, `seam/redact.py`

- `query.py:72-86` `check_consumable`: "set" test becomes `text is not None and text.strip()` for the text member only.
- `selectors.py:108` plain `ValueError` -> `MultiMemberSelectorError(set_members=...)`; `resolve_selector` (237) gets the `capability == []` refusal; delete `_DEFAULT_ARM`/`_ARM_NAMES` (79-80) only after the owner edits `tests/mcp/test_tool_growth_invariant.py:49`.
- `redact.py:77,103`: `assert cond, msg` -> `if not cond: raise AssertionError(msg)` (precedent: `tests/mcp/test_tool_growth_invariant.py:56-60`).

### Tests (new)

**Analog for transport tests:** `tests/seam/test_rest_transport.py` (factory table `_REFUSAL_FACTORIES`, 400-441; AST proofs 182-200 forbid transports calling names in `selectors.__all__`/`redact.__all__`). Each new refusal needs an entry, e.g.:
```python
PageSizeExceededError: lambda: PageSizeExceededError(requested=101, limit=100),
ForeignEngineRefusalError: lambda: ForeignEngineRefusalError(operation="ingest", cause=RuntimeError("stub subprocess failure")),
```
**MCP wire test:** `mcp = import_sdk("mcp"); async with mcp.Client(server) as client: result = await client.call_tool(...)`; assert `result.is_error` and `json.loads(result.content[0].text)["refusal_type"]`. Stub-client builder: `_stub_clients` in `tests/mcp/test_dual_transport_parity.py:109`. Reuse (without editing) `_make_registry`, `_patch_status_and_health` from the protected `tests/seam/test_rest_corpus_endpoints.py`.

## Shared Patterns

### Refusal body (one definition)
**Source:** `refusals.refusal_body` (new), extracted from `rest.py` `_refusal_response` and `mcp/server.py` `_refusal_detail`. **Apply to:** REST handlers, MCP `call_tool` override.

### Validator-raised refusals carry the class name in the message
**Source:** `refusals.py` 190-206 comment. **Apply to:** every refusal raised inside `Page`, `IngestDocument`, `Selector` validators; transports unwrap via `ctx.error`.

### Private attributes never on the wire
**Source:** `rest.py` `_refusal_response` docstring (CR-03), `tokens.py` `_internal_node_id`. **Apply to:** `ForeignEngineRefusalError._cause`.

### Allow-list `fullmatch` for ids and namespaces
**Source:** `corpus.py:56` regex; `namespaces.py:37` `_NAMESPACE_TOKEN_RE`. **Apply to:** evidence namespace, document id. Never `.match` plus `$`.

### Module-global `run_corpus_op` in `engine.py`
**Apply to:** all read-op helpers; tests monkeypatch `engine_module.run_corpus_op`.

### Transport thinness
Routes and tool bodies make one awaited engine call; no selector resolution or redaction in `rest.py`/`mcp/`.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `RefusalToolError` / `_DatabasiseServer.call_tool` override in `mcp/server.py` | transport | request-response | No existing `MCPServer` subclass; use research Pattern 3 (verified against SDK 2.2.0) |
| `RequestValidationError` / `pydantic.ValidationError` handlers in `rest.py` | transport | request-response | No existing validation-error handler; use research Pattern 2 |

## Protected files (owner `grant-check-edit` needed; hook also blocks shell commands naming them)

`tests/mcp/test_tool_growth_invariant.py:49` (`_ARM_NAMES` import) and `tests/seam/test_rest_corpus_endpoints.py:232-238` (422 to 404). Others on the BAK list: `tests/clients/test_openai_compat.py`, `tests/foreign/test_mcp_sdk_guard.py`, `tests/clients/test_build_clients.py`, `tests/launcher/test_launchers.py`, `tests/seam/test_rest_cors.py`, `tests/test_check_offline_suite.py`.

## Metadata

**Analog search scope:** `databasise/seam/`, `databasise/mcp/`, `databasise/tests/seam/`, `databasise/tests/mcp/`
**Files scanned:** about 12 read directly; remaining line sites taken from 09-RESEARCH.md (verified there this session)
**Pattern extraction date:** 2026-10-16
