# Lane 4 findings: Distillation and RL recipes on one consumer GPU

Scope: on-policy distillation, generalised knowledge distillation, MiniLLM, DistiLLM,
sequence-level KD, rejection-sampling fine-tuning, RL with verifiable rewards (GRPO family,
RLVR) applied to structured emission, validator-as-reward, reported compute, model sizes,
released artefacts. Screened 47, admitted 29, with 1 refutation and 17 abstentions. All arXiv ids below were opened at
`https://arxiv.org/abs/<id>` (title, authors, date, abstract verified); all repos via the
GitHub API; the R1-Distill checkpoint via the Hugging Face API.

## (a) Admitted items

**MiniLLM (2306.08543).** On-policy distillation for generative LMs: replaces forward KL
with reverse KL so the student does not over-cover the teacher's low-probability tails,
then optimizes it on student-generated sequences; ICLR 2024, 120M--13B students, code/data/
checkpoints released under microsoft/LMOps (MIT, 4473 stars). Take: reverse KL is the
correct divergence when the student must *emit* narrow structured ops rather than match a
broad distribution, and on-policy (student-generated) training directly attacks the
exposure bias behind Proof failures on quotes/dates. Caution: needs teacher logits on
student rollouts (white-box teacher, memory cost); pair with DistiLLM's off-policy trick
below. `https://arxiv.org/abs/2306.08543`

**GKD, Generalised Knowledge Distillation (2306.13649).** Trains the student on its own
self-generated outputs with teacher feedback, supports arbitrary student--teacher losses
for capacity-mismatched students, and explicitly unifies distillation with RL fine-tuning;
ICLR 2024. Take: this is the paper that legitimizes spike 011's joint contrastive +
op-emission arm — GKD is the "train on your own mistakes with teacher correction" loop,
and its RL-integration section is the bridge from distillation to Proof-as-reward RL.
Caution: on-policy rollouts during training are the expensive part (see DistiLLM for the
fix); loss choice matters more than the paper's headline suggests when the student is 2B.
`https://arxiv.org/abs/2306.13649`

**DistiLLM (2402.03898).** Skew-KL loss with proven properties plus an *adaptive
off-policy* scheme that reuses student-generated outputs instead of regenerating them;
ICML 2024, up to 4.3x speedup over recent KD methods at equal quality; code at
jongwooko/distillm. Take: on a 16 GB card the rollout budget is the binding constraint,
and DistiLLM is the cheapest credible way to keep on-policy benefits without on-policy
cost — use it as the distillation stage before any RL. Caution: repo is small (268 stars,
last push 2025-03-13, no license stated) — vendor it, do not depend on it upstream.
`https://arxiv.org/abs/2402.03898`

**DistiLLM-2 (2503.07067).** Contrastive distillation: push likelihood up on teacher
responses and down on student responses, with the loss matched to the data source; ICML
2025 Spotlight; extends to preference alignment and vision-language students. Take: the
push-down-on-student-outputs term is a natural home for Proof-rejected ops — failed
emissions become contrastive negatives for free. Caution: contrastive objectives can
collapse narrow structured grammars if the negative weight is too high; sweep it.
`https://arxiv.org/abs/2503.07067`

**Sequence-level KD (1606.07947).** The founding result: training the NMT student on
teacher-*generated sequences* (not token labels) produced a 10x-faster student with little
quality loss and reduced beam-search dependence. Take: any MelodyScribe distillation
should use teacher *emission traces* (full op lists per section), never token-level
cross-entropy on documents — sequence-level is what transfers structured behavior.
Caution: 2016 NMT setting; the mechanism transfers, the numbers do not.
`https://arxiv.org/abs/1606.07947`

**STaR (2203.14465).** Self-Taught Reasoner: generate rationales, retry with the answer,
fine-tune only on traces that yield correct answers, iterate; matched a 30x larger SOTA.
Take: this is the exact template for Proof-as-reward data flywheel — Proof verdict
(answer-correct equivalent) filters self-generated op traces, and iteration bootstraps
from few seeds. MelodyScribe's evidence-quote check is a stricter filter than STaR's
answer check, so expect lower yield per rollout and budget accordingly. Caution:
rationalization (retry-given-answer) teaches answer-conditioned generation, which can
inflate pass rates without teaching first-pass emission; track first-pass Proof-pass
separately. `https://arxiv.org/abs/2203.14465`

**RFT, Rejection-sampling Fine-Tuning (2308.01825).** Self-generates reasoning paths,
keeps correct ones, fine-tunes; finds log-linear data-vs-performance scaling and that
*weaker* models gain most (LLaMA-7B GSM8K 35.9 to 49.3 percent). Take: two predictions
for MelodyScribe — (1) expect log-linear gains from Proof-filtered op traces, so plan
data budgets on a log scale; (2) the 2B is exactly the "less performant LLM" that gains
most, which favors RFT over heavier RL as the first recipe. Caution: diversity of kept
paths matters more than count; dedupe traces or gains saturate.
`https://arxiv.org/abs/2308.01825`

**DeepSeekMath (2402.03300).** Introduces GRPO — PPO with the critic replaced by
group-normalized advantages — plus a full open pipeline (data selection, 7B and 1.3B
models, 51.7 percent MATH for the 7B); code/models MIT at deepseek-ai/DeepSeek-Math.
Take: GRPO is the memory story — no value network means RL fits where PPO does not, and
the 1.3B model's existence proves rule-reward RL works below 2B. This is the base
algorithm for any Proof-as-reward stage. Caution: vanilla GRPO has the biases Dr.GRPO
fixes (below); never run uncorrected GRPO with a length-correlated reward.
`https://arxiv.org/abs/2402.03300`

**DeepSeek-R1 (2501.12948).** R1-Zero shows pure verifiable-reward RL induces reasoning
without SFT traces; then distills traces into small models, releasing R1-Distill down to
1.5B (deepseek-ai/DeepSeek-R1, MIT, 91994 stars; Distill-Qwen-1.5B has 400956 HF downloads).
Take: the two-phase pattern — RL-induce with a checker, then distill to small — maps onto
MelodyScribe as "RL-tune the 2B against Proof, then distill the winner back to a clean
adapter"; the 1.5B distill's popularity is existence proof of a market-tested small
reasoner. Caution: R1-Zero scale is far beyond one 16 GB GPU; import the pattern (rule
reward + distill-down), not the compute budget. `https://arxiv.org/abs/2501.12948`

**DAPO (2503.14476).** Fully open large-scale RL system: decoupled-clip and dynamic-sampling
GRPO variant, 50 AIME-2024 points on Qwen2.5-32B, code built on verl plus curated dataset
released. Take: dynamic sampling (oversample groups with nonzero advantage variance,
discard all-correct/all-wrong groups) is directly applicable to Proof rewards, where most
rollouts will initially fail — without it, GPU cycles burn on zero-gradient groups.
Caution: 32B-scale system; extract the algorithm (clip + sampling), run it in verl/TRL at
2B. `https://arxiv.org/abs/2503.14476` — project page `https://dapo-sia.github.io/`

**Dr.GRPO (2503.20783).** Diagnoses GRPO's optimization bias — response length (especially
of *incorrect* outputs) drifts up — and replaces it with an unbiased token-mean
objective; minimalist 7B recipe reaches 43.3 percent AIME 2024. Take: mandatory fix if
spike 011 runs GRPO against Proof, because Proof failures correlate with long,
rambling op lists — uncorrected GRPO would reward exactly the failure mode. Also note the
pretraining-bias finding (base models already show "aha" patterns): check whether
MiniCPM-2B already emits self-correction before assuming RL taught it. Caution: paper
compares base-model families; transfer the objective fix, not the family ranking.
`https://arxiv.org/abs/2503.20783`

**RLOO / Back to Basics (2402.14740).** REINFORCE with leave-one-out baselines beats PPO
and DPO/RAFT in the authors' alignment tests at much lower cost — no critic, no reference
model gymnastics. Take: the simplest critic-free online method; if GRPO proves fiddly at
2B/16GB, RLOO is the fallback with the smallest memory footprint (policy + one rollout
batch). Caution: REINFORCE variance is real; needs the same dynamic-sampling hygiene as
GRPO. `https://arxiv.org/abs/2402.14740`

**ReMax (2310.10505).** REINFORCE with a greedy-rollout baseline: no value model, drops
4-plus PPO hyperparameters, ~46 percent less GPU memory than PPO at 7B with shorter
training. Take: second fallback in the critic-free family, with the strongest reported
memory saving of the three (GRPO/RLOO/ReMax) — relevant if even RLOO's rollout batch
strains 16 GB alongside the embedder adapter. Caution: greedy baseline doubles
generation per step (sample + greedy); net wall-clock may not beat GRPO.
`https://arxiv.org/abs/2310.10505`

**RLAIF (2309.00267).** AI-labeled preferences match RLHF on summarization/dialogue, work
even when the labeler is the *same size/checkpoint as the policy*, and direct-RLAIF
(rewards straight from an off-the-shelf LLM, no reward model trained) performs best.
Take: the license for a frontier-teacher-as-Proof-assistant design — a larger model can
score op traces during RL without training a reward model, and self-labeling (2B judging
2B) is evidence-backed as better than nothing. Caution: judge-policy correlation
overstates gains; hold out a frozen judge for evaluation. `https://arxiv.org/abs/2309.00267`

**DeepSeek-Prover-V1.5 (2408.08152).** RLPAF: a 7B prover refined by RL whose reward is the
*Lean 4 proof assistant's verdict* — a deterministic external checker, exactly Proof's
role — plus MCTS with intrinsic rewards; SOTA on miniF2F (63.5 percent) and ProofNet.
Take: this is the closest published validator-as-reward system and it works at 7B: binary
checker verdict as reward + SFT cold start + RL refinement is a proven stack. Map Lean
verdict onto Proof verdict, tactic search onto op-list search. Caution: Lean feedback is
total (every tactic checked); Proof's quote/format checks are partial validators — expect
more reward hacking (see Verifier-Flaws). `https://arxiv.org/abs/2408.08152`

**One-shot RLVR (2504.20571).** A *single* training example under RLVR lifts
Qwen2.5-Math-1.5B MATH500 36.0 to 73.6 percent, matching a 1.2k-example run; replicates on
Llama3.2-3B and R1-Distill-1.5B with GRPO and PPO; entropy bonus is the critical
ingredient; code Apache-2.0 at ypwang61/One-Shot-RLVR. Take: the strongest evidence that
RL data scale is not the bottleneck at 1.5--3B — a handful of Proof-verified op traces
plus entropy-driven exploration may suffice for the RL stage, which collapses the data
budget for spike 011's RL arm. Caution: effects concentrate on tasks within the base
model's existing capability envelope (also see MATH-Beyond in inventory context and
RL-in-Name-Only); verify the 2B can emit a valid op *at all* before expecting 1-shot
miracles. `https://arxiv.org/abs/2504.20571`

**PEFT-for-RLVR (2512.23165).** First systematic comparison of 12 PEFT methods under
RLVR on R1-Distill models: DoRA/AdaLoRA/MiSS consistently beat standard LoRA; SVD-seeded
inits (PiSSA/MiLoRA) collapse under RL (spectral-collapse diagnosis); extreme reduction
(VeRA, rank-1) bottlenecks reasoning. Take: directly constrains spike 011 — run RL under
DoRA or AdaLoRA, not vanilla LoRA; never PiSSA-init an RL adapter; rank 16 (our spike
004/006 setting) is above the bottleneck zone but re-test rank under RL since the
ordering was established for reasoning, not structured emission. Shared with lane 5.
`https://arxiv.org/abs/2512.23165`

**SuperCorrect (2410.09008).** Two-stage small-model recipe: distill hierarchical
thought templates from a teacher (4.5K seed critiques), then cross-model DPO on teacher
correction traces; 7B student beats DeepSeekMath-7B by 7.8/5.3 points; ICLR 2025; code at
YangLing0818/SuperCorrect-llm. Take: the concrete "distill-then-prefer" pipeline for a
narrow skill (self-correction) at 7B — replace "correction traces" with "Proof-failing
then teacher-fixed op traces" for MelodyScribe. Caution: small repo (90 stars, no
license); treat code as reference, reimplement. `https://arxiv.org/abs/2410.09008`

**DPO (2305.18290).** Collapses RLHF to a classification loss with the optimal policy in
closed form — no reward model, no RL loop. Take: the cheapest possible preference step
between SFT and full RL; use it to burn in "Proof-passing preferred over Proof-failing"
pairs before spending rollout budget. Caution: needs a reference policy in memory (see
SimPO) and is offline — it cannot explore new valid op shapes. `https://arxiv.org/abs/2305.18290`

**SimPO (2405.14734).** Reference-free preference optimization: average-logprob implicit
reward plus a target margin, no reference model, more compute/memory efficient than DPO
across Mistral/Llama-3/Gemma-2 setups. Take: the DPO variant that actually fits 16 GB
alongside an embedding adapter — drop the reference copy, keep the preference signal.
Caution: length normalization interacts with op-list length; watch for short-output bias
against evidence-rich emissions. `https://arxiv.org/abs/2405.14734`

**KTO (2402.01306).** Matches or exceeds preference methods from 1B to 30B using only
*binary* desirable/undesirable labels. Take: Proof already emits exactly this signal
(pass/fail) — KTO lets every validator verdict become training signal without pairing
winners with losers, which fits a harness where failures outnumber successes 2:1.
Highest preference-method priority for MelodyScribe. Caution: prospect-theoretic
asymmetry (loss aversion) needs calibration to Proof's false-positive rate.
`https://arxiv.org/abs/2402.01306`

**Tricks-or-Traps (2508.08221).** Systematic reproduction of RL-for-reasoning techniques
in one open framework with selection guidelines; headline: a minimalist two-technique
vanilla-PPO-loss combo beats GRPO and DAPO. Take: before committing spike 011 to GRPO,
consult its guidelines table — the "simplest combo that works" may be PPO-loss with two
tricks, and its unified framework is the harness to replicate comparisons in. Caution:
preprint, single-group reproductions; treat rankings as priors, not verdicts.
`https://arxiv.org/abs/2508.08221`

**Verifier-Flaws (2502.00271).** Imperfect verifiers misrank candidates and prune all
valid paths, so verifier-guided search falls *below* repeated sampling at scale — across
models (incl. 7B), benchmarks, and verifier types. Take: the central risk register for
Proof-as-reward — a noisy Proof (fuzzy quote matching, date-format edge cases) will
mislead RL exactly this way; invest in Proof precision *before* scaling RL, and keep a
repeated-sampling baseline to detect the crossover. Caution: math-reasoning setting;
op-emission verifiers are stricter (exact-matchable), so the flaw may bite less — measure.
`https://arxiv.org/abs/2502.00271`

**RLVR-Implicit (2506.14245).** Answer-only verifiable rewards still extend the reasoning
boundary (new CoT-Pass@K metric) rather than merely sharpening sampling, with early
training incentivizing correct intermediate steps. Take: partial antidote to
RL-in-Name-Only — even coarse Proof verdicts (pass/fail on the whole op list) can shape
intermediate emission structure, so a per-op dense reward may not be required on day one.
Caution: observational + theoretical mix; the boundary-extension claim is contested
(MATH-Beyond benchmark argues current RL mostly sharpens). `https://arxiv.org/abs/2506.14245`

**LiteGUI (2605.07505).** SFT-free guided on-policy distillation (GKD-style with oracle
trajectories + retrieval) followed by dual-level GRPO, unlocking 2B/3B agents past
imitation limits; automated trajectory-synthesis pipeline included. Take: the only
admitted recipe demonstrated at exactly 2B/3B that *combines* on-policy distillation and
RL without SFT — the closest published analog of spike 011's full plan; its data pipeline
is the template for generating Proof-annotated multi-solution trajectories. Caution:
newest item (May 2026 preprint), GUI-agent domain, no released-code evidence verified —
replicate the recipe, do not depend on artefacts. `https://arxiv.org/abs/2605.07505`

**TinyZero (code, https://github.com/Jiayi-Pan/TinyZero).** 13k-star Apache-2.0 minimal
R1-Zero reproduction at 3B scale on a counting task. Take: the starter codebase for
spike 011's RL arm — read it before touching verl/TRL. Caution: toy task; the RL loop
transfers, the hyperparameters do not. Admitted as artefact (no paper).

**verl (code, https://github.com/volcengine/verl).** 23k-star Apache-2.0 RL post-training
framework with PPO/GRPO trainers; DAPO's system is built on it. Take: the RL backend if
spike 011 outgrows TRL. Caution: cluster-oriented; single-16GB-GB operation needs config
care. Admitted as artefact (no paper).

**open-r1 (code, https://github.com/huggingface/open-r1).** 26k-star Apache-2.0 fully open
R1 reproduction pipeline. Take: recipe reference for the SFT-plus-RL stack and its data
mixes. Caution: pipeline scale exceeds our rig; mine it for config, not compute parity.
Admitted as artefact (no paper).

**TRL (code, https://github.com/huggingface/trl).** 19k-star Apache-2.0 HF
transformer-plus-RL training library. Take: default implementation substrate for
DPO/SimPO/KTO/GRPO experiments at 2B. Caution: API churn; pin a commit. Admitted as
artefact (no paper).

## (b) Refutations

**R1: "GRPO-style RL post-training adds reasoning capability beyond filtered supervised
fine-tuning."** Refuted (with boundary conditions) by RL-in-Name-Only (2505.13697): under
the paper's structural assumptions (concatenated state, uniform trajectory reward split),
the GRPO objective reduces to filtered iterative SFT, and filtered SFT with positives and
negatives matches GRPO on GSM8K/Countdown across model families. Standing: treat RL and
rejection-filtered SFT as competing hypotheses in spike 011 — every RL arm needs a
filtered-SFT control on the same rollouts, or a "win" is uninterpretable. Partially
countered by RLVR-Implicit (2506.14245, boundary extension) and the MATH-Beyond benchmark
(sharpening vs discovery distinction); the honest position is "RL sharpens reliably,
discovers rarely."

**R2 (soft, caution not refutation): "A validator is sufficient as an RL reward."**
Challenged by Verifier-Flaws (2502.00271): imperfect verifiers actively harm selection at
scale. Standing: Proof must be calibrated (precision/recall on quotes, dates) before it
becomes a reward; keep repeated-sampling baselines.

No claim in the brief about distillation methods, LoRA capacity, or dataset construction
was contradicted by lane-4 sources; those belong to lanes 3/5/2.

## (c) Unresolved ledger

1. ORPO (reference-free monolithic preference opt): arXiv id unverifiable — guessed
   2404.10019 disproven via abs fetch (unrelated astrophysics paper), follow-up search
   timed out. Unresolved, low cost: SimPO covers the reference-free niche.
2. V-STaR (verifier-augmented STaR with DPO): id unverifiable — guessed 2310.05689
   disproven (opinion dynamics), text searches empty. Unresolved; STaR + KTO compose the
   same idea from verified parts.
3. Tulu 3 (open post-training recipe): guessed id 2411.15134 disproven (toric
   invariance). Unresolved; DeepSeek-R1 + DAPO + open-r1 cover the recipe space.
4. RAFT (reward-ranked fine-tuning): guessed id 2309.07487 disproven (biomechanics).
   Unresolved; RFT + filtered-SFT controls cover the mechanism.
5. Whether KTO/SimPO preserve embedding quality when the same adapter emits: no lane-4
   source measures retrieval metrics after preference tuning — joint-evaluation gap,
   shared with lane 8.
6. Optimal Proof-reward density (whole-list pass/fail vs per-op credit): RLVR-Implicit
   suggests coarse rewards suffice; Verifier-Flaws warns coarse verifiers mislead; no
   source tests dense vs sparse validator rewards for structured emission.
7. Single-16GB-GB colocated embedding-adapter + RL-loop memory accounting: no admitted
   source runs RL and a contrastive embedder loss on one 16 GB card; ReMax/RLOO memory
   figures are 7B-scale claims, not 2B measurements.
8. LiteGUI artefacts (trajectory pipeline code): release status unverified at screening
   time; recheck before depending on it.

## (d) Security findings

No lane-4 source introduces executable-risk beyond standard training practice. Stated as
requirements: (1) vendor (do not submodule-track) the small unlicensed repos
(jongwooko/distillm, SuperCorrect-llm — no license stated) to keep license exposure
explicit; (2) RL rollouts execute model-generated text only inside Proof/dataset
pipelines — no admitted recipe requires executing generated code, so keep that invariant
(no code-execution rewards) unless a future lane explicitly justifies it; (3) TinyZero/
verl/open-r1/TRL are high-star Apache-2.0 but pin commits and review training-loop code
before running, as RL frameworks execute user-supplied reward functions.
