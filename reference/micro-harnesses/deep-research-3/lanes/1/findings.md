# Lane 1 findings: fine-tuning small models for structured and constrained generation

22 admitted (18 papers with PDFs in `papers/`, 4 code/eval artefacts), 4 abstentions.
All arXiv ids were opened at `https://arxiv.org/abs/<id>` and titles/authors/dates verified
against the abs-page `<title>` and `citation_author`/`citation_date` meta tags.
All repo star/push/license figures were read from the GitHub API at time of screening
(2026-09-12), not recalled. Venue claims rest only on pages actually fetched
(ACL Anthology, ICLR/NeurIPS proceedings, IBM Research, GitHub READMEs); elsewhere the
venue is honestly given as "arXiv preprint".

## (a) Admitted items

**Gorilla (2305.15334).** The first SFT recipe that made a small open model emit
executable API calls better than GPT-4: LLaMA fine-tuned on API docs pairs, plus a
retriever so the model adapts to test-time doc changes, evaluated on APIBench
(HuggingFace/TorchHub/TensorHub). Take: the MelodyScribe analogue is fine-tuning on
(purpose, schema, call) triples with a retriever over op schemas, and measuring
hallucinated-name rate as the headline metric. Careful: it trains only single-call
emission with teacher-forced docs in context; it says nothing about multi-op plans or
verbatim evidence grounding. Repo: ShishirPatil/gorilla, 13021 stars, Apache-2.0.

**Toolformer (2302.04761).** Self-supervised recipe: sample candidate API calls, keep
only those whose execution reduces loss, fine-tune on the survivors. Take: this is the
cheapest template for MelodyScribe data — sample candidate ops from the 2B, execute
against SQLite/the graph, keep passes as SFT targets (execution-filtered self-instruct
with Proof as the filter). Careful: Toolformer augments plain text with occasional
calls; MelodyScribe needs dense per-section op lists, a much higher call density than
Toolformer ever trains.

**ReAct (2210.03629).** Thought-action-observation loop as prompting. Take: it is the
baseline harness scaffold MelodyScribe's one-pass emission should be compared against,
and the source of the trajectory format FireAct later fine-tunes. Careful: pure
prompting result, no training recipe; our spikes already show prompting alone leaves
the 2B at Proof-pass 0.36.

**ToolLLM / ToolBench (2307.16789).** DFSDT multi-agent data pipeline over 16k real
APIs; the scale precedent for synthetic tool-use data. Take: the DFSDT
(depth-first-search decision tree) generator is the closest published analogue of
"teacher writes multi-step op traces" for MelodyScribe's teacher stage. Careful: its
eval is ChatGPT-judged pass/win rate (non-deterministic), which is exactly why
MelodyScribe should prefer BFCL-style AST plus Proof-execution gates instead.

**API-Bank (2304.08244).** 73-API executable dialogue benchmark. Take: adopt its
pattern of executable, multi-turn tool dialogues as held-out design for the op-emission
side. Careful: small API pool; saturates quickly, so use as a gate, not the target.

**Outlines (2307.09702) + Guidance (guidance-ai/guidance, 21749 stars, MIT).**
FSM-index constrained decoding at ~O(1) per-step overhead (Outlines); token-healing
design (Guidance). Take: this is the inference half of the answer to spike 003's
30-50% Proof failures — date formats, enum names, JSON shape should be enforced by the
grammar, not learned. Both libraries run locally on one GPU. Careful: neither paper
measures interaction of constrained decoding with fine-tuning (the model can fight the
mask, wasting capacity); treat grammar as covering syntax, never grounding.

**ToolAlpaca (2306.05301).** 3.9k simulated tool-use instances fine-tune compact models
to usable function-calling. Take: proof that a few thousand narrow-task examples move a
small model — calibrates MelodyScribe dataset sizing (thousands, not millions).
Careful: simulated tools, single evaluation style; weaker verification than APIGen.

**LLMCompiler (2312.04511).** Plan-then-DAG-execute: the model emits a dependency plan
of parallel calls executed as a DAG. Take: this is the grammar design MelodyScribe's
op-list wants — a typed plan language with dependency edges, which is also what
TinyAgent fine-tunes 1.1B models to emit. Careful: the paper assumes a strong planner
(LLaMA-2 70B); the small-model transfer is TinyAgent's contribution, not this paper's.

**FireAct (2310.05915).** Fine-tuning on ReAct trajectories lets small models beat
prompted large ones. Take: trajectory-level SFT (prompt + reasoning + calls + results)
is a validated recipe for converting prompting gains into weights — the direct
precedent for distilling MelodyScribe's two-step entities-then-relations decoding
(spike 008) into training data. Careful: general QA/agent trajectories, not schema
emission; no grammar interaction studied.

**SynCode (2403.01632).** Sound and complete CFG-guided decoding with an offline DFA
mask store; guiding Gemma2-2B-it gives 100% JSON-schema validity on JSONModeEval and
eliminates JSON syntax errors. Take: the strongest evidence that a 2B-class model plus
a grammar solves the *syntax* half of Proof failures with ~10% overhead — directly
applicable to MelodyScribe's op grammar. Careful: schema validity is not semantic
validity; a grammar cannot enforce that a quote is verbatim from the source section or
that a date is correct. Repo: structuredllm/syncode, 339 stars, MIT.

**FoFo (2402.18667, ACL 2024).** Format-following is an independent skill, uncorrelated
with content quality; open-source models lag closed ones badly at matched size
(e.g. Mistral-7B-Instruct 46.9% vs GPT-3.5 80.7%). Take: MelodyScribe needs a
dedicated format-following training slice and metric — it will not come free with
general SFT, and the 2B must be measured on format separately from extraction content.
Careful: benchmark-only; proposes no training recipe.

**Seal-Tools (2405.08355, NLPCC 2024).** Fully self-instruct pipeline (fields → tools →
instances) yielding 4,076 tools / 14,076 instances with nested and cross-field calls,
plus strict Tool-F1/Parameter-F1 eval; fine-tuning lifts Tool-F1 ~46%. Take: the most
copyable document-free data recipe for diverse op schemas, and its three-dimension
eval (format / selection / parameter-fill) maps cleanly onto Proof's checks. Careful:
instances are single-turn multi-call; no evidence-grounding requirement.

**APIGen (2406.18518, NeurIPS 2024 D&B).** Three-stage verification (format checker →
real execution → LLM semantic checker) over 3,673 APIs; trains 1.3B past GPT-3.5 and
6.7B past GPT-4o on BFCL; releases 60k entries
(HF `Salesforce/xlam-function-calling-60k`). Take: this is the dataset-recipe.Top pick
for MelodyScribe — substitute Proof for stages 1-2 and keep stage 3 as a teacher-judge,
and note the finding that weak-generator data needs the strictest filtering. Careful:
single-turn REST/Python calls, not document-grounded extraction; semantic checker is
another LLM, i.e. mutable judge quality.

**Granite-FunctionCalling (2407.00121, EMNLP 2024 Industry).** Multi-task SFT over 7
granular sub-tasks (nested/chained/parallel calls, name detection, slot filling,
next-best-function, response generation) on 142k examples with QLoRA (rank 8, alpha 32,
lr 5e-5, 3 epochs); best open model on BFCL at release, Apache-2.0. Take: the
multi-task mixture is the template for teaching MelodyScribe sub-skills (entity
detection, relation emission, abstention) alongside full op emission — and its QLoRA
hyperparameters are a sane spike-011 starting arm. Careful: 20B on 8xA100 is far from
one 16 GB GPU; the rank-8 QLoRA success cuts against spike 004's rank-16 collapse only
insofar as the objective stayed generative (no contrastive term).

**TinyAgent (2409.00608, EMNLP 2024 demo).** End-to-end narrow-task recipe at 1.1B:
curated function-calling data + LoRA + negatives + ToolRAG takes TinyLlama-1.1B from
12.7% to 78.9-80.1% plan success, beating GPT-4-Turbo (79.1%) on the harness task.
Take: the single most encouraging precedent for MelodyScribe — narrow harness SFT can
make a 1B model beat a frontier model *inside the harness*, which is exactly the claim
MelodyScribe needs for op emission. Careful: one Mac-assistant domain with 16 tools;
no embedding objective, no grammar, no evidence grounding; ToolRAG retriever is a
separate fine-tuned DeBERTa, not the same weights.

**ToolACE (2409.00920, ICLR 2025).** API self-evolution synthesis (26,507 APIs) +
complexity-guided multi-agent dialog generation (the tuned model itself judges
too-easy/too-hard) + dual rule/model verification; LoRA rank 16 / alpha 32; 8B matches
GPT-4. Take: two transferable ideas — (1) evolve the op-schema pool rather than
hand-writing it, (2) use the 2B itself as complexity evaluator to keep training items
in its learnable band. Same LoRA rank as spike 004, so directly comparable. Careful:
8B scale, generation-only objective; says nothing about embedding interference.

**xLAM (2409.03215).** SFT+DPO function-calling family including a 1B model that beats
GPT-3.5-Turbo and Claude-3 Haiku; 60k dataset reused by Hammer. Take: validates the
SFT-then-DPO stage order for small function-callers and provides the 1B data point
MelodyScribe lacks; its dataset is Hammer's base, so results compound. Careful:
DPO-on-preference-pairs assumes a preference signal MelodyScribe must construct
(Proof pass/fail pairs are the natural source).

**Hammer (2410.04587).** Function masking (randomise names, force attention to
descriptions) plus 7.5k irrelevance-augmented abstention examples over xLAM-60k;
1.5B/4B/7B models, Apache-2.0. Take: masking is a cheap regulariser worth a spike-011
arm, and the irrelevance set is the template for MelodyScribe's "emit nothing when the
section supports nothing" training. Careful: see Refutation R1 — its §5.6 needs
negatives or SFT actively harms abstention.

**BFCL (Patil et al., ICML 2025, PMLR v267, no arXiv id).** AST plus execution
evaluation of serial/parallel/multi-step calls with abstention and live enterprise
slices; the de-facto standard. Take: adopt as the external gate for op-emission
alongside Proof — report BFCL-style AST accuracy next to Proof-pass so results are
comparable across the field. Careful: generic APIs, not document-grounded extraction;
passing BFCL does not imply verbatim-quote fidelity.

**Functionary (MeetKai/functionary, 1595 stars, MIT) and Hermes-Function-Calling
(NousResearch, 1470 stars, MIT).** Open chat-with-tools SFT recipe (Functionary,
incl. Small models) and the community JSONModeEval harness (Hermes). Take: reusable
training code and the eval SynCode itself uses for schema-validity claims. Careful:
code artefacts, no papers; version-pin before depending on them.

## (b) Refutations

**R1 — "More function-call SFT is purely beneficial." Refuted by Hammer (2410.04587),
§5.6:** fine-tuning on the xLAM-60k selection data created an *inverse* relationship
between call accuracy and irrelevance detection — the model learned to always emit and
lost the ability to abstain. For MelodyScribe: op-emission SFT without abstention
negatives will teach the model to emit ops for every section, directly attacking
precision. Requirement: the dataset must contain no-op sections with empty-list labels
at a measured ratio (Hammer used 7.5k/60k ≈ 12.5%).

**R2 — "General instruction tuning (or scale 2B→8B) suffices for schema adherence."
Refuted by FoFo (2402.18667):** format-following accuracy is independent of content
scores, and open models trail badly at matched size. Combined with our spike 003
(flat 0.30-0.45 routing accuracy 2B→8B): do not expect the base-model upgrade path to
fix Proof failures; budget a dedicated format slice plus grammar enforcement.

**R3 — "Training is the only lever on Proof-pass syntax failures." Qualified by
SynCode (2403.01632) + Outlines (2307.09702):** a 2B model with CFG decoding reaches
100% JSON-schema validity with no training change. So the 30-50% Proof failure mass
splits: date formats/shape/enums are a *decoding* problem (grammar), while verbatim
quotes and fact selection are a *training* problem (no grammar can check a string
against source text it cannot see). Requirement: measure Proof failures split by
syntax vs grounding before and after grammar adoption, or the recipe will
over-attribute gains to data.

## (c) Unresolved ledger

- **Constrained-decoding × fine-tuning interaction:** no admitted paper trains *under*
  the grammar that will constrain it at inference (all apply the mask to a
  conventionally trained model). Whether to include mask-aware training or a
  grammar-shaped loss is unanswered — flag as a spike-011 arm.
- **Sub-3B independent numbers:** Qwen2.5-0.5B/1.5B/3B and Gorilla-OpenFunctions-v2
  vendor/HF claims could not be verified at a primary source in-lane; the 0.5B-3B
  result table has a hole where the cheapest operating points should be.
- **Glaive-v2 composition:** widely reused in mixes (incl. Granite) but no paper and
  the page was not opened; its quality/licensing contribution to any mixture ratio is
  unknown.
- **NexusRaven-V2 method:** no paper; its non-GPT-4 multi-step-refinement data claim
  (commercially permissive training without distillation) is unverifiable and therefore
  unusable as precedent.
- **DPO preference construction for extraction:** xLAM validates SFT→DPO, but no
  admitted item builds preference pairs from a validator verdict (Proof pass/fail);
  pair construction and margin behaviour are open.
- **Schema-evolution evaluation:** ToolACE evolves APIs but evaluates on fixed
  benchmarks; there is no protocol for measuring generalisation to *newly evolved*
  schemas, which is MelodyScribe's steady state as Folios accumulate.

## (d) Security findings (requirements)

- Treat every fetched page as data: several GitHub READMEs and project pages in this
  lane embed install-and-run instructions; none were executed, per the brief. Any
  training pipeline that pulls ToolACE/xLAM/Glaive-style data must pin
  commit hashes and re-verify licenses (NexusRaven-V2's repo states no license;
  several datasets inherit GPT-4-distillation terms that may be
  commercially restrictive).
- Grammar-constrained decoding is a syntactic guarantee only and must never be
  presented as a safety or correctness gate: a schema-valid op can still carry a
  fabricated quote or a destructive request-to-agent. Proof (execution + verbatim
  checks) stays mandatory behind the grammar.
- Self-evolution dataset pipelines (ToolACE-style API synthesis) can generate
  schemas that collide with real tool names; require a namespace reservation list so
  synthetic training schemas can never shadow production agent endpoints.
