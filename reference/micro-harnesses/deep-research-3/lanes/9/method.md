# Lane 9 method

## Queries run

No general web-search engine with arXiv/Semantic Scholar API access was usable: `export.arxiv.org/api/query` returned `Rate exceeded` and `api.semanticscholar.org` returned HTTP 429 throughout the session. All discovery therefore used the `websearch` tool (fast mode) with targeted queries, followed by direct primary-source fetches with `curl`/`webfetch`:

- Seed queries from the brief: `LLMLingua prompt compression`, `RECOMP retrieval compression`, `xRAG modality fusion retrieval augmentation`.
- Family completion: `LongLLMLingua question-aware compression`, `LLMLingua-2 data distillation`, `FILCO filtering retrieval context`, `Gist tokens distillation instruction compression`, `AutoCompressors soft prompts`, `ICAE in-context autoencoder`, `Lost in the Middle long contexts`, `Selective Context self-information`.
- Procedural-memory / skills branch: `Voyager skill library`, `MemGPT memory hierarchies`, `Generative Agents simulacra`, `Reflexion verbal reinforcement learning`.
- Assembly / ordering / eval branch: `RAPTOR tree-organized retrieval`, `Self-RAG reflection tokens`, `RankGPT re-ranking`, `QMSum query-based meeting summarization`, `distracted by irrelevant context`, `Making Retrieval-Augmented Language Models Robust to Irrelevant Context` (Yoran et al.), `ARES automated evaluation RAG`.
- Forward/backward chaining was done through paper text (related-work sections in fetched pages) rather than the Semantic Scholar graph, which was unreachable; e.g. xRAG's comparison table surfaced FILCO/RECOMP/ICAE, and LongLLMLingua's text surfaced Lost-in-the-Middle.

## Sources used, in brief order of authority

1. arXiv abs pages (`https://arxiv.org/abs/<id>`) — all 22 IDs verified live via curl title check on 2026-09-12.
2. Downloaded PDFs (`https://arxiv.org/pdf/<id>`) — all 22 downloaded, `%PDF` header verified, filed as `papers/<id>_<slug>.pdf`.
3. Venues: ACL Anthology pages (LLMLingua, LongLLMLingua, LLMLingua-2 via MS Research, AutoCompressors, Selective Context via repo, RankGPT, ARES), ICLR proceedings pages (RECOMP, ICAE, RAPTOR, Self-RAG), NeurIPS proceedings pages (Gist, xRAG, Reflexion via repo), TACL/transacl.org (Lost-in-the-Middle), PMLR (GSM-IC), ACM DL (Generative Agents), OpenReview (FILCO, Self-RAG), Microsoft Research publication pages (LLMLingua family).
4. GitHub API (`api.github.com/repos/<owner>/<repo>`) for stars/pushed_at/license — 13 repos verified; rate limit (60/hr unauthenticated) exhausted before ARES, whose facts come from its fetched repo page instead. Lost-in-the-Middle repo URL comes from the paper text; its star/push/license fields are recorded as `unknown`.
5. Hugging Face: RECOMP compressor checkpoints (`fangyuan/*_compressor`) confirmed via the repo README; no separate Hub API calls (rate budget reserved for GitHub).

## Screening counts

22 candidates screened, 22 admitted, 0 refuted, 0 abstained. The literature was not thinner than the minimums: every sub-topic of the lane (hard compression, soft compression, query-focused summarization, ordering/reranking, procedural memory/skills, consumer-quality measurement, RAG eval) yielded at least two verified primaries.

## Column convention note

`inventory.tsv` uses `capability=6` for all rows, per brief section 4 ("which question from section 1 it bears on (1 to 6...)"); this lane covers brief question 6. The lane task text says "(1-5 or refutes)", which appears to be a copy error since the brief defines six questions.

## What failed

- arXiv search API and Semantic Scholar API: rate-limited for the whole session; replaced by websearch + direct abs/PDF fetches.
- GitHub API: rate-limited after ~15 calls; ARES repo facts taken from the fetched repo page, Lost-in-the-Middle repo facts recorded as unknown rather than invented.
- One PDF batch timed out at the shell level (120 s); all 21 completed files verified `%PDF`, the 22nd (Reflexion) fetched in a follow-up call.
- No Papers-with-Code or Hugging Face Hub API screening; artefacts recorded only where a primary source (paper or repo README) named them.
