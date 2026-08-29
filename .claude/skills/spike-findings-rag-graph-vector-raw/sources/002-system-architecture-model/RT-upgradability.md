# Red Team — Lens: UPGRADABILITY

**Question under attack:** not "does this architecture work?" but "does it still work in 2028, after the things it depends on have moved without asking permission?"

Targets: Candidate A (Stage Bus), B (Conductor), C (Federation), D (Kernel+Sandbox), and the **Shared Anatomy** itself — which turns out to be the more productive target.

**Evidence key:** `[code-verified]` = read in source this session; `[docs-verified]` = read in a docstring/spec; `[paper-claim]` = asserted by a paper, untested; `[inference]` = my reasoning from verified facts. No benchmark number is used to move a ranking.

**Severity scale (used consistently below):**

| | Meaning |
|---|---|
| **Critical** | The architecture must be re-cut, or every corpus must be re-indexed from scratch, or a project goal becomes unreachable |
| **High** | Multi-week migration touching most parts; evidence integrity or attribution is lost during it |
| **Medium** | Bounded and mechanical, but it recurs and it scales with modality count |
| **Low** | Absorbed by normal work; a named owner and one migration script cover it |

---

## §0 — What actually ages (and the finding that reframes everything)

Before the scenarios, the finding they all converge on.

The design versions **components**, **wirings**, and **index recipes** (ARCHITECTURE-RUBRIC goal 7). Walk the Shared Anatomy diagram and list what it does *not* version:

| Unversioned layer | Where it lives in the diagram | Can it change an output? |
|---|---|---|
| **API clients — embed / rerank / LLM roles** | `CLIENTS` box, machine services, addressed by *role* | Yes. Determines the value of every stored vector and the content of every stored graph |
| **Prompts** | inside `llm-extractor@2.0` | Yes. A prompt edit with no version rev silently forks the corpus |
| **Store schemas** | `STORES` box, machine infrastructure | Yes, and it is the thing upstream changes |
| **The executor** | Candidate B/D's graph engine | Yes. It runs everything and appears in no trace |
| **The slot vocabulary** | Candidate A's fixed slots | Yes, by constraining what is expressible at all |

**Every one of the five attack scenarios below finds its worst failure inside one of those five rows.** The versioned layer holds up well under attack. The unversioned layer is where the damage is.

The rubric's own goal 9 says traces are "tagged with the component versions involved" — component-scoped, and that is exactly the gap. Proposed rubric amendment, stated once here and referenced throughout:

> **AMENDMENT R7-a (applies to all four candidates):** anything whose change can alter an output is a versioned artifact and appears in the trace. Acceptance test: *if I change X and nothing in the trace changes, X is a bug.*

Concretely, for the embedder — the sharpest case [code-verified]:

- LightRAG's stored vector records carry `__id__`, `__created_at__`, and declared `meta_fields`. **Nothing else.** No embedder identity, no dimension, no recipe stamp. [code-verified: `lightrag/kg/nano_vector_db_impl.py:300-302`]
- The only compatibility guard anywhere in the vector path is dimension equality, an `assert` inside the vendored `nano_vectordb` on load: `"Embedding dim mismatch, expected: {}, but loaded: {}"`. [code-verified: `nano_vectordb/dbs.py:72-74`]
- Meanwhile LightRAG *does* partition its LLM response cache by model identity — `llm_cache_identity`, documented as "Non-secret model/provider identity used to partition cache entries across role model, binding, or host changes." [code-verified: `lightrag/utils.py:3484,3512-3513`]

Upstream learned this lesson for LLM caches and did not apply it to embeddings. A same-dimension embedder swap is accepted silently and is wrong forever. Inheriting LightRAG's storage contracts as the machine's contracts (SYNTHESIS §6.2 calls `base.py` "essentially a ready-made fitting contract") inherits this hole by default.

---

## §1 — Scenario 1: upstream LightRAG ships v2 with a changed storage schema

**Ground truth about what you are tracking** [code-verified]:

- `lightrag/base.py` is 1,068 lines and defines **43 `@abstractmethod` declarations** across five storage base classes: `StorageNameSpace` 2, `BaseVectorStorage` 8, `BaseKVStorage` 6, `BaseGraphStorage` 18, `DocStatusStorage` 9.
- The Databasise fork's contribution is one plugin file implementing `BaseGraphStorage` — i.e. **20 abstract methods** (18 + 2 inherited) that must track upstream's every rev. [code-verified via base.py; plugin identity per PROJECT.md spike 001]
- Drift already exists: fork `api_version` 0312 vs vendored copy 0313. [PROJECT.md, spike 001]
- **Upstream's own migration mechanism is version-free heuristic sniffing.** `lightrag/storage_migrations.py` (329 lines) is a mixin run once at startup that decides a migration is needed by checking *emptiness*: graph has labels AND `full_entities`/`full_relations` KV stores are empty ⇒ backfill. [code-verified: `storage_migrations.py:1-60`] There is no schema version field anywhere in the storage layer.

That last point is the load-bearing one. Upstream's model — "sniff the data, guess the version, backfill once, in place" — is adequate for a single-tenant deployment upgrading itself. It is **unusable** as a foundation for a machine holding N artifact sets from M recipe versions, because it cannot answer "what version is *this* artifact?", only "has *this one* backfill run?". Any candidate that inherits `base.py` inherits a storage layer with no version identity. [inference from code-verified facts]

### Per candidate

**A — Stage Bus. Severity: High (with one Critical tail).**
A has already ported; upstream v2 is not an upgrade you take, it is a paper you re-read. Improvements arrive as a source diff you hand-port. The blast radius concentrates on the index side, which spike 001 measured as ~1,786 entangled lines welded to LightRAG's entity/relation ontology, and A shares **one** extraction component across all parts — so an upstream extraction change hits the single component every stored artifact depends on.
*Critical tail:* A's slot vocabulary was transcribed from LightRAG's internal 4-stage refactor — the stage names in the archive docstring are literally upstream's private function names (`_perform_kg_search` → `_apply_token_truncation` → `_merge_all_chunks` → `_build_context_str`) [code-verified per PROJECT.md spike 001]. If v2 re-cuts that pipeline (6 stages, or an inline retrieve→grade loop), A's *contract* is wrong, not just its components, and every wiring is re-cut. A has bet its boundary vocabulary on one vendor's 2026 internals.
*Cheapest fix:* version the slot vocabulary and support two vocabularies concurrently (see §7 amendment A-1). Also: derive slot names from the paradigm-neutral vocabulary the rubric already mandates (goal 2: "seeds/evidence, not entities/relations") rather than from upstream function names — a documentation-level fix done now, a rewrite later.

**B — Conductor. Severity: Medium.**
B owns its stores, so v2's schema is a temptation, not a break. The exposure is subtler: if the machine's store contract is a copy of `base.py`, it silently absorbs LightRAG-shaped concepts that every store implementation must then implement forever — `full_entities`, `full_relations`, `entity_chunks`, `relation_chunks` are all LightRAG-specific KV namespaces visible in the migration mixin [code-verified], and a HippoRAG-style phrase-graph part needs none of them.
*Cheapest fix:* take `base.py` as a *starting point to subtract from*, not a contract to adopt. Explicitly enumerate which of the 43 abstract methods are paradigm-neutral machine primitives and which are LightRAG artifacts; the latter become part-level concerns. This is a half-day of reading with a large permanent payoff, and it is the single most concrete near-term action this report recommends.

**C — Federation. Severity: Medium for breakage, High for evidence integrity.**
`pip install -U` genuinely works — this is C's best scenario. But C has no component versions inside a part, so the only version identity is the opaque string "LightRAG 1.5.4" vs "LightRAG 2.0". When quality moves after the upgrade, C cannot attribute the move to a stage, a prompt, or a schema change. The project's stated Core Value is local measurement replacing untrusted benchmarks (GOALS §4); C upgrades in a way that **destroys the comparability of its own historical results** and offers no instrument to recover it. Also, a v2 schema change means a full re-index of that engine's corpus — a cost C pays per engine, per release, forever.
*Cheapest fix:* the broker records the engine's full resolved dependency set as the part's version identity, and the rig hard-partitions results across it — old numbers are archived, never silently compared. Preserves honesty; does not restore attribution, which C cannot have.

**D — Kernel + Sandbox. Severity: Low. D's strongest scenario.**
The correct move falls out of the structure: LightRAG lives in the sandbox tracking upstream, while the ported kernel version is frozen. Same corpus feed, answer-level comparison ⇒ **D is the only candidate that can measure whether upstream v2 is worth adopting**, rather than guessing from a changelog. That is a genuine, non-obvious upgradability asset and it should be stated as a design goal, not left as an emergent property.
*The failure D must be attacked on:* the promotion path in CANDIDATES.md is one-way — "prove in sandbox, port to kernel." There is **no re-promotion path**. Once LightRAG is ported, upstream v2's genuinely better extraction prompt is a thing you can now *observe* is better and have no ritual to absorb. The sandbox copy and the kernel copy drift and nobody owns reconciliation.
*Cheapest fix:* make promotion idempotent. A standing "upstream delta" comparison in the rig (sandbox@latest vs kernel@ours, same feed, run on every upstream release) plus a named owner for the re-port decision. The mechanism already exists; only the *repetition* is missing.

---

## §2 — Scenario 2: the embedding model is upgraded; all stored vectors are invalid

### Does artifact provenance actually capture the embedder version? No.

Read the Shared Anatomy recipe diagram literally:

```
chunker@1.2 → llm-extractor@2.0 → artifact(graph + vectors + KV, provenance: ER1@v2)
```

**The embedder is not a node in the recipe.** It sits in the `CLIENTS` box as a machine service addressed by role. Role-addressability (SYNTHESIS §3) makes this worse rather than better: "the embed role" can be re-pointed at a different model by configuration, invisibly to every recipe version, with no artifact changing its stamp. Combined with the §0 code-verified facts — no embedder identity in stored records, dimension-equality as the only guard — the failure narrative is exact:

> Ops swaps the embed role from a 1536-dim model to a different 1536-dim model. No assert fires. No stamp changes. New chunks embed under the new model into the same namespace as old chunks embedded under the old one. Cosine distance across that boundary is meaningless. Retrieval degrades by an amount nobody can measure because the eval set drifts with it. Six weeks later someone blames a component version. There is no trace field that could exonerate it. [inference, from code-verified facts in §0]

A dimension change, by contrast, is the *good* case: it crashes loudly at startup. The dangerous upgrade is the one that fits.

**AMENDMENT SA-1 (Shared Anatomy — highest value in this report, applies to all four candidates):** the index recipe's version identity is a **content hash of its resolved inputs**, including `(embed_model_id, dim, normalization, pooling)` and `(extract_role_model_id, prompt_hash)`. Artifacts store the hash. "I can read ER1@v2" is checked against the hash, not against a hand-typed label. Keep `name@version` as the human-readable lineage label; run compatibility on the hash. Cost: one field and one function. Hand-assigned versions require a human to remember to bump; hashes cannot be forgotten. (Rung 3 — this is what every build system already does; do not invent a version algebra.)

**AMENDMENT SA-2 (Shared Anatomy — cheapest large saving):** split the index recipe into independently-stamped sub-recipes. Today one recipe emits "graph + vectors + KV" under **one** provenance stamp — so an embedder change invalidates the graph, which is logically false but is what the stamp asserts. Coarse provenance forces over-invalidation. Instead: KV carries the chunker stamp, graph carries the extraction stamp, each vector namespace carries the embedding stamp. This is the difference between re-running the entire LLM extraction pass and re-running embeddings only — and spike 001 established that extraction is the expensive, entangled side (~1,786 lines, and all the tokens).

### Per candidate — recovery cost

**A — Stage Bus. Severity: Low–Medium. A wins this scenario.**
All parts share one recipe and one extraction component; all vectors sit in machine-store namespaces. With SA-2, recovery is "re-embed N namespaces, keep the graph, keep the extraction output" — the cheap half. One re-embed fixes every part at once, because maximal artifact sharing means maximal migration sharing. **Artifact sharing and migration cost are the same axis**, a point CANDIDATES.md scores only on the sharing side.

**B — Conductor. Severity: Medium.**
Same machine stores, so the same recovery — but nodes are opaque, so a node may call the embed role internally. Its behavior version does not change; its output does. B needs SA-1 *more* than A does, precisely because opacity hides where the embedder is used.
*B's compensating asset:* graph specs are data, so "re-embed" is expressible as a graph you run, and an old-vectors wiring can be A/B'd against a new-vectors wiring on a corpus slice **before** paying for the full re-embed. B is the only candidate that can pilot this upgrade rather than commit to it. Worth stating explicitly as a B advantage.

**C — Federation. Severity: High.**
Every engine owns its vectors inside its own storage; re-embedding means re-indexing all N engines at N× token cost. For self-contained-storage parts (ColBERT/PLAID blob directories, codebase-memory-mcp) you may not be able to determine which embedder produced what, or change it. Worse, "upgrade the embedding model" is not one event in C — each engine pins its own embedder on its own upstream schedule, so at any moment the fleet is mixed and cross-engine comparison is quietly invalid.
*Cheapest fix:* embedder identity becomes a **required** manifest field, and the broker **refuses** to emit a cross-engine comparison when identities differ. Degrade to an explicit refusal rather than publishing a wrong number. This does not make C cheap; it makes C honest.

**D — Kernel + Sandbox. Severity: Low.**
Kernel gets A/B's cheap recovery; sandbox gets C's expensive one — which is *fine*, because sandbox parts are disposable: you do not re-index them, you retire them. This crystallises what D is actually for:

> **D's real value is not "two regimes." It is that migration debt is confined to the regime that is allowed to be thrown away.**

That is a stronger argument for D than the "try fast vs evolve deep" framing in CANDIDATES.md, and it is an upgradability argument, not a velocity one.

---

## §3 — Scenario 3: a contract change in the assembler, which 6 wirings pin at v2.2

### The version-skew attack lands on the identity scheme, not on the contract change

Rubric goal 7 states two version axes — **contract** version (breaking boundary changes) and **behavior** version (internals, free to rev under a stable contract) — but gives identity as a *single* string, `name@version`, immutable once referenced.

A single string cannot express the pin you actually want: *"any behavior version under contract v2."* So:

> `assembler@2.3` ships a bugfix. Six wirings pin `assembler@2.2` literally. Each wiring must be edited. Each wiring is itself immutable-once-referenced, so each edit mints a new wiring version. Each of those is referenced by traces, eval results, and possibly a harness spec — so the harnesses rev too. Every historical trace now names a wiring that is no longer current. **One bugfix produced six wiring revs and a discontinuity in every comparison series.** [inference from ARCHITECTURE-RUBRIC goal 7 as written]

Scale it: 15 modalities over a shared core of ~7 components (SYNTHESIS §4) means one core-component rev touches roughly 15 wirings. Three core revs a month is ~45 mechanical wiring revs a month, each needing a rig run to confirm no regression. **That is the drowning, and it is caused by the identity scheme, not by combinatorics being inherently hard.**

**AMENDMENT R7-b (applies to all four candidates):** wirings pin a **contract-version range**; a **resolved lock** records the exact behavior version per run. Two artifacts, not one — the spec says `assembler@^2`, the lock captured at run time says `assembler@2.2`. The wiring is stable across behavior revs; the trace stays exact because the lock is per-run. This is npm/cargo/Nix; adopt it rather than deriving a version algebra. It converts `O(wirings × revs)` hand-edits into `O(1)` lock refresh.

### Per candidate — the genuine *contract* break (v2 → v3)

**A — Stage Bus. Severity: Low. A wins this scenario outright and it is not close.**
The assembler occupies a **machine-owned slot** with a machine-owned plain-data contract. A contract change is therefore a *machine* change: rev the ASSEMBLE slot to v3 and have the machine present a v2 view to unported components via one adapter. **One adapter serves all six wirings, because the boundary has a name and an owner.** Fixed slots are always written up as A's weakness (four of six agentic control-flow shapes unexpressible). Under contract evolution they are A's decisive strength — a named, machine-owned boundary is the only place a compatibility shim can live exactly once.

**B — Conductor. Severity: High without amendment, Medium with.**
Contracts in B are per-edge between two specific nodes; there is no machine-owned named boundary, so there is nowhere for one adapter to live. You either insert an adapter node into six graph specs — six spec revs, and the graphs stay uglier permanently — or rev six downstream consumers.
*Cheapest fix:* B's escape is that specs are *data*. **AMENDMENT B-1: spec migrations are a first-class versioned artifact** — a named, replayable transform over graph specs that emits new spec versions with lineage pointing at the migration itself. Then a contract break is one migration authored once and mechanically applied, with the provenance to prove what changed. Without B-1, B's six hand-edits are exactly the combinatorial drown; with it, B is Medium and improving.

**C — Federation. Severity: Low — but score the reason, not the number.**
C is immune because there is no shared assembler; each engine carries its own. C has converted a migration event into permanent duplication. This is the immunity of a system with no reuse left to protect, and it must not be recorded as a win.

**D. Severity: Medium.** Kernel inherits B's story (and needs B-1); sandbox is untouched. D's containment works here too.

### The immutability trap (all candidates; worst for B and D)

"Immutable once referenced" plus 15 modalities plus two years yields a registry containing every version ever referenced by any trace, none of it deletable without breaking reconstructability. Most entries will not *run* — their transitive Python dependencies no longer install. The promise "the system as run yesterday is reconstructable" stays true on paper and false in practice, which is the worst combination because nobody notices.

**AMENDMENT R7-c:** three retention tiers — **runnable** (CI proves it still executes), **readable** (spec + lineage retained, execution not guaranteed), **tombstoned** (identity + hash retained so old traces resolve; artifact purged). And reconstructability is a *claim to be tested*: a scheduled job re-runs one randomly chosen archived wiring and reports whether it still executes. Cheap, and it is the only thing that keeps goal 7 honest past year one.

---

## §4 — Scenario 4: two years pass, 15 modalities accumulated. Which one is the legacy system?

Operational definition used here: **the legacy system is the one where adding modality N+1 costs more than modality 1 did, and where most components are ones nobody dares change.**

**A — ages *rigid*.**
Failure mode: **slot ossification**. The slot vocabulary is machine-owned and frozen from 2026's paradigm. When the field moves, new modalities either do not fit or get crammed into an escape-hatch slot that becomes the dumping ground. Two mitigating facts: A stays small (5 slots × k components — at 15 modalities it is still comprehensible), and **the decay is measurable** — count components in the escape hatch over time. Rigid systems are recoverable by one painful, scheduled vocabulary migration. Complicated systems are not. A is not the legacy system.

**B — ages *complicated*, with a named slide risk.**
CANDIDATES.md already concedes it: "opaque nodes tempt teams to stuff whole modalities into one node, quietly becoming Candidate C." The honest two-year projection: 15 modalities, ~60 nodes, ~200 versions, and 4–5 modalities that are **one-node graphs** because someone was in a hurry. At that point B has C's opacity *and* B's engine complexity — the worst cell in the matrix. This is a behavioural failure, which is why architecture reviews miss it.
*Cheapest fix — make it visible, do not try to ban it:* **AMENDMENT B-2: the registry computes a decomposition ratio per part (nodes / declared stages) and the rig displays it beside every result.** A one-node graph cannot be stage-compared, so the metric is self-evidencing: the part's own comparison output advertises its degradation. Free, since the rig already renders per-part results.
*Second B aging defect:* the executor is a permanent maintenance object that **has no version axis in this design and appears in no trace**. Two years in it has its own bug backlog, and "reconstruct the system as run yesterday" fails on the one component that ran everything. **AMENDMENT B-3: the executor is a versioned artifact named in every trace** (an instance of R7-a).

**C — is the legacy system, decisively, by year two.**
Fifteen engines, fifteen Python dependency trees, fifteen upstream maintenance schedules. Research code abandonment rates make "a third of hosted engines unmaintained in two years" a conservative estimate [inference; base rate, not measured here]. C's parts do not degrade gracefully — they stop installing. And C **cannot** repair them, because its defining choice was never to decompose them. Meanwhile C's indexing cost is N× and never amortises: the corpus is re-indexed once per engine, forever.
**C is the only candidate whose legacy is someone else's code that you are structurally forbidden from refactoring.** That is the worst kind to own.

**D — ages like B, or ages like C, and one governance mechanism decides which.**
CANDIDATES.md names the risk ("everything stays in the sandbox forever") and then relies on "discipline," which is not a design. Honest two-year projection under discretionary promotion: **3 kernel parts, 12 sandbox parts** — i.e. D has become C plus an execution engine nobody uses, which is *strictly worse than plain C*. This is D's live risk and the reason its ranking is conditional.
*Cheapest structural fixes, in order of laziness:*
1. **AMENDMENT D-1 (safety property): sandbox parts are excluded from the default selector.** Runnable by the rig and by explicit request; never routed to by production. A sandbox part then cannot *accidentally* become load-bearing, which is what makes "stays forever" harmful rather than merely untidy. One condition in the selector.
2. **AMENDMENT D-2 (pressure): sandbox parts carry a TTL** (~90 days), after which they are disabled unless promoted or explicitly renewed **with a recorded reason**. Renewal is cheap; the accumulating record is the whole mechanism.
3. *(Only if 1+2 prove insufficient)* a hard sandbox population cap forcing a retirement per admission.

Adopt D-1 and D-2. D-1 is the safety property; D-2 is the pressure. Skip 3 until measured.

**Ranking on ageing alone:** A (rigid, recoverable, measurable) > B (complicated, fixable with B-2/B-3) > D (bimodal on one mechanism; with D-1/D-2 it lands at B's level or better) >> C (unfixable third-party debt).

---

## §5 — Scenario 5: the index recipe format itself must change (a new provenance field)

This is the sharpest scenario because it is *meta*: the versioning mechanism needs versioning. And it is **not hypothetical** — amendment SA-1 above (embedder identity in the recipe hash) *is* this scenario. The report's own top recommendation triggers it.

### The finding that generalises

**Nobody in the design owns migration.** SYNTHESIS §4 lists ~7 primitive component types — retriever, grader/filter, rewriter, ranker, assembler, generator, external-tool. There is no migrator. The rubric's ten goals never mention migration. Yet three of the five scenarios in this report require one.

**AMENDMENT SA-3 (Shared Anatomy): add an eighth primitive — the *migration component*.** A versioned artifact that transforms stored artifacts from `recipe@vN` to `recipe@vN+1`, declares the pairs it bridges, carries lineage like any component, and is testable. It converts every scenario in this document from "a project" into "a component someone writes on a Tuesday."

**And its acceptance test is already built:** run the *same* wiring against pre- and post-migration artifacts; outputs must be byte-identical for a lossless migration, or differ only in ways the migration declares. **The comparison rig is the migration test harness** — the cheapest quality gate in the whole design, and currently unclaimed. `tests/parity/run_substrate_parity.py` is the working precedent (same corpus, isolated dir per backend, structural diff, JSON out) [PROJECT.md context].

### Per candidate — who runs the migration?

**A — Stage Bus. Severity: Low. A wins scenario 5 too, for the same reason it won scenario 3.**
Normalization is total: the machine owns every artifact and every stamp, so the migration is written once and run over machine stores. The real problem is **backfill** — existing artifacts do not have the new field, because it was never recorded. Options: infer from index-time logs/config, mark `unknown`, or re-index. Realistically `unknown`, and then the policy question is what `unknown` means for compatibility.
*Recommended policy (all candidates):* `unknown` provenance is **readable but never declared-compatible**. Old artifacts keep serving the part that built them; they are never shared into a part claiming recipe compatibility. This converts silent wrongness into an explicit refusal for the cost of one enum value.

**B — Conductor. Severity: Low–Medium.**
90% is A's story since B also owns machine stores. The tail is the **blob escape hatch**: opaque artifacts have provenance the machine can neither read nor rewrite, so a format migration strands them permanently — and provenance you cannot migrate is provenance you cannot trust.
*Cheapest fix:* **AMENDMENT B-4: every blob artifact carries a machine-owned sidecar manifest.** The machine never touches the blob; it owns a small JSON beside it holding the provenance stamp. Provenance stays uniformly machine-migratable even for artifacts the machine cannot parse — which is the entire point of having provenance. Trivially cheap, and it is the fix that keeps B's escape hatch from being a permanent hole in goal 6.

**C — Federation. Severity: High. This is where C's incompatibility with goals 6 and 7 is clearest.**
Nobody owns it. Provenance lives inside 15 engines that have never heard of your recipe format. The broker can stamp only what it fed in (the corpus feed) and what came back out. **You cannot add a provenance field to artifacts you do not own.** So C's answer is: the field exists at the feed boundary only, and artifact-level provenance is permanently unavailable. That is not a migration cost — it is a capability C structurally cannot have, and goals 6 (artifact-shareable, provenance checkable) and 7 (recipes version too) are therefore unreachable in C by construction.

**D. Severity: Low–Medium.** Kernel migrates like B (and needs B-4); sandbox is like C, which is tolerable precisely because sandbox artifacts are disposable and compared at answer level only. Containment holds a third time.

---

## §6 — Scenario × candidate severity matrix

| Scenario | A Stage Bus | B Conductor | C Federation | D Kernel+Sandbox |
|---|---|---|---|---|
| 1. Upstream v2 schema change | **High** (+Critical tail: slot vocabulary is transcribed from upstream internals) | Medium (inherits LightRAG-shaped store concepts) | Medium breakage / **High** evidence-integrity loss | **Low** — only candidate that can *measure* whether to adopt |
| 2. Embedder upgraded | **Low–Med** — one re-embed fixes all parts | Medium — opacity hides embedder use; can pilot on a slice | **High** — N× re-index, mixed fleet, some engines unfixable | **Low** — expensive case confined to the disposable regime |
| 3. Assembler contract change, 6 wirings | **Low** — one adapter at a machine-owned slot | **High** without B-1, Medium with | Low, but only because no reuse remains to protect | Medium (kernel = B; sandbox untouched) |
| 4. Two years, 15 modalities | Ages **rigid** — recoverable, and measurable | Ages **complicated** — one-node-graph slide; unversioned executor | **Legacy.** Third-party debt you may not refactor | **Bimodal** — B-grade with D-1/D-2, worse-than-C without |
| 5. Recipe format change | **Low** — one machine-owned migration | Low–Med (blob tail; needs B-4) | **High** — capability never existed | Low–Med |

---

## §7 — Ranking for UPGRADABILITY, and the amendments that change it

**As the candidates are written today:**

**1. D — Kernel + Sandbox.** Wins because migration debt is confined to the regime allowed to be thrown away, and because it is the only candidate that can *measure* whether an upstream upgrade is worth taking rather than inferring it from a changelog. **Conditional** on sandbox containment — without D-1/D-2 it degenerates below C.

**2. A — Stage Bus.** The surprise of this pass. A wins scenarios 3 and 5 outright and does well on 2, all for one reason: **a machine-owned named boundary is the only place a compatibility shim or a migration can live exactly once.** Its ageing failure is rigidity, which is recoverable and measurable. A is disqualified on *other* lenses (four of six agentic shapes unexpressible; black-box parts and CAG do not fit slots) — not on this one. Any final choice should consciously import A's boundary-ownership property.

**3. B — Conductor.** Strong on 1 and 2, weak on 3 (no single boundary for a shim) and 4 (opaque-node slide, unversioned executor). B is the candidate whose ranking moves *most* under amendment.

**4. C — Federation.** Last, clearly. Loses 2, 4, and 5 badly; its apparent win on 1 buys an upgrade whose effects cannot be attributed. **No amendment fixes C for upgradability**, because its defining choice — do not decompose — is precisely the property upgradability requires. C is a *regime*, not an architecture, and D already models it correctly as one.

### Amendments that change the ranking

- **B overtakes both D and A** if all three of: **B-1** (spec migrations are first-class versioned artifacts), **B-3** (executor versioned and named in traces), **B-2** (decomposition ratio published per part). These convert B's two losses into wins while keeping its wins on 1 and 2. This is the single highest-leverage amendment set in the report.
- **A overtakes D** if the **slot vocabulary is itself versioned** with two vocabularies supported concurrently (**A-1**). That turns A's one fatal ageing mode — ossification — from a rewrite into a scheduled migration, on top of an architecture that already wins the migration mechanics.
- **D falls below C** if **D-1** (sandbox excluded from the default selector) and **D-2** (sandbox TTL with recorded renewals) are *not* adopted. 3 kernel + 12 sandbox parts plus an unused execution engine is strictly worse than plain C: B's cost, C's opacity.
- **C never rises** — but it becomes entirely acceptable *as D's sandbox*, which is exactly what D proposes.
- **All four improve materially** under the shared-anatomy amendments **SA-1** (resolved client identity in the recipe hash), **SA-2** (per-artifact-class provenance, splitting extraction from embedding), **SA-3** (migration component as the eighth primitive), plus **R7-a/b/c**. These are not discriminators — adopt them regardless of which candidate wins.

### Amendment index

| ID | Applies to | Amendment |
|---|---|---|
| **SA-1** | all | Recipe version identity = content hash of resolved inputs, incl. `(embed_model_id, dim, norm, pooling)` and `(extract_model_id, prompt_hash)` |
| **SA-2** | all | Per-artifact-class provenance: KV←chunker, graph←extraction recipe, vector namespace←embedding recipe |
| **SA-3** | all | Eighth primitive component type: the **migration component**; its acceptance test is a rig run over pre/post artifacts |
| **R7-a** | all | Anything that can alter an output is versioned and appears in the trace (clients, prompts, store schemas, executor, slot vocabulary) |
| **R7-b** | all | Wirings pin a contract-version *range*; a per-run **lock** records the resolved behavior version |
| **R7-c** | all (worst B/D) | Retention tiers runnable / readable / tombstoned + a scheduled reconstructability test |
| **A-1** | A | Version the slot vocabulary; support two concurrently; name slots from paradigm-neutral vocabulary, not upstream function names |
| **B-1** | B, D-kernel | Graph-spec migrations are first-class versioned, replayable artifacts with lineage |
| **B-2** | B, D-kernel | Registry publishes a decomposition ratio per part; the rig displays it |
| **B-3** | B, D-kernel | The executor is a versioned artifact named in every trace |
| **B-4** | B, D-kernel | Blob artifacts carry a machine-owned sidecar provenance manifest |
| **D-1** | D | Sandbox parts excluded from the default selector (safety property) |
| **D-2** | D | Sandbox parts carry a TTL; renewal requires a recorded reason (pressure) |
| **C-1** | C, D-sandbox | Embedder identity is a required manifest field; the broker refuses cross-engine comparison on mismatch |

---

## §8 — What would falsify this ranking

- **If the machine hard-forks upstream on day one and never tracks it**, scenario 1 evaporates and the A↔B gap narrows sharply. Worth deciding explicitly rather than by drift — it is the cheapest decision in the project and it changes two rankings.
- **If the embedding model is pinned for the project's life** (local model, no upgrades), scenario 2 loses most of its weight and C's position improves.
- **If modality count stays under ~5**, scenario 4 never fires and C is genuinely fine. C's failure is a function of N, not of C.
- **If graph-spec migration turns out not to be mechanisable**, amendment B-1 is unavailable and B stays permanently below A on upgradability.
- **If sandbox containment (D-1/D-2) is rejected on usability grounds**, D drops below C and the recommendation should switch to B-with-amendments.

## §9 — Three small spikes that would settle the open questions

1. **U1 — silent-corruption magnitude.** Take existing LightRAG 1.5.4 artifacts, re-point the embed role at a *different model of the same dimension*, and run the existing parity harness. Measures how bad the §2 failure actually is, and whether it is detectable without ground truth. Cheap: the harness exists.
2. **U2 — recipe hash.** Implement SA-1's hash over `(chunker, extractor + prompt hash, embed model id + dim)`, stamp existing artifacts, and confirm the compatibility check refuses the mismatched pair produced in U1. ~1 day. Validates the report's top recommendation end to end.
3. **U3 — mechanical spec migration.** Apply one contract change across six toy graph specs via a scripted transform; check that lineage comes out clean and replayable. Directly confirms or falsifies amendment B-1, which is the amendment that moves the ranking most.

---
*Red team pass, lens: upgradability. Drafted 2026-08-10 against CANDIDATES.md, SYNTHESIS.md, ARCHITECTURE-RUBRIC.md, GOALS.md, PROJECT.md. Code claims verified against the vendored LightRAG 1.5.4 in `Databasise/upstream-venv/Lib/site-packages/lightrag/`. Not committed.*
