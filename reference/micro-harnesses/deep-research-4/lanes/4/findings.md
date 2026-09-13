# Lane 4 findings: thinking modes for small models

## (a) Admitted items

**1. Qwen3 Technical Report (arXiv:2505.09388).** The Qwen3 family (0.6B to 235B, Apache 2.0
weights) unifies thinking and non-thinking modes in one model with a thinking-budget mechanism
that trades latency against accuracy per task; repo https://github.com/QwenLM/Qwen3 (27610
stars, pushed 2026-01-09). MelodyScribe should take the hybrid-switch pattern as its thinking
contract: one 2B process serving both a terse non-thinking path (ingest ops, recall assembly)
and a thinking path (hard sections), switched per section by the harness, not per deployment.
Be careful: the report's agent/tool tables are vendor-reported on large sizes; nothing in the
report measures think-on/off tool-call accuracy at 0.6-4B, so do not cite it for small-scale
thinking gains.

**2. Qwen3 README thinking controls (vendor docs, https://github.com/QwenLM/Qwen3).**
`enable_thinking=False` passed to `apply_chat_template` strictly blocks thinking content;
`/think` and `/no_think` markers in system/user messages switch modes with latest-instruction
wins; the default template pre-includes `<think>`. MelodyScribe should take this exact
mechanism shape: a harness-owned template flag plus inline markers, with the harness (not the
model) resolving conflicts by recency. Be careful: this is API documentation, primary only for
what the switch does, not for any accuracy claim.

**3. MiniCPM4 (arXiv:2506.07900).** 0.5B and 8B on-device models (8.3T tokens, ~22% of Qwen3-8B
data; InfLLM v2 sparse attention; 7x long-document speed) plus MiniCPM4.1, a hybrid model with
deep-reasoning and non-reasoning modes, applied to MCP tool use; repo
https://github.com/OpenBMB/MiniCPM (10915 stars, Apache-2.0). MelodyScribe should take it as
the existence proof that a sub-10B hybrid think/no-think model with tool use ships on-device,
and mirror the 4.1 split: reasoning mode only where measured to pay. Be careful: no MiniCPM4.1
think-vs-no-think ablation on structured emission is published; the 0.5B size has almost no
training detail in the report.

**4. s1: Simple test-time scaling (arXiv:2501.19393).** Supervised fine-tune on 1K curated
traces plus budget forcing: forcibly terminate thinking or extend it by appending "Wait";
s1-32B beats o1-preview by up to 27% on MATH/AIME24 and scales 50% to 57% on AIME24;
https://github.com/simplescaling/s1 (6668 stars, Apache-2.0). MelodyScribe should take budget
forcing as the cheapest harness-side thinking knob: a per-section token cap with forced stop,
no model change required. Be careful: "Wait"-extension gains are contested (see Mirage #14);
adopt only the termination half until extension is measured on extraction ops, and note s1's
evidence is all 32B math, not 2B extraction.

**5. L1 (arXiv:2503.04697, COLM 2025).** Length-Controlled Policy Optimization trains models
that obey a prompt-given length constraint and yields Short Reasoning Models; the 1.5B L1
surpasses GPT-4o at equal reasoning lengths and beats s1-style control. MelodyScribe should
take LCPO as the fine-tuning target for thinking: if thinking is ever enabled, train the 2B
to obey an explicit budget token rather than hoping the base model self-limits. Be careful:
code/model URLs in the paper were not verified from this environment, so fetch them before
depending on the artefact; results are math/QA, not grammar-constrained emission.

**6. Coconut (arXiv:2412.06769, COLM 2025).** Feeds the last hidden state back as the next
input embedding instead of decoding words, letting continuous thoughts encode several next
steps (latent BFS); beats CoT on planning-heavy logic with a better accuracy-efficiency
tradeoff; https://github.com/facebookresearch/coconut (1704 stars, MIT). MelodyScribe should
take the architectural hint seriously: its [EMB]-marker design already reads a hidden state
for the embedding, and Coconut shows hidden-state feedback can carry multi-path reasoning a
2B model cannot verbalize. Be careful: Coconut needs staged training and only pays on
search-heavy planning tasks; for deterministic op emission it is a research direction, not a
v0.1 component.

**7. Huginn recurrent depth (arXiv:2502.05171).** A 3.5B depth-recurrent model (2,4,2) blocks,
h=5280, trained 800B tokens with randomized recurrence counts, improving with test-time
recurrences up to ~50B-equivalent FLOPs, with KV-cache sharing and adaptive compute;
weights https://huggingface.co/tomg-group-umd/huginn-0125, code
https://github.com/seal-rg/recurrent-pretraining (955 stars, Apache-2.0). MelodyScribe should
take it as the only small open weights where "thinking" is extra recurrent passes instead of
extra tokens: relevant if the harness ever wants depth without lengthening the context the
grammar decoder must scan. Be careful: academic data mix, never cooled down, lags careful
7B models on standard benchmarks; treat as compat-check target, not base-model candidate.

**8. Huginn latent-CoT probe (arXiv:2507.02199, COLM 2025 workshop).** Logit-lens/coda-lens
probing of Huginn-3.5B finds no structured latent chain-of-thought, and recurrence depth 4 to
32 moves GSM8K only 3.11 to 4.93 versus 24.87/38.13 with explicit CoT;
https://github.com/wenquanlu/huginn-latent-cot. MelodyScribe should take the negative result
at face value: latent-only thinking does not substitute for an explicit trace on tasks the
harness must verify. Be careful: probing lenses are weak detectors, which the authors concede;
this bounds, not kills, latent approaches.

**9. SoftCoT (arXiv:2502.12134, ACL 2025).** A frozen backbone LLM reasons better when a
small fixed assistant (e.g. 1B-class) speculatively emits soft thought tokens mapped through
a trained projection, with only the projection tuned; gains hold across five benchmarks and
stack with self-consistency; https://github.com/xuyige/SoftCoT. MelodyScribe should take the
pattern small-thinks-for-large: a 2B MelodyScribe could emit compact soft-thought prefixes
for the frozen frontier model instead of only assembling text payloads. Be careful: needs per-task
projection training and a shared embedding geometry; cross-family (2B local to frontier API)
mapping is unproven.

**10. LightThinker (arXiv:2502.15589, EMNLP 2025 oral).** Trains the model to compress each
thought into a few gist tokens and discard the original chain, with a Dependency metric for
reliance on history; cuts peak memory and inference time at competitive accuracy;
https://github.com/zjunlp/LightThinker (165 stars, MIT). MelodyScribe should take
compress-then-discard as the thinking design compatible with per-decode token caps: if a
section ever gets a trace, compress it to gist tokens before op emission so the grammar
decoder never scans a long chain. Be careful: compression training is extra fine-tuning
machinery; the Dependency metric is new and uncalibrated outside the paper's four datasets.

**11. Search-R1 (arXiv:2503.09516).** RL over interleaved think-then-search trajectories with
retrieved-token masking and a plain outcome reward lifts Qwen2.5-7B by 41% and Qwen2.5-3B by
20% over RAG baselines on seven QA sets; https://github.com/PeterGriffinJin/Search-R1 (5413
stars, Apache-2.0). MelodyScribe should take two things: interleaved thinking-with-retrieval
is trainable down to 3B, and retrieved tokens must be masked from the RL loss, which is the
same hygiene its recall loop needs (store text is environment, not policy). Be careful: the
trace here is load-bearing at inference (queries are generated mid-thought); that does not
transfer to MelodyScribe ingest, where the trace can be discarded after Proof.

**12. ReTool (arXiv:2504.11536).** RL with live code execution inside the reasoning loop from
a synthetic cold start teaches a 32B model when to call tools from outcome feedback alone:
67% AIME at 400 steps versus 40% for text-only RL at 1080 steps, 72.5% extended versus
o1-preview, with emergent code self-correction. MelodyScribe should take the cold-start-then-RL
recipe for op emission: Proof verdicts are exactly the kind of outcome reward that taught
strategic tool invocation here. Be careful: no code URL could be verified from the paper HTML
and all numbers are 32B math; the transfer to 2B grammar-constrained ops is a hypothesis
requiring the harness-first fine-tune the brief already plans.

**13. ToRL (arXiv:2503.23383).** Tool-integrated RL straight from base models without SFT
first, capped by default at one tool call per response, reaches 43.3% AIME24 at 7B (+14 over
no-tool RL, +17 over the best TIR baseline) and, critically, 48.5% average at 1.5B versus
35.9/41.3 for instruct variants, with emergent cross-checking of tool outputs;
https://github.com/GAIR-NLP/ToRL. MelodyScribe should take RL-from-base plus a hard tool-call
cap as the training template for op emission, and note 1.5B as proof that strategic tool use
is learnable at MelodyScribe scale. Be careful: the cap (C=1) that makes training tractable
also bounds expressiveness; MelodyScribe emits op lists, so the cap analog is per-op Proof,
not per-response.

**14. Self-consistency (arXiv:2203.11171, ICLR 2023).** Sampling diverse reasoning paths and
marginalizing (GSM8K +17.9%, SVAMP +11.0, AQuA +12.2, StrategyQA +6.4, ARC-c +3.9) is the
canonical way to spend a token budget on breadth instead of length. MelodyScribe should take
it as the default parallel-thinking baseline for any query-time use of thinking: N short
independent section reads with agreement-gating, never one long trace. Be careful: N full
decodes multiply the grammar-filtering bottleneck (already 9x CPU-side per spike 009);
parallel thinking is cheap only if most paths are non-thinking or share prefixes.

**15. When More is Less (arXiv:2502.07266).** Accuracy follows an inverted U in CoT length;
the optimal length grows with task difficulty but shrinks with model capability, and RL
training itself drifts toward shorter CoTs as accuracy rises (simplicity bias, formally
modeled). MelodyScribe should take the scaling law as the thinking policy: budget per
section should be set from estimated section difficulty, defaulting near zero for routine
prose, since a 2B model past its optimum gets worse, not just slower. Be careful: optimal
lengths are measured on math/QA, and the paper gives no extraction-task calibration.

**16. Mirage of test-time scaling (arXiv:2506.04210, NeurIPS 2025).** "Wait"-appended longer
thinking first helps then degrades (overthinking as variance growth, not refinement), while
parallel thinking at the same token budget gains up to 20-22%, e.g. R1-Distill-Qwen-1.5B on
GSM8K drops 11.8% sequential but rises 10.1% parallel. MelodyScribe should take the budget
rule: never spend spare tokens lengthening one trace; spend them on parallel short reads plus
majority/Proof-gated selection. Be careful: the variance-mirage model is explanatory, and its
1.5B evidence is one model family on math; still, it directly contradicts adopting s1-style
extension for the harness.

**17. short-m@k (arXiv:2505.17813).** Within-question shortest chains beat longest by up to
34.5%; short-3@k (stop when 3 of k finish, majority vote) beats majority@k on all budgets up
to 33% faster; fine-tuning on short traces beats training on long ones (+2.8%, -5.8%
tokens). MelodyScribe should take both the decoding rule (early-finish selection among
parallel reads) and the training rule (fine-tune the 2B on short successful op traces, never
on long ones). Be careful: stopping at first-finish biases toward easy paths; keep m>=3 and
a Proof-validity gate so speed does not select sloppy ops.

**18. NoThinking (arXiv:2504.09858).** Prefilling an empty thinking box on R1-Distill models
matches or beats thinking at equal tokens (51.3 vs 28.9 on AMC23 at 700 tokens, 2-5.1x fewer
tokens, 7-9x latency wins) with the gap growing in pass@k. MelodyScribe should take the
strong default the brief's unknown leans toward: non-thinking single-pass emission, with
parallel NoThinking-plus-verifier as the scaling path instead of any thinking mode. Be
careful: evidence is math/code/theorem-proving, and best-of-N needs a verifier, which
MelodyScribe has (Proof) for ingest but may lack for open-ended recall reads.

**19. Do NOT Think That Much (arXiv:2412.21187, ICML 2025).** First overthinking metrics
(outcome/process efficiency): o1-like models burn 1953% more tokens than conventional models
on "2+3" with 13 redundant solutions, worst on easy items; self-training on pruned traces
cuts ~49% of MATH500 tokens at equal accuracy;
https://github.com/galaxyChen/overthinking. MelodyScribe should take the efficiency metrics
as harness health metrics (tokens per admitted op, solutions per section) and the pruning
recipe for distilling its own fine-tune data. Be careful: difficulty grading and solution
splitting are heuristic; port the metrics, not the exact thresholds.

**20. Underthinking (arXiv:2501.18585).** The mirror failure: o1-like models switch thoughts
before exploring any path deeply, and switching frequency predicts wrong answers; a
thought-switching penalty (TIP) at decoding time restores depth, including under Best-of-N.
MelodyScribe should take TIP as the guard for the rare thinking-enabled path: penalize
section/topic switching inside one section read so hard sections get depth, not tourism. Be
careful: TIP is tuned for math reasoning traces; an equivalent "stay-on-section" penalty for
extraction reads needs its own calibration.

**21. Under/overthinking at 1.5B (arXiv:2505.00127).** On DeepSeek-R1-Distill-1.5B and
DeepScaler-1.5B-Preview (GSM8K/MATH), models miscalibrate both directions: overlong on easy
items, too short on hard ones; preference-tuning toward shorter responses keeps accuracy at
much lower length. MelodyScribe should take the direct 1.5B evidence that small reasoning
models cannot self-size their thinking, so the harness must set the budget from its own
difficulty estimate. Be careful: only two 1.5B models and two math benchmarks; extraction
difficulty signals (entity density, quote length) are untested.

**22. Mind Your Step (arXiv:2410.21333).** CoT cuts accuracy where verbalization hurts
humans: up to -36.3pp (o1-preview vs GPT-4o zero-shot) on implicit statistical learning,
with similar drops on unverbalizable stimuli and exception-ridden rules. MelodyScribe should
take the boundary condition: extraction sub-tasks that are implicit pattern match
(entity spotting, near-duplicate detection, "this is code" routing) are exactly where a
thinking trace is predicted to hurt, so keep them non-thinking by design. Be careful: three
of six archetypes showed mixed/positive CoT effects, so this is a scalpel (which sub-tasks
think) not a ban.

**23. ThinkBrake (arXiv:2510.00546, ACL 2026 Findings).** Training-free early stop when the
log-margin between the top token and `</think>` narrows at sentence boundaries: oracle
stopping gains +8% accuracy at -72% thinking tokens, and on BFCL-v2 with Qwen3-4B-Thinking it
holds parallel accuracy at -32% tokens and improves multi-parallel ~8%, where cruder cuts
(ThinkLess -50% parallel) collapse; https://github.com/holi-lab/ThinkBrake. MelodyScribe
should take ThinkBrake as the thinking-off switch implementation for any think-enabled pass:
logit-level, per-boundary, no training, and the only tool-call thinking study at 4B scale.
Be careful: needs `</think>`-style explicit reasoning format and logit access (fine for
local SGLang/llama.cpp, unavailable behind some APIs); threshold tau is tuned per setup.

**24. DeepSeek-R1 (arXiv:2501.12948, Nature 2025).** Pure outcome-reward RL produces
reflection/verification behaviors without human traces, and the recipe distills to open 1.5B
reasoning weights. MelodyScribe should take the training moral for its harness-first plan:
validator-as-reward works, and small open thinking-capable weights exist as experimental
substrates. Be careful: R1-Zero needed a large base and long RL; nothing here says a 2B
model keeps op emission after reasoning RL (spikes 004/006/011 say the opposite risk is
real: embedding pressure already kills ops once).

**25. Let Me Speak Freely (arXiv:2408.02442).** Format restrictions degrade reasoning, worse
when stricter: JSON-mode placed "answer" before "reason" and scored zero on Last-Letter
while free text succeeded; LLaMA-3-8B shows a 38.15pp gap with only 0.148% parse failures,
so the loss is reasoning damage, not extraction noise. MelodyScribe should take the ordering
rule: anything resembling reasoning (section triage, store choice) must precede or sit
outside the grammar-constrained span, never inside it. Be careful: models are 2024-vintage
and JSON-mode implementations differ; the mechanism (order + restriction), not the numbers,
is what transfers.

**26. In-Writing (arXiv:2601.07525).** Free-think first, then constrain after a trigger token:
up to +27% over natural generation with 100% format validity at +5-20 tokens, beating both
constrain-everything (high variance, reasoning damage) and CRANE-style grammar-restricted
reasoning (+32%); https://github.com/Nokia-Bell-Labs/InWriting (BSD-3-Clause-Clear).
MelodyScribe should take the single most applicable architecture in this lane: one decode in
which the op list is emitted only after a trigger, with the grammar applied to the op span
alone, so the embedding read and any triage stay unconstrained. Be careful: 2026 preprint,
small repo footprint (1 star); replicate the trigger discipline before trusting the 27%.

**27. MiniCPM5 existence line (vendor repo https://github.com/OpenBMB/MiniCPM).** The repo
describes MiniCPM5 as its current SOTA on-device LLM line (10915 stars, Apache-2.0, pushed
2026-09-12). MelodyScribe should take this only as a pointer: MiniCPM5-2B exists as the
current rig model and its thinking controls must be read from its own model card/docs, not
inferred from MiniCPM4. Be careful: no thinking-accuracy claim is attached to this item.

## (b) Refutations

**R1. Against "explicit thinking is necessary for capable reasoning" (background assumption,
not a brief claim).** NoThinking (arXiv:2504.09858) shows R1-Distill models match or beat
thinking-mode at equal token budgets with an emptied thinking box. Status: refuted for
math/code-style tasks; untested for extraction.

**R2. Against "more thinking is better / Wait-extension scales reasoning".** Mirage
(arXiv:2506.04210) shows sequential extension gains are a variance artifact followed by
degradation, with parallel thinking up to 20% better at equal budget. Status: sequential
scaling refuted as a budget policy; s1-style termination (not extension) is unaffected.

**R3. Against "latent/recurrent thinking can replace explicit traces".** The Huginn probe
(arXiv:2507.02199) finds recurrence-depth scaling moving GSM8K 3.11 to 4.93 against
24.87/38.13 with explicit CoT, with no detectable latent CoT structure. Status: refuted as a
v0.1 direction; latent feedback (Coconut-style) remains an open research bet, not a
replacement.

**R4. Against "thinking helps all sub-tasks, so default it on".** Mind Your Step
(arXiv:2410.21333) plus Speak Freely (arXiv:2408.02442) show thinking/format constraints
actively damage implicit-pattern and reasoning-heavy tasks (up to -36.3pp; 38pp gap at 8B).
Status: universal-think-on refuted; thinking must be gated per sub-task, default off for
extraction.

## (c) Unresolved ledger

**U1. MiniCPM5-2B think-on/off tool-call accuracy.** No primary source found with measured
numbers; the Qwen3 report does not break out small sizes and MiniCPM4.1 has no published
ablation. Reason: literature gap, not enough search. Requirement: measure on-rig with
Proof-gated op emission before enabling thinking anywhere.

**U2. Thinking-bytes interaction with grammar-constrained op emission at 1-3B.** No paper
tests thinking modes jointly with hard grammar constraints on small models; the format-tax
papers use prompting/JSON-mode, not token-mask grammars. Reason: genuine gap. Requirement:
on-rig A/B (grammar-constrained ops with think-off vs trigger-gated think, per In-Writing)
with Proof pass rate as the metric.

**U3. Whether the interleaved trace is needed at inference for extraction.** Search-R1,
ReTool, and ToRL all need their traces/queries at inference, but all are math/code/search;
no extraction-harness equivalent was found. Reason: domain gap. Requirement: treat ingest
traces as discardable (evidence: NoThinking, ThinkBrake oracle) until a recall-side
experiment shows otherwise.

**U4. Thinking-token budget for embedding quality at 2B.** The reasoning-embedder line
(ReasonEmbed, DIVER, CRE-T1, MRE-T1, O1-Embedder, RL-Index, Rank1, per prior round) shows
thinking helps embeddings, but none was found tested inside a single-pass emit-embedding-plus
-ops harness at 2B with op emission intact (spikes 004/006/011 warn of the conflict).
Reason: interface gap between two literatures. Requirement: any thinking budget must be
co-measured on MRR and op Proof-pass jointly.

**U5. Small-model thinking on code-graph queries.** No thinking-mode study targeting
graph-query formulation over code graphs at 1-3B was found. Reason: gap between lane 4 and
lane 7 literatures. Requirement: default code routing to non-thinking with parser-built
context; revisit only with measured evidence.

**U6. L1 and ReTool artefacts.** Both papers declare released code/models but no repository
URL could be verified from this environment (arXiv HTML contains no repo link). Reason:
verification failure, not absence. Requirement: re-fetch before depending on either
artefact; claims above rest on the papers alone.

## (d) Security findings (stated as requirements)

**S1. Treat thinking traces as untrusted input.** Interleaved think-tool designs (Search-R1,
ReTool, ToRL) place tool/store output inside the trace that conditions later tokens; any
stored section text reaching a trace is an injection path. Requirement: thinking traces must
never be persisted to the learning graph or Folios verbatim, and any trace reused across
sections must pass through Proof-equivalent validation.

**S2. Cap thinking as a compute-DoS control.** Budget forcing, "Wait" extension, and
recurrence loops all convert a crafted input into unbounded generation; overthinking papers
show models already overspend most on the simplest inputs. Requirement: the harness must
enforce a hard per-section thinking-token cap independent of model cooperation, with
forced stop (s1-style termination) as the default closer.

**S3. Do not assume trace presence.** NoThinking and ThinkBrake change the output
distribution by removing or truncating traces; a validator or merger that keys on trace
markers will misfire. Requirement: Proof and the recall assembler must accept traceless
decodes as the normal case and treat any trace as optional metadata.

## Harness implications

1. Default every MelodyScribe decode to non-thinking single-pass emission of the [EMB]
   embedding plus grammar-constrained ops, because small models that skip thinking match or
   beat thinking models at equal budgets while using several times fewer tokens (NoThinking,
   arXiv:2504.09858; Under/Over-1.5B, arXiv:2505.00127).
2. Spend any spare thinking budget on parallel short reads with early-finish selection and
   Proof-gated voting, never on lengthening one trace, because parallel thinking beats
   sequential extension by up to 20% at equal tokens and shortest-of-k beats longest by up to
   34.5% (Mirage, arXiv:2506.04210; short-m@k, arXiv:2505.17813; self-consistency,
   arXiv:2203.11171).
3. Expose thinking as a harness-owned per-section switch in the Qwen3 shape
   (enable_thinking flag plus /think + /no_think markers, latest wins) with a hard token cap
   and forced stop, because hybrid models already ship this contract and budget forcing is the
   cheapest effective control (Qwen3 report, arXiv:2505.09388; Qwen3 vendor README; s1,
   arXiv:2501.19393).
4. Gate thinking per sub-task with default-off for implicit-pattern work (entity spotting,
   code-vs-date routing) and optional-on only for hard sections under a TIP-style
   stay-on-section penalty, because thinking actively damages exactly those tasks (Mind Your
   Step, arXiv:2410.21333; Underthinking, arXiv:2501.18585; When-More-is-Less,
   arXiv:2502.07266).
5. Implement the thinking-off switch as ThinkBrake-style logit-margin early stopping at
   sentence boundaries wherever a think-enabled pass exists, because it is training-free,
   needs only local logit access, and is the only method holding tool-call accuracy on a 4B
   hybrid model (ThinkBrake, arXiv:2510.00546).
6. Structure any think-enabled decode as reason-then-format with the grammar applied only to
   the op span after a trigger, keeping the embedding read and triage unconstrained, because
   constraining the whole decode damages reasoning while trigger-gated constraining keeps
   100% validity at +5-20 tokens (In-Writing, arXiv:2601.07525; Speak Freely,
   arXiv:2408.02442).
7. Train thinking (if ever enabled) with RL length control toward short traces and
   validator-as-reward from Proof, following the cold-start-then-RL recipe with capped tool
   calls that works down to 1.5B, because length-obedient short reasoning beats long traces
   on both accuracy and cost (L1, arXiv:2503.04697; ToRL, arXiv:2503.23383; ReTool,
   arXiv:2504.11536; Search-R1, arXiv:2503.09516).
8. Keep latent and recurrent thinking out of v0.1 while tracking Coconut-style hidden-state
   feedback as the research bet, because latent-only depth currently falls an order of
   magnitude short of explicit traces on verifiable tasks (Huginn probe, arXiv:2507.02199;
   Huginn, arXiv:2502.05171; Coconut, arXiv:2412.06769), and co-measure any future thinking
   budget jointly on MRR and op Proof-pass since embedding pressure already kills op
   emission once (DeepSeek-R1, arXiv:2501.12948; SoftCoT, arXiv:2502.12134; LightThinker,
   arXiv:2502.15589).
