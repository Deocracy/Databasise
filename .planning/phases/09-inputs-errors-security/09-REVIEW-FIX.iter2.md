---
phase: 09-inputs-errors-security
fixed_at: 2026-10-17T00:00:00Z
review_path: .planning/phases/09-inputs-errors-security/09-REVIEW.md
iteration: 2
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 9: Code Review Fix Report

**Fixed at:** 2026-10-17
**Source review:** .planning/phases/09-inputs-errors-security/09-REVIEW.md
**Iteration:** 2

**Iteration 1 summary (see 09-REVIEW-FIX.iter1.md):** five fixes committed (bdecc6c non-finite floats refused by name, f31b69b read-route fault breadth, 44d4212 write-path parse wrapping, b07a614 `error_message` scrub, f357d24 exclusive-create raw-upload staging).

**Summary:**
- Findings in scope: 5 (CR-01, WR-01..WR-04)
- Fixed: 5 (CR-01 and WR-04 through option (c), see below)
- Skipped: 0

Edits were made in the main checkout (`workflow.use_worktrees` is false), so no worktree or recovery sentinel was created. Verification ran in the main checkout; the counts are in the final section.

## Fixed Issues

### CR-01: A raw-upload document id is permanently burned

**Files modified:** `databasise/seam/engine.py`, `databasise/seam/refusals.py`, `databasise/tests/seam/test_raw_upload_staging.py`
**Commits:** 4e9d32f (shared with WR-04), c83e7c8 and be65af3 (workspace ownership)
**Applied fix (option (c) of the review, then (b) below):** The flat layout `corpus-inbox/<generated_on_disk_name(document_id)>` and the exclusive create stay, because the protected `test_rest_corpus_endpoints.py` pins that layout (a per-request subdirectory was tried on paper and rejected for that reason; the protected file passes unchanged). `delete_document` now removes the staged file for its id after the v1 delete has run (subject to the ownership rule below), with `missing_ok`. A removal error is logged once server-side and never fails a delete v1 already performed. So delete followed by re-upload always works, including after a crash orphan or a failed asynchronous parse. `DuplicateDocumentIdError` stays, with its message and docstring reworded: the id has a staged upload in this store; delete the document first to re-upload it. Tests: upload, delete, re-upload accepted; delete of an unknown id removes an orphaned staged file; a failing file removal does not fail the delete. Status: fixed, requires human verification (logic).

**Workspace ownership (option (b), commit c83e7c8):** on a successful exclusive create, ingest writes an owner record naming the uploading workspace at `store_root/corpus-inbox-owners/<generated_on_disk_name(id)>`, a sibling directory, so `corpus-inbox` still holds exactly one entry and the protected test passes unchanged. The staged file is created first (it is the duplicate authority), then the record is written with a plain write (the staged file's exclusive create already serialises the id, and an exclusive `open` added a ruff error). If the record write fails, both files are removed and the error re-raised. `delete_document` removes the staged file and record only when the record names its own workspace, or when there is no record (legacy or orphaned file) and v1's delete returned `success`; otherwise it logs and leaves them. Tests: w1 stages X, w2's delete leaves w1's file and record, w2's upload is refused, w1's delete removes both, then X can be uploaded in w2; an orphan without a record is removed only on v1 `success`; a failed record write removes the staged file.

**Remaining limit:** a staged id is unique per store, not per workspace, so the duplicate refusal still applies across workspaces of one store until the owner deletes it. The `shortcut:` comment was removed; the limit is noted in the `ingest` docstring and `DuplicateDocumentIdError`.

### WR-04: Staged-file cleanup could remove a file v1 is still using

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/seam/test_raw_upload_staging.py`
**Commits:** 4e9d32f, c70b90d (logs the staged path once)
**Applied fix:** The `except BaseException` cleanup and the cleanup on `ForeignEngineRefusalError` are gone. The staged file is removed only when its own write fails (`except Exception` around the write, before the v1 subprocess starts). On timeout, cancellation, a subprocess failure or malformed output the file stays, because v1 may hold its path; a leftover is harmless now that `delete_document` releases it. Every post-run fault path (run raising, node failure, malformed output) logs the staged path once at WARNING (`staged upload left in place after an ingest fault: <path>`) so an operator can reap it; a test covers the timeout case. Tests: a pre-run failure (store build) leaves no file; a timeout and a subprocess failure leave the file; malformed driver output leaves the file. Status: fixed, requires human verification (logic).

### WR-01: A store-minted NaN or infinite evidence score was reported as a 422 caller refusal

**Files modified:** `databasise/seam/evidence.py`, `databasise/seam/engine.py`, `databasise/tests/seam/test_evidence_refs.py`
**Commits:** 5bbb776, 5ae18f1 (follow-up)
**Applied fix:** `mint_evidence_refs` checks the score before building `EvidenceRef` and raises `MalformedEvidenceItemError` (new `reason` argument). `_execute` turns that into `_foreign_fault("query", ..., failure_class="MalformedDriverOutput")`, so the cause is logged once and REST answers 502. The `EvidenceRef.score` validator stays for `/evidence/resolve`. The follow-up widens the check to `isinstance(score, numbers.Real) and not math.isfinite(float(score))`, so numpy float32 and float64 values are caught; numpy was already used by this test module. Tests: NaN, inf, -inf, numpy float32 NaN and numpy float64 inf at unit level, plus a query through a store returning NaN checking the in-process fault and the REST 502. Status: fixed, requires human verification (logic).

### WR-02: `scrub_error_message` leaked common path forms and overclaimed

**Files modified:** `databasise/seam/corpus.py`, `databasise/tests/seam/test_error_message_scrub.py`
**Commit:** 1f00236 (shared with WR-03)
**Applied fix:** The one shared helper now handles `~/` and `~user/`, quoted paths with spaces, UNC paths, `./` and `../` paths, and `file://`, `http://`, `https://` URLs (replaced with `<url>`). Docstrings say best-effort. A parametrized test covers every form. Known remaining limit, stated in the docstring: an unquoted path containing spaces keeps its tail. Status: fixed, requires human verification (a regex heuristic, not an allow-list).

### WR-03: `DeletionOutcome.message` returned v1 failure text unscrubbed

**Files modified:** `databasise/seam/corpus.py`, `databasise/tests/seam/test_error_message_scrub.py`
**Commit:** 1f00236
**Applied fix:** A field validator on `DeletionOutcome.message` calls `scrub_error_message` (an empty result becomes `""`), so REST DELETE and the MCP delete tool, which return this model, share it. Tests: a model-level construction test and a REST DELETE test with a path in the driver message. The MCP delete tool is covered through the shared model, not by its own test.

## Deferred

Orphaned staged files after a timeout or malformed driver output (MEDIUM, acknowledged): only machine faults leave the file, and for a server-minted id the caller cannot reclaim it. This phase only logs the path server-side. A reaper or a reclaim handle is an owner decision.

## Skipped Issues

None. Info findings IN-01..IN-05 are out of scope (`fix_scope: critical_warning`).

## Verification

Run in the main checkout, not a worktree. The protected `tests/seam/test_rest_corpus_endpoints.py` passes unchanged. `tests/seam tests/mcp`: 713 passed, 1 skipped. `tools/check_offline_suite.py`: both modes 1625 passed, 1 skipped, 4 deselected. ruff on `seam mcp`: 22 errors.

---

_Fixed: 2026-10-17_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 2_
