# Lane 1 findings: Micro-harness architectures for small models

Scope: what the harness does that the model does not, and which pieces are deterministic code versus model output.
Capability key used in inventory: 1 = ingest routing and constrained emission, 2 = recall and fusion,
3 = thinking control, 4 = caching/parallel/scheduling, 5 = real-time co-processor and harness boundaries.

## Admitted items

**TinyAgent (arXiv:2409.00608, Erdogan et al., EMNLP 2024 Demo).** End-to-end recipe for turning 1.1B and 7B
open models into edge function-callers that beat GPT-4-turbo on the authors' Mac-automation suite: fine-tune on
40k curated cases, plan with the LLMCompiler DAG format, retrieve tools and few-shot examples with ToolRAG, and
quantize for inference. Take: fine-tuning plus retrieval plus harness planning is the proven stack for making a
small model emit reliable ops, matching the rig's spike-003 conclusion that fine-tuning, not scale, is the lever.
Careful: success rates are vendor-reported on the authors' own task suite; the 1.1B model still needs ToolRAG at
inference, so the retriever is load-bearing, not optional.

**LLMCompiler (arXiv:2312.04511, Kim et al., ICML 2024).** Splits orchestration into three parts with crisp
ownership: a planner (model output) that emits a dependency graph of calls, a task-fetching unit and an executor
(deterministic code) that dispatch independent calls in parallel, reporting up to 3.7x latency and 6.7x cost wins
over ReAct. Take: MelodyScribe's op planner should emit a DAG with dependencies and let deterministic code do the
parallel fan-out, replay, and joining; the model must never own scheduling. Careful: gains assume genuinely
independent calls; MelodyScribe ops that share Proof state (offsets, entity identity) need the dependency edges to
be explicit or parallel dispatch will corrupt them.

**Octopus v2 (arXiv:2404.01744, Chen and Li).** A 2B on-device model that replaces RAG-over-tool-docs with
functional tokens: one special token selects the function and reformats arguments, cutting context length ~95%
and claimed 35x latency over Llama-7B-plus-RAG. Take: a single-token op selector plus argument reformatter is the
minimal model-side surface for MelodyScribe; tool descriptions should live in harness-side storage, not in the
prompt. Careful: accuracy-vs-GPT-4 claims are vendor-reported with no independent reproduction found; treat the
mechanism as admitted and the scoreboard as vendor data.

**Octopus v3 (arXiv:2404.11459, Chen and Li).** Pushes the functional-token design under 1B parameters with
text/vision/audio input, running on Raspberry-Pi-class hardware. Take: sub-billion models can carry the op-selection
job if the output vocabulary is constrained to functional tokens, which supports keeping MelodyScribe at 1-2B.
Careful: the evaluation is thin and multimodal; text-only structured emission at MelodyScribe's reliability bar is
not demonstrated here.

**Octopus v4 (arXiv:2404.19296, Chen and Li).** A 3B master node routes each query to the best specialist worker
model via functional tokens, activating only two small models per query for 74.8 MMLU. Take: the router/worker
split is the direct precedent for MelodyScribe-as-router (cheap ingest routing and recall triage on device,
frontier model as worker for hard reasoning). Careful: routing is per-query single-shot with no planner, no
validation, and no state; the cited GitHub repo could not be verified (see abstain row), so only the paper's
mechanism is admitted.

**xLAM (arXiv:2409.03215, Zhang et al., Salesforce).** A 1B-to-8x22B family of action models from one unified,
augmented, synthesized data pipeline; the 1B model beats GPT-3.5-Turbo and larger ones top BFCL over GPT-4
(vendor-reported). Take: unifying diverse action datasets into one format plus DPO alignment transfers across
agent environments, which is evidence for training MelodyScribe's op emitter on a unified multi-store op schema
rather than per-store formats. Careful: all ranking claims are vendor-reported; the paper contributes the data
pipeline insight, not an independently verified scoreboard.

**APIGen (arXiv:2406.18518, Liu et al., NeurIPS 2024 Datasets and Benchmarks).** A data-generation pipeline whose
three hierarchical verifiers (format checker, real execution engine, semantic LLM judge) over 3,673 executable
APIs produced the 60k dataset behind xLAM. Take: this is the closest published analog of Proof — executable
verification plus a semantic judge — and MelodyScribe should copy the layering (cheap deterministic checks first,
model judge last) and the practice of feeding verified outputs back as training seeds. Careful: verification here
is offline and batched; MelodyScribe needs the same checks at real-time ingest latency, which the paper does not cost.

**Hammer (arXiv:2410.04587, Lin et al.).** Diagnoses cross-benchmark instability as models memorizing function and
parameter names, and fixes it with function masking (randomized names at train time) plus 7,500 irrelevance
examples that teach abstention. Take: mask store/entity names during op-emitter fine-tuning so the model reads
descriptions, and add explicit no-op/abstain training so Proof receives fewer bogus ops. Careful: masking ratio
0.33 is tuned to their benchmarks; MelodyScribe must re-tune the ratio against Proof pass rate, not copy it.

**ReAct (arXiv:2210.03629, Yao et al., ICLR 2023).** The canonical interleaved thought/action/observation loop
where the model emits reasoning traces and actions while deterministic harness code owns the environment, parses
actions, and returns observations. Take: the reason-act split is the baseline architecture — model proposes,
harness disposes — and MelodyScribe's Score loop should be framed as ReAct with the action space replaced by typed
store ops. Careful: ReAct re-prompts the full trajectory each step, which is the token-inefficient pattern ReWOO
and the rig's prefix-reuse work both argue against; do not copy its prompt management.

**ReWOO (arXiv:2305.18323, Xu et al.).** Decouples planning from observation: the model writes the whole tool-use
plan up front, then unforking workers execute it without further model calls — 5x token saving, plus offloading
reasoning from 175B to a 7B planner. Take: MelodyScribe's one-forward-pass-per-section design is independently
convergent with ReWOO; keep planning observation-free and push evidence resolution into deterministic code
(offset lookup, exactly as the rig already does). Careful: plans that need mid-course correction on evidence
content cannot adapt; MelodyScribe needs a bounded re-plan path for Proof rejections, which ReWOO lacks.

**Toolformer (arXiv:2302.04761, Schick et al.).** Self-supervised tool-use: candidate API calls are inserted,
executed, and kept only if they reduce language-modeling loss — the harness (executor plus loss gate) decides
admission, not the model. Take: the loss-gated admission principle generalizes to MelodyScribe training: admit
op-emission patterns that improve retrieval/answer metrics, drop the rest. Careful: the gate requires executing
candidate calls during training, which is expensive against five live stores; approximate with offline replay.

**Gorilla (arXiv:2305.15334, Patil et al.).** Fine-tuned LLaMA plus a document retriever for massive API spaces;
retrieval grounds argument generation and absorbs documentation drift without retraining. Take: retriever-in-the-loop
is validated for op-argument grounding, and the APIBench construction is a template for a MelodyScribe op benchmark.
Careful: retrieval happens once up front, so stale or contradictory store state mid-episode is unhandled; MelodyScribe
needs retrieval freshness guarantees the paper does not provide.

**SGLang (arXiv:2312.07104, Zheng et al.).** A frontend language (generation plus parallelism plus control flow
primitives) over a runtime with RadixAttention prefix reuse and compressed finite-state machines for structured
decoding, up to 6.4x throughput. Take: the harness should be a *program* (branches, parallel joins, typed
generations), not a prompt string; radix prefix reuse and FSM-constrained decoding are the mechanisms behind the
rig's settled prefix-reuse and grammar-constrained-ops decisions. Careful: the paper's speedups are on large-model
agent workloads; the rig's own spike-009 numbers (grammar filtering 9x CPU cost) govern MelodyScribe, not SGLang's.

**MiniCPM (arXiv:2404.06395, Hu et al.).** The training recipe (WSD scheduler, wind-tunnel scaling) behind the
1.2B/2.4B models that match 7B-13B behavior and underpin the rig's current 2B model. Take: WSD plus domain
adaptation supports the harness-first plan — the base can be continually adapted to MelodyScribe's op schema
without full retraining. Careful: a pre-training recipe, not a harness; it says nothing about structured emission
reliability, which is where the rig's 30-50% Proof-failure problem lives.

**MiniCPM4 (arXiv:2506.07900, MiniCPM Team).** End-device stack: InfLLM-v2 trainable sparse attention, CPM.cu
inference kernels, 0.5B/8B sizes, hybrid MiniCPM4.1 think/no-think modes, plus reported MCP tool-use and survey
adaptations. Take: sparse attention plus quantized kernels plus a hybrid reasoning switch is the deployment stack to
target for the 16GB card; MCP adaptation is existence proof that a MiniCPM-scale model can be a machine client on a
typed seam. Careful: MCP/survey adaptations are reported inside the vendor tech report with no standalone artefact
verified (see abstain rows); think-mode effects on structured output are lane 4's question, not answered here.

**Phi-4-mini (arXiv:2503.01743, Microsoft).** 3.8B model from synthetic math/code data; Phi-4-Multimodal keeps the
backbone frozen and adds modality LoRA routers. Take: frozen-backbone-plus-routers is the vendor precedent for the
rig's KL-anchored adapter direction (keep op emission alive while adding embedding skill). Careful: almost no
tool-use or harness content; relevance is limited to the adapter-architecture analogy.

**ToolAlpaca (arXiv:2306.05301, Tang et al.).** Multi-agent simulation synthesizes 3,938 tool-use cases over 400+
APIs; fine-tuned 7B/13B models match GPT-3.5 on unseen tools. Take: simulated multi-agent data synthesis is a
workable substitute when real ingest traffic is scarce — directly applicable to bootstrapping MelodyScribe op
training data. Careful: simulated tools are cleaner than the rig's five stores with real contradictions and
temporal mess; generalization numbers will not transfer directly.

**ToolLLM (arXiv:2307.16789, Qin et al.).** ToolBench (16,464 real APIs) plus ToolLLaMA plus a depth-first
decision-tree search over reasoning traces at data time, with a neural API retriever at inference. Take: move
search to data time and keep inference to retrieve-then-emit — the same asymmetry MelodyScribe wants (heavy
offline synthesis, cheap one-pass ingest). Careful: DFSDT inference-time search is the expensive pattern the
harness must avoid at ingest; cite only the data-time/inference-time split.

**Apple AFM (arXiv:2407.21075, Gunter et al.).** 3B on-device model (distilled, pruned, ~3.7-bit palettized) plus
server model, with per-task rank-16 LoRA adapters swapped on the fly and orchestrated as guided generation.
Take: the production existence proof for the whole thesis — tiny on-device model plus swappable adapters plus
server escalation — and the adapter-size arithmetic (tens of MB) bounds MelodyScribe's adapter budget. Careful:
closed weights, no code, no tool-use numbers; only the architectural pattern transfers.

**LFM2 (arXiv:2511.23404, Amini et al.).** Edge-first hybrid conv-attention backbone (2x CPU prefill/decode),
tool-call special tokens in the tokenizer, and LFM2-Nano task specialists for function calling, extraction, and
RAG, shipped for llama.cpp/ExecuTorch/vLLM. Take: tokenizer-level op delimiters plus per-task specialist
variants is convergent with MelodyScribe's `[EMB]` marker plus typed ops; hardware-in-loop architecture search is
the right way to pick the 1-10B operating point. Careful: November 2025, very recent, vendor-reported numbers,
no independent reproduction.

**BFCL (PMLR v267, Patil et al., ICML 2025; proceedings: https://proceedings.mlr.press/v267/patil25a.html ).**
AST-based executable grading of serial, parallel, multi-turn, and stateful function calls; the de-facto standard
the xLAM, Hammer, and APIGen claims are all scored on. Take: score MelodyScribe op emission with AST-exactness
plus execution, not string match — and adopt its multi-turn/stateful categories for Proof-evasion testing. Careful:
BFCL covers generic APIs, not typed-store routing; MelodyScribe needs a store-routing accuracy split BFCL does not
define. (PMLR PDF filed under adapted filename; no arXiv id exists.)

**OpenBMB/MiniCPM repo (https://github.com/OpenBMB/MiniCPM , 10915 stars, Apache-2.0, pushed 2026-09-12).**
Living cookbook plus Agent Skills plus MCP examples around the MiniCPM family. Take: the deployment harness the
brief names — skills-as-markdown-consumed-by-model plus MCP tool surface — verified live and maintained. Careful:
cookbook quality varies by contributor; pin and vendor-review anything lifted.

**llama.cpp (https://github.com/ggml-org/llama.cpp , 128102 stars, MIT, pushed 2026-09-13).** Server README
verified: function-calling/tool-use parsers for many templates including minicpm, `--grammar`/GBNF plus
`json_schema`-to-grammar per-request constrained decoding, Jinja chat templates. Take: the deterministic
constrained-decoding substrate for MelodyScribe's grammar-constrained ops already exists — do not build a
constrainer, configure this one. Careful: grammar enforcement constrains tokens, not semantics; Proof stays
mandatory (a schema-valid op can still cite a fabricated quote).

**smolagents (https://github.com/huggingface/smolagents , 29308 stars, Apache-2.0).** Agents whose actions are
executable code rather than JSON tool calls. Take: the minimal-surface precedent — one expressive primitive beats
a tool zoo — supporting a small, composable MelodyScribe op set over one executor. Careful: code actions need a
sandbox MelodyScribe does not have for arbitrary code; keep ops declarative data, not code, unless sandboxing
(Folios precedent) is extended.

**SGLang runtime (https://github.com/sgl-project/sglang , 35900 stars, Apache-2.0).** Production radix-attention
serving with structured decoding and parallel-generation primitives. Take: the serving layer that makes one-model
embedding-plus-generation plus prefix reuse practical; target its primitives rather than hand-rolled batching.
Careful: operating a full serving runtime on a single 16GB laptop card alongside five stores is unproven in the
cited material; the rig's one-process-plus-asyncio design stays the default until measured otherwise.

**LLMCompiler repo (https://github.com/SqueezeAILab/LLMCompiler , 1881 stars, MIT).** Reference planner plus DAG
plus parallel executor. Take: portable scheduling code for MelodyScribe op batching. Careful: last push
2024-07-10 — stable but aging; check dependency rot before adopting.

**NexusRaven (https://github.com/nexusflowai/NexusRaven , 324 stars, Apache-2.0).** Demonstration-retrieval
augmentation: retrieving query-response example pairs (not docs) lifted success 72 to 94%, and single-turn
zero-shot calling avoids the latency and risk of executing wrong calls to observe them. Take: retrieve
op-emission *examples* per section type at ingest, and prefer single-shot emission plus Proof over
execute-and-observe loops. Careful: no paper, vendor-reported numbers, 13B scale — the example-retrieval
mechanism transfers, the percentages do not.

**huggingface/smollm (https://github.com/huggingface/smollm , 3890 stars, Apache-2.0).** SmolLM3-3B dual-mode
think/no_think instruct model with public training recipe. Take: the open precedent for a harness-controlled
reasoning switch, directly relevant to the thinking question. Careful: no paper; think-mode quality on structured
tool output is unevaluated here (lane 4's problem).

**Hammer repo (https://github.com/MadeAgents/Hammer , 123 stars, Apache-2.0).** Executable function-masking
tuning pipeline plus 7.5k irrelevance dataset. Take: reusable code and negatives for abstention training.
Careful: small community, verify pinned commit behavior before depending on it.

**ShishirPatil/gorilla (https://github.com/ShishirPatil/gorilla , 13019 stars, Apache-2.0).** APIBench plus BFCL
evaluator plus retriever code. Take: reuse the AST evaluator and leaderboard harness for MelodyScribe op scoring.
Careful: generic-API oriented; store-routing splits must be added.

## Refutations

No claim in the brief is directly contradicted by a primary source in this lane. Two cautions that limit how
brief-adjacent claims may be used: (a) Octopus v2/v3/v4, xLAM, TinyAgent, Hammer, and LFM2 performance-vs-frontier
numbers are vendor-reported with no independent reproduction found — they are primary only for "what the vendor
reports" and must not be cited as independent results; (b) three arXiv ids recalled for lane candidates
(2409.13324, 2406.03600, 2311.05390) resolve to unrelated papers on verification, so any prior citation of those
ids for TinyAgent, APIGen, or NexusRaven is a mis-citation corrected in the inventory.

## Unresolved ledger

- MiniCPM4-MCP and MiniCPM4-Survey as standalone artefacts: no paper or repo found; described only inside the
MiniCPM4 report. Reason: could not verify standalone existence.
- NexaAI/octopus-v4 repo: API 404 despite being cited in the paper. Reason: existence unverifiable; HF mirror
not directly verified.
- SmolLM3: no arXiv paper; HF model page license field empty via API. Reason: secondary/vendor sources only,
dependency status unclear.
- Gemma 3n and FunctionGemma: vendor docs/blog only, no peer-reviewed harness content. Reason: secondary only.
- nexusflowai/NexusRaven-V2: exists (418 stars) but license field empty via API. Reason: unclear license;
V1 (Apache-2.0) covers the idea.
- Salesforce xLAM code: no salesforce/xlam GitHub repo (API 404). Reason: distribution is via Hugging Face.
- Semantic Scholar and arXiv listing APIs were rate-limited during this lane, so forward/backward citation
chaining was done via web search plus fetched abs pages instead of the APIs. Reason: transport limits, not
source limits; every admit was still opened at its primary source.
- Real-time injection mid-stream (lane 5's core) has no lane-1 primary source; the closest mechanisms are
Octopus v4 routing and Apple adapter swapping, both per-turn, not mid-stream. Reason: literature gap.

## Security findings (stated as requirements)

- R1 (untrusted tool schemas): function/parameter names and descriptions must be treated as untrusted input;
Hammer (2410.04587) shows models are misled by naming conventions, so the harness shall mask or normalize names
and require decisions from descriptions plus Proof checks before any write.
- R2 (no execute-to-observe at ingest): the harness shall not execute candidate store writes to see what happens;
prefer NexusRaven-style single-shot emission plus offline Proof over ReAct-style observation loops against live
stores.
- R3 (abstention gate): an irrelevance/abstain detector (Hammer-style negatives) shall sit between emission and
Proof so out-of-scope sections yield no ops, bounding junk writes and wasted Proof cycles.
- R4 (grammar is not validation): schema-valid output is not truthful output; llama.cpp-style constrained
decoding shall always be followed by Proof semantic checks (evidence quotes, offsets, dates).
- R5 (example-retrieval hygiene): retrieved few-shot op examples (ToolRAG/NexusRaven pattern) come from the
harness's own verified store and shall be integrity-tagged; never retrieve examples from untrusted ingested
content, or ingested text can steer future emissions.

## Harness implications

1. Put scheduling, parsing, validation, retrieval, and joining in deterministic harness code and let the small
model own only selection plus argument content, because every successful small-model agent (ReAct's executor
[2210.03629], LLMCompiler's planner/executor split [2312.04511], Toolformer's loss gate [2302.04761]) wins by
shrinking the model surface, not enlarging it.
2. Emit the per-section plan as a dependency graph in one forward pass and execute independent ops in parallel
under one write lock per store, following LLMCompiler [2312.04511] and ReWOO's observation-free planning
[2305.18323], with explicit dependency edges wherever ops share entity or offset state.
3. Constrain every emitted op with a checked grammar (GBNF/JSON-schema, as llama.cpp provides) and then run
Proof anyway, because grammars enforce shape but not truth [llama.cpp server README; 2410.04587].
4. Keep tool schemas and descriptions out of the prompt in a harness-side registry and retrieve per section only
the tools plus verified emission examples needed (ToolRAG [2409.00608]; Gorilla retriever [2305.15334];
NexusRaven demo-retrieval), since stuffing all stores' schemas into context confuses small models.
5. Replace free-text function selection with single-token or single-field op selectors plus a reformatter
(Octopus functional tokens [2404.01744]) so the embedding pass and the op pass share one decode.
6. Train abstention explicitly with irrelevance negatives and randomized-name masking [2410.04587] so the model
emits no op for out-of-scope text and reads descriptions instead of memorizing store names.
7. Verify ops in APIGen order [2406.18518] — cheap deterministic format checks, then real execution/offset
resolution, then the expensive semantic judge — and feed verified ops back as training seeds [2302.04761].
8. Serve one model process for embedding plus generation with radix prefix reuse and structured decoding
(SGLang [2312.07104]) on top of sparse-attention plus quantized kernels (MiniCPM4 [2506.07900]), keeping the
rig's asyncio-over-one-lock and no-persisted-KV decisions until measured otherwise.
9. Structure MelodyScribe as router-plus-specialists with swappable adapters (Octopus v4 graph [2404.19296];
Apple per-task LoRA adapters [2407.21075]; Phi-4 frozen backbone plus routers [2503.01743]), keeping the shared
backbone frozen and the op skill in a KL-anchored adapter.
10. Score the harness on BFCL-style AST-plus-execution grading extended with a store-routing accuracy split and
abstention tests, because string match hides the failure modes Hammer [2410.04587] and the rig's Proof logs
actually show.
