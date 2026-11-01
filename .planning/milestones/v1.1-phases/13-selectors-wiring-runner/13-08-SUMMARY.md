---
phase: 13-selectors-wiring-runner
plan: 08
subsystem: seam
tags: [preflight-refusals, cyclic-wiring, strict-int-settings, guard-declaration, environment-digest, refusals]
requires: ["13-01", "13-04", "13-07"]
provides:
  - a cyclic wiring is one UnparseableWiringError (422, code cyclic-wiring) on query, ingest, delete and retry
  - max_concurrency and token_allowance accept only true ints (no bool, float or string coercion)
  - guard entries are shape-checked and their evaluating_node must be the guarded node or a transitive dependency
  - InvalidNodeSettingError and InvalidGuardDeclarationError (422, node id private) in refusals.__all__
  - EnvironmentDigestError becomes ForeignEngineRefusalError(failure_class=EnvironmentDigestUnavailable), 503
affects: [13-12]
actuals:
  tokens: 40000
  tasks: 3
  commits: 3
plan_head_before: c545e0032aa30a685476e1637c6a33ae2b8fcf25
plan_head_after: f3202097b5268c2794b258e34a4165ce2dd703b6
tech-stack:
  added: []
  patterns: ["one translating helper (_run_wiring) around every run_wiring call", "refusal detail kept on a private attribute and the server log; the body carries codes only"]
key-files:
  created:
    - databasise/tests/seam/test_preflight_refusals.py
    - databasise/tests/runner/test_guard_evaluation.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/refusals.py
    - databasise/seam/rest.py
    - databasise/runner/scheduler.py
    - databasise/runner/guards.py
    - databasise/tests/seam/test_rest_transport.py
key-decisions:
  - "A cycle is a violation code added inside _refuse_unparseable; the defensive RuntimeError after run_wiring on the query path is deleted because the refusal now precedes it"
  - "GuardDeclarationError keeps its positional (guard_name, granularity) pair; node_id and problem are new keyword-only fields"
requirements-completed: [WIRE-05]
status: complete
duration: 2h
completed: 2026-10-19
---

# Phase 13 Plan 08: Pre-dispatch refusals are named, settings are strict, guards are checked Summary

**A cyclic wiring is now one named 422 on all four write and query paths, `max_concurrency` and `token_allowance` are never coerced, a misdeclared guard is refused before any node runs, and every runner pre-flight error reaches REST as a named refusal instead of a 500.**

## Accomplishments

- `seam/engine.py`: `_refuse_unparseable` adds `CODE_CYCLIC_WIRING` when `parsed.report.cycles` is non-empty, logs each violation's code and pointer once, and keeps `(code, pointer, message)` on the refusal's private `_details`. The query-path `RuntimeError("... cyclic resolved wiring")` is gone. One `_run_wiring` helper wraps the four `run_wiring` call sites (`_run_corpus_ingest`, `_mirror_v1_index_only`, `delete_document`, `_execute_resolved`) and translates `InvalidMaxConcurrencyError`/`InvalidTokenAllowanceError` to `InvalidNodeSettingError`, `GuardDeclarationError` to `InvalidGuardDeclarationError`, and `EnvironmentDigestError` to `_foreign_fault(..., failure_class="EnvironmentDigestUnavailable")`.
- `seam/refusals.py`: `InvalidNodeSettingError(setting, *, node_id)` (public `setting` only) and `InvalidGuardDeclarationError(*, node_id)` (no public attribute), both in `__all__`, node id on `_node_id`. `UnparseableWiringError` and `ForeignEngineRefusalError` docstrings updated.
- `seam/rest.py`: `EnvironmentDigestUnavailable` joins `_ENGINE_UNAVAILABLE` (503).
- `runner/scheduler.py`: strict `isinstance(raw, int) and not bool` checks in both `_validated_*` helpers; `_validated_guards(node_id, config, parsed)` refuses a non-mapping entry, maps the `TypeError` from missing or extra keys, and refuses an `evaluating_node` outside the node's dependency closure; the `run_wiring` docstring lists every pre-dispatch case.
- `runner/guards.py`: `GuardDeclarationError` gains keyword-only `node_id` and `problem` (positional pair unchanged, so protected `test_dpr_fallback_guard.py` passes unedited).

## Task Commits

1. Task 1 (tracer): 195b4e1 - cycle code in `_refuse_unparseable`, `test_preflight_refusals.py` cycle legs
2. Task 2: a77c22d - strict ints, guard pre-flight, `test_guard_evaluation.py`, setting legs
3. Task 3: f320209 - translating helper, two seam refusals, 503 digest class, REST legs, two `_REFUSAL_FACTORIES` entries

## Intended ledger test_refs and fail-first evidence

Each fail-first run was against the source as it stood before the change that fixes it (Task 1 tests vs `c545e00` source, Task 2 tests vs `195b4e1`, Task 3 tests vs `a77c22d`). Every failure is a plain `AssertionError`. 13-01..13-07 did not touch these paths beyond adding `CODE_CYCLIC_WIRING`, so phase-base behaviour is the same.

**WIRE-05** - intended test_ref `databasise/tests/seam/test_preflight_refusals.py` (whole file)
- `::test_a_cyclic_query_wiring_is_refused_by_name_over_rest`: `AssertionError: Internal Server Error` / `assert 500 == 422`
- `::test_a_cycle_and_an_unknown_component_are_one_refusal`, `::test_the_refusal_body_carries_codes_only`, `::test_a_refused_cyclic_request_repeats_the_same_refusal`: same 500 (`assert (500, None) == (422, 'UnparseableWiringError')` for the repeat leg)
- `::test_ingest_delete_and_retry_refuse_a_cyclic_corpus_wiring[ingest]`: `AssertionError: ForeignEngineRefusalError("... operation 'ingest' failed (RunIncomplete)")` / `assert 'ForeignEngineRefusalError' == 'UnparseableWiringError'`; `[delete]` the same with `'delete'`; `[retry]`: `AssertionError('a refused cyclic wiring must not reach v1')` / `assert 'AssertionError' == 'UnparseableWiringError'` (the pre-fix retry reaches the stubbed v1 status probe)
- `::test_a_non_int_setting_is_refused_before_dispatch[max_concurrency-True-InvalidMaxConcurrencyError]`: `AssertionError: None` / `assert 'NoneType' == 'InvalidMaxConcurrencyError'` (the same shape for 2.7, '100', token_allowance 0.9, '100' and False)
- `::test_an_invalid_setting_reaches_rest_as_a_named_422[config0-max_concurrency]` and `[config1-token_allowance]`: `AssertionError: Internal Server Error` / `assert 500 == 422`
- `::test_a_misdeclared_guard_reaches_rest_as_a_named_422`: `assert 500 == 422`
- `::test_an_uncomputable_environment_digest_is_a_named_503`: `AssertionError: Internal Server Error` / `assert 500 == 503`
- `::test_a_repeated_refusal_writes_nothing`: `assert (500, None) == (422, 'InvalidNodeSettingError')`
- Edge rows: adjacency and empty (`::test_boundary_settings[...]`) pass before and after by design (accepted values); ordering is `::test_a_cycle_and_an_unknown_component_are_one_refusal`; idempotency is the two repeat tests (refusal repeated, trace row count unchanged); encoding is the parametrised non-int test; concurrency (gate released after a refusal) is `backstop`.
- The requirement text's KeyError-on-scheduled leg is stale since feadf3e and is not re-created (per the plan).

**WIRE-08** (row's test_ref is set in 13-12) - `databasise/tests/runner/test_guard_evaluation.py`
- `::test_a_misplaced_evaluating_node_is_refused_before_dispatch[downstream]` (and `[sibling]`, `[no-such-node]`): `AssertionError: None` / `assert 'NoneType' == 'GuardDeclarationError'`
- `::test_a_guard_entry_with_wrong_keys_is_refused_by_name[renamed-key]`: `AssertionError: TypeError("declare_guard() got an unexpected keyword argument 'guard_name'")` / `assert 'TypeError' == 'GuardDeclarationError'`; `[missing-key]` and `[extra-key]` the same shape; `[not-a-mapping]` also a bare `TypeError`
- `::test_an_inadmissible_granularity_is_refused_with_the_guarded_node`: fails on the missing `node_id` (`getattr(exc, "node_id", None) == "guarded"`)
- Pass by design before the fix (accepted cases): `::test_an_evaluating_node_that_is_the_guarded_node_or_an_ancestor_is_accepted[guarded|root]`

## Verification

- `cd databasise && .venv/bin/pytest -q tests/seam tests/mcp tests/runner tests/validator tests/wirings tests/identity tests/parts tests/parts_core tests/evidence tests/parity`: `1889 passed, 3 deselected`.
- Protected tests pass unedited: `test_refusal_catalogue.py`, `test_refusal_status_codes.py`, `tests/mcp/test_mcp_refusal_mapping.py`, `test_dpr_fallback_guard.py`.
- Acceptance greps: `isinstance(raw, bool)` twice in `scheduler.py`; `CODE_CYCLIC_WIRING` import plus use in `engine.py`; `class InvalidNodeSettingError` and `class InvalidGuardDeclarationError` in `refusals.py` and `__all__`; `EnvironmentDigestUnavailable` in `engine.py` and `rest.py`; "does not yet support a cyclic" gone.

## Deviations from Plan

None - plan executed as written. Minor choices inside the plan: the corpus cycle test stubs `_corpus_op_or_refuse` so a pre-fix retry cannot start a v1 subprocess; the cyclic "unknown component" node is made a dependency of the provides node so the D-16 prune keeps it.

## Known Stubs

None.

## Threat Flags

None. T-13-16 (codes only in the body) is asserted by `test_the_refusal_body_carries_codes_only` and the REST legs (no node id in the body); T-13-17 by the REST translation tests; T-13-18 by the parametrised non-int tests.

## Self-Check: PASSED

- Files created: `databasise/tests/seam/test_preflight_refusals.py`, `databasise/tests/runner/test_guard_evaluation.py` present.
- Commits 195b4e1, a77c22d, f320209 are ancestors of HEAD.
