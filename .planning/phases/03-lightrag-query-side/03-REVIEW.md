---
phase: 03-lightrag-query-side
reviewed: 2026-09-06T21:10:00Z
depth: standard
files_reviewed: 16
files_reviewed_list:
  - databasise/evidence/parity_report.py
  - databasise/evidence/PARITY-EVIDENCE.md
  - databasise/evidence/DECLARED-DEVIATIONS.md
  - databasise/parity/import_index.py
  - databasise/tests/parity/test_import_verification.py
  - databasise/tests/parity/test_parity_evidence.py
  - v1/lightrag/operate.py
  - v1/README-PARITY.md
  - databasise/stores/vector.py
  - databasise/parity/run_arm.py
  - databasise/clients/openai_compat.py
  - databasise/parts_core/lightrag/entity_lookup.py
  - databasise/parts_core/lightrag/relation_lookup.py
  - databasise/parts_core/lightrag/chunk_vector.py
  - databasise/parts_core/lightrag/chunk_sel_kg.py
  - databasise/parts_core/lightrag/heading_backfill.py
findings:
  critical: 0
  warning: 3
  info: 1
  total: 4
status: issues_found
---

# Phase 03: Code Review Report (iteration 2 — fix verification)

**Reviewed:** 2026-09-06T21:10:00Z
**Depth:** standard
**Files Reviewed:** 16
**Status:** issues_found

## Summary

This is a re-review of three fixes landed against the prior review's CR-01, CR-02, and WR-01
(commits `f2f7e96`, `31738b1`, `45925d6`), reviewed as new code rather than as a diff, per this
task's instructions. All three fixes are correct on the actual committed data and each is backed
by a genuine, non-vacuous regression test that exercises real committed evidence or a real
imported index — none of the three passes vacuously.

**WR-01** is a clean, exact mirror of the already-fixed sibling site; confirmed no third unguarded
`get("weight", ...)` read of the same `get_edge()` shape remains in the file, and
`v1/README-PARITY.md`'s disclosure now correctly names both sites.

**CR-02**'s replacement primitive is sound at the core: I exercised `_compare_vector_sets`
directly against synthetic id-missing, id-extra, below-tolerance, and above-tolerance cases, and
all four behave correctly — it compares the right pairs by id, not by position; it flags a
one-sided id with the correct offending id; and the 1e-4 boundary triggers exactly where
documented. It also correctly declines to reproduce the boundary-flake class the prior review
named, since there is no rounding grid left to sit near. Two things about the surrounding
justification do not hold up, both detailed under Warnings below: the docstring's own stated
safety margin ("two orders of magnitude") is arithmetically wrong, and the new perturbation test
does not prove the specific property CR-02 was fixed to deliver (see WR-02/WR-03 below).

**CR-01**'s fix correctly derives the sentence from the same `_arm_degraded()`/
`_arm_excursion_summary()` state `_render_verdict()` already computes, and both
`PARITY-EVIDENCE.md` and `DECLARED-DEVIATIONS.md` were confirmed byte-for-byte re-renderable from
the current code against the current committed data (`render_markdown()` output and
`render_deviations_document(_collect_deviations())` output both match the committed files
exactly). On the real data (no arm currently degraded), the fix is correct and the two documents
no longer contradict each other or the Verdict section. The one gap found — detailed under WR-01
below — is that the new branching is not as generic as `_render_verdict()`'s per-arm loop: it
would silently drop mention of a non-priority arm bucket if the data ever produced a mix of
degraded and excursion arms simultaneously. This does not misstate anything on the current data
and does not reproduce CR-01's original defect (a false "measured agreement" claim); it is a
latent completeness gap, not a live one.

IN-01 (graph-topology assertion never checks node/edge attribute payloads) was out of this fix
cycle's scope and still holds unchanged — confirmed `_v1_graph`/`_v2_graph` in
`databasise/parity/import_index.py` still return only id-sets and edge-endpoint-pair sets.

## Warnings

### WR-01: `_render_not_measured()`'s three-way branch is not per-arm, unlike `_render_verdict()`, and would drop an arm's status silently under a future mixed degraded+excursion state

**File:** `databasise/evidence/parity_report.py:1228-1253`

**Issue:** The CR-01 fix computes `degraded_arms`/`excursion_arms`/`clean_arms` (mirroring
`_render_verdict()`'s per-arm state), but then picks exactly one whole-document clause via
`if degraded_arms: ... elif excursion_arms: ... else: ...` — a priority chain, not a per-arm
report. `_render_verdict()` (the function this fix explicitly modeled itself on) instead loops
`for arm in graph_arms` and emits one sentence per arm regardless of how the three buckets mix.

On the real committed data (`degraded_arms == []` for all three graph arms today) this produces
the correct sentence and the fix is fully correct for the case it was written to close. But
imagine a future re-run where, say, `hybrid` degrades while `local`/`global` keep their real,
non-degraded excursions (a state `_arm_degraded`/`_arm_excursion_summary` already computes fresh
from committed records, so it can occur with no code change): `degraded_arms == ["hybrid"]` is
truthy, so the `elif excursion_arms:` branch never runs, and the resulting sentence discusses only
`hybrid`'s degradation — `local`/`global`'s real excursions go completely unmentioned by this
paragraph. This does not resurrect CR-01's specific defect (no false "measured agreement" claim is
made), but it does silently omit disclosure for two arms whose status this exact section exists to
name, which is the same class of gap CR-01 was written to close and the exact question this task
asked to check ("would it still be true if the arms' measured outcomes changed again?" — the
answer for this section is "no, it would stop naming two of the three arms").

**Fix:** Mirror `_render_verdict()`'s per-arm loop instead of a single whole-document clause, e.g.
build one clause per arm keyed on that arm's own `(degraded, excursion, clean)` state and join
them, so every graph arm's status is always named in this section regardless of how the three
buckets mix:
```python
arm_clauses = []
for arm in graph_arms:
    degraded, _ = _arm_degraded(arm)
    if degraded:
        arm_clauses.append(f"`{arm}`'s decomposed run degraded before completing a real retrieval")
    elif _arm_excursion_summary(arm):
        arm_clauses.append(f"`{arm}` measured a real, non-empty disagreement rather than an agreement")
    else:
        arm_clauses.append(f"`{arm}` measured retrieval-level agreement with no degradation")
degradation_clause = "; ".join(arm_clauses)
```
and add a synthetic (non-real-data) unit test that constructs a mixed degraded+excursion state and
asserts every arm is named in the output — the current regression test only exercises the
all-excursion, no-degradation state the real data happens to be in today.

### WR-02: `_VECTOR_TOLERANCE`'s stated safety margin is arithmetically wrong — it is one order of magnitude above the noise ceiling, not two

**File:** `databasise/parity/import_index.py:289-290` (same claim repeated in commit `45925d6`'s message)

**Issue:** The code comment states: `"1e-4 is two orders of magnitude above the measured ~1e-5
noise ceiling"`. `1e-4 / 1e-5 = 10`, i.e. one order of magnitude, not two — "two orders of
magnitude" above `1e-5` would be `1e-3`, ten times looser than the tolerance actually shipped.
This exact miscalculation was already present in the prior review's own suggested fix text
("still 100x the measured ~1e-5 noise ceiling") and was carried forward verbatim into the shipped
docstring and commit message without being checked. This is precisely the class of "evidence looks
cleaner than the numbers support" defect this review track exists to catch: a reader trusting the
comment believes there is 100x headroom between the tolerance and the worst observed noise, when
the real margin is 10x. Ten times is not necessarily too tight — the module's own claim is that
`~1e-5` is already the observed maximum per-component noise across 407 real vectors, so 10x above
a measured maximum is a defensible margin — but the code should not misstate its own math, since
the next person to consider tightening or loosening `_VECTOR_TOLERANCE` will reason from the wrong
number.

**Fix:** Correct the comment to say "one order of magnitude" (or restate the actual ratio, `10x`),
and either accept the true 10x margin explicitly or widen `_VECTOR_TOLERANCE` if a firmer margin
above the observed noise ceiling is wanted.

### WR-03: The new perturbation test proves the mechanism still fires, but not the specific improvement CR-02 claimed over the old rounding-grid check

**File:** `databasise/tests/parity/test_import_verification.py` (new
`test_real_v1_build_perturbed_vector_is_caught_and_named`)

**Issue:** The task this fix was reviewed under specifically asked whether the perturbation test
"perturb[s] by an amount that would have passed the old 2-decimal grid, so it proves the new check
is strictly stronger." It does not: the test adds `+1.0` to one component of a unit-normalized
vector (whose components have typical magnitude `~1/sqrt(4096) ≈ 0.0156`), a perturbation the test
itself asserts is `> 1000 * _VECTOR_TOLERANCE`. A shift of `+1.0` moves the rounded-to-2-decimals
value from something like `0.02` to `1.02` — the old `_VECTOR_HASH_DECIMALS = 2` rounding-grid
check the prior review criticized would have caught this trivially, since it is nowhere near a
grid boundary. This test therefore only proves the new mechanism still catches an obvious, gross
difference (the same thing the old hash-based check already caught); it does not exercise, and
cannot distinguish, the actual property CR-02 was implemented to deliver — catching a subtler
difference (in the `0.005`–`0.0156` component-magnitude range that used to collapse toward zero
or land within a 2-decimal grid cell) that the old check would have missed but the new tolerance
check catches. As shipped, nothing in the test suite demonstrates the new check is "strictly
stronger" rather than merely "differently implemented but equally coarse-grained."

**Fix:** Add (or change the existing perturbation to use) a component-level perturbation sized
between the tolerance and the old grid's resolution — e.g. perturb by `5e-3` (above
`_VECTOR_TOLERANCE = 1e-4`, but small enough that `np.round(x, 2)` often leaves the 2-decimal
rounded value unchanged for a component whose true value sits mid-cell) and assert both that (a)
the new tolerance check still flags it and names the id, and (b) recompute what the old
`_quantized_vector_bytes`/`_vector_set_hash` comparison would have produced for the same
perturbed pair and assert it would *not* have differed — proving the new check is strictly
stronger on a concrete case, not just equally capable on an easy one.

## Info

### IN-01: `verify_import`'s graph-topology assertion never checks node/edge attribute payloads

**File:** `databasise/parity/import_index.py:365-462` (unchanged by this fix cycle; carried
forward from the prior review, out of scope for this fix run)

**Issue:** `_v1_graph`/`_v2_graph` still read only node-id sets and edge-endpoint-pair sets — the
D-02 graph-topology assertion never compares each node/edge's `attrs` payload (`description`,
`weight`, `entity_type`, etc.). An import that preserves every id and edge pair but corrupts or
drops an attribute value (exactly the class of string/float weight confusion WR-01 in the prior
review discussed) would pass `verify_import` cleanly. This may be a deliberate, documented scope
choice rather than an oversight, but it still means "verified" names less than a reader might
assume from the name.

**Fix:** If attribute-level fidelity matters for this phase's claims, extend the graph-topology
assertion to also compare each node/edge's `attrs` dict (or a canonical hash of it) between v1 and
v2. If it is an intentional scope limitation, say so explicitly in the module docstring's list of
"D-02's three assertions."

---

_Reviewed: 2026-09-06T21:10:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
