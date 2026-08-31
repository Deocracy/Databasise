---
phase: 01-machine-core
plan: 10
subsystem: runner
tags: [budget-metering, data-guards, cr-01, blast-radius, ast-invariant, tdd]

# Dependency graph
requires:
  - phase: 01-machine-core (01-08)
    provides: runner/scheduler.py's live dispatch loop, structured-concurrency batching, honesty
      run-record fields
  - phase: 01-machine-core (01-09)
    provides: runner/budget.py's meter()/realised_share()/split_allowance()/apportion(),
      runner/guards.py's declare_guard()/evaluate_guards() (both previously standalone, unwired)
provides:
  - runner/budget.py and runner/guards.py wired into scheduler.py's live dispatch path
  - config.token_allowance and config.guards as ordinary wiring-config fields, covered by
    config_hash for free
  - a budget-halted node reaches databasise.run_wiring as a traced partial/degraded record with
    stop_reason="budget_halt", never a clean record and never a raised exception
  - a regression test proving the blast-radius rule is registry-sourced against an
    effects-omitting wiring node
  - an AST-based structural pin (tests/test_trusted_source_invariant.py) proving no enforcement
    path in runner/scheduler.py or validator/blast_radius.py reads a wiring node's effects/kind
affects: [phase-02-falsifiers, phase-02-gate]

actuals:
  tokens: 12300
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "AST-based structural invariant test (mirrors tools/check_import_boundary.py's precedent) to
      pin a trust-boundary sourcing rule against silent regression, rather than leaving it as
      prose"
    - "Temporary-revert-observe-restore verification for tests covering already-correct source
      (blast_radius.py, the trusted-source invariant) — reverts the real module, observes RED,
      restores with a clean git diff, all inside one execution session"

key-files:
  created:
    - databasise/tests/runner/test_live_metering.py
    - databasise/tests/test_trusted_source_invariant.py
  modified:
    - databasise/runner/scheduler.py
    - databasise/__init__.py
    - databasise/parts_core/fake_llm_caller.py
    - databasise/tests/parts/test_reference_parts.py
    - databasise/tests/test_phase_success_criteria.py
    - databasise/tests/validator/test_blast_radius.py

key-decisions:
  - "DEC-A/DEC-B honored verbatim: config.token_allowance is an ordinary field on a node's own
    wiring config, defaulting to DEFAULT_TOKEN_ALLOWANCE=0 when absent (a branch cannot spend
    what it was not handed, CONTRACT §9)."
  - "DEC-C honored: metering happens once, post-hoc, at each node's declared boundary after its
    body returns — never pre-authorising internal calls."
  - "DEC-D honored: the CR-01 kind-vs-effects narrowing (effects only, not kind) is accepted and
    now pinned by an AST-based structural test rather than left as prose."
  - "Rule 3 auto-fix: FAKE_LLM_CALLER_PART's effects declaration was missing writes_kv, which its
    body needs for ctx.stores[\"kv\"] cache access under the runner's CR-01 scoped-store view. This
    Part had never been dispatched through the live scheduler before Task 1 first did so; the gap
    was invisible until then. Fixed by adding writes_kv to the Part's declared effects and updating
    the one existing test that asserted the old effects list literally."

patterns-established:
  - "A new calling-effect Part (calls_llm/calls_rerank/calls_embedding) that also touches a store
    must declare the matching store effect (reads_kv/writes_kv/...) for the CR-01 scoped-store
    view to grant it access — declaring only the calling effect is not sufficient even if the body
    only uses the store for its own caching."

requirements-completed: [MACH-05, MACH-08]

coverage:
  - id: D1
    description: "Real metering end to end: a metered node's trace carries its body's own
      TokenAccounting, real cache_hit, computed budget_state and realised_budget_share, sourced
      from the registry's Part.effects (never the wiring's under-declared effects)."
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/runner/test_live_metering.py (12 tests)"
        status: pass
      - kind: integration
        ref: "databasise/tests/test_phase_success_criteria.py::test_criterion_2_the_runner_executes_to_completion_with_metered_spend"
        status: pass
    human_judgment: false
  - id: D2
    description: "A budget-halted node reaches databasise.run_wiring as a traced partial/degraded
      record with stop_reason=\"budget_halt\", never a clean record and never a raised exception."
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/runner/test_live_metering.py::test_metered_node_over_allowance_halts_and_the_record_is_a_traced_budget_halt_partial_run"
        status: pass
    human_judgment: false
  - id: D3
    description: "The blast-radius rule refuses an under-declaring wiring node (effects omitted)
      whose resolved Part still declares a shared artifact write at a non-stage depth, proven
      through the real parse_wiring path; and no enforcement path reads a wiring node's
      effects/kind, proven structurally by AST inspection."
    requirement: "MACH-08"
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_blast_radius.py::test_under_declaring_wiring_cannot_route_a_shared_artifact_write_around_the_rule"
        status: pass
      - kind: unit
        ref: "databasise/tests/test_trusted_source_invariant.py::test_no_scanned_module_reads_a_wiring_nodes_effects_or_kind"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-08-31
status: complete
---

# Phase 1 Plan 10: Live Metering + Blast-Radius Structural Pin Summary

**Wired `runner/budget.py`'s `meter()` and `runner/guards.py`'s `evaluate_guards()` into `runner/scheduler.py`'s live dispatch path — closing both BLOCKER gaps from `01-VERIFICATION.md` (real metered spend sourced from the registry's `Part.effects`, and the one missing blast-radius regression test) so Phase 2's Falsifier 2 / Falsifier 5 gate can open.**

## Performance

- **Duration:** 55 min
- **Tasks:** 3
- **Files modified:** 8 (2 created, 6 modified)
- **Commits:** 5

## Accomplishments

- A metered node's trace now carries its own body's real `TokenAccounting`, real `cache_hit`
  (a genuine second-call cache hit against the run's own KV store), and computed `budget_state`
  / `realised_budget_share` — never the scheduler's previous hardcoded `within_budget`/`1.0`/
  all-zero-tokens literals.
- `meter()` is handed `parsed.parts[node_id].effects` (the registry's own resolved declaration),
  never `parsed.nodes[node_id].effects` — an under-declaring wiring node cannot meter a real LLM
  spend as zero (CR-01's trusted-source rule applied to the metering path).
- A node whose realised spend exceeds its `config.token_allowance` halts, and the run is returned
  through the public `databasise.run_wiring` seam as a traced `partial=True`/`degraded=True`/
  `stop_reason="budget_halt"` record — never a clean record, never a raised exception.
- `config.guards` is validated pre-flight via `declare_guard` (refusing an inadmissible
  granularity before any node dispatches) and evaluated post-dispatch via `evaluate_guards`,
  stamping `NodeTrace.guards_fired` in declaration order.
- The full metering edge battery (boundary, adjacency, empty, ordering, precision, guard refusal)
  named in this plan's `must_haves.truths` is each pinned by a named test, and ROADMAP Success
  Criterion 2's own acceptance test now asserts real metered spend on a real metered node instead
  of a constant that any hardcoded value would satisfy.
- The blast-radius rule's third missing regression test (an under-declaring wiring node whose
  resolved Part still declares a shared artifact write at a non-stage depth) now exists, proven
  through the real `parse_wiring` path.
- A new AST-based structural test (`tests/test_trusted_source_invariant.py`) pins the claim that
  no enforcement path in `runner/scheduler.py` or `validator/blast_radius.py` reads a wiring
  node's `effects`/`kind` — the exact failure class that let the `resumable` residual survive the
  first CR-01 fix pass until a later manual inspection caught it.

## Task Commits

Each task was committed atomically (Task 1 followed the RED/GREEN TDD gate; Task 2's edge battery
passed immediately against Task 1's already-general implementation, so it has a single commit;
Task 3 is test-only and has a single commit):

1. **Rule 3 fix (prerequisite to Task 1):** `883d14a` (fix) — `FAKE_LLM_CALLER_PART` declares
   `writes_kv` for its own scoped store access.
2. **Task 1 RED:** `b3272a2` (test) — failing test for live metering through the public seam.
3. **Task 1 GREEN:** `852d2b3` (feat) — wire `runner/budget.py` and `runner/guards.py` into the
   live dispatch path.
4. **Task 2:** `eb98cac` (test) — the metering edge battery, and criterion 2 told the truth.
5. **Task 3:** `4905335` (test) — Gap 1 residual: under-declaring blast-radius refusal, plus a
   structural pin.

## Files Created/Modified

- `databasise/runner/scheduler.py` — `DEFAULT_TOKEN_ALLOWANCE`, `InvalidTokenAllowanceError`,
  `_validated_token_allowance`, `_validated_guards`, `_body_report` added; the successful-dispatch
  `NodeTrace` stamp now computes every field it previously hardcoded; `budget_halted` local
  extends the end-of-batch break condition.
- `databasise/__init__.py` — `RunRecord(...)` now threads `partial`/`degraded`/`stop_reason`/
  `degradation_reason` from the scheduler's result.
- `databasise/parts_core/fake_llm_caller.py` — `FAKE_LLM_CALLER_PART.effects` gains `writes_kv`
  (Rule 3 fix; see Deviations below).
- `databasise/tests/parts/test_reference_parts.py` — updated the one assertion on
  `FAKE_LLM_CALLER_PART.effects`'s literal list to match.
- `databasise/tests/runner/test_live_metering.py` (new) — Task 1's 6 end-to-end tests plus Task
  2's 6 edge-battery tests, 12 total.
- `databasise/tests/test_phase_success_criteria.py` — `_transparent_wiring`/
  `_transparent_registry` gain an independent `llm-caller` node; `test_criterion_2_...` now
  distinguishes metered from unmetered nodes instead of asserting a shared constant.
- `databasise/tests/validator/test_blast_radius.py` — 2 new tests (the under-declaring-wiring
  refusal and its discriminating `stage`-depth sibling), going through `parse_wiring` end to end
  rather than constructing a `ParsedWiring` directly.
- `databasise/tests/test_trusted_source_invariant.py` (new) — the AST-based structural pin, 2
  tests.

## Decisions Made

- DEC-A, DEC-B, DEC-C, DEC-D from the plan's own `<decisions_recorded_here>` were followed
  verbatim — none were revisited or reversed.
- No new architectural decisions were required beyond the plan's own; the one genuine discovery
  (`FAKE_LLM_CALLER_PART`'s missing `writes_kv` declaration) is a Rule 3 auto-fix, not a design
  decision.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `FAKE_LLM_CALLER_PART` was missing the store effect its own body needs**

- **Found during:** Task 1, first attempt to run `FAKE_LLM_CALLER_PART` end to end through
  `databasise.run_wiring` (this Part had never been dispatched through the live scheduler before —
  only invoked as a bare body against a raw, unscoped `stores` dict in
  `tests/parts/test_reference_parts.py` and `tests/runner/test_run_record.py`).
- **Issue:** The Part's body reads and writes `ctx.stores["kv"]` for its own cache round trip, but
  the Part declared `effects=["calls_llm"]` alone. Under the runner's CR-01 scoped-store view
  (`_ScopedStoresView`, built from the registry's own `Part.effects`), `ctx.stores["kv"]` only
  resolves when a declared effect's suffix is `"kv"`. With no such effect declared, every dispatch
  raised `UndeclaredEffectError`, which the scheduler wraps as a `NodeExecutionError` — surfacing
  as an unrelated node-failure trace (`budget_state="halted"` via the failure path, not the
  metering path) rather than exercising the metering logic Task 1 exists to test.
- **Fix:** Added `writes_kv` to `FAKE_LLM_CALLER_PART.effects` (chosen over `reads_kv` because the
  body also unconditionally `upsert`s the cache entry). Documented the discovery path in the
  Part's own module docstring.
- **Files modified:** `databasise/parts_core/fake_llm_caller.py`,
  `databasise/tests/parts/test_reference_parts.py` (one existing assertion on the literal effects
  list updated to match).
- **Verification:** Full suite green before and after (baseline 217, unaffected outside the two
  touched files); `writes_kv` does not affect `execution_mode` derivation (not in
  `_NOT_IN_PROCESS_EFFECTS`), does not affect the blast-radius rule (keys only on
  `writes_artifact`), and correctly makes the Part's `resumable` computation `False` (it does
  mutate a store), which is the honest value.
- **Committed in:** `883d14a` (its own commit, separate from Task 1's RED/GREEN pair, since it is
  a prerequisite fix rather than part of either).

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking)
**Impact on plan:** Necessary for Task 1's own required behavior (a genuine end-to-end cache hit
through `databasise.run_wiring`) to be achievable at all via the documented public seam. No scope
creep beyond the two files this fix required.

## Issues Encountered

None beyond the deviation above. The `databasise/.venv` referenced by this plan's `<verification>`
section lives in the main checkout, not this worktree; all commands were run with
`PYTHONPATH=<worktree-root>` prepended so the main checkout's interpreter resolved the worktree's
own (modified) `databasise` package rather than the main checkout's installed copy.

## Fail-Without-Fix / Pass-With-Fix Observations (plan `<output>` requirement)

- **Task 1/2 (scheduler stamp block):** all 6 Task 1 tests observed FAILING against the pre-fix
  tree (5 on the metering assertions, plus one AttributeError-class failure that was actually an
  unrelated `UndeclaredEffectError` from the Rule 3 gap — resolved before re-observing RED on the
  intended metering gap alone). After the GREEN implementation, all 6 passed; the full suite
  (223 tests including the new file) was green except the one criterion-2 exception this plan's
  own acceptance criteria names, which Task 2 then corrected.
- **Task 2 (`test_criterion_2_...`):** temporarily reverted the Task 1 stamp block back to literal
  `budget_state="within_budget"`/`realised_budget_share=1.0`; observed the corrected test fail
  (`assert 1.0 == 0.0` on the first unmetered node); restored (clean `git diff`); re-confirmed the
  full suite green (229 passed).
- **Task 3 (blast-radius regression):** temporarily reverted `blast_radius_violations` to iterate
  `parsed.nodes.items()` and gate on the wiring node's own `effects` instead of
  `parsed.parts.items()`/`part.effects`; observed the new test fail
  (`report.ok` wrongly `True`); restored (clean `git diff`).
- **Task 3 (trusted-source invariant):** temporarily reintroduced a single `node.effects` read
  into `_run_node`'s `execution_mode` derivation (`derive_execution_mode(node.effects, part.kind)`
  in place of `part.effects`); observed the AST-based test fail, correctly flagging
  `runner/scheduler.py` line 339 (`node.effects (bound from parsed.nodes[...])`); restored (clean
  `git diff`).
- **Non-vacuity of the AST check:** confirmed the check passes on the current (correct) tree
  despite both scanned modules' docstrings containing the exact prose `parsed.nodes[node_id]
  .effects` — proving the AST walk distinguishes real attribute access from documentation
  describing the rule, rather than false-positiving on prose.

## Final Test Count Against the 217 Baseline

`cd databasise && .venv/bin/python -m pytest tests/ -q` (run via `PYTHONPATH=<worktree-root>`,
main checkout's `.venv`): **233 passed** = 217 baseline (`01-REVIEW-FIX.md`'s own count) + 16 new
tests across this plan's three tasks (6 in Task 1's section of `test_live_metering.py`, 6 in
Task 2's section, 2 in `test_blast_radius.py`, 2 in `test_trusted_source_invariant.py`).
`check_import_boundary` exits 0.

## DEC-B's Observed Blast Radius

No existing test's behavior changed as a result of `DEFAULT_TOKEN_ALLOWANCE=0`: `meter()` already
implemented the `spent <= allowance` comparison (unchanged by this plan), and every node in every
pre-existing test declares none of `calls_llm`/`calls_rerank`/`calls_embedding`, so every one
already accrued spend 0 and stayed `within_budget` against any allowance including 0. The only
behavior change from wiring metering into the live path is that `FAKE_LLM_CALLER_PART` (the sole
`calls_llm` Part) is now, for the first time, actually meterable when run through
`databasise.run_wiring` — and it was never wired through `run_wiring` in any pre-existing test, so
this plan's own new tests are the first and only exercise of that path.

## Confirmation: `01-01-PLAN.md` … `01-09-PLAN.md` Were Not Modified

`git diff <worktree-base>..HEAD --stat` shows exactly 8 files changed, all under
`databasise/runner/`, `databasise/`, `databasise/parts_core/`, and `databasise/tests/`. No file
under `.planning/phases/01-machine-core/01-0[1-9]-PLAN.md` appears in the diff.

## Next Phase Readiness

Both `01-VERIFICATION.md` BLOCKER gaps are closed: Gap 2 (MACH-05, real metering on the live path)
by Tasks 1-2, and Gap 1's third `missing:` bullet (MACH-08, the under-declaring blast-radius
regression test) by Task 3. Phase 1 → Phase 2's gate condition (Falsifiers 2 and 5 passing) has no
outstanding blocker from this plan's scope. `01-VERIFICATION.md` re-verification is the
orchestrator's next step, not this plan's.

---

*Phase: 01-machine-core*
*Completed: 2026-08-31*

## Self-Check: PASSED

- FOUND: `databasise/tests/runner/test_live_metering.py`
- FOUND: `databasise/tests/test_trusted_source_invariant.py`
- FOUND: `.planning/phases/01-machine-core/01-10-SUMMARY.md`
- FOUND commit: `883d14a` (fix)
- FOUND commit: `b3272a2` (test, RED)
- FOUND commit: `852d2b3` (feat, GREEN)
- FOUND commit: `eb98cac` (test)
- FOUND commit: `4905335` (test)
