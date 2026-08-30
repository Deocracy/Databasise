---
phase: 01-machine-core
plan: 03
subsystem: infra
tags: [validator, tarjan, scc, taint-rule, blast-radius, execution-mode, graphlib]

# Dependency graph
requires:
  - phase: 01-machine-core
    provides: "01-02's tracer slice — validator/{parse,depth}.py's acyclic min-reduce, parts/schema.py's Part/WiringNode shapes and 17-member Effect literal, the PartRegistry tracer instance"
provides:
  - "validator/cycles.py — strongly_connected_components() and condensation(), hand-rolled iterative Tarjan, no networkx dependency"
  - "validator/depth.py — effective_depth() replaced to compute over the SCC condensation DAG; cyclic wirings now resolve a defined depth for every node instead of raising graphlib.CycleError"
  - "validator/errors.py — Violation/ValidationReport shapes; parse_wiring never raises, accumulates every violation plus every detected cycle into one report"
  - "validator/blast_radius.py — blast_radius_violations(), the load-time half of D-02's blast-radius rule"
  - "validator/execution_mode.py — derive_execution_mode() (4-way placement) and host() with D-08's named UnimplementedPlacementError refusals"
  - "validator/parse.py — parse_wiring() now returns ParsedWiring.report (never raises); cycle detection always runs; blast-radius check wired in at load time once the wiring is otherwise structurally sound"
  - "tests/validator/test_taint_conformance.py — spike-005's 12-case laundering conformance set, ported and D-03-repaired, non-skippable"
affects: ["01-07", "01-08"]

actuals:
  tokens: 14044
  tasks: 3
  commits: 5

tech-stack:
  added: []
  patterns:
    - "Iterative Tarjan SCC (explicit work-stack, no recursion) — a wiring is author-supplied data, so a deep dependency chain must not exhaust Python's recursion limit"
    - "SCC condensation + graphlib.TopologicalSorter for cycle-safe depth: cycles collapse to one condensed node, the condensation is acyclic by construction, min-reduce runs over it unchanged"
    - "ValidationReport accumulation, never raise: every validator check (component resolution, dangling deps, empty wiring, blast-radius) appends to one report; parse_wiring returns it instead of raising WiringValidationError"
    - "artifact_scope read via getattr(part, \"artifact_scope\", \"shared\") rather than a required dataclass field — decouples this plan's lane (validator/**) from a sibling wave-3 plan's file (parts/schema.py) while matching CONTRACT §3's own default"
    - "execution_mode's derive/host split: derivation is a pure function of effects[]+kind and always succeeds; host() is the separate refusal point (D-08)"

key-files:
  created:
    - databasise/validator/cycles.py
    - databasise/validator/errors.py
    - databasise/validator/blast_radius.py
    - databasise/validator/execution_mode.py
    - databasise/tests/validator/__init__.py
    - databasise/tests/validator/test_cycles_and_depth.py
    - databasise/tests/validator/test_blast_radius.py
    - databasise/tests/validator/test_execution_mode.py
    - databasise/tests/validator/test_taint_conformance.py
  modified:
    - databasise/validator/depth.py
    - databasise/validator/parse.py

key-decisions:
  - "parse_wiring's return contract changed: it never raises WiringValidationError anymore (that class is retained, unused, for import stability). ParsedWiring gained a report: ValidationReport field (default_factory=ValidationReport) carrying every accumulated violation and every detected cycle. This keeps parse_wiring(doc, registry) -> ParsedWiring's call-site signature identical for databasise/__init__.py and runner/scheduler.py (neither file is in this plan's lane), while satisfying Task 1's 'parse_wiring returns a report, raises nothing' behavior tests."
  - "Cross-plan lane conflict on Part.artifact_scope, resolved by not touching parts/schema.py: Task 2's action text says to add artifact_scope to the Part dataclass 'if plan 01-02 did not already carry it', but in this wave it is plan 01-04 (a parallel sibling, not 01-02) whose files_modified and Task 3 own databasise/parts/schema.py. This plan's worktree lane instructions explicitly forbid editing parts/**. blast_radius.py reads the scope via getattr(part, \"artifact_scope\", \"shared\") instead — correct whether or not the field has landed in a given worktree, since Part is a plain non-frozen dataclass and CONTRACT §3's own default is 'shared' when unstated. Test fixtures set the attribute post-construction the same way. The acceptance criterion requiring databasise/parts/schema.py to declare artifact_scope is therefore satisfied by 01-04's Task 3, not by this plan — see Deviations below."
  - "depth.py's existing (2-way in-process/subprocess) derive_execution_mode was left completely untouched: runner/scheduler.py (a different wave's lane, 01-08) still imports it. The new 4-way derive_execution_mode/host live only in the new execution_mode.py module; wiring runner/scheduler.py over to it is explicitly plan 01-08's deliverable (depends_on: [01-03, 01-04])."
  - "Task 1's GREEN commit intentionally excluded the blast-radius wiring into parse_wiring, and Task 2's GREEN commit added it back — matching the plan's own task split (Task 1's action text never mentions blast_radius; Task 2's does: 'Wire blast_radius_violations into parse_wiring's report')."
  - "The depth/blast-radius pass inside parse_wiring only runs when the wiring is otherwise structurally sound (report.ok before that point) — unknown-component/dangling-dep/invalid-schema violations mean some node's part never resolved, and computing a depth map over an unresolved graph would KeyError rather than say anything meaningful. A cycle does not gate this: SCC condensation resolves a defined depth for a cyclic-but-otherwise-well-formed wiring."

patterns-established:
  - "Test-file-local duck-typed registry (test_taint_conformance.py's _FixtureRegistry) instead of touching a sibling plan's owned file: parse_wiring only calls registry.get(name_at_version), so a single-method shim satisfies the real code path without reaching across a wave's file-ownership lane."

requirements-completed: [MACH-05, MACH-08]

coverage:
  - id: D1
    description: "Effective depth is computed over an SCC condensation of the wiring graph: opaque/evidence/stage taint min-reduce holds on linear chains, parallel lanes, non-adjacent fan-in, and cycles (all cycle members share one depth; a downstream node inherits the cycle's depth in dependency order)"
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_cycles_and_depth.py -x"
        status: pass
    human_judgment: false
  - id: D2
    description: "A cyclic wiring resolves a defined depth for every node without raising; the cycle is reported as data (report.cycles) rather than treated as a violation, and parse_wiring never raises for an ordinary defect — every violation accumulates into one ValidationReport in a single pass"
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_cycles_and_depth.py#test_unintended_cycle_is_reported_as_data_not_raised"
        status: pass
      - kind: unit
        ref: "databasise/tests/validator/test_cycles_and_depth.py#test_parse_wiring_accumulates_three_independent_defects_in_one_pass"
        status: pass
    human_judgment: false
  - id: D3
    description: "The blast-radius rule refuses a shared artifact write at load time whenever effective depth is not stage, naming the offending node id and its computed depth; quarantined and self_storage writes are always legal at any depth; an unstated artifact scope defaults explicitly to shared"
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_blast_radius.py -x"
        status: pass
    human_judgment: false
  - id: D4
    description: "The four transient store-write effects (writes_kv/writes_vector/writes_graph/writes_lexical) sit outside the blast-radius rule by design and never trigger a refusal, however shallow the writing node's effective depth (D-03 repair 2, PARTS-04 D1)"
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_blast_radius.py#test_transient_store_writes_are_outside_the_rule_at_any_depth"
        status: pass
      - kind: unit
        ref: "databasise/tests/validator/test_taint_conformance.py#test_transient_effects_added_to_case_6_change_nothing"
        status: pass
    human_judgment: false
  - id: D5
    description: "execution_mode is derived purely from a node's declared effects[] and kind (never requested); it always resolves to one of the four placements, and hosting subprocess/confined-unit/long-lived-service refuses explicitly by name (UnimplementedPlacementError) while the derivation itself still succeeds and is available for stamping (D-08)"
    requirement: "MACH-08"
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_execution_mode.py -x"
        status: pass
    human_judgment: false
  - id: D6
    description: "Spike 005's twelve-case laundering conformance set, ported under the repaired contract vocabulary, reproduces the measured taint/blast-radius result exactly on all twelve cases with no case exempt from the failure count (D-03's three named repairs)"
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_taint_conformance.py -x"
        status: pass
    human_judgment: false
  - id: D7
    description: "A wiring with an empty nodes object is refused at parse time with a violation pointing at /nodes; a single-node wiring with an empty deps list validates clean and yields a depth map of length one"
    requirement: "MACH-05"
    verification:
      - kind: unit
        ref: "databasise/tests/validator/test_cycles_and_depth.py#test_empty_wiring_is_one_violation_and_a_single_clean_node_yields_one_depth"
        status: pass
    human_judgment: false

duration: 55min
completed: 2026-08-30
status: complete
---

# Phase 01 Plan 03: Cycle-Safe Depth, Blast-Radius Rule, and execution_mode Derivation Summary

**Cycle-safe effective-depth computation over a hand-rolled iterative Tarjan SCC condensation, the blast-radius rule enforced at load time, a four-way execution_mode derivation with D-08's named hosting refusals, and spike 005's twelve-case laundering conformance set ported and repaired per D-03 — all fifteen `<behavior>` requirements plus the full 12-case oracle passing exactly, not approximately.**

## Performance

- **Duration:** 55 min
- **Tasks:** 3
- **Files modified:** 11 (9 new, 2 modified)

## Accomplishments

- `validator/cycles.py`: hand-rolled, iterative `strongly_connected_components()` (Tarjan, explicit work stack — no recursion, no `networkx`) plus `condensation()`, both exercised directly and through `effective_depth()`
- `validator/depth.py`: `effective_depth()`'s ordering source replaced with the SCC condensation DAG — a cyclic wiring now resolves a defined depth for every node instead of raising `graphlib.CycleError`; the min-reduce loop body is otherwise unchanged
- `validator/errors.py`: `Violation`/`ValidationReport` — `parse_wiring` now accumulates every defect into one report and never raises
- `validator/parse.py`: cycle detection always runs and populates `report.cycles` as data; the blast-radius check is wired in at load time (D-02's first call site) once the wiring is otherwise structurally sound
- `validator/blast_radius.py`: `blast_radius_violations()` — the three D-03 repairs (no fabricated `writes_quarantined` effect; transient store writes exempt; violation messages name node id + depth + scope)
- `validator/execution_mode.py`: `derive_execution_mode()` (four placements, pure function of `effects[]`/`kind`) and `host()` (D-08's named refusals for the three unimplemented placements — derivation always succeeds, only hosting refuses)
- `tests/validator/test_taint_conformance.py`: all twelve spike-005 cases reproduced exactly under the repaired vocabulary, plus a transient-effects guard and a non-exemptible meta-test — 50/50 tests green across the whole `databasise/` suite, including the pre-existing tracer test unchanged

## Task Commits

Each task was committed as a TDD RED/GREEN pair:

1. **Task 1 (RED): failing tests for cycle-safe depth computation** — `1a8ed2b` (test)
2. **Task 1 (GREEN): Tarjan SCC condensation, taint min-reduce, one-pass accumulation** — `3b318a9` (feat)
3. **Task 2 (RED): failing tests for blast-radius rule and execution_mode** — `36f43e9` (test)
4. **Task 2 (GREEN): blast-radius rule at load time, execution_mode + D-08 refusals** — `681193a` (feat)
5. **Task 3: ported spike-005 12-case conformance set (D-03 repaired)** — `e610ca4` (test — proof-only, no new production code; the taint/blast-radius rules it proves already exist from Tasks 1-2)

**Plan metadata:** (this commit) `docs(01-03): complete cycle-safe depth, blast-radius, execution_mode plan`

## Files Created/Modified

- `databasise/validator/cycles.py` - `strongly_connected_components()`, `condensation()`
- `databasise/validator/errors.py` - `Violation`, `ValidationReport`, stable violation-code constants
- `databasise/validator/depth.py` - `effective_depth()` rewritten over the SCC condensation; `derive_execution_mode()` (the tracer's own 2-way version) left untouched — still consumed by `runner/scheduler.py`
- `databasise/validator/parse.py` - `parse_wiring()` accumulates into `ValidationReport`, never raises; `ParsedWiring.report` field added; cycle detection and the blast-radius check both wired in
- `databasise/validator/blast_radius.py` - `blast_radius_violations()`
- `databasise/validator/execution_mode.py` - `derive_execution_mode()` (4-way), `host()`, `UnimplementedPlacementError`
- `databasise/tests/validator/__init__.py` - test package marker
- `databasise/tests/validator/test_cycles_and_depth.py` - 9 tests (Task 1's `<behavior>`)
- `databasise/tests/validator/test_blast_radius.py` - 7 tests (Task 2's blast-radius `<behavior>`)
- `databasise/tests/validator/test_execution_mode.py` - 9 tests (Task 2's execution_mode `<behavior>`)
- `databasise/tests/validator/test_taint_conformance.py` - 15 tests: 12 parametrized spike-005 cases + transient-effects guard + meta-test + repair-one check

## Decisions Made

- **`parse_wiring` never raises; `ParsedWiring` gained a `report` field.** See `key-decisions` in frontmatter — this keeps the `parse_wiring(doc, registry) -> ParsedWiring` call-site contract identical for `databasise/__init__.py` and `runner/scheduler.py` (neither in this plan's lane) while satisfying the plan's own "returns every violation, raises nothing" requirement.
- **`artifact_scope` read via `getattr`, not a declared `Part` field** — this wave's `databasise/parts/schema.py` is plan 01-04's file, not this plan's; see Deviations below for the full cross-plan resolution.
- **`depth.py`'s existing 2-way `derive_execution_mode` left untouched.** The new 4-way derivation lives only in the new `execution_mode.py`; wiring `runner/scheduler.py` over to it is explicitly plan 01-08's job (`depends_on: [01-03, 01-04]`).
- **Task 1's GREEN commit excluded the blast-radius wiring**, added back in Task 2's GREEN commit — matches the plan's own task split (Task 1's `<action>` never mentions `blast_radius`; Task 2's does).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed the literal string "networkx" from cycles.py's docstring**
- **Found during:** Task 1, verifying the acceptance-criteria grep `grep -v '^#' validator/cycles.py | grep -c 'networkx'` (must return 0)
- **Issue:** The module docstring explained why no third-party graph library was added, and named `networkx` twice while doing so — tripping the acceptance criterion's own strict grep (unlike Task 2's semantically-scoped criterion, this one has no "docstring explaining the rejection doesn't trip its own gate" carve-out)
- **Fix:** Reworded the docstring to explain the same rationale (01-RESEARCH.md Pattern 2's rejection, D-14's import boundary) without the literal substring
- **Files modified:** `databasise/validator/cycles.py`
- **Verification:** `grep -v '^#' validator/cycles.py | grep -c 'networkx'` returns 0; `uv run ruff check validator/cycles.py` passes
- **Committed in:** `3b318a9` (Task 1 GREEN commit — fixed before commit, not a follow-up)

**2. [Rule 3 - Blocking] Ruff import-sort fixes on newly created test files**
- **Found during:** Task 2 and Task 3, post-implementation lint pass
- **Issue:** `uv run ruff check` flagged `I001` (import block un-sorted) in `test_execution_mode.py` and `test_taint_conformance.py` — a blank-line-separated third-party (`pytest`) vs first-party (`databasise.*`) import grouping ruff expects
- **Fix:** `uv run ruff check --fix` on the two affected files
- **Files modified:** `databasise/tests/validator/test_execution_mode.py`, `databasise/tests/validator/test_taint_conformance.py`
- **Verification:** `uv run ruff check validator/ tests/validator/` — all checks passed; full suite still green after the fix
- **Committed in:** `681193a` (Task 2 GREEN) / `e610ca4` (Task 3)

**3. [Cross-plan lane resolution, not a rule 1-3 auto-fix] `Part.artifact_scope` not added to `databasise/parts/schema.py`**
- **Found during:** Task 2, reading the plan's own action text ("Add `artifact_scope` to the `Part` dataclass in `databasise/parts/schema.py` if plan 01-02 did not already carry it")
- **Issue:** In this wave, `databasise/parts/schema.py` is plan 01-04's file (confirmed: 01-04's frontmatter `files_modified` and its Task 3 both list it), not plan 01-02's — and this plan's own worktree lane instructions explicitly forbid editing `databasise/parts/**`. Editing it directly would either silently overwrite or merge-conflict with 01-04's concurrent worktree.
- **Resolution:** `blast_radius.py` reads the field via `getattr(part, "artifact_scope", "shared")` instead of requiring it as a declared dataclass field. `Part` is a plain, non-frozen, non-slotted dataclass, so attribute assignment (`part.artifact_scope = "quarantined"`) works in test fixtures regardless of whether the field is formally declared yet in a given worktree. The default (`"shared"` when absent) matches CONTRACT §3's own rule for an unstated scope, so behavior is correct in every worktree state: before 01-04 lands, during the merge, and after.
- **Files affected:** `databasise/validator/blast_radius.py`, `databasise/tests/validator/test_blast_radius.py`, `databasise/tests/validator/test_taint_conformance.py` — none of them `databasise/parts/schema.py`
- **Residual acceptance-criteria gap:** Task 2's acceptance criterion "`databasise/parts/schema.py` declares an `artifact_scope` field over exactly `shared`, `quarantined`, `self_storage`" is **not satisfiable from this plan's worktree** — it is satisfied by plan 01-04's Task 3 in its own worktree. The orchestrator should verify this criterion against the merged tree (post-wave), not against this plan's commit range alone.
- **Committed in:** `681193a` (Task 2 GREEN)

---

**Total deviations:** 3 (2 auto-fixed blocking issues, 1 cross-plan lane resolution documented for orchestrator verification)
**Impact on plan:** No scope creep — every fix stayed inside `databasise/validator/**` and `databasise/tests/validator/**`. The one residual gap (`parts/schema.py`'s `artifact_scope` field) is by design: it is a sibling plan's deliverable in this wave, not a defect in this plan's own work, and this plan's code is correct with or without it present.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The validator is complete for Phase 1's scope: cycle-safe depth, the load-time blast-radius rule, and execution_mode derivation with D-08's named refusals all work over the real `parse_wiring` path, and spike 005's measured result reproduces exactly under the repaired vocabulary. `cd databasise && uv run pytest -q` is green (50 tests), including the pre-existing tracer test from plan 01-02 unchanged.

Two follow-on items for later plans in this phase, both already anticipated by the plan structure:
- **Plan 01-04** (parallel sibling, this wave) must land `Part.artifact_scope` in `databasise/parts/schema.py` for the acceptance criterion this plan's Task 2 could not satisfy from its own lane (see Deviations).
- **Plan 01-08** (wave 4, `depends_on: [01-03, 01-04]`) wires `runner/scheduler.py` over to this plan's new `validator/execution_mode.py` (`derive_execution_mode`/`host`), replacing the tracer's own 2-way version still living in `depth.py`.

Note for the orchestrator: this plan's frontmatter lists `requirements: [MACH-05, MACH-08]`. Per this phase's shared context (see 01-02-SUMMARY.md's own note), MACH-05 is also listed by other plans in this phase (01-08 in particular, which completes the runner integration) and should not be marked complete in `REQUIREMENTS.md` until its last contributing plan lands — the orchestrator closes it at phase end. MACH-08 (execution_mode derived from effects[], never requested) is fully proven by this plan's `test_execution_mode.py` and may be closeable now, but is left to the orchestrator's judgment alongside MACH-05 for consistency.

No blockers.

---
*Phase: 01-machine-core*
*Completed: 2026-08-30*

## Self-Check: PASSED

All 11 claimed files found on disk (6 validator/ modules, 5 tests/validator/ files including
`__init__.py`); commits `1a8ed2b`, `3b318a9`, `36f43e9`, `681193a`, `e610ca4` all confirmed in
`git log --oneline --all`.
