# Lane 10 method

## Queries run

arXiv title search (`https://arxiv.org/search/?query=...&searchtype=title`),
verified one by one at `https://arxiv.org/abs/<id>` (citation_title /
citation_author / citation_date meta + Accepted/Published comment), 1–2 s
between calls:
- "Hierarchical Navigable Small World" -> 1603.09320 (HNSW)
- "Billion-scale similarity search with GPUs" path via known id -> 1702.08734
- "Accelerating Large-Scale Inference with Anisotropic Vector Quantization"
  -> 1908.10396 (ScaNN)
- "SPANN: Highly-efficient Billion-scale Approximate Nearest" -> 2111.08566
- "Matryoshka Representation Learning" via known id -> 2205.13147
- "ColBERT: Efficient and Effective Passage Search" -> 2004.12832
  (abs page: Accepted at SIGIR 2020)
- "ColBERTv2: Effective and Efficient Retrieval" -> 2112.01488
- "PLAID: An Efficient Engine for Late Interaction Retrieval" -> 2205.09707
- XTR all-fields search -> 2304.01982 (confirmed XTR by abstract author/title)
- "SPLADE v2: Sparse Lexical and Expansion" -> 2109.10086
- "ANN-Benchmarks: A Benchmarking Tool" via known id -> 1807.05614
- "M3-Embedding" via known id -> 2402.03216
- "Document Ranking with a Pretrained Sequence-to-Sequence Model" -> 2003.06713
- "RankT5: Fine-Tuning T5 for Text Ranking with Ranking Losses" -> 2210.10634
- DPR / ANCE / SPLADEv1 / MiniLM / SBERT / E5 / Nomic / RAPTOR / DocT5Query /
  jina-v3 / C-Pack / Llama2Vec via known ids, each confirmed at its abs page
- "DiskANN: Fast Accurate Billion-point Nearest Neighbor Search" -> no arXiv
  hit (abstained as paper); "uniCOIL" -> ambiguous hits, none verified
  (abstained)

GitHub API (`/repos/{owner}/{repo}`): facebookresearch/faiss (40893 stars,
2026-09-12, MIT), microsoft/DiskANN (1924, 2026-09-11, MIT), nmslib/hnswlib
(5327, 2026-09-12, Apache-2.0), erikbern/ann-benchmarks (5732, 2026-07-10,
MIT), unum-cloud/USearch (4300, 2026-08-31, Apache-2.0), microsoft/SPTAG
(5016, 2026-09-04, MIT). Hugging Face API: BAAI/bge-reranker-v2-m3 card
(Apache-2.0, ~18M downloads) — abstained as secondary source.

## Sources used

arXiv abs pages (18 admitted + 10 screened), admitted PDFs (18, text-extracted
with pypdf for numbers), GitHub REST API (6 repos), Hugging Face models API
(1 card). No sources outside `reference/micro-harnesses/deep-research-2/`
were modified.

## Counts

Screened 37 (27 arXiv ids + 6 GitHub repos + 1 HF card + 3 paper-no-arXiv:
RRF, PQ-2011, DiskANN-paper). Admitted 23 (18 papers + 5 repos). Abstained 14
with reasons in `inventory.tsv`. Minimums met (≥20 screened, ≥8 admitted).

## What failed

- `export.arxiv.org` API (`/api/query`): "Rate exceeded" then connection
timeout; replaced with HTML title search on `arxiv.org/search/`, which worked.
- Semantic Scholar API: HTTP 429 throughout (no key); no citation-graph
chaining was possible. Forward-chaining was approximated by (a) following
in-paper citation trails extracted from the PDFs (e.g. ColBERTv2 -> SPLADEv2 /
RocketQA / TAS-B; SPANN -> DiskANN / SPTAG; XTR -> GTR / ColBERT) and (b)
screening every co-cited candidate found that way (SPLADEv1, C-Pack, E5,
Llama2Vec). A follow-up with an S2 key could still add post-2024 ANN systems
(aluminum-bench, FreshDiskANN, LVQ, RaBitQ) that this lane did not cover.
- Papers with Code API: not attempted after S2 failed (secondary index, low
marginal value once PDFs were in hand).
- No local PDF toolchain (no pdftotext, no pip); used `uv run --with
pypdf --with fonttools` for text extraction. One paper needed fonttools for
CFF fonts; extraction succeeded after adding it.
- Two recalled ids were wrong and corrected against fetched pages: 2009.10270
is not RRF, 2005.00830 is not monoT5, 2106.14871 is not uniCOIL, 2402.01691
is not Nomic (correct: 2402.01613), 2212.06757 is not RankT5 (correct:
2210.10634). Nothing recalled was admitted without abs-page confirmation.
