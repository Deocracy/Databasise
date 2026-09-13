# Lane 9 findings: Structured facts store (SQL-shaped memory)

Scope: what schema the SQL store should have in v0.1, and how the harness decides a piece is SQL-shaped.
Screened 143 candidates; admitted 26 (20 papers with PDFs in `papers/`, 6 repos/models). All arXiv ids below
were opened at `https://arxiv.org/abs/<id>` and the PDFs downloaded from `https://arxiv.org/pdf/<id>` (%PDF verified).

## A. Admitted items

**MIRIX: Multi-Agent Memory System for LLM-Based Agents (arXiv:2507.07957, Yu Wang, Xi Chen, 2025).**
What it is: a modular memory system with six typed stores — Core, Episodic, Semantic, Procedural, Resource,
and Knowledge Vault — plus a multi-agent framework coordinating updates and retrieval; implementation at
https://github.com/Mirix-AI/MIRIX (3441 stars, Apache-2.0, pushed 2026-09-12, GitHub API verified).
Take: the six-store taxonomy is the closest published convergence to Databasise's own store split, and the
Knowledge Vault is the direct precedent for the SQL store: exact, durable facts live outside vector/graph.
Careful: MIRIX is multimodal and multi-agent with no reported routing-accuracy numbers, so it justifies the
vault's existence, not any routing mechanism.

**Zep: A Temporal Knowledge Graph Architecture for Agent Memory (arXiv:2501.13956, Rasmussen et al., 2025).**
What it is: a memory-layer service whose Graphiti engine (https://github.com/getzep/graphiti, ~30850 stars
page-embedded, Apache-2.0; https://github.com/getzep/zep, 4913 stars, pushed 2026-09-13) stores facts as
bi-temporal edges with validity intervals, outperforming MemGPT on the DMR benchmark.
Take: copy the bi-temporal edge semantics into relational columns — every facts row needs `valid_from`,
`valid_to` (or `invalidated_at`), not just a timestamp; contradiction handling falls out of interval overlap.
Careful: vendor benchmark (DMR) is primary only for "what the vendor reports"; Graphiti star count is
page-embedded, not API-verified, so treat it as approximate.

**SodaMem: Evidence-Grounded Temporal Graph Memory for LLM Agents (arXiv:2608.08055, Wan et al., 2026).**
What it is: typed FactEvents with mandatory provenance spans, separate mention/occurrence/validity times, and
SUPERSEDES/CONTRADICTS/UPDATES edges under hybrid lexical-dense indexing; 92.8% on LongMemEval-S at
~$0.00161/question via a planner-reader loop over citable evidence.
Take: this is the closest published analog of MelodyScribe's SQL facts table — adopt its triple-time model
(mention_time, occurrence_time, valid_from/valid_to) and its typed update edges as a `supersedes` column;
mandatory provenance spans match the brief's verbatim-quote rule exactly.
Careful: accuracy and cost figures are single-benchmark self-reports; the planner-reader loop assumes a
capable reader model, not a 2B extractor.

**TRACE: State-Aware Query Processing over Temporal Evidence Graphs (arXiv:2607.00339, Wang et al., 2026).**
What it is: a query framework modelling evolving conversations as hierarchical event/session/topic graphs with
validity annotations and typed temporal, causal, update, and contradiction relations, motivated by plans being
revised and later messages superseding earlier ones.
Take: recall from the SQL store must be validity-filtered (only currently-valid rows by default, with
time-travel available) — treat stale-but-similar evidence as the primary failure mode, matching the brief's
Proof concerns about dates.
Careful: a query-processing framework, not a write path; it says nothing about how rows get in.

**MOSAIC: Accurate and Efficient Long-Term Memory for LLM Agents (arXiv:2607.16211, Zhao et al., 2026).**
What it is: entity-typed graph storage with semantic classification plus conflict-aware writes, explicitly
designed to avoid expensive LLM-based classification and to stop silent contradiction accumulation.
Take: write-time routing and contradiction checks must be cheap classifiers/rules, not LLM calls — directly
supports a deterministic SQL-shaped gate on a 2B rig; entity typing at write time is the alias-merge point.
Careful: "substantially more accurate and efficient" is the authors' own framing; no independent replication traced.

**TokenMizer: Graph-Structured Session Memory (arXiv:2606.06337, Mishra, 2026).**
What it is: an open-source proxy keeping session state as a typed graph (14 node types, 7 edge types) under an
8-state lifecycle with bitemporal validity intervals and first-class decision-transition records.
Take: borrow the lifecycle, not the size — facts rows need states (current/superseded/invalidated) rather than
deletion, and transitions should record trigger+reason+evidence.
Careful: single-author open-source project (v0.3.1); maturity below Zep/Graphiti/Mem0.

**WorldDB: A Vector Graph-of-Worlds Memory Engine (arXiv:2604.18478, Ganesan, 2026).**
What it is: a memory engine with content-addressed immutable nodes (Merkle-style audit trail), recursive world
composition, and ontology-aware write-time reconciliation, positioned against Graphiti/Memento/HydraDB.
Take: two ideas transfer — content-addressed/idempotent op keys (already in the brief's design, now with
precedent) and reconciliation at write time against the existing store contents.
Careful: single-author paper citing competitor systems; treat comparative claims as unverified.

**Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory (arXiv:2504.19413, Chhikara et al., 2025).**
What it is: extraction-then-consolidation memory with explicit ADD/UPDATE/DELETE memory operations and a graph
variant, evaluated on LOCOMO; implementation at https://github.com/mem0ai/mem0 (65238 stars, Apache-2.0,
pushed 2026-09-11).
Take: the ADD/UPDATE/DELETE op vocabulary is the minimal write-time lifecycle the SQL store needs, and
Mem0's consolidation pass is precedent for the harness (not the model) merging aliases and resolving
contradictions after emission.
Careful: Mem0's extraction relies on capable models; its numbers do not transfer to a 2B extractor.

**TableRAG: Million-Token Table Understanding with Language Models (arXiv:2410.04739, Chen et al., 2024).**
What it is: a RAG framework for tables using query expansion with schema and cell retrieval, plus two new
million-token benchmarks built from Arcade and BIRD-SQL, showing precise retrieval beats whole-table prompting.
Take: tables/charts must be stored as schema + addressable cells, never flattened into vector chunks — the
strongest evidence for a SQL-shaped carve-out; schema+cell retrieval is the recall pattern.
Careful: benchmarks are author-constructed; gains are over whole-table prompting, not over a SQL store.

**TableRAG for Heterogeneous Document Reasoning (arXiv:2506.10380, Yu et al., 2025).**
What it is: an SQL-based framework unifying text and tables via query decomposition, text retrieval, SQL
programming and execution, and composed answer generation, with the HeteQA benchmark.
Take: the four-step loop (decompose → retrieve text → program+execute SQL → compose) is a directly reusable
recall-side harness pattern for mixed text/table content.
Careful: single-benchmark (HeteQA, author-built) evaluation; the SQL-generation step assumes capable models.

**BIRD: A Big Bench for Large-Scale Database Grounded Text-to-SQLs (arXiv:2305.03111, Li et al., 2023).**
What it is: 12,751 NL-SQL pairs over 95 databases (33.4 GB, 37 domains) stressing dirty values, external
knowledge, and SQL efficiency — the values-aware successor to Spider.
Take: BIRD's lesson is that SQL correctness is decided by database values and external knowledge, not schema
alone — so the harness must store cell values and aliases alongside schema, and any text-to-SQL eval for
MelodyScribe should be BIRD-style (values + efficiency), not Spider-style.
Careful: a benchmark, not a memory design; efficient-SQL metrics need adaptation to a facts-table setting.

**Spider (arXiv:1809.08887, Yu et al., 2018, EMNLP 2018).**
What it is: 10,181 questions and 5,693 complex SQL queries over 200 multi-table databases in 138 domains, with
a cross-domain split requiring generalization to unseen schemas.
Take: the canonical schema-generalization test — any SQL MelodyScribe emits (recall queries, typed inserts)
should generalize across table shapes the way Spider demands.
Careful: small clean databases; under-tests the dirty-values problem BIRD later exposed.

**ReAct-SQL: Iteration Without Elaboration (arXiv:2608.22651, Lu et al., 2026).**
What it is: a zero-shot ReAct text-to-SQL framework using a typed DSL of 15 relational operations with
compiled-SQL execution feedback instead of free-form SQL or multi-stage pipelines: 84.5% on corrected BIRD
mini-dev and 73.9% on EHR-SQL at up to 8x lower latency.
Take: the single most harness-relevant SQL finding — a small typed op DSL with execution feedback beats
elaborate pipelines, which maps exactly onto MelodyScribe's grammar-constrained ops + Proof validator design.
Careful: zero-shot results on two benchmarks from the authors; DSL design is doing heavy lifting that must be
replicated, not assumed.

**OmniSQL: Synthesizing High-quality Text-to-SQL Data at Scale (arXiv:2503.02240, Li et al., 2025).**
What it is: a scalable synthesis framework producing SynSQL-2.5M, a large diverse text-to-SQL training set.
Take: the recipe for the fine-tuning phase the brief defers — synthesize harness-shaped (NL → typed-op/SQL)
pairs at scale rather than collecting them.
Careful: data-synthesis paper; downstream gains depend on the base model and are reported by the authors.

**PaVeRL-SQL (arXiv:2509.07159, Hao et al., 2025).**
What it is: text-to-SQL via partial-match rewards plus verbal reinforcement learning, with a CoT RL pipeline
on the small OmniSQL-7B backbone for industry-scale databases with business logic.
Take: small (7B-class) backbones improve at SQL emission under execution/reward signals — precedent for using
Proof pass/fail and retrieval-hit as fine-tuning rewards later (lane 10's problem, but the signal exists).
Careful: 7B backbone, not 2B; business-logic setting differs from personal-facts memory.

**SQLCoder-7B-2 weights (https://huggingface.co/defog/sqlcoder-7b-2, HF API verified: 442 likes, 10547 downloads, CC-BY-SA-4.0).**
What it is: a widely used open 7B text-to-SQL model family.
Take: small-model SQL emission is a released artefact, not a hypothesis; a 2B MelodyScribe emitting
constrained SQL-shaped ops is well within demonstrated range.
Careful: a model, not a harness; no routing or validity story.

**prem-1B-SQL weights (https://huggingface.co/prem-research/prem-1B-SQL, HF API verified: 48 likes, 435 downloads, Apache-2.0, 2024-08-31).**
What it is: a 1B text-to-SQL model.
Take: directly qualifies the brief's spike-003 finding — a 1B model emits no ops under grammar decoding
*before fine-tuning*, but 1B SQL emission after fine-tuning exists as an artefact, so scale is not a hard bar.
Careful: low adoption (435 downloads); capability claims rest on the authors' release, not independent eval.

**State Compression in Two-Agent LLM Relays (arXiv:2607.18265, Sharma et al., 2026).**
What it is: a closed-world travel-planning study comparing hand-off formats; schema-constrained JSON
extraction preserves numeric/categorical constraints while narrative summarization and embedding pruning break them.
Take: the most direct evidence for the SQL-shaped rule — numbers, dates, and settings must travel as schema
(JSON/SQL rows), never as prose summaries; exhaustive enumeration over a fixed inventory is also a good
evaluation trick for facts recall.
Careful: a 50-instance closed-world study; effect size outside travel inventory is unmeasured.

**LINK-KG (arXiv:2510.26486, Meher et al., 2025).**
What it is: a modular KG-construction framework with a three-stage LLM coreference pipeline and a
type-specific prompt cache that tracks and resolves aliases across document chunks.
Take: the write-time entity-resolution pattern — a persistent per-type alias map (in SQL terms: an `aliases`
table consulted at insert) beats re-resolving from scratch each decode.
Careful: built for legal case documents; alias-tracking accuracy numbers are domain-specific.

**ScrapeGraphAI-100k (arXiv:2602.15189, Brach et al., 2026).**
What it is: 93,695 real schema-constrained extraction events over 18,000+ schemas with per-example
jsonschema conformance labels (opt-in telemetry, Q2–Q3 2025).
Take: grammar-constrained emission at scale is feasible and, crucially, measurable per-example — the same
conformance-label methodology should meter MelodyScribe's op emission against the facts schema.
Careful: web-extraction schemas, not memory schemas; semantic correctness explicitly out of scope.

**HippoRAG 2 (arXiv:2502.14802, Gutierrez et al., 2025) — refutes graph-everything.**
What it is: shows recent KG-augmented RAG variants drop basic factual memory performance considerably below
standard RAG, then proposes a framework beating RAG on factual, sense-making, and associative tasks.
Take: the refutation that justifies the SQL store's existence — forcing exact facts through graph retrieval
hurts; keep a non-graph exact path (SQL) for dates, numbers, and settings.
Careful: the "deterioration" claim covers specific prior systems; HippoRAG 2's own fix is graph-side, so this
bounds but does not eliminate graph retrieval.

**ReFind (arXiv:2608.12888, Li et al., 2026) — refutes structure-everything.**
What it is: an agent-controlled iterative keyword-search interface over raw unmodified chat logs that rivals
structured-memory pipelines across conversational-memory tasks.
Take: not everything needs structuring — route to SQL only the content SQL answers better (exact lookup,
aggregation, temporal filtering, contradiction checks); narrative/episodic content can stay raw+indexed.
Careful: conversational-memory tasks only; says nothing about tables, arithmetic, or cross-session facts.

## B. Refutations of brief claims

1. Against "typed stores for everything" (implicit in the harness thesis): HippoRAG 2 (arXiv:2502.14802)
measured KG-augmented retrieval dropping below plain RAG on basic factual tasks, and ReFind (arXiv:2608.12888)
matched structured-memory pipelines with raw-log lexical search. Together they refute any route-everything-
to-typed-stores reading: the harness must be selective, and selectivity is exactly what the SQL-shaped rule
below provides. Disposition: admit both as refuting items (capability `refutes` in inventory).
2. Qualification of spike 003 ("1B emits no ops"): prem-research/prem-1B-SQL (HF-verified 1B text-to-SQL
weights) shows 1B SQL emission exists post-fine-tuning — scale is not a hard bar, consistent with the brief's
own "fine-tuning, not scale, is the lever". This supports, rather than contradicts, the harness-first thesis.

## C. Unresolved ledger

- CodeS / DIN-SQL / DAIL-SQL small-model text-to-SQL papers: recalled ids did not verify (2402.14738 resolves
to a physics paper on the abs page); not located via search. Reason: abstain — no claim made.
- HyphaeDB (2606.28781), SuperLocalMemory V3 (2603.14588): abs opened; single-author architectural proposals
with no traced artefact. Reason: abstain — needs full read before any design claim.
- PEEK (2605.19932), schema-lineage extraction (2508.07179), IDP AutoOpt (2607.26075), SEAL (2512.04868),
Trusted-KE survey (2507.22935), When-Memory-Lies VLM staleness (2608.04574): abs opened, tangential to the
facts-schema question. Reason: abstain — out of scope, noted for other lanes (PEEK→lane 6, SEAL→lane 7,
When-Memory-Lies→lane 4/8).
- ~100 further arXiv ids title-screened only, not opened. Reason: abstain — ranked below cutoff, no claim made.
- defog/sqlcoder, premAI/*-guest, zepi-ai/graphiti GitHub lookups: API rate-limited; superseded by Hugging
Face API rows (sqlcoder-7b-2, prem-1B-SQL) and the fetched getzep/graphiti repo page. Reason: abstain lookups,
admit via alternate primary source.
- Semantic Scholar API: rate-limited (429) for the whole session; citation forward-chaining was replaced by
arXivrelated-search plus reference-list inspection. Consequence: forward-chain coverage is thinner than
planned; 2026 papers' citation contexts are under-explored.

## D. Security findings

No independent memory-poisoning literature was verified in this lane (that is lane 8's listed territory:
MINJA, PoisonedRAG, AgentPoison). Requirements falling out of admitted items, stated as harness requirements:
(1) facts rows must be append-only with supersede/invalidate transitions, never hard deletes, so a poisoning
or mistaken write is always auditable and reversible (SodaMem provenance spans, arXiv:2608.08055; TokenMizer
lifecycle, arXiv:2606.06337; WorldDB content-addressing, arXiv:2604.18478); (2) every row must carry a
provenance span (verbatim quote + offsets) so a suspect fact resolves to source text (SodaMem mandatory
provenance); (3) write-time reconciliation must run against existing store contents before insert
(WorldDB; MOSAIC conflict-aware writes, arXiv:2607.16211), which is also the natural admission-gate hook for
any lane-8 verifier.

## E. Harness implications

1. Keep the v0.1 SQL store as one generic `facts` table, but give every row `valid_from`/`valid_to` validity
columns plus a `supersedes` link and a provenance span, following the bi-temporal edge semantics of Zep/
Graphiti (2501.13956) and SodaMem's triple-time FactEvents (2608.08055).
2. Add an `aliases` table consulted at every insert for write-time entity/alias merging, following LINK-KG's
type-specific alias tracking (2510.26486) and MOSAIC's cheap write-time classification (2607.16211).
3. Decide SQL-shaped with a cheap deterministic gate, not an LLM call: route to SQL any op whose payload is a
date, number, setting, table cell, or chart datum, or whose recall needs exact lookup, aggregation, or
temporal filtering — because schema-constrained hand-off preserves numeric constraints that prose summaries
break (2607.18265), and tables must stay schema+cell addressable, never flattened (2410.04739).
4. Emit SQL-facing content as a small typed op DSL with execution feedback under Proof, not free-form SQL,
following ReAct-SQL's 15-op DSL at 84.5% BIRD mini-dev (2608.22651) and Mem0's ADD/UPDATE/DELETE op
vocabulary (2504.19413).
5. Recall from the SQL store must default to currently-valid rows with explicit time-travel, because
stale-but-similar evidence is the primary failure mode (TRACE, 2607.00339), and must support the
decompose → text-retrieve → SQL-execute → compose loop for mixed content (2506.10380).
6. Do not route narrative or episodic content to SQL: raw-log search rivals structured memory on conversational
tasks (ReFind, 2608.12888) and graph retrieval can hurt basic factual recall (HippoRAG 2, 2502.14802), so
selectivity — SQL only for what SQL answers better — is a correctness requirement, not an optimization.
7. Make facts rows append-only with supersede/invalidate transitions and mandatory provenance, so every fact
is auditable, reversible, and resolvable to source text (2608.08055; 2606.06337; 2604.18478).
8. Meter op emission with per-example schema-conformance labels à la ScrapeGraphAI-100k (2602.15189) and
evaluate emitted SQL BIRD-style (values + efficiency, 2305.03111) with Spider-style cross-schema splits
(1809.08887), since values and unseen schemas — not grammar alone — decide correctness.
9. Plan fine-tuning with synthesized harness-shaped pairs (OmniSQL/SynSQL-2.5M recipe, 2503.02240) and
execution/reward signals on a small backbone (PaVeRL-SQL, 2509.07159), because 1B-scale SQL emission is a
demonstrated artefact (prem-1B-SQL), not a scale impossibility.
