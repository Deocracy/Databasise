---
phase: 06-hipporag-2-side-by-side
fixed_at: 2026-09-11T00:00:00Z
review_path: .planning/phases/06-hipporag-2-side-by-side/06-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 06: Code Review Fix Report

**Fixed at:** 2026-09-11
**Source review:** `.planning/phases/06-hipporag-2-side-by-side/06-REVIEW.md` (review commit `183139a`, gap-closure round)
**Iteration:** 1

**Summary:**
- Findings in scope (critical_warning): 4 (CR-01, CR-02, WR-01, WR-02)
- Fixed: 4
- Skipped: 0
- Out of scope (not attempted, per fix_scope): 2 (IN-01, IN-02)

Each finding was re-verified against the current source before any edit — no line numbers had
drifted meaningfully from the review, and every defect described was still present exactly as
reported.

## Fixed Issues

### CR-01: `floor_value_pattern`'s `<=`-exclusion lets a fabricated floor value through undetected

**File:** `databasise/tests/evidence/test_falsifier5_record.py`
**Commit:** `e8612d8`
**Applied fix:** Confirmed the hole live before fixing: the old pattern excluded every `=`
preceded by `<`, so `floor <= 0.31` and `p95 <= 0.42` matched nothing. Narrowed the exclusion to
require the excluded number be part of the actual two-sided pre-registered formula shape — a
second `floor`/`p95` token appearing later on the same line after an `x`/`*`/`×` multiplier — via
a negative lookahead: `(?![^\n]{0,80}(?:x|\*|×)[^\n]{0,80}(?:floor|p95))`. Verified live with a
standalone Python check before touching the test suite:
  - `'floor = 0.31'` → MATCH (caught)
  - `'floor: 0.31'` → MATCH (caught)
  - `'floor <= 0.31'` → MATCH (now caught — was the hole)
  - `'p95 <= 0.42'` → MATCH (now caught — was the hole)
  - The real two-sided formula line from `FALSIFIER-5-EVIDENCE.md` (`` `gold_passage`'s (`T1`)
    calibrated p95 floor <= 0.5 x `answer_level`'s (`T0`) calibrated p95\nfloor** ``) → no match
    (still correctly exempted, formula spans the `x`/second-`floor` shape across the line wrap)
`databasise/tests/evidence/test_falsifier5_record.py` (11 tests) passes with the narrowed
pattern.

### CR-02: `POST /documents/upload` returns an unhandled 500, not the documented 422, on a malformed `selector` field

**Files modified:** `databasise/seam/refusals.py`, `databasise/seam/rest.py`, `databasise/tests/seam/test_rest_transport.py`
**Commit:** `554e071`
**Applied fix:** Reproduced the 500 live before fixing (`TestClient` post with
`data={"selector": "{not valid json"}` → 500, `"Internal Server Error"`). Added
`MalformedSelectorPayloadError(SeamRefusalError)` to `refusals.py`, mirroring
`MalformedBase64PayloadError`'s documented house pattern for a manually-parsed (non-pydantic-
validator) field, and added it to `__all__`. Wrapped the manual
`Selector.model_validate_json(selector)` call in `rest.py`'s upload route in a
`try/except pydantic.ValidationError` that raises the new refusal. Registered the new class in
`test_rest_transport.py`'s exhaustive `_REFUSAL_FACTORIES` dict (the parametrized
`test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value` test fails
loudly on a missing factory entry, per its own docstring — this closes that gap for the new
class). Added a new live-reproduction test,
`test_upload_with_malformed_selector_field_returns_422_not_a_raw_500`, that posts the same
malformed selector to `/documents/upload` and asserts `response.status_code == 422` and
`body["refusal_type"] == "MalformedSelectorPayloadError"`.
`databasise/tests/seam/test_rest_transport.py` (34 tests, up from the review's baseline) all
pass.

### WR-01: `score_gold_passage` divides by zero on an empty `gold_document_ids` list

**Files modified:** `databasise/eval/aa_run.py`, `databasise/tests/eval/test_aa_run.py`
**Commit:** `8846730`
**Applied fix:** Confirmed the crash is reachable exactly as described (empty
`gold_document_ids`, non-empty evidence → bare `ZeroDivisionError`). Moved the
`gold_ids = list(gold_document_ids)` conversion to the top of the function and added an early
`if not gold_ids: raise ValueError(...)` guard, before any evidence resolution or store access —
tighter than the review's suggested placement (raises before the empty-evidence early return, so
the function never touches the store on this path either). Added
`test_score_gold_passage_empty_gold_document_ids_raises_value_error_not_zero_division`, using a
store stub configured to raise if called, and non-empty evidence, to prove both the named
refusal and the "no store touch" property.

### WR-02: `aa_run.main()`'s `--spend` path does not catch a partial/degraded run or a `SeamRefusalError`

**File:** `databasise/eval/aa_run.py`
**Commit:** `7540450`
**Applied fix:** Confirmed the calibration `try/except` block only caught
`(SplitNotCalibratableError, UnparseableJudgeVerdictError, UnusableFloorError)`. Added
`from databasise.seam.refusals import SeamRefusalError` and broadened the except tuple to include
`RuntimeError` (run_one_pass's own confounded partial/degraded-pass refusal) and
`SeamRefusalError` (the base class for every refusal the real `engine.query()` call could raise).
Confirmed live, before editing, that `SeamRefusalError` is importable from `aa_run.py` with no
circular import: `databasise/seam/refusals.py` has zero `databasise.*` imports of its own, and
`python -c "import databasise.eval.aa_run"` succeeds cleanly both before and after the change.
No test was added for this except-clause directly (the `--spend` real-run path is deferred and
unauthorized in this environment per the module's own docstring, and exercising it would require
building the full live-client/engine harness this module explicitly gates behind a checkpoint);
the import-safety check and the full `test_aa_run.py` pass (14/14) are the verification available
without spending a real run.

## Skipped Issues

None — all four in-scope findings were fixed.

## Out of Scope

### IN-01: `test_aa_run.py`'s blanket `pytestmark = pytest.mark.asyncio` on sync tests (pre-confirmed)

**File:** `databasise/tests/eval/test_aa_run.py:42`
Not attempted — `fix_scope` is `critical_warning`, which excludes Info-tier findings. Cosmetic
only (6-7 `PytestWarning`s, no behavioral effect); still visible in this round's test output.

### IN-02: Redundant exception type in `aa_run.main()`'s first except clause

**File:** `databasise/eval/aa_run.py:506`
Not attempted — `fix_scope` is `critical_warning`, which excludes Info-tier findings.
`SplitNotCalibratableError` still subclasses `ValueError`; the redundant tuple member is
harmless and unchanged.

## Verification

All commands run from `databasise/` using the project's own virtualenv (`databasise/.venv`).

```
$ .venv/bin/python -m pytest tests/evidence/test_falsifier5_record.py -q
11 passed in 0.11s

$ .venv/bin/python -m pytest tests/seam/test_rest_transport.py -q
34 passed in 5.06s

$ .venv/bin/python -m pytest tests/eval/test_aa_run.py -q
14 passed, 7 warnings in 1.78s   (warnings are the pre-existing, out-of-scope IN-01)

$ .venv/bin/python -m pytest tests/seam tests/eval tests/evidence -q
318 passed, 2 skipped, 7 warnings in 27.11s
```

The 2 skips and 7 warnings are pre-existing and unrelated to this round's fixes (verified by
running the same suite against the WR-01-only staged state mid-fix, which reproduced the
identical warning set). No new failures, skips, or warnings were introduced by any of the four
fixes.

Additional live checks performed before committing (not part of the pytest run, per the
task's own instruction to verify with a small live check):
- CR-01's regex verified against 4 hand-picked strings plus the actual formula text pulled from
  `databasise/evidence/FALSIFIER-5-EVIDENCE.md` (see Fixed Issues above for the exact inputs/outputs).
- CR-02's fix verified against a live `TestClient` posting the exact malformed payload from the
  review's own reproduction, both before the fix (500) and after (422).
- WR-02's import safety verified with `python -c "import databasise.eval.aa_run"` (succeeds; no
  circular import from adding `databasise.seam.refusals.SeamRefusalError`).

---

_Fixed: 2026-09-11_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
