---
phase: 03-lightrag-query-side
plan: 07
subsystem: rag-engine
tags: [lightrag, parity, subprocess, kendall-tau, variance-band, keyword-pinning, statistics]

# Dependency graph
requires:
  - phase: 03-02
    provides: "v1 parity environment (v1/.env.parity, v1/README-PARITY.md), hash-verified corpus snapshot, verified read-and-reinsert import of v1's built index into the v2 namespace layout (databasise.parity.import_index)"
  - phase: 03-04
    provides: "databasise/parity/run_arm.py (the decomposed-arm driver and its store/client-assembly helpers), the registered wiring set, resolve_arm"
  - phase: 03-05
    provides: "keywords' pinned-replay mechanism (config['pinned']/config['pinned_output']) — the D-12 injection seam this plan drives"
  - phase: 03-06
    provides: "All eighteen §L.1 positions registered; the unpatched base and all five arms parse clean"
provides:
  - "databasise/parity/v1_driver_script.py — the subprocess entry point run by v1's own pinned interpreter, driving v1's existing QueryParam.hl_keywords/ll_keywords seam"
  - "databasise/parity/v1_arm.py — the harness-side subprocess driver, V1ArmResult with an explicit instrumentation='harness-external' marker (D-05)"
  - "databasise/parity/run_comparison.py — the pre-flight index-identity gate, D-12 keyword pinning, the N-run keywords variance band, the deterministic zero-token retrieval-level diff, and main()"
  - "databasise/tests/parity/test_retrieval_parity.py, databasise/tests/parity/test_keyword_variance.py — the deterministic (no-venv, no-network) test group plus one skip-guarded real two-arm run"
  - "A small, documented exclusion in databasise/tools/check_import_boundary.py for subprocess-entry-point leaf scripts (v1_driver_script.py) that intentionally import v1's lightrag package under a different interpreter"
affects: [03-09]

# Actuals (#2632)
actuals:
  tokens: 14000
  tasks: 3
  commits: 3

tech-stack:
  added: []
  patterns:
    - "A subprocess entry point placed under databasise/ but executed by a different interpreter (v1's own venv) needs an explicit, named exclusion in the AST-walking import-boundary checker — self-exclusion-by-resolved-path (the checker's own existing pattern) extended to a small filename-matched set, not a broad carve-out."
    - "A harness-side driver that needs full per-node results (not just a wiring's own `provides` list) reuses an existing arm driver's private store/client-assembly helpers directly rather than duplicating their logic or widening the existing driver's public contract."
    - "A variance band is a dataclass whose to_dict() always carries its own run_count alongside every computed figure — a band figure is meaningless without knowing how many runs it was computed over, so the two travel together structurally, not by convention."
    - "The retrieval-level diff is a pure function of two plain lists — no NodeContext, no client, no store — proven zero-token by grepping the module for clients[\"llm\"]/calls_llm and finding no occurrence anywhere, not merely in the diff function."

key-files:
  created:
    - databasise/parity/v1_driver_script.py
    - databasise/parity/v1_arm.py
    - databasise/parity/run_comparison.py
    - databasise/tests/parity/test_retrieval_parity.py
    - databasise/tests/parity/test_keyword_variance.py
  modified:
    - databasise/tools/check_import_boundary.py
    - databasise/.gitignore

key-decisions:
  - "check_import_boundary.py gained a small, explicitly named _SUBPROCESS_ENTRY_POINT_EXCLUSIONS set (Rule 3 — blocking issue) so v1_driver_script.py's load-bearing `import lightrag` is not flagged: the checker's scan_tree walks every .py file under databasise/ regardless of whether that file is ever imported by anything else under databasise/, and v1_driver_script.py is a leaf subprocess entry point that runs under v1's own interpreter, never Python-imported by databasise/ itself. Mirrors the checker's own pre-existing self-exclusion-by-resolved-path pattern."
  - "run_v1_arm's answer text comes from a second real v1 call (rag.aquery, full generation) alongside rag.aquery_data (context-only, no generation) — v1's own aquery_data forces only_need_context=True internally and never generates a prose answer, but Task 1's V1ArmResult contract requires an `answer` field. Both calls share the same pinned hl_keywords/ll_keywords, so the second call spends no extra keyword-extraction call."
  - "hl_keywords_used/ll_keywords_used in the driver script's JSON are read back from v1's own aquery_data response (data['metadata']['keywords']) — v1's own echo of what it actually used — rather than reflecting the pinned input back on the script's own authority, satisfying Task 1's acceptance criterion that pinning be confirmed in v1's own returned output."
  - "The retrieval-level diff's 'ranking agreement over the intersection' is a Kendall-style pairwise concordance fraction (for every pair of commonly-retrieved ids, do both lists agree on relative order), and 'first disagreement position' is literal position-by-position zip comparison, falling back to the shorter list's length when one is a prefix of the other — both are simple, deterministic, and directly testable against hand-built ranked lists; neither term is specified further in the plan text, and both readings are defensible."
  - "The keywords-node-presence check (has_keywords_node = 'keywords' in resolved arm's nodes) gates both the D-12 pinning step and the entity/relation diffs: naive and bypass have no keywords node and produce no entities/relationships at all (v1's own documented behaviour for those two modes), so their entity_diff/relation_diff are None rather than empty-vs-empty diffs that would read as a coincidental match."
  - "_run_decomposed_arm duplicates run_arm.py's RunRecord-assembly shape (not its store/client helpers, which are imported directly) because run_arm.run_arm() itself only returns the resolved wiring's own `provides` list — for the naive arm, just {'generate': ...} — which cannot supply the rerank/budget-entities/budget-relations node outputs the retrieval-level diff needs. Modifying run_arm.py's public contract was out of this plan's files_modified list and would have widened a plan-03-04 file's scope; a local variant reusing its private assembly helpers was the smaller diff."

patterns-established:
  - "compute_keyword_variance_band(runs) raises SingleRunBandError for len(runs) < 2 — the refusal lives in the pure computation, not scattered across every call site, so any future caller inherits the PITFALLS 2 guard for free."
  - "diff_ranked_ids(decomposed_ids, original_ids) is intentionally reachable with zero I/O — no NodeContext, no clients dict, no store — so the retrieval-level comparison stays provably zero-token by construction, not by convention."

requirements-completed: [MODAL-01]

coverage:
  - id: D1
    description: "The original arm runs on demand from its own pinned v1 environment via a subprocess, accepts pinned keywords through v1's existing hl_keywords/ll_keywords seam with no change to v1, and returns ranked chunk ids, entity/relation ids, and an answer — its trace asymmetry (instrumentation='harness-external') recorded in the data, not only in prose."
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "cd databasise && uv run python -m databasise.tools.check_import_boundary (exit 0)"
        status: pass
      - kind: unit
        ref: "grep -rn '^import v1|^from v1|import lightrag|from lightrag' databasise/parity/v1_arm.py (no matches)"
        status: pass
      - kind: unit
        ref: "V1ArmResult dataclass fields include chunk_ids, answer, instrumentation (verified via __dataclass_fields__ inspection)"
        status: pass
      - kind: unit
        ref: "run_v1_arm(interpreter=<nonexistent path>) raises MissingV1InterpreterError naming the expected path"
        status: pass
      - kind: manual_procedural
        ref: "A real subprocess run against v1's built index with a deliberately distinctive pinned keyword set, confirming v1's own aquery_data echoes it back in metadata.keywords"
        status: unknown
    human_judgment: true
    rationale: "This worktree has no v1/.venv, no v1/.parity_working_dir, and no v1/.env.parity — the same gitignored, worktree-local build-artifact gap 03-04-SUMMARY.md and 03-05-SUMMARY.md both already document for their own real-endpoint acceptance criteria. The code path is written and its refusal/error handling is proven (MissingV1InterpreterError, V1ArmSubprocessError, the import-boundary exclusion); the actual live subprocess round-trip against v1's real index has not been exercised in this session. A human (or a future session on a machine holding the plan 03-02 artifacts) must confirm it."
  - id: D2
    description: "Both arms run from one recorded keyword pair per query (D-12), the keywords variance band carries its own run count and refuses a single-run request, the retrieval-level diff is exact and zero-token, and a failed index-identity precondition yields status=inconclusive with no comparison number recorded."
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "databasise/tests/parity/test_retrieval_parity.py (8 deterministic cases + 1 skip-guarded live case, all passing)"
        status: pass
      - kind: unit
        ref: "databasise/tests/parity/test_keyword_variance.py (7 cases, zero skips)"
        status: pass
      - kind: unit
        ref: "grep -c 'clients\\[\"llm\"\\]|calls_llm' databasise/parity/run_comparison.py returns 0 occurrences anywhere in the module"
        status: pass
      - kind: manual_procedural
        ref: "uv run python -m databasise.parity.run_comparison --arm naive against the real imported index and live endpoints, confirming exit 0 and both a human summary and a JSON path printed"
        status: unknown
    human_judgment: true
    rationale: "Same environment gap as D1 — no real imported index or live endpoints in this worktree. The CLI was exercised for real in this environment (see Issues Encountered): it correctly reports status=inconclusive (index-identity precondition 'refused': no imported store found) and exits 2, distinct from 0 and 1 — proving the harness's own refusal path end to end, but not the clean-pass path, which needs the real index. A human on a machine holding the plan 03-02 artifacts must confirm the clean-pass CLI run."
  - id: D3
    description: "The comparison's arithmetic (diff, band) and its refusals (inconclusive gate, single-run band refusal) are proven deterministically on any machine; the live two-arm run is proven where the environment allows it."
    requirement: "MODAL-01"
    verification:
      - kind: unit
        ref: "cd databasise && uv run pytest -q tests/parity/ -x (46 passed, 4 skipped — all skips environment-dependent)"
        status: pass
      - kind: unit
        ref: "cd databasise && uv run pytest -q (367 passed, 4 skipped — no regressions against the pre-plan baseline)"
        status: pass
    human_judgment: false

duration: ~1h40m
completed: 2026-09-01
status: complete
---

# Phase 3 Plan 07: LightRAG Query Side — The Parity Harness Summary

**The pre-decomposition original driven as a pinned v1 subprocess, `keywords` pinned once per query and fed to both arms, a deterministic zero-token retrieval-level diff (Kendall-style ranking agreement, symmetric difference, first-disagreement position), and an N-run variance band over the one stochastic node — refusing rather than reporting a verdict whenever the index-identity precondition or the run count says the comparison isn't sound.**

## Performance

- **Duration:** ~1h40m
- **Tasks:** 3/3 completed
- **Files modified:** 7 (5 created, 2 modified)

## Accomplishments

- `databasise/parity/v1_driver_script.py`: a dependency-free leaf script executed by v1's own pinned interpreter — builds v1's `LightRAG` facade against the plan 03-02 ingest output using the same env-var-driven D-05/D-07/D-08/amended-D-09 configuration `v1/scripts/run_parity_ingest.py` used to build it, sets `QueryParam(hl_keywords=..., ll_keywords=...)` so v1's own keyword-resolution short-circuit (`v1/lightrag/operate.py:4023-4024`, confirmed live, no change to v1) fires, and returns ranked chunk ids, entity/relation ids, and an answer — with the keywords v1 actually used echoed back from its own `aquery_data` response.
- `databasise/parity/v1_arm.py`: the harness-side subprocess driver, instrumenting the arm from the outside only (wall clock, exit status, captured stderr) — `V1ArmResult.instrumentation` is always `"harness-external"`, carrying D-05's trace asymmetry in the data itself. A missing interpreter or a non-zero subprocess exit both raise named errors carrying enough context to act on, never an empty result.
- A small, documented deviation to `databasise/tools/check_import_boundary.py`: the AST-walking scanner flags every `.py` file under `databasise/` for a forbidden `import lightrag`, with no allowance for a leaf subprocess entry point that is never Python-imported by anything under `databasise/`. Added a filename-matched `_SUBPROCESS_ENTRY_POINT_EXCLUSIONS` set mirroring the checker's own pre-existing self-exclusion pattern.
- `databasise/parity/run_comparison.py`: the parity harness. Runs plan 03-02's index verifier first (a non-`"verified"` result yields `status="inconclusive"` before either arm is touched); pins `keywords` once per query and feeds the recorded pair to both arms; separately runs `keywords` N times live and computes a variance band (per-keyword frequency, mean/spread of list sizes, cache-served marking) that refuses to report for N < 2 (`SingleRunBandError`); computes a deterministic, zero-token retrieval-level diff (symmetric difference, Kendall-style ranking agreement, first-disagreement position) over ranked chunk/entity/relation id lists; and carries the decomposed side's full RIG §TR.1 run record alongside the original arm's harness-external result under distinguishable keys. `main()` drives one arm from a shell with three distinct exit codes (0 clean, 1 runtime error, 2 inconclusive).
- `databasise/tests/parity/{test_retrieval_parity.py,test_keyword_variance.py}`: 15 total cases. The deterministic group (14 cases, zero skip markers) proves the diff arithmetic, the band arithmetic, both refusals, and the precondition gate on any machine; one skip-guarded case proves the full two-arm run against the real imported index and live endpoints.

## Task Commits

1. **Task 1: The original arm — a pinned subprocess, instrumented by the harness** — `6d2cfe8` (feat)
2. **Task 2: The comparison — pinned keywords, deterministic retrieval-level diff, N-run band** — `7e54d7e` (feat)
3. **Task 3: The comparison's own tests** — `ff185ec` (test)

_No plan-metadata commit yet — SUMMARY.md is the orchestrator's post-wave responsibility in worktree mode._

## Files Created/Modified

- `databasise/parity/v1_driver_script.py` — the v1-interpreter subprocess entry point
- `databasise/parity/v1_arm.py` — the harness-side driver, `V1ArmResult`, `run_v1_arm`, `main()`
- `databasise/parity/run_comparison.py` — pre-flight gate, keyword pinning, variance band, retrieval diff, `ComparisonRecord`, `main()`
- `databasise/tests/parity/test_retrieval_parity.py`, `databasise/tests/parity/test_keyword_variance.py` — the test suites
- `databasise/tools/check_import_boundary.py` — the subprocess-entry-point exclusion (deviation)
- `databasise/.gitignore` — added `parity/.comparison_results/` (the CLI's own gitignored runtime output directory)

## Decisions Made

See `key-decisions` in frontmatter for the full list. Highlights: the import-boundary checker exclusion (Rule 3, blocking); `answer` text comes from a second real v1 `aquery` call since `aquery_data` never generates one; pinned-keyword confirmation reads back v1's own `metadata.keywords` echo rather than asserting the script's own input; "ranking agreement" is a Kendall-style pairwise concordance fraction and "first disagreement" is literal position-by-position comparison, both directly testable and not otherwise specified by the plan text; `_run_decomposed_arm` reuses `run_arm.py`'s private assembly helpers rather than widening that file's public contract (out of this plan's `files_modified`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking Issue] `check_import_boundary.py`'s scan flagged `v1_driver_script.py`'s load-bearing `import lightrag`**
- **Found during:** Task 1, first run of the task's own `<verify>` block
- **Issue:** The checker's `scan_tree` walks every `.py` file under `databasise/` for a forbidden `import lightrag`/`import v1` reference, with no distinction between "a file that is itself imported by something under `databasise/`" and "a leaf subprocess entry point that is never Python-imported by anything under `databasise/`, but necessarily imports v1's own package because it runs under v1's own interpreter." `v1_driver_script.py` is exactly the second case (per the plan's own Task 1 text and this file's own module docstring), and the checker had no existing mechanism to distinguish it.
- **Fix:** Added a small, explicitly named `_SUBPROCESS_ENTRY_POINT_EXCLUSIONS` frozenset (currently one entry: `"v1_driver_script.py"`) to `databasise/tools/check_import_boundary.py`, skipped in `scan_tree` by filename — mirroring the checker's own pre-existing self-exclusion-by-resolved-path pattern one function up, and documented in both the module docstring and an inline comment naming exactly why the exception exists and what it does not weaken (nothing under `databasise/` imports v1 either way; the two-way wall stays intact).
- **Files modified:** `databasise/tools/check_import_boundary.py`
- **Verification:** `cd databasise && uv run python -m databasise.tools.check_import_boundary` exits 0; the pre-existing `databasise/tests/test_import_boundary.py` suite (6 tests, unmodified) still passes in full, including `test_1_the_real_package_tree_has_zero_violations_and_main_returns_zero`.
- **Committed in:** `6d2cfe8` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 Rule 3 blocking issue)
**Impact on plan:** Necessary for Task 1's own stated acceptance criterion (`check_import_boundary` exits 0) to be achievable at all, given the plan's explicit instruction to place the driver script under `databasise/parity/` while running under v1's interpreter. No scope creep — the exclusion names exactly one file and changes no other behavior of the checker.

## TDD Gate Compliance

Task 2 (`run_comparison.py`, `tdd="true"`) and Task 3 (the test files, `tdd="true"`) do not follow a strict RED-then-GREEN commit ordering: Task 2's own `<verify>` block (`pytest tests/parity/test_retrieval_parity.py -x`) names a test file Task 3 creates, so the two tasks are structurally interdependent rather than sequential TDD steps. Both were authored and verified together (implementation and tests iterated against each other locally) before either commit landed, then split into two commits matching the plan's own task/file-list structure — `7e54d7e` (Task 2, `feat`, implementation only) followed by `ff185ec` (Task 3, `test`, test files only). No `test(...)` commit precedes `7e54d7e` in git history for this plan. Recorded here per this codebase's own precedent (03-04-SUMMARY.md documents an identical pattern for its own Task 2) rather than silently claimed as a clean RED/GREEN pair.

## Known Stubs

None. Every module delivered here reaches real store/client/subprocess boundaries — `diff_ranked_ids` and `compute_keyword_variance_band` are intentionally pure (zero I/O by design, not as a stub), and every other function either drives a real v1 subprocess, a real decomposed-arm run through the real scheduler, or a real index-identity verification.

## Issues Encountered

- **No real v1 build artifacts in this worktree** (the same gap 03-04-SUMMARY.md, 03-05-SUMMARY.md, and 03-06-SUMMARY.md all already document): `v1/.venv`, `v1/.parity_working_dir`, `v1/.parity_v2_store`, and `v1/.env.parity` are gitignored, worktree-local build products from a different execution session and do not carry over to a freshly spawned parallel worktree. This blocks Task 1's live-subprocess acceptance criterion and Task 2's clean-pass CLI acceptance criterion (see `coverage` D1/D2 above) — both code paths are written correctly and were exercised for their *refusal* behavior instead: `run_v1_arm` with a deliberately broken interpreter path raises `MissingV1InterpreterError` naming the expected path (confirmed manually), and `uv run python -m databasise.parity.run_comparison --arm naive` in this environment correctly reports `status="inconclusive"` (index-identity precondition `"refused"` — no imported v2 store found) and exits `2`, distinct from both `0` and `1` — proving the harness's own refusal path end to end. The clean-pass path needs the real index and is unproven in this session; it resolves itself on any machine holding the plan 03-02 artifacts.
- **`heading_backfill.py`'s hardcoded `chunk-vector` input key (03-06's own flagged caveat) was not hit.** This plan's only real live-run acceptance criterion targets `--arm naive`, whose own patch explicitly overrides `heading-backfill`'s dep to `["chunk-vector"]` — the one arm where the caveat does not apply. `hybrid`/`local`/`global` were not exercised end-to-end in this plan (no real index available to exercise them against regardless), so the caveat remains open for whichever future plan first drives one of those three arms for real, exactly as 03-06-SUMMARY.md's own "Next Phase Readiness" already flagged.
- **"Ranking agreement" and "first disagreement position" are not further specified by the plan text or CONTRACT.md/RIG.md beyond their names.** Implemented as a Kendall-style pairwise concordance fraction (restricted to ids common to both lists) and literal position-by-position comparison respectively — both are simple, deterministic, directly testable against hand-built lists, and behave sensibly at the edge cases (empty lists, fully disjoint lists, one list a prefix of the other), all covered by `test_retrieval_parity.py`'s deterministic group. Recorded as an interpretation, not silently assumed to be the only possible reading.

## User Setup Required

None for the code delivered here. To exercise the live-endpoint paths this plan leaves skip-guarded/manually-verified, a future session needs the same setup 03-04-SUMMARY.md and 03-05-SUMMARY.md already document: plan 03-02's real ingest artifacts (or a re-run) plus `v1/.env.parity` and the `v1/.venv` environment.

## Next Phase Readiness

- `databasise/parity/run_comparison.py`'s `compare_arm_on_query` is ready for plan 03-09's evidence document to call directly (or via `main()`'s CLI) once real artifacts are present — it accepts `verify_fn`/`store_root`/`workspace`/`clients`/`v1_interpreter`/`v1_working_dir` as override points, matching this codebase's established test-injection convention.
- `--arm naive` is the only arm this plan's own acceptance criteria require to run for real; `hybrid`/`local`/`global`'s real live runs still need `heading_backfill.py`'s hardcoded `chunk-vector` dep fixed first (03-06's flagged caveat), which remains out of this plan's `files_modified` scope.
- The D1/D2 real-endpoint gaps (see `coverage` above) are environment gaps, not code gaps — both refusal paths were proven for real in this session; only the clean-pass path awaits a machine holding the plan 03-02 artifacts.

---
*Phase: 03-lightrag-query-side*
*Completed: 2026-09-01*

## Self-Check: PASSED

All created/modified files confirmed present on disk; all three task commit hashes (`6d2cfe8`, `7e54d7e`, `ff185ec`) confirmed in `git log --oneline --all`.
