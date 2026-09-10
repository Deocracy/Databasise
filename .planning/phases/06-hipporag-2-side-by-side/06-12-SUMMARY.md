---
phase: 06-hipporag-2-side-by-side
plan: 12
subsystem: eval-infrastructure
tags: [falsifier-5, mach-03, mach-02, eval-bundle, judge-identity, cost-bounded-ingest, gap-closure]

# Dependency graph
requires:
  - phase: 06-hipporag-2-side-by-side
    plan: "06-10"
    provides: "Databasise.ingest()'s per-modality write dispatch (wiring_family()/_corpus_wiring()) — the public seam corpus_ingest.py drives one document at a time"
  - phase: 06-hipporag-2-side-by-side
    plan: "06-04"
    provides: "the eval-corpus fixture (291 documents), bundle@v1 and EVAL-BUNDLE-V1.md's own next-minted-version rule for a resolved judge_instance"
provides:
  - "databasise/eval/corpus_ingest.py — a dry-run-by-default entry point printing a real, computed projection for the eval-corpus and ingesting exactly --limit documents through the public seam only on explicit --spend opt-in"
  - "databasise/eval/remint.py — resolve_judge_identity()/remint() closing the resolved-judge-identity precondition by minting the bundle's next version, never editing bundle@v1 in place"
  - "Both of FALSIFIER-5-EVIDENCE.md's named preconditions now have a concrete, runnable, spend-free answer in the repository"
affects: ["06-13"]

# Actuals (#2632)
actuals:
  tokens: 8005
  tasks: 2
  commits: 4
plan_head_before: ae2c284

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Estimate-first, spend-only-on-opt-in CLI shape: --limit prints a real computed projection and touches nothing; --spend is the single flag that reaches a real client/store, mirroring build_hipporag_index.py's own build-then-verify docstring convention."
    - "Refuse-never-clamp on an over-large --limit (LimitExceedsCorpusError), matching Page's own PageSizeExceededError precedent."
    - "A thin call-through (remint()) that adds zero versioning logic of its own, relying entirely on mint_bundle's pre-existing content-hash idempotence over judge_instance — the correct instinct here was to add nothing, not a second dedup mechanism."

key-files:
  created:
    - databasise/eval/corpus_ingest.py
    - databasise/eval/remint.py
    - databasise/tests/eval/test_corpus_ingest.py
    - databasise/tests/eval/test_remint.py
  modified: []

key-decisions:
  - "gsd_run check tdd-red-evidence is TAP/Node-test-runner-oriented (parses `# tests N`/`ok N - <name>` TAP lines) and cannot classify pytest's default output — a project-wide, previously-documented limitation (06-01-SUMMARY.md, 06-04-SUMMARY.md). RED evidence for both tasks was produced by committing the test files together with a deliberately broken draft implementation (specific checks disabled/mangled, module still importable), running pytest to capture real per-test AssertionErrors tied to the planned behavior, then restoring the correct implementation for GREEN — the same technique 06-01/06-04 already established for this codebase."
  - "corpus_ingest.py's real --spend path lands in its own store root (v1/.eval_corpus_store, workspace eval-corpus-ingest) — a new module constant, deliberately separate from both the Phase 3 parity store (run_arm.DEFAULT_STORE_ROOT) and the Phase 6 build-harness store (import_index.DEFAULT_STORE_ROOT), so a real eval-corpus ingest run (06-13, if authorized) never lands documents in either of those two stores' own directories."
  - "_ARM_SELECTORS copies test_compare.py's exact two Selector values verbatim (reads_vector for lightrag, reads_graph+reads_kv for hipporag) rather than inventing new selector values, per the plan's own read_first instruction and this codebase's reuse-over-reinvention convention."

requirements-completed: []  # MACH-02/MACH-03 stay Pending — both are shared with 06-13 (not yet summarized); the shared-ID gate (#2388) blocks marking either complete until every sibling plan declaring them has finished. See "Requirements" note below.

coverage:
  - id: D1
    description: "corpus_ingest.py prints a real, computed projection for the first N eval-corpus documents and spends nothing by default"
    requirement: MACH-03
    verification:
      - kind: unit
        ref: "databasise/tests/eval/test_corpus_ingest.py#test_default_path_spends_nothing"
        status: pass
      - kind: unit
        ref: "databasise/tests/eval/test_corpus_ingest.py#test_estimate_labels_its_own_bound_and_note_per_arm"
        status: pass
      - kind: other
        ref: "uv run python -m databasise.eval.corpus_ingest --limit 5"
        status: pass
    human_judgment: false
  - id: D2
    description: "--spend ingests exactly --limit eval-corpus documents through the public Databasise.ingest() seam, one call per document, never the whole 291-document corpus"
    requirement: MACH-03
    verification:
      - kind: unit
        ref: "databasise/tests/eval/test_corpus_ingest.py#test_spend_flag_ingests_exactly_the_limit_never_the_whole_corpus"
        status: pass
      - kind: unit
        ref: "databasise/tests/eval/test_corpus_ingest.py#test_estimate_then_ingest_lands_in_hipporags_own_namespaces"
        status: pass
    human_judgment: false
  - id: D3
    description: "An over-large --limit is refused by name (LimitExceedsCorpusError), never silently clamped"
    requirement: MACH-03
    verification:
      - kind: unit
        ref: "databasise/tests/eval/test_corpus_ingest.py#test_limit_exceeding_corpus_size_is_refused_by_name"
        status: pass
      - kind: other
        ref: "uv run python -m databasise.eval.corpus_ingest --limit 100000 (exit 1)"
        status: pass
    human_judgment: false
  - id: D4
    description: "resolve_judge_identity() returns the identity a real provider response reports and raises UnresolvedJudgeIdentityError rather than substituting the requested/declared model id"
    requirement: MACH-02
    verification:
      - kind: unit
        ref: "databasise/tests/eval/test_remint.py#test_resolve_judge_identity_returns_the_identity_a_real_response_reports"
        status: pass
      - kind: unit
        ref: "databasise/tests/eval/test_remint.py#test_resolve_judge_identity_raises_when_response_carries_no_identity"
        status: pass
    human_judgment: false
  - id: D5
    description: "Re-minting the bundle with a resolved judge identity produces a new version while bundle@v1's on-disk bytes and checksum are byte-identical before and after"
    requirement: MACH-02
    verification:
      - kind: unit
        ref: "databasise/tests/eval/test_remint.py#test_remint_mints_a_new_version_and_leaves_v1_bytes_untouched"
        status: pass
      - kind: unit
        ref: "databasise/tests/eval/test_remint.py#test_reminting_twice_with_the_same_identity_reuses_the_version"
        status: pass
      - kind: other
        ref: "python -c \"...hashlib.sha256(bundle@v1/bundle.json bytes)...\" matches bundle@v1/bundle.sha256"
        status: pass
    human_judgment: false
  - id: D6
    description: "main() with no live credentials exits 1 and never proceeds to a mint with a placeholder identity"
    requirement: MACH-02
    verification:
      - kind: unit
        ref: "databasise/tests/eval/test_remint.py#test_main_with_no_live_credentials_exits_1_and_never_mints"
        status: pass
    human_judgment: false
  - id: D7
    description: "Backstop truths hold unchanged: bundle-versioning suite and the 15 calibration tests still pass; no lightrag import leaked"
    verification:
      - kind: other
        ref: "cd databasise && uv run pytest -q tests/eval/ -x (41 passed)"
        status: pass
      - kind: other
        ref: "cd databasise && uv run python -m databasise.tools.check_import_boundary (exit 0)"
        status: pass
    human_judgment: false

duration: ~24min
completed: 2026-09-10
status: complete
---

# Phase 6 Plan 12: Falsifier 5 Precondition Closure Summary

**Two new spend-free modules — `corpus_ingest.py` (dry-run-by-default eval-corpus ingest, bounded by `--limit`) and `remint.py` (real-response-only judge identity resolution and next-version minting) — close both of Falsifier 5's named preconditions without spending anything.**

## Performance

- **Duration:** ~24 min
- **Tasks:** 2 completed
- **Files modified:** 4 (all created; 0 modified)
- **Commits:** 4

## Accomplishments

- `databasise/eval/corpus_ingest.py` — `estimate()` computes a real, labelled projection (document count, byte total, `chars_per_token`-derived input-token floor, a per-arm `bound`/`note` that names what actually bounds the spend and states plainly that the figure is a floor, never a bill); `ingest_documents()` drives exactly `--limit` documents through `Databasise.ingest()`, one call per document, through the arm's own `Selector` (copied verbatim from `test_compare.py`); `main()` defaults to estimate-only (no client constructed, no store touched) and only reaches real clients/store under the explicit `--spend` flag.
- `LimitExceedsCorpusError` refuses an over-large `--limit` by name rather than silently clamping — `uv run python -m databasise.eval.corpus_ingest --limit 100000` exits 1 naming both the requested and available document counts.
- `databasise/eval/remint.py` — `resolve_judge_identity()` issues one minimal chat call and returns only what the response itself reports, raising `UnresolvedJudgeIdentityError` when the response carries none; `remint()` is a thin call-through to `mint_bundle` (which is already content-addressed over `judge_instance`, so no separate versioning logic was added); `main()` builds real clients, resolves the identity, and mints — gated entirely behind 06-13's own blocking spend checkpoint.
- FALSIFIER-5-EVIDENCE.md's two named preconditions — a resolved judge identity, and a cost-bounded eval-corpus ingest path — both now have concrete, runnable, spend-free answers in the repository. Neither was executed for real; both are proven against stub clients and seeded fixtures only.
- Full `tests/eval/` suite: 41 passed (36 pre-existing/new corpus-ingest + 5 new remint). Full `databasise` suite: 936 passed, 3 skipped — unchanged skip count, no regression.

## Task Commits

Each task followed the RED -> GREEN TDD cycle (committed as a `test` + `feat` pair):

1. **Task 1: Cost-bounded eval-corpus ingest path** — `ea2f090` (test, RED), `3ae7f94` (feat, GREEN)
2. **Task 2: Resolve judge identity and mint the next bundle version** — `def77fd` (test, RED), `ac30ec2` (feat, GREEN)

**Plan metadata:** committed as part of this SUMMARY's own commit.

## Files Created/Modified

- `databasise/eval/corpus_ingest.py` - `IngestEstimate`, `LimitExceedsCorpusError`, `estimate()`, `ingest_documents()`, `main()` — the dry-run-by-default eval-corpus ingest entry point
- `databasise/eval/remint.py` - `UnresolvedJudgeIdentityError`, `resolve_judge_identity()`, `remint()`, `main()` — the judge-identity resolver and next-version mint
- `databasise/tests/eval/test_corpus_ingest.py` - 5 tests covering the tracer path, spend-nothing default, `--spend` bound enforcement, over-large-limit refusal, and per-arm bound/note labelling
- `databasise/tests/eval/test_remint.py` - 5 tests covering identity resolution (present/absent), version minting with `bundle@v1` byte-pinning, idempotent re-mint, and the no-credentials refusal

## Decisions Made

See `key-decisions` in frontmatter. Most consequential: the `gsd_run check tdd-red-evidence` tool cannot classify pytest output for this Python project (a pre-existing, documented limitation from 06-01/06-04) — RED evidence for both tasks was produced by the same "commit tests + a deliberately broken draft implementation, capture real pytest `AssertionError`s, then restore the correct implementation for GREEN" technique those two prior plans already established, rather than mechanically invoking the TAP-oriented tool.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<action>` specifications were implemented as described; no Rule 1-4 auto-fixes were required beyond the RED-phase draft-defect technique already covered above (which is TDD process, not a plan deviation).

## Requirements

`MACH-02` and `MACH-03` (this plan's declared `requirements`) both stay **Pending** in `.planning/REQUIREMENTS.md`. Both IDs are shared with `06-13-PLAN.md`, which has not yet produced a `*-SUMMARY.md` — the shared-ID gate (#2388) correctly blocks marking either complete until every plan declaring them has finished, so a sibling still in flight cannot be marked done by this plan alone. `requirements.ready-ids` confirmed neither ID is ready. This is expected: this plan closes both of Falsifier 5's *preconditions* (a resolved judge identity, a cost-bounded ingest path) without running the real A/A calibration itself — that real run, and the requirement completion it would justify, is 06-13's own scope.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. `--spend`/`remint.main()` both require `v1/.env.parity` (already present in this environment) and real provider credentials it names, but neither is invoked for real by this plan — that is 06-13's own blocking checkpoint.

## Next Phase Readiness

- Both of FALSIFIER-5-EVIDENCE.md's named preconditions have a concrete, runnable, spend-free answer: `corpus_ingest.py --limit N --spend` for the gold-passage/T1 leg's ingest question, and `remint.py` for the answer-level/T0 leg's judge-identity question.
- 06-13's own blocking checkpoint is now a bounded question — "N documents, ~X input tokens, proceed?" and "resolve the judge identity via one real call, proceed?" — never "unbudgetable".
- No blockers for 06-13. `MACH-02`/`MACH-03` remain Pending until 06-13's real run (if authorized) lands and every declaring plan has a SUMMARY.

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-10*

## Self-Check: PASSED

- FOUND: databasise/eval/corpus_ingest.py
- FOUND: databasise/eval/remint.py
- FOUND: databasise/tests/eval/test_corpus_ingest.py
- FOUND: databasise/tests/eval/test_remint.py
- FOUND: .planning/phases/06-hipporag-2-side-by-side/06-12-SUMMARY.md
- FOUND commit: ea2f090 (test, Task 1)
- FOUND commit: 3ae7f94 (feat, Task 1)
- FOUND commit: def77fd (test, Task 2)
- FOUND commit: ac30ec2 (feat, Task 2)
- FOUND commit: e9bcf89 (docs, SUMMARY)
