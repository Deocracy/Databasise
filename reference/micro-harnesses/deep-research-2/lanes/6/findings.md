# Lane 6 findings: Evaluating "best" and fixing anisotropy

Scope: MTEB / MMTEB / BEIR and domain-specific evaluation; building an eval set for a
private corpus with synthetic queries; anisotropy and isotropy fixes; what a fair
head-to-head between a trained embedder and a decoder state looks like; metric pitfalls
with small query sets. 22 admitted, 10 abstained, 32 screened. Every arXiv id below was
opened at `https://arxiv.org/abs/<id>` (title, authors, date, abstract read); repo
facts come from the GitHub API. Detail level varies honestly: papers whose abstract I
read carry stronger claims than papers verified by title record only — the latter are
flagged "title-record" so the integrator knows to read the PDF before quoting numbers.

## (a) Admitted items

**MTEB (2210.07316, Muennighoff et al. 2022).** The multi-task embedding benchmark:
8 embedding tasks, 58 datasets, 112 languages, 33 models at release. Its headline result
is that no single method dominates all tasks. Take: adopt MTEB task diversity as the
definition of "best" — report retrieval, STS, clustering and reranking separately and
never a single mean as the selection criterion. Careful: MTEB-scale evaluation is
expensive; for iteration use the MMTEB cheap splits (below), and MTEB does not cover
private-corpus distributions at all.

**MMTEB (2502.13595, Enevoldsen et al. 2025).** 500+ quality-controlled tasks across
250+ languages; finds a 560M-parameter model (multilingual-e5-large-instruct) beating
billion-parameter LLMs overall. Two methods transfer directly: downsampling tasks by
inter-task correlation while preserving model ranking, and hard-negative sampling to
make small-but-effective retrieval splits. Take: copy the downsampling recipe for the
MelodyScribe eval harness, and note the existence proof that sub-billion models can top
the board. Careful: 2025 item, fast-moving leaderboard; re-fetch rankings before citing
a "current best".

**BEIR (2104.08663, Thakur et al. 2021, NeurIPS Datasets and Benchmarks).** 18-dataset
heterogeneous zero-shot retrieval benchmark over 10 systems (lexical, sparse, dense,
late-interaction, rerank). Verified findings: BM25 is a robust baseline; reranking and
late-interaction models are best zero-shot on average but costly; dense and sparse
models are efficient but often lag. Take: BEIR is the "does it generalise" gate every
MelodyScribe embedder must pass, and BM25 is the mandatory baseline. Careful: BEIR
averages hide per-dataset reversals (see Brewing BEIR); several BEIR sets are tiny
(TREC-COVID 50 queries, Touché-2020 49, TREC-NEWS 57 — per the official repo dataset
table), so small-query variance applies.

**Brewing BEIR (2306.07471, Kamalloo et al. 2023).** Reproducible dense/sparse reference
implementations plus an official leaderboard; its meta-analysis contribution is that
collapsing heterogeneous dataset scores into one average is hard to interpret, and
effect sizes across datasets quantify model differences accurately. Take: replace every
mean-score model comparison in spikes with per-dataset effects (win rate, mean effect
with intervals). Careful: reference-model code lives in the BEIR ecosystem — pin the
commit before benchmarking.

**BIRCO (2402.14151, Wang et al. 2024) — title-record.** Retrieval tasks with complex
multi-part objectives. Take: if MelodyScribe queries carry instructions or compound
constraints, BIRCO-style tasks are the eval to watch; check whether instruction
conditioning (lane 5) moves these scores. Careful: only the title record was verified;
read the PDF before adopting its tasks.

**AIR-Bench (2412.13102, Chen et al. 2024) — title-record.** An automatically generated
heterogeneous IR benchmark — the closest public analogue of "eval set with no human
labels". Take: this is the template for the MelodyScribe private-corpus benchmark
(LLM-written queries + judgments, then a small human audit as in ARES). Careful:
title-record only; verify its correlation-with-human-benchmarks claim in the PDF before
trusting fully synthetic labels.

**SimCSE (2104.08821, Gao et al. 2021, EMNLP).** Dropout-as-noise unsupervised
contrastive learning matches prior supervised STS results; NLI entailment/contradiction
pairs give the supervised variant. Central for this lane: the paper shows, theoretically
and empirically, that the contrastive objective regularises the anisotropic pretrained
space toward uniformity while aligning positives. Take: this is the mechanism Spike 004
did not run — contrastive/LLM2Vec-style tuning is the missing treatment, and dropout
positives mean it needs no labelled pairs to start. Careful: results are STS-centric;
STS gains do not imply BEIR gains.

**Alignment and uniformity (2005.10242, Wang & Isola 2020, ICML).** Contrastive loss
asymptotically optimises two measurable properties — alignment of positives and
uniformity of features on the hypersphere — with metrics that track downstream
performance; optimising the metrics directly matches contrastive training. Take: report
alignment and uniformity alongside MRR in every spike; they diagnose whether a fix
worked even when MRR is noisy on 20 documents. Careful: theory is asymptotic and the
experiments are vision+language, not retrieval-specific.

**BERT-whitening (2103.15316, Su et al. 2021).** A classical whitening operation on
sentence representations improves isotropy with competitive results while cutting
dimension, storage and retrieval time. Take: this is the cheapest Spike 004 follow-up —
whiten the MiniCPM5 last-token states on the 20-document corpus statistics and
re-run MRR before any training; it costs minutes on CPU. Careful: whitening statistics
estimated on 20 documents may be unstable; estimate on a larger unlabeled sample.

**BERT-flow (2011.05864, Li et al. 2020, EMNLP).** Argues BERT sentence embeddings
underuse their semantic content because the space is anisotropic and non-smooth, and
maps them to an isotropic Gaussian with an unsupervised flow for large STS gains. Take:
pairs with whitening as the two post-hoc controls for the fair head-to-head (linear
vs. non-linear unsupervised repair). Careful: flows add inference machinery whitening
does not; prefer whitening unless the flow wins clearly.

**All-but-the-top (1702.01417, Mu et al. 2017) — title-record.** Removes dominant
common directions from word representations. Take: the oldest, simplest repair in this
family — implement it as a third baseline next to whitening once the PDF is read. Careful: title-record only, and the result originates on static embeddings;
verify on contextual/decoder states rather than assuming transfer.

**Ethayarajh (1909.00512, 2019) — title-record.** Compares the geometry of BERT, ELMo
and GPT-2 embeddings — the only admitted study covering a causal decoder, i.e. the
closest published analogue of Spike 004's MiniCPM5 last-token state. Take: read it for
baseline anisotropy expectations before concluding the 0.91 mean-cosine is
"surprising". Careful: title-record only; word-level geometry need not match
section-level pooled states.

**Representation degeneration (1907.12009, Gao et al. 2019) — title-record.** Diagnoses
why likelihood-trained generation models degenerate token-embedding geometry. Take: the
causal candidate for *why* the untrained decoder state is anisotropic — cite it as the
mechanism hypothesis Spike 004 should test (e.g. frequency-stratified cosine
analysis). Careful: title-record only; word-token result, not a pooled-state result.

**IsoScore (2108.07344, Rudman et al. 2021) — title-record.** A score for how uniformly
an embedding space is used. Take: adopt IsoScore as the single number that says whether
any anisotropy fix worked, reported next to MRR in spikes 004/006/007. Careful:
title-record only; confirm in the PDF that it applies to sentence/section embeddings,
not just word types.

**E5 (2212.03533, Wang et al. 2022) — title-record.** Weakly-supervised contrastive
pretraining recipe for text embeddings. Take: the data-curation template (large noisy
pairs first, high-quality triplets after) for the Q1 training plan. Careful:
title-record only; compute budget in the paper exceeds one 16 GB GPU — the recipe
needs the lane-2 downscaling, not a direct copy.

**Promptagator (2209.11755, Dai et al. 2022) — title-record.** Dense retrieval from
8 examples via LLM-generated data. Take: the minimum-viable synthetic eval-set recipe —
8 labelled examples per query type is within a maintainer's afternoon. Careful:
title-record only; few-shot generation quality is LLM-dependent, so audit a sample.

**InPars-v2 (2301.01820, Jeronymo et al. 2023) — title-record.** Efficient LLM dataset
generation for IR. Take: the efficiency upgrade over v1 for generating the 20-document
corpus's query set at scale. Careful: the arXiv record version is a short (4-page)
PDF; check for a longer venue version before implementing details.

**GPL (2112.07577, Wang et al. 2021) — title-record.** Generative pseudo-labelling for
unsupervised domain adaptation of dense retrieval. Take: the closest published answer
to "no labelled query-passage pairs" — generate queries, pseudo-label with a
cross-encoder, train the dense model. Careful: needs a cross-encoder teacher at
generation time; budget that GPU time.

**ARES (2311.09476, Saad-Falcon et al. 2023) — title-record + verified code
(stanford-futuredata/ARES, Apache-2.0).** Automated RAG evaluation over synthetic
queries/judgments. Take: the validation layer for synthetic eval — small human sample
plus statistical intervals, not blind trust. Careful: builds full RAG-system eval,
heavier than passage-retrieval-only needs; lift the judgment protocol, not the whole
system.

**Gecko (2403.20327, Lee et al. 2024) — title-record.** Distilling versatile text
embeddings from LLMs into a compact model. Take: the "small model from big-model
signal" recipe most relevant to distilling a larger embedder into MelodyScribe's 2B
host (with lane 3). Careful: no public artefact recorded; recipe only.

**DPR (2004.04906, Karpukhin et al. 2020) — title-record + verified code
(facebookresearch/DPR).** Dense passage retrieval for open-domain QA. Take: the
top-k retrieval-accuracy eval protocol (k = 5/20/100) that keeps small-corpus
head-to-heads comparable across papers. Careful: its in-domain training regime is
exactly what BEIR later showed to generalise poorly — cite for protocol, not for
training claims.

**MS MARCO (1611.09268, Bajaj et al. 2016) — title-record.** Large-scale
human-generated queries for passage ranking. Take: the query-distribution reference —
any synthetic query set should be sanity-checked against MS MARCO query-length/type
statistics before trusting its MRR. Careful: well-known false-negative sparsity in its
labels; sparse labels punish good retrievers.

## (b) Refutations

1. **Naive cross-dataset averaging ranks models reliably.** Refuted by Brewing BEIR
   (2306.07471): collapsing heterogeneous BEIR scores into one average is hard to
   interpret; per-dataset effect sizes are the sound comparison. Any spike or recipe
   step that selects a model by mean MTEB/BEIR score contradicts this source.
2. **Raw cosine of an untrained decoder state is a fair "untrained embedder"
   baseline.** Refuted in combination by Ethayarajh (1909.00512), BERT-flow
   (2011.05864) and Representation Degeneration (1907.12009): likelihood-trained
   geometry is anisotropic, so raw cosine confounds representation quality with
   cone effects. Spike 004's 0.31-vs-trained gap is uninterpretable without a
   whitened/centred control (Whitening 2103.15316, ABTT 1702.01417).
3. **Post-processing cannot repair embedding geometry (reading of Spike 004's ridge
   result).** Qualified refutation: the ridge head was supervised on tiny data, while
   Whitening (2103.15316) and ABTT (1702.01417) show *unsupervised* linear repairs
   help. The claim "no linear head helps" is contradicted; the claim "a supervised
   ridge head on 20 documents helps" stands.
4. **Evaluation requires human labels at scale.** Refuted in its strong form by the
   AIR-Bench programme (2412.13102, automated benchmarks) together with ARES
   (2311.09476, synthetic judgments plus human-anchored intervals): a small human
   audit calibrates synthetic labels instead of replacing them.

## (c) Unresolved ledger

- **SBERT (1908.10084) — abstain (scope).** Abs page verified. Bi-encoder training
  belongs to lanes 1–2; its eval protocol is subsumed by MTEB/BEIR from the same
  author line. Revisit if the head-to-head section needs the 65h-to-5s precedent.
- **ColBERT (2004.12832) — abstain (scope).** Abs page + repo verified (3932 stars,
  MIT). Architecture comparison is lane 1; BEIR carries its eval result.
- **Contriever (2112.09118) — abstain (scope).** Abs page + repo verified (779
  stars). Unsupervised training recipe is lane 2.
- **TSDAE (2104.06979) — abstain (scope).** Abs page verified. Denoising
  auto-encoder training is lane 2; GPL covers adaptation for this lane.
- **Doc2Query (1904.08375) — abstain (scope).** Abs page verified. Expansion and
  training-data use is lane 2; the synthetic-query recipe is carried by
  E5/Promptagator/InPars-v2.
- **AugSBERT (2010.08240) — abstain (scope + shallow verification).** OpenAlex
  record only; abs page opened for authors/title but abstract not read. Training
  augmentation is lane 2 in any case.
- **InPars-v1 (2202.05144) — abstain (superseded).** Abs page verified; v2 admitted.
- **InPars-Light (2301.02998) — abstain (scope).** Abs page verified; note the
  authors are Boytsov et al., not the InPars team — it is an independent
  cost-effective ranker-training variant, lane 10 territory.
- **RAGAS — abstain (unverifiable).** No arXiv record; venue is the EACL 2024
  system-demonstration track (OpenAlex, secondary); the code repo could not be
  resolved because the GitHub API rate-limited mid-lane. Revisit with API quota.
- **SIF / Arora et al. — abstain (unverifiable).** No arXiv record found; OpenAlex
  points to the ICLR 2017 venue paper and a Princeton OAR copy. Plausibly relevant but not downloadable per lane rules.
- **TREC Deep Learning track overview — not screened.** No arXiv record identified
  within budget; MS MARCO + BEIR cover the sparse-label warning instead.
- **Rank-stability statistics for n ≤ 50 query sets — not screened to a primary
  source.** The pitfall is evidenced (BEIR tiny sets + Brewing BEIR), but a
  dedicated power/significance reference was not verified. Gap for the integrator.

## (d) Security findings (as requirements)

- **Eval corpora are untrusted input.** MS MARCO, BEIR and any web-derived synthetic
  eval set can contain PII, toxic text and prompt-injection payloads. Requirement:
  the eval harness must sandbox corpus text (no execution, no outbound calls) and
  log corpus version hashes so a poisoned re-download cannot silently move MRR.
- **No train-on-eval.** Several admitted recipes (E5 weakly-supervised pairs, Gecko
  distillation, GPL pseudo-labels) scrape broad data that may contain benchmark
  text. Requirement: the training plan must include a decontamination step
  (n-gram overlap against every eval split) with the overlap report stored next to
  the checkpoint, or "best" numbers are void.
- **Metric gaming.** Single-mean model selection is gameable by construction
  (Brewing BEIR). Requirement: model-selection decisions must cite per-dataset
  effects, not a mean, with the comparison script checked into the harness.
