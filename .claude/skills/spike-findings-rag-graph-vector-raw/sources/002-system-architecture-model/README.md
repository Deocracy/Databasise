---
spike: 002
name: system-architecture-model
type: theory
validates: "Given the component inventory, rubric, and 24-system survey, when 4 candidate architectures are drafted, red-teamed for modularity+upgradability, checked against prior art, and stress-tested by an exhaustive RAG-type gap sweep, then at least one architecture satisfies the 10 rubric goals with documented fixes — or none does and the concept pivots"
verdict: PENDING
related: [001]
tags: [architecture, red-team, prior-art, gap-sweep, fitting, versioning]
---

# Spike 002: System Architecture Model

## What This Validates

**Given** the component inventory, the 10-goal rubric (versioning-as-improvement mandated), and the 24-system modality survey,
**when** four candidate architectures (A Stage Bus, B Conductor, C Federation, D Kernel+Sandbox) are drafted as positions on the five tension axes, red-teamed specifically for **modularity and upgradability**, compared against **prior art** (does anything already do this? what do we adopt?), and stress-tested by an **any-and-every-way gap sweep** of RAG types not yet surveyed,
**then** at least one architecture (possibly amended) satisfies the rubric with documented fixes and a defensible selection rationale — or none survives and the machine/fitting concept needs a pivot.

This is a **theory spike**: the "experiment" is adversarial analysis and deep research executed by a background workflow, not code. Code-level questions it surfaces become future standard spikes (003+).

## Inputs (already committed)

- [CANDIDATES.md](../../architectures/CANDIDATES.md) — the four candidates + shared anatomy diagrams
- [SYNTHESIS.md](../../research/SYNTHESIS.md) — fitting requirements from the modality survey
- [ARCHITECTURE-RUBRIC.md](../../ARCHITECTURE-RUBRIC.md) — the 10 component goals
- [GOALS.md](../../GOALS.md), [PROJECT.md](../../PROJECT.md) — goal ladder, 16 test dimensions
- Modality survey: research/MODALITIES-{GRAPH, VECTOR-TREE, AGENTIC, CODE-AND-ALIEN}.md

## Experiment in Flight (landing pads)

A background workflow (12 agents: 6 Sonnet research, 3 Opus red-team, 1 Opus anatomy review, 2 Opus consolidators — no Fable per user directive) is producing the evidence. Its outputs land at these paths and are **part of this spike**:

| Landing pad | Producer | Question it answers |
|---|---|---|
| `.planning/architectures/ANATOMY-REVIEW.md` | Opus reviewer | What must change in the Shared Anatomy (missing seams, wrong relationships, nesting errors, upgrade blind spots)? |
| `.planning/redteam/RT-upgradability.md` | Opus attacker | How does each candidate age (upstream v2, embedder swap, version skew, 2-years-later test)? |
| `.planning/redteam/RT-modularity.md` | Opus attacker | Is the modularity real, or does hidden coupling (tokenizer, embedding-space, prompt-format, ontology) survive the manifests? |
| `.planning/redteam/RT-selfimprove.md` | Opus attacker | Does branch→A/B→promote survive registry explosion, weak eval power, and mutation blast radius? |
| `.planning/research/prior-art-{1,2,3}-*.md` → `PRIOR-ART.md` | 3 Sonnet + Opus consolidator | Does anything already do this (FlashRAG, AutoRAG, Haystack 2.x, LangGraph, DSPy, MLflow/DVC/Nix)? Adopt vs build? |
| `.planning/research/gap-{1,2,3}-*.md` → `GAP-SWEEP.md` | 3 Sonnet + Opus consolidator | Which RAG types are we missing for "RAG-it-any-and-every-way"? Each: expressible-now / new-capability / new-store / out-of-scope |

## How to Run

Not runnable code. To reproduce: re-run the workflow script at the session's workflow scripts directory (`rag-anatomy-redteam-research-*.js`) or re-issue the equivalent research prompts. Verification is by reading the landing-pad documents against the validation statement above.

## What to Expect

- Concrete amendment list for the Shared Anatomy (v2)
- Per-candidate attack narratives with severity and fixes; a modularity+upgradability ranking of A/B/C/D with the amendments that would change it
- A verdict on prior art: closest three existing systems and the exact gap; adopt-list (candidates: Haystack component protocol, AutoRAG search loop, DSPy optimizer pattern, Nix content-addressing) vs build-list
- The full RAG taxonomy tree with the delta the fitting must absorb
- Updated candidate set feeding step 8 of SPIKE-PLAN.md (fitting contract spec)

## Observability

Workflow transcript: session `subagents/workflows/wf_2092b67a-3e4/` (journal.jsonl records each agent's return). Every landing-pad doc tags claims [code-verified]/[docs-verified]/[paper-claim]/[inference].

## Investigation Trail

- 2026-08-10: Candidates drafted (4 architectures over 5 tension axes) after the 24-system survey; committed with diagrams + artifact page
- 2026-08-10: User directives locked: versioning is THE improvement mechanism; red-team target = modularity + upgradability; completeness target = "RAG-it-any-and-every-way"; Opus/Sonnet only in subagents
- 2026-08-10: Workflow `wf_2092b67a-3e4` launched (12 agents, 3 phases: Research → Red Team → Consolidate)
- 2026-08-10: Spike regularized into GSD structure (this README + MANIFEST); spike 001 retroactively manifested
- 2026-08-10: Workflow `wf_2092b67a-3e4` completed — 12/12 agents, 0 errors, ~1.24M subagent tokens, 252 tool uses. All landing pads filled. Findings folded below.

## Results

**Verdict: VALIDATED ✓ (with mandatory amendments and one sequencing correction)** — the concept survives its own red team. At least one architecture (D, amended; importing A's boundary-ownership and B's pilot-before-commit property) satisfies the rubric with documented fixes. No pivot needed. But the red team's largest finding is about *order of work*, not architecture.

### 1. The sequencing correction (biggest single finding)

All four candidates fail the improve-loop as documented — not on structure, on **instrumentation**: a 30–50-question eval set with no A/A null calibration and no significance gate promotes mutations on noise, and the eval set is currently the only unversioned artifact in the design. **Order of work must be: eval bundle + promotion gate first (architecture-independent), then isolation domain, then choose between B and D.** Building the machine before the instrument makes year one of "self-improvement" an unfalsifiable random walk.

### 2. Red-team rankings

- **Upgradability:** D > A > B > C. D wins because migration debt is confined to the throwaway regime. Surprise second: A — a machine-owned named boundary is the only place a shim/migration lives exactly once ("artifact sharing and migration cost are the same axis"). No amendment fixes C: not-decomposing is precisely what upgradability cannot survive. C is a *regime*, not an architecture — D already models it as one.
- **Modularity:** prior (B and D only viable) survives with corrections: B beats A *only if* the five contract clauses are contract, not aspiration; C is more honest than credited (no fake modularity to break); D gains an unstated cost — cross-regime comparison collapses to the shallowest denominator, so promotion runs on the weakest evidence. **[REJECTED — `SELECTION.md ## The shallowest-denominator ruling` (spike 003): this condition never entered the settled set and is superseded; comparison is instead defined at the greatest common depth of the two arms.]**
- **Self-improvement:** D (conditional on sandbox respecified as the isolation domain + improvement loop kernel-only) > B; A and C additionally fail blast-radius containment.

### 3. Mandatory amendments (highest-value)

- **SA-1:** index-recipe identity = **content hash of resolved inputs** including `(embed_model_id, dim, normalization, pooling)` and `(extract_model_id, prompt_hash)`; artifacts store the hash; compatibility checks run on the hash, `name@version` stays as the human lineage label. Closes the invisible-embedder-swap failure (the dimension-preserving swap that silently poisons a namespace).
- **SA-2:** split recipe provenance into sub-recipe stamps — KV↔chunker, graph↔extraction, each vector namespace↔embedder — so an embedder change re-embeds only, never re-extracts (extraction is the token-expensive side, spike 001).
- **Five contract clauses** (RT-modularity): (1) declarations are machine-enforced preconditions, fail closed; (2) identity closes over the closure `(name@version, config_hash, dependency_ids)`; (3) machine-minted refs with recipe provenance, loud resolution; (4) interpretation travels with the value (`kind`, score semantics, embedding-space ids); (5) structured prompt boundary — typed context blocks, machine-owned renderer, machine-owned token counting stamped `counted_by`.
- **Anatomy v2 edit set** (ANATOMY-REVIEW: 10 must-fix): add ingest path + chunker placement (per-document, embedder-coupled); eval set + scorer + results store; split artifact registry from component registry; wiring validator/capability negotiator; harness drawn as optional *wrapper with back-edge and stacking self-edge*, never a pass-through; rig actually wired (fan-out, reads trace+artifacts, consumes eval set, feeds promotion); budget enclosing the whole execution including ingest; embedder→vector coupling made visible; staleness/GC ownership; migration/reindex planner.
- **Six machine services** self-improvement actually requires: eval bundle@version (artifact), promotion gate (A/A null + paired significance + confirmation rule + FDR + hard-gate regression suite), isolation domain with *enforced* manifests (deny-by-default network/FS/store-write), artifact ownership + CoW + GC, promotion ledger (decisions, distinct from lineage), static mutation validator. Budgets cover only one of six mutation-failure classes; shared-artifact corruption is the largest uncovered blast radius, LLM-cache poisoning the most insidious.

### 4. Prior art (PRIOR-ART.md)

**Nothing does all four** (agnostic fitting + versioned components + parallel comparison + self-improvement); 18 systems surveyed, the union covers all four, the intersection is empty. Closest: AutoRAG (trial→promote as data, zero version axis, repo since repurposed), DSPy (only shipped self-improvement, but versions predictor state never topology), Haystack 2.x (best executor contract, identity is an import path — exactly what goal 7 forbids). **The novel work is one seam: `name@version`-with-lineage as node identity inside a declared graph.** 15 adopt-patterns, 22 avoid-failures extracted; field confirmation of A's ceiling (LlamaIndex *removed* its DAG-only QueryPipeline: "inability to perform loops… simply unacceptable"). Build-vs-adopt: build a Haystack-*shaped* executor (don't take the dependency); Nix content-addressing on promotion only (cheap hashes in flight); DSPy narrowly for prompt-shaped components; vendor AutoRAG's strategy.py from its legacy tag; registry = three Cozo relations + recursive Datalog GC.

### 5. Gap sweep (GAP-SWEEP.md) — "RAG-it-any-and-every-way"

45 new types consolidated; taxonomy is **8 axes, not a partition** (query-transform / index recipe / retrieval mechanism / control flow / data modality / generation integration / meta layer / where-knowledge-lives). Verdicts: 16 wire-today, 4 declared-graph-only, 13 need a new capability, 4 need store *sub*-capabilities, 6 contract additions, 7 out-of-scope. **No sixth store type needed by anything in scope.** Six of seven exclusions collapse to one declared non-goal: `model-weight-access` (DSI, ROME/MEMIT, RAFT, RL retrieval, RETRO-style) — to be stated in the viability verdict as chosen-not-to-host, not a silent gap. New capabilities: `self-ingesting`, `deferred-extraction`, `parse-derived-graph`, `pass-through-retrieve`, `live-external-retrieval`.

### 6. Follow-up spikes surfaced (candidates for 003+)

1. Zero-copy branching of artifacts against **Cozo specifically** — storage property, must be verified not assumed
2. Content-hash recipe identity end-to-end (SA-1) on the real parity harness
3. PPR-through-fitting overhead (from spike 001, still open)
4. Runtime-arity fan-out (LangGraph `Send()`-style) — expressible in none of A/B/C/D as drawn; needs a home before the contract freezes
