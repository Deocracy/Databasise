---
phase: 06-hipporag-2-side-by-side
fixed_at: 2026-09-11T15:14:03Z
review_path: .planning/phases/06-hipporag-2-side-by-side/06-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 06: Code Review Fix Report

**Fixed at:** 2026-09-11T15:14:03Z
**Source review:** .planning/phases/06-hipporag-2-side-by-side/06-REVIEW.md
**Iteration:** 1

**Summary:**

- Findings in scope: 2 (WR-01, WR-02 — `fix_scope: critical_warning`; IN-01 excluded, and its own
  Fix section states "Optional — no code change needed")
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-02: bare `RuntimeError` in the `--spend` except tuple is broader than the fix needs

**Files modified:** `databasise/eval/aa_run.py`
**Commit:** `a886f1d`
**Applied fix:** Added `ConfoundedPassError(RuntimeError)` (module-level, next to the file's other
locally-defined refusal classes `UnparseableJudgeVerdictError`/`SplitNotCalibratableError`,
following the same attribute-carrying constructor pattern `calibration.StaleNullError` and this
file's own `UnparseableJudgeVerdictError` already use). `run_one_pass` now raises
`ConfoundedPassError(question_id, partial=..., degraded=...)` instead of a bare `RuntimeError` for
a confounded (partial/degraded) pass. `main()`'s `--spend` except tuple now catches
`ConfoundedPassError` by name instead of bare `RuntimeError` — this stops the tuple from also
silently swallowing `calibration.StaleNullError` (a `RuntimeError` subclass `calibrate_family`
explicitly must not have caught) or an unrelated `RuntimeError` from deeper in the call chain.
Also updated `run_one_pass`'s own docstring to name `ConfoundedPassError` instead of the generic
`RuntimeError` it used to cite. Did not drop `UnusableFloorError`/`UnparseableJudgeVerdictError`
from the except tuple: the review's "redundant" observation was contingent on the bare
`RuntimeError` entry that this fix removes — once removed, both are load-bearing again (neither
`ConfoundedPassError` nor `SeamRefusalError` would catch them).

### WR-01: WR-02's fix (from the prior round) had zero test coverage

**Files modified:** `databasise/tests/eval/test_aa_run.py`
**Commit:** `7d69588`
**Applied fix:** Added `test_main_spend_path_catches_confounded_pass_error_and_exits_1`, which
monkeypatches `aa_run._load_env_file`, `aa_run._build_clients`, `aa_run.Databasise`,
`aa_run.MultiNamespaceVectorStore` to lightweight stub doubles and `aa_run.calibrate_family` to an
async stub raising `ConfoundedPassError("q1", partial=True, degraded=False)`, then drives
`main(["--split", "dev", "--spend"])` and asserts it returns `1` with the refusal's message on
stderr rather than letting the exception propagate as an unhandled traceback. Written after WR-02
so the test exercises the renamed `ConfoundedPassError` class directly, per this round's own fix
guidance.

## Skipped Issues

None — both in-scope findings were fixed.

## Verification

Ran inside an isolated git worktree (`gsd-reviewfix/06-609645`, fast-forwarded onto `main` and
removed after this report was written — not reproducible from the main checkout post-cleanup, but
reproducible by checking out either commit hash above).

- `databasise/.venv/bin/python -m pytest tests/eval/test_aa_run.py -q` (run against the worktree's
  own source via `PYTHONPATH=<worktree-root>` — the shared venv's editable install otherwise
  resolves `databasise` from the main checkout, not the worktree): 15 passed (14 pre-existing + the
  new WR-01 test), after each of the two commits above.
- `databasise/.venv/bin/python -m pytest tests/eval/ tests/seam/test_rest_transport.py -q`: 90
  passed, no regressions.
- `databasise/.venv/bin/python -m ruff check eval/aa_run.py tests/eval/test_aa_run.py`: 2
  pre-existing findings (an unsorted `dataclasses` import and an over-length `corpus_ingest`
  import line in `aa_run.py`, plus a blank-line-after-import in the test file), all present
  unchanged in `HEAD~1` — confirmed via `git show HEAD~1:... | ruff check --diff -` — not
  introduced by this round's diff, left as-is per minimal-diff scope.

---

_Fixed: 2026-09-11T15:14:03Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
