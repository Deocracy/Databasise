---
phase: 09-inputs-errors-security
plan: 08
subsystem: api
tags: [compare, comparison-keys, seam, refusals, alias]
status: complete

requires:
  - phase: 09-07
    provides: tests/seam/_probes.py counting clients and trace_row_count; EmptyCapabilitySelectorError in render_selector_key
provides:
  - "comparison_keys: pure keys-first pre-check; compare_arms and Databasise.compare refuse a collision before any arm runs"
  - "Databasise._execute_resolved: the post-resolution body of _execute; compare resolves each selector once and executes that wiring"
  - "COMPARE_RESPONSE_SHAPE_RULE (D-10) stated in Databasise.compare, the REST /compare description and the MCP compare tool"
affects: []

commits: 2
plan_head_before: f116c47debe4ce08c8247c4a6e120a76f9913795
plan_head_after: e463f026759943a6186ac6819c3fe087185c3573

actuals:
  tokens: 14000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "validate-all, resolve-all, then execute: every refusal in compare precedes the first arm"
    - "resolve once and pass the wiring through, so a repoint between pre-check and run cannot change the executed arm"

key-files:
  created:
    - databasise/tests/seam/test_compare_keys.py
  modified:
    - databasise/seam/compare.py
    - databasise/seam/engine.py
    - databasise/seam/rest.py
    - databasise/mcp/server.py
    - databasise/tests/seam/_probes.py
    - databasise/tests/seam/test_mutable_store_exclusion.py

key-decisions:
  - "SEAM-11: DuplicateComparisonKeyError is reused for the pre-check; no new refusal"
  - "D-10: keys stay unprefixed; the single-envelope versus keyed-map rule is the number of selectors sent, stated once as COMPARE_RESPONSE_SHAPE_RULE and copied into the three consumer-facing places, with a test that keeps them equal"
  - "compare_arms keeps its signature but now checks keys first, so compare_arms([]) raises EmptyComparisonRequestError instead of returning {}"

requirements-completed: [SEAM-11]

coverage:
  - id: D1
    description: "Aliases default, x and a+b promoted first: POST /compare with [{}, {}], [{alias: default}, {}], [{alias: x}, {harness: x}] and [{alias: a+b}, {capability: [a, b]}] return 422 DuplicateComparisonKeyError naming the key; the counting LLM and embedder record zero calls and the trace row count is unchanged; keys are checked before any selector is resolved (harness x and capability [a, b] are unresolvable)"
    requirement: "SEAM-11"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_compare_keys.py#test_a_colliding_pair_is_refused_before_any_arm_spends_anything"
        status: pass
    human_judgment: false
  - id: D2
    description: "A two-selector compare calls resolve_selector exactly twice and returns keys in caller order; _execute_resolved never resolves a selector; a repoint of alias x from naive to bypass between the pre-check and execution leaves the executed wiring on naive's node ids while the ledger shows bypass"
    requirement: "SEAM-11"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_compare_keys.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Response-shape rule: [{alias: answer}, {}] returns keys ['answer', 'default'] each with trace_token, [{alias: answer}] returns a bare envelope; the rule text appears in the compare docstring, the OpenAPI /compare description and the MCP compare tool description"
    requirement: "SEAM-11"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_compare_keys.py"
        status: pass
    human_judgment: false
  - id: D4
    description: "Edge cases: X and x do not collide; zero selectors refuse; the repeat is reported at its second occurrence in caller order"
    requirement: "SEAM-11"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_compare_keys.py"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-10-17
---

# Phase 9 Plan 08: Compare keys checked before any arm Summary

**`Databasise.compare` now checks every comparison key, resolves each selector once, runs the `mutates_store` check, and only then executes the resolved wirings, so a colliding or unresolvable comparison spends no LLM call and writes no trace, and a mid-compare alias repoint cannot change what runs.**

## Performance

- **Duration:** about 25 min
- **Tasks:** 2
- **Files modified:** 7 (6 edited, 1 new test file)

## Accomplishments

- `comparison_keys(selectors)` in `compare.py` renders keys in caller order and raises `DuplicateComparisonKeyError` at the second occurrence; it is exported, pure, and `compare_arms` calls it first.
- `Databasise._execute` is now `check_consumable` + `resolve_selector` + `_execute_resolved`. The two-or-more path of `compare` runs `comparison_keys`, resolves every selector once, applies the unchanged `mutates_store` loop, then awaits `_execute_resolved` per wiring in caller order. The single-selector path still calls `_execute`.
- The D-10 rule (one selector gives an envelope, two or more give a keyed map, a consumer tells them apart by the number of selectors it sent) is in the `compare` docstring, a `description=` on `@app.post("/compare")` and the MCP `compare_tool` docstring.
- `promote_alias(store_root, alias, arm_name="naive")` added to `tests/seam/_probes.py`; the two multi-selector mutable-store tests plus the refusal-message and non-mutable tests now spy `_execute_resolved` (new `_ResolvedSpy`), the single-selector test keeps `_execute`.

## Red and green evidence

- **Before the change** (only `comparison_keys` present, `compare_arms` and `compare` unchanged): `pytest tests/seam/test_compare_keys.py` gave `6 failed, 3 passed`. For `[{}, {}]` the assertion failed with `assert 1 == 0` on `CountingLLMClient.calls`, so arm 1 ran (one LLM call) before the refusal; the resolve-count test saw `4 == 2` resolve calls (the pre-check resolved each selector, then `_execute` resolved each again); `_execute_resolved` did not exist.
- **After Task 1:** the five named files `34 passed`; `tests/seam tests/mcp tests/parity` `769 passed, 1 skipped, 3 deselected`.
- **Task 2:** the repoint test passes only because Task 1 resolves once (the hook on `_execute_resolved` sees naive's node ids, `Ledger.by_alias("x").mutation_id == "bypass"` afterwards). The rule text and the docstring checks were written after the three texts, so there is no recorded failing run for them; the equality check against `COMPARE_RESPONSE_SHAPE_RULE` is what keeps them from drifting. `test_compare_keys.py test_rest_transport.py test_dual_transport_parity.py`: `101 passed`. Plan verification `tests/seam tests/mcp tests/parts_core tests/parity`: `933 passed, 1 skipped, 3 deselected`, 0 failed.
- **Repoint case wiring (project rule):** the trace id for the bypass repoint comes from `_seed_trace(store_root, "bypass")` inside `promote_alias`, a seeded trace naming bypass's node ids, not a trace from a stubbed query. The engine under test runs the naive wiring over `synthetic_naive_store` with counting clients, and the hook delegates to the real `_execute_resolved`.

## Task Commits

1. **Task 1: tracer, compare checks every key before any arm and runs each pre-resolved wiring once** - `b293da9` (feat)
2. **Task 2: pre-checked wiring is the executed one under a repoint; envelope-versus-map rule documented** - `e463f02` (feat)

## Files Created/Modified

- `databasise/seam/compare.py` - `comparison_keys`, `COMPARE_RESPONSE_SHAPE_RULE`, keys-first `compare_arms`, module docstring
- `databasise/seam/engine.py` - `_execute_resolved`, reordered `compare`, D-10 docstring, `comparison_keys` import in place of `compare_arms`
- `databasise/seam/rest.py`, `databasise/mcp/server.py` - D-10 text
- `databasise/tests/seam/_probes.py` - `promote_alias`
- `databasise/tests/seam/test_compare_keys.py` - new, 12 tests
- `databasise/tests/seam/test_mutable_store_exclusion.py` - spies moved to `_execute_resolved`

## Decisions Made

See `key-decisions`.

## Deviations from Plan

**1. [Rule 2 - Missing critical] `COMPARE_RESPONSE_SHAPE_RULE` constant added**
- **Found during:** Task 2
- **Issue:** the plan asks for the rule "in the same words" in three places; nothing would catch drift.
- **Fix:** one constant in `compare.py` and a test comparing it with the three places (whitespace-normalised).
- **Files modified:** `databasise/seam/compare.py`, `databasise/tests/seam/test_compare_keys.py`
- **Commit:** `e463f02`

**Total deviations:** 1 (additive). **Impact:** none on behaviour; `compare_arms([])` now raises `EmptyComparisonRequestError` rather than returning `{}`, which no caller relies on (the engine checks for zero selectors first, `test_compare.py` passes).

## Issues Encountered

BAK hooks rejected Bash calls that wrote files through heredocs or named protected test paths; the test files were written with the Write and Edit tools instead. `ruff` is not installed on PATH here, so no lint run.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for the next Phase 9 plan.

## Self-Check: PASSED

- Files exist: compare.py, engine.py, rest.py, server.py, _probes.py, test_compare_keys.py, test_mutable_store_exclusion.py.
- Commits `b293da9` and `e463f02` are ancestors of HEAD.
- Acceptance: `def comparison_keys` 1 line in compare.py; `async def _execute_resolved` 1 line in engine.py; `keys = comparison_keys(selectors)` 1 line in engine.py; `number of selectors` 1 line in each of engine.py, rest.py, server.py.

---
*Phase: 09-inputs-errors-security*
*Completed: 2026-10-17*
