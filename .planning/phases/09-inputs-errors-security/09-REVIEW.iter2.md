---
phase: 09-inputs-errors-security
reviewed: 2026-10-17T00:00:00Z
depth: standard
files_reviewed: 42
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
  - databasise/tests/seam/test_non_finite_numbers.py
  - databasise/tests/seam/test_read_route_fault_breadth.py
  - databasise/tests/seam/test_error_message_scrub.py
  - databasise/tests/seam/test_raw_upload_staging.py
findings:
  critical: 1
  warning: 4
  info: 5
  total: 10
status: issues_found
---

# Phase 9: Code Review Report (iteration 2)

**Reviewed:** 2026-10-17
**Depth:** standard
**Files Reviewed:** 42
**Status:** issues_found

## Summary

`tests/seam` and `tests/mcp` pass (688 passed, 1 skipped, no `-m live`). I re-read the fix commits bdecc6c, f31b69b, 44d4212, b07a614 and f357d24 against the iteration-1 findings and ran probe scripts for the specific checks you listed.

Status of the iteration-1 findings:

- **CR-01 (non-finite floats): resolved for caller input.** `refusal_body` replaces non-finite floats recursively through dicts, lists and tuples, and both float-bearing models refuse by name. A new problem comes from the same change: see WR-01.
- **WR-01 (read-route fault breadth): resolved.** `except SeamRefusalError: raise` comes before `except Exception`. `asyncio.CancelledError`, `KeyboardInterrupt` and `SystemExit` derive from `BaseException`, so they pass through untouched, and no `SeamRefusalError` subclass is swallowed. `OSError` maps to 503 `DriverUnavailable`, and `UnicodeDecodeError` maps to 502.
- **WR-02 (write-path parsing): resolved.** Both constructions are wrapped.
- **WR-03 (`error_message` leak): partly resolved.** The helper is applied once through `DocumentStatusEntry`, so `/corpus`, `/jobs/{id}` and the MCP `status` tool all share it. Several common path forms still leak (WR-02 below), and an equivalent unscrubbed v1 text field remains (WR-03 below).
- **WR-04 (raw upload staging): partly resolved, and the fix introduced a regression.** Overwrite is closed, but the id can now never be reused (CR-01 below).

## Critical Issues

### CR-01: A raw-upload document id is permanently burned: re-upload after delete, after an async parse failure, or after a crash is refused with no way to recover

**File:** `databasise/seam/engine.py:826-851` (staging, `open(staged, "xb")`, and cleanup); `databasise/seam/engine.py:~905-960` (`delete_document`, which never touches the inbox)
**Issue:** The staged file `<store_root>/corpus-inbox/<document_id>.bin` is kept after a successful upload, and nothing in the product ever removes it. I ran this probe against the real `Databasise` with the driver ops monkeypatched:

```
ingest(raw, "doc-1")  -> ok
delete_document("doc-1") -> status "success"; corpus-inbox/doc-1.bin still on disk
ingest(raw, "doc-1")  -> DuplicateDocumentIdError
```

v1's `adelete_by_doc_id` does not remove the input file (no `unlink` in `v1/lightrag/lightrag.py`). The same refusal follows in two other cases:

- v1 accepts the upload (the seam returns an `IngestJob`) and then fails the parse asynchronously (`doc_status` goes to `failed`). The architecture's stated recovery is "the user can retry after fixing the file", but the retry with the same id is now refused.
- The process dies between the write and the cleanup. The orphan file blocks the id.

The refusal is also not scoped to the workspace. The inbox is `store_root/corpus-inbox`, with no workspace or modality component. I confirmed that `Databasise(store_root=X, workspace="w2")` is refused for an id uploaded under `workspace="w1"`. A caller-supplied id cannot be used by two workspaces or two selectors that share a `store_root`.

A JSON ingest of the same id after the delete is accepted, because it has no staged file, so raw and JSON uploads are now inconsistent for the same id. The fixer noted the delete-then-reupload consequence as an owner decision, but it is more than that. Delete-then-reingest is a core corpus lifecycle step and the product surface gives no way to clear the id.

**Fix:** Pick one of these:
1. Stage under a name that is unique per request (for example `<document_id>.<track_id>.bin`), remove the `xb` refusal, and update `generated_on_disk_name` and the tests that assert it. This also removes the cross-workspace collision.
2. Keep the name. Have `delete_document` remove `corpus-inbox/<id>.bin` after v1 reports `success` or `not_found`. Scope the inbox directory by workspace, for example `store_root/<workspace>/corpus-inbox`. Add a regression test for the delete-then-reupload cycle.

## Warnings

### WR-01: A NaN or infinite evidence score minted by a store is reported to the caller as a 422 caller refusal

**File:** `databasise/seam/engine.py:1164` (`mint_evidence_refs`); `databasise/seam/evidence.py:68-73`; `databasise/seam/rest.py:327` (`_pydantic_validation_response`)
**Issue:** The new `EvidenceRef.score` validator raises `NonFiniteNumberError` inside pydantic. When the value comes from a retrieval node (for example a similarity store returning NaN) and not from a caller, `mint_evidence_refs` raises a `pydantic.ValidationError` inside the query path. `_pydantic_validation_response` finds the refusal inside and answers 422 `NonFiniteNumberError: field 'score' must hold finite numbers`. That tells the caller to fix an input they never supplied. This contradicts D-03/D-04: a machine fault must not be reported as a caller refusal. On MCP, `_find_refusal` makes the same mistake. In-process callers of `Databasise.query` get a raw `pydantic.ValidationError`. The fixer noted that "a store NaN now fails validation". It did not classify the result.
**Fix:** In `mint_evidence_refs`, check the score before constructing the model, and raise the machine-fault type instead:
```python
score = item.get("score")
if isinstance(score, float) and not math.isfinite(score):
    raise MalformedEvidenceItemError(namespace=namespace, index=index)  # or a ForeignEngineRefusalError fault
```
Keep the validator for the caller-supplied `/evidence/resolve` path only. Add a test that drives a NaN score through a query.

### WR-02: `scrub_error_message` still leaks real path fragments in common forms, and its docstrings claim more than it does

**File:** `databasise/seam/corpus.py:183-199` (`_ABSOLUTE_PATH_RE`, `scrub_error_message`); `databasise/seam/corpus.py:204-208` (`DocumentStatusEntry` docstring: "no absolute path")
**Issue:** I probed the helper with these inputs. The results are the output of the real function:

| Input | Output | Problem |
|---|---|---|
| `Failed parsing ~/store/a.bin` | unchanged | The `~` is in the lookbehind class, so a home-relative path is never matched. `~chris/...` is the same. |
| `...'/home/chris/my docs/a b.bin' ok` | `'my docs/a b.bin'` | A path with spaces. The match stops at the first space, and the tail (`docs/a b.bin`) leaks. |
| `\\server\share\a.bin` | unchanged | UNC paths are not matched. |
| `./store/corpus-inbox/a.bin`, `../../etc/passwd` | unchanged | Relative paths that reveal the server layout are untouched. |
| `http://host:8000/path/to` | `http:to` | A URL is mangled, not preserved. |

The `~` case matters because v1 and Python tracebacks often print `expanduser` forms. The docstring and the DocumentStatusEntry claim ("no absolute path") overstate a regex heuristic. The fixer's own note says it is a heuristic and not an allow-list, but the model docstring does not say so.
**Fix:** Either replace free text with an allow-listed category plus a server-side log (the iteration-1 recommendation), or extend the heuristic with `~`, UNC and relative forms, handle quoted paths up to the closing quote, and reword the docstring to "best-effort". The honest, lower-effort fix is to drop everything after the first `:` that follows a known failure keyword.

### WR-03: `DeletionOutcome.message` returns v1 failure text unscrubbed on `DELETE /documents/{id}` and the MCP delete tool

**File:** `databasise/seam/engine.py:~950-957` (`DeletionOutcome(... message=str(result.get("message") or ""))`); `databasise/seam/corpus.py:122-139`; v1 source `v1/lightrag/lightrag.py:3944` (`f"Error while deleting document {doc_id}: {e}"`) and `:4009` (`... failed to persist changes: {persistence_error}`)
**Issue:** This is the same disclosure class as iteration-1 WR-03, on a different field. On a failed delete, v1 puts `str(e)` into the message, and that text can name storage paths. The seam returns it as a 200 body with `status="fail"`. The WR-03 fix covers only `DocumentStatusEntry.error_message`, so the claim that phase 9 closed v1 error-text leaks is false for delete.
**Fix:** Apply `scrub_error_message` (or a category mapping) to `message` on `DeletionOutcome`, with the same field-validator pattern. Add a test next to `test_error_message_scrub.py`.

### WR-04: Staged-file cleanup can remove a file v1 is still using, and misses one path

**File:** `databasise/seam/engine.py:831-851`, `engine.py:~856-863`
**Issue:**
- `except BaseException` also fires for `asyncio.CancelledError`, and the node failure path also covers a driver timeout. `run_corpus_op` runs in `asyncio.to_thread`, and a thread cannot be cancelled, so the v1 driver subprocess can still be running and may already have enqueued the document with `file_paths=[<staged>]` in `doc_status`. The cleanup then deletes the file under the running job. v1 will fail the parse later, and the retry with the same id sees a v1 duplicate document id.
- The WR-02 wrapper on the `IngestJob` construction raises a 502 after the cleanup block, so a malformed-output ingest (where v1 did run) leaves the staged file and, with CR-01, burns the id. The cleanup rule is inconsistent between the two failure paths.

The cleanup never removes another request's file: the file is only unlinked when this request created it with `xb`, and a concurrent request with the same id is refused earlier. That part is sound.
**Fix:** Remove the staged file on `CancelledError` and on a driver timeout only if v1 provably has not enqueued it (the read-after-write status op can tell). Otherwise leave it and rely on CR-01's per-request unique name. Apply the same decision on the malformed-output path.

## Info

### IN-01: Every node exception, and now every read-route exception, is reported as "the foreign engine failed"

**File:** `databasise/seam/engine.py:~407-418` (`_corpus_op_or_refuse`), `engine.py:~438-446` (`_node_result_or_refuse`)
**Issue:** `except Exception` in `_corpus_op_or_refuse` converts any non-refusal failure, including a local `TypeError` from a bad payload, into `UnclassifiedEngineFailure` 502. The server log keeps the traceback, so it is a diagnosability issue only. The iteration-1 note on `_node_result_or_refuse` still applies.
**Fix:** Classify by origin where practical, or keep as is and say so in the docstring.

### IN-02: The generated OpenAPI documents the wrong 422 shape and omits the 404 shape

**File:** `databasise/seam/rest.py:~150-159`
**Issue:** Unchanged from iteration 1. `_FAULT_RESPONSES` declares only 502/503. The new `DuplicateDocumentIdError` (422) is not documented on the upload route either.
**Fix:** Add `404`/`422` `RefusalBody` entries.

### IN-03: `UnknownDocumentError` can never be raised and stays in `__all__`; `MalformedSelectorPayloadError` has a stale docstring

**File:** `databasise/seam/refusals.py` (`UnknownDocumentError`, `MalformedSelectorPayloadError`)
**Issue:** Unchanged from iteration 1.
**Fix:** Remove from `__all__` or wire a raise site; update the docstring.

### IN-04: Refusals echo unbounded caller input

**File:** `databasise/seam/refusals.py` (`EmptyQueryObjectError`, `InvalidDocumentIdError`)
**Issue:** Unchanged. `EmptyQueryObjectError` now also echoes through `_finite`, which copies the whole structure again.
**Fix:** Cap echoed values (for example `repr()[:200]`).

### IN-05: The compare envelope-rule text is copied in three places, and a mid-run arm failure leaves earlier arms' traces

**File:** `databasise/seam/rest.py:~341-350`, `databasise/mcp/server.py:~209-220`, `databasise/seam/engine.py:~673-677`
**Issue:** Unchanged from iteration 1.
**Fix:** Use `description=COMPARE_RESPONSE_SHAPE_RULE` in `rest.py`, and add one sentence to the `compare` docstring about persisted earlier-arm traces.

---

_Reviewed: 2026-10-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
