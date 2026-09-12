# Lane 5 findings: Documents to structured tables and SQL with LLMs

Scope: schema induction and LLM-driven ETL (Evaporate, DocETL, LOTUS, Palimpzest, ZenDB,
TAG, semantic operators), text-to-SQL memory, and routers choosing between SQL, vector and
graph at query time (HybridRAG, Adaptive-RAG, RouterRetriever, LlamaIndex routers, query
routing). All arXiv ids below were verified against the arXiv API record (title + date +
authors); all PDFs were downloaded from `https://arxiv.org/pdf/<id>` and `%PDF`-verified.
All star/license/push figures were read from the GitHub API on 2026-09-12.

## (a) Admitted items

### A. Declarative semantic-operator stacks (the direct template for capability 2)

**Evaporate (2304.09433, Arora et al., 2023).** Synthesizes code, not labels: an LLM writes
candidate extraction functions per attribute, weak supervision aggregates them, and the
result is a structured view over heterogeneous lakes with no training data. Take: this is
the cheapest proven pattern for MelodyScribe's file-to-SQL step — generate several small
extractors per paragraph and vote, rather than trusting one constrained emission. Careful:
quality rests on function diversity and aggregation, not on the single pass; the repo
(HazyResearch/evaporate, 498 stars, no declared license, last push 2024-03-26) is a paper
artefact, not a maintained engine.

**ZenDB (2405.04674, Lin et al., 2024).** Discovers tables from document collections via
templates, then answers analytics queries with explicit cost/accuracy trade-offs per
operator. Take: the template-first idea maps directly onto MelodyScribe's Score directives
("file this section to the graph", "rewrite as propositions"): learn one template per
section type, then apply cheaply. Careful: no official code repository could be located
(see unresolved ledger), so the cost model is paper-only.

**LOTUS (2407.11418, Patel et al., 2024).** Defines semantic operators (sem-filter, join,
group-by, top-k over natural-language criteria) with a gold-algorithm semantics and an
optimizer giving accuracy guarantees while cutting cost up to 1000x on some operators.
Take: this is the formalism MelodyScribe's op-list language wants — a small fixed operator
set with stated semantics, so a 2B model emits operators, not free text. Code:
lotus-data/lotus (1672 stars, Apache-2.0, pushed 2026-07-03), actively maintained. Careful:
guarantees are relative to the gold algorithm, not to ground truth; a bad gold program is
still bad.

**Palimpzest (2405.14696, Liu et al., 2024).** Declarative AI pipelines ("convert this PDF
collection to this schema") compiled by a cost/quality optimizer. Take: its optimizer is
the missing piece between MelodyScribe's op list and execution — identical logical ops
should run on the small model, a bigger model, or code depending on budget. Code:
mitdbg/palimpzest (238 stars, MIT, pushed 2026-08-25). Careful: optimization needs
calibrated cost/quality statistics per operator that MelodyScribe does not yet collect.

**DocETL (2410.12189, Shankar et al., 2024).** YAML document pipelines where an agent
rewrites operations (split, gather, map) and each op carries validation directives that
trigger retries. Take: the per-op `validate:` pattern is directly reusable as the grammar
around MelodyScribe's filing ops — emit op plus a checkable assertion, re-run on failure.
Code: ucbepic/docetl (4087 stars, MIT, pushed 2026-09-05), the most-adopted stack in this
lane. Careful: validation is LLM-judged, so correlated errors (cf. brief's Correlated
Errors seed) can pass bad extractions; see refutations.

**PalimpChat (2502.03368, Liu et al., 2025).** Compiles interactive natural-language
requests into Palimpzest pipelines so non-programmers drive declarative AI analytics.
Take: validates the "one human-authored skill file" direction of capability 5 — a single
NL surface over a fixed operator set works for analytics users. Careful: no released code
found; paper-only, and interactive latency/cost figures are not independently reproduced.

**BlendSQL (2402.17882, Glenn et al., 2024).** A SQLite dialect in which LLM calls are
"ingredients" evaluated inside relational algebra, so hybrid questions run as one query
mixing exact SQL with fuzzy LLM predicates. Take: the single strongest precedent for
MelodyScribe capability 2 — structured facts stay in SQLite while the model fills only
the cells SQL cannot compute, keeping everything auditable as rows. Code:
parkervg/blendsql (169 stars, Apache-2.0, pushed 2026-08-28). Careful: small project,
single-maintainer risk; SQLite-only execution.

### B. Routers across SQL, vector and graph at query time

**HybridRAG (2408.04948, Sarmah et al., 2024).** Runs KG-triple retrieval and vector RAG
side by side and fuses them for extraction over financial documents. Take: evidence that
graph + vector fusion beats either alone on entity-heavy extraction — the read-side
justification for MelodyScribe owning all three stores. Careful: fusion is heuristic
concatenation, not learned routing; no released code found.

**Adaptive-RAG (2403.14403, Jeong et al., NAACL 2024).** Trains a small classifier to
predict query complexity and routes to no-retrieval, single-step, or iterative RAG. Take:
the proven cost saver MelodyScribe should copy — most queries need no retrieval at all,
and a tiny router (not the 2B worker) can decide. Code: starsuzi/Adaptive-RAG (410 stars,
Apache-2.0). Careful: complexity labels are auto-collected from model outcomes, so the
router inherits the teacher's blind spots; see refutations.

**RouterRetriever (2409.02685, Lee et al., 2024).** Routes each query over a mixture of
specialist embedding models and beats every single embedder. Take: qualifies capability
1's single-embedding-pass assumption — if MelodyScribe's own hidden-state embeddings lag
on some section types, a tiny per-section embedder router is a legitimate fallback. Code:
amy-hyunji/RouterRetriever (14 stars, no declared license). Careful: pilot-scale repo,
gated models, no production hardening.

**RouteLLM (2406.18665, Ong et al., 2024).** Learns a router from human preference data
that sends easy queries to cheap/weak models and hard ones to the frontier, holding
quality while cutting cost up to an order of magnitude. Take: the serving-side economics
for capability 5 — MelodyScribe's 2B worker handles routine filing, the frontier skill is
invoked only when the router says so. Code: lm-sys/RouteLLM (5477 stars, Apache-2.0), the
reference routing harness. Careful: routers trained on chat preferences transfer
imperfectly to extraction/routing workloads; recalibration on MelodyScribe's own outcomes
is required.

**LlamaIndex routers (code only, no paper).** LlamaIndex (run-llama/llama_index, 52129
stars, MIT, pushed 2026-09-11) ships router query engines that select among vector, SQL,
KG and summarizer tools per query. Take: the most production-tested router-over-stores
implementation to study or wrap. Careful: router behavior is documented in docs/blogs
only — secondary source — so any performance claim about it is abstained, not admitted.

**Vanna (code only, no paper).** Vanna (vanna-ai/vanna, 23815 stars, MIT, pushed
2026-02-02) is a RAG-based chat-with-SQL framework that retrieves schema, docs and prior
queries before generating SQL. Take: its "train on your schema + question-SQL pairs"
loop is the practical text-to-SQL memory MelodyScribe's SQL store needs. Careful: no
peer-reviewed evaluation; accuracy claims are vendor/community only.

### C. Table understanding and text-to-SQL machinery

**TableRAG million-token (2410.04739, Chen et al., 2024).** Retrieves schema elements and
cells so LMs query million-token tables without stuffing them in context. Take: the
retrieval pattern for MelodyScribe's SQL store at scale — never prompt the whole table,
retrieve schema then cells. Careful: no official code located; several unofficial
reproductions exist (e.g. YuhangWuAI/tablerag, GPL-3.0 — license-incompatible with
Apache-2.0 plans, avoid vendoring).

**TableRAG heterogeneous-doc (2506.10380, Yu et al., 2025).** Joint retrieval over text
and tables inside mixed documents. Take: closest retrieval-side match to MelodyScribe's
Score format, where prose and structured sections interleave. Code: yxh-y/TableRAG (143
stars, no declared license). Careful: small repo, thin evaluation beyond its own suite.

**ReAcTable (2310.00815, Zhang et al., 2023).** A ReAct agent whose only tools are SQL
executors, voting over intermediate tables. Take: shows execution-grounded table QA works
with mid-size models because SQL errors are self-correcting at runtime. Careful: no
released code found; iteration counts make it token-hungry without caching.

**Chain-of-Table (2401.04398, Wang et al., 2024).** Reasoning as an explicit chain of
table transformations (select/filter/group), each step a valid table. Take: a
grammar-constrainable trace format — every step type-checks against the schema, which is
exactly how MelodyScribe should constrain op emission. Careful: paper-only artefact for
our purposes; operator set is fixed and small.

**StructGPT (2305.09645, Jiang et al., 2023).** One LLM loop reading linearised tables,
KGs and DBs through defined interfaces. Take: early proof that a single model can mediate
all three store types behind interfaces — the conceptual ancestor of MelodyScribe's fixed
REST/MCP surface. Careful: predates strong tool-calling models; interface design is dated.

**Binder (2210.02875, Cheng et al., 2022).** Binds LM generations to symbolic executors
(SQL/Python) so outputs are programs, not answers. Take: the "never emit a fact, emit a
query" discipline that keeps MelodyScribe's SQL rows auditable. Careful: from the
pre-instruction-tuning era; absolute numbers are stale, only the pattern transfers.

**BIRD (2305.03111, Li et al., 2023).** Large-scale text-to-SQL benchmark on big, dirty,
real databases with an efficiency score alongside accuracy. Take: adopt BIRD (plus its
efficiency metric) as the acceptance test for any MelodyScribe SQL emission — it punishes
exactly the failure modes clean benchmarks hide. Careful: leaderboard-chasing has
overfit some systems to its quirks; use the dev split, not test, for iteration.

**DIN-SQL (2304.11015, Pourreza & Rafiei, 2023).** Decomposes text-to-SQL into
schema-linking, classification, generation and self-correction prompts. Take: the
decomposition is a ready-made op list for capability 2's SQL branch — four small,
verifiable steps instead of one heroic generation. Careful: prompt-heavy and
frontier-tuned; per-step accuracy with a 2B model is unmeasured (a gap, see §Gaps in
method notes).

**CHESS (2405.16755, Talaei et al., 2024).** Multi-stage harness (retrieval, column
filtering, synthesis, verification) that led BIRD-style tasks at release. Take: its
column-filter-then-synthesize ordering is the cheapest reliable recipe for schema-grounded
SQL from long documents. Code: ShayanTalaei/CHESS (281 stars, Apache-2.0, pushed
2025-05-26). Careful: multi-stage LLM calls multiply cost; needs the Adaptive-RAG-style
gate in front.

**Chain-of-Query (2508.15809, Sui et al., 2025).** Multi-agent collaboration that writes
and chains SQL sub-queries for table understanding. Take: validates splitting SQL
emission across cooperating sub-agents — relevant if MelodyScribe delegates (capability
2's fourth outlet). Careful: coordination overhead unmeasured outside its benchmark.

### D. 2025–2026 consolidation: benchmarks, compilation, NL front-ends

**SemBench (2511.01716, Lao et al., 2025).** Head-to-head benchmark for semantic query
engines of the Palimpzest/LOTUS/DocETL class. Take: the fairest available yardstick for
comparing MelodyScribe's filing path against the declarative stacks; use its task set
before inventing our own. Careful: very recent (Nov 2025); engine coverage vs. version
skew needs checking before citing numbers.

**Compilation engine (2608.06677, Dong & Wang, 2026).** Compiles semantic-operator
pipelines to optimized plans rather than interpreting op-by-op. Take: the performance
argument for fixing MelodyScribe's op vocabulary early — a compilable op list can be
optimized wholesale (predicate pushdown, batching) where free-text plans cannot. Careful:
preprint, no code, single small author team; treat as direction, not dependency.

**NL-to-semantic-pipelines (2606.04641, Dong et al., 2026).** Compiles natural-language
questions directly into semantic-operator pipelines. Take: the missing compiler between
capability 5's human-authored skill and capability 2's op list — NL directives in, typed
pipeline out. Careful: same caveats as above (preprint, no code).

**Larch (2606.07923, Zhao et al., 2026).** Learned cost/quality optimization for semantic
predicates. Take: if MelodyScribe logs per-op outcomes, Larch-style learned models can
replace hand-tuned routing thresholds. Careful: preprint, no code; needs exactly the
telemetry we do not yet collect.

**RUBICON (2604.21413, Wenz et al., 2026).** Agentic preparation of messy enterprise data
before querying. Take: the only near-miss on the thesis found in this lane — it couples
ingestion/structuring with downstream querying, though without MelodyScribe's single-pass
embedding, KV reuse, or skill sandboxing. Careful: preprint, no code.

**Multi-objective rewrites (2512.02289, Wei et al., 2025).** Agent-driven pipeline
rewrites trading cost, latency and quality (DocETL lineage authors). Take: the rewrite
objective MelodyScribe's background revise pass (capability 4) should optimize — not
quality alone. Careful: preprint, no code.

**Type-rules (2509.20208, Glenn et al., 2025).** Infers type constraints for LLM-valued
functions inside declarative programs (BlendSQL lineage). Take: type inference over op
signatures is how MelodyScribe can statically check a 2B model's op list before
executing it. Careful: preprint, no code.

**Small-LMs-for-large-DBs (2606.31808, Glenn & Samuel, 2026).** Argues small open-weight
LMs suffice for large-database QA when paired with execution and verification. Take:
direct supporting evidence for the motivating hypothesis, from the BlendSQL team.
Careful: short paper, author-overlapping with BlendSQL, vendor-adjacent framing — treat
as one vote, not proof.

### E. Small-model text-to-SQL and schema memory (hypothesis-relevant)

**SQuaD-SQL (2607.08161, Wu et al., 2026).** Distils frontier text-to-SQL into small LMs
via LLM-guided distillation. Take: the most actionable distillation recipe for getting
MelodyScribe's 2B worker to emit valid SQL. Careful: preprint, no released adapter found.

**FINER-SQL (2605.03465, Hoang et al., 2026).** Training recipe boosting small-LM
text-to-SQL. Take: second independent vote that 1–3B models reach usable SQL accuracy
with the right recipe. Careful: preprint, no released artefact found.

**Schema-First Retrieval (2606.28387, Agrawal & Indukuri, 2026).** Embeds the data
catalog so NL analytics queries route to the right tables first. Take: MelodyScribe
should embed its own SQLite schema/catalog as a first-class retrieval target at query
time. Careful: preprint, no code.

**Listwise-memory text-to-SQL (2609.00834, Jeong et al., 2026).** Replaces fine-tuning
with retrieved-experience selection for text-to-SQL adaptation. Take: supports the Folio
intuition — a memory of past successes can substitute for weight updates. Careful:
preprint, no code.

**Multi-turn text-to-SQL memory (2605.26394, Tummalapenta & Addanki, 2026).** Benchmarks
memory architectures for conversational text-to-SQL agents. Take: use its memory taxonomy
when designing MelodyScribe's cross-paragraph state. Careful: benchmark-only, small
author team, no code.

**LoRA trade-offs (2607.25583, Rathor & Azzam, 2026).** Controlled study of LoRA rank,
target modules and quantization for text-to-SQL on small models. Take: directly answers
the lane-7-adjacent question of what fits on one 16 GB GPU; read before any fine-tune.
Careful: preprint, single-benchmark scope.

### F. Evaluation methodology for mixed modalities

**T2-RAGBench (2506.12071, Strich et al., 2025).** Benchmark for RAG over mixed
text-and-table corpora. Take: adopt for the text-vs-table ablation of MelodyScribe's
stores. Careful: recent, community uptake still thin.

**mmRAG (2505.11180, Xu et al., 2025).** Modular benchmark over text, tables and KGs in
one setup. Take: the closest existing harness to "compare modalities on one corpus"
(lane 10's question) — run MelodyScribe's three stores through it. Careful: modularity
means results depend on configuration; report configs, not just scores.

**Ontology-RAG-from-RDBs (2506.01232, Fathallah et al., 2025).** Generates ontologies
from relational DBs for RAG — the reverse direction (SQL → graph schema). Take:
MelodyScribe's revise pass (capability 4) could induce graph ontology from accumulated
SQL rows exactly this way. Careful: ontology quality is weakly evaluated; human review
still required.

**Agentic Context Cracking (2608.31082, Hajidehi et al., 2026).** An agent structures
unstructured data once, adaptively, so later queries run cheaply. Take: the index-time
vs query-time cost argument for MelodyScribe's one-pass filing — pay once at ingest,
query cheaply forever. Careful: preprint, no code, single-system evaluation.

**VikingRAG (2609.11390, Gao et al., 2026).** Token-efficient RAG over structured
documents. Take: candidate efficiency techniques for MelodyScribe's query path over
sectioned Scores. Careful: days-old preprint (Sep 2026), no code, no independent
reproduction.

## (b) Refutations and qualifications (each traced to a primary source)

1. **"Retrieval always helps" is false — and therefore MelodyScribe must gate it.**
Adaptive-RAG (2403.14403) trains its router with an explicit no-retrieval option and
finds a large share of queries are best answered without any retrieval. Any MelodyScribe
design that always retrieves-then-reads pays cost and adds noise on exactly those
queries. Requirement: a query gate (even heuristic) in front of the retrieval path.
2. **"One embedding model suffices" is false at the margin.** RouterRetriever
(2409.02685) shows a routed mixture of specialist embedders beats every single embedder
tested. This qualifies capability 1: a single hidden-state embedding pass is a cost
choice, not a quality optimum, and section types where it lags should be measurable via
a SemBench/mmRAG-style ablation.
3. **"LLM-extracted structure is trustworthy by construction" is false.** The LOTUS
program (2407.11418) exists precisely because raw LLM operators are unreliable: every
operator needs a gold algorithm plus an optimizer with accuracy guarantees, and DocETL
(2410.12189) wraps every op in validation directives with retries. A MelodyScribe op
list executed without per-op validation repeats the failure mode both systems were built
to fix. Requirement: validate-then-file, with the validator cheaper than the generator.
4. **"No project combines these pieces" survives, but narrowed.** RUBICON (2604.21413)
couples agentic structuring with querying, and PalimpChat (2502.03368) couples NL
interaction with declarative analytics — but neither does single-pass embedding,
KV-cache reuse, background revision, or sandboxed self-written skills. The combination
claim holds; the ETL-plus-query half alone does not.

## (c) Unresolved ledger

- **TAG (Table-Augmented Generation):** recalled from prior knowledge; arXiv
title/abstract search did not confirm an id within budget. Unverifiable — do not cite.
- **DATER:** recalled table-QA decomposition; title search returned only an unrelated
namesake (data architectures). Unverifiable — do not cite.
- **SemCEB:** seen once in an arXiv result listing (semantic cardinality-estimation
benchmark); id and abs page not verified. Unverifiable within budget.
- **CSR-RAG (enterprise text-to-SQL retrieval):** recalled title mismatched — candidate
id 2602.11443 verified via API as a different paper (filtered ANN search). Sources
conflict due to faulty recall; dropped, not cited.
- **ZenDB code:** no official repository located (GitHub search returned unrelated
namesakes only). Paper admitted; code claims abstained.
- **LlamaIndex router performance:** repo verified (52129 stars, MIT); routing
effectiveness claims rest on docs/blogs (secondary sources). Abstained as evidence.
- **Vanna accuracy:** repo verified (23815 stars, MIT); no peer-reviewed evaluation
found. Accuracy claims abstained; architecture pattern admitted.

## (d) Security findings

None in lane scope. Persistent-memory/skill poisoning is lane 6's subject. One
lane-5-adjacent note, stated without security-requirement force: DocETL-style
LLM-judged validators (2410.12189) and Adaptive-RAG auto-collected router labels
(2403.14403) both create self-grading loops where a compromised or systematically wrong
model approves its own outputs — the filing gate should use a cheaper independent check
(ReAcTable-style execution feedback, 2310.00815, or schema type-checks as in 2509.20208)
rather than the generator judging itself.
