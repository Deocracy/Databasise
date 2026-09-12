# Lane 6 findings: Self-written skills and procedural memory

Scope: skill libraries an agent writes and retrieves; the Agent Skills specification
and file-style memory; the security literature on persistent injection through
memory and skills. All admitted items were opened at a primary source (arXiv abs
page, downloaded PDF, repo page, or spec page) during this session. 20 admitted,
7 abstained, 27 screened.

## (a) Admitted items

**Voyager (arXiv 2305.16291).** The first large-scale self-written skill library:
an agent stores successful action programs indexed by description embedding,
retrieves top-k for new tasks, and composes complex skills from simpler ones,
with an automatic curriculum and execution-feedback repair loop. For
MelodyScribe it is the existence proof that file-like, model-written,
embedding-indexed skills compound ability without weight updates.
Be careful: skills are executable code with no trust model at all, and the
system assumes a frontier model (GPT-4) as the writer; a 2B writer will produce
far noisier candidates, so the verification gate matters more than the library.

**ExpeL (arXiv 2308.10144).** Learns cross-task natural-language insights with
ADD/EDIT/UPVOTE/DOWNVOTE operators over success/failure pools, then retrieves
insights plus similar trajectories at inference. This is the direct precedent
for a revise pass that writes Folios: voted, curated, text-form procedural
memory. Be careful: insight quality depended on GPT-4 as the extractor, and
the vote counters are gameable by a compromised memory (see MINJA below), so
votes must be weighted by provenance, not raw counts.

**ACE (arXiv 2510.04618).** Generator/Reflector/Curator roles maintain an
evolving playbook via incremental delta updates with helpful/harmful counters,
explicitly designed to avoid brevity bias and context collapse; +10.6% on
agents, +8.6% on finance, and the repo (https://github.com/ace-agent/ace)
acknowledges building on Dynamic Cheatsheet. This is the closest published
analog of a Folio: a single evolving text artefact with structured curation.
Be careful: counters and bullets are still prompt-level metadata with no
integrity protection, and online adaptation without ground truth (its headline
feature) is exactly the setting where poisoning is hardest to detect.

**Dynamic Cheatsheet (arXiv 2504.07952).** A single persistent text memory
updated at test time, with cumulative and retrieval-synthesis variants; GPT-4o
went from ~10% to ~99% on Game-of-24 by reusing a discovered Python strategy.
Take the curator-prompt pattern and the cumulative-vs-retrieval ablation as the
starting design for Folios. Be careful: the paper reports capability gains only
and does no adversarial evaluation of the cheatsheet itself.

**Agent Workflow Memory (arXiv 2409.07429).** Induces reusable sub-routines
from annotated examples (offline) or past experience (online) and injects the
relevant workflow at generation time; large gains on Mind2Web/WebArena. Take
the offline/online split as the template for MelodyScribe's background revise
pass versus inline filing. Be careful: online induction inherits whatever is
in the trajectory store, poison included.

**SOP-Agent (arXiv 2501.09316).** Inverts the direction: domain experts write
pseudocode SOPs as decision graphs that the general agent traverses. This is
the published form of MelodyScribe's "one human-authored skill file" serving a
frontier model, and the strongest argument for keeping that tier human-signed.
Be careful: no code artefact was released, so the traversal machinery must be
rebuilt; also SOPs are human-authored, so this paper says nothing about
machine-written skill safety.

**Reflexion (arXiv 2303.11366).** Verbal self-reflection written to episodic
memory across trials. Take it as the minimal write-back loop, and as evidence
that even short self-written notes improve task success. Be careful: the
repository moved (the PDF cites noahshinn024/reflexion, now a 404; live code
is at https://github.com/noahshinn/reflexion), and there is no memory hygiene
of any kind.

**Generative Agents (arXiv 2304.03442).** Memory stream scored by
recency/importance/relevance plus periodic reflection synthesis. Take the
scoring-tuple idea for Folio retrieval ranking. Be careful: importance scores
are self-assigned by the model, which is an attack surface, not a control.

**MemoryBank (arXiv 2305.10250).** Ebbinghaus forgetting-curve updates plus a
companion demo with released LoRA checkpoints. Take the forgetting/refresh
policy as the starting point for eviction (lane 8's territory, but the
mechanism lives here). Be careful: forgetting by time-decay can silently drop
exactly the rare safety-relevant memories; decay must be importance-aware.

**Memory-mechanism survey (arXiv 2404.13501).** Taxonomy of agent memory
mechanisms with a companion repo. Useful as the chaining index for anything
this lane missed. Careful: surveys age fast; half its categories predate the
2025 memory-attack wave.

**INMS memory sharing (arXiv 2404.09982).** Protocol for sharing memory across
agents. Relevant only as a warning: shared Folio pools multiply every
poisoning result below by the number of readers. Keep Folio pools per-principal
until a sharing design with provenance exists.

**MINJA (arXiv 2503.03704).** Query-only memory injection: bridging steps plus
progressive shortening implant malicious records with no direct memory access
(98.2% injection, 76.8% attack success). This is the attack MelodyScribe's
Folio gate must defeat first, because our ingest path (a small model filing
paragraphs) is exactly a query-only writer. Be careful: the released repo is
small (37 stars) but the technique needs no code reuse to replicate.

**AgentPoison (arXiv 2407.12784).** Optimized backdoor triggers mapped to an
isolated embedding region; >=80% ASR at <0.1% poison rate, triggers transfer
across embedders including black-box ones. Lesson: triggers survive as
retrieval attractors even when the generator is clean, so Folio admission must
inspect embedding-space behavior (near-duplicate/novelty checks), not just
text. Note the repo moved from BillChan226/AgentPoison (as cited in the paper)
to https://github.com/AI-secure/AgentPoison.

**PoisonedRAG (arXiv 2402.07867).** Formalizes the retrieval condition plus
generation condition for poison texts; 5 injected texts per question reach ~97%
ASR in databases of millions, and tested defenses (paraphrasing, perplexity
filtering) fail. Directly applicable: a Folio is a small RAG database, so the
same two conditions govern attacks on it.

**Indirect prompt injection, Greshake et al. (arXiv 2302.12173).** The founding
taxonomy: retrieved content as unsigned code execution, including persistent
cross-session compromise through agent memory. Every Folio read is this threat
model. Be careful: 2023-era demos, but the taxonomy (exfiltration, worming,
ecosystem contamination) still covers the Folio threat surface.

**Prompt-injection survey, Liu et al. (arXiv 2306.05499).** Systematic analysis
of injection against LLM-integrated applications. Supporting citation for gate
requirements; no artefact.

**CaMeL (arXiv 2503.18813).** Capability-based isolation: untrusted content
becomes data with explicit capabilities, never instructions. This is the design
pattern the Folio gate should copy: Folio contents (model-written) must enter
the frontier model's context as data with a capability tag, while only the
human-authored skill carries instruction privilege. Be careful: the authors
state the released code is an unmaintained research artifact that "might not
be fully secure"; adopt the architecture, not the code.

**Signed-Prompt (arXiv 2401.07612).** Role-based signed instructions as a
lightweight authorized-write precedent for the human tier of Folios. Single
author, no artefact; take the concept (signed human tier), not the scheme.

**Episodic-memory risks, DeChant (arXiv 2501.11739, IEEE SaTML 2025).**
Enumerates deception, retention, situational-awareness, and unpredictability
risks of agent episodic memory, and proposes principles including that agents
must not be able to add, delete, or change their own memories afterward.
Directly supports the Folio gate's append-only/agent-uneditable rule. Single
author position paper; principles are argued, not evaluated.

**Agent Skills specification (agentskills.io; https://github.com/anthropics/skills).**
The open SKILL.md folder standard with name/description metadata and
progressive disclosure (discovery with metadata only, activation reads full
instructions, execution runs bundled code). Adopt this exact shape for Folios:
it is what frontier tooling already consumes, and progressive disclosure is
the cost control for serving frontier models. Be careful: the standard has no
integrity, provenance, or privilege story, which is precisely the gap the
Folio gate must fill; also note the canonical spec repo is
agentskills/agentskills while skill content lives at anthropics/skills.

## (b) Refutations

1. "Self-written memory can be trusted once it helps on benchmarks." Refuted
   by MINJA (2503.03704): helpful-looking records implanted through normal
   interaction steer later queries; utility and integrity are independent axes.
2. "Output-side filters (paraphrase, perplexity) are sufficient memory
   hygiene." Refuted by PoisonedRAG (2402.07867), which evaluated both and
   found them insufficient.
3. "Prompt-level guardrails around a frontier reader are enough." Refuted by
   Greshake et al. (2302.12173): no effective mitigations existed for
   retrieval-driven compromise, and the attack persists across sessions via
   memory.
4. "Small/rare poison fractions are negligible." Refuted by AgentPoison
   (2407.12784): <0.1% poison rate with >=80% ASR and transferred triggers.
5. Implicit "the agent may freely rewrite its own memory." Contested by
   DeChant (2501.11739), whose non-editability principle for agent memories is
   the safer default for Folios.

## (c) Unresolved ledger

- BadChain: recalled id 2405.04619 resolves to an unrelated physics paper;
  genuine id never established. Unverifiable.
- MemFS-style file memory: no primary paper located; term collides with the
  JS memfs library. Unverifiable.
- OpenAI instruction-hierarchy defenses: secondary (blog/docs) only.
- Progent-class tool policies: id/repo not verified from memory. Unverifiable.
- 2026 preprints (MAFIA, transferable indirect poisoning, untrusted-to-trusted
  memory studies, sleeper-memory attacks): listing titles only, papers unopened.
- LearnAct / EvoAgent / WorkflowLLM: named but never verified.

## (d) Security findings: Folio-gate requirements

- R1 (MINJA): treat every model-written Folio entry as untrusted input;
  require provenance (which paragraph, which model, which run) on each entry.
- R2 (AgentPoison): admission screening must include embedding-space checks
  (novelty/isolation analysis), not text inspection alone; triggers transfer
  across embedders.
- R3 (PoisonedRAG): evaluate candidate entries against both conditions:
  would this entry be retrieved for unrelated queries, and would it steer
  generation if retrieved.
- R4 (Greshake): Folio reads are code-execution-equivalent; sandbox the
  model's own skills and never merge them into the human-authored skill's
  privilege tier.
- R5 (CaMeL): architect the gate as capability separation (data vs
  instructions), not as a text filter; adopt the pattern, not the unmaintained
  code.
- R6 (MINJA PSS): rate-limit and audit memory writes per principal;
  progressive multi-query implantation must be detectable in the write log.
- R7 (DeChant): Folios append-only from the agent's perspective; the agent
  cannot edit or delete entries, only the revise pass (with human-tier
  authorization) can.
- R8 (PoisonedRAG): do not rely on paraphrasing or perplexity filtering as
  the gate; they were measured and failed.
