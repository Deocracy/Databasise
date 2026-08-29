# Red Team — Self-Improvement Operability

**Lens:** does the improve-loop actually work in practice? Attacks the four candidates (CANDIDATES.md) and versioning-as-improvement (ARCHITECTURE-RUBRIC.md goal 7) on operability, not elegance.

**Evidence tags:** `[code-verified]` (spike 001 / SYNTHESIS source reads, cited second-hand), `[docs-verified]` (what the five planning docs do or do not say — I read all five), `[paper-claim]`, `[inference]` (my modelling; assumptions shown).

**Headline:** the versioning model is sound as *bookkeeping* and unproven as an *improvement mechanism*. Three of the five attacks land on things no document specifies; one (evaluation validity) is a quantitative disqualifier for the loop as currently sketched. The architecture choice barely moves the needle on the biggest risk — the eval set does.

---

## 1. Combinatorial explosion — what actually explodes

### 1.1 The count nobody has written down

7 primitive component types [SYNTHESIS §4, docs-verified] × N modalities, branch-per-mutation. The naive fear is "too many components". That is not the explosion.

| Object | Growth per mutation | Year-1 size @10 experiments/day | Cost per unit |
|---|---|---|---|
| Component version | +1 | ~3,650 | KB (a diff) |
| **Wiring version** | **+1 (forced — wirings pin versions)** | ~3,650 | ~2 KB JSON |
| Trace records | +~400 node-runs | ~29 GB/yr @20 KB each | disk |
| **Index artifacts** | **+1 full artifact set per *recipe* mutation** | **1–4 GB and 10–50 M tokens each** | the real bill |

[inference; rates assumed, unit sizes from a 10k-chunk corpus estimate]

Registry entries are free. **Artifacts and traces are not, and no document specifies retention, eviction, or GC for either** [docs-verified — "immutable once referenced" appears in goal 7; nothing states when a version stops being referenced or what happens then].

### 1.2 The three multipliers the design has hidden

**(a) Wiring versions are derived, not authored.** Goal 7 makes a wiring a pinned tuple of `name@version`. Any component mutation therefore mints a wiring version too. The addressable wiring space for a 5-node wiring with k versions per node is k⁵; at k=5 that is 3,125 wirings from 25 components. Only tried ones get instantiated, but the *search* space is what the mutation proposer sees, and it is exponential in slots, not linear [inference].

**(b) Shared-component promotion fans out.** CANDIDATES §0 shows `seed-selector@1.0`, `assembler@2.2`, `generator@1.0` shared by the LightRAG and PathRAG wirings [code-verified: PathRAG reuses LightRAG's index verbatim; component sharing is the diagram's own claim]. Promoting `assembler@2.3` means either (i) re-validating every wiring that pins it — 5 wirings = 5× experiment cost — or (ii) accepting **version skew**, where wiring₁ runs @2.2 and wiring₂ runs @2.3. Skew is the path of least resistance and it makes the registry's effective state 2ⁿ in shared-component bumps. **No document specifies an adoption policy for shared-component promotions** [docs-verified]. This is the single most likely source of "why is this modality suddenly worse" six months in.

**(c) Config-vs-component ambiguity.** Is `top_k=40 → 60` a new component version or a wiring-node attribute? The docs never say [docs-verified]. If config is baked into the component, every knob turn mints a near-duplicate component and the registry fills with `ranker@1.0…ranker@1.47` that differ by an integer. **Recommendation: config belongs to the wiring node, not the component version.** One object per config mutation instead of two, and config mutation becomes a ~200-byte diff rather than a code artifact. Cheapest fix in this document.

### 1.3 Navigability crossover

A human can scan ~100 items. At 10 experiments/day the lineage tree is unreadable inside two months; at 1/day, inside a year [inference]. The fix is not a better UI, it is **loser tombstones**: when a mutation loses, delete its code and artifacts, keep ~200 bytes (mutation id, parent, effect size, decision, evidence pointer). Tombstoning moves "unreadable" from ~6 weeks to effectively never, and — more valuable — it stops a stateless LLM proposer from re-proposing the same losing mutation every epoch, which it will otherwise do indefinitely.

### 1.4 Missing policies (none of these appear in any document) [docs-verified]

1. Reference-counted retention with tiers: pinned (current defaults) / reachable (in a live wiring) / orphan (GC-eligible).
2. Artifact GC keyed on **recipe-version reachability** — index artifacts die when the last wiring that can read that `recipe@version` is unpinned.
3. Trace policy: keep aggregates forever, raw node IO for 30 days or for promoted/contested experiments only. Otherwise 29 GB/yr of text you will never read.
4. Frontier cap: max live branches per component type; a mutation proposer without a cap will fan out breadth-first forever.
5. Loser tombstones (§1.3).
6. Shared-component adoption policy (§1.2b) — pick "re-validate all dependents" or "explicit skew with an expiry".

### 1.5 Per candidate

- **A (Stage Bus):** 5 fixed slots bound the space; mutations are slot-local and the registry is the most navigable of the four. But topology and harness mutations are unreachable, so half the interesting search space does not exist. Safest and least capable.
- **B (Conductor):** the wiring spec is a *graph*, so the mutation space is topologically unbounded — the proposer can emit a 40-node monster. Needs a schema-level cap (max nodes, max loop bound, max fan-out) that no document mentions [docs-verified].
- **C (Federation):** no mutation; registry is ~20 installed engines, forever. Navigable because inert.
- **D (Kernel+Sandbox):** kernel inherits B's unboundedness, sandbox inherits C's flatness. **But D bounds the explosion structurally if the improvement loop is declared kernel-only and the kernel population is capped** (3–5 modalities). Registry growth then scales with kernel size, not with total modality count. CANDIDATES does not make this argument for D; it is D's strongest under-sold property.

---

## 2. Evaluation validity — the disqualifier

### 2.1 30–50 questions cannot see what the loop produces

Paired design (both arms on the same questions), binary correctness, exact McNemar. Power depends only on discordant pairs.

At **n=40** with 15% discordance (arms sharing an index differ on few questions), a true **+5 pp** improvement gives b+c≈6 discordant pairs with c−b≈2. Exact two-sided p for c=4, b=2 is **0.69**. To reach p<0.05 at b+c=6 the challenger must win **all six** discordant questions (p=0.031). Power for a genuine +5 pp effect: **≈0.10** [inference, standard exact McNemar; assumptions stated].

Absolute floor of detectability at n=40: the challenger must win ≥6 discordant questions and lose none → **+15 pp minimum, and only under unanimity.** Realistic MDE at 80% power: **+20–25 pp** [inference].

Sample size to detect **+5 pp** at 80% power, 15% discordance: **n ≈ 470** [inference, McNemar sample-size formula].

**Consequence:** published *architecture*-level deltas run 5–15 pp [paper-claim, and PROJECT.md itself says papers disagree 6× for the same system, so treat as unreliable]. Component-level mutations — a reranker swap, a prompt tweak, a threshold — move 1–5 pp [inference]. **Essentially no single component mutation is statistically detectable on a 30–50 question set.** The eval set is off by an order of magnitude for the loop's stated purpose.

### 2.2 How many mutations get promoted on noise

Naive rule "adopt if the challenger scores higher": under the null, P(challenger strictly higher) ≈ (1 − P(tie))/2 ≈ **0.40–0.45**.

At 10 mutations/day with a generous 10% genuinely-good rate [inference]:
- real wins detected ≈ 10 × 0.10 × 0.75 ≈ **0.75/day**
- noise promotions ≈ 10 × 0.90 × 0.42 ≈ **3.8/day**

**≈5 noise promotions per real one.** After ~50 promotions the eval set is thoroughly overfit; measured score climbs monotonically while held-out quality is flat or worse — textbook adaptive-overfitting on a reused holdout. The system will look like it is improving. It will be doing a random walk with a scoreboard.

### 2.3 The noise floor is the same size as the signal

LLM-judge self-disagreement on re-run is ~5–15% of items [inference; widely observed, not verified here]. At 10% self-disagreement, judge-only measurement error on n=40 is ≈ √(0.1×0.9/40) ≈ **±4.7 pp (1 SE)**. Generator nondeterminism adds more: **the same wiring scored twice does not score the same.** No document specifies a null A/A run [docs-verified]. Without one, every reported delta is uninterpretable.

### 2.4 The instrument is the only unversioned artifact

Goal 7 versions components, index recipes, wirings, and traces [docs-verified]. It does not version the **eval set**, the **judge**, the **judge prompt**, or the **corpus snapshot** — the four things that determine every promotion decision. A score is only comparable within a fixed (eval@v, judge@v, corpus@v) triple. This is a structural inconsistency in the mandate, not an oversight to fix later: *the measuring instrument must be versioned like everything else, or the lineage tree records decisions whose evidence cannot be reconstructed.*

### 2.5 What the machine needs (nothing here is currently specified)

1. **Versioned, hash-pinned eval set** with dev/holdout split, and a **sealed holdout** touched at most once per ~20 dev experiments, budgeted as a scarce resource.
2. **A/A null calibration** — champion vs itself, N repeats, to learn the null distribution of the score difference. Promote only above the A/A 95th percentile. Cheap (reuses the index) and the single best defence.
3. **Paired significance gate** — exact McNemar (binary) or paired bootstrap (continuous), with an explicit MDE stated in the UI so no one reads a +3 pp move as progress.
4. **Confirmation rule** — a winner must win twice on disjoint question subsets. Kills ~85% of noise winners at 2× cost [inference]. Cheapest robust defence after A/A.
5. **Multiplicity control** — α-spend budget per epoch, or Benjamini–Hochberg FDR over the epoch's experiments.
6. **Regression suite as hard gates, not score components** — citation validity, refuse-when-no-evidence, latency ceiling, token ceiling, output-schema conformance. Averaging these into one number is how you promote a mutation that gains 3 pp mean while catastrophically failing two questions.
7. **Per-question effect logging** so evidence pools across experiments — a 2 pp mutation may prove itself over five experiments even when no single one is significant.
8. **Corpus/eval drift pinning** — every score carries (corpus@v, eval@v, judge@v) or it is not comparable.

### 2.6 Two cheap levers that beat all of the above

- **Measure retrieval, not answers, for retrieval-side mutations.** Gold-passage recall@k / nDCG removes generator noise *and* judge noise entirely, costs no judge calls, and is the correct target for 5 of the 7 component types [inference]. Reserve end-to-end answer judging for generator and assembler mutations.
- **Continuous per-question scores instead of binary.** Paired t/bootstrap at n=40 detects d≈0.44 SD at 80% power; at score SD≈0.25 that is ~11 pp absolute — better than 15–25 pp, though still not enough alone.

### 2.7 Cost model

Adjudicated decision = n_questions × n_arms × tokens_per_query × n_repeats, plus judging.

At n=40, 2 arms, ~10 k tokens/query [inference — PROJECT.md forbids trusting the 6×-disagreeing published numbers, so treat as an order-of-magnitude band], 2 repeats for confirmation: **~1.6 M tokens + ~0.3 M judging ≈ 2 M tokens per accepted/rejected decision.** At 10/day: **~20 M tokens/day**, query-side only.

Index-side is a different regime: 10 k chunks × ~1.5 k extraction tokens ≈ **15 M tokens per recipe version** — i.e. **one index-recipe mutation ≈ 7 days of query-side experimentation.** No document distinguishes index-side from query-side mutation budgets [docs-verified], although SYNTHESIS §5's sharing rule ("near-zero extra cost for query-side components") implies the distinction. **Index-side mutations need a separate, far stricter rate limit and a sub-corpus screening stage.**

---

## 3. Mutation safety — budgets cover one failure class of six

| # | Failure | Covered by budget? | What actually covers it |
|---|---|---|---|
| 1 | Runaway loop (steps/tokens) | **Yes** | budget enforcer |
| 2 | Tight CPU loop making no machine calls | **No** | wall-clock watchdog + process isolation |
| 3 | Prompt / corpus exfiltration (generator leaks system prompt; external-tool ships evidence to a URL) | **No** | enforced capability manifest: deny-by-default network + FS |
| 4 | **Shared-artifact corruption** | **No** | per-(recipe@version, namespace) write scoping; CoW for experimental arms |
| 5 | **LLM-cache poisoning** | **No** | cache key must include component version + prompt hash |
| 6 | Concurrency skew (arms sharing rate-limited clients distort each other's latency) | **No** | interleave arms, or score tokens not seconds; production quota lane |

**(4) is the largest blast radius.** Goal 6 (artifact-shareable) plus SYNTHESIS §5 (PathRAG reads LightRAG's index verbatim [code-verified]) mean components read *shared* stores. **Immutability of component versions does not imply immutability of artifacts.** A mutated index-side component with write access corrupts the graph and vectors that every other modality depends on — including the champion it is being compared against.

**(5) is the cheapest to fix and the most insidious.** SYNTHESIS §2 makes content-hash LLM caches machine-owned and load-bearing for incremental rebuild [code-verified]. A mutated extractor writing bad entries under a colliding key poisons every future run silently and permanently.

**The manifest enforcement gap.** ARCHITECTURE-RUBRIC goal 3 says a component "declares what it implements and what machine primitives it requires" [docs-verified]. No document says the machine **enforces** the declaration. An unenforced manifest is documentation, not a boundary. Enforcement is what converts goal 3 from a design nicety into the safety mechanism the improve-loop needs.

### 3.1 Which candidate contains the blast radius

- **A — strongest containment by construction.** The narrow plain-data contract *is* the sandbox: a mutated ranker handed `List[ScoredNode]` literally cannot reach a store. Containment is structural, not policy. Smallest mutation space, so least to contain.
- **B — containment by policy, with a named hole.** Executor owns checkpoints, meters, budgets; node boundaries are contract-defined. The "blob escape hatch" and opaque nodes [CANDIDATES §B, docs-verified] can do anything, and mutated code runs in-process beside the champion. B must *add* an isolation domain it does not currently have.
- **C — excellent isolation (process/container level), zero introspection, nothing to contain** because nothing mutates.
- **D — the only candidate with a natural home for untrusted mutated code**, *if* the sandbox is respecified. CANDIDATES describes the sandbox as a hosting convenience for external engines [docs-verified], not as a security boundary. **Respecifying the sandbox as the isolation domain for untrusted mutations is the single change that most improves self-improvement safety across the whole design** — and it simultaneously gives the sandbox a permanent job, which answers attack 5.

**Is budget enforcement enough? No.** The required trio is **budget (what it may spend) + capability enforcement (what it may touch) + artifact write-scoping (what it may break)**, plus a wall-clock watchdog. Budget alone covers row 1 of six.

---

## 4. Who writes mutations — permit in decreasing order of static verifiability

The ordering principle: **permit a mutation class in proportion to how well the machine can verify it *before* running it.** That is the whole argument.

| Rank | Class | Static verifiability | Risk | Reward | Permit |
|---|---|---|---|---|---|
| 1 | **Config / parameter** (top_k, thresholds, chunk size, weights, temperature) | Full — typed domain + range check | Near-zero | High per unit risk | **First** |
| 2 | **Wiring / topology** over already-trusted component versions | Static — contract type-check, acyclicity or loop-budget, node cap | Moderate, machine-checkable | Highest practical | **Second** |
| 3 | **Prompt text** inside an existing component | Partial — output-schema validation, leak scan | Medium (unbounded string; injection, leak, schema break) | Medium-high | Third, gated |
| 4 | **LLM-generated component code** | **None** | Highest — all six failure classes plus supply chain plus silent-correctness rot | Highest ceiling, low near-term rate | **Last** |

**Why config first, beyond safety.** PROJECT.md's own observation — published benchmarks disagree 6× for the same system [docs-verified] — implies **configuration sensitivity dominates architectural difference**. If a system's measured quality moves 6× on setup, then top-k, chunk size and threshold tuning is where the recoverable gains actually are [inference]. Config mutation therefore has the best reward-per-risk in the whole space, and it exercises the entire loop machinery (branch → A/B → gate → promote → ledger) at trivial cost, which is exactly how you debug the loop before trusting it.

**Why wiring second.** SYNTHESIS §5: the cheapest custom modality is a new query wiring over an existing index, ≈ days, zero re-index tokens [code-verified via PathRAG]. Wiring mutation is the architecture's whole thesis, no new code executes, and every failure mode is either statically caught (type mismatch) or cheap and visible (a semantically incoherent but type-valid wiring simply scores badly). Failure is loud and free.

**Why code last — the real reason.** *You cannot safely evaluate LLM-written components until you have proven your evaluator.* §2 shows the evaluator is currently incapable of distinguishing a 5 pp improvement from noise. Permitting class 4 first means pointing an uncalibrated instrument at the most dangerous input class, and the failure mode is not a crash — it is an LLM-written component that looks correct, passes a noisy eval, gets promoted, and quietly degrades artifacts for months. Gate class 4 on: (i) classes 1–3 have produced a track record, (ii) A/A calibration exists, (iii) the isolation domain exists.

**Missing from every document:** the mutation **proposer** is itself an unversioned, unevaluated component [docs-verified]. Its hit-rate is the most important number in the system — at 2 M tokens per decision and a 5% win rate, improvement costs ~40 M tokens per win. Track proposer hit-rate *per mutation class* in the ledger; it is nearly free and it tells you whether to keep paying.

---

## 5. D's two-regime cost — is promotion cheaper than building in the kernel?

Decomposed honestly, the answer is **it depends entirely on which side of the index/query split the modality falls**, and CANDIDATES treats it as one question.

Baseline costs [code-verified via spike 001 line counts in PROJECT.md]: LightRAG's query side is ~794 lines across 5 stages (~160 each) with plain-data boundaries; the index side is ~1,786 lines welded to LightRAG's entity/relation ontology.

| Case | Sandbox cost | Kernel-direct cost | Verdict |
|---|---|---|---|
| **New query wiring over an existing recipe** (PathRAG-class) | 1–3 days adapter | **1–3 days** — 1–2 new components on shared stages | **Sandbox is pure waste.** Same cost, and kernel-direct buys deep traces, mutation, artifact sharing. Then you pay a migration on top. |
| **New index recipe** | 1–3 days adapter, and it can run on a 500-chunk sub-corpus for ~5% of the token bill | Weeks (the 1,786-line entanglement) **plus 10–50 M tokens to re-index** | **Sandbox genuinely cheaper** — its real value is *cheap disqualification before paying the index bill*, not hosting. |
| **Black boxes** (codebase-memory-mcp, CAG, ColBERT/PLAID blob indexes) | 1–3 days | **Undefined** — not high, unbounded | **Sandbox is the only option.** These never promote, and that is correct behaviour, not failure. |

[inference for day/week estimates; line counts and the PathRAG precedent are code-verified]

### 5.1 Does the sandbox become a graveyard?

**Partly, and the design should own it.** Three populations, not one:

1. **Transients** — trialed, then promoted or deleted. Healthy.
2. **Permanent residents** — unportable black boxes. Healthy, and CANDIDATES C is right that hosting them is unbeatable.
3. **Drifters** — valuable, portable, never ported, because the port is a week and "the sandbox version works fine." **This is the graveyard, and it is an organisational failure mode, not an architectural one.**

The cost of drift is precise and worth stating in the design: **sandbox residency = improvement opt-out.** Sandbox parts compare at answer level only [CANDIDATES §C/D, docs-verified], so the machine cannot mutate their components. Every day a valuable modality sits in the sandbox is a day it cannot be improved.

### 5.2 Two mechanisms that bound the cost

- **Promotion SLA.** Anything that is (a) selectable in production and (b) has survived K experiments must be either ported or explicitly declared a permanent resident with a written reason. Force the decision; do not let the default be drift.
- **Promotion economics rule.** Promote when (expected mutations/year on this modality × expected value per mutation) > port cost. With ports at 1–3 weeks and maybe 2 real wins per 10 mutations, that pays only for modalities *actually selected in production frequently*. **So: port the top 2–3 by production traffic; leave the tail in the sandbox permanently.** This bounds the kernel population by design — which is also what bounds attack 1.

### 5.3 Verdict on the two-regime cost

Real but **smaller than CANDIDATES fears, and located somewhere else than CANDIDATES expects.** The maintenance cost of two regimes is not the problem; the problem is that (i) the sandbox is currently justified by the wrong argument (hosting convenience rather than cheap disqualification + isolation domain), and (ii) with the improvement loop declared kernel-only, D is the only candidate whose registry growth and blast radius are both structurally bounded. D's two-regime cost is **worth paying, on two conditions** (§7).

---

## 6. Minimal machine services self-improvement actually requires

Beyond registry / budget / trace / rig. Forced by the attacks above, nothing speculative added.

**One versioned artifact:**

0. **Eval bundle @version** — questions + gold passages + judge + judge prompt + corpus snapshot hash, with dev/holdout split. Forced by §2.4. Without it, no promotion is reconstructable.

**Four services:**

1. **Promotion Gate** — takes two arms' per-question scores, returns promote / reject / inconclusive. Contains: stored A/A null distribution, paired significance test, minimum-effect floor, confirmation-run rule, epoch-level FDR, and the **hard-gate regression suite** as a veto (never averaged into the score). Forced by §2.
2. **Isolation Domain + Manifest Enforcement** — deny-by-default network, filesystem, and store-write; wall-clock watchdog; per-arm process boundary. This is goal 3's manifest made *enforced* rather than declared. Forced by §3. In D this is the sandbox, respecified.
3. **Artifact Ownership + GC** — write capability scoped to (recipe@version, namespace); copy-on-write for experimental arms; reference-counted GC of orphaned artifacts and traces; cache keys include component version. Forced by §1.4 and §3 rows 4–5.
4. **Promotion Ledger** — append-only, one small record per experiment: mutation id, class, parent, arms, effect size, gate decision, evidence pointer, proposer id. **Distinct from the lineage tree** — lineage says what exists, the ledger says what was decided and why. Serves navigability (§1.3), cross-experiment meta-analysis (§2.5.7), loser tombstoning, shared-component skew tracking (§1.2b), and proposer hit-rate (§4). Cheapest item here and the highest leverage.

**One registry function:**

5. **Static Mutation Validator** — type-checks a proposed wiring against component contracts; enforces caps (max nodes, loop budgets, config domains) *before* execution. It is what makes classes 1 and 2 of §4 safe enough to permit first.

Everything else the analysis surfaced — frontier caps, trace downsampling, index-vs-query budget split — is configuration of these five, not new machinery.

---

## 7. Ranking for safe self-improvement

| Rank | Candidate | Why |
|---|---|---|
| **1** | **D — Kernel + Sandbox** | Only candidate where registry growth *and* blast radius are both structurally bounded: improvement loop kernel-only, kernel population capped at 3–5 by promotion economics, sandbox as the isolation domain for untrusted mutations. Also the only one with a cheap-disqualification path before paying the index bill. **Conditional** — see falsifiers. |
| **2** | **B — Conductor** | Same expressiveness as D's kernel and the same versioning-native substrate, but no isolation domain (must be added), no cheap sub-corpus screening path, and a topologically unbounded mutation space that needs a schema cap not currently specified. B is D minus the jail, plus the temptation to run mutated code in-process. |
| **3** | **A — Stage Bus** | Best containment (the contract *is* the sandbox) and the most navigable registry. But it structurally cannot mutate control flow or harnesses — the highest-leverage surface, where CRAG/Self-RAG live. **The safest improver and the least capable one.** Correct choice only if you do not trust yourself to build isolation. |
| **4** | **C — Federation** | Safe because inert. Deserves genuine credit for one thing: **selection-level improvement (a router/bandit over engines) is the only improvement loop that is safe on day one with zero mutation-safety machinery.** But it can never improve a component, so the ceiling is permanent. |

**D and B are close.** D's advantage is entirely contingent.

### What would falsify the D recommendation

1. **The sandbox is not respecified as an isolation domain** — then D degrades to B plus maintenance cost, and the ranking flips to B.
2. **The promotion SLA is not enforced** — drifters accumulate, the kernel stays at one modality, and the sandbox is a graveyard. D becomes C with extra steps.
3. **The eval set stays at 30–50 questions** — then no candidate matters, because none of them can tell a real improvement from noise (§2.1). *This is the falsifier that dominates the architecture choice.*
4. **Kernel population is not capped** — attack 1's artifact/trace growth becomes unbounded and D loses its only structural advantage over B.

### The uncomfortable summary

The architecture debate is currently over-weighted relative to the evaluation debate. All four candidates fail the improve-loop at n=40 questions with no A/A null and no significance gate; two of them additionally fail on blast radius. **Order of work should be: eval bundle + promotion gate first (they are architecture-independent), then isolation domain, then pick between B and D.** Building the machine before the instrument means the first year of "self-improvement" is an unfalsifiable random walk with a rising scoreboard.

---
*Red team pass, self-improvement operability lens. 2026-08-10. Not committed.*
