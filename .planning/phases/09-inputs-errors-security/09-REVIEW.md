---
phase: 09-inputs-errors-security
reviewed: 2026-10-17T00:00:00Z
depth: standard
files_reviewed: 43
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
  - databasise/tests/seam/test_evidence_refs.py
findings:
  critical: 1
  warning: 2
  info: 8
  total: 11
status: issues_found
---

# Phase 9: Code Review Report (iteration 3)

**Reviewed:** 2026-10-17
**Depth:** standard
**Files Reviewed:** 43
**Status:** issues_found

## Summary

I re-read commits 1f00236 through be65af3 against the iteration-2 findings. I ran the targeted test files (`test_raw_upload_staging`, `test_error_message_scrub`, `test_evidence_refs`, `test_non_finite_numbers`, `test_read_route_fault_breadth`: 70 passed) and probe scripts for each point you listed. The probes ran against the real `Databasise` with the driver op monkeypatched, in a temp store. Nothing was left in the repo.

Status of the iteration-2 findings:

- **CR-01 (burned id): mostly resolved, with a regression.** Delete then re-upload works, including after a failed asynchronous parse. The owner record is written only after the exclusive create wins, and it lives outside `corpus-inbox`. The new release rule removes the file in cases where v1 refused or failed the delete (CR-01 below).
- **WR-01 (store NaN reported as caller refusal): resolved.** `MalformedEvidenceItemError` becomes a `ForeignEngineRefusalError` (502) in `_execute`. NaN, inf, -inf and numpy float32/float64 are caught. Two non-`Real` shapes still reach the old path (IN-02).
- **WR-02 (scrub leaks): resolved for the listed forms.** `~`, `~user`, UNC, `./`, `../`, quoted paths with spaces and `file://`/`http(s)://` are handled. Residue is in IN-01.
- **WR-03 (`DeletionOutcome.message` unscrubbed): resolved.** The field validator covers REST, MCP and in-process callers.
- **WR-04 (cleanup under a running job): resolved for the ingest side.** The file is removed only when the staged write fails, before the run starts. Every post-run fault leaves it and logs the path once. The same hazard exists on the delete side (CR-01).

The specific checks you asked for:

- **Owner-record path from unvalidated input:** no. The path is built only from `generated_on_disk_name(document_id)`, which is a `fullmatch` on `[A-Za-z0-9_-]+`. The check runs in `ingest` (line 764) and `delete_document` (line 954), and again inside `_staged_owner_path`.
- **Path traversal through the workspace value:** no. The workspace string is written as the record's content and compared by equality. It is never joined into a path by this code.
- **Crash window that burns an id:** yes, narrow (WR-02).
- **Delete then re-upload failing:** it works when a record exists or v1 reports `success`. It fails for the orphan cases in WR-02.
- **Removal error failing a delete:** an `OSError` is handled. A `UnicodeDecodeError` from reading the record is not (WR-01).

## Critical Issues

### CR-01: `delete_document` removes the staged upload when v1 answered `not_allowed` or `fail`, so the document stays registered while its input file is gone

**File:** `databasise/seam/engine.py:906-909` (`_release_staged_upload`), called from `engine.py:994`
**Issue:** The condition is `recorded == self.workspace or (recorded is None and v1_status == "success")`. The first clause ignores `v1_status`. v1's `DeletionResult.status` is one of `success`, `not_found`, `not_allowed` and `fail`. `not_allowed` is returned when the v1 pipeline is busy (`v1/lightrag/lightrag.py:3167-3192`), which is exactly when the document may be parsing from the staged path. `fail` is returned when the delete raised.

I confirmed this with a probe: after a raw upload by workspace `w`, a v1 delete answer of `not_allowed` returned status `not_allowed` and the inbox was empty afterwards. The same happened for `fail`. Consequences:

- The document is still registered in v1 (nothing was deleted), and a running parse loses its input file. This is the hazard iteration-2 WR-04 was filed to prevent, re-introduced on the delete path.
- The caller is told the delete did not happen, but the staged bytes are gone. A retry of the delete finds no file. A re-upload of the id is accepted by the seam and is then refused by v1 as a duplicate id, with a staged file left behind.
- The method docstring ("after v1 has answered ... removed if the owner record names this workspace") reads as if status does not matter. The no-record branch already gates on `success`, so the two branches are inconsistent.

**Fix:** Gate both branches on v1 having actually released the document. A `not_found` answer is also safe, because v1 holds no document that could be reading the file:
```python
released = v1_status in ("success", "not_found")
if released and (recorded == self.workspace or (recorded is None and v1_status == "success")):
    staged.unlink(missing_ok=True)
    owner.unlink(missing_ok=True)
```
Add a test: upload, delete answered `not_allowed` and `fail`, assert the staged file and the owner record both remain.

## Warnings

### WR-01: A corrupt, truncated or empty owner record fails the delete after v1 already deleted the document, or makes the id permanently undeletable

**File:** `databasise/seam/engine.py:906` (`owner.read_text(encoding="utf-8")`), `engine.py:917` (`except OSError`)
**Issue:** Two failures come from the same read.

1. `read_text` raises `UnicodeDecodeError` (a `ValueError`, not an `OSError`) for non-UTF-8 content. The `except OSError` does not catch it. I confirmed with a probe that a record holding `b"\xff\xfe"` makes `delete_document` raise `UnicodeDecodeError` after v1 returned `success`. This contradicts the documented rule that a removal error never fails a delete v1 already performed. A crash during `owner.write_bytes` (which truncates first) can leave exactly this kind of file, as can a truncated multi-byte workspace name.
2. An empty record (crash between truncation and write) decodes to `""`. It is not `None`, and it equals no workspace, so every workspace's delete logs "left in place" and the staged file can never be removed. The id is permanently refused as `DuplicateDocumentIdError`.

**Fix:** Treat an unreadable or empty record the same as a missing one:
```python
try:
    recorded = owner.read_text(encoding="utf-8") if owner.exists() else None
except (OSError, UnicodeDecodeError):
    recorded = None
recorded = recorded or None
...
except (OSError, UnicodeError):
    logger.exception(...)
```
Better still, write the record atomically (write a temp file in the same directory, then `os.replace`) so a crash never leaves a partial record.

### WR-02: A crash between the exclusive create and the owner-record write leaves an orphan that no delete can ever release

**File:** `databasise/seam/engine.py:821-828` (create, then record write); `engine.py:907` (no-record branch requires `success`)
**Issue:** If the process dies after `open(staged, "xb")` and before `owner.write_bytes(...)`, the staged file has no record. The v1 run never started, so v1 knows no such document. `delete_document` for that id returns v1 `not_found`, and the no-record branch removes the file only on `success`, so the file stays. Every re-upload of the id is refused. The test `test_an_orphan_without_an_owner_record_is_removed_only_when_v1_deleted_successfully` pins this behaviour (lines 62-76), but the case it describes (an orphan left by a crashed upload) is the one that can never reach `success`. Only a legacy file that v1 does hold can.

This is the same crash class that iteration-2 CR-01 was filed to close. The window is small, so I rate it a warning, not a blocker. The id is burned with no product-surface way to recover.

**Fix:** Pick one:
- Write the record first, to a temp name in `corpus-inbox-owners`, create the staged file with `xb`, then `os.replace` the temp record into place. A leftover temp file can then be ignored or reaped, and no staged file ever exists without a record.
- Or accept `not_found` in the no-record branch as well. The cost is that a legacy file staged by another workspace could be removed by a workspace whose v1 does not hold the id, which the record rule exists to prevent. Because pre-record files are a legacy case only, state the trade-off in the docstring if this is chosen.

## Info

### IN-01: `scrub_error_message` mangles and leaks non-listed URL schemes, and an unquoted path with spaces keeps its tail

**File:** `databasise/seam/corpus.py:183-221` (`_URL_RE`, `_PATH_RE`)
**Issue:** `_URL_RE` knows only `file`, `http` and `https`. I probed `s3://bucket/key and ftp://host/x`, which becomes `s3:key and ftp:x`: the bucket path tail leaks and the scheme is mangled. `file /srv/my data/a.bin missing` becomes `file my data/a.bin missing`, which the docstring already admits. This is the accepted best-effort limit and not a defect on its own. It is listed because the scheme list is an easy extension.
**Fix:** Widen to any scheme: `\b[a-z][a-z0-9+.-]*://[^\s'"`<>()\[\],;]*`.

### IN-02: Non-`Real` and huge-int scores from a store still take the wrong failure path

**File:** `databasise/seam/evidence.py:115-116`
**Issue:** The finite check is `isinstance(score, numbers.Real) and not math.isfinite(float(score))`. I probed these:

- A string `"nan"` and `Decimal("NaN")` are not `Real`. They reach `EvidenceRef`, whose validator raises `NonFiniteNumberError`, so the 422 caller refusal returns for a store fault.
- An integer such as `10**400` is `Real`, and `float(score)` raises `OverflowError` before any check. The error is not a `MalformedEvidenceItemError`, so it surfaces as an unclassified 500.
- `True` passes as `1.0`.

All three are unlikely store outputs, so this is not a regression of the iteration-2 fix.
**Fix:** In `mint_evidence_refs`, wrap the check in `try: math.isfinite(float(score)) except (TypeError, ValueError, OverflowError)` and raise `MalformedEvidenceItemError` for any score that is not a finite real number.

### IN-03: `DuplicateDocumentIdError` is a 422 caller refusal, and the OpenAPI document does not declare it

**File:** `databasise/seam/rest.py` (`_FAULT_RESPONSES`, upload route); `databasise/seam/refusals.py:240-254`
**Issue:** Carried over from iteration-2 IN-02 and extended: the generated OpenAPI documents only 502/503 and does not list the 404 or 422 refusal shapes, including the new duplicate-id refusal. A 409 would also describe a state conflict more accurately than 422.
**Fix:** Add `404`/`422` `RefusalBody` entries to the declared responses.

### IN-04: Every node exception, and every read-route exception, is reported as "the foreign engine failed"

**File:** `databasise/seam/engine.py` (`_corpus_op_or_refuse`, `_node_result_or_refuse`)
**Issue:** Carried over from iteration-2 IN-01. A local `TypeError` becomes `UnclassifiedEngineFailure` 502. The server log keeps the traceback.
**Fix:** Classify by origin where practical, or say so in the docstrings.

### IN-05: `UnknownDocumentError` can never be raised and stays in `__all__`; `MalformedSelectorPayloadError` has a stale docstring

**File:** `databasise/seam/refusals.py`
**Issue:** Carried over from iteration-2 IN-03.
**Fix:** Remove from `__all__` or wire a raise site; update the docstring.

### IN-06: Refusals echo unbounded caller input

**File:** `databasise/seam/refusals.py` (`EmptyQueryObjectError`, `InvalidDocumentIdError`, `DuplicateDocumentIdError`)
**Issue:** Carried over from iteration-2 IN-04. `DuplicateDocumentIdError` also echoes the caller's id, which is bounded only by the token regex and not by length.
**Fix:** Cap echoed values (for example `repr()[:200]`).

### IN-07: The compare envelope-rule text is copied in three places, and a mid-run arm failure leaves earlier arms' traces

**File:** `databasise/seam/rest.py`, `databasise/mcp/server.py`, `databasise/seam/engine.py`
**Issue:** Carried over from iteration-2 IN-05.
**Fix:** Use `description=COMPARE_RESPONSE_SHAPE_RULE` in `rest.py`, and add one sentence to the `compare` docstring about persisted earlier-arm traces.

### IN-08: Accepted design limits, listed for the record

**File:** `databasise/seam/engine.py:755-757`, `engine.py:862-865`; `databasise/seam/corpus.py:189-221`
**Issue:** Not defects, per your instruction:

- A staged id is unique per store, not per workspace. Another workspace's upload of the same id is refused until the owner deletes it.
- Files orphaned by post-run faults stay on disk. There is no reaper, and the path is logged once at WARNING.
- The error-message scrub is a best-effort heuristic.

**Fix:** None required this phase.

---

_Reviewed: 2026-10-17_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
