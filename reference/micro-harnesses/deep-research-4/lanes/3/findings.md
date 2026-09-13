# Lane 3 findings: recall-side harnesses

## Admitted items

**IRCoT (Trivedi et al., 2022; arXiv:2212.10509).** Interleaves chain-of-thought
generation with retrieval so each reasoning step produces the query for the next
retrieval round, the canonical iterative recall loop for multi-hop QA. For
MelodyScribe the takeaway is architectural: recall is a budgeted loop owned by
the harness (retrieve → reason → re-query), not a single vector lookup; the
`fixpoint` node in the Databasise contract is the natural home for this loop and
its hop budget. Caution: all reported behavior uses large reader models, and the
paper's loop assumes every intermediate step is worth a retrieval call, which
later work (FLARE, ITER-RETGEN, DeepRAG) shows is wasteful.

**Self-RAG (Asai et al., 2023; arXiv:2310.11511).** Trains the model to emit
reflection tokens that decide whether to retrieve at all and to critique each
retrieved passage's relevance and support, enabling adaptive per-instance
retrieval. MelodyScribe should take the gating pattern: a cheap retrieve-or-skip
decision plus per-passage relevance/support verdicts before anything enters the
frontier payload. Caution: the gate is learned jointly with generation, so a
2B model with a contrastive embedding adapter (cf. brief spikes 004/006/011)
may not reproduce the gate's calibration without explicit reward on gate
accuracy.

**FLARE (Jiang et al., 2023; arXiv:2305.06983).** Forward-looking active
retrieval: draft the next sentence without retrieval, retrieve only when a
token's probability falls below a threshold θ (θ=0 never retrieves, θ=1 always),
and regenerate conditioned on the results. For MelodyScribe this is the cheapest
speculative-recall trigger available: token confidence from the one decode
already being run doubles as the retrieval gate, with θ as the single harness
knob trading recall coverage against latency. Caution: retrieved-then-regenerate
costs a second pass per trigger, so θ must be tuned against the grammar-decoding
bottleneck, and hypothetical-sentence queries can drift off-topic.

**DRAGIN (Su et al., 2024; arXiv:2403.10081).** Decides *when* to retrieve from
real-time information needs (attention- and confidence-weighted need signals
over generated tokens, with stopword filtering) and *what* to retrieve by
formulating queries from the uncertain spans. MelodyScribe should take the
two-signal split: a need detector (when) decoupled from a query formulator
(what), so the harness can log and ablate them separately. Caution: the
attention-based need signal assumes access to internals that are cheap in
research code but add plumbing on a served llama.cpp/SGLang path.

**ReAct (Yao et al., 2022; arXiv:2210.03629).** The thought→act→observe loop that
underlies every tool-calling recall agent: the model reasons, issues a retrieval
action, reads the observation, and repeats. MelodyScribe's query-time assembly
is a ReAct instance whose actions are store queries; the paper's contribution
here is only the discipline of making every retrieval an explicit, logged,
harness-executed action rather than an implicit model behavior. Caution: free
alternation has no stopping rule, so ReAct alone is insufficient without one of
this lane's stopping criteria (gates, thresholds, budgets).

**Search-R1 (Jin et al., 2025; arXiv:2503.09516).** Trains LLMs with
reinforcement learning to emit retrieval invocations wrapped in special
`<information>…</information>` tokens during reasoning, with outcome-only
rewards. For MelodyScribe this is the training-side complement to the harness:
retrieval-call tokens can be grammar-constrained markers whose placement is
shaped by validator/downstream reward, exactly the "design the harness first,
then fine-tune" thesis. Caution: RL with live search is expensive and
unstable at small scale, and the paper's models are far larger than 2B.

**Search-o1 (Li et al., 2025; arXiv:2501.05366).** Wraps long-reasoning models
with an agentic retrieval loop (search, filter, re-reason) so retrieval repairs
reasoning chains rather than merely prefacing them. MelodyScribe should take the
repair framing for its multi-cycle recall: later cycles exist to fix gaps in
earlier ones, which argues for carrying a compact "what is still missing" state
between cycles rather than re-issuing the raw query. Caution: built for
frontier-scale reasoners; the loop overhead is only justified when the first
pass is already strong.

**DeepRAG (Guan et al., 2025; arXiv:2502.01142).** Models retrieval-augmented
reasoning as a Markov decision process: decompose into subqueries, then per
subquery decide retrieve-vs-parametric, trained by imitation of minimal-cost
successful paths plus calibration of knowledge boundaries; reports +26.4%
answer accuracy with less retrieval. MelodyScribe should take the per-subquery
retrieve/parametric decision as its cycle policy and the minimal-retrieval
imitation objective as a fine-tuning target. Caution: binary-tree-search data
synthesis is heavyweight, and the calibration step presumes a model that can
assess its own knowledge boundary, unproven at 2B.

**OneGen (Zhang et al., 2024; Findings of EMNLP 2024; arXiv:2409.05152).** Adds
autoregressive retrieval tokens ([RQ]/[RD]) whose hidden states serve as
query/document encodings, unifying generation and vector retrieval in a single
forward pass (+1.5pt on single-hop QA over Self-RAG, +3.3 F1 multi-hop, +3.2
entity-linking accuracy). This is the closest published analogue of
MelodyScribe's one-decode embedding-plus-ops design and the strongest existence
proof that it can work without harming generation. Caution: it unifies only
*vector* retrieval; routing to graph/SQL/fact stores still needs a separate
mechanism, and joint contrastive+LM training is exactly what the brief's spikes
found fragile (op emission dies under pure contrastive pressure).

**HippoRAG (Gutiérrez et al., 2024; NeurIPS 2024; arXiv:2405.14831).** Builds a
schemaless OpenIE knowledge graph offline and runs Personalized PageRank from
query-linked concepts at recall time, doing multi-hop reasoning in a single
retrieval step: up to +20% over prior RAG, matching iterative IRCoT at 10–20×
lower cost and 6–13× lower latency, with further gains when combined with
IRCoT. MelodyScribe should take single-step PPR-over-graph as the default
graph-recall path and keep the iterative loop only as backoff, since PPR's
cost/latency profile fits a real-time co-processor. Caution: gains concentrate
on entity-centric multi-hop sets (MuSiQue, 2Wiki); on HotpotQA the paper itself
reports weakness from low knowledge-integration need and the concept–context
tradeoff (see Refutations).

**HippoRAG 2 (Gutiérrez et al., 2025; arXiv:2502.14802).** Fixes HippoRAG's
entity-centrism three ways: passage nodes joined by "contains" edges
(dense–sparse integration), query-to-triple linking instead of NER, and an LLM
recognition-memory filter over candidate triples; 59.8 vs 57.0 mean F1 against
NV-Embed-v2 over seven benchmarks and Recall@5 78.2 vs 73.4. MelodyScribe should
take all three as specified mechanisms: (1) index passages alongside phrases,
(2) seed PPR from query–triple matches, (3) gate seeds through a relevance
filter before propagation. Caution: the online LLM filter adds a call per
query, and reset-probability balancing between phrase and passage nodes is a
tuned constant, not a learned policy.

**LightRAG (Guo et al., 2024; Findings of EMNLP 2025; arXiv:2410.05779).**
Dual-level retrieval (low-level entity/relation lookup plus high-level
topic/theme lookup) over a graph index with vector matching, one-hop neighbor
expansion, and incremental updates: under 100 tokens and a single LLM call per
query versus ~610K tokens and hundreds of calls for community-traversal
GraphRAG. MelodyScribe should take the low/high two-tier query shape as its
recall fan-out (one specific tier, one abstract tier) and the union-merge
incremental update rule for store writes. Caution: keyword→entity/relation
matching quality bounds everything, and the paper's cost comparison is against
the most expensive GraphRAG configuration, not against lean vector baselines.

**MIRIX (Wang & Chen, 2025; arXiv:2507.07957).** Six typed stores (Core,
Episodic, Semantic, Procedural, Resource, Knowledge Vault) under a Meta Memory
Manager that routes writes in parallel and a Chat Agent that does coarse
retrieval over summaries followed by targeted per-store retrieval (Active
Retrieval: generate a topic, then retrieve top-10 into the system prompt);
85.4% on LoCoMo and +35% over RAG on ScreenshotVQA at −99.9% storage. This is
the nearest full-system precedent for MelodyScribe's typed-store routing plus
two-stage recall, and its coarse-then-targeted pattern maps directly onto
vector-first ranking with graph/SQL backoff. Caution: evaluated with large
models only, and the six-manager fan-out assumes serving capacity far beyond
one 16 GB card.

**Adaptive-RAG (Jeong et al., 2024; NAACL 2024; arXiv:2403.14403).** A small
language model classifies each query into A (answer directly), B (single-step
retrieval), or C (multi-step retrieval), with labels auto-collected from
model-outcome and dataset-bias signals; beats one-size-fits-all on accuracy and
efficiency across single- and multi-hop sets. MelodyScribe should take the
complexity-gated three-lane policy verbatim: most queries should cost zero or
one retrieval round, and the classifier itself can be far smaller than the 2B
extractor. Caution: only three coarse levels, and auto-labels inherit the
biases of the datasets used to mine them.

**ITER-RETGEN (Shao et al., 2023; arXiv:2305.15294).** Uses the previous
iteration's full generation as context for the next retrieval round; the paper's
ablation finds two iterations give most of the gain, with diminishing returns
after. For MelodyScribe this is the empirical hop cap: budget recall at two
cycles by default and require measured justification for more. Caution: the
result is on standard QA with large models; memory-recall queries with
adversarial or temporal structure may not share the same knee.

**MemGPT (Packer et al., 2023; arXiv:2310.08560).** OS-style virtual context
management: main vs external memory tiers, function-call paging, and
`request_heartbeat` chaining so the model performs multi-step recall inside one
task. MelodyScribe should take heartbeat-style chaining as the precedent for
its asyncio-workers-over-one-model-lock design: the model explicitly requests
continuation rather than the harness guessing. Caution: the agent self-manages
memory with no validator in the loop, which MelodyScribe's Proof stage must not
replicate.

**GritLM (Muennighoff et al., 2024; arXiv:2402.09906).** Generative–
representational instruction tuning unifies embedding and generation in one
model at no loss versus single-task variants, halving RAG forward passes
(>60% faster RAG on long documents). This is the serving precedent for
MelodyScribe's one loaded model process: embedding and generation can share
weights and cache computation, provided the two objectives are kept in separate
instruction streams. Caution: unification was demonstrated at 7B+; the brief's
own spikes show the embedding/op co-training tradeoff is harsher at 2B, and
4096-dim outputs are storage-heavy.

**Self-Ask (Press et al., 2022; arXiv:2210.03350).** Explicitly decomposing a
compositional question into follow-up subquestions answered by retrieval
narrows the compositionality gap where direct answering fails. MelodyScribe
should take follow-up decomposition as one of its query-rewrite operators at
recall time. Caution: the paper's decompositions are model-generated in
unconstrained text, whereas MelodyScribe needs them grammar-constrained and
offset-grounded to survive Proof.

**LoCoMo (Maharana et al., 2024; ACL 2024; arXiv:2402.17753).** Very-long
dialogue recall benchmark (v1: 50 dialogues, ~300 turns/9K tokens; ACL release:
10 dialogues, ~600 turns/16K tokens) with five QA categories including
temporal and adversarial; long-context and RAG models improve 12–66% yet lag
humans badly, especially on temporal reasoning and speaker attribution.
MelodyScribe should adopt LoCoMo's category split (single-hop, multi-hop,
temporal, open-domain, adversarial) as its recall scorecard, since each
category maps to a different store/cycle in the harness. Caution: human-human
dialogues, not assistant interaction logs, so transfer to co-processor recall
is indirect.

**LongMemEval (Wu et al., 2024; arXiv:2410.10813).** 500 curated questions over
five memory abilities with a freely scalable history (S: ~115K tokens,
M: ~500 sessions/1.5M tokens), plus the most actionable recall ablations in the
lane: round- (not session-) granularity values, fact-expanded retrieval keys
(+9.4% recall@k, +5.4% QA), time-aware query expansion (+6.8–11.3% temporal
recall), and Chain-of-Note plus structured reading (+10 pts QA with perfect
recall). MelodyScribe should take all four as specified recall defaults.
Caution: the benchmark is single-vector-store oriented, so its numbers do not
cover cross-store fusion or graph PPR.

**RAG-Fusion (Rackauckas, 2024; arXiv:2402.03367).** Multi-query generation
fused by reciprocal rank fusion; reports more comprehensive answers but also
off-topic drift when generated queries are weakly relevant, evaluated manually
on undisclosed queries. For MelodyScribe the value is cautionary, not
prescriptive: multi-query fan-out without a relevance gate injects noise, which
is direct evidence for gating every fused stream. Admitted at relevance 1 for
this reason only.

**Zep (Rasmussen et al., 2025; arXiv:2501.13956).** Bi-temporal knowledge-graph
edges (validity windows with invalidation-not-deletion), episode-level
provenance for every fact, and hybrid semantic+keyword+graph recall. MelodyScribe
should take the bi-temporal edge plus episode-pointer schema as its graph
recall contract: every recalled item carries when-it-was-true and the raw
source it came from. Caution: the paper describes the managed Zep system, not
the OSS Graphiti core, so latency/throughput figures do not transfer directly.

**Graphiti repo (getzep/graphiti; Abt 30.9k stars per GitHub API/page,
Apache-2.0, pushed 2026-09-11; https://github.com/getzep/graphiti).**
Production OSS implementation of the Zep-style temporal graph with hybrid
retrieval and an MCP server; its README explicitly warns that small/local
models frequently emit schema-invalid extraction JSON. For MelodyScribe the
takeaway is twofold: hybrid recall without LLM summarization is deployable at
sub-second latency, and small-model structured output must be treated as
unreliable by default (grammar constraints + validator, as already planned).
Caution: no peer-reviewed paper for the codebase itself; behavior claims rest
on the README and the companion Zep paper.

**LlamaIndex routers (run-llama/llama_index; ~52k stars, MIT; official router
docs opened 2026-09-13).** RouterQueryEngine/RouterRetriever with LLM and
Pydantic single/multi selectors that route one query across heterogeneous
engines (e.g. summary vs vector) or fan out to several and combine. MelodyScribe
should take the selector-over-described-tools shape as its query-routing
interface: each store exposes a description, a small selector picks stores per
query, multi-select is a first-class mode. Caution: selection quality is bounded
by tool-description quality, and every selective route is an extra LLM call on
the critical path unless the selector is a distilled small model.

## Refutations

1. **"Graph retrieval dominates vector retrieval, so route to graph first."**
Refuted by HippoRAG itself (arXiv:2405.14831, verified NeurIPS proceedings
text): on HotpotQA it underperforms because of that set's low
knowledge-integration need, and the authors attribute a systematic weakness to
the concept–context tradeoff. The brief's vector-first with graph-as-backoff
(spike 010) is therefore the correct default, not a stopgap.
2. **"More retrieval rounds monotonically help."** Refuted three ways:
ITER-RETGEN's ablation (verified PDF text) finds two iterations capture most of
the gain; FLARE (arXiv:2305.06983) retrieves only below a confidence threshold
precisely because unnecessary retrieval wastes compute and risks bad context;
DeepRAG's abstract states redundant retrieval "can introduce noise and degrade
response quality." Recall budgets should be small and gated, not maximal.
3. **"Naive score fusion across stores is safe."** Qualified into a rejection:
HippoRAG 2 (arXiv:2502.14802) replaces HippoRAG's flat document-ensemble score
aggregation with structured dense–sparse integration and reports comprehensive
gains; flat fusion bonuses lowering recall (brief spike 010) is consistent with
this. Fuse by structure (PPR seeds, rank gates, tiered levels), never by adding
raw scores.

## Unresolved ledger

- Hop-count and threshold numbers for 1–3B models: every loop paper above uses
large readers; no verified numbers exist for when a 2B extractor should stop
retrieving. Reason: literature gap, not yet screened out.
- Whether RRF with k=60 transfers to heterogeneous five-store fusion: the RRF
result is verified (SIGIR 2009, DOI 10.1145/1571941.1572114) but covers
homogeneous TREC rankings only, and it is abstained (no arXiv PDF filed).
Reason: primary paywalled; filed copy would violate the papers/ naming rule.
- Mem0's recall accuracy on LongMemEval/LoCoMo: vendor-site numbers only, no
paper opened. Reason: secondary source only; recorded as abstain.
- RankRAG and other ranker-in-the-loop retrievers: identified, not opened.
Reason: budget; no claim asserted.
- LlamaIndex SQLAutoVectorQueryEngine routing behavior: not verified at its
docs page. Reason: page not opened; recorded as abstain.
- Small-model (≤3B) recall agents with published LoCoMo/LongMemEval/BRIGHT
numbers: none found; MIRIX's 85.4% uses large models. Reason: literature gap.

## Security findings (stated as requirements)

1. Every recalled payload item must carry provenance (source episode/offsets)
and temporal validity, per the Zep/Graphiti schema, so poisoned or stale store
content is attributable and expirable rather than anonymous context.
2. Every fused stream must pass a relevance gate before entering the frontier
payload (HippoRAG 2 recognition-memory filter; Self-RAG support verdicts),
because multi-query fan-out without gating demonstrably drifts off-topic
(RAG-Fusion) and redundant retrieval degrades answers (DeepRAG).
3. The harness must implement abstention as a first-class recall outcome:
LoCoMo's adversarial category and LongMemEval's abstention ability show models
otherwise hallucinate speaker attribution and unanswerable content; recall that
cannot support an answer must return "insufficient evidence," never a guess.

## Harness implications

1. Make recall a harness-owned budgeted loop (retrieve → reason → re-query, cap
two cycles by default) with per-cycle missing-information state, resting on
IRCoT, ITER-RETGEN, Search-o1, and the DeepRAG MDP framing.
2. Gate every retrieval round on predicted need (Self-RAG reflection tokens,
FLARE θ threshold, DRAGIN when/what split, Adaptive-RAG A/B/C classifier)
rather than retrieving unconditionally.
3. Rank vector first and use graph PPR and SQL as gated backoff, resting on the
HippoRAG HotpotQA refutation and the MIRIX coarse-then-targeted pattern.
4. Fuse stores by structure only (PPR seed weighting, rank gates, LightRAG
low/high tiers, query-to-triple seeding), never by flat score addition,
resting on HippoRAG 2 and the spike-010 fusion finding.
5. Unify embedding and generation in the one 2B process with separate
instruction streams (GritLM, OneGen retrieval tokens), and emit retrieval calls
as grammar-constrained marker tokens trainable by downstream reward (Search-R1).
6. Adopt the LongMemEval recall defaults verbatim: round-granularity values,
fact-expanded keys, time-aware query expansion, and structured Chain-of-Note
reading.
7. Score recall per LoCoMo category (single-hop, multi-hop, temporal,
open-domain, adversarial) instead of one aggregate number, and require an
explicit abstain outcome.
8. Attach episode provenance and validity windows to every recalled item and
filter all fused candidates through a relevance gate before frontier assembly,
resting on Zep/Graphiti, HippoRAG 2, Self-RAG, and RAG-Fusion's drift warning.
