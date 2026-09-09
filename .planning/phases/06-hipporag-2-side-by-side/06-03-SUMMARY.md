---
phase: 06-hipporag-2-side-by-side
plan: 03
subsystem: rag-engine
tags: [api-08, comparison, seam, rest, mcp, falsifier-14, hipporag, lightrag]

# Dependency graph
requires:
  - phase: 06-hipporag-2-side-by-side
    plan: "06-01"
    provides: "the §18 Databasise seam object (query/_execute), selector resolution, evidence minting, the modality-agnostic wiring pool"
provides:
  - "Databasise.compare(query_object, selectors) — API-08's inspection-only comparison operation, degenerating to a run at one selector"
  - "databasise/seam/compare.py's compare_arms(execute, query_object, selectors) — a pure async fan-out over the bound _execute callable, no second scheduler/envelope path"
  - "POST /compare (REST) and the compare MCP tool — both thin adapters over the identical Databasise.compare method"
  - "F-14's first recorded outcome: databasise/evidence/F-14-SEAM-INVARIANCE.md, from a real two-arm comparison call"
  - "Phase 6's own §18.5 operations-table record (.planning/phases/06-hipporag-2-side-by-side/COVERAGE.md)"
affects: [06-08, 06-09]

# Actuals (#2632)
actuals:
  tokens: 17061
  tasks: 3
  commits: 3
plan_head_before: ecd4be6

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Comparison as a thin fan-out over the existing single-arm _execute() path — compare_arms() never builds a second scheduler, store-resolution path or envelope-assembly function; the leak gate/§4 provenance redaction apply to every comparison arm by construction, not by a second copy of the rule"
    - "Selector-key rendering as a deterministic, case-preserving function (render_selector_key) — never normalised, case-folded, sorted or deduplicated; a multi-capability selector's own values join in the caller's own supplied order by a declared module-constant separator"
    - "A comparison-response key collision refuses by name (DuplicateComparisonKeyError) rather than silently collapsing two selectors into one entry"

key-files:
  created:
    - databasise/seam/compare.py
    - databasise/tests/seam/test_compare.py
    - databasise/evidence/F-14-SEAM-INVARIANCE.md
    - databasise/tests/evidence/test_f14_record.py
    - .planning/phases/06-hipporag-2-side-by-side/COVERAGE.md
  modified:
    - databasise/seam/engine.py
    - databasise/seam/refusals.py
    - databasise/seam/__init__.py
    - databasise/seam/rest.py
    - databasise/mcp/tools.py
    - databasise/mcp/server.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/tests/mcp/test_tool_growth_invariant.py
    - databasise/tests/mcp/test_dual_transport_parity.py
    - .planning/phases/05-opaque-side-admission/COVERAGE.md

key-decisions:
  - "Capability-selector key rendering joins the caller's own requested values, in their own supplied order, with a module-constant separator (CAPABILITY_KEY_SEPARATOR = '+') — this plan's own decision, since §18.4 names no rendering rule for a multi-capability selector (flagged assumption, carried verbatim from the plan)."
  - "A selector-key collision (two selectors rendering to the same key) refuses by name via a new DuplicateComparisonKeyError, rather than silently collapsing the two into one dict entry — not explicitly tested by this plan's own <behavior> block, but required by its <action> text; implemented and registered a REST refusal-mapping factory for it alongside EmptyComparisonRequestError's own required factory."
  - "Both LightRAG's naive arm and HippoRAG's base wiring were seeded under one shared store_root/workspace for every real comparison call in this plan (test_compare.py's dual_arm_store fixture, reused by test_dual_transport_parity.py's compare scenario and by F-14's own evidence-generating run) — RIG §RUN.1/§RUN.2's own per-modality namespace isolation (already proven by test_store_isolation.py) makes this safe without any new isolation code."

requirements-completed: [API-08, MODAL-05]

coverage:
  - id: D1
    description: "One query object and two selectors return a mapping keyed by exactly those two caller-supplied selector values, each a §18.2 ResponseEnvelope"
    requirement: API-08
    verification:
      - kind: unit
        ref: "tests/seam/test_compare.py#test_keyed_by_selector"
        status: pass
    human_judgment: false
  - id: D2
    description: "A comparison call carrying exactly one selector returns a bare ResponseEnvelope — the same object query() returns — never a one-key mapping"
    requirement: API-08
    verification:
      - kind: unit
        ref: "tests/seam/test_compare.py#test_single_selector_is_a_run"
        status: pass
    human_judgment: false
  - id: D3
    description: "A comparison call carrying zero selectors is refused by name (EmptyComparisonRequestError) rather than silently defaulting"
    requirement: API-08
    verification:
      - kind: unit
        ref: "tests/seam/test_compare.py#test_zero_selectors_is_refused"
        status: pass
    human_judgment: false
  - id: D4
    description: "No comparison response contains a verdict-vocabulary token, an arm id, a wiring id, a node id, an instance hash, or a provenance key at any nesting depth"
    requirement: API-08
    verification:
      - kind: unit
        ref: "tests/seam/test_compare.py#test_no_verdict_leaks"
        status: pass
      - kind: unit
        ref: "tests/seam/test_compare.py#test_no_internal_identity_leaks"
        status: pass
    human_judgment: false
  - id: D5
    description: "Selector values key the response exactly as the caller supplied them — two selectors differing only in letter case are two distinct keys"
    requirement: API-08
    verification:
      - kind: unit
        ref: "tests/seam/test_compare.py#test_selector_keys_are_not_normalised"
        status: pass
    human_judgment: false
  - id: D6
    description: "An unsatisfiable selector anywhere in a comparison request refuses the whole comparison, never a partial mapping with one arm silently missing"
    requirement: API-08
    verification:
      - kind: unit
        ref: "tests/seam/test_compare.py#test_unsatisfiable_selector_refuses_the_whole_comparison"
        status: pass
    human_judgment: false
  - id: D7
    description: "The comparison surface is reachable identically in-process, over REST (POST /compare), and over MCP (compare tool), with the tool roster growing by exactly one name"
    requirement: API-08
    verification:
      - kind: integration
        ref: "tests/seam/test_rest_transport.py (28 passed, --extra rest)"
        status: pass
      - kind: integration
        ref: "tests/mcp/test_tool_growth_invariant.py + tests/mcp/test_dual_transport_parity.py (28 passed, --extra rest --extra mcp)"
        status: pass
    human_judgment: false
  - id: D8
    description: "F-14's outcome is recorded from a real cross-modality comparison call, either way"
    requirement: MODAL-05
    verification:
      - kind: unit
        ref: "tests/evidence/test_f14_record.py (7 passed)"
        status: pass
    human_judgment: true
    rationale: "The evidence document's own verdict (no consumer-visible field changed) reflects one real run against seeded fixtures with stub clients — a human should confirm the document's own house-format completeness and that the recorded verdict reads as an honest, non-overreaching claim, per this plan's own prohibition against recording F-14 as holding without a real call."

# Metrics
duration: ~75min
completed: 2026-09-09
status: complete
---

# Phase 6 Plan 3: API-08 Comparison Surface & F-14 Summary

**One query object and N selectors return N §18.2 envelopes keyed by the caller's own selector values, reachable identically in-process, over REST, and over MCP, through the identical single-arm `_execute()` path — and F-14 has fired for the first time, from a real LightRAG-vs-HippoRAG comparison call, recording that no consumer-visible envelope field changed across the modality swap.**

## Performance

- **Duration:** ~75 min
- **Completed:** 2026-09-09
- **Tasks:** 3
- **Files modified/created:** 15

## Accomplishments

- `databasise/seam/compare.py`: `compare_arms(execute, query_object, selectors)` — a pure async fan-out over the bound `_execute` callable, no second scheduler, store-resolution path or envelope-assembly function; `render_selector_key` renders the caller's own selector value deterministically, never normalising, case-folding or sorting it
- `Databasise.compare()`: runs `check_consumable` once, refuses zero selectors with `EmptyComparisonRequestError`, degenerates to `self._execute(...)` unchanged at exactly one selector (RIG §RUN.3's degenerate-width rule), otherwise delegates to `compare_arms`
- A real two-arm comparison proven end to end (`databasise/tests/seam/test_compare.py`'s `dual_arm_store` fixture): LightRAG's `naive` arm and HippoRAG's base wiring, seeded under one shared `store_root`/workspace, keyed by their own rendered capability-selector values, with no verdict token and no internal identity (node id, wiring id, `provenance` key, instance-hash-shaped value) anywhere in the serialized response — the identity-leak check derives its forbidden-token set live from the registry and both resolved wirings, never a hand-written list
- `POST /compare` (REST) and the `compare` MCP tool: both exactly deserialize → `await engine.compare(...)` → return, mapped through each transport's own existing generic refusal handler; `TOOL_NAMES` grew from five to six, and the growth-invariant test that registers a fixture second modality still passes with the tool set byte-identical before/after
- `databasise/evidence/F-14-SEAM-INVARIANCE.md`: the first genuine cross-modality seam call this project's record has ever run — all ten `ResponseEnvelope` fields present with identical shape in both arms' responses; `answer` and `depth_label` legitimately carry different *content* per arm (HippoRAG's missing generator position, its still-`opaque` effective depth), explicitly distinguished from a field-set difference. Verdict: F-14 holds for this pair — §18.3's invariance rule is not refuted by this run
- Full suite: bare `uv run pytest -q` → 729 passed, 6 skipped, exit 0; `--extra rest` → 797 passed, 1 skipped, exit 0; `--extra rest --extra mcp` together → 790 passed, 1 skipped, exit 0 — no regressions against the 702/13 (bare) baseline plan 06-02 recorded, plus 27 new tests (14 in `test_compare.py`+`test_f14_record.py`, 13 across the extended MCP/REST parity/growth files)

## Task Commits

Each task was committed atomically:

1. **Task 1: `Databasise.compare` — a fan-out over the one existing execution path** — `b05569e` (feat)
2. **Task 2: the same comparison over REST and MCP, with the tool-growth rule re-proven** — `218dd25` (feat)
3. **Task 3: F-14's outcome, recorded from a real cross-modality call** — `9085fd5` (test)

## Files Created/Modified

- `databasise/seam/compare.py` — `compare_arms`, `render_selector_key`, `CAPABILITY_KEY_SEPARATOR`
- `databasise/seam/engine.py` — `Databasise.compare`
- `databasise/seam/refusals.py` — `EmptyComparisonRequestError`, `DuplicateComparisonKeyError`
- `databasise/seam/__init__.py` — exports `compare_arms`
- `databasise/tests/seam/test_compare.py` — the seven `<behavior>`-block tests, `dual_arm_store` fixture
- `databasise/seam/rest.py` — `CompareRequest`, `POST /compare`
- `databasise/mcp/tools.py` — `CompareToolArgs`, `TOOL_NAMES` grown to six
- `databasise/mcp/server.py` — `compare` tool registration
- `databasise/tests/seam/test_rest_transport.py` — `_REFUSAL_FACTORIES` entries for the two new refusal types
- `databasise/tests/mcp/test_tool_growth_invariant.py` — pinned counts updated to six, `_OPERATION_TO_TOOLS` gained `compare`, the retired compare-is-absent assertion replaced with one asserting the current (present-in-`TOOL_NAMES`) state
- `databasise/tests/mcp/test_dual_transport_parity.py` — pinned count updated to six, a `compare` scenario added to the per-tool three-way sweep
- `.planning/phases/05-opaque-side-admission/COVERAGE.md` — `compare` row moved from the deliberately-absent table into the §18.5 operations table
- `.planning/phases/06-hipporag-2-side-by-side/COVERAGE.md` — this phase's own §18.5 record
- `databasise/evidence/F-14-SEAM-INVARIANCE.md`, `databasise/tests/evidence/test_f14_record.py`

## Decisions Made

See `key-decisions` in frontmatter. Most load-bearing: the capability-selector key rendering (`+`-joined, caller's own order) is this plan's own declared decision, since §18.4 leaves it unspecified — carried verbatim from the plan's own flagged assumption rather than silently invented mid-implementation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `DuplicateComparisonKeyError` for a selector-key collision**
- **Found during:** Task 1 (writing `compare_arms`)
- **Issue:** The plan's own `<action>` text for Task 1 states "Where two supplied selectors render to the same key, refuse by name rather than silently collapsing them into one entry" — required functionality not covered by any of the seven named `<behavior>` tests.
- **Fix:** Added `DuplicateComparisonKeyError(SeamRefusalError)` to `databasise/seam/refusals.py`, raised by `compare_arms` on a key collision; registered its own REST refusal-mapping factory in `test_rest_transport.py`'s `_REFUSAL_FACTORIES` (Task 2, alongside the plan's own required `EmptyComparisonRequestError` factory) so the subclass-enumerating parity test does not fail loudly for an unregistered refusal type.
- **Files modified:** `databasise/seam/refusals.py`, `databasise/tests/seam/test_rest_transport.py`
- **Verification:** `tests/seam/test_rest_transport.py::test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value[DuplicateComparisonKeyError]` passes.
- **Committed in:** `b05569e` (class), `218dd25` (factory)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Necessary for correctness — the plan's own action text names this refusal explicitly; leaving it unimplemented would have left a silently-collapsing comparison response, exactly the "partial mapping a consumer cannot distinguish from legitimate emptiness" failure mode Task 1's action text calls out for the unsatisfiable-selector case. No scope creep — narrowly scoped to the one behavior the plan's own prose already required.

## Issues Encountered

- **Verify-command ordering gap (not a defect in this plan's own code).** Task 2's literal `<verify>` sequence (`uv sync --extra mcp` after `uv sync --extra rest` already ran) uninstalls `fastapi` — `uv sync --extra X` performs an exact sync, not an additive install — so `uv run --extra mcp pytest -q tests/mcp/ -x -rs` run in that exact order skips `test_dual_transport_parity.py`'s entire module (its own `pytest.importorskip("fastapi")` guard), including this plan's own new `compare` cross-transport parity scenario. This did not trip the plan's own `<fails_when>` condition (not every test in the run reported skipped — `test_tool_growth_invariant.py`'s tests still ran for real), so the literal verify command as written passed. Verified separately, outside the literal sequence, with both extras installed together (`uv sync --extra rest --extra mcp`): the full `tests/mcp/` directory (28 tests, including the new `compare` scenario) passes for real. Flagging this so a future phase's own verify-command authoring is aware `uv sync --extra X` followed by `uv sync --extra Y` does not leave `X` installed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- API-08's comparison surface is live on all three transports and proven against a real two-arm call — 06-08 (the real-corpus side-by-side run) and 06-09 can build directly on `Databasise.compare()` rather than reinventing a fan-out.
- F-14 is discharged for the one pair this project can currently compare (LightRAG's `naive` arm, HippoRAG's base wiring) — as this plan's own Verdict section states, this is not a permanent closure: a future arm (a third modality, or HippoRAG once its own index-side parity run lands) could still surface a genuinely modality-conditioned field gap this run did not observe.
- HippoRAG's index side remains `opaque`/`quarantined` per the taint rule (06-RESEARCH.md) — this plan's comparison exercises HippoRAG's query side only, against pre-seeded stores; the real upstream-package parity run 06-RESEARCH.md recommends (and which would earn HippoRAG's index side `stage` depth) is unchanged by this plan.

## Self-Check: PASSED

- All `key-files.created` verified present on disk.
- `git log --oneline --all | grep -E "b05569e|218dd25|9085fd5"` returns all three commits.
- Every task's `<acceptance_criteria>` re-verified: `databasise/seam/compare.py` contains no `import databasise.seam.engine` and no `RunRecord(` construction; `Databasise.compare`'s one-selector branch returns `self._execute(...)` directly (`grep -n "return await self._execute" databasise/seam/engine.py`); `EmptyComparisonRequestError`'s message contains its own class name; the three targeted `test_compare.py` tests (`test_single_selector_is_a_run`, `test_keyed_by_selector`, `test_no_verdict_leaks`) each pass in isolation; `grep -n 'len(TOOL_NAMES) == 5' databasise/tests/mcp/test_tool_growth_invariant.py databasise/tests/mcp/test_dual_transport_parity.py` prints no lines; `POST /compare`'s body is a single awaited `engine.compare(...)` call and a return; `_REFUSAL_FACTORIES` carries an `EmptyComparisonRequestError` entry; both COVERAGE.md files carry a `compare` row naming both transports; `F-14-SEAM-INVARIANCE.md` exists with a dated header, the F-14 claim quoted verbatim (cross-checked live against `MODEL-RED-TEAM.md`), a findings table with one row per `ResponseEnvelope.model_fields` field each `[code-verified]`-tagged, and an explicit `answer`/`depth_label` field-content-vs-field-set distinction.
- Plan-level `<verification>`: bare `cd databasise && uv run pytest -q` exits 0 (729 passed, 6 skipped); `cd databasise && uv run --extra rest pytest -q` exits 0 (797 passed, 1 skipped); one real comparison call returns two envelopes keyed by the caller's selectors with no verdict/internal identity; `databasise/evidence/F-14-SEAM-INVARIANCE.md` is committed (`9085fd5`).

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-09*
