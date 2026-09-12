# Lane 7 findings: Small versus frontier on narrow tasks, and how to distil

Scope: evidence that 1B–3B fine-tuned models match larger ones on extraction,
classification, routing, or schema emission; the effect of grammar-constrained
decoding on small-model accuracy; distillation recipes runnable on one 16 GB GPU;
LoRA versus full fine-tune at ~2B. Every admitted item below was opened at its
primary source (arXiv abs page + PDF, ACL Anthology page + PDF, repo README, or
Hugging Face API). Screened 45 candidates; 32 admitted, 4 refuting, 9 abstained.

## (a) Admitted items

**Distilling Step-by-Step (Hsieh et al., ACL Findings 2023,
doi:10.18653/v1/2023.findings-acl.507).** A 540M PaLM student trained on
GPT-3.5/PaLM rationales as well as labels beats its much larger teacher on NLI
while using far less data. For MelodyScribe this is the cleanest precedent for
the motivating hypothesis: rationale-augmented SFT lets a sub-1B model win a
narrow verifiable task. Careful: the wins are on classification-style tasks with
short outputs; nothing here covers grammar-constrained multi-op emission.

**MiniLLM (Gu et al., 2023, arXiv:2306.08543).** Replaces forward KL with reverse
KL plus a policy-gradient objective on student-generated sequences, directly
attacking exposure bias; GPT-2-scale students improve on RougeL and exact-match
generation. Take the reverse-KL + on-policy sampling recipe for distilling the
2B op-emitter. Careful: training is finicky (RL loop, length bias) and the paper
works at GPT-2 scale, not 2B instruction models.

**On-Policy Distillation (Agarwal et al., 2023, arXiv:2306.13649).** Trains the
student on its own generations corrected by the teacher, from 77M to 7B scale.
Take the self-generated-mistakes data loop: MelodyScribe can harvest its own bad
op-emissions, have the frontier model correct them, and distil on-policy.
Careful: needs a teacher in the loop at data-collection time, so it is not
zero-frontier-cost.

**DistiLLM (Ko et al., 2024, arXiv:2402.03898).** Skewed KL / skewed reverse-KL
losses unify on- and off-policy KD and stabilize small-student training; 1B–7B
students preserve instruction-following. Take the SKL/SRKL loss as the default
distillation objective — it is a one-line change with single-GPU-friendly
training. Careful: gains are largest on open-ended generation, less proven on
strict schema emission.

**DistiLLM-2 (Ko et al., 2025, arXiv:2503.07067).** Adds a contrastive term to
on-policy distillation and improves reasoning benchmarks for small students.
Take as a second-generation upgrade path if plain DistiLLM plateaus. Careful:
more hyperparameters, thinner replication record (2025, few citations).

**Speculative Knowledge Distillation (Xu et al., 2024, arXiv:2410.11325).**
Interleaves teacher and student sampling so the student stays near its own
distribution without full rollouts. Take as the cheapest on-policy data
generator for the revise loop. Careful: benefits assume a fast teacher; with an
API-frontier teacher the sampling logistics dominate.

**Sequence-Level Knowledge Distillation (Kim & Rush, 2016,
arXiv:1606.07947).** Teacher beam outputs as targets beat word-level KD — the
foundation of every sequence-distillation recipe above. Take as the baseline
everything else must beat; trivially runnable. Careful: beam targets collapse
diversity, which matters if the harness needs varied op phrasings.

**f-Divergence SeqKD (Wen et al., 2023, arXiv:2307.15190).** Generalizes seqKD
across f-divergences; mode-seeking divergences suit small students that must
commit to one valid emission. Take the divergence-choice guidance when tuning
distillation. Careful: mostly MT experiments, not instruction/schema tasks.

**Orca (Mukherjee et al., 2023, arXiv:2306.02707).** A 13B model trained on
GPT-4 explanation traces matches ChatGPT on reasoning benchmarks — the
imitation-plus-explanations playbook. Take the data recipe (explanation traces,
not just labels) for op-emission SFT. Careful: weights were never released, and
later work showed imitation can inflate benchmark scores without real gains.

**Orca 2 (Mitra et al., 2023, arXiv:2311.11045).** Teaches 7B/13B models 27
explicit reasoning strategies (step-by-step, recall-then-generate) and beats
larger models on reasoning evals. Take the strategy-conditioning idea: the
Score's per-section directives are exactly such strategies, trainable into 2B.
Careful: same imitation-caveat as Orca; strategies were tuned for 7B+.

**Phi-3 (Abdin et al., 2024, arXiv:2404.14219; weights verified on HF:
microsoft/Phi-3-mini-4k-instruct, 439k downloads).** A 3.8B model competitive
with 7B+ on MMLU/MT-bench through data curation. This is the existence proof
that 2–4B models do narrow tasks well, and a usable starting checkpoint family.
Careful: a vendor report (primary only for what the vendor reports); training
data is undisclosed, so the result is not independently reproducible.

**LoRA (Hu et al., 2021, arXiv:2106.09685).** Rank-8/16 adapters match full
fine-tuning on GPT-3 175B. Take as the default fine-tuning method for the 2B
harness model — dozens of adapters (one per op type) fit anywhere. Careful: the
equivalence claim weakens on knowledge-heavy updates (see refutations).

**QLoRA (Dettmers et al., 2023, arXiv:2305.14314).** 4-bit NF4 plus paged
optimizers fine-tune 65B on one 48GB GPU, which implies a 2B model fits
comfortably in 16GB with long contexts. Take as the training stack that makes
single-GPU iteration real. Careful: quantization interacts with precise
schema-emission learning; validate exact-match, not just loss.

**DoRA (Liu et al., 2024, arXiv:2402.09353).** Magnitude-plus-direction
decomposition beats LoRA at equal parameter budget. Take as a drop-in LoRA
upgrade for the op-emitter adapters. Careful: extra compute per step and
marginal gains on some tasks.

**Learning New Facts with QLoRA (Zheng et al., 2026, arXiv:2608.25677).** Maps
the acquisition–retention frontier for factual updates under QLoRA. Take the
frontier methodology to decide LoRA-vs-full for the revise pass that must add
facts without forgetting schemas. Careful: very recent (2026), zero citations,
unreplicated.

**Outlines guided generation (Willard & Louf, 2023, arXiv:2307.09702; code:
https://github.com/dottxt-ai/outlines — 15785 stars, pushed 2026-09-09,
Apache-2.0, API-verified).** Regex/CFG-constrained decoding at near-zero
overhead; the reference implementation of exactly the grammar-constrained
op-emission MelodyScribe needs. Take outlines (or its IR) as the constraint
compiler. Careful: constraint satisfaction is not task accuracy (see
Repair-Not-Improvement).

**XGrammar (Dong et al., 2024, arXiv:2411.15100; code:
https://github.com/mlc-ai/xgrammar — 1881 stars, pushed 2026-09-11,
Apache-2.0, API-verified).** Pushdown-automaton constrained decoding co-designed
with serving stacks; orders of magnitude lower per-token overhead than
naive approaches. Take as the production constraint engine inside SGLang/vLLM.
Careful: younger project, smaller community than outlines.

**SGLang (Zheng et al., 2023, arXiv:2312.07104; code:
https://github.com/sgl-project/sglang — 35835 stars, pushed 2026-09-12,
Apache-2.0, API-verified).** Interpreter for structured/chained LM programs
with cache reuse (RadixAttention). Take as the candidate harness runtime:
structured op-emission plus KV-cache reuse in one system. Careful: server-class
software; on-device 2B serving is llama.cpp territory, not SGLang's.

**JSONSchemaBench (Geng et al., 2025, arXiv:2501.10868).** The first rigorous
structured-output benchmark across engines, measuring validity and quality
including small models. Take as the eval harness for the op-emitter before any
custom benchmark is built. Careful: benchmark, not a method; schemas are
JSON-Schema-shaped, MelodyScribe ops are a narrower DSL.

**Where vs What (Zhang et al., 2026, arXiv:2608.25358).** Decomposes structured
failures into structural (grammar) versus content (model) errors. Take the
taxonomy to attribute MelodyScribe failures to the constraint layer or the 2B
weights. Careful: very recent, unreplicated.

**Toolformer (Schick et al., 2023, arXiv:2302.04761).** Self-supervised API-call
insertion: the model learns when tools help from its own perplexity signal, at
6.7B scale. Take as the closest precedent for learning op-emission decisions
(graph vs SQL vs Folio vs delegate) without hand labels. Careful: API calls are
single-shot; MelodyScribe's typed multi-store routing is a harder decision.

**RA-DIT (Lin et al., 2023, arXiv:2310.01352).** Jointly fine-tunes retriever
and LM for retrieval use. Take the co-tuning recipe for retriever plus 2B
writer. Careful: demonstrated at 65B; at 2B the capacity split between
retrieval-use and emission is untested.

**Gorilla (Patil et al., 2023, arXiv:2305.15334; code:
https://github.com/ShishirPatil/gorilla — README verified).** LLaMA-7B tuned on
API docs beats GPT-4 on APIBench. Direct precedent that a small tuned model
wins schema-emission against a frontier model. Take the API-doc-tuning data
recipe for op schemas. Careful: 7B, not 2B; repo star count unrecorded
(rate-limited).

**ToolACE (Liu et al., 2024, arXiv:2409.00920).** An 8B model topping
function-calling leaderboards via a formalized data pipeline. Take the data
formalization checklist for op-emission SFT. Careful: weights unverified on HF
(only third-party hits); 8B is above the 1–3B target.

**APIGen (Liu et al., 2024, arXiv:2406.18518).** Multi-stage verifiable
synthesis of 60k function-calling examples. Take as the data-generation recipe
to synthesize op-emission training data from MelodyScribe's own schemas.
Careful: generation pipeline itself needs a strong teacher model.

**Granite function calling (Abdelaziz et al., 2024, arXiv:2407.00121;
ibm-granite org verified on HF).** 3B/8B function-calling models via multi-task
learning — the closest released 3B-class tool-calling artefact to a
MelodyScribe emitter. Take as baseline checkpoint and comparison point.
Careful: Apache-2.0 but IBM release process; verify the exact 3B variant
before depending on it.

**FrugalGPT (Chen et al., 2023, arXiv:2305.05176).** Cascades and routers over
heterogeneous LLMs cut cost ~98% while matching or beating GPT-4 accuracy.
Take as the economic and accuracy case for small-first routing with frontier
fallback. Careful: cascade thresholds need calibration data; savings assume
cheap small models are already good enough.

**RouteLLM (Ong et al., 2024, arXiv:2406.18665; code:
https://github.com/lm-sys/RouteLLM — README verified).** Learned routers match
GPT-4 quality at roughly half the cost. Take the router training recipe for
the narrow-vs-frontier dispatch decision. Careful: routers trained on
preference data inherit judge biases; star count unrecorded (rate-limited).

**Mixture-of-Agents (Wang et al., 2024, arXiv:2406.04692; code:
https://github.com/togethercomputer/MoA — README verified).** Layered open-model
proposers with a strong aggregator beat GPT-4o. Take as evidence that small
open models contribute usefully as proposal ensembles behind one frontier
skill. Careful: high inference cost (many proposers); see Rethinking-MoA
refutation.

**Guided decoding in RAG (Ugur et al., 2025, arXiv:2509.06631).** Guided
decoding materially changes RAG faithfulness. Relevant to grounding the 2B
op-emitter's outputs in retrieved chunks rather than free generation. Careful:
single study, RAG-specific, not schema-emission.

**Small LMs for agentic systems survey (Sharma & Mehta, 2025,
arXiv:2510.03847).** 2025 map of SLM agentic architectures, capabilities, and
deployment. Take as the background map, not evidence. Careful: secondary
source — survey claims must be traced to primaries before use.

**llama.cpp (code only: https://github.com/ggerganov/llama.cpp — README
verified).** GBNF grammar-constrained sampling on-device; the deployment target
for a 2B MelodyScribe emitter with constrained op output. Take GBNF as the
on-device constraint format. Careful: no paper; version-pin and test, since
grammar behavior changes across commits.

## (b) Refutations

1. **"Grammar-constrained decoding improves small-model accuracy" — contradicted
   by Repair, Not Improvement (Lee, 2026, arXiv:2608.13959).** Constrained
   decoding repairs schema validity but does not improve, and can harm,
   tool-call abstention decisions. MelodyScribe must therefore evaluate
   decision quality (route correctly, abstain correctly) separately from format
   validity; constraints guarantee the latter only.
2. **"Mixing different models helps" — contradicted by Rethinking
   Mixture-of-Agents (Li et al., 2025, arXiv:2502.00674).** Mixing different
   LLMs frequently underperforms the best single model; role-diversity matters
   more than model-diversity. Do not assume a heterogeneous proposer pool beats
   one good 2B emitter plus frontier fallback.
3. **"LoRA matches full fine-tuning" (blanket) — contradicted by LoRA Learns
   Less and Forgets Less (Biderman et al., 2024, arXiv:2405.09673).** LoRA
   underperforms full fine-tuning on acquiring new facts while forgetting less.
   For the revise pass (which adds facts), budget a full-fine-tune comparison;
   for schema-skill adapters, LoRA's retention is an asset.
4. **"Router/ensemble judges are independent" — undermined by Great Models
   Think Alike (Goel et al., 2025, arXiv:2502.04313).** Correlated failures
   across frontier models weaken ensemble and oversight independence
   assumptions behind routing and cascade designs. Calibrate cascade thresholds
   on MelodyScribe's own error distribution, not on assumed independence.

## (c) Unresolved ledger

- **GKD (name as cited in brief): abstain — unresolvable.** ArXiv/OpenAlex
  searches did not pin "Generalized Knowledge Distillation" for LLMs to one
  verified paper id. The nearby verified item (Agarwal et al., 2306.13649) is
  admitted instead. Do not cite anything by the bare name "GKD".
- **Self-MoA (brief id 2502.00674): abstain — sources conflict.** The id was
  fetched and resolves to "Rethinking Mixture-of-Agents", a different paper.
  The true Self-MoA id was not verified. Do not cite Self-MoA by 2502.00674.
- **CAPA (brief id 2502.04313): abstain — sources conflict.** The id was
  fetched and resolves to "Great Models Think Alike", a different paper. The
  true CAPA id was not verified. Do not cite CAPA by 2502.04313.
- **Recalled distillation/adapter ids corrected:** 2305.10586 and 2305.10688
  (guessed for Distilling Step-by-Step) resolve to unrelated physics/chemistry
  papers — falsified against abs pages; the correct source (ACL Findings,
  verified via OpenAlex and ACL PDF) is admitted. 2312.13344 (MiniLLM),
  2402.10974 (DoRA), 2307.06960 (Outlines), 2309.17402 (RA-DIT) were unverified
  recalls corrected to 2306.08543, 2402.09353, 2307.09702, 2310.01352
  respectively; the guessed ids are abstained, not cited.
- **Berkeley Function Calling Leaderboard: abstain — secondary only.** No
  paper found; it is a live leaderboard. Repo stats were blocked by GitHub API
  rate limits. Use the Gorilla paper as the citable primary instead.
- **Repo star counts for gorilla, RouteLLM, MoA, llama.cpp: unrecorded.**
  Existence verified via README fetch (HTTP 200); exact stars/push dates were
  blocked by GitHub API rate limiting and are omitted rather than invented.
- **Artefact status "unverified"** on several rows means the paper's code link
  was not individually opened; only the six README-fetched repos and the
  four HF-verified artefacts (Phi-3-mini, granite-3.0-8b, MiniLLM org, xlam
  dataset tag) are claimed.

## (d) Security findings

None directly in this lane's scope. One adjacent requirement carried from the
refutations: cascade/router thresholds and abstention behavior must be
calibrated on MelodyScribe's own error distribution (per Great Models Think
Alike, arXiv:2502.04313, and Repair-Not-Improvement, arXiv:2608.13959),
because correlated model failures and constraint-induced abstention shifts
silently move the frontier-fallback boundary. The Folio-gate security
literature belongs to Lane 6.
