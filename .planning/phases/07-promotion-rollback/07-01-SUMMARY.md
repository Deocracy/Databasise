---
phase: 07-promotion-rollback
plan: 01
subsystem: database
tags: [sqlite, promotion-ledger, seam, pydantic, refusals, semver]

# Dependency graph
requires:
  - phase: 04-the-seam
    provides: "The alias-column ledger schema, selectors._resolve_alias's read contract, TraceStore, and the SeamRefusalError/_StrictModel house style this plan's write path satisfies"
provides:
  - "Databasise.promote(alias, trace_ids, change_origin, *, verb) — the operator-asserted MACH-07/API-09 promotion path"
  - "Four additive ledger columns (change_origin, record_kind, minted_version, targets_version) and the generation_state() projection"
  - "databasise/seam/promotion.py — arm resolution, semver mint, mutation-class derivation, measurement-posture refusal"
  - "Six new SeamRefusalError subclasses covering the full promote() refusal ladder"
affects: [07-02-rollback-retire, 07-03-rest-mcp-surface]

# Actuals (#2632)
actuals:
  tokens: 18985
  tasks: 3
  commits: 3

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Pure-computation seam module (promotion.py) mirroring selectors.py's shape: module constants + pure functions over already-resolved data, no I/O, no engine import"
    - "Trace-id -> arm-name resolution via dispatched-node-id-set matching (query-invariant), not wiring_id/arm_id (both constant across LightRAG arms) or wiring_instance_hash (varies per query)"
    - "Whole synchronous ledger sequence (open + read prior + append) offloaded in one run_in_executor call, never split across threads — sqlite3 forbids cross-thread connection use"
    - "Gate-verb refusal enforced at exactly one _MEASUREMENT_POSTURE read site inside promotion.py, never in the calling engine method"

key-files:
  created:
    - databasise/seam/promotion.py
    - databasise/tests/seam/test_promote.py
    - databasise/tests/seam/test_promotion_posture.py
  modified:
    - databasise/ledger/ledger.py
    - databasise/seam/engine.py
    - databasise/seam/envelope.py
    - databasise/seam/refusals.py
    - databasise/seam/__init__.py
    - databasise/tests/ledger/test_ledger.py
    - databasise/tests/seam/test_alias_registry.py
    - databasise/tests/seam/test_selectors.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/runner/test_measurement_posture.py
    - .planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md

key-decisions:
  - "Trace-id -> arm-name resolution matches on the dispatched node id set (RunRecord.nodes[*].node_id), not wiring_id/arm_id (both constant literals across every LightRAG arm) or wiring_instance_hash (varies per query, since it hashes the fully query-injected wiring) — the plan's own literal description of matching on wiring_id/arm_id does not survive contact with the actual RunRecord shape _execute() constructs."
  - "derive_mutation_class takes the two full resolved wiring dicts, not bare node-id sets, so it can compare each shared node id's own component field — the plan's literal 'differing node ids' signature cannot express the 'component identity differs' half of D-10's own stated rule without the full dicts."
  - "The MAJOR/MINOR/mutation-class tests use only real LightRAG arms (naive/bypass/hybrid/local) rather than a HippoRAG wiring — resolve_arm (the unchanged Phase 4 read path _resolve_alias calls) only resolves LightRAG's five named arms, so promoting a HippoRAG wiring through this exact path would leave a later alias read unable to resolve it; using two real, already-registered LightRAG arms satisfies the plan's 'real registered arms, not a fabricated wiring document' instruction without exercising that pre-existing gap."
  - "Test trace records are seeded via TraceStore.persist() with a hand-built minimal record (nodes[*].node_id matching a real arm's own resolved node set) rather than running a full engine.query() for every arm — avoids needing entity/graph retrieval data wired up for hybrid/local, while still going through the same persist() path the engine uses (per the plan's own instruction)."
  - "The entire ledger read-modify-append sequence inside promote() runs in one run_in_executor call, not just the final append() — opening Ledger() on the calling event-loop thread and then calling append() from the executor thread hits sqlite3's cross-thread-use refusal; the fix keeps every Ledger touch on the executor thread."

patterns-established:
  - "MutationClass (a Literal) is the single source of truth both _MEASUREMENT_POSTURE's key set and its own test introspect against — a fourth class landing in the Literal without a matching posture entry is a KeyError, not a silent fall-through."

requirements-completed: [MACH-07, API-09]

coverage:
  - id: D1
    description: "Databasise.promote() appends one operator-asserted ledger row per call; the alias selector resolves to the promoted arm through the unchanged Phase 4 read path"
    requirement: "MACH-07"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_promote.py#test_promote_appends_one_row_the_alias_selector_resolves"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_promote.py#test_two_promotions_produce_two_ordered_rows"
        status: pass
    human_judgment: false
  - id: D2
    description: "change_origin and promotion_provenance are required on every generation record, never defaulted; no verdict/tier-of-decision on an operator-asserted record"
    requirement: "API-09"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_promote.py#test_record_carries_change_origin_and_operator_asserted_provenance"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_promote.py#test_absent_change_origin_refuses_by_name"
        status: pass
    human_judgment: false
  - id: D3
    description: "A semver is minted only at promotion: 1.0.0 on first promotion, MAJOR when the declared surface differs, MINOR otherwise, never a PATCH"
    requirement: "MACH-07"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_promote.py#test_first_promotion_mints_1_0_0"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_promote.py#test_major_bump_when_declared_surface_differs"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_promote.py#test_minor_bump_when_it_does_not"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_promote.py#test_no_path_mints_a_patch"
        status: pass
    human_judgment: false
  - id: D4
    description: "The promotion target, mutation class, and version are all derived — the caller cannot state any of them; empty/unknown/disagreeing trace ids and an invalid change_origin refuse by name before any write"
    requirement: "API-09"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_promote.py#test_empty_trace_ids_refuses_before_any_write"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_promote.py#test_disagreeing_trace_ids_refuse_rather_than_pick_one"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_promote.py#test_mutation_class_is_derived_not_supplied"
        status: pass
    human_judgment: false
  - id: D5
    description: "promote-next/promote-now refuse by name for answer-level and index-side under the default posture (citing RIG SS3.2), and for retrieval-side citing the missing calibrated floor (RIG SSAA.2); check/preview/run refuse as not built; no gate verb ever appends a row"
    requirement: "MACH-07"
    verification:
      - kind: unit
        ref: "databasise/tests/seam/test_promotion_posture.py#test_promote_next_refuses_at_answer_level_naming_the_posture"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_promotion_posture.py#test_promote_next_refuses_at_retrieval_side_naming_the_missing_floor"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_promotion_posture.py#test_no_gate_verb_appends_a_row"
        status: pass
      - kind: unit
        ref: "databasise/tests/seam/test_promotion_posture.py#test_posture_is_not_flippable_at_runtime"
        status: pass
    human_judgment: false

duration: ~55min
completed: 2026-09-12
status: complete
---

# Phase 7 Plan 1: Ledger Columns, Promotion Module, and the Operator-Asserted Promote Path Summary

**`Databasise.promote(alias, trace_ids, change_origin, *, verb)` — four additive ledger columns, a
new pure-computation `promotion.py` module, and the full six-refusal verb ladder that keeps the
gate-adjudicated path genuinely unreachable while the operator-asserted path appends real rows.**

## Performance

- **Duration:** ~55 min
- **Completed:** 2026-09-12
- **Tasks:** 3 of 3
- **Files modified:** 14 (3 created, 11 modified)

## Accomplishments

- `Ledger`/`LedgerRecord` gained four additive columns (`change_origin`, `record_kind`,
  `minted_version`, `targets_version`, no `ALTER TABLE`), a `generation_state()` projection, and a
  `by_alias()` change to exclude tombstoned rows — following Phase 4's own `alias`-column
  no-migration precedent exactly.
- New `databasise/seam/promotion.py`: `resolve_single_arm` (trace records -> one arm name, matched
  on dispatched node id sets — the one query-invariant signal a persisted `RunRecord` actually
  carries), `declared_surface`/`mint_version` (D-06's semver rule, PATCH never minted),
  `derive_mutation_class` (D-10, comparing both node-id-set and per-node `component` identity
  against the prior active generation), and `enforce_gate_verb_posture` (D-11, the one call site
  reading the frozen `_MEASUREMENT_POSTURE` dict).
- `Databasise.promote()` — the caller states only alias, trace ids, and `change_origin`; the arm,
  mutation class, and minted semver are all derived. Six new `SeamRefusalError` subclasses cover
  every way the call can be wrong. Only `verb="operator-asserted"` (the default) reaches
  `Ledger.append()`; `check`/`preview`/`run` refuse immediately as not built, and
  `promote-next`/`promote-now` refuse by posture, naming the class and citing RIG §F3.2/§AA.2.
- `PromotionResult` (§18.2's closed set) added beside `ResponseEnvelope`/`SeamEvent`.
- Updated `.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md` and its guard test
  (`tests/runner/test_measurement_posture.py`) for the new, narrowly-named operator-asserted write
  exception — the guard test's own docstring anticipated exactly this update, and its two
  exemption lists now name `seam/engine.py` explicitly, with the reason recorded in both files.

## Task Commits

1. **Tasks 1-3 (production code): ledger columns, promotion module, `promote()`, MACH-09 posture
   record update** — `953b203` (feat)
2. **Tasks 1-3 (test coverage): tracer, refusals, semver, mutation-class, posture-refusal
   behavior** — `a1b9d40` (test)
3. **Rule 3 fix: REST transport growth-invariant factory entries for the six new refusals** —
   `37ac327` (fix)

_Note: production code and tests for all three plan tasks were implemented together as one
interdependent unit (the promote() refusal ladder, semver mint, and mutation-class derivation are
not independently correct in isolation — see "TDD Gate Compliance" below) and committed in two
passes (code, then tests) plus one required fix, rather than nine separate per-task RED/GREEN
commits._

## Files Created/Modified

- `databasise/seam/promotion.py` - pure computation: arm resolution, semver mint, mutation-class derivation, posture refusal
- `databasise/ledger/ledger.py` - four additive columns, `generation_state()`, tombstone-excluding `by_alias()`
- `databasise/seam/engine.py` - `Databasise.promote()`
- `databasise/seam/envelope.py` - `PromotionResult`
- `databasise/seam/refusals.py` - six new `SeamRefusalError` subclasses
- `databasise/seam/__init__.py` - exports `PromotionResult`
- `databasise/tests/seam/test_promote.py` - Tasks 1-2 behavior coverage (20 tests)
- `databasise/tests/seam/test_promotion_posture.py` - Task 3 behavior coverage (10 tests)
- `databasise/tests/ledger/test_ledger.py` - new-column round trip, trigger regression, `generation_state()` coverage
- `databasise/tests/seam/test_alias_registry.py`, `test_selectors.py` - two now-required `LedgerRecord` fields on existing fixtures
- `databasise/tests/seam/test_rest_transport.py` - refusal-factory entries for the six new types
- `databasise/tests/runner/test_measurement_posture.py`, `.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md` - narrowly-named exceptions for the new operator-asserted write path

## Decisions Made

See `key-decisions` in frontmatter. In short: trace-id → arm-name resolution had to be redesigned
from the plan's literal `wiring_id`/`arm_id` description (both are constant literals across every
LightRAG arm and cannot distinguish them) to matching on the dispatched node id set instead;
`derive_mutation_class` takes full resolved wiring dicts rather than bare id sets so it can compare
per-node `component` identity, per D-10's own stated rule; and the MAJOR/MINOR tests use two real
LightRAG arms rather than a HippoRAG wiring, since the unchanged Phase 4 read path (`resolve_arm`)
cannot resolve a non-LightRAG arm name.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Cross-thread sqlite3 use in the async `run_in_executor` offload**
- **Found during:** Task 1 (manual end-to-end verification before writing tests)
- **Issue:** Opening `Ledger(self.store_root)` on the calling event-loop thread, then calling
  `ledger.append(record)` via `run_in_executor` (a different OS thread), raised
  `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same
  thread`.
- **Fix:** The entire read-modify-append sequence (open `Ledger`, read the prior active
  generation, derive the class/version, construct the record, append) now runs inside one
  function passed to `run_in_executor`, so the connection is opened and used on the same thread.
- **Files modified:** `databasise/seam/engine.py`
- **Verification:** Manual end-to-end run succeeded; all 20 `test_promote.py` tests pass.
- **Committed in:** `953b203` (part of the production-code commit)

**2. [Rule 3 - Blocking] Six new `SeamRefusalError` subclasses had no REST-transport factory entry**
- **Found during:** running the full test suite after landing the promote() refusal ladder
- **Issue:** `test_rest_transport.py::test_every_refusal_subclass_maps_to_a_non_success_status_...`
  walks `SeamRefusalError.__subclasses__()` and requires a factory entry per subclass; the six new
  refusal types failed this pre-existing growth-invariant test.
- **Fix:** Added a factory-callable entry for each of the six new refusal types to
  `_REFUSAL_FACTORIES`.
- **Files modified:** `databasise/tests/seam/test_rest_transport.py`
- **Verification:** `uv run pytest -q tests/seam/test_rest_transport.py` passes.
- **Committed in:** `37ac327`

**3. [Rule 1/3 - Bug/Blocking] The MACH-09 measurement-posture guard test failed as its own
docstring anticipated**
- **Found during:** running the full test suite after landing `Databasise.promote()`
- **Issue:** `tests/runner/test_measurement_posture.py` pins, structurally, that no non-test module
  imports the ledger and that no module defines a `promote`/`promote_next`/`promote_now`/
  `rollback` function — a check its own docstring says "is expected to fail when Phase 7 builds
  MACH-07's promote/rollback path." That failure fired exactly as designed.
- **Fix:** Following the guard's own instruction, updated `.planning/phases/02-falsifier-gate/
  02-MACH-09-POSTURE.md` with a new "07-01-PLAN.md: the operator-asserted write exception" section
  explaining why `seam/engine.py`'s `Ledger` import and `promote` definition do not mean the
  gate-adjudicated path has started to exist (only `verb="operator-asserted"` ever appends), and
  narrowed the guard test's two exemption lists to name `seam/engine.py` explicitly, with the
  promotion-verb exemption scoped to the literal string `"def promote(...)"` only — a future
  `promote_next`/`promote_now`/`rollback` *implementation*, or `promote` defined anywhere else,
  still fails this test.
- **Files modified:** `databasise/tests/runner/test_measurement_posture.py`,
  `.planning/phases/02-falsifier-gate/02-MACH-09-POSTURE.md`
- **Verification:** `uv run pytest -q tests/runner/test_measurement_posture.py` passes (3/3).
- **Committed in:** `953b203` (part of the production-code commit)

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All three were required for the plan's own `<verification>` block ("`uv run
pytest -q` is green at or above the Phase 6 baseline") to hold. No scope creep — no new feature was
added beyond what the plan's tasks specify.

## TDD Gate Compliance

This plan's three tasks all carry `tdd="true"`. `workflow.tdd_mode` is not set in
`.planning/config.json`, so the RED/GREEN/REFACTOR gate is advisory, not enforced. The three
tasks' production code (ledger schema, `promotion.py`, `Databasise.promote()`) was implemented as
one interdependent unit rather than incrementally per task, because Task 2's refusal/semver
completion and Task 3's verb-ladder branching are not separable correctness boundaries from Task
1's own happy path — e.g. `mint_version`'s real prior-generation comparison (Task 2) and
`derive_mutation_class`'s real prior-resolved comparison (Task 2) are exercised by Task 1's own
`test_first_promotion_mints_1_0_0`/`test_promote_appends_one_row_...` tests via the `prior=None`
branch of the identical function. Every task's own `<behavior>`-block test is present, named
exactly as specified, and passing (verified individually via each task's own `<verify>` command
before committing). No `test(...)` commit strictly precedes every corresponding `feat(...)` commit
per task; instead, one `feat` commit (`953b203`) landed all three tasks' production code and one
`test` commit (`a1b9d40`) landed all three tasks' test files — verified together before either
commit was made. This is recorded here per the gate's own instruction rather than left implicit.

## Issues Encountered

None beyond the deviations documented above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `databasise/seam/promotion.py`'s `resolved_wiring_for_arm`, `RECORD_KIND_ROLLBACK`,
  `RECORD_KIND_TOMBSTONE` constants, and `Ledger.generation_state()` all already exist for
  07-02's `rollback()`/`retire()` to consume directly — no further ledger schema change is needed.
- `_GATE_VERBS`/`_NOT_BUILT_VERBS`/`PromotionVerb`/`enforce_gate_verb_posture` are all exported
  from `promotion.py` and ready for 07-03's REST/MCP transports to route through unchanged.
- No blockers. Full suite: 1006 passed, 1 skipped (baseline was 960 passed / 3 skipped at
  06-16) — no regressions, all new coverage green.

---

*Phase: 07-promotion-rollback*
*Completed: 2026-09-12*
