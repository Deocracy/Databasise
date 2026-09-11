---
phase: 06-hipporag-2-side-by-side
reviewed: 2026-09-11T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - databasise/clients/openai_compat.py
  - databasise/eval/aa_run.py
  - databasise/parity/build_hipporag_index.py
  - databasise/seam/engine.py
  - databasise/seam/refusals.py
  - databasise/seam/rest.py
  - databasise/wirings/resolve.py
  - databasise/tests/clients/test_openai_compat.py
  - databasise/tests/eval/test_aa_run.py
  - databasise/tests/evidence/test_falsifier5_record.py
  - databasise/tests/parity/test_build_hipporag_index.py
  - databasise/tests/seam/test_hipporag_write_path.py
  - databasise/tests/seam/test_rest_transport.py
findings:
  critical: 2
  warning: 2
  info: 2
  total: 6
status: issues_found
---

# Phase 06: Code Review Report (Incremental — gap-closure round)

**Reviewed:** 2026-09-11
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

This is an incremental review of the 13 files that changed across gap-closure plans 06-14
through 06-17 plus two earlier code-review fix commits, since the prior review at `cc3abf39`.
All 82 existing tests for these files pass, and the two items flagged as pre-confirmed in the
review brief were verified rather than re-derived:

1. `test_aa_run.py`'s blanket `pytestmark = pytest.mark.asyncio` over sync tests — confirmed,
   cosmetic, 6 PytestWarnings, no behavioral effect. Not re-litigated further (see Info).
2. `test_falsifier5_record.py`'s `floor_value_pattern` narrowing to exclude `<=` — **confirmed to
   leave a real hole**, detailed below as CR-01. This is the review's most significant finding.

Beyond those two, live reproduction (not just static reading) surfaced one more concrete defect:
`POST /documents/upload` crashes with an unhandled 500 instead of the documented 422 when a
client sends a malformed `selector` form field — verified against a running `TestClient`, not
inferred. `databasise/eval/aa_run.py` (the file flagged for closest reading) got that reading; two
lower-severity robustness gaps came out of it, both reproduced live.

`databasise/parity/build_hipporag_index.py`, `databasise/seam/refusals.py`, and
`databasise/wirings/resolve.py` read clean — no defects found in this pass.

## Critical Issues

### CR-01: `floor_value_pattern`'s `<=`-exclusion lets a fabricated floor value through undetected

**File:** `databasise/tests/evidence/test_falsifier5_record.py:99-105`
**Issue:** The regex added to `test_document_never_reports_a_floor_value` excludes any `=` sign
immediately preceded by `<` from the "reports a floor value" pattern, specifically to let the
pre-registered threshold formula (`floor <= 0.5 x ... floor`) through without a false positive.
Verified live:

```
'floor = 0.31'   -> MATCH      (caught, as intended)
'floor: 0.31'    -> MATCH      (caught, as intended)
'floor <= 0.31'  -> no match   (NOT caught)
'p95 <= 0.42'    -> no match   (NOT caught)
```

The narrowing excludes *every* use of `<=` after `floor`/`p95`, not just the one specific
pre-registered formula it was meant to admit. A future edit to `FALSIFIER-5-EVIDENCE.md` that
states a concrete fabricated number as an inequality bound — `"the observed floor <= 0.31"` —
passes this test silently, even though a reader would take that as a reported measurement. This is
exactly the failure mode this test exists to prevent (per the project's own evidence-integrity
discipline, a weakened guard is a correctness defect, not a style preference), and the hole is
provably real, not theoretical: it was reproduced against the actual compiled regex, not inferred
from reading the pattern.
**Fix:** Narrow the exclusion to the specific pre-registered formula shape rather than to the `<=`
operator generally — e.g. only exempt an `=`/`<=` that is followed by a variable/formula token
(`x`, `×`, another `floor`/`p95` reference) rather than a bare numeric literal, or require the
excluded match to contain a second `floor`/`p95` token later on the same line (the two-sided
"formula" shape the docstring actually describes):

```python
floor_value_pattern = re.compile(
    r"(?:p95|floor)[^a-zA-Z0-9\n]{0,10}(?:<=|=|:)[^a-zA-Z0-9\n]{0,5}\d"
    r"(?!\s*(?:x|\*|×)\s*\S*(?:floor|p95))",  # still excludes the two-floor formula shape
    re.IGNORECASE,
)
```
(Any equivalent narrowing works — the requirement is that `floor <= <number>` alone, with no
second `floor`/`p95` term on the right-hand side, must still fail the test.)

### CR-02: `POST /documents/upload` returns an unhandled 500, not the documented 422, on a malformed `selector` field

**File:** `databasise/seam/rest.py:260-285` (selector parse at line 284)
**Issue:** `selector` arrives as a JSON-encoded multipart form field and is parsed manually inside
the route body via `Selector.model_validate_json(selector)`. This raises a raw
`pydantic.ValidationError`, not `SeamRefusalError` or FastAPI's own `RequestValidationError` — the
only two exception families this app's registered handlers (and FastAPI's built-in ones) map to a
non-2xx response with a body. Reproduced live against a real `TestClient`:

```python
resp = client.post(
    "/documents/upload",
    files={"file": ("doc.txt", b"hello world", "text/plain")},
    data={"selector": "{not valid json"},
)
# resp.status_code == 500, resp.text == "Internal Server Error"
```

This directly violates the module's own stated design contract (module docstring: *"Non-success,
never a 2xx — the one property T-04-27's mitigation depends on. 422 ... is used uniformly for
every refusal kind"*). This endpoint carries no authentication (by explicit, accepted design), so
any network-reachable client can trigger this 500 with an ordinary malformed request, not even a
crafted attack — and no test in `test_rest_transport.py` or `test_hipporag_write_path.py` exercises
a malformed `selector` on the upload route, so this gap shipped untested.
**Fix:** Wrap the manual parse and translate the failure into an existing (or new)
`SeamRefusalError` subclass, mirroring `MalformedBase64PayloadError`'s own house pattern
(`refusals.py:209-228`) for exactly this "manually parsed field, not a pydantic validator, so the
exception must be raised directly" situation:

```python
try:
    parsed_selector = Selector.model_validate_json(selector) if selector else None
except pydantic.ValidationError as exc:
    raise MalformedSelectorPayloadError(field="selector") from exc
```

## Warnings

### WR-01: `score_gold_passage` divides by zero on an empty `gold_document_ids` list

**File:** `databasise/eval/aa_run.py:194-214` (division at line 214)
**Issue:** `matched / len(gold_ids)` has no guard for `len(gold_ids) == 0`. Reproduced live: an
envelope with non-empty evidence scored against `gold_document_ids=[]` raises a bare
`ZeroDivisionError` rather than a named refusal. This is reachable whenever a bundle's
`gold_passage` target family records an empty gold-document list for some question id (a
plausible bundle-authoring mistake, not requiring malicious input) — `_check_family_covers_questions`
only checks that a question id is present in `family.targets`, never that its value is non-empty.
The empty-*evidence* case is already handled explicitly (`if not envelope.evidence: return 0.0`,
line 204) — the empty-*gold-set* case is the one path left unguarded, and it crashes with an
opaque `ZeroDivisionError` instead of a named refusal, inconsistent with this codebase's own
"refuse by name, never crash opaquely" house style applied everywhere else in this same module.
**Fix:**
```python
gold_ids = list(gold_document_ids)
if not gold_ids:
    raise ValueError(
        f"score_gold_passage: gold_document_ids is empty — cannot compute a recall fraction "
        "with zero gold documents"
    )
matched = sum(1 for doc_id in gold_ids if str(doc_id) in resolved_document_ids)
return matched / len(gold_ids)
```

### WR-02: `aa_run.main()`'s `--spend` path does not catch a partial/degraded run or a `SeamRefusalError`, producing a raw traceback instead of the module's own clean-refusal pattern

**File:** `databasise/eval/aa_run.py:334-338` (raise site), `547` (incomplete except clause)
**Issue:** `run_one_pass` raises a bare `RuntimeError` when an envelope reports
`partial`/`degraded` true (line 334-338). `main()`'s `--spend` try/except (line 547) only catches
`(SplitNotCalibratableError, UnparseableJudgeVerdictError, UnusableFloorError)`. Neither this
`RuntimeError` nor any `SeamRefusalError` the real `engine.query()` call could raise (e.g. an
`UnsatisfiableSelectorError`, `EmptyQueryObjectError`, or `ForeignEngineRefusalError` from the
underlying HippoRAG/LightRAG dispatch) is caught — every other named refusal in this module prints
a clean message to stderr and returns exit code 1; these two classes of failure instead crash
`main()` with a raw Python traceback. This is a real gap in the one code path this module's whole
design is built around gating carefully (the `--spend` real-run path), even though it is
currently deferred/unauthorized in this environment and has not fired for real.
**Fix:** Broaden the except clause (or add a second one) to cover the confounded-run case and the
seam's own refusal family, consistent with how every other exit path in this module already
degrades cleanly:
```python
except (
    SplitNotCalibratableError,
    UnparseableJudgeVerdictError,
    UnusableFloorError,
    RuntimeError,          # confounded (partial/degraded) pass, run_one_pass's own refusal
    SeamRefusalError,      # any refusal the real engine.query() call itself raises
) as exc:
    print(str(exc), file=sys.stderr)
    return 1
```

## Info

### IN-01: `test_aa_run.py`'s blanket `pytestmark = pytest.mark.asyncio` on sync tests (pre-confirmed)

**File:** `databasise/tests/eval/test_aa_run.py:42`
**Issue:** Confirmed via a live test run: 6 `PytestWarning`s fire for sync test functions
(`test_score_gold_passage_*`, `test_main_*`) carrying the module-level `asyncio` mark. Purely
cosmetic — all 82 tests in this review's scope still pass.
**Fix:** Move the mark to only the async tests, or mark the sync ones individually as an
exception, per the review brief's own note that this is already known.

### IN-02: Redundant exception type in `aa_run.main()`'s first except clause

**File:** `databasise/eval/aa_run.py:506`
**Issue:** `except (SplitNotCalibratableError, ValueError) as exc:` — `SplitNotCalibratableError`
already subclasses `ValueError` (line 132), so the tuple's first member is redundant. Harmless,
but slightly obscures which specific error types this path is meant to guard against.
**Fix:** `except ValueError as exc:` alone is equivalent and clearer.

---

_Reviewed: 2026-09-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
