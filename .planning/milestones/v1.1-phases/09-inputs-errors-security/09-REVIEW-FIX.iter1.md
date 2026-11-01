---
phase: 09-inputs-errors-security
fixed_at: 2026-10-17T00:00:00Z
review_path: .planning/phases/09-inputs-errors-security/09-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 9: Code Review Fix Report

**Fixed at:** 2026-10-17
**Source review:** .planning/phases/09-inputs-errors-security/09-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (CR-01, WR-01..WR-04)
- Fixed: 5
- Skipped: 0

Edits were made in the main checkout (`workflow.use_worktrees` is false), so no worktree or recovery sentinel was created. Verification ran in the main checkout: `cd databasise && .venv/bin/pytest -q tests/seam tests/mcp` gave 688 passed, 1 skipped. `tools/check_offline_suite.py` passed both modes: `pytest -q -rs` and `python -m pytest -q -rs` each 1600 passed, 1 skipped, 4 deselected.

## Fixed Issues

### CR-01: A refusal that echoes a non-finite float is a 500 on REST and invalid JSON on MCP

**Files modified:** `databasise/seam/refusals.py`, `databasise/seam/evidence.py`, `databasise/seam/query.py`, `databasise/tests/seam/test_rest_transport.py`, `databasise/tests/seam/test_non_finite_numbers.py` (new)
**Commit:** bdecc6c
**Applied fix:** New refusal `NonFiniteNumberError(field)` (in `__all__`, factory added to `_REFUSAL_FACTORIES`), raised by a field validator on `EvidenceRef.score` and `QueryObject.embedding`. `refusal_body` now replaces any non-finite float in a copied value with `None` (recursive), so no refusal can produce a 500 or non-strict JSON. Status: fixed, requires human verification (logic).
Note: a store that returned a NaN `score` while minting evidence now fails validation instead of passing NaN into the envelope.

### WR-01: The read-route fault wrapper catches a closed list

**Files modified:** `databasise/seam/engine.py`, `databasise/seam/refusals.py`, `databasise/seam/rest.py`, `databasise/tests/seam/test_read_route_fault_breadth.py` (new)
**Commit:** f31b69b
**Applied fix:** `_corpus_op_or_refuse` re-raises `SeamRefusalError` and turns every other exception into `ForeignEngineRefusalError`. `UnicodeDecodeError` maps to 502 `MalformedDriverOutput`; any `OSError` maps to 503 `DriverUnavailable` (added to `_ENGINE_UNAVAILABLE`). The cause is logged once by `_foreign_fault` and never in the body. Unused foreign-exception imports removed from `engine.py`. Status: fixed, requires human verification (logic).

### WR-02: Write-path result parsing is not wrapped

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/seam/test_read_route_fault_breadth.py`
**Commit:** 44d4212
**Applied fix:** `IngestJob` and `DeletionOutcome` construction are wrapped in `except _MALFORMED_RESULT` and raise `ForeignEngineRefusalError(failure_class="MalformedDriverOutput")` (502). Tests drive the real write routes with a malformed `enqueued` and an out-of-Literal delete `status`.

### WR-03: v1 `error_message` text is returned verbatim

**Files modified:** `databasise/seam/corpus.py`, `databasise/tests/seam/test_error_message_scrub.py` (new)
**Commit:** b07a614
**Applied fix:** One helper, `scrub_error_message`, applied by a field validator on `DocumentStatusEntry.error_message`, so REST (`/corpus`, `/jobs/{id}`) and the MCP `status` tool share it. It cuts everything from a traceback marker, keeps the first non-empty line, replaces each absolute POSIX or Windows path with its basename (`<path>` if none), and caps at 200 characters. Status: fixed, requires human verification (a regex heuristic, not an allow-list).

### WR-04: Raw upload staged before the run, never cleaned up, silently overwritten on id reuse

**Files modified:** `databasise/seam/engine.py`, `databasise/seam/refusals.py`, `databasise/tests/seam/test_rest_transport.py`, `databasise/tests/seam/test_raw_upload_staging.py` (new)
**Commit:** f357d24
**Applied fix (minimal approach):** the staged path is computed early (unchanged name and directory, which existing protected tests assert), but the bytes are written only right before `run_wiring`, after `parse_wiring` and `_build_stores`, so a validation, parse or store-build failure leaves no file. The write is an exclusive create (`open(path, "xb")`); an existing file is refused as new `DuplicateDocumentIdError` (422, in `__all__`, factory added). If the run raises or `_node_result_or_refuse` faults, the file this request wrote is removed so a retry can reuse the id. A successful upload's file is kept, because v1 stores its path.
Consequence to confirm with the owner: re-uploading the same `document_id` after a successful raw upload is now refused (the file is never deleted). A unique on-disk name was not used because tests that assert `name == generated_on_disk_name(document_id)` (including the protected `tests/seam/test_rest_corpus_endpoints.py`) fix the naming. Status: fixed, requires human verification (logic).

## Skipped Issues

None. Info findings IN-01..IN-05 are out of scope (`fix_scope: critical_warning`).

---

_Fixed: 2026-10-17_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
