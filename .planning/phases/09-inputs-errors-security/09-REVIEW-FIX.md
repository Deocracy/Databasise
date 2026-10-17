---
phase: 09-inputs-errors-security
fixed_at: 2026-10-17T00:00:00Z
review_path: .planning/phases/09-inputs-errors-security/09-REVIEW.md
iteration: 3
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 9: Code Review Fix Report

**Fixed at:** 2026-10-17
**Source review:** .planning/phases/09-inputs-errors-security/09-REVIEW.md
**Iteration:** 3 (final pass)

**Iteration 1 (09-REVIEW-FIX.iter1.md):** five fixes committed (non-finite floats refused by name, read-route fault breadth, write-path parse wrapping, `error_message` scrub, exclusive-create raw-upload staging).
**Iteration 2 (09-REVIEW-FIX.iter2.md):** five fixes committed (burned id released by `delete_document` with a per-workspace owner record, staged-file cleanup limited to pre-run failures, store NaN/inf scores become a 502, wider path/URL scrub, `DeletionOutcome.message` scrubbed).

**Summary:**
- Findings in scope: 5 (CR-01, WR-01, WR-02, plus IN-01 and IN-02 by orchestrator instruction)
- Fixed: 5
- Skipped: 0

Edits were made in the main checkout (`workflow.use_worktrees` is false): no worktree, no recovery sentinel.

## Fixed Issues

### CR-01: `delete_document` removed the staged upload when v1 answered `not_allowed` or `fail`

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/seam/test_raw_upload_staging.py`
**Commit:** 185e0f1
**Applied fix:** In `_release_staged_upload` both branches now require v1 to have released the document (`success` or `not_found`). The owned-record branch releases on either; the no-record branch still releases on `success` only (a record-less file may be a legacy file from another workspace). On `not_allowed`, `fail` or any other status both files stay and the existing single warning is logged. Docstring updated. Test: a parametrized upload then delete answered `not_allowed` / `fail` asserts the staged file and owner record remain. Status: fixed, requires human verification (logic).

### WR-01: A corrupt, truncated or empty owner record failed the delete

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/seam/test_raw_upload_staging.py`
**Commit:** dccac1e
**Applied fix:** The record read catches `OSError` and `UnicodeDecodeError`; an unreadable record, or one empty after `strip()`, is treated as no record, so it can never raise out of `delete_document`. The record is now written atomically in `ingest` (temp file in the same directory, then `os.replace`; the temp file is removed if either step fails). Tests: `b"\xff\xfe"`, `b""` and blank records are each treated as no record and released on v1 `success`; the owners directory holds only the final record after an upload. Status: fixed, requires human verification (logic).

### WR-02: A crash between the exclusive create and the record write leaves an orphan

**Files modified:** `databasise/seam/engine.py`, `databasise/tests/seam/test_raw_upload_staging.py` (comments only)
**Commit:** 8943a8a
**Choice: option (b), keep the order and accept the window.** The order stays (1) exclusive create, (2) atomic record write, (3) remove the file if (2) fails. Reason: the exclusive create is the only thing that serialises a duplicate id. Writing the record first, even atomically, lets a losing duplicate upload overwrite the live upload's record (a second workspace would then own the first workspace's file), and not overwriting needs a check-then-write that races. A record-first order that is correct would need a lock or a link-based create, which is more code than a window that needs a process kill inside two adjacent statements. Mitigation: the atomic write (WR-01) means the window now leaves "file without record", never a partial record. Consequence: a crash orphan is not released by delete (v1 answers `not_found`, the no-record branch needs `success`) and an operator removes it by hand. The limit is stated in the `ingest` docstring. The existing test that pins "no record releases only on `success`" stays; a comment says why. Status: accepted limit, documented.

### IN-01: `scrub_error_message` mangled non-listed URL schemes

**Files modified:** `databasise/seam/corpus.py`, `databasise/tests/seam/test_error_message_scrub.py`
**Commit:** 21f40ad
**Applied fix:** `_URL_RE` now matches any `scheme://`. A parametrized case covers `s3://bucket/key`. Status: fixed.

### IN-02: A huge int score raised `OverflowError` and surfaced as an unclassified 500

**Files modified:** `databasise/seam/evidence.py`, `databasise/tests/seam/test_evidence_refs.py`
**Commit:** 54dabda
**Applied fix:** In `mint_evidence_refs`, `OverflowError` from `float(score)` marks the score non-finite, so it raises `MalformedEvidenceItemError` (502). String and Decimal scores are left alone as instructed. Test: `10**400` added to the existing non-finite parametrization. Status: fixed.

## Skipped Issues

None. IN-03 through IN-08 are out of scope for this pass.

## Verification

Run in the main checkout, not a worktree. `tests/seam tests/mcp`: 721 passed, 1 skipped. `tools/check_offline_suite.py`: both modes 1633 passed, 1 skipped, 4 deselected. `ruff check seam mcp`: 22 errors (at the baseline). Protected test files were not edited.

---

_Fixed: 2026-10-17_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 3_

## Post-loop verification (orchestrator, after iteration 3)

A targeted verification pass over the iteration-3 commits (185e0f1..54dabda) rated all five fixes RESOLVED and found two regressions. The orchestrator fixed both in 2da7ad9:

- **WR-A:** the owner-record temp name `.{id}.bin.{hex}.tmp` exceeded NAME_MAX for ids of 214 to 251 characters. It is now `.{hex}.tmp`. Test: `test_a_document_id_that_fits_as_a_file_name_also_fits_its_owner_record_temp_file`.
- **WR-B:** `_URL_RE` with an unbounded scheme took quadratic time, about 10 s on a 40 K line. A first fix cut the input to 1 KB, but an automated security review showed that could split a quoted path. Replaced in the follow-up commit: the match now starts only at the head of a scheme-character run (lookbehind), which is linear, with no truncation and no scheme cap. Test: `test_scrub_stays_fast_on_a_long_line_without_a_url`.

These were not fixed:
- The cleanup's `owner.unlink` is unguarded when the owner path is a directory. This is pathological.
- Concurrent delete and ingest races on one id were not checked.
- The v1 `not_found` answer for a queued but not-yet-registered document was not checked.
