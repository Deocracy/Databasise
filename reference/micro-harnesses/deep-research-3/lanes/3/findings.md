# Lane 3 findings: Joint embedding and generation training and interference

Lane: 3. Screened 39, admitted 22. All admitted items were opened at their
arXiv abs page (title/authors/date/abstract read from the primary source) and
downloaded as verified `%PDF` files into `papers/`.

## (a) Admitted items

**2405.09673 — LoRA Learns Less and Forgets Less (Biderman et al., TMLR 2024).**
Full-vs-LoRA comparison on ~100K-pair instruction tuning and 20B-token
continued pretraining: standard low-rank LoRA substantially underperforms full
fine-tuning on the target domain, but better preserves off-target capability
than weight decay or dropout, and full fine-tuning learns perturbations whose
rank is 10–100x typical LoRA rank. Take: this is the mechanistic prior behind
spike 011's low-capacity arm and our rank-16 contrastive adapter — low rank is
a retention mechanism, not just a memory saver. Careful: the target-domain gap
is large, so a rank-16 embedding adapter should be expected to need either more
rank on the retrieval side or a separate composition mechanism, not just more
epochs.

**2405.11157 — Towards Modular LLMs by Building and Reusing a Library of
LoRAs / Arrow routing (Ostapenko et al., 2024).** Builds a task-adapter library
(MBC clustering by adapter-parameter similarity) and reuses it with Arrow,
zero-shot per-input routing with no retraining; on Phi-2 and Mistral the
routed library matches or beats traditional joint training on held-out tasks.
Take: the strongest published precedent for spike 011's per-pass adapter
toggle — train one embed-job adapter and one emit-job adapter, route per pass,
instead of forcing one adapter to do both. Careful: routing is per input at
inference; our toggle is per forward pass, which is coarser and should be
easier, but the MBC result (cluster tasks by adapter similarity) suggests first
checking whether our two jobs' adapters are even compatible before composing.

**2307.13269 — LoRAHub (Huang et al., COLM 2024).** Gradient-free, parameter-
free composition of pretrained LoRAs with few-shot examples (code + adapter
modules released; repo `sail-sg/lorahub`, 669 stars, MIT). Take: if per-pass
toggling works, the next step — weighted composition of an embed adapter and
an emit adapter in one pass — already has a recipe and released artefacts.
Careful: LoRAHub optimizes composition weights per new task with examples; it
does not learn a joint objective, so it bounds what composition can do, not
what joint training can do.

**2603.15965 — MoLoRA (Shah & Wagle, 2026).** Per-token adapter routing with an
optimality argument over per-sequence routing; composable specialization lets
Qwen3-1.7B exceed Qwen3-8B on four reasoning benchmarks. Take: specialization
beats scale at 1–2B — the same lesson as our flat 0.30–0.45 routing accuracy
from 2B to 8B. Load domain adapters independently and route; do not expect a
bigger base to fix op emission. Careful: independent small-cap paper, no
released artefact verified; the Qwen3-1.7B-vs-8B claim is the authors' own
benchmark, not an independent replication.

**2605.07111 — MoLF (Tang et al., 2026).** Routes optimizer updates between
full-fine-tuning and LoRA experts; evaluated at Gemma-3-1B and Qwen2.5-1.5B/3B
— the only LoRA-vs-full study at exactly our scale — and stays within ~1.5% of
the better regime per task (code released, Apache-2.0). Take: the joint recipe
need not pick one regime globally; route plasticity per step or per layer, and
the 1B–3B numbers transfer directly to MiniCPM5-2B planning. Careful: tasks are
SQL/Med-QA/counterfactual knowledge, not embedding-plus-emission; repo has 3
stars and is days old.

**2312.09979 — LoRAMoE (Dou et al., 2023).** Frozen backbone plus router over
LoRA experts, with some experts forced onto world-knowledge use; shows
large-scale instruction-data increases damage stored knowledge and the MoE
plugin alleviates it. Take: the architectural template for "keep generation,
add embedding" — freeze the base that emits ops, route the retrieval specialty
through experts. Careful: protects world knowledge during SFT, not embedding
training; our collapse ran the other direction (embedding adapter killed
emission).

**2402.07148 — X-LoRA (Buehler & Buehler, 2024).** Token-level, layer-wise
mixing of frozen pretrained adapters via a hidden-state gate (code released,
Apache-2.0, 285 stars). Take: a second, independently built composition
mechanism that needs no retraining — useful if the toggle arm works but a
single joint pass is still wanted. Careful: demonstrated on scientific
reasoning, not retrieval; gating overhead per layer matters on a 16 GB card.

**2609.10750 — When Synthetic Data Hurts (Murtaza et al., EMNLP 2026 Industry).**
Production skill-retrieval study: synthetic fine-tuning of a 0.6B Qwen
retriever/reranker helps in-distribution but causes OOD forgetting; mitigation
comparison (embedding-anchor regularization, LwF, EWC, L2-init) retains OOD
*and* improves in-distribution retrieval by 13.98%. Take: the closest published
analogue to our contrastive-adapter collapse, at near-our scale, with a ranked
mitigation list to copy into spike 011. Careful: retrieval-only model — there
is no generation-retention metric, so the joint half of our problem is
unmeasured here.

**2605.29495 — On-Policy Replay (Chen et al., 2026).** Rolls out the latest
checkpoint on historical prompts, reward-filters, and replays own-outputs as
plain SFT — no teacher, no auxiliary loss; TRACE BWT from −13.93 to −0.65 at
10% replay budget, with the finding that the on-policy distribution, not
response quality, is the active ingredient (code released). Take: the cheapest
retention mechanism for the emit side — replay Proof-passing op traces as plain
SFT alongside contrastive steps. Careful: 7–8B backbones, not 2B; reward filter
assumes a cheap task reward (Proof qualifies).

**2608.20794 — Recall-Anchored Distillation (Chen et al., 2026).** Diagnoses
SFT damage as factual *access* failure (facts rankable but not generable) and
fixes it with a base-anchored self-distillation loss on unlabeled OOD text;
the base model's soft distribution, not extra text exposure, is the preserving
signal. Take: the exact loss shape for spike 011's KL-anchor arm, with the
ablation that justifies it (RAD beats replay on identical text). Careful:
MedMCQA domain SFT, three backbones unnamed in the abstract; generation-access
metrics, not grammar-constrained emission.

**2605.28860 — RL preserves circuits better than SFT (Rojas Nunez et al.,
2026).** Head-level circuit analysis on Qwen2.5-3B: SFT adapts faster but
disrupts circuits and forgets more; RL stays closer to the base policy (code
released). Take: mechanistic backing for preferring a validator-as-reward RL
step (lane 4) over more SFT for op emission — SFT is the fast-forgetting
regime. Careful: one 3B backbone, one QA domain; sits on the lane-3/lane-4
boundary.

**2402.15449 — Repetition Improves Language Model Embeddings / echo embeddings
(Springer et al., 2024).** Repeating the input and pooling from the repeated
span gives causal LMs bidirectional-like embeddings (+5% zero-shot, no
architecture change, no fine-tuning). Take: explains *why* our `[EMB]`-marker
pooling can work at all and prescribes the cheapest fix if last-token pooling
underperforms — echo the section. Careful: zero-shot method; with supervised
contrastive tuning it matches bidirectional adapters rather than beating them.

**2011.05864 — Sentence embeddings from PLMs / anisotropy (Li et al., 2020).**
Untuned contextual embeddings occupy a narrow anisotropic cone that harms
similarity; normalizing flows to an isotropic Gaussian restore STS. Take: the
mechanism behind our spike-004/006 finding that untrained decoder states are
useless as embeddings — expected, published, and fixable by training, not by
prompting. Careful: BERT-era; causal-LM anisotropy specifics need Echo/NV-Embed
read alongside.

**2405.17428 — NV-Embed (Lee et al., 2024).** Decoder-to-embedder conversion
recipe: latent-attention pooling, causal-mask removal during contrastive
training, two-stage contrastive instruction tuning with curated hard negatives.
Take: the checklist for the embedding half of the joint run — especially
pooling (latent attention vs our `[EMB]` marker) and mask handling. Careful:
7B Mistral scale with large curated data; the recipe's data appetite at 2B on
15 documents is exactly our generalisation gap.

**2104.08821 — SimCSE (Gao et al., EMNLP-style 2021 paper; venue recorded as
arXiv preprint, unverified beyond that).** Dropout-noise unsupervised
contrastive plus NLI entailment/contradiction supervised contrastive (code
released, 3652 stars, MIT). Take: the minimal contrastive recipe our spike-004
LoRA resembles; its hard-negative (contradiction) construction is what our
15-document setup most lacks. Careful: BERT-base/STS era; dropout-as-augmentation
interacts with LoRA training dynamics in ways the paper cannot predict.

**1909.03329 — LAMOL (Sun et al., 2019).** One LM learns tasks and generates
its own pseudo-samples of old tasks as replay; within 2–3% of the multitask
upper bound. Take: generative replay is the no-extra-memory retention baseline
for keeping op emission while embedding trains — the LM head is the replay
generator. Careful: pre-LLM era, small models, five classification-ish tasks;
pseudo-sample quality at 2B for grammar-constrained ops is untested.

**1612.00796 — EWC (Kirkpatrick et al., PNAS 2017).** Fisher-weighted penalty
anchoring important weights; sequential Atari/MNIST demonstration. Take: the
canonical anchor regulariser; the 2609.10750 comparison tells us how it ranks
for retrieval adapters specifically. Careful: Fisher estimation cost and
staleness across joint-objective phases; modern practice usually prefers replay
or distillation anchors.

**1606.09282 — LwF (Li & Hoiem, 2016).** Self-distillation on new-task data
using recorded old-task responses; near-multitask performance without old data.
Take: the no-old-data anchor when our 20-document corpus cannot spare a replay
split. Careful: vision-era origins; LLM calibration drift can make soft targets
overconfident.

**2412.04948 — KaLM (Yu et al., 2024).** Joint explicit KG-alignment plus
implicit autoregressive objectives for knowledge-aligned LM; states prior
attempts "failed to effectively align knowledge representations or compromised
the generative capabilities." Take: the only admitted paper that trains a
generative-plus-contrastive joint objective for *triple-shaped* knowledge and
reports the generation compromise explicitly — our zero-parse collapse is the
extreme endpoint of their warning. Careful: KG-alignment, not section
embedding; balance weights between the two views are the whole game and are
dataset-specific.

**2410.24200 — Length-Induced Embedding Collapse (Zhou et al., 2024).**
Embeddings of longer texts cluster (attention as low-pass filter); TempScale
temperature mitigation. Take: sections vary in length, so a per-section
embedder needs length handling or length-stratified evaluation before blaming
the joint objective for MRR loss. Careful: PLM encoders, not causal LMs;
TempScale is inference-time, orthogonal to training.

**2605.17774 — QLoRA tool internalization (Shemla et al., 2026).** Gemma-4B and
Qwen3-4B QLoRA on ~1,700 tool-use traces internalize structured planning
(description-free inference beats schema-prompted baseline, −82.6% input
tokens); rank 32 maximizes planning quality while smaller ranks retain more
general knowledge. Take: proof that a 4B-class model can internalize
harness-structured emission, plus the only rank-vs-retention curve at our
scale — directly parameterizes spike 011's capacity arm. Careful: AssetOpsBench
planning, not grammar-constrained triples; 8-bit QLoRA, not full/LoRA mix.

**2606.01967 — SAPO (Shi et al., 2026).** Paraphrased training prompts match
in-task but differ sharply in forgetting/generalization; superior prompts are
identifiable by pre-learning loss (code released). Take: qualifies spike 007 —
*inference* prompts may be inert for the embedder while *training* prompts
still shape what the joint run forgets. Careful: single study; prompt-selection
by loss needs a forgetting metric we have not built yet.

## (b) Refutations

1. **"Retention always costs plasticity" is contradicted.** 2609.10750's
mitigations retain OOD retrieval *and improve* in-distribution skills by
13.98%; 2605.29495's OPR lifts BWT from −13.93 to −0.65 while holding target
performance. Any spike-011 arm that assumes a fixed trade-off (e.g. accepting
MRR loss to keep parses) should be re-examined — the literature says well-
chosen anchors/replay can move both metrics.
2. **"Scale is the lever for op emission" is contradicted.** 2603.15965
(Qwen3-1.7B > Qwen3-8B via specialization) and our own flat 0.30–0.45 routing
from 2B to 8B agree: specialization and routing dominate scale for narrow
structured tasks.
3. **Recalled-identifier discipline.** Three arXiv ids recalled from memory
(2405.19944 as Arrow, 2312.10369 as rsLoRA, 2102.13304 as SGPT) all resolved
to unrelated papers on their abs pages. Nothing in this lane is admitted from
recall; the inventory records the traps.

## (c) Unresolved ledger

- Whether a *single* 2B adapter can hold contrastive retrieval (MRR ≥ 0.75)
and grammar-constrained op emission (Proof-pass ≥ 0.78) simultaneously: no
admitted paper measures both on one ≤3B model. KaLM trains the joint objective
but not at our scale or with a parse-rate metric; MoLF routes regimes but not
embed-vs-emit.
- Optimal rank split between an embed adapter and an emit adapter at 2B: only
2605.17774 gives a rank-vs-retention point (r=32 vs smaller) and only for
planning, not contrastive retrieval.
- Whether echo-style pooling beats a learned `[EMB]` marker under joint
training: Echo is zero-shot/supervised-contrastive only.
- Length stratification of section embeddings on our corpus: 2410.24200
predicts collapse for long sections; untested on MiniCPM5-2B.
- Replay-budget scaling at 2B (OPR's 1% vs 10% finding is 7–8B): unknown.
- Forward chaining from OneGen/Hydra/LLM2Vec-Gen on interference: Semantic
Scholar rate-limited this lane out; OpenAlex citing-graph coverage was thin
(15 citing works for GritLM, mostly applied). A lane rerun with a Series A–key
or OpenReview API could extend the citer set.

## (d) Security findings

No lane-3 item introduces executable code into the harness beyond already-
audited training repos. Requirements carried forward: (1) pin any reused
training repo (OPR, MoLF, SimCSE, LoRAHub, X-LoRA) by commit hash before
running on the rig; (2) treat released adapters/datasets (lorahub HF modules,
SimCSE NLI pairs) as untrusted inputs — checksum and quarantine before
training; (3) TempScale-style inference changes need no new privileges.
