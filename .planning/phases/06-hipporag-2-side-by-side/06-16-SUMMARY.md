---
phase: 06-hipporag-2-side-by-side
plan: 16
subsystem: eval
tags: [python, pytest, scipy, calibration, a-a-testing, hipporag, lightrag]

# Dependency graph
requires:
  - phase: 06-hipporag-2-side-by-side (06-14)
    provides: a green full suite baseline (947 passed, 3 skipped) and the fact-score/full-ingest fixes this driver's run_one_pass reads through
provides:
  - The first runnable A/A calibration driver in this repository — score_gold_passage, score_answer_level, run_one_pass, calibrate_family, estimate_calls, main
  - A dry-run-by-default CLI (databasise.eval.aa_run) that projects call counts without constructing a client
affects: [06-17, MACH-03, "Falsifier 5"]

# Actuals (#2632)
actuals:
  tokens: 10875
  tasks: 2
  commits: 1

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A driver module that never catches the statistical procedure's own refusals (UnusableFloorError/StaleNullError) — inherits calibrate_aa_floor's §AA.2 precondition unchanged rather than re-implementing it"
    - "Dry-run-by-default CLI: estimate_calls prints a real, computed call-count projection and returns before any client is constructed; --spend is the sole opt-in path to a live call"

key-files:
  created:
    - databasise/eval/aa_run.py
    - databasise/tests/eval/test_aa_run.py
  modified: []

key-decisions:
  - "Removed a `del StaleNullError` line that referenced a name never imported into the module (StaleNullError is not among calibration.py's imported names here) — the line raised NameError at import time. Verified the behavior claim behind it first: calibrate_family calls calibrate_aa_floor directly and never calls CalibrationResult.floor_for, so StaleNullError genuinely cannot be raised anywhere in this module's own code path; deleting the dead statement is correct and adds no second, weaker path to a floor."
  - "Committed the finished draft as a single task commit spanning both Task 1 and Task 2's scope, rather than manufacturing an artificial two-commit split — both files were already fully written together by the interrupted prior executor before this session began, so splitting them post hoc would misrepresent what was actually built when."

requirements-completed: []

coverage:
  - id: D1
    description: "score_gold_passage returns gold-document recall (2/3, 0/n, n/n), scores an empty evidence list as 0.0 without a store call, and propagates UnresolvableEvidenceReferenceError rather than treating a lost reference as a miss"
    requirement: "MACH-03"
    verification:
      - kind: unit
        ref: "databasise/tests/eval/test_aa_run.py#test_score_gold_passage_returns_the_gold_recall_fraction"
        status: pass
      - kind: unit
        ref: "databasise/tests/eval/test_aa_run.py#test_score_gold_passage_empty_evidence_scores_zero_and_touches_no_store"
        status: pass
      - kind: unit
        ref: "databasise/tests/eval/test_aa_run.py#test_score_gold_passage_propagates_unresolvable_evidence_reference_error"
        status: pass
    human_judgment: false
  - id: D2
    description: "score_answer_level makes exactly one judge call against the committed prompt, maps CORRECT/PARTIAL/INCORRECT to 1.0/0.5/0.0 case/whitespace-insensitively, and raises UnparseableJudgeVerdictError (carrying the raw text) on a verdict it cannot parse, never a default score"
    requirement: "MACH-03"
    verification:
      - kind: unit
        ref: "databasise/tests/eval/test_aa_run.py#test_score_answer_level_formats_prompt_and_maps_verdicts"
        status: pass
      - kind: unit
        ref: "databasise/tests/eval/test_aa_run.py#test_score_answer_level_raises_on_unparseable_verdict"
        status: pass
    human_judgment: false
  - id: D3
    description: "run_one_pass runs one arm once over a named split's question ids, returns scores keyed by exactly those ids plus every run's node traces, and never touches the judge for the gold_passage family"
    requirement: "MACH-03"
    verification:
      - kind: unit
        ref: "databasise/tests/eval/test_aa_run.py#test_run_one_pass_returns_scores_for_exactly_the_question_ids_and_their_traces"
        status: pass
      - kind: unit
        ref: "databasise/tests/eval/test_aa_run.py#test_run_one_pass_gold_passage_makes_zero_chat_calls"
        status: pass
    human_judgment: false
  - id: D4
    description: "calibrate_family runs a family twice, feeds paired_differences into calibrate_aa_floor, builds NullIdentity entirely from the bundle/family's own fields, propagates UnusableFloorError unchanged on a cache_hit-true trace, and is reproducible under a fixed seed"
    requirement: "MACH-03"
    verification:
      - kind: unit
        ref: "databasise/tests/eval/test_aa_run.py#test_calibrate_family_builds_identity_from_bundle_and_family"
        status: pass
      - kind: unit
        ref: "databasise/tests/eval/test_aa_run.py#test_calibrate_family_propagates_unusable_floor_error_on_cache_hit"
        status: pass
      - kind: unit
        ref: "databasise/tests/eval/test_aa_run.py#test_calibrate_family_is_reproducible_under_a_fixed_seed"
        status: pass
    human_judgment: false
  - id: D5
    description: "main's default (no --spend) path prints a real projection naming the question count and per-family call counts and constructs no client; --split sealed/holdout and an unknown/incompletely-covered split all refuse by name with a non-zero exit"
    requirement: "MACH-03"
    verification:
      - kind: unit
        ref: "databasise/tests/eval/test_aa_run.py#test_main_default_path_constructs_no_client_and_prints_a_real_projection"
        status: pass
      - kind: unit
        ref: "databasise/tests/eval/test_aa_run.py#test_main_refuses_unknown_split_or_split_not_covered_by_a_family"
        status: pass
      - kind: unit
        ref: "databasise/tests/eval/test_aa_run.py#test_main_refuses_holdout_and_sealed_splits_by_name"
        status: pass
      - kind: other
        ref: "uv run python -m databasise.eval.aa_run --split dev"
        status: pass
      - kind: other
        ref: "uv run python -m databasise.eval.aa_run --split sealed (non-zero exit)"
        status: pass
    human_judgment: false

duration: 45min
completed: 2026-09-10
status: complete
---

# Phase 06 Plan 16: A/A Calibration Driver Summary

**Finished an interrupted prior executor's uncommitted `databasise/eval/aa_run.py` — the first runnable A/A calibration driver in the repository, with a dry-run-by-default CLI and 13 passing tests proving both §EV.2 scorers, the paired-run pipeline, and calibrate_aa_floor's inherited refusals.**

## Performance

- **Duration:** ~45 min (this session — recovery/verification of an already-drafted, uncommitted implementation, not a from-scratch build)
- **Completed:** 2026-09-10
- **Tasks:** 2 (both already drafted on disk at session start; this session verified, repaired, tested, and committed them)
- **Files modified:** 2 (both new)

## Accomplishments

- Verified the entire uncommitted draft (`databasise/eval/aa_run.py`, `databasise/tests/eval/test_aa_run.py`) line-by-line against 06-16-PLAN.md's `<action>` text and every imported symbol's real source (`calibration.py`, `bundle.py`, `remint.py`, `corpus_ingest.py`, `run_arm.py`, `seam/evidence.py`, `seam/envelope.py`, `seam/trace_store.py`, `runner/trace.py`, `clients/base.py`, `seam/query.py`, `stores/vector.py`) — every call site, keyword argument, field name, and constructor signature matches.
- Diagnosed and fixed the one blocking defect: a `del StaleNullError` statement referenced a name the module's own import list never bound, raising `NameError` at import time and blocking pytest collection entirely. Confirmed the comment's behavioral claim first (`calibrate_family` never calls `CalibrationResult.floor_for`, so `StaleNullError` cannot fire in this module's own code path) before deleting the line — this is a Rule 1 bug fix, not a weakening of any refusal.
- Checked test coverage against all six `must_haves.truths` and all thirteen `<behavior>` items in the plan: the draft already contained exactly 13 test functions (Tests 1–13), matching the plan's own enumeration one-for-one. No test gaps found; no new tests were needed.
- Confirmed both per-question scorers, the paired-calibration pipeline, and the dry-run CLI all behave as specified: `score_gold_passage` returns exact gold-recall fractions and propagates `UnresolvableEvidenceReferenceError`; `score_answer_level` raises `UnparseableJudgeVerdictError` (never a default score) on an unrecognised verdict; `calibrate_family` propagates `UnusableFloorError` unchanged from a cache-hit trace and never calls `floor_for`; `main()`'s default path constructs no client and prints a real call-count projection; `--split sealed`/`holdout` refuse by name.

## Task Commits

Both tasks were already merged into one coherent draft before this session began (the interrupted prior executor wrote both files in full before being killed). Splitting them into two commits post hoc would misrepresent when each piece was actually built, so this session committed the verified, repaired whole as one atomic commit:

1. **Tasks 1+2: the two per-question scorers, one A/A pass, paired calibration, and dry-run CLI** — `0a281fb` (feat)

**Plan metadata:** committed alongside this SUMMARY (see `/gsd-execute-phase`'s final commit step)

## Files Created/Modified

- `databasise/eval/aa_run.py` - The A/A calibration driver: `score_gold_passage`, `score_answer_level`, `run_one_pass`, `calibrate_family`, `estimate_calls`, `main`, plus `UnparseableJudgeVerdictError`, `SplitNotCalibratableError`, `PassResult`, `AARunResult`
- `databasise/tests/eval/test_aa_run.py` - 13 tests (Tests 1–13 per the plan's `<behavior>` blocks), all stub-based, reaching no network endpoint

## Decisions Made

- Deleted the dead `del StaleNullError` statement rather than importing `StaleNullError` to satisfy it — the module never calls `CalibrationResult.floor_for`, so there is nothing in `aa_run.py`'s own code path that could ever raise `StaleNullError`; importing it just to delete it again would have been a no-op with an extra name to track.
- Recorded a single task commit for both Task 1 and Task 2's scope instead of an artificial two-commit split, given the recovery circumstances (see Deviations below for the full rationale).
- Left `requirements mark-complete` uncalled for both `MACH-03` and `MACH-02` in this plan's frontmatter `requirements: [MACH-03, MACH-02]`. `MACH-02` was already `Complete` (closed by 06-04); `MACH-03` is bound by this plan's own explicit prohibition ("MUST NOT flip MACH-03 to Complete") and its success criteria ("MACH-03 remains Pending in `.planning/REQUIREMENTS.md`"). Confirmed via `grep` against `.planning/REQUIREMENTS.md` before skipping the step: `MACH-03` still reads Pending; no annotation was added.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed a `del StaleNullError` statement that referenced an unbound name, causing `NameError` at import time**
- **Found during:** Recovery verification (before Task 1/2 could be considered complete — the module could not even be imported)
- **Issue:** `databasise/eval/aa_run.py` line 89 read `del StaleNullError  # imported for read_first context only — calibrate_family never calls floor_for`, but `StaleNullError` was never imported (the `from databasise.eval.calibration import (...)` block above it lists only `CalibrationResult`, `NullIdentity`, `UnusableFloorError`, `calibrate_aa_floor`, `paired_differences`). `del` on an unbound name raises `NameError`, which fired at module import time and blocked pytest from collecting `test_aa_run.py` at all.
- **Verification before fixing:** Read `databasise/eval/calibration.py` in full and confirmed `calibrate_family` only ever calls `calibrate_aa_floor` directly — it never calls `CalibrationResult.floor_for` (the only function in the codebase that can raise `StaleNullError`). The comment's claim ("calibrate_family never calls floor_for") is therefore literally true, and `StaleNullError` genuinely cannot be raised anywhere in `aa_run.py`'s own code path. Removing the dead statement does not weaken the plan's `MUST NOT add a second path to a floor that bypasses calibrate_aa_floor's own cache-bypass and staleness refusals` prohibition — that refusal path (`UnusableFloorError` via `_verify_cache_bypassed`) is untouched and is exercised directly by Test 9.
- **Fix:** Deleted the `del StaleNullError` line and its trailing comment. No other line changed.
- **Files modified:** `databasise/eval/aa_run.py`
- **Verification:** `uv run python -c "from databasise.eval import aa_run"` succeeds; `uv run pytest -q tests/eval/test_aa_run.py -x` → 13 passed; full suite → 960 passed, 3 skipped.
- **Committed in:** `0a281fb`

---

**Total deviations:** 1 auto-fixed (1 bug — Rule 1)
**Impact on plan:** The fix is a one-line deletion of dead, incorrect code with no behavioral surface; every prohibition and truth in the plan's `must_haves` still holds exactly as specified. No scope creep.

## Issues Encountered

- **Recovery scope, not net-new work.** This plan's actual deliverable (`databasise/eval/aa_run.py` and its tests) had already been fully drafted, structurally complete, by a prior executor that was killed before committing. This session's work was verification (reading every real source file every import touches, confirming every call site's keyword arguments and field names against the actual signatures), one bug fix (see above), and a coverage audit against the plan's six `must_haves.truths` and thirteen `<behavior>` items — which found the draft's 13 tests already matched the plan's Tests 1–13 one-for-one, so no test gaps needed filling. The `<recovery_state>` note that "6 tests is thin" did not hold once the file was actually read in full (`grep -c "def test_"` counts 13, not 6); flagged for the record in case that count was based on a partial or stale view of the file.
- **No live API spend occurred anywhere in this plan.** All 13 tests use in-file stub doubles (`_StubEngine`, `_StubVectorStore`, `_RecordingLLMClient`); `main()`'s dry-run default path was proven to construct no client (Test 11, asserted via a monkeypatched constructor that raises `AssertionError` if called); the two CLI invocations run for real verification (`--split dev`, `--split sealed`) both exercise only the estimate-only/refusal paths, never `--spend`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `databasise.eval.aa_run` is genuine, runnable, tested code — proven against stub clients and the committed `bundle@v1` fixture (17 dev questions, both `gold_passage`/`answer_level` families fully cover them). It has not been invoked for real (no `--spend`) in this environment.
- 06-17 is the next plan named in the objective as holding "06-17's own blocking spend checkpoint" — the actual `--spend` A/A calibration run this driver makes possible, and the point at which MACH-03/Falsifier 5 can finally move off Pending.
- `MACH-03` stays `Pending` in `.planning/REQUIREMENTS.md`, unchanged by this plan, per the plan's own explicit prohibition.

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-10*
