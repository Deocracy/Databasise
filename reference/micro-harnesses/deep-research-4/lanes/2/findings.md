# Lane 2 findings — ingest-side routing to typed stores

Scope: how memory layers decide where a fact goes and with what schema — which store
taxonomies converge, and how "this is code" / "this is a date" is decided (rules,
classifier, or the model). All arXiv ids below were opened at `arxiv.org/abs/<id>`;
mechanism claims were additionally checked against arXiv full-text HTML and repo
READMEs (see method.md). 2026 preprints are cited for what their authors report.

## (a) Admitted items

**1. MIRIX — six stores, six routing agents, one meta-router (arXiv:2507.07957).**
MIRIX defines Core, Episodic, Semantic, Procedural, Resource, and Knowledge Vault
memory, assigns a dedicated Memory Manager agent to each, and puts a Meta Memory
Manager above them "responsible for task routing", with separate Memory Update and
Conversational Retrieval workflows; it reports 85.4% on LoCoMo and +35% over a RAG
baseline on ScreenshotVQA at 99.9% less storage. Take: per-store owner agents plus
one explicit router is the closest published analogue to MelodyScribe's
emit-ops/Proof-files-them split — MelodyScribe just compiles the router and the
owners into grammar + validator instead of agents. Caution: all routing numbers come
from frontier-class models; nothing here says a 2B model can do the routing, which
is exactly MelodyScribe's open risk. Repo: https://github.com/Mirix-AI/MIRIX
(3441 stars, Apache-2.0).

**2. Mem0 — op-based ingest with ADD/UPDATE/DELETE (arXiv:2504.19413).**
The add phase extracts candidate facts, retrieves similar existing memories, and has
the model emit ADD, UPDATE, DELETE (or NONE) per fact, resolving conflicts before
writing; a newer variant adds a graph store with entity/relationship extraction for
relational facts. Take: this is the cleanest existence proof that routing can be
framed as a small closed op set over retrieved neighbours — MelodyScribe's op list
should be judged against ADD/UPDATE/DELETE/NONE completeness, and "update" and
"contradict" deserve first-class ops, not just "store". Caution: conflict resolution
is LLM judgment with no validator; MelodyScribe's Proof-side quote/date checks are
the missing piece, not the op set. Repo: https://github.com/mem0ai/mem0
(65k stars, Apache-2.0).

**3. Zep — temporal graph ingest with invalidation (arXiv:2501.13956).**
Ingest turns messages into episodes, extracts entities, edges, and facts, and
invalidates (`invalid_at`) contradicted edges instead of deleting them, keeping a
bi-temporal history; it beats MemGPT on the Deep Memory Retrieval benchmark.
Take: never-delete, timestamp-and-invalidate is the correct primitive for dates,
settings, and any fact that can change — MelodyScribe's SQL `facts` table and graph
edges should carry validity intervals, and contradiction should be an edge state,
not a delete. Caution: extraction is heavyweight LLM-per-message; the paper does
not show the ingest cost curve that Total Recall later demands. Impl:
https://github.com/getzep/graphiti (30k stars, Apache-2.0).

**4. Cognee — pipelines and rules instead of per-fact model routing (arXiv:2505.24478).**
Cognee builds knowledge graphs through configurable ECL (extract/cognify/load)
pipelines over chunks, and the paper's contribution is systematic tuning of
chunking, construction, and retrieval hyperparameters on HotPotQA/TwoWiki/MuSiQue.
Take: the opposite end of the spectrum from MIRIX — routing decided once in pipeline
configuration, with chunk boundaries and granularity doing the work that model calls
do elsewhere. Caution: this only covers text-to-graph; there is no typed-store
choice at all, so it cannot answer code-vs-date. Repo:
https://github.com/topoteretes/cognee (30k stars, Apache-2.0).

**5. MemGPT — the model routes by issuing paging calls (arXiv:2310.08560).**
Virtual context management splits main context from recall and archival stores;
placement and movement happen exclusively through model-issued function calls
(paging in/out). Take: the original proof that a harness can own the stores while
the model owns every routing decision via a function interface — MelodyScribe's
grammar-constrained ops are a strict, validated descendant of this interface.
Caution: no schema per store beyond the main-context block format, and no validity
or conflict machinery; every hard ingest problem in this lane postdates it.
Lineage repo: https://github.com/letta-ai/letta (24k stars, Apache-2.0).

**6. MemoryBank — forgetting as an admission/decay policy (arXiv:2305.10250).**
A long-term store with Ebbinghaus-curve forgetting and an explicit memory-updating
path, so retention strength decays unless reinforced. Take: forgetting is a routing
decision in reverse — MelodyScribe needs a symmetric un-route (decay, demote,
expire) for every store, or bulk ingest will silt all five; decay curves are the
simplest admission gate that requires no model call. Caution: decay is global and
content-blind; it cannot distinguish a birthday (never decay) from chatter.

**7. MemOS — typed memory units plus an explicit scheduler (arXiv:2507.03724).**
MemCube gives every memory a uniform type/tier envelope and MemScheduler moves
units across plaintext, activation, and parameter tiers with lifecycle control.
Take: the OS framing MelodyScribe should copy — separate the unit envelope (what
store, what schema, what validity) from the scheduler (when to move/promote/evict),
because MelodyScribe's one-GPU bulk-vs-realtime contention is a scheduling problem
wearing a routing costume. Caution: two same-team papers in two months (with
2505.22101) signal a fast-moving, still-settling design; adopt the envelope idea,
not the API. Repo: https://github.com/MemTensor/MemOS (11k stars, Apache-2.0).

**8. A-MEM — agentic linking plus backward evolution (arXiv:2502.12110, NeurIPS 2025).**
New memories become Zettelkasten notes (description, keywords, tags); the agent
links them to historical notes and evolves old notes' representations in light of
the new one. Take: ingest must write backwards as well as forwards — filing an op
should be allowed to touch existing graph neighbours and vector entries (re-tag,
re-link, invalidate), which argues for Proof rules that permit bounded
multi-record transactions, not single-record appends. Caution: unconstrained
evolution risks memory drift and attacker-controlled rewriting (see Chronos below).
Repo: https://github.com/agiresearch/A-mem (1178 stars, MIT).

**9. Mem-α — construction policy learned by RL (arXiv:2509.25911).**
Instead of prompted heuristics, an RL framework trains the agent to decide what to
store, how to structure it, and when to update it. Take: direct support for the
owner's harness-first thesis — the harness defines the construction action space
and the reward, and routing skill is trained into the small model rather than
prompted out of it. Caution: reward design is everything and the paper's rewards
are QA-accuracy-shaped; MelodyScribe should reward Proof-pass and retrieval-hit,
not just downstream answer quality (see lane 10).

**10. Memory-R1 — GRPO for manage-and-utilize (arXiv:2508.19828).**
An RL loop (GRPO) over store/update/retrieve actions on an external bank replaces
static heuristic pipelines. Take: second independent point (with Mem-α) that the
field is moving from "prompt the router" to "train the router" — and that the
training signal comes from harness events (store/update/retrieve outcomes), which
MelodyScribe's Proof validator already emits for free. Caution: only a repro repo
exists publicly; treat the method as promising, not replicated.

**11. Learn to Memorize — adaptive memory with memory-cycle effects (arXiv:2508.16629).**
Replaces expert-predefined mechanisms with a data-driven framework that models the
store/recall cycle of interactive settings. Take: routing policy should be fit to
the interaction loop (bulk ingest vs live co-processor have different cycles), not
one static rule — supports separate ingest-time and query-time routing postures in
MelodyScribe. Caution: small repo footprint (18 stars); mechanism needs
independent confirmation. Repo: https://github.com/nuster1128/learn_to_memorize.

**12. HippoRAG — parser-built graph, PPR retrieval (arXiv:2405.14831, NeurIPS 2024).**
OpenIE extracts phrases/entities into a KG and Personalized PageRank runs over
it; single-step retrieval matches iterative IRCoT at 10–30x lower cost and 6–13x
lower latency. Take: ingest does not have to be model-based — a deterministic
parser (OpenIE, and by extension tree-sitter/LSP for code) can build the graph the
small model then queries, which is exactly how MelodyScribe should treat code
detection (parser decides, model never guesses). Caution: OpenIE quality bounds the
graph; hero numbers are multi-hop QA, not store-routing accuracy. Repo:
https://github.com/OSU-NLP-Group/HippoRAG (4000 stars, MIT).

**13. From RAG to Memory — ingest as continual learning (arXiv:2502.14802).**
The HippoRAG team's framing of memory as non-parametric continual accumulation
organized by PPR across sessions. Take: licenses treating MelodyScribe's stores as
accumulating indexes with update/invalidate semantics rather than a database with
transactions — no catastrophic forgetting because nothing parametric is overwritten.
Caution: conceptual framing paper; the hard versioning mechanics still come from
Zep/A-MEM.

**14. LightRAG — dual-level keywords, entities as index keys (arXiv:2410.05779).**
Extraction produces low-level (specific) and high-level (thematic) keywords;
entities and relations carry them as retrieval keys in a hybrid graph+vector
setup. Take: the routing decision can be lexicalized — the keywords the extractor
emits determine which level of the graph a fact lands in, a pattern MelodyScribe
can copy by letting op arguments (entity names, tags) double as index keys rather
than running a separate classifier. Caution: LightRAG-style wording is known to
collapse on small models (brief spike 008); the keyword idea must be re-expressed
in one-shot held-out-example form. Repo: https://github.com/HKUDS/LightRAG
(39k stars, MIT).

**15. GraphRAG — community summaries, with gleanings (arXiv:2404.16130).**
LLM-extracted graph plus Leiden communities with precomputed summaries; optional
"gleaning" repair passes recover missed entities. Take: gleanings are the
respectable name for a second-pass ingest sweep — MelodyScribe should plan a cheap
async repair pass (missed entity/quote backfill) rather than demanding perfect
one-pass extraction. Caution: full community summarization is far too expensive
per-op for a 2B co-processor; import the gleaning pattern, not the pipeline.
Repo: https://github.com/microsoft/graphrag (35k stars, MIT).

**16. RAPTOR — model-free hierarchical ingest (arXiv:2401.18059).**
Recursive embed → GMM-cluster → summarize builds a tree with multiple abstraction
levels; placement is statistical, no per-fact model call. Take: the baseline any
model-routed hierarchy must beat — if a 2B router cannot outperform recursive
clustering on placement quality per unit cost, delete the router and keep the
clustering for the vector store. Caution: summaries are lossy and unquoted, which
violates MelodyScribe's verbatim-evidence rule; use for vector organization only.
Repo: https://github.com/parthsarthi03/raptor (1756 stars, MIT).

**17. Hindsight — evidence/inference split with reflection (arXiv:2512.12818).**
Retain/recall/reflect separation that keeps verbatim evidence distinct from model
inference and organizes beyond snippet extraction. Take: independent convergence
on MelodyScribe's core rule — quotes are harness-resolved data, never model text —
plus reflection as a named post-ingest consolidation stage (a home for Folio
distillation and auto-dream style merge passes). Caution: commercial system; the
paper is also the product pitch — verify consolidation claims against the repo
before copying mechanics. Repo: https://github.com/vectorize-io/hindsight
(23k stars, MIT).

**18. RuleMem — rules as a validated store (arXiv:2609.03915).**
Reusable natural-language Horn clauses induced from dialogue, admitted only after a
Rule Perplexity validation check, then actively guiding retrieval and reasoning.
Take: the template for MelodyScribe's procedural/learning content — induced rules
(pass the validator, earn admission) rather than stored raw, with validation as a
numbered gate exactly like Proof. Caution: September-2026 single-version preprint;
the perplexity gate needs replication at small-model scale.

**19. Chronos vulnerability — memory attacks taxonomy (arXiv:2607.19433).**
Names MINJA (memory injection) and sleeper-agent persistence as first-class threats
against stateful agents with long-term memory. Take: every ingest path in
MelodyScribe is an attack surface — admission gating, provenance, and invalidation
are security requirements, not hygiene (detailed in §(d)). Caution: taxonomy
paper; it organizes threats but tests no defenses.

**20. LoCoMo — very-long dialogue substrate (arXiv:2402.17753).**
Machine-human pipeline generating multi-session persona- and event-graph-grounded
dialogues with QA pairs. Take: the shared substrate that makes routing comparisons
possible at all — any MelodyScribe routing ablation should run on LoCoMo-shaped
data so numbers are comparable to MIRIX/Mem0/Hindsight reports. Caution: dialogue
memory only; no code, no dates-as-facts, no store-choice labels — it measures
recall, not routing, so it cannot score a wrong-store decision directly.

**21. LongMemEval — update and abstention splits (arXiv:2410.10813, ICLR 2025).**
500 curated questions over scalable histories covering extraction, multi-session
and temporal reasoning, knowledge updates, and abstention. Take: the
knowledge-update split is the closest public proxy for routing correctness (did
the new fact land where the question can find it) and abstention is the proxy for
wrong-store cost (answer from the wrong store should be no answer). Adopt both
splits as MelodyScribe ingest evals. Caution: still QA-shaped; no per-op routing
labels. Repo: https://github.com/xiaowu0162/LongMemEval (1083 stars, MIT).

**22. AgentMemBench — five management strategies head-to-head (arXiv:2608.00009).**
In-context windowing, external key-value, graph episodic, compression
summarization, and web-augmented memory compared identically on LoCoMo and
document-grounding sets. Take: the first fair fight between management strategies —
use its harness design (identical conditions, shared datasets) as the template for
MelodyScribe's own routing ablation (grammar-ops vs classifier vs pipeline), and
read its strategy ranking before assuming graph+vector beats simpler stores.
Caution: single-author June-2026 preprint; check dataset leakage controls before
trusting the ranking.

**23. Total Recall at What Cost — serving-cost benchmark (arXiv:2608.11879).**
Mem0, Hindsight, and Mastra observational memory vs rolling-window and
full-transcript baselines on 665 LoCoMo questions to 400 turns: serving cost
cannot be predicted from conversation length, and every cost number is paired with
accuracy. Take: the paper this lane needed most — it makes wrong-store and
over-store choices legible as tokens-per-accuracy-point, which is the unit
MelodyScribe's ingest budget should be denominated in; cost must be measured with
accuracy attached or it misleads. Caution: two-backbone, three-system snapshot;
treat as method template plus order-of-magnitude priors, not constants.

**24. MERIT — marginal utility of memory for tool agents (arXiv:2609.05441).**
Leak-checked episodic tool-use tasks with a difficulty ladder, measuring whether
remembered facts change what the agent does under explicit cost accounting.
Take: reframes the routing question correctly for MelodyScribe — a store choice is
right iff it changes a downstream tool call (or the frontier payload) for the
better, per unit cost — which argues for logging routing decisions against later
retrieval hits as the training signal (cf. lane 10). Caution: brand-new
(July-2026) harness+benchmark; task distribution is narrow (three domains).

**25. Memori — triple-extraction ingest for token economy (arXiv:2603.19935).**
An LLM-agnostic persistent layer whose Advanced Augmentation pipeline converts
dialogue into compact semantic triples plus summaries to cut prompt token cost.
Take: triples-plus-summary is a credible schema for MelodyScribe's semantic/fact
content, and the paper's explicit token-economy motive matches the one-pass
emission constraint — extraction shape should be chosen to minimize emitted
tokens per filed fact. Caution: vendor-adjacent (16k-star commercial repo,
NOASSERTION license); verify the augmentation pipeline in code, not prose. Repo:
https://github.com/MemoriLabs/Memori.

Repo-only admits: **Letta** (https://github.com/letta-ai/letta) covers the brief's
Letta seed — maintained MemGPT lineage, no separate ingest paper exists; **Graphiti**
(https://github.com/getzep/graphiti) is the running code behind the Zep paper's
ingest claims.

## (b) Refutations

**R1 — Against "more stores are self-evidently better": the cost-aware 2026
benchmarks refute cost-free memory.** Total Recall (2608.11879) shows serving cost
is unpredictable from conversation length and must be paired with accuracy;
AgentMemBench (2608.00009) forces all five management strategies onto identical
footing instead of letting each paper choose its flattering baseline; MERIT
(2609.05441) shows conversational-recall scores do not predict whether memory
changes tool-agent behavior. Jointly they refute any harness argument of the form
"store X scored higher on LoCoMo, therefore route more there" — the claim the
MelodyScribe report must never make without cost-attached, task-grounded numbers.

**R2 — Against "the model should emit character offsets": Hindsight and the brief
agree, and no admitted paper defends model-emitted offsets.** Hindsight
(2512.12818) keeps evidence separate from inference as an architectural principle;
Zep (2501.13956) resolves mentions to graph elements harness-side; Mem0
(2504.19413) resolves against retrieved neighbours. The brief's
harness-resolved-verbatim-quote rule stands uncontradicted.

**R3 — Against "one store taxonomy has converged": taxonomies diverge, mechanisms
recur.** Six stores (MIRIX), ECL pipelines (Cognee), paging tiers (MemGPT),
MemCube tiers (MemOS), Zettelkasten notes (A-MEM), triples+summary (Memori),
Horn-clause rules (RuleMem), community summaries (GraphRAG), recursive trees
(RAPTOR) — nine different answers. What converges is not the taxonomy but three
mechanisms: (i) a closed op/paging interface between model and harness, (ii)
harness-side resolution of references, (iii) invalidation/versioning instead of
deletion. Design those three; treat any specific store count as provisional.

**R4 — Correction to the brief's seed list: "MemBench" and a standalone
"HippoRAG 2" paper could not be verified.** No memory-harness benchmark named
MemBench exists (DiceDB's membench is an unrelated DB benchmark); the closest
verified artefact is AgentMemBench (2608.00009). ArXiv 2505.03234 is a
clinical-trials paper, not HippoRAG 2; the HippoRAG team's continual-learning
position is 2502.14802. "Mem-alpha" resolves to Mem-α (2509.25911); "Memori"
resolves to Memori (2603.19935).

## (c) Unresolved ledger

- **Supra Cognitive Modes: A Routed Architecture for Agent Memory (2607.19096)** —
  the most on-point title seen; abs page not opened in budget. Recommend promotion
  to admit next round.
- **FluctlightDB: A Memory Model of Data for AI Agents (2608.12365)** — memory
  data-model proposal adjacent to typed-store schema design; title-only screening.
- **ZenBrain 7-layer architecture (2604.23878), TRUSTMEM consolidation
  (2606.25161), Graph-Native Belief Revision (2603.17244)** — layered/verified
  alternatives to the six-store view; title-only screening.
- **memoripy / matrixorigin-memoria** — snippet-screened repos with admission
  policies and integrity framing; repos not opened.
- **"This is code" decision** — no admitted paper studies code-vs-text routing;
  HippoRAG's parser-built graph is the nearest evidence (parser decides). The
  code-graph lane carries the rest; this lane records that the decision should be
  a deterministic parser/extension signal, not a model judgment, but has no
  measured comparison to cite.
- **"This is a date" decision** — Zep extracts temporal facts model-side; no paper
  compares regex/rule date detection against model extraction for routing
  accuracy. MelodyScribe's Proof-side date check is stricter than anything
  published; its false-reject rate is unmeasured anywhere.
- **Routing accuracy as a metric** — no public dataset labels per-fact store
  choice; LongMemEval's update split and MERIT's marginal utility are proxies.
  A MelodyScribe-native routing-accuracy eval (op choice vs oracle store) does not
  exist yet and must be built (lane 10 input).

## (d) Security findings (stated as requirements)

- **S1 — Treat every ingest path as untrusted input (Chronos 2607.19433).**
  MINJA-style memory injection and sleeper persistence target exactly the
  store-from-conversation loop MelodyScribe runs. Requirement: Proof must validate
  quotes against source text AND the source must carry provenance (which turn,
  which speaker, which document); unattributed ops are rejected, not filed.
- **S2 — Gate evolution and contradiction (A-MEM 2502.12110 + Chronos).**
  Backward evolution (old notes rewritten on new arrivals) is also the
  attacker's write primitive. Requirement: multi-record ingest transactions
  require a higher gate than appends (human, sandbox, or trust-tier rule), and
  invalidation (Zep-style) is always preferred over silent overwrite.
- **S3 — Quarantine Folio-distilled and rule-induced content (RuleMem 2609.03915,
  Hindsight 2512.12818).** Induced rules and reflections are inference, not
  evidence. Requirement: induced content lands in a separate tier (Folios /
  learning graph) that is never used as verbatim evidence, and its admission
  passes a named validation gate with a logged score.

## Harness implications

1. Give every store a dedicated owner (agent today, grammar+validator slot
   tomorrow) under one explicit meta-router, as MIRIX does with six Memory
   Managers plus a Meta Memory Manager for task routing (2507.07957).
2. Frame ingest as a closed op set with update/contradict semantics
   (ADD/UPDATE/DELETE/NONE), resolving each op against retrieved neighbours
   before filing, as Mem0 does (2504.19413).
3. Resolve all references harness-side — quotes to offsets, mentions to graph
   elements — and never accept model-emitted positions, per Hindsight's
   evidence/inference split and Zep's harness-resolved extraction (2512.12818;
   2501.13956).
4. Invalidate, don't delete: carry validity intervals on facts and edges and
   contradict by state change, as Zep's bi-temporal edges do (2501.13956).
5. Decide "this is code" with a deterministic parser signal (tree-sitter/LSP),
   not model judgment, following HippoRAG's parser-built graph precedent
   (2405.14831).
6. Ship a decay/expire path symmetric to every ingest path so bulk loading
   cannot silt the stores, starting from Ebbinghaus-style forgetting
   (2305.10250) and MemCube/scheduler lifecycle control (2507.03724).
7. Allow bounded backward evolution on ingest (re-tag, re-link, invalidate
   neighbours, per A-MEM (2502.12110)) but gate multi-record writes above
   appends, with provenance required on every op (2607.19433).
8. Measure every routing choice as accuracy-per-serving-cost with the cost
   attached (2608.11879), ablate strategies under identical conditions
   (2608.00009), and score marginal task utility rather than recall alone
   (2609.05441).
9. Train the router, don't just prompt it: define the construction action space
   in the harness and reward Proof-pass and retrieval-hit, the path Mem-α
   (2509.25911) and Memory-R1 (2508.19828) point to.
10. Run a cheap async repair/gleaning pass for missed entities and quotes
    rather than demanding perfect one-pass extraction, as GraphRAG's gleanings
    practice shows (2404.16130).
