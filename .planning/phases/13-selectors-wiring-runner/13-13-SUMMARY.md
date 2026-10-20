---
phase: 13-selectors-wiring-runner
plan: 13
subsystem: seam-events
tags: [seam-event, capability-token, api-inventory, offline-gate]
requires: ["13-11", "13-12"]
provides:
  - SeamEvent.component is the resolved capability mutates_store on every emitted event
  - envelope docstring, API inventory and STATE concern brought current
  - offline gate green in both pytest styles
affects: []
actuals:
  tokens: 14000
  tasks: 2
  commits: 3
plan_head_before: efd111d
plan_head_after: ab2285a
tech-stack:
  added: []
  patterns: ["a consumer-visible event names a capability, never a modality's part"]
key-files:
  created: []
  modified:
    - databasise/seam/engine.py
    - databasise/seam/envelope.py
    - databasise/tests/seam/test_lightrag_ingest_mach11.py
    - databasise/tests/seam/test_seam_events.py
    - databasise/tests/seam/test_mach11_event.py
    - docs/gui/API-INVENTORY.md
    - .planning/STATE.md
key-decisions:
  - "component is the literal mutates_store in _mach11_events, no constant or lookup (D-15)"
requirements-completed: [WIRE-13, WIRE-11]
status: complete
duration: about 40m of work plus a 26 minute gate
completed: 2026-10-20
---

# Phase 13 Plan 13: Seam events name the capability, phase gate Summary

**Every SeamEvent now reports `component == "mutates_store"`; the LightRAG ingest and full-delete events no longer name `lightrag/...@version`.**

## Task Commits

1. Task 1 (tracer, WIRE-13, D-15): c167cdd (engine, envelope docstring, granted line 17, test_seam_events.py, test_mach11_event.py)
2. Task 2 code-side docs: 4707131 (docs/gui/API-INVENTORY.md)
3. Task 2 STATE concern (`.planning/` alone): ab2285a

## Protected-test handling

Precondition checked with the Read tool: `ledger/REQUIREMENTS.json` lists `databasise/tests/seam/test_lightrag_ingest_mach11.py` under `check_edit_grants` (granted_at 646). Only line 17 changed (`_SYNC = "mutates_store"`); the assertions at lines 28 and 34 are untouched. Both LRAG-03 tests ran (not skipped) and pass. No other protected test failed. `test_compare.py` and `test_rest_transport.py` needed no edit: their forbidden sets hold part names and the capability token is not one; both pass unchanged.

## Row tests (WIRE-13) and fail-first evidence

Intended ledger test_ref: `databasise/tests/seam/test_seam_events.py`. Nodes:

- `::test_an_emitted_event_names_the_capability` (new, component leg). Unchanged source: `AssertionError: assert ['test/seam-e...utator@1.0.0'] == ['mutates_store']` (`At index 0 diff: 'test/seam-events-mutator@1.0.0' != 'mutates_store'`).
- `::test_events_come_in_recorded_touch_order_one_per_mutating_node` (new, ordering edge). Passes before the change: a regression guard for the existing touch-order behaviour, not a fail-first leg.
- `::test_a_mutating_node_that_raised_reports_failed`, `::test_a_budget_halted_mutating_node_reports_halted`, `::test_a_completed_mutating_node_reports_completed`, `::test_a_run_with_no_mutating_node_emits_no_event`, `::test_an_ingest_with_a_mutating_part_returns_one_seam_event` come from 13-07 (outcome legs fail at the phase base by AssertionError; the ingest-event node passes at the phase base, met by LRAG-03, and fails at 7be6968^).

Companion edits: `tests/seam/test_mach11_event.py` has two component tests rewritten to expect `mutates_store` (`test_the_events_component_is_the_capability_not_the_out_of_deps_parts_name_at_version`, `test_the_real_deleting_events_component_is_the_capability_not_a_part_name_or_node_id`); both failed by AssertionError against the new source until updated, which shows they cover the same leg.

Result of the task verify command (seam_events, lightrag_ingest_mach11, mach11_event, compare, rest_transport, leak): 116 passed, no skips.

## Task 2: gate

`cd databasise && .venv/bin/python tools/check_offline_suite.py`, exit 0:

- `pytest -q -rs: 2453 passed, 4 deselected in 640.64s (0:10:40)`
- `python -m pytest -q -rs: 2453 passed, 4 deselected in 905.73s (0:15:05)`

## Consolidated WIRE ledger table (intended test_ref and fail-first route)

Fail-first route for every row is `record-fail --at <phase base b0b5a6c8de6090907d1ddeab19b7513f447f1a75>` unless stated; the orchestrator owns the ledger commands.

| Row | Intended test_ref | Fail-first route |
|-----|-------------------|------------------|
| WIRE-01 | `databasise/tests/seam/test_selector_reachability.py` | hybrid, global, ordering and docstring legs fail at base; the reads_graph mapping pins pass there by design |
| WIRE-02 | `databasise/tests/validator/test_top_level_refs.py` | ghost and per-arm legs fail for bypass, hybrid, local and global; KG-arm evidence in `tests/seam/test_evidence_position.py::test_a_local_arm_query_returns_non_empty_evidence_that_resolves` (needs the v1 venv) |
| WIRE-03 | `databasise/tests/seam/test_stop_reason_leak.py` | construction legs (13-04) plus value-walk, leaky, legacy and appended legs fail at base |
| WIRE-04 | `databasise/tests/seam/test_depth_label.py` | null-depth and free-text legs fail at base |
| WIRE-05 | `databasise/tests/seam/test_preflight_refusals.py` | cycle, strict-int, translation and digest legs fail at base; the KeyError-on-scheduled leg is stale since feadf3e and not re-created |
| WIRE-06 | `databasise/tests/validator/test_parse_report.py` | malformed-document, cycle, pointer, kind and message legs fail at base |
| WIRE-07 | `databasise/tests/validator/test_execution_mode_single_source.py` | deleted-duplicate, Phase-1, docstring and getattr legs fail at base; the calls_llm placement leg already passes (D-18) |
| WIRE-08 | `databasise/tests/runner/test_guard_evaluation.py` | misdeclared-guard (13-08) and signal legs fail at base |
| WIRE-09 | `databasise/tests/wirings/test_lightrag_guards.py` | top-level-guards scan and README leg fail at base |
| WIRE-10 | `databasise/tests/runner/test_trace_completeness.py` | status, wall-time, escape and cancelled legs fail at base |
| WIRE-11 | `databasise/tests/runner/test_node_trace_fields.py` | execution_mode, cache_hit, spent/allowance and default-tier legs fail at base; D-14 calibration consequence recorded in STATE.md by this plan |
| WIRE-12 | `databasise/tests/seam/test_run_record_identity.py` | concurrency (13-04), trace_token (13-10), hash and wiring-id legs fail at base |
| WIRE-13 | `databasise/tests/seam/test_seam_events.py` | failed-outcome (13-07) and component legs fail at base; the ingest-event node passes at base (met by LRAG-03) and fails at 7be6968^ |
| WIRE-14 | `databasise/tests/seam/test_engine_internals.py` | items and keyword legs fail at base; delete-namespace, resolve-graph and openie legs pass at base, satisfied by the STOR-07, STOR-03 and HIPP-04 commits |
| WIRE-15 | `databasise/tests/identity/test_env.py` | health (13-07), kernel and docstring legs fail at base |
| WIRE-16 | `databasise/tests/seam/test_advanced_query_members.py` | registration and docstring legs fail at base; the four-member refusal leg already passes (D-10) |
| WIRE-17 | `databasise/tests/seam/test_refusal_reachability.py` | one-mutating-selector compare leg fails at base; other legs pin present reachability |
| WIRE-18 | `databasise/tests/runner/test_runner_surface.py` | deletion, degraded-member, echo and wiring-string legs fail at base; the `_semaphore` leg passes there (used by openie since 40e541f) |

Granted edits needing plant runs: LRAG-03 `databasise/tests/seam/test_lightrag_ingest_mach11.py` (this plan, grant 646); LRAG-19 `databasise/tests/seam/test_query_trace_nodes.py` (granted edits of 13-11 and 13-12, the latter grant 645).

## Deviations from Plan

None. The plan's line ranges for `test_compare.py` and `test_rest_transport.py` named no component expectation to change, so they were left untouched; `test_mach11_event.py` was the only unprotected follow-up that needed an edit. API-INVENTORY line 148 also now lists `IngestJob` among the carriers of `seam_events`.

## Known Stubs

None.

## Threat Flags

None. T-13-27 mitigated: the component is a fixed token with no `/` or `@` (asserted), and `tests/seam/test_leak.py` passes.

## Self-Check: PASSED

Commits c167cdd, 4707131, ab2285a are ancestors of HEAD; engine.py contains `component="mutates_store"` once; the SUMMARY file exists.
