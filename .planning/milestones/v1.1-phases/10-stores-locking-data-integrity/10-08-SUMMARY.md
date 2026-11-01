---
phase: 10-stores-locking-data-integrity
plan: 08
subsystem: runner-capability-scoping
tags: [capability-scoping, effect-to-store, allowlist-proxy, d-09, stor-05]
status: complete

requires: ["10-07"]
provides:
  - "databasise/parts_core/__init__.py: EFFECT_TO_STORE (17 effects -> (kind, mode) or None), _READ_ALLOWLIST, _ENGINE_ONLY, _StoreProxy; UndeclaredEffectError(..., reason=None); CapabilityScopedStores.require on the table"
  - "databasise/runner/scheduler.py: _ScopedStoresView resolves through EFFECT_TO_STORE and prefers a declared write mode over a read mode"
  - "databasise/parity/storage_audit.py: _declared_handles uses EFFECT_TO_STORE; store-less effects permit no handle"
  - "databasise/seam/engine.py: _accounted_store_keys uses EFFECT_TO_STORE; _ACCOUNTABLE_STORE_EFFECT_PREFIXES removed"
  - "databasise/tests/runner/test_capability_scoping_modes.py (new, 33 cases)"
affects: [every future part (allowlists are the part-boundary contract), 10-09, 10-10]

actuals:
  tokens: 7278
  tasks: 2
  commits: 2
plan_head_before: d7bb8e7ae50ac19256f6609f6d00f3da2ade2e08
plan_head_after: 53382e51e9cd95561d8516af0905b4932f8259bf

tech-stack:
  added: []
  patterns:
    - "Allowlist proxy with __slots__ and __getattr__: engine-only names refused in both modes, read mode refuses any name outside the kind's allowlist naming writes_<kind>, select() re-wraps the child in the same mode"

key-files:
  created:
    - databasise/tests/runner/test_capability_scoping_modes.py
  modified:
    - databasise/parts_core/__init__.py
    - databasise/runner/scheduler.py
    - databasise/parity/storage_audit.py
    - databasise/seam/engine.py
    - databasise/tests/runner/test_scheduler.py
    - databasise/tests/parity/test_storage_audit.py

key-decisions:
  - "An engine-only name raises UndeclaredEffectError whose .effect is the method name and whose message says 'is engine-only'; a read-mode mutator raises with .effect == 'writes_<kind>'. drop on a read handle therefore reports the engine-only refusal, because the engine-only check runs first"
  - "Writable handles are proxies too (needed to hold back the lifecycle methods), so a handle is never the raw store object; two unprotected tests that compared the handle to the raw store now compare the proxy's _target"

requirements-completed: [STOR-05]

duration: 23min
completed: 2026-10-17
---

# Phase 10 Plan 08: Capability scoping per access mode Summary

A node that declares only `reads_X` now receives a read-only allowlist proxy through the real scheduler dispatch path, and a node that declares `writes_X` receives the writable handle. Lifecycle methods are engine-only on every handle, and the store-less effects are refused before `raw_stores` is read. One `EFFECT_TO_STORE` table drives the runner, the parity audit and the engine's MACH-11 accounting (D-09).

## What was built

- `EFFECT_TO_STORE` covers all 17 `Effect` members. Six map to `(kind, "r"|"w")` for kv, vector and graph. The other eleven map to `None`.
- `_StoreProxy(target, kind, mode, declared)`:
  - It refuses the seven `_ENGINE_ONLY` names in both modes: `index_done_callback`, `drop_pending_index_ops`, `finalize`, `drop`, `prepare`, `commit_prepared` and `abort_prepared`.
  - In read mode it refuses any name outside the D-09 per-kind allowlist with `UndeclaredEffectError("writes_<kind>")`.
  - `select()` wraps the selected `FaissVectorStore` in a proxy of the same kind and mode.
- `CapabilityScopedStores.require` refuses an undeclared effect as before. A `None` entry is refused with "no store backs effect X" before any `raw_stores` access. A missing store key still raises `StoreNotWiredError`.
- `_ScopedStoresView.__getitem__` collects every declared effect that maps to the key and takes the write mode if one is declared (research Pitfall 6). The recorder call is unchanged.
- `storage_audit._declared_handles` and `engine._accounted_store_keys` use the same table. `writes_artifact`, `mutates_store`, `net` and the other store-less effects no longer produce bogus `("store", "artifact")`-style handles or keys.
- The parity builder is covered with no change to `run_arm.py`. A test asserts that `run_arm._scheduler is scheduler` and that no file under `parity/` constructs `CapabilityScopedStores(`.

## TDD evidence

- Task 1 RED, before any source change: `1 failed, 3 passed`. `test_case_1_reads_kv_node_cannot_upsert_and_nothing_is_written` failed with `KeyError: 'n1'` because no node exception was recorded: the read-only upsert succeeded.
- Task 1 GREEN: `tests/runner/test_capability_scoping_modes.py tests/parts/test_reference_parts.py tests/runner` gave `66 passed`. `tests/parts_core tests/parts tests/seam/test_hipporag_write_path.py tests/seam/test_ingest_abort.py` gave `204 passed`. The tracer gate re-ran both suites with the same counts before Task 2 started.
- Task 2 RED, against the Task 1 source: `3 failed, 30 passed`.
  - `test_storage_audit_uses_the_same_table` failed: `_declared_handles(['writes_artifact'])` returned `{('store', 'artifact')}`.
  - `test_no_effect_is_mapped_to_a_store_by_splitting_its_name` failed on `storage_audit.py` and `engine.py`.
  - `test_every_allowlisted_name_resolves_on_a_read_proxy` failed because of a bug in the test itself: it looked up `select` on the selected child. The test was fixed.
- Task 2 GREEN:
  - `tests/runner/test_capability_scoping_modes.py tests/parity/test_storage_audit.py tests/seam/test_mach11_event.py`: `62 passed`.
  - `tests/parts_core tests/parts tests/runner tests/parity tests/seam`: `1090 passed, 1 skipped, 3 deselected`.
- Full gate, `tools/check_offline_suite.py`: `1718 passed, 1 skipped, 4 deselected`, under both `pytest` and `python -m pytest`.

Step 5 grep, `grep -rn 'split("_", 1)' databasise/parts_core databasise/runner databasise/parity databasise/seam`: empty output, exit 1. `grep -rn "CapabilityScopedStores(" databasise/parity`: empty output, exit 1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two unprotected tests compared a scoped handle to the raw store**
- **Found during:** Task 1 (`tests/runner/test_scheduler.py::test_12`) and Task 2 (`tests/parity/test_storage_audit.py::test_no_recorder_passed_behaves_exactly_as_before`).
- **Issue:** Both tests asserted `result["results"]["n1"]["kv"] == "<raw store>"`. Every handle is now a `_StoreProxy`, including writable handles, which need the proxy so the engine-only lifecycle methods stay blocked. The plan's flagged assumption covered `is` checks in parts, not these two tests.
- **Fix:** Each assertion now compares the proxy's `_target`, so the tests still prove that the handle comes from the Part's declared effects. Neither file is on the 24-file protected list.
- **Files modified:** `databasise/tests/runner/test_scheduler.py`, `databasise/tests/parity/test_storage_audit.py`
- **Commits:** 07d7822, 53382e5

**2. Scheduler docstring wording.** The plan asked for the `_ScopedClientsView` suffix-rule sentence to be rewritten. It now says that the clients side uses its explicit table just as the store side uses `EFFECT_TO_STORE`.

No other deviations. No protected test file was edited.

## Known Stubs

None.

## Threat Flags

None. T-10-25, T-10-26 and T-10-27 are mitigated as planned, and each has tests.

## Commits

- 07d7822 feat(10-08): a reads_kv node gets a read-only kv handle through the scheduler; read plus write gets the writable one (STOR-05)
- 53382e5 feat(10-08): vector and graph read proxies, engine-only lifecycle, store-less effects refused, one table everywhere (STOR-05)

## Self-Check: PASSED
