# Deep-research round 4: what the MelodyScribe harness should look like

Assembled 2026-09-13 by the owner's main session from ten Muse Spark 1.3 contributor lanes (`lanes/<n>/findings.md`, `merged/INVENTORY.tsv`, `merged/SUMMARY.md`). No finding below was written by the assembler; every claim carries the lane's source. The design that uses these findings is `.planning/notes/melodyscribe-harness-frameworks.md`.

Counts: 461 rows screened across lanes, 348 unique after dedup, 173 admitted, 1 refute row, 174 abstain (about 100 of them lane 9's declared title-screen-only rows), 162 admitted PDFs staged under `merged/papers/` (on disk, not committed). Malformed rows: 0.

## 1. Verdicts, one per lane question

**Lane 1, micro-harness architectures.** Every successful small-model agent wins by shrinking the model surface: scheduling, parsing, validation, retrieval, and joining live in deterministic code; the model owns selection plus argument content (ReAct executor 2210.03629; LLMCompiler planner and executor split 2312.04511; Toolformer loss gate 2302.04761). The per-section plan should be a dependency graph emitted in one pass and executed in parallel under per-store locks (2312.04511; ReWOO 2305.18323). Grammars enforce shape, never truth, so Proof stays mandatory (llama.cpp; Hammer 2410.04587). Tool schemas belong in a harness registry with per-section retrieval of tools and verified examples (TinyAgent ToolRAG 2409.00608; Gorilla 2305.15334). Abstention is trained with irrelevance negatives and masked store names (2410.04587). Vendor scoreboards (Octopus, xLAM, TinyAgent, Hammer, LFM2) are primary only for what the vendor reports.

**Lane 2, ingest routing to typed stores.** Store taxonomies diverge (nine different answers screened); what converges is three mechanisms: a closed op or paging interface between model and harness, harness-side resolution of references, and invalidation instead of deletion (refutation R3). Frame ingest as ADD, UPDATE, DELETE, NONE resolved against retrieved neighbours (Mem0 2504.19413); carry validity intervals and contradict by state change (Zep 2501.13956); decide code by parser, never by model judgement (HippoRAG precedent 2405.14831); ship a decay path symmetric to every ingest path (2305.10250; 2507.03724); measure routing as accuracy per serving cost (Total Recall 2608.11879; AgentMemBench 2608.00009; MERIT 2609.05441); train the router rather than prompt it (Mem-α 2509.25911; Memory-R1 2508.19828). No admitted paper studies code-versus-text or date-versus-prose routing, and no dataset labels per-fact store choice.

**Lane 3, recall-side harnesses.** Recall is a harness-owned budgeted loop capped at two cycles by default (IRCoT 2212.10509; ITER-RETGEN 2305.15294; DeepRAG 2502.01142), gated on predicted need (Self-RAG 2310.11511; FLARE 2305.06983; DRAGIN 2403.10081; Adaptive-RAG 2403.14403). Vector first with graph PPR and SQL as gated backoff is confirmed by HippoRAG's own HotpotQA underperformance (2405.14831). Fuse by structure only, never by flat score addition (HippoRAG 2 2502.14802; spike 010). Adopt LongMemEval's recall defaults and per-ability scoring with an explicit abstain outcome (2410.10813; LoCoMo 2402.17753). No small-model (3B or less) recall agent with LoCoMo, LongMemEval, or BRIGHT numbers was found.

**Lane 4, thinking modes.** Default every decode to non-thinking single-pass emission (NoThinking 2504.09858; 1.5B under and overthinking 2505.00127). Spend spare budget on parallel short reads with early-finish selection, never on a longer trace (Mirage 2506.04210; short-m@k 2505.17813; self-consistency 2203.11171). Expose thinking as a harness-owned per-section switch in the Qwen3 shape with a hard cap and forced stop (2505.09388; s1 2501.19393). Gate per sub-task, default off for implicit-pattern work (Mind Your Step 2410.21333; Underthinking 2501.18585; When More is Less 2502.07266). Reason-then-format with the grammar after a trigger (In-Writing 2601.07525; Speak Freely 2408.02442); ThinkBrake early stop is the only method shown to hold tool-call accuracy on a 4B hybrid (2510.00546). Latent and recurrent thinking stay out of v0.1 (Huginn probe 2507.02199).

**Lane 5, real-time co-processor.** No text API permits mutating an in-flight generation; Anthropic, OpenAI Responses, and Gemini expose read-only stream deltas and accept context only in the next request; MCP sampling is server-asks-client, not a tap. Injection is therefore at turn and tool-call boundaries only (refutations R1, R2). Tap the stream read-only with response id and offset provenance; prefetch from stream-prefix drafts with the harness owning the retrieve-now decision (FLARE 2305.06983; DRAGIN 2403.10081); small drafts and frontier disposes with Proof pre-filtering (Speculative RAG 2407.08223); compress and cite before injection (Search-o1 2501.05366); sidecar outputs out of band (OpenAI Realtime pattern); sleep-time precompute for predictable queries (2504.13171); always-on storing behind a break-even gate (Total Recall 2608.11879).

**Lane 6, caching and parallel workload.** Runtime prefix reuse stays but is not behaviour-transparent on a quantised small model: an enabled prefix cache changed agentic trajectories on 36.2 percent of episodes at 16-bit and 75.0 percent under quantisation (2609.04748), so gate reuse on Proof pass rate. KV composes only across byte-identical prefixes; anything else needs a recompute budget (CacheBlend 2405.16444). Chunk prefills against real-time deadlines (SARATHI 2308.16369; Sarathi-Serve 2403.02310; SLOWeave 2609.07883); schedule to goodput with shortest-remaining-work-first and aging (DistServe 2401.09670; FastServe 2305.05920); cached-automaton grammar masks remove the measured 9x CPU cost (XGrammar 2411.15100); namespace-keyed caches with bounded list values (Cache Saver 2025.findings-emnlp.1402; MeanCache 2403.02694); one write lock per store and SQLite at or above 3.51.3 because of the WAL reset race (sqlite.org); treat one process serving two jobs as multi-tenant batching (Punica 2310.18547).

**Lane 7, code graphs.** Keep the code graph a separate, parser-built store; every admitted system builds code structure deterministically and reserves the LLM for querying (RepoGraph 2410.14684; CodexGraph 2408.03910; GraphCoder 2406.07003; Potpie; GitNexus; SCIP). Converge on files, symbols, and CONTAINS, CALLS or USES, INHERITS, IMPORTS edges with line-span anchors. Never show the whole graph: ranked signature map as prefix (Aider repo map) plus per-query ego-graphs. Route the small model through intent-plus-translator, not raw Cypher (2408.03910). Blanket "graph beats embeddings on code" is not established (CodeRAG-Bench 2406.14497); the supported claim is mechanism-specific structure-aware retrieval beats similarity-only baselines. Unconditional multi-store recall is refuted (Repoformer 2403.10059). Build on tree-sitter with an LSP or SCIP resolver; re-index incrementally (CocoIndex).

**Lane 8, learning graphs and procedural memory.** The learning graph is a v0.1 write-only ledger and a v0.2 or later retrievable store: query-only injection succeeds 98.2 percent against ungated memory (MINJA 2503.03704) and embedding-retrievable poison wins under 0.1 percent presence (AgentPoison 2407.12784). Admission is execution-shaped, never judge opinion (Voyager 2305.16291; SkillWeaver 2504.07079; LATM 2305.17126). Induce offline (AWM 2409.07429), reflect as a scheduled job (2304.03442; 2310.08560), organise procedures as a skill graph keyed by situation (WebXSkill 2604.13318), gate evolution above appends (A-MEM 2502.12110; InjecMEM 2608.23471). Minimum schema: five node types, six edge types, and an admission envelope; see the lane file.

**Lane 9, structured facts store.** Keep one generic `facts` table in v0.1 but give every row `valid_from`, `valid_to`, `supersedes`, and a provenance span (Zep 2501.13956; SodaMem 2608.08055); add an `aliases` table consulted at insert (LINK-KG 2510.26486; MOSAIC 2607.16211). Decide SQL-shaped with a deterministic gate: dates, numbers, settings, table cells, chart data, or anything whose recall needs exact lookup, aggregation, or temporal filtering (2607.18265; TableRAG 2410.04739). Emit SQL-facing content as a small typed op DSL with execution feedback, not free-form SQL (ReAct-SQL 2608.22651). Recall defaults to currently valid rows with time travel (TRACE 2607.00339). Do not route narrative content to SQL (ReFind 2608.12888; HippoRAG 2 2502.14802). 1B-scale SQL emission exists post fine-tune (prem-1B-SQL), consistent with "fine-tuning, not scale".

**Lane 10, evaluation and rewards.** The literature never ranks harnesses analytically before training; the supported procedure is fix the model, ablate the harness, report per-capability deltas with consistency statistics (refutation R4). Score recall on LongMemEval's five abilities (2410.10813); report Proof reliability as pass^k with store-state matching (tau-bench 2406.12045); grade ops by AST match plus irrelevance split (BFCL PMLR v267); milestones and minefields for partial credit (ToolSandbox 2408.04682); stage rewards so grammar-valid emission and invocation are rewarded before correctness (R1-Searcher 2503.05592), mask non-model tokens (Search-R1 2503.09516), keep Proof rule-based (DeepSeek-R1 2501.12948), treat memory-write choice as an RL action (Memory-R1 2508.19828), report serving as capacity under a tail-latency SLO (Sarathi-Serve 2403.02310), and keep a Reflexion loop beside the RL track (2303.11366).

## 2. Refutations of claims in or behind the brief

| # | Claim | Refuted by | Lane |
|---|---|---|---|
| 1 | A sidecar can inject into the frontier context mid-stream | Anthropic, OpenAI, Gemini streaming and tool-use docs; MCP sampling spec | 5 |
| 2 | MCP sampling gives a tap into frontier generation | MCP sampling spec 2025-06-18 | 5 |
| 3 | Always-on storing from the stream is self-evidently worth it | Total Recall 2608.11879 | 5 |
| 4 | Recall pulls from all stores every cycle | Repoformer 2403.10059; FLARE, DeepRAG, ITER-RETGEN | 3, 7 |
| 5 | More retrieval rounds monotonically help | ITER-RETGEN 2305.15294; FLARE; DeepRAG | 3 |
| 6 | Graph retrieval dominates vector, so graph first | HippoRAG 2405.14831 (HotpotQA) | 3 |
| 7 | Naive score fusion across stores is safe | HippoRAG 2 2502.14802; spike 010 | 3 |
| 8 | Graph retrieval beats embeddings on code, blanket | CodeRAG-Bench 2406.14497 | 7 |
| 9 | Explicit thinking is necessary; more thinking is better; latent thinking can replace traces; think-on for all sub-tasks | NoThinking 2504.09858; Mirage 2506.04210; Huginn probe 2507.02199; Mind Your Step 2410.21333 and Speak Freely 2408.02442 | 4 |
| 10 | Runtime prefix reuse is transparent | Cache divergence 2609.04748 | 6 |
| 11 | KV of reused chunks composes freely | CacheBlend 2405.16444 | 6 |
| 12 | SQLite WAL plus one writer is bulletproof | sqlite.org WAL reset race, fixed 3.51.3 | 6 |
| 13 | A retrievable learning graph in v0.1 is a free choice | MINJA 2503.03704; AgentPoison 2407.12784 | 8 |
| 14 | A-MEM backward evolution can be copied wholesale | A-MEM 2502.12110; InjecMEM 2608.23471 | 8 |
| 15 | Admission can be an LLM judge call | Voyager, SkillWeaver, LATM | 8 |
| 16 | One store suffices for facts and procedures | DKT 1506.05908; WebXSkill 2604.13318; Hindsight 2512.12818 | 8 |
| 17 | More stores are self-evidently better | Total Recall; AgentMemBench 2608.00009; MERIT 2609.05441 | 2 |
| 18 | One store taxonomy has converged | nine divergent taxonomies screened | 2 |
| 19 | Route everything to typed stores | HippoRAG 2 2502.14802; ReFind 2608.12888 | 9 |
| 20 | Embedder choice settles recall quality on hard queries | BRIGHT 2407.12883 | 10 |
| 21 | Weight updates are the only learning lever | Reflexion 2303.11366 | 10 |
| 22 | Outcome-only rewards transfer to the emits-nothing regime | R1-Searcher 2503.05592 | 10 |
| 23 | Harnesses can be compared in theory before training | no analytic ranking in any admitted source | 10 |

Seed-list corrections: MemBench as a memory-harness benchmark could not be verified by lane 2 (closest artefact AgentMemBench 2608.00009), while lane 10 admitted a different MemBench (2506.21605, ACL 2025 Findings); "CodeGraph" 2408.13863 is graph-reasoning-via-code, not a repository code graph; recalled ids for TinyAgent, APIGen, NexusRaven, ExpeL, AWM, and AKT resolved to unrelated papers and were corrected in the inventories.

## 3. Security requirements, consolidated

1. Every ingest path is untrusted input: Proof validates quotes against source text and every op carries provenance (turn, speaker, document, response id, stream offset); unattributed ops are rejected (lanes 2, 5).
2. Multi-record writes (evolve, supersede, re-link, invalidate) require a strictly higher gate than appends; invalidation over overwrite (lanes 2, 8).
3. Induced content (rules, reflections, Folios, lessons) is inference, never verbatim evidence; it lives in a separate tier with a logged admission score and is rendered as data, never instructions (lanes 2, 8).
4. Learning-graph retrieval filters by admission status and trust tier before similarity ranking; decay and ranking are not defenses (lane 8).
5. Grammar is not validation; Proof follows every constrained decode (lanes 1, 4).
6. No execute-to-observe against live stores at ingest; abstention gate before Proof; few-shot examples come only from the harness's own verified store (lane 1).
7. Thinking traces are untrusted input, never persisted verbatim, capped by the harness independent of model cooperation; Proof accepts traceless decodes as normal (lane 4).
8. Sidecar outputs travel out of band and are labelled harness-generated; recall payloads assert only Proof-passed ops; MCP sampling requests are human-approval-gated (lane 5).
9. Caches are namespace-keyed (session, store version, model hash); prefix-hit timing is an observable channel; SQLite at or above 3.51.3 with checkpoints off the real-time path; every reuse optimisation ships only with a measured non-regression on Proof (lane 6).
10. Code-graph query surface is read-only and parameterised; indexed repository content is untrusted; build-monitoring extractors run sandboxed; grammars pinned by hash; serve the graph version matching the checked-out commit, fail closed on staleness (lane 7).
11. Facts rows are append-only with supersede and invalidate transitions and mandatory provenance; write-time reconciliation against existing contents (lane 9).
12. Proof as reward must be game-resistant with hack probes; harness evals include an adversarial write split; abstention, irrelevance detection, and policy-violation rates are reported with every recall number; simulator-graded evals are human spot-checked (lane 10).

## 4. Unresolved ledger, cross-lane

- Small-model (1B to 3B) numbers are missing for typed-store routing, retrieve-or-not gating, graph-query authorship, procedure induction, and recall agents on LoCoMo, LongMemEval, or BRIGHT (lanes 2, 3, 7, 8).
- MiniCPM5-2B think-on versus think-off tool-call accuracy is unmeasured; thinking-bytes interaction with grammar-constrained emission at 2B is unmeasured (lane 4).
- One model process serving embedding and generation on one 16 GB card has no published capacity-under-SLO figure (lanes 6, 10).
- No public dataset labels per-fact store choice; no dedicated cache-invalidation-on-store-change study; semantic-cache hit rates are reported only on vendor workloads (lanes 2, 6).
- Persisted-KV tiers (LMCache, Mooncake-style) must be re-tested against recompute each release (lane 6).
- Several 2026 single-version preprints (SLOWeave, cache divergence, InjecMEM, WebXSkill, SodaMem, MOSAIC, ReAct-SQL, AgentMemBench, MERIT) are admitted for their mechanism with a replication obligation.
- MiniCPM4-MCP and MiniCPM4-Survey have no standalone paper or repo; Gemma 3n and SmolLM3 harness claims are vendor-only (lane 1).
- Rate limits on Semantic Scholar and the arXiv listing API during several lanes reduced forward and backward citation chaining (lanes 1, 9).

## 5. Method

Ten lanes, each one Muse Spark 1.3 contributor session through OpenCode with `BRIEF.md` attached and `LANE-PROMPT.md` plus its `lane.txt` as the prompt, four in parallel (`run-lanes.sh`), nudged on the captured session id when a lane stopped early. Each lane wrote `findings.md` (admitted items, refutations, unresolved ledger, security findings, harness implications), `inventory.tsv` (16 columns), `method.md`, and `papers/`. `integrate.py` deduplicated by arXiv id or repo URL and staged PDFs. No Muse integrator ran; the assembler read the ten findings files and wrote this report and the design note.

| Lane | Subject | Rows | Admitted |
|---|---|---|---|
| 1 | Micro-harness architectures for small models | 41 | 30 |
| 2 | Ingest-side routing to typed stores | 44 | 27 |
| 3 | Recall-side harnesses | 28 | 24 |
| 4 | Thinking modes for small models | 38 | 27 |
| 5 | Real-time co-processor next to a frontier model | 36 | 26 |
| 6 | Caching and parallel workload | 39 | 27 |
| 7 | Code graphs as a store | 23 | 18 |
| 8 | Learning graphs and procedural memory | 30 | 21 |
| 9 | Structured facts store | 144 | 26 |
| 10 | Evaluating harnesses and harness signals as rewards | 38 | 19 |

Lane 9's 118 abstains include about 100 title-screen-only rows it declared in `method.md`. Sources per lane: arXiv abs pages and the export API, Semantic Scholar where not rate-limited, the GitHub API, Hugging Face API, vendor API documentation (lane 5), sqlite.org (lane 6), PMLR (BFCL). Wall time about 65 minutes for all lanes.
