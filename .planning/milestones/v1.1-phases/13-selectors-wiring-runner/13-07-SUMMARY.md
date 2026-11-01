---
phase: 13-selectors-wiring-runner
plan: 07
subsystem: seam
tags: [compare, health, seam-events, refusals, api-inventory]
requires: ["13-05"]
provides:
  - compare with one selector runs the mutates_store check before any node runs
  - health() reports an environment-digest failure as a fixed reason and degraded status
  - _mach11_events reports failed for a mutating node that raised
  - tests pinning where each partly reachable refusal occurs; accurate API inventory rows
affects: [13-12, 13-13]
actuals:
  tokens: 21000
  tasks: 3
  commits: 4
plan_head_before: d6f128f1c8941f1f9d9c3f2db321fe3f8c2b8577
plan_head_after: 9980fdd8eba004dc11914e67496b3bee66d00074
tech-stack:
  added: []
  patterns: ["resolve once, check, then run", "digest computed off the event loop; only success memoised"]
key-files:
  created:
    - databasise/tests/seam/test_refusal_reachability.py
    - databasise/tests/identity/test_env.py
    - databasise/tests/seam/test_seam_events.py
  modified:
    - databasise/seam/engine.py
    - databasise/seam/refusals.py
    - databasise/seam/envelope.py
    - databasise/tests/seam/test_mutable_store_exclusion.py
    - docs/gui/API-INVENTORY.md
key-decisions:
  - "A single-selector compare resolves its selector once and runs the mutates_store check, then returns the bare envelope via _execute_resolved (D-11)"
  - "The seam event outcome is failed when the node trace status is not completed or a failure cause is set; halted only for a completed node whose budget halted (D-15)"
  - "The digest failure adds one fixed reason to engine_reason and no HealthReport field (D-16)"
requirements-completed: [WIRE-17, WIRE-15, WIRE-13]
coverage:
  - id: D1
    description: "compare with one mutating selector refuses before any node runs and writes no trace row; a plain single selector still returns a bare envelope; compare([]) still refuses"
    requirement: WIRE-17
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_refusal_reachability.py::test_compare_with_one_mutating_selector_is_refused"
        status: pass
    human_judgment: false
  - id: D2
    description: "health reports an environment-digest failure with a fixed reason and recovers when it computes again"
    requirement: WIRE-15
    verification:
      - kind: unit
        ref: "databasise/tests/identity/test_env.py::test_health_reports_a_failed_environment_digest"
        status: pass
    human_judgment: false
  - id: D3
    description: "a mutating node that raised reports a failed seam event; halted and completed stay distinct; an ingest with a mutating part carries one event"
    requirement: WIRE-13
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_seam_events.py::test_a_mutating_node_that_raised_reports_failed"
        status: pass
    human_judgment: false
duration: 35min
completed: 2026-10-19
status: complete
---

# Phase 13 Plan 07: One-selector compare refusal, health digest leg, failed seam events Summary

**`compare` with one selector now refuses a `mutates_store` wiring before any node runs, `/health` reports an environment-digest failure instead of `ok`, and a mutating node that raised reports a `failed` seam event instead of `halted`.**

## Accomplishments

- `seam/engine.py` `compare` (D-11): resolves every selector once (one included), runs the `mutates_store` check on each, then returns `_execute_resolved` for one selector (bare envelope) or goes on to the namespace pre-check and keyed map for two or more. The SEAM-11 key check still precedes resolution for two or more. `seam/refusals.py` docstring no longer says the one-selector path never raises; it keeps the word `unreachable` (protected `test_seam_doc_consistency.py` passes).
- `seam/engine.py` `health()` (D-16): `asyncio.to_thread(environment_hash)`; `EnvironmentDigestError` logs only the class name, appends `environment digest unavailable` after the existing reasons and clears `overall_ok`. No `HealthReport` field added. The protected health tests pass unedited.
- `seam/engine.py` `_mach11_events` (D-15): `failed` when the node trace `status` is not `completed` or `cross_process_failure_cause` is set; `halted` for a completed node with `budget_state == "halted"`; else `completed`. `component` is untouched (13-13, behind the LRAG-03 grant). `envelope.py` comment and `SeamEvent` docstring updated.
- `docs/gui/API-INVENTORY.md`: `UnbudgetableParticipantError` on /query, /query/stream, /compare with the reachability condition; `MutableStoreComparisonExcludedError` on /compare for one or more selectors; `NoWritePathForModalityError` on retry with a HippoRAG selector, ingest only as a kept mapping, and removed from delete (false since HIPP-16). The seam-event `component` text is left for 13-13. The inventory has no section for `POST /documents/{document_id}/retry`; the retry refusal is noted on the ingest row.

## Task Commits

1. Task 1 (tracer): 04bb39c - one-selector compare refusal, docstring, `test_refusal_reachability.py` (3 legs), reversed old test in `test_mutable_store_exclusion.py` (renamed `test_single_selector_resolving_a_mutating_wiring_is_refused`, unused `_ExecuteSpy` removed)
2. Task 2: 9f15f8d - four reachability pins, API inventory rows
3. Task 3: d6a8dbd - health digest leg, failed outcome, `test_env.py`, `test_seam_events.py`
4. Follow-up: 9980fdd - ingest-event test builds its mutating part from `LIGHTRAG_FULL_INGEST_PART` (exists at 7be6968^, unlike the index-sync part)

Verification: `tests/seam tests/runner tests/validator tests/wirings tests/identity tests/parts tests/parts_core tests/evidence tests/parity` -> 1752 passed, 3 deselected (protected tests included, no grant needed). The task-1 and task-2 verify commands and the task-3 verify command also pass on their own.

## Intended ledger test_refs and fail-first evidence

Pre-fix runs were made against the unchanged source at the point each test was written. For the code touched this equals phase base b0b5a6c, which the orchestrator's `record-fail --at` route re-checks. All failures are plain `AssertionError`.

**WIRE-17** - intended test_ref `databasise/tests/seam/test_refusal_reachability.py`.
- `::test_compare_with_one_mutating_selector_is_refused` (fails before the fix): `AssertionError: (<class 'NoneType'>, ResponseEnvelope(answer='', evidence=[], trace_token='Kag8Py6e...', ... seam_events=[]))` / `assert 'NoneType' == 'MutableStoreComparisonExcludedError'`. Before the fix the mutating wiring was run and a bare envelope came back.
- Pass at the base by design (they pin present reachability): `::test_compare_with_one_plain_selector_returns_a_bare_envelope`, `::test_compare_with_no_selector_is_still_refused` (the empty edge), `::test_an_unbudgetable_client_on_a_hipporag_query_is_refused`, `::test_the_shipped_client_with_usage_is_budgetable_on_lightrag`, `::test_retry_with_a_hipporag_selector_has_no_write_path`, `::test_every_shipped_family_has_a_corpus_ingest_wiring`.
- Edge rows: adjacency (plain single selector returns a bare envelope) and empty are tests above; ordering (refuse before any node, no trace row written) is asserted in the failing test through `_trace_rows`, and `test_mutable_store_exclusion.py::test_single_selector_resolving_a_mutating_wiring_is_refused` asserts the `_execute_resolved` spy has zero calls. Idempotency and concurrency stay `backstop`.

**WIRE-15** - intended test_ref `databasise/tests/identity/test_env.py` (health leg only; 13-12 adds the payload legs and sets the row).
- `::test_health_reports_a_failed_environment_digest`: `AssertionError: assert 'environment digest unavailable' in ((None or ''))` (engine_reason was None)
- `::test_health_recovers_once_the_digest_computes_again`: the same `AssertionError` on its failing leg (`assert 'environment digest unavailable' in ((None or ''))`); the recovered leg asserts the reason is absent after the fault is removed and `environment_hash.cache_clear()` runs (the idempotency edge).
- Ordering edge: the reason is appended after the v1, interpreter and client reasons in `health()`; concurrency stays `backstop`.

**WIRE-13** - intended test_ref `databasise/tests/seam/test_seam_events.py` (outcome and ingest legs; the component leg follows in 13-13, which sets the row).
- `::test_a_mutating_node_that_raised_reports_failed`: `AssertionError: assert ['halted'] == ['failed']`
- Pass at the base by design: `::test_a_budget_halted_mutating_node_reports_halted`, `::test_a_completed_mutating_node_reports_completed` (adjacency edge), `::test_a_run_with_no_mutating_node_emits_no_event` (empty edge), `::test_an_ingest_with_a_mutating_part_returns_one_seam_event`.
- The ingest node was also run in a detached worktree at 7be6968^ (the parent of the first 11-01 commit), copying only this file in: it collects and fails by `AssertionError: assert 0 == 1` (`IngestJob(job_id='t', enqueued=1)` has no `seam_events`). The other four tests of the file also failed there; their reason was not inspected because the ledger route only needs the ingest node at that commit. The worktree was removed.

## Deviations from Plan

None - plan executed as written. Two small choices:
- The ingest-event test needs a registry holding the test part, so it uses `default_registry()` plus `register`, with `engine._corpus_wiring` monkeypatched and a HippoRAG selector (no v1 gate). The first draft used `LIGHTRAG_V1_INDEX_SYNC_PART`, which does not exist at 7be6968^; commit 9980fdd switched it to `LIGHTRAG_FULL_INGEST_PART`.
- `test_mutable_store_exclusion.py` was unprotected (checked against the ledger test_ref list), so its reversed test is an in-place edit.

## Notes

- A node traced `not-scheduled` that nevertheless has a recorded touch would now read `failed` (status other than `completed`). The scheduler records no touch for a node it never ran, so this does not occur; `test_mach11_event.py`'s fixture reads its out-of-deps node this way and still passes (it asserts only the closed vocabulary).
- `ruff check` on the touched files reports pre-existing findings (import ordering, two unused `noqa`, one ASYNC230, `__all__` order); none were introduced here and none were reformatted.
- `query()` is not a comparison and still runs a single `mutates_store` selector; only `compare` refuses.

## Known Stubs

None.

## Threat Flags

None. T-13-14 is mitigated (check before any node for one selector, no trace row asserted); T-13-15 is mitigated (fixed reason text, class name only in the log).

## Self-Check: PASSED

- 04bb39c, 9f15f8d, d6a8dbd and 9980fdd are ancestors of HEAD; all listed files exist.
