---
phase: 03-lightrag-query-side
reviewed: 2026-09-06T20:18:28Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - databasise/clients/openai_compat.py
  - databasise/evidence/parity_report.py
  - databasise/parity/import_index.py
  - databasise/parity/run_arm.py
  - databasise/parts_core/lightrag/chunk_sel_kg.py
  - databasise/parts_core/lightrag/chunk_vector.py
  - databasise/parts_core/lightrag/entity_lookup.py
  - databasise/parts_core/lightrag/heading_backfill.py
  - databasise/parts_core/lightrag/relation_lookup.py
  - databasise/stores/vector.py
  - databasise/tests/clients/test_openai_compat.py
  - databasise/tests/parity/test_graph_arm_real_index.py
  - databasise/tests/parity/test_import_verification.py
  - databasise/tests/parity/test_naive_arm_end_to_end.py
  - databasise/tests/parity/test_parity_evidence.py
  - databasise/tests/parts_core/lightrag/test_graph_half_parts.py
  - databasise/tests/parts_core/lightrag/test_naive_arm_parts.py
  - databasise/tests/parts_core/lightrag/test_transform_parts.py
  - databasise/tests/stores/test_vector_namespaces.py
  - v1/lightrag/operate.py
  - v1/scripts/run_parity_ingest.py
  - v1/README-PARITY.md
  - databasise/evidence/PARITY-EVIDENCE.md
  - databasise/evidence/DECLARED-DEVIATIONS.md
findings:
  critical: 2
  warning: 1
  info: 1
  total: 4
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-09-06T20:18:28Z
**Depth:** standard
**Files Reviewed:** 23 (plus the committed `parity_results/*.json` sanity-checked as data)
**Status:** issues_found

## Summary

This is a gap-closure wave over a parity-measurement harness; the product being reviewed is not
just code but the honesty of a comparison. Most of the wave holds up well under adversarial
reading: the `MultiNamespaceVectorStore` no-default refusal is real and tested (no silent `chunks`
fallback survives); `render_deviations_document()`'s split into "reasoned" (rendered through the
still-strict, unmodified `render_deviations_markdown`) and "PENDING, not fabricated" outstanding
entries is a legitimate refinement, not a weakening — 18 real, non-degraded, unreasoned excursions
on `hybrid`/`local`/`global` are disclosed as `PENDING`, never smuggled into "Named deviations",
and `test_committed_deviations_document_matches_a_fresh_render` proves the committed file is not
stale; `test_parity_evidence.py`'s re-pin (`matched=14`/`no-touch=2`, specific per-arm excursion
counts) asserts real numbers against the real committed data, not a shape-only check. The
`v1/lightrag/operate.py` `float()` coercion is correct, minimal for the crash it fixes, and
honestly disclosed in `v1/README-PARITY.md` as a baseline change.

Two defects stand out, both in the "evidence looks cleaner than the numbers support" class this
review was told to weight highest:

1. `PARITY-EVIDENCE.md`'s own "What is not measured" section states, of `hybrid`/`local`/`global`,
   that "their measured retrieval-level agreement is not an artifact of a halted run" — but the
   committed data for all three arms shows real, substantial *disagreement*
   (`ranking_agreement` 0.50-0.86, `entity_diff`/`relation_diff` symmetric differences of 20-78
   items per query), which the same document's own Verdict section correctly refuses to call
   agreement. The renderer's degradation branch was updated (03-13-PLAN.md gap 2) to also check
   for excursions; the "not measured" branch producing this sentence was not, and no test asserts
   on its wording — the stale phrase survived the fix cycle that closed the identical bug
   elsewhere in the same file.

2. `_VECTOR_HASH_DECIMALS` was dropped from 3 to 2 against the plan's explicit "the importer is
   already correct, do not change it" instruction, to clear a rounding-grid boundary case. The
   change is a probability reduction of a defect class, not a removal of it, and it costs real
   discriminating power (see finding CR-02) — a boundary-free tolerance check was available and
   would have been strictly better on both counts.

## Critical Issues

### CR-01: `PARITY-EVIDENCE.md`'s "What is not measured" section asserts a measured agreement that the committed data contradicts

**File:** `databasise/evidence/parity_report.py:1234-1238` (rendered into
`databasise/evidence/PARITY-EVIDENCE.md:115`)

**Issue:** `_render_not_measured()`'s `degradation_clause` has two branches, keyed only on whether
any of `hybrid`/`local`/`global` degraded:

```python
if degraded_arms:
    degradation_clause = (... "so its/their measured zero diff is not a validated agreement...")
else:
    degradation_clause = (
        f"and `{'`/`'.join(graph_arms)}` completed without a decomposed-run "
        "degradation, so their measured retrieval-level agreement is not an artifact of "
        "a halted run"
    )
```

The `else` branch was written under the assumption (the same one 03-13-PLAN.md gap 2's fix to
`_render_verdict` names and corrects) that "not degraded" implies "measured agreement." It does
not: the real committed run for all three graph arms is non-degraded *and* substantially
disagreeing —

```
hybrid  q1: ranking_agreement=0.628, entity_diff=58, relation_diff=60
hybrid  q2: ranking_agreement=0.731, entity_diff=46, relation_diff=44
local   q1: ranking_agreement=0.500, entity_diff=20, relation_diff=33
local   q2: ranking_agreement=0.673, entity_diff=22, relation_diff=30
global  q1: ranking_agreement=0.533, entity_diff=76, relation_diff=78
global  q2: ranking_agreement=0.857, entity_diff=68, relation_diff=68
```

(figures read directly from `databasise/evidence/parity_results/{hybrid,local,global}-comparison.json`).
The rendered sentence — "their measured retrieval-level agreement is not an artifact of a halted
run" — asserts an agreement that was never measured, directly contradicting the same document's
own Verdict section three sections later ("this is not read as exact retrieval-level agreement
either... the two disagree"). A reader of only the "What is not measured" section, or anyone
grepping the document for "agreement", is told the opposite of what "Per-arm retrieval-level
comparison" and "Verdict" actually show. This is exactly the failure mode this review was told to
weight above an ordinary crash: code that makes a comparison look cleaner than it is.

No test in `test_parity_evidence.py` asserts on `_render_not_measured()`'s wording for the
non-degraded-with-excursions case — the existing regression test for this fix cycle
(`test_render_markdown_states_the_hybrid_local_global_excursions_rather_than_a_clean_pass`) only
checks the Verdict section's text, so the stale sibling branch in a different function went
unnoticed.

**Fix:** Branch `degradation_clause` on the same three-way state `_render_verdict()` already
computes (degraded / non-degraded-with-excursions / non-degraded-and-clean), not on `degraded_arms`
alone, e.g.:

```python
excursion_arms = [a for a in graph_arms if not _arm_degraded(a)[0] and _arm_excursion_summary(a)]
clean_arms = [a for a in graph_arms if a not in degraded_arms and a not in excursion_arms]
if degraded_arms:
    degradation_clause = (...)
elif excursion_arms:
    degradation_clause = (
        f"and `{'`/`'.join(excursion_arms)}` completed without a decomposed-run degradation but "
        "measured a real, non-empty entity/relation disagreement rather than an agreement (see "
        "the per-arm degradation notes and Verdict section) — no retrieval-level agreement claim "
        "is made for these arms at all"
    )
else:
    degradation_clause = (
        f"and `{'`/`'.join(clean_arms)}` completed without a decomposed-run degradation, so their "
        "measured retrieval-level agreement is not an artifact of a halted run"
    )
```
and add a test asserting `"measured retrieval-level agreement"` does NOT appear in
`_render_not_measured()`'s output when any graph arm has a non-empty, non-degraded excursion.

### CR-02: `_VECTOR_HASH_DECIMALS = 2` trades away discriminating power to clear a boundary case that a tolerance check would remove entirely

**File:** `databasise/parity/import_index.py:294-298`

**Issue:** The task specifically asked whether this committed constant should stand. It should
not, for three compounding reasons:

1. **It lowers the probability of the boundary-flake class; it does not remove it.** Any
   fixed-decimal round is a grid with edges. The docstring's own history (6 and 5 decimals tried
   first, then 3, now 2) is itself the pattern of "coarsen until the current dataset stops
   crossing a line" — each step reduces the chance of landing near an edge on *this* 410-vector
   build, but the next real re-ingest (more documents, more entities) can land near an edge at 2
   decimals exactly as one did at 3. The class of bug is unchanged; only its odds on today's data
   moved.

2. **The coarsening measurably reduces the hash's discriminating power, not just its
   flakiness.** A 4096-dim, L2-normalised, float32 embedding has a typical per-component magnitude
   of `1/sqrt(4096) ≈ 0.0156`. Rounding to 2 decimals (a 0.01 grid) means any component with
   `|x| < 0.005` — roughly a quarter of all components under a normal-ish distribution around that
   magnitude — collapses to exactly `0.00`, and the surviving nonzero values are quantized onto a
   handful of buckets (`±0.01`, `±0.02`, rarely `±0.03`). The hash is still over 4096 quantized
   components at once, so a *wrong id-to-vector pairing* or a *genuine re-embedding* (which differ
   across many components by an amount well above 0.005) will still almost certainly be caught —
   but a subtler defect (e.g. two near-duplicate entities' vectors accidentally swapped, or a
   small but real normalisation drift affecting a minority of components) now has roughly 4x more
   room to hide below the new grid's resolution than it did at 3 decimals. The check is weaker in
   a way that is real, even though it happens not to matter for the one case actually exercised.

3. **A tolerance-based check is strictly better on both axes the docstring itself argues for.**
   Replacing the rounded-hash comparison with an explicit per-vector distance check (e.g.
   `np.max(np.abs(v1 - v2)) < 1e-4` — still 100x the measured ~1e-5 noise ceiling, five orders of
   magnitude above the 1.49e-8 diff that triggered this change) is monotonic, not a step function:
   it has no grid line to land near, so it cannot flake regardless of how the dataset grows, and it
   does not collapse a quarter of every vector's components to a shared value first. It would have
   passed the exact case that motivated this change (1.49e-8 ≪ 1e-4) without discarding resolution
   from the other 75% of components that don't round to zero. This is a case where the "how do I
   make the boundary case pass" framing produced a worse fix than the one directly available.

Compounding this: no test pins `_quantized_vector_bytes`/`_VECTOR_HASH_DECIMALS`'s behavior at all
— nothing regresses if this constant is changed again, nothing proves a genuinely different vector
still fails the check post-coarsening, and nothing proves a near-boundary pair now matches. The
change shipped on the strength of a code-comment narrative and one manual real-build observation,
not a runnable check (this codebase's own stated convention — see `chunk_sel_kg.py`'s and
`vector.py`'s docstrings' emphasis on tests proving claims, not comments alone).

Separately, and worth naming plainly: 03-11-PLAN.md's own text instructed the executor not to
change this module. The change was made anyway, is reasoned in the code, and is disclosed — but it
still departs from an explicit plan directive on the one module in this wave whose entire purpose
is measuring correctness, and it should have been escalated rather than executed unilaterally,
independent of whether the technical outcome (see below) turns out defensible.

**Verdict on the constant:** it should not stand as implemented. Replace the rounded-hash
comparison with a tolerance-based per-vector distance check (component-wise or max-abs-diff over
the raw float32 vectors, no rounding at all) in both `_v1_vector_pairs`/`_v2_vector_pairs`'s
comparison path. This removes the boundary-flake class entirely rather than making it rarer, and
restores full component resolution for genuinely-different-vector detection. If the hash-of-sorted-
pairs shape is kept for its whole-set fingerprint convenience, at minimum add a test that (a)
proves a real, non-trivial vector difference (e.g. swap two entities' vectors) still fails
verification at `_VECTOR_HASH_DECIMALS = 2`, and (b) documents in a runnable assertion — not only a
comment — what per-component magnitude a difference must exceed to be caught.

## Warnings

### WR-01: The `_merge_edges_then_upsert` string-weight fix is not applied to the sibling code path with the identical defect

**File:** `v1/lightrag/operate.py:1835` (compare to the fixed line at `v1/lightrag/operate.py:2370`)

**Issue:** The committed fix wraps `already_edge.get("weight", 1.0)` in `float(...)` inside
`_merge_edges_then_upsert` (line 2370), because every `BaseGraphStorage.get_edge()` backend returns
attribute values as strings. `_rebuild_single_relationship` (the cache-rebuild path) reads the
identical shape from the identical source one function up in the same file:

```python
current_relationship = await knowledge_graph_inst.get_edge(src, tgt)   # line 1739 — same source
...
weight = sum(weights) if weights else current_relationship.get("weight", 1.0)   # line 1835
```

When `weights` is empty (no extraction data carried a weight for this rebuild), `weight` is
assigned directly from `current_relationship.get("weight", 1.0)` with no `float()` coercion — the
exact unguarded read the fix elsewhere in this file exists to close. This does not crash inside
`_rebuild_single_relationship` itself (no arithmetic is performed on `weight` in that function
before it is written back to storage), but it re-introduces a string-typed `"weight"` value into
graph storage on the cache-rebuild path, which is the same class of value `_merge_edges_then_upsert`
was just hardened against — this is not proven to be currently reachable by any of the five parity
arms, but it is the same bug, one function away from the one that was fixed, and the fix cycle's
disclosure ("this is a bug fix to the pinned baseline... recorded here so the original-arm identity
stays honest") did not mention it.

**Fix:** Apply the identical `float(...)` coercion at line 1835:
```python
weight = sum(weights) if weights else float(current_relationship.get("weight", 1.0))
```
and note the second site alongside the first in `v1/README-PARITY.md`'s existing disclosure
paragraph, since both are the same baseline-identity change.

## Info

### IN-01: `verify_import`'s graph-topology assertion never checks node/edge attribute payloads

**File:** `databasise/parity/import_index.py:331-359, 430-462`

**Issue:** `_v1_graph`/`_v2_graph` read only `id`/`src, tgt` — the D-02 graph-topology assertion
compares node-id sets and edge-endpoint-pair sets, never the `attrs` payload (`description`,
`weight`, `entity_type`, etc.) each node/edge carries. An import that correctly preserves every
node id and edge pair but silently corrupts or drops an attribute value (for example, exactly the
kind of string/float weight confusion CR-01/WR-01 discuss) would pass `verify_import` cleanly. This
may be a deliberate, documented scope choice ("three assertions": chunk-text, vector-hash,
graph-topology) rather than an oversight, but it is worth naming explicitly since the review was
asked to give this importer/verifier extra scrutiny: a "verified" result names less than its own
name implies to a reader who has not read this file's internals.

**Fix:** If attribute-level fidelity matters for this phase's claims, extend the graph-topology
assertion to also compare each node/edge's `attrs` dict (or a canonical hash of it) between v1 and
v2, the same way `_vector_set_hash` already does for vectors. If it is an intentional scope
limitation, say so in the module docstring's list of "D-02's three assertions" so a reader does not
have to infer the boundary from the code.

---

_Reviewed: 2026-09-06T20:18:28Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
