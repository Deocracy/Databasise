# Lane 3 findings: Small embedders and distillation into them

Scope: best 0.1B–0.6B embedders with independent results, what made them good,
distillation of large embedders into small ones, long-document behaviour.
15 admitted (all opened at the primary source), 6 abstained. Full table in
`inventory.tsv`; PDFs in `papers/`.

## (a) Admitted items

**Qwen3-Embedding (2506.05176).** Decoder-based embedding family at 0.6B/4B/8B
built on the Qwen3 LLMs, Apache-2.0, with the 0.6B checkpoint at 8.3M HF
downloads (Qwen/Qwen3-Embedding-0.6B). Training is multi-stage (large
unsupervised pretraining, supervised fine-tuning on high-quality data, model
merging), the loss is an improved InfoNCE with in-batch queries and documents
as extra negatives plus K mined hard negatives and an explicit false-negative
mask, and the LLMs themselves synthesize diverse multilingual training data.
Take: this is the closest public recipe to a 0.6B dense embedder at
MelodyScribe scale — copy the loss (hard negatives + false-negative masking),
the two-stage schedule, and the synthetic-data flywheel. Careful: the 0.6B
still inherits a decoder backbone (inference cost well above a 30M BERT), and
reported SOTA numbers are vendor-reported.

**BGE-M3 (2402.03216).** Single model doing dense, multi-vector, and sparse
retrieval over 100+ languages and up to 8192 tokens, trained with
self-knowledge distillation (relevance scores from the three functionalities
teach each other) and a batching strategy for very large batches. Code is MIT
(FlagOpen/FlagEmbedding, 12153 stars). Take: self-KD across heads is the
mechanism to copy if MelodyScribe wants one trunk serving vector and
(keyword) sparse paths; the 8k-token handling is the long-section precedent.
Careful: M3's base size is far above 0.6B, so transfer the mechanism, not the
checkpoint.

**Nomic Embed (2402.01613).** nomic-embed-text-v1, 136.7M params (verified via
HF safetensors metadata), 8192-token context, fully reproducible (weights,
code, and curated data, Apache-2.0; nomic-ai/contrastors, 802 stars), accepted
to TMLR. Take: the only small long-context recipe where every artefact is
open — replicate it first on the rig before inventing anything. Careful:
English-focused; multilingual needs came later (v2/MoE line).

**Gecko (2403.20327).** Canonical LLM-to-small distillation: a 1.2B
transformer (Gecko-1B, 768d) trained in two stages where an LLM first
generates diverse synthetic query–passage pairs and then retrieves candidates
and relabels positives and hard negatives; result MTEB average 66.31, and its
256d variant beats all 768d entries. Take: the two-step
(generate-then-relabel) distillation pattern plus MRL-style short vectors is
the quality-per-byte winner. Careful: no public weights — distill the method,
not the model.

**MRL (2205.13147).** Matryoshka Representation Learning nests coarse-to-fine
information in one vector: up to 14x smaller embeddings at the same accuracy,
14x retrieval speedups, ~2% long-tail few-shot gains, no inference overhead
(RAIVNLab/MRL, MIT, 658 stars). Take: train every MelodyScribe embedding
matryoshka-style so vectors can be truncated at query time (fits lane 10's
quantization story). Careful: gains are retrieval-measured; verify truncation
holds on our corpus (spike 004's anisotropy is exactly what MRL does not fix
by itself).

**jina-embeddings-v3 (2409.10173).** 570M params, 8192 tokens, with
task-specific LoRA adapters for retrieval/clustering/classification/matching;
vendor-reports beating OpenAI/Cohere on English and multilingual-e5-large on
multilingual. Weights are CC-BY-NC-4.0 (non-commercial). Take: the task-LoRA
pattern maps directly onto query-side vs document-side prefixes (lane 5) —
one trunk, cheap asymmetric adapters. Careful: NC license excludes product
use; no official training repo found, so the recipe is paper-only.

**E5-Mistral (2401.00368).** Decoder-to-embedder with synthetic data only and
under 1k training steps: LLM-generated tasks across 93 languages, then
fine-tune an open decoder — no multi-stage weakly-supervised pipeline needed.
Take: this is the cheapest proven path to convert a small generative model
into an embedder, and the direct answer to spike 004's missing-pairs problem.
Careful: result quality leans entirely on the generator LLM's diversity; a 2B
self-distillation loop can collapse without the relabel/filter step Gecko adds.

**Nomic MoE (2502.07972).** Sparse mixture-of-experts text embedders aimed at
RAG ingestion/latency limits: capacity without proportional inference cost.
Take: the fallback if a dense 0.6B underfits — MoE buys headroom inside one
16 GB card. Careful: 2025 paper, ecosystem (serving, merging) thinner than
dense; treat as option, not default.

**E5 (2212.03533).** The foundational small-model recipe: 1.3B noisy pairs
consistency-filtered to ~270M (CCPairs), contrastive pretraining at batch
32,768 for 20k steps (AdamW, LR 3/2/1e-4 for small/base/large from
MiniLM/BERT inits), then supervised fine-tuning. Take: the two-stage template
(weak pretrain → supervised fine-tune) behind bge-small-class models, with
batch size doing most of the work. Careful: replicate the filtering, not just
the loss — noisy pairs without consistency filtering waste the stage.

**SBERT (1908.10084).** Siamese bi-encoder over BERT (Reimers & Gurevych) that
made sub-second sentence retrieval practical; every 0.1–0.6B bi-encoder
descends from it, and the sentence-transformers stack (19092 stars,
Apache-2.0) is its maintained home. Take: architectural and code baseline;
start any 0.1B experiment here. Careful: 2019 negatives/pooling predate hard
negatives, MRL, and instruction conditioning — baseline only.

**EmbeddingGemma (2509.20354).** 300M decoder-family embedder (Gemma 3 based):
encoder-decoder initialization plus geometric embedding distillation from
larger models, spread-out regularizer, checkpoint merging over data mixtures;
vendor-reported SOTA under 500M params. Take: the single closest public
analogue to MelodyScribe's one-small-model goal — read this first, and test
whether its distillation/merging recipe ports to a 1–2B generative host
(spike 006 input). Careful: Gemma license, vendor numbers, September 2025 —
independent replication is thin.

**Arctic-Embed (2405.05374).** Five models from 22M to 334M (Apache-2.0),
each SOTA-for-size on MTEB Retrieval at release, with the paper's value in the
data recipe and ablations rather than architecture. Take: the small-model data
playbook (sources, filtering, curricula) for the 22–300M band. Careful:
retrieval-benchmark SOTA ≠ our corpus; re-run the ablations that matter
(source mix, negatives) on Score sections.

**Granite Embedding (2502.20204).** Encoder family with 12-layer models and
6-layer distilled counterparts: retrieval-oriented pretraining, contrastive
fine-tuning, KD, and model merging; Apache-2.0 weights
(ibm-granite/granite-embedding-125m-english). Take: proof that a 6-layer
(~125M) distilled model stays competitive — the floor for "how small can the
embedder be". Careful: enterprise-retrieval evaluation; confirm on
general/BEIR-style tasks before adopting the recipe wholesale.

**C-Pack (2309.07597).** BGE-family training resources (data, small-model
baselines, C-MTEB) from the same team behind bge-small. Take: how the most
downloaded small embedder (64M downloads, MIT) was actually packaged and
evaluated. Careful: Chinese-embedding focus; the English bge-small recipe is
informed by it, not contained in it.

**Data clustering for pretraining (2407.18887).** Snowflake's Merrick shows
embedding-and-clustering the pretraining data improves contrastive learning
(cluster-aware sampling). Take: a data-curation lever that costs no
parameters — apply to Score-derived pairs before scaling GPUs. Careful:
single-lab result; treat as an ablation to re-run, not a law.

## (b) Refutations

1. **"2506.07900 is the MiniCPM embedding reference."** Refuted by the primary
   source: 2506.07900 is *MiniCPM4, an efficient end-side generative LLM*,
   not an embedding paper. MiniCPM-Embedding itself (openbmb, Apache-2.0) has
   no linked paper on its verified HF card. Do not cite 2506.07900 as an
   embedding recipe.
2. **"Contrastive training is blocked for lack of labelled query–passage
   pairs" (spike 004 rationale).** Refuted by E5-Mistral (2401.00368,
   purely synthetic data, <1k steps) and Gecko (2403.20327, LLM
   generate-then-relabel): synthetic pairs are the established substitute.
   The blocker is generator diversity and filtering, not labels.
3. **Vendor tables as independent results.** Qwen3, jina-v3, Arctic, and
   EmbeddingGemma MTEB/BEIR claims are vendor-reported (primary only for
   "what the vendor reports"). None is treated here as an independent
   replication; the one independent anchor is spike 004's own measurement
   (Qwen3-Embedding-0.6B gold MRR 1.00 on our corpus).

## (c) Unresolved ledger

- **MiniCPM-Embedding method**: no paper, no recipe doc found; HF card only.
  Reason: OpenBMB never published the training report. (Secondary-only.)
- **model2vec paper**: repo verified (MinishLab/model2vec, 2205 stars, MIT,
  pushed 2026-09-12) but no paper id verified before write-up. Reason: paper
  id never confirmed against a primary source; static-distillation claims
  need it.
- **GTE and Contriever paper ids**: not verified (early id guesses 2308.11528
  and 2112.09118 returned zero entries — recorded as failed probes, not
  candidates). Reason: API rate limits ended the search window.
- **Per-model MTEB/BEIR numbers**: not re-fetched from the leaderboard;
  figures above are paper/abstract-reported. Reason: leaderboard fetch
  deferred to the integrator (lane 6 owns evaluation).
- **Compute cost per stage (GPU-hours)**: mostly absent from the papers
  surveyed (steps and batch sizes recorded where stated, e.g. E5 20k steps at
  batch 32k). Reason: papers rarely report it; Nomic's reproducibility
  artefacts are the best proxy.
- **Long-document specifics (LoCo scores, chunking vs 8k native)**: abstracts
  confirm 8k support (Nomic, BGE-M3, jina-v3) but score tables were not
  extracted. Reason: PDF text tooling unavailable in the lane environment;
  tables need a follow-up pass.

## (d) Security findings (requirements)

- **Checkpoint supply chain**: pin every admitted checkpoint by commit hash
  and verify safetensors hashes on download (all 15 PDFs are content-hashed
  by arXiv id; do the same for weights). No pickle-format weights.
- **License gates**: jina-embeddings-v3 weights are CC-BY-NC-4.0 (no
  commercial use); EmbeddingGemma weights carry the Gemma license; the rest
  of the admitted small-model weights are Apache-2.0/MIT. Enforce the gate in
  the artifact table before any product embedding ships.
- **Synthetic-data provenance**: Gecko/E5-Mistral-style generation inherits
  the generator's biases and PII risk; log generator, prompt, and filter
  version per training pair (ties to Proof's evidence-quote validator).
- No prompt-injection or remote-execution surface was found in this lane's
  artefacts (papers, weights, Apache/MIT training code).
