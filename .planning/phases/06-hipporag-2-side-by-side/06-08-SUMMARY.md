---
phase: 06-hipporag-2-side-by-side
plan: 08
subsystem: rag-engine
tags: [parity, cross-modality, hipporag, lightrag, modal-05, evidence, deferred-run]

# Dependency graph
requires:
  - phase: 06-hipporag-2-side-by-side
    plan: "06-03"
    provides: "Databasise.compare() — API-08's fan-out over the seam's single-arm _execute() path, used unmodified by run_cross_modality.py"
  - phase: 06-hipporag-2-side-by-side
    plan: "06-07"
    provides: "HippoRAG 2's complete thirteen-position decomposition — the wiring build_hipporag_index.py resolves and runs"
provides:
  - "databasise/parity/build_hipporag_index.py — build_index()/IndexBuildResult, a build-then-verify-then-report harness for HippoRAG's real index build, written but never invoked"
  - "databasise/parity/run_cross_modality.py — run_cross_modality()/preflight()/CrossModalityRecord, a pre-flight-then-compare harness for the real two-arm run, written but never invoked"
  - "databasise/evidence/CROSS-MODALITY-EVIDENCE.md — MODAL-05 recorded honestly as BLOCKED, not discharged, mirroring FALSIFIER-5-EVIDENCE.md's house format"
affects: []

# Actuals (#2632)
actuals:
  tokens: 14038
  tasks: 3
  commits: 3
plan_head_before: 8a60f06d8c0f66bcfd83fce8e2de160053f32103

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "House-format BLOCKED evidence record, second application: FALSIFIER-5-EVIDENCE.md's shape (dated header, verbatim claim quote, findings table, owner-decision section, method-and-limits, entry criterion, Next Phase Readiness) applied to a second, independently-unrun requirement (MODAL-05) for an unrelated blocking cause (unauthorized real spend vs. an unresolved judge identity/unbudgetable ingest)."
    - "Harness written to genuine runnable completeness under an explicit non-execution mandate — the code mirrors every real precondition (env-key assertion, index-presence assertion, post-build verification) a live run would need, with zero shortcuts taken because the run itself is deferred."

key-files:
  created:
    - databasise/parity/build_hipporag_index.py
    - databasise/parity/run_cross_modality.py
    - databasise/tests/parity/test_cross_modality_isolation.py
    - databasise/evidence/CROSS-MODALITY-EVIDENCE.md
    - databasise/tests/evidence/test_cross_modality_record.py
  modified: []

key-decisions:
  - "Owner decision at Task 1's gate=\"blocking-human\" spend checkpoint: defer-and-record-blocked. No real HippoRAG index build or cross-modality comparison executes in this plan — no LLM calls, no embedding calls, no ingestion, no spend. Both build_hipporag_index.py and run_cross_modality.py are written as genuine, reviewable, runnable code and committed unexecuted."
  - "Task 2 and Task 3's acceptance criteria adapted to the deferred reality, per the owner-authorized deviation: test_cross_modality_isolation.py's real-index tests are skip-guarded (they skip on every machine today, since no real HippoRAG index exists) with synthetic-store tests exercising the harness's own isolation logic instead; CROSS-MODALITY-EVIDENCE.md is written as a BLOCKED record (one blocker, no real-run numbers) rather than a passing-shape record of two real per-query comparisons."
  - "MODAL-05 stays Pending in .planning/REQUIREMENTS.md — this plan discharges the runnable harnesses and the honest blocked-record, not the cross-modality proof itself. No requirements.mark-complete call was made for MODAL-05 in this plan's state-update step."
  - "The index-recipe hash artifacts_overlap is computed against, is the resolved wiring's own canonicalise() hash pre-query-injection (structural identity only) — not derived via namespaces.py's full derive_namespace() eight-input scheme, since no per-query call site in this codebase computes a standalone 'index recipe' hash today; this plan's own pragmatic choice, stated in run_cross_modality.py's own docstring."

patterns-established:
  - "A deferred-spend plan can still land a genuinely complete, reviewable artifact: the harness code, written to the same standard as if it were about to run for real, is the actual deliverable when the run itself is the withheld decision."

requirements-completed: []

coverage:
  - id: D1
    description: "databasise/parity/build_hipporag_index.py written as genuine, runnable code (build-then-verify-then-report, adopting 03-11-PLAN.md's empty-extraction guard) — never invoked, per the owner's defer-and-record-blocked decision"
    requirement: MODAL-05
    verification: []
    human_judgment: true
    rationale: "No real invocation exists to verify against — the deliverable is the harness's own written correctness, which a human should read against Task 1's own acceptance criteria (precondition assertions, post-build verification, token-spend-from-accounting) rather than a test asserting on a run that did not happen."
  - id: D2
    description: "databasise/parity/run_cross_modality.py's own isolation logic (directory-disjointness, artifacts_overlap as a genuine iff, a cross-read negative control) verified against synthetic, hand-seeded stores — no real corpus, no network, no spend"
    requirement: MODAL-05
    verification:
      - kind: unit
        ref: "tests/parity/test_cross_modality_isolation.py#test_directories_disjoint_check_against_synthetic_seeded_stores"
        status: pass
      - kind: unit
        ref: "tests/parity/test_cross_modality_isolation.py#test_artifacts_overlap_is_false_for_the_two_structurally_different_recipes"
        status: pass
      - kind: unit
        ref: "tests/parity/test_cross_modality_isolation.py#test_artifacts_overlap_is_true_for_two_identical_recipe_hashes"
        status: pass
      - kind: integration
        ref: "tests/parity/test_cross_modality_isolation.py#test_cross_read_negative_control_against_synthetic_seeded_stores"
        status: pass
    human_judgment: false
  - id: D3
    description: "databasise/evidence/CROSS-MODALITY-EVIDENCE.md — MODAL-05 recorded honestly as BLOCKED, structurally verified: names the one blocker, the owner's decision, the entry criterion, and never reports a real-run number"
    verification:
      - kind: unit
        ref: "tests/evidence/test_cross_modality_record.py (11 passed)"
        status: pass
    human_judgment: false

# Metrics
duration: ~55min
completed: 2026-09-09
status: complete
---

# Phase 6 Plan 8: MODAL-05 Cross-Modality Run — Harnesses Built, Real Run Deferred (BLOCKED, Not Discharged)

**Both the HippoRAG index-build harness and the cross-modality comparison harness landed as genuine, runnable code against every real precondition a live run would need, but the owner deferred the one real invocation that requires live spend — so MODAL-05, this milestone's own core-value proof point, is recorded honestly as BLOCKED rather than passed, failed, or silently skipped.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-09
- **Completed:** 2026-09-09
- **Tasks:** 3 of 3 planned tasks executed as code (all three landed; none executed a real invocation)
- **Files modified:** 5 (all new)

## Accomplishments

- `databasise/parity/build_hipporag_index.py`: `build_index()`, `IndexBuildResult` — a build-then-verify-then-report harness in `import_index.py`'s own shape. Loads the committed Phase 3 parity corpus, resolves HippoRAG 2's base wiring, injects the corpus documents onto `chunk-embed`'s `config["documents"]` and a real token allowance onto every node, builds real clients from `v1/.env.parity`, and runs the wiring through `runner.scheduler.run_wiring` directly. Adopts 03-11-PLAN.md's own guard against a silently-empty extraction pass: refuses to report success unless the graph namespace holds non-zero node/edge counts (with at least one `entity:`- and one `chunk:`-prefixed vertex present) and the entity/fact vector namespaces hold non-zero entries. Reads token spend from the run's own node-trace accounting via `assemble_token_breakdown`, never an estimate.
- `databasise/parity/run_cross_modality.py`: `run_cross_modality()`, `preflight()`, `CrossModalityRecord` — a pre-flight-then-compare harness in `run_comparison.py`'s own shape. Pre-flight (in order): both arms' indexes present and non-empty at their own declared namespaces; the two arms' resolved store directories disjoint; `artifacts_overlap` between the two arms' index-recipe hashes recorded (never used to gate — an unexpected `True` is a human-judgment finding, not an automatic refusal). Then runs the corpus's own queries through one `Databasise.compare()` call per query, collecting each arm's envelope field set, item count, and honesty-invariant fields — refusing (`DegradedCrossModalityRunError`) if either arm reports `partial` or `degraded` on any query.
- `databasise/tests/parity/test_cross_modality_isolation.py`: two tests against the real built indexes, guarded by a pure path-existence check (`_real_hipporag_index_present()` — never constructs a store, so collecting the module never mutates the real parity store) and confirmed to skip cleanly on this machine, since no real HippoRAG index exists yet. Four synthetic-store tests exercise the identical isolation logic with hand-seeded stores: directories disjoint, `artifacts_overlap` false for the two real structurally-different recipes, `artifacts_overlap` true for two identical hashes (proving the false result above is not vacuous), and a cross-read negative control (seeding one arm's graph namespace leaves the other's empty, in both directions).
- `databasise/evidence/CROSS-MODALITY-EVIDENCE.md`: an honest BLOCKED record mirroring `FALSIFIER-5-EVIDENCE.md`'s house format — MODAL-05's claim quoted verbatim, one blocker named precisely (one real, unauthorized invocation against live `v1/.env.parity` credentials, against the 20-document Phase 3 parity corpus), the owner's `defer-and-record-blocked` decision recorded, the entry criterion for the deferred run stated, and no count/spend/duration/comparison-result number reported anywhere.
- `databasise/tests/evidence/test_cross_modality_record.py`: 11 structural tests pinning the BLOCKED shape — parses the document's own front matter and section structure (never a whole-file grep), asserting the claim is quoted verbatim, the status states BLOCKED/not-discharged, no fabricated result field appears, the findings table has exactly one blocker row, the owner decision and entry criterion are both named, and MODAL-05 stays Pending in the Limits section.
- Full suite: `uv run --extra rest --extra mcp pytest -q` → 901 passed, 3 skipped (up from the 886/1 baseline by exactly this plan's own 15 new tests — 4 synthetic isolation tests + 11 structural evidence tests — plus 2 newly-skipped real-index tests), zero regressions.

## Task Commits

Each task was committed atomically:

1. **Task 1: Build HippoRAG's index over the Phase 3 parity corpus, for real** — `c0b5845` (feat) — written, not invoked
2. **Task 2: One query, both arms, and the isolation the run makes observable** — `fc1a01c` (feat)
3. **Task 3: The MODAL-05 evidence record** — `b58fdf3` (test)

## Files Created/Modified

- `databasise/parity/build_hipporag_index.py` - `build_index()`, `IndexBuildResult`, `_inject_documents`, `_assert_preconditions`, `MissingParityLightRAGIndexError`, `HippoRAGIndexBuildRefusedError`
- `databasise/parity/run_cross_modality.py` - `run_cross_modality()`, `preflight()`, `CrossModalityRecord`, `CrossModalityQueryRecord`, `ArmQueryResult`, `PreflightResult`, `MissingArmIndexError`, `OverlappingStoreDirectoriesError`, `DegradedCrossModalityRunError`
- `databasise/tests/parity/test_cross_modality_isolation.py` - real-index tests (skip-guarded) + four synthetic-store isolation-logic tests
- `databasise/evidence/CROSS-MODALITY-EVIDENCE.md` - the MODAL-05 BLOCKED record
- `databasise/tests/evidence/test_cross_modality_record.py` - 11 structural tests pinning the BLOCKED shape

## Decisions Made

See `key-decisions` in frontmatter. Most load-bearing: the owner's `defer-and-record-blocked` decision at Task 1's own `gate="blocking-human"` spend checkpoint — the checkpoint that raised it is not re-presented here; it was resolved before this continuation began (see the continuation prompt's own `<continuation_state>` for the exact prior turn).

## Deviations from Plan

### Owner-Authorized Deviations

**1. [Owner-directed — not a Rule 1-4 auto-fix] Task 1's real index build not executed; Task 2/Task 3 adapted to the deferred reality**
- **Found during:** Task 1's own `<precondition>` gate (one real HippoRAG index build against the 20-document Phase 3 parity corpus, requiring live `v1/.env.parity` credentials)
- **Issue:** Task 1's action text required actually running the index build and recording its observed counts, spend, and duration in this SUMMARY. Task 2's action text required running a real two-arm comparison against that built index. Task 3's action text required a passing-shape evidence record built from those two real runs.
- **Resolution:** A prior turn of this continuation presented the spend checkpoint as `gate="blocking-human"` (never auto-approved, even under `--auto`, per the executor's own precondition-unmet protocol). The owner selected `defer-and-record-blocked`: write both harnesses to genuine, reviewable completeness; run neither for real; adapt Task 2's own test file to skip cleanly against the real (absent) index while still testing the harness's own isolation logic against synthetic stores; adapt Task 3's evidence record to the BLOCKED shape `FALSIFIER-5-EVIDENCE.md` already established, rather than the passing-shape record the plan's literal text describes.
- **Files modified:** all five files listed above
- **Verification:** `uv run --extra rest --extra mcp pytest -q` (901 passed, 3 skipped); `uv run pytest -q tests/parity/test_cross_modality_isolation.py -rs` (4 passed, 2 skipped); `uv run pytest -q tests/evidence/test_cross_modality_record.py -x` (11 passed)
- **Committed in:** `c0b5845`, `fc1a01c`, `b58fdf3`

---

**Total deviations:** 1 owner-authorized (the entire plan's real-run scope deferred; harness-writing and structural-testing scope unaffected).
**Impact on plan:** MODAL-05 — this phase's own core-value proof point — is not discharged by this plan. No fabricated or simulated real-run number exists anywhere in the committed code or evidence record. The blocked state is fully explicit and machine-checked (`test_cross_modality_record.py` fails if the document ever silently claims a real-run result; `test_cross_modality_isolation.py`'s skip guard is a pure path check, never a store construction that would mutate the real parity store as a side effect of merely running the test suite).

## Issues Encountered

None beyond the checkpoint itself, which is documented above as an owner-authorized deviation rather than an issue.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **The real cross-modality run is deferred, not abandoned.** Its entry criterion is owner authorization of one real invocation of `databasise.parity.build_hipporag_index` against the 20-document Phase 3 parity corpus using live `v1/.env.parity` credentials (`qwen/qwen3.7-flash` extraction, `qwen/qwen3-embedding-8b` embedding), followed by one real invocation of `databasise.parity.run_cross_modality`. Both harnesses need no further code changes to accept that run's data.
- **MODAL-05, this phase's own core-value requirement, remains unproven** until the real run happens — `.planning/PROJECT.md`'s Core Value statement ("the same corpus, the same seam, N modalities running side-by-side and comparable on the rig") is exactly what that run exists to demonstrate observed rather than asserted.
- **MODAL-05 remains Pending** in `.planning/REQUIREMENTS.md` and is not marked complete by this plan.
- **Falsifier 5/MACH-03 (06-06-PLAN.md) carries the same shape of deferral** for an unrelated cause (unresolved judge identity, unbudgetable eval-corpus ingest, not a HippoRAG index build) — two of this phase's evidence requirements ship blocked, both recorded honestly rather than softened.
- Phase 6's remaining plan (06-09, per `06-01-PLAN.md`'s own phase-level artifact list) can proceed independently of this deferral; nothing in this plan's own scope blocks it.

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-09*

## Self-Check: PASSED

- `databasise/parity/build_hipporag_index.py` — FOUND
- `databasise/parity/run_cross_modality.py` — FOUND
- `databasise/tests/parity/test_cross_modality_isolation.py` — FOUND
- `databasise/evidence/CROSS-MODALITY-EVIDENCE.md` — FOUND
- `databasise/tests/evidence/test_cross_modality_record.py` — FOUND
- Commit `c0b5845` (Task 1) — FOUND in `git log`
- Commit `fc1a01c` (Task 2) — FOUND in `git log`
- Commit `b58fdf3` (Task 3) — FOUND in `git log`
- `uv run --extra rest --extra mcp pytest -q` — 901 passed, 3 skipped
- `uv run pytest -q tests/parity/test_cross_modality_isolation.py -rs` — 4 passed, 2 skipped
- `uv run pytest -q tests/evidence/test_cross_modality_record.py -x` — 11 passed
- `.planning/REQUIREMENTS.md` MODAL-05 row confirmed still reads `Pending` (not modified by this plan)
