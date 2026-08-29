---
spike: 005
name: laundering-test
type: code (runnable validator prototype)
validates: "Given the taint rule (effective depth = min over transitive deps) and the blast-radius rule (a node may write a shared artifact namespace only at effective depth `stage`), when both are implemented in a validator prototype and run against half-decomposed wirings drawn from the real LightRAG decomposition path, then the rule permits every legitimate middle state and refuses every opaque-derived shared write — or it blocks a legitimate middle state, in which case D4's ratchet has no usable middle, D1's cliff is vindicated, and the two-regime design re-opens"
verdict: PARTIAL — rules behave exactly as specified; the reasoning that justified them is FALSIFIED (decomposition order runs the other way); selection survives with one named amendment (quarantined namespace)
related: [001, 003]
tags: [validator, depth, taint, blast-radius, falsifier, decomposition]
---

# Spike 005: The Laundering Test — Falsifier 1 of the spike-003 selection

**This is the decisive falsifier of the selected architecture**, named in `.planning/architectures/D-VARIANTS/SELECTION.md` §Falsifiers as "correct-by-reasoning, not correct-by-evidence." Spike 003 selected D4 One Machine partly on a taint rule that was argued, never measured. This spike measures it.

## Why this runs before step 8

The fitting contract hardens around one machine. If the taint rule is wrong, the contract's §3 (Depth and containment) is wrong, and every later section that depends on the blast-radius guarantee inherits the defect. Running the test after step 8 means rewriting the contract; running it now means shaping it.

## The rules under test

Both from SELECTION.md §Contract skeleton §3, adopted as Condition 1 of the selection:

1. **The taint rule** — a node's *effective* depth is the minimum over its transitive `deps` (and its own structural depth). Depth ordering: `opaque < evidence < stage`.
2. **The blast-radius rule** — a node may write into a **shared** artifact namespace only if its **effective** depth is `stage`. `self_storage` is always legal, instance-scoped, refcounted.

Fable's ruling, which this spike exists to check, was:

> in every surveyed decomposition the ingest lane sits upstream of (or parallel to) the query-side opaque core, so an ingest-adapter's transitive deps are clean and its shared writes remain legal; what taint blocks is opaque-*derived* data entering the shared plane.

That is an argument about **decomposition order**. It is checkable against spike 001, which established which side of LightRAG is actually entangled.

## Decision rule — FIXED BEFORE RUNNING

| Outcome | Condition | Consequence |
|---|---|---|
| **PASS** | (a) legitimate middle-state shared writes permitted, **and** (b) every opaque-derived shared write refused, **and** (c) no realistic point on the LightRAG decomposition path is wrongly blocked | Selection holds; contract §3 ships as written |
| **FAIL-A** | taint blocks a legitimate middle state — the ratchet has no usable middle | **D4's central advantage over D1 evaporates.** D1's all-or-nothing cliff is vindicated, and the two-regime design re-opens |
| **FAIL-B** | an opaque-derived shared write is permitted | The blast-radius mechanism is fiction; the largest uncovered failure class from RT-selfimprove is still uncovered |
| **PARTIAL** | rules behave exactly as specified, but the *realistic decomposition order* needs a contract amendment to stay usable | Selection holds; contract §3 gains a named mechanism, and this spike specifies it |

A negative result is a successful spike. FAIL-A in particular is a finding worth more than a confirmation, because it would reverse a selection made on reasoning alone.

**Standing disqualifier:** any repair that makes the rule permit opaque-derived data into the shared plane is rejected regardless of how convenient it is. The rule exists to bound the blast radius identified as the largest uncovered mutation-failure class; a repair that dissolves it fails the spike rather than passing it.

## Method

A single Python 3 file, stdlib only, no corpus, no network — `taint.py`. It implements the registry, the wiring format, structural depth, the taint computation, and the blast-radius check, then asserts expected verdicts over a case table. Adversarial cases are included deliberately: the point is to *find* a wrongly-blocked middle state, not to confirm the happy path.

## How to Run

```bash
cd .planning/spikes/005-laundering-test
python3 taint.py          # runs the case table, prints a verdict per case, exits non-zero on unexpected result
```

## What to Expect

A per-case table of `permitted / refused` against expectation, and a verdict line. Cases 1 and 2 are the two named in SELECTION.md; cases 3–8 probe the decomposition path and the adversarial edges.

## Investigation Trail

- 2026-08-10: Spike created; decision rule fixed and committed (`384c645`) before the prototype was written or run.
- First run, 9 cases: 8 as expected, **case 3 (the real LightRAG middle state) refused** → looked like FAIL-A.
- **Modelling check before recording the verdict.** Case 3 gave the query nodes a runtime `deps` edge on the ingest node, but per the two-plane rule those are separate runs joined by an *artifact*, not one wiring. Added 3b (ingest run alone) and 3c (query run alone) to isolate the mechanism. The correction mattered: it moved the finding from "taint is wrong" to "the base rule on opaque nodes is mis-fitted to the real port order."
- Added 3d to test whether a repair exists that does not breach the standing disqualifier. It does.

## Results

**Verdict: PARTIAL** — the rules behave exactly as specified; the *argument* that justified them is falsified; the selection survives with one named amendment.

Run `python3 taint.py` to reproduce; 12 cases, exit 0.

### What holds

**The taint rule is sound.** Effective depth as the minimum over transitive deps does what it claims, including the cases most likely to leak:

- opaque core → stage extractor writing shared: **refused** (case 2)
- non-adjacent fan-in — a stage cache reading an opaque *sibling*, then writing shared: **refused** (case 7). Taint follows the partial order, not just the direct chain.
- `evidence`-depth part → stage extractor writing shared: **refused** (case 9). `evidence < stage` behaves correctly.
- parallel opaque lane does **not** taint an independent ingest lane (case 8) — no over-blocking.
- **decomposition credit survives the artifact boundary** (case 3c): a decomposed query run reading an index produced by an opaque ingest run still computes `stage` throughout. Taint does not erase the work you actually did first.

### What breaks

**The realistic entry state of the port is forbidden** (cases 3, 3b, 6). The opaque LightRAG ingest core cannot write the shared index — but producing the shared index is exactly what ingest *is*. And spike 001 [code-verified] establishes the decomposition order: *"Query path is already a named 4-stage component pipeline; index side is entangled (~1,786 lines, ontology-welded)."* The query side decomposes first because it is already component-shaped; **ingest stays opaque longest because it is the hard side**. So the machine forbids precisely the state the port begins in.

This is **not** the taint rule. 3b vs 3c isolates it: the blocker is the base blast-radius rule applied to the opaque node itself.

### What is falsified

**The reasoning behind Condition 1 of the spike-003 selection.** Fable's ruling was:

> in every surveyed decomposition the ingest lane sits upstream of (or parallel to) the query-side opaque core, so an ingest-adapter's transitive deps are clean

The decomposition runs the other way. The premise is backwards against `[code-verified]` evidence from spike 001. The *conclusion* (taint does not destroy the ratchet's middle state) survives — but for a different reason than the one given, and only with the amendment below. A selection condition resting on an inverted premise is exactly what a falsifier is for.

### The amendment (case 3d, passes)

**Add a third artifact scope: the instance-scoped QUARANTINED namespace.** An opaque node may write it; it is readable by explicit pin from another wiring; it is **never SA-1-shareable**, never declared-compatible with any recipe, and GC'd with the instance that produced it.

- The standing disqualifier holds: opaque-derived data still never enters the shared plane.
- Scopes become three, not two: `shared` (stage only) · `quarantined` (any depth, instance-scoped, single-provenance) · `self_storage` (any depth, private).
- **Honest cost:** no artifact sharing in the middle state. Two modalities over an opaque index each re-index — candidate C's N× token cost — but confined to the middle state and paid only until decomposition. Decomposition becomes the way to *earn* artifact sharing, which is the ratchet's incentive stated in tokens rather than in discipline.

### Effect on the selection

**D4 still stands, and D1's cliff is not vindicated** — the ratchet has a usable middle once the scope exists. But the selection's Condition 1 must be restated: it is the quarantined scope, not clean transitive deps, that makes the middle state legal. Contract skeleton §3 needs the third scope; §8 (opaque-node admission) needs "may write quarantined, never shared."

### Still unmeasured

The three remaining falsifiers are untouched by this spike. **Falsifier 3 — eval-bundle affordability at the required n — still outranks the selection itself.**
