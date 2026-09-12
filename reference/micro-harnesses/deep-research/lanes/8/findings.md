# Lane 8 findings: Memory consolidation and refinement loops, and their failure modes

Scope: sleep-time/offline consolidation, reflection-to-learnings, memory evolution that rewrites
older entries, documented self-refinement degradation, forgetting and eviction policies.
Screened 40 candidates; 34 admitted, 2 refute, 4 abstain. All admitted items verified at the
arXiv abs page plus the paper PDF; repos verified via paper links and HTTP existence checks.

## (a) Admitted items

**Sleep-time Compute (arXiv 2504.13171).** Precomputes reasoning over known context offline
("sleep time") into reusable state so test-time queries are answered from consolidated
artifacts instead of recomputed context. MelodyScribe should take the cost model: the revise
pass is sleep-time compute, and its budget should be justified by amortized test-time savings.
Careful: their wins assume predictable future queries; ad-hoc corpora amortize worse.

**Language Models Need Sleep (arXiv 2606.03979).** Trains the LM itself to self-modify and
consolidate memories during a sleep phase rather than bolting on a separate consolidator.
Take: the revise pass need not be a second system — a LoRA trained to rewrite Folios/graph
edges is the same pattern at MelodyScribe scale. Careful: self-modifying weights add a
safety surface; prefer self-modifying files first.

**A-MEM (arXiv 2502.12110).** Zettelkasten-style agentic memory where each note links to
neighbors and an evolution step rewrites older notes as the store grows. Take: the link-and-
evolve loop is the closest published analog of MelodyScribe capability 4; copy its
link-generation prompt structure. Careful: evolution without versioning destroys provenance —
keep superseded notes, mark them superseded.

**Mem0 (arXiv 2504.19413; https://github.com/mem0ai/mem0).** Production memory layer doing
extraction, dedup, salience decay and hybrid retrieval at scale (65k stars, Apache-2.0).
Take: its add/update/delete decision schema and decay Scores are directly reusable for the
revise pass. Careful: it is a hosted-product codebase, large; lift the decision prompts, not
the stack.

**MemOS (arXiv 2507.03724; https://github.com/MemTensor/MemOS).** OS abstraction over memory:
MemCube versioned units, lifecycle states (active/decayed/archived), scheduler-driven
promotion. Take: lifecycle states are what the revise pass should implement per item instead
of binary keep/delete. Careful: heavy framework; adopt the state machine, not the runtime.

**Reflexion (arXiv 2303.11366).** Actor-evaluator loop that stores verbal self-reflections as
episodic memory for later trials. Take: the reflection artifact should be stored as data
(verify against the two refutations below before paying for the loop). Careful: gains require
a reliable evaluator signal; an LLM grading itself is the failure case of 2310.01798.

**Generative Agents (arXiv 2304.03442).** Periodic reflection compresses episodes into
higher-level insights; retrieval weights recency, importance and relevance. Take: the
three-factor retrieval score plus scheduled reflection is a proven consolidation recipe.
Careful: reflection frequency is a cost knob; reflect on schedule, not per paragraph.

**MemoryBank (arXiv 2305.10250).** Ebbinghaus forgetting-curve updating with nightly
consolidation of long-term persona memory. Take: time-decayed salience with a consolidation
pass is the simplest defensible revise policy. Careful: fixed decay curves underfit bursty
technical content; make decay per-store.

**Self-Refine (arXiv 2303.17651).** Same-model generate-feedback-refine iterations. Take:
feedback-then-rewrite is the cheapest revise operator for Folio polishing. Careful: see the
refutations — iteration without external signal stalls or degrades at small scale.

**ExpeL (arXiv 2308.10144).** Distills success/failure trajectories into transferable
insights and rules reused across tasks. Take: the revise pass should mine failed retrievals,
not just successes, into Folio updates. Careful: extracted rules overfit the task
distribution; version them and measure transfer.

**CRITIC (arXiv 2305.11738).** Self-correction succeeds when critiques come from external
tools (search, interpreters), not from the model itself. Take: gate every revise rewrite on
a tool-verifiable check (retrieval hit-rate, schema validity, re-embedding stability).
Careful: tool calls per item make the revise pass expensive; batch verification.

**Titans (arXiv 2501.00663).** Test-time neural memory updated by gradient "surprise".
Take: surprise-gated writes (only consolidate what the model mispredicted) as an admission
policy for the revise pass. Careful: needs training machinery; use the gating idea with
file writes, not the architecture.

**MemGPT/Letta (arXiv 2310.08560; https://github.com/letta-ai/letta).** OS-paged memory with
explicit eviction, function-call memory management and archival recall. Take: paging plus
explicit eviction functions is the right interface for bounded-context revise passes.
Careful: function-call-driven paging adds latency per decision; batch it.

**Self-RAG (arXiv 2310.11511).** Trained reflection tokens control retrieval and critique
behavior end to end. Take: special control tokens (or control headers in the Score format)
can gate consolidate-vs-skip decisions in one forward pass. Careful: official code not
found; reimplementation cost is real.

**Retain or Consolidate (arXiv 2607.17545).** Chooses retain-vs-consolidate operators as a
function of memory budget. Take: this is the revise-pass scheduler MelodyScribe needs —
budget-aware operator selection, not one fixed policy. Careful: single author-cluster paper
from 2026; replicate the operator comparison on our corpus before trusting the tradeoff.

**Learning to Forget (arXiv 2603.14517).** Sleep-inspired consolidation that resolves
proactive interference by forgetting blocking memories. Take: forgetting is a first-class
revise operator aimed at interference, not just capacity. Careful: single-author 2026 paper;
validate interference metrics on our stores.

**TRUSTMEM (arXiv 2606.25161).** Trust-scores content before consolidation so untrustworthy
material never enters long-term memory. Take: a trust gate before Folio promotion is
mandatory given Folios are executed as skills. Careful: trust scorer quality bounds the
whole scheme; calibrate it.

**TiMem (arXiv 2601.02845; https://github.com/TiMEM-AI/timem).** Temporal-hierarchical
consolidation with time-aware indexing for long conversations. Take: temporal validity
windows on graph edges and Folios (backed by per-item timestamps). Careful: new repo,
maturity unknown.

**Mela (arXiv 2605.10537; https://github.com/Musubi-ai/Mela).** Test-time consolidation
operator from a transformation hypothesis of memory. Take: a second independent
consolidation-operator implementation to compare against Retain-or-Consolidate. Careful:
single-author 2026 work; treat as experimental.

**StreamingLLM (arXiv 2309.17453).** Attention-sink KV eviction enabling unbounded
streaming. Take: if cached attention states are ever composed (capability 3), sink-plus-
recent eviction is the proven policy. Careful: eviction changes outputs; pair with
quality measurement from lane 2.

**EWC (arXiv 1612.00796).** Fisher-weighted consolidation protecting important weights
against catastrophic forgetting. Take: the classical reference for any claim about
"forgetting" — cite it when the revise pass touches weights (LoRA merge). Careful:
weight-level, not file-level; do not overgeneralize to text memory.

**Who's Harry Potter (arXiv 2310.02238).** Targeted unlearning via relabeled forget-set
fine-tuning. Take: the only verified recipe for deleting knowledge from weights when a
revise pass must truly expunge (not just hide) content. Careful: approximate — verification
of forgetting is itself an open problem.

**Recursive Self-Refinement as Textual Relaxation (arXiv 2607.22653).** Formalizes
recursive self-refinement as relaxation with convergence analysis. Take: a stopping
criterion for revise loops (iterate to fixed point, bound iterations). Careful: 2026 paper,
theory-heavy; check the assumptions match discrete file edits.

**The Sleeping Agent (arXiv 2608.11775).** Measures what gist-based sleep-time compression
loses and why. Take: mandatory caution — consolidation destroys information; measure
recall-before/after every revise policy. Careful: single-author analysis; still the best
counterweight in the admitted set.

**Agent Drift (arXiv 2601.04170).** Quantifies behavioral degradation over extended
multi-agent interaction. Take: track a drift metric across revise generations; roll back
when it rises. Careful: metric generality unproven; define drift on our retrieval tasks.

**SSGM (arXiv 2603.11768).** Governance framework for stability/safety of evolving memory.
Take: stability bounds and review gates around the revise pass. Careful: framework paper,
no code; implement the gates, not the bureaucracy.

**OEP (arXiv 2605.18930).** Poisoning via locally-correct but non-transferable experiences
in self-evolving agents. Take: the revise pass must test transferability, not just local
correctness, before promoting a learning. Careful: attack paper; pair with TRUSTMEM and the
provenance firewall below.

**Provenance firewall (arXiv 2607.29167).** Non-amplification firewall against memory
provenance laundering. Take: provenance tags that survive consolidation, with a no-
amplification rule for low-trust sources. Careful: 2026 paper, no code; design pattern only.

**Hindsight (arXiv 2512.12818; https://github.com/vectorize-io/hindsight).**
Retain-recall-reflect pipeline with an explicit hindsight step (already in our survey; now
verified at primary source). Take: the reflect step design for the revise pass. Careful:
vendor-adjacent repo; treat benchmarks as vendor-reported.

**Mem-alpha (arXiv 2509.25911; https://github.com/wangyu-ustc/Mem-alpha).** RL-learned
memory-construction policy (already in our survey; now verified). Take: the RL recipe for
training the 2B model to decide write/link/skip. Careful: training cost; start from their
released code before designing our own reward.

**LifeAlign (arXiv 2509.17183).** Memory-augmented preference optimization for lifelong
alignment. Take: preference-tune the consolidator against retrieval success, not just
imitation. Careful: alignment framing; relevance to filing is indirect (score 1).

**Function Tokens (arXiv 2510.08203).** Consolidation/retrieval via learned function-token
interface. Take: control-token gating as an alternative to prompt-based revise control.
Careful: no code; relevance indirect (score 1).

**Human-like recall (arXiv 2404.00573).** Recall/consolidation loop modeled on human memory
dynamics. Take: background design vocabulary only. Careful: companion-agent setting, thin
evaluation (score 1).

**MemGAS (arXiv 2505.19549).** Multi-granularity memory association/selection. Take:
selection across granularities as a revise-pass retrieval check. Careful: relevance
indirect (score 1).

## (b) Refutations

**R1 — Unsupervised self-refinement does not reliably help.** Huang et al. (arXiv
2310.01798, abs-verified) report that LLMs cannot self-correct reasoning without external
feedback. Refuted claim: a background revise pass improves the base "by itself." Requirement
that follows: every revise operator must be gated on an external signal (retrieval
hit-rate, tool check, human label) — never pure self-rewrite.

**R2 — Reflection loops lose to sampling at small scale and equal cost.** Mirzaei (arXiv
2607.28576, abs-verified) finds Self-Refine and Reflexion lose to repeated sampling at
equal token cost from 1.5B to 7B. Refuted claim: reflection is worth its tokens for a 2B
model. Requirement: benchmark the revise pass against best-of-N sampling at equal budget
before shipping it; reflection must earn its cost.

## (c) Unresolved ledger

- 2310.09297 (human-memory inference framework): abs-verified only, full text not reviewed;
  mechanism detail unknown.
- H2O KV eviction: could not verify the arXiv id (guessed 2311.13856 resolved to an
  unrelated paper); no primary source opened.
- RMM: name recalled without a source; no fetched page confirms it exists.
- 2310.01417: reached via a wrong recalled id for ExpeL; abs page confirms it is an
  unrelated air-taxi paper. Kept so the misidentification is not repeated.

## (d) Security findings (requirements for the Folio gate)

- **R-SEC1 — Trust-gate every promotion.** No experience, insight, or Folio edit enters
  long-term memory without a trust score (TRUSTMEM, 2606.25161).
- **R-SEC2 — Test transferability, not local correctness.** OEP (2605.18930) shows
  locally-correct learnings can be poison; promote only what improves held-out retrieval.
- **R-SEC3 — Preserve provenance across rewrites.** Provenance must survive consolidation
  with a non-amplification rule for low-trust sources (2607.29167).
- **R-SEC4 — Bound evolution with governance.** Self-evolving memory needs stability gates
  and rollback on drift (SSGM 2603.11768; Agent Drift 2601.04170).
- **R-SEC5 — Gate self-correction on external signal.** Intrinsic self-rewrite without tool
  or retrieval verification is the failure mode (2310.01798; CRITIC 2305.11738 inverts it:
  allow correction only with tool critique).
