---
title: D-Variants Drafting Brief — shared, binding
spike: 003
date: 2026-08-10
status: BINDING on all four variant documents
---

# D-Variants Drafting Brief

You are drafting **one** of four concrete versions of the Kernel+Sandbox architecture (candidate D) for the Databasise re-cut. Every drafter works from this same brief and does not see the others' output. Divergence is the point — do not hedge toward what you imagine the other variants say, and do not write a document that would be true of all four.

Your variant is a **design someone would actually build**, not a cell in a matrix sweep. If your assigned position forces an incoherence, say so in the document and draw the coherent design nearest to it, naming what you changed and why.

---

## 1. What candidate D is

Two regimes with a documented promotion path:

- **Kernel** — a Conductor-style regime (candidate B): modalities are declared graphs of versioned components running on machine-owned stores, with deep traces, mutation, and A/B.
- **Sandbox** — a Federation-style regime (candidate C): whole engines behind capability manifests, self-contained, answer-level comparison only.
- **Promotion** — a part that proves valuable in the sandbox crosses into the kernel.

D leads the field because *migration debt is confined to the regime that is allowed to be thrown away* — it is the only candidate whose registry growth and blast radius are both structurally bounded. Its named risks are (a) two regimes to maintain, (b) the promotion path rotting into "everything stays in the sandbox forever", (c) selector and rig having to handle both regimes.

Read `.planning/architectures/CANDIDATES.md` §0 and §D for the drawn form. **Draw the *fixed* anatomy, not the drawn one** — see §4.

---

## 2. The settled set — incorporate, never re-litigate

These are decided. A variant that argues against one of them is off-brief. A variant may state *where* it places a settled thing, never *whether*.

**Identity and versioning**

- Every component is `name@version`, immutable once referenced, lineage-tracked. Improvement = branch → A/B → promote/rollback. Nothing is edited in place; rollback is re-pinning.
- Instance identity closes over its closure: `(name@version, config_hash, resolved_dependency_ids)`. Traces record the instance hash.
- **`config_hash` includes a build/runtime environment hash.** Version pin without environment pin is the Feast version-skew failure. Binding on all variants.
- **SA-1** — recipe identity is a content hash of resolved inputs, *including* `(embed_model_id, dim, normalization, pooling)` and `(extract_model_id, prompt_hash)`. `name@version` remains a human lineage label, never the identity.
- **SA-2** — sub-recipe stamps (KV↔chunker, graph↔extraction, vector-namespace↔embedder) so an upgrade invalidates only what it touches.
- **`config_hash` is computed over the author-supplied input JSON**, canonicalized by RFC 8785 (JCS), never over a tool's normalized output. No integers outside int64; `1` ≡ `1.0`.

**Wirings**

- **Wiring specs are JSON with no evaluation semantics.** Never a language the validator must sandbox. The mutation operator emits JSON only.
- **Socket wiring is a partial order over named nodes** (`deps` + topological sort), never a total order by integer priority. Node ids are positions, never instance identities.
- **A component's kind is a tagged sum** — a single-key object whose key selects the kind and whose value is validated by that kind's schema. State it in portable vocabulary (serde external tagging / pydantic discriminated unions).
- **Arm deltas are RFC 7386 merge-patch** *(or RFC 6902 for operation-level precision)*. A differing component-kind tag replaces the whole `kind` subtree. Subtractive operations are fail-closed: a mistyped key errors, never silently no-ops.

  > **AMENDMENT (2026-08-10, post-drafting).** As originally written this clause omitted "(or RFC 6902)" and was **unsatisfiable**: RFC 7386 expresses removal as a `null` sentinel, so an unknown or mistyped key is a silent no-op *by construction* and can never be fail-closed. `MANIFEST.md:52` carries the parenthetical; `WIRING-SPEC-DRAFT.md:100` states plainly that RFC 6902 `remove` is what supplies the fail-closed property, and records the spike-004 measurement behind it — a one-character typo produced an arm that reported "reranker dropped" and shipped with the reranker still in it. The defect was introduced here, in this brief, not by the variants. All four restated it verbatim, so **every variant document contains the unsatisfiable form** and must be read with this amendment applied. The fitting contract takes: merge-patch semantics for additive/overriding deltas, RFC 6902 (or an explicitly fail-closed equivalent) for any subtractive operation.
- **The wiring validator returns all violations at once**, with JSON-Pointer paths. One-error-per-run costs an LLM repair round trip per defect. Cycles are reported **as data** (offending node names), never thrown — cyclic wirings are legal.

**The five contract clauses (RT-modularity — load-bearing)**

1. Declarations are machine-enforced preconditions; the wiring validator runs before execution and fails closed.
2. Identity closes over the closure (above).
3. Machine-minted refs with provenance: `ChunkRef = (corpus_id, recipe@version, ordinal, content_hash)`; deref raises loudly; runs record refs_in / refs_resolved.
4. Interpretation travels with the value: `ScoredItem` carries `kind`; `Score = {value, semantics, space_id}`; vector namespaces stamped with an EmbeddingSpace id; graph edges declare weight semantics; whole-graph algorithms declare required semantics.
5. Structured prompt boundary: assemblers emit typed `ContextPackage` blocks; machine-owned renderer; token counting is a machine service using the consuming model's tokenizer, stamped `counted_by`.

**The six self-improvement machine services (RT-selfimprove — all mandatory)**

0. Eval bundle@version (questions + gold + judge + corpus-hash; dev/holdout; sealed holdout)
1. Promotion Gate (A/A null, paired significance, minimum-effect floor, confirmation rule, epoch FDR, regression suite as hard gates never averaged)
2. Isolation Domain + manifest enforcement (deny-by-default net/FS/store-write, wall-clock watchdog, per-arm process)
3. Artifact Ownership + CoW + reference-counted GC (writes scoped to `recipe@version` + namespace; **cache keys include component version** — cache poisoning is the insidious failure)
4. Promotion Ledger (append-only decisions; distinct from the lineage tree)
5. Static Mutation Validator (type-check wirings and caps *before* execution)

Budgets cover 1 of 6 mutation-failure classes. Shared-artifact corruption is the largest uncovered blast radius.

**Sequencing** — eval bundle + promotion gate → isolation domain → architecture. Settled. Variants place the instruments; they may not re-order the build.

**Ledger/projection split** — running an arm SHALL NOT append to the promotion ledger. The active-wiring pointer SHALL be derivable from the ledger. Promotion verbs follow a ladder (validate / preview / run-without-promoting / promote-next / promote-now) with one gate implementation serving all transitions. Promotion itself is an atomic alias repoint plus a generation record (~1 ms, `rename(2)`-atomic, multi-artifact in one swap) — never a build.

**Substrate**

- **Nix is substrate-only. It names nothing in the architecture model.** NixOS hosts Sourcerer and Nix builds the software; the machine builds the indexes. Store paths are never component or artifact identity — they close over store directory and name, so they are not SA-1 and would create a second identity vocabulary.
- Carve-outs you may name as *implementation* (never as model vocabulary): NAR hashing as the artifact content-hash serialization (the format, not the store); systemd confinement (`confinement.enable`, `mode = "full-apivfs"`, `PrivateNetwork`, `RuntimeMaxSec`) as the isolation-domain implementation; `lib.evalModules` as one candidate implementation of machine service #5.
- No design may depend on `ca-derivations`, `dynamic-derivations`, or `impure-derivations`.

**Scope**

- `model-weight-access` modalities (DSI, ROME/MEMIT, RAFT, RL retrieval) are a declared non-goal, not a gap.
- Never depend on a live RAG framework. Build a Haystack-*shaped* executor; never take the dependency. Vendor pinned tags only.

---

## 3. Disqualifiers — auto-fail, checked at drafting time

Not scored down later. If your variant trips one, the honest move is to report it as a falsification of your assigned position, not to widen the design until it stops being your variant.

**DQ-1 — Executor primitives.** A kernel style that cannot host all three is disqualified:
- **fan-out / join** as a first-class node type alongside loop-with-condition
- **ephemeral subgraph** — a planner emits a runtime graph per query; the *planner* is the versioned artifact and the *emitted plan is recorded as trace data*, so the run stays reconstructable. Versioned wirings and ephemeral plans have separate lifecycles.
- **non-adjacent fan-in** — a node may read a sibling's output (an eval component needs pre-assembly evidence *and* the final answer)

**DQ-2 — Two-plane separation.** The artifact/lineage plane (DAG, content-addressed: component versions, recipes, index artifacts, wiring specs, traces, lineage) and the execution plane (loops, branches, fan-out/join, planner-emitted subgraphs — kernel-owned) stay separate. A completed run's trace is an unrolled DAG. No component may treat the artifact plane as a runtime control channel. **A variant that merges the planes is disqualified.**

Note carefully: **a cyclic wiring is not a merged plane.** A wiring spec is DAG-plane data whose *content* describes a possibly-cyclic execution graph; the cycles live inside the value, not in the dependency edges between artifacts. No variant may be disqualified on the grounds that "its wirings have loops."

**DQ-3 — Second identity vocabulary.** Any scheme where a store path, a filesystem location, an import path, or any tool-native address serves as component or artifact identity.

**DQ-4 — Environment-unpinned identity.** Instance identity that omits the environment hash.

**DQ-5 — Wirings with evaluation semantics.** Any wiring format the validator must sandbox to read.

---

## 4. Draw the fixed anatomy

`CANDIDATES.md` §0 has ten reviewed **must-fix** defects (`ANATOMY-REVIEW.md`). Your diagrams inherit the *fixed* version. Minimum edit set:

1. **Ingest lane** with a source-polymorphic seam (`documents | repo | stream | nothing` — CAG and codebase-memory-mcp break the document assumption), per-document chunker, and **per-chunk** provenance. Ingest is currently a mixin welded onto the LightRAG class; cutting it off the part is real, un-costed work and the single largest port cost.
2. **Four service boxes**: artifact registry (split from the component registry — different lifecycles, sizes, immutability, and deletion policies), wiring validator (fails at *load*, not at query), eval set + scorer + scoreboard, reindex planner (`recipe@vA → recipe@vB ⇒ {reuse | re-embed | re-extract | rebuild}` + cost estimate).
3. **Three rewired edges**: harness as an optional **wrapper with a back-edge and a stacking self-edge** (never a pass-through — a harness wraps a part and calls it N times); the rig actually **connected** (fans out N wirings, reads traces + artifact registry, consumes the eval set, writes the scoreboard, feeds promotion); budget as an **enclosure over the whole execution including ingest**, not a side-arrow to one tier.
4. **`EMB -.binds.-> VEC`** plus the rule **"index-time clients bind artifacts; query-time clients do not"** — rerank and generator upgrades are free, extractor and embedder upgrades cost a rebuild. Embedder identity is mandatory in the contract: the machine refuses to write vectors it cannot attribute.

Also cheap and expected: graph-store `validity` as a declared sub-capability with an `as_of` field on the query contract; `upstream_ref` (repo + tag/commit + file/symbol) on component registry entries; selector policy as a versioned artifact; partial results first-class (budget-halted and degraded runs are traced and scored, never discarded); manifests may declare **degradation paths** as well as requirements.

Two live hazards to place somewhere: the chunker is selected **per document** and one strategy (`V`) consumes the embedder, so chunk *boundaries* are a function of the embedding model — the "shared KV is paradigm-neutral" claim is false under it, and this lands hardest on D's cross-regime shared corpus feed. And LLM role→binding is **hot-updatable at runtime**, so the trace must record the *resolved model per role per run*, never the role name.

---

## 5. The three scenarios — walk all three, same order, in every variant

These are the comparison surface across variants. Be concrete: name the artifacts touched, what invalidates, what is recomputed, what the trace records, who decides.

**S1 — Embedder swap.** A query-side and index-side embedder change. What invalidates, what is reused, what the reindex planner classifies, what happens to in-flight A/B arms straddling the migration, and how the rig avoids attributing the resulting regression to the component under test rather than to the invalidated artifact.

**S2 — LightRAG ships v2 upstream.** Which components have upstream deltas, how you know, what a re-port costs, what the sandbox absorbs versus what the kernel must re-implement, and whether the answer is a diff-able list or a blind decision.

**S3 — One full mutate → A/B → promote cycle.** From mutation operator emitting a wiring delta, through static validation, isolation, both arms running, evidence collection, the promotion gate, the ledger append, and the alias repoint. Name every service touched, in order. State what the gate sees and what it refuses.

---

## 6. Required document structure

Write to your assigned landing pad. Markdown. Mermaid for diagrams.

```
# D<N> <Name> — <one-line position>

## Position          — one paragraph; what this variant believes that the others don't
## The five axes     — table: kernel style / containment / promotion / instruments / comparison depth, each with a sentence of justification
## Anatomy           — mermaid, the fixed anatomy (§4), specialized to this variant
## Execution model   — mermaid or prose; how the kernel executes; explicitly: fan-out/join, ephemeral subgraph, non-adjacent fan-in (DQ-1)
## The sandbox boundary — what is enforced, by what mechanism, and what crosses it
## Promotion         — the exact mechanics; what evidence gates it; what is discarded
## Instruments       — where the six machine services live; who owns the eval bundle, gate, ledger, validator
## Comparison depth  — how kernel-deep and sandbox-shallow evidence are labelled so promotion never runs on silently-mixed quality
## Scenario S1 / S2 / S3 — the three walk-throughs (§5)
## Advantages        — what this variant buys that a reasonable alternative does not
## Disadvantages     — honest; a variant with no real cost has not been drafted seriously
## Disqualifier check — DQ-1 through DQ-5, each answered explicitly, with the mechanism that satisfies it
## Rubric scoring    — the ten goals (ARCHITECTURE-RUBRIC.md), scored honestly; no variant scores all ten
## Machine services  — services 0–5: where each lives and what it costs this variant
## Contract clauses  — clauses 1–5: how each is satisfied
## What would falsify this variant — concrete, observable; the thing that if true means this design is wrong
## Contract skeleton implied — the boundaries this variant would freeze into the fitting contract (feeds SPIKE-PLAN step 8)
```

**Evidence tagging is mandatory on every non-trivial claim**: `[code-verified]` / `[docs-verified]` / `[paper-claim]` / `[inference]`. Most of what you write is `[inference]` — that is expected and fine. What is not fine is an `[inference]` dressed as a fact. Published benchmarks never settle a decision.

Length: whatever the argument needs. Roughly 300–500 lines is typical. Do not pad, do not compress away the scenarios.

---

## 7. Inputs

Read what you need, in roughly this order:

- `.claude/skills/spike-findings-rag-graph-vector-raw/SKILL.md` + `references/*.md` — curated findings from spikes 001, 002, 004
- `.planning/architectures/CANDIDATES.md` — §0 shared anatomy, §D (and §A/§B/§C for what D inherits from each)
- `.planning/architectures/ANATOMY-REVIEW.md` — the twenty findings, ten must-fix; §4 above is the summary, the document has the evidence
- `.planning/ARCHITECTURE-RUBRIC.md` — the ten goals you score against
- `.planning/redteam/RT-modularity.md`, `RT-upgradability.md`, `RT-selfimprove.md` — the attack scenarios; re-run them against *your* variant
- `.planning/research/GAP-SWEEP.md` — §3 is the growth map (how the system grows as parts are added, grouped by artifact to edit; zero new store types); §3.8 is DQ-1; §4 is the five stress tests
- `.planning/research/SYNTHESIS.md`, `PRIOR-ART.md` — machine primitives, adopt/avoid list
- `.planning/architectures/WIRING-SPEC-DRAFT.md` — the wiring design as it stands
- `.planning/notes/two-plane-separation.md` — DQ-2 in full
- `.planning/research/NIX-LEVERAGE.md` — the substrate boundary and what survived as implementation carve-outs
- `.planning/spikes/MANIFEST.md` — the Requirements section, binding

## 8. Output

One file at your assigned path. Do not write anywhere else. Do not edit shared documents. Do not commit.

Your final message back is a **≤15-line summary**: your variant's position in one sentence, its single strongest advantage, its single most serious cost, the DQ check results, and anything you found that you believe falsifies the assigned position or the lineup itself. Do not restate the document.
