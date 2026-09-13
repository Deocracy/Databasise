# Lane 5 findings: Real-time co-processor next to a frontier model

Scope: harnesses where a small model taps a frontier model's streaming output and stores
from it, and where stored information is injected back (turn boundary, tool-call boundary,
or mid-stream); what the vendor streaming/tool-use APIs, MCP sampling, and server-side
context editing actually allow; anticipatory retrieval; small-assists-large collaboration;
measured latency budgets. 19 papers admitted (PDFs in `papers/`), 7 primary doc/repo
sources admitted, 10 candidates abstained (see inventory.tsv and §4).

## 1. Admitted items

### Anticipatory and need-driven retrieval

**FLARE — Active Retrieval Augmented Generation (arXiv:2305.06983, EMNLP 2023,
https://github.com/jzbjyb/FLARE, 668 stars, MIT).** Forward-looking active retrieval:
draft the upcoming sentence, use it as the retrieval query, and regenerate the sentence
from retrieved documents when it contains low-confidence tokens; evaluated on 4 long-form
knowledge-intensive tasks with superior or competitive results. Take: this is the
reference shape for MelodyScribe's prefetch path — a cheap draft (the small model's own
continuation or the frontier stream prefix) becomes the query *before* the fact is
needed, and regeneration is conditional on a confidence signal. Caution: the
low-confidence trigger is token-probability based; under grammar-constrained decoding
(spike 010: grammar filtering is already the ingest bottleneck) the trigger must be
computed from the same single forward pass, not a second scoring run.

**DRAGIN — Dynamic Retrieval Augmented Generation based on the Information Needs of
Large Language Models (arXiv:2403.10081; repo states ACL 2024 Long Paper Oral,
https://github.com/oneal2000/DRAGIN, 191 stars, Apache-2.0).** Decides *when* to retrieve
from real-time signals (not static rules) and *what* to retrieve by formulating the query
from the model's information need across the whole context, not just the last sentence;
superior on all 4 evaluated knowledge-intensive generation datasets. Take: the harness,
not the model, should own the retrieve-now decision and the query constructor, and the
query should attend over the full Score section plus the frontier stream prefix. Caution:
DRAGIN's attention-based query formulation assumes access to the generator's attention
weights — with a frontier API behind a seam, MelodyScribe must approximate need from
streamed text (entities, dates, unresolved references) rather than logits.

**Self-RAG — Learning to Retrieve, Generate, and Critique through Self-Reflection
(arXiv:2310.11511).** Trains reflection tokens so one model adaptively retrieves
on-demand and critiques its own generations; 7B/13B variants beat ChatGPT and
retrieval-augmented Llama2-chat on open-domain QA, reasoning, and fact verification, with
citation-accuracy gains on long-form generation. Take: gate tokens (retrieve / relevant /
supported) are the mechanism for "the model says which store each piece goes to" — the
harness executes retrieval only when the gate fires, which bounds cost. Caution: gates
are learned behaviors that need fine-tuning to be reliable (consistent with spike 003:
routing accuracy is flat before fine-tuning); do not trust zero-shot gate tokens from
the 2B model.

### Interleaved reasoning, search, and tools

**Search-R1 — Training LLMs to Reason and Leverage Search Engines with Reinforcement
Learning (arXiv:2503.09516, https://github.com/PeterGriffinJin/Search-R1, 5413 stars,
Apache-2.0).** Multi-turn think-then-search trajectories learned by outcome RL with
retrieved-token masking for stable training; +41% (Qwen2.5-7B) and +20% (Qwen2.5-3B) over
RAG baselines on seven QA datasets. Take: retrieved tokens must be masked out of any
policy-gradient update (they are environment observations, not model actions) — the same
discipline applies if MelodyScribe ever fine-tunes on harness trajectories (lane 10).
Caution: outcome-only rewards train the *invocation policy*, not store routing; the
paper's loop is single-store web search, so it says nothing about which store to hit.

**Search-o1 — Agentic Search-Enhanced Large Reasoning Models (arXiv:2501.05366; repo
states EMNLP 2025, https://github.com/sunnynexus/Search-o1, 1244 stars, MIT).** Agentic
search inside long reasoning chains plus a separate Reason-in-Documents module that
denoises retrieved documents *before* they enter the reasoning flow. Take: MelodyScribe
should copy the two-stage shape — a small-model Reason-in-Documents pass that compresses
and cites retrieved evidence before anything is injected into the frontier context, so
injection never carries raw retrieved noise. Caution: the extra module adds a full
inference hop on the critical path; budget it against the prefill rate (spike 002:
~3.7k tok/s) or move it off the injection path into sleep-time.

**ReTool — Reinforcement Learning for Strategic Tool Use in LLMs (arXiv:2504.11536).**
Real-time code execution interleaved inside natural-language reasoning, with the
invocation policy discovered by RL from outcome rewards (cold-start synthetic traces +
RL refinement); 32B reaches 67% AIME with 400 training steps vs 40% for a text-only RL
baseline at 1080 steps, 72.5% in extended settings. Take: tool-call boundaries are
trainable decision points — the harness should log every boundary (state, call, result)
as a trajectory for later reward use. Caution: code-execution traces; the transfer to
memory-store calls (non-verifiable by execution) is unproven.

**ToRL — Scaling Tool-Integrated RL (arXiv:2503.23383).** Outcome-RL discovery of
autonomous tool use with emergent strategic invocation, self-regulation of ineffective
calls, and dynamic compute/analysis switching (ToRL-7B: 43.3% AIME24, +14% over RL
without tools). Take: supports the harness-first thesis — even invocation *strategy* can
be left to RL once the tool boundary exists; design the boundary (idempotent op keys,
Proof verdicts as observations) before training the policy. Caution: same
single-tool-class caveat as ReTool; no multi-store routing evidence.

### Small-drafts, large-verifies collaboration

**Speculative RAG — Enhancing Retrieval Augmented Generation through Drafting
(arXiv:2407.08223, ICLR 2025).** A small specialist drafts multiple RAG answers in
parallel; a larger generalist verifies and selects. Take: this is the canonical
small-next-to-large division of labor for MelodyScribe — the 2B model proposes
(store-routed ops, draft payloads), the frontier model disposes; parallelism of drafts
maps directly onto MelodyScribe's embed slots. Caution: verification by the large model
costs frontier tokens; the harness must pre-filter drafts with Proof so the frontier
verifies few, high-precision candidates.

**Co-LLM — Learning to Decode Collaboratively with Multiple Language Models
(arXiv:2403.03870, https://github.com/clinicalml/co-llm, 130 stars).** Token-level
deferral between a generalist base model and domain assistant models, learned as a latent
variable by marginal likelihood with no direct supervision; joint performance exceeds
each model alone, with interpretable patterns (e.g. template-filling). Take: deferral
can be learned without token-level labels — relevant if MelodyScribe ever learns
frontier-vs-local routing from outcome data alone. Caution: joint training of both
sides; with a frozen API frontier model only the local side's deferral head is
trainable, which the paper does not isolate.

**Contrastive Decoding (arXiv:2210.15097, ACL 2023 long paper).** Expert-minus-amateur
logit arithmetic under a plausibility constraint; zero training; demonstrated with
OPT-13B vs OPT-125M. **Emulated Fine-Tuning (arXiv:2310.12962).** Test-time logit
arithmetic mixing pre-train/fine-tune scales (small-tuned − small-base + large-base),
enabling trait adjustment without retraining. Take: both give MelodyScribe a fallback
steering channel that needs no frontier cooperation — bias the local model's own
decoding toward store-relevant or trait-desired continuations. Caution: both need logit
access on both models; inapplicable to steering the frontier API itself, and the
plausibility constraint must be re-tuned under grammar decoding.

**Speculative Decoding (arXiv:2211.17192, ICML 2023 Oral) and Speculative Sampling
(arXiv:2302.01318).** Draft-then-verify exact decoding: 2–3x on T5-XXL with identical
outputs (Leviathan et al.), 2–2.5x on 70B Chinchilla with distribution preserved (Chen
et al.). Take: the measured latency budget for any draft-verify sidecar — MelodyScribe's
local draft + Proof verify loop should be benchmarked against this 2–3x band, and the
rejection-sampling formulation is the correct way to keep a verifier honest. Caution:
both papers verify tokens of one sequence, not memory ops; mapping accept/reject onto
Proof verdicts needs its own calibration experiment.

### Sleep-time, memory architecture, and cost

**Sleep-time Compute (arXiv:2504.13171, Letta authors).** Think offline about contexts
before queries arrive: ~5x less test-time compute at equal accuracy on Stateful
GSM-Symbolic and Stateful AIME, up to +13%/+18% accuracy from scaling sleep-time, 2.5x
amortized cost per query over related queries, efficacy correlated with query
predictability, plus a SWE-task case study. Take: the direct license for MelodyScribe's
idle cycles — precompute section embeddings, entity/relation candidates, and Folio
summaries for predictable frontier queries (recurring meetings, active documents);
amortize across turns on the same context. Caution: gains depend on predictability;
unpredictable streams get nothing — meter hit rate and fall back to reactive retrieval.

**Hindsight — Building Agent Memory that Retains, Recalls, and Reflects
(arXiv:2512.12818).** Memory as a structured substrate in four networks (world facts,
agent experiences, entity summaries, evolving beliefs) with three operations
(retain, recall, reflect); conversational streams incrementally become a queryable bank
while a reflection layer answers and updates traceably; evaluated on LongMemEval and
LoCoMo with an open 20B model. Take: the retain/recall/reflect split maps onto
MelodyScribe's ingest/recall/learning-graph stages, and the evidence-vs-inference
separation is the right invariant for Proof. Caution: Dec 2025 paper, no independent
replication visible; the four-network schema is heavier than v0.1 needs — adopt the
operations, defer the full schema.

**MemGPT — Towards LLMs as Operating Systems (arXiv:2310.08560; lineage continues at
https://github.com/letta-ai/letta, 24.7k stars, Apache-2.0).** Virtual context
management across memory tiers with interrupts for control flow, evaluated on document
analysis beyond the context window and multi-session chat with remembering/reflecting
agents. Take: interrupts are the precedent for MelodyScribe waking on frontier-stream
events (tool-call boundaries, turn ends) rather than polling; tiering (working vs
archival) matches Score-window vs stores. Caution: function-call-driven paging assumes
a cooperative model; a frontier API will not call MelodyScribe's functions — the
harness must drive paging itself from stream observations.

**Llama Guard — LLM-based Input-Output Safeguard for Human-AI Conversations
(arXiv:2312.06674).** Llama2-7B instruction-tuned as a prompt/response classifier with
a customizable safety taxonomy; matches or exceeds existing moderation tools on the
OpenAI Moderation Evaluation set and ToxicChat. Take: the reference design for a small
classifier riding alongside a large generator — MelodyScribe's Proof validator and any
store-admission gate should be shaped like this (small, fast, taxonomy-driven), not
like a second generator. Caution: the paper contains no streaming-deployment
evaluation; per-token incremental classification latency is unmeasured — do not claim
mid-stream redaction on this basis (see abstain).

**Total Recall at What Cost? — Benchmarking the Serving Cost of Agentic Memory Systems
(arXiv:2608.11879).** Three memory systems (Mem0, Hindsight, Mastra Observational
Memory) vs rolling-window vs full-transcript resubmission, two backbones, to 400 turns,
cost paired with accuracy on 665 LoCoMo questions: cost is driven by internal memory
behavior (length-based regression misses by 18–69%), break-even vs full transcript
ranges from tens of turns to never within 400, accuracy spans 21–54%, backbone choice
drives cost as much as system choice. Take: the only measured serving-cost budget in
the lane — MelodyScribe needs the same break-even analysis (memory vs full-Score
resubmission) before enabling always-on storing; gate bulk ingest behind it. Caution:
conversational memory systems, not multi-store harness; absolute numbers will not
transfer, only the methodology.

**Hindsight Memory-PRM (arXiv:2608.29605).** Memory-op supervision from machine-readable
audit trails (retrieval hits, answer-time citations): offline operation-conditioned
utility critic plus online deletion-and-reanswer intervention credit, no human labels,
no Monte-Carlo replay; a local 8B policy reaches 77.5% LoCoMo (vs 65.1% API teacher)
at one-eighth Mem0's context, 79.0% LongMemEval. Take: retrieval hits and Proof
verdicts are free reward signals — log them as the training substrate for admission
and routing policies (lane 10). Caution: credit is computed under a fixed reader;
co-design with the harness (lane 10's brief) before treating it as a reward.

### Vendor APIs and protocol (primary doc sources)

**Anthropic — Streaming, fine-grained tool streaming, context editing, prompt caching
(https://platform.claude.com/docs/en/build-with-claude/streaming,
/agents-and-tools/tool-use/fine-grained-tool-streaming,
/build-with-claude/context-editing, /build-with-claude/prompt-caching).** SSE event
flow (message_start, content_block_start/delta/stop with text_delta and
input_json_delta partial JSON, message_delta, message_stop); tool execution is a
client-driven round trip — no mid-stream injection. `eager_input_streaming` streams
unvalidated input fragments earlier at the cost of possibly-invalid JSON (accumulate,
guard the parse, return INVALID_JSON wrapper with is_error). Server-side
`context_management` edits (beta `context-management-2025-06-27`:
`clear_tool_uses_20250919`, `clear_thinking_20251015`) apply per-request before the
model runs — configured editing, not live mutation. Prompt caching pins
`cache_control` breakpoints over the tools→system→messages prefix (5-min default,
1-hour TTL, 20-block lookback, ~0.1x read pricing). Take: tap the SSE stream for
storage; inject only via the next request; put the stable Score/skill prefix behind a
cache breakpoint; use eager streaming on the harness's own tools to cut time-to-first-op.

**OpenAI — Responses streaming + function calling
(https://developers.openai.com/api/docs/guides/streaming-responses,
.../guides/function-calling).** Semantic SSE events
(response.output_text.delta, response.output_item.added,
response.function_call_arguments.delta/done, response.completed); the tool loop is:
second request carrying function_call_output, chained with previous_response_id; strict
mode and allowed_tools constrain the surface. Same verdict as Anthropic: fully
observable stream, injection only at the next request. Take: accumulate argument deltas
per output_index exactly as documented; keep the tool surface under ~20 functions.

**OpenAI — Realtime API
(https://developers.openai.com/api/docs/guides/realtime-conversations).** Stateful
60-minute sessions over WebSocket/WebRTC: session.update accepted anytime (instructions
updatable mid-session), conversation.item.create plus conversation.item.truncate for
interruption handling, response.create with conversation:none for out-of-band responses
that do not pollute the default conversation, custom input arrays per response, VAD
with create_response=false for moderation/RAG gating, and function calling with
streamed argument deltas. Take: this is the closest any vendor API comes to the
co-processor pattern — OOB responses are the sanctioned sidecar-compute channel and
truncate-then-continue is the sanctioned mid-stream steering primitive. Caution:
voice-session oriented; text co-processing inherits the pattern, not the SLA.

**Gemini — Interactions streaming, function calling, implicit caching (ai.google.dev
Gemini API docs, fetched via curl+extract).** stream=true yields SSE step.delta events
(REST alt=sse); functions are client-executed with results returned to the model —
same turn/tool-boundary-only verdict; previous_interaction_id gives server-side
conversation state across turns; implicit context caching is automatic with per-model
minima (Flash 4,096; 2.5 series 2,048 tokens) reported via usage.total_cached_tokens.
Take: server-side interaction state plus automatic prefix caching lowers the cost of
the inject-next-turn loop; place stable context first to maximize implicit hits.
Caution: docs are in migration (Interactions API superseding generateContent);
ai.google.dev blocked the markdown fetcher so fidelity is lower — re-verify endpoint
names before building.

**MCP sampling (specification 2025-06-18, client/sampling.mdx, fetched verbatim from
the spec repo).** sampling/createMessage flows server→client; the client declares the
sampling capability, selects the model from hints plus cost/speed/intelligence
priorities, and SHOULD keep a human in the loop with approve/edit/review; single
request-response, no streaming. Take: sampling is how MelodyScribe-as-server asks a
host for a completion — it is not a tap, not a subscription, and not an injection
channel. Caution: any design where MelodyScribe steers the frontier through sampling
inverts the protocol's trust model; keep sampling for host-assisted chores only.

### Deployed memory harnesses (primary repo sources)

**Memori (https://github.com/MemoriLabs/Memori, 16,694 stars, pushed 2026-09-03,
Apache-2.0 LICENSE file).** "Memory from what agents do, not just what they say":
LLM/datastore/framework-agnostic layer turning agent execution and conversation into
structured persistent state, with Python/TS SDKs and cloud plus self-hosted deploy.
Take: the existence proof that storing-from-the-stream is productizable as a
model-agnostic layer, and the agnostic posture matches the Databasise contract (no
modality-specific seam tools). Caution: vendor benchmark graphics are primary only
for what the vendor reports; the "conscious vs raw" memory claims were not
independently verified here.

**Letta (https://github.com/letta-ai/letta, 24.7k stars, 2.6k forks, Apache-2.0).**
Stateful-agent platform, f.k.a. MemGPT; active development moved to letta-code with
terminal UI, app server, channels, and SDKs. Take: the living continuation of the
MemGPT lineage and the institutional home of sleep-time compute (shared authors) —
track its sleep-time integration for the offline-precompute pattern. Caution: repo
restructured mid-2026 (archive branch holds V1); pin to letta-code paths, not the
retired server layout.

## 2. Refutations (of claims in or behind the brief)

**R1 — Refuted: a sidecar can inject into the frontier context mid-stream.** None of
the three vendor text APIs permits mutating an in-flight generation: Anthropic, OpenAI
Responses, and Gemini all expose the stream as read-only deltas and accept new context
only in a subsequent request (Anthropic streaming + OpenAI function-calling + Gemini
function-calling docs). Anthropic's server-side context_management edits apply
per-request before the model runs; MCP sampling is single-shot with no streaming.
The brief's "at turn boundaries, at tool-call boundaries, or mid-stream" collapses to:
turn and tool-call boundaries only. The nearest supported primitive is OpenAI Realtime's
truncate-then-new-response, which cancels rather than edits, and is voice-session
oriented.

**R2 — Refuted: MCP sampling gives MelodyScribe a tap into frontier generation.** The
sampling direction is server-requests, client-disposes: the client picks the model,
SHOULD require human approval, and returns one message (MCP sampling spec). A
MelodyScribe-as-MCP-server cannot observe the frontier stream through sampling, cannot
subscribe to it, and cannot push into it. Sampling is an agentic-subtask channel, not
a co-processor channel.

**R3 — Refuted (bounded): always-on storing from the frontier stream is
self-evidently worth it.** Total Recall at What Cost (arXiv:2608.11879) measures memory
systems that never break even against full-transcript resubmission within 400 turns,
with cost driven by internal memory behavior (18–69% regression miss) rather than
conversation length. Storing everything the frontier says has a measured cost ceiling;
bulk ingest needs a break-even gate, not a default-on switch.

## 3. Unresolved ledger

1. Streaming guardrail sidecars: no primary source found that specifies incremental
   classification semantics or latency over a live stream (NeMo docs 404, README
   silent, guardrails-ai README silent). Llama Guard is admitted without streaming
   claims; mid-stream redaction latency is unmeasured.
2. A paper literally named "Proxy Tuning": arXiv quoted searches did not surface one;
   Emulated Fine-Tuning admitted as the verified proxy-arithmetic referent. If the
   brief meant a different paper, its ID is still unknown.
3. Code URLs for Self-RAG, ReTool, ToRL, Speculative RAG, contrastive decoding,
   speculative decoding/sampling, Llama Guard weights repo, Hindsight, Total Recall,
   and Memory-PRM: absent from abs pages or hrefs unextracted before GitHub API rate
   limit. Artefact claims rest on abs text ("code available") where stated.
4. Exact Hindsight benchmark numbers: the abs-page extract truncated before the
   figures; only the benchmark names (LongMemEval, LoCoMo) and the 20B open model are
   recorded. Read the downloaded PDF before citing numbers.
5. Gemini endpoint names: the Interactions API is mid-migration and ai.google.dev
   blocked structured fetching; re-verify stream/previous_interaction_id field names
   against the live reference before building.
6. Small-model recall-agent numbers on LoCoMo/LongMemEval/BRIGHT for the co-processor
   configuration specifically (small storing + frontier answering) were not found;
   Hindsight and Memory-PRM report single-system numbers. The draft-verify split has
   no end-to-end memory benchmark.

## 4. Security findings (stated as requirements)

1. The harness MUST treat the frontier stream as untrusted input: every stored item
   must carry its source span plus stream offset (item id, response id), because
   truncation (Realtime truncate semantics) means stored text can differ from what
   the frontier model actually consumed.
2. Persistent memory MUST have an admission gate with provenance: Hindsight's
   evidence/inference separation and Memory-PRM's audit-trail credit are the
   patterns; mining the stream without them replicates the MINJA/AgentPoison attack
   surface (persistent memory injection — lane 8 owns the taxonomy, lane 5 requires
   the gate).
3. Guardrail/sidecar outputs MUST travel out-of-band (the Realtime
   conversation:none pattern) and MUST be labeled as harness-generated when
   assembled into any frontier-bound payload; in-band unmarked injection lets a
   compromised sidecar speak as the user.
4. MCP sampling requests issued by MelodyScribe MUST be human-approval-gated in
   production (the spec's SHOULD), since sampling exfiltrates harness context to a
   client-chosen model.
5. Recall payloads assembled for the frontier MUST contain only Proof-passed ops;
   speculative or unverified drafts (Speculative RAG pattern) must be demoted to
   cited candidates, never asserted facts.

## 5. Harness implications

1. Prefetch with drafts: use the small model's own continuation (or the frontier
   stream prefix) as the retrieval query and regenerate conditionally on a
   confidence signal, in one forward pass (FLARE, arXiv:2305.06983).
2. Let the harness own the retrieve-now decision and build the query from the whole
   section plus stream prefix, approximating information need from text signals
   since frontier logits are unavailable (DRAGIN, arXiv:2403.10081).
3. Tap streams read-only and inject only at turn or tool-call boundaries via a new
   request; never design for mid-stream mutation, which no text API supports
   (Anthropic/OpenAI/Gemini streaming and tool-use docs, MCP sampling spec).
4. Run sidecar classification, summarization, and Proof validation out-of-band so
   harness compute never pollutes the frontier conversation (OpenAI Realtime
   conversation:none pattern).
5. Split labor as small-drafts-frontier-disposes with Proof pre-filtering so the
   frontier verifies few high-precision candidates (Speculative RAG,
   arXiv:2407.08223), and gate retrieval behind learned on-demand tokens once
   fine-tuned (Self-RAG, arXiv:2310.11511).
6. Compress and cite retrieved evidence in a small Reason-in-Documents pass before
   anything enters the frontier context (Search-o1, arXiv:2501.05366).
7. Spend idle cycles on sleep-time precompute for predictable queries (embeddings,
   entity candidates, Folio summaries) and amortize across turns, metering hit
   rate with reactive fallback (Sleep-time Compute, arXiv:2504.13171).
8. Gate always-on storing behind a measured break-even analysis against
   full-context resubmission, since memory serving can cost more than no memory
   (Total Recall, arXiv:2608.11879).
9. Log retrieval hits, Proof verdicts, and boundary trajectories as free reward
   signals for future admission and routing policies, with memory organized as
   versioned, evidence-separated substrate (Hindsight Memory-PRM,
   arXiv:2608.29605; Hindsight, arXiv:2512.12818).
10. Keep a logit-arithmetic steering fallback (expert-minus-amateur with a
    plausibility guard) for the local model only, never for the frontier API
    (Contrastive Decoding, arXiv:2210.15097; Emulated Fine-Tuning,
    arXiv:2310.12962).
