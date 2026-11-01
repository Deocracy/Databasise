---
phase: 09-inputs-errors-security
reviewed: 2026-10-17T00:00:00Z
depth: standard
files_reviewed: 38
files_reviewed_list:
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
  - databasise/seam/trace_store.py
  - databasise/tests/mcp/test_mcp_refusal_mapping.py
  - databasise/tests/mcp/test_tool_growth_invariant.py
  - databasise/tests/seam/_probes.py
  - databasise/tests/seam/test_compare_keys.py
  - databasise/tests/seam/test_corpus_adapter_failures.py
  - databasise/tests/seam/test_corpus_status.py
  - databasise/tests/seam/test_delete_document.py
  - databasise/tests/seam/test_empty_capability_selector.py
  - databasise/tests/seam/test_empty_inputs.py
  - databasise/tests/seam/test_evidence_namespace_guard.py
  - databasise/tests/seam/test_foreign_engine_refusal.py
  - databasise/tests/seam/test_hipporag_write_path.py
  - databasise/tests/seam/test_ingest_file_name.py
  - databasise/tests/seam/test_ingest_input_refusals.py
  - databasise/tests/seam/test_mutable_store_exclusion.py
  - databasise/tests/seam/test_page_bounds.py
  - databasise/tests/seam/test_promote_alias_validation.py
  - databasise/tests/seam/test_refusal_body_shape.py
  - databasise/tests/seam/test_refusal_catalogue.py
  - databasise/tests/seam/test_refusal_status_codes.py
  - databasise/tests/seam/test_rest_corpus_endpoints.py
  - databasise/tests/seam/test_rest_transport.py
  - databasise/tests/seam/test_seam_doc_consistency.py
  - databasise/tests/seam/test_upload_selector_field.py
findings:
  critical: 1
  warning: 4
  info: 5
  total: 10
status: issues_found
---

# Phase 9: Code Review Report

**Reviewed:** 2026-10-17
**Depth:** standard
**Files Reviewed:** 38
**Status:** issues_found

## Summary

`tests/seam` and `tests/mcp` pass (648 passed, 1 skipped, no `-m live`). The core D-01..D-13 work is sound. I checked these and found no defect:

- The one refusal body with no `detail` wrapper, and the unwrap of validator-wrapped refusals on both transports.
- 404 vs 422 vs 502/503 mapping through `_status_for`.
- Leading-underscore attributes (`_cause`, `_internal_node_id`) stay out of bodies, and the fault message names only the operation and failure class.
- Input is validated before any disk or store side effect on ingest, delete and evidence resolve (document id, evidence namespace, raw-upload gate, page bounds).
- The compare key and mutable-store pre-check runs before any arm executes, selectors are resolved once, and `all_wirings()` returns fresh dicts, so `_execute_resolved` mutating its input is safe.
- The MCP `call_tool` override matches the installed SDK signature, and `UnexpectedToolError` subclasses `ToolError`.

The defects are in the gaps around those paths. A refusal body that carries a non-finite float turns into an unhandled 500 on REST and invalid JSON on MCP. The read routes and write routes catch driver failures with different breadth, so some driver failures still escape as bare 500s. v1's own `error_message` text is passed through unredacted.

## Critical Issues

### CR-01: A refusal that echoes a non-finite float is a 500 on REST and invalid JSON on MCP

**File:** `databasise/seam/refusals.py:33-46` (`refusal_body`); `databasise/seam/rest.py:262` (`JSONResponse`); `databasise/mcp/server.py:126` (`json.dumps`)
**Issue:** `refusal_body` copies caller-supplied models and values into the body unchanged. Two refusals echo float-bearing input:
- `UnresolvableEvidenceReferenceError.ref` carries `EvidenceRef.score: float | None`.
- `EmptyQueryObjectError.query_object` carries `QueryObject.embedding: list[float]`.

FastAPI parses the JSON literal `NaN`, and pydantic accepts it as a float. Starlette's `JSONResponse` renders with `allow_nan=False`, so building the refusal response raises `ValueError`. This is verified live:

```
POST /evidence/resolve {"ref":"x","namespace":"chunks","kind":"text_chunk","score":NaN}   -> 500 Internal Server Error
POST /query {"query":{"text":"  ","embedding":[NaN]}}                                      -> 500 Internal Server Error
```

On MCP the same input does not fail. `json.dumps` default `allow_nan=True` emits `"score": NaN` inside the `isError` text, which a strict JSON client cannot parse. This breaks the phase invariant (SEAM-02/03) that every caller-facing failure is a named refusal in one JSON shape. A single unauthenticated request triggers it, and the 500 hides the real refusal.

**Fix:** Refuse non-finite floats at the model boundary and make the body builder safe:
```python
# evidence.py
score: float | None = Field(default=None, allow_inf_nan=False)
# query.py
embedding: list[Annotated[float, Field(allow_inf_nan=False)]] | None = None
```
Also sanitise in `refusal_body` so no future refusal reintroduces this. Dump models with `mode="json"` and `ser_json_inf_nan="null"` (or recursively replace non-finite floats with `None`). Add a regression test for both routes and the MCP tool.

## Warnings

### WR-01: The read-route fault wrapper catches a closed list, so driver failures still escape as bare 500s

**File:** `databasise/seam/engine.py:407-415` (`_corpus_op_or_refuse`)
**Issue:** D-04 and SEAM-06 say `ForeignEngineRefusalError` is the one fault type on `GET /corpus`, `/corpus/counts` and `/jobs/{id}`. The wrapper catches only `MissingV1InterpreterError`, `CorpusOpSubprocessError`, `CorpusOpTimeoutError` and `json.JSONDecodeError`. `run_corpus_op` (`foreign/v1_corpus_adapter.py:101-149`) can also raise:
- `UnicodeDecodeError` from `subprocess.run(text=True)` when the driver writes non-UTF-8 bytes. This is malformed driver output.
- `OSError` subclasses: `PermissionError` on an interpreter that exists but is not executable, or `FileNotFoundError` if `v1/` is missing as the cwd.

Verified live: monkeypatching `run_corpus_op` to raise either gives `GET /corpus` -> 500 `Internal Server Error`. The 500 body leaks nothing, but it is the wrong class and status, and the caller cannot tell a fault from a bug. The inline comment ("any other exception is not an adapter failure mode") is wrong for these.

**Fix:**
```python
except (MissingV1InterpreterError, CorpusOpSubprocessError, CorpusOpTimeoutError,
        json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
    raise _foreign_fault(operation, exc) from exc
```
Add `UnicodeDecodeError` and `OSError` to `_FOREIGN_FAILURE_CLASSES`. Map `UnicodeDecodeError` to `MalformedDriverOutput`, and `OSError` to 503 (v1 unavailable) in `_ENGINE_UNAVAILABLE`.

### WR-02: Write-path result parsing is not wrapped, so malformed driver output on ingest or delete is a 500

**File:** `databasise/seam/engine.py:830-833` (`ingest`), `engine.py:907-912` (`delete_document`)
**Issue:** The read methods wrap result parsing in `except _MALFORMED_RESULT` and raise `MalformedDriverOutput`. The write methods do not:
- `ingest` runs `int(enqueued)`, which raises `ValueError` for a non-numeric `enqueued`.
- `delete_document` builds `DeletionOutcome(status=result.get("status") or "fail", ...)`. `status` is a `Literal`, so an unexpected v1 status string raises `pydantic.ValidationError`.

`_pydantic_validation_response` re-raises a `ValidationError` that carries no refusal, so both end as a bare 500. This was not run end to end; the re-raise behaviour is confirmed by `test_a_route_validation_error_with_no_refusal_inside_stays_a_server_error`. The result is inconsistent with D-04: the same malformed output is a 502 on three routes and a 500 on two.

**Fix:** Wrap the final model construction in both methods:
```python
try:
    return IngestJob(job_id=str(result.get("track_id") or track_id), enqueued=int(enqueued))
except _MALFORMED_RESULT as exc:
    raise _foreign_fault("ingest", exc, failure_class="MalformedDriverOutput") from exc
```
Do the same around `DeletionOutcome(...)` with `"delete"`.

### WR-03: v1 `error_message` text is returned verbatim on the status routes

**File:** `databasise/seam/corpus.py:183-193` (`DocumentStatusEntry.error_message`); `databasise/foreign/v1_corpus_driver_script.py:312`
**Issue:** `GET /corpus` and `GET /jobs/{id}` (and the MCP `status` tool) return `doc_status.error_msg` from v1 unmodified. It is v1's free-text failure message for a failed document. Raw uploads are handed to v1 as an absolute path (`engine.py:776`, `file_paths=[str(on_disk_path)]`), and failure messages typically name the file and the exception text. Verified live that the text is passed through with no filtering: a driver value `"Failed parsing /home/chris/store/corpus-inbox/a.bin"` reaches the 200 body unchanged. Phase 9 closed server-path leaks on refusal and fault bodies (D-04) but not on this success body. It is a server-internals disclosure on an unauthenticated read route.

**Fix:** Either do both of these, or document the field as raw v1 text and make the exposure an explicit owner decision:
- Replace `error_message` with a bounded, allow-listed category such as `"parse_failed"`, and log the raw text server-side as `_foreign_fault` does.
- If the text must stay, strip absolute paths and cap the length before it crosses the seam.

### WR-04: A raw upload is written to the inbox before the run, never cleaned up, and silently overwritten on id reuse

**File:** `databasise/seam/engine.py:770-777`
**Issue:** `ingest` writes `corpus-inbox/<document_id>.bin` before `parse_wiring`, `_build_stores` and the scheduler run. Nothing removes the file, whether the run succeeds, hits `parse_wiring` errors, or ends in a 502/503 fault, so failed attempts leave orphan files. Since D-12/SEAM-07 a caller can supply the id. A second upload with the same `document_id` does `write_bytes` over the file of an earlier ingest that v1 may still be parsing (`docs_format=pending_parse` is read asynchronously). The earlier job then silently parses the newer bytes. Input validation is correct (the write happens after the token check), but the side-effect ordering and lifetime are not.

**Fix:** Write only after `parse_wiring` and `_build_stores` succeed. Refuse a pre-existing path with `open(path, "xb")` (a named refusal such as `DuplicateDocumentIdError`) or mint a unique on-disk name distinct from the document id. Remove the file in a `finally` once the run is refused. If v1 consumes it asynchronously, document who owns cleanup.

## Info

### IN-01: Every node exception is reported as "the foreign engine failed"

**File:** `databasise/seam/engine.py:438-446` (`_node_result_or_refuse`)
**Issue:** Any `node_exceptions` entry becomes `ForeignEngineRefusalError` (message "the foreign engine failed operation ..."), including machine-side failures such as `VectorStoreCorruptedError`, a `KeyError` in a HippoRAG node (not a foreign engine), or a programming error. Callers see 502 `UnclassifiedEngineFailure` and may retry what is a local bug. The server log keeps the real traceback, so this is a diagnosability issue, not a leak.
**Fix:** Classify by origin: foreign-adapter exceptions become the fault, and other exceptions propagate as a 500 (or get their own machine-fault class).

### IN-02: The generated OpenAPI documents the wrong 422 shape and omits the 404 shape

**File:** `databasise/seam/rest.py:150-159`, route decorators
**Issue:** `responses=_FAULT_RESPONSES` declares only 502/503 on the five corpus routes. FastAPI adds its own 422 `HTTPValidationError` (`{detail: [...]}`) to every route with a body or params, but refusals are the top-level `RefusalBody` (D-01). The 404 refusal shape (`UnknownJobError`, trace, evidence, generation) is not declared at all. An OpenAPI-generated client will mis-model the main error body.
**Fix:** Add `422: {"model": RefusalBody}` and `404: {"model": RefusalBody}` to the relevant routes (or app-wide), and say in the description that bare `{detail}` appears only for schema errors.

### IN-03: A catalogued refusal can never be raised, and some docstrings are stale

**File:** `databasise/seam/refusals.py:214-223` (`UnknownDocumentError`), `refusals.py:364-378` (`MalformedSelectorPayloadError`), `refusals.py:14-19`
**Issue:**
- `UnknownDocumentError` is in `__all__`, which the module docstring defines as "every refusal type either transport can return", but its own docstring says nothing raises it. A consumer matching on the catalogue will wait for a refusal that never arrives.
- `MalformedSelectorPayloadError`'s docstring says an escaping `ValidationError` "produces an unhandled 500", which is no longer true now that `_pydantic_validation_response` exists.

**Fix:** Remove `UnknownDocumentError` from `__all__`, or wire a real raise-site. Update the stale docstring.

### IN-04: Refusals echo unbounded caller input, twice

**File:** `databasise/seam/refusals.py:65-69` (`EmptyQueryObjectError`), `198-211` (`InvalidDocumentIdError`)
**Issue:** `EmptyQueryObjectError` puts `{query_object!r}` in the message and the model in the body. A multi-megabyte whitespace `text` or a large `embedding` comes back in the response about twice. `InvalidDocumentIdError` echoes an arbitrarily long id the same way. `OversizedDocumentError` deliberately avoids echoing; these do not. This is not an information disclosure (it is the caller's own input), but it amplifies response size.
**Fix:** Cap echoed values (for example `repr()[:200]`) in the message and attribute. At minimum, drop `query_object` from the message.

### IN-05: The compare envelope-rule text is copied in three places, and a mid-run arm failure leaves earlier arms' traces

**File:** `databasise/seam/rest.py:341-350`, `databasise/mcp/server.py:209-220`, `databasise/seam/engine.py:673-677`, `databasise/seam/compare.py:48-54`
**Issue:**
- `COMPARE_RESPONSE_SHAPE_RULE` exists as a constant, but the REST description is retyped as a literal string and the other two places are docstrings. A test keeps them equal, but the REST literal could simply be `description=COMPARE_RESPONSE_SHAPE_RULE`.
- `Databasise.compare` says a collision refuses "before any arm runs", but only selector-derived refusals are pre-checked. If arm 2 fails at execution (for example `UnbudgetableParticipantError` or a node fault), arm 1 has already spent tokens and persisted a trace in `trace.db`. The `compare_arms` docstring claims "the whole comparison refuses", which is true for the response but not for side effects.

**Fix:** Import the constant in `rest.py`. Add one sentence to the compare docstring that execution-time failures can leave earlier arms' traces persisted.

---

_Reviewed: 2026-10-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
