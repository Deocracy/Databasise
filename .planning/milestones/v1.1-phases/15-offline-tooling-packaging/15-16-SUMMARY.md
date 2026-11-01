---
phase: 15-offline-tooling-packaging
plan: 16
subsystem: eval
tags: [promotion-gate, aa-calibration, floors-store, tool-12]

requires:
  - phase: 15-03
    provides: "Databasise.__init__ shape the FloorStore attribute sits beside"
  - phase: 15-05
    provides: "offline suite and doc-consistency pins this plan keeps green"
  - phase: 15-10
    provides: "aa_run/calibration named errors, index_probe and the shared CLI contract"
provides:
  - "seam/floors_store.FloorStore and FloorRow over <store_root>/floors.db"
  - "two-stage promotion gate: GateNotCalibratedError lifts to GateVerbNotBuiltError / MeasurementPostureRefusalError for an arm with a fresh floor"
  - "calibrate_aa_floor refuses empty passes and returns a two-sided floor; score_answer_level takes the first whole-word verdict"
  - "aa_run --spend persists each family's floor keyed on the traces' wiring_instance_hash"
affects: [15-17, 15-18]

actuals:
  tokens: 15700
  tasks: 3
  commits: 3

plan_head_before: 9a7c7f5
plan_head_after: 0cf349133cfe91b3dfc27eac2958011637dff7c9

tech-stack:
  added: []
  patterns:
    - "jobs_store pattern for floors.db: per-call connection, file created on first write only, ?mode=ro reads"
    - "lazy eval imports inside the gate branch because eval.aa_run imports databasise.seam at module level"

key-files:
  created:
    - databasise/seam/floors_store.py
    - databasise/tests/seam/test_promotion_floor.py
    - databasise/tests/seam/test_floors_store.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/promotion.py
    - databasise/eval/calibration.py
    - databasise/eval/aa_run.py
    - databasise/tests/eval/test_calibration.py
    - databasise/tests/eval/test_aa_run.py
    - docs/gui/API-INVENTORY.md

key-decisions:
  - "Candidate NullIdentity (15-RESEARCH Open Question 2, A3): newest minted bundle@v under remint._COMMITTED_BUNDLE_ROOT, tier and metric by class (retrieval-side and index-side T1 / gold_passage_recall, answer-level T0 / answer_level_correctness), and the engine's own _DETERMINISM_SETTING and _CONCURRENCY_SETTING"
  - "A trace set carrying no wiring_instance_hash cannot match any floor, so stage 2 refuses it as GateNotCalibratedError"
  - "PassResult.wiring_instance_hashes is the sorted distinct tuple; calibrate_family sets CalibrationResult.wiring_instance_hash only when both passes together saw exactly one"
  - "aa_run checks every family for a hash before writing any floor, so an UnkeyableFloorError persists nothing"
  - "promote does not call enforce_gate_verb_posture any more; the stage-2 method raises the per-class refusal itself, and enforce_gate_verb_posture keeps its pinned signature"

requirements-completed: [TOOL-12]

duration: 40min
completed: 2026-10-21
status: complete
---

# Phase 15 Plan 16: Promotion floor persistence and the two-stage gate Summary

**A calibrated two-sided A/A floor is persisted per arm hash in `floors.db`, `aa_run --spend` writes it, and `promote` lifts `GateNotCalibratedError` for an arm whose own traces have a fresh floor, reaching the RIG F3.2 posture without appending anything.**

## Accomplishments

- `FloorStore`/`FloorRow` (`seam/floors_store.py`): `record` creates `floors.db` (WAL, `INSERT OR REPLACE`, primary key the first six columns); `any_floor` and `lookup` open `?mode=ro` and create nothing. No ledger import, no promotion-verb function.
- `Databasise.promote`: stage 1 (`not self._floors.any_floor()`) keeps the protected LEDG-08 behaviour; stage 2 (`_refuse_gate_verb`) reads the prior row through `Ledger.open_existing(read_only=True)` closed in `finally`, derives the class, and requires a `CalibrationResult.floor_for`-valid row for every hash in `arm_instance_hashes`. Missing or stale gives `GateNotCalibratedError`; valid gives `GateVerbNotBuiltError` (retrieval-side) or `MeasurementPostureRefusalError` (answer-level, index-side). It always raises before `_promote_sync`, so no `ledger.db` and no row.
- `calibrate_aa_floor`: refuses a pass with no node traces (`yielded no node traces`) before the bypass check; floor is `max(abs(ci.low), abs(ci.high))`; `CalibrationResult.wiring_instance_hash: str | None = None`.
- `score_answer_level`: first whole-word `CORRECT|PARTIAL|INCORRECT` in the upper-cased response.
- `aa_run`: `PassResult.wiring_instance_hashes`, `calibrate_family` keys the result, `main --spend` persists via `_persist_floors` or refuses with `UnkeyableFloorError` (in `_refusals()`).
- `docs/gui/API-INVENTORY.md` section 3.5.1 describes the two stages (no `UncalibratedFloorRefusalError` in it); section 7 and the section 6 row now name `floors.db`.

## Task Commits

1. **Task 1: tracer, floor lifts the gate** - `41a122e` (feat)
2. **Task 2: calibration and judge parser** - `57194e4` (feat)
3. **Task 3: aa_run persistence and inventory** - `0cf3491` (feat)

## Row test node ids and fail-first evidence

| Row | Intended test_ref node | Fail-first |
|-----|------------------------|------------|
| TOOL-12 | `databasise/tests/seam/test_promotion_floor.py::test_a_floor_for_the_arms_own_hash_lifts_the_gate_to_not_built` (whole file is the row file) | `record-fail --at 9a7c7f5` (the commit before this plan's first code commit). On that code: `AssertionError: databasise.seam.floors_store has no FloorStore/FloorRow` / `assert (None is not None)`; 8 of 9 nodes in the file fail by AssertionError the same way, the fresh-root node passes (stage 1 already refused). |

Supporting nodes (written first, run on unchanged source, failed by AssertionError):

- `databasise/tests/eval/test_calibration.py::test_empty_node_lists_are_refused` - `assert 'CalibrationResult' == 'UnusableFloorError'`
- `databasise/tests/eval/test_calibration.py::test_a_one_directional_shift_gives_a_non_negative_floor[-0.1]` - `assert -0.09999999999999998 >= 0`
- `databasise/tests/eval/test_calibration.py::test_a_part_that_omits_cache_hit_is_refused` and `[0.1]` shift: pass at HEAD (as the plan predicted)
- `databasise/tests/eval/test_aa_run.py::test_the_four_verdict_shapes_parse_to_correct` - `UnparseableJudgeVerdictError(...) == 1.0` for `CORRECT.`, `**CORRECT**`, `Verdict: CORRECT`, `CORRECT-dash`
- `databasise/tests/eval/test_aa_run.py::test_a_pass_records_the_traces_wiring_instance_hash` - `assert None == ('sha256:eee...',)`
- `databasise/tests/eval/test_aa_run.py::test_spend_persists_one_floor_per_family` - `AssertionError: []`; `test_a_result_without_a_hash_is_refused_by_name` - `assert 0 == 1`
- `databasise/tests/seam/test_floors_store.py` (4 nodes) - `AssertionError: databasise.seam.floors_store does not exist`

## Test results

- Task 1 set (floor, floors_store, posture, alias validation, refusal catalogue, status codes, measurement posture, promotion ledger record, ledger directory): 155 passed.
- Task 2 set (`databasise/tests/eval`, `test_node_trace_fields.py`): 108 passed.
- Task 3 set (eval, posture, floor, seam doc consistency): 162 passed.
- Plan verification `databasise/tests/seam eval runner ledger evidence`: 1491 passed in 480s, which includes every protected file the plan names (`test_promotion_posture.py`, the ledger directory, `test_refusal_catalogue.py`, `test_refusal_status_codes.py`, `test_node_trace_fields.py`, `test_lightrag_eval_store.py`, `test_promote_alias_validation.py`). No protected test failed and none was edited.
- The full wave command and `check_offline_suite.py` were not run by this plan (wave-level, orchestrator-owned).

## Decisions Made

See `key-decisions`. Recorded limits (also in the `aa_run` and `floors_store` docstrings and the inventory): no production part reports `cache_hit`, so a real A/A run is refused with `UnusableFloorError` after both passes have spent and persists no floor yet; only an engine started on the eval store root reads the floors.

## Deviations from Plan

**1. [Rule 3 - Blocking] Existing `_stub_spend_path` in `test_aa_run.py` returned a `CalibrationResult` with no hash**
- **Found during:** Task 3
- **Issue:** with `UnkeyableFloorError` in `main`, the 15-10 stub path (`test_two_families_run_inside_one_event_loop`) would exit 1.
- **Fix:** the stub now returns a result carrying a hash and takes an `instance_hash` keyword. The stub helpers named as kept (`_make_bundle`, `_StubEngine`, `_StubVectorStore`) are unchanged.
- **Files modified:** `databasise/tests/eval/test_aa_run.py`
- **Commit:** `0cf3491`

**2. [Rule 2 - Missing critical] Stage 2 refuses a trace set with no instance hash**
- **Issue:** "for every hash in arm_instance_hashes" is vacuously true for an empty list, which would let a hashless trace pass the floor check.
- **Fix:** an empty `arm_instance_hashes` raises `GateNotCalibratedError`; covered by `test_a_trace_without_an_instance_hash_cannot_use_any_floor`.
- **Commit:** `41a122e`

**3. Inventory edits beyond 3.5.1 and section 7:** the section 6 table row (line 736) said "No A/A floor is persisted" and the section 7 row's signed-mean and cache-bypass sentences were stale; both updated in `0cf3491`.

## Known Stubs

None.

## Threat Flags

None. T-15-43 to T-15-46 are mitigated by the tests above.

## Self-Check

PASSED: created files exist, commits 41a122e, 57194e4 and 0cf3491 are ancestors of HEAD.
