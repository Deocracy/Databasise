---
phase: 13-selectors-wiring-runner
plan: 12
subsystem: identity-and-guards
tags: [wiring-identity, guard-signal, environment-hash, apportionment, hash-annotation]
requires: ["13-04", "13-06", "13-07", "13-08", "13-09", "13-10", "13-11"]
provides:
  - per-arm wiring_id (lightrag-<arm>, naive keeps lightrag-base) and arm_id in resolve_arm and all_wirings
  - wiring_instance_hash taken from the full resolved wiring before query, allowance and max_total_tokens injection
  - RunRecord.arm_id from the resolved wiring
  - GuardDeclaration.signal; evaluate_guards reads output[signal] and refuses a missing output or key
  - plain-dict fact-filter and assemble-result (wrapper classes deleted)
  - environment payload with OS, architecture and libc instead of platform.platform()
  - apportionment strings removed from the LightRAG wirings
  - one D-24 annotation in the rendered parity evidence
affects: [13-13]
actuals:
  tokens: 60000
  tasks: 3
  commits: 4
plan_head_before: 6e3db4b1e0f391e773deff949b0713e5a2c05bf6
plan_head_after: f85bcedc834f0f48dcac01ce6e50a270a514875f
tech-stack:
  added: []
  patterns: ["a guard reads one declared boolean key of the evaluating node's output", "identity hash taken before any injection"]
key-files:
  created: []
  modified:
    - databasise/wirings/resolve.py
    - databasise/seam/engine.py
    - databasise/seam/promotion.py
    - databasise/runner/guards.py
    - databasise/runner/scheduler.py
    - databasise/parts_core/hipporag/fact_filter.py
    - databasise/parts_core/hipporag/assemble_result.py
    - databasise/wirings/hipporag/base.json
    - databasise/identity/env.py
    - databasise/wirings/lightrag/base.json
    - databasise/wirings/lightrag/arm-local.json-patch.json
    - databasise/wirings/lightrag/arm-global.json-patch.json
    - databasise/wirings/lightrag/arm-hybrid.json-patch.json
    - databasise/parts_core/lightrag/truncator_token_budget.py
    - databasise/wirings/lightrag/README.md
    - databasise/evidence/parity_report.py
    - databasise/evidence/PARITY-EVIDENCE.md
    - databasise/evidence/HIPPORAG-PORT-RECORD.md
key-decisions:
  - "naive keeps wiring_id lightrag-base; the other four arms get lightrag-<arm> (D-03)"
  - "declare_guard validates granularity before signal so the protected four-keyword call still fails on its bad granularity"
  - "A guard output without its signal fails the evaluating node (GuardDeclarationError), never a fire"
requirements-completed: [WIRE-12, WIRE-08, WIRE-15, WIRE-18]
status: complete
duration: about 3h
completed: 2026-10-20
---

# Phase 13 Plan 12: Identity, guard signal, environment inputs and apportionment deletions Summary

**Run identity names the arm and is stable across queries on one arm; guards read one declared signal key; the environment hash drops the kernel string; the dead apportionment strings are gone; every shifted hash is annotated once.**

## Task Commits

1. Task 1 (tracer, WIRE-12, D-03): d2d4f0e
2. Task 2 (WIRE-08, D-19): c891dd2
3. Task 3 (WIRE-15, WIRE-18, D-16, D-17, D-24): 4133d15

## Follow-up fix f85bced (resolved; supersedes the earlier grant item)

The protected `tests/wirings/test_lightrag_guards.py::test_the_resolved_local_and_global_arms_are_unchanged` failed after Task 1 because `resolve_arm` stamped `wiring_id`/`arm_id` in code, so it differed from base plus patch. Fix, product side: the D-03 identity now lives in the data (each arm patch sets `/wiring_id` and `/arm_id`, naive only adds `/arm_id`; `wirings/hipporag/base.json` carries `arm_id`), and `resolve_arm`/`all_wirings` stamp nothing. No protected test was edited for it; wave command 1831 passed, other directories 620 passed, `test_query_trace_nodes.py` and the WIRE-12 row tests still pass.

## Task 1: row tests (WIRE-12) and fail-first evidence

All in `databasise/tests/seam/test_run_record_identity.py`. Unchanged source, plain AssertionError each:

- `::test_two_queries_on_the_local_arm_share_the_wiring_instance_hash`: `AssertionError: assert 'sha256:9964d...a4a8c4f71f1ee' == 'sha256:038e9...01182cc110047'`
- `::test_a_unicode_query_shares_the_hash`: `AssertionError: assert 'sha256:79269...daace3f9ec261' == 'sha256:1f365...a04762d74ff96'`
- `::test_local_and_naive_record_different_wiring_ids`: `AssertionError: assert 'lightrag-base' == 'lightrag-local'`
- `::test_every_arm_has_a_distinct_wiring_id`: `AssertionError: assert 2 == 6` (set `{'hipporag-base', 'lightrag-base'}`)

Earlier WIRE-12 legs in the same file (concurrency, trace_token, post-dispatch refusals) come from 13-04 and 13-10. The empty-query edge is the existing EmptyQueryObjectError refusal before dispatch, so no hash exists for it.

Granted edit of protected `tests/seam/test_query_trace_nodes.py`: lines 33-38 only, `_expected_instance_hash` now returns the hash of `canonicalise(resolve_arm(arm))`; the grant is `granted_at` 645.

## Task 2: row tests (WIRE-08) and fail-first evidence

All in `databasise/tests/runner/test_guard_evaluation.py` (before the guard change: 8 failed, 10 passed, every failure an AssertionError):

- `::test_a_declared_signal_fires_only_on_its_value[output0-True]` and `[output1-False]`
- `::test_a_plain_dict_output_without_the_signal_does_not_fire`: `AssertionError: GuardDeclarationError("guard entry keys [...'signal'...] must be exactly name, evaluating_node, value_when_not_fired and granularity")` (the `assert exc is None` message)
- `::test_a_non_mapping_output_does_not_fire`
- `::test_no_guards_means_none_fired` (empty edge)
- `::test_fired_guards_keep_declaration_order` (ordering edge)
- `::test_a_four_key_entry_is_refused_by_name`: `AssertionError: None` (the run completed, nothing refused)
- `::test_a_bad_granularity_is_still_the_refusal_when_the_signal_is_missing` passes at the base too; it is a regression guard for the protected four-keyword call

Existing cases in that file now carry `signal`. Protected edit: `tests/runner/test_trace_completeness.py::test_an_output_whose_comparison_raises_fails_that_node` (grant `granted_at` 647): guard gains `"signal": "flag"`, the body returns `{"flag": Bomb()}`, assertions untouched.

## Task 3: row tests (WIRE-15, WIRE-18) and fail-first evidence

WIRE-15, `databasise/tests/identity/test_env.py` (3 failed, 3 passed at Task 2 source):

- `::test_a_kernel_update_does_not_change_the_environment_hash`: `AssertionError: assert 'f071d8667ef8...5d64c7218bb1f' == '7c728bff388a...57a0cd6e779c1'`
- `::test_a_different_architecture_changes_the_hash`: `AssertionError: assert 'f071d866...' != 'f071d866...'`
- `::test_the_docstrings_list_every_input`: `AssertionError: python`
- `::test_an_empty_libc_still_hashes` passes at the base (empty edge, regression guard)
- Earlier 13-07 legs: `::test_health_reports_a_failed_environment_digest`, `::test_health_recovers_once_the_digest_computes_again`

WIRE-18, `databasise/tests/runner/test_runner_surface.py::test_no_wiring_json_carries_an_apportionment_string`: before the deletions `AssertionError: assert {'wirings/lig...ment_policy']} == {}`, offenders `arm-global`, `arm-hybrid`, `arm-local` and `base.json`.

`PARITY-EVIDENCE.md` differs from its previous render by the one "Pinned hashes" paragraph; `docs/system-model`, `evidence/wirings` and `evidence/parity_results` are untouched.

## Deviations from Plan

**1. [Rule 3 - Blocking] `tests/runner/test_live_metering.py` edited (unplanned).**
- **Found during:** Task 2 verification.
- **Issue:** `test_ordering_guards_fired_is_declaration_order_never_sorted_and_empty_list_never_none` declared three four-key guards, which the new `declare_guard` refuses.
- **Fix:** the three guards now carry `"signal": "completion"` (the fake LLM caller's output key; its string value never equals the `None` sentinel, so every guard still fires). The assertions are unchanged. The edit hook allowed it, so the file is not protected.
- **Commit:** c891dd2

**2. [Rule 3 - Blocking] Other unprotected tests edited as the plan expected:** `test_run_record.py` (test_6, test_11), `test_degraded_on_guard.py`, `test_cross_modality_run.py` (lines 117 and 123 now `wiring_family(...) == "lightrag"`).

**3. Protected `test_trace_completeness.py` edited under the 13-12 grant (647)** after the first dispatch stopped at this item.

## Verification

- Task 2 set (`tests/runner tests/parts_core/hipporag` plus the seam hipporag query and write path and port-record tests): 290 passed.
- Wave command (`tests/seam tests/runner tests/validator tests/wirings tests/identity tests/parts tests/parts_core tests/evidence tests/parity`): 1831 passed, 3 deselected after the follow-up fix f85bced (1830 passed and 1 failed before it).
- Remaining test directories (`clients eval foreign launcher ledger mcp stores` and `tests/test_*.py`): 620 passed, 1 deselected.

## Known Stubs

None.

## Threat Flags

None. `wiring_id` and `arm_id` stay in the debug-only trace fields; `tests/seam/test_leak.py` passes.

## Self-Check: PASSED

Commits d2d4f0e, c891dd2, 4133d15 are ancestors of HEAD; the SUMMARY's files exist.
