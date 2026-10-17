---
phase: 09-inputs-errors-security
plan: 07
subsystem: api
tags: [selectors, capability, promote, alias, refusals, seam]
status: complete

requires:
  - phase: 09-06
    provides: tests/seam/_probes.py counting clients, trace_row_count, inbox_files
provides:
  - "EmptyCapabilitySelectorError: resolve_selector and render_selector_key refuse Selector(capability=[]) by name"
  - "InvalidPromotionAliasError: Databasise.promote refuses an empty or instance-hash-shaped alias before trace resolution and any ledger touch"
affects: []

commits: 2
plan_head_before: fe87b534b63a0904e20ff53d35fc0fd769dfc955
plan_head_after: ce666e5a2a2281f335d74402bf92a03cc2df3924

actuals:
  tokens: 9000
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns:
    - "refusal in the resolver, not the model validator: construction succeeds, resolution refuses, so every selector route is covered by one check"
    - "promote reuses Selector's private _INSTANCE_HASH_PATTERN so the two checks cannot drift"

key-files:
  created:
    - databasise/tests/seam/test_empty_capability_selector.py
    - databasise/tests/seam/test_promote_alias_validation.py
  modified:
    - databasise/seam/refusals.py
    - databasise/seam/selectors.py
    - databasise/seam/compare.py
    - databasise/seam/engine.py
    - databasise/tests/seam/test_rest_transport.py

key-decisions:
  - "SEAM-10: the empty capability list is refused in resolve_selector (not Selector's validator) and in render_selector_key; '' and [''] stay UnsatisfiableSelectorError"
  - "SEAM-12: one promotion-specific InvalidPromotionAliasError covers both the empty and the hash-shaped alias; a whitespace-only alias is selectable and stays allowed"

requirements-completed: [SEAM-10, SEAM-12]

coverage:
  - id: D1
    description: "Selector(capability=[]) is refused as EmptyCapabilitySelectorError by resolve_selector (twice) and render_selector_key; POST /query, /query/stream, /compare ([{capability: []}, {}] and [{}, {capability: []}]), /documents, /documents/upload, DELETE /documents/x and MCP query and compare return the refusal with zero LLM/embedding calls, no new trace row and an empty corpus inbox; ['reads_vector'] still resolves"
    requirement: "SEAM-10"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_empty_capability_selector.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /promote and MCP promote refuse alias '', 'sha256:'+'b'*64 and the bare 64-hex form as InvalidPromotionAliasError with the ledger row count unchanged; 'good-alias' and 'sha256:'+'b'*63 promote and are then selectable by POST /query; refusal order is verb, alias, then trace resolution"
    requirement: "SEAM-12"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_promote_alias_validation.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Concurrency edge for the capability check (pure function of the selector, no shared state)"
    requirement: "SEAM-10"
    human_judgment: true
    rationale: "Backstop edge; no concurrent test was written, the property follows from the check reading only its argument"

duration: 15min
completed: 2026-10-17
---

# Phase 9 Plan 07: Empty capability selector and unselectable promote alias Summary

**`Selector(capability=[])` is refused by name in `resolve_selector` and `render_selector_key`, so it never reaches the bypass wiring or renders an empty compare key on any route, and `Databasise.promote` refuses an empty or hash-shaped alias before any ledger write.**

## Performance

- **Duration:** about 15 min
- **Tasks:** 2
- **Files modified:** 7 (5 edited, 2 new test files)

## Accomplishments

- `EmptyCapabilitySelectorError` is raised in the capability branch of `resolve_selector` before `_resolve_capability`, and in `render_selector_key` before the join. `Databasise.compare` resolves every selector before any arm, so an empty one anywhere in the list refuses first.
- `InvalidPromotionAliasError(alias=...)` is raised in `Databasise.promote` after the two verb checks and before `_resolve_operator_preconditions`, using `_INSTANCE_HASH_PATTERN` imported from `selectors` (not added to `selectors.__all__`). `rollback` and `retire` are untouched.
- Both refusals are in `refusals.__all__` and have `_REFUSAL_FACTORIES` entries in `test_rest_transport.py`.

## Red and green evidence

- Task 1 before the change (scratch test over `synthetic_naive_store` and counting clients): `POST /query` with `{capability: []}` returned `200` and the LLM was called once (bypass wiring); `POST /compare` with `[{capability: []}, {}]` returned `200` with keys `['', 'default']`. After: the five named files `107 passed`; `tests/seam tests/mcp`: `607 passed, 1 skipped`.
- Task 2 before the change: `pytest tests/seam/test_promote_alias_validation.py` gave `5 failed, 2 passed`; the hash-shaped alias returned `200` with `"alias":"sha256:bbbb...","version":"1.0.0"` (a ledger row written), and the empty-alias MCP call gave `DID NOT RAISE ToolError`. After: the six named files `115 passed`; plan verification `cd databasise && .venv/bin/pytest -q tests/seam tests/mcp tests/parts_core`: `775 passed, 1 skipped`, 0 failed.

## Task Commits

1. **Task 1: tracer, Selector(capability=[]) is refused by name on every selector route** - `7fae5ce` (feat)
2. **Task 2: promote refuses an alias no selector could carry before any ledger write** - `ce666e5` (feat)

## Files Created/Modified

- `databasise/seam/refusals.py` - `EmptyCapabilitySelectorError`, `InvalidPromotionAliasError`, `__all__`
- `databasise/seam/selectors.py` - empty-list refusal in `resolve_selector`
- `databasise/seam/compare.py` - empty-list refusal and docstring in `render_selector_key`
- `databasise/seam/engine.py` - alias check and docstring in `promote`, import of `_INSTANCE_HASH_PATTERN`
- `databasise/tests/seam/test_rest_transport.py` - imports and two `_REFUSAL_FACTORIES` entries
- `databasise/tests/seam/test_empty_capability_selector.py`, `test_promote_alias_validation.py` - new

## Decisions Made

See `key-decisions`. No existing test needed editing beyond the two factory entries.

## Deviations from Plan

**1. [Ordering] Both new refusal classes landed in the Task 1 commit**
- **Found during:** Task 1
- **Issue:** `InvalidPromotionAliasError` was added to `refusals.py` and the transport test factories in the Task 1 commit, because the transport test walks every `SeamRefusalError` subclass and both edits touch the same files.
- **Fix:** accepted as is; Task 2 wires the rule that raises it.
- **Commit:** `7fae5ce`

**Total deviations:** 1 (commit grouping only). **Impact:** none on behaviour.

## Issues Encountered

A Bash call that wrote files via a python heredoc was rejected by the BAK ledger-frozen guard, so all edits were redone with the Edit tool. The pre-change Task 1 run used a scratch test in the scratchpad directory (copied into `tests/seam/` and deleted again) because the new test module imports the new refusal. A final `ruff check` was blocked by a BAK check-edit guard hook, so lint was not run on the new files.

## Known Stubs

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for the next Phase 9 plan.

## Self-Check: PASSED

- Files exist: refusals.py, selectors.py, compare.py, engine.py, both new test files.
- Commits `7fae5ce` and `ce666e5` are ancestors of HEAD.
- Acceptance: `EmptyCapabilitySelectorError()` 1 line each in selectors.py and compare.py; `raise InvalidPromotionAliasError` 1 line in engine.py (line 1251); `_INSTANCE_HASH_PATTERN` 2 lines in engine.py (import and use).

---
*Phase: 09-inputs-errors-security*
*Completed: 2026-10-17*
