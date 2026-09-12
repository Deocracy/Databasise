# Lane 2 method: training recipes for embedders

## Queries run

arXiv export API (Atom), id_list batches first to verify memory-guessed ids,
then title/abstract searches (max_results 5-8, sortBy relevance or
submittedDate), 3-10s sleeps between calls (429s forced backoff to 8-15s):

- id_list batches covering 28 ids; 6 memory-guessed ids proved wrong
(Gecko, Promptagator, InPars, Arctic, TAS-B, plus one Promptagator miss)
and were recovered via title search (correct: 2403.20327, 2209.11755,
2202.05144, 2405.05374, 2104.06967).
- ti:InPars, ti:"Topic Aware Sampling", abs:"Arctic Embed",
ti:distillation AND abs:"dense retrieval" (16 hits, scanned for
distillation-into-small items).
- Early all: queries returned 0 hits (underscore tokenization); ti:/abs:
prefix form works. Two curl batches were lost to 429s (empty files
s_i*.xml); retried after backoff.

Semantic Scholar API: one successful citations call
(/paper/arXiv:2401.00368/citations, 30 results, mostly off-topic applied
papers), then 429 on subsequent search calls despite 5-8s waits. Forward
chaining is therefore incomplete; recorded as a gap.

GitHub REST API (repo facts + search, ~15 calls, 3s spacing, well under the
60/hr quota): McGill-NLP/llm2vec, QwenLM/Qwen3-Embedding,
FlagOpen/FlagEmbedding, facebookresearch/contriever, facebookresearch/DPR,
microsoft/ANCE, princeton-nlp/SimCSE, microsoft/unilm, microsoft/LoRA,
UKPLab/gpl, PaddlePaddle/RocketQA, artidoro/qlora, castorini/docTTTTTquery;
search for sentence-transformers (found huggingface/sentence-transformers,
UKPLab path dead), NV-Embed (nvidia/NV-Embed 404, no official training
repo), InPars (community mirror only), arctic-embed (Snowflake-Labs),
TAS-Balanced (sebastian-hofstaetter/tas-balanced-dense-retrieval).

Hugging Face API (4 model lookups): intfloat/e5-mistral-7b-instruct,
Qwen/Qwen3-Embedding-0.6B, BAAI/bge-m3, nvidia/NV-Embed-v2 (downloads,
likes, license recorded).

arXiv abs pages (curl, 2-3s spacing): 20 admitted plus Doc2Query, LoRA,
CPC abs verified; titles/authors/dates/abstracts extracted by regex.

## Sources used

arXiv export API and abs pages (primary), GitHub API (repo existence,
stars, pushed_at, license), Hugging Face API (artefact existence,
downloads, license), Semantic Scholar (one citation chain). No blog or
vendor pages used. Papers with Code and OpenReview not consulted (lane
budget). Per the brief, arxiv.org/search HTML was avoided after the
reminder; export API used instead.

## Counts

Screened 29 (one inventory row each). Admitted 20 (abs verified + PDF
downloaded + %PDF checked). Abstained 9 (3 abs-verified but subsumed:
Doc2Query, LoRA, InfoNCE; 3 API-verified but budget-deprioritized: GTE,
Nomic, AnglE; 3 API-search-only: PairDistill, CL-Distill, BiXSE).

## What failed

- 6 of 11 memory-guessed arXiv ids were wrong; all recovered via live
title search. Lesson recorded: never trust recalled ids.
- arXiv export API 429s under 3s spacing; 8-15s spacing works.
- Semantic Scholar throttled after 1-2 calls; chaining incomplete.
- nvidia/NV-Embed repo 404s; sentence-transformers moved orgs
(UKPLab -> huggingface); both resolved via search API.
- No PDF text toolchain (no pdftotext, pypdf, pymupdf; no pip) in the
sandbox, so per-stage compute numbers were not extracted from full texts.
The 20 PDFs in papers/ are staged for that pass.
