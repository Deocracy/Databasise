---
phase: 06-hipporag-2-side-by-side
reviewed: 2026-09-11T00:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - databasise/eval/aa_run.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/tests/eval/test_aa_run.py
  - databasise/tests/evidence/test_falsifier5_record.py
  - databasise/tests/seam/test_rest_transport.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 06: Code Review Report (Incremental — fix-round re-review)

**Reviewed:** 2026-09-11
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

This review **supersedes** the prior `06-REVIEW.md` recorded at commit `183139a`. That review
found 2 Critical and 2 Warning issues; commits `e8612d8` (CR-01), `554e071` (CR-02), `8846730`
(WR-01), and `7540450` (WR-02) were applied afterward, and this round re-reviews exactly the six
files those commits touched, per `git diff 183139a..HEAD`.

**All four prior findings are confirmed resolved, verified live, not just read:**

- **CR-01** (`floor_value_pattern`'s `<=`-exclusion let a fabricated floor value through) —
  resolved. Reproduced the new negative-lookahead regex directly against Python's `re` module: it
  now catches `"floor <= 0.31"` (bare, no second `floor`/`p95` term) while still passing the real
  two-sided pre-registered formula in `FALSIFIER-5-EVIDENCE.md` (`"floor <= 0.5 x ... p95
  floor"`), and the full 246-line document still passes the test.
- **CR-02** (`POST /documents/upload` 500s on a malformed `selector` field) — resolved. The route
  now catches `pydantic.ValidationError` from `Selector.model_validate_json` and re-raises
  `MalformedSelectorPayloadError`, mapped by the existing app-level handler to a 422. Verified via
  `test_upload_with_malformed_selector_field_returns_422_not_a_raw_500` against a real
  `TestClient`.
- **WR-01** (`score_gold_passage` bare `ZeroDivisionError` on empty `gold_document_ids`) —
  resolved. The empty-list check now runs before the evidence walk, raising a named `ValueError`
  and never touching the vector store, matching the new `raise_if_called=True` test.
- **WR-02** (`main()`'s `--spend` path didn't catch `run_one_pass`'s confounded-run `RuntimeError`
  or a `SeamRefusalError` from `engine.query()`) — resolved: both are now in the `except` tuple in
  `aa_run.main()`.

Ran the full scoped test suite against the real `databasise/.venv`: `tests/eval/test_aa_run.py`
(25 passed), `tests/evidence/test_falsifier5_record.py` (part of the same 25), and
`tests/seam/test_rest_transport.py` (34 passed) — all green, no regressions.

Two new lower-severity issues surfaced in this pass, both in the WR-02 fix; see below. No Critical
issues found in this round.

## Warnings

### WR-01 (this round): WR-02's fix has zero test coverage

**File:** `databasise/eval/aa_run.py:560-568`
**Issue:** The `--spend` path's `except` tuple now includes `RuntimeError` and `SeamRefusalError`
specifically to catch `run_one_pass`'s confounded-pass refusal and any refusal the real
`engine.query()` call raises (the WR-02 gap-closure). No test in `test_aa_run.py` exercises the
`--spend` branch of `main()` at all — the only `--spend`-related tests
(`test_main_default_path_constructs_no_client_and_prints_a_real_projection`) explicitly assert
`Databasise`/`_build_clients`/`_load_env_file` are *not* called, which is the estimate-only path,
not the spend path this fix touches. The fix is plausible by inspection but unverified by any
test — the project's own review discipline (mirrored in `test_rest_transport.py`'s "a missing
dict key fails loudly" pattern) treats an unverified fix as incomplete.
**Fix:** Add a test that monkeypatches `aa_run.Databasise`, `aa_run._build_clients`, and
`aa_run._load_env_file` to stub doubles, drives `main(["--split", "dev", "--spend"])` with a
`calibrate_family`/`run_one_pass` stub that raises a confounded-pass `RuntimeError` (or a
`SeamRefusalError` subclass), and asserts `main()` returns `1` with the message on stderr rather
than letting the exception propagate as an unhandled traceback.

### WR-02 (this round): bare `RuntimeError` in the `--spend` except tuple is broader than the fix needs, and makes two other tuple members dead

**File:** `databasise/eval/aa_run.py:560-568`
**Issue:** `UnusableFloorError` and `UnparseableJudgeVerdictError` are both already declared as
`RuntimeError` subclasses (`calibration.py:83`, `aa_run.py:111`), so adding a bare `RuntimeError`
to the same `except` tuple makes both of those entries redundant — dead listing, not a functional
bug, but worth cleaning up since a future reader may assume they're doing independent work.
More substantively: the confounded-pass refusal `run_one_pass` raises is itself a bare
`RuntimeError` with no dedicated class (`aa_run.py:347-351`), inconsistent with this codebase's
own documented house style (`databasise/seam/refusals.py`'s module docstring: "every refusal
names exactly what was wrong in its constructor and message ... rather than letting a bare
`ValueError`/`KeyError` propagate"). Because that raise site uses an unnamed exception, the only
way to catch it specifically at the `main()` boundary is to catch `RuntimeError` broadly — which
also silently swallows `calibration.py`'s `StaleNullError` (another `RuntimeError` subclass,
explicitly *not* supposed to be caught by `calibrate_family` per that function's own docstring)
and any unrelated `RuntimeError` raised by a bug deeper in the call chain (e.g. inside
`TraceStore`, `asyncio.run`, or a client library), converting what should be a loud traceback into
a quiet "refusal" printed to stderr with exit code 1.
**Fix:** Give the confounded-pass refusal in `run_one_pass` a named exception class (e.g.
`ConfoundedPassError(RuntimeError)`, following the same attribute-naming convention as
`refusals.py`), catch that specific class in `main()` instead of bare `RuntimeError`, and drop the
now-redundant `UnusableFloorError`/`UnparseableJudgeVerdictError` entries from the tuple (or keep
them for readability but note the redundancy) — this restores the "only refusals this module
means to print-and-exit on" contract without also masking `StaleNullError` or an unrelated bug's
`RuntimeError`.

## Info

### IN-01: `MalformedSelectorPayloadError`'s constructor message doesn't follow the class-name-substring convention, but two nearly-identical sibling refusals in the same file do — worth a one-line note for future readers

**File:** `databasise/seam/refusals.py:231-245`
**Issue:** Not a defect — `MalformedSelectorPayloadError` is raised directly rather than inside a
pydantic validator, so it correctly does not need the "class name embedded in the message"
convention that `AmbiguousIngestPayloadError`/`PageSizeExceededError` document and rely on (their
own docstrings explain why). The class's own docstring does explain this correctly. Flagging only
because a reader skimming the file for the "always embed the class name" rule without reading each
docstring in full could mistake the omission for an inconsistency; a one-clause cross-reference
next to `MalformedBase64PayloadError` (the other "raised directly" sibling) would save that
re-derivation.
**Fix:** Optional — no code change needed; at most a doc nit.

---

_Reviewed: 2026-09-11T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
