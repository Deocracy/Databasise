# Lane 8 findings — learning graphs and procedural memory

Scope: whether MelodyScribe needs a learning graph (procedures, lessons,
mistakes, preferences, their dependencies), what its minimum schema is, how
entries earn admission, and what persistent memory costs in security terms.
All arXiv ids below were opened at `arxiv.org/abs/<id>` and downloaded as
PDF (`%PDF` verified); mechanism claims were additionally checked against
arXiv full-text HTML term counts (see method.md). Vendor/reported numbers
are cited for what the authors report and nothing more. 2026 preprints are
single-version and treated as provisional.

## (a) Admitted items

**1. Voyager — skill library with execution-gated admission
(arXiv:2305.16291).** A lifelong Minecraft agent that accumulates a library
of code skills (executable programs), proposes its own curriculum, and admits
a new skill only after self-verification by executing it in the environment.
Take: this is the oldest existence proof that a persistent procedural store
works when admission is execution, not opinion — the environment, not a
judge model, decides what enters the library. MelodyScribe's learning graph
should copy the gate (a candidate procedure earns admission by running
successfully somewhere checkable), not the Minecraft setting. Caution:
Voyager's verifier is a full game simulator; MelodyScribe has no equivalent
execution environment for general "learnings" in v0.1, which bounds what can
be admitted at first. Repo: https://github.com/MineDojo/Voyager (~7.2k
stars, page scrape 2026-09-13).

**2. Reflexion — verbal reinforcement over episodic memory
(arXiv:2303.11366).** The agent stores past trajectories in episodic memory,
generates a verbal self-reflection on failure, and retries with the
reflection in context — reinforcement in language, with no weight updates.
Take: the minimal learning loop (act, fail, reflect in words, retry with the
words attached) needs no graph at all, and it is the correct v0.1-shape
fallback: a reflection is a candidate lesson, and the retry outcome is its
first verification signal. Caution: reflections accumulate unboundedly and
are never versioned or invalidated here; without supersede/contradict edges
this becomes silt, which is exactly the failure the schema below is designed
to prevent.

**3. ExpeL — insights extracted from success and failure, retrieved at test
time (arXiv:2308.10144).** Past trajectories are distilled into
natural-language insights (what worked, what did not), which are retrieved
into context for new tasks; the agent improves with no parameter updates.
Take: ExpeL is the cleanest template for MelodyScribe's lesson layer —
learnings are short declarative statements induced from contrasted
experiences and retrieved by similarity at use time. Caution: induction is
unvalidated LLM judgment with no execution check and no provenance back to
the episodes; MelodyScribe must attach each lesson to its source turns and a
verification outcome (see admission schema), or lessons are ungrounded lore.

**4. Agent Workflow Memory — induced reusable routines, offline and online
(arXiv:2409.07429).** AWM induces workflows (reusable sub-routines) from
agent trajectories and installs them as memory, either once beforehand
(offline) or incrementally during testing (online); text and code
representations work equally well; reported relative gains are 24.6% on
Mind2Web and 51.1% on WebArena. Take: workflows are the right granularity
for MelodyScribe procedures — bigger than an op, smaller than a Folio —
and the offline/online split maps directly onto MelodyScribe's bulk-ingest
vs live co-processor split (distill bulk histories offline; induce online
only through the gated path). Caution: induction and retrieval both assume a
frontier-class model; a 2B model's induced workflows are unmeasured, and
online induction during live turns is the highest-risk write path in this
whole lane. Repo: https://github.com/zorazrw/agent-workflow-memory (~471
stars, page scrape).

**5. SkillWeaver — explore, practice, distill into APIs with a reliability
gate (arXiv:2504.07079).** A three-stage pipeline (discover skills by
exploration, practice them, distill successes into tested Python APIs) grows
a plug-and-play library; reported relative gains are 31.8% (WebArena) and
39.8% (real sites), and strong-agent APIs transfer to weaker agents (up to
+54.3%). Take: the practice-then-distill order is the admission protocol
MelodyScribe should copy — a Folio-grade skill is not filed when written but
when it has survived practice — and the strong-to-weak transfer result is
direct evidence that procedures learned once can serve a smaller model,
which is MelodyScribe's whole bet. Caution: the test/debug gate runs real
code against live sites; MelodyScribe's sandbox story for Folios must exist
before this pattern can be used. Repo:
https://github.com/OSU-NLP-Group/SkillWeaver (156 stars, MIT, via API).

**6. WebXSkill — the only explicit skill-graph schema found
(arXiv:2604.13318).** Skills are dual-mode (executable code plus step
guidance), organized in a skill graph keyed by page nodes (~4.2 skills per
node, keeping each retrieval unit compact); usage rate 70.8% vs 37.7% for
SkillWeaver-style flat libraries; skills average 3.8 operations vs 1.6.
Take: this is the single closest structural answer to the lane question —
procedural memory should be a graph (context-node to skill edges), not a
flat list, because the graph is what keeps retrieval precision up as the
library grows; MelodyScribe's Folio index should copy page-node-style
partitioning (skill keyed by the situation it applies to). Caution:
August-2026 single-version preprint; the usage-rate comparison is
author-reported on their own harness.

**7. AFlow — procedures as searchable code graphs (arXiv:2410.10762, ICLR
2025).** Agentic workflows are represented as code (nodes plus edges) and
optimized by Monte Carlo Tree Search with execution feedback; reported +5.7%
over manual designs and +19.5% over automated baselines, with small models
beating GPT-4o at 4.55% of inference cost on some tasks. Take: two lessons —
learned procedures want a code/graph representation so they can be searched
and composed, and small-model-plus-good-workflow beats big-model-alone,
which is the economic argument for MelodyScribe's learning graph existing at
all. Caution: search happens offline with a strong optimizer model; nothing
here runs on-device or in real time.

**8. LATM — tool maker, tool user, dispatcher, unit-test gate
(arXiv:2305.17126).** One role makes tools (functions), another uses them,
a dispatcher routes; candidate tools enter the cache only after passing
generated unit tests. Take: the role split is directly portable — MelodyScribe
(the maker, offline or background) proposes procedures while the serving path
(the user) only invokes admitted ones — and the unit-test gate is the
minimal viable admission verifier for anything executable. Caution: test
generation is itself model judgment; a weak maker writes weak tests, so the
gate's strength must be calibrated, not assumed.

**9. A-MEM — Zettelkasten notes with linking and evolution
(arXiv:2502.12110).** Each memory is a note `{content, timestamp, keywords,
tags, contextual description, embedding, links}`; new notes trigger link
generation to old notes and evolution (rewriting) of old notes' context.
Take: the note schema is the best starting point for the minimum learning
record (attributes plus embedding plus links in one unit), and backward
evolution names the operation MelodyScribe needs when a new lesson changes
an old one. Caution: unconstrained evolution is also the attacker's favorite
write primitive (see §(d) S2) — adopt the schema, but gate evolution above
appends. Repo: https://github.com/agiresearch/A-mem (1178 stars, MIT).

**10. Mem-α — the construction policy itself is learned by RL
(arXiv:2509.25911).** Instead of prompted heuristics, reinforcement learning
trains what to store, how to structure it, and when to update. Take: direct
support for the owner's harness-first thesis applied to learning memory —
the harness defines the learning action space (admit, link, supersede,
invalidate) and the reward (retrieval-hit, task gain), and the small model
is fine-tuned into it later. Caution: paper rewards are QA-shaped; for
procedural memory the reward must be execution success and later reuse, not
answer overlap.

**11. Hindsight — retain/recall/reflect with evidence kept separate from
inference (arXiv:2512.12818).** Verbatim evidence is stored apart from model
inference, and reflection is a named post-ingest consolidation stage that
organizes memory beyond snippets. Take: the architectural home for learning
content — reflections, lessons, and Folio distillations belong to the
reflect stage, never to the evidence tier — which settles the tiering
question: learning graph is a separate tier from knowledge graph and SQL,
and its contents are never cited as verbatim evidence. Caution: commercial
system; consolidation claims should be verified in code before copying
mechanics. Repo: https://github.com/vectorize-io/hindsight.

**12. Generative Agents — memory stream with importance gating and
scheduled reflection (arXiv:2304.03442).** Observations stream in; each gets
an importance score; retrieval blends recency, importance, and relevance;
reflection runs on a schedule over recent memories, not per event. Take: two
admission primitives worth copying — importance scoring at write time (a
cheap learned or heuristic gate before anything reaches the graph) and
batched scheduled reflection (learning runs as a background job, never on
the live turn path). Caution: importance scores are uncalibrated model
judgment; treat as a priority hint for the reflection backlog, not as an
admission decision.

**13. MemGPT/Letta — paging plus memory blocks and sleep-time consolidation
(arXiv:2310.08560).** The paper's paging interface
(model-issued reads/writes between main context and archival/recall stores)
is the ancestor of op-based memory; the maintained Letta lineage adds
persistent memory blocks (the "memory files" of the brief) and sleep-time
consolidation — background passes that reorganize memory off the live path.
Take: memory files/blocks are the running-code precedent for Folios as
private persistent files, and sleep-time compute is the scheduling pattern
for all learning writes: reflection, distillation, and evolution run while
the co-processor is idle, never competing with a live turn. Caution: the
paper itself has no learning graph and no admission policy; the pattern
comes from the lineage's later engineering. Lineage:
https://github.com/letta-ai/letta (24.7k stars, Apache-2.0).

**14. STaR — generate, filter on success, retrain (arXiv:2203.14465).**
Rationales that lead to correct answers are kept and fine-tuned on;
bootstrapping repeats the loop. Take: the template for converting harness
validation signals into training data — MelodyScribe's Proof pass/fail plus
retrieval-hit logs are the filter, and admitted learnings are the rationales
— which is how the learning graph becomes the fine-tuning dataset (lane-10
input). Caution: STaR filters on answer correctness, a signal MelodyScribe
often lacks; execution success and Proof-pass are the available substitutes
and must be validated as filters first.

**15. Deep Knowledge Tracing — latent-state tracing without a graph
(arXiv:1506.05908).** An RNN predicts student performance from interaction
sequences, modeling knowledge as an implicit hidden state. Take: the
baseline that shows what a graph adds — DKT works but cannot name
prerequisites, compose skills, or explain; if MelodyScribe's learning store
were just embeddings of past sessions it would inherit exactly these blind
spots, which is the argument for explicit nodes and edges over implicit
state. Caution: 2015, pre-Transformer; cite for the representational point
only.

**16. Knowledge Tracing: A Survey — the skill-graph schema catalogue
(arXiv:2201.06953, ACM Computing Surveys).** Reviews graph-based KT:
knowledge-component nodes with dependency/prerequisite edges, graphs built
by statistics (transition counts) or learned end-to-end, plus
forgetting-aware and attentive variants; frames the student as any agent,
including artificial ones. Take: the schema menu for the learning graph —
KC-style nodes, prerequisite/dependency edges, statistics-built edges as the
cheap default (co-occurrence of procedures in successful sessions) with
learned edges deferred — and forgetting-aware tracing as the principled
form of decay for learned content (prefer over global Ebbinghaus for skills:
decay what is superseded, not what is old). Caution: tutoring domain; edge
semantics (prerequisite) transfer, but student-performance prediction does
not — MelodyScribe predicts usefulness, not correctness.

**17. LongMemEval-V2 — workflow-knowledge and gotchas as an eval target
(arXiv:2605.12493).** 451 questions over histories of up to 500 trajectories
testing five abilities including workflow knowledge and environment gotchas;
the code-gathering AgentRunbook-C reaches 72.5% vs 48.5% for RAG. Take: the
gotchas split is the first public proxy for "did the harness learn the
lesson" — MelodyScribe's learning-graph eval should be gotcha-shaped
(saved lesson changes a later outcome), and runbook/strategy notes are an
independent convergence on Folio-like private procedure files. Caution:
May-2026 single-version preprint; coding-agent methods carry high latency
cost by the authors' own report.

**18. MINJA — query-only memory injection (arXiv:2503.03704, NeurIPS
2025).** Any unprivileged user injects malicious records into agent memory
through ordinary queries (indication prompt plus progressive shortening);
reported 98.2% injection success and 76.8% attack success, surviving
perplexity and rephrasing defenses. Take: the decisive security fact for
this lane — every ingest path that can write a learning (including
storing from the frontier stream) is writable by the frontier stream's
counterparty, so learnings need provenance (who said it, in which turn)
and a trust tier before they are retrievable. Caution: demonstrated on
reasoning-agent demo memories, not on graph-structured procedural stores;
transfer to skill graphs is plausible but unmeasured.

**19. AgentPoison — embedding-optimized backdoor triggers on agent memory
(arXiv:2407.12784, NeurIPS 2024).** Optimized triggers map poisoned
demonstrations into a unique embedding region so they are retrieved on
demand; reported ≥80% attack success at <0.1% poison rate with ≤1% benign
impact, transferring across embedders. Take: retrieval-by-embedding over a
learning store is itself the attack surface — a poisoned lesson needs only
to be retrievable, not believed — so learning-graph retrieval must be gated
by admission status and trust tier before similarity is even computed.
Caution: assumes attacker knowledge of (or transfer to) the embedder;
still, MelodyScribe's embedder is fixed and public-shaped, which helps the
attacker. Repo: https://github.com/BillChan226/AgentPoison (~243 stars,
page scrape).

**20. PoisonedRAG — corpus-layer poisoning of retrieval (arXiv:2402.07867).**
Attacker-injected texts are crafted to be retrieved for target questions
and steer generation, under both black-box and white-box retriever
assumptions. Take: the corpus layer (the stored texts themselves) is
poisonable independent of the model — for MelodyScribe this means the
learning graph's text bodies must be treated as untrusted input at
retrieval time (sandboxed rendering, no instruction following from
retrieved lessons), not just at write time. Caution: RAG QA setting;
procedure-invocation poisoning (poisoned skill executes harmfully) is the
sharper MelodyScribe analogue and is unstudied.

**21. InjecMEM — single-interaction injection robust to drift
(arXiv:2608.23471).** One interaction suffices: a retriever-agnostic topical
anchor plus an optimized command, effective under memory drift and variable
placement while leaving non-target queries clean. Take: recency and
placement defenses do not work — the anchor survives drift — so the learning
graph cannot rely on decay or ranking to neutralize poison; only admission
gating and trust tiers do. Caution: August-2026 single-version preprint
from a 2-star repo; treat as a warning shot, not a settled result. Repo:
https://github.com/BlueBlood6/InjecMEM.

## (b) Refutations

**R1 — Against "a v0.1 learning graph that is read at query time is a free
choice": refuted as safe.** MINJA (2503.03704: 98.2% injection via
query-only interaction) and AgentPoison (2407.12784: ≥80% success at <0.1%
poison) jointly show that any retrievable persistent memory without
provenance and admission gating is attacker-writable. The brief's "may or
may not exist in v0.1" must therefore resolve to: write-only ledger in v0.1,
retrievable store only after gating exists. The safe subset is logging, not
recall.

**R2 — Against "A-MEM-style backward evolution can be copied wholesale":
refuted as safe without a higher gate.** A-MEM (2502.12110) lets new
memories rewrite old ones; MINJA and InjecMEM (2608.23471) show that
update/evolution paths are exactly the persistence mechanism attacks rely
on. Evolution must require a strictly higher gate than appends (verifier
pass plus provenance, or human), with Zep-style invalidation preferred over
silent overwrite.

**R3 — Against "admission can be an LLM judge call": execution beats
opinion everywhere it was tried.** Voyager (2305.16291: environment
self-verification), SkillWeaver (2504.07079: practice plus test/debug),
LATM (2305.17126: unit-test gate) all admit by running, not by judging.
No admitted paper shows judge-scored admission working for procedural
content on small models. MelodyScribe admission must be execution-shaped
(sandbox run, Proof check, retrieval-hit history); judge scores are at most
a prioritization hint.

**R4 — Three seed-id corrections.** The recalled ExpeL id 2310.10495
resolves to an unrelated hallucination-detection paper (true ExpeL:
2308.10144); the recalled AWM id 2405.15283 resolves to a condensed-matter
physics paper (true AWM: 2409.07429); the assumed AKT id 2007.12375 resolves
to a medical-data paper (AKT has no verified arXiv id). All caught by
opening the abs page; recorded as guard rows in inventory.tsv.

**R5 — Against "the learning graph duplicates the knowledge graph, so one
store suffices": refuted by representation.** DKT (1506.05908) shows implicit
state cannot express prerequisites or composition; WebXSkill (2604.13318)
shows a flat skill list retrieves measurably worse than a skill graph
(37.7% vs 70.8% usage); Hindsight (2512.12818) separates evidence from
inference as an architectural rule. Procedures (runnable, versioned,
execution-verified) and facts (quoted, offset-resolved) need different
nodes, different edges, and different gates — one store cannot serve both.

## (c) Unresolved ledger

- **A2Flow (2511.20693, AAAI-2026 per abs)** — self-adaptive operator
  extraction with an operator-memory mechanism; title/abstract verified,
  paper not opened. Most relevant follow-up; recommend promotion.
- **MemoryAgentBench (2507.05257)** — memory-agent benchmark with a
  test-time-learning split; abstract verified, paper not opened. Eval
  territory (lane 10); the test-time-learning split overlaps this lane.
- **ASI / WALT (2025–2026)** — skill methods known only via WebXSkill's
  comparison table; no ids verified. Follow-up candidates.
- **GIKT (2009.05991)** — graph-interaction KT; abstract verified, paper not
  opened. Coverage carried by KT-Survey + DKT.
- **Second KT survey (2105.15106)** — abstract verified; prefer the ACM
  version admitted here; its EduData/EduKTM libraries are tooling
  follow-ups.
- **Chronos taxonomy (2607.19433)** — admitted and verified by lane 2, cited
  here, not re-downloaded.
- **Small-model procedure induction quality** — no admitted paper measures
  1–3B workflow/skill induction; AWM, SkillWeaver, and AFlow numbers all
  come from frontier-class models. Whether a 2B model can induce usable
  procedures pre-fine-tuning is unmeasured anywhere and is this lane's
  biggest open risk (parallels the brief's spike-003 routing finding).
- **Poisoned-skill execution** — corpus poisoning (PoisonedRAG) and
  memory-trigger poisoning (AgentPoison) are demonstrated; a poisoned
  executable skill (harmful when run, clean when read) is not studied in
  any admitted paper. The sandbox requirement in §(d) rests on this gap.

## (d) Security findings (stated as requirements)

- **S1 — Provenance on every learning, trust tier before retrieval
  (MINJA 2503.03704; AgentPoison 2407.12784).** Each learning record carries
  source session, speaker/principal, and source turns; retrieval filters by
  admission status and trust tier before similarity ranking. Unattributed or
  low-tier content is never retrieved into a live turn.
- **S2 — Evolution gated above appends (A-MEM 2502.12110; InjecMEM
  2608.23471).** Any write that touches existing records (supersede,
  re-link, invalidate, evolve) requires verifier-pass plus provenance, or
  human approval; prefer invalidation (state change with history) over
  silent overwrite.
- **S3 — Retrieved lessons are data, never instructions (PoisonedRAG
  2402.07867).** Learning-graph content rendered into any context must be
  sandboxed as data: no instruction-following from retrieved lessons, and
  executable skills run only in the Folio sandbox, never in the serving
  path directly.
- **S4 — Decay is not a defense (InjecMEM 2608.23471).** Anchors survive
  drift and placement changes; do not rely on recency, decay, or ranking
  to neutralize poisoned learnings. Quarantine is explicit state, not a
  score.

## Verdict: v0.1 component or later, and the minimum schema

**Verdict: the learning graph is a v0.1 write-only ledger and a v0.2+
retrievable store.** In v0.1 MelodyScribe logs candidate learnings
(append-only, with provenance, never retrieved into a turn) and distills
Folios offline through the execution gate; the serving path reads no
learned content. Promotion to a retrieved store waits on three gates that
do not exist in v0.1: an execution verifier for procedures (the
Voyager/SkillWeaver/LATM pattern), provenance plus trust tiers (the
MINJA/AgentPoison requirement), and a scheduled reflection job off the live
path (the Generative-Agents/AWM-online pattern). Shipping retrieval before
those gates exist replays the exact configuration every attack paper in
§(a) exploits.

**Minimum schema.** Node types: `procedure` (runnable skill: name,
signature, body, version), `workflow` (ordered procedure refs plus induction
source), `lesson` (declarative statement plus scope), `preference`
(statement plus principal), `mistake` (failed attempt plus context). Edge
types: `depends_on` (prerequisite, per KT-Survey), `composes_with`,
`derived_from` (lesson to source turns; ExpeL lineage), `supersedes`,
`contradicts`, `evidenced_by` (execution or retrieval-hit record).
Admission envelope on every node: `status`
(candidate/admitted/quarantined), `verifier` (what ran, result, sandbox
id), `provenance` (session, speaker, source turns), `validity`
(valid_from, invalid_at), `trust_tier`. Retrieval rule: only `admitted`
nodes at or above the turn's trust tier, filtered before similarity
ranking; learning content is never cited as verbatim evidence (Hindsight
rule — quotes come only from knowledge-graph/SQL ops).

## Harness implications

1. Ship the learning graph in v0.1 as a write-only ledger with provenance
   on every entry and no serving-path retrieval, because query-only
   injection succeeds 98.2% of the time against ungated persistent memory
   (2503.03704).
2. Admit procedures by execution (sandbox run, test pass, or observed reuse
   success), never by judge-model opinion, following the Voyager
   self-verification, SkillWeaver practice-plus-test, and LATM unit-test
   gates (2305.16291; 2504.07079; 2305.17126).
3. Induce workflows and lessons offline from bulk histories and online only
   through the gated path, copying AWM's offline/online split and its
   routine granularity (2409.07429).
4. Organize procedures as an explicit skill graph keyed by applicable
   situation (not a flat list), because graph organization doubles skill
   usage over flat libraries (2604.13318).
5. Run all learning writes (reflection, distillation, evolution) as
   scheduled background jobs off the live turn, per Generative-Agents
   scheduled reflection and Letta sleep-time consolidation (2304.03442;
   2310.08560).
6. Define the learning action space (admit, link, supersede, invalidate) in
   the harness and reward retrieval-hit and execution success, so the later
   fine-tune trains construction rather than prompting it (2509.25911;
   2203.14465).
7. Give every learning node an admission envelope (status, verifier result,
   provenance, validity interval, trust tier) and filter by tier before
   similarity ranking, because embedding-retrievable poison needs <0.1%
   presence to win (2407.12784; 2502.12110).
8. Gate multi-record evolution strictly above appends with invalidation
   preferred over overwrite, since update paths are the attacks'
   persistence mechanism (2502.12110; 2608.23471).
9. Treat retrieved lessons as untrusted data (never instructions) and run
   learned skills only in the Folio sandbox, because corpus-layer poisoning
   works independent of the model (2402.07867).
10. Evaluate the learning graph gotcha-shaped (a saved lesson must change a
    later outcome, à la LongMemEval-V2 workflow/gotchas splits) rather than
    by recall scores, and log Proof-pass plus retrieval-hit as the future
    training signal (2605.12493; 2203.14465).
