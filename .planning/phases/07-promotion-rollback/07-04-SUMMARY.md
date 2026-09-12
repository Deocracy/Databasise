---
phase: 07-promotion-rollback
plan: 04
subsystem: api
tags: [seam, refusals, promotion, rest, mcp, pydantic, fastapi, tdd]

# Dependency graph
requires:
  - phase: 07-promotion-rollback
    provides: promote()/rollback()/retire() over the append-only ledger, three-transport parity (07-01, 07-02, 07-03)
provides:
  - UnrecognisedPromotionVerbError, a named SeamRefusalError subclass for any promote() verb outside the six declared PromotionVerb literals
  - PROMOTION_VERBS, the runtime accepted-verb set derived from typing.get_args(PromotionVerb)
  - a verb guard as the first statement in Databasise.promote(), running before the not-built check and before any trace-id resolution
  - three-transport proof that the identical refusal name surfaces in-process, over REST (422), and over MCP (ToolError)
affects: [07-promotion-rollback, gsd-verify-work, gsd-ship]

# Actuals (#2632)
actuals:
  tokens: 5605
  tasks: 2
  commits: 5
plan_head_before: ad0a1596e524ba442fb732f4acab990dc4b5f460

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Runtime enum guard derived from typing.get_args() rather than a hand-restated literal list, so a future enum member cannot drift the guard out of sync"
    - "Refusal DTOs stay deserialization-only (verb: str, no Literal/field_validator) so the named engine-level SeamRefusalError is the sole mechanism and every transport carries the identical refusal_type"

key-files:
  created: []
  modified:
    - databasise/seam/refusals.py
    - databasise/seam/promotion.py
    - databasise/seam/engine.py
    - databasise/seam/rest.py
    - databasise/mcp/tools.py
    - databasise/tests/seam/test_promotion_posture.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/seam/test_dual_transport.py
    - databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md

key-decisions:
  - "Kept PromoteRequest.verb/PromoteToolArgs.verb as plain str with no Literal/field_validator, per the plan's own rejected-alternative analysis: routing through Pydantic validation would produce a 422 with no refusal_type key, making the verb the one refusal that differs by transport instead of the one refusal architecture this plan closes."
  - "Kept _promote_sync's terminal ValueError-raising branch as a named-refusal backstop rather than deleting it — unreachable by construction after the top-of-body guard, but it stops a future seventh PromotionVerb literal with no matching branch from falling through into a ledger append."

requirements-completed: [API-09]

coverage:
  - id: D1
    description: "An out-of-enum promote() verb (typo, case variant, separator variant, empty string, None, spaced variant) refuses with UnrecognisedPromotionVerbError before trace-id resolution runs, with zero ledger rows written"
    requirement: "API-09"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_promotion_posture.py#test_an_unrecognised_verb_refuses_by_name_before_any_trace_resolution"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_promotion_posture.py#test_the_verb_guard_reads_the_enum_rather_than_a_second_list"
        status: pass
    human_judgment: false
  - id: D2
    description: "The identical out-of-enum verb refuses under the identical refusal name on all three transports: in-process raise, REST 422 with refusal_type, MCP ToolError with refusal_type"
    requirement: "API-09"
    verification:
      - kind: integration
        ref: "databasise/tests/seam/test_dual_transport.py#test_an_out_of_enum_verb_refuses_identically_across_three_transports"
        status: pass
      - kind: integration
        ref: "databasise/tests/seam/test_rest_transport.py#test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value[UnrecognisedPromotionVerbError]"
        status: pass
    human_judgment: false
  - id: D3
    description: "The six declared PromotionVerb literals are unaffected by the guard (no regression) and PROMOTION_VERBS is derived from the enum, never a second hand-maintained list"
    requirement: "API-09"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_promotion_posture.py#test_no_gate_verb_appends_a_row"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_promotion_posture.py#test_operator_asserted_verb_still_appends"
        status: pass
    human_judgment: false

duration: ~21 min
completed: 2026-09-12
status: complete
---

# Phase 07 Plan 04: Named Verb-Refusal Gap Closure Summary

**Out-of-enum `promote()` verbs now refuse as `UnrecognisedPromotionVerbError` (checked before trace-id resolution) identically on in-process, REST (422/`refusal_type`), and MCP (`ToolError`/`refusal_type`), closing 07-VERIFICATION.md's sole gap and 07-REVIEW.md's CR-01.**

## Performance

- **Duration:** ~21 min
- **Started:** 2026-09-12T06:15:33Z
- **Completed:** 2026-09-12T06:36:21Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added `UnrecognisedPromotionVerbError(SeamRefusalError)` to `databasise/seam/refusals.py`, following `InvalidChangeOriginError`'s exact shape (keyword-only, `Any`-typed, no menu, no implied default).
- Added `PROMOTION_VERBS: frozenset[str] = frozenset(get_args(PromotionVerb))` to `databasise/seam/promotion.py` — the runtime guard's accepted set is derived from the enum, never restated.
- `Databasise.promote()`'s `verb` parameter is now annotated `PromotionVerb` (closing 07-01-PLAN.md's own outstanding Task 3 instruction), and the guard `if verb not in PROMOTION_VERBS: raise UnrecognisedPromotionVerbError(verb=verb)` runs as the very first statement in `promote()`'s body — above the not-built check, above trace-id resolution, above any ledger read.
- `_promote_sync`'s terminal fallback branch now raises the same named refusal instead of a bare `ValueError` (unreachable by construction post-guard, kept as a backstop against a future undeclared literal).
- Registered a `_REFUSAL_FACTORIES` entry in `test_rest_transport.py` so the module's own exhaustiveness test (`SeamRefusalError.__subclasses__()` walk) covers the new class.
- Added `test_an_out_of_enum_verb_refuses_identically_across_three_transports` to `test_dual_transport.py`, mirroring `test_refusal_parity_across_three_transports`'s structure — one shared store root, one resolvable trace, one body driven at all three transports, asserting the identical `refusal_type` and zero ledger rows.
- Updated `PROMOTION-LEDGER-EVIDENCE.md`'s criterion 3 row and "Method and limits" section to cite both new node ids and record the CR-01 closure.

## Task Commits

Each task was committed atomically:

1. **Task 1: An out-of-enum verb refuses by name, end-to-end in-process, before anything resolves** (`tdd="true"`)
   - `86ca4b3` (test) — RED: failing tests added, confirmed genuinely RED via a temporary revert of the guard/terminal branch (six parametrized cases fail on a bare `ValueError`, not a collection error)
   - `214faff` (feat) — GREEN: refusal class, `PROMOTION_VERBS`, the guard, and the terminal-branch fix
2. **Task 2: The same refusal, the same name, on REST and MCP** - `844ccf5` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified

- `databasise/seam/refusals.py` - `UnrecognisedPromotionVerbError`, placed between `InvalidChangeOriginError` and `GateVerbNotBuiltError`
- `databasise/seam/promotion.py` - `PROMOTION_VERBS`, derived from `typing.get_args(PromotionVerb)`
- `databasise/seam/engine.py` - `promote()` signature annotated `PromotionVerb`; top-of-body guard; terminal-branch backstop fixed
- `databasise/seam/rest.py` - `PromoteRequest` docstring records the deliberate `verb: str` decision
- `databasise/mcp/tools.py` - `PromoteToolArgs` docstring mirrors the same decision
- `databasise/tests/seam/test_promotion_posture.py` - two new tests (refusal + drift guard)
- `databasise/tests/seam/test_rest_transport.py` - `_REFUSAL_FACTORIES` entry for the new class
- `databasise/tests/seam/test_dual_transport.py` - three-transport parity test for the new refusal
- `databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md` - criterion 3 row + "Method and limits" updated

## Decisions Made

- Kept `PromoteRequest.verb`/`PromoteToolArgs.verb` as plain `str` (no `Literal`, no `field_validator`) — the plan's own rejected-alternative analysis showed that constraining at the Pydantic layer produces a 422 with no `refusal_type` key, making the verb the one refusal in the system whose name differs per transport. The named-refusal-at-the-engine approach keeps one refusal, one mechanism, three transports.
- Cited one extras-gated test node id (`tests/seam/test_dual_transport.py::test_an_out_of_enum_verb_refuses_identically_across_three_transports`) in `PROMOTION-LEDGER-EVIDENCE.md`'s "Criteria" table for the first time, per the plan's explicit instruction — previously that table cited only extras-free tests. Updated the "Method and limits" section to name this one exception explicitly rather than leave the document's own stated design principle silently contradicted.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Evidence-doc node-id citation needed a specific parametrized case, not the bare function name**
- **Found during:** Task 2's verify step (`uv run pytest -q tests/evidence/test_promotion_ledger_record.py -x`)
- **Issue:** `test_promotion_ledger_record.py`'s own collectibility check asserts `"1 test collected"` per cited node id. `test_an_unrecognised_verb_refuses_by_name_before_any_trace_resolution` is parametrized over six cases, so citing the bare name collected 6 tests and failed the check.
- **Fix:** Cited the specific parametrized node id `tests/seam/test_promotion_posture.py::test_an_unrecognised_verb_refuses_by_name_before_any_trace_resolution[promote_next_typo]` in criterion 3's Tests cell instead.
- **Files modified:** `databasise/evidence/PROMOTION-LEDGER-EVIDENCE.md`
- **Verification:** `uv run pytest -q tests/evidence/test_promotion_ledger_record.py -x` → 7 passed
- **Committed in:** `844ccf5` (Task 2 commit)

### Documented Non-Blocking Deviation (no code fix required)

**Tracer feedback gate — expected, self-resolving cross-task test failure.** After Task 1's commits landed, re-running Task 1's own `<verify>` block surfaced one FAILED line in `uv run pytest -q tests/seam/ -x`: `test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value[UnrecognisedPromotionVerbError]`, because `test_rest_transport.py`'s own exhaustiveness test walks `SeamRefusalError.__subclasses__()` and hard-fails on any subclass lacking a registered `_REFUSAL_FACTORIES` entry — by the codebase's own explicit, intentional design (its own comment: "a refusal type was added without extending this test"). Registering that entry is Task 2's sole, explicit job, and Task 1's action text forbids touching `test_rest_transport.py`. Task 1's own named `<acceptance_criteria>` (verified individually and listed above) all passed; this single, structurally-unavoidable cross-task artifact was documented rather than treated as a genuine tracer failure, and execution proceeded directly to Task 2 in the same session, which resolved it (confirmed: full suite green afterward, 1063 passed / 1 skipped).

---

**Total deviations:** 1 auto-fixed (1 blocking — evidence-doc node-id specificity); 1 documented non-blocking (expected cross-task test-suite transition, resolved by Task 2 in the same session).
**Impact on plan:** No scope creep. Both are direct, foreseeable consequences of the plan's own two-task split around a codebase-enforced exhaustiveness test; neither required deviating from the plan's designed shape.

## Issues Encountered

- A concurrent, unrelated process committed twice to `main` (`d1ce730`, `775476b`, both `docs(melodyscribe): ...`) during this plan's execution window — confirmed via `git show --stat` to touch no file under `databasise/`. `actuals.commits: 5` in this SUMMARY's frontmatter is the raw `git rev-list --count` measurement between this plan's recorded `plan_head_before` and `HEAD`, per the mandated measurement protocol, and therefore includes those 2 unrelated commits alongside this plan's own 3 (`86ca4b3`, `214faff`, `844ccf5`).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- 07-VERIFICATION.md's sole gap (CR-01, the out-of-enum verb crash) is closed: full suite 1063 passed / 1 skipped (baseline 1054 passed / 1 skipped — no regression, no skip growth), `test_an_out_of_enum_verb_refuses_identically_across_three_transports` passes with both `rest`/`mcp` extras genuinely installed, and `check_import_boundary` passes clean.
- Phase 7's three ROADMAP success criteria now hold without qualification; API-09 is fully satisfied (previously "satisfied as literally worded" with a flagged robustness gap).
- No new architectural surface, no new dependency, no threat-model change: this plan narrows an existing input to a named refusal.

---
*Phase: 07-promotion-rollback*
*Completed: 2026-09-12*

## Self-Check: PASSED

All 9 key files and all 3 task commits (`86ca4b3`, `214faff`, `844ccf5`) confirmed present on disk and in `git log --oneline --all`.
