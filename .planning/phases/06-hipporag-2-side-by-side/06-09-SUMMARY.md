---
phase: 06-hipporag-2-side-by-side
plan: 09
subsystem: rag-engine
tags: [f-07, mach-10, mutable-store, refusal, evidence, requirements-closeout, stack-supersession]

# Dependency graph
requires:
  - phase: 06-hipporag-2-side-by-side
    plan: "06-03"
    provides: "Databasise.compare() — API-08's fan-out over the seam's single-arm _execute() path, the comparison path this plan adds the mutable-store refusal into"
  - phase: 06-hipporag-2-side-by-side
    plan: "06-07"
    provides: "databasise/evidence/HIPPORAG-PORT-RECORD.md — the committed port record this plan extends with a named deferral entry"
  - phase: 06-hipporag-2-side-by-side
    plan: "06-06"
    provides: "databasise/evidence/FALSIFIER-5-EVIDENCE.md — MACH-03's BLOCKED record, cited by this plan's REQUIREMENTS.md annotation"
  - phase: 06-hipporag-2-side-by-side
    plan: "06-08"
    provides: "databasise/evidence/CROSS-MODALITY-EVIDENCE.md — MODAL-05's BLOCKED record, cited by this plan's REQUIREMENTS.md annotation"
provides:
  - "databasise/evidence/f07_report.py — render_f07_record(), a pure function of default_registry() plus two catalogued-not-built roster entries; MACH-10/F-07's discharge record"
  - "databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md — the committed, byte-identical F-07 disposition record"
  - "databasise.seam.refusals.MutableStoreComparisonExcludedError — the explicit refusal §14.4 point 3 requires, wired into Databasise.compare()"
  - "The phase's closing record: HIPPORAG-PORT-RECORD.md's named deferred-measurement entry, STACK.md's corrected-in-place vector-store recommendation, and all six Phase 6 requirement rows annotated against committed evidence"
affects: []

# Actuals (#2632)
actuals:
  tokens: 22829
  tasks: 3
  commits: 3
plan_head_before: a593af6738edbc5cf418313079eaf1cdf14a7d1a

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Render-from-committed-inputs for an evidence record (second application, after parity_report.py): render_f07_record() is a pure function of default_registry() plus a fixed catalogued-not-built table, and the committed .md file is required to be byte-identical to its own output — a second run of the discharge is not a second finding"
    - "Test-scoped candidate-pool monkeypatch to drive a real, committed wiring file through the real selector-resolution code path without a production code change — used because databasise/wirings/codebase-memory-mcp.json is not in the production candidate pool (WIRING_NAMES) today, and adding it there would be an out-of-scope architectural change (making a dev tool comparable as a query-answering modality)"

key-files:
  created:
    - databasise/evidence/f07_report.py
    - databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md
    - databasise/tests/evidence/test_f07_record.py
    - databasise/tests/seam/test_mutable_store_exclusion.py
  modified:
    - databasise/seam/refusals.py
    - databasise/seam/engine.py
    - databasise/tests/seam/test_rest_transport.py
    - databasise/evidence/HIPPORAG-PORT-RECORD.md
    - .planning/REQUIREMENTS.md
    - .planning/research/STACK.md

key-decisions:
  - "Enumerating mutable-store components from default_registry() itself (as the plan's own action text requires) surfaced a fourth real component, lightrag/full-delete@0.1.0, that MODEL-RED-TEAM.md's frozen three-entry roster (CA-2/MC-1/CA-7) does not name at all — recorded explicitly in the F-07 record as exactly the kind of gap a hand list would miss, given the same permanent-exclusion disposition as codebase-memory-mcp."
  - "Discovered that databasise/wirings/codebase-memory-mcp.json is not resolvable through any of §18.4's four production selectors today (databasise/wirings/resolve.py's WIRING_NAMES names only lightrag/hipporag) — contrary to the plan's own read_first framing ('now reachable through the candidate pool'). Recorded as a code-verified fact in the F-07 record rather than silently treated as true; Task 2's own test drives the real wiring via a test-scoped monkeypatch of the capability selector's candidate pool rather than a production WIRING_NAMES change, since adding a dev-tool engine to the modality candidate pool is an architectural decision outside this plan's scope."
  - "MACH-10 stays Pending in REQUIREMENTS.md, not Complete, mirroring Task 1's own <verify><human-check> instruction ('MACH-10 is not marked Complete... until this confirmation is recorded') and 06-08-SUMMARY.md's identical precedent for MODAL-05: no requirements.mark-complete call was made for MACH-10 in this plan's state-update step, and requirements-completed is left empty in this frontmatter rather than copying [MACH-10] verbatim, since the plan's own frontmatter naming a requirement is not the same as that requirement actually completing."
  - "lightrag/full-delete@0.1.0's exclusion is recorded as a structural fact (never routed through resolve_selector()'s candidate pool at all) rather than an enforced refusal the way codebase-memory-mcp's is — MutableStoreComparisonExcludedError has no live code path to guard for this component today, stated plainly in the F-07 record rather than implied to be equivalent to the enforced case."

requirements-completed: []

coverage:
  - id: D1
    description: "Every mutable-store component in default_registry() (codebase-memory-mcp@0.1.0, lightrag/full-delete@0.1.0) plus MODEL-RED-TEAM.md's two catalogued-not-built roster entries (MC-1, CA-7) is named in the F-07 record with exactly one admissible disposition and a non-empty reason; an empty enumeration is refused, not rendered; re-rendering is byte-identical"
    requirement: MACH-10
    verification:
      - kind: unit
        ref: "tests/evidence/test_f07_record.py (11 passed)"
        status: pass
    human_judgment: true
    rationale: "Task 1's own <verify><human-check> requires the owner's confirmation that codebase-memory-mcp's permanent-exclusion disposition matches their intent before MACH-10 is marked Complete — not yet recorded. The automated tests prove the record's structural correctness (completeness, byte-identical rendering, admissible dispositions); they cannot substitute for the owner's own judgment on the disposition itself."
  - id: D2
    description: "Databasise.compare() refuses a comparison whose selectors resolve a mutates_store-declaring wiring, before any arm executes, naming only the excluded component; a single-selector run and a comparison between two non-mutable wirings are both unaffected"
    requirement: MACH-10
    verification:
      - kind: unit
        ref: "tests/seam/test_mutable_store_exclusion.py (5 passed)"
        status: pass
      - kind: integration
        ref: "tests/seam/test_rest_transport.py::test_every_refusal_subclass_maps_to_a_non_success_status_carrying_its_named_value[MutableStoreComparisonExcludedError]"
        status: pass
      - kind: integration
        ref: "tests/seam/ full directory, --extra rest (185 passed, 1 skipped)"
        status: pass
    human_judgment: false
  - id: D3
    description: "HIPPORAG-PORT-RECORD.md's Limits section names the deferred upstream-package parity measurement with a trigger; STACK.md's stale LanceDB recommendation is corrected in place, never deleted; all six Phase 6 requirement rows carry a dated annotation naming committed evidence, with MACH-03/MODAL-05/MACH-10 staying Pending against their own named outstanding item"
    verification:
      - kind: other
        ref: "grep -c lancedb .planning/research/STACK.md == 10 (non-zero, corrected in place)"
        status: pass
      - kind: unit
        ref: "cd databasise && uv run pytest -q (918 passed, 3 skipped)"
        status: pass
    human_judgment: true
    rationale: "Whether each requirement row's prose annotation honestly reflects what its cited evidence document actually establishes (rather than rounding a partial result up) is a judgment call about accuracy of representation that no automated test asserts on — the same class of check Phase 5's own lesson (five never-defective rows reverted en masse) was about."

# Metrics
duration: ~70min
completed: 2026-09-10
status: complete
---

# Phase 6 Plan 9: F-07/MACH-10 Discharged — Explicit Refusal, and the Phase's Record Closed Summary

**Every mutable-store component in this project's live registry — including a fourth, unrosterred component (`lightrag/full-delete@0.1.0`) the frozen red-team review never named — now carries exactly one recorded disposition, `codebase-memory-mcp`'s exclusion is enforced by a real, tested refusal in `Databasise.compare()`, and the phase's own closing record (the deferred HippoRAG parity measurement, the stale LanceDB recommendation, and all six Phase 6 requirement statuses) is reconciled against committed evidence rather than against the fact that the plans ran.**

## Performance

- **Duration:** ~70 min
- **Started:** 2026-09-10
- **Completed:** 2026-09-10
- **Tasks:** 3
- **Files created/modified:** 10

## Accomplishments

- `databasise/evidence/f07_report.py`: `render_f07_record()` — a pure function of `default_registry()` plus two fixed catalogued-not-built roster entries (`MC-1`, `CA-7`), following `parity_report.py`'s own render-from-committed-inputs convention; raises rather than silently rendering an empty table if the enumeration is empty, and raises if it finds a `mutates_store` component it has no named disposition reason for
- Live enumeration found **two** real registered mutable-store components, not the one the plan's own prior-wave context implied: `codebase-memory-mcp@0.1.0` (`CA-2`) and `lightrag/full-delete@0.1.0` — a fourth component `MODEL-RED-TEAM.md`'s own three-entry roster never names, discovered precisely because this record computes its population from the registry itself rather than transcribing the frozen roster. Both given `permanent-exclusion`, on `06-RESEARCH.md`'s own recommended grounds
- `databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md`: the committed record, verified byte-identical to `render_f07_record()`'s own output; quotes `CONTRACT.md §14.4` point 3 and the `MODEL-RED-TEAM.md` F-07 finding verbatim; records the write-quiesce caveat (06-RESEARCH's assumption A5) as **not established**, and states plainly that the interrupted-mid-snapshot and concurrent-touch questions are structurally moot under the `permanent-exclusion` disposition actually adopted (neither a snapshot nor a reset ever runs)
- `databasise.seam.refusals.MutableStoreComparisonExcludedError`: a `SeamRefusalError` subclass naming only the excluded component's own `name@version` and pointing at the F-07 record. `Databasise.compare()` resolves every selector up front (two-or-more-selector comparisons only — a single selector is a run, not a comparison, per RIG §RUN.3) and raises before `compare_arms` is ever called if any resolved wiring's declared effect union (via `selectors.py`'s own `_wiring_effects` — no second computation) contains `mutates_store`
- **A real discrepancy surfaced and recorded, not silently worked around:** `databasise/wirings/codebase-memory-mcp.json` is **not** resolvable through any of §18.4's four production selectors today — `databasise/wirings/resolve.py`'s `WIRING_NAMES` names only `("lightrag", "hipporag")`. The plan's own read_first material assumed this wiring was "now reachable through the candidate pool"; it is not. `databasise/tests/seam/test_mutable_store_exclusion.py` drives the real wiring and the real registered `Part` through a real `Databasise.compare()` call anyway, via a test-scoped `monkeypatch` of the capability selector's own candidate pool — never a production code change, since widening the production candidate pool to include a non-modality dev tool is an architectural decision outside this plan's scope
- `databasise/evidence/HIPPORAG-PORT-RECORD.md`: Limits section extended with a named deferral entry (what it consists of, what it would buy, why it is deferred, its trigger, and the upstream package's own alpha-status risk to that future measurement)
- `.planning/research/STACK.md`: a dated supersession note naming Cozo/Faiss as the shipped defaults, added at the top of the document; every LanceDB row corrected in place (never deleted — `grep -c lancedb` still returns 10); line 85's `nano-vectordb` replacement claim now names Faiss
- `.planning/REQUIREMENTS.md`: all six Phase 6 rows (MACH-02, MACH-03, MODAL-04, MODAL-05, API-08, MACH-10) carry a dated annotation naming the committed evidence document that establishes their status. MACH-03 and MODAL-05 stay Pending with their own outstanding precondition named; MACH-10 stays Pending pending the owner's own confirmation of the `codebase-memory-mcp` disposition
- Full suite: `uv run pytest -q` (bare), `uv run --extra rest pytest -q`, and `uv run --extra rest --extra mcp pytest -q` all report **918 passed, 3 skipped** — up from the 901/3 baseline by exactly this plan's own 17 new tests (11 `test_f07_record.py` + 5 `test_mutable_store_exclusion.py` + 1 `_REFUSAL_FACTORIES` entry exercised by the existing parametrized `test_rest_transport.py` test), zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Enumerate every mutable-store component and give each exactly one disposition** — `36559d3` (feat)
2. **Task 2: The explicit refusal §14.4 requires, in the comparison path** — `a07d014` (feat)
3. **Task 3: Close the record — deferred measurement, stale docs, and per-requirement status** — `d0421f0` (docs)

## Files Created/Modified

- `databasise/evidence/f07_report.py` — `render_f07_record()`, `DISPOSITION_PERMANENT_EXCLUSION`, `DISPOSITION_SNAPSHOT_RESET_DEFINED`
- `databasise/evidence/F-07-MUTABLE-STORE-DISPOSITION.md` — the committed F-07 record
- `databasise/tests/evidence/test_f07_record.py` — structural assertions over the record
- `databasise/seam/refusals.py` — `MutableStoreComparisonExcludedError`
- `databasise/seam/engine.py` — `Databasise.compare()`'s pre-execution mutable-store check, `_mutates_store_component()`
- `databasise/tests/seam/test_mutable_store_exclusion.py` — the `<behavior>` block's five tests
- `databasise/tests/seam/test_rest_transport.py` — `_REFUSAL_FACTORIES` entry for the new refusal
- `databasise/evidence/HIPPORAG-PORT-RECORD.md` — named deferral entry for the upstream-package parity measurement
- `.planning/REQUIREMENTS.md` — six Phase 6 rows annotated
- `.planning/research/STACK.md` — LanceDB recommendation corrected in place

## Decisions Made

See `key-decisions` in frontmatter. Most load-bearing: enumerating from the registry itself (as instructed) surfaced `lightrag/full-delete@0.1.0` as a fourth mutable-store component MODEL-RED-TEAM.md's roster never named, and separately surfaced that `codebase-memory-mcp`'s own wiring is not reachable through any production selector today — both recorded plainly rather than smoothed over to match the plan's own prior assumptions.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `databasise/evidence/f07_report.py` added as a new file, not in the plan's `files_modified` list**
- **Found during:** Task 1
- **Issue:** The plan's own Artifacts section names `render_f07_record` as a symbol this plan creates, and Task 1's own acceptance criteria require a test asserting re-rendering reproduces the document byte-identically — both require a real, importable, pure-function module. No such module is named in the plan's `files_modified` frontmatter list.
- **Fix:** Added `databasise/evidence/f07_report.py`, mirroring `databasise/evidence/parity_report.py`'s own render-from-committed-inputs shape, as the natural home for `render_f07_record()`.
- **Files modified:** `databasise/evidence/f07_report.py` (new)
- **Verification:** `render_f07_record(default_registry())` output verified byte-identical to the committed `.md` file before it was written; `tests/evidence/test_f07_record.py`'s own byte-identical re-render test passes.
- **Committed in:** `36559d3` (Task 1)

**2. [Rule 3 - Blocking] `databasise/tests/seam/test_mutable_store_exclusion.py` drives the real wiring via a test-scoped candidate-pool monkeypatch, not `WIRING_NAMES`**
- **Found during:** Task 2, writing the `<behavior>` tests
- **Issue:** The plan's own read_first framed `databasise/wirings/codebase-memory-mcp.json` as "now reachable through the candidate pool" — it is not (see Accomplishments). Adding `"codebase-memory-mcp"` to `databasise/wirings/resolve.py`'s `WIRING_NAMES` does not even work mechanically (`load_wiring()` expects a per-modality `<name>/base.json` subdirectory layout the committed file does not use), and doing so anyway would be an architectural change (making a non-modality dev-tool engine reachable as a comparable query modality) outside this plan's scope and files_modified list.
- **Fix:** The test file's own `cbm_reachable` fixture reads the real, committed wiring JSON directly and appends it to `selectors.py`'s own `_capability_candidates()` pool via `monkeypatch`, for the duration of each test that needs it only — the real wiring content and the real registered `Part`'s declared effects are what the refusal check operates on, with zero production code change.
- **Files modified:** `databasise/tests/seam/test_mutable_store_exclusion.py`
- **Verification:** All 5 tests pass; `test_comparison_between_two_non_mutable_wirings_is_unaffected` runs with no `cbm_reachable` fixture at all, proving production behavior (where `codebase-memory-mcp` stays unreachable) is unaffected by this plan's own change.
- **Committed in:** `a07d014` (Task 2)

---

**Total deviations:** 2 auto-fixed (both Rule 3 — blocking issues necessary to satisfy the plan's own stated acceptance criteria; no scope creep, no architectural change made).
**Impact on plan:** Both deviations are additive test/evidence infrastructure required by the plan's own text; neither touches production selector-resolution behavior for any existing caller.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **MACH-10 stays Pending**, not Complete — the F-07 disposition record and its enforcing refusal are both landed and tested, but Task 1's own `<verify><human-check>` requires the owner's confirmation that `codebase-memory-mcp`'s permanent-exclusion disposition matches their intent, which is not yet recorded. This will be harvested into the phase's UAT flow per `workflow.human_verify_mode = end-of-phase`.
- **MACH-03 and MODAL-05 remain Pending, as they were before this plan** — this plan did not attempt to discharge either; it only annotated their REQUIREMENTS.md rows against the evidence 06-06/06-08 already committed. Two of this phase's six evidence requirements ship BLOCKED (`FALSIFIER-5-EVIDENCE.md`, `CROSS-MODALITY-EVIDENCE.md`), both honestly recorded rather than softened.
- **Phase 6 is otherwise closed.** MODAL-04 and API-08 are Complete with dated annotations; MACH-02 is Complete with a dated annotation. The comparison surface (API-08) is proven and now also enforces §14.4 point 3's mutable-store exclusion. HippoRAG 2's thirteen-position decomposition (MODAL-04) is complete, with its own deferred parity measurement now tracked with a trigger rather than left as an absence.
- **This was the phase's last plan** (`06-01-PLAN.md`'s own phase-level artifact list). Phase 6 is ready for `/gsd-verify-work 6`.

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-10*

## Self-Check: PASSED

- All `key-files.created` verified present on disk via `[ -f ]`.
- `git log --oneline --all | grep -E "36559d3|a07d014|d0421f0"` returns all three commits.
- Every task's `<acceptance_criteria>` re-verified: `F-07-MUTABLE-STORE-DISPOSITION.md` exists with a dated header and quotes §14.4 point 3 and the F-07 finding verbatim; its table names all three `MODEL-RED-TEAM.md` roster entries (`CA-2`, `MC-1`, `CA-7`) each with one disposition and a non-empty reason; `test_f07_record.py` asserts the enumerated set equals the live `mutates_store` set (11 tests, all passing, including the empty-table-is-refused test and the byte-identical re-render test); `MutableStoreComparisonExcludedError` is a `SeamRefusalError` subclass whose message contains its own class name and the excluded component's `name@version`; `Databasise.compare()` computes the effect union via `selectors.py`'s `_wiring_effects` and defines no second computation (`grep -n "_wiring_effects" databasise/seam/engine.py` shows exactly one call site); `_REFUSAL_FACTORIES` carries a `MutableStoreComparisonExcludedError` entry; `grep -c lancedb .planning/research/STACK.md` returns 10 (non-zero).
- Plan-level `<verification>`: `cd databasise && uv run pytest -q` exits 0 (918 passed, 3 skipped); `cd databasise && uv run --extra rest pytest -q` exits 0 (918 passed, 3 skipped); `F-07-MUTABLE-STORE-DISPOSITION.md` is committed and re-renders byte-identically (verified via direct `diff` before writing the committed file, and via the test suite's own assertion); no Phase 6 requirement row is marked Complete without a committed evidence document named in its annotation (MACH-02, MODAL-04, API-08 cite their own evidence; MACH-03, MODAL-05, MACH-10 stay Pending with their own outstanding item named).
