---
phase: 01-machine-core
plan: 08
subsystem: infra
tags: [asyncio, taskgroup, graphlib, budget, run-record, data-guards, d-08, d-09, d-10, d-11]

# Dependency graph
requires:
  - phase: 01-machine-core
    provides: "01-02's tracer runner/scheduler.py + runner/trace.py, 01-03's validator.execution_mode (host()/UnimplementedPlacementError) and cycle-safe depth, 01-04's parts.registry.dispatch()/parts_core.CapabilityScopedStores"
provides:
  - "runner/scheduler.py — completed: per-node asyncio.Semaphore (D-09), sorted ready-batch dispatch tie-break, D-08 placement refusal via validator.execution_mode, dispatch() via parts.registry (closes 01-04 inherited gap 1), CapabilityScopedStores wired into NodeContext.stores (closes 01-04 inherited gap 2), cycle-as-data via parsed.report.cycles (fixes a real uncaught-CycleError bug), structured-concurrency batch failure handling"
  - "runner/budget.py (new) — CONTRACT §9 budget as a splittable capability token: split_allowance() (floor-division, remainder to lexicographically-first branch), realised_share() (report-only), meter() (spend at declared boundary only), apportion()/ApportionmentPolicy (merge-side, D4 repair)"
  - "runner/trace.py — RunRecord.__post_init__ honesty invariant (D-10): refuses to construct a confounded run record, grounded in RIG §TR.3's required-together rule and the frozen schema's allOf clause"
  - "runner/guards.py (new) — declared data guards per CONTRACT §19.8: declare_guard() (refuses a missing/invalid granularity), evaluate_guards() (fired-guard list, never absent)"
affects: ["01-09"]

actuals:
  tokens: 15967
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "Scheduler-owned NodeContext extension attribute (ctx._semaphore): D-09's per-node semaphore is exposed to a part body without widening NodeContext's frozen public schema (parts/schema.py, out of this plan's lane) — the runner creates and sizes the semaphore, a body MAY voluntarily use it for its own internal fan-out, consistent with CONTRACT §9's V-7 repair that a node's internal parallelism is its own private implementation detail"
    - "_ScopedStoresView: a subscript-compatible wrapper around parts_core.CapabilityScopedStores so existing dict-style bodies (ctx.stores[\"kv\"]) keep working while every access routes through the underlying deny-by-default .require(effect) check, mapping a store key back to the declared effect whose suffix matches it"
    - "Pre-flight validation vs. in-flight partial outcome: a defect that means the run never starts (empty/violated wiring, max_concurrency < 1) raises before any node dispatches; a defect discovered mid-run (placement refusal, batch-internal node failure) returns a partial run record instead, per CONTRACT §9's explicit 'a partial run MUST NOT be discarded' rule"
    - "Honesty invariant as one required-together check, not three independent ones: RIG §TR.3's own wording ('records stop_reason, partial, degraded and degradation_reason as a required-together set') and the schema's allOf clause (either partial=true or degraded=true alone already demands both reason fields) together resolve what the plan's own action text phrased as three separate OR conditions into one consistent rule — partial and degraded now travel together"

key-files:
  created:
    - databasise/runner/budget.py
    - databasise/runner/guards.py
    - databasise/tests/runner/__init__.py
    - databasise/tests/runner/test_scheduler.py
    - databasise/tests/runner/test_budget.py
    - databasise/tests/runner/test_run_record.py
  modified:
    - databasise/runner/scheduler.py
    - databasise/runner/trace.py

key-decisions:
  - "Switched execution_mode derivation from the tracer-era duplicate in validator.depth to validator.execution_mode (01-03's hardened version with host()/UnimplementedPlacementError) — the two modules independently define a function of the same name; validator.depth's own copy is left untouched (out of lane; tests/parts/test_reference_parts.py still imports it unaffected)."
  - "Cyclic wirings now read parsed.report.cycles (already computed by validator.parse.parse_wiring) instead of relying on catching graphlib.CycleError from effective_depth() — that try/except was already dead code once 01-03's SCC-based depth landed, and the runner's own separate TopologicalSorter(...).static_order() call inside _resolve_identities would otherwise let a real dependency cycle's CycleError propagate uncaught past the runner. This was a genuine pre-existing bug this plan's Test 10 closes."
  - "A placement refusal (D-08) or a batch-internal node failure returns a partial run record (partial=True, the failing node's cross_process_failure_cause stamped) rather than raising past run_wiring() — grounded in CONTRACT §9's explicit 'a run that halts ... MUST be traced ... MUST NOT be discarded' rule, read as applying to any in-flight failure, not only a budget halt specifically."
  - "budget.py and guards.py are intentionally standalone modules this plan, not wired into scheduler.py's live dispatch path — each task's own <files> list in 01-08-PLAN.md scopes scheduler.py changes to Task 1 only; Tasks 2 and 3 list only their own new module + test file. See 'Known Gaps' below."

patterns-established:
  - "meter()/split_allowance()/apportion() as pure functions over TokenAccounting, never raising for an over-budget spend — the caller (a future scheduler integration) decides how a BudgetToken's state=\"halted\" becomes a traced, non-discarded partial run via trace.py's honesty invariant."

requirements-completed: []

coverage:
  - id: D1
    description: "Structured concurrency: per-node asyncio.Semaphore sized from config.max_concurrency, refused below 1 naming the node, never a process-wide cap; sorted-by-node-id ready-batch dispatch is stable across ten runs; D-11 isolation between two nodes with differing declared widths"
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/runner/test_scheduler.py (10 tests, Tests 1-5)"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-04 declaration-only dispatch refuses via registry.dispatch() instead of silently passing inputs through; CapabilityScopedStores is wired into the live NodeContext.stores; cyclic wirings return {\"cycle\": [...]} as data; a batch-internal node failure cancels siblings and marks the run not clean; a D-08 placement refusal stamps the derived placement without suppressing it"
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/runner/test_scheduler.py (Tests 6-10)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Budget metered at each node's declared boundary with exact integer split arithmetic (floor division, remainder to lexicographically-first branch), report-only realised share, multiplicative fan-out, merge-side apportionment declared at the apportioning node, and the five-member token accounting split"
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/runner/test_budget.py (10 tests)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The full RIG §TR.1 run-record field set validates against rig-trace.schema.json with zero errors; the honesty invariant refuses a confounded RunRecord on construction; declared data guards refuse a missing granularity and report exactly the guards that fired"
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/runner/test_run_record.py (12 tests)"
        status: pass
    human_judgment: false
  - id: D5
    description: "Plan 01-02's tracer test still passes unchanged after the runner completion; full suite green with no regression"
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/test_tracer_end_to_end.py (7 tests, part of the 162-test full suite)"
        status: pass
    human_judgment: false

duration: 95min
completed: 2026-08-30
status: complete
---

# Phase 01 Plan 08: Runner Completion — Budget Metering, Structured Concurrency, Full Run Record Summary

**Runner completed with a per-node semaphore and D-08 placement refusal in scheduler.py, a standalone budget.py implementing CONTRACT §9's exact-arithmetic splittable capability token, and trace.py's honesty invariant plus a new guards.py for CONTRACT §19.8's declared data guards — 162/162 tests green, both of 01-04's inherited gaps closed, and a real pre-existing cyclic-wiring bug fixed along the way.**

## Performance

- **Duration:** 95 min
- **Tasks:** 3
- **Files modified:** 8 (6 new, 2 modified)

## Accomplishments

- **Task 1 — Structured concurrency (`runner/scheduler.py`):** Completed the runner with a per-node `asyncio.Semaphore` sized from `config.max_concurrency` (D-09, refused below 1 at pre-flight validation, never a process-wide cap per D-11), sorted-by-node-id ready-batch dispatch stable across repeated runs, and D-08's named placement refusal via `validator.execution_mode.host()`. Closed both of 01-04's inherited gaps: node dispatch now goes through `parts.registry.dispatch()` (a declaration-only Part refuses explicitly instead of silently passing inputs through), and every node's `ctx.stores` is now a `_ScopedStoresView` wrapping `parts_core.CapabilityScopedStores` (deny-by-default, keyed by the node's own declared effects) while preserving existing dict-subscript bodies. Fixed a real bug along the way: cyclic wirings previously let `graphlib.CycleError` propagate uncaught past the runner once 01-03's SCC-based `effective_depth` stopped raising for cycles — the runner now reads `parsed.report.cycles` directly and returns `{"cycle": [...]}` as data. 10 new tests, all passing.
- **Task 2 — Budget metering (`runner/budget.py`, new):** Implemented CONTRACT §9's budget as a splittable capability token: `split_allowance()` (exact floor-division fan-out split, remainder to the lexicographically-first branch id, stated as the tie-break), `realised_share()` (spent/allowance computed at report time only, never fed back into an allocation), `meter()` (spend recorded only at a node's own declared `calls_llm`/`calls_rerank`/`calls_embedding` boundary, never a downstream consumer's), and `apportion()`/`ApportionmentPolicy` (merge-side apportionment declared at the apportioning node per the D4 repair, carried as an ordinary field on that node's own config so `config_hash` covers it automatically). 10 new tests, all passing.
- **Task 3 — Full run record + data guards (`runner/trace.py`, `runner/guards.py` new):** Added `RunRecord.__post_init__`'s honesty invariant, refusing to construct a confounded run record — grounded directly in RIG §TR.3's "required-together set" wording and the frozen schema's `allOf` clause, which together resolve the plan's own three-condition action text into one consistent required-together check (partial and degraded now travel together, since either alone already demands both reason fields under the schema). The field set was already schema-complete from earlier plans (14 per-node / 15 run-level fields matching `rig-trace.schema.json` exactly) — no field-shape changes were needed. New `guards.py` implements CONTRACT §19.8's declared data guards: `declare_guard()` refuses a missing/invalid granularity naming both admissible values, `evaluate_guards()` returns exactly the guards that fired (never absent, empty list when none fired). 12 new tests, all passing, validated against `rig-trace.schema.json` via the `assert_valid_trace` fixture.
- Full suite: 162/162 tests pass (130 pre-existing + 32 new). `ruff check` clean on every file this plan touched. The plan's own `<verification>` block is satisfied: `tests/runner/` is green (32/32), the tracer test is unmodified and passing (7/7), and every emitted run record validates against the frozen schema.

## Task Commits

1. **Task 1:** `da1d061` — feat(01-08): structured concurrency, per-node semaphore, D-08 placement refusal
2. **Task 2:** `285a5a7` — feat(01-08): budget metering at each node's declared boundary
3. **Task 3:** `6df1eb2` — feat(01-08): full RIG §TR.1 run record + declared data guards

**Plan metadata:** (this commit) `docs(01-08): complete runner completion plan`

## Files Created/Modified

- `databasise/runner/scheduler.py` — completed: `_ScopedStoresView`, `_node_semaphore`/`_validated_max_concurrency`, `WiringRefusedError`, `InvalidMaxConcurrencyError`, `NodeExecutionError`, `NodePlacementRefusedError`; `run_wiring()` and `_run_node()` rewritten
- `databasise/runner/budget.py` (new) — `Allowance`, `BudgetToken`, `ApportionmentPolicy`, `BudgetHalted`, `split_allowance()`, `realised_share()`, `apportion()`, `meter()`
- `databasise/runner/trace.py` — `RunRecord.__post_init__` (new, the honesty invariant); module docstring extended
- `databasise/runner/guards.py` (new) — `GuardGranularity`, `GuardDeclaration`, `GuardDeclarationError`, `declare_guard()`, `evaluate_guards()`
- `databasise/tests/runner/__init__.py` (new)
- `databasise/tests/runner/test_scheduler.py` (new) — 10 tests
- `databasise/tests/runner/test_budget.py` (new) — 10 tests
- `databasise/tests/runner/test_run_record.py` (new) — 12 tests

## Decisions Made

- **execution_mode source swap** — see key-decisions above; scheduler.py now imports from `validator.execution_mode`, not `validator.depth`.
- **Cycle detection via `parsed.report.cycles`, not `graphlib.CycleError`** — see key-decisions above; this closes a real gap left when 01-03's SCC-based depth computation stopped raising for cyclic input.
- **Partial-outcome vs. pre-flight-refusal split** — see key-decisions above; grounded in CONTRACT §9's "MUST NOT be discarded" rule read as applying to any in-flight failure.
- **budget.py/guards.py left standalone this plan** — see key-decisions above; each task's own `<files>` list scopes the work this way.
- **Placement-refused node's `budget_state` stamped `"halted"`** — the schema's three-value `budget_state` enum (`within_budget`/`halted`/`degraded`) has no dedicated value for "never ran due to a placement refusal"; `"halted"` is the closest fit ("this node's execution did not complete"), and `cross_process_failure_cause` carries the real cause so the choice is never ambiguous in the trace.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cyclic wirings could raise `graphlib.CycleError` uncaught past the runner**
- **Found during:** Task 1, writing Test 10 (cycle as data)
- **Issue:** The tracer-era `run_wiring()` wrapped only `effective_depth()` in `try/except graphlib.CycleError`, but 01-03's SCC-condensation-based `effective_depth` no longer raises for cyclic input — the `except` clause had been dead code since 01-03 landed. `_resolve_identities()`'s own separate `TopologicalSorter(...).static_order()` call still raised for a genuine cycle, and nothing caught it, so a cyclic wiring's exception would propagate straight past the runner rather than returning `{"cycle": [...]}` as data (CONTRACT §1: cyclic wirings are legal content).
- **Fix:** `run_wiring()` now checks `parsed.report.cycles` (already computed once by `validator.parse.parse_wiring`, independent of dispatch) before touching identity resolution at all, returning `{"cycle": [...]}` immediately when non-empty.
- **Files modified:** `databasise/runner/scheduler.py`
- **Verification:** `tests/runner/test_scheduler.py::test_10_a_cyclic_wiring_returns_the_cycle_as_data_rather_than_raising`; full suite green.
- **Committed in:** `da1d061`

---

**Total deviations:** 1 auto-fixed (1 bug fix). No architectural decision was changed; no scope creep.

## Known Gaps (deferred, out of this plan's scope)

- **`runner/budget.py` and `runner/guards.py` are not yet wired into `runner/scheduler.py`'s live dispatch path.** Both are standalone, fully tested modules — `scheduler.py`'s `NodeTrace` construction still hardcodes `budget_state="within_budget"`, `realised_budget_share=1.0`, `guards_fired=[]` for every successfully-completed node, same as the pre-existing tracer placeholders. Each task's own `<files>` list in `01-08-PLAN.md` scopes this plan's `scheduler.py` edits to Task 1 only (Tasks 2 and 3 list only their own new module + test file), so wiring `budget.meter()`/`guards.evaluate_guards()` into `_run_node()`'s dispatch — reading a new `config.budget_tokens`/`config.guards` wiring field — is left to a later plan or the orchestrator.
- **`databasise/__init__.py`'s public composer does not yet thread `scheduler.run_wiring()`'s `partial`/`stop_reason`/`degraded`/`degradation_reason` return-dict keys into the `RunRecord` it constructs** — it still hardcodes all four to their clean-run defaults. `run_wiring()` now returns these keys (added this plan, for `scheduler.py`'s own new partial-outcome paths — placement refusal, batch-internal node failure), but `databasise/__init__.py` is not in this plan's `files_modified` and was left untouched per the parallel-execution lane boundary. A later plan should read these keys through into the composer's `RunRecord(...)` call.
- **A placement-refused node's `budget_state` is stamped `"halted"`** as the closest fit among the schema's three enum values — see "Decisions Made" above. Not a claim that a token/step budget was specifically exceeded; `cross_process_failure_cause` names the real cause.

## Known Stubs

None beyond the "Known Gaps" integration points above, which are documented deferrals rather than unintentional stubs — every module this plan built is a complete, tested, standalone deliverable per its own `<files>` scope.

## Issues Encountered

None beyond the one deviation documented above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

The runner now has D-09's per-node semaphore, D-08's named placement refusals, both of 01-04's inherited gaps closed, a real cyclic-wiring bug fixed, exact-arithmetic budget metering, declared data guards, and a run record whose constructor refuses to serialise a confounded run as clean — the full instrument set MACH-05/D-10 require for the Phase 2 gate to read. The one open integration point (wiring `budget.py`/`guards.py` into the live dispatch path, and threading `scheduler.run_wiring()`'s partial-outcome keys into `databasise/__init__.py`'s composer) is documented above for whichever plan next touches those two files.

Note for the orchestrator: this plan's frontmatter lists `requirements: [MACH-05]`, also listed by other plans in this phase; per this phase's shared context, do not mark it complete in `REQUIREMENTS.md` until its last contributing plan lands — the orchestrator closes it at phase end. `requirements-completed` above is left empty for the same reason.

---
*Phase: 01-machine-core*
*Completed: 2026-08-30*

## Self-Check: PASSED

All 8 claimed files found on disk; commits `da1d061`, `285a5a7`, `6df1eb2` confirmed in `git log --oneline --all`.
