# Lane 1 findings: Embedding model architectures

Scope: bi-encoders from encoders and decoders, pooling, bidirectional conversion,
Matryoshka representations, multi-vector late interaction (ColBERT), learned sparse
(SPLADE), inference cost, and which architectures top MTEB / MMTEB / BEIR.
All figures below come from the fetched arXiv abs pages (titles, authors, abstracts)
and fetched GitHub API repo metadata recorded in `inventory.tsv`. No PDF was read
beyond a title spot-check; no leaderboard page was opened (see ledger).

## (a) Admitted items

**Sentence-BERT (1908.10084).** Siamese/triplet fine-tuning of BERT that makes
sentence vectors directly comparable with cosine similarity; the paper reports
cutting the 10k-sentence nearest-pair search from ~50M BERT inferences (~65 hours)
to seconds. Take: this is the reference single-vector bi-encoder design and the
cheapest baseline any MelodyScribe embedder must beat. Careful: it is an
encoder-only recipe from 2019; its pooling (mean) and scale predate every
decoder-based result below, so use it as a floor, not a target.

**DPR (2004.04906).** A simple dual-encoder that learns dense passage vectors and,
per its abstract, beats a strong Lucene-BM25 system by 9-19 absolute points on
top-20 retrieval accuracy across open-domain QA sets (venue: EMNLP 2020, confirmed
on the abs page). Take: proof that a plain bi-encoder with the right training pairs
beats sparse GMTOu_N47 on retrieval; the architecture did not need to be exotic.
Careful: DPR is trained per-domain with question-passage pairs, so its numbers do
not transfer to zero-shot general embedding; the BEIR-era work exists precisely
because DPR-style models generalized poorly.

**ColBERT (2004.12832).** Late interaction: query and document are encoded
independently with BERT, then a cheap MaxSim token-level interaction scores them,
avoiding per-pair transformer passes (repo: stanford-futuredata/ColBERT, 3932
stars, MIT). Take: the canonical multi-vector architecture and the inference-cost
reference point — encode once, interact cheaply at query time. Careful: token
vectors inflate the index by an order of magnitude versus single-vector models;
that storage/latency bill is exactly what ColBERTv2 addresses next.

**SPLADE v2 (2109.10086).** Learned sparse expansion over the MLM vocabulary head
with FLOPS regularization, retrievable with a standard inverted index
(repo: naver/splade, 1011 stars). Take: the sparse complement to dense vectors —
exact lexical match plus learned expansion, cheap to serve on CPU infrastructure.
Careful: sparsity/regularization trade-offs need tuning per corpus, and its
BEIR-era wins are retrieval-specific, not general-embedding wins.

**ColBERTv2 (2112.01488).** Adds aggressive residual compression and denoised
supervision to late interaction, reporting state-of-the-art quality in and out of
domain at a much smaller space footprint. Take: the fix for ColBERT's index-size
problem and the template for sizing a MelodyScribe vector store if token-level
vectors are ever kept. Careful: compression always trades a little recall for a
lot of bytes — measure that curve on the private corpus rather than trusting the
paper's operating point.

**Matryoshka Representation Learning (2205.13147).** Trains nested coarse-to-fine
vectors so one embedding can be truncated (e.g. to 1/2, 1/4, 1/8 dims) at query
time with no retraining and minimal quality loss. Take: the single highest-leverage
trick for MelodyScribe storage and QPS — train once at full width, serve truncated
widths per latency budget. Careful: the quality-vs-dims curve is model- and
task-dependent; the truncation schedule must be calibrated on the private eval,
not copied.

**MTEB (2210.07316).** 58 datasets across 8 task types with 33 models benchmarked;
headline finding: no single embedding method dominates all tasks. Take: this is the
operational definition of "best" the brief asks about, and it already warns that
top-of-retrieval is not top-of-everything. Careful: MTEB scores saturate and are
gamed by instruction/prompt fitting; a private-corpus eval (lane 6) still decides.

**E5 (2212.03533).** Weakly-supervised contrastive pretraining on curated CCPairs;
per its abstract the first model to beat BM25 zero-shot on BEIR without labeled
data, and the best MTEB result at the time against models with 40x more parameters
when fine-tuned. Take: the two-stage recipe (weak pretrain, supervised finetune)
that every later recipe, including Qwen3-Embedding, inherits. Careful: CCPairs is a
web-mined resource whose replication cost is the real budget item, not the GPU
steps.

**E5-Mistral (2401.00368).** Fine-tunes a decoder-only LLM into an embedder using
only synthetic data and under 1k training steps, no labels, across 93 languages.
Take: the minimal decoder-embedder recipe — last-token pooling, standard
contrastive loss, tiny step count — and therefore the closest public template for
a one-GPU MelodyScribe run. Careful: "under 1k steps" hides the proprietary-LLM
synthetic-data generation cost and the large batch sizes those steps assume.

**BGE-M3 (2402.03216).** One model serving dense, multi-vector, and sparse
retrieval over 100+ languages and up to 8192 tokens, with self-knowledge
distillation across the three heads (repo: FlagOpen/FlagEmbedding, 12153 stars,
MIT). Take: the existence proof that one backbone can host all three retrieval
functionalities with cross-head distillation, plus a native 8k-context design.
Careful: three heads means three index paths to serve; versatility is not free at
query time.

**GritLM (2402.09906).** Generative Representational Instruction Tuning: one LLM
trained jointly for generation and embedding, switched by instruction; GritLM 7B
set open-model SOTA on MTEB while matching generative baselines, and the paper
states GRIT matches single-mode training (no loss to either side)
(repo: ContextualAI/gritlm, 700 stars, MIT). Take: the direct precedent for one
MelodyScribe model doing both jobs — unification cost ~zero at 7B. Careful: the
"no loss" claim is at 7B with full joint training; whether it holds at 0.3-2B or
with embedding-only adapters is unmeasured here (lane 4's question).

**Echo embeddings (2402.15449).** Repeating the input inside the prompt gives
causal-LM tokens access to the full context, yielding +5% zero-shot over classical
LM embeddings with no architecture change and no training, nearly matching
bidirectionally-converted models. Take: the cheapest decoder-to-embedder
conversion known, and direct evidence that prompt/marker design (repeat-then-read)
moves embedding quality several points — the mechanism behind any `[EMB]`-marker
scheme. Careful: echo doubles the effective sequence length (KV/time cost), and
supervised fine-tuning still beats it; it is a floor for training-free states,
not a replacement for training.

**LLM2Vec (2404.05961).** Three steps — enable bidirectional attention, masked
next-token pretraining, unsupervised contrastive tuning — applied to 4 LLMs from
1.3B to 8B, reaching unsupervised SOTA on MTEB (repo: McGill-NLP/llm2vec, 1714
stars, MIT). Take: the canonical cheap recipe for converting a small generative
model into an encoder, with the 1.3B endpoint inside the MelodyScribe band.
Careful: bidirectional attention breaks KV-cache reuse assumptions of the
generative path, so a converted model may not serve both roles in one pass
without the adapter/merge machinery of lane 4.

**NV-Embed (2405.17428).** Reports that a latent-attention pooling layer
consistently beats mean pooling and last-`<EOS>`-token pooling, removes the causal
mask during contrastive training, and uses two-stage contrastive
instruction-tuning. Take: the pooling verdict — do not default to last-token;
a small learned pooling head is worth more than extra backbone. Careful: no
official training repo was found (weights-only release posture), so the recipe is
paper-described, not code-verified; and latent attention adds parameters that
must be trained, contra the brief's ridge-head warning.

**MMTEB (2502.13595).** 500+ quality-controlled tasks across 250+ languages,
adding instruction-following, long-document, and code retrieval; finds
billion-parameter LLM embedders lead only on some languages. Take: the current
multilingual definition of "best" and the source of long-doc/instruction task
coverage MTEB lacks. Careful: at 500+ tasks it is an evaluation project, not a
tuning loop — far too heavy to run per-iteration on one GPU.

**Qwen3-Embedding (2506.05176).** 0.6B/4B/8B series on Qwen3 backbones:
large-scale unsupervised pretraining plus supervised fine-tuning on
model-synthesized multi-domain data, with model merging for robustness
(repo: QwenLM/Qwen3-Embedding, 2030 stars, license not stated via API). Take:
the in-band recipe — the 0.6B endpoint sits in the MelodyScribe size range, and
the pretrain-then-finetune-plus-merge pipeline is the current top-tier template
to copy stage by stage. Careful: the data engine (Qwen3-synthesized pairs) and
the merge recipe's ablations are the load-bearing details this lane did not
extract from the PDF; lane 2 must read them before costing the run.

## (b) Refutations

- "One architecture is best at everything." Refuted by MTEB (2210.07316): "no
  particular text embedding method dominates across all tasks."
- "A decoder must be made bidirectional to embed well." Challenged by echo
  embeddings (2402.15449): repetition matches bidirectionally-converted models
  without changing the architecture.
- "One model cannot embed and generate without losing something." Refuted at 7B
  by GritLM (2402.09906): joint GRIT training "matches training on only
  generative or embedding data."
- "Last-token state is an adequate embedding readout." Challenged by NV-Embed
  (2405.17428): latent-attention pooling "consistently improves" over mean
  pooling and last-`<EOS>` pooling. (Supports the brief's spike-004 suspicion
  that the untrained last-token state is the problem, not the hidden size.)
- "bigger is required for top-tier." Qualified by E5 (2212.03533): best MTEB
  results against models with 40x more parameters; and by Qwen3-Embedding
  (2506.05176), which fields a competitive 0.6B endpoint.

## (c) Unresolved ledger

- Current MTEB/MMTEB/BEIR top-table numbers: not fetched. No leaderboard page
  (MTEB leaderboard, Papers with Code) was opened; all figures above are
  vendor-reported abstracts. Reason: abs-page-first strategy consumed the
  budget; leaderboard scraping is future work for the integrator.
- BEIR paper identity: three guessed arXiv ids from memory resolved to unrelated
  papers on fetch (2104.08671 = law pretraining; 2310.01730 = compact-object
  physics; 2402.13840 = session recommendation). Reason: ids recalled, not
  fetched; recorded as abstains. BEIR coverage comes only via E5/MTEB abstracts.
- GTE paper id: unresolved (same wrong-id cause); GTE-line coverage deferred to
  Qwen3-Embedding (its self-described successor series).
- ANCE (2007.00808), ModernBERT (2412.13663), Nomic (2402.01613), Jina-v2
  (2310.19923), C-Pack (2309.07597): abs pages verified but not admitted.
  Reason: training-recipe (ANCE), deprioritized-vs-admits (the rest); details in
  inventory.tsv reasons.
- Per-architecture inference-cost numbers (FLOPs, latency, bytes/vector):
  not extracted — only abstracts were read, and abstracts rarely carry them.
  The PDFs on disk contain them; someone must read them.
- NV-Embed training code and Qwen3-Embedding license: no official training repo
  found for NV-Embed via GitHub search; Qwen3-Embedding repo license field
  returned null from the API. Reason: search-API limits; needs a human click.

## (d) Security findings

None. This lane fetched only public metadata (arXiv abs pages, GitHub search/API
records) and PDF bytes; no code was executed, no model was run, no credentials
were used. Requirement for downstream lanes: treat downloaded PDFs as untrusted
bytes (do not execute embedded content; view with a plain reader).
