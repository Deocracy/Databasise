# Lane 5 findings: LoRA and PEFT science for forgetting and capacity

Screened 32 candidates; admitted 20 (PDFs in `papers/`). All arXiv ids below were
opened at `https://arxiv.org/abs/<id>` (or a fetched proceedings/HTML page for the
same paper). Three recalled ids were wrong and are on record as disproved in the
inventory — nothing is cited from memory.

## (a) Admitted items

**2106.09685 — LoRA (Hu et al.).** The base method: freeze W, train BA with rank r,
alpha scaling, dropout; no inference latency after merge. What matters for
MelodyScribe is not the method but the ablations: adaptation is rank-deficient
(r=1-4 suffices for the tested NLU/NLG tasks), and adapting W_q+W_v only beats
adapting more matrices at fixed budget on GPT-3. Take: target-module choice is a
first-class capacity knob, and rank 16 is already above what the original
evidence needed. Careful: all of this predates small-model instruction tuning;
the rank-deficiency claim was shown on RoBERTa/GPT-2/GPT-3, not on a 2B chat
model doing contrastive embedding plus structured emission.

**2405.09673 — LoRA Learns Less and Forgets Less (Biderman et al., TMLR 2024).**
The paper behind the lane's slogan, and it both confirms and bounds it: at the
standard r=16 LoRA underperforms full fine-tuning but keeps off-target
performance and generation diversity better than weight decay or dropout; at
r=256 LoRA learns as much as the other methods while still forgetting less on
code — but on math it forgets nearly as much as full fine-tuning. Full-FT
perturbations are 10-100x higher rank than typical LoRA updates. Take: the
slogan holds at low rank and is domain-dependent, not a law. Careful: the r=256
runs use alpha scaling that later work (rsLoRA, Illusion paper) shows is
mismeasured under the default alpha/r rule, so treat the high-rank numbers as
an underestimate of what rank can do.

**2410.21228 — LoRA vs Full Fine-tuning: An Illusion of Equivalence
(Shuttleworth et al., NeurIPS 2025).** Spectral analysis: LoRA writes new
high-ranking singular vectors ("intruder dimensions") that full FT does not,
and forgetting is causally localized in them — scaling their singular values
down cuts pre-training-distribution loss with minimal task loss (e.g. ~0% task
drop for ~33% forgetting drop on QQP at r=8 in one reported setting). With the
common fixed alpha=8, high-rank LoRA converges to lower-rank solutions AND
forgets more; alpha=2r fixes both. Take: forgetting has a mechanism and a
post-hoc dial (downscale intruder singular values), and alpha must grow with
rank. Careful: causal evidence is via post-hoc singular-value surgery, not a
training recipe; continual-learning accumulation results are on RoBERTa-scale
plus one LLaMA2-7B check.

**2401.05605 — Scaling Laws for Forgetting (Kalajdzievski).** The only
quantitative forgetting law found: PEFT (LoRA) still suffers catastrophic
forgetting; forgetting is inverse-linear in fine-tuning loss and follows a
shifted power law in number of parameters tuned and number of steps; proposes
measuring forgetting as pre/post cross-entropy rather than task scores. Take:
steps x params is the forgetting budget — spike 011's 6-epoch, 147 s run sits
at the low end of both axes, which predicts mild forgetting, consistent with
the observed collapse coming from the objective (contrastive pressure on shared
weights) rather than from scale of tuning. Careful: single-author preprint,
Llama-2-7B/OpenOrca only; the power-law constants will not transfer to MiniCPM.

**2312.03732 — rsLoRA (Kalajdzievski).** Proves the default alpha/r scaling
collapses gradients as rank grows and replaces it with alpha/sqrt(r); on Llama
2 + 20k OpenOrca, ranks 4-2048, rsLoRA improves with rank while standard LoRA
flatlines, and no LR sweep on rank 4 recovers the gap. Take: if spike 011 tests
rank > 16 with stock alpha/r, it is testing a crippled high-rank arm — use
alpha/sqrt(r) (or alpha=2r per the Illusion paper) whenever rank varies.
Careful: perplexity evidence only, single-author, no forgetting measurement.

**2402.12354 — LoRA+ (Hayou, Ghosh, Yu, ICML 2024).** Same LR for A and B is
inefficient at width; a fixed ratio eta_B >> eta_A (order 2^1-2^4 depending on
model/init) gives up to ~2x speedup and 1-2% gains at identical cost; reduces
LR tuning to a 1-D search. Take: spike 004/006's single lr=1e-4 for both
matrices is exactly the configuration this paper shows is suboptimal — the
joint recipe should split LRs before concluding capacity is the problem.
Careful: optimal ratio is model/task/init sensitive; the paper's suggested
defaults are starting points, not constants.

**2602.06204 — LR Scaling across LoRA Ranks / muA (Chen, Villar, Hayou, Feb
2026).** Newest guidance: under alpha=r^-1 the optimal LR is rank-invariant;
under constant alpha it scales ~1/sqrt(rank); and LRs tuned on LoRA transfer to
full fine-tuning. Take: pick the scaling regime first, then the LR follows —
this plus rsLoRA/LoRA+ composes into a complete rank/alpha/LR policy for spike
011. Careful: weeks old, unrefereed, theory-heavy; validate the transfer claim
on MiniCPM before trusting it.

**2402.09353 — DoRA (Liu et al., NVIDIA, ICML 2024 Oral).** Decomposes weights
into magnitude + direction, LoRA on direction only; weight-decomposition
analysis shows this mimics full-FT learning patterns (LoRA alone cannot move
magnitude and direction independently). Beats LoRA on LLaMA/LLaVA/VL-BART
commonsense, VL instruction tuning, and video-text. Take: the closest
drop-in capacity upgrade over LoRA with no inference cost; the magnitude term
is a natural home for a KL anchor. Careful: extra magnitude parameters and
training-time normalization cost on a 16 GB rig; no forgetting measurement.

**2404.02948 — PiSSA (Meng et al., NeurIPS 2024).** Initializes A/B from the
principal SVD components of W and freezes the residual; faster convergence and
consistent wins over LoRA from 184M to 70B; QPiSSA beats QLoRA 4-bit on
LLaMA-3-70B/GSM8K. Take: SVD init is cheap (seconds) and strictly dominates
Gaussian init in their sweep — any joint recipe should start adapters from
principal components, not noise. Careful: freezing the residual while updating
principals is the opposite of the forgetting-friendly designs (MiLoRA,
OPLoRA); expect faster learning and worse retention.

**2303.10512 — AdaLoRA (Zhang et al., ICLR 2023).** SVD-parametrized updates
with importance-scored rank allocation across matrices on a cubic budget
schedule; biggest wins at low budgets. Take: rank is not one number — the
joint recipe can spend rank where importance scores say the op-emission loss
needs it and starve the embedding path, or vice versa. Careful: SVD
parametrization + orthogonality regularization adds overhead; importance
scoring needs gradient statistics the 147 s budget may not afford.

**2310.11454 — VeRA (Kopiczko et al., ICLR 2024).** One frozen random A/B pair
shared across all layers, only per-layer scaling vectors trained; 10x fewer
params than LoRA at matched GLUE/E2E quality, plus 7B/13B instruction-tuning
checks; supported in HF peft (verified in peft docs). Take: the extreme
low-capacity anchor for spike 011's lower-capacity arm — if VeRA-scale capacity
recovers op emission while embeddings lag, that bounds how little capacity the
grammar needs. Careful: shared frozen matrices cap expressivity; no forgetting
data.

**2308.03303 — LoRA-FA (Zhang et al.).** Freezes A, trains B only: kills the
A-path activation memory (1.4x cheaper than LoRA) at matched accuracy. Take:
activation memory, not just parameters, is the 16 GB binding constraint for a
joint contrastive+emission run — freeze-A halves the adapter activation bill.
Careful: LoRA-Null's authors report LoRA-FA is poor on Math/Code fine-tuning;
A-frozen adapters may lack exactly the capacity structured emission needs.

**2310.08659 — LoftQ (Li et al., ICLR 2024 Oral).** Alternating optimization
finds quantized Q plus LoRA init jointly, closing the QLoRA gap; converges at
2-bit where QLoRA fails (Llama-2 perplexity 7.85 at 2-bit). Take: if the joint
run needs quantization to fit 16 GB, LoftQ init is the evidenced choice over
naive QLoRA. Careful: alternating SVD/quant steps are a slow CPU-side setup
cost per requantization; 2B-model evidence is thin (7B/13B shown).

**2309.14717 — QA-LoRA (Xu et al., ICLR 2024).** Group-wise quantization +
adaptation rebalances degrees of freedom so the fine-tuned model merges back
to INT4 losslessly; beats QLoRA at 2-4 bit on LLaMA. Take: the mergeable
alternative to LoftQ — matters because MelodyScribe merges adapters for the
single-forward-pass serving design. Careful: group-wise ops complicate the
[EMB]-marker hidden-state read path; verify the embedding survives merge.

**2310.14152 — O-LoRA (Wang et al., EMNLP 2023 Findings).** Sequential tasks
trained in mutually orthogonal LoRA subspaces, no replay; large gains over
continual-learning baselines with generalization to unseen tasks preserved.
Take: the multi-adapter prior art for spike 011's per-pass toggle — orthogonal
subspaces are the simple version of "embed here, emit there." Careful: needs
task IDs at training time; orthogonality cost grows with task count; two jobs
may not need the machinery.

**2510.13003 — OPLoRA (Xiong & Xie, AAAI 2026).** Double-sided projections
constrain updates to the orthogonal complement of the top-k singular subspace,
with a proof that top-k triples are exactly preserved, plus a rho_k subspace
interference metric; tested on LLaMA-2-7B and Qwen2.5-7B across commonsense,
math, and code. Take: the most directly usable anti-forgetting construction —
a 2B-scale-verified projection plus a metric (rho_k) spike 011 can log per arm.
Careful: brand new (Oct 2025), no independent replication; SVD per matrix per
step has a cost to budget.

**2503.02659 — LoRA-Null (Tang et al., AAAI 2026).** Initializes A in the null
space of sampled pre-trained activations, freezes A, trains B; argues init
*space* (not residual distance) is what preserves knowledge; higher rank
trades retention for capacity; head-to-head vs LoRA-FA/PiSSA/MiLoRA. Take: the
cleanest single-knob retention/capacity tradeoff curve in the lane, and it
names the rank knob spike 011 is already turning. Careful: needs representative
activation samples (a corpus dependence); repo has 11 stars and no license.

**2406.09044 — MiLoRA (Wang et al., NAACL 2025).** Updates only minor singular
components, freezes principal ones — PiSSA's mirror image — with wins on
commonsense, math, instruction, and visual-instruction tuning. Take: pairs with
PiSSA as a controlled experiment (principal vs minor updates) for which
subspace the embedding vs emission jobs want. Careful: repo match unconfirmed
(23-star API hit); no forgetting metric, only task scores.

**2307.05695 — ReLoRA (Lialin et al., ICLR 2024).** Periodic merge-and-restart
with jagged LR and partial optimizer reset converts sequential low-rank
updates into high-rank training (to 1.3B, +9-40% speed, 5.5 GB/GPU saved).
Take: a capacity *schedule* rather than a capacity *setting* — merge-restart
cycles could alternate embedding-heavy and emission-heavy phases inside one
run. Careful: requires full-rank warm start, which the 16 GB budget may not
allow; pre-training, not fine-tuning, evidence.

**2403.03507 — GaLore (Zhao et al., ICML 2024).** Full-parameter learning with
low-rank gradient projections: 65.5% optimizer-memory cut, LLaMA-7B pre-train
on a 24 GB card with no warmup, competitive GLUE fine-tuning. Take: the
non-adapter escape hatch — if every adapter recipe trades one job against the
other, GaLore keeps full plasticity under the memory cap. Careful:
8-bit/projection-switching machinery; embedding-readout interaction with
projected gradients is unstudied.

## (b) Refutations

R1 — Against "adapters forget less" as a blanket claim. 2401.05605 shows PEFT
still suffers catastrophic forgetting with power-law scaling in params and
steps; 2405.09673 shows r=256 LoRA forgets nearly as much as full FT on math;
2410.21228 shows fixed-alpha high-rank LoRA forgets *more*. The brief's
spike-006 collapse (adapter kills generation) is consistent with all three:
retention is a property of rank/alpha/steps/objective, not of adapters.

R2 — Against single-LR adapter training (spike 004/006 used lr=1e-4 for the
whole adapter). 2402.12354 proves shared A/B learning rates are inefficient and
that eta_B >> eta_A wins; 2602.06204 shows the optimal LR moves with rank
unless alpha=r^-1. A collapse at one shared LR does not imply the capacity is
insufficient.

R3 — Against rank-16-by-default with stock scaling. 2312.03732 proves alpha/r
collapses gradients as rank grows (rank 16+ is already in the degraded regime
relative to alpha/sqrt(r)); 2410.21228 shows fixed-alpha high rank converges
to low-rank solutions while forgetting more. Any rank sweep without scaling
correction mismeasures rank.

## (c) Unresolved ledger

- LQ-LoRA (2311.12023): verified but not admitted — third quant-LoRA recipe
  after LoftQ/QA-LoRA; ILP bit-allocation could still matter for a 16 GB
  mixed-budget run. Reason: lane scope bound, no PDF.
- Haque 2025 small-model forgetting survey (2504.01241): sub-10B GLUE
  continual-FT with Phi-3.5-mini forgetting least, but prompt-engineering
  confound and no PEFT-vs-FT isolation. Reason: weak evidence.
- (IA)3 (2205.05638): verified minimal-capacity anchor (0.01% params, beats
  full FT few-shot) but no forgetting measurement and repo unverified. Reason:
  era/scope mismatch, no PDF.
- LR-QAT (2406.06385): abs excerpt only, full abs page never opened; 7B QAT on
  24 GB is relevant but narrow. Reason: incompletely verified, no PDF.
- QuAILoRA (2410.14713), AFLoRA (ACL 2024 short), LoRAF (ICLR 2025 workshop):
  secondary-excerpt verification only, no arXiv id opened (AFLoRA/LoRAF). Reason:
  below the primary-source bar for admits.
- QLoRA/TIES/DARE: in prior inventories, not re-screened per brief section 2.
- FourierFT, Delta-LoRA, LoRA-GA, MTLoRA, MoLE-family: never verified (API
  outages consumed the search budget); named here so the gap is explicit, not
  silent. Closest covered neighbor: AdaLoRA (budget allocation), O-LoRA
  (multi-adapter orthogonality).
- No paper found that trains one adapter for contrastive embedding while a
  grammar-constrained decoder stays intact — the joint objective itself is the
  literature gap (expected to be covered by lanes 3/10; no lane-5 paper
  measures generation loss caused by embedding training).

## (d) Security findings (as requirements)

No prompt-injection or model-safety findings in this lane. Supply-chain
requirements before vendoring any artefact: (1) LoRA-Null (11 stars, no
license), MiLoRA repo match (23 stars, no license, officiality unconfirmed),
and PiSSA (no license declared) must not be vendored until license and
provenance are confirmed — prefer Apache-2.0/MIT repos (GaLore, ReLoRA,
LoftQ, QA-LoRA, O-LoRA, AdaLoRA, LoRA). (2) loraplus repo URL from the LoRA+
paper failed to resolve on 2026-09-12; re-verify before cloning. (3) All star
counts above are point-in-time GitHub API reads (2026-09-12), not enduring
facts — re-check at use.
