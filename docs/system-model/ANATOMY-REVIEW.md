# Shared Anatomy — Review (improvements only)

**Status:** archived-with-standing — fully dispositioned in `ANATOMY.md ## Appendix A — ANATOMY-REVIEW disposition`; tracked at `SYSTEM-MODEL.md ## §ST`.

Scope: CANDIDATES.md §0 only (both mermaid diagrams + the prose between them). Candidates A–D are untouched here; several findings below change what those candidates inherit, so this review should land before the red-team round.

Evidence key: `[code-verified]` = read this session in `Databasise/upstream-venv/Lib/site-packages/lightrag/`; `[doc]` = asserted with a tag in SYNTHESIS.md / PROJECT.md / ARCHITECTURE-RUBRIC.md (their own tags carry); `[inference]` = my architectural reasoning, unverified.

Severity: **must-fix** (the anatomy is wrong or silently unsafe as drawn — a candidate built on it inherits the defect) · **should-fix** (a real gap that will be paid for later) · **nice** (clarity).

New evidence gathered for this review, because it changes several items:

| # | Finding | Where |
|---|---|---|
| F1 | Vector collections are already namespaced by embedder: `_generate_collection_suffix()` → `f"{safe_model_name}_{embedding_dim}d"`. It returns `None` when `model_name` is absent, while `embedding_dim` is required. | `lightrag/base.py:240-265` `[code-verified]` |
| F2 | Four shipped chunkers (`F`/`R`/`V`/`P`), dispatched **per document** from `doc_process_opts.chunking`, under two coexisting contracts (legacy positional + keyword file-chunker). | `lightrag/chunker/__init__.py` `[code-verified]` |
| F3 | `chunking_by_semantic_vector` ("V") **consumes an `EmbeddingFunc`** — chunk *boundaries*, not just vectors, are a function of the embedding model. | `lightrag/chunker/__init__.py` `[code-verified]` |
| F4 | An eval seam already ships: `evaluation/eval_rag_quality.py` (RAGAS faithfulness / answer-relevance / context-recall / context-precision, driven against a REST `--ragendpoint` with a dataset JSON) and `evaluation/offline_retrieval_check.py` (deterministic lexical ranker, no LLM). | `lightrag/evaluation/` `[code-verified]` |
| F5 | LLM role registry is `extract`, `keyword`, `query`, `vlm` — and the module drives **hot config updates** of role→binding at runtime. | `lightrag/llm_roles.py:53-56` + module docstring `[code-verified]` |
| F6 | Ingest is a **mixin welded onto the `LightRAG` class** (`_PipelineMixin`), depending on `self.full_docs`, `self.doc_status`, `self.tokenizer`, `self._process_extract_entities`. | `lightrag/pipeline.py` docstring `[code-verified]` |
| F7 | No chunker/recipe/provenance field exists on stored chunks: grep of `chunker_name|chunk_method|recipe|provenance` over `base.py` + `chunk_schema.py` returns zero hits. | `[code-verified negative]` |

---

## A. Missing boxes and seams

### 1. There is no ingest path in the machine diagram at all — must-fix

Diagram 1 has exactly one entry point (`SEAM --> SEL`), and it is a *query* entry. The universal core is `part.ingest(source)` plus retrieve/answer `[doc: SYNTHESIS §1]`, so half the contract is undrawn. Diagram 2 shows a chunker, but inside a "shared artifact" subgraph with no connection to diagram 1's machine, so no reader can tell whether ingest is machine-owned, part-owned, or Sourcerer-owned.

Change: add a second seam and a machine-side ingest lane — `INGEST["Ingest seam: source → doc-status → chunker@v → recipe run"]` entering `MACHINE` in parallel with the query seam, feeding `PARTS`/`STORES` via the recipe. Draw source polymorphism on it (`documents | repo | stream | nothing`), since CAG and codebase-memory-mcp break the document assumption `[doc: SYNTHESIS §1]`.

Why it matters beyond tidiness: F6 shows the upstream ingest pipeline is a mixin on the modality object, reading `self.full_docs`/`self.doc_status`/`self.tokenizer` `[code-verified]`. The inversion decision ("machine owns DBs and clients, part owns orchestration" `[doc: PROJECT Key Decisions]`) therefore requires *cutting ingest off the part*, which is real, un-costed work. An anatomy with no ingest box hides the single largest port cost — consistent with spike 001's finding that the index side is the entangled ~1,786-line side `[doc: PROJECT Context]`.

### 2. The chunker is drawn as one recipe-level component; it is per-document and embedder-coupled — must-fix

Diagram 2 shows `chunker@1.2` as a single node inside `RECIPE`. F2 shows chunking strategy is selected **per document** at ingest `[code-verified]`, and F3 shows one strategy consumes the embedder `[code-verified]`.

Two consequences the anatomy must express:
- Provenance is **per-chunk**, not per-recipe-run. A corpus can legitimately contain chunks from four strategies. F7 says no such field exists today `[code-verified negative]` — so "artifact shareability = same or declared-compatible index recipe" `[doc: SYNTHESIS §5]` is currently uncheckable at the granularity it actually varies.
- The PROJECT key decision "**shared KV across parts**; chunks/doc-status are paradigm-neutral" is false under the `V` chunker `[inference from F3]`: change the embedding model and chunk text itself changes, so the shared KV is no longer shared. Either the anatomy marks embedder-dependent chunkers as recipe-bound (not shared-KV), or the machine forbids them in the shared lane. This is a silent correctness issue, not a diagram issue.

Change: split the node into `chunker@v (strategy per doc)` and annotate the edge into `ART` with "per-chunk provenance: chunker@v (+embedder@v if strategy=V)". Add a footnote to the shared-KV claim.

### 3. No eval set, no scorer, no results store — must-fix

`RIG["Comparison rig"]` is a single box. Goal 4 demands "comparable outputs, token counts, and **quality scores on our own eval set**" `[doc: GOALS]`, and the improvement loop is "A/B both versions … → promote winner" `[doc: RUBRIC goal 7]`. A rig with no eval-set input and no scorer output cannot close that loop.

Change: add three boxes and wire them —
```
EVALSET["Eval set@version (per domain: single-hop / multi-hop / summary)"] --> RIG
SCORER["Quality scorer (judge role + deterministic checks)"] --> RIG
RIG --> BOARD[("Scoreboard: run × wiring × versions × tokens × scores")]
```
Three points the boxes force into the open:
- **The eval set is itself a versioned artifact.** Scores are comparable only within one eval-set version; growing the eval set silently invalidates the scoreboard. Nothing in §0 versions it today.
- **The judge is an LLM client role**, so it belongs in `CLIENTS` and is version-coupled like any other. If the judge model changes mid-A/B, the measured "improvement" is the judge's drift. F5 shows role→binding is **hot-updatable at runtime** `[code-verified]`, which makes this a live hazard, not a hypothetical.
- F4 shows an inherited starting point exists (RAGAS + an offline lexical check) but it is **endpoint-shaped**: it drives a REST server with a dataset JSON `[code-verified]`. That shape can only ever measure answers, never stages — so Candidate A's headline claim (stage-level diff) and Candidate D's "deep in kernel" both need a rig the upstream code does *not* provide. Worth saying out loud in §0 rather than discovering it in the build.

### 4. Artifact registry is conflated with the component registry — must-fix

`REG["Component registry name@version + lineage"]` is the only registry. Diagram 2 puts provenance inside the artifact node (`provenance: ER1@v2`). These are two registries with different lifecycles and must be separate boxes:

| | Component registry | Artifact registry |
|---|---|---|
| Contents | code identities `name@version`, contract vs behavior version, lineage | which stored namespace was produced by which `recipe@version` + chunker@v + extractor@v + **embedder model/dim** + corpus id + time |
| Size | bytes | gigabytes |
| Immutability | free `[doc: RUBRIC goal 7]` | expensive (see #17) |
| Deletion | never | required |
| Read by | the wiring validator, at load | the compatibility check, per query |

Change: add `AREG["Artifact registry: namespace → recipe@v + chunker@v + extractor@v + embedder@model@dim + corpus"]` inside `SERVICES`, with edges `AREG --- STORES` and `AREG --> REG` (a recipe version *references* component versions). Then diagram 2's `ART` node is a *row in AREG* rather than a floating provenance string, and "one recipe, many wirings" becomes checkable instead of asserted.

### 5. No wiring validator / capability negotiator — must-fix

Manifests appear in prose ("declares what it implements and what machine primitives it requires" `[doc: RUBRIC goal 3]`) and in Candidate C's boxes, but §0 has no box that *reads* a manifest. Without it, "declared capability" is documentation, not a mechanism.

One box catches five distinct failure classes that are otherwise all silent or late:
- vector store lacks `score_all()` → HippoRAG 2 cannot run `[doc: SYNTHESIS §2, code-verified there]`
- graph store lacks bulk-export → PPR wirings cannot run `[doc: SYNTHESIS §2]`
- LLM client lacks logprobs → Self-RAG/FLARE need the prompt-mediated degradation path `[doc: SYNTHESIS §3]`
- query-time embedder ≠ index-time embedder → **silently wrong results**, see #16
- wiring pins a component version that no longer exists / recipe version the part cannot read `[doc: RUBRIC goal 6]`

Change: `VAL["Wiring validator: manifest requirements × machine capabilities × artifact provenance — fails at load, not at query"]` between `SEL` and execution, reading `REG` + `AREG`. Placing it at *load* time (not per query) is the point: this is the box that makes a wiring's validity a static property.

### 6. No migration / reindex planner — should-fix

Nothing in §0 answers "recipe@v1 artifacts exist; wiring now wants recipe@v2 — what has to be recomputed?". Versioning without a migration path is versioning that can ship exactly one version. Two concrete instances are already on the books: the Cozo bi-temporal "additive `Validity` column" Phase-6 migration `[doc: PROJECT Context]`, and every embedder change (#16).

Change: `MIG["Reindex planner: recipe@vA → recipe@vB ⇒ {reuse | re-embed | re-extract | rebuild}, cost estimate"]` in `SERVICES`, reading `AREG`. The value is the *classification*, which is the cheap thing the anatomy should promise: a query-side component bump reuses everything (near-zero cost `[doc: RUBRIC goal 7]`); an embedder bump re-embeds but may reuse chunks (unless strategy `V`, per #2); an ontology/extractor bump re-extracts; a chunker bump rebuilds. Also needs a dual-artifact/shadow window, or no A/B can straddle a migration.

### 7. The API-client box does not match the real role registry, and has no phase split — should-fix

`LLM["LLM roles: extract/filter/answer"]` vs the actual registry `extract | keyword | query | vlm` `[code-verified, F5]`. `keyword` is missing (it is the query-side LLM call that most affects retrieval, and therefore a prime mutation target); `filter`/`answer` are aspirational. Separately, SYNTHESIS §3 requires embed/rerank be declared **per phase** (index-time vs query-time) "so wiring is validated up front" `[doc]` — diagram 1 shows no phase split, which is precisely the information #16's check needs.

Change: label the clients `index-time` vs `query-time`, use the real role names plus declared extensions, and add `JUDGE` as a role (#3). Add a note that role→binding is hot-updatable `[code-verified, F5]`, therefore **the trace must record the resolved model per role per run**, not the role name.

---

## B. Wrong or misleading relationships

### 8. `SEL --> HARNESS --> PARTS` makes the harness a mandatory pass-through — must-fix

Three errors in one edge chain:
- **Optionality.** Most runs have no harness. As drawn, every query traverses the harness tier.
- **Wrapping vs sequencing.** A harness *wraps* a part and calls it repeatedly (CRAG re-retrieves after grading); the arrow shows a single forward pass. This is the diagram's most load-bearing wrong claim, since test dimension 5 is exactly "harnesses wrap any modality, stack, and are themselves selectable" `[doc: PROJECT]`.
- **Stacking.** `H1` and `H2` are drawn as siblings with no composition edge, yet Self-CRAG nests CRAG over Self-RAG in published code `[doc: SYNTHESIS §4, code-verified there]`.

Change: `SEL --> PARTS` direct, plus `HARNESS` as an optional wrapper with a back-edge (`HARNESS --> PARTS` and `PARTS --> HARNESS` labelled "N calls"), and a self-edge on `HARNESS` labelled "stacks". The visual claim to make is *containment* — harness ⊃ part — not sequence.

### 9. The comparison rig is connected to nothing — must-fix

`RIG` sits inside `SERVICES` with zero edges, which reads as decorative. It is the mechanism behind end-state goal 4 and the entire improvement loop.

Change, minimum viable wiring: `RIG` fans out N wirings at/above `SEL` (parallel run on one corpus), reads `TRACE` and `AREG`, consumes `EVALSET`, writes `BOARD`, and is the input to promotion. Also note the two comparison *depths* explicitly at the rig, since the candidates differ on exactly this axis and §0 currently gives them no shared vocabulary for it.

### 10. Budget is attached to `PARTS` only, which inverts rubric goal 10 — must-fix

`PARTS -.metered by.-> BUD` — but the looping risk lives in the harness tier and (in Candidate B) the executor, not in the part. "No component owns its own loop limits" `[doc: RUBRIC goal 10]` and "every looping family hand-rolls max-steps/max-tokens today" `[doc: SYNTHESIS §4]`.

Change: draw `BUD` as an enclosure around the whole `SEL → HARNESS → PARTS → CLIENTS` execution (or an edge from `BUD` to the execution boundary), not a side-arrow to one tier. Budget must also cover ingest (an extraction run is the most expensive thing the machine does) — which is invisible while #1 is unfixed.

### 11. Trace is drawn as a passive sink fed only by parts — should-fix

`PARTS -.emit.-> TRACE`. The selector's choice and the harness's loop decisions are precisely what self-improvement mutates and what a regression gets attributed to; store/client spend is where tokens actually go (test dimension 13). If they do not emit, the trace cannot support goal 9 ("every component emits its trace … tagged with the component versions involved" `[doc: RUBRIC]`).

Change: `SEL`, `HARNESS`, `PARTS`, `CLIENTS`, `STORES` all emit to `TRACE`; label the trace payload `versions + resolved models + tokens + time + IO refs`.

### 12. The seam is drawn inside Sourcerer — should-fix

`SEAM` sits in the `SOURCERER` subgraph, implying the GUI owns the machine's public surface. Then a second consumer (CLI, the rig, the self-improvement loop, another app) has no drawn entry, and "the REST/MCP seam stays modality-agnostic" `[doc: GOALS 6, test dim 9]` reads as a GUI property rather than a Databasise property.

Change: move `SEAM` onto the `MACHINE` boundary; `APPLETS` becomes one client of it alongside `RIG`/CLI. Cheap edit, and it makes the seam-stability requirement testable against something other than the GUI.

---

## C. Nesting errors

### 13. The temporal / Cozo validity layer is absent, and the `as-of` parameter has nowhere to live — should-fix

Tension axis 4 is "temporal placement" `[doc: SYNTHESIS §7]` and every candidate takes a position on it, but §0 provides no vocabulary — so each candidate invents its own. `GR` lists sub-capabilities (`pointwise + bulk-export`) and simply omits validity.

Change, two parts:
- Add `validity (valid_at/invalid_at, created_at/expired_at)` as a **declared sub-capability of the graph store**, exactly parallel to `score_all` on `VEC`. That is the correct nesting: bi-temporal edges are a store property, and contradiction invalidation is deterministic date arithmetic `[doc: SYNTHESIS §6.1, code-verified there]` — machine-layer logic, not modality logic.
- Note the alternative placement (a Graphiti-style temporal *part*) as an annotation on `PARTS`, so the axis is visible without prejudging it.

The consequential half: an **`as_of` / time-context field on the query contract** threads seam → selector → harness → part → store. No box shows it, and it is the kind of parameter that is nearly free to design in now and expensive to thread later `[inference]`. Absence of `time_travel|as_of|bitemporal` anywhere in the archive `[doc: PROJECT spike 001 correction]` means this is a forward constraint with no legacy to inherit — all the more reason to place it in the shared contract before four candidates harden around its absence.

### 14. The two diagrams do not share vocabulary, so the nesting claim is asserted rather than shown — should-fix

Prose says "Parts sit inside the machine. Components sit inside parts." Diagram 1's parts (`M1` LightRAG-local, `M2` HippoRAG2, `M3` code-graph) are flat leaf boxes with nothing inside them; diagram 2 introduces a disjoint vocabulary (`RECIPE`/`ART`/`W1`/`W2`) that never names `M1`. A reader cannot see that `M1 = W1 over ART`.

Change: rename so diagram 2 is explicitly a zoom of `M1` — e.g. title it "Zoom: M1 = lightrag-local@3.1 (wiring) × ER1@v2 (recipe)" and label `W1` with `M1`. Zero structural cost, and it makes the central sharing claim legible.

### 15. Diagram 2 nests the recipe and the artifact in one subgraph — should-fix

`RECIPE["Index recipe ER1@v2 (shared artifact)"]` contains both the producing components (`CH`, `EX`) and the produced artifact (`ART`). The title even calls the *recipe* the shared artifact. Recipe = versioned spec (code identities); artifact = data with physical cost, a corpus binding, and a deletion policy.

Change: pull `ART` out of the recipe subgraph; `RECIPE --produces--> ART`. This makes two cases drawable that are currently unrepresentable: one recipe over two corpora (two artifacts), and one artifact read by a *declared-compatible* later recipe version (`[doc: RUBRIC goal 6]`) — which is the whole point of tracking provenance.

---

## D. Upgradability blind spots

### 16. Embedding-model → stored-vector coupling appears nowhere. Highest-severity item in this review — must-fix

`EMB` sits in `CLIENTS`, `VEC` sits in `STORES`, and no edge connects them. But every stored vector is a function of (model, dim, normalization/pooling, instruction prefix, tokenizer). Change the embedder and the corpus is silently invalidated; ANN structures are dim-locked; a query embedded by model B against vectors from model A returns *plausible, ranked, wrong* results — no exception, no error, just degraded retrieval.

The evidence makes this concrete rather than theoretical:
- Upstream's answer is **physical separation**: `_generate_collection_suffix()` → `f"{model_name}_{dim}d"` `[code-verified, F1]`. Vectors from different models never share a collection. Good — and it means an embedder upgrade is a *full re-embed into a new collection*, never a migration. That cost belongs on the anatomy.
- The suffix returns `None` when `model_name` is absent, while only `embedding_dim` is required `[code-verified, F1]`. So a custom `EmbeddingFunc` without `model_name` gets **no suffix**, and two different models at the same dimension collide in one collection. That is a live silent-corruption path in the code this project intends to invert, and exactly the case a homemade/local embedder hits.
- Under chunker strategy `V`, the embedder also determines chunk boundaries `[code-verified, F3]` — so the blast radius is KV, not just vectors.

Change, three edits:
- Edge `EMB -.binds.-> VEC` labelled "every vector is (model, dim, norm, prefix); changing it invalidates the namespace".
- State the asymmetry as a rule on the diagram: **index-time clients bind artifacts; query-time clients do not.** Rerank and generator upgrades are free; extractor and embedder upgrades cost a rebuild. This one sentence tells a reader which upgrades are cheap, which is the practical payoff of the whole versioning apparatus.
- Make `model_name` (or an explicit embedder identity) **mandatory** in the fitting contract, not optional — the machine refuses to write vectors it cannot attribute. This is the cheapest possible fix for a defect that is otherwise undetectable after the fact.

### 17. Nothing owns artifact staleness or artifact garbage collection — must-fix (staleness) / should-fix (GC)

Two consequences of #16 that need a home:
- **Staleness view.** Derive from `AREG × currently-pinned component versions`: "namespaces built by embedder@X are unreadable by wirings pinned to embedder@Y". Without it, an embedder upgrade degrades retrieval silently *and* poisons the rig — a regression gets attributed to the mutated component under test rather than to the invalidated artifact, which corrupts the improvement loop rather than merely slowing it `[inference]`.
- **Retention/GC.** "A version is immutable once referenced" `[doc: RUBRIC goal 7]` is free for code and expensive for multi-GB vector namespaces. A/B-ing two embedders means two full copies; doing it three times means six. Add a retention rule: artifact versions are reference-counted by pinned wirings and evictable when unreferenced *and* not cited by a scoreboard entry someone still wants reproducible. Note the honest tension — full reproducibility of an old run and bounded disk are incompatible; §0 should say which one wins.

### 18. No upstream-lineage axis on ported components — should-fix (cheap, high payoff)

The stated question "what hurts when LightRAG ships a new version" has no answer in §0 because nothing records which components are *ports of upstream code*. Rubric goal 7 tracks lineage as parent-version + change `[doc]`, which covers our own edits but not upstream drift.

Change: add `upstream_ref` (repo + tag/commit + file/symbol) to component registry entries, drawn as a field on `REG`. Then LightRAG 1.6 becomes a diff-able list of affected components — "these 4 of 23 components have upstream deltas" — instead of a re-port decision made blind. This also gives the outstanding "`upstream-venv` is not verified-clean upstream (api_version 0313 vs the fork's 0312)" caveat `[doc: PROJECT Context]` somewhere to be pinned rather than remembered.

Related: F2 shows upstream deliberately maintains **two coexisting chunker contracts** for backward compatibility `[code-verified]`. That is the shape of upstream's own versioning discipline, and a useful precedent to name — contract version vs behavior version `[doc: RUBRIC goal 7]` is not an invention here, it is already how the inherited code behaves.

### 19. The selector's policy is not a versioned artifact — should-fix

`SEL["Selector: choose harness + modality per query"]` is a box that decides, with no drawn policy and no version. Routing policy is plausibly the *cheapest* thing a self-improving system can improve (no re-index, no new components, pure query-side `[inference]`), yet as drawn it is the one decision point outside the versioning system.

Change: `SELPOL["Selector policy@version"] -.pins.-> SEL`, and route it through the same branch → A/B → promote loop as any other component. Also worth deciding here, not per-candidate: is selection per-query (routing), or per-session (configuration)? Candidates A–D silently assume different answers.

### 20. No failure, degradation, or partial-result path — nice (but it compounds)

Every arrow in §0 is a success arrow. Real behavior includes: a part errors mid-harness-loop; a budget halts execution with partial evidence; a required capability is missing (#5); a store is mid-migration (#6); an LLM client lacks logprobs and takes the prompt-mediated degradation path `[doc: SYNTHESIS §3]`. The last one is interesting because it is a *declared* degradation — the manifest says "I prefer logprobs, I can degrade" — which is a contract feature, not an error path.

Change: one annotation on the execution boundary — "partial results are first-class: budget-halted and degraded runs are traced and scored, not discarded" — plus a note that manifests may declare degradation paths as well as requirements. Cheap now; it prevents the rig from silently dropping the exact runs that are most informative.

---

## Minimum edit set

The smallest set of edits that closes every must-fix (items 1, 2, 3, 4, 5, 8, 9, 10, 16, 17-staleness):

1. Add an **ingest lane** with a source-polymorphic seam, per-document chunker, and per-chunk provenance (#1, #2).
2. Add four service boxes: **artifact registry**, **wiring validator**, **eval set + scorer + scoreboard**, **reindex planner** (#3, #4, #5, #6).
3. Rewire three edges: harness as **optional wrapper with back-edge and stacking** (#8); rig **connected** to fan-out/trace/eval/scoreboard (#9); budget as an **enclosure** over the whole execution (#10).
4. Add the edge `EMB -.binds.-> VEC` plus the rule "**index-time clients bind artifacts, query-time clients do not**", and make embedder identity mandatory in the contract (#16, #17).

Items 13 (validity sub-capability + `as_of` on the query contract) and 18 (`upstream_ref`) are should-fix but nearly free, and both get more expensive after the candidates harden.

## Effect on the four candidates

Not a redraw of §1–4, only what these findings change about scoring them:

- **A (Stage Bus)** — its headline advantage is stage-level comparison, but the inherited eval code is endpoint-shaped and answer-only `[code-verified, F4]`. The stage-diff rig is net-new work for A specifically; its "cheapest port" claim should be re-priced against that.
- **B (Conductor)** — item 5's wiring validator is the box that keeps opaque nodes honest; without it, B's stated failure mode ("opaque nodes tempt teams to stuff whole modalities into one node") has no mechanical brake, only discipline.
- **C (Federation)** — item 16 is C's hidden tax: every engine embeds independently, so N engines mean N vector copies with N embedder identities, and #17's GC problem arrives on day one rather than at the first upgrade.
- **D (Kernel+Sandbox)** — the shared corpus feed crosses the regime boundary, so item 2's finding (chunks are *not* paradigm-neutral under an embedder-coupled chunker) lands hardest here: D's "same corpus feed" edge is doing more work than it can currently support.

---
*Review of CANDIDATES.md §0 only, 2026-08-10. Uncommitted. New code evidence F1–F7 read from `Databasise/upstream-venv/.../lightrag/` this session; F4/F5/F6 findings are new to the planning set and may be worth folding back into PROJECT.md Context.*
