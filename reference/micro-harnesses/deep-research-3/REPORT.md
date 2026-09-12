# Deep-research round 3: training one small model to embed and to generate structured outputs

Integrator report. Inputs: `lanes/<n>/findings.md` and `lanes/<n>/method.md` for lanes 1-10,
`merged/INVENTORY.tsv` (288 unique items after dedup of 326 lane rows), `merged/SUMMARY.md`,
and 227 staged PDFs in `merged/papers/`. No item is admitted from memory; every claim below
traces to a lane finding or an inventory row. Per-lane full takeaways live in
`lanes/<n>/findings.md`; this report synthesizes and ranks.

Counts: 224 admitted (221 clean inventory rows plus 3 lane-9 rows repaired from a merge
column shift, documented in part 9), 6 refuted, 58 abstained.

## 1. Verdict

**Q1 — fine-tuning small models for structured/constrained generation.** Narrow-task SFT
works at 1-3B: TinyAgent (2409.00608) takes a 1.1B model from 12.7% to ~80% plan success,
beating GPT-4-Turbo inside its harness; APIGen (2406.18518) trains a 1.3B model past GPT-3.5
on function calling with a 3-stage verified dataset; Granite (2407.00121) and Hammer
(2410.04587) confirm the recipe shape (multi-task SFT, function masking, LoRA r8-r16).
Syntax failures are a decoding problem, not a training problem: SynCode (2403.01632) gives
100% JSON-schema validity on a 2B model with CFG-guided decoding, and Outlines
(2307.09702) provides FSM-constrained decoding at ~O(1) per step — so the 30-50% Proof
failure mass in spike 003 should be split into grammar-fixable (dates, shapes, enums) and
training-fixable (verbatim quotes, fact selection) before any data budget is spent.
Two mandatory dataset rules: format-following is an independent skill that does not come
free with SFT (FoFo, 2402.18667), and op-emission SFT without abstention negatives teaches
the model to always emit (Hammer, 2410.04587, section 5.6; ~12.5% no-op ratio used).

**Q2 — building fine-tuning datasets from documents.** The pipeline shape is settled:
seed/generate with a frontier teacher (Self-Instruct 2212.10560, Magpie 2406.08464,
Humpback/backtranslation 2308.06259, Bonito conditional generator 2402.18334), expand
with Evol-Instruct operators (WizardLM 2304.12244, WizardCoder 2306.08568 proof of
narrow-task transfer), filter in stages (metric rules per Instruction Mining 2307.06290,
LLM judge per AlpaGasus 2307.08701, Proof verdict as final gate per APIGen/Toolformer
patterns), deduplicate exactly and semantically (2107.06499, SemDeDup 2303.09540), and
fit slice mixtures on proxies (DoReMi 2305.10429, RegMix 2407.01492). Quantity guidance:
~1K extreme-curation gold examples can align format (LIMA 2305.11206), thousands of
narrow examples move small models (ToolAlpaca 2306.05301, WizardCoder), and 5% influence-
selected subsets beat full data (LESS 2402.04333, DEITA 2312.15685). No study measures a
small-model (<=3B) SFT data-quantity scaling law directly; that curve must be measured on
the rig.

**Q3 — one model for embedding and generation.** No admitted paper trains one <=3B model
for contrastive retrieval and grammar-constrained emission simultaneously and measures
both — that joint measurement is spike 011's to make and is the central gap of this
round. What exists: co-training works at 7B+ (RA-DIT 2310.01352 matches expensive
pre-training with light dual tuning; RankRAG 2407.02485 co-trains ranking and generation
with a small ranking-data fraction; Self-RAG 2310.11511 emits control tokens from the
same weights; CorpusLM 2402.01176 unifies retrieval identifiers and answers in one
decode), theory says generative retrieval decomposes into bi-encoder dot products so the
objectives are compatible (2306.11397), and KaLM (2412.04948) warns explicitly that prior
joint attempts compromised generation — consistent with the spike-006 zero-parse
collapse. Retention machinery to copy: KL/base-anchored self-distillation (Recall-Anchored
Distillation 2608.20794, where the soft distribution — not replay text — is the active
ingredient), on-policy reward-filtered replay as plain SFT (2605.29495, TRACE BWT -13.93
to -0.65), embedding-anchor regularization with a ranked mitigation list at 0.6B
(2609.10750, +13.98% in-distribution with OOD retained), and per-pass adapter separation
instead of one shared adapter (Arrow routing 2405.11157 matches/beats joint training;
LoRAHub 2307.13269 composes adapters gradient-free; X-LoRA 2402.07148 mixes frozen
adapters per token/layer; MoLF 2605.07111 routes optimizer regimes at exactly 1-3B).
Spike 011's toggle arm is therefore the best-supported starting shape; the single-adapter
joint loss is the experiment, not the default.

**Q4 — distillation and RL on one 16 GB GPU.** Distillation first, RL second: Qwen3
(2505.09388, Table 21) measures on-policy distillation beating continued RL from the same
checkpoint at ~1/10 GPU-hours; sequence-level teacher traces transfer structured behavior
(1606.07947); reverse-KL on-policy distillation fits emission (MiniLLM 2306.08543) with
the off-policy cost fix (DistiLLM 2402.03898, up to 4.3x) and a contrastive term that can
absorb Proof-rejected ops as negatives (DistiLLM-2 2503.07067). Rejection-filtered SFT is
the mandatory control for every RL arm: RL-in-Name-Only (2505.13697) reduces GRPO to
filtered iterative SFT under stated assumptions, RFT (2308.01825) finds log-linear gains
with the weakest models gaining most, and STaR (2203.14465) is the Proof-filtered
flywheel template. If RL runs: GRPO (DeepSeekMath 2402.03300) only with the Dr.GRPO
unbiasing fix (2503.20783, since Proof failures correlate with long rambling op lists),
DAPO-style dynamic sampling to skip zero-gradient groups (2503.14476), RLOO
(2402.14740) or ReMax (2310.10505, ~46% less memory than PPO at 7B) as critic-free
fallbacks, and DoRA/AdaLoRA — never vanilla LoRA or PiSSA init — under RLVR per the
only PEFT-under-RLVR study (2512.23165). The closest validator-as-reward precedent is
DeepSeek-Prover-V1.5 (2408.08152), where a Lean 4 verdict rewards a 7B prover; the
closest full 2B/3B recipe is LiteGUI (2605.07505, GKD-style on-policy distillation plus
dual-level GRPO, no SFT). Preference steps that fit 16 GB: KTO (2402.01306) consumes
Proof's binary pass/fail directly without pairing winners and losers; SimPO
(2405.14734) drops the reference model. Proof precision must precede RL scale
(Verifier-Flaws 2502.00271).

**Q5 — LoRA/PEFT and forgetting.** "Adapters forget less" holds at low rank and is
domain-dependent, not a law (2405.09673; r=256 forgets nearly as much as full FT on
math; 2410.21228 localizes forgetting in high-ranking intruder singular vectors with a
post-hoc downscaling dial, and shows fixed-alpha high rank forgets more; 2401.05605
gives the only quantitative law — forgetting inverse-linear in FT loss, power-law in
params-times-steps, which predicts mild forgetting for the 147 s spike-004 run and
points at the contrastive objective, not tuning scale, as the collapse cause). Three
corrections to spike 004/006 settings before concluding capacity is the problem: use
alpha/sqrt(r) or alpha=2r whenever rank varies (rsLoRA 2312.03732; 2410.21228), split
A/B learning rates with eta_B >> eta_A (LoRA+ 2402.12354), and follow the rank/LR
regime policy (muA 2602.06204). Constructions worth arms: OPLoRA orthogonal projections
with a rho_k interference metric (2510.13003), LoRA-Null null-space init with a clean
retention/capacity knob (2503.02659), MiLoRA-vs-PiSSA principal/minor subspace pairing
(2406.09044 vs 2404.02948), O-LoRA orthogonal subspaces for the toggle (2310.14152),
VeRA as the extreme low-capacity anchor (2310.11454), LoRA-FA for activation memory
(2308.03303), LoftQ/QA-LoRA if quantization is needed with a mergeable end state
(2310.08659, 2309.14717), and GaLore full-plasticity-under-memory-cap as the non-adapter
escape hatch (2403.03507).

**Q6 — composing outputs for a frontier consumer.** End-task filtering beats
looks-like-a-good-summary: RECOMP (2310.04408) keeps the candidate payload that makes
the frozen consumer right, with selective augmentation (emit nothing when retrieval is
useless); contrastive perplexity is the cheapest query-aware salience signal plus
mandatory reordering against position bias (LongLLMLingua 2310.06839; Lost-in-the-Middle
2307.03172, which with Robust-RALM 2310.01558 refutes any more-payload-helps assumption);
a 1,000-example mixed relevant/irrelevant fine-tune is the cheapest robustness arm
(2310.01558); collapsed multi-level retrieval (leaf quotes plus parent summaries) is the
assembly pattern for sectioned documents (RAPTOR 2401.18059); Voyager (2305.16291) is
the Folio blueprint (model-written, embedding-indexed, compositional, verifier-gated
admission) with the Folio-utility experiment still unrun; ARES (2311.09476) gives the
three-metric payload-to-consumer protocol (relevant? grounded? answering?) with PPI
intervals from ~150-300 human labels. Soft-vector payloads (gist 2304.08467, ICAE
2307.06945, AutoCompressors 2305.14788, xRAG 2405.13792) support the [EMB]-marker
mechanism but are consumer-locked and unverifiable by Proof — text payloads with
verbatim quotes stay mandatory. No public work measures a frontier consumer's answer
quality as a function of payloads built by a <=3B grammar-constrained composer.

**Final verdict on the working conclusion.** The literature supports the owner's thesis:
a fine-tuning dataset plus a joint recipe is the remaining problem, and no published
system has closed it. The closest existing systems are CorpusLM (2402.01176) for
architecture (one decode, identifiers plus grounded answer) — lacking an embedding
objective, small scale, and a grammar; RA-DIT (2310.01352) for training (light dual
tuning, LM supervises retriever) — lacking a <=3B demonstration and constrained
emission; TinyAgent (2409.00608) for the narrow-harness win at 1B — lacking embeddings,
grammar, and evidence grounding; and LiteGUI (2605.07505) for the 2B/3B combined
distill-plus-RL recipe — lacking the embedding half and verified artefacts. The sourced
recipe is: APIGen/SynthIE-style Proof-gated teacher data, Arrow-style adapter separation
with a KL anchor and replay, distill-then-preference-then-RLVR staging, grammar at
decode time, and a KILT-gated joint metric with PPI intervals. Each step is detailed in
part 5 with spike-011 arm mappings.

## 2. Top twenty

Ranked by expected leverage on MelodyScribe's joint problem (narrow-harness precedent,
dataset recipe, joint-training mechanism, evaluability), not by citation count.

1. **TinyAgent (2409.00608).** Narrow-task SFT (curated data, LoRA, negatives,
ToolRAG) takes TinyLlama-1.1B from 12.7% to ~80% plan success, beating GPT-4-Turbo
in-harness. Take: the single most encouraging precedent that a 1B model can beat a
frontier model inside a harness — exactly the claim MelodyScribe needs for op
emission. Careful: one 16-tool domain, no embedding objective, no grammar, no
evidence grounding; its retriever is a separate DeBERTa, not shared weights.

2. **APIGen (2406.18518).** Three-stage verification pipeline (format checker, real
execution, LLM semantic checker) over 3,673 APIs; 1.3B beats GPT-3.5, 6.7B beats
GPT-4o on BFCL; 60k entries released (`Salesforce/xlam-function-calling-60k`).
Take: the dataset-recipe top pick — substitute Proof for stages 1-2, keep a
teacher-judge for stage 3, and apply the strictest filtering to weak-generator
data. Careful: single-turn REST/Python calls, not document-grounded extraction.

3. **RA-DIT (2310.01352).** Dual instruction tuning (retrieval-augmented LM tuning
plus LM-supervised retriever tuning) matches expensive Atlas-class pre-training at
7B/13B/65B with parametric knowledge intact on 7/8 controls.
Take: no retrieval-specific pre-training is needed; fine-tune both sides lightly
with the LM supervising the retriever. Careful: smallest LM tested is 7B; the
preservation result must be re-tested at 2B with Proof-pass, not QA accuracy.
Code: `https://github.com/facebookresearch/RA-DIT` (3 stars; no machine-readable license).

4. **Self-RAG (2310.11511).** One LM learns offline-critic-inserted reflection
tokens (retrieve/relevant/supported/useful) as ordinary next tokens; 7B/13B beats
ChatGPT on QA, reasoning, and fact verification with adaptive retrieval.
Take: the training pattern for Proof-shaped gates (emit/retrieve/abstain) inside
the small model. Careful: GPT-4-distilled data, frozen Contriever, and 7B scale;
reflection-token reliability at 2B is unproven. Models released;
`https://github.com/AkariAsai/self-rag`.

5. **RankRAG (2407.02485).** One instruction-tuned LLM does context ranking and
answer generation; a small ranking-data fraction beats expert rankers and lifts
nine RAG benchmarks at 8B/70B. Take: ranking and generation co-train with
surprisingly little ranking data — calibrate the joint loss toward a small
contrastive fraction. Careful: 8B scale; the ratio needs re-tuning at 2B where
capacity binds. Paper only, no verified repo.

6. **LoRA Learns Less and Forgets Less (2405.09673).** Full-vs-LoRA comparison:
low-rank LoRA underperforms full FT on target but preserves off-target capability;
full-FT perturbations are 10-100x typical LoRA rank. Take: the mechanistic prior
for the low-capacity arm — low rank is a retention mechanism, not just a memory
saver. Careful: the target-domain gap is large, so expect to need more retrieval
rank or a composition mechanism, not more epochs. TMLR 2024.

7. **MiniLLM (2306.08543).** Reverse-KL on-policy distillation for generative LMs
(120M-13B); fixes teacher-tail over-coverage and exposure bias. Take: the correct
divergence when the student must emit narrow structured ops. Careful: needs
teacher logits on student rollouts (white-box teacher, memory cost); pair with
DistiLLM's off-policy reuse. Code/data/checkpoints: `https://github.com/microsoft/LMOps` (MIT).

8. **DeepSeek-Prover-V1.5 (2408.08152).** RLPAF: a 7B prover refined by RL on the
Lean 4 proof-assistant verdict plus MCTS; SOTA on miniF2F/ProofNet. Take: the
closest published validator-as-reward stack (binary checker verdict plus SFT
cold start plus RL refinement) — map Lean verdict to Proof verdict, tactic
search to op-list search. Careful: Lean feedback is total; Proof's checks are
partial, so expect more reward hacking.

9. **SynthIE (2303.04132).** Asymmetric synthesis: LLM writes text from triples
(1.8M points), small models (220M/770M) learn triples-from-text and beat prior
SOTA by +57 micro-F1, with humans rating synthetic data above existing sets.
Take: copy the direction — teacher writes documents from gold ops, student learns
ops-from-documents. Careful: no out-of-distribution generalization without the
diversity/filtering steps (shown by BoostCD 2506.14901).
Code/data/models: `https://github.com/epfl-dlab/SynthIE` (MIT).

10. **GenIE (2112.08340).** First end-to-end autoregressive closed IE: BART
generates relations/entities under bi-level constrained generation so only
schema-valid triplets are producible. Take: constraints as part of the
training/inference contract, exactly what Proof needs at the op-emission end.
Careful: REBEL distant supervision gives weak triple-text alignment — the same
evidence-quote failure as spike 003. Code plus 27.7 GB data/models:
`https://github.com/epfl-dlab/GenIE` (MIT).

11. **Hammer (2410.04587).** Function masking plus 7.5k irrelevance-augmented
abstention examples over xLAM-60k; 1.5B/4B/7B, Apache-2.0. Take: masking as a
cheap regularizer arm, and the no-op training template ("emit nothing when the
section supports nothing"). Careful: its section 5.6 refutes naive SFT — without
negatives, fine-tuning creates an inverse accuracy/abstention relationship.

12. **SynCode (2403.01632).** Sound/complete CFG-guided decoding with offline DFA
masks; Gemma2-2B reaches 100% JSON-schema validity at ~10% overhead. Take: the
syntax half of Proof failures is solvable at inference with no training change.
Careful: schema validity is not semantic validity — no grammar checks a quote
against unseen source text. `https://github.com/structuredllm/syncode` (MIT).

13. **Qwen3 (2505.09388).** Four-stage post-training; small models (<=14B) via
off-policy then on-policy distillation from 32B/235B teachers; on-policy
distillation beats continued RL at ~1/10 GPU-hours while only distillation
improves pass@64. Take: distill harness behavior before spending RL budget; keep
a KL/logit anchor to the teacher. Careful: teacher logits for a custom op
grammar require a cold-start SFT first. Weights Apache-2.0 on HF.

14. **Tulu 3 (2411.15124).** Fully open SFT plus length-normalized DPO plus RLVR
pipeline with decontaminated evals. Take: the reference stage order
SFT-DPO-RLVR for spike 011, and RLVR as the direct precedent for Proof-as-reward;
SmolTulu (2412.08347) replicates it at 1.7B with LR/BS-ratio guidance.
Careful: demonstrated at 8B/70B, not 1-3B. Code/datasets/checkpoints:
`https://github.com/allenai/open-instruct` (Apache-2.0 code; stage models under Llama-3.1 terms).

15. **ReLiK (2408.00103).** Retriever proposes candidates, a shared reader links
spans and predicts relations in one forward pass; SOTA EL+RE down to tiny/small
checkpoints. Take: existence proof that sub-billion extraction is SOTA when
retrieval narrows the decision space — the closest architectural cousin to one
forward pass per section. Careful: closed IE only, no Folios or free-text
rationales. Code/checkpoints: `https://github.com/SapienzaNLP/relik`.

16. **RECOMP (2310.04408).** Extractive (contrastive on sentences leading to
correct outputs) and abstractive (distilled, downstream-filtered) compressors
against a frozen consumer, with selective augmentation; 5-10% token budgets at
small relative drop, transferring across consumers. Take: end-task filtering
(keep the payload that makes the consumer right) and empty-string augmentation
for useless sections. Careful: the compressor is a separate encoder-decoder, not
the embedder's weights — silent on interference. Code:
`https://github.com/carriex/recomp`; compressors on Hugging Face.

17. **xRAG (2405.13792).** Two-layer projector (<0.5% params) maps a frozen dense
retrieval embedding to one token for a frozen LLM; +10% average over six
knowledge tasks at 3.53x fewer FLOPs. Take: the headline external support that a
retrieval embedding already contains nearly as much usable content as the text —
one forward pass can serve both jobs. Careful: single-document only,
consumer-specific projector, and soft tokens are unverifiable by Proof.
NeurIPS 2024.

18. **ARES (2311.09476).** Synthetic in-domain QA plus fine-tuned lightweight
judges on context relevance, faithfulness, answer relevance, calibrated with
prediction-powered inference from ~150-300 human labels; beats RAGAS by wide
margins and resolves near-tied systems. Take: the payload-to-consumer eval
protocol plus affordable human calibration. Careful: judges are domain-fitted
(an NQ-tuned judge only reaches tau 0.38 on extraction) — op judges need
in-domain data and their own validation. Code:
`https://github.com/stanford-futuredata/ARES` (Apache-2.0).

19. **KTO (2402.01306).** Matches/exceeds preference methods from 1B to 30B using
only binary desirable/undesirable labels. Take: Proof's pass/fail is already the
required signal — every validator verdict becomes training signal without
winner/loser pairing, fitting a harness where failures outnumber successes 2:1.
Careful: the prospect-theoretic asymmetry needs calibration to Proof's
false-positive rate.

20. **CorpusLM (2402.01176).** One model unifies generative retrieval, closed-book
generation, and RAG in a single greedy DocIDs-References-Answer decode with
ranking-oriented DocID-list training. Take: the closest published architecture to
MelodyScribe — train on ranked identifier lists plus DocID-semantics
auxiliaries. Careful: backbone/scale details unverified here; DocIDs are corpus
identifiers, not a section/op grammar. SIGIR 2024; paper only.

## 3. Refutations

Every claim below is contradicted by a fetched primary source. Lane-1/3/4/5/10
refutations rest on admitted papers; lane-7 and lane-8 refutations carry
disposition `refute` in the inventory.

- **More function-call SFT is purely beneficial.** Refuted by Hammer (2410.04587,
section 5.6): fine-tuning on selection data created an inverse relationship
between call accuracy and irrelevance detection. Op-emission SFT without
abstention negatives will teach always-emit.
- **Scale (2B to 8B) or general instruction tuning fixes schema adherence.**
Refuted by FoFo (2402.18667, format-following independent of content quality,
open models trailing) together with spike 003's flat 0.30-0.45 routing; and by
Pradeep et al. (2305.11841, naive parameter scaling can hurt at 8.8M passages).
- **Training is the only lever on Proof-pass syntax failures.** Qualified by
SynCode (2403.01632) and Outlines (2307.09702): grammar decoding reaches 100%
schema validity on 2B models with no training change. Split Proof failures into
syntax (decoding) vs grounding (training) or gains will be misattributed.
- **Retention always costs plasticity.** Contradicted by 2609.10750 (anchors
retain OOD and gain +13.98% in-distribution) and 2605.29495 (replay lifts TRACE
BWT -13.93 to -0.65 while holding target performance). Do not accept MRR loss as
the price of parses without testing anchors/replay first.
- **Adapters forget less, as a blanket claim.** Refuted by 2401.05605 (PEFT
still forgets catastrophically; power-law in params-times-steps), 2405.09673
(r=256 LoRA forgets nearly as much as full FT on math), and 2410.21228
(fixed-alpha high-rank LoRA forgets more). Retention is a property of
rank/alpha/steps/objective, not of adapters.
- **One shared LR and default alpha/r are adequate for adapter training.**
Refuted by LoRA+ (2402.12354, shared A/B LRs inefficient, eta_B >> eta_A wins),
rsLoRA (2312.03732, alpha/r collapses gradients with rank), and muA
(2602.06204, optimal LR moves with rank unless alpha=r^-1). The spike-004/006
collapse at one shared lr=1e-4 does not imply insufficient capacity.
- **GRPO-style RL adds reasoning beyond filtered SFT.** Refuted with boundary
conditions by RL-in-Name-Only (2505.13697, disposition refute): under its
structural assumptions GRPO reduces to filtered iterative SFT, matched by
filtered SFT on GSM8K/Countdown. Every RL arm needs a filtered-SFT control on
the same rollouts. Partially countered by RLVR-Implicit (2506.14245, boundary
extension); honest position is RL sharpens reliably and discovers rarely.
- **A validator suffices as an RL reward.** Challenged by Verifier-Flaws
(2502.00271): imperfect verifiers misrank and prune all valid paths so guided
search falls below repeated sampling at scale. Proof precision precedes RL
scale; keep a repeated-sampling baseline.
- **The rig model is MiniCPM5-2B.** Refuted by the vendor README (lane 7,
primary for what ships): the MiniCPM5 series' first release is MiniCPM5-1B
(2026-05-19); no MiniCPM5-2B checkpoint appears. Either the rig model is
mislabeled or non-public; size-dependent claims should be re-checked against
the actual checkpoint. (No inventory row; the brief's own label is refuted.)
- **A frontier model is a neutral judge of payload quality.** Refuted by Zheng
et al. (2306.05685, position/verbosity/self-enhancement biases; disposition
refute) and Liu et al. (2303.16634, G-Eval-4 scores GPT-3.5 above human text
humans prefer; disposition refute). No judge score is admissible without
swap-averaging, length control, and human-agreement calibration.
- **Raw win rates rank correctly.** Refuted by Dubois et al. (2404.04475,
length bias; length control lifts Arena correlation 0.94 to 0.98; disposition
refute). Length-control or fix payload budgets before ranking spike-011 arms.
- **Reference-based F1 measures extractor quality.** Refuted by Tan et al.
(2205.12696, 64.6% of DocRED triples missing; re-annotation lifts ~13 F1 with
no model change; disposition via Re-DocRED admit, refutation recorded in lane
8). Proof failures against incomplete references overstate model error; the
parity corpus needs a completion pass.
- **Small-n wins are statistically significant.** Refuted by Smucker et al.
(SIGIR 2009, 10.1145/1571941.1572050; disposition refute): agreeing tests at 50
topics disagree toward n=10, bootstrap biased to smaller p-values. With 20
documents, report PPI intervals and effect sizes, never bare p-values.
- **Public held-out sets are clean.** Refuted by Sainz et al. (2310.18018;
disposition refute): ChatGPT-era models absorbed benchmarks including CoNLL03;
every benchmark needs per-model contamination measurement. The private parity
corpus is the only trustworthy final gate.
- **An answer-relevance judge transfers to scoring op emission.** Refuted by
the ARES paper's own cross-domain results (2311.09476, tau 0.38 on T-Rex
extraction, 0.28 code, 0.33 cross-lingual). Op judges need in-domain data and
validation.
- **Co-training needs expensive retrieval pre-training; GR obsoletes dense
retrieval; one model cannot rank and generate; scale buys quality.** All four
refuted in lane 10: RA-DIT (2310.01352), REPLUG (2301.12652), and In-Context
RALM (2302.00083) remove the necessity claim at each budget point; 2306.11397
shows GR decomposes into bi-encoder dot products (same object, different
clothes — keep the dense index swappable); RankRAG (2407.02485) shows one model
ranks and generates; 2305.11841 removes the scale claim.

## 4. Per-lane findings

Tables list admitted items with sources (arXiv id or URL) and the merged
one-line takeaway. Full take-careful notes are in `lanes/<n>/findings.md`.
Items serving several lanes appear under each lane they serve.

### Lane 1 admitted (20 items also counted under other lanes where listed)
| Item | ID | Rel | Lanes | Takeaway |
|---|---|---|---|---|
| APIGen | 2406.18518 | 3 | 1 | Format+execution+semantic 3-stage verification; 1.3B beats GPT-3.5 |
| BFCL | none (PMLR v267 patil25a) | 3 | 1 | AST/execution function-call eval; de-facto standard small-model gate |
| FoFo | 2402.18667 | 3 | 1 | Format-following is independent of content quality; open models lag |
| Gorilla | 2305.15334 | 3 | 1 | First SFT recipe for API-call emission (LLaMA + retriever + APIBench) |
| Granite | 2407.00121 | 3 | 1 | 7-task granular multi-task SFT with QLoRA r8 on 142k examples |
| Hammer | 2410.04587 | 3 | 1 | Function masking + irrelevance augmentation; SFT harms abstention w/o negatives |
| LLMCompiler | 2312.04511 | 3 | 1 | Plan-then-DAG-execute grammar for parallel calls; TinyAgent builds on it |
| Outlines | 2307.09702 | 3 | 1 | FSM-index constrained decoding at ~O(1) per step |
| SynCode | 2403.01632 | 3 | 1 | Sound/complete CFG decoding; 100% JSON-schema validity on Gemma2-2B |
| TinyAgent | 2409.00608 | 3 | 1 | Narrow-task SFT takes 1.1B 12.7%->80% success, beating GPT-4-Turbo |
| ToolACE | 2409.00920 | 3 | 1 | API self-evolution + complexity-guided dialogs + dual verification; LoRA r16 |
| ToolLLM | 2307.16789 | 3 | 1 | DFSDT multi-agent data pipeline + ToolBench 16k-API benchmark |
| xLAM | 2409.03215 | 3 | 1 | SFT+DPO function-calling family incl. 1B model; data reused by Hammer |
| API-Bank | 2304.08244 | 2 | 1 | 73-API executable dialogue benchmark used by Granite/Hammer for generalisation |
| FireAct | 2310.05915 | 2 | 1 | ReAct-trajectory fine-tuning: small models beat prompted large ones |
| Functionary | none | 2 | 1,6 | Open SFT recipe for chat-with-tools at small scale incl. Small models |
| ReAct | 2210.03629 | 2 | 1 | Thought-action-observation prompting scaffold for harness tool loops |
| Seal-Tools | 2405.08355 | 2 | 1 | Self-instruct tool/instance generation with nested calls; Tool/Param F1 eval |
| ToolAlpaca | 2306.05301 | 2 | 1 | 3000-case simulated tool-use SFT showing compact-model gains |
| Toolformer | 2302.04761 | 2 | 1 | Self-supervised API-call insertion via execution-filtered sampling |

### Lane 2 admitted (25 items also counted under other lanes where listed)
| Item | ID | Rel | Lanes | Takeaway |
|---|---|---|---|---|
| Bonito | 2402.18334 | 3 | 2 | Conditional task generator turning unannotated text into instruction data; trained on 1.65M remixed examples. |
| Humpback | 2308.06259 | 3 | 2 | Backtranslates instructions from unannotated web segments (502K) and filters by self-consistency; beats text-davinci-003 win-rate. |
| LIMA | 2305.11206 | 3 | 2 | 1,000 curated examples align a 65B model (superficial-alignment hypothesis). |
| Magpie | 2406.08464 | 3 | 2 | Extracts instruction data from an aligned teacher using only its pre-query template; SFT-only rivals SFT+DPO pipelines. |
| PersonaHub | 2406.20094 | 3 | 2 | 1B web-mined personas as generation lenses for math, instructions, knowledge, NPC and tool data. |
| RAFT | 2403.10131 | 3 | 2,10 | Trains with golden + distractor documents and CoT answers so the model reasons over retrieved context. |
| Self-Instruct | 2212.10560 | 3 | 2 | Bootstraps 52K instructions from seed tasks with similarity filtering; +33% absolute on SuperNI. |
| TinyZero | n/a | 3 | 2,4,7 | verifiable-reward RL on 3B-scale models for a counting task; canonical tiny RL starter |
| Tulu3 | 2411.15124 | 3 | 2,7 | Fully open SFT + length-normalized DPO + RLVR (verifiable-reward RL) pipeline; decontaminated evals; recipe SmolTulu replicates |
| WizardLM (Evol-Instruct) | 2304.12244 | 3 | 2 | Evolves seed instructions in-depth/in-breadth then mixes all levels for SFT. |
| AlpaGasus | 2307.08701 | 2 | 2 | ChatGPT-judge filters 52K Alpaca to 9K; trains 7B/13B faster and better. |
| DEITA (What Makes Good Data) | 2312.15685 | 2 | 2 | Scores complexity/quality/diversity (Evol-Complexity/Evol-Quality + embeddings) and selects small high-performing subsets. |
| Data Pruning Scales | 2206.14486 | 2 | 2 | Prototype-based pruning beats power-law data scaling on CIFAR/ImageNet/SVHN; only scaling-law-shaped pruning evidence found. |
| Deduplicating Training Data | 2107.06499 | 2 | 2 | Near + exact dedup of C4/RealNews/LM1B/Wiki40B improves perplexity and cuts memorization. |
| DoReMi | 2305.10429 | 2 | 2 | 280M proxy + group-DRO finds domain weights; 8B Pile training speeds up 2.6x. |
| FineWeb | 2406.17557 | 2 | 2 | Fully documented dedup/filter pipeline (MinHash, C4-style rules, classifiers) with ablations. |
| Instruction Mining | 2307.06290 | 2 | 2 | Lightweight metric rule blending quality/diversity for picking small high-performing subsets. |
| LESS | 2402.04333 | 2 | 2 | Gradient datastore (LoRA warmup) + influence picks 5% subsets beating full data on MMLU/TyDiQA/BBH. |
| Nemotron-CC | 2412.02595 | 2 | 2 | Classifier ensembling + synthetic rephrasing keep 6.3T tokens for 15T-horizon training; +5.6 MMLU over DCLM at 8B/1T. |
| RegMix | 2407.01492 | 2 | 2 | Rank-invariance lets tiny proxies + LightGBM regression predict the best mix (Pile-CC, 1M-token proxies). |
| Rephrasing the Web (WRAP) | 2401.16380 | 2 | 2 | Uses an instruction-tuned model to rephrase web docs (Wikipedia/QA styles) and trains jointly on real + synthetic. |
| SemDeDup | 2303.09540 | 2 | 2 | K-means on embeddings + intra-cluster pruning keeps ~50% of data at parity (OPT experiments). |
| UltraChat | 2305.14233 | 2 | 2 | Topic-scaffolded two-agent generation of 1.5M multi-turn dialogues. |
| Unnatural Instructions | 2212.09689 | 2 | 2 | Expands 15 seed instructions to ~64K examples by paraphrase; core of the minimal-diversity recipe. |
| WizardCoder | 2306.08568 | 2 | 2 | Evol-Instruct applied to a narrow task (code) on a StarCoder base. |

### Lane 3 admitted (22 items also counted under other lanes where listed)
| Item | ID | Rel | Lanes | Takeaway |
|---|---|---|---|---|
| Arrow-MBC | 2405.11157 | 3 | 3 | Zero-shot Arrow routing over an MBC-clustered LoRA library; matches/outperforms joint training |
| Echo | 2402.15449 | 3 | 3 | Echo (repeat-input) embeddings from causal LMs gain 5%+ zero-shot with no architecture change |
| KaLM | 2412.04948 | 3 | 3 | Joint explicit KG-alignment plus implicit AR objectives; reports prior attempts compromised generation |
| LoRA-Learns-Less | 2405.09673 | 3 | 3,5 | LoRA underperforms full FT on target but forgets less; full-FT perturbations are 10-100x the rank of LoRA |
| LoRAHub | 2307.13269 | 3 | 3 | Gradient-free composition of a library of task LoRAs for few-shot transfer |
| LoRAMoE | 2312.09979 | 3 | 3 | Frozen backbone + routed LoRA experts with a world-knowledge expert split; forgetting worsens with more instruction data |
| MoLF | 2605.07111 | 3 | 3 | Optimizer-level routing between FFT and LoRA experts tested at Gemma-3-1B and Qwen2.5-1.5B/3B |
| MoLoRA | 2603.15965 | 3 | 3 | Per-token adapter routing proven optimal vs per-sequence; Qwen3-1.7B exceeds Qwen3-8B via specialization |
| NV-Embed | 2405.17428 | 3 | 3 | Latent-attention pooling plus causal-mask removal plus two-stage contrastive instruction tuning with hard negatives |
| OPR | 2605.29495 | 3 | 3 | Replay of reward-filtered own-outputs as plain SFT; no teacher; KL-shrinkage interpretation; BWT -13.93 to -0.65 |
| RAD | 2608.20794 | 3 | 3 | Base-anchored self-distillation on unlabeled OOD text; soft-distribution signal beats replay on same text |
| Synthetic-Hurts | 2609.10750 | 3 | 3 | Synthetic retrieval fine-tuning causes forgetting at 0.6B; embedding-anchor reg/LwF/EWC/L2 recover OOD and gain +13.98% in-distribution |
| BERT-anisotropy | 2011.05864 | 2 | 3 | Untuned contextual embeddings live in an anisotropic cone; flow-based isotropy transform restores STS |
| EWC | 1612.00796 | 2 | 3 | Fisher-weighted anchor to old-task weights enables sequential task learning |
| LAMOL | 1909.03329 | 2 | 3 | LM head generates pseudo-samples of old tasks as replay; within 2-3% of multitask upper bound |
| Length-Collapse | 2410.24200 | 2 | 3 | Long-text embeddings cluster via attention low-pass filtering; TempScale temperature mitigation |
| LwF | 1606.09282 | 2 | 3 | Self-distillation against old-task outputs using only new-task data |
| QLoRA-tool | 2605.17774 | 2 | 3 | 4B QLoRA on ~1700 tool-use traces internalizes structured planning; rank 32 best quality, smaller ranks retain more |
| RL-vs-SFT-circuits | 2605.28860 | 2 | 3 | Head-level circuit analysis on Qwen2.5-3B: SFT adapts faster but disrupts circuits; RL preserves base circuit |
| SAPO | 2606.01967 | 2 | 3 | Paraphrased training prompts match in-task but differ sharply in forgetting; SAPO selects prompts by pre-learning loss |
| SimCSE | 2104.08821 | 2 | 3 | Dropout-noise unsupervised contrastive plus NLI entailment/contradiction supervised contrastive recipe |
| X-LoRA | 2402.07148 | 2 | 3 | Token-level deep layer-wise mixing of frozen pretrained adapters with a hidden-state gate |

### Lane 4 admitted (26 items also counted under other lanes where listed)
| Item | ID | Rel | Lanes | Takeaway |
|---|---|---|---|---|
| DAPO | 2503.14476 | 3 | 4 | decoupled-clip plus dynamic-sampling GRPO variant; 50 points on AIME 2024 with Qwen2.5-32B; fully open |
| DeepSeek-Prover-V1.5 | 2408.08152 | 3 | 4 | RLPAF: Lean 4 proof-assistant verdict as RL reward on a 7B prover; closest published validator-as-reward analogue |
| DeepSeek-R1 | 2501.12948 | 3 | 4 | R1-Zero pure rule-reward RL plus distillation of reasoning traces into small models down to 1.5B |
| DeepSeekMath | 2402.03300 | 3 | 4 | GRPO origin paper: critic-free RL with group-normalized advantage; 7B reaches 51.7 percent on MATH |
| DistiLLM | 2402.03898 | 3 | 4 | skew-KL loss plus adaptive off-policy use of student outputs; up to 4.3x speedup over on-policy KD |
| DrGRPO | 2503.20783 | 3 | 4 | identifies GRPO length/normalization bias; Dr.GRPO unbiased objective; minimalist 7B recipe reaches 43.3 percent AIME 2024 |
| GKD | 2306.13649 | 3 | 4 | trains student on its own generated sequences with teacher feedback; unifies distillation with RLHF |
| KTO | 2402.01306 | 3 | 4 | matches/exceeds preference methods at 1B to 30B from binary desirable/undesirable signals only |
| LiteGUI | 2605.07505 | 3 | 4 | SFT-free on-policy (GKD-style) distillation plus dual-level GRPO unlocks 2B/3B agents past imitation-learning limits |
| MiniLLM | 2306.08543 | 3 | 4 | reverse-KL on-policy distillation for generative LMs; scales 120M to 13B |
| OneShotRLVR | 2504.20571 | 3 | 4 | 1-example RLVR lifts Qwen2.5-Math-1.5B MATH500 36.0 to 73.6 percent; matches 1.2k-example run; entropy bonus critical |
| PEFT-for-RLVR | 2512.23165 | 3 | 4 | first systematic PEFT-under-RLVR study on R1-Distill models: DoRA/AdaLoRA/MiSS beat LoRA; PiSSA spectral collapse; rank-1 bottlenecks |
| RFT | 2308.01825 | 3 | 4 | rejection-sampling fine-tuning on self-generated correct paths; log-linear data scaling; LLaMA-7B GSM8K 35.9 to 49.3 percent |
| RLAIF | 2309.00267 | 3 | 4 | AI-labeled preferences match RLHF; works even when labeler equals policy size; direct-RLAIF scores rewards straight from an off-the-shelf LLM |
| RLOO | 2402.14740 | 3 | 4 | REINFORCE leave-one-out baseline outperforms PPO and DPO/RAFT at lower cost; no critic network |
| STaR | 2203.14465 | 3 | 4 | iterative loop: generate rationales, keep those yielding correct answers (validator filter), retrain; matches 30x larger SOTA |
| SeqKD | 1606.07947 | 3 | 4 | train student on teacher-generated sequences rather than token labels; best student 10x faster with little loss |
| SuperCorrect | 2410.09008 | 3 | 4 | teacher thought-templates plus cross-model DPO teach 7B student self-correction; beats DeepSeekMath-7B by 7.8/5.3 percent |
| TinyZero | n/a | 3 | 2,4,7 | verifiable-reward RL on 3B-scale models for a counting task; canonical tiny RL starter |
| Verifier-Flaws | 2502.00271 | 3 | 4 | imperfect verifiers misrank and prune all valid paths at scale; repeated sampling overtakes verifier search; holds at 7B |
| DPO | 2305.18290 | 2 | 4 | solves RLHF with a classification loss, no reward model or RL loop; stable and cheap |
| DistiLLM-2 | 2503.07067 | 2 | 4 | contrastive distillation: raise likelihood of teacher responses while lowering student ones; covers instruction-following, code, preference alignment |
| RLVR-Implicit | 2506.14245 | 2 | 4 | answer-only verifiable rewards still extend the reasoning boundary (CoT-Pass@K) rather than merely sharpening sampling |
| ReMax | 2310.10505 | 2 | 4 | greedy-baseline REINFORCE with no value model; removes 4-plus PPO hyperparameters; about 46 percent less GPU memory than PPO at 7B |
| SimPO | 2405.14734 | 2 | 4 | average-logprob implicit reward removes the reference model from memory; margin objective |
| Tricks-or-Traps | 2508.08221 | 2 | 4 | systematic reproduction of RL-for-reasoning techniques in one framework with selection guidelines; vanilla-PPO-loss minimalist combo beats GRPO/DAPO |

### Lane 5 admitted (20 items also counted under other lanes where listed)
| Item | ID | Rel | Lanes | Takeaway |
|---|---|---|---|---|
| Forgetting Scaling Laws | 2401.05605 | 3 | 5 | PEFT still forgets: forgetting is inverse-linear in FT loss and a shifted power law in params-tuned and steps; proposes pre/post cross-entropy forgetting metric. |
| Intruder Dimensions | 2410.21228 | 3 | 5 | LoRA creates high-ranking intruder singular vectors that cause forgetting; scaling them down cuts forgetting with minimal task loss; fixed-alpha high-rank LoRA forgets more. |
| LoRA | 2106.09685 | 3 | 5 | Freezes base weights, trains rank-r BA adapters; includes rank-deficiency and W_q/W_v-only ablations. |
| LoRA+ | 2402.12354 | 3 | 5 | Same LR for A and B is inefficient at width; fixed ratio eta_B >> eta_A gives ~2x speedup and 1-2% gains at LoRA cost. |
| LoRA-Learns-Less | 2405.09673 | 3 | 3,5 | LoRA underperforms full FT on target but forgets less; full-FT perturbations are 10-100x the rank of LoRA |
| LoRA-Null | 2503.02659 | 3 | 5 | Init A in null space of sampled pre-trained activations, freeze A, train B; higher rank trades retention for capacity; compares directly vs LoRA-FA/PiSSA/MiLoRA. |
| OPLoRA | 2510.13003 | 3 | 5 | Double-sided projections constrain updates to orthogonal complement of top-k singular subspace with preservation proof; rho_k interference metric; Llama-2-7B + Qwen2.5-7B. |
| rsLoRA | 2312.03732 | 3 | 5 | Standard alpha/r scaling collapses gradients as rank grows; alpha/sqrt(r) stabilizes and unlocks gains from r up to 2048 on Llama 2 + OpenOrca. |
| AdaLoRA | 2303.10512 | 2 | 5 | Allocates rank budget by importance across matrices with SVD parametrization + cubic schedule; biggest wins at low budgets. |
| DoRA | 2402.09353 | 2 | 5 | Decomposes weights into magnitude + direction, LoRA on direction; mimics FT learning pattern and beats LoRA on LLaMA/LLaVA/VL-BART. |
| GaLore | 2403.03507 | 2 | 5 | Full-parameter learning with low-rank gradient projections; 65.5% optimizer memory cut; Llama 7B pre-train on 24GB without ReLoRA-style warmup. |
| LoRA-FA | 2308.03303 | 2 | 5 | Freezes A, trains B only: removes A-activation memory (1.4x vs LoRA), matches LoRA/FT; poor on Math/Code noted by LoRA-Null authors. |
| LoftQ | 2310.08659 | 2 | 5 | Jointly optimizes quantized Q + LoRA init to close QLoRA gap; converges at 2-bit where QLoRA fails; Llama-2-7B/13B evidence. |
| MiLoRA | 2406.09044 | 2 | 5 | Updates only minor singular components, freezes principal ones; init orthogonal to principal subspace; wins on commonsense/math/instruction/VL. |
| O-LoRA | 2310.14152 | 2 | 5 | Sequential tasks in mutually orthogonal LoRA subspaces without replay; +24% over LFPT5; preserves unseen-task generalization. |
| PiSSA | 2404.02948 | 2 | 5 | Init A/B from principal SVD components, freeze residual; faster convergence than LoRA across 184M-70B; QPiSSA beats QLoRA 4-bit. |
| QA-LoRA | 2309.14717 | 2 | 5 | Group-wise quant + adaptation balances degrees of freedom; INT4 fine-tune merges back losslessly, beats QLoRA at 2-4 bit. |
| ReLoRA | 2307.05695 | 2 | 5 | Periodic merge-and-restart with jagged LR + partial optimizer reset turns sequential low-rank updates into high-rank training to 1.3B; needs full-rank warm start. |
| VeRA | 2310.11454 | 2 | 5 | Frozen shared random A/B across layers, trains only scaling vectors; 10x fewer params than LoRA at same GLUE/E2E quality. |
| muA | 2602.06204 | 2 | 5 | muA theory: optimal LR is rank-invariant under alpha=r^-1 but scales ~1/sqrt(r) under constant alpha; LoRA-tuned LRs transfer to full FT. |

### Lane 6 admitted (34 items also counted under other lanes where listed)
| Item | ID | Rel | Lanes | Takeaway |
|---|---|---|---|---|
| BoostCD | 2506.14901 | 3 | 6 | Boosted model fuses constrained+unconstrained base runs; BoostIE beats SynthIE by +17 micro-F1 in-dist, +11 OOD |
| EDC | 2404.03868 | 3 | 6 | Three-phase extract/define/canonicalize KGC with a trained schema retriever for large schemas |
| GENRE | 2010.00904 | 3 | 6,10 | Generates entity names with constrained beam search; cross-encodes mention and entity |
| GLiNER | 2311.08526 | 3 | 6 | Span/type dot-product matching with DeBERTa-v3 encoder beats ChatGPT zero-shot NER; CPU/ONNX/INT8 deployable |
| GLiREL | 2501.03172 | 3 | 6 | All entity pairs x all labels classified in one forward pass; SOTA on FewRel/WikiZSL zero-shot |
| GenIE | 2112.08340 | 3 | 6,8 | First end-to-end autoregressive closed IE with bi-level constrained generation over a Wikidata schema |
| GoLLIE | 2310.03668 | 3 | 6 | Fine-tunes LLMs to follow annotation guidelines (label schemas as class definitions) for zero-shot IE |
| KnowCoder | 2403.07969 | 3 | 6 | Python-class schema representation; 1.5B-token code pretrain then instruction tune; +49.8% few-shot vs LLaMA2 |
| Re-DocRED | 2205.12696 | 3 | 6,8 | Re-annotated 4053 docs (64.6% triples were missing); models gain ~13 F1; adds freq/long-tail/intra/inter metrics |
| ReLiK | 2408.00103 | 3 | 6 | Retriever-reader EL+RE with shared reader doing closed IE in one forward pass; SOTA on academic budget |
| SynthIE | 2303.04132 | 3 | 6 | Generates 1.8M synthetic text-from-triples points with an LLM; small fine-tunes beat prior SOTA by +57 micro-F1 |
| Text2KGBench | 2308.02357 | 3 | 6,8 | Ontology-conditioned fact extraction eval: P/R/F1 + ontology conformance + subject/relation/object hallucination |
| USM | 2301.03282 | 3 | 6 | Three directed token-linking ops replace generation; 356M model beats UIE-large by 5.11 few-shot |
| UniversalNER | 2308.03279 | 3 | 6 | Distills ChatGPT NER annotations on Pile passages into 7B/13B students; beats ChatGPT by 7-9 F1 |
| WebIE | 2305.14293 | 3 | 6 | C4-based generative IE with negatives and ~21K crowdsourced triples + 4-language mWebIE; entity-linking aux improves faithfulness |
| ChatIE | 2302.10205 | 2 | 6 | Two-stage multi-turn QA decomposition of RE/NER/EE; beats some full-shot models (e.g. NYT11-HRL) |
| DREEAM | 2302.08675 | 2 | 6 | Supervises transformer attention with sentence-evidence distributions (zero extra parameters) + ER self-training on distant data |
| DocRED | 1906.06127 | 2 | 6 | 132k-entity human-annotated document-level RE from Wikipedia/Wikidata plus distant supervision |
| Functionary | none | 2 | 1,6 | Open SFT recipe for chat-with-tools at small scale incl. Small models |
| GLiDRE | 2508.00757 | 2 | 6 | GLiNER-style bi-encoder extended to document-level relation extraction |
| GLiNER2 | 2507.18546 | 2 | 6 | Multi-task IE (NER+RE+hierarchical) behind a schema-driven interface |
| InstructUIE | 2304.08085 | 2 | 6 | IE INSTRUCTIONS (32 datasets) instruction-tuned FlanT5-11B; matches BERT supervised, beats GPT-3.5 zero-shot |
| KGGen | 2502.09956 | 2 | 6 | LLM pipeline for open KG extraction from plain text |
| KnowCoder-X | 2411.04794 | 2 | 6 | IE cross-lingual alignment phase + code schemas; 64 benchmarks, +30% over ChatGPT cross-lingual, 20 African languages |
| PIVOINE | 10.18653/v1/2023.findings-emnlp.1009 | 2 | 6 | Instruction tuning for open-world entity profiling (open-world IE sub-task) |
| R1-RE | 2507.04642 | 2 | 6 | RL with verifiable rewards for cross-domain relation extraction |
| REBEL | 10.18653/v1/2021.findings-emnlp.204 | 2 | 6 | Seq2seq triplet linearization on BART for 200+ relation types; SOTA on RE/RC benchmarks after few-epoch fine-tunes |
| REDFM | 2306.09802 | 2 | 6 | NLI-filtered silver RE data with Triplet Critic; mREBEL extracts typed triplets in 7 languages |
| RexUIE | 2304.14770 | 2 | 6 | Recursive token-linking queries extract n-ary schemas (quadruples/quintuples); 3M distant JERE pretrain |
| UIE | 10.18653/v1/2022.acl-long.395 | 2 | 6 | T5 text-to-structure with structural schema instructor and structured extraction language |
| YAYI-UIE | 2312.15548 | 2 | 6 | Two-step chat-then-IE instruction tuning; largest Chinese IE instruction benchmark; keeps English ability |
| Eider | 2106.08657 | 1 | 6 | Joint RE + lightweight evidence extractor with heuristic silver labels and inference-stage fusion |
| MR-UIE | 2509.09082 | 1 | 6 | RL with multi-perspective reasoning for universal IE |
| mGENRE | 2103.12528 | 1 | 6 | Multilingual GENRE resolving mentions in 100+ languages to a multilingual KB |

### Lane 7 admitted (16 items also counted under other lanes where listed)
| Item | ID | Rel | Lanes | Takeaway |
|---|---|---|---|---|
| APO | 2408.06266 | 3 | 7 | APO-zero/APO-down controllable DPO family; 32K CLAIR revision pairs + APO closes Llama-3-8B to GPT-4-turbo gap by 45% on MixEval-Hard |
| Gemma2 | 2408.00118 | 3 | 7 | 2B/9B trained with KD instead of next-token prediction (>50x Chinchilla tokens); SFT (behavioral cloning + on-student distillation) + RLHF + checkpoint averaging |
| Gemma3 | 2503.19786 | 3 | 7 | 256-logit sampled KD pre-training; post-training = IT-teacher KD + RL phase (BOND/WARM/WARP variants); Gemma3-4B-IT competitive with Gemma2-27B-IT |
| LFM2 | 2511.23404 | 3 | 7 | SFT 3 epochs cosine 3e-5 to 1e-7 (500-step warmup, AdamW 0.9/0.95, wd 0.1); length-normalized offline+on-policy preference opt; model merging (soup/TIES/DARE/DELLA); tempered decoupled Top-K KD in pretraining; LFM2-Nanos for extraction/tool-call/RAG |
| MiniCPM-2024 | 2404.06395 | 3 | 7 | WSD LR schedule; decay-stage annealing on pretrain+SFT mix (20B tokens); separate ~6B-token SFT; DPO family member |
| MiniCPM4 | 2506.07900 | 3 | 7 | UltraChat v2 SFT dataset; ModelTunnel v2 hyperparam search; chunk-wise rollout load-balanced RL; BitCPM ternary QAT |
| Phi-4 | 2412.08905 | 3 | 7 | 50-type synthetic data factory (~400B tokens: multi-agent prompting, self-revision, instruction reversal); SFT then pivotal-token DPO + judge-guided DPO (~850k pairs) |
| Phi-4-mini | 2503.01743 | 3 | 7 | 3.8B on synthetic-heavy reasoning/code mix with enlarged function-calling + summarization SFT; frozen backbone + per-modality LoRA routers (Mixture-of-LoRAs) for interference-free extension |
| Phi-4-mini-reasoning | 2504.21233 | 3 | 7 | 3.8B: large-scale mid-training on distilled long-CoT, SFT on 200K curated CoT, rollout DPO on 300K pairs (LR 5e-7, 1 epoch), then verifiable-reward RL; beats 7-8B distills on MATH-500 |
| Qwen2.5 | 2412.15115 | 3 | 7 | SFT on 1M+ samples, 2 epochs, seq 32768, LR 7e-6 to 7e-7, wd 0.1; then offline DPO + online GRPO |
| Qwen3 | 2505.09388 | 3 | 7 | 4-stage post-training (long-CoT cold start, reasoning GRPO on 3995 pairs, mode-fusion SFT, general RL); small models via off-policy + on-policy (KL) strong-to-weak distillation, which beats RL at ~1/10 GPU-hours |
| SmolLM2 | 2502.02737 | 3 | 7 | 1.7B on 11T tokens multi-stage; SFT on SmolTalk 2 epochs LR 3e-4 BS128 seq8192; DPO on UltraFeedback 2 epochs LR 1e-6 beta 0.5 |
| SmolTulu | 2412.08347 | 3 | 7 | Tulu-3 pipeline adapted to SmolLM2-1.7B: reasoning (ARC/GSM8K) wants high LR/BS ratio (SFT LR/BS 11.25e-6), DPO 8e-7/BS12 len-normed beta 5.0; IFEval 67.7%, GSM8K 51.6% |
| TinyZero | n/a | 3 | 2,4,7 | verifiable-reward RL on 3B-scale models for a counting task; canonical tiny RL starter |
| Tulu3 | 2411.15124 | 3 | 2,7 | Fully open SFT + length-normalized DPO + RLVR (verifiable-reward RL) pipeline; decontaminated evals; recipe SmolTulu replicates |
| APO-hinge-zero | 2508.08466 | 2 | 7 | Hinge-margin APO-zero variant for 0.5B-scale: zero gradient on easy pairs (hard-example mining), best AlpacaEval WR 36.02 / LC 17.07 |

### Lane 8 admitted (18 items also counted under other lanes where listed)
| Item | ID | Rel | Lanes | Takeaway |
|---|---|---|---|---|
| ARES | 2311.09476 | 3 | 8,9 | Fine-tunes lightweight judges on synthetic data; scores context relevance, faithfulness, answer relevance with PPI confidence intervals from ~150-300 human labels. |
| BDC-survey | 2406.04244 | 3 | 8 | Taxonomy of contamination types plus detection (n-gram overlap, membership inference, order tests) and mitigation; documents paraphrase-evasion of n-gram gates. |
| BEIR | 2104.08663 | 3 | 8 | 18-dataset zero-shot retrieval benchmark with nDCG@10/Recall@100 protocol; BM25 stays a hard baseline. |
| GenIE | 2112.08340 | 3 | 6,8 | First end-to-end autoregressive closed IE with bi-level constrained generation over a Wikidata schema |
| KILT | 2009.02252 | 3 | 8 | Unifies 5 knowledge-intensive tasks on one snapshot; KILT score requires provenance (R-precision 1) AND downstream output correct: joint retrieval-generation metric. |
| MTEB | 2210.07316 | 3 | 8 | 8-task embedding benchmark (retrieval, STS, clustering, rerank, classification...); no single method dominates all tasks. |
| PPI | 2301.09633 | 3 | 8 | Valid confidence intervals combining a small labeled set with many model predictions; more accurate predictor means tighter intervals. |
| Prometheus | 2310.08491 | 3 | 8 | Open 13B evaluator trained on 1K rubrics/100K GPT-4 feedbacks; Pearson 0.897 with humans, on par with GPT-4 when reference materials accompany. |
| Prometheus-2 | 2405.01535 | 3 | 8 | Adds pairwise ranking via weight-merged direct-assessment and preference models; 0.6-0.7 Pearson with GPT-4, 72-85pct human agreement. |
| RAGAS | 2309.15217 | 3 | 8 | Reference-free RAG metrics (faithfulness, answer relevance, context relevance) via LLM prompts; validated against human judgments on WikiEval. |
| Re-DocRED | 2205.12696 | 3 | 6,8 | Re-annotated 4053 docs (64.6% triples were missing); models gain ~13 F1; adds freq/long-tail/intra/inter metrics |
| Smucker-CIKM07 | 10.1145/1321440.1321528 | 3 | 8 | Randomization, bootstrap-shift, and paired t-tests agree on TREC runs; Wilcoxon and sign tests mislead and should be discontinued. |
| Text2KGBench | 2308.02357 | 3 | 6,8 | Ontology-conditioned fact extraction eval: P/R/F1 + ontology conformance + subject/relation/object hallucination |
| WebIE | 10.18653/v1/2023.acl-long.428 | 3 | 8 | 1.6M-sentence web closed-IE set WITH negatives; REBEL-only models score 0pct on negatives; entity-linking auxiliary head best for faithfulness. |
| FLASK | 2307.10928 | 2 | 8 | 12-skill instance-wise rubric eval; fine-grained scoring raises human-model correlation and robustness to verbosity gaming. |
| Generative-IE-survey | 2312.17617 | 2 | 8 | Technique taxonomy (augmentation, prompts, constrained decoding, SFT) with empirical finding that SFT dominates few/zero-shot and universal models win strict relation scores. |
| HELM | 2211.09110 | 2 | 8 | Multi-metric standard (accuracy, calibration, robustness, fairness, toxicity, efficiency) over 16 core scenarios; reporting template for joint-capability models. |
| MMTEB | 2502.13595 | 2 | 8 | Community expansion of MTEB: 500+ quality-controlled tasks incl. instruction-following and long-document retrieval. |

### Lane 9 admitted (22 items also counted under other lanes where listed)
| Item | ID | Rel | Lanes | Takeaway |
|---|---|---|---|---|
| ARES | 2311.09476 | 3 | 8,9 | Fine-tunes lightweight judges on synthetic data; scores context relevance, faithfulness, answer relevance with PPI confidence intervals from ~150-300 human labels. |
| AutoCompressors | 2305.14788 | 3 | 9 | Unsupervised summary-vector compression with summary accumulation; OPT/LLaMA-2 to 30k tokens on one 80GB GPU. |
| FILCO | 2311.08377 | 3 | 9 | Sentence-level context filtering trained on StrInc/lexical/CXMI silver labels; +3 pts avg, 44-64% shorter prompts. |
| Gist | 2304.08467 | 3 | 9 | Attention-mask trick that learns gist-token compression during instruction tuning at no extra cost; up to 26x. |
| ICAE | 2307.06945 | 3 | 9 | LoRA encoder (~1% params) compresses context to memory slots for a frozen LLM; AE+LM pretrain then instruction fine-tune; 4x. |
| LLMLingua | 2310.05736 | 3 | 9 | Small-LM perplexity coarse-to-fine prompt compression with budget controller and distribution alignment, up to 20x compression. |
| LLMLingua-2 | 2403.12968 | 3 | 9 | Distils GPT-4 compression into a token-classification compressor (XLM-R/mBERT); task-agnostic, 3-6x faster. |
| LongLLMLingua | 2310.06839 | 3 | 9 | Question-aware compression via contrastive perplexity plus document reordering; NQ +21.4% with 4x fewer tokens. |
| Lost-in-the-Middle | 2307.03172 | 3 | 9 | U-shaped position bias; reader QA saturates by ~20 docs; recommends reranking and truncation. |
| RAPTOR | 2401.18059 | 3 | 9 | Recursive embed-cluster-summarize tree; collapsed-tree retrieval mixes abstraction levels; QuALITY +20pp with GPT-4. |
| RECOMP | 2310.04408 | 3 | 9 | End-task-trained extractive and abstractive query-focused compressors with selective (possibly empty) augmentation. |
| RankGPT | 2304.09542 | 3 | 9 | Instructional permutation generation with sliding window; GPT-4 beats supervised rankers; distilled 435M student beats 3B monoT5 on BEIR. |
| Robust-RALM | 2310.01558 | 3 | 9 | Characterizes when retrieval hurts QA; NLI back-off baseline; 1000-example mixed relevant/irrelevant fine-tune yields robustness. |
| Self-RAG | 2310.11511 | 3 | 9,10 | Reflection tokens for on-demand retrieval and self-critique distilled offline from GPT-4; 7B beats ChatGPT on ODQA/reasoning. |
| xRAG | 2405.13792 | 3 | 9 | Two-layer projector maps frozen dense-retrieval embedding to one token for a frozen LLM; +10% avg, 3.53x fewer FLOPs. |
| GSM-IC | 2302.00093 | 2 | 9 | Measures consumer accuracy collapse under irrelevant context; self-consistency and distractor-aware exemplars mitigate. |
| Generative-Agents | 2304.03442 | 2 | 9 | Memory stream with relevance-recency-importance retrieval plus reflection synthesis; ablations and failure taxonomy (retrieval failure, confabulation). |
| MemGPT | 2310.08560 | 2 | 9 | OS-style virtual context management: hierarchical memory with function-call paging and heartbeat chaining. |
| QMSum | 2104.05938 | 2 | 9 | 1808 query-summary pairs over 232 meetings in 3 domains; locate-then-summarize baseline; cross-domain generalization fails. |
| Reflexion | 2303.11366 | 2 | 9 | Actor/Evaluator/Self-Reflection loop storing verbal feedback in a small episodic buffer; 91% HumanEval. |
| Selective-Context | 2310.06201 | 2 | 9 | Self-information filtering of lexical units; 50% context cut at minor quality loss; thresholds are domain-dependent. |
| Voyager | 2305.16291 | 2 | 9 | Ever-growing library of model-written code skills indexed by description embedding with iterative self-verification. |

### Lane 10 admitted (33 items also counted under other lanes where listed)
| Item | ID | Rel | Lanes | Takeaway |
|---|---|---|---|---|
| CorpusLM | 2402.01176 | 3 | 10 | One model unifies generative retrieval, closed-book generation and RAG in a single greedy DocIDs-References-Answer decode with ranking-oriented DocID-list training. |
| DSI | 2202.06991 | 3 | 10 | Single Transformer maps queries directly to docids; indexing and retrieval trained jointly with atomic and semantic-string docids. |
| GENRE | 2010.00904 | 3 | 6,10 | Generates entity names with constrained beam search; cross-encodes mention and entity |
| GR-as-Dense | 2306.11397 | 3 | 10 | Analytic result: DSI/NCI-style generative retrieval decomposes into dot products between query and document vectors, i.e. a bi-encoder. |
| GR-scaling | 2305.11841 | 3 | 10 | At 8.8M passages only synthetic-query document representations matter; PAWA/2D-IDs/consistency-loss add nothing net of parameters, and naive parameter scaling can hurt; web-scale GR remains unsolved. |
| InstructRetro | 2310.07713 | 3 | 10 | Continued retrieval-augmented pre-training of a 43B GPT on 100B tokens over 1.2T-token store, then instruction tuning; the Retro encoder can be ablated away and the decoder alone keeps the gains. |
| MiniRAG | 2501.06713 | 3 | 10 | Heterogeneous chunk-entity graph plus lightweight topology retrieval lets 1.5B-4B SLMs (incl. MiniCPM3-4B, Qwen2.5-3B) match LLM RAG at 25 percent storage; entity extraction is the designated easy subtask. |
| NCI | 2206.02743 | 3 | 10 | Seq2seq retriever with prefix-aware weight-adaptive decoder, semantic docids from hierarchical k-means, query-generation augmentation and consistency regularization. |
| RA-DIT | 2310.01352 | 3 | 10 | Lightweight two-step retrofit of any LLM (7B/13B/65B tested): retrieval-augmented instruction tuning for the LM plus LM-supervised retriever tuning; parametric knowledge preserved on 7/8 control tasks. |
| RAFT | 2403.10131 | 3 | 2,10 | Trains with golden + distractor documents and CoT answers so the model reasons over retrieved context. |
| REALM | 2002.08909 | 3 | 10 | First unsupervised joint pre-training of a dense retriever with an LM via backprop through MIPS over millions of docs with async index refresh. |
| REPLUG | 2301.12652 | 3 | 10 | Black-box LM with a tunable retriever supervised by LM perplexity (REPLUG LSR); improves GPT-3 175B LM likelihood 6.3 percent and Codex 5-shot MMLU 5.1 percent. |
| RETRO | 2112.04426 | 3 | 10 | Frozen BERT retriever plus differentiable encoder and chunked cross-attention matches GPT-3-scale Pile performance with 25x fewer parameters; any transformer can be RETROfitted. |
| RankRAG | 2407.02485 | 3 | 10 | One instruction-tuned LLM does both context ranking and answer generation; a small ranking-data fraction beats expert rankers and lifts nine RAG benchmarks at 8B and 70B. |
| SEAL | 2204.10628 | 3 | 10 | Generates corpus-grounded n-gram identifiers under FM-index-constrained decoding and scores documents by aggregating identifier scores. |
| Self-RAG | 2310.11511 | 3 | 9,10 | Reflection tokens for on-demand retrieval and self-critique distilled offline from GPT-4; 7B beats ChatGPT on ODQA/reasoning. |
| Atlas | 2208.03299 | 2 | 10 | Contriever plus FiD jointly pre-trained with periodic index refresh and query-side fine-tuning; 64-shot NQ beats a 540B model with 50x fewer parameters. |
| Contriever | 2112.09118 | 2 | 10 | MoCo-style contrastive pre-training with cropping-based positives yields an unsupervised dense retriever competitive with BM25 and a strong Atlas/Self-RAG starting point. |
| CorpusBrain | 2208.07652 | 2 | 10 | Generative-retrieval pre-training with inner-sentence-selection, lead-paragraph-selection and hyperlink-identifier-prediction tasks, then single-step generative fine-tuning per KILT task. |
| CorpusBrain++ | 2402.16767 | 2 | 10 | Pre-trained CorpusBrain catastrophically forgets on the new KILT++ continual benchmark; rehearsal-plus-regularization continual generative pre-training restores it. |
| DPR | 2004.04906 | 2 | 10 | Dual-encoder trained with one BM25 hard negative plus in-batch negatives; +9-19 point top-20 gains over BM25 and the initializer for RAG joint fine-tuning. |
| DSI-QG | 2206.10128 | 2 | 10 | Diagnoses DSI train-serve mismatch (long documents indexed, short queries retrieved) and fixes it by indexing cross-encoder-filtered generated queries instead of document text. |
| FLARE | 2305.06983 | 2 | 10 | Forward-looking active retrieval: draft the next sentence, use it as the retrieval query, and regenerate only when low-confidence tokens appear; best or competitive on four long-form tasks. |
| FiD | 2007.01282 | 2 | 10 | Fusion-in-Decoder encodes each retrieved passage independently and fuses evidence in the decoder; accuracy keeps improving to ~100 passages. |
| GAR | 2009.08553 | 2 | 10 | Reverse direction: a generator expands the query with heuristically discovered contexts and BM25 over expansions matches or beats DPR; fusing diverse generations helps. |
| GenIR-survey-Kuo | 2406.01197 | 2 | 10 | Taxonomy of DocID strategies (single-token, sequential, text-based) and indexing-versus-retrieval training, with future directions on learnable DocIDs and multi-task GR. |
| GenIR-survey-Li | 2404.14851 | 2 | 10 | Two-branch survey: generative document retrieval plus reliable response generation (memorization, augmentation, attribution), with incremental-learning and evaluation sections. |
| In-Context RALM | 2302.00083 | 2 | 10 | Prepending retrieved passages with no LM changes gives gains equivalent to 2-3x parameters across 110M-66B models; ranking the retriever for the RALM objective adds more. |
| IncDSI | 2307.10323 | 2 | 10 | New documents indexed in 20-50 ms by constrained optimization over the added docid vector only, matching full-retrain retrieval quality without touching the encoder. |
| RAG | 2005.11401 | 2 | 10 | RAG-Sequence and RAG-Token jointly fine-tune a DPR retriever with a BART generator treating documents as latents; index is hot-swappable. |
| RAG-survey-Gao | 2312.10997 | 2 | 10 | Naive, Advanced and Modular RAG paradigms with pre-retrieval, post-retrieval and evaluation taxonomies. |
| RIPOR | 2311.09134 | 2 | 10 | Prefix-oriented ranking optimization plus multi-stage distillation makes GR work on large standard benchmarks (MS MARCO, NQ) for the first time. |
| Ultron | 2208.09257 | 2 | 10 | Semantically rich URL-plus-title-plus-title docids with a three-stage (general, search-oriented, supervised) training workflow; beats DSI-style baselines on MS MARCO and NQ. |

### Unresolved ledgers by lane

Lane 1: constrained-decoding x fine-tuning interaction (no paper trains under
its inference grammar — spike-011 arm); sub-3B independent numbers hole
(Qwen2.5-0.5B/1.5B/3B, Gorilla-OpenFunctions-v2 unverifiable); Glaive-v2
composition unknown (no paper, page unopened); NexusRaven-V2 method
unverifiable (no paper, no license); DPO preference construction from validator
verdicts open; schema-evolution evaluation protocol missing.

Lane 2: GLAN, Genie, Auto Evol-Instruct unresolvable names/ids (nothing
invented); no direct <=3B SFT data-quantity scaling law (gap, implies a
Proof-pass-vs-pool-size experiment); Humpback/RAFT/PersonaHub/Instruction
Mining lack official code (reimplement from papers); Tulu 3, Nemotron-4 340B,
Min-K% screened out as scope cuts; venue strings unverified unless fetched.

Lane 3: no paper measures MRR >= 0.75 and Proof-pass >= 0.78 on one <=3B
adapter (central gap); optimal embed/emit rank split unknown (one planning
data point at 2605.17774 only); echo-vs-[EMB]-marker under joint training
untested; length stratification on MiniCPM5 untested (2410.24200 predicts
collapse for long sections); replay-budget scaling at 2B unknown; S2
forward-chaining from OneGen/Hydra/LLM2Vec-Gen rate-limited out (OpenAlex thin).

Lane 4: ORPO, V-STaR, Tulu-3-recipe, RAFT-reward-ranked ids unverifiable
(guessed ids disproven at abs pages; covered by SimPO, STaR+KTO, R1+DAPO+open-r1,
RFT+filtered-SFT respectively); KTO/SimPO embedding-retention unmeasured
(joint-eval gap); Proof-reward density (whole-list vs per-op) untested;
single-16GB embedder-plus-RL memory accounting absent; LiteGUI artefact release
status unverified.

Lane 5: LQ-LoRA verified but not admitted (third quant recipe, no PDF);
Haque-2025 survey weak evidence (prompting confound, no PEFT-vs-FT isolation);
(IA)3 era/scope mismatch; LR-QAT incompletely verified; QuAILoRA/AFLoRA/LoRAF
below primary-source bar; QLoRA/TIES/DARE per brief section 2 not re-screened;
FourierFT/Delta-LoRA/LoRA-GA/MTLoRA/MoLE-family never verified (API outages;
neighbors AdaLoRA/O-LoRA cover); no paper trains one adapter for contrastive
embedding with a grammar-constrained decoder intact (the joint objective is the
gap).

Lane 6: Triplex abstains (vendor pages only, no paper/report/license);
NuExtract abstains as research (no paper) but flags as reusable artefact (0.5B
Qwen1.5, 3.8B Phi-3-mini, 7B, 4B VLM; MIT/Apache-2.0; vendor claims only);
WikiNRE unlocated (known via WebIE citation); GENRE/mGENRE checkpoint status
unverified; UIE/InstructUIE/USM/RexUIE/PIVOINE/YAYI-UIE/ChatIE/EDC/KGGen/GLiNER2/
GLiDRE/R1-RE/MR-UIE/Eider/DocRED/mGENRE admitted as papers, not as verified
artefacts; sub-3B extraction numbers sparse except SynthIE, ReLiK-small/tiny,
GLiNER sizes, vendor-only NuExtract-tiny (real gap).

Lane 7: MiniCPM3-4B recipe (card only, no training disclosure); MiniCPM5-1B
post-training undisclosed; Qwen3-Embedding out of scope (round-2 dedup);
LFM2-Nanos announced with weights but no standalone recipe (follow-up fetch
worthwhile); Smol Training Playbook secondary (resolves to admitted
primaries); per-size LR/BS schedules below 1B on 16 GB absent (SmolTulu covers
135M/1.7B; spike 011 must close empirically).

Lane 8: Urbano SIGIR13 optimality unopened (paywalled); Deng NAACL24
TS-Guessing implementability unknown; DCR-2025 adjusted accuracy unverified;
2409.09927 detector inconsistency unopened (no single detector agreed);
2502.14425 likely redundant with BDC survey; GenIE small-scale constrained
numbers unopened; ADELIE SFT recipe unopened (lane-2/6 overlap); BiGGen-Bench
unopened (Prometheus-2-BGB second-hand); PPI++ efficiency unconfirmed (PPI
itself admitted).

Lane 9: no frontier-consumer-vs-<=3B-composer measurement (gap); no Folio
utility by downstream gain (gap); soft-payload cross-consumer portability
unmeasured with a negative prior (gap); verbatim-quote faithfulness-vs-utility
tradeoff unquantified (gap); no query-focused evidence-span dataset for
graph/SQL-op payloads (gap).

Lane 10: DynamicRetriever abs unopened (abstain; Ultron admitted instead);
Reader-to-Retriever distillation no arXiv id (OpenReview primary; covered by
Atlas/REPLUG-LSR); REPLUG/RankRAG/Self-RAG repo URLs 404 on API (unverified,
not invented); CorpusLM/GR-as-Dense/RIPOR/CorpusBrain++ stage code URLs blank
rather than guessed; S2 chaining impossible (429s), manual reference-list
chaining substituted; sub-3B weights-level co-training evidence absent
(MiniRAG 1.5B-4B is harness-level; the weights-level measurement is spike
011's).

## 5. The recipe

Concrete plan. Every step traces to an admitted paper or documented system;
spike-011 arm mappings are inline in brackets.

### (a) Dataset

Sources: the 20 parity documents (whole-document holdout, never example-level;
decontamination checklist per BDC survey 2406.04244 with n-gram plus
embedding/paraphrase screening, since paraphrase evades string gates), plus
teacher-generated sections from gold ops in the SynthIE direction
(teacher writes documents from gold triples, student learns ops-from-documents;
2303.04132) and persona-lensed generations per section to break teacher
mode-collapse (PersonaHub 2406.20094). Coverage discipline: a
section-by-operation-type matrix the generator must fill (UltraChat 2305.14233
pattern), evolved from trivial to adversarial extractions (nested dates,
ambiguous entities, multi-hop; Evol-Instruct operators 2304.12244, narrow-task
proof via WizardCoder 2306.08568).

Generation: teacher op traces per section (full op lists, sequence-level, never
token labels; 1606.07947), two-step entities-then-relations traces distilled
from spike 008's win (FireAct trajectory-SFT precedent 2310.05915; inference
analogue ChatIE 2302.10205), conditional task generation for private sections
(Bonito 2402.18334, bolt Proof validation on), and instruction-reversal for
harness prompts from gold ops (Phi-4 2412.08905 pattern).

Filtering, in order: exact-substring plus MinHash near-dup (2107.06499);
semantic dedup over triple-identity redundancy with an external embedder, never
the adapter under training (SemDeDup 2303.09540); cheap metric sieve
(Instruction Mining 2307.06290), frontier-judge score kept as metadata
(AlpaGasus 2307.08701), Proof verdict as final gate (APIGen 3-stage pattern
2406.18518; Toolformer execution filter 2302.04761); NLI/critic filtering of
distant silver (REDFM 2306.09802); influence selection against gold
Proof-passing examples once the pool exceeds one run (LESS 2402.04333; DEITA
three-scorer stack 2312.15685). Rephrases stay on the embedding side only,
never as quote sources (WRAP drift risk 2401.16380); every example logs
teacher, template version, source section, license (lane-2 requirement).

Composition and sizes: ~1K extreme-curation gold op examples for format
(LIMA 2305.11206); thousands of narrow examples total (ToolAlpaca 2306.05301
calibration); 12.5% no-op sections with empty-list labels (Hammer 2410.04587
ratio); RAFT P%-golden/(1-P)%-distractor mixture with quoted CoT for the
assembly slice, P tuned (2403.10131; Robust-RALM 1K mixed-context arm
2310.01558); contrastive pairs multiplied by style rephrasing (WRAP 2401.16380)
with hard contradictions (SimCSE 2104.08821) and citation-verbatim format
(RAFT); slice weights fit on a tiny proxy, then train once (DoReMi 2305.10429;
RegMix 2407.01492 at 1M-token proxy scale). Splits: whole-document held-out
with a Re-DocRED-style completion pass on eval references (2205.12696),
explicit negative sections (WebIE 2305.14293/10.18653 rule: REBEL-only models
score 0% on negatives), and a logged exclusion quarantine of the final gate
(lane-8 requirement). [Maps to spike-011 dataset arms; the missing <=3B
quantity law becomes a Proof-pass-vs-pool-size curve measured on the rig.]

### (b) Joint training run on one 16 GB GPU

Start from separation, earn jointness [toggle arm first]. Train one embed-job
adapter and one emit-job adapter with per-pass toggling (Arrow precedent
2405.11157: routed library matches/beats joint training; LoRAHub 2307.13269 and
X-LoRA 2402.07148 as composition fallbacks; O-LoRA orthogonal subspaces
2310.14152 as the simple variant; Phi-4-mini freeze-backbone-plus-per-job-LoRA
2503.01743 as lab precedent). Embed adapter: rank 16 with alpha/sqrt(r)
(rsLoRA 2312.03732) or alpha=2r (2410.21228), split A/B LRs eta_B >> eta_A
(LoRA+ 2402.12354), rank/LR regime per muA (2602.06204); emit adapter: DoRA or
AdaLoRA, never PiSSA init, rank above the rank-1 bottleneck zone (PEFT-for-RLVR
2512.23165). Anchor every joint step with a KL/base-distribution loss
(Recall-Anchored Distillation 2608.20794: soft distribution is the active
signal) plus reward-filtered on-policy replay of Proof-passing traces as plain
SFT at ~10% budget (2605.29495; STaR loop 2203.14465); embedding-anchor
regularization ranked list as backup (2609.10750). Try the single-adapter joint
contrastive-plus-emission loss only against the toggle baseline, with loss
weights as the whole game (KaLM warning 2412.04948) and early-identifier-token
credit assignment (RIPOR prefix idea 2311.09134); GR-as-dense theory
(2306.11397) licenses the attempt, RankRAG (2407.02485) says keep the ranking
fraction small.

Staging: SFT (anneal-style mixed phase, not final-only; MiniCPM 2404.06395)
at Qwen2.5/SmolLM2 bands (2 epochs; SFT LR ~1e-5 full-model, 3e-4 at 1.7B
SmolLM2 2502.02737; SmolTulu high LR/BS ratio for reasoning-ish routing skill
2412.08347), then length-normalized preference opt on Proof pass/fail pairs —
KTO first (binary signal, no pairing; 2402.01306), SimPO if the reference copy
pinches memory (2405.14734), APO-zero over teacher-revised failures per
SmolLM3's choice (2408.06266), pivotal-token pairs for single bad quote/date
tokens (Phi-4 2412.08905) — then RLVR against Proof only after Proof precision
is calibrated, with Dr.GRPO objective (2503.20783), DAPO dynamic sampling
(2503.14476), entropy bonus (2504.20571; 1-example RLVR data-scale precedent),
and a filtered-SFT control on identical rollouts (2505.13697). Distill (GKD
2306.13649; DistiLLM 2402.03898) before RL per Qwen3's 10x measurement
(2505.09388). Grammar (SynCode 2403.01632 / Outlines 2307.09702) at decode
throughout; log syntax-vs-grounding failure splits. Expected cost: SFT-stage
minutes on one card (spike-004 class: 147 s for 6 epochs LoRA-r16); on-policy
stages bounded by DistiLLM 4.3x savings and dynamic sampling; no admitted
source runs embedder-loss plus RL on one 16 GB card, so memory accounting
(ReMax 46% claim at 7B, LoRA-FA activation halving 2308.03303) must be measured
at 2B, not imported. [Maps: low-capacity arm (VeRA 2310.11454 as floor),
KL-anchor arm (2608.20794), joint-loss arm (GKD 2306.13649 + 2306.11397),
toggle arm (2405.11157/2307.13269), RL arm (TinyZero starter code, verl/TRL
backends).]

### (c) Evaluation protocol

Joint metric with a KILT-shaped gate (2009.02252): an op counts only if its
quote is verbatim (provenance gate) AND its triple/SQL parses (generation
gate); report retrieval MRR/nDCG@10 with BM25 alongside (BEIR protocol
2104.08663, Hole@10 analysis for unjudged hits) next to gated generation
accuracy — never MRR alone, plus one non-retrieval embedding task (MTEB
discipline 2210.07316) so the adapter cannot silently destroy section
representations. Report extraction F1 and conformance/hallucination split
separately (Text2KGBench SH/RH/OH 2308.02357), BFCL-style AST accuracy next to
Proof-pass (lane-1 gate), strict and soft match both (Generative-IE survey
2312.17617 lesson), negative-section accuracy apart from positive F1 (WebIE
rule). Statistics for n=20: PPI intervals from all predictions plus gold
labels (2301.09633), pre-registered randomization tests with paired-t
cross-check, no Wilcoxon/sign (Smucker CIKM07 10.1145/1321440.1321528), no
bare p-values (Smucker SIGIR09 10.1145/1571941.1572050), effect sizes always.
Judge hygiene: local pinned judges over API judges (Prometheus recipe
2310.08491; pairwise ranking for arm comparison, Prometheus 2 2405.01535),
swap-averaging plus length control plus human-agreement calibration on own ops
(2306.05685, 2403.16634, 2404.04475), in-domain judge data with own tau
validation (ARES caveat 2311.09476 section 5.4/6), FLASK-style skill split with
at least one deterministic rule-scored skill (Proof; 2307.10928). Regression
gates: frozen splits, fixed metric set, raw completions archived (HELM
discipline 2211.09110), re-run every epoch (MTEB <10-lines pattern); eval
complements ARES-three-metric (relevant/grounded/answering 2311.09476) and
RAGAS faithfulness-as-second-opinion (2309.15217, dev signal only).

## 6. Reusable artefacts

Released datasets, checkpoints, adapters, training and evaluation code usable
on one 16 GB GPU, with licenses as recorded at screening (point-in-time
2026-09-12; re-check at use). Inventory-verified rows first; findings-level
items (no separate inventory row) flagged with an asterisk.

Function-calling data and recipes: APIGen 60k (`Salesforce/xlam-function-calling-60k`,
HF dataset; paper 2406.18518); xLAM-60k reused by Hammer (2409.03215);
TinyAgent 1.1B/7B models plus dataset (`SqueezeAILab/TinyAgent`, MIT);
Hammer 1.5B/4B/7B plus 7.5k irrelevance data (`MadeAgents/Hammer`,
Apache-2.0); Granite function-calling QLoRA-r8 recipe (2407.00121,
Apache-2.0); *Functionary SFT recipe incl. small models
(`MeetKai/functionary`, MIT); *Hermes JSONModeEval harness
(`NousResearch`, MIT); Seal-Tools 4,076-tool/14,076-instance generator plus
Tool/Param-F1 eval (2405.08355); ToolBench/ToolLLM pipeline (2307.16789);
BFCL eval (PMLR v267, no arXiv id); *Guidance token-healing library
(`guidance-ai/guidance`, MIT); SynCode library
(`structuredllm/syncode`, MIT).

Extraction data and models: SynthIE 1.8M synthetic points plus 220M/770M
models (`epfl-dlab/SynthIE`, MIT); GenIE code plus 27.7 GB Zenodo data/models
(`epfl-dlab/GenIE`, MIT); BoostCD/BoostIE code, models, data
(`epfl-dlab/BoostCD`, MIT); GoLLIE (`hitz-zentroa/GoLLIE`, Apache-2.0);
UniversalNER recipe/data/models (research-only: code MIT, Pile-NER-type and
checkpoints CC-BY-NC-4.0, LLaMA/ChatGPT-encumbered — regenerate, do not ship);
REBEL code plus rebel-large (code repo 576 stars; HF checkpoint
CC-BY-NC-SA-4.0 — eval/comparison only); WebIE annotations plus scripts
(`amazon-science/webie`, CC-BY-NC-4.0 — eval only); Re-DocRED data plus eval
code (`tonytan48/re-docred`, MIT); ReLiK code plus tiny/small/base/large/XL
checkpoints (`SapienzaNLP/relik`, no license stated — confirm before use);
GLiNER (`urchade/GLiNER`, Apache-2.0, CPU/ONNX/INT8); GLiREL
(`jackboyla/GLiREL`); KnowCoder code/schema/data/model
(`ICT-GoKnow/KnowCoder`); DREEAM (`YoumiMa/dreeam`); Text2KGBench benchmark
plus code (`cenguix/Text2KGBench`, Apache-2.0; data CC-BY-4.0); *NuExtract
0.5B/3.8B/7B/4B-VLM (MIT/Apache-2.0, vendor claims only, ~30-example
fine-tune).

Post-training recipes and weights: SmolLM2 1.7B recipe plus SmolTalk
(`huggingface/smollm`, Apache-2.0); *SmolLM3 SFT/APO configs
(`huggingface/alignment-handbook` recipes, LR/BS fields fetched); Tulu 3
pipeline plus data/checkpoints (`allenai/open-instruct`, Apache-2.0 code;
stage models under Llama-3.1 terms); Qwen3 small weights (Apache-2.0);
Phi-4-mini weights (MIT) with frozen-backbone-plus-LoRA pattern; MiniCPM
weights (Apache-2.0; note lane-7 size-label refutation); Granite 3.0/4.0 repos
(Apache-2.0); Gemma 2/3 and LFM2 weights gated (custom terms — avoid for
reproducible baselines).

Distillation/RL code: *TRL (`huggingface/trl`, Apache-2.0) as default
DPO/KTO/GRPO substrate; *verl (`volcengine/verl`, Apache-2.0) if TRL is
outgrown; *open-r1 (`huggingface/open-r1`, Apache-2.0) recipe reference;
*TinyZero (`Jiayi-Pan/TinyZero`, Apache-2.0) RL starter; DistiLLM
(`jongwooko/distillm`, no license stated — vendor, do not track upstream);
SuperCorrect (`YangLing0818/SuperCorrect-llm`, no license — reference only);
One-Shot-RLVR (`ypwang61/One-Shot-RLVR`, Apache-2.0); LoRAHub adapters
(`sail-sg/lorahub`, MIT); X-LoRA (`EricLBuehler/xlora`, Apache-2.0); SimCSE
(`princeton-nlp/SimCSE`, MIT); OPR (`Yancey2024/OnPolicyReplay`, no license);
MoLF (`11785T23/molf`, Apache-2.0); MiniRAG (`HKUDS/MiniRAG`, MIT);
DPR/Contriever/FiD/Atlas/SEAL/CorpusBrain/GENRE/FLARE/DSI-QG/IncDSI repos per
lane-10 rows (check live availability; REPLUG/RankRAG/Self-RAG claimed URLs
404'd at screening).

Eval code: MTEB/BEIR harnesses (Apache-2.0); ARES judges plus pipeline
(Apache-2.0); RAGAS (Apache-2.0); KILT (MIT); Prometheus/Prometheus-2
(MIT/Apache-2.0); FLASK (no license recorded); *retro-8b-instruct-4k 8B
retrieval-trained checkpoint (`nvidia/retro-8b-instruct-4k`, analysis
artefact). Compression: LLMLingua family, RECOMP compressors on HF, ICAE PWC
dataset/model, AutoCompressors models, Gist checkpoints (per lane-9 rows).

## 7. Gaps

What nobody has built or measured, stated precisely: (1) one <=3B model
trained for contrastive retrieval and grammar-constrained emission with both
metrics reported — no paper, the spike-011 measurement; (2) a <=3B SFT
data-quantity scaling law for narrow structured tasks — single points only
(LIMA, AlpaGasus), implying a Proof-pass-vs-pool-size rig experiment;
(3) constrained-decoding x fine-tuning interaction — nobody trains under its
inference grammar; (4) embedding retention under KTO/SimPO/DPO preference
tuning — unmeasured; (5) Proof-reward density (whole-list vs per-op credit)
for structured emission — untested; (6) single-16GB embedder-loss-plus-RL
memory accounting at 2B — absent; (7) frontier-consumer answer quality as a
function of <=3B-composer payloads — unmeasured; (8) Folio utility by
downstream consumer gain — unrun; (9) soft-payload cross-consumer portability
at small scale — unmeasured with negative prior; (10) verbatim-quote
faithfulness-vs-utility tradeoff — unquantified; (11) query-focused
evidence-span dataset for graph/SQL-op payloads — nonexistent; (12) sub-3B
extraction numbers outside SynthIE/ReLiK-small/GLiNER/vendor-only NuExtract —
sparse; (13) per-size LR/BS SFT/DPO schedules below 1B on a single 16 GB GPU —
absent; (14) schema-evolution generalization protocol for accumulating Folios —
missing; (15) agreed contamination detector (detectors disagree; instruction
tuning blinds them) — open per 2409.09927 abstain; (16) MoLE-family, LQ-LoRA
depth, AFLoRA/LoRAF verification — unverified for budget/API reasons, named so
they are not silent.

## 8. Reading order

One day, in order, each under an hour except where noted: (1) TinyAgent
(2409.00608) — the 1B harness win, sets the ceiling belief; (2) APIGen
(2406.18518) — the dataset pipeline to copy; (3) Hammer (2410.04587) section
5.6 plus FoFo (2402.18667) — the two mandatory negative lessons; (4) RA-DIT
(2310.01352) with RankRAG (2407.02485) — the joint-training evidence pair;
(5) LoRA Learns Less (2405.09673) with the Illusion paper (2410.21228) —
retention mechanics plus the rank/alpha corrections; (6) Qwen3 report
(2505.09388) Table 21 plus RL-in-Name-Only (2505.13697) — distill-before-RL and
the filtered-SFT control; (7) DeepSeek-Prover-V1.5 (2408.08152) — the
validator-as-reward template; (8) RECOMP (2310.04408) with Lost-in-the-Middle
(2307.03172) — composer training signal plus assembly constraint; (9) ARES
(2311.09476) with the PPI paper (2301.09633) — eval protocol plus small-n
statistics; (10) Self-RAG (2310.11511) — the control-token training pattern
(90 minutes, the longest read, skimmable to method sections 3-4).

## 9. Full inventory table

Every screened candidate, admitted or not, sorted by disposition (admit, refute, abstain) then relevance descending. Detail column carries the one-line takeaway for admits and the verification reason for refutes/abstains. Field values are the merged inventory as written by the lanes (see repair note).

Repair note: three lane-9 rows (GSM-IC, Robust-RALM, xRAG) arrived in merged/INVENTORY.tsv with columns shifted two places right (reason text in the relevance column, empty disposition). They are restored here as admit with the relevance and reason shown; license/artefact fields were overwritten by the shift and are marked not recorded.

| name | title | authors | year | venue | id | repo | stars | last_push | license | artefact | detail(one-line_or_reason) | Q | rel | disp | lanes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| APIGen | APIGen: Automated Pipeline for Generating Verifiable and Diverse Function-Calling Datasets | Liu et al. | 2024 | NeurIPS 2024 Datasets & Benchmarks | 2406.18518 | none verified | — | — | — | yes: 60k-entry dataset (HF Salesforce/xlam-function-calling-60k) | Format+execution+semantic 3-stage verification; 1.3B beats GPT-3.5 | 1 | 3 | admit | 1 |
| APO | Anchored Preference Optimization and Contrastive Revisions: Addressing Underspecification in Alignment | D'Oosterlinck et al. | 2024 | arXiv preprint (cs.LG) | 2408.06266 | n/a | n/a | n/a | n/a (method paper, no artefact) | method + 32K CLAIR pairs recipe published | APO-zero/APO-down controllable DPO family; 32K CLAIR revision pairs + APO closes Llama-3-8B to GPT-4-turbo gap by 45% on MixEval-Hard | 4 | 3 | admit | 7 |
| ARES | ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems | Jon Saad-Falcon, Omar Khattab, Christopher Potts, Matei Zaharia | 2024 | NAACL 2024 | 2311.09476 | https://github.com/stanford-futuredata/ARES | 732 | 2025-03-28 | Apache-2.0 | yes: code, synthetic-data pipeline, DeBERTa judges | Fine-tunes lightweight judges on synthetic data; scores context relevance, faithfulness, answer relevance with PPI confidence intervals from ~150-300 human labels. | 6 | 3 | admit | 8,9 |
| Arrow-MBC | Towards Modular LLMs by Building and Reusing a Library of LoRAs | Oleksiy Ostapenko; Zhan Su; Edoardo Maria Ponti; Laurent Charlin; Nicolas Le Roux; Matheus Pereira; Lucas Caccia; Alessandro Sordoni | 2024 | arXiv preprint | 2405.11157 |  |  |  | unknown | unknown | Zero-shot Arrow routing over an MBC-clustered LoRA library; matches/outperforms joint training | 3 | 3 | admit | 3 |
| AutoCompressors | Adapting Language Models to Compress Contexts | Alexis Chevalier; Alexander Wettig; Anirudh Ajith; Danqi Chen | 2023 | EMNLP 2023 | 2305.14788 | https://github.com/princeton-nlp/AutoCompressors | 336 | 2024-09-09 | None | models released | Unsupervised summary-vector compression with summary accumulation; OPT/LLaMA-2 to 30k tokens on one 80GB GPU. | 6 | 3 | admit | 9 |
| BDC-survey | Benchmark Data Contamination of Large Language Models: A Survey | Cheng Xu, Shuhao Guan, Derek Greene, M-Tahar Kechadi | 2024 | arXiv preprint | 2406.04244 |  |  |  |  | no | Taxonomy of contamination types plus detection (n-gram overlap, membership inference, order tests) and mitigation; documents paraphrase-evasion of n-gram gates. | 2 | 3 | admit | 8 |
| BEIR | BEIR: A Heterogenous Benchmark for Zero-shot Evaluation of Information Retrieval Models | Nandan Thakur, Nils Reimers, Andreas Rucke, Abhishek Srivastava, Iryna Gurevych | 2021 | NeurIPS 2021 Datasets and Benchmarks | 2104.08663 | https://github.com/beir-cellar/beir | 2288 | 2025-10-16 | Apache-2.0 | yes: code, 18 datasets, leaderboard | 18-dataset zero-shot retrieval benchmark with nDCG@10/Recall@100 protocol; BM25 stays a hard baseline. | 3 | 3 | admit | 8 |
| BFCL | The Berkeley Function Calling Leaderboard: From Tool Use to Agentic Evaluation of Large Language Models | Patil et al. | 2025 | ICML 2025 | none (PMLR v267 patil25a) | https://gorilla.cs.berkeley.edu/leaderboard | — | — | — | yes: live leaderboard + eval harness | AST/execution function-call eval; de-facto standard small-model gate | 1 | 3 | admit | 1 |
| Bonito | Learning to Generate Instruction Tuning Datasets for Zero-Shot Task Adaptation (Bonito) | Nihal V. Nayak, Yiyang Nan, Avi Trost, Stephen H. Bach | 2024 | arXiv preprint (venue unverified) | 2402.18334 | https://github.com/BatsResearch/bonito | 829 | 2025-07-15 | BSD-3-Clause | Model + HF BatsResearch/bonito-experiment | Conditional task generator turning unannotated text into instruction data; trained on 1.65M remixed examples. | 2 | 3 | admit | 2 |
| BoostCD | Combining Constrained and Unconstrained Decoding via Boosting: BoostCD and Its Application to Information Extraction | Marija Sakota, Robert West | 2025 | EMNLP 2025 | 2506.14901 | https://github.com/epfl-dlab/BoostCD | 2 | 2025-10-28 | MIT | yes (code + models + Wiki-cIE data) | Boosted model fuses constrained+unconstrained base runs; BoostIE beats SynthIE by +17 micro-F1 in-dist, +11 OOD | 1 | 3 | admit | 6 |
| CorpusLM | CorpusLM: Towards a Unified Language Model on Corpus for Knowledge-Intensive Tasks | Li; Dou; Zhou; Liu | 2024 | SIGIR 2024 | 2402.01176 | n/a | n/a | n/a | n/a | paper only | One model unifies generative retrieval, closed-book generation and RAG in a single greedy DocIDs-References-Answer decode with ranking-oriented DocID-list training. | 3 | 3 | admit | 10 |
| DAPO | DAPO: AN OPEN-SOURCE LLM REINFORCEMENT LEARNING SYSTEM AT SCALE | Yu, Qiying; Zhang, Zheng; Zhu, Ruofei; Yuan, Yufeng; Zuo, Xiaochen; Yue, Yu et al. | 2025 | arXiv preprint (venue not verified) | 2503.14476 | https://dapo-sia.github.io/ (code built on verl: https://github.com/volcengine/verl) | 23398 | 2026-09-11 | Apache-2.0 | yes (training code, curated dataset) | decoupled-clip plus dynamic-sampling GRPO variant; 50 points on AIME 2024 with Qwen2.5-32B; fully open | 4 | 3 | admit | 4 |
| DSI | Transformer Memory as a Differentiable Search Index | Tay; Tran; Dehghani; Ni; Bahri; Mehta; Qin; Hui; Zhao; Gupta; Schuster; Cohen; Metzler | 2022 | NeurIPS 2022 | 2202.06991 | n/a | n/a | n/a | n/a | paper only | Single Transformer maps queries directly to docids; indexing and retrieval trained jointly with atomic and semantic-string docids. | 3 | 3 | admit | 10 |
| DeepSeek-Prover-V1.5 | DEEPSEEK-PROVER-V1.5: HARNESSING PROOF ASSISTANT FEEDBACK FOR REINFORCEMENT LEARNING AND MONTE-CARLO TREE SEARCH | Xin, Huajian; Ren, Z. Z.; Song, Junxiao; Shao, Zhihong; Zhao, Wanjia; Wang, Haocheng et al. | 2024 | arXiv preprint (venue not verified) | 2408.08152 |  |  |  |  | unknown | RLPAF: Lean 4 proof-assistant verdict as RL reward on a 7B prover; closest published validator-as-reward analogue | 4 | 3 | admit | 4 |
| DeepSeek-R1 | DEEPSEEK-R1: INCENTIVIZING REASONING CAPABILITY IN LLMS VIA REINFORCEMENT LEARNING | DeepSeek-AI; Guo, Daya; Yang, Dejian; Zhang, Haowei; Song, Junxiao; Wang, Peiyi et al. | 2025 | arXiv preprint (venue not verified) | 2501.12948 | https://github.com/deepseek-ai/DeepSeek-R1 | 91994 | 2025-06-27 | MIT | yes (open models incl. R1-Distill-Qwen-1.5B, 400956 HF downloads, MIT) | R1-Zero pure rule-reward RL plus distillation of reasoning traces into small models down to 1.5B | 4 | 3 | admit | 4 |
| DeepSeekMath | DEEPSEEKMATH: PUSHING THE LIMITS OF MATHEMATICAL REASONING IN OPEN LANGUAGE MODELS | Shao, Zhihong; Wang, Peiyi; Zhu, Qihao; Xu, Runxin; Song, Junxiao; Bi, Xiao et al. | 2024 | arXiv preprint (venue not verified) | 2402.03300 | https://github.com/deepseek-ai/DeepSeek-Math | 3441 | 2024-04-15 | MIT | yes (open 7B and 1.3B models, code, data pipeline) | GRPO origin paper: critic-free RL with group-normalized advantage; 7B reaches 51.7 percent on MATH | 4 | 3 | admit | 4 |
| DistiLLM | DISTILLM: TOWARDS STREAMLINED DISTILLATION FOR LARGE LANGUAGE MODELS | Ko, Jongwoo; Kim, Sungnyun; Chen, Tianyi; Yun, Se-Young | 2024 | ICML 2024 | 2402.03898 | https://github.com/jongwooko/distillm | 268 | 2025-03-13 | none listed | yes (code) | skew-KL loss plus adaptive off-policy use of student outputs; up to 4.3x speedup over on-policy KD | 4 | 3 | admit | 4 |
| DrGRPO | UNDERSTANDING R1-ZERO-LIKE TRAINING: A CRITICAL PERSPECTIVE | Liu, Zichen; Chen, Changyu; Li, Wenjun; Qi, Penghui; Pang, Tianyu; Du, Chao et al. | 2025 | arXiv preprint (venue not verified) | 2503.20783 |  |  |  |  | unknown | identifies GRPO length/normalization bias; Dr.GRPO unbiased objective; minimalist 7B recipe reaches 43.3 percent AIME 2024 | 4 | 3 | admit | 4 |
| EDC | Extract, Define, Canonicalize: An LLM-based Framework for Knowledge Graph Construction | Bowen Zhang, Harold Soh | 2024 | EMNLP 2024 | 2404.03868 |  |  | unknown | unknown | unknown | Three-phase extract/define/canonicalize KGC with a trained schema retriever for large schemas | 1 | 3 | admit | 6 |
| Echo | Repetition Improves Language Model Embeddings | Jacob Mitchell Springer; Suhas Kotha; Daniel Fried; Graham Neubig; Aditi Raghunathan | 2024 | arXiv preprint | 2402.15449 |  |  |  | unknown | unknown | Echo (repeat-input) embeddings from causal LMs gain 5%+ zero-shot with no architecture change | 3 | 3 | admit | 3 |
| FILCO | Learning to Filter Context for Retrieval-Augmented Generation | Zhiruo Wang; Jun Araki; Zhengbao Jiang; Md Rizwan Parvez; Graham Neubig | 2023 | preprint | 2311.08377 | https://github.com/zorazrw/filco | 199 | 2024-04-06 | CC-BY-SA-4.0 | code+data released | Sentence-level context filtering trained on StrInc/lexical/CXMI silver labels; +3 pts avg, 44-64% shorter prompts. | 6 | 3 | admit | 9 |
| FoFo | FoFo: A Benchmark to Evaluate LLMs' Format-Following Capability | Xia et al. | 2024 | ACL 2024 | 2402.18667 | https://github.com/SalesforceAIResearch/FoFo | 27 | 2026-06-02 | Apache-2.0 | yes: benchmark | Format-following is independent of content quality; open models lag | 1 | 3 | admit | 1 |
| Forgetting Scaling Laws | Scaling Laws for Forgetting When Fine-Tuning Large Language Models | Damjan Kalajdzievski | 2024 | not venue-checked (arXiv abs excerpt) | 2401.05605 | unknown | unverified | unverified | unverified | unknown | PEFT still forgets: forgetting is inverse-linear in FT loss and a shifted power law in params-tuned and steps; proposes pre/post cross-entropy forgetting metric. | 5 | 3 | admit | 5 |
| GENRE | Autoregressive Entity Retrieval | Nicola De Cao, Gautier Izacard, Sebastian Riedel, Fabio Petroni | 2020 | preprint (ICLR 2021) | 2010.00904 |  |  | unknown | unknown | unknown | Generates entity names with constrained beam search; cross-encodes mention and entity | 1 | 3 | admit | 6,10 |
| GKD | ON-POLICY DISTILLATION OF LANGUAGE MODELS: LEARNING FROM SELF-GENERATED MISTAKES | Agarwal, Rishabh; Vieillard, Nino; Zhou, Yongchao; Stanczyk, Piotr; Ramos, Sabela; Geist, Matthieu et al. | 2023 | ICLR 2024 | 2306.13649 |  |  |  |  | unknown | trains student on its own generated sequences with teacher feedback; unifies distillation with RLHF | 4 | 3 | admit | 4 |
| GLiNER | GLiNER: Generalist Model for Named Entity Recognition using Bidirectional Transformer | Urchade Zaratiana, Nadi Tomeh, Pierre Holat, Thierry Charnois | 2024 | NAACL 2024 | 2311.08526 | https://github.com/urchade/GLiNER | 3641 | 2026-09-08 | Apache-2.0 | yes (code + HF checkpoints; trained on Pile-NER) | Span/type dot-product matching with DeBERTa-v3 encoder beats ChatGPT zero-shot NER; CPU/ONNX/INT8 deployable | 1 | 3 | admit | 6 |
| GLiREL | GLiREL: Generalist Model for Zero-Shot Relation Extraction | Jack Boylan, Chris Hokamp, Demian Gholipour Ghalandari | 2025 | NAACL 2025 | 2501.03172 | https://github.com/jackboyla/GLiREL | 290 | 2026-03-30 | none stated | yes (code + synthetic-data generation protocol) | All entity pairs x all labels classified in one forward pass; SOTA on FewRel/WikiZSL zero-shot | 1 | 3 | admit | 6 |
| GR-as-Dense | Generative Retrieval as Dense Retrieval | Nguyen; Yates | 2023 | arXiv preprint | 2306.11397 | n/a | n/a | n/a | n/a | paper only | Analytic result: DSI/NCI-style generative retrieval decomposes into dot products between query and document vectors, i.e. a bi-encoder. | 3 | 3 | admit | 10 |
| GR-scaling | How Does Generative Retrieval Scale to Millions of Passages? | Pradeep; Hui; Gupta; Lelkes; Zhuang; Lin; Metzler; Tran | 2023 | EMNLP 2023 | 2305.11841 | n/a | n/a | n/a | n/a | paper only | At 8.8M passages only synthetic-query document representations matter; PAWA/2D-IDs/consistency-loss add nothing net of parameters, and naive parameter scaling can hurt; web-scale GR remains unsolved. | 3 | 3 | admit | 10 |
| Gemma2 | Gemma 2: Improving Open Language Models at a Practical Size | Gemma Team (Riviere et al.) | 2024 | arXiv preprint (cs.CL) | 2408.00118 | https://github.com/google-deepmind/gemma | 5723 | 2026-09-03 | Gemma license (weights, gated; per HF cardData) | yes (2B/9B/27B weights, gated) | 2B/9B trained with KD instead of next-token prediction (>50x Chinchilla tokens); SFT (behavioral cloning + on-student distillation) + RLHF + checkpoint averaging | 4 | 3 | admit | 7 |
| Gemma3 | Gemma 3 Technical Report | Gemma Team (Kamath et al.) | 2025 | arXiv preprint (cs.CL) | 2503.19786 | https://github.com/google-deepmind/gemma | 5723 | 2026-09-03 | Gemma license (weights, gated; per HF cardData) | yes (1B-27B weights, gated) | 256-logit sampled KD pre-training; post-training = IT-teacher KD + RL phase (BOND/WARM/WARP variants); Gemma3-4B-IT competitive with Gemma2-27B-IT | 4 | 3 | admit | 7 |
| GenIE | GenIE: Generative Information Extraction | Martin Josifoski, Nicola De Cao, Maxime Peyrard, Fabio Petroni, Robert West | 2022 | NAACL 2022 | 2112.08340 | https://github.com/epfl-dlab/GenIE | 104 | 2023-03-28 | MIT | yes (code + 27.7GB Zenodo data/models) | First end-to-end autoregressive closed IE with bi-level constrained generation over a Wikidata schema | 1 | 3 | admit | 6,8 |
| Gist | Learning to Compress Prompts with Gist Tokens | Jesse Mu; Xiang Lisa Li; Noah Goodman | 2023 | NeurIPS 2023 | 2304.08467 | https://github.com/jayelm/gisting | 322 | 2025-02-14 | Apache-2.0 | checkpoints released | Attention-mask trick that learns gist-token compression during instruction tuning at no extra cost; up to 26x. | 6 | 3 | admit | 9 |
| GoLLIE | GoLLIE: Annotation Guidelines improve Zero-Shot Information-Extraction | Oscar Sainz, Iker Garcia-Ferrero, Rodrigo Agerri, Oier Lopez de Lacalle, German Rigau, Eneko Agirre | 2024 | ICLR 2024 | 2310.03668 | https://github.com/hitz-zentroa/GoLLIE | 443 | 2024-10-27 | Apache-2.0 | yes (code verified; checkpoints per repo, sizes not individually verified) | Fine-tunes LLMs to follow annotation guidelines (label schemas as class definitions) for zero-shot IE | 1 | 3 | admit | 6 |
| Gorilla | Gorilla: Large Language Model Connected with Massive APIs | Patil et al. | 2023 | arXiv preprint | 2305.15334 | https://github.com/ShishirPatil/gorilla | 13021 | 2026-04-13 | Apache-2.0 | yes: model + APIBench data | First SFT recipe for API-call emission (LLaMA + retriever + APIBench) | 1 | 3 | admit | 1 |
| Granite | Granite-Function Calling Model: Introducing Function Calling Abilities via Multi-task Learning of Granular Tasks | Abdelaziz et al. | 2024 | EMNLP 2024 Industry | 2407.00121 | none verified | — | — | — | yes: Apache-2.0 20B model (reported in paper) | 7-task granular multi-task SFT with QLoRA r8 on 142k examples | 1 | 3 | admit | 1 |
| Hammer | Hammer: Robust Function-Calling for On-Device Language Models via Function Masking | Lin et al. | 2024 | arXiv preprint | 2410.04587 | https://github.com/MadeAgents/Hammer | 123 | 2025-06-13 | Apache-2.0 | yes: 1.5B/4B/7B models + 7.5k irrelevance data | Function masking + irrelevance augmentation; SFT harms abstention w/o negatives | 1 | 3 | admit | 1 |
| Humpback | Self-Alignment with Instruction Backtranslation | Xian Li, Ping Yu, Chunting Zhou, Timo Schick, Omer Levy, Luke Zettlemoyer, Jason Weston, Mike Lewis | 2023 | arXiv preprint (venue unverified) | 2308.06259 | none official (unofficial: github.com/Spico197/Humpback, 139 stars) | unverified | unverified | unverified | No official release verified | Backtranslates instructions from unannotated web segments (502K) and filters by self-consistency; beats text-davinci-003 win-rate. | 2 | 3 | admit | 2 |
| ICAE | In-context Autoencoder for Context Compression in a Large Language Model | Tao Ge; Jing Hu; Lei Wang; Xun Wang; Si-Qing Chen; Furu Wei | 2024 | ICLR 2024 | 2307.06945 | https://github.com/getao/icae | 178 | 2024-05-11 | CC0-1.0 | PWC 240k dataset and LoRA-encoder model released | LoRA encoder (~1% params) compresses context to memory slots for a frozen LLM; AE+LM pretrain then instruction fine-tune; 4x. | 6 | 3 | admit | 9 |
| InstructRetro | InstructRetro: Instruction Tuning post Retrieval-Augmented Pretraining | Wang; Ping; McAfee; Xu; Li; Shoeybi; Catanzaro | 2023 | ICML 2024 | 2310.07713 | code in NVIDIA/Megatron-LM InstructRetro branch (per paper); checkpoint https://huggingface.co/nvidia/retro-8b-instruct-4k (HF page verified) | n/a (branch of monorepo) | n/a | n/a | checkpoint (8B instruct, HF) plus code (branch) | Continued retrieval-augmented pre-training of a 43B GPT on 100B tokens over 1.2T-token store, then instruction tuning; the Retro encoder can be ablated away and the decoder alone keeps the gains. | 3,4 | 3 | admit | 10 |
| Intruder Dimensions | LoRA vs Full Fine-tuning: An Illusion of Equivalence | Reece Shuttleworth, Jacob Andreas, Antonio Torralba, Pratyusha Sharma | 2024 | NeurIPS 2025 (proceedings PDF URL) | 2410.21228 | unknown | unverified | unverified | unverified | unknown | LoRA creates high-ranking intruder singular vectors that cause forgetting; scaling them down cuts forgetting with minimal task loss; fixed-alpha high-rank LoRA forgets more. | 5 | 3 | admit | 5 |
| KILT | KILT: a Benchmark for Knowledge Intensive Language Tasks | Fabio Petroni et al. (13 authors) | 2021 | NAACL 2021 | 2009.02252 | https://github.com/facebookresearch/KILT | 978 | 2022-03-31 | MIT | yes: code, 11 datasets on one Wikipedia snapshot | Unifies 5 knowledge-intensive tasks on one snapshot; KILT score requires provenance (R-precision 1) AND downstream output correct: joint retrieval-generation metric. | 6 | 3 | admit | 8 |
| KTO | MODEL ALIGNMENT AS PROSPECT THEORETIC OPTIMIZATION | Ethayarajh, Kawin; Xu, Winnie; Muennighoff, Niklas; Jurafsky, Dan; Kiela, Douwe | 2024 | arXiv preprint (venue not verified) | 2402.01306 |  |  |  |  | unknown | matches/exceeds preference methods at 1B to 30B from binary desirable/undesirable signals only | 4 | 3 | admit | 4 |
| KaLM | KaLM: Knowledge-aligned Autoregressive Language Modeling via Dual-view Knowledge Graph Contrastive Learning | Peng Yu; Cheng Deng; Beiya Dai; Xinbing Wang; Ying Wen | 2024 | arXiv preprint | 2412.04948 |  |  |  | unknown | unknown | Joint explicit KG-alignment plus implicit AR objectives; reports prior attempts compromised generation | 3 | 3 | admit | 3 |
| KnowCoder | KnowCoder: Coding Structured Knowledge into LLMs for Universal Information Extraction | Zixuan Li, Yutao Zeng, Yuxin Zuo, Weicheng Ren, Wenxuan Liu, Miao Su, Yucan Guo, Yantao Liu, Xiang Li, Zhilei Hu, Long Bai, Wei Li, Yidan Liu, Pan Yang, Xiaolong Jin, Jiafeng Guo, Xueqi Cheng | 2024 | ACL 2024 | 2403.07969 | https://github.com/ICT-GoKnow/KnowCoder | 108 | 2025-05-28 | NOASSERTION | yes (code + 30k-type schema library + data + model per repo) | Python-class schema representation; 1.5B-token code pretrain then instruction tune; +49.8% few-shot vs LLaMA2 | 1 | 3 | admit | 6 |
| LFM2 | LFM2 Technical Report | Amini et al. | 2025 | arXiv preprint (cs.LG) | 2511.23404 | n/a | n/a | n/a | custom LFM license (HF cardData: other) | yes (350M-8.3B weights + ExecuTorch/llama.cpp/vLLM packs on HF) | SFT 3 epochs cosine 3e-5 to 1e-7 (500-step warmup, AdamW 0.9/0.95, wd 0.1); length-normalized offline+on-policy preference opt; model merging (soup/TIES/DARE/DELLA); tempered decoupled Top-K KD in pretraining; LFM2-Nanos for extraction/tool-call/RAG | 4 | 3 | admit | 7 |
| LIMA | LIMA: Less Is More for Alignment | Chunting Zhou, Pengfei Liu, Puxin Xu, Srini Iyer, Jiao Sun, Yuning Mao, Xuezhe Ma, Avia Efrat, Ping Yu, Lili Yu, Susan Zhang, Gargi Ghosh, Mike Lewis, Luke Zettlemoyer | 2023 | arXiv preprint (venue unverified) | 2305.11206 | none verified | unverified | unverified | unverified | 1,000-example set described in paper | 1,000 curated examples align a 65B model (superficial-alignment hypothesis). | 2 | 3 | admit | 2 |
| LLMCompiler | An LLM Compiler for Parallel Function Calling | Kim et al. | 2023 | arXiv preprint | 2312.04511 | none verified | — | — | — | yes: framework code (reported in paper) | Plan-then-DAG-execute grammar for parallel calls; TinyAgent builds on it | 1 | 3 | admit | 1 |
| LLMLingua | LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models | Huiqiang Jiang; Qianhui Wu; Chin-Yew Lin; Yuqing Yang; Lili Qiu | 2023 | EMNLP 2023 | 2310.05736 | https://github.com/microsoft/LLMLingua | 6650 | 2026-09-10 | MIT | code+models released | Small-LM perplexity coarse-to-fine prompt compression with budget controller and distribution alignment, up to 20x compression. | 6 | 3 | admit | 9 |
| LLMLingua-2 | LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression | Zhuoshi Pan; Qianhui Wu; Huiqiang Jiang; Menglin Xia; Xufang Luo; Jue Zhang et al. | 2024 | Findings of ACL 2024 | 2403.12968 | https://github.com/microsoft/LLMLingua | 6650 | 2026-09-10 | MIT | extractive compression dataset released | Distils GPT-4 compression into a token-classification compressor (XLM-R/mBERT); task-agnostic, 3-6x faster. | 6 | 3 | admit | 9 |
| LiteGUI | LITEGUI: DISTILLING COMPACT GUI AGENTS WITH REINFORCEMENT LEARNING | Wu, Yubin; Cai, Zicheng; Ning, Liping; Wang, Hua; Chen, Zhi; Tang, Yaohua et al. | 2026 | arXiv preprint (venue not verified) | 2605.07505 |  |  |  |  | unknown | SFT-free on-policy (GKD-style) distillation plus dual-level GRPO unlocks 2B/3B agents past imitation-learning limits | 4 | 3 | admit | 4 |
| LoRA | LoRA: Low-Rank Adaptation of Large Language Models | Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Shean Wang, Lu Wang, Weizhu Chen | 2021 | not venue-checked (arXiv abs opened) | 2106.09685 | https://github.com/microsoft/LoRA | 13789 | 2024-12-17T03:55:52Z | MIT | code+checkpoints (per paper) | Freezes base weights, trains rank-r BA adapters; includes rank-deficiency and W_q/W_v-only ablations. | 5 | 3 | admit | 5 |
| LoRA+ | LoRA+: Efficient Low Rank Adaptation of Large Models | Soufiane Hayou, Nikhil Ghosh, Bin Yu | 2024 | ICML 2024 (PMLR v235) | 2402.12354 | https://github.com/nikhil-ghosh-berkeley/loraplus (in paper; API lookup failed 2026-09-12) | unverified | unverified | unverified | code (per PMLR page) | Same LR for A and B is inefficient at width; fixed ratio eta_B >> eta_A gives ~2x speedup and 1-2% gains at LoRA cost. | 5 | 3 | admit | 5 |
| LoRA-Learns-Less | LoRA Learns Less and Forgets Less | Dan Biderman; Jacob Portes; Jose Javier Gonzalez Ortiz; Mansheej Paul; Philip Greengard; Connor Jennings; Daniel King; Sam Havens; Vitaliy Chiley; Jonathan Frankle; Cody Blakeney; John P. Cunningham | 2024 | TMLR | 2405.09673 |  |  |  | unknown | unknown | LoRA underperforms full FT on target but forgets less; full-FT perturbations are 10-100x the rank of LoRA | 3 | 3 | admit | 3,5 |
| LoRA-Null | LoRA-Null: Low-Rank Adaptation via Null Space for Large Language Models (v2 retitled Put the Space of LoRA Initialization to the Extreme to Preserve Pre-trained Knowledge) | Pengwei Tang, Xiaolin Hu, Yong Liu, Lizhong Ding, Dongjie Zhang, Xing Wu, Debing Zhang | 2025 | AAAI 2026 | 2503.02659 | https://github.com/HungerPWAY/LoRA-Null | 11 | 2026-01-16T16:23:12Z | no license declared | code | Init A in null space of sampled pre-trained activations, freeze A, train B; higher rank trades retention for capacity; compares directly vs LoRA-FA/PiSSA/MiLoRA. | 5 | 3 | admit | 5 |
| LoRAHub | LoraHub: Efficient Cross-Task Generalization via Dynamic LoRA Composition | Chengsong Huang; Qian Liu; Bill Yuchen Lin; Tianyu Pang; Chao Du; Min Lin | 2023 | COLM 2024 | 2307.13269 | https://github.com/sail-sg/lorahub | 669 | 2024-07-22 | MIT | code + HF lorahub modules released | Gradient-free composition of a library of task LoRAs for few-shot transfer | 3 | 3 | admit | 3 |
| LoRAMoE | LoRAMoE: Alleviate World Knowledge Forgetting in Large Language Models via MoE-Style Plugin | Shihan Dou; Enyu Zhou; Yan Liu; Songyang Gao; Jun Zhao; Wei Shen; Yuhao Zhou; Zhiheng Xi | 2023 | arXiv preprint | 2312.09979 |  |  |  | unknown | unknown | Frozen backbone + routed LoRA experts with a world-knowledge expert split; forgetting worsens with more instruction data | 3 | 3 | admit | 3 |
| LongLLMLingua | LongLLMLingua: Accelerating and Enhancing LLMs in Long Context Scenarios via Prompt Compression | Huiqiang Jiang; Qianhui Wu; Xufang Luo; Dongsheng Li; Chin-Yew Lin; Yuqing Yang; Lili Qiu | 2024 | ACL 2024 | 2310.06839 | https://github.com/microsoft/LLMLingua | 6650 | 2026-09-10 | MIT | code released (shared repo) | Question-aware compression via contrastive perplexity plus document reordering; NQ +21.4% with 4x fewer tokens. | 6 | 3 | admit | 9 |
| Lost-in-the-Middle | Lost in the Middle: How Language Models Use Long Contexts | Nelson F. Liu; Kevin Lin; John Hewitt; Ashwin Paranjape; Michele Bevilacqua; Fabio Petroni; Percy Liang | 2024 | TACL 2024 | 2307.03172 | https://github.com/nelson-liu/lost-in-the-middle-code | unknown | unknown | unknown | code+data released per paper | U-shaped position bias; reader QA saturates by ~20 docs; recommends reranking and truncation. | 6 | 3 | admit | 9 |
| MTEB | MTEB: Massive Text Embedding Benchmark | Niklas Muennighoff, Nouamane Tazi, Loic Magne, Nils Reimers | 2023 | EACL 2023 | 2210.07316 | https://github.com/embeddings-benchmark/mteb | 3420 | 2026-09-11 | Apache-2.0 | yes: code, 58 datasets, HF leaderboard | 8-task embedding benchmark (retrieval, STS, clustering, rerank, classification...); no single method dominates all tasks. | 3 | 3 | admit | 8 |
| Magpie | Magpie: Alignment Data Synthesis from Scratch by Prompting Aligned LLMs with Nothing | Zhangchen Xu, Fengqing Jiang, Luyao Niu, Yuntian Deng, Radha Poovendran, Yejin Choi, Bill Yuchen Lin | 2024 | ICLR 2025 (per author repo description) | 2406.08464 | https://github.com/magpie-align/magpie | 884 | 2025-03-17 | MIT | Data: HF Magpie-Align org (e.g. Pro 300K); 4M generated, 300K filtered per paper | Extracts instruction data from an aligned teacher using only its pre-query template; SFT-only rivals SFT+DPO pipelines. | 2 | 3 | admit | 2 |
| MiniCPM-2024 | MiniCPM: Unveiling the Potential of Small Language Models with Scalable Training Strategies | Hu et al. | 2024 | arXiv preprint (cs.CL) | 2404.06395 | https://github.com/OpenBMB/MiniCPM | 10885 | 2026-09-12 | Apache-2.0 | yes (weights on HF, code on GitHub) | WSD LR schedule; decay-stage annealing on pretrain+SFT mix (20B tokens); separate ~6B-token SFT; DPO family member | 4 | 3 | admit | 7 |
| MiniCPM4 | MiniCPM4: Ultra-Efficient LLMs on End Devices | MiniCPM Team (Xiao et al.) | 2025 | arXiv preprint (cs.CL) | 2506.07900 | https://github.com/OpenBMB/MiniCPM | 10885 | 2026-09-12 | Apache-2.0 | yes (0.5B/8B weights on HF, CPM.cu code) | UltraChat v2 SFT dataset; ModelTunnel v2 hyperparam search; chunk-wise rollout load-balanced RL; BitCPM ternary QAT | 4 | 3 | admit | 7 |
| MiniLLM | MINILLM: ON-POLICY DISTILLATION OF LARGE LANGUAGE MODELS | Gu, Yuxian; Dong, Li; Wei, Furu; Huang, Minlie | 2023 | ICLR 2024 | 2306.08543 | https://github.com/microsoft/LMOps | 4473 | 2026-07-25 | MIT | yes (code, data, checkpoints per abstract) | reverse-KL on-policy distillation for generative LMs; scales 120M to 13B | 4 | 3 | admit | 4 |
| MiniRAG | MiniRAG: Towards Extremely Simple Retrieval-Augmented Generation | Fan; Wang; Ren; Huang | 2025 | ACL 2026 (arXiv Jan 2025; repo labels ACL2026) | 2501.06713 | https://github.com/HKUDS/MiniRAG | 2014 | 2025-10-16T07:43:16Z | MIT | code plus LiHua-World benchmark data (repo) | Heterogeneous chunk-entity graph plus lightweight topology retrieval lets 1.5B-4B SLMs (incl. MiniCPM3-4B, Qwen2.5-3B) match LLM RAG at 25 percent storage; entity extraction is the designated easy subtask. | 3,6 | 3 | admit | 10 |
| MoLF | Beyond LoRA vs. Full Fine-Tuning: Gradient-Guided Optimizer Routing for LLM Adaptation | Haozhan Tang; Xiuqi Zhu; Xinyin Zhang; Boxun Li; Virginia Smith; Kevin Kuo | 2026 | arXiv preprint | 2605.07111 | https://github.com/11785T23/molf | 3 | 2026-07-02 | Apache-2.0 | training code released | Optimizer-level routing between FFT and LoRA experts tested at Gemma-3-1B and Qwen2.5-1.5B/3B | 3 | 3 | admit | 3 |
| MoLoRA | MoLoRA: Composable Specialization via Per-Token Adapter Routing | Shrey Shah; Justin Wagle | 2026 | arXiv preprint | 2603.15965 |  |  |  | unknown | unknown | Per-token adapter routing proven optimal vs per-sequence; Qwen3-1.7B exceeds Qwen3-8B via specialization | 3 | 3 | admit | 3 |
| NCI | A Neural Corpus Indexer for Document Retrieval | Wang; Hou; Wang; Miao; Wu; Chen; Xia; Chi; Zhao; Liu; Xie; Sun; Deng; Zhang; Yang | 2022 | NeurIPS 2022 | 2206.02743 | n/a | n/a | n/a | n/a | paper only | Seq2seq retriever with prefix-aware weight-adaptive decoder, semantic docids from hierarchical k-means, query-generation augmentation and consistency regularization. | 3 | 3 | admit | 10 |
| NV-Embed | NV-Embed: Improved Techniques for Training LLMs as Generalist Embedding Models | Chankyu Lee; Rajarshi Roy; Mengyao Xu; Jonathan Raiman; Mohammad Shoeybi; Bryan Catanzaro; Wei Ping | 2024 | arXiv preprint | 2405.17428 |  |  |  | unknown | unknown | Latent-attention pooling plus causal-mask removal plus two-stage contrastive instruction tuning with hard negatives | 3 | 3 | admit | 3 |
| OPLoRA | OPLoRA: Orthogonal Projection LoRA Prevents Catastrophic Forgetting during Parameter-Efficient Fine-Tuning | Yifeng Xiong, Xiaohui Xie | 2025 | AAAI 2026 | 2510.13003 | unknown | unverified | unverified | unverified | unknown | Double-sided projections constrain updates to orthogonal complement of top-k singular subspace with preservation proof; rho_k interference metric; Llama-2-7B + Qwen2.5-7B. | 5 | 3 | admit | 5 |
| OPR | On-Policy Replay for Continual Supervised Fine-Tuning | Yan Chen; Taojie Zhu; Meng Zhang; Xin Chen; Jiaqi Huang; Dongyang Xu; Yizhi Wang | 2026 | arXiv preprint | 2605.29495 | https://github.com/Yancey2024/OnPolicyReplay | 3 | 2026-05-29 | none | training code released | Replay of reward-filtered own-outputs as plain SFT; no teacher; KL-shrinkage interpretation; BWT -13.93 to -0.65 | 3 | 3 | admit | 3 |
| OneShotRLVR | REINFORCEMENT LEARNING FOR REASONING IN LARGE LANGUAGE MODELS WITH ONE TRAINING EXAMPLE | Wang, Yiping; Yang, Qing; Zeng, Zhiyuan; Ren, Liliang; Liu, Liyuan; Peng, Baolin et al. | 2025 | NeurIPS 2025 (per repo description) | 2504.20571 | https://github.com/ypwang61/One-Shot-RLVR | 445 | 2026-03-11 | Apache-2.0 | yes (code and resources) | 1-example RLVR lifts Qwen2.5-Math-1.5B MATH500 36.0 to 73.6 percent; matches 1.2k-example run; entropy bonus critical | 4 | 3 | admit | 4 |
| Outlines | Efficient Guided Generation for Large Language Models | Willard & Louf | 2023 | arXiv preprint | 2307.09702 | https://github.com/dottxt-ai/outlines | 15788 | 2026-09-09 | Apache-2.0 | yes: Outlines library | FSM-index constrained decoding at ~O(1) per step | 1 | 3 | admit | 1 |
| PEFT-for-RLVR | EVALUATING PARAMETER EFFICIENT METHODS FOR RLVR | Yin, Qingyu; Wu, Yulun; Shen, Zhennan; Li, Sunbowen; Wang, Zhilin; Li, Yanshu et al. | 2025 | arXiv preprint (venue not verified) | 2512.23165 |  |  |  |  | unknown | first systematic PEFT-under-RLVR study on R1-Distill models: DoRA/AdaLoRA/MiSS beat LoRA; PiSSA spectral collapse; rank-1 bottlenecks | 4,5 | 3 | admit | 4 |
| PPI | Prediction-Powered Inference | Anastasios Angelopoulos, Stephen Bates, Clara Fannjiang, Michael Jordan, Tijana Zrnic | 2023 | Science 382 (6671) | 2301.09633 |  |  |  |  | yes: code linked from paper (URL not recorded) | Valid confidence intervals combining a small labeled set with many model predictions; more accurate predictor means tighter intervals. | 3 | 3 | admit | 8 |
| PersonaHub | Scaling Synthetic Data Creation with 1,000,000,000 Personas | Tao Ge, Xin Chan, Xiaoyang Wang, Dian Yu, Haitao Mi, Dong Yu | 2024 | arXiv preprint (venue unverified) | 2406.20094 | none verified (github.com/proj-persona/PersonaHub returns 404) | unverified | unverified | unverified | Data: HF proj-persona/PersonaHub (800 likes) | 1B web-mined personas as generation lenses for math, instructions, knowledge, NPC and tool data. | 2 | 3 | admit | 2 |
| Phi-4 | Phi-4 Technical Report | Abdin et al. | 2024 | arXiv preprint (cs.CL) | 2412.08905 | n/a | n/a | n/a | MIT (weights per HF) | yes (weights on HF) | 50-type synthetic data factory (~400B tokens: multi-agent prompting, self-revision, instruction reversal); SFT then pivotal-token DPO + judge-guided DPO (~850k pairs) | 2 | 3 | admit | 7 |
| Phi-4-mini | Phi-4-Mini Technical Report: Compact yet Powerful Multimodal Language Models via Mixture-of-LoRAs | Microsoft (Abouelenin et al.) | 2025 | arXiv preprint (cs.CL) | 2503.01743 | n/a | n/a | n/a | MIT (weights per HF) | yes (3.8B weights on HF) | 3.8B on synthetic-heavy reasoning/code mix with enlarged function-calling + summarization SFT; frozen backbone + per-modality LoRA routers (Mixture-of-LoRAs) for interference-free extension | 1 | 3 | admit | 7 |
| Phi-4-mini-reasoning | Phi-4-Mini-Reasoning: Exploring the Limits of Small Reasoning Language Models in Math | Xu et al. | 2025 | arXiv preprint (cs.CL) | 2504.21233 | n/a | n/a | n/a | MIT (weights per HF) | yes (weights + 150B-token training disclosure on HF card) | 3.8B: large-scale mid-training on distilled long-CoT, SFT on 200K curated CoT, rollout DPO on 300K pairs (LR 5e-7, 1 epoch), then verifiable-reward RL; beats 7-8B distills on MATH-500 | 4 | 3 | admit | 7 |
| Prometheus | Prometheus: Inducing Fine-grained Evaluation Capability in Language Models | Seungone Kim et al. | 2024 | ICLR 2024 | 2310.08491 | https://github.com/prometheus-eval/prometheus | 325 | 2023-11-11 | MIT | yes: code, Feedback Collection, 13B evaluator on HF | Open 13B evaluator trained on 1K rubrics/100K GPT-4 feedbacks; Pearson 0.897 with humans, on par with GPT-4 when reference materials accompany. | 6 | 3 | admit | 8 |
| Prometheus-2 | Prometheus 2: An Open Source Language Model Specialized in Evaluating Other Language Models | Seungone Kim et al. | 2024 | EMNLP 2024 | 2405.01535 | https://github.com/prometheus-eval/prometheus-eval | 1115 | 2025-04-25 | Apache-2.0 | yes: code, Preference Collection, 7B and 8x7B evaluators | Adds pairwise ranking via weight-merged direct-assessment and preference models; 0.6-0.7 Pearson with GPT-4, 72-85pct human agreement. | 6 | 3 | admit | 8 |
| Qwen2.5 | Qwen2.5 Technical Report | Qwen Team (Yang et al.) | 2024 | arXiv preprint (cs.CL) | 2412.15115 | n/a | n/a | n/a | Apache-2.0 (weights per HF) | yes (0.5B-72B weights on HF) | SFT on 1M+ samples, 2 epochs, seq 32768, LR 7e-6 to 7e-7, wd 0.1; then offline DPO + online GRPO | 4 | 3 | admit | 7 |
| Qwen3 | Qwen3 Technical Report | Qwen Team (Yang et al.) | 2025 | arXiv preprint (cs.CL) | 2505.09388 | https://github.com/QwenLM/Qwen3 | 27609 | 2026-01-09 | Apache-2.0 (weights per HF) | yes (0.6B-235B weights on HF) | 4-stage post-training (long-CoT cold start, reasoning GRPO on 3995 pairs, mode-fusion SFT, general RL); small models via off-policy + on-policy (KL) strong-to-weak distillation, which beats RL at ~1/10 GPU-hours | 4 | 3 | admit | 7 |
| RA-DIT | RA-DIT: Retrieval-Augmented Dual Instruction Tuning | Lin; Chen; Chen; Shi; Lomeli; James; Rodriguez; Kahn; Szilvasy; Lewis; Zettlemoyer; Yih | 2023 | ICLR 2024 | 2310.01352 | https://github.com/facebookresearch/RA-DIT | 3 | 2025-09-18T22:46:13Z | NOASSERTION (no machine-readable license) | code (artifact release) | Lightweight two-step retrofit of any LLM (7B/13B/65B tested): retrieval-augmented instruction tuning for the LM plus LM-supervised retriever tuning; parametric knowledge preserved on 7/8 control tasks. | 3,4 | 3 | admit | 10 |
| RAD | Knowing but Not Saying: Preventing Factual Access Failures in LLM SFT via Recall-Anchored Distillation | Haodong Chen; Yadong Wang; Shengtao Wen; Dong Liang; Xiang Chen | 2026 | arXiv preprint | 2608.20794 |  |  |  | unknown | unknown | Base-anchored self-distillation on unlabeled OOD text; soft-distribution signal beats replay on same text | 3 | 3 | admit | 3 |
| RAFT | RAFT: Adapting Language Model to Domain Specific RAG | Tianjun Zhang, Shishir G. Patil, Naman Jain, Sheng Shen, Matei Zaharia, Ion Stoica, Joseph E. Gonzalez | 2024 | arXiv preprint (venue unverified) | 2403.10131 | none found | unverified | unverified | unverified | Recipe + dataset construction (NQ, HotpotQA, Gorilla API) described in paper | Trains with golden + distractor documents and CoT answers so the model reasons over retrieved context. | 2 | 3 | admit | 2,10 |
| RAGAS | Ragas: Automated Evaluation of Retrieval Augmented Generation | Shahul Es, Jithin James, Luis Espinosa-Anke, Steven Schockaert | 2024 | EACL 2024 System Demonstrations | 2309.15217 | https://github.com/vibrantlabsai/ragas | 15714 | 2026-02-24 | Apache-2.0 | yes: code, WikiEval dataset on HF | Reference-free RAG metrics (faithfulness, answer relevance, context relevance) via LLM prompts; validated against human judgments on WikiEval. | 6 | 3 | admit | 8 |
| RAPTOR | RAPTOR: Recursive Abstractive Processing for Tree-Organized Retrieval | Parth Sarthi; Salman Abdullah; Aditi Tuli; Shubh Khanna; Anna Goldie; Christopher D. Manning | 2024 | ICLR 2024 | 2401.18059 | https://github.com/parthsarthi03/raptor | 1755 | 2024-09-03 | MIT | code released | Recursive embed-cluster-summarize tree; collapsed-tree retrieval mixes abstraction levels; QuALITY +20pp with GPT-4. | 6 | 3 | admit | 9 |
| REALM | REALM: Retrieval-Augmented Language Model Pre-Training | Guu; Lee; Tung; Pasupat; Chang | 2020 | ICML 2020 | 2002.08909 | https://github.com/google-research/language (monorepo; REALM code under language/realm) | 1799 | 2026-06-10T18:34:36Z | Apache-2.0 | code (monorepo subdir) | First unsupervised joint pre-training of a dense retriever with an LM via backprop through MIPS over millions of docs with async index refresh. | 3 | 3 | admit | 10 |
| RECOMP | RECOMP: Improving Retrieval-Augmented LMs with Compression and Selective Augmentation | Fangyuan Xu; Weijia Shi; Eunsol Choi | 2024 | ICLR 2024 | 2310.04408 | https://github.com/carriex/recomp | 149 | 2026-01-06 | MIT | extractive+abstractive compressors on Hugging Face; code released | End-task-trained extractive and abstractive query-focused compressors with selective (possibly empty) augmentation. | 6 | 3 | admit | 9 |
| REPLUG | REPLUG: Retrieval-Augmented Black-Box Language Models | Shi; Min; Yasunaga; Seo; James; Lewis; Zettlemoyer; Yih | 2023 | NAACL 2024 | 2301.12652 | https://github.com/swj0419/REPLUG (URL as claimed in paper; GitHub API returned 404 on 2026-09-12) | n/a (unverifiable) | n/a | n/a | unverified | Black-box LM with a tunable retriever supervised by LM perplexity (REPLUG LSR); improves GPT-3 175B LM likelihood 6.3 percent and Codex 5-shot MMLU 5.1 percent. | 3,4 | 3 | admit | 10 |
| RETRO | Improving Language Models by Retrieving from Trillions of Tokens | Borgeaud; Mensch; Hoffmann; et al. (DeepMind) | 2022 | ICML 2022 (arXiv Dec 2021) | 2112.04426 | n/a | n/a | n/a | n/a | paper only | Frozen BERT retriever plus differentiable encoder and chunked cross-attention matches GPT-3-scale Pile performance with 25x fewer parameters; any transformer can be RETROfitted. | 3 | 3 | admit | 10 |
| RFT | SCALING RELATIONSHIP ON LEARNING MATHEMATICAL REASONING WITH LARGE LANGUAGE MODELS | Yuan, Zheng; Yuan, Hongyi; Li, Chengpeng; Dong, Guanting; Lu, Keming; Tan, Chuanqi et al. | 2023 | arXiv preprint (working paper) | 2308.01825 |  |  |  |  | unknown | rejection-sampling fine-tuning on self-generated correct paths; log-linear data scaling; LLaMA-7B GSM8K 35.9 to 49.3 percent | 4 | 3 | admit | 4 |
| RLAIF | RLAIF VS. RLHF: SCALING REINFORCEMENT LEARNING FROM HUMAN FEEDBACK WITH AI FEEDBACK | Lee, Harrison; Phatale, Samrat; Mansoor, Hassan; Mesnard, Thomas; Ferret, Johan; Lu, Kellie et al. | 2023 | arXiv preprint (venue not verified) | 2309.00267 |  |  |  |  | unknown | AI-labeled preferences match RLHF; works even when labeler equals policy size; direct-RLAIF scores rewards straight from an off-the-shelf LLM | 4 | 3 | admit | 4 |
| RLOO | BACK TO BASICS: REVISITING REINFORCE STYLE OPTIMIZATION FOR LEARNING FROM HUMAN FEEDBACK IN LLMS | Ahmadian, Arash; Cremer, Chris; Galle, Matthias; Fadaee, Marzieh; Kreutzer, Julia; Pietquin, Olivier et al. | 2024 | arXiv preprint (venue not verified) | 2402.14740 |  |  |  |  | unknown | REINFORCE leave-one-out baseline outperforms PPO and DPO/RAFT at lower cost; no critic network | 4 | 3 | admit | 4 |
| RankGPT | Is ChatGPT Good at Search? Investigating Large Language Models as Re-Ranking Agents | Weiwei Sun; Lingyong Yan; Xinyu Ma; Shuaiqiang Wang; Pengjie Ren; Zhumin Chen; Dawei Yin; Zhaochun Ren | 2023 | EMNLP 2023 | 2304.09542 | https://github.com/sunnweiwei/RankGPT | 669 | 2024-03-10 | Apache-2.0 | code released | Instructional permutation generation with sliding window; GPT-4 beats supervised rankers; distilled 435M student beats 3B monoT5 on BEIR. | 6 | 3 | admit | 9 |
| RankRAG | RankRAG: Unifying Context Ranking with Retrieval-Augmented Generation in LLMs | Yu; Ping; Liu; Wang; You; Zhang; Shoeybi; Catanzaro | 2024 | NeurIPS 2024 | 2407.02485 | n/a | n/a | n/a | n/a | paper only | One instruction-tuned LLM does both context ranking and answer generation; a small ranking-data fraction beats expert rankers and lifts nine RAG benchmarks at 8B and 70B. | 3 | 3 | admit | 10 |
| Re-DocRED | Revisiting DocRED - Addressing the False Negative Problem in Relation Extraction | Qingyu Tan, Lu Xu, Lidong Bing, Hwee Tou Ng, Sharifah Mahani Aljunied | 2022 | EMNLP 2022 | 2205.12696 | https://github.com/tonytan48/re-docred | 68 | 2023-08-21 | MIT | yes (re-annotated dataset + eval script) | Re-annotated 4053 docs (64.6% triples were missing); models gain ~13 F1; adds freq/long-tail/intra/inter metrics | 2 | 3 | admit | 6,8 |
| ReLiK | ReLiK: Retrieve and LinK, Fast and Accurate Entity Linking and Relation Extraction on an Academic Budget | Riccardo Orlando, Pere-Lluis Huguet Cabot, Edoardo Barba, Roberto Navigli | 2024 | Findings of ACL 2024 | 2408.00103 | https://github.com/SapienzaNLP/relik | 518 | 2025-07-29 | none stated | yes (code + tiny/small/base/large/XL HF checkpoints incl. closed-IE) | Retriever-reader EL+RE with shared reader doing closed IE in one forward pass; SOTA on academic budget | 1 | 3 | admit | 6 |
| Robust-RALM | Making Retrieval-Augmented Language Models Robust to Irrelevant Context | Ori Yoran; Tomer Wolfson; Ori Ram; Jonathan Berant | 2023 | preprint | 2310.01558 |  |  | none confirmed | not recorded (merge column shift) | unknown | Characterizes when retrieval hurts QA; NLI back-off baseline; 1000-example mixed relevant/irrelevant fine-tune yields robustness. | 6 | 3 | admit | 9 |
| SEAL | Autoregressive Search Engines: Generating Substrings as Document Identifiers | Bevilacqua; Ottaviano; Lewis; Yih; Riedel; Petroni | 2022 | arXiv preprint | 2204.10628 | https://github.com/facebookresearch/SEAL | 296 | 2023-04-04T12:21:57Z | NOASSERTION (no machine-readable license) | code (repo) | Generates corpus-grounded n-gram identifiers under FM-index-constrained decoding and scores documents by aggregating identifier scores. | 3,1 | 3 | admit | 10 |
| STaR | STAR: BOOTSTRAPPING REASONING WITH REASONING | Zelikman, Eric; Wu, Yuhuai; Mu, Jesse; Goodman, Noah D. | 2022 | arXiv preprint (venue not verified) | 2203.14465 |  |  |  |  | unknown | iterative loop: generate rationales, keep those yielding correct answers (validator filter), retrain; matches 30x larger SOTA | 4 | 3 | admit | 4 |
| Self-Instruct | Self-Instruct: Aligning Language Models with Self-Generated Instructions | Yizhong Wang, Yeganeh Kordi, Swaroop Mishra, Alisa Liu, Noah A. Smith, Daniel Khashabi, Hannaneh Hajishirzi | 2022 | ACL 2023 | 2212.10560 | https://github.com/yizhongw/self-instruct | 4611 | 2023-03-27 | Apache-2.0 | Code + 52K dataset (HF yizhongw/self_instruct) | Bootstraps 52K instructions from seed tasks with similarity filtering; +33% absolute on SuperNI. | 2 | 3 | admit | 2 |
| Self-RAG | Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection | Akari Asai; Zeqiu Wu; Yizhong Wang; Avirup Sil; Hannaneh Hajishirzi | 2024 | ICLR 2024 | 2310.11511 | https://github.com/AkariAsai/self-rag | 2424 | 2024-05-25 | MIT | 7B/13B generator and critic models released | Reflection tokens for on-demand retrieval and self-critique distilled offline from GPT-4; 7B beats ChatGPT on ODQA/reasoning. | 6 | 3 | admit | 9,10 |
| SeqKD | SEQUENCE-LEVEL KNOWLEDGE DISTILLATION | Kim, Yoon; Rush, Alexander M. | 2016 | arXiv preprint (venue not verified) | 1606.07947 |  |  |  |  | unknown | train student on teacher-generated sequences rather than token labels; best student 10x faster with little loss | 4 | 3 | admit | 4 |
| SmolLM2 | SmolLM2: When Smol Goes Big -- Data-Centric Training of a Small Language Model | Allal et al. | 2025 | arXiv preprint (cs.CL) | 2502.02737 | https://github.com/huggingface/smollm | 3891 | 2026-05-26 | Apache-2.0 | yes (weights, SmolTalk/FineMath/Stack-Edu datasets, alignment-handbook configs) | 1.7B on 11T tokens multi-stage; SFT on SmolTalk 2 epochs LR 3e-4 BS128 seq8192; DPO on UltraFeedback 2 epochs LR 1e-6 beta 0.5 | 4 | 3 | admit | 7 |
| SmolTulu | SmolTulu: Higher Learning Rate to Batch Size Ratios Can Lead to Better Reasoning in SLMs | Alrashed | 2024 | arXiv preprint (cs.CL) | 2412.08347 | n/a (HF: SultanR/SmolTulu-1.7b-Instruct) | n/a | n/a | Apache-2.0 (weights per HF) | yes (weights + RLVR variant on HF) | Tulu-3 pipeline adapted to SmolLM2-1.7B: reasoning (ARC/GSM8K) wants high LR/BS ratio (SFT LR/BS 11.25e-6), DPO 8e-7/BS12 len-normed beta 5.0; IFEval 67.7%, GSM8K 51.6% | 4 | 3 | admit | 7 |
| Smucker-CIKM07 | A comparison of statistical significance tests for information retrieval evaluation | Mark Smucker, James Allan, Ben Carterette | 2007 | CIKM 2007 | 10.1145/1321440.1321528 |  |  |  |  | no (author-hosted paper PDF only) | Randomization, bootstrap-shift, and paired t-tests agree on TREC runs; Wilcoxon and sign tests mislead and should be discontinued. | 3 | 3 | admit | 8 |
| SuperCorrect | SUPERCORRECT: ADVANCING SMALL LLM REASONING WITH THOUGHT TEMPLATE DISTILLATION AND SELF-CORRECTION | Yang, Ling; Yu, Zhaochen; Zhang, Tianjun; Xu, Minkai; Gonzalez, Joseph E.; Cui, Bin et al. | 2024 | ICLR 2025 | 2410.09008 | https://github.com/YangLing0818/SuperCorrect-llm | 90 | 2025-03-23 | none listed | yes (code, data, models per abstract) | teacher thought-templates plus cross-model DPO teach 7B student self-correction; beats DeepSeekMath-7B by 7.8/5.3 percent | 4 | 3 | admit | 4 |
| SynCode | SynCode: LLM Generation with Grammar Augmentation | Ugare et al. | 2024 | arXiv preprint | 2403.01632 | https://github.com/structuredllm/syncode | 339 | 2026-01-19 | MIT | yes: SynCode library | Sound/complete CFG decoding; 100% JSON-schema validity on Gemma2-2B | 1 | 3 | admit | 1 |
| SynthIE | Exploiting Asymmetry for Synthetic Training Data Generation: SynthIE and the Case of Information Extraction | Martin Josifoski, Marija Sakota, Maxime Peyrard, Robert West | 2023 | EMNLP 2023 | 2303.04132 | https://github.com/epfl-dlab/SynthIE | 63 | unknown | MIT | yes (code + 1.8M-point synthetic data + 220M/770M models) | Generates 1.8M synthetic text-from-triples points with an LLM; small fine-tunes beat prior SOTA by +57 micro-F1 | 2 | 3 | admit | 6 |
| Synthetic-Hurts | When Synthetic Data Hurts: On Catastrophic Forgetting in Skill Retrieval for LLM Agents | Syed Shariyar Murtaza; Yifan Nie; Utkarsh Soni; Eugene Wen; Arvid Frydenlund | 2026 | EMNLP 2026 Industry track | 2609.10750 |  |  |  | unknown | unknown | Synthetic retrieval fine-tuning causes forgetting at 0.6B; embedding-anchor reg/LwF/EWC/L2 recover OOD and gain +13.98% in-distribution | 3 | 3 | admit | 3 |
| Text2KGBench | Text2KGBench: A Benchmark for Ontology-Driven Knowledge Graph Generation from Text | Nandana Mihindukulasooriya, Sanju Tiwari, Carlos F. Enguix, Kusum Lata | 2023 | ISWC 2023 | 2308.02357 | https://github.com/cenguix/Text2KGBench | unknown | unknown | unknown | yes (10+19 ontologies, ~18k sentences, metric code, Vicuna/Alpaca baselines) | Ontology-conditioned fact extraction eval: P/R/F1 + ontology conformance + subject/relation/object hallucination | 1 | 3 | admit | 6,8 |
| TinyAgent | TinyAgent: Function Calling at the Edge | Erdogan et al. | 2024 | EMNLP 2024 demo | 2409.00608 | https://github.com/SqueezeAILab/TinyAgent | 498 | 2024-09-04 | MIT | yes: 1.1B/7B models + dataset | Narrow-task SFT takes 1.1B 12.7%->80% success, beating GPT-4-Turbo | 1 | 3 | admit | 1 |
| TinyZero | code artefact: minimal R1-Zero reproduction | Pan, Jiayi et al. (community) | 2025 | n/a (code) | n/a | https://github.com/Jiayi-Pan/TinyZero | 13236 | 2026-02-27 | Apache-2.0 | yes (code) | verifiable-reward RL on 3B-scale models for a counting task; canonical tiny RL starter | 4 | 3 | admit | 2,4,7 |
| ToolACE | ToolACE: Winning the Points of LLM Function Calling | Liu et al. | 2024 | ICLR 2025 | 2409.00920 | none verified | — | — | — | yes: model + data subset (HF Team-ACE) | API self-evolution + complexity-guided dialogs + dual verification; LoRA r16 | 1 | 3 | admit | 1 |
| ToolLLM | ToolLLM: Facilitating Large Language Models to Master 16000+ Real-world APIs | Qin et al. | 2023 | arXiv preprint | 2307.16789 | none verified | — | — | — | yes: ToolBench data (reported in paper) | DFSDT multi-agent data pipeline + ToolBench 16k-API benchmark | 1 | 3 | admit | 1 |
| Tulu3 | Tulu 3: Pushing Frontiers in Open Language Model Post-Training | Lambert et al. | 2024 | arXiv preprint (cs.CL) | 2411.15124 | https://github.com/allenai/open-instruct | 3862 | 2026-09-12 | Apache-2.0 (code); stage models under Llama3.1 license | yes (SFT/DPO/RLVR checkpoints, datasets, open-instruct code) | Fully open SFT + length-normalized DPO + RLVR (verifiable-reward RL) pipeline; decontaminated evals; recipe SmolTulu replicates | 4 | 3 | admit | 2,7 |
| USM | Universal Information Extraction as Unified Semantic Matching | Jie Lou, Yaojie Lu, Dai Dai, Wei Jia, Hongyu Lin, Xianpei Han, Le Sun, Hua Wu | 2023 | AAAI 2023 | 2301.03282 |  |  | unknown | unknown | unknown | Three directed token-linking ops replace generation; 356M model beats UIE-large by 5.11 few-shot | 1 | 3 | admit | 6 |
| UniversalNER | UniversalNER: Targeted Distillation from Large Language Models for Open Named Entity Recognition | Wenxuan Zhou, Sheng Zhang, Yu Gu, Muhao Chen, Hoifung Poon | 2024 | ICLR 2024 | 2308.03279 | https://github.com/universal-ner/universal-ner | 375 | unknown | MIT (code); CC-BY-NC-4.0 (HF models/data) | yes (recipe + Pile-NER-type data + UniNER-7B/13B on HF) | Distills ChatGPT NER annotations on Pile passages into 7B/13B students; beats ChatGPT by 7-9 F1 | 1 | 3 | admit | 6 |
| Verifier-Flaws | SCALING FLAWS OF VERIFIER-GUIDED SEARCH IN MATHEMATICAL REASONING | Yu, Fei; Li, Yingru; Wang, Benyou | 2025 | arXiv preprint (venue not verified) | 2502.00271 |  |  |  |  | unknown | imperfect verifiers misrank and prune all valid paths at scale; repeated sampling overtakes verifier search; holds at 7B | 4 | 3 | admit | 4 |
| WebIE | WEBIE: Faithful and Robust Information Extraction on the Web | Chenxi Whitehouse, Clara Vania, Alham Fikri Aji, Christos Christodoulopoulos, Andrea Pierleoni | 2023 | ACL 2023 | 2305.14293 | https://github.com/amazon-science/webie | 8 | 2023-07-26 | NOASSERTION (repo text: CC BY-NC-4.0) | yes (annotations + C4 reconstruction scripts) | C4-based generative IE with negatives and ~21K crowdsourced triples + 4-language mWebIE; entity-linking aux improves faithfulness | 2 | 3 | admit | 6 |
| WebIE | WebIE: Faithful and Robust Information Extraction on the Web | Chenxi Whitehouse, Clara Vania, Alham Fikri Aji, Christos Christodoulopoulos, Andrea Pierleoni | 2023 | ACL 2023 | 10.18653/v1/2023.acl-long.428 | https://github.com/amazon-science/webie | 8 | 2023-07-26 | CC-BY-NC-4.0 | yes: annotations, preprocessing scripts | 1.6M-sentence web closed-IE set WITH negatives; REBEL-only models score 0pct on negatives; entity-linking auxiliary head best for faithfulness. | 1 | 3 | admit | 8 |
| WizardLM (Evol-Instruct) | WizardLM: Empowering large pre-trained language models to follow complex instructions | Can Xu, Qingfeng Sun, Kai Zheng, Xiubo Geng, Pu Zhao, Jiazhan Feng, Chongyang Tao, Qingwei Lin, Daxin Jiang | 2023 | ICLR 2024 | 2304.12244 | https://github.com/nlpxucan/WizardLM | 9482 | 2025-06-07 | None (no license file) | Data: HF WizardLMTeam/WizardLM_evol_instruct_70k and V2 196k | Evolves seed instructions in-depth/in-breadth then mixes all levels for SFT. | 2 | 3 | admit | 2 |
| rsLoRA | A Rank Stabilization Scaling Factor for Fine-Tuning with LoRA | Damjan Kalajdzievski | 2023 | not venue-checked (arXiv abs excerpt) | 2312.03732 | unknown (HF blog by author) | unverified | unverified | unverified | unknown | Standard alpha/r scaling collapses gradients as rank grows; alpha/sqrt(r) stabilizes and unlocks gains from r up to 2048 on Llama 2 + OpenOrca. | 5 | 3 | admit | 5 |
| xLAM | xLAM: A Family of Large Action Models to Empower AI Agent Systems | Zhang et al. | 2024 | arXiv preprint | 2409.03215 | none verified | — | — | — | yes: models + 60k dataset (reported in paper) | SFT+DPO function-calling family incl. 1B model; data reused by Hammer | 1 | 3 | admit | 1 |
| xRAG | xRAG: Extreme Context Compression for Retrieval-augmented Generation with One Token | Xin Cheng; Xun Wang; Xingxing Zhang; Tao Ge; Si-Qing Chen; Furu Wei; Huishuai Zhang; Dongyan Zhao | 2024 | NeurIPS 2024 | 2405.13792 |  |  | none confirmed | not recorded (merge column shift) | unknown | Two-layer projector maps frozen dense-retrieval embedding to one token for a frozen LLM; +10% avg, 3.53x fewer FLOPs. | 6 | 3 | admit | 9 |
| API-Bank | API-Bank: A Comprehensive Benchmark for Tool-Augmented LLMs | Li et al. | 2023 | arXiv preprint | 2304.08244 | none verified | — | — | — | yes: benchmark data (reported in paper) | 73-API executable dialogue benchmark used by Granite/Hammer for generalisation | 1 | 2 | admit | 1 |
| APO-hinge-zero | Enhancing Small LLM Alignment through Margin-Based Objective Modifications under Resource Constraints | Yao et al. | 2025 | arXiv preprint (cs.CL) | 2508.08466 | n/a | n/a | n/a | n/a (method paper, small-scale study) | no released artefact (study only) | Hinge-margin APO-zero variant for 0.5B-scale: zero gradient on easy pairs (hard-example mining), best AlpacaEval WR 36.02 / LC 17.07 | 4 | 2 | admit | 7 |
| AdaLoRA | AdaLoRA: Adaptive Budget Allocation for Parameter-Efficient Fine-Tuning | Qingru Zhang, Minshuo Chen, Alexander Bukharin, Nikos Karampatziakis, Pengcheng He, Yu Cheng, Weizhu Chen, Tuo Zhao | 2023 | ICLR 2023 | 2303.10512 | https://github.com/QingruZhang/AdaLoRA | 395 | 2023-06-01T18:56:18Z | MIT | code | Allocates rank budget by importance across matrices with SVD parametrization + cubic schedule; biggest wins at low budgets. | 5 | 2 | admit | 5 |
| AlpaGasus | AlpaGasus: Training A Better Alpaca with Fewer Data | Lichang Chen, Shiyang Li, Jun Yan, Hai Wang, Kalpa Gunaratna, Vikas Yadav, Zheng Tang, Vijay Srinivasan, Tianyi Zhou, Heng Huang, Hongxia Jin | 2023 | arXiv preprint (venue unverified) | 2307.08701 | https://github.com/Lichang-Chen/AlpaGasus (author repo; unofficial gpt4life/alpagasus has 94 stars) | 25 | 2024-07-26 | None (no license file) | 9K filtered subset described in paper | ChatGPT-judge filters 52K Alpaca to 9K; trains 7B/13B faster and better. | 2 | 2 | admit | 2 |
| Atlas | Atlas: Few-shot Learning with Retrieval Augmented Language Models | Izacard; Lewis; Lomeli; Hosseini; Petroni; Schick; Dwivedi-Yu; Joulin; Riedel; Grave | 2022 | JMLR 2023 (arXiv Aug 2022) | 2208.03299 | https://github.com/facebookresearch/atlas | 563 | 2026-07-02T03:27:01Z | NOASSERTION (no machine-readable license) | code (repo) | Contriever plus FiD jointly pre-trained with periodic index refresh and query-side fine-tuning; 64-shot NQ beats a 540B model with 50x fewer parameters. | 3 | 2 | admit | 10 |
| BERT-anisotropy | On the Sentence Embeddings from Pre-trained Language Models | Bohan Li; Hao Zhou; Junxian He; Mingxuan Wang; Yiming Yang; Lei Li | 2020 | arXiv preprint | 2011.05864 |  |  |  | unknown | unknown | Untuned contextual embeddings live in an anisotropic cone; flow-based isotropy transform restores STS | 3 | 2 | admit | 3 |
| ChatIE | ChatIE: Zero-Shot Information Extraction via Chatting with ChatGPT | Xiang Wei, Xingyu Cui, Ning Cheng, Xiaobin Wang, Xin Zhang, Shen Huang, Pengjun Xie, Jinan Xu, Yufeng Chen, Meishan Zhang, Yong Jiang, Wenjuan Han | 2023 | preprint (v2 May 2024) | 2302.10205 |  |  | unknown | unknown | unknown | Two-stage multi-turn QA decomposition of RE/NER/EE; beats some full-shot models (e.g. NYT11-HRL) | 1 | 2 | admit | 6 |
| Contriever | Unsupervised Dense Information Retrieval with Contrastive Learning | Izacard; Caron; Hosseini; Riedel; Bojanowski; Joulin; Grave | 2021 | TMLR 2022 (arXiv Dec 2021) | 2112.09118 | https://github.com/facebookresearch/contriever | 779 | 2023-04-07T10:14:11Z | NOASSERTION (no machine-readable license) | code plus models (repo) | MoCo-style contrastive pre-training with cropping-based positives yields an unsupervised dense retriever competitive with BM25 and a strong Atlas/Self-RAG starting point. | 3 | 2 | admit | 10 |
| CorpusBrain | CorpusBrain: Pre-train a Generative Retrieval Model for Knowledge-Intensive Language Tasks | Chen; Zhang; Guo; Liu; Fan; Cheng | 2022 | CIKM 2022 | 2208.07652 | https://github.com/ict-bigdatalab/CorpusBrain | 34 | 2022-08-31T08:59:19Z | Apache-2.0 | code (repo) | Generative-retrieval pre-training with inner-sentence-selection, lead-paragraph-selection and hyperlink-identifier-prediction tasks, then single-step generative fine-tuning per KILT task. | 3 | 2 | admit | 10 |
| CorpusBrain++ | CorpusBrain++: A Continual Generative Pre-Training Framework for Knowledge-Intensive Language Tasks | Guo; Zhou; Zhang; Chen; de Rijke; Fan; Cheng | 2024 | arXiv preprint | 2402.16767 | n/a | n/a | n/a | n/a | paper only | Pre-trained CorpusBrain catastrophically forgets on the new KILT++ continual benchmark; rehearsal-plus-regularization continual generative pre-training restores it. | 3 | 2 | admit | 10 |
| DEITA (What Makes Good Data) | What Makes Good Data for Alignment? A Comprehensive Study of Automatic Data Selection in Instruction Tuning (DEITA) | Wei Liu, Weihao Zeng, Keqing He, Yong Jiang, Junxian He | 2023 | arXiv preprint (venue unverified) | 2312.15685 | https://github.com/hkust-nlp/deita (linked in paper footnote) | 602 | 2024-12-09 | Apache-2.0 | Code + selected subsets per paper | Scores complexity/quality/diversity (Evol-Complexity/Evol-Quality + embeddings) and selects small high-performing subsets. | 2 | 2 | admit | 2 |
| DPO | DIRECT PREFERENCE OPTIMIZATION: YOUR LANGUAGE MODEL IS SECRETLY A REWARD MODEL | Rafailov, Rafael; Sharma, Archit; Mitchell, Eric; Ermon, Stefano; Manning, Christopher D.; Finn, Chelsea et al. | 2023 | arXiv preprint (venue not verified) | 2305.18290 |  |  |  |  | unknown | solves RLHF with a classification loss, no reward model or RL loop; stable and cheap | 4 | 2 | admit | 4 |
| DPR | Dense Passage Retrieval for Open-Domain Question Answering | Karpukhin; Oguz; Min; Lewis; Wu; Edunov; Chen; Yih | 2020 | EMNLP 2020 | 2004.04906 | https://github.com/facebookresearch/DPR | 1871 | 2023-04-06T07:36:18Z | NOASSERTION (no machine-readable license) | code plus data (repo) | Dual-encoder trained with one BM25 hard negative plus in-batch negatives; +9-19 point top-20 gains over BM25 and the initializer for RAG joint fine-tuning. | 3 | 2 | admit | 10 |
| DREEAM | DREEAM: Guiding Attention with Evidence for Improving Document-Level Relation Extraction | Youmi Ma, An Wang, Naoaki Okazaki | 2023 | EACL 2023 | 2302.08675 | https://github.com/YoumiMa/dreeam | unknown | unknown | unknown | yes (code, per repo) | Supervises transformer attention with sentence-evidence distributions (zero extra parameters) + ER self-training on distant data | 1 | 2 | admit | 6 |
| DSI-QG | Bridging the Gap Between Indexing and Retrieval for Differentiable Search Index with Query Generation | Zhuang; Ren; Shou; Pei; Gong; Zuccon; Jiang | 2022 | Gen-IR @ SIGIR 2023 | 2206.10128 | https://github.com/ArvinZhuang/DSI-QG | 129 | 2023-07-09T05:23:53Z | MIT | code (repo) | Diagnoses DSI train-serve mismatch (long documents indexed, short queries retrieved) and fixes it by indexing cross-encoder-filtered generated queries instead of document text. | 3 | 2 | admit | 10 |
| Data Pruning Scales | Beyond neural scaling laws: beating power law scaling via data pruning | Ben Sorscher, Robert Geirhos, Shashank Shekhar, Surya Ganguli, Ari S. Morcos | 2022 | arXiv preprint (venue unverified) | 2206.14486 | none verified | unverified | unverified | unverified | None (vision study) | Prototype-based pruning beats power-law data scaling on CIFAR/ImageNet/SVHN; only scaling-law-shaped pruning evidence found. | 2 | 2 | admit | 2 |
| Deduplicating Training Data | Deduplicating Training Data Makes Language Models Better | Katherine Lee, Daphne Ippolito, Andrew Nystrom, Chiyuan Zhang, Douglas Eck, Chris Callison-Burch, Nicholas Carlini | 2021 | arXiv preprint (venue unverified) | 2107.06499 | none verified | unverified | unverified | unverified | Method (MinHash + suffix-array exact-substring) described in paper | Near + exact dedup of C4/RealNews/LM1B/Wiki40B improves perplexity and cuts memorization. | 2 | 2 | admit | 2 |
| DistiLLM-2 | DISTILLM-2: A CONTRASTIVE APPROACH BOOSTS THE DISTILLATION OF LLMS | Ko, Jongwoo; Chen, Tianyi; Kim, Sungnyun; Ding, Tianyu; Liang, Luming; Zharkov, Ilya et al. | 2025 | ICML 2025 Spotlight | 2503.07067 |  |  |  |  | unknown | contrastive distillation: raise likelihood of teacher responses while lowering student ones; covers instruction-following, code, preference alignment | 4 | 2 | admit | 4 |
| DoRA | DoRA: Weight-Decomposed Low-Rank Adaptation | Shih-Yang Liu, Chien-Yi Wang, Hongxu Yin, Pavlo Molchanov, Yu-Chiang Frank Wang, Kwang-Ting Cheng, Min-Hung Chen | 2024 | ICML 2024 (PMLR v235; Oral per abs comments) | 2402.09353 | https://github.com/NVlabs/DoRA | 997 | 2026-03-24T09:13:24Z | NOASSERTION | code | Decomposes weights into magnitude + direction, LoRA on direction; mimics FT learning pattern and beats LoRA on LLaMA/LLaVA/VL-BART. | 5 | 2 | admit | 5 |
| DoReMi | DoReMi: Optimizing Data Mixtures Speeds Up Language Model Pretraining | Sang Michael Xie, Hieu Pham, Xuanyi Dong, Nan Du, Hanxiao Liu, Yifeng Lu, Percy Liang, Quoc V. Le, Tengyu Ma, Adams Wei Yu | 2023 | arXiv preprint (venue unverified) | 2305.10429 | https://github.com/sangmichaelxie/doremi | 359 | 2023-12-26 | MIT | Code released | 280M proxy + group-DRO finds domain weights; 8B Pile training speeds up 2.6x. | 2 | 2 | admit | 2 |
| DocRED | DocRED: A Large-Scale Document-Level Relation Extraction Dataset | Yuan Yao, Deming Ye, Peng Li, Xu Han, Yankai Lin, Zhenghao Liu, Zhiyuan Liu, Lixin Huang, Jie Zhou, Maosong Sun | 2019 | ACL 2019 | 1906.06127 |  |  | unknown | unknown | unknown | 132k-entity human-annotated document-level RE from Wikipedia/Wikidata plus distant supervision | 2 | 2 | admit | 6 |
| EWC | Overcoming catastrophic forgetting in neural networks | James Kirkpatrick; Razvan Pascanu; Neil Rabinowitz; Joel Veness; Guillaume Desjardins; Andrei A. Rusu; Kieran Milan; John Quan; Tiago Ramalho; Agnieszka Grabska-Barwinska; Demis Hassabis; Claudia Clopath; Dharshan Kumaran; Raia Hadsell | 2016 | PNAS | 1612.00796 |  |  |  | unknown | no | Fisher-weighted anchor to old-task weights enables sequential task learning | 3 | 2 | admit | 3 |
| FLARE | Active Retrieval Augmented Generation | Jiang; Xu; Gao; Sun; Liu; Dwivedi-Yu; Yang; Callan; Neubig | 2023 | EMNLP 2023 | 2305.06983 | https://github.com/jzbjyb/FLARE | 668 | 2023-11-20T08:25:17Z | MIT | code plus data (repo) | Forward-looking active retrieval: draft the next sentence, use it as the retrieval query, and regenerate only when low-confidence tokens appear; best or competitive on four long-form tasks. | 6 | 2 | admit | 10 |
| FLASK | FLASK: Fine-grained Language Model Evaluation based on Alignment Skill Sets | Seonghyeon Ye et al. (KAIST) | 2024 | ICLR 2024 Spotlight | 2307.10928 | https://github.com/kaistAI/FLASK | 218 | 2023-12-24 |  | yes: code, skill-annotated eval set | 12-skill instance-wise rubric eval; fine-grained scoring raises human-model correlation and robustness to verbosity gaming. | 6 | 2 | admit | 8 |
| FiD | Leveraging Passage Retrieval with Generative Models for Open Domain Question Answering | Izacard; Grave | 2020 | EACL 2021 | 2007.01282 | https://github.com/facebookresearch/FiD | 594 | 2023-10-04T21:23:33Z | NOASSERTION (no machine-readable license) | code (repo) | Fusion-in-Decoder encodes each retrieved passage independently and fuses evidence in the decoder; accuracy keeps improving to ~100 passages. | 3,6 | 2 | admit | 10 |
| FineWeb | The FineWeb Datasets: Decanting the Web for the Finest Text Data at Scale | Guilherme Penedo, Hynek Kydlicek, Loubna Ben Allal, Anton Lozhkov, Margaret Mitchell, Colin Raffel, Leandro Von Werra, Thomas Wolf (et al.) | 2024 | arXiv preprint (venue unverified) | 2406.17557 | https://github.com/huggingface/datatrove (pipeline tooling used by the paper) | 3328 | 2026-08-13 | Apache-2.0 | Data: HF HuggingFaceFW/fineweb (15T tokens, 96 CC snapshots) | Fully documented dedup/filter pipeline (MinHash, C4-style rules, classifiers) with ablations. | 2 | 2 | admit | 2 |
| FireAct | FireAct: Toward Language Agent Fine-tuning | Chen et al. | 2023 | arXiv preprint | 2310.05915 | none verified | — | — | — | no (uses public benchmarks) | ReAct-trajectory fine-tuning: small models beat prompted large ones | 1 | 2 | admit | 1 |
| Functionary | Functionary (MeetKai function-calling SFT codebase + Small/Medium v2.x models) | MeetKai team | 2024 | none (code artefact) | none | https://github.com/MeetKai/functionary | 1595 | 2026-06-30 | MIT | yes: training code + models | Open SFT recipe for chat-with-tools at small scale incl. Small models | 1 | 2 | admit | 1,6 |
| GAR | Generation-Augmented Retrieval for Open-domain Question Answering | Mao; He; Liu; Shen; Gao; Han; Chen | 2020 | ACL-IJCNLP 2021 | 2009.08553 | n/a | n/a | n/a | n/a | paper only | Reverse direction: a generator expands the query with heuristically discovered contexts and BM25 over expansions matches or beats DPR; fusing diverse generations helps. | 3 | 2 | admit | 10 |
| GLiDRE | GLiDRE: Generalist Lightweight model for Document-level Relation Extraction | Robin Armingaud, Romaric Besancon | 2025 | preprint (submitted ARR Oct) | 2508.00757 |  |  | unknown | unknown | unknown | GLiNER-style bi-encoder extended to document-level relation extraction | 1 | 2 | admit | 6 |
| GLiNER2 | GLiNER2: An Efficient Multi-Task Information Extraction System with Schema-Driven Interface | Urchade Zaratiana, Gil Pasternak, Oliver Boyd, George Hurn-Maloney, Ash Lewis | 2025 | preprint | 2507.18546 |  |  | unknown | unknown | unknown | Multi-task IE (NER+RE+hierarchical) behind a schema-driven interface | 1 | 2 | admit | 6 |
| GSM-IC | Large Language Models Can Be Easily Distracted by Irrelevant Context | Freda Shi; Xinyun Chen; Kanishka Misra; Nathan Scales; David Dohan; Ed H. Chi; Nathanael Scharli; Denny Zhou | 2023 | ICML 2023 | 2302.00093 |  |  | none confirmed | not recorded (merge column shift) | unknown | Measures consumer accuracy collapse under irrelevant context; self-consistency and distractor-aware exemplars mitigate. | 6 | 2 | admit | 9 |
| GaLore | GaLore: Memory-Efficient LLM Training by Gradient Low-Rank Projection | Jiawei Zhao, Zhenyu Zhang, Beidi Chen, Zhangyang Wang, Anima Anandkumar, Yuandong Tian | 2024 | ICML 2024 (PMLR v235) | 2403.03507 | https://github.com/jiaweizzhao/GaLore | 1701 | 2024-10-28T18:01:54Z | Apache-2.0 | code | Full-parameter learning with low-rank gradient projections; 65.5% optimizer memory cut; Llama 7B pre-train on 24GB without ReLoRA-style warmup. | 4 | 2 | admit | 5 |
| GenIR-survey-Kuo | A Survey of Generative Information Retrieval | Kuo; Chiu; Lin; Wu; Huang; Chen | 2024 | arXiv preprint | 2406.01197 | https://github.com/MiuLab/GenIR-Survey (paper-collection repo named in paper) | 6 | 2024-03-14T03:46:38Z | None detected | code-adjacent (paper collection) | Taxonomy of DocID strategies (single-token, sequential, text-based) and indexing-versus-retrieval training, with future directions on learnable DocIDs and multi-task GR. | 3 | 2 | admit | 10 |
| GenIR-survey-Li | From Matching to Generation: A Survey on Generative Information Retrieval | Li; Jin; Zhou; Zhang; Zhang; Zhu; Dou | 2024 | TOIS 2025 (arXiv Apr 2024, v4 Mar 2025) | 2404.14851 | https://github.com/RUC-NLPIR/GenIR-Survey | 210 | 2025-04-05T09:11:44Z | MIT | paper collection (repo) | Two-branch survey: generative document retrieval plus reliable response generation (memorization, augmentation, attribution), with incremental-learning and evaluation sections. | 3,6 | 2 | admit | 10 |
| Generative-Agents | Generative Agents: Interactive Simulacra of Human Behavior | Joon Sung Park; Joseph C. O'Brien; Carrie J. Cai; Meredith Ringel Morris; Percy Liang; Michael S. Bernstein | 2023 | UIST 2023 | 2304.03442 | https://github.com/joonspk-research/generative_agents | 22094 | 2024-08-05 | Apache-2.0 | code released | Memory stream with relevance-recency-importance retrieval plus reflection synthesis; ablations and failure taxonomy (retrieval failure, confabulation). | 6 | 2 | admit | 9 |
| Generative-IE-survey | Large Language Models for Generative Information Extraction: A Survey | Derong Xu et al. | 2024 | Frontiers of Computer Science | 2312.17617 |  |  |  |  | yes: LLM4IE repo linked from paper (URL not recorded) | Technique taxonomy (augmentation, prompts, constrained decoding, SFT) with empirical finding that SFT dominates few/zero-shot and universal models win strict relation scores. | 1 | 2 | admit | 8 |
| HELM | Holistic Evaluation of Language Models | Percy Liang et al. (CRFM, many authors) | 2023 | TMLR 2023 | 2211.09110 | https://github.com/stanford-crfm/helm | 2907 | 2026-09-01 | Apache-2.0 | yes: code, scenarios, raw completions | Multi-metric standard (accuracy, calibration, robustness, fairness, toxicity, efficiency) over 16 core scenarios; reporting template for joint-capability models. | 6 | 2 | admit | 8 |
| In-Context RALM | In-Context Retrieval-Augmented Language Models | Ram; Levine; Dalmedigos; Muhlgay; Shashua; Leyton-Brown; Shoham | 2023 | TACL 2023 | 2302.00083 | n/a | n/a | n/a | n/a | paper only | Prepending retrieved passages with no LM changes gives gains equivalent to 2-3x parameters across 110M-66B models; ranking the retriever for the RALM objective adds more. | 3,6 | 2 | admit | 10 |
| IncDSI | IncDSI: Incrementally Updatable Document Retrieval | Kishore; Wan; Lovelace; Artzi; Weinberger | 2023 | ICML 2023 | 2307.10323 | https://github.com/varshakishore/IncDSI | 10 | 2023-09-10T03:52:38Z | MIT | code (repo) | New documents indexed in 20-50 ms by constrained optimization over the added docid vector only, matching full-retrain retrieval quality without touching the encoder. | 3 | 2 | admit | 10 |
| InstructUIE | InstructUIE: Multi-task Instruction Tuning for Unified Information Extraction | Xiao Wang, Weikang Zhou, Can Zu, Han Xia, Tianze Chen, Yuansen Zhang, Rui Zheng, Junjie Ye, Qi Zhang, Tao Gui et al. | 2023 | preprint | 2304.08085 |  |  | unknown | unknown | unknown | IE INSTRUCTIONS (32 datasets) instruction-tuned FlanT5-11B; matches BERT supervised, beats GPT-3.5 zero-shot | 1 | 2 | admit | 6 |
| Instruction Mining | Instruction Mining: Instruction Data Selection for Tuning Large Language Models | Yihan Cao, Yanbin Kang, Chi Wang, Lichao Sun | 2023 | arXiv preprint (venue unverified) | 2307.06290 | none found | unverified | unverified | unverified | Selection rule described in paper | Lightweight metric rule blending quality/diversity for picking small high-performing subsets. | 2 | 2 | admit | 2 |
| KGGen | KGGen: Extracting Knowledge Graphs from Plain Text with Language Models | Belinda Mo, Kyssen Yu, Joshua Kazdan, Joan Cabezas, Proud Mpala, Lisa Yu, Chris Cundy, Charilaos Kanatsoulis, Sanmi Koyejo | 2025 | preprint | 2502.09956 |  |  | unknown | unknown | unknown | LLM pipeline for open KG extraction from plain text | 1 | 2 | admit | 6 |
| KnowCoder-X | KnowCoder-X: Boosting Multilingual Information Extraction via Code | Yuxin Zuo, Wenxuan Jiang, Wenxuan Liu, Zixuan Li, Long Bai, Hanbin Wang, Yutao Zeng, Xiaolong Jin, Jiafeng Guo, Xueqi Cheng | 2024 | preprint | 2411.04794 |  |  | unknown | CC-BY-NC-SA-4.0 (v2 license tag) | yes (code + dataset claimed in abstract) | IE cross-lingual alignment phase + code schemas; 64 benchmarks, +30% over ChatGPT cross-lingual, 20 African languages | 1 | 2 | admit | 6 |
| LAMOL | LAMOL: LAnguage MOdeling for Lifelong Language Learning | Fan-Keng Sun; Cheng-Hao Ho; Hung-Yi Lee | 2019 | arXiv preprint | 1909.03329 |  |  |  | unknown | training code released | LM head generates pseudo-samples of old tasks as replay; within 2-3% of multitask upper bound | 3 | 2 | admit | 3 |
| LESS | LESS: Selecting Influential Data for Targeted Instruction Tuning | Mengzhou Xia, Sadhika Malladi, Suchin Gururangan, Sanjeev Arora, Danqi Chen | 2024 | arXiv preprint (venue unverified) | 2402.04333 | https://github.com/princeton-nlp/LESS | 532 | 2024-10-20 | MIT | Code released | Gradient datastore (LoRA warmup) + influence picks 5% subsets beating full data on MMLU/TyDiQA/BBH. | 2 | 2 | admit | 2 |
| Length-Collapse | Length-Induced Embedding Collapse in PLM-based Models | Yuqi Zhou; Sunhao Dai; Zhanshuo Cao; Xiao Zhang; Jun Xu | 2024 | arXiv preprint | 2410.24200 |  |  |  | unknown | unknown | Long-text embeddings cluster via attention low-pass filtering; TempScale temperature mitigation | 3 | 2 | admit | 3 |
| LoRA-FA | LoRA-FA: Memory-efficient Low-rank Adaptation for Large Language Models Fine-tuning (v3 retitled Efficient and Effective Low Rank Representation Fine-tuning) | Longteng Zhang, Lin Zhang, Shaohuai Shi, Xiaowen Chu, Bo Li | 2023 | not venue-checked (arXiv abs excerpt; v3 May 2026) | 2308.03303 | unverified | unverified | unverified | unverified | code (per paper) | Freezes A, trains B only: removes A-activation memory (1.4x vs LoRA), matches LoRA/FT; poor on Math/Code noted by LoRA-Null authors. | 5 | 2 | admit | 5 |
| LoftQ | LoftQ: LoRA-Fine-Tuning-Aware Quantization for Large Language Models | Yixiao Li, Yifan Yu, Chen Liang, Pengcheng He, Nikos Karampatziakis, Weizhu Chen, Tuo Zhao | 2023 | ICLR 2024 (Oral) | 2310.08659 | https://github.com/yxli2123/LoftQ | 235 | 2024-06-11T16:24:25Z | MIT | code | Jointly optimizes quantized Q + LoRA init to close QLoRA gap; converges at 2-bit where QLoRA fails; Llama-2-7B/13B evidence. | 4 | 2 | admit | 5 |
| LwF | Learning without Forgetting | Zhizhong Li; Derek Hoiem | 2016 | arXiv preprint | 1606.09282 |  |  |  | unknown | no | Self-distillation against old-task outputs using only new-task data | 3 | 2 | admit | 3 |
| MMTEB | MMTEB: Massive Multilingual Text Embedding Benchmark | Kenneth Enevoldsen et al. (community) | 2025 | arXiv preprint | 2502.13595 | https://github.com/embeddings-benchmark/mteb |  |  | Apache-2.0 | yes: via MTEB repo, 500+ tasks over 250+ languages | Community expansion of MTEB: 500+ quality-controlled tasks incl. instruction-following and long-document retrieval. | 3 | 2 | admit | 8 |
| MemGPT | MemGPT: Towards LLMs as Operating Systems | Charles Packer; Sarah Wooders; Kevin Lin; Vivian Fang; Shishir G. Patil; Ion Stoica; Joseph E. Gonzalez | 2023 | preprint | 2310.08560 | https://github.com/letta-ai/letta (successor of cpacker/MemGPT) | 24714 | 2026-09-10 | Apache-2.0 | code released (repo continued as Letta) | OS-style virtual context management: hierarchical memory with function-call paging and heartbeat chaining. | 6 | 2 | admit | 9 |
| MiLoRA | MiLoRA: Harnessing Minor Singular Components for Parameter-Efficient LLM Finetuning | Hanqing Wang, Yixia Li, Shuo Wang, Guanhua Chen, Yun Chen | 2024 | NAACL 2025 | 2406.09044 | https://github.com/sufenlp/MiLoRA (top API hit; officiality unconfirmed) | 23 | 2025-05-31T00:58:31Z | no license declared | code (officiality unconfirmed) | Updates only minor singular components, freezes principal ones; init orthogonal to principal subspace; wins on commonsense/math/instruction/VL. | 5 | 2 | admit | 5 |
| Nemotron-CC | Nemotron-CC: Transforming Common Crawl into a Refined Long-Horizon Pretraining Dataset | Dan Su, Kezhi Kong, Ying Lin, Joseph Jennings, Brandon Norick, Markus Kliegl, Mostofa Patwary, Mohammad Shoeybi, Bryan Catanzaro (et al.) | 2024 | ACL 2025 (OpenAlex DOI 10.18653/v1/2025.acl-long.123) | 2412.02595 | none verified (code) | unverified | unverified | unverified | Data: HF nvidia/Nemotron-CC-v2 (+Math, +Code) | Classifier ensembling + synthetic rephrasing keep 6.3T tokens for 15T-horizon training; +5.6 MMLU over DCLM at 8B/1T. | 2 | 2 | admit | 2 |
| O-LoRA | Orthogonal Subspace Learning for Language Model Continual Learning (O-LoRA) | Xiao Wang, Tianze Chen, Qiming Ge, Han Xia, Rong Bao, Rui Zheng, Qi Zhang, Tao Gui, Xuanjing Huang | 2023 | EMNLP 2023 Findings | 2310.14152 | https://github.com/cmnfriend/O-LoRA | 213 | 2024-07-13T04:49:26Z | MIT | code+data | Sequential tasks in mutually orthogonal LoRA subspaces without replay; +24% over LFPT5; preserves unseen-task generalization. | 3 | 2 | admit | 5 |
| PIVOINE | PIVOINE: Instruction Tuning for Open-world Entity Profiling | Keming Lu, Xiaoman Pan, Kaiqiang Song, Hongming Zhang, Dong Yu, Jianshu Chen | 2023 | Findings of EMNLP 2023 | 10.18653/v1/2023.findings-emnlp.1009 |  |  | unknown | unknown | unknown | Instruction tuning for open-world entity profiling (open-world IE sub-task) | 1 | 2 | admit | 6 |
| PiSSA | PiSSA: Principal Singular Values and Singular Vectors Adaptation of Large Language Models | Fanxu Meng, Zhaohui Wang, Muhan Zhang | 2024 | NeurIPS 2024 | 2404.02948 | https://github.com/MuLabPKU/PiSSA | 430 | 2025-06-30T04:04:33Z | none declared | code | Init A/B from principal SVD components, freeze residual; faster convergence than LoRA across 184M-70B; QPiSSA beats QLoRA 4-bit. | 5 | 2 | admit | 5 |
| QA-LoRA | QA-LoRA: Quantization-Aware Low-Rank Adaptation of Large Language Models | Yuhui Xu, Lingxi Xie, Xiaotao Gu, Xin Chen, Heng Chang, Hengheng Zhang, Zhengsu Chen, Xiaopeng Zhang, Qi Tian | 2023 | ICLR 2024 | 2309.14717 | https://github.com/yuhuixu1993/qa-lora | 146 | 2024-03-13T09:30:53Z | MIT | code | Group-wise quant + adaptation balances degrees of freedom; INT4 fine-tune merges back losslessly, beats QLoRA at 2-4 bit. | 4 | 2 | admit | 5 |
| QLoRA-tool | Internalizing Tool Knowledge in Small Language Models via QLoRA Fine-Tuning | Yuval Shemla; Ayal Yakobe; Tanmay Agarwal; Dhaval Patel; Kaoutar El Maghraoui | 2026 | arXiv preprint | 2605.17774 |  |  |  | unknown | unknown | 4B QLoRA on ~1700 tool-use traces internalizes structured planning; rank 32 best quality, smaller ranks retain more | 1 | 2 | admit | 3 |
| QMSum | QMSum: A New Benchmark for Query-based Multi-domain Meeting Summarization | Ming Zhong; Da Yin; Tao Yu; Ahmad Zaidi; Mutethia Mutuma; Rahul Jha; Ahmed Hassan Awadallah; Asli Celikyilmaz; Yang Liu; Xipeng Qiu; Dragomir Radev | 2021 | NAACL 2021 | 2104.05938 | https://github.com/Yale-LILY/QMSum | 155 | 2023-08-29 | MIT | dataset released | 1808 query-summary pairs over 232 meetings in 3 domains; locate-then-summarize baseline; cross-domain generalization fails. | 6 | 2 | admit | 9 |
| R1-RE | R1-RE: Cross-Domain Relation Extraction with RLVR | Runpeng Dai, Tong Zheng, Run Yang, Kaixian Yu, Hongtu Zhu | 2025 | preprint | 2507.04642 |  |  | unknown | unknown | unknown | RL with verifiable rewards for cross-domain relation extraction | 1 | 2 | admit | 6 |
| RAG | Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks | Lewis; Perez; Piktus; Petroni; Karpukhin; Goyal; Kuettler; Lewis; Yih; Rocktaschel; Riedel; Kiela | 2020 | NeurIPS 2020 | 2005.11401 | n/a | n/a | n/a | n/a | paper only | RAG-Sequence and RAG-Token jointly fine-tune a DPR retriever with a BART generator treating documents as latents; index is hot-swappable. | 3 | 2 | admit | 10 |
| RAG-survey-Gao | Retrieval-Augmented Generation for Large Language Models: A Survey | Gao; Xiong; Gao; Jia; Pan; Bi; Dai; Sun; Wang; Wang | 2023 | arXiv preprint | 2312.10997 | n/a | n/a | n/a | n/a | paper only | Naive, Advanced and Modular RAG paradigms with pre-retrieval, post-retrieval and evaluation taxonomies. | 6,3 | 2 | admit | 10 |
| REBEL | REBEL: Relation Extraction By End-to-end Language generation | Pere-Lluis Huguet Cabot, Roberto Navigli | 2021 | Findings of EMNLP 2021 | 10.18653/v1/2021.findings-emnlp.204 | https://github.com/Babelscape/rebel | 576 | 2023-11-09 | none stated (repo); CC-BY-NC-SA-4.0 (HF checkpoint) | yes (code + BART-based rebel-large on HF) | Seq2seq triplet linearization on BART for 200+ relation types; SOTA on RE/RC benchmarks after few-epoch fine-tunes | 1 | 2 | admit | 6 |
| REDFM | REDFM: a Filtered and Multilingual Relation Extraction Dataset | Pere-Lluis Huguet Cabot, Simone Tedeschi, Axel-Cyrille Ngonga Ngomo, Roberto Navigli | 2023 | ACL 2023 | 2306.09802 | https://github.com/babelscape/rebel | 576 | 2023-11-09 | none stated (repo) | yes (silver+gold multilingual data + mREBEL checkpoints, per paper) | NLI-filtered silver RE data with Triplet Critic; mREBEL extracts typed triplets in 7 languages | 2 | 2 | admit | 6 |
| RIPOR | Scalable and Effective Generative Information Retrieval | Zeng; Luo; Jin; Sarwar; Wei; Zamani | 2023 | arXiv preprint | 2311.09134 | n/a | n/a | n/a | n/a | paper only | Prefix-oriented ranking optimization plus multi-stage distillation makes GR work on large standard benchmarks (MS MARCO, NQ) for the first time. | 3 | 2 | admit | 10 |
| RL-vs-SFT-circuits | Mechanistic origins of catastrophic forgetting: why RL preserves circuits better than SFT? | Jeanmely Rojas Nunez; Viraj Sawant; Nathan Allen; Nomgondalai Amgalanbaatar; Yannis Zongo; Vasu Sharma; Maheep Chaudhary | 2026 | arXiv preprint | 2605.28860 | https://github.com/rl-sft-circuit-research/differential-circuit-vulnerability |  |  | unknown | training code released | Head-level circuit analysis on Qwen2.5-3B: SFT adapts faster but disrupts circuits; RL preserves base circuit | 3 | 2 | admit | 3 |
| RLVR-Implicit | REINFORCEMENT LEARNING WITH VERIFIABLE REWARDS IMPLICITLY INCENTIVIZES CORRECT REASONING IN BASE LLMS | Wen, Xumeng; Liu, Zihan; Zheng, Shun; Ye, Shengyu; Wu, Zhirong; Wang, Yang et al. | 2025 | arXiv preprint (venue not verified) | 2506.14245 |  |  |  |  | unknown | answer-only verifiable rewards still extend the reasoning boundary (CoT-Pass@K) rather than merely sharpening sampling | 4 | 2 | admit | 4 |
| ReAct | ReAct: Synergizing Reasoning and Acting in Language Models | Yao et al. | 2022 | arXiv preprint | 2210.03629 | none found | — | — | — | no | Thought-action-observation prompting scaffold for harness tool loops | 1 | 2 | admit | 1 |
| ReLoRA | ReLoRA: High-Rank Training Through Low-Rank Updates | Vladislav Lialin, Namrata Shivagunde, Sherin Muckatira, Anna Rumshisky | 2023 | ICLR 2024 | 2307.05695 | https://github.com/Guitaricet/relora | 475 | 2024-04-21T20:09:58Z | Apache-2.0 | code | Periodic merge-and-restart with jagged LR + partial optimizer reset turns sequential low-rank updates into high-rank training to 1.3B; needs full-rank warm start. | 5 | 2 | admit | 5 |
| ReMax | REMAX: A SIMPLE, EFFECTIVE, AND EFFICIENT REINFORCEMENT LEARNING METHOD FOR ALIGNING LARGE LANGUAGE MODELS | Li, Ziniu; Xu, Tian; Zhang, Yushun; Lin, Zhihang; Yu, Yang; Sun, Ruoyu et al. | 2023 | arXiv preprint (venue not verified) | 2310.10505 |  |  |  |  | unknown | greedy-baseline REINFORCE with no value model; removes 4-plus PPO hyperparameters; about 46 percent less GPU memory than PPO at 7B | 4 | 2 | admit | 4 |
| Reflexion | Reflexion: Language Agents with Verbal Reinforcement Learning | Noah Shinn; Federico Cassano; Edward Berman; Ashwin Gopinath; Karthik Narasimhan; Shunyu Yao | 2023 | NeurIPS 2023 | 2303.11366 | https://github.com/noahshinn/reflexion | 3264 | 2025-01-14 | MIT | code+demos+logs released | Actor/Evaluator/Self-Reflection loop storing verbal feedback in a small episodic buffer; 91% HumanEval. | 6 | 2 | admit | 9 |
| RegMix | RegMix: Data Mixture as Regression for Language Model Pre-training | Qian Liu, Xiaosen Zheng, Niklas Muennighoff, Guangtao Zeng, Longxu Dou, Tianyu Pang, Jing Jiang, Min Lin | 2024 | ICLR 2025 (per author repo description) | 2407.01492 | https://github.com/sail-sg/regmix | 208 | 2025-02-17 | MIT | Code released | Rank-invariance lets tiny proxies + LightGBM regression predict the best mix (Pile-CC, 1M-token proxies). | 2 | 2 | admit | 2 |
| Rephrasing the Web (WRAP) | Rephrasing the Web: A Recipe for Compute and Data-Efficient Language Modeling | Pratyush Maini, Skyler Seto, He Bai, David Grangier, Yizhe Zhang, Navdeep Jaitly | 2024 | ACL 2024 (OpenAlex DOI 10.18653/v1/2024.acl-long.757) | 2401.16380 | none verified | unverified | unverified | unverified | Method (WRAP) described in paper | Uses an instruction-tuned model to rephrase web docs (Wikipedia/QA styles) and trains jointly on real + synthetic. | 2 | 2 | admit | 2 |
| RexUIE | RexUIE: A Recursive Method with Explicit Schema Instructor for Universal Information Extraction | Chengyuan Liu, Fubang Zhao, Yangyang Kang, Jingyuan Zhang, Xiang Zhou, Changlong Sun, Kun Kuang, Fei Wu | 2023 | Findings of EMNLP 2023 | 2304.14770 |  |  | unknown | unknown | unknown | Recursive token-linking queries extract n-ary schemas (quadruples/quintuples); 3M distant JERE pretrain | 1 | 2 | admit | 6 |
| SAPO | Training Prompt Matters: State-Adaptive Optimization for Robust Fine-Tuning | Wenhang Shi; Yiren Chen; Shuqing Bian; Zhe Zhao; Jinhao Dong; Jiaheng Hu; Pengfei Hu; Wei Lu; Xiaoyong Du | 2026 | arXiv preprint | 2606.01967 |  |  |  | unknown | training code released | Paraphrased training prompts match in-task but differ sharply in forgetting; SAPO selects prompts by pre-learning loss | 3 | 2 | admit | 3 |
| Seal-Tools | Seal-Tools: Self-Instruct Tool Learning Dataset for Agent Tuning and Detailed Benchmark | Wu et al. | 2024 | NLPCC 2024 | 2405.08355 | https://github.com/fairyshine/Seal-Tools | 57 | 2024-11-05 | Apache-2.0 | yes: 4k tools + 14k instances | Self-instruct tool/instance generation with nested calls; Tool/Param F1 eval | 1 | 2 | admit | 1 |
| Selective-Context | Compressing Context to Enhance Inference Efficiency of Large Language Models | Yucheng Li; Bo Dong; Chenghua Lin; Frank Guerin | 2023 | EMNLP 2023 | 2310.06201 | https://github.com/liyucheng09/Selective_Context | 425 | 2024-02-12 | None | code+data released | Self-information filtering of lexical units; 50% context cut at minor quality loss; thresholds are domain-dependent. | 6 | 2 | admit | 9 |
| SemDeDup | SemDeDup: Data-efficient learning at web-scale through semantic deduplication | Amro Abbas, Kushal Tirumala, Daniel Simig, Surya Ganguli, Ari S. Morcos | 2023 | arXiv preprint (venue unverified) | 2303.09540 | https://github.com/facebookresearch/SemDeDup | 158 | 2023-10-01 | NOASSERTION | Code released | K-means on embeddings + intra-cluster pruning keeps ~50% of data at parity (OPT experiments). | 2 | 2 | admit | 2 |
| SimCSE | SimCSE: Simple Contrastive Learning of Sentence Embeddings | Tianyu Gao; Xingcheng Yao; Danqi Chen | 2021 | arXiv preprint | 2104.08821 | https://github.com/princeton-nlp/SimCSE | 3652 | 2024-10-16 | MIT | training code released | Dropout-noise unsupervised contrastive plus NLI entailment/contradiction supervised contrastive recipe | 3 | 2 | admit | 3 |
| SimPO | SIMPO: SIMPLE PREFERENCE OPTIMIZATION WITH A REFERENCE-FREE REWARD | Meng, Yu; Xia, Mengzhou; Chen, Danqi | 2024 | arXiv preprint (venue not verified) | 2405.14734 |  |  |  |  | unknown | average-logprob implicit reward removes the reference model from memory; margin objective | 4 | 2 | admit | 4 |
| ToolAlpaca | ToolAlpaca: Generalized Tool Learning for Language Models with 3000 Simulated Cases | Tang et al. | 2023 | arXiv preprint | 2306.05301 | none verified | — | — | — | yes: 3.9k simulated instances (reported in paper) | 3000-case simulated tool-use SFT showing compact-model gains | 1 | 2 | admit | 1 |
| Toolformer | Toolformer: Language Models Can Teach Themselves to Use Tools | Schick et al. | 2023 | arXiv preprint | 2302.04761 | none found | — | — | — | no: no official release | Self-supervised API-call insertion via execution-filtered sampling | 1 | 2 | admit | 1 |
| Tricks-or-Traps | PART I: TRICKS OR TRAPS? A DEEP DIVE INTO RL FOR LLM REASONING | Liu, Zihe; Liu, Jiashun; He, Yancheng; Wang, Weixun; Liu, Jiaheng; Pan, Ling et al. | 2025 | arXiv preprint (venue not verified) | 2508.08221 |  |  |  |  | unknown | systematic reproduction of RL-for-reasoning techniques in one framework with selection guidelines; vanilla-PPO-loss minimalist combo beats GRPO/DAPO | 4 | 2 | admit | 4 |
| UIE | Unified Structure Generation for Universal Information Extraction | Yaojie Lu, Qing Liu, Dai Dai, Xinyan Xiao, Hongyu Lin, Xianpei Han, Le Sun, Hua Wu | 2022 | ACL 2022 | 10.18653/v1/2022.acl-long.395 |  |  | unknown | unknown | unknown | T5 text-to-structure with structural schema instructor and structured extraction language | 1 | 2 | admit | 6 |
| UltraChat | Enhancing Chat Language Models by Scaling High-quality Instructional Conversations (UltraChat) | Ning Ding, Yulin Chen, Bokai Xu, Yujia Qin, Zhi Zheng, Shengding Hu, Zhiyuan Liu, Maosong Sun, Bowen Zhou | 2023 | EMNLP 2023 (OpenAlex DOI 10.18653/v1/2023.emnlp-main.183) | 2305.14233 | https://github.com/thunlp/UltraChat | 2898 | 2024-03-13 | MIT | Data: HF HuggingFaceH4/ultrachat_200k; 1.5M dialogues per paper | Topic-scaffolded two-agent generation of 1.5M multi-turn dialogues. | 2 | 2 | admit | 2 |
| Ultron | Ultron: An Ultimate Retriever on Corpus with a Model-based Indexer | Zhou; Yao; Dou; Wu; Zhang; Wen | 2022 | arXiv preprint | 2208.09257 | https://github.com/smallporridge/WebUltron (README cites Ultron abs id and calls itself its official repo; also hosts WebUltron follow-up) | 12 | 2023-03-21T15:19:33Z | MIT | code (repo, with caveat above) | Semantically rich URL-plus-title-plus-title docids with a three-stage (general, search-oriented, supervised) training workflow; beats DSI-style baselines on MS MARCO and NQ. | 3 | 2 | admit | 10 |
| Unnatural Instructions | Unnatural Instructions: Tuning Language Models with (Almost) No Human Labor | Or Honovich, Thomas Scialom, Omer Levy, Timo Schick | 2022 | arXiv preprint (venue unverified) | 2212.09689 | https://github.com/orhonovich/unnatural-instructions | 181 | 2023-02-23 | MIT | Dataset released per paper | Expands 15 seed instructions to ~64K examples by paraphrase; core of the minimal-diversity recipe. | 2 | 2 | admit | 2 |
| VeRA | VeRA: Vector-based Random Matrix Adaptation | Dawid J. Kopiczko, Tijmen Blankevoort, Yuki M. Asano | 2023 | ICLR 2024 (per abs comments) | 2310.11454 | unverified (paper site URL redacted; supported in HF peft docs, verified) | unverified | unverified | unverified | code (via HF peft) | Frozen shared random A/B across layers, trains only scaling vectors; 10x fewer params than LoRA at same GLUE/E2E quality. | 5 | 2 | admit | 5 |
| Voyager | Voyager: An Open-Ended Embodied Agent with Large Language Models | Guanzhi Wang; Yuqi Xie; Yunfan Jiang; Ajay Mandlekar; Chaowei Xiao; Yuke Zhu; Linxi Fan; Anima Anandkumar | 2023 | preprint | 2305.16291 | https://github.com/MineDojo/Voyager | 7193 | 2024-04-03 | MIT | code released | Ever-growing library of model-written code skills indexed by description embedding with iterative self-verification. | 6 | 2 | admit | 9 |
| WizardCoder | WizardCoder: Empowering Code Large Language Models with Evol-Instruct | Ziyang Luo, Can Xu, Pu Zhao, Qingfeng Sun, Xiubo Geng, Wenxiang Hu, Chongyang Tao, Jing Ma, Qingwei Lin, Daxin Jiang | 2023 | arXiv preprint (venue unverified) | 2306.08568 | https://github.com/nlpxucan/WizardLM (shared with WizardLM) | 9482 | 2025-06-07 | None (no license file) | Model + evolved code-instruction data per paper | Evol-Instruct applied to a narrow task (code) on a StarCoder base. | 2 | 2 | admit | 2 |
| X-LoRA | X-LoRA: Mixture of Low-Rank Adapter Experts, a Flexible Framework for Large Language Models with Applications in Protein Mechanics and Molecular Design | Eric L. Buehler; Markus J. Buehler | 2024 | arXiv preprint | 2402.07148 | https://github.com/EricLBuehler/xlora | 285 | 2024-08-04 | Apache-2.0 | training code released | Token-level deep layer-wise mixing of frozen pretrained adapters with a hidden-state gate | 3 | 2 | admit | 3 |
| YAYI-UIE | YAYI-UIE: A Chat-Enhanced Instruction Tuning Framework for Universal Information Extraction | Xinglin Xiao, Yijie Wang, Nan Xu, Yuqi Wang, Hanxuan Yang, Minzheng Wang, Yin Luo, Lei Wang, Wenji Mao, Daniel Zeng | 2023 | preprint | 2312.15548 |  |  | unknown | unknown | unknown | Two-step chat-then-IE instruction tuning; largest Chinese IE instruction benchmark; keeps English ability | 1 | 2 | admit | 6 |
| muA | Learning Rate Scaling across LoRA Ranks and Transfer to Full Finetuning | Nan Chen, Soledad Villar, Soufiane Hayou | 2026 | not venue-checked (arXiv abs opened) | 2602.06204 | unknown | unverified | unverified | unverified | unknown | muA theory: optimal LR is rank-invariant under alpha=r^-1 but scales ~1/sqrt(r) under constant alpha; LoRA-tuned LRs transfer to full FT. | 5 | 2 | admit | 5 |
| Eider | Empowering Document-level Relation Extraction with Efficient Evidence Extraction and Inference-stage Fusion | Yiqing Xie, Jiaming Shen, Sha Li, Yuning Mao, Jiawei Han | 2022 | Findings of ACL 2022 | 2106.08657 |  |  | unknown | unknown | unknown | Joint RE + lightweight evidence extractor with heuristic silver labels and inference-stage fusion | 1 | 1 | admit | 6 |
| MR-UIE | MR-UIE: Multi-Perspective Reasoning with Reinforcement Learning for Universal Information Extraction | Zhongqiu Li, Shiquan Wang, Ruiyu Fang, Mengjiao Bao, Zhenhe Wu, Shuangyong Song, Yongxiang Li, Zhongjiang He | 2025 | preprint | 2509.09082 |  |  | unknown | unknown | unknown | RL with multi-perspective reasoning for universal IE | 1 | 1 | admit | 6 |
| mGENRE | Multilingual Autoregressive Entity Linking | Nicola De Cao, Ledell Wu, Kashyap Popat, Mikel Artetxe, Naman Goyal, Mikhail Plekhanov, Luke Zettlemoyer, Nicola Cancedda, Sebastian Riedel, Fabio Petroni | 2021 | preprint (TACL 2022) | 2103.12528 |  |  | unknown | unknown | unknown | Multilingual GENRE resolving mentions in 100+ languages to a multilingual KB | 1 | 1 | admit | 6 |
| AlpacaEval-LC | Length-Controlled AlpacaEval: A Simple Way to Debias Automatic Evaluators | Yann Dubois, Balazs Galambosi, Percy Liang, Tatsunori Hashimoto | 2024 | COLM 2024 | 2404.04475 | https://github.com/tatsu-lab/alpaca_eval | 2014 | 2025-08-09 | Apache-2.0 | yes: code, leaderboard | Abs page and full PDF opened; id-title match verified. | refutes | 3 | refute | 8 |
| G-Eval | G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment | Yang Liu, Dan Iter, Yichong Xu, Shuohang Wang, Ruochen Xu, Chenguang Zhu | 2023 | EMNLP 2023 | 2303.16634 | https://github.com/nlpyang/geval |  |  |  | yes: code per paper | Abs page and full PDF opened. Repo URL is as printed in paper; stars/push not recorded, left blank rather than invented. | refutes | 3 | refute | 8 |
| MT-Bench-judge | Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena | Lianmin Zheng et al. | 2023 | NeurIPS 2023 Datasets and Benchmarks | 2306.05685 | https://github.com/lm-sys/FastChat | 39525 | 2026-05-01 | Apache-2.0 | yes: MT-bench questions, 3K expert votes, 30K arena conversations | Abs page and full PDF opened. Refutes the brief's implicit claim that a frontier model is a neutral scorer of payload quality. | refutes | 3 | refute | 8 |
| RL-in-Name-Only | RL IN NAME ONLY? ANALYZING THE STRUCTURAL ASSUMPTIONS IN RL POST-TRAINING FOR LLMS | Samineni, Soumya Rani; Kalwar, Durgesh; Valmeekam, Karthik; Stechly, Kaya; Kambhampati, Subbarao | 2025 | arXiv preprint (venue not verified) | 2505.13697 |  |  |  |  | unknown | verified via arXiv abs page and downloaded PDF; refutes claim that GRPO-style RL adds reasoning beyond filtered SFT | 4 | 3 | refute | 4 |
| Sainz-contamination | NLP Evaluation in trouble: On the Need to Measure LLM Data Contamination for each Benchmark | Oscar Sainz, Jon Ander Campos, Iker Garcia-Ferrero, Julen Etxaniz, Oier Lopez de Lacalle, Eneko Agirre | 2023 | EMNLP 2023 Findings | 2310.18018 |  |  |  |  | no | Abs page and full PDF opened; id-title match verified. Position paper, no released artefact. | refutes | 3 | refute | 8 |
| Smucker-SIGIR09 | Agreement Among Statistical Significance Tests for Information Retrieval Evaluation at Varying Sample Sizes | Mark Smucker, James Allan, Ben Carterette | 2009 | SIGIR 2009 | 10.1145/1571941.1572050 |  |  |  |  | no (author-hosted paper PDF only) | Verified at UMass CIIR publication list (venue/year/pages) and author-hosted PDF (title text confirmed inside PDF). | refutes | 3 | refute | 8 |
| QLoRA | QLoRA: Efficient Finetuning of Quantized LLMs | Tim Dettmers, Artidoro Pagnoni, Ari Holtzman, Luke Zettlemoyer | 2023 | NeurIPS 2023 (see round-2 inventory) | 2305.14314 | see round-2 inventory | see round-2 inventory | see round-2 inventory | see round-2 inventory | see round-2 inventory | In round-1/round-2 inventories; not re-found per brief section 2. | 4 | 3 | abstain | 5 |
| LQ-LoRA | LQ-LoRA: Low-rank Plus Quantized Matrix Decomposition for Efficient Language Model Finetuning | Han Guo, Philip Greengard, Eric Xing, Yoon Kim | 2023 | ICLR 2024 | 2311.12023 | https://github.com/HanGuo97/lq-lora | 129 | 2024-01-22T03:24:39Z | MIT | code | Verified at abs/ICLR pages but omitted from admits as third quant-LoRA recipe after LoftQ/QA-LoRA; no PDF downloaded. | 4 | 2 | abstain | 5 |
| (IA)3 | Few-Shot Parameter-Efficient Fine-Tuning is Better and Cheaper than In-Context Learning ((IA)3 + T-Few) | Haokun Liu, Derek Tam, Mohammed Muqeeth, Jay Mohta, Tenghao Huang, Mohit Bansal, Colin Raffel | 2022 | NeurIPS 2022 | 2205.05638 | unverified | unverified | unverified | unverified | code (per paper) | Verified at abs/NeurIPS/HF-docs pages; few-shot-era, no forgetting measurement; repo not verified; no PDF. | 5 | 1 | abstain | 5 |
| ADELIE | ADELIE: Aligning Large Language Models on Information Extraction | Yunjia Qi et al. | 2024 | EMNLP 2024 | n/a (ACL id 2024.emnlp-main.419) |  |  |  |  | not recorded | Primary source never opened; belongs partly to lane 6 as well. Flagged, not cited. | 1 | 1 | abstain | 8 |
| AFLoRA | AFLoRA: Adaptive Freezing of Low Rank Adaptation in Parameter Efficient Fine-Tuning of Large Models | Zeyu Liu, Souvik Kundu, Anni Li, Junrui Wan, Lianghao Jiang, Peter Beerel | 2024 | ACL 2024 (short) | doi:10.18653/v1/2024.acl-short.16 | unknown | unverified | unverified | unverified | unknown | ACL Anthology excerpt only, no arXiv id for papers/ naming; no PDF. | 5 | 1 | abstain | 5 |
| BiGGen-Bench | The BigGen Bench: A Principled Benchmark for Fine-grained Evaluation of Language Models with Language Models | authors not recorded | 2024 | arXiv preprint | 2406.05761 |  |  |  |  | not recorded | Primary source never opened. Listed so the integrator knows the Prometheus-2-BGB claim is second-hand. | 6 | 1 | abstain | 8 |
| Bottleneck-Tokens | Bottleneck Tokens for Unified Multimodal Retrieval | (authors not recorded) | 2026 | arXiv preprint | 2604.11095 |  |  |  | unknown | unknown | Screened via arXiv search snippet only; multimodal scope; not opened at primary source | 3 | 1 | abstain | 3 |
| CoMoL | CoMoL: Efficient Mixture of LoRA Experts via Dynamic Core Space Merging | Cao et al. | 2026 | arXiv preprint | 2603.00573 |  |  |  | unknown | unknown | Screened via arXiv search snippet; representative coverage via admitted MoLoRA; not opened at abs page | 3 | 1 | abstain | 3 |
| ConciseR | WALK BEFORE YOU RUN! CONCISE LLM REASONING VIA REINFORCEMENT LEARNING | Song, Mingyang; Zheng, Mao | 2025 | arXiv preprint (venue not verified) | 2505.21178 |  |  |  |  | unknown | verified via arXiv search snippet only; conciseness-only, tangential | 4 | 1 | abstain | 4 |
| Contamination-oracle-2024 | Towards Data Contamination Detection for Modern Large Language Models: Limitations, Inconsistencies, and Oracle Challenges | Vinay Samuel et al. | 2024 | arXiv preprint | 2409.09927 |  |  |  |  | not recorded | Primary source never opened. Listed so the gap (no agreed detector) is not silently dropped. | 2 | 1 | abstain | 8 |
| DARE-seed | Language Models are Super Mario (DARE) | (not verified in this lane) | 2023 | round-2 inventory | 2311.03099 |  |  |  | unknown | not re-verified | In round-2 inventory; not re-screened in this lane | 3 | 1 | abstain | 3,5 |
| DP-OPD | DP-OPD: DIFFERENTIALLY PRIVATE ON-POLICY DISTILLATION FOR LANGUAGE MODELS | Khadem, Fatemeh; Mousavi, Sajad; Fang, Yi; Liu, Yuhong | 2026 | arXiv preprint (venue not verified) | 2604.04461 |  |  |  |  | unknown | verified via arXiv search snippet only; differential-privacy scope, tangential | 4 | 1 | abstain | 4 |
| Data-contamination-survey-2025 | A Survey on Data Contamination for Large Language Models | authors not recorded | 2025 | arXiv preprint | 2502.14425 |  |  |  |  | not recorded | Primary source never opened; superseded for our purposes by admitted 2406.04244 survey. | 2 | 1 | abstain | 8 |
| DeepSeek-Prover-SFT | DEEPSEEK-PROVER: ADVANCING THEOREM PROVING IN LLMS THROUGH LARGE-SCALE SYNTHETIC DATA | Xin, Huajian; Guo, Daya; Shao, Zhihong; Ren, Zhizhou; Zhu, Qihao; Liu, Bo et al. | 2024 | arXiv preprint (venue not verified) | 2405.14333 |  |  |  |  | unknown | verified via arXiv search snippet only; large-scale synthetic SFT, lane-2 overlap | 4 | 1 | abstain | 4 |
| DeepSeekMath-V2 | DEEPSEEK-MATH-V2: TOWARDS SELF-VERIFIABLE MATHEMATICAL REASONING | Shao, Zhihong; Luo, Yuxiang; Lu, Chengda; Ren, Z. Z.; Hu, Jiewen; Ye, Tian et al. | 2025 | arXiv preprint (venue not verified) | 2511.22570 |  |  |  |  | unknown | verified via arXiv search snippet only; frontier scale, no single-GPU recipe | 4 | 1 | abstain | 4 |
| Demystifying-GRPO | DEMYSTIFYING GROUP RELATIVE POLICY OPTIMIZATION: ITS POLICY GRADIENT IS A U-STATISTIC | Zhou, Hongyi; Ye, Kai; Xu, Erhan; Zhu, Jin; Yang, Ying; Gong, Shijin et al. | 2026 | arXiv preprint (venue not verified) | 2603.01162 |  |  |  |  | unknown | verified via arXiv search snippet only; pure theory, no actionable recipe | 4 | 1 | abstain | 4 |
| Deng-NAACL24 | Investigating Data Contamination in Modern Benchmarks for Large Language Models | Chunyuan Deng et al. | 2024 | NAACL 2024 | n/a (DOI not recorded) |  |  |  |  | not recorded | Primary source never opened; cited here only as screened. Covered by admitted BDC survey and Sainz. | 2 | 1 | abstain | 8 |
| Distill-Reader-to-Retriever | Distilling Knowledge from Reader to Retriever for Question Answering | Izacard; Grave | 2021 | ICLR 2021 | none (OpenReview primary; no arXiv id) | n/a | n/a | n/a | n/a | unknown | No arXiv PDF to file (OpenReview is the primary); content covered by the Atlas and REPLUG-LSR admits; repo not resolved. | 3 | 1 | abstain | 10 |
| DynamicRetriever | DynamicRetriever: A Pre-training Model-based IR System with Neither Sparse nor Dense Index | Zhou; Yao; Dou; Wu; Wen | 2022 | unconfirmed | 2203.00537 (id from PDF search-result URL only) | n/a | n/a | n/a | n/a | unknown | Abs page never opened (only a PDF search-result excerpt); venue and details unconfirmed; same-group successor Ultron admitted instead. | 3 | 1 | abstain | 10 |
| GKD-AV-Application | ON-POLICY DISTILLATION OF LANGUAGE MODELS FOR AUTONOMOUS VEHICLE MOTION PLANNING | Afsharrad, Amirhossein; Abedsoltan, Amirhesam; Moradipari, Ahmadreza; Lall, Sanjay | 2026 | arXiv preprint (venue not verified) | 2604.07944 |  |  |  |  | unknown | verified via arXiv search snippet only; single-domain application, low transfer | 4 | 1 | abstain | 4 |
| GRPO-Alignment-Objective | WHAT IS THE ALIGNMENT OBJECTIVE OF GRPO? | Vojnovic, Milan; Yun, Se-Young | 2025 | arXiv preprint (venue not verified) | 2502.18548 |  |  |  |  | unknown | verified via arXiv search snippet only; theory note, no recipe | 4 | 1 | abstain | 4 |
| HAPO | HAPO: TRAINING LANGUAGE MODELS TO REASON CONCISELY VIA HISTORY-AWARE POLICY OPTIMIZATION | Huang, Chengyu; Zhang, Zhengxin; Cardie, Claire | 2025 | arXiv preprint (venue not verified) | 2505.11225 |  |  |  |  | unknown | verified via arXiv search snippet only; length-efficiency only, tangential | 4 | 1 | abstain | 4 |
| L-MoE | L-MoE: End-to-End Training of a Lightweight Mixture of Low-Rank Adaptation Experts | Ji; Song | 2025 | arXiv preprint | 2510.17898 |  |  |  | unknown | unknown | Screened via arXiv search snippet; overlaps admitted MoLoRA; not opened at abs page | 3 | 1 | abstain | 3 |
| LR-QAT | Low-Rank Quantization-Aware Training for LLMs | Yelysei Bondarenko, Riccardo Del Chiaro, Markus Nagel | 2024 | not venue-checked (arXiv abs excerpt only) | 2406.06385 | unverified | unverified | unverified | unverified | code (per paper) | Abs excerpt via search only, full abs page never opened; narrow QAT scope; no PDF. | 4 | 1 | abstain | 5 |
| Lamer-SSL | Lamer-SSL: Layer-aware Mixture of LoRA Experts for Continual Multilingual Expansion | Xu et al. | 2026 | ICASSP 2026 | 2602.12746 |  |  |  | unknown | unknown | Screened via arXiv search snippet; speech setting; replay-plus-MoLE pattern already covered by admitted items | 3 | 1 | abstain | 3 |
| LoRAF | LoRA Without Forgetting: Freezing and Sparse Masking for Low-Rank Adaptation | Juzheng Zhang, Jiacheng You, Ashwinee Panda, Tom Goldstein | 2025 | ICLR 2025 SLLM workshop | none found | unknown | unverified | unverified | unverified | unknown | ICLR workshop page excerpt only; no arXiv id opened; no PDF. | 3 | 1 | abstain | 5 |
| LongWriter-Zero | LONGWRITER-ZERO: MASTERING ULTRA-LONG TEXT GENERATION VIA REINFORCEMENT LEARNING | Wu, Yuhao; Bai, Yushi; Hu, Zhiqiang; Lee, Roy Ka-Wei; Li, Juanzi | 2025 | ICLR 2026 Oral (per snippet) | 2506.18841 | https://huggingface.co/THU-KEG/LongWriter-Zero-32B | unknown |  | unknown | yes (data, checkpoints per abstract) | verified via arXiv search snippet only; 32B long-form scope, not transferable to 2B harness | 4 | 1 | abstain | 4 |
| Macaron-MoL | Macaron-V1: Towards Open Continual Learning with Self-Improvement and Mixture-of-LoRA | Mind Lab et al. | 2026 | arXiv preprint | 2608.09819 |  |  |  | unknown | unknown | Screened via arXiv search snippet; two orders of magnitude above our scale; no transferable 1-3B measurement | 3 | 1 | abstain | 3 |
| MathFusion | MATHFUSION: ENHANCING MATHEMATICAL PROBLEM-SOLVING OF LLM THROUGH INSTRUCTION FUSION | Pei, Qizhi; Wu, Lijun; Pan, Zhuoshi; Li, Yu; Lin, Honglin; Ming, Chenlin et al. | 2025 | ACL 2025 (per snippet) | 2503.16212 | https://github.com/QizhiPei/mathfusion | unknown |  | unknown | yes (datasets, models, code per abstract) | verified via arXiv search snippet only; lane-2 (data) overlap, math-only | 4 | 1 | abstain | 4 |
| Min-K Percent Prob | Detecting Pretraining Data from Large Language Models (Min-K% Prob) | Weijia Shi, Anirudh Ajith, Mengzhou Xia, Yangsibo Huang, Daogao Liu, Terra Blevins, Danqi Chen, Luke Zettlemoyer | 2023 | arXiv preprint (venue unverified) | 2310.16789 | unverified | unverified | unverified | unverified | Method described in paper | Verified at primary source but deferred: contamination detection is evaluation-side (lane 8 territory), not dataset construction. | 2 | 1 | abstain | 2 |
| Nemotron-4 340B | Nemotron-4 340B Technical Report | Nvidia | 2024 | NVIDIA technical report | 2406.11704 | unverified | unverified | unverified | unverified | Data: HF nvidia/HelpSteer2 (verified entry) | Verified at primary source but screened out: base-model-scale report; document-synthetic detail thinner than Nemotron-CC for this lane; kept as background. | 2 | 1 | abstain | 2 |
| ProtoAda | ProtoAda: Prototype-Guided Adaptive Adapter Expansion and Geometric Consolidation | Shi et al. | 2026 | arXiv preprint | 2606.02576 |  |  |  | unknown | unknown | Screened via arXiv search snippet; vision-language setting; routing insight covered by admitted Arrow/MoLoRA | 3 | 1 | abstain | 3 |
| QuAILoRA | QuAILoRA: Quantization-Aware Initialization for LoRA | Neal Lawton, Aishwarya Padmakumar, Judith Gaspers, Jack FitzGerald, Anoop Kumar, Greg Ver Steeg, Aram Galstyan | 2024 | NeurIPS ENLSP workshop (PMLR v262) | 2410.14713 | unknown | unverified | unverified | unverified | unknown | Abs excerpt via search only; workshop; no PDF. | 4 | 1 | abstain | 5 |
| Rank-DistiLLM | RANK-DISTILLM: CLOSING THE EFFECTIVENESS GAP BETWEEN CROSS-ENCODERS AND LLMS FOR PASSAGE RE-RANKING | Schlatt, Ferdinand; Frobe, Maik; Scells, Harrisen; Zhuang, Shengyao; Koopman, Bevan; Zuccon, Guido et al. | 2024 | ECIR 2025 (per snippet) | 2405.07920 | https://github.com/webis-de/ECIR-25 | unknown |  | unknown | yes (code and data per abstract) | verified via arXiv search snippet only; re-ranking scope, not generative harness | 4 | 1 | abstain | 4 |
| ReMix | ReMix: Reinforcement routing for mixtures of LoRAs in LLM finetuning | Qiu et al. | 2026 | arXiv preprint | 2603.10160 |  |  |  | unknown | unknown | Screened via arXiv search snippet; router-collapse finding noted but not verified at primary source | 3 | 1 | abstain | 3 |
| S-GRPO | S-GRPO: EARLY EXIT VIA REINFORCEMENT LEARNING IN REASONING MODELS | Dai, Muzhi; Yang, Chenxu; Si, Qingyi | 2025 | arXiv preprint (venue not verified) | 2505.07686 |  |  |  |  | unknown | verified via arXiv search snippet only; conciseness-only, tangential | 4 | 1 | abstain | 4 |
| SAMoRA | SAMoRA: Semantic-Aware Mixture of LoRA Experts for Task-Adaptive Learning | Shi et al. | 2026 | arXiv preprint | 2604.19048 | https://github.com/boyan-code/SAMoRA |  |  | unknown | code released | Screened via arXiv search snippet; representative coverage via admitted MoLoRA/Arrow; not opened at abs page | 3 | 1 | abstain | 3 |
| Small-model forgetting | Catastrophic Forgetting in LLMs: A Comparative Analysis Across Language Tasks | Naimul Haque | 2025 | not venue-checked (arXiv abs opened) | 2504.01241 | none | 0 | n/a | n/a | n/a | Abs page opened; single-author, no PEFT-vs-FT isolation, prompting confound; weak evidence. | 5 | 1 | abstain | 5 |
| TIES-seed | TIES-Merging: Resolving Interference When Merging Models | (not verified in this lane) | 2023 | round-2 inventory | 2306.01708 |  |  |  | unknown | not re-verified | In round-2 inventory; not re-screened in this lane | 3 | 1 | abstain | 3,5 |
| Urbano-SIGIR13 | A comparison of the optimality of statistical significance tests for information retrieval evaluation | Julian Urbano, Monica Marrero, Diego Martin | 2013 | SIGIR 2013 | 10.1145/2484028.2484163 |  |  |  |  | not recorded | Primary source (paywalled ACM) never opened; claims taken only from secondary excerpts. Covered for our purposes by admitted Smucker papers. | 3 | 1 | abstain | 8 |
| X-KD | -XKD: GENERAL EXPERIENTIAL KNOWLEDGE DISTILLATION FOR LARGE LANGUAGE MODELS | Cai, Yuang; Yuan, Yuyu | 2026 | arXiv preprint (venue not verified) | 2602.12674 |  |  |  |  | unknown | verified via arXiv search snippet only; tangential framing, no harness-transferable recipe beyond baselines | 4 | 1 | abstain | 4 |
| Arrow-trap | Discrete-Time I and I Adaptive Interconnection and Damping Passivity-Based Control | Alkrunz; Yalcin | 2024 | arXiv preprint | 2405.19944 |  |  |  | unknown | no | Opened abs page to check a recalled id; title mismatch proves the guess wrong; recorded as verification trap | 3 | 0 | abstain | 3 |
| CaseHOLD-2104.08671 | When Does Pretraining Help? Assessing Self-Supervised Learning for Law and the CaseHOLD Dataset | Lucia Zheng et al. | 2021 | ICAIL 2021 | 2104.08671 |  |  |  |  | not recorded | Opened abs page to rule it out: it is the correct paper for 2104.08671, not BEIR (2104.08663). Screened, out of scope. | 1 | 0 | abstain | 8 |
| FLAN | Finetuned Language Models Are Zero-Shot Learners (FLAN) | Jason Wei, Maarten Bosma (et al.; full list per arXiv) | 2021 | arXiv preprint (venue unverified) | 2109.01652 | unverified | unverified | unverified | unverified | Human instruction collection per paper | Verified at primary source but out of scope: human-written data, no synthetic-generation recipe for the lane. | 2 | 0 | abstain | 2 |
| GritLM-seed | Generative Representational Instruction Tuning | Muennighoff et al. (not verified in this lane) | 2024 | round-2 inventory | 2402.09906 |  |  |  | unknown | not re-verified | Seed from brief/round-2; used only as forward-chaining source via OpenAlex, not re-found | 3 | 0 | abstain | 3 |
| Hydra-seed | Hydra: Unifying Document Retrieval and Generation in a Single Vision-Language Model | (not verified in this lane) | 2026 | round-2 inventory | 2603.28554 |  |  |  | unknown | not re-verified | Seed from brief/round-2; chaining source only, not re-found | 3 | 0 | abstain | 3 |
| Instruction Mining wrong id | Record of miss: 2307.06215 is an unrelated paper (rotating black holes) | n/a | n/a | n/a | 2307.06215 (wrong) | n/a | n/a | n/a | n/a | n/a | Resolved miss, kept in inventory so nothing screened is dropped silently. | 2 | 0 | abstain | 2 |
| LLM2Vec-seed | LLM2Vec paper (title not verified in this lane) | BehnamGhader et al. (not verified in this lane) | 2024 | round-2 inventory | 2404.05961 |  |  |  | unknown | not re-verified | Seed from brief/round-2; chaining source only, not re-found | 3 | 0 | abstain | 3 |
| ORPO | unverified candidate (monolithic preference optimization) | unknown | unknown | unknown | unverified (guessed 2404.10019 disproven via abs fetch: unrelated astrophysics paper) |  |  |  |  |  | could not verify arXiv id; follow-up search timed out; do not cite | 4 | 0 | abstain | 4 |
| OneGen-seed | OneGen paper (title not verified in this lane) | (not verified in this lane) | 2024 | round-2 inventory | 2409.05152 |  |  |  | unknown | not re-verified | Seed from brief/round-2; chaining source only, not re-found | 3 | 0 | abstain | 3 |
| RAFT | unverified candidate (reward-ranked fine-tuning) | unknown | unknown | unknown | unverified (guessed 2309.07487 disproven via abs fetch: biomechanics) |  |  |  |  |  | could not verify arXiv id; do not cite | 4 | 0 | abstain | 4 |
| SGPT-trap | Feasibility Enhancement of Constrained Receding Horizon Control Using Generalized Control Barrier Function | Ma et al. | 2021 | arXiv preprint | 2102.13304 |  |  |  | unknown | no | Opened abs page to check a recalled id; title mismatch proves the guess wrong | 3 | 0 | abstain | 3 |
| Super-NaturalInstructions | Super-NaturalInstructions: Generalization via Declarative Instructions on 1600+ NLP Tasks | Yizhong Wang, Swaroop Mishra (et al.; full list per arXiv) | 2022 | arXiv preprint (venue unverified) | 2204.07705 | unverified | unverified | unverified | unverified | Benchmark released per paper | Verified at primary source but out of scope: human-written data, no synthetic-generation recipe for the lane. | 2 | 0 | abstain | 2 |
| Tulu-3 | unverified candidate (open post-training recipe) | unknown | unknown | unknown | unverified (guessed 2411.15134 disproven via abs fetch: toric invariance) |  |  |  |  |  | could not verify arXiv id; do not cite | 4 | 0 | abstain | 4 |
| V-STaR | unverified candidate (verifier-augmented STaR) | unknown | unknown | unknown | unverified (guessed 2310.05689 disproven via abs fetch: opinion dynamics; text searches empty) |  |  |  |  |  | could not verify arXiv id after three attempts; do not cite | 4 | 0 | abstain | 4 |
| Wrong-id probe 1 | Topotactic Transition (materials science; NOT a LoRA paper) | Ziang Meng et al. | n/a | n/a | 2305.16605 | n/a | n/a | n/a | n/a | n/a | Opened to disprove; listed so the error is on record, not silently dropped. | 5 | 0 | abstain | 5 |
| Wrong-id probe 2 | Designing metainterfaces with specified friction laws (NOT DoRA) | Antoine Aymard et al. | n/a | n/a | 2402.10960 | n/a | n/a | n/a | n/a | n/a | Opened to disprove; listed so the error is on record, not silently dropped. | 5 | 0 | abstain | 5 |
| rsLoRA-trap | Proportional Representation in Metric Spaces and Low-Distortion Committee Selection | Kalayci; Kempe; Kher | 2023 | arXiv preprint | 2312.10369 |  |  |  | unknown | no | Opened abs page to check a recalled id; title mismatch proves the guess wrong | 3 | 0 | abstain | 3 |

## 10. Method

Per-lane screened/admitted counts (from `lanes/<n>/method.md`; all lanes met
the >=20 screened / >=8 admitted minimums):

| Lane | Screened | Admitted | Abstained | Refute-disposition | PDFs staged |
|---|---|---|---|---|---|
| 1 structured/constrained generation | 26 | 22 (18 papers + BFCL + 3 code/eval artefacts) | 4 | 0 (3 refutations rest on admitted papers) | 18 |
| 2 dataset construction | 34 | 23 | 11 | 0 | 23 |
| 3 joint/interference | 39 | 22 | 17 | 0 (3 refutations rest on admitted papers) | 22 |
| 4 distillation/RL | 47 | 29 (25 papers + 4 code artefacts) | 17 | 1 (RL-in-Name-Only) | 26 |
| 5 LoRA/PEFT | 32 | 20 | 12 | 0 (3 refutations rest on admitted papers) | 20 |
| 6 extraction | 36 | 33 | 3 | 0 | 33 (30 arXiv + 3 ACL Anthology) |
| 7 lab recipes | 24 | 18 (15 papers + SmolLM3 configs + Granite 3.0/4.0) | 5 | 0 (1 size-label refutation, no inventory row) | 15 |
| 8 evaluation | 31 | 16 | 9 | 6 | 22 (16 admits + 6 refutes) |
| 9 composition | 22 | 22 | 0 | 0 | 22 |
| 10 generative retrieval | 35 | 33 | 2 | 0 (4 refutations rest on admitted papers) | 33 |
| Merge total | 326 rows | 224 unique (238 pre-dedup) | 58 | 6 | 227 |

Queries and sources: every lane opened each admitted arXiv id at
`https://arxiv.org/abs/<id>` (title/authors/date from page metadata) and
downloaded PDFs from `https://arxiv.org/pdf/<id>` with `%PDF` verification,
filenames `<arxiv-id>_<Title_Slug>.pdf` without spaces (lane 6 used ACL
Anthology ids for REBEL/UIE/PIVOINE, lane 8 used ACL/DOI/author-PDF prefixes
for its three non-arXiv primaries — documented deviations). Repo facts came
from the GitHub REST API (stars/pushed_at/license, point-in-time 2026-09-12),
datasets from the Hugging Face API, venues only from fetched pages (ACL
Anthology, ICLR/NeurIPS/PMLR proceedings, PMLR, TACL, publisher sites);
elsewhere venue reads "arXiv preprint". Forward/backward citation chaining ran
through fetched reference lists and OpenAlex (lane 2: 110 citers of WizardLM
scanned; lane 3: 15 GritLM citers, thin coverage).

What failed, globally: `export.arxiv.org/api/query` rate-limited ("Rate
exceeded"/503) for all lanes — no systematic listing sweeps, so 2025-onward
coverage leans on search ranking, biasing toward cited work; Semantic Scholar
API HTTP 429 throughout — no S2 citation-graph chaining; Papers with Code API
empty/non-JSON; GitHub unauthenticated quota (60/hr) exhausted in several
lanes, leaving some repo fields `unverified`/`unknown` rather than invented;
no PDF text tooling on some machines (hand-rolled parsers or stream
decompression substituted; lane 5 screened abstracts only). Recalled arXiv ids
were wrong in every lane that tried them (documented as abstain traps, e.g.
lane-1 Gorilla/APIGen/ToolACE corrections, lane-3 Arrow/rsLoRA/SGPT traps,
lane-4 ORPO/V-STaR/Tulu-3/RAFT guesses, lane-6 REBEL/DocRED/GenIE/InstructUIE
guesses, lane-8 BEIR 2104.08671, lane-10 DSI guesses) — nothing is admitted
from recall.

Merge (integrator): 326 lane rows deduplicated to 288 unique items on
name/id; cross-lane items carry all lanes (e.g. Self-RAG 9,10; RAFT 2,10;
LoRA-Learns-Less 3,5; Tulu-3 2,7; WebIE 6,8; GenIE 6,8; ARES 8,9; TinyZero
2,4,7; Functionary 1,6). Repair: three lane-9 rows (GSM-IC 2302.00093,
Robust-RALM 2310.01558, xRAG 2405.13792) arrived column-shifted with empty
disposition; restored as admit with relevance 2/3/3 and reasons as written by
lane 9; their license/artefact cells were overwritten by the shift and are
marked not recorded. Lane-7's MiniCPM5-2B refutation has no inventory row
(the brief's own label is refuted). Lane capability-column notes: lanes 2 and
9 record that their task text said "(1-5 or refutes)" while the brief defines
six questions; inventory uses Q1-Q6 numbering. Lane 8's capability mapping is
approximate by design ("which training question this eval evidence serves").
