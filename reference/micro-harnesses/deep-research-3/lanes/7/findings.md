# Lane 7 findings: Small-model post-training recipes from the labs

Scope: what MiniCPM, Qwen (2.5/3) small, SmolLM2/3, Phi-4-mini (+reasoning), Gemma 2/3 small,
LFM2, and Granite (3.0/4.0) disclose about SFT, DPO/preference-opt, and RL stages
(learning rates, data sizes, mixing), plus the independent replications that transfer
to a narrow harness task on one 16 GB GPU. Screened 24, admitted 18. All arXiv
claims below were verified against the fetched abs page and PDF; repo/config claims
against the fetched YAML or README; weight licenses against the Hugging Face API.

## (a) Admitted items

**MiniCPM (2404.06395).** The three-stage base recipe (stable pretrain, decay/anneal,
SFT) plus the Warmup-Stable-Decay scheduler. The transferable result is the annealing
finding: mixing high-quality SFT-style data into the 20B-token exponential-decay phase
beats pretrain-only decay followed by a longer SFT (their A-1 vs A-2 and B-2 vs B-3
ablations), with a separate ~6B-token SFT still required afterwards. MelodyScribe
should take: teach the op-emission format during an anneal-style mixed phase, not only
in a final SFT. Careful: pretraining-scale recipe (1.1T tokens, LR 0.01, batch ~4M
tokens) — only the staging pattern transfers to a 16 GB rig, not the scale.

**MiniCPM4 (2506.07900).** UltraChat v2 as a comprehensive SFT dataset, ModelTunnel v2
for searching hyperparameters on small proxies and transferring them up, and chunk-wise
rollout for load-balanced RL (fixes straggler-idle GPUs on long-tail responses).
MelodyScribe should take: proxy-model hyperparameter search before committing the 2B
run, and chunk-wise/balanced rollouts if spike 011 runs any on-policy stage.
Careful: 8.3T-token pretraining and 8B scale are out of rig reach; the 0.5B variant's
recipe details are thinner than the 8B's.

**Qwen2.5 (2412.15115).** Exact small-model SFT numbers: 1M+ examples, 2 epochs,
sequence length 32768, LR decaying 7e-6 to 7e-7, weight decay 0.1, grad-clip 1.0,
then offline DPO plus online GRPO. MelodyScribe should take: the two-epoch SFT
starting point and the sub-1e-5 LR band for full-model SFT at 0.5-3B. Careful: recipe
is shared across 0.5B-72B with no per-size SFT ablation, so the 0.5B/1.5B may be
under-tuned copies of the flagship schedule.

**Qwen3 (2505.09388).** Four-stage post-training (long-CoT cold start, reasoning GRPO
on only 3995 curated query-verifier pairs with large batch + many rollouts per query,
thinking/non-thinking mode-fusion SFT, general RL) and strong-to-weak distillation for
all models 14B and below: off-policy response distillation first, then on-policy
logit-KL distillation from Qwen3-32B/235B. The headline measurement (Table 21):
on-policy distillation beats continued RL from the same 8B checkpoint while using
roughly 1/10 of the GPU-hours, and only distillation improves pass@64. MelodyScribe
should take: distill the harness behavior from a frontier teacher before spending
budget on RL; keep a KL/logit anchor to the teacher. Careful: teacher logits for a
custom op grammar are only available if the teacher can already emit it — the cold
start still needs SFT data.

**SmolLM2 (2502.02737).** Fully open 1.7B recipe: SFT on SmolTalk, 2 epochs, global
batch 128, seq 8192, LR 3.0e-4; DPO on UltraFeedback, 2 epochs, LR 1.0e-6, beta 0.5,
global batch 128, seq 1024; short-context DPO does not harm 8k context ability.
MelodyScribe should take: this is the closest public LR/step template for a 1-2B
SFT-then-DPO run, including the 300x SFT-to-DPO LR ratio. Careful: post-training data
(SmolTalk, UltraFeedback) is general chat, not structured emission — format following
for an op grammar needs separate evidence.

**SmolLM3 recipe (alignment-handbook + HF blog, no paper).** The only fully-open
dual-mode (think/no-think) reasoning recipe at 3B: mid-training on 140B reasoning
tokens (~4 epochs over OpenThoughts3-1.2M + Nemotron traces), SFT on 1.8B tokens
(1B non-reasoning + 0.8B reasoning, 10 + 12 datasets) for 4 epochs with BFD packing
(SFT config: LR 2.0e-5, cosine-with-min-LR, warmup 0.03, per-device BS 1, 8 nodes GBS
128 — fetched from sft.yaml), then APO-zero preference alignment (LR 1.0e-6, beta
0.05, 1 epoch, GBS 32 — fetched from apo.yaml) on Tulu-3 preferences plus synthetic
Qwen3-32B-chosen / Qwen3-0.6B-rejected pairs, finished by souping APO checkpoints and
a 0.9/0.1 merge with the mid-training checkpoint to recover RULER long-context
scores. MelodyScribe should take: the whole skeleton — reasoning mid-train, mixed
mode SFT, APO-zero over teacher/student pairs, merge-repair for regressions.
Careful: configs assume 8x80GB (SFT) / 2-node (DPO) hardware; the LR/BS numbers must
be rescaled for one 16 GB GPU (see SmolTulu below), and long-context recovery by
merging is a workaround, not a guarantee.

**SmolTulu (2412.08347).** The only independent study of the Tulu-3 pipeline at
135M-1.7B. Finding: LR-to-batch-size ratio effects are task-dependent — reasoning
tasks (ARC, GSM8K) favor higher ratios, pattern tasks favor lower ones at 135M;
at 1.7B the high-ratio variant (SFT LR/BS 11.25e-6) wins IFEval 67.7% and GSM8K
51.6%, while the low-ratio variant wins ARC 57.1%. DPO used length-normalized DPO,
LR 8e-7/BS 12 (high) vs 5e-7/BS 32 (low), beta 5.0, 1 epoch; an RLVR (PPO,
verifiable rewards) follow-up exists on HF. MelodyScribe should take: run SFT/DPO
at higher LR/BS ratios than the big-lab defaults, and expect the harness's
reasoning-ish (routing) vs pattern-ish (verbatim quotes) objectives to prefer
different ratios — tune them separately. Careful: single-author study, small eval
suite; the ratio split may not survive at 2B or on Proof-style metrics.

**Tulu 3 (2411.15124).** The reference open pipeline: SFT, length-normalized DPO on
curated on-policy + off-policy preferences, then RLVR (RL with verifiable rewards)
on math/IF tasks, with decontaminated multi-task evals and released data/code
(allenai/open-instruct). MelodyScribe should take: RLVR is the direct precedent for
using Proof as a reward (verifiable > learned reward model), and the stage order
SFT-DPO-RLVR maps onto spike 011's arms. Careful: demonstrated at 8B/70B Llama-3.1,
not at 1-3B; the RLVR gains may shrink where the base model cannot explore.

**Phi-4 (2412.08905).** A 50-type synthetic-data factory (~400B unweighted tokens:
multi-agent prompting, self-revision, instruction reversal) plus a two-round DPO
design: round 1 on pivotal-token pairs (preference localized to the single token
where good/bad trajectories diverge), round 2 judge-guided on ~850k pairs.
Pivotal-token DPO helps reasoning-heavy tasks (GPQA, MATH); judge-DPO helps
judge-scored tasks (ArenaHard); they stack. MelodyScribe should take: pivotal-token
preference pairs are the natural format for Proof failures (one bad quote/date token
vs the corrected op), and instruction reversal for generating harness prompts from
gold ops. Careful: 14B scale with GPT-4-family teachers; the "surpasses the teacher
on STEM" claim is vendor-measured.

**Phi-4-mini (2503.01743).** 3.8B recipe with enlarged function-calling and
summarization SFT data, code fill-in-the-middle data, and Mixture-of-LoRAs: the
language backbone is frozen while per-modality LoRA routers are trained, giving
interference-free extension. MelodyScribe should take two things: (1) the closest
lab precedent for SFT data targeting function calling at 3-4B; (2) the
freeze-backbone + per-job-LoRA pattern as the architectural answer to spike 011's
adapter-toggle arm. Careful: no per-size ablations published; multimodal LoRAs (460M
speech LoRA) are bigger than a 16 GB rig's adapter budget per skill.

**Phi-4-mini-reasoning (2504.21233).** Complete small-model reasoning recipe on the
3.8B backbone: large-scale mid-training on filtered distilled long-CoT, SFT on
~200K curated CoT, rollout DPO on ~300K pairs (LR 5e-7, 1 epoch, seq 16K), then
verifiable-reward RL (LR 5e-6 class, seq 25K) with prompt rebalancing and
temperature annealing; beats DeepSeek-R1-Distill-Qwen-7B by 3.2 pts on MATH-500.
MelodyScribe should take: the stage sizes (mid-train >> SFT > DPO) and the explicit
choice of distillation-first over RL-first at small scale. Careful: math-only
evaluation; transfer to grammar-constrained emission is untested.

**Gemma 2 (2408.00118).** Ablation evidence that training 2B/9B students with KD
(teacher distribution as target) beats from-scratch training on the same tokens, at
>50x Chinchilla token counts; post-training is SFT (behavioral cloning plus
on-student distillation) + RLHF + averaging across phase checkpoints. MelodyScribe
should take: KD-over-overtraining as the justification for distilling harness
behavior rather than training longer on 20 documents. Careful: teacher is internal
and undisclosed; weights are gated under the custom Gemma license.

**Gemma 3 (2503.19786).** Distillation-native recipe: 256-logits-per-token sampled
KD in pretraining, then post-training as KD from a large IT teacher plus an RL phase
built on BOND/WARM/WARP variants; result is Gemma3-4B-IT competing with
Gemma2-27B-IT. MelodyScribe should take: sampled-logit KD as the cheap teacher
signal when full-logit storage is infeasible, and IT-teacher (not base-teacher)
distillation for harness behavior. Careful: BOND/WARM/WARP details are named, not
specified; weights gated under Gemma license.

**LFM2 (2511.23404).** The most hardware-relevant recipe: SFT 3 epochs, cosine
3e-5 to 1e-7, 500-step warmup from 1e-5, AdamW (0.9/0.95, wd 0.1), grad-clip 1.0,
10% embedding dropout, bf16, ZeRO-2 on 8xH100; preference alignment with
length-normalized direct objectives on offline + on-policy (SFT-checkpoint-sampled)
pairs; then systematic model merging (soup, task arithmetic, TIES, DARE, DELLA) as
a full third stage; tempered decoupled Top-K KD in pretraining to avoid support
mismatch; plus LFM2-Nanos showing the same shop further specializes models for
extraction, tool/function calling, and RAG. MelodyScribe should take: the exact SFT
schedule shape, length-normalized preference objectives (portable to Proof pairs),
and merging-as-a-stage for robustness. Careful: schedule ran on 8xH100-80GB and the
teacher (LFM1-7B) is internal; weights carry a custom LFM license.

**Granite 3.0 (GitHub paper.pdf, no arXiv).** Curriculum SFT followed by PPO/BRAIn
alignment plus best-of-N sampling and model merging, with explicit function-calling
support at 1-3B (MoE) and 2-8B (dense); pretraining uses a two-stage 10T+2T mix and
a Power-law LR scheduler for hyperparameter transfer. MelodyScribe should take:
BRAIn + merging as an alternative RL stack to GRPO, and curriculum SFT ordering.
Careful: admitted via the repo (paper.pdf has no arXiv id, so integrators cannot
file it under papers/); vendor evals are primary only for what IBM reports.

**Granite 4.0 (GitHub repos + IBM docs, no arXiv).** Recipe explicitly aimed at
structured JSON output, fill-in-the-middle code, RAG, and tool/function calling,
with a 3B Micro (dense transformer and hybrid variants) that per IBM beats
Granite-3.3-8B. MelodyScribe should take: the 3B84205? No — the 3B-micro-as-harness
existence proof for structured emission plus RAG at rig scale. Careful: recipe
details in the fetched READMEs are high-level (SFT + RL alignment + merging named,
not specified); treat capability claims as vendor-reported, not independently
verified.

**APO (2408.06266).** APO-zero (push winner up, loser down) vs APO-down (push both
down, loser more) framing with the selection rule keyed to whether the winning
outputs beat the current model; 32K CLAIR revision pairs + APO-zero give +7.65% on
MixEval-Hard, closing 45% of the gap to GPT-4-turbo. MelodyScribe should take:
APO-zero over teacher-revised Proof failures (winner = corrected op, which beats
the 2B), APO-down only if the preference data is weaker than the model — and
SmolLM3's choice of loss_type apo_zero corroborates it. Careful: demonstrated at
8B; the CLAIR revision procedure needs a capable reviser.

**APO-hinge-zero (2508.08466).** Margin-hinge variant of APO-zero aimed at 0.5B
models: zero gradient once a pair's margin is satisfied, concentrating updates on
hard pairs; best AlpacaEval win rate (36.02%) and length-controlled rate (17.07%)
in its comparison. MelodyScribe should take: a candidate objective if preference
training at 1-2B saturates on easy pairs. Careful: small-scale study, AlpacaEval
only plus narrow MT-Bench slices — provisional, needs replication on Proof metrics.

## (b) Refutations

- **Brief section 1 size label "MiniCPM5-2B".** The fetched OpenBMB/MiniCPM README
  (primary for what the vendor ships) lists MiniCPM5-1B, released 2026-05-19, as the
  first model of the MiniCPM5 series; no MiniCPM5-2B checkpoint appears. Either the
  rig model is MiniCPM5-1B under a 2B label or it is a non-public checkpoint. The
  recipe evidence in this lane is unaffected, but size-dependent claims should be
  re-checked against the actual checkpoint. (Refute row in inventory.tsv.)

No other brief claim is directly contradicted: the Qwen3 distillation-beats-RL
measurement (2505.09388 Table 21) constrains but does not refute spike 011's RL arm
(RL still helps after distillation in Qwen3's own pipeline), and the SmolTulu
task-dependence finding complicates but does not refute any single-LR assumption in
the brief.

## (c) Unresolved ledger

- **MiniCPM3-4B recipe.** Abstain: only the HF model card was fetched; it discloses
  function calling as a capability but no training recipe beyond citing 2404.06395.
- **MiniCPM5-1B post-training recipe.** Abstain: release notes fetched; no SFT/DPO/RL
  disclosure for the exact rig-model series.
- **Qwen3-Embedding (2506.05176).** Abstain (out of scope): round-2 item, screened
  only to deduplicate.
- **LFM2-Nanos (extraction/tool-call/RAG specialists).** Abstain: announced in the
  LFM2 report with weights on HF, but no standalone recipe was fetched; closest to
  MelodyScribe's deployment shape, so worth a follow-up fetch.
- **Smol Training Playbook.** Abstain: secondary long-form guide; its checkable
  recipe claims resolve to the admitted SmolLM2/SmolLM3 primaries.
- **Per-size LR/BS schedules below 1B on 16 GB.** Unresolved: SmolTulu covers
  135M/1.7B, vendors report shared schedules; no primary source gives a 2B-on-single-GPU
  SFT/DPO schedule with gradient-accumulation equivalence. This is spike 011's gap
  to close empirically.

## (d) Security / compliance findings (requirements)

- **R1 — License tracking.** Admitted artefacts span Apache-2.0 (MiniCPM, SmolLM,
  Tulu-3 code, Qwen3 weights, Granite, Phi-4-mini weights under MIT), gated custom
  licenses (Gemma weights under Gemma Terms of Use; LFM2 weights under custom LFM
  terms; Tulu-3 stage checkpoints under Llama-3.1 terms). Any training-data reuse
  must record per-artefact license before ingesting teacher outputs or preference
  data derived from gated weights.
- **R2 — Gated access in CI.** Gemma weights require manual gated access; automated
  single-GPU replication pipelines must not assume anonymous download. Prefer
  ungated Apache-2.0/MIT artefacts (SmolLM, Qwen3 small, Phi-4-mini, Granite) for
  reproducible spike-011 baselines.
- **R3 — Safety-data handling.** Several recipes mix 1-5% safety/hallucination SFT
  and DPO data (Phi-4 two-round DPO, Granite safety alignment). A harness
  fine-tune that strips safety mixtures to save capacity must document the removal
  and re-run the vendor safety evals it can afford, or explicitly scope the model
  to non-user-facing harness use.
- No remote-execution, credential, or data-exfiltration vectors were found in the
  fetched configs, READMEs, or paper texts reviewed for this lane.
