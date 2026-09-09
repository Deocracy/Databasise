---
phase: 05-opaque-side-admission
reviewed: 2026-09-08T00:00:00Z
depth: standard
files_reviewed: 58
files_reviewed_list:
  - databasise/evidence/ADMISSION-CODEBASE-MEMORY-MCP.md
  - databasise/evidence/DR-04-DECISION.md
  - databasise/evidence/FALSIFIER-2-EVIDENCE.md
  - databasise/evidence/FALSIFIER-4-EVIDENCE.md
  - databasise/evidence/INJECTED-LLM-ENDPOINT-SURVEY.md
  - databasise/foreign/__init__.py
  - databasise/foreign/_mcp_sdk_guard.py
  - databasise/foreign/codebase_memory_mcp_adapter.py
  - databasise/foreign/v1_corpus_adapter.py
  - databasise/foreign/v1_corpus_driver_script.py
  - databasise/mcp/__init__.py
  - databasise/mcp/_sdk.py
  - databasise/mcp/server.py
  - databasise/mcp/tools.py
  - databasise/parts/admission.py
  - databasise/parts/registry.py
  - databasise/parts/schema.py
  - databasise/parts_core/codebase_memory_mcp.py
  - databasise/parts_core/declared_only.py
  - databasise/parts_core/lightrag/OPAQUE-BOUNDARY-RULE.md
  - databasise/parts_core/lightrag/full_delete.py
  - databasise/parts_core/lightrag/full_ingest.py
  - databasise/pyproject.toml
  - databasise/runner/scheduler.py
  - databasise/seam/corpus.py
  - databasise/seam/engine.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/tests/_ast_helpers.py
  - databasise/tests/evidence/__init__.py
  - databasise/tests/evidence/test_admission_docs.py
  - databasise/tests/evidence/test_falsifier4_evidence.py
  - databasise/tests/fixtures/codebase_memory_mcp_raw_items.json
  - databasise/tests/fixtures/v1_corpus_driver_stub.py
  - databasise/tests/mcp/test_dual_transport_parity.py
  - databasise/tests/mcp/test_tool_growth_invariant.py
  - databasise/tests/parts/test_admission.py
  - databasise/tests/parts/test_registry.py
  - databasise/tests/parts_core/lightrag/test_full_delete.py
  - databasise/tests/parts_core/lightrag/test_full_ingest.py
  - databasise/tests/parts_core/lightrag/test_full_ingest_compat.py
  - databasise/tests/parts_core/test_codebase_memory_mcp_admission.py
  - databasise/tests/seam/test_corpus_status.py
  - databasise/tests/seam/test_delete_document.py
  - databasise/tests/seam/test_ingest_job_status.py
  - databasise/tests/seam/test_mach11_event.py
  - databasise/tests/seam/test_rest_corpus_endpoints.py
  - databasise/tests/seam/test_rest_transport.py
  - databasise/tests/test_embed_startup.py
  - databasise/tests/validator/test_execution_mode.py
  - databasise/tools/check_import_boundary.py
  - databasise/uv.lock
  - databasise/validator/execution_mode.py
  - databasise/wirings/codebase-memory-mcp.json
  - databasise/wirings/lightrag/corpus-delete.json
  - databasise/wirings/lightrag/corpus-ingest.json
  - .gitignore
  - v1/.gitignore
findings:
  critical: 2
  warning: 3
  info: 1
  total: 6
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-09-08T00:00:00Z
**Depth:** standard
**Files Reviewed:** 58
**Status:** issues_found

## Summary

Reviewed the phase 5 opaque-side admission changes: the second (`codebase-memory-mcp`) and third
(`lightrag/full-delete`) admitted opaque parts, the bounded corpus status/health surface, the REST
transport's corpus endpoints, and the new MCP transport (`databasise/mcp/`) with its
CWD-shadow-safe SDK resolver. The scheduler/admission/registry machinery and the `mcp` SDK shadow
guard (`databasise/foreign/_mcp_sdk_guard.py`) are careful and, on inspection, correct.

Two BLOCKER-level correctness bugs were found and confirmed by direct reproduction against the
actual code (not merely by inspection):

1. The MCP transport's own page-cap and payload-decode refusals crash with an unhandled,
   generic tool error instead of the documented, mapped 422-equivalent refusal REST already gets
   right — the exact bug class `databasise/seam/rest.py`'s `_checked_page` was written to prevent,
   reintroduced one file over.
2. `Databasise.ingest()` fabricates a successful `IngestJob` (with `enqueued=0`) when the
   underlying corpus-side subprocess fails with anything other than the two specifically-checked
   exception types — directly contradicting this codebase's own extensively documented
   "never a fabricated zero / refusal over silent narrowing" house style, and reproduced live
   against a missing v1 interpreter.

Both are narrow, mechanical fixes (mirror `_checked_page`'s pattern; widen the `isinstance` check
or catch-all in `engine.py`), but both are real, silent correctness failures that a caller has no
way to detect short of noticing the returned data does not match what actually happened.

## Critical Issues

### CR-01: MCP transport crashes instead of refusing on a page-cap violation and on malformed base64

**File:** `databasise/mcp/server.py:106-113`, `databasise/mcp/tools.py:73-74`, `databasise/mcp/server.py:90-103`

**Issue:** `_status_job`/`_status_corpus` construct `Page(limit=args.limit, offset=args.offset)`
directly inside the tool body, rather than through a `_checked_page`-style pre-check. `Page`'s own
`model_validator` raises `PageSizeExceededError` (a `SeamRefusalError`/`ValueError` subclass) for
`limit > MAX_PAGE_SIZE`, but pydantic v2 wraps any `ValueError` raised inside a `model_validator`
into `pydantic_core.ValidationError` at the construction call site — this is the *exact* failure
mode `databasise/seam/rest.py`'s `_checked_page` (lines 112-130) was written to avoid, and its own
docstring explains the mechanism in detail. `_refusal_mapped` (server.py:90-103) only catches
`SeamRefusalError`, so the wrapped `ValidationError` is never caught — it propagates out of the
tool call as the SDK's generic crash type, not the documented, refusal-shaped `ToolError`.

The identical failure mode also fires from `IngestToolArgs.to_ingest_document()`
(`databasise/mcp/tools.py:74`): `base64.b64decode(self.raw_base64)` raises `binascii.Error` (a
`ValueError` subclass, but not `SeamRefusalError`) for malformed base64, which is likewise
uncaught by `_refusal_mapped`.

Confirmed live against the actual code:

```
$ python -c "... server.call_tool('status', {'args': {'scope': 'corpus', 'limit': 9999}}) ..."
EXC: <class 'mcp.server.mcpserver.exceptions.UnexpectedToolError'> Error executing tool status

$ python -c "... server.call_tool('ingest', {'args': {'raw_base64': 'not-valid-base64!!!', ...}}) ..."
EXC: <class 'mcp.server.mcpserver.exceptions.UnexpectedToolError'> Error executing tool ingest
```

REST's equivalent endpoints (`GET /corpus`, `GET /jobs/{job_id}`) do not have this bug — they
route through `_checked_page` precisely to avoid it. The MCP transport is documented elsewhere in
this same phase as sharing "the identical thin-adapter shape" as REST; this is a real behavioral
divergence between the two transports for the exact same operation, and (per the task's own
framing) a page-cap is a deliberate exfiltration control whose failure mode should degrade to a
clean refusal, not an unhandled crash.

**Fix:** Mirror `rest.py`'s `_checked_page` in the MCP transport — validate `limit` against
`MAX_PAGE_SIZE` and raise `PageSizeExceededError` directly (never via `Page(...)`'s constructor)
before calling `engine.get_job_status`/`engine.corpus_status`. For the base64 case, either validate
`raw_base64` with a pydantic field validator that raises a `SeamRefusalError`-compatible refusal,
or widen `_refusal_mapped`'s except clause to also catch `pydantic.ValidationError`/`ValueError`
raised by this module's own DTOs and re-raise as a mapped `ToolError`:

```python
def _checked_page(limit: int, offset: int) -> Page:
    if limit > MAX_PAGE_SIZE:
        raise PageSizeExceededError(requested=limit, limit=MAX_PAGE_SIZE)
    return Page(limit=limit, offset=offset)

async def _status_job(engine: Databasise, args: StatusToolArgs) -> Any:
    if args.job_id is None:
        raise ToolError("status tool: scope 'job' requires a job_id")
    return await engine.get_job_status(args.job_id, _checked_page(args.limit, args.offset))
```

### CR-02: `Databasise.ingest()` fabricates a successful `IngestJob` when the corpus-side subprocess fails for any reason other than the two checked exception types

**File:** `databasise/seam/engine.py:512-524`

**Issue:**

```python
node_exception = scheduled.get("node_exceptions", {}).get(_INGEST_NODE_ID)
if isinstance(node_exception, (CorpusOpSubprocessError, CorpusOpTimeoutError)):
    raise ForeignEngineRefusalError(operation="ingest", cause=node_exception) from node_exception

result = scheduled["results"].get(_INGEST_NODE_ID) or {}
return IngestJob(
    job_id=str(result.get("track_id") or track_id),
    enqueued=int(result.get("enqueued", 0)),
)
```

`run_corpus_op` (`databasise/foreign/v1_corpus_adapter.py`) can also raise
`MissingV1InterpreterError` (the pinned v1 interpreter does not exist), and the subprocess call can
fail for other reasons entirely (a malformed/non-JSON stdout, an unexpected exception inside the
driver script that still exits non-zero via a code path not modeled here, etc.). None of these is
a `CorpusOpSubprocessError`/`CorpusOpTimeoutError`, so the `isinstance` check above is false, the
method falls through, `results` has no entry for the failed node (only a successful dispatch
populates `results`), and `result` is the empty dict — yet the method still returns a plausible-
looking `IngestJob(job_id=<minted-track_id>, enqueued=0)` as if the operation had succeeded.

Confirmed live by pointing `DEFAULT_V1_INTERPRETER` at a nonexistent path (simulating a genuinely
broken v1 install) and calling `engine.ingest(...)`:

```
RETURNED (no exception): job_id='12417ab38302486c8f3ef28ec106ce1b' enqueued=0
```

No exception was raised at all — the caller receives a job handle for an ingest that never ran.
This directly contradicts the codebase's own repeatedly-stated house style (see
`databasise/seam/refusals.py`'s module docstring, `full_ingest.py`'s own "never a fabricated zero"
comments on the token-accounting path) applied to the exact same operation's job handle instead of
its token count. It is also untested: `test_full_ingest.py` only exercises the timeout path
(`CorpusOpTimeoutError`); no test exercises a `MissingV1InterpreterError` or any other unclassified
node failure.

**Fix:** Invert the check — treat "no result was produced" as the refusal condition, rather than
enumerating known-refusal exception types:

```python
node_exception = scheduled.get("node_exceptions", {}).get(_INGEST_NODE_ID)
if node_exception is not None:
    raise ForeignEngineRefusalError(operation="ingest", cause=node_exception) from node_exception
result = scheduled["results"].get(_INGEST_NODE_ID)
if result is None:
    raise ForeignEngineRefusalError(
        operation="ingest", cause=RuntimeError("ingest node produced no result and no exception")
    )
```

## Warnings

### WR-01: `Databasise.delete_document()` silently downgrades any unclassified node failure to a bare `status="fail"`, losing the real cause

**File:** `databasise/seam/engine.py:578-591`

**Issue:** The same `isinstance(node_exception, (CorpusOpSubprocessError, CorpusOpTimeoutError))`
pattern as CR-02 is used here. Unlike `ingest`, this path does not fabricate a *success* — an empty
`result` degrades to `status=result.get("status") or "fail"` — but a genuine engine failure (e.g.
`MissingV1InterpreterError`) is reported as an undifferentiated `DeletionOutcome(status="fail",
message="")` with no indication of what actually went wrong, rather than the documented
`ForeignEngineRefusalError` a caller could otherwise catch and inspect (`.cause`). Confirmed live:
the same missing-interpreter scenario that fabricates a success for `ingest` produces
`DeletionOutcome(document_id='some-doc-id', status='fail', message='', seam_events=[])` for
`delete_document` — a real failure reported with an empty message and no cause.

**Fix:** Apply the same "no result => refusal" inversion from CR-02's fix here too, so a caller
gets `ForeignEngineRefusalError` (with `.cause`) for any node failure, not only the two
specifically-checked types.

### WR-02: MCP `codebase_memory_mcp_body` forwards an unchecked `tool`/`arguments` pair to the foreign MCP binary

**File:** `databasise/parts_core/codebase_memory_mcp.py:304-316`

**Issue:** `codebase_memory_mcp_body` reads `tool`/`arguments` straight off `ctx.config` with no
validation against `CBM_KNOWN_TOOL_NAMES` (the fifteen-tool admitted surface this same module
defines) before calling `call_tool(tool_name, arguments, ...)`. Today the shipped wiring
(`databasise/wirings/codebase-memory-mcp.json`) declares no `config` at all, so this is not
reachable through any currently-wired path, but nothing in this function itself enforces that only
an admitted tool name can be dispatched — a future wiring or a caller who stamps `config` before
dispatch (the same pattern `Databasise.ingest`/`delete_document` already use to stamp
`documents`/`doc_id` onto their own opaque nodes) could reach an unadmitted tool
(`delete_project`, `manage_adr`, ...) through this same body with no admission-record-level check
stopping it.

**Fix:** Validate `tool_name in CBM_KNOWN_TOOL_NAMES` (or against whatever subset this admission
record actually covers) before calling `call_tool`, raising a named error for anything else —
mirroring `normalise_to_item_kind`'s own `UntypedForeignItemError` refusal for an unmapped tool.

## Info

### IN-01: Dead `try: pass finally:` block in `Databasise.health()`

**File:** `databasise/seam/engine.py:684-688`

**Issue:**

```python
try:
    pass
finally:
    for store in opened_stores.values():
        await store.finalize()
```

The `try` body is empty — this is equivalent to just running the `finally` block's contents
unconditionally, but reads as if something is guarded. Looks like a leftover from refactoring
(likely a construction step that used to live in the `try` body and was moved into the loop above).

**Fix:** Drop the vestigial `try:`/`finally:` wrapper:

```python
for store in opened_stores.values():
    await store.finalize()
```

---

_Reviewed: 2026-09-08T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
