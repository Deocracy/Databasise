---
title: MelodyScribe harness frameworks — pre-alpha design from deep research 4
date: 2026-09-13
context: /gsd-explore session; ten Muse Spark 1.3 lanes in reference/micro-harnesses/deep-research-4/ (348 unique items, 173 admitted); assembled by the main session. Design the harness first, fine-tune the model to it.
status: pre-alpha design, owner review pending; no experiment run in this round
---

# MelodyScribe harness frameworks

Purpose: list the candidate harness frameworks that could run MelodyScribe on Databasise 2.0, check each against the owner's requirements, and say which holds up in theory. Pre-alpha: the claim is that every requirement fits together in one design, not that the design is optimal. Every mechanism cites a lane finding by arXiv id or URL; lane files hold the full paragraphs (`reference/micro-harnesses/deep-research-4/lanes/<n>/findings.md`).

## 1. Requirements (owner brief, 2026-09-13)

| Id | Requirement |
|---|---|
| R1 | Ingest routing: as the model reads text it emits tool calls naming the store for each piece; the harness executes them under Proof |
| R2 | Five store targets: vector; knowledge graph (LightRAG-like); code graph (code only); learning graph (may not exist in v0.1); SQL (dates, birthdays, charts, tables, numbers). Plus Folios (model-written, sandboxed) |
| R3 | Recall pulls from all stores, possibly in several cycles, and assembles a payload for the frontier model |
| R4 | Thinking: type unknown; must be switchable and priced |
| R5 | Caching and parallel workload are of the utmost importance |
| R6 | Real-time co-processor: store what the frontier model says as it says it; add information to the frontier model because the small model is faster; both directions |
| R7 | Databasise 2.0 fit, with updates allowed: model is a machine client; loops are `fixpoint` nodes under executor budget; SQL is a §15 Branch 2 blob artifact; Folios are `self_storage`; no modality-specific seam tool (§18.5) |
| R8 | Pre-alpha: all components fit together; optimisation later |

## 2. Corrections to the requirements that the research forces

These are refutations from primary sources. The design below takes them as given.

1. **Mid-stream interruption of a frontier model does not exist.** Anthropic, OpenAI Responses, and Gemini expose the stream as read-only deltas and accept new context only in the next request; Anthropic context editing applies per request before the model runs; MCP sampling is single-shot server-asks-client, not a tap. The only mid-stream primitive is OpenAI Realtime's truncate-then-new-response, which cancels rather than edits. R6's "interrupt" therefore means: inject at turn boundaries and at tool-call boundaries (lane 5 R1, R2; vendor docs cited there).
2. **"Pull from all stores every cycle" is refuted.** Repoformer shows always-retrieve is often harmful and a learned abstention policy matches or beats it while skipping most retrievals (2403.10059); FLARE, DeepRAG, and ITER-RETGEN show extra rounds add noise past two (2305.06983, 2502.01142, 2305.15294). R3 becomes: every store pull is gated, two cycles by default (lanes 3, 7).
3. **A retrievable learning graph in v0.1 is unsafe.** Query-only memory injection succeeds 98.2 percent of the time against ungated persistent memory (MINJA 2503.03704); embedding-retrievable poison wins at under 0.1 percent presence (AgentPoison 2407.12784). R2's "may or may not exist" resolves to: v0.1 write-only ledger with provenance, retrieval only after execution-gated admission and trust tiers exist (lane 8 R1).
4. **Thinking defaults off for extraction.** NoThinking matches or beats thinking at equal tokens on distilled small models (2504.09858); chain-of-thought damages implicit-pattern tasks by up to 36 points (2410.21333); constraining a whole decode damages reasoning (2408.02442). R4 becomes a harness-owned per-section switch, default off (lane 4).
5. **Prefix reuse is a correctness variable on a quantised 2B.** With model, seed, and order fixed, an enabled prefix cache changed agentic trajectories on 36 percent of episodes at 16-bit and 75 percent under quantisation (2609.04748). R5's cache stays, gated on Proof pass rate (lane 6 R1).
6. **No literature ranks harnesses in theory before training.** Every comparison found is empirical and model-conditional (lane 10 R4). The verdict in section 6 is therefore a requirements-coverage argument plus refutation counts, and must be confirmed by fixing the model and ablating the harness.
7. **Route-everything-to-typed-stores is refuted.** KG-augmented retrieval fell below plain RAG on basic facts (HippoRAG 2, 2502.14802) and raw-log lexical search matched structured-memory pipelines on conversational tasks (ReFind 2608.12888). Typed routing must be selective (lane 9 R1).

## 3. What is fixed before any framework is chosen

Settled on the rig (spikes 001 to 011): one decode yields embedding plus logits; grammar guarantees shape and a token cap guarantees termination; evidence is a verbatim quote resolved harness-side; 1B emits no ops and routing accuracy is flat 0.30 to 0.45 from 2B to 8B before fine-tuning; the 0.6B dedicated embedder owns the durable index; runtime prefix reuse stays and persisted per-chunk KV does not; 16 decode slots saturate one 16 GB card; grammar filtering is the CPU-side ingest bottleneck; one model process, asyncio workers over one model lock, one write lock per store, idempotent op keys; vector-first ranking with graph and SQL as backoff; flat fusion bonuses hurt.

Fixed by the contract: NodeKind tagged sum with `fixpoint` for anything iterative (§2); three artifact scopes with `self_storage` producer-only (§3); opaque admission conditions incl. denied network namespace and a wall-clock ceiling (§8); budget encloses ingest, partial runs are first-class, degradation paths declared (§9); storage-need branches 1 to 4, SQL on Branch 2 (§15); envelope carries evidence refs, trace ref, depth and tier labels, partial and degraded flags (§18.2); invariance (§18.3); selection by alias, capability, or harness name (§18.4); tools grow per part kind, never per modality (§18.5).

## 4. Candidate frameworks

Three whole-system shapes, then the layers the composite is built from. Each line names the lane evidence.

### 4.1 Whole-system shapes

**A. Score Pipeline (baseline, spike 010).** Chunker writes the Score; one pass per section emits `[EMB]` plus grammar-constrained ops with thinking off; Proof files them; recall is one routed cycle, vector-first with graph and SQL backoff; the frontier reads through the §18 tools and one skill. Deterministic everywhere but op content. Convergent with ReWOO's observation-free planning (2305.18323) and the executor half of ReAct (2210.03629). Misses R3 multi-cycle, R6, the learning graph, and any scheduler.

**B. Agentic Loop.** The model runs thought, act, observe with store tools for both ingest and recall, thinking on, in the MemGPT paging shape (2310.08560). Refuted in three places for MelodyScribe: re-prompting the full trajectory each step is the token-inefficient pattern ReWOO argues against (lane 1); execute-to-observe against live stores is a write-path attack surface and a Proof bypass (lane 1 S2); thinking hurts extraction at small scale (lane 4). No admitted paper measures a model of 3B or smaller running such a loop (lane 10 U7). Rejected as the ingest harness; a bounded variant survives inside recall.

**C. Layered Composite.** Shape A extended with seven layers: a dependency-graph planner, a typed-store router with deterministic pre-gates, a gated two-cycle recall, a two-plane scheduler, a boundary co-processor, a sleep-time learner, and a thinking policy. Each layer is deterministic code around one model call surface. This is the proposal; section 5 specifies it.

### 4.2 Layers

**L1 Planner and executor.** Per section the model emits one op list that is a dependency graph; deterministic code fans independent ops out in parallel under one write lock per store, replays, joins, and re-plans once on Proof rejection (LLMCompiler 2312.04511; ReWOO 2305.18323). Op selection is a single-field selector plus argument content (Octopus functional tokens 2404.01744); tool schemas live in a harness registry and only the needed ones plus verified examples are retrieved per section (ToolRAG 2409.00608; Gorilla 2305.15334). Abstention is a trained op: no ops for out-of-scope text, store names masked so the model reads descriptions (Hammer 2410.04587). Proof runs in APIGen order: format checks, then execution and offset resolution, then the semantic judge last (2406.18518).

**L2 Typed-store router.** Deterministic pre-gates decide before the model sees the section: code is detected by tree-sitter (HippoRAG's parser-built precedent 2405.14831; every admitted code-graph system builds by parser, lane 7); SQL-shaped is any payload that is a date, number, setting, table cell, or chart datum, or whose recall needs exact lookup, aggregation, or temporal filtering (2607.18265; TableRAG 2410.04739). The model routes only the residual, narrative content, with a closed op set ADD, UPDATE, INVALIDATE, NOOP resolved against retrieved neighbours before filing (Mem0 2504.19413). Each store has an owner validator slot under one meta-router (MIRIX 2507.07957). Facts and edges carry `valid_from`, `valid_to`, `supersedes`, and a provenance span; contradiction is a state change, never a delete (Zep 2501.13956; SodaMem 2608.08055). An `aliases` table is consulted at insert (LINK-KG 2510.26486). Every ingest path has a symmetric decay or expire path (MemoryBank 2305.10250; MemOS scheduler 2507.03724). A cheap async gleaning pass backfills missed entities and quotes (GraphRAG 2404.16130).

**L3 Gated recall.** A need gate first: a small classifier or reflection token decides no retrieval, one step, or multi-step (Adaptive-RAG 2403.14403; Self-RAG 2310.11511). Then vector first, then structured backoff: graph by PPR seeded from query-to-triple links (HippoRAG 2 2502.14802), SQL filtered to currently-valid rows with time travel available (TRACE 2607.00339), code by ranked signature map plus ego-graph (Aider repo map; RepoGraph 2410.14684), each pull gated (Repoformer 2403.10059). Fusion by structure only, never by adding raw scores (spike 010; HippoRAG 2). Cap two cycles with per-cycle missing-information state (ITER-RETGEN 2305.15294; DeepRAG 2502.01142). A Reason-in-Documents compression pass cites evidence before anything enters the payload (Search-o1 2501.05366). Abstain is a first-class outcome (LongMemEval 2410.10813). Every item carries provenance and validity (Zep).

**L4 Two-plane scheduler.** Two job classes on one model process: real-time (co-processor requests with deadlines) and bulk ingest. Section prefills are chunked and woven against real-time deadlines (SARATHI 2308.16369; SLOWeave 2609.07883); shortest-remaining-work-first with aging (FastServe 2305.05920); checkpoint-yield-resume for preemption (Llumnix 2406.03243); goodput defined as deadlines met plus sections per hour (DistServe 2401.09670). Radix prefix reuse with instruction-first ordering, logged as hit rate and gated on Proof pass rate (SGLang 2312.07104; 2609.04748); KV reused only across byte-identical prefixes, recompute budgeted for any composition (CacheBlend 2405.16444). Grammar masks from a cached automaton engine to remove the 9x CPU cost (XGrammar 2411.15100). Semantic and result caches keyed by session, store version, and model hash with bounded list-valued entries (Cache Saver 2025.findings-emnlp.1402; MeanCache 2403.02694). Embedding and op-emission decodes as segregated tenants (Punica 2310.18547). SQLite at or above 3.51.3, checkpoint off the real-time path (sqlite.org WAL page).

**L5 Boundary co-processor.** Tap the frontier SSE stream read-only; every stored item carries response id and stream offset (Anthropic and OpenAI streaming docs). Inject only in the next request, at turn or tool-call boundaries; put the stable Score and skill prefix behind a cache breakpoint (Anthropic prompt caching). Prefetch: the harness owns the retrieve-now decision and builds the query from the stream prefix, approximating need from text signals since frontier logits are unavailable (FLARE 2305.06983; DRAGIN 2403.10081). Division of labour: the small model drafts and Proof pre-filters so the frontier verifies few high-precision candidates (Speculative RAG 2407.08223). Sidecar outputs travel out of band and are labelled harness-generated (OpenAI Realtime out-of-band pattern). Always-on storing sits behind a measured break-even gate against full-context resubmission (Total Recall 2608.11879). Idle cycles do sleep-time precompute for predictable queries (2504.13171).

**L6 Sleep-time learner.** The reviser is a `fixpoint` node under executor budget. The learning graph in v0.1 is an append-only ledger with provenance, never read on the serving path (lane 8 verdict). Procedures earn admission by execution: sandbox run, test pass, or observed reuse (Voyager 2305.16291; SkillWeaver 2504.07079; LATM 2305.17126). Workflows and lessons are induced offline from bulk histories (AWM 2409.07429); reflection runs as a scheduled background job (Generative Agents 2304.03442; Letta sleep-time 2310.08560). Minimum schema: nodes `procedure`, `workflow`, `lesson`, `preference`, `mistake`; edges `depends_on`, `composes_with`, `derived_from`, `supersedes`, `contradicts`, `evidenced_by`; envelope `status`, `verifier`, `provenance`, `validity`, `trust_tier` (lane 8). Evolution of existing records is gated strictly above appends (A-MEM 2502.12110; InjecMEM 2608.23471). Retrieved lessons are data, never instructions; learned skills run only in the Folio sandbox (PoisonedRAG 2402.07867).

**L7 Thinking policy.** Default non-thinking single pass. Thinking is a per-section harness switch in the Qwen3 shape (`enable_thinking` plus `/think` and `/no_think`, latest wins; 2505.09388) with a hard token cap and forced stop (s1 2501.19393). Spare budget goes to parallel short reads with early-finish selection and Proof-gated voting, never to a longer single trace (Mirage 2506.04210; short-m@k 2505.17813). Think-enabled decodes are reason-then-format with the grammar applied after a trigger token (In-Writing 2601.07525) and ThinkBrake logit-margin early stop (2510.00546). Latent and recurrent thinking stay out of v0.1 (Huginn probe 2507.02199). Thinking traces are never persisted verbatim (lane 4 S1).

**L8 Evaluation and reward (the meta-harness).** Op emission graded by AST match plus execution with an explicit irrelevance split (BFCL PMLR v267); Proof reliability as pass^k over repeated trials with store-state matching (tau-bench 2406.12045); milestones and minefields for partial credit (ToolSandbox 2408.04682); recall scored on LongMemEval's five abilities and LoCoMo's categories; serving reported as capacity under a tail-latency SLO with TTFT and TBT split (Sarathi-Serve 2403.02310). Rewards staged: grammar-valid emission and retrieval invocation first with no answer component, correctness second (R1-Searcher 2503.05592), non-model tokens masked from the loss (Search-R1 2503.09516), Proof as a rule-based reward with no learned reward model (DeepSeek-R1 2501.12948), memory-write choice as an RL action (Memory-R1 2508.19828). A Reflexion-style no-weight-update loop runs beside the RL track (2303.11366).

## 5. The pre-alpha composite (shape C)

```
                 frontier model (Claude / GPT / Gemini)
                     │ SSE stream (read-only tap)          ▲ next request at turn / tool-call boundary
                     ▼                                      │ payload = Proof-passed, cited, compressed
  ┌────────────── L5 boundary co-processor ─────────────────┤
  │  stream buffer + offsets   need detector   prefetch queue   break-even gate
  └──────┬──────────────────────────────┬───────────────────┘
         │ Score (chunker-authored)     │ recall request (deadline)
         ▼                              ▼
  ┌── L2 pre-gates ──┐         ┌── L3 gated recall ───────────────────────────┐
  │ tree-sitter→code │         │ need gate → vector → {PPR graph | SQL valid │
  │ date/number/     │         │ rows | code ego-graph} each gated → structure│
  │ table→SQL-shaped │         │ fusion → cycle 2 if missing → compress+cite │
  │ residual→model   │         │ → abstain or payload                         │
  └──────┬───────────┘         └───────────────────▲──────────────────────────┘
         ▼                                         │
  ┌── L1 one pass per section (L7: thinking off by default) ───────────────┐
  │ [doc_prefix][section][EMB] → embedding      grammar ops = dependency DAG│
  └──────┬─────────────────────────────────────────────────────────────────┘
         ▼
  ┌── L1 Proof (format → resolve quotes/offsets → semantic) → executor fan-out ──┐
  │  ADD / UPDATE / INVALIDATE / NOOP, per-store write lock, idempotent keys       │
  └──┬────────┬────────────┬───────────┬──────────────┬────────────────────────────┘
     ▼        ▼            ▼           ▼              ▼
  vector   knowledge    code graph   SQL facts     Folios (self_storage)
  (Faiss)  graph(Cozo)  (parser-     (SQLite blob, learning ledger v0.1
           quotes,      built, own   valid_from/to, (append-only, provenance,
           validity     schema)      supersedes,    never read on serving path)
                                     aliases)
     ▲
  ┌── L6 sleep-time learner (fixpoint under budget): gleaning, decay/expire, reflection,
  │   execution-gated Folio admission, evolution gated above appends
  └── L4 two-plane scheduler underneath everything: real-time deadlines vs bulk ingest,
      chunked prefill, SRWF+aging, radix prefix (gated on Proof), XGrammar masks,
      namespace-keyed caches, one model process, segregated tenants, SQLite ≥ 3.51.3
  L8 eval/reward wraps the whole thing: pass^k, AST+exec, five abilities, capacity under SLO
```

Dataflows:

- **Bulk ingest.** Chunker writes the Score. L2 pre-gates tag each section (code, SQL-shaped, narrative). Code sections bypass the model: tree-sitter plus an LSP or SCIP resolver builds symbols and CONTAINS, CALLS, INHERITS, IMPORTS edges with line spans into the code graph, incrementally on change (lane 7). Other sections go through L1: one pass emits `[EMB]` and the op DAG; Proof resolves quotes to offsets, checks dates and types, rejects and logs; the executor fans out under per-store locks. L4 runs this on the bulk plane and chunks prefills so real-time work is never blocked.
- **Recall.** A §18 query arrives, or L5 issues a prefetch. L3's need gate decides; vector first; each structured backoff is gated; structure-only fusion; a second cycle only if the missing-information state is non-empty; compress and cite; abstain if evidence is insufficient. Payload items carry provenance and validity; only Proof-passed content is asserted, drafts are cited as candidates.
- **Co-processor.** L5 taps the frontier stream, buffers deltas with offsets, and hands closed spans to the bulk plane with provenance (response id, offset, speaker). The need detector reads the stream prefix and, when a need fires, schedules a prefetch on the real-time plane. At the next boundary the harness sends the assembled payload in the next request behind a cache breakpoint. Nothing is injected mid-stream because no API allows it.
- **Sleep time.** When the real-time plane is idle, L6 runs gleaning, decay, reflection, Folio practice-and-admit, and precompute for predictable queries, all as `fixpoint` work under budget, all off the live path.

## 6. Evaluation against the requirements (in theory)

| Requirement | A Pipeline | B Agentic loop | C Composite |
|---|---|---|---|
| R1 ingest routing under Proof | yes, single-store-per-op | yes but execute-to-observe bypasses Proof (lane 1 S2) | yes, DAG ops plus pre-gates plus closed op set |
| R2 five stores plus Folios | vector, graph, SQL, Folios only | all, model-routed, code and dates by judgement (refuted, lane 2 U) | all: code by parser, SQL by deterministic gate, learning ledger write-only |
| R3 multi-cycle recall | one cycle | unbounded loop, refuted past two rounds | gated two-cycle with abstain |
| R4 thinking | off, unswitchable | on, refuted for extraction | per-section switch, default off, parallel-short when budgeted |
| R5 caching and parallelism | prefix reuse and slots only | per-step re-prompt defeats prefix reuse | two-plane scheduler, gated caches, XGrammar, tenants |
| R6 co-processor | none | none | boundary tap and inject, prefetch, break-even gate |
| R7 contract fit | fits today | loop outside executor control (§2 fixpoint rule) | fits with the four updates in section 7 |
| R8 all components fit | no (R3, R6 missing) | no (three refutations) | yes, every requirement has a layer and a cited mechanism |

Verdict: **C, the layered composite, is the framework that holds up in theory.** A is its degenerate case and remains the correct first rung to build. B is rejected as the ingest harness on three primary-source refutations and survives only as the bounded loop inside L3. Caveat from lane 10 R4: this ranking is a coverage argument; the literature supports only fix-the-model, ablate-the-harness, per-capability deltas with consistency statistics as the way to confirm it.

## 7. Databasise 2.0 updates the composite needs

1. **A stream-tap ingest operation.** Storing from a frontier stream is ingest of a stream with provenance (response id, offset, speaker), not of a document. Under §18.5 a genuinely new operation earns a tool per part kind; propose a `stream_ingest` part kind (not a `melodyscribe_*` tool) whose §18 tool any modality can implement.
2. **Request deadline classes.** §8 gives nodes a wall-clock ceiling and §9 gives budgets, but nothing distinguishes a real-time request from bulk work. Add a per-request deadline or priority class to the run record so L4 can schedule to goodput and the envelope can flag a deadline miss as a declared degradation path (§18.2).
3. **Code graph as a capability, not a store kind.** §15 Branch 1: a second graph instance with a declared `code` sub-capability and its own schema on the existing graph store type. No sixth store.
4. **Cache and memo keys in the identity model.** Semantic and result caches key on session, store version, and model hash; memoised payloads are `quarantined` artifacts refcounted to the instance. §1's `config_hash` already covers model and wiring; store version needs to be addressable.
5. **Validity intervals on facts.** `fact_with_validity_interval` already exists in the `ItemKind` union (§4); the SQL sidecar schema and graph edge metadata must carry `valid_from`, `valid_to`, `supersedes`, and a provenance span so recall can filter to currently valid rows.
6. **Learning ledger scope.** v0.1 ledger is Branch 3 `self_storage`, append-only; promotion to a readable store is a §6 promotion with the execution gate as its evidence. Fits today; note it so it is not skipped.

## 8. What this harness tells the fine-tune

The point of designing the harness first. Training targets the harness defines:

- **Op emission**: one-pass `[EMB]` plus dependency-DAG ops under the per-file-set grammar; explicit NOOP and abstention with irrelevance negatives; store names masked; verbatim-quote evidence; closed lifecycle ops ADD, UPDATE, INVALIDATE.
- **Routing residual only**: the model never decides code versus text or date versus prose; it decides graph versus vector versus Folio for narrative content, and UPDATE versus INVALIDATE against retrieved neighbours.
- **Recall gates**: a need token (retrieve or not, one step or multi) and per-passage relevance and support verdicts; a stop signal for cycle two.
- **Rewards, staged**: stage 1 grammar-valid emission and correct invocation with no answer component; stage 2 Proof pass, retrieval hit, and downstream answer quality; Proof stays rule-based; non-model tokens masked from the loss; memory-write choice rewarded by downstream QA.
- **Thinking**: trained toward short traces with RL length control only if a think-enabled path is ever kept; otherwise no thinking data at all.
- **Embedding**: the durable index stays on the 0.6B embedder; the 2B's `[EMB]` serves session recall and Folios until a generation-preserving adapter beats parity (spike 011 line).

## 9. Open questions carried forward (unresolved ledger, condensed)

- No admitted paper measures a 1B to 3B model routing across typed stores, deciding retrieve-or-not, or writing usable graph queries; every routing number comes from frontier-class models (lanes 2, 3, 7).
- No study reports capacity under a latency SLO for one model process serving embedding and generation on one 16 GB card (lanes 6, 10).
- No per-fact store-routing labels exist in any public dataset; LongMemEval's update and abstention splits are the closest proxies (lane 2).
- The interaction between thinking bytes and grammar-constrained op emission at 2B is unmeasured (lane 4 U2).
- Small-model procedure induction quality and poisoned-skill execution are unmeasured (lane 8).
- Persisted-KV tiers must be re-tested against recompute each release; "no persisted KV at 2B" is a price ratio (lane 6).

## 10. Next steps proposed

1. Owner review of this note and of the seven corrections in section 2, especially the boundary-only co-processor and the write-only learning ledger.
2. A rig spike that fixes MiniCPM5-2B and ablates the harness layers in order A, then A plus L2, then plus L3, reporting per-capability deltas and pass^k, per lane 10 implication 8.
3. A contract amendment note for the four updates in section 7, argued under §15 and §18.5 before any code.
4. Fold section 8 into the spike 011 training recipe as the target op schema and reward stages.
