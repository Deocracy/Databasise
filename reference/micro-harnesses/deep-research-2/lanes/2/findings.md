# Lane 2 findings: training recipes for embedders

Scope: contrastive objectives, negatives, false-negative handling, two-stage
weakly-supervised pretraining then supervised fine-tuning, synthetic query
generation, instruction tuning, and single-16GB-GPU fit. 29 screened, 20
admitted. Every admitted item was opened at its arXiv abs page; repo facts
were fetched from the GitHub API and artefact facts from the Hugging Face
API on 2026-09-12. No figure below comes from memory.

## Admitted items

**E5 (arXiv:2212.03533).** The canonical two-stage recipe: contrastive
pretraining on a curated large-scale weakly-supervised pair set (CCPairs),
then supervised fine-tuning; the paper reports the first zero-shot BEIR
result above BM25 with no labeled data and top MTEB results after
fine-tuning. Take: this pretrain-then-finetune split is the default shape of
every serious recipe below, and the weak-pair curation step is where quality
is decided. Careful: the CCPairs construction cost is the hidden bill --
curating hundreds of millions of filtered pairs is itself a pipeline, and
the paper's numbers assume it. Training code lives in microsoft/unilm
(22213 stars, MIT, pushed 2026-08-26).

**E5-Mistral (arXiv:2401.00368, ACL 2024).** Replaces the billion-pair
weak stage entirely: proprietary-LLM synthetic pairs over hundreds of
thousands of tasks across 93 languages, then standard contrastive
fine-tuning of a decoder-only LLM in under 1k steps, reaching SOTA on BEIR
and MTEB (with labels mixed in for the top result). Take: for MelodyScribe
this is the most transferable recipe -- synthetic pairs plus a short
contrastive run, no CCPairs-scale crawl needed. Careful: the synthetic data
was GPT-4 generated, so reproducing it means depending on a frontier API
(license/cost), and the headline run still fine-tunes a 7B model, not a
sub-2B one.

**LLM2Vec (arXiv:2404.05961).** Three-step decoder-to-encoder conversion:
enable bidirectional attention, masked next-token prediction, then
unsupervised contrastive learning; works with LoRA and needs no labels.
Take: this is the cheapest known path to turn the small generative model
itself into an embedder, and the LoRA compatibility is what makes it fittable
on 16 GB. Careful: the unsupervised contrastive step alone gives a weak
embedder (exactly the anisotropy regime Spike 004 measured); the paper's
strong numbers come with supervised follow-up training. Code:
McGill-NLP/llm2vec (1714 stars, MIT).

**Qwen3-Embedding (arXiv:2506.05176).** Multi-stage unsupervised
pretraining plus supervised fine-tuning on Qwen3 backbones, with explicit
model-merging steps for robustness, covering 0.6B to 8B sizes. Take: the
current best-documented multi-stage recipe at the small end, and the
0.6B artefact (Qwen/Qwen3-Embedding-0.6B, 8.3M downloads, Apache-2.0,
verified) is the distillation target / baseline Spike 006 should compare
against. Careful: the report's compute and data-mix details live in the
full text, not the abstract -- stage costs were not extracted in this lane (see ledger).

**BGE-M3 (arXiv:2402.03216).** Trains dense, multi-vector, and sparse
retrieval heads in one model via self-knowledge distillation, over 100+
languages and up to 8192 tokens. Take: the self-distillation pattern (one
model teaching its own auxiliary heads) is directly reusable for a
MelodyScribe embedder that must serve dense retrieval plus long sections,
and the FlagEmbedding repo (12153 stars, MIT) is the most complete open
training codebase found. Careful: multi-function training adds loss
weighting complexity; verify each head helps before adopting all three.
Artefact BAAI/bge-m3 verified (37.8M downloads, MIT).

**Contriever (arXiv:2112.09118).** Purely unsupervised contrastive
pretraining using inverse-cloze and cropping augmentations. Take: the
floor recipe -- if a new corpus has zero labels and zero budget, this is
the starting point, and its augmentations (crop, ICT) are cheap to copy.
Careful: unsupervised-only models lag supervised ones on BEIR averages;
treat as initialization, not destination. Code:
facebookresearch/contriever (779 stars, license NOASSERTION -- check reuse
terms).

**DPR (arXiv:2004.04906).** The dual-encoder baseline: in-batch negatives
plus one BM25 hard negative per question. Take: every negative-sampling
claim in this lane is measured against this setup; replicate it first as
the control. Careful: one hard negative and in-batch-only sampling is
exactly the regime ANCE and RocketQA show to be deficient. Code:
facebookresearch/DPR (1871 stars, NOASSERTION license).

**ANCE (arXiv:2007.00808).** Diagnoses the train/test mismatch (training
negatives unrepresentative of test-time irrelevants) and fixes it with an
asynchronously refreshed ANN index that mines corpus-representative hard
negatives during training. Take: ANN-mined negatives are the single highest
leverage change over DPR-style sampling; any MelodyScribe trainer should
refresh its negative index during training. Careful: async index refresh
adds infra (periodic re-encoding of the corpus) that a 20-document rig does
not need but a real corpus does. Code: microsoft/ANCE (389 stars, MIT).

**SimCSE (arXiv:2104.08821, EMNLP 2021).** Dropout as the only augmentation
for unsupervised positives; NLI entailment/contradiction pairs for the
supervised variant. Take: the cheapest positive-construction trick known,
useful for a first contrastive run on Score sections (two forward passes,
different dropout masks). Careful: dropout positives teach uniformity, not
task semantics; grain (query-passage asymmetry) still needs real or
synthetic pairs. Code: princeton-nlp/SimCSE (3652 stars, MIT).

**Sentence-BERT (arXiv:1908.10084).** Siamese/triplet NLI training that made
single-vector sentence embeddings practical. Take: less for the recipe,
more for the tooling -- the sentence-transformers framework (now
huggingface/sentence-transformers, 19092 stars, Apache-2.0, actively pushed)
is the fastest way to run small-embedder contrastive experiments on one
GPU. Careful: NLI-trained siamese models transfer poorly to retrieval
without a retrieval fine-tuning stage.

**NV-Embed (arXiv:2405.17428).** LLM-as-embedder recipe with a latent
attention pooling layer over decoder states plus two-stage curated-data
training on a Mistral base. Take: the latent-attention pooling design is
the most relevant architectural datapoint for Q1's pooling question applied
to decoder states, and the curated two-stage data recipe reinforces E5's
shape. Careful: no public training repo was locatable via GitHub search, so
the recipe must be reimplemented from the paper; and the released weights
(nvidia/NV-Embed-v2, verified) carry a CC-BY-NC-4.0 license -- non-commercial
only, a hard constraint (see security). 

**Gecko (arXiv:2403.20327).** Two-step distillation of LLM knowledge into a
compact retriever: LLM generates diverse synthetic pairs, then retrieves
candidates per query and has the LLM relabel positives and hard negatives.
Take: the closest published analogue to "distill a frontier model into the
small MelodyScribe embedder," including the relabeling step that fixes
noisy synthetic positives. Careful: Google-internal pipeline, no public
training code; the relabeling step doubles LLM API cost, so budget it.

**GPL (arXiv:2112.07577).** Label-free domain adaptation: generate queries
for unlabelled target passages, label them with a cross-encoder, train with
hard negatives. Take: this is the recipe for adapting an embedder to the
Score corpus with zero manual labels -- only raw passages required.
Careful: needs a decent cross-encoder and a query generator; garbage in
(synthetic queries off-distribution) propagates. Code: UKPLab/gpl
(342 stars, Apache-2.0).

**RocketQA (arXiv:2010.08191).** Cross-batch negatives (larger effective
batch without larger GPUs), denoised hard negatives (filtering false
negatives), and data augmentation. Take: two directly portable tricks --
cross-batch sharing for the 16GB batch-size limit, and false-negative
filtering, which matters acutely on small corpora where random negatives
collide with positives. Careful: cross-batch needs multi-GPU or gradient
accumulation engineering in most implementations. Code:
PaddlePaddle/RocketQA (784 stars, Apache-2.0).

**QLoRA (arXiv:2305.14314).** Frozen 4-bit base plus LoRA adapters;
reported 65B fine-tuning on a single 48GB GPU at full 16-bit quality.
Take: the technique that makes contrastive/adapter training of 1-10B
models fit 16 GB -- quantize the MiniCPM-class base, train adapters or a
pooling head. Careful: embedding training does many full forward passes
over long documents; quantization slows training throughput even as it saves
memory, so measure tokens/sec, not just fit. Code: artidoro/qlora
(11013 stars, MIT).

**Promptagator (arXiv:2209.11755).** Few-shot prompted LLM generates
per-task synthetic queries from as few as 8 examples, then trains
task-specific dual-encoders. Take: the minimal-seed synthetic recipe --
eight exemplar query-passage pairs per retrieval intent is an attainable
annotation ask for the Score corpus. Careful: Google-internal FLAN pipeline,
no public code; round-trip consistency filtering (the InPars lesson) is
still required.

**InPars (arXiv:2202.05144).** The original LLM query-generation recipe:
GPT-3 writes a synthetic query per document, consistency-checked, then
standard retriever fine-tuning; v2 and toolkit papers extend it (found via
title search). Take: the consistency filter (keep only pairs where the
source document retrieves well) is the quality gate every synthetic
pipeline here needs. Careful: only a community mirror
(zetaalphavector/InPars, 201 stars) was locatable, not official code;
early versions propagate generator bias unchecked.

**Arctic-Embed (arXiv:2405.05374).** Efficiency-first small-model recipe
with explicit data filtering and long-context handling; five models from
22M to 334M parameters, each reported SOTA-for-size on MTEB Retrieval at
release, weights Apache-2.0. Take: the existence proof that sub-0.5B models
reach competitive retrieval with the right data recipe rather than scale,
and the parameter range brackets MelodyScribe's 0.3-2B target. Careful:
retrieval-only tuning; clustering/classification transfer needs checking.
Code: Snowflake-Labs/arctic-embed (91 stars, Apache-2.0).

**TAS-B (arXiv:2104.06967, SIGIR 2021).** Topic-aware balanced sampling
plus MarginMSE distillation from a cross-encoder teacher into a 6-layer
DistilBERT student -- efficient end-to-end (train, index, query). Take:
the complete "distill into small" template (balanced sampling avoids topic
collapse; MarginMSE transfers graded relevance, not just ranks), directly
shaped for a small MelodyScribe student. Careful: repo is small and stale
(sebastian-hofstaetter/tas-balanced-dense-retrieval, 60 stars, last push
2021); reimplement in sentence-transformers rather than reviving it.

**PROD (arXiv:2209.13335).** Progressive distillation: a stronger teacher
can produce a worse student through the capacity gap, so the teacher signal
is introduced progressively. Take: calibrates distillation expectations
for Spike 006 -- distilling Qwen3-Embedding-scale teachers into a 0.6B
student may underperform distilling a mid-size teacher; test both.
Careful: no public code located; method must be reimplemented.

## Refutations

1. "In-batch negatives are sufficient." Refuted by ANCE (arXiv:2007.00808):
training negatives must represent test-time irrelevants; ANN-mined hard
negatives, not in-batch samples, close the gap.
2. "A better teacher always distills a better student." Refuted by PROD
(arXiv:2209.13335): the teacher-student capacity gap means a stronger
teacher can yield a worse student; progression is required.
3. "Top embedders require billion-pair weak-supervision pipelines."
Qualified by E5-Mistral (arXiv:2401.00368): synthetic-only data with under
1k contrastive steps reaches SOTA; the pipeline is replaceable, though the
frontier-API dependency is not.
4. "LLM embedders require full fine-tuning." Qualified by LLM2Vec
(arXiv:2404.05961, LoRA-compatible conversion) and QLoRA
(arXiv:2305.14314, 4-bit plus adapters at 16-bit quality): adapter training
suffices, which is what fits 16 GB.

## Unresolved ledger

- GTE (arXiv:2308.03281): verified relevant via arXiv API; not admitted
under lane budget, subsumed by E5/Qwen3-Embedding two-stage coverage.
- Nomic-Embed (arXiv:2402.01613): verified relevant; not admitted, long-input
coverage subsumed by BGE-M3.
- AnglE (arXiv:2309.12871): verified relevant; objective variant,
deprioritized under lane budget.
- Doc2Query (arXiv:1904.08375): abs verified; mechanism covered by admitted
synthetic items; repo castorini/docTTTTTquery (376 stars, Apache-2.0).
- LoRA (arXiv:2106.09685): abs verified; covered via admitted QLoRA; repo
microsoft/LoRA (13789 stars, MIT).
- InfoNCE/CPC (arXiv:1807.03748): abs verified; objective background only,
no recipe; no official code.
- PairDistill (arXiv:2410.01383), CL-Distill (arXiv:2204.13679), BiXSE
(arXiv:2508.06781): screened via arXiv API title search only; abs pages not
opened under lane budget. Pairwise and curriculum distillation variants
remain unexamined.
- Per-stage compute (GPU-hours, batch sizes, temperatures, steps) for
Qwen3-Embedding, BGE-M3, NV-Embed, Gecko, Arctic-Embed: not extracted --
abstracts do not carry them, no PDF text toolchain was available in the
lane sandbox, and reading 20 full texts exceeds the lane budget. The
downloaded PDFs in papers/ are the input for that pass.
- Instruction-tuning ablations for embedders (E5-instruct, NV-Embed
instructions): surfaced as relevant but belong to Lane 5's instruction
scope; not duplicated here.
- Semantic Scholar citation chaining was throttled (429 after one successful
call); forward-chaining from seed papers is incomplete.

## Security findings (requirements)

1. Do not train on or redistribute weights with non-commercial terms without
a license decision: nvidia/NV-Embed-v2 is CC-BY-NC-4.0 (verified via HF
API). Requirement: any recipe touching NV-Embed weights needs explicit
approval and must not ship in commercial artefacts.
2. Synthetic data from proprietary LLM APIs (the E5-Mistral/Gecko pattern)
inherits the provider's terms on generated data. Requirement: record the
generator model, date, and terms for every synthetic pair set; prefer
self-hosted open generators for data that must stay unencumbered.
3. GPL-style adaptation on the Score corpus sends passages to whatever
model generates queries. Requirement: run generators locally for private
corpora; no Score text to third-party APIs without approval.
4. Contriever/DPR repos report license NOASSERTION via the GitHub API.
Requirement: treat as unlicensed for reuse until clarified; prefer MIT or
Apache-2.0 codebases (FlagEmbedding, sentence-transformers, unilm, ANCE).
