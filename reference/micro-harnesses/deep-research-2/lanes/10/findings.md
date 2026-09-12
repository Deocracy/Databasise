# Lane 10 findings: High-speed retrieval and vector storage

Screened 37, admitted 23 (18 papers with PDFs in `papers/`, 5 code artefacts).
All figures below were read out of the admitted PDFs or the live GitHub/HF API
responses recorded in `inventory.tsv`; venue claims appear only where the arXiv
abs page or the PDF itself states them.

## (a) Admitted items

**HNSW (arXiv 1603.09320).** Multi-layer proximity-graph index: each element
enters a random max layer (exponentially decaying distribution, skip-list-like),
links are separated by distance scale, and a neighbor-selection heuristic keeps
recall high on clustered data. What to take: this is the default in-memory
index for MelodyScribe — hnswlib/FAISS-HNSW need no coarse quantizer, give
logarithmic scaling, and are the high-recall winners in ANN-Benchmarks.
Caution: build is slow on hard distributions, and the paper's wins are on
SIFT/GloVe/CoPhIR-class data (brute-force baselines 22–590 ms in-paper), not
on text embeddings; re-measure on our vectors before assuming dominance.

**Faiss GPU / billion-scale search (arXiv 1702.08734).** k-selection at 55% of
theoretical peak, an 8.5x-faster-than-prior GPU nearest-neighbor path, plus
GPU-native brute-force, IVF, and product-quantized compressed-domain search;
k-NN graph over 95M YFCC images in 35 minutes and 1B vectors in under 12 hours
on 4 Maxwell Titan X. What to take: if the corpus ever needs a GPU pass
(index build, re-ranking candidate generation, batch embedding search), this is
the design and the library (facebookresearch/faiss, MIT, ~40.9k stars, active).
Caution: numbers are Maxwell-era; treat them as architecture evidence (fused
k-selection, tiled PQ tables), not as current latency promises.

**ANN-Benchmarks (arXiv 1807.05614).** The recall-vs-QPS harness plus the
finding that "very different approaches yield comparable quality-performance
trade-offs". What to take: adopt its protocol (fixed-recall QPS plots, index
size normalized by QPS) for Spike 010 instead of inventing a harness, and reuse
the repo (erikbern/ann-benchmarks, MIT). Caution: the paper's headline
conclusion cuts against any "one index wins" story — see Refutations.

**ScaNN / anisotropic quantization (arXiv 1908.10396).** For MIPS, penalize the
residual's query-parallel component more than the orthogonal one instead of
minimizing raw reconstruction error; SOTA on the ann-benchmarks public suites
at the time, with open-source implementation. What to take: when MelodyScribe
retrieves by cosine/inner-product over trained embeddings, an anisotropic PQ
code beats vanilla PQ at the same byte budget — this is the quantization to try
first for compressed storage. Caution: gains assume query distribution known at
train time; shifting query style (self-queries vs gold queries in Spike 004)
can erode them.

**DPR (arXiv 2004.04906).** Dual-encoder dense retrieval beating a strong
Lucene BM25 by 9–19 absolute points in top-20 accuracy and driving SOTA
end-to-end QA. What to take: the floor a MelodyScribe embedder must clear, and
the simplest architecture that counts as "trained embedder" in head-to-heads
against decoder states. Caution: DPR alone is dated; the paper's own ablations
say training ingredients (batch size, negatives) matter more than framework
complexity — do not read it as an architecture recommendation.

**ColBERT (arXiv 2004.12832, SIGIR 2020 per abs page).** Query/document token
matrices with MaxSim late interaction: 170x faster and 14,000x fewer
FLOPs/query than BERT cross-encoders at up to 36% MRR@10 (MS MARCO), plus full
end-to-end retrieval off the token index. What to take: the quality ceiling for
first-stage retrieval when storage allows per-token vectors. Caution: footprint
is an order of magnitude above single-vector (the paper's own Figure 1 trades
latency log-scale against MRR) — only admissible with ColBERTv2 compression.

**monoT5 (arXiv 2003.06713).** Relevance as generated target words ("true" /
"false") with logits as scores: T5-base 0.363, T5-large 0.383 MRR@10 on MS
MARCO, plus zero-shot transfer on Robust04 and a clear edge in the data-poor
regime. What to take: the template for a generative reranker, and evidence that
small-data reranking works — relevant if MelodyScribe reranks with few labels.
Caution: scores are 2020-era and scale with model size (3B ≈ 0.382); a 0.3B
reranker needs distillation, not this recipe raw.

**MiniLM (arXiv 2002.10957).** Distill the teacher's last-layer self-attention
distributions plus value-relation into any-size student (teacher assistant for
large gaps): 6-layer/768-dim student 2.0x faster at >99% of BERT-base on SQuAD
2.0/GLUE; 12x384 student 2.7x speedup, competitive. What to take: the recipe
for 0.3B-class cross-encoder rerankers (the ms-marco-MiniLM-L-6-v2 pattern) and
for distilling any large ranker into the latency budget. Caution: results are
on GLUE/SQuAD, not ranking; ranking transfer must be measured, not assumed.

**ANCE (arXiv 2007.00808).** In-batch negatives give diminishing gradients, so
mine hard negatives globally from an asynchronously refreshed ANN index; ANCE
dot-product retrieval "nearly matches" a BERT cascade at "100x" efficiency.
What to take: the negative-mining loop for training the MelodyScribe embedder
(lane 2 executes, this is the design reference), and proof that first-stage
retrieval can approach cascade quality. Caution: async index refresh is
fiddly infrastructure (stale negatives, refresh schedule in their Table settings);
"100x" is vs. their cascade, not vs. all rerankers.

**SPLADEv2 (arXiv 2109.10086).** Max pooling over the MLM head plus standard
distillation: ~+2 MRR@10/NDCG@10 over SPLADE, near-SOTA on MS MARCO/TREC DL
2019, and "clearly outperforming recent dense models on zero-shot evaluation"
(BEIR subset), with controllable FLOPs (0.35 MRR at ~0.3 FLOPS, 0.368 at ~4).
What to take: the sparse arm of hybrid retrieval that runs on a plain inverted
index — no ANN library, no GPU, tiny ops footprint, best zero-shot in this
lane. Caution: efficiency claims are FLOPs-based; real latency depends on the
inverted-index implementation and avg. document expansion length.

**SPANN (arXiv 2111.08566, NeurIPS 2021 per abs page).** Memory-disk hybrid on
the inverted-index methodology (centroids in RAM, posting lists on SSD,
hierarchical balanced clustering + closure augmentation + query-aware dynamic
pruning): 2x faster than DiskANN at equal recall/memory on three billion-scale
sets, ~1 ms at 90% recall@1/10 with 32 GB RAM. What to take: the scaling path
when the corpus outgrows RAM — beats keeping a lossy in-memory compressed
index (the paper shows IVF-PQ recall@1 collapsing to ~60% under 64 GB for 1B
128-dim vectors). Caution: their headline compares against DiskANN on
Microsoft hardware/datasets (SIFT1B, SPACEV1B, DEEP1B); replicate on our data
before choosing it over DiskANN.

**ColBERTv2 (arXiv 2112.01488).** Residual compression (cluster centroids +
quantized residuals) cuts late-interaction footprint 6–10x; 2-bit codes keep
vanilla quality (36.2% MRR@10, 82.3% Recall@50 on MS MARCO) and 1-bit keeps
35.5%; cross-encoder distillation gives 40.8% MRR@10 and SOTA on 28 datasets
in/out of domain. What to take: compression and supervision are separable wins
— apply residual compression to any token index and distill the reranker into
the retriever. Caution: centroid tables + 4.5 GiB inverted list overheads are
included in their ratio; small-corpus math differs.

**PLAID (arXiv 2205.09707).** Centroid-interaction + centroid-pruning engine
over ColBERTv2: 2.5–6.8x GPU and 9.2–45x CPU speedups with no quality loss
(12.9–22.6x GPU / 86–145x CPU with minimal loss), tens of ms on GPU at 140M
passages, within 1.6x of SPLADEv2 latency at higher quality. What to take: the
serving design that makes late interaction CPU-viable on one box — this is the
closest published answer to "expensive retrieval on consumer hardware".
Caution: needs custom kernels (padding-free MaxSim, residual decompression)
and centroid-index tuning; not an off-the-shelf pip install.

**MRL (arXiv 2205.13147).** Nested "matryoshka" training so the first d dims
are as good as an independently trained d-dim model: 14x smaller embeddings at
equal ImageNet accuracy, funnel (adaptive) retrieval 14x wall-clock faster via
HNSW at equal mAP@10, ~128x FLOP savings. What to take: train the MelodyScribe
embedding dim nested once, then truncate per query budget at serve time —
directly applicable to Qwen3-Embedding-0.6B dims and to Spike 004's anisotropy
problem (trained nested dims, not post-hoc slicing). Caution: evidence is
vision + ALIGN/BERT; text-retrieval transfer of the 14x figure is plausible but
not shown in-paper — measure on BEIR-style eval, not ImageNet.

**RankT5 (arXiv 2210.10634).** Encoder-decoder and encoder-only T5 rankers
trained with pairwise/listwise losses: +1.8% MRR@10 over monoT5 on MS MARCO,
+2.8% on NQ, with better zero-shot out-of-domain under listwise losses.
What to take: if we train any reranker, use ranking losses not pointwise
cross-entropy, and consider the encoder-only variant for latency. Caution:
experiments use T5-base and up; no 0.3B-class latency story in-paper — combine
with MiniLM-style distillation for serving.

**XTR (arXiv 2304.01982).** Train token retrieval itself (retrieve top document
tokens first), then score only retrieved tokens: +2.8 nDCG@10 on BEIR with no
distillation, +3.6 over GTR dual-encoder, scoring stage 4000x fewer FLOPs than
ColBERT. What to take: the cheapest multi-vector design and the best zero-shot
number in this lane — if MelodyScribe stores token vectors, XTR's objective is
the one to copy. Caution: MS MARCO-trained English-centric (authors flag the
dependency); multilingual/private-corpus transfer is future work per their
Limitations.

**BGE-M3 (arXiv 2402.03216).** One model, three functionalities (dense +
sparse + multi-vector) via self-knowledge distillation across them, 100+
languages, up to 8192 tokens; MLDR-long-doc and MIRACL SOTA-class, NarrativeQA
61.7 nDCG@10 at full length. What to take: (1) hybrid fusion can live inside
one model instead of three pipelines; (2) functionality-distillation improves
each arm — a template for distilling MelodyScribe's embedder; (3) 8k-token
handling is a solved data/batching problem, not a research project. Caution:
their limits section admits untested generalization, long-doc efficiency gaps,
and uneven language coverage — verify before trusting a single-model hybrid.

**RAPTOR (arXiv 2401.18059, ICLR 2024 per PDF).** Recursive
cluster-summarize tree over chunks; collapsed-tree retrieval with SBERT/BM25/
DPR each beats its flat counterpart; clustering beats contiguous-chunk trees
(56.6% ablation); linear build cost in tokens. What to take: the query-time
graph+vector fusion pattern for MelodyScribe Folios — summaries are just
higher tree nodes, any retriever works over them, no joint training needed.
Caution: summaries are LLM-generated (build-time cost, staleness on edit) and
QA accuracy is downstream of the reader (UnifiedQA 3B in-paper), not pure
retrieval.

**Faiss repo (https://github.com/facebookresearch/faiss, MIT, 40893 stars,
pushed 2026-09-12).** Runnable backend for IVF/PQ/HNSW on CPU+GPU. Take: pin
this as the ANN implementation; benchmarks in 1702.08734 transfer to its
current GPU paths. Careful: version-pin — API shifts across releases.

**DiskANN repo (https://github.com/microsoft/DiskANN, MIT, 1924 stars, pushed
2026-09-11).** SSD-resident graph index. Take: fallback if the vector corpus
outgrows RAM and SPANN's SPTAG path is unavailable. Careful: needs fast local
SSD; no arXiv paper found, so cite only repo-observed facts.

**hnswlib (https://github.com/nmslib/hnswlib, Apache-2.0, 5327 stars, pushed
2026-09-12).** Header-only HNSW with Python bindings. Take: smallest-footprint
CPU ANN for small-to-mid corpora (the 20-doc rig through millions of
sections). Careful: single-process oriented; sharding is our problem.

**ann-benchmarks (https://github.com/erikbern/ann-benchmarks, MIT, 5732
stars).** Docker harness behind the paper's plots. Take: reuse for Spike 010
index comparisons. Careful: Docker-heavy; aluminum-bench successors exist but
were out of lane scope.

**USearch (https://github.com/unum-cloud/USearch, Apache-2.0, 4300 stars).**
HNSW-family engine. Take: fallback only. Careful: no paper; claims are vendor
statements, not admitted results.

## (b) Refutations of brief-held claims

1. "A graph index (HNSW) is the safe default everywhere." Qualified by
ANN-Benchmarks (1807.05614): on the Rand-Euclidean set "both HNSW and SWG
fail... while PANNG, KGraph, NND can solve the task easily with high QPS",
and graph builds "take a long time for datasets with difficult queries".
Default HNSW, but keep an IVF fallback armed.
2. "Compression/truncation of embeddings is approximately free." Refuted in
detail by ColBERTv2 (2112.01488): 1-bit codes cost 36.2% -> 35.5% MRR@10 even
with residual centroids, and naive binarization without centroids is worse
(34.8%). Truncation needs nested training (MRL, 2205.13147), not slicing.
3. "Dense first-stage retrieval has made sparse signals redundant."
Contradicted by SPLADEv2 (2109.10086): distilled sparse "clearly
outperforming recent dense models on zero-shot evaluation", and by BGE-M3
(2402.03216), whose cross-functionality distillation exists precisely because
each arm contributes. Keep a sparse arm.
4. "Rerankers are too slow for a small-GPU harness." Qualified by MiniLM
(2002.10957) + PLAID (2205.09707): distilled 6-layer students hold >99% at
2.0x speedup, and PLAID-ColBERTv2 lands within 1.6x of SPLADEv2 latency at
higher quality. Small/fast reranking is an engineering point in range, not a
research bet — but neither paper demonstrates it at 0.3B on ranking data, so
Spike 010 must measure it.

## (c) Unresolved ledger

- Reciprocal-rank / score fusion weights for dense+sparse+graph arms: RRF has
no arXiv PDF (abstain); BGE-M3 fuses by distillation at train time, not by
score fusion at query time. Open: measure linear/RRF fusion on our corpus.
- Product quantization 2011 foundations: no arXiv PDF (abstain); Faiss paper
covers usage but not the full Jégou analysis. No action — Faiss suffices.
- DiskANN paper numbers: no arXiv id found (abstain); SPANN's reported 2x-over-
DiskANN is single-source (authors compare against their SPTAG/DiskANN runs).
Needs independent replication before choosing SPANN over DiskANN.
- uniCOIL exact reference: unresolved id (abstain); COIL-family terrain is
covered by SPLADEv2/ColBERT, but a COIL-vs-SPLADE head-to-head is missing.
- Consumer-GPU QPS for 0.3B–1B rerankers with batching: no admitted paper
reports it (monoT5/RankT5 report quality; MiniLM reports GLUE/SQuAD speedups).
Spike 010 must produce this number.
- ANN recall on trained text embeddings with cosine/IP (vs SIFT/GloVe in the
old papers): ScaNN addresses MIPS directly, but an HNSW-vs-IVF shootout on
Qwen3-Embedding-0.6B vectors is unmeasured. Spike 010 item.
- Index-update/write-amplification costs (streaming ingestion, §1 Q6 second
half): none of the admitted papers measure incremental updates; lane 9 owns
it, and it is open there too.

## (d) Security findings (stated as requirements)

- No lane-10 paper or repo exposes a prompt-injection or data-exfiltration
surface: ANN libraries consume numeric vectors, not text.
- REQUIREMENT: pin exact faiss/hnswlib/SPTAG versions (commit hash) in the
serving image; ANN libs contain native code with a history of memory-safety
CVEs — do not float on latest.
- REQUIREMENT: checksum-verify downloaded index artefacts and model files
before mmap; a corrupt PQ codebook fails silently into wrong neighbors.
- REQUIREMENT: RAPTOR-style summary trees cache LLM output keyed by chunk
hash; invalidate on source edit or retrieval serves stale evidence quotes
(feeds Spike 003's validator-failure mode).
