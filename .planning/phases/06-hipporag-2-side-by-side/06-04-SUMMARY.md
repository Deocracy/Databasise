---
phase: 06-hipporag-2-side-by-side
plan: 04
subsystem: eval
tags: [eval-bundle, mach-02, versioning, content-addressed, rig-ev1, rig-ev2, hotpotqa]

# Dependency graph
requires:
  - phase: 03-lightrag-query-side
    provides: "the corpus fixture pattern (build_corpus_fixture.py/corpus.py) this plan parameterises and reuses byte-identically"
  - phase: 06-hipporag-2-side-by-side
    plan: "06-01"
    provides: "no direct code dependency — this plan is standalone within the phase, but shares its wave-2 slot with 06-02/06-03"
provides:
  - "A 30-question eval-corpus fixture (databasise/tests/fixtures/eval-corpus/), independent of and disjoint from the Phase 3 parity corpus"
  - "databasise/eval/bundle.py — EvalBundle, mint_bundle/load_bundle/open_sealed/record_holdout_use/read_holdout: a minted, content-addressed, append-only eval bundle carrying §EV.1's six content members and §EV.2's two target families over three disjoint dev/holdout/sealed splits"
  - "bundle@v1, the project's first real minted bundle, committed at databasise/evidence/eval-bundles/, with judge_instance recorded as an explicit 'unresolved' sentinel (no live judge call was made)"
  - "databasise/evidence/EVAL-BUNDLE-V1.md — the house-format evidence record for MACH-02, with limits naming the absent owner corpus and the absent A/A null"
affects: [06-06]

# Actuals (#2632)
actuals:
  tokens: 17873
  tasks: 3
  commits: 4
plan_head_before: 2db2712c28bda7f0cf53472e45ddfac1ed788606

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Content-addressed versioning: a bundle version's identity is a SHA-256 over the RFC 8785 canonicalisation of exactly the five §EV.1 invalidating inputs — re-minting identical input is idempotent (returns the existing version), re-minting after any one input changes always mints a new sequential version, and every prior version's bytes are provably untouched (a separate bundle.sha256 sidecar checksum, distinct from the content-identity hash, detects any later on-disk mutation)"
    - "Partition discipline enforced in code, not by convention: dev is a plain field read; holdout is gated behind an append-only usage log (record_holdout_use/read_holdout); sealed is reachable only through open_sealed, which unconditionally mints a new version (bypassing the content-hash dedup, since sealing is a property of whether the partition was touched, not of the six content members) and logs its own opening event before returning content"
    - "Second, independent corpus fixture built by parameterising the existing one-time fixture generator (question count, output dir, row offset) rather than resizing the original — a resize would change the Phase 3 corpus's own hash and orphan the v1 index already imported against it"

key-files:
  created:
    - databasise/eval/__init__.py
    - databasise/eval/bundle.py
    - databasise/tests/eval/__init__.py
    - databasise/tests/eval/conftest.py
    - databasise/tests/eval/test_bundle_versioning.py
    - databasise/tests/fixtures/eval-corpus/MANIFEST.json
    - databasise/tests/fixtures/eval-corpus/README.md
    - databasise/tests/fixtures/eval-corpus/documents/*.txt (291 files)
    - databasise/evidence/EVAL-BUNDLE-V1.md
    - databasise/evidence/eval-bundles/bundle@v1/bundle.json
    - databasise/evidence/eval-bundles/bundle@v1/bundle.sha256
    - databasise/evidence/eval-bundles/bundle@v1/usage.jsonl
    - databasise/evidence/eval-bundles/judge-prompt-v1.txt
  modified:
    - databasise/parity/build_corpus_fixture.py
    - databasise/pyproject.toml

key-decisions:
  - "Query ids in the new eval-corpus fixture are offset-anchored (q{offset+i+1}), not enumerate-anchored (q{i+1}) — the literal enumerate-anchored form would re-mint 'q1'/'q2' for the eval corpus's own first two rows, colliding with the Phase 3 corpus's own q1/q2 and failing the plan's own 'no question id appears in both fixtures' acceptance criterion"
  - "Split assignment is a deterministic SHA-256 hash of each question's own id at a fixed 60/20/20 dev/holdout/sealed proportion — this plan's own decision (RIG §EV.1/§10 name no minimum partition size or correct proportions), carried forward as a flagged assumption already present in the plan itself, not newly introduced here"
  - "judge_instance is recorded as the literal sentinel 'unresolved', not a plausible-looking model string — no live LLM call was made in this environment to resolve a real judge identity, and this project's own resolved-identity convention (Phase 1 D-12: never the requested id, only what a real provider response reports) forbids substituting one. The judge prompt text is still checked in and its SHA-256 is real; only the model identity is deferred to whichever later plan first makes a real judge call."
  - "read_holdout, SealedOpening, HoldoutUsageRequiredError, and MissingSealedEventError were added beyond the plan's own literal 'Artifacts this phase produces' symbol list — the plan's <behavior> block (Tests 5/6) requires partition-discipline gating behavior that needs a concrete accessor/error surface to be testable at all; these are additive helpers, not a change to any of the nine named symbols"

requirements-completed: [MACH-02]

coverage:
  - id: D1
    description: "A 30-question public-benchmark corpus fixture exists, hash-verified by the existing loader, disjoint from and non-destructive to the Phase 3 parity corpus"
    requirement: MACH-02
    verification:
      - kind: unit
        ref: "manual verify command: uv run python -c \"load_snapshot(Path('tests/fixtures/eval-corpus'))\" prints queries=30"
        status: pass
      - kind: other
        ref: "git diff --stat databasise/tests/fixtures/corpus/ reports no changes"
        status: pass
    human_judgment: false
  - id: D2
    description: "EvalBundle mints both §EV.2 target families over three disjoint dev/holdout/sealed splits; every one of §EV.1's five invalidating changes mints a new version and leaves the prior version's bytes untouched; a mutated version is detected and refused on next load; sealed/holdout partition discipline is enforced in code"
    requirement: MACH-02
    verification:
      - kind: unit
        ref: "tests/eval/test_bundle_versioning.py (12 tests covering the plan's own seven <behavior> items, including the Test 7 negative control)"
        status: pass
    human_judgment: false
  - id: D3
    description: "bundle@v1 minted for real from the eval-corpus fixture and committed, with a house-format evidence document (EVAL-BUNDLE-V1.md) stating what MACH-02's content requirement is met and what this bundle does not yet carry"
    requirement: MACH-02
    verification:
      - kind: unit
        ref: "tests/eval/test_bundle_versioning.py::test_bundle_v1_loads_and_matches_the_engines_own_settings"
        status: pass
      - kind: unit
        ref: "tests/eval/test_bundle_versioning.py::test_eval_bundle_v1_evidence_doc_findings_table_has_one_row_per_ev1_member"
        status: pass
    human_judgment: true
    rationale: "The split proportions (60/20/20) and the deterministic hash-based assignment are this plan's own unvalidated decision (flagged in the plan itself — no document states a minimum partition size or correct proportions); a human should confirm the evidence document's own honesty about what bundle@v1 does and does not yet establish (no A/A null, no owner corpus, an unresolved judge identity) before any later plan treats bundle@v1 as settled rather than provisional."

# Metrics
duration: ~65min
completed: 2026-09-09
status: complete
---

# Phase 6 Plan 4: Eval Bundle (MACH-02) Summary

**A minted, content-addressed EvalBundle — dev/holdout/sealed splits, both §EV.2 target families, five §EV.1 invalidating changes proven to mint rather than mutate — stood up over a fresh 30-question HotpotQA fixture, with `bundle@v1` minted for real and recorded in house-format evidence.**

## Performance

- **Duration:** ~65 min
- **Completed:** 2026-09-09
- **Tasks:** 3
- **Files modified/created:** 15 (excluding the 291 generated eval-corpus document text files and MANIFEST.json)

## Accomplishments

- Parameterised `build_corpus_fixture.py`'s `build()` on question count, output directory, and HotpotQA row offset — the bare, no-argument invocation still regenerates the Phase 3 corpus byte-identically (`git diff --stat` reports no changes)
- Built `databasise/tests/fixtures/eval-corpus/`: 291 documents, 30 questions (HotpotQA distractor validation split, offset 2 past the Phase 3 corpus's own two rows), no query id overlap with `tests/fixtures/corpus/`
- `databasise/eval/bundle.py`: `EvalBundle`/`BundleSplit`/`TargetFamily`, `mint_bundle`/`load_bundle`/`open_sealed`/`record_holdout_use`/`read_holdout`, `BundleDriftError`/`MissingTargetFamilyError`/`BundleEditInPlaceError`/`MissingSealedEventError`/`HoldoutUsageRequiredError` — a content-addressed, append-only bundle carrying §EV.1's six content members and §EV.2's two mandatory target families over three disjoint splits
- Version identity is a SHA-256 over `databasise.identity.canon.canonicalise`'s RFC 8785 output of exactly the five §EV.1 invalidating inputs; file integrity is a separate `bundle.sha256` sidecar checksum of `bundle.json`'s own raw bytes — two different hashes, one hashing library (`hashlib`)
- Partition discipline enforced in code: `dev` is a plain read; `holdout` gates behind `record_holdout_use`'s append-only usage log; `sealed` is reachable only through `open_sealed`, which requires a stated event and unconditionally mints a new version
- `bundle@v1` minted for real from the eval-corpus fixture and committed at `databasise/evidence/eval-bundles/` — 17 dev / 9 holdout / 4 sealed questions, `corpus_snapshot_hash`/`determinism_setting`/`concurrency_setting` read live from the real corpus loader and `databasise.seam.engine`'s own constants, `judge_instance` recorded as the explicit `"unresolved"` sentinel
- `databasise/evidence/EVAL-BUNDLE-V1.md`: dated header, `RIG §EV.1` content requirement quoted verbatim, findings tables for both the six required members and the two target families, a verdict, and a limits section naming the absent owner corpus, the absent A/A null, and the unresolved judge identity
- Full suite: 732 passed, 13 skipped bare (`uv run pytest -q`); 809 passed, 1 skipped with `--extra rest --extra mcp` — no regressions

## Task Commits

Each task was committed atomically (RED→GREEN for Task 2's `tdd="true"` cycle):

1. **Task 1: 30-question eval-corpus fixture, Phase 3 corpus untouched** - `3770a4c` (feat)
2. **Task 2 (tdd): RED — failing EvalBundle versioning tests** - `00de574` (test)
2. **Task 2 (tdd): GREEN — EvalBundle implementation** - `5637abf` (feat)
3. **Task 3: mint bundle@v1 and record MACH-02's evidence** - `fe7dc06` (test)

_No REFACTOR commit — the GREEN implementation needed no follow-up cleanup once green._

## TDD Gate Compliance

Task 2 (`type="auto" tdd="true"`) followed RED→GREEN:

- **RED:** `00de574` — the seven `<behavior>` tests committed together with a deliberately incomplete draft implementation (validation checks, dedup lookup, checksum verification, and partition-discipline gates each individually disabled/broken, with the module otherwise fully importable — a genuinely new package with no prior implementation to `git stash`, so the stash technique 06-01-SUMMARY.md used was not applicable here; disabling specific checks in place while keeping the module importable is what produces real assertion failures rather than an INVALID_RED collection error). `uv run pytest -q tests/eval/test_bundle_versioning.py`: **12 of 12 target tests failed on real `AssertionError`s** tied to the planned behavior (the split-partition invariant assertion firing because the draft dropped the last question id; missing `pytest.raises(...)` exceptions for `MissingTargetFamilyError`/`BundleDriftError`/`MissingSealedEventError`/`HoldoutUsageRequiredError`; the negative-control test failing because the draft's disabled dedup lookup minted `bundle@v2` instead of returning the existing `bundle@v1`). Every failure traces to a real assertion inside the target tests, not an import or collection error.
- **GREEN:** `5637abf` — the draft's six disabled checks restored to their full implementation (unchanged from the file's own original design, backed up before the RED edits and diffed byte-identical after restoration); all 12 target tests pass, full suite green (728 passed/13 skipped bare before Task 3's four additional tests; 732/13 after).
- **Tool note (same limitation 06-01-SUMMARY.md already recorded):** `gsd_run check tdd-red-evidence` is TAP/Node-test-runner-oriented and does not natively parse pytest's default output format for this Python project; RED evidence was verified manually via pytest's own exit code and per-test failure attribution instead of running that tool mechanically.

## Files Created/Modified

- `databasise/parity/build_corpus_fixture.py` - parameterised on question count/fixture dir/offset; default invocation unchanged
- `databasise/tests/fixtures/eval-corpus/` - 291 documents, `MANIFEST.json`, `README.md`
- `databasise/eval/__init__.py`, `databasise/eval/bundle.py` - the EvalBundle module
- `databasise/tests/eval/__init__.py`, `conftest.py`, `test_bundle_versioning.py` - fixtures and 16 tests
- `databasise/evidence/EVAL-BUNDLE-V1.md`, `databasise/evidence/eval-bundles/` - the committed `bundle@v1` and its evidence record
- `databasise/pyproject.toml` - `databasise.eval` added to `[tool.setuptools] packages`

## Decisions Made

See `key-decisions` in frontmatter. Most load-bearing: `judge_instance` is recorded as the literal `"unresolved"` sentinel rather than a plausible model string, matching this project's own resolved-identity discipline (a model identity is only ever read from a real provider response, never declared) and its `unbudgetable`-over-a-fabricated-value convention already established in `full_ingest.py`/`full_delete.py` for token accounting.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Query ids in the eval-corpus fixture offset-anchored, not enumerate-anchored**
- **Found during:** Task 1 (parameterising `build_corpus_fixture.py`)
- **Issue:** The original `build()` minted query ids as `f"q{i+1}"` (enumerate-anchored). Applied unchanged to the eval-corpus fixture (offset=2, 30 questions), this would produce ids `q1`-`q30`, directly colliding with the Phase 3 corpus's own `q1`/`q2` — failing the plan's own acceptance criterion "No question id appears in both fixtures' manifests."
- **Fix:** Query ids are now `f"q{offset + i + 1}"` — offset 0 (the Phase 3 corpus's own default) reproduces the exact same ids as before (byte-identical default output preserved), while offset 2 (the eval corpus) produces `q3`-`q32`, disjoint from `q1`/`q2`.
- **Files modified:** `databasise/parity/build_corpus_fixture.py`
- **Verification:** `git diff --stat databasise/tests/fixtures/corpus/` reports no changes after regenerating with default args; a direct set-intersection check between the two fixtures' query ids returns empty.
- **Committed in:** `3770a4c` (Task 1 commit)

**2. [Rule 2 - Missing Critical] `read_holdout`, `SealedOpening`, and two additional named errors added beyond the plan's literal symbol list**
- **Found during:** Task 2 (implementing partition discipline)
- **Issue:** The plan's "Artifacts this phase produces" line names nine symbols (`EvalBundle`, `BundleSplit`, `TargetFamily`, `mint_bundle`, `load_bundle`, `open_sealed`, `record_holdout_use`, `BundleDriftError`, `MissingTargetFamilyError`) plus `BundleEditInPlaceError`, but the plan's own `<behavior>` Tests 5/6 require "reading holdout content without one raises" and "`open_sealed` requires a stated event" — behavior that needs a concrete accessor and error types to be testable and usable at all.
- **Fix:** Added `read_holdout` (the holdout accessor `record_holdout_use` gates), `SealedOpening` (a small return-value dataclass for `open_sealed`), `MissingSealedEventError`, and `HoldoutUsageRequiredError`. All nine originally-named symbols are unchanged and present.
- **Files modified:** `databasise/eval/bundle.py`
- **Verification:** All 16 `tests/eval/` tests pass; the nine originally-named symbols are all present and importable per Task 2's own acceptance criteria.
- **Committed in:** `5637abf` (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (both Rule 2 — missing critical functionality required by the plan's own stated acceptance criteria/behavior)
**Impact on plan:** Both necessary for the plan's own explicit acceptance criteria to hold; no scope creep — the second deviation adds only what the plan's own `<behavior>` tests already required to be testable.

## Issues Encountered

- **`uv sync` (bare) uninstalls the `rest`/`mcp` extras** — the same non-additive-sync gotcha 06-03-SUMMARY.md already flagged. Running `uv sync` (bare) mid-session to register the new `databasise.eval` package dropped `fastapi`/`mcp`, briefly showing a lower bare pass count (728 vs the recorded 729 baseline) purely from more REST/MCP tests skipping, not a code regression. Reinstalled with `uv sync --extra rest --extra mcp` together and confirmed the full suite green both ways (732 passed/13 skipped bare; 809 passed/1 skipped with both extras) before finishing.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `bundle@v1` and `databasise.eval.bundle` are ready for plan 06-06's A/A calibration (MACH-03, Falsifier 5) — `mint_bundle`/`load_bundle` give it a real, hash-verified `(bundle@v, tier, metric)` key to calibrate a null against.
- MACH-02's traceability row can move from `Pending` to `Complete` — bundle content, versioning, both target families, and partition discipline are all proven in code and evidence, not asserted.
- Two things explicitly remain open for later plans, named in `EVAL-BUNDLE-V1.md`'s own limits section: the owner's own corpus (Phase 7's HARD-04) and a resolved judge identity (whichever plan first makes a real judge call mints the version that carries it).
- The split proportions (60/20/20) and the deterministic hash-based assignment are this plan's own unvalidated decision, carried forward as a flagged assumption — no document states a minimum partition size or correct proportions, and nothing in this plan settles that boundary.

## Self-Check: PASSED

- All `key-files.created` verified present on disk (`eval/__init__.py`, `eval/bundle.py`, `tests/eval/__init__.py`, `tests/eval/conftest.py`, `tests/eval/test_bundle_versioning.py`, `tests/fixtures/eval-corpus/MANIFEST.json`, `tests/fixtures/eval-corpus/README.md`, `evidence/EVAL-BUNDLE-V1.md`, `evidence/eval-bundles/bundle@v1/{bundle.json,bundle.sha256,usage.jsonl}`, `evidence/eval-bundles/judge-prompt-v1.txt`).
- `git log --oneline --all | grep -E "3770a4c|00de574|5637abf|fe7dc06"` returns all four commits.
- Every task's `<acceptance_criteria>` re-verified: `tests/fixtures/eval-corpus/MANIFEST.json`'s 30 queries all carry non-empty `question`/`answer`/`gold_document_ids`; `git diff --stat databasise/tests/fixtures/corpus/` reports no changes; no query id overlaps the Phase 3 corpus; `databasise/eval/bundle.py` defines all nine originally-named symbols plus `BundleEditInPlaceError`; `databasise.eval` is in `pyproject.toml`'s `[tool.setuptools] packages`; `bundle.py` imports no hashing library besides `hashlib`; a fresh-process `load_bundle` against the committed `bundle@v1` succeeds and hash-verifies.
- Plan-level `<verification>`: `cd databasise && uv run pytest -q` exits 0 (732 passed, 13 skipped); `git diff --stat databasise/tests/fixtures/corpus/` reports no changes; `bundle@v1` loads and hash-verifies from a fresh `uv run python -c` process.

---
*Phase: 06-hipporag-2-side-by-side*
*Completed: 2026-09-09*
