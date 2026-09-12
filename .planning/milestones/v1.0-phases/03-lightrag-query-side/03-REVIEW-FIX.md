---
phase: 03-lightrag-query-side
fixed_at: 2026-09-06T20:58:48Z
review_path: .planning/phases/03-lightrag-query-side/03-REVIEW.md
iteration: 3
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-09-06T20:58:48Z
**Source review:** `.planning/phases/03-lightrag-query-side/03-REVIEW.md`
**Iteration:** 3

**Summary:**

- Findings in scope (critical + warning): 3
- Fixed: 3
- Skipped: 0

**Verification environment:** all edits were authored and unit-verified inside an isolated git
worktree (`gsd-reviewfix/03-4176741`), fast-forward-merged into `main`, then the worktree and its
temp branch were removed. The two real-data tests that need the real Task 2 v1 build
(`v1/.parity_working_dir`, gitignored and untracked) do not exist inside a fresh git worktree by
default — only git-tracked files are checked out there — so they were first proven against real
data by temporarily symlinking `v1/.parity_working_dir` (and `.parity_v2_store`, `.venv`) into the
worktree, running them there, then deleting the symlinks before committing (`git status` inside
the worktree was clean of the symlinks at commit time). `v1/.env.parity` was deliberately never
symlinked into the worktree — it is a live-API-key file and this session's secret-file guard
refuses to touch it. The **authoritative full-suite run below is the main checkout's**, taken
after the fast-forward merge, where all real-data fixtures (including `.env.parity`) are present
natively.

## Fixed Issues

### WR-01: `_render_not_measured()`'s three-way branch is not per-arm, unlike `_render_verdict()`, and would drop an arm's status silently under a future mixed degraded+excursion state

**Files modified:** `databasise/evidence/parity_report.py`, `databasise/tests/parity/test_parity_evidence.py`
**Commit:** `4504e22`
**Applied fix:** `_render_not_measured()`'s `degradation_clause` was picked by an `if
degraded_arms: ... elif excursion_arms: ... else: ...` priority chain — mutually exclusive, so a
future state with a degraded arm alongside a real, non-degraded excursion arm would silently drop
the excursion (and any clean) arm from this section. Changed the chain to three independent `if`
blocks, each appending its own clause to an `arm_clauses` list, then joined with `"; "` —
`degraded_arms`/`excursion_arms`/`clean_arms` already partition `graph_arms` with no overlap (each
comprehension excludes the buckets computed before it), so this always names every graph arm in
exactly one clause regardless of how the three buckets mix, mirroring `_render_verdict()`'s
per-arm completeness without changing its existing wording for any single-bucket case. Added
`test_render_not_measured_names_every_arm_when_degraded_and_excursion_states_mix` — a synthetic
fixture (not the real committed data) with `hybrid` degraded, `local` a real non-degraded
excursion, and `global` clean — asserting all three arms are named in the rendered text. Confirmed
the existing regression test (`test_render_not_measured_does_not_assert_agreement_for_an_arm_with_
a_real_excursion`, which pins the real-data, all-excursion case) still passes unchanged, and
re-rendered both `PARITY-EVIDENCE.md` and `DECLARED-DEVIATIONS.md` against the real committed
data — byte-for-byte identical to the already-committed documents (`git diff` reported no changes
to either), since the real data has no degraded arm and this fix only changes behavior when
multiple buckets are non-empty simultaneously.

### WR-02: `_VECTOR_TOLERANCE`'s stated safety margin is arithmetically wrong — it is one order of magnitude above the noise ceiling, not two

**Files modified:** `databasise/parity/import_index.py`
**Commit:** `d2fd287`
**Applied fix:** The comment claimed `1e-4` is "two orders of magnitude above the measured ~1e-5
noise ceiling," but `1e-4 / 1e-5 = 10` — one order of magnitude. Corrected the comment to state
the true `10x` ratio, and added the reasoning for why that margin is still defensible: the `~1e-5`
figure is itself the observed *maximum* per-component noise across all 407 real vectors (not a
typical/average value), so 10x above a measured maximum is reasonable headroom — without changing
`_VECTOR_TOLERANCE`'s value, since the review explicitly asked for the honest sentence rather than
inflating the constant to match the original (wrong) claim.

### WR-03: The new perturbation test proves the mechanism still fires, but not the specific improvement CR-02 claimed over the old rounding-grid check

**Files modified:** `databasise/tests/parity/test_import_verification.py`
**Commit:** `1fbc04a`
**Applied fix:** The existing `test_real_v1_build_perturbed_vector_is_caught_and_named` perturbs a
component by `+1.0` — a shift the old 2-decimal rounding-grid hash (`_quantized_vector_bytes` /
`_vector_set_hash`, both fully removed from the source by the CR-02 fix, confirmed via `git log`
on the pre-fix commit) would also have caught trivially, since it moves the value nowhere near a
grid boundary. Kept that test as-is (it still covers "a gross difference is still caught," a
separate, legitimate case) and added a new sibling test,
`test_real_v1_build_perturbation_below_old_rounding_grid_resolution_is_still_caught`, that
computes a component-specific delta guaranteed to (a) stay inside that real component's own
2-decimal rounding cell — so `round(value, 2)` is provably unchanged, meaning the old whole-vector
hash would have reported no difference at all — while (b) still exceeding `_VECTOR_TOLERANCE` by
10x, so the new tolerance check still flags and names the offending id. The delta is derived from
the real vector's own value at test time (not hardcoded), using the fact that the two rounding-cell
half-widths on either side of any real float always sum to `0.01`, so the larger half is always
`>= 0.005` — comfortably above the `10x`-tolerance minimum regardless of which real vector value
the test happens to draw. Verified against the real imported index (`v1/.parity_working_dir`,
symlinked into the isolated worktree for this run only): both the kept `+1.0` test and the new
discriminating test pass, and the new test's own in-test assertions confirm the delta both
round-trips through the old grid unchanged and clears the new tolerance.

## Skipped Issues

None — all in-scope findings were fixed.

## Out of scope

IN-01 (`_v1_graph`/`_v2_graph`'s node/edge-attribute payloads are never compared) is an
Info-severity finding, outside this run's `critical_warning` fix scope, and was left unaddressed
for the record — unchanged from the prior iteration's review.

## Verification

Full suite, run in the **main checkout** after the review-fix branch (`gsd-reviewfix/03-4176741`)
was fast-forward-merged into `main` and the worktree removed:

```text
cd databasise && uv run pytest -q
466 passed in 120.39s (0:02:00)
```

Baseline before this fix cycle was 464 passed, 0 failed; the two additional passing tests are the
WR-01 mixed-state regression test and the WR-03 discriminating perturbation test added above. No
test was removed, weakened, or marked skip/xfail by any of the three fixes.

---

_Fixed: 2026-09-06T20:58:48Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 3_
