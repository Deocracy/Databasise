# Lane 3 method

Lane: Small embedders and distillation into them (0.1B–0.6B, distillation,
long-document behaviour), including MiniCPM-Embedding, Qwen3-Embedding-0.6B,
arctic-embed-s, bge-small, nomic-embed, jina-embeddings-v3, EmbeddingGemma,
granite-embedding.

## Queries run

- arXiv export API (`export.arxiv.org/api/query`), `ti:` and `id_list`
  forms, one call per ~65s after rate limiting began:
  `ti:"Qwen3 Embedding"`, `ti:"Nomic Embed"`, `ti:"Gecko Versatile Text
  Embeddings"`, `ti:"MiniCPM"`, `ti:"BGE M3"`, `ti:"C-Pack"`,
  `ti:"Towards General Text Embeddings"`, `id_list` for 2506.07900,
  2402.03216, 2310.05187 (zero entries — wrong id, recorded as failed probe),
  2309.07597 / 2308.03281 (empty during throttle window; 2309.07597 later
  confirmed via HF card link), 1908.10084, 2212.03533, 2112.09118 (zero
  entries — wrong id, failed probe).
- arXiv HTML search pages (`arxiv.org/search/`, curl): used only to locate
  the Nomic MoE paper id (2502.07972, "Training Sparse Mixture Of Experts
  Text Embedding Models"). Per lane instructions these pages are not cited;
  every located id was re-verified at its abs page.
- arXiv abs pages (curl + webfetch, the primary verification surface):
  2506.05176, 2402.03216, 2402.01613, 2403.20327, 2205.13147, 2409.10173,
  2401.00368, 2502.07972, 2506.07900, plus 2509.20354, 2502.20204,
  2405.05374, 2309.07597, 2407.18887 found via HF-card paper links.
- arXiv full-text HTML (`arxiv.org/html/<id>`) greps for training facts:
  Qwen3 loss/masking, Gecko 1.2B base + 66.31 MTEB, E5 batch 32,768 / 20k
  steps / 270M filtered pairs.
- Hugging Face API (`huggingface.co/api/models`): download/like/license
  facts for 8 small-embedder checkpoints; safetensors param count for
  nomic-embed-text-v1 (136,731,648). HF model-card pages (curl + arxiv-link
  grep) yielded the paper ids for EmbeddingGemma, Granite, Arctic, C-Pack,
  and the clustering paper, and confirmed MiniCPM-Embedding links no paper.
- GitHub API (`api.github.com`): stars/pushed/license for
  nomic-ai/contrastors, RAIVNLab/MRL, MinishLab/model2vec, openbmb/MiniCPM,
  huggingface/sentence-transformers, FlagOpen/FlagEmbedding (found via
  search after BAAI/FlagEmbedding 404 — org renamed), Snowflake-Labs/
  arctic-embed (found via search). No repositories cloned.

## Counts

Screened 21 candidates (15 admit, 6 abstain). Every admitted item was opened
at its arXiv abs page (title/authors/date/abstract on record) and its PDF
downloaded to `papers/` (all verified to start with `%PDF`, 15 files).

## What failed

- `export.arxiv.org` returned "Rate exceeded" / empty bodies / timeouts for
  extended stretches (shared-IP throttling); worked in small windows with
  ≥60s gaps. Three id guesses probed during the outage returned nothing and
  are recorded as failed probes, not candidates.
- Semantic Scholar API returned persistent HTTP 429 for this IP; no S2 data
  used. Forward-chaining via citations was therefore not performed; it was
  compensated with HF-card paper-link mining (which surfaces the papers the
  artefacts themselves cite) and direct abs verification.
- `paperswithcode.com/api` returned empty bodies; not used.
- No PDF text-extraction tooling (no pypdf/pymupdf/pdftotext, no pip) — score
  tables inside PDFs were not extracted; abstracts + HTML full-text greps
  ground the numbers cited.
- jina-ai/embeddings and BAAI/FlagEmbedding as GitHub paths 404 (renamed:
  FlagOpen/FlagEmbedding; jina has no official training repo under an obvious
  name) — corrected via the search API, not memory.
